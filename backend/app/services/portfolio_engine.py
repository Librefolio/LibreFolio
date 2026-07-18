"""
Portfolio Calculation Engine for LibreFolio.

Replaces the scattered logic in PortfolioService.get_summary() / get_history()
with a single engine that produces a DailyPortfolioState[] vector from which
all views (summary, history, allocation, performance) are derived.

Architecture:
1. ScopeAwareTransactionClassifier — classifies txs as internal/external
2. DailyStateBuilder — pure function, no I/O, builds daily state vector
3. DerivedViewsBuilder — derives summary/history/allocation/performance views
4. PortfolioCalculationEngine — async orchestrator, loads data and calls 1-3
"""

from __future__ import annotations

import bisect
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Literal, Optional

import structlog
from sqlalchemy import func, select

from backend.app.db.models import Asset, AssetEvent, AssetEventType, BrokerUserAccess, PriceHistory, Transaction, TransactionType
from backend.app.schemas.common import Currency as CurrencySchema
from backend.app.schemas.portfolio import (
    DataQualityIssue,
    DataQualityReport,
    IssueCode,
    IssueDomain,
    IssueSeverity,
)
from backend.app.services.fx import convert_bulk
from backend.app.services.settings_service import get_global_setting
from backend.app.utils.cache_utils import get_ttl_cache
from backend.app.utils.financial.roi_utils import CashFlowInput, NAVSnapshot
from backend.app.utils.financial.valuation_utils import compute_holding_value

logger = structlog.get_logger(__name__)

# Portfolio engine blob cache: stores PortfolioCalculationResult keyed by
# (user, brokers, currency, fingerprints). Range-aware: can be sliced or extended.
_portfolio_blob_cache = get_ttl_cache("portfolio_blob", maxsize=30, ttl=86400)  # 24h

# Transaction types that are always external cash flows when unlinked
_EXTERNAL_CASH_TYPES = {TransactionType.DEPOSIT, TransactionType.WITHDRAWAL}

# Emoji mapping for sector allocation keys (backend-canonical, language-independent)
SECTOR_EMOJIS: dict[str, str] = {
    "Technology": "💻",
    "Financials": "🏦",
    "Consumer Discretionary": "🛍️",
    "Health Care": "💊",
    "Industrials": "🏭",
    "Basic Materials": "⛏️",
    "Energy": "⚡",
    "Consumer Staples": "🛒",
    "Telecommunication": "📡",
    "Real Estate": "🏢",
    "Utilities": "🔌",
    "Other": "📦",
    "Unknown": "❓",
    "Liquidity": "💵",
}

# Linked transaction types (require or support related_transaction_id)
_LINKED_TYPES = {
    TransactionType.TRANSFER,
    TransactionType.CASH_TRANSFER,
    TransactionType.FX_CONVERSION,
}

# Types where linked pairs move cash between brokers
_CASH_LINKED_TYPES = {TransactionType.CASH_TRANSFER, TransactionType.FX_CONVERSION}

# Types where linked pairs move assets between brokers
_ASSET_LINKED_TYPES = {TransactionType.TRANSFER}


# =============================================================================
# DATACLASSES — Internal runtime objects (not API DTOs)
# =============================================================================


ClassificationType = Literal[
    "normal",
    "linked_internal",
    "linked_external_inflow",
    "linked_external_outflow",
    "ignored",
]


@dataclass
class ClassifiedTransaction:
    """Transaction classified by the ScopeAwareTransactionClassifier."""

    tx: Transaction
    classification: ClassificationType
    paired_tx: Optional[Transaction] = None
    share: Decimal = Decimal("1")


@dataclass
class InTransitInterval:
    """In-transit window for an internal linked pair with different dates.

    Window is [start_date, end_date] inclusive, representing the half-open
    convention [min(departure_date, arrival_date), max(departure_date, arrival_date))
    from plan v2 §7.2:
        start_date = min(departure_date, arrival_date)       # = departure_date (dep <= arr by construction)
        end_date   = max(departure_date, arrival_date) - 1   # last day still "in transit"
    The departure date itself is included (value leaves the source broker and
    enters transit on the same day — no value-hole), the arrival date itself is
    excluded (destination custody begins on arrival day, no double-count).
    If start_date > end_date the interval is empty (same-day transfer only).
    """

    start_date: date_type  # min(departure_date, arrival_date) == departure_date
    end_date: date_type  # max(departure_date, arrival_date) - 1
    tx_type: Literal["cash", "asset"]
    departure_leg: Transaction
    arrival_leg: Transaction
    share: Decimal
    # For asset transfers:
    asset_id: Optional[int] = None
    cost_basis_amount: Optional[Decimal] = None  # cbo or WAC fallback
    cost_basis_currency: Optional[str] = None


