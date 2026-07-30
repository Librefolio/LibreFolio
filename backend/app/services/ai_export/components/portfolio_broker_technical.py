"""Real `ComponentSpec` implementations for the Portfolio/Broker technical wave.

Owns exactly the seven `portfolio.technical_*`/`broker.technical_*` component
IDs (matching the placeholders declared verbatim in `backend.app.services.
ai_export.components.catalog`, so a future catalog wiring can swap the
placeholder builders for these without touching any `component_id`/`domains`/
`dependencies` metadata):

- `portfolio.technical_prices` / (no Broker equivalent - Broker starts at
  `technical_indicators`, per the frozen catalog wiring).
- `portfolio.technical_indicators` / `broker.technical_indicators`.
- `portfolio.technical_breadth` / `broker.technical_breadth`.
- `portfolio.technical_events` / `broker.technical_events`.

Every builder analyzes the *complete* eligible held-asset universe (no
Compact-level asset selection - requirement 5): eligibility, NAV weights, and
the shared bulk price/signal loading are all delegated to
`technical_shared.load_technical_universe_bundle`, which itself reuses the
`PORTFOLIO_REPORT_RESOURCE`/`BROKER_REPORT_RESOURCE` resource cache entries
also used by the sibling Portfolio/Broker *financial* wave (via
`payloads/portfolio_broker.load_portfolio_report`), so the underlying
`PortfolioService.get_report` call only ever happens once per request
regardless of how many components (financial or technical) need it.

This module is intentionally NOT wired into `backend.app.services.ai_export.
components.catalog` (that file is owned by the parent integration step) -
see the plan's Phase 0 AI Export refinement, "shared technical wave" section.
"""

from __future__ import annotations

from collections.abc import Mapping

from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.technical_payloads import (
    AssetIndicatorsPayload,
    AssetPriceSeriesPayload,
    PortfolioTechnicalPricesPayload,
    TechnicalEventsPayload,
    UniverseBreadthPayload,
    UniverseIndicatorsPayload,
)
from backend.app.services.ai_export.components.technical_shared import (
    BROKER_TECHNICAL_UNIVERSE_KWARGS,
    OHLC_BUCKET_AGGREGATOR,
    PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS,
    SIGNAL_PROFILE_BUCKET_AGGREGATOR,
    TechnicalUniverseBundle,
    build_breadth_payload,
    build_events_payload,
    build_indicator_table_payloads,
    build_price_buckets,
    latest_point_value,
    load_technical_universe_bundle,
    price_result_to_close_points,
    signal_results_to_discrete_events,
)
from backend.app.services.ai_export.components.types import Domain, PeriodBehavior
from backend.app.services.ai_export.dependencies import BuildContext

# =============================================================================
# portfolio.technical_prices (Portfolio only - no Broker equivalent)
# =============================================================================


