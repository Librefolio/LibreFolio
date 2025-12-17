"""
Utility endpoints for frontend support.

Provides helper endpoints for:
- Country/region normalization
- Sector classification listing
- Other frontend utilities
"""
from typing import List
from fastapi import APIRouter, Query

from backend.app.schemas.utilities import (
    CountryNormalizationResponse,
    CountryListResponse,
    CountryListItem,
    SectorListResponse
)
from backend.app.utils.sector_normalization import FinancialSector
from backend.app.utils.geo_normalization import normalize_country_to_iso3

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

    TODO: Implement region expansion (EUR → [DEU, FRA, ITA, ESP, ...])
    """
    try:
        iso3_code = normalize_country_to_iso3(name)
        return CountryNormalizationResponse(
            query=name,
            iso3_codes=[iso3_code],
            match_type="exact"
        )
    except ValueError as e:
        # Could be a region - for now return error
        # TODO: Implement region mapping
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
    Get list of all countries with ISO codes.

    Returns all ISO-3166 countries with:
    - ISO-3166-A3 code (e.g., USA)
    - ISO-3166-A2 code (e.g., US)
    - Country name in requested language

    **Supported Languages**:
    - en (English) - default
    - Other languages depend on pycountry translations

    **Example Request**:
    ```
    GET /api/v1/utilities/countries
    GET /api/v1/utilities/countries?language=en
    ```

    **Response**:
    ```json
    {
      "countries": [
        {"iso3": "AFG", "iso2": "AF", "name": "Afghanistan"},
        {"iso3": "ALB", "iso2": "AL", "name": "Albania"},
        ...
      ],
      "count": 249,
      "language": "en"
    }
    ```
    """
    import pycountry

    countries = []
    for country in pycountry.countries:
        countries.append(CountryListItem(
            iso3=country.alpha_3,
            iso2=country.alpha_2,
            name=country.name
        ))

    # Sort by name
    countries.sort(key=lambda c: c.name)

    return CountryListResponse(
        countries=countries,
        count=len(countries),
        language=language
    )


