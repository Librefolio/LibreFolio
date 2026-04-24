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

from backend.app.db.models import IdentifierType
from backend.app.schemas.assets import (
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
    InterestType,
    MaturationFrequency,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAAssetEventPoint
from backend.app.services.asset_source_providers.scheduled_investment import ScheduledInvestmentProvider, _compute_value_at, _generate_schedule_values


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
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            ),
            FAInterestRatePeriod(
                start_date=date(2025, 7, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.06"),
                maturation_frequency=MaturationFrequency.DAILY,
            ),
        ],
        late_interest=FALateInterestConfig(
            annual_rate=Decimal("0.12"),
            grace_period_days=30,
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


# Scenario 2: Different maturation frequencies — selective emission
# The engine computes day-by-day internally but only emits price points at
# maturation dates. DAILY emits every day; MONTHLY emits monthly anchors;
# ANNUAL emits only start+end anchors. Final value at end_date is the same
# regardless of frequency (interest accrues identically).
@pytest.mark.asyncio
async def test_e2e_maturation_frequencies():
    base = {
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 12, 31),
        "annual_rate": Decimal("0.04"),
    }

    # Collect end-of-year value for each frequency — must be identical
    end_values = {}
    for freq in [MaturationFrequency.DAILY, MaturationFrequency.MONTHLY, MaturationFrequency.ANNUAL]:
        schedule = FAScheduledInvestmentSchedule(
            initial_value=Currency(code="EUR", amount=Decimal("20000")),
            schedule=[FAInterestRatePeriod(**base, maturation_frequency=freq)],
            asset_events=[],
        )
        params = schedule.model_dump()

        # Query the full year: end_date (Dec 31) is always an anchor
        hist = await _history_values(params, date(2025, 1, 1), date(2025, 12, 31))

        # Start value is always initial_value
        assert hist[0] == Decimal("20000"), f"{freq}: start != 20000"
        # End value must be > start (interest accrued)
        assert hist[-1] > hist[0], f"{freq}: end not > start: {hist[-1]}"
        end_values[freq] = hist[-1]

    # DAILY emits 365 points; MONTHLY ~13; ANNUAL just 2 — but final value is same
    assert end_values[MaturationFrequency.DAILY] == end_values[MaturationFrequency.MONTHLY]
    assert end_values[MaturationFrequency.DAILY] == end_values[MaturationFrequency.ANNUAL]

    # DAILY has more price points than ANNUAL
    daily_schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("20000")),
        schedule=[FAInterestRatePeriod(**base, maturation_frequency=MaturationFrequency.DAILY)],
        asset_events=[],
    )
    annual_schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("20000")),
        schedule=[FAInterestRatePeriod(**base, maturation_frequency=MaturationFrequency.ANNUAL)],
        asset_events=[],
    )
    daily_hist = await _history_values(daily_schedule.model_dump(), date(2025, 1, 1), date(2025, 12, 31))
    annual_hist = await _history_values(annual_schedule.model_dump(), date(2025, 1, 1), date(2025, 12, 31))
    assert len(daily_hist) > len(annual_hist)


