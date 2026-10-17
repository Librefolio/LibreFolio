"""
ACT/ACT across years, memoized by year — R13-SEC7-2, night decision N73, workstream MF.

Before: ``_calculate_act_act`` cut a span at every 1 January and added one Decimal quotient per calendar year, days /
that year's length, in calendar order. A span of n years cost n steps, and SIMPLE late interest asks for one span from
maturity per emitted date: a DAILY late history read 125 years after maturity cost ~125 steps per date.

Now the same loop, the same additions in the same order, so the same digits (workstream J's contract, lot CP-14b: the
per-year sum, digit for digit, and additive at 1 January): the years before the end's are summed by
``_act_act_years_before(start, end_year)``, memoized, then the last segment is added. A run of dates from one start sums
the whole years once per end year, not once per date. A reversed span across years is 0, the loop's empty sum; a span
inside one year is the one division it always was.

The oracle is the loop itself, ported verbatim from the code before the fix (``_year_loop_act_act``), compared with
``str``: digits and exponent. The cost is counted, never timed: the calls of ``calendar.isleap`` the ``interest`` module
makes, through the ``calendar`` name it reads, from a cleared memo.

Every fraction is asked in the default context: the memo keeps the sums of the context that first asked them.

Pure: no database, no server, no network.
"""

import calendar
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.schemas.assets.scheduled_investment import DayCountConvention
from backend.app.services.financial_math import interest as fm_interest
from backend.app.services.financial_math.interest import calculate_day_count_fraction


