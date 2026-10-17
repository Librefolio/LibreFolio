"""
Utility endpoints for frontend support.

Provides helper endpoints for:
- Currency normalization and listing
- Country listing with multi-language support
- Sector classification listing
- Other frontend utilities
"""

from fastapi import APIRouter, Query

from backend.app.schemas.common import is_canonical_iso_currency, iso_currency_candidates, suggested_iso_currency
from backend.app.schemas.utilities import (
    CountryListItem,
    CountryListResponse,
    CurrencyListItem,
    CurrencyListResponse,
    CurrencyNormalizationResponse,
    CurrencySuggestionResponse,
    SectorItem,
    SectorListResponse,
)
from backend.app.utils.asset.geo import (
    list_countries as list_countries_util,
)
from backend.app.utils.asset.sector import ALLOCATION_BUCKETS, SECTOR_EMOJI_FALLBACK, FinancialSector, sector_emoji
from backend.app.utils.fx.currency import (
    list_currencies as list_currencies_util,
)
from backend.app.utils.fx.currency import (
    normalize_currency,
)

router = APIRouter(prefix="/utilities", tags=["Utilities"])


@router.get("/sectors", response_model=SectorListResponse)
async def list_sectors(include_other: bool = Query(True, description="Include 'Other' in the list")):
    """
    Get list of all standard financial sectors, with their emoji.

    Returns the list of sectors that the system recognizes and stores.
    Based on GICS (Global Industry Classification Standard).

    The emoji come from the one map of `utils/asset/sector.py`, which the allocation views of the portfolio engine read
    too. `buckets` lists the two allocation buckets the engine adds beside the sectors, the cash and the holdings
    without a sector: never a sector to choose, listed for their emoji. `fallback_emoji` is the glyph of a key outside
    both lists.

    **Example Request**:
    ```
    GET /api/v1/utilities/sectors
    GET /api/v1/utilities/sectors?include_other=false
    ```

    **Response** (items shortened):
    ```json
    {
      "items": [
        {"key": "Industrials", "emoji": "🏭"},
        {"key": "Technology", "emoji": "💻"},
        {"key": "Other", "emoji": "📦"}
      ],
      "buckets": [
        {"key": "Liquidity", "emoji": "💰"},
        {"key": "Unknown", "emoji": "❓"}
      ],
      "fallback_emoji": "❓"
    }
    ```
    """
    if include_other:
        sectors = FinancialSector.list_all_with_other()
    else:
        sectors = FinancialSector.list_all()

    items = [SectorItem(key=s, emoji=sector_emoji(s)) for s in sectors]
    buckets = [SectorItem(key=bucket, emoji=sector_emoji(bucket)) for bucket in ALLOCATION_BUCKETS]
    return SectorListResponse(items=items, buckets=buckets, fallback_emoji=SECTOR_EMOJI_FALLBACK)


@router.get("/countries", response_model=CountryListResponse)
async def list_countries(
    language: str = Query("en", description="Language for country names (default: en)"),
    include_other: bool = Query(True, description="Append 'Other' catch-all entry at the end"),
):
    """
    Get list of all countries with ISO codes and flag emoji.

    Returns all ISO-3166 countries with:
    - ISO-3166-A3 code (e.g., USA)
    - ISO-3166-A2 code (e.g., US)
    - Country name in requested language (via Babel)
    - Flag emoji (e.g., 🇺🇸)

    When `include_other` is True (default), an additional "Other" entry
    is appended at the end for catch-all geographic allocation.

    **Supported Languages**:
    - en (English) - default
    - it (Italian)
    - fr (French)
    - es (Spanish)
    - Other languages supported by Babel
    - Falls back to English if language not supported

    **Example Request**:
    ```
    GET /api/v1/utilities/countries
    GET /api/v1/utilities/countries?language=it
    ```

    **Response**:
    ```json
    {
      "countries": [
        {"iso3": "USA", "iso2": "US", "name": "Stati Uniti", "flag_emoji": "🇺🇸"},
        {"iso3": "ITA", "iso2": "IT", "name": "Italia", "flag_emoji": "🇮🇹"},
        ...
      ],
      "count": 249,
      "language": "it"
    }
    ```
    """
    countries_data = list_countries_util(language)
    countries = [CountryListItem(**c) for c in countries_data]

    if include_other:
        OTHER_NAMES = {"en": "Other", "it": "Altro", "fr": "Autre", "es": "Otro"}
        other_name = OTHER_NAMES.get(language, "Other")
        countries.append(CountryListItem(iso3="Other", iso2="XX", name=other_name, flag_emoji="🏳️"))

    return CountryListResponse(items=countries, language=language)


