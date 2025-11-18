"""
Test suite for synthetic yield calculation using ScheduledInvestmentProvider.

Tests cover:
- Provider validation (Pydantic schemas)
- Provider calculation methods (get_current_value, get_history_value)
- Private calculation method (_calculate_value_for_date)
- Integration with get_prices() - automatic provider delegation
- Utility functions (find_active_period)
"""
import asyncio
import json
import os
import sys
from datetime import date
from decimal import Decimal

# Force test mode BEFORE any other imports
os.environ["LIBREFOLIO_TEST_MODE"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///backend/data/sqlite/test_app.db"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from backend.app.db.models import (
    Asset, ValuationModel, AssetType, PriceHistory,
    Transaction, AssetProviderAssignment, CashMovement, CashAccount, Broker,
    TransactionType, CashMovementType
)
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.asset_source_providers.scheduled_investment import ScheduledInvestmentProvider
from backend.app.utils.financial_math import find_active_period

from backend.app.schemas.assets import (
    InterestRatePeriod,
    LateInterestConfig,
    ScheduledInvestmentSchedule,
    CompoundingType,
    DayCountConvention,
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
        {"start_date": "2025-01-01", "end_date": "2025-12-31", "annual_rate": "0.05", "compounding": "SIMPLE", "day_count": "ACT/365"},
        {"start_date": "2026-01-01", "end_date": "2026-12-31", "annual_rate": "0.06", "compounding": "SIMPLE", "day_count": "ACT/365"}
        ]

    late_interest = {"annual_rate": "0.12", "grace_period_days": 30, "compounding": "SIMPLE", "day_count": "ACT/365"}

    # Create full schedule structure
    full_schedule = {
        "schedule": interest_schedule,
        "late_interest": late_interest
    }

    # Create broker for transactions (or reuse existing)
    # Try to find existing broker first
    result = await session.execute(select(Broker).where(Broker.name == "Test Broker"))
    broker = result.scalar_one_or_none()

    if not broker:
        broker = Broker(name="Test Broker", description="For scheduled yield tests")
        session.add(broker)
        await session.flush()

    asset = Asset(
        display_name="Test Recrowd Loan",
        identifier="RECROWD-TEST-001",
        currency="EUR",
        asset_type=AssetType.CROWDFUND_LOAN,
        valuation_model=ValuationModel.SCHEDULED_YIELD,
        interest_schedule=json.dumps(full_schedule),
        )

    session.add(asset)
    await session.flush()

    # Create cash account (or reuse existing)
    result = await session.execute(
        select(CashAccount).where(
            CashAccount.broker_id == broker.id,
            CashAccount.currency == "EUR"
        )
    )
    cash_account = result.scalar_one_or_none()

    if not cash_account:
        cash_account = CashAccount(broker_id=broker.id, currency="EUR", display_name="Test Cash EUR")
        session.add(cash_account)
        await session.flush()

    # Create cash movement for BUY
    cash_mov = CashMovement(
        cash_account_id=cash_account.id,
        type=CashMovementType.BUY_SPEND,
        amount=Decimal("-10000"),
        trade_date=date(2025, 1, 1),
        currency="EUR"
    )
    session.add(cash_mov)
    await session.flush()

    # Create BUY transaction to establish face_value
    txn = Transaction(
        asset_id=asset.id,
        broker_id=broker.id,
        type=TransactionType.BUY,
        quantity=Decimal("1"),
        price=Decimal("10000"),
        currency="EUR",
        cash_movement_id=cash_mov.id,
        trade_date=date(2025, 1, 1)
    )
    session.add(txn)
    await session.commit()
    await session.refresh(asset)

    return asset


# ============================================================================
# PROVIDER TESTS
# ============================================================================


