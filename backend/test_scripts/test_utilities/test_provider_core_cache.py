"""
Test: Provider Core Cache & Thread Isolation.

Tests the canonical asset-source core contracts:
- _run_provider_in_thread(): thread isolation, timeout, exception propagation
- _asset_history_cache: smart range with per-date granularity
- _asset_current_cache: simple TTL cache for current values
- _asset_metadata_cache: simple TTL cache for metadata
- _search_query_cache: Layer 2 exact query cache
- _search_result_cache: Layer 1 individual-result cache
- probe_provider_config bypasses cache
- the history and current-value cache keys across the paths that fill them (refresh, current price) and the ones
  that drop them (currency-change wipe, parametric assignment change): X-R27, X-R28
"""

import asyncio
import contextvars
import functools
import json
import subprocess
import sys
import textwrap
import threading
import time
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.db import IdentifierType
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.app.db.models import Asset, AssetProviderAssignment, AssetType, PriceHistory, ProviderInputType
from backend.app.schemas.assets.assets import FAAssetPatchItem
from backend.app.schemas.prices import FACurrentPriceItem, FACurrentValue, FAHistoricalData, FAPricePoint
from backend.app.schemas.provider import FAProviderAssignmentItem, FAProviderConfigBase, FAProviderKind, ProbeOperation
from backend.app.schemas.refresh import FARefreshItem, FARefreshResult, SyncDateRangeModel
from backend.app.services.assets import core as asset_source_core
from backend.app.services.assets import currency_change as currency_change_operations
from backend.app.services.assets import metadata as metadata_operations
from backend.app.services.assets import price_query as price_query_operations
from backend.app.services.assets import provider_management as provider_management_operations
from backend.app.services.assets import refresh as refresh_operations
from backend.app.services.assets import search as search_operations
from backend.app.services.assets.base import AssetSourceError, AssetSourceProvider
from backend.app.services.assets.core import _asset_current_cache, _asset_history_cache, _asset_metadata_cache, _run_provider_in_thread, _search_query_cache, _search_result_cache
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.plugin_settings.fields import PluginSettingField, SettingOption, SettingScope, SettingType, env_name
from backend.test_scripts.test_utils import print_section, print_success

