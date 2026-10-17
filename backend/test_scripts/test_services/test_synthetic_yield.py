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

J-39 (lot CP-14b, workstream J), the section before the golden: without late interest, the MATURITY_SETTLEMENT of a
schedule whose last period pays coupons is the value after the final coupon (the principal), not the chart's value
before it. Before: it read ``values[last_end]``, so the final coupon was counted twice, as INTEREST and inside the
settlement, and so were ``get_current_value`` and ``get_history_value`` after maturity. Its tests marked "Red" fail on
that code; those marked "Guard" pass before and after.

ACCRUAL GOLDEN (lot CP-14a, workstream J, U10 / decision D-8): the section at the end freezes,
digit for digit, what ``_generate_schedule_values``, ``_compute_value_at`` and
``_compute_late_interest_value`` return on a matrix of schedules, in
``backend/test_scripts/fixtures/scheduled_investment/accrual_golden.json``. U10 moves the day
counts and simple interest into ``financial_math/interest.py`` and merges the provider's
duplicated day-by-day walks into one: not a number may change. Regenerate the golden only for a
reviewed, intended change of these numbers:

    LIBREFOLIO_TEST_REGEN_SI_ACCRUAL_GOLDEN=1 ./dev.py test services synthetic-yield accrual_golden

The switch is a ``LIBREFOLIO_TEST_*`` name because a test lane drops every other ``LIBREFOLIO_*``
variable of the shell before pytest starts (``configure_test_runtime``, ``scripts/cli_base.py``).
"""

import difflib
import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

# Force test mode BEFORE any other imports
os.environ["LIBREFOLIO_TEST_MODE"] = "1"

from backend.app.db.models import IdentifierType
from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.assets.scheduled_investment import (
    DayCountConvention,
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
    InterestType,
    MaturationFrequency,
)
from backend.app.schemas.common import Currency
from backend.app.services.asset_source_providers.scheduled_investment.plugin import (
    ScheduledInvestmentProvider,
    _compute_late_interest_value,
    _compute_value_at,
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
    base_args = {
        "initial_value": Currency(code="EUR", amount=Decimal("10000")),
        "schedule": [
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.10"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        "asset_events": [],
    }

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
    base_args = {
        "initial_value": Currency(code="EUR", amount=Decimal("10000")),
        "interest_type": InterestType.COMPOUND,
        "schedule": [
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
            )
        ],
        "asset_events": [],
    }

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
    base_args = {
        "initial_value": Currency(code="EUR", amount=Decimal("10000")),
        "schedule": [
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        "asset_events": [],
    }

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
    from pydantic import ValidationError  # noqa: PLC0415 — test setup — imports after sys.path/db config

    # Empty schedule with no initial_value → should raise
    with pytest.raises(ValidationError):
        FAScheduledInvestmentSchedule(
            initial_value=None,  # required, not nullable
            schedule=[],
        )


@pytest.mark.asyncio
async def test_validate_params_invalid_day_count():
    """Test that invalid day count convention is rejected by Pydantic."""
    from pydantic import ValidationError  # noqa: PLC0415 — test setup — imports after sys.path/db config

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


# ============================================================================
# J-39 — THE MATURITY SETTLEMENT IS THE VALUE AFTER THE FINAL COUPON (lot CP-14b, workstream J)
# ============================================================================
#
# Without late interest, ``_generate_schedule_values`` closes a schedule whose last period pays coupons with a
# MATURITY_SETTLEMENT on its last day. That same day the walk pays the final coupon as an auto INTEREST event, and after
# a coupon the value restarts from the principal: the settlement is the value after the final coupon, the principal.
# Before: the settlement read ``values[last_end]``, the chart's value BEFORE that day's coupon (I-bis #26), so the final
# coupon was paid twice, once as INTEREST and once inside the settlement; ``get_current_value`` and ``get_history_value``
# after maturity read the settlement and paid it twice too.
#
# Unchanged, and guarded here: the chart's maturation value ``values[last_end]`` (the pre-coupon peak); no settlement
# when the last period pays no coupons, nor in ``_generate_schedule_values`` when the schedule has late interest; a last
# day that pays no coupon (its value not above the principal) settles at that day's value. The late-interest part of
# J-39 (the base of late interest, the late settlement) waits for the developer and is deliberately not tested here.
#
# The bond: 10 000 EUR at 5 %, ACT/365, SIMPLE, one ANNUAL period over 2024 (maturation dates 1/1 and 31/12) paying its
# interest at maturity, no late interest. Its one coupon, read off the walk (worked out, not run):
#   - 365 accrual days (2/1 .. 31/12 of a leap year), each 10 000 x 0.05 x 1/365 = 1.369863013698630136986301370 in the
#     default 28-digit Decimal context;
#   - the running sum is exact for 72 days; the 73rd rounds 100.00000000000000000000000001 down to 100, and each of the
#     292 days after adds 1.3698630136986301369863014 (25 decimals fit there): 500.0000000000000000000000088;
#   - the day's value, 10 000 + that sum at 28 digits, is 10 500.00000000000000000000001, and the coupon (value minus
#     principal) 500.00000000000000000000001: one year of 5 % on 10 000, 1e-23 above 500 by rounding.

_J39_PRINCIPAL = Decimal("10000")
_J39_START = date(2024, 1, 1)
_J39_MATURITY = date(2024, 12, 31)
_J39_COUPON = Decimal("500.00000000000000000000001")


def _j39_bond(*, coupons: bool = True, asset_events: list[FAAssetEventPoint] | None = None, late_interest: FALateInterestConfig | None = None) -> FAScheduledInvestmentSchedule:
    """The J-39 bond of the section's comment; ``coupons=False`` makes its (last) period pay none."""
    return FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=_J39_PRINCIPAL),
        interest_type=InterestType.SIMPLE,
        day_count=DayCountConvention.ACT_365,
        schedule=[FAInterestRatePeriod(start_date=_J39_START, end_date=_J39_MATURITY, annual_rate=Decimal("0.05"), maturation_frequency=MaturationFrequency.ANNUAL, generate_interest=coupons)],
        late_interest=late_interest,
        asset_events=asset_events or [],
    )


