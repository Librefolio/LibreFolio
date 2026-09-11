"""
Transaction Service for LibreFolio.

Centralizes all transaction business logic:
- CRUD operations with validation
- Link resolution for paired transactions (TRANSFER, FX_CONVERSION)
- Balance validation (cash and asset positions)

Atomic multi-broker semantics (Part 3):
- All bulk endpoints accept items spanning multiple brokers in a single batch.
- Access check (EDITOR) is enforced once per distinct `broker_id` touched.
- Any exception, access denial, or balance violation → full session rollback,
  `rolled_back=True`, per-item `status` in {failed, simulated, not_attempted}.
- The router never commits when `rolled_back=True`.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, Broker, BrokerUserAccess, Transaction, TransactionType, UserRole
from backend.app.schemas.transactions import (
    EVENT_COMPATIBLE_TYPES,
    TX_TYPE_METADATA,
    PairFieldConstraint,
    TXBatchResponse,
    TXCreateItem,
    TXEventSuggestCandidate,
    TXEventSuggestRequestItem,
    TXEventSuggestResultItem,
    TXPromoteSuggestCandidate,
    TXPromoteSuggestResponse,
    TXQueryParams,
    TXReadItem,
    TXTransferPromoteRequest,
    TXTransferPromoteResponse,
    TXUpdateItem,
    TXValidationCode,
)
from backend.app.schemas.wac import WACPreviewResultItem
from backend.app.services.portfolio_service import compute_wac_iterative
from backend.app.services.transaction_batch_context import (
    BalanceValidationError as BalanceValidationError,
)
from backend.app.services.transaction_batch_context import TransactionBatchContext
from backend.app.services.transaction_batch_stages import _parse_lenient as _parse_lenient
from backend.app.services.transaction_batch_stages import (
    apply_creates,
    apply_deletes,
    apply_promotes,
    apply_splits,
    apply_updates,
    compute_wac_and_fx_issues,
    finalize_response,
    parse_inputs,
    preload_and_authorize,
    resolve_create_links,
    validate_balances,
    validate_cost_basis,
    validate_updated_pairs,
)


class LinkedTransactionError(Exception):
    """Raised when linked transaction operations fail."""


from dataclasses import dataclass


@dataclass(frozen=True)
class _PromoteCandidate:
    """Lightweight duck-type-compatible object for _check_promote_constraints.
    Used by promote-suggest to validate constraints without a full Transaction."""

    broker_id: int
    asset_id: Optional[int]
    currency: Optional[str]
    amount: Optional[Decimal]
    quantity: Optional[Decimal]


class TransactionService:
    """
    Service for managing transactions.

    All methods are async and expect an AsyncSession.
    The caller is responsible for commit when `rolled_back=False`.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # =========================================================================
    # ACCESS CONTROL
    # =========================================================================

    async def _check_broker_access(self, broker_id: int, user_id: int, min_role: UserRole = UserRole.VIEWER) -> Optional[UserRole]:
        """Return the user's role (≥ min_role) or None if access is denied."""
        stmt = select(BrokerUserAccess).where(and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == user_id))
        result = await self.session.execute(stmt)
        access = result.scalar_one_or_none()

        if not access:
            return None

        role_order = {UserRole.OWNER: 3, UserRole.EDITOR: 2, UserRole.VIEWER: 1}
        if role_order.get(access.role, 0) >= role_order.get(min_role, 0):
            return access.role
        return None

    async def _check_broker_access_or_raise(self, broker_id: int, user_id: int, min_role: UserRole = UserRole.EDITOR) -> UserRole:
        """Enforce broker access at batch boundary; raise HTTPException(403) on miss."""
        role = await self._check_broker_access(broker_id, user_id, min_role=min_role)
        if role is None:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: {min_role.value} role required for broker {broker_id}",
            )
        return role

    async def _get_accessible_broker_ids(self, user_id: int) -> Set[int]:
        """Return the set of broker IDs the user can at least VIEW."""
        stmt = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id)
        result = await self.session.execute(stmt)
        return {row[0] for row in result.all()}

    async def _enforce_batch_access(self, broker_ids: Set[int], user_id: Optional[int], min_role: UserRole = UserRole.EDITOR) -> None:
        """One access check per distinct broker_id touched by the batch."""
        if user_id is None:
            return
        for broker_id in broker_ids:
            await self._check_broker_access_or_raise(broker_id, user_id, min_role=min_role)

    # =========================================================================
    # CROSS-RECORD VALIDATION HELPERS
    # =========================================================================

    async def _validate_asset_event_link(self, asset_event_id: int, expected_asset_id: int) -> None:
        """Verify the referenced AssetEvent exists and belongs to expected_asset_id."""
        event = await self.session.get(AssetEvent, asset_event_id)
        if event is None:
            raise ValueError(f"asset_event_id={asset_event_id} not found")
        if event.asset_id != expected_asset_id:
            raise ValueError(f"asset_event_id={asset_event_id} belongs to asset {event.asset_id}, not {expected_asset_id}")

    @staticmethod
    def _requires_cost_basis(tx: Transaction) -> bool:
        """True if this Transaction type+quantity requires cost_basis_override to be set."""
        if tx.quantity is None:
            return False
        if tx.type == TransactionType.TRANSFER and tx.quantity > 0:
            return True
        if tx.type == TransactionType.ADJUSTMENT and tx.quantity > 0:
            return True
        return False

    @staticmethod
    def _validate_linked_pair(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """
        Validate semantic coherence of a linked pair (Block H.1).

        Rules:
        - Both items must share the same `type` (no mixing e.g. TRANSFER + SELL).
        - TRANSFER requires distinct brokers (same-broker TRANSFER is a no-op).
        - FX_CONVERSION intra-broker is allowed (multi-currency account use case).
        - CASH_TRANSFER requires distinct brokers (same-broker is a no-op).

        Returns None when the pair is valid, otherwise a tuple of
        (error_message, code, params).
        """
        if a.type != b.type:
            return (
                f"linked pair must share the same type (got {a.type.value} + {b.type.value})",
                "pairTypeMismatch",
                {"typeA": a.type.value, "typeB": b.type.value},
            )
        if a.type == TransactionType.TRANSFER and a.broker_id == b.broker_id:
            return (
                f"TRANSFER requires distinct brokers (both on broker {a.broker_id})",
                "pairSameBroker",
                {"brokerId": a.broker_id},
            )
        if a.type == TransactionType.CASH_TRANSFER and a.broker_id == b.broker_id:
            return (
                f"CASH_TRANSFER requires distinct brokers (both on broker {a.broker_id})",
                "pairSameBroker",
                {"brokerId": a.broker_id},
            )
        return None

    @staticmethod
    def _validate_pair_description_tags(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """Validate that a linked pair has identical description and tags.

        Returns None when consistent, otherwise (error_message, code, params).
        """
        # Normalize None to "" for comparison
        desc_a = a.description or ""
        desc_b = b.description or ""
        if desc_a != desc_b:
            return (
                "Linked pair must have identical description",
                "pairDescriptionMismatch",
                {"descA": desc_a[:50], "descB": desc_b[:50]},
            )
        # Tags are stored as CSV strings; normalize None to ""
        tags_a = a.tags or ""
        tags_b = b.tags or ""
        if tags_a != tags_b:
            return (
                "Linked pair must have identical tags",
                "pairTagsMismatch",
                {"tagsA": tags_a, "tagsB": tags_b},
            )
        return None

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def query(self, params: TXQueryParams, user_id: Optional[int] = None) -> List[TXReadItem]:  # noqa: C901 — flat query-builder chain, one branch per filter
        """
        Query transactions with filters.

        When `user_id` is provided, the result is filtered to brokers the user
        can at least VIEW. When `params.ids` is set, results are returned in
        the exact input order (other filters besides access are ignored).
        """
        accessible_broker_ids: Optional[Set[int]] = None
        if user_id is not None:
            accessible_broker_ids = await self._get_accessible_broker_ids(user_id)
            if not accessible_broker_ids:
                return []

        if params.ids:
            stmt = select(Transaction).where(Transaction.id.in_(params.ids))
            if accessible_broker_ids is not None:
                stmt = stmt.where(Transaction.broker_id.in_(accessible_broker_ids))
            result = await self.session.execute(stmt)
            by_id = {tx.id: tx for tx in result.scalars().all()}
            ordered = [by_id[i] for i in params.ids if i in by_id]
            items = [TXReadItem.from_db_model(tx) for tx in ordered]
            return await self._enrich_partner_broker_ids(items)

        stmt = select(Transaction)

        if accessible_broker_ids is not None:
            stmt = stmt.where(Transaction.broker_id.in_(accessible_broker_ids))

        if params.broker_id:
            stmt = stmt.where(Transaction.broker_id == params.broker_id)
        if params.asset_id:
            stmt = stmt.where(Transaction.asset_id == params.asset_id)
        if params.types:
            stmt = stmt.where(Transaction.type.in_(params.types))
        if params.date_range:
            stmt = stmt.where(Transaction.date >= params.date_range.start)
            if params.date_range.end:
                stmt = stmt.where(Transaction.date <= params.date_range.end)
        if params.currency:
            stmt = stmt.where(Transaction.currency == params.currency)
        if params.tags:
            tag_conditions = [Transaction.tags.contains(tag) for tag in params.tags]
            stmt = stmt.where(or_(*tag_conditions))

        # H.3 — transfer-match helpers.
        if params.amount_abs_min is not None:
            stmt = stmt.where(func.abs(Transaction.amount) >= params.amount_abs_min)
        if params.amount_abs_max is not None:
            stmt = stmt.where(func.abs(Transaction.amount) <= params.amount_abs_max)
        if params.only_unlinked:
            stmt = stmt.where(Transaction.related_transaction_id.is_(None))
        if params.exclude_ids:
            stmt = stmt.where(Transaction.id.notin_(params.exclude_ids))

        stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
        stmt = stmt.offset(params.offset)
        if params.limit is not None:
            stmt = stmt.limit(params.limit)

        result = await self.session.execute(stmt)
        items = [TXReadItem.from_db_model(tx) for tx in result.scalars().all()]
        return await self._enrich_partner_broker_ids(items)

    async def _enrich_partner_broker_ids(self, items: List[TXReadItem]) -> List[TXReadItem]:
        """Batch-populate partner_broker_id for all items with related_transaction_id."""
        partner_ids = {item.related_transaction_id for item in items if item.related_transaction_id}
        if not partner_ids:
            return items
        stmt = select(Transaction.id, Transaction.broker_id).where(Transaction.id.in_(partner_ids))
        result = await self.session.execute(stmt)
        partner_map = {row.id: row.broker_id for row in result}
        for item in items:
            if item.related_transaction_id:
                item.partner_broker_id = partner_map.get(item.related_transaction_id)
        return items

    async def get_by_ids(self, tx_ids: List[int]) -> List[Transaction]:
        """Get multiple transactions by IDs (DB models, no access check)."""
        if not tx_ids:
            return []
        stmt = select(Transaction).where(Transaction.id.in_(tx_ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # =========================================================================
    # DELETE OPERATIONS (internal — delete_by_broker only)
    # =========================================================================

    async def delete_by_broker(self, broker_id: int) -> int:
        """
        Delete all transactions for a broker (internal helper for BrokerService).

        Skips access control and balance validation — caller is expected to have
        already verified OWNER permissions on the broker.
        """
        stmt = select(Transaction).where(Transaction.broker_id == broker_id)
        result = await self.session.execute(stmt)
        txs = result.scalars().all()
        tx_ids = [tx.id for tx in txs if tx.id is not None]

        if tx_ids:
            await self.session.execute(update(Transaction).where(Transaction.related_transaction_id.in_(tx_ids)).values(related_transaction_id=None))

        count = 0
        for tx in txs:
            await self.session.delete(tx)
            count += 1

        return count

    # =========================================================================
    # BALANCE VALIDATION
    # =========================================================================

    async def _validate_broker_balances(  # noqa: C901 — day-by-day balance replay, per-tx accumulate + raises
        self,
        broker_id: int,
        from_date: Optional[date_type] = None,
        batch_tx_ids: Optional[Dict[int, tuple]] = None,
    ) -> None:
        """Validate cash and asset balances for a broker from a given date.

        Args:
            batch_tx_ids: mapping of tx.id → (operation, batch_index) for batch transactions.
                When a violation is caused by a batch tx, the error carries its index.
        """
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return

        if broker.allow_cash_overdraft and broker.allow_asset_shorting:
            return

        if from_date is None:
            cash_balances: Dict[str, Decimal] = {}
            asset_balances: Dict[int, Decimal] = {}
            stmt = select(Transaction).where(Transaction.broker_id == broker_id).order_by(Transaction.date, Transaction.id)
        else:
            cash_balances, asset_balances = await self._get_balances_before_date(broker_id, from_date)
            stmt = select(Transaction).where(Transaction.broker_id == broker_id).where(Transaction.date >= from_date).order_by(Transaction.date, Transaction.id)

        result = await self.session.execute(stmt)
        txs = list(result.scalars().all())

        if not txs:
            return

        _batch = batch_tx_ids or {}

        txs_by_date: Dict[date_type, List[Transaction]] = defaultdict(list)
        for tx in txs:
            txs_by_date[tx.date].append(tx)

        current_date = min(txs_by_date.keys()) if from_date is None else from_date
        end_date = max(txs_by_date.keys())

        while current_date <= end_date:
            # Track last batch tx that reduced each balance on this day
            last_cash_reducer: Dict[str, tuple] = {}
            last_asset_reducer: Dict[int, tuple] = {}

            for tx in txs_by_date.get(current_date, []):
                if tx.amount != Decimal("0") and tx.currency:
                    cash_balances[tx.currency] = cash_balances.get(tx.currency, Decimal("0")) + tx.amount
                    # Track batch txs that reduce cash
                    if tx.amount < Decimal("0") and tx.id in _batch:
                        last_cash_reducer[tx.currency] = _batch[tx.id]
                if tx.quantity != Decimal("0") and tx.asset_id:
                    asset_balances[tx.asset_id] = asset_balances.get(tx.asset_id, Decimal("0")) + tx.quantity
                    # Track batch txs that reduce asset quantity
                    if tx.quantity < Decimal("0") and tx.id in _batch:
                        last_asset_reducer[tx.asset_id] = _batch[tx.id]

            if not broker.allow_cash_overdraft:
                for currency, balance in cash_balances.items():
                    if balance < Decimal("0"):
                        b_op, b_idx = last_cash_reducer.get(currency, ("create", -1))
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=currency,
                            balance=balance,
                            message=f"Cash balance for {currency} goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code=TXValidationCode.BALANCE_CASH_NEGATIVE.value,
                            params={"brokerId": broker_id, "currency": currency, "balance": str(balance), "date": str(current_date)},
                            batch_index=b_idx,
                            batch_operation=b_op,
                        )

            if not broker.allow_asset_shorting:
                for asset_id, balance in asset_balances.items():
                    if balance < Decimal("0"):
                        b_op, b_idx = last_asset_reducer.get(asset_id, ("create", -1))
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=f"asset:{asset_id}",
                            balance=balance,
                            message=f"Asset {asset_id} quantity goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code=TXValidationCode.BALANCE_ASSET_NEGATIVE.value,
                            params={"brokerId": broker_id, "assetId": asset_id, "balance": str(balance), "date": str(current_date)},
                            batch_index=b_idx,
                            batch_operation=b_op,
                        )

            current_date += timedelta(days=1)

    async def _get_balances_before_date(self, broker_id: int, before_date: date_type) -> Tuple[Dict[str, Decimal], Dict[int, Decimal]]:
        """Get cash and asset balances at end of day before the given date."""
        cash_stmt = select(Transaction.currency, func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.date < before_date).where(Transaction.currency.isnot(None)).group_by(Transaction.currency)
        result = await self.session.execute(cash_stmt)
        cash_balances: Dict[str, Decimal] = {currency: amount for currency, amount in result.all() if currency}

        asset_stmt = select(Transaction.asset_id, func.sum(Transaction.quantity)).where(Transaction.broker_id == broker_id).where(Transaction.date < before_date).where(Transaction.asset_id.isnot(None)).group_by(Transaction.asset_id)
        result = await self.session.execute(asset_stmt)
        asset_balances: Dict[int, Decimal] = {asset_id: qty for asset_id, qty in result.all() if asset_id}

        return cash_balances, asset_balances

    # =========================================================================
    # BALANCE QUERIES (for BRSummary)
    # =========================================================================

    async def get_cash_balances(self, broker_id: int) -> Dict[str, Decimal]:
        """Get current cash balances for a broker (currency → balance)."""
        stmt = select(Transaction.currency, func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.currency.isnot(None)).group_by(Transaction.currency)
        result = await self.session.execute(stmt)
        return {currency: amount for currency, amount in result.all() if currency}

    async def get_asset_holdings(self, broker_id: int) -> Dict[int, Decimal]:
        """Get current asset holdings for a broker (asset_id → quantity)."""
        stmt = select(Transaction.asset_id, func.sum(Transaction.quantity)).where(Transaction.broker_id == broker_id).where(Transaction.asset_id.isnot(None)).group_by(Transaction.asset_id)
        result = await self.session.execute(stmt)
        return {asset_id: qty for asset_id, qty in result.all() if asset_id}

    async def get_cost_basis(self, broker_id: int, asset_id: int) -> Decimal:
        """
        Get total cost basis for an asset holding (sum of BUY amounts, absolute).

        TODO: FIFO matching for accurate cost basis.
        """
        stmt = select(func.sum(Transaction.amount)).where(Transaction.broker_id == broker_id).where(Transaction.asset_id == asset_id).where(Transaction.type == TransactionType.BUY)
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        return abs(value or Decimal("0"))

    # =========================================================================
    # EVENTS SUGGEST (Block C.2)
    # =========================================================================

    async def suggest_events_bulk(self, requests: List[TXEventSuggestRequestItem]) -> List[TXEventSuggestResultItem]:
        """
        For each (asset_id, date, type, tolerance_days), return candidate
        AssetEvent rows whose type maps to the tx.type and whose date is
        within ±tolerance_days. Candidates are sorted by ascending |Δdays|.

        Mapping (TransactionType → AssetEventType):
        - DIVIDEND  → {DIVIDEND}
        - INTEREST  → {INTEREST}
        - ADJUSTMENT → {PRICE_ADJUSTMENT, SPLIT}
        Any other tx.type → skipped_reason="type_not_event_compatible".

        No side effects. The caller is responsible for auth.
        """
        type_map = {
            TransactionType.DIVIDEND: {AssetEventType.DIVIDEND},
            TransactionType.INTEREST: {AssetEventType.INTEREST},
            TransactionType.ADJUSTMENT: {AssetEventType.PRICE_ADJUSTMENT, AssetEventType.SPLIT},
        }

        results: List[TXEventSuggestResultItem] = []
        for req in requests:
            if req.type not in EVENT_COMPATIBLE_TYPES:
                results.append(
                    TXEventSuggestResultItem(
                        asset_id=req.asset_id,
                        date=req.date,
                        type=req.type,
                        candidates=[],
                        skipped_reason="type_not_event_compatible",
                    )
                )
                continue

            event_types = type_map.get(req.type, set())
            lo = req.date - timedelta(days=req.tolerance_days)
            hi = req.date + timedelta(days=req.tolerance_days)

            stmt = select(AssetEvent).where(AssetEvent.asset_id == req.asset_id).where(AssetEvent.type.in_(event_types)).where(AssetEvent.date >= lo).where(AssetEvent.date <= hi)
            rows = (await self.session.execute(stmt)).scalars().all()

            candidates = [
                TXEventSuggestCandidate(
                    id=ev.id,
                    asset_id=ev.asset_id,
                    date=ev.date,
                    type=str(ev.type),
                    value=ev.value,
                    currency=ev.currency,
                    is_auto=ev.provider_assignment_id is not None,
                    distance_days=abs((ev.date - req.date).days),
                )
                for ev in rows
            ]
            candidates.sort(key=lambda c: c.distance_days)

            results.append(
                TXEventSuggestResultItem(
                    asset_id=req.asset_id,
                    date=req.date,
                    type=req.type,
                    candidates=candidates,
                    skipped_reason=None,
                )
            )

        return results

    # =========================================================================
    # TRANSFER PROMOTION (Block H.4)
    # =========================================================================

    async def promote_transfer(  # noqa: C901 — sequential validation gates + per-type payload build
        self,
        req: TXTransferPromoteRequest,
        user_id: Optional[int] = None,
    ) -> TXTransferPromoteResponse:
        """
        Promote a sciolta coppia DEPOSIT/WITHDRAWAL in TRANSFER or FX_CONVERSION.

        Atomic: delete the original pair + create the new pair in the same
        session. Any failure → rollback and `rolled_back=True`. Caller (router)
        commits only when `rolled_back=False`.
        """
        errors: List[str] = []

        from_tx = await self.session.get(Transaction, req.from_tx_id)
        to_tx = await self.session.get(Transaction, req.to_tx_id)

        if from_tx is None:
            errors.append(f"from_tx_id={req.from_tx_id} not found")
        if to_tx is None:
            errors.append(f"to_tx_id={req.to_tx_id} not found")
        if errors:
            return TXTransferPromoteResponse(rolled_back=True, errors=errors)

        # Access check EDITOR on both brokers (distinct).
        try:
            await self._enforce_batch_access({from_tx.broker_id, to_tx.broker_id}, user_id, min_role=UserRole.EDITOR)
        except HTTPException as e:
            return TXTransferPromoteResponse(rolled_back=True, errors=[e.detail if isinstance(e.detail, str) else str(e.detail)])

        # Pre-check: both current types must be in {DEPOSIT, WITHDRAWAL}.
        cash_pair = {TransactionType.DEPOSIT, TransactionType.WITHDRAWAL}
        if from_tx.type not in cash_pair or to_tx.type not in cash_pair:
            errors.append(f"promote supports only DEPOSIT/WITHDRAWAL pairs (got {from_tx.type.value}+{to_tx.type.value})")

        # new_type-specific checks.
        if req.new_type == TransactionType.TRANSFER:
            if req.asset_id is None or req.quantity is None:
                errors.append("TRANSFER promotion requires asset_id and quantity")
            if from_tx.broker_id == to_tx.broker_id:
                errors.append(f"TRANSFER requires distinct brokers (both on broker {from_tx.broker_id})")
        elif req.new_type == TransactionType.FX_CONVERSION:
            if from_tx.currency == to_tx.currency:
                errors.append(f"FX_CONVERSION requires different currencies (got {from_tx.currency}+{to_tx.currency})")
            if req.asset_id is not None:
                errors.append("FX_CONVERSION promotion must not set asset_id")

        if errors:
            return TXTransferPromoteResponse(rolled_back=True, errors=errors)

        # Snapshot originals before delete (we need broker/date/amount/currency).
        from_broker_id: int = from_tx.broker_id
        from_date: date_type = from_tx.date
        from_amount: Decimal = from_tx.amount
        from_currency: Optional[str] = from_tx.currency
        from_description: Optional[str] = from_tx.description
        from_tags_csv: Optional[str] = from_tx.tags

        to_broker_id: int = to_tx.broker_id
        to_date: date_type = to_tx.date
        to_amount: Decimal = to_tx.amount
        to_currency: Optional[str] = to_tx.currency
        to_description: Optional[str] = to_tx.description
        to_tags_csv: Optional[str] = to_tx.tags

        # Build the new pair.
        link_uuid = str(uuid4())
        from_tags = [t.strip() for t in from_tags_csv.split(",")] if from_tags_csv else None
        to_tags = [t.strip() for t in to_tags_csv.split(",")] if to_tags_csv else None

        if req.new_type == TransactionType.TRANSFER:
            qty = req.quantity
            assert qty is not None
            # Raw dicts (not TXCreateItem) because they go into execute_batch(creates_raw=...)
            # which does per-row model_validate() in try/except, collecting ALL errors
            # in one response instead of failing on the first one.
            create_from_dict = {
                "broker_id": from_broker_id,
                "asset_id": req.asset_id,
                "type": TransactionType.TRANSFER.value,
                "date": from_date.isoformat(),
                "quantity": format(-abs(qty), "f"),
                "link_uuid": link_uuid,
                "tags": from_tags,
                "description": from_description,
            }
            create_to_dict = {
                "broker_id": to_broker_id,
                "asset_id": req.asset_id,
                "type": TransactionType.TRANSFER.value,
                "date": to_date.isoformat(),
                "quantity": format(abs(qty), "f"),
                "link_uuid": link_uuid,
                "tags": to_tags,
                "description": to_description,
                "cost_basis_override": {"code": req.cost_basis_override.code, "amount": format(req.cost_basis_override.amount, "f")} if req.cost_basis_override is not None else None,
            }
        else:  # FX_CONVERSION
            if from_currency is None or to_currency is None:
                return TXTransferPromoteResponse(rolled_back=True, errors=["FX_CONVERSION requires both sides to have a currency"])
            # Raw dicts — same rationale: execute_batch collects all errors in bulk.
            create_from_dict = {
                "broker_id": from_broker_id,
                "type": TransactionType.FX_CONVERSION.value,
                "date": from_date.isoformat(),
                "cash": {"code": from_currency, "amount": format(from_amount, "f")},
                "link_uuid": link_uuid,
                "tags": from_tags,
                "description": from_description,
            }
            create_to_dict = {
                "broker_id": to_broker_id,
                "type": TransactionType.FX_CONVERSION.value,
                "date": to_date.isoformat(),
                "cash": {"code": to_currency, "amount": format(to_amount, "f")},
                "link_uuid": link_uuid,
                "tags": to_tags,
                "description": to_description,
            }

        # Atomic: delete originals + create new pair via unified pipeline.
        resp = await self.execute_batch(
            creates_raw=[create_from_dict, create_to_dict],
            updates_raw=[],
            deletes=[req.from_tx_id, req.to_tx_id],
            user_id=user_id,
            commit=True,
        )

        if resp.issues:
            err_msgs = [iss.error for iss in resp.issues]
            return TXTransferPromoteResponse(rolled_back=True, errors=err_msgs)

        # Extract IDs of the two created transactions.
        new_ids = [r.ids[0] for r in (resp.results or []) if r.operation == "create" and r.ids]
        return TXTransferPromoteResponse(
            rolled_back=False,
            new_from_tx_id=new_ids[0] if len(new_ids) > 0 else None,
            new_to_tx_id=new_ids[1] if len(new_ids) > 1 else None,
        )

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
                    if TransactionService._check_promote_constraints(tx_a, tx_b, rule.field_constraints):
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
        accessible = await self._get_accessible_broker_ids(user_id)
        if not accessible:
            return TXPromoteSuggestResponse(results={})

        # Collect all positive IDs from inputs to exclude self-match
        input_positive_ids: set[int] = {inp.id for inp in inputs if inp.id > 0}

        results: Dict[int, List[TXPromoteSuggestCandidate]] = {}

        for inp in inputs:
            # Determine complementary types from promote_from rules
            complementary: list[tuple[TransactionType, list]] = []
            for _pair_type, meta in TX_TYPE_METADATA.items():
                if meta.promote_from is None:
                    continue
                for rule in meta.promote_from:
                    if inp.type.value == rule.type_a:
                        comp_type = TransactionType(rule.type_b)
                        complementary.append((comp_type, rule.field_constraints))
                    elif inp.type.value == rule.type_b:
                        comp_type = TransactionType(rule.type_a)
                        complementary.append((comp_type, rule.field_constraints))

            if not complementary:
                results[inp.id] = []
                continue

            # Query DB: standalone TX with complementary type, date ±tolerance, accessible broker
            comp_types = list({ct for ct, _ in complementary})
            lo = inp.date - timedelta(days=tolerance_days)
            hi = inp.date + timedelta(days=tolerance_days)

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
                for comp_type, constraints in complementary:
                    if row.type == comp_type:
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

    # =========================================================================
    # UNIFIED BATCH PIPELINE (replaces separate create/update/delete bulk)
    # =========================================================================

    async def execute_batch(
        self,
        creates_raw: List[dict],
        updates_raw: List[dict],
        deletes: List[int],
        splits_raw: List[dict] | None = None,
        promotes_raw: List[dict] | None = None,
        user_id: Optional[int] = None,
        commit: bool = False,
    ) -> TXBatchResponse:
        """Unified pipeline for both /validate (commit=False) and /commit (commit=True).

        Order: parse → access → delete → split → update → create → promote →
        link → WAC → cost basis → balance replay → response.

        ``commit`` selects response semantics only. The caller still owns the
        session commit or rollback.
        """
        context = TransactionBatchContext.from_inputs(
            creates_raw=creates_raw,
            updates_raw=updates_raw,
            deletes=deletes,
            splits_raw=splits_raw,
            promotes_raw=promotes_raw,
            user_id=user_id,
            commit_requested=commit,
        )

        parse_inputs(context)
        if await preload_and_authorize(self, context):
            return TXBatchResponse(
                committed=False,
                issues=context.issues,
                results=[],
                success_count=0,
            )

        await apply_deletes(self, context)
        await apply_splits(self, context)
        await apply_updates(self, context)
        await validate_updated_pairs(self, context)

        await apply_creates(self, context)
        await apply_promotes(self, context)
        resolve_create_links(self, context)

        await compute_wac_and_fx_issues(self, context)
        await validate_cost_basis(self, context)
        await validate_balances(self, context)
        return finalize_response(context)

    # =========================================================================
    # WAC AUTO-COMPUTATION (inline in validate/commit)
    # =========================================================================

    async def _compute_wac_for_auto_items(  # noqa: C901 — per-item WAC dispatch loop, sequential checks
        self,
        parsed_creates: list[tuple[int, TXCreateItem]],
        parsed_updates: list[tuple[int, TXUpdateItem]],
        link_uuid_map: dict[str, list[tuple[int, Transaction]]],
    ) -> list[WACPreviewResultItem] | None:
        """Compute WAC for items with cost_basis_mode in ('auto', 'auto-detail').

        Called post-flush: all rows are in the session (not committed).
        For TRANSFER (has link_uuid): source broker = partner's broker_id.
        For ADJUSTMENT (no link_uuid): source broker = own broker_id, exclude self.

        Returns list of WACPreviewResultItem with batch-context fields populated
        (operation, index, source_broker_id).
        """
        # Collect auto items: (operation, orig_idx, schema_item, db_tx)
        auto_items: list[tuple[str, int, TXCreateItem | TXUpdateItem, Transaction]] = []

        for orig_idx, item in parsed_creates:
            if getattr(item, "cost_basis_mode", None) in ("auto", "auto-detail"):
                # Find the flushed Transaction row by matching in link_uuid_map or by query
                tx = await self._find_created_tx_for_wac(item, link_uuid_map, orig_idx)
                if tx:
                    auto_items.append(("create", orig_idx, item, tx))

        for orig_idx, item in parsed_updates:
            if getattr(item, "cost_basis_mode", None) in ("auto", "auto-detail"):
                tx = await self.session.get(Transaction, item.id)
                if tx:
                    auto_items.append(("update", orig_idx, item, tx))

        if not auto_items:
            return None

        results: list[WACPreviewResultItem] = []

        for operation, idx, schema_item, db_tx in auto_items:
            # Determine source broker
            link_uuid = getattr(schema_item, "link_uuid", None)
            if link_uuid:
                # TRANSFER: find partner via link_uuid_map → use partner's broker_id
                source_broker_id = self._resolve_source_broker_from_link(link_uuid, db_tx.id, link_uuid_map)
            else:
                # ADJUSTMENT standalone: own broker, exclude self
                source_broker_id = db_tx.broker_id

            # SPLIT-linked ADJUSTMENT: cost is derived live from the ratio at WAC/FIFO
            # computation time (wac_utils.compute_wac_from_txlist / portfolio_engine.py
            # split-rescale path), never from a stored override. Writing "current WAC
            # before this tx" here — the normal auto-mode fallback — would double the
            # cost basis for a forward split (or halve it for a reverse split). Skip.
            is_split_linked = False
            if db_tx.asset_event_id is not None:
                event_type = (await self.session.execute(select(AssetEvent.type).where(AssetEvent.id == db_tx.asset_event_id))).scalar_one_or_none()
                is_split_linked = event_type == AssetEventType.SPLIT

            if is_split_linked:
                db_tx.cost_basis_override = None
                db_tx.cost_basis_currency = None
                results.append(
                    WACPreviewResultItem(
                        operation=operation,
                        index=idx,
                        source_broker_id=source_broker_id,
                        wac=None,
                        wac_qualifying_txs=[],
                        wac_missing_pairs=[],
                    )
                )
                continue

            # Get asset currency
            asset_result = await self.session.execute(select(Asset.currency).where(Asset.id == db_tx.asset_id))
            asset_currency = asset_result.scalar_one_or_none() or "USD"

            # Compute WAC (session sees all flushed rows)
            excluded = [db_tx.id] if not link_uuid else []

            # Extract currency hint from cost_basis_override when mode is auto
            ccy_hint: str | None = None
            if getattr(schema_item, "cost_basis_override", None) is not None:
                ccy_hint = schema_item.cost_basis_override.code

            wac_result = await compute_wac_iterative(
                self.session,
                broker_id=source_broker_id,
                asset_id=db_tx.asset_id,
                as_of_date=db_tx.date,
                asset_currency=asset_currency,
                excluded_tx_ids=excluded if excluded else None,
                target_currency_override=ccy_hint,
            )

            # Write cost_basis_override on the DB row
            if wac_result.wac:
                db_tx.cost_basis_override = wac_result.wac.amount
                db_tx.cost_basis_currency = wac_result.wac.code

            # Build response item (reuse WACPreviewResultItem with batch-context fields)
            is_detail = getattr(schema_item, "cost_basis_mode", None) == "auto-detail"
            results.append(
                WACPreviewResultItem(
                    operation=operation,
                    index=idx,
                    source_broker_id=source_broker_id,
                    wac=wac_result.wac,
                    wac_qualifying_txs=wac_result.wac_qualifying_txs if is_detail else [],
                    wac_missing_pairs=wac_result.wac_missing_pairs,
                    asset_price=wac_result.asset_price if is_detail else None,
                    asset_price_stale=wac_result.asset_price_stale if is_detail else None,
                    asset_price_missing=wac_result.asset_price_missing if is_detail else False,
                )
            )

        return results if results else None

    async def _find_created_tx_for_wac(
        self,
        item: TXCreateItem,
        link_uuid_map: dict[str, list[tuple[int, Transaction]]],
        orig_idx: int,
    ) -> Transaction | None:
        """Find the flushed Transaction DB row for a created item."""
        if item.link_uuid and item.link_uuid in link_uuid_map:
            # Find in link_uuid_map by matching orig_idx
            for map_idx, tx in link_uuid_map[item.link_uuid]:
                if map_idx == orig_idx:
                    return tx
        # Fallback: query by matching fields (last resort)
        stmt = (
            select(Transaction)
            .where(
                Transaction.broker_id == item.broker_id,
                Transaction.asset_id == item.asset_id,
                Transaction.date == item.date,
                Transaction.type == item.type,
            )
            .order_by(Transaction.id.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    def _resolve_source_broker_from_link(
        self,
        link_uuid: str,
        self_id: int,
        link_uuid_map: dict[str, list[tuple[int, Transaction]]],
    ) -> int:
        """For a TRANSFER with link_uuid, find the partner's broker_id (source)."""
        if link_uuid in link_uuid_map:
            pairs = link_uuid_map[link_uuid]
            for _, tx in pairs:
                if tx.id != self_id:
                    return tx.broker_id
        # Fallback: if partner not found in map, use own broker
        # This shouldn't happen in a valid batch but is safe.
        for _, tx in link_uuid_map.get(link_uuid, []):
            if tx.id == self_id:
                return tx.broker_id
        return 0  # Should never reach here
