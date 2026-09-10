"""Exact bounded arithmetic and a presentation-only rational approximation."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, Inexact, InvalidOperation, Overflow

P1_DECIMAL_PRECISION = 256
RATIO_DECIMAL_PLACES = 28
ZERO = Decimal("0")
ONE = Decimal("1")
HUNDRED = Decimal("100")


def decimal_context() -> Context:
    return Context(prec=P1_DECIMAL_PRECISION, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999, traps=[DivisionByZero, Inexact, InvalidOperation, Overflow])


def decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise ArithmeticError("Non-finite value in PAC analysis")
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("0", "-0") else text


def ratio_approximation(numerator: Decimal, denominator: Decimal) -> tuple[str, bool]:
    if denominator <= 0:
        raise ArithmeticError("PAC ratio denominator must be positive")
    n_value, n_scale = numerator.as_integer_ratio()
    d_value, d_scale = denominator.as_integer_ratio()
    divisor = n_scale * d_value
    scaled, remainder = divmod(abs(n_value) * d_scale * 10**RATIO_DECIMAL_PLACES, divisor)
    digits = str(scaled).rjust(RATIO_DECIMAL_PLACES + 1, "0")
    whole, fraction = digits[:-RATIO_DECIMAL_PLACES], digits[-RATIO_DECIMAL_PLACES:].rstrip("0")
    text = f"{whole}.{fraction}" if fraction else whole
    if n_value < 0 and scaled != 0:
        text = f"-{text}"
    return text, remainder == 0
