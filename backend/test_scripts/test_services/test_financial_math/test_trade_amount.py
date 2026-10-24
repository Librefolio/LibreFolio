"""
Red tests for #47 «trade amount» (the transaction form types the unit price or the amount, the backend calculates the other).

Module under test: ``backend/app/services/financial_math/trade_amount.py``. Two pure functions, no DB, no server:

* ``amount_from_unit_price(quantity, unit_price, quote_base_quantity, *, scale)`` =
  ``quantity / quote_base_quantity × unit_price``, rounded ROUND_HALF_EVEN to ``scale`` decimals (callers pass 6);
* ``unit_price_from_amount(quantity, amount, quote_base_quantity, *, scale)`` =
  ``amount × quote_base_quantity / quantity``, rounded ROUND_HALF_EVEN to ``scale`` decimals (callers pass 12);
  ``ZeroDivisionError`` on a zero quantity (``amount_from_unit_price`` with a zero quantity is 0).

``quote_base_quantity`` None, 0 or negative counts as 1 (``valuation.normalize_quote_base_quantity``).

What these tests guard against: a float anywhere, the ambient ``decimal`` context leaking in (a 28-digit context
raises ``InvalidOperation`` on the extreme inputs the input limits allow), a rounding mode other than half-even, a
division done before the multiplication that loses digits, and a base-100 bond read as base 1.

Every expected value is written by hand or derived through ``fractions.Fraction`` (exact rationals, half-even
``round``), never through ``decimal`` itself, so the oracle shares no code path with the function under test.
"""

from decimal import ROUND_DOWN, Decimal, getcontext, localcontext
from fractions import Fraction

import pytest

from backend.app.services.financial_math.trade_amount import amount_from_unit_price, unit_price_from_amount

AMOUNT_SCALE = 6
PRICE_SCALE = 12


def _exact(value: Fraction, scale: int) -> Decimal:
    """``value`` rounded half-even to ``scale`` decimals, from exact rationals (``round(Fraction)`` is half-even)."""
    return Decimal(f"{round(value * 10**scale)}e-{scale}")  # the string form is exact, whatever the ambient context


def _amount(quantity: str, price: str, base: int | None = 1, scale: int = AMOUNT_SCALE) -> Decimal:
    return amount_from_unit_price(Decimal(quantity), Decimal(price), base, scale=scale)


def _price(quantity: str, amount: str, base: int | None = 1, scale: int = PRICE_SCALE) -> Decimal:
    return unit_price_from_amount(Decimal(quantity), Decimal(amount), base, scale=scale)


class TestAmountFromUnitPrice:
    def test_the_worked_example(self):
        result = _amount("12", "83.40")
        assert isinstance(result, Decimal)
        assert result == Decimal("1000.8")

    def test_a_bond_quoted_on_base_100(self):
        """10000 units of a bond quoted per 100 at 98.5: 10000 / 100 × 98.5 = 9850."""
        assert _amount("10000", "98.5", 100) == Decimal("9850")

    def test_fractional_quantity(self):
        assert _amount("0.5", "3", 1) == Decimal("1.5")
        assert _amount("2.5", "0.4", 1) == Decimal("1")

    @pytest.mark.parametrize("base", [None, 0, -1, -100])
    def test_a_missing_or_non_positive_base_counts_as_one(self, base):
        assert _amount("12", "83.40", base) == _amount("12", "83.40", 1) == Decimal("1000.8")

    def test_the_base_divides_the_quantity(self):
        assert _amount("50", "10", 10) == Decimal("50")
        assert _amount("50", "10", 1) == Decimal("500")
        assert _amount("1", "100", 4) == Decimal("25")

    @pytest.mark.parametrize(
        ("price", "expected"),
        [
            ("0.0000025", "0.000002"),  # tie, 2 is even: stays
            ("0.0000035", "0.000004"),  # tie, 3 is odd: up
            ("0.0000015", "0.000002"),  # tie, 1 is odd: up
            ("0.0000045", "0.000004"),  # tie, 4 is even: stays
            ("0.0000026", "0.000003"),  # not a tie: up
            ("0.0000024", "0.000002"),  # not a tie: down
        ],
    )
    def test_half_even_at_the_scale(self, price, expected):
        assert _amount("1", price) == Decimal(expected)

    def test_half_even_is_symmetric_on_a_negative_quantity(self):
        assert _amount("-1", "0.0000025") == Decimal("-0.000002")
        assert _amount("-1", "0.0000035") == Decimal("-0.000004")

    def test_the_scale_is_the_callers(self):
        assert _amount("1", "0.125", scale=2) == Decimal("0.12")
        assert _amount("1", "0.135", scale=2) == Decimal("0.14")
        assert _amount("1", "0.5", scale=0) == Decimal("0")
        assert _amount("1", "1.5", scale=0) == Decimal("2")

    def test_zero_quantity_is_zero(self):
        assert _amount("0", "83.40") == Decimal("0")
        assert _amount("0", "83.40", 100) == Decimal("0")

    def test_sign_follows_the_quantity(self):
        assert _amount("-12", "83.40") == Decimal("-1000.8")
        assert _amount("12", "-83.40") == Decimal("-1000.8")
        assert _amount("-12", "-83.40") == Decimal("1000.8")

    def test_the_division_does_not_cost_digits_before_the_multiplication(self):
        """1 / 3 × 3 is 1: a quantity divided by the base first at a short precision would give 0.999…"""
        assert _amount("1", "3", 3) == Decimal("1")
        assert _amount("7", "3", 7) == Decimal("3")
        # 10 / 3 × 0.3 = 1 exactly
        assert _amount("10", "0.3", 3) == Decimal("1")