# Scenario 3: Multi-period rate changes
@pytest.mark.asyncio
async def test_e2e_multi_period_rate_changes():
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("5000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.03"),
                maturation_frequency=MaturationFrequency.DAILY,
            ),
            FAInterestRatePeriod(
                start_date=date(2025, 4, 1),
                end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.035"),
                maturation_frequency=MaturationFrequency.MONTHLY,
            ),
            FAInterestRatePeriod(
                start_date=date(2025, 7, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.04"),
                maturation_frequency=MaturationFrequency.DAILY,
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


# ============================================================================
# Scenario 4+: generate_interest, auto-coupon, MATURITY_SETTLEMENT
# ============================================================================


@pytest.mark.asyncio
async def test_generate_interest_monthly_coupons():
    """generate_interest=True + MONTHLY → 12 auto INTEREST events, price resets to initial_value each month."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.SIMPLE,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.12"),
                maturation_frequency=MaturationFrequency.MONTHLY,
                generate_interest=True,
            )
        ],
        asset_events=[],
    )
    values, auto_events = _generate_schedule_values(schedule)

    # Auto INTEREST events (excluding MATURITY_SETTLEMENT)
    interest_events = [e for e in auto_events if e.type == "INTEREST"]
    # At least 11 coupons (Feb..Dec maturation dates). Jan 1 = start with 0 interest so no coupon there.
    assert len(interest_events) >= 11, f"Expected ≥11 interest events, got {len(interest_events)}"

    # After each coupon, value should reset close to initial_value (10000)
    # Check end-of-year value: with generate_interest, most interest was paid out
    end_value = values[date(2025, 12, 31)]
    # End value should be close to initial_value (coupon stripped most interest)
    assert end_value < Decimal("10200"), f"After coupons, end value should be near 10000, got {end_value}"


@pytest.mark.asyncio
async def test_generate_interest_compound_resets():
    """generate_interest=True + COMPOUND → after coupon, compound restarts from initial_value."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.COMPOUND,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.12"),
                maturation_frequency=MaturationFrequency.MONTHLY,
                generate_interest=True,
            )
        ],
        asset_events=[],
    )
    values, auto_events = _generate_schedule_values(schedule)
    interest_events = [e for e in auto_events if e.type == "INTEREST"]
    assert len(interest_events) >= 11

    # With compound + generate_interest, each month compounds on ~10000 (not accumulated)
    # End value should be close to initial_value
    end_value = values[date(2025, 12, 31)]
    assert end_value < Decimal("10200"), f"After compound coupons, end should be near 10000, got {end_value}"


@pytest.mark.asyncio
async def test_generate_interest_negative_no_coupon():
    """generate_interest=True + negative PRICE_ADJUSTMENT → no coupon generated (only positive)."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.MONTHLY,
                generate_interest=True,
            )
        ],
        asset_events=[
            FAAssetEventPoint(
                date=date(2025, 1, 2),
                type="PRICE_ADJUSTMENT",
                value=Currency(code="EUR", amount=Decimal("-5000")),
                notes="Massive write-down",
            ),
        ],
    )
    values, auto_events = _generate_schedule_values(schedule)
    interest_events = [e for e in auto_events if e.type == "INTEREST"]
    # After write-down of 5000, value drops below initial_value → no positive coupon possible for a while
    # At most only late months could generate a coupon if interest recovers
    # The key assertion: no coupon on Feb 1 since value was still below principal
    feb_coupons = [e for e in interest_events if e.date == date(2025, 2, 1)]
    assert len(feb_coupons) == 0, "No coupon should be generated when value < initial_value"


@pytest.mark.asyncio
async def test_maturity_settlement_no_late():
    """generate_interest=True on last period without late → MATURITY_SETTLEMENT at end_date."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.06"),
                maturation_frequency=MaturationFrequency.MONTHLY,
                generate_interest=True,
            )
        ],
        late_interest=None,
        asset_events=[],
    )
    values, auto_events = _generate_schedule_values(schedule)
    settlements = [e for e in auto_events if e.type == "MATURITY_SETTLEMENT"]
    assert len(settlements) == 1, f"Expected 1 MATURITY_SETTLEMENT, got {len(settlements)}"
    assert settlements[0].date == date(2025, 6, 30)
    # Settlement value should be close to initial_value (since coupons were paid out)
    assert settlements[0].value.amount < Decimal("10200")


@pytest.mark.asyncio
async def test_get_current_value_after_settlement():
    """get_current_value after MATURITY_SETTLEMENT → returns settlement value (engine stopped)."""
    provider = ScheduledInvestmentProvider()
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2024, 1, 1),
                end_date=date(2024, 6, 30),
                annual_rate=Decimal("0.06"),
                maturation_frequency=MaturationFrequency.MONTHLY,
                generate_interest=True,
            )
        ],
        late_interest=None,
        asset_events=[],
    )
    params = schedule.model_dump()

    # Current date (2026-04-03) is well past settlement (2024-06-30)
    result = await provider.get_current_value("test-1", IdentifierType.OTHER, params)

    # Should return the settlement value, no further interest
    _, auto_events = _generate_schedule_values(schedule)
    settlement = next(e for e in auto_events if e.type == "MATURITY_SETTLEMENT")
    assert result.value == settlement.value.amount, f"Expected settlement value {settlement.value.amount}, got {result.value}"


