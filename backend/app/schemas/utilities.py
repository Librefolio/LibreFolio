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


class SectorListResponse(BaseModel):
    """Response for sectors list endpoint."""
    model_config = ConfigDict(extra="forbid")

    sectors: List[str] = Field(..., description="List of standard financial sector names")
    count: int = Field(..., description="Number of sectors in the list")

