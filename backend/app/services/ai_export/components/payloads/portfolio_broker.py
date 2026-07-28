"""Shared Portfolio/Broker financial payload models and domain-neutral build helpers.

This module hosts everything the Portfolio (`backend.app.services.ai_export.
components.portfolio_financial`) and Broker (`backend.app.services.ai_export.
components.broker_financial`) component builder modules need in common, so
neither financial formulas nor payload shapes are duplicated between the two
domains:

- Currency-safe, `extra="forbid"` Pydantic row/payload models (reusing
  `backend.app.schemas.common.Currency`/`SafeDecimal` for stable, non-scientific
  JSON output) for every frozen `portfolio.*`/`broker.*` non-technical
  component ID.
- Pure mapping helpers from `PortfolioService`/`LotsAnalysisService` output
  models to the payload rows above - no financial formulas are recomputed
  here, every number is read straight off the already-computed engine output.
- Domain-neutral `BuildContext` resource-loading helpers (`load_portfolio_report`,
  `load_lots_results`) that both domains call with their own
  `PORTFOLIO_REPORT_RESOURCE`/`BROKER_REPORT_RESOURCE` and
  `PORTFOLIO_LOTS_RESULTS_RESOURCE`/`BROKER_LOTS_RESULTS_RESOURCE` keys (see
  `backend.app.services.ai_export.components.resources`), guaranteeing exactly
  one `PortfolioService.get_report` call per request regardless of how many
  components need it.

Transitional reuse note: a handful of pure, formula-free helpers are imported
from the legacy `backend.app.services.ai_export.assemblers.fifo` module
(deterministic lot status/residual-cost-basis classification and the bulk
transacted-asset-id discovery query) - these are plain FIFO-lot bookkeeping
helpers, not financial engine formulas, and are deliberately isolated behind
the `_LEGACY_FIFO_HELPERS` import block below for later cleanup once that
legacy module is retired.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date as Date
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, BrokerUserAccess
from backend.app.schemas.common import Currency, OpenDateRangeModel, SafeDecimal
from backend.app.schemas.portfolio import (
    AllocationItem,
    AssetPeriodContribution,
    LotAnalysisType,
    LotsAnalysisResponse,
    LotSummarySchema,
    OtherPeriodEffect,
    PortfolioHolding,
    PortfolioReportQuery,
    PortfolioReportResponse,
    PortfolioSummary,
    UnallocatedContribution,
)

# -- Transitional reuse (see module docstring) --------------------------------
from backend.app.services.ai_export.assemblers.fifo import (  # noqa: E402  _LEGACY_FIFO_HELPERS
    default_transaction_asset_ids_loader,
    has_nonzero_open_lot,
    lot_is_eligible,
    lot_residual_cost_basis,
    lot_status,
)
from backend.app.services.ai_export.components.resources import LotsResultsResource
from backend.app.services.ai_export.components.types import BuildScope, ResourceKey
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService

if TYPE_CHECKING:
    from backend.app.services.ai_export.dependencies import BuildContext

__all__ = [
    "AllocationSlice",
    "ContributionRow",
    "EffectRow",
    "FifoAssetSummaryRow",
    "FifoLotRow",
    "PerformanceBucketRow",
    "PositionRow",
    "UnallocatedRow",
    "discover_transacted_asset_ids",
    "has_nonzero_open_lot",
    "load_lots_results",
    "load_portfolio_report",
    "lot_is_eligible",
    "lot_residual_cost_basis",
    "lot_status",
    "map_allocation_slice",
    "map_contribution_row",
    "map_effect_row",
    "map_fifo_lot_row",
    "map_position_row",
    "map_unallocated_row",
    "resolve_accessible_broker_ids",
]


# =============================================================================
# Currency-safe helpers
# =============================================================================


def _currency(currency_code: str, value: Decimal | None) -> Currency | None:
    """Wraps a plain `Decimal`/`SafeDecimal` amount as a `Currency` in `currency_code`, preserving `None`."""
    if value is None:
        return None
    return Currency(code=currency_code, amount=value)


def _currency_required(currency_code: str, value: Decimal) -> Currency:
    return Currency(code=currency_code, amount=value)


# =============================================================================
# Row models
# =============================================================================


class PositionRow(BaseModel):
    """One open holding snapshot at `snapshot_as_of`, currency-safe and self-describing."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    asset_name: str
    asset_ticker: str | None = None
    asset_type: str
    broker_id: int | None = None
    broker_name: str | None = None
    quantity: SafeDecimal
    wac_per_unit: Currency | None = None
    current_price: Currency | None = None
    current_value: Currency | None = None
    valuation_source: str | None = None
    gain_loss: Currency | None = None
    gain_loss_percent: SafeDecimal | None = None
    allocation_percent: SafeDecimal | None = None
    nav_weight_percent: SafeDecimal | None = None


