"""
The bounds of a Scheduled Investment schedule — R13-SEC7-2 (MEDIUM, a DoS), night decision N73, workstream MF.

Before: ``FAScheduledInvestmentSchedule`` checked its periods only for order, overlaps and gaps. The provider walks a
schedule one day at a time, so ``POST /assets/provider/probe`` — a dry run open to any user — with one DAILY period from
year 1 to 9999 walked ~3.65 M days twice, in threads the 15 s timeout does not stop, and cached ~0.7 GB per schedule.

Now (``schemas/assets/scheduled_investment.py``):
    - every period date lies in [1900-01-01, 2200-12-31];
    - a schedule spans at most 36 525 days, from its first start to its last end;
    - a schedule holds at most 1 200 periods;
    - the late interest's ``grace_period_days`` is at most 36 525;
    - a schedule holds at most 10 000 manual ``asset_events`` (MF-SI2, E's review of R13-SEC7-2: every valuation replays
      them, so their number is work too).
Each N73 bound is a ``ValueError`` in a validator; the events bound is the list's ``max_length`` (pydantic ``too_long``).
Either way a pydantic ``ValidationError``, which ``ScheduledInvestmentProvider.validate_params`` turns into
``AssetSourceError`` ``INVALID_PARAMS`` as it does for every other invalid schedule.

The numbers are written out here, not imported: they are the contract N73 (and MF-SI2) fixed, and a test that read them
from the module would follow any change of them. ``test_bounds_are_the_n73_values`` and
``test_events_bound_is_the_mf_si2_value`` pin the module's constants to them.

Each refused input is otherwise valid (contiguous periods, valid rates), so the only rule it can break is the bound under
test; the error's ``loc`` says which validator refused it. A refusal never matches the message text.

"Red" tests fail on the code before the fix: it accepts what they expect refused, or lacks the constants. "Guard" tests
pass before and after: every boundary value itself is accepted, and an ordinary schedule still validates.

Pure: no database, no server, no network. Nothing is computed, only validated.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.app.schemas.assets.scheduled_investment import (
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
)
from backend.app.services.asset_source_providers.scheduled_investment.plugin import ScheduledInvestmentProvider
from backend.app.services.assets.base import AssetSourceError

# The N73 contract, written out (see the module docstring).
MIN_DATE = date(1900, 1, 1)
MAX_DATE = date(2200, 12, 31)
MAX_SPAN_DAYS = 36_525
MAX_PERIODS = 1_200
MAX_GRACE_DAYS = 36_525
# The MF-SI2 contract, written out the same way.
MAX_EVENTS = 10_000


def _period(start: date, end: date, frequency: str = "MONTHLY") -> dict:
    return {"start_date": start.isoformat(), "end_date": end.isoformat(), "annual_rate": "0.05", "maturation_frequency": frequency}


def _params(periods: list[dict], *, grace_days: int | None = None, events: list[dict] | None = None) -> dict:
    params = {"initial_value": {"code": "EUR", "amount": "10000"}, "day_count": "ACT/365", "schedule": periods, "asset_events": events or []}
    if grace_days is not None:
        params["late_interest"] = {"annual_rate": "0.12", "grace_period_days": grace_days}
    return params


def _daily_interest_events(count: int, first: date = date(2020, 1, 1)) -> list[dict]:
    """``count`` valid INTEREST payouts, one a day from ``first``: a list whose only excess can be its length."""
    return [{"date": (first + timedelta(days=offset)).isoformat(), "type": "INTEREST", "value": {"code": "EUR", "amount": "1"}} for offset in range(count)]


def _one_day_periods(count: int, first: date = date(2020, 1, 1)) -> list[dict]:
    """``count`` contiguous one-day periods from ``first``: a schedule whose only excess can be its number of periods."""
    return [_period(first + timedelta(days=offset), first + timedelta(days=offset), "DAILY") for offset in range(count)]


def _assert_refused_at(params: dict, loc: tuple, error_type: str = "value_error") -> None:
    """The schedule is refused, and among its errors is one of ``error_type`` (a ``value_error`` by default) at ``loc``."""
    with pytest.raises(ValidationError) as excinfo:
        FAScheduledInvestmentSchedule(**params)
    errors = {tuple(error["loc"]): error["type"] for error in excinfo.value.errors()}
    assert errors.get(loc) == error_type, f"expected a {error_type} at {loc}, got {errors}"


# ============================================================================
# The constants
# ============================================================================


def test_bounds_are_the_n73_values():
    """Red: the module's bounds are the N73 values (before: the names do not exist)."""
    from backend.app.schemas.assets import scheduled_investment  # noqa: PLC0415 — read here so the Guards import on HEAD

    assert scheduled_investment.SCHEDULE_MIN_DATE == MIN_DATE
    assert scheduled_investment.SCHEDULE_MAX_DATE == MAX_DATE
    assert scheduled_investment.SCHEDULE_MAX_SPAN_DAYS == MAX_SPAN_DAYS
    assert scheduled_investment.SCHEDULE_MAX_PERIODS == MAX_PERIODS
    assert scheduled_investment.LATE_INTEREST_MAX_GRACE_DAYS == MAX_GRACE_DAYS


