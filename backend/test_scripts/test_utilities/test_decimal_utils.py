"""
Test decimal precision utilities.
All test is independent of the others, so help use pytest features.
"""

from decimal import Decimal

import pytest

from backend.app.db.models import FxRate, PriceHistory, Transaction
from backend.app.db.precision import get_model_column_precision, truncate_fx_rate, truncate_priceHistory, truncate_to_db_precision
from backend.app.utils.decimal_utils import parse_decimal_value


def test_get_model_column_precision_price_history():
    """Test getting precision from PriceHistory columns."""
    # C-97a: the price columns are RealDecimal(24, 12): a PEPE close of 0.0000034573 keeps its digits
    for column in ["open", "high", "low", "close", "adjusted_close"]:
        precision, scale = get_model_column_precision(PriceHistory, column)
        assert precision == 24, f"{column}: expected precision 24, got {precision}"
        assert scale == 12, f"{column}: expected scale 12, got {scale}"


def test_get_model_column_precision_fx_rate():
    """Test getting precision from FxRate.rate column."""
    precision, scale = get_model_column_precision(FxRate, "rate")
    assert precision == 24, f"Expected precision 24, got {precision}"
    assert scale == 10, f"Expected scale 10, got {scale}"


def test_get_model_column_precision_transaction():
    """Test getting precision from Transaction numeric columns."""
    # C-97a: quantity is RealDecimal(22, 10) (crypto quantities); amount stays NUMERIC(18, 6)
    for column, expected in {"quantity": (22, 10), "amount": (18, 6)}.items():
        found = get_model_column_precision(Transaction, column)
        assert found == expected, f"{column}: expected {expected}, got {found}"


def test_get_model_column_precision_price_history_volume():
    """Test getting precision from integer-like numeric columns."""
    precision, scale = get_model_column_precision(PriceHistory, "volume")

    assert precision == 24
    assert scale == 0


def test_get_model_column_precision_invalid_column():
    """Test error when column doesn't exist."""
    with pytest.raises(ValueError, match="Column 'invalid' not found"):
        get_model_column_precision(PriceHistory, "invalid")


def test_get_model_column_precision_non_numeric():
    """Test error when column is not Numeric type."""
    with pytest.raises(ValueError, match="not Numeric type"):
        get_model_column_precision(PriceHistory, "currency")


def test_truncate_to_db_precision_price():
    """Test truncating price values to the price_history scale (C-97a: RealDecimal(24, 12))."""
    value = Decimal("175.1234567890123")
    truncated = truncate_to_db_precision(value, PriceHistory, "close")

    assert truncated == Decimal("175.123456789012")
    assert -truncated.normalize().as_tuple().exponent == 12  # 12 decimals left


def test_truncate_to_db_precision_fx_rate():
    """Test truncating FX rate to NUMERIC(24, 10)."""
    value = Decimal("1.08501234567890")
    truncated = truncate_to_db_precision(value, FxRate, "rate")

    assert truncated == Decimal("1.0850123456")
    assert len(str(truncated).split(".")[1]) == 10  # Exactly 10 decimals


def test_truncate_price_to_db_precision_convenience():
    """Test convenience function for price truncation."""
    value = Decimal("99.9999999999999")
    truncated = truncate_priceHistory(value)

    assert truncated == Decimal("99.999999999999")  # C-97a: 12 decimals, ROUND_DOWN


def test_truncate_fx_rate_to_db_precision_convenience():
    """Test convenience function for FX rate truncation."""
    value = Decimal("1.123456789012345")
    truncated = truncate_fx_rate(value)

    assert truncated == Decimal("1.1234567890")


# ============================================================================
# TESTS: Edge cases
# ============================================================================


def test_truncate_preserves_small_values():
    """Test that small values are preserved correctly."""
    value = Decimal("0.000001")  # Exactly at scale limit
    truncated = truncate_to_db_precision(value, PriceHistory, "close")

    assert truncated == Decimal("0.000001")


def test_truncate_large_values():
    """Test that large values are truncated correctly."""
    value = Decimal("999999999999.123456789")
    truncated = truncate_to_db_precision(value, PriceHistory, "close")

    # C-97a: a price keeps at most 15 significant digits (what a REAL holds), ROUND_DOWN
    assert truncated == Decimal("999999999999.123")


def test_truncate_negative_values():
    """Test that negative values are truncated correctly."""
    value = Decimal("-123.456789")
    truncated = truncate_to_db_precision(value, PriceHistory, "close")

    assert truncated == Decimal("-123.456789")  # Already within precision


def test_truncate_zero():
    """Test that zero is handled correctly."""
    value = Decimal("0.0")
    truncated = truncate_to_db_precision(value, PriceHistory, "close")

    assert truncated == Decimal("0.0")


def test_no_false_update_detection():
    """Test that truncation prevents false update detection."""
    # Simulate a value that came from an external API (more decimals than price_history keeps: 12)
    external_value = Decimal("175.1234567890123")

    # Truncate before comparing with DB value
    truncated = truncate_priceHistory(external_value)

    # Simulate DB value (already truncated on write)
    db_value = Decimal("175.123456789012")

    # They should match after truncation
    assert truncated == db_value


# ============================================================================
# TESTS: parse_decimal_value helper
# ============================================================================


def test_parse_decimal_value_from_decimal():
    """Test parsing already Decimal value."""
    value = Decimal("123.456")
    result = parse_decimal_value(value)
    assert result == value


def test_parse_decimal_value_from_string():
    """Test parsing string to Decimal."""
    value = "123.456"
    result = parse_decimal_value(value)
    assert result == Decimal("123.456")


def test_parse_decimal_value_from_int():
    """Test parsing int to Decimal."""
    value = 123
    result = parse_decimal_value(value)
    assert result == Decimal("123")


def test_parse_decimal_value_from_float():
    """Test parsing float to Decimal."""
    value = 123.456
    result = parse_decimal_value(value)
    assert isinstance(result, Decimal)
    assert result == Decimal("123.456")


def test_parse_decimal_value_from_negative_string():
    """Test parsing signed string values to Decimal."""
    result = parse_decimal_value("-0.125")

    assert result == Decimal("-0.125")


def test_parse_decimal_value_none():
    """Test parsing None returns None."""
    result = parse_decimal_value(None)
    assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
