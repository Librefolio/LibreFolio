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
from typing import Annotated, List, Literal, Optional, Union

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.app.schemas.assets.events import FAAssetEventPoint, FAAssetEventPointOut
from backend.app.schemas.common import (
    BackwardFillInfo,
    BaseBulkDeleteResponse,
    BaseBulkResponse,
    BaseDeleteResult,
    BaseListResponse,
    Currency,
    DateRangeModel,
    FxBackwardFillInfo,
    PeriodChangesAsOf,
    SafeDecimal,
    StrictModel,
)
from backend.app.schemas.signals import (
    SignalAnnotationRequest,
    SignalBandValueSource,
    SignalLineCrossoverRequest,
    SignalOutputValueSource,
    SignalRequest,
    SignalResult,
)
from backend.app.services.assets.price_sampling import SampleResolution  # Z-29: a pure module of dates, no service

#: A price query item's key, and a sample_like naming one (Z-29)
SAMPLE_KEY_PATTERN = r"^[A-Za-z0-9_.:-]{1,64}$"

# ============================================================================
# BACKWARD-FILL INFO (EXTENDED FOR FX STALENESS)
# ============================================================================


class AssetBackwardFillInfo(BackwardFillInfo, FxBackwardFillInfo):
    """Extended backward-fill info for asset prices with FX staleness tracking.

    Composed via multiple inheritance from two orthogonal dimensions:
    - ``BackwardFillInfo`` → price staleness (``actual_rate_date``, ``days_back``).
    - ``FxBackwardFillInfo`` → FX staleness (``fx_rate_date``, ``fx_days_back``).

    This is the right shape **only** for price points, which can have both
    dimensions at once (e.g. a stale price AND a stale FX rate for its
    conversion). For events and other entities that don't have price
    backward-fill semantics, use ``FxBackwardFillInfo`` directly.

    Wire format: inherits all 4 fields; serialization is identical to the
    previous flat class — no client-side breaking change.
    """


# ============================================================================
# FA PRICE UPSERT
# ============================================================================


def _description_without_backticks(schema: dict) -> None:
    """The web client's generator writes the description of a required field's model between backticks
    (openapi-zod-client, a multi-line text in a template literal): a backtick inside would end it. Since Z-29,
    ``FAPriceSampleBounds`` holds two required ``FAPricePoint`` fields; the docstring keeps its backticks, the
    schema says quotes."""
    if isinstance(schema.get("description"), str):
        schema["description"] = schema["description"].replace("`", "'")


