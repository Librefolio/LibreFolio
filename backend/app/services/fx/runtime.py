"""The runtime of the FX provider calls: a configured instance, and the one boundary every call goes through.

- ``configured_fx_provider(code)``: a new instance with the instance's plugin settings bound. An FX provider never
  receives a user's values: a sync serves every user (``plugin_settings/fields.py``, family rules).
- ``call_fx_provider(provider, fn)``: refuses the call with ``FXNotConfiguredError`` when a required setting has no
  value, then runs it with the provider's secrets in flight — masked in every line logged meanwhile and in the
  exception the call raises (``utils/runtime/secret_masking.py``). X1–X7 (Z7) consult the pause registry here.
- ``settings_cache_part(provider)``: the part of a cache key that depends on the provider's settings, empty when it
  declares none.

FX providers are async (``httpx``) and run on the main event loop, not in a thread. Every call goes through here:
``sync.py`` (``ensure_rates_multi_source`` and ``_fetch_provider``) and ``catalog.py``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from backend.app.services.fx.base import FXNotConfiguredError, FXRateProvider, FXServiceError
from backend.app.services.fx.registry import FXProviderRegistry
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.runtime import configure_instance
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
    """Run ``fn()`` — a call to ``provider`` — through the boundary: ``NOT_CONFIGURED`` first, the secrets masked.

    An error that still shows a secret after masking (its text built by a ``__str__`` of its own) is replaced by an
    ``FXServiceError`` with its masked description and no link to the original. A test double that is not a plugin has
    no settings: it is called as it is.
    """
    if not isinstance(provider, PluginSettingsMixin):
        return await fn()
    settings = provider.settings
    if settings.missing:
        raise FXNotConfiguredError(provider.provider_code, list(settings.missing))
    secrets = settings.secret_values()
    with secrets_in_flight(secrets):
        try:
            return await fn()
        except BaseException as error:
            mask_exception(error, secrets)
            if not isinstance(error, Exception) or not exception_renders_secret(error, secrets):
                raise
            description = masked_description(error, secrets)
    # Raised out of the except block: the new error keeps no link to the one that still shows a secret.
    raise FXServiceError(f"Provider {provider.provider_code} failed: {description}")
