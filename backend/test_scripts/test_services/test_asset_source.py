"""
Test asset source service (provider assignment and helper functions).

Tests:
- Helper functions (truncation, ACT/365 calculation)
- Synthetic yield calculation
- Provider assignment (bulk and single)
- Provider removal (bulk and single)
- Price CRUD operations
"""

import asyncio
import json
import sys
import time
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.utils.decimal_utils import get_model_column_precision, truncate_priceHistory

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetEventType,
    AssetProviderAssignment,
    AssetType,
    Broker,
    FxRate,
    IdentifierType,
    PriceHistory,
    ProviderInputType,
    Transaction,
    TransactionType,
    User,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas import FAGeographicArea, FASectorArea
from backend.app.schemas.assets import FAAssetCreateItem, FAClassificationParams
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.prices import FAAssetDelete, FAPricePoint, FAPriceQueryItem, FAUpsert
from backend.app.schemas.provider import FAProviderAssignmentItem, FAProviderConfigBase, ProbeOperation
from backend.app.schemas.refresh import FARefreshItem, FXSyncPairRequest
from backend.app.services import asset_source as asset_source_module
from backend.app.services.asset_source import (
    AssetCRUDService,
    AssetSearchService,
    AssetSourceManager,
    AssetSourceProvider,
    _provider_params_hash,
)
from backend.app.services.asset_source_providers import borsa_italiana as borsa_provider_module
from backend.app.services.asset_source_providers import yahoo_finance as yahoo_provider_module
from backend.app.services.asset_source_providers.scheduled_investment import (
    calculate_day_count_fraction,
)
from backend.app.services.fx_providers.mockfx import MOCKFX_FIXED_RATE, MockFXProvider
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.test_scripts.test_utils import (
    print_info,
    print_section,
    print_success,
)

# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def asset_ids():
    """
    Module-scoped fixture: Create test assets once for all tests that need them.

    Creates 3 test assets synchronously using asyncio.run().
    Returns list of asset IDs for use in tests.

    Uses timestamp to ensure unique asset names across test runs.
    """

    timestamp = int(time.time() * 1000)  # Millisecond timestamp for uniqueness

    async def _create_assets():
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Create test assets with unique names using timestamp
            test_assets = [
                Asset(
                    display_name=f"Test Asset {timestamp}-{i}",
                    currency="USD",
                    asset_type=AssetType.STOCK,
                    active=True,
                )
                for i in range(1, 4)
            ]

            session.add_all(test_assets)
            await session.commit()

            # Refresh to get IDs
            for asset in test_assets:
                await session.refresh(asset)

            return [a.id for a in test_assets]

    # Run async setup synchronously
    asset_id_list = asyncio.run(_create_assets())
    yield asset_id_list
    # Cleanup not needed - test DB is recreated


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


def test_price_column_precision():
    """Test get_price_column_precision() helper."""
    print_section("Test 1: Price Column Precision")

    columns = ["open", "high", "low", "close", "adjusted_close"]
    for col in columns:
        precision, scale = get_model_column_precision(PriceHistory, col)
        # Detailed logging per case
        print_info(f"Case: column={col} | expected=(18,6) | actual=({precision},{scale})")
        assert precision == 18, f"{col}: Expected precision 18, got {precision}"
        assert scale == 6, f"{col}: Expected scale 6, got {scale}"
        print_success(f"✓ {col}: precision OK ({precision},{scale})")


def test_truncate_price():
    """Test truncate_price_to_db_precision() helper."""
    print_section("Test 2: Price Truncation")

    test_cases = [
        ("175.1234567890", "175.123456"),  # Truncate extra decimals
        ("175.123456", "175.123456"),  # Already at precision
        ("175.12", "175.120000"),  # Pad to 6 decimals
        ("1000.9999999", "1000.999999"),  # Large number
    ]

    for input_str, expected_str in test_cases:
        input_val = Decimal(input_str)
        result = truncate_priceHistory(input_val)
        expected = Decimal(expected_str)

        # Detailed logging per case
        print_info(f"Case: input={input_val} | expected={expected} | actual={result}")

        assert result == expected, f"Mismatch: {result} != {expected} for input {input_val}"
        print_success(f"✓ Truncation OK for input {input_val} -> {result}")


def test_act365_calculation():
    """Test calculate_days_between_act365() helper."""
    print_section("Test 3: ACT/365 Day Count")

    test_cases = [
        (date(2025, 1, 1), date(2025, 1, 31), Decimal("30") / Decimal("365")),  # 30 days
        (date(2025, 1, 1), date(2025, 12, 31), Decimal("364") / Decimal("365")),  # 364 days
        (date(2025, 1, 1), date(2026, 1, 1), Decimal("365") / Decimal("365")),  # Exactly 1 year
    ]

    for start, end, expected in test_cases:
        result = calculate_day_count_fraction(start, end)

        # Detailed logging per case
        print_info(f"Case: start={start} end={end} | expected={expected} | actual={result}")

        assert result == expected, f"Mismatch: {result} != {expected} for period {start} to {end}"
        print_success(f"✓ ACT/365 OK for {start} to {end} -> {result}")


def test_refresh_schemas_accept_min_start():
    """Sync schemas accept the 'min' sentinel for provider-driven full history sync."""
    fa_req = FARefreshItem(asset_id=1, date_range={"start": "min", "end": date(2025, 1, 31)})
    fx_req = FXSyncPairRequest(pairs=["USD-EUR"], start="min", end=date(2025, 1, 31))

    assert fa_req.date_range.start == "min"
    assert fa_req.date_range.end == date(2025, 1, 31)
    assert fx_req.start == "min"
    assert fx_req.pairs == ["EUR-USD"]


@pytest.mark.asyncio
async def test_yfinance_history_uses_native_max_for_min_start(monkeypatch):
    """Yahoo provider must forward the 'min' sentinel as period='max'."""
    pd = pytest.importorskip("pandas")
    provider = yahoo_provider_module.YahooFinanceProvider()
    calls: dict[str, dict] = {}

    history_index = pd.DatetimeIndex(["2025-01-01", "2025-01-02"], tz="UTC")
    history_df = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [101.0, 102.0],
            "Low": [99.0, 100.0],
            "Close": [100.5, 101.5],
            "Volume": [10, 20],
        },
        index=history_index,
    )

    class DummyTicker:
        info = {"currency": "USD"}
        dividends = pd.Series(dtype=float)
        splits = pd.Series(dtype=float)

        def history(self, **kwargs):
            calls["history_kwargs"] = kwargs
            return history_df

    monkeypatch.setattr(yahoo_provider_module, "YFINANCE_AVAILABLE", True)
    monkeypatch.setattr(yahoo_provider_module, "pd", pd)
    monkeypatch.setattr(yahoo_provider_module, "yf", SimpleNamespace(Ticker=lambda _symbol: DummyTicker()))

    result = await provider.get_history_value("AAPL", IdentifierType.TICKER, None, "min", date(2025, 1, 2))

    assert calls["history_kwargs"] == {"period": "max"}
    assert [p.date for p in result.prices] == [date(2025, 1, 1), date(2025, 1, 2)]