@dataclass
class ClassificationResult:
    """Output of ScopeAwareTransactionClassifier.classify()."""

    classified: list[ClassifiedTransaction] = field(default_factory=list)
    in_transit_intervals: list[InTransitInterval] = field(default_factory=list)
    external_cash_flows: list[tuple[date_type, Decimal, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def get_needed_paired_ids(self) -> set[int]:
        """IDs of linked txs whose pair is not in the scope transaction set."""
        return self._needed_paired_ids

    _needed_paired_ids: set[int] = field(default_factory=set, repr=False)


# =============================================================================
# SCOPE-AWARE TRANSACTION CLASSIFIER
# =============================================================================


class ScopeAwareTransactionClassifier:
    """Classifies transactions as internal/external relative to a broker scope.

    Pure logic — no I/O.  The caller must pre-load:
      - all_transactions: every tx belonging to scope brokers
      - external_paired: paired txs outside scope (loaded after get_needed_paired_ids)
      - broker_shares: broker_id → share_percentage
    """

    def __init__(
        self,
        scope_broker_ids: set[int],
        all_transactions: list[Transaction],
        broker_shares: dict[int, Decimal],
    ) -> None:
        self.scope_broker_ids = scope_broker_ids
        self.all_transactions = all_transactions
        self.broker_shares = broker_shares

    def get_needed_paired_ids(self) -> set[int]:
        """Return IDs of related txs that are NOT in the scope transaction set.

        The caller should load these from DB and pass them to classify().
        """
        tx_ids = {tx.id for tx in self.all_transactions if tx.id is not None}
        needed: set[int] = set()
        for tx in self.all_transactions:
            if tx.related_transaction_id is not None and tx.related_transaction_id not in tx_ids:
                needed.add(tx.related_transaction_id)
        return needed

    def classify(
        self,
        external_paired: dict[int, Transaction] | None = None,
    ) -> ClassificationResult:
        """Classify all transactions.

        Args:
            external_paired: paired transactions outside the broker scope,
                             keyed by their transaction ID.
        """
        if external_paired is None:
            external_paired = {}

        tx_by_id: dict[int, Transaction] = {}
        for tx in self.all_transactions:
            if tx.id is not None:
                tx_by_id[tx.id] = tx

        classified: list[ClassifiedTransaction] = []
        in_transit_intervals: list[InTransitInterval] = []
        external_cash_flows: list[tuple[date_type, Decimal, str]] = []
        warnings: list[str] = []

        # Track which linked pairs we've already processed (avoid duplicates)
        processed_pairs: set[tuple[int, int]] = set()

        for tx in self.all_transactions:
            share = self.broker_shares.get(tx.broker_id, Decimal("1"))

            # ── UNLINKED transaction ──
            if tx.related_transaction_id is None:
                ctxn = ClassifiedTransaction(tx=tx, classification="normal", share=share)
                classified.append(ctxn)

                # Unlinked DEPOSIT/WITHDRAWAL → external cash flow
                if tx.type in _EXTERNAL_CASH_TYPES and tx.amount and tx.amount != 0 and tx.currency:
                    external_cash_flows.append((tx.date, tx.amount * share, tx.currency))
                continue

            # ── LINKED transaction — find paired leg ──
            paired = tx_by_id.get(tx.related_transaction_id) or external_paired.get(tx.related_transaction_id)

            if paired is None:
                # Paired tx not found → treat as normal with warning
                ctxn = ClassifiedTransaction(tx=tx, classification="normal", share=share)
                classified.append(ctxn)
                warnings.append(f"Transaction {tx.id} ({tx.type}) has related_transaction_id={tx.related_transaction_id} " f"but paired transaction not found — treating as normal")
                # If it looks like a deposit/withdrawal, count as external
                if tx.amount and tx.amount != 0 and tx.currency:
                    external_cash_flows.append((tx.date, tx.amount * share, tx.currency))
                continue

            pair_key = (min(tx.id or 0, paired.id or 0), max(tx.id or 0, paired.id or 0))
            is_paired_in_scope = paired.broker_id in self.scope_broker_ids

            if is_paired_in_scope:
                # ── LINKED INTERNAL — both legs in scope ──
                ctxn = ClassifiedTransaction(tx=tx, classification="linked_internal", paired_tx=paired, share=share)
                classified.append(ctxn)

                # In-transit: only create once per pair, only if dates differ
                if pair_key not in processed_pairs and tx.date != paired.date:
                    interval = self._build_in_transit_interval(tx, paired)
                    if interval is not None:
                        in_transit_intervals.append(interval)

                    # Warn if share percentages differ between source/dest brokers
                    paired_share = self.broker_shares.get(paired.broker_id, Decimal("1"))
                    if share != paired_share:
                        warnings.append(f"Linked internal pair ({tx.id}, {paired.id}): share mismatch " f"broker {tx.broker_id}={share} vs broker {paired.broker_id}={paired_share}")
            else:
                # ── LINKED EXTERNAL — only this leg in scope ──
                # Determine if this leg is inflow or outflow based on amount/quantity sign
                classification = self._classify_external_leg(tx)
                ctxn = ClassifiedTransaction(tx=tx, classification=classification, paired_tx=paired, share=share)
                classified.append(ctxn)

                # External linked → generates external cash flow
                if tx.amount and tx.amount != 0 and tx.currency:
                    external_cash_flows.append((tx.date, tx.amount * share, tx.currency))

            processed_pairs.add(pair_key)

        result = ClassificationResult(
            classified=classified,
            in_transit_intervals=in_transit_intervals,
            external_cash_flows=external_cash_flows,
            warnings=warnings,
        )
        return result

    @staticmethod
    def _classify_external_leg(tx: Transaction) -> ClassificationType:
        """Determine if an external linked leg is inflow or outflow."""
        # For cash-based linked types: amount sign determines direction
        if tx.amount and tx.amount > 0:
            return "linked_external_inflow"
        if tx.amount and tx.amount < 0:
            return "linked_external_outflow"
        # For asset transfers: quantity sign determines direction
        if tx.quantity and tx.quantity > 0:
            return "linked_external_inflow"
        if tx.quantity and tx.quantity < 0:
            return "linked_external_outflow"
        return "linked_external_inflow"  # fallback

    @staticmethod
    def _build_in_transit_interval(tx_a: Transaction, tx_b: Transaction) -> InTransitInterval | None:
        """Build an InTransitInterval for a linked internal pair with different dates.

        Departure = earlier date leg, arrival = later date leg.
        Window = [departure_date, arrival_date - 1] inclusive — i.e. the half-open
        [min(dep,arr), max(dep,arr)) convention from plan v2 §7.2. The departure
        date is included (fixes the value-hole where the source broker already
        shows qty=0 but the old dep+1 window hadn't started yet); the arrival
        date is excluded (destination custody starts there, no double-count).
        Returns None only for a same-day transfer (no transit period at all).
        """
        if tx_a.date <= tx_b.date:
            departure, arrival = tx_a, tx_b
        else:
            departure, arrival = tx_b, tx_a

        start = departure.date
        end = arrival.date - timedelta(days=1)

        if start > end:
            return None  # Same-day transfer — no transit window

        # Determine type: cash or asset
        if departure.type in _ASSET_LINKED_TYPES or arrival.type in _ASSET_LINKED_TYPES:
            tx_type: Literal["cash", "asset"] = "asset"
            asset_id = departure.asset_id or arrival.asset_id
            # Cost basis: prefer departure leg's cost_basis_override
            cbo = departure.cost_basis_override or arrival.cost_basis_override
            cbc = departure.cost_basis_currency or arrival.cost_basis_currency
        else:
            tx_type = "cash"
            asset_id = None
            cbo = None
            cbc = None

        # Use departure leg's share
        share = Decimal("1")  # Will be overridden by caller

        return InTransitInterval(
            start_date=start,
            end_date=end,
            tx_type=tx_type,
            departure_leg=departure,
            arrival_leg=arrival,
            share=share,
            asset_id=asset_id,
            cost_basis_amount=cbo,
            cost_basis_currency=cbc,
        )


# =============================================================================
# DAILY PORTFOLIO STATE — Core daily snapshot
# =============================================================================

STALE_PRICE_THRESHOLD_DAYS = 7

# Grace period after first acquisition during which a missing market price is
# considered a normal pre-listing/placement lag (e.g. BTP collocamento) rather
# than a data-quality problem worth flagging (TRANSACTION_IMPLIED issue).
TRANSACTION_IMPLIED_GRACE_DAYS = 14


@dataclass
class DailyPositionState:
    """Per-position daily state — the atomic building block of portfolio computation.

    One instance per (broker_id, asset_id) per day with qty > 0.
    Portfolio-level DailyPortfolioState is aggregated from these.
    """

    date: date_type
    broker_id: int
    asset_id: int
    quantity: Decimal
    valuation_price: Decimal | None
    valuation_price_ccy: str | None
    valuation_source: str  # "MARKET_PRICE", "LAST_BUY_PRICE", "MISSING"
    market_value: Decimal | None  # in target_currency
    wac: Decimal  # in asset_currency
    wac_currency: str
    cost_basis: Decimal  # in target_currency (wac * qty * fx)
    unrealized_pnl: Decimal | None  # market_value - cost_basis (None if MV missing)


@dataclass
class DailyPortfolioState:
    """Complete daily portfolio state — the heart of the calculation engine."""

    date: date_type
    # Valuation
    cash_value: Decimal
    market_value: Decimal
    broker_nav_value: Decimal
    in_transit_cash_value: Decimal
    in_transit_asset_market_value: Decimal
    in_transit_market_value: Decimal
    nav_value: Decimal
    # Accounting
    open_cost_basis: Decimal
    in_transit_asset_cost_basis: Decimal
    in_transit_book_value: Decimal
    book_value: Decimal
    unrealized_gain_loss: Decimal
    # Performance inputs
    external_cash_flow: Decimal
    cumulative_external_cash_flow: Decimal  # Running total of deposits - withdrawals (net invested capital)
    # Cash decomposition (Capital Baseline narrative: P&L = NAV - capital_baseline)
    # capital_baseline = cumulative_external_cash_flow (alias, same value)
    book_asset_like: Decimal  # open_cost_basis + in_transit_asset_cost_basis
    cash_from_contributed_capital: Decimal  # min(cash_like, max(capital_baseline - book_asset_like, 0))
    cash_from_generated_returns: Decimal  # cash_like - cash_from_contributed_capital
    total_pnl: Decimal  # nav_value - capital_baseline
    # Allocation
    by_type: dict[str, Decimal] = field(default_factory=dict)
    by_sector: dict[str, Decimal] = field(default_factory=dict)
    by_geography: dict[str, Decimal] = field(default_factory=dict)
    # Data quality
    missing_price_asset_ids: set[int] = field(default_factory=set)
    missing_fx_pairs: set[str] = field(default_factory=set)
    stale_price_asset_ids: set[int] = field(default_factory=set)
    transaction_implied_asset_ids: set[int] = field(default_factory=set)
    nav_complete: bool = True


# =============================================================================
# DAILY STATE BUILDER — Pure function, no I/O
# =============================================================================


class DailyStateBuilder:
    """Builds a dense DailyPortfolioState[] vector for every calendar day.

    Pure function — no I/O, no DB, no async. All data is pre-loaded.

    WAC is computed inline during the daily loop (no external wac_series needed).
    Each position's (asset_id, broker_id) WAC pool is maintained in its native
    asset_currency, then converted to target_currency at evaluation time.
    """

    def __init__(
        self,
        *,
        classified_txs: list[ClassifiedTransaction],
        in_transit_intervals: list[InTransitInterval],
        external_cash_flows: list[tuple[date_type, Decimal, str]],
        price_map: dict[int, list[tuple[date_type, Decimal, str]]],
        quote_base_map: dict[int, int | None],
        fx_rate_map: dict[tuple[str, str, date_type], Decimal],
        asset_classifications: dict[int, dict | None],
        asset_types: dict[int, str],
        asset_currencies: dict[int, str],
        target_currency: str,
        date_from: date_type,
        date_to: date_type,
        frame_start: date_type | None = None,
        last_buy_prices: dict[int, tuple[date_type, Decimal, str]] | None = None,
        split_linked_tx_ids: set[int] | None = None,
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
        self.target_currency = target_currency
        self.date_from = date_from
        self.date_to = date_to
        # Transaction ids for ADJUSTMENT rows linked to an AssetEvent of type SPLIT.
        # These bypass the normal add/reduce WAC pool math (see _apply_wac_pool_update):
        # a split redistributes existing cost over a new quantity, it never adds or
        # removes economic cost. Populated by PortfolioCalculationEngine.run().
        self.split_linked_tx_ids: set[int] = split_linked_tx_ids or set()
        # frame_start: first day to emit DailyPortfolioState. Before this = pre-frame (accounting only).
        # None → same as date_from (no pre-frame, full evaluation from start).
        self.frame_start = frame_start if frame_start is not None else date_from
        # last_buy_prices: asset_id → (date, unit_price, currency) from V(u) BUY txs
        self.last_buy_prices: dict[int, tuple[date_type, Decimal, str]] = last_buy_prices or {}

    def build(self) -> PortfolioCalculationResult:
        """Build daily states for [frame_start, date_to] + position snapshots + period accumulators.

        Architecture (pre-frame / frame split):
        - Pre-frame [date_from, frame_start): update accumulators only (cash, qty, WAC, pools).
          No market evaluation, no FX lookups for prices, no state emission.
        - Frame [frame_start, date_to]: full daily evaluation + DailyPortfolioState emission.
        """
        zero = Decimal("0")

        # ── 1. Cash ledger: sum amount deltas per day ──
        cash_deltas: dict[date_type, Decimal] = defaultdict(lambda: zero)
        for ctxn in self.classified_txs:
            tx = ctxn.tx
            if tx.amount and tx.amount != 0 and tx.currency:
                converted = self._convert(tx.amount, tx.currency, tx.date)
                if converted is not None:
                    cash_deltas[tx.date] += converted * ctxn.share

        # ── 2. Position transactions by date (for inline WAC computation) ──
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
        for dt, amount, ccy in self.external_cash_flows:
            converted = self._convert(amount, ccy, dt)
            if converted is not None:
                ecf_by_date[dt] += converted

        # ── 4. Accumulators (shared across pre-frame and frame) ──
        states: list[DailyPortfolioState] = []
        cumulative_cash = zero
        cumulative_ecf = zero
        cumulative_qty: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)
        wac_pool_qty: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)
        wac_pool_cost: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)
        # 3-pool: per-broker K and R, global W
        K: dict[int, Decimal] = defaultdict(lambda: zero)  # capital pool per broker
        R: dict[int, Decimal] = defaultdict(lambda: zero)  # returns pool per broker
        W: Decimal = zero  # withdrawn returns (global, exits system)
        # Period accumulators for contribution (only frame txs counted)
        per_realized: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)
        per_income: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)
        per_fees_taxes: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)
        unalloc_income: dict[int, Decimal] = defaultdict(lambda: zero)
        unalloc_fees: dict[int, Decimal] = defaultdict(lambda: zero)
        # Position state snapshots
        position_states_start: list[DailyPositionState] = []
        position_states_end: list[DailyPositionState] = []
        is_first_frame_day = True

        # ── 5. PRE-FRAME: [date_from, frame_start) — accounting only ──
        # Process all transaction days before frame_start: update cash, qty, WAC, ECF.
        # No market evaluation, no DailyPortfolioState emission.
        preframe_tx_dates = sorted(
            d for d in (set(cash_deltas.keys()) | set(position_txs_by_date.keys()) | set(ecf_by_date.keys()))
            if d < self.frame_start
        )
        for day in preframe_tx_dates:
            cumulative_cash += cash_deltas.get(day, zero)
            cumulative_ecf += ecf_by_date.get(day, zero)
            # Pre-frame 3-pool per-broker: process all tx types
            for ctxn in all_txs_by_date.get(day, []):
                tx = ctxn.tx
                bid = tx.broker_id
                if tx.amount is None or tx.amount == 0 or tx.currency is None:
                    continue
                amt = self._convert(abs(tx.amount), tx.currency, tx.date)
                if amt is None:
                    continue
                amt = amt * ctxn.share
                if tx.type == TransactionType.DEPOSIT:
                    restore = min(amt, W)
                    R[bid] += restore
                    W -= restore
                    K[bid] += (amt - restore)
                elif tx.type == TransactionType.WITHDRAWAL:
                    from_k = min(amt, max(K[bid], zero))
                    K[bid] -= from_k
                    remaining = amt - from_k
                    from_r = min(remaining, max(R[bid], zero))
                    R[bid] -= from_r
                    W += from_r
                elif tx.type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
                    R[bid] += amt
                elif tx.type in (TransactionType.FEE, TransactionType.TAX):
                    R[bid] -= amt
                    if R[bid] < zero:
                        K[bid] += R[bid]
                        R[bid] = zero
                elif tx.type == TransactionType.BUY and tx.asset_id:
                    from_r = min(amt, max(R[bid], zero))
                    R[bid] -= from_r
                    K[bid] -= (amt - from_r)
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
            # Update WAC pools for position txs
            day_pos_txs = position_txs_by_date.get(day)
            if day_pos_txs:
                additions = [c for c in day_pos_txs if c.tx.quantity and c.tx.quantity > 0]
                reductions = [c for c in day_pos_txs if c.tx.quantity and c.tx.quantity < 0]
                for ctxn in additions + reductions:
                    tx = ctxn.tx
                    key = (tx.asset_id, tx.broker_id)
                    tx_qty = tx.quantity * ctxn.share
                    if tx.id in self.split_linked_tx_ids:
                        self._apply_split_rescale(key, tx_qty, wac_pool_qty, wac_pool_cost, zero)
                        cumulative_qty[key] += tx_qty
                        continue
                    if tx.quantity > 0:
                        unit_cost_asset_ccy = self._buy_unit_cost(tx)
                        if unit_cost_asset_ccy is not None:
                            old_qty = wac_pool_qty[key]
                            old_cost = wac_pool_cost[key]
                            new_qty = old_qty + tx_qty
                            if new_qty > zero:
                                wac_pool_cost[key] = old_cost + unit_cost_asset_ccy * tx_qty
                                wac_pool_qty[key] = new_qty
                            else:
                                wac_pool_qty[key] = zero
                                wac_pool_cost[key] = zero
                        else:
                            old_qty = wac_pool_qty[key]
                            new_qty = old_qty + tx_qty
                            if old_qty > zero:
                                current_wac = wac_pool_cost[key] / old_qty
                                wac_pool_cost[key] += current_wac * tx_qty
                            wac_pool_qty[key] = max(new_qty, zero)
                    else:
                        old_qty = wac_pool_qty[key]
                        if old_qty > zero:
                            current_wac = wac_pool_cost[key] / old_qty
                            wac_pool_qty[key] = max(old_qty + tx_qty, zero)
                            wac_pool_cost[key] = wac_pool_qty[key] * current_wac
                        else:
                            wac_pool_qty[key] = zero
                            wac_pool_cost[key] = zero
                    cumulative_qty[key] += tx_qty

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
        for interval in self.in_transit_intervals:
            if interval.start_date >= self.frame_start:
                dirty_days.add(interval.start_date)
            if interval.end_date >= self.frame_start:
                dirty_days.add(interval.end_date)
            if interval.end_date < self.date_to and interval.end_date + timedelta(days=1) >= self.frame_start:
                dirty_days.add(interval.end_date + timedelta(days=1))
        for prices in self.price_map.values():
            prev_price = None
            for dt, close, _ in prices:
                if dt < self.frame_start:
                    prev_price = close
                    continue
                if prev_price is not None and close != prev_price:
                    dirty_days.add(dt)
                elif prev_price is None:
                    dirty_days.add(dt)
                prev_price = close
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
                        nav_complete=prev.nav_complete,
                    )
                )
                current += timedelta(days=1)
                continue

            # 4a. Update cash
            cumulative_cash += cash_deltas.get(current, zero)

            # 4b. Unified per-transaction loop: WAC + 3-pool + period accumulators
            # Single pass: for each tx, in additions-first order:
            #   1. Read current WAC (before mutation)
            #   2. Update WAC pool (BUY adds, SELL reduces)
            #   3. Update 3-pool (K, R) using the captured WAC
            #   4. Update period accumulators (realized, income, fees)
            ecf_today = ecf_by_date.get(current, zero)
            cumulative_ecf += ecf_today
            capital_baseline = cumulative_ecf

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
                    amount_target = self._convert(abs(tx.amount), tx.currency, tx.date)
                    if amount_target is not None:
                        amount_target = amount_target * ctxn.share

                # ── Position tx: WAC pool update ──
                if tx.quantity and tx.quantity != 0 and tx.asset_id and key:
                    if tx.id in self.split_linked_tx_ids:
                        self._apply_split_rescale(key, tx_qty, wac_pool_qty, wac_pool_cost, zero)
                        cumulative_qty[key] += tx_qty
                        continue  # split never touches cash/K/R/realized accounting
                    if tx.quantity > 0:
                        # Acquisition: update WAC pool
                        unit_cost_asset_ccy = self._buy_unit_cost(tx)
                        if unit_cost_asset_ccy is not None:
                            old_qty = wac_pool_qty[key]
                            old_cost = wac_pool_cost[key]
                            new_qty = old_qty + tx_qty
                            if new_qty > zero:
                                wac_pool_cost[key] = old_cost + unit_cost_asset_ccy * tx_qty
                                wac_pool_qty[key] = new_qty
                            else:
                                wac_pool_qty[key] = zero
                                wac_pool_cost[key] = zero
                        else:
                            old_qty = wac_pool_qty[key]
                            new_qty = old_qty + tx_qty
                            if old_qty > zero:
                                cur_wac = wac_pool_cost[key] / old_qty
                                wac_pool_cost[key] += cur_wac * tx_qty
                            wac_pool_qty[key] = max(new_qty, zero)
                        cumulative_qty[key] += tx_qty
                    else:
                        # Reduction: READ WAC before reducing, then reduce
                        old_qty = wac_pool_qty[key]
                        sell_qty_abs = abs(tx_qty)
                        if old_qty > zero:
                            cur_wac = wac_pool_cost[key] / old_qty
                            # Cost basis in target currency (captured before reduction)
                            cb_local = cur_wac * sell_qty_abs
                            wac_ccy = self.asset_currencies.get(tx.asset_id, self.target_currency)
                            if wac_ccy == self.target_currency:
                                sell_cb_target = cb_local
                            else:
                                rate = self.fx_rate_map.get((wac_ccy, self.target_currency, current))
                                sell_cb_target = cb_local * rate if rate else cb_local
                            # Now reduce pool
                            wac_pool_qty[key] = max(old_qty + tx_qty, zero)
                            wac_pool_cost[key] = wac_pool_qty[key] * cur_wac
                        else:
                            sell_cb_target = zero
                            wac_pool_qty[key] = zero
                            wac_pool_cost[key] = zero
                        cumulative_qty[key] += tx_qty

                        # 3-pool per-broker: SELL → K[bid] += cost_basis, R[bid] += gain
                        if amount_target is not None:
                            gain = amount_target - sell_cb_target
                            K[bid] += sell_cb_target
                            R[bid] += gain
                            if R[bid] < zero:
                                K[bid] += R[bid]
                                R[bid] = zero

                        # Period accumulator: realized gain/loss
                        if amount_target is not None:
                            per_realized[key] += amount_target - sell_cb_target
                        continue  # skip generic 3-pool/accumulator below

                # ── 3-pool per-broker + period accumulators for non-SELL txs ──
                if amount_target is None:
                    continue

                bid = tx.broker_id

                if tx.type == TransactionType.DEPOSIT:
                    restore = min(amount_target, W)
                    R[bid] += restore
                    W -= restore
                    K[bid] += (amount_target - restore)

                elif tx.type == TransactionType.WITHDRAWAL:
                    from_k = min(amount_target, max(K[bid], zero))
                    K[bid] -= from_k
                    remaining = amount_target - from_k
                    from_r = min(remaining, max(R[bid], zero))
                    R[bid] -= from_r
                    W += from_r

                elif tx.type in (TransactionType.DIVIDEND, TransactionType.INTEREST):
                    R[bid] += amount_target
                    # Period accumulator
                    if tx.asset_id:
                        per_income[(tx.asset_id, tx.broker_id)] += amount_target
                    else:
                        unalloc_income[tx.broker_id] += amount_target

                elif tx.type in (TransactionType.FEE, TransactionType.TAX):
                    R[bid] -= amount_target
                    if R[bid] < zero:
                        K[bid] += R[bid]
                        R[bid] = zero
                    # Period accumulator
                    if tx.asset_id:
                        per_fees_taxes[(tx.asset_id, tx.broker_id)] += amount_target
                    else:
                        unalloc_fees[tx.broker_id] += amount_target

                elif tx.type == TransactionType.BUY and tx.asset_id:
                    from_r = min(amount_target, max(R[bid], zero))
                    R[bid] -= from_r
                    K[bid] -= (amount_target - from_r)

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
            by_type: dict[str, Decimal] = defaultdict(lambda: zero)
            by_sector: dict[str, Decimal] = defaultdict(lambda: zero)
            by_geo: dict[str, Decimal] = defaultdict(lambda: zero)
            missing: set[int] = set()
            stale: set[int] = set()
            missing_fx: set[str] = set()
            implied: set[int] = set()

            for (asset_id, _broker_id), qty in cumulative_qty.items():
                if qty <= 0:
                    continue
                mv, price_found, is_stale, fx_missing, is_implied = self._market_value_for(
                    asset_id, qty, current, wac_pool_qty, wac_pool_cost, _broker_id
                )
                if mv is not None:
                    market_value += mv
                    self._distribute_allocation(asset_id, mv, by_type, by_sector, by_geo)
                if not price_found and not is_implied:
                    missing.add(asset_id)
                if is_stale:
                    stale.add(asset_id)
                if fx_missing:
                    missing_fx.add(fx_missing)
                if is_implied:
                    implied.add(asset_id)

            # 4d. In-transit values
            it_cash, it_asset_mv, it_asset_cb = self._compute_in_transit(current, missing_fx)

            # 4e. Open cost basis from inline WAC pool
            open_cost_basis = self._compute_open_cost_basis_inline(
                cumulative_qty, wac_pool_qty, wac_pool_cost, current, missing_fx
            )

            # 4f. Compose
            broker_nav = market_value + cumulative_cash
            in_transit_mv = it_cash + it_asset_mv
            nav = broker_nav + in_transit_mv
            in_transit_bv = it_cash + it_asset_cb
            book = open_cost_basis + cumulative_cash + in_transit_bv
            ug = nav - book

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

            total_pnl = nav - capital_baseline

            # 4b2. Position state snapshots (start of frame + every day end)
            if is_first_frame_day:
                for (aid, bid), qty in cumulative_qty.items():
                    if qty <= 0:
                        continue
                    ps = self._build_position_state(aid, bid, qty, current, wac_pool_qty, wac_pool_cost)
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
                    nav_complete=len(missing) == 0,
                )
            )
            current += timedelta(days=1)

        # End-of-frame position snapshot (t1)
        for (aid, bid), qty in cumulative_qty.items():
            if qty <= 0:
                continue
            ps = self._build_position_state(aid, bid, qty, self.date_to, wac_pool_qty, wac_pool_cost)
            position_states_end.append(ps)

        return PortfolioCalculationResult(
            daily_states=states,
            position_states_start=position_states_start,
            position_states_end=position_states_end,
            per_realized=dict(per_realized),
            per_income=dict(per_income),
            per_fees_taxes=dict(per_fees_taxes),
            unalloc_income=dict(unalloc_income),
            unalloc_fees=dict(unalloc_fees),
            end_state=EngineEndState(
                cumulative_cash=cumulative_cash,
                cumulative_ecf=cumulative_ecf,
                cumulative_qty=dict(cumulative_qty),
                wac_pool_qty=dict(wac_pool_qty),
                wac_pool_cost=dict(wac_pool_cost),
                capital_pool=dict(K),
                returns_pool=dict(R),
                withdrawn_pool=W,
            ),
            scope_broker_ids=list(set(ctxn.tx.broker_id for ctxn in self.classified_txs)),
            target_currency=self.target_currency,
            date_from=self.date_from,
            date_to=self.date_to,
        )

    # ── Helper methods ──

    def _build_position_state(
        self,
        asset_id: int,
        broker_id: int,
        qty: Decimal,
        dt: date_type,
        wac_pool_qty: dict[tuple[int, int], Decimal],
        wac_pool_cost: dict[tuple[int, int], Decimal],
    ) -> DailyPositionState:
        """Build a DailyPositionState for one position at a given date."""
        zero = Decimal("0")
        key = (asset_id, broker_id)
        pool_q = wac_pool_qty.get(key, zero)
        wac_val = (wac_pool_cost.get(key, zero) / pool_q) if pool_q > 0 else zero
        wac_ccy = self.asset_currencies.get(asset_id, self.target_currency)

        # Cost basis in target currency
        ocb_local = wac_val * qty
        if wac_ccy == self.target_currency:
            cost_basis = ocb_local
        else:
            rate = self.fx_rate_map.get((wac_ccy, self.target_currency, dt))
            cost_basis = ocb_local * rate if rate else ocb_local

        # Market value + valuation source
        mv, price_found, _, _, is_lbp = self._market_value_for(
            asset_id, qty, dt, wac_pool_qty, wac_pool_cost, broker_id
        )
        if price_found:
            source = "MARKET_PRICE"
        elif is_lbp:
            source = "LAST_BUY_PRICE"
        else:
            source = "MISSING"

        unrealized = (mv - cost_basis) if mv is not None else None

        # Get valuation price/ccy
        prices = self.price_map.get(asset_id)
        price_result = self._price_on_date(prices, dt) if prices else None
        if price_result:
            val_price, val_ccy, _ = price_result
        elif is_lbp and asset_id in self.last_buy_prices:
            _, val_price, val_ccy = self.last_buy_prices[asset_id]
        else:
            val_price, val_ccy = None, None

        return DailyPositionState(
            date=dt,
            broker_id=broker_id,
            asset_id=asset_id,
            quantity=qty,
            valuation_price=val_price,
            valuation_price_ccy=val_ccy,
            valuation_source=source,
            market_value=mv,
            wac=wac_val,
            wac_currency=wac_ccy,
            cost_basis=cost_basis,
            unrealized_pnl=unrealized,
        )

    def _convert(self, amount: Decimal, from_ccy: str, dt: date_type) -> Decimal | None:
        """Convert amount from from_ccy to target_currency using pre-loaded FX map."""
        if from_ccy == self.target_currency:
            return amount
        rate = self.fx_rate_map.get((from_ccy, self.target_currency, dt))
        if rate is None:
            return None
        return amount * rate

    def _price_on_date(
        self,
        sorted_prices: list[tuple[date_type, Decimal, str]],
        query_date: date_type,
    ) -> tuple[Decimal, str, date_type] | None:
        """Backward-fill: latest (close, currency, actual_date) with date <= query_date."""
        if not sorted_prices:
            return None
        dates = [p[0] for p in sorted_prices]
        idx = bisect.bisect_right(dates, query_date) - 1
        if idx < 0:
            return None
        actual_date, close, ccy = sorted_prices[idx]
        return close, ccy, actual_date

    def _market_value_for(
        self,
        asset_id: int,
        qty: Decimal,
        dt: date_type,
        wac_pool_qty: dict[tuple[int, int], Decimal] | None = None,
        wac_pool_cost: dict[tuple[int, int], Decimal] | None = None,
        broker_id: int | None = None,
    ) -> tuple[Decimal | None, bool, bool, str | None, bool]:
        """Compute market_value for one asset holding.

        Returns: (value_in_target_ccy, price_found, is_stale, missing_fx_pair, is_last_buy)

        Valuation sources (in priority order):
        1. MARKET_PRICE: PriceHistory exists on or before dt → use market price
        2. LAST_BUY_PRICE: No PriceHistory but last BUY price from V(u) available
        3. MISSING: Neither → excluded from NAV (error)

        NO WAC→price fallback. WAC is only for cost basis, never for valuation.
        """
        prices = self.price_map.get(asset_id)
        result = self._price_on_date(prices, dt) if prices else None

        if result is not None:
            # --- MARKET_PRICE path ---
            raw_price, price_ccy, actual_date = result
            is_stale = (dt - actual_date).days > STALE_PRICE_THRESHOLD_DAYS
            quote_base = self.quote_base_map.get(asset_id)
            holding_value = compute_holding_value(qty, raw_price, quote_base)

            if price_ccy == self.target_currency:
                return holding_value, True, is_stale, None, False

            rate = self.fx_rate_map.get((price_ccy, self.target_currency, dt))
            if rate is None:
                return None, True, is_stale, f"{price_ccy}/{self.target_currency}", False

            return holding_value * rate, True, is_stale, None, False

        # --- LAST_BUY_PRICE path (from V(u) visible brokers) ---
        lbp = self.last_buy_prices.get(asset_id)
        if lbp is not None:
            buy_date, unit_price, buy_ccy = lbp
            if buy_date <= dt:
                # Use last buy price as valuation
                holding_value = unit_price * qty
                if buy_ccy == self.target_currency:
                    return holding_value, False, False, None, True
                rate = self.fx_rate_map.get((buy_ccy, self.target_currency, dt))
                if rate is not None:
                    return holding_value * rate, False, False, None, True
                # FX missing for last_buy_price conversion
                return None, False, False, f"{buy_ccy}/{self.target_currency}", True

        # --- MISSING: no valuation source available ---
        return None, False, False, None, False

    def _compute_in_transit(self, dt: date_type, missing_fx: set[str]) -> tuple[Decimal, Decimal, Decimal]:
        """Compute in_transit_cash, in_transit_asset_mv, in_transit_asset_cb."""
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
                        it_cash += converted * interval.share
                    else:
                        missing_fx.add(f"{dep.currency}/{self.target_currency}")
            else:
                # Asset in transit: market value from daily price
                if interval.asset_id is not None:
                    dep = interval.departure_leg
                    qty = abs(dep.quantity) if dep.quantity else zero
                    if qty > 0:
                        mv, _, _, fx_miss, _ = self._market_value_for(interval.asset_id, qty, dt)
                        if mv is not None:
                            it_asset_mv += mv * interval.share
                        if fx_miss:
                            missing_fx.add(fx_miss)

                # Cost basis from cost_basis_override or fallback
                if interval.cost_basis_amount is not None and interval.cost_basis_currency:
                    cb = self._convert(interval.cost_basis_amount, interval.cost_basis_currency, dt)
                    if cb is not None:
                        it_asset_cb += cb * interval.share

        return it_cash, it_asset_mv, it_asset_cb

    def _compute_open_cost_basis_inline(
        self,
        cumulative_qty: dict[tuple[int, int], Decimal],
        wac_pool_qty: dict[tuple[int, int], Decimal],
        wac_pool_cost: dict[tuple[int, int], Decimal],
        dt: date_type,
        missing_fx: set[str],
    ) -> Decimal:
        """Compute open cost basis from inline WAC pool.

        For each position with qty > 0: cost_basis = wac * qty, converted to target_currency.
        WAC is in asset_currency; conversion uses daily FX rate.
        """
        total = Decimal("0")
        for (asset_id, broker_id), qty in cumulative_qty.items():
            if qty <= 0:
                continue
            key = (asset_id, broker_id)
            pool_q = wac_pool_qty.get(key, Decimal("0"))
            pool_c = wac_pool_cost.get(key, Decimal("0"))
            if pool_q <= 0:
                continue
            wac_val = pool_c / pool_q
            wac_ccy = self.asset_currencies.get(asset_id, self.target_currency)
            ocb_in_wac_ccy = wac_val * qty
            if wac_ccy == self.target_currency:
                total += ocb_in_wac_ccy
            else:
                rate = self.fx_rate_map.get((wac_ccy, self.target_currency, dt))
                if rate is not None:
                    total += ocb_in_wac_ccy * rate
                else:
                    missing_fx.add(f"{wac_ccy}/{self.target_currency}")
        return total

    def _buy_unit_cost(self, tx: Transaction) -> Decimal | None:
        """Compute unit cost for a BUY/acquisition transaction in the asset's native currency.

        Returns unit_cost in asset_currency, or None if cost cannot be determined.
        Handles FX conversion from tx.currency to asset_currency via fx_rate_map.
        """
        asset_id = tx.asset_id
        if asset_id is None:
            return None

        qty = abs(tx.quantity) if tx.quantity else Decimal("0")
        if qty == 0:
            return None

        asset_ccy = self.asset_currencies.get(asset_id, self.target_currency)

        # For BUY: cost = |amount| in tx.currency
        # For TRANSFER-in: cost = cost_basis_override in cost_basis_currency
        if tx.type == TransactionType.BUY:
            if tx.amount is None or tx.amount == 0:
                return Decimal("0")
            total_cost = abs(tx.amount)
            cost_ccy = tx.currency or asset_ccy
        elif tx.cost_basis_override is not None:
            # TRANSFER with cost_basis_override
            total_cost = tx.cost_basis_override * qty
            cost_ccy = tx.cost_basis_currency or asset_ccy
        else:
            # No cost info (e.g., TRANSFER without CBO) → None (add at current WAC)
            return None

        # Convert total_cost from cost_ccy to asset_ccy
        if cost_ccy == asset_ccy:
            return total_cost / qty

        # Need FX: cost_ccy → asset_ccy
        # Strategy: use fx(cost_ccy → target) / fx(asset_ccy → target) if asset_ccy != target
        #           or fx(cost_ccy → target) directly if asset_ccy == target
        if asset_ccy == self.target_currency:
            rate = self.fx_rate_map.get((cost_ccy, self.target_currency, tx.date))
            if rate is not None:
                return (total_cost * rate) / qty
        else:
            rate_cost_to_target = self.fx_rate_map.get((cost_ccy, self.target_currency, tx.date))
            rate_asset_to_target = self.fx_rate_map.get((asset_ccy, self.target_currency, tx.date))
            if rate_cost_to_target is not None and rate_asset_to_target is not None and rate_asset_to_target != 0:
                cross_rate = rate_cost_to_target / rate_asset_to_target
                return (total_cost * cross_rate) / qty

        # Cannot convert — return None (will be treated as add-at-current-WAC)
        return None

    @staticmethod
    def _apply_split_rescale(
        key: tuple[int, int],
        tx_qty: Decimal,
        wac_pool_qty: dict[tuple[int, int], Decimal],
        wac_pool_cost: dict[tuple[int, int], Decimal],
        zero: Decimal,
    ) -> None:
        """Apply a SPLIT-linked quantity change to the WAC pool by rescaling, not add/reduce.

        A split (forward or reverse) never adds or removes economic cost — it only
        redistributes the existing total cost over a different unit count. Unlike a
        BUY (cost added) or SELL (cost removed proportionally at current WAC), the
        pool's total cost is left UNCHANGED here; only quantity moves. This preserves
        the cost invariant q*wac = const from plan v2 §8.2 for both forward
        (tx_qty > 0) and reverse (tx_qty < 0) splits alike — e.g. 15@100 -> +15 ->
        30@50 (cost 1500 both sides), or 30@50 -> -15 -> 15@100 (cost 1500 both sides).
        Mutates wac_pool_qty/wac_pool_cost in place.
        """
        new_qty = wac_pool_qty[key] + tx_qty
        if new_qty > zero:
            wac_pool_qty[key] = new_qty
            # wac_pool_cost[key] intentionally untouched: total cost is split-invariant.
        else:
            wac_pool_qty[key] = zero
            wac_pool_cost[key] = zero

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


