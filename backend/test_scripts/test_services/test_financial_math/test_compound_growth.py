"""
``compound_growth`` (``financial_math/interest.py``) — R13-SEC7-2, night decision N73, workstream MF.

Before: COMPOUND late interest walked one day at a time from maturity, for every date it was asked on, so a long DAILY
late history was quadratic in its days. Now the walk ``V += V · r · f`` has a closed form:

    compound_growth(start, end, r, convention) = Π over d in (start, end] of (1 + r · f(d − 1, d)),
    f = calculate_day_count_fraction,

one power per run of equal day fractions: ACT/365 and ACT/360 have one; ACT/ACT one per calendar year (the year of
d − 1); 30/360 counts steps of 0, 1, 2 or 3 days over 360 month by month. An empty or reversed span is 1.

The oracle is that definition, multiplied day by day in a 60-digit ``localcontext``, so its own rounding (~n · 1e-60) is
nothing next to the tolerance; each day's fraction is asked in the default context, as the provider asks it (28 digits,
a relative 1e-28 on r · f, again nothing next to the tolerance). ``compound_growth`` runs in the default 28-digit
context, as the provider calls it: each power rounds its base once (a relative 5e-28 at most), which a span of n days
carries to ~n · 5e-28 — under 6e-25 for the ~1 100 days of the longest span here. Hence a relative tolerance of 1e-24,
and spans under three years: a ten-year span would sit on the tolerance by construction, not by defect.

Red on the code before the fix: ``compound_growth`` does not exist, so the module does not import.

Pure: no database, no server, no network.
"""

from datetime import date, timedelta
from decimal import Decimal, localcontext

import pytest

from backend.app.schemas.assets.scheduled_investment import DayCountConvention
from backend.app.services.financial_math.interest import calculate_day_count_fraction, compound_growth

RELATIVE_TOLERANCE = Decimal("1e-24")
ORACLE_PRECISION = 60
RATES = (Decimal("0.0475"), Decimal("0.12"))


def _daily_product(start: date, end: date, rate: Decimal, convention: DayCountConvention) -> Decimal:
    """The definition: Π (1 + r · f(d − 1, d)) for d in (start, end], day by day, multiplied in a 60-digit context.

    Each fraction is asked in the caller's context, as the provider asks it: ``calculate_day_count_fraction`` memoizes
    ACT/ACT year sums, and a 60-digit call would leave 60-digit sums for every later caller of this process.
    """
    growth = Decimal(1)
    day = start + timedelta(days=1)
    while day <= end:
        fraction = calculate_day_count_fraction(day - timedelta(days=1), day, convention)
        with localcontext() as context:
            context.prec = ORACLE_PRECISION
            growth *= 1 + rate * fraction
        day += timedelta(days=1)
    return growth


