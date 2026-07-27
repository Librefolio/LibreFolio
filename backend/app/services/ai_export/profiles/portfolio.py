"""Portfolio AI Export task manifests."""

from __future__ import annotations

from backend.app.schemas.ai_export import AiExportDetailLevel, AiExportDomain, AiExportTask
from backend.app.services.ai_export.models import TaskSpec, TechnicalDepth
from backend.app.services.ai_export.profiles.asset import ASSET_COMPACT_BUNDLE, ASSET_FULL_BUNDLE, ASSET_STANDARD_BUNDLE
from backend.app.services.ai_export.profiles.base import compact_selection, no_technical, technical_detail, technical_matrix


def _asset_technical(
    compact_depth: TechnicalDepth,
    standard_depth: TechnicalDepth,
    full_depth: TechnicalDepth,
):
    compact = (
        no_technical(AiExportDetailLevel.COMPACT)
        if compact_depth == TechnicalDepth.NONE
        else technical_detail(
            AiExportDetailLevel.COMPACT,
            compact_depth,
            ASSET_COMPACT_BUNDLE,
        )
    )
    standard = (
        no_technical(AiExportDetailLevel.STANDARD)
        if standard_depth == TechnicalDepth.NONE
        else technical_detail(
            AiExportDetailLevel.STANDARD,
            standard_depth,
            ASSET_STANDARD_BUNDLE,
        )
    )
    full = (
        no_technical(AiExportDetailLevel.FULL)
        if full_depth == TechnicalDepth.NONE
        else technical_detail(
            AiExportDetailLevel.FULL,
            full_depth,
            ASSET_FULL_BUNDLE,
        )
    )
    return technical_matrix(compact, standard, full)


PORTFOLIO_TASK_SPECS = (
    TaskSpec(
        domain=AiExportDomain.PORTFOLIO,
        task=AiExportTask.PAC_PLANNING,
        required_sections=(
            "facts.summary",
            "facts.positions",
            "facts.contributions",
            "facts.unallocated_contributions",
            "facts.other_period_effects",
            "facts.allocations",
            "facts.cash_context",
            "coverage",
            "semantics",
        ),
        optional_sections=("states", "technical", "events", "domain_notes"),
        applicability_code="portfolio_accessible",
        frontend_response_contract_id="portfolio.pac_planning",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=compact_selection(
            "largest_nav_and_smallest_non_zero_position",
            12,
            metric="nav",
            largest_count=6,
            smallest_count=6,
            non_zero_only=True,
            deduplicate_union=True,
        ),
        technical_by_detail=_asset_technical(
            TechnicalDepth.LATEST_BREADTH,
            TechnicalDepth.STANDARD_SUMMARY,
            TechnicalDepth.FULL,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.PORTFOLIO,
        task=AiExportTask.REBALANCING,
        required_sections=("facts.summary", "facts.positions", "facts.allocations", "coverage", "semantics"),
        optional_sections=(
            "facts.contributions",
            "facts.unallocated_contributions",
            "facts.other_period_effects",
            "facts.cash_context",
            "states",
            "technical",
            "events",
            "domain_notes",
        ),
        applicability_code="portfolio_accessible",
        frontend_response_contract_id="portfolio.rebalancing",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=True,
        compact_selection=compact_selection(
            "largest_nav",
            12,
            metric="nav",
            ordering="descending",
        ),
        technical_by_detail=_asset_technical(
            TechnicalDepth.LATEST_BREADTH,
            TechnicalDepth.STANDARD_SUMMARY,
            TechnicalDepth.FULL,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.PORTFOLIO,
        task=AiExportTask.PERFORMANCE_ATTRIBUTION,
        required_sections=(
            "facts.summary",
            "facts.contributions",
            "facts.unallocated_contributions",
            "facts.other_period_effects",
            "facts.positions",
            "coverage",
            "semantics",
        ),
        optional_sections=("states", "technical", "events", "domain_notes"),
        applicability_code="selected_range_has_data",
        frontend_response_contract_id="portfolio.performance_attribution",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=False,
        compact_selection=compact_selection(
            "period_pnl_positive_and_negative",
            10,
            metric="period_pnl_amount",
            positive_count=5,
            negative_count=5,
            deduplicate_union=True,
        ),
        technical_by_detail=_asset_technical(
            TechnicalDepth.NONE,
            TechnicalDepth.LATEST_STATES,
            TechnicalDepth.SAMPLED_STANDARD,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.PORTFOLIO,
        task=AiExportTask.INCOME_REVIEW,
        required_sections=(
            "facts.summary",
            "facts.contributions",
            "facts.unallocated_contributions",
            "facts.other_period_effects",
            "facts.positions",
            "coverage",
            "semantics",
        ),
        optional_sections=("states", "technical", "events", "domain_notes"),
        applicability_code="portfolio_accessible",
        frontend_response_contract_id="portfolio.income_review",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=False,
        compact_selection=compact_selection(
            "largest_period_income",
            10,
            metric="period_income_amount",
            ordering="descending",
        ),
        technical_by_detail=_asset_technical(
            TechnicalDepth.NONE,
            TechnicalDepth.LATEST_STATES,
            TechnicalDepth.SAMPLED_STANDARD,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.PORTFOLIO,
        task=AiExportTask.TECHNICAL_BREADTH,
        required_sections=("facts.summary", "facts.positions", "coverage", "semantics"),
        optional_sections=("states", "technical", "events"),
        applicability_code="portfolio_accessible_technical_optional",
        frontend_response_contract_id="portfolio.technical_breadth",
        frontend_response_contract_version=1,
        supports_user_notes=False,
        supports_web_research=True,
        compact_selection=compact_selection(
            "recent_events_weighted_by_nav",
            10,
            metric="nav_weight",
            ordering=("event_date_descending", "nav_weight_descending"),
            aggregate_scope="all_eligible_entities",
        ),
        technical_by_detail=technical_matrix(
            technical_detail(
                AiExportDetailLevel.COMPACT,
                TechnicalDepth.BREADTH_ONLY,
                ASSET_COMPACT_BUNDLE,
                event_limit_override=10,
            ),
            technical_detail(
                AiExportDetailLevel.STANDARD,
                TechnicalDepth.STANDARD,
                ASSET_STANDARD_BUNDLE,
            ),
            technical_detail(
                AiExportDetailLevel.FULL,
                TechnicalDepth.FULL,
                ASSET_FULL_BUNDLE,
            ),
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.PORTFOLIO,
        task=AiExportTask.PORTFOLIO_DESCRIPTION,
        required_sections=("facts.summary", "facts.positions", "facts.allocations", "facts.cash_context", "coverage", "semantics"),
        optional_sections=(
            "facts.contributions",
            "facts.unallocated_contributions",
            "facts.other_period_effects",
            "states",
            "technical",
            "events",
            "domain_notes",
        ),
        applicability_code="portfolio_accessible",
        frontend_response_contract_id="portfolio.portfolio_description",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=False,
        compact_selection=compact_selection(
            "largest_nav",
            10,
            metric="nav",
            ordering="descending",
        ),
        technical_by_detail=_asset_technical(
            TechnicalDepth.NONE,
            TechnicalDepth.STANDARD_SUMMARY,
            TechnicalDepth.SAMPLED_STANDARD,
        ),
    ),
)
