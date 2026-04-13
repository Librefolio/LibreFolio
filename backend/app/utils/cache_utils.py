"""
Centralized caching utilities using theine (high-performance Rust-backed cache).

Provides TTL-based caching with automatic expiration via hierarchical timer wheel.
All caches are thread-safe by default (including free-threaded Python support).

theine API used by callers:
    cache.set(key, value)            # set with the cache's default TTL
    value, ok = cache.get(key)       # get returns (value, exists) tuple
    cache.delete(key)                # remove a key
    cache.clear()                    # remove all entries
    len(cache)                       # current entry count

Why theine (vs cachetools):
- Rust core with W-TinyLFU eviction policy (adaptive LRU/LFU)
- Per-item TTL set on write; expired items removed by timer wheel (no scanning)
- Thread-safe by default; free-threaded Python 3.13.6+ supported
- No need to re-set items to refresh TTL — timer wheel handles expiry efficiently
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import structlog
from theine import Cache

logger = structlog.get_logger(__name__)


class NamedCache:
    """
    Thin wrapper around theine.Cache that binds a default TTL and tracks metadata.

    Callers use theine's native API:
        cache.set(key, value)            # uses default TTL
        value, ok = cache.get(key)       # returns (value, True) or (None, False)
        cache.delete(key)
        cache.clear()
        len(cache)
    """

    def __init__(self, name: str, maxsize: int, ttl: int):
        self.name = name
        self._maxsize = maxsize
        self._ttl_seconds = ttl
        self._default_ttl = timedelta(seconds=ttl)
        self._cache = Cache(maxsize)

    # -- theine native API pass-through with default TTL --

    def get(self, key: Any) -> tuple[Any, bool]:
        """Get value by key. Returns (value, True) if found, (None, False) otherwise."""
        return self._cache.get(key)

    def set(self, key: Any, value: Any, *, ttl: timedelta | None = None) -> None:
        """Set value with TTL (defaults to cache-level TTL)."""
        self._cache.set(key, value, ttl=ttl or self._default_ttl)

    def delete(self, key: Any) -> None:
        """Remove a key from the cache."""
        self._cache.delete(key)

    def clear(self) -> None:
        """Remove all entries."""
        self._cache.clear()

    def close(self) -> None:
        """Stop the timer wheel thread (call on shutdown)."""
        self._cache.close()

    def __len__(self) -> int:
        return len(self._cache)

    # -- metadata for stats/admin --

    @property
    def maxsize(self) -> int:
        return self._maxsize

    @property
    def ttl(self) -> float:
        return float(self._ttl_seconds)


# ============================================================================
# Global registry
# ============================================================================

_cache_registry: dict[str, NamedCache] = {}


def get_ttl_cache(name: str, maxsize: int = 1000, ttl: int = 3600) -> NamedCache:
    """
    Get or create a named TTL cache.

    Args:
        name: Unique identifier for the cache (e.g., 'yfinance_search')
        maxsize: Maximum number of entries (W-TinyLFU eviction when full)
        ttl: Default time-to-live in seconds

    Returns:
        NamedCache instance (theine.Cache with bound default TTL)

    Example::

        cache = get_ttl_cache('my_cache', maxsize=500, ttl=1800)
        cache.set('key', 'value')
        value, ok = cache.get('key')
        if ok:
            print(value)
    """
    if name not in _cache_registry:
        logger.info("Creating new TTL cache", cache_name=name, maxsize=maxsize, ttl_seconds=ttl)
        _cache_registry[name] = NamedCache(name=name, maxsize=maxsize, ttl=ttl)
    return _cache_registry[name]


def clear_cache(name: str) -> bool:
    """Clear a named cache. Returns True if found, False otherwise."""
    if name in _cache_registry:
        _cache_registry[name].clear()
        logger.info("Cache cleared", cache_name=name)
        return True
    return False


def clear_all_caches() -> int:
    """Clear all registered caches. Returns count cleared."""
    count = len(_cache_registry)
    for cache in _cache_registry.values():
        cache.clear()
    logger.info("All caches cleared", cache_count=count)
    return count


def close_all_caches() -> int:
    """
    Close all registered caches (stop timer wheel threads) and clear the registry.

    Call this during application shutdown for a clean exit.
    Each theine.Cache runs a background timer wheel thread; closing stops it.

    Returns:
        Number of caches closed.
    """
    count = len(_cache_registry)
    for name, cache in list(_cache_registry.items()):
        try:
            cache.close()
            logger.debug("Cache closed", cache_name=name)
        except Exception as e:
            logger.warning("Failed to close cache", cache_name=name, error=str(e))
    _cache_registry.clear()
    if count:
        logger.info("All caches closed on shutdown", cache_count=count)
    return count


def get_cache_stats(name: str) -> dict[str, Any] | None:
    """Get statistics for a named cache, or None if not found."""
    if name not in _cache_registry:
        return None
    c = _cache_registry[name]
    return {"name": c.name, "current_size": len(c), "maxsize": c.maxsize, "ttl": c.ttl}


def list_caches() -> list[dict[str, Any]]:
    """List all registered caches with their stats."""
    return [s for name in _cache_registry if (s := get_cache_stats(name)) is not None]