def _j39_events(events: list[FAAssetEventPoint]) -> list[tuple[date, str, Decimal, str]]:
    """Events as (date, type, amount, currency code), in the order given. The notes are not part of the contract."""
    return [(event.date, event.type, event.value.amount, event.value.code) for event in events]


def test_j39_maturity_settlement_is_the_principal_after_the_final_coupon():
    """Red. The last day pays the final coupon, then settles the principal: the coupon is counted once.

    Before: [INTEREST 500.00000000000000000000001, MATURITY_SETTLEMENT 10 500.00000000000000000000001] on 31/12/2024.
    Contract: [INTEREST 500.00000000000000000000001, MATURITY_SETTLEMENT 10 000], amounts compared exactly; the coupon and
    the chart's maturation values (the principal on 1/1, principal + coupon on 31/12) unchanged.
    """
    values, auto_events = _generate_schedule_values(_j39_bond())

    peaks = {_J39_START: _J39_PRINCIPAL, _J39_MATURITY: _J39_PRINCIPAL + _J39_COUPON}
    premise = "premise, unchanged by J-39: the maturation values are the principal and principal + the final coupon (the pre-coupon peak)"
    misread = "If only the digits of the coupon differ, the reading of the walk in the section's comment is wrong, not the code."
    assert values == peaks, f"{premise}, got {values}. {misread}"
    assert _j39_events(auto_events) == [
        (_J39_MATURITY, "INTEREST", _J39_COUPON, "EUR"),
        (_J39_MATURITY, "MATURITY_SETTLEMENT", _J39_PRINCIPAL, "EUR"),
    ]


@pytest.mark.asyncio
async def test_j39_current_value_after_maturity_is_the_principal():
    """Red. The bond matured on 31/12/2024, so today is after maturity whatever day the test runs: the value is the settlement.

    Before: 10 500.00000000000000000000001, the settlement with the final coupon still inside it.
    Contract: 10 000.
    """
    assert date.today() > _J39_MATURITY, "premise: the bond has matured"

    result = await ScheduledInvestmentProvider().get_current_value("j39", IdentifierType.OTHER, _j39_bond().model_dump())

    assert result.value == _J39_PRINCIPAL, f"current value after maturity: expected the principal {_J39_PRINCIPAL}, got {result.value}"
    assert result.currency == "EUR"