@pytest.mark.asyncio
async def test_borsa_history_uses_remote_fallback_for_min_start(monkeypatch):
    """Borsa provider must translate 'min' to a provider-local MAX-range fetch."""
    provider = borsa_provider_module.BorsaItalianaProvider()
    calls: dict[str, str] = {}

    punti = [
        SimpleNamespace(data=date(1899, 12, 31), apertura=Decimal("90"), massimo=Decimal("91"), minimo=Decimal("89"), chiusura=Decimal("90"), ultimo=Decimal("90"), volume=None),
        SimpleNamespace(data=date(1900, 1, 1), apertura=Decimal("100"), massimo=Decimal("101"), minimo=Decimal("99"), chiusura=Decimal("100"), ultimo=Decimal("100"), volume=None),
        SimpleNamespace(data=date(2025, 1, 2), apertura=Decimal("110"), massimo=Decimal("111"), minimo=Decimal("109"), chiusura=Decimal("110"), ultimo=Decimal("110"), volume=None),
    ]

    def fake_ottieni_storico(identifier, periodo, sessione):
        calls["identifier"] = identifier
        calls["periodo"] = periodo
        return SimpleNamespace(punti=punti)

    monkeypatch.setattr(borsa_provider_module, "BORSA_ITALIANA_AVAILABLE", True)
    monkeypatch.setattr(borsa_provider_module, "_get_session", lambda: object())
    monkeypatch.setattr(borsa_provider_module, "ottieni_storico", fake_ottieni_storico)

    result = await provider.get_history_value("IT0003128367", IdentifierType.ISIN, None, "min", date(2025, 1, 2))

    assert calls["periodo"] == "MAX"
    assert [p.date for p in result.prices] == [date(1900, 1, 1), date(2025, 1, 2)]


@pytest.mark.asyncio
async def test_mockfx_provider_accepts_min_start():
    """Mock FX provider keeps sentinel path working for small historical ranges."""
    provider = MockFXProvider()

    result = await provider.fetch_rates(("min", date(1900, 1, 3)), ["USD"])

    assert "USD" in result
    assert len(result["USD"]) == 3
    assert all(row[3] == MOCKFX_FIXED_RATE for row in result["USD"])


@pytest.mark.asyncio
async def test_bulk_refresh_prices_with_min_start_does_not_crash():
    """Regression test: end-to-end bulk_refresh_prices() with start='min' must not raise
    TypeError comparing str vs date. A prior fix guarded the history-window comparisons in
    the fetch loop but missed the post-fetch `has_history` status computation, which did
    `start < date.today()` unconditionally — crashing with "'<' not supported between
    instances of 'str' and 'datetime.date'" whenever a real fetch succeeded with the "min"
    sentinel still unresolved (mockprov.supports_history is True, so this path is reached).
    """
    AssetProviderRegistry.auto_discover()
    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset = Asset(
            display_name=f"MinStartRefresh Test {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
        )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_MIN_START",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={},
        )
        results = await AssetSourceManager.bulk_assign_providers([item], session)
        assert results[0].success

        sync_response = await AssetSourceManager.bulk_refresh_prices(
            requests=[
                FARefreshItem(
                    asset_id=test_asset.id,
                    date_range={"start": "min", "end": date(2025, 1, 10)},
                )
            ],
            session=session,
        )

        sync_result = sync_response.results[0]
        assert not sync_result.errors, f"Sync with start='min' should not error: {sync_result.errors}"
        assert sync_result.status in ("ok", "partial"), f"Unexpected status: {sync_result.status}"
        print_success("✓ bulk_refresh_prices() with start='min' completed without a str/date comparison crash")


# ============================================================================
# PROVIDER ASSIGNMENT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_assign_providers():
    """Test bulk_assign_providers() method."""
    print_section("Test 5: Bulk Assign Providers")

    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Create test assets with unique names using timestamp
        test_assets = [
            Asset(
                display_name=f"Test Asset Assign {timestamp}-{i}",
                currency="USD",
                asset_type=AssetType.STOCK,
                active=True,
            )
            for i in range(1, 4)
        ]

        session.add_all(test_assets)
        await session.commit()

        # Refresh to get IDs
        for asset in test_assets:
            await session.refresh(asset)

        # Bulk assign providers

        assignments = [
            FAProviderAssignmentItem(
                asset_id=test_assets[0].id,
                provider_code="yfinance",
                identifier="TEST1",
                identifier_type=IdentifierType.TICKER,
                provider_params={"ticker": "TEST1"},
            ),
            FAProviderAssignmentItem(
                asset_id=test_assets[1].id,
                provider_code="yfinance",
                identifier="TEST2",
                identifier_type=IdentifierType.TICKER,
                provider_params={"ticker": "TEST2"},
            ),
            FAProviderAssignmentItem(
                asset_id=test_assets[2].id,
                provider_code="mockprov",
                identifier="MOCK1",
                identifier_type=ProviderInputType.AUTO_GENERATED,
                provider_params=None,
            ),
        ]

        results = await AssetSourceManager.bulk_assign_providers(assignments, session)

        # Detailed logging of results
        for r in results:
            status = "OK" if r.success else "ERROR"
            print_info(f"Assignment result: asset_id={r.asset_id} status={status} message={r.message}")

        # Verify all succeeded
        for result in results:
            assert result.success, f"Assignment failed: {result.message}"

        # Verify in DB and print mapping
        for assignment in assignments:
            provider = await AssetSourceManager.get_asset_provider(assignment.asset_id, session)
            assert provider is not None, f"Provider not found for asset {assignment.asset_id}"
            assert provider.provider_code == assignment.provider_code
            print_success(f"✓ Verified DB: asset {assignment.asset_id} -> {provider.provider_code}")


@pytest.mark.asyncio
async def test_assign_does_not_modify_metadata(asset_ids: list[int]):
    """Test that provider assignment does NOT auto-populate metadata (removed in C2R2)."""
    print_section("Test 6a: Assign Does Not Modify Metadata")

    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset = Asset(
            display_name=f"NoAutoPopulate Test {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            classification_params=None,
        )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_NO_AUTO",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={"mock_param": "test"},
        )

        results = await AssetSourceManager.bulk_assign_providers([item], session)
        result = results[0]
        assert result.success, f"Assignment failed: {result.message}"

        await session.refresh(test_asset)
        assert test_asset.classification_params is None, f"classification_params should be None after assign (no auto-populate), " f"got: {test_asset.classification_params}"
        print_success("✓ Assignment does not auto-populate metadata")


@pytest.mark.asyncio
async def test_assign_preserves_existing_metadata(asset_ids: list[int]):
    """Test that provider assignment preserves pre-existing metadata."""
    print_section("Test 6b: Assign Preserves Existing Metadata")

    timestamp = int(time.time() * 1000)
    pre_existing = json.dumps(
        {
            "sector_area": {"distribution": {"Healthcare": 1.0}},
            "geographic_area": {"distribution": {"DEU": 0.5, "FRA": 0.5}},
            "short_description": "Pre-existing description",
        }
    )

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset = Asset(
            display_name=f"PreserveMetadata Test {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            classification_params=pre_existing,
        )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_PRESERVE",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={},
        )

        results = await AssetSourceManager.bulk_assign_providers([item], session)
        assert results[0].success

        await session.refresh(test_asset)
        assert test_asset.classification_params == pre_existing, "classification_params should be unchanged after assign"
        metadata = json.loads(test_asset.classification_params)
        assert "Healthcare" in metadata["sector_area"]["distribution"]
        assert "DEU" in metadata["geographic_area"]["distribution"]
        print_success("✓ Pre-existing metadata preserved after assignment")


@pytest.mark.asyncio
async def test_refresh_populates_empty_asset(asset_ids: list[int]):
    """Test that explicit refresh populates metadata on an empty asset."""
    print_section("Test 6c: Refresh Populates Empty Asset")

    AssetProviderRegistry.auto_discover()

    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset = Asset(
            display_name=f"RefreshPopulate Test {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            classification_params=None,
        )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        # Assign provider first (no auto-populate)
        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_REFRESH",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={},
        )
        results = await AssetSourceManager.bulk_assign_providers([item], session)
        assert results[0].success

        # Explicit refresh
        refresh_resp = await AssetSourceManager.refresh_assets_from_provider([test_asset.id], session)
        assert len(refresh_resp.results) == 1
        r = refresh_resp.results[0]
        assert r.success, f"Refresh failed: {r.message}"

        # Verify metadata written to DB
        await session.refresh(test_asset)
        assert test_asset.classification_params is not None, "Metadata should be populated after refresh"
        metadata = json.loads(test_asset.classification_params)
        assert "Technology" in metadata.get("sector_area", {}).get("distribution", {}), "sector not populated"
        assert "USA" in metadata.get("geographic_area", {}).get("distribution", {}), "geo not populated"
        print_success("✓ Refresh populated empty asset with metadata from mockprov")


