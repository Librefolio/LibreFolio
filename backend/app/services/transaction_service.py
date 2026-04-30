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
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, UserRole
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import (
    EVENT_COMPATIBLE_TYPES,
    TXBatchResponse,
    TXBatchResultItem,
    TXCreateItem,
    TXEventSuggestCandidate,
    TXEventSuggestRequestItem,
    TXEventSuggestResultItem,
    TXQueryParams,
    TXReadItem,
    TXTransferPromoteRequest,
    TXTransferPromoteResponse,
    TXUpdateItem,
    TXValidationIssue,
    tags_to_csv,
)
from backend.app.utils.datetime_utils import utcnow


class BalanceValidationError(Exception):
    """Raised when a balance validation fails."""

    def __init__(
        self,
        broker_id: int,
        date: date_type,
        currency_or_asset: str,
        balance: Decimal,
        message: str,
        code: str = "",
        params: dict | None = None,
    ):
        self.broker_id = broker_id
        self.date = date
        self.currency_or_asset = currency_or_asset
        self.balance = balance
        self.code = code
        self.params = params or {}
        super().__init__(message)


class LinkedTransactionError(Exception):
    """Raised when linked transaction operations fail."""

    pass


def _loc_to_field(loc: tuple | list) -> Optional[str]:
    """Convert Pydantic loc tuple to a dotted field path string."""
    parts = [str(p) for p in loc if not isinstance(p, int)]
    return ".".join(parts) if parts else None