@pytest.mark.asyncio
async def test_j39_history_after_maturity_anchors_the_principal():
    """Red. A history past maturity: the pre-coupon peak on the last day, then the principal after the settlement.

    Before: the anchor of 31/3/2025 and the MATURITY_SETTLEMENT event are 10 500.00000000000000000000001.
    Contract: points [1/1/2024 10 000, 31/12/2024 principal + coupon (unchanged), 31/3/2025 10 000]; events [INTEREST
    coupon, MATURITY_SETTLEMENT 10 000], both on 31/12/2024.
    """
    end = date(2025, 3, 31)

    result = await ScheduledInvestmentProvider().get_history_value("j39", IdentifierType.OTHER, _j39_bond().model_dump(), _J39_START, end)

    assert [(point.date, point.close) for point in result.prices] == [
        (_J39_START, _J39_PRINCIPAL),
        (_J39_MATURITY, _J39_PRINCIPAL + _J39_COUPON),
        (end, _J39_PRINCIPAL),
    ]
    assert _j39_events(result.events) == [
        (_J39_MATURITY, "INTEREST", _J39_COUPON, "EUR"),
        (_J39_MATURITY, "MATURITY_SETTLEMENT", _J39_PRINCIPAL, "EUR"),
    ]


def test_j39_guard_a_last_period_without_coupons_settles_nothing():
    """Guard, green before and after: a last period with ``generate_interest=False`` emits no coupon and no settlement.

    Its maturation value is the same pre-coupon value as the bond that pays the coupon: the whole year's interest.
    """
    values, auto_events = _generate_schedule_values(_j39_bond(coupons=False))
    paying_values, _paying_events = _generate_schedule_values(_j39_bond())

    assert auto_events == []
    assert values[_J39_MATURITY] == paying_values[_J39_MATURITY]


def test_j39_guard_a_last_day_without_a_coupon_settles_at_its_value():
    """Guard, green before and after: a last day that pays no coupon settles at its own value.

    A write-down of 1 000 in July keeps the value under the principal at maturity, so the last day pays no coupon (only a
    positive one is paid) and there is no coupon to take out of the settlement.
    """
    write_down = FAAssetEventPoint(date=date(2024, 7, 1), type="PRICE_ADJUSTMENT", value=Currency(code="EUR", amount=Decimal("-1000")), notes="Write-down")

    values, auto_events = _generate_schedule_values(_j39_bond(asset_events=[write_down]))

    last_value = values[_J39_MATURITY]
    assert last_value < _J39_PRINCIPAL, f"premise: the write-down keeps the last day under the principal, got {last_value}"
    assert _j39_events(auto_events) == [(_J39_MATURITY, "MATURITY_SETTLEMENT", last_value, "EUR")]


def test_j39_guard_a_schedule_with_late_interest_settles_nothing_at_maturity():
    """Guard, green before and after: with late interest the final coupon is paid and no settlement is emitted at maturity.

    Whether and when a schedule with late interest settles is the part of J-39 left to the developer: not tested here.
    """
    late = FALateInterestConfig(annual_rate=Decimal("0.10"), grace_period_days=30, interest_type=InterestType.SIMPLE)

    values, auto_events = _generate_schedule_values(_j39_bond(late_interest=late))

    assert _j39_events(auto_events) == [(_J39_MATURITY, "INTEREST", values[_J39_MATURITY] - _J39_PRINCIPAL, "EUR")]