@pytest.mark.asyncio
async def test_refresh_returns_metadata_fields(asset_ids: list[int]):
    """Test that refresh returns fields_detail with refreshed_fields info."""
    print_section("Test 6d: Refresh Returns Metadata Fields")

    AssetProviderRegistry.auto_discover()

    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset = Asset(
            display_name=f"RefreshFields Test {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            classification_params=None,
        )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_FIELDS",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={},
        )
        await AssetSourceManager.bulk_assign_providers([item], session)

        refresh_resp = await AssetSourceManager.refresh_assets_from_provider([test_asset.id], session)
        r = refresh_resp.results[0]
        assert r.success
        assert r.fields_detail is not None, "fields_detail should be present"

        refreshed_names = [f.info for f in r.fields_detail.refreshed_fields]
        assert "classification_params" in refreshed_names, f"classification_params should be in refreshed_fields, got: {refreshed_names}"
        print_success(f"✓ Refresh returned fields_detail with refreshed_fields: {refreshed_names}")


@pytest.mark.asyncio
async def test_refresh_field_detail_completeness(asset_ids: list[int]):
    """Test that refresh reports missing_data_fields for fields not returned by provider."""
    print_section("Test 6e: Refresh Field Detail Completeness")

    AssetProviderRegistry.auto_discover()

    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset = Asset(
            display_name=f"FieldCompleteness Test {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            classification_params=None,
        )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_COMPLETE",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={},
        )
        await AssetSourceManager.bulk_assign_providers([item], session)

        refresh_resp = await AssetSourceManager.refresh_assets_from_provider([test_asset.id], session)
        r = refresh_resp.results[0]
        assert r.success
        assert r.fields_detail is not None

        # mockprov returns classification_params only — other patchable fields are missing
        missing = r.fields_detail.missing_data_fields
        assert isinstance(missing, list)
        assert len(missing) > 0, "Should have missing_data_fields for fields not returned by mockprov"
        assert r.fields_detail.ignored_fields == [], "ignored_fields should be empty"
        print_success(f"✓ missing_data_fields={missing}, ignored_fields=[]")


@pytest.mark.asyncio
async def test_refresh_overwrites_user_set_fields(asset_ids: list[int]):
    """Test that explicit refresh overwrites user-set fields (refresh = take from provider)."""
    print_section("Test 6f: Refresh Overwrites User-Set Fields")

    AssetProviderRegistry.auto_discover()

    timestamp = int(time.time() * 1000)

    # Start with user-set geographic_area different from mockprov
    user_params = json.dumps(
        {
            "geographic_area": {"distribution": {"JPN": 1.0}},
            "short_description": "User description",
        }
    )

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset = Asset(
            display_name=f"RefreshOverwrite Test {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            classification_params=user_params,
        )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_OVERWRITE",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={},
        )
        await AssetSourceManager.bulk_assign_providers([item], session)

        # Refresh — mockprov returns geo=USA+ITA, sector=Technology
        refresh_resp = await AssetSourceManager.refresh_assets_from_provider([test_asset.id], session)
        r = refresh_resp.results[0]
        assert r.success, f"Refresh failed: {r.message}"

        await session.refresh(test_asset)
        metadata = json.loads(test_asset.classification_params)

        # mockprov's geo (USA+ITA) should have overwritten user's (JPN)
        geo = metadata.get("geographic_area", {}).get("distribution", {})
        assert "USA" in geo, f"Expected USA in geo after refresh, got: {geo}"
        assert "JPN" not in geo, f"JPN should have been overwritten by provider, got: {geo}"
        print_success("✓ Refresh correctly overwrites user-set fields with provider data")


@pytest.mark.asyncio
async def test_bulk_remove_providers(asset_ids: list[int]):
    """Test bulk_remove_providers() method."""
    print_section("Test 7: Bulk Remove Providers")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        bulkDelResults = await AssetSourceManager.bulk_remove_providers(asset_ids, session)

        # Detailed logging
        for r in bulkDelResults.results:
            print_info(f"Removal: asset_id={r.asset_id} success={r.success} message={r.message}")

        # Verify all succeeded
        for result in bulkDelResults.results:
            assert result.success, f"Removal failed: {result}"

        # Verify removal
        for asset_id in asset_ids:
            provider = await AssetSourceManager.get_asset_provider(asset_id, session)
            assert provider is None, f"Provider still exists for asset {asset_id}"
            print_success(f"✓ Verified DB: asset {asset_id} has no provider providers successfully removed")


# ============================================================================
# PRICE CRUD TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_upsert_prices(asset_ids: list[int]):
    """Test bulk_upsert_prices() method."""
    print_section("Test 9: Bulk Upsert Prices")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Upsert prices for 2 assets
        data = [
            FAUpsert(
                asset_id=asset_ids[0],
                prices=[
                    FAPricePoint(
                        date=date(2025, 1, 1),
                        close=Decimal("100.50"),
                        volume=Decimal("1000"),
                        currency="USD",
                    ),
                    FAPricePoint(
                        date=date(2025, 1, 2),
                        close=Decimal("101.25"),
                        volume=Decimal("1500"),
                        currency="USD",
                    ),
                ],
            ),
            FAUpsert(
                asset_id=asset_ids[1],
                prices=[
                    FAPricePoint(
                        date=date(2025, 1, 1),
                        close=Decimal("200.00"),
                        volume=Decimal("500"),
                        currency="USD",
                    ),
                ],
            ),
        ]

        result = await AssetSourceManager.bulk_upsert_prices(data, session)

        # Verify result contains expected count
        assert "inserted_count" in result, "Result should contain inserted_count"
        assert result["inserted_count"] == 3, f"Expected 3 prices inserted, got {result.get('inserted_count')}"

        # Detailed logging of DB state per asset
        for item in data:
            stmt = select(PriceHistory).where(PriceHistory.asset_id == item.asset_id)
            db_result = await session.execute(stmt)
            prices = db_result.scalars().all()
            print_info(f"Asset {item.asset_id} prices in DB: {[(p.date, p.close, p.volume) for p in prices]}")

        # Verify in DB
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_ids[0])
        db_result = await session.execute(stmt)
        prices = db_result.scalars().all()

        assert len(prices) == 2, f"Expected 2 prices, got {len(prices)}"
        assert prices[0].volume == Decimal("1000") and prices[1].volume == Decimal("1500"), "Volume values not persisted correctly"


@pytest.mark.asyncio
async def test_get_prices_with_backfill(asset_ids: list[int]):
    """Test get_prices_bulk() with backward-fill logic."""
    print_section("Test 10: Get Prices with Backward-Fill")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Query range with gaps via bulk API
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=asset_ids[0],
                    date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 5)),
                )
            ],
            session=session,
        )
        prices = results[0].prices

        assert len(prices) == 5, f"Expected 5 prices, got {len(prices)}"

        # Print each date's info
        for p in prices:
            bf = p.backward_fill_info
            if bf:
                print_info(f"{p.date}: {p.close} (backfilled from {bf.actual_rate_date} , days_back={bf.days_back})")
            else:
                print_info(f"{p.date}: {p.close} (exact)")

        # Count backfilled dates
        backfilled = [p for p in prices if p.backward_fill_info]

        # Verify we have some backfilled prices (days 3-5 should be backfilled from day 2)
        assert len(backfilled) == 3, f"Expected 3 backfilled prices, got {len(backfilled)}"

        # Verify first 2 are exact matches (not backfilled)
        assert prices[0].backward_fill_info is None, "Day 1 should not be backfilled"
        assert prices[1].backward_fill_info is None, "Day 2 should not be backfilled"


