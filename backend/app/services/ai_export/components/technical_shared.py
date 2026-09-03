"""Shared runtime helpers for the AI Export "technical wave" (Portfolio/Broker/Asset/FX).

This module owns every piece of logic reused by the four real domain builder
modules (`portfolio_broker_technical.py`, `asset_fx_technical.py`):

- two domain-specific curated indicator/annotation bundles - an exact,
  explicit replica of the legacy `ASSET_FULL_BUNDLE` (20 instances, reused
  unchanged across Asset/Portfolio-per-asset/Broker-per-asset) and
  `FX_FULL_BUNDLE` (12 instances) signal sets and annotation topology,
  reused unchanged across every detail level. Detail changes bucket granularity,
  public non-empty history-row density, and event density, never the Signal set;
- price/rate loading with SignalService-computed warm-up, using
  `AssetSourceManager.get_prices_bulk` (Asset/Portfolio/Broker) or a
  backward-filled `FxRate` range query (FX), normalized into the shared
  `PriceResultsResource`/`FxRateSeriesResource` resource types;
- held-asset-universe resolution for Portfolio/Broker via `PortfolioService.get_report`;
- conversion helpers bridging `SignalResult`/price series into the temporal
  engine's typed points/aggregators, producing the `technical_payloads` models.

Nothing here duplicates indicator math or semantics: every semantic label
(`semantic_id`/`semantic_description`/`category`/output units) is read from
the owning plugin's own `describe_for_ai()`/`output_specs` at call time via
`SignalPluginRegistry`, never re-derived or hardcoded.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from types import MappingProxyType

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.schemas.common import BackwardFillInfo, Currency, DateRangeModel
from backend.app.schemas.portfolio import (
    AssetPeriodContribution,
    PortfolioReportResponse,
)
from backend.app.schemas.prices import FAPriceQueryItem, FAPriceQueryResult
from backend.app.schemas.signals import (
    SignalAnnotationRequest,
    SignalAreaSeries,
    SignalBandComponent,
    SignalBandSeries,
    SignalBandValueSource,
    SignalBarSeries,
    SignalCadence,
    SignalDomain,
    SignalExecutionContext,
    SignalLineCrossoverRequest,
    SignalLineSeries,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalReferenceLevel,
    SignalRequest,
    SignalResult,
    SignalSourceCapability,
    SignalStatus,
    SignalThresholdCrossingRequest,
)
from backend.app.services.ai_export.components.payloads.portfolio_broker import load_portfolio_report
from backend.app.services.ai_export.components.resources import (
    ASSET_PRICE_RESULTS_RESOURCE,
    BROKER_PRICE_RESULTS_RESOURCE,
    BROKER_REPORT_RESOURCE,
    PORTFOLIO_PRICE_RESULTS_RESOURCE,
    PORTFOLIO_REPORT_RESOURCE,
    FxRateObservation,
    FxRateSeriesResource,
    PriceResultsResource,
)
from backend.app.services.ai_export.components.technical_payloads import (
    BreadthStateBucket,
    IndicatorBucketRow,
    IndicatorOutputColumn,
    IndicatorTablePayload,
    PriceBucket,
    TechnicalDatedValue,
    TechnicalEventBucket,
    TechnicalEventPayload,
    TechnicalEventSelectionSummary,
    TechnicalEventsPayload,
    TechnicalIndicatorCell,
    TechnicalNumericBounds,
    TechnicalRangeValueCell,
    TechnicalSingleValueCell,
    UniverseBreadthPayload,
)
from backend.app.services.ai_export.components.types import BuildScope, DetailLevel, ResourceKey, TemporalAggregatorSpec
from backend.app.services.ai_export.dependencies import (
    BuildContext,
    build_indicator_bucket_plan_for_scope,
)
from backend.app.services.ai_export.temporal.aggregators import (
    BandBucketStatistics,
    DatedValue,
    ScalarBucketStatistics,
    aggregate_scalar_statistics,
    aggregate_signal_buckets,
    assign_discrete_events,
)
from backend.app.services.ai_export.temporal.plan import Bucket, BucketPlan
from backend.app.services.ai_export.temporal.points import (
    BandObservedPoint,
    ContinuousMultiOutputPoint,
    DiscreteEvent,
    ObservedPoint,
)
from backend.app.services.ai_export.temporal.policy import (
    BucketDetailLevel,
    EventSelectionPolicy,
    indicator_history_row_limit,
)
from backend.app.services.ai_export.temporal.warmup import slice_to_requested_period
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.fx import convert_bulk
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_service import SignalExecutionPlan, SignalService

# =============================================================================
# Shared temporal aggregator metadata (matches catalog.py's own constant)
# =============================================================================

#: Same `kind`/description as catalog.py's private `_OHLC_BUCKET_AGGREGATOR` -
#: kept as an independent value here since catalog.py is read-only reference
#: for this workstream (not imported), but `TemporalAggregatorSpec` equality is
#: value-based so both builder modules share one canonical constant.
OHLC_BUCKET_AGGREGATOR = TemporalAggregatorSpec(kind="ohlc_bucket", description="Adaptive OHLC bucket aggregation (30/14/7 day cap), owned by the temporal engine workstream")
SIGNAL_PROFILE_BUCKET_AGGREGATOR = TemporalAggregatorSpec(
    kind="signal_profile_bucket",
    description="Plugin-declared signal profile aggregation with dated row cells",
)

_AI_EXPORT_ANNOTATION_ABSOLUTE_EPSILON = 1e-12
_AI_EXPORT_ANNOTATION_RELATIVE_EPSILON = 1e-12
EVENT_SELECTION_MINIMUM_LATEST = 20
EVENT_SELECTION_RECENT_WINDOW_DAYS = 30


# =============================================================================
# Curated indicator/annotation bundles (requirement 1)
# =============================================================================
#
# Two fixed, domain-specific bundles - one for every Asset-like target
# (Asset itself, plus Portfolio/Broker per-asset technical analysis) and one
# for FX - each an exact, explicit replica of the legacy `ASSET_FULL_BUNDLE`/
# `FX_FULL_BUNDLE` signal set and annotation topology (see
# `backend/app/services/ai_export/profiles/{asset,fx}.py`, read-only
# reference; never imported at runtime). The same bundle is requested
# regardless of `BuildScope.detail_level`. Prices use the detail-owned
# `BuildContext.bucket_plan`; each indicator resolves a plugin-owned temporal
# class plus the request detail into its own plan. The signal/annotation set
# itself never changes.
#
# Unlike the legacy profile system, no global max-event `EventLimitSpec`, no
# `SignalOutputMode`/`requested_components` narrowing and no `SignalEligibility`
# marker are replicated here. The central detail-owned event policy preserves a
# complete recent window plus a minimum latest count per entity/annotation:
# `SignalPluginRegistry`'s own `compatible_domains` gating naturally omits
# FX-incompatible plugins (ATR/MFI/OBV are simply absent from the FX bundle
# by construction), and `SignalService`'s own `requires_meaningful_volume`
# check naturally omits MFI/OBV whenever the source's volume isn't
# authoritative - neither is re-implemented here (requirement 7).


@dataclass(frozen=True, slots=True)
class CuratedSignalSpec:
    """One explicitly-curated indicator: a stable ``instance_id`` bound to a plugin code/params."""

    instance_id: str
    signal_code: str
    params: Mapping[str, object] = MappingProxyType({})


#: Exact replica of legacy `ASSET_FULL_BUNDLE`'s 20 signal instances (see
#: `profiles/asset.py` lines 320-437) - reused unchanged for Asset and every
#: Portfolio/Broker per-asset technical section.
ASSET_CURATED_SIGNALS: tuple[CuratedSignalSpec, ...] = (
    CuratedSignalSpec("ema_20", "EMA", MappingProxyType({"period": 20, "offset": 0.0})),
    CuratedSignalSpec("ema_50", "EMA", MappingProxyType({"period": 50, "offset": 0.0})),
    CuratedSignalSpec("ema_200", "EMA", MappingProxyType({"period": 200, "offset": 0.0})),
    CuratedSignalSpec("sma_50", "SMA", MappingProxyType({"period": 50})),
    CuratedSignalSpec("sma_200", "SMA", MappingProxyType({"period": 200})),
    CuratedSignalSpec("kama_20", "KAMA", MappingProxyType({"period": 20})),
    CuratedSignalSpec("aroon_25", "AROON", MappingProxyType({"period": 25})),
    CuratedSignalSpec("adx_14", "ADX", MappingProxyType({"period": 14})),
    CuratedSignalSpec("donchian_20", "DONCHIAN", MappingProxyType({"period": 20})),
    CuratedSignalSpec("rsi_14", "RSI", MappingProxyType({"period": 14, "overbought": 70, "oversold": 30})),
    CuratedSignalSpec("macd_12_26_9", "MACD", MappingProxyType({"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9})),
    CuratedSignalSpec("ppo_12_26_9", "PPO", MappingProxyType({"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9})),
    CuratedSignalSpec("roc_20", "ROC", MappingProxyType({"period": 20})),
    CuratedSignalSpec("stoch_rsi_14_3", "STOCH_RSI", MappingProxyType({"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20})),
    CuratedSignalSpec("cci_20", "CCI", MappingProxyType({"period": 20})),
    CuratedSignalSpec("bollinger_20_2", "BOLLINGER", MappingProxyType({"period": 20, "multiplier": 2.0})),
    CuratedSignalSpec("atr_14", "ATR", MappingProxyType({"period": 14})),
    CuratedSignalSpec("natr_14", "NATR", MappingProxyType({"period": 14})),
    CuratedSignalSpec("mfi_14", "MFI", MappingProxyType({"period": 14, "overbought": 80, "oversold": 20})),
    CuratedSignalSpec("obv", "OBV"),
)

#: Exact replica of legacy `FX_FULL_BUNDLE`'s 12 signal instances (see
#: `profiles/fx.py` lines 233-292) - no ADX/AROON/DONCHIAN/CCI/ATR/NATR/MFI/OBV
#: by design (no volume, no high/low needed for FX conversion series).
FX_CURATED_SIGNALS: tuple[CuratedSignalSpec, ...] = (
    CuratedSignalSpec("ema_20", "EMA", MappingProxyType({"period": 20, "offset": 0.0})),
    CuratedSignalSpec("ema_50", "EMA", MappingProxyType({"period": 50, "offset": 0.0})),
    CuratedSignalSpec("ema_200", "EMA", MappingProxyType({"period": 200, "offset": 0.0})),
    CuratedSignalSpec("sma_50", "SMA", MappingProxyType({"period": 50})),
    CuratedSignalSpec("sma_200", "SMA", MappingProxyType({"period": 200})),
    CuratedSignalSpec("kama_20", "KAMA", MappingProxyType({"period": 20})),
    CuratedSignalSpec("rsi_14", "RSI", MappingProxyType({"period": 14, "overbought": 70, "oversold": 30})),
    CuratedSignalSpec("macd_12_26_9", "MACD", MappingProxyType({"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9})),
    CuratedSignalSpec("ppo_12_26_9", "PPO", MappingProxyType({"fastPeriod": 12, "slowPeriod": 26, "signalPeriod": 9})),
    CuratedSignalSpec("roc_20", "ROC", MappingProxyType({"period": 20})),
    CuratedSignalSpec("stoch_rsi_14_3", "STOCH_RSI", MappingProxyType({"period": 14, "dPeriod": 3, "overbought": 80, "oversold": 20})),
    CuratedSignalSpec("bollinger_20_2", "BOLLINGER", MappingProxyType({"period": 20, "multiplier": 2.0})),
)


def _signal_requests(specs: Sequence[CuratedSignalSpec]) -> tuple[SignalRequest, ...]:
    return tuple(SignalRequest(instance_id=spec.instance_id, signal_code=spec.signal_code, params=dict(spec.params)) for spec in specs)


def build_asset_signal_requests() -> tuple[SignalRequest, ...]:
    """The fixed, explicit Asset-bundle signal requests (Asset and Portfolio/Broker per-asset)."""
    return _signal_requests(ASSET_CURATED_SIGNALS)


def build_fx_signal_requests() -> tuple[SignalRequest, ...]:
    """The fixed, explicit FX-bundle signal requests."""
    return _signal_requests(FX_CURATED_SIGNALS)


def _own_param_value(specs: Sequence[CuratedSignalSpec], instance_id: str, param_key: str) -> float:
    """Reads a threshold value from a curated instance's *own* requested params (RSI/MFI/STOCH_RSI).

    These plugins expose `overbought`/`oversold` as tunable parameters whose
    defaults the curated bundle deliberately keeps at the plugins' own
    declared defaults - reading the value back from the instance's own
    params (rather than hardcoding it a second time) keeps the annotation
    threshold and the actually-computed parameter a single source of truth.
    """
    for spec in specs:
        if spec.instance_id == instance_id:
            return float(spec.params[param_key])
    raise ValueError(f"no curated signal instance {instance_id!r} in bundle")


def _declared_zero_level(signal_code: str, output_key: str) -> float:
    """Reads a plugin's own declared "zero" reference level for one output (ROC/PPO) - never hardcoded."""
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    if plugin_class is None:
        raise ValueError(f"unknown curated plugin signal_code={signal_code!r}")
    output_spec = next((spec for spec in plugin_class.output_specs if spec.key == output_key), None)
    if output_spec is None:
        raise ValueError(f"{signal_code} declares no output {output_key!r}")
    level = next((lvl for lvl in output_spec.default_reference_levels if lvl.key == "zero"), None)
    if level is None:
        raise ValueError(f"{signal_code}.{output_key} declares no 'zero' reference level")
    return level.value


