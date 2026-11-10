"""Interest and day count: the time fraction between two dates under a day count convention, and simple interest.

The conventions are the market's (ACT/365, ACT/360, ACT/ACT, 30/360). They take plain dates and return a ``Decimal``
year fraction; simple interest is principal × annual rate × that fraction, and ``compound_growth`` the product of a
day's simple interest over a span, in closed form. The Scheduled Investment provider builds its
accrual on them: a day's interest is the simple interest of one day, on the principal (SIMPLE) or on the running value
(COMPOUND), and late interest after maturity uses the same primitives.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, getcontext
from functools import lru_cache

from backend.app.schemas.assets.scheduled_investment import DayCountConvention


def calculate_day_count_fraction(
    start_date: date,
    end_date: date,
    convention: DayCountConvention = DayCountConvention.ACT_365,
) -> Decimal:
    """
    Calculate day fraction using specified day count convention.

    Supports multiple conventions:
    - ACT/365: Actual days / 365
    - ACT/360: Actual days / 360
    - ACT/ACT (ISDA): the days in each calendar year / that year's length (365, or 366 in a leap year)
    - 30/360: Assumes 30 days per month, 360 days per year

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        convention: Day count convention to use

    Returns:
        Decimal fraction representing the time period
    """
    if convention == DayCountConvention.ACT_365:
        return _calculate_act_fixed(start_date, end_date, 365)
    elif convention == DayCountConvention.ACT_360:
        return _calculate_act_fixed(start_date, end_date, 360)
    elif convention == DayCountConvention.ACT_ACT:
        return _calculate_act_act(start_date, end_date)
    elif convention == DayCountConvention.THIRTY_360:
        return _calculate_30_360(start_date, end_date)
    else:
        raise ValueError(f"Unsupported day count convention: {convention}")


def _calculate_act_fixed(start_date: date, end_date: date, denominator: int) -> Decimal:
    """ACT/N: Actual days / fixed denominator (365 or 360)."""
    days = (end_date - start_date).days
    return Decimal(days) / Decimal(denominator)


def _calculate_act_act(start_date: date, end_date: date) -> Decimal:
    """
    ACT/ACT (ISDA): the days in each calendar year over that year's length.

    The span is cut at every 1 January it crosses: each piece counts its days up to the next 1 January (or the end
    date) and is divided by 366 in a leap year, 365 otherwise. 2025-07-01 → 2026-06-30 is 184/365 + 180/365 = 364/365.
    """
    if start_date.year == end_date.year:
        days = (end_date - start_date).days
        days_in_year = 366 if calendar.isleap(start_date.year) else 365
        return Decimal(days) / Decimal(days_in_year)

    if end_date < start_date:
        return Decimal(0)  # a reversed span over two years: the year loop sums nothing
    last_days = (end_date - date(end_date.year, 1, 1)).days
    context = getcontext()
    whole = _act_act_years_before(start_date, end_date.year, context.prec, context.rounding)
    return whole + Decimal(last_days) / Decimal(366 if calendar.isleap(end_date.year) else 365) if last_days > 0 else whole


@lru_cache(maxsize=4096)
def _act_act_years_before(start_date: date, end_year: int, precision: int, rounding: str) -> Decimal:
    """The ACT/ACT fraction from ``start_date`` to 1 January of ``end_year``, summed year by year in calendar order.

    The additions of the year loop, in its order, so the same digits. Memoized: the fractions of a long run of dates
    from one start (a late-interest history) sum each year once per end year, not once per date (R13-SEC7-2). The
    caller's ``precision`` and ``rounding`` are part of the key, so a sum rounded in one Decimal context is never
    returned to another.
    """
    total = Decimal(0)
    for year in range(start_date.year, end_year):
        segment_start = max(start_date, date(year, 1, 1))
        days = (date(year + 1, 1, 1) - segment_start).days
        if days > 0:
            total += Decimal(days) / Decimal(366 if calendar.isleap(year) else 365)
    return total


def _calculate_30_360(start_date: date, end_date: date) -> Decimal:
    """
    30/360: Assumes 30 days per month, 360 days per year (US NASD convention).
    """
    d1 = start_date.day
    d2 = end_date.day
    m1 = start_date.month
    m2 = end_date.month
    y1 = start_date.year
    y2 = end_date.year

    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 >= 30:
        d2 = 30

    days = (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)
    return Decimal(days) / Decimal(360)


def calculate_simple_interest(principal: Decimal, annual_rate: Decimal, time_fraction: Decimal) -> Decimal:
    """
    Calculate simple interest: I = P * r * t.

    Args:
        principal: Principal amount
        annual_rate: Annual interest rate (e.g., 0.05 for 5%)
        time_fraction: Time period as fraction of year

    Returns:
        Interest earned
    """
    return principal * annual_rate * time_fraction


def compound_growth(start_date: date, end_date: date, annual_rate: Decimal, convention: DayCountConvention = DayCountConvention.ACT_365) -> Decimal:
    """The growth factor of daily compounding from ``start_date`` to ``end_date``: Π (1 + r · f) over the days.

    Each day ``d`` in (start, end] adds the simple interest of one day, ``f = calculate_day_count_fraction(d − 1, d)``,
    on the value of the day before: the walk ``V += V · r · f`` in closed form, one power per run of equal fractions
    instead of a step per day. ACT/365 and ACT/360 have one fraction; ACT/ACT one per calendar year (the year of the
    day before); 30/360 one of 0, 1, 2 or 3 days over 360, counted month by month. 1 for an empty or reversed span.
    """
    if end_date <= start_date:
        return Decimal(1)
    context = getcontext()
    return _compound_growth(start_date, end_date, annual_rate, str(annual_rate), convention, context.prec, context.rounding)


@lru_cache(maxsize=4096)
def _compound_growth(start_date: date, end_date: date, annual_rate: Decimal, rate_text: str, convention: DayCountConvention, precision: int, rounding: str) -> Decimal:
    """``compound_growth`` of a non-empty span, memoized: a late-interest history multiplies the same grace-period span
    into every date after it. The key holds the rate as written (``0.05`` and ``0.050`` are equal Decimals with other
    digits) and the caller's ``precision`` and ``rounding``."""
    if convention == DayCountConvention.ACT_365:
        return (1 + annual_rate / 365) ** (end_date - start_date).days
    if convention == DayCountConvention.ACT_360:
        return (1 + annual_rate / 360) ** (end_date - start_date).days
    if convention == DayCountConvention.ACT_ACT:
        return _act_act_growth(start_date, end_date, annual_rate)
    if convention == DayCountConvention.THIRTY_360:
        steps_by_days = _thirty_360_daily_steps(start_date, end_date)
        growth = Decimal(1)
        for days, count in steps_by_days.items():
            if days and count:
                growth *= (1 + annual_rate * days / 360) ** count
        return growth
    raise ValueError(f"Unsupported day count convention: {convention}")


