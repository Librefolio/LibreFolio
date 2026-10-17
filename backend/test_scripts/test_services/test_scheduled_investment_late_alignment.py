"""
The Scheduled Investment late interest, read three ways on one day — J's review note on R13-SEC7-2 (workstream MF).

After maturity a COMPOUND late-interest value is read in three places:
    - ``get_current_value`` on day D: ``_compute_late_interest_value(D)``, the closed form from maturity
      (``V_maturity · compound_growth``);
    - the history's close on D (``get_history_value``, through ``_late_interest_values``);
    - the late ``MATURITY_SETTLEMENT`` of a ``generate_interest`` late interest, on the last late date.

Before: the history grew COMPOUND over the late grid, one date to the next (``value *= growth(previous, d)``), each
product rounded: the close on D differed from the current value read on D in its last digits, and the settlement (the
last close) from the closed form of its own day. A sync stores the history, the current value overwrites today's point:
the same day had two values depending on which path wrote it.

Now: every late date is the closed form of that date, in constant time (``compound_growth``, memoized), so the three
read the same digits, compared with ``str`` (digits and exponent), whatever window the history is read in.

Sections:
    A. Current value = history close on D (Red): 4 day counts × DAILY / MONTHLY late frequency × 3 windows — ending on
       D (a first sync), resuming 3 days before D (a later sync), read 75 days after D (D inside the window).
    B. Settlement = last close = ``_compute_late_interest_value`` on its day = current value on that day (Red), 4 day
       counts × DAILY / MONTHLY.

The day is frozen by replacing ``date_type`` in the plugin module (the name ``get_current_value`` reads ``today()``
through) for the length of one ``with`` block, and put back in its ``finally``. Every test deletes the ``_CACHE`` entry of
its schedule before (cold) and after (no leftovers).

Pure: no database, no server, no network.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.db.models import IdentifierType
from backend.app.schemas.assets.scheduled_investment import (
    DayCountConvention,
    FAInterestRatePeriod,
    FALateInterestConfig,
    FAScheduledInvestmentSchedule,
    InterestType,
    MaturationFrequency,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAHistoricalData
from backend.app.services.asset_source_providers.scheduled_investment import plugin as si_plugin
from backend.app.services.asset_source_providers.scheduled_investment.plugin import (
    _CACHE,
    ScheduledInvestmentProvider,
    _cache_key,
    _compute_late_interest_value,
    _generate_schedule_values,
)
from backend.app.services.assets.base import AssetSourceError

IDENTIFIER = "mf-late-alignment"
FIRST_START = date(2024, 1, 10)
MATURITY = date(2024, 9, 30)
GRACE_DAYS = 20  # grace ends on 2024-10-20: D is read past it, so both rates are in its growth
# The day the values are read on: 13 months after maturity, past a year end out of a leap year (two ACT/ACT fractions),
# a 28-day February (a 30/360 step of 3 days) and seven 31sts (30/360 steps of 0). A MONTHLY late grid starts on
# maturity + 1 (2024-10-01), so D, a 1st, is on it as well as on the DAILY one.
DAY = date(2025, 11, 1)

CONVENTIONS = list(DayCountConvention)
LATE_FREQUENCIES = [MaturationFrequency.DAILY, MaturationFrequency.MONTHLY]

# The windows of section A, as (start, end) around D.
_WINDOWS = {
    "ends-on-the-day": (FIRST_START, DAY),
    "resumes-3-days-before": (DAY - timedelta(days=3), DAY),
    "read-75-days-later": (FIRST_START, DAY + timedelta(days=75)),
}


def _schedule(day_count: DayCountConvention, late_frequency: MaturationFrequency, *, settle: bool) -> FAScheduledInvestmentSchedule:
    """One COMPOUND MONTHLY period, then COMPOUND late interest at another rate after 20 days of grace."""
    return FAScheduledInvestmentSchedule(
        initial_value=Currency(code="EUR", amount=Decimal("8000")),
        interest_type=InterestType.COMPOUND,
        day_count=day_count,
        schedule=[FAInterestRatePeriod(start_date=FIRST_START, end_date=MATURITY, annual_rate=Decimal("0.055"), maturation_frequency=MaturationFrequency.MONTHLY)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.13"), grace_period_days=GRACE_DAYS, interest_type=InterestType.COMPOUND, maturation_frequency=late_frequency, generate_interest=settle),
    )


@contextmanager
def _own_cache_entry(schedule: FAScheduledInvestmentSchedule) -> Iterator[None]:
    """The schedule's ``_CACHE`` entry, absent when the block starts and deleted when it ends."""
    key = _cache_key(schedule)
    _CACHE.delete(key)
    try:
        yield
    finally:
        _CACHE.delete(key)


