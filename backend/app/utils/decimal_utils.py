"""
Decimal precision utilities for LibreFolio.

Provides functions to work with database numeric precision and decimal truncation.
All numeric columns in the database use NUMERIC(precision, scale) type.

Usage:
    from backend.app.utils.decimal_utils import get_model_column_precision, truncate_to_db_precision

    # Get precision for a column
    precision, scale = get_model_column_precision(PriceHistory, "close")
    # Returns: (18, 6)

    # Truncate a decimal to match DB precision
    value = Decimal("175.123456789")
    truncated = truncate_to_db_precision(value, PriceHistory, "close")
    # Returns: Decimal("175.123456")
"""
from decimal import Decimal, ROUND_DOWN
from typing import Type, Tuple

from sqlalchemy import Numeric
from sqlmodel import SQLModel

from backend.app.db.models import PriceHistory, FxRate


def get_model_column_precision(model: Type[SQLModel], column_name: str) -> Tuple[int, int]:
    """
    Get (precision, scale) for a numeric column from SQLModel.

    Reads the column type definition from the model to get the actual
    precision and scale values, avoiding hardcoded constants.

    Args:
        model: SQLModel class (e.g., PriceHistory, FxRate)
        column_name: Column name (e.g., "close", "rate")

    Returns:
        Tuple of (precision, scale)
        - precision: Total number of digits
        - scale: Number of decimal digits
        Example: (18, 6) means 18 total digits, 6 after decimal point

    Raises:
        ValueError: If column not found or not a Numeric type

    Example:
        >>> get_model_column_precision(PriceHistory, "close")
        (18, 6)
        >>> get_model_column_precision(FxRate, "rate")
        (24, 10)
    """
    # Get the table columns from SQLModel
    if not hasattr(model, '__table__'):
        raise ValueError(f"Model {model.__name__} has no __table__ attribute")

    table = model.__table__

    if column_name not in table.columns:
        raise ValueError(f"Column '{column_name}' not found in {model.__name__}")

    column = table.columns[column_name]
    column_type = column.type

    # Check if it's a Numeric type
    if not isinstance(column_type, Numeric):
        raise ValueError(
            f"Column '{column_name}' in {model.__name__} is not Numeric type "
            f"(found: {type(column_type).__name__})"
            )

    precision = column_type.precision
    scale = column_type.scale

    if precision is None or scale is None:
        raise ValueError(f"Column '{column_name}' in {model.__name__} has undefined precision/scale")

    return precision, scale


def truncate_to_db_precision(value: Decimal, model: Type[SQLModel], column_name: str) -> Decimal:
    """
    Truncate decimal to match database column precision.

    Prevents false update detection when re-syncing identical values.
    Database truncates on write, so we truncate before comparing or storing.

    Args:
        value: Decimal value to truncate
        model: SQLModel class (e.g., PriceHistory, FxRate)
        column_name: Column name (e.g., "close", "rate")

    Returns:
        Truncated Decimal matching DB precision

    Example:
        >>> truncate_to_db_precision(Decimal("175.123456789"), PriceHistory, "close")
        Decimal("175.123456")  # Truncated to 6 decimals (NUMERIC(18, 6))

        >>> truncate_to_db_precision(Decimal("1.0850123456"), FxRate, "rate")
        Decimal("1.0850123456")  # Kept 10 decimals (NUMERIC(24, 10))

    Note:
        Uses ROUND_DOWN to match SQLite truncation behavior.
        This ensures values match exactly what's stored in the database.
    """
    precision, scale = get_model_column_precision(model, column_name)

    # Create quantizer for the target scale
    # Example: scale=6 → quantizer=0.000001
    quantizer = Decimal(10) ** -scale

    # Truncate (round down) to match DB behavior
    return value.quantize(quantizer, rounding=ROUND_DOWN)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def truncate_priceHistory(value: Decimal, column_name: str = "close") -> Decimal:
    """Truncate value with the precision used in DB price_history.<column_name>."""
    return truncate_to_db_precision(value, PriceHistory, column_name)


def truncate_fx_rate(value: Decimal) -> Decimal:
    """Truncate value with the precision used in DB fx_rates.rate column."""
    return truncate_to_db_precision(value, FxRate, "rate")