# ============================================================================
# ACCRUAL GOLDEN — the safety net of lot U10 (CP-14a, workstream J, decision D-8)
# ============================================================================
#
# U10 moves the day counts and simple interest into financial_math/interest.py and merges the provider's two
# day-by-day walks (_generate_schedule_values, _compute_value_at) and the two branch pairs of
# _compute_late_interest_value into one walk. The golden holds what the three functions return today, and every
# later run must write the same text: every Decimal with str() (its digits and its exponent: a sum done in another
# order can change the last digit), dates in ISO, None as null, an event as [date, type, amount, code, notes] in the
# order the function returns them.
#
# Four shapes, each under the four day counts and the two interest types (32 cases), and the empty schedule:
#   s1  one MONTHLY period from a month end, across a year end and 29 February (the maturation dates drift: 30/11,
#       30/12, 30/01, 29/02, ...); no coupons, no manual events; SIMPLE late interest, 30 days of grace.
#   s2  a QUARTERLY then a SEMIANNUAL period, each ending on 31/12, at different rates; coupons; a manual INTEREST on a
#       maturation date and a PRICE_ADJUSTMENT between two; COMPOUND late interest, 15 days of grace.
#   s3  20 DAILY days across 29 February, a coupon every day; a PRICE_ADJUSTMENT of -8 keeps the value under the
#       principal for four days, which pay no coupon and do not reset; late interest of the schedule's own type and
#       no grace.
#   s4  ANNUAL over two years with coupons and no late interest: the MATURITY_SETTLEMENT event.
# _compute_value_at is read the day before the start (None), on the start and the day after, on every maturation date
# and the day after it, on the manual events' days and a few others, on the last day and the day after the end (None).
# _compute_late_interest_value, given values[last day], is read the day after maturity, on the last day of grace and
# the first after it, 40 days after maturity, and more than a year after it, past a 31/12.
#
# Lot CP-14b (workstream J) fixed two of the defects these numbers had frozen, and regenerated the fixture on purpose with
# the change declared:
#   - ACT/ACT is ISDA: a span no longer loses a day at every year end it crosses. Exactly 3 points changed, all SIMPLE
#     late interest in closed form over a 31/12, each one more day of late interest: s1 ACT/ACT compound and simple at
#     2025-05-15, s3 ACT/ACT simple at 2025-03-20. Day-by-day steps (the accrual walk, COMPOUND late interest) did not
#     move: a one-day step over a year end was already right.
#   - The maturity settlement is the value after the final coupon (J-39): the 8 MATURITY_SETTLEMENT amounts of
#     s4_annual_settlement (4 day counts x 2 interest types) are now the principal, 12345.67.
# R13-SEC7-2 (workstream MF, night decision N73) regenerated it once more, with the change declared: COMPOUND late interest
# is the closed form of the daily product (financial_math.interest.compound_growth) instead of a step per day rounded at
# every step, so 44 late_interest_value_at entries moved in their last digits, at most 1.05e-25 relative — the 8 s2 cases
# (their late interest is COMPOUND) and the 4 s3 compound cases. Nothing else moved: values, value_at, auto_events and
# every SIMPLE late value (ACT/ACT keeps its year-by-year sum, digit for digit) are as before.
# The COMPOUND base (it leaves out the manual events) is still frozen as it is: it waits for the developer, and the lot
# that changes it regenerates this file the same way, with the change declared.

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "scheduled_investment" / "accrual_golden.json"
_REGEN_ENV = "LIBREFOLIO_TEST_REGEN_SI_ACCRUAL_GOLDEN"
_REGEN_COMMAND = f"{_REGEN_ENV}=1 ./dev.py test services synthetic-yield accrual_golden"
_DIFF_LINES = 120

# Readable ids of the day counts ("ACT/365" carries a slash). A new convention is a KeyError here: extend the golden.
_DAY_COUNT_IDS = {
    DayCountConvention.ACT_365: "act365",
    DayCountConvention.ACT_360: "act360",
    DayCountConvention.ACT_ACT: "actact",
    DayCountConvention.THIRTY_360: "30-360",
}


@dataclass(frozen=True)
class _GoldenCase:
    """A schedule of the golden and the days its walk and its late interest are read on."""

    schedule: FAScheduledInvestmentSchedule
    value_at_dates: tuple[date, ...]
    late_targets: tuple[date, ...]


def _days(*texts: str) -> tuple[date, ...]:
    return tuple(date.fromisoformat(text) for text in texts)


def _span(first: str, last: str) -> tuple[date, ...]:
    """Every day from ``first`` to ``last``, both included."""
    start, end = date.fromisoformat(first), date.fromisoformat(last)
    return tuple(start + timedelta(days=offset) for offset in range((end - start).days + 1))


def _principal() -> Currency:
    return Currency(code="EUR", amount=Decimal("12345.67"))


def _period(start: str, end: str, rate: str, frequency: MaturationFrequency, *, coupons: bool) -> FAInterestRatePeriod:
    return FAInterestRatePeriod(start_date=date.fromisoformat(start), end_date=date.fromisoformat(end), annual_rate=Decimal(rate), maturation_frequency=frequency, generate_interest=coupons)


def _manual(day: str, kind: str, amount: str) -> FAAssetEventPoint:
    return FAAssetEventPoint(date=date.fromisoformat(day), type=kind, value=Currency(code="EUR", amount=Decimal(amount)))


