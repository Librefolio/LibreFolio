"""
The accounts over ``LIBREFOLIO_MAX_USERS`` (workstream A, lot A5-7).

When the active accounts outnumber the limit of the plan — a smaller plan, or a restore that brought more users than the
plan holds — the instance is **over the limit**. The state is never stored: every question reads the accounts again
(``over_limit_state``), so a restore needs no special code and two workers never disagree. While it stands, ordinary
users do not enter (``api/v1/user_limit.py``), and an administrator chooses who keeps the access (``list_for_choice``,
``resolve``): the others are **deactivated**, never deleted.

Rules, from the developer (26/10):

- The state is ``active > limit``, strictly. No limit, or a limit that cannot be read, is never a state: a typo in the
  variable must not lock everybody out (it still closes the registration, as before).
- Live invitations and the accounts that wait for their verification take places (``registration_service.user_usage``)
  without being users: they do not trigger the state. An invitation can be revoked to make room for a kept account; a
  waiting account cannot.
- The protected account stays: the owner of a managed instance (``user_service.account_protection``); without one, the
  administrator who chooses. At least one administrator must stay active.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.accounts import max_users as configured_max_users
from backend.app.db.models import BrokerUserAccess, User, UserRole
from backend.app.db.session import begin_writes
from backend.app.logging_config import get_logger
from backend.app.services.accounts import registration_service, user_service
from backend.app.utils.datetime_utils import utcnow

logger = get_logger(__name__)

Protection = Literal["owner", "you"]
ResolutionCode = Literal["NOT_OVER_LIMIT", "UNKNOWN_USER", "TOO_MANY_KEPT", "PROTECTED_MISSING", "NO_ADMIN_KEPT"]


class UserLimitError(Exception):
    """A resolution refused, with the code the API answers; nothing was changed."""

    def __init__(self, code: ResolutionCode, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class OverLimitState:
    """What the accounts say about the limit: the numbers of an instance that is over it."""

    active: int
    max_users: int
    live_invites: int
    waiting_accounts: int

    @property
    def max_keep(self) -> int:
        """Most accounts the administrator may keep: the limit less the accounts that wait (an invitation can be revoked)."""
        return max(0, self.max_users - self.waiting_accounts)


@dataclass(frozen=True)
class ChoiceUser:
    id: int
    username: str
    email: str
    is_superuser: bool
    protected: Optional[Protection]
    owned_brokers_alone: int


@dataclass(frozen=True)
class Choice:
    """What the administrator sees to choose; ``users`` is empty when the instance is not over the limit."""

    over_limit: bool
    active: int
    max_users: Optional[int]
    live_invites: int
    waiting_accounts: int
    max_keep: int
    users: list[ChoiceUser]


@dataclass(frozen=True)
class Resolution:
    kept: int
    deactivated: int
    revoked_invites: int


def _limit() -> Optional[int]:
    """``LIBREFOLIO_MAX_USERS``; None when there is none or it cannot be read (the registration reports that, once)."""
    try:
        return configured_max_users()
    except ValueError:
        return None


async def _active_count(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))).scalar() or 0  # type: ignore[attr-defined]


async def over_limit_state(session: AsyncSession) -> Optional[OverLimitState]:
    """The state, or None while the active accounts do not outnumber the limit. One ``COUNT``; nothing else without a limit."""
    limit = _limit()
    if limit is None:
        return None
    active = await _active_count(session)
    if active <= limit:
        return None
    usage = await registration_service.user_usage(session)
    invites = len(await registration_service.list_pending_invites(session))
    return OverLimitState(active=active, max_users=limit, live_invites=invites, waiting_accounts=max(0, usage.used - active - invites))


async def _brokers_owned_alone(session: AsyncSession) -> dict[int, int]:
    """How many brokers each account owns alone: those where it is the only OWNER."""
    sole = select(BrokerUserAccess.broker_id).where(BrokerUserAccess.role == UserRole.OWNER).group_by(BrokerUserAccess.broker_id).having(func.count() == 1).subquery()
    statement = select(BrokerUserAccess.user_id, func.count()).where(BrokerUserAccess.role == UserRole.OWNER, BrokerUserAccess.broker_id.in_(select(sole.c.broker_id))).group_by(BrokerUserAccess.user_id)  # type: ignore[attr-defined]
    return dict((await session.execute(statement)).all())


async def _active_users(session: AsyncSession) -> list[User]:
    return list((await session.execute(select(User).where(User.is_active.is_(True)).order_by(User.id))).scalars().all())  # type: ignore[attr-defined]


def _protection(users: list[User], chooser: User) -> dict[int, Protection]:
    """Who must stay: the protected owner of a managed instance; the chooser only when there is no such owner."""
    owners = {user.id: "owner" for user in users if user_service.account_protection(user) is not None}
    if owners:
        return owners  # type: ignore[return-value]
    return {chooser.id: "you"}


async def list_for_choice(session: AsyncSession, admin: User) -> Choice:
    """What the administrator chooses from. Not over the limit: ``over_limit`` False and no users."""
    state = await over_limit_state(session)
    if state is None:
        return Choice(over_limit=False, active=await _active_count(session), max_users=_limit(), live_invites=0, waiting_accounts=0, max_keep=0, users=[])
    users = await _active_users(session)
    protection = _protection(users, admin)
    alone = await _brokers_owned_alone(session)
    rows = [ChoiceUser(id=user.id, username=user.username, email=user.email, is_superuser=user.is_superuser, protected=protection.get(user.id), owned_brokers_alone=alone.get(user.id, 0)) for user in users]
    return Choice(over_limit=True, active=state.active, max_users=state.max_users, live_invites=state.live_invites, waiting_accounts=state.waiting_accounts, max_keep=state.max_keep, users=rows)


async def resolve(session: AsyncSession, admin: User, keep_user_ids: list[int]) -> Resolution:
    """Keep the access of ``keep_user_ids``, deactivate the other active accounts: one transaction, committed here.

    Read again under SQLite's write lock (A-56): of two administrators confirming at once, the second finds the state gone
    (``NOT_OVER_LIMIT``). Every refusal rolls back and changes nothing. The accounts are deactivated as ``user_service``
    deactivates them (sessions ended, verification and setup links retired), never deleted. Live invitations are revoked,
    the newest first, only as far as the kept accounts need their places.
    """
    await begin_writes(session, User)
    state = await over_limit_state(session)
    if state is None:
        await session.rollback()
        raise UserLimitError("NOT_OVER_LIMIT", "The instance is not over its limit of users")
    users = await _active_users(session)
    by_id = {user.id: user for user in users}
    keep = set(keep_user_ids)
    if keep - by_id.keys():
        await session.rollback()
        raise UserLimitError("UNKNOWN_USER", "A chosen account is not an active account of this instance")
    if len(keep) > state.max_keep:
        await session.rollback()
        raise UserLimitError("TOO_MANY_KEPT", "More accounts chosen than the plan holds")
    protected = set(_protection(users, admin))
    if protected - keep:
        await session.rollback()
        raise UserLimitError("PROTECTED_MISSING", "The owner of the instance, or the administrator who chooses, must stay")
    if not any(by_id[user_id].is_superuser for user_id in keep):
        await session.rollback()
        raise UserLimitError("NO_ADMIN_KEPT", "At least one administrator must keep the access")

    deactivated = [user for user in users if user.id not in keep]
    for user in deactivated:
        await user_service.deactivate_for_limit(session, user)
    revoked = 0
    surplus = len(keep) + state.live_invites + state.waiting_accounts - state.max_users
    if surplus > 0:
        moment = utcnow()
        newest_first = sorted(await registration_service.list_pending_invites(session, now=moment), key=lambda invite: (invite.created_at, invite.id), reverse=True)
        for invite in newest_first[:surplus]:
            if await registration_service.revoke_invite(session, invite.id, now=moment):
                revoked += 1
    await session.commit()
    logger.warning("The users over the limit were chosen", admin_id=admin.id, kept=len(keep), deactivated=[user.id for user in deactivated], revoked_invites=revoked, max_users=state.max_users)
    return Resolution(kept=len(keep), deactivated=len(deactivated), revoked_invites=revoked)
