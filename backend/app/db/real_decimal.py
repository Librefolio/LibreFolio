"""Decimal columns stored as an SQLite REAL that read back the decimal that was written (C-97, issue #43).

SQLite keeps the value of a ``NUMERIC`` column as a double (REAL), and SQLAlchemy's ``Numeric`` reads it back through
``'%.<scale>f'``: at scale 6 a quantity of ``0.12345678`` reads ``0.123457``, and a larger scale shows the double's noise
instead (``65000.123456`` at scale 12 reads ``65000.123456000001``). ``RealDecimal`` writes the same double and reads it
back as the shortest decimal that represents it: the decimal that was written, when it had at most
``REAL_SIGNIFICANT_DIGITS`` significant digits, which the input limits guarantee (``db/precision.decimal_limit_issue``).

Sums are never left to SQL: a ``SUM`` of REALs adds the doubles, not the decimals (``financial_math`` adds the values
read back, exactly).
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal
from typing import Any, Optional

from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator

#: The significant digits a double keeps for every decimal: what a REAL gives back exactly.
REAL_SIGNIFICANT_DIGITS = 15
#: A value with fewer decimals reads back padded to this many: the form ``Numeric(18, 6)`` gave every value before C-97.
READ_MIN_SCALE = 6

_REAL_CONTEXT = Context(prec=REAL_SIGNIFICANT_DIGITS, rounding=ROUND_HALF_EVEN)
_WIDE_CONTEXT = Context(prec=60, rounding=ROUND_HALF_EVEN)
_MIN_STEP = Decimal(1).scaleb(-READ_MIN_SCALE)


class RealDecimal(TypeDecorator):
    """A ``NUMERIC(precision, scale)`` column read back as the decimal that was written (see the module docstring).

    The value goes to SQLite as a float, as ``Numeric`` sends it. It comes back as the shortest decimal of that double
    (its ``repr``), at most ``REAL_SIGNIFICANT_DIGITS`` significant digits, rounded to ``scale`` decimals when it has
    more, and padded to ``READ_MIN_SCALE`` decimals when it has fewer: ``10`` reads ``10.000000``, as it always did.
    """

    impl = Numeric
    cache_ok = True

    def __init__(self, precision: int, scale: int) -> None:
        super().__init__(precision=precision, scale=scale, asdecimal=False)
        self._step = Decimal(1).scaleb(-scale)

    def __repr__(self) -> str:
        return f"RealDecimal(precision={self.impl_instance.precision}, scale={self.impl_instance.scale})"

    @property
    def python_type(self) -> type:
        return Decimal

    def process_result_value(self, value: Any, dialect: Any) -> Optional[Decimal]:
        """The decimal the stored double represents; SQLite answers an INTEGER for a whole value."""
        if value is None:
            return None
        result = _REAL_CONTEXT.create_decimal(repr(float(value)))
        if result.as_tuple().exponent < -self.impl_instance.scale:
            result = result.quantize(self._step, context=_WIDE_CONTEXT)
        if result.as_tuple().exponent > -READ_MIN_SCALE:
            result = result.quantize(_MIN_STEP, context=_WIDE_CONTEXT)
        return result
