"""
Test: Provider Core Cache & Thread Isolation.

Tests the core-level infrastructure in asset_source.py:
- _run_provider_in_thread(): thread isolation, timeout, exception propagation
- _asset_history_cache: smart range with per-date granularity
- _asset_current_cache: simple TTL cache for current values
- _asset_metadata_cache: simple TTL cache for metadata
- _search_query_cache: Layer 2 exact query cache
- probe_provider_config bypasses cache
"""

import asyncio
import inspect
import sys
import time

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.services.asset_source import (
    AssetSourceError,
    AssetSourceManager,
    _asset_current_cache,
    _asset_history_cache,
    _asset_metadata_cache,
    _run_provider_in_thread,
    _search_query_cache,
)
from backend.test_scripts.test_utils import print_section, print_success


# ============================================================================
# FIXTURES — clear core caches before each test
# ============================================================================


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear all core caches before each test."""
    _asset_history_cache.clear()
    _asset_current_cache.clear()
    _asset_metadata_cache.clear()
    _search_query_cache.clear()
    yield


# ============================================================================
# _run_provider_in_thread — Thread Isolation
# ============================================================================


@pytest.mark.asyncio
class TestRunProviderInThread:
    """Tests for _run_provider_in_thread()."""

    async def test_blocking_provider_does_not_block_main_loop(self):
        """A provider that sleeps 1s should NOT block the main event loop."""
        print_section("_run_provider_in_thread: blocking provider")

        async def slow_provider():
            time.sleep(1)  # Intentionally blocking (sync sleep in async def)
            return "done"

        async def instant_task():
            return "instant"

        t0 = time.monotonic()
        # Run both concurrently — if thread isolation works, instant_task
        # completes immediately even though slow_provider blocks for 1s
        results = await asyncio.gather(
            _run_provider_in_thread(slow_provider),
            instant_task(),
        )
        elapsed = time.monotonic() - t0

        assert results[0] == "done"
        assert results[1] == "instant"
        # Should complete in ~1s (slow provider), NOT 2s (sequential)
        assert elapsed < 2.0, f"Took {elapsed:.2f}s — main loop was blocked!"
        print_success(f"Completed in {elapsed:.2f}s — main loop not blocked")

    async def test_timeout_raises_timeout_error(self):
        """A provider that takes too long should raise TimeoutError."""
        print_section("_run_provider_in_thread: timeout")

        async def stuck_provider():
            await asyncio.sleep(10)  # Will never complete within timeout
            return "never"

        with pytest.raises(asyncio.TimeoutError):
            await _run_provider_in_thread(stuck_provider, timeout=1.0)
        print_success("TimeoutError raised correctly")

    async def test_exception_propagation(self):
        """Provider exceptions should propagate to the caller."""
        print_section("_run_provider_in_thread: exception propagation")

        async def failing_provider():
            raise AssetSourceError("Test error", "TEST_ERROR", {"detail": "test"})

        with pytest.raises(AssetSourceError, match="Test error"):
            await _run_provider_in_thread(failing_provider)
        print_success("AssetSourceError propagated correctly")

    async def test_return_value(self):
        """Provider return values should be passed through."""
        print_section("_run_provider_in_thread: return value")

        async def value_provider():
            return {"price": 42.5, "currency": "USD"}

        result = await _run_provider_in_thread(value_provider)
        assert result == {"price": 42.5, "currency": "USD"}
        print_success(f"Return value: {result}")

    async def test_sync_code_in_async_def(self):
        """Sync code (requests-style) inside async def should work in thread."""
        print_section("_run_provider_in_thread: sync code in async def")

        async def sync_in_async_provider():
            # Simulate what yfinance does: sync HTTP inside async def
            time.sleep(0.5)  # blocking sync call
            return "fetched"

        result = await _run_provider_in_thread(sync_in_async_provider, timeout=5.0)
        assert result == "fetched"
        print_success("Sync code inside async def works correctly")


# ============================================================================
# History Cache — Smart Range
# ============================================================================


class TestHistoryCache:
    """Tests for _asset_history_cache smart range logic."""

    def test_full_hit(self):
        """Cache fully populated → all dates returned, no gaps."""
        print_section("History cache: full hit")
        cache_key = ("test_prov", "AAPL", "TICKER")
        dates = {f"2025-01-{d:02d}": {"date": f"2025-01-{d:02d}", "close": 100 + d} for d in range(1, 11)}
        _asset_history_cache.set(cache_key, {"dates": dates, "events": []})

        cached, ok = _asset_history_cache.get(cache_key)
        assert ok is True
        assert len(cached["dates"]) == 10
        # All dates from 01 to 10 present
        for d in range(1, 11):
            assert f"2025-01-{d:02d}" in cached["dates"]
        print_success(f"Full hit: {len(cached['dates'])} dates")

    def test_partial_gap_detection(self):
        """Cache has gaps → gap dates identifiable."""
        print_section("History cache: partial gap detection")
        cache_key = ("test_prov", "AAPL", "TICKER")
        # Dates: 1,2,5,6,9,10 — missing 3,4,7,8
        dates = {}
        for d in [1, 2, 5, 6, 9, 10]:
            dates[f"2025-01-{d:02d}"] = {"date": f"2025-01-{d:02d}", "close": 100 + d}
        _asset_history_cache.set(cache_key, {"dates": dates, "events": []})

        cached, ok = _asset_history_cache.get(cache_key)
        assert ok is True

        # Check which dates are missing in range 1-10
        missing = []
        for d in range(1, 11):
            d_iso = f"2025-01-{d:02d}"
            if d_iso not in cached["dates"]:
                missing.append(d_iso)
        assert len(missing) == 4
        assert "2025-01-03" in missing
        assert "2025-01-04" in missing
        print_success(f"Gaps detected: {missing}")

    def test_full_miss(self):
        """Cache empty → miss."""
        print_section("History cache: full miss")
        cache_key = ("test_prov", "AAPL", "TICKER")
        cached, ok = _asset_history_cache.get(cache_key)
        assert ok is False
        print_success("Cache miss for empty cache")

    def test_merge_updates_cache(self):
        """Merging new data into cache updates existing entry."""
        print_section("History cache: merge updates")
        cache_key = ("test_prov", "AAPL", "TICKER")
        # Start with dates 1-3
        dates = {f"2025-01-{d:02d}": {"date": f"2025-01-{d:02d}", "close": 100} for d in range(1, 4)}
        _asset_history_cache.set(cache_key, {"dates": dates, "events": []})

        # Simulate merge: add dates 4-6
        cached, ok = _asset_history_cache.get(cache_key)
        for d in range(4, 7):
            cached["dates"][f"2025-01-{d:02d}"] = {"date": f"2025-01-{d:02d}", "close": 200}
        _asset_history_cache.set(cache_key, cached)

        # Verify merged data
        merged, ok = _asset_history_cache.get(cache_key)
        assert ok is True
        assert len(merged["dates"]) == 6
        assert merged["dates"]["2025-01-04"]["close"] == 200
        print_success(f"Merged: {len(merged['dates'])} dates")

    def test_events_stored_with_dates(self):
        """Events are stored alongside dates in the cache entry."""
        print_section("History cache: events stored")
        cache_key = ("test_prov", "AAPL", "TICKER")
        events = [{"date": "2025-01-05", "type": "DIVIDEND", "value": 0.5}]
        dates = {"2025-01-05": {"date": "2025-01-05", "close": 150}}
        _asset_history_cache.set(cache_key, {"dates": dates, "events": events})

        cached, ok = _asset_history_cache.get(cache_key)
        assert ok is True
        assert len(cached["events"]) == 1
        assert cached["events"][0]["type"] == "DIVIDEND"
        print_success("Events stored and retrieved correctly")


# ============================================================================
# Current Cache
# ============================================================================


class TestCurrentCache:
    """Tests for _asset_current_cache."""

    def test_hit(self):
        """Set cache → get returns value."""
        print_section("Current cache: hit")
        cache_key = ("test_prov", "AAPL", "TICKER")
        mock_value = {"value": 150.0, "currency": "USD", "as_of_date": "2025-04-14"}
        _asset_current_cache.set(cache_key, mock_value)

        cached, ok = _asset_current_cache.get(cache_key)
        assert ok is True
        assert cached["value"] == 150.0
        assert cached["currency"] == "USD"
        print_success("Current cache hit OK")

    def test_miss(self):
        """Empty cache → miss."""
        print_section("Current cache: miss")
        cache_key = ("test_prov", "UNKNOWN", "TICKER")
        cached, ok = _asset_current_cache.get(cache_key)
        assert ok is False
        print_success("Current cache miss OK")

    def test_miss_then_populate_then_hit(self):
        """Miss → populate → second get is hit."""
        print_section("Current cache: miss → populate → hit")
        cache_key = ("test_prov", "MSFT", "TICKER")

        # Miss
        _, ok = _asset_current_cache.get(cache_key)
        assert ok is False

        # Populate
        _asset_current_cache.set(cache_key, {"value": 400.0, "currency": "USD"})

        # Hit
        cached, ok = _asset_current_cache.get(cache_key)
        assert ok is True
        assert cached["value"] == 400.0
        print_success("Miss → populate → hit cycle OK")


# ============================================================================
# Metadata Cache
# ============================================================================


class TestMetadataCache:
    """Tests for _asset_metadata_cache."""

    def test_hit(self):
        """Set cache → get returns metadata."""
        print_section("Metadata cache: hit")
        cache_key = ("test_prov", "AAPL", "TICKER")
        mock_meta = {"display_name": "Apple Inc.", "asset_type": "STOCK", "currency": "USD"}
        _asset_metadata_cache.set(cache_key, mock_meta)

        cached, ok = _asset_metadata_cache.get(cache_key)
        assert ok is True
        assert cached["display_name"] == "Apple Inc."
        print_success("Metadata cache hit OK")

    def test_none_value_cached(self):
        """None can be cached (provider returned no metadata)."""
        print_section("Metadata cache: None value")
        cache_key = ("test_prov", "NODATA", "TICKER")
        _asset_metadata_cache.set(cache_key, None)

        cached, ok = _asset_metadata_cache.get(cache_key)
        assert ok is True
        assert cached is None
        print_success("None value cached correctly")


# ============================================================================
# Search Query Cache (Layer 2)
# ============================================================================


class TestSearchQueryCache:
    """Tests for _search_query_cache (Layer 2)."""

    def test_exact_query_hit(self):
        """Exact query cached → returned immediately."""
        print_section("Search query cache: exact hit")
        cache_key = ("yfinance", "apple")
        mock_results = [
            {"identifier": "AAPL", "display_name": "Apple Inc.", "provider_code": "yfinance"},
            {"identifier": "APLE", "display_name": "Apple Hospitality", "provider_code": "yfinance"},
        ]
        _search_query_cache.set(cache_key, mock_results)

        cached, ok = _search_query_cache.get(cache_key)
        assert ok is True
        assert len(cached) == 2
        assert cached[0]["identifier"] == "AAPL"
        print_success(f"Exact query hit: {len(cached)} results")

    def test_different_query_miss(self):
        """Different query → miss."""
        print_section("Search query cache: different query miss")
        _search_query_cache.set(("yfinance", "apple"), [{"identifier": "AAPL"}])

        cached, ok = _search_query_cache.get(("yfinance", "microsoft"))
        assert ok is False
        print_success("Different query correctly misses")

    def test_different_provider_miss(self):
        """Same query, different provider → miss."""
        print_section("Search query cache: different provider miss")
        _search_query_cache.set(("yfinance", "apple"), [{"identifier": "AAPL"}])

        cached, ok = _search_query_cache.get(("justetf", "apple"))
        assert ok is False
        print_success("Same query, different provider correctly misses")

    def test_case_sensitivity(self):
        """Cache key is case-sensitive (caller normalizes to lowercase)."""
        print_section("Search query cache: case sensitivity")
        _search_query_cache.set(("yfinance", "apple"), [{"identifier": "AAPL"}])

        # Uppercase query → miss (caller is responsible for lowering)
        _, ok = _search_query_cache.get(("yfinance", "Apple"))
        assert ok is False

        # Lowercase → hit
        _, ok = _search_query_cache.get(("yfinance", "apple"))
        assert ok is True
        print_success("Case sensitivity works correctly")


# ============================================================================
# Probe Bypasses Cache
# ============================================================================


class TestProbeBypassesCache:
    """Tests that probe operations should NOT use cache."""

    def test_probe_callsite_does_not_check_cache(self):
        """
        Verify that probe_provider_config uses _run_provider_in_thread
        directly (no cache get/set). We test this by verifying that
        populating the current cache does NOT affect what probe would call.

        This is a design verification test: probe should ALWAYS call the
        provider, even if the cache has data for the same identifier.
        """
        print_section("Probe: bypasses cache (design check)")
        # Populate current cache
        cache_key = ("yfinance", "AAPL", "TICKER")
        _asset_current_cache.set(cache_key, {"value": 999.0, "currency": "CACHED"})

        # The cache has data, but probe_provider_config in asset_source.py
        # calls _run_provider_in_thread directly without checking cache.
        # We verify this by checking the probe code does NOT reference cache.

        source = inspect.getsource(AssetSourceManager.probe_provider_config)
        assert "_asset_current_cache" not in source, "Probe should NOT use current cache"
        assert "_asset_history_cache" not in source, "Probe should NOT use history cache"
        assert "_asset_metadata_cache" not in source, "Probe should NOT use metadata cache"
        assert "_run_provider_in_thread" in source, "Probe should use thread isolation"
        print_success("Probe bypasses all caches, uses thread isolation only")