async def test_provider_validate_params():
    """Test provider parameter validation using Pydantic schemas."""
    provider = ScheduledInvestmentProvider()

    # Test 1: Valid params (only schedule structure)
    valid_params = {
        "schedule": [
            {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "annual_rate": "0.05",
                "compounding": "SIMPLE",
                "day_count": "ACT/365"
            }
        ],
        "late_interest": {
            "annual_rate": "0.12",
            "grace_period_days": 30,
            "compounding": "SIMPLE",
            "day_count": "ACT/365"
        }
    }

    try:
        validated = provider.validate_params(valid_params)
        passed = isinstance(validated, ScheduledInvestmentSchedule)
        passed = passed and len(validated.schedule) == 1
        passed = passed and validated.schedule[0].annual_rate == Decimal("0.05")
        passed = passed and validated.late_interest is not None
        passed = passed and validated.late_interest.annual_rate == Decimal("0.12")

        return {
            "passed": passed,
            "message": f"Validation successful, validated type: {type(validated).__name__}"
            }
    except Exception as e:
        return {"passed": False, "message": f"Validation failed: {e}"}


async def test_provider_get_current_value():
    """Test provider get_current_value method."""
    provider = ScheduledInvestmentProvider()

    params = {
        "schedule": [
            {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "annual_rate": "0.05",
                "compounding": "SIMPLE",
                "day_count": "ACT/365"
            }
        ],
        "late_interest": {
            "annual_rate": "0.12",
            "grace_period_days": 30,
            "compounding": "SIMPLE",
            "day_count": "ACT/365"
        },
        "_transaction_override": [
            {"type": "BUY", "quantity": 1, "price": "10000", "trade_date": "2025-01-01"}
        ]
    }

    try:
        # Use identifier "1" for test mode with _transaction_override
        result = await provider.get_current_value("1", params)

        # Value should be > face_value (interest accrued since 2025-01-01)
        passed = result.value > Decimal("10000")
        passed = passed and result.currency == "EUR"
        passed = passed and result.source == "Scheduled Investment Calculator"

        return {
            "passed": passed,
            "value": str(result.value),
            "currency": result.currency,
            "message": f"Current value: {result.value} {result.currency}"
            }
    except Exception as e:
        return {"passed": False, "message": f"Exception: {e}"}


async def test_provider_get_history_value():
    """Test provider get_history_value method."""
    provider = ScheduledInvestmentProvider()

    params = {
        "schedule": [
            {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "annual_rate": "0.05",
                "compounding": "SIMPLE",
                "day_count": "ACT/365"
            }
        ],
        "late_interest": {
            "annual_rate": "0.12",
            "grace_period_days": 30,
            "compounding": "SIMPLE",
            "day_count": "ACT/365"
        },
        "_transaction_override": [
            {"type": "BUY", "quantity": 1, "price": "10000", "trade_date": "2025-01-01"}
        ]
    }

    start = date(2025, 1, 1)
    end = date(2025, 1, 7)

    try:
        result = await provider.get_history_value("1", params, start, end)

        # Should have 7 prices
        passed = len(result.prices) == 7

        # Values should increase daily
        values = [p.close for p in result.prices]
        increasing = all(values[i] < values[i + 1] for i in range(len(values) - 1))
        passed = passed and increasing

        # Currency should match
        passed = passed and result.currency == "EUR"

        return {
            "passed": passed,
            "count": len(result.prices),
            "first": str(values[0]) if values else "N/A",
            "last": str(values[-1]) if values else "N/A",
            "increasing": increasing,
            "message": f"Generated {len(result.prices)} prices, increasing: {increasing}"
            }
    except Exception as e:
        return {"passed": False, "message": f"Exception: {e}"}


async def test_provider_private_calculate_value():
    """Test provider private _calculate_value_for_date method."""

    provider = ScheduledInvestmentProvider()

    # Create validated params using Pydantic model (no face_value, currency, maturity_date)
    params_dict = {
        "schedule": [
            {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "annual_rate": "0.05",
                "compounding": "SIMPLE",
                "day_count": "ACT/365"
            }
        ],
        "late_interest": {
            "annual_rate": "0.12",
            "grace_period_days": 30,
            "compounding": "SIMPLE",
            "day_count": "ACT/365"
        }
    }
    params = ScheduledInvestmentSchedule(**params_dict)

    try:
        # Calculate value for Jan 30, 2025 (29 days from Jan 1 - timedelta does not include end date)
        # Now _calculate_value_for_date requires face_value as parameter
        face_value = Decimal("10000")
        value = provider._calculate_value_for_date(params, face_value, date(2025, 1, 30))

        # Expected: 10000 + (10000 * 0.05 * 29/365) ≈ 10039.73
        expected_interest = Decimal("10000") * Decimal("0.05") * Decimal("29") / Decimal("365")
        expected_value = Decimal("10000") + expected_interest

        diff = abs(value - expected_value)
        passed = diff < Decimal("0.01")

        return {
            "passed": passed,
            "value": str(value),
            "expected": str(expected_value),
            "diff": str(diff),
            "message": f"Calculated: {value:.2f}, Expected: {expected_value:.2f}"
            }
    except Exception as e:
        return {"passed": False, "message": f"Exception: {e}"}


