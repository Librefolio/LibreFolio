"""Broker AI Export task manifests."""

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
    return technical_matrix(
        compact,
        technical_detail(
            AiExportDetailLevel.STANDARD,
            standard_depth,
            ASSET_STANDARD_BUNDLE,
        ),
        technical_detail(
            AiExportDetailLevel.FULL,
            full_depth,
            ASSET_FULL_BUNDLE,
        ),
    )


BROKER_TASK_SPECS = (
    TaskSpec(
        domain=AiExportDomain.BROKER,
        task=AiExportTask.BROKER_REVIEW,
        required_sections=("facts.summary", "facts.positions", "coverage", "semantics"),
        optional_sections=(
            "facts.contributions",
            "facts.unallocated_contributions",
            "facts.other_period_effects",
            "facts.concentration",
            "facts.latest_transaction",
            "facts.fifo_summary",
            "states",
            "technical",
            "events",
            "domain_notes",
        ),
        applicability_code="broker_accessible_via_broker_user_access",
        frontend_response_contract_id="broker.broker_review",
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
            TechnicalDepth.BREADTH_ONLY,
            TechnicalDepth.STANDARD,
            TechnicalDepth.FULL,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.BROKER,
        task=AiExportTask.BROKER_COST_EFFICIENCY,
        required_sections=(
            "facts.summary",
            "facts.positions",
            "facts.contributions",
            "facts.unallocated_contributions",
            "facts.other_period_effects",
            "coverage",
            "semantics",
        ),
        optional_sections=("facts.latest_transaction", "states", "technical", "events", "domain_notes"),
        applicability_code="broker_accessible_via_broker_user_access",
        frontend_response_contract_id="broker.broker_cost_efficiency",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=False,
        compact_selection=compact_selection(
            "largest_absolute_period_fees_taxes",
            10,
            metric="abs_period_fees_taxes_amount",
            ordering="descending",
        ),
        technical_by_detail=_asset_technical(
            TechnicalDepth.NONE,
            TechnicalDepth.LATEST_STATES,
            TechnicalDepth.SAMPLED_STANDARD,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.BROKER,
        task=AiExportTask.BROKER_CONCENTRATION_CONTEXT,
        required_sections=("facts.summary", "facts.positions", "facts.concentration", "coverage", "semantics"),
        optional_sections=("states", "technical", "events", "domain_notes"),
        applicability_code="broker_accessible_via_broker_user_access",
        frontend_response_contract_id="broker.broker_concentration_context",
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
            TechnicalDepth.BREADTH_ONLY,
            TechnicalDepth.STANDARD,
            TechnicalDepth.FULL,
        ),
    ),
    TaskSpec(
        domain=AiExportDomain.BROKER,
        task=AiExportTask.BROKER_FIFO_LOT_REVIEW,
        required_sections=("facts.summary", "facts.positions", "facts.fifo_summary", "coverage", "semantics"),
        optional_sections=("states", "technical", "events", "domain_notes"),
        applicability_code="broker_accessible_via_broker_user_access",
        frontend_response_contract_id="broker.broker_fifo_lot_review",
        frontend_response_contract_version=1,
        supports_user_notes=True,
        supports_web_research=False,
        compact_selection=compact_selection(
            "largest_residual_cost_basis",
            10,
            metric="residual_cost_basis",
            ordering="descending",
        ),
        technical_by_detail=_asset_technical(
            TechnicalDepth.NONE,
            TechnicalDepth.LATEST_STATES,
            TechnicalDepth.SAMPLED_STANDARD,
        ),
    ),
)
