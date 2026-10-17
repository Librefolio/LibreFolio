"""
The cost of the Scheduled Investment provider — R13-SEC7-2 (MEDIUM, a DoS), night decision N73, workstream MF.

Before: COMPOUND late interest (``_compute_late_interest_value``) walked one day at a time from maturity, and the late
history called it once per late maturation date, so a DAILY late history of n days cost ~n²/2 day steps; a schedule's
values were cached whatever their size. With the schema unbounded, ``POST /assets/provider/probe`` (a dry run open to any
user) could keep a thread busy past its 15 s timeout and cache ~0.7 GB per schedule.

Now:
    - COMPOUND late interest is the closed form ``V · compound_growth(...)``: grace days at the last period's rate, the
      days after at the late rate (``_late_compound_growth``). ``compound_growth`` is O(1) in its span and memoized:
      ACT/ACT one power for the whole common years and one for the leap years, 30/360 step counts as differences of
      prefixes (``_thirty_360_steps_up_to``, at most 12 months per date);
    - the late history (``_late_interest_values``) values every late date by its closed form,
      ``_compute_late_interest_value``, in constant time per date; SIMPLE and COMPOUND alike value only the emitted
      dates and the last late date (the settlement's);
    - late interest is emitted up to 2200-12-31 (``SCHEDULE_MAX_DATE``) at most, and a schedule with late interest whose
      maturity is that day emits nothing after it (the flat line of a schedule without late interest is not drawn);
    - ``_generate_schedule_values`` does not store a result of more than 3 660 points (``_CACHE_MAX_POINTS``) in
      ``_CACHE``;
    - the ACT/ACT fraction across years is still the year-by-year sum, with the same additions as before: the whole
      years before the end's are a memoized prefix per (start, end year) (``interest._act_act_years_before``), then the
      last year's days are added; so SIMPLE late interest, closed form per date from maturity, no longer looks up every
      year since maturity on every date;
    - a late date's value is the closed form of that date, so it does not depend on the window it is read in, and the
      history's close, the current value (``get_current_value``) and the late ``MATURITY_SETTLEMENT`` (the last late
      price itself) read the same digits for one day (J's review note: ``test_scheduled_investment_late_alignment.py``).

Sections:
    C. Parity (Guard: green before and after). The closed form equals the old day-by-day loop, ported here as the oracle
       (``_day_by_day_late_compound``, the body ``git show`` gives for the COMPOUND branch before the fix), within a
       relative 1e-22: it is more exact than the loop, not the same digits. The late history equals
       ``_compute_late_interest_value`` called on each date, within 1e-22 (now digit for digit: it is that call).
    D. Cost (Red). Deterministic, never wall-clock: the calls of ``calculate_day_count_fraction`` the plugin makes, counted
       through the name the plugin reads. Before: ~n²/2 for the late history; the counter stops the walk at the budget, so
       the red arrives in a fraction of a second instead of after ~3·10⁸ calls. For SIMPLE ACT/ACT, the calls of
       ``calendar.isleap`` the ``interest`` module makes, through the ``calendar`` name it reads, from a cleared memo:
       before, one per year between maturity and each date.
    E. Cache cap (Red for the schedule over the cap).
    F. Horizon (Red): no price point nor event after 2200-12-31, also when maturity is that day.
    G. Settlement (Guard: green before the fix, which computed both from maturity day by day, and on every history since:
       the one-pass history that first replaced it, whose first version settled on a closed form that differed from the
       last price in the last digits, and the closed form per date that replaced the one pass).
    H. Window independence (Guard: green before the fix, which valued each date from maturity, and on every history
       since: a first version of the one pass grew from the first date of the window and so gave a date other last
       digits in another window; the closed form per date reads no window at all).

``get_history_value`` is given the schedule's first start, not ``"min"``: before MF-SI1 ``"min"`` raised
``CALCULATION_ERROR`` (the provider compared the literal with dates), a defect apart from R13-SEC7-2. For these schedules,
which have no manual event before their start, ``"min"`` now resolves to that same first start
(``test_scheduled_investment_min_start.py``).

Every test that runs the schedule deletes its ``_CACHE`` entry before (cold) and after (no leftovers).

Pure: no database, no server, no network. ``plugin.calculate_day_count_fraction`` and ``interest.calendar`` are replaced
for the length of one ``with`` block and put back in its ``finally``.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal, localcontext

import pytest
from dateutil.relativedelta import relativedelta

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
from backend.app.services.asset_source_providers.scheduled_investment import plugin as si_plugin
from backend.app.services.asset_source_providers.scheduled_investment.plugin import (
    _CACHE,
    ScheduledInvestmentProvider,
    _cache_key,
    _compute_late_interest_value,
    _generate_schedule_values,
)
from backend.app.services.assets.base import AssetSourceError
from backend.app.services.financial_math import interest as fm_interest
from backend.app.services.financial_math.interest import calculate_day_count_fraction, calculate_simple_interest

PARITY_TOLERANCE = Decimal("1e-22")
# The N73 horizon, written out: late interest is never valued after it.
HORIZON = date(2200, 12, 31)
CONVENTIONS = list(DayCountConvention)


def _relative_gap(actual: Decimal, expected: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 60
        return abs(actual - expected) / abs(expected)


def _principal() -> Currency:
    return Currency(code="EUR", amount=Decimal("10000"))


def _period(start: date, end: date, rate: str, frequency: MaturationFrequency) -> FAInterestRatePeriod:
    return FAInterestRatePeriod(start_date=start, end_date=end, annual_rate=Decimal(rate), maturation_frequency=frequency)


@contextmanager
def _own_cache_entry(schedule: FAScheduledInvestmentSchedule) -> Iterator[str]:
    """The schedule's ``_CACHE`` key, absent when the block starts and deleted when it ends."""
    key = _cache_key(schedule)
    _CACHE.delete(key)
    try:
        yield key
    finally:
        _CACHE.delete(key)


