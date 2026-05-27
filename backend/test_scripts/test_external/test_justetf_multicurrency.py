"""
JustETF provider multi-currency tests.

Validates that all 4 supported currencies (EUR, USD, CHF, GBP) work correctly:
- EUR: current value ✅ + history ✅
- USD/CHF/GBP: current value → NOT_SUPPORTED + history ✅
- Search returns 4× results per ETF match with flag emojis
"""

import sys
from datetime import date, timedelta

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.db import IdentifierType

sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.asset_source import AssetSourceError
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.test_scripts.test_utils import print_section, print_success

# Discover providers
AssetProviderRegistry.auto_discover()

ISIN = "IE00B4L5Y983"  # iShares Core MSCI World UCITS ETF USD (Acc)
NON_EUR_CURRENCIES = ("USD", "CHF", "GBP")


def _get_provider():
    provider = AssetProviderRegistry.get_provider_instance("justetf")
    assert provider is not None, "JustETF provider not registered"
    return provider


@pytest.mark.asyncio
async def test_current_value_eur():
    """EUR current value should succeed (gettex WebSocket)."""
    print_section("JustETF: Current Value EUR")
    provider = _get_provider()

    result = await provider.get_current_value(ISIN, IdentifierType.ISIN, {"currency": "EUR"})
    assert result.value > 0
    assert result.currency == "EUR"
    print_success(f"EUR current: {result.value} {result.currency}")


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", NON_EUR_CURRENCIES)
async def test_current_value_non_eur_rejected(currency: str):
    """Non-EUR current value should raise NOT_SUPPORTED."""
    print_section(f"JustETF: Current Value {currency} → NOT_SUPPORTED")
    provider = _get_provider()

    with pytest.raises(AssetSourceError) as exc_info:
        await provider.get_current_value(ISIN, IdentifierType.ISIN, {"currency": currency})

    assert "NOT_SUPPORTED" in str(exc_info.value) or "only available in EUR" in str(exc_info.value)
    print_success(f"{currency} current correctly rejected")


@pytest.mark.asyncio
@pytest.mark.parametrize("currency", ("EUR", "USD", "CHF", "GBP"))
async def test_history_all_currencies(currency: str):
    """Historical data should work for all 4 currencies."""
    print_section(f"JustETF: History {currency}")
    provider = _get_provider()

    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    result = await provider.get_history_value(ISIN, IdentifierType.ISIN, {"currency": currency}, start_date, end_date)

    assert hasattr(result, "prices")
    assert len(result.prices) > 0, f"No prices returned for {currency}"

    first = result.prices[0]
    assert first.close > 0
    print_success(f"{currency} history: {len(result.prices)} points, first={first.close}")


@pytest.mark.asyncio
async def test_search_multicurrency():
    """Search should return 4 results per ETF match (one per currency)."""
    print_section("JustETF: Search Multi-Currency")
    provider = _get_provider()

    results = await provider.search("IE00B4L5Y983")

    # Exact ISIN search should match 1 ETF × 4 currencies = 4 results
    assert len(results) == 4, f"Expected 4 results, got {len(results)}"

    currencies_found = {r["currency"] for r in results}
    assert currencies_found == {"EUR", "USD", "CHF", "GBP"}

    # All should have same identifier
    for r in results:
        assert r["identifier"] == ISIN
        assert r["identifier_type"] == IdentifierType.ISIN
        assert r["type"] == "ETF"

    # Check flag emojis in display names
    flags_found = set()
    for r in results:
        name = r["display_name"]
        if "🇪🇺" in name:
            flags_found.add("EUR")
        if "🇺🇸" in name:
            flags_found.add("USD")
        if "🇨🇭" in name:
            flags_found.add("CHF")
        if "🇬🇧" in name:
            flags_found.add("GBP")
    assert flags_found == {"EUR", "USD", "CHF", "GBP"}

    # Check 👑 is on exactly one result (the fund currency)
    crown_results = [r for r in results if "👑" in r["display_name"]]
    assert len(crown_results) == 1, f"Expected 1 crown result, got {len(crown_results)}"
    # iShares Core MSCI World is USD-denominated
    assert crown_results[0]["currency"] == "USD"

    print_success("Search returned 4 currency variants with correct flags and 👑")


def test_params_schema():
    """params_schema should include currency select field."""
    print_section("JustETF: params_schema")
    provider = _get_provider()

    schema = provider.params_schema
    assert len(schema) == 1

    field = schema[0]
    assert field["key"] == "currency"
    assert field["type"] == "select"
    assert set(field["options"]) == {"EUR", "USD", "CHF", "GBP"}
    assert field["default"] == "EUR"

    print_success("params_schema correct")


def test_validate_params():
    """validate_params should accept valid currencies and reject invalid ones."""
    print_section("JustETF: validate_params")
    provider = _get_provider()

    # Valid
    provider.validate_params(None)
    provider.validate_params({})
    provider.validate_params({"currency": "EUR"})
    provider.validate_params({"currency": "USD"})
    provider.validate_params({"currency": "CHF"})
    provider.validate_params({"currency": "GBP"})

    # Invalid
    with pytest.raises(AssetSourceError):
        provider.validate_params({"currency": "JPY"})

    with pytest.raises(AssetSourceError):
        provider.validate_params({"currency": "INVALID"})

    print_success("validate_params correct")
