"""
Tests for cache_utils — NamedCache, registry, TTL, stats.

Tests cover:
- NamedCache basic operations (set/get/delete/clear)
- TTL-based expiration
- Registry: get_ttl_cache, clear_cache, clear_all_caches, close_all_caches
- Cache stats and listing
- Edge cases: missing keys, duplicate registry names
"""

import time

import pytest

from backend.app.utils.cache_utils import (
    NamedCache,
    get_ttl_cache,
    clear_cache,
    clear_all_caches,
    close_all_caches,
    get_cache_stats,
    list_caches,
    _cache_registry,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _clean_registry():
    """Clean the global cache registry before and after each test."""
    # Close any existing caches to stop timer wheel threads
    for c in list(_cache_registry.values()):
        try:
            c.close()
        except Exception:
            pass
    _cache_registry.clear()
    yield
    # Cleanup after test
    for c in list(_cache_registry.values()):
        try:
            c.close()
        except Exception:
            pass
    _cache_registry.clear()


# ============================================================================
# NamedCache basic operations
# ============================================================================


class TestNamedCache:
    """Test NamedCache wrapper around theine.Cache."""

    def test_set_and_get(self):
        cache = NamedCache("test", maxsize=100, ttl=60)
        cache.set("key1", "value1")
        val, ok = cache.get("key1")
        assert ok is True
        assert val == "value1"
        cache.close()

    def test_get_missing_key(self):
        cache = NamedCache("test", maxsize=100, ttl=60)
        val, ok = cache.get("nonexistent")
        assert ok is False
        assert val is None
        cache.close()

    def test_delete(self):
        cache = NamedCache("test", maxsize=100, ttl=60)
        cache.set("key1", "value1")
        cache.delete("key1")
        val, ok = cache.get("key1")
        assert ok is False
        cache.close()

    def test_clear(self):
        cache = NamedCache("test", maxsize=100, ttl=60)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        assert len(cache) >= 1  # at least 1 entry
        cache.clear()
        assert len(cache) == 0
        cache.close()

    def test_len(self):
        cache = NamedCache("test", maxsize=100, ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert len(cache) == 3
        cache.close()

    def test_metadata_properties(self):
        cache = NamedCache("my_cache", maxsize=500, ttl=1800)
        assert cache.name == "my_cache"
        assert cache.maxsize == 500
        assert cache.ttl == 1800.0
        cache.close()

    def test_overwrite_key(self):
        cache = NamedCache("test", maxsize=100, ttl=60)
        cache.set("key", "old")
        cache.set("key", "new")
        val, ok = cache.get("key")
        assert ok is True
        assert val == "new"
        cache.close()

    def test_various_value_types(self):
        cache = NamedCache("test", maxsize=100, ttl=60)
        cache.set("int", 42)
        cache.set("float", 3.14)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1})
        cache.set("none", None)

        val, ok = cache.get("int")
        assert ok and val == 42
        val, ok = cache.get("float")
        assert ok and val == 3.14
        val, ok = cache.get("list")
        assert ok and val == [1, 2, 3]
        val, ok = cache.get("dict")
        assert ok and val == {"a": 1}
        val, ok = cache.get("none")
        assert ok and val is None
        cache.close()


# ============================================================================
# TTL expiration
# ============================================================================


class TestCacheTTL:
    """Test TTL-based expiration."""

    def test_ttl_expiration(self):
        """Value should expire after TTL."""
        cache = NamedCache("ttl_test", maxsize=100, ttl=1)
        cache.set("key", "value")
        val, ok = cache.get("key")
        assert ok is True

        # Wait for TTL to expire
        time.sleep(1.5)
        val, ok = cache.get("key")
        assert ok is False
        cache.close()


# ============================================================================
# Global registry
# ============================================================================


class TestCacheRegistry:
    """Test global cache registry functions."""

    def test_get_ttl_cache_creates_new(self):
        cache = get_ttl_cache("test_reg", maxsize=200, ttl=300)
        assert cache.name == "test_reg"
        assert cache.maxsize == 200
        assert "test_reg" in _cache_registry

    def test_get_ttl_cache_returns_same_instance(self):
        c1 = get_ttl_cache("singleton", maxsize=100, ttl=60)
        c2 = get_ttl_cache("singleton", maxsize=999, ttl=999)  # params ignored for existing
        assert c1 is c2
        assert c1.maxsize == 100  # original params kept

    def test_clear_cache_existing(self):
        cache = get_ttl_cache("clearable", maxsize=100, ttl=60)
        cache.set("key", "value")
        assert len(cache) == 1
        result = clear_cache("clearable")
        assert result is True
        assert len(cache) == 0

    def test_clear_cache_nonexistent(self):
        result = clear_cache("does_not_exist")
        assert result is False

    def test_clear_all_caches(self):
        c1 = get_ttl_cache("cache_a", maxsize=50, ttl=60)
        c2 = get_ttl_cache("cache_b", maxsize=50, ttl=60)
        c1.set("k", "v")
        c2.set("k", "v")
        count = clear_all_caches()
        assert count == 2
        assert len(c1) == 0
        assert len(c2) == 0

    def test_close_all_caches(self):
        get_ttl_cache("closeable_1", maxsize=50, ttl=60)
        get_ttl_cache("closeable_2", maxsize=50, ttl=60)
        count = close_all_caches()
        assert count == 2
        assert len(_cache_registry) == 0

    def test_get_cache_stats(self):
        cache = get_ttl_cache("stats_cache", maxsize=100, ttl=300)
        cache.set("a", 1)
        cache.set("b", 2)
        stats = get_cache_stats("stats_cache")
        assert stats is not None
        assert stats["name"] == "stats_cache"
        assert stats["current_size"] == 2
        assert stats["maxsize"] == 100
        assert stats["ttl"] == 300.0

    def test_get_cache_stats_nonexistent(self):
        assert get_cache_stats("no_such_cache") is None

    def test_list_caches(self):
        get_ttl_cache("list_1", maxsize=50, ttl=60)
        get_ttl_cache("list_2", maxsize=100, ttl=120)
        result = list_caches()
        assert len(result) == 2
        names = {s["name"] for s in result}
        assert names == {"list_1", "list_2"}

