"""
Test suite for synthetic yield calculation (SCHEDULED_YIELD assets).

Tests cover:
- find_active_rate() - rate lookup from schedule
- calculate_accrued_interest() - SIMPLE interest calculation
- calculate_synthetic_value() - full valuation
- Integration with get_prices() - automatic calculation
"""
import asyncio
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
import json

# Force test mode BEFORE any other imports
os.environ["LIBREFOLIO_TEST_MODE"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///backend/data/sqlite/test_app.db"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from backend.app.db.models import Asset, ValuationModel, AssetType
from backend.app.utils.financial_math import (
    find_active_rate,
    calculate_accrued_interest,
)
from backend.app.services.asset_source import (
    calculate_synthetic_value,
    AssetSourceManager,
)


# ============================================================================
# TEST DATABASE SETUP
# ============================================================================


async def get_test_session():
    """Create async session for tests."""
    DATABASE_URL = os.environ.get("DATABASE_URL")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        yield session


async def create_test_asset(session: AsyncSession) -> Asset:
    """
    Create test SCHEDULED_YIELD asset with interest schedule.

    Asset details:
    - Type: CROWDFUND_LOAN
    - Valuation: SCHEDULED_YIELD
    - Face value: 10000 EUR
    - Maturity: 2026-12-31 (2 years)
    - Interest schedule:
      - 2025-01-01 to 2025-12-31: 5% annual
      - 2026-01-01 to 2026-12-31: 6% annual
    - Late interest: 12% after 30 days grace
    """
    interest_schedule = [
        {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "rate": "0.05"  # 5%
        },
        {
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "rate": "0.06"  # 6%
        }
    ]

    late_interest = {
        "rate": "0.12",  # 12%
        "grace_period_days": 30
    }

    asset = Asset(
        display_name="Test Recrowd Loan",
        identifier="RECROWD-TEST-001",
        currency="EUR",
        asset_type=AssetType.CROWDFUND_LOAN,
        valuation_model=ValuationModel.SCHEDULED_YIELD,
        face_value=Decimal("10000.00"),
        maturity_date=date(2026, 12, 31),
        interest_schedule=json.dumps(interest_schedule),
        late_interest=json.dumps(late_interest),
    )

    session.add(asset)
    await session.commit()
    await session.refresh(asset)

    return asset


# ============================================================================
# TEST FUNCTIONS
# ============================================================================


def test_find_active_rate_simple_schedule():
    """Test find_active_rate with simple schedule (2 periods)."""
    schedule = [
        {"start_date": "2025-01-01", "end_date": "2025-12-31", "rate": "0.05"},
        {"start_date": "2026-01-01", "end_date": "2026-12-31", "rate": "0.06"}
    ]
    maturity = date(2026, 12, 31)
    late_interest = {"rate": "0.12", "grace_period_days": 30}

    # Test cases
    test_cases = [
        # (target_date, expected_rate, description)
        (date(2025, 6, 15), Decimal("0.05"), "Mid-2025 (first period)"),
        (date(2026, 6, 15), Decimal("0.06"), "Mid-2026 (second period)"),
        (date(2026, 12, 31), Decimal("0.06"), "Maturity date (second period)"),
        (date(2027, 1, 15), Decimal("0.06"), "15 days after maturity (within grace)"),
        (date(2027, 2, 15), Decimal("0.12"), "45 days after maturity (late interest)"),
    ]

    results = []
    for target, expected, desc in test_cases:
        actual = find_active_rate(schedule, target, maturity, late_interest)
        passed = actual == expected
        results.append({
            "test": desc,
            "passed": passed,
            "expected": str(expected),
            "actual": str(actual)
        })

    return {
        "passed": all(r["passed"] for r in results),
        "details": results
    }


def test_find_active_rate_no_late_interest():
    """Test find_active_rate without late interest configuration."""
    schedule = [
        {"start_date": "2025-01-01", "end_date": "2025-12-31", "rate": "0.05"}
    ]
    maturity = date(2025, 12, 31)
    late_interest = None

    # After maturity, should return 0 (no late interest configured)
    target = date(2026, 2, 1)
    result = find_active_rate(schedule, target, maturity, late_interest)

    passed = result == Decimal("0")
    return {
        "passed": passed,
        "message": f"Expected 0 after maturity (no late interest), got {result}"
    }


def test_calculate_accrued_interest_single_rate():
    """Test calculate_accrued_interest with single rate (SIMPLE interest)."""
    face_value = Decimal("10000")
    schedule = [
        {"start_date": "2025-01-01", "end_date": "2025-12-31", "rate": "0.05"}
    ]
    maturity = date(2025, 12, 31)
    late_interest = None

    # Calculate interest for 30 days (Jan 1 to Jan 30)
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

    # Allow small rounding difference (< 0.01)
    diff = abs(interest - expected)
    passed = diff < Decimal("0.01")

    return {
        "passed": passed,
        "expected": str(expected),
        "actual": str(interest),
        "diff": str(diff),
        "message": f"30 days at 5%: expected {expected:.2f}, got {interest:.2f}"
    }


def test_calculate_accrued_interest_with_rate_change():
    """Test calculate_accrued_interest across rate change boundary."""
    face_value = Decimal("10000")
    schedule = [
        {"start_date": "2025-01-01", "end_date": "2025-06-30", "rate": "0.05"},
        {"start_date": "2025-07-01", "end_date": "2025-12-31", "rate": "0.06"}
    ]
    maturity = date(2025, 12, 31)
    late_interest = None

    # Calculate interest for full year (365 days)
    start = date(2025, 1, 1)
    end = date(2025, 12, 31)

    interest = calculate_accrued_interest(
        face_value=face_value,
        start_date=start,
        end_date=end,
        schedule=schedule,
        maturity_date=maturity,
        late_interest=late_interest
    )

    # Expected:
    # - 181 days at 5%: 10000 * 0.05 * (181/365) = 248.08
    # - 184 days at 6%: 10000 * 0.06 * (184/365) = 302.47
    # - Total: ~550.55
    expected_part1 = Decimal("10000") * Decimal("0.05") * Decimal("181") / Decimal("365")
    expected_part2 = Decimal("10000") * Decimal("0.06") * Decimal("184") / Decimal("365")
    expected = expected_part1 + expected_part2

    # Allow small rounding difference (< 1.00)
    diff = abs(interest - expected)
    passed = diff < Decimal("1.00")

    return {
        "passed": passed,
        "expected": str(expected),
        "actual": str(interest),
        "diff": str(diff),
        "message": f"Full year with rate change: expected {expected:.2f}, got {interest:.2f}"
    }


async def test_calculate_synthetic_value():
    """Test calculate_synthetic_value for SCHEDULED_YIELD asset."""
    async for session in get_test_session():
        # Create test asset
        asset = await create_test_asset(session)

        try:
            # Calculate value after 30 days (Jan 30, 2025)
            target_date = date(2025, 1, 30)

            result = await calculate_synthetic_value(asset, target_date, session)

            # Expected: face_value + accrued_interest
            # accrued_interest = 10000 * 0.05 * (30/365) ≈ 41.10
            # Note: calculation starts from asset.created_at.date()

            close_value = result["close"]
            face_value = asset.face_value

            # Value should be greater than face_value (interest accrued)
            passed = close_value > face_value

            return {
                "passed": passed,
                "face_value": str(face_value),
                "calculated_value": str(close_value),
                "accrued_interest": str(close_value - face_value),
                "message": f"Value after 30 days: {close_value:.2f} (face: {face_value:.2f})"
            }

        finally:
            # Cleanup
            await session.delete(asset)
            await session.commit()

    return {"passed": False, "message": "Session error"}


async def test_get_prices_synthetic_yield_integration():
    """Test get_prices() automatically uses synthetic calculation for SCHEDULED_YIELD."""
    async for session in get_test_session():
        # Create test asset
        asset = await create_test_asset(session)

        try:
            # Query prices for 7 days
            start = date(2025, 1, 1)
            end = date(2025, 1, 7)

            prices = await AssetSourceManager.get_prices(
                asset_id=asset.id,
                start_date=start,
                end_date=end,
                session=session
            )

            # Should return 7 prices (one per day)
            passed = len(prices) == 7

            # All prices should have backward_fill_info = None (exact calculation)
            all_exact = all(p.get("backward_fill_info") is None for p in prices)
            passed = passed and all_exact

            # Values should increase daily (interest accrues)
            values = [p["close"] for p in prices]
            increasing = all(values[i] < values[i+1] for i in range(len(values)-1))
            passed = passed and increasing

            return {
                "passed": passed,
                "count": len(prices),
                "first_value": str(values[0]) if values else "N/A",
                "last_value": str(values[-1]) if values else "N/A",
                "all_exact": all_exact,
                "increasing": increasing,
                "message": f"Generated {len(prices)} prices, values increasing: {increasing}"
            }

        finally:
            # Cleanup
            await session.delete(asset)
            await session.commit()

    return {"passed": False, "message": "Session error"}


async def test_synthetic_value_not_written_to_db():
    """Test that synthetic values are NOT written to price_history table."""
    async for session in get_test_session():
        # Create test asset
        asset = await create_test_asset(session)

        try:
            # Query prices (triggers synthetic calculation)
            start = date(2025, 1, 1)
            end = date(2025, 1, 7)

            await AssetSourceManager.get_prices(
                asset_id=asset.id,
                start_date=start,
                end_date=end,
                session=session
            )

            # Check DB - should have NO price_history records for this asset
            from backend.app.db.models import PriceHistory
            stmt = select(PriceHistory).where(PriceHistory.asset_id == asset.id)
            result = await session.execute(stmt)
            db_prices = result.scalars().all()

            passed = len(db_prices) == 0

            return {
                "passed": passed,
                "db_count": len(db_prices),
                "message": f"DB has {len(db_prices)} prices (expected 0, calculated on-demand)"
            }

        finally:
            # Cleanup
            await session.delete(asset)
            await session.commit()

    return {"passed": False, "message": "Session error"}


# ============================================================================
# TEST RUNNER
# ============================================================================


def print_test_result(test_name: str, result: dict):
    """Print test result with colored output."""
    status = "✅ PASSED" if result["passed"] else "❌ FAILED"
    print(f"\n{status} - {test_name}")

    if "message" in result:
        print(f"  Message: {result['message']}")

    if "details" in result:
        for detail in result["details"]:
            status_icon = "✓" if detail["passed"] else "✗"
            print(f"    {status_icon} {detail['test']}: expected={detail['expected']}, actual={detail['actual']}")

    if not result["passed"] and "expected" in result and "actual" in result:
        print(f"  Expected: {result['expected']}")
        print(f"  Actual: {result['actual']}")


async def run_all_tests():
    """Run all synthetic yield tests."""
    print("=" * 80)
    print("SYNTHETIC YIELD TEST SUITE")
    print("=" * 80)

    tests = {
        "Test 1: find_active_rate - Simple Schedule": test_find_active_rate_simple_schedule,
        "Test 2: find_active_rate - No Late Interest": test_find_active_rate_no_late_interest,
        "Test 3: calculate_accrued_interest - Single Rate": test_calculate_accrued_interest_single_rate,
        "Test 4: calculate_accrued_interest - Rate Change": test_calculate_accrued_interest_with_rate_change,
        "Test 5: calculate_synthetic_value - Full Calculation": test_calculate_synthetic_value,
        "Test 6: get_prices - Synthetic Yield Integration": test_get_prices_synthetic_yield_integration,
        "Test 7: Synthetic Values Not Written to DB": test_synthetic_value_not_written_to_db,
    }

    results = {}

    for test_name, test_func in tests.items():
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            results[test_name] = result
            print_test_result(test_name, result)

        except Exception as e:
            results[test_name] = {"passed": False, "message": f"Exception: {e}"}
            print_test_result(test_name, results[test_name])

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for r in results.values() if r["passed"])
    total = len(results)

    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
        for name, result in results.items():
            if not result["passed"]:
                print(f"  - {name}")

    return passed == total


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)