class AllocationSlice(BaseModel):
    """One allocation category slice (type/sector/geography)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    percent: SafeDecimal
    amount: Currency
    emoji: str | None = None


class ContributionRow(BaseModel):
    """Per-asset period P&L contribution, mirroring `AssetPeriodContribution` currency-safe."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    asset_name: str
    asset_ticker: str | None = None
    asset_type: str
    broker_id: int
    broker_name: str
    period_unrealized_delta: Currency | None = None
    period_realized_gain_loss: Currency | None = None
    period_income: Currency | None = None
    period_fees_taxes: Currency | None = None
    period_pnl: Currency | None = None
    period_pnl_percent: SafeDecimal | None = None
    start_value: Currency | None = None
    end_value: Currency | None = None
    is_fully_sold: bool = False


class UnallocatedRow(BaseModel):
    """Broker-level fees/income not attributed to a specific asset, mirroring `UnallocatedContribution`."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int
    broker_name: str
    unallocated_income: Currency | None = None
    unallocated_fees_taxes: Currency | None = None


class EffectRow(BaseModel):
    """Non-position period P&L row, mirroring `OtherPeriodEffect`."""

    model_config = ConfigDict(extra="forbid")

    description: str
    category: str
    period_pnl: Currency
    broker_id: int | None = None
    broker_name: str | None = None


class PerformanceBucketRow(BaseModel):
    """One `BucketPlan` bucket's start/end/min/max value, flow, P&L and reconciliation.

    `has_data=False` (all other fields `None`) is an explicit, valid outcome for a
    bucket with no daily history points (e.g. a bucket entirely before the first
    transaction) - never fabricated as zero.
    """

    model_config = ConfigDict(extra="forbid")

    index: int
    start_date: Date
    end_date: Date
    has_data: bool
    start_value: Currency | None = None
    end_value: Currency | None = None
    min_value: Currency | None = None
    max_value: Currency | None = None
    net_external_flow: Currency | None = None
    period_pnl: Currency | None = None
    return_percent: SafeDecimal | None = None
    reconciliation_diff: Currency | None = None


class FifoAssetSummaryRow(BaseModel):
    """Per-asset FIFO lot counts/cost-basis summary."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    asset_name: str
    asset_ticker: str | None = None
    open_lot_count: int
    partial_lot_count: int
    closed_lot_count: int
    has_open_position: bool
    residual_cost_basis: Currency


