"""Broker access roles of ``BrokerService``: checks, the access list, leaving a broker, stepping down."""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Broker,
    BrokerUserAccess,
    UserRole,
)
from backend.app.schemas.brokers import BRDeleteItem
from backend.app.utils.datetime_utils import utcnow


class BrokerAccessMixin:
    """Access roles: the role a user holds, the brokers a user can see, the access list and its changes, leaving a broker and stepping down.

    Mixed into ``BrokerService`` (``broker_service.py``), which provides ``session`` and ``delete_bulk``.
    """

    session: AsyncSession

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

    # =========================================================================
    # ACCESS MANAGEMENT
    # =========================================================================

    async def list_accesses(self, broker_id: int, user_id: int, is_superuser: bool = False) -> List[dict]:
        """
        List all users with access to a broker: role, share and profile fields.

        Checks no access: the route decides who may read the list (today any authenticated user, for any existing
        broker). ``user_id`` and ``is_superuser`` are not read: every authenticated user may read the list (the
        developer's decision P4, 16/10: users need to know other brokers exist, to see why a name is taken and whom to ask).

        Args:
            broker_id: Broker ID
            user_id: Current user ID (not read)
            is_superuser: Whether the caller is an administrator (not read)

        Returns:
            List of dicts with user_id, username, email, role, share_percentage, avatar_url, created_at
        """
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

    async def bulk_update_access(  # noqa: C901 — sequential validation gates with early returns + diff-apply loops
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
        - At least one OWNER must remain: nobody, the caller included, can remove or downgrade the last one
        - Only OWNERs can have share_percentage > 0 (enforced by schema)
        - Sum of share_percentage must be ≤ 1.0

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

    async def leave_broker(
        self,
        broker_id: int,
        user_id: int,
    ) -> tuple[bool, str, bool]:
        """Remove the caller's own access to a broker (F4).

        Rules:
        - EDITOR/VIEWER: always allowed.
        - OWNER: allowed when at least one other OWNER remains.
        - The LAST owner leaving deletes the broker entirely (cascade over
          transactions; BRIM report files are cleaned up by the API layer),
          per the confirmed F4 semantics.

        Returns:
            Tuple of (success, message, broker_deleted)
        """
        stmt = select(BrokerUserAccess).where(and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == user_id))
        access = (await self.session.execute(stmt)).scalars().first()
        if not access:
            return False, "You have no access to this broker", False

        if access.role == UserRole.OWNER:
            owners_stmt = select(func.count()).select_from(BrokerUserAccess).where(and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.role == UserRole.OWNER))
            owner_count = (await self.session.execute(owners_stmt)).scalar_one()
            if owner_count <= 1:
                response = await self.delete_bulk([BRDeleteItem(id=broker_id, force=True)], user_id=user_id)
                result = response.results[0] if response.results else None
                if not result or not result.success:
                    return False, (result.message if result else None) or "Broker deletion failed", False
                return True, "Broker deleted: the last owner left", True

        await self.session.delete(access)
        await self.session.flush()
        return True, "Access removed", False

    async def update_own_role(
        self,
        broker_id: int,
        user_id: int,
        new_role: UserRole,
    ) -> tuple[bool, str]:
        """Self-demotion only (F4): EDITOR → VIEWER, or OWNER → EDITOR/VIEWER when
        at least one other OWNER remains. Promotions stay on the OWNER-only bulk path.

        Demoting from OWNER also zeroes the share (only OWNERs may hold share > 0).

        Returns:
            Tuple of (success, message)
        """
        stmt = select(BrokerUserAccess).where(and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.user_id == user_id))
        access = (await self.session.execute(stmt)).scalars().first()
        if not access:
            return False, "You have no access to this broker"

        current = access.role
        allowed = (current == UserRole.EDITOR and new_role == UserRole.VIEWER) or (current == UserRole.OWNER and new_role in (UserRole.EDITOR, UserRole.VIEWER))
        if not allowed:
            return False, f"Self role change {current.value} → {new_role.value} is not allowed"

        if current == UserRole.OWNER:
            owners_stmt = select(func.count()).select_from(BrokerUserAccess).where(and_(BrokerUserAccess.broker_id == broker_id, BrokerUserAccess.role == UserRole.OWNER))
            owner_count = (await self.session.execute(owners_stmt)).scalar_one()
            if owner_count <= 1:
                return False, "The last OWNER cannot demote themselves — promote another user first"

        access.role = new_role
        if current == UserRole.OWNER:
            access.share_percentage = Decimal("0")
        access.updated_at = utcnow()
        await self.session.flush()
        return True, f"Role updated to {new_role.value}"
