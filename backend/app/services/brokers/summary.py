"""The broker summary of ``BrokerService`` (``GET /brokers/{id}/summary``)."""

from __future__ import annotations

from datetime import date as date_type
from typing import Literal, Optional, Union

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Broker,
    BrokerUserAccess,
)
from backend.app.schemas.brokers import BRSummary
from backend.app.schemas.common import Currency
from backend.app.services.transactions.transaction_service import TransactionService


class BrokerSummaryMixin:
    """The broker summary: cash, the caller's role and share.

    Mixed into ``BrokerService`` (``broker_service.py``), which provides ``session``, ``tx_service`` and, from
    ``BrokerAccessMixin``, ``_check_user_access``.
    """

    session: AsyncSession
    tx_service: TransactionService

    # =========================================================================
    # READ OPERATIONS
    # =========================================================================

    async def get_summary(self, broker_id: int, user_id: int, as_user_id: Union[int, Literal["all"], None] = None, as_of: Optional[date_type] = None) -> Optional[BRSummary]:  # noqa: C901 — sequential fetch/assemble with guard returns
        """
        Get the broker with its cash balances, the caller's role and share.

        Args:
            broker_id: Broker ID
            user_id: Current user ID (always required)
            as_user_id: For superuser - impersonate (int) or "all" for no check
            as_of: The day the summary describes, the user's today; ``date.today()`` when omitted.
                A transaction dated later counts in none of the cash balances.

        Returns:
            BRSummary with cash_balances, or None if not found
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

        # The summary is the broker on the user's day: a transaction dated later counts in none of its figures.
        as_of = as_of or date_type.today()

        # Get cash balances. Currencies with a net-zero balance are still
        # included (as long as they have transaction history) — a currency
        # deposited and then fully invested should stay visible at 0, not
        # disappear entirely.
        cash_dict = await self.tx_service.get_cash_balances(broker_id, as_of=as_of)
        cash_balances = [Currency(code=code, amount=amount) for code, amount in cash_dict.items()]

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
            user_role=user_role_value,
            user_share_percentage=user_share_value,
        )
