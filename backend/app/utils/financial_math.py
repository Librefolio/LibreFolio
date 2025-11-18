"""
Financial mathematics utility functions.

Provides day count conventions, interest calculations, and other
financial formulas used across the application.

All functions are pure (no side effects) and reusable.

Key concepts:
- Day count conventions: ACT/365, ACT/360, 30/360, ACT/ACT
- Interest types: SIMPLE and COMPOUND interest
- Rate format: Annual rate as Decimal (0.05 = 5%)

Note:
    All functions require Pydantic models from backend.app.schemas.assets.
    To convert from dict/JSON, use: InterestRatePeriod(**dict_data)
    To get dict/JSON from model: model.dict() or model.json()
"""
import calendar
import math
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional, List

from backend.app.schemas.assets import (
    InterestRatePeriod,
    LateInterestConfig,
    DayCountConvention,
    CompoundFrequency,
    )


# ============================================================================
# DAY COUNT CONVENTIONS
# ============================================================================

def calculate_day_count_fraction(start_date: date_type, end_date: date_type, convention: DayCountConvention = DayCountConvention.ACT_365) -> Decimal:
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

    Example:
        >>> calculate_day_count_fraction(date(2025, 1, 1), date(2025, 1, 31), DayCountConvention.ACT_365)
        Decimal('0.0821917808219178082191780821917808')  # 30 days / 365

        >>> calculate_day_count_fraction(date(2025, 1, 1), date(2025, 1, 31), DayCountConvention.ACT_360)
        Decimal('0.0833333333333333333333333333333333')  # 30 days / 360
    """
    if convention == DayCountConvention.ACT_365:
        return _calculate_act_365(start_date, end_date)
    elif convention == DayCountConvention.ACT_360:
        return _calculate_act_360(start_date, end_date)
    elif convention == DayCountConvention.ACT_ACT:
        return _calculate_act_act(start_date, end_date)
    elif convention == DayCountConvention.THIRTY_360:
        return _calculate_30_360(start_date, end_date)
    else:
        raise ValueError(f"Unsupported day count convention: {convention}")


def _calculate_act_365(start_date: date_type, end_date: date_type) -> Decimal:
    """ACT/365: Actual days / 365."""
    days = (end_date - start_date).days
    return Decimal(days) / Decimal(365)


def _calculate_act_360(start_date: date_type, end_date: date_type) -> Decimal:
    """ACT/360: Actual days / 360 (common in money markets)."""
    days = (end_date - start_date).days
    return Decimal(days) / Decimal(360)


def _calculate_act_act(start_date: date_type, end_date: date_type) -> Decimal:
    """
    ACT/ACT: Actual days / actual days in year.

    Handles leap years correctly by calculating the fraction for each year separately.
    """
    if start_date.year == end_date.year:
        # Same year - simple calculation
        days = (end_date - start_date).days
        days_in_year = 366 if calendar.isleap(start_date.year) else 365
        return Decimal(days) / Decimal(days_in_year)

    # Multiple years - calculate fraction for each year
    total_fraction = Decimal("0")
    current_year = start_date.year

    # Determine actual last year to process
    # If end_date is Jan 1, don't process that year (0 days)
    last_year = end_date.year
    if end_date.month == 1 and end_date.day == 1:
        last_year -= 1

    while current_year <= last_year:
        # Determine the actual period within this year
        if current_year == start_date.year:
            # First year: from start_date to end of year (or end_date if in same year)
            period_start = start_date
            if current_year == last_year:
                period_end = end_date
            else:
                period_end = date_type(current_year, 12, 31)
        elif current_year == last_year:
            # Last year: from start of year to end_date
            period_start = date_type(current_year, 1, 1)
            period_end = end_date
        else:
            # Middle years: full year
            period_start = date_type(current_year, 1, 1)
            period_end = date_type(current_year, 12, 31)

        days = (period_end - period_start).days
        days_in_year = 366 if calendar.isleap(current_year) else 365

        total_fraction += Decimal(days) / Decimal(days_in_year)

        # Move to next year
        current_year += 1

    return total_fraction


def _calculate_30_360(start_date: date_type, end_date: date_type) -> Decimal:
    """
    30/360: Assumes 30 days per month, 360 days per year.

    Uses the US (NASD) 30/360 convention:
    - Each month is treated as having 30 days
    - The year has 360 days
    - Special rules for end-of-month dates
    """
    d1 = start_date.day
    d2 = end_date.day
    m1 = start_date.month
    m2 = end_date.month
    y1 = start_date.year
    y2 = end_date.year

    # Apply 30/360 US (NASD) rules
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 >= 30:
        d2 = 30

    days = (y2 - y1) * 360 + (m2 - m1) * 30 + (d2 - d1)
    return Decimal(days) / Decimal(360)


# ============================================================================
# COMPOUND INTEREST CALCULATIONS
# ============================================================================

def get_compounding_periods_per_year(frequency: CompoundFrequency) -> int:
    """
    Get the number of compounding periods per year for a given frequency.

    Args:
        frequency: Compounding frequency

    Returns:
        Number of compounding periods per year

    Raises:
        ValueError: If frequency is CONTINUOUS (handled separately)
    """
    if frequency == CompoundFrequency.DAILY:
        return 365
    elif frequency == CompoundFrequency.MONTHLY:
        return 12
    elif frequency == CompoundFrequency.QUARTERLY:
        return 4
    elif frequency == CompoundFrequency.SEMIANNUAL:
        return 2
    elif frequency == CompoundFrequency.ANNUAL:
        return 1
    elif frequency == CompoundFrequency.CONTINUOUS:
        raise ValueError("CONTINUOUS compounding should be handled separately")
    else:
        raise ValueError(f"Unsupported compound frequency: {frequency}")


def calculate_compound_interest(
    principal: Decimal,
    annual_rate: Decimal,
    time_fraction: Decimal,
    frequency: CompoundFrequency
    ) -> Decimal:
    """
    Calculate compound interest for a given period.

    Formula (periodic compounding): A = P * (1 + r/n)^(n*t)
    Formula (continuous compounding): A = P * e^(r*t)

    Where:
        - P: Principal
        - r: Annual interest rate (as decimal, e.g., 0.05 for 5%)
        - n: Number of compounding periods per year
        - t: Time in years (as fraction)
        - A: Final amount (principal + interest)

    Args:
        principal: Starting principal amount
        annual_rate: Annual interest rate (e.g., 0.05 for 5%)
        time_fraction: Time period as fraction of year (from day count convention)
        frequency: Compounding frequency

    Returns:
        Interest earned (A - P)

    Example:
        >>> # €10,000 at 5% for 1 year, monthly compounding
        >>> principal = Decimal("10000")
        >>> rate = Decimal("0.05")
        >>> time = Decimal("1")  # 1 year
        >>> interest = calculate_compound_interest(principal, rate, time, CompoundFrequency.MONTHLY)
        >>> # Returns approximately €511.62
    """
    if frequency == CompoundFrequency.CONTINUOUS:
        # Continuous compounding: A = P * e^(r*t)
        exponent = float(annual_rate * time_fraction)
        multiplier = Decimal(str(math.exp(exponent)))
        final_amount = principal * multiplier
    else:
        # Periodic compounding: A = P * (1 + r/n)^(n*t)
        n = Decimal(get_compounding_periods_per_year(frequency))
        rate_per_period = annual_rate / n
        num_periods = n * time_fraction

        # (1 + r/n)^(n*t)
        base = Decimal("1") + rate_per_period
        exponent = float(num_periods)
        multiplier = Decimal(str(pow(float(base), exponent)))
        final_amount = principal * multiplier

    # Return only the interest portion (A - P)
    return final_amount - principal


def calculate_simple_interest(
    principal: Decimal,
    annual_rate: Decimal,
    time_fraction: Decimal
    ) -> Decimal:
    """
    Calculate simple interest for a given period.

    Formula: I = P * r * t

    Where:
        - P: Principal
        - r: Annual interest rate (as decimal)
        - t: Time in years (as fraction)
        - I: Interest earned

    Args:
        principal: Principal amount
        annual_rate: Annual interest rate (e.g., 0.05 for 5%)
        time_fraction: Time period as fraction of year

    Returns:
        Interest earned

    Example:
        >>> # €10,000 at 5% for 1 year
        >>> principal = Decimal("10000")
        >>> rate = Decimal("0.05")
        >>> time = Decimal("1")
        >>> interest = calculate_simple_interest(principal, rate, time)
        >>> # Returns €500
    """
    return principal * annual_rate * time_fraction


# ============================================================================
# INTEREST SCHEDULE HELPERS
# ============================================================================

def find_active_period(
    schedule: List[InterestRatePeriod],
    target_date: date_type,
    maturity_date: date_type,
    late_interest: Optional[LateInterestConfig] = None,
    ) -> Optional[InterestRatePeriod]:
    """
    Find the active interest rate period for a given date.

    Returns the full InterestRatePeriod object (with compounding, day_count, etc.)
    or constructs a late interest period if applicable.

    Logic:
    1. Search schedule for period covering target_date
    2. If past maturity but within grace period: return last schedule period
    3. If past maturity + grace period: construct period from late_interest
    4. Otherwise: return None

    Args:
        schedule: List of InterestRatePeriod objects
        target_date: Date to find period for
        maturity_date: Asset maturity date
        late_interest: Optional LateInterestConfig object

    Returns:
        InterestRatePeriod or None if no applicable period

    Example:
        >>> period = find_active_period(schedule, date(2025, 6, 15), date(2025, 12, 31))
        >>> if period:
        ...     print(f"Rate: {period.annual_rate}, Compounding: {period.compounding}")
    """
    # Step 1: Check if target_date falls within any scheduled period
    for period in schedule:
        if period.start_date <= target_date <= period.end_date:
            return period

    # Step 2: Handle dates after maturity
    if target_date > maturity_date:
        if late_interest:
            grace_end = maturity_date + timedelta(days=late_interest.grace_period_days)

            if target_date <= grace_end:
                # Within grace period: return last scheduled period
                if schedule:
                    return schedule[-1]
            else:
                # Past grace period: construct a late interest period
                # Use late_interest config to create a synthetic period
                return InterestRatePeriod(
                    start_date=grace_end + timedelta(days=1),
                    end_date=target_date,  # Extend to current date
                    annual_rate=late_interest.annual_rate,
                    compounding=late_interest.compounding,
                    compound_frequency=late_interest.compound_frequency,
                    day_count=late_interest.day_count
                    )

    # Step 3: No applicable period found
    return None


def parse_decimal_value(value) -> Optional[Decimal]:
    """
    Convert input to Decimal safely.

    Args:
        value: Input value (Decimal, int, float, str, or None)

    Returns:
        Decimal or None
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None