def _line_crossover(key: str, attach_to_instance_id: str, left, right) -> SignalLineCrossoverRequest:
    return SignalLineCrossoverRequest(
        key=key,
        attach_to_instance_id=attach_to_instance_id,
        left=left,
        right=right,
        observed_only=True,
        epsilon=_AI_EXPORT_ANNOTATION_ABSOLUTE_EPSILON,
        relative_epsilon=_AI_EXPORT_ANNOTATION_RELATIVE_EPSILON,
    )


def _threshold_crossing(key: str, attach_to_instance_id: str, source, threshold: float) -> SignalThresholdCrossingRequest:
    return SignalThresholdCrossingRequest(
        key=key,
        attach_to_instance_id=attach_to_instance_id,
        source=source,
        threshold=threshold,
        observed_only=True,
        epsilon=_AI_EXPORT_ANNOTATION_ABSOLUTE_EPSILON,
        relative_epsilon=_AI_EXPORT_ANNOTATION_RELATIVE_EPSILON,
    )


def _price_source() -> SignalPriceValueSource:
    return SignalPriceValueSource(field=SignalPriceField.CLOSE)


def _output_source(instance_id: str, series_key: str) -> SignalOutputValueSource:
    return SignalOutputValueSource(instance_id=instance_id, series_key=series_key)


def _band_source(instance_id: str, series_key: str, component: SignalBandComponent) -> SignalBandValueSource:
    return SignalBandValueSource(instance_id=instance_id, series_key=series_key, component=component)