class FifoLotRow(BaseModel):
    """One FIFO lot row: every open/partial lot plus closed lots within scope, no `lot_id`."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    asset_name: str
    asset_ticker: str | None = None
    opening_broker_id: int
    opening_broker_name: str | None = None
    direction: str
    status: str
    opening_date: Date
    closing_date: Date | None = None
    opening_unit_price: Currency
    original_quantity: SafeDecimal
    open_quantity: SafeDecimal
    realized_quantity: SafeDecimal
    original_cost: Currency
    residual_cost_basis: Currency
    cumulative_proceeds: Currency
    open_value: Currency | None = None
    realized_pnl: Currency
    unrealized_pnl: Currency | None = None
    total_pnl: Currency | None = None
    net_total_pnl: Currency | None = None
    income: Currency
    fees: Currency
    taxes: Currency
    value_source: str | None = None
    net_metrics_status: str
    states: list[str] = Field(default_factory=list)


# =============================================================================
# Pure mapping helpers (no I/O, no recomputed formulas)
# =============================================================================


def map_position_row(holding: PortfolioHolding, *, currency_code: str) -> PositionRow:
    return PositionRow(
        asset_id=holding.asset_id,
        asset_name=holding.asset_name,
        asset_ticker=holding.asset_ticker,
        asset_type=holding.asset_type,
        broker_id=holding.broker_id,
        broker_name=holding.broker_name,
        quantity=holding.quantity,
        wac_per_unit=_currency(currency_code, holding.wac_per_unit),
        current_price=_currency(currency_code, holding.current_price),
        current_value=_currency(currency_code, holding.current_value),
        valuation_source=holding.valuation_source,
        gain_loss=_currency(currency_code, holding.gain_loss),
        gain_loss_percent=holding.gain_loss_percent,
        allocation_percent=holding.allocation_percent,
        nav_weight_percent=holding.nav_weight_percent,
    )


def sort_positions(rows: Sequence[PositionRow]) -> list[PositionRow]:
    """Deterministic order independent of upstream ordering: (broker_id, asset_id)."""
    return sorted(rows, key=lambda row: (row.broker_id if row.broker_id is not None else -1, row.asset_id))


def map_allocation_slice(item: AllocationItem, *, currency_code: str) -> AllocationSlice:
    return AllocationSlice(name=item.name, percent=item.value, amount=_currency_required(currency_code, item.amount), emoji=item.emoji)


def map_contribution_row(item: AssetPeriodContribution, *, currency_code: str) -> ContributionRow:
    return ContributionRow(
        asset_id=item.asset_id,
        asset_name=item.asset_name,
        asset_ticker=item.asset_ticker,
        asset_type=item.asset_type,
        broker_id=item.broker_id,
        broker_name=item.broker_name,
        period_unrealized_delta=_currency(currency_code, item.period_unrealized_delta),
        period_realized_gain_loss=_currency(currency_code, item.period_realized_gain_loss),
        period_income=_currency(currency_code, item.period_income),
        period_fees_taxes=_currency(currency_code, item.period_fees_taxes),
        period_pnl=_currency(currency_code, item.period_pnl),
        period_pnl_percent=item.period_pnl_percent,
        start_value=_currency(currency_code, item.start_value),
        end_value=_currency(currency_code, item.end_value),
        is_fully_sold=item.is_fully_sold,
    )


def sort_contributions(rows: Sequence[ContributionRow]) -> list[ContributionRow]:
    return sorted(rows, key=lambda row: (row.broker_id, row.asset_id))


def map_unallocated_row(item: UnallocatedContribution, *, currency_code: str) -> UnallocatedRow:
    return UnallocatedRow(
        broker_id=item.broker_id,
        broker_name=item.broker_name,
        unallocated_income=_currency(currency_code, item.unallocated_income),
        unallocated_fees_taxes=_currency(currency_code, item.unallocated_fees_taxes),
    )


def sort_unallocated(rows: Sequence[UnallocatedRow]) -> list[UnallocatedRow]:
    return sorted(rows, key=lambda row: row.broker_id)


def map_effect_row(item: OtherPeriodEffect, *, currency_code: str) -> EffectRow:
    return EffectRow(
        description=item.description,
        category=item.category,
        period_pnl=_currency_required(currency_code, item.period_pnl),
        broker_id=item.broker_id,
        broker_name=item.broker_name,
    )


def sort_effects(rows: Sequence[EffectRow]) -> list[EffectRow]:
    return sorted(rows, key=lambda row: (row.broker_id if row.broker_id is not None else -1, row.category, row.description))


def map_fifo_lot_row(
    lot: LotSummarySchema,
    *,
    asset_id: int,
    currency_code: str,
    asset_name: str,
    asset_ticker: str | None,
    opening_broker_name: str | None,
) -> FifoLotRow:
    """Maps one authoritative `LotSummarySchema` row to `FifoLotRow` - no `lot_id`/`opening_transaction_id`."""
    status = lot_status(lot)
    residual_cost_basis = lot_residual_cost_basis(lot)
    closing_date = lot.closing_date if status.value == "closed" else None
    return FifoLotRow(
        asset_id=asset_id,
        asset_name=asset_name,
        asset_ticker=asset_ticker,
        opening_broker_id=lot.opening_broker_id,
        opening_broker_name=opening_broker_name,
        direction=str(lot.direction),
        status=status.value.upper(),
        opening_date=lot.opening_date,
        closing_date=closing_date,
        opening_unit_price=_currency_required(currency_code, lot.opening_unit_price),
        original_quantity=lot.original_quantity,
        open_quantity=lot.open_quantity,
        realized_quantity=lot.realized_quantity,
        original_cost=_currency_required(currency_code, lot.original_cost),
        residual_cost_basis=_currency_required(currency_code, residual_cost_basis),
        cumulative_proceeds=_currency_required(currency_code, lot.cumulative_proceeds),
        open_value=_currency(currency_code, lot.open_value),
        realized_pnl=_currency_required(currency_code, lot.realized_pnl),
        unrealized_pnl=_currency(currency_code, lot.market_pnl),
        total_pnl=_currency(currency_code, lot.total_pnl),
        net_total_pnl=_currency(currency_code, lot.net_total_pnl),
        income=_currency_required(currency_code, lot.asset_income),
        fees=_currency_required(currency_code, lot.allocated_fees),
        taxes=_currency_required(currency_code, lot.allocated_taxes),
        value_source=lot.value_source,
        net_metrics_status=lot.net_metrics_status,
        states=list(lot.states),
    )


def sort_fifo_lots(rows: Sequence[tuple[int, FifoLotRow]]) -> list[FifoLotRow]:
    """Sorts `(lot_id, row)` pairs deterministically by `(asset_id, opening_date, lot_id)`, then drops `lot_id`.

    `lot_id` is used purely as the final deterministic tie-breaker (mirroring the
    engine's own internal identifier ordering) and is never present on the
    returned `FifoLotRow` instances.
    """
    ordered = sorted(rows, key=lambda pair: (pair[1].asset_id, pair[1].opening_date, pair[0]))
    return [row for _lot_id, row in ordered]


# =============================================================================
# Domain-neutral BuildContext resource-loading helpers
# =============================================================================


async def resolve_accessible_broker_ids(session: AsyncSession, user_id: int) -> list[int]:
    """Every broker_id `user_id` has any access role on, sorted ascending.

    Used only when `BuildScope.broker_scope` is empty (whole-portfolio scope):
    FIFO asset discovery needs a concrete broker_id list, unlike
    `PortfolioService`/`LotsAnalysisService`, which already resolve `None` to
    "every accessible broker" internally.
    """
    result = await session.execute(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id))
    return sorted({int(broker_id) for broker_id in result.scalars().all()})


async def load_portfolio_report(
    context: BuildContext,
    scope: BuildScope,
    resource_key: ResourceKey[PortfolioReportResponse],
) -> PortfolioReportResponse:
    """Loads the single `PortfolioReportResponse` for this request, memoized under `resource_key`.

    Every `portfolio.*`/`broker.*` financial component builder calls this with
    the *same* `PORTFOLIO_REPORT_RESOURCE`/`BROKER_REPORT_RESOURCE` key for its
    domain, so `BuildContext.db_resource` guarantees exactly one
    `PortfolioService.get_report` call per request regardless of how many
    components need it. Includes summary + history + breakdown +
    positions-contribution for the inclusive `[scope.period_start,
    scope.period_end]` period - an empty portfolio/broker is a valid,
    successfully-built (empty) result, never a source failure.
    """

    async def _loader(session: AsyncSession) -> PortfolioReportResponse:
        query = PortfolioReportQuery(
            broker_ids=list(scope.broker_scope) if scope.broker_scope else None,
            date_range=OpenDateRangeModel(start=scope.period_start, end=scope.period_end),
            target_currency=scope.target_currency,
            include_summary=True,
            include_history=True,
            include_allocation_history=False,
            include_breakdown=True,
            include_positions_contribution=True,
        )
        return await PortfolioService(session).get_report(scope.user_id, query)

    return await context.db_resource(resource_key, _loader)


async def discover_transacted_asset_ids(session: AsyncSession, scope: BuildScope) -> set[int]:
    """Every distinct asset_id ever transacted within `scope`'s broker access, through `snapshot_as_of`."""
    if scope.broker_scope:
        broker_ids = list(scope.broker_scope)
    else:
        broker_ids = await resolve_accessible_broker_ids(session, scope.user_id)
    return await default_transaction_asset_ids_loader(session, broker_ids, scope.snapshot_as_of)


async def load_lots_results(
    context: BuildContext,
    scope: BuildScope,
    resource_key: ResourceKey[LotsResultsResource],
) -> LotsResultsResource:
    """Loads one `LotsAnalysisResponse` (LOT_SUMMARY) per historical asset, memoized under `resource_key`.

    Historical assets are discovered from transactions (never a fixed/limited
    universe), scoped to `scope`'s accessible brokers. An empty transacted-asset
    universe is a valid, successfully-built empty result.
    """

    async def _loader(session: AsyncSession) -> LotsResultsResource:
        broker_ids = list(scope.broker_scope) if scope.broker_scope else await resolve_accessible_broker_ids(session, scope.user_id)
        asset_ids = await discover_transacted_asset_ids(session, scope)
        service = LotsAnalysisService(session)
        results: dict[int, LotsAnalysisResponse] = {}
        for asset_id in sorted(asset_ids):
            results[asset_id] = await service.get_lots_analysis(
                user_id=scope.user_id,
                asset_id=asset_id,
                broker_ids=broker_ids or None,
                date_from=None,
                date_to=scope.snapshot_as_of,
                target_currency=scope.target_currency,
                selected_lot_ids=None,
                requested_analyses=[LotAnalysisType.LOT_SUMMARY],
            )
        return LotsResultsResource.from_mapping(results)

    return await context.db_resource(resource_key, _loader)


async def load_asset_metadata(session: AsyncSession, asset_ids: Sequence[int]) -> Mapping[int, Asset]:
    """Bulk asset metadata lookup (name/ticker), used only by FIFO lot row mapping."""
    if not asset_ids:
        return {}
    result = await session.execute(select(Asset).where(Asset.id.in_(sorted(set(asset_ids)))))
    return {asset.id: asset for asset in result.scalars().all() if asset.id is not None}


async def load_broker_metadata(session: AsyncSession, broker_ids: Sequence[int]) -> Mapping[int, Broker]:
    """Bulk broker metadata lookup (name), used only by FIFO lot row mapping."""
    if not broker_ids:
        return {}
    result = await session.execute(select(Broker).where(Broker.id.in_(sorted(set(broker_ids)))))
    return {broker.id: broker for broker in result.scalars().all() if broker.id is not None}


def summary_position_count(summary: PortfolioSummary | None) -> int:
    return len(summary.holdings) if summary is not None else 0
