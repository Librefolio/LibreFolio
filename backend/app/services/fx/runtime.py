"""The runtime of the FX provider calls: a configured instance, and the one boundary every call goes through.

- ``configured_fx_provider(code)``: a new instance with the instance's plugin settings bound. An FX provider never
  receives a user's values: a sync serves every user (``plugin_settings/fields.py``, family rules).
- ``call_fx_provider(provider, fn)``: refuses the call with ``FXNotConfiguredError`` when a required setting has no
  value, and with ``FXRateLimitedError`` while the provider is paused after «too many requests»
  (``services/platform/provider_cooldown.py``); then runs it with the provider's secrets in flight — masked in every
  line logged meanwhile and in the exception the call raises (``utils/runtime/secret_masking.py``) — and records the
  outcome for the pauses.
- ``settings_cache_part(provider)``: the part of a cache key that depends on the provider's settings, empty when it
  declares none.

FX providers are async (``httpx``) and run on the main event loop, not in a thread. Every call goes through here:
``sync.py`` (``ensure_rates_multi_source`` and ``_fetch_provider``) and ``catalog.py``.
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable

from backend.app.services.fx.base import FXNotConfiguredError, FXRateLimitedError, FXRateProvider, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform.provider_cooldown import record_no_verdict, record_refusal, record_success, wait_before_call
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.runtime import configure_instance
from backend.app.utils.runtime.cooldown import RateLimitedError
from backend.app.utils.runtime.secret_masking import exception_renders_secret, mask_exception, masked_description, secrets_in_flight


async def configured_fx_provider(code: str) -> FXRateProvider | None:
    """A new instance of the FX provider ``code`` with the instance's settings bound, or ``None`` for an unknown code."""
    provider = FXProviderRegistry.get_provider_instance(code)
    if provider is None:
        return None
    return await configure_instance(provider, "fx")


def settings_cache_part(provider: FXRateProvider) -> str:
    """The part of a cache key that depends on the provider's settings: empty when it declares none."""
    return provider.settings.fingerprint if isinstance(provider, PluginSettingsMixin) else ""


async def call_fx_provider[ResultT](provider: FXRateProvider, fn: Callable[[], Awaitable[ResultT]]) -> ResultT:
    """Run ``fn()`` — a call to ``provider`` — through the boundary: ``NOT_CONFIGURED`` first, the pauses, the secrets masked.

    A provider paused after «too many requests» (decision 34, ``services/platform/provider_cooldown.py``) is not called:
    ``FXRateLimitedError`` at once, ``retry_after`` the seconds left; the sync records a failed leg and tries the next
    route. A refusal the call meets pauses the provider and leaves with ``retry_after`` set to the pause decided; an
    answer ends a pause; any other end frees the trial of an expired pause. An error that still shows a secret after
    masking (its text built by a ``__str__`` of its own) is replaced by an ``FXServiceError`` (``FXRateLimitedError``
    for a refusal) with its masked description and no link to the original. A test double that is not a plugin has no
    settings and no pause: it is called as it is.
    """
    if not isinstance(provider, PluginSettingsMixin):
        return await fn()
    code = provider.provider_code
    settings = provider.settings
    if settings.missing:
        raise FXNotConfiguredError(code, list(settings.missing))
    wait = wait_before_call("fx", code)
    if wait > 0:
        raise FXRateLimitedError(f"Provider {code} is paused after too many requests: {math.ceil(wait)} s left", retry_after=wait)
    secrets = settings.secret_values()
    with secrets_in_flight(secrets):
        try:
            result = await fn()
        except BaseException as error:
            mask_exception(error, secrets)
            refused = isinstance(error, RateLimitedError)
            if refused:
                paused = record_refusal("fx", code, None, error.retry_after)
                if paused > 0:
                    error.retry_after = paused
            else:
                record_no_verdict("fx", code)
            if not isinstance(error, Exception) or (not exception_renders_secret(error, secrets) and (not refused or isinstance(error, FXServiceError))):
                raise
            description = masked_description(error, secrets)
            retry_after = error.retry_after if refused else None
        else:
            record_success("fx", code)
            return result
    # Raised out of the except block: the new error keeps no link to the one it replaces.
    if refused:
        raise FXRateLimitedError(f"Provider {code} refused for too many requests: {description}", retry_after=retry_after)
    raise FXServiceError(f"Provider {code} failed: {description}")
