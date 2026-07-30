"""Shared, JSON-safe Pydantic payload models for the AI Export technical wave.

Every model here backs one or more of the real `portfolio.technical_*`,
`broker.technical_*`, `asset.{ohlc_returns,indicators,states_events}` and
`fx.{rate_ohlc,returns_volatility,indicators,states_events}` `ComponentSpec`
builders (see `technical_shared.py`, `portfolio_broker_technical.py` and
`asset_fx_technical.py`). All models are ``extra="forbid"`` and JSON-safe
(floats/dates/strings only - no ``Decimal``), and every tuple field is
deterministically ordered by its producing builder (never re-sorted here).

Design notes:
- Price/rate/return series retain the generic OHLC-style `TechnicalBucket`.
- Plugin indicators are row-oriented: one `IndicatorTablePayload` per plugin
  instance, one `IndicatorBucketRow` per temporal bucket, and one cell per
  scalar output or band component. Cells preserve real observation dates and
  use a compact single-observation shape or complete first/min/max/last stats.
- Discrete events/state-changes are never bucket-aggregated numerically: they
  are assigned to buckets verbatim via `temporal.aggregators.assign_discrete_events`
  (dedup, never averaged/truncated/capped) and exposed as `TechnicalEventBucket`.
- Detail level (Compact/Standard/Full) only changes bucket *counts* (via the
  `BuildContext.bucket_plan`), never the emitted signal/entity/event set - see
  the module-level requirement in the refinement plan/todo.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalBandComponent,
    SignalSeriesKind,
)


class TechnicalBucket(BaseModel):
    """One OHLC-style bucket for a continuous (single- or multi-output) series.

    Empty buckets are explicit: ``first``/``minimum``/``maximum``/``last`` are
    all ``None`` and ``observation_count == 0`` (never synthesized/carried
    forward - see `temporal.aggregators.aggregate_continuous_multi_output`).
    """

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    calendar_days: int = Field(..., ge=1)
    first: dict[str, float] | None = None
    minimum: dict[str, float] | None = None
    maximum: dict[str, float] | None = None
    last: dict[str, float] | None = None
    observation_count: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_bucket(self) -> TechnicalBucket:
        if self.start_date > self.end_date:
            raise ValueError("start_date must not follow end_date")
        if self.calendar_days != (self.end_date - self.start_date).days + 1:
            raise ValueError("calendar_days must match the inclusive bucket range")
        values = (self.first, self.minimum, self.maximum, self.last)
        if self.observation_count == 0 and any(value is not None for value in values):
            raise ValueError("empty technical buckets must not contain values")
        if self.observation_count > 0 and any(value is None for value in values):
            raise ValueError("populated technical buckets require first/minimum/maximum/last")
        return self


class PriceBucket(TechnicalBucket):
    """Price/rate OHLC plus the return from the previous observed bucket close."""

    minimum_date: date | None = None
    maximum_date: date | None = None
    return_start_date: date | None = None
    simple_return: float | None = None


class ReturnVolatilityBucket(TechnicalBucket):
    """An FX daily-return OHLC bucket (``"return"`` key) plus its bucket-local realized volatility."""

    volatility: float | None = None


class AssetPriceSeriesPayload(BaseModel):
    """One held asset's price/return OHLC-bucketed series (Portfolio/Broker universe)."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    weight: float | None = None
    currency: str
    buckets: tuple[PriceBucket, ...]
    latest_close: float | None = None
    latest_date: date | None = None


class AssetOhlcReturnsPayload(BaseModel):
    """`asset.ohlc_returns`: single-target price/return OHLC-bucketed series."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    currency: str
    buckets: tuple[PriceBucket, ...]
    latest_close: float | None = None
    latest_date: date | None = None


class PortfolioTechnicalPricesPayload(BaseModel):
    """`portfolio.technical_prices`: per-asset price/return series over the full eligible universe."""

    model_config = ConfigDict(extra="forbid")

    assets: tuple[AssetPriceSeriesPayload, ...]
    eligible_asset_count: int
    considered_asset_count: int


class TechnicalDatedValue(BaseModel):
    """One finite value paired with its real observation date."""

    model_config = ConfigDict(extra="forbid")

    value: FiniteFloat
    date: date


class TechnicalSingleValueCell(BaseModel):
    """Compact cell for a bucket containing exactly one finite observation."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["single"] = "single"
    value: FiniteFloat
    date: date


