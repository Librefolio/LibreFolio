"""
Test decimal precision utilities.
All test is independent of the others, so help use pytest features.
"""
from decimal import Decimal

import pytest

from backend.app.db.models import PriceHistory, FxRate, Transaction
from backend.app.utils.decimal_utils import (
    get_model_column_precision,
    truncate_to_db_precision,
    truncate_price_to_db_precision,
    truncate_fx_rate_to_db_precision,
    )


def test_get_model_column_precision_price_history():
    """Test getting precision from PriceHistory columns."""
    # All price columns should be NUMERIC(18, 6)
    for column in ["open", "high", "low", "close", "adjusted_close"]:
        precision, scale = get_model_column_precision(PriceHistory, column)
        assert precision == 18, f"{column}: expected precision 18, got {precision}"
        assert scale == 6, f"{column}: expected scale 6, got {scale}"


def test_get_model_column_precision_fx_rate():
    """Test getting precision from FxRate.rate column."""
    precision, scale = get_model_column_precision(FxRate, "rate")
    assert precision == 24, f"Expected precision 24, got {precision}"
    assert scale == 10, f"Expected scale 10, got {scale}"


def test_get_model_column_precision_transaction():
    """Test getting precision from Transaction numeric columns."""
    for column in ["quantity", "price"]:
        precision, scale = get_model_column_precision(Transaction, column)
        assert precision == 18, f"{column}: expected precision 18, got {precision}"
        assert scale == 6, f"{column}: expected scale 6, got {scale}"


def test_get_model_column_precision_invalid_column():
    """Test error when column doesn't exist."""
    with pytest.raises(ValueError, match="Column 'invalid' not found"):
        get_model_column_precision(PriceHistory, "invalid")


def test_get_model_column_precision_non_numeric():
    """Test error when column is not Numeric type."""
    with pytest.raises(ValueError, match="not Numeric type"):
        get_model_column_precision(PriceHistory, "currency")


def test_truncate_to_db_precision_price():
    """Test truncating price values to NUMERIC(18, 6)."""
    value = Decimal("175.123456789")
    truncated = truncate_to_db_precision(value, PriceHistory, "close")

    assert truncated == Decimal("175.123456")
    assert len(str(truncated).split('.')[1]) == 6  # Exactly 6 decimals


def test_truncate_to_db_precision_fx_rate():
    """Test truncating FX rate to NUMERIC(24, 10)."""
    value = Decimal("1.08501234567890")
    truncated = truncate_to_db_precision(value, FxRate, "rate")

    assert truncated == Decimal("1.0850123456")
    assert len(str(truncated).split('.')[1]) == 10  # Exactly 10 decimals


def test_truncate_price_to_db_precision_convenience():
    """Test convenience function for price truncation."""
    value = Decimal("99.999999999")
    truncated = truncate_price_to_db_precision(value)

    assert truncated == Decimal("99.999999")


def test_truncate_fx_rate_to_db_precision_convenience():
    """Test convenience function for FX rate truncation."""
    value = Decimal("1.123456789012345")
    truncated = truncate_fx_rate_to_db_precision(value)

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

    assert truncated == Decimal("999999999999.123456")


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
    # Simulate a value that came from an external API
    external_value = Decimal("175.123456789")

    # Truncate before comparing with DB value
    truncated = truncate_price_to_db_precision(external_value)

    # Simulate DB value (already truncated by SQLite)
    db_value = Decimal("175.123456")

    # They should match after truncation
    assert truncated == db_value