# ============================================================================
# UTILITY FUNCTION TESTS
# ============================================================================


def test_find_active_period_with_pydantic():
    """Test find_active_period utility with Pydantic models (only format accepted)."""

    # Use Pydantic models (only way to call the function)
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        ),
        InterestRatePeriod(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 12, 31),
            annual_rate=Decimal("0.06"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        )
        ]
    late_interest = LateInterestConfig(
        annual_rate=Decimal("0.12"),
        grace_period_days=30,
        compounding=CompoundingType.SIMPLE,
        day_count=DayCountConvention.ACT_365
    )
    maturity = date(2026, 12, 31)

    test_cases = [
        (date(2025, 6, 15), Decimal("0.05"), "Mid-2025 (first period)"),
        (date(2026, 6, 15), Decimal("0.06"), "Mid-2026 (second period)"),
        (date(2027, 1, 15), Decimal("0.06"), "15 days after maturity (grace)"),
        (date(2027, 2, 15), Decimal("0.12"), "45 days after maturity (late)"),
        ]

    results = []
    for target, expected, desc in test_cases:
        period = find_active_period(schedule, target, maturity, late_interest)
        if period is None:
            actual = Decimal("0")  # No period found
        else:
            actual = period.annual_rate
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

# NOTE: test_calculate_accrued_conversion removed - function deprecated
# The calculate_accrued_interest() function was obsolete (day-by-day, SIMPLE only)
# Use period-based calculation in ScheduledInvestmentProvider instead


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


async def test_get_prices_integration():
    """Test get_prices() integration with scheduled_investment provider."""
    async for session in get_test_session():
        asset = await create_test_asset(session)

        try:
            # Assign provider - interest_schedule now contains full ScheduledInvestmentSchedule structure
            schedule_data = json.loads(asset.interest_schedule)
            provider_params = schedule_data  # Already has {schedule: [...], late_interest: {...}}

            await AssetSourceManager.assign_provider(
                asset_id=asset.id,
                provider_code="scheduled_investment",
                provider_params=json.dumps(provider_params),
                session=session
                )

            # Get prices
            prices = await AssetSourceManager.get_prices(
                asset_id=asset.id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 7),
                session=session
                )

            # Validate
            passed = len(prices) == 7
            all_exact = all(p.backward_fill_info is None for p in prices)
            values = [p.close for p in prices]
            increasing = all(values[i] < values[i + 1] for i in range(len(values) - 1))

            passed = passed and all_exact and increasing

            return {
                "passed": passed,
                "count": len(prices),
                "increasing": increasing,
                "message": f"get_prices() returned {len(prices)} calculated values"
                }
        finally:
            # Clean up: delete ALL related records first due to FK constraints
            # Delete in reverse dependency order with flush() between groups
            from sqlmodel import delete as sqlmodel_delete

            # 1. Delete provider assignment first
            await session.execute(
                sqlmodel_delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset.id)
            )
            await session.flush()

            # 2. Delete price history
            await session.execute(
                sqlmodel_delete(PriceHistory).where(PriceHistory.asset_id == asset.id)
            )
            await session.flush()

            # 3. Get cash movement IDs before deleting transactions
            stmt_txn = select(Transaction.cash_movement_id).where(Transaction.asset_id == asset.id)
            result = await session.execute(stmt_txn)
            cash_movement_ids = [row[0] for row in result.all() if row[0]]

            # 4. Delete transactions
            await session.execute(
                sqlmodel_delete(Transaction).where(Transaction.asset_id == asset.id)
            )
            await session.flush()

            # 5. Delete cash movements
            if cash_movement_ids:
                await session.execute(
                    sqlmodel_delete(CashMovement).where(CashMovement.id.in_(cash_movement_ids))
                )
                await session.flush()

            # 6. Finally delete asset
            await session.execute(
                sqlmodel_delete(Asset).where(Asset.id == asset.id)
            )

            await session.commit()

    return {"passed": False, "message": "Session error"}


