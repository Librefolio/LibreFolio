"""The runtime of the FX provider calls: a configured instance, and the one boundary every call goes through.

- ``configured_fx_provider(code)``: a new instance with the instance's plugin settings bound. An FX provider never
  receives a user's values: a sync serves every user (``plugin_settings/fields.py``, family rules).
- ``call_fx_provider(provider, fn)``: refuses the call with ``FXNotConfiguredError`` when a required setting has no
  value, and with ``FXRateLimitedError`` while the provider is paused after «too many requests»
  (``services/platform/provider_cooldown.py``); counts a provider that reaches an external service before the call and
  refuses it with ``FXCallLimitError`` when an instance limit is full (``services/platform/call_counter.py``, project 76
  U3); then runs it with the provider's secrets in flight — masked in every
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

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXCallLimitError, FXNotConfiguredError, FXRateLimitedError, FXRateProvider, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.platform import call_counter
from backend.app.services.platform.provider_cooldown import limit_pause_left, record_limit_pause, record_no_verdict, record_refusal, record_success, wait_before_call
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.runtime import configure_instance
from backend.app.utils.runtime.cooldown import RateLimitedError
from backend.app.utils.runtime.secret_masking import exception_renders_secret, mask_exception, masked_description, secrets_in_flight

logger = get_logger(__name__)


async def configured_fx_provider(code: str) -> FXRateProvider | None:
    """A new instance of the FX provider ``code`` with the instance's settings bound, or ``None`` for an unknown code."""
    provider = FXProviderRegistry.get_provider_instance(code)
    if provider is None:
        return None
    return await configure_instance(provider, "fx")


def settings_cache_part(provider: FXRateProvider) -> str:
    """The part of a cache key that depends on the provider's settings: empty when it declares none."""
    return provider.settings.fingerprint if isinstance(provider, PluginSettingsMixin) else ""


async def _count_fx_call(provider: FXRateProvider, code: str) -> None:
    """Count the call before it leaves, whatever it then meets (project 76, U3). A full limit refuses it and pauses the
    provider exactly until the window ends, on the limit's own key (never a source's 429 streak); a count that ends with
    neither (cancelled) frees the trial of an expired source pause for the next caller."""
    fingerprint = provider.settings.fingerprint
    left = limit_pause_left("fx", code, fingerprint)
    if left > 0:
        raise FXCallLimitError(f"Provider {code} is paused at its call limit: {math.ceil(left)} s left", retry_after=left, details={"reason": "call_limit"})
    family, owner, limits = call_counter.call_owner(provider, "fx")
    try:
        await call_counter.count_and_check(family, owner, limits)
    except call_counter.CallLimitReached as full:
        logger.warning("Provider call refused: instance call limit reached", provider=code, owner=f"{family}/{owner}", window=full.window, limit=full.limit, retry_after_s=round(full.retry_after, 1))
        # Exactly until the full window ends, on the limit's own key: never a refusal of the source (U2b)
        paused = record_limit_pause("fx", code, fingerprint, full.retry_after)
        details = {"reason": "call_limit", "window": full.window, "limit": full.limit}
        raise FXCallLimitError(f"Provider {code} reached its {full.window} call limit ({full.limit})", retry_after=paused or full.retry_after, details=details) from full
    except BaseException:
        record_no_verdict("fx", code)
        raise


def _admit_fx_call_checks(provider: FXRateProvider, code: str) -> None:
    """The refusals before any I/O that need no database: a required setting without a value, a pause."""
    settings = provider.settings
    if settings.missing:
        raise FXNotConfiguredError(code, list(settings.missing))
    wait = wait_before_call("fx", code)
    if wait > 0:
        raise FXRateLimitedError(f"Provider {code} is paused after too many requests: {math.ceil(wait)} s left", retry_after=wait)


async def call_fx_provider[ResultT](provider: FXRateProvider, fn: Callable[[], Awaitable[ResultT]]) -> ResultT:
    """Run ``fn()`` — a call to ``provider`` — through the boundary: ``NOT_CONFIGURED`` first, the pauses, the secrets masked.

    A provider paused after «too many requests» (decision 34, ``services/platform/provider_cooldown.py``) is not called:
    ``FXRateLimitedError`` at once, ``retry_after`` the seconds left; the sync records a failed leg and tries the next
    route. A refusal the call meets pauses the provider and leaves with ``retry_after`` set to the pause decided; an
    answer ends a pause; any other end frees the trial of an expired pause. An error that still shows a secret after
    masking (its text built by a ``__str__`` of its own) is replaced by an ``FXServiceError`` (``FXRateLimitedError``
    for a refusal) with its masked description and no link to the original. A test double that is not a plugin has no
    settings and no pause: it is called as it is.

    A provider with ``calls_external_service`` is counted before the call, after the two refusals above, on its own row
    or its credit-sharing group's (``call_counter.call_owner``). A full limit: ``FXCallLimitError`` without the call,
    and a pause exactly until the window ends on the limit's own key (the settings fingerprint in it). A limit refusal
    frees the trial of an expired source pause; a count that ends with neither frees both trials.
    """
    if not isinstance(provider, PluginSettingsMixin):
        return await fn()
    code = provider.provider_code
    settings = provider.settings
    _admit_fx_call_checks(provider, code)
    # A test double with settings that is no FXRateProvider declares nothing: never counted, as a bare double
    if getattr(provider, "calls_external_service", False):
        try:
            await _count_fx_call(provider, code)
        except FXCallLimitError:
            # A limit refusal is no verdict on the source: the trial of its expired pause goes to the next caller
            record_no_verdict("fx", code)
            raise
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