def _shape_one_period_monthly(day_count: DayCountConvention, interest_type: InterestType) -> _GoldenCase:
    """s1. Maturation dates: 31/10, 30/11, 30/12, 30/01, 29/02, 29/03, 29/04 and the last day 30/04."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=interest_type,
        day_count=day_count,
        schedule=[_period("2023-10-31", "2024-04-30", "0.0475", MaturationFrequency.MONTHLY, coupons=False)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.12"), grace_period_days=30, interest_type=InterestType.SIMPLE),
        asset_events=[],
    )
    value_at = _days(
        "2023-10-30",
        "2023-10-31",
        "2023-11-01",
        "2023-11-15",
        "2023-11-30",
        "2023-12-01",
        "2023-12-30",
        "2023-12-31",
        "2024-01-01",
        "2024-01-30",
        "2024-01-31",
        "2024-02-28",
        "2024-02-29",
        "2024-03-01",
        "2024-03-29",
        "2024-03-30",
        "2024-04-15",
        "2024-04-29",
        "2024-04-30",
        "2024-05-01",
    )
    # Maturity 30/04: the day after, the last day of grace (30/05), the first after it, +40 days, past 31/12/2024.
    late = _days("2024-05-01", "2024-05-30", "2024-05-31", "2024-06-09", "2025-05-15")
    return _GoldenCase(schedule, value_at, late)


def _shape_two_periods_coupons(day_count: DayCountConvention, interest_type: InterestType) -> _GoldenCase:
    """s2. Maturation dates: 01/07, 01/10, 31/12 of 2023 (QUARTERLY at 4.5 %), 01/01, 01/07, 31/12 of 2024 (SEMIANNUAL at 6 %)."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=interest_type,
        day_count=day_count,
        schedule=[
            _period("2023-07-01", "2023-12-31", "0.045", MaturationFrequency.QUARTERLY, coupons=True),
            _period("2024-01-01", "2024-12-31", "0.06", MaturationFrequency.SEMIANNUAL, coupons=True),
        ],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.10"), grace_period_days=15, interest_type=InterestType.COMPOUND),
        asset_events=[_manual("2023-10-01", "INTEREST", "10"), _manual("2024-03-15", "PRICE_ADJUSTMENT", "-25")],
    )
    value_at = _days(
        "2023-06-30",
        "2023-07-01",
        "2023-07-02",
        "2023-08-15",
        "2023-09-30",
        "2023-10-01",
        "2023-10-02",
        "2023-11-30",
        "2023-12-31",
        "2024-01-01",
        "2024-01-02",
        "2024-02-29",
        "2024-03-15",
        "2024-03-16",
        "2024-05-31",
        "2024-07-01",
        "2024-07-02",
        "2024-10-15",
        "2024-12-31",
        "2025-01-01",
    )
    # Maturity 31/12/2024: the day after (past a 31/12), the last day of grace (15/01), the first after it, +40 days,
    # past 31/12/2025.
    late = _days("2025-01-01", "2025-01-15", "2025-01-16", "2025-02-09", "2026-01-10")
    return _GoldenCase(schedule, value_at, late)


def _shape_daily_coupons(day_count: DayCountConvention, interest_type: InterestType) -> _GoldenCase:
    """s3. Every day is a maturation date. The -8 of 24/02 outweighs four days' interest (about 1.7 a day): no coupon until the accrual covers it."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=interest_type,
        day_count=day_count,
        schedule=[_period("2024-02-20", "2024-03-10", "0.05", MaturationFrequency.DAILY, coupons=True)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.09"), grace_period_days=0, interest_type=interest_type),
        asset_events=[_manual("2024-02-24", "PRICE_ADJUSTMENT", "-8")],
    )
    # No grace: the day after maturity is the first day of late interest; then +40 days, and past 31/12/2024.
    late = _days("2024-03-11", "2024-04-19", "2025-03-20")
    return _GoldenCase(schedule, _span("2024-02-19", "2024-03-11"), late)


def _shape_annual_settlement(day_count: DayCountConvention, interest_type: InterestType) -> _GoldenCase:
    """s4. Maturation dates: 30/06 of 2022, 2023 and 2024; no late interest, so the last day settles the asset."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=interest_type,
        day_count=day_count,
        schedule=[_period("2022-06-30", "2024-06-30", "0.035", MaturationFrequency.ANNUAL, coupons=True)],
        late_interest=None,
        asset_events=[],
    )
    value_at = _days(
        "2022-06-29",
        "2022-06-30",
        "2022-07-01",
        "2022-12-31",
        "2023-01-01",
        "2023-06-30",
        "2023-07-01",
        "2023-12-31",
        "2024-01-01",
        "2024-02-29",
        "2024-03-01",
        "2024-06-29",
        "2024-06-30",
        "2024-07-01",
    )
    return _GoldenCase(schedule, value_at, ())


_GOLDEN_SHAPES = {
    "s1_one_period_monthly": _shape_one_period_monthly,
    "s2_two_periods_coupons": _shape_two_periods_coupons,
    "s3_daily_coupons": _shape_daily_coupons,
    "s4_annual_settlement": _shape_annual_settlement,
}