async def test_no_db_storage():
    """Test that synthetic values are NOT written to database."""
    async for session in get_test_session():
        asset = await create_test_asset(session)

        try:
            # Assign provider first
            schedule_data = json.loads(asset.interest_schedule)
            await AssetSourceManager.assign_provider(
                asset_id=asset.id,
                provider_code="scheduled_investment",
                provider_params=json.dumps(schedule_data),
                session=session
            )

            # Query prices (should calculate on-demand)
            await AssetSourceManager.get_prices(
                asset_id=asset.id,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 7),
                session=session
                )

            # Check DB - should have NO price_history records
            stmt = select(PriceHistory).where(PriceHistory.asset_id == asset.id)
            result = await session.execute(stmt)
            db_prices = result.scalars().all()

            passed = len(db_prices) == 0

            return {
                "passed": passed,
                "db_count": len(db_prices),
                "message": f"DB has {len(db_prices)} prices (expected 0)"
                }
        finally:
            # Clean up: delete ALL related records first due to FK constraints
            # Delete in reverse dependency order with flush() between groups
            from sqlmodel import delete as sqlmodel_delete

            # 1. Delete provider assignment first
            await session.execute(
                sqlmodel_delete(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset.id)
            )
            await session.flush()

            # 2. Delete price history
            await session.execute(
                sqlmodel_delete(PriceHistory).where(PriceHistory.asset_id == asset.id)
            )
            await session.flush()

            # 3. Get cash movement IDs before deleting transactions
            stmt_txn = select(Transaction.cash_movement_id).where(Transaction.asset_id == asset.id)
            result = await session.execute(stmt_txn)
            cash_movement_ids = [row[0] for row in result.all() if row[0]]

            # 4. Delete transactions
            await session.execute(
                sqlmodel_delete(Transaction).where(Transaction.asset_id == asset.id)
            )
            await session.flush()

            # 5. Delete cash movements
            if cash_movement_ids:
                await session.execute(
                    sqlmodel_delete(CashMovement).where(CashMovement.id.in_(cash_movement_ids))
                )
                await session.flush()

            # 6. Finally delete asset
            await session.execute(
                sqlmodel_delete(Asset).where(Asset.id == asset.id)
            )

            await session.commit()

    return {"passed": False, "message": "Session error"}


async def test_pydantic_schema_validation():
    """Test Pydantic schema validation with invalid data."""
    provider = ScheduledInvestmentProvider()

    # Test invalid dates (end_date before start_date - should be rejected by validation)
    invalid_params = {
        "schedule": [
            {
                "start_date": "2025-12-31",
                "end_date": "2025-01-01",  # Before start_date - invalid!
                "annual_rate": "0.05",
                "compounding": "SIMPLE",
                "day_count": "ACT/365"
            }
        ]
    }

    try:
        provider.validate_params(invalid_params)
        return {"passed": False, "message": "Should have raised validation error"}
    except Exception as e:
        # Should raise AssetSourceError with INVALID_PARAMS or validation error
        passed = "INVALID_PARAMS" in str(e) or "end_date" in str(e).lower() or "after" in str(e).lower()
        return {
            "passed": passed,
            "message": f"Correctly rejected invalid params: {e}"
            }


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
    print("SYNTHETIC YIELD TEST SUITE (Provider-Based)")
    print("=" * 80)

    tests = {
        # Provider tests
        "Test 1: Provider Param Validation (Pydantic)": test_provider_validate_params,
        "Test 2: Provider get_current_value()": test_provider_get_current_value,
        "Test 3: Provider get_history_value()": test_provider_get_history_value,
        "Test 4: Provider _calculate_value_for_date()": test_provider_private_calculate_value,

        # Utility tests (require Pydantic models)
        "Test 5: find_active_period() with Pydantic": test_find_active_period_with_pydantic,

        # Integration tests
        "Test 6: get_prices() Integration": test_get_prices_integration,
        "Test 7: No DB Storage (On-Demand)": test_no_db_storage,
        "Test 8: Pydantic Schema Validation Error": test_pydantic_schema_validation,
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
