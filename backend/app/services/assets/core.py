"""
Asset pricing core: the runtime shared by the asset service modules and every plugin call.

This module provides:
- the provider caches (history, current value, metadata, search results, search queries)
- configured_provider(): a new provider instance with its plugin settings bound (services/plugin_settings/)
- call_provider(): the one boundary of every provider call — NOT_CONFIGURED, the pauses after «too many requests»
  (RATE_LIMITED, services/platform/provider_cooldown.py), the secrets masked in the call's errors and log lines, then
  _run_provider_in_thread(), where the call runs in a dedicated thread with its own event loop
- cooldown_scope_for(): the part of a provider a pause applies to for one identifier (the plugin's hook)
- the provider parameter helpers (_provider_params_hash, _parse_provider_params)
- _json_safe_details(): the sanitizer of ``AssetSourceError.details`` for API responses

The plugin contract (AssetSourceProvider, AssetSourceError) lives in ``base.py``.

Nothing here backward-fills prices: history is stored exactly as providers return
it, and gaps are filled only when prices are read (assets/price_query.py).

Similar to the FX service (services/fx/) but for price_history table (asset prices vs FX rates).

Key differences from FX:
- Table: price_history (not fx_rates)
- Fields: OHLC (open/high/low/close) + volume (not single rate)
- Lookup: (asset_id, date) not (base, quote, date)
- Synthetic yield: Calculated on-demand for SCHEDULED_YIELD assets

Design principles:
- Bulk-first: All operations have bulk version as PRIMARY
- Singles call bulk with 1 element
- DB optimization: Minimize queries (typically 1-3 max)
- Parallel provider calls where possible
"""

import asyncio
import hashlib
import json
import math
from collections.abc import Awaitable, Callable
from typing import Optional

from backend.app.logging_config import get_logger
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceError, AssetSourceProvider
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.platform.provider_cooldown import record_no_verdict, record_refusal, record_success, wait_before_call
from backend.app.services.plugin_settings.contract import PluginSettingsMixin
from backend.app.services.plugin_settings.runtime import configure_instance
from backend.app.utils.runtime.cache import get_ttl_cache
from backend.app.utils.runtime.cooldown import RateLimitedError
from backend.app.utils.runtime.secret_masking import exception_renders_secret, mask_exception, mask_text, masked_description, secrets_in_flight

# Initialize structured logger
logger = get_logger(__name__)

# ============================================================================
# CORE CACHES — automatic TTL expiration via theine timer wheel
# ============================================================================

_asset_history_cache = get_ttl_cache("asset_history_fetch", maxsize=500, ttl=900)  # 15 min
_asset_current_cache = get_ttl_cache("asset_current_fetch", maxsize=300, ttl=120)  # 2 min
_asset_metadata_cache = get_ttl_cache("asset_metadata_fetch", maxsize=200, ttl=1800)  # 30 min
_search_result_cache = get_ttl_cache("search_results", maxsize=5000, ttl=86400)  # 24h — individual items
_search_query_cache = get_ttl_cache("search_queries", maxsize=500, ttl=900)  # 15 min — query→results
_RISK_WARMUP_DAY_MULTIPLIER = 2


def _provider_params_hash(provider_params: Optional[dict]) -> str:
    """
    Stable short hash of `provider_params` for use in cache keys (#R3-4).

    Uses MD5 (non-cryptographic, just for keying) over the JSON-serialized params
    with sorted keys to guarantee determinism regardless of dict iteration order.
    Returns the first 8 hex chars — enough entropy to avoid collisions across the
    small number of concurrently-cached keys per asset.
    """
    if not provider_params:
        return "none"
    try:
        payload = json.dumps(provider_params, sort_keys=True, default=str)
    except Exception:
        payload = repr(sorted(provider_params.items()))
    return hashlib.md5(payload.encode("utf-8")).hexdigest()[:8]


def _parse_provider_params(raw_params):
    """Parse stored provider params into a dictionary."""
    if raw_params is None:
        return {}
    if isinstance(raw_params, dict):
        return raw_params
    if isinstance(raw_params, str):
        try:
            return json.loads(raw_params)
        except Exception:
            return {}
    return {}


# ============================================================================
# THREAD ISOLATION FOR PROVIDER CALLS
# ============================================================================


async def configured_provider(code: str, *, user_id: int | None = None) -> AssetSourceProvider | None:
    """A new instance of the provider ``code`` with its settings bound, or ``None`` for an unknown code.

    ``user_id`` only for a call made for a user (search, the probe of a configuration): the user's own values then
    reach the plugin too. Prices, history, metadata and scheduled jobs serve every user: they pass none.
    """
    provider = AssetProviderRegistry.get_provider_instance(code)
    if provider is None:
        return None
    return await configure_instance(provider, "asset", user_id=user_id)


