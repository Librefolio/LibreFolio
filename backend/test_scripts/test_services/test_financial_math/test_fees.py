"""
A0 (project 67, the Rebalancer): the broker fee formula gets one home, ``financial_math/fees.py::calculate_fee``.

The PAC engine owned the formula (``pac_allocator/numeric.py::calculate_fee``, on its ``ExactRatio``) and nothing else in
the project computed it. The planner now serves two Tools, so the formula lives with the common financial math
(``fixed + clamp(rate * notional, floor, cap)``, zero for a zero notional), generic on the number type the way
``oriented_rate`` is: the same lines serve ``Decimal``, ``Fraction`` and the PAC's ``ExactRatio``. ``financial_math``
cannot import the engine (``test_layer_boundaries.py``), so a refused input is a plain ``ValueError`` here, not the
engine's ``InvalidEconomicInputError``.

What is tested, once per number type:

* the values of the engine's own cases (they moved here with the formula): zero notional, the minimum, the cap, the
  fixed part, no cap, a minimum on a zero rate, a free schedule;
* the refusals: a negative input and a minimum above the cap raise ``ValueError``;
* the result keeps the number type of the inputs (no float, no ``Decimal`` out of a ``Fraction``).

That the engine no longer defines the formula is guarded in ``test_pac_planner_engine_boundaries.py``.

Pure: no server, no database.
"""

from __future__ import annotations

from decimal import Decimal
from fractions import Fraction

import pytest

from backend.app.services.financial_math import fees
from backend.app.services.financial_math.fees import calculate_fee
from backend.app.services.pac_allocator.numeric import ExactRatio

# One constructor per number type the formula serves: (name, number(numerator, denominator)).
NUMBER_TYPES = [
    pytest.param(lambda n, d=1: Decimal(n) / Decimal(d), Decimal, id="decimal"),
    pytest.param(lambda n, d=1: Fraction(n, d), Fraction, id="fraction"),
    pytest.param(lambda n, d=1: ExactRatio(n, d), ExactRatio, id="exact-ratio"),
]


def test_fee_formula_has_its_home_in_financial_math():
    assert calculate_fee is fees.calculate_fee
    assert calculate_fee.__module__ == "backend.app.services.financial_math.fees"


@pytest.mark.parametrize(("number", "kind"), NUMBER_TYPES)
def test_fee_is_zero_for_zero_notional_even_with_nonzero_schedule(number, kind):
    fee = calculate_fee(notional=number(0), fixed=number(5), rate=number(1, 10), floor=number(2), cap=number(4))

    assert fee == number(0)
    assert type(fee) is kind


@pytest.mark.parametrize(("number", "kind"), NUMBER_TYPES)
@pytest.mark.parametrize(
    ("rate", "floor", "cap", "expected"),
    [
        pytest.param((1, 200), 1, 3, 2, id="below-floor"),
        pytest.param((1, 100), 1, 3, 2, id="at-floor"),
        pytest.param((1, 50), 1, 3, 3, id="between-bounds"),
        pytest.param((3, 100), 1, 3, 4, id="at-cap"),
        pytest.param((1, 20), 1, 3, 4, id="above-cap"),
        pytest.param((1, 20), 1, None, 6, id="cap-absent"),
    ],
)
def test_fee_formula_is_generic_on_the_number_type(number, kind, rate, floor, cap, expected):
    """Notional 100, fixed 1: the same values the engine's own cases asserted on ``ExactRatio``."""
    fee = calculate_fee(
        notional=number(100),
        fixed=number(1),
        rate=number(*rate),
        floor=number(floor),
        cap=None if cap is None else number(cap),
    )

    assert fee == number(expected)
    assert type(fee) is kind


@pytest.mark.parametrize(("number", "kind"), NUMBER_TYPES)
def test_fee_minimum_binds_an_active_zero_rate_order_and_a_free_schedule_is_explicit(number, kind):
    minimum_only = calculate_fee(notional=number(10), fixed=number(0), rate=number(0), floor=number(2), cap=None)
    free = calculate_fee(notional=number(10), fixed=number(0), rate=number(0), floor=number(0), cap=None)

    assert minimum_only == number(2)
    assert free == number(0)
    assert type(minimum_only) is type(free) is kind


@pytest.mark.parametrize(("number", "kind"), NUMBER_TYPES)
@pytest.mark.parametrize("field", ["notional", "fixed", "rate", "floor", "cap"])
def test_fee_rejects_negative_inputs_and_floor_above_cap(number, kind, field):
    schedule = {"notional": number(100), "fixed": number(1), "rate": number(1, 100), "floor": number(1), "cap": number(3)}
    schedule[field] = number(-1)

    with pytest.raises(ValueError, match=field):
        calculate_fee(**schedule)

    # A minimum above the cap is the second refusal.
    with pytest.raises(ValueError, match="floor"):
        calculate_fee(notional=number(100), fixed=number(0), rate=number(1, 100), floor=number(4), cap=number(3))


def test_fee_refusal_is_a_plain_value_error_not_the_engines_error():
    """``financial_math`` cannot name the engine's exception: the refusal is exactly ``ValueError``."""
    with pytest.raises(ValueError) as raised:
        calculate_fee(notional=Decimal(-1), fixed=Decimal(0), rate=Decimal(0), floor=Decimal(0), cap=None)

    assert type(raised.value) is ValueError
