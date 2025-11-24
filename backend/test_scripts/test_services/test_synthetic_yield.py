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
import os
from datetime import date
from decimal import Decimal

import pytest

# Force test mode BEFORE any other imports
os.environ["LIBREFOLIO_TEST_MODE"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///backend/data/sqlite/test_app.db"

from backend.app.services.asset_source_providers.scheduled_investment import ScheduledInvestmentProvider

from backend.app.schemas.assets import FAScheduledInvestmentSchedule


# ============================================================================
# PROVIDER TESTS
# ============================================================================


@pytest.mark.asyncio
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

    validated = provider.validate_params(valid_params)
    assert isinstance(validated, FAScheduledInvestmentSchedule), f"Expected FAScheduledInvestmentSchedule, got {type(validated)}"
    assert len(validated.schedule) == 1, f"Expected 1 period in schedule, got {len(validated.schedule)}"
    assert validated.schedule[0].annual_rate == Decimal("0.05"), f"Expected rate 0.05, got {validated.schedule[0].annual_rate}"
    assert validated.late_interest is not None, "Late interest should be present"
    assert validated.late_interest.annual_rate == Decimal("0.12"), f"Expected late rate 0.12, got {validated.late_interest.annual_rate}"


@pytest.mark.asyncio
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

    # Use identifier "1" for test mode with _transaction_override
    result = await provider.get_current_value("1", params)

    # Value should be > face_value (interest accrued since 2025-01-01)
    assert result.value > Decimal("10000"), f"Expected value > 10000, got {result.value}"
    assert result.currency == "EUR", f"Expected EUR, got {result.currency}"
    assert result.source == "Scheduled Investment Calculator", f"Unexpected source: {result.source}"


@pytest.mark.asyncio
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

    result = await provider.get_history_value("1", params, start, end)

    # Should have 7 prices
    assert len(result.prices) == 7, f"Expected 7 prices, got {len(result.prices)}"

    # Values should increase daily
    values = [p.close for p in result.prices]
    increasing = all(values[i] < values[i + 1] for i in range(len(values) - 1))
    assert increasing, f"Values are not monotonically increasing: {values}"

    # Currency should match
    assert result.currency == "EUR", f"Expected EUR, got {result.currency}"


@pytest.mark.asyncio
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
    params = FAScheduledInvestmentSchedule(**params_dict)

    # Calculate value for Jan 30, 2025 (29 days from Jan 1)
    face_value = Decimal("10000")
    value = provider._calculate_value_for_date(params, face_value, date(2025, 1, 30))

    # Expected: 10000 + (10000 * 0.05 * 29/365) ≈ 10039.73
    expected_interest = Decimal("10000") * Decimal("0.05") * Decimal("29") / Decimal("365")
    expected_value = Decimal("10000") + expected_interest

    diff = abs(value - expected_value)
    assert diff < Decimal("0.01"), f"Value calculation mismatch: expected {expected_value}, got {value}, diff {diff}"


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


# ============================================================================
# TEST ORCHESTRATION (LEGACY)
# ============================================================================
# NOTE: This run_all_tests() function is LEGACY code from before pytest migration.
# This function is kept for backward compatibility with manual execution
# (e.g., `python -m backend.test_scripts.test_services.test_synthetic_yield`),
# but the recommended way is: pytest backend/test_scripts/test_services/test_synthetic_yield.py
# TODO: rimuovere test orchestration legacy una volta che tutti i test sono migrati a pytest.
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