def _relative_gap(actual: Decimal, expected: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = ORACLE_PRECISION
        return abs(actual - expected) / expected


def _assert_matches_daily_product(start: date, end: date, rate: Decimal, convention: DayCountConvention) -> None:
    actual = compound_growth(start, end, rate, convention)
    expected = _daily_product(start, end, rate, convention)
    gap = _relative_gap(actual, expected)
    assert gap <= RELATIVE_TOLERANCE, f"{convention} {start} -> {end} at {rate}: compound_growth {actual}, daily product {expected}, relative gap {gap:.3E}"


# (start, end) of the named spans: each is a place where the day fraction changes.
_SPANS = {
    "month-end-31-days": (date(2025, 1, 25), date(2025, 2, 5)),
    "month-end-30-days": (date(2024, 4, 27), date(2024, 5, 3)),
    "across-a-31st": (date(2025, 3, 29), date(2025, 4, 2)),
    "february-not-leap": (date(2025, 2, 26), date(2025, 3, 3)),
    "february-leap": (date(2024, 2, 26), date(2024, 3, 3)),
    "onto-february-29": (date(2024, 2, 28), date(2024, 2, 29)),
    "from-february-29": (date(2024, 2, 29), date(2024, 3, 1)),
    "from-february-28-not-leap": (date(2025, 2, 28), date(2025, 3, 1)),
    "onto-a-31st": (date(2024, 3, 30), date(2024, 3, 31)),
    "year-end-from-a-leap-year": (date(2024, 12, 29), date(2025, 1, 3)),
    "year-end-into-a-leap-year": (date(2023, 12, 30), date(2024, 1, 2)),
    "onto-january-1": (date(2024, 12, 31), date(2025, 1, 1)),
    "multi-year-across-a-leap-year": (date(2023, 11, 15), date(2026, 8, 20)),
    "whole-leap-year": (date(2024, 1, 1), date(2025, 1, 1)),
    "30-360-31st-to-30th": (date(2024, 1, 31), date(2024, 4, 30)),
    "30-360-31st-to-31st": (date(2024, 1, 31), date(2024, 3, 31)),
    "30-360-31st-to-31st-over-a-year-end": (date(2023, 8, 31), date(2024, 5, 31)),
    "30-360-30th-to-31st": (date(2024, 4, 30), date(2024, 5, 31)),
}


@pytest.mark.parametrize("rate", RATES, ids=str)
@pytest.mark.parametrize("span", list(_SPANS), ids=str)
@pytest.mark.parametrize("convention", list(DayCountConvention), ids=lambda c: c.name)
def test_compound_growth_equals_the_daily_product(convention, span, rate):
    """Red: on each named span, under the four conventions, compound_growth is the day-by-day product within 1e-24."""
    start, end = _SPANS[span]
    _assert_matches_daily_product(start, end, rate, convention)


# Windows of a few weeks around the places the fraction changes: every (start, end) pair inside is checked.
_WINDOWS = {
    "leap-february": (date(2024, 1, 27), date(2024, 3, 3)),
    "non-leap-february": (date(2025, 2, 24), date(2025, 3, 3)),
    "year-end": (date(2023, 12, 26), date(2024, 1, 4)),
    "30-and-31-day-months": (date(2024, 4, 27), date(2024, 6, 2)),
}


@pytest.mark.parametrize("window", list(_WINDOWS), ids=str)
@pytest.mark.parametrize("convention", list(DayCountConvention), ids=lambda c: c.name)
def test_compound_growth_equals_the_daily_product_for_every_pair_in_a_window(convention, window):
    """Red: inside each window, every start and every later end, so no run boundary of 30/360 or ACT/ACT is skipped."""
    first, last = _WINDOWS[window]
    days = [first + timedelta(days=offset) for offset in range((last - first).days + 1)]
    for index, start in enumerate(days):
        for end in days[index + 1 :]:
            _assert_matches_daily_product(start, end, RATES[1], convention)


def test_compound_growth_thirty_360_from_the_31st_by_hand():
    """Red: 30/360 from 31/01/2024 to 31/03/2024 is 58 steps of one day, the step onto 1/03 after a 29-day February of
    two, and the step onto 31/03 of none: (1 + r/360)^58 · (1 + 2r/360)."""
    rate = Decimal("0.12")
    with localcontext() as context:
        context.prec = ORACLE_PRECISION
        by_hand = (1 + rate / 360) ** 58 * (1 + 2 * rate / 360)
    actual = compound_growth(date(2024, 1, 31), date(2024, 3, 31), rate, DayCountConvention.THIRTY_360)
    assert _relative_gap(actual, by_hand) <= RELATIVE_TOLERANCE, f"{actual} != {by_hand}"


@pytest.mark.parametrize("convention", list(DayCountConvention), ids=lambda c: c.name)
def test_compound_growth_at_rate_zero_is_one(convention):
    """Red: at rate 0 there is no growth, over any span: exactly 1."""
    assert compound_growth(date(2023, 11, 15), date(2026, 8, 20), Decimal("0"), convention) == Decimal(1)
    assert compound_growth(date(2024, 1, 31), date(2024, 3, 31), Decimal("0"), convention) == Decimal(1)


@pytest.mark.parametrize("convention", list(DayCountConvention), ids=lambda c: c.name)
def test_compound_growth_of_an_empty_or_reversed_span_is_one(convention):
    """Red: no day in (start, end] means no step: exactly 1, at any rate (the daily product is empty too)."""
    day = date(2024, 2, 29)
    assert compound_growth(day, day, Decimal("0.12"), convention) == Decimal(1)
    assert compound_growth(day, day - timedelta(days=400), Decimal("0.12"), convention) == Decimal(1)
    assert _daily_product(day, day - timedelta(days=400), Decimal("0.12"), convention) == Decimal(1)