def _act_act_growth(start_date: date, end_date: date, annual_rate: Decimal) -> Decimal:
    """ACT/ACT daily compounding over a non-empty span: the first year's days, the whole years between (one power for the
    common years, one for the leap ones), the last year's days — a long span costs what a short one does (R13-SEC7-2)."""
    if start_date.year == end_date.year:
        return (1 + annual_rate / _year_length(start_date.year)) ** (end_date - start_date).days
    growth = (1 + annual_rate / _year_length(start_date.year)) ** (date(start_date.year + 1, 1, 1) - start_date).days
    leap_years = _leap_years_before(end_date.year) - _leap_years_before(start_date.year + 1)
    common_years = end_date.year - start_date.year - 1 - leap_years
    if common_years:
        growth *= (1 + annual_rate / 365) ** (365 * common_years)
    if leap_years:
        growth *= (1 + annual_rate / 366) ** (366 * leap_years)
    last_days = (end_date - date(end_date.year, 1, 1)).days
    if last_days:
        growth *= (1 + annual_rate / _year_length(end_date.year)) ** last_days
    return growth


def _thirty_360_daily_steps(start_date: date, end_date: date) -> dict[int, int]:
    """How many one-day steps (d − 1 → d, d in (start, end]) count 0, 1, 2 or 3 days under 30/360.

    Inside a month a step counts 1, except the step onto the 31st (30 → 31 counts 0). The step onto the 1st counts
    30 − the previous month's last day, capped at 30, plus 1: 1 after a 31- or 30-day month, 2 after 29, 3 after 28.
    The counts of (start, end] are the counts up to end minus those up to start: integers, so exact.
    """
    up_to_end = _thirty_360_steps_up_to(end_date)
    up_to_start = _thirty_360_steps_up_to(start_date)
    return {days: up_to_end[days] - up_to_start[days] for days in (0, 1, 2, 3)}


def _thirty_360_steps_up_to(day: date) -> dict[int, int]:
    """The 30/360 one-day steps onto every date from 1 January of year 1 to ``day``, by the days they count.

    A whole year has 7 steps of 0 (onto the seven 31sts), one of 3 onto 1 March of a common year or of 2 in a leap
    year, and the rest of 1: computed per year in closed form, per month in the last one.
    """
    whole_years = day.year - 1
    leap_years = _leap_years_before(day.year)
    counts = {0: 7 * whole_years, 1: 0, 2: leap_years, 3: whole_years - leap_years}
    counts[1] = (date(day.year, 1, 1) - date(1, 1, 1)).days - counts[0] - counts[2] - counts[3]
    for month in range(1, day.month + 1):
        month_length = calendar.monthrange(day.year, month)[1]
        last = day.day if month == day.month else month_length
        if month > 1:  # the step onto 1 January is in the whole years (or is the start, in year 1)
            previous_length = calendar.monthrange(day.year, month - 1)[1]
            counts[31 - min(previous_length, 30)] += 1
        inner = last - 1
        if inner > 0:
            onto_31 = 1 if last == 31 else 0
            counts[1] += inner - onto_31
            counts[0] += onto_31
    return counts


def _year_length(year: int) -> int:
    return 366 if calendar.isleap(year) else 365


def _leap_years_before(year: int) -> int:
    """The leap years from year 1 to ``year − 1``."""
    previous = year - 1
    return previous // 4 - previous // 100 + previous // 400
