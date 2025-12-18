"""
Pydantic schemas for utility endpoints.
"""
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


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


class CountryListResponse(BaseModel):
    """Response for countries list endpoint."""
    model_config = ConfigDict(extra="forbid")

    countries: List[CountryListItem] = Field(..., description="List of all countries")
    count: int = Field(..., description="Number of countries")
    language: str = Field(..., description="Language used for country names")


class SectorListResponse(BaseModel):
    """Response for sectors list endpoint."""
    model_config = ConfigDict(extra="forbid")

    sectors: List[str] = Field(..., description="List of standard financial sector names")
    count: int = Field(..., description="Number of sectors in the list")