def build_asset_annotation_requests() -> tuple[SignalAnnotationRequest, ...]:
    """The fixed, explicit Asset-bundle annotation topology - exact replica of legacy `_asset_annotations`.

    Threshold values are read from the plugin's own declared metadata
    wherever available (RSI/MFI/STOCH_RSI's own `overbought`/`oversold`
    params); ADX's trend threshold (25) and MACD's histogram-zero threshold
    (0) have no plugin-declared reference level to source from, so they are
    explicit topology values (allowed per requirement). Events are restricted
    to observed market dates and use a deterministic absolute+relative epsilon.
    No legacy 10/40/120 caps are applied.
    """
    specs = ASSET_CURATED_SIGNALS
    return (
        _line_crossover("price_ema_20", "ema_20", _price_source(), _output_source("ema_20", "ema")),
        _line_crossover("ema_20_ema_50", "ema_20", _output_source("ema_20", "ema"), _output_source("ema_50", "ema")),
        _line_crossover("ema_50_ema_200", "ema_50", _output_source("ema_50", "ema"), _output_source("ema_200", "ema")),
        _threshold_crossing("rsi_14_oversold_30", "rsi_14", _output_source("rsi_14", "rsi"), _own_param_value(specs, "rsi_14", "oversold")),
        _threshold_crossing("rsi_14_overbought_70", "rsi_14", _output_source("rsi_14", "rsi"), _own_param_value(specs, "rsi_14", "overbought")),
        _line_crossover("macd_signal", "macd_12_26_9", _output_source("macd_12_26_9", "macd"), _output_source("macd_12_26_9", "signal")),
        _threshold_crossing("macd_histogram_zero", "macd_12_26_9", _output_source("macd_12_26_9", "histogram"), 0.0),
        _threshold_crossing("mfi_14_oversold_20", "mfi_14", _output_source("mfi_14", "mfi"), _own_param_value(specs, "mfi_14", "oversold")),
        _threshold_crossing("mfi_14_overbought_80", "mfi_14", _output_source("mfi_14", "mfi"), _own_param_value(specs, "mfi_14", "overbought")),
        _line_crossover("price_bollinger_lower", "bollinger_20_2", _price_source(), _band_source("bollinger_20_2", "bands", SignalBandComponent.LOWER)),
        _line_crossover("price_bollinger_middle", "bollinger_20_2", _price_source(), _band_source("bollinger_20_2", "bands", SignalBandComponent.MIDDLE)),
        _line_crossover("price_bollinger_upper", "bollinger_20_2", _price_source(), _band_source("bollinger_20_2", "bands", SignalBandComponent.UPPER)),
        _threshold_crossing("adx_14_trend_25", "adx_14", _output_source("adx_14", "adx"), 25.0),
        _line_crossover("stoch_rsi_k_d", "stoch_rsi_14_3", _output_source("stoch_rsi_14_3", "k"), _output_source("stoch_rsi_14_3", "d")),
        _threshold_crossing("stoch_rsi_k_oversold_20", "stoch_rsi_14_3", _output_source("stoch_rsi_14_3", "k"), _own_param_value(specs, "stoch_rsi_14_3", "oversold")),
        _threshold_crossing("stoch_rsi_k_overbought_80", "stoch_rsi_14_3", _output_source("stoch_rsi_14_3", "k"), _own_param_value(specs, "stoch_rsi_14_3", "overbought")),
        _line_crossover("price_donchian_lower", "donchian_20", _price_source(), _band_source("donchian_20", "channels", SignalBandComponent.LOWER)),
        _line_crossover("price_donchian_middle", "donchian_20", _price_source(), _band_source("donchian_20", "channels", SignalBandComponent.MIDDLE)),
        _line_crossover("price_donchian_upper", "donchian_20", _price_source(), _band_source("donchian_20", "channels", SignalBandComponent.UPPER)),
    )


def build_fx_annotation_requests() -> tuple[SignalAnnotationRequest, ...]:
    """The fixed, explicit FX-bundle annotation topology - exact replica of legacy `_fx_annotations`.

    PPO's own declared "zero" reference level lives on its ``ppo`` output
    (not ``histogram``); its value (0.0) is still sourced from that plugin
    metadata rather than a second hardcoded literal, then attached to the
    ``histogram`` threshold - explicit cross-output topology, generic value.
    ROC's zero level is declared directly on its sole ``roc`` output, so it
    is fully generic. No legacy 10/40/120 caps (requirement 4).
    """
    specs = FX_CURATED_SIGNALS
    return (
        _line_crossover("rate_ema_20", "ema_20", _price_source(), _output_source("ema_20", "ema")),
        _line_crossover("ema_20_ema_50", "ema_20", _output_source("ema_20", "ema"), _output_source("ema_50", "ema")),
        _line_crossover("ema_50_ema_200", "ema_50", _output_source("ema_50", "ema"), _output_source("ema_200", "ema")),
        _threshold_crossing("rsi_14_oversold_30", "rsi_14", _output_source("rsi_14", "rsi"), _own_param_value(specs, "rsi_14", "oversold")),
        _threshold_crossing("rsi_14_overbought_70", "rsi_14", _output_source("rsi_14", "rsi"), _own_param_value(specs, "rsi_14", "overbought")),
        _line_crossover("ppo_signal", "ppo_12_26_9", _output_source("ppo_12_26_9", "ppo"), _output_source("ppo_12_26_9", "signal")),
        _threshold_crossing("ppo_histogram_zero", "ppo_12_26_9", _output_source("ppo_12_26_9", "histogram"), _declared_zero_level("PPO", "ppo")),
        _line_crossover("rate_bollinger_lower", "bollinger_20_2", _price_source(), _band_source("bollinger_20_2", "bands", SignalBandComponent.LOWER)),
        _line_crossover("rate_bollinger_middle", "bollinger_20_2", _price_source(), _band_source("bollinger_20_2", "bands", SignalBandComponent.MIDDLE)),
        _line_crossover("rate_bollinger_upper", "bollinger_20_2", _price_source(), _band_source("bollinger_20_2", "bands", SignalBandComponent.UPPER)),
        _threshold_crossing("roc_20_zero", "roc_20", _output_source("roc_20", "roc"), _declared_zero_level("ROC", "roc")),
        _line_crossover("stoch_rsi_k_d", "stoch_rsi_14_3", _output_source("stoch_rsi_14_3", "k"), _output_source("stoch_rsi_14_3", "d")),
        _threshold_crossing("stoch_rsi_k_oversold_20", "stoch_rsi_14_3", _output_source("stoch_rsi_14_3", "k"), _own_param_value(specs, "stoch_rsi_14_3", "oversold")),
        _threshold_crossing("stoch_rsi_k_overbought_80", "stoch_rsi_14_3", _output_source("stoch_rsi_14_3", "k"), _own_param_value(specs, "stoch_rsi_14_3", "overbought")),
    )


# =============================================================================
# Asset (single target) price + signal loading
# =============================================================================


async def load_asset_price_results(context: BuildContext) -> PriceResultsResource:
    """Loads a homogeneous native-market series plus curated signals.

    Warm-up is computed internally by `AssetSourceManager.get_prices_bulk` from
    the `SignalService` plan, and the returned `result.prices`/signal series are
    already sliced to the requested visible period. Financial valuation uses a
    separate target-currency resource so technical calculations never mix
    native and converted observations.
    """
    scope = context.scope
    assert scope is not None and scope.asset_id is not None

    async def _loader(session: AsyncSession) -> PriceResultsResource:
        item = FAPriceQueryItem(
            asset_id=scope.asset_id,
            date_range=DateRangeModel(start=scope.period_start, end=scope.period_end),
            include_price=True,
            include_events=False,
            target_currency=None,
            signals=list(build_asset_signal_requests()),
            annotation_requests=list(build_asset_annotation_requests()),
        )
        results = await AssetSourceManager.get_prices_bulk([item], session)
        return PriceResultsResource.from_results(results)

    return await context.db_resource(ASSET_PRICE_RESULTS_RESOURCE, _loader)


# =============================================================================
# Portfolio/Broker held-asset universe + bulk price/signal loading
# =============================================================================


async def load_portfolio_or_broker_report(context: BuildContext, *, report_key: ResourceKey[PortfolioReportResponse]) -> PortfolioReportResponse:
    """Loads the `PortfolioReportResponse` backing `PORTFOLIO_REPORT_RESOURCE`/`BROKER_REPORT_RESOURCE`.

    Delegates to the sibling Portfolio/Broker financial workstream's own
    shared `load_portfolio_report` helper (`payloads/portfolio_broker.py`)
    instead of re-implementing a second, differently-scoped loader for the
    same resource key: both workstreams then request the *same*
    `PortfolioReportQuery` shape (summary+history+breakdown+positions
    contribution) under the *same* key, so `BuildContext.db_resource`'s "at
    most once per request" memoization is correctness-safe regardless of
    which sibling component resolves it first (requirement 5) - unlike the
    hand-rolled FX rate series case (see `_FX_TECHNICAL_RATE_SERIES_RESOURCE`),
    reusing the exact same loader here removes the race entirely rather than
    just working around it.
    """
    scope = context.scope
    assert scope is not None
    return await load_portfolio_report(context, scope, report_key)


def eligible_positions(report: PortfolioReportResponse) -> tuple[AssetPeriodContribution, ...]:
    """Currently-held positions at period end: not fully sold and a non-zero end value.

    Analyzes the *complete* eligible universe - no Compact-level asset
    selection (requirement 5).
    """
    contribution = report.positions_contribution
    if contribution is None:
        return ()
    return tuple(position for position in contribution.positions if not position.is_fully_sold and position.end_value is not None and position.end_value != 0)


def period_position_leg_count(report: PortfolioReportResponse) -> int:
    """Count of period ``(broker_id, asset_id)`` position-contribution legs before eligibility.

    One leg per contribution row, so the *same* asset held at two brokers
    counts as two legs, and a leg that was fully sold *inside* the period is
    still counted (it contributed period P&L). This is the raw pre-eligibility
    leg denominator - NOT a unique-asset count (see
    `period_contributor_asset_count`) and NOT the currently-held eligible
    universe (see `eligible_positions`).
    """
    contribution = report.positions_contribution
    return len(contribution.positions) if contribution is not None else 0