def settings_cache_part(provider: AssetSourceProvider) -> str:
    """The part of a cache key that depends on the provider's settings: empty when it declares none."""
    return provider.settings.fingerprint if isinstance(provider, PluginSettingsMixin) else ""


def public_asset_url(provider: AssetSourceProvider, url: str | None) -> str | None:
    """``url``, unless it shows one of the provider's secrets: an asset URL is shown to the user, so a plugin never puts
    a secret in it; one that does gets no URL, and the log says which provider (security review of CP10–CP11). Hidden
    whole, never masked: a masked URL would tell a caller where a value they chose occurs."""
    if not url or not isinstance(provider, PluginSettingsMixin):
        return url
    secrets = provider.settings.secret_values()
    if secrets and mask_text(url, secrets) != url:
        logger.warning("Provider asset URL withheld: it shows a secret", provider=provider.provider_code)
        return None
    return url


async def settings_cache_part_for(code: str) -> str:
    """The settings part of the cache keys of the provider ``code``, as a call would compute it now.

    For the code that drops cache entries by key. An entry stored under other settings has another key: no lookup
    reaches it any more, and it expires with its TTL.
    """
    provider = await configured_provider(code)
    return settings_cache_part(provider) if provider is not None else ""


def asset_cache_key(provider_code: str, identifier: str | None, identifier_type: object, provider_params: dict | str | None, settings_part: str) -> tuple[str, str, str, str, str]:
    """The key of a provider's answers in `_asset_history_cache` and `_asset_current_cache`: the inputs of the call.

    The one function for every reader, writer and drop of those entries (X-R27, X-R28): the provider, the identifier as
    the assignment stores it (none as ""), its stored input type, the hash of the parameters (#R3-4) and the provider's
    settings (`settings_cache_part`). A provider sees nothing else, so equal keys always mean equal answers, and other
    parameters or settings never share one.
    """
    return (provider_code, identifier or "", str(identifier_type), _provider_params_hash(_parse_provider_params(provider_params)), settings_part)


async def drop_asset_cache_entries(provider_code: str, identifier: str | None, identifier_type: object, provider_params: dict | str | None) -> None:
    """Drop the cached history and current value of one provider assignment, keyed as a call would key them now."""
    key = asset_cache_key(provider_code, identifier, identifier_type, provider_params, await settings_cache_part_for(provider_code))
    _asset_history_cache.delete(key)
    _asset_current_cache.delete(key)


def cooldown_scope_for(provider: AssetSourceProvider, identifier: str, identifier_type=None, provider_params: dict | None = None) -> str | None:
    """The part of ``provider`` a pause applies to for this identifier: the plugin's ``cooldown_scope``, else None.

    None for a test double without the hook, and when the hook fails (logged): a pause then applies to the whole
    provider, which is never wrong, only broader.
    """
    hook = getattr(provider, "cooldown_scope", None)
    if hook is None:
        return None
    try:
        scope = hook(identifier, identifier_type, provider_params)
    except Exception as error:  # noqa: BLE001 — a broken hook must not stop the call
        logger.warning("Provider cooldown_scope failed: the pause covers the whole provider", provider=getattr(provider, "provider_code", None), error=type(error).__name__)
        return None
    return scope if isinstance(scope, str) and scope else None


