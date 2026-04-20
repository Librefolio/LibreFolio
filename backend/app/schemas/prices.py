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
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.common import (
    BackwardFillInfo,
    BaseBulkDeleteResponse,
    BaseBulkResponse,
    BaseDeleteResult,
    BaseListResponse,
    Currency,
    DateRangeModel,
)

# ============================================================================
# BACKWARD-FILL INFO (EXTENDED FOR FX STALENESS)
# ============================================================================


class AssetBackwardFillInfo(BackwardFillInfo):
    """Extended backward-fill info for asset prices with FX staleness tracking.

    Inherits price staleness from BackwardFillInfo (actual_rate_date, days_back).
    Adds FX-specific staleness fields for currency-converted prices.

    When a price is converted to a target currency:
    - fx_rate_date: the actual date of the FX rate used for conversion
    - fx_days_back: how many days old the FX rate is (0 = same-day rate)

    Both fields are None when no currency conversion was performed.
    """

    fx_rate_date: Optional[date_type] = Field(None, description="Actual date of the FX rate used for conversion")
    fx_days_back: Optional[int] = Field(None, description="Days back for the FX rate (0 = same-day, None = no conversion)")


# ============================================================================
# FA PRICE UPSERT
# ============================================================================


class FAPricePoint(BaseModel):
    """Single price point with OHLC data.

    Used for both:
    - Upsert operations (backward_fill_info is None)
    - Query results (backward_fill_info may be present)

    The API contract uses separate `close: Decimal` and `currency: str` fields
    for JSON compatibility. Use `close_cur` property for internal operations
    that need a Currency object.
    """

    model_config = ConfigDict(extra="forbid")

    date: date_type = Field(..., description="Price date")
    open: Optional[Decimal] = Field(None, description="Opening price")
    high: Optional[Decimal] = Field(None, description="High price")
    low: Optional[Decimal] = Field(None, description="Low price")
    close: Decimal = Field(..., description="Closing price (required)")
    volume: Optional[Decimal] = Field(None, description="Trading volume")
    currency: str = Field(..., description="Currency code (ISO 4217)")
    original_currency: Optional[str] = Field(None, description="Original currency before FX conversion (None = no conversion)")
    original_close: Optional[Decimal] = Field(None, description="Close price in original currency before FX conversion")
    original_open: Optional[Decimal] = Field(None, description="Open price in original currency before FX conversion")
    original_high: Optional[Decimal] = Field(None, description="High price in original currency before FX conversion")
    original_low: Optional[Decimal] = Field(None, description="Low price in original currency before FX conversion")
    backward_fill_info: Optional[AssetBackwardFillInfo] = Field(None, description="Backward-fill + FX staleness info (only in query results)")

    @field_validator("currency")
    @classmethod
    def currency_validate(cls, v: str) -> str:
        return Currency.validate_code(v)

    @field_validator("open", "high", "low", "close", "volume", "original_open", "original_high", "original_low", "original_close", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))

    @property
    def close_cur(self) -> Currency:
        """Get close price as Currency object for internal calculations."""
        return Currency(code=self.currency, amount=self.close)

    @property
    def open_cur(self) -> Optional[Currency]:
        """Get open price as Currency object for internal calculations."""
        return Currency(code=self.currency, amount=self.open) if self.open is not None else None

    @property
    def high_cur(self) -> Optional[Currency]:
        """Get high price as Currency object for internal calculations."""
        return Currency(code=self.currency, amount=self.high) if self.high is not None else None

    @property
    def low_cur(self) -> Optional[Currency]:
        """Get low price as Currency object for internal calculations."""
        return Currency(code=self.currency, amount=self.low) if self.low is not None else None


class FAUpsert(BaseModel):
    """Price upsert for a single asset (multiple dates).

    Groups multiple price points for one asset.
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    prices: List[FAPricePoint] = Field(..., min_length=1, description="List of price points")


class FAUpsertResult(BaseModel):
    """Result of price upsert for single asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    count: int
    message: str


