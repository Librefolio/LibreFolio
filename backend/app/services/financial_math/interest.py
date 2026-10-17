"""Interest and day count: the time fraction between two dates under a day count convention, and simple interest.

The conventions are the market's (ACT/365, ACT/360, ACT/ACT, 30/360). They take plain dates and return a ``Decimal``
year fraction; simple interest is principal × annual rate × that fraction. The Scheduled Investment provider builds its
accrual on them: a day's interest is the simple interest of one day, on the principal (SIMPLE) or on the running value
(COMPOUND), and late interest after maturity uses the same primitives.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

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
    - ACT/ACT: Actual days / actual days in year (365 or 366 if leap year)
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
    ACT/ACT: Actual days / actual days in year.

    Handles leap years correctly by calculating the fraction for each year separately.
    """
    if start_date.year == end_date.year:
        days = (end_date - start_date).days
        days_in_year = 366 if calendar.isleap(start_date.year) else 365
        return Decimal(days) / Decimal(days_in_year)

    total_fraction = Decimal("0")
    current_year = start_date.year

    last_year = end_date.year
    if end_date.month == 1 and end_date.day == 1:
        last_year -= 1

    while current_year <= last_year:
        if current_year == start_date.year:
            period_start = start_date
            if current_year == last_year:
                period_end = end_date
            else:
                period_end = date(current_year, 12, 31)
        elif current_year == last_year:
            period_start = date(current_year, 1, 1)
            period_end = end_date
        else:
            period_start = date(current_year, 1, 1)
            period_end = date(current_year, 12, 31)

        days = (period_end - period_start).days
        days_in_year = 366 if calendar.isleap(current_year) else 365
        total_fraction += Decimal(days) / Decimal(days_in_year)
        current_year += 1

    return total_fraction


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
