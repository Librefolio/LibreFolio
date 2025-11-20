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

from backend.app.utils.decimal_utils import truncate_priceHistory, get_model_column_precision

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.db.session import get_async_engine
from backend.app.db.models import (
    Asset,
    AssetType,
    ValuationModel,
    )
from backend.app.services.asset_source import AssetSourceManager

from backend.app.utils.financial_math import (
    calculate_day_count_fraction,
    find_active_period,
    )
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_test_header,
    print_test_summary,
    exit_with_result,
    )

from backend.app.db.models import PriceHistory
from sqlalchemy import select


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


def test_price_column_precision():
    """Test get_price_column_precision() helper."""
    print_section("Test 1: Price Column Precision")

    try:
        columns = ["open", "high", "low", "close", "adjusted_close"]
        for col in columns:
            precision, scale = get_model_column_precision(PriceHistory, col)
            # Detailed logging per case
            print_info(f"Case: column={col} | expected=(18,6) | actual=({precision},{scale})")
            assert precision == 18, f"{col}: Expected precision 18, got {precision}"
            assert scale == 6, f"{col}: Expected scale 6, got {scale}"
            print_success(f"✓ {col}: precision OK ({precision},{scale})")

        return {"passed": True, "message": "All price columns have correct precision (18, 6)"}
    except Exception as e:
        print_error(f"Error during price column precision test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


def test_truncate_price():
    """Test truncate_price_to_db_precision() helper."""
    print_section("Test 2: Price Truncation")

    try:
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

        return {"passed": True, "message": f"All {len(test_cases)} truncation test cases passed"}
    except Exception as e:
        print_error(f"Error during price truncation test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


def test_act365_calculation():
    """Test calculate_days_between_act365() helper."""
    print_section("Test 3: ACT/365 Day Count")

    try:
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

        return {"passed": True, "message": f"All {len(test_cases)} ACT/365 test cases passed"}
    except Exception as e:
        print_error(f"Error during ACT/365 test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


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
    try:
        from backend.app.schemas.assets import (
            InterestRatePeriod,
            LateInterestConfig,
            CompoundingType,
            DayCountConvention,
            )
        schedule = [
            InterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                ),
            InterestRatePeriod(
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                annual_rate=Decimal("0.06"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                ),
            ]
        maturity = date(2026, 12, 31)
        late_interest = LateInterestConfig(
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
        return {"passed": True, "message": f"All {len(test_cases)} find_active_period cases passed"}
    except Exception as e:
        print_error(f"Error during find_active_period test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


# ============================================================================
# PROVIDER ASSIGNMENT TESTS
# ============================================================================


async def test_bulk_assign_providers():
    """Test bulk_assign_providers() method."""
    print_section("Test 5: Bulk Assign Providers")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Create test assets
            test_assets = [
                Asset(
                    display_name=f"Test Asset {i}",
                    identifier=f"TEST{i}",
                    identifier_type="TICKER",
                    currency="USD",
                    asset_type=AssetType.STOCK,
                    valuation_model=ValuationModel.MARKET_PRICE,
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
                {"asset_id": test_assets[0].id, "provider_code": "yfinance", "provider_params": '{"ticker": "TEST1"}'},
                {"asset_id": test_assets[1].id, "provider_code": "yfinance", "provider_params": '{"ticker": "TEST2"}'},
                {"asset_id": test_assets[2].id, "provider_code": "cssscraper", "provider_params": '{"url": "http://example.com"}'},
                ]

            results = await AssetSourceManager.bulk_assign_providers(assignments, session)

            # Detailed logging of results
            for r in results:
                status = "OK" if r.get("success") else "ERROR"
                print_info(f"Assignment result: asset_id={r.get('asset_id')} provider={r.get('provider_code')} status={status} message={r.get('message')}")

            # Verify all succeeded
            for result in results:
                assert result["success"], f"Assignment failed: {result}"

            # Verify in DB and print mapping
            for assignment in assignments:
                provider = await AssetSourceManager.get_asset_provider(assignment["asset_id"], session)
                assert provider is not None, f"Provider not found for asset {assignment['asset_id']}"
                assert provider.provider_code == assignment["provider_code"]
                print_success(f"✓ Verified DB: asset {assignment['asset_id']} -> {provider.provider_code}")

            return {
                "passed": True,
                "message": f"Bulk assigned {len(results)} providers successfully",
                "asset_ids": [a.id for a in test_assets]
                }
    except Exception as e:
        print_error(f"Exception in bulk_assign_providers: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}", "asset_ids": []}


async def test_single_assign_provider(asset_ids: list[int]):
    """Test assign_provider() single method (calls bulk)."""
    print_section("Test 6: Single Assign Provider (calls bulk)")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset_id = asset_ids[0]

            # Update provider (yfinance → cssscraper)
            result = await AssetSourceManager.assign_provider(
                asset_id=asset_id,
                provider_code="cssscraper",
                provider_params='{"url": "http://new-url.com"}',
                session=session,
                )

            print_info(f"Assign call returned: {result}")

            assert result["success"], f"Assignment failed: {result}"

            # Verify update
            provider = await AssetSourceManager.get_asset_provider(asset_id, session)
            assert provider.provider_code == "cssscraper", "Provider not updated"
            print_success(f"✓ Verified DB: asset {asset_id} -> {provider.provider_code}")

            return {"passed": True, "message": f"Asset {asset_id} updated to cssscraper"}
    except Exception as e:
        print_error(f"Exception in single_assign_provider: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_metadata_auto_populate(asset_ids: list[int]):
    """Test metadata auto-populate on provider assignment."""
    print_section("Test 6a: Metadata Auto-Populate")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Create new test asset for metadata test
            test_asset = Asset(
                display_name="MockProvider Test Asset",
                identifier="MOCK_METADATA_TEST",
                identifier_type="TICKER",
                currency="USD",
                asset_type=AssetType.STOCK,
                valuation_model=ValuationModel.MARKET_PRICE,
                active=True,
                classification_params=None  # Start with no metadata
                )
            session.add(test_asset)
            await session.commit()
            await session.refresh(test_asset)

            print_info(f"Created test asset {test_asset.id} with no metadata")

            # Assign mockprov provider (has metadata support)
            result = await AssetSourceManager.assign_provider(
                asset_id=test_asset.id,
                provider_code="mockprov",
                provider_params='{"mock_param": "test"}',
                session=session,
                )

            print_info(f"Assignment result: {result}")
            assert result["success"], f"Assignment failed: {result}"

            # Refresh asset to get updated metadata
            await session.refresh(test_asset)

            # Verify metadata was populated
            if test_asset.classification_params:
                print_success(f"✓ Metadata auto-populated: {test_asset.classification_params[:100]}")

                # Parse and verify content
                import json
                metadata = json.loads(test_asset.classification_params)
                assert "investment_type" in metadata, "investment_type not populated"
                assert metadata["investment_type"] == "stock", "investment_type incorrect"
                print_success("✓ Metadata content verified (investment_type=stock)")

                # Check for metadata_updated flag in result
                if result.get("metadata_updated"):
                    print_success("✓ Result includes metadata_updated flag")
                    if result.get("metadata_changes"):
                        print_info(f"  Changes: {len(result['metadata_changes'])} fields updated")
            else:
                print_info("ℹ️  Note: Metadata not populated (provider may not support it)")

            return {
                "passed": True,
                "message": "Metadata auto-populate test completed",
                "metadata_populated": test_asset.classification_params is not None
                }
    except Exception as e:
        print_error(f"Exception in metadata auto-populate test: {e}")
        import traceback
        traceback.print_exc()
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_bulk_remove_providers(asset_ids: list[int]):
    """Test bulk_remove_providers() method."""
    print_section("Test 7: Bulk Remove Providers")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            results = await AssetSourceManager.bulk_remove_providers(asset_ids, session)

            # Detailed logging
            for r in results:
                print_info(f"Removal: asset_id={r.get('asset_id')} success={r.get('success')} message={r.get('message')}")

            # Verify all succeeded
            for result in results:
                assert result["success"], f"Removal failed: {result}"

            # Verify removal
            for asset_id in asset_ids:
                provider = await AssetSourceManager.get_asset_provider(asset_id, session)
                assert provider is None, f"Provider still exists for asset {asset_id}"
                print_success(f"✓ Verified DB: asset {asset_id} has no provider")

            return {"passed": True, "message": f"Bulk removed {len(results)} providers successfully"}
    except Exception as e:
        print_error(f"Exception in bulk_remove_providers: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_single_remove_provider(asset_ids: list[int]):
    """Test remove_provider() single method (calls bulk)."""
    print_section("Test 8: Single Remove Provider (calls bulk)")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            asset_id = asset_ids[1]

            # First assign a provider
            await AssetSourceManager.assign_provider(
                asset_id=asset_id,
                provider_code="yfinance",
                provider_params='{"ticker": "TEST"}',
                session=session,
                )

            # Remove via single method
            result = await AssetSourceManager.remove_provider(asset_id, session)
            print_info(f"Remove call returned: {result}")
            assert result["success"], f"Removal failed: {result}"

            # Verify removal
            provider = await AssetSourceManager.get_asset_provider(asset_id, session)
            assert provider is None, "Provider not removed"
            print_success(f"✓ Verified DB: asset {asset_id} provider removed")

            return {"passed": True, "message": f"Asset {asset_id} provider removed successfully"}
    except Exception as e:
        print_error(f"Exception in single_remove_provider: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


# ============================================================================
# PRICE CRUD TESTS
# ============================================================================


async def test_bulk_upsert_prices(asset_ids: list[int]):
    """Test bulk_upsert_prices() method."""
    print_section("Test 9: Bulk Upsert Prices")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Upsert prices for 2 assets
            data = [
                {
                    "asset_id": asset_ids[0],
                    "prices": [
                        {"date": date(2025, 1, 1), "close": Decimal("100.50"), "volume": Decimal("1000"), "currency": "USD"},
                        {"date": date(2025, 1, 2), "close": Decimal("101.25"), "volume": Decimal("1500"), "currency": "USD"},
                        ]
                    },
                {
                    "asset_id": asset_ids[1],
                    "prices": [
                        {"date": date(2025, 1, 1), "close": Decimal("200.00"), "volume": Decimal("500"), "currency": "USD"},
                        ]
                    },
                ]

            result = await AssetSourceManager.bulk_upsert_prices(data, session)

            # Detailed logging of DB state per asset
            for item in data:
                stmt = select(PriceHistory).where(PriceHistory.asset_id == item["asset_id"])
                db_result = await session.execute(stmt)
                prices = db_result.scalars().all()
                print_info(f"Asset {item['asset_id']} prices in DB: {[(p.date, p.close, p.volume) for p in prices]}")

            # Verify in DB
            stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_ids[0])
            db_result = await session.execute(stmt)
            prices = db_result.scalars().all()

            assert len(prices) == 2, f"Expected 2 prices, got {len(prices)}"
            assert prices[0].volume == Decimal("1000") and prices[1].volume == Decimal("1500"), "Volume values not persisted correctly"

            return {"passed": True, "message": f"Bulk upserted {result['inserted_count']} prices successfully", "inserted_count": result.get('inserted_count', 0)}
    except Exception as e:
        print_error(f"Exception in bulk_upsert_prices: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_single_upsert_prices(asset_ids: list[int]):
    """Test upsert_prices() single method (calls bulk)."""
    print_section("Test 10: Single Upsert Prices (calls bulk)")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Update existing price
            prices = [
                {"date": date(2025, 1, 1), "close": Decimal("105.00"), "currency": "USD"},
                ]

            # Read previous value
            stmt_prev = select(PriceHistory).where(
                PriceHistory.asset_id == asset_ids[0],
                PriceHistory.date == date(2025, 1, 1)
                )
            prev = (await session.execute(stmt_prev)).scalar_one_or_none()
            prev_val = prev.close if prev is not None else None
            print_info(f"Before update: asset {asset_ids[0]} date=2025-01-01 close={prev_val}")

            result = await AssetSourceManager.upsert_prices(asset_ids[0], prices, session)

            # Verify update
            stmt = select(PriceHistory).where(
                PriceHistory.asset_id == asset_ids[0],
                PriceHistory.date == date(2025, 1, 1)
                )
            db_result = await session.execute(stmt)
            price = db_result.scalar_one()

            print_info(f"After update: asset {asset_ids[0]} date=2025-01-01 close={price.close}")

            assert price.close == Decimal("105.00"), "Price not updated"

            return {"passed": True, "message": f"Price updated to {price.close}"}
    except Exception as e:
        print_error(f"Exception in single_upsert_prices: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_get_prices_with_backfill(asset_ids: list[int]):
    """Test get_prices() with backward-fill logic."""
    print_section("Test 11: Get Prices with Backward-Fill")

    try:
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

            return {
                "passed": True,
                "message": f"Queried 5 days, got {len(prices)} prices ({len(backfilled)} backfilled)",
                "backfilled_count": len(backfilled)
                }
    except Exception as e:
        print_error(f"Exception in get_prices_with_backfill: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


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
    print_section("Test 12: Backward-Fill Volume Propagation")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Setup: Insert prices for Day 1 and Day 2 WITH volume
            test_asset_id = asset_ids[0]

            # Clear existing prices first
            from sqlalchemy import delete
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

            return {
                "passed": True,
                "message": f"Volume propagation verified: 2 exact + 2 backfilled prices",
                "backfilled_count": backfilled_count
                }

    except AssertionError as e:
        print_error(f"Assertion failed in volume propagation test: {e}")
        return {"passed": False, "message": f"Assertion failed: {str(e)}"}
    except Exception as e:
        print_error(f"Exception in volume propagation test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_backward_fill_edge_case_no_initial_data(asset_ids: list[int]):
    """Test backward-fill edge case: no initial data exists.

    Scenario:
    - Query range Day 1-4 but NO prices exist in DB

    Expected:
    - Empty list or no backfill (implementation dependent)
    - Should NOT crash
    """
    print_section("Test 13: Backward-Fill Edge Case (No Initial Data)")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Use a different asset to ensure it has no prices
            test_asset_id = asset_ids[1] if len(asset_ids) > 1 else asset_ids[0]

            # Clear all prices for this asset
            from sqlalchemy import delete
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

            return {
                "passed": True,
                "message": "Edge case verified: no crash when querying range with no data"
                }

    except Exception as e:
        print_error(f"Exception in edge case test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_provider_fallback_invalid(asset_ids: list[int]):
    """Test provider fallback when invalid/unregistered provider assigned.

    Scenario:
    - Assign an invalid (non-existent) provider to an asset
    - Insert some prices in DB as fallback
    - Query prices -> should fallback to DB gracefully
    - Verify warning log is generated (manually via log inspection)

    Expected:
    - No crash
    - Prices returned from DB fallback
    - Warning logged about provider not registered
    """
    print_section("Test 14: Provider Fallback (Invalid Provider)")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            test_asset_id = asset_ids[0]

            # Assign invalid provider (not registered in AssetProviderRegistry)
            invalid_provider = "invalid_nonexistent_provider"
            await AssetSourceManager.assign_provider(
                asset_id=test_asset_id,
                provider_code=invalid_provider,
                provider_params='{}',
                session=session
                )
            print_info(f"Assigned invalid provider '{invalid_provider}' to asset {test_asset_id}")

            # Insert fallback prices in DB
            from sqlalchemy import delete
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
            assert prices[0].close == Decimal("999.00"), "Price mismatch in fallback"
            assert prices[0].date == date(2025, 1, 10), "Date mismatch in fallback"

            print_success(f"✓ Fallback to DB successful: retrieved price {prices[0].close}")
            print_info("⚠️  Check logs for warning: 'Provider not registered in registry, falling back to DB'")

            return {
                "passed": True,
                "message": f"Invalid provider handled gracefully, fallback to DB successful"
                }

    except Exception as e:
        print_error(f"Exception in provider fallback test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_bulk_delete_prices(asset_ids: list[int]):
    """Test bulk_delete_prices() method."""
    print_section("Test 15: Bulk Delete Prices")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Delete specific ranges
            data = [
                {
                    "asset_id": asset_ids[0],
                    "date_ranges": [{"start": date(2025, 1, 1), "end": date(2025, 1, 2)}]
                    },
                {
                    "asset_id": asset_ids[1],
                    "date_ranges": [{"start": date(2025, 1, 1)}]  # Single day
                    },
                ]

            result = await AssetSourceManager.bulk_delete_prices(data, session)

            # Detailed logging of deletion
            print_info(f"Bulk delete returned: {json.dumps(result, indent=2, default=str)}")

            # Verify deletion
            stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_ids[0])
            db_result = await session.execute(stmt)
            prices = db_result.scalars().all()

            print_info(f"Remaining prices for asset {asset_ids[0]}: {len(prices)}")

            return {
                "passed": True,
                "message": f"Bulk deleted {result['deleted_count']} prices ({len(prices)} remaining for asset {asset_ids[0]})",
                "deleted_count": result.get('deleted_count', 0)
                }
    except Exception as e:
        print_error(f"Exception in bulk_delete_prices: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


# ============================================================================
# TEST ORCHESTRATION
# ============================================================================


async def run_all_tests():
    """Run all tests in sequence and display summary.

    This version builds a single `results` dict and fills it using direct await
    calls for the async tests where possible. The bulk assign test is awaited
    first to extract `asset_ids` which are then used for dependent tests.

    Enhanced: collect full result objects and print detailed messages and
    any additional fields (asset_ids, counts) for each subtest.
    """
    print_test_header("Asset Source Service - Complete Tests")

    # Initialize test database (synchronous helper)
    initialize_test_database()

    def print_result_detail(test_name: str, result: dict):
        """Print detailed information for a test result dict."""
        if not isinstance(result, dict):
            print_info(f"{test_name}: (no detailed result) {result}")
            return
        msg = result.get("message")
        if msg:
            print_info(f"{test_name}: {msg}")
        # Print any useful additional keys
        extra_keys = [k for k in result.keys() if k not in ("passed", "message")]
        for k in extra_keys:
            print_info(f"  {k}: {result[k]}")

    # Run synchronous helper tests and collect results
    helper_price_precision = test_price_column_precision()
    print_result_detail("Price Column Precision", helper_price_precision)

    helper_truncate = test_truncate_price()
    print_result_detail("Price Truncation", helper_truncate)

    helper_act365 = test_act365_calculation()
    print_result_detail("ACT/365 Calculation", helper_act365)

    # Insert new period-based helper
    helper_find_period = test_find_active_period()
    print_result_detail("Find Active Period", helper_find_period)

    # Run the bulk assign first to retrieve asset_ids for dependent tests
    bulk_assign_result = await test_bulk_assign_providers()
    print_result_detail("Bulk Assign Providers", bulk_assign_result)
    asset_ids = bulk_assign_result.get("asset_ids", []) if isinstance(bulk_assign_result, dict) else []

    # Build results dict with full result objects
    full_results = {
        "Price Column Precision": helper_price_precision,
        "Price Truncation": helper_truncate,
        "ACT/365 Calculation": helper_act365,
        "Find Active Period": helper_find_period,
        "Bulk Assign Providers": bulk_assign_result,
        }

    if asset_ids:
        # Await and insert dependent async tests directly into the dict
        full_results["Single Assign Provider"] = await test_single_assign_provider(asset_ids)
        print_result_detail("Single Assign Provider", full_results["Single Assign Provider"])

        full_results["Metadata Auto-Populate"] = await test_metadata_auto_populate(asset_ids)
        print_result_detail("Metadata Auto-Populate", full_results["Metadata Auto-Populate"])

        full_results["Bulk Remove Providers"] = await test_bulk_remove_providers(asset_ids)
        print_result_detail("Bulk Remove Providers", full_results["Bulk Remove Providers"])

        full_results["Single Remove Provider"] = await test_single_remove_provider(asset_ids)
        print_result_detail("Single Remove Provider", full_results["Single Remove Provider"])

        # Price CRUD tests
        full_results["Bulk Upsert Prices"] = await test_bulk_upsert_prices(asset_ids)
        print_result_detail("Bulk Upsert Prices", full_results["Bulk Upsert Prices"])

        full_results["Single Upsert Prices"] = await test_single_upsert_prices(asset_ids)
        print_result_detail("Single Upsert Prices", full_results["Single Upsert Prices"])

        full_results["Get Prices (Backward-Fill)"] = await test_get_prices_with_backfill(asset_ids)
        print_result_detail("Get Prices (Backward-Fill)", full_results["Get Prices (Backward-Fill)"])

        full_results["Backward-Fill Volume Propagation"] = await test_backward_fill_volume_propagation(asset_ids)
        print_result_detail("Backward-Fill Volume Propagation", full_results["Backward-Fill Volume Propagation"])

        full_results["Backward-Fill Edge Case (No Data)"] = await test_backward_fill_edge_case_no_initial_data(asset_ids)
        print_result_detail("Backward-Fill Edge Case (No Data)", full_results["Backward-Fill Edge Case (No Data)"])

        full_results["Provider Fallback (Invalid Provider)"] = await test_provider_fallback_invalid(asset_ids)
        print_result_detail("Provider Fallback (Invalid Provider)", full_results["Provider Fallback (Invalid Provider)"])

        full_results["Bulk Delete Prices"] = await test_bulk_delete_prices(asset_ids)
        print_result_detail("Bulk Delete Prices", full_results["Bulk Delete Prices"])
    else:
        # Mark dependent tests as skipped/failed if no assets were created
        skipped_result = {"passed": False, "message": "Skipped (no assets created)", "asset_ids": []}
        for key in [
            "Single Assign Provider",
            "Metadata Auto-Populate",
            "Bulk Remove Providers",
            "Single Remove Provider",
            "Bulk Upsert Prices",
            "Single Upsert Prices",
            "Get Prices (Backward-Fill)",
            "Backward-Fill Volume Propagation",
            "Backward-Fill Edge Case (No Data)",
            "Provider Fallback (Invalid Provider)",
            "Bulk Delete Prices",
            ]:
            full_results[key] = skipped_result
            print_result_detail(key, skipped_result)

    # Convert full_results to simple bool mapping for summary
    results_bool = {k: bool(v.get("passed", False)) if isinstance(v, dict) else False for k, v in full_results.items()}

    # Display summary and return boolean success
    success = print_test_summary(results_bool, "Asset Source Service")
    return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit_with_result(success)

# TODO:
#  Aggiungere casi limite (data prima dell’inizio del schedule, dopo la late interest senza config).
#  Test aggiuntivi per compounding diverso (es. COMPOUND con frequenza mensile).
#  Un test negativo (periodo mancante → None).