def test_events_bound_is_the_mf_si2_value():
    """Red: the module's events bound is the MF-SI2 value (before: the name does not exist)."""
    from backend.app.schemas.assets import scheduled_investment  # noqa: PLC0415 — read here so the Guards import on HEAD

    assert getattr(scheduled_investment, "SCHEDULE_MAX_EVENTS", None) == MAX_EVENTS


# ============================================================================
# Period dates in [1900-01-01, 2200-12-31]
# ============================================================================


@pytest.mark.parametrize(
    ("start", "end", "field"),
    [
        pytest.param(MIN_DATE - timedelta(days=1), date(1900, 6, 30), "start_date", id="starts-1899-12-31"),
        pytest.param(date(2200, 6, 1), MAX_DATE + timedelta(days=1), "end_date", id="ends-2201-01-01"),
    ],
)
def test_period_date_outside_1900_2200_is_refused(start, end, field):
    """Red: a period starting before 1900-01-01 or ending after 2200-12-31 is refused on that date, alone and in a schedule."""
    with pytest.raises(ValidationError) as excinfo:
        FAInterestRatePeriod(start_date=start, end_date=end, annual_rate=Decimal("0.05"))
    assert {tuple(error["loc"]) for error in excinfo.value.errors()} == {(field,)}
    _assert_refused_at(_params([_period(start, end)]), ("schedule", 0, field))


def test_period_dates_on_the_bounds_are_accepted():
    """Guard: 1900-01-01 and 2200-12-31 themselves are valid period dates."""
    assert FAScheduledInvestmentSchedule(**_params([_period(MIN_DATE, date(1900, 12, 31))])).schedule[0].start_date == MIN_DATE
    assert FAScheduledInvestmentSchedule(**_params([_period(date(2200, 1, 1), MAX_DATE)])).schedule[0].end_date == MAX_DATE


# ============================================================================
# Span: at most 36 525 days from the first start to the last end
# ============================================================================

# 2000-01-01 + 36 525 days = 2100-01-01 (25 leap days in 2000-2099).
_SPAN_START = date(2000, 1, 1)
_SPAN_LIMIT_END = _SPAN_START + timedelta(days=MAX_SPAN_DAYS)


@pytest.mark.parametrize(
    "periods",
    [
        pytest.param([_period(_SPAN_START, _SPAN_LIMIT_END + timedelta(days=1))], id="one-period"),
        # Each period alone is under 100 years: the bound is on the schedule, not on a period.
        pytest.param([_period(_SPAN_START, date(2049, 12, 31)), _period(date(2050, 1, 1), _SPAN_LIMIT_END + timedelta(days=1))], id="two-periods"),
        # Both dates inside [1900, 2200], 110 years apart: the span bound holds on its own.
        pytest.param([_period(MIN_DATE, date(2010, 1, 1))], id="inside-the-date-bounds"),
    ],
)
def test_span_over_36525_days_is_refused(periods):
    """Red: a schedule spanning 36 526 days or more is refused by the schedule validator."""
    _assert_refused_at(_params(periods), ("schedule",))


def test_span_of_36525_days_is_accepted():
    """Guard: exactly 36 525 days, in one period or two, is valid."""
    assert _SPAN_LIMIT_END == date(2100, 1, 1)
    FAScheduledInvestmentSchedule(**_params([_period(_SPAN_START, _SPAN_LIMIT_END)]))
    FAScheduledInvestmentSchedule(**_params([_period(_SPAN_START, date(2049, 12, 31)), _period(date(2050, 1, 1), _SPAN_LIMIT_END)]))


# ============================================================================
# At most 1 200 periods
# ============================================================================


def test_1201_periods_are_refused():
    """Red: 1 201 contiguous one-day periods (a span of 1 200 days) are refused for their number."""
    _assert_refused_at(_params(_one_day_periods(MAX_PERIODS + 1)), ("schedule",))


def test_1200_periods_are_accepted():
    """Guard: 1 200 periods is valid."""
    assert len(FAScheduledInvestmentSchedule(**_params(_one_day_periods(MAX_PERIODS))).schedule) == MAX_PERIODS


# ============================================================================
# Grace period: at most 36 525 days
# ============================================================================


