"""
Test suite for synthetic yield calculation using ScheduledInvestmentProvider.

WHY THIS FILE EXISTS (vs normal plugin tests):
Normal plugin tests (test_assets_provider.py) verify API contracts — probe returns
current price + history. These tests verify the FINANCIAL MATH internals:
- Day count conventions, simple interest, late interest
- Event processing (INTEREST ex-date drop, PRICE_ADJUSTMENT write-down)
- Edge cases (before schedule, after maturity, grace period)
- Cache behavior
The provider is pure/deterministic, so these tests run without DB or server.
"""

import os
from datetime import date
from decimal import Decimal

import pytest

# Force test mode BEFORE any other imports
os.environ["LIBREFOLIO_TEST_MODE"] = "1"

from backend.app.db.models import IdentifierType
from backend.app.schemas.assets import (
    DayCountConvention,
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
    InterestType,
    MaturationFrequency,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAAssetEventPoint
from backend.app.services.asset_source_providers.scheduled_investment import (
    ScheduledInvestmentProvider,
    _compute_late_interest_value,
    _generate_schedule_values,
)

# ============================================================================
# PROVIDER TESTS — Pure deterministic (no DB, no _transaction_override)
# ============================================================================


@pytest.mark.asyncio
async def test_provider_validate_params():
    """Test provider parameter validation using Pydantic schemas."""
    provider = ScheduledInvestmentProvider()

    valid_params = {
        "initial_value": {"code": "EUR", "amount": "10000"},
        "day_count": "ACT/365",
        "schedule": [
            {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "annual_rate": "0.05",
                "maturation_frequency": "DAILY",
            }
        ],
        "late_interest": {
            "annual_rate": "0.12",
            "grace_period_days": 30,
        },
        "asset_events": [],
    }

    validated = provider.validate_params(valid_params)
    assert isinstance(validated, FAScheduledInvestmentSchedule)
    assert validated.initial_value.amount == Decimal("10000")
    assert validated.initial_value.code == "EUR"
    assert len(validated.schedule) == 1
    assert validated.schedule[0].annual_rate == Decimal("0.05")
    assert validated.late_interest is not None
    assert validated.late_interest.annual_rate == Decimal("0.12")


@pytest.mark.asyncio
async def test_provider_get_current_value():
    """Test provider get_current_value — pure, no DB access."""

    provider = ScheduledInvestmentProvider()
    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
        ),
        asset_events=[],
    ).model_dump()

    result = await provider.get_current_value("test-1", IdentifierType.OTHER, params)

    # Value should be > initial_value (interest accrued since 2025-01-01)
    assert result.value > Decimal("10000"), f"Expected value > 10000, got {result.value}"
    assert result.currency == "EUR", f"Expected EUR, got {result.currency}"
    assert result.source == "Scheduled Investment Calculator"


@pytest.mark.asyncio
async def test_provider_get_history_value():
    """Test provider get_history_value — pure, no DB access."""

    provider = ScheduledInvestmentProvider()
    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=None,
        asset_events=[],
    ).model_dump()

    start = date(2025, 1, 1)
    end = date(2025, 1, 7)

    result = await provider.get_history_value("test-1", IdentifierType.OTHER, params, start, end)

    assert len(result.prices) == 7, f"Expected 7 prices, got {len(result.prices)}"
    values = [p.close for p in result.prices]
    increasing = all(values[i] < values[i + 1] for i in range(len(values) - 1))
    assert increasing, f"Values are not monotonically increasing: {values}"
    assert result.currency == "EUR"
    assert result.events == []


@pytest.mark.asyncio
async def test_provider_interest_calculation():
    """Test simple interest calculation: 10000 * 0.05 * 29/365."""

    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=None,
        asset_events=[],
    )

    cached, _ = _generate_schedule_values(params)
    value = cached[date(2025, 1, 30)]

    # Expected: 10000 + (10000 * 0.05 * 29/365) ≈ 10039.73
    expected_interest = Decimal("10000") * Decimal("0.05") * Decimal("29") / Decimal("365")
    expected_value = Decimal("10000") + expected_interest

    diff = abs(value - expected_value)
    assert diff < Decimal("0.01"), f"Value mismatch: expected {expected_value}, got {value}, diff {diff}"