def period_contributor_asset_count(report: PortfolioReportResponse) -> int:
    """Count of unique asset IDs across ALL period contribution legs before eligibility.

    Broker-deduplicated over the same raw pre-eligibility legs counted by
    `period_position_leg_count` (so an asset held at two brokers counts once,
    and an asset fully sold inside the period still counts). Always
    ``<= period_position_leg_count`` and ``>= eligible_asset_count``.
    """
    contribution = report.positions_contribution
    if contribution is None:
        return 0
    return len({position.asset_id for position in contribution.positions})


def compute_nav_weights(positions: Sequence[AssetPeriodContribution]) -> Mapping[int, Decimal]:
    """Gross (absolute) NAV weight per asset_id, so leveraged/short positions still weigh in.

    Returns an empty mapping when total gross exposure is zero (e.g. an
    all-cash or genuinely empty eligible universe).
    """
    gross_by_asset: dict[int, Decimal] = {}
    for position in positions:
        if position.end_value is None:
            continue
        gross_by_asset[position.asset_id] = gross_by_asset.get(
            position.asset_id,
            Decimal(0),
        ) + abs(position.end_value)

    total = sum(gross_by_asset.values(), Decimal(0))
    if total <= 0:
        return MappingProxyType({})
    return MappingProxyType({asset_id: gross_value / total for asset_id, gross_value in sorted(gross_by_asset.items())})


@dataclass(frozen=True, slots=True)
class TechnicalUniverseBundle:
    """Held-asset universe + bulk price/signal results for one Portfolio/Broker technical request."""

    positions: tuple[AssetPeriodContribution, ...]
    asset_ids: tuple[int, ...]
    current_position_asset_ids: tuple[int, ...]
    excluded_current_assets: Mapping[int, str]
    current_scope_weights: Mapping[int, Decimal]
    current_unvalued_asset_ids: tuple[int, ...]
    period_position_leg_count: int
    period_contributor_asset_count: int
    weights: Mapping[int, Decimal]
    price_results: PriceResultsResource


async def load_technical_universe_bundle(  # noqa: C901 — thin wrapper; complexity from flat nested _build closure
    context: BuildContext,
    *,
    report_key: ResourceKey[PortfolioReportResponse],
    price_key: ResourceKey[PriceResultsResource],
    bundle_key: ResourceKey[TechnicalUniverseBundle],
) -> TechnicalUniverseBundle:
    """Loads (and memoizes) the full held-asset universe + bulk price/signal bundle.

    `report_key`/`price_key` are the shared, stable resource keys the parent
    Portfolio/Broker financial workstream can also reuse; `bundle_key` is this
    technical wave's own memoized combination of the two, so every one of
    `portfolio.technical_{prices,indicators,breadth,events}` /
    `broker.technical_{prices,indicators,breadth,events}` shares one identical
    universe/price/signal computation per request (requirement 5).
    """
    scope = context.scope
    assert scope is not None

    async def _build() -> TechnicalUniverseBundle:  # noqa: C901 — flat bundle assembly with reason-mapping chain
        report = await load_portfolio_or_broker_report(context, report_key=report_key)
        positions = eligible_positions(report)
        asset_ids = tuple(sorted({position.asset_id for position in positions}))
        current_position_asset_ids = tuple(sorted({holding.asset_id for holding in report.summary.holdings})) if report.summary is not None else ()
        current_values_by_asset: dict[int, Decimal] = {}
        valued_asset_ids: set[int] = set()
        if report.summary is not None:
            for holding in report.summary.holdings:
                if holding.current_value is None:
                    continue
                valued_asset_ids.add(holding.asset_id)
                current_values_by_asset[holding.asset_id] = current_values_by_asset.get(holding.asset_id, Decimal("0")) + abs(holding.current_value)
        current_total = sum(current_values_by_asset.values(), Decimal("0"))
        current_scope_weights = MappingProxyType({asset_id: value / current_total for asset_id, value in sorted(current_values_by_asset.items())}) if current_total > 0 else MappingProxyType({})
        current_unvalued_asset_ids = tuple(sorted(set(current_position_asset_ids) - valued_asset_ids))
        contributions_by_asset: dict[int, list[AssetPeriodContribution]] = {}
        if report.positions_contribution is not None:
            for contribution in report.positions_contribution.positions:
                contributions_by_asset.setdefault(contribution.asset_id, []).append(contribution)
        excluded_current_assets: dict[int, str] = {}
        for asset_id in sorted(set(current_position_asset_ids) - set(asset_ids)):
            contributions = contributions_by_asset.get(asset_id, [])
            if not contributions:
                reason = "no_period_contribution"
            elif all(contribution.is_fully_sold for contribution in contributions):
                reason = "fully_sold_by_period_end"
            elif all(contribution.end_value is None for contribution in contributions):
                reason = "end_value_unavailable"
            elif all(contribution.end_value is None or contribution.end_value == 0 for contribution in contributions):
                reason = "zero_end_value"
            else:
                reason = "technical_eligibility_unavailable"
            excluded_current_assets[asset_id] = reason
        leg_count = period_position_leg_count(report)
        contributor_asset_count = period_contributor_asset_count(report)
        weights = compute_nav_weights(positions)

        async def _price_loader(session: AsyncSession) -> PriceResultsResource:
            if not asset_ids:
                return PriceResultsResource.from_results([])
            signals = list(build_asset_signal_requests())
            annotations = list(build_asset_annotation_requests())
            items = [
                FAPriceQueryItem(
                    asset_id=asset_id,
                    date_range=DateRangeModel(start=scope.period_start, end=scope.period_end),
                    include_price=True,
                    include_events=False,
                    target_currency=None,
                    signals=signals,
                    annotation_requests=annotations,
                )
                for asset_id in asset_ids
            ]
            results = await AssetSourceManager.get_prices_bulk(items, session)
            return PriceResultsResource.from_results(results)

        price_results = await context.db_resource(price_key, _price_loader)
        return TechnicalUniverseBundle(
            positions=positions,
            asset_ids=asset_ids,
            current_position_asset_ids=current_position_asset_ids,
            excluded_current_assets=MappingProxyType(excluded_current_assets),
            current_scope_weights=current_scope_weights,
            current_unvalued_asset_ids=current_unvalued_asset_ids,
            period_position_leg_count=leg_count,
            period_contributor_asset_count=contributor_asset_count,
            weights=weights,
            price_results=price_results,
        )

    return await context.resource(bundle_key, _build)


PORTFOLIO_TECHNICAL_BUNDLE_RESOURCE: ResourceKey[TechnicalUniverseBundle] = ResourceKey("portfolio.technical_bundle", TechnicalUniverseBundle)
BROKER_TECHNICAL_BUNDLE_RESOURCE: ResourceKey[TechnicalUniverseBundle] = ResourceKey("broker.technical_bundle", TechnicalUniverseBundle)

PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS: Mapping[str, ResourceKey] = MappingProxyType(
    {
        "report_key": PORTFOLIO_REPORT_RESOURCE,
        "price_key": PORTFOLIO_PRICE_RESULTS_RESOURCE,
        "bundle_key": PORTFOLIO_TECHNICAL_BUNDLE_RESOURCE,
    }
)
BROKER_TECHNICAL_UNIVERSE_KWARGS: Mapping[str, ResourceKey] = MappingProxyType(
    {
        "report_key": BROKER_REPORT_RESOURCE,
        "price_key": BROKER_PRICE_RESULTS_RESOURCE,
        "bundle_key": BROKER_TECHNICAL_BUNDLE_RESOURCE,
    }
)


# =============================================================================
# FX daily rate series (existing FX service, requirement 6)
# =============================================================================

#: This technical wave's own resource key for the warm-up-inclusive daily
#: base->quote series, deliberately DISTINCT from the sibling FX-core
#: workstream's `FX_RATE_SERIES_RESOURCE` (which is scoped to the visible
#: period only - see `fx_core.py`'s `_load_rate_series`): both loaders share
#: the same `FxRateSeriesResource` *type* and the same underlying
#: `backend.app.services.fx.convert_bulk` source of truth, but a shared
#: request-scoped cache key must always mean the exact same date range to
#: every caller. Reusing the literal `FX_RATE_SERIES_RESOURCE` key here would
#: make correctness depend on which sibling component resolves it first
#: (whichever range is memoized "wins" for every other caller within the
#: request) - a decision this technical wave cannot make unilaterally without
#: risking silently truncating the other workstream's series or vice versa.
_FX_TECHNICAL_RATE_SERIES_RESOURCE: ResourceKey[FxRateSeriesResource] = ResourceKey("fx.technical_rate_series", FxRateSeriesResource)


