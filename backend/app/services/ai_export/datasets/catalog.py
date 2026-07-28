"""Frozen 18-dataset catalog for the AI Export Phase 0 refinement (workstream D).

Dataset IDs and domains are frozen per the refinement plan
(`plan-phase00AiExportRefinementImplementation.prompt.md`, section 4):

    portfolio.overview, portfolio.performance_flows, portfolio.technical,
    portfolio.fifo, portfolio.all_data,
    broker.overview, broker.performance_flows, broker.technical, broker.fifo,
    broker.all_data,
    asset.overview, asset.position_performance, asset.market_technical,
    asset.all_data,
    fx.overview, fx.market_technical, fx.direct_exposure, fx.all_data

All 18 datasets support Compact/Standard/Full. Every `*.all_data` dataset is
computed from its domain's non-`all_data` siblings via `build_all_data_dataset`
(declarative union, never a bespoke builder).

Component composition (required/optional component IDs) is this workstream's own
foundation design choice - only the dataset IDs/domains/detail-level support are
frozen by the plan; the component-level breakdown will be extended by workstreams
E1 (Portfolio/Broker) and E2 (Asset/FX) without changing dataset IDs.

Requiredness follows the approved architecture review: provenance/semantics
sections are required for every overview dataset, reconciliation is required for
every performance dataset, portfolio/broker technical breadth is required, FX/Asset
technical states/events are required, and FX exposure provenance is required.
Empty results from any of these remain a valid success (see
`backend.app.services.ai_export.dependencies` module docstring) - they are never
promoted to errors. The single deliberately-optional exception is
`asset.lot_detail` ("if useful" lot-level detail on top of aggregate position
performance).
"""

from __future__ import annotations

from backend.app.services.ai_export.components.catalog import build_component_registry
from backend.app.services.ai_export.components.registry import ComponentRegistry
from backend.app.services.ai_export.components.types import ALL_DETAIL_LEVELS, Domain, PeriodBehavior
from backend.app.services.ai_export.datasets.spec import DatasetRegistry, DatasetSpec, build_all_data_dataset

EXPECTED_DATASET_COUNT = 18

# -- Portfolio ------------------------------------------------------------------

