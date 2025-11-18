"""
Provider Assignment Schemas (FA + FX).

This module contains Pydantic models for provider assignment operations across
both Financial Assets (FA) and Foreign Exchange (FX) systems.

**Naming Conventions**:
- FA prefix: Financial Assets (asset pricing providers like yfinance, cssscraper)
- FX prefix: Foreign Exchange (FX rate providers like ECB, FED, BOE, SNB)

**Domain Coverage**:
- Provider discovery and metadata (ProviderInfo classes)
- Provider assignment to assets/pairs (Assignment classes)
- Bulk assignment operations (BulkAssign/Remove classes)

**Design Notes**:
- No backward compatibility maintained during refactoring
- All models use Pydantic v2 with strict validation
- Field descriptions included for OpenAPI documentation

**Structure**:
- Provider Info: Discovery and metadata retrieval
- Assignment Operations: Assign/remove providers to/from assets
- Bulk Operations: Batch processing for efficiency
"""
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# FA PROVIDER INFO
# ============================================================================

class FAProviderInfo(BaseModel):
    """Information about a single Financial Asset pricing provider.

    Used for provider discovery and capability inspection.
    """
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Provider code (e.g., yfinance, cssscraper)")
    name: str = Field(..., description="Provider full name")
    description: str = Field(..., description="Provider description")
    supports_search: bool = Field(..., description="Whether provider supports asset search")


class FAProvidersResponse(BaseModel):
    """Response containing list of available FA providers."""
    model_config = ConfigDict(extra="forbid")

    providers: List[FAProviderInfo]


# ============================================================================
# FX PROVIDER INFO
# ============================================================================

class FXProviderInfo(BaseModel):
    """Information about a single FX rate provider.

    Used for FX provider discovery and capability inspection.
    """
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Provider code (e.g., ECB, FED, BOE, SNB)")
    name: str = Field(..., description="Provider full name")
    base_currencies: List[str] = Field(..., description="Supported base currencies")
    description: Optional[str] = Field(None, description="Provider description")


class FXProvidersResponse(BaseModel):
    """Response containing list of available FX providers."""
    model_config = ConfigDict(extra="forbid")

    providers: List[FXProviderInfo]


# ============================================================================
# FA PROVIDER ASSIGNMENT
# ============================================================================

class FAProviderAssignmentItem(BaseModel):
    """Single FA provider assignment configuration.

    Links an asset to a pricing provider with optional parameters.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    provider_code: str = Field(..., description="Provider code (yfinance, cssscraper, etc.)")
    provider_params: dict = Field(..., description="Provider-specific configuration (JSON)")
    fetch_interval: Optional[int] = Field(None, description="Refresh frequency in minutes (NULL = default 1440 = 24h)")


class FABulkAssignRequest(BaseModel):
    """Request for bulk FA provider assignment."""
    model_config = ConfigDict(extra="forbid")

    assignments: List[FAProviderAssignmentItem] = Field(..., min_length=1, description="List of provider assignments")


class FAProviderAssignmentResult(BaseModel):
    """Result of single FA provider assignment."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    success: bool
    message: str


class FABulkAssignResponse(BaseModel):
    """Response for bulk FA provider assignment."""
    model_config = ConfigDict(extra="forbid")

    results: List[FAProviderAssignmentResult]
    success_count: int


# ============================================================================
# FA PROVIDER REMOVAL
# ============================================================================

class FABulkRemoveRequest(BaseModel):
    """Request for bulk FA provider removal."""
    model_config = ConfigDict(extra="forbid")

    asset_ids: List[int] = Field(..., min_length=1, description="List of asset IDs to remove providers from")


class FAProviderRemovalResult(BaseModel):
    """Result of single FA provider removal."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    success: bool
    message: str


class FABulkRemoveResponse(BaseModel):
    """Response for bulk FA provider removal."""
    model_config = ConfigDict(extra="forbid")

    results: List[FAProviderRemovalResult]
    success_count: int
