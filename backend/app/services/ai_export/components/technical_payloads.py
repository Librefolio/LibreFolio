"""Shared, JSON-safe Pydantic payload models for the AI Export technical wave.

Every model here backs one or more of the real `portfolio.technical_*`,
`broker.technical_*`, `asset.{ohlc_returns,indicators,states_events}` and
`fx.{rate_ohlc,returns_volatility,indicators,states_events}` `ComponentSpec`
builders (see `technical_shared.py`, `portfolio_broker_technical.py` and
`asset_fx_technical.py`). All models are ``extra="forbid"`` and JSON-safe
(floats/dates/strings only - no ``Decimal``), and every tuple field is
deterministically ordered by its producing builder (never re-sorted here).

Design notes:
- Every continuous series (price/rate OHLC, indicator lines, indicator bands,
  FX returns) is represented uniformly as `TechnicalBucket` (or a thin
  subclass adding one extra derived field): first/minimum/maximum/last are
  each a mapping of named numeric outputs (a single ``"value"``-shaped key
  for a scalar line, ``"lower"``/``"middle"``/``"upper"`` for a band, ...),
  produced by `temporal.aggregators.aggregate_continuous_multi_output`. This
  keeps one bucket shape for every "OHLC-style" series in the technical wave.
- Discrete events/state-changes are never bucket-aggregated numerically: they
  are assigned to buckets verbatim via `temporal.aggregators.assign_discrete_events`
  (dedup, never averaged/truncated/capped) and exposed as `TechnicalEventBucket`.
- Detail level (Compact/Standard/Full) only changes bucket *counts* (via the
  `BuildContext.bucket_plan`), never the emitted signal/entity/event set - see
  the module-level requirement in the refinement plan/todo.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class TechnicalBucket(BaseModel):
    """One OHLC-style bucket for a continuous (single- or multi-output) series.

    Empty buckets are explicit: ``first``/``minimum``/``maximum``/``last`` are
    all ``None`` and ``observation_count == 0`` (never synthesized/carried
    forward - see `temporal.aggregators.aggregate_continuous_multi_output`).
    """

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    first: dict[str, float] | None = None
    minimum: dict[str, float] | None = None
    maximum: dict[str, float] | None = None
    last: dict[str, float] | None = None
    observation_count: int


class PriceBucket(TechnicalBucket):
    """A price/rate OHLC bucket (``"close"``/``"rate"`` key) plus its bucket-local simple return."""

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


class IndicatorSeriesPayload(BaseModel):
    """One plugin-computed indicator output series, OHLC-bucketed, with its own latest state.

    ``semantic_id``/``semantic_description``/``category``/``unit`` are copied
    verbatim from the owning plugin's `describe_for_ai()` (never re-derived or
    duplicated here) so AI Export never re-implements indicator semantics.
    """

    model_config = ConfigDict(extra="forbid")

    instance_id: str
    signal_code: str
    semantic_id: str
    semantic_description: str
    category: str
    output_key: str
    unit: str
    kind: str
    buckets: tuple[TechnicalBucket, ...]
    latest: dict[str, float] | None = None
    latest_date: date | None = None


class AssetIndicatorsPayload(BaseModel):
    """One held asset's full curated indicator bundle (Portfolio/Broker universe)."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    weight: float | None = None
    indicators: tuple[IndicatorSeriesPayload, ...]


class UniverseIndicatorsPayload(BaseModel):
    """`portfolio.technical_indicators` / `broker.technical_indicators`: per-asset indicators, full universe."""

    model_config = ConfigDict(extra="forbid")

    assets: tuple[AssetIndicatorsPayload, ...]
    eligible_asset_count: int
    considered_asset_count: int


class SingleTargetIndicatorsPayload(BaseModel):
    """`asset.indicators` / `fx.indicators`: the curated indicator bundle for one target."""

    model_config = ConfigDict(extra="forbid")

    indicators: tuple[IndicatorSeriesPayload, ...]


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
    events: tuple[TechnicalEventPayload, ...] = ()
    event_count: int


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
    "IndicatorSeriesPayload",
    "PortfolioTechnicalPricesPayload",
    "PriceBucket",
    "ReturnVolatilityBucket",
    "SingleTargetIndicatorsPayload",
    "TechnicalBucket",
    "TechnicalEventBucket",
    "TechnicalEventPayload",
    "TechnicalEventsPayload",
    "UniverseBreadthPayload",
    "UniverseIndicatorsPayload",
]
