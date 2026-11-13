"""The table «maximum acceptable cost» of the Rebalancer's target fidelity (decisioni-REB §7.3, §11.2; B4 of project 67).

A plan scores ``J = λ·D/F + (F − W)``. Moving ``d`` misplaced euros back to their target shortens the distance ``D`` by about
``2·d²`` (``d`` from one item to another), so a plan accepts to spend up to ``2·λ·d²/F`` for it: that is the table the
strategy step shows, one row per amount of misplaced money and one column per fidelity level. The rows are 1 %, 2.5 %, 5 %
and 10 % of the plan's total, rounded to two significant digits; the reference row is the 5 % one, and the «custom»
fidelity turns the euros typed on it into ``λ`` with the figure **shown** in that row, never the exact 5 %.

Every function is generic on the number type, like ``fx_rates.oriented_rate``: the caller's ``Decimal``, ``Fraction`` or the
PAC's ``ExactRatio`` comes back in kind. The frontend computes none of this (N1): it reads the preview.
"""

from __future__ import annotations

from fractions import Fraction

__all__ = ["REFERENCE_ROW_INDEX", "acceptable_cost_rows", "lambda_from_reference_amount", "max_acceptable_cost", "two_significant_digits"]

# The rows' shares of the plan's total: 1 %, 2.5 %, 5 %, 10 % (§7.3). The reference row is the 5 % one.
_ROW_SHARES = (Fraction(1, 100), Fraction(1, 40), Fraction(1, 20), Fraction(1, 10))
REFERENCE_ROW_INDEX = 2


def _as_fraction(value) -> Fraction:
    numerator, denominator = value.as_integer_ratio()
    return Fraction(numerator, denominator)


def _like[N](value: N, fraction: Fraction) -> N:
    """``fraction`` in the number type of ``value``."""
    kind = type(value)
    return kind(fraction.numerator) / kind(fraction.denominator)


def two_significant_digits[N](value: N) -> N:
    """``value`` rounded to two significant digits, half up (134.57 → 130, 335 → 340, 995 → 1 000); zero stays zero. A
    negative value is refused: the table's rows are amounts of misplaced money."""
    exact = _as_fraction(value)
    if exact < 0:
        raise ValueError("two significant digits of a negative amount")
    if exact == 0:
        return value
    scale = Fraction(1)
    while exact / scale >= 100:
        scale *= 10
    while exact / scale < 10:
        scale /= 10
    mantissa = exact / scale
    rounded = int(mantissa) + (1 if mantissa - int(mantissa) >= Fraction(1, 2) else 0)
    return _like(value, rounded * scale)


def acceptable_cost_rows[N](total: N) -> tuple[N, ...]:
    """The table's four rows of misplaced money on ``total``: 1 %, 2.5 %, 5 %, 10 %, each to two significant digits."""
    exact = _as_fraction(total)
    return tuple(two_significant_digits(_like(total, exact * share)) for share in _ROW_SHARES)


def max_acceptable_cost[N](distance_weight: N, misplaced: N, total: N) -> N:
    """``2·λ·d²/F``: the most a plan accepts to spend to put ``misplaced`` euros back, at fidelity ``λ``, on a total ``F``."""
    return 2 * distance_weight * misplaced * misplaced / total


def lambda_from_reference_amount[N](amount: N, total: N, reference: N) -> N:
    """``x·F / (2·d_ref²)``: the ``λ`` that accepts to spend ``amount`` to put the reference row's ``reference`` euros back;
    ``reference`` is the figure shown in the row."""
    return amount * total / (2 * reference * reference)