def test_grace_of_36526_days_is_refused():
    """Red: a grace period of 36 526 days is refused, alone and inside a schedule."""
    with pytest.raises(ValidationError) as excinfo:
        FALateInterestConfig(annual_rate=Decimal("0.12"), grace_period_days=MAX_GRACE_DAYS + 1)
    assert {tuple(error["loc"]) for error in excinfo.value.errors()} == {("grace_period_days",)}
    _assert_refused_at(_params([_period(date(2020, 1, 1), date(2024, 12, 31))], grace_days=MAX_GRACE_DAYS + 1), ("late_interest", "grace_period_days"))


def test_grace_of_36525_days_is_accepted():
    """Guard: a grace period of exactly 36 525 days is valid."""
    assert FALateInterestConfig(annual_rate=Decimal("0.12"), grace_period_days=MAX_GRACE_DAYS).grace_period_days == MAX_GRACE_DAYS
    schedule = FAScheduledInvestmentSchedule(**_params([_period(date(2020, 1, 1), date(2024, 12, 31))], grace_days=MAX_GRACE_DAYS))
    assert schedule.late_interest.grace_period_days == MAX_GRACE_DAYS


# ============================================================================
# At most 10 000 manual events (MF-SI2)
# ============================================================================

# 2020-2049 MONTHLY: thirty years hold every event date below (10 001 days from 2020-01-01 end on 2047-05-19), so the
# schedule itself is valid and the only rule the events can break is their number.
_EVENTS_SCHEDULE = [_period(date(2020, 1, 1), date(2049, 12, 31))]
_TOO_MANY_EVENTS_PARAMS = _params(_EVENTS_SCHEDULE, events=_daily_interest_events(MAX_EVENTS + 1))


def test_10001_events_are_refused():
    """Red: 10 001 valid daily INTEREST events are refused for their number: a ``too_long`` error at ``asset_events``,
    the list itself, not one of its items (before: accepted)."""
    _assert_refused_at(_TOO_MANY_EVENTS_PARAMS, ("asset_events",), "too_long")


def test_10000_events_are_accepted():
    """Guard: 10 000 events is valid, and every one of them is kept."""
    schedule = FAScheduledInvestmentSchedule(**_params(_EVENTS_SCHEDULE, events=_daily_interest_events(MAX_EVENTS)))
    assert len(schedule.asset_events) == MAX_EVENTS
    assert (schedule.asset_events[0].date, schedule.asset_events[-1].date) == (date(2020, 1, 1), date(2020, 1, 1) + timedelta(days=MAX_EVENTS - 1))


# ============================================================================
# The report's schedule, and the provider's door
# ============================================================================

_REPORT_PARAMS = _params([{"start_date": "0001-01-01", "end_date": "9999-12-31", "annual_rate": "0.05", "maturation_frequency": "DAILY"}])


def test_report_schedule_year_1_to_9999_daily_is_refused():
    """Red: the security review's input, one DAILY period from 0001-01-01 to 9999-12-31, does not validate."""
    _assert_refused_at(_REPORT_PARAMS, ("schedule", 0, "start_date"))
    _assert_refused_at(_REPORT_PARAMS, ("schedule", 0, "end_date"))


@pytest.mark.parametrize(
    "params",
    [
        pytest.param(_REPORT_PARAMS, id="report-year-1-to-9999-daily"),
        pytest.param(_params([_period(MIN_DATE, date(2010, 1, 1))]), id="span-over-100-years"),
        pytest.param(_params(_one_day_periods(MAX_PERIODS + 1)), id="1201-periods"),
        pytest.param(_params([_period(date(2020, 1, 1), date(2024, 12, 31))], grace_days=MAX_GRACE_DAYS + 1), id="grace-36526"),
        pytest.param(_TOO_MANY_EVENTS_PARAMS, id="10001-events"),
    ],
)
def test_provider_validate_params_refuses_with_invalid_params(params):
    """Red: ``validate_params`` — the probe's first step — raises ``AssetSourceError`` ``INVALID_PARAMS`` from the
    schema's ``ValidationError``, before anything is computed."""
    with pytest.raises(AssetSourceError) as excinfo:
        ScheduledInvestmentProvider().validate_params(params)
    assert excinfo.value.error_code == "INVALID_PARAMS"
    assert isinstance(excinfo.value.__cause__, ValidationError)


def test_ordinary_schedule_2020_2030_monthly_is_accepted():
    """Guard: an ordinary schedule, 2020-2030 MONTHLY in two periods with 30 days of grace, validates in the schema and
    through the provider."""
    params = _params([_period(date(2020, 1, 1), date(2024, 12, 31)), _period(date(2025, 1, 1), date(2030, 12, 31))], grace_days=30)
    schedule = FAScheduledInvestmentSchedule(**params)
    assert [(p.start_date, p.end_date) for p in schedule.schedule] == [(date(2020, 1, 1), date(2024, 12, 31)), (date(2025, 1, 1), date(2030, 12, 31))]
    assert ScheduledInvestmentProvider().validate_params(params) == schedule