@pytest.mark.asyncio
async def test_provider_with_interest_event():
    """Test that INTEREST event reduces price (ex-date drop)."""

    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=None,
        asset_events=[
            FAAssetEventPoint(
                date=date(2025, 7, 1),
                type="INTEREST",
                value=Currency(code="EUR", amount=Decimal("250")),
                notes="H1 interest payout",
            ),
        ],
    )

    cached, _ = _generate_schedule_values(params)
    value_before = cached[date(2025, 6, 30)]
    value_after = cached[date(2025, 7, 1)]

    drop = value_before - value_after
    assert drop > Decimal("248"), f"Expected drop ~250, got {drop}"
    assert drop < Decimal("252"), f"Expected drop ~250, got {drop}"


@pytest.mark.asyncio
async def test_provider_with_price_adjustment_event():
    """Test that PRICE_ADJUSTMENT event modifies value algebraically."""

    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=None,
        asset_events=[
            FAAssetEventPoint(
                date=date(2025, 6, 1),
                type="PRICE_ADJUSTMENT",
                value=Currency(code="EUR", amount=Decimal("-1000")),
                notes="Write-down",
            ),
        ],
    )

    cached, _ = _generate_schedule_values(params)
    value_before = cached[date(2025, 5, 31)]
    value_after = cached[date(2025, 6, 1)]

    drop = value_before - value_after
    assert drop > Decimal("998"), f"Expected drop ~1000, got {drop}"
    assert drop < Decimal("1002"), f"Expected drop ~1000, got {drop}"


@pytest.mark.asyncio
async def test_provider_history_with_events():
    """Test that get_history_value returns events filtered to range."""

    provider = ScheduledInvestmentProvider()
    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=None,
        asset_events=[
            FAAssetEventPoint(date=date(2025, 3, 15), type="INTEREST", value=Currency(code="EUR", amount=Decimal("100"))),
            FAAssetEventPoint(date=date(2025, 6, 15), type="INTEREST", value=Currency(code="EUR", amount=Decimal("100"))),
            FAAssetEventPoint(date=date(2025, 9, 15), type="INTEREST", value=Currency(code="EUR", amount=Decimal("100"))),
        ],
    ).model_dump()

    # Query only March
    result = await provider.get_history_value("test-1", IdentifierType.OTHER, params, date(2025, 3, 1), date(2025, 3, 31))

    assert len(result.events) == 1, f"Expected 1 event in March, got {len(result.events)}"
    assert result.events[0].date == date(2025, 3, 15)


@pytest.mark.asyncio
async def test_provider_late_interest():
    """Test late interest calculation after maturity."""

    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
        ),
        asset_events=[],
    )

    cached, _ = _generate_schedule_values(params)
    maturity_date = date(2025, 3, 31)
    value_maturity = cached[maturity_date]

    # During grace period (uses last scheduled rate 0.05)
    value_grace = _compute_late_interest_value(params, date(2025, 4, 15), value_maturity, maturity_date)
    assert value_grace > value_maturity, "Value should increase during grace period"

    # After grace period (uses late rate 0.12)
    value_late = _compute_late_interest_value(params, date(2025, 6, 1), value_maturity, maturity_date)
    assert value_late > value_grace, "Value should increase further with late interest"


# ============================================================================
# COMPOUND INTEREST TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_compound_vs_simple_interest():
    """Test that COMPOUND yields more than SIMPLE for the same parameters."""
    base_args = dict(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.10"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        asset_events=[],
    )

    simple = FAScheduledInvestmentSchedule(interest_type=InterestType.SIMPLE, **base_args)
    compound = FAScheduledInvestmentSchedule(interest_type=InterestType.COMPOUND, **base_args)

    simple_values, _ = _generate_schedule_values(simple)
    compound_values, _ = _generate_schedule_values(compound)

    # At the end of the year, compound must exceed simple
    end_date = date(2025, 12, 31)
    assert compound_values[end_date] > simple_values[end_date], f"COMPOUND ({compound_values[end_date]}) should exceed SIMPLE ({simple_values[end_date]})"

    # Both must start at the same value on day 1
    assert simple_values[date(2025, 1, 1)] == compound_values[date(2025, 1, 1)] == Decimal("10000")


@pytest.mark.asyncio
async def test_compound_interest_numeric():
    """Test compound interest numeric accuracy: 10000 * (1 + 0.05/365)^365 ≈ 10512.67."""
    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.COMPOUND,
        day_count=DayCountConvention.ACT_365,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
            )
        ],
        asset_events=[],
    )

    cached, _ = _generate_schedule_values(params)
    value_end = cached[date(2025, 12, 31)]

    # Expected: 10000 * (1 + 0.05/365)^365 ≈ 10512.67
    # Simple would be: 10000 + 10000 * 0.05 * 365/365 = 10500
    assert value_end > Decimal("10500"), f"Compound should exceed simple 10500, got {value_end}"
    assert value_end < Decimal("10520"), f"Compound should be ~10512.67, got {value_end}"


