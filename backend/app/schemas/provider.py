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

from backend.app.db.models import IdentifierType
from backend.app.schemas.common import BaseDeleteResult, BaseBulkResponse, OldNew


# Note: AssetProviderRegistry is imported inside validators to avoid circular imports

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
    icon_url: Optional[str] = Field(None, description="Provider icon URL (hardcoded)")
    supports_search: bool = Field(..., description="Whether provider supports asset search")


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


# ============================================================================
# FA PROVIDER ASSIGNMENT
# ============================================================================

class FAProviderAssignmentItem(BaseModel):
    """Single FA provider assignment configuration.

    Links an asset to a pricing provider with identifier and parameters.

    Fields:
    - identifier: How the provider identifies this asset (ticker, ISIN, UUID, URL, etc.)
    - identifier_type: Type of identifier (TICKER, ISIN, UUID, OTHER, etc.)
    - provider_params: Provider-specific configuration (e.g., FAScheduledInvestmentSchedule for scheduled_investment)
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    provider_code: str = Field(..., description="Provider code (yfinance, cssscraper, scheduled_investment, etc.)")
    identifier: str = Field(..., description="Asset identifier for this provider (ticker, ISIN, UUID, URL, etc.)")
    identifier_type: IdentifierType = Field(..., description="Type of identifier (TICKER, ISIN, UUID, OTHER, etc.)")
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
        # Lazy import to avoid circular dependency
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


class FAProviderAssignmentReadItem(BaseModel):
    """Provider assignment read response (includes all fields).

    Used for GET /assets/provider/assignments endpoint.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    provider_code: str = Field(..., description="Provider code")
    identifier: str = Field(..., description="Asset identifier for provider")
    identifier_type: IdentifierType = Field(..., description="Type of identifier")
    provider_params: Optional[dict[str, Any]] = Field(None, description="Provider configuration")
    fetch_interval: Optional[int] = Field(None, description="Refresh frequency in minutes")
    last_fetch_at: Optional[str] = Field(None, description="Last fetch timestamp (ISO format)")


class FAProviderRefreshFieldsDetail(BaseModel):
    """Field-level details for provider refresh operation.

    Provides granular information about which fields were updated during refresh,
    including old and new values for each changed field.

    Examples:
        >>> detail = FAProviderRefreshFieldsDetail(
        ...     refreshed_fields=[
        ...         OldNew(info="sector", old="Technology", new="Industrials"),
        ...         OldNew(old=None, new="Test Corp")  # First time set
        ...     ],
        ...     missing_data_fields=["currency"],
        ...     ignored_fields=[]
        ... )
    """
    model_config = ConfigDict(extra="forbid")

    refreshed_fields: List[OldNew[str | None]] = Field(..., description="Fields updated with old→new values. Old is None if first time set, new is None if field cleared.")
    missing_data_fields: List[str] = Field(..., description="Fields provider couldn't fetch (no data available)")
    ignored_fields: List[str] = Field(..., description="Fields ignored (not requested when using field selection)")


class FAProviderAssignmentResult(BaseModel):
    """Result of single FA provider assignment or refresh."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    success: bool
    message: str
    fields_detail: Optional[FAProviderRefreshFieldsDetail] = Field(None, description="Field-level refresh details (for refresh operations)")


class FABulkAssignResponse(BaseBulkResponse[FAProviderAssignmentResult]):
    """Response for bulk FA provider assignment."""
    pass


# ============================================================================
# FA PROVIDER REMOVAL
# ============================================================================


class FAProviderRemovalResult(BaseDeleteResult):
    """Result of single FA provider removal."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    # Inherits from BaseDeleteResult:
    # - success: bool
    # - deleted_count: int (always 0 or 1 for single provider removal)
    # - message: Optional[str]


class FABulkRemoveResponse(BaseBulkResponse[FAProviderRemovalResult]):
    """Response for bulk FA provider removal."""
    pass


# ============================================================================
# FA PROVIDER SEARCH
# ============================================================================


class FAProviderSearchResultItem(BaseModel):
    """Single search result from a provider.

    Contains the asset identifier and metadata from the provider's search.
    The identifier_type field is required so the result can be used directly
    for asset creation without needing to look up the identifier type.
    """
    model_config = ConfigDict(extra="forbid")

    identifier: str = Field(..., description="Asset identifier (ISIN, ticker, URL, etc.)")
    identifier_type: IdentifierType = Field(..., description="Type of identifier (ISIN, TICKER, URL, etc.)")
    display_name: str = Field(..., description="Human-readable asset name")
    provider_code: str = Field(..., description="Provider that returned this result")
    currency: Optional[str] = Field(None, description="Asset currency if known")
    asset_type: Optional[str] = Field(None, description="Asset type (ETF, stock, bond, etc.)")


class FAProviderSearchResponse(BaseModel):
    """Response for provider search endpoint.

    Returns aggregated search results from one or more providers.
    """
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., description="Original search query")
    total_results: int = Field(..., description="Total number of results across all providers")
    results: List[FAProviderSearchResultItem] = Field(..., description="Search results")
    providers_queried: List[str] = Field(..., description="Provider codes that were queried")
    providers_with_errors: List[str] = Field(default_factory=list, description="Providers that returned errors")