def _year_length(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def _act_act(start: date, end: date) -> Decimal:
    return calculate_day_count_fraction(start, end, DayCountConvention.ACT_ACT)


def _year_loop_act_act(start_date: date, end_date: date) -> Decimal:
    """The oracle: ``_calculate_act_act`` before R13-SEC7-2, verbatim but for the names."""
    if start_date.year == end_date.year:
        days = (end_date - start_date).days
        return Decimal(days) / Decimal(_year_length(start_date.year))
    total_fraction = Decimal("0")
    for year in range(start_date.year, end_date.year + 1):
        segment_start = max(start_date, date(year, 1, 1))
        segment_end = min(end_date, date(year + 1, 1, 1))
        days = (segment_end - segment_start).days
        if days > 0:
            total_fraction += Decimal(days) / Decimal(_year_length(year))
    return total_fraction


def _clear_memo() -> None:
    """Empty the memo of the year sums, where the module has one (the code before the fix has none)."""
    memo = getattr(fm_interest, "_act_act_years_before", None)
    if memo is not None:
        memo.cache_clear()


def _mismatches(pairs) -> list[str]:
    return [f"{start} -> {end}: {_act_act(start, end)}, the year loop {_year_loop_act_act(start, end)}" for start, end in pairs if str(_act_act(start, end)) != str(_year_loop_act_act(start, end))]


# Spans across at least one 1 January, by name: (start, end).
_ACROSS_YEARS = {
    "1-day-over-a-leap-year-end": (date(2024, 12, 31), date(2025, 1, 1)),
    "1-day-over-a-non-leap-year-end": (date(2025, 12, 31), date(2026, 1, 1)),
    "1-day-into-a-leap-year": (date(2023, 12, 31), date(2024, 1, 1)),
    "4-days-leap-to-non-leap": (date(2024, 12, 30), date(2025, 1, 3)),
    "4-days-non-leap-to-leap": (date(2023, 12, 30), date(2024, 1, 3)),
    "leap-to-non-leap-364-days": (date(2024, 7, 1), date(2025, 6, 30)),
    "non-leap-to-non-leap-364-days": (date(2025, 7, 1), date(2026, 6, 30)),
    "non-leap-to-leap": (date(2027, 3, 15), date(2028, 9, 30)),
    "leap-to-leap": (date(2024, 2, 29), date(2028, 2, 29)),
    "2-years-over-a-leap-year": (date(2023, 7, 1), date(2025, 6, 30)),
    "2-years-from-29-february": (date(2024, 2, 29), date(2026, 3, 1)),
    "ends-on-1-january": (date(2024, 6, 1), date(2027, 1, 1)),
    "starts-on-1-january": (date(2024, 1, 1), date(2025, 3, 1)),
    "1-january-to-1-january": (date(2023, 1, 1), date(2026, 1, 1)),
    "300-years": (date(1900, 1, 31), date(2200, 12, 31)),
    "300-years-1900-to-2200-february": (date(1900, 3, 1), date(2200, 2, 28)),
    "century-1900-non-leap-to-2000-leap": (date(1900, 6, 30), date(2000, 6, 30)),
    "late-interest-125-years": (date(1900, 3, 2), date(2025, 7, 14)),
}

# Spans inside one calendar year: the division the loop did too.
_INSIDE_ONE_YEAR = {
    "whole-leap-year-but-a-day": (date(2024, 1, 1), date(2024, 12, 31)),
    "across-29-february": (date(2024, 2, 28), date(2024, 3, 1)),
    "non-leap-february": (date(2025, 2, 28), date(2025, 3, 1)),
    "one-day": (date(2025, 6, 30), date(2025, 7, 1)),
    "empty": (date(2025, 6, 30), date(2025, 6, 30)),
    "reversed-inside-a-year": (date(2024, 5, 1), date(2024, 3, 1)),
}


@pytest.mark.parametrize("span", list(_ACROSS_YEARS), ids=str)
def test_act_act_across_years_is_the_year_loop_digit_for_digit(span):
    """Guard: across years, ACT/ACT is the old year loop's value, ``str`` for ``str`` — from a cold memo and from a warm one."""
    start, end = _ACROSS_YEARS[span]
    _clear_memo()
    assert _mismatches([(start, end)]) == []
    assert _mismatches([(start, end)]) == []


def _sweep_pairs() -> Iterator[tuple[date, date]]:
    """Starts every 11 days through 2023-2024 (67), ends every 13 days through 2024-2028 (141): the 8 490 pairs across
    a 1 January, with every combination of leap and non-leap ends."""
    starts = [date(2023, 1, 1) + timedelta(days=11 * step) for step in range(67)]
    ends = [date(2024, 1, 1) + timedelta(days=13 * step) for step in range(141)]
    for start in starts:
        for end in ends:
            if end.year > start.year:
                yield start, end


def test_act_act_sweep_is_the_year_loop_digit_for_digit():
    """Guard: on every pair of the sweep, ACT/ACT across years is the old year loop's value, ``str`` for ``str``."""
    _clear_memo()
    misses = _mismatches(_sweep_pairs())
    assert not misses, f"{len(misses)} spans differ from the year loop:\n" + "\n".join(misses[:20])


@pytest.mark.parametrize("start", [date(1900, 3, 2), date(1999, 12, 31), date(2024, 2, 29)], ids=str)
def test_act_act_long_run_from_one_start_is_the_year_loop_digit_for_digit(start):
    """Guard: a run of ends from one start, every 17 days to 2200 — the memo's case, one sum per end year read back by
    every later end of that year — is the old year loop's value, ``str`` for ``str``."""
    _clear_memo()
    ends = [date(start.year + 1, 1, 1) + timedelta(days=17 * step) for step in range(((date(2200, 12, 31) - date(start.year + 1, 1, 1)).days // 17) + 1)]
    misses = _mismatches((start, end) for end in ends)
    assert not misses, f"{len(misses)} of {len(ends)} spans differ from the year loop:\n" + "\n".join(misses[:20])


def _one_january_splits() -> Iterator[tuple[date, date, date]]:
    """(a, 1 January, c) with a in the year before and c in the year after, every 3 days, over the year ends 2020-2029."""
    for year in range(2020, 2030):
        new_year = date(year + 1, 1, 1)
        for back in range(1, 366, 3):
            for forward in range(1, 366, 3):
                start, end = new_year - timedelta(days=back), new_year + timedelta(days=forward)
                if start.year == year and end.year == year + 1:
                    yield start, new_year, end


def test_act_act_is_additive_at_1_january_digit_for_digit():
    """Guard: ISDA is additive at a year boundary, [a, 1/1) + [1/1, c) is [a, c), ``str`` for ``str``, on every split of
    the sweep (J's contract, lot CP-14b)."""
    _clear_memo()
    broken = []
    for start, new_year, end in _one_january_splits():
        whole, halves = _act_act(start, end), _act_act(start, new_year) + _act_act(new_year, end)
        if str(whole) != str(halves):
            broken.append(f"[{start}, {end}) = {whole}, [{start}, {new_year}) + [{new_year}, {end}) = {halves}")
    assert not broken, f"{len(broken)} splits are not additive:\n" + "\n".join(broken[:20])


@pytest.mark.parametrize(
    ("start", "end"),
    [
        pytest.param(date(2025, 3, 1), date(2024, 3, 1), id="one-year-back"),
        pytest.param(date(2025, 1, 1), date(2024, 12, 31), id="one-day-back-over-a-year-end"),
        pytest.param(date(2200, 12, 31), date(1900, 1, 1), id="300-years-back"),
    ],
)
def test_act_act_reversed_span_across_years_is_zero(start, end):
    """Guard: a reversed span across years is 0, the year loop's empty sum (inside one year it stays negative)."""
    assert _act_act(start, end) == 0
    assert str(_act_act(start, end)) == str(_year_loop_act_act(start, end))


@pytest.mark.parametrize("span", list(_INSIDE_ONE_YEAR), ids=str)
def test_act_act_inside_one_year_is_unchanged(span):
    """Guard: inside one calendar year ACT/ACT is the year loop's value, ``str`` for ``str``."""
    start, end = _INSIDE_ONE_YEAR[span]
    assert str(_act_act(start, end)) == str(_year_loop_act_act(start, end))


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
    counter = _CountingCalendar(fm_interest.calendar)
    fm_interest.calendar = counter
    try:
        yield counter
    finally:
        fm_interest.calendar = counter.real


# At most this many year-length look-ups per fraction, besides the year sums: the last segment's year.
PER_DATE = 2


@pytest.mark.parametrize(
    ("start", "first", "last"),
    [
        pytest.param(date(1900, 3, 2), date(2025, 1, 1), date(2025, 12, 31), id="1900-start-a-year-of-ends"),
        pytest.param(date(1900, 3, 2), date(2024, 1, 1), date(2025, 12, 31), id="1900-start-two-years-of-ends"),
        pytest.param(date(1900, 3, 2), date(2016, 1, 1), date(2025, 12, 31), id="1900-start-ten-years-of-ends"),
        pytest.param(date(2000, 6, 30), date(2195, 1, 1), date(2200, 12, 31), id="2000-start-ends-to-the-horizon"),
    ],
)
def test_act_act_run_of_dates_from_one_start_costs_its_dates_plus_its_years(start, first, last):
    """Red: the fractions from one start to N consecutive dates cost at most PER_DATE · N year-length look-ups, plus the
    years before each end year once: N + years for a run inside one end year. Before: every date looked up every year
    of its span, ~N · years."""
    ends = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    years_once_per_end_year = sum(end_year - start.year for end_year in range(first.year, last.year + 1))
    budget = PER_DATE * len(ends) + years_once_per_end_year
    _clear_memo()
    with _counting_isleap() as counter:
        for end in ends:
            _act_act(start, end)
    assert counter.isleap_calls <= budget, f"{counter.isleap_calls} calls of calendar.isleap for {len(ends)} dates from {start} (~{counter.isleap_calls / len(ends):.0f} per date), budget {budget}"
