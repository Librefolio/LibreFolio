"""
Pydantic schemas for utility endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.common import BaseListResponse, StrictModel


class CountryListItem(StrictModel):
    """Single country in the country list."""

    iso3: str = Field(..., description="ISO-3166-A3 country code (e.g., USA, ITA)")
    iso2: str = Field(..., description="ISO-3166-A2 country code (e.g., US, IT)")
    name: str = Field(..., description="Country name in requested language")
    flag_emoji: str = Field(..., description="Flag emoji (e.g., 🇺🇸, 🇮🇹)")


class CountryListResponse(BaseListResponse[CountryListItem]):
    """Response for countries list endpoint."""

    language: str = Field(..., description="Language used for country names")


class CurrencyListItem(StrictModel):
    """Single currency in the currency list."""

    code: str = Field(..., description="ISO 4217 currency code (e.g., USD, EUR)")
    name: str = Field(..., description="Currency name in requested language")
    symbol: str = Field(..., description="Currency symbol (e.g., $, €)")
    flag_emoji: str = Field("🏳️", description="Flag emoji of primary country using this currency (e.g., 🇺🇸, 🇪🇺)")
    country_codes: list[str] = Field(default_factory=list, description="ISO-2 country codes using this currency (e.g., ['US', 'AS', 'EC'] for USD)")
    country_names: list[str] = Field(default_factory=list, description="Localized country names using this currency (e.g., ['United States', 'American Samoa'] for USD in English)")


class CurrencyListResponse(BaseListResponse[CurrencyListItem]):
    """Response for currencies list endpoint."""

    language: str = Field(..., description="Language used for currency names")


class CurrencyNormalizationResponse(StrictModel):
    """Response for currency normalization endpoint."""

    query: str = Field(..., description="Original query string")
    iso_codes: List[str] = Field(..., description="List of ISO 4217 currency codes")
    match_type: str = Field(..., description="Match type: exact, symbol_ambiguous, multi-match, not_found")
    error: Optional[str] = Field(None, description="Error message if normalization failed")


class CurrencySuggestionResponse(StrictModel):
    """What a stored currency value stands for (E-19b1): the currency picker shows it beside a value that is no ISO 4217
    code, such as the ``978`` or ``EURO`` an earlier version saved as written."""

    canonical: bool = Field(..., description="The value is stored as an ISO 4217 alphabetic code: upper case, nothing around it")
    suggestion: Optional[str] = Field(None, description="The one ISO 4217 code the value stands for, or null: none, or more than one")
    candidates: List[str] = Field(default_factory=list, description="The ISO 4217 codes the value may stand for, sorted")


class SectorItem(BaseModel):
    """A sector with its key and emoji icon."""

    key: str = Field(..., description="Sector key (e.g. 'Industrials')")
    emoji: str = Field(..., description="Sector emoji icon")


class SectorListResponse(BaseListResponse[SectorItem]):
    """Response for sectors list endpoint.

    ``items`` are the sectors an asset can be classified in. ``buckets`` are the two allocation buckets the portfolio
    engine adds on its own, the cash (``Liquidity``) and the holdings without a sector (``Unknown``): never a sector to
    choose, listed for their emoji. ``fallback_emoji`` is the glyph of a key outside both lists.
    """

    buckets: List[SectorItem] = Field(..., description="Allocation buckets the engine adds on its own (cash, unclassified), with their emoji; never a sector to choose")
    fallback_emoji: str = Field(..., description="Emoji of a key outside the sectors and the buckets")
