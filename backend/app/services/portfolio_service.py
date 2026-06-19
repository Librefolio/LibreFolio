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
from typing import NamedTuple, Optional

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
    AllocationItem,
    AssetHistoryPoint,
    BrokerBreakdown,
    ClosedLotSchema,
    FIFOLotsResponse,
    MissingPriceAsset,
    OpenLotSchema,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioSummary,
)
from backend.app.schemas.wac import WACMissingPairInfo, WACPreviewResultItem, WACQualifyingTX
from backend.app.services.fx import convert_bulk
from backend.app.services.settings_service import get_global_setting
from backend.app.utils.financial.fifo_utils import FIFOTransactionInput, calculate_fifo_lots
from backend.app.utils.financial.roi_utils import (
    CashFlowInput,
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
    ) -> PortfolioSummary:
        """Return aggregated portfolio summary via PortfolioCalculationEngine.

        Uses the new engine for aggregate values (NAV, market_value, book_value,
        allocation, performance) while keeping the per-asset holdings loop for
        individual holding details and broker breakdown.

        Fixes:
        - TWRR/MWRR now uses per-day NAV (not flat today's NAV)
        - Allocation uses engine's scope-aware calculation
        - Data quality report populated
        """
        from backend.app.services.portfolio_engine import (  # noqa: PLC0415
            DerivedViewsBuilder,
            PortfolioCalculationEngine,
        )

        today = date_type.today()
        base_currency = target_currency_override or await self._get_base_currency()

        # ── 1. Run engine for aggregate values + performance ──
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
        total_cost_basis = Decimal("0")
        all_cash_balances: dict[str, Decimal] = defaultdict(Decimal)
        all_holdings: list[PortfolioHolding] = []
        by_broker_list: list[BrokerBreakdown] = []
        all_missing_pairs: list[WACMissingPairInfo] = []
        missing_price_assets: list[MissingPriceAsset] = []

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

                if tx.type in _CASH_FLOW_TYPES:
                    total_invested += amount_base_signed * share

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
        simple_roi = calculate_simple_roi(engine_nav, total_invested)
        twrr_result: Decimal | None = None
        mwrr_result: Decimal | None = None

        if nav_snapshots and cash_flows_perf and engine_nav > 0:
            try:
                twrr_point = calculate_twrr(nav_snapshots, cash_flows_perf)
                twrr_result = twrr_point.twrr
            except (ValueError, ZeroDivisionError):
                twrr_result = None
            if total_invested > 0:
                mwrr_point = await asyncio.to_thread(
                    calculate_mwrr, cash_flows_perf, total_invested,
                    engine_nav, nav_snapshots[0].date, today,
                )
                mwrr_result = mwrr_point.mwrr

        total_gl = engine_nav - total_invested
        total_gl_pct = (total_gl / total_invested) if total_invested > 0 else Decimal("0")
        cash_balances_list = [Currency(code=ccy, amount=amt) for ccy, amt in all_cash_balances.items()]

        # ── 6. Data quality report ──
        data_quality = views.build_data_quality_report(
            missing_price_assets_dto=missing_price_assets,
            missing_fx_pairs_dto=self._merge_missing_pairs(all_missing_pairs),
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
            twrr_percent=twrr_result,
            mwrr_percent=mwrr_result,
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
    ) -> list[PortfolioHistoryPoint]:
        """Return daily portfolio value series via PortfolioCalculationEngine.

        Uses the new engine to produce a DailyPortfolioState[] vector, then derives
        history + performance metrics. Fixes known bugs:
        - NAV is per-day (not flat today's NAV for all dates)
        - Quantity tracking includes TRANSFER + ADJUSTMENT (not just BUY/SELL)
        - Linked internal transfers excluded from external cash flows
        """
        from backend.app.services.portfolio_engine import (  # noqa: PLC0415
            DerivedViewsBuilder,
            PortfolioCalculationEngine,
        )

        base_currency = target_currency_override or await self._get_base_currency()
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
            period_start_nav = pre_period[-1].nav if pre_period else nav_snapshots[0].nav
            period_start_date = pre_period[-1].date if pre_period else nav_snapshots[0].date

            synthetic_cf = CashFlowInput(date=period_start_date, amount=-period_start_nav)
            period_cash_flows = [synthetic_cf] + [cf for cf in cash_flows if cf.date > period_start_date]
            period_nav_snapshots = [s for s in nav_snapshots if s.date >= period_start_date]
        else:
            period_cash_flows = cash_flows
            period_nav_snapshots = nav_snapshots

        twrr_map: dict[date_type, Decimal] = {}
        roi_map: dict[date_type, Decimal] = {}
        mwrr_map: dict[date_type, Decimal] = {}

        if period_nav_snapshots and period_cash_flows:
            twrr_series = calculate_twrr_series(period_nav_snapshots, period_cash_flows)
            roi_series = calculate_simple_roi_series(period_nav_snapshots, period_cash_flows)
            mwrr_series = await asyncio.to_thread(
                calculate_mwrr_series, period_nav_snapshots, period_cash_flows
            )
            twrr_map = {pt.date: pt.twrr for pt in twrr_series}
            roi_map = {pt.date: pt.roi for pt in roi_series}
            mwrr_map = {pt.date: pt.mwrr for pt in mwrr_series}

        # ── Slice to [date_from, date_to] and merge performance ──
        history_points: list[PortfolioHistoryPoint] = []
        for h in history_dicts:
            d = h["date"]
            if date_from and d < date_from:
                continue

            twrr = twrr_map.get(d)
            roi = roi_map.get(d)
            mwrr = mwrr_map.get(d)

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
                    unrealized_gain_loss=h.get("unrealized_gain_loss"),
                    twrr=twrr,
                    mwrr=mwrr,
                    roi=roi,
                )
            )

        # First point gets 0% for chart continuity
        if history_points:
            if history_points[0].twrr is None:
                history_points[0].twrr = Decimal("0")
            if history_points[0].mwrr is None:
                history_points[0].mwrr = Decimal("0")
            if history_points[0].roi is None:
                history_points[0].roi = Decimal("0")

        return history_points

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