class TestUnitPriceFromAmount:
    def test_the_worked_example(self):
        result = _price("12", "1000.8")
        assert isinstance(result, Decimal)
        assert result == Decimal("83.4")

    def test_a_bond_quoted_on_base_100(self):
        assert _price("10000", "9850", 100) == Decimal("98.5")

    @pytest.mark.parametrize("base", [None, 0, -1, -100])
    def test_a_missing_or_non_positive_base_counts_as_one(self, base):
        assert _price("12", "1000.8", base) == _price("12", "1000.8", 1) == Decimal("83.4")

    def test_the_base_multiplies_the_amount(self):
        assert _price("50", "50", 10) == Decimal("10")
        assert _price("50", "500", 1) == Decimal("10")

    def test_half_even_tie_at_scale_12_rounds_to_the_even_digit(self):
        """1 / 8192 = 0.0001220703125 exactly: a true tie at 12 decimals, 2 is even, so it stays."""
        assert _price("8192", "1") == Decimal("0.000122070312")

    def test_half_even_tie_at_scale_12_rounds_up_to_the_even_digit(self):
        """3 / 8192 = 0.0003662109375 exactly: a true tie, 7 is odd, so it goes up."""
        assert _price("8192", "3") == Decimal("0.000366210938")

    def test_the_tie_cases_agree_with_the_exact_oracle(self):
        for amount in ("1", "3", "5", "7", "9", "11"):
            assert _price("8192", amount) == _exact(Fraction(int(amount), 8192), PRICE_SCALE)

    @pytest.mark.parametrize(
        ("quantity", "amount", "expected"),
        [
            ("3", "100", "33.333333333333"),
            ("3", "200", "66.666666666667"),
            ("3", "1", "0.333333333333"),
            ("3", "2", "0.666666666667"),
        ],
    )
    def test_a_non_terminating_quotient_rounds_at_the_scale(self, quantity, amount, expected):
        assert _price(quantity, amount) == Decimal(expected)

    def test_zero_quantity_raises(self):
        with pytest.raises(ZeroDivisionError):
            _price("0", "1000.8")
        with pytest.raises(ZeroDivisionError):
            _price("0.0000000000", "1000.8")
        with pytest.raises(ZeroDivisionError):
            _price("0", "0")

    def test_zero_amount_is_a_zero_price(self):
        assert _price("12", "0") == Decimal("0")

    def test_sign_follows_amount_and_quantity(self):
        assert _price("-12", "1000.8") == Decimal("-83.4")
        assert _price("12", "-1000.8") == Decimal("-83.4")
        assert _price("-12", "-1000.8") == Decimal("83.4")

    def test_the_scale_is_the_callers(self):
        assert _price("3", "1", scale=2) == Decimal("0.33")
        assert _price("3", "2", scale=2) == Decimal("0.67")
        assert _price("8", "1", scale=2) == Decimal("0.12")  # 0.125, tie, 2 even


