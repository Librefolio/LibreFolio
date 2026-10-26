"""
Portfolio Service for LibreFolio.

Contains:
- compute_wac_iterative(): WAC (PMC) of one (broker, asset) for the transaction preview, the
  WAC endpoint and the planner — a facade over financial_math.average_cost
- wac_pool_holding(): what that WAC's pool holds — the units, and whether their cost is known (N88)
- PortfolioService: Orchestrator for portfolio-level aggregation and reporting

PortfolioService uses:
- the portfolio engine for valuation, cost basis (financial_math.average_cost) and realized sales
- financial_math.returns for TWRR/MWRR/Simple ROI
- FX service for currency conversion
- Transaction, Broker, Asset, PriceHistory DB models
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Any, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    Broker,
    BrokerUserAccess,
    PriceHistory,
    Transaction,
    TransactionType,
)
from backend.app.db.precision import round_computed_value
from backend.app.schemas.common import Currency, DateSpan, FxBackwardFillInfo, is_canonical_iso_currency
from backend.app.schemas.portfolio import (
    AcquisitionFundingPoint,
    AcquisitionFundingSeries,
    AllocationHistoryDimensions,
    AllocationHistoryPoint,
    AllocationItem,
    AssetPeriodContribution,
    BrokerBreakdown,
    BrokerPnlHistory,
    BrokerPnlHistoryPoint,
    CostHistoryPoint,
    CostHistorySeries,
    DepositHistoryPoint,
    DepositHistorySeries,
    HoldingGroupGainLoss,
    IncomeHistoryPoint,
    IncomeHistorySeries,
    MissingPriceAsset,
    MwrrLinePoint,
    OtherPeriodEffect,
    PnlCandlePoint,
    PnlCandleSeries,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioReportMetadata,
    PortfolioReportQuery,
    PortfolioReportResponse,
    PortfolioSummary,
    PositionsContribution,
    StalePriceAsset,
    UnallocatedContribution,
    UnrealizedBreakdownRow,
)
from backend.app.schemas.wac import WACMissingPairInfo, WACPreviewResultItem, WACQualifyingTX
from backend.app.services.accounts.settings_service import get_effective_base_currency
from backend.app.services.financial_math.average_cost import (
    CostEffect,
    CostPosition,
    CostStep,
    compute_average_costs,
    cost_movement_from_transaction,
    determine_target_currency,
    movement_unit_costs,
)
from backend.app.services.financial_math.holding_window import closed_position_window, exits_in, oldest_open_lot_date, quantity_moves
from backend.app.services.financial_math.native_cash import CONVERSION_DUST, NativeCash, cash_movement_from_transaction, compute_native_cash, effective_share
from backend.app.services.financial_math.portfolio import period as period_math
from backend.app.services.financial_math.portfolio.contributions import (
    annualized_period_return,
    closed_position_annualized,
    closed_position_base,
    period_return_on_start,
    position_period_pnl,
    transfer_costs_moved_out,
    transfer_tract_adjustments,
    transfer_tracts_moved_in,
    window_start,
)
from backend.app.services.financial_math.portfolio.models import DailyStates
from backend.app.services.financial_math.returns import (
    annualized_to_cumulative,
    calculate_simple_roi,
    calculate_simple_roi_series,
    calculate_twrr,
    calculate_twrr_series,
    change_ratio,
    cumulative_to_annualized,
    gain_loss_ratio,
    group_gain_loss,
    net_holding_return,
    period_mwrr,
    period_mwrr_series,
    realized_gain,
    rebase_to_period,
    timing_effect,
)
from backend.app.services.financial_math.series_steps import merged_spans
from backend.app.services.financial_math.splits import split_linked_ids
from backend.app.services.financial_math.valuation import compute_holding_value
from backend.app.services.financial_math.weights import percent_of
from backend.app.services.financial_math.yield_on_cost import (
    YieldOnCostPositionInput,
    calculate_yield_on_cost_for_positions,
    compute_yield_on_cost_dependency_identity,
)
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.platform.data_quality_thresholds import QUANTITY_DUST_THRESHOLD
from backend.app.utils.datetime_utils import latest_range_end
from backend.app.utils.runtime.cache import get_ttl_cache

_logger = structlog.get_logger(__name__)

# Layer 2 cache: full report results keyed by scope/query plus tx, price, FX and split identities.
_portfolio_l2_cache = get_ttl_cache("portfolio_layer2", maxsize=20, ttl=1800)  # 30 min

# WAC computation cache: avoid re-querying DB for unchanged (broker, asset) pairs
_wac_cache = get_ttl_cache("portfolio_wac", maxsize=200, ttl=3600)  # 1h

# =============================================================================
# WAC ITERATIVE — Inventory-aware iterative WAC (PMC)
# =============================================================================


async def compute_wac_iterative(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
    target_currency_override: str | None = None,
    use_cache: bool = True,
) -> WACPreviewResultItem:
    """Compute inventory-aware WAC (PMC) for an asset at a broker up to a date.

    Facade over :func:`~backend.app.services.financial_math.average_cost.compute_average_costs`
    for the transaction preview, ``POST /portfolio/wac`` and the planner: it loads the rows,
    detects split-linked adjustments, picks the target currency (the override, or the currency
    of the last acquisition) and maps the average-cost timeline to ``WACPreviewResultItem``.
    Each acquisition is converted into the target currency at its own date; when one
    conversion is missing the result is ``wac=None`` with the missing pairs and dates.

    By default, results are cached per (broker_id, asset_id, as_of_date) with a
    transaction fingerprint. Callers that need an uncached domain snapshot can
    set ``use_cache=False`` without mutating shared cache state.
    """
    excluded = set(excluded_tx_ids or [])

    # 1. The pool's rows, and the ones linked to a split
    db_rows, split_linked_row_ids = await _wac_pool_rows(session, broker_id, asset_id, as_of_date)

    # WAC cache check: fingerprint from transaction IDs + updated_at
    import hashlib  # noqa: PLC0415

    wac_h = hashlib.md5(usedforsecurity=False)
    for row in db_rows:
        wac_h.update(f"{row.id}:{row.updated_at.isoformat()}".encode())
    # split_linked_row_ids is queried live against AssetEvent.type (not reflected in
    # Transaction.updated_at), so it must contribute to the fingerprint separately.
    wac_h.update(str(tuple(sorted(split_linked_row_ids))).encode())
    wac_fp = wac_h.hexdigest()
    excluded_key = tuple(sorted(excluded)) if excluded else ()
    wac_cache_key = (broker_id, asset_id, as_of_date.isoformat(), asset_currency, target_currency_override, excluded_key, wac_fp)

    if use_cache:
        cached_wac, wac_hit = _wac_cache.get(wac_cache_key)
        if wac_hit:
            return cached_wac

    # 2. The rows in replay order, as average-cost movements
    rows = sorted((row for row in db_rows if row.id not in excluded), key=lambda row: (row.date, row.id))
    if not rows:
        return WACPreviewResultItem(
            wac=Currency(code=asset_currency, amount=Decimal("0")),
            wac_qualifying_txs=[],
            wac_missing_pairs=[],
        )
    movements = tuple(movement for row in rows if (movement := cost_movement_from_transaction(row, asset_currency=asset_currency, split_linked=row.id in split_linked_row_ids)) is not None)

    # 3. Target currency: the override, or the currency of the last acquisition
    target_currency = target_currency_override or determine_target_currency(movements, asset_currency)

    # 4. Average cost in the target currency, each acquisition converted at its own date
    position_key = (broker_id, asset_id)
    average_cost = (
        await compute_average_costs(
            session,
            [CostPosition(key=position_key, asset_currency=asset_currency, movements=movements)],
            report_currency=target_currency,
            asset_leg=False,
        )
    )[position_key]

    # 5. Fail-safe: one missing conversion and there is no average cost to give
    if average_cost.has_missing_report_fx:
        return WACPreviewResultItem(
            wac=None,
            wac_qualifying_txs=[],
            wac_missing_pairs=[WACMissingPairInfo(pair=item.pair, dates=list(item.dates)) for item in average_cost.missing if item.leg == "report"],
        )

    # The average stays exact in the house; here it leaves the calculation to become an input — a preview the user
    # freezes into a manual cost, an auto cost written on the row — so it is rounded to what that column keeps
    # (C-97 decision D6, MF-W56): a periodic quotient would otherwise be refused (D2) or stored past the limit.
    result = WACPreviewResultItem(
        wac=Currency(code=target_currency, amount=round_computed_value(average_cost.unit_cost_report, Transaction, "cost_basis_override")),
        wac_qualifying_txs=_wac_qualifying_txs(average_cost.steps, target_currency),
        wac_missing_pairs=[],
    )

    # Store in WAC cache
    if use_cache:
        _wac_cache.set(wac_cache_key, result)

    return result


async def _wac_pool_rows(session: AsyncSession, broker_id: int, asset_id: int, as_of_date: date_type) -> tuple[list[Transaction], set[int]]:
    """The rows of the pool a WAC averages — every transaction of ``(broker, asset)`` up to ``as_of_date`` with a quantity
    neither NULL nor zero — and those linked to a SPLIT AssetEvent, which rescale the pool (same cost, new quantity)
    instead of adding or reducing."""
    stmt = select(Transaction).where(
        Transaction.broker_id == broker_id,
        Transaction.asset_id == asset_id,
        Transaction.date <= as_of_date,
        Transaction.quantity.is_not(None),
        Transaction.quantity != 0,
    )
    db_rows = list((await session.execute(stmt)).scalars().all())
    return db_rows, await split_linked_ids(session, db_rows)


@dataclass(frozen=True, slots=True)
class WacPoolHolding:
    """What the pool of a WAC holds on its date (N88, J-57): the units, and whether their cost is wholly known."""

    quantity: Decimal
    cost_complete: bool


async def wac_pool_holding(
    session: AsyncSession,
    broker_id: int,
    asset_id: int,
    as_of_date: date_type,
    asset_currency: str,
    excluded_tx_ids: list[int] | None = None,
    target_currency_override: str | None = None,
) -> WacPoolHolding:
    """The average-cost engine's own quantity and cost completeness for the pool :func:`compute_wac_iterative` averages
    with the same arguments, uncached.

    An average of 0 is no cost when the pool holds no units (never held, or sold out: the engine resets a pool that
    empties) or holds only units of unknown cost (``ADD_UNKNOWN_COST`` counts at zero and leaves the cost incomplete);
    a pool of free units holds units at a known cost of 0. The batch's Auto step reads it only when the average is 0.
    """
    excluded = set(excluded_tx_ids or [])
    db_rows, split_linked_row_ids = await _wac_pool_rows(session, broker_id, asset_id, as_of_date)
    rows = sorted((row for row in db_rows if row.id not in excluded), key=lambda row: (row.date, row.id))
    movements = tuple(movement for row in rows if (movement := cost_movement_from_transaction(row, asset_currency=asset_currency, split_linked=row.id in split_linked_row_ids)) is not None)
    if not movements:
        return WacPoolHolding(quantity=Decimal("0"), cost_complete=True)
    position_key = (broker_id, asset_id)
    average_cost = (
        await compute_average_costs(
            session,
            [CostPosition(key=position_key, asset_currency=asset_currency, movements=movements)],
            report_currency=target_currency_override or determine_target_currency(movements, asset_currency),
            asset_leg=False,
        )
    )[position_key]
    return WacPoolHolding(quantity=average_cost.quantity, cost_complete=average_cost.report_complete)


# Effects of the average-cost steps in the vocabulary of WACQualifyingTX.effect, which the
# transaction preview and the planner read: an acquisition of unknown cost enters at zero.
_WAC_PREVIEW_EFFECTS = {
    CostEffect.ADD: "add",
    CostEffect.ADD_ZERO_COST: "add_zero_cost",
    CostEffect.ADD_UNKNOWN_COST: "add_zero_cost",
    CostEffect.REDUCE: "reduce",
    CostEffect.SPLIT_RESCALE: "split_rescale",
}


def _wac_qualifying_txs(steps: tuple[CostStep, ...], target_currency: str) -> list[WACQualifyingTX]:
    """One preview row per movement: unit cost, running WAC and conversion provenance."""
    rows: list[WACQualifyingTX] = []
    for step, unit_cost in zip(steps, movement_unit_costs(steps), strict=True):
        movement = step.movement
        conversion = step.conversion
        rows.append(
            WACQualifyingTX(
                tx_id=movement.movement_id,
                type=movement.transaction_type,
                date=movement.date,
                quantity=movement.quantity,
                unit_cost=unit_cost.report,
                currency=target_currency,
                effect=_WAC_PREVIEW_EFFECTS[step.effect],
                running_wac=step.unit_cost_report,
                fx_info=FxBackwardFillInfo(fx_rate_date=conversion.rate_date, fx_days_back=conversion.days_back) if conversion else None,
                original_unit_cost=unit_cost.original,
                original_currency=conversion.original_currency if conversion else None,
                fx_rate_used=conversion.rate if conversion else None,
            )
        )
    return rows


def _period_realized_sales(sales: list[Any], date_from: date_type | None, date_to: date_type | None) -> list[Any]:
    """The engine's realized SELLs in (date_from, date_to] whose proceeds and cost are both known.

    A sale whose proceeds could not be converted, or taken from a pool that already lacked part
    of its cost, is left out: its pair, or the cost it lacks, is reported in the data quality.
    """
    return [sale for sale in sales if (date_from is None or sale.date > date_from) and (date_to is None or sale.date <= date_to) and sale.proceeds is not None and sale.cost_complete]


def _engine_missing_fx_pairs(engine_result: Any, period_from: date_type | None, period_to: date_type | None) -> list[WACMissingPairInfo]:
    """Every conversion the engine could not make, as pair + dates + ranges for the data-quality banner.

    ``dates``: the movements (cost, cash, external flows, in-transit cost), on whatever date they happened. ``ranges``:
    the valuation days, only those of the period shown, [period_from, period_to], whose first day is the opening state of
    the period, with the consecutive days merged (D-P4: no list of every day).
    """
    dates_by_pair: dict[str, set[date_type]] = defaultdict(set)
    for pair, dates in (getattr(engine_result, "missing_fx", None) or {}).items():
        dates_by_pair[pair].update(dates)
    spans_by_pair: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
    daily_states = getattr(engine_result, "daily_states", None) or []
    if isinstance(daily_states, DailyStates):
        # Every day of a segment reads its state's pairs (P4): no state is built
        for segment in daily_states.iter_segments(period_from, period_to):
            for pair in segment.state.missing_fx_pairs:
                spans_by_pair[pair].append((segment.start, segment.end))
    else:
        for state in daily_states:
            if not state.missing_fx_pairs:
                continue
            if (period_from is not None and state.date < period_from) or (period_to is not None and state.date > period_to):
                continue
            for pair in state.missing_fx_pairs:
                spans_by_pair[pair].append((state.date, state.date))
    return [WACMissingPairInfo(pair=pair, dates=sorted(dates_by_pair.get(pair, ())), ranges=[DateSpan(start=first, end=last) for first, last in merged_spans(spans_by_pair.get(pair, ()))]) for pair in sorted(set(dates_by_pair) | set(spans_by_pair))]


@dataclass(frozen=True)
class HistorySteps:
    """The report's history in steps (D-P4): its ``range``, the steps, and the MWRR line of true points."""

    range: DateSpan | None
    history: list[PortfolioHistoryPoint]
    mwrr_line: list[MwrrLinePoint]


