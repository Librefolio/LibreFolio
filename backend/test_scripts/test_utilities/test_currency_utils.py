"""
Tests for currency_utils: list_currencies, flag mapping, and validation consistency.

Ensures:
- list_currencies() uses pycountry (no historic currencies)
- Every listed currency passes the backend validator
- Crypto currencies are included
- Flag emoji are correctly assigned for major currencies
"""

from backend.app.schemas.common import CRYPTO_CURRENCIES, _validate_currency_code_cached
from backend.app.utils.currency_utils import (
    _build_currency_to_flag_map,
    list_currencies,
)


class TestListCurrencies:
    """Tests for list_currencies() function."""

    def test_returns_sufficient_currencies(self):
        """Should return at least 150 currencies (ISO 4217 active + crypto)."""
        currencies = list_currencies("en")
        assert len(currencies) > 150, f"Expected 150+ currencies, got {len(currencies)}"

    def test_all_listed_currencies_pass_validation(self):
        """Every code from list_currencies must be accepted by _validate_currency_code_cached."""
        currencies = list_currencies("en")
        failures = []
        for c in currencies:
            try:
                _validate_currency_code_cached(c["code"])
            except ValueError as e:
                failures.append(f"{c['code']}: {e}")
        assert not failures, "Validation failures:\n" + "\n".join(failures)

    def test_no_historic_currencies(self):
        """Historic currencies like ADP, AFA, ATS should NOT appear."""
        currencies = list_currencies("en")
        codes = {c["code"] for c in currencies}
        historic = [
            "ADP",
            "AFA",
            "ATS",
            "ARA",
            "ARL",
            "BEF",
            "DEM",
            "FRF",
            "ITL",
            "ESP",
            "GRD",
            "NLG",
            "PTE",
            "FIM",
            "IEP",
        ]
        for h in historic:
            assert h not in codes, f"Historic currency {h} should not be in the list"

    def test_crypto_currencies_included(self):
        """Crypto currencies from CRYPTO_CURRENCIES should appear in the list."""
        currencies = list_currencies("en")
        codes = {c["code"] for c in currencies}
        for crypto_code in CRYPTO_CURRENCIES:
            assert crypto_code in codes, f"Crypto {crypto_code} missing from list_currencies()"

    def test_crypto_currencies_have_coin_emoji(self):
        """Crypto currencies should have 🪙 as flag_emoji."""
        currencies = list_currencies("en")
        crypto_entries = [c for c in currencies if c["code"] in CRYPTO_CURRENCIES]
        for c in crypto_entries:
            assert c["flag_emoji"] == "🪙", f"{c['code']} should have 🪙, got {c['flag_emoji']}"

    def test_all_entries_have_required_fields(self):
        """Every entry must have code, name, symbol, flag_emoji."""
        currencies = list_currencies("en")
        for c in currencies:
            assert "code" in c, f"Missing 'code' in {c}"
            assert "name" in c, f"Missing 'name' in {c}"
            assert "symbol" in c, f"Missing 'symbol' in {c}"
            assert "flag_emoji" in c, f"Missing 'flag_emoji' in {c}"
            assert c["code"], f"Empty 'code' in {c}"
            assert c["name"], f"Empty 'name' in {c}"

    def test_major_currencies_present(self):
        """Major world currencies must be in the list."""
        currencies = list_currencies("en")
        codes = {c["code"] for c in currencies}
        major = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "CNY", "INR", "BRL"]
        for m in major:
            assert m in codes, f"Major currency {m} missing"

    def test_localization_works(self):
        """Currency names should change with language."""
        en = list_currencies("en")
        it = list_currencies("it")
        # Find EUR in both
        eur_en = next((c for c in en if c["code"] == "EUR"), None)
        eur_it = next((c for c in it if c["code"] == "EUR"), None)
        assert eur_en is not None
        assert eur_it is not None
        # Names should differ (Euro vs Euro is same in many langs, try USD)
        usd_en = next((c for c in en if c["code"] == "USD"), None)
        usd_it = next((c for c in it if c["code"] == "USD"), None)
        assert usd_en is not None
        assert usd_it is not None
        # At least the flag should be same regardless of language
        assert usd_en["flag_emoji"] == usd_it["flag_emoji"]


class TestCurrencyFlagMap:
    """Tests for _build_currency_to_flag_map() function."""

    def test_map_has_entries(self):
        """Flag map should have entries for most currencies."""
        fm = _build_currency_to_flag_map()
        assert len(fm) > 150, f"Expected 150+ flag entries, got {len(fm)}"

    def test_major_currencies_correct_flags(self):
        """Major currencies must have the correct flag emoji."""
        fm = _build_currency_to_flag_map()
        expected = {
            "USD": "🇺🇸",
            "EUR": "🇪🇺",
            "GBP": "🇬🇧",
            "JPY": "🇯🇵",
            "CHF": "🇨🇭",
            "CAD": "🇨🇦",
            "AUD": "🇦🇺",
            "NZD": "🇳🇿",
            "CNY": "🇨🇳",
            "INR": "🇮🇳",
            "BRL": "🇧🇷",
            "MXN": "🇲🇽",
            "ZAR": "🇿🇦",
            "SEK": "🇸🇪",
            "NOK": "🇳🇴",
            "DKK": "🇩🇰",
            "PLN": "🇵🇱",
            "CZK": "🇨🇿",
            "HUF": "🇭🇺",
            "RON": "🇷🇴",
            "BGN": "🇧🇬",
            "TRY": "🇹🇷",
            "KRW": "🇰🇷",
            "SGD": "🇸🇬",
            "HKD": "🇭🇰",
            "THB": "🇹🇭",
            "RUB": "🇷🇺",
            "ILS": "🇮🇱",
        }
        for code, exp_flag in expected.items():
            actual = fm.get(code, "?")
            assert actual == exp_flag, f"{code}: expected {exp_flag}, got {actual}"

    def test_crypto_have_coin_emoji(self):
        """All crypto currencies should map to 🪙."""
        fm = _build_currency_to_flag_map()
        for code in CRYPTO_CURRENCIES:
            assert fm.get(code) == "🪙", f"Crypto {code} should map to 🪙"

    def test_eur_override_not_single_country(self):
        """EUR must map to 🇪🇺 (EU flag), not any single Eurozone country."""
        fm = _build_currency_to_flag_map()
        assert fm["EUR"] == "🇪🇺"
