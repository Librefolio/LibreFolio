"""Exact numeric kernel tests for PAC planning and rebalancing.

All witnesses are pure in-memory values.  Bounded property loops compare the
kernel with :class:`fractions.Fraction`; no database, server, clock, or external
property-testing dependency is involved.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, Inexact
from fractions import Fraction

import pytest

from backend.app.services.pac_allocator.numeric import (
    HUNDRED,
    ONE,
    P1_DECIMAL_PRECISION,
    RATIO_DECIMAL_PLACES,
    ZERO,
    ExactArithmeticError,
    ExactDivisionByZeroError,
    ExactRatio,
    InvalidEconomicInputError,
    InvalidExactRatioError,
    InvalidQuantumError,
    NonFiniteDecimalError,
    NonTerminatingDecimalError,
    PostedAmount,
    calculate_effective_fx_rate,
    calculate_fee,
    calculate_fx_credit,
    calculate_tax_reserve,
    calculate_taxable_gain,
    ceil_to_quantum_units,
    decimal_context,
    decimal_text,
    exact_holding_value,
    post_half_up,
    ratio_approximation,
)


def _ratio(value: str) -> ExactRatio:
    return ExactRatio.from_decimal(Decimal(value))


def _fraction(value: ExactRatio) -> Fraction:
    return Fraction(*value.as_integer_ratio())


def test_p1_decimal_constants_context_and_text_api_remain_stable():
    assert ZERO == Decimal("0")
    assert ONE == Decimal("1")
    assert HUNDRED == Decimal("100")
    assert P1_DECIMAL_PRECISION == 256
    assert RATIO_DECIMAL_PLACES == 28

    context = decimal_context()
    assert context.prec == P1_DECIMAL_PRECISION
    assert context.rounding == ROUND_HALF_EVEN
    assert context.traps[Inexact] is True

    assert decimal_text(Decimal("1.2300")) == "1.23"
    assert decimal_text(Decimal("-0.000")) == "0"
    with pytest.raises(ArithmeticError):
        decimal_text(Decimal("NaN"))


def test_p1_exact_holding_value_api_remains_unquantized():
    assert exact_holding_value(
        Decimal("3.25"),
        Decimal("98.5"),
        100,
    ) == Decimal("3.20125")


def test_p1_ratio_approximation_api_remains_stable():
    assert ratio_approximation(Decimal("1"), Decimal("8")) == ("0.125", True)
    assert ratio_approximation(Decimal("1"), Decimal("3")) == (
        "0.3333333333333333333333333333",
        False,
    )
    with pytest.raises(ArithmeticError):
        ratio_approximation(Decimal("1"), Decimal("0"))


def test_exact_error_taxonomy_is_public_and_rooted_in_arithmetic_error():
    typed_errors = (
        InvalidExactRatioError,
        ExactDivisionByZeroError,
        NonFiniteDecimalError,
        NonTerminatingDecimalError,
        InvalidQuantumError,
        InvalidEconomicInputError,
    )

    assert issubclass(ExactArithmeticError, ArithmeticError)
    assert all(issubclass(error, ExactArithmeticError) for error in typed_errors)
    assert len(set(typed_errors)) == len(typed_errors)


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected"),
    [
        pytest.param(2, 4, (1, 2), id="positive"),
        pytest.param(2, -4, (-1, 2), id="negative-denominator"),
        pytest.param(-2, -4, (1, 2), id="double-negative"),
        pytest.param(0, -9, (0, 1), id="canonical-zero"),
    ],
)
def test_ratio_canonicalizes_sign_gcd_and_zero(numerator, denominator, expected):
    ratio = ExactRatio(numerator, denominator)

    assert ratio.as_integer_ratio() == expected
    assert ratio.denominator > 0


@pytest.mark.parametrize(
    ("numerator", "denominator", "error"),
    [
        pytest.param(True, 1, InvalidExactRatioError, id="boolean-numerator"),
        pytest.param(1, True, InvalidExactRatioError, id="boolean-denominator"),
        pytest.param(Decimal("1"), 1, InvalidExactRatioError, id="decimal-numerator"),
        pytest.param(1, Decimal("2"), InvalidExactRatioError, id="decimal-denominator"),
        pytest.param(1, 0.0, InvalidExactRatioError, id="float-zero-denominator"),
        pytest.param(1, 0, ExactDivisionByZeroError, id="integer-zero-denominator"),
    ],
)
def test_ratio_constructor_rejects_invalid_components_with_typed_error(
    numerator,
    denominator,
    error,
):
    with pytest.raises(error) as raised:
        ExactRatio(numerator, denominator)

    assert type(raised.value) is error


def test_ratio_operations_reject_invalid_operands_and_zero_divisors():
    ratio = ExactRatio(3, 2)

    with pytest.raises(InvalidExactRatioError) as invalid_decimal:
        ratio + Decimal("1")
    assert type(invalid_decimal.value) is InvalidExactRatioError

    with pytest.raises(InvalidExactRatioError) as invalid_order:
        assert ratio < "1"
    assert type(invalid_order.value) is InvalidExactRatioError

    with pytest.raises(ExactDivisionByZeroError) as direct_zero:
        ratio / ExactRatio(0)
    assert type(direct_zero.value) is ExactDivisionByZeroError

    with pytest.raises(ExactDivisionByZeroError) as reverse_zero:
        1 / ExactRatio(0)
    assert type(reverse_zero.value) is ExactDivisionByZeroError

    with pytest.raises(InvalidExactRatioError) as non_decimal:
        ExactRatio.from_decimal("1")
    assert type(non_decimal.value) is InvalidExactRatioError


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("1.2300", (123, 100), id="trailing-zeroes"),
        pytest.param("-0.000", (0, 1), id="negative-zero"),
        pytest.param("1E+3", (1000, 1), id="positive-exponent"),
    ],
)
def test_decimal_conversion_is_lossless_and_canonical(value, expected):
    ratio = ExactRatio.from_decimal(Decimal(value))

    assert ratio.as_integer_ratio() == expected


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("NaN", id="nan"),
        pytest.param("Infinity", id="positive-infinity"),
        pytest.param("-Infinity", id="negative-infinity"),
    ],
)
def test_decimal_conversion_rejects_nonfinite_values_with_typed_error(value):
    with pytest.raises(NonFiniteDecimalError) as raised:
        ExactRatio.from_decimal(Decimal(value))

    assert type(raised.value) is NonFiniteDecimalError


@pytest.mark.parametrize(
    ("ratio", "expected"),
    [
        pytest.param(ExactRatio(1, 8), Decimal("0.125"), id="positive"),
        pytest.param(ExactRatio(-3, 20), Decimal("-0.15"), id="negative"),
    ],
)
def test_exact_decimal_projection_accepts_terminating_ratios(ratio, expected):
    assert ratio.to_decimal_exact() == expected


def test_exact_decimal_projection_rejects_nonterminating_ratio():
    with pytest.raises(NonTerminatingDecimalError) as raised:
        ExactRatio(1, 3).to_decimal_exact()

    assert type(raised.value) is NonTerminatingDecimalError


def test_ratio_integer_interop_and_helpers_remain_exact():
    ratio = ExactRatio(3, 2)

    assert ratio + 2 == ExactRatio(7, 2)
    assert 2 + ratio == ExactRatio(7, 2)
    assert ratio - 2 == ExactRatio(-1, 2)
    assert 2 - ratio == ExactRatio(1, 2)
    assert ratio * 2 == ExactRatio(3)
    assert 2 * ratio == ExactRatio(3)
    assert ratio / 2 == ExactRatio(3, 4)
    assert 3 / ratio == ExactRatio(2)
    assert -ratio == ExactRatio(-3, 2)
    assert abs(-ratio) == ratio
    assert ratio.square() == ExactRatio(9, 4)
    assert bool(ratio) is True
    assert bool(ExactRatio(0)) is False
    assert ExactRatio(3) == 3
    assert 3 == ExactRatio(3)
    assert ExactRatio(3, 2) < 2
    assert str(ratio) == "3/2"
    assert str(ExactRatio(3)) == "3"
    assert hash(ExactRatio(3)) == hash(3)


def test_ratio_arithmetic_and_ordering_match_fraction_on_bounded_domain():
    witnesses = (
        ExactRatio(-11, 7),
        ExactRatio(-5, 2),
        ExactRatio(-1, 9),
        ExactRatio(0),
        ExactRatio(1, 8),
        ExactRatio(2, 3),
        ExactRatio(13, 5),
    )

    for left in witnesses:
        left_fraction = _fraction(left)
        assert _fraction(left.square()) == left_fraction**2
        for right in witnesses:
            right_fraction = _fraction(right)
            witness = (left.as_integer_ratio(), right.as_integer_ratio())

            assert _fraction(left + right) == left_fraction + right_fraction, witness
            assert _fraction(left - right) == left_fraction - right_fraction, witness
            assert _fraction(left * right) == left_fraction * right_fraction, witness
            if right:
                assert _fraction(left / right) == left_fraction / right_fraction, witness

            assert (left == right) is (left_fraction == right_fraction), witness
            assert (left < right) is (left_fraction < right_fraction), witness
            assert (left <= right) is (left_fraction <= right_fraction), witness
            assert (left > right) is (left_fraction > right_fraction), witness
            assert (left >= right) is (left_fraction >= right_fraction), witness


def test_ratio_canonicalization_is_idempotent_on_bounded_domain():
    scales = (-7, -2, 1, 3, 11)

    for numerator in range(-8, 9):
        for denominator in range(-8, 9):
            if denominator == 0:
                continue
            expected = Fraction(numerator, denominator)
            ratio = ExactRatio(numerator, denominator)
            canonical = (expected.numerator, expected.denominator)

            assert ratio.as_integer_ratio() == canonical
            assert ExactRatio(*ratio.as_integer_ratio()).as_integer_ratio() == canonical
            for scale in scales:
                scaled = ExactRatio(numerator * scale, denominator * scale)
                assert scaled.as_integer_ratio() == canonical
                assert scaled == ratio


@pytest.mark.parametrize(
    ("value", "expected_posted", "expected_delta", "expected_units"),
    [
        pytest.param("1.005", "1.01", "0.005", 101, id="positive-tie"),
        pytest.param("-1.005", "-1.01", "-0.005", -101, id="negative-tie"),
        pytest.param("1.004", "1.00", "-0.004", 100, id="positive-below-tie"),
        pytest.param("-1.004", "-1.00", "0.004", -100, id="negative-below-tie"),
    ],
)
def test_signed_half_up_posts_once_with_explicit_quantum(
    value,
    expected_posted,
    expected_delta,
    expected_units,
):
    exact = _ratio(value)
    quantum = _ratio("0.01")
    result = post_half_up(exact, quantum)

    assert isinstance(result, PostedAmount)
    assert result.exact == exact
    assert result.quantum == quantum
    assert result.posted == _ratio(expected_posted)
    assert result.rounding_delta == _ratio(expected_delta)
    assert result.units == expected_units
    assert abs(result.rounding_delta) <= quantum / 2


@pytest.mark.parametrize(
    ("value", "quantum", "error"),
    [
        pytest.param(Decimal("1"), ExactRatio(1, 100), InvalidEconomicInputError, id="decimal-value"),
        pytest.param(ExactRatio(1), ExactRatio(0), InvalidQuantumError, id="zero-quantum"),
        pytest.param(ExactRatio(1), ExactRatio(-1, 100), InvalidQuantumError, id="negative-quantum"),
        pytest.param(ExactRatio(1), Decimal("0.01"), InvalidQuantumError, id="decimal-quantum"),
    ],
)
def test_half_up_rejects_invalid_value_or_quantum_with_typed_error(
    value,
    quantum,
    error,
):
    with pytest.raises(error) as raised:
        post_half_up(value, quantum)

    assert type(raised.value) is error


def test_half_up_is_odd_and_delta_bounded_on_deterministic_domain():
    quantums = (ExactRatio(1, 100), ExactRatio(1, 8), ExactRatio(3, 20))

    for quantum in quantums:
        for numerator in range(0, 21):
            for denominator in range(1, 10):
                value = ExactRatio(numerator, denominator)
                positive = post_half_up(value, quantum)
                negative = post_half_up(-value, quantum)
                witness = (
                    value.as_integer_ratio(),
                    quantum.as_integer_ratio(),
                )

                assert negative.posted == -positive.posted, witness
                assert negative.units == -positive.units, witness
                assert negative.rounding_delta == -positive.rounding_delta, witness
                assert abs(positive.rounding_delta) <= quantum / 2, witness
                assert abs(negative.rounding_delta) <= quantum / 2, witness


@pytest.mark.parametrize(
    ("value", "quantum", "expected_units"),
    [
        pytest.param(ExactRatio(10, 3), ExactRatio(1, 100), 334, id="positive-fraction"),
        pytest.param(ExactRatio(-10, 3), ExactRatio(1, 100), -333, id="negative-fraction"),
        pytest.param(ExactRatio(15, 4), ExactRatio(1, 100), 375, id="exact-multiple"),
    ],
)
def test_ceil_to_quantum_units_uses_mathematical_ceiling(
    value,
    quantum,
    expected_units,
):
    assert ceil_to_quantum_units(value, quantum) == expected_units


@pytest.mark.parametrize(
    ("value", "quantum", "error"),
    [
        pytest.param(Decimal("1"), ExactRatio(1, 100), InvalidEconomicInputError, id="decimal-value"),
        pytest.param(ExactRatio(1), ExactRatio(0), InvalidQuantumError, id="zero-quantum"),
        pytest.param(ExactRatio(1), ExactRatio(-1), InvalidQuantumError, id="negative-quantum"),
        pytest.param(ExactRatio(1), Decimal("0.01"), InvalidQuantumError, id="decimal-quantum"),
    ],
)
def test_ceil_to_quantum_units_rejects_invalid_inputs(value, quantum, error):
    with pytest.raises(error) as raised:
        ceil_to_quantum_units(value, quantum)

    assert type(raised.value) is error


def test_fee_is_zero_for_zero_notional_even_with_nonzero_schedule():
    assert calculate_fee(
        notional=ExactRatio(0),
        fixed=ExactRatio(5),
        rate=ExactRatio(1, 10),
        floor=ExactRatio(2),
        cap=ExactRatio(4),
    ) == ExactRatio(0)


@pytest.mark.parametrize(
    ("rate", "floor", "cap", "expected"),
    [
        pytest.param(ExactRatio(1, 200), ExactRatio(1), ExactRatio(3), ExactRatio(2), id="below-floor"),
        pytest.param(ExactRatio(1, 100), ExactRatio(1), ExactRatio(3), ExactRatio(2), id="at-floor"),
        pytest.param(ExactRatio(1, 50), ExactRatio(1), ExactRatio(3), ExactRatio(3), id="between-bounds"),
        pytest.param(ExactRatio(3, 100), ExactRatio(1), ExactRatio(3), ExactRatio(4), id="at-cap"),
        pytest.param(ExactRatio(1, 20), ExactRatio(1), ExactRatio(3), ExactRatio(4), id="above-cap"),
        pytest.param(ExactRatio(1, 20), ExactRatio(1), None, ExactRatio(6), id="cap-absent"),
    ],
)
def test_fee_applies_rate_floor_cap_then_fixed(rate, floor, cap, expected):
    assert (
        calculate_fee(
            notional=ExactRatio(100),
            fixed=ExactRatio(1),
            rate=rate,
            floor=floor,
            cap=cap,
        )
        == expected
    )


def test_fee_minimum_binds_active_zero_rate_order_and_free_schedule_is_explicit():
    assert calculate_fee(
        notional=ExactRatio(10),
        fixed=ExactRatio(0),
        rate=ExactRatio(0),
        floor=ExactRatio(2),
        cap=None,
    ) == ExactRatio(2)
    assert calculate_fee(
        notional=ExactRatio(10),
        fixed=ExactRatio(0),
        rate=ExactRatio(0),
        floor=ExactRatio(0),
        cap=None,
    ) == ExactRatio(0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("notional", ExactRatio(-1), id="negative-notional"),
        pytest.param("fixed", ExactRatio(-1), id="negative-fixed"),
        pytest.param("rate", ExactRatio(-1), id="negative-rate"),
        pytest.param("floor", ExactRatio(-1), id="negative-floor"),
        pytest.param("cap", ExactRatio(-1), id="negative-cap"),
        pytest.param("notional", Decimal("1"), id="non-ratio-notional"),
    ],
)
def test_fee_rejects_invalid_inputs(field, value):
    schedule = {
        "notional": ExactRatio(100),
        "fixed": ExactRatio(1),
        "rate": ExactRatio(1, 100),
        "floor": ExactRatio(1),
        "cap": ExactRatio(3),
    }
    schedule[field] = value

    with pytest.raises(InvalidEconomicInputError) as raised:
        calculate_fee(**schedule)

    assert type(raised.value) is InvalidEconomicInputError


def test_fee_rejects_floor_above_cap():
    with pytest.raises(InvalidEconomicInputError) as raised:
        calculate_fee(
            notional=ExactRatio(100),
            fixed=ExactRatio(0),
            rate=ExactRatio(1, 100),
            floor=ExactRatio(4),
            cap=ExactRatio(3),
        )

    assert type(raised.value) is InvalidEconomicInputError


@pytest.mark.parametrize(
    ("approved_rate", "spread", "expected"),
    [
        pytest.param(ExactRatio(6, 5), ExactRatio(1, 100), ExactRatio(297, 250), id="direct-quote"),
        pytest.param(ExactRatio(5, 6), ExactRatio(1, 100), ExactRatio(33, 40), id="inverse-direction"),
        pytest.param(ExactRatio(7, 4), ExactRatio(0), ExactRatio(7, 4), id="zero-spread"),
        pytest.param(ExactRatio(7, 4), ExactRatio(999, 1000), ExactRatio(7, 4000), id="spread-below-one"),
    ],
)
def test_effective_fx_rate_respects_explicit_direction_and_spread(
    approved_rate,
    spread,
    expected,
):
    assert (
        calculate_effective_fx_rate(
            approved_rate=approved_rate,
            spread=spread,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("source_debit", "expected"),
    [
        pytest.param(ExactRatio(250), ExactRatio(297), id="positive-credit"),
        pytest.param(ExactRatio(0), ExactRatio(0), id="zero-credit"),
    ],
)
def test_fx_credit_uses_effective_rate_without_rounding(source_debit, expected):
    assert (
        calculate_fx_credit(
            source_debit=source_debit,
            approved_rate=ExactRatio(6, 5),
            spread=ExactRatio(1, 100),
        )
        == expected
    )


@pytest.mark.parametrize(
    ("approved_rate", "spread"),
    [
        pytest.param(ExactRatio(0), ExactRatio(0), id="zero-approved-rate"),
        pytest.param(ExactRatio(-1), ExactRatio(0), id="negative-approved-rate"),
        pytest.param(ExactRatio(1), ExactRatio(-1, 100), id="negative-spread"),
        pytest.param(ExactRatio(1), ExactRatio(1), id="spread-one"),
        pytest.param(ExactRatio(1), ExactRatio(101, 100), id="spread-above-one"),
        pytest.param(Decimal("1"), ExactRatio(0), id="non-ratio-approved-rate"),
        pytest.param(ExactRatio(1), Decimal("0.01"), id="non-ratio-spread"),
    ],
)
def test_effective_fx_rate_rejects_invalid_inputs(approved_rate, spread):
    with pytest.raises(InvalidEconomicInputError) as raised:
        calculate_effective_fx_rate(
            approved_rate=approved_rate,
            spread=spread,
        )

    assert type(raised.value) is InvalidEconomicInputError


@pytest.mark.parametrize(
    "source_debit",
    [
        pytest.param(ExactRatio(-1), id="negative"),
        pytest.param(Decimal("1"), id="non-ratio"),
    ],
)
def test_fx_credit_rejects_invalid_source_debit(source_debit):
    with pytest.raises(InvalidEconomicInputError) as raised:
        calculate_fx_credit(
            source_debit=source_debit,
            approved_rate=ExactRatio(1),
            spread=ExactRatio(0),
        )

    assert type(raised.value) is InvalidEconomicInputError


def test_taxable_gain_and_reserve_are_exact_before_posting():
    inputs = {
        "gross_sell_proceeds": ExactRatio(100),
        "sell_fee": ExactRatio(2),
        "sold_quantity": ExactRatio(4),
        "unit_cost": ExactRatio(20),
    }

    assert calculate_taxable_gain(**inputs) == ExactRatio(18)
    assert calculate_tax_reserve(
        **inputs,
        tax_rate=ExactRatio(1, 4),
    ) == ExactRatio(9, 2)
    assert calculate_tax_reserve(
        **inputs,
        tax_rate=ExactRatio(0),
    ) == ExactRatio(0)
    assert calculate_tax_reserve(
        **inputs,
        tax_rate=ExactRatio(1),
    ) == ExactRatio(18)


@pytest.mark.parametrize(
    "gross_sell_proceeds",
    [
        pytest.param(ExactRatio(82), id="zero-gain"),
        pytest.param(ExactRatio(81), id="negative-gain"),
    ],
)
def test_taxable_gain_clamps_nonpositive_result_to_zero(gross_sell_proceeds):
    inputs = {
        "gross_sell_proceeds": gross_sell_proceeds,
        "sell_fee": ExactRatio(2),
        "sold_quantity": ExactRatio(4),
        "unit_cost": ExactRatio(20),
    }

    assert calculate_taxable_gain(**inputs) == ExactRatio(0)
    assert calculate_tax_reserve(
        **inputs,
        tax_rate=ExactRatio(1, 4),
    ) == ExactRatio(0)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        pytest.param("gross_sell_proceeds", ExactRatio(-1), id="negative-proceeds"),
        pytest.param("sell_fee", ExactRatio(-1), id="negative-fee"),
        pytest.param("sold_quantity", ExactRatio(-1), id="negative-quantity"),
        pytest.param("unit_cost", ExactRatio(-1), id="negative-unit-cost"),
        pytest.param("tax_rate", ExactRatio(-1), id="negative-tax-rate"),
        pytest.param("gross_sell_proceeds", Decimal("100"), id="non-ratio-proceeds"),
    ],
)
def test_tax_reserve_rejects_invalid_inputs(field, value):
    inputs = {
        "gross_sell_proceeds": ExactRatio(100),
        "sell_fee": ExactRatio(2),
        "sold_quantity": ExactRatio(4),
        "unit_cost": ExactRatio(20),
        "tax_rate": ExactRatio(1, 4),
    }
    inputs[field] = value

    with pytest.raises(InvalidEconomicInputError) as raised:
        calculate_tax_reserve(**inputs)

    assert type(raised.value) is InvalidEconomicInputError


def test_tax_reserve_rejects_rate_above_one():
    with pytest.raises(InvalidEconomicInputError) as raised:
        calculate_tax_reserve(
            gross_sell_proceeds=ExactRatio(100),
            sell_fee=ExactRatio(2),
            sold_quantity=ExactRatio(4),
            unit_cost=ExactRatio(20),
            tax_rate=ExactRatio(1001, 1000),
        )

    assert type(raised.value) is InvalidEconomicInputError