# =============================================================================
# PORTFOLIO CALCULATION RESULT
# =============================================================================


@dataclass
class EngineEndState:
    """Serialized accumulator state at end of a computation blob.

    Used for forward cache extension: resume computation from this state
    instead of recomputing from scratch.
    """

    cumulative_cash: Decimal
    cumulative_ecf: Decimal
    cumulative_qty: dict[tuple[int, int], Decimal]
    wac_pool_qty: dict[tuple[int, int], Decimal]
    wac_pool_cost: dict[tuple[int, int], Decimal]
    capital_pool: dict[int, Decimal]  # K per broker
    returns_pool: dict[int, Decimal]  # R per broker
    withdrawn_pool: Decimal  # W global


@dataclass
class PortfolioCalculationResult:
    """Complete result from the portfolio calculation engine."""

    daily_states: list[DailyPortfolioState]
    # Position snapshots for exposure + contribution views
    position_states_start: list[DailyPositionState] = field(default_factory=list)
    position_states_end: list[DailyPositionState] = field(default_factory=list)
    # Period accumulators for contribution (populated during frame loop)
    per_realized: dict[tuple[int, int], Decimal] = field(default_factory=dict)
    per_income: dict[tuple[int, int], Decimal] = field(default_factory=dict)
    per_fees_taxes: dict[tuple[int, int], Decimal] = field(default_factory=dict)
    unalloc_income: dict[int, Decimal] = field(default_factory=dict)
    unalloc_fees: dict[int, Decimal] = field(default_factory=dict)
    # End state for cache forward extension
    end_state: EngineEndState | None = None
    # Metadata
    scope_broker_ids: list[int] = field(default_factory=list)
    target_currency: str = "EUR"
    date_from: date_type = field(default_factory=date_type.today)
    date_to: date_type = field(default_factory=date_type.today)