class FABulkUpsertResponse(BaseBulkResponse[FAUpsertResult]):
    """Response for bulk price upsert."""

    # Operation-specific fields
    inserted_count: int = Field(..., description="Number of prices inserted")
    updated_count: int = Field(..., description="Number of prices updated")


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


class FAPriceDeleteResult(BaseDeleteResult):
    """Result of price deletion for single asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    # Inherits from BaseDeleteResult:
    # - success: bool
    # - deleted_count: int (number of price records deleted)
    # - message: Optional[str]


class FABulkDeleteResponse(BaseBulkDeleteResponse[FAPriceDeleteResult]):
    """Response for bulk price deletion."""

    # Inherits from BaseBulkDeleteResponse:
    # - results: List[FAPriceDeleteResult]
    # - success_count: int
    # - errors: List[str]
    # - total_deleted: int (total price records deleted)
    pass


# ============================================================================
# FA PRICE QUERY
# ============================================================================


class FACurrentValue(BaseModel):
    """Current value of an asset.

    The API contract uses separate `value: Decimal` and `currency: str` fields
    for JSON compatibility. Use `value_cur` property for internal operations.
    """

    model_config = ConfigDict(extra="forbid")

    value: Decimal
    currency: str
    as_of_date: date_type
    source: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        return Decimal(str(v))

    @field_validator("currency")
    @classmethod
    def currency_validate(cls, v: str) -> str:
        return Currency.validate_code(v)

    @property
    def value_cur(self) -> Currency:
        """Get value as Currency object for internal calculations."""
        return Currency(code=self.currency, amount=self.value)


class FAHistoricalData(BaseModel):
    """Historical price data for an asset (list of price points)."""

    model_config = ConfigDict(extra="forbid")

    prices: List[FAPricePoint]
    events: List[FAAssetEventPoint] = Field(default_factory=list, description="Asset events in the date range")
    currency: Optional[str] = None
    source: Optional[str] = None


class FAAssetEventPoint(BaseModel):
    """
    Single asset event data point — shared shape between DB, provider output, and frontend editor.

    Uses Currency class for value (amount + currency code in one object).

    Used in:
    - FAHistoricalData.events (provider output)
    - FAPriceQueryResult.events (API response)
    - FAScheduledInvestmentSchedule.asset_events (provider_params config)
    """

    model_config = ConfigDict(extra="forbid")

    date: date_type = Field(..., description="Event date")
    type: str = Field(..., description="Event type (DIVIDEND, INTEREST, PRICE_ADJUSTMENT, SPLIT)")
    value: Currency = Field(..., description="Event value with currency (amount + code)")
    notes: Optional[str] = Field(None, description="Optional notes")


class FAAssetEventPointOut(FAAssetEventPoint):
    """
    Output-only schema for asset events returned by the API.

    Extends FAAssetEventPoint with DB-level fields needed by the frontend editor:
    - id: Primary key for targeted deletion
    - is_auto: Whether this event was auto-generated by a provider (readonly in UI)
    """

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="Event DB primary key")
    is_auto: bool = Field(..., description="True if generated by provider (provider_assignment_id IS NOT NULL)")


# ============================================================================
# FA EVENT CRUD
# ============================================================================


class FAEventUpsert(BaseModel):
    """Manual event upsert for a single asset (multiple events).

    Groups multiple event points for one asset.
    Only for manual events (provider_assignment_id = NULL).
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    events: List[FAAssetEventPoint] = Field(..., min_length=1, description="List of event points")