class TestRoundTrip:
    @pytest.mark.parametrize(
        ("quantity", "price", "base"),
        [
            ("12", "83.40", 1),
            ("7", "12.3456", 1),
            ("250", "0.1", 1),
            ("10000", "98.5", 100),
            ("1", "1", 1),
            ("0.5", "40", 1),
        ],
    )
    def test_price_to_amount_to_price_gives_the_price_back(self, quantity, price, base):
        """Only the terminating cases, where the amount is exact at 6 decimals: the others are not asserted."""
        amount = _amount(quantity, price, base)
        assert _price(quantity, str(amount), base) == Decimal(price)

    @pytest.mark.parametrize(("quantity", "amount", "base"), [("12", "1000.8", 1), ("10000", "9850", 100), ("250", "25", 1)])
    def test_amount_to_price_to_amount_gives_the_amount_back_when_the_price_is_exact(self, quantity, amount, base):
        price = _price(quantity, amount, base)
        assert _amount(quantity, str(price), base) == Decimal(amount)


class TestExtremeInputs:
    """The largest values the input limits allow (15 integer digits for a quantity, 12 decimals for a price) do not raise."""

    QUANTITY = "999999999999999"
    PRICE = "999999999999.999999999999"

    def test_the_largest_amount_computation_does_not_raise_and_is_exact(self):
        result = _amount(self.QUANTITY, self.PRICE)
        expected = _exact(Fraction(self.QUANTITY) * Fraction(self.PRICE), AMOUNT_SCALE)
        assert result == expected

    def test_the_largest_amount_computation_on_a_base_does_not_raise_and_is_exact(self):
        result = _amount(self.QUANTITY, self.PRICE, 100)
        expected = _exact(Fraction(self.QUANTITY) / 100 * Fraction(self.PRICE), AMOUNT_SCALE)
        assert result == expected

    def test_the_largest_price_computation_does_not_raise_and_is_exact(self):
        amount = "999999999999999.999999"
        result = _price("0.0000000001", amount)
        expected = _exact(Fraction(amount) / Fraction("0.0000000001"), PRICE_SCALE)
        assert result == expected

    def test_a_long_non_terminating_price_is_exact_at_the_scale(self):
        result = _price("999999999999999", "1")
        assert result == _exact(Fraction(1, 999999999999999), PRICE_SCALE)


class TestAmbientDecimalContext:
    def test_a_narrow_ambient_context_changes_nothing(self):
        outside_amount = _amount("12", "83.40")
        outside_price = _price("100", "3")
        with localcontext() as ctx:
            ctx.prec = 5
            assert _amount("12", "83.40") == outside_amount == Decimal("1000.8")
            assert _price("100", "3") == outside_price
            assert _amount("999999999999999", "999999999999.999999999999") == _exact(Fraction("999999999999999") * Fraction("999999999999.999999999999"), AMOUNT_SCALE)

    def test_the_ambient_rounding_mode_changes_nothing(self):
        with localcontext() as ctx:
            ctx.prec = 5
            ctx.rounding = ROUND_DOWN
            assert _amount("1", "0.0000035") == Decimal("0.000004")
            assert _price("8192", "3") == Decimal("0.000366210938")
            assert _price("3", "200") == Decimal("66.666666666667")

    def test_the_ambient_context_is_not_mutated(self):
        with localcontext() as ctx:
            ctx.prec = 5
            ctx.rounding = ROUND_DOWN
            before = (ctx.prec, ctx.rounding, ctx.Emin, ctx.Emax, ctx.capitals, ctx.clamp, dict(ctx.traps))
            _amount("12", "83.40")
            _price("100", "3")
            after = (getcontext().prec, getcontext().rounding, getcontext().Emin, getcontext().Emax, getcontext().capitals, getcontext().clamp, dict(getcontext().traps))
            assert after == before

    def test_the_default_context_precision_is_untouched(self):
        before = getcontext().prec
        _amount("999999999999999", "999999999999.999999999999")
        _price("999999999999999", "1")
        assert getcontext().prec == before