def _engine_native_cash(engine_result: Any, report_currency: str) -> NativeCash:
    """The engine's native cash of the scope; an empty one when the engine stopped early (no access, no transaction)."""
    native_cash = getattr(engine_result, "native_cash", None)
    return native_cash if native_cash is not None else NativeCash(report_currency=report_currency, movements=(), converted=(), unit_rates={})


def _unrealized_breakdown_rows(engine_result: Any, date_from: date_type | None, as_of: date_type, currency: str) -> list[UnrealizedBreakdownRow]:
    """The period's unrealized change by asset currency: assets' own change, exchange-rate effect, unsplit.

    Same boundary states as the period P&L (``financial_math.portfolio.period.period_boundaries``: the
    last state on or before ``date_from``, zero when there is none or no ``date_from``; the state at
    ``as_of``), so the rows add up to ``period_unrealized_gain_loss_delta`` exactly. Order: asset rows,
    then exchange-rate rows, then unsplit rows; the report currency first, then alphabetical.
    """
    boundaries = period_math.period_boundaries(getattr(engine_result, "daily_states", None) or [], date_from, as_of)
    if boundaries is None:
        return []
    start_state, end_state = boundaries.start, boundaries.end
    end_parts = end_state.unrealized_by_currency
    start_parts = start_state.unrealized_by_currency if start_state is not None else {}
    currencies = sorted(set(end_parts) | set(start_parts), key=lambda code: (code != currency, code))

    zero = Decimal("0")

    def delta(code: str, kind: str) -> tuple[Decimal, Decimal, Decimal]:
        end_value = getattr(end_parts[code], kind) if code in end_parts else zero
        start_value = getattr(start_parts[code], kind) if code in start_parts else zero
        return start_value, end_value, end_value - start_value

    rows: list[UnrealizedBreakdownRow] = []
    for code in currencies:
        rows.append(UnrealizedBreakdownRow(kind="asset", asset_currency=code, period_delta=Currency(code=currency, amount=delta(code, "asset")[2])))
    for code in currencies:
        if code != currency:
            rows.append(UnrealizedBreakdownRow(kind="fx", asset_currency=code, period_delta=Currency(code=currency, amount=delta(code, "fx")[2])))
    for code in currencies:
        start_value, end_value, change = delta(code, "unsplit")
        if start_value != zero or end_value != zero:
            rows.append(UnrealizedBreakdownRow(kind="unsplit", asset_currency=code, period_delta=Currency(code=currency, amount=change)))
    return rows


# =============================================================================
# PORTFOLIO SERVICE — Orchestrator
# =============================================================================

_HOLDING_TYPES = {TransactionType.BUY, TransactionType.SELL}
# Transaction types that move a position's quantity: its holding window comes from them
# (financial_math.holding_window; a split rescales the open lots, a transfer-in opens one
# dated at its arrival at the receiving broker).
_LOT_AFFECTING_TYPES = {TransactionType.BUY, TransactionType.SELL, TransactionType.ADJUSTMENT, TransactionType.TRANSFER}


# Some instruments (e.g. CROWDFUND real-estate loans redeemed via periodic partial
# buybacks) accrue a tiny non-zero quantity residual even after the position is
# economically fully closed — the platform computes each redemption tranche's
# quantity independently (rounded to its own precision), and those tranches don't
# always sum back to *exactly* the original quantity bought (observed real case:
# 8×(-0.031102) + (-0.751182) against a +1 buy leaves a +0.000002 residual). This
# is not Decimal arithmetic error — it's an artifact of the recorded transaction
# quantities themselves — so treat anything at or below this threshold as closed.
# The value lives in data_quality_thresholds, shared with the asset list's held-now flags
# and the closed-position window (financial_math.holding_window).
_QUANTITY_DUST_THRESHOLD = QUANTITY_DUST_THRESHOLD


@dataclass(frozen=True)
class HeldAssetQuoteFacts:
    """An asset held at the end of a report's period, with what the data-quality report's asset quote check reads: its
    stored currency (E-19b's NON_ISO_CURRENCY)."""

    asset_id: int
    name: str
    currency: str


