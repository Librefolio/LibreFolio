"""
Portfolio Service for LibreFolio.

Contains:
- compute_wac_iterative(): Inventory-aware iterative WAC (PMC) — standalone async function
- PortfolioService: Orchestrator for portfolio-level aggregation, history, and FIFO lots

PortfolioService uses:
- WAC utils for cost basis calculation
- ROI utils for TWRR/MWRR/Simple ROI
- FIFO utils for lot matching
- FX service for currency conversion
- Transaction, Broker, Asset, PriceHistory DB models
"""

from __future__ import annotations

import asyncio
import bisect
from collections import defaultdict
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Any, NamedTuple, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    Broker,
    BrokerUserAccess,
    PriceHistory,
    Transaction,
    TransactionType,
)
from backend.app.schemas.common import Currency, FxBackwardFillInfo
from backend.app.schemas.portfolio import (
    AllocationHistoryDimensions,
    AllocationHistoryPoint,
    AllocationItem,
    AssetHistoryPoint,
    BrokerBreakdown,
    ClosedLotSchema,
    DataQualityIssue,
    FIFOLotsResponse,
    IssueCode,
    IssueDomain,
    IssueSeverity,
    MissingPriceAsset,
    OpenLotSchema,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioReportMetadata,
    PortfolioReportQuery,
    PortfolioReportResponse,
    PortfolioSummary,
)
from backend.app.schemas.wac import WACMissingPairInfo, WACPreviewResultItem, WACQualifyingTX
from backend.app.services.fx import convert_bulk
from backend.app.services.settings_service import get_global_setting
from backend.app.utils.financial.fifo_utils import FIFOTransactionInput, calculate_fifo_lots
from backend.app.utils.financial.roi_utils import (
    CashFlowInput,
    NAVSnapshot,
    annualized_to_cumulative,
    calculate_mwrr,
    calculate_mwrr_series,
    calculate_simple_roi,
    calculate_simple_roi_series,
    calculate_twrr,
    calculate_twrr_series,
)
from backend.app.utils.financial.valuation_utils import compute_holding_value
from backend.app.utils.financial.wac_utils import WACInputTX, compute_wac_from_txlist, determine_target_currency

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
) -> WACPreviewResultItem:
    """Compute inventory-aware WAC (PMC) for an asset at a broker up to a date.

    Preparation layer: queries DB, handles FX conversion,
    then delegates to compute_wac_from_txlist() for pure math.
    """
    excluded = set(excluded_tx_ids or [])

    # 1. Query ALL transactions for this (broker, asset) with date <= as_of_date and qty != 0
    stmt = select(Transaction).where(
        Transaction.broker_id == broker_id,
        Transaction.asset_id == asset_id,
        Transaction.date <= as_of_date,
        Transaction.quantity.is_not(None),
        Transaction.quantity != 0,
    )
    db_rows = (await session.execute(stmt)).scalars().all()

    # 2. Build unified row tuples from DB rows (minus excluded)
    # Tuple: (tx_id, type_str, date, quantity, amount, currency, cbo_amount, cbo_ccy, is_pending, cbm)
    unified: list[tuple] = []

    for row in db_rows:
        if row.id in excluded:
            continue
        unified.append(
            (
                row.id,
                row.type.value if hasattr(row.type, "value") else str(row.type),
                row.date,
                row.quantity,
                row.amount,
                row.currency,
                row.cost_basis_override,
                row.cost_basis_currency,
                False,
                None,
            )
        )

    if not unified:
        return WACPreviewResultItem(
            wac=Currency(code=asset_currency, amount=Decimal("0")),
            wac_qualifying_txs=[],
            wac_missing_pairs=[],
        )

    # 3. Build WACInputTX list and determine target_currency
    #    First pass: determine currencies for target_currency selection
    pre_txs: list[WACInputTX] = []
    for tid, ttype, dt, qty, _amount, ccy, _cbo_amt, cbo_ccy, is_pend, _cbm in unified:
        if qty > 0:
            orig_ccy = ccy if ttype == "BUY" else (cbo_ccy or asset_currency)
        else:
            orig_ccy = ccy or asset_currency
        pre_txs.append(
            WACInputTX(
                tx_id=tid,
                type=ttype,
                date=dt,
                quantity=qty,
                unit_cost_converted=None,
                original_currency=orig_ccy,
                is_pending=is_pend,
            )
        )

    target_currency = target_currency_override or determine_target_currency(pre_txs, asset_currency)

    # 4. FX conversion for acquisitions with different currency
    fx_requests: list[tuple[int, Currency, str, date_type]] = []  # (idx, cost_ccy, target, date)

    for i, (_tid, ttype, dt, qty, amount, ccy, cbo_amt, cbo_ccy, _is_pend, _cbm) in enumerate(unified):
        if qty <= 0:
            continue
        if ttype == "BUY":
            tx_ccy = ccy or asset_currency
            if tx_ccy != target_currency and amount:
                cost = abs(amount)
                fx_requests.append((i, Currency(code=tx_ccy, amount=cost), target_currency, dt))
        elif cbo_amt is not None:
            tx_ccy = cbo_ccy or asset_currency
            if tx_ccy != target_currency:
                cost = qty * cbo_amt
                fx_requests.append((i, Currency(code=tx_ccy, amount=cost), target_currency, dt))

    fx_converted: dict[int, Decimal] = {}
    fx_staleness: dict[int, FxBackwardFillInfo] = {}
    fx_rates: dict[int, Decimal] = {}  # unified_idx → derived FX rate
    missing_pair_dates: dict[str, list[date_type]] = {}

    if fx_requests:
        bulk_input = [(amt, to_ccy, dt) for _, amt, to_ccy, dt in fx_requests]
        fx_results, _fx_errors = await convert_bulk(session, bulk_input, raise_on_error=False)
        for j, (unified_idx, amt_ccy, _to_ccy, _dt) in enumerate(fx_requests):
            result = fx_results[j] if j < len(fx_results) else None
            if result is None:
                pair_key = f"{amt_ccy.code}/{_to_ccy}"
                missing_pair_dates.setdefault(pair_key, []).append(_dt)
            else:
                converted, rate_date, _bf = result
                fx_converted[unified_idx] = converted.amount
                # Derive FX rate from conversion (linear)
                if amt_ccy.amount and amt_ccy.amount != 0:
                    fx_rates[unified_idx] = converted.amount / amt_ccy.amount
                # Track staleness info for qualifying TX enrichment
                tx_date = unified[unified_idx][2]  # date is at index 2
                stale_days = (tx_date - rate_date).days if rate_date < tx_date else 0
                fx_staleness[unified_idx] = FxBackwardFillInfo(fx_rate_date=rate_date, fx_days_back=stale_days)

    if missing_pair_dates:
        missing_pairs_out = [WACMissingPairInfo(pair=k, dates=sorted(set(v))) for k, v in missing_pair_dates.items()]
        return WACPreviewResultItem(wac=None, wac_qualifying_txs=[], wac_missing_pairs=missing_pairs_out)

    # 5. Build final WACInputTX list with converted costs
    input_txs: list[WACInputTX] = []
    # Track original unit costs (before FX) keyed by unified_idx
    original_unit_costs: dict[int, tuple[Decimal, str]] = {}  # idx → (unit_cost, currency)
    for i, (tid, ttype, dt, qty, amount, ccy, cbo_amt, cbo_ccy, is_pend, cbm) in enumerate(unified):
        unit_cost: Decimal | None = None
        orig_ccy = ccy or asset_currency

        if qty > 0:
            if ttype == "BUY":
                if i in fx_converted:
                    unit_cost = fx_converted[i] / qty
                    # Original unit cost before FX
                    original_unit_costs[i] = (abs(amount) / qty if amount else Decimal("0"), ccy or asset_currency)
                elif amount:
                    unit_cost = abs(amount) / qty
                else:
                    unit_cost = Decimal("0")
                orig_ccy = ccy or asset_currency
            elif cbo_amt is not None:
                if i in fx_converted:
                    unit_cost = fx_converted[i] / qty
                    # Original unit cost before FX
                    original_unit_costs[i] = (cbo_amt, cbo_ccy or asset_currency)
                else:
                    unit_cost = cbo_amt
                orig_ccy = cbo_ccy or asset_currency
            else:
                unit_cost = None  # will be treated as zero cost (or add_at_wac if cbm == "auto")
                orig_ccy = asset_currency
        # For reductions, unit_cost stays None — compute_wac_from_txlist uses current WAC

        input_txs.append(
            WACInputTX(
                tx_id=tid,
                type=ttype,
                date=dt,
                quantity=qty,
                unit_cost_converted=unit_cost,
                original_currency=orig_ccy,
                is_pending=is_pend,
                cost_basis_mode=cbm,
            )
        )

    # 6. Delegate to pure math function
    calc_result = compute_wac_from_txlist(input_txs, target_currency)

    # 7. Convert result to schema
    # Build tx_id → fx_staleness lookup for qualifying TX enrichment
    tx_fx_info: dict[int, FxBackwardFillInfo] = {}
    tx_original_costs: dict[int, tuple[Decimal, str]] = {}  # tx_id → (original_unit_cost, original_ccy)
    tx_fx_rates: dict[int, Decimal] = {}  # tx_id → fx_rate
    for idx, info in fx_staleness.items():
        tx_id = unified[idx][0]
        tx_fx_info[tx_id] = info
    for idx, (orig_cost, orig_ccy) in original_unit_costs.items():
        tx_id = unified[idx][0]
        tx_original_costs[tx_id] = (orig_cost, orig_ccy)
    for idx, rate in fx_rates.items():
        tx_id = unified[idx][0]
        tx_fx_rates[tx_id] = rate

    qualifying_txs = [
        WACQualifyingTX(
            tx_id=q.tx_id,
            type=q.type,
            date=q.date,
            quantity=q.quantity,
            unit_cost=q.unit_cost,
            currency=q.currency,
            effect=q.effect,
            running_wac=q.running_wac,
            fx_info=tx_fx_info.get(q.tx_id) if q.tx_id is not None else None,
            original_unit_cost=tx_original_costs[q.tx_id][0] if q.tx_id is not None and q.tx_id in tx_original_costs else None,
            original_currency=tx_original_costs[q.tx_id][1] if q.tx_id is not None and q.tx_id in tx_original_costs else None,
            fx_rate_used=tx_fx_rates.get(q.tx_id) if q.tx_id is not None else None,
        )
        for q in calc_result.qualifying
    ]

    return WACPreviewResultItem(
        wac=Currency(code=target_currency, amount=calc_result.wac_amount) if calc_result.pool_qty >= 0 else None,
        wac_qualifying_txs=qualifying_txs,
        wac_missing_pairs=[],
    )