class TechnicalRangeValueCell(BaseModel):
    """Complete dated statistics for a bucket containing multiple observations."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["range"] = "range"
    observation_count: int = Field(..., ge=2)
    first: TechnicalDatedValue
    min: TechnicalDatedValue
    max: TechnicalDatedValue
    last: TechnicalDatedValue

    @model_validator(mode="after")
    def validate_statistics(self) -> TechnicalRangeValueCell:
        if self.first.date > self.last.date:
            raise ValueError("first date must not follow last date")
        if self.min.value > self.max.value:
            raise ValueError("min value must not exceed max value")
        if not self.min.value <= self.first.value <= self.max.value:
            raise ValueError("first value must fall inside min/max")
        if not self.min.value <= self.last.value <= self.max.value:
            raise ValueError("last value must fall inside min/max")
        return self


TechnicalIndicatorCell = Annotated[
    Union[TechnicalSingleValueCell, TechnicalRangeValueCell],
    Field(discriminator="kind"),
]


class IndicatorOutputColumn(BaseModel):
    """Plugin-owned metadata for one scalar output or one band component."""

    model_config = ConfigDict(extra="forbid")

    column_key: str
    output_key: str
    component: SignalBandComponent | None = None
    semantic_id: str
    semantic_description: str
    unit: str
    kind: SignalSeriesKind
    aggregation_profile: SignalAggregationProfile
    latest: TechnicalDatedValue | None = None


class IndicatorBucketRow(BaseModel):
    """One temporal row shared by every output column of one plugin instance."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    calendar_days: int = Field(..., ge=1)
    observation_count: int = Field(..., ge=0)
    cells: dict[str, TechnicalIndicatorCell | None]

    @model_validator(mode="after")
    def validate_bucket(self) -> IndicatorBucketRow:
        if self.start_date > self.end_date:
            raise ValueError("start_date must not follow end_date")
        if self.calendar_days != (self.end_date - self.start_date).days + 1:
            raise ValueError("calendar_days must match the inclusive bucket range")
        cell_counts = [1 if isinstance(cell, TechnicalSingleValueCell) else cell.observation_count for cell in self.cells.values() if cell is not None]
        if cell_counts and max(cell_counts) > self.observation_count:
            raise ValueError("cell observation count cannot exceed row observation_count")
        if self.observation_count == 0 and cell_counts:
            raise ValueError("empty indicator rows must not contain populated cells")
        for cell in self.cells.values():
            if isinstance(cell, TechnicalSingleValueCell):
                dates = (cell.date,)
            elif isinstance(cell, TechnicalRangeValueCell):
                dates = (cell.first.date, cell.min.date, cell.max.date, cell.last.date)
            else:
                continue
            if any(day < self.start_date or day > self.end_date for day in dates):
                raise ValueError("cell dates must fall inside the bucket")
        return self


class IndicatorTablePayload(BaseModel):
    """One plugin instance with temporally local output columns and bucket rows.

    Plugin and output semantics are copied from `describe_for_ai()` and
    `SignalOutputSpec`; AI Export never re-derives indicator meaning.
    """

    model_config = ConfigDict(extra="forbid")

    instance_id: str
    signal_code: str
    semantic_id: str
    semantic_description: str
    category: str
    columns: tuple[IndicatorOutputColumn, ...] = Field(..., min_length=1)
    rows: tuple[IndicatorBucketRow, ...] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_table(self) -> IndicatorTablePayload:
        column_keys = [column.column_key for column in self.columns]
        if len(column_keys) != len(set(column_keys)):
            raise ValueError("indicator column keys must be unique")
        expected_keys = set(column_keys)
        for row in self.rows:
            if set(row.cells) != expected_keys:
                raise ValueError("every indicator row must contain exactly the declared columns")
        for previous, current in zip(self.rows, self.rows[1:], strict=False):
            if current.start_date != previous.end_date + timedelta(days=1):
                raise ValueError("indicator rows must be contiguous and ordered")
        return self


