"""
Tests for Currency class in common.py.

Tests cover:
- Currency creation with valid ISO 4217 codes
- Currency creation with crypto currencies
- Invalid currency code rejection
- Arithmetic operations (add, sub, neg, abs)
- Comparison operations
- Error handling for different currencies
- Serialization (to_dict, str, repr)
- Utility methods (zero, is_zero, is_positive, is_negative)
"""

from decimal import Decimal

import pytest

from backend.app.schemas.common import Currency, CRYPTO_CURRENCIES


class TestCurrencyCreation:
    """Test Currency object creation."""

    def test_create_usd(self):
        """Create USD currency."""
        usd = Currency(code="USD", amount=Decimal("100.50"))
        assert usd.code == "USD"
        assert usd.amount == Decimal("100.50")

    def test_create_eur(self):
        """Create EUR currency."""
        eur = Currency(code="EUR", amount=Decimal("50"))
        assert eur.code == "EUR"
        assert eur.amount == Decimal("50")

    def test_create_lowercase_code(self):
        """Currency code is normalized to uppercase."""
        usd = Currency(code="usd", amount=Decimal("100"))
        assert usd.code == "USD"

    def test_create_mixed_case_code(self):
        """Currency code handles mixed case."""
        usd = Currency(code="UsD", amount=Decimal("100"))
        assert usd.code == "USD"

    def test_create_with_whitespace(self):
        """Currency code is trimmed."""
        usd = Currency(code="  USD  ", amount=Decimal("100"))
        assert usd.code == "USD"

    def test_create_negative_amount(self):
        """Negative amounts are allowed."""
        usd = Currency(code="USD", amount=Decimal("-50"))
        assert usd.amount == Decimal("-50")

    def test_create_from_int(self):
        """Amount can be int."""
        usd = Currency(code="USD", amount=100)
        assert usd.amount == Decimal("100")

    def test_create_from_float(self):
        """Amount can be float."""
        usd = Currency(code="USD", amount=100.50)
        assert usd.amount == Decimal("100.5")

    def test_create_from_string(self):
        """Amount can be string."""
        usd = Currency(code="USD", amount="100.50")
        assert usd.amount == Decimal("100.50")


class TestCryptoCurrencies:
    """Test cryptocurrency support."""

    def test_btc(self):
        """BTC is valid."""
        btc = Currency(code="BTC", amount=Decimal("0.5"))
        assert btc.code == "BTC"

    def test_eth(self):
        """ETH is valid."""
        eth = Currency(code="ETH", amount=Decimal("2.0"))
        assert eth.code == "ETH"

    def test_all_supported_cryptos(self):
        """All cryptos in CRYPTO_CURRENCIES are valid."""
        for code in CRYPTO_CURRENCIES.keys():
            crypto = Currency(code=code, amount=Decimal("1"))
            assert crypto.code == code


