"""Broker-domain financial `ComponentSpec` builders (Phase 0 AI Export refinement, workstream E1).

Real replacement builders for the eight frozen non-technical Broker component
IDs (`broker.summary`, `broker.positions`, `broker.allocation_concentration`,
`broker.provenance`, `broker.performance`, `broker.flows_income_costs`,
`broker.reconciliation`, `broker.fifo_lots`) - see `backend.app.services.
ai_export.components.catalog` for the frozen `component_id`/domain/dependency/
period-behavior wiring these mirror exactly, and `backend.app.services.
ai_export.components.payloads.portfolio_broker` for the shared payload row
models, pure mapping helpers and domain-neutral `BuildContext` resource-loading
helpers this module builds on (shared 1:1 with
`backend.app.services.ai_export.components.portfolio_financial` so no
financial formula or payload shape is duplicated between the two domains).

This module deliberately does **not** touch `components/catalog.py`: it is a
standalone, importable set of real `ComponentSpec`s ready to replace the
fail-closed placeholders there once a later integration step wires them in.

A Broker `BuildScope` always carries exactly one `broker_id` with
`broker_scope == (broker_id,)` (enforced by `BuildScope.__post_init__`), so
every builder here is inherently single-broker scoped - no additional broker
filtering logic is needed beyond what `BuildScope` already guarantees.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date as Date
from decimal import Decimal

from pydantic import Field

from backend.app.db.models import Asset
from backend.app.schemas.common import Currency, CurrencyCode, PeriodBoundedModel, SafeDecimal, StrictModel
from backend.app.schemas.portfolio import PortfolioHistoryPoint
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.payloads.portfolio_broker import (
    ContributionRow,
    EffectRow,
    FifoAssetSummaryRow,
    FifoLotRow,
    PerformanceBucketRow,
    PositionRow,
    UnallocatedRow,
    build_fifo_lot_refs,
    build_performance_bucket_rows,
    build_uniform_performance_buckets,
    load_lots_results,
    load_portfolio_report,
    lot_is_eligible,
    map_contribution_row,
    map_effect_row,
    map_fifo_lot_row,
    map_position_row,
    map_unallocated_row,
    performance_path_bucket_count,
    sort_contributions,
    sort_effects,
    sort_fifo_lots,
    sort_positions,
    sort_unallocated,
    summarize_fifo_asset_rows,
)
from backend.app.services.ai_export.components.payloads.portfolio_broker import (
    load_asset_metadata as _load_asset_metadata,
)
from backend.app.services.ai_export.components.resources import BROKER_LOTS_RESULTS_RESOURCE, BROKER_REPORT_RESOURCE
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext

_BROKER_FIFO_ASSET_METADATA_RESOURCE: ResourceKey[Mapping[int, Asset]] = ResourceKey("broker.fifo_asset_metadata", Mapping)


class BrokerComponentScopeError(RuntimeError):
    """Raised when a Broker financial component builder is invoked without a matching `BuildScope`."""


def _require_broker_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise BrokerComponentScopeError("broker financial components require BuildContext.scope")
    if scope.domain is not Domain.BROKER:
        raise BrokerComponentScopeError(f"expected Domain.BROKER scope, got {scope.domain!r}")
    if scope.broker_id is None:
        raise BrokerComponentScopeError("broker financial components require BuildScope.broker_id")
    return scope


async def _load_broker_asset_metadata(context: BuildContext, asset_ids: Sequence[int]) -> Mapping[int, Asset]:
    async def _loader(session):
        return await _load_asset_metadata(session, asset_ids)

    return await context.db_resource(_BROKER_FIFO_ASSET_METADATA_RESOURCE, _loader)


# =============================================================================
# broker.summary
# =============================================================================


class BrokerSummaryPayload(StrictModel):

    broker_id: int
    as_of: Date
    period_start: Date
    target_currency: CurrencyCode
    position_count: int
    net_worth: Currency
    total_invested: Currency
    total_gain_loss: Currency
    total_gain_loss_percent: SafeDecimal
    cash_total: Currency
    cash_balances: list[Currency] = Field(default_factory=list)
    market_value: Currency | None = None
    open_cost_basis: Currency | None = None
    unrealized_gain_loss: Currency | None = None
    total_deposited: Currency | None = None
    total_withdrawn: Currency | None = None
    net_deposited_capital: Currency | None = None
    simple_roi_percent: SafeDecimal
    twrr_percent: SafeDecimal | None = None
    mwrr_annualized_percent: SafeDecimal | None = None
    mwrr_cumulative_percent: SafeDecimal | None = None


async def _build_broker_summary(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerSummaryPayload:
    scope = _require_broker_scope(context)
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    if summary is None:
        raise RuntimeError("broker.summary: PortfolioReportResponse.summary missing despite include_summary=True")
    return BrokerSummaryPayload(
        broker_id=scope.broker_id,
        as_of=scope.snapshot_as_of,
        period_start=scope.period_start,
        target_currency=scope.target_currency,
        position_count=len(summary.holdings),
        net_worth=summary.net_worth,
        total_invested=summary.total_invested,
        total_gain_loss=summary.total_gain_loss,
        total_gain_loss_percent=summary.total_gain_loss_percent,
        cash_total=summary.cash_total,
        cash_balances=list(summary.cash_balances),
        market_value=summary.market_value,
        open_cost_basis=summary.open_cost_basis,
        unrealized_gain_loss=summary.unrealized_gain_loss,
        total_deposited=summary.total_deposited,
        total_withdrawn=summary.total_withdrawn,
        net_deposited_capital=summary.net_deposited_capital,
        simple_roi_percent=summary.simple_roi_percent,
        twrr_percent=summary.twrr_percent,
        mwrr_annualized_percent=summary.mwrr_annualized_percent,
        mwrr_cumulative_percent=summary.mwrr_cumulative_percent,
    )


# =============================================================================
# broker.positions
# =============================================================================


class BrokerPositionsPayload(StrictModel):

    broker_id: int
    as_of: Date
    target_currency: CurrencyCode
    position_count: int
    positions: list[PositionRow] = Field(default_factory=list)


async def _build_broker_positions(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerPositionsPayload:
    scope = _require_broker_scope(context)
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    rows = [] if summary is None else [map_position_row(holding, currency_code=scope.target_currency) for holding in summary.holdings]
    rows = sort_positions(rows)
    return BrokerPositionsPayload(broker_id=scope.broker_id, as_of=scope.snapshot_as_of, target_currency=scope.target_currency, position_count=len(rows), positions=rows)


# =============================================================================
# broker.allocation_concentration (depends on broker.positions)
# =============================================================================


class BrokerAllocationConcentrationPayload(StrictModel):

    broker_id: int
    as_of: Date
    target_currency: CurrencyCode
    position_count: int
    market_value: Currency | None = None
    cash_total: Currency
    cash_balances: list[Currency] = Field(default_factory=list)
    largest_position_weight_percent: SafeDecimal | None = None
    herfindahl_index_points: SafeDecimal | None = Field(
        None,
        description="Sum of squared nav_weight_percent across ALL positions (no top-N truncation); higher = more concentrated. 10000 == fully concentrated in one position.",
    )


def _concentration_metrics(positions: Sequence[PositionRow]) -> tuple[Decimal | None, Decimal | None]:
    """Computes concentration metrics over the *entire* position set - never a top-N subset."""
    weights = [position.nav_weight_percent for position in positions if position.nav_weight_percent is not None]
    if not weights:
        return None, None
    largest = max(abs(weight) for weight in weights)
    herfindahl = sum(weight * weight for weight in weights)
    return largest, herfindahl


async def _build_broker_allocation_concentration(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerAllocationConcentrationPayload:
    scope = _require_broker_scope(context)
    # `dependencies["broker.positions"]` is guaranteed already-built by the frozen
    # catalog wiring; positions are recomputed from the same shared (memoized)
    # PortfolioReportResponse resource rather than reparsed from that envelope.
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    currency_code = scope.target_currency
    if summary is None:
        return BrokerAllocationConcentrationPayload(broker_id=scope.broker_id, as_of=scope.snapshot_as_of, target_currency=currency_code, position_count=0, cash_total=Currency(code=currency_code, amount=Decimal("0")))
    positions = sort_positions([map_position_row(holding, currency_code=currency_code) for holding in summary.holdings])
    largest, herfindahl = _concentration_metrics(positions)
    return BrokerAllocationConcentrationPayload(
        broker_id=scope.broker_id,
        as_of=scope.snapshot_as_of,
        target_currency=currency_code,
        position_count=len(positions),
        market_value=summary.market_value,
        cash_total=summary.cash_total,
        cash_balances=list(summary.cash_balances),
        largest_position_weight_percent=largest,
        herfindahl_index_points=herfindahl,
    )


# =============================================================================
# broker.provenance
# =============================================================================


class ProvenanceNote(StrictModel):

    subject: str
    text: str


class BrokerProvenancePayload(PeriodBoundedModel):

    domain: str
    broker_id: int
    target_currency: CurrencyCode
    engine_source: str
    fifo_methodology: str
    valuation_semantics: str
    notes: list[ProvenanceNote] = Field(default_factory=list)


def _build_broker_provenance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerProvenancePayload:
    scope = _require_broker_scope(context)
    return BrokerProvenancePayload(
        domain="broker",
        broker_id=scope.broker_id,
        target_currency=scope.target_currency,
        period_start=scope.period_start,
        period_end=scope.period_end,
        engine_source="PortfolioCalculationEngine via a single PortfolioService.get_report call per request, scoped to this broker",
        fifo_methodology="FIFO lots are computed at runtime by FifoLotEngine via LotsAnalysisService; never persisted.",
        valuation_semantics="wac_per_unit/original_cost/open_cost_basis are Weighted Average Cost; current_value/current_price/open_value are mark-to-market via the valuation hierarchy (MARKET_PRICE > LAST_TRADE_PRICE > MISSING).",
        notes=[
            ProvenanceNote(subject="currency", text=f"All monetary amounts are expressed in {scope.target_currency}."),
            ProvenanceNote(subject="period", text=f"Period is inclusive [{scope.period_start.isoformat()}, {scope.period_end.isoformat()}]; snapshot_as_of == period_end."),
            ProvenanceNote(subject="scope", text="Scoped to the selected broker only."),
            ProvenanceNote(subject="empty_data", text="An empty broker (no holdings, no lots, no transactions) is valid successfully-built data, not a source failure."),
        ],
    )


# =============================================================================
# broker.performance
# =============================================================================


class BrokerPerformancePayload(PeriodBoundedModel):

    broker_id: int
    target_currency: CurrencyCode
    twrr_percent: SafeDecimal | None = None
    mwrr_annualized_percent: SafeDecimal | None = None
    mwrr_cumulative_percent: SafeDecimal | None = None
    simple_roi_percent: SafeDecimal | None = None
    period_pnl: Currency | None = None
    gross_gains: Currency
    gross_losses: Currency
    path_policy_code: str
    path_value_basis: str
    path_return_basis: str
    target_bucket_count: int
    bucket_count: int
    buckets: list[PerformanceBucketRow] = Field(default_factory=list)
    contributor_count: int
    contributors: list[ContributionRow] = Field(default_factory=list)


def _build_performance_buckets(scope: BuildScope, history: Sequence[PortfolioHistoryPoint]) -> list[PerformanceBucketRow]:
    return list(
        build_performance_bucket_rows(
            history,
            build_uniform_performance_buckets(scope),
            currency_code=scope.target_currency,
        )
    )


async def _build_broker_performance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerPerformancePayload:
    scope = _require_broker_scope(context)
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    contribution = report.positions_contribution
    buckets = _build_performance_buckets(scope, report.history or [])
    contributors = sort_contributions([map_contribution_row(item, currency_code=scope.target_currency) for item in contribution.positions]) if contribution is not None else []
    currency_code = scope.target_currency
    return BrokerPerformancePayload(
        broker_id=scope.broker_id,
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=currency_code,
        twrr_percent=summary.twrr_percent if summary else None,
        mwrr_annualized_percent=summary.mwrr_annualized_percent if summary else None,
        mwrr_cumulative_percent=summary.mwrr_cumulative_percent if summary else None,
        simple_roi_percent=summary.simple_roi_percent if summary else None,
        period_pnl=summary.period_pnl if summary else None,
        gross_gains=Currency(code=currency_code, amount=contribution.gross_gains if contribution else Decimal("0")),
        gross_losses=Currency(code=currency_code, amount=contribution.gross_losses if contribution else Decimal("0")),
        path_policy_code="uniform_calendar_path_v1",
        path_value_basis="nav_value_including_external_flows",
        path_return_basis="historical_twrr",
        target_bucket_count=performance_path_bucket_count(scope.detail_level),
        bucket_count=len(buckets),
        buckets=buckets,
        contributor_count=len(contributors),
        contributors=contributors,
    )


# =============================================================================
# broker.flows_income_costs
# =============================================================================


class BrokerFlowsIncomeCostsPayload(PeriodBoundedModel):

    broker_id: int
    target_currency: CurrencyCode
    total_deposited: Currency | None = None
    total_withdrawn: Currency | None = None
    net_deposited_capital: Currency | None = None
    period_net_flows: Currency | None = None
    period_income: Currency | None = None
    period_fees: Currency | None = None
    period_taxes: Currency | None = None
    period_fees_taxes: Currency | None = None
    unallocated: list[UnallocatedRow] = Field(default_factory=list)
    effects: list[EffectRow] = Field(default_factory=list, description="Income and cost non-position period effects, combined (broker view keeps them together, unlike the split Portfolio flows_income/fees_taxes pair).")


async def _build_broker_flows_income_costs(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerFlowsIncomeCostsPayload:
    scope = _require_broker_scope(context)
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    contribution = report.positions_contribution
    currency_code = scope.target_currency
    unallocated = sort_unallocated([map_unallocated_row(item, currency_code=currency_code) for item in contribution.unallocated]) if contribution is not None else []
    effects = sort_effects([map_effect_row(item, currency_code=currency_code) for item in contribution.other_effects]) if contribution is not None else []
    return BrokerFlowsIncomeCostsPayload(
        broker_id=scope.broker_id,
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=currency_code,
        total_deposited=summary.total_deposited if summary else None,
        total_withdrawn=summary.total_withdrawn if summary else None,
        net_deposited_capital=summary.net_deposited_capital if summary else None,
        period_net_flows=summary.period_net_flows if summary else None,
        period_income=summary.period_income if summary else None,
        period_fees=summary.period_fees if summary else None,
        period_taxes=summary.period_taxes if summary else None,
        period_fees_taxes=summary.period_fees_taxes if summary else None,
        unallocated=unallocated,
        effects=effects,
    )


# =============================================================================
# broker.reconciliation (depends on broker.flows_income_costs)
# =============================================================================


class BrokerReconciliationPayload(PeriodBoundedModel):

    broker_id: int
    target_currency: CurrencyCode
    period_pnl: Currency | None = None
    period_unrealized_gain_loss_delta: Currency | None = None
    period_realized_gain_loss: Currency | None = None
    period_income: Currency | None = None
    period_fees_taxes: Currency | None = None
    period_other_result: Currency | None = None
    reconciled: bool | None = None
    residual: Currency | None = None


async def _build_broker_reconciliation(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerReconciliationPayload:
    scope = _require_broker_scope(context)
    # `dependencies["broker.flows_income_costs"]` is guaranteed already-built by
    # the frozen catalog wiring; reconciliation is validated straight from the
    # shared (memoized) PortfolioReportResponse resource's own engine fields.
    report = await load_portfolio_report(context, scope, BROKER_REPORT_RESOURCE)
    summary = report.summary
    currency_code = scope.target_currency
    reconciled: bool | None = None
    residual: Currency | None = None
    if summary is not None:
        components = (
            summary.period_unrealized_gain_loss_delta,
            summary.period_realized_gain_loss,
            summary.period_income,
            summary.period_fees_taxes,
            summary.period_other_result,
        )
        if summary.period_pnl is not None and all(component is not None for component in components):
            residual_amount = summary.period_pnl.amount - (summary.period_unrealized_gain_loss_delta.amount + summary.period_realized_gain_loss.amount + summary.period_income.amount - summary.period_fees_taxes.amount + summary.period_other_result.amount)
            residual = Currency(code=currency_code, amount=residual_amount)
            reconciled = residual_amount == Decimal("0")
    return BrokerReconciliationPayload(
        broker_id=scope.broker_id,
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=currency_code,
        period_pnl=summary.period_pnl if summary else None,
        period_unrealized_gain_loss_delta=summary.period_unrealized_gain_loss_delta if summary else None,
        period_realized_gain_loss=summary.period_realized_gain_loss if summary else None,
        period_income=summary.period_income if summary else None,
        period_fees_taxes=summary.period_fees_taxes if summary else None,
        period_other_result=summary.period_other_result if summary else None,
        reconciled=reconciled,
        residual=residual,
    )


# =============================================================================
# broker.fifo_summary / broker.fifo_lots
# =============================================================================


async def _broker_fifo_rows(context: BuildContext, scope: BuildScope) -> list[FifoLotRow]:
    currency_code = scope.target_currency
    lots_resource = await load_lots_results(context, scope, BROKER_LOTS_RESULTS_RESOURCE)
    asset_ids = sorted(lots_resource.by_asset_id)
    assets_meta = await _load_broker_asset_metadata(context, asset_ids)
    cutoff = scope.period_start
    eligible_by_asset = {asset_id: [lot for lot in (lots_resource.by_asset_id[asset_id].lots or []) if lot_is_eligible(lot, cutoff=cutoff)] for asset_id in asset_ids}
    lot_refs = build_fifo_lot_refs(eligible_by_asset)
    candidate_pairs: list[tuple[int, FifoLotRow]] = []
    for asset_id in asset_ids:
        asset = assets_meta.get(asset_id)
        asset_name = str(getattr(asset, "display_name", None) or f"Asset {asset_id}")
        asset_ticker = getattr(asset, "identifier_ticker", None)
        for lot in eligible_by_asset[asset_id]:
            row = map_fifo_lot_row(
                lot,
                lot_ref=lot_refs[lot.lot_id],
                asset_id=asset_id,
                currency_code=currency_code,
                asset_name=asset_name,
                asset_ticker=asset_ticker,
            )
            candidate_pairs.append((lot.lot_id, row))
    return sort_fifo_lots(candidate_pairs)


class BrokerFifoSummaryPayload(PeriodBoundedModel):

    broker_id: int
    target_currency: CurrencyCode
    cost_allocation_semantics: str
    asset_count: int
    total_open_lots: int
    total_partial_lots: int
    total_closed_lots: int
    total_residual_cost_basis: Currency
    assets: list[FifoAssetSummaryRow] = Field(default_factory=list)


async def _build_broker_fifo_summary(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerFifoSummaryPayload:
    scope = _require_broker_scope(context)
    lot_rows = await _broker_fifo_rows(context, scope)
    grouped: dict[int, list[FifoLotRow]] = {}
    for row in lot_rows:
        grouped.setdefault(row.asset_id, []).append(row)
    rows = [summarize_fifo_asset_rows(grouped[asset_id]) for asset_id in sorted(grouped)]
    return BrokerFifoSummaryPayload(
        broker_id=scope.broker_id,
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=scope.target_currency,
        cost_allocation_semantics="Fees and taxes are amounts deterministically allocated to FIFO lots. Broker-level unallocated costs are excluded and must be read from broker flows/cost-efficiency evidence.",
        asset_count=len(rows),
        total_open_lots=sum(row.open_lot_count for row in rows),
        total_partial_lots=sum(row.partial_lot_count for row in rows),
        total_closed_lots=sum(row.closed_lot_count for row in rows),
        total_residual_cost_basis=Currency(
            code=scope.target_currency,
            amount=sum((row.residual_cost_basis.amount for row in rows), Decimal("0")),
        ),
        assets=rows,
    )


class BrokerFifoLotsPayload(PeriodBoundedModel):

    broker_id: int
    target_currency: CurrencyCode
    cost_allocation_semantics: str
    lot_count: int
    lots: list[FifoLotRow] = Field(default_factory=list)


async def _build_broker_fifo_lots(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> BrokerFifoLotsPayload:
    scope = _require_broker_scope(context)
    rows = await _broker_fifo_rows(context, scope)
    return BrokerFifoLotsPayload(
        broker_id=scope.broker_id,
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=scope.target_currency,
        cost_allocation_semantics="Lot fees and taxes include only deterministically allocated costs. Broker-level unallocated costs are excluded and must not be interpreted as recorded zero.",
        lot_count=len(rows),
        lots=rows,
    )


# =============================================================================
# ComponentSpec wiring (mirrors backend.app.services.ai_export.components.catalog exactly)
# =============================================================================

BROKER_SUMMARY_COMPONENT = ComponentSpec(
    component_id="broker.summary",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerSummaryPayload,
    builder=_build_broker_summary,
    period_behavior=PeriodBehavior.AS_OF,
)

BROKER_POSITIONS_COMPONENT = ComponentSpec(
    component_id="broker.positions",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerPositionsPayload,
    builder=_build_broker_positions,
    period_behavior=PeriodBehavior.AS_OF,
)

BROKER_ALLOCATION_CONCENTRATION_COMPONENT = ComponentSpec(
    component_id="broker.allocation_concentration",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerAllocationConcentrationPayload,
    builder=_build_broker_allocation_concentration,
    dependencies=("broker.positions",),
    period_behavior=PeriodBehavior.AS_OF,
)

BROKER_PROVENANCE_COMPONENT = ComponentSpec(
    component_id="broker.provenance",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerProvenancePayload,
    builder=_build_broker_provenance,
    period_behavior=PeriodBehavior.NONE,
)

BROKER_PERFORMANCE_COMPONENT = ComponentSpec(
    component_id="broker.performance",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerPerformancePayload,
    builder=_build_broker_performance,
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_FLOWS_INCOME_COSTS_COMPONENT = ComponentSpec(
    component_id="broker.flows_income_costs",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerFlowsIncomeCostsPayload,
    builder=_build_broker_flows_income_costs,
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_RECONCILIATION_COMPONENT = ComponentSpec(
    component_id="broker.reconciliation",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerReconciliationPayload,
    builder=_build_broker_reconciliation,
    dependencies=("broker.flows_income_costs",),
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_FIFO_SUMMARY_COMPONENT = ComponentSpec(
    component_id="broker.fifo_summary",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerFifoSummaryPayload,
    builder=_build_broker_fifo_summary,
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_FIFO_LOTS_COMPONENT = ComponentSpec(
    component_id="broker.fifo_lots",
    version=1,
    domains=frozenset({Domain.BROKER}),
    output_model=BrokerFifoLotsPayload,
    builder=_build_broker_fifo_lots,
    dependencies=("broker.fifo_summary",),
    period_behavior=PeriodBehavior.WINDOWED,
)

BROKER_FINANCIAL_COMPONENTS: tuple[ComponentSpec, ...] = (
    BROKER_SUMMARY_COMPONENT,
    BROKER_POSITIONS_COMPONENT,
    BROKER_ALLOCATION_CONCENTRATION_COMPONENT,
    BROKER_PROVENANCE_COMPONENT,
    BROKER_PERFORMANCE_COMPONENT,
    BROKER_FLOWS_INCOME_COSTS_COMPONENT,
    BROKER_RECONCILIATION_COMPONENT,
    BROKER_FIFO_SUMMARY_COMPONENT,
    BROKER_FIFO_LOTS_COMPONENT,
)

__all__ = [
    "BROKER_ALLOCATION_CONCENTRATION_COMPONENT",
    "BROKER_FIFO_LOTS_COMPONENT",
    "BROKER_FIFO_SUMMARY_COMPONENT",
    "BROKER_FINANCIAL_COMPONENTS",
    "BROKER_FLOWS_INCOME_COSTS_COMPONENT",
    "BROKER_PERFORMANCE_COMPONENT",
    "BROKER_POSITIONS_COMPONENT",
    "BROKER_PROVENANCE_COMPONENT",
    "BROKER_RECONCILIATION_COMPONENT",
    "BROKER_SUMMARY_COMPONENT",
    "BrokerAllocationConcentrationPayload",
    "BrokerComponentScopeError",
    "BrokerFifoLotsPayload",
    "BrokerFifoSummaryPayload",
    "BrokerFlowsIncomeCostsPayload",
    "BrokerPerformancePayload",
    "BrokerPositionsPayload",
    "BrokerProvenancePayload",
    "BrokerReconciliationPayload",
    "BrokerSummaryPayload",
    "ProvenanceNote",
]
