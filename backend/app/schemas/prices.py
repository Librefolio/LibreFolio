"""
Price Operation Schemas (FA - Financial Assets).

This module contains Pydantic models for price data operations on Financial Assets.
Covers upsert, delete, and query operations for asset price history.

**Naming Conventions**:
- FA prefix: Financial Assets (stocks, ETFs, bonds, loans, etc.)
- All models use 3-level nesting: Item → Asset → Bulk

**Domain Coverage**:
- Price upsert: Insert or update price points (OHLC + volume)
- Price delete: Remove price data by date ranges
- Price query: Retrieve historical prices with backward-fill

**Design Notes**:
- No backward compatibility maintained during refactoring
- All models use Pydantic v2 with strict validation
- Bulk operations are PRIMARY (single operations call bulk internally)
- Uses DateRangeModel from common.py for consistency

**Structure Differences vs FX**:
- FA: 3 levels (Item → Asset → Bulk) - multiple items per asset, multiple assets per request
- FX: 2 levels (Item → Bulk) - direct item-to-bulk without intermediate grouping
"""
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.utils.validation_utils import normalize_currency_code


# ============================================================================
# FA PRICE UPSERT
# ============================================================================

class FAUpsertItem(BaseModel):
    """Single price point for upsert (OHLC + volume).

    Represents one day's price data for an asset.
    """
    model_config = ConfigDict(extra="forbid")

    date: date_type = Field(..., description="Price date")
    open: Optional[Decimal] = Field(None, description="Opening price")
    high: Optional[Decimal] = Field(None, description="High price")
    low: Optional[Decimal] = Field(None, description="Low price")
    close: Decimal = Field(..., description="Closing price (required)")
    volume: Optional[Decimal] = Field(None, description="Trading volume")
    currency: str = Field(..., description="Currency code (ISO 4217)")

    @field_validator("currency")
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return normalize_currency_code(v)

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


class FAUpsert(BaseModel):
    """Price upsert for a single asset (multiple dates).

    Groups multiple price points for one asset.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    prices: List[FAUpsertItem] = Field(..., min_length=1, description="List of price points")


class FABulkUpsertRequest(BaseModel):
    """Request for bulk price upsert across multiple assets."""
    model_config = ConfigDict(extra="forbid")

    assets: List[FAUpsert] = Field(..., min_length=1, description="List of asset price upserts")


class FAUpsertResult(BaseModel):
    """Result of price upsert for single asset."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    count: int
    message: str


class FABulkUpsertResponse(BaseModel):
    """Response for bulk price upsert."""
    model_config = ConfigDict(extra="forbid")

    results: List[FAUpsertResult]
    inserted_count: int
    updated_count: int


# ============================================================================
# FA PRICE DELETE
# ============================================================================

class FAAssetDelete(BaseModel):
    """Price deletion request for a single asset (multiple ranges).

    Groups multiple date ranges for one asset.
    Uses DateRangeModel for consistency.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    date_ranges: List[DateRangeModel] = Field(..., min_length=1, description="List of date ranges to delete")


class FAPriceBulkDeleteRequest(BaseModel):
    """Request for bulk price deletion across multiple assets."""
    model_config = ConfigDict(extra="forbid")

    assets: List[FAAssetDelete] = Field(..., min_length=1, description="List of asset price deletions")


class FAPriceDeleteResult(BaseModel):
    """Result of price deletion for single asset."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    deleted: int
    message: str


class FABulkDeleteResponse(BaseModel):
    """Response for bulk price deletion."""
    model_config = ConfigDict(extra="forbid")

    results: List[FAPriceDeleteResult]
    deleted_count: int


# ============================================================================
# FA PRICE QUERY
# ============================================================================

class FACurrentValue(BaseModel):
    """Current value of an asset."""
    model_config = ConfigDict(extra="forbid")

    value: Decimal
    currency: str
    as_of_date: date_type
    source: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        return Decimal(str(v))


class FAPricePoint(BaseModel):
    """Single price point with OHLC data and optional backward-fill info."""
    model_config = ConfigDict(extra="forbid")

    date: date_type
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    volume: Optional[Decimal] = None
    currency: Optional[str] = None
    backward_fill_info: Optional[BackwardFillInfo] = None

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def parse_optional_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


class FAHistoricalData(BaseModel):
    """Historical price data for an asset (list of price points)."""
    model_config = ConfigDict(extra="forbid")

    prices: List[FAPricePoint]
    currency: Optional[str] = None
    source: Optional[str] = None
