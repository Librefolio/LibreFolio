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
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Literal, Optional, Union

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    Broker,
    BrokerUserAccess,
    PriceHistory,
    Transaction,
    TransactionType,
    UserRole,
)
from backend.app.schemas.brokers import (
    BRAssetHolding,
    BRBulkCreateResponse,
    BRBulkDeleteResponse,
    BRBulkUpdateResponse,
    BRCreateItem,
    BRCreateResult,
    BRDeleteItem,
    BRDeleteResult,
    BRReadItem,
    BRSummary,
    BRUpdateItem,
    BRUpdateResult,
)
from backend.app.schemas.common import Currency
from backend.app.services.transaction_service import (
    BalanceValidationError,
    TransactionService,
)
from backend.app.utils.datetime_utils import today_date, utcnow


class BrokerService:
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

    async def create_bulk(self, items: List[BRCreateItem], user_id: int) -> BRBulkCreateResponse:
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
                            deposit_dicts.append(
                                {
                                    "broker_id": broker.id,
                                    "type": "DEPOSIT",
                                    "date": today_date().isoformat(),
                                    "cash": {"code": currency_obj.code, "amount": format(currency_obj.amount, "f")},
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

    async def _check_user_access(self, broker_id: int, user_id: int, min_role: UserRole = UserRole.VIEWER) -> Optional[UserRole]:
        """
        Check if user has access to a broker and return their role.

        Args:
            broker_id: Broker ID
            user_id: User ID
            min_role: Minimum role required (OWNER > EDITOR > VIEWER)

        Returns:
            User's role if they have at least min_role access, None otherwise
        """
        stmt = select(BrokerUserAccess).where(and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == user_id))
        result = await self.session.execute(stmt)
        access = result.scalar_one_or_none()

        if not access:
            return None

        # Role hierarchy: OWNER > EDITOR > VIEWER
        role_order = {UserRole.OWNER: 3, UserRole.EDITOR: 2, UserRole.VIEWER: 1}
        if role_order.get(access.role, 0) >= role_order.get(min_role, 0):
            return access.role
        return None

    async def get_accessible_broker_ids(self, user_id: int, min_role: UserRole = UserRole.VIEWER) -> List[int]:
        """
        Get list of broker IDs the user has access to.

        Args:
            user_id: User ID
            min_role: Minimum role required (default: VIEWER = any access)

        Returns:
            List of broker IDs the user can access
        """
        role_order = {UserRole.OWNER: 3, UserRole.EDITOR: 2, UserRole.VIEWER: 1}
        min_role_value = role_order.get(min_role, 1)

        stmt = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id)
        result = await self.session.execute(stmt)

        # Filter by role in Python (simpler than complex SQL)
        broker_ids = []
        for row in result.fetchall():
            # Re-query to get role - or we can do a more complex query
            broker_ids.append(row[0])

        # Actually, let's do this properly with the role
        stmt = select(BrokerUserAccess).where(BrokerUserAccess.user_id == user_id)
        result = await self.session.execute(stmt)
        accesses = result.scalars().all()

        return [acc.broker_id for acc in accesses if role_order.get(acc.role, 0) >= min_role_value]

    async def get_all(self, user_id: int, as_user_id: Union[int, Literal["all"], None] = None) -> List[BRReadItem]:
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
            return [BRReadItem.model_validate(b) for b in brokers]
        else:
            # LEFT JOIN with BrokerUserAccess: returns ALL brokers; user_role is
            # set when the user has access, null otherwise. This allows the
            # frontend to know broker names even when the user has no access
            # (for paired-tx placeholder rendering), while still distinguishing
            # accessible (OWNER/EDITOR/VIEWER) from inaccessible (null).
            stmt = (
                select(Broker, BrokerUserAccess.role)
                .outerjoin(
                    BrokerUserAccess,
                    and_(Broker.id == BrokerUserAccess.broker_id, BrokerUserAccess.user_id == filter_user_id),
                )
                .order_by(Broker.name)
            )

        result = await self.session.execute(stmt)
        rows = result.all()
        items = []
        for broker, role in rows:
            item = BRReadItem.model_validate(broker)
            item.user_role = role.value if role else None
            items.append(item)
        return items

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

    async def get_summary(self, broker_id: int, user_id: int, as_user_id: Union[int, Literal["all"], None] = None) -> Optional[BRSummary]:
        """
        Get broker with full summary including balances and holdings.

        Args:
            broker_id: Broker ID
            user_id: Current user ID (always required)
            as_user_id: For superuser - impersonate (int) or "all" for no check

        Returns:
            BRSummary with cash_balances and holdings, or None if not found
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

        # Get cash balances
        cash_dict = await self.tx_service.get_cash_balances(broker_id)
        cash_balances = [Currency(code=code, amount=amount) for code, amount in cash_dict.items() if amount != Decimal("0")]

        # Get asset holdings
        holdings_dict = await self.tx_service.get_asset_holdings(broker_id)
        holdings: List[BRAssetHolding] = []

        for asset_id, quantity in holdings_dict.items():
            if quantity == Decimal("0"):
                continue

            # Get asset info
            asset = await self.session.get(Asset, asset_id)
            if not asset:
                continue

            # Get cost basis
            total_cost_amount = await self.tx_service.get_cost_basis(broker_id, asset_id)
            average_cost = total_cost_amount / quantity if quantity != Decimal("0") else Decimal("0")
            # SafeDecimal in BRAssetHolding guarantees fixed-point JSON
            # serialization — no scientific notation reaches the frontend.
            if average_cost == 0:
                average_cost = Decimal("0")

            # Get current price (from latest price_history)
            current_price = await self._get_latest_price(asset_id)
            current_value = None
            unrealized_pnl = None
            unrealized_pnl_percent = None

            if current_price is not None:
                current_value_amount = current_price * quantity
                current_value = Currency(code=asset.currency, amount=current_value_amount)

                unrealized_pnl_amount = current_value_amount - total_cost_amount
                unrealized_pnl = Currency(code=asset.currency, amount=unrealized_pnl_amount)

                if total_cost_amount != Decimal("0"):
                    unrealized_pnl_percent = ((unrealized_pnl_amount / total_cost_amount) * 100).quantize(Decimal("0.01"))

            holdings.append(
                BRAssetHolding(
                    asset_id=asset_id,
                    asset_name=asset.display_name,
                    quantity=quantity,
                    total_cost=Currency(code=asset.currency, amount=total_cost_amount),
                    average_cost_per_unit=average_cost,
                    current_price=current_price,
                    current_value=current_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_percent=unrealized_pnl_percent,
                )
            )

        # Get current user's role and share on this broker
        user_role_value = None
        user_share_value = None
        if not skip_access_check and check_user_id is not None:
            access_stmt = select(BrokerUserAccess).where(
                and_(
                    BrokerUserAccess.broker_id == broker_id,
                    BrokerUserAccess.user_id == check_user_id,
                )
            )
            access_result = await self.session.execute(access_stmt)
            user_access = access_result.scalar_one_or_none()
            if user_access:
                user_role_value = user_access.role.value
                user_share_value = user_access.share_percentage
        elif not skip_access_check:
            # user_id is the actual logged-in user
            access_stmt = select(BrokerUserAccess).where(
                and_(
                    BrokerUserAccess.broker_id == broker_id,
                    BrokerUserAccess.user_id == user_id,
                )
            )
            access_result = await self.session.execute(access_stmt)
            user_access = access_result.scalar_one_or_none()
            if user_access:
                user_role_value = user_access.role.value
                user_share_value = user_access.share_percentage

        return BRSummary(
            id=broker.id,
            name=broker.name,
            description=broker.description,
            portal_url=broker.portal_url,
            icon_url=broker.icon_url,
            default_import_plugin=broker.default_import_plugin,
            allow_cash_overdraft=broker.allow_cash_overdraft,
            allow_asset_shorting=broker.allow_asset_shorting,
            is_active=broker.is_active,
            opened_at=broker.opened_at,
            created_at=broker.created_at,
            updated_at=broker.updated_at,
            cash_balances=cash_balances,
            holdings=holdings,
            user_role=user_role_value,
            user_share_percentage=user_share_value,
        )

    async def _get_latest_price(self, asset_id: int) -> Optional[Decimal]:
        """Get the latest price for an asset from price_history."""
        stmt = select(PriceHistory.close).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date.desc()).limit(1)
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        return value if value else None

    # =========================================================================
    # UPDATE OPERATIONS
    # =========================================================================

    async def update_bulk(
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

        for item in items:
            try:
                broker = await self.session.get(Broker, item.id)
                if not broker:
                    results.append(
                        BRDeleteResult(
                            id=item.id,
                            success=False,
                            deleted_count=0,
                            message=f"Broker {item.id} not found",
                        )
                    )
                    continue

                # Determine access check
                skip_access_check = as_user_id == "all"
                check_user_id = user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))

                if not skip_access_check and check_user_id is not None:
                    # Only OWNER can delete broker
                    role = await self._check_user_access(item.id, check_user_id, min_role=UserRole.OWNER)
                    if not role:
                        results.append(BRDeleteResult(id=item.id, success=False, deleted_count=0, message="Access denied"))
                        continue

                # Count transactions
                tx_count = await self._count_transactions(item.id)

                if tx_count > 0 and not item.force:
                    results.append(
                        BRDeleteResult(
                            id=item.id,
                            success=False,
                            deleted_count=0,
                            message=(f"Broker has {tx_count} transactions. " f"Use force=True to delete all."),
                        )
                    )
                    continue

                # Delete transactions if force
                transactions_deleted = 0
                if tx_count > 0 and item.force:
                    transactions_deleted = await self.tx_service.delete_by_broker(item.id)
                    await self.session.flush()

                # Delete broker
                await self.session.delete(broker)

                results.append(
                    BRDeleteResult(
                        id=item.id,
                        success=True,
                        deleted_count=1,
                        transactions_deleted=transactions_deleted,
                        message=None,
                    )
                )
                success_count += 1
                total_deleted += 1

            except Exception as e:
                results.append(BRDeleteResult(id=item.id, success=False, deleted_count=0, message=str(e)))

        return BRBulkDeleteResponse(
            results=results,
            success_count=success_count,
            total_deleted=total_deleted,
            errors=errors,
        )

    async def _count_transactions(self, broker_id: int) -> int:
        """Count transactions for a broker."""
        stmt = select(func.count()).select_from(Transaction).where(Transaction.broker_id == broker_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # =========================================================================
    # ACCESS MANAGEMENT
    # =========================================================================

    async def list_accesses(self, broker_id: int, user_id: int, is_superuser: bool = False) -> List[dict]:
        """
        List all users with access to a broker.

        Args:
            broker_id: Broker ID
            user_id: Current user ID
            is_superuser: If True, skip access check

        Returns:
            List of dicts with user_id, username, email, role, created_at
        """
        # Check access (any role can view access list)
        if not is_superuser:
            role = await self._check_user_access(broker_id, user_id)
            if not role:
                return []

        # Import here to avoid circular import
        from backend.app.db.models import User, UserSettings  # noqa: PLC0415 — avoid circular import

        stmt = select(BrokerUserAccess, User, UserSettings).join(User, BrokerUserAccess.user_id == User.id).outerjoin(UserSettings, UserSettings.user_id == User.id).where(BrokerUserAccess.broker_id == broker_id).order_by(BrokerUserAccess.role, User.username)
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "user_id": access.user_id,
                "username": user.username,
                "email": user.email,
                "role": access.role,
                "share_percentage": access.share_percentage,
                "avatar_url": settings.avatar_url if settings else None,
                "created_at": access.created_at,
            }
            for access, user, settings in rows
        ]

    async def bulk_update_access(
        self,
        broker_id: int,
        desired_accesses: list,
        current_user_id: int,
        is_superuser: bool = False,
    ) -> tuple[bool, str, list]:
        """
        Atomically replace the access configuration for a broker.

        Computes the diff between current and desired state, then applies
        all adds, updates, and removes in a single transaction.

        Rules:
        - Only OWNERs (or superusers) can call this
        - At least one OWNER must remain
        - Only OWNERs can have share_percentage > 0 (enforced by schema)
        - Sum of share_percentage must be ≤ 1.0
        - Cannot remove the calling user as last OWNER

        Args:
            broker_id: Broker ID
            desired_accesses: List of BRAccessBulkItem (user_id, role, share_percentage in 0-1)
            current_user_id: Current user ID
            is_superuser: If True, skip OWNER check

        Returns:
            Tuple of (success, message, access_list)
        """
        # 1. Check current user is OWNER (unless superuser)
        if not is_superuser:
            current_role = await self._check_user_access(broker_id, current_user_id, min_role=UserRole.OWNER)
            if not current_role:
                return False, "Only OWNERs can manage access", []

        # 2. Check broker exists
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return False, f"Broker {broker_id} not found", []

        # 3. Validate desired state (in API % scale 0-100)
        # 3a. Must have at least one OWNER
        owner_count = sum(1 for a in desired_accesses if a.role == UserRole.OWNER)
        if owner_count == 0:
            return False, "At least one OWNER is required", []

        # 3b. Sum of share_percentage ≤ 1.0
        total_share = sum(a.share_percentage for a in desired_accesses)
        if total_share > Decimal("1"):
            return False, (f"Total share percentage exceeds 1.0. " f"Current total: {total_share}"), []

        # 3c. No duplicate user_ids
        user_ids = [a.user_id for a in desired_accesses]
        if len(user_ids) != len(set(user_ids)):
            return False, "Duplicate user IDs in request", []

        # 3d. All users exist
        from backend.app.db.models import User  # noqa: PLC0415 — lazy import / avoid circular

        for uid in user_ids:
            user = await self.session.get(User, uid)
            if not user:
                return False, f"User {uid} not found", []

        # 4. Get current accesses
        stmt = select(BrokerUserAccess).where(BrokerUserAccess.broker_id == broker_id)
        result = await self.session.execute(stmt)
        current_accesses = {a.user_id: a for a in result.scalars().all()}

        desired_map = {a.user_id: a for a in desired_accesses}

        # 5. Compute diff and apply
        # 5a. Remove users not in desired list
        for uid, access in current_accesses.items():
            if uid not in desired_map:
                await self.session.delete(access)

        # 5b. Add new users and update existing
        for uid, desired in desired_map.items():
            if uid in current_accesses:
                # Update existing
                existing = current_accesses[uid]
                existing.role = desired.role
                existing.share_percentage = desired.share_percentage
                existing.updated_at = utcnow()
            else:
                # Add new
                new_access = BrokerUserAccess(
                    user_id=uid,
                    broker_id=broker_id,
                    role=desired.role,
                    share_percentage=desired.share_percentage,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                self.session.add(new_access)

        # Flush to ensure consistency before returning
        await self.session.flush()

        return True, "Access configuration updated", []