class FAEventUpsertResult(BaseModel):
    """Result of event upsert for a single asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    count: int
    message: str


class FABulkEventUpsertResponse(BaseBulkResponse[FAEventUpsertResult]):
    """Response for bulk event upsert."""

    pass


class FAEventDeleteResult(BaseDeleteResult):
    """Result of deleting a single event by ID."""

    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(..., description="ID of the event that was deleted")


class FAEventDeleteItemResult(BaseModel):
    """
    Per-item result of a bulk AssetEvent delete.

    status:
      - "deleted": event removed
      - "not_found": id did not match any event
      - "in_use": event is referenced by one or more transactions (RESTRICT);
                  accessible_transactions[] lists tx IDs the caller can see,
                  hidden_transactions_count counts refs from other users.
    """

    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(..., description="Event ID this result refers to")
    status: Literal["deleted", "not_found", "in_use"] = Field(..., description="Outcome for this event")
    accessible_transactions: List[int] = Field(
        default_factory=list,
        description="Transaction IDs referencing this event that the current user can access",
    )
    hidden_transactions_count: int = Field(
        default=0,
        description="Number of transactions referencing this event that belong to other users",
    )


class FAEventBulkDeleteResponse(BaseModel):
    """
    Aggregate response of a bulk AssetEvent delete.

    Always HTTP 200: inspect per-item ``results`` for per-id outcome.
    Successful deletions are committed even if others are blocked (no partial rollback).
    """

    model_config = ConfigDict(extra="forbid")

    results: List[FAEventDeleteItemResult] = Field(default_factory=list)
    deleted_count: int = Field(..., description="Count of events successfully deleted")
    not_found_count: int = Field(..., description="Count of ids that did not exist")
    in_use_count: int = Field(..., description="Count of events blocked by RESTRICT")


class FAEventQueryItem(BaseModel):
    """Single asset event query in a bulk request."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID to query")
    date_range: DateRangeModel = Field(..., description="Date range (end defaults to start)")


class FAEventQueryResult(BaseModel):
    """Response for a single asset event query."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID queried")
    events: List[FAAssetEventPointOut] = Field(default_factory=list, description="Asset events with id and is_auto")


class FAEventQueryResponse(BaseListResponse[FAEventQueryResult]):
    """Bulk response for event queries."""

    pass


# ============================================================================
# FA PRICE BULK QUERY
# ============================================================================


class FAPriceQueryItem(BaseModel):
    """Single asset price query in a bulk request.

    Uses DateRangeModel from common.py (same as FXConversionRequest.date_range).
    If date_range.end is None, defaults to date_range.start (single day).
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID to query")
    date_range: DateRangeModel = Field(..., description="Date range (end defaults to start)")
    include_price: bool = Field(True, description="Include price history in response")
    include_events: bool = Field(False, description="Include asset events in response")
    target_currency: Optional[str] = Field(None, description="Convert prices to this currency via FX rates (None = native currency)")

    @field_validator("target_currency")
    @classmethod
    def target_currency_validate(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return Currency.validate_code(v)
        return v


class FAPriceQueryResult(BaseModel):
    """Response for a single asset price query."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID queried")
    prices: List[FAPricePoint] = Field(default_factory=list, description="Price history with backward-fill")
    events: List[FAAssetEventPointOut] = Field(
        default_factory=list,
        description="Asset events (if requested). Includes DB id + is_auto flag so the frontend editor can reference them by id.",
    )
    errors: List[str] = Field(default_factory=list, description="Non-fatal warnings (e.g. FX pair missing)")


class FAPriceQueryResponse(BaseListResponse[FAPriceQueryResult]):
    """Bulk response for price queries.

    Inherits from BaseListResponse[FAPriceQueryResult]:
    - items: List[FAPriceQueryResult]  (one per asset queried)
    """

    pass


# ============================================================================
# FA BULK CURRENT PRICE
# ============================================================================


class FACurrentPriceItem(BaseModel):
    """Current price result for a single asset."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    value: Optional[Decimal] = Field(None, description="Current price value")
    currency: Optional[str] = Field(None, description="Currency code (ISO 4217)")
    as_of_date: Optional[date_type] = Field(None, description="Date/time the price refers to")
    source: Optional[str] = Field(None, description="Price source (e.g. 'provider:justetf', 'db:last_known')")
    error: Optional[str] = Field(None, description="Error message if price could not be fetched")


class FACurrentPriceResponse(BaseBulkResponse[FACurrentPriceItem]):
    """Response for bulk current-price fetch.

    Inherits from BaseBulkResponse[FACurrentPriceItem]:
    - results: List[FACurrentPriceItem]
    - success_count: int
    - errors: List[str]
    """

    pass