async def _history(schedule: FAScheduledInvestmentSchedule, end: date, start: date | None = None):
    """The provider's history of ``schedule`` from ``start`` — by default its first start, what ``"min"`` means for
    a schedule without a manual event before it — to ``end``."""
    params = schedule.model_dump(mode="json")
    return await ScheduledInvestmentProvider().get_history_value("r13-sec7-2", IdentifierType.OTHER, params, start or schedule.schedule[0].start_date, end)


def _every_day(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


# ============================================================================
# C. Parity: the closed form against the old day-by-day loop
# ============================================================================


def _day_by_day_late_compound(schedule: FAScheduledInvestmentSchedule, target_date: date, last_scheduled_value: Decimal, maturity_date: date) -> Decimal:
    """The oracle: the COMPOUND branch of ``_compute_late_interest_value`` before R13-SEC7-2, verbatim but for the names.

    Each day d in (maturity, target] adds V · r · f(d − 1, d), r the last period's rate up to the end of the grace period
    and the late rate after it.
    """
    li = schedule.late_interest
    grace_end = maturity_date + timedelta(days=li.grace_period_days)
    last_rate = schedule.schedule[-1].annual_rate
    value = last_scheduled_value
    current = maturity_date + timedelta(days=1)
    while current <= target_date:
        rate = last_rate if current <= grace_end else li.annual_rate
        frac = calculate_day_count_fraction(start_date=current - timedelta(days=1), end_date=current, convention=schedule.day_count)
        value += calculate_simple_interest(principal=value, annual_rate=rate, time_fraction=frac)
        current += timedelta(days=1)
    return value


_PARITY_MATURITY = date(2023, 12, 15)
_PARITY_LAST_VALUE = Decimal("10456.78901")


def _parity_schedule(day_count: DayCountConvention, grace_days: int) -> FAScheduledInvestmentSchedule:
    """Two periods at different rates, so "the last period's rate" is told apart from the first; late at 14 % COMPOUND."""
    return FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=InterestType.COMPOUND,
        day_count=day_count,
        schedule=[
            _period(date(2023, 3, 1), date(2023, 8, 31), "0.03", MaturationFrequency.QUARTERLY),
            _period(date(2023, 9, 1), _PARITY_MATURITY, "0.055", MaturationFrequency.MONTHLY),
        ],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.14"), grace_period_days=grace_days, interest_type=InterestType.COMPOUND),
    )


