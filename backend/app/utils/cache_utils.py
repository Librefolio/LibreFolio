"""
Centralized caching utilities using cachetools.

Provides TTL-based caching with automatic expiration to avoid manual garbage collection.
All caches are thread-safe and support automatic cleanup of expired entries.
"""

from typing import Any

import structlog
from cachetools import TTLCache

logger = structlog.get_logger(__name__)

# Global registry of named caches
_cache_registry: dict[str, TTLCache] = {}


def get_ttl_cache(name: str, maxsize: int = 1000, ttl: int = 3600) -> TTLCache:
    """
    Get or create a named TTL cache with automatic expiration.

    Args:
        name: Unique identifier for the cache (e.g., 'yfinance_search', 'justetf_metadata')
        maxsize: Maximum number of entries in cache (default: 1000)
        ttl: Time-to-live in seconds (default: 3600 = 1 hour)

    Returns:
        TTLCache instance with specified parameters

    Example:
        cache = get_ttl_cache('my_cache', maxsize=500, ttl=1800)
        cache['key'] = 'value'
        value = cache.get('key', default_value)
    """
    if name not in _cache_registry:
        logger.info(
            "Creating new TTL cache",
            cache_name=name,
            maxsize=maxsize,
            ttl_seconds=ttl
            )
        _cache_registry[name] = TTLCache(maxsize=maxsize, ttl=ttl)

    return _cache_registry[name]


def clear_cache(name: str) -> bool:
    """
    Clear a named cache.

    Args:
        name: Cache identifier

    Returns:
        True if cache existed and was cleared, False if not found
    """
    if name in _cache_registry:
        _cache_registry[name].clear()
        logger.info("Cache cleared", cache_name=name)
        return True
    return False


def clear_all_caches() -> int:
    """
    Clear all registered caches.

    Returns:
        Number of caches cleared
    """
    count = len(_cache_registry)
    for cache in _cache_registry.values():
        cache.clear()
    logger.info("All caches cleared", cache_count=count)
    return count


def get_cache_stats(name: str) -> dict[str, Any] | None:
    """
    Get statistics for a named cache.

    Args:
        name: Cache identifier

    Returns:
        Dict with cache stats (size, maxsize, ttl) or None if not found
    """
    if name not in _cache_registry:
        return None

    cache = _cache_registry[name]
    return {
        "name": name,
        "current_size": len(cache),
        "maxsize": cache.maxsize,
        "ttl": cache.ttl
        }


def list_caches() -> list[dict[str, Any]]:
    """
    List all registered caches with their stats.

    Returns:
        List of cache statistics
    """
    return [
        get_cache_stats(name)
        for name in _cache_registry.keys()
        ]
