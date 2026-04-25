"""
Currency utilities with multi-language support via Babel.

Provides normalization and listing of currencies with localized names and symbols.
Uses pycountry as source-of-truth for active ISO 4217 currencies.
Babel is used only for localized names, symbols, and territory→currency mapping.
"""

from functools import lru_cache
from typing import List

import pycountry
import structlog
from babel.core import get_global
from babel.numbers import get_currency_name, get_currency_symbol

from backend.app.schemas.common import CRYPTO_CURRENCIES
from backend.app.utils.geo_utils import iso2_to_flag_emoji
from backend.app.utils.translation_utils import get_babel_locale

logger = structlog.get_logger(__name__)

# =============================================================================
# CURRENCY → FLAG EMOJI MAPPING
# =============================================================================

# Multi-country currency overrides (flag for the "representative" entity)
# These currencies are used by multiple territories; pycountry iterates alphabetically
# so a smaller territory (e.g., American Samoa) would win over the main country (US).
_CURRENCY_FLAG_OVERRIDES: dict[str, str] = {
    # Supranational currencies
    "EUR": "🇪🇺",  # European Union (not a single country)
    "XAF": "🌍",  # CFA franc BEAC — Central Africa (multi-country)
    "XOF": "🌍",  # CFA franc BCEAO — West Africa (multi-country)
    "XCD": "🌍",  # East Caribbean dollar (multi-country)
    "XPF": "🌍",  # CFP franc — French Pacific (multi-country)
    # Major currencies used by multiple territories (alphabetical first ≠ main country)
    "USD": "🇺🇸",  # United States (not American Samoa 🇦🇸)
    "INR": "🇮🇳",  # India (not Bhutan 🇧🇹)
    "NOK": "🇳🇴",  # Norway (not Bouvet Island 🇧🇻)
    "NZD": "🇳🇿",  # New Zealand (not Cook Islands 🇨🇰)
    "ZAR": "🇿🇦",  # South Africa (not Lesotho 🇱🇸)
}


@lru_cache(maxsize=1)
def _build_currency_to_flag_map() -> dict[str, str]:
    """
    Build mapping: currency_code → flag_emoji.

    Uses Babel's territory_currencies data to find which country uses each currency
    as legal tender, then converts country ISO-2 → flag emoji.

    Multi-country currencies (EUR, XAF, etc.) use explicit overrides.
    Crypto currencies use 🪙.

    Babel territory_currencies format: dict[territory_iso2] → list of tuples
    Each tuple: (currency_code, start_date_tuple, end_date_tuple_or_None, is_tender)
    Example: ('USD', (1792, 1, 1), None, True)
    - end=None means still active
    - tender=True means legal tender
    """
    currency_to_flag: dict[str, str] = {}

    # Start with overrides (they win over auto-detected)
    currency_to_flag.update(_CURRENCY_FLAG_OVERRIDES)

    # Get Babel's territory→currencies mapping
    territory_currencies = get_global("territory_currencies")

    # Iterate all countries from pycountry
    for country in pycountry.countries:
        iso2 = country.alpha_2
        entries = territory_currencies.get(iso2, [])

        for entry in entries:
            # entry is tuple: (code, start, end, tender)
            code, _start, end, tender = entry

            # Only current (end=None) and legal tender currencies
            if end is not None or not tender:
                continue

            # Don't override multi-country currencies already set
            if code not in currency_to_flag:
                currency_to_flag[code] = iso2_to_flag_emoji(iso2)

    # Add crypto
    for code in CRYPTO_CURRENCIES:
        currency_to_flag[code] = "🪙"

    return currency_to_flag


# =============================================================================
# CURRENCY → COUNTRY CODES MAPPING (for search by nation)
# =============================================================================


@lru_cache(maxsize=1)
def _build_currency_to_countries_map() -> dict[str, list[str]]:
    """
    Build mapping: currency_code → list of ISO-2 country codes that use it.

    Only includes active legal tender currencies (end=None, tender=True).
    Used to enable searching currencies by country name.
    """
    currency_to_countries: dict[str, list[str]] = {}
    territory_currencies = get_global("territory_currencies")

    for country in pycountry.countries:
        iso2 = country.alpha_2
        entries = territory_currencies.get(iso2, [])

        for entry in entries:
            code, _start, end, tender = entry
            if end is not None or not tender:
                continue
            if code not in currency_to_countries:
                currency_to_countries[code] = []
            currency_to_countries[code].append(iso2)

    return currency_to_countries


# Map of common currency symbols to possible ISO codes
SYMBOL_TO_ISO = {
    "$": ["USD", "CAD", "AUD", "NZD", "HKD", "SGD", "MXN", "ARS", "CLP", "COP"],
    "€": ["EUR"],
    "£": ["GBP"],
    "¥": ["JPY", "CNY"],
    "₹": ["INR"],
    "₽": ["RUB"],
    "₩": ["KRW"],
    "₺": ["TRY"],
    "₱": ["PHP"],
    "₴": ["UAH"],
    "₡": ["CRC"],
    "₦": ["NGN"],
    "₨": ["PKR", "LKR", "NPR"],
    "₫": ["VND"],
    "₪": ["ILS"],
    "₮": ["MNT"],
    "₵": ["GHS"],
    "₸": ["KZT"],
    "฿": ["THB"],
    "﷼": ["IRR", "OMR", "QAR", "SAR", "YER"],
    "Fr": ["CHF"],
    "kr": ["SEK", "NOK", "DKK", "ISK"],
    "zł": ["PLN"],
    "Ft": ["HUF"],
    "Kč": ["CZK"],
    "лв": ["BGN"],
    "lei": ["RON", "MDL"],
    "R": ["ZAR"],
    "R$": ["BRL"],
}