# =============================================================================
# DERIVED VIEWS BUILDER — Converts DailyPortfolioState[] into API DTOs
# =============================================================================


class DerivedViewsBuilder:
    """Derives summary, history, allocation, and performance views from daily states.

    Pure function — no I/O.
    """

    def __init__(
        self,
        daily_states: list[DailyPortfolioState],
        target_currency: str,
    ) -> None:
        self.daily_states = daily_states
        self.target_currency = target_currency

    def build_history(self) -> list[dict]:
        """Build PortfolioHistoryPoint-compatible dicts from daily states.

        Returns dicts (not PortfolioHistoryPoint) to avoid circular import.
        The API adapter converts these to PortfolioHistoryPoint.
        """
        return [
            {
                "date": s.date,
                "cash_value": CurrencySchema(code=self.target_currency, amount=s.cash_value),
                "market_value": CurrencySchema(code=self.target_currency, amount=s.market_value),
                "broker_nav_value": CurrencySchema(code=self.target_currency, amount=s.broker_nav_value),
                "in_transit_cash_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_cash_value) if s.in_transit_cash_value else None,
                "in_transit_asset_market_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_asset_market_value) if s.in_transit_asset_market_value else None,
                "in_transit_market_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_market_value) if s.in_transit_market_value else None,
                "nav_value": CurrencySchema(code=self.target_currency, amount=s.nav_value),
                "open_cost_basis": CurrencySchema(code=self.target_currency, amount=s.open_cost_basis) if s.open_cost_basis else None,
                "in_transit_asset_cost_basis": CurrencySchema(code=self.target_currency, amount=s.in_transit_asset_cost_basis) if s.in_transit_asset_cost_basis else None,
                "in_transit_book_value": CurrencySchema(code=self.target_currency, amount=s.in_transit_book_value) if s.in_transit_book_value else None,
                "book_value": CurrencySchema(code=self.target_currency, amount=s.book_value) if s.book_value else None,
                "capital_baseline": CurrencySchema(code=self.target_currency, amount=s.cumulative_external_cash_flow),
                "book_asset_like": CurrencySchema(code=self.target_currency, amount=s.book_asset_like),
                "cash_from_contributed_capital": CurrencySchema(code=self.target_currency, amount=s.cash_from_contributed_capital),
                "cash_from_generated_returns": CurrencySchema(code=self.target_currency, amount=s.cash_from_generated_returns),
                "total_pnl": CurrencySchema(code=self.target_currency, amount=s.total_pnl),
                "unrealized_gain_loss": CurrencySchema(code=self.target_currency, amount=s.unrealized_gain_loss) if s.unrealized_gain_loss else None,
            }
            for s in self.daily_states
        ]

    def build_performance_inputs(
        self,
    ) -> tuple[list, list]:
        """Extract NAV snapshots and cash flows for ROI calculations.

        Returns (nav_snapshots, cash_flows) compatible with roi_utils functions.
        Sign convention: CashFlowInput uses investor perspective (deposit = negative).
        DailyPortfolioState uses portfolio perspective (deposit = positive).
        So we negate external_cash_flow when passing to performance functions.
        """
        nav_snapshots = [NAVSnapshot(date=s.date, nav=s.nav_value) for s in self.daily_states]
        cash_flows = [CashFlowInput(date=s.date, amount=-s.external_cash_flow) for s in self.daily_states if s.external_cash_flow != 0]
        return nav_snapshots, cash_flows

    def build_allocation_current(
        self,
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Build current allocation from the last daily state.

        Returns (by_type, by_sector, by_geography) as lists of AllocationItem-like dicts.
        """
        if not self.daily_states:
            return [], [], []

        last = self.daily_states[-1]

        def _alloc(d: dict[str, Decimal], use_sector_emoji: bool = False) -> list[dict]:
            total = sum(d.values()) or Decimal("1")
            return [
                {
                    "name": name,
                    "value": (amt / total * 100).quantize(Decimal("0.01")),
                    "amount": amt,
                    "emoji": SECTOR_EMOJIS.get(name) if use_sector_emoji else None,
                }
                for name, amt in sorted(d.items(), key=lambda x: -x[1])
            ]

        return _alloc(last.by_type), _alloc(last.by_sector, use_sector_emoji=True), _alloc(last.by_geography)

    def build_allocation_history(self, dimension: str, date_from: date_type | None = None) -> list[dict]:
        """Build allocation history series for a given dimension.

        Returns list of {date, components: [{name, value, amount}]} dicts.
        """
        from datetime import date as date_type  # noqa: PLC0415

        attr_map = {"type": "by_type", "sector": "by_sector", "geography": "by_geography"}
        attr = attr_map.get(dimension, "by_type")

        result = []
        for s in self.daily_states:
            if date_from and s.date < date_from:
                continue
            d = getattr(s, attr, {})
            total = sum(d.values()) or Decimal("1")
            components = [
                {
                    "name": name,
                    "value": (amt / total * 100).quantize(Decimal("0.01")),
                    "amount": amt,
                }
                for name, amt in sorted(d.items(), key=lambda x: -x[1])
            ]
            result.append({"date": s.date, "components": components})
        return result

    def aggregate_missing_price_ids(self) -> set[int]:
        """Collect all asset IDs that had missing prices across any day."""
        ids: set[int] = set()
        for s in self.daily_states:
            ids.update(s.missing_price_asset_ids)
        return ids

    def aggregate_stale_price_ids(self) -> set[int]:
        """Collect all asset IDs that had stale prices across any day."""
        ids: set[int] = set()
        for s in self.daily_states:
            ids.update(s.stale_price_asset_ids)
        return ids

    def aggregate_missing_fx_pairs(self) -> set[str]:
        """Collect all missing FX pairs across all days."""
        pairs: set[str] = set()
        for s in self.daily_states:
            pairs.update(s.missing_fx_pairs)
        return pairs

    def aggregate_transaction_implied_ids(self) -> set[int]:
        """Collect all asset IDs valued via transaction-implied (no market price)."""
        ids: set[int] = set()
        for s in self.daily_states:
            ids.update(s.transaction_implied_asset_ids)
        return ids

    def build_data_quality_report(
        self,
        missing_price_assets_dto: list | None = None,
        stale_prices_dto: list | None = None,
        missing_fx_pairs_dto: list | None = None,
        transaction_implied_assets_dto: list | None = None,
        classifier_warnings: list[str] | None = None,
        mwrr_available: bool = True,
    ) -> DataQualityReport:
        """Aggregate per-day data quality into a DataQualityReport DTO.

        missing_price_assets_dto / stale_prices_dto / missing_fx_pairs_dto are
        pre-built DTO lists (caller constructs them with full asset/broker info).
        transaction_implied_assets_dto: assets valued at cost (no market price but WAC present).
        If None, the report still populates date-level fields.
        """
        incomplete_nav: list[date_type] = []
        for s in self.daily_states:
            if not s.nav_complete:
                incomplete_nav.append(s.date)

        # Build structured issues list
        issues: list[DataQualityIssue] = []

        # MISSING_PRICE — error: assets excluded from NAV
        if missing_price_assets_dto:
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.MISSING_PRICE,
                    severity=IssueSeverity.ERROR,
                    message_i18n_key="dataQuality.missingPrice",
                    message_params={"count": len(missing_price_assets_dto)},
                    count=len(missing_price_assets_dto),
                    affected_asset_ids=[a.asset_id for a in missing_price_assets_dto],
                    affected_asset_names=[a.name for a in missing_price_assets_dto],
                    cta_action="navigate_asset",
                    cta_target=str(missing_price_assets_dto[0].asset_id),
                    group_key="missing_price",
                )
            )

        # TRANSACTION_IMPLIED — warning: assets at cost (pre-market, e.g. BTP collocamento)
        if transaction_implied_assets_dto:
            as_of_date = self.daily_states[-1].date.isoformat() if self.daily_states else None
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.TRANSACTION_IMPLIED,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.transactionImplied",
                    message_params={"count": len(transaction_implied_assets_dto), "as_of_date": as_of_date},
                    count=len(transaction_implied_assets_dto),
                    affected_asset_ids=[a.asset_id for a in transaction_implied_assets_dto],
                    affected_asset_names=[a.name for a in transaction_implied_assets_dto],
                    cta_action="navigate_asset",
                    cta_target=str(transaction_implied_assets_dto[0].asset_id),
                    group_key="transaction_implied",
                )
            )

        # STALE_PRICE — warning: prices older than threshold
        if stale_prices_dto:
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.STALE_PRICE,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.stalePrice",
                    message_params={"count": len(stale_prices_dto)},
                    count=len(stale_prices_dto),
                    affected_asset_ids=[a.asset_id for a in stale_prices_dto],
                    affected_asset_names=[a.name for a in stale_prices_dto],
                    cta_action="navigate_asset",
                    cta_target=str(stale_prices_dto[0].asset_id),
                    group_key="stale_price",
                )
            )

        # MISSING_FX_MARKET — warning: FX pairs needed but missing
        if missing_fx_pairs_dto:
            pairs = list({p.pair for p in missing_fx_pairs_dto})
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.MISSING_FX_MARKET,
                    severity=IssueSeverity.WARNING,
                    message_i18n_key="dataQuality.missingFx",
                    message_params={"count": len(pairs)},
                    count=len(pairs),
                    affected_fx_pairs=pairs,
                    cta_action="add_fx_pair",
                    group_key="missing_fx",
                )
            )

        # NAV_INCOMPLETE — info: some days had incomplete NAV
        if incomplete_nav:
            incomplete_nav_sorted = sorted(incomplete_nav)
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.NAV_INCOMPLETE,
                    severity=IssueSeverity.INFO,
                    message_i18n_key="dataQuality.navIncomplete",
                    message_params={
                        "count": len(incomplete_nav_sorted),
                        "date_from": incomplete_nav_sorted[0].isoformat(),
                        "date_to": incomplete_nav_sorted[-1].isoformat(),
                    },
                    count=len(incomplete_nav_sorted),
                    group_key="nav_incomplete",
                )
            )

        # MWRR_NOT_CALCULABLE — info
        if not mwrr_available:
            issues.append(
                DataQualityIssue(
                    domain=IssueDomain.PORTFOLIO,
                    code=IssueCode.MWRR_NOT_CALCULABLE,
                    severity=IssueSeverity.INFO,
                    message_i18n_key="dataQuality.mwrrNotAvailable",
                    group_key="mwrr",
                )
            )

        return DataQualityReport(
            issues=issues,
            missing_price_assets=missing_price_assets_dto or [],
            missing_fx_pairs=missing_fx_pairs_dto or [],
            stale_prices=stale_prices_dto or [],
            incomplete_nav_dates=incomplete_nav,
            warnings=classifier_warnings or [],
        )


# =============================================================================
# PORTFOLIO CALCULATION ENGINE — Async orchestrator
# =============================================================================


def _compute_tx_fingerprint(transactions: list[Transaction]) -> str:
    """Compute a hash fingerprint over transaction IDs and updated_at timestamps.

    Any transaction insert, update, or delete changes this fingerprint,
    automatically invalidating cached portfolio results.
    """
    h = hashlib.md5(usedforsecurity=False)
    for tx in transactions:
        h.update(f"{tx.id}:{tx.updated_at.isoformat()}".encode())
    return h.hexdigest()


class PortfolioCalculationEngine:
    """Async orchestrator that loads data from DB and runs the calculation pipeline.

    Usage:
        engine = PortfolioCalculationEngine(db_session)
        result = await engine.calculate(user_id, broker_ids, date_from, date_to, currency)
        views = DerivedViewsBuilder(result.daily_states, result.target_currency)
    """

    def __init__(self, db) -> None:
        """Initialize with an async DB session."""
        self.db = db

    async def calculate(
        self,
        user_id: int,
        broker_ids: list[int] | None = None,
        date_from: date_type | None = None,
        date_to: date_type | None = None,
        target_currency: str | None = None,
    ) -> PortfolioCalculationResult:
        """Run the full portfolio calculation pipeline.

        WAC is computed inline during the daily state build — no separate
        compute_wac_iterative calls needed (eliminates N×M DB round-trips).
        """
        # ── 1. Resolve target currency ──
        if target_currency is None:
            target_currency = await get_global_setting(self.db, "base_currency", "EUR")

        # ── 2. Resolve scope + visible brokers ──
        # V(u) = all visible brokers (for last_buy_price fallback)
        all_access_stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        all_access_result = await self.db.execute(all_access_stmt)
        all_accesses = list(all_access_result.scalars().all())
        visible_broker_ids = {a.broker_id for a in all_accesses}

        # S = scope (filtered subset for portfolio aggregation)
        if broker_ids:
            accesses = [a for a in all_accesses if a.broker_id in set(broker_ids)]
        else:
            accesses = all_accesses

        if not accesses:
            return PortfolioCalculationResult(
                daily_states=[],
                scope_broker_ids=[],
                target_currency=target_currency,
                date_from=date_from or date_type.today(),
                date_to=date_to or date_type.today(),
            )

        scope_broker_ids = {a.broker_id for a in accesses}
        broker_shares = {a.broker_id: a.share_percentage or Decimal("1") for a in accesses}

        # ── 3. Load ALL transactions for scope brokers ──
        tx_stmt = select(Transaction).where(Transaction.broker_id.in_(scope_broker_ids)).order_by(Transaction.date, Transaction.id)
        tx_result = await self.db.execute(tx_stmt)
        all_txs = list(tx_result.scalars().all())

        if not all_txs:
            return PortfolioCalculationResult(
                daily_states=[],
                scope_broker_ids=list(scope_broker_ids),
                target_currency=target_currency,
                date_from=date_from or date_type.today(),
                date_to=date_to or date_type.today(),
            )

        # ── 3b. Identify ADJUSTMENT rows linked to a SPLIT AssetEvent ──
        # These bypass the normal BUY/SELL WAC pool math in DailyStateBuilder: a split
        # redistributes existing cost over a new quantity, it never adds/removes cost.
        split_event_tx_ids = {tx.id for tx in all_txs if tx.asset_event_id is not None}
        split_linked_tx_ids: set[int] = set()
        if split_event_tx_ids:
            split_asset_event_stmt = select(Transaction.id).join(AssetEvent, Transaction.asset_event_id == AssetEvent.id).where(Transaction.id.in_(split_event_tx_ids)).where(AssetEvent.type == AssetEventType.SPLIT)
            split_linked_tx_ids = set((await self.db.execute(split_asset_event_stmt)).scalars().all())

        # ── 4. Classify transactions ──
        classifier = ScopeAwareTransactionClassifier(scope_broker_ids, all_txs, broker_shares)
        needed_ids = classifier.get_needed_paired_ids()

        external_paired: dict[int, Transaction] = {}
        if needed_ids:
            ext_stmt = select(Transaction).where(Transaction.id.in_(needed_ids))
            ext_result = await self.db.execute(ext_stmt)
            external_paired = {tx.id: tx for tx in ext_result.scalars().all()}

        classification = classifier.classify(external_paired)

        # ── 4b. Precompute last_buy_prices from V(u) BUY transactions ──
        # For valuation fallback: MARKET_PRICE → LAST_BUY_PRICE(V(u)) → MISSING
        # Load BUY txs from non-scope visible brokers (scope BUYs already in all_txs)
        extra_visible_ids = visible_broker_ids - scope_broker_ids
        all_buy_txs: list[Transaction] = [
            tx for tx in all_txs
            if tx.type == TransactionType.BUY and tx.asset_id and tx.quantity and tx.quantity > 0
        ]
        if extra_visible_ids:
            extra_buy_stmt = (
                select(Transaction)
                .where(Transaction.broker_id.in_(extra_visible_ids))
                .where(Transaction.type == TransactionType.BUY)
                .where(Transaction.quantity > 0)
                .where(Transaction.asset_id.is_not(None))
                .order_by(Transaction.date)
            )
            extra_buy_result = await self.db.execute(extra_buy_stmt)
            all_buy_txs.extend(extra_buy_result.scalars().all())

        # Build last_buy_prices: asset_id → (date, unit_price, currency)
        # Sorted chronologically, last one wins
        last_buy_prices: dict[int, tuple[date_type, Decimal, str]] = {}
        for tx in sorted(all_buy_txs, key=lambda t: (t.date, t.id or 0)):
            if tx.asset_id and tx.quantity and tx.quantity > 0 and tx.amount:
                unit_price = abs(tx.amount) / tx.quantity
                ccy = tx.currency or "EUR"
                last_buy_prices[tx.asset_id] = (tx.date, unit_price, ccy)

        # ── 5. Determine date range ──
        first_tx_date = min(tx.date for tx in all_txs)
        actual_from = date_from or first_tx_date
        actual_to = date_to or date_type.today()

        # ── 5b. Blob cache check (range-aware) ──
        tx_fingerprint = _compute_tx_fingerprint(all_txs)
        held_asset_ids = {tx.asset_id for tx in all_txs if tx.asset_id and tx.quantity and tx.quantity != 0}
        price_fingerprint = await self._compute_price_fingerprint(held_asset_ids, actual_to)
        # split_linked_tx_ids is queried live (not derived from tx_fingerprint), so it must
        # be part of the key: editing an AssetEvent's type after linking does not bump any
        # Transaction.updated_at, but does change this set on the next call.
        split_linked_fingerprint = tuple(sorted(split_linked_tx_ids))

        # Blob key: independent of date range (blob stores its own range)
        blob_key = (
            user_id,
            tuple(sorted(scope_broker_ids)),
            target_currency,
            tx_fingerprint,
            price_fingerprint,
            split_linked_fingerprint,
        )

        cached_blob, blob_hit = _portfolio_blob_cache.get(blob_key)
        if blob_hit and cached_blob is not None:
            blob_from = cached_blob.date_from
            blob_to = cached_blob.date_to
            # Check if requested range exactly matches the blob's range.
            # NOTE: must be an EXACT match on blob_to, not a superset check
            # (blob_to >= actual_to). The blob's daily_states/position_states_end/
            # end_state are not trimmed to actual_to before being returned, so a
            # "wider" cached blob would leak days beyond the requested date_to
            # into every downstream consumer (get_history, get_summary, ...).
            if blob_from <= actual_from and blob_to == actual_to:
                logger.debug("Portfolio blob cache hit (exact match)", user_id=user_id)
                return cached_blob
            # Forward extension: blob covers from start but needs more days at end
            if (blob_from <= actual_from and blob_to < actual_to
                    and cached_blob.end_state is not None):
                logger.debug("Portfolio blob cache forward extension",
                            user_id=user_id, extending=f"{blob_to}..{actual_to}")
                # Will proceed to full compute but with frame_start = blob_to + 1
                # and initial accumulators from end_state
                # (full extension with state resume deferred — for now recompute)
                pass
            else:
                logger.debug("Portfolio blob cache miss (range mismatch)", user_id=user_id,
                            blob_range=f"{blob_from}..{blob_to}", requested=f"{actual_from}..{actual_to}")

        # ── 6. Preload prices (bulk) ──
        price_map: dict[int, list[tuple[date_type, Decimal, str]]] = {}
        if held_asset_ids:
            price_stmt = select(PriceHistory).where(PriceHistory.asset_id.in_(held_asset_ids)).where(PriceHistory.date <= actual_to).order_by(PriceHistory.asset_id, PriceHistory.date)
            price_result = await self.db.execute(price_stmt)
            for ph in price_result.scalars().all():
                price_map.setdefault(ph.asset_id, []).append((ph.date, ph.close, ph.currency))

        # ── 7. Preload quote_base_quantity ──
        quote_base_map: dict[int, int | None] = {}
        assets_list: list = []
        if held_asset_ids:
            asset_stmt = select(Asset).where(Asset.id.in_(held_asset_ids))
            asset_result = await self.db.execute(asset_stmt)
            assets_list = list(asset_result.scalars().all())
            for a in assets_list:
                quote_base_map[a.id] = a.quote_base_quantity

        # ── 8. Build asset_currencies map (replaces N×M WAC pre-load) ──
        asset_currencies: dict[int, str] = {}
        for a in assets_list:
            asset_currencies[a.id] = a.currency or target_currency

        # ── 9. Preload asset classification + types ──
        asset_classifications: dict[int, dict | None] = {}
        asset_types: dict[int, str] = {}
        for a in assets_list:
            asset_types[a.id] = a.asset_type.value if a.asset_type else "Unknown"
            if a.classification_params:
                try:
                    asset_classifications[a.id] = json.loads(a.classification_params)
                except Exception:
                    asset_classifications[a.id] = None
            else:
                asset_classifications[a.id] = None

        # ── 10. Preload FX rates ──
        fx_rate_map = await self._preload_fx_rates(
            classification.classified,
            classification.in_transit_intervals,
            classification.external_cash_flows,
            price_map,
            asset_currencies,
            target_currency,
            actual_from,
            actual_to,
        )

        # ── 11. Build daily states ──
        builder = DailyStateBuilder(
            classified_txs=classification.classified,
            in_transit_intervals=classification.in_transit_intervals,
            external_cash_flows=classification.external_cash_flows,
            price_map=price_map,
            quote_base_map=quote_base_map,
            fx_rate_map=fx_rate_map,
            asset_classifications=asset_classifications,
            asset_types=asset_types,
            asset_currencies=asset_currencies,
            target_currency=target_currency,
            date_from=actual_from,
            date_to=actual_to,
            last_buy_prices=last_buy_prices,
            split_linked_tx_ids=split_linked_tx_ids,
        )
        result = builder.build()

        # ── 12. Store in blob cache ──
        _portfolio_blob_cache.set(blob_key, result)
        logger.debug("Portfolio blob cache stored", user_id=user_id, n_states=len(result.daily_states),
                    range=f"{actual_from}..{actual_to}")

        return result

    async def _compute_price_fingerprint(
        self,
        held_asset_ids: set[int],
        date_to: date_type,
    ) -> str:
        """Compute a lightweight fingerprint of price data for cache invalidation.

        Uses COUNT + MAX(fetched_at) as a proxy — any price insert/update
        changes at least one of these, invalidating the cache key.
        """
        if not held_asset_ids:
            return "no_assets"
        stmt = (
            select(
                func.count(PriceHistory.id),
                func.max(PriceHistory.fetched_at),
            )
            .where(PriceHistory.asset_id.in_(held_asset_ids))
            .where(PriceHistory.date <= date_to)
        )
        row = (await self.db.execute(stmt)).one()
        count = row[0] or 0
        max_fetched = row[1].isoformat() if row[1] else "none"
        return f"{count}:{max_fetched}"

    async def _preload_fx_rates(
        self,
        classified_txs: list[ClassifiedTransaction],
        in_transit_intervals: list[InTransitInterval],
        external_cash_flows: list[tuple[date_type, Decimal, str]],
        price_map: dict[int, list[tuple[date_type, Decimal, str]]],
        asset_currencies: dict[int, str],
        target_currency: str,
        date_from: date_type,
        date_to: date_type,
    ) -> dict[tuple[str, str, date_type], Decimal]:
        """Pre-load all FX rates needed for the calculation in one bulk call.

        Includes rates for:
        - Transaction amounts → target_currency (all tx dates)
        - External cash flows → target_currency
        - Price currencies → target_currency (every day in range)
        - Asset currencies (for inline WAC) → target_currency (every day in range + BUY dates)
        - In-transit currencies → target_currency
        """
        # Collect all (from_ccy, date) pairs needed
        fx_needs: set[tuple[str, date_type]] = set()

        # From transaction amounts
        for ctxn in classified_txs:
            tx = ctxn.tx
            if tx.amount and tx.amount != 0 and tx.currency and tx.currency != target_currency:
                fx_needs.add((tx.currency, tx.date))

        # From external cash flows
        for dt, _, ccy in external_cash_flows:
            if ccy != target_currency:
                fx_needs.add((ccy, dt))

        # From price currencies — need rate for every day in range
        price_currencies: set[str] = set()
        for prices in price_map.values():
            for _, _, ccy in prices:
                if ccy != target_currency:
                    price_currencies.add(ccy)

        # From asset currencies (for inline WAC cost_basis evaluation daily)
        asset_ccys_non_target: set[str] = set()
        for ccy in asset_currencies.values():
            if ccy != target_currency:
                asset_ccys_non_target.add(ccy)

        # For price/asset currencies we need rates for every day in range
        all_non_target_ccys = price_currencies | asset_ccys_non_target
        if all_non_target_ccys:
            current = date_from
            while current <= date_to:
                for ccy in all_non_target_ccys:
                    fx_needs.add((ccy, current))
                current += timedelta(days=1)

        # For inline WAC: also need asset currency rates at BUY dates (pre-frame)
        # so that cross-rate fx(tx_ccy → asset_ccy) can be computed
        for ctxn in classified_txs:
            tx = ctxn.tx
            if tx.quantity and tx.quantity > 0 and tx.asset_id:
                asset_ccy = asset_currencies.get(tx.asset_id, target_currency)
                if asset_ccy != target_currency:
                    fx_needs.add((asset_ccy, tx.date))

        # From in-transit intervals
        for interval in in_transit_intervals:
            dep = interval.departure_leg
            if interval.tx_type == "cash" and dep.currency and dep.currency != target_currency:
                current = interval.start_date
                while current <= interval.end_date:
                    fx_needs.add((dep.currency, current))
                    current += timedelta(days=1)
            if interval.cost_basis_currency and interval.cost_basis_currency != target_currency:
                current = interval.start_date
                while current <= interval.end_date:
                    fx_needs.add((interval.cost_basis_currency, current))
                    current += timedelta(days=1)

        if not fx_needs:
            return {}

        # Batch convert
        fx_needs_list = list(fx_needs)
        bulk_items = [(CurrencySchema(code=ccy, amount=Decimal("1")), target_currency, dt) for ccy, dt in fx_needs_list]

        results, _ = await convert_bulk(self.db, bulk_items, raise_on_error=False)

        fx_rate_map: dict[tuple[str, str, date_type], Decimal] = {}
        for i, (ccy, dt) in enumerate(fx_needs_list):
            if i < len(results) and results[i] is not None:
                converted_amount = results[i][0].amount if results[i] else None
                if converted_amount is not None:
                    fx_rate_map[(ccy, target_currency, dt)] = converted_amount

        return fx_rate_map
