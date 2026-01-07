"""
Utility endpoints for frontend support.

Provides helper endpoints for:
- Country/region normalization with multi-language support
- Currency normalization and listing
- Sector classification listing
- Other frontend utilities
"""
from fastapi import APIRouter, Query

from backend.app.schemas.utilities import (
    CountryNormalizationResponse,
    CountryListResponse,
    CountryListItem,
    CurrencyListResponse,
    CurrencyListItem,
    CurrencyNormalizationResponse,
    SectorListResponse
    )
from backend.app.utils.currency_utils import (
    normalize_currency,
    list_currencies as list_currencies_util
    )
from backend.app.utils.geo_utils import (
    normalize_country_to_iso3,
    is_region,
    expand_region,
    list_countries as list_countries_util
    )
from backend.app.utils.sector_fin_utils import FinancialSector

router = APIRouter(prefix="/utilities", tags=["Utilities"])


@router.get("/countries/normalize", response_model=CountryNormalizationResponse)
async def normalize_country(
    name: str = Query(..., min_length=1, description="Country name or code to normalize")
    ):
    """
    Normalize country name/code to ISO-3166-A3 format.

    Accepts:
    - ISO-3166-A3 codes (e.g., USA, GBR)
    - ISO-3166-A2 codes (e.g., US, GB)
    - Country names (e.g., "United States", "Italy")
    - Regions (e.g., "EUR", "ASIA") - returns list of countries

    **Example Requests**:
    ```
    GET /api/v1/utilities/countries/normalize?name=USA
    GET /api/v1/utilities/countries/normalize?name=Italy
    GET /api/v1/utilities/countries/normalize?name=EUR
    ```

    **Response**:
    ```json
    {
      "query": "Italy",
      "iso3_codes": ["ITA"],
      "match_type": "exact"
    }
    ```

    For regions like EUR, ASIA, G7, returns multiple countries:
    ```json
    {
      "query": "G7",
      "iso3_codes": ["USA", "CAN", "GBR", "DEU", "FRA", "ITA", "JPN"],
      "match_type": "region"
    }
    ```
    """
    name_upper = name.strip().upper()

    # Check if it's a region first
    if is_region(name_upper):
        countries = expand_region(name_upper)
        return CountryNormalizationResponse(
            query=name,
            iso3_codes=countries,
            match_type="region",
            error=None
            )

    # Try to normalize as single country
    try:
        iso3_code = normalize_country_to_iso3(name)
        return CountryNormalizationResponse(
            query=name,
            iso3_codes=[iso3_code],
            match_type="exact",
            error=None
            )
    except ValueError as e:
        return CountryNormalizationResponse(
            query=name,
            iso3_codes=[],
            match_type="not_found",
            error=str(e)
            )


@router.get("/sectors", response_model=SectorListResponse)
async def list_sectors(
    include_other: bool = Query(True, description="Include 'Other' in the list")
    ):
    """
    Get list of all standard financial sectors.

    Returns the list of sectors that the system recognizes and stores.
    Based on GICS (Global Industry Classification Standard).

    **Example Request**:
    ```
    GET /api/v1/utilities/sectors
    GET /api/v1/utilities/sectors?include_other=false
    ```

    **Response**:
    ```json
    {
      "sectors": [
        "Industrials",
        "Technology",
        "Financials",
        "Consumer Discretionary",
        "Health Care",
        "Real Estate",
        "Basic Materials",
        "Energy",
        "Consumer Staples",
        "Telecommunication",
        "Utilities",
        "Other"
      ],
      "count": 12
    }
    ```
    """
    if include_other:
        sectors = FinancialSector.list_all_with_other()
    else:
        sectors = FinancialSector.list_all()

    return SectorListResponse(
        sectors=sectors,
        count=len(sectors)
        )


@router.get("/countries", response_model=CountryListResponse)
async def list_countries(
    language: str = Query("en", description="Language for country names (default: en)")
    ):
    """
    Get list of all countries with ISO codes and flag emoji.

    Returns all ISO-3166 countries with:
    - ISO-3166-A3 code (e.g., USA)
    - ISO-3166-A2 code (e.g., US)
    - Country name in requested language (via Babel)
    - Flag emoji (e.g., 🇺🇸)

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

    return CountryListResponse(
        countries=countries,
        count=len(countries),
        language=language
        )


@router.get("/currencies", response_model=CurrencyListResponse)
async def list_currencies(
    language: str = Query("en", description="Language for currency names (default: en)")
    ):
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

    return CurrencyListResponse(
        currencies=currencies,
        count=len(currencies),
        language=language
        )


@router.get("/currencies/normalize", response_model=CurrencyNormalizationResponse)
async def normalize_currency_endpoint(
    name: str = Query(..., min_length=1, description="Currency code, symbol, or name to normalize"),
    language: str = Query("en", description="Language for name matching (default: en)")
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
        error=result.get("error")
        )