class FAPricePoint(StrictModel):
    """Single price point with OHLC data.

    Used for:
    - a provider's history (``FAHistoricalData``) and the Sync's ``changed_points`` (backward_fill_info is None);
    - query results (backward_fill_info may be present).

    The API contract uses separate `close: Decimal` and `currency: str` fields
    for JSON compatibility. Build a `Currency(code=…, amount=…)` inline where
    a Currency object is needed (project-wide style).

    A manual write uses ``FAPriceWritePoint`` (N92), where ``"clear"`` empties a stored field. This model checks no
    sign: the refresh discards a provider's point with a price not above 0, and the write model refuses one (N92).
    """

    model_config = ConfigDict(json_schema_extra=_description_without_backticks)

    date: date_type = Field(..., description="Price date")
    open: Optional[SafeDecimal] = Field(None, description="Opening price (None when unknown)")
    high: Optional[SafeDecimal] = Field(None, description="High price (None when unknown)")
    low: Optional[SafeDecimal] = Field(None, description="Low price (None when unknown)")
    close: SafeDecimal = Field(..., description="Closing price")
    volume: Optional[SafeDecimal] = Field(None, description="Trading volume (None when unknown)")
    currency: Optional[str] = Field(
        None,
        description=(
            "Currency code (ISO 4217). Post-Blocco I: OPTIONAL in both request and response. "
            "On upsert, if omitted the backend uses `asset.currency`; if provided and != asset.currency, "
            "the whole upsert is refused with HTTP 422 price_currency_mismatch before anything is written "
            "(defensive — the frontend no longer sends it). "
            "On response, kept populated for backward compat but the frontend uses `asset.currency` "
            "as single source of truth; see phase-07 Blocco I for rationale."
        ),
    )
    original_currency: Optional[str] = Field(None, description="Original currency before FX conversion (None = no conversion)")
    original_close: Optional[SafeDecimal] = Field(None, description="Close price in original currency before FX conversion")
    original_open: Optional[SafeDecimal] = Field(None, description="Open price in original currency before FX conversion")
    original_high: Optional[SafeDecimal] = Field(None, description="High price in original currency before FX conversion")
    original_low: Optional[SafeDecimal] = Field(None, description="Low price in original currency before FX conversion")
    source_plugin_key: Optional[str] = Field(None, description="Provider key that produced the stored price")
    backward_fill_info: Optional[AssetBackwardFillInfo] = Field(None, description="Backward-fill + FX staleness info (only in query results)")

    @field_validator("currency")
    @classmethod
    def currency_validate(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return Currency.validate_code(v)

    @field_validator("open", "high", "low", "close", "volume", "original_open", "original_high", "original_low", "original_close", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


#: The value of a manual write that empties a stored open, high, low or volume (N92); ``null`` or no field leaves it.
CLEAR = "clear"

#: A manual write's open, high, low or volume (N92): a number, written; ``"clear"``, which empties the stored value; or
#: ``null``. Read left to right, so ``"clear"`` is never taken for a number; any other text is refused. The ``enum``
#: beside pydantic's ``const`` makes the generated client read ``'clear'`` as a literal (openapi-zod-client 1.18.3
#: ignores ``const``), as in ``schemas/signals.py``.
PriceWriteValue = Annotated[Union[Annotated[Literal["clear"], Field(json_schema_extra={"enum": [CLEAR]})], SafeDecimal, None], Field(union_mode="left_to_right")]


class FAPriceWritePoint(StrictModel):
    """One price point of a manual write (``POST /assets/prices``), N92.

    ``open``, ``high``, ``low`` and ``volume`` each take a number of 0 or more, written as it is; the string ``"clear"``,
    which empties the stored value (NULL); or ``null``, or no field at all, which leaves the stored value as it is.
    ``close`` is required and above 0: LibreFolio keeps no negative price. The ``-1`` that emptied a field before N92 is
    a negative number now, refused. ``from_attributes``: a ``FAPricePoint`` can be given, read field by field.
    """

    model_config = ConfigDict(from_attributes=True)

    date: date_type = Field(..., description="Price date")
    open: PriceWriteValue = Field(None, description="Opening price: a number (0 or more) writes it, 'clear' empties the stored value, null or absent leaves it")
    high: PriceWriteValue = Field(None, description="High price: a number (0 or more) writes it, 'clear' empties the stored value, null or absent leaves it")
    low: PriceWriteValue = Field(None, description="Low price: a number (0 or more) writes it, 'clear' empties the stored value, null or absent leaves it")
    close: SafeDecimal = Field(..., description="Closing price, above 0 (required)")
    volume: PriceWriteValue = Field(None, description="Trading volume: a number (0 or more) writes it, 'clear' empties the stored value, null or absent leaves it")
    currency: Optional[str] = Field(None, description="Currency code (ISO 4217), optional: if omitted the backend uses `asset.currency`; if provided and != asset.currency, the whole upsert is refused with HTTP 422 price_currency_mismatch before anything is written.")

    @field_validator("currency")
    @classmethod
    def currency_validate(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return Currency.validate_code(v)

    @field_validator("close", mode="after")
    @classmethod
    def close_above_zero(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("close price must be above 0")
        return v

    @field_validator("open", "high", "low", "volume", mode="after")
    @classmethod
    def zero_or_more_or_clear(cls, v: Decimal | str | None) -> Decimal | str | None:
        if v is None or v == CLEAR:
            return v
        if v < 0:
            raise ValueError('price and volume fields must be 0 or more, or "clear" to empty the stored value')
        return v


class FAUpsert(StrictModel):
    """Price upsert for a single asset (multiple dates).

    Groups multiple price points for one asset.
    """

    asset_id: int = Field(..., description="Asset ID")
    prices: List[FAPriceWritePoint] = Field(..., min_length=1, description="List of price points (N92: open, high, low and volume take a number, 'clear' or null)")


class FAPriceRejection(StrictModel):
    """A date a price upsert left out, and why (X-R46): the data editor names it instead of counting it as saved."""

    date: date_type = Field(..., description="The date left out")
    reason: Literal["ohlc_inconsistent", "date_out_of_range", "value_not_storable"] = Field(
        ...,
        description="ohlc_inconsistent: the close lies outside [low, high]; date_out_of_range: a provider's date after tomorrow; value_not_storable: a provider's value no price column can keep",
    )


class FAUpsertResult(StrictModel):
    """Result of price upsert for single asset."""

    asset_id: int
    count: int
    message: str
    rejected: List[FAPriceRejection] = Field(default_factory=list, description="The dates left out, in date order, each with its reason (X-R46); `count` does not include them")


class FABulkUpsertResponse(BaseBulkResponse[FAUpsertResult]):
    """Response for bulk price upsert."""

    # Operation-specific fields
    inserted_count: int = Field(..., description="Number of prices inserted")
    updated_count: int = Field(..., description="Number of prices updated")


# ============================================================================
# FA PRICE DELETE
# ============================================================================


class FAAssetDelete(StrictModel):
    """Price deletion request for a single asset (multiple ranges).

    Groups multiple date ranges for one asset.
    Uses DateRangeModel for consistency.
    """

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


# ============================================================================
# FA PRICE QUERY
# ============================================================================


class FACurrentValue(StrictModel):
    """Current value of an asset.

    The API contract uses separate `value: Decimal` and `currency: str` fields
    for JSON compatibility. Build a `Currency(code=…, amount=…)` inline where
    a Currency object is needed (project-wide style).
    """

    value: SafeDecimal
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


class FAHistoricalData(StrictModel):
    """Historical price data for an asset (list of price points)."""

    prices: List[FAPricePoint]
    events: List[FAAssetEventPoint] = Field(default_factory=list, description="Asset events in the date range")
    currency: Optional[str] = Field(
        None,
        description="The quote currency as the provider reports it, NOT normalized (Yahoo's `GBp` for a line quoted in pence; the price points carry the ISO code, `GBP`): a validator here would hide the minor unit.",
    )
    source: Optional[str] = None


# ============================================================================
# FA PRICE BULK QUERY
# ============================================================================


class FAPriceQueryItem(StrictModel):
    """Single asset price query in a bulk request.

    Uses DateRangeModel from common.py (same as FXConversionRequest.date_range).
    If date_range.end is None, defaults to date_range.start (single day).
    """

    asset_id: int = Field(..., description="Asset ID to query")
    date_range: DateRangeModel = Field(..., description="Date range (end defaults to start)")
    include_price: bool = Field(True, description="Include price history in response")
    include_events: bool = Field(False, description="Include asset events in response")
    target_currency: Optional[str] = Field(None, description="Convert prices to this currency via FX rates (None = native currency)")
    signals: List[SignalRequest] = Field(
        default_factory=list,
        description="Technical signal instances to compute on the requested asset series",
    )
    annotation_requests: List[SignalAnnotationRequest] = Field(
        default_factory=list,
        description="Optional cross/threshold rules evaluated on extended signal output",
    )
    key: Optional[str] = Field(None, pattern=SAMPLE_KEY_PATTERN, description="A name for this item, unique in the request, that another item's sample_like can give (Z-29)")
    max_points: Optional[int] = Field(
        None,
        ge=1,
        le=10_000,
        description=(
            "Sample the series for a compact chart (Z-29): the most points the chart's plot takes. Per asset, the finest of daily, weekly (ISO, Monday to Sunday) and monthly whose count over the asset's own fill fits, "
            "monthly when none does; a weekly or monthly series is the last point of each week or month, each the point the daily series has on that date, and sample_bounds its first and last points. "
            "The result's resolution says the step. At most one of max_points, resolution and sample_like; not with signals, annotation_requests or include_events. None: every day."
        ),
    )
    resolution: Optional[SampleResolution] = Field(None, description="Sample the series at this step whatever its length (Z-29): daily, weekly (ISO, Monday to Sunday) or monthly; as max_points does otherwise")
    sample_like: Optional[str] = Field(
        None,
        pattern=SAMPLE_KEY_PATTERN,
        description=(
            "Sample the series like the item of this request whose key this is (Z-29): its step and buckets, from the later of its first day and this item's own; the same date_range. "
            "A comparison's target, on its card. That item has no sample_like itself; with nothing to fill it lends its max_points or resolution."
        ),
    )

    @field_validator("target_currency")
    @classmethod
    def target_currency_validate(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return Currency.validate_code(v)
        return v

    @model_validator(mode="after")
    def validate_signal_references(self) -> FAPriceQueryItem:
        instance_ids = [signal.instance_id for signal in self.signals]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("signal instance_id values must be unique")
        annotation_keys = [annotation.key for annotation in self.annotation_requests]
        if len(annotation_keys) != len(set(annotation_keys)):
            raise ValueError("annotation request keys must be unique")
        known_instances = set(instance_ids)
        for annotation in self.annotation_requests:
            if annotation.attach_to_instance_id not in known_instances:
                raise ValueError(f"annotation target '{annotation.attach_to_instance_id}' is not in signals")
            sources = (annotation.left, annotation.right) if isinstance(annotation, SignalLineCrossoverRequest) else (annotation.source,)
            for source in sources:
                if isinstance(source, (SignalOutputValueSource, SignalBandValueSource)) and source.instance_id not in known_instances:
                    raise ValueError(f"annotation source '{source.instance_id}' is not in signals")
        return self

    @model_validator(mode="after")
    def validate_sampling(self) -> FAPriceQueryItem:
        """One way to sample the series at most, and a sampled series alone: signals, their annotations and events need
        every day (Z-29)."""
        asked = [name for name in ("max_points", "resolution", "sample_like") if getattr(self, name) is not None]
        if len(asked) > 1:
            raise ValueError(f"at most one of max_points, resolution and sample_like, not {' and '.join(asked)}")
        if asked and (self.signals or self.annotation_requests or self.include_events):
            raise ValueError(f"{asked[0]} samples the price series alone: not with signals, annotation_requests or include_events")
        return self


class FAPriceSampleBounds(StrictModel):
    """The ends of a sampled price series (Z-29): the chart draws the last point of each week or month, and these two
    points apart — the fill's first, from which the percentage view and «All» start, and its last."""

    first: FAPricePoint = Field(..., description="The fill's first point: the range's start when a row precedes it, else the asset's first row in the range (with sample_like, the later of that and the item named's)")
    last: FAPricePoint = Field(..., description="The fill's last point, on the range's end once cut at the ceiling: the last point of prices too")


class FAPriceQueryResult(StrictModel):
    """Response for a single asset price query."""

    asset_id: int = Field(..., description="Asset ID queried")
    prices: List[FAPricePoint] = Field(default_factory=list, description="Price history with backward-fill")
    events: List[FAAssetEventPointOut] = Field(
        default_factory=list,
        description="Asset events (if requested). Includes DB id + is_auto flag so the frontend editor can reference them by id.",
    )
    errors: List[str] = Field(default_factory=list, description="Non-fatal warnings (e.g. FX pair missing)")
    signals: List[SignalResult] = Field(
        default_factory=list,
        description="Technical signal results keyed by request instance_id",
    )
    resolution: SampleResolution = Field("daily", description="The step of prices (Z-29): daily, or weekly or monthly when the item's max_points, resolution or sample_like sampled the series")
    sample_bounds: Optional[FAPriceSampleBounds] = Field(None, description="A weekly or monthly series' first and last points (Z-29); None for a daily one")


class FAPriceQueryResponse(BaseListResponse[FAPriceQueryResult]):
    """Bulk response for price queries.

    Inherits from BaseListResponse[FAPriceQueryResult]:
    - items: List[FAPriceQueryResult]  (one per asset queried)
    """


# ============================================================================
# FA BULK CURRENT PRICE
# ============================================================================


class FARangeChange(StrictModel):
    """The change of an asset's price over the whole range the page shows (X-R59): the first and last point of its series."""

    reference_date: Optional[date_type] = Field(None, description="The day of the reference price: range_start, or the first price inside the range when none is on or before it; null without any")
    change_abs: Optional[SafeDecimal] = Field(None, description="Price on as_of (or the live price) − reference price, in the result's currency; null without a usable price (a reference ≤ 0, a negative price)")
    change_ratio: Optional[SafeDecimal] = Field(None, description="((Price on as_of or the live price) ÷ reference price) − 1; −1 for a price of 0; null without a usable price")


class FACurrentPriceItem(StrictModel):
    """Current price result for a single asset."""

    asset_id: int = Field(..., description="Asset ID")
    value: Optional[SafeDecimal] = Field(None, description="Current price value")
    currency: Optional[str] = Field(None, description="Currency code (ISO 4217)")
    as_of_date: Optional[date_type] = Field(None, description="Date/time the price refers to")
    source: Optional[str] = Field(None, description="Price source (e.g. 'provider:justetf', 'db:last_known')")
    error: Optional[str] = Field(None, description="Error message if price could not be fetched")
    error_code: Optional[str] = Field(None, description="'RATE_LIMITED' when the provider refused for too many requests or is paused: the price is then the last one stored, if any")
    retry_after: Optional[float] = Field(None, ge=0, description="With RATE_LIMITED: seconds until the provider may be called again")
    range_change: Optional[FARangeChange] = Field(None, description="With range_start: the change from the reference of the range to this price (X-R59), the one the page shows with a live quote")


class FACurrentPriceResponse(BaseBulkResponse[FACurrentPriceItem]):
    """Response for bulk current-price fetch.

    Inherits from BaseBulkResponse[FACurrentPriceItem]:
    - results: List[FACurrentPriceItem]
    - success_count: int
    - errors: List[str]
    """


# ============================================================================
# FA FIXED-PERIOD CHANGES (MF-P2, D-MF6 b)
# ============================================================================


class FAPeriodChangesQueryItem(StrictModel):
    """One asset of a fixed-period changes request: the Assets table's Δ columns (1D … 5Y), up to ``as_of``."""

    asset_id: int = Field(..., description="Asset ID")
    as_of: PeriodChangesAsOf = Field(..., description="Anchor day: the end of the range the table shows (1900-01-01 or later)")
    target_currency: Optional[str] = Field(None, description="Value the prices in this currency, each day's at that day's rate (None = native currency)")
    range_start: Optional[PeriodChangesAsOf] = Field(None, description="First day of the range the page shows: asks its whole-range change (X-R59); on or before as_of")

    @field_validator("target_currency")
    @classmethod
    def target_currency_validate(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return Currency.validate_code(v)
        return v

    @model_validator(mode="after")
    def validate_range_start(self) -> FAPeriodChangesQueryItem:
        if self.range_start is not None and self.range_start > self.as_of:
            raise ValueError(f"range_start ({self.range_start}) must be on or before as_of ({self.as_of})")
        return self


class FAPeriodChange(StrictModel):
    """The change of an asset's price over one fixed period, as a fraction (0.05 = +5 %)."""

    key: str = Field(..., description="Period key: 1D, 1W, 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y")
    days: int = Field(..., ge=1, description="Calendar days of the period")
    change_ratio: Optional[SafeDecimal] = Field(None, description="(Price on as_of ÷ price on as_of − days) − 1; −1 for a price of 0 on as_of; null without a usable price on either day")


class FAPeriodChangesResult(StrictModel):
    """The fixed-period changes of one asset.

    The price on a day is the last stored price on or before it, the rule of the price history's backward fill; with a
    ``target_currency`` it is converted at that day's rate.
    """

    asset_id: int = Field(..., description="Asset ID")
    as_of: date_type = Field(..., description="Anchor day")
    currency: Optional[str] = Field(None, description="Currency of the compared prices: target_currency when given, else the asset's own on as_of (null with no price up to as_of)")
    periods: List[FAPeriodChange] = Field(default_factory=list, description="One entry per fixed period, in display order")
    range_change: Optional[FARangeChange] = Field(None, description="The whole-range change, when range_start was asked")
    errors: List[str] = Field(default_factory=list, description="Non-fatal warnings (e.g. a missing FX rate)")


class FAPeriodChangesResponse(BaseListResponse[FAPeriodChangesResult]):
    """Bulk response of fixed-period changes: one item per requested asset, in request order."""
