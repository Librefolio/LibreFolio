"""
Refresh & Sync Operation Schemas (FA + FX).

This module consolidates refresh/sync operations for both Financial Assets (FA)
and Foreign Exchange (FX) systems. These are operational workflows that fetch
and update price/rate data from external providers.

**Naming Conventions**:
- FA prefix: Financial Assets refresh operations
- FX prefix: Foreign Exchange sync operations

**Domain Coverage**:
- FA Refresh: Fetch and store asset prices from providers (yfinance, etc.)
- FX Sync: Fetch and store FX rates from central banks (ECB, FED, etc.)

**Design Notes**:
- Consolidation rationale: Both operations perform similar "fetch-and-store" workflows
- Kept separate sections (FA Refresh / FX Sync) for semantic clarity
- No backward compatibility maintained during refactoring
- All models use Pydantic v2 with strict validation

**Structure Differences**:
- FA Refresh: 3-level (Item → Bulk → Result per asset)
- FX Sync: 2-level (Request with params → Response with summary)
  - FX sync operates on date ranges + currency lists (no per-pair config)
  - FA refresh operates on asset-by-asset basis with provider-specific params
"""
from datetime import date as date_type
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.app.utils.datetime_utils import parse_ISO_date


# ============================================================================
# FA REFRESH SECTION
# ============================================================================

class FARefreshItem(BaseModel):
    """Single asset refresh request.

    Specifies asset and date range for price data refresh from provider.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    start_date: date_type = Field(..., description="Start date for refresh")
    end_date: date_type = Field(..., description="End date for refresh")


class FABulkRefreshRequest(BaseModel):
    """Request for bulk asset price refresh."""
    model_config = ConfigDict(extra="forbid")

    requests: List[FARefreshItem] = Field(..., min_length=1, description="List of refresh requests")
    timeout: Optional[int] = Field(60, description="Timeout in seconds per provider call")


class FARefreshResult(BaseModel):
    """Result of refresh for single asset."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    fetched_count: int = Field(..., description="Number of prices fetched from provider")
    inserted_count: int = Field(..., description="Number of prices inserted into DB")
    updated_count: int = Field(..., description="Number of prices updated in DB")
    errors: List[str] = Field(default_factory=list)


class FABulkRefreshResponse(BaseModel):
    """Response for bulk asset price refresh."""
    model_config = ConfigDict(extra="forbid")

    results: List[FARefreshResult]


# ============================================================================
# FX SYNC SECTION
# ============================================================================

class FXSyncResponse(BaseModel):
    """Response for FX rate synchronization from central banks.
    
    Provides summary of synced FX rates operation.
    Different structure from FA: summarizes overall sync with date range
    rather than per-asset results.
    
    Migrated from fx.py (was SyncResponseModel) to consolidate refresh/sync
    operations in single module for operational coherence.
    """
    model_config = ConfigDict(extra="forbid")

    synced: int = Field(..., description="Number of new rates inserted/updated")
    date_range: tuple[date_type, date_type] = Field(..., description="Date range synced (ISO format)")
    currencies: List[str] = Field(..., description="Currencies synced")

    @field_validator("date_range", mode="before")
    @classmethod
    def _parse_date_range(cls, v):
        return parse_ISO_date(v[0]), parse_ISO_date(v[1])


    def date_range_str(self)-> str:
        return self.date_range[0].isoformat() + " to " + self.date_range[1].isoformat()
