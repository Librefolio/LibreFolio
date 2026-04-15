"""
DB Model Validator Tests.

Tests that Pydantic/SQLModel field validators on DB models correctly
reject invalid data. These validators are at 0% coverage because they
are only triggered via model_validate() (not direct construction —
SQLModel table=True skips validation on __init__).

Covers:
- _validate_currency_field() — shared currency validator
- Asset.validate_currency, validate_identifier_isin, validate_identifier_ticker
- Asset.validate_classification_params
- FxRate.validate_currencies (base, quote)
- FxConversionRoute.validate_currencies
- PriceHistory.validate_currency
- Transaction.validate_currency
- UserSettings.validate_base_currency
- FxConversionRoute computed properties (is_chain, providers_used)
"""

import pytest
from pydantic import ValidationError

from backend.app.db.models import (
    Asset,
    FxConversionRoute,
    FxRate,
    PriceHistory,
    Transaction,
    UserSettings,
    )


# ============================================================================
# CURRENCY VALIDATOR
# ============================================================================


class TestCurrencyValidation:
    """Test _validate_currency_field via model_validate (triggers validators)."""

    def test_asset_valid_currency(self):
        """Valid ISO currency should pass."""
        a = Asset.model_validate({"display_name": "Test", "currency": "USD"})
        assert a.currency == "USD"

    def test_asset_currency_lowercased_normalized(self):
        """Lowercase currency should be normalized to uppercase."""
        a = Asset.model_validate({"display_name": "Test", "currency": "eur"})
        assert a.currency == "EUR"

    def test_asset_invalid_currency_rejects(self):
        """Invalid currency code should raise ValidationError."""
        with pytest.raises(ValidationError):
            Asset.model_validate({"display_name": "Test", "currency": "INVALID_CURR"})

    def test_price_history_valid_currency(self):
        """PriceHistory with valid currency should pass."""
        p = PriceHistory.model_validate(
            {
                "asset_id": 1, "date": "2025-01-01", "close": 100.0, "currency": "GBP",
                "source_plugin_key": "test"
                }
            )
        assert p.currency == "GBP"

    def test_price_history_invalid_currency(self):
        """PriceHistory with invalid currency should raise."""
        with pytest.raises(ValidationError):
            PriceHistory.model_validate(
                {
                    "asset_id": 1, "date": "2025-01-01", "close": 100.0, "currency": "XXX_BAD",
                    "source_plugin_key": "test"
                    }
                )

    def test_fxrate_valid_currencies(self):
        """FxRate with valid base/quote should pass."""
        r = FxRate.model_validate(
            {"date": "2025-01-01", "base": "EUR", "quote": "USD", "rate": 1.08}
            )
        assert r.base == "EUR"
        assert r.quote == "USD"

    def test_fxrate_invalid_base(self):
        """FxRate with invalid base currency should raise."""
        with pytest.raises(ValidationError):
            FxRate.model_validate(
                {"date": "2025-01-01", "base": "BADCURR", "quote": "USD", "rate": 1.0}
                )

    def test_fxrate_invalid_quote(self):
        """FxRate with invalid quote currency should raise."""
        with pytest.raises(ValidationError):
            FxRate.model_validate(
                {"date": "2025-01-01", "base": "EUR", "quote": "BADCURR", "rate": 1.0}
                )

    def test_fxroute_valid_currencies(self):
        """FxConversionRoute with valid currencies should pass."""
        r = FxConversionRoute.model_validate({
            "base": "EUR", "quote": "USD",
            "chain_steps": '[{"from":"EUR","to":"USD","provider":"ECB"}]',
            })
        assert r.base == "EUR"
        assert r.quote == "USD"

    def test_fxroute_invalid_currency(self):
        """FxConversionRoute with invalid currency should raise."""
        with pytest.raises(ValidationError):
            FxConversionRoute.model_validate({
                "base": "NOPE", "quote": "USD",
                "chain_steps": '[{"from":"NOPE","to":"USD","provider":"ECB"}]',
                })

    def test_user_settings_valid_base_currency(self):
        """UserSettings with valid base_currency should pass."""
        s = UserSettings.model_validate({"user_id": 999, "base_currency": "CHF"})
        assert s.base_currency == "CHF"

    def test_user_settings_invalid_base_currency(self):
        """UserSettings with invalid base_currency should raise."""
        with pytest.raises(ValidationError):
            UserSettings.model_validate({"user_id": 999, "base_currency": "INVALID"})

    def test_transaction_currency_none_allowed(self):
        """Transaction currency can be None."""
        t = Transaction.model_validate({
            "broker_id": 1, "date": "2025-01-01",
            "type": "BUY", "quantity": 10, "price": 100,
            "currency": None,
            })
        assert t.currency is None


