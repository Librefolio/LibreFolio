"""
Test suite for synthetic yield calculation using ScheduledInvestmentProvider.

Tests cover:
- Provider validation (Pydantic schemas with initial_value + currency)
- Provider calculation methods (get_current_value, get_history_value) — pure, no DB
- Private calculation method (_calculate_value_for_date)
- Asset events: INTEREST ex-date drop, PRICE_ADJUSTMENT
- Late interest (post-maturity)
- Compound interest
"""

import os
from datetime import date
from decimal import Decimal

import pytest

# Force test mode BEFORE any other imports
os.environ["LIBREFOLIO_TEST_MODE"] = "1"

from backend.app.services.asset_source_providers.scheduled_investment import (
    ScheduledInvestmentProvider,
    )

from backend.app.schemas.assets import (
    FAScheduledInvestmentSchedule,
    FAInterestRatePeriod,
    CompoundingType,
    DayCountConvention,
    FALateInterestConfig,
    )
from backend.app.schemas.prices import FAAssetEventPoint


# ============================================================================
# PROVIDER TESTS — Pure deterministic (no DB, no _transaction_override)
# ============================================================================


@pytest.mark.asyncio
async def test_provider_validate_params():
    """Test provider parameter validation using Pydantic schemas."""
    provider = ScheduledInvestmentProvider()

    valid_params = {
        "initial_value": "10000",
        "currency": "EUR",
        "schedule": [
            {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "annual_rate": "0.05",
                "compounding": "SIMPLE",
                "day_count": "ACT/365",
                }
            ],
        "late_interest": {
            "annual_rate": "0.12",
            "grace_period_days": 30,
            "compounding": "SIMPLE",
            "day_count": "ACT/365",
            },
        "asset_events": [],
        }

    validated = provider.validate_params(valid_params)
    assert isinstance(validated, FAScheduledInvestmentSchedule)
    assert validated.initial_value == Decimal("10000")
    assert validated.currency == "EUR"
    assert len(validated.schedule) == 1
    assert validated.schedule[0].annual_rate == Decimal("0.05")
    assert validated.late_interest is not None
    assert validated.late_interest.annual_rate == Decimal("0.12")


@pytest.mark.asyncio
async def test_provider_get_current_value():
    """Test provider get_current_value — pure, no DB access."""
    from backend.app.db.models import IdentifierType

    provider = ScheduledInvestmentProvider()
    params = FAScheduledInvestmentSchedule(
        initial_value=Decimal("10000"),
        currency="EUR",
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                )
            ],
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365,
            ),
        asset_events=[],
        ).model_dump(mode="json")

    result = await provider.get_current_value("test-1", IdentifierType.OTHER, params)

    # Value should be > initial_value (interest accrued since 2025-01-01)
    assert result.value > Decimal("10000"), f"Expected value > 10000, got {result.value}"
    assert result.currency == "EUR", f"Expected EUR, got {result.currency}"
    assert result.source == "Scheduled Investment Calculator"


@pytest.mark.asyncio
async def test_provider_get_history_value():
    """Test provider get_history_value — pure, no DB access."""
    from backend.app.db.models import IdentifierType

    provider = ScheduledInvestmentProvider()
    params = FAScheduledInvestmentSchedule(
        initial_value=Decimal("10000"),
        currency="EUR",
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                )
            ],
        late_interest=None,
        asset_events=[],
        ).model_dump(mode="json")

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
async def test_provider_private_calculate_value():
    """Test provider private _calculate_value_for_date method."""
    provider = ScheduledInvestmentProvider()

    params = FAScheduledInvestmentSchedule(
        initial_value=Decimal("10000"),
        currency="EUR",
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                )
            ],
        late_interest=None,
        asset_events=[],
        )

    # Calculate value for Jan 30, 2025 (29 days from Jan 1)
    value = provider._calculate_value_for_date(params, date(2025, 1, 30))

    # Expected: 10000 + (10000 * 0.05 * 29/365) ≈ 10039.73
    expected_interest = Decimal("10000") * Decimal("0.05") * Decimal("29") / Decimal("365")
    expected_value = Decimal("10000") + expected_interest

    diff = abs(value - expected_value)
    assert diff < Decimal("0.01"), f"Value mismatch: expected {expected_value}, got {value}, diff {diff}"


