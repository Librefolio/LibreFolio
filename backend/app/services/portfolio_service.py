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
from datetime import date as date_type
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
from backend.app.schemas.analytics import (
    AllocationItem,
    AssetHistoryPoint,
    BrokerBreakdown,
    ClosedLotSchema,
    FIFOLotsResponse,
    OpenLotSchema,
    PortfolioHistoryPoint,
    PortfolioHolding,
    PortfolioSummary,
)
from backend.app.schemas.assets import FAClassificationParams
from backend.app.schemas.common import Currency, FxBackwardFillInfo
from backend.app.schemas.wac import WACMissingPairInfo, WACPreviewResultItem, WACQualifyingTX
from backend.app.services.fx import convert_bulk
from backend.app.services.settings_service import get_global_setting
from backend.app.utils.financial.fifo_utils import FIFOTransactionInput, calculate_fifo_lots
from backend.app.utils.financial.roi_utils import (
    CashFlowInput,
    NAVSnapshot,
    calculate_mwrr,
    calculate_mwrr_series,
    calculate_simple_roi,
    calculate_simple_roi_series,
    calculate_twrr,
    calculate_twrr_series,
)
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

    This NamedTuple represents a single already-converted, already-scaled row.
    """

    date: date_type
    type: str  # "DEPOSIT" | "WITHDRAWAL" | "BUY" | "SELL"
    amount: Decimal  # absolute value, already converted to base currency, > 0
    share: Decimal  # broker ownership fraction (0.0-1.0), already incorporated in amount


class _HistoryQtyRow(NamedTuple):
    """Quantity delta for a single BUY or SELL transaction.

    Parallel to _HistoryTxRow but carries per-asset quantity info so that
    get_history() can compute mark-to-market holdings value.
    qty_delta is share-adjusted and signed: positive for BUY, negative for SELL.
    """

    date: date_type
    asset_id: int
    qty_delta: Decimal  # share-adjusted signed quantity change


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
) -> list[PortfolioHistoryPoint]:
    """Build daily portfolio value series from pre-processed transaction rows.

    Pure function — no I/O, no DB, no async. Deterministic given the same input.

    Rules:
    - DEPOSIT    → cumulative_cash += amount * share
    - WITHDRAWAL → cumulative_cash -= amount * share
    - BUY        → cumulative_cash -= amount * share; cumulative_invested += amount * share
    - SELL       → cumulative_cash += amount * share; cumulative_invested -= amount * share
    - NAV = cash + invested (approximation — no live prices)
    - Output is sorted by date ascending.
    - Multiple transactions on the same date: each updates the daily snapshot cumulatively.
      The snapshot for a date records the state AFTER all transactions of that day.

    Args:
        transactions: List of _HistoryTxRow, may be in any order (will be sorted).

    Returns:
        List of PortfolioHistoryPoint, one per distinct date, sorted ascending.
    """
    if not transactions:
        return []

    daily: dict[date_type, dict[str, Decimal]] = defaultdict(lambda: {"cash": Decimal("0"), "invested": Decimal("0"), "nav": Decimal("0")})

    cumulative_cash = Decimal("0")
    cumulative_invested = Decimal("0")

    for row in sorted(transactions, key=lambda r: r.date):
        effective = row.amount * row.share
        if row.type == "DEPOSIT":
            cumulative_cash += effective
        elif row.type == "WITHDRAWAL":
            cumulative_cash -= effective
        elif row.type == "BUY":
            cumulative_cash -= effective
            cumulative_invested += effective
        elif row.type == "SELL":
            cumulative_cash += effective
            cumulative_invested -= effective
        # Unknown types are silently skipped.

        daily[row.date]["cash"] = cumulative_cash
        daily[row.date]["invested"] = cumulative_invested
        daily[row.date]["nav"] = cumulative_cash + cumulative_invested

    return [
        PortfolioHistoryPoint(
            date=dt,
            cash_value=daily[dt]["cash"],
            invested_value=daily[dt]["invested"],
            nav_value=daily[dt]["nav"],
        )
        for dt in sorted(daily.keys())
    ]


# =============================================================================
# PORTFOLIO SERVICE — Orchestrator
# =============================================================================

_DEPOSIT_TYPES = {TransactionType.DEPOSIT}
_WITHDRAWAL_TYPES = {TransactionType.WITHDRAWAL}
_CASH_FLOW_TYPES = _DEPOSIT_TYPES | _WITHDRAWAL_TYPES
_HOLDING_TYPES = {TransactionType.BUY, TransactionType.SELL}


class PortfolioService:
    """Orchestrator for portfolio-level analytics.

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
        """Return aggregated portfolio summary.

        Flow:
        1. Get accessible brokers for user (optionally filtered by broker_ids).
        2. Per broker: compute WAC per asset, get current prices, aggregate.
        3. Apply share_percentage on broker-level values BEFORE aggregation.
        4. Compute ROI metrics (simple ROI, TWRR, MWRR).
        5. Build allocation breakdown (by type, sector, geo).
        """

        today = date_type.today()

        base_currency = target_currency_override or await self._get_base_currency()
        accesses = await self._get_user_broker_access(user_id, broker_ids)

        total_nav = Decimal("0")
        total_invested = Decimal("0")  # capital deployed = deposits - withdrawals (in base currency)
        total_cost_basis = Decimal("0")  # cost basis of current holdings (for per-holding P&L)
        total_cash = Decimal("0")
        all_cash_balances: dict[str, Decimal] = defaultdict(Decimal)
        all_holdings: list[PortfolioHolding] = []
        by_broker_list: list[BrokerBreakdown] = []
        nav_snapshots: list[NAVSnapshot] = []
        cash_flows: list[CashFlowInput] = []
        all_missing_pairs: list[WACMissingPairInfo] = []
        allocation_by_type: dict[str, Decimal] = defaultdict(Decimal)
        allocation_by_sector: dict[str, Decimal] = defaultdict(Decimal)
        allocation_by_geo: dict[str, Decimal] = defaultdict(Decimal)

        for access in accesses:
            broker_id = access.broker_id
            share = access.share_percentage or Decimal("1")

            # --- Cash transactions ---
            cash_txns = await self._get_transactions(broker_id, tx_types=_CASH_FLOW_TYPES)
            broker_cash: dict[str, Decimal] = defaultdict(Decimal)
            for tx in cash_txns:
                if tx.amount is None or tx.currency is None:
                    continue
                # Convert to base currency for capital tracking
                if tx.currency == base_currency:
                    amount_base_cf = abs(tx.amount)
                else:
                    cf_results, _ = await convert_bulk(
                        self.db,
                        [(Currency(code=tx.currency, amount=abs(tx.amount)), base_currency, tx.date)],
                        raise_on_error=False,
                    )
                    amount_base_cf = cf_results[0][0].amount if cf_results and cf_results[0] is not None else Decimal("0")

                if tx.type == TransactionType.DEPOSIT:
                    broker_cash[tx.currency] += abs(tx.amount)
                    total_invested += amount_base_cf * share  # capital deployed
                    cash_flows.append(CashFlowInput(tx.date, -amount_base_cf * share))
                elif tx.type == TransactionType.WITHDRAWAL:
                    broker_cash[tx.currency] -= abs(tx.amount)
                    total_invested -= amount_base_cf * share  # capital returned
                    cash_flows.append(CashFlowInput(tx.date, amount_base_cf * share))

            # --- Holding transactions ---
            hold_txns = await self._get_transactions(broker_id, tx_types=_HOLDING_TYPES)
            # Group by asset
            txns_by_asset: dict[int, list[Transaction]] = defaultdict(list)
            for tx in hold_txns:
                if tx.asset_id is not None:
                    txns_by_asset[tx.asset_id].append(tx)

            broker_market_value = Decimal("0")

            for asset_id, asset_txns in txns_by_asset.items():
                asset = await self._get_asset(asset_id)
                if not asset:
                    continue

                wac_result = await compute_wac_iterative(
                    session=self.db,
                    broker_id=broker_id,
                    asset_id=asset_id,
                    as_of_date=today,
                    asset_currency=asset.currency or base_currency,
                )

                if wac_result.wac is None:
                    if wac_result.wac_missing_pairs:
                        all_missing_pairs.extend(wac_result.wac_missing_pairs)
                    continue

                wac_per_unit = wac_result.wac.amount
                wac_currency = wac_result.wac.code

                # Get pool quantity — compute net from txns directly
                net_qty = sum((tx.quantity or Decimal("0")) for tx in asset_txns if tx.type in (TransactionType.BUY, TransactionType.SELL))
                if net_qty <= 0:
                    continue

                # Get current market price
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
                            all_missing_pairs.extend(mp)
                    else:
                        current_price = raw_price

                if current_price is not None:
                    current_value = current_price * net_qty * share
                    broker_market_value += current_value

                # Convert WAC to base_currency for comparisons
                if wac_currency != base_currency:
                    wac_base, mp = await self._convert_to_base(wac_per_unit, wac_currency, base_currency, today)
                    all_missing_pairs.extend(mp)
                else:
                    wac_base = wac_per_unit

                cost_basis = (wac_base or wac_per_unit) * net_qty * share
                total_cost_basis += cost_basis

                if current_value is not None and wac_base is not None:
                    gain_loss = current_value - cost_basis
                    gain_loss_pct = (gain_loss / cost_basis) if cost_basis != 0 else Decimal("0")

                # Allocation data — parse classification_params for sector/geo distributions
                cp: FAClassificationParams | None = None
                if asset.classification_params:
                    try:
                        cp = FAClassificationParams.model_validate_json(asset.classification_params)
                    except Exception:
                        pass

                asset_type = asset.asset_type.value if asset.asset_type else "Unknown"
                if current_value:
                    allocation_by_type[asset_type] += current_value
                    if cp and cp.sector_area and cp.sector_area.distribution:
                        for sector, weight in cp.sector_area.distribution.items():
                            allocation_by_sector[sector] += current_value * weight
                    else:
                        allocation_by_sector["Unknown"] += current_value
                    if cp and cp.geographic_area and cp.geographic_area.distribution:
                        for country, weight in cp.geographic_area.distribution.items():
                            allocation_by_geo[country] += current_value * weight
                    else:
                        allocation_by_geo["Unknown"] += current_value

                all_holdings.append(
                    PortfolioHolding(
                        asset_id=asset_id,
                        asset_name=asset.display_name,
                        asset_ticker=asset.identifier_ticker,
                        asset_type=asset_type,
                        quantity=net_qty,
                        wac_per_unit=wac_base if wac_base else wac_per_unit,
                        current_price=current_price,
                        current_value=current_value,
                        gain_loss=gain_loss,
                        gain_loss_percent=gain_loss_pct,
                        allocation_percent=None,  # computed after full aggregation
                    )
                )

            # --- Broker-level cash in base currency ---
            broker_cash_base = Decimal("0")
            for ccy, amt in broker_cash.items():
                if ccy == base_currency:
                    broker_cash_base += amt * share
                    all_cash_balances[ccy] += amt * share
                else:
                    converted, mp = await self._convert_to_base(amt, ccy, base_currency, today)
                    all_missing_pairs.extend(mp)
                    if converted is not None:
                        broker_cash_base += converted * share
                        all_cash_balances[ccy] += amt * share

            total_cash += broker_cash_base
            broker_nav = broker_market_value + broker_cash_base
            total_nav += broker_nav

            # Broker breakdown
            if include_breakdown:
                broker = await self._get_broker(broker_id)
                broker_name = broker.name if broker else f"Broker {broker_id}"
                broker_gain = broker_nav - total_invested  # approx per broker
                broker_gl_pct = (broker_gain / total_invested) if total_invested else Decimal("0")
                by_broker_list.append(
                    BrokerBreakdown(
                        broker_id=broker_id,
                        broker_name=broker_name,
                        net_worth=broker_nav,
                        gain_loss=broker_gain,
                        gain_loss_percent=broker_gl_pct,
                        cash_total=broker_cash_base,
                    )
                )

        # --- Compute allocation percentages ---
        total_market = sum(allocation_by_type.values()) or Decimal("1")

        def _alloc(d: dict[str, Decimal]) -> list[AllocationItem]:
            return [
                AllocationItem(
                    name=name,
                    value=(amt / total_market * 100).quantize(Decimal("0.01")),
                    amount=amt,
                )
                for name, amt in sorted(d.items(), key=lambda x: -x[1])
            ]

        # Update holdings allocation_percent
        for h in all_holdings:
            if h.current_value and total_market:
                object.__setattr__(h, "allocation_percent", (h.current_value / total_market * 100).quantize(Decimal("0.01")))

        # --- ROI Metrics ---
        simple_roi = calculate_simple_roi(total_nav, total_invested)

        # Build NAV snapshots at CF dates + today for TWRR/MWRR
        cf_dates = sorted({cf.date for cf in cash_flows})
        twrr_result: Decimal | None = None
        mwrr_result: Decimal | None = None

        if len(cf_dates) >= 1 and total_nav > 0:
            nav_snapshots = [NAVSnapshot(d, total_nav) for d in cf_dates] + [NAVSnapshot(today, total_nav)]
            try:
                twrr_point = calculate_twrr(nav_snapshots, cash_flows)
                twrr_result = twrr_point.twrr
            except (ValueError, ZeroDivisionError):
                twrr_result = None

            if total_invested > 0:
                mwrr_point = await asyncio.to_thread(
                    calculate_mwrr,
                    cash_flows,
                    total_invested,  # initial capital deployed
                    total_nav,
                    cf_dates[0],
                    today,
                )
                mwrr_result = mwrr_point.mwrr

        # total_gl = net_worth - capital_deployed  (how much the portfolio grew vs what was put in)
        total_gl = total_nav - total_invested
        total_gl_pct = (total_gl / total_invested) if total_invested > 0 else Decimal("0")

        cash_balances_list = [Currency(code=ccy, amount=amt) for ccy, amt in all_cash_balances.items()]

        return PortfolioSummary(
            net_worth=total_nav,
            total_invested=total_invested,
            total_gain_loss=total_gl,
            total_gain_loss_percent=total_gl_pct,
            cash_total=total_cash,
            cash_balances=cash_balances_list,
            twrr_percent=twrr_result,
            mwrr_percent=mwrr_result,
            simple_roi_percent=simple_roi,
            allocation_by_type=_alloc(allocation_by_type),
            allocation_by_sector=_alloc(allocation_by_sector),
            allocation_by_geography=_alloc(allocation_by_geo),
            holdings=all_holdings,
            by_broker=by_broker_list if include_breakdown else None,
            wac_missing_pairs=all_missing_pairs,
        )

    async def get_history(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency_override: str | None = None,
    ) -> list[PortfolioHistoryPoint]:
        """Return daily portfolio value series (cash, invested, NAV) in base currency.

        NAV is computed as mark-to-market: cumulative_cash + Σ(qty_i × price_i × FX_i).
        This makes TWRR/ROI non-zero when asset prices change between snapshots.

        Always accumulates the full history from t=0 regardless of date_from,
        so that NAV/invested balances are correct. The display series is then
        sliced to [date_from, date_to] and ROI metrics are re-based to the
        period start so that TWRR/MWRR/ROI show the return OF that specific
        period (starting from ~0%).

        Only includes dates where transactions exist.
        """
        base_currency = target_currency_override or await self._get_base_currency()
        accesses = await self._get_user_broker_access(user_id, broker_ids)

        rows: list[_HistoryTxRow] = []
        qty_rows: list[_HistoryQtyRow] = []

        for access in accesses:
            broker_id = access.broker_id
            share = access.share_percentage or Decimal("1")

            # Always fetch full history from t=0 — date_from only slices the output.
            all_txns = await self._get_transactions(
                broker_id,
                date_from=None,
                date_to=date_to,
            )

            for tx in all_txns:
                if tx.amount is None:
                    continue
                if tx.type not in (_DEPOSIT_TYPES | _WITHDRAWAL_TYPES | _HOLDING_TYPES):
                    continue

                # Convert to base currency
                if tx.currency == base_currency:
                    amount_base: Decimal | None = abs(tx.amount)
                else:
                    fx_results, _ = await convert_bulk(
                        self.db,
                        [(Currency(code=tx.currency, amount=abs(tx.amount)), base_currency, tx.date)],
                        raise_on_error=False,
                    )
                    amount_base = fx_results[0][0].amount if fx_results and fx_results[0] is not None else None

                if amount_base is None:
                    continue

                rows.append(
                    _HistoryTxRow(
                        date=tx.date,
                        type=tx.type.value if hasattr(tx.type, "value") else str(tx.type),
                        amount=amount_base,
                        share=share,
                    )
                )

                # Track per-asset quantities for mark-to-market NAV computation.
                if tx.type in _HOLDING_TYPES and tx.asset_id is not None and tx.quantity is not None and tx.quantity != 0:
                    qty_sign = Decimal("1") if tx.type == TransactionType.BUY else Decimal("-1")
                    qty_rows.append(_HistoryQtyRow(date=tx.date, asset_id=tx.asset_id, qty_delta=abs(tx.quantity) * qty_sign * share))

        all_history = _build_history_series(rows)
        if not all_history:
            return all_history

        # ── Mark-to-market: patch invested_value / nav_value ─────────────────
        # Build cumulative quantity snapshots keyed by snapshot date.
        held_asset_ids = {r.asset_id for r in qty_rows}
        if held_asset_ids:
            date_min = all_history[0].date
            date_max = all_history[-1].date
            price_map = await self._bulk_load_asset_prices(held_asset_ids, date_min, date_max)

            # Collect all (price_ccy → base_ccy, date) conversions needed — one bulk call.
            # First pass: build snap_qtys (cumulative quantities at each snapshot date)
            # and collect FX conversion requests for market values priced in non-base currency.
            fx_inputs: list[tuple[Currency, str, date_type]] = []
            fx_index: list[tuple[int, date_type]] = []  # (asset_id, date) for each fx_inputs entry

            snap_qtys: dict[date_type, dict[int, Decimal]] = {}
            cumulative_qtys_snapshot: dict[int, Decimal] = defaultdict(Decimal)
            qi = 0
            qty_rows_sorted = sorted(qty_rows, key=lambda r: r.date)

            for pt in all_history:
                while qi < len(qty_rows_sorted) and qty_rows_sorted[qi].date <= pt.date:
                    r = qty_rows_sorted[qi]
                    cumulative_qtys_snapshot[r.asset_id] += r.qty_delta
                    qi += 1
                snap_qtys[pt.date] = dict(cumulative_qtys_snapshot)

                for asset_id, qty in snap_qtys[pt.date].items():
                    if qty <= Decimal("0"):
                        continue
                    price_info = _price_on_date(price_map.get(asset_id, []), pt.date)
                    if price_info is None:
                        continue
                    price, price_ccy = price_info
                    if price_ccy != base_currency:
                        fx_inputs.append((Currency(code=price_ccy, amount=price * qty), base_currency, pt.date))
                        fx_index.append((asset_id, pt.date))
                    # else identity — no FX conversion needed

            # Bulk FX conversion for all market values that need it.
            fx_results_bulk: list = []
            if fx_inputs:
                fx_results_bulk, _ = await convert_bulk(self.db, fx_inputs, raise_on_error=False)

            # Build lookup: (asset_id, date) → converted_market_value (or None).
            fx_mv_map: dict[tuple[int, date_type], Decimal] = {}
            for i, (asset_id, snap_date) in enumerate(fx_index):
                if i < len(fx_results_bulk) and fx_results_bulk[i] is not None:
                    converted, _, _ = fx_results_bulk[i]
                    fx_mv_map[(asset_id, snap_date)] = converted.amount
                # else: no conversion available → asset excluded from market value

            # Second pass: patch each history point with mark-to-market values.
            for pt in all_history:
                market_value = Decimal("0")
                for asset_id, qty in snap_qtys[pt.date].items():
                    if qty <= Decimal("0"):
                        continue
                    price_info = _price_on_date(price_map.get(asset_id, []), pt.date)
                    if price_info is None:
                        continue
                    price, price_ccy = price_info
                    if price_ccy == base_currency:
                        market_value += qty * price
                    else:
                        mv = fx_mv_map.get((asset_id, pt.date))
                        if mv is not None:
                            market_value += mv

                pt.invested_value = market_value
                pt.nav_value = pt.cash_value + market_value

        # Slice display series to [date_from, date_to]
        if date_from:
            history = [pt for pt in all_history if pt.date >= date_from]
        else:
            history = all_history

        if not history:
            return history

        # ── Full NAV snapshots and cash flows (from t=0) ──────────────────────
        all_nav_snapshots = [NAVSnapshot(date=pt.date, nav=pt.nav_value) for pt in all_history]
        all_cash_flows: list[CashFlowInput] = []
        for row in rows:
            if row.type == "DEPOSIT":
                all_cash_flows.append(CashFlowInput(date=row.date, amount=-(row.amount * row.share)))
            elif row.type == "WITHDRAWAL":
                all_cash_flows.append(CashFlowInput(date=row.date, amount=row.amount * row.share))

        # ── Period re-basing for ROI metrics ─────────────────────────────────
        # If date_from is set, inject the period-start NAV as a synthetic negative
        # cash flow so that TWRR/MWRR/ROI represent the return OF this period.
        if date_from and all_history:
            # NAV at (or just before) date_from — last available point <= date_from
            pre_period = [pt for pt in all_history if pt.date <= date_from]
            period_start_nav = pre_period[-1].nav_value if pre_period else all_history[0].nav_value
            period_start_date = pre_period[-1].date if pre_period else history[0].date

            # Synthetic "investor starts with this NAV" cash flow
            synthetic_cf = CashFlowInput(date=period_start_date, amount=-period_start_nav)
            # Only keep original cash flows strictly after period start
            period_cash_flows = [synthetic_cf] + [cf for cf in all_cash_flows if cf.date > period_start_date]
            # NAV snapshots from the period start onwards
            period_nav_snapshots = [s for s in all_nav_snapshots if s.date >= period_start_date]
        else:
            period_cash_flows = all_cash_flows
            period_nav_snapshots = all_nav_snapshots

        if period_nav_snapshots and period_cash_flows:
            # TWRR and Simple ROI are O(N) CPU-light — run inline.
            twrr_series = calculate_twrr_series(period_nav_snapshots, period_cash_flows)
            roi_series = calculate_simple_roi_series(period_nav_snapshots, period_cash_flows)
            # MWRR runs Newton-Raphson per point — offload to thread pool.
            mwrr_series = await asyncio.to_thread(calculate_mwrr_series, period_nav_snapshots, period_cash_flows)

            # Build date-keyed lookup dicts for O(1) mapping
            twrr_map = {pt.date: pt.twrr for pt in twrr_series}
            roi_map = {pt.date: pt.roi for pt in roi_series}
            mwrr_map = {pt.date: pt.mwrr for pt in mwrr_series}

            for pt in history:
                pt.twrr = twrr_map.get(pt.date)
                pt.roi = roi_map.get(pt.date)
                pt.mwrr = mwrr_map.get(pt.date)

            # The first history point is always index-0 in the series: both
            # twrr_series and mwrr_series skip it by design (no prior period).
            # For chart continuity the starting value is mathematically 0%.
            if history:
                if history[0].twrr is None:
                    history[0].twrr = Decimal("0")
                if history[0].mwrr is None:
                    history[0].mwrr = Decimal("0")

        return history

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
