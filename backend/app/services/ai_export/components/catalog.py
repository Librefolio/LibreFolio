"""Integrated `ComponentSpec` catalog for the AI Export runtime.

`ALL_FOUNDATION_COMPONENTS` retains the frozen fail-closed placeholder tuple as
the metadata validation baseline used by domain-fragment tests. Production
`build_component_registry()` returns `ALL_COMPONENTS`: the same canonical order
with all 45 IDs replaced by the reviewed Portfolio/Broker/Asset/FX builders.

Both replacement fragments validate exact version/domain/dependency/period/
aggregator parity against the placeholders before the central tuple is created.
Import-time count/ID checks then reject duplicates, omissions, or extra builders.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from backend.app.services.ai_export.components.asset_fx_registry import (
    ASSET_FX_COMPONENTS,
)
from backend.app.services.ai_export.components.asset_fx_registry import (
    validate_replacements_against_placeholders as validate_asset_fx_replacements,
)
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.portfolio_broker_registry import (
    PORTFOLIO_BROKER_COMPONENTS,
)
from backend.app.services.ai_export.components.portfolio_broker_registry import (
    validate_replacements_against_placeholders as validate_portfolio_broker_replacements,
)
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import Domain, PeriodBehavior, TemporalAggregatorSpec
from backend.app.services.ai_export.dependencies import BuildContext


class ComponentNotImplementedError(RuntimeError):
    """Raised by every production foundation builder placeholder.

    Deliberately fail-closed: real domain logic (workstreams E1/E2) has not
    replaced this builder yet, so it must never fabricate a fake successful
    payload that could silently leak into a wired-up runtime ahead of E1/E2. Any
    caller (`BuildContext`/`Composer`) treats this exactly like any other build
    failure - propagated via `RequiredComponentBuildError` when required, or
    recorded as a single internal diagnostic and swallowed when optional.
    """


class FoundationComponentPayload(BaseModel):
    """Documents the intended future payload shape for foundation components.

    Never actually produced by a production builder (see
    `ComponentNotImplementedError`); kept only so `ComponentSpec.output_model`
    has a concrete, versionable schema placeholder for workstreams E1/E2 to
    replace or extend.
    """

    model_config = ConfigDict(extra="forbid")

    component_id: str
    domain: Domain
    label: str
    depends_on: tuple[str, ...] = ()


def _not_implemented_builder(component_id: str):
    def _build(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> FoundationComponentPayload:
        raise ComponentNotImplementedError(f"{component_id}: production domain builder not implemented yet (pending workstream E1/E2)")

    return _build


_OHLC_BUCKET_AGGREGATOR = TemporalAggregatorSpec(kind="ohlc_bucket", description="Adaptive OHLC bucket aggregation (30/14/7 day cap), owned by the temporal engine workstream")
_SIGNAL_PROFILE_BUCKET_AGGREGATOR = TemporalAggregatorSpec(
    kind="signal_profile_bucket",
    description="Plugin-declared signal profile aggregation with dated row cells",
)


def _component(
    domain: Domain,
    suffix: str,
    label: str,
    *,
    dependencies: tuple[str, ...] = (),
    period_behavior: PeriodBehavior = PeriodBehavior.WINDOWED,
    aggregator: TemporalAggregatorSpec | None = None,
) -> ComponentSpec:
    component_id = f"{domain.value}.{suffix}"
    return ComponentSpec(
        component_id=component_id,
        version=1,
        domains=frozenset({domain}),
        output_model=FoundationComponentPayload,
        builder=_not_implemented_builder(component_id),
        dependencies=dependencies,
        period_behavior=period_behavior,
        aggregator=aggregator,
    )


# -- Portfolio ----------------------------------------------------------------

_PORTFOLIO_COMPONENTS: tuple[ComponentSpec, ...] = (
    _component(Domain.PORTFOLIO, "summary", "Portfolio summary", period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.PORTFOLIO, "positions", "All portfolio positions", period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.PORTFOLIO, "allocations_cash", "Allocations and cash", dependencies=("portfolio.positions",), period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.PORTFOLIO, "provenance", "Semantics and provenance", period_behavior=PeriodBehavior.NONE),
    _component(Domain.PORTFOLIO, "performance", "Portfolio performance and contributors", period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.PORTFOLIO, "flows_income", "Flows and income", period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.PORTFOLIO, "fees_taxes", "Fees and taxes", period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.PORTFOLIO, "reconciliation", "Reconciliation", dependencies=("portfolio.flows_income",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.PORTFOLIO, "technical_prices", "Prices and returns", period_behavior=PeriodBehavior.AGGREGATED, aggregator=_OHLC_BUCKET_AGGREGATOR),
    _component(Domain.PORTFOLIO, "technical_indicators", "Indicators and states", dependencies=("portfolio.technical_prices",), period_behavior=PeriodBehavior.AGGREGATED, aggregator=_SIGNAL_PROFILE_BUCKET_AGGREGATOR),
    _component(Domain.PORTFOLIO, "technical_breadth", "Breadth metrics", dependencies=("portfolio.technical_indicators",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.PORTFOLIO, "technical_events", "Technical state-change events", dependencies=("portfolio.technical_indicators",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.PORTFOLIO, "fifo_summary", "FIFO summary", period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.PORTFOLIO, "fifo_lots", "FIFO open/partial/closed lots", dependencies=("portfolio.fifo_summary",), period_behavior=PeriodBehavior.WINDOWED),
)

# -- Broker ---------------------------------------------------------------------

_BROKER_COMPONENTS: tuple[ComponentSpec, ...] = (
    _component(Domain.BROKER, "summary", "Broker summary", period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.BROKER, "positions", "All broker positions", period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.BROKER, "allocation_concentration", "Allocation and concentration", dependencies=("broker.positions",), period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.BROKER, "provenance", "Semantics and provenance", period_behavior=PeriodBehavior.NONE),
    _component(Domain.BROKER, "performance", "Broker performance and contributors", period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.BROKER, "flows_income_costs", "Flows, income and costs", period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.BROKER, "reconciliation", "Reconciliation", dependencies=("broker.flows_income_costs",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.BROKER, "technical_indicators", "Indicators and states (broker-scoped)", period_behavior=PeriodBehavior.AGGREGATED, aggregator=_SIGNAL_PROFILE_BUCKET_AGGREGATOR),
    _component(Domain.BROKER, "technical_breadth", "Breadth metrics (broker-scoped)", dependencies=("broker.technical_indicators",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.BROKER, "technical_events", "Technical state-change events (broker-scoped)", dependencies=("broker.technical_indicators",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.BROKER, "fifo_lots", "All applicable FIFO lots (broker-scoped)", period_behavior=PeriodBehavior.WINDOWED),
)

# -- Asset ------------------------------------------------------------------------

_ASSET_COMPONENTS: tuple[ComponentSpec, ...] = (
    _component(Domain.ASSET, "identity", "Asset identity", period_behavior=PeriodBehavior.NONE),
    _component(Domain.ASSET, "market_snapshot", "Current market snapshot", dependencies=("asset.identity",), period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.ASSET, "position_scope", "Position scope across brokers", period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.ASSET, "provenance", "Semantics and provenance", period_behavior=PeriodBehavior.NONE),
    _component(Domain.ASSET, "positions_by_broker", "Positions per broker", dependencies=("asset.position_scope",), period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.ASSET, "cost_value_pl", "Cost, value and P&L", dependencies=("asset.positions_by_broker",), period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.ASSET, "performance", "Position performance", dependencies=("asset.cost_value_pl",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.ASSET, "lot_detail", "Applicable lot detail", dependencies=("asset.positions_by_broker",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.ASSET, "ohlc_returns", "OHLC buckets and returns", dependencies=("asset.identity",), period_behavior=PeriodBehavior.AGGREGATED, aggregator=_OHLC_BUCKET_AGGREGATOR),
    _component(Domain.ASSET, "indicators", "Technical indicators", dependencies=("asset.ohlc_returns",), period_behavior=PeriodBehavior.AGGREGATED, aggregator=_SIGNAL_PROFILE_BUCKET_AGGREGATOR),
    _component(Domain.ASSET, "states_events", "Technical states and events", dependencies=("asset.indicators",), period_behavior=PeriodBehavior.WINDOWED),
)

# -- FX -----------------------------------------------------------------------------

_FX_COMPONENTS: tuple[ComponentSpec, ...] = (
    _component(Domain.FX, "pair_identity", "FX pair identity", period_behavior=PeriodBehavior.NONE),
    _component(Domain.FX, "current_rate", "Current rate", dependencies=("fx.pair_identity",), period_behavior=PeriodBehavior.AS_OF),
    _component(Domain.FX, "conversion_provenance", "Conversion provenance", period_behavior=PeriodBehavior.NONE),
    _component(Domain.FX, "rate_ohlc", "Rate OHLC", dependencies=("fx.pair_identity",), period_behavior=PeriodBehavior.AGGREGATED, aggregator=_OHLC_BUCKET_AGGREGATOR),
    _component(Domain.FX, "returns_volatility", "Returns and volatility", dependencies=("fx.rate_ohlc",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.FX, "indicators", "Technical indicators", dependencies=("fx.rate_ohlc",), period_behavior=PeriodBehavior.AGGREGATED, aggregator=_SIGNAL_PROFILE_BUCKET_AGGREGATOR),
    _component(Domain.FX, "states_events", "Technical states and events", dependencies=("fx.indicators",), period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.FX, "exposure_base_quote", "Direct base/quote exposures", period_behavior=PeriodBehavior.WINDOWED),
    _component(Domain.FX, "exposure_provenance", "Conversion provenance for exposures", dependencies=("fx.exposure_base_quote",), period_behavior=PeriodBehavior.NONE),
)

ALL_FOUNDATION_COMPONENTS: tuple[ComponentSpec, ...] = _PORTFOLIO_COMPONENTS + _BROKER_COMPONENTS + _ASSET_COMPONENTS + _FX_COMPONENTS

ALL_REAL_COMPONENTS: tuple[ComponentSpec, ...] = (
    *PORTFOLIO_BROKER_COMPONENTS,
    *ASSET_FX_COMPONENTS,
)


def _build_integrated_components() -> tuple[ComponentSpec, ...]:
    validate_portfolio_broker_replacements(
        PORTFOLIO_BROKER_COMPONENTS,
        placeholders=ALL_FOUNDATION_COMPONENTS,
    )
    validate_asset_fx_replacements(
        ASSET_FX_COMPONENTS,
        placeholders=ALL_FOUNDATION_COMPONENTS,
    )
    replacement_by_id = {spec.component_id: spec for spec in ALL_REAL_COMPONENTS}
    if len(replacement_by_id) != len(ALL_REAL_COMPONENTS):
        raise RuntimeError("real AI Export component fragments contain duplicate component_ids")
    foundation_ids = {spec.component_id for spec in ALL_FOUNDATION_COMPONENTS}
    replacement_ids = set(replacement_by_id)
    if replacement_ids != foundation_ids:
        missing = sorted(foundation_ids - replacement_ids)
        extra = sorted(replacement_ids - foundation_ids)
        raise RuntimeError("real AI Export component coverage mismatch " f"(missing={missing}, extra={extra})")
    return tuple(replacement_by_id[placeholder.component_id] for placeholder in ALL_FOUNDATION_COMPONENTS)


ALL_COMPONENTS: tuple[ComponentSpec, ...] = _build_integrated_components()

assert len(ALL_FOUNDATION_COMPONENTS) == 45
assert len(ALL_REAL_COMPONENTS) == 45
assert len(ALL_COMPONENTS) == 45


def build_component_registry() -> ComponentRegistry:
    """Build the production registry containing all 45 real component specs."""

    return ComponentRegistry(ALL_COMPONENTS)
