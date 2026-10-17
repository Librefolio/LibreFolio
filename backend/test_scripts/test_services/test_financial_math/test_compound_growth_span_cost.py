"""
``compound_growth`` in constant time over its span, and its memo — J's review note on R13-SEC7-2 (workstream MF).

``compound_growth(start, end, r, convention)`` is Π over d in (start, end] of (1 + r · f(d − 1, d)), one power per run
of equal day fractions (``test_compound_growth.py`` pins it against the day-by-day product).

Before: ACT/ACT raised one power per calendar year of the span, and 30/360 counted its steps of 0, 1, 2 and 3 days
month by month (``_thirty_360_daily_steps``): a 250-year late-interest span cost ~250 ``calendar.isleap`` calls, or
~6 000 ``calendar.monthrange`` calls, for every date of a late history.

Now:
    - ACT/ACT: the first year's days, then the whole years in one power for the common years and one for the leap years
      (counted in closed form, ``_leap_years_before``), then the last year's days;
    - 30/360: the step counts of (start, end] are the counts up to end minus the counts up to start
      (``_thirty_360_steps_up_to``: closed form over the whole years, month by month in the last one, so at most 12
      months per date);
    - the result is memoized (``_compound_growth``), keyed on the rate as written and on the caller's precision and
      rounding.

Sections:
    A. Cost (Red for the long span): the ``calendar.isleap`` and ``calendar.monthrange`` calls the ``interest`` module
       makes, through the ``calendar`` name it reads, from a cleared memo, for one call over 1 year and over 250 years:
       the same count, within a budget that does not grow with the span.
    B. Parity (Guard: green before and after). 30/360: the step counts are the old month loop's (``_month_loop_steps``,
       ported from the code before the note), exactly, over random spans and month-end edges. ACT/ACT: the old per-year
       product (``_per_year_act_act_growth``, ported) within a relative 1e-26 for spans of at most 2 whole years; for
       long spans, within 1e-22 of the same product in a 60-digit context.
    C. The memo key (Guard: green before the memo, which had none): ``Decimal("0.000")`` and ``Decimal("0")`` are equal
       Decimals with other digits, and keep each its own ``str`` in either order; a call in a 60-digit context leaves the
       default context's result as it was, and the reverse.

Every cost or memo test clears the memo first (where the module has one: the code before the note has none), and every
call runs in the default context unless the test says otherwise.

Pure: no database, no server, no network. ``interest.calendar`` is replaced for the length of one ``with`` block and put
back in its ``finally``.
"""

import calendar
import random
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal, localcontext

import pytest

from backend.app.schemas.assets.scheduled_investment import SCHEDULE_MAX_DATE, SCHEDULE_MIN_DATE, DayCountConvention
from backend.app.services.financial_math import interest as fm_interest
from backend.app.services.financial_math.interest import compound_growth

ORACLE_PRECISION = 60
SHORT_SPAN_TOLERANCE = Decimal("1e-26")
LONG_SPAN_TOLERANCE = Decimal("1e-22")
RATES = (Decimal("0.0475"), Decimal("0.12"), Decimal("0.0733333"))


def _clear_memo() -> None:
    """Empty the memo of ``compound_growth``, where the module has one (the code before the note has none)."""
    memo = getattr(fm_interest, "_compound_growth", None)
    if memo is not None:
        memo.cache_clear()