def _golden_cases() -> dict[str, _GoldenCase]:
    """The cases by readable id (``<shape>-<day count>-<interest type>``), and the empty schedule: 33 today."""
    cases = {f"{shape}-{_DAY_COUNT_IDS[day_count]}-{interest_type.value.lower()}": build(day_count, interest_type) for shape, build in _GOLDEN_SHAPES.items() for day_count in DayCountConvention for interest_type in InterestType}
    cases["s0_empty_schedule"] = _GoldenCase(FAScheduledInvestmentSchedule(initial_value=_principal(), schedule=[]), _days("2024-01-01"), ())
    expected = len(_GOLDEN_SHAPES) * len(DayCountConvention) * len(InterestType) + 1
    assert len(cases) == expected, f"expected {expected} cases with distinct ids, got {len(cases)}: {sorted(cases)}"
    return cases


def _text(value: Decimal | None) -> str | None:
    """A Decimal as ``str()`` writes it, digits and exponent; None stays None. Anything else is a change of type."""
    if value is None:
        return None
    assert isinstance(value, Decimal), f"expected a Decimal, got {type(value).__name__} {value!r}"
    return str(value)


def _dump_case(case: _GoldenCase) -> dict:
    """What the three functions return for one case; the late interest only where the schedule has some."""
    schedule = case.schedule
    values, auto_events = _generate_schedule_values(schedule)
    dump = {
        "values": {day.isoformat(): _text(value) for day, value in values.items()},
        "auto_events": [[event.date.isoformat(), event.type, _text(event.value.amount), event.value.code, event.notes] for event in auto_events],
        "value_at": {day.isoformat(): _text(_compute_value_at(schedule, day)) for day in case.value_at_dates},
        "late_interest_value_at": {},
    }
    if case.late_targets:
        maturity = schedule.schedule[-1].end_date
        dump["late_interest_value_at"] = {day.isoformat(): _text(_compute_late_interest_value(schedule, day, values[maturity], maturity)) for day in case.late_targets}
    return dump


def _diff(expected: str, actual: str, expected_name: str, actual_name: str) -> str:
    """The unified diff of two dumps, cut to its first ``_DIFF_LINES`` lines."""
    lines = list(difflib.unified_diff(expected.splitlines(), actual.splitlines(), expected_name, actual_name, lineterm=""))
    if len(lines) > _DIFF_LINES:
        lines = [*lines[:_DIFF_LINES], f"... {len(lines) - _DIFF_LINES} more lines of diff"]
    return "\n".join(lines)


def test_accrual_golden_walks_agree_on_every_maturation_date():
    """Self-check of the golden's cases: on every date the schedule emits, ``_compute_value_at`` walks to the same value.

    Both are the accrued value after the day's manual events and before the day's coupon reset, so today they agree
    digit for digit, and U10's single walk keeps them so. Green before and after U10.
    """
    disagreements: list[str] = []
    for case_id, case in _golden_cases().items():
        values, _auto_events = _generate_schedule_values(case.schedule)
        for day, value in sorted(values.items()):
            walked = _compute_value_at(case.schedule, day)
            if _text(walked) != _text(value):
                disagreements.append(f"{case_id} {day.isoformat()}: emitted {_text(value)}, walked {_text(walked)}")
    assert not disagreements, "the two walks disagree on maturation dates:\n" + "\n".join(disagreements[:40])


def test_accrual_golden_is_unchanged():
    """The accrual of every case, byte for byte as the golden holds it: U10's safety net, green before and after U10.

    The golden is written by the regeneration command (see the module docstring), once, on the code before U10; from
    then on it is the contract. A missing golden is a failure, never a pass.
    """
    text = json.dumps({case_id: _dump_case(case) for case_id, case in _golden_cases().items()}, sort_keys=True, indent=2) + "\n"
    if os.environ.get(_REGEN_ENV) == "1":
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_text(text, encoding="utf-8")
        pytest.skip("golden regenerated")
    if not GOLDEN_PATH.exists():
        pytest.fail(f"golden file missing: {GOLDEN_PATH}\nGenerate it with: {_REGEN_COMMAND}")
    golden = GOLDEN_PATH.read_text(encoding="utf-8")
    assert text == golden, f"scheduled investment accrual differs from {GOLDEN_PATH.name}:\n" + _diff(golden, text, "golden", "this run")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