@pytest.mark.asyncio
async def test_auto_and_manual_interest_coexist():
    """Auto INTEREST + manual INTEREST on same date → both appear in events."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 6, 30),
                annual_rate=Decimal("0.12"),
                maturation_frequency=MaturationFrequency.MONTHLY,
                generate_interest=True,
            )
        ],
        late_interest=None,
        asset_events=[
            FAAssetEventPoint(
                date=date(2025, 2, 1),
                type="INTEREST",
                value=Currency(code="EUR", amount=Decimal("50")),
                notes="Manual extra interest",
            ),
        ],
    )
    params = schedule.model_dump()
    provider = ScheduledInvestmentProvider()
    result = await provider.get_history_value("test", IdentifierType.OTHER, params, date(2025, 1, 1), date(2025, 6, 30))

    # Events on Feb 1: should have both auto + manual
    feb_events = [e for e in result.events if e.date == date(2025, 2, 1) and e.type == "INTEREST"]
    assert len(feb_events) >= 2, f"Expected ≥2 INTEREST events on Feb 1 (auto+manual), got {len(feb_events)}"


# =============================================================================
# I-bis #26 — regression tests: emitted value at maturation date is PRE-reset
# =============================================================================


@pytest.mark.asyncio
async def test_generate_interest_daily_emits_pre_reset_value():
    """I-bis #26: DAILY + generate_interest=True must emit the pre-reset
    accrued value; the old bug emitted post-reset principal → flat series."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.SIMPLE,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.12"),
                maturation_frequency=MaturationFrequency.DAILY,
                generate_interest=True,
            )
        ],
        asset_events=[],
    )
    values, _ = _generate_schedule_values(schedule)

    v_jan_2 = values[date(2025, 1, 2)]
    assert v_jan_2 > Decimal("10000"), f"DAILY + gen_interest=True must emit pre-reset value; got flat {v_jan_2} → " "I-bis #26 regression (Step 2 running before value emission)."
    assert v_jan_2 < Decimal("10010"), f"Day-1 accrual looks implausible: {v_jan_2}"


@pytest.mark.asyncio
async def test_generate_interest_weekly_shows_sawtooth_peaks():
    """I-bis #26: WEEKLY + generate_interest=True must produce peaks > initial_value."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.SIMPLE,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 3, 31),
                annual_rate=Decimal("0.52"),
                maturation_frequency=MaturationFrequency.WEEKLY,
                generate_interest=True,
            )
        ],
        asset_events=[],
    )
    values, auto_events = _generate_schedule_values(schedule)

    interest_events = [e for e in auto_events if e.type == "INTEREST"]
    assert len(interest_events) >= 10, f"Expected ≥10 weekly coupons, got {len(interest_events)}"

    peaks = [v for v in values.values() if v > Decimal("10000")]
    assert len(peaks) >= 5, f"WEEKLY sawtooth must emit values > 10000 at maturation peaks; got {len(peaks)} → " "I-bis #26 regression."


# =============================================================================
# current_price intra-cycle accrual — regression tests (retest 2026-04-24)
# =============================================================================
#
# Bug: ``get_current_value`` backward-filled from the most recent cached
# maturation date, which returned the pre-reset peak (== the coupon just
# paid). Correct behaviour: on the day AFTER a coupon payout, the accrued
# value should restart from principal and grow intra-cycle.
# Fix: ``_compute_value_at`` re-walks the schedule day-by-day up to the
# target date applying manual subtractive events + auto-coupon resets.


def test_compute_value_at_semiannual_after_first_coupon_is_close_to_principal():
    """After a SEMIANNUAL coupon + 1 day, the value should be ~principal,
    NOT the pre-reset peak (~10500 at 5% annual on 10k over 6mo)."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.SIMPLE,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.10"),
                maturation_frequency=MaturationFrequency.SEMIANNUAL,
                generate_interest=True,
            )
        ],
        asset_events=[],
    )
    # Jul 2 is the day after the first SEMIANNUAL maturation (Jul 1 is the
    # reset point). Value should be back to ~principal + 1 day of accrual,
    # NOT ~10500.
    v_jul2 = _compute_value_at(schedule, date(2025, 7, 2))
    assert v_jul2 is not None
    # 1 day at 10% annual on 10k ≈ 2.74 EUR
    assert Decimal("10001") <= v_jul2 <= Decimal("10010"), f"Post-coupon intra-cycle value should be ~principal + 1d accrual; got {v_jul2}. " "If this is ~10500 the fix has regressed (backward-fill to peak)."


