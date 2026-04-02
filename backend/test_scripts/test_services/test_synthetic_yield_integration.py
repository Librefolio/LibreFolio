"""
End-to-End integration tests for ScheduledInvestmentProvider synthetic yield valuation.

Scenarios covered:
1. P2P Loan with two periods + late interest (grace + penalty).
2. Single period with different maturation frequencies.
3. Multi-period scheduled rate changes.

All tests are pure — the provider is deterministic with initial_value, no DB needed.
Interest is always simple (on initial_value.amount).
"""

import os
from datetime import date
from decimal import Decimal

import pytest

# Force test mode BEFORE any other imports
os.environ["LIBREFOLIO_TEST_MODE"] = "1"

from backend.app.schemas.assets import (
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
    DayCountConvention,
    MaturationFrequency,
    InterestType,
    )
from backend.app.schemas.common import Currency
from backend.app.db.models import IdentifierType
from backend.app.services.asset_source_providers.scheduled_investment import (
    ScheduledInvestmentProvider,
    )


async def _history_values(params: dict, start: date, end: date):
    provider = ScheduledInvestmentProvider()
    result = await provider.get_history_value("1", IdentifierType.OTHER, params, start, end)
    return [p.close for p in result.prices]


# Scenario 1: P2P Loan - Two periods + late interest
@pytest.mark.asyncio
async def test_e2e_p2p_loan_two_periods_late_interest():
    schedule_model = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1), end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.05"), maturation_frequency=MaturationFrequency.DAILY,
                ),
            FAInterestRatePeriod(
                start_date=date(2025, 7, 1), end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.06"), maturation_frequency=MaturationFrequency.DAILY,
                ),
            ],
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"), grace_period_days=30,
            ),
        asset_events=[],
        )
    params = schedule_model.model_dump()

    async def value_on(d: date) -> Decimal:
        return (await _history_values(params, d, d))[0]

    mid_first = await value_on(date(2025, 3, 15))
    assert mid_first > Decimal("10000")

    maturity = await value_on(date(2025, 12, 31))
    assert maturity > mid_first

    grace = await value_on(date(2026, 1, 15))
    assert grace > maturity

    late = await value_on(date(2026, 2, 5))
    assert late > grace, f"Late interest not applied: late={late} grace={grace}"


# Scenario 2: Different maturation frequencies (result is same for simple interest)
@pytest.mark.asyncio
async def test_e2e_maturation_frequencies():
    base = dict(
        start_date=date(2025, 1, 1), end_date=date(2025, 12, 31),
        annual_rate=Decimal("0.04"),
        )

    for freq in [MaturationFrequency.DAILY, MaturationFrequency.MONTHLY, MaturationFrequency.ANNUAL]:
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("20000")),
            schedule=[FAInterestRatePeriod(**base, maturation_frequency=freq)],
            asset_events=[],
            )
        params = schedule.model_dump()
        hist = await _history_values(params, date(2025, 1, 1), date(2025, 3, 31))
        assert hist[0] == Decimal("20000")
        assert hist[-1] > hist[0]


# Scenario 3: Multi-period rate changes
@pytest.mark.asyncio
async def test_e2e_multi_period_rate_changes():
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("5000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1), end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.03"), maturation_frequency=MaturationFrequency.DAILY,
                ),
            FAInterestRatePeriod(
                start_date=date(2025, 4, 1), end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.035"), maturation_frequency=MaturationFrequency.MONTHLY,
                ),
            FAInterestRatePeriod(
                start_date=date(2025, 7, 1), end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.04"), maturation_frequency=MaturationFrequency.DAILY,
                ),
            ],
        asset_events=[],
        )
    params = schedule.model_dump()

    q1 = (await _history_values(params, date(2025, 3, 31), date(2025, 3, 31)))[0]
    q2 = (await _history_values(params, date(2025, 6, 30), date(2025, 6, 30)))[0]
    q3 = (await _history_values(params, date(2025, 9, 30), date(2025, 9, 30)))[0]
    q4 = (await _history_values(params, date(2025, 12, 31), date(2025, 12, 31)))[0]

    assert q1 > Decimal("5000")
    assert q2 > q1
    assert q3 > q2
    assert q4 > q3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
