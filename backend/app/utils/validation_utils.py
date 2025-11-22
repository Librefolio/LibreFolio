"""
Validation utilities for Pydantic models.

Provides reusable validator functions for common field types like currencies,
date ranges, and compound frequency configurations.
"""
from datetime import date as date_type
from typing import Optional, Any


def normalize_currency_code(v: Any) -> str:
    """
    Normalize currency code to uppercase ISO 4217 format.

    Converts lowercase/mixed case currency codes to uppercase and strips whitespace.
    This ensures consistent currency representation in the database and API responses.

    Args:
        v: Currency code string (or any type, returns as-is if not string)

    Returns:
        str: Uppercase, stripped currency code (e.g., "USD", "EUR", "GBP")

    Examples:
        >>> normalize_currency_code("usd")
        'USD'
        >>> normalize_currency_code("  eur  ")
        'EUR'
        >>> normalize_currency_code("GBP")
        'GBP'

    Note:
        Use this function in Pydantic @field_validator for all currency fields
        to ensure consistency across FA (Financial Asset) and FX schemas.
    """
    if isinstance(v, str):
        return v.upper().strip()
    return v


def validate_date_range_order(start: date_type, end: Optional[date_type]) -> None:
    """
    Validate that end date is not before start date.

    Ensures logical date range integrity by checking that end >= start when
    end is provided. Single-day ranges (end=None) are always valid.

    Args:
        start: Start date (required, inclusive)
        end: End date (optional, inclusive). None means single day.

    Raises:
        ValueError: If end < start

    Examples:
        >>> from datetime import date
        >>> validate_date_range_order(date(2025, 1, 1), date(2025, 1, 31))  # OK
        >>> validate_date_range_order(date(2025, 1, 1), None)  # OK (single day)
        >>> validate_date_range_order(date(2025, 1, 31), date(2025, 1, 1))  # ValueError

    Note:
        Use this in DateRangeModel @model_validator to ensure valid ranges
        before processing queries or deletions.
    """
    if end is not None and end < start:
        raise ValueError(
            f"end date ({end}) must be >= start date ({start})"
        )


def validate_compound_frequency(
    compounding: str,
    compound_frequency: Optional[int],
    field_name: str = "compound_frequency"
) -> None:
    """
    Validate compound frequency based on compounding type.

    Ensures that:
    - COMPOUND compounding requires a frequency value (e.g., daily=365, monthly=12)
    - SIMPLE compounding must NOT have a frequency (it's meaningless for simple interest)

    Args:
        compounding: Compounding type ("COMPOUND" or "SIMPLE")
        compound_frequency: Frequency value (e.g., 365 for daily, 12 for monthly, 1 for annual)
        field_name: Name of the frequency field (for error messages)

    Raises:
        ValueError: If COMPOUND has no frequency, or SIMPLE has a frequency

    Examples:
        >>> validate_compound_frequency("COMPOUND", 12)  # OK (monthly compounding)
        >>> validate_compound_frequency("SIMPLE", None)  # OK (simple interest)
        >>> validate_compound_frequency("COMPOUND", None)  # ValueError
        >>> validate_compound_frequency("SIMPLE", 365)  # ValueError

    Note:
        Use this in FAInterestRatePeriod and FALateInterestConfig @model_validator
        to ensure scheduled investment configurations are logically consistent.
    """
    if compounding == "COMPOUND":
        if compound_frequency is None:
            raise ValueError(
                f"{field_name} is required when compounding=COMPOUND "
                f"(e.g., 365 for daily, 12 for monthly, 1 for annual)"
            )
    elif compounding == "SIMPLE":
        if compound_frequency is not None:
            raise ValueError(
                f"{field_name} should not be set when compounding=SIMPLE "
                f"(simple interest does not use compounding frequency)"
            )

