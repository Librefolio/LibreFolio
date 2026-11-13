"""B4 of project 67: the table «maximum acceptable cost» of the Rebalancer's fidelity (decisioni-REB §7.3, §11.2).

Module under test: ``backend/app/services/financial_math/acceptable_cost.py``. Three pure formulas, generic on the number
type like ``fx_rates.oriented_rate`` (``Decimal``, ``Fraction``, the PAC's ``ExactRatio``):

* ``two_significant_digits(value)``: the rows of the table are 1 %, 2.5 %, 5 % and 10 % of the plan's total, rounded to two
  significant digits (on 13 457 €: 130, 340, 670, 1 300);
* ``max_acceptable_cost(λ, d, F) = 2·λ·d²/F``: what a plan may spend at most to put ``d`` misplaced euros back;
* ``lambda_from_reference_amount(x, F, d_ref) = x·F / (2·d_ref²)``: the «custom» ``λ`` from the euros typed on the
  reference row, with ``d_ref`` the figure **shown** in the row.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest

from backend.app.services.financial_math.acceptable_cost import (
    acceptable_cost_rows,
    lambda_from_reference_amount,
    max_acceptable_cost,
    two_significant_digits,
)
from backend.app.services.pac_allocator.numeric import ExactRatio as R


@pytest.mark.parametrize(
    ("total", "rows"),
    [
        pytest.param(Decimal("13457"), (Decimal("130"), Decimal("340"), Decimal("670"), Decimal("1300")), id="13457"),
        pytest.param(Decimal("20000"), (Decimal("200"), Decimal("500"), Decimal("1000"), Decimal("2000")), id="20000"),
        pytest.param(Fraction(13_457), (Fraction(130), Fraction(340), Fraction(670), Fraction(1_300)), id="fraction"),
        pytest.param(R(13_457), (R(130), R(340), R(670), R(1_300)), id="exact-ratio"),
        # Below 100 €: the rows keep two significant digits, cents included (1 % of 57.30 is 0.573 → 0.57).
        pytest.param(Decimal("57.30"), (Decimal("0.57"), Decimal("1.4"), Decimal("2.9"), Decimal("5.7")), id="under-a-hundred"),
    ],
)
def test_two_significant_digits_rounds_the_reference_rows(total, rows) -> None:
    """B4 test 1: the four rows of the table, rounded to two significant digits, in the caller's number type."""
    assert acceptable_cost_rows(total) == rows
    assert all(type(row) is type(total) for row in acceptable_cost_rows(total))


@pytest.mark.parametrize(
    ("value", "rounded"),
    [
        pytest.param(Fraction(13_457, 100), Fraction(130), id="134.57"),
        pytest.param(Fraction(336_425, 1_000), Fraction(340), id="336.425"),
        pytest.param(Fraction(335), Fraction(340), id="half-goes-up"),
        pytest.param(Fraction(995), Fraction(1_000), id="carries-to-a-new-digit"),
        pytest.param(Fraction(7), Fraction(7), id="one-digit"),
        pytest.param(Fraction(456, 10_000), Fraction(46, 1_000), id="cents"),
        pytest.param(Fraction(0), Fraction(0), id="zero"),
    ],
)
def test_two_significant_digits_on_single_values(value: Fraction, rounded: Fraction) -> None:
    assert two_significant_digits(value) == rounded


def test_two_significant_digits_refuses_a_negative_value() -> None:
    with pytest.raises(ValueError):
        two_significant_digits(Fraction(-1))


def test_max_acceptable_cost_and_lambda_from_euros() -> None:
    """B4 test 2: ``2·λ·d²/F`` and ``x·F / (2·d_ref²)`` on ``Fraction``, ``Decimal`` and ``ExactRatio``; with ``x`` = 100 €,
    ``F`` = 20 000, ``d_ref`` = 1 000: ``λ`` = 1 («Balanced»), and back."""
    assert max_acceptable_cost(Fraction(1, 4), Fraction(200), Fraction(20_000)) == Fraction(1)
    assert max_acceptable_cost(Decimal("4"), Decimal("200"), Decimal("20000")) == Decimal("16")
    assert max_acceptable_cost(R(1), R(500), R(20_000)) == R(25)
    assert lambda_from_reference_amount(Fraction(100), Fraction(20_000), Fraction(1_000)) == Fraction(1)
    assert lambda_from_reference_amount(Decimal("60"), Decimal("20000"), Decimal("1000")) == Decimal("0.6")
    lam = lambda_from_reference_amount(R(60), R(20_000), R(1_000))
    assert lam == R(3, 5) and max_acceptable_cost(lam, R(1_000), R(20_000)) == R(60)
