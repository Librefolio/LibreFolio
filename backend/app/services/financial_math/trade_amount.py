"""
The amount of a trade and its unit price: one the user types, the other follows (#47, the transaction form).

A BUY or a SELL stores a quantity and an amount; the unit price is only a way of typing the amount. The two directions
use the one convention of the whole app, the market quote's: ``value = quantity / quote_base_quantity × price``
(``valuation.compute_holding_value``), so a bond quoted on base 100 is entered the way its quote is read.

The result is rounded half-even to the scale of the column that keeps it (an amount keeps 6 decimals, a price 12): a
calculated value is never a surprise at save time, the form shows exactly what will be stored. The scales are the
caller's to pass (``db/precision.py`` knows them): this module does no I/O and reads no model.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from backend.app.services.financial_math.valuation import compute_holding_value, normalize_quote_base_quantity

#: Working precision of the multiplication and the division: wider than any value the input limits let in (15 digits
#: before the point, 12 after), so the only rounding is the final one.
_WORKING_PRECISION = 80


def _round_to_scale(value: Decimal, scale: int) -> Decimal:
    """``value`` rounded half-even to ``scale`` decimals; the caller holds the working context."""
    return value.quantize(Decimal(1).scaleb(-scale), rounding=ROUND_HALF_EVEN)


def amount_from_unit_price(quantity: Decimal, unit_price: Decimal, quote_base_quantity: int | None, *, scale: int) -> Decimal:
    """The amount of ``quantity`` units bought at ``unit_price`` (per ``quote_base_quantity`` units), rounded to ``scale`` decimals."""
    with localcontext() as context:
        context.prec = _WORKING_PRECISION
        context.rounding = ROUND_HALF_EVEN
        return _round_to_scale(compute_holding_value(quantity, unit_price, quote_base_quantity), scale)


def unit_price_from_amount(quantity: Decimal, amount: Decimal, quote_base_quantity: int | None, *, scale: int) -> Decimal:
    """The unit price (per ``quote_base_quantity`` units) that ``amount`` paid for ``quantity`` units, rounded to ``scale`` decimals.

    Raises ``ZeroDivisionError`` for a zero quantity: no price is behind an amount paid for nothing.
    """
    if quantity == 0:
        raise ZeroDivisionError("no unit price is behind an amount paid for a zero quantity")
    with localcontext() as context:
        context.prec = _WORKING_PRECISION
        context.rounding = ROUND_HALF_EVEN
        base = Decimal(normalize_quote_base_quantity(quote_base_quantity))
        return _round_to_scale(amount * base / quantity, scale)