@router.get("/currencies", response_model=CurrencyListResponse)
async def list_currencies(language: str = Query("en", description="Language for currency names (default: en)")):
    """
    Get list of all currencies with ISO codes, names, and symbols.

    Returns all ISO 4217 currencies with:
    - ISO 4217 code (e.g., USD, EUR)
    - Currency name in requested language (via Babel)
    - Currency symbol (e.g., $, €)

    **Supported Languages**:
    - en (English) - default
    - it (Italian)
    - fr (French)
    - es (Spanish)
    - Other languages supported by Babel
    - Falls back to English if language not supported

    **Example Request**:
    ```
    GET /api/v1/utilities/currencies
    GET /api/v1/utilities/currencies?language=it
    ```

    **Response**:
    ```json
    {
      "currencies": [
        {"code": "USD", "name": "Dollaro statunitense", "symbol": "$"},
        {"code": "EUR", "name": "Euro", "symbol": "€"},
        ...
      ],
      "count": 182,
      "language": "it"
    }
    ```
    """
    currencies_data = list_currencies_util(language)
    currencies = [CurrencyListItem(**c) for c in currencies_data]

    return CurrencyListResponse(items=currencies, language=language)


@router.get("/currencies/normalize", response_model=CurrencyNormalizationResponse)
async def normalize_currency_endpoint(
    name: str = Query(..., min_length=1, description="Currency code, symbol, or name to normalize"),
    language: str = Query("en", description="Language for name matching (default: en)"),
):
    """
    Normalize currency name/code/symbol to ISO 4217 format.

    Accepts:
    - ISO 4217 codes (e.g., USD, EUR)
    - Currency symbols (e.g., $, €, £)
    - Currency names in requested language (e.g., "Dollar", "Euro")

    **Example Requests**:
    ```
    GET /api/v1/utilities/currencies/normalize?name=USD
    GET /api/v1/utilities/currencies/normalize?name=$
    GET /api/v1/utilities/currencies/normalize?name=Dollar&language=en
    ```

    **Response for exact match**:
    ```json
    {
      "query": "EUR",
      "iso_codes": ["EUR"],
      "match_type": "exact",
      "error": null
    }
    ```

    **Response for ambiguous symbol**:
    ```json
    {
      "query": "$",
      "iso_codes": ["USD", "CAD", "AUD", "NZD", "HKD", "SGD", "MXN"],
      "match_type": "symbol_ambiguous",
      "error": "Symbol '$' matches multiple currencies"
    }
    ```
    """
    result = normalize_currency(name, language)

    return CurrencyNormalizationResponse(
        query=result["query"],
        iso_codes=result["iso_codes"],
        match_type=result["match_type"],
        error=result.get("error"),
    )


#: The longest value the suggestion reads (E-19b1): every ISO 4217 name (at most 65 characters) fits, with room.
SUGGEST_MAX_LENGTH = 200


@router.get("/currencies/suggest", response_model=CurrencySuggestionResponse)
def suggest_currency(value: str = Query(..., min_length=1, max_length=SUGGEST_MAX_LENGTH, description="A stored currency value: a code, a numeric code or a currency name")):
    """The ISO 4217 code a stored currency value stands for (E-19b1).

    Since E-18 a write takes only an ISO 4217 alphabetic code, while an earlier version saved what it accepted as written:
    a numeric code or a name (``978``, ``EURO``). The currency picker asks here for such a value it cannot list, and
    shows the code it stands for. ``canonical``: already stored as a code. ``suggestion``: the one code it stands for, or
    null when it stands for none or for two (``Bolívar Soberano``: VED and VES); a subunit code (``GBX``, ``ZAC``,
    ``ILA``) never gets one. ``candidates``: every code it may stand for, sorted. The rule is ``schemas/common.py``'s.
    """
    return CurrencySuggestionResponse(canonical=is_canonical_iso_currency(value), suggestion=suggested_iso_currency(value), candidates=list(iso_currency_candidates(value)))
