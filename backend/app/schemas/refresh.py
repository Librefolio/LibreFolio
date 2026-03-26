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

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.app.schemas.common import Currency, DateRangeModel, BaseBulkResponse


# ============================================================================
# SHARED SYNC STATUS ENUM
# ============================================================================


class SyncStatus(str, Enum):
    """Status of a single sync operation (shared by FA and FX)."""
    OK = "ok"             # Provider returned data, inserted/updated in DB
    PARTIAL = "partial"   # Provider has data but incomplete (e.g. SNB monthly, gaps)
    FAILED = "failed"     # All providers for this pair/asset failed
    SKIPPED = "skipped"   # Pair is MANUAL-only or asset has no provider


# Backward-compatible alias (will be removed in future)
FXSyncStatus = SyncStatus


# ============================================================================
# FA REFRESH SECTION
# ============================================================================


class FARefreshItem(BaseModel):
    """Single asset refresh request.

    Specifies asset and date range for price data refresh from provider.
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    date_range: DateRangeModel = Field(..., description="Date range for refresh")


class FARefreshResult(BaseModel):
    """Result of refresh for single asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    status: SyncStatus = Field(SyncStatus.FAILED, description="Sync status for this asset")
    provider_used: Optional[str] = Field(None, description="Provider code that served data")
    points_fetched: int = Field(0, description="Number of prices fetched from provider")
    points_changed: int = Field(0, description="Number of prices actually inserted/updated in DB")
    inserted_count: int = Field(0, description="Number of prices inserted into DB")
    updated_count: int = Field(0, description="Number of prices updated in DB")
    message: Optional[str] = Field(None, description="Optional note/summary (non-error)")
    errors: List[str] = Field(default_factory=list)
    elapsed_ms: Optional[int] = Field(None, ge=0, description="Backend sync time for this asset in ms")


class FABulkRefreshResponse(BaseBulkResponse[FARefreshResult]):
    """Response for bulk asset price refresh."""

    date_range: Optional[DateRangeModel] = Field(None, description="Requested date range")
    total_points_changed: int = Field(0, ge=0, description="Sum of points_changed across all assets")


# ============================================================================
# FX SYNC SECTION — Pair-Based Bulk Sync
# ============================================================================


class FXSyncPairRequest(BaseModel):
    """Request body for pair-based FX sync.

    Accepts a list of pair slugs (e.g. ['EUR-USD', 'CHF-CNY']) and a date range.
    Pairs are normalized to alphabetical order internally.
    """

    model_config = ConfigDict(extra="forbid")

    pairs: List[str] = Field(..., min_length=1, description="Pair slugs, e.g. ['EUR-USD', 'CHF-CNY']")
    start: date = Field(..., description="Start date (inclusive)")
    end: date = Field(..., description="End date (inclusive)")

    @field_validator('pairs', mode='before')
    @classmethod
    def validate_pairs(cls, v):
        """Validate each pair: split by '-', validate both currencies, normalize to alphabetical order."""
        validated = []
        for pair in v:
            parts = pair.split('-')
            if len(parts) != 2:
                raise ValueError(f"Invalid pair format: '{pair}'. Expected 'BASE-QUOTE'.")
            base = Currency.validate_code(parts[0])
            quote = Currency.validate_code(parts[1])
            if base == quote:
                raise ValueError(f"Invalid pair: '{pair}'. Base and quote must be different.")
            # Normalize: alphabetical order
            if base > quote:
                base, quote = quote, base
            validated.append(f"{base}-{quote}")
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for p in validated:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        return deduped


class FXSyncLegDetail(BaseModel):
    """Diagnostic detail for a single leg in a chain (or single-provider route)."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(..., description="Provider code for this leg, e.g. 'ECB'")
    leg: str = Field(..., description="Leg pair in the chain, e.g. 'EUR→GBP'")
    dates_available: int = Field(0, ge=0, description="Number of dates with data from this provider in the requested range")
    error: Optional[str] = Field(None, description="Error message if the leg failed (e.g. timeout, provider error)")


class FXSyncPairResult(BaseModel):
    """Result of sync operation for a single pair."""

    model_config = ConfigDict(extra="forbid")

    pair: str = Field(..., description="Normalized pair slug, e.g. 'EUR-USD'")
    status: SyncStatus = Field(..., description="Sync status for this pair")
    provider_used: Optional[str] = Field(None, description="Provider code that served data (None if failed/skipped)")
    points_fetched: int = Field(0, ge=0, description="Number of rate points fetched from provider")
    points_changed: int = Field(0, ge=0, description="Number of rate points actually inserted/updated in DB")
    message: Optional[str] = Field(None, description="Optional note (e.g. 'monthly data only', 'fallback used')")
    errors: List[str] = Field(default_factory=list, description="List of error messages for this pair")
    detail: Optional[List[FXSyncLegDetail]] = Field(
        None,
        description="Per-leg diagnostic breakdown. Present for chains and single-provider routes "
                    "when status is partial or failed. Each entry shows provider name, "
                    "leg pair, dates available, and any error encountered."
    )
    elapsed_ms: Optional[int] = Field(
        None, ge=0,
        description="Backend sync time for this pair in integer milliseconds. "
                    "Measured from bulk start (Phase 1) to commit completion, "
                    "via time.monotonic_ns() with integer division (// 1_000_000). "
                    "None for SKIPPED/MANUAL pairs."
    )

    @field_validator('pair')
    @classmethod
    def validate_pair(cls, v):
        """Validate pair currencies via Currency.validate_code."""
        parts = v.split('-')
        if len(parts) != 2:
            raise ValueError(f"Invalid pair format: '{v}'")
        Currency.validate_code(parts[0])
        Currency.validate_code(parts[1])
        return v


class FXSyncBulkResponse(BaseBulkResponse[FXSyncPairResult]):
    """Response for bulk pair-based FX sync.

    Inherits from BaseBulkResponse:
    - results: List[FXSyncPairResult]
    - success_count: int (pairs with status ok or partial)
    - errors: List[str] (operation-level errors)
    - failed_count: computed property

    Additional fields:
    - date_range: requested date range
    - total_points_changed: aggregate across all pairs
    """

    date_range: DateRangeModel = Field(..., description="Requested date range")
    total_points_changed: int = Field(0, ge=0, description="Sum of points_changed across all pairs")

