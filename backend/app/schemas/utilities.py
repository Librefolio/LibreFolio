"""
Pydantic schemas for utility endpoints.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import BaseListResponse


class CountryNormalizationResponse(BaseModel):
    """Response for country normalization endpoint."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Original query string")
    iso3_codes: List[str] = Field(..., description="List of ISO-3166-A3 country codes")
    match_type: str = Field(..., description="Match type: exact, region, multi-match, not_found")
    error: Optional[str] = Field(None, description="Error message if normalization failed")


class CountryListItem(BaseModel):
    """Single country in the country list."""

    model_config = ConfigDict(extra="forbid")

    iso3: str = Field(..., description="ISO-3166-A3 country code (e.g., USA, ITA)")
    iso2: str = Field(..., description="ISO-3166-A2 country code (e.g., US, IT)")
    name: str = Field(..., description="Country name in requested language")
    flag_emoji: str = Field(..., description="Flag emoji (e.g., 🇺🇸, 🇮🇹)")


class CountryListResponse(BaseListResponse[CountryListItem]):
    """Response for countries list endpoint."""

    language: str = Field(..., description="Language used for country names")


class CurrencyListItem(BaseModel):
    """Single currency in the currency list."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="ISO 4217 currency code (e.g., USD, EUR)")
    name: str = Field(..., description="Currency name in requested language")
    symbol: str = Field(..., description="Currency symbol (e.g., $, €)")
    flag_emoji: str = Field("🏳️", description="Flag emoji of primary country using this currency (e.g., 🇺🇸, 🇪🇺, 🪙 for crypto)")
    country_codes: list[str] = Field(default_factory=list, description="ISO-2 country codes using this currency (e.g., ['US', 'AS', 'EC'] for USD)")
    country_names: list[str] = Field(default_factory=list, description="Localized country names using this currency (e.g., ['United States', 'American Samoa'] for USD in English)")


class CurrencyListResponse(BaseListResponse[CurrencyListItem]):
    """Response for currencies list endpoint."""

    language: str = Field(..., description="Language used for currency names")


class CurrencyNormalizationResponse(BaseModel):
    """Response for currency normalization endpoint."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Original query string")
    iso_codes: List[str] = Field(..., description="List of ISO 4217 currency codes")
    match_type: str = Field(..., description="Match type: exact, symbol_ambiguous, multi-match, not_found")
    error: Optional[str] = Field(None, description="Error message if normalization failed")


class SectorListResponse(BaseListResponse[str]):
    """Response for sectors list endpoint."""

    pass
