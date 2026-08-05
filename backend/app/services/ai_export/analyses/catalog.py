"""Public AI Export V3 analysis catalog.

The component runtime exposes eleven task-oriented analyses. Granular datasets
remain internal composition blocks, but analyses themselves are public-only:
there is no second legacy analysis registry or profile catalog.
"""

from __future__ import annotations

from backend.app.services.ai_export.analyses.spec import (
    AdditionalExportPeriod,
    AdditionalExportSuggestion,
    AnalysisRegistry,
    AnalysisSpec,
)
from backend.app.services.ai_export.catalog_visibility import CatalogVisibility
from backend.app.services.ai_export.components.types import DetailLevel, Domain
from backend.app.services.ai_export.datasets.catalog import build_dataset_registry
from backend.app.services.ai_export.datasets.spec import DatasetRegistry

EXPECTED_ANALYSIS_COUNT = 11
EXPECTED_PUBLIC_ANALYSIS_COUNT = 11

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
    suggestions: tuple[AdditionalExportSuggestion, ...] = (),
) -> AnalysisSpec:
    analysis_id = f"{domain.value}.{suffix}"
    return AnalysisSpec(
        analysis_id=analysis_id,
        version=3,
        domain=domain,
        display_i18n_key=f"aiExport.analysis.{analysis_id}.display",
        description_i18n_key=f"aiExport.analysis.{analysis_id}.description",
        icon=icon,
        applicability_code=applicability_code,
        applicable_pages=_DOMAIN_PAGES[domain],
        required_dataset_ids=required,
        optional_dataset_ids=optional,
        instruction_template_id=f"{analysis_id}.instructions",
        instruction_template_version=3,
        response_contract_id=f"{analysis_id}.response",
        response_contract_version=3,
        additional_export_suggestions=suggestions,
        visibility=CatalogVisibility.PUBLIC,
    )


def _suggest(
    dataset_id: str,
    reason: str,
    period: AdditionalExportPeriod,
    detail: DetailLevel,
) -> AdditionalExportSuggestion:
    return AdditionalExportSuggestion(
        dataset_id=dataset_id,
        reason_i18n_key=f"aiExport.additionalData.reason.{reason}",
        recommended_period=period,
        recommended_detail=detail,
    )


PUBLIC_ANALYSES: tuple[AnalysisSpec, ...] = (
    _analysis(
        Domain.PORTFOLIO,
        "pac_planning",
        icon="calendar-clock",
        required=("portfolio.overview_and_history",),
        suggestions=(
            _suggest(
                "portfolio.asset_history",
                "deeperTechnical",
                AdditionalExportPeriod.THREE_MONTHS,
                DetailLevel.STANDARD,
            ),
        ),
    ),
    _analysis(
        Domain.PORTFOLIO,
        "rebalancing",
        icon="scale",
        required=("portfolio.overview_and_history",),
        suggestions=(
            _suggest(
                "portfolio.asset_history",
                "deeperTechnical",
                AdditionalExportPeriod.ONE_YEAR,
                DetailLevel.COMPACT,
            ),
        ),
    ),
    _analysis(
        Domain.PORTFOLIO,
        "performance_market_drivers",
        icon="newspaper",
        required=("portfolio.overview_and_history",),
        suggestions=(
            _suggest(
                "portfolio.asset_history",
                "deeperTechnical",
                AdditionalExportPeriod.THREE_MONTHS,
                DetailLevel.STANDARD,
            ),
        ),
    ),
    _analysis(
        Domain.PORTFOLIO,
        "fiscal_lots",
        icon="list-ordered",
        required=("portfolio.overview_and_history", "portfolio.fifo"),
        suggestions=(
            _suggest(
                "portfolio.asset_history",
                "deeperTechnical",
                AdditionalExportPeriod.ONE_YEAR,
                DetailLevel.COMPACT,
            ),
        ),
    ),
    _analysis(
        Domain.BROKER,
        "review",
        icon="landmark",
        required=("broker.overview_and_history",),
        suggestions=(
            _suggest(
                "broker.asset_history",
                "deeperTechnical",
                AdditionalExportPeriod.THREE_MONTHS,
                DetailLevel.STANDARD,
            ),
        ),
    ),
    _analysis(
        Domain.BROKER,
        "performance_market_drivers",
        icon="newspaper",
        required=("broker.overview_and_history",),
        suggestions=(
            _suggest(
                "broker.asset_history",
                "deeperTechnical",
                AdditionalExportPeriod.THREE_MONTHS,
                DetailLevel.STANDARD,
            ),
        ),
    ),
    _analysis(
        Domain.BROKER,
        "fiscal_lots",
        icon="list-ordered",
        required=("broker.overview_and_history", "broker.fifo"),
        suggestions=(
            _suggest(
                "broker.asset_history",
                "deeperTechnical",
                AdditionalExportPeriod.ONE_YEAR,
                DetailLevel.COMPACT,
            ),
        ),
    ),
    _analysis(
        Domain.ASSET,
        "position_review",
        icon="wallet",
        required=("asset.position_and_history",),
        applicability_code="requires_position",
        suggestions=(
            _suggest(
                "asset.market_history",
                "deeperTechnical",
                AdditionalExportPeriod.ONE_YEAR,
                DetailLevel.STANDARD,
            ),
        ),
    ),
    _analysis(
        Domain.ASSET,
        "market_analysis",
        icon="trending-up",
        required=("asset.market_history",),
        suggestions=(
            _suggest(
                "asset.position_and_history",
                "positionContext",
                AdditionalExportPeriod.ONE_YEAR,
                DetailLevel.STANDARD,
            ),
        ),
    ),
    _analysis(
        Domain.FX,
        "pair_analysis",
        icon="trending-up",
        required=("fx.market_history",),
        suggestions=(
            _suggest(
                "fx.market_and_exposure",
                "directExposure",
                AdditionalExportPeriod.THREE_MONTHS,
                DetailLevel.COMPACT,
            ),
        ),
    ),
    _analysis(
        Domain.FX,
        "exposure_impact",
        icon="scale",
        required=("fx.market_and_exposure",),
        applicability_code="requires_direct_exposure",
        suggestions=(
            _suggest(
                "fx.market_history",
                "deeperTechnical",
                AdditionalExportPeriod.ONE_YEAR,
                DetailLevel.COMPACT,
            ),
        ),
    ),
)

assert len(PUBLIC_ANALYSES) == EXPECTED_ANALYSIS_COUNT


def build_analysis_registry(
    dataset_registry: DatasetRegistry | None = None,
) -> AnalysisRegistry:
    """Build the eleven-entry public V3 analysis registry."""

    registry = dataset_registry or build_dataset_registry()
    return AnalysisRegistry(PUBLIC_ANALYSES, dataset_registry=registry)
