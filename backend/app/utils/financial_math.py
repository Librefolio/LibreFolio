"""
Financial mathematics utility functions.

Provides day count conventions, interest calculations, and other
financial formulas used across the application.

All functions are pure (no side effects) and reusable.
"""
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional


# ============================================================================
# DAY COUNT CONVENTIONS
# ============================================================================


def calculate_daily_factor_between_act365(start_date: date_type, end_date: date_type) -> Decimal:
    """
    Calculate day fraction using ACT/365 day count convention.

    Formula: (actual_days) / 365

    Args:
        start_date: Start date (inclusive)
        end_date: End date (inclusive)

    Returns:
        Decimal fraction representing the time period

    Example:
        >>> calculate_daily_factor_between_act365(date(2025, 1, 1), date(2025, 1, 31))
        Decimal('0.0821917808219178082191780821917808')  # 30 days / 365

    Note:
        ACT/365 is used for simplicity and is standard in many markets.
        This is an estimate for valuation purposes.
    """
    days = (end_date - start_date).days
    return Decimal(days) / Decimal(365)


def find_active_rate(
    schedule: list[dict],
    target_date: date_type,
    maturity_date: date_type,
    late_interest: Optional[dict],
    ) -> Decimal:
    """
    Find applicable interest rate for target date from schedule.

    Logic:
    1. Search schedule for rate covering target_date
    2. If past maturity but within grace period: use last schedule rate
    3. If past maturity + grace period: use late_interest rate
    4. Otherwise: return 0%

    Args:
        schedule: List of rate periods
            Format: [{start_date, end_date, rate}, ...]
            Dates can be strings (ISO "YYYY-MM-DD") or date objects
            Rate is annual rate as string or Decimal (e.g., "0.05" for 5%)
        target_date: Date to find rate for
        maturity_date: Asset maturity date
        late_interest: Late interest configuration
            Format: {rate, grace_period_days}

    Returns:
        Annual interest rate as Decimal (e.g., Decimal("0.05") for 5%)
    """
    # Check if within schedule
    for period in schedule:
        # Convert string dates to date objects if needed
        start_raw = period["start_date"]
        end_raw = period["end_date"]

        if isinstance(start_raw, str):
            start = date_type.fromisoformat(start_raw)
        else:
            start = start_raw

        if isinstance(end_raw, str):
            end = date_type.fromisoformat(end_raw)
        else:
            end = end_raw

        if start <= target_date <= end:
            return Decimal(str(period["rate"]))

    # Check if past maturity
    if target_date > maturity_date:
        if late_interest:
            grace_days = late_interest.get("grace_period_days", 0)
            grace_end = maturity_date + timedelta(days=grace_days)

            if target_date <= grace_end:
                # Within grace period: use last schedule rate
                if schedule:
                    last_period = schedule[-1]
                    return Decimal(str(last_period["rate"]))
            else:
                # Past grace period: use late interest rate
                return Decimal(str(late_interest["rate"]))

    # No applicable rate
    return Decimal("0")


def calculate_accrued_interest(
    face_value: Decimal,
    start_date: date_type,
    end_date: date_type,
    schedule: list[dict],
    maturity_date: date_type,
    late_interest: Optional[dict],
) -> Decimal:
    """
    Calculate accrued SIMPLE interest from start to end date.

    Formula (SIMPLE interest):
        interest = principal * sum(rate_i * time_fraction_i)

    Where:
        - rate_i: Annual interest rate for period i
        - time_fraction_i: Days in period i / 365 (ACT/365)

    Args:
        face_value: Principal amount
        start_date: Calculation start date
        end_date: Calculation end date (inclusive)
        schedule: Interest rate schedule (see find_active_rate for format)
        maturity_date: Asset maturity date
        late_interest: Late interest configuration

    Returns:
        Total accrued interest as Decimal

    Note:
        Uses day-by-day iteration to handle rate changes correctly.
        ACT/365 day count convention is used.
    """
    total_interest = Decimal("0")
    current_date = start_date

    while current_date <= end_date:
        # Find rate for this day
        rate = find_active_rate(schedule, current_date, maturity_date, late_interest)

        # Calculate daily interest: principal * (rate / 365)
        daily_interest = face_value * rate / Decimal(365)
        total_interest += daily_interest

        current_date += timedelta(days=1)

    return total_interest


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