async def call_provider[ResultT](provider: AssetSourceProvider, fn: Callable[[], Awaitable[ResultT]], *, timeout: float, scope: str | None = None) -> ResultT:
    """The one boundary of every call to an asset provider.

    ``provider`` is the configured instance (``configured_provider``), ``fn`` a zero-argument callable that returns the
    provider coroutine, for example ``lambda: provider.get_current_value(identifier, identifier_type, params)``.
    ``scope`` is the part of the provider the call is about (``cooldown_scope_for``), None for all of it.

    - A required setting left without a value refuses the call before any I/O: ``AssetSourceError`` with
      ``NOT_CONFIGURED`` and the missing field keys in ``details["missing"]``.
    - A provider paused after «too many requests» (decision 34, ``services/platform/provider_cooldown.py``) is not
      called: ``AssetRateLimitedError`` at once, ``retry_after`` the seconds of pause left. A refusal the call meets
      (the plugin raises a ``RateLimitedError``) pauses the provider, and the error leaves with ``retry_after`` set to
      the pause decided; an answer ends a pause; any other end frees the trial of an expired pause for the next caller.
    - The provider's secrets are in flight for the call: masked in every line logged meanwhile, here and in the
      provider's thread, and in the exception the call raises, its chain included (``utils/runtime/secret_masking.py``).
      An error that still shows a secret after masking (its text built by a ``__str__`` of its own) is replaced by an
      ``AssetSourceError`` with ``PROVIDER_ERROR`` (``RATE_LIMITED`` for a refusal), its masked description and no link
      to the original. ``PROVIDER_ERROR`` also carries the masked description in ``details["detail"]``, for the
      localized message (``providerErrors.PROVIDER_ERROR``).
    - When the call carries a secret the caller chose (a personal field), a text that shows any secret is hidden whole
      (``***``), not masked in place: masking a chosen value would tell whether it occurs in the text, and so, by
      guesses, what stands beside it — an instance secret (security review of CP10–CP11, decision N15). The log lines
      keep the precise masking.

    A test double that is not a plugin has no settings and no pause: it is called as it is.
    """
    if not isinstance(provider, PluginSettingsMixin):  # a test double: no settings to check or mask, no pause
        return await _run_provider_in_thread(fn, timeout=timeout)
    code = provider.provider_code
    settings = provider.settings
    if settings.missing:
        missing = list(settings.missing)
        raise AssetSourceError(f"Provider {code} is not configured: {', '.join(missing)} missing", "NOT_CONFIGURED", {"missing": missing})
    wait = wait_before_call("asset", code, scope)
    if wait > 0:
        raise AssetRateLimitedError(f"Provider {code} is paused after too many requests: {math.ceil(wait)} s left", retry_after=wait, scope=scope)
    secrets = settings.secret_values()
    # A secret the caller chose (a personal field) is in this call: hide whole every text that shows a secret, since
    # masking it in place would tell whether that value occurs beside an instance secret (decision N15).
    whole = settings.carries_user_secrets
    with secrets_in_flight(secrets):
        try:
            result = await _run_provider_in_thread(fn, timeout=timeout)
        except BaseException as error:
            mask_exception(error, secrets, whole=whole)
            refused = isinstance(error, RateLimitedError)
            if refused:
                error_scope = error.scope if error.scope is not None else scope
                paused = record_refusal("asset", code, error_scope, error.retry_after)
                if paused > 0:
                    error.retry_after, error.scope = paused, error_scope
            else:
                record_no_verdict("asset", code, scope)
            if not isinstance(error, Exception) or (not exception_renders_secret(error, secrets) and (not refused or isinstance(error, AssetSourceError))):
                raise
            description = masked_description(error, secrets, whole=whole)
            retry_after, error_scope = (error.retry_after, error.scope) if refused else (None, None)
        else:
            record_success("asset", code, scope)
            return result
    # Raised out of the except block: the new error keeps no link to the one it replaces.
    if refused:
        raise AssetRateLimitedError(f"Provider {code} refused for too many requests: {description}", retry_after=retry_after, scope=error_scope)
    raise AssetSourceError(f"Provider {code} failed: {description}", "PROVIDER_ERROR", {"detail": description})


async def _run_provider_in_thread(coro_factory, *, timeout: float = 60.0):
    """
    Run a provider coroutine in a dedicated thread with its own event loop.

    Protects the main event loop from blocking provider implementations.
    Even a well-written async provider (httpx) works fine — it just uses
    the thread's event loop instead of the main one.

    A badly-written provider that does `requests.get()` directly in an
    async def will block the thread, NOT the main event loop.

    Args:
        coro_factory: Zero-arg callable that returns the coroutine to run.
                     Example: lambda: provider.get_current_value(id, type, params)
        timeout: Maximum time to wait (seconds). Default 60s.

    Returns:
        Result of the coroutine.

    Raises:
        asyncio.TimeoutError: If provider takes longer than timeout.
        Any exception raised by the provider.
    """

    def _sync_runner():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro_factory())
        finally:
            asyncio.set_event_loop(None)
            loop.close()

    return await asyncio.wait_for(
        asyncio.to_thread(_sync_runner),
        timeout=timeout,
    )


# (Pydantic models for API request/response live in backend.app.schemas.assets)
# They are imported by API modules when needed


def _json_safe_details(details: Optional[dict]) -> Optional[dict]:
    """Make an AssetSourceError ``details`` dict safe for a JSON response (I3).

    Providers may put dates, Decimals or other non-primitives in ``details``;
    the probe DTO must serialize, so anything not natively JSON-safe is
    stringified. ``None`` and empty dicts stay ``None`` (field omitted).

    Deliberately NOT :func:`backend.app.utils.json_utils.ensure_json_safe`:
    that one is a *validator* — it rejects non-JSON producer output on contract
    boundaries (signals, AI Export). Here the provider is a third-party plugin
    and the probe must still return a localized error, so we *sanitize*
    (stringify, one list level deep) instead of raising. See
    ``backend/app/utils/json_utils.py`` module docstring (audit 08, report 03 §N-03-A).
    """
    if not details:
        return None
    safe: dict = {}
    for key, value in details.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            safe[str(key)] = value
        elif isinstance(value, (list, tuple)):
            safe[str(key)] = [item if item is None or isinstance(item, (str, int, float, bool)) else str(item) for item in value]
        else:
            safe[str(key)] = str(value)
    return safe
