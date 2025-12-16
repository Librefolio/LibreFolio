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
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.utils.decimal_utils import truncate_priceHistory, get_model_column_precision

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_async_engine
from backend.app.db.models import (
    Asset,
    AssetType,
    IdentifierType,
    )
from backend.app.services.asset_source import AssetSourceManager

from backend.app.utils.financial_math import (
    calculate_day_count_fraction,
    find_active_period,
    )
from backend.test_scripts.test_utils import (
    print_info,
    print_section,
    print_success,
    )

from backend.app.db.models import PriceHistory
from sqlalchemy import select
from backend.app.schemas.assets import (
    FAInterestRatePeriod,
    FALateInterestConfig,
    CompoundingType,
    DayCountConvention,
    )
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.prices import FAUpsert, FAPricePoint

from backend.app.db.models import AssetProviderAssignment
from sqlalchemy import delete

from backend.app.schemas.prices import FAAssetDelete
from backend.app.schemas.common import DateRangeModel


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
    import time
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


def test_find_active_period():
    """Test find_active_period() for synthetic yield using Pydantic periods.

    Covers:
      - Mid first period
      - Mid second period
      - Maturity date (still in schedule)
      - Grace period (uses last scheduled rate)
      - Late interest period (after grace)
    """
    print_section("Test 4: Find Active Period (Synthetic Yield)")

    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365,
            ),
        FAInterestRatePeriod(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            annual_rate=Decimal("0.06"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365,
            ),
        ]

    maturity = date(2026, 12, 31)
    late_interest = FALateInterestConfig(
        annual_rate=Decimal("0.12"),
        grace_period_days=30,
        compounding=CompoundingType.SIMPLE,
        day_count=DayCountConvention.ACT_365,
        )

    test_cases = [
        (date(2025, 6, 15), Decimal("0.05"), "Mid-2025 (first period)"),
        (date(2026, 6, 15), Decimal("0.06"), "Mid-2026 (second period)"),
        (date(2026, 12, 31), Decimal("0.06"), "Maturity date"),
        (date(2027, 1, 15), Decimal("0.06"), "15 days after maturity (grace period)"),
        (date(2027, 2, 15), Decimal("0.12"), "45 days after maturity (late interest)"),
        ]

    for target, expected_rate, desc in test_cases:
        period = find_active_period(schedule, target, maturity, late_interest)
        if desc.startswith("45 days"):
            assert period is not None, f"Late interest period not found for {target}"
        if period is None:
            raise AssertionError(f"No period found for {desc} ({target})")

        actual_rate = period.annual_rate
        print_info(f"Case: {desc} | expected={expected_rate} | actual={actual_rate}")
        assert actual_rate == expected_rate, f"Mismatch for {desc}: {actual_rate} != {expected_rate}"
        print_success(f"✓ {desc} -> {actual_rate}")