class AssetIndicatorsPayload(BaseModel):
    """One held asset's full curated indicator bundle (Portfolio/Broker universe)."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    weight: float | None = None
    indicators: tuple[IndicatorTablePayload, ...]


class UniverseIndicatorsPayload(BaseModel):
    """`portfolio.technical_indicators` / `broker.technical_indicators`: per-asset indicators, full universe."""

    model_config = ConfigDict(extra="forbid")

    assets: tuple[AssetIndicatorsPayload, ...]
    eligible_asset_count: int
    considered_asset_count: int


class SingleTargetIndicatorsPayload(BaseModel):
    """`asset.indicators` / `fx.indicators`: the curated indicator bundle for one target."""

    model_config = ConfigDict(extra="forbid")

    indicators: tuple[IndicatorTablePayload, ...]


class TechnicalEventPayload(BaseModel):
    """One preserved-verbatim technical state-change event (crossover/threshold-crossing)."""

    model_config = ConfigDict(extra="forbid")

    date: date
    key: str
    annotation_type: str
    signal_code: str
    semantic_description: str
    direction: str | None = None
    values: dict[str, float]
    asset_id: int | None = None


class TechnicalEventBucket(BaseModel):
    """Every deduplicated event assigned to one bucket, verbatim (never averaged/truncated)."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    calendar_days: int = Field(..., ge=1)
    events: tuple[TechnicalEventPayload, ...] = ()
    event_count: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_bucket(self) -> TechnicalEventBucket:
        if self.start_date > self.end_date:
            raise ValueError("start_date must not follow end_date")
        if self.calendar_days != (self.end_date - self.start_date).days + 1:
            raise ValueError("calendar_days must match the inclusive bucket range")
        if self.event_count != len(self.events):
            raise ValueError("event_count must match events")
        if any(event.date < self.start_date or event.date > self.end_date for event in self.events):
            raise ValueError("event dates must fall inside the bucket")
        return self


class TechnicalEventsPayload(BaseModel):
    """`*.technical_events` / `*.states_events`: the complete bucketed event timeline.

    ``total_event_count`` is the deduplicated total across every bucket (no
    legacy top-N/10/40/120 cap - every surviving event is present in exactly
    one bucket, and an empty event list is a valid payload).
    """

    model_config = ConfigDict(extra="forbid")

    buckets: tuple[TechnicalEventBucket, ...]
    total_event_count: int


class BreadthStateBucket(BaseModel):
    """Weighted/unweighted share of the eligible universe currently in one reference-level state.

    ``state`` is derived generically from the owning plugin's own
    `SignalOutputSpec.default_reference_levels` (e.g. RSI/MFI's own
    oversold/overbought labels) - never a hardcoded threshold.
    """

    model_config = ConfigDict(extra="forbid")

    signal_code: str
    output_key: str
    state: str
    unweighted_count: int
    unweighted_ratio: float
    weighted_ratio: float


class UniverseBreadthPayload(BaseModel):
    """`portfolio.technical_breadth` / `broker.technical_breadth`: reconciled coverage + breadth states."""

    model_config = ConfigDict(extra="forbid")

    eligible_asset_count: int
    considered_asset_count: int
    covered_asset_count: int
    total_weight: float
    states: tuple[BreadthStateBucket, ...]


class FxRateOhlcPayload(BaseModel):
    """`fx.rate_ohlc`: daily base->quote conversion rate, OHLC-bucketed (``"rate"`` key)."""

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    buckets: tuple[PriceBucket, ...]
    latest_rate: float | None = None
    latest_date: date | None = None


class FxReturnsVolatilityPayload(BaseModel):
    """`fx.returns_volatility`: daily rate return + bucket-local realized volatility."""

    model_config = ConfigDict(extra="forbid")

    base_currency: str
    quote_currency: str
    buckets: tuple[ReturnVolatilityBucket, ...]


__all__ = [
    "AssetIndicatorsPayload",
    "AssetOhlcReturnsPayload",
    "AssetPriceSeriesPayload",
    "BreadthStateBucket",
    "FxRateOhlcPayload",
    "FxReturnsVolatilityPayload",
    "IndicatorBucketRow",
    "IndicatorOutputColumn",
    "IndicatorTablePayload",
    "PortfolioTechnicalPricesPayload",
    "PriceBucket",
    "ReturnVolatilityBucket",
    "SingleTargetIndicatorsPayload",
    "TechnicalBucket",
    "TechnicalDatedValue",
    "TechnicalEventBucket",
    "TechnicalEventPayload",
    "TechnicalEventsPayload",
    "TechnicalIndicatorCell",
    "TechnicalRangeValueCell",
    "TechnicalSingleValueCell",
    "UniverseBreadthPayload",
    "UniverseIndicatorsPayload",
]