def _relative_gap(actual: Decimal, expected: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = ORACLE_PRECISION
        return abs(actual - expected) / abs(expected)


# ============================================================================
# A. Cost: one call costs the same over 1 year and over 250 years
# ============================================================================


class _CountingCalendar:
    """The ``calendar`` module as the ``interest`` module reads it, with ``isleap`` and ``monthrange`` counted."""

    def __init__(self, real):
        self.real = real
        self.calls = 0

    def isleap(self, year: int) -> bool:
        self.calls += 1
        return self.real.isleap(year)

    def monthrange(self, year: int, month: int) -> tuple[int, int]:
        self.calls += 1
        return self.real.monthrange(year, month)

    def __getattr__(self, name: str):
        return getattr(self.real, name)


@contextmanager
def _counting_calendar() -> Iterator[_CountingCalendar]:
    counter = _CountingCalendar(fm_interest.calendar)
    fm_interest.calendar = counter
    try:
        yield counter
    finally:
        fm_interest.calendar = counter.real


def _calendar_calls(start: date, end: date, convention: DayCountConvention) -> int:
    """The calendar look-ups of one ``compound_growth`` call, from a cleared memo."""
    _clear_memo()
    with _counting_calendar() as counter:
        compound_growth(start, end, RATES[1], convention)
    return counter.calls


# The budget of one call: 30/360 reads the months of its two dates, each month up to twice (its length and the one
# before), so 2 dates × 12 months × 2; ACT/ACT reads two year lengths; ACT/365 and ACT/360 none. Before: one year length
# per year of an ACT/ACT span, one or two month lengths per month of a 30/360 span.
CALENDAR_CALLS_PER_GROWTH = 2 * 12 * 2
# Both spans run from mid-December to late December, so the end dates read the same months: the worst case of 30/360.
SHORT_SPAN = (date(2024, 12, 15), date(2025, 12, 20))
LONG_SPAN = (date(1950, 12, 15), date(2200, 12, 20))


@pytest.mark.parametrize("convention", list(DayCountConvention), ids=lambda c: c.name)
def test_compound_growth_cost_does_not_grow_with_the_span(convention):
    """Red before the note (ACT/ACT ~250 calls, 30/360 ~6 000 over 250 years): one call over 250 years makes the same
    calendar look-ups as one over 1 year, within ``CALENDAR_CALLS_PER_GROWTH``."""
    short = _calendar_calls(*SHORT_SPAN, convention)
    long = _calendar_calls(*LONG_SPAN, convention)
    assert long <= CALENDAR_CALLS_PER_GROWTH, f"{convention}: {long} calendar calls for {LONG_SPAN[0]} -> {LONG_SPAN[1]}, budget {CALENDAR_CALLS_PER_GROWTH}"
    assert short <= CALENDAR_CALLS_PER_GROWTH, f"{convention}: {short} calendar calls for {SHORT_SPAN[0]} -> {SHORT_SPAN[1]}, budget {CALENDAR_CALLS_PER_GROWTH}"
    assert long == short, f"{convention}: {long} calendar calls over 250 years, {short} over 1 year"


# ============================================================================
# B. Parity: 30/360 counts exactly, ACT/ACT within the tolerances
# ============================================================================


def _month_loop_steps(start_date: date, end_date: date) -> dict[int, int]:
    """The oracle: ``_thirty_360_daily_steps`` before the note, verbatim but for the names (and ``calendar`` read from
    this module, so a counting stand-in never sees it)."""
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    first_day = start_date + timedelta(days=1)
    year, month = first_day.year, first_day.month
    while date(year, month, 1) <= end_date:
        month_length = calendar.monthrange(year, month)[1]
        low = max(first_day, date(year, month, 1))
        high = min(end_date, date(year, month, month_length))
        if low <= high:
            if low.day == 1:
                previous_length = calendar.monthrange(year - 1, 12)[1] if month == 1 else calendar.monthrange(year, month - 1)[1]
                counts[31 - min(previous_length, 30)] += 1
                low_inner = 2
            else:
                low_inner = low.day
            inner = high.day - low_inner + 1
            if inner > 0:
                onto_31 = 1 if high.day == 31 else 0
                counts[1] += inner - onto_31
                counts[0] += onto_31
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return counts


def _month_edges(years: range) -> list[date]:
    """The 1st, the day before the last and the last of every month of ``years``: where a 30/360 step changes."""
    edges = []
    for year in years:
        for month in range(1, 13):
            length = calendar.monthrange(year, month)[1]
            edges += [date(year, month, 1), date(year, month, length - 1), date(year, month, length)]
    return edges


def _thirty_360_spans() -> Iterator[tuple[date, date]]:
    """Every pair of month edges through 2023-2025 (both kinds of February, every 30th and 31st); random spans of up to
    3 years and of up to 100 years between 1900 and 2200 (seeded); and two spans from 1 January of year 1, where the
    counts up to a date start."""
    edges = _month_edges(range(2023, 2026))
    for index, start in enumerate(edges):
        for end in edges[index + 1 :]:
            yield start, end
    rng = random.Random(20261017)
    last_start = (SCHEDULE_MAX_DATE - SCHEDULE_MIN_DATE).days - 1
    for max_days in [1_100] * 3_000 + [36_525] * 200:
        start = SCHEDULE_MIN_DATE + timedelta(days=rng.randint(0, last_start))
        yield start, min(start + timedelta(days=rng.randint(1, max_days)), SCHEDULE_MAX_DATE)
    yield date(1, 1, 1), date(1, 3, 5)
    yield date(1, 1, 1), date(4, 3, 1)


def test_thirty_360_step_counts_are_the_month_loop_counts():
    """Guard: the step counts of every span are the old month loop's, exactly — integers, so no tolerance."""
    spans = [(start, end) for start, end in _thirty_360_spans() if end > start]
    misses = []
    for start, end in spans:
        counts = fm_interest._thirty_360_daily_steps(start, end)
        expected = _month_loop_steps(start, end)
        if {days: counts.get(days, 0) for days in (0, 1, 2, 3)} != expected or set(counts) - {0, 1, 2, 3}:
            misses.append(f"{start} -> {end}: {counts}, the month loop {expected}")
    assert sum(expected.values()) == (end - start).days  # the oracle counts one step per day (checked on the last span)
    assert not misses, f"{len(misses)} of {len(spans)} spans differ from the month loop:\n" + "\n".join(misses[:20])


def _per_year_act_act_growth(start_date: date, end_date: date, annual_rate: Decimal) -> Decimal:
    """The oracle: the ACT/ACT branch of ``compound_growth`` before the note, verbatim but for the names."""
    growth = Decimal(1)
    for year in range(start_date.year, end_date.year + 1):
        steps = (min(end_date, date(year + 1, 1, 1)) - max(start_date, date(year, 1, 1))).days
        if steps > 0:
            growth *= (1 + annual_rate / (366 if calendar.isleap(year) else 365)) ** steps
    return growth


def _act_act_short_spans() -> Iterator[tuple[date, date]]:
    """Starts every 11 days through 2023, ends every 13 days through 2023-2027, with at most 2 whole calendar years
    between the start's year and the end's: inside one year, across one 1 January, and across two or three."""
    starts = [date(2023, 1, 1) + timedelta(days=11 * step) for step in range(34)]
    ends = [date(2023, 1, 1) + timedelta(days=13 * step) for step in range(141)]
    for start in starts:
        for end in ends:
            if end > start and end.year - start.year - 1 <= 2:
                yield start, end


@pytest.mark.parametrize("rate", RATES, ids=str)
def test_act_act_growth_equals_the_per_year_product_on_short_spans(rate):
    """Guard: over at most 2 whole years, ACT/ACT is the old per-year product within a relative 1e-26 (a few roundings
    of 5e-28 grouped otherwise)."""
    _clear_memo()
    spans = list(_act_act_short_spans())
    misses = []
    for start, end in spans:
        actual = compound_growth(start, end, rate, DayCountConvention.ACT_ACT)
        expected = _per_year_act_act_growth(start, end, rate)
        gap = _relative_gap(actual, expected)
        if gap > SHORT_SPAN_TOLERANCE:
            misses.append(f"{start} -> {end}: {actual}, per-year product {expected}, relative gap {gap:.3E}")
    assert not misses, f"{len(misses)} of {len(spans)} spans past {SHORT_SPAN_TOLERANCE}:\n" + "\n".join(misses[:20])


_LONG_SPANS = {
    "1900-to-2200": (date(1900, 3, 2), date(2200, 12, 31)),
    "250-years-mid-december": LONG_SPAN,
    "century-from-a-leap-day": (date(2000, 2, 29), date(2100, 3, 1)),
    "century-over-1900": (date(1899, 7, 1), date(1999, 6, 30)),
    "50-years-1-january-to-1-january": (date(1975, 1, 1), date(2025, 1, 1)),
}


@pytest.mark.parametrize("rate", RATES, ids=str)
@pytest.mark.parametrize("span", list(_LONG_SPANS), ids=str)
def test_act_act_growth_over_long_spans_is_the_60_digit_product(span, rate):
    """Guard: over up to 300 years, ACT/ACT is within a relative 1e-22 of the per-year product in a 60-digit context
    (each power correctly rounded to 60 digits, so the exact daily product to ~1e-57). The default context rounds
    ``1 + r / 365`` once, 5e-28 at most, which ~110 000 days carry to ~5.5e-23."""
    start, end = _LONG_SPANS[span]
    _clear_memo()
    actual = compound_growth(start, end, rate, DayCountConvention.ACT_ACT)
    with localcontext() as context:
        context.prec = ORACLE_PRECISION
        exact = _per_year_act_act_growth(start, end, rate)
    gap = _relative_gap(actual, exact)
    assert gap <= LONG_SPAN_TOLERANCE, f"{start} -> {end} at {rate}: {actual}, 60-digit product {exact}, relative gap {gap:.3E}"


# ============================================================================
# C. The memo key: the rate as written, the caller's context
# ============================================================================

MEMO_SPAN = (date(2024, 1, 15), date(2026, 3, 1))
# The growth at a zero rate, as each zero is written: the trailing zeros of 0.000 survive the division and the power.
_ZERO_RATE_TEXTS = {"0.000": "1.000000000000000000000000000", "0": "1"}


@pytest.mark.parametrize("order", [("0.000", "0"), ("0", "0.000")], ids="-then-".join)
@pytest.mark.parametrize("convention", list(DayCountConvention), ids=lambda c: c.name)
def test_memo_keeps_each_zero_rate_its_own_digits(convention, order):
    """Guard: ``Decimal("0.000") == Decimal("0")`` and they hash alike, so a memo keyed on the rate alone would hand the
    second the first's result. Each keeps its own ``str``, in either order."""
    _clear_memo()
    texts = {rate: str(compound_growth(*MEMO_SPAN, Decimal(rate), convention)) for rate in order}
    assert texts == _ZERO_RATE_TEXTS


@pytest.mark.parametrize("convention", list(DayCountConvention), ids=lambda c: c.name)
def test_memo_keeps_each_context_its_own_result(convention):
    """Guard: a call in a 60-digit context neither changes the default context's result after it, nor gets the default
    context's result when the default asked first."""
    rate = RATES[2]
    _clear_memo()
    default_cold = str(compound_growth(*MEMO_SPAN, rate, convention))
    _clear_memo()
    with localcontext() as context:
        context.prec = ORACLE_PRECISION
        wide_cold = str(compound_growth(*MEMO_SPAN, rate, convention))
    default_after_wide = str(compound_growth(*MEMO_SPAN, rate, convention))
    with localcontext() as context:
        context.prec = ORACLE_PRECISION
        wide_after_default = str(compound_growth(*MEMO_SPAN, rate, convention))

    assert wide_cold != default_cold, "not vacuous: the two contexts give other digits"
    assert default_after_wide == default_cold, f"default context after a 60-digit call: {default_after_wide}, cold {default_cold}"
    assert wide_after_default == wide_cold, f"60-digit context after a default call: {wide_after_default}, cold {wide_cold}"