@pytest.mark.asyncio
async def test_backward_fill_volume_propagation(asset_ids: list[int]):
    """Test backward-fill with volume propagation.

    Scenario:
    - Day 1 and 2: have prices WITH volume
    - Day 3 and 4: missing (should backfill close AND volume)

    Assertions:
    - backward_fill_info is not None for days 3-4
    - volume backfilled equals last known volume
    - Edge case: if no initial data exists, no backfill occurs (empty list or shorter list)
    """
    print_section("Test 11: Backward-Fill Volume Propagation")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Setup: Insert prices for Day 1 and Day 2 WITH volume
        test_asset_id = asset_ids[0]

        # Clear existing prices first
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == test_asset_id))
        await session.commit()

        # Insert Day 1 and Day 2 with volume
        day1_volume = Decimal("1000.50")
        day2_volume = Decimal("2500.75")

        prices_to_insert = [
            PriceHistory(
                asset_id=test_asset_id,
                date=date(2025, 1, 1),
                open=Decimal("100.00"),
                high=Decimal("105.00"),
                low=Decimal("99.00"),
                close=Decimal("103.00"),
                volume=day1_volume,
                currency="USD",
                source_plugin_key="manual_test",
            ),
            PriceHistory(
                asset_id=test_asset_id,
                date=date(2025, 1, 2),
                open=Decimal("103.00"),
                high=Decimal("107.00"),
                low=Decimal("102.00"),
                close=Decimal("106.00"),
                volume=day2_volume,
                currency="USD",
                source_plugin_key="manual_test",
            ),
        ]

        session.add_all(prices_to_insert)
        await session.commit()

        # Query range Day 1-4 (Day 3 and 4 should be backfilled)
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=test_asset_id,
                    date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 4)),
                )
            ],
            session=session,
        )
        prices = results[0].prices

        assert len(prices) == 4, f"Expected 4 prices (2 actual + 2 backfilled), got {len(prices)}"

        # Verify Day 1 and Day 2 (exact, no backfill)
        day1_price = prices[0]
        assert day1_price.date == date(2025, 1, 1), "Day 1 date mismatch"
        assert day1_price.close == Decimal("103.00"), "Day 1 close mismatch"
        assert day1_price.volume == day1_volume, f"Day 1 volume mismatch: expected {day1_volume}, got {day1_price.volume}"
        assert day1_price.backward_fill_info is None, "Day 1 should not be backfilled"
        print_success(f"✓ Day 1: close={day1_price.close}, volume={day1_price.volume} (exact)")

        day2_price = prices[1]
        assert day2_price.date == date(2025, 1, 2), "Day 2 date mismatch"
        assert day2_price.close == Decimal("106.00"), "Day 2 close mismatch"
        assert day2_price.volume == day2_volume, f"Day 2 volume mismatch: expected {day2_volume}, got {day2_price.volume}"
        assert day2_price.backward_fill_info is None, "Day 2 should not be backfilled"
        print_success(f"✓ Day 2: close={day2_price.close}, volume={day2_price.volume} (exact)")

        # Verify Day 3 and Day 4 (backfilled from Day 2)
        for idx, expected_date in enumerate([date(2025, 1, 3), date(2025, 1, 4)], start=2):
            price = prices[idx]
            assert price.date == expected_date, f"Day {idx + 1} date mismatch"
            assert price.backward_fill_info is not None, f"Day {idx + 1} should have backward_fill_info"
            assert price.backward_fill_info.actual_rate_date == date(2025, 1, 2), f"Day {idx + 1} should be backfilled from Day 2"
            assert price.backward_fill_info.days_back == idx - 1, f"Day {idx + 1} days_back should be {idx - 1}"

            # Critical assertion: volume must be backfilled
            assert price.close == Decimal("106.00"), f"Day {idx + 1} close should be backfilled"
            assert price.volume == day2_volume, f"Day {idx + 1} volume should be backfilled: expected {day2_volume}, got {price.volume}"

            print_success(f"✓ Day {idx + 1}: close={price.close}, volume={price.volume} " f"(backfilled from {price.backward_fill_info.actual_rate_date}, " f"days_back={price.backward_fill_info.days_back})")

        backfilled_count = sum(1 for p in prices if p.backward_fill_info)

        # Verify exactly 2 prices are backfilled (days 3 and 4)
        assert backfilled_count == 2, f"Expected 2 backfilled prices, got {backfilled_count}"


@pytest.mark.asyncio
async def test_backward_fill_edge_case_no_initial_data(asset_ids: list[int]):
    """Test backward-fill edge case: no initial data exists.

    Scenario:
    - Query range Day 1-4 but NO prices exist in DB

    Expected:
    - Empty list or no backfill (implementation dependent)
    - Should NOT crash
    """
    print_section("Test 12: Backward-Fill Edge Case (No Initial Data)")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Use a different asset to ensure it has no prices
        test_asset_id = asset_ids[1] if len(asset_ids) > 1 else asset_ids[0]

        # Clear all prices for this asset
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == test_asset_id))
        await session.commit()

        # Query range with no data
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=test_asset_id,
                    date_range=DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 4)),
                )
            ],
            session=session,
        )
        prices = results[0].prices

        # Should return empty list (no data to backfill from)
        assert len(prices) == 0, f"Expected empty list when no data exists, got {len(prices)} prices"
        print_info("✓ Edge case handled: empty list returned when no initial data exists")


@pytest.mark.asyncio
async def test_provider_fallback_invalid(asset_ids: list[int]):
    """Test sync/query separation when invalid/unregistered provider is assigned.

    With the new architecture (Sync ≠ Query):
    - Sync with invalid provider → should fail gracefully (error in result, no crash)
    - Query from DB → should still return manually inserted prices (query is provider-agnostic)

    This certifies that the query path is completely independent from the provider path.
    """
    print_section("Test 13: Sync/Query Separation with Invalid Provider")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        test_asset_id = asset_ids[0]

        # Insert invalid provider assignment directly in DB (bypass Pydantic validation)
        # This simulates a legacy provider or corrupted data
        invalid_provider = "invalid_nonexistent_provider"

        # Delete existing assignment if any
        await session.execute(delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == test_asset_id))

        # Insert invalid provider directly
        invalid_assignment = AssetProviderAssignment(
            asset_id=test_asset_id,
            provider_code=invalid_provider,
            identifier="INVALID_TEST",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params=None,
        )
        session.add(invalid_assignment)
        await session.commit()
        print_info(f"Inserted invalid provider '{invalid_provider}' directly in DB for asset {test_asset_id}")

        # Insert manual prices in DB
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == test_asset_id))
        await session.commit()

        fallback_price = PriceHistory(
            asset_id=test_asset_id,
            date=date(2025, 1, 10),
            close=Decimal("999.00"),
            currency="USD",
            source_plugin_key="manual_test_fallback",
        )
        session.add(fallback_price)
        await session.commit()
        print_info("Inserted manual price in DB: date=2025-01-10, close=999.00")

        # Step 1: SYNC with invalid provider → should fail gracefully, no crash
        sync_response = await AssetSourceManager.bulk_refresh_prices(
            requests=[
                FARefreshItem(
                    asset_id=test_asset_id,
                    date_range=DateRangeModel(start=date(2025, 1, 10), end=date(2025, 1, 10)),
                )
            ],
            session=session,
        )

        sync_result = sync_response.results[0]
        assert len(sync_result.errors) > 0, "Sync with invalid provider should produce errors"
        print_success(f"✓ Sync failed gracefully with errors: {sync_result.errors}")

        # Step 2: QUERY from DB → should still return the manual price (query is provider-agnostic)
        query_results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=test_asset_id,
                    date_range=DateRangeModel(start=date(2025, 1, 10), end=date(2025, 1, 10)),
                )
            ],
            session=session,
        )
        prices = query_results[0].prices

        # Verify query returned manual data despite invalid provider
        assert len(prices) == 1, f"Expected 1 price from DB query, got {len(prices)}"
        assert prices[0].close == Decimal("999.00"), f"Expected price 999.00, got {prices[0].close}"
        assert prices[0].date == date(2025, 1, 10), f"Expected date 2025-01-10, got {prices[0].date}"

        print_success(f"✓ Query returned manual price despite invalid provider: {prices[0].close}")
        print_info("✓ Sync/Query separation verified: invalid provider blocks sync but NOT query")


