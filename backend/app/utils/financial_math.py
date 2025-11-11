"""
Financial mathematics utility functions.

Provides day count conventions, interest calculations, and other
financial formulas used across the application.

All functions are pure (no side effects) and reusable.

Key concepts:
- Day count convention: ACT/365 (Actual/365 Fixed)
- Interest type: SIMPLE interest (not compound)
- Rate format: Annual rate as Decimal (0.05 = 5%)

Note:
    All functions require Pydantic models from backend.app.schemas.assets.
    To convert from dict/JSON, use: InterestRatePeriod(**dict_data)
    To get dict/JSON from model: model.dict() or model.json()
"""
from datetime import date as date_type, timedelta
from decimal import Decimal
from typing import Optional, List

from backend.app.schemas.assets import InterestRatePeriod, LateInterestConfig


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
    schedule: List[InterestRatePeriod],
    target_date: date_type,
    maturity_date: date_type,
    late_interest: Optional[LateInterestConfig] = None,
    ) -> Decimal:
    """
    Find and return the daily interest rate for target date from schedule+late_interest.
    To have a full calculation in a period, call this function for each day in the period.

    Logic:
    1. Search schedule for rate covering target_date
    2. If past maturity but within grace period: use last schedule rate
    3. If past maturity + grace period: use late_interest rate
    4. Otherwise: return 0%

    Args:
        schedule: List of InterestRatePeriod objects
            Use InterestRatePeriod(start_date, end_date, rate) or
            InterestRatePeriod(**dict_data) to convert from dict/JSON

        target_date: Date to find rate for
        maturity_date: Asset maturity date
        late_interest: Optional LateInterestConfig object
            Use LateInterestConfig(rate, grace_period_days) or
            LateInterestConfig(**dict_data) to convert from dict/JSON

    Returns:
        Annual interest rate as Decimal (e.g., Decimal("0.05") for 5%)

    Example:
        >>> from backend.app.schemas.assets import InterestRatePeriod
        >>> schedule = [InterestRatePeriod(
        ...     start_date=date(2025, 1, 1),
        ...     end_date=date(2025, 12, 31),
        ...     rate=Decimal("0.05")
        ... )]
        >>> find_active_rate(schedule, date(2025, 6, 15), date(2025, 12, 31), None)
        Decimal('0.05')

    Note:
        To convert from dict: InterestRatePeriod(**dict_data)
        To convert from JSON: InterestRatePeriod.parse_raw(json_string)
    """
    # Step 1: Check if target_date falls within any scheduled period
    # This covers the normal case where the asset is still within its defined rate schedule
    for period in schedule:
        if period.start_date <= target_date <= period.end_date:
            return period.rate

    # Step 2: Handle dates after maturity
    # This covers late payments, defaults, or extended holding periods
    if target_date > maturity_date:
        if late_interest:
            # Calculate when grace period ends
            grace_end = maturity_date + timedelta(days=late_interest.grace_period_days)

            if target_date <= grace_end:
                # Within grace period: continue using last scheduled rate
                # This gives borrower time to repay without penalty
                if schedule:
                    return schedule[-1].rate
            else:
                # Past grace period: apply late interest penalty rate
                # This incentivizes timely repayment
                return late_interest.rate

    # Step 3: No applicable rate found
    # This happens for dates before schedule starts or after maturity with no late interest
    return Decimal("0")


def calculate_accrued_interest(
    face_value: Decimal,
    start_date: date_type,
    end_date: date_type,
    schedule: List[InterestRatePeriod],
    maturity_date: date_type,
    late_interest: Optional[LateInterestConfig] = None,
    ) -> Decimal:
    """
    Calculate accrued SIMPLE interest from start to end date.

    Formula (SIMPLE interest):
        interest = principal * sum(rate_i * time_fraction_i)

    Note: principal (face_value) in the SIMPLE interest formula is the principal amount
          at the beginning of the calculation period.

    Where:
        - rate_i: Annual interest rate for period i
        - time_fraction_i: Days in period i / 365 (ACT/365)

    Args:
        face_value: Principal amount
        start_date: Calculation start date
        end_date: Calculation end date (inclusive)
        schedule: List of InterestRatePeriod objects
            Use [InterestRatePeriod(**item) for item in dict_list] to convert
        maturity_date: Asset maturity date
        late_interest: Optional LateInterestConfig object
            Use LateInterestConfig(**dict_data) to convert from dict

    Returns:
        Total accrued interest as Decimal

    Example:
        >>> from backend.app.schemas.assets import InterestRatePeriod
        >>> face_value = Decimal("10000")
        >>> schedule = [InterestRatePeriod(
        ...     start_date=date(2025, 1, 1),
        ...     end_date=date(2025, 12, 31),
        ...     rate=Decimal("0.05")
        ... )]
        >>> interest = calculate_accrued_interest(
        ...     face_value, date(2025, 1, 1), date(2025, 1, 30),
        ...     schedule, date(2025, 12, 31), None
        ... )
        >>> # Returns approximately 41.10 (10000 * 0.05 * 30/365)

    Note:
        Uses day-by-day iteration to handle rate changes correctly.
        ACT/365 day count convention is used.

        To convert from dict list:
        schedule = [InterestRatePeriod(**item) for item in dict_list]
    """
    total_interest = Decimal("0")
    current_date = start_date

    # Iterate through each day in the period
    # This approach handles rate changes mid-calculation correctly
    # Example: If rate changes from 5% to 6% on July 1st,
    # days before July 1st use 5%, days after use 6%
    while current_date <= end_date:
        # Find the applicable rate for this specific day
        # Handles: normal schedule, grace period, late interest
        rate = find_active_rate(schedule, current_date, maturity_date, late_interest)

        # Calculate interest for this single day
        # Formula: principal * (annual_rate / 365)
        # Using ACT/365: each day is exactly 1/365 of the year
        daily_interest = face_value * rate / Decimal(365)
        total_interest += daily_interest

        # Move to next day
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