PORTFOLIO_OVERVIEW = DatasetSpec(
    dataset_id="portfolio.overview",
    version=1,
    domain=Domain.PORTFOLIO,
    display_i18n_key="aiExport.dataset.portfolio.overview.display",
    description_i18n_key="aiExport.dataset.portfolio.overview.description",
    icon="layout-dashboard",
    applicability_code="always_applicable",
    applicable_pages=("dashboard",),
    required_component_ids=("portfolio.summary", "portfolio.positions", "portfolio.allocations_cash", "portfolio.provenance"),
    optional_component_ids=(),
    section_order=("portfolio.summary", "portfolio.positions", "portfolio.allocations_cash", "portfolio.provenance"),
    technical_requirements=(),
    period_semantics=PeriodBehavior.AS_OF,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

PORTFOLIO_PERFORMANCE_FLOWS = DatasetSpec(
    dataset_id="portfolio.performance_flows",
    version=1,
    domain=Domain.PORTFOLIO,
    display_i18n_key="aiExport.dataset.portfolio.performance_flows.display",
    description_i18n_key="aiExport.dataset.portfolio.performance_flows.description",
    icon="trending-up",
    applicability_code="always_applicable",
    applicable_pages=("dashboard",),
    required_component_ids=("portfolio.performance", "portfolio.flows_income", "portfolio.fees_taxes", "portfolio.reconciliation"),
    optional_component_ids=(),
    section_order=("portfolio.performance", "portfolio.flows_income", "portfolio.fees_taxes", "portfolio.reconciliation"),
    technical_requirements=("requires_price_history",),
    period_semantics=PeriodBehavior.WINDOWED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

PORTFOLIO_TECHNICAL = DatasetSpec(
    dataset_id="portfolio.technical",
    version=1,
    domain=Domain.PORTFOLIO,
    display_i18n_key="aiExport.dataset.portfolio.technical.display",
    description_i18n_key="aiExport.dataset.portfolio.technical.description",
    icon="activity",
    applicability_code="always_applicable",
    applicable_pages=("dashboard",),
    required_component_ids=("portfolio.technical_prices", "portfolio.technical_indicators", "portfolio.technical_events", "portfolio.technical_breadth"),
    optional_component_ids=(),
    section_order=("portfolio.technical_prices", "portfolio.technical_indicators", "portfolio.technical_events", "portfolio.technical_breadth"),
    technical_requirements=("requires_price_history", "requires_signal_plugins"),
    period_semantics=PeriodBehavior.AGGREGATED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

PORTFOLIO_FIFO = DatasetSpec(
    dataset_id="portfolio.fifo",
    version=1,
    domain=Domain.PORTFOLIO,
    display_i18n_key="aiExport.dataset.portfolio.fifo.display",
    description_i18n_key="aiExport.dataset.portfolio.fifo.description",
    icon="list-ordered",
    applicability_code="always_applicable",
    applicable_pages=("dashboard",),
    required_component_ids=("portfolio.fifo_summary", "portfolio.fifo_lots"),
    optional_component_ids=(),
    section_order=("portfolio.fifo_summary", "portfolio.fifo_lots"),
    technical_requirements=("requires_lots_analysis_service",),
    period_semantics=PeriodBehavior.WINDOWED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

# -- Broker -----------------------------------------------------------------------

BROKER_OVERVIEW = DatasetSpec(
    dataset_id="broker.overview",
    version=1,
    domain=Domain.BROKER,
    display_i18n_key="aiExport.dataset.broker.overview.display",
    description_i18n_key="aiExport.dataset.broker.overview.description",
    icon="landmark",
    applicability_code="always_applicable",
    applicable_pages=("broker",),
    required_component_ids=("broker.summary", "broker.positions", "broker.allocation_concentration", "broker.provenance"),
    optional_component_ids=(),
    section_order=("broker.summary", "broker.positions", "broker.allocation_concentration", "broker.provenance"),
    technical_requirements=(),
    period_semantics=PeriodBehavior.AS_OF,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

BROKER_PERFORMANCE_FLOWS = DatasetSpec(
    dataset_id="broker.performance_flows",
    version=1,
    domain=Domain.BROKER,
    display_i18n_key="aiExport.dataset.broker.performance_flows.display",
    description_i18n_key="aiExport.dataset.broker.performance_flows.description",
    icon="trending-up",
    applicability_code="always_applicable",
    applicable_pages=("broker",),
    required_component_ids=("broker.performance", "broker.flows_income_costs", "broker.reconciliation"),
    optional_component_ids=(),
    section_order=("broker.performance", "broker.flows_income_costs", "broker.reconciliation"),
    technical_requirements=("requires_price_history",),
    period_semantics=PeriodBehavior.WINDOWED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

BROKER_TECHNICAL = DatasetSpec(
    dataset_id="broker.technical",
    version=1,
    domain=Domain.BROKER,
    display_i18n_key="aiExport.dataset.broker.technical.display",
    description_i18n_key="aiExport.dataset.broker.technical.description",
    icon="activity",
    applicability_code="always_applicable",
    applicable_pages=("broker",),
    required_component_ids=("broker.technical_indicators", "broker.technical_events", "broker.technical_breadth"),
    optional_component_ids=(),
    section_order=("broker.technical_indicators", "broker.technical_events", "broker.technical_breadth"),
    technical_requirements=("requires_price_history", "requires_signal_plugins"),
    period_semantics=PeriodBehavior.AGGREGATED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

BROKER_FIFO = DatasetSpec(
    dataset_id="broker.fifo",
    version=1,
    domain=Domain.BROKER,
    display_i18n_key="aiExport.dataset.broker.fifo.display",
    description_i18n_key="aiExport.dataset.broker.fifo.description",
    icon="list-ordered",
    applicability_code="always_applicable",
    applicable_pages=("broker",),
    required_component_ids=("broker.fifo_lots",),
    optional_component_ids=(),
    section_order=("broker.fifo_lots",),
    technical_requirements=("requires_lots_analysis_service",),
    period_semantics=PeriodBehavior.WINDOWED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

# -- Asset ----------------------------------------------------------------------

ASSET_OVERVIEW = DatasetSpec(
    dataset_id="asset.overview",
    version=1,
    domain=Domain.ASSET,
    display_i18n_key="aiExport.dataset.asset.overview.display",
    description_i18n_key="aiExport.dataset.asset.overview.description",
    icon="coins",
    applicability_code="always_applicable",
    applicable_pages=("asset",),
    required_component_ids=("asset.identity", "asset.market_snapshot", "asset.position_scope", "asset.provenance"),
    optional_component_ids=(),
    section_order=("asset.identity", "asset.market_snapshot", "asset.position_scope", "asset.provenance"),
    technical_requirements=(),
    period_semantics=PeriodBehavior.AS_OF,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

ASSET_POSITION_PERFORMANCE = DatasetSpec(
    dataset_id="asset.position_performance",
    version=1,
    domain=Domain.ASSET,
    display_i18n_key="aiExport.dataset.asset.position_performance.display",
    description_i18n_key="aiExport.dataset.asset.position_performance.description",
    icon="wallet",
    applicability_code="always_applicable",
    applicable_pages=("asset",),
    required_component_ids=("asset.positions_by_broker", "asset.cost_value_pl", "asset.performance"),
    # asset.lot_detail is deliberately the sole optional component in this catalog
    # (per architecture review: lot-level detail is "if useful" on top of the
    # required aggregate cost/value/P&L/performance sections).
    optional_component_ids=("asset.lot_detail",),
    section_order=("asset.positions_by_broker", "asset.cost_value_pl", "asset.performance", "asset.lot_detail"),
    technical_requirements=("requires_lots_analysis_service",),
    period_semantics=PeriodBehavior.WINDOWED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

ASSET_MARKET_TECHNICAL = DatasetSpec(
    dataset_id="asset.market_technical",
    version=1,
    domain=Domain.ASSET,
    display_i18n_key="aiExport.dataset.asset.market_technical.display",
    description_i18n_key="aiExport.dataset.asset.market_technical.description",
    icon="activity",
    applicability_code="always_applicable",
    applicable_pages=("asset",),
    required_component_ids=("asset.ohlc_returns", "asset.indicators", "asset.states_events"),
    optional_component_ids=(),
    section_order=("asset.ohlc_returns", "asset.indicators", "asset.states_events"),
    technical_requirements=("requires_price_history", "requires_signal_plugins"),
    period_semantics=PeriodBehavior.AGGREGATED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

# -- FX ---------------------------------------------------------------------------

FX_OVERVIEW = DatasetSpec(
    dataset_id="fx.overview",
    version=1,
    domain=Domain.FX,
    display_i18n_key="aiExport.dataset.fx.overview.display",
    description_i18n_key="aiExport.dataset.fx.overview.description",
    icon="arrow-left-right",
    applicability_code="always_applicable",
    applicable_pages=("fx",),
    required_component_ids=("fx.pair_identity", "fx.current_rate", "fx.conversion_provenance"),
    optional_component_ids=(),
    section_order=("fx.pair_identity", "fx.current_rate", "fx.conversion_provenance"),
    technical_requirements=(),
    period_semantics=PeriodBehavior.AS_OF,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

FX_MARKET_TECHNICAL = DatasetSpec(
    dataset_id="fx.market_technical",
    version=1,
    domain=Domain.FX,
    display_i18n_key="aiExport.dataset.fx.market_technical.display",
    description_i18n_key="aiExport.dataset.fx.market_technical.description",
    icon="activity",
    applicability_code="always_applicable",
    applicable_pages=("fx",),
    required_component_ids=("fx.rate_ohlc", "fx.returns_volatility", "fx.indicators", "fx.states_events"),
    optional_component_ids=(),
    section_order=("fx.rate_ohlc", "fx.returns_volatility", "fx.indicators", "fx.states_events"),
    technical_requirements=("requires_price_history", "requires_signal_plugins"),
    period_semantics=PeriodBehavior.AGGREGATED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)

FX_DIRECT_EXPOSURE = DatasetSpec(
    dataset_id="fx.direct_exposure",
    version=1,
    domain=Domain.FX,
    display_i18n_key="aiExport.dataset.fx.direct_exposure.display",
    description_i18n_key="aiExport.dataset.fx.direct_exposure.description",
    icon="scale",
    applicability_code="always_applicable",
    applicable_pages=("fx",),
    # Binding semantics: this capability is statically declared in the catalog
    # regardless of whether any given request actually has FX exposure. A request
    # for a portfolio with no foreign-currency positions must still succeed with an
    # empty payload (component build succeeds, data is simply empty) - it must
    # never surface as an error/503; that is a build *failure*, not an *absence of
    # exposure*. Whether "no exposure" makes an analysis inapplicable is a separate,
    # higher-level applicability concern (future 422), not decided here.
    required_component_ids=("fx.exposure_base_quote", "fx.exposure_provenance"),
    optional_component_ids=(),
    section_order=("fx.exposure_base_quote", "fx.exposure_provenance"),
    technical_requirements=("requires_fx_conversions",),
    period_semantics=PeriodBehavior.WINDOWED,
    supported_detail_levels=ALL_DETAIL_LEVELS,
)


def _build_all_data_specs(component_registry: ComponentRegistry) -> tuple[DatasetSpec, DatasetSpec, DatasetSpec, DatasetSpec]:
    portfolio_all_data = build_all_data_dataset(
        dataset_id="portfolio.all_data",
        version=1,
        domain=Domain.PORTFOLIO,
        display_i18n_key="aiExport.dataset.portfolio.all_data.display",
        description_i18n_key="aiExport.dataset.portfolio.all_data.description",
        icon="database",
        applicability_code="always_applicable",
        applicable_pages=("dashboard",),
        technical_requirements=("requires_price_history", "requires_signal_plugins", "requires_lots_analysis_service"),
        period_semantics=PeriodBehavior.AGGREGATED,
        supported_detail_levels=ALL_DETAIL_LEVELS,
        source_specs=(PORTFOLIO_OVERVIEW, PORTFOLIO_PERFORMANCE_FLOWS, PORTFOLIO_TECHNICAL, PORTFOLIO_FIFO),
        component_registry=component_registry,
    )
    broker_all_data = build_all_data_dataset(
        dataset_id="broker.all_data",
        version=1,
        domain=Domain.BROKER,
        display_i18n_key="aiExport.dataset.broker.all_data.display",
        description_i18n_key="aiExport.dataset.broker.all_data.description",
        icon="database",
        applicability_code="always_applicable",
        applicable_pages=("broker",),
        technical_requirements=("requires_price_history", "requires_signal_plugins", "requires_lots_analysis_service"),
        period_semantics=PeriodBehavior.AGGREGATED,
        supported_detail_levels=ALL_DETAIL_LEVELS,
        source_specs=(BROKER_OVERVIEW, BROKER_PERFORMANCE_FLOWS, BROKER_TECHNICAL, BROKER_FIFO),
        component_registry=component_registry,
    )
    asset_all_data = build_all_data_dataset(
        dataset_id="asset.all_data",
        version=1,
        domain=Domain.ASSET,
        display_i18n_key="aiExport.dataset.asset.all_data.display",
        description_i18n_key="aiExport.dataset.asset.all_data.description",
        icon="database",
        applicability_code="always_applicable",
        applicable_pages=("asset",),
        technical_requirements=("requires_price_history", "requires_signal_plugins", "requires_lots_analysis_service"),
        period_semantics=PeriodBehavior.AGGREGATED,
        supported_detail_levels=ALL_DETAIL_LEVELS,
        source_specs=(ASSET_OVERVIEW, ASSET_POSITION_PERFORMANCE, ASSET_MARKET_TECHNICAL),
        component_registry=component_registry,
    )
    fx_all_data = build_all_data_dataset(
        dataset_id="fx.all_data",
        version=1,
        domain=Domain.FX,
        display_i18n_key="aiExport.dataset.fx.all_data.display",
        description_i18n_key="aiExport.dataset.fx.all_data.description",
        icon="database",
        applicability_code="always_applicable",
        applicable_pages=("fx",),
        technical_requirements=("requires_price_history", "requires_signal_plugins", "requires_fx_conversions"),
        period_semantics=PeriodBehavior.AGGREGATED,
        supported_detail_levels=ALL_DETAIL_LEVELS,
        source_specs=(FX_OVERVIEW, FX_MARKET_TECHNICAL, FX_DIRECT_EXPOSURE),
        component_registry=component_registry,
    )
    return portfolio_all_data, broker_all_data, asset_all_data, fx_all_data


def build_dataset_registry(component_registry: ComponentRegistry | None = None) -> DatasetRegistry:
    """Builds the `DatasetRegistry` for the frozen 18-dataset catalog."""
    registry = component_registry or build_component_registry()
    portfolio_all_data, broker_all_data, asset_all_data, fx_all_data = _build_all_data_specs(registry)
    specs = (
        PORTFOLIO_OVERVIEW,
        PORTFOLIO_PERFORMANCE_FLOWS,
        PORTFOLIO_TECHNICAL,
        PORTFOLIO_FIFO,
        portfolio_all_data,
        BROKER_OVERVIEW,
        BROKER_PERFORMANCE_FLOWS,
        BROKER_TECHNICAL,
        BROKER_FIFO,
        broker_all_data,
        ASSET_OVERVIEW,
        ASSET_POSITION_PERFORMANCE,
        ASSET_MARKET_TECHNICAL,
        asset_all_data,
        FX_OVERVIEW,
        FX_MARKET_TECHNICAL,
        FX_DIRECT_EXPOSURE,
        fx_all_data,
    )
    assert len(specs) == EXPECTED_DATASET_COUNT
    return DatasetRegistry(specs, component_registry=registry)