# ============================================================================
# FIXTURES — clear core caches before each test
# ============================================================================


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear all core caches before each test."""
    caches = (
        _asset_history_cache,
        _asset_current_cache,
        _asset_metadata_cache,
        _search_query_cache,
        _search_result_cache,
    )
    for cache in caches:
        cache.clear()
    yield
    for cache in caches:
        cache.clear()


# ============================================================================
# Canonical Modules
# ============================================================================


@pytest.mark.parametrize(
    ("operation_module", "core_object_names"),
    [
        (metadata_operations, ("_asset_metadata_cache", "_run_provider_in_thread")),
        (
            refresh_operations,
            (
                "_asset_history_cache",
                "_asset_current_cache",
                "_run_provider_in_thread",
            ),
        ),
        (
            search_operations,
            (
                "_search_query_cache",
                "_search_result_cache",
                "_run_provider_in_thread",
            ),
        ),
        (
            provider_management_operations,
            (
                "_asset_history_cache",
                "_asset_current_cache",
                "_run_provider_in_thread",
            ),
        ),
        (price_query_operations, ("_asset_current_cache", "_run_provider_in_thread")),
        (currency_change_operations, ("_asset_history_cache", "_asset_current_cache")),
    ],
    ids=[
        "metadata",
        "refresh",
        "search",
        "provider-management",
        "price-query",
        "currency-change",
    ],
)
def test_operation_modules_share_canonical_core_objects(operation_module, core_object_names):
    """Operation modules must resolve caches and the thread boundary from core."""
    assert operation_module.core is asset_source_core
    for object_name in core_object_names:
        assert getattr(operation_module.core, object_name) is getattr(asset_source_core, object_name)


def _registered_provider_instances(registry):
    provider_codes = [item["code"] for item in registry.list_providers()]
    instances = [registry.get_provider_instance(code) for code in provider_codes]
    assert instances, "Asset provider discovery returned no providers"
    assert all(instance is not None for instance in instances)
    return instances


def test_normal_and_cold_discovery_keep_provider_base_identity():
    """Warm and fresh-interpreter discovery must use one provider base class."""
    AssetProviderRegistry.auto_discover()
    normal_instances = _registered_provider_instances(AssetProviderRegistry)
    assert all(isinstance(provider, AssetSourceProvider) for provider in normal_instances)

    cold_probe = textwrap.dedent("""
        from backend.app.services.assets.registry import AssetProviderRegistry

        AssetProviderRegistry.auto_discover()

        from backend.app.services.assets.base import AssetSourceProvider

        providers = [
            AssetProviderRegistry.get_provider_instance(item["code"])
            for item in AssetProviderRegistry.list_providers()
        ]
        assert providers
        assert all(isinstance(provider, AssetSourceProvider) for provider in providers)
        """)
    completed = subprocess.run(
        [sys.executable, "-c", cold_probe],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, "Cold AssetProviderRegistry discovery failed without touching the parent " f"registry:\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"


def test_concrete_history_method_has_exactly_one_ohlc_guard():
    """A concrete history implementation must not lose or duplicate its guard."""
    provider = AssetProviderRegistry.get_provider_instance("mockprov")
    assert provider is not None

    current = type(provider).get_history_value
    seen = set()
    guard_count = 0
    while current is not None:
        current_id = id(current)
        assert current_id not in seen, "Cycle detected in get_history_value wrappers"
        seen.add(current_id)
        guard_count += int(getattr(current, "_ohlc_guarded", False))
        current = getattr(current, "__wrapped__", None)

    assert guard_count == 1


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

    async def test_worker_thread_does_not_keep_closed_event_loop(self, monkeypatch):
        """J-5: the thread that ran a provider must be left without a current event loop, as it was found.

        _sync_runner makes a new loop current in its executor thread and closes it on the way out: unless it also
        unsets it, as asyncio.Runner.close() does, every later asyncio.get_event_loop() in that pooled thread gets
        the closed loop (J saw an aiosqlite connection collected there die with "Event loop is closed"). The
        default executor has many threads, so asyncio.to_thread is pinned, for this one call only, to a private
        single-worker executor: both probes run in the very thread that ran the provider, and the test loop's
        default executor is never involved.
        """
        print_section("_run_provider_in_thread: no closed loop left in the worker thread (J-5)")

        pinned = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pinned-provider")

        async def to_pinned_thread(func, /, *args, **kwargs):
            # asyncio.to_thread() itself, on the pinned executor instead of the loop's default one.
            call = functools.partial(contextvars.copy_context().run, func, *args, **kwargs)
            return await asyncio.get_running_loop().run_in_executor(pinned, call)

        def current_loop_here():
            # Off the main thread get_event_loop() never creates a loop: it raises when none is set.
            try:
                return threading.current_thread(), asyncio.get_event_loop()
            except RuntimeError:
                return threading.current_thread(), None

        provider_threads = []

        async def provider():
            provider_threads.append(threading.current_thread())
            return "priced"

        test_loop = asyncio.get_running_loop()
        try:
            thread_before, loop_before = await test_loop.run_in_executor(pinned, current_loop_here)
            assert loop_before is None, f"precondition: the fresh {thread_before.name} already has {loop_before!r} as its current loop"

            with monkeypatch.context() as patch:
                patch.setattr(asset_source_core.asyncio, "to_thread", to_pinned_thread)
                assert await _run_provider_in_thread(provider, timeout=5.0) == "priced"

            thread_after, loop_after = await test_loop.run_in_executor(pinned, current_loop_here)
        finally:
            pinned.shutdown(wait=True)

        assert provider_threads == [thread_before], f"the provider ran in {provider_threads}, not in the pinned {thread_before.name}"
        assert thread_after is thread_before, f"the second probe ran in {thread_after.name}, not in the pinned {thread_before.name}"
        assert loop_after is None, f"{thread_after.name} still has {loop_after!r} as its current loop after _run_provider_in_thread() returned: every later asyncio.get_event_loop() in that pooled thread gets it"
        print_success(f"{thread_after.name} ran the provider and was left with no current event loop")


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

    @pytest.mark.asyncio
    async def test_probe_bypasses_all_core_caches_and_executes_each_operation_through_thread_boundary(self, monkeypatch):
        """Seeded cache data cannot replace any live probe operation."""
        print_section("Probe: bypasses all caches through thread boundary")

        class FakeProbeProvider:
            def __init__(self):
                self.validated_params = []
                self.current_calls = []
                self.history_calls = []
                self.metadata_calls = []

            def validate_params(self, params):
                self.validated_params.append(params)

            def get_asset_url(self, identifier, identifier_type=None, provider_params=None):
                return f"https://probe.invalid/{identifier}"

            async def get_current_value(self, identifier, identifier_type, provider_params):
                self.current_calls.append((identifier, identifier_type, provider_params))
                return FACurrentValue(
                    value=Decimal("123.45"),
                    currency="EUR",
                    as_of_date=date(2026, 9, 11),
                    source="fake-probe",
                )

            async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
                self.history_calls.append((identifier, identifier_type, provider_params, start_date, end_date))
                return FAHistoricalData(
                    prices=[
                        FAPricePoint(
                            date=date(2026, 9, 10),
                            close=Decimal("120.25"),
                            currency="EUR",
                        )
                    ],
                    currency="EUR",
                    source="fake-probe",
                )

            async def fetch_asset_metadata(self, identifier, identifier_type, provider_params):
                self.metadata_calls.append((identifier, identifier_type, provider_params))
                return FAAssetPatchItem(
                    asset_id=0,
                    display_name="Fresh provider metadata",
                    currency="EUR",
                )

        provider = FakeProbeProvider()
        monkeypatch.setattr(
            provider_management_operations.AssetProviderRegistry,
            "get_provider_instance",
            classmethod(lambda cls, code, **kwargs: provider),
        )

        boundary_calls = []

        async def fake_run_provider_in_thread(coro_factory, *, timeout):
            boundary_calls.append((coro_factory, timeout))
            return await coro_factory()

        monkeypatch.setattr(asset_source_core, "_run_provider_in_thread", fake_run_provider_in_thread)

        provider_params = None
        config = FAProviderConfigBase(
            provider_code="cache-probe",
            identifier="CACHE-PROBE",
            identifier_type=ProviderInputType.TICKER.value,
            provider_params=provider_params,
        )

        # Each seed has the key the cached path would compute for this config (refresh's for history and current,
        # metadata's, search's for the query "cache-probe"), so a probe that consulted or filled a cache would meet its
        # sentinel. Since CP10 the provider's settings part closes those keys (core.settings_cache_part): "" for this
        # double, which declares no settings, yet still an element of the key. Nothing reads the search-result cache
        # by key, so its seed keeps its shape.
        settings_part = asset_source_core.settings_cache_part(provider)
        seeded_caches = [
            (
                _asset_history_cache,
                ("cache-probe", "CACHE-PROBE", ProviderInputType.TICKER.value, "none", settings_part),
                {"sentinel": "history"},
            ),
            (
                _asset_current_cache,
                ("cache-probe", "CACHE-PROBE", ProviderInputType.TICKER.value, "none", settings_part),
                {"sentinel": "current"},
            ),
            (
                _asset_metadata_cache,
                ("cache-probe", "CACHE-PROBE", ProviderInputType.TICKER.value, settings_part),
                {"sentinel": "metadata"},
            ),
            (
                _search_query_cache,
                ("cache-probe", "cache-probe", settings_part),
                [{"sentinel": "search-query"}],
            ),
            (
                _search_result_cache,
                ("cache-probe", "CACHE-PROBE"),
                {"sentinel": "search-result"},
            ),
        ]
        for cache, key, sentinel in seeded_caches:
            cache.set(key, sentinel)

        response = await AssetSourceManager.probe_provider_config(
            config,
            [
                ProbeOperation.CURRENT_PRICE,
                ProbeOperation.HISTORY,
                ProbeOperation.METADATA,
            ],
        )

        assert provider.validated_params == [provider_params]
        assert provider.current_calls == [("CACHE-PROBE", IdentifierType.TICKER, {})]
        assert provider.metadata_calls == [("CACHE-PROBE", IdentifierType.TICKER, {})]
        assert len(provider.history_calls) == 1
        history_identifier, history_identifier_type, history_params, history_start, history_end = provider.history_calls[0]
        assert history_identifier == "CACHE-PROBE"
        assert history_identifier_type == IdentifierType.TICKER
        assert history_params == {}
        assert history_end - history_start == timedelta(days=7)

        assert len(boundary_calls) == 3
        assert all(callable(coro_factory) for coro_factory, _timeout in boundary_calls)
        assert [timeout for _coro_factory, timeout in boundary_calls] == [15.0, 15.0, 15.0]

        assert response.provider_url == "https://probe.invalid/CACHE-PROBE"
        assert response.current_price is not None
        assert response.current_price.success is True
        assert response.current_price.value == Decimal("123.45")
        assert response.current_price.currency == "EUR"
        assert response.history is not None
        assert response.history.success is True
        assert response.history.points_count == 1
        assert response.history.date_range == "2026-09-10 → 2026-09-10"
        assert response.history.sample_prices == [{"date": "2026-09-10", "close": 120.25}]
        assert response.metadata is not None
        assert response.metadata.success is True
        assert response.metadata.patch_data["display_name"] == "Fresh provider metadata"
        assert response.metadata.patch_data["currency"] == "EUR"

        for cache, key, sentinel in seeded_caches:
            cached, ok = cache.get(key)
            assert ok is True
            assert cached == sentinel

        print_success("Probe ignored all seeded cache sentinels and used the thread boundary")


# ============================================================================
# Cache keys across the paths: refresh, current price, the drops (X-R27, X-R28)
# ============================================================================
#
# Two paths fill the history and current-value caches, the refresh (refresh.py) and the current-price path
# (price_query.py, behind /assets/prices/current), and two drop entries from them: the currency-change wipe
# (currency_change.py) and a parametric provider's assignment change (provider_management.py). Each of the four builds
# its key by hand. The refresh's key is the canonical one: (provider_code, identifier, str(identifier_type),
# _provider_params_hash(params), settings_cache_part(provider)), every field read from the asset's provider assignment.
#
# - X-R27: the wipe reads provider_code, provider_params, identifier and identifier_type from Asset, which has none of
#   them (they live on AssetProviderAssignment). The AttributeError is caught and logged as "cache invalidation
#   skipped": a wipe never drops anything.
# - X-R28: the current-price path keys _asset_current_cache without the params hash. Assignments that differ only in
#   their params share one current value, which that path also stores as the other asset's price for today; no drop
#   reaches what that path cached, and it never shares an entry with the refresh.
#
# In process, never on the lane: each test gets a private SQLite file (tmp_path, create_all) in place of the process's
# engine, so every session of the services under test, the refresh's persist sessions and the plugin-settings read
# included, reaches that file and nothing of the lane's database. The provider is a double the asset registry hands out
# for a code of the test's own: no network, every call recorded. What is asserted is behaviour, the provider's calls and
# the value each path answers, never a key built here; the one key read is the key the current-price path itself wrote
# (_record_current_cache_keys). _clear_caches empties the core caches around every test.

_INVALIDATION_SKIPPED = "wipe_market_data: cache invalidation skipped"
_REGION_PRICES = {"eu": Decimal("10"), "us": Decimal("20")}

# The two shapes of an assignment: an identifier the user typed, and none at all: AUTO_GENERATED, which
# bulk_assign_providers stores as NULL. The second is scheduled_investment's shape: today every such assignment of one
# provider shares the current-price path's key, (code, None, "AUTO_GENERATED", settings part), whatever its params. A
# drop must reach the entries of both shapes, keyed as the paths that filled them key them.
_ASSIGNMENT_SHAPES = [
    pytest.param(ProviderInputType.TICKER, True, id="ticker"),
    pytest.param(ProviderInputType.AUTO_GENERATED, False, id="auto-generated-without-identifier"),
]


@dataclass
class _Quotes:
    """What the provider double of one test answers, and every call it got."""

    code: str
    kind: FAProviderKind = FAProviderKind.ONLINE_SCRAPER
    price: Decimal = Decimal("100")
    currency: str = "USD"
    current_calls: list = field(default_factory=list)
    history_calls: list = field(default_factory=list)


class _QuoteDouble(AssetSourceProvider):
    """The provider of the cache-key tests: never on the network, every call recorded in its ``_Quotes``.

    The current value is ``provider_params["price"]`` when the params name one, else ``quotes.price``, in
    ``quotes.currency``, as of today; the history is that price on every day of the range asked. It declares no setting:
    the settings part of its keys is "".
    """

    test_only = True

    def __init__(self, quotes: _Quotes):
        self.quotes = quotes

    @property
    def provider_code(self) -> str:
        return self.quotes.code

    @property
    def provider_name(self) -> str:
        return "Cache-key test double"

    @property
    def provider_kind(self) -> FAProviderKind:
        return self.quotes.kind

    @property
    def test_cases(self) -> list[dict]:
        return []

    @property
    def test_search_query(self) -> str | None:
        return None

    def validate_params(self, params: dict | None) -> None:
        """Any params will do."""

    def _price(self, provider_params: dict | None) -> Decimal:
        return Decimal(str((provider_params or {}).get("price", self.quotes.price)))

    async def get_current_value(self, identifier, identifier_type, provider_params=None) -> FACurrentValue:
        self.quotes.current_calls.append((identifier, dict(provider_params or {})))
        return FACurrentValue(value=self._price(provider_params), currency=self.quotes.currency, as_of_date=date.today(), source=self.provider_code)

    async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date) -> FAHistoricalData:
        self.quotes.history_calls.append((identifier, start_date, end_date))
        price = self._price(provider_params)
        days = [start_date + timedelta(days=offset) for offset in range((end_date - start_date).days + 1)]
        return FAHistoricalData(prices=[FAPricePoint(date=day, close=price, currency=self.quotes.currency) for day in days], currency=self.quotes.currency, source=self.provider_code)


class _RegionQuoteDouble(_QuoteDouble):
    """The double with one plain system setting, ``region``: its current value is 10 in ``eu``, 20 in ``us``."""

    settings_fields = (
        PluginSettingField(
            key="region",
            type=SettingType.SELECT,
            scope=SettingScope.SYSTEM,
            label="Region (testing)",
            default="eu",
            options=(SettingOption("eu", "Europe"), SettingOption("us", "United States")),
        ),
    )

    def _price(self, provider_params: dict | None) -> Decimal:
        return _REGION_PRICES[self.settings.get("region")]


def _hand_out(monkeypatch: pytest.MonkeyPatch, double: type[_QuoteDouble] = _QuoteDouble) -> _Quotes:
    """The asset registry hands out a new ``double`` for a code of this test's own, and its own providers otherwise."""
    quotes = _Quotes(code=f"xr_keys_{uuid.uuid4().hex[:12]}")
    original = AssetProviderRegistry.get_provider_instance

    def get_provider_instance(_cls, code, **kwargs):
        return double(quotes) if code == quotes.code else original(code, **kwargs)

    monkeypatch.setattr(AssetProviderRegistry, "get_provider_instance", classmethod(get_provider_instance))
    return quotes


