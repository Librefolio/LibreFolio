"""The daily portfolio state vector: positions, cash, valuation, capital and P&L for every day of the range, without I/O."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal

import structlog

from backend.app.db.models import Transaction, TransactionType
from backend.app.services.financial_math.average_cost import (
    AverageCost,
    CostEffect,
    CostStep,
)
from backend.app.services.financial_math.native_cash import NativeCash, change_days
from backend.app.services.financial_math.portfolio.classifier import _CASH_LINKED_TYPES, _LINKED_TYPES
from backend.app.services.financial_math.portfolio.models import (
    AcquisitionFundingContribution,
    BrokerDailyContribution,
    ClassifiedTransaction,
    DailyPortfolioState,
    DailyPositionState,
    EngineEndState,
    InTransitInterval,
    PnlCandleContribution,
    PortfolioCalculationResult,
    RealizedSale,
    SplitHistory,
    SplitRecord,
    UnrealizedSplit,
    ValuationResult,
    ValuationSource,
)
from backend.app.services.financial_math.price_marks import AssetPriceSeries
from backend.app.services.financial_math.valuation import compute_holding_value
from backend.app.services.platform.data_quality_thresholds import STALE_PRICE_THRESHOLD_DAYS

logger = structlog.get_logger(__name__)


def _cumulative_split_ratio(history: SplitHistory, reference_date: date_type, valuation_date: date_type) -> tuple[Decimal, bool]:
    """Return product of split ratios in (reference_date, valuation_date]."""

    ratio = Decimal("1")
    adjusted = False
    for split in history:
        if reference_date < split.date <= valuation_date:
            ratio *= split.ratio
            adjusted = True
    return ratio, adjusted


def _calendar(first: date_type, last: date_type) -> list[date_type]:
    """Every day from ``first`` to ``last``, both included."""
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


# =============================================================================
# DAILY STATE BUILDER — Pure function, no I/O
# =============================================================================


class DailyStateBuilder:
    """Builds a dense DailyPortfolioState[] vector for every calendar day.

    Pure function — no I/O, no DB, no async. All data is pre-loaded.

    The cost of every position comes from ``average_costs`` (financial_math.average_cost,
    computed by the engine before the replay): each (asset_id, broker_id) pool is the
    historical cost in target_currency, every acquisition converted at its own date. The
    builder replays each position's cost steps in the order of its transactions and never
    converts a cost itself.
    """

    def __init__(
        self,
        *,
        classified_txs: list[ClassifiedTransaction],
        in_transit_intervals: list[InTransitInterval],
        external_cash_flows: list[tuple[date_type, int, Decimal, str]],
        price_map: dict[int, list[tuple[date_type, Decimal, str]]],
        quote_base_map: dict[int, int | None],
        fx_rate_map: dict[tuple[str, str, date_type], Decimal],
        asset_classifications: dict[int, dict | None],
        asset_types: dict[int, str],
        asset_currencies: dict[int, str],
        average_costs: Mapping[tuple[int, int], AverageCost],
        native_cash: NativeCash,
        target_currency: str,
        date_from: date_type,
        date_to: date_type,
        frame_start: date_type | None = None,
        split_linked_tx_ids: set[int] | None = None,
        split_history: dict[int, SplitHistory] | None = None,
        mark_series: dict[int, AssetPriceSeries] | None = None,
        compute_candles: bool = False,
        compute_acquisition_funding: bool = False,
    ) -> None:
        self.classified_txs = classified_txs
        self.in_transit_intervals = in_transit_intervals
        self.external_cash_flows = external_cash_flows
        self.price_map = price_map
        self.quote_base_map = quote_base_map
        self.fx_rate_map = fx_rate_map
        self.asset_classifications = asset_classifications
        self.asset_types = asset_types
        self.asset_currencies = asset_currencies
        # Average cost of every position, keyed (asset_id, broker_id): see build_cost_positions().
        self.average_costs = average_costs
        # Every broker's cash in its own currencies (financial_math.native_cash): revalues
        # foreign cash on each rate-change day, see _revalue_foreign_cash().
        self.native_cash = native_cash
        self.target_currency = target_currency
        self.date_from = date_from
        self.date_to = date_to
        # Transaction ids for ADJUSTMENT rows linked to an AssetEvent of type SPLIT.
        # A split redistributes existing cost over a new quantity: it never adds or
        # removes economic cost, nor capital. Populated by PortfolioCalculationEngine.calculate().
        self.split_linked_tx_ids: set[int] = split_linked_tx_ids or set()
        # Replay state: next cost step of each position, and the conversions movements
        # needed but could not get (pair "FROM/TO" -> dates). Reset by build().
        self._cost_cursor: dict[tuple[int, int], int] = {}
        self._missing_fx: dict[str, set[date_type]] = defaultdict(set)
        # frame_start: first day to emit DailyPortfolioState. Before this = pre-frame (accounting only).
        # None → same as date_from (no pre-frame, full evaluation from start).
        self.frame_start = frame_start if frame_start is not None else date_from
        self.split_history: dict[int, SplitHistory] = {}
        for asset_id, history in (split_history or {}).items():
            unique_by_event_id: dict[int, SplitRecord] = {}
            for split in history:
                if split.asset_id != asset_id:
                    raise ValueError("split history key must match SplitRecord.asset_id")
                if not split.ratio.is_finite() or split.ratio <= 0:
                    raise ValueError("split ratio must be positive and finite")
                unique_by_event_id[split.event_id] = split
            self.split_history[asset_id] = tuple(sorted(unique_by_event_id.values(), key=lambda split: (split.date, split.event_id)))
        # Per-asset unified price-resolver series: the single valuation brain. Each held asset gets
        # one AssetPriceSeries fed with both asset-system quotes and observed trades (in the asset's
        # native currency); _market_value_for converts each mark to the reporting currency at the
        # valuation date. Populated by PortfolioCalculationEngine.calculate().
        self.mark_series: dict[int, AssetPriceSeries] = mark_series or {}
        # G1b — synthetic P&L candles (plan §4.3). False by default: the daily OHLC composition
        # below is opt-in extra Decimal/FX work per plan §4.1 ("expensive OHLC work stays off
        # ordinary reports"), never run unless a caller explicitly requests candles.
        self.compute_candles = compute_candles
        # Batch 2 — new-vs-reinvested BUY funding split (plan §5.2). False by default:
        # this is a pure bookkeeping side-capture of values the BUY branch already
        # computes for the 3-pool update, so the extra cost is negligible either way,
        # but stays opt-in for consistency with compute_candles's "extra output stays
        # off ordinary reports unless requested" convention.
        self.compute_acquisition_funding = compute_acquisition_funding

    def build(self) -> PortfolioCalculationResult:  # noqa: C901 — TODO(P2-refactor): monolithic daily-replay engine; extract pre-frame/frame stages
        """Build daily states for [frame_start, date_to] + position snapshots + period accumulators.

        Architecture (pre-frame / frame split):
        - Pre-frame [date_from, frame_start): update accumulators only (cash, qty, cost pools, K/R/W).
          No market evaluation, no FX lookups for prices, no state emission.
        - Frame [frame_start, date_to]: full daily evaluation + DailyPortfolioState emission.
        """
        zero = Decimal("0")

        # Replay state. Conversions the cost computation could not make are movement failures too.
        self._cost_cursor = {}
        self._missing_fx = defaultdict(set)
        for average_cost in self.average_costs.values():
            for missing in average_cost.missing:
                self._missing_fx[missing.pair].update(missing.dates)
        realized_sales: list[RealizedSale] = []

        # ── 1. Cash ledger: sum amount deltas per day ──
        cash_deltas: dict[date_type, Decimal] = defaultdict(lambda: zero)
        cash_deltas_by_broker: dict[tuple[date_type, int], Decimal] = defaultdict(lambda: zero)
        for ctxn in self.classified_txs:
            tx = ctxn.tx
            if tx.amount and tx.amount != 0 and tx.currency:
                converted = self._convert_movement(tx.amount, tx.currency, tx.date)
                if converted is not None:
                    delta = converted * ctxn.share
                    cash_deltas[tx.date] += delta
                    cash_deltas_by_broker[(tx.date, tx.broker_id)] += delta

        # ── 2. Position transactions by date (replayed against their average-cost steps) ──
        position_txs_by_date: dict[date_type, list[ClassifiedTransaction]] = defaultdict(list)
        for ctxn in self.classified_txs:
            tx = ctxn.tx
            if tx.quantity and tx.quantity != 0 and tx.asset_id is not None:
                position_txs_by_date[tx.date].append(ctxn)

        # ── 2b. All transactions by date (for 3-pool event processing) ──
        all_txs_by_date: dict[date_type, list[ClassifiedTransaction]] = defaultdict(list)
        for ctxn in self.classified_txs:
            all_txs_by_date[ctxn.tx.date].append(ctxn)

        # ── 3. External cash flow index ──
        ecf_by_date: dict[date_type, Decimal] = defaultdict(lambda: zero)
        ecf_by_date_by_broker: dict[tuple[date_type, int], Decimal] = defaultdict(lambda: zero)
        for dt, bid, amount, ccy in self.external_cash_flows:
            converted = self._convert_movement(amount, ccy, dt)
            if converted is not None:
                ecf_by_date[dt] += converted
                ecf_by_date_by_broker[(dt, bid)] += converted

        # ── 3b. Lot 41 — internal flows between brokers (per-broker capital only) ──
        # An internal pair across two brokers moves X of capital from the sender to the
        # receiver on the arrival day, the same Decimal on both sides, so the broker
        # lines do not jump when the value changes hands. Never into ecf_by_date: the
        # scope capital (cumulative_ecf) and every aggregate stay as they are.
        internal_flow_dates: set[date_type] = set()
        for flow_date, sender_bid, receiver_bid, flow_value in self._internal_transfer_flows():
            ecf_by_date_by_broker[(flow_date, sender_bid)] -= flow_value
            ecf_by_date_by_broker[(flow_date, receiver_bid)] += flow_value
            internal_flow_dates.add(flow_date)

        # ── 4. Accumulators (shared across pre-frame and frame) ──
        states: list[DailyPortfolioState] = []
        cumulative_cash = zero
        cumulative_ecf = zero
        # G1a — additive per-broker contribution accumulators. Mirrors of the scope
        # aggregates above, incremented at every one of the same mutation sites with
        # the same Decimal amounts, so sum(...values()) == the aggregate holds by
        # construction rather than by a post-hoc reconciliation/residual line.
        cumulative_cash_by_broker: dict[int, Decimal] = defaultdict(lambda: zero)
        cumulative_ecf_by_broker: dict[int, Decimal] = defaultdict(lambda: zero)
        cumulative_qty: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)
        # Pool of every position after its last replayed movement (historical cost in target_currency)
        cost_pool: dict[tuple[int, int], CostStep] = {}
        # 3-pool: per-broker K and R, global W
        K: dict[int, Decimal] = defaultdict(lambda: zero)  # capital pool per broker
        R: dict[int, Decimal] = defaultdict(lambda: zero)  # returns pool per broker
        W: Decimal = zero  # withdrawn returns (global, exits system)
        # Position state snapshots
        position_states_start: list[DailyPositionState] = []
        position_states_end: list[DailyPositionState] = []
        is_first_frame_day = True
        # Universe of broker ids in this scope — used to fan out the date-only
        # cash/ECF aggregates above into their per-broker components below.
        all_broker_ids: set[int] = {ctxn.tx.broker_id for ctxn in self.classified_txs}

        # ── 5. PRE-FRAME: [date_from, frame_start) — accounting only ──
        # Process all transaction days before frame_start: update cash, qty, cost pools, ECF.
        # No market evaluation, no DailyPortfolioState emission. A day the rate of a held
        # foreign currency changes is replayed too: its cash is revalued.
        preframe_fx_days = set(self.native_cash.rate_change_days(None, self.frame_start - timedelta(days=1)))
        preframe_tx_dates = sorted(d for d in (set(cash_deltas.keys()) | set(position_txs_by_date.keys()) | set(ecf_by_date.keys()) | internal_flow_dates | preframe_fx_days) if d < self.frame_start)
        for day in preframe_tx_dates:
            cumulative_cash += cash_deltas.get(day, zero)
            cumulative_ecf += ecf_by_date.get(day, zero)
            for bid in all_broker_ids:
                cumulative_cash_by_broker[bid] += cash_deltas_by_broker.get((day, bid), zero)
                cumulative_ecf_by_broker[bid] += ecf_by_date_by_broker.get((day, bid), zero)
            # Exchange result on foreign cash: after the day's cash, before its pool rules
            if day in preframe_fx_days:
                for exchange_result in self._revalue_foreign_cash(day, cumulative_cash_by_broker, K, R):
                    cumulative_cash += exchange_result
            # Pre-frame 3-pool per-broker: process all tx types
            for ctxn in all_txs_by_date.get(day, []):
                tx = ctxn.tx
                bid = tx.broker_id
                if tx.amount is None or tx.amount == 0 or tx.currency is None:
                    continue
                amt = self._convert_movement(abs(tx.amount), tx.currency, tx.date)
                if amt is None:
                    continue
                amt = amt * ctxn.share
                if tx.type == TransactionType.DEPOSIT:
                    restore = min(amt, W)
                    R[bid] += restore
                    W -= restore
                    K[bid] += amt - restore
                elif tx.type == TransactionType.WITHDRAWAL:
                    from_k = min(amt, max(K[bid], zero))
                    K[bid] -= from_k
                    remaining = amt - from_k
                    from_r = min(remaining, max(R[bid], zero))
                    R[bid] -= from_r
                    W += from_r
                elif tx.type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
                    # Signed: preserve a legacy negative correction (plan §4.4). `amt` is
                    # abs(tx.amount) converted through the same (sign-agnostic) FX rate —
                    # flip its sign to match the original tx.amount instead of re-querying.
                    signed_amt = amt if tx.amount >= 0 else -amt
                    R[bid] += signed_amt
                elif tx.type in (TransactionType.FEE, TransactionType.TAX):
                    R[bid] -= amt
                    if R[bid] < zero:
                        K[bid] += R[bid]
                        R[bid] = zero
                elif tx.type == TransactionType.BUY and tx.asset_id:
                    from_r = min(amt, max(R[bid], zero))
                    R[bid] -= from_r
                    K[bid] -= amt - from_r
                elif tx.type == TransactionType.SELL and tx.asset_id:
                    # Pre-frame sells: approximate all proceeds to K (WAC not tracked yet in pre-frame for sell cost basis)
                    K[bid] += amt
                elif tx.type in (TransactionType.CASH_TRANSFER, TransactionType.FX_CONVERSION):
                    # Linked-internal cash transfer: move pools from src to dst
                    if ctxn.classification == "linked_internal" and tx.amount < 0:
                        # Departure leg (negative amount = outflow)
                        from_r = min(amt, max(R[bid], zero))
                        R[bid] -= from_r
                        from_k = amt - from_r
                        K[bid] -= from_k
                        # Arrival leg will add these back to paired broker
                    elif ctxn.classification == "linked_internal" and tx.amount > 0:
                        # Arrival leg (positive amount = inflow)
                        # Approximate: add to K (can't track exact split without buffering)
                        K[bid] += amt
            # Replay the position txs against their average-cost steps
            day_pos_txs = position_txs_by_date.get(day)
            if day_pos_txs:
                additions = [c for c in day_pos_txs if c.tx.quantity and c.tx.quantity > 0]
                reductions = [c for c in day_pos_txs if c.tx.quantity and c.tx.quantity < 0]
                for ctxn in additions + reductions:
                    tx = ctxn.tx
                    key = (tx.asset_id, tx.broker_id)
                    tx_qty = tx.quantity * ctxn.share
                    cumulative_qty[key] += tx_qty
                    previous = cost_pool.get(key)
                    step = self._next_cost_step(key, tx, tx_qty)
                    if step is None:
                        continue
                    cost_pool[key] = step
                    if tx.id in self.split_linked_tx_ids:
                        continue
                    transfer_capital = self._transfer_leg_capital(ctxn, tx_qty)
                    if transfer_capital is not None:
                        cumulative_ecf += transfer_capital
                        cumulative_ecf_by_broker[tx.broker_id] += transfer_capital
                    if tx.quantity > 0:
                        if step.effect == CostEffect.ADD and self._is_capital_adjustment(tx):
                            cumulative_ecf += step.cost_report_change
                            cumulative_ecf_by_broker[tx.broker_id] += step.cost_report_change
                    else:
                        removed = -step.cost_report_change
                        if self._is_capital_adjustment(tx):
                            cumulative_ecf -= removed
                            cumulative_ecf_by_broker[tx.broker_id] -= removed
                        if tx.type == TransactionType.SELL:
                            realized_sales.append(self._realized_sale(ctxn, tx_qty, removed, previous))

        # ── 6. FRAME: [frame_start, date_to] — full daily evaluation ──
        # Build dirty_days for frame range only
        dirty_days: set[date_type] = set()
        for d in cash_deltas.keys():
            if d >= self.frame_start:
                dirty_days.add(d)
        for d in position_txs_by_date.keys():
            if d >= self.frame_start:
                dirty_days.add(d)
        for d in ecf_by_date.keys():
            if d >= self.frame_start:
                dirty_days.add(d)
        for d in internal_flow_dates:
            if d >= self.frame_start:
                dirty_days.add(d)
        # A rate change of a held foreign currency revalues its cash
        frame_fx_days = set(self.native_cash.rate_change_days(self.frame_start, self.date_to))
        dirty_days.update(frame_fx_days)
        # ...and a rate the day reads for its securities or its cash in transit changes their value
        dirty_days.update(self._valuation_rate_change_days())
        for interval in self.in_transit_intervals:
            if interval.start_date >= self.frame_start:
                dirty_days.add(interval.start_date)
            if interval.end_date >= self.frame_start:
                dirty_days.add(interval.end_date)
            if interval.end_date < self.date_to and interval.end_date + timedelta(days=1) >= self.frame_start:
                dirty_days.add(interval.end_date + timedelta(days=1))
        # A market quote sets the day's mark even with the previous close: the mark may have come from a trade, and
        # a new quote restarts the price's age
        for prices in self.price_map.values():
            dirty_days.update(dt for dt, _close, _currency in prices if self.frame_start <= dt <= self.date_to)
        # A carried price turns stale on the day its age passes the threshold, with nothing else happening
        observed = {dt for prices in self.price_map.values() for dt, _close, _currency in prices} | set(position_txs_by_date)
        for day in observed:
            first_stale = day + timedelta(days=STALE_PRICE_THRESHOLD_DAYS + 1)
            if self.frame_start <= first_stale <= self.date_to:
                dirty_days.add(first_stale)
        for history in self.split_history.values():
            dirty_days.update(split.date for split in history if self.frame_start <= split.date <= self.date_to)
        dirty_days.add(self.frame_start)

        current = self.frame_start
        while current <= self.date_to:
            # Day skipping: if this day is stationary (no tx, ecf, price change, or
            # in-transit boundary), reuse the previous state with updated date.
            if current not in dirty_days and states:
                prev = states[-1]
                states.append(
                    DailyPortfolioState(
                        date=current,
                        cash_value=prev.cash_value,
                        market_value=prev.market_value,
                        broker_nav_value=prev.broker_nav_value,
                        in_transit_cash_value=prev.in_transit_cash_value,
                        in_transit_asset_market_value=prev.in_transit_asset_market_value,
                        in_transit_market_value=prev.in_transit_market_value,
                        nav_value=prev.nav_value,
                        open_cost_basis=prev.open_cost_basis,
                        in_transit_asset_cost_basis=prev.in_transit_asset_cost_basis,
                        in_transit_book_value=prev.in_transit_book_value,
                        book_value=prev.book_value,
                        unrealized_gain_loss=prev.unrealized_gain_loss,
                        external_cash_flow=zero,
                        cumulative_external_cash_flow=prev.cumulative_external_cash_flow,
                        book_asset_like=prev.book_asset_like,
                        cash_from_contributed_capital=prev.cash_from_contributed_capital,
                        cash_from_generated_returns=prev.cash_from_generated_returns,
                        total_pnl=prev.total_pnl,
                        by_type=dict(prev.by_type),
                        by_sector=dict(prev.by_sector),
                        by_geography=dict(prev.by_geography),
                        missing_price_asset_ids=set(prev.missing_price_asset_ids),
                        missing_fx_pairs=set(prev.missing_fx_pairs),
                        stale_price_asset_ids=set(prev.stale_price_asset_ids),
                        transaction_implied_asset_ids=set(prev.transaction_implied_asset_ids),
                        transaction_implied_last_quote_dates=dict(prev.transaction_implied_last_quote_dates),
                        nav_complete=prev.nav_complete,
                        broker_contributions=dict(prev.broker_contributions),
                        pnl_candle=prev.pnl_candle,
                        acquisition_funding=None,
                        unrealized_by_currency=dict(prev.unrealized_by_currency),
                    )
                )
                current += timedelta(days=1)
                continue

            # 4a. Update cash
            cumulative_cash += cash_deltas.get(current, zero)
            for bid in all_broker_ids:
                cumulative_cash_by_broker[bid] += cash_deltas_by_broker.get((current, bid), zero)
            # Exchange result on foreign cash: after the day's cash, before its pool rules
            if current in frame_fx_days:
                for exchange_result in self._revalue_foreign_cash(current, cumulative_cash_by_broker, K, R):
                    cumulative_cash += exchange_result

            # Batch 2 — per-day BUY funding split accumulator (see
            # AcquisitionFundingContribution), reset every day like external_cash_flow.
            day_acq_from_k = zero
            day_acq_from_r = zero

            # 4b. Unified per-transaction loop: cost pool + 3-pool
            # Single pass: for each tx, in additions-first order:
            #   1. Replay the position's next average-cost step (BUY adds, SELL removes cost)
            #   2. Update 3-pool (K, R) with the historical cost a reduction gave up
            # Period flows by type and position come from the native cash, sales from realized_sales.
            ecf_today = ecf_by_date.get(current, zero)
            cumulative_ecf += ecf_today
            for bid in all_broker_ids:
                cumulative_ecf_by_broker[bid] += ecf_by_date_by_broker.get((current, bid), zero)

            day_all_txs = all_txs_by_date.get(current, [])
            # Sort: additions (qty > 0) first, then reductions (qty < 0), then non-position txs
            day_additions = [c for c in day_all_txs if c.tx.quantity and c.tx.quantity > 0 and c.tx.asset_id]
            day_reductions = [c for c in day_all_txs if c.tx.quantity and c.tx.quantity < 0 and c.tx.asset_id]
            day_non_position = [c for c in day_all_txs if not (c.tx.quantity and c.tx.quantity != 0 and c.tx.asset_id)]

            for ctxn in day_additions + day_reductions + day_non_position:
                tx = ctxn.tx
                bid = tx.broker_id
                key = (tx.asset_id, tx.broker_id) if tx.asset_id else None
                tx_qty = (tx.quantity * ctxn.share) if tx.quantity else zero

                # ── Convert amount to target currency ──
                amount_target: Decimal | None = None
                if tx.amount and tx.amount != 0 and tx.currency:
                    amount_target = self._convert_movement(abs(tx.amount), tx.currency, tx.date)
                    if amount_target is not None:
                        amount_target = amount_target * ctxn.share

                # ── Position tx: replay its average-cost step ──
                if tx.quantity and tx.quantity != 0 and tx.asset_id and key:
                    cumulative_qty[key] += tx_qty
                    previous = cost_pool.get(key)
                    step = self._next_cost_step(key, tx, tx_qty)
                    if step is not None:
                        cost_pool[key] = step
                    if tx.id in self.split_linked_tx_ids:
                        continue  # split never touches cash/K/R/realized accounting
                    # Lot 41 (D2/D5): a TRANSFER leg with no internal partner is in-kind
                    # capital at market value. Not in ecf_today: the daily
                    # external_cash_flow stays cash-only, as for the in-kind ADJUSTMENT.
                    transfer_capital = self._transfer_leg_capital(ctxn, tx_qty)
                    if transfer_capital is not None:
                        cumulative_ecf += transfer_capital
                        cumulative_ecf_by_broker[bid] += transfer_capital
                    if tx.quantity > 0:
                        # In-kind ADJUSTMENT-in (priced, no cash): capital contribution.
                        # Add the cost it brings into the pool to the capital baseline so total
                        # P&L excludes it (opening equity, not profit). See _is_capital_adjustment.
                        if step is not None and step.effect == CostEffect.ADD and self._is_capital_adjustment(tx):
                            cumulative_ecf += step.cost_report_change
                            cumulative_ecf_by_broker[bid] += step.cost_report_change
                    else:
                        # Reduction: the historical cost the pool gave up, in target currency
                        sell_cb_target = -step.cost_report_change if step is not None else zero
                        if tx.type == TransactionType.SELL:
                            realized_sales.append(self._realized_sale(ctxn, tx_qty, sell_cb_target, previous))

                        # In-kind ADJUSTMENT-out (no cash proceeds): capital distribution.
                        # Remove the cost from the capital baseline (mirror of the in-kind
                        # contribution on ADJUSTMENT-in) so total P&L keeps tracking
                        # unrealized instead of dumping the book into "Other".
                        if self._is_capital_adjustment(tx):
                            cumulative_ecf -= sell_cb_target
                            cumulative_ecf_by_broker[bid] -= sell_cb_target

                        # 3-pool per-broker: SELL → K[bid] += cost_basis, R[bid] += gain
                        if amount_target is not None:
                            gain = amount_target - sell_cb_target
                            K[bid] += sell_cb_target
                            R[bid] += gain
                            if R[bid] < zero:
                                K[bid] += R[bid]
                                R[bid] = zero

                        continue  # skip the generic 3-pool rules below

                # ── 3-pool per-broker for non-SELL txs ──
                if amount_target is None:
                    continue

                bid = tx.broker_id

                if tx.type == TransactionType.DEPOSIT:
                    restore = min(amount_target, W)
                    R[bid] += restore
                    W -= restore
                    K[bid] += amount_target - restore

                elif tx.type == TransactionType.WITHDRAWAL:
                    from_k = min(amount_target, max(K[bid], zero))
                    K[bid] -= from_k
                    remaining = amount_target - from_k
                    from_r = min(remaining, max(R[bid], zero))
                    R[bid] -= from_r
                    W += from_r

                elif tx.type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
                    # Signed: preserve a legacy negative correction (plan §4.4). `amount_target`
                    # is abs(tx.amount) converted through the same (sign-agnostic) FX rate —
                    # flip its sign to match the original tx.amount instead of re-querying.
                    signed_amount_target = amount_target if tx.amount >= 0 else -amount_target
                    R[bid] += signed_amount_target

                elif tx.type in (TransactionType.FEE, TransactionType.TAX):
                    R[bid] -= amount_target
                    if R[bid] < zero:
                        K[bid] += R[bid]
                        R[bid] = zero

                elif tx.type == TransactionType.BUY and tx.asset_id:
                    from_r = min(amount_target, max(R[bid], zero))
                    R[bid] -= from_r
                    K[bid] -= amount_target - from_r
                    if self.compute_acquisition_funding:
                        day_acq_from_r += from_r
                        day_acq_from_k += amount_target - from_r

                elif tx.type in (TransactionType.CASH_TRANSFER, TransactionType.FX_CONVERSION):
                    # Linked-internal: pool transfer between brokers
                    if ctxn.classification == "linked_internal" and tx.amount < 0:
                        # Departure leg: R exits first, then K
                        from_r = min(amount_target, max(R[bid], zero))
                        R[bid] -= from_r
                        from_k = amount_target - from_r
                        K[bid] -= from_k
                    elif ctxn.classification == "linked_internal" and tx.amount > 0:
                        # Arrival leg: receives from paired broker
                        # Approximate: proportional to departure (use K as default)
                        K[bid] += amount_target

            # 4c. Market value per asset (after all txs for the day are processed)
            market_value = zero
            market_value_by_broker: dict[int, Decimal] = defaultdict(lambda: zero)
            by_type: dict[str, Decimal] = defaultdict(lambda: zero)
            by_sector: dict[str, Decimal] = defaultdict(lambda: zero)
            by_geo: dict[str, Decimal] = defaultdict(lambda: zero)
            missing: set[int] = set()
            stale: set[int] = set()
            missing_fx: set[str] = set()
            implied: set[int] = set()
            implied_last_quotes: dict[int, date_type | None] = {}
            # G1b — synthetic P&L candles (plan §4.3): sum every held asset's resolved daily OHLC
            # contribution (flat open=high=low=close=market_value when no intraday range is known,
            # never a guess). A MISSING valuation makes the whole day's candle unavailable, mirroring
            # nav_complete — a resolved contribution cannot be composed from an unresolved one.
            candle_open_sum = zero
            candle_high_sum = zero
            candle_low_sum = zero
            candle_close_sum = zero
            # Open cost basis: historical cost of the held quantity, already in target currency
            open_cost_basis = zero
            unrealized_parts: dict[str, list[Decimal]] = {}

            for (asset_id, position_broker_id), qty in cumulative_qty.items():
                if qty <= 0:
                    continue
                valuation = self._market_value_for(asset_id, qty, current, compute_ohlc=self.compute_candles)
                if valuation.market_value is not None:
                    market_value += valuation.market_value
                    market_value_by_broker[position_broker_id] += valuation.market_value
                    self._distribute_allocation(asset_id, valuation.market_value, by_type, by_sector, by_geo)
                    if self.compute_candles:
                        has_ohlc = valuation.market_value_open is not None and valuation.market_value_high is not None and valuation.market_value_low is not None
                        candle_open_sum += valuation.market_value_open if has_ohlc else valuation.market_value
                        candle_high_sum += valuation.market_value_high if has_ohlc else valuation.market_value
                        candle_low_sum += valuation.market_value_low if has_ohlc else valuation.market_value
                        candle_close_sum += valuation.market_value
                if valuation.source == ValuationSource.MISSING:
                    missing.add(asset_id)
                if valuation.stale:
                    stale.add(asset_id)
                if valuation.missing_fx_pair:
                    missing_fx.add(valuation.missing_fx_pair)
                if valuation.source == ValuationSource.LAST_TRADE_PRICE:
                    implied.add(asset_id)
                    series = self.mark_series.get(asset_id)
                    implied_last_quotes[asset_id] = series.last_market_date(current) if series is not None else None
                position_cost = cost_pool.get((asset_id, position_broker_id))
                position_cost_report = position_cost.cost_report_for(qty) if position_cost is not None else zero
                open_cost_basis += position_cost_report
                self._add_unrealized_part(unrealized_parts, asset_id, qty, valuation.market_value, position_cost_report, position_cost, current)

            # 4d. In-transit values. `it_by_broker` is attributed to each interval's
            # departure-broker (cash+asset market value only — additive NAV
            # component, not the cost-basis breakdown), per plan §3.2: value stays
            # with the departure broker for the whole transit window.
            it_by_broker: dict[int, Decimal] = defaultdict(lambda: zero)
            it_cash, it_asset_mv, it_asset_cb = self._compute_in_transit(current, missing_fx, it_by_broker)

            # 4f. Compose
            broker_nav = market_value + cumulative_cash
            in_transit_mv = it_cash + it_asset_mv
            nav = broker_nav + in_transit_mv
            in_transit_bv = it_cash + it_asset_cb
            book = open_cost_basis + cumulative_cash + in_transit_bv
            ug = nav - book

            # 4f2. G1a — additive per-broker NAV/capital/P&L contribution. Built from
            # exactly the same Decimal components summed above (market value, cash,
            # in-transit, external capital flow), plus the step-3b internal flows, which
            # cancel out across brokers every day (lot 41), so
            #   sum(nav_contribution) == nav
            #   sum(capital_contribution) == capital_baseline
            #   sum(pnl_contribution) == total_pnl
            # hold by construction — never a residual/plug line.
            broker_contributions: dict[int, BrokerDailyContribution] = {}
            for bid in all_broker_ids:
                broker_in_transit_contribution = it_by_broker.get(bid, zero)
                broker_nav_contribution = market_value_by_broker.get(bid, zero) + cumulative_cash_by_broker.get(bid, zero) + broker_in_transit_contribution
                broker_capital_contribution = cumulative_ecf_by_broker.get(bid, zero)
                broker_contributions[bid] = BrokerDailyContribution(
                    broker_id=bid,
                    nav_contribution=broker_nav_contribution,
                    capital_contribution=broker_capital_contribution,
                    pnl_contribution=broker_nav_contribution - broker_capital_contribution,
                    in_transit_contribution=broker_in_transit_contribution,
                )

            # 4g. Clamp pools per-broker (rounding safety)
            for bid in list(K.keys()):
                K[bid] = max(K[bid], zero)
            for bid in list(R.keys()):
                R[bid] = max(R[bid], zero)

            # Derive final display values (aggregated across brokers)
            capital_cash_pool_total = sum(K.values())
            returns_cash_pool_total = sum(R.values())
            book_asset_like = open_cost_basis + it_asset_cb
            cash_like = cumulative_cash + it_cash
            pool_sum = capital_cash_pool_total + returns_cash_pool_total
            if pool_sum > zero and abs(pool_sum - cash_like) > Decimal("0.01"):
                scale = cash_like / pool_sum
                cash_from_contributed = max(capital_cash_pool_total * scale, zero)
                cash_from_generated = max(cash_like - cash_from_contributed, zero)
            else:
                cash_from_contributed = min(capital_cash_pool_total, cash_like)
                cash_from_generated = max(cash_like - cash_from_contributed, zero)

            # capital_baseline includes in-kind ADJUSTMENT capital routed into
            # cumulative_ecf inside the per-transaction loop above, so re-read it here.
            capital_baseline = cumulative_ecf
            total_pnl = nav - capital_baseline

            # 4f3. G1b — synthetic P&L candle (plan §4.3). offset absorbs every non-
            # per-asset-OHLC contribution (cash, capital baseline, realized/income,
            # in-transit, flat fallback) so close = total_pnl exactly, by construction.
            # Unavailable (None) when candles weren't requested or a held asset's
            # valuation is MISSING that day (mirrors nav_complete: a resolved
            # contribution cannot be composed from an unresolved one).
            pnl_candle: PnlCandleContribution | None = None
            if self.compute_candles and len(missing) == 0:
                candle_offset = total_pnl - candle_close_sum
                pnl_candle = PnlCandleContribution(
                    open=candle_offset + candle_open_sum,
                    high=candle_offset + candle_high_sum,
                    low=candle_offset + candle_low_sum,
                    close=total_pnl,
                )

            # Batch 2 — new-vs-reinvested BUY funding split (see
            # AcquisitionFundingContribution). None when not requested or no BUY
            # happened today (a genuine gap, not a zero-valued contribution).
            acquisition_funding: AcquisitionFundingContribution | None = None
            if self.compute_acquisition_funding and (day_acq_from_k != zero or day_acq_from_r != zero):
                acquisition_funding = AcquisitionFundingContribution(
                    from_new_capital=day_acq_from_k,
                    from_reinvested=day_acq_from_r,
                )

            # 4b2. Position state snapshots (start of frame + every day end)
            if is_first_frame_day:
                for (aid, bid), qty in cumulative_qty.items():
                    if qty <= 0:
                        continue
                    ps = self._build_position_state(aid, bid, qty, current, cost_pool)
                    position_states_start.append(ps)
                is_first_frame_day = False

            # 4h. Allocation: cash as Liquidity (type + sector, not geography)
            by_type["Liquidity"] = by_type.get("Liquidity", zero) + cumulative_cash + it_cash
            by_sector["Liquidity"] = by_sector.get("Liquidity", zero) + cumulative_cash + it_cash

            states.append(
                DailyPortfolioState(
                    date=current,
                    cash_value=cumulative_cash,
                    market_value=market_value,
                    broker_nav_value=broker_nav,
                    in_transit_cash_value=it_cash,
                    in_transit_asset_market_value=it_asset_mv,
                    in_transit_market_value=in_transit_mv,
                    nav_value=nav,
                    open_cost_basis=open_cost_basis,
                    in_transit_asset_cost_basis=it_asset_cb,
                    in_transit_book_value=in_transit_bv,
                    book_value=book,
                    unrealized_gain_loss=ug,
                    external_cash_flow=ecf_today,
                    cumulative_external_cash_flow=cumulative_ecf,
                    book_asset_like=book_asset_like,
                    cash_from_contributed_capital=cash_from_contributed,
                    cash_from_generated_returns=cash_from_generated,
                    total_pnl=total_pnl,
                    by_type=dict(by_type),
                    by_sector=dict(by_sector),
                    by_geography=dict(by_geo),
                    missing_price_asset_ids=missing,
                    missing_fx_pairs=missing_fx,
                    stale_price_asset_ids=stale,
                    transaction_implied_asset_ids=implied,
                    transaction_implied_last_quote_dates=implied_last_quotes,
                    nav_complete=len(missing) == 0,
                    broker_contributions=broker_contributions,
                    pnl_candle=pnl_candle,
                    acquisition_funding=acquisition_funding,
                    unrealized_by_currency={currency: UnrealizedSplit(asset=part[0], fx=part[1], unsplit=part[2]) for currency, part in unrealized_parts.items()},
                )
            )
            current += timedelta(days=1)

        # End-of-frame position snapshot (t1)
        for (aid, bid), qty in cumulative_qty.items():
            if qty <= 0:
                continue
            ps = self._build_position_state(aid, bid, qty, self.date_to, cost_pool)
            position_states_end.append(ps)

        return PortfolioCalculationResult(
            daily_states=states,
            position_states_start=position_states_start,
            position_states_end=position_states_end,
            native_cash=self.native_cash,
            end_state=EngineEndState(
                cumulative_cash=cumulative_cash,
                cumulative_ecf=cumulative_ecf,
                cumulative_qty=dict(cumulative_qty),
                wac_pool_qty={key: step.quantity for key, step in cost_pool.items()},
                wac_pool_cost={key: step.cost_report for key, step in cost_pool.items()},
                capital_pool=dict(K),
                returns_pool=dict(R),
                withdrawn_pool=W,
                cumulative_cash_by_broker=dict(cumulative_cash_by_broker),
                cumulative_ecf_by_broker=dict(cumulative_ecf_by_broker),
            ),
            scope_broker_ids=list({ctxn.tx.broker_id for ctxn in self.classified_txs}),
            target_currency=self.target_currency,
            date_from=self.date_from,
            date_to=self.date_to,
            average_costs=dict(self.average_costs),
            realized_sales=realized_sales,
            missing_fx={pair: set(dates) for pair, dates in self._missing_fx.items()},
        )

    # ── Helper methods ──

    def _build_position_state(
        self,
        asset_id: int,
        broker_id: int,
        qty: Decimal,
        dt: date_type,
        cost_pool: dict[tuple[int, int], CostStep],
    ) -> DailyPositionState:
        """Build a DailyPositionState for one position at a given date."""
        zero = Decimal("0")
        asset_currency = self.asset_currencies.get(asset_id, self.target_currency)
        position_cost = cost_pool.get((asset_id, broker_id))
        if position_cost is None:
            cost_basis = zero
            cost_complete = True
            wac_val: Decimal | None = zero
            wac_asset: Decimal | None = zero
        else:
            cost_basis = position_cost.cost_report_for(qty)
            cost_complete = position_cost.report_complete
            wac_val = position_cost.unit_cost_report if cost_complete else None
            wac_asset = position_cost.unit_cost_asset if position_cost.asset_complete else None

        valuation = self._market_value_for(asset_id, qty, dt)
        unrealized = (valuation.market_value - cost_basis) if valuation.market_value is not None and cost_complete else None

        return DailyPositionState(
            date=dt,
            broker_id=broker_id,
            asset_id=asset_id,
            quantity=qty,
            valuation_effective_unit_price=valuation.effective_unit_price,
            valuation_effective_currency=valuation.effective_currency,
            valuation_reference_date=valuation.reference_date,
            valuation_reference_unit_price=valuation.reference_unit_price,
            valuation_reference_currency=valuation.reference_currency,
            valuation_source=valuation.source,
            valuation_split_adjusted=valuation.split_adjusted,
            valuation_stale=valuation.stale,
            missing_fx_pair=valuation.missing_fx_pair,
            market_value=valuation.market_value,
            wac=wac_val,
            wac_currency=self.target_currency,
            cost_basis=cost_basis,
            unrealized_pnl=unrealized,
            asset_currency=asset_currency,
            wac_asset=wac_asset,
            cost_complete=cost_complete,
        )

    def _next_cost_step(self, key: tuple[int, int], tx: Transaction, tx_qty: Decimal) -> CostStep | None:
        """The average-cost step of ``tx``: the next one of its position, in replay order.

        build_cost_positions() feeds compute_average_costs the same transactions, in the same
        order, that the replay visits; a mismatch is a bug, never data, so it raises.
        """
        if tx_qty == 0:
            return None  # an owner's 0% share moves nothing
        average_cost = self.average_costs.get(key)
        index = self._cost_cursor.get(key, 0)
        if average_cost is None or index >= len(average_cost.steps):
            raise RuntimeError(f"no average-cost step for transaction {tx.id} of position {key}")
        step = average_cost.steps[index]
        if step.movement.movement_id != tx.id or step.movement.date != tx.date:
            raise RuntimeError(f"average-cost steps out of replay order at transaction {tx.id} of position {key}")
        self._cost_cursor[key] = index + 1
        return step

    def _realized_sale(self, ctxn: ClassifiedTransaction, tx_qty: Decimal, cost: Decimal, previous: CostStep | None) -> RealizedSale:
        """A SELL with its proceeds converted at its date and the historical cost it took from the pool."""
        tx = ctxn.tx
        proceeds: Decimal | None = Decimal("0")
        if tx.amount:
            converted = self._convert_movement(abs(tx.amount), tx.currency or self.target_currency, tx.date)
            proceeds = converted * ctxn.share if converted is not None else None
        return RealizedSale(
            transaction_id=tx.id,
            asset_id=tx.asset_id,
            broker_id=tx.broker_id,
            date=tx.date,
            quantity=abs(tx_qty),
            proceeds=proceeds,
            cost=cost,
            cost_complete=previous.report_complete if previous is not None else True,
        )

    def _add_unrealized_part(
        self,
        parts: dict[str, list[Decimal]],
        asset_id: int,
        qty: Decimal,
        market_value: Decimal | None,
        cost_report: Decimal,
        position_cost: CostStep | None,
        day: date_type,
    ) -> None:
        """Add one position's MV − C_T to its asset currency's [asset, fx, unsplit] parts (see UnrealizedSplit)."""
        zero = Decimal("0")
        asset_currency = self.asset_currencies.get(asset_id, self.target_currency)
        part = parts.setdefault(asset_currency, [zero, zero, zero])
        value = market_value if market_value is not None else zero
        if asset_currency == self.target_currency:
            part[0] += value - cost_report
            return
        rate = self.fx_rate_map.get((asset_currency, self.target_currency, day))
        if position_cost is None:
            cost_asset: Decimal | None = zero
            complete = True
        else:
            cost_asset = position_cost.cost_asset_for(qty)
            complete = position_cost.report_complete and position_cost.asset_complete
        if market_value is None or rate is None or cost_asset is None or not complete:
            part[2] += value - cost_report
            return
        cost_at_today_rate = cost_asset * rate
        part[0] += market_value - cost_at_today_rate
        part[1] += cost_at_today_rate - cost_report

    def _read_rate(self, currency: str, day: date_type) -> Decimal | None:
        """The rate the day reads from the pre-loaded map: the exact day's, or None."""
        return self.fx_rate_map.get((currency, self.target_currency, day))

    def _valuation_rate_change_days(self) -> set[date_type]:
        """Frame days on which a rate the day reads to value it changes from the day before.

        The currencies of prices and assets are read every day (securities held and in transit, the exchange part
        of the unrealized result); the currency of cash in transit on the days of its transit. Same reading as the
        valuation: the exact day's rate, so one that appears or disappears counts.
        """
        changed: set[date_type] = set()
        currencies = {currency for prices in self.price_map.values() for _day, _close, currency in prices if currency}
        currencies.update(currency for currency in self.asset_currencies.values() if currency)
        currencies.discard(self.target_currency)
        if currencies:
            changed.update(day for day in change_days(self._read_rate, currencies, _calendar(self.frame_start - timedelta(days=1), self.date_to)) if day >= self.frame_start)
        for interval in self.in_transit_intervals:
            currency = interval.departure_leg.currency
            start, end = max(interval.start_date, self.frame_start), min(interval.end_date, self.date_to)
            if interval.tx_type != "cash" or not currency or currency == self.target_currency or start > end:
                continue
            changed.update(day for day in change_days(self._read_rate, {currency}, _calendar(start - timedelta(days=1), end)) if day >= start)
        return changed

    def _convert(self, amount: Decimal, from_ccy: str, dt: date_type) -> Decimal | None:
        """Convert amount from from_ccy to target_currency using pre-loaded FX map."""
        if from_ccy == self.target_currency:
            return amount
        rate = self.fx_rate_map.get((from_ccy, self.target_currency, dt))
        if rate is None:
            return None
        return amount * rate

    def _convert_movement(self, amount: Decimal, from_ccy: str, dt: date_type) -> Decimal | None:
        """Convert a movement's amount at its own date; a missing rate is recorded with that date."""
        converted = self._convert(amount, from_ccy, dt)
        if converted is None:
            self._missing_fx[f"{from_ccy}/{self.target_currency}"].add(dt)
        return converted

    def _revalue_foreign_cash(self, day: date_type, cash_by_broker: dict[int, Decimal], capital_pool: dict[int, Decimal], returns_pool: dict[int, Decimal]) -> list[Decimal]:
        """Revalue every broker's foreign cash at the rate of ``day``; return each exchange result booked.

        The replay holds each cash movement at the rate of its own date. The native cash holds
        the balances in their own currencies, valued at the rate of ``day``: the difference is
        the exchange result on cash. It goes to the broker's cash and returns pool; a loss larger
        than the returns comes out of capital, as a FEE does. The capital baseline never moves:
        an exchange result is a result, not a contribution.
        """
        zero = Decimal("0")
        values = self.native_cash.value_at(day)
        booked: list[Decimal] = []
        for broker_id in sorted(self.native_cash.foreign_cash_broker_ids):
            value = values.get(broker_id)
            if value is None:
                continue
            exchange_result = value - cash_by_broker.get(broker_id, zero)
            if exchange_result == 0:
                continue
            cash_by_broker[broker_id] = cash_by_broker.get(broker_id, zero) + exchange_result
            returns_pool[broker_id] = returns_pool.get(broker_id, zero) + exchange_result
            if returns_pool[broker_id] < zero:
                capital_pool[broker_id] = capital_pool.get(broker_id, zero) + returns_pool[broker_id]
                returns_pool[broker_id] = zero
            booked.append(exchange_result)
        return booked

    def _market_value_for(
        self,
        asset_id: int,
        qty: Decimal,
        dt: date_type,
        *,
        compute_ohlc: bool = False,
    ) -> ValuationResult:
        """Value one holding via the unified price resolver — the single valuation brain.

        ``mark_series`` holds a per-asset :class:`AssetPriceSeries` fed with *both* asset-system
        quotes and observed trades in the asset's *native* currency, so a single ``resolve(dt)``
        answers the whole valuation at once: a real quote (exact or carried forward) →
        ``MARKET_PRICE``; a trade-derived mark (BUY/SELL/priced ADJUSTMENT, same-day average, LOCF
        with staleness) → ``LAST_TRADE_PRICE``. The mark is converted to the reporting currency
        **here**, at the valuation date ``dt`` (never at the observation date), so a carried mark
        tracks the current FX rather than a frozen one. When the resolver has no observation on/before
        ``dt`` the holding is ``MISSING`` (no legacy price-map / last-buy / last-seed cascade — those
        tiers are subsumed by the resolver's trade observations).

        ``compute_ohlc`` (G1b, default False — stays off the ordinary hot path per plan §4.1's
        "expensive OHLC work stays off ordinary reports") additionally resolves
        ``market_value_open/high/low`` through the exact same conversion as ``market_value``,
        when the mark carries a same-day OHLC triple (never for CARRIED/TRADE_AVG/MISSING).
        """
        mark_series = self.mark_series.get(asset_id)
        if mark_series is not None:
            mark = mark_series.resolve(dt)
            if not mark.is_missing:
                quote_base = self.quote_base_map.get(asset_id)
                days_back = mark.price_backward_fill.days_back if mark.price_backward_fill else 0
                native_ref = mark.unit_price  # native currency, pre-split, par-axis scale
                native_ccy = mark.currency or self.target_currency
                if mark.estimated:
                    # Trade-derived mark: restate the observed unit price to current units through any
                    # intervening splits (real asset-system quotes already sit on the current-unit axis).
                    split_ratio, split_adjusted = _cumulative_split_ratio(self.split_history.get(asset_id, ()), mark.as_of_date, dt)
                    native_effective = native_ref / split_ratio
                    # Trade observations were lifted onto the market ×quote_base_quantity axis at
                    # ingestion (price_marks), so ``native_ref`` is on that axis. Restate the
                    # *reference* unit price back to the source per-unit axis so it reports the price
                    # as it appeared in the trade record. ``effective_unit_price`` stays on the market
                    # axis (it is the price actually fed to ``compute_holding_value``). Market quotes
                    # already report on their native per-unit axis and need no restatement.
                    scale = Decimal(quote_base if quote_base and quote_base > 0 else 1)
                    display_ref = native_ref / scale
                    source = ValuationSource.LAST_TRADE_PRICE
                else:
                    native_effective = native_ref
                    split_adjusted = False
                    display_ref = native_ref
                    source = ValuationSource.MARKET_PRICE
                holding_value = compute_holding_value(qty, native_effective, quote_base)
                # G1b: OHLC is only ever present on a mark.estimated=False exact MARKET day (see
                # price_marks — CARRIED/TRADE_AVG always report None), so it never needs the
                # split-restatement above (real quotes already sit on the current-unit axis).
                holding_open = holding_high = holding_low = None
                if compute_ohlc and mark.open is not None and mark.high is not None and mark.low is not None:
                    holding_open = compute_holding_value(qty, mark.open, quote_base)
                    holding_high = compute_holding_value(qty, mark.high, quote_base)
                    holding_low = compute_holding_value(qty, mark.low, quote_base)
                is_stale = days_back > STALE_PRICE_THRESHOLD_DAYS
                if native_ccy == self.target_currency:
                    return ValuationResult(
                        market_value=holding_value,
                        source=source,
                        effective_unit_price=native_effective,
                        effective_currency=native_ccy,
                        reference_date=mark.as_of_date,
                        reference_unit_price=display_ref,
                        reference_currency=native_ccy,
                        stale=is_stale,
                        split_adjusted=split_adjusted,
                        market_value_open=holding_open,
                        market_value_high=holding_high,
                        market_value_low=holding_low,
                    )
                # Foreign mark: convert to the reporting currency at the *valuation date* dt (never at
                # the observation date) so a carried mark tracks the current FX, not a frozen one.
                rate = self.fx_rate_map.get((native_ccy, self.target_currency, dt))
                return ValuationResult(
                    market_value=holding_value * rate if rate is not None else None,
                    source=source,
                    effective_unit_price=native_effective,
                    effective_currency=native_ccy,
                    reference_date=mark.as_of_date,
                    reference_unit_price=display_ref,
                    reference_currency=native_ccy,
                    stale=is_stale,
                    split_adjusted=split_adjusted,
                    missing_fx_pair=f"{native_ccy}/{self.target_currency}" if rate is None else None,
                    market_value_open=holding_open * rate if (rate is not None and holding_open is not None) else None,
                    market_value_high=holding_high * rate if (rate is not None and holding_high is not None) else None,
                    market_value_low=holding_low * rate if (rate is not None and holding_low is not None) else None,
                )

        return ValuationResult(
            market_value=None,
            source=ValuationSource.MISSING,
            effective_unit_price=None,
            effective_currency=None,
            reference_date=None,
            reference_unit_price=None,
            reference_currency=None,
        )

    def _compute_in_transit(self, dt: date_type, missing_fx: set[str], it_by_broker: dict[int, Decimal] | None = None) -> tuple[Decimal, Decimal, Decimal]:  # noqa: C901 — TODO(P2-refactor): nested per-interval valuation with FX/cost fallbacks
        """Compute in_transit_cash, in_transit_asset_mv, in_transit_asset_cb.

        `it_by_broker`, if given, is mutated in place with each interval's NAV
        contribution (cash + asset market value, no cost basis) attributed to
        the departure broker — the broker whose portfolio the in-transit value
        stays with for the whole transit window (plan §3.2).
        """
        zero = Decimal("0")
        it_cash = zero
        it_asset_mv = zero
        it_asset_cb = zero

        for interval in self.in_transit_intervals:
            if not (interval.start_date <= dt <= interval.end_date):
                continue

            if interval.tx_type == "cash":
                dep = interval.departure_leg
                cash_amount = abs(dep.amount) if dep.amount else zero
                if dep.currency:
                    converted = self._convert(cash_amount, dep.currency, dt)
                    if converted is not None:
                        contribution = converted * interval.share
                        it_cash += contribution
                        if it_by_broker is not None:
                            it_by_broker[dep.broker_id] += contribution
                    else:
                        missing_fx.add(f"{dep.currency}/{self.target_currency}")
            else:
                # Frozen cost is per unit. Convert total cost once, then use it as a
                # valuation only when neither a market price nor a visible BUY exists.
                authoritative_cost_value: Decimal | None = None
                if interval.asset_id is not None:
                    dep = interval.departure_leg
                    qty = abs(dep.quantity) if dep.quantity else zero
                    if qty > 0:
                        has_authoritative_cost = interval.cost_basis_amount is not None and interval.cost_basis_currency is not None
                        if has_authoritative_cost:
                            # Historical cost: converted at the arrival date, as the destination
                            # pool books it, not re-converted every day of the transit.
                            authoritative_cost_value = self._convert_movement(interval.cost_basis_amount * qty, interval.cost_basis_currency, interval.arrival_leg.date)
                            if authoritative_cost_value is not None:
                                it_asset_cb += authoritative_cost_value * interval.share

                        valuation = self._market_value_for(interval.asset_id, qty, dt)
                        if valuation.market_value is not None:
                            contribution = valuation.market_value * interval.share
                            it_asset_mv += contribution
                            if it_by_broker is not None:
                                it_by_broker[dep.broker_id] += contribution
                        elif valuation.source == ValuationSource.MISSING and authoritative_cost_value is not None:
                            contribution = authoritative_cost_value * interval.share
                            it_asset_mv += contribution
                            if it_by_broker is not None:
                                it_by_broker[dep.broker_id] += contribution
                        if valuation.missing_fx_pair:
                            missing_fx.add(valuation.missing_fx_pair)

        return it_cash, it_asset_mv, it_asset_cb

    def _is_capital_adjustment(self, tx: Transaction) -> bool:
        """True when a transaction is a priced in-kind ADJUSTMENT (a capital event).

        An opening / transfer / succession ADJUSTMENT that carries a per-unit
        ``cost_basis_override`` injects (qty>0) or removes (qty<0) real book value
        WITHOUT any cash counterpart. Economically this is a capital contribution /
        distribution in kind (opening equity), NOT profit — so its cost must move the
        capital baseline (``cumulative_ecf``), leaving total P&L = NAV − capital to
        reflect only genuine market / realized / income effects. Without this the
        injected book value leaks into the "Other / reconciliation residual".

        SPLIT-linked adjustments are excluded: a split redistributes existing cost
        over a new quantity, it neither adds nor removes economic capital.
        """
        return tx.type == TransactionType.ADJUSTMENT and tx.cost_basis_override is not None and tx.quantity is not None and tx.quantity != 0 and (tx.id is None or tx.id not in self.split_linked_tx_ids)

    def _internal_transfer_flows(self) -> list[tuple[date_type, int, int, Decimal]]:
        """Lot 41 — the capital flows of the internal pairs between two brokers (step 3b).

        One ``(arrival_date, sender_broker_id, receiver_broker_id, value)`` for each
        linked-internal CASH_TRANSFER / FX_CONVERSION / TRANSFER pair whose two legs sit on
        different brokers. The sender is the leg going out (negative amount for cash, negative
        quantity for securities), the receiver the leg coming in; the arrival date is the later
        leg's date. Pairs without exactly one of each, same-broker pairs and ADJUSTMENT pairs
        give no flow.

        ``value`` is what the arrival brings into the receiver's NAV, valued on the arrival
        date as the NAV values it — the received amount converted at that date, or the market
        value of the received quantity — at the sender's share, like the value in transit.
        A value that cannot be computed (MISSING mark, missing FX rate) gives no flow, which is
        what the arrival adds to the NAV.

        Pure: it records no missing data, so a build with this method returning ``[]`` differs
        only in the per-broker capital.
        """
        zero = Decimal("0")
        ctxn_by_id = {ctxn.tx.id: ctxn for ctxn in self.classified_txs if ctxn.tx.id is not None}
        seen_pairs: set[tuple[int, int]] = set()
        flows: list[tuple[date_type, int, int, Decimal]] = []
        for ctxn in self.classified_txs:
            tx = ctxn.tx
            if ctxn.classification != "linked_internal" or ctxn.paired_tx is None or tx.id is None or tx.type not in _LINKED_TYPES:
                continue
            partner = ctxn_by_id.get(ctxn.paired_tx.id)
            if partner is None or partner.classification != "linked_internal" or partner.tx.type != tx.type:
                continue
            pair_key = (min(tx.id, partner.tx.id), max(tx.id, partner.tx.id))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            if tx.broker_id is None or partner.tx.broker_id is None or tx.broker_id == partner.tx.broker_id:
                continue  # a same-broker pair never leaves the broker's line
            is_cash = tx.type in _CASH_LINKED_TYPES
            legs = (ctxn, partner)
            directions = [(leg.tx.amount if is_cash else leg.tx.quantity) or zero for leg in legs]
            senders = [leg for leg, direction in zip(legs, directions, strict=True) if direction < 0]
            receivers = [leg for leg, direction in zip(legs, directions, strict=True) if direction > 0]
            if len(senders) != 1 or len(receivers) != 1:
                logger.debug("Internal pair without one sender and one receiver: no broker flow", pair=pair_key)
                continue
            sender, receiver = senders[0], receivers[0]
            arrival = max(sender.tx.date, receiver.tx.date)
            received = receiver.tx
            if is_cash:
                value = self._convert(abs(received.amount), received.currency, arrival) if received.currency else None
            else:
                value = self._market_value_for(received.asset_id, abs(received.quantity), arrival).market_value if received.asset_id is not None else None
            if value is None:
                continue
            flow_value = value * sender.share
            if flow_value != zero:
                flows.append((arrival, sender.tx.broker_id, received.broker_id, flow_value))
        return flows

    def _transfer_leg_capital(self, ctxn: ClassifiedTransaction, tx_qty: Decimal) -> Decimal | None:
        """Lot 41 (D2/D5) — in-kind capital of a TRANSFER leg that forms no internal pair.

        A TRANSFER whose other leg is outside the scope (linked_external_*), missing, or never
        linked (an orphan) moves securities across the scope boundary without cash: capital,
        not profit. It counts at market value on its own date, for ``tx_qty`` (already at the
        broker's share): positive for securities received, negative for securities sent.
        None for any other row, for an internal-pair leg (step 3b handles it), for a
        split-linked row, or when the security cannot be valued that day.
        """
        tx = ctxn.tx
        if tx.type != TransactionType.TRANSFER or tx.asset_id is None or tx_qty == 0:
            return None
        if ctxn.classification == "linked_internal" or (tx.id is not None and tx.id in self.split_linked_tx_ids):
            return None
        market_value = self._market_value_for(tx.asset_id, abs(tx_qty), tx.date).market_value
        if market_value is None:
            return None
        return market_value if tx_qty > 0 else -market_value

    def _distribute_allocation(
        self,
        asset_id: int,
        mv: Decimal,
        by_type: dict[str, Decimal],
        by_sector: dict[str, Decimal],
        by_geo: dict[str, Decimal],
    ) -> None:
        """Distribute market value into allocation buckets."""
        asset_type = self.asset_types.get(asset_id, "Unknown")
        by_type[asset_type] = by_type.get(asset_type, Decimal("0")) + mv

        cp = self.asset_classifications.get(asset_id)
        if cp and isinstance(cp, dict):
            sector_area = cp.get("sector_area")
            if sector_area and isinstance(sector_area, dict):
                dist = sector_area.get("distribution", {})
                if dist:
                    for sector, weight in dist.items():
                        by_sector[sector] = by_sector.get(sector, Decimal("0")) + mv * Decimal(str(weight))
                else:
                    by_sector["Unknown"] = by_sector.get("Unknown", Decimal("0")) + mv
            else:
                by_sector["Unknown"] = by_sector.get("Unknown", Decimal("0")) + mv

            geo_area = cp.get("geographic_area")
            if geo_area and isinstance(geo_area, dict):
                dist = geo_area.get("distribution", {})
                if dist:
                    for country, weight in dist.items():
                        # "Other" is a provider placeholder for "rest of world" — merge into Unknown
                        bucket = "Unknown" if country == "Other" else country
                        by_geo[bucket] = by_geo.get(bucket, Decimal("0")) + mv * Decimal(str(weight))
                else:
                    by_geo["Unknown"] = by_geo.get("Unknown", Decimal("0")) + mv
            else:
                by_geo["Unknown"] = by_geo.get("Unknown", Decimal("0")) + mv
        else:
            by_sector["Unknown"] = by_sector.get("Unknown", Decimal("0")) + mv
            by_geo["Unknown"] = by_geo.get("Unknown", Decimal("0")) + mv