def _parity_targets(grace_days: int) -> list[date]:
    """Maturity itself, the day after, the grace period's last day and its neighbours, +40 days after it, the year ends
    and 29 February of 2024, and three years after maturity."""
    grace_end = _PARITY_MATURITY + timedelta(days=grace_days)
    candidates = {
        _PARITY_MATURITY,
        _PARITY_MATURITY + timedelta(days=1),
        grace_end - timedelta(days=1),
        grace_end,
        grace_end + timedelta(days=1),
        grace_end + timedelta(days=40),
        date(2023, 12, 31),
        date(2024, 1, 1),
        date(2024, 2, 29),
        date(2024, 3, 1),
        date(2024, 3, 31),
        date(2024, 12, 31),
        date(2025, 1, 1),
        _PARITY_MATURITY + timedelta(days=1_100),
    }
    return sorted(day for day in candidates if day >= _PARITY_MATURITY)


@pytest.mark.parametrize("grace_days", [0, 15, 400], ids=lambda g: f"grace-{g}")
@pytest.mark.parametrize("day_count", CONVENTIONS, ids=lambda c: c.name)
def test_late_compound_equals_the_day_by_day_walk(day_count, grace_days):
    """Guard: ``_compute_late_interest_value`` COMPOUND equals the old loop within 1e-22 — inside the grace period, on
    its last day, after it, and across a year end. With 400 days of grace, 2024 and its 29 February are all grace."""
    schedule = _parity_schedule(day_count, grace_days)
    gaps = []
    for target in _parity_targets(grace_days):
        actual = _compute_late_interest_value(schedule, target, _PARITY_LAST_VALUE, _PARITY_MATURITY)
        expected = _day_by_day_late_compound(schedule, target, _PARITY_LAST_VALUE, _PARITY_MATURITY)
        gap = _relative_gap(actual, expected)
        if gap > PARITY_TOLERANCE:
            gaps.append(f"{target}: closed form {actual}, day by day {expected}, relative gap {gap:.3E}")
    assert not gaps, f"{day_count} grace {grace_days}:\n" + "\n".join(gaps)


_HISTORY_END = date(2024, 12, 31)


def _history_schedule(day_count: DayCountConvention, late_type: InterestType, late_frequency: MaturationFrequency) -> FAScheduledInvestmentSchedule:
    """2022 MONTHLY at 5 %, then two years of late interest at 11 % with 15 days of grace."""
    return FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=InterestType.COMPOUND,
        day_count=day_count,
        schedule=[_period(date(2022, 1, 1), date(2022, 12, 31), "0.05", MaturationFrequency.MONTHLY)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.11"), grace_period_days=15, interest_type=late_type, maturation_frequency=late_frequency),
    )


def _expected_late_dates(maturity: date, end: date, frequency: MaturationFrequency) -> set[date]:
    """The late maturation dates: from the day after maturity, one step of the frequency at a time, and the end."""
    first = maturity + timedelta(days=1)
    step = {MaturationFrequency.DAILY: relativedelta(days=1), MaturationFrequency.MONTHLY: relativedelta(months=1)}[frequency]
    dates, day = {end}, first
    while day <= end:
        dates.add(day)
        day += step
    return dates


@pytest.mark.parametrize(
    ("late_type", "late_frequency"),
    [
        pytest.param(InterestType.COMPOUND, MaturationFrequency.DAILY, id="compound-daily"),
        pytest.param(InterestType.COMPOUND, MaturationFrequency.MONTHLY, id="compound-monthly"),
        pytest.param(InterestType.SIMPLE, MaturationFrequency.DAILY, id="simple-daily"),
    ],
)
@pytest.mark.parametrize("day_count", CONVENTIONS, ids=lambda c: c.name)
@pytest.mark.asyncio
async def test_late_history_equals_the_value_on_each_date(day_count, late_type, late_frequency):
    """Guard: every late point of ``get_history_value`` is ``_compute_late_interest_value`` on its date, within 1e-22.

    Every late date is now the closed form of that date, SIMPLE and COMPOUND alike, so the two agree digit for digit
    (``test_scheduled_investment_late_alignment.py`` pins it by ``str``); the tolerance is the one-pass history's, kept.
    """
    schedule = _history_schedule(day_count, late_type, late_frequency)
    maturity = schedule.schedule[-1].end_date
    with _own_cache_entry(schedule):
        history = await _history(schedule, _HISTORY_END)
        values, _auto_events = _generate_schedule_values(schedule)
    late = {point.date: point.close for point in history.prices if point.date > maturity}
    assert set(late) == _expected_late_dates(maturity, _HISTORY_END, late_frequency)
    gaps = []
    for day, close in sorted(late.items()):
        expected = _compute_late_interest_value(schedule, day, values[maturity], maturity)
        gap = _relative_gap(close, expected)
        if gap > PARITY_TOLERANCE:
            gaps.append(f"{day}: history {close}, per date {expected}, relative gap {gap:.3E}")
    assert not gaps, f"{day_count} {late_type} {late_frequency}:\n" + "\n".join(gaps[:20])


