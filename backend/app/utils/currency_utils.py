"""
Currency utilities with multi-language support via Babel.

Provides normalization and listing of currencies with localized names and symbols.
"""

from typing import List

import structlog
from babel.numbers import get_currency_symbol, get_currency_name

from backend.app.utils.translation_utils import get_babel_locale

logger = structlog.get_logger(__name__)

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


def normalize_currency(input_str: str, language: str = 'en') -> dict:
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
            "error": "Empty input"
            }

    input_clean = input_str.strip().upper()
    locale = get_babel_locale(language)

    # Try direct ISO code match
    try:
        # Check if it's a valid currency by trying to get its symbol
        symbol = get_currency_symbol(input_clean, locale=locale)
        if symbol:
            return {
                "query": input_str,
                "iso_codes": [input_clean],
                "match_type": "exact",
                "error": None
                }
    except Exception:
        pass

    # Try symbol match
    if input_clean in SYMBOL_TO_ISO or input_str.strip() in SYMBOL_TO_ISO:
        symbol_key = input_clean if input_clean in SYMBOL_TO_ISO else input_str.strip()
        candidates = SYMBOL_TO_ISO[symbol_key]
        if len(candidates) == 1:
            return {
                "query": input_str,
                "iso_codes": candidates,
                "match_type": "exact",
                "error": None
                }
        else:
            return {
                "query": input_str,
                "iso_codes": candidates,
                "match_type": "symbol_ambiguous",
                "error": f"Symbol '{input_str}' matches multiple currencies"
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
            return {
                "query": input_str,
                "iso_codes": matches,
                "match_type": "exact",
                "error": None
                }
        elif len(matches) > 1:
            return {
                "query": input_str,
                "iso_codes": matches,
                "match_type": "multi-match",
                "error": f"Multiple currencies match '{input_str}'"
                }
    except Exception as e:
        logger.debug(f"Name search failed for '{input_str}'", error=str(e))

    return {
        "query": input_str,
        "iso_codes": [],
        "match_type": "not_found",
        "error": f"No currency found for '{input_str}'"
        }


def list_currencies(language: str = 'en') -> List[dict]:
    """
    List all currencies with localized names and symbols.

    Args:
        language: ISO 639-1 language code (default: 'en')

    Returns:
        List of dicts with 'code', 'name', 'symbol'
    """
    locale = get_babel_locale(language)
    currencies = []

    try:
        all_codes = sorted(locale.currencies.keys())

        for code in all_codes:
            try:
                name = get_currency_name(code, locale=locale)
                symbol = get_currency_symbol(code, locale=locale)

                if name and symbol:
                    currencies.append({
                        "code": code,
                        "name": name,
                        "symbol": symbol
                        })
            except Exception as e:
                logger.debug(f"Could not get info for currency {code}", error=str(e))
                continue
    except Exception as e:
        logger.error(f"Failed to list currencies for language {language}", error=str(e))

    return currencies
