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
    SignalTemporalClass,
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
    portfolio_weight_ratio: float | None = Field(
        None,
        description="Gross absolute open-position value of this unique asset / gross eligible exposure. Aggregated once per asset ID across brokers. Fraction in [0,1]; None if weightless.",
    )
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
    eligible_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique eligible currently-held (not fully sold, non-zero end value) assets, broker-deduplicated. Denominator of the eligible technical universe. Unit: assets.",
    )
    period_position_leg_count: int = Field(
        ...,
        ge=0,
        description="Period (broker_id, asset_id) position-contribution legs before eligibility, including legs fully sold inside the period. NOT a unique-asset count. Unit: legs.",
    )
    period_contributor_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique asset IDs across ALL period contribution legs before eligibility (broker-deduplicated, includes fully-sold-in-period assets). Between eligible_asset_count and period_position_leg_count. Unit: assets.",
    )
    covered_asset_count: int = Field(
        ...,
        ge=0,
        description="Eligible assets with a returned price series in this payload (subset of eligible_asset_count). Unit: assets.",
    )


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
    minimum: FiniteFloat | None = None
    maximum: FiniteFloat | None = None
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
    """One plugin instance with class-aware rows plus whole-period state.

    Plugin and output semantics are copied from `describe_for_ai()` and
    `SignalOutputSpec`; AI Export never re-derives indicator meaning.
    """

    model_config = ConfigDict(extra="forbid")

    instance_id: str
    signal_code: str
    temporal_class: SignalTemporalClass
    semantic_id: str
    semantic_description: str
    category: str
    portfolio_weight_ratio: float | None = Field(
        None,
        description="Gross absolute open-position value per unique asset / gross eligible exposure. Fraction in [0,1]; None if weightless.",
    )
    technical_normalized_weight_ratio: float | None = Field(
        None,
        description="portfolio_weight_ratio renormalized to sum to 1 across the covered universe of THIS Signal instance/state only (not across the whole portfolio). Fraction in [0,1]; None if uncovered.",
    )
    columns: tuple[IndicatorOutputColumn, ...] = Field(..., min_length=1)
    period_summary: dict[str, TechnicalIndicatorCell | None]
    rows: tuple[IndicatorBucketRow, ...] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_table(self) -> IndicatorTablePayload:
        column_keys = [column.column_key for column in self.columns]
        if len(column_keys) != len(set(column_keys)):
            raise ValueError("indicator column keys must be unique")
        expected_keys = set(column_keys)
        if set(self.period_summary) != expected_keys:
            raise ValueError("period_summary must contain exactly the declared columns")
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
    portfolio_weight_ratio: float | None = Field(
        None,
        description="Gross absolute open-position value of this unique asset / gross eligible exposure. Aggregated once per asset ID across brokers. Fraction in [0,1]; None if weightless.",
    )
    indicators: tuple[IndicatorTablePayload, ...]


class UniverseIndicatorsPayload(BaseModel):
    """`portfolio.technical_indicators` / `broker.technical_indicators`: per-asset indicators, full universe."""

    model_config = ConfigDict(extra="forbid")

    assets: tuple[AssetIndicatorsPayload, ...]
    eligible_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique eligible currently-held (not fully sold, non-zero end value) assets, broker-deduplicated. Unit: assets.",
    )
    period_position_leg_count: int = Field(
        ...,
        ge=0,
        description="Period (broker_id, asset_id) position-contribution legs before eligibility, including legs fully sold inside the period. NOT a unique-asset count. Unit: legs.",
    )
    period_contributor_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique asset IDs across ALL period contribution legs before eligibility (broker-deduplicated, includes fully-sold-in-period assets). Unit: assets.",
    )
    covered_asset_count: int = Field(
        ...,
        ge=0,
        description="Eligible assets that produced at least one curated indicator instance (subset of eligible_asset_count). Unit: assets.",
    )
    eligible_portfolio_weight_ratio: float = Field(
        ...,
        description="Sum of gross absolute open-position weight ratios across all eligible assets. Denominator for covered_weight_ratio. Fraction in [0,1].",
    )
    covered_portfolio_weight_ratio: float = Field(
        ...,
        description="Sum of gross absolute open-position weight ratios across covered assets only. Fraction in [0,1].",
    )
    covered_weight_ratio: float = Field(
        ...,
        description="covered_portfolio_weight_ratio / eligible_portfolio_weight_ratio. Share of eligible gross exposure that is indicator-covered. Fraction in [0,1].",
    )


class SingleTargetIndicatorsPayload(BaseModel):
    """`asset.indicators` / `fx.indicators`: the curated indicator bundle for one target."""

    model_config = ConfigDict(extra="forbid")

    indicators: tuple[IndicatorTablePayload, ...]


class TechnicalNumericBounds(BaseModel):
    """Optional plugin-owned numerical bounds for one rendered value."""

    model_config = ConfigDict(extra="forbid")

    minimum: FiniteFloat | None = None
    maximum: FiniteFloat | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> TechnicalNumericBounds:
        if self.minimum is None and self.maximum is None:
            raise ValueError("technical numeric bounds require minimum and/or maximum")
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("technical numeric bounds minimum must be lower than maximum")
        return self


