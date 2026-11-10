"""Promotion of loose rows into linked pairs, for ``TransactionService``: the type maps and the suggestions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.transactions.promotion import TXPromoteSuggestCandidate, TXPromoteSuggestResponse
from backend.app.schemas.transactions.type_metadata import TX_TYPE_METADATA, PairFieldConstraint
from backend.app.utils.datetime_utils import shift_date


@dataclass(frozen=True)
class _PromoteCandidate:
    """Lightweight duck-type-compatible object for _check_promote_constraints.
    Used by promote-suggest to validate constraints without a full Transaction."""

    broker_id: int
    asset_id: Optional[int]
    currency: Optional[str]
    amount: Optional[Decimal]
    quantity: Optional[Decimal]


class TransactionPromotionMixin:
    """Promotion: the type maps of split and promote, and the suggestions of what to promote.

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session``, ``execute_batch`` and,
    from ``TransactionAccessMixin``, ``_enforce_batch_access`` and ``_get_accessible_broker_ids``.
    """

    session: AsyncSession

    # =========================================================================
    # BULK SPLIT / PROMOTE (server-driven, immediate)
    # =========================================================================

    # Deterministic type mutation maps for split/promote.
    # Key: paired type → (from_type, to_type).
    # "from" = negative/source side, "to" = positive/destination side.
    SPLIT_TYPE_MAP: dict[TransactionType, tuple[TransactionType, TransactionType]] = {
        TransactionType.CASH_TRANSFER: (TransactionType.WITHDRAWAL, TransactionType.DEPOSIT),
        TransactionType.TRANSFER: (TransactionType.ADJUSTMENT, TransactionType.ADJUSTMENT),
        TransactionType.FX_CONVERSION: (TransactionType.WITHDRAWAL, TransactionType.DEPOSIT),
    }

    # Inverse: (type_a, type_b) → target paired type.
    # type_a/type_b ordering comes from promote_from metadata.
    # For WITHDRAWAL+DEPOSIT we need to distinguish CASH_TRANSFER vs FX_CONVERSION
    # using field constraints, so the service checks dynamically.

    @staticmethod
    def _find_promote_rule_match(tx_a, tx_b) -> Optional[TransactionType]:
        """Scan TX_TYPE_METADATA promote_from rules for a match between tx_a and tx_b."""
        for pair_type, meta in TX_TYPE_METADATA.items():
            if meta.promote_from is None:
                continue
            for rule in meta.promote_from:
                if (tx_a.type.value == rule.type_a and tx_b.type.value == rule.type_b) or (tx_a.type.value == rule.type_b and tx_b.type.value == rule.type_a):
                    if TransactionPromotionMixin._check_promote_constraints(tx_a, tx_b, rule.field_constraints):
                        return pair_type
        return None

    @staticmethod
    def _resolve_promote_ref(
        id_val: Optional[int],
        link_uuid_val: Optional[str],
        existing_by_id: Dict[int, Transaction],
        link_uuid_map: Dict[str, List[Tuple[int, Transaction]]],
    ) -> Optional[Transaction]:
        """Resolve a promote reference to a Transaction.

        - id_val > 0 → lookup in existing_by_id
        - link_uuid_val → lookup first TX in link_uuid_map[link_uuid_val]
        """
        if id_val is not None and id_val > 0:
            return existing_by_id.get(id_val)
        if link_uuid_val:
            entries = link_uuid_map.get(link_uuid_val, [])
            if entries:
                return entries[0][1]  # (idx, Transaction) → Transaction
        return None

    @staticmethod
    def _check_promote_constraints(tx_a: Transaction, tx_b: Transaction, constraints: list) -> bool:  # noqa: C901 — flat field×relation matcher, early returns
        """Check if two transactions satisfy promote field constraints."""
        for c in constraints:
            assert isinstance(c, PairFieldConstraint)
            if c.field == "broker_id":
                if c.relation == "equal" and tx_a.broker_id != tx_b.broker_id:
                    return False
                if c.relation == "different" and tx_a.broker_id == tx_b.broker_id:
                    return False
            elif c.field == "asset_id":
                if c.relation == "equal" and tx_a.asset_id != tx_b.asset_id:
                    return False
                if c.relation == "different" and tx_a.asset_id == tx_b.asset_id:
                    return False
            elif c.field == "cash_currency":
                if c.relation == "equal" and tx_a.currency != tx_b.currency:
                    return False
                if c.relation == "different" and tx_a.currency == tx_b.currency:
                    return False
            elif c.field == "cash_amount":
                if c.relation == "opposite":
                    if tx_a.amount is None or tx_b.amount is None:
                        continue  # Cannot verify — skip constraint
                    if tx_a.amount != -tx_b.amount:
                        return False
            elif c.field == "quantity":
                if c.relation == "opposite":
                    if tx_a.quantity is None or tx_b.quantity is None:
                        continue  # Cannot verify — skip constraint
                    if tx_a.quantity != -tx_b.quantity:
                        return False
        return True

    async def promote_suggest_bulk(  # noqa: C901 — nested rule/candidate matching loops, no decision trees
        self,
        inputs: List,
        tolerance_days: int,
        user_id: int,
    ) -> TXPromoteSuggestResponse:
        """For each input TX, find DB transactions compatible for promote."""
        # Only brokers the user can edit: a merge changes both rows, so a candidate on a broker the user only views
        # could never be taken (the bulk editor's picker shows it disabled), and offering it would inflate the 💡 count
        accessible = await self._get_editable_broker_ids(user_id)
        if not accessible:
            return TXPromoteSuggestResponse(results={})

        # Collect all positive IDs from inputs to exclude self-match
        input_positive_ids: set[int] = {inp.id for inp in inputs if inp.id > 0}

        results: Dict[int, List[TXPromoteSuggestCandidate]] = {}

        for inp in inputs:
            # Determine complementary types from promote_from rules. A row linked to an asset event
            # can only become a type that accepts the link: apply_promotes refuses any other
            # (`eventTypeIncompatible`), so neither side of a suggestion may carry one.
            linked_input = bool(inp.asset_event_id)
            complementary: list[tuple[TransactionType, list, bool]] = []
            for _pair_type, meta in TX_TYPE_METADATA.items():
                if meta.promote_from is None:
                    continue
                if linked_input and not meta.event_compatible:
                    continue
                for rule in meta.promote_from:
                    if inp.type.value == rule.type_a:
                        comp_type = TransactionType(rule.type_b)
                        complementary.append((comp_type, rule.field_constraints, meta.event_compatible))
                    elif inp.type.value == rule.type_b:
                        comp_type = TransactionType(rule.type_a)
                        complementary.append((comp_type, rule.field_constraints, meta.event_compatible))

            if not complementary:
                results[inp.id] = []
                continue

            # Query DB: standalone TX with complementary type, date ±tolerance, editable broker
            comp_types = list({ct for ct, _, _ in complementary})
            # W-B71: a draft's date at the calendar's edge narrows the window, never raises (a 500 for the whole request).
            lo = shift_date(inp.date, -tolerance_days)
            hi = shift_date(inp.date, tolerance_days)

            stmt = select(Transaction).where(Transaction.type.in_(comp_types)).where(Transaction.related_transaction_id.is_(None)).where(Transaction.date >= lo).where(Transaction.date <= hi).where(Transaction.broker_id.in_(accessible))
            if input_positive_ids:
                stmt = stmt.where(Transaction.id.notin_(input_positive_ids))

            rows = (await self.session.execute(stmt)).scalars().all()

            # Build input as _PromoteCandidate for constraint checking
            inp_candidate = _PromoteCandidate(
                broker_id=inp.broker_id,
                asset_id=inp.asset_id,
                currency=inp.currency,
                amount=inp.amount,
                quantity=inp.quantity,
            )

            candidates: list[TXPromoteSuggestCandidate] = []
            for row in rows:
                matched = False
                for comp_type, constraints, accepts_event in complementary:
                    if row.type != comp_type:
                        continue
                    if row.asset_event_id is not None and not accepts_event:
                        continue
                    if self._check_promote_constraints(inp_candidate, row, constraints):
                        matched = True
                        break
                if matched:
                    candidates.append(
                        TXPromoteSuggestCandidate(
                            id=row.id,
                            broker_id=row.broker_id,
                            date=row.date,
                            type=row.type.value,
                            currency=row.currency,
                            asset_id=row.asset_id,
                        )
                    )

            results[inp.id] = candidates

        return TXPromoteSuggestResponse(results=results)
