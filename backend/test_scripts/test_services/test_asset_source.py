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

from backend.app.utils.decimal_utils import get_price_column_precision, truncate_price_to_db_precision

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
    calculate_daily_factor_between_act365,
    find_active_rate,
    calculate_accrued_interest,
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
            precision, scale = get_price_column_precision(col)
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
            result = truncate_price_to_db_precision(input_val)
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
            result = calculate_daily_factor_between_act365(start, end)

            # Detailed logging per case
            print_info(f"Case: start={start} end={end} | expected={expected} | actual={result}")

            assert result == expected, f"Mismatch: {result} != {expected} for period {start} to {end}"
            print_success(f"✓ ACT/365 OK for {start} to {end} -> {result}")

        return {"passed": True, "message": f"All {len(test_cases)} ACT/365 test cases passed"}
    except Exception as e:
        print_error(f"Error during ACT/365 test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


def test_find_active_rate():
    """Test find_active_rate() for synthetic yield."""
    print_section("Test 4: Find Active Rate (Synthetic Yield)")

    try:
        from backend.app.schemas.assets import InterestRatePeriod, LateInterestConfig

        # Convert dict to Pydantic models (required by function)
        schedule = [
            InterestRatePeriod(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), rate=Decimal("0.05")),
            InterestRatePeriod(start_date=date(2026, 1, 1), end_date=date(2026, 12, 31), rate=Decimal("0.06"))
            ]
        maturity = date(2026, 12, 31)
        late_interest = LateInterestConfig(rate=Decimal("0.12"), grace_period_days=30)

        test_cases = [
            (date(2025, 6, 15), Decimal("0.05"), "Mid-2025 (first period)"),
            (date(2026, 6, 15), Decimal("0.06"), "Mid-2026 (second period)"),
            (date(2026, 12, 31), Decimal("0.06"), "Maturity date"),
            (date(2027, 1, 15), Decimal("0.06"), "15 days after maturity (grace period)"),
            (date(2027, 2, 15), Decimal("0.12"), "45 days after maturity (late interest)"),
            ]

        for target, expected, desc in test_cases:
            result = find_active_rate(schedule, target, maturity, late_interest)
            print_info(f"Case: {desc} | expected={expected} | actual={result}")
            assert result == expected, f"Mismatch for {desc}: {result} != {expected}"
            print_success(f"✓ {desc} -> {result}")

        return {"passed": True, "message": f"All {len(test_cases)} find_active_rate cases passed"}
    except Exception as e:
        print_error(f"Error during find_active_rate test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


def test_calculate_accrued_interest():
    """Test calculate_accrued_interest() for synthetic yield."""
    print_section("Test 5: Calculate Accrued Interest (Synthetic Yield)")

    try:
        from backend.app.schemas.assets import InterestRatePeriod

        face_value = Decimal("10000")
        # Convert dict to Pydantic model (required by function)
        schedule = [
            InterestRatePeriod(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), rate=Decimal("0.05"))
            ]
        maturity = date(2025, 12, 31)
        late_interest = None

        # Test: 30 days at 5%
        start = date(2025, 1, 1)
        end = date(2025, 1, 30)

        interest = calculate_accrued_interest(
            face_value=face_value,
            start_date=start,
            end_date=end,
            schedule=schedule,
            maturity_date=maturity,
            late_interest=late_interest
            )

        # Expected: 10000 * 0.05 * (30/365) = 41.0958...
        expected = Decimal("10000") * Decimal("0.05") * Decimal("30") / Decimal("365")
        diff = abs(interest - expected)

        print_info(f"Case: 30 days at 5% | expected={expected:.2f} | actual={interest:.2f} | diff={diff:.4f}")

        assert diff < Decimal("0.01"), f"Difference too large: {diff}"
        print_success(f"✓ Accrued interest calculation OK: {interest:.2f}")

        return {"passed": True, "message": f"Accrued interest calculation passed (diff < 0.01)"}
    except Exception as e:
        print_error(f"Error during accrued interest test: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


# ============================================================================
# PROVIDER ASSIGNMENT TESTS
# ============================================================================


async def test_bulk_assign_providers():
    """Test bulk_assign_providers() method."""
    print_section("Test 4: Bulk Assign Providers")

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
    print_section("Test 5: Single Assign Provider (calls bulk)")

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


async def test_bulk_remove_providers(asset_ids: list[int]):
    """Test bulk_remove_providers() method."""
    print_section("Test 6: Bulk Remove Providers")

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
    print_section("Test 7: Single Remove Provider (calls bulk)")

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
    print_section("Test 8: Bulk Upsert Prices")

    try:
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            # Upsert prices for 2 assets
            data = [
                {
                    "asset_id": asset_ids[0],
                    "prices": [
                        {"date": date(2025, 1, 1), "close": Decimal("100.50"), "currency": "USD"},
                        {"date": date(2025, 1, 2), "close": Decimal("101.25"), "currency": "USD"},
                        ]
                    },
                {
                    "asset_id": asset_ids[1],
                    "prices": [
                        {"date": date(2025, 1, 1), "close": Decimal("200.00"), "currency": "USD"},
                        ]
                    },
                ]

            result = await AssetSourceManager.bulk_upsert_prices(data, session)

            # Detailed logging of DB state per asset
            for item in data:
                stmt = select(PriceHistory).where(PriceHistory.asset_id == item["asset_id"])
                db_result = await session.execute(stmt)
                prices = db_result.scalars().all()
                print_info(f"Asset {item['asset_id']} prices in DB: {[(p.date, p.close) for p in prices]}")

            # Verify in DB
            stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_ids[0])
            db_result = await session.execute(stmt)
            prices = db_result.scalars().all()

            assert len(prices) == 2, f"Expected 2 prices, got {len(prices)}"

            return {"passed": True, "message": f"Bulk upserted {result['inserted_count']} prices successfully", "inserted_count": result.get('inserted_count', 0)}
    except Exception as e:
        print_error(f"Exception in bulk_upsert_prices: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_single_upsert_prices(asset_ids: list[int]):
    """Test upsert_prices() single method (calls bulk)."""
    print_section("Test 9: Single Upsert Prices (calls bulk)")

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
    print_section("Test 10: Get Prices with Backward-Fill")

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
                bf = p.get("backward_fill_info")
                if bf:
                    print_info(f"{p['date']}: {p['close']} (backfilled from {bf.get('actual_rate_date')} , days_back={bf.get('days_back')})")
                else:
                    print_info(f"{p['date']}: {p['close']} (exact)")

            # Count backfilled dates
            backfilled = [p for p in prices if p.get("backward_fill_info")]

            return {
                "passed": True,
                "message": f"Queried 5 days, got {len(prices)} prices ({len(backfilled)} backfilled)",
                "backfilled_count": len(backfilled)
                }
    except Exception as e:
        print_error(f"Exception in get_prices_with_backfill: {e}")
        return {"passed": False, "message": f"Failed: {str(e)}"}


async def test_bulk_delete_prices(asset_ids: list[int]):
    """Test bulk_delete_prices() method."""
    print_section("Test 11: Bulk Delete Prices")

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

    helper_find_rate = test_find_active_rate()
    print_result_detail("Find Active Rate", helper_find_rate)

    helper_accrued = test_calculate_accrued_interest()
    print_result_detail("Calculate Accrued Interest", helper_accrued)

    # Run the bulk assign first to retrieve asset_ids for dependent tests
    bulk_assign_result = await test_bulk_assign_providers()
    print_result_detail("Bulk Assign Providers", bulk_assign_result)
    asset_ids = bulk_assign_result.get("asset_ids", []) if isinstance(bulk_assign_result, dict) else []

    # Build results dict with full result objects
    full_results = {
        "Price Column Precision": helper_price_precision,
        "Price Truncation": helper_truncate,
        "ACT/365 Calculation": helper_act365,
        "Find Active Rate": helper_find_rate,
        "Calculate Accrued Interest": helper_accrued,
        "Bulk Assign Providers": bulk_assign_result,
        }

    if asset_ids:
        # Await and insert dependent async tests directly into the dict
        full_results["Single Assign Provider"] = await test_single_assign_provider(asset_ids)
        print_result_detail("Single Assign Provider", full_results["Single Assign Provider"])

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

        full_results["Bulk Delete Prices"] = await test_bulk_delete_prices(asset_ids)
        print_result_detail("Bulk Delete Prices", full_results["Bulk Delete Prices"])
    else:
        # Mark dependent tests as skipped/failed if no assets were created
        skipped_result = {"passed": False, "message": "Skipped (no assets created)", "asset_ids": []}
        for key in [
            "Single Assign Provider",
            "Bulk Remove Providers",
            "Single Remove Provider",
            "Bulk Upsert Prices",
            "Single Upsert Prices",
            "Get Prices (Backward-Fill)",
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