class FxRateHistoryError(RuntimeError):
    """Typed FX source-history failure surfaced through AI Export problem details."""

    def __init__(self, reason_code: str, message: str) -> None:
        self.reason_code = reason_code
        super().__init__(message)


def _fx_warmup_days(scope: BuildScope) -> int:
    context = SignalExecutionContext(
        domain=SignalDomain.FX,
        requested_range=DateRangeModel(start=scope.period_start, end=scope.period_end),
        cadence=SignalCadence.DAILY,
        source_reference=f"fx:{scope.base_currency}/{scope.quote_currency}",
    )
    plan: SignalExecutionPlan = SignalService().prepare_plan(
        list(build_fx_signal_requests()),
        context,
        list(build_fx_annotation_requests()),
    )
    warmup_days = plan.max_history_points_before_visible
    return min(warmup_days, (scope.period_start - date.min).days)


async def load_fx_rate_series(context: BuildContext) -> FxRateSeriesResource:
    """Loads a daily base->quote conversion rate series over the warm-up + visible range.

    Routed entirely through the existing `backend.app.services.fx.convert_bulk`
    batch conversion service (unlimited backward-fill, no invented economics -
    requirement 6), exactly like the sibling FX-core workstream's own rate
    series loader, just over a wider (warm-up-inclusive) date range and under
    this technical wave's own resource key (see `_FX_TECHNICAL_RATE_SERIES_RESOURCE`).
    """
    scope = context.scope
    assert scope is not None and scope.base_currency is not None and scope.quote_currency is not None

    async def _loader(session: AsyncSession) -> FxRateSeriesResource:
        warmup_days = _fx_warmup_days(scope)
        load_start = scope.period_start - timedelta(days=warmup_days)
        dates = tuple(load_start + timedelta(days=offset) for offset in range((scope.period_end - load_start).days + 1))
        conversions = [(Currency(code=scope.base_currency, amount=Decimal(1)), scope.quote_currency, day) for day in dates]
        results, _errors = await convert_bulk(session, conversions, raise_on_error=False)

        observations: list[FxRateObservation] = []
        source_history_started = False
        for requested_date, result in zip(dates, results, strict=True):
            if result is None:
                if source_history_started:
                    raise FxRateHistoryError(
                        "fx_minimum_payload_unavailable",
                        f"FX source history became unavailable after it had started for {scope.base_currency}->{scope.quote_currency} on {requested_date.isoformat()}",
                    )
                continue
            source_history_started = True
            converted, actual_date, backward_filled = result
            if converted.code != scope.quote_currency or converted.amount <= 0:
                raise FxRateHistoryError(
                    "fx_minimum_payload_unavailable",
                    f"invalid FX conversion result for {scope.base_currency}->{scope.quote_currency} on {requested_date.isoformat()}",
                )
            observations.append(
                FxRateObservation(
                    requested_date=requested_date,
                    actual_date=actual_date,
                    rate=Decimal(str(converted.amount)),
                    backward_filled=bool(backward_filled),
                )
            )
        if not observations or observations[-1].requested_date != scope.period_end:
            raise FxRateHistoryError(
                "fx_no_usable_rate",
                f"no FX rate exists for {scope.base_currency}->{scope.quote_currency} on or before {scope.period_end.isoformat()}",
            )
        return FxRateSeriesResource.from_observations(observations)

    return await context.db_resource(_FX_TECHNICAL_RATE_SERIES_RESOURCE, _loader)


@dataclass(frozen=True, slots=True)
class FxTechnicalBundle:
    """FX rate series + curated signal results for one FX technical request."""

    rate_series: FxRateSeriesResource
    signal_results: tuple[SignalResult, ...]


_FX_TECHNICAL_BUNDLE_RESOURCE: ResourceKey[FxTechnicalBundle] = ResourceKey("fx.technical_bundle", FxTechnicalBundle)


async def load_fx_technical_bundle(context: BuildContext) -> FxTechnicalBundle:
    """Computes the curated signal bundle over the FX rate series (no volume field - requirement 6)."""
    scope = context.scope
    assert scope is not None

    async def _build() -> FxTechnicalBundle:
        rate_series = await load_fx_rate_series(context)
        source_start = rate_series.observations[0].requested_date
        effective_start = max(scope.period_start, source_start)
        price_points = tuple(
            SignalPricePoint(
                date=observation.requested_date,
                close=observation.rate,
                backward_fill_info=(
                    BackwardFillInfo(
                        actual_rate_date=observation.actual_date,
                        days_back=(observation.requested_date - observation.actual_date).days,
                    )
                    if observation.backward_filled or observation.actual_date != observation.requested_date
                    else None
                ),
            )
            for observation in rate_series.observations
        )
        signal_context = SignalExecutionContext(
            domain=SignalDomain.FX,
            requested_range=DateRangeModel(start=effective_start, end=scope.period_end),
            cadence=SignalCadence.DAILY,
            source_reference=f"fx:{scope.base_currency}/{scope.quote_currency}",
        )
        results = await SignalService().compute(
            list(build_fx_signal_requests()),
            price_points,
            signal_context,
            annotation_requests=list(build_fx_annotation_requests()),
            source_capability=SignalSourceCapability(),
        )
        return FxTechnicalBundle(rate_series=rate_series, signal_results=tuple(results))

    return await context.resource(_FX_TECHNICAL_BUNDLE_RESOURCE, _build)


# =============================================================================
# Temporal engine bridging (price/rate OHLC, indicator series, events)
# =============================================================================


def observations_to_rate_points(
    rate_series: FxRateSeriesResource,
    *,
    start: date,
    end: date,
    observed_only: bool = True,
) -> tuple[ContinuousMultiOutputPoint, ...]:
    points = tuple(
        ContinuousMultiOutputPoint(
            date=observation.requested_date,
            values={"rate": observation.rate},
        )
        for observation in rate_series.observations
        if not observed_only or (not observation.backward_filled and observation.actual_date == observation.requested_date)
    )
    return slice_to_requested_period(points, start, end)


def coherent_price_currency(result: FAPriceQueryResult | None) -> str | None:
    """Return the single series currency, or ``None`` for empty/mixed series."""
    if result is None:
        return None
    currencies = {point.currency for point in result.prices if point.currency}
    if len(currencies) != 1:
        return None
    return next(iter(currencies))


def price_result_to_close_points(result: FAPriceQueryResult, *, start: date, end: date) -> tuple[ContinuousMultiOutputPoint, ...]:
    if coherent_price_currency(result) is None:
        return ()
    points = tuple(ContinuousMultiOutputPoint(date=point.date, values={"close": point.close}) for point in result.prices if point.backward_fill_info is None or point.backward_fill_info.days_back == 0)
    return slice_to_requested_period(points, start, end)


def build_price_buckets(points: Sequence[ContinuousMultiOutputPoint], plan: BucketPlan, *, key: str = "close") -> tuple[PriceBucket, ...]:
    """OHLC-bucket a series and compare each close with the previous bucket close."""
    statistics = aggregate_scalar_statistics(
        tuple(ObservedPoint(date=point.date, value=point.values[key]) for point in points),
        plan,
    )
    buckets: list[PriceBucket] = []
    previous_close: DatedValue | None = None
    for statistic in statistics:
        simple_return = None
        return_start_date = None
        if statistic.last is not None and previous_close is not None and previous_close.value != 0:
            simple_return = float(statistic.last.value / previous_close.value - Decimal(1))
            return_start_date = previous_close.observed_date

        buckets.append(
            PriceBucket(
                start_date=statistic.bucket.start_date,
                end_date=statistic.bucket.end_date,
                calendar_days=statistic.bucket.day_count,
                first=({key: float(statistic.first.value)} if statistic.first is not None else None),
                minimum=({key: float(statistic.minimum.value)} if statistic.minimum is not None else None),
                maximum=({key: float(statistic.maximum.value)} if statistic.maximum is not None else None),
                last=({key: float(statistic.last.value)} if statistic.last is not None else None),
                observation_count=statistic.observation_count,
                minimum_date=(statistic.minimum.observed_date if statistic.minimum is not None else None),
                maximum_date=(statistic.maximum.observed_date if statistic.maximum is not None else None),
                return_start_date=return_start_date,
                simple_return=simple_return,
            )
        )
        if statistic.last is not None:
            previous_close = statistic.last
    return tuple(buckets)


