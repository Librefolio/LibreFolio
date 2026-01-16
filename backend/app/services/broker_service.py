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

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Broker,
    Transaction,
    TransactionType,
    Asset,
    BrokerUserAccess,
    UserRole,
)
from backend.app.db.models import PriceHistory
from backend.app.schemas.brokers import (
    BRCreateItem,
    BRReadItem,
    BRSummary,
    BRAssetHolding,
    BRUpdateItem,
    BRDeleteItem,
    BRCreateResult,
    BRBulkCreateResponse,
    BRUpdateResult,
    BRBulkUpdateResponse,
    BRDeleteResult,
    BRBulkDeleteResponse,
)
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.transaction_service import (
    TransactionService,
    BalanceValidationError,
)
from backend.app.utils.datetime_utils import utcnow, today_date


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
                    results.append(
                        BRCreateResult(
                            success=False,
                            name=item.name,
                            error=f"Broker with name '{item.name}' already exists",
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
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
                self.session.add(access)

                # Create initial deposits
                deposits_created = 0
                if item.initial_balances:
                    deposit_items = []
                    for currency_obj in item.initial_balances:
                        if currency_obj.is_positive():
                            deposit_items.append(
                                TXCreateItem(
                                    broker_id=broker.id,
                                    type=TransactionType.DEPOSIT,
                                    date=today_date(),
                                    cash=currency_obj,
                                )
                            )

                    if deposit_items:
                        deposit_response = await self.tx_service.create_bulk(deposit_items)
                        deposits_created = deposit_response.success_count

                        # Add any deposit errors to broker errors
                        if deposit_response.errors:
                            errors.extend(
                                [f"Broker '{item.name}': {err}" for err in deposit_response.errors]
                            )

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

    async def _check_user_access(
        self, broker_id: int, user_id: int, min_role: UserRole = UserRole.VIEWER
    ) -> Optional[UserRole]:
        """
        Check if user has access to a broker and return their role.

        Args:
            broker_id: Broker ID
            user_id: User ID
            min_role: Minimum role required (OWNER > EDITOR > VIEWER)

        Returns:
            User's role if they have at least min_role access, None otherwise
        """
        stmt = select(BrokerUserAccess).where(
            and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        access = result.scalar_one_or_none()

        if not access:
            return None

        # Role hierarchy: OWNER > EDITOR > VIEWER
        role_order = {UserRole.OWNER: 3, UserRole.EDITOR: 2, UserRole.VIEWER: 1}
        if role_order.get(access.role, 0) >= role_order.get(min_role, 0):
            return access.role
        return None

    async def get_all(
        self, user_id: int, as_user_id: Union[int, Literal["all"], None] = None
    ) -> List[BRReadItem]:
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
        else:
            # Join with BrokerUserAccess to filter by user
            stmt = (
                select(Broker)
                .join(BrokerUserAccess, Broker.id == BrokerUserAccess.broker_id)
                .where(BrokerUserAccess.user_id == filter_user_id)
                .order_by(Broker.name)
            )

        result = await self.session.execute(stmt)
        brokers = result.scalars().all()
        return [BRReadItem.model_validate(b) for b in brokers]

    async def get_by_id(
        self, broker_id: int, user_id: int, as_user_id: Union[int, Literal["all"], None] = None
    ) -> Optional[BRReadItem]:
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
        check_user_id = (
            user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))
        )

        if not skip_access_check and check_user_id is not None:
            has_access = await self._check_user_access(broker_id, check_user_id)
            if not has_access:
                return None

        return BRReadItem.model_validate(broker)

    async def get_summary(
        self, broker_id: int, user_id: int, as_user_id: Union[int, Literal["all"], None] = None
    ) -> Optional[BRSummary]:
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
        check_user_id = (
            user_id if as_user_id is None else (None if skip_access_check else int(as_user_id))
        )

        if not skip_access_check and check_user_id is not None:
            has_access = await self._check_user_access(broker_id, check_user_id)
            if not has_access:
                return None

        # Get cash balances
        cash_dict = await self.tx_service.get_cash_balances(broker_id)
        cash_balances = [
            Currency(code=code, amount=amount)
            for code, amount in cash_dict.items()
            if amount != Decimal("0")
        ]

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
            average_cost = (
                total_cost_amount / quantity if quantity != Decimal("0") else Decimal("0")
            )

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
                    unrealized_pnl_percent = (
                        (unrealized_pnl_amount / total_cost_amount) * 100
                    ).quantize(Decimal("0.01"))

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
        )

    async def _get_latest_price(self, asset_id: int) -> Optional[Decimal]:
        """Get the latest price for an asset from price_history."""
        stmt = (
            select(PriceHistory.close)
            .where(PriceHistory.asset_id == asset_id)
            .order_by(PriceHistory.date.desc())
            .limit(1)
        )
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

        for item, broker_id in zip(items, broker_ids):
            try:
                broker = await self.session.get(Broker, broker_id)
                if not broker:
                    results.append(
                        BRUpdateResult(
                            id=broker_id, success=False, error=f"Broker {broker_id} not found"
                        )
                    )
                    continue

                # Determine access check
                skip_access_check = as_user_id == "all"
                check_user_id = (
                    user_id
                    if as_user_id is None
                    else (None if skip_access_check else int(as_user_id))
                )

                if not skip_access_check and check_user_id is not None:
                    # EDITOR or OWNER can update broker
                    role = await self._check_user_access(
                        broker_id, check_user_id, min_role=UserRole.EDITOR
                    )
                    if not role:
                        results.append(
                            BRUpdateResult(id=broker_id, success=False, error="Access denied")
                        )
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
                    broker.description = item.description

                if item.portal_url is not None:
                    broker.portal_url = item.portal_url

                if item.allow_cash_overdraft is not None:
                    broker.allow_cash_overdraft = item.allow_cash_overdraft

                if item.allow_asset_shorting is not None:
                    broker.allow_asset_shorting = item.allow_asset_shorting

                broker.updated_at = utcnow()

                # Validate if needed
                if validation_triggered:
                    try:
                        # Validate from the beginning of time
                        await self.tx_service._validate_broker_balances(
                            broker_id, None
                        )  # None = from beginning
                    except BalanceValidationError as e:
                        results.append(
                            BRUpdateResult(
                                id=broker_id, success=False, validation_triggered=True, error=str(e)
                            )
                        )
                        continue

                results.append(
                    BRUpdateResult(
                        id=broker_id, success=True, validation_triggered=validation_triggered
                    )
                )
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
                check_user_id = (
                    user_id
                    if as_user_id is None
                    else (None if skip_access_check else int(as_user_id))
                )

                if not skip_access_check and check_user_id is not None:
                    # Only OWNER can delete broker
                    role = await self._check_user_access(
                        item.id, check_user_id, min_role=UserRole.OWNER
                    )
                    if not role:
                        results.append(
                            BRDeleteResult(
                                id=item.id, success=False, deleted_count=0, message="Access denied"
                            )
                        )
                        continue

                # Count transactions
                tx_count = await self._count_transactions(item.id)

                if tx_count > 0 and not item.force:
                    results.append(
                        BRDeleteResult(
                            id=item.id,
                            success=False,
                            deleted_count=0,
                            message=(
                                f"Broker has {tx_count} transactions. "
                                f"Use force=True to delete all."
                            ),
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
                results.append(
                    BRDeleteResult(id=item.id, success=False, deleted_count=0, message=str(e))
                )

        return BRBulkDeleteResponse(
            results=results,
            success_count=success_count,
            total_deleted=total_deleted,
            errors=errors,
        )

    async def _count_transactions(self, broker_id: int) -> int:
        """Count transactions for a broker."""
        stmt = (
            select(func.count()).select_from(Transaction).where(Transaction.broker_id == broker_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # =========================================================================
    # ACCESS MANAGEMENT
    # =========================================================================

    async def list_accesses(
        self, broker_id: int, user_id: int, is_superuser: bool = False
    ) -> List[dict]:
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
        from backend.app.db.models import User

        stmt = (
            select(BrokerUserAccess, User)
            .join(User, BrokerUserAccess.user_id == User.id)
            .where(BrokerUserAccess.broker_id == broker_id)
            .order_by(BrokerUserAccess.role, User.username)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "user_id": access.user_id,
                "username": user.username,
                "email": user.email,
                "role": access.role,
                "created_at": access.created_at,
            }
            for access, user in rows
        ]

    async def _count_owners(self, broker_id: int) -> int:
        """Count number of OWNERs for a broker."""
        stmt = (
            select(func.count())
            .select_from(BrokerUserAccess)
            .where(
                and_(
                    BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.role == UserRole.OWNER
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def add_access(
        self,
        broker_id: int,
        target_user_id: int,
        role: UserRole,
        current_user_id: int,
        is_superuser: bool = False,
    ) -> tuple[bool, str]:
        """
        Add user access to a broker.

        Args:
            broker_id: Broker ID
            target_user_id: User ID to grant access
            role: Access role
            current_user_id: Current user ID
            is_superuser: If True, skip OWNER check

        Returns:
            Tuple of (success, message)
        """
        # Check current user is OWNER (unless superuser)
        if not is_superuser:
            current_role = await self._check_user_access(
                broker_id, current_user_id, min_role=UserRole.OWNER
            )
            if not current_role:
                return False, "Only OWNERs can add access"

        # Check broker exists
        broker = await self.session.get(Broker, broker_id)
        if not broker:
            return False, f"Broker {broker_id} not found"

        # Check target user exists
        from backend.app.db.models import User

        target_user = await self.session.get(User, target_user_id)
        if not target_user:
            return False, f"User {target_user_id} not found"

        # Check if access already exists
        existing = await self._check_user_access(broker_id, target_user_id)
        if existing:
            return False, f"User {target_user_id} already has access"

        # Create access
        access = BrokerUserAccess(
            user_id=target_user_id,
            broker_id=broker_id,
            role=role,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self.session.add(access)

        return True, "Access granted"

    async def update_access(
        self,
        broker_id: int,
        target_user_id: int,
        new_role: UserRole,
        current_user_id: int,
        is_superuser: bool = False,
    ) -> tuple[bool, str]:
        """
        Update user access role.

        Args:
            broker_id: Broker ID
            target_user_id: User ID to update
            new_role: New role
            current_user_id: Current user ID
            is_superuser: If True, skip some checks

        Returns:
            Tuple of (success, message)
        """
        # Get current user's role
        if not is_superuser:
            current_role = await self._check_user_access(broker_id, current_user_id)
            if not current_role:
                return False, "Access denied"

            # OWNER can modify anyone's role
            # EDITOR can only remove themselves (handled in delete)
            # VIEWER cannot modify
            if current_role != UserRole.OWNER:
                return False, "Only OWNERs can modify access"

        # Get target access
        stmt = select(BrokerUserAccess).where(
            and_(
                BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == target_user_id
            )
        )
        result = await self.session.execute(stmt)
        access = result.scalar_one_or_none()

        if not access:
            return False, f"User {target_user_id} does not have access"

        # Check if degrading last OWNER
        if access.role == UserRole.OWNER and new_role != UserRole.OWNER:
            owner_count = await self._count_owners(broker_id)
            if owner_count <= 1:
                return False, "Cannot degrade the last OWNER. Delete broker instead."

        # Update role
        access.role = new_role
        access.updated_at = utcnow()

        return True, "Access updated"

    async def remove_access(
        self, broker_id: int, target_user_id: int, current_user_id: int, is_superuser: bool = False
    ) -> tuple[bool, str]:
        """
        Remove user access from a broker.

        Args:
            broker_id: Broker ID
            target_user_id: User ID to remove
            current_user_id: Current user ID
            is_superuser: If True, skip some checks

        Returns:
            Tuple of (success, message)
        """
        # Get current user's role
        if not is_superuser:
            current_role = await self._check_user_access(broker_id, current_user_id)
            if not current_role:
                return False, "Access denied"

            # Check permissions
            if target_user_id == current_user_id:
                # Anyone can remove themselves (except last OWNER)
                pass
            elif current_role == UserRole.OWNER:
                # OWNER can remove others
                pass
            else:
                # EDITOR/VIEWER can only remove themselves
                return False, "You can only remove yourself"

        # Get target access
        stmt = select(BrokerUserAccess).where(
            and_(
                BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == target_user_id
            )
        )
        result = await self.session.execute(stmt)
        access = result.scalar_one_or_none()

        if not access:
            return False, f"User {target_user_id} does not have access"

        # Check if removing last OWNER
        if access.role == UserRole.OWNER:
            owner_count = await self._count_owners(broker_id)
            if owner_count <= 1:
                return False, "Cannot remove the last OWNER. Delete broker instead."

        # Delete access
        await self.session.delete(access)

        return True, "Access removed"