class PortfolioService:
    """Orchestrator for portfolio-level calculations.

    Aggregates WAC, prices, allocations, ROI metrics (TWRR/MWRR) and FIFO lots
    across brokers, applying share_percentage before cross-broker aggregation.

    Event loop safety:
    - All sync CPU-heavy calls (scipy) are wrapped in asyncio.to_thread().
    - All DB I/O uses AsyncSession.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_base_currency(self, user_id: int) -> str:
        """Effective base currency: per-user setting, global default, EUR (P0-1)."""
        return await get_effective_base_currency(self.db, user_id)

    async def _get_user_broker_access(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
    ) -> list[BrokerUserAccess]:
        """Return BrokerUserAccess rows for a user, optionally filtered by broker_ids."""
        stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        if broker_ids:
            stmt = stmt.where(BrokerUserAccess.broker_id.in_(broker_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_broker(self, broker_id: int) -> Broker | None:
        return await self.db.get(Broker, broker_id)

    async def _get_brokers_map(self, broker_ids: set[int]) -> dict[int, Broker]:
        if not broker_ids:
            return {}
        stmt = select(Broker).where(Broker.id.in_(broker_ids))
        result = await self.db.execute(stmt)
        return {broker.id: broker for broker in result.scalars().all()}

    async def _get_transactions(
        self,
        broker_id: int,
        tx_types: set[TransactionType] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
    ) -> list[Transaction]:
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        if tx_types:
            stmt = stmt.where(Transaction.type.in_(tx_types))
        if date_from:
            stmt = stmt.where(Transaction.date >= date_from)
        if date_to:
            stmt = stmt.where(Transaction.date <= date_to)
        stmt = stmt.order_by(Transaction.date, Transaction.id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_price_at_date(self, asset_id: int, target_date: date_type) -> Optional[tuple[Decimal, str, date_type]]:
        """Return (close_price, currency, actual_date) for the latest price on or before target_date (backward-fill)."""
        stmt = select(PriceHistory.close, PriceHistory.currency, PriceHistory.date).where(PriceHistory.asset_id == asset_id, PriceHistory.close.is_not(None), PriceHistory.date <= target_date).order_by(PriceHistory.date.desc()).limit(1)
        row = (await self.db.execute(stmt)).one_or_none()
        if row:
            return row.close, row.currency, row.date
        return None

    async def _get_asset(self, asset_id: int) -> Asset | None:
        return await self.db.get(Asset, asset_id)

    async def _get_assets_map(self, asset_ids: set[int]) -> dict[int, Asset]:
        if not asset_ids:
            return {}
        stmt = select(Asset).where(Asset.id.in_(asset_ids))
        result = await self.db.execute(stmt)
        return {asset.id: asset for asset in result.scalars().all()}

    async def _convert_to_base(
        self,
        amount: Decimal,
        currency: str,
        base_currency: str,
        as_of_date: date_type,
    ) -> tuple[Decimal | None, list[WACMissingPairInfo]]:
        """Convert amount to base_currency. Returns (converted_amount, missing_pairs)."""
        if currency == base_currency:
            return amount, []
        results, _ = await convert_bulk(
            self.db,
            [(Currency(code=currency, amount=amount), base_currency, as_of_date)],
            raise_on_error=False,
        )
        if results and results[0] is not None:
            converted, _, _ = results[0]
            return converted.amount, []
        pair_key = f"{currency}/{base_currency}"
        return None, [WACMissingPairInfo(pair=pair_key, dates=[as_of_date])]

    async def _missing_cost_basis_assets(self, engine_result: Any) -> list[tuple[int, str]]:
        """(asset_id, name) of the assets with an acquisition of unknown cost in the engine's replay."""
        asset_ids = sorted({asset_id for (asset_id, _broker_id), average_cost in getattr(engine_result, "average_costs", {}).items() if average_cost.unknown_cost_movement_ids})
        if not asset_ids:
            return []
        assets = await self._get_assets_map(set(asset_ids))
        return [(asset_id, assets[asset_id].display_name if asset_id in assets else f"Asset {asset_id}") for asset_id in asset_ids]

    async def _invalid_split_assets(self, engine_result: Any) -> list[tuple[int, str]]:
        """(asset_id, name) of the assets with a SPLIT event whose stored ratio the engine counted as missing (MF-D4)."""
        asset_ids = sorted({event.asset_id for event in getattr(engine_result, "invalid_split_events", [])})
        if not asset_ids:
            return []
        assets = await self._get_assets_map(set(asset_ids))
        return [(asset_id, assets[asset_id].display_name if asset_id in assets else f"Asset {asset_id}") for asset_id in asset_ids]

    async def _held_asset_quote_facts(self, engine_result: Any) -> list[HeldAssetQuoteFacts]:
        """The assets held at the end of the period (a position above the dust threshold), each with its stored
        currency, read in one query: what the data-quality report's asset quote check needs (E-19b's NON_ISO_CURRENCY)."""
        asset_ids = sorted({ps.asset_id for ps in engine_result.position_states_end if ps.quantity > _QUANTITY_DUST_THRESHOLD})
        if not asset_ids:
            return []
        assets = (await self.db.execute(select(Asset).where(Asset.id.in_(asset_ids)).order_by(Asset.id))).scalars().all()
        return [HeldAssetQuoteFacts(asset_id=asset.id, name=asset.display_name, currency=asset.currency) for asset in assets]

    @staticmethod
    def _non_iso_currency_assets(facts: Sequence[HeldAssetQuoteFacts]) -> list[tuple[int, str, str]]:
        """(asset_id, name, stored currency) of the held assets whose currency is not an ISO 4217 code as stored (E-19b):
        ``978``, ``EURO`` or ``eur``, which an earlier version saved as written."""
        return [(fact.asset_id, fact.name, fact.currency) for fact in facts if not is_canonical_iso_currency(fact.currency)]

    @staticmethod
    def _merge_missing_pairs(items: list[WACMissingPairInfo]) -> list[WACMissingPairInfo]:
        merged: dict[str, set[date_type]] = defaultdict(set)
        spans: dict[str, list[tuple[date_type, date_type]]] = defaultdict(list)
        for item in items:
            merged[item.pair].update(item.dates)
            spans[item.pair].extend((span.start, span.end) for span in item.ranges)
        return [WACMissingPairInfo(pair=pair, dates=sorted(dates), ranges=[DateSpan(start=first, end=last) for first, last in merged_spans(spans[pair])]) for pair, dates in sorted(merged.items())]

    async def _get_configured_fx_pair_sets(self) -> tuple[set[str], set[str]]:
        from backend.app.services.financial_math.portfolio.data_quality import load_configured_fx_pair_sets  # noqa: PLC0415 — same lazy engine import as the methods below

        return await load_configured_fx_pair_sets(self.db)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_summary(  # noqa: C901 — TODO(P2-refactor): nested broker/tx/asset accumulation; extract per-position builder
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        include_breakdown: bool = False,
        target_currency_override: str | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        _precomputed_engine_result=None,
    ) -> PortfolioSummary:
        """Return aggregated portfolio summary via PortfolioCalculationEngine.

        Uses the new engine for aggregate values (NAV, market_value, book_value,
        allocation, performance) and derives holding rows from end-of-period
        position snapshots.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        from backend.app.services.financial_math.portfolio.data_quality import transaction_implied_assets_to_report  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.models import ValuationSource  # noqa: PLC0415
        from backend.app.services.platform.data_quality_thresholds import TRANSACTION_IMPLIED_GRACE_DAYS  # noqa: PLC0415

        today = date_type.today()
        # R13-SEC7-1: the summary's whole horizon (engine run, MWRR, stale prices, annualization) ends by latest_range_end()
        if date_to is not None:
            date_to = min(date_to, latest_range_end())
        valuation_date = date_to or today
        if date_from is not None:
            date_from = min(date_from, valuation_date)
        base_currency = target_currency_override or await self._get_base_currency(user_id)

        # ── 1. Run engine for aggregate values + performance ──
        if _precomputed_engine_result is not None:
            engine_result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            engine_result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,
                date_to=date_to,
                target_currency=base_currency,
            )

        views = DerivedViewsBuilder(engine_result.daily_states, base_currency)

        # ── 2. Extract aggregate values from last daily state ──
        # Looked up by date (not blindly daily_states[-1]) as a guard against a
        # stale/wider cached blob leaking states beyond the requested valuation_date.
        last_state = period_math.state_as_of(engine_result.daily_states, valuation_date)
        engine_nav = last_state.nav_value if last_state else Decimal("0")
        engine_cash = last_state.cash_value if last_state else Decimal("0")
        engine_market_value = last_state.market_value if last_state else Decimal("0")

        # ── 3. Broker cash / realized P&L + end-of-period holdings snapshot ──
        accesses = await self._get_user_broker_access(user_id, broker_ids)

        total_invested = Decimal("0")
        all_cash_balances: dict[str, Decimal] = defaultdict(Decimal)
        all_holdings: list[PortfolioHolding] = []
        by_broker_list: list[BrokerBreakdown] = []
        all_missing_pairs: list[WACMissingPairInfo] = []
        missing_price_assets: list[MissingPriceAsset] = []
        broker_names: dict[int, str] = {}
        first_position_dates: dict[tuple[int, int], date_type] = {}
        # Holding-transaction streams per (broker, asset) for FIFO oldest-open-lot derivation.
        lot_txns_by_key: dict[tuple[int, int], list[Transaction]] = defaultdict(list)

        # Cash, deposits, income and costs come from the engine's native cash: the same
        # movements, each at its broker's share and converted at its own date. A movement
        # with no rate on its date is left out of values and flows, still counted in its own
        # currency, and reported as a missing pair with that date.
        native_cash = _engine_native_cash(engine_result, base_currency)
        period_flows = native_cash.flows(date_from, valuation_date)
        # Per-position income and fee/tax totals over the position's whole life (<= valuation
        # date), used for the net holding return that feeds the annualized column.
        lifetime_flows = native_cash.flows(None, valuation_date)
        _total_deposited = period_flows.absolute_by_type.get(TransactionType.DEPOSIT, Decimal("0"))
        _total_withdrawn = period_flows.absolute_by_type.get(TransactionType.WITHDRAWAL, Decimal("0"))
        # Signed: a legacy negative DIVIDEND/INTEREST correction must reduce period_income,
        # not be folded into the "Other" reconciliation residual via abs() (plan §4.4).
        _income_accum = Decimal("0") + period_flows.signed_by_type.get(TransactionType.DIVIDEND, Decimal("0")) + period_flows.signed_by_type.get(TransactionType.INTEREST, Decimal("0"))
        _fees_accum = period_flows.absolute_by_type.get(TransactionType.FEE, Decimal("0"))
        _taxes_accum = period_flows.absolute_by_type.get(TransactionType.TAX, Decimal("0"))
        _fees_taxes_accum = Decimal("0") + _fees_accum + _taxes_accum
        income_by_pos = lifetime_flows.income_by_position
        fees_taxes_by_pos = lifetime_flows.costs_by_position
        all_missing_pairs.extend(WACMissingPairInfo(pair=missing.pair, dates=list(missing.dates)) for missing in native_cash.missing_conversions(None, valuation_date))

        for access in accesses:
            broker_id = access.broker_id
            broker = await self._get_broker(broker_id)
            broker_name = broker.name if broker else f"Broker {broker_id}"
            broker_names[broker_id] = broker_name

            # Same horizon as the engine: without date_to it stops at today, so a row dated
            # later must not reach the lots either.
            broker_txns = await self._get_transactions(broker_id, date_to=valuation_date)

            # Holding transactions — lot streams and first position dates
            for tx in broker_txns:
                if tx.asset_id is not None and tx.type in _LOT_AFFECTING_TYPES:
                    lot_txns_by_key[(broker_id, tx.asset_id)].append(tx)
                if tx.type not in _HOLDING_TYPES or tx.asset_id is None:
                    continue
                pos_key = (broker_id, tx.asset_id)
                if pos_key not in first_position_dates or tx.date < first_position_dates[pos_key]:
                    first_position_dates[pos_key] = tx.date

        # Realized G/L of the SELLs and outgoing ADJUSTMENTs (proceeds 0, N78-1) in the period: proceeds minus the
        # historical cost the engine's average-cost pool gave up, both in base currency with the owner's share.
        _realized_accum = sum((gain for sale in _period_realized_sales(engine_result.realized_sales, date_from, date_to) if (gain := realized_gain(sale.proceeds, sale.cost)) is not None), Decimal("0"))

        lot_split_ids = await split_linked_ids(self.db, [tx for txns in lot_txns_by_key.values() for tx in txns])
        # MF-A10: the moves at the owner's share, as the engine's quantities the rows test against the dust threshold
        lot_shares = {access.broker_id: effective_share(access.role, access.share_percentage) for access in accesses}
        oldest_open_lot_dates: dict[tuple[int, int], Optional[date_type]] = {key: oldest_open_lot_date(quantity_moves(txns, lot_split_ids, share=lot_shares[key[0]])) for key, txns in lot_txns_by_key.items()}
        # First lot-affecting transaction per position (includes ADJUSTMENT/TRANSFER, so
        # in-kind/succession/snapshot-seeded positions get a real window start — unlike
        # first_position_dates which only tracks BUY/SELL). Anchors the net annualized window.
        first_lot_txn_dates: dict[tuple[int, int], date_type] = {key: min(t.date for t in txns) for key, txns in lot_txns_by_key.items() if txns}

        end_positions = [ps for ps in engine_result.position_states_end if ps.quantity > _QUANTITY_DUST_THRESHOLD]
        yield_on_cost_by_position = await calculate_yield_on_cost_for_positions(
            self.db,
            user_id=user_id,
            positions=[
                YieldOnCostPositionInput(
                    asset_id=position.asset_id,
                    broker_id=position.broker_id,
                    wac_per_unit=position.wac,
                    wac_currency=position.wac_currency,
                )
                for position in end_positions
            ],
            target_currency=base_currency,
            as_of_date=valuation_date,
        )
        assets_map = await self._get_assets_map({ps.asset_id for ps in end_positions})
        brokers_map = await self._get_brokers_map({ps.broker_id for ps in end_positions})

        for ps in end_positions:
            asset = assets_map.get(ps.asset_id)
            if not asset:
                continue

            broker = brokers_map.get(ps.broker_id)
            broker_name = broker.name if broker else broker_names.get(ps.broker_id, f"Broker {ps.broker_id}")

            current_price: Decimal | None = None
            if ps.valuation_effective_unit_price is not None and ps.valuation_effective_currency is not None:
                if ps.valuation_effective_currency == base_currency:
                    current_price = ps.valuation_effective_unit_price
                else:
                    current_price, mp = await self._convert_to_base(
                        ps.valuation_effective_unit_price,
                        ps.valuation_effective_currency,
                        base_currency,
                        ps.date,
                    )
                    all_missing_pairs.extend(mp)

            yield_on_cost_calculation = yield_on_cost_by_position[(ps.asset_id, ps.broker_id)]
            wac_per_unit = yield_on_cost_calculation.wac_per_unit
            all_missing_pairs.extend(yield_on_cost_calculation.missing_fx_pairs)

            current_value = ps.market_value

            gain_loss = ps.unrealized_pnl
            gain_loss_pct = gain_loss_ratio(gain_loss, ps.cost_basis, positive_base=False)

            price_change_1d: Decimal | None = None
            gain_loss_change_1d: Decimal | None = None
            gain_loss_change_1d_percent: Decimal | None = None
            if ps.valuation_source == "MARKET_PRICE" and current_price is not None:
                prev_price_data = await self._get_price_at_date(ps.asset_id, ps.date - timedelta(days=1))
                if prev_price_data:
                    prev_raw, prev_ccy, prev_date = prev_price_data
                    if prev_ccy == base_currency:
                        prev_price_base = prev_raw
                    else:
                        prev_price_base, mp = await self._convert_to_base(prev_raw, prev_ccy, base_currency, prev_date)
                        all_missing_pairs.extend(mp)
                    if prev_price_base is not None and prev_price_base != 0:
                        # MF-A12 (N92): the change over the size of the previous price, measured as the % column measures
                        # the value's (the same association: a tie rounds as before); a negative price's change keeps the
                        # move's sign, as the % column's does
                        price_ratio_1d = change_ratio(current_price - prev_price_base, prev_price_base)
                        price_change_1d = price_ratio_1d.quantize(Decimal("0.0001")) if price_ratio_1d is not None else None
                        # Bugfix: raw quoted prices (current_price/prev_price_base) are NOT
                        # 1 unit == 1 currency unit for every asset — e.g. bonds are quoted
                        # "per quote_base_quantity" (BTPs: quote_base_quantity=100, price=98.70
                        # means 98.70 per 100 nominal). market_value/gain_loss above already go
                        # through compute_holding_value() to apply that scaling; a naive
                        # `(current_price - prev_price_base) * ps.quantity` here skipped it,
                        # inflating the daily delta by quote_base_quantity× for such assets
                        # (reported: a BTP position showed a +93.60% "1-day" P&L swing).
                        # Reuse compute_holding_value for both legs so the scaling matches.
                        current_position_value = compute_holding_value(ps.quantity, current_price, asset.quote_base_quantity)
                        previous_position_value = compute_holding_value(ps.quantity, prev_price_base, asset.quote_base_quantity)
                        gain_loss_change_1d = current_position_value - previous_position_value
                        if abs(previous_position_value) > Decimal("0.01"):
                            value_ratio_1d = change_ratio(gain_loss_change_1d, previous_position_value)
                            gain_loss_change_1d_percent = (value_ratio_1d * 100).quantize(Decimal("0.01")) if value_ratio_1d is not None else None

            if ps.valuation_source == "MISSING":
                missing_price_assets.append(
                    MissingPriceAsset(
                        asset_id=ps.asset_id,
                        symbol=asset.identifier_ticker,
                        name=asset.display_name,
                        broker_id=ps.broker_id,
                        broker_name=broker_name,
                        first_position_date=first_position_dates.get((ps.broker_id, ps.asset_id)),
                        quantity=ps.quantity,
                        open_cost_basis=ps.cost_basis if ps.cost_basis != 0 else None,
                        currency=base_currency,
                    )
                )

            # Net annualized return of the still-open position over its full life
            # (first lot-affecting transaction -> valuation date). Net = unrealized
            # (valued at cost, i.e. 0 market P&L, when the price is missing) + income
            # (coupons/dividends) - fees/taxes, normalized by cost basis. This makes a
            # no-price position with coupons (e.g. an unquoted BTP) show an income-only
            # return instead of "—", and includes income/costs per the product rule.
            holding_first_tx = first_lot_txn_dates.get((ps.broker_id, ps.asset_id))
            holding_annualized = None
            if ps.cost_complete and ps.cost_basis and ps.cost_basis != 0 and holding_first_tx is not None:
                pos_income = income_by_pos.get((ps.broker_id, ps.asset_id), Decimal("0"))
                pos_fees = fees_taxes_by_pos.get((ps.broker_id, ps.asset_id), Decimal("0"))
                holding_return = net_holding_return(gain_loss, pos_income, pos_fees, ps.cost_basis)
                holding_annualized = cumulative_to_annualized(holding_return, (valuation_date - holding_first_tx).days)

            all_holdings.append(
                PortfolioHolding(
                    asset_id=ps.asset_id,
                    asset_name=asset.display_name,
                    asset_ticker=asset.identifier_ticker,
                    asset_type=asset.asset_type.value if asset.asset_type else "Unknown",
                    broker_id=ps.broker_id,
                    broker_name=broker_name,
                    quantity=ps.quantity,
                    wac_per_unit=wac_per_unit,
                    current_price=current_price,
                    current_value=current_value,
                    valuation_source=ps.valuation_source.value,
                    valuation_effective_unit_price=ps.valuation_effective_unit_price,
                    valuation_effective_currency=ps.valuation_effective_currency,
                    valuation_reference_date=ps.valuation_reference_date,
                    valuation_reference_unit_price=ps.valuation_reference_unit_price,
                    valuation_reference_currency=ps.valuation_reference_currency,
                    valuation_split_adjusted=ps.valuation_split_adjusted,
                    missing_fx_pair=ps.missing_fx_pair,
                    gain_loss=gain_loss,
                    gain_loss_percent=gain_loss_pct,
                    annualized_return=holding_annualized,
                    price_change_1d=price_change_1d,
                    gain_loss_change_1d=gain_loss_change_1d,
                    gain_loss_change_1d_percent=gain_loss_change_1d_percent,
                    oldest_open_lot_date=oldest_open_lot_dates.get((ps.broker_id, ps.asset_id)),
                    yield_on_cost=yield_on_cost_calculation.result if yield_on_cost_calculation is not None else None,
                    allocation_percent=None,
                )
            )

        # Each card's cash is its native balances valued at valuation_date's rates; the headline
        # lists every currency held, summed over the cards. A broker whose movements are all
        # zero has no value of its own: its cash is its report-currency balance.
        native_balances = native_cash.balances(valuation_date)
        cash_values = native_cash.value_at(valuation_date)
        broker_cash_base = {broker_id: cash_values.get(broker_id, native_balances.get(broker_id, {}).get(base_currency, Decimal("0"))) for broker_id in broker_names}
        for broker_id in broker_names:
            for ccy, amt in native_balances.get(broker_id, {}).items():
                all_cash_balances[ccy] += amt

        if include_breakdown:
            for broker_id, broker_name in broker_names.items():
                # Each card is the engine's per-broker slice of the headline on valuation_date
                # (the cards add up to it): market value, cash at that day's rates and the value
                # in transit, which stays on the sender's card; capital moves on arrival, so an
                # internal transfer never shows -X / +X.
                contribution = last_state.broker_contributions.get(broker_id) if last_state is not None else None
                broker_capital = contribution.capital_contribution if contribution is not None else Decimal("0")
                broker_nav = contribution.nav_contribution if contribution is not None else Decimal("0")
                broker_gain = contribution.pnl_contribution if contribution is not None else Decimal("0")
                broker_gl_ratio = gain_loss_ratio(broker_gain, broker_capital, positive_base=True)
                broker_gl_pct = broker_gl_ratio if broker_gl_ratio is not None else Decimal("0")
                by_broker_list.append(
                    BrokerBreakdown(
                        broker_id=broker_id,
                        broker_name=broker_name,
                        net_worth=Currency(code=base_currency, amount=broker_nav),
                        gain_loss=Currency(code=base_currency, amount=broker_gain),
                        gain_loss_percent=broker_gl_pct,
                        cash_total=Currency(code=base_currency, amount=broker_cash_base.get(broker_id, Decimal("0"))),
                        cash_balances=[Currency(code=ccy, amount=amt) for ccy, amt in native_balances.get(broker_id, {}).items()],
                    )
                )

        # ── 4. Allocation from engine (scope-aware, includes in-transit) ──
        alloc_type, alloc_sector, alloc_geo = views.build_allocation_current()
        last_by_asset = views.daily_states[-1].by_asset if views.daily_states else {}
        alloc_asset_names = {asset_id: asset.display_name for asset_id, asset in (await self._get_assets_map(set(last_by_asset))).items()}
        alloc_asset = views.build_asset_allocation_current(alloc_asset_names)

        def _alloc_from_engine(items: list[dict]) -> list[AllocationItem]:
            return [AllocationItem(**item) for item in items]

        # Weights from the house (D-MF7): no share of a total at or below zero — the field stays None («—»).
        total_market = sum((h.current_value for h in all_holdings if h.current_value), Decimal("0"))
        for h in all_holdings:
            if not h.current_value:
                continue
            allocation = percent_of(h.current_value, total_market)
            nav_weight = percent_of(h.current_value, engine_nav)
            object.__setattr__(h, "allocation_percent", allocation.quantize(Decimal("0.01")) if allocation is not None else None)
            object.__setattr__(h, "nav_weight_percent", nav_weight.quantize(Decimal("0.01")) if nav_weight is not None else None)

        # ── 5. Performance from engine (correct daily NAV) ──
        nav_snapshots, cash_flows_perf = views.build_performance_inputs(date_from)

        # Period re-basing: when date_from is set, compute metrics for that period only
        period = rebase_to_period(nav_snapshots, cash_flows_perf, date_from)
        period_cfs = list(period.cash_flows)
        period_navs = list(period.nav_snapshots)
        period_start_date_perf = period.start_date if period.start_date is not None else today

        # Net invested for the period (sum of deposits minus withdrawals)
        period_net_invested = sum(-cf.amount for cf in period_cfs)
        simple_roi = calculate_simple_roi(engine_nav, period_net_invested) if period_net_invested > 0 else Decimal("0")
        twrr_result: Decimal | None = None
        mwrr_result: Decimal | None = None

        if period_navs and period_cfs and engine_nav > 0:
            try:
                twrr_point = calculate_twrr(period_navs, period_cfs)
                twrr_result = twrr_point.twrr
            except (ValueError, ZeroDivisionError):
                twrr_result = None
        # The Dashboard's MWRR rule lives in the house: the card is the last point of the line by construction
        # (D-MF5): no rate without net invested capital or with a value at or below zero.
        mwrr_result = (await asyncio.to_thread(period_mwrr, period_navs, period_cfs, date_to or today, engine_nav)).mwrr

        # ── MWRR cumulative derivation ──
        mwrr_period_days: int | None = None
        mwrr_cumulative: Decimal | None = None
        if period_navs:
            mwrr_period_days = ((date_to or today) - period_start_date_perf).days
            mwrr_cumulative = annualized_to_cumulative(mwrr_result, mwrr_period_days) if mwrr_result is not None else None

        # Headline invested capital & P&L come from the engine's capital baseline
        # (cumulative_external_cash_flow), which folds in priced in-kind ADJUSTMENT
        # capital (opening equity / succession). Deriving total_gl from a cash-only
        # "invested" would treat that in-kind capital as pure profit, inflating the
        # headline gain to thousands of percent on in-kind-seeded portfolios. The
        # engine's total_pnl = NAV - capital_baseline is the authoritative figure.
        if last_state is not None:
            total_invested = last_state.cumulative_external_cash_flow
            total_gl = last_state.total_pnl
        else:
            total_gl = engine_nav - total_invested
        total_gl_ratio = gain_loss_ratio(total_gl, total_invested, positive_base=True)
        total_gl_pct = total_gl_ratio if total_gl_ratio is not None else Decimal("0")
        cash_balances_list = [Currency(code=ccy, amount=amt) for ccy, amt in all_cash_balances.items()]

        # ── Period P&L breakdown: NAV, unrealized delta, income, fees ──
        period_figures = period_math.period_pnl(getattr(engine_result, "daily_states", None) or [], date_from, valuation_date)
        period_nav_start_val = period_figures.nav_start if period_figures is not None else None
        period_net_flows_val = period_figures.net_flows if period_figures is not None else None
        period_pnl_val = period_figures.pnl if period_figures is not None else None
        period_ugl_start = period_figures.ugl_start if period_figures is not None else None
        period_ugl_end = period_figures.ugl_end if period_figures is not None else None
        period_ugl_delta = period_figures.ugl_delta if period_figures is not None else None
        period_book_value_start_val = period_figures.book_value_start if period_figures is not None else None
        period_market_value_start_val = period_figures.market_value_start if period_figures is not None else None
        period_realized_val: Decimal | None = None
        period_income_val: Decimal | None = None
        period_fees_taxes_val: Decimal | None = None
        period_other_result_val: Decimal | None = None

        if period_pnl_val is not None and period_ugl_delta is not None:
            # Realized, income, fees from accumulated values
            period_realized_val = _realized_accum
            period_income_val = _income_accum if _income_accum else Decimal("0")
            period_fees_taxes_val = _fees_taxes_accum if _fees_taxes_accum else Decimal("0")

            # Other result: residual that closes the identity
            # pnl = ugl_delta + realized + income - fees_taxes + other_result
            period_other_result_val = period_math.period_other_result(period_pnl_val, period_ugl_delta, period_realized_val, period_income_val, period_fees_taxes_val)

        # ── 6. Data quality report ──
        # "Valued at cost" is an *as-of* statement (dataQuality.transactionImplied:
        # "…as of {as_of_date}"): evaluate ONLY the valuation-date state, so an asset that
        # has since received a real market quote clears the warning even if it was
        # transaction-implied for most of its earlier history. The previous behaviour
        # unioned the flag across every day of the asset's lifetime, permanently flagging
        # any asset ever valued at cost — e.g. funds that only get quotes from their first
        # provider sync onward stayed flagged forever despite a fresh current price.
        # The grace period still suppresses a brand-new acquisition whose first market
        # price simply has not landed yet (e.g. BTP collocamento lag); it counts from the
        # last market quote (decision 30), see transaction_implied_assets_to_report.
        first_position_date_by_asset: dict[int, date_type] = {}
        for (_b_id, a_id), d in first_position_dates.items():
            if a_id not in first_position_date_by_asset or d < first_position_date_by_asset[a_id]:
                first_position_date_by_asset[a_id] = d

        implied_asset_ids: set[int] = set()
        if last_state is not None:
            implied_asset_ids = transaction_implied_assets_to_report(
                last_state.transaction_implied_asset_ids,
                last_state.transaction_implied_last_quote_dates,
                first_position_date_by_asset,
                last_state.date,
                TRANSACTION_IMPLIED_GRACE_DAYS,
            )

        transaction_implied_assets: list[MissingPriceAsset] = []
        for ps in end_positions:
            if ps.asset_id in implied_asset_ids:
                asset = assets_map.get(ps.asset_id)
                if not asset:
                    continue
                broker = brokers_map.get(ps.broker_id)
                transaction_implied_assets.append(
                    MissingPriceAsset(
                        asset_id=ps.asset_id,
                        symbol=asset.identifier_ticker,
                        name=asset.display_name,
                        broker_id=ps.broker_id,
                        broker_name=broker.name if broker else broker_names.get(ps.broker_id, f"Broker {ps.broker_id}"),
                        first_position_date=first_position_dates.get((ps.broker_id, ps.asset_id)),
                        quantity=ps.quantity,
                        open_cost_basis=ps.cost_basis if ps.cost_basis != 0 else None,
                        currency=base_currency,
                    )
                )

        # For manual assets (no provider, valued at cost): suppress MISSING_PRICE
        # They're already represented by TRANSACTION_IMPLIED which is expected behavior
        from backend.app.db.models import AssetProviderAssignment  # noqa: PLC0415

        provider_result = await self.db.execute(select(AssetProviderAssignment.asset_id))
        assets_with_provider = {row[0] for row in provider_result.fetchall()}
        # Remove from missing_price_assets if the asset is manual (no provider) AND implied (valued at cost)
        missing_price_assets = [a for a in missing_price_assets if a.asset_id in assets_with_provider or a.asset_id not in implied_asset_ids]
        # For truly manual assets (implied, no provider): suppress TRANSACTION_IMPLIED too
        # since cost valuation is their intended/permanent behavior
        manual_implied_ids = implied_asset_ids - assets_with_provider
        transaction_implied_assets = [a for a in transaction_implied_assets if a.asset_id not in manual_implied_ids]

        # VALUED_AT_COST: an open position with no price at all (no quote, no BUY or SELL), counted at its
        # book cost (J-17). Same grace as TRANSACTION_IMPLIED, counted from the asset's first acquisition:
        # it has no quote, and no BUY or SELL (an ADJUSTMENT or a TRANSFER opened it), so the BUY/SELL
        # first position date would list it at once. Only for an asset with a provider: for a manual
        # asset the cost is its intended value.
        first_acquisition_by_asset: dict[int, date_type] = {}
        for (_b_id, a_id), d in first_lot_txn_dates.items():
            if a_id not in first_acquisition_by_asset or d < first_acquisition_by_asset[a_id]:
                first_acquisition_by_asset[a_id] = d
        at_cost_ids = {ps.asset_id for ps in end_positions if ps.valuation_source == ValuationSource.ESTIMATED_AT_COST}
        at_cost_reported = transaction_implied_assets_to_report(at_cost_ids, {}, first_acquisition_by_asset, last_state.date, TRANSACTION_IMPLIED_GRACE_DAYS) if last_state is not None else set()
        valued_at_cost_assets: list[MissingPriceAsset] = []
        for ps in end_positions:
            if ps.asset_id not in at_cost_reported or ps.asset_id not in assets_with_provider:
                continue
            asset = assets_map.get(ps.asset_id)
            if not asset:
                continue
            broker = brokers_map.get(ps.broker_id)
            valued_at_cost_assets.append(
                MissingPriceAsset(
                    asset_id=ps.asset_id,
                    symbol=asset.identifier_ticker,
                    name=asset.display_name,
                    broker_id=ps.broker_id,
                    broker_name=broker.name if broker else broker_names.get(ps.broker_id, f"Broker {ps.broker_id}"),
                    first_position_date=first_lot_txn_dates.get((ps.broker_id, ps.asset_id)),
                    quantity=ps.quantity,
                    open_cost_basis=ps.cost_basis if ps.cost_basis != 0 else None,
                    currency=base_currency,
                )
            )

        # STALE_PRICE: an open position valued at a market price carried forward past the
        # threshold, for an asset with a provider — the case a price sync can fix. A manual
        # asset valued at its last trade price (crowdfunding, HOLD) is stale by design, and a
        # provider asset with no quote at all is TRANSACTION_IMPLIED's or VALUED_AT_COST's case. One entry per asset.
        stale_price_dates: dict[int, date_type] = {}
        for ps in end_positions:
            if not ps.valuation_stale or ps.valuation_source != ValuationSource.MARKET_PRICE:
                continue
            if ps.asset_id not in assets_with_provider or ps.valuation_reference_date is None:
                continue
            known = stale_price_dates.get(ps.asset_id)
            stale_price_dates[ps.asset_id] = ps.valuation_reference_date if known is None else max(known, ps.valuation_reference_date)
        stale_prices = [StalePriceAsset(asset_id=asset_id, name=assets_map[asset_id].display_name, last_price_date=last_date, stale_days=(valuation_date - last_date).days) for asset_id, last_date in sorted(stale_price_dates.items(), key=lambda item: (item[1], item[0])) if asset_id in assets_map]

        configured_fx_pairs, real_provider_fx_pairs = await self._get_configured_fx_pair_sets()
        all_missing_pairs.extend(_engine_missing_fx_pairs(engine_result, date_from, valuation_date))
        merged_missing_fx_pairs = self._merge_missing_pairs(all_missing_pairs)
        held_quote_facts = await self._held_asset_quote_facts(engine_result)
        data_quality = views.build_data_quality_report(
            missing_price_assets_dto=missing_price_assets,
            stale_prices_dto=stale_prices or None,
            missing_fx_pairs_dto=merged_missing_fx_pairs,
            transaction_implied_assets_dto=transaction_implied_assets if transaction_implied_assets else None,
            missing_cost_basis_assets=await self._missing_cost_basis_assets(engine_result) or None,
            invalid_split_assets=await self._invalid_split_assets(engine_result) or None,
            non_iso_currency_assets=self._non_iso_currency_assets(held_quote_facts) or None,
            report_currency=base_currency,
            valued_at_cost_assets_dto=valued_at_cost_assets or None,
            mwrr_available=mwrr_result is not None,
            share_mismatches=engine_result.share_mismatches,
            configured_fx_pairs=configured_fx_pairs,
            real_provider_fx_pairs=real_provider_fx_pairs,
            period_from=date_from,
            period_to=valuation_date,
        )

        # The day's change of the total P&L, from the engine's states of the valuation date and of the calendar day before.
        day_change = period_math.day_change(engine_result.daily_states, valuation_date)

        # Unrealized G/L of each broker's holdings, and of each asset type at each broker (the Dashboard treemap's groups).
        group_members: dict[tuple[int, str | None], list[tuple[Decimal | None, Decimal | None]]] = defaultdict(list)
        for holding in all_holdings:
            group_members[(holding.broker_id, None)].append((holding.current_value, holding.gain_loss))
            group_members[(holding.broker_id, holding.asset_type)].append((holding.current_value, holding.gain_loss))
        holding_groups: list[HoldingGroupGainLoss] = []
        for (group_broker_id, group_asset_type), members in sorted(group_members.items(), key=lambda item: (item[0][0], item[0][1] is not None, item[0][1] or "")):
            group_gain, group_ratio = group_gain_loss(members)
            holding_groups.append(
                HoldingGroupGainLoss(
                    broker_id=group_broker_id,
                    asset_type=group_asset_type,
                    gain_loss=Currency(code=base_currency, amount=group_gain) if group_gain is not None else None,
                    gain_loss_percent=group_ratio,
                )
            )

        return PortfolioSummary(
            net_worth=Currency(code=base_currency, amount=engine_nav),
            total_invested=Currency(code=base_currency, amount=total_invested),
            total_gain_loss=Currency(code=base_currency, amount=total_gl),
            total_gain_loss_percent=total_gl_pct,
            cash_total=Currency(code=base_currency, amount=engine_cash),
            cash_balances=cash_balances_list,
            market_value=Currency(code=base_currency, amount=engine_market_value),
            broker_nav_value=Currency(code=base_currency, amount=last_state.broker_nav_value) if last_state else None,
            in_transit_market_value=Currency(code=base_currency, amount=last_state.in_transit_market_value) if last_state and last_state.in_transit_market_value else None,
            open_cost_basis=Currency(code=base_currency, amount=last_state.open_cost_basis) if last_state else None,
            in_transit_book_value=Currency(code=base_currency, amount=last_state.in_transit_book_value) if last_state and last_state.in_transit_book_value else None,
            book_value=Currency(code=base_currency, amount=last_state.book_value) if last_state else None,
            unrealized_gain_loss=Currency(code=base_currency, amount=last_state.unrealized_gain_loss) if last_state else None,
            total_deposited=Currency(code=base_currency, amount=_total_deposited) if _total_deposited else None,
            total_withdrawn=Currency(code=base_currency, amount=_total_withdrawn) if _total_withdrawn else None,
            net_deposited_capital=Currency(code=base_currency, amount=_total_deposited - _total_withdrawn),
            period_nav_start=Currency(code=base_currency, amount=period_nav_start_val) if period_nav_start_val is not None else None,
            period_market_value_start=Currency(code=base_currency, amount=period_market_value_start_val) if period_market_value_start_val is not None else None,
            period_book_value_start=Currency(code=base_currency, amount=period_book_value_start_val) if period_book_value_start_val is not None else None,
            period_net_flows=Currency(code=base_currency, amount=period_net_flows_val) if period_net_flows_val is not None else None,
            period_pnl=Currency(code=base_currency, amount=period_pnl_val) if period_pnl_val is not None else None,
            period_unrealized_gain_loss_start=Currency(code=base_currency, amount=period_ugl_start) if period_ugl_start is not None else None,
            period_unrealized_gain_loss_end=Currency(code=base_currency, amount=period_ugl_end) if period_ugl_end is not None else None,
            period_unrealized_gain_loss_delta=Currency(code=base_currency, amount=period_ugl_delta) if period_ugl_delta is not None else None,
            period_unrealized_breakdown=_unrealized_breakdown_rows(engine_result, date_from, valuation_date, base_currency) if period_ugl_delta is not None else [],
            period_realized_gain_loss=Currency(code=base_currency, amount=period_realized_val) if period_realized_val is not None else None,
            period_income=Currency(code=base_currency, amount=period_income_val) if period_income_val is not None else None,
            period_fees_taxes=Currency(code=base_currency, amount=period_fees_taxes_val) if period_fees_taxes_val is not None else None,
            period_fees=Currency(code=base_currency, amount=_fees_accum) if _fees_accum else None,
            period_taxes=Currency(code=base_currency, amount=_taxes_accum) if _taxes_accum else None,
            period_other_result=Currency(code=base_currency, amount=period_other_result_val) if period_other_result_val is not None else None,
            twrr_percent=twrr_result,
            mwrr_annualized_percent=mwrr_result,
            mwrr_cumulative_percent=mwrr_cumulative,
            mwrr_period_days=mwrr_period_days,
            timing_effect_percent=timing_effect(mwrr_cumulative, twrr_result),
            pnl_change_1d=Currency(code=base_currency, amount=day_change.pnl_change) if day_change is not None else None,
            pnl_change_1d_vs_total_pnl_percent=day_change.vs_total_pnl if day_change is not None else None,
            pnl_change_1d_vs_nav_percent=day_change.vs_nav if day_change is not None else None,
            simple_roi_percent=simple_roi,
            allocation_by_type=_alloc_from_engine(alloc_type),
            allocation_by_sector=_alloc_from_engine(alloc_sector),
            allocation_by_geography=_alloc_from_engine(alloc_geo),
            allocation_by_asset=_alloc_from_engine(alloc_asset),
            holdings=all_holdings,
            holding_groups=holding_groups,
            by_broker=by_broker_list if include_breakdown else None,
            missing_fx_pairs=merged_missing_fx_pairs,
            missing_price_assets=missing_price_assets,
            data_quality=data_quality,
        )

    async def get_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> list[PortfolioHistoryPoint]:
        """Return the portfolio value series in steps via PortfolioCalculationEngine: see :meth:`get_history_steps`.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        steps = await self.get_history_steps(user_id, broker_ids, date_from, date_to, target_currency_override, _precomputed_engine_result)
        return steps.history

    async def get_history_steps(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> HistorySteps:
        """The history of ``[date_from, date_to]`` in steps, its ``range`` and its MWRR line (D-P4, contract §1.2, §2).

        Each point holds from its ``date`` to its ``through``: the values of every day in it, TWRR and ROI included, are
        the daily series' values of that day. The MWRR moves even on a quiet day, so it is not in the steps: the line has
        its true values at each step's ``date`` and ``through``, and at the month ends inside a long step.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder, mwrr_line_days  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,  # Always compute from t=0 for correct cumulative values
                date_to=date_to,
                target_currency=base_currency,
            )

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        window = views.window_range(date_from, date_to) if result.daily_states else None
        if window is None:
            return HistorySteps(range=None, history=[], mwrr_line=[])
        start, end = window

        # The first point pins the TWRR to 0, so the day after it may differ from it even when nothing happens
        pins = (start + timedelta(days=1),) if start < end else ()

        # ── TWRR and ROI on the days a step may start (a quiet day keeps both) ──
        nav_snapshots, cash_flows = views.build_performance_inputs(date_from, days=[*views.change_days(start, end, pins), end])
        period = rebase_to_period(nav_snapshots, cash_flows, date_from)
        period_cash_flows = list(period.cash_flows)
        period_nav_snapshots = list(period.nav_snapshots)
        twrr_map: dict[date_type, Decimal] = {}
        roi_map: dict[date_type, Decimal] = {}
        if period_nav_snapshots and period_cash_flows:
            twrr_map = {pt.date: pt.twrr for pt in calculate_twrr_series(period_nav_snapshots, period_cash_flows)}
            roi_map = {pt.date: pt.roi for pt in calculate_simple_roi_series(period_nav_snapshots, period_cash_flows)}

        # First point pinned to 0% for the TWRR (and the MWRR line): period-relative returns measured from inception are
        # 0 at the period start by definition. ROI is NOT pinned — it is an absolute ratio (NAV − net_invested)/net_invested,
        # so on the very first day it must already reflect any seeded cost-vs-market gap (e.g. an in-kind succession
        # seeded above/below market shows its day-1 gain/loss instead of a flat 0).
        def metrics(day: date_type) -> dict[str, Decimal | None]:
            return {"twrr": Decimal("0") if day == start else twrr_map.get(day), "roi": roi_map.get(day)}

        history_dicts = views.build_history(start, end, metrics=metrics, extra_days=pins)
        history = [PortfolioHistoryPoint(**point) for point in history_dicts]
        mwrr_line = await self._mwrr_line(views, date_from, mwrr_line_days(history_dicts), start)
        return HistorySteps(range=DateSpan(start=start, end=end), history=history, mwrr_line=mwrr_line)

    @staticmethod
    async def _mwrr_line(views: Any, date_from: date_type | None, days: list[date_type], start: date_type) -> list[MwrrLinePoint]:
        """The MWRR line's true points on ``days`` (D-P4, contract §2): each the period MWRR ending that day — the value
        the daily line gives there, bit for bit (:func:`returns.period_mwrr_series`, every point its own solve) — and its
        cumulative form from the period's start; the first day pinned to 0."""
        nav_snapshots, cash_flows = views.build_performance_inputs(date_from, days=days)
        period = rebase_to_period(nav_snapshots, cash_flows, date_from)
        period_nav_snapshots, period_cash_flows = list(period.nav_snapshots), list(period.cash_flows)
        mwrr_map: dict[date_type, Decimal | None] = {}
        if period_nav_snapshots and period_cash_flows:
            # The same rule as the card, at every point (D-MF5): no rate where the card would have none.
            mwrr_series = await asyncio.to_thread(period_mwrr_series, period_nav_snapshots, period_cash_flows)
            mwrr_map = {pt.date: pt.mwrr for pt in mwrr_series}
        period_start = period_nav_snapshots[0].date if period_nav_snapshots else None
        line: list[MwrrLinePoint] = []
        for day in days:
            if day == start:
                line.append(MwrrLinePoint(date=day, annualized=Decimal("0"), cumulative=Decimal("0")))
                continue
            annualized = mwrr_map.get(day)
            line.append(MwrrLinePoint(date=day, annualized=annualized, cumulative=annualized_to_cumulative(annualized, (day - period_start).days if period_start else 0)))
        return line

    async def get_broker_pnl_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> list[BrokerPnlHistory]:
        """Per-broker additive P&L history for the GrowthChart P&L broker overlay (G1a).

        Each broker's points sum to the scope-aggregate PortfolioHistoryPoint.total_pnl
        for every date, by construction (see DailyStateBuilder §4.2 / BrokerDailyContribution).

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,  # Always compute from t=0 for correct cumulative values
                date_to=date_to,
                target_currency=base_currency,
            )

        if not result.daily_states:
            return []

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        by_broker = views.build_broker_pnl_history(date_from, date_to)
        if not by_broker:
            # A window holding no state: the whole-history build still listed every broker, with no point. Otherwise
            # the window lists them all, in the same order: every state carries every broker of the scope (DailyStateBuilder)
            states = (segment.state for segment in result.daily_states.segments) if isinstance(result.daily_states, DailyStates) else result.daily_states
            by_broker = {broker_id: [] for state in states for broker_id in state.broker_contributions}

        broker_pnl_history: list[BrokerPnlHistory] = []
        for broker_id, points in by_broker.items():
            broker = await self._get_broker(broker_id)
            broker_name = broker.name if broker else f"Broker {broker_id}"
            broker_pnl_history.append(BrokerPnlHistory(broker_id=broker_id, broker_name=broker_name, points=[BrokerPnlHistoryPoint(**point) for point in points]))

        return broker_pnl_history

    async def get_pnl_candles(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> PnlCandleSeries:
        """Synthetic total-P&L candle series for the GrowthChart P&L candles submode (G1b).

        Requires the engine run itself to have been computed with include_candles=True —
        when called standalone (no _precomputed_engine_result) this runs its own engine pass
        with that flag; when called from get_report() the shared engine result must already
        have been computed with query.include_pnl_candles, or every day comes back with no
        candle (silently empty, not wrong — the L1/L2 cache keys both include the flag so a
        cache hit can never silently return the wrong shape here).
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,  # Always compute from t=0 for correct cumulative values
                date_to=date_to,
                target_currency=base_currency,
                include_candles=True,
            )

        if not result.daily_states:
            return PnlCandleSeries(points=[])

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        return PnlCandleSeries(points=[PnlCandlePoint(**point) for point in views.build_pnl_candles(date_from, date_to)])

    async def _signed_transaction_sums_by_date(
        self,
        accesses: list,
        tx_types: set[TransactionType],
        base_currency: str,
        date_from: date_type | None,
        date_to: date_type | None,
        native_cash: NativeCash | None = None,
    ) -> tuple[dict[date_type, dict[str, Decimal]], list[str]]:
        """Signed sums of ``tx_types`` by date in (date_from, date_to], and the pairs left out.

        Read from the native cash (financial_math.native_cash), the same reconstruction the
        engine and get_summary() use: each movement at its broker's share (F2), converted at
        its own date; a movement with no rate is left out of the sums and its pair reported.
        Without date_to the window stops at today, the engine's horizon. ``native_cash`` is
        the engine's own when the caller already ran it (get_report); otherwise one is built
        here from the requested types. Shared by get_income_history/get_cost_history/
        get_deposit_history (G1c, batch 2), which differ only in the types they read and how
        they combine the per-type sums.
        """
        horizon = date_to or date_type.today()
        if native_cash is None:
            movements = []
            for access in accesses:
                share = effective_share(access.role, access.share_percentage)
                for tx in await self._get_transactions(access.broker_id, tx_types=tx_types, date_to=horizon):
                    movement = cash_movement_from_transaction(tx, share=share)
                    if movement is not None:
                        movements.append(movement)
            movements.sort(key=lambda movement: (movement.date, movement.movement_id or 0))
            native_cash = await compute_native_cash(self.db, movements, report_currency=base_currency, rates_until=horizon)
        types = {tx_type.value for tx_type in tx_types}
        sums_by_date = native_cash.sums_by_date(date_from, horizon, types)
        missing_fx_pairs = [missing.pair for missing in native_cash.missing_conversions(date_from, horizon, types)]
        return sums_by_date, missing_fx_pairs

    async def get_income_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_native_cash: NativeCash | None = None,
    ) -> IncomeHistorySeries:
        """Signed daily DIVIDEND/INTEREST income history for the GrowthChart P&L income
        submode (G1c, plan §3.4/§4.4).

        Read from the native cash (financial_math.native_cash), the reconstruction
        get_summary() also reads its period income from: same (date_from, date_to]
        boundary, same F2 role-aware share applied once, same conversion at each row's
        own date, so sum(dividend)+sum(interest) reproduces PortfolioSummary.period_income
        exactly for the same scope/window, by construction. get_report() passes the
        engine's own native cash; a standalone call builds one from the income rows.
        """
        base_currency = target_currency_override or await self._get_base_currency(user_id)
        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return IncomeHistorySeries(points=[])

        sums_by_date, missing_fx_pairs = await self._signed_transaction_sums_by_date(accesses, {TransactionType.DIVIDEND, TransactionType.INTEREST}, base_currency, date_from, date_to, _precomputed_native_cash)

        # Sparse series: only dates with actual DIVIDEND/INTEREST activity, never a
        # dense day-by-day zero-filled series (plan §3.4 — "sparse economic flows").
        points = [
            IncomeHistoryPoint(
                date=d,
                dividend=Currency(code=base_currency, amount=type_sums.get(TransactionType.DIVIDEND, Decimal("0"))),
                interest=Currency(code=base_currency, amount=type_sums.get(TransactionType.INTEREST, Decimal("0"))),
            )
            for d, type_sums in sorted(sums_by_date.items())
        ]
        return IncomeHistorySeries(points=points, missing_fx_pairs=sorted(missing_fx_pairs))

    async def get_cost_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_native_cash: NativeCash | None = None,
    ) -> CostHistorySeries:
        """Signed daily FEE+TAX cost history for the GrowthChart P&L income submode's
        costs dimension (batch 2). Same native-cash read as get_income_history (see
        _signed_transaction_sums_by_date). FEE and TAX are
        summed together into one "cost" figure — matching the dashboard's existing
        "Fees & taxes" KPI grouping — preserving the raw (negative) Transaction.amount
        sign rather than flipping to a positive magnitude, same signed-fidelity policy
        as income.
        """
        base_currency = target_currency_override or await self._get_base_currency(user_id)
        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return CostHistorySeries(points=[])

        sums_by_date, missing_fx_pairs = await self._signed_transaction_sums_by_date(accesses, {TransactionType.FEE, TransactionType.TAX}, base_currency, date_from, date_to, _precomputed_native_cash)

        points = [CostHistoryPoint(date=d, cost=Currency(code=base_currency, amount=sum(type_sums.values(), Decimal("0")))) for d, type_sums in sorted(sums_by_date.items())]
        return CostHistorySeries(points=points, missing_fx_pairs=sorted(missing_fx_pairs))

    async def get_deposit_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_native_cash: NativeCash | None = None,
    ) -> DepositHistorySeries:
        """Daily DEPOSIT history for the GrowthChart P&L income submode's deposit-size
        dimension (batch 2). Same native-cash read as get_income_history
        (see _signed_transaction_sums_by_date).
        """
        base_currency = target_currency_override or await self._get_base_currency(user_id)
        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return DepositHistorySeries(points=[])

        sums_by_date, missing_fx_pairs = await self._signed_transaction_sums_by_date(accesses, {TransactionType.DEPOSIT}, base_currency, date_from, date_to, _precomputed_native_cash)

        points = [DepositHistoryPoint(date=d, deposit=Currency(code=base_currency, amount=type_sums.get(TransactionType.DEPOSIT, Decimal("0")))) for d, type_sums in sorted(sums_by_date.items())]
        return DepositHistorySeries(points=points, missing_fx_pairs=sorted(missing_fx_pairs))

    async def get_acquisition_funding_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> AcquisitionFundingSeries:
        """New-vs-reinvested BUY funding split for the GrowthChart P&L income submode's
        acquisition-size dimension (batch 2, plan §5.2).

        Unlike cost/deposit/income (pure transaction scans), this REQUIRES an engine
        run: the new-vs-reinvested split depends on the running capital/returns pool
        state built up over the ENTIRE prior transaction history, not just the day's
        own transactions in isolation — mirrors get_pnl_candles()'s
        include_candles=True requirement exactly (same
        _precomputed_engine_result/standalone dual-mode, same "flag must be set on
        the shared engine run or every day comes back empty" caveat).
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

        base_currency = target_currency_override or await self._get_base_currency(user_id)
        if _precomputed_engine_result is not None:
            result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,  # Always compute from t=0 for correct cumulative pool state
                date_to=date_to,
                target_currency=base_currency,
                include_acquisition_funding=True,
            )

        if not result.daily_states:
            return AcquisitionFundingSeries(points=[])

        views = DerivedViewsBuilder(result.daily_states, base_currency)
        raw_points = views.build_acquisition_funding(date_from, date_to)
        # Canonical (date_from, date_to] boundary — exclusive start, inclusive end.
        # NOTE the deliberate difference from get_pnl_candles/get_broker_pnl_history,
        # whose engine-backed slicing this method otherwise mirrors: those two are
        # LEVEL series (a cumulative P&L value per day), so the period's opening day
        # must be shown as the baseline. This one is a FLOW series (that day's own BUY
        # split), so a BUY dated exactly on date_from belongs to the PREVIOUS period —
        # the same rule already applied to its five co-rendered Income-submode
        # siblings (income/cost/deposit). Using >= here would make a BUY on date_from
        # draw a bar while a DIVIDEND on that very same date draws none.
        sliced_points = [AcquisitionFundingPoint(date=p["date"], from_new_capital=p["from_new_capital"], from_reinvested=p["from_reinvested"]) for p in raw_points if (date_from is None or p["date"] > date_from) and (date_to is None or p["date"] <= date_to)]
        return AcquisitionFundingSeries(points=sliced_points)

    async def get_positions_contribution(  # noqa: C901 — TODO(P2-refactor): nested broker/asset accumulation with per-position valuation branches
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
        _precomputed_engine_result=None,
    ) -> PositionsContribution:
        """Compute per-asset period P&L contribution for dashboard Performance view.

        For each (broker_id, asset_id) pair with activity in the period, computes:
        - unrealized_delta: change in unrealized P&L over the period
        - realized_gain_loss: gain/loss from SELLs in the period
        - income: DIVIDEND/INTEREST attributed to this asset
        - fees_taxes: FEE/TAX attributed to this asset
        - period_pnl: total = unrealized_delta + realized + income - fees_taxes

        Fees/taxes without asset_id go to raw unallocated buckets plus UX-ready
        other_effects rows. Each broker's exchange result on foreign cash is an
        other_effects row of its own ("FX on cash"), ahead of the reconciliation residual.
        """
        today = date_type.today()
        effective_end = date_to or today
        base_currency = target_currency_override or await self._get_base_currency(user_id)

        accesses = await self._get_user_broker_access(user_id, broker_ids)
        if not accesses:
            return PositionsContribution(gross_gains=Decimal("0"), gross_losses=Decimal("0"))

        engine_result = _precomputed_engine_result
        if engine_result is None:
            from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

            engine = PortfolioCalculationEngine(self.db)
            engine_result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,
                date_to=date_to,
                target_currency=base_currency,
                period_start=date_from,
            )
        elif date_from is not None and engine_result.position_states_start_date != date_from:
            # A shared run taken for another period start has no positions at this one's: replay with it.
            from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine  # noqa: PLC0415

            engine_result = await PortfolioCalculationEngine(self.db).calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,
                date_to=date_to,
                target_currency=base_currency,
                period_start=date_from,
            )

        # Quantity-affecting transactions: BUY/SELL plus in-kind ADJUSTMENT and TRANSFER,
        # mirroring _LOT_AFFECTING_TYPES / the engine's position model. Restricting this to
        # {BUY, SELL} made ADJUSTMENT/TRANSFER-seeded positions (e.g. in-kind succession
        # transfers) collapse to qty 0 at period end -> reported as fully-sold with no value
        # or annualized return, diverging from the holdings view where they are held.
        _QTY_TYPES = _LOT_AFFECTING_TYPES

        # Per-position accumulators
        per_realized: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        per_cost_sold: dict[tuple[int, int], Decimal] = defaultdict(Decimal)
        per_sales: dict[tuple[int, int], int] = defaultdict(int)

        # ── Income / Fees with asset_id attribution: the period's cash flows of the native
        # cash (financial_math.native_cash), the same the summary's period income and fees
        # read. Signed income keeps legacy negative DIVIDEND/INTEREST corrections (plan §4.4);
        # fees and taxes are absolute. The unallocated sums keep the access order.
        native_cash = _engine_native_cash(engine_result, base_currency)
        flows = native_cash.flows(date_from, effective_end)
        per_income = flows.income_by_position
        per_fees_taxes = flows.costs_by_position
        access_order = {access.broker_id: index for index, access in enumerate(accesses)}
        unalloc_income = dict(sorted(flows.unallocated_income.items(), key=lambda item: access_order.get(item[0], len(access_order))))
        unalloc_fees = dict(sorted(flows.unallocated_costs.items(), key=lambda item: access_order.get(item[0], len(access_order))))

        # Track all positions with lot-affecting activity (BUY/SELL/ADJUSTMENT/TRANSFER)
        position_info: dict[tuple[int, int], dict] = {}
        # Holding-transaction streams per (broker, asset) for FIFO oldest-open-lot derivation.
        lot_txns_by_key: dict[tuple[int, int], list[Transaction]] = defaultdict(list)

        for access in accesses:
            broker_id = access.broker_id
            broker = await self._get_broker(broker_id)
            broker_name = broker.name if broker else f"Broker {broker_id}"

            broker_txns = await self._get_transactions(broker_id, date_to=effective_end)

            # ── Positions: every (broker, asset) whose quantity a transaction ever moved ──
            # The owner's share is the engine's: its boundary states are already scaled.
            held_asset_ids: dict[int, None] = {}  # in the order of each asset's first transaction
            for tx in broker_txns:
                if tx.asset_id is not None and tx.type in _QTY_TYPES:
                    lot_txns_by_key[(broker_id, tx.asset_id)].append(tx)
                    held_asset_ids.setdefault(tx.asset_id, None)

            for asset_id in held_asset_ids:
                asset = await self._get_asset(asset_id)
                if not asset:
                    continue
                position_info[(broker_id, asset_id)] = {"asset": asset, "broker_name": broker_name}

        # ── Realized gain/loss from SELLs and outgoing ADJUSTMENTs (proceeds 0, N78-1) in period: proceeds minus the
        # historical cost the engine's average-cost pool gave up (base currency, owner share applied) ──
        for sale in _period_realized_sales(engine_result.realized_sales, date_from, date_to):
            gain = realized_gain(sale.proceeds, sale.cost)
            if gain is None:
                continue
            pos_key = (sale.broker_id, sale.asset_id)
            per_realized[pos_key] += gain
            per_cost_sold[pos_key] += sale.cost
            per_sales[pos_key] += 1

        # ── Unrealized change per position, from the engine's values at the period's boundaries ──
        # The positions held at the end of the period's start day and at its end, valued as the portfolio values them
        # (trade marks, split adjustment, estimate at cost, the boundary day's rate): the rows' unrealized changes add up
        # to the period's ugl_delta. An internal transfer inside the period splits the result between the two brokers.
        contributions: list[AssetPeriodContribution] = []
        start_states = {(ps.broker_id, ps.asset_id): ps for ps in engine_result.position_states_start} if date_from is not None else {}
        end_states = {(ps.broker_id, ps.asset_id): ps for ps in engine_result.position_states_end}
        tract_adjustments = transfer_tract_adjustments(engine_result.internal_asset_transfers, date_from, effective_end)
        moved_out = transfer_costs_moved_out(engine_result.internal_asset_transfers, date_from, effective_end)
        moved_in = transfer_tracts_moved_in(engine_result.internal_asset_transfers, date_from, effective_end)

        lot_split_ids = await split_linked_ids(self.db, [tx for txns in lot_txns_by_key.values() for tx in txns])
        # MF-A10: the moves at the owner's share, as the engine's quantities the rows test against the dust threshold
        lot_shares = {access.broker_id: effective_share(access.role, access.share_percentage) for access in accesses}
        lot_moves = {key: quantity_moves(txns, lot_split_ids, share=lot_shares[key[0]]) for key, txns in lot_txns_by_key.items()}
        oldest_open_lot_dates: dict[tuple[int, int], Optional[date_type]] = {key: oldest_open_lot_date(moves) for key, moves in lot_moves.items()}

        for pos_key, info in position_info.items():
            broker_id, asset_id = pos_key
            asset = info["asset"]
            start_state = start_states.get(pos_key)
            end_state = end_states.get(pos_key)
            qty_at_start = start_state.quantity if start_state is not None else Decimal("0")
            qty_at_end = end_state.quantity if end_state is not None else Decimal("0")
            is_fully_sold = qty_at_end <= _QUANTITY_DUST_THRESHOLD

            # A dust residual counts as not held: no value, no unrealized of its own.
            ug_start: Decimal | None = None
            ug_end: Decimal | None = None
            cb_end: Decimal | None = None
            start_value: Decimal | None = Decimal("0") if date_from is None or qty_at_start <= _QUANTITY_DUST_THRESHOLD else None
            end_value: Decimal | None = Decimal("0") if qty_at_end <= _QUANTITY_DUST_THRESHOLD else None
            if start_state is not None and qty_at_start > _QUANTITY_DUST_THRESHOLD:
                start_value = start_state.market_value
                ug_start = start_state.unrealized_pnl
            if end_state is not None and qty_at_end > _QUANTITY_DUST_THRESHOLD:
                end_value = end_state.market_value
                ug_end = end_state.unrealized_pnl
                cb_end = end_state.cost_basis if end_state.cost_complete else None

            # The period P&L of the row (financial_math.portfolio.contributions, the one home of the formula)
            realized = per_realized.get(pos_key)
            income = per_income.get(pos_key)
            fees = per_fees_taxes.get(pos_key)
            row_pnl = position_period_pnl(
                held_at_start=qty_at_start > _QUANTITY_DUST_THRESHOLD and start_state is not None,
                held_at_end=qty_at_end > _QUANTITY_DUST_THRESHOLD,
                unrealized_start=ug_start,
                unrealized_end=ug_end,
                transfer_adjustment=tract_adjustments.get(pos_key),
                realized=realized,
                income=income,
                fees=fees,
            )
            unrealized_delta, period_pnl = row_pnl.unrealized_delta, row_pnl.period_pnl
            has_period_activity = any(value is not None and value != 0 for value in (realized, income, fees))
            has_boundary_position = qty_at_start > _QUANTITY_DUST_THRESHOLD or qty_at_end > _QUANTITY_DUST_THRESHOLD

            if not has_period_activity and not has_boundary_position and period_pnl is None:
                continue

            # R4 (financial_math.portfolio.contributions): the return on the start value; the annualized return over
            # the position's window, on the end cost for a position opened inside the period; for a position closed in
            # it, the annualized return on the cost it sold over its flight time.
            period_pnl_pct = period_return_on_start(period_pnl, start_value)
            # MF-A9: a position opened in the period that received units by a counted tract, and from which no unit left in
            # the period, counts them, in its fallback base, from their value on arrival, as its result does
            row_exits = exits_in(lot_moves.get(pos_key, []), date_from, effective_end)
            period_annualized = annualized_period_return(
                period_pnl,
                start_value,
                cb_end,
                window_from=window_start(date_from, oldest_open_lot_dates.get(pos_key)),
                end=effective_end,
                moved_in=moved_in.get(pos_key) if row_exits == 0 else None,
            )
            if is_fully_sold:
                opened, closed = closed_position_window(lot_moves.get(pos_key, []))
                # MF-A5: the base is the cost of every unit that left, sold or moved by a counted tract; a unit that left
                # another way leaves no base, and the general rule stands. MF-A8: units received by a counted tract enter
                # the base at their value on arrival, as they enter the row's result
                base = closed_position_base(
                    per_cost_sold.get(pos_key, Decimal("0")),
                    per_sales.get(pos_key, 0),
                    moved_out.get(pos_key),
                    row_exits,
                    moved_in.get(pos_key),
                )
                closed_annualized = closed_position_annualized(period_pnl, base, opened, closed, date_from)
                if closed_annualized is not None:
                    period_annualized = closed_annualized

            contributions.append(
                AssetPeriodContribution(
                    asset_id=asset_id,
                    asset_name=asset.display_name,
                    asset_ticker=asset.identifier_ticker,
                    asset_type=asset.asset_type.value if asset.asset_type else "Unknown",
                    broker_id=broker_id,
                    broker_name=info["broker_name"],
                    period_unrealized_delta=unrealized_delta,
                    period_realized_gain_loss=realized if realized else None,
                    period_income=income if income else None,
                    period_fees_taxes=fees if fees else None,
                    period_pnl=period_pnl,
                    period_pnl_percent=period_pnl_pct,
                    # Each component on the same base as the row's return (P4, the Performance tooltip).
                    period_unrealized_delta_percent=period_return_on_start(unrealized_delta, start_value),
                    period_realized_gain_loss_percent=period_return_on_start(realized if realized else None, start_value),
                    period_income_percent=period_return_on_start(income if income else None, start_value),
                    period_fees_taxes_percent=period_return_on_start(fees if fees else None, start_value),
                    annualized_return=period_annualized,
                    start_value=start_value,
                    end_value=end_value,
                    is_fully_sold=is_fully_sold,
                    oldest_open_lot_date=oldest_open_lot_dates.get(pos_key),
                )
            )

        # Include positions with income/fees only (no BUY/SELL)
        for bid, aid in sorted(set(per_income.keys()) | set(per_fees_taxes.keys())):
            if (bid, aid) not in position_info:
                asset = await self._get_asset(aid)
                broker = await self._get_broker(bid)
                income = per_income.get((bid, aid), Decimal("0"))
                fees = per_fees_taxes.get((bid, aid), Decimal("0"))
                # Nonzero, not positive-only: a legacy negative income correction must
                # still surface here, never silently dropped (plan §4.4).
                if income == 0 and fees == 0:
                    continue
                pnl = income - fees
                contributions.append(
                    AssetPeriodContribution(
                        asset_id=aid,
                        asset_name=asset.display_name if asset else f"Asset {aid}",
                        asset_ticker=asset.identifier_ticker if asset else None,
                        asset_type=asset.asset_type.value if asset and asset.asset_type else "Unknown",
                        broker_id=bid,
                        broker_name=broker.name if broker else f"Broker {bid}",
                        period_income=income if income else None,
                        period_fees_taxes=fees if fees > 0 else None,
                        period_pnl=pnl,
                        start_value=Decimal("0"),
                        end_value=Decimal("0"),
                        is_fully_sold=True,
                        oldest_open_lot_date=oldest_open_lot_dates.get((bid, aid)),
                    )
                )

        # Build unallocated
        unallocated: list[UnallocatedContribution] = []
        other_effects: list[OtherPeriodEffect] = []
        for bid in set(unalloc_income.keys()) | set(unalloc_fees.keys()):
            inc = unalloc_income.get(bid)
            fee = unalloc_fees.get(bid)
            # inc: nonzero check (legacy negative corrections must stay visible, plan §4.4).
            # fee: unchanged positive-only check — fee/tax signed corrections are out of
            # this plan's scope.
            if inc or (fee and fee > 0):
                broker = await self._get_broker(bid)
                broker_name = broker.name if broker else f"Broker {bid}"
                unallocated.append(
                    UnallocatedContribution(
                        broker_id=bid,
                        broker_name=broker_name,
                        unallocated_income=inc if inc else None,
                        unallocated_fees_taxes=fee if fee and fee > 0 else None,
                    )
                )
                if inc:
                    other_effects.append(
                        OtherPeriodEffect(
                            description="Unallocated income",
                            category="Income",
                            period_pnl=inc,
                            broker_id=bid,
                            broker_name=broker_name,
                        )
                    )
                if fee and fee > 0:
                    other_effects.append(
                        OtherPeriodEffect(
                            description="Unallocated costs",
                            category="Cost",
                            period_pnl=Decimal("0") - fee,
                            broker_id=bid,
                            broker_name=broker_name,
                        )
                    )

        period_figures = period_math.period_pnl(getattr(engine_result, "daily_states", None) or [], date_from, effective_end)
        period_pnl_total = period_figures.pnl if period_figures is not None else None
        period_ugl_delta = period_figures.ugl_delta if period_figures is not None else None
        period_other_result: Decimal | None = None
        if period_pnl_total is not None and period_ugl_delta is not None:
            total_realized = sum(per_realized.values(), Decimal("0"))
            total_income = sum(per_income.values(), Decimal("0")) + sum(unalloc_income.values(), Decimal("0"))
            total_fees = sum(per_fees_taxes.values(), Decimal("0")) + sum(unalloc_fees.values(), Decimal("0"))
            period_other_result = period_math.period_other_result(period_pnl_total, period_ugl_delta, total_realized, total_income, total_fees)

        if period_other_result is not None:
            # FX on cash (financial_math.native_cash): each broker's exchange result on foreign
            # cash, a row of its own in access order; the residual drops by the same amount.
            # Below CONVERSION_DUST a figure is the rounding of two conversions of the same
            # cash, not a result: with foreign cash in scope neither row shows it. A
            # report-currency-only scope keeps the exact residual rule.
            residual = period_other_result
            exchange_results = native_cash.exchange_results(date_from, effective_end)
            for bid in sorted(exchange_results, key=lambda broker_id: access_order.get(broker_id, len(access_order))):
                exchange_result = exchange_results[bid]
                if abs(exchange_result) < CONVERSION_DUST:
                    continue
                broker = await self._get_broker(bid)
                other_effects.append(
                    OtherPeriodEffect(
                        description="FX on cash",
                        category="Other",
                        period_pnl=exchange_result,
                        broker_id=bid,
                        broker_name=broker.name if broker else f"Broker {bid}",
                    )
                )
                residual -= exchange_result
            # B5 (financial_math.portfolio.period): the gain securities accrued at a broker outside the view before they
            # crossed its boundary, a row per broker in the same order; the residual drops by the same amount.
            transfer_results = period_math.market_value_transfer_results(getattr(engine_result, "market_value_transfers", None) or [], date_from, effective_end)
            for bid in sorted(transfer_results, key=lambda broker_id: access_order.get(broker_id, len(access_order))):
                transfer_result = transfer_results[bid]
                if abs(transfer_result) < CONVERSION_DUST:
                    continue
                broker = await self._get_broker(bid)
                other_effects.append(
                    OtherPeriodEffect(
                        description="Transfers at market value",
                        category="Other",
                        period_pnl=transfer_result,
                        broker_id=bid,
                        broker_name=broker.name if broker else f"Broker {bid}",
                    )
                )
                residual -= transfer_result
            show_residual = abs(residual) >= CONVERSION_DUST if native_cash.foreign_cash_broker_ids else residual != 0
            if show_residual:
                other_effects.append(
                    OtherPeriodEffect(
                        description="Other / reconciliation residual",
                        category="Other",
                        period_pnl=residual,
                        broker_id=None,
                        broker_name=None,
                    )
                )

        gross_gains = sum(c.period_pnl for c in contributions if c.period_pnl and c.period_pnl > 0) or Decimal("0")
        gross_losses = sum(abs(c.period_pnl) for c in contributions if c.period_pnl and c.period_pnl < 0) or Decimal("0")

        return PositionsContribution(
            positions=contributions,
            unallocated=unallocated,
            other_effects=other_effects,
            gross_gains=gross_gains,
            gross_losses=gross_losses,
        )

    async def get_report(  # noqa: C901 — TODO(P2-refactor): include-flag orchestration
        self,
        user_id: int,
        query: PortfolioReportQuery,
    ) -> PortfolioReportResponse:
        """Run the engine ONCE and return all requested views in a single response.

        Avoids the need for separate summary/history/allocation-history calls from
        the dashboard. A single POST /portfolio/report is enough for a full page load.

        Uses Layer 2 cache: keyed by (user, scope, date_range, query_features, data_fingerprint).
        """
        from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder  # noqa: PLC0415
        from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine, compute_portfolio_fx_cache_identity, compute_tx_fingerprint  # noqa: PLC0415

        today = date_type.today()
        base_currency = query.target_currency or await self._get_base_currency(user_id)
        date_from = query.date_range.resolved_start() if query.date_range else None
        date_to = query.date_range.resolved_end() if query.date_range else None
        # R13-SEC7-1: the report — history, summary, metadata, cache key — ends by latest_range_end(), and a start after
        # that end moves to it
        if date_to is not None:
            date_to = min(date_to, latest_range_end())
        effective_date_to = date_to or today
        if date_from is not None:
            date_from = min(date_from, effective_date_to)

        # ── 0. Layer 2 cache check ──
        # Build a fingerprint from transactions + prices to detect data changes
        l2_key = None
        broker_ids_for_scope = query.broker_ids
        scope_stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        if broker_ids_for_scope:
            scope_stmt = scope_stmt.where(BrokerUserAccess.broker_id.in_(broker_ids_for_scope))
        scope_result = await self.db.execute(scope_stmt)
        scope_accesses = list(scope_result.scalars().all())
        scope_broker_ids = sorted({a.broker_id for a in scope_accesses})
        # Role/share edits change every scaled number but not the data
        # fingerprints — they must bust the cache (F2 follow-up).
        access_fp = tuple(sorted((a.broker_id, getattr(a.role, "value", a.role), str(a.share_percentage)) for a in scope_accesses))

        if scope_broker_ids:
            # Quick fingerprints for cache key (lightweight queries)
            tx_stmt = select(Transaction).where(Transaction.broker_id.in_(scope_broker_ids)).order_by(Transaction.date, Transaction.id)
            tx_result = await self.db.execute(tx_stmt)
            all_txs_for_fp = list(tx_result.scalars().all())
            tx_fp = compute_tx_fingerprint(all_txs_for_fp) if all_txs_for_fp else "no_txs"

            held_ids = {tx.asset_id for tx in all_txs_for_fp if tx.asset_id and tx.quantity and tx.quantity != 0}
            price_fp = "no_assets"
            if held_ids:
                pf_stmt = select(func.count(PriceHistory.id), func.max(PriceHistory.fetched_at)).where(PriceHistory.asset_id.in_(held_ids)).where(PriceHistory.date <= effective_date_to)
                pf_row = (await self.db.execute(pf_stmt)).one()
                price_fp = f"{pf_row[0] or 0}:{pf_row[1].isoformat() if pf_row[1] else 'none'}"

            fx_fp = await compute_portfolio_fx_cache_identity(
                self.db,
                set(scope_broker_ids),
                base_currency,
                effective_date_to,
            )
            yield_on_cost_fp = await compute_yield_on_cost_dependency_identity(
                self.db,
                user_id=user_id,
                scope_transactions=all_txs_for_fp,
                as_of_date=effective_date_to,
            )

            l2_key = (
                user_id,
                tuple(scope_broker_ids),
                tuple(sorted(broker_ids_for_scope)) if broker_ids_for_scope else None,
                access_fp,
                base_currency,
                str(date_from),
                str(date_to),
                str(effective_date_to),
                query.include_summary,
                query.include_history,
                query.include_allocation_history,
                query.include_breakdown,
                query.include_positions_contribution,
                query.include_broker_pnl_history,
                query.include_pnl_candles,
                query.include_income_history,
                query.include_cost_history,
                query.include_deposit_history,
                query.include_acquisition_funding,
                tx_fp,
                price_fp,
                fx_fp,
                yield_on_cost_fp,
            )

            cached, hit = _portfolio_l2_cache.get(l2_key)
            if hit:
                _logger.debug("Portfolio L2 cache hit", user_id=user_id)
                return cached

        # ── 1. Single engine run ──
        engine = PortfolioCalculationEngine(self.db)
        engine_result = await engine.calculate(
            user_id=user_id,
            broker_ids=query.broker_ids,
            date_from=None,  # always from t=0 for correct cumulative values
            date_to=effective_date_to,
            target_currency=base_currency,
            include_candles=query.include_pnl_candles,
            include_acquisition_funding=query.include_acquisition_funding,
            # The positions at the end of the period's start day, for the Performance table (MF-A).
            period_start=date_from if query.include_positions_contribution else None,
        )

        views = DerivedViewsBuilder(engine_result.daily_states, base_currency)

        included: list[str] = []

        # ── 2. Summary (reuses get_summary logic inline to share engine result) ──
        summary: PortfolioSummary | None = None
        if query.include_summary:
            included.append("summary")
            summary = await self.get_summary(
                user_id=user_id,
                broker_ids=query.broker_ids,
                target_currency_override=base_currency,
                include_breakdown=query.include_breakdown,
                date_from=date_from,
                date_to=effective_date_to,
                _precomputed_engine_result=engine_result,
            )

        # ── 3. History ──
        history: list[PortfolioHistoryPoint] | None = None
        mwrr_line: list[MwrrLinePoint] | None = None
        if query.include_history:
            included.append("history")
            history_steps = await self.get_history_steps(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )
            history, mwrr_line = history_steps.history, history_steps.mwrr_line

        # ── 4. Allocation history (all 4 dimensions from same engine result) ──
        alloc_history: AllocationHistoryDimensions | None = None
        if query.include_allocation_history:
            included.append("allocation_history")
            history_asset_names = {asset_id: asset.display_name for asset_id, asset in (await self._get_assets_map(views.allocation_asset_ids(date_from))).items()}
            alloc_history = AllocationHistoryDimensions(
                type=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("type", date_from=date_from)],
                sector=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("sector", date_from=date_from)],
                geography=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("geography", date_from=date_from)],
                asset=[AllocationHistoryPoint(**p) for p in views.build_asset_allocation_history(history_asset_names, date_from=date_from)],
            )

        # ── 4b. Positions contribution (per-asset period P&L attribution) ──
        positions_contribution: PositionsContribution | None = None
        if query.include_positions_contribution:
            included.append("positions_contribution")
            positions_contribution = await self.get_positions_contribution(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 4c. Broker P&L history (additive per-broker overlay for GrowthChart P&L mode) ──
        broker_pnl_history: list[BrokerPnlHistory] | None = None
        if query.include_broker_pnl_history:
            included.append("broker_pnl_history")
            broker_pnl_history = await self.get_broker_pnl_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 4d. Synthetic total-P&L candle series (GrowthChart P&L candles submode, G1b) ──
        pnl_candles: PnlCandleSeries | None = None
        if query.include_pnl_candles:
            included.append("pnl_candles")
            pnl_candles = await self.get_pnl_candles(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 4e. Signed personal income history (GrowthChart P&L income submode, G1c) ──
        income_history: IncomeHistorySeries | None = None
        if query.include_income_history:
            included.append("income_history")
            income_history = await self.get_income_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_native_cash=engine_result.native_cash,
            )

        # ── 4f. Signed FEE+TAX cost history (batch 2 — Income submode's costs dimension) ──
        cost_history: CostHistorySeries | None = None
        if query.include_cost_history:
            included.append("cost_history")
            cost_history = await self.get_cost_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_native_cash=engine_result.native_cash,
            )

        # ── 4g. DEPOSIT history (batch 2 — Income submode's deposit-size dimension) ──
        deposit_history: DepositHistorySeries | None = None
        if query.include_deposit_history:
            included.append("deposit_history")
            deposit_history = await self.get_deposit_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_native_cash=engine_result.native_cash,
            )

        # ── 4h. New-vs-reinvested BUY funding split (batch 2 — Income submode's
        # acquisition-size dimension). Requires the shared engine run to have been
        # computed with include_acquisition_funding=True (see above), mirroring
        # pnl_candles's own shared-engine-result requirement.
        acquisition_funding: AcquisitionFundingSeries | None = None
        if query.include_acquisition_funding:
            included.append("acquisition_funding")
            acquisition_funding = await self.get_acquisition_funding_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=effective_date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 5. Data quality from engine (already computed if summary was built) ──
        if summary:
            data_quality = summary.data_quality
        else:
            configured_fx_pairs, real_provider_fx_pairs = await self._get_configured_fx_pair_sets()
            held_quote_facts = await self._held_asset_quote_facts(engine_result)
            data_quality = views.build_data_quality_report(
                missing_fx_pairs_dto=_engine_missing_fx_pairs(engine_result, date_from, effective_date_to) or None,
                missing_cost_basis_assets=await self._missing_cost_basis_assets(engine_result) or None,
                invalid_split_assets=await self._invalid_split_assets(engine_result) or None,
                non_iso_currency_assets=self._non_iso_currency_assets(held_quote_facts) or None,
                report_currency=base_currency,
                mwrr_available=False,
                share_mismatches=engine_result.share_mismatches,
                configured_fx_pairs=configured_fx_pairs,
                real_provider_fx_pairs=real_provider_fx_pairs,
                period_from=date_from,
                period_to=effective_date_to,
            )

        # ── 6. Metadata ──
        computed_from = engine_result.daily_states[0].date if engine_result.daily_states else None
        computed_to = engine_result.daily_states[-1].date if engine_result.daily_states else None

        metadata = PortfolioReportMetadata(
            broker_ids=query.broker_ids,
            target_currency=base_currency,
            requested_date_from=date_from,
            requested_date_to=date_to,
            computed_date_from=computed_from,
            computed_date_to=computed_to,
            generated_at=today,
            included_features=included,
        )

        # The window of the step series (D-P4): the days of the period that have a state
        step_series_included = query.include_history or query.include_allocation_history or query.include_broker_pnl_history or query.include_pnl_candles
        window = views.window_range(date_from, effective_date_to) if step_series_included and engine_result.daily_states else None

        report = PortfolioReportResponse(
            metadata=metadata,
            range=DateSpan(start=window[0], end=window[1]) if window is not None else None,
            summary=summary,
            history=history,
            mwrr_line=mwrr_line,
            allocation_history=alloc_history,
            data_quality=data_quality,
            positions_contribution=positions_contribution,
            broker_pnl_history=broker_pnl_history,
            pnl_candles=pnl_candles,
            income_history=income_history,
            cost_history=cost_history,
            deposit_history=deposit_history,
            acquisition_funding=acquisition_funding,
        )

        # Store in Layer 2 cache
        if l2_key is not None:
            _portfolio_l2_cache.set(l2_key, report)
            _logger.debug("Portfolio L2 cache stored", user_id=user_id)

        return report
