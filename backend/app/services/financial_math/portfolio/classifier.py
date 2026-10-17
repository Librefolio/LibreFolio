"""Scope-aware classification of transactions: internal or external to the selected brokers, and the in-transit intervals of transfers."""

from __future__ import annotations

from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from backend.app.db.models import Transaction, TransactionType
from backend.app.services.financial_math.portfolio.models import ClassificationResult, ClassificationType, ClassifiedTransaction, InTransitInterval, ShareMismatch

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

    def classify(  # noqa: C901 — per-tx linked/unlinked variant dispatch with early continues
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
        external_cash_flows: list[tuple[date_type, int, Decimal, str]] = []
        warnings: list[str] = []
        share_mismatches: list[ShareMismatch] = []

        # Track which linked pairs we've already processed (avoid duplicates)
        processed_pairs: set[tuple[int, int]] = set()

        for tx in self.all_transactions:
            share = self.broker_shares.get(tx.broker_id, Decimal("1"))

            # ── UNLINKED transaction ──
            if tx.related_transaction_id is None:
                ctxn = ClassifiedTransaction(tx=tx, classification="normal", share=share)
                classified.append(ctxn)

                # Unlinked DEPOSIT/WITHDRAWAL → external cash flow. Lot 41 (D5): so is an
                # orphan CASH_TRANSFER / FX_CONVERSION, whose link was cleared when the
                # broker of the other leg was deleted: its money crossed the scope boundary.
                # An orphan TRANSFER (no amount) is in-kind capital, booked by
                # DailyStateBuilder._transfer_leg_capital.
                if (tx.type in _EXTERNAL_CASH_TYPES or tx.type in _CASH_LINKED_TYPES) and tx.amount and tx.amount != 0 and tx.currency:
                    external_cash_flows.append((tx.date, tx.broker_id, tx.amount * share, tx.currency))
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
                    external_cash_flows.append((tx.date, tx.broker_id, tx.amount * share, tx.currency))
                continue

            pair_key = (min(tx.id or 0, paired.id or 0), max(tx.id or 0, paired.id or 0))
            is_paired_in_scope = paired.broker_id in self.scope_broker_ids

            if is_paired_in_scope:
                # ── LINKED INTERNAL — both legs in scope ──
                ctxn = ClassifiedTransaction(tx=tx, classification="linked_internal", paired_tx=paired, share=share)
                classified.append(ctxn)

                # In-transit, and the share check: once per pair (the first of its two legs met)
                if pair_key not in processed_pairs:
                    # In-transit: only if the dates differ
                    if tx.date != paired.date:
                        interval = self._build_in_transit_interval(tx, paired)
                        if interval is not None:
                            # F2 — ownership scaling: attribute in-transit value at the
                            # departure broker's actual ownership share, not a fixed 100%.
                            # Without this, a <100%-owned shared broker would report the
                            # full untouched value while it is in transit, then jump to the
                            # correct scaled value the moment it lands — an owner-share
                            # regression `_build_in_transit_interval` deliberately leaves
                            # for this call site to close, since only here is
                            # `self.broker_shares` in scope.
                            interval.share = self.broker_shares.get(interval.departure_leg.broker_id, Decimal("1"))
                            in_transit_intervals.append(interval)

                    # J-43: brokers owned at different shares, on any dates (a same-day pair too): each leg counts at
                    # its own broker's share, so the gap between them is a result (D-MF4 = a), which the data-quality
                    # report explains with this record.
                    paired_share = self.broker_shares.get(paired.broker_id, Decimal("1"))
                    if share != paired_share:
                        warnings.append(f"Linked internal pair ({tx.id}, {paired.id}): share mismatch " f"broker {tx.broker_id}={share} vs broker {paired.broker_id}={paired_share}")
                        share_mismatches.append(self._share_mismatch(tx, share, paired, paired_share))
            else:
                # ── LINKED EXTERNAL — only this leg in scope ──
                # Determine if this leg is inflow or outflow based on amount/quantity sign
                classification = self._classify_external_leg(tx)
                ctxn = ClassifiedTransaction(tx=tx, classification=classification, paired_tx=paired, share=share)
                classified.append(ctxn)

                # External linked → generates external cash flow
                if tx.amount and tx.amount != 0 and tx.currency:
                    external_cash_flows.append((tx.date, tx.broker_id, tx.amount * share, tx.currency))

            processed_pairs.add(pair_key)

        result = ClassificationResult(
            classified=classified,
            in_transit_intervals=in_transit_intervals,
            external_cash_flows=external_cash_flows,
            warnings=warnings,
            share_mismatches=share_mismatches,
        )
        return result

    @staticmethod
    def _share_mismatch(tx: Transaction, share: Decimal, paired: Transaction, paired_share: Decimal) -> ShareMismatch:
        """The pair as a ShareMismatch: its legs ordered by transaction id, dated on the later leg."""
        (low_id, low_broker, low_share), (high_id, high_broker, high_share) = sorted(((tx.id or 0, tx.broker_id, share), (paired.id or 0, paired.broker_id, paired_share)))
        return ShareMismatch(tx_ids=(low_id, high_id), broker_ids=(low_broker, high_broker), shares=(low_share, high_share), date=max(tx.date, paired.date))

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

        if departure.date == arrival.date:
            return None  # Same-day transfer — no transit window (compared first: a pair on date.min has no day before)

        start = departure.date
        end = arrival.date - timedelta(days=1)

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