def latest_point_value(points: Sequence[ContinuousMultiOutputPoint], *, key: str) -> tuple[float | None, date | None]:
    if not points:
        return None, None
    last = points[-1]
    value = last.values.get(key)
    return (float(value) if value is not None else None), last.date


def _technical_dated_value(value: DatedValue | None) -> TechnicalDatedValue | None:
    if value is None:
        return None
    return TechnicalDatedValue(value=float(value.value), date=value.observed_date)


def _technical_cell(
    statistics: ScalarBucketStatistics,
) -> TechnicalSingleValueCell | TechnicalRangeValueCell | None:
    if statistics.observation_count == 0:
        return None
    if statistics.observation_count == 1:
        assert statistics.last is not None
        return TechnicalSingleValueCell(
            value=float(statistics.last.value),
            date=statistics.last.observed_date,
        )
    assert statistics.first is not None
    assert statistics.minimum is not None
    assert statistics.maximum is not None
    assert statistics.last is not None
    return TechnicalRangeValueCell(
        observation_count=statistics.observation_count,
        first=_technical_dated_value(statistics.first),
        min=_technical_dated_value(statistics.minimum),
        max=_technical_dated_value(statistics.maximum),
        last=_technical_dated_value(statistics.last),
    )


def _bucket_index_by_date(plan: BucketPlan) -> dict[date, int]:
    result: dict[date, int] = {}
    for bucket in plan.buckets:
        current = bucket.start_date
        while current <= bucket.end_date:
            result[current] = bucket.index
            current += timedelta(days=1)
    return result


def _latest_observed_value(points: Sequence[ObservedPoint]) -> TechnicalDatedValue | None:
    if not points:
        return None
    latest = max(points, key=lambda point: point.date)
    return TechnicalDatedValue(value=float(latest.value), date=latest.date)


def _scalar_series_points(
    series: SignalLineSeries | SignalAreaSeries | SignalBarSeries,
) -> tuple[ObservedPoint, ...]:
    return tuple(ObservedPoint(date=point.date, value=Decimal(str(point.value))) for point in series.points if point.value is not None)


def _band_series_points(series: SignalBandSeries) -> tuple[BandObservedPoint, ...]:
    return tuple(
        BandObservedPoint(
            date=point.date,
            lower=(Decimal(str(point.lower)) if point.lower is not None else None),
            middle=(Decimal(str(point.middle)) if point.middle is not None else None),
            upper=(Decimal(str(point.upper)) if point.upper is not None else None),
        )
        for point in series.points
        if any(value is not None for value in (point.lower, point.middle, point.upper))
    )


def build_indicator_table_payloads(  # noqa: C901 — flat payload packing, per-series-type dispatch
    results: Sequence[SignalResult],
    context: BuildContext,
) -> tuple[IndicatorTablePayload, ...]:
    """Build one row-oriented table per available curated signal instance.

    Only `OK`/`PARTIAL` results with at least one series are surfaced.
    Each plugin resolves its own AI Export temporal class from normalized
    parameters. Multi-output signals share one row per class/detail bucket;
    band components become independent lower/middle/upper columns with
    truthful dated stats. Full-period summary/latest values are computed before
    temporal reduction and therefore do not change with detail/class density.
    `UNAVAILABLE`/`FAILED` results are silently omitted (requirement 7,
    "partial success"), never replaced with a placeholder.
    """

    scope = context.scope
    if scope is None:
        raise ValueError("indicator table construction requires BuildContext.scope")
    payloads: list[IndicatorTablePayload] = []
    for result in results:
        if result.status not in (SignalStatus.OK, SignalStatus.PARTIAL) or not result.series:
            continue
        plugin_class = SignalPluginRegistry.get_plugin(result.signal_code)
        if plugin_class is None:
            raise ValueError(f"unknown signal plugin in AI Export result: {result.signal_code}")
        temporal_class = plugin_class.resolve_ai_export_temporal_class(result.normalized_params)
        plan = build_indicator_bucket_plan_for_scope(scope, temporal_class)
        date_to_bucket = _bucket_index_by_date(plan)
        summary_plan = BucketPlan(
            start=plan.start,
            end=plan.end,
            policy=plan.policy,
            buckets=(
                Bucket(
                    index=0,
                    start_date=plan.start,
                    end_date=plan.end,
                ),
            ),
        )
        ai_description = plugin_class.describe_for_ai()
        output_specs = {output.key: output for output in plugin_class.output_specs}
        output_descriptions = {output.key: output for output in ai_description.outputs}
        columns: list[IndicatorOutputColumn] = []
        period_summary: dict[str, TechnicalIndicatorCell | None] = {}
        cells_by_bucket: list[dict[str, object]] = [{} for _bucket in plan.buckets]
        observed_dates_by_bucket: list[set[date]] = [set() for _bucket in plan.buckets]

        for series in result.series:
            output_spec = output_specs.get(series.key)
            output_description = output_descriptions.get(series.key)
            if output_spec is None or output_description is None:
                raise ValueError(f"{result.signal_code}.{series.key} is missing plugin-owned output metadata")
            if isinstance(series, SignalBandSeries):
                points = _band_series_points(series)
                aggregates = aggregate_signal_buckets(
                    output_spec.aggregation_profile,
                    points,
                    plan,
                )
                if any(not isinstance(aggregate, BandBucketStatistics) for aggregate in aggregates):
                    raise TypeError("band aggregation returned a non-band result")
                for point in points:
                    observed_dates_by_bucket[date_to_bucket[point.date]].add(point.date)
                for component in SignalBandComponent:
                    component_points = tuple(
                        ObservedPoint(
                            date=point.date,
                            value=value,
                        )
                        for point in points
                        if (value := getattr(point, component.value)) is not None
                    )
                    column_key = f"{series.key}.{component.value}"
                    columns.append(
                        IndicatorOutputColumn(
                            column_key=column_key,
                            output_key=series.key,
                            component=component,
                            semantic_id=output_description.semantic_id,
                            semantic_description=output_description.semantic_description,
                            unit=output_description.unit.value,
                            kind=series.kind,
                            aggregation_profile=output_spec.aggregation_profile,
                            minimum=output_spec.axis.minimum,
                            maximum=output_spec.axis.maximum,
                            latest=_latest_observed_value(component_points),
                        )
                    )
                    period_summary[column_key] = _technical_cell(
                        aggregate_scalar_statistics(
                            component_points,
                            summary_plan,
                        )[0]
                    )
                    for index, aggregate in enumerate(aggregates):
                        cells_by_bucket[index][column_key] = _technical_cell(getattr(aggregate, component.value))
            elif isinstance(series, (SignalLineSeries, SignalAreaSeries, SignalBarSeries)):
                points = _scalar_series_points(series)
                aggregates = aggregate_signal_buckets(
                    output_spec.aggregation_profile,
                    points,
                    plan,
                )
                if any(not isinstance(aggregate, ScalarBucketStatistics) for aggregate in aggregates):
                    raise TypeError("scalar aggregation returned a non-scalar result")
                for point in points:
                    observed_dates_by_bucket[date_to_bucket[point.date]].add(point.date)
                column_key = series.key
                columns.append(
                    IndicatorOutputColumn(
                        column_key=column_key,
                        output_key=series.key,
                        semantic_id=output_description.semantic_id,
                        semantic_description=output_description.semantic_description,
                        unit=output_description.unit.value,
                        kind=series.kind,
                        aggregation_profile=output_spec.aggregation_profile,
                        minimum=output_spec.axis.minimum,
                        maximum=output_spec.axis.maximum,
                        latest=_latest_observed_value(points),
                    )
                )
                period_summary[column_key] = _technical_cell(aggregate_scalar_statistics(points, summary_plan)[0])
                for index, aggregate in enumerate(aggregates):
                    cells_by_bucket[index][column_key] = _technical_cell(aggregate)
            else:
                raise TypeError(f"unsupported SignalSeries type for AI Export: {type(series).__name__}")

        if not columns:
            continue
        source_rows = tuple(
            IndicatorBucketRow(
                start_date=bucket.start_date,
                end_date=bucket.end_date,
                calendar_days=bucket.day_count,
                observation_count=len(observed_dates_by_bucket[index]),
                cells=cells_by_bucket[index],
            )
            for index, bucket in enumerate(plan.buckets)
        )
        nonempty_rows = tuple(row for row in source_rows if row.observation_count > 0)
        history_limit = indicator_history_row_limit(BucketDetailLevel(scope.detail_level.value))
        rows = _uniform_sample_rows(nonempty_rows, history_limit)
        payloads.append(
            IndicatorTablePayload(
                instance_id=result.instance_id,
                signal_code=result.signal_code,
                temporal_class=temporal_class,
                semantic_id=ai_description.semantic_id,
                semantic_description=ai_description.semantic_description,
                category=ai_description.category.value,
                result_status=result.status,
                partial_reason_code=(result.availability.reason_code.value if result.status == SignalStatus.PARTIAL and result.availability is not None and result.availability.reason_code is not None else None),
                columns=tuple(columns),
                period_summary=period_summary,
                source_bucket_count=len(source_rows),
                source_nonempty_row_count=len(nonempty_rows),
                rows=rows,
            )
        )
        context.register_indicator_sampling(
            signal_instance_id=result.instance_id,
            signal_code=result.signal_code,
            temporal_class=temporal_class,
            bucket_plan=plan,
        )
    return tuple(payloads)