# ============================================================================
# D. Cost: counted, not timed
# ============================================================================


class _DayCountBudgetExceeded(Exception):
    """Raised by the counter on the call past its budget: the walk stops there instead of running ~n²/2 steps."""


class _CountingDayCount:
    def __init__(self, real, budget: int):
        self.real = real
        self.budget = budget
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls > self.budget:
            raise _DayCountBudgetExceeded(f"calculate_day_count_fraction called more than {self.budget} times")
        return self.real(*args, **kwargs)


@contextmanager
def _counting_day_count(budget: int) -> Iterator[_CountingDayCount]:
    """Count the calls of ``calculate_day_count_fraction`` through the name the plugin reads, and put it back after."""
    counter = _CountingDayCount(si_plugin.calculate_day_count_fraction, budget)
    si_plugin.calculate_day_count_fraction = counter
    try:
        yield counter
    finally:
        si_plugin.calculate_day_count_fraction = counter.real


_COST_START = date(1949, 1, 1)
_COST_MATURITY = date(1950, 6, 30)
_COST_END = date(2020, 6, 30)  # 70 years after maturity: 25 568 DAILY late dates


def _cost_schedule() -> FAScheduledInvestmentSchedule:
    """Maturity in 1950, then COMPOUND late interest at 9 % with 30 days of grace, a maturation date every day."""
    return FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=InterestType.COMPOUND,
        schedule=[_period(_COST_START, _COST_MATURITY, "0.04", MaturationFrequency.MONTHLY)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.09"), grace_period_days=30, interest_type=InterestType.COMPOUND, maturation_frequency=MaturationFrequency.DAILY),
    )


@pytest.mark.asyncio
async def test_late_history_cost_is_linear_in_its_days():
    """Red: 70 years of DAILY COMPOUND late history cost at most one day-count call per day of the history (the
    scheduled walk's days plus the late days) plus a constant. Before: one walk from maturity per late date, ~n²/2 calls
    (~3.3·10⁸ here), stopped by the counter at the budget."""
    schedule = _cost_schedule()
    walk_days = (_COST_MATURITY - _COST_START).days + 1
    late_days = (_COST_END - _COST_MATURITY).days
    budget = walk_days + late_days + 64
    with _own_cache_entry(schedule), _counting_day_count(budget) as counter:
        try:
            history = await _history(schedule, _COST_END)
        except AssetSourceError as error:
            if isinstance(error.__cause__, _DayCountBudgetExceeded):
                pytest.fail(f"the late history called calculate_day_count_fraction more than {budget} times for {walk_days + late_days} days: not linear")
            raise
    late_points = [point for point in history.prices if point.date > _COST_MATURITY]
    assert len(late_points) == late_days, "every late day is emitted: the cost is not saved by skipping work"
    assert late_points[-1].date == _COST_END
    assert counter.calls <= budget


def test_late_value_on_a_far_date_is_not_a_day_walk():
    """Red: one COMPOUND late value 70 years after maturity (the current value of ``get_current_value``) costs a bounded
    number of day-count calls — at most a few per calendar year, never one per day (before: 25 568)."""
    schedule = _cost_schedule()
    budget = 4 * (_COST_END.year - _COST_MATURITY.year + 1)
    last_value = Decimal("10612.34")
    with _counting_day_count(budget) as counter:
        value = _compute_late_interest_value(schedule, _COST_END, last_value, _COST_MATURITY)
    assert counter.calls <= budget
    assert value > last_value


class _CountingCalendar:
    """The ``calendar`` module as the ``interest`` module reads it, with ``isleap`` counted and the rest passed through."""

    def __init__(self, real):
        self.real = real
        self.isleap_calls = 0

    def isleap(self, year: int) -> bool:
        self.isleap_calls += 1
        return self.real.isleap(year)

    def __getattr__(self, name: str):
        return getattr(self.real, name)