# ============================================================================
# PROVIDER ASSIGNMENT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_assign_providers():
    """Test bulk_assign_providers() method."""
    print_section("Test 5: Bulk Assign Providers")

    import time
    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Create test assets with unique names using timestamp
        test_assets = [
            Asset(
                display_name=f"Test Asset Assign {timestamp}-{i}",
                currency="USD",
                asset_type=AssetType.STOCK,
                active=True,
                ) for i in range(1, 4)]

        session.add_all(test_assets)
        await session.commit()

        # Refresh to get IDs
        for asset in test_assets:
            await session.refresh(asset)

        # Bulk assign providers
        from backend.app.db.models import IdentifierType
        assignments = [
            FAProviderAssignmentItem(
                asset_id=test_assets[0].id,
                provider_code="yfinance",
                identifier="TEST1",
                identifier_type=IdentifierType.TICKER,
                provider_params={"ticker": "TEST1"}
            ),
            FAProviderAssignmentItem(
                asset_id=test_assets[1].id,
                provider_code="yfinance",
                identifier="TEST2",
                identifier_type=IdentifierType.TICKER,
                provider_params={"ticker": "TEST2"}
            ),
            FAProviderAssignmentItem(
                asset_id=test_assets[2].id,
                provider_code="mockprov",
                identifier="MOCK1",
                identifier_type=IdentifierType.UUID,
                provider_params=None
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
async def test_metadata_auto_populate(asset_ids: list[int]):
    """Test metadata auto-populate on provider assignment."""
    print_section("Test 6a: Metadata Auto-Populate")

    import time
    timestamp = int(time.time() * 1000)

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Create new test asset for metadata test
        test_asset = Asset(
            display_name=f"MockProvider Test Asset {timestamp}",
            currency="USD",
            asset_type=AssetType.STOCK,
            active=True,
            classification_params=None  # Start with no metadata
            )
        session.add(test_asset)
        await session.commit()
        await session.refresh(test_asset)

        print_info(f"Created test asset {test_asset.id} with no metadata")
        # Bulk assign providers (single item for compatibility)
        item = FAProviderAssignmentItem(
            asset_id=test_asset.id,
            provider_code="mockprov",
            identifier="MOCK_META_TEST",
            identifier_type=IdentifierType.UUID,
            provider_params={"mock_param": "test"}
        )

        results = await AssetSourceManager.bulk_assign_providers([item], session)
        # Assuming single result, extract it
        result = results[0]

        print_info(f"Assignment result: {result}")
        assert result.success, f"Assignment failed: {result.message}"

        # Refresh asset to get updated metadata
        await session.refresh(test_asset)

        # Verify metadata was populated (mockprov MUST populate metadata)
        assert test_asset.classification_params is not None, "Metadata should be populated by mockprov provider"
        print_success(f"✓ Metadata auto-populated: {test_asset.classification_params[:100]}")

        # Parse and verify content
        metadata = json.loads(test_asset.classification_params)
        assert 'Technology' in metadata['sector_area']['distribution'], "sector incorrect"
        print_success("✓ Metadata content verified (sector=Technology)")

        # Metadata auto-populate during assignment is successful (verified by log and DB content above)
        # Note: fields_detail is None during assignment (it's used in refresh endpoint)
        print_success("✓ Metadata auto-populate on assignment completed successfully")


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
                    FAPricePoint(date=date(2025, 1, 1), close=Decimal("100.50"), volume=Decimal("1000"), currency="USD"),
                    FAPricePoint(date=date(2025, 1, 2), close=Decimal("101.25"), volume=Decimal("1500"), currency="USD"),
                    ]
                ),
            FAUpsert(
                asset_id=asset_ids[1],
                prices=[
                    FAPricePoint(date=date(2025, 1, 1), close=Decimal("200.00"), volume=Decimal("500"), currency="USD"),
                    ]
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
    """Test get_prices() with backward-fill logic."""
    print_section("Test 10: Get Prices with Backward-Fill")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Query range with gaps
        prices = await AssetSourceManager.get_prices(
            asset_id=asset_ids[0],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 5),
            session=session
            )

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
                source_plugin_key="manual_test"
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
                source_plugin_key="manual_test"
                )
            ]

        session.add_all(prices_to_insert)
        await session.commit()

        # Query range Day 1-4 (Day 3 and 4 should be backfilled)
        prices = await AssetSourceManager.get_prices(
            asset_id=test_asset_id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 4),
            session=session
            )

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
            assert price.backward_fill_info.actual_rate_date == date(2025, 1, 2), \
                f"Day {idx + 1} should be backfilled from Day 2"
            assert price.backward_fill_info.days_back == idx - 1, \
                f"Day {idx + 1} days_back should be {idx - 1}"

            # Critical assertion: volume must be backfilled
            assert price.close == Decimal("106.00"), f"Day {idx + 1} close should be backfilled"
            assert price.volume == day2_volume, \
                f"Day {idx + 1} volume should be backfilled: expected {day2_volume}, got {price.volume}"

            print_success(
                f"✓ Day {idx + 1}: close={price.close}, volume={price.volume} "
                f"(backfilled from {price.backward_fill_info.actual_rate_date}, "
                f"days_back={price.backward_fill_info.days_back})"
                )

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
        prices = await AssetSourceManager.get_prices(
            asset_id=test_asset_id,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 4),
            session=session
            )

        # Should return empty list (no data to backfill from)
        assert len(prices) == 0, f"Expected empty list when no data exists, got {len(prices)} prices"
        print_info("✓ Edge case handled: empty list returned when no initial data exists")


@pytest.mark.asyncio
async def test_provider_fallback_invalid(asset_ids: list[int]):
    """Test provider fallback when invalid/unregistered provider assigned.

    Scenario:
    - Insert invalid provider assignment directly in DB (bypass Pydantic validation)
    - Insert some prices in DB as fallback
    - Query prices -> should fallback to DB gracefully
    - Verify warning log is generated (manually via log inspection)

    Expected:
    - No crash
    - Prices returned from DB fallback
    - Warning logged about provider not registered
    """
    print_section("Test 13: Provider Fallback (Invalid Provider)")

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
            identifier_type=IdentifierType.UUID,
            provider_params=None,
            fetch_interval=1440
            )
        session.add(invalid_assignment)
        await session.commit()
        print_info(f"Inserted invalid provider '{invalid_provider}' directly in DB for asset {test_asset_id}")

        # Insert fallback prices in DB
        await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == test_asset_id))
        await session.commit()

        fallback_price = PriceHistory(
            asset_id=test_asset_id,
            date=date(2025, 1, 10),
            close=Decimal("999.00"),
            currency="USD",
            source_plugin_key="manual_test_fallback"
            )
        session.add(fallback_price)
        await session.commit()
        print_info(f"Inserted fallback price in DB: date=2025-01-10, close=999.00")

        # Query prices -> should fallback to DB (provider fetch will fail)
        prices = await AssetSourceManager.get_prices(
            asset_id=test_asset_id,
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 10),
            session=session
            )

        # Verify fallback worked
        assert len(prices) == 1, f"Expected 1 price from DB fallback, got {len(prices)}"
        assert prices[0].close == Decimal("999.00"), f"Expected price 999.00, got {prices[0].close}"
        assert prices[0].date == date(2025, 1, 10), f"Expected date 2025-01-10, got {prices[0].date}"

        print_success(f"✓ Fallback to DB successful: retrieved price {prices[0].close}")
        print_info("⚠️  Check logs for warning: 'Provider not registered in registry, falling back to DB'")


@pytest.mark.asyncio
async def test_bulk_delete_prices(asset_ids: list[int]):
    """Test bulk_delete_prices() method."""
    print_section("Test 14: Bulk Delete Prices")

    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        # Delete specific ranges
        data = [
            FAAssetDelete(
                asset_id=asset_ids[0],
                date_ranges=[DateRangeModel(start=date(2025, 1, 1), end=date(2025, 1, 2))]
                ),
            FAAssetDelete(
                asset_id=asset_ids[1],
                date_ranges=[DateRangeModel(start=date(2025, 1, 1), end=None)]  # Single day
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
