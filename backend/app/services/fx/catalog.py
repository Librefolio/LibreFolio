"""
The supported-currency list of each FX provider, cached for ``GET /fx/providers``.

Some providers fetch that list over the network (ECB on every call, SNB until its first success), so the provider
catalog used to wait for them on every request and showed them with no currencies when the network was down.
``get_supported_currencies_cached`` asks each provider at most once a day:

- a list that came back is cached for 24 hours (named cache ``fx_provider_currencies``, listed in the cache panel);
- a fetch that fails or exceeds ``SUPPORTED_CURRENCIES_TIMEOUT_S`` answers with the last list that provider returned
  in this process (empty before its first success), cached for ``RETRY_AFTER_FAILURE_S`` before the next attempt;
- clearing the cache forces a new fetch but keeps the last known lists.
"""

import asyncio
import weakref
from datetime import timedelta

from backend.app.logging_config import get_logger
from backend.app.services.fx.base import FXRateProvider
from backend.app.services.fx.runtime import call_fx_provider, settings_cache_part
from backend.app.utils.runtime.cache import get_ttl_cache

logger = get_logger(__name__)

SUPPORTED_CURRENCIES_TTL_S = 24 * 3600
RETRY_AFTER_FAILURE_S = 5 * 60
SUPPORTED_CURRENCIES_TIMEOUT_S = 5.0

_currencies_cache = get_ttl_cache("fx_provider_currencies", maxsize=32, ttl=SUPPORTED_CURRENCIES_TTL_S)
_last_known: dict[str, list[str]] = {}
# One lock per provider and per event loop: a contended asyncio.Lock stays bound to the loop it waited in.
_fetch_locks: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Lock]]" = weakref.WeakKeyDictionary()


def _fetch_lock(code: str) -> asyncio.Lock:
    locks = _fetch_locks.setdefault(asyncio.get_running_loop(), {})
    return locks.setdefault(code, asyncio.Lock())


def _cache_key(code: str, provider: FXRateProvider) -> str:
    """The cache key of a provider's list: its code, plus the fingerprint of its settings when it declares any."""
    settings_part = settings_cache_part(provider)
    return f"{code}#{settings_part}" if settings_part else code


async def get_supported_currencies_cached(code: str, provider: FXRateProvider, *, timeout: float = SUPPORTED_CURRENCIES_TIMEOUT_S) -> list[str]:
    """The sorted supported currencies of ``provider`` (registry ``code``): cached, never raising, never waiting more than ``timeout``.

    ``provider`` is a configured instance (``fx/runtime.py``): its settings are part of the cache key, and the call goes
    through the FX boundary.
    """
    key = _cache_key(code, provider)
    cached, found = _currencies_cache.get(key)
    if found:
        return list(cached)
    async with _fetch_lock(key):
        cached, found = _currencies_cache.get(key)
        if found:
            return list(cached)
        try:
            currencies = sorted(await asyncio.wait_for(call_fx_provider(provider, provider.get_supported_currencies), timeout=timeout))
        except Exception as exc:  # timeout, network or parse error: the catalog must still answer
            fallback = _last_known.get(code, [])
            reason = str(exc) or type(exc).__name__
            logger.warning(f"Supported currencies of {code} unavailable ({reason}): using {'the last known list' if fallback else 'an empty list'} for {RETRY_AFTER_FAILURE_S} s")
            _currencies_cache.set(key, list(fallback), ttl=timedelta(seconds=RETRY_AFTER_FAILURE_S))
            return list(fallback)
        _last_known[code] = currencies
        _currencies_cache.set(key, currencies)
        return list(currencies)