@contextmanager
def _counting_isleap() -> Iterator[_CountingCalendar]:
    """Count the calls of ``calendar.isleap`` through the ``calendar`` name the ``interest`` module reads."""
    counter = _CountingCalendar(fm_interest.calendar)
    fm_interest.calendar = counter
    try:
        yield counter
    finally:
        fm_interest.calendar = counter.real


_ACT_ACT_START = date(1900, 1, 1)
_ACT_ACT_MATURITY = date(1900, 1, 31)
_ACT_ACT_READ = (date(2024, 1, 1), date(2025, 12, 31))  # the last two years of the history: 731 DAILY late dates


@pytest.mark.asyncio
async def test_simple_act_act_late_history_cost_is_bounded_per_date():
    """Red: SIMPLE ACT/ACT late interest from a maturity in 1900, read over 2024-2025, a point a day. Each date is a
    closed form from maturity: two ACT/ACT fractions, the grace period (inside 1900) and the late span (across 124 to
    125 year ends). From a cleared memo: at most 4 ``calendar.isleap`` calls per date, plus the years since maturity
    once per end year (124 + 125), plus one per day of the scheduled walk. Before: the late span looked up every year
    since 1900 on every date, ~126 calls per date."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        day_count=DayCountConvention.ACT_ACT,
        schedule=[_period(_ACT_ACT_START, _ACT_ACT_MATURITY, "0.04", MaturationFrequency.MONTHLY)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.08"), grace_period_days=30, interest_type=InterestType.SIMPLE, maturation_frequency=MaturationFrequency.DAILY),
    )
    walk_days = (_ACT_ACT_MATURITY - _ACT_ACT_START).days + 1
    first, last = _ACT_ACT_READ
    years_once_per_end_year = sum(end_year - _ACT_ACT_MATURITY.year for end_year in range(first.year, last.year + 1))
    memo = getattr(fm_interest, "_act_act_years_before", None)  # the code before the fix has none
    if memo is not None:
        memo.cache_clear()
    with _own_cache_entry(schedule), _counting_isleap() as counter:
        history = await _history(schedule, last, start=first)
    dates = [point.date for point in history.prices]
    assert dates == _every_day(first, last), "the history emits the requested range, every day of it, and nothing else"
    budget = walk_days + 4 * len(dates) + years_once_per_end_year
    per_date = (counter.isleap_calls - walk_days) / len(dates)
    assert counter.isleap_calls <= budget, f"{counter.isleap_calls} calls of calendar.isleap for {len(dates)} late dates (~{per_date:.0f} per date), budget {budget}"


# ============================================================================
# E. Cache cap: a result of more than 3 660 points is not stored
# ============================================================================


def _daily_schedule(start: date, end: date) -> FAScheduledInvestmentSchedule:
    """A DAILY schedule (one maturation date a day) with a principal and a rate no other test uses: a key of its own."""
    return FAScheduledInvestmentSchedule(initial_value=Currency(code="EUR", amount=Decimal("13579.24")), schedule=[_period(start, end, "0.0333", MaturationFrequency.DAILY)])


def test_daily_schedule_of_eleven_years_is_computed_but_not_cached():
    """Red: 2010-2020 DAILY (4 018 points) is computed, the same on every call, and never stored in ``_CACHE``."""
    schedule = _daily_schedule(date(2010, 1, 1), date(2020, 12, 31))
    with _own_cache_entry(schedule) as key:
        values, _auto_events = _generate_schedule_values(schedule)
        assert len(values) == (date(2020, 12, 31) - date(2010, 1, 1)).days + 1
        _cached, hit = _CACHE.get(key)
        assert not hit, f"a schedule of {len(values)} points was stored in _CACHE"
        again, _auto_events = _generate_schedule_values(schedule)
        assert again == values


@pytest.mark.parametrize(("points", "stored"), [pytest.param(3_660, True, id="3660-stored"), pytest.param(3_661, False, id="3661-not-stored")])
def test_cache_cap_is_3660_points(points, stored):
    """Red for 3 661 (before: stored); Guard for 3 660, the largest result still stored."""
    start = date(2001, 1, 1)
    schedule = _daily_schedule(start, start + timedelta(days=points - 1))
    with _own_cache_entry(schedule) as key:
        values, _auto_events = _generate_schedule_values(schedule)
        assert len(values) == points
        _cached, hit = _CACHE.get(key)
        assert hit is stored, f"{points} points: stored {hit}, expected {stored}"


def test_monthly_schedule_of_five_years_is_cached():
    """Guard: 2018-2022 MONTHLY (61 points) is stored, and the stored result is the one returned."""
    schedule = FAScheduledInvestmentSchedule(initial_value=Currency(code="EUR", amount=Decimal("13579.24")), schedule=[_period(date(2018, 1, 1), date(2022, 12, 31), "0.0333", MaturationFrequency.MONTHLY)])
    with _own_cache_entry(schedule) as key:
        values, _auto_events = _generate_schedule_values(schedule)
        cached, hit = _CACHE.get(key)
        assert hit, "a five-year MONTHLY schedule was not stored in _CACHE"
        assert cached[0] == values


# ============================================================================
# F. Horizon: late interest stops at 2200-12-31
# ============================================================================


@pytest.mark.parametrize("generate_interest", [False, True], ids=lambda g: "coupons" if g else "no-coupons")
@pytest.mark.parametrize("late_type", [InterestType.COMPOUND, InterestType.SIMPLE], ids=lambda t: t.value.lower())
class TestLateInterestHorizon:
    """No price point nor event after 2200-12-31 (``SCHEDULE_MAX_DATE``), whatever the end the history is asked to."""

    @staticmethod
    def _schedule(first: date, maturity: date, late_type: InterestType, generate_interest: bool) -> FAScheduledInvestmentSchedule:
        return FAScheduledInvestmentSchedule(
            initial_value=_principal(),
            schedule=[_period(first, maturity, "0.04", MaturationFrequency.MONTHLY)],
            late_interest=FALateInterestConfig(annual_rate=Decimal("0.08"), grace_period_days=30, interest_type=late_type, maturation_frequency=MaturationFrequency.MONTHLY, generate_interest=generate_interest),
        )

    @pytest.mark.asyncio
    async def test_late_interest_stops_at_the_horizon(self, late_type, generate_interest):
        """Red: maturity in 2195, history asked to 2210-06-30. Late interest runs to 2200-12-31, its last point, and no
        price nor event lies after it. Before: points every month to 2210-06-30."""
        schedule = self._schedule(date(2190, 1, 1), date(2195, 6, 30), late_type, generate_interest)
        with _own_cache_entry(schedule):
            history = await _history(schedule, date(2210, 6, 30))
        price_dates = [point.date for point in history.prices]
        assert max(price_dates) == HORIZON, f"late interest should run to {HORIZON}, last point {max(price_dates)}"
        assert [day for day in price_dates if day > HORIZON] == []
        assert [(event.date, event.type) for event in history.events if event.date > HORIZON] == []

    @pytest.mark.asyncio
    async def test_maturity_on_the_horizon_emits_nothing_after_it(self, late_type, generate_interest):
        """Red: a schedule with late interest maturing on 2200-12-31 itself, history asked to 2210-06-30: its last point
        is the maturity, and nothing lies after it. Before the fix: late points every month to 2210-06-30; with only the
        late clamp, the flat line of a schedule without late interest, a point on 2210-06-30."""
        schedule = self._schedule(date(2199, 1, 1), HORIZON, late_type, generate_interest)
        with _own_cache_entry(schedule):
            history = await _history(schedule, date(2210, 6, 30))
            values, _auto_events = _generate_schedule_values(schedule)
        last = max(history.prices, key=lambda point: point.date)
        assert (last.date, last.close) == (HORIZON, values[HORIZON]), f"last point {last.date} {last.close}"
        assert [point.date for point in history.prices if point.date > HORIZON] == []
        assert [(event.date, event.type) for event in history.events if event.date > HORIZON] == []


# ============================================================================
# G. Settlement: the late MATURITY_SETTLEMENT is the last late price
# ============================================================================

_SETTLEMENT_MATURITY = date(2020, 12, 31)
_SETTLEMENT_END = date(2025, 12, 31)


@pytest.mark.parametrize(
    "read_from",
    [pytest.param(None, id="from-the-first-start"), pytest.param(date(2024, 7, 1), id="from-mid-late")],
)
@pytest.mark.parametrize("late_frequency", [MaturationFrequency.DAILY, MaturationFrequency.MONTHLY], ids=lambda f: f.value.lower())
@pytest.mark.parametrize("day_count", CONVENTIONS, ids=lambda c: c.name)
@pytest.mark.asyncio
async def test_late_settlement_is_the_last_late_price(day_count, late_frequency, read_from):
    """Guard: with ``generate_interest`` on COMPOUND late interest, the one ``MATURITY_SETTLEMENT`` is dated on the last
    late price and is worth its close exactly, and the INTEREST of that day is the close less the principal — whether
    the history is read from the first start or from the middle of the late period."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=InterestType.COMPOUND,
        day_count=day_count,
        schedule=[_period(date(2020, 1, 1), _SETTLEMENT_MATURITY, "0.04", MaturationFrequency.MONTHLY)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.08"), grace_period_days=10, interest_type=InterestType.COMPOUND, maturation_frequency=late_frequency, generate_interest=True),
    )
    with _own_cache_entry(schedule):
        history = await _history(schedule, _SETTLEMENT_END, start=read_from)
    last = max(history.prices, key=lambda point: point.date)
    settlements = [event for event in history.events if event.type == "MATURITY_SETTLEMENT"]
    assert [event.date for event in settlements] == [_SETTLEMENT_END] == [last.date]
    assert settlements[0].value.amount == last.close, f"settlement {settlements[0].value.amount}, last price {last.close}"
    interest_on_last = [event.value.amount for event in history.events if event.type == "INTEREST" and event.date == last.date]
    assert interest_on_last == [last.close - schedule.initial_value.amount]