@pytest.fixture
def quotes(monkeypatch: pytest.MonkeyPatch) -> _Quotes:
    """The provider double of this test (``_QuoteDouble``), behind a code of its own."""
    return _hand_out(monkeypatch)


@pytest_asyncio.fixture
async def private_engine(tmp_path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole schema, as the process's engine for the test; disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'cache_keys.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        monkeypatch.setattr(db_session, "async_engine", engine)
        yield engine
    finally:
        await engine.dispose()


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


async def _new_asset(
    engine: AsyncEngine,
    quotes: _Quotes | None = None,
    *,
    identifier: str | None = None,
    identifier_type: ProviderInputType = ProviderInputType.TICKER,
    params: str | None = None,
    prices: tuple[tuple[date, Decimal], ...] = (),
) -> int:
    """A USD asset of this test, assigned to the double of ``quotes`` (none when ``quotes`` is None), with ``prices``.

    ``params`` is the assignment's ``provider_params`` as stored: JSON text.
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        asset = Asset(display_name=_unique("X-R cache keys"), currency="USD", asset_type=AssetType.STOCK)
        session.add(asset)
        await session.flush()
        if quotes is not None:
            session.add(AssetProviderAssignment(asset_id=asset.id, provider_code=quotes.code, identifier=identifier, identifier_type=identifier_type, provider_params=params))
        for day, close in prices:
            session.add(PriceHistory(asset_id=asset.id, date=day, close=close, currency="USD", source_plugin_key="test"))
        await session.commit()
        return asset.id


async def _twin_assets(engine: AsyncEngine, quotes: _Quotes, identifier_type: ProviderInputType, has_identifier: bool) -> tuple[int, int]:
    """Two assets assigned alike, one provider code, identifier and input type, but for their params: price 11 and 22."""
    identifier = _unique("XR28") if has_identifier else None
    first = await _new_asset(engine, quotes, identifier=identifier, identifier_type=identifier_type, params=json.dumps({"price": "11"}))
    second = await _new_asset(engine, quotes, identifier=identifier, identifier_type=identifier_type, params=json.dumps({"price": "22"}))
    return first, second


async def _current_price(engine: AsyncEngine, asset_id: int) -> FACurrentPriceItem:
    """The current-price path (``get_current_prices_bulk``) for one asset: its item."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        (item,) = await AssetSourceManager.get_current_prices_bulk([asset_id], session)
    return item


async def _refresh(engine: AsyncEngine, asset_id: int, start: date, end: date) -> FARefreshResult:
    """The refresh (``bulk_refresh_prices``) of one asset from ``start`` to ``end``: its result."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        response = await AssetSourceManager.bulk_refresh_prices([FARefreshItem(asset_id=asset_id, date_range=SyncDateRangeModel(start=start, end=end))], session)
    (result,) = response.results
    return result


async def _wipe(engine: AsyncEngine, asset_id: int) -> dict:
    """The currency-change wipe of one asset, not a dry run: its summary."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await AssetSourceManager.wipe_market_data_for_currency_change(asset_id, session, dry_run=False)


async def _stored_close(engine: AsyncEngine, asset_id: int, day: date) -> Decimal | None:
    async with AsyncSession(engine) as session:
        close = (await session.execute(select(PriceHistory.close).where(PriceHistory.asset_id == asset_id, PriceHistory.date == day))).scalar_one_or_none()
    return None if close is None else Decimal(str(close))


async def _stored_days(engine: AsyncEngine, asset_id: int) -> list[date]:
    async with AsyncSession(engine) as session:
        rows = await session.execute(select(PriceHistory.date).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date))
        return list(rows.scalars())


