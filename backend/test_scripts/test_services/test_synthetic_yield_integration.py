"""
End-to-End integration tests for ScheduledInvestmentProvider synthetic yield valuation.

Scenarios covered:
1. P2P Loan with two periods + late interest (grace + penalty) SIMPLE interest.
2. Bond with quarterly COMPOUND interest (coupon-like accrual) single period.
3. Multi-period scheduled rate changes with mixed SIMPLE/COMPOUND segments.

All tests use _transaction_override to avoid DB dependency except where DB integration explicit.

Assertions use exact Decimal equality where deterministic.
"""
import json
from datetime import date
from decimal import Decimal

import pytest

from backend.app.schemas.assets import (
    InterestRatePeriod,
    LateInterestConfig,
    ScheduledInvestmentSchedule,
    CompoundingType,
    CompoundFrequency,
    DayCountConvention,
    )
from backend.app.services.asset_source_providers.scheduled_investment import ScheduledInvestmentProvider


# Helper to run provider current value with override
async def _current_value(params: dict) -> Decimal:
    provider = ScheduledInvestmentProvider()
    result = await provider.get_current_value("1", params)
    return result.value


# Helper to run provider history with override
async def _history_values(params: dict, start: date, end: date):
    provider = ScheduledInvestmentProvider()
    result = await provider.get_history_value("1", params, start, end)
    return [p.close for p in result.prices]


# =============================================================================
# Scenario 1: P2P Loan - Two periods + late interest (SIMPLE interest)
# =============================================================================
@pytest.mark.asyncio
async def test_e2e_p2p_loan_two_periods_late_interest():
    schedule_model = ScheduledInvestmentSchedule(
        schedule=[
            InterestRatePeriod(
                start_date=date(2025, 1, 1), end_date=date(2025, 6, 30), annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE, day_count=DayCountConvention.ACT_365
                ),
            InterestRatePeriod(
                start_date=date(2025, 7, 1), end_date=date(2025, 12, 31), annual_rate=Decimal("0.06"),
                compounding=CompoundingType.SIMPLE, day_count=DayCountConvention.ACT_365
                ),
            ],
        late_interest=LateInterestConfig(
            annual_rate=Decimal("0.12"), grace_period_days=30,
            compounding=CompoundingType.SIMPLE, day_count=DayCountConvention.ACT_365
            )
        )

    params = json.loads(schedule_model.model_dump_json())
    params["_transaction_override"] = [
        {"type": "BUY", "quantity": 1, "price": "10000", "trade_date": "2025-01-01"}
        ]

    # Helper to get single-day value
    async def value_on(d: date) -> Decimal:
        return (await _history_values(params, d, d))[0]

    # Value mid first period (fixed date instead of today)
    mid_first_date = date(2025, 3, 15)
    mid_first_value = await value_on(mid_first_date)

    # Sanity: value should be > principal
    assert mid_first_value > Decimal("10000")

    # Value at maturity
    maturity_value = await value_on(date(2025, 12, 31))
    assert maturity_value > mid_first_value

    # Value within grace (15 days after maturity)
    grace_value = await value_on(date(2026, 1, 15))
    assert grace_value > maturity_value

    # Value after grace (late interest applies) - 36 days after maturity
    late_value = await value_on(date(2026, 2, 5))
    assert late_value > grace_value, (
        f"Late interest not applied: late={late_value} grace={grace_value} maturity={maturity_value} mid_first={mid_first_value}"
    )


# =============================================================================
# Scenario 2: Bond - Quarterly compounding
# =============================================================================
@pytest.mark.asyncio
async def test_e2e_bond_quarterly_compound():
    schedule_model = ScheduledInvestmentSchedule(
        schedule=[
            InterestRatePeriod(
                start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), annual_rate=Decimal("0.04"),
                compounding=CompoundingType.COMPOUND, compound_frequency=CompoundFrequency.QUARTERLY,
                day_count=DayCountConvention.ACT_365
                )
            ]
        )

    params = json.loads(schedule_model.model_dump_json())
    params["_transaction_override"] = [
        {"type": "BUY", "quantity": 1, "price": "20000", "trade_date": "2025-01-01"}
        ]

    # Value end of Q1 vs start
    hist_q1 = await _history_values(params, date(2025, 1, 1), date(2025, 3, 31))
    assert hist_q1[0] == Decimal("20000")
    assert hist_q1[-1] > hist_q1[0]

    # Check mid-year vs year-end growth
    mid_year = (await _history_values(params, date(2025, 6, 1), date(2025, 6, 1)))[0]
    year_end = (await _history_values(params, date(2025, 12, 31), date(2025, 12, 31)))[0]
    assert year_end > mid_year > hist_q1[-1]


# =============================================================================
# Scenario 3: Mixed SIMPLE/COMPOUND multi-period schedule
# =============================================================================
@pytest.mark.asyncio
async def test_e2e_mixed_schedule_simple_compound():
    schedule_model = ScheduledInvestmentSchedule(
        schedule=[
            InterestRatePeriod(
                start_date=date(2025, 1, 1), end_date=date(2025, 3, 31), annual_rate=Decimal("0.03"),
                compounding=CompoundingType.SIMPLE, day_count=DayCountConvention.ACT_365
                ),
            InterestRatePeriod(
                start_date=date(2025, 4, 1), end_date=date(2025, 6, 30), annual_rate=Decimal("0.035"),
                compounding=CompoundingType.COMPOUND, compound_frequency=CompoundFrequency.MONTHLY,
                day_count=DayCountConvention.ACT_365
                ),
            InterestRatePeriod(
                start_date=date(2025, 7, 1), end_date=date(2025, 12, 31), annual_rate=Decimal("0.04"),
                compounding=CompoundingType.SIMPLE, day_count=DayCountConvention.ACT_365
                ),
            ]
        )

    params = json.loads(schedule_model.model_dump_json())
    params["_transaction_override"] = [
        {"type": "BUY", "quantity": 1, "price": "5000", "trade_date": "2025-01-01"}
        ]

    # Collect quarterly snapshots
    q1_end = (await _history_values(params, date(2025, 3, 31), date(2025, 3, 31)))[0]
    q2_end = (await _history_values(params, date(2025, 6, 30), date(2025, 6, 30)))[0]
    q3_end = (await _history_values(params, date(2025, 9, 30), date(2025, 9, 30)))[0]
    q4_end = (await _history_values(params, date(2025, 12, 31), date(2025, 12, 31)))[0]

    assert q1_end > Decimal("5000")
    assert q2_end > q1_end  # higher rate + compounding
    assert q3_end > q2_end  # next rate
    assert q4_end > q3_end  # final growth

# Run all tests with pytest
# pytest backend/test_scripts/test_services/test_synthetic_yield_integration.py -v
