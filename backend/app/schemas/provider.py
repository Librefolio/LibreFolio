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
from __future__ import annotations
from typing import List, Optional, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


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
    provider_params: Optional[dict[str, Any]] = Field(None, description="Provider-specific configuration (JSON)")
    fetch_interval: int = Field(1440, description="Refresh frequency in minutes (default: 1440 = 24h)")

    @field_validator('fetch_interval', mode='before')
    @classmethod
    def set_default_fetch_interval(cls, v):
        """Set default fetch_interval if None or empty."""
        if v is None or v == "":
            return 1440
        return v

    @model_validator(mode='after')
    def validate_provider_params_with_plugin(self):
        """Validate provider_params using the plugin's validate_params method."""
        from backend.app.services.provider_registry import AssetProviderRegistry
        from backend.app.services.asset_source import AssetSourceError

        # Get provider instance
        provider = AssetProviderRegistry.get_provider_instance(self.provider_code)
        if not provider:
            raise ValueError(f"Unknown provider code: {self.provider_code}")

        # Validate params using plugin's validate_params method
        try:
            provider.validate_params(self.provider_params)
        except AssetSourceError as e:
            raise ValueError(f"Invalid provider_params for {self.provider_code}: {e.message}")
        except Exception as e:
            raise ValueError(f"Provider validation error for {self.provider_code}: {str(e)}")

        return self


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
    metadata_updated: Optional[bool] = None
    metadata_changes: Optional[List[dict]] = None


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
