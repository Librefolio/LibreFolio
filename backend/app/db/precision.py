"""
Database numeric precision for LibreFolio.

Provides functions to work with database numeric precision, decimal truncation and the input limits.
All numeric columns in the database are declared NUMERIC(precision, scale); quantities, amounts, event values and
prices use ``RealDecimal`` (``db/real_decimal.py``; amounts and event values since W-B60), which reads back the decimal
written, at most 15 significant digits.

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
INTEGER_DIGITS_EXCEEDED = "integerDigitsExceeded"

#: The digits before the decimal point of a quantity and of a transaction amount (night decision N63, 17/10/2026): 15,
#: as many as a REAL gives back, not the 12 their declarations leave (``RealDecimal(22, 10)``, ``RealDecimal(18, 6)``). A
#: thousand billion VND or IDR is a real amount, and release 1.2, which never enforced the declarations on SQLite, may
#: hold such data already. Every other column keeps the digits it declares (``max_integer_digits``).
_INTEGER_DIGITS_BY_COLUMN = {("transactions", "quantity"): REAL_SIGNIFICANT_DIGITS, ("transactions", "amount"): REAL_SIGNIFICANT_DIGITS}

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
    significant digits: the result passes the decimal places of ``decimal_limit_issue`` and, on a ``RealDecimal``
    column, its significant digits too (on a plain ``Numeric`` column, an FX rate, ``123456789.12345678912`` becomes
    ``123456789.1234567891``, still 19 significant digits); never its digits before the decimal point (W-B58), which no
    rounding can bring back. For the values a plugin derives, such as a
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


def _digit_counts(value: Decimal) -> Optional[Tuple[int, int, int]]:
    """``(decimal places, significant digits, integer digits)`` of ``value``, trailing zeros not counted; None when it is
    not finite. Read from its digits, never through a context, so nothing rounds, overflows or underflows:
    ``1E+1000000`` has 1 000 001 integer digits, ``1E-2000000`` 2 000 000 decimal places (W-B58).
    """
    if not value.is_finite():
        return None
    _sign, digits, exponent = value.as_tuple()
    kept = len(digits)
    while kept > 1 and digits[kept - 1] == 0:
        kept -= 1
    exponent += len(digits) - kept
    if digits[:kept] == (0,):
        return 0, 1, 0
    return max(0, -exponent), kept, max(0, kept + exponent)


def max_integer_digits(model: Type[SQLModel], column_name: str) -> int:
    """The digits before the decimal point a value of the column may have (W-B58): 15 for a quantity and a transaction
    amount (decision N63), otherwise what the column declares, precision − scale (12 for a price, a per-unit cost basis
    and an event value, 24 for a volume).
    """
    precision, scale = get_model_column_precision(model, column_name)
    return _INTEGER_DIGITS_BY_COLUMN.get((model.__tablename__, column_name), precision - scale)


def integer_digits_issue(value: Decimal, model: Type[SQLModel], column_name: str) -> Optional[Tuple[str, int]]:
    """``(INTEGER_DIGITS_EXCEEDED, max_integer_digits)`` when ``value`` is not finite or has more digits before the
    decimal point than the column takes, otherwise None: the size limit alone (W-B58). For a value whose decimals are
    not refused (a volume, a count) and for a provider's value before it is truncated (``storable_value``).
    """
    maximum = max_integer_digits(model, column_name)
    counts = _digit_counts(value)
    if counts is None or counts[2] > maximum:
        return INTEGER_DIGITS_EXCEEDED, maximum
    return None


def decimal_limit_issue(value: Decimal, model: Type[SQLModel], column_name: str) -> Optional[Tuple[str, int]]:
    """What keeps ``value`` out of the column, or None: the input limit of C-97 (issue #43), never a rounding.

    ``(DECIMAL_PLACES_EXCEEDED, scale)`` when its decimals, trailing zeros not counted, exceed the column scale (a
    quantity keeps 10, a price and a per-unit cost basis 12, an amount 6); otherwise ``(SIGNIFICANT_DIGITS_EXCEEDED, 15)`` when it has more
    significant digits than a REAL gives back (``REAL_SIGNIFICANT_DIGITS``, decision D1); otherwise
    ``(INTEGER_DIGITS_EXCEEDED, max_integer_digits)`` when it has more digits before the decimal point than the column
    takes (15 for a quantity and an amount, decision N63; the declared ones elsewhere), or is not finite (W-B58:
    ``1E+60``, one digit and no decimals, passed, and past 1.8e308 a double is infinite). The order keeps the answers of
    C-97a: a value over two limits names the first. The scale is the model's; the digits are counted without a context
    (``_digit_counts``), so ``1E+1000000`` and ``1E-2000000`` are refused, never an overflow or a zero.
    """
    _precision, scale = get_model_column_precision(model, column_name)
    maximum = max_integer_digits(model, column_name)
    counts = _digit_counts(value)
    if counts is None:
        return INTEGER_DIGITS_EXCEEDED, maximum
    places, significant, integer = counts
    if places > scale:
        return DECIMAL_PLACES_EXCEEDED, scale
    if significant > REAL_SIGNIFICANT_DIGITS:
        return SIGNIFICANT_DIGITS_EXCEEDED, REAL_SIGNIFICANT_DIGITS
    if integer > maximum:
        return INTEGER_DIGITS_EXCEEDED, maximum
    return None


def storable_value(value: Decimal, model: Type[SQLModel], column_name: str) -> Optional[Decimal]:
    """A provider's value as the column keeps it (``truncate_to_db_precision``), or None when no truncation makes it fit:
    not finite, or more digits before the decimal point than the column takes (W-B58). Never raises; the caller skips a
    None and says so. Within those digits the truncation needs at most 15 + 12 digits, far from its context's 60.
    """
    if integer_digits_issue(value, model, column_name) is not None:
        return None
    return truncate_to_db_precision(value, model, column_name)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def truncate_priceHistory(value: Decimal, column_name: str = "close") -> Decimal:
    """Truncate value with the precision used in DB price_history.<column_name>."""
    return truncate_to_db_precision(value, PriceHistory, column_name)


def storable_price(value: Decimal, column_name: str = "close") -> Optional[Decimal]:
    """A provider's price as ``price_history.<column_name>`` keeps it (``truncate_priceHistory``), or None when it cannot:
    not finite, more integer digits than the column declares, or — a close — above zero and truncated to zero (``1E-13``
    at 12 decimal places: a close is never 0, and returns divide by it). W-B58.
    """
    stored = storable_value(value, PriceHistory, column_name)
    if stored is None or (column_name == "close" and stored == 0 and value != 0):
        return None
    return stored


def truncate_fx_rate(value: Decimal) -> Decimal:
    """Truncate value with the precision used in DB fx_rates.rate column."""
    return truncate_to_db_precision(value, FxRate, "rate")


def storable_fx_rate(value: Decimal) -> Optional[Decimal]:
    """An exchange rate as ``fx_rates.rate`` keeps it (``truncate_fx_rate``), or None when it cannot (X-R38, the FX side
    of W-B58): not finite, more digits before the decimal point than the column declares (``max_integer_digits``: 14),
    or 0 once truncated to its 10 decimal places (a rate is never 0: its inverse and the conversions divide by it).
    Never raises; a negative rate is the caller's business (``upsert_rates_bulk`` refuses it).

    The double SQLite keeps must stay below ``1E+14`` too (X-R50): a rate within about 0.008 of it, with more digits than
    a double holds (``99999999999999.995``), has 14 digits before the point but is written as ``1E+14``, which every
    read skips as unusable (``usable_fx_rate_bounds``); it is refused here, never answered «inserted».
    """
    stored = storable_value(value, FxRate, "rate")
    if stored is None or stored == 0 or float(stored) >= float(usable_fx_rate_bounds()[1]):
        return None
    return stored


def fx_rate_limits_text() -> str:
    """``fx_rates.rate``'s limits in words, read from the model, for a refusal or a warning (X-R38). The bound below
    ``1E+14`` is said too (X-R51): a rate of 14 digits within about 0.008 of it is refused (X-R50), and «at most 14
    digits» alone did not say why."""
    _precision, scale = get_model_column_precision(FxRate, "rate")
    first_refused = usable_fx_rate_bounds()[1]
    return f"an exchange rate keeps at most {max_integer_digits(FxRate, 'rate')} digits before the decimal point and {scale} decimal places, stays below {first_refused:f} (as the database stores it), and must stay above 0 once cut to them"


def usable_fx_rate_bounds() -> Tuple[Decimal, Decimal]:
    """``(smallest, first refused)``, ``1E-10`` and ``1E+14``: a stored rate ``storable_fx_rate`` keeps is at least the first
    and below the second (X-R38). For the SQL of the reads, which skip a legacy rate outside them (an infinite one, 0,
    ``1e19``) as a missing rate.
    """
    _precision, scale = get_model_column_precision(FxRate, "rate")
    return Decimal(1).scaleb(-scale), Decimal(1).scaleb(max_integer_digits(FxRate, "rate"))
