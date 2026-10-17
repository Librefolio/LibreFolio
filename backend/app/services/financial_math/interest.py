"""Interest and day count: the time fraction between two dates under a day count convention, and simple interest.

The conventions are the market's (ACT/365, ACT/360, ACT/ACT, 30/360). They take plain dates and return a ``Decimal``
year fraction; simple interest is principal × annual rate × that fraction, and ``compound_growth`` the product of a
day's simple interest over a span, in closed form. The Scheduled Investment provider builds its
accrual on them: a day's interest is the simple interest of one day, on the principal (SIMPLE) or on the running value
(COMPOUND), and late interest after maturity uses the same primitives.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
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
    if convention == DayCountConvention.ACT_365:
        return (1 + annual_rate / 365) ** (end_date - start_date).days
    if convention == DayCountConvention.ACT_360:
        return (1 + annual_rate / 360) ** (end_date - start_date).days
    if convention == DayCountConvention.ACT_ACT:
        growth = Decimal(1)
        for year in range(start_date.year, end_date.year + 1):
            steps = (min(end_date, date(year + 1, 1, 1)) - max(start_date, date(year, 1, 1))).days
            if steps > 0:
                growth *= (1 + annual_rate / (366 if calendar.isleap(year) else 365)) ** steps
        return growth
    if convention == DayCountConvention.THIRTY_360:
        steps_by_days = _thirty_360_daily_steps(start_date, end_date)
        growth = Decimal(1)
        for days, count in steps_by_days.items():
            if days and count:
                growth *= (1 + annual_rate * days / 360) ** count
        return growth
    raise ValueError(f"Unsupported day count convention: {convention}")


def _thirty_360_daily_steps(start_date: date, end_date: date) -> dict[int, int]:
    """How many one-day steps (d − 1 → d, d in (start, end]) count 0, 1, 2 or 3 days under 30/360.

    Inside a month a step counts 1, except the step onto the 31st (30 → 31 counts 0). The step onto the 1st counts
    30 − the previous month's last day, capped at 30, plus 1: 1 after a 31- or 30-day month, 2 after 29, 3 after 28.
    """
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