def _parse_lenient(
    raw_list: List[dict],
    model_class: type,
    operation: str,
) -> Tuple[List[Tuple[int, Any]], List[TXValidationIssue]]:
    """Per-row model_validate with error collection.

    Returns (parsed_items, issues) where parsed_items is a list of (index, model)
    tuples for successfully-parsed rows, and issues contains all schema/business
    errors from rows that failed validation.
    """
    parsed: List[Tuple[int, Any]] = []
    issues: List[TXValidationIssue] = []
    for idx, raw in enumerate(raw_list):
        try:
            parsed.append((idx, model_class.model_validate(raw)))
        except ValidationError as e:
            for err in e.errors():
                # Handle packed multi-error from model_validator
                if err.get("type") == "multipleBusinessRuleErrors":
                    ctx = err.get("ctx", {})
                    sub_errors = ctx.get("errors", [])
                    for sub in sub_errors:
                        # sub.ctx is always our own PydanticCustomError context
                        # (e.g. {"type": "BUY"}) — safe to pass as-is.
                        issues.append(
                            TXValidationIssue(
                                operation=operation,
                                index=idx,
                                error=sub.get("msg", ""),
                                code=sub.get("code"),
                                params=sub.get("ctx") or None,
                                field=None,
                            )
                        )
                    continue
                # Standard Pydantic errors: ctx can contain non-serializable
                # objects (e.g. {'error': ValueError('...')}), so we don't
                # forward it as params.  The error message already carries the
                # human-readable description; `code` = Pydantic error type
                # (e.g. "value_error", "missing"); `field` pinpoints the loc.
                issues.append(
                    TXValidationIssue(
                        operation=operation,
                        index=idx,
                        error=err.get("msg", str(err)),
                        code=err.get("type"),
                        params=None,
                        field=_loc_to_field(err.get("loc", ())),
                    )
                )
    return parsed, issues


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
    def _validate_linked_pair(a: Transaction, b: Transaction) -> Optional[tuple[str, str, dict]]:
        """
        Validate semantic coherence of a linked pair (Block H.1).

        Rules:
        - Both items must share the same `type` (no mixing e.g. TRANSFER + SELL).
        - TRANSFER requires distinct brokers (same-broker TRANSFER is a no-op).
        - FX_CONVERSION intra-broker is allowed (multi-currency account use case).
        - DEPOSIT/WITHDRAWAL linked pairs are allowed as "intent markers" for
          cash movements between the user's own brokers (Block H.2).

        Returns None when the pair is valid, otherwise a tuple of
        (error_message, code, params).
        """
        if a.type != b.type:
            # W34: Allow WITHDRAWAL↔DEPOSIT pairs (cash transfer / "Bonifico").
            # These are deliberately different types linked to represent a cash
            # movement between the user's own brokers (Block H.2).
            valid_mixed = {
                frozenset({TransactionType.WITHDRAWAL, TransactionType.DEPOSIT}),
            }
            if frozenset({a.type, b.type}) not in valid_mixed:
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
        return None

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def query(self, params: TXQueryParams, user_id: Optional[int] = None) -> List[TXReadItem]:
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
            return [TXReadItem.from_db_model(tx) for tx in ordered]

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
        stmt = stmt.offset(params.offset).limit(params.limit)

        result = await self.session.execute(stmt)
        return [TXReadItem.from_db_model(tx) for tx in result.scalars().all()]

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

        count = 0
        for tx in txs:
            await self.session.delete(tx)
            count += 1

        return count

    # =========================================================================
    # BALANCE VALIDATION
    # =========================================================================

    async def _validate_broker_balances(self, broker_id: int, from_date: Optional[date_type] = None) -> None:
        """Validate cash and asset balances for a broker from a given date."""
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

        txs_by_date: Dict[date_type, List[Transaction]] = defaultdict(list)
        for tx in txs:
            txs_by_date[tx.date].append(tx)

        current_date = min(txs_by_date.keys()) if from_date is None else from_date
        end_date = max(txs_by_date.keys())

        while current_date <= end_date:
            for tx in txs_by_date.get(current_date, []):
                if tx.amount != Decimal("0") and tx.currency:
                    cash_balances[tx.currency] = cash_balances.get(tx.currency, Decimal("0")) + tx.amount
                if tx.quantity != Decimal("0") and tx.asset_id:
                    asset_balances[tx.asset_id] = asset_balances.get(tx.asset_id, Decimal("0")) + tx.quantity

            if not broker.allow_cash_overdraft:
                for currency, balance in cash_balances.items():
                    if balance < Decimal("0"):
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=currency,
                            balance=balance,
                            message=f"Cash balance for {currency} goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code="balanceCashNegative",
                            params={"brokerId": broker_id, "currency": currency, "balance": str(balance), "date": str(current_date)},
                        )

            if not broker.allow_asset_shorting:
                for asset_id, balance in asset_balances.items():
                    if balance < Decimal("0"):
                        raise BalanceValidationError(
                            broker_id=broker_id,
                            date=current_date,
                            currency_or_asset=f"asset:{asset_id}",
                            balance=balance,
                            message=f"Asset {asset_id} quantity goes negative ({balance}) on {current_date} for broker {broker_id}",
                            code="balanceAssetNegative",
                            params={"brokerId": broker_id, "assetId": asset_id, "balance": str(balance), "date": str(current_date)},
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

    async def promote_transfer(
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
            create_from_dict = {
                "broker_id": from_broker_id,
                "asset_id": req.asset_id,
                "type": TransactionType.TRANSFER.value,
                "date": from_date.isoformat(),
                "quantity": str(-abs(qty)),
                "link_uuid": link_uuid,
                "tags": from_tags,
                "description": from_description,
            }
            create_to_dict = {
                "broker_id": to_broker_id,
                "asset_id": req.asset_id,
                "type": TransactionType.TRANSFER.value,
                "date": to_date.isoformat(),
                "quantity": str(abs(qty)),
                "link_uuid": link_uuid,
                "tags": to_tags,
                "description": to_description,
                "cost_basis_override": str(req.cost_basis_override) if req.cost_basis_override is not None else None,
            }
        else:  # FX_CONVERSION
            if from_currency is None or to_currency is None:
                return TXTransferPromoteResponse(rolled_back=True, errors=["FX_CONVERSION requires both sides to have a currency"])
            create_from_dict = {
                "broker_id": from_broker_id,
                "type": TransactionType.FX_CONVERSION.value,
                "date": from_date.isoformat(),
                "cash": {"code": from_currency, "amount": str(from_amount)},
                "link_uuid": link_uuid,
                "tags": from_tags,
                "description": from_description,
            }
            create_to_dict = {
                "broker_id": to_broker_id,
                "type": TransactionType.FX_CONVERSION.value,
                "date": to_date.isoformat(),
                "cash": {"code": to_currency, "amount": str(to_amount)},
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
        new_ids = [r.id for r in (resp.results or []) if r.operation == "create"]
        return TXTransferPromoteResponse(
            rolled_back=False,
            new_from_tx_id=new_ids[0] if len(new_ids) > 0 else None,
            new_to_tx_id=new_ids[1] if len(new_ids) > 1 else None,
        )

    # =========================================================================
    # UNIFIED BATCH PIPELINE (replaces separate create/update/delete bulk)
    # =========================================================================

    async def execute_batch(
        self,
        creates_raw: List[dict],
        updates_raw: List[dict],
        deletes: List[int],
        user_id: Optional[int] = None,
        commit: bool = False,
    ) -> TXBatchResponse:
        """Unified pipeline for both /validate (commit=False) and /commit (commit=True).

        Order: lenient parse → access check → deletes → updates → creates →
        link resolution → balance walk → commit/rollback.

        Always collects the full set of issues instead of failing fast.
        """
        issues: List[TXValidationIssue] = []
        results: List[TXBatchResultItem] = []

        # 1. Lenient per-row parse
        parsed_creates, create_issues = _parse_lenient(creates_raw, TXCreateItem, "create")
        parsed_updates, update_issues = _parse_lenient(updates_raw, TXUpdateItem, "update")
        issues.extend(create_issues)
        issues.extend(update_issues)

        # 2. Determine touched brokers for access check
        touched_brokers: Set[int] = set()
        for _, item in parsed_creates:
            touched_brokers.add(item.broker_id)

        # Lookup existing TXs for updates and deletes
        ids_to_lookup: Set[int] = set(deletes)
        for _, item in parsed_updates:
            ids_to_lookup.add(item.id)
        existing_by_id: Dict[int, Transaction] = {}
        if ids_to_lookup:
            existing_txs = await self.get_by_ids(list(ids_to_lookup))
            existing_by_id = {tx.id: tx for tx in existing_txs}
            touched_brokers |= {tx.broker_id for tx in existing_txs}

        # Access check (EDITOR) — report as issues, not HTTPException
        if user_id is not None:
            for broker_id in touched_brokers:
                role = await self._check_broker_access(broker_id, user_id, min_role=UserRole.EDITOR)
                if role is None:
                    issues.append(
                        TXValidationIssue(
                            operation="create",
                            index=0,
                            ref_id=None,
                            error=f"Access denied: EDITOR required for broker {broker_id}",
                            code="accessDenied",
                            params={"brokerId": broker_id},
                        )
                    )

        # If access denied, stop early
        if any(i.code == "accessDenied" for i in issues):
            return TXBatchResponse(committed=False, issues=issues)

        earliest_date_by_broker: Dict[int, date_type] = {}

        # 3. Apply deletes
        id_set_deletes = set(deletes)
        for idx, tx_id in enumerate(deletes):
            tx = existing_by_id.get(tx_id)
            if tx is None:
                issues.append(TXValidationIssue(operation="delete", index=idx, ref_id=tx_id, error=f"Transaction {tx_id} not found", code="txNotFound", params={"id": tx_id}))
                continue
            # Linked-pair integrity check
            if tx.related_transaction_id and tx.related_transaction_id not in id_set_deletes:
                issues.append(
                    TXValidationIssue(
                        operation="delete",
                        index=idx,
                        ref_id=tx_id,
                        error=f"Cannot delete linked transaction {tx_id} without its pair {tx.related_transaction_id}",
                        code="pairDeleteIncomplete",
                        params={"id": tx_id, "partnerId": tx.related_transaction_id},
                    )
                )
                continue
            try:
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = tx.date if prev is None else min(prev, tx.date)
                await self.session.delete(tx)
                results.append(TXBatchResultItem(operation="delete", index=idx, id=tx_id, status="success"))
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="delete", index=idx, ref_id=tx_id, error=str(e)))

        # 4. Apply updates (only successfully-parsed rows)
        for orig_idx, item in parsed_updates:
            tx = existing_by_id.get(item.id)
            if tx is None:
                issues.append(TXValidationIssue(operation="update", index=orig_idx, ref_id=item.id, error=f"Transaction {item.id} not found", code="txNotFound", params={"id": item.id}))
                continue
            try:
                check_date = tx.date
                if item.date is not None:
                    check_date = min(check_date, item.date)
                    tx.date = item.date
                if item.quantity is not None:
                    tx.quantity = item.quantity
                if item.cash is not None:
                    tx.amount = item.cash.amount
                    tx.currency = item.cash.code
                if item.tags is not None:
                    tx.tags = tags_to_csv(item.tags)
                if item.description is not None:
                    tx.description = item.description
                if item.cost_basis_override is not None:
                    tx.cost_basis_override = item.cost_basis_override
                if item.asset_event_id is not None:
                    if item.asset_event_id == 0:
                        tx.asset_event_id = None
                    else:
                        if tx.asset_id is None:
                            raise ValueError("Cannot link asset_event_id: transaction has no asset_id")
                        await self._validate_asset_event_link(item.asset_event_id, tx.asset_id)
                        tx.asset_event_id = item.asset_event_id
                tx.updated_at = utcnow()
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = check_date if prev is None else min(prev, check_date)
                results.append(TXBatchResultItem(operation="update", index=orig_idx, id=item.id, status="success"))
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="update", index=orig_idx, ref_id=item.id, error=str(e)))

        # 5. Apply creates (only successfully-parsed rows)
        link_uuid_map: Dict[str, List[Tuple[int, Transaction]]] = defaultdict(list)
        for orig_idx, item in parsed_creates:
            try:
                if item.asset_id is not None:
                    asset_result = await self.session.execute(select(Asset.asset_type).where(Asset.id == item.asset_id))
                    if asset_result.scalar_one_or_none() == AssetType.INDEX:
                        raise ValueError("Cannot create transactions for INDEX assets")
                if item.asset_event_id is not None:
                    assert item.asset_id is not None
                    await self._validate_asset_event_link(item.asset_event_id, item.asset_id)
                tx = Transaction(
                    broker_id=item.broker_id,
                    asset_id=item.asset_id,
                    type=item.type,
                    date=item.date,
                    quantity=item.quantity,
                    amount=item.get_amount(),
                    currency=item.get_currency(),
                    tags=item.get_tags_csv(),
                    description=item.description,
                    cost_basis_override=item.cost_basis_override,
                    asset_event_id=item.asset_event_id,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                self.session.add(tx)
                await self.session.flush()
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = tx.date if prev is None else min(prev, tx.date)
                if item.link_uuid:
                    link_uuid_map[item.link_uuid].append((orig_idx, tx))
                results.append(TXBatchResultItem(operation="create", index=orig_idx, id=tx.id, link_uuid=item.link_uuid, status="success"))
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="create", index=orig_idx, ref_id=None, error=str(e)))

        # 6. Link resolution
        for link_uuid, pairs in link_uuid_map.items():
            if len(pairs) == 2:
                pair_result = self._validate_linked_pair(pairs[0][1], pairs[1][1])
                if pair_result is not None:
                    pair_error, pair_code, pair_params = pair_result
                    issues.append(TXValidationIssue(operation="create", index=pairs[0][0], ref_id=None, error=pair_error, code=pair_code, params=pair_params))
                    continue
                pairs[0][1].related_transaction_id = pairs[1][1].id
                pairs[1][1].related_transaction_id = pairs[0][1].id
            else:
                issues.append(
                    TXValidationIssue(
                        operation="create",
                        index=pairs[0][0] if pairs else 0,
                        ref_id=None,
                        error=f"link_uuid '{link_uuid}' has {len(pairs)} creates (expected 2)",
                        code="linkUuidPairCount",
                        params={"linkUuid": link_uuid, "count": len(pairs)},
                    )
                )

        # 7. Balance walk per affected broker
        try:
            await self.session.flush()
            for broker_id, from_date in earliest_date_by_broker.items():
                await self._validate_broker_balances(broker_id, from_date)
        except BalanceValidationError as e:
            issues.append(TXValidationIssue(operation="create", index=-1, ref_id=None, error=str(e), code=e.code, params=e.params))
        except Exception as e:  # noqa: BLE001
            issues.append(TXValidationIssue(operation="create", index=-1, ref_id=None, error=f"Balance validation error: {e}"))

        # 8. Decision
        if issues:
            return TXBatchResponse(committed=False, issues=issues)
        elif not commit:
            # Dry-run: clean batch but caller requested validate-only
            return TXBatchResponse(committed=False, issues=[], results=results)
        else:
            # Commit: caller (router) will session.commit()
            return TXBatchResponse(committed=True, issues=[], results=results)