def test_compute_value_at_semiannual_mid_cycle_grows_monotonically():
    """Between two coupons, the value should grow monotonically from
    principal to the next peak — no early resets."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.SIMPLE,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.12"),
                maturation_frequency=MaturationFrequency.SEMIANNUAL,
                generate_interest=True,
            )
        ],
        asset_events=[],
    )
    # Sample days after the first coupon (Jul 1 → reset). Aug 1, Sep 1, Oct 1
    # should form a strictly increasing sequence.
    v_aug = _compute_value_at(schedule, date(2025, 8, 1))
    v_sep = _compute_value_at(schedule, date(2025, 9, 1))
    v_oct = _compute_value_at(schedule, date(2025, 10, 1))
    assert v_aug is not None and v_sep is not None and v_oct is not None
    assert Decimal("10000") < v_aug < v_sep < v_oct, f"Expected strictly increasing series Aug<Sep<Oct after coupon; got {v_aug}, {v_sep}, {v_oct}."


def test_compute_value_at_respects_manual_interest_subtractive_event():
    """A manual INTEREST event is subtractive — _compute_value_at should
    reflect the coupon payout on the requested date."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        interest_type=InterestType.SIMPLE,
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.12"),
                maturation_frequency=MaturationFrequency.ANNUAL,
                generate_interest=False,  # No auto-coupon; manual event drives the subtraction
            )
        ],
        asset_events=[
            FAAssetEventPoint(
                date=date(2025, 6, 1),
                type="INTEREST",
                value=Currency(code="EUR", amount=Decimal("500")),
                notes="manual coupon",
            )
        ],
    )
    # Before manual event (May 31): value ~ principal + 5mo accrual (≈ 500)
    v_before = _compute_value_at(schedule, date(2025, 5, 31))
    # On manual event day (Jun 1): value AFTER subtraction (principal + accrual - 500)
    v_on = _compute_value_at(schedule, date(2025, 6, 1))
    # Right after (Jun 2): value continues from v_on + 1d accrual
    v_after = _compute_value_at(schedule, date(2025, 6, 2))
    assert v_before is not None and v_on is not None and v_after is not None
    assert v_on < v_before, f"Manual INTEREST must lower the value on its date; got before={v_before} on={v_on}."
    # Jun 2 = v_on + 1d accrual. Must be > v_on but much less than v_before.
    assert v_on < v_after < v_before, f"Post-event day should resume accrual from reduced value; got {v_on}/{v_after}/{v_before}."


def test_compute_value_at_returns_none_outside_schedule():
    """Before first_start or after last_end → None (caller fallback)."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("10000")),
        schedule=[
            FAInterestRatePeriod(
                start_date=date(2025, 1, 1),
                end_date=date(2025, 12, 31),
                annual_rate=Decimal("0.05"),
                maturation_frequency=MaturationFrequency.DAILY,
            )
        ],
        asset_events=[],
    )
    assert _compute_value_at(schedule, date(2024, 12, 31)) is None
    assert _compute_value_at(schedule, date(2026, 1, 1)) is None