@pytest.mark.asyncio
async def test_provider_with_interest_event():
    """Test that INTEREST event reduces price (ex-date drop)."""
    provider = ScheduledInvestmentProvider()

    params = FAScheduledInvestmentSchedule(
        initial_value=Decimal("10000"),
        currency="EUR",
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                )
            ],
        late_interest=None,
        asset_events=[
            FAAssetEventPoint(
                date=date(2025, 7, 1),
                type="INTEREST",
                value=Decimal("250"),
                currency="EUR",
                notes="H1 interest payout",
                ),
            ],
        )

    # Before the event: value should not be affected
    value_before = provider._calculate_value_for_date(params, date(2025, 6, 30))
    # After the event: value should drop by 250
    value_after = provider._calculate_value_for_date(params, date(2025, 7, 1))

    # The drop should be approximately 250 (plus one day of interest difference)
    drop = value_before - value_after
    # drop should be close to 250 - 1 day interest ≈ 250 - 1.37 ≈ 248.63
    assert drop > Decimal("248"), f"Expected drop ~250, got {drop}"
    assert drop < Decimal("252"), f"Expected drop ~250, got {drop}"


@pytest.mark.asyncio
async def test_provider_with_price_adjustment_event():
    """Test that PRICE_ADJUSTMENT event modifies value algebraically."""
    provider = ScheduledInvestmentProvider()

    params = FAScheduledInvestmentSchedule(
        initial_value=Decimal("10000"),
        currency="EUR",
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                )
            ],
        late_interest=None,
        asset_events=[
            FAAssetEventPoint(
                date=date(2025, 6, 1),
                type="PRICE_ADJUSTMENT",
                value=Decimal("-1000"),
                notes="Write-down",
                ),
            ],
        )

    # Before the event
    value_before = provider._calculate_value_for_date(params, date(2025, 5, 31))
    # After the event
    value_after = provider._calculate_value_for_date(params, date(2025, 6, 1))

    # After event, value should be ~1000 less (plus 1 day interest difference)
    drop = value_before - value_after
    assert drop > Decimal("998"), f"Expected drop ~1000, got {drop}"
    assert drop < Decimal("1002"), f"Expected drop ~1000, got {drop}"


@pytest.mark.asyncio
async def test_provider_history_with_events():
    """Test that get_history_value returns events filtered to range."""
    from backend.app.db.models import IdentifierType

    provider = ScheduledInvestmentProvider()
    params = FAScheduledInvestmentSchedule(
        initial_value=Decimal("10000"),
        currency="EUR",
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                )
            ],
        late_interest=None,
        asset_events=[
            FAAssetEventPoint(date=date(2025, 3, 15), type="INTEREST", value=Decimal("100")),
            FAAssetEventPoint(date=date(2025, 6, 15), type="INTEREST", value=Decimal("100")),
            FAAssetEventPoint(date=date(2025, 9, 15), type="INTEREST", value=Decimal("100")),
            ],
        ).model_dump(mode="json")

    # Query only March
    result = await provider.get_history_value("test-1", IdentifierType.OTHER, params, date(2025, 3, 1), date(2025, 3, 31))

    assert len(result.events) == 1, f"Expected 1 event in March, got {len(result.events)}"
    assert result.events[0].date == date(2025, 3, 15)


@pytest.mark.asyncio
async def test_provider_late_interest():
    """Test late interest calculation after maturity."""
    provider = ScheduledInvestmentProvider()

    params = FAScheduledInvestmentSchedule(
        initial_value=Decimal("10000"),
        currency="EUR",
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.05"),
                compounding=CompoundingType.SIMPLE,
                day_count=DayCountConvention.ACT_365,
                )
            ],
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365,
            ),
        asset_events=[],
        )

    # At maturity
    value_maturity = provider._calculate_value_for_date(params, date(2025, 3, 31))

    # During grace period (uses last scheduled rate 0.05)
    value_grace = provider._calculate_value_for_date(params, date(2025, 4, 15))
    assert value_grace > value_maturity, "Value should increase during grace period"

    # After grace period (uses late rate 0.12)
    value_late = provider._calculate_value_for_date(params, date(2025, 6, 1))
    assert value_late > value_grace, "Value should increase further with late interest"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
