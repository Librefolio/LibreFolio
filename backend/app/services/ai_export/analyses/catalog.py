"""Frozen 17-analysis catalog for the AI Export Phase 0 refinement (workstream D).

Analysis IDs and required/optional dataset mapping are frozen per the refinement
plan (`plan-phase00AiExportRefinementImplementation.prompt.md`, section 5):

| Analysis ID | Required | Optional |
|---|---|---|
| portfolio.pac_planning | overview, performance_flows | - |
| portfolio.rebalancing | overview | performance_flows, technical |
| portfolio.performance_attribution | overview, performance_flows | - |
| portfolio.income_review | overview, performance_flows | - |
| portfolio.fifo_review | overview, fifo | - |
| portfolio.technical_breadth | overview, technical | - |
| portfolio.description | overview | performance_flows, technical |
| broker.review | overview, performance_flows | technical, fifo |
| broker.cost_efficiency | overview, performance_flows | - |
| broker.concentration_context | overview | technical |
| broker.fifo_review | overview, fifo | - |
| asset.trend_analysis | overview, market_technical | - |
| asset.position_review | overview, position_performance | market_technical |
| asset.drawdown_recovery | overview, market_technical | position_performance |
| fx.trend_review | overview, market_technical | - |
| fx.conversion_timing | overview, market_technical | direct_exposure |
| fx.exposure_impact | overview, direct_exposure | market_technical |

Full dataset IDs are used internally (e.g. `portfolio.performance_flows`, not the
ambiguous short name `performance_flows`).

`instruction_template_id`/`response_contract_id` are placeholder identities: the
real localized templates and response contracts are owned by workstream F
(Analysis/prompt/API); this workstream only freezes the identity/version pairing
each `AnalysisSpec` is validated against.

`display_i18n_key`/`description_i18n_key` follow the `aiExport.analysis.<id>.*`
convention (i18n keys only, catalog returns keys - never literal text).
`applicability_code` is a stable, non-i18n programmatic code; every analysis here
uses `"always_applicable"` because whether an analysis's *prerequisite datasets
actually contain non-empty data* is a separate, future applicability concern (a
422 decision made once real domain builders exist) - not decided by this static
catalog.
"""

from __future__ import annotations

from backend.app.services.ai_export.analyses.spec import AnalysisRegistry, AnalysisSpec
from backend.app.services.ai_export.components.types import Domain
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.ai_export.datasets.spec import DatasetRegistry

EXPECTED_ANALYSIS_COUNT = 17

_DOMAIN_PAGES: dict[Domain, tuple[str, ...]] = {
    Domain.PORTFOLIO: ("dashboard",),
    Domain.BROKER: ("broker",),
    Domain.ASSET: ("asset",),
    Domain.FX: ("fx",),
}


def _analysis(
    domain: Domain,
    suffix: str,
    *,
    icon: str,
    required: tuple[str, ...],
    optional: tuple[str, ...] = (),
    applicability_code: str = "always_applicable",
) -> AnalysisSpec:
    analysis_id = f"{domain.value}.{suffix}"
    return AnalysisSpec(
        analysis_id=analysis_id,
        version=1,
        domain=domain,
        display_i18n_key=f"aiExport.analysis.{analysis_id}.display",
        description_i18n_key=f"aiExport.analysis.{analysis_id}.description",
        icon=icon,
        applicability_code=applicability_code,
        applicable_pages=_DOMAIN_PAGES[domain],
        required_dataset_ids=required,
        optional_dataset_ids=optional,
        instruction_template_id=f"{analysis_id}.instructions",
        instruction_template_version=1,
        response_contract_id=f"{analysis_id}.response",
        response_contract_version=1,
    )


_PORTFOLIO_ANALYSES: tuple[AnalysisSpec, ...] = (
    _analysis(Domain.PORTFOLIO, "pac_planning", icon="calendar-clock", required=("portfolio.overview", "portfolio.performance_flows")),
    _analysis(Domain.PORTFOLIO, "rebalancing", icon="scale", required=("portfolio.overview",), optional=("portfolio.performance_flows", "portfolio.technical")),
    _analysis(Domain.PORTFOLIO, "performance_attribution", icon="pie-chart", required=("portfolio.overview", "portfolio.performance_flows")),
    _analysis(Domain.PORTFOLIO, "income_review", icon="banknote", required=("portfolio.overview", "portfolio.performance_flows")),
    _analysis(Domain.PORTFOLIO, "fifo_review", icon="list-ordered", required=("portfolio.overview", "portfolio.fifo")),
    _analysis(Domain.PORTFOLIO, "technical_breadth", icon="activity", required=("portfolio.overview", "portfolio.technical")),
    _analysis(Domain.PORTFOLIO, "description", icon="file-text", required=("portfolio.overview",), optional=("portfolio.performance_flows", "portfolio.technical")),
)

_BROKER_ANALYSES: tuple[AnalysisSpec, ...] = (
    _analysis(Domain.BROKER, "review", icon="landmark", required=("broker.overview", "broker.performance_flows"), optional=("broker.technical", "broker.fifo")),
    _analysis(Domain.BROKER, "cost_efficiency", icon="receipt", required=("broker.overview", "broker.performance_flows")),
    _analysis(Domain.BROKER, "concentration_context", icon="target", required=("broker.overview",), optional=("broker.technical",)),
    _analysis(Domain.BROKER, "fifo_review", icon="list-ordered", required=("broker.overview", "broker.fifo")),
)

_ASSET_ANALYSES: tuple[AnalysisSpec, ...] = (
    _analysis(Domain.ASSET, "trend_analysis", icon="trending-up", required=("asset.overview", "asset.market_technical")),
    _analysis(Domain.ASSET, "position_review", icon="wallet", required=("asset.overview", "asset.position_performance"), optional=("asset.market_technical",)),
    _analysis(Domain.ASSET, "drawdown_recovery", icon="trending-down", required=("asset.overview", "asset.market_technical"), optional=("asset.position_performance",)),
)

_FX_ANALYSES: tuple[AnalysisSpec, ...] = (
    _analysis(Domain.FX, "trend_review", icon="trending-up", required=("fx.overview", "fx.market_technical")),
    _analysis(Domain.FX, "conversion_timing", icon="clock", required=("fx.overview", "fx.market_technical"), optional=("fx.direct_exposure",)),
    _analysis(Domain.FX, "exposure_impact", icon="scale", required=("fx.overview", "fx.direct_exposure"), optional=("fx.market_technical",)),
)

ALL_ANALYSES: tuple[AnalysisSpec, ...] = _PORTFOLIO_ANALYSES + _BROKER_ANALYSES + _ASSET_ANALYSES + _FX_ANALYSES

assert len(ALL_ANALYSES) == EXPECTED_ANALYSIS_COUNT


def build_analysis_registry(dataset_registry: DatasetRegistry | None = None) -> AnalysisRegistry:
    """Builds the `AnalysisRegistry` for the frozen 17-analysis catalog."""
    registry = dataset_registry or build_dataset_registry()
    return AnalysisRegistry(ALL_ANALYSES, dataset_registry=registry)