# =============================================================================
# HISTORY SERIES — Pure function (no I/O, fully testable)
# =============================================================================


class _HistoryTxRow(NamedTuple):
    """Pre-processed transaction row ready for history series computation.

    The async layer (get_history) is responsible for:
    - Querying the DB
    - Converting amounts to base currency
    - Applying share_percentage per broker

    This NamedTuple represents a single already-converted row.
    """

    date: date_type
    type: str
    amount: Decimal  # signed amount, already converted to base currency
    share: Decimal  # broker ownership fraction (0.0-1.0), applied during aggregation


class _HistoryQtyRow(NamedTuple):
    """Quantity delta for a single BUY or SELL transaction.

    Parallel to _HistoryTxRow but carries per-asset quantity info so that
    get_history() can compute mark-to-market holdings value.
    qty_delta is share-adjusted and signed: positive for BUY, negative for SELL.
    """

    date: date_type
    asset_id: int
    qty_delta: Decimal  # share-adjusted signed quantity change


@dataclass
class _HistoryCalcPoint:
    """Mutable internal history point for backend calculations before API serialization."""

    date: date_type
    cash_value: Decimal
    market_value: Decimal
    nav_value: Decimal
    twrr: Decimal | None = None
    mwrr: Decimal | None = None
    roi: Decimal | None = None


# ---------------------------------------------------------------------------
# Mark-to-market helpers (pure, no I/O)
# ---------------------------------------------------------------------------


def _price_on_date(
    sorted_prices: list[tuple[date_type, Decimal, str]],
    query_date: date_type,
) -> tuple[Decimal, str] | None:
    """Return the latest (close, currency) with date <= query_date using backward fill.

    sorted_prices must be sorted ascending by date[0].
    Returns None if no price exists at or before query_date.
    """
    if not sorted_prices:
        return None
    # bisect_right gives insertion point after all dates == query_date
    dates = [p[0] for p in sorted_prices]
    idx = bisect.bisect_right(dates, query_date) - 1
    if idx < 0:
        return None
    _, close, ccy = sorted_prices[idx]
    return close, ccy


