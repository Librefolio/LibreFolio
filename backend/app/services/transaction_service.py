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

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetEvent, AssetType, Broker, BrokerUserAccess, Transaction, TransactionType, UserRole
from backend.app.schemas.transactions import (
    TXBulkCreateResponse,
    TXBulkDeleteResponse,
    TXBulkUpdateResponse,
    TXCreateItem,
    TXCreateResultItem,
    TXDeleteResult,
    TXQueryParams,
    TXReadItem,
    TXUpdateItem,
    TXUpdateResultItem,
    TXValidateResponse,
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
    ):
        self.broker_id = broker_id
        self.date = date
        self.currency_or_asset = currency_or_asset
        self.balance = balance
        super().__init__(message)


class LinkedTransactionError(Exception):
    """Raised when linked transaction operations fail."""

    pass


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

    # =========================================================================
    # ATOMIC ROLLBACK HELPER
    # =========================================================================

    def _mark_rolled_back(self, results: list) -> None:
        """
        Downgrade any `success` results to `simulated`.

        NOTE: this method does NOT call `session.rollback()` — the router
        owns the session lifecycle and will roll back when the response
        carries `rolled_back=True`. Keeping rollback in the router avoids
        interfering with FastAPI's dependency-managed session greenlet
        (otherwise aiosqlite may raise MissingGreenlet on subsequent cleanup).
        """
        for r in results:
            if getattr(r, "status", None) == "success":
                r.success = False
                r.status = "simulated"

    # =========================================================================
    # CREATE OPERATIONS
    # =========================================================================

    async def create_bulk(self, items: List[TXCreateItem], user_id: Optional[int] = None) -> TXBulkCreateResponse:
        """
        Atomic multi-broker bulk create.

        Semantics:
        1. Access check EDITOR on every distinct `broker_id` touched.
        2. Insert all transactions + bidirectional `link_uuid` pairing (DEFERRABLE FK).
           TRANSFER cross-broker is supported.
        3. Balance validation per affected broker.
        4. On ANY failure → full rollback, `rolled_back=True`, `success_count=0`.
        """
        n = len(items)
        results: List[TXCreateResultItem] = [TXCreateResultItem(success=False, status="not_attempted", link_uuid=it.link_uuid) for it in items]

        if n == 0:
            return TXBulkCreateResponse(results=results, success_count=0, errors=[])

        # Access check once per distinct broker.
        await self._enforce_batch_access({it.broker_id for it in items}, user_id, min_role=UserRole.EDITOR)

        link_uuid_map: Dict[str, List[Transaction]] = defaultdict(list)
        earliest_date_by_broker: Dict[int, date_type] = {}

        # Phase 1: Insert.
        failure_reason: Optional[str] = None

        for idx, item in enumerate(items):
            try:
                # Reject INDEX assets (benchmarks, not tradeable).
                if item.asset_id is not None:
                    asset_result = await self.session.execute(select(Asset.asset_type).where(Asset.id == item.asset_id))
                    if asset_result.scalar_one_or_none() == AssetType.INDEX:
                        raise ValueError("Cannot create transactions for INDEX assets")

                if item.asset_event_id is not None:
                    assert item.asset_id is not None  # guaranteed by Pydantic Rule 9
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
                    link_uuid_map[item.link_uuid].append(tx)

                results[idx] = TXCreateResultItem(
                    success=True,
                    status="success",
                    transaction_id=tx.id,
                    link_uuid=item.link_uuid,
                )
            except Exception as e:  # noqa: BLE001
                failure_reason = str(e)
                results[idx] = TXCreateResultItem(success=False, status="failed", link_uuid=item.link_uuid, error=failure_reason)
                break

        if failure_reason is not None:
            self._mark_rolled_back(results)
            return TXBulkCreateResponse(results=results, success_count=0, errors=[failure_reason], rolled_back=True)

        # Phase 2: Bidirectional link resolution.
        link_errors: List[str] = []
        for link_uuid, txs in link_uuid_map.items():
            if len(txs) == 2:
                txs[0].related_transaction_id = txs[1].id
                txs[1].related_transaction_id = txs[0].id
            else:
                link_errors.append(f"link_uuid '{link_uuid}' has {len(txs)} transactions (expected 2)")

        if link_errors:
            self._mark_rolled_back(results)
            return TXBulkCreateResponse(results=results, success_count=0, errors=link_errors, rolled_back=True)

        # Phase 3: Balance validation per affected broker.
        try:
            for broker_id, from_date in earliest_date_by_broker.items():
                await self._validate_broker_balances(broker_id, from_date)
        except BalanceValidationError as e:
            self._mark_rolled_back(results)
            return TXBulkCreateResponse(results=results, success_count=0, errors=[str(e)], rolled_back=True)
        except Exception as e:  # noqa: BLE001
            self._mark_rolled_back(results)
            return TXBulkCreateResponse(results=results, success_count=0, errors=[f"Balance validation error: {e}"], rolled_back=True)

        success_count = sum(1 for r in results if r.status == "success")
        return TXBulkCreateResponse(results=results, success_count=success_count, errors=[], rolled_back=False)

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
    # UPDATE OPERATIONS
    # =========================================================================

    async def update_bulk(self, items: List[TXUpdateItem], user_id: Optional[int] = None) -> TXBulkUpdateResponse:
        """Atomic multi-broker bulk update."""
        n = len(items)
        results: List[TXUpdateResultItem] = [TXUpdateResultItem(id=it.id, success=False, status="not_attempted") for it in items]

        if n == 0:
            return TXBulkUpdateResponse(results=results, success_count=0, errors=[])

        # Resolve broker ownership of targets up front → access check.
        existing = {tx.id: tx for tx in await self.get_by_ids([it.id for it in items])}
        await self._enforce_batch_access({tx.broker_id for tx in existing.values()}, user_id, min_role=UserRole.EDITOR)

        earliest_date_by_broker: Dict[int, date_type] = {}
        failure_reason: Optional[str] = None

        for idx, item in enumerate(items):
            try:
                tx = existing.get(item.id)
                if tx is None:
                    raise ValueError(f"Transaction {item.id} not found")

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

                # asset_event_id sentinel: None = unchanged, 0 = unlink, >0 = link.
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

                results[idx] = TXUpdateResultItem(id=item.id, success=True, status="success")
            except Exception as e:  # noqa: BLE001
                failure_reason = str(e)
                results[idx] = TXUpdateResultItem(id=item.id, success=False, status="failed", error=failure_reason)
                break

        if failure_reason is not None:
            self._mark_rolled_back(results)
            return TXBulkUpdateResponse(results=results, success_count=0, errors=[failure_reason], rolled_back=True)

        await self.session.flush()

        try:
            for broker_id, from_date in earliest_date_by_broker.items():
                await self._validate_broker_balances(broker_id, from_date)
        except BalanceValidationError as e:
            self._mark_rolled_back(results)
            return TXBulkUpdateResponse(results=results, success_count=0, errors=[str(e)], rolled_back=True)
        except Exception as e:  # noqa: BLE001
            self._mark_rolled_back(results)
            return TXBulkUpdateResponse(results=results, success_count=0, errors=[f"Balance validation error: {e}"], rolled_back=True)

        success_count = sum(1 for r in results if r.status == "success")
        return TXBulkUpdateResponse(results=results, success_count=success_count, errors=[], rolled_back=False)

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    async def delete_bulk(self, ids: List[int], user_id: Optional[int] = None) -> TXBulkDeleteResponse:
        """Atomic multi-broker bulk delete."""
        n = len(ids)
        results: List[TXDeleteResult] = [TXDeleteResult(id=i, success=False, deleted_count=0, status="not_attempted", message=None) for i in ids]

        if n == 0:
            return TXBulkDeleteResponse(results=results, success_count=0, total_deleted=0, errors=[])

        id_set: Set[int] = set(ids)
        existing = {tx.id: tx for tx in await self.get_by_ids(list(id_set))}

        await self._enforce_batch_access({tx.broker_id for tx in existing.values()}, user_id, min_role=UserRole.EDITOR)

        idx_by_id = {i: k for k, i in enumerate(ids)}
        failure_reason: Optional[str] = None

        # Pre-check linked-pair integrity.
        for tx in existing.values():
            assert tx.id is not None  # persisted row
            if tx.related_transaction_id and tx.related_transaction_id not in id_set:
                failure_reason = f"Cannot delete linked transaction {tx.id} without its pair " f"{tx.related_transaction_id}. Include both IDs in the delete request."
                fi = idx_by_id[tx.id]
                results[fi] = TXDeleteResult(id=tx.id, success=False, deleted_count=0, status="failed", message=failure_reason)
                break
            stmt = select(Transaction).where(Transaction.related_transaction_id == tx.id)
            related = (await self.session.execute(stmt)).scalar_one_or_none()
            if related and related.id not in id_set:
                failure_reason = f"Cannot delete linked transaction {tx.id} without its pair " f"{related.id}. Include both IDs in the delete request."
                fi = idx_by_id[tx.id]
                results[fi] = TXDeleteResult(id=tx.id, success=False, deleted_count=0, status="failed", message=failure_reason)
                break

        if failure_reason is not None:
            self._mark_rolled_back(results)
            return TXBulkDeleteResponse(results=results, success_count=0, total_deleted=0, errors=[failure_reason], rolled_back=True)

        # All ids must exist.
        for idx, tx_id in enumerate(ids):
            if tx_id not in existing:
                failure_reason = f"Transaction {tx_id} not found"
                results[idx] = TXDeleteResult(id=tx_id, success=False, deleted_count=0, status="failed", message=failure_reason)
                break

        if failure_reason is not None:
            self._mark_rolled_back(results)
            return TXBulkDeleteResponse(results=results, success_count=0, total_deleted=0, errors=[failure_reason], rolled_back=True)

        earliest_date_by_broker: Dict[int, date_type] = {}
        total_deleted = 0

        for idx, tx_id in enumerate(ids):
            try:
                tx = existing[tx_id]
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = tx.date if prev is None else min(prev, tx.date)
                await self.session.delete(tx)
                total_deleted += 1
                results[idx] = TXDeleteResult(id=tx_id, success=True, deleted_count=1, status="success", message=None)
            except Exception as e:  # noqa: BLE001
                failure_reason = str(e)
                results[idx] = TXDeleteResult(id=tx_id, success=False, deleted_count=0, status="failed", message=failure_reason)
                break

        if failure_reason is not None:
            self._mark_rolled_back(results)
            return TXBulkDeleteResponse(results=results, success_count=0, total_deleted=0, errors=[failure_reason], rolled_back=True)

        await self.session.flush()

        try:
            for broker_id, from_date in earliest_date_by_broker.items():
                await self._validate_broker_balances(broker_id, from_date)
        except BalanceValidationError as e:
            self._mark_rolled_back(results)
            return TXBulkDeleteResponse(results=results, success_count=0, total_deleted=0, errors=[str(e)], rolled_back=True)
        except Exception as e:  # noqa: BLE001
            self._mark_rolled_back(results)
            return TXBulkDeleteResponse(results=results, success_count=0, total_deleted=0, errors=[f"Balance validation error: {e}"], rolled_back=True)

        success_count = sum(1 for r in results if r.status == "success")
        return TXBulkDeleteResponse(results=results, success_count=success_count, total_deleted=total_deleted, errors=[], rolled_back=False)

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
    # VALIDATE (DRY-RUN MIXED BATCH)
    # =========================================================================

    async def validate_batch(
        self,
        creates: List[TXCreateItem],
        updates: List[TXUpdateItem],
        deletes: List[int],
        user_id: Optional[int] = None,
    ) -> TXValidateResponse:
        """
        Dry-run engine for POST /transactions/validate.

        Order: deletes → updates → creates (so creates see DB post-cleanup).
        Does NOT stop at the first error — collects the full set of issues for
        the Staging UI. Always rolls back at the end; never commits.
        """
        issues: List[TXValidationIssue] = []

        # Determine touched brokers for access check.
        touched_brokers: Set[int] = {c.broker_id for c in creates}
        if updates or deletes:
            ids_to_lookup = {u.id for u in updates} | set(deletes)
            existing_txs = await self.get_by_ids(list(ids_to_lookup))
            existing_by_id = {tx.id: tx for tx in existing_txs}
            touched_brokers |= {tx.broker_id for tx in existing_txs}
        else:
            existing_by_id = {}

        # Access check (EDITOR) — report as issue rather than HTTPException.
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
                        )
                    )

        if issues:
            await self.session.rollback()
            return TXValidateResponse(would_rollback=True, issues=issues)

        earliest_date_by_broker: Dict[int, date_type] = {}

        # --- deletes ---
        for idx, tx_id in enumerate(deletes):
            tx = existing_by_id.get(tx_id)
            if tx is None:
                issues.append(TXValidationIssue(operation="delete", index=idx, ref_id=tx_id, error=f"Transaction {tx_id} not found"))
                continue
            try:
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = tx.date if prev is None else min(prev, tx.date)
                await self.session.delete(tx)
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="delete", index=idx, ref_id=tx_id, error=str(e)))

        # --- updates ---
        for idx, item in enumerate(updates):
            tx = existing_by_id.get(item.id)
            if tx is None:
                issues.append(TXValidationIssue(operation="update", index=idx, ref_id=item.id, error=f"Transaction {item.id} not found"))
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
                prev = earliest_date_by_broker.get(tx.broker_id)
                earliest_date_by_broker[tx.broker_id] = check_date if prev is None else min(prev, check_date)
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="update", index=idx, ref_id=item.id, error=str(e)))

        # --- creates ---
        link_uuid_map: Dict[str, List[Transaction]] = defaultdict(list)
        for idx, item in enumerate(creates):
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
                    link_uuid_map[item.link_uuid].append(tx)
            except Exception as e:  # noqa: BLE001
                issues.append(TXValidationIssue(operation="create", index=idx, ref_id=None, error=str(e)))

        for link_uuid, pair in link_uuid_map.items():
            if len(pair) == 2:
                pair[0].related_transaction_id = pair[1].id
                pair[1].related_transaction_id = pair[0].id
            else:
                issues.append(TXValidationIssue(operation="create", index=0, ref_id=None, error=f"link_uuid '{link_uuid}' has {len(pair)} creates (expected 2)"))

        balance_violation = False
        try:
            await self.session.flush()
            for broker_id, from_date in earliest_date_by_broker.items():
                await self._validate_broker_balances(broker_id, from_date)
        except BalanceValidationError as e:
            balance_violation = True
            issues.append(TXValidationIssue(operation="create", index=0, ref_id=None, error=str(e)))
        except Exception as e:  # noqa: BLE001
            balance_violation = True
            issues.append(TXValidationIssue(operation="create", index=0, ref_id=None, error=f"Balance validation error: {e}"))

        balance_preview: Dict[str, Decimal] = {}
        holdings_preview: Dict[str, Decimal] = {}
        if not issues and not balance_violation:
            for broker_id in earliest_date_by_broker:
                cash = await self.get_cash_balances(broker_id)
                for currency, value in cash.items():
                    balance_preview[f"{broker_id}:{currency}"] = value
                holdings = await self.get_asset_holdings(broker_id)
                for asset_id, qty in holdings.items():
                    holdings_preview[f"{broker_id}:asset:{asset_id}"] = qty

        await self.session.rollback()

        return TXValidateResponse(
            would_rollback=bool(issues) or balance_violation,
            issues=issues,
            balance_preview=balance_preview,
            holdings_preview=holdings_preview,
        )

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
