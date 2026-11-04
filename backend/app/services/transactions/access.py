"""Broker access checks of ``TransactionService``."""

from __future__ import annotations

from typing import Optional, Set

from fastapi import HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess, UserRole


class TransactionAccessMixin:
    """Broker access checks: the role a user holds on a broker, and the check a batch makes once per broker.

    Mixed into ``TransactionService`` (``transaction_service.py``), which provides ``session``.
    """

    session: AsyncSession

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
