"""
Broker Service for LibreFolio.

Centralizes all broker business logic:
- CRUD operations
- Initial balance handling (auto-creates DEPOSIT transactions)
- Flag validation (overdraft/shorting)
- Balance aggregation for summaries
- Multi-user access control via BrokerUserAccess

Design Notes:
- Uses TransactionService for transaction operations
- Validates balances when disabling overdraft/shorting
- All methods are async for non-blocking I/O
- User filtering via BrokerUserAccess join

``BrokerService`` is composed of two mixins: ``access`` (roles and access management) and ``summary``
(``GET /brokers/{id}/summary``); the class keeps create, read, update and delete.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Literal, Optional, Union

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Broker,
    BrokerUserAccess,
    Transaction,
    UserRole,
)
from backend.app.db.session import begin_writes
from backend.app.schemas.brokers import (
    BRBulkCreateResponse,
    BRBulkDeleteResponse,
    BRBulkUpdateResponse,
    BRCreateItem,
    BRCreateResult,
    BRDeleteItem,
    BRDeleteResult,
    BRDiscoveryItem,
    BRListResponse,
    BRReadItem,
    BRUpdateItem,
    BRUpdateResult,
)
from backend.app.services.brokers.access import BrokerAccessMixin
from backend.app.services.brokers.summary import BrokerSummaryMixin
from backend.app.services.transactions.transaction_batch_context import BalanceValidationError
from backend.app.services.transactions.transaction_service import TransactionService
from backend.app.utils.datetime_utils import today_date, utcnow

BROKER_NAME_RECOVERY = "To resolve this, rename the existing broker or choose a different name for the broker you are adding."


class BrokerService(BrokerAccessMixin, BrokerSummaryMixin):
    """
    Service for managing brokers.

    All methods are async and expect an AsyncSession.
    The caller is responsible for commit/rollback.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tx_service = TransactionService(session)

    # =========================================================================
    # CREATE OPERATIONS
    # =========================================================================

    async def create_bulk(self, items: List[BRCreateItem], user_id: int) -> BRBulkCreateResponse:  # noqa: C901 — per-item loop with duplicate-name error variants, no nested logic
        """
        Create multiple brokers.

        For each broker with initial_balances, automatically creates
        DEPOSIT transactions. Creates BrokerUserAccess with OWNER role
        for the creating user.

        Args:
            items: List of BRCreateItem DTOs
            user_id: User ID to set as OWNER (required)

        Returns:
            BRBulkCreateResponse with results for each item
        """
        results: List[BRCreateResult] = []
        success_count = 0
        errors: List[str] = []

        for item in items:
            try:
                # Check for duplicate name
                stmt = select(Broker).where(Broker.name == item.name)
                result = await self.session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    # Find the owner of the existing broker
                    owner_stmt = select(BrokerUserAccess).where(BrokerUserAccess.broker_id == existing.id, BrokerUserAccess.role == UserRole.OWNER)
                    owner_result = await self.session.execute(owner_stmt)
                    owner_access = owner_result.scalar_one_or_none()

                    if owner_access and owner_access.user_id == user_id:
                        error_msg = f"You already have a broker named '{item.name}'"
                    elif owner_access:
                        # Get owner username
                        from backend.app.db.models import User  # noqa: PLC0415 — lazy import / avoid circular

                        user_stmt = select(User).where(User.id == owner_access.user_id)
                        user_result = await self.session.execute(user_stmt)
                        owner_user = user_result.scalar_one_or_none()
                        owner_name = owner_user.username if owner_user else f"user #{owner_access.user_id}"
                        error_msg = f"Broker '{item.name}' already exists (owned by '{owner_name}')"
                    else:
                        error_msg = f"Broker with name '{item.name}' already exists"
                    error_msg = f"{error_msg}. {BROKER_NAME_RECOVERY}"

                    results.append(
                        BRCreateResult(
                            success=False,
                            name=item.name,
                            error=error_msg,
                        )
                    )
                    continue

                # Create broker
                broker = Broker(
                    name=item.name,
                    description=item.description,
                    portal_url=item.portal_url,
                    icon_url=item.icon_url,
                    default_import_plugin=item.default_import_plugin,
                    allow_cash_overdraft=item.allow_cash_overdraft,
                    allow_asset_shorting=item.allow_asset_shorting,
                    is_active=item.is_active,
                    opened_at=item.opened_at,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                self.session.add(broker)
                await self.session.flush()  # Get ID

                # Create user access (OWNER for creator)
                access = BrokerUserAccess(
                    user_id=user_id,
                    broker_id=broker.id,
                    role=UserRole.OWNER,
                    share_percentage=Decimal("1"),
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                self.session.add(access)

                # Create initial deposits
                deposits_created = 0
                if item.initial_balances:
                    deposit_dicts = []
                    for currency_obj in item.initial_balances:
                        if currency_obj.is_positive():
                            # Raw dict (not TXCreateItem) because it goes into
                            # execute_batch(creates_raw=...) which does per-row
                            # model_validate() in try/except, collecting ALL
                            # errors in one response instead of failing on the first.
                            # str, never format(…, "f"): the batch refuses a value past its column's limits (W-B58),
                            # while the fixed point of 1E+999999999 is a billion digits on the event loop (R13-SEC7-3).
                            deposit_dicts.append(
                                {
                                    "broker_id": broker.id,
                                    "type": "DEPOSIT",
                                    "date": today_date().isoformat(),
                                    "cash": {"code": currency_obj.code, "amount": str(currency_obj.amount)},
                                }
                            )

                    if deposit_dicts:
                        deposit_response = await self.tx_service.execute_batch(
                            creates_raw=deposit_dicts,
                            updates_raw=[],
                            deletes=[],
                            commit=True,
                        )
                        deposits_created = len([r for r in (deposit_response.results or []) if r.status == "success"])

                        # Add any deposit errors to broker errors
                        if deposit_response.issues:
                            errors.extend([f"Broker '{item.name}': {iss.error}" for iss in deposit_response.issues])

                results.append(
                    BRCreateResult(
                        success=True,
                        broker_id=broker.id,
                        name=item.name,
                        deposits_created=deposits_created,
                    )
                )
                success_count += 1

            except Exception as e:
                results.append(BRCreateResult(success=False, name=item.name, error=str(e)))

        return BRBulkCreateResponse(results=results, success_count=success_count, errors=errors)

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def get_all(
        self,
        user_id: int,
        as_user_id: Union[int, Literal["all"], None] = None,
        include_inaccessible: bool = False,
    ) -> BRListResponse:
        """
        Get brokers filtered by user access.

        Args:
            user_id: Current user ID (always required)
            as_user_id: For superuser - impersonate another user (int) or "all" for no filter
                       If None, uses current user's access
        """
        filter_user_id = user_id
        no_filter = False

        if as_user_id is not None:
            if as_user_id == "all":
                no_filter = True
            else:
                filter_user_id = int(as_user_id)

        if no_filter:
            stmt = select(Broker).order_by(Broker.name)
            result = await self.session.execute(stmt)
            brokers = result.scalars().all()
            return BRListResponse(items=[BRReadItem.model_validate(b) for b in brokers])

        stmt = (
            select(Broker, BrokerUserAccess.role, BrokerUserAccess.share_percentage)
            .join(
                BrokerUserAccess,
                and_(Broker.id == BrokerUserAccess.broker_id, BrokerUserAccess.user_id == filter_user_id),
            )
            .order_by(Broker.name)
        )

        result = await self.session.execute(stmt)
        rows = result.all()
        items = []
        for broker, role, share_percentage in rows:
            item = BRReadItem.model_validate(broker)
            item.user_role = role.value if role else None
            item.user_share_percentage = share_percentage
            items.append(item)

        inaccessible: List[BRDiscoveryItem] = []
        if include_inaccessible:
            inaccessible_stmt = (
                select(Broker.id, Broker.name, Broker.icon_url)
                .outerjoin(
                    BrokerUserAccess,
                    and_(Broker.id == BrokerUserAccess.broker_id, BrokerUserAccess.user_id == filter_user_id),
                )
                .where(BrokerUserAccess.user_id.is_(None))
                .order_by(Broker.name)
            )
            inaccessible_result = await self.session.execute(inaccessible_stmt)
            inaccessible = [BRDiscoveryItem(id=broker_id, name=name, icon_url=icon_url) for broker_id, name, icon_url in inaccessible_result.all()]

        return BRListResponse(items=items, inaccessible=inaccessible)

    async def get_by_id(self, broker_id: int, user_id: int, as_user_id: Union[int, Literal["all"], None] = None) -> Optional[BRReadItem]:
        """
        Get a broker by ID, checking user access.

        Args:
            broker_id: Broker ID
            user_id: Current user ID (always required)
            as_user_id: For superuser - impersonate (int) or "all" for no check
        """
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return None

        # Determine access check
        skip_access_check = as_user_id == "all"
        check_user_id = user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))

        if not skip_access_check and check_user_id is not None:
            has_access = await self._check_user_access(broker_id, check_user_id)
            if not has_access:
                return None

        item = BRReadItem.model_validate(broker)
        # Populate user_role if we know the user
        effective_user = user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))
        if effective_user is not None:
            role = await self._check_user_access(broker_id, effective_user)
            item.user_role = role.value if role else None
        return item

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    async def update_bulk(  # noqa: C901 — per-item loop: sequential field mapping + error continues
        self,
        items: List[BRUpdateItem],
        broker_ids: List[int],
        user_id: int,
        as_user_id: Union[int, Literal["all"], None] = None,
    ) -> BRBulkUpdateResponse:
        """
        Update multiple brokers.

        If overdraft/shorting flags change from True to False,
        validates that current balances don't violate new constraints.

        Requires at least EDITOR role (OWNER or EDITOR can modify).

        Args:
            items: List of BRUpdateItem DTOs
            broker_ids: List of broker IDs to update (parallel to items)
            user_id: Current user ID (always required)
            as_user_id: For superuser - impersonate (int) or "all" for no check

        Returns:
            BRBulkUpdateResponse with results for each item
        """
        results: List[BRUpdateResult] = []
        success_count = 0
        errors: List[str] = []

        for item, broker_id in zip(items, broker_ids, strict=True):
            try:
                broker = await self.session.get(Broker, broker_id)
                if not broker:
                    results.append(BRUpdateResult(id=broker_id, success=False, error=f"Broker {broker_id} not found"))
                    continue

                # Determine access check
                skip_access_check = as_user_id == "all"
                check_user_id = user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))

                if not skip_access_check and check_user_id is not None:
                    # EDITOR or OWNER can update broker
                    role = await self._check_user_access(broker_id, check_user_id, min_role=UserRole.EDITOR)
                    if not role:
                        results.append(BRUpdateResult(id=broker_id, success=False, error="Access denied"))
                        continue

                validation_triggered = False

                # Check if disabling overdraft/shorting
                if item.allow_cash_overdraft is False and broker.allow_cash_overdraft:
                    validation_triggered = True
                if item.allow_asset_shorting is False and broker.allow_asset_shorting:
                    validation_triggered = True

                # Apply updates
                if item.name is not None:
                    # Check for duplicate
                    stmt = select(Broker).where(Broker.name == item.name, Broker.id != broker_id)
                    result = await self.session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    if existing:
                        results.append(
                            BRUpdateResult(
                                id=broker_id,
                                success=False,
                                error=f"Broker with name '{item.name}' already exists",
                            )
                        )
                        continue
                    broker.name = item.name

                if item.description is not None:
                    broker.description = item.description if item.description != "" else None

                # For URLs: empty string "" means clear field, None means don't update
                if item.portal_url is not None:
                    broker.portal_url = item.portal_url if item.portal_url != "" else None

                if item.icon_url is not None:
                    broker.icon_url = item.icon_url if item.icon_url != "" else None

                if item.default_import_plugin is not None:
                    broker.default_import_plugin = item.default_import_plugin if item.default_import_plugin != "" else None

                if item.is_active is not None:
                    broker.is_active = item.is_active

                if item.opened_at is not None:
                    broker.opened_at = item.opened_at

                if item.allow_cash_overdraft is not None:
                    broker.allow_cash_overdraft = item.allow_cash_overdraft

                if item.allow_asset_shorting is not None:
                    broker.allow_asset_shorting = item.allow_asset_shorting

                broker.updated_at = utcnow()

                # Validate if needed
                if validation_triggered:
                    try:
                        # Validate from the beginning of time
                        await self.tx_service._validate_broker_balances(broker_id, None)  # None = from beginning
                    except BalanceValidationError as e:
                        results.append(BRUpdateResult(id=broker_id, success=False, validation_triggered=True, error=str(e)))
                        continue

                results.append(BRUpdateResult(id=broker_id, success=True, validation_triggered=validation_triggered))
                success_count += 1

            except Exception as e:
                results.append(BRUpdateResult(id=broker_id, success=False, error=str(e)))

        return BRBulkUpdateResponse(results=results, success_count=success_count, errors=errors)

    # =========================================================================
    # DELETE OPERATIONS
    # =========================================================================

    async def delete_bulk(
        self,
        items: List[BRDeleteItem],
        user_id: int,
        as_user_id: Union[int, Literal["all"], None] = None,
    ) -> BRBulkDeleteResponse:
        """
        Delete multiple brokers.

        If force=False and broker has transactions, fails with count.
        If force=True, deletes broker and all transactions.

        Requires OWNER role to delete.

        Args:
            items: List of BRDeleteItem DTOs
            user_id: Current user ID (always required)
            as_user_id: For superuser - impersonate (int) or "all" for no check

        Returns:
            BRBulkDeleteResponse with results for each item
        """
        results: List[BRDeleteResult] = []
        success_count = 0
        total_deleted = 0
        errors: List[str] = []

        # Each broker in its own savepoint: a failure half-way through one (W-B20) rolls back that broker's writes only,
        # never the brokers before or after it. begin_writes opens the transaction first, so the savepoints nest in it.
        await begin_writes(self.session, Broker)
        for item in items:
            try:
                async with self.session.begin_nested():
                    result = await self._delete_one(item, user_id, as_user_id)
            except Exception as e:
                result = BRDeleteResult(id=item.id, success=False, deleted_count=0, message=str(e))
            results.append(result)
            if result.success:
                success_count += 1
                total_deleted += 1

        return BRBulkDeleteResponse(
            results=results,
            success_count=success_count,
            total_deleted=total_deleted,
            errors=errors,
        )

    async def _delete_one(
        self,
        item: BRDeleteItem,
        user_id: int,
        as_user_id: Union[int, Literal["all"], None],
    ) -> BRDeleteResult:
        """Delete one broker of ``delete_bulk``, inside its savepoint, and answer its result.

        Its writes are flushed here, so an error surfaces before the savepoint is released and the broker is reported
        failed, not deleted.
        """
        broker = await self.session.get(Broker, item.id)
        if not broker:
            return BRDeleteResult(
                id=item.id,
                success=False,
                deleted_count=0,
                message=f"Broker {item.id} not found",
            )

        # Determine access check
        skip_access_check = as_user_id == "all"
        check_user_id = user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))

        if not skip_access_check and check_user_id is not None:
            # Only OWNER can delete broker
            role = await self._check_user_access(item.id, check_user_id, min_role=UserRole.OWNER)
            if not role:
                return BRDeleteResult(id=item.id, success=False, deleted_count=0, message="Access denied")

        # Count transactions
        tx_count = await self._count_transactions(item.id)

        if tx_count > 0 and not item.force:
            return BRDeleteResult(
                id=item.id,
                success=False,
                deleted_count=0,
                message=(f"Broker has {tx_count} transactions. " f"Use force=True to delete all."),
                transaction_count=tx_count,
            )

        # Delete transactions if force
        transactions_deleted = 0
        if tx_count > 0 and item.force:
            transactions_deleted = await self.tx_service.delete_by_broker(item.id)
            await self.session.flush()

        # Delete broker
        await self.session.delete(broker)
        await self.session.flush()

        return BRDeleteResult(
            id=item.id,
            success=True,
            deleted_count=1,
            transactions_deleted=transactions_deleted,
            message=None,
        )

    async def _count_transactions(self, broker_id: int) -> int:
        """Count transactions for a broker."""
        stmt = select(func.count()).select_from(Transaction).where(Transaction.broker_id == broker_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