async def _build_portfolio_technical_prices(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioTechnicalPricesPayload:
    scope = context.scope
    assert scope is not None
    universe: TechnicalUniverseBundle = await load_technical_universe_bundle(context, **PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS)

    assets: list[AssetPriceSeriesPayload] = []
    for position in universe.positions:
        result = universe.price_results.by_asset_id.get(position.asset_id)
        if result is None:
            continue
        points = price_result_to_close_points(result, start=scope.period_start, end=scope.period_end)
        buckets = build_price_buckets(points, context.bucket_plan, key="close")
        latest_close, latest_date = latest_point_value(points, key="close")
        currency = result.prices[0].currency if result.prices and result.prices[0].currency else scope.target_currency
        weight = universe.weights.get(position.asset_id)
        assets.append(
            AssetPriceSeriesPayload(
                asset_id=position.asset_id,
                weight=(float(weight) if weight is not None else None),
                currency=currency,
                buckets=buckets,
                latest_close=latest_close,
                latest_date=latest_date,
            )
        )
    assets.sort(key=lambda payload: payload.asset_id)

    return PortfolioTechnicalPricesPayload(
        assets=tuple(assets),
        eligible_asset_count=len(universe.positions),
        considered_asset_count=universe.considered_count,
    )


PORTFOLIO_TECHNICAL_PRICES_SPEC = ComponentSpec(
    component_id="portfolio.technical_prices",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioTechnicalPricesPayload,
    builder=_build_portfolio_technical_prices,
    period_behavior=PeriodBehavior.AGGREGATED,
    aggregator=OHLC_BUCKET_AGGREGATOR,
)


# =============================================================================
# {portfolio,broker}.technical_indicators
# =============================================================================


async def _build_universe_technical_indicators(context: BuildContext, *, universe_kwargs: Mapping[str, object]) -> UniverseIndicatorsPayload:
    universe: TechnicalUniverseBundle = await load_technical_universe_bundle(context, **universe_kwargs)

    assets: list[AssetIndicatorsPayload] = []
    for position in universe.positions:
        result = universe.price_results.by_asset_id.get(position.asset_id)
        if result is None:
            continue
        indicators = build_indicator_table_payloads(result.signals, context.bucket_plan)
        weight = universe.weights.get(position.asset_id)
        assets.append(
            AssetIndicatorsPayload(
                asset_id=position.asset_id,
                weight=(float(weight) if weight is not None else None),
                indicators=indicators,
            )
        )
    assets.sort(key=lambda payload: payload.asset_id)

    return UniverseIndicatorsPayload(
        assets=tuple(assets),
        eligible_asset_count=len(universe.positions),
        considered_asset_count=universe.considered_count,
    )


async def _build_portfolio_technical_indicators(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> UniverseIndicatorsPayload:
    return await _build_universe_technical_indicators(context, universe_kwargs=PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS)


async def _build_broker_technical_indicators(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> UniverseIndicatorsPayload:
    return await _build_universe_technical_indicators(context, universe_kwargs=BROKER_TECHNICAL_UNIVERSE_KWARGS)


PORTFOLIO_TECHNICAL_INDICATORS_SPEC = ComponentSpec(
    component_id="portfolio.technical_indicators",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=UniverseIndicatorsPayload,
    builder=_build_portfolio_technical_indicators,
    dependencies=("portfolio.technical_prices",),
    period_behavior=PeriodBehavior.AGGREGATED,
    aggregator=SIGNAL_PROFILE_BUCKET_AGGREGATOR,
)

BROKER_TECHNICAL_INDICATORS_SPEC = ComponentSpec(
    component_id="broker.technical_indicators",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=UniverseIndicatorsPayload,
    builder=_build_broker_technical_indicators,
    period_behavior=PeriodBehavior.AGGREGATED,
    aggregator=SIGNAL_PROFILE_BUCKET_AGGREGATOR,
)


# =============================================================================
# {portfolio,broker}.technical_breadth
# =============================================================================


async def _build_portfolio_technical_breadth(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> UniverseBreadthPayload:
    universe = await load_technical_universe_bundle(context, **PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS)
    return build_breadth_payload(universe)


async def _build_broker_technical_breadth(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> UniverseBreadthPayload:
    universe = await load_technical_universe_bundle(context, **BROKER_TECHNICAL_UNIVERSE_KWARGS)
    return build_breadth_payload(universe)


PORTFOLIO_TECHNICAL_BREADTH_SPEC = ComponentSpec(
    component_id="portfolio.technical_breadth",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=UniverseBreadthPayload,
    builder=_build_portfolio_technical_breadth,
    dependencies=("portfolio.technical_indicators",),
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_TECHNICAL_BREADTH_SPEC = ComponentSpec(
    component_id="broker.technical_breadth",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=UniverseBreadthPayload,
    builder=_build_broker_technical_breadth,
    dependencies=("broker.technical_indicators",),
    period_behavior=PeriodBehavior.WINDOWED,
)


# =============================================================================
# {portfolio,broker}.technical_events
# =============================================================================


async def _build_universe_technical_events(context: BuildContext, *, universe_kwargs: Mapping[str, object]) -> TechnicalEventsPayload:
    universe: TechnicalUniverseBundle = await load_technical_universe_bundle(context, **universe_kwargs)

    events = []
    for position in universe.positions:
        result = universe.price_results.by_asset_id.get(position.asset_id)
        if result is None:
            continue
        events.extend(signal_results_to_discrete_events(result.signals, asset_id=position.asset_id))

    return build_events_payload(tuple(events), context.bucket_plan)


async def _build_portfolio_technical_events(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalEventsPayload:
    return await _build_universe_technical_events(context, universe_kwargs=PORTFOLIO_TECHNICAL_UNIVERSE_KWARGS)


async def _build_broker_technical_events(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> TechnicalEventsPayload:
    return await _build_universe_technical_events(context, universe_kwargs=BROKER_TECHNICAL_UNIVERSE_KWARGS)


PORTFOLIO_TECHNICAL_EVENTS_SPEC = ComponentSpec(
    component_id="portfolio.technical_events",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=TechnicalEventsPayload,
    builder=_build_portfolio_technical_events,
    dependencies=("portfolio.technical_indicators",),
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_TECHNICAL_EVENTS_SPEC = ComponentSpec(
    component_id="broker.technical_events",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=TechnicalEventsPayload,
    builder=_build_broker_technical_events,
    dependencies=("broker.technical_indicators",),
    period_behavior=PeriodBehavior.WINDOWED,
)


PORTFOLIO_BROKER_TECHNICAL_COMPONENTS: tuple[ComponentSpec, ...] = (
    PORTFOLIO_TECHNICAL_PRICES_SPEC,
    PORTFOLIO_TECHNICAL_INDICATORS_SPEC,
    PORTFOLIO_TECHNICAL_BREADTH_SPEC,
    PORTFOLIO_TECHNICAL_EVENTS_SPEC,
    BROKER_TECHNICAL_INDICATORS_SPEC,
    BROKER_TECHNICAL_BREADTH_SPEC,
    BROKER_TECHNICAL_EVENTS_SPEC,
)


__all__ = [
    "BROKER_TECHNICAL_BREADTH_SPEC",
    "BROKER_TECHNICAL_EVENTS_SPEC",
    "BROKER_TECHNICAL_INDICATORS_SPEC",
    "PORTFOLIO_BROKER_TECHNICAL_COMPONENTS",
    "PORTFOLIO_TECHNICAL_BREADTH_SPEC",
    "PORTFOLIO_TECHNICAL_EVENTS_SPEC",
    "PORTFOLIO_TECHNICAL_INDICATORS_SPEC",
    "PORTFOLIO_TECHNICAL_PRICES_SPEC",
]
