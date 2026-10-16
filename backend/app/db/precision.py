"""
Database numeric precision for LibreFolio.

Provides functions to work with database numeric precision, decimal truncation and the input limits.
All numeric columns in the database are declared NUMERIC(precision, scale); quantities and prices use
``RealDecimal`` (``db/real_decimal.py``), which reads back the decimal written, at most 15 significant digits.

Usage:
    from backend.app.db.precision import get_model_column_precision, truncate_to_db_precision

    # Get precision for a column
    precision, scale = get_model_column_precision(PriceHistory, "close")
    # Returns: (24, 12)

    # Truncate a decimal to match DB precision
    value = Decimal("175.12345678901234")
    truncated = truncate_to_db_precision(value, PriceHistory, "close")
    # Returns: Decimal("175.123456789012")
"""

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Context, Decimal
from typing import Optional, Tuple, Type

from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator
from sqlmodel import SQLModel

from backend.app.db.models import FxRate, PriceHistory
from backend.app.db.real_decimal import REAL_SIGNIFICANT_DIGITS, RealDecimal

#: The codes of ``decimal_limit_issue``: the same values as ``TXValidationCode`` (schemas/transactions/batch.py).
DECIMAL_PLACES_EXCEEDED = "decimalPlacesExceeded"
SIGNIFICANT_DIGITS_EXCEEDED = "significantDigitsExceeded"

_WIDE_CONTEXT = Context(prec=60)
_REAL_DOWN = Context(prec=REAL_SIGNIFICANT_DIGITS, rounding=ROUND_DOWN)
_REAL_HALF_EVEN = Context(prec=REAL_SIGNIFICANT_DIGITS, rounding=ROUND_HALF_EVEN)


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
        (24, 12)
        >>> get_model_column_precision(FxRate, "rate")
        (24, 10)
    """
    # Get the table columns from SQLModel
    # Valid SQLModel/SQLAlchemy models always have __table__ after definition
    try:
        table = model.__table__
    except AttributeError:
        raise ValueError(f"Model {model.__name__} is not a valid SQLModel/SQLAlchemy model (no __table__)") from None

    if column_name not in table.columns:
        raise ValueError(f"Column '{column_name}' not found in {model.__name__}")

    column = table.columns[column_name]
    column_type = column.type
    # A RealDecimal (C-97) declares its precision and scale on the Numeric it decorates.
    if isinstance(column_type, TypeDecorator):
        column_type = column_type.impl_instance

    # Check if it's a Numeric type
    if not isinstance(column_type, Numeric):
        raise ValueError(f"Column '{column_name}' in {model.__name__} is not Numeric type " f"(found: {type(column_type).__name__})")

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
        >>> truncate_to_db_precision(Decimal("175.12345678901234"), PriceHistory, "close")
        Decimal("175.123456789012")  # 12 decimals and 15 significant digits (RealDecimal(24, 12))

        >>> truncate_to_db_precision(Decimal("1.0850123456"), FxRate, "rate")
        Decimal("1.0850123456")  # Kept 10 decimals (NUMERIC(24, 10))

    Note:
        Uses ROUND_DOWN to match SQLite truncation behavior.
        This ensures values match exactly what's stored in the database.
        On a ``RealDecimal`` column the value also keeps at most ``REAL_SIGNIFICANT_DIGITS`` significant digits
        (ROUND_DOWN): the column reads back no more, so what is written is what is read back (C-97).
    """
    precision, scale = get_model_column_precision(model, column_name)

    # Create quantizer for the target scale
    # Example: scale=6 → quantizer=0.000001
    quantizer = Decimal(10) ** -scale

    # Truncate (round down) to match DB behavior
    truncated = value.quantize(quantizer, rounding=ROUND_DOWN, context=_WIDE_CONTEXT)
    if isinstance(model.__table__.columns[column_name].type, RealDecimal):
        truncated = _REAL_DOWN.plus(truncated)
    return truncated


def round_computed_value(value: Decimal, model: Type[SQLModel], column_name: str) -> Decimal:
    """A value that was COMPUTED (a quotient, a product), rounded to what the column keeps: C-97, decision D6.

    ``ROUND_HALF_EVEN`` to the column scale and, on a ``RealDecimal`` column, to ``REAL_SIGNIFICANT_DIGITS``
    significant digits: the result always passes ``decimal_limit_issue``. For the values a plugin derives, such as a
    per-unit cost from a total and a quantity (1000 / 3 → 333.333333333333). Never for a value the user typed or a
    file holds: over the limit those are refused, never rounded (decision D2).

    A value that already fits comes back as it is, its form included: ``100.00 / 100`` stays ``1.00``, not
    ``1.000000000000`` (the import shows it as computed, and the parse output stays what it was).
    """
    _precision, scale = get_model_column_precision(model, column_name)
    exponent = value.as_tuple().exponent
    rounded = value
    if not isinstance(exponent, int) or -exponent > scale:
        rounded = value.quantize(Decimal(1).scaleb(-scale), rounding=ROUND_HALF_EVEN, context=_WIDE_CONTEXT)
    if isinstance(model.__table__.columns[column_name].type, RealDecimal):
        rounded = _REAL_HALF_EVEN.plus(rounded)
    return rounded


def decimal_limit_issue(value: Decimal, model: Type[SQLModel], column_name: str) -> Optional[Tuple[str, int]]:
    """What keeps ``value`` out of the column, or None: the input limit of C-97 (issue #43), never a rounding.

    ``(DECIMAL_PLACES_EXCEEDED, scale)`` when its decimals, trailing zeros not counted, exceed the column scale (a
    quantity keeps 10, a price and a per-unit cost basis 12, an amount 6); otherwise ``(SIGNIFICANT_DIGITS_EXCEEDED, 15)`` when it has more
    significant digits than a REAL gives back (``REAL_SIGNIFICANT_DIGITS``, decision D1). The scale is the model's.
    """
    _precision, scale = get_model_column_precision(model, column_name)
    _sign, digits, exponent = value.normalize(_WIDE_CONTEXT).as_tuple()
    if not isinstance(exponent, int):
        return None
    if -exponent > scale:
        return DECIMAL_PLACES_EXCEEDED, scale
    if len(digits) > REAL_SIGNIFICANT_DIGITS:
        return SIGNIFICANT_DIGITS_EXCEEDED, REAL_SIGNIFICANT_DIGITS
    return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def truncate_priceHistory(value: Decimal, column_name: str = "close") -> Decimal:
    """Truncate value with the precision used in DB price_history.<column_name>."""
    return truncate_to_db_precision(value, PriceHistory, column_name)


def truncate_fx_rate(value: Decimal) -> Decimal:
    """Truncate value with the precision used in DB fx_rates.rate column."""
    return truncate_to_db_precision(value, FxRate, "rate")