# ============================================================================
# H. Window independence: a late COMPOUND value is the date's, not the read's
# ============================================================================

_WINDOW_MATURITY = date(2020, 12, 31)
# Three reads of one schedule; every one covers the late dates of 2024-01-01 .. 2024-06-30.
_WINDOWS = {
    "from-the-first-start": (None, date(2025, 12, 31)),
    "a-year-from-mid-2023": (date(2023, 3, 15), date(2024, 6, 30)),
    "from-2024": (date(2024, 1, 1), date(2025, 9, 30)),
}
_COMMON = (date(2024, 1, 1), date(2024, 6, 30))


@pytest.mark.parametrize("late_frequency", [MaturationFrequency.DAILY, MaturationFrequency.MONTHLY], ids=lambda f: f.value.lower())
@pytest.mark.parametrize("day_count", CONVENTIONS, ids=lambda c: c.name)
@pytest.mark.asyncio
async def test_late_compound_close_does_not_depend_on_the_read_window(day_count, late_frequency):
    """Guard: one COMPOUND schedule read in three windows that start on different dates. On every late date the three
    share, the close (and the late INTEREST of that day) is the same, ``str`` for ``str``."""
    schedule = FAScheduledInvestmentSchedule(
        initial_value=_principal(),
        interest_type=InterestType.COMPOUND,
        day_count=day_count,
        schedule=[_period(date(2020, 1, 1), _WINDOW_MATURITY, "0.04", MaturationFrequency.MONTHLY)],
        late_interest=FALateInterestConfig(annual_rate=Decimal("0.08"), grace_period_days=10, interest_type=InterestType.COMPOUND, maturation_frequency=late_frequency, generate_interest=True),
    )
    reads: dict[str, dict[date, tuple[str, str]]] = {}
    with _own_cache_entry(schedule):
        for name, (start, end) in _WINDOWS.items():
            history = await _history(schedule, end, start=start)
            interest = {event.date: str(event.value.amount) for event in history.events if event.type == "INTEREST" and event.date > _WINDOW_MATURITY}
            reads[name] = {point.date: (str(point.close), interest.get(point.date)) for point in history.prices if point.date > _WINDOW_MATURITY}
    common = sorted(set.intersection(*(set(read) for read in reads.values())))
    expected_common = [day for day in common if _COMMON[0] <= day <= _COMMON[1]]
    assert expected_common, "the windows share no late date"
    assert {day for day in _every_day(*_COMMON) if day in reads["from-the-first-start"]} <= set(common)
    differing = [f"{day}: " + ", ".join(f"{name} {read[day]}" for name, read in reads.items()) for day in common if len({read[day] for read in reads.values()}) > 1]
    assert not differing, f"{len(differing)} of {len(common)} common late dates differ by window:\n" + "\n".join(differing[:10])
