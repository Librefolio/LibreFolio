"""Decimal columns stored as an SQLite REAL that read back the decimal that was written (C-97, issue #43).

SQLite keeps the value of a ``NUMERIC`` column as a double (REAL), and SQLAlchemy's ``Numeric`` reads it back through
``'%.<scale>f'``: at scale 6 a quantity of ``0.12345678`` reads ``0.123457``, and a larger scale shows the double's noise
instead (``65000.123456`` at scale 12 reads ``65000.123456000001``). ``RealDecimal`` writes the same double and reads it
back as the shortest decimal that represents it: the decimal that was written, when it had at most
``REAL_SIGNIFICANT_DIGITS`` significant digits, which the input limits guarantee (``db/precision.decimal_limit_issue``).

Sums are never left to SQL: a ``SUM`` of REALs adds the doubles, not the decimals (``financial_math`` adds the values
read back, exactly).

Reading never raises (W-B58, E's review R13-SEC2): one row that cannot be read would take down every listing that loads
it, for every user. A stored double that is not finite (±inf: a value past 1.8e308, written before the input limits or
by hand) reads back as ``None``, logged once per process; the row loads, and can be deleted. A finite double of any size
reads back exactly, even one past the column's integer digits: a database of release 1.2 never enforced them, and
reading such a quantity as ``None`` would erase a position. Writing a value that a double cannot hold (it would become
±inf) raises ``ValueError``: whoever writes, nothing infinite is stored.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Context, Decimal
from typing import Any, Optional

from sqlalchemy import Numeric
from sqlalchemy.types import TypeDecorator

from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: The significant digits a double keeps for every decimal: what a REAL gives back exactly.
REAL_SIGNIFICANT_DIGITS = 15
#: A value with fewer decimals reads back padded to this many: the form ``Numeric(18, 6)`` gave every value before C-97.
READ_MIN_SCALE = 6

_REAL_CONTEXT = Context(prec=REAL_SIGNIFICANT_DIGITS, rounding=ROUND_HALF_EVEN)
_WIDE_PRECISION = 60
_WIDE_CONTEXT = Context(prec=_WIDE_PRECISION, rounding=ROUND_HALF_EVEN)
_MIN_STEP = Decimal(1).scaleb(-READ_MIN_SCALE)
_non_finite_logged = False


def _padding_context(value: Decimal) -> Context:
    """A context wide enough to pad ``value`` to ``READ_MIN_SCALE`` decimals without rounding it: a double has up to 309
    integer digits, past the 60 of ``_WIDE_CONTEXT`` from 1e54 up."""
    return Context(prec=max(_WIDE_PRECISION, value.adjusted() + 1 + READ_MIN_SCALE), rounding=ROUND_HALF_EVEN)


def _as_double(value: Any) -> float:
    """``value`` as a double; NaN for one that is no number at all (a signaling NaN, a text): never raises."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _log_non_finite(column_type: RealDecimal, stored: Any) -> None:
    """Say once per process that a stored value reads as ``None``: a listing would repeat it at every request."""
    global _non_finite_logged
    if _non_finite_logged:
        return
    _non_finite_logged = True
    logger.warning(
        "A stored decimal is not a finite number: it reads as no value. Find the row and correct or delete it",
        column_type=repr(column_type),
        stored=repr(stored),
    )


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

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        """The value as ``Numeric`` sends it, a double; one that a double cannot hold is refused (W-B58).

        Raises:
            ValueError: ``value`` is not finite as a double (``Decimal("1E+400")`` would be stored as inf).
        """
        if value is not None and not math.isfinite(_as_double(value)):
            raise ValueError(f"{self!r}: {value} is not finite as a double, so it cannot be stored")
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Optional[Decimal]:
        """The decimal the stored double represents; SQLite answers an INTEGER for a whole value. Never raises.

        ``None`` for a double that is not finite, or a stored value that is no number at all (logged once per process); the
        exact decimal for a finite double of any size.
        """
        if value is None:
            return None
        number = _as_double(value)
        if not math.isfinite(number):
            _log_non_finite(self, value)
            return None
        result = _REAL_CONTEXT.create_decimal(repr(number))
        if result.as_tuple().exponent < -self.impl_instance.scale:
            result = result.quantize(self._step, context=_WIDE_CONTEXT)
        if result.as_tuple().exponent > -READ_MIN_SCALE:
            result = result.quantize(_MIN_STEP, context=_padding_context(result))
        return result