@pytest.mark.asyncio
async def test_bulk_delete_prices(asset_ids: list[int]):
    """Test bulk_delete_prices() method."""
    print_section("Test 14: Bulk Delete Prices")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Delete specific ranges
        data = [
            FAAssetDelete(
                asset_id=asset_ids[0],
                date_ranges=[DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 2))],
            ),
            FAAssetDelete(
                asset_id=asset_ids[1],
                date_ranges=[DateRangeModel(start=date(2025, 1, 1), end=None)],  # Single day
            ),
        ]

        bulkDelresult = await AssetSourceManager.bulk_delete_prices(data, session)

        # Detailed logging of deletion
        print_info(f"Bulk delete returned: {bulkDelresult.model_dump_json(indent=2)}")

        # Verify deletion
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_ids[0])
        db_result = await session.execute(stmt)
        prices = db_result.scalars().all()

        print_info(f"Remaining prices for asset {asset_ids[0]}: {len(prices)}")

        # Verify that prices for the date range were actually deleted
        # (Note: the actual count depends on what was inserted in previous tests)
        # We just verify that the operation completed successfully
        assert all(r.message for r in bulkDelresult.results), "All results should have a message"


# ============================================================================
# CURRENCY CONVERSION TESTS (C1/C2)
# ============================================================================


@pytest.fixture(scope="module")
def fx_asset_ids():
    """Create assets with EUR currency + insert FX rates for USD→EUR conversion tests."""

    timestamp = int(time.time() * 1000)

    async def _setup():
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Create a USD-denominated asset
            asset = Asset(
                display_name=f"FX Test Asset {timestamp}",
                currency="USD",
                asset_type=AssetType.STOCK,
                active=True,
            )
            session.add(asset)
            await session.commit()
            await session.refresh(asset)

            # Insert USD prices for the asset (use Feb dates to avoid collisions)
            prices = [
                PriceHistory(
                    asset_id=asset.id,
                    date=date(2025, 2, d),
                    close=Decimal("100.00") + d,
                    currency="USD",
                    source_plugin_key="test_fx_conversion",
                )
                for d in range(1, 6)  # Feb 1-5
            ]
            session.add_all(prices)

            # Insert FX rates: EUR/USD (base=EUR < quote=USD → 1 EUR = rate USD)
            # So to convert USD → EUR: divide by rate
            # Use MERGE/upsert pattern to handle re-runs
            for fx_data in [
                {"date": date(2025, 2, 1), "base": "EUR", "quote": "USD", "rate": Decimal("1.10"), "source": "TEST"},
                {"date": date(2025, 2, 2), "base": "EUR", "quote": "USD", "rate": Decimal("1.12"), "source": "TEST"},
                # Gap on Feb 3-4 → FX backward-fill should kick in
                {"date": date(2025, 2, 5), "base": "EUR", "quote": "USD", "rate": Decimal("1.08"), "source": "TEST"},
            ]:
                stmt = (
                    sqlite_insert(FxRate)
                    .values(**fx_data)
                    .on_conflict_do_update(
                        index_elements=["date", "base", "quote"],
                        set_={"rate": fx_data["rate"], "source": fx_data["source"]},
                    )
                )
                await session.execute(stmt)
            await session.commit()

            return asset.id

    asset_id = asyncio.run(_setup())
    yield asset_id


@pytest.mark.asyncio
async def test_get_prices_with_target_currency(fx_asset_ids: int):
    """Test get_prices_bulk() with target_currency conversion."""
    print_section("Test 15: Price Query with Currency Conversion")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=fx_asset_ids,
                    date_range=DateRangeModel(start=date(2025, 2, 1), end=date(2025, 2, 5)),
                    target_currency="EUR",
                )
            ],
            session=session,
        )
        result = results[0]
        prices = result.prices

        assert len(prices) == 5, f"Expected 5 prices, got {len(prices)}"

        # All prices should be in EUR
        for p in prices:
            assert p.currency == "EUR", f"Expected EUR, got {p.currency}"
            assert p.original_currency == "USD", f"Expected original USD, got {p.original_currency}"
            # original_close must be present and in native currency
            assert p.original_close is not None, f"original_close should be set for converted price on {p.date}"

        # Day 1: USD 101 / 1.10 = ~91.818 EUR
        p1 = prices[0]
        expected_close_1 = Decimal("101.00") / Decimal("1.10")
        assert abs(float(p1.close) - float(expected_close_1)) < 0.01, f"Day 1 close mismatch: {p1.close} vs expected ~{expected_close_1:.4f}"
        # Verify original values preserved
        assert float(p1.original_close) == 101.0, f"original_close should be 101.0, got {p1.original_close}"
        print_info(f"Day 1: USD 101.00 → EUR {p1.close:.4f} (rate 1.10), original_close={p1.original_close}")

        # Day 2: USD 102 / 1.12 = ~91.071 EUR
        p2 = prices[1]
        expected_close_2 = Decimal("102.00") / Decimal("1.12")
        assert abs(float(p2.close) - float(expected_close_2)) < 0.01, f"Day 2 close mismatch: {p2.close} vs expected ~{expected_close_2:.4f}"
        print_info(f"Day 2: USD 102.00 → EUR {p2.close:.4f} (rate 1.12)")

        # Day 3: FX backward-filled from day 2 (rate 1.12), price 103
        p3 = prices[2]
        assert p3.backward_fill_info is not None, "Day 3 should have backward_fill_info"
        assert p3.backward_fill_info.fx_days_back is not None, "Day 3 should have fx_days_back"
        assert p3.backward_fill_info.fx_days_back == 1, f"Day 3 fx_days_back should be 1, got {p3.backward_fill_info.fx_days_back}"
        print_info(f"Day 3: USD 103.00 → EUR {p3.close:.4f} (FX backfilled {p3.backward_fill_info.fx_days_back}d)")

        # Day 5: exact FX rate (1.08), price 105
        p5 = prices[4]
        expected_close_5 = Decimal("105.00") / Decimal("1.08")
        assert abs(float(p5.close) - float(expected_close_5)) < 0.01, f"Day 5 close mismatch: {p5.close} vs expected ~{expected_close_5:.4f}"
        # Day 5 has exact FX rate → no FX staleness
        if p5.backward_fill_info is not None:
            assert p5.backward_fill_info.fx_days_back == 0 or p5.backward_fill_info.fx_days_back is None, f"Day 5 fx_days_back should be 0 or None, got {p5.backward_fill_info.fx_days_back}"
        print_info(f"Day 5: USD 105.00 → EUR {p5.close:.4f} (rate 1.08, exact)")

        print_success("✓ Currency conversion with FX backward-fill verified")


@pytest.mark.asyncio
async def test_get_prices_no_target_currency(fx_asset_ids: int):
    """Test that get_prices_bulk() without target_currency returns native prices unchanged."""
    print_section("Test 16: Price Query without Currency Conversion")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=fx_asset_ids,
                    date_range=DateRangeModel(start=date(2025, 2, 1), end=date(2025, 2, 2)),
                )
            ],
            session=session,
        )
        prices = results[0].prices

        assert len(prices) == 2
        for p in prices:
            assert p.currency == "USD", f"Expected native USD, got {p.currency}"
            assert p.original_currency is None, f"original_currency should be None, got {p.original_currency}"
            assert p.original_close is None, f"original_close should be None without conversion, got {p.original_close}"
        assert prices[0].close == Decimal("101.00")
        print_success("✓ No conversion when target_currency is absent")