class TestInvalidCurrency:
    """Test invalid currency rejection."""

    def test_invalid_code(self):
        """Invalid currency code raises ValueError."""
        with pytest.raises(ValueError, match="Invalid currency code"):
            Currency(code="NOTACURRENCY", amount=Decimal("100"))

    def test_empty_code(self):
        """Empty currency code raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Currency(code="", amount=Decimal("100"))

    def test_whitespace_only_code(self):
        """Whitespace-only code raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Currency(code="   ", amount=Decimal("100"))

    def test_invalid_amount(self):
        """Invalid amount raises ValueError."""
        with pytest.raises(ValueError):
            Currency(code="USD", amount="not-a-number")

    def test_non_string_code(self):
        """Non-string code raises ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            Currency(code=123, amount=Decimal("100"))


class TestArithmetic:
    """Test arithmetic operations."""

    def test_addition(self):
        """Add two currencies."""
        a = Currency(code="USD", amount=Decimal("100"))
        b = Currency(code="USD", amount=Decimal("50"))
        c = a + b
        assert c.code == "USD"
        assert c.amount == Decimal("150")

    def test_subtraction(self):
        """Subtract two currencies."""
        a = Currency(code="USD", amount=Decimal("100"))
        b = Currency(code="USD", amount=Decimal("30"))
        c = a - b
        assert c.code == "USD"
        assert c.amount == Decimal("70")

    def test_subtraction_negative_result(self):
        """Subtraction can result in negative."""
        a = Currency(code="USD", amount=Decimal("30"))
        b = Currency(code="USD", amount=Decimal("100"))
        c = a - b
        assert c.amount == Decimal("-70")

    def test_negation(self):
        """Negate currency."""
        usd = Currency(code="USD", amount=Decimal("100"))
        neg = -usd
        assert neg.code == "USD"
        assert neg.amount == Decimal("-100")

    def test_negation_of_negative(self):
        """Negate negative currency."""
        usd = Currency(code="USD", amount=Decimal("-50"))
        pos = -usd
        assert pos.amount == Decimal("50")

    def test_abs_positive(self):
        """Abs of positive amount."""
        usd = Currency(code="USD", amount=Decimal("100"))
        result = abs(usd)
        assert result.amount == Decimal("100")

    def test_abs_negative(self):
        """Abs of negative amount."""
        usd = Currency(code="USD", amount=Decimal("-100"))
        result = abs(usd)
        assert result.amount == Decimal("100")


class TestArithmeticErrors:
    """Test arithmetic error handling."""

    def test_add_different_currencies(self):
        """Cannot add different currencies."""
        usd = Currency(code="USD", amount=Decimal("100"))
        eur = Currency(code="EUR", amount=Decimal("50"))
        with pytest.raises(ValueError, match="Cannot add USD and EUR"):
            usd + eur

    def test_sub_different_currencies(self):
        """Cannot subtract different currencies."""
        usd = Currency(code="USD", amount=Decimal("100"))
        eur = Currency(code="EUR", amount=Decimal("50"))
        with pytest.raises(ValueError, match="Cannot subtract EUR from USD"):
            usd - eur

    def test_add_non_currency(self):
        """Cannot add non-Currency."""
        usd = Currency(code="USD", amount=Decimal("100"))
        with pytest.raises(TypeError, match="Cannot add Currency and int"):
            usd + 50

    def test_sub_non_currency(self):
        """Cannot subtract non-Currency."""
        usd = Currency(code="USD", amount=Decimal("100"))
        with pytest.raises(TypeError, match="Cannot subtract int from Currency"):
            usd - 50


class TestComparison:
    """Test comparison operations."""

    def test_equality(self):
        """Equal currencies."""
        a = Currency(code="USD", amount=Decimal("100"))
        b = Currency(code="USD", amount=Decimal("100"))
        assert a == b

    def test_inequality_amount(self):
        """Different amounts."""
        a = Currency(code="USD", amount=Decimal("100"))
        b = Currency(code="USD", amount=Decimal("50"))
        assert a != b

    def test_inequality_code(self):
        """Different codes."""
        usd = Currency(code="USD", amount=Decimal("100"))
        eur = Currency(code="EUR", amount=Decimal("100"))
        assert usd != eur

    def test_not_equal_to_non_currency(self):
        """Currency is not equal to non-Currency."""
        usd = Currency(code="USD", amount=Decimal("100"))
        assert usd != 100
        assert usd != "100 USD"

    def test_less_than(self):
        """Less than comparison."""
        a = Currency(code="USD", amount=Decimal("50"))
        b = Currency(code="USD", amount=Decimal("100"))
        assert a < b
        assert not b < a

    def test_less_than_or_equal(self):
        """Less than or equal comparison."""
        a = Currency(code="USD", amount=Decimal("50"))
        b = Currency(code="USD", amount=Decimal("100"))
        c = Currency(code="USD", amount=Decimal("50"))
        assert a <= b
        assert a <= c
        assert not b <= a

    def test_greater_than(self):
        """Greater than comparison."""
        a = Currency(code="USD", amount=Decimal("100"))
        b = Currency(code="USD", amount=Decimal("50"))
        assert a > b
        assert not b > a

    def test_greater_than_or_equal(self):
        """Greater than or equal comparison."""
        a = Currency(code="USD", amount=Decimal("100"))
        b = Currency(code="USD", amount=Decimal("50"))
        c = Currency(code="USD", amount=Decimal("100"))
        assert a >= b
        assert a >= c
        assert not b >= a

    def test_compare_different_currencies_error(self):
        """Cannot compare different currencies."""
        usd = Currency(code="USD", amount=Decimal("100"))
        eur = Currency(code="EUR", amount=Decimal("50"))
        with pytest.raises(ValueError, match="Cannot compare"):
            usd < eur


class TestSerialization:
    """Test serialization methods."""

    def test_str(self):
        """String representation."""
        usd = Currency(code="USD", amount=Decimal("100.50"))
        assert str(usd) == "100.50 USD"

    def test_repr(self):
        """Developer representation."""
        usd = Currency(code="USD", amount=Decimal("100.50"))
        assert repr(usd) == "Currency(code='USD', amount=Decimal('100.50'))"

    def test_to_dict(self):
        """Dict serialization."""
        usd = Currency(code="USD", amount=Decimal("100.50"))
        d = usd.to_dict()
        assert d == {"currency": "USD", "amount": "100.50"}

    def test_hash(self):
        """Currency is hashable."""
        usd1 = Currency(code="USD", amount=Decimal("100"))
        usd2 = Currency(code="USD", amount=Decimal("100"))

        # Same currencies should have same hash
        assert hash(usd1) == hash(usd2)

        # Can be used in sets
        s = {usd1, usd2}
        assert len(s) == 1


class TestUtilityMethods:
    """Test utility methods."""

    def test_zero(self):
        """Create zero currency."""
        usd = Currency.zero("USD")
        assert usd.code == "USD"
        assert usd.amount == Decimal("0")

    def test_is_zero(self):
        """Check if zero."""
        zero = Currency(code="USD", amount=Decimal("0"))
        nonzero = Currency(code="USD", amount=Decimal("100"))
        assert zero.is_zero()
        assert not nonzero.is_zero()

    def test_is_positive(self):
        """Check if positive."""
        pos = Currency(code="USD", amount=Decimal("100"))
        neg = Currency(code="USD", amount=Decimal("-100"))
        zero = Currency(code="USD", amount=Decimal("0"))
        assert pos.is_positive()
        assert not neg.is_positive()
        assert not zero.is_positive()

    def test_is_negative(self):
        """Check if negative."""
        pos = Currency(code="USD", amount=Decimal("100"))
        neg = Currency(code="USD", amount=Decimal("-100"))
        zero = Currency(code="USD", amount=Decimal("0"))
        assert neg.is_negative()
        assert not pos.is_negative()
        assert not zero.is_negative()


class TestOldNew:
    """Test OldNew generic class."""

    def test_basic_usage(self):
        """Basic OldNew usage."""
        from backend.app.schemas.common import OldNew

        change = OldNew(old="Technology", new="Industrials")
        assert change.old == "Technology"
        assert change.new == "Industrials"

    def test_none_old(self):
        """OldNew with None old value (first time set)."""
        from backend.app.schemas.common import OldNew

        change = OldNew(old=None, new="Technology")
        assert change.old is None
        assert change.new == "Technology"
