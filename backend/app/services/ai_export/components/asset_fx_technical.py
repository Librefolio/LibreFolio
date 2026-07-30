"""Real `ComponentSpec` implementations for the Asset/FX technical wave.

Owns exactly the seven `asset.{ohlc_returns,indicators,states_events}` /
`fx.{rate_ohlc,returns_volatility,indicators,states_events}` component IDs
(matching the placeholders declared verbatim in `backend.app.services.
ai_export.components.catalog`, so a future catalog wiring can swap the
placeholder builders for these without touching any `component_id`/`domains`/
`dependencies` metadata).

- Asset builders load the single `BuildScope.asset_id` target's prices +
  curated signals once (`technical_shared.load_asset_price_results`, backed
  by `AssetSourceManager.get_prices_bulk`) and reuse the same
  `ASSET_PRICE_RESULTS_RESOURCE` cache entry across all three components.
- FX builders load the daily base->quote rate series once
  (`technical_shared.load_fx_rate_series`, routed through the existing
  `backend.app.services.fx.convert_bulk` service - no invented economics) and
  the curated signal bundle computed over it once
  (`technical_shared.load_fx_technical_bundle`), reused across all four
  components.
- `fx.returns_volatility` is the one series this technical wave computes
  itself (day-over-day pct change of the rate series): no signal plugin
  covers FX returns/volatility, so this module derives it directly from the
  already-loaded rate series - never inventing a rate, only a period-over-
  period ratio of already-authoritative rates.

This module is intentionally NOT wired into `backend.app.services.ai_export.
components.catalog` (that file is owned by the parent integration step) -
see the plan's Phase 0 AI Export refinement, "shared technical wave" section.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal
from statistics import pstdev

from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.resources import FxRateSeriesResource
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_payloads import (
    AssetOhlcReturnsPayload,
    FxRateOhlcPayload,
    FxReturnsVolatilityPayload,
    ReturnVolatilityBucket,
    SingleTargetIndicatorsPayload,
    TechnicalEventsPayload,
)
from backend.app.services.ai_export.components.technical_shared import (
    OHLC_BUCKET_AGGREGATOR,
    SIGNAL_PROFILE_BUCKET_AGGREGATOR,
    build_events_payload,
    build_indicator_table_payloads,
    build_price_buckets,
    coherent_price_currency,
    latest_point_value,
    load_asset_price_results,
    load_fx_rate_series,
    load_fx_technical_bundle,
    observations_to_rate_points,
    price_result_to_close_points,
    signal_results_to_discrete_events,
)
from backend.app.services.ai_export.components.types import Domain, PeriodBehavior
from backend.app.services.ai_export.dependencies import BuildContext
from backend.app.services.ai_export.temporal.aggregators import aggregate_continuous_multi_output
from backend.app.services.ai_export.temporal.plan import BucketPlan
from backend.app.services.ai_export.temporal.points import ContinuousMultiOutputPoint
from backend.app.services.ai_export.temporal.warmup import slice_to_requested_period

# =============================================================================
# asset.ohlc_returns
# =============================================================================


async def _build_asset_ohlc_returns(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> AssetOhlcReturnsPayload:
    scope = context.scope
    assert scope is not None and scope.asset_id is not None
    price_results = await load_asset_price_results(context)
    result = price_results.by_asset_id.get(scope.asset_id)

    points = (
        price_result_to_close_points(
            result,
            start=scope.period_start,
            end=scope.period_end,
        )
        if result is not None
        else ()
    )
    buckets = build_price_buckets(points, context.bucket_plan, key="close")
    latest_close, latest_date = latest_point_value(points, key="close")
    currency = coherent_price_currency(result)

    return AssetOhlcReturnsPayload(
        asset_id=scope.asset_id,
        currency=currency,
        buckets=buckets,
        latest_close=latest_close,
        latest_date=latest_date,
    )


ASSET_OHLC_RETURNS_SPEC = ComponentSpec(
    component_id="asset.ohlc_returns",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=AssetOhlcReturnsPayload,
    builder=_build_asset_ohlc_returns,
    dependencies=("asset.identity",),
    period_behavior=PeriodBehavior.AGGREGATED,
    aggregator=OHLC_BUCKET_AGGREGATOR,
)


# =============================================================================
# asset.indicators
# =============================================================================


async def _build_asset_indicators(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> SingleTargetIndicatorsPayload:
    scope = context.scope
    assert scope is not None and scope.asset_id is not None
    price_results = await load_asset_price_results(context)
    result = price_results.by_asset_id.get(scope.asset_id)
    signals = result.signals if result is not None else ()
    indicators = build_indicator_table_payloads(signals, context.bucket_plan)
    return SingleTargetIndicatorsPayload(indicators=indicators)


ASSET_INDICATORS_SPEC = ComponentSpec(
    component_id="asset.indicators",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=SingleTargetIndicatorsPayload,
    builder=_build_asset_indicators,
    dependencies=("asset.ohlc_returns",),
    period_behavior=PeriodBehavior.AGGREGATED,
    aggregator=SIGNAL_PROFILE_BUCKET_AGGREGATOR,
)


# =============================================================================
# asset.states_events
# =============================================================================


async def _build_asset_states_events(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalEventsPayload:
    scope = context.scope
    assert scope is not None and scope.asset_id is not None
    price_results = await load_asset_price_results(context)
    result = price_results.by_asset_id.get(scope.asset_id)
    signals = result.signals if result is not None else ()
    events = signal_results_to_discrete_events(signals)
    return build_events_payload(events, context.bucket_plan)


ASSET_STATES_EVENTS_SPEC = ComponentSpec(
    component_id="asset.states_events",
    version=1,
    domains=frozenset({Domain.ASSET}),
    output_model=TechnicalEventsPayload,
    builder=_build_asset_states_events,
    dependencies=("asset.indicators",),
    period_behavior=PeriodBehavior.WINDOWED,
)


# =============================================================================
# fx.rate_ohlc
# =============================================================================


async def _build_fx_rate_ohlc(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxRateOhlcPayload:
    scope = context.scope
    assert scope is not None and scope.base_currency is not None and scope.quote_currency is not None
    rate_series = await load_fx_rate_series(context)
    points = observations_to_rate_points(rate_series, start=scope.period_start, end=scope.period_end)
    buckets = build_price_buckets(points, context.bucket_plan, key="rate")
    latest_rate, latest_date = latest_point_value(points, key="rate")

    return FxRateOhlcPayload(
        base_currency=scope.base_currency,
        quote_currency=scope.quote_currency,
        buckets=buckets,
        latest_rate=latest_rate,
        latest_date=latest_date,
    )


FX_RATE_OHLC_SPEC = ComponentSpec(
    component_id="fx.rate_ohlc",
    version=1,
    domains=frozenset({Domain.FX}),
    output_model=FxRateOhlcPayload,
    builder=_build_fx_rate_ohlc,
    dependencies=("fx.pair_identity",),
    period_behavior=PeriodBehavior.AGGREGATED,
    aggregator=OHLC_BUCKET_AGGREGATOR,
)


# =============================================================================
# fx.returns_volatility
# =============================================================================


def _daily_return_points(rate_series: FxRateSeriesResource, *, start, end) -> tuple[ContinuousMultiOutputPoint, ...]:
    """Return changes between genuine FX observations, excluding carry-forward."""
    observations = tuple(observation for observation in rate_series.observations if (not observation.backward_filled and observation.actual_date == observation.requested_date))
    points: list[ContinuousMultiOutputPoint] = []
    for previous, current in zip(observations, observations[1:], strict=False):
        if previous.rate == 0:
            continue
        pct_change = current.rate / previous.rate - Decimal(1)
        points.append(ContinuousMultiOutputPoint(date=current.requested_date, values={"return": pct_change}))
    return slice_to_requested_period(tuple(points), start, end)


def _build_return_volatility_buckets(points: Sequence[ContinuousMultiOutputPoint], plan: BucketPlan) -> tuple[ReturnVolatilityBucket, ...]:
    aggregates = aggregate_continuous_multi_output(points, plan)
    buckets: list[ReturnVolatilityBucket] = []
    for aggregate in aggregates:
        bucket_returns = [float(point.values["return"]) for point in points if aggregate.bucket.contains(point.date)]
        volatility = pstdev(bucket_returns) if len(bucket_returns) >= 2 else None
        buckets.append(
            ReturnVolatilityBucket(
                start_date=aggregate.bucket.start_date,
                end_date=aggregate.bucket.end_date,
                calendar_days=aggregate.bucket.day_count,
                first={key: float(value) for key, value in aggregate.first.items()} if aggregate.first else None,
                minimum={key: float(value) for key, value in aggregate.minimum.items()} if aggregate.minimum else None,
                maximum={key: float(value) for key, value in aggregate.maximum.items()} if aggregate.maximum else None,
                last={key: float(value) for key, value in aggregate.last.items()} if aggregate.last else None,
                observation_count=aggregate.observation_count,
                volatility=volatility,
            )
        )
    return tuple(buckets)


async def _build_fx_returns_volatility(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FxReturnsVolatilityPayload:
    scope = context.scope
    assert scope is not None and scope.base_currency is not None and scope.quote_currency is not None
    rate_series = await load_fx_rate_series(context)
    points = _daily_return_points(rate_series, start=scope.period_start, end=scope.period_end)
    buckets = _build_return_volatility_buckets(points, context.bucket_plan)

    return FxReturnsVolatilityPayload(
        base_currency=scope.base_currency,
        quote_currency=scope.quote_currency,
        buckets=buckets,
    )


FX_RETURNS_VOLATILITY_SPEC = ComponentSpec(
    component_id="fx.returns_volatility",
    version=1,
    domains=frozenset({Domain.FX}),
    output_model=FxReturnsVolatilityPayload,
    builder=_build_fx_returns_volatility,
    dependencies=("fx.rate_ohlc",),
    period_behavior=PeriodBehavior.WINDOWED,
)


# =============================================================================
# fx.indicators
# =============================================================================


async def _build_fx_indicators(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> SingleTargetIndicatorsPayload:
    bundle = await load_fx_technical_bundle(context)
    indicators = build_indicator_table_payloads(bundle.signal_results, context.bucket_plan)
    return SingleTargetIndicatorsPayload(indicators=indicators)


FX_INDICATORS_SPEC = ComponentSpec(
    component_id="fx.indicators",
    version=1,
    domains=frozenset({Domain.FX}),
    output_model=SingleTargetIndicatorsPayload,
    builder=_build_fx_indicators,
    dependencies=("fx.rate_ohlc",),
    period_behavior=PeriodBehavior.AGGREGATED,
    aggregator=SIGNAL_PROFILE_BUCKET_AGGREGATOR,
)


# =============================================================================
# fx.states_events
# =============================================================================


async def _build_fx_states_events(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalEventsPayload:
    bundle = await load_fx_technical_bundle(context)
    events = signal_results_to_discrete_events(bundle.signal_results)
    return build_events_payload(events, context.bucket_plan)


FX_STATES_EVENTS_SPEC = ComponentSpec(
    component_id="fx.states_events",
    version=1,
    domains=frozenset({Domain.FX}),
    output_model=TechnicalEventsPayload,
    builder=_build_fx_states_events,
    dependencies=("fx.indicators",),
    period_behavior=PeriodBehavior.WINDOWED,
)


ASSET_FX_TECHNICAL_COMPONENTS: tuple[ComponentSpec, ...] = (
    ASSET_OHLC_RETURNS_SPEC,
    ASSET_INDICATORS_SPEC,
    ASSET_STATES_EVENTS_SPEC,
    FX_RATE_OHLC_SPEC,
    FX_RETURNS_VOLATILITY_SPEC,
    FX_INDICATORS_SPEC,
    FX_STATES_EVENTS_SPEC,
)


__all__ = [
    "ASSET_FX_TECHNICAL_COMPONENTS",
    "ASSET_INDICATORS_SPEC",
    "ASSET_OHLC_RETURNS_SPEC",
    "ASSET_STATES_EVENTS_SPEC",
    "FX_INDICATORS_SPEC",
    "FX_RATE_OHLC_SPEC",
    "FX_RETURNS_VOLATILITY_SPEC",
    "FX_STATES_EVENTS_SPEC",
]