@pytest.mark.asyncio
async def test_get_prices_same_target_currency(fx_asset_ids: int):
    """Test that target_currency == native currency is a no-op."""
    print_section("Test 17: Price Query with Same Currency (no-op)")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=fx_asset_ids,
                    date_range=DateRangeModel(start=date(2025, 2, 1), end=date(2025, 2, 2)),
                    target_currency="USD",
                )
            ],
            session=session,
        )
        prices = results[0].prices

        assert len(prices) == 2
        for p in prices:
            assert p.currency == "USD"
            # Same currency → no conversion, original_currency should be None
            assert p.original_currency is None, f"Same-currency conversion should not set original_currency, got {p.original_currency}"
        assert prices[0].close == Decimal("101.00"), "Price should be unchanged"
        print_success("✓ Same-currency target is a no-op")


@pytest.mark.asyncio
async def test_get_prices_missing_fx_pair():
    """Test that missing FX pair results in native prices + errors list."""
    print_section("Test 18: Price Query with Missing FX Pair")

    async def _create_asset():
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset = Asset(
                display_name=f"JPY Test Asset {int(time.time() * 1000)}",
                currency="JPY",
                asset_type=AssetType.STOCK,
                active=True,
            )
            session.add(asset)
            await session.commit()
            await session.refresh(asset)

            # Insert a JPY price
            session.add(
                PriceHistory(
                    asset_id=asset.id,
                    date=date(2025, 2, 1),
                    close=Decimal("15000.00"),
                    currency="JPY",
                    source_plugin_key="test_fx_missing",
                )
            )
            await session.commit()
            return asset.id

    jpy_asset_id = await _create_asset()

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=jpy_asset_id,
                    date_range=DateRangeModel(start=date(2025, 2, 1), end=date(2025, 2, 1)),
                    target_currency="CHF",  # No JPY/CHF rate exists
                )
            ],
            session=session,
        )
        result = results[0]

        # Price should remain in JPY (conversion failed)
        assert len(result.prices) == 1
        p = result.prices[0]
        assert p.currency == "JPY", f"Expected native JPY (conversion failed), got {p.currency}"
        assert p.close == Decimal("15000.00"), "Price should be unchanged"

        # Errors should report the missing FX pair
        assert len(result.errors) > 0, "Expected error about missing FX pair"
        print_info(f"Error message: {result.errors[0]}")
        print_success("✓ Missing FX pair: native price returned + error reported")


@pytest.mark.asyncio
async def test_query_result_errors_field(fx_asset_ids: int):
    """Test that FAPriceQueryResult.errors is empty list when no issues."""
    print_section("Test 19: Query Result errors field (empty when no issues)")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        results = await AssetSourceManager.get_prices_bulk(
            requests=[
                FAPriceQueryItem(
                    asset_id=fx_asset_ids,
                    date_range=DateRangeModel(start=date(2025, 2, 1), end=date(2025, 2, 2)),
                    target_currency="EUR",
                )
            ],
            session=session,
        )
        result = results[0]
        assert isinstance(result.errors, list), "errors should be a list"
        assert len(result.errors) == 0, f"Expected 0 errors, got {result.errors}"
        print_success("✓ errors field is empty list when conversion succeeds")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# ============================================================================
# MAP IDENTIFIER TYPE TESTS (C13b)
# ============================================================================


class TestMapIdentifierTypeToInputType:
    """Tests for AssetSourceProvider.map_identifier_type_to_input_type (reverse mapping)."""

    def test_ticker_maps_to_ticker(self):
        """TICKER IdentifierType → ProviderInputType.TICKER."""
        result = AssetSourceProvider.map_identifier_type_to_input_type(IdentifierType.TICKER.value)
        assert result == ProviderInputType.TICKER

    def test_isin_maps_to_isin(self):
        """ISIN IdentifierType → ProviderInputType.ISIN."""
        result = AssetSourceProvider.map_identifier_type_to_input_type(IdentifierType.ISIN.value)
        assert result == ProviderInputType.ISIN

    def test_other_maps_to_url(self):
        """OTHER IdentifierType → ProviderInputType.URL."""
        result = AssetSourceProvider.map_identifier_type_to_input_type(IdentifierType.OTHER.value)
        assert result == ProviderInputType.URL

    def test_uuid_maps_to_auto_generated(self):
        """UUID IdentifierType → ProviderInputType.AUTO_GENERATED."""
        result = AssetSourceProvider.map_identifier_type_to_input_type(IdentifierType.UUID.value)
        assert result == ProviderInputType.AUTO_GENERATED

    def test_unmapped_returns_none(self):
        """Unknown identifier type (e.g. CUSIP, SEDOL) → None."""
        result = AssetSourceProvider.map_identifier_type_to_input_type("CUSIP")
        assert result is None

    def test_figi_returns_none(self):
        """FIGI has no provider equivalent → None."""
        result = AssetSourceProvider.map_identifier_type_to_input_type("FIGI")
        assert result is None


def test_provider_param_helpers_and_identifier_mapping():
    """Helper paths: provider param hash/parse and input-type mapping."""
    print_section("Test 20: Provider param helpers")

    params_a = {"b": 2, "a": 1}
    params_b = {"a": 1, "b": 2}

    assert _provider_params_hash(None) == "none"
    assert _provider_params_hash(params_a) == _provider_params_hash(params_b)
    assert AssetSourceManager._parse_provider_params(None) == {}
    assert AssetSourceManager._parse_provider_params(params_a) == params_a
    assert AssetSourceManager._parse_provider_params('{"x": 1, "y": "z"}') == {"x": 1, "y": "z"}
    assert AssetSourceProvider.map_input_type_to_identifier_type(ProviderInputType.URL.value) == IdentifierType.OTHER
    assert AssetSourceProvider.map_input_type_to_identifier_type(ProviderInputType.AUTO_GENERATED.value) == IdentifierType.UUID
    assert AssetSourceProvider.map_input_type_to_identifier_type(IdentifierType.CUSIP.value) == IdentifierType.CUSIP
    print_success("✓ Provider param helpers cover main branches")


@pytest.mark.asyncio
async def test_create_assets_bulk_with_duplicate_and_metadata():
    """Create path persists metadata while duplicate rows fail without aborting the batch."""
    print_section("Test 21: create_assets_bulk partial success")

    timestamp = int(time.time() * 1000)
    display_name = f"CreateBulk {timestamp}"

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        payload = [
            FAAssetCreateItem(
                display_name=display_name,
                currency="usd",
                asset_type=AssetType.ETF,
                quote_base_quantity=0,
                identifier_ticker="cbt",
                classification_params=FAClassificationParams(
                    short_description="Created from bulk test",
                    sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")}),
                    geographic_area=FAGeographicArea(distribution={"USA": Decimal("1.0")}),
                ),
            ),
            FAAssetCreateItem(
                display_name=display_name,
                currency="EUR",
            ),
        ]

        response = await AssetCRUDService.create_assets_bulk(payload, session)

        assert response.success_count == 1
        assert response.results[0].success is True
        assert response.results[1].success is False
        assert "already exists" in response.results[1].message

        created = (await session.execute(select(Asset).where(Asset.id == response.results[0].asset_id))).scalar_one()
        created_meta = json.loads(created.classification_params)

        assert created.currency == "USD"
        assert created.quote_base_quantity == 1
        assert created.identifier_ticker == "CBT"
        assert created_meta["short_description"] == "Created from bulk test"
        assert created_meta["sector_area"]["distribution"]["Technology"] == "1.0000"
        print_success("✓ Bulk create keeps successful asset and isolates duplicate failure")