def _build_history_series(
    transactions: list[_HistoryTxRow],
    date_to: date_type | None = None,
) -> list[_HistoryCalcPoint]:
    """Build a dense daily cash/NAV baseline series from pre-processed transaction rows.

    Pure function — no I/O, no DB, no async. Deterministic given the same input.

    Rules:
    - Cash follows the signed transaction ledger exactly.
    - One output point per calendar day from first transaction to `date_to` (or the
      last transaction date if `date_to` is omitted).
    - `market_value`/`nav_value` are temporary placeholders at this stage and
      are patched later by the mark-to-market layer in `get_history()`.

    Args:
        transactions: List of _HistoryTxRow, may be in any order (will be sorted).
        date_to: Optional inclusive end date for dense expansion.

    Returns:
        List of _HistoryCalcPoint, one per calendar day, sorted ascending.
    """
    if not transactions:
        return []

    cash_delta_by_date: dict[date_type, Decimal] = defaultdict(Decimal)

    for row in sorted(transactions, key=lambda r: r.date):
        cash_delta_by_date[row.date] += row.amount * row.share

    sorted_rows = sorted(transactions, key=lambda r: r.date)
    start_date = sorted_rows[0].date
    final_date = date_to or sorted_rows[-1].date
    if final_date < start_date:
        return []

    history: list[_HistoryCalcPoint] = []
    cumulative_cash = Decimal("0")
    current_date = start_date
    while current_date <= final_date:
        cumulative_cash += cash_delta_by_date.get(current_date, Decimal("0"))
        history.append(
            _HistoryCalcPoint(
                date=current_date,
                cash_value=cumulative_cash,
                market_value=Decimal("0"),
                nav_value=cumulative_cash,
            )
        )
        current_date += timedelta(days=1)

    return history


# =============================================================================
# PORTFOLIO SERVICE — Orchestrator
# =============================================================================