def _uniform_sample_rows(
    rows: Sequence[IndicatorBucketRow],
    limit: int | None,
) -> tuple[IndicatorBucketRow, ...]:
    if limit is None or len(rows) <= limit:
        return tuple(rows)
    indexes = {(2 * index * (len(rows) - 1) + (limit - 1)) // (2 * (limit - 1)) for index in range(limit)}
    return tuple(rows[index] for index in sorted(indexes))


def _annotation_semantic_description(signal_code: str, annotation) -> str:
    plugin_class = SignalPluginRegistry.get_plugin(signal_code)
    base_description = plugin_class.describe_for_ai().semantic_description if plugin_class is not None else signal_code
    return f"{base_description} ({annotation.annotation_type}: {annotation.key})"


def _source_numeric_bounds(
    source: object,
    result_by_instance: Mapping[str, SignalResult],
) -> TechnicalNumericBounds | None:
    if not isinstance(source, Mapping) or source.get("kind") not in {"signal", "band"}:
        return None
    instance_id = source.get("instance_id")
    series_key = source.get("series_key")
    if not isinstance(instance_id, str) or not isinstance(series_key, str):
        return None
    result = result_by_instance.get(instance_id)
    if result is None:
        return None
    plugin_class = SignalPluginRegistry.get_plugin(result.signal_code)
    if plugin_class is None:
        return None
    output_spec = next((spec for spec in plugin_class.output_specs if spec.key == series_key), None)
    if output_spec is None or (output_spec.axis.minimum is None and output_spec.axis.maximum is None):
        return None
    return TechnicalNumericBounds(
        minimum=output_spec.axis.minimum,
        maximum=output_spec.axis.maximum,
    )


def _annotation_value_bounds(
    annotation,
    result_by_instance: Mapping[str, SignalResult],
) -> dict[str, TechnicalNumericBounds]:
    metadata = annotation.metadata
    if annotation.annotation_type == "line_crossover":
        pairs = (("left", metadata.get("left")), ("right", metadata.get("right")))
    elif annotation.annotation_type == "threshold_crossing":
        source = metadata.get("source")
        pairs = (("value", source), ("threshold", source))
    else:
        pairs = ()
    return {key: bounds for key, source in pairs if (bounds := _source_numeric_bounds(source, result_by_instance)) is not None}


def signal_results_to_discrete_events(
    results: Sequence[SignalResult],
    *,
    entity_id: str,
    asset_id: int | None = None,
) -> tuple[DiscreteEvent, ...]:
    """Converts every OK/PARTIAL result's preserved annotations into `DiscreteEvent`s, verbatim.

    Dedup key is ``(entity_id, instance_id, annotation_key, date)`` -
    deterministic and stable across rebuilds of the same request; never
    averages/merges/limits (requirement 4).
    """
    events: list[DiscreteEvent] = []
    result_by_instance = {result.instance_id: result for result in results}
    for result in results:
        if result.status not in (SignalStatus.OK, SignalStatus.PARTIAL):
            continue
        for annotation in result.annotations:
            payload: dict[str, object] = {
                "entity_id": entity_id,
                "key": annotation.key,
                "annotation_type": annotation.annotation_type,
                "signal_code": result.signal_code,
                "semantic_description": _annotation_semantic_description(result.signal_code, annotation),
                "direction": annotation.direction.value if annotation.direction is not None else None,
                "values": {key: float(value) for key, value in annotation.values.items()},
                "value_bounds": {
                    key: bounds.model_dump(mode="json", exclude_none=True)
                    for key, bounds in _annotation_value_bounds(
                        annotation,
                        result_by_instance,
                    ).items()
                },
            }
            if asset_id is not None:
                payload["asset_id"] = asset_id
            dedup_key = (
                entity_id,
                result.instance_id,
                annotation.key,
                annotation.date.isoformat(),
            )
            events.append(DiscreteEvent(date=annotation.date, dedup_key=dedup_key, payload=payload))
    return tuple(events)


@dataclass(frozen=True, slots=True)
class SelectedTechnicalEvents:
    events: tuple[DiscreteEvent, ...]
    summaries: tuple[TechnicalEventSelectionSummary, ...]
    detected_count: int


def select_technical_events(
    events: Sequence[DiscreteEvent],
    *,
    snapshot_as_of: date,
    detail_level: DetailLevel = DetailLevel.FULL,
) -> SelectedTechnicalEvents:
    """Apply the detail-owned complete-recent-window/minimum-latest policy."""
    event_policy = EventSelectionPolicy.for_detail_level(BucketDetailLevel(detail_level.value))
    deduplicated: dict[object, DiscreteEvent] = {}
    for event in events:
        deduplicated.setdefault(event.dedup_key, event)

    grouped: dict[tuple[str, str], list[DiscreteEvent]] = {}
    for event in deduplicated.values():
        if not isinstance(event.payload, Mapping):
            raise TypeError("technical event payload must be a mapping")
        entity_id = event.payload.get("entity_id")
        annotation_key = event.payload.get("key")
        if not isinstance(entity_id, str) or not entity_id:
            raise ValueError("technical event payload requires entity_id")
        if not isinstance(annotation_key, str) or not annotation_key:
            raise ValueError("technical event payload requires annotation key")
        grouped.setdefault((entity_id, annotation_key), []).append(event)

    recent_boundary = snapshot_as_of - timedelta(days=event_policy.complete_recent_window_days)
    selected: list[DiscreteEvent] = []
    summaries: list[TechnicalEventSelectionSummary] = []
    for entity_id, annotation_key in sorted(grouped):
        detected = sorted(
            grouped[(entity_id, annotation_key)],
            key=lambda event: (event.date, repr(event.dedup_key)),
            reverse=True,
        )
        recent_count = sum(event.date >= recent_boundary for event in detected)
        exported_count = min(
            len(detected),
            max(event_policy.minimum_latest_events_per_annotation, recent_count),
        )
        exported = detected[:exported_count]
        selected.extend(exported)
        directions = Counter(event.payload.get("direction") for event in detected if isinstance(event.payload, Mapping))
        summaries.append(
            TechnicalEventSelectionSummary(
                entity_id=entity_id,
                annotation_key=annotation_key,
                detected_count=len(detected),
                recent_window_count=recent_count,
                exported_count=exported_count,
                selection_applied=exported_count < len(detected),
                oldest_detected_event_date=detected[-1].date,
                newest_detected_event_date=detected[0].date,
                oldest_exported_event_date=exported[-1].date,
                newest_exported_event_date=exported[0].date,
                upward_count=directions["up"],
                downward_count=directions["down"],
            )
        )

    selected.sort(
        key=lambda event: (
            event.date,
            str(event.payload.get("entity_id")),
            str(event.payload.get("key")),
            repr(event.dedup_key),
        )
    )
    return SelectedTechnicalEvents(
        events=tuple(selected),
        summaries=tuple(summaries),
        detected_count=len(deduplicated),
    )


def build_events_payload(
    events: Sequence[DiscreteEvent],
    context: BuildContext,
) -> TechnicalEventsPayload:
    plan = context.bucket_plan
    if plan is None:
        raise ValueError("event payload construction requires bucket_plan")
    selection = select_technical_events(
        events,
        snapshot_as_of=plan.end,
        detail_level=context.scope.detail_level if context.scope is not None else DetailLevel.FULL,
    )
    assignments = assign_discrete_events(selection.events, plan)
    buckets: list[TechnicalEventBucket] = []
    exported_total = 0
    for assignment in assignments:
        event_payloads = tuple(TechnicalEventPayload(date=event.date, **event.payload) for event in assignment.events)
        buckets.append(
            TechnicalEventBucket(
                start_date=assignment.bucket.start_date,
                end_date=assignment.bucket.end_date,
                calendar_days=assignment.bucket.day_count,
                events=event_payloads,
                event_count=assignment.event_count,
            )
        )
        exported_total += assignment.event_count
    context.register_event_selection()
    return TechnicalEventsPayload(
        buckets=tuple(buckets),
        detected_event_count=selection.detected_count,
        exported_event_count=exported_total,
        selection_summaries=selection.summaries,
    )


# Absolute tolerance for "value == reference level" comparisons. Signal series
# values reaching this classifier have already been rounded/quantized by the
# owning plugin's own computation (Decimal-derived, converted to float once at
# the very output boundary), so residual floating-point noise is far below
# this bound; it exists only to guard against that noise, never to widen a
# plugin-declared threshold.
_REFERENCE_LEVEL_EQUALITY_TOLERANCE = 1e-9


def classify_reference_level_state(value: float, levels: Sequence[SignalReferenceLevel]) -> str | None:
    """Classifies `value` against the plugin's own declared reference level(s).

    - Degenerate single-level case (e.g. ROC/PPO/AROON-oscillator's "zero"):
      every value is informative relative to that one level - never collapsed
      to a single constant state. Returns ``below_<key>`` / ``at_<key>`` /
      ``above_<key>`` (equality within a tiny float tolerance, see
      `_REFERENCE_LEVEL_EQUALITY_TOLERANCE`).
    - 2+-level case (e.g. RSI/MFI/STOCH_RSI oversold/overbought): preserves the
      existing region behavior - below the lowest level / above the highest /
      "neutral" between.

    Uses only the plugin's own declared reference levels (labels + values) -
    never a hardcoded threshold.
    """
    if not levels:
        return None
    if len(levels) == 1:
        level = levels[0]
        if math.isclose(value, level.value, rel_tol=0.0, abs_tol=_REFERENCE_LEVEL_EQUALITY_TOLERANCE):
            return f"at_{level.key}"
        return f"below_{level.key}" if value < level.value else f"above_{level.key}"
    ordered = sorted(levels, key=lambda level: level.value)
    lowest, highest = ordered[0], ordered[-1]
    if value <= lowest.value:
        return lowest.key
    if value >= highest.value:
        return highest.key
    return "neutral"


def build_breadth_payload(universe: TechnicalUniverseBundle) -> UniverseBreadthPayload:  # noqa: C901 — guard-clause classification pipeline + rollup packing
    """`portfolio.technical_breadth` / `broker.technical_breadth`: reconciled weighted/unweighted breadth.

    Analyzes every `ASSET_CURATED_SIGNALS` plugin output that declares
    reference levels (e.g. RSI/MFI/STOCH_RSI's oversold/overbought, ROC's
    zero - discovered generically from `output_spec.default_reference_levels`,
    never hardcoded) over the *complete* eligible universe (requirement 5).
    For each such (signal_code, output_key), each eligible asset's *latest*
    value is classified via `classify_reference_level_state`;
    `unweighted_ratio`/`technical_normalized_weight_ratio` are relative to the
    assets for which that particular indicator actually produced a classifiable
    value (so the ratios for one indicator's states always reconcile to 1.0), and
    `covered_asset_count` (top-level) is the number of eligible assets with
    at least one classifiable indicator value. MFI naturally drops out of an
    all-MANUAL/mixed-volume universe via `SignalService`'s own
    volume-capability gating - no manual gating here.
    """
    eligible_asset_count = len(universe.asset_ids)
    leg_count = universe.period_position_leg_count
    contributor_asset_count = universe.period_contributor_asset_count
    eligible_portfolio_weight = float(sum(universe.weights.values(), Decimal(0)))

    # (signal_code, output_key) -> {asset_id: (state, weight)}
    classifications: dict[tuple[str, str], dict[int, tuple[str, float]]] = {}
    covered_asset_ids: set[int] = set()

    for asset_id in universe.asset_ids:
        result_by_asset = universe.price_results.by_asset_id.get(asset_id)
        if result_by_asset is None:
            continue
        weight = float(universe.weights.get(asset_id, Decimal(0)))
        signals_by_instance = {result.instance_id: result for result in result_by_asset.signals}
        for spec in ASSET_CURATED_SIGNALS:
            result = signals_by_instance.get(spec.instance_id)
            if result is None or result.status not in (SignalStatus.OK, SignalStatus.PARTIAL):
                continue
            plugin_class = SignalPluginRegistry.get_plugin(spec.signal_code)
            if plugin_class is None:
                continue
            for output_spec in plugin_class.output_specs:
                if not output_spec.supports_reference_levels or not output_spec.default_reference_levels:
                    continue
                series = next((series for series in result.series if series.key == output_spec.key), None)
                if series is None or not series.points:
                    continue
                latest_value = series.points[-1].value
                if latest_value is None:
                    continue
                state = classify_reference_level_state(float(latest_value), output_spec.default_reference_levels)
                if state is None:
                    continue
                bucket_key = (spec.signal_code, output_spec.key)
                classifications.setdefault(bucket_key, {})[asset_id] = (state, weight)
                covered_asset_ids.add(asset_id)

    states: list[BreadthStateBucket] = []
    for signal_code, output_key in sorted(classifications):
        by_asset = classifications[(signal_code, output_key)]
        covered_count = len(by_asset)
        covered_weight = sum(weight for _state, weight in by_asset.values())
        state_counts: dict[str, int] = {}
        state_weights: dict[str, float] = {}
        for _asset_id, (state, weight) in by_asset.items():
            state_counts[state] = state_counts.get(state, 0) + 1
            state_weights[state] = state_weights.get(state, 0.0) + weight
        for state in sorted(state_counts):
            unweighted_count = state_counts[state]
            unweighted_ratio = (unweighted_count / covered_count) if covered_count else 0.0
            weighted_ratio = (state_weights[state] / covered_weight) if covered_weight else 0.0
            states.append(
                BreadthStateBucket(
                    signal_code=signal_code,
                    output_key=output_key,
                    state=state,
                    covered_asset_count=covered_count,
                    covered_portfolio_weight_ratio=covered_weight,
                    unweighted_count=unweighted_count,
                    unweighted_ratio=unweighted_ratio,
                    technical_normalized_weight_ratio=weighted_ratio,
                )
            )

    covered_portfolio_weight = float(
        sum(
            (universe.weights.get(asset_id, Decimal(0)) for asset_id in covered_asset_ids),
            Decimal(0),
        )
    )
    return UniverseBreadthPayload(
        eligible_asset_count=eligible_asset_count,
        period_position_leg_count=leg_count,
        period_contributor_asset_count=contributor_asset_count,
        covered_asset_count=len(covered_asset_ids),
        eligible_portfolio_weight_ratio=eligible_portfolio_weight,
        covered_portfolio_weight_ratio=covered_portfolio_weight,
        covered_weight_ratio=(covered_portfolio_weight / eligible_portfolio_weight if eligible_portfolio_weight else 0.0),
        states=tuple(states),
    )


__all__ = [
    "ASSET_CURATED_SIGNALS",
    "BROKER_TECHNICAL_BUNDLE_RESOURCE",
    "BROKER_TECHNICAL_UNIVERSE_KWARGS",
    "CuratedSignalSpec",
    "EVENT_SELECTION_MINIMUM_LATEST",
    "EVENT_SELECTION_RECENT_WINDOW_DAYS",
    "FX_CURATED_SIGNALS",
    "FxRateHistoryError",
    "FxTechnicalBundle",
    "OHLC_BUCKET_AGGREGATOR",
    "SIGNAL_PROFILE_BUCKET_AGGREGATOR",
    "SelectedTechnicalEvents",
    "PORTFOLIO_TECHNICAL_BUNDLE_RESOURCE",
    "PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS",
    "TechnicalUniverseBundle",
    "build_asset_annotation_requests",
    "build_asset_signal_requests",
    "build_breadth_payload",
    "build_events_payload",
    "build_fx_annotation_requests",
    "build_fx_signal_requests",
    "build_indicator_table_payloads",
    "build_price_buckets",
    "classify_reference_level_state",
    "compute_nav_weights",
    "eligible_positions",
    "latest_point_value",
    "load_asset_price_results",
    "load_fx_rate_series",
    "load_fx_technical_bundle",
    "load_portfolio_or_broker_report",
    "load_technical_universe_bundle",
    "observations_to_rate_points",
    "period_contributor_asset_count",
    "period_position_leg_count",
    "price_result_to_close_points",
    "select_technical_events",
    "signal_results_to_discrete_events",
]