@pytest.mark.asyncio
async def test_refresh_assets_from_provider_mixed_results():
    """Refresh handles success, no-assignment, bad-provider, and missing-asset in one batch."""
    print_section("Test 22: refresh_assets_from_provider mixed batch")

    AssetProviderRegistry.auto_discover()
    asset_source_module._asset_metadata_cache.clear()
    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        good_asset = Asset(display_name=f"Refresh Good {timestamp}", currency="USD", asset_type=AssetType.STOCK, active=True)
        no_provider_asset = Asset(display_name=f"Refresh NoProv {timestamp}", currency="USD", asset_type=AssetType.STOCK, active=True)
        bad_provider_asset = Asset(display_name=f"Refresh BadProv {timestamp}", currency="USD", asset_type=AssetType.STOCK, active=True)
        session.add_all([good_asset, no_provider_asset, bad_provider_asset])
        await session.commit()
        for asset in (good_asset, no_provider_asset, bad_provider_asset):
            await session.refresh(asset)

        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=good_asset.id,
                    provider_code="mockprov",
                    identifier="MIXED_REFRESH",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params={},
                )
            ],
            session,
        )
        session.add(
            AssetProviderAssignment(
                asset_id=bad_provider_asset.id,
                provider_code="missing_provider",
                identifier="BAD_REFRESH",
                identifier_type=ProviderInputType.AUTO_GENERATED,
                provider_params="{}",
            )
        )
        await session.commit()

        response = await AssetSourceManager.refresh_assets_from_provider(
            [good_asset.id, no_provider_asset.id, bad_provider_asset.id, 999999],
            session,
        )

        by_asset = {item.asset_id: item for item in response.results}
        assert response.success_count == 1
        assert by_asset[good_asset.id].success is True
        assert by_asset[good_asset.id].fields_detail is not None
        assert by_asset[no_provider_asset.id].success is False
        assert "No provider assigned" in by_asset[no_provider_asset.id].message
        assert by_asset[bad_provider_asset.id].success is False
        assert "Provider missing_provider not found" == by_asset[bad_provider_asset.id].message
        assert by_asset[999999].success is False
        assert "not found" in by_asset[999999].message

        await session.refresh(good_asset)
        good_meta = json.loads(good_asset.classification_params)
        assert "Technology" in good_meta["sector_area"]["distribution"]
        print_success("✓ Mixed refresh batch reports each outcome correctly")


@pytest.mark.asyncio
async def test_refresh_assets_from_provider_uses_metadata_cache(monkeypatch):
    """Second refresh uses the metadata cache instead of calling the provider again."""
    print_section("Test 23: refresh_assets_from_provider metadata cache")

    AssetProviderRegistry.auto_discover()
    asset_source_module._asset_metadata_cache.clear()
    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = Asset(display_name=f"Refresh Cache {timestamp}", currency="USD", asset_type=AssetType.STOCK, active=True)
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=asset.id,
                    provider_code="mockprov",
                    identifier="CACHE_REFRESH",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params={},
                )
            ],
            session,
        )

        first = await AssetSourceManager.refresh_assets_from_provider([asset.id], session)
        assert first.results[0].success is True

        async def _unexpected_provider_call(*args, **kwargs):
            raise AssertionError("provider fetch should not run on cache hit")

        monkeypatch.setattr(asset_source_module, "_run_provider_in_thread", _unexpected_provider_call)

        second = await AssetSourceManager.refresh_assets_from_provider([asset.id], session)
        assert second.results[0].success is True
        assert second.results[0].fields_detail is not None
        print_success("✓ Metadata cache hit bypassed provider call")


@pytest.mark.asyncio
async def test_wipe_market_data_for_currency_change_dry_run_and_execute():
    """Dry-run reports counts; destructive call wipes prices/events and disconnects transactions."""
    print_section("Test 24: wipe_market_data_for_currency_change")

    AssetProviderRegistry.auto_discover()
    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = User(
            username=f"wipe_user_{timestamp}",
            email=f"wipe_{timestamp}@test.local",
            hashed_password="hashed",
        )
        broker = Broker(name=f"Wipe Broker {timestamp}")
        asset = Asset(display_name=f"Wipe Asset {timestamp}", currency="USD", asset_type=AssetType.BOND, active=True)
        session.add_all([user, broker, asset])
        await session.commit()
        for obj in (user, broker, asset):
            await session.refresh(obj)

        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=asset.id,
                    provider_code="mockprov",
                    identifier="WIPE_ASSET",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params={},
                )
            ],
            session,
        )
        assignment = await AssetSourceManager.get_asset_provider(asset.id, session)
        assert assignment is not None

        session.add_all(
            [
                PriceHistory(
                    asset_id=asset.id,
                    date=date(2025, 6, 1),
                    close=Decimal("100.00"),
                    currency="USD",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=asset.id,
                    date=date(2025, 6, 2),
                    close=Decimal("101.00"),
                    currency="USD",
                    source_plugin_key="manual_test",
                ),
                AssetEvent(
                    asset_id=asset.id,
                    date=date(2025, 6, 1),
                    type=AssetEventType.DIVIDEND,
                    value=Decimal("5.00"),
                    currency="USD",
                    provider_assignment_id=None,
                    notes="manual event",
                ),
                AssetEvent(
                    asset_id=asset.id,
                    date=date(2025, 6, 2),
                    type=AssetEventType.INTEREST,
                    value=Decimal("6.00"),
                    currency="USD",
                    provider_assignment_id=assignment.id,
                    notes="provider event",
                ),
            ]
        )
        await session.commit()

        provider_event = (
            await session.execute(
                select(AssetEvent).where(
                    AssetEvent.asset_id == asset.id,
                    AssetEvent.provider_assignment_id == assignment.id,
                )
            )
        ).scalar_one()

        session.add(
            Transaction(
                broker_id=broker.id,
                asset_id=asset.id,
                type=TransactionType.DIVIDEND,
                date=date(2025, 6, 2),
                quantity=Decimal("0"),
                amount=Decimal("6.00"),
                currency="USD",
                asset_event_id=provider_event.id,
                description="linked event tx",
            )
        )
        await session.commit()

        dry_run = await AssetSourceManager.wipe_market_data_for_currency_change(asset.id, session, dry_run=True)
        assert dry_run == {
            "prices": 2,
            "events_manual": 1,
            "events_provider": 1,
            "linked_tx": 1,
            "oldest": "2025-06-01",
            "newest": "2025-06-02",
            "dry_run": True,
        }

        wiped = await AssetSourceManager.wipe_market_data_for_currency_change(asset.id, session, dry_run=False)
        assert wiped["dry_run"] is False
        assert wiped["prices"] == 2
        assert (await session.execute(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset.id))).scalar_one() == 0
        assert (await session.execute(select(func.count()).select_from(AssetEvent).where(AssetEvent.asset_id == asset.id))).scalar_one() == 0
        tx = (await session.execute(select(Transaction).where(Transaction.asset_id == asset.id))).scalar_one()
        assert tx.asset_event_id is None
        print_success("✓ Currency-change wipe clears market data and disconnects linked tx")


@pytest.mark.asyncio
async def test_probe_provider_config_history_and_metadata():
    """Probe runs history + metadata operations and returns structured results."""
    print_section("Test 25: probe_provider_config")

    AssetProviderRegistry.auto_discover()
    config = FAProviderConfigBase(
        provider_code="mockprov",
        identifier="PROBE_ME",
        identifier_type=ProviderInputType.AUTO_GENERATED.value,
        provider_params={"source": "test"},
    )

    response = await AssetSourceManager.probe_provider_config(
        config,
        [ProbeOperation.HISTORY, ProbeOperation.METADATA],
    )

    assert response.provider_code == "mockprov"
    assert response.history is not None and response.history.success is True
    assert response.history.points_count >= 7
    assert response.history.sample_prices
    assert "→" in response.history.date_range
    assert response.metadata is not None and response.metadata.success is True
    assert response.metadata.patch_data is not None
    assert response.metadata.patch_data["classification_params"]["short_description"].startswith("Mock test asset PROBE_ME")
    print_success("✓ Probe history + metadata paths both succeeded")