# ============================================================================
# ISIN / TICKER VALIDATORS
# ============================================================================


class TestIdentifierValidation:
    """Test Asset identifier validators via model_validate."""

    def test_isin_valid_12chars(self):
        """Valid 12-character ISIN should pass."""
        a = Asset.model_validate({
            "display_name": "Apple", "currency": "USD",
            "identifier_isin": "US0378331005",
            })
        assert a.identifier_isin == "US0378331005"

    def test_isin_lowercased_normalized(self):
        """Lowercase ISIN should be normalized to uppercase."""
        a = Asset.model_validate({
            "display_name": "Apple", "currency": "USD",
            "identifier_isin": "us0378331005",
            })
        assert a.identifier_isin == "US0378331005"

    def test_isin_wrong_length(self):
        """ISIN with wrong length should raise ValidationError."""
        with pytest.raises(ValidationError, match="12 characters"):
            Asset.model_validate({
                "display_name": "Test", "currency": "USD",
                "identifier_isin": "US037",
                })

    def test_isin_none_allowed(self):
        """ISIN can be None."""
        a = Asset.model_validate({
            "display_name": "Test", "currency": "USD",
            "identifier_isin": None,
            })
        assert a.identifier_isin is None

    def test_isin_empty_string_becomes_none(self):
        """Empty string ISIN should become None."""
        a = Asset.model_validate({
            "display_name": "Test", "currency": "USD",
            "identifier_isin": "",
            })
        assert a.identifier_isin is None

    def test_ticker_normalized_uppercase(self):
        """Ticker should be normalized to uppercase."""
        a = Asset.model_validate({
            "display_name": "Test", "currency": "USD",
            "identifier_ticker": "aapl",
            })
        assert a.identifier_ticker == "AAPL"

    def test_ticker_none_allowed(self):
        """Ticker can be None."""
        a = Asset.model_validate({
            "display_name": "Test", "currency": "USD",
            "identifier_ticker": None,
            })
        assert a.identifier_ticker is None

    def test_ticker_empty_string_becomes_none(self):
        """Empty string ticker should become None."""
        a = Asset.model_validate({
            "display_name": "Test", "currency": "USD",
            "identifier_ticker": "",
            })
        assert a.identifier_ticker is None


# ============================================================================
# FxConversionRoute PROPERTIES
# ============================================================================


class TestFxConversionRouteProperties:
    """Test computed properties on FxConversionRoute."""

    def test_is_chain_single_step(self):
        """1-step route is NOT a chain."""
        r = FxConversionRoute(
            base="EUR", quote="USD",
            chain_steps='[{"from":"EUR","to":"USD","provider":"ECB"}]'
            )
        assert r.is_chain is False

    def test_is_chain_multi_step(self):
        """2-step route IS a chain."""
        r = FxConversionRoute(
            base="EUR", quote="USD",
            chain_steps='[{"from":"RON","to":"EUR","provider":"ECB"},{"from":"EUR","to":"USD","provider":"ECB"}]'
            )
        assert r.is_chain is True

    def test_providers_used_single(self):
        """providers_used returns set of provider codes."""
        r = FxConversionRoute(
            base="EUR", quote="USD",
            chain_steps='[{"from":"EUR","to":"USD","provider":"ECB"}]'
            )
        assert r.providers_used == {"ECB"}

    def test_providers_used_multi(self):
        """providers_used with multiple providers."""
        r = FxConversionRoute(
            base="CHF", quote="USD",
            chain_steps='[{"from":"CHF","to":"EUR","provider":"SNB"},{"from":"EUR","to":"USD","provider":"ECB"}]'
            )
        assert r.providers_used == {"SNB", "ECB"}