@contextmanager
def _today_is(day: date) -> Iterator[None]:
    """``date_type.today()`` in the plugin module is ``day`` for the length of the block."""

    class _FrozenDate(date):
        @classmethod
        def today(cls) -> date:
            return day

    real = si_plugin.date_type
    si_plugin.date_type = _FrozenDate
    try:
        yield
    finally:
        si_plugin.date_type = real


async def _read(schedule: FAScheduledInvestmentSchedule, start: date, end: date) -> tuple[Decimal, FAHistoricalData]:
    """The current value on D and the history from ``start`` to ``end``; an ``AssetSourceError`` fails the test."""
    provider, params = ScheduledInvestmentProvider(), schedule.model_dump(mode="json")
    try:
        with _today_is(DAY):
            current = await provider.get_current_value(IDENTIFIER, IdentifierType.OTHER, params)
        history = await provider.get_history_value(IDENTIFIER, IdentifierType.OTHER, params, start, end)
    except AssetSourceError as exc:
        pytest.fail(f"AssetSourceError({exc.error_code}): {exc.message}")
    assert current.as_of_date == DAY, f"the current value is as of {current.as_of_date}, not the frozen day {DAY}"
    return current.value, history


def _close_on(history: FAHistoricalData, day: date) -> Decimal:
    closes = [point.close for point in history.prices if point.date == day]
    assert len(closes) == 1, f"{len(closes)} price points on {day}, expected one"
    return closes[0]


def _closed_form_on(schedule: FAScheduledInvestmentSchedule, day: date) -> Decimal:
    """``_compute_late_interest_value`` on ``day``, from the value the schedule ends on."""
    values, _auto_events = _generate_schedule_values(schedule)
    maturity = max(values)
    assert maturity == MATURITY
    return _compute_late_interest_value(schedule, day, values[maturity], maturity)


# ============================================================================
# A. The current value on D is the history's close on D
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("window", list(_WINDOWS), ids=str)
@pytest.mark.parametrize("late_frequency", LATE_FREQUENCIES, ids=lambda f: f.value.lower())
@pytest.mark.parametrize("day_count", CONVENTIONS, ids=lambda c: c.name)
async def test_current_value_equals_history_close_on_the_day(day_count, late_frequency, window):
    """Red before the note: the history multiplied the late grid date by date, so its close on D had other last digits
    than the current value read on D. Now both are the closed form of D: the same ``str``, in every window."""
    schedule = _schedule(day_count, late_frequency, settle=False)
    start, end = _WINDOWS[window]
    with _own_cache_entry(schedule):
        current, history = await _read(schedule, start, end)
        close = _close_on(history, DAY)
        closed_form = _closed_form_on(schedule, DAY)
        maturity_value = _generate_schedule_values(schedule)[0][MATURITY]

    # Not vacuous: D is after the grace period, so the value grew at both rates, above the maturity value.
    assert DAY > MATURITY + timedelta(days=GRACE_DAYS)
    assert closed_form > maturity_value
    assert str(current) == str(close), f"{day_count} {late_frequency} [{start}, {end}]: current value on {DAY} {current}, history close {close}"
    assert str(close) == str(closed_form), f"history close {close}, _compute_late_interest_value {closed_form}"


# ============================================================================
# B. The late settlement is the last close and the closed form of its day
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("late_frequency", LATE_FREQUENCIES, ids=lambda f: f.value.lower())
@pytest.mark.parametrize("day_count", CONVENTIONS, ids=lambda c: c.name)
async def test_late_settlement_equals_last_close_and_closed_form(day_count, late_frequency):
    """Red before the note: the settlement was the last close, grown over the grid, not the closed form of its day.
    Now the late ``MATURITY_SETTLEMENT`` on D, the last close, ``_compute_late_interest_value`` on D and the current
    value on D are one ``str``."""
    schedule = _schedule(day_count, late_frequency, settle=True)
    with _own_cache_entry(schedule):
        current, history = await _read(schedule, FIRST_START, DAY)
        closed_form = _closed_form_on(schedule, DAY)

    settlements = [event for event in history.events if event.type == "MATURITY_SETTLEMENT"]
    assert [event.date for event in settlements] == [DAY], f"settlements on {[event.date for event in settlements]}, expected one on {DAY}"
    last = history.prices[-1]
    assert last.date == DAY, f"the last close is on {last.date}, expected {DAY}"
    texts = {
        "settlement": str(settlements[0].value.amount),
        "last close": str(last.close),
        "_compute_late_interest_value": str(closed_form),
        "current value": str(current),
    }
    assert len(set(texts.values())) == 1, f"{day_count} {late_frequency}: {texts}"