def _calls(quotes: _Quotes) -> tuple[int, int]:
    """How many times the double was asked for a history, and for a current value."""
    return len(quotes.history_calls), len(quotes.current_calls)


def _record_current_cache_keys(monkeypatch: pytest.MonkeyPatch) -> list:
    """From now on, the key of every value stored in ``_asset_current_cache``, in order; each value is still stored."""
    written: list = []
    store = _asset_current_cache.set

    def recording_set(key, value, *, ttl=None):
        written.append(key)
        store(key, value, ttl=ttl)

    monkeypatch.setattr(_asset_current_cache, "set", recording_set)
    return written


@pytest.mark.asyncio
class TestAssetCacheKeysAcrossPaths:
    """One assignment, one key: the refresh, the current-price path and both drops agree on it (X-R27, X-R28).

    The ``test_xr27_*`` and ``test_xr28_*`` cases are red until the fix (one key function in core.py, used in the four
    places); the ``test_guard_*`` cases are green today and must stay green.
    """

    # -- X-R27: the currency-change wipe never drops anything -----------------------------------------------------------

    @pytest.mark.parametrize(("identifier_type", "has_identifier"), _ASSIGNMENT_SHAPES)
    async def test_xr27_wipe_drops_the_history_and_current_value_the_refresh_cached(self, private_engine, quotes, identifier_type, has_identifier):
        """X-R27: after the wipe, the next refresh asks the provider again for both the history and the current value.

        Today the wipe looks for the provider fields on ``Asset``, which has none: nothing is dropped, and the refresh
        after the wipe is answered from the caches with what was fetched before it (for up to 15 and 2 minutes).
        """
        print_section(f"X-R27: the currency-change wipe drops the refresh's entries ({identifier_type.value})")
        identifier = _unique("XR27") if has_identifier else None
        asset_id = await _new_asset(private_engine, quotes, identifier=identifier, identifier_type=identifier_type)
        today = date.today()
        start = today - timedelta(days=3)

        await _refresh(private_engine, asset_id, start, today)
        assert _calls(quotes) == (1, 1), f"precondition: the first refresh asks the provider once for each, got (history, current) = {_calls(quotes)}"
        await _refresh(private_engine, asset_id, start, today)
        assert _calls(quotes) == (1, 1), f"precondition: a second refresh is answered from the caches, got (history, current) = {_calls(quotes)}"

        await _wipe(private_engine, asset_id)
        await _refresh(private_engine, asset_id, start, today)

        assert _calls(quotes) == (2, 2), f"after the currency-change wipe the refresh was still answered from the caches, provider asked (history, current) = {_calls(quotes)} instead of (2, 2): the wipe did not drop the history and current value the refresh cached for this assignment"
        print_success("the refresh after the wipe asked the provider again for both")

    @pytest.mark.parametrize("assigned", [pytest.param(True, id="assigned"), pytest.param(False, id="unassigned")])
    async def test_xr27_wipe_logs_no_cache_invalidation_skipped_warning(self, private_engine, quotes, assigned):
        """X-R27: a wipe that is not a dry run logs no "cache invalidation skipped", provider assignment or not.

        Today ``Asset`` has no ``provider_code``: every such wipe raises the AttributeError, catches it and logs the
        warning, also for an asset without a provider assignment, before anything could tell there is none.
        """
        print_section(f"X-R27: no 'cache invalidation skipped' warning ({'assigned' if assigned else 'unassigned'} asset)")
        asset_id = await _new_asset(private_engine, quotes if assigned else None, identifier=_unique("XR27W"))

        with capture_logs() as events:
            summary = await _wipe(private_engine, asset_id)

        assert summary["dry_run"] is False, "precondition: the destructive branch, where the caches are dropped, ran"
        skipped = [event for event in events if event.get("event") == _INVALIDATION_SKIPPED]
        assert not skipped, f"the currency-change wipe logged {skipped!r}"
        print_success("no 'cache invalidation skipped' warning")

    async def test_guard_wipe_of_an_asset_without_provider_succeeds(self, private_engine):
        """Guard: an asset without a provider assignment: the wipe does not fail, and its prices are gone."""
        print_section("Guard: the currency-change wipe of an asset without a provider")
        today = date.today()
        asset_id = await _new_asset(private_engine, prices=((today - timedelta(days=2), Decimal("10")), (today - timedelta(days=1), Decimal("11"))))

        summary = await _wipe(private_engine, asset_id)

        assert (summary["prices"], summary["dry_run"]) == (2, False)
        assert await _stored_days(private_engine, asset_id) == []
        print_success("wiped, nothing raised")

    # -- X-R28: the current-price path keys without the provider params ------------------------------------------------

    @pytest.mark.parametrize(("identifier_type", "has_identifier"), _ASSIGNMENT_SHAPES)
    async def test_xr28_assignments_differing_only_in_params_get_each_its_own_current_value(self, private_engine, quotes, identifier_type, has_identifier):
        """X-R28: same provider code, identifier and input type, other params: each asset its own current value.

        Today the current-price path keys ``_asset_current_cache`` without the params, so the second asset is answered,
        for up to 2 minutes, the value cached for the first. Without an identifier (AUTO_GENERATED, scheduled_investment's
        shape) that holds for every assignment of the provider.
        """
        print_section(f"X-R28: assignments differing only in params, each its own current value ({identifier_type.value})")
        first, second = await _twin_assets(private_engine, quotes, identifier_type, has_identifier)

        first_item = await _current_price(private_engine, first)
        second_item = await _current_price(private_engine, second)

        assert first_item.value == Decimal("11"), f"precondition: the first asset gets its own value, got {first_item.value}"
        assert second_item.value == Decimal("22"), f"the second asset (params price=22) was answered {second_item.value}, the current value cached for the first (price=11): the current-price path keys _asset_current_cache without the provider params"
        assert [params for _identifier, params in quotes.current_calls] == [{"price": "11"}, {"price": "22"}]
        print_success("11 and 22, one provider call each")

    @pytest.mark.parametrize(("identifier_type", "has_identifier"), _ASSIGNMENT_SHAPES)
    async def test_xr28_current_price_path_stores_each_assets_own_quote_as_todays_close(self, private_engine, quotes, identifier_type, has_identifier):
        """X-R28: the current-price path writes, as each asset's close for today, that asset's own quote.

        The path stores every provider item dated today, cache hits included (F.2/F.3 in ``get_current_prices_bulk``).
        Today the second asset is answered the first one's cached value, and 11 is written as its open, high, low and
        close for today: a later right quote replaces the close, but F.3 keeps 11 as the day's open and low.
        """
        print_section(f"X-R28: today's stored close of each asset is its own quote ({identifier_type.value})")
        first, second = await _twin_assets(private_engine, quotes, identifier_type, has_identifier)
        today = date.today()

        await _current_price(private_engine, first)
        await _current_price(private_engine, second)

        first_close = await _stored_close(private_engine, first, today)
        second_close = await _stored_close(private_engine, second, today)
        assert first_close == Decimal("11"), f"precondition: the current-price path stored the first asset's quote as its close for today, got {first_close}"
        assert second_close == Decimal("22"), f"the second asset's close for today (its params price=22) was stored as {second_close}, the current value cached for the first asset (price=11): the current-price path keys _asset_current_cache without the provider params"
        print_success("today's close: 11 for the first asset, 22 for the second")

    async def test_guard_assignments_configured_alike_share_one_current_value(self, private_engine, quotes):
        """Guard: two assets configured alike (equal params, written in another key order) share one entry."""
        print_section("Guard: assignments configured alike share one current value")
        identifier = _unique("XR28G")
        first = await _new_asset(private_engine, quotes, identifier=identifier, params='{"price": "11", "venue": "XMIL"}')
        second = await _new_asset(private_engine, quotes, identifier=identifier, params='{"venue": "XMIL", "price": "11"}')

        first_item = await _current_price(private_engine, first)
        second_item = await _current_price(private_engine, second)

        assert (first_item.value, second_item.value) == (Decimal("11"), Decimal("11"))
        assert len(quotes.current_calls) == 1, f"the second asset, configured as the first, asked the provider again ({len(quotes.current_calls)} calls) instead of sharing the first one's entry"
        print_success("one provider call for both")

    async def test_xr28_wipe_drops_the_current_value_the_current_price_path_cached(self, private_engine, quotes):
        """X-R28: after the wipe, the current-price path asks the provider again instead of answering its old entry.

        Today the wipe drops nothing (X-R27); and a wipe that built the refresh's key would still miss this entry, which
        the current-price path stores under a key of its own, without the params hash.
        """
        print_section("X-R28: the currency-change wipe drops the current-price path's entry")
        asset_id = await _new_asset(private_engine, quotes, identifier=_unique("XR28W"))
        quotes.price = Decimal("11")
        before = await _current_price(private_engine, asset_id)
        again = await _current_price(private_engine, asset_id)
        assert (before.value, again.value, len(quotes.current_calls)) == (Decimal("11"), Decimal("11"), 1), "precondition: the second ask is answered from the entry the first one cached"

        await _wipe(private_engine, asset_id)
        quotes.price = Decimal("12")  # what the provider quotes after the wipe
        after = await _current_price(private_engine, asset_id)

        assert (after.value, len(quotes.current_calls)) == (Decimal("12"), 2), f"after the currency-change wipe the current-price path answered {after.value} with {len(quotes.current_calls)} provider call(s) in all: the value it cached before the wipe (11) was not dropped"
        print_success("the provider was asked again after the wipe")

    @pytest.mark.parametrize(("identifier_type", "has_identifier"), _ASSIGNMENT_SHAPES)
    async def test_xr28_parametric_params_change_drops_the_current_value_the_current_price_path_cached(self, private_engine, quotes, monkeypatch, identifier_type, has_identifier):
        """X-R28: a parametric provider's params change drops the entry the current-price path cached for the old params.

        provider_management drops the refresh's key of the old assignment, and the current-price path wrote its value
        under a key without the params hash, which that drop never reaches.
        """
        print_section(f"X-R28: the parametric params change drops the current-price path's entry ({identifier_type.value})")
        quotes.kind = FAProviderKind.PARAMETRIC_GENERATION
        identifier = _unique("XR28P") if has_identifier else None
        asset_id = await _new_asset(private_engine, quotes, identifier=identifier, identifier_type=identifier_type, params=json.dumps({"price": "11"}))
        written = _record_current_cache_keys(monkeypatch)

        before = await _current_price(private_engine, asset_id)
        assert (before.value, len(written)) == (Decimal("11"), 1), f"precondition: the current-price path cached one value, 11; got {before.value} and {len(written)} key(s)"
        (key,) = written
        assert _asset_current_cache.get(key)[1], "precondition: the entry is cached"

        async with AsyncSession(private_engine, expire_on_commit=False) as session:
            change = FAProviderAssignmentItem(asset_id=asset_id, provider_code=quotes.code, identifier=identifier or "", identifier_type=identifier_type.value, provider_params={"price": "22"})
            await AssetSourceManager.bulk_assign_providers([change], session)

        assert not _asset_current_cache.get(key)[1], f"the parametric params change left in _asset_current_cache the current value the current-price path cached for the old params (key {key!r})"
        after = await _current_price(private_engine, asset_id)
        assert after.value == Decimal("22"), f"after the params change the current-price path answered {after.value}, not the new params' 22"
        print_success("the old entry is gone; the new params' value is answered")

    @pytest.mark.parametrize("first_path", [pytest.param("refresh", id="refresh-first"), pytest.param("current-price", id="current-price-first")])
    async def test_xr28_refresh_and_current_price_path_share_one_current_value(self, private_engine, quotes, first_path):
        """X-R28: within the TTL, the current value one path cached answers the other for the same assignment.

        Today the two paths key the same assignment differently (five elements, four), so the second asks again.
        """
        print_section(f"X-R28: the refresh and the current-price path share one entry ({first_path} first)")
        asset_id = await _new_asset(private_engine, quotes, identifier=_unique("XR28S"), params=json.dumps({"price": "11"}))
        today = date.today()

        if first_path == "refresh":
            first_label, second_label = "refresh", "current-price path"
            await _refresh(private_engine, asset_id, today, today)
            assert len(quotes.current_calls) == 1, f"precondition: the refresh asked the provider once, got {len(quotes.current_calls)}"
            assert (await _current_price(private_engine, asset_id)).value == Decimal("11")
        else:
            first_label, second_label = "current-price path", "refresh"
            item = await _current_price(private_engine, asset_id)
            assert (item.value, len(quotes.current_calls)) == (Decimal("11"), 1), "precondition: the current-price path asked the provider once"
            await _refresh(private_engine, asset_id, today, today)

        assert len(quotes.current_calls) == 1, f"the {second_label} asked the provider again ({len(quotes.current_calls)} calls) instead of answering the current value the {first_label} had just cached"
        print_success("one provider call for both paths")

    @pytest.mark.parametrize("path", ["current-price", "refresh"])
    async def test_guard_other_provider_settings_are_not_answered_from_the_old_entry(self, private_engine, monkeypatch, path):
        """Guard: the provider's settings are part of the key (``settings_cache_part``) on both paths.

        After a change of a system setting the path asks the provider again, and stores the value of the new settings.
        """
        print_section(f"Guard: other provider settings, other entry ({path})")
        quotes = _hand_out(monkeypatch, _RegionQuoteDouble)
        variable = env_name("asset", quotes.code, "region")
        monkeypatch.setenv(variable, "eu")
        asset_id = await _new_asset(private_engine, quotes, identifier=_unique("XRSET"))
        today = date.today()

        async def current_value() -> Decimal | None:
            if path == "current-price":
                return (await _current_price(private_engine, asset_id)).value
            await _refresh(private_engine, asset_id, today, today)
            return await _stored_close(private_engine, asset_id, today)

        assert await current_value() == Decimal("10"), "precondition: region eu prices 10"
        monkeypatch.setenv(variable, "us")
        value = await current_value()

        assert (value, len(quotes.current_calls)) == (Decimal("20"), 2), f"with region us the {path} gave {value} after {len(quotes.current_calls)} provider call(s): it was answered the entry cached under the old settings"
        print_success("10 under eu, 20 under us")