def normalize_currency(input_str: str, language: str = "en") -> dict:
    """
    Normalize currency input to ISO 4217 code(s).

    Accepts:
    - ISO code (USD, EUR, etc.)
    - Currency symbol ($, €, etc.)
    - Localized currency name (Dollar, Euro, etc.)

    Args:
        input_str: Currency identifier in any format
        language: Language for name matching (default: 'en')

    Returns:
        Dict with:
        - query: Original input
        - iso_codes: List of matching ISO codes
        - match_type: 'exact', 'symbol_ambiguous', 'multi-match', 'not_found'
        - error: Error message if any
    """
    if not input_str:
        return {
            "query": input_str,
            "iso_codes": [],
            "match_type": "not_found",
            "error": "Empty input",
        }

    input_clean = input_str.strip().upper()
    locale = get_babel_locale(language)

    # Try direct ISO code match — accept only **strict 3-letter alpha_3 codes**
    # validated against pycountry's active list or the supported crypto set.
    # NOTE: ``babel.numbers.get_currency_symbol`` echoes the input back for
    # unknown codes, so it cannot be used as a validator. Likewise
    # ``pycountry.currencies.lookup`` does fuzzy NAME matching ("SWISS FRANC"
    # → CHF) which would skip the dedicated symbol/name branches below.
    if len(input_clean) == 3 and input_clean.isalpha():
        is_iso = pycountry.currencies.get(alpha_3=input_clean) is not None
        if is_iso or input_clean in CRYPTO_CURRENCIES:
            return {
                "query": input_str,
                "iso_codes": [input_clean],
                "match_type": "exact",
                "error": None,
            }

    # Try symbol match
    if input_clean in SYMBOL_TO_ISO or input_str.strip() in SYMBOL_TO_ISO:
        symbol_key = input_clean if input_clean in SYMBOL_TO_ISO else input_str.strip()
        candidates = SYMBOL_TO_ISO[symbol_key]
        if len(candidates) == 1:
            return {
                "query": input_str,
                "iso_codes": candidates,
                "match_type": "exact",
                "error": None,
            }
        else:
            return {
                "query": input_str,
                "iso_codes": candidates,
                "match_type": "symbol_ambiguous",
                "error": f"Symbol '{input_str}' matches multiple currencies",
            }

    # Try name match (search all currencies)
    try:
        all_currencies = list(locale.currencies.keys())
        matches = []
        input_lower = input_str.lower()

        for code in all_currencies:
            try:
                name = get_currency_name(code, locale=locale)
                if name and input_lower in name.lower():
                    matches.append(code)
            except Exception:
                continue

        if len(matches) == 1:
            return {"query": input_str, "iso_codes": matches, "match_type": "exact", "error": None}
        elif len(matches) > 1:
            return {
                "query": input_str,
                "iso_codes": matches,
                "match_type": "multi-match",
                "error": f"Multiple currencies match '{input_str}'",
            }
    except Exception as e:
        logger.debug(f"Name search failed for '{input_str}'", error=str(e))

    return {
        "query": input_str,
        "iso_codes": [],
        "match_type": "not_found",
        "error": f"No currency found for '{input_str}'",
    }


def list_currencies(language: str = "en") -> List[dict]:
    """
    List all active currencies with localized names, symbols, flag emoji, country codes, and country names.

    Source-of-truth: pycountry (only active ISO 4217 currencies).
    Babel is used only for localized names, symbols, and country name translations.
    Crypto currencies from CRYPTO_CURRENCIES are appended at the end.

    Args:
        language: ISO 639-1 language code (default: 'en')

    Returns:
        List of dicts with 'code', 'name', 'symbol', 'flag_emoji', 'country_codes', 'country_names'
    """
    locale = get_babel_locale(language)
    flag_map = _build_currency_to_flag_map()
    countries_map = _build_currency_to_countries_map()
    currencies = []

    # Pre-build localized territory names from Babel
    territory_names = locale.territories  # dict: ISO-2 → localized name

    # 1. Active ISO 4217 currencies from pycountry (source-of-truth)
    for currency in sorted(pycountry.currencies, key=lambda c: c.alpha_3):
        code = currency.alpha_3
        try:
            name = get_currency_name(code, locale=locale) or currency.name
            symbol = get_currency_symbol(code, locale=locale) or code
        except Exception:
            name = currency.name
            symbol = code

        country_codes = sorted(countries_map.get(code, []))
        # Resolve localized country names via Babel territories
        country_names = []
        for cc in country_codes:
            localized = territory_names.get(cc)
            if localized:
                country_names.append(localized)
            else:
                # Fallback to pycountry English name
                country = pycountry.countries.get(alpha_2=cc)
                country_names.append(country.name if country else cc)

        currencies.append(
            {
                "code": code,
                "name": name,
                "symbol": symbol,
                "flag_emoji": flag_map.get(code, "🏳️"),
                "country_codes": country_codes,
                "country_names": country_names,
            }
        )

    # 2. Crypto currencies (from CRYPTO_CURRENCIES dict)
    for code, crypto_name in sorted(CRYPTO_CURRENCIES.items()):
        currencies.append(
            {
                "code": code,
                "name": crypto_name,
                "symbol": code,
                "flag_emoji": "🪙",
                "country_codes": [],
                "country_names": [],
            }
        )

    return currencies