_DEPOSIT_TYPES = {TransactionType.DEPOSIT}
_WITHDRAWAL_TYPES = {TransactionType.WITHDRAWAL}
_CASH_FLOW_TYPES = _DEPOSIT_TYPES | _WITHDRAWAL_TYPES
_HOLDING_TYPES = {TransactionType.BUY, TransactionType.SELL}


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

    async def _get_base_currency(self) -> str:
        """Return the global base currency (default: EUR)."""
        setting = await get_global_setting("base_currency", self.db)
        return setting.value if setting else "EUR"

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

    async def _get_latest_price(self, asset_id: int) -> Optional[tuple[Decimal, str, date_type]]:
        """Return (close_price, currency, date) for latest price history entry."""
        stmt = select(PriceHistory.close, PriceHistory.currency, PriceHistory.date).where(PriceHistory.asset_id == asset_id, PriceHistory.close.is_not(None)).order_by(PriceHistory.date.desc()).limit(1)
        row = (await self.db.execute(stmt)).one_or_none()
        if row:
            return row.close, row.currency, row.date
        return None

    async def _bulk_load_asset_prices(
        self,
        asset_ids: set[int],
        date_from: date_type,
        date_to: date_type,
    ) -> dict[int, list[tuple[date_type, Decimal, str]]]:
        """Bulk-load PriceHistory for a set of assets over a date range.

        Returns {asset_id: [(date, close, currency)]} with each list sorted ascending.
        A single SQL query for all assets — avoids N separate round-trips.
        """
        if not asset_ids:
            return {}
        stmt = (
            select(PriceHistory.asset_id, PriceHistory.date, PriceHistory.close, PriceHistory.currency)
            .where(
                PriceHistory.asset_id.in_(asset_ids),
                PriceHistory.close.is_not(None),
                PriceHistory.date >= date_from,
                PriceHistory.date <= date_to,
            )
            .order_by(PriceHistory.asset_id, PriceHistory.date)
        )
        rows = (await self.db.execute(stmt)).all()
        result: dict[int, list[tuple[date_type, Decimal, str]]] = defaultdict(list)
        for r in rows:
            result[r.asset_id].append((r.date, r.close, r.currency))
        return dict(result)

    async def _get_asset(self, asset_id: int) -> Asset | None:
        return await self.db.get(Asset, asset_id)

    async def _get_quote_base_map(self, asset_ids: set[int]) -> dict[int, int | None]:
        if not asset_ids:
            return {}
        stmt = select(Asset.id, Asset.quote_base_quantity).where(Asset.id.in_(asset_ids))
        rows = (await self.db.execute(stmt)).all()
        return dict(rows)

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

    @staticmethod
    def _merge_missing_pairs(items: list[WACMissingPairInfo]) -> list[WACMissingPairInfo]:
        merged: dict[str, set[date_type]] = defaultdict(set)
        for item in items:
            merged[item.pair].update(item.dates)
        return [WACMissingPairInfo(pair=pair, dates=sorted(dates)) for pair, dates in sorted(merged.items())]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_summary(
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
        allocation, performance) while keeping the per-asset holdings loop for
        individual holding details and broker breakdown.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        """
        from backend.app.services.portfolio_engine import (  # noqa: PLC0415
            DerivedViewsBuilder,
            PortfolioCalculationEngine,
        )

        today = date_type.today()
        base_currency = target_currency_override or await self._get_base_currency()

        # ── 1. Run engine for aggregate values + performance ──
        if _precomputed_engine_result is not None:
            engine_result = _precomputed_engine_result
        else:
            engine = PortfolioCalculationEngine(self.db)
            engine_result = await engine.calculate(
                user_id=user_id,
                broker_ids=broker_ids,
                date_from=None,
                date_to=None,
                target_currency=base_currency,
            )

        views = DerivedViewsBuilder(engine_result.daily_states, base_currency)

        # ── 2. Extract aggregate values from last daily state ──
        last_state = engine_result.daily_states[-1] if engine_result.daily_states else None
        engine_nav = last_state.nav_value if last_state else Decimal("0")
        engine_cash = last_state.cash_value if last_state else Decimal("0")
        engine_market_value = last_state.market_value if last_state else Decimal("0")

        # ── 3. Per-asset holdings loop (kept for individual holding details) ──
        accesses = await self._get_user_broker_access(user_id, broker_ids)

        total_invested = Decimal("0")
        _total_deposited = Decimal("0")
        _total_withdrawn = Decimal("0")
        total_cost_basis = Decimal("0")
        all_cash_balances: dict[str, Decimal] = defaultdict(Decimal)
        all_holdings: list[PortfolioHolding] = []
        by_broker_list: list[BrokerBreakdown] = []
        all_missing_pairs: list[WACMissingPairInfo] = []
        missing_price_assets: list[MissingPriceAsset] = []
        _income_accum = Decimal("0")
        _fees_taxes_accum = Decimal("0")
        _fees_accum = Decimal("0")
        _taxes_accum = Decimal("0")
        _realized_accum = Decimal("0")
        _INCOME_TYPES = {TransactionType.DIVIDEND, TransactionType.INTEREST}
        _FEE_TAX_TYPES = {TransactionType.FEE, TransactionType.TAX}

        for access in accesses:
            broker_id = access.broker_id
            share = access.share_percentage or Decimal("1")
            broker = await self._get_broker(broker_id)
            broker_name = broker.name if broker else f"Broker {broker_id}"

            broker_txns = await self._get_transactions(broker_id)
            broker_cash: dict[str, Decimal] = defaultdict(Decimal)
            for tx in broker_txns:
                if tx.amount is None or tx.currency is None:
                    continue
                broker_cash[tx.currency] += tx.amount * share

                if tx.currency == base_currency:
                    amount_base_signed: Decimal | None = tx.amount
                else:
                    cf_results, _ = await convert_bulk(
                        self.db,
                        [(Currency(code=tx.currency, amount=tx.amount), base_currency, tx.date)],
                        raise_on_error=False,
                    )
                    amount_base_signed = cf_results[0][0].amount if cf_results and cf_results[0] is not None else None

                if amount_base_signed is None:
                    pair_key = f"{tx.currency}/{base_currency}"
                    all_missing_pairs.append(WACMissingPairInfo(pair=pair_key, dates=[tx.date]))
                    continue

                # Accumulate income, fees, and net deposited capital for period breakdown
                after_start = (date_from is None or tx.date > date_from)
                before_end = (date_to is None or tx.date <= date_to)
                in_period = after_start and before_end

                if tx.type in _CASH_FLOW_TYPES:
                    total_invested += amount_base_signed * share
                    if in_period:
                        if tx.type in _DEPOSIT_TYPES:
                            _total_deposited += abs(amount_base_signed) * share
                        else:
                            _total_withdrawn += abs(amount_base_signed) * share

                if in_period and tx.type in _INCOME_TYPES:
                    _income_accum += abs(amount_base_signed) * share
                if in_period and tx.type in _FEE_TAX_TYPES:
                    _fees_taxes_accum += abs(amount_base_signed) * share
                    if tx.type == TransactionType.FEE:
                        _fees_accum += abs(amount_base_signed) * share
                    else:
                        _taxes_accum += abs(amount_base_signed) * share

            # Holding transactions — group by asset
            txns_by_asset: dict[int, list[Transaction]] = defaultdict(list)
            for tx in broker_txns:
                if tx.type not in _HOLDING_TYPES:
                    continue
                if tx.asset_id is not None:
                    txns_by_asset[tx.asset_id].append(tx)

            broker_market_value = Decimal("0")

            for asset_id, asset_txns in txns_by_asset.items():
                asset = await self._get_asset(asset_id)
                if not asset:
                    continue

                # Compute realized G/L for SELLs in the period (WAC at sell date)
                for tx in asset_txns:
                    if tx.type != TransactionType.SELL:
                        continue
                    after_start = (date_from is None or tx.date > date_from)
                    before_end = (date_to is None or tx.date <= date_to)
                    if not (after_start and before_end):
                        continue
                    sell_qty = abs(tx.quantity or Decimal("0"))
                    if sell_qty == 0 or tx.id is None:
                        continue
                    # Get WAC just before the sell (exclude this SELL from computation)
                    sell_wac_result = await compute_wac_iterative(
                        session=self.db, broker_id=broker_id, asset_id=asset_id,
                        as_of_date=tx.date, asset_currency=asset.currency or base_currency,
                        excluded_tx_ids=[tx.id],
                    )
                    if sell_wac_result.wac is None:
                        continue
                    wac_at_sell = sell_wac_result.wac.amount
                    wac_at_sell_ccy = sell_wac_result.wac.code
                    # Convert WAC to base currency
                    if wac_at_sell_ccy != base_currency:
                        wac_at_sell_base, _ = await self._convert_to_base(wac_at_sell, wac_at_sell_ccy, base_currency, tx.date)
                        if wac_at_sell_base is None:
                            continue
                    else:
                        wac_at_sell_base = wac_at_sell
                    # Proceeds in base currency
                    sell_amount = abs(tx.amount or Decimal("0"))
                    if tx.currency and tx.currency != base_currency:
                        sell_converted, _ = await self._convert_to_base(sell_amount, tx.currency, base_currency, tx.date)
                        sell_proceeds = sell_converted if sell_converted else sell_amount
                    else:
                        sell_proceeds = sell_amount
                    cost_sold = sell_qty * wac_at_sell_base
                    _realized_accum += (sell_proceeds - cost_sold) * share

                wac_result = await compute_wac_iterative(
                    session=self.db, broker_id=broker_id, asset_id=asset_id,
                    as_of_date=today, asset_currency=asset.currency or base_currency,
                )
                if wac_result.wac is None:
                    if wac_result.wac_missing_pairs:
                        all_missing_pairs.extend(wac_result.wac_missing_pairs)
                    continue

                wac_per_unit = wac_result.wac.amount
                wac_currency = wac_result.wac.code
                net_qty = sum((tx.quantity or Decimal("0")) for tx in asset_txns if tx.type in (TransactionType.BUY, TransactionType.SELL))
                if net_qty <= 0:
                    continue

                price_data = await self._get_latest_price(asset_id)
                current_price: Decimal | None = None
                current_value: Decimal | None = None
                gain_loss: Decimal | None = None
                gain_loss_pct: Decimal | None = None

                if price_data:
                    raw_price, price_ccy, price_date = price_data
                    if price_ccy != base_currency:
                        converted, mp = await self._convert_to_base(raw_price, price_ccy, base_currency, price_date)
                        if converted is not None:
                            current_price = converted
                        all_missing_pairs.extend(mp)
                    else:
                        current_price = raw_price

                if current_price is not None:
                    current_value = compute_holding_value(net_qty, current_price, asset.quote_base_quantity) * share
                    broker_market_value += current_value

                has_missing_price = price_data is None and current_price is None

                if wac_currency != base_currency:
                    wac_base, mp = await self._convert_to_base(wac_per_unit, wac_currency, base_currency, today)
                    all_missing_pairs.extend(mp)
                else:
                    wac_base = wac_per_unit

                cost_basis = (wac_base or wac_per_unit) * net_qty * share
                total_cost_basis += cost_basis

                if has_missing_price:
                    first_date = min((tx.date for tx in asset_txns), default=None)
                    missing_price_assets.append(MissingPriceAsset(
                        asset_id=asset_id, symbol=asset.identifier_ticker,
                        name=asset.display_name, broker_id=broker_id,
                        broker_name=broker_name, first_position_date=first_date,
                        quantity=net_qty,
                        open_cost_basis=cost_basis if wac_base is not None else None,
                        currency=base_currency,
                    ))

                if current_value is not None and wac_base is not None:
                    gain_loss = current_value - cost_basis
                    gain_loss_pct = (gain_loss / cost_basis) if cost_basis != 0 else Decimal("0")

                all_holdings.append(PortfolioHolding(
                    asset_id=asset_id, asset_name=asset.display_name,
                    asset_ticker=asset.identifier_ticker,
                    asset_type=asset.asset_type.value if asset.asset_type else "Unknown",
                    quantity=net_qty, wac_per_unit=wac_base if wac_base else wac_per_unit,
                    current_price=current_price, current_value=current_value,
                    gain_loss=gain_loss, gain_loss_percent=gain_loss_pct,
                    allocation_percent=None,
                ))

            # Broker-level cash
            broker_cash_base = Decimal("0")
            for ccy, amt in broker_cash.items():
                if ccy == base_currency:
                    broker_cash_base += amt
                    all_cash_balances[ccy] += amt
                else:
                    converted, mp = await self._convert_to_base(amt, ccy, base_currency, today)
                    all_missing_pairs.extend(mp)
                    if converted is not None:
                        broker_cash_base += converted
                        all_cash_balances[ccy] += amt

            broker_nav = broker_market_value + broker_cash_base

            if include_breakdown:
                broker_gain = broker_nav - total_invested
                broker_gl_pct = (broker_gain / total_invested) if total_invested else Decimal("0")
                by_broker_list.append(BrokerBreakdown(
                    broker_id=broker_id, broker_name=broker_name,
                    net_worth=Currency(code=base_currency, amount=broker_nav),
                    gain_loss=Currency(code=base_currency, amount=broker_gain),
                    gain_loss_percent=broker_gl_pct,
                    cash_total=Currency(code=base_currency, amount=broker_cash_base),
                ))

        # ── 4. Allocation from engine (scope-aware, includes in-transit) ──
        alloc_type, alloc_sector, alloc_geo = views.build_allocation_current()

        def _alloc_from_engine(items: list[dict]) -> list[AllocationItem]:
            return [AllocationItem(**item) for item in items]

        total_market = sum(h.current_value for h in all_holdings if h.current_value) or Decimal("1")
        for h in all_holdings:
            if h.current_value and total_market:
                object.__setattr__(h, "allocation_percent", (h.current_value / total_market * 100).quantize(Decimal("0.01")))

        # ── 5. Performance from engine (correct daily NAV) ──
        nav_snapshots, cash_flows_perf = views.build_performance_inputs()

        # Period re-basing: when date_from is set, compute metrics for that period only
        if date_from and nav_snapshots:
            pre_period = [s for s in nav_snapshots if s.date <= date_from]
            if pre_period:
                period_start_nav_perf = pre_period[-1].nav
                period_start_date_perf = pre_period[-1].date
            else:
                period_start_nav_perf = Decimal("0")
                period_start_date_perf = nav_snapshots[0].date

            synthetic_cf = CashFlowInput(date=period_start_date_perf, amount=-period_start_nav_perf)
            if period_start_nav_perf > 0:
                period_cfs = [synthetic_cf] + [cf for cf in cash_flows_perf if cf.date > period_start_date_perf]
            else:
                period_cfs = [synthetic_cf] + [cf for cf in cash_flows_perf if cf.date >= period_start_date_perf]
            period_navs = [s for s in nav_snapshots if s.date >= period_start_date_perf]
        else:
            period_cfs = cash_flows_perf
            period_navs = nav_snapshots
            period_start_nav_perf = Decimal("0") if nav_snapshots else Decimal("0")
            period_start_date_perf = nav_snapshots[0].date if nav_snapshots else today

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
            if period_net_invested > 0:
                # Use first actual NAV when period_start is 0 (portfolio starts from nothing)
                # This matches calculate_mwrr_series which uses sorted_navs[0].nav
                initial_nav_for_mwrr = period_start_nav_perf if period_start_nav_perf > 0 else (period_navs[0].nav if period_navs else Decimal("0"))
                mwrr_point = await asyncio.to_thread(
                    calculate_mwrr, period_cfs, initial_nav_for_mwrr,
                    engine_nav, period_start_date_perf, date_to or today,
                )
                mwrr_result = mwrr_point.mwrr

        # ── MWRR cumulative derivation ──
        mwrr_period_days: int | None = None
        mwrr_cumulative: Decimal | None = None
        if period_navs:
            mwrr_period_days = ((date_to or today) - period_start_date_perf).days
            mwrr_cumulative = annualized_to_cumulative(mwrr_result, mwrr_period_days) if mwrr_result is not None else None

        total_gl = engine_nav - total_invested
        total_gl_pct = (total_gl / total_invested) if total_invested > 0 else Decimal("0")
        cash_balances_list = [Currency(code=ccy, amount=amt) for ccy, amt in all_cash_balances.items()]

        # ── Period P&L computation ──
        period_nav_start_val: Decimal | None = None
        period_net_flows_val: Decimal | None = None
        period_pnl_val: Decimal | None = None

        if nav_snapshots and len(nav_snapshots) >= 2:
            # Find nav at period start
            if date_from:
                pre_period = [s for s in nav_snapshots if s.date <= date_from]
                # If date_from is before any portfolio data, NAV was 0
                period_nav_start_val = pre_period[-1].nav if pre_period else Decimal("0")
                # Sum external CFs within the period (respecting both boundaries)
                period_net_flows_val = sum(
                    (-cf.amount) for cf in cash_flows_perf
                    if cf.date > date_from and (date_to is None or cf.date <= date_to)
                )
            else:
                # Full history: NAV at t=0 is effectively 0 (portfolio starts empty)
                period_nav_start_val = Decimal("0")
                # All CFs up to date_to
                period_net_flows_val = sum(
                    (-cf.amount) for cf in cash_flows_perf
                    if (date_to is None or cf.date <= date_to)
                )

            period_pnl_val = engine_nav - period_nav_start_val - (period_net_flows_val or Decimal("0"))

        # ── Period P&L breakdown: unrealized delta, income, fees ──
        period_ugl_start: Decimal | None = None
        period_ugl_end: Decimal | None = None
        period_ugl_delta: Decimal | None = None
        period_book_value_start_val: Decimal | None = None
        period_market_value_start_val: Decimal | None = None
        period_realized_val: Decimal | None = None
        period_income_val: Decimal | None = None
        period_fees_taxes_val: Decimal | None = None
        period_other_result_val: Decimal | None = None

        if engine_result.daily_states and period_pnl_val is not None:
            # Unrealized G/L from daily states (market_value - open_cost_basis)
            last_ds = engine_result.daily_states[-1]
            period_ugl_end = last_ds.market_value - last_ds.open_cost_basis

            if date_from:
                # Find daily state at or before date_from
                pre_states = [s for s in engine_result.daily_states if s.date <= date_from]
                if pre_states:
                    start_ds = pre_states[-1]
                    period_ugl_start = start_ds.market_value - start_ds.open_cost_basis
                    period_book_value_start_val = start_ds.book_value
                    period_market_value_start_val = start_ds.market_value
                else:
                    period_ugl_start = Decimal("0")
                    period_book_value_start_val = Decimal("0")
                    period_market_value_start_val = Decimal("0")
            else:
                period_ugl_start = Decimal("0")
                period_book_value_start_val = Decimal("0")
                period_market_value_start_val = Decimal("0")

            period_ugl_delta = period_ugl_end - period_ugl_start

            # Realized, income, fees from accumulated values
            period_realized_val = _realized_accum
            period_income_val = _income_accum if _income_accum else Decimal("0")
            period_fees_taxes_val = _fees_taxes_accum if _fees_taxes_accum else Decimal("0")

            # Other result: residual that closes the identity
            # pnl = ugl_delta + realized + income - fees_taxes + other_result
            period_other_result_val = (
                period_pnl_val - period_ugl_delta - period_realized_val - period_income_val + period_fees_taxes_val
            )

        # ── 6. Data quality report ──
        # Collect transaction-implied assets (valued at WAC cost, no market price yet)
        implied_asset_ids = views.aggregate_transaction_implied_ids()
        transaction_implied_assets: list[MissingPriceAsset] = []
        for h in all_holdings:
            if h.asset_id in implied_asset_ids and h.current_value is None:
                transaction_implied_assets.append(MissingPriceAsset(
                    asset_id=h.asset_id,
                    symbol=h.asset_ticker,
                    name=h.asset_name,
                    broker_id=0,  # approximate — not tracked per-broker here
                    broker_name="",
                    quantity=h.quantity,
                    currency=base_currency,
                ))

        # For manual assets (no provider, valued at cost): suppress MISSING_PRICE
        # They're already represented by TRANSACTION_IMPLIED which is expected behavior
        from backend.app.db.models import AssetProviderAssignment  # noqa: PLC0415
        provider_result = await self.db.execute(
            select(AssetProviderAssignment.asset_id)
        )
        assets_with_provider = {row[0] for row in provider_result.fetchall()}
        # Remove from missing_price_assets if the asset is manual (no provider) AND implied (valued at cost)
        missing_price_assets = [
            a for a in missing_price_assets
            if a.asset_id in assets_with_provider or a.asset_id not in implied_asset_ids
        ]
        # For truly manual assets (implied, no provider): suppress TRANSACTION_IMPLIED too
        # since cost valuation is their intended/permanent behavior
        manual_implied_ids = implied_asset_ids - assets_with_provider
        transaction_implied_assets = [
            a for a in transaction_implied_assets if a.asset_id not in manual_implied_ids
        ]

        data_quality = views.build_data_quality_report(
            missing_price_assets_dto=missing_price_assets,
            missing_fx_pairs_dto=self._merge_missing_pairs(all_missing_pairs),
            transaction_implied_assets_dto=transaction_implied_assets if transaction_implied_assets else None,
            mwrr_available=mwrr_result is not None,
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
            simple_roi_percent=simple_roi,
            allocation_by_type=_alloc_from_engine(alloc_type),
            allocation_by_sector=_alloc_from_engine(alloc_sector),
            allocation_by_geography=_alloc_from_engine(alloc_geo),
            holdings=all_holdings,
            by_broker=by_broker_list if include_breakdown else None,
            missing_fx_pairs=self._merge_missing_pairs(all_missing_pairs),
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
        _mwrr_use_warm_start: bool = True,
    ) -> list[PortfolioHistoryPoint]:
        """Return daily portfolio value series via PortfolioCalculationEngine.

        _precomputed_engine_result: if provided by get_report(), skip engine re-run.
        _mwrr_use_warm_start: if False, use cold-start for MWRR series (no warm-start).
        """
        from backend.app.services.portfolio_engine import (  # noqa: PLC0415
            DerivedViewsBuilder,
            PortfolioCalculationEngine,
        )

        base_currency = target_currency_override or await self._get_base_currency()
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

        # ── Build history dicts ──
        history_dicts = views.build_history()

        # ── Performance metrics ──
        nav_snapshots, cash_flows = views.build_performance_inputs()

        # Period re-basing for ROI metrics
        if date_from and nav_snapshots:
            pre_period = [s for s in nav_snapshots if s.date <= date_from]
            if pre_period:
                period_start_nav = pre_period[-1].nav
                period_start_date = pre_period[-1].date
            else:
                # date_from is before any portfolio data — NAV was 0
                period_start_nav = Decimal("0")
                period_start_date = nav_snapshots[0].date

            synthetic_cf = CashFlowInput(date=period_start_date, amount=-period_start_nav)
            # When period_start_nav > 0, CFs on start date are already embedded in starting NAV (exclude with >)
            # When period_start_nav == 0, CFs on start date must be included (use >=)
            if period_start_nav > 0:
                period_cash_flows = [synthetic_cf] + [cf for cf in cash_flows if cf.date > period_start_date]
            else:
                period_cash_flows = [synthetic_cf] + [cf for cf in cash_flows if cf.date >= period_start_date]
            period_nav_snapshots = [s for s in nav_snapshots if s.date >= period_start_date]
            # When period_start_nav > 0, ensure first snapshot matches so MWRR series is consistent
            if period_start_nav > 0 and period_nav_snapshots and period_nav_snapshots[0].nav != period_start_nav:
                period_nav_snapshots = [NAVSnapshot(date=period_start_date, nav=period_start_nav)] + period_nav_snapshots
        else:
            period_cash_flows = cash_flows
            period_nav_snapshots = nav_snapshots

        twrr_map: dict[date_type, Decimal] = {}
        roi_map: dict[date_type, Decimal] = {}
        mwrr_map: dict[date_type, Decimal | None] = {}

        if period_nav_snapshots and period_cash_flows:
            twrr_series = calculate_twrr_series(period_nav_snapshots, period_cash_flows)
            roi_series = calculate_simple_roi_series(period_nav_snapshots, period_cash_flows)
            mwrr_series = await asyncio.to_thread(
                calculate_mwrr_series, period_nav_snapshots, period_cash_flows,
                use_warm_start=_mwrr_use_warm_start,
            )
            twrr_map = {pt.date: pt.twrr for pt in twrr_series}
            roi_map = {pt.date: pt.roi for pt in roi_series}
            mwrr_map = {pt.date: pt.mwrr for pt in mwrr_series}

        # Period start date for cumulative MWRR calculation
        period_start = period_nav_snapshots[0].date if period_nav_snapshots else None

        # ── Slice to [date_from, date_to] and merge performance ──
        history_points: list[PortfolioHistoryPoint] = []
        for h in history_dicts:
            d = h["date"]
            if date_from and d < date_from:
                continue

            twrr = twrr_map.get(d)
            roi = roi_map.get(d)
            mwrr_ann = mwrr_map.get(d)

            # Compute cumulative MWRR from annualized
            days_from_start = (d - period_start).days if period_start else 0
            mwrr_cum = annualized_to_cumulative(mwrr_ann, days_from_start)

            history_points.append(
                PortfolioHistoryPoint(
                    date=d,
                    cash_value=h["cash_value"],
                    market_value=h["market_value"],
                    broker_nav_value=h.get("broker_nav_value"),
                    in_transit_cash_value=h.get("in_transit_cash_value"),
                    in_transit_asset_market_value=h.get("in_transit_asset_market_value"),
                    in_transit_market_value=h.get("in_transit_market_value"),
                    nav_value=h["nav_value"],
                    open_cost_basis=h.get("open_cost_basis"),
                    in_transit_asset_cost_basis=h.get("in_transit_asset_cost_basis"),
                    in_transit_book_value=h.get("in_transit_book_value"),
                    book_value=h.get("book_value"),
                    net_invested=h.get("net_invested"),
                    unrealized_gain_loss=h.get("unrealized_gain_loss"),
                    twrr=twrr,
                    mwrr_annualized=mwrr_ann,
                    mwrr_cumulative=mwrr_cum,
                    roi=roi,
                )
            )

        # First point always 0% for chart continuity (period starts here)
        if history_points:
            history_points[0].twrr = Decimal("0")
            history_points[0].mwrr_annualized = Decimal("0")
            history_points[0].mwrr_cumulative = Decimal("0")
            history_points[0].roi = Decimal("0")

        return history_points

    async def get_report(
        self,
        user_id: int,
        query: PortfolioReportQuery,
    ) -> PortfolioReportResponse:
        """Run the engine ONCE and return all requested views in a single response.

        Avoids the need for separate summary/history/allocation-history calls from
        the dashboard. A single POST /portfolio/report is enough for a full page load.
        """
        from backend.app.services.portfolio_engine import (  # noqa: PLC0415
            DerivedViewsBuilder,
            PortfolioCalculationEngine,
        )

        today = date_type.today()
        base_currency = query.target_currency or await self._get_base_currency()
        date_from = query.date_range.resolved_start() if query.date_range else None
        date_to = query.date_range.resolved_end() if query.date_range else None

        # ── 1. Single engine run ──
        engine = PortfolioCalculationEngine(self.db)
        engine_result = await engine.calculate(
            user_id=user_id,
            broker_ids=query.broker_ids,
            date_from=None,   # always from t=0 for correct cumulative values
            date_to=date_to,
            target_currency=base_currency,
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
                date_to=date_to,
                _precomputed_engine_result=engine_result,
            )

        # ── 3. History ──
        history: list[PortfolioHistoryPoint] | None = None
        if query.include_history:
            included.append("history")
            history = await self.get_history(
                user_id=user_id,
                broker_ids=query.broker_ids,
                date_from=date_from,
                date_to=date_to,
                target_currency_override=base_currency,
                _precomputed_engine_result=engine_result,
            )

        # ── 3b. MWRR series reliability check ──
        mwrr_series_unreliable = False
        _mwrr_divergence_info: dict[str, Any] = {}
        if summary and history and len(history) >= 2:
            summary_mwrr_cum = summary.mwrr_cumulative_percent
            history_last_mwrr_cum = history[-1].mwrr_cumulative
            if summary_mwrr_cum is not None and history_last_mwrr_cum is not None:
                divergence = abs(summary_mwrr_cum - history_last_mwrr_cum)
                # Relative tolerance: 5% of summary value or 50bp absolute, whichever is larger
                tolerance = max(Decimal("0.005"), abs(summary_mwrr_cum) * Decimal("0.05"))
                if divergence > tolerance:
                    # Retry with cold-start
                    history = await self.get_history(
                        user_id=user_id,
                        broker_ids=query.broker_ids,
                        date_from=date_from,
                        date_to=date_to,
                        target_currency_override=base_currency,
                        _precomputed_engine_result=engine_result,
                        _mwrr_use_warm_start=False,
                    )
                    # Re-check invariant
                    history_last_mwrr_cum = history[-1].mwrr_cumulative if history else None
                    if history_last_mwrr_cum is not None:
                        divergence = abs(summary_mwrr_cum - history_last_mwrr_cum)
                    if history_last_mwrr_cum is None or divergence > tolerance:
                        # Find first date where cumulative diverges significantly
                        first_bad_date: str | None = None
                        for pt in history:
                            if pt.mwrr_cumulative is not None and summary.mwrr_annualized_percent is not None:
                                days_from_start = (pt.date - history[0].date).days
                                expected_cum = annualized_to_cumulative(summary.mwrr_annualized_percent, days_from_start)
                                if expected_cum is not None and abs(pt.mwrr_cumulative - expected_cum) > tolerance:
                                    first_bad_date = str(pt.date)
                                    break
                        # Store info for issue
                        _mwrr_divergence_info = {
                            "summary_cum": str(round(float(summary_mwrr_cum) * 100, 2)),
                            "series_cum": str(round(float(history_last_mwrr_cum or 0) * 100, 2)),
                            "divergence_pp": str(round(float(divergence) * 100, 2)),
                            "first_bad_date": first_bad_date or "unknown",
                        }
                        # Null out MWRR in history
                        mwrr_series_unreliable = True
                        for pt in history:
                            object.__setattr__(pt, "mwrr_annualized", None)
                            object.__setattr__(pt, "mwrr_cumulative", None)

        # ── 4. Allocation history (all 3 dimensions from same engine result) ──
        alloc_history: AllocationHistoryDimensions | None = None
        if query.include_allocation_history:
            included.append("allocation_history")
            alloc_history = AllocationHistoryDimensions(
                type=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("type", date_from=date_from)],
                sector=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("sector", date_from=date_from)],
                geography=[AllocationHistoryPoint(**p) for p in views.build_allocation_history("geography", date_from=date_from)],
            )

        # ── 5. Data quality from engine (already computed if summary was built) ──
        data_quality = summary.data_quality if summary else views.build_data_quality_report(
            mwrr_available=False,
        )

        # Append MWRR series unreliable issue if needed
        if mwrr_series_unreliable and data_quality:
            mwrr_issue = DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MWRR_SERIES_UNRELIABLE,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.mwrrSeriesUnreliable",
                message_params=_mwrr_divergence_info,
            )
            data_quality.issues.append(mwrr_issue)

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

        return PortfolioReportResponse(
            metadata=metadata,
            summary=summary,
            history=history,
            allocation_history=alloc_history,
            data_quality=data_quality,
        )

    async def get_asset_history(
        self,
        user_id: int,
        asset_id: int,
        broker_id: int | None = None,
    ) -> list[AssetHistoryPoint]:
        """Return WAC vs market price series for a specific asset.

        Returns one point per date where both WAC and price are available.
        """

        base_currency = await self._get_base_currency()

        # Determine which brokers the user has access to
        accesses = await self._get_user_broker_access(user_id, [broker_id] if broker_id else None)
        if not accesses:
            return []

        # Use first accessible broker (or merge across brokers if multiple)
        target_broker_id = accesses[0].broker_id

        asset = await self._get_asset(asset_id)
        if not asset:
            return []

        # Get all price history for the asset
        stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id, PriceHistory.close.is_not(None)).order_by(PriceHistory.date)
        prices = list((await self.db.execute(stmt)).scalars().all())
        if not prices:
            return []

        result: list[AssetHistoryPoint] = []
        for ph in prices:
            wac_result = await compute_wac_iterative(
                session=self.db,
                broker_id=target_broker_id,
                asset_id=asset_id,
                as_of_date=ph.date,
                asset_currency=asset.currency or base_currency,
            )
            if wac_result.wac is None:
                continue

            wac_amount = wac_result.wac.amount
            market_price = ph.close

            result.append(AssetHistoryPoint(date=ph.date, wac=wac_amount, market_price=market_price))

        return result

    async def get_lots(
        self,
        user_id: int,
        broker_id: int,
        asset_id: int,
    ) -> FIFOLotsResponse:
        """Return FIFO open and closed lots for a specific (broker, asset) pair.

        Enriches open lots with unrealized P&L using the latest market price.
        """
        # Verify access
        accesses = await self._get_user_broker_access(user_id, [broker_id])
        if not accesses:
            return FIFOLotsResponse(
                open_lots=[],
                closed_lots=[],
                total_realized_pnl=Decimal("0"),
                total_unrealized_quantity=Decimal("0"),
            )

        # Fetch BUY/SELL transactions
        txns = await self._get_transactions(broker_id, tx_types=_HOLDING_TYPES)
        asset_txns = [t for t in txns if t.asset_id == asset_id]

        if not asset_txns:
            return FIFOLotsResponse(
                open_lots=[],
                closed_lots=[],
                total_realized_pnl=Decimal("0"),
                total_unrealized_quantity=Decimal("0"),
            )

        # Build FIFO inputs
        fifo_inputs: list[FIFOTransactionInput] = []

        for tx in asset_txns:
            if tx.quantity is None or tx.amount is None:
                continue
            qty = abs(tx.quantity)
            # Price per unit in asset currency
            price_per_unit = abs(tx.amount) / qty if qty else Decimal("0")
            tx_type = "BUY" if tx.type == TransactionType.BUY else "SELL"
            fifo_inputs.append(
                FIFOTransactionInput(
                    id=tx.id,
                    type=tx_type,
                    quantity=qty,
                    price=price_per_unit,
                    date=tx.date,
                )
            )

        fifo_result = calculate_fifo_lots(fifo_inputs)

        # Get current price for unrealized P&L enrichment
        price_data = await self._get_latest_price(asset_id)
        current_price: Decimal | None = price_data[0] if price_data else None

        open_lot_schemas: list[OpenLotSchema] = []
        for lot in fifo_result.open_lots:
            unrealized: Decimal | None = None
            if current_price is not None:
                unrealized = (current_price - lot.buy_price) * lot.remaining_quantity
            open_lot_schemas.append(
                OpenLotSchema(
                    buy_transaction_id=lot.buy_transaction_id,
                    buy_date=lot.buy_date,
                    buy_price=lot.buy_price,
                    original_quantity=lot.original_quantity,
                    remaining_quantity=lot.remaining_quantity,
                    unrealized_pnl=unrealized,
                )
            )

        closed_lot_schemas: list[ClosedLotSchema] = [
            ClosedLotSchema(
                buy_transaction_id=lot.buy_transaction_id,
                sell_transaction_id=lot.sell_transaction_id,
                buy_date=lot.buy_date,
                sell_date=lot.sell_date,
                buy_price=lot.buy_price,
                sell_price=lot.sell_price,
                quantity=lot.quantity,
                realized_pnl=lot.realized_pnl,
            )
            for lot in fifo_result.closed_lots
        ]

        return FIFOLotsResponse(
            open_lots=open_lot_schemas,
            closed_lots=closed_lot_schemas,
            total_realized_pnl=fifo_result.total_realized_pnl,
            total_unrealized_quantity=fifo_result.total_unrealized_quantity,
        )
