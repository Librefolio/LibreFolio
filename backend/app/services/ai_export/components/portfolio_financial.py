"""Portfolio-domain financial `ComponentSpec` builders (Phase 0 AI Export refinement, workstream E1).

Real replacement builders for the ten frozen non-technical Portfolio component
IDs (`portfolio.summary`, `portfolio.positions`, `portfolio.allocations_cash`,
`portfolio.provenance`, `portfolio.performance`, `portfolio.flows_income`,
`portfolio.fees_taxes`, `portfolio.reconciliation`, `portfolio.fifo_summary`,
`portfolio.fifo_lots`) - see `backend.app.services.ai_export.components.catalog`
for the frozen `component_id`/domain/dependency/period-behavior wiring these
mirror exactly (same IDs, same declared dependencies), and
`backend.app.services.ai_export.components.payloads.portfolio_broker` for the
shared payload row models, pure mapping helpers and domain-neutral
`BuildContext` resource-loading helpers this module builds on.

This module deliberately does **not** touch `components/catalog.py`: it is a
standalone, importable set of real `ComponentSpec`s ready to replace the
fail-closed placeholders there once a later integration step wires them in.

Every builder here:
- reads `BuildContext.scope`/`bucket_plan` (never re-derives its own period or
  bucketing logic - see `backend.app.services.ai_export.dependencies.
  build_bucket_plan_for_scope` and `backend.app.services.ai_export.temporal.
  plan.BucketPlan`);
- loads its data through `BuildContext.db_resource`, so the underlying
  `PortfolioService.get_report`/`LotsAnalysisService.get_lots_analysis` calls
  are memoized once per request even though several components need the same
  report or lots data;
- lets any loader/service exception propagate (no broad `except Exception:
  return success` fallback) so `BuildContext.resolve` can apply the
  required/optional semantics documented in `backend.app.services.ai_export.
  dependencies`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date as Date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.db.models import Asset, Broker
from backend.app.schemas.common import Currency, SafeDecimal
from backend.app.schemas.portfolio import PortfolioHistoryPoint
from backend.app.services.ai_export.components.envelope import SectionEnvelope
from backend.app.services.ai_export.components.payloads.portfolio_broker import (
    AllocationSlice,
    ContributionRow,
    EffectRow,
    FifoAssetSummaryRow,
    FifoLotRow,
    PerformanceBucketRow,
    PositionRow,
    UnallocatedRow,
    has_nonzero_open_lot,
    load_lots_results,
    load_portfolio_report,
    lot_is_eligible,
    lot_residual_cost_basis,
    lot_status,
    map_allocation_slice,
    map_contribution_row,
    map_effect_row,
    map_fifo_lot_row,
    map_position_row,
    map_unallocated_row,
    sort_contributions,
    sort_effects,
    sort_fifo_lots,
    sort_positions,
    sort_unallocated,
)
from backend.app.services.ai_export.components.payloads.portfolio_broker import (
    load_asset_metadata as _load_asset_metadata,
)
from backend.app.services.ai_export.components.payloads.portfolio_broker import (
    load_broker_metadata as _load_broker_metadata,
)
from backend.app.services.ai_export.components.resources import PORTFOLIO_LOTS_RESULTS_RESOURCE, PORTFOLIO_REPORT_RESOURCE
from backend.app.services.ai_export.components.spec import ComponentSpec
from backend.app.services.ai_export.components.types import BuildScope, Domain, PeriodBehavior, ResourceKey
from backend.app.services.ai_export.dependencies import BuildContext

_PORTFOLIO_FIFO_ASSET_METADATA_RESOURCE: ResourceKey[Mapping[int, Asset]] = ResourceKey("portfolio.fifo_asset_metadata", Mapping)
_PORTFOLIO_FIFO_BROKER_METADATA_RESOURCE: ResourceKey[Mapping[int, Broker]] = ResourceKey("portfolio.fifo_broker_metadata", Mapping)


class PortfolioComponentScopeError(RuntimeError):
    """Raised when a Portfolio financial component builder is invoked without a matching `BuildScope`."""


def _require_portfolio_scope(context: BuildContext) -> BuildScope:
    scope = context.scope
    if scope is None:
        raise PortfolioComponentScopeError("portfolio financial components require BuildContext.scope")
    if scope.domain is not Domain.PORTFOLIO:
        raise PortfolioComponentScopeError(f"expected Domain.PORTFOLIO scope, got {scope.domain!r}")
    return scope


async def _load_portfolio_asset_metadata(context: BuildContext, asset_ids: Sequence[int]) -> Mapping[int, Asset]:
    async def _loader(session):
        return await _load_asset_metadata(session, asset_ids)

    return await context.db_resource(_PORTFOLIO_FIFO_ASSET_METADATA_RESOURCE, _loader)


async def _load_portfolio_broker_metadata(context: BuildContext, broker_ids: Sequence[int]) -> Mapping[int, Broker]:
    async def _loader(session):
        return await _load_broker_metadata(session, broker_ids)

    return await context.db_resource(_PORTFOLIO_FIFO_BROKER_METADATA_RESOURCE, _loader)


# =============================================================================
# portfolio.summary
# =============================================================================


class PortfolioSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: Date
    period_start: Date
    target_currency: str
    position_count: int
    broker_count: int
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


async def _build_portfolio_summary(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioSummaryPayload:
    scope = _require_portfolio_scope(context)
    report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
    summary = report.summary
    if summary is None:
        raise RuntimeError("portfolio.summary: PortfolioReportResponse.summary missing despite include_summary=True")
    return PortfolioSummaryPayload(
        as_of=scope.snapshot_as_of,
        period_start=scope.period_start,
        target_currency=scope.target_currency,
        position_count=len(summary.holdings),
        broker_count=len({holding.broker_id for holding in summary.holdings if holding.broker_id is not None}),
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
# portfolio.positions
# =============================================================================


class PortfolioPositionsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: Date
    target_currency: str
    position_count: int
    positions: list[PositionRow] = Field(default_factory=list)


async def _build_portfolio_positions(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioPositionsPayload:
    scope = _require_portfolio_scope(context)
    report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
    summary = report.summary
    rows = [] if summary is None else [map_position_row(holding, currency_code=scope.target_currency) for holding in summary.holdings]
    rows = sort_positions(rows)
    return PortfolioPositionsPayload(as_of=scope.snapshot_as_of, target_currency=scope.target_currency, position_count=len(rows), positions=rows)


# =============================================================================
# portfolio.allocations_cash (depends on portfolio.positions)
# =============================================================================


class PortfolioAllocationsCashPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: Date
    target_currency: str
    by_type: list[AllocationSlice] = Field(default_factory=list)
    by_sector: list[AllocationSlice] = Field(default_factory=list)
    by_geography: list[AllocationSlice] = Field(default_factory=list)
    cash_total: Currency
    cash_balances: list[Currency] = Field(default_factory=list)
    market_value: Currency | None = None


async def _build_portfolio_allocations_cash(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioAllocationsCashPayload:
    scope = _require_portfolio_scope(context)
    # `dependencies["portfolio.positions"]` is guaranteed already-built by the frozen
    # catalog wiring; allocations are recomputed from the same shared (memoized)
    # PortfolioReportResponse resource rather than re-parsing the dependency envelope.
    report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
    summary = report.summary
    currency_code = scope.target_currency
    if summary is None:
        return PortfolioAllocationsCashPayload(as_of=scope.snapshot_as_of, target_currency=currency_code, cash_total=Currency(code=currency_code, amount=Decimal("0")))
    return PortfolioAllocationsCashPayload(
        as_of=scope.snapshot_as_of,
        target_currency=currency_code,
        by_type=[map_allocation_slice(item, currency_code=currency_code) for item in summary.allocation_by_type],
        by_sector=[map_allocation_slice(item, currency_code=currency_code) for item in summary.allocation_by_sector],
        by_geography=[map_allocation_slice(item, currency_code=currency_code) for item in summary.allocation_by_geography],
        cash_total=summary.cash_total,
        cash_balances=list(summary.cash_balances),
        market_value=summary.market_value,
    )


# =============================================================================
# portfolio.provenance
# =============================================================================


class ProvenanceNote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    text: str


class PortfolioProvenancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: str
    target_currency: str
    period_start: Date
    period_end: Date
    broker_scope: list[int] = Field(default_factory=list)
    engine_source: str
    fifo_methodology: str
    valuation_semantics: str
    notes: list[ProvenanceNote] = Field(default_factory=list)


def _build_portfolio_provenance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioProvenancePayload:
    scope = _require_portfolio_scope(context)
    return PortfolioProvenancePayload(
        domain="portfolio",
        target_currency=scope.target_currency,
        period_start=scope.period_start,
        period_end=scope.period_end,
        broker_scope=list(scope.broker_scope),
        engine_source="PortfolioCalculationEngine via a single PortfolioService.get_report call per request",
        fifo_methodology="FIFO lots are computed at runtime by FifoLotEngine via LotsAnalysisService; never persisted.",
        valuation_semantics="wac_per_unit/original_cost/open_cost_basis are Weighted Average Cost; current_value/current_price/open_value are mark-to-market via the valuation hierarchy (MARKET_PRICE > LAST_BUY_PRICE > LAST_SEED_COST).",
        notes=[
            ProvenanceNote(subject="currency", text=f"All monetary amounts are expressed in {scope.target_currency}."),
            ProvenanceNote(subject="period", text=f"Period is inclusive [{scope.period_start.isoformat()}, {scope.period_end.isoformat()}]; snapshot_as_of == period_end."),
            ProvenanceNote(subject="empty_data", text="An empty portfolio (no holdings, no lots, no transactions) is valid successfully-built data, not a source failure."),
        ],
    )


# =============================================================================
# portfolio.performance
# =============================================================================


class PortfolioPerformancePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: Date
    period_end: Date
    target_currency: str
    twrr_percent: SafeDecimal | None = None
    mwrr_annualized_percent: SafeDecimal | None = None
    mwrr_cumulative_percent: SafeDecimal | None = None
    simple_roi_percent: SafeDecimal | None = None
    period_pnl: Currency | None = None
    gross_gains: Currency
    gross_losses: Currency
    bucket_count: int
    buckets: list[PerformanceBucketRow] = Field(default_factory=list)
    contributor_count: int
    contributors: list[ContributionRow] = Field(default_factory=list)


def _build_performance_buckets(context: BuildContext, scope: BuildScope, history: Sequence[PortfolioHistoryPoint]) -> list[PerformanceBucketRow]:
    bucket_plan = context.bucket_plan
    if bucket_plan is None:
        raise PortfolioComponentScopeError("portfolio.performance requires BuildContext.bucket_plan")
    currency_code = scope.target_currency
    rows: list[PerformanceBucketRow] = []
    for bucket in bucket_plan.buckets:
        points = sorted((point for point in history if bucket.start_date <= point.date <= bucket.end_date), key=lambda point: point.date)
        if not points:
            rows.append(PerformanceBucketRow(index=bucket.index, start_date=bucket.start_date, end_date=bucket.end_date, has_data=False))
            continue
        start_point, end_point = points[0], points[-1]
        start_value = start_point.nav_value.amount
        end_value = end_point.nav_value.amount
        net_external_flow = end_point.capital_baseline.amount - start_point.capital_baseline.amount
        period_pnl = end_point.total_pnl.amount - start_point.total_pnl.amount
        reconciliation_diff = (end_value - start_value) - (net_external_flow + period_pnl)
        # A simple bucket return is only reported when the bucket carries no external
        # flow: with a flow present, end-start no longer isolates a return without
        # re-deriving TWRR (an engine formula this builder must not duplicate).
        return_percent = (period_pnl / abs(start_value)) if net_external_flow == 0 and start_value != 0 else None
        rows.append(
            PerformanceBucketRow(
                index=bucket.index,
                start_date=bucket.start_date,
                end_date=bucket.end_date,
                has_data=True,
                start_value=Currency(code=currency_code, amount=start_value),
                end_value=Currency(code=currency_code, amount=end_value),
                min_value=Currency(code=currency_code, amount=min(point.nav_value.amount for point in points)),
                max_value=Currency(code=currency_code, amount=max(point.nav_value.amount for point in points)),
                net_external_flow=Currency(code=currency_code, amount=net_external_flow),
                period_pnl=Currency(code=currency_code, amount=period_pnl),
                return_percent=return_percent,
                reconciliation_diff=Currency(code=currency_code, amount=reconciliation_diff),
            )
        )
    return rows


async def _build_portfolio_performance(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioPerformancePayload:
    scope = _require_portfolio_scope(context)
    report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
    summary = report.summary
    contribution = report.positions_contribution
    buckets = _build_performance_buckets(context, scope, report.history or [])
    contributors = sort_contributions([map_contribution_row(item, currency_code=scope.target_currency) for item in contribution.positions]) if contribution is not None else []
    currency_code = scope.target_currency
    return PortfolioPerformancePayload(
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
        bucket_count=len(buckets),
        buckets=buckets,
        contributor_count=len(contributors),
        contributors=contributors,
    )


# =============================================================================
# portfolio.flows_income
# =============================================================================


class PortfolioFlowsIncomePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: Date
    period_end: Date
    target_currency: str
    total_deposited: Currency | None = None
    total_withdrawn: Currency | None = None
    net_deposited_capital: Currency | None = None
    period_net_flows: Currency | None = None
    period_income: Currency | None = None
    unallocated: list[UnallocatedRow] = Field(default_factory=list)
    income_effects: list[EffectRow] = Field(default_factory=list)


async def _build_portfolio_flows_income(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioFlowsIncomePayload:
    scope = _require_portfolio_scope(context)
    report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
    summary = report.summary
    contribution = report.positions_contribution
    currency_code = scope.target_currency
    unallocated = sort_unallocated([map_unallocated_row(item, currency_code=currency_code) for item in contribution.unallocated]) if contribution is not None else []
    income_effects = sort_effects([map_effect_row(item, currency_code=currency_code) for item in contribution.other_effects if item.category == "Income"]) if contribution is not None else []
    return PortfolioFlowsIncomePayload(
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=currency_code,
        total_deposited=summary.total_deposited if summary else None,
        total_withdrawn=summary.total_withdrawn if summary else None,
        net_deposited_capital=summary.net_deposited_capital if summary else None,
        period_net_flows=summary.period_net_flows if summary else None,
        period_income=summary.period_income if summary else None,
        unallocated=unallocated,
        income_effects=income_effects,
    )


# =============================================================================
# portfolio.fees_taxes
# =============================================================================


class PortfolioFeesTaxesPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: Date
    period_end: Date
    target_currency: str
    period_fees: Currency | None = None
    period_taxes: Currency | None = None
    period_fees_taxes: Currency | None = None
    unallocated: list[UnallocatedRow] = Field(default_factory=list)
    cost_effects: list[EffectRow] = Field(default_factory=list)


async def _build_portfolio_fees_taxes(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioFeesTaxesPayload:
    scope = _require_portfolio_scope(context)
    report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
    summary = report.summary
    contribution = report.positions_contribution
    currency_code = scope.target_currency
    unallocated = sort_unallocated([map_unallocated_row(item, currency_code=currency_code) for item in contribution.unallocated]) if contribution is not None else []
    cost_effects = sort_effects([map_effect_row(item, currency_code=currency_code) for item in contribution.other_effects if item.category == "Cost"]) if contribution is not None else []
    return PortfolioFeesTaxesPayload(
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=currency_code,
        period_fees=summary.period_fees if summary else None,
        period_taxes=summary.period_taxes if summary else None,
        period_fees_taxes=summary.period_fees_taxes if summary else None,
        unallocated=unallocated,
        cost_effects=cost_effects,
    )


# =============================================================================
# portfolio.reconciliation (depends on portfolio.flows_income)
# =============================================================================


class PortfolioReconciliationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: Date
    period_end: Date
    target_currency: str
    period_pnl: Currency | None = None
    period_unrealized_gain_loss_delta: Currency | None = None
    period_realized_gain_loss: Currency | None = None
    period_income: Currency | None = None
    period_fees_taxes: Currency | None = None
    period_other_result: Currency | None = None
    reconciled: bool | None = None
    residual: Currency | None = None


async def _build_portfolio_reconciliation(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioReconciliationPayload:
    scope = _require_portfolio_scope(context)
    # `dependencies["portfolio.flows_income"]` is guaranteed already-built by the
    # frozen catalog wiring; reconciliation is validated straight from the shared
    # (memoized) PortfolioReportResponse resource's own engine fields.
    report = await load_portfolio_report(context, scope, PORTFOLIO_REPORT_RESOURCE)
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
    return PortfolioReconciliationPayload(
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
# portfolio.fifo_summary
# =============================================================================


class PortfolioFifoSummaryPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: Date
    period_end: Date
    target_currency: str
    asset_count: int
    total_open_lots: int
    total_partial_lots: int
    total_closed_lots: int
    total_residual_cost_basis: Currency
    assets: list[FifoAssetSummaryRow] = Field(default_factory=list)


async def _build_portfolio_fifo_summary(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioFifoSummaryPayload:
    scope = _require_portfolio_scope(context)
    currency_code = scope.target_currency
    lots_resource = await load_lots_results(context, scope, PORTFOLIO_LOTS_RESULTS_RESOURCE)
    asset_ids = sorted(lots_resource.by_asset_id)
    assets_meta = await _load_portfolio_asset_metadata(context, asset_ids)
    cutoff = scope.period_start

    rows: list[FifoAssetSummaryRow] = []
    total_open = total_partial = total_closed = 0
    total_residual = Decimal("0")
    for asset_id in asset_ids:
        response = lots_resource.by_asset_id[asset_id]
        lots = [lot for lot in (response.lots or []) if lot_is_eligible(lot, cutoff=cutoff)]
        open_count = sum(1 for lot in lots if lot_status(lot).value == "open")
        partial_count = sum(1 for lot in lots if lot_status(lot).value == "partial")
        closed_count = sum(1 for lot in lots if lot_status(lot).value == "closed")
        residual = sum((lot_residual_cost_basis(lot) for lot in lots), start=Decimal("0"))
        total_open += open_count
        total_partial += partial_count
        total_closed += closed_count
        total_residual += residual
        asset = assets_meta.get(asset_id)
        rows.append(
            FifoAssetSummaryRow(
                asset_id=asset_id,
                asset_name=str(getattr(asset, "display_name", None) or f"Asset {asset_id}"),
                asset_ticker=getattr(asset, "identifier_ticker", None),
                open_lot_count=open_count,
                partial_lot_count=partial_count,
                closed_lot_count=closed_count,
                has_open_position=has_nonzero_open_lot(lots),
                residual_cost_basis=Currency(code=currency_code, amount=residual),
            )
        )
    return PortfolioFifoSummaryPayload(
        period_start=scope.period_start,
        period_end=scope.period_end,
        target_currency=currency_code,
        asset_count=len(rows),
        total_open_lots=total_open,
        total_partial_lots=total_partial,
        total_closed_lots=total_closed,
        total_residual_cost_basis=Currency(code=currency_code, amount=total_residual),
        assets=rows,
    )


# =============================================================================
# portfolio.fifo_lots (depends on portfolio.fifo_summary)
# =============================================================================


class PortfolioFifoLotsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period_start: Date
    period_end: Date
    target_currency: str
    lot_count: int
    lots: list[FifoLotRow] = Field(default_factory=list)


async def _build_portfolio_fifo_lots(context: BuildContext, dependencies: Mapping[str, SectionEnvelope]) -> PortfolioFifoLotsPayload:
    scope = _require_portfolio_scope(context)
    currency_code = scope.target_currency
    # `dependencies["portfolio.fifo_summary"]` is guaranteed already-built by the
    # frozen catalog wiring; lots are (re)read from the same memoized
    # PORTFOLIO_LOTS_RESULTS_RESOURCE rather than reparsed from that envelope.
    lots_resource = await load_lots_results(context, scope, PORTFOLIO_LOTS_RESULTS_RESOURCE)
    asset_ids = sorted(lots_resource.by_asset_id)
    assets_meta = await _load_portfolio_asset_metadata(context, asset_ids)
    cutoff = scope.period_start

    eligible_by_asset: dict[int, list] = {}
    broker_ids_needed: set[int] = set()
    for asset_id in asset_ids:
        response = lots_resource.by_asset_id[asset_id]
        lots = [lot for lot in (response.lots or []) if lot_is_eligible(lot, cutoff=cutoff)]
        eligible_by_asset[asset_id] = lots
        broker_ids_needed.update(lot.opening_broker_id for lot in lots)
    brokers_meta = await _load_portfolio_broker_metadata(context, sorted(broker_ids_needed))

    candidate_pairs: list[tuple[int, FifoLotRow]] = []
    for asset_id in asset_ids:
        asset = assets_meta.get(asset_id)
        asset_name = str(getattr(asset, "display_name", None) or f"Asset {asset_id}")
        asset_ticker = getattr(asset, "identifier_ticker", None)
        for lot in eligible_by_asset[asset_id]:
            broker = brokers_meta.get(lot.opening_broker_id)
            row = map_fifo_lot_row(
                lot,
                asset_id=asset_id,
                currency_code=currency_code,
                asset_name=asset_name,
                asset_ticker=asset_ticker,
                opening_broker_name=getattr(broker, "name", None),
            )
            candidate_pairs.append((lot.lot_id, row))
    rows = sort_fifo_lots(candidate_pairs)
    return PortfolioFifoLotsPayload(period_start=scope.period_start, period_end=scope.period_end, target_currency=currency_code, lot_count=len(rows), lots=rows)


# =============================================================================
# ComponentSpec wiring (mirrors backend.app.services.ai_export.components.catalog exactly)
# =============================================================================

PORTFOLIO_SUMMARY_COMPONENT = ComponentSpec(
    component_id="portfolio.summary",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioSummaryPayload,
    builder=_build_portfolio_summary,
    period_behavior=PeriodBehavior.AS_OF,
)

PORTFOLIO_POSITIONS_COMPONENT = ComponentSpec(
    component_id="portfolio.positions",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioPositionsPayload,
    builder=_build_portfolio_positions,
    period_behavior=PeriodBehavior.AS_OF,
)

PORTFOLIO_ALLOCATIONS_CASH_COMPONENT = ComponentSpec(
    component_id="portfolio.allocations_cash",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioAllocationsCashPayload,
    builder=_build_portfolio_allocations_cash,
    dependencies=("portfolio.positions",),
    period_behavior=PeriodBehavior.AS_OF,
)

PORTFOLIO_PROVENANCE_COMPONENT = ComponentSpec(
    component_id="portfolio.provenance",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioProvenancePayload,
    builder=_build_portfolio_provenance,
    period_behavior=PeriodBehavior.NONE,
)

PORTFOLIO_PERFORMANCE_COMPONENT = ComponentSpec(
    component_id="portfolio.performance",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioPerformancePayload,
    builder=_build_portfolio_performance,
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_FLOWS_INCOME_COMPONENT = ComponentSpec(
    component_id="portfolio.flows_income",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioFlowsIncomePayload,
    builder=_build_portfolio_flows_income,
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_FEES_TAXES_COMPONENT = ComponentSpec(
    component_id="portfolio.fees_taxes",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioFeesTaxesPayload,
    builder=_build_portfolio_fees_taxes,
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_RECONCILIATION_COMPONENT = ComponentSpec(
    component_id="portfolio.reconciliation",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioReconciliationPayload,
    builder=_build_portfolio_reconciliation,
    dependencies=("portfolio.flows_income",),
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_FIFO_SUMMARY_COMPONENT = ComponentSpec(
    component_id="portfolio.fifo_summary",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioFifoSummaryPayload,
    builder=_build_portfolio_fifo_summary,
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_FIFO_LOTS_COMPONENT = ComponentSpec(
    component_id="portfolio.fifo_lots",
    version=1,
    domains=frozenset({Domain.PORTFOLIO}),
    output_model=PortfolioFifoLotsPayload,
    builder=_build_portfolio_fifo_lots,
    dependencies=("portfolio.fifo_summary",),
    period_behavior=PeriodBehavior.WINDOWED,
)

PORTFOLIO_FINANCIAL_COMPONENTS: tuple[ComponentSpec, ...] = (
    PORTFOLIO_SUMMARY_COMPONENT,
    PORTFOLIO_POSITIONS_COMPONENT,
    PORTFOLIO_ALLOCATIONS_CASH_COMPONENT,
    PORTFOLIO_PROVENANCE_COMPONENT,
    PORTFOLIO_PERFORMANCE_COMPONENT,
    PORTFOLIO_FLOWS_INCOME_COMPONENT,
    PORTFOLIO_FEES_TAXES_COMPONENT,
    PORTFOLIO_RECONCILIATION_COMPONENT,
    PORTFOLIO_FIFO_SUMMARY_COMPONENT,
    PORTFOLIO_FIFO_LOTS_COMPONENT,
)

__all__ = [
    "PORTFOLIO_ALLOCATIONS_CASH_COMPONENT",
    "PORTFOLIO_FEES_TAXES_COMPONENT",
    "PORTFOLIO_FIFO_LOTS_COMPONENT",
    "PORTFOLIO_FIFO_SUMMARY_COMPONENT",
    "PORTFOLIO_FINANCIAL_COMPONENTS",
    "PORTFOLIO_FLOWS_INCOME_COMPONENT",
    "PORTFOLIO_PERFORMANCE_COMPONENT",
    "PORTFOLIO_POSITIONS_COMPONENT",
    "PORTFOLIO_PROVENANCE_COMPONENT",
    "PORTFOLIO_RECONCILIATION_COMPONENT",
    "PORTFOLIO_SUMMARY_COMPONENT",
    "PortfolioAllocationsCashPayload",
    "PortfolioComponentScopeError",
    "PortfolioFeesTaxesPayload",
    "PortfolioFifoLotsPayload",
    "PortfolioFifoSummaryPayload",
    "PortfolioFlowsIncomePayload",
    "PortfolioPerformancePayload",
    "PortfolioPositionsPayload",
    "PortfolioProvenancePayload",
    "PortfolioReconciliationPayload",
    "PortfolioSummaryPayload",
    "ProvenanceNote",
]