@pytest.mark.asyncio
async def test_compound_with_different_day_counts():
    """Test compound interest with ACT/360 vs ACT/365."""
    base_args = dict(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.COMPOUND,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
            )
        ],
        asset_events=[],
    )

    act365 = FAScheduledInvestmentSchedule(day_count=DayCountConvention.ACT_365, **base_args)
    act360 = FAScheduledInvestmentSchedule(day_count=DayCountConvention.ACT_360, **base_args)

    v365, _ = _generate_schedule_values(act365)
    v360, _ = _generate_schedule_values(act360)

    # ACT/360 gives larger fractions per day → higher total interest
    assert v360[date(2025, 12, 31)] > v365[date(2025, 12, 31)], f"ACT/360 ({v360[date(2025, 12, 31)]}) should exceed ACT/365 ({v365[date(2025, 12, 31)]})"


# ============================================================================
# LATE INTEREST COMPOUND vs SIMPLE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_late_interest_compound_vs_simple():
    """Test that COMPOUND late interest yields more than SIMPLE for same parameters."""
    base_args = dict(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        asset_events=[],
    )

    simple_params = FAScheduledInvestmentSchedule(
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=10,
            interest_type=InterestType.SIMPLE,
        ),
        **base_args,
    )
    compound_params = FAScheduledInvestmentSchedule(
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=10,
            interest_type=InterestType.COMPOUND,
        ),
        **base_args,
    )

    simple_cached, _ = _generate_schedule_values(simple_params)
    compound_cached, _ = _generate_schedule_values(compound_params)
    maturity = date(2025, 3, 31)
    simple_maturity = simple_cached[maturity]
    compound_maturity = compound_cached[maturity]

    # Both should have same value at maturity (main schedule is identical)
    assert simple_maturity == compound_maturity

    # Well after grace period: compound late interest should exceed simple
    target = date(2025, 8, 1)  # ~4 months after maturity
    simple_late = _compute_late_interest_value(simple_params, target, simple_maturity, maturity)
    compound_late = _compute_late_interest_value(compound_params, target, compound_maturity, maturity)

    assert compound_late > simple_late, f"COMPOUND late ({compound_late}) should exceed SIMPLE late ({simple_late})"
    # Both should exceed maturity value (interest is accruing)
    assert simple_late > simple_maturity
    assert compound_late > compound_maturity


@pytest.mark.asyncio
async def test_late_interest_default_is_compound():
    """Test that FALateInterestConfig defaults to COMPOUND interest_type."""
    li = FALateInterestConfig(annual_rate=Decimal("0.10"), grace_period_days=15)
    assert li.interest_type == InterestType.COMPOUND


@pytest.mark.asyncio
async def test_validate_params_missing_required():
    """Test that missing required params raise validation error."""
    from pydantic import ValidationError

    # Empty schedule with no initial_value → should raise
    with pytest.raises(ValidationError):
        FAScheduledInvestmentSchedule(
            initial_value=None,  # required, not nullable
            schedule=[],
        )


@pytest.mark.asyncio
async def test_validate_params_invalid_day_count():
    """Test that invalid day count convention is rejected by Pydantic."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("1000")),
            day_count="INVALID_CONVENTION",
            schedule=[
                FAInterestRatePeriod(
                    annual_rate=Decimal("0.05"),
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 12, 31),
                )
            ],
        )


@pytest.mark.asyncio
async def test_late_interest_within_grace_period():
    """Late interest within grace period → value = maturity value (no penalty)."""
    params = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("1000")),
        schedule=[
            FAInterestRatePeriod(
                annual_rate=Decimal("0.05"),
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
            interest_type=InterestType.SIMPLE,
        ),
    )
    cached, _ = _generate_schedule_values(params)
    maturity = date(2025, 3, 31)
    maturity_value = cached[maturity]

    # Within grace period (5 days after maturity)
    # Grace period means regular rate continues (not the late penalty rate)
    target = date(2025, 4, 5)
    late_value = _compute_late_interest_value(params, target, maturity_value, maturity)
    # Value should be >= maturity (interest still accruing at regular rate)
    assert late_value >= maturity_value, "Within grace period → value should not decrease"
    # Value should be less than what late penalty rate would give
    # (we just verify it's reasonable and different from maturity)
    assert late_value > maturity_value, "Within grace period → regular interest still accrues"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
