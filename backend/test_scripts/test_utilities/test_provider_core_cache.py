"""
Test: Provider Core Cache & Thread Isolation.

Tests the canonical asset-source core and legacy facade contracts:
- _run_provider_in_thread(): thread isolation, timeout, exception propagation
- _asset_history_cache: smart range with per-date granularity
- _asset_current_cache: simple TTL cache for current values
- _asset_metadata_cache: simple TTL cache for metadata
- _search_query_cache: Layer 2 exact query cache
- _search_result_cache: Layer 1 individual-result cache
- probe_provider_config bypasses cache
"""

import asyncio
import subprocess
import sys
import textwrap
import time
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.app.db import IdentifierType
from backend.app.db.models import ProviderInputType
from backend.app.schemas.assets import FAAssetPatchItem, FACurrentValue, FAHistoricalData, FAPricePoint
from backend.app.schemas.provider import FAProviderConfigBase, ProbeOperation
from backend.app.services import asset_source as legacy_asset_source
from backend.app.services import asset_sources as canonical_asset_sources
from backend.app.services.asset_source import (
    AssetCRUDService,
    AssetSearchService,
    AssetSourceError,
    AssetSourceManager,
    AssetSourceProvider,
)
from backend.app.services.asset_sources import core as asset_source_core
from backend.app.services.asset_sources import metadata as metadata_operations
from backend.app.services.asset_sources import price_query as price_query_operations
from backend.app.services.asset_sources import price_store as price_store_operations
from backend.app.services.asset_sources import provider_management as provider_management_operations
from backend.app.services.asset_sources import refresh as refresh_operations
from backend.app.services.asset_sources import search as search_operations
from backend.app.services.asset_sources.core import (
    AssetSourceError as CanonicalAssetSourceError,
)
from backend.app.services.asset_sources.core import (
    AssetSourceProvider as CanonicalAssetSourceProvider,
)
from backend.app.services.asset_sources.core import (
    _asset_current_cache,
    _asset_history_cache,
    _asset_metadata_cache,
    _run_provider_in_thread,
    _search_query_cache,
    _search_result_cache,
)
from backend.app.services.asset_sources.crud import AssetCRUDService as CanonicalAssetCRUDService
from backend.app.services.asset_sources.manager import AssetSourceManager as CanonicalAssetSourceManager
from backend.app.services.asset_sources.search import AssetSearchService as CanonicalAssetSearchService
from backend.app.services.provider_registry import AssetProviderRegistry
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
# Canonical Modules & Legacy Compatibility
# ============================================================================


@pytest.mark.parametrize(
    ("symbol_name", "legacy_symbol", "canonical_symbol"),
    [
        ("AssetSourceProvider", AssetSourceProvider, CanonicalAssetSourceProvider),
        ("AssetSourceError", AssetSourceError, CanonicalAssetSourceError),
        ("AssetSourceManager", AssetSourceManager, CanonicalAssetSourceManager),
        ("AssetCRUDService", AssetCRUDService, CanonicalAssetCRUDService),
        ("AssetSearchService", AssetSearchService, CanonicalAssetSearchService),
    ],
)
def test_legacy_and_canonical_public_symbols_share_identity(symbol_name, legacy_symbol, canonical_symbol):
    """The legacy facade and canonical package must expose the same objects."""
    assert legacy_symbol is canonical_symbol
    assert getattr(legacy_asset_source, symbol_name) is canonical_symbol
    assert getattr(canonical_asset_sources, symbol_name) is canonical_symbol


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
        (price_store_operations, ("_asset_history_cache", "_asset_current_cache")),
    ],
    ids=[
        "metadata",
        "refresh",
        "search",
        "provider-management",
        "price-query",
        "price-store",
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
    assert all(isinstance(provider, CanonicalAssetSourceProvider) for provider in normal_instances)

    cold_probe = textwrap.dedent("""
        from backend.app.services.provider_registry import AssetProviderRegistry

        AssetProviderRegistry.auto_discover()

        from backend.app.services.asset_source import AssetSourceProvider as LegacyProvider
        from backend.app.services.asset_sources.core import AssetSourceProvider as CanonicalProvider

        providers = [
            AssetProviderRegistry.get_provider_instance(item["code"])
            for item in AssetProviderRegistry.list_providers()
        ]
        assert providers
        assert LegacyProvider is CanonicalProvider
        assert all(isinstance(provider, CanonicalProvider) for provider in providers)
        assert all(isinstance(provider, LegacyProvider) for provider in providers)
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

        seeded_caches = [
            (
                _asset_history_cache,
                ("cache-probe", "CACHE-PROBE", ProviderInputType.TICKER.value, "none"),
                {"sentinel": "history"},
            ),
            (
                _asset_current_cache,
                ("cache-probe", "CACHE-PROBE", ProviderInputType.TICKER.value, "none"),
                {"sentinel": "current"},
            ),
            (
                _asset_metadata_cache,
                ("cache-probe", "CACHE-PROBE", ProviderInputType.TICKER.value),
                {"sentinel": "metadata"},
            ),
            (
                _search_query_cache,
                ("cache-probe", "cache-probe"),
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
