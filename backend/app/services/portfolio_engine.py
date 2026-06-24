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
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Literal, Optional

from sqlalchemy import select

from backend.app.db.models import Asset, BrokerUserAccess, PriceHistory, Transaction, TransactionType
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
from backend.app.utils.financial.roi_utils import CashFlowInput, NAVSnapshot
from backend.app.utils.financial.valuation_utils import compute_holding_value

# Transaction types that are always external cash flows when unlinked
_EXTERNAL_CASH_TYPES = {TransactionType.DEPOSIT, TransactionType.WITHDRAWAL}

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

    Window is [start_date, end_date] inclusive.  Both dates are the exclusive
    boundaries of the departure/arrival legs:
        start_date = departure_date + 1
        end_date   = arrival_date   - 1
    If start_date > end_date the interval is empty (same day or adjacent days).
    """

    start_date: date_type  # departure_date + 1
    end_date: date_type  # arrival_date - 1
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
                warnings.append(
                    f"Transaction {tx.id} ({tx.type}) has related_transaction_id={tx.related_transaction_id} "
                    f"but paired transaction not found — treating as normal"
                )
                # If it looks like a deposit/withdrawal, count as external
                if tx.amount and tx.amount != 0 and tx.currency:
                    external_cash_flows.append((tx.date, tx.amount * share, tx.currency))
                continue

            pair_key = (min(tx.id or 0, paired.id or 0), max(tx.id or 0, paired.id or 0))
            is_paired_in_scope = paired.broker_id in self.scope_broker_ids

            if is_paired_in_scope:
                # ── LINKED INTERNAL — both legs in scope ──
                ctxn = ClassifiedTransaction(
                    tx=tx, classification="linked_internal", paired_tx=paired, share=share
                )
                classified.append(ctxn)

                # In-transit: only create once per pair, only if dates differ
                if pair_key not in processed_pairs and tx.date != paired.date:
                    interval = self._build_in_transit_interval(tx, paired)
                    if interval is not None:
                        in_transit_intervals.append(interval)

                    # Warn if share percentages differ between source/dest brokers
                    paired_share = self.broker_shares.get(paired.broker_id, Decimal("1"))
                    if share != paired_share:
                        warnings.append(
                            f"Linked internal pair ({tx.id}, {paired.id}): share mismatch "
                            f"broker {tx.broker_id}={share} vs broker {paired.broker_id}={paired_share}"
                        )
            else:
                # ── LINKED EXTERNAL — only this leg in scope ──
                # Determine if this leg is inflow or outflow based on amount/quantity sign
                classification = self._classify_external_leg(tx)
                ctxn = ClassifiedTransaction(
                    tx=tx, classification=classification, paired_tx=paired, share=share
                )
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
    def _build_in_transit_interval(
        tx_a: Transaction, tx_b: Transaction
    ) -> InTransitInterval | None:
        """Build an InTransitInterval for a linked internal pair with different dates.

        Departure = earlier date leg, arrival = later date leg.
        Window = [departure_date + 1, arrival_date - 1] (exclusive endpoints).
        Returns None if the interval would be empty (adjacent days).
        """
        if tx_a.date <= tx_b.date:
            departure, arrival = tx_a, tx_b
        else:
            departure, arrival = tx_b, tx_a

        start = departure.date + timedelta(days=1)
        end = arrival.date - timedelta(days=1)

        if start > end:
            return None  # Adjacent days or same day — no transit window

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
    """

    def __init__(
        self,
        *,
        classified_txs: list[ClassifiedTransaction],
        in_transit_intervals: list[InTransitInterval],
        external_cash_flows: list[tuple[date_type, Decimal, str]],
        price_map: dict[int, list[tuple[date_type, Decimal, str]]],
        quote_base_map: dict[int, int | None],
        wac_series: dict[tuple[int, int], list[tuple[date_type, Decimal, str]]],
        fx_rate_map: dict[tuple[str, str, date_type], Decimal],
        asset_classifications: dict[int, dict | None],
        asset_types: dict[int, str],
        target_currency: str,
        date_from: date_type,
        date_to: date_type,
    ) -> None:
        self.classified_txs = classified_txs
        self.in_transit_intervals = in_transit_intervals
        self.external_cash_flows = external_cash_flows
        self.price_map = price_map
        self.quote_base_map = quote_base_map
        self.wac_series = wac_series
        self.fx_rate_map = fx_rate_map
        self.asset_classifications = asset_classifications
        self.asset_types = asset_types
        self.target_currency = target_currency
        self.date_from = date_from
        self.date_to = date_to

    def build(self) -> list[DailyPortfolioState]:
        """Build one DailyPortfolioState per calendar day in [date_from, date_to]."""
        zero = Decimal("0")

        # ── 1. Cash ledger: sum amount deltas per day ──
        cash_deltas: dict[date_type, Decimal] = defaultdict(lambda: zero)
        for ctxn in self.classified_txs:
            tx = ctxn.tx
            if tx.amount and tx.amount != 0 and tx.currency:
                converted = self._convert(tx.amount, tx.currency, tx.date)
                if converted is not None:
                    cash_deltas[tx.date] += converted * ctxn.share

        # ── 2. Quantity ledger: sum qty deltas per (asset_id, broker_id) per day ──
        qty_deltas: dict[date_type, dict[tuple[int, int], Decimal]] = defaultdict(
            lambda: defaultdict(lambda: zero)
        )
        for ctxn in self.classified_txs:
            tx = ctxn.tx
            if tx.quantity and tx.quantity != 0 and tx.asset_id is not None:
                key = (tx.asset_id, tx.broker_id)
                qty_deltas[tx.date][key] += tx.quantity * ctxn.share

        # ── 3. External cash flow index ──
        ecf_by_date: dict[date_type, Decimal] = defaultdict(lambda: zero)
        for dt, amount, ccy in self.external_cash_flows:
            converted = self._convert(amount, ccy, dt)
            if converted is not None:
                ecf_by_date[dt] += converted

        # ── 4. Dense daily loop ──
        states: list[DailyPortfolioState] = []
        cumulative_cash = zero
        cumulative_qty: dict[tuple[int, int], Decimal] = defaultdict(lambda: zero)

        current = self.date_from
        while current <= self.date_to:
            # 4a. Update cash
            cumulative_cash += cash_deltas.get(current, zero)

            # 4b. Update quantities
            day_qty = qty_deltas.get(current)
            if day_qty:
                for key, delta in day_qty.items():
                    cumulative_qty[key] += delta

            # 4c. Market value per asset
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
                    asset_id, qty, current
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

            # 4e. WAC / open_cost_basis
            open_cost_basis = self._compute_open_cost_basis(
                cumulative_qty, current, missing_fx
            )

            # 4f. Compose
            broker_nav = market_value + cumulative_cash
            in_transit_mv = it_cash + it_asset_mv
            nav = broker_nav + in_transit_mv
            in_transit_bv = it_cash + it_asset_cb
            book = open_cost_basis + cumulative_cash + in_transit_bv
            ug = nav - book

            # 4g. External cash flow for this day
            ecf_today = ecf_by_date.get(current, zero)

            # 4h. Allocation: cash as Liquidity (type + sector, not geography)
            by_type["Liquidity"] = by_type.get("Liquidity", zero) + cumulative_cash + it_cash
            by_sector["Liquidity"] = (
                by_sector.get("Liquidity", zero) + cumulative_cash + it_cash
            )

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

        return states

    # ── Helper methods ──

    def _convert(
        self, amount: Decimal, from_ccy: str, dt: date_type
    ) -> Decimal | None:
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

    def _wac_on_date(
        self,
        sorted_wac: list[tuple[date_type, Decimal, str]],
        query_date: date_type,
    ) -> tuple[Decimal | None, str | None]:
        """Forward-fill: latest WAC at or before query_date."""
        if not sorted_wac:
            return None, None
        dates = [p[0] for p in sorted_wac]
        idx = bisect.bisect_right(dates, query_date) - 1
        if idx < 0:
            return None, None
        _, wac_val, wac_ccy = sorted_wac[idx]
        return wac_val, wac_ccy

    def _market_value_for(
        self, asset_id: int, qty: Decimal, dt: date_type
    ) -> tuple[Decimal | None, bool, bool, str | None, bool]:
        """Compute market_value for one asset holding.

        Returns: (value_in_target_ccy, price_found, is_stale, missing_fx_pair, is_implied)

        Valuation sources (in priority order):
        1. MARKET_PRICE: PriceHistory exists on or before dt → use market price
        2. TRANSACTION_IMPLIED: No PriceHistory but WAC/cost_basis available →
           use open_cost_basis as a temporary proxy (warning issued at report level)
        3. MISSING: Neither price nor cost_basis → excluded from NAV (error)
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

        # No market price — try TRANSACTION_IMPLIED via WAC/open_cost_basis
        # Check all (asset_id, broker_id) WAC series for this asset
        implied_value: Decimal | None = None
        for (aid, _bid), wac_data in self.wac_series.items():
            if aid != asset_id:
                continue
            wac_val, wac_ccy = self._wac_on_date(wac_data, dt)
            if wac_val is None or wac_ccy is None:
                continue
            ocb = wac_val * qty
            if wac_ccy == self.target_currency:
                implied_value = (implied_value or Decimal("0")) + ocb
            else:
                rate = self.fx_rate_map.get((wac_ccy, self.target_currency, dt))
                if rate is not None:
                    implied_value = (implied_value or Decimal("0")) + ocb * rate

        if implied_value is not None and implied_value > 0:
            return implied_value, False, False, None, True

        # Neither market price nor WAC — fully missing
        return None, False, False, None, False

    def _compute_in_transit(
        self, dt: date_type, missing_fx: set[str]
    ) -> tuple[Decimal, Decimal, Decimal]:
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
                        mv, _, _, fx_miss, _ = self._market_value_for(
                            interval.asset_id, qty, dt
                        )
                        if mv is not None:
                            it_asset_mv += mv * interval.share
                        if fx_miss:
                            missing_fx.add(fx_miss)

                # Cost basis from cost_basis_override or fallback
                if (
                    interval.cost_basis_amount is not None
                    and interval.cost_basis_currency
                ):
                    cb = self._convert(
                        interval.cost_basis_amount, interval.cost_basis_currency, dt
                    )
                    if cb is not None:
                        it_asset_cb += cb * interval.share

        return it_cash, it_asset_mv, it_asset_cb

    def _compute_open_cost_basis(
        self,
        cumulative_qty: dict[tuple[int, int], Decimal],
        dt: date_type,
        missing_fx: set[str],
    ) -> Decimal:
        """WAC forward-fill × quantity for each asset/broker with qty > 0."""
        total = Decimal("0")
        for (asset_id, broker_id), qty in cumulative_qty.items():
            if qty <= 0:
                continue
            wac_data = self.wac_series.get((asset_id, broker_id), [])
            wac_val, wac_ccy = self._wac_on_date(wac_data, dt)
            if wac_val is None or wac_ccy is None:
                continue
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
                        by_geo[country] = by_geo.get(country, Decimal("0")) + mv * Decimal(str(weight))
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
class PortfolioCalculationResult:
    """Complete result from the portfolio calculation engine."""

    daily_states: list[DailyPortfolioState]
    scope_broker_ids: list[int]
    target_currency: str
    date_from: date_type
    date_to: date_type


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
        nav_snapshots = [
            NAVSnapshot(date=s.date, nav=s.nav_value) for s in self.daily_states
        ]
        cash_flows = [
            CashFlowInput(date=s.date, amount=-s.external_cash_flow)
            for s in self.daily_states
            if s.external_cash_flow != 0
        ]
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

        def _alloc(d: dict[str, Decimal]) -> list[dict]:
            total = sum(d.values()) or Decimal("1")
            return [
                {
                    "name": name,
                    "value": (amt / total * 100).quantize(Decimal("0.01")),
                    "amount": amt,
                }
                for name, amt in sorted(d.items(), key=lambda x: -x[1])
            ]

        return _alloc(last.by_type), _alloc(last.by_sector), _alloc(last.by_geography)

    def build_allocation_history(
        self, dimension: str, date_from: date_type | None = None
    ) -> list[dict]:
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
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MISSING_PRICE,
                severity=IssueSeverity.ERROR,
                message_i18n_key="dataQuality.missingPrice",
                message_params={"count": len(missing_price_assets_dto)},
                count=len(missing_price_assets_dto),
                affected_asset_ids=[a.asset_id for a in missing_price_assets_dto],
                affected_asset_names=[a.name for a in missing_price_assets_dto],
                cta_action="navigate_asset",
                group_key="missing_price",
            ))

        # TRANSACTION_IMPLIED — warning: assets at cost (pre-market, e.g. BTP collocamento)
        if transaction_implied_assets_dto:
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.TRANSACTION_IMPLIED,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.transactionImplied",
                message_params={"count": len(transaction_implied_assets_dto)},
                count=len(transaction_implied_assets_dto),
                affected_asset_ids=[a.asset_id for a in transaction_implied_assets_dto],
                affected_asset_names=[a.name for a in transaction_implied_assets_dto],
                cta_action="navigate_asset",
                group_key="transaction_implied",
            ))

        # STALE_PRICE — warning: prices older than threshold
        if stale_prices_dto:
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.STALE_PRICE,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.stalePrice",
                message_params={"count": len(stale_prices_dto)},
                count=len(stale_prices_dto),
                affected_asset_ids=[a.asset_id for a in stale_prices_dto],
                affected_asset_names=[a.name for a in stale_prices_dto],
                cta_action="navigate_asset",
                group_key="stale_price",
            ))

        # MISSING_FX_MARKET — warning: FX pairs needed but missing
        if missing_fx_pairs_dto:
            pairs = list({p.pair for p in missing_fx_pairs_dto})
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MISSING_FX_MARKET,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.missingFx",
                message_params={"count": len(pairs)},
                count=len(pairs),
                affected_fx_pairs=pairs,
                cta_action="add_fx_pair",
                group_key="missing_fx",
            ))

        # NAV_INCOMPLETE — info: some days had incomplete NAV
        if incomplete_nav:
            incomplete_nav_sorted = sorted(incomplete_nav)
            issues.append(DataQualityIssue(
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
            ))

        # MWRR_NOT_CALCULABLE — info
        if not mwrr_available:
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MWRR_NOT_CALCULABLE,
                severity=IssueSeverity.INFO,
                message_i18n_key="dataQuality.mwrrNotAvailable",
                group_key="mwrr",
            ))

        return DataQualityReport(
            issues=issues,
            missing_price_assets=missing_price_assets_dto or [],
            missing_fx_pairs=missing_fx_pairs_dto or [],
            stale_prices=stale_prices_dto or [],
            incomplete_nav_dates=incomplete_nav,
            warnings=classifier_warnings or [],
        )
        """Aggregate per-day data quality into a DataQualityReport DTO.

        missing_price_assets_dto / stale_prices_dto / missing_fx_pairs_dto are
        pre-built DTO lists (caller constructs them with full asset/broker info).
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
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MISSING_PRICE,
                severity=IssueSeverity.ERROR,
                message_i18n_key="dataQuality.missingPrice",
                message_params={"count": len(missing_price_assets_dto)},
                count=len(missing_price_assets_dto),
                affected_asset_ids=[a.asset_id for a in missing_price_assets_dto],
                affected_asset_names=[a.name for a in missing_price_assets_dto],
                cta_action="navigate_asset",
                group_key="missing_price",
            ))

        # STALE_PRICE — warning: prices older than threshold
        if stale_prices_dto:
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.STALE_PRICE,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.stalePrice",
                message_params={"count": len(stale_prices_dto)},
                count=len(stale_prices_dto),
                affected_asset_ids=[a.asset_id for a in stale_prices_dto],
                affected_asset_names=[a.name for a in stale_prices_dto],
                cta_action="navigate_asset",
                group_key="stale_price",
            ))

        # MISSING_FX_MARKET — warning: FX pairs needed but missing
        if missing_fx_pairs_dto:
            pairs = list({p.pair for p in missing_fx_pairs_dto})
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MISSING_FX_MARKET,
                severity=IssueSeverity.WARNING,
                message_i18n_key="dataQuality.missingFx",
                message_params={"count": len(pairs)},
                count=len(pairs),
                affected_fx_pairs=pairs,
                cta_action="add_fx_pair",
                group_key="missing_fx",
            ))

        # NAV_INCOMPLETE — info: some days had incomplete NAV
        if incomplete_nav:
            incomplete_nav_sorted = sorted(incomplete_nav)
            issues.append(DataQualityIssue(
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
            ))

        # MWRR_NOT_CALCULABLE — info
        if not mwrr_available:
            issues.append(DataQualityIssue(
                domain=IssueDomain.PORTFOLIO,
                code=IssueCode.MWRR_NOT_CALCULABLE,
                severity=IssueSeverity.INFO,
                message_i18n_key="dataQuality.mwrrNotAvailable",
                group_key="mwrr",
            ))

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
        """Run the full portfolio calculation pipeline."""
        from backend.app.services.portfolio_service import compute_wac_iterative  # noqa: PLC0415 (deferred to avoid circular)
        # ── 1. Resolve target currency ──
        if target_currency is None:
            target_currency = await get_global_setting(self.db, "base_currency", "EUR")

        # ── 2. Resolve scope ──
        stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        if broker_ids:
            stmt = stmt.where(BrokerUserAccess.broker_id.in_(broker_ids))
        result = await self.db.execute(stmt)
        accesses = list(result.scalars().all())

        if not accesses:
            return PortfolioCalculationResult(
                daily_states=[],
                scope_broker_ids=[],
                target_currency=target_currency,
                date_from=date_from or date_type.today(),
                date_to=date_to or date_type.today(),
            )

        scope_broker_ids = {a.broker_id for a in accesses}
        broker_shares = {
            a.broker_id: a.share_percentage or Decimal("1") for a in accesses
        }

        # ── 3. Load ALL transactions for scope brokers ──
        tx_stmt = (
            select(Transaction)
            .where(Transaction.broker_id.in_(scope_broker_ids))
            .order_by(Transaction.date, Transaction.id)
        )
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

        # ── 4. Classify transactions ──
        classifier = ScopeAwareTransactionClassifier(
            scope_broker_ids, all_txs, broker_shares
        )
        needed_ids = classifier.get_needed_paired_ids()

        external_paired: dict[int, Transaction] = {}
        if needed_ids:
            ext_stmt = select(Transaction).where(Transaction.id.in_(needed_ids))
            ext_result = await self.db.execute(ext_stmt)
            external_paired = {tx.id: tx for tx in ext_result.scalars().all()}

        classification = classifier.classify(external_paired)

        # ── 5. Determine date range ──
        first_tx_date = min(tx.date for tx in all_txs)
        actual_from = date_from or first_tx_date
        actual_to = date_to or date_type.today()

        # ── 6. Preload prices (bulk) ──
        held_asset_ids = {
            tx.asset_id
            for tx in all_txs
            if tx.asset_id and tx.quantity and tx.quantity != 0
        }

        price_map: dict[int, list[tuple[date_type, Decimal, str]]] = {}
        if held_asset_ids:
            price_stmt = (
                select(PriceHistory)
                .where(PriceHistory.asset_id.in_(held_asset_ids))
                .where(PriceHistory.date <= actual_to)
                .order_by(PriceHistory.asset_id, PriceHistory.date)
            )
            price_result = await self.db.execute(price_stmt)
            for ph in price_result.scalars().all():
                price_map.setdefault(ph.asset_id, []).append(
                    (ph.date, ph.close, ph.currency)
                )

        # ── 7. Preload quote_base_quantity ──
        quote_base_map: dict[int, int | None] = {}
        assets_list: list = []
        if held_asset_ids:
            asset_stmt = select(Asset).where(Asset.id.in_(held_asset_ids))
            asset_result = await self.db.execute(asset_stmt)
            assets_list = list(asset_result.scalars().all())
            for a in assets_list:
                quote_base_map[a.id] = a.quote_base_quantity

        # ── 8. Preload WAC series ──
        wac_series: dict[tuple[int, int], list[tuple[date_type, Decimal, str]]] = {}
        for asset_id in held_asset_ids:
            for broker_id in scope_broker_ids:
                asset_obj = next((a for a in assets_list if a.id == asset_id), None)
                asset_ccy = (asset_obj.currency if asset_obj else None) or target_currency
                wac_result = await compute_wac_iterative(
                    session=self.db,
                    broker_id=broker_id,
                    asset_id=asset_id,
                    as_of_date=actual_to,
                    asset_currency=asset_ccy,
                )
                if wac_result.wac and wac_result.wac_qualifying_txs:
                    series: list[tuple[date_type, Decimal, str]] = []
                    for qtx in wac_result.wac_qualifying_txs:
                        if qtx.running_wac is not None:
                            series.append((qtx.date, qtx.running_wac, wac_result.wac.code))
                    if series:
                        wac_series[(asset_id, broker_id)] = sorted(series, key=lambda x: x[0])

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
            wac_series,
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
            wac_series=wac_series,
            fx_rate_map=fx_rate_map,
            asset_classifications=asset_classifications,
            asset_types=asset_types,
            target_currency=target_currency,
            date_from=actual_from,
            date_to=actual_to,
        )
        daily_states = builder.build()

        return PortfolioCalculationResult(
            daily_states=daily_states,
            scope_broker_ids=list(scope_broker_ids),
            target_currency=target_currency,
            date_from=actual_from,
            date_to=actual_to,
        )

    async def _preload_fx_rates(
        self,
        classified_txs: list[ClassifiedTransaction],
        in_transit_intervals: list[InTransitInterval],
        external_cash_flows: list[tuple[date_type, Decimal, str]],
        price_map: dict[int, list[tuple[date_type, Decimal, str]]],
        wac_series: dict[tuple[int, int], list[tuple[date_type, Decimal, str]]],
        target_currency: str,
        date_from: date_type,
        date_to: date_type,
    ) -> dict[tuple[str, str, date_type], Decimal]:
        """Pre-load all FX rates needed for the calculation in one bulk call."""
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

        # From WAC currencies
        wac_currencies: set[str] = set()
        for series in wac_series.values():
            for _, _, ccy in series:
                if ccy != target_currency:
                    wac_currencies.add(ccy)

        # For price/WAC currencies we need rates for every day in range
        all_non_target_ccys = price_currencies | wac_currencies
        if all_non_target_ccys:
            current = date_from
            while current <= date_to:
                for ccy in all_non_target_ccys:
                    fx_needs.add((ccy, current))
                current += timedelta(days=1)

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
        bulk_items = [
            (CurrencySchema(code=ccy, amount=Decimal("1")), target_currency, dt)
            for ccy, dt in fx_needs
        ]

        results, _ = await convert_bulk(self.db, bulk_items, raise_on_error=False)

        fx_rate_map: dict[tuple[str, str, date_type], Decimal] = {}
        for i, (ccy, dt) in enumerate(fx_needs):
            if i < len(results) and results[i] is not None:
                converted_amount = results[i][0].amount if results[i] else None
                if converted_amount is not None:
                    fx_rate_map[(ccy, target_currency, dt)] = converted_amount

        return fx_rate_map