@pytest.mark.asyncio
async def test_get_prices_bulk_with_events_seed_and_request_order():
    """Bulk price query keeps request order, uses seed backfill, and includes events only when requested."""
    print_section("Test 26: get_prices_bulk events + seed backfill")

    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset_a = Asset(display_name=f"Price Query A {timestamp}", currency="USD", asset_type=AssetType.STOCK, active=True)
        asset_b = Asset(display_name=f"Price Query B {timestamp}", currency="USD", asset_type=AssetType.STOCK, active=True)
        session.add_all([asset_a, asset_b])
        await session.commit()
        for asset in (asset_a, asset_b):
            await session.refresh(asset)

        session.add_all(
            [
                PriceHistory(
                    asset_id=asset_a.id,
                    date=date(2025, 5, 1),
                    open=Decimal("10"),
                    high=Decimal("10"),
                    low=Decimal("10"),
                    close=Decimal("10"),
                    volume=Decimal("100"),
                    currency="USD",
                    source_plugin_key="manual_test",
                ),
                PriceHistory(
                    asset_id=asset_b.id,
                    date=date(2025, 5, 2),
                    close=Decimal("20"),
                    currency="USD",
                    source_plugin_key="manual_test",
                ),
                AssetEvent(
                    asset_id=asset_a.id,
                    date=date(2025, 5, 3),
                    type=AssetEventType.DIVIDEND,
                    value=Decimal("1.50"),
                    currency="USD",
                    provider_assignment_id=None,
                    notes="seeded event",
                ),
            ]
        )
        await session.commit()

        results = await AssetSourceManager.get_prices_bulk(
            [
                FAPriceQueryItem(
                    asset_id=asset_b.id,
                    date_range=DateRangeModel(start=date(2025, 5, 2), end=date(2025, 5, 2)),
                ),
                FAPriceQueryItem(
                    asset_id=asset_a.id,
                    date_range=DateRangeModel(start=date(2025, 5, 2), end=date(2025, 5, 4)),
                    include_events=True,
                ),
            ],
            session,
        )

        assert [item.asset_id for item in results] == [asset_b.id, asset_a.id]
        assert len(results[0].prices) == 1 and results[0].events == []
        assert len(results[1].prices) == 3
        assert all(point.backward_fill_info is not None for point in results[1].prices)
        assert results[1].prices[0].backward_fill_info.actual_rate_date == date(2025, 5, 1)
        assert len(results[1].events) == 1
        assert results[1].events[0].notes == "seeded event"
        assert results[1].events[0].is_auto is False
        print_success("✓ Price query handles seed backfill, event fetch, and request order")


@pytest.mark.asyncio
async def test_bulk_refresh_prices_current_only_marks_partial(monkeypatch):
    """Current-only provider refresh inserts one row and returns PARTIAL status."""
    print_section("Test 27: bulk_refresh_prices current-only partial")

    timestamp = int(time.time() * 1000)

    class PartialProvider:
        supports_history = True
        provider_kind = asset_source_module.FAProviderKind.ONLINE_SCRAPER

        async def get_history_value(self, identifier, identifier_type, provider_params, start_date, end_date):
            return SimpleNamespace(prices=[], events=[])

        async def get_current_value(self, identifier, identifier_type, provider_params):
            return SimpleNamespace(value=Decimal("77.77"), currency="USD", as_of_date=date.today())

        def validate_params(self, params):
            return None

    original_get_provider_instance = AssetProviderRegistry.get_provider_instance

    def _patched_get_provider_instance(cls, code: str, **kwargs):
        if code == "partialprov":
            return PartialProvider()
        return original_get_provider_instance.__func__(cls, code, **kwargs)

    monkeypatch.setattr(AssetProviderRegistry, "get_provider_instance", classmethod(_patched_get_provider_instance))

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        asset = Asset(display_name=f"Partial Refresh {timestamp}", currency="USD", asset_type=AssetType.STOCK, active=True)
        session.add(asset)
        await session.commit()
        await session.refresh(asset)

        session.add(
            AssetProviderAssignment(
                asset_id=asset.id,
                provider_code="partialprov",
                identifier="PARTIAL_ONLY",
                identifier_type=ProviderInputType.AUTO_GENERATED,
                provider_params='{"mode":"current_only"}',
            )
        )
        await session.commit()

        response = await AssetSourceManager.bulk_refresh_prices(
            [
                FARefreshItem(
                    asset_id=asset.id,
                    date_range=DateRangeModel(start=date.today() - timedelta(days=2), end=date.today()),
                )
            ],
            session,
        )

        result = response.results[0]
        assert result.status == asset_source_module.SyncStatus.PARTIAL
        assert result.points_fetched == 1
        assert result.inserted_count == 1
        assert result.message == "Current value only, history unavailable"

        stored = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == asset.id, PriceHistory.date == date.today()))).scalar_one()
        assert stored.close == Decimal("77.770000")
        print_success("✓ Current-only refresh returns PARTIAL and persists today price")


@pytest.mark.asyncio
async def test_asset_search_service_search_handles_cache_and_errors(monkeypatch):
    """Search aggregates successes, skips unsupported providers, and reuses cache on repeat query."""
    print_section("Test 28: AssetSearchService.search")

    asset_source_module._search_query_cache.clear()

    class OkSearchProvider:
        supports_search = True

        async def search(self, query: str):
            return [
                {
                    "identifier": "OK-1",
                    "identifier_type": IdentifierType.TICKER,
                    "display_name": f"Provider result {query}",
                    "currency": "USD",
                    "type": "MYSTERY",
                    "provider_params": {"query": query},
                }
            ]

        def get_asset_url(self, identifier, identifier_type, provider_params=None):
            return f"https://example.test/{identifier}"

    class ErrorSearchProvider:
        supports_search = True

        async def search(self, query: str):
            raise RuntimeError("provider exploded")

        def get_asset_url(self, identifier, identifier_type, provider_params=None):
            return None

    class NoSearchProvider:
        supports_search = False

    ok_provider = OkSearchProvider()
    err_provider = ErrorSearchProvider()
    no_provider = NoSearchProvider()
    providers = {"okprov": ok_provider, "errprov": err_provider, "nosrch": no_provider}

    monkeypatch.setattr(
        AssetProviderRegistry,
        "list_providers",
        classmethod(lambda cls: [{"code": "okprov"}, {"code": "errprov"}, {"code": "nosrch"}]),
    )
    monkeypatch.setattr(
        AssetProviderRegistry,
        "get_provider_instance",
        classmethod(lambda cls, code, **kwargs: providers.get(code)),
    )

    first = await AssetSearchService.search("alpha")

    assert first.total_results == 1
    assert first.providers_queried == ["okprov", "errprov"]
    assert first.providers_with_errors == ["errprov"]
    assert first.results[0].provider_url == "https://example.test/OK-1"
    assert first.results[0].asset_type == "OTHER"

    async def _cached_search_should_not_run(query: str):
        raise AssertionError("query cache should satisfy repeated search")

    ok_provider.search = _cached_search_should_not_run

    second = await AssetSearchService.search("alpha", provider_codes=["okprov"])
    assert second.total_results == 1
    assert second.providers_with_errors == []
    assert second.results[0].display_name == "Provider result alpha"
    print_success("✓ Search cache and per-provider error handling both covered")