class TechnicalEventPayload(BaseModel):
    """One preserved-verbatim technical state-change event (crossover/threshold-crossing)."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(..., min_length=1)
    date: date
    key: str
    annotation_type: str
    signal_code: str
    semantic_description: str
    direction: str | None = None
    values: dict[str, float]
    value_bounds: dict[str, TechnicalNumericBounds] = Field(default_factory=dict)
    asset_id: int | None = None


class TechnicalEventBucket(BaseModel):
    """Every selected event assigned to one bucket, verbatim."""

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


class TechnicalEventSelectionSummary(BaseModel):
    """Complete detection/export statistics for one entity + annotation key."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(..., min_length=1)
    annotation_key: str = Field(..., min_length=1)
    detected_count: int = Field(..., ge=1)
    recent_30d_count: int = Field(..., ge=0)
    exported_count: int = Field(..., ge=1)
    selection_applied: bool
    oldest_detected_event_date: date
    newest_detected_event_date: date
    oldest_exported_event_date: date
    newest_exported_event_date: date
    upward_count: int = Field(..., ge=0)
    downward_count: int = Field(..., ge=0)

    @model_validator(mode="after")
    def validate_summary(self) -> TechnicalEventSelectionSummary:
        if self.recent_30d_count > self.detected_count:
            raise ValueError("recent_30d_count cannot exceed detected_count")
        if self.exported_count > self.detected_count:
            raise ValueError("exported_count cannot exceed detected_count")
        if self.selection_applied != (self.exported_count < self.detected_count):
            raise ValueError("selection_applied must reflect whether events were omitted")
        if self.oldest_detected_event_date > self.newest_detected_event_date:
            raise ValueError("detected event date range must be chronological")
        if self.oldest_exported_event_date > self.newest_exported_event_date:
            raise ValueError("exported event date range must be chronological")
        if self.oldest_exported_event_date < self.oldest_detected_event_date or self.newest_exported_event_date > self.newest_detected_event_date:
            raise ValueError("exported event dates must fall inside detected event dates")
        if self.upward_count + self.downward_count > self.detected_count:
            raise ValueError("direction counts cannot exceed detected_count")
        return self


class TechnicalEventsPayload(BaseModel):
    """Selected technical events plus complete per-group detection statistics."""

    model_config = ConfigDict(extra="forbid")

    buckets: tuple[TechnicalEventBucket, ...]
    detected_event_count: int = Field(..., ge=0)
    exported_event_count: int = Field(..., ge=0)
    selection_summaries: tuple[TechnicalEventSelectionSummary, ...]

    @model_validator(mode="after")
    def validate_payload(self) -> TechnicalEventsPayload:
        bucket_total = sum(bucket.event_count for bucket in self.buckets)
        if bucket_total != self.exported_event_count:
            raise ValueError("exported_event_count must match the events assigned to buckets")
        if self.exported_event_count > self.detected_event_count:
            raise ValueError("exported_event_count cannot exceed detected_event_count")
        if sum(summary.detected_count for summary in self.selection_summaries) != self.detected_event_count:
            raise ValueError("selection summaries must reconcile detected_event_count")
        if sum(summary.exported_count for summary in self.selection_summaries) != self.exported_event_count:
            raise ValueError("selection summaries must reconcile exported_event_count")
        keys = [(summary.entity_id, summary.annotation_key) for summary in self.selection_summaries]
        if len(keys) != len(set(keys)):
            raise ValueError("selection summaries must be unique by entity_id and annotation_key")
        return self


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
    covered_asset_count: int = Field(
        ...,
        ge=0,
        description="Eligible assets classified into any state for this (signal_code, output_key). Denominator of unweighted_ratio within this indicator. Unit: assets.",
    )
    covered_portfolio_weight_ratio: float = Field(
        ...,
        description="Sum of gross absolute weight ratios of the assets classified for this indicator. Fraction in [0,1].",
    )
    unweighted_count: int = Field(
        ...,
        ge=0,
        description="Assets currently in THIS state for this indicator. Unit: assets.",
    )
    unweighted_ratio: float = Field(
        ...,
        description="unweighted_count / covered_asset_count for this indicator. Sums to 1 across the indicator's states. Fraction in [0,1].",
    )
    technical_normalized_weight_ratio: float = Field(
        ...,
        description="State weight / covered_portfolio_weight_ratio for this indicator. Sums to 1 across the indicator's states. Fraction in [0,1].",
    )


class UniverseBreadthPayload(BaseModel):
    """`portfolio.technical_breadth` / `broker.technical_breadth`: reconciled coverage + breadth states."""

    model_config = ConfigDict(extra="forbid")

    eligible_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique eligible currently-held (not fully sold, non-zero end value) assets, broker-deduplicated. Unit: assets.",
    )
    period_position_leg_count: int = Field(
        ...,
        ge=0,
        description="Period (broker_id, asset_id) position-contribution legs before eligibility, including legs fully sold inside the period. NOT a unique-asset count. Unit: legs.",
    )
    period_contributor_asset_count: int = Field(
        ...,
        ge=0,
        description="Unique asset IDs across ALL period contribution legs before eligibility (broker-deduplicated, includes fully-sold-in-period assets). Unit: assets.",
    )
    covered_asset_count: int = Field(
        ...,
        ge=0,
        description="Eligible assets with at least one classifiable reference-level indicator value (subset of eligible_asset_count). Unit: assets.",
    )
    eligible_portfolio_weight_ratio: float = Field(
        ...,
        description="Sum of gross absolute open-position weight ratios across all eligible assets. Fraction in [0,1].",
    )
    covered_portfolio_weight_ratio: float = Field(
        ...,
        description="Sum of gross absolute open-position weight ratios across covered assets only. Fraction in [0,1].",
    )
    covered_weight_ratio: float = Field(
        ...,
        description="covered_portfolio_weight_ratio / eligible_portfolio_weight_ratio. Fraction in [0,1].",
    )
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
    "TechnicalNumericBounds",
    "TechnicalRangeValueCell",
    "TechnicalSingleValueCell",
    "UniverseBreadthPayload",
    "UniverseIndicatorsPayload",
]
