"""
Validation utilities for Pydantic models.

Provides reusable validator functions for common field types like
date ranges and compound frequency configurations.

Note: Currency validation is now handled by Currency.validate_code()
in backend.app.schemas.common
"""
from typing import Optional


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
