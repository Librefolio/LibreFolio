"""Who may create an account, and how many accounts an instance may hold.

The registration mode is ``LIBREFOLIO_REGISTRATION`` when the operator sets it, otherwise the ``registration_mode``
global setting (``open`` by default). A value of that variable that is not a mode closes the registration instead of
opening it, and says so in the log; so does a stored value that is not a mode. The limit is ``LIBREFOLIO_MAX_USERS``:
active accounts and live invitations count against it, so an invitation keeps its place until it is used, revoked or
expired. An invalid limit closes too, as a limit of 0.

``register_user`` holds the whole rule of ``POST /auth/register`` and owns its transaction: the account, the invitation
it spends and the check of the limit are committed together, or not at all. ``create_invite`` and ``revoke_invite``
flush without committing, like the token service they build on.
"""

import functools
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, cast

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.accounts import REGISTRATION_MODES, billing_url, public_url, registration_mode_override
from backend.app.config.accounts import max_users as configured_max_users
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import token_service, user_service
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.utils.datetime_utils import ensure_utc, utcnow

logger = structlog.get_logger(__name__)

RegistrationMode = Literal["open", "invite", "disabled"]


class RegistrationError(Exception):
    """A registration or an invitation refused; ``code`` is the ``error_code`` the API answers with."""

    def __init__(self, code: str, message: Optional[str] = None):
        super().__init__(message or code)
        self.code = code
        self.message = message or code


@dataclass(frozen=True)
class RegistrationModeState:
    """The registration mode in force, and whether ``LIBREFOLIO_REGISTRATION`` pins it (the setting is then read-only)."""

    mode: RegistrationMode
    locked: bool


@dataclass(frozen=True)
class UserUsage:
    """Places taken (active accounts plus live invitations) against the limit, None when there is no limit."""

    used: int
    max_users: Optional[int]

    @property
    def full(self) -> bool:
        """No place left for a new account or invitation."""
        return self.max_users is not None and self.used >= self.max_users


@functools.cache
def _report_invalid(problem: str) -> None:
    """Log an invalid account setting once per process: the instance runs closed until it is fixed."""
    logger.error("Invalid account configuration: registration stays closed until it is fixed", problem=problem)


async def effective_registration_mode(session: AsyncSession) -> RegistrationModeState:
    """``LIBREFOLIO_REGISTRATION`` when set (an invalid value is ``disabled``), else the global setting."""
    try:
        pinned = registration_mode_override()
    except ValueError as exc:
        _report_invalid(str(exc))
        return RegistrationModeState(mode="disabled", locked=True)
    if pinned is not None:
        return RegistrationModeState(mode=cast(RegistrationMode, pinned), locked=True)
    stored = await get_setting_value(session, SETTINGS_REGISTRY.global_.REGISTRATION_MODE.key, "open")
    if stored not in REGISTRATION_MODES:
        _report_invalid(f"registration_mode={stored!r}: expected one of {', '.join(REGISTRATION_MODES)}")
        return RegistrationModeState(mode="disabled", locked=False)
    return RegistrationModeState(mode=cast(RegistrationMode, stored), locked=False)


def _max_users() -> Optional[int]:
    """``LIBREFOLIO_MAX_USERS``; an invalid value is a limit of 0."""
    try:
        return configured_max_users()
    except ValueError as exc:
        _report_invalid(str(exc))
        return 0


def public_link(path: str) -> Optional[str]:
    """``LIBREFOLIO_PUBLIC_URL`` followed by ``path``; None when the variable is unset, or invalid (logged once)."""
    try:
        base = public_url()
    except ValueError as exc:
        _report_invalid(str(exc))
        return None
    return f"{base}{path}" if base else None


def billing_link() -> Optional[str]:
    """``LIBREFOLIO_BILLING_URL``; None when it is unset, or invalid (logged once). For administrators only."""
    try:
        return billing_url()
    except ValueError as exc:
        _report_invalid(str(exc))
        return None


def _live_invites(now: datetime):
    """The conditions of an invitation that still holds a place: not used, not revoked, not expired."""
    return (
        AccountToken.purpose == AccountTokenPurpose.INVITE,
        AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
        AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
        AccountToken.expires_at > now,
    )


async def user_usage(session: AsyncSession, *, now: Optional[datetime] = None) -> UserUsage:
    """How many places are taken: active accounts plus live invitations."""
    moment = now or utcnow()
    active = (await session.execute(select(func.count()).select_from(User).where(User.is_active.is_(True)))).scalar() or 0  # type: ignore[attr-defined]
    invites = (await session.execute(select(func.count()).select_from(AccountToken).where(*_live_invites(moment)))).scalar() or 0
    return UserUsage(used=active + invites, max_users=_max_users())


async def create_invite(
    session: AsyncSession,
    *,
    created_by_user_id: Optional[int],
    grants_admin: bool = False,
    email: Optional[str] = None,
    now: Optional[datetime] = None,
    enforce_limit: bool = True,
) -> token_service.IssuedToken:
    """Issue an invitation (flushed, not committed). Refused when the registration is disabled or no place is left.

    ``enforce_limit=False`` is for the command line, which the operator may use past the limit.
    """
    if (await effective_registration_mode(session)).mode == "disabled":
        raise RegistrationError("REGISTRATION_DISABLED", "Registration is disabled: invitations cannot be created")
    if enforce_limit and (await user_usage(session, now=now)).full:
        raise RegistrationError("USER_LIMIT_REACHED", "The instance has reached its maximum number of users")
    issued = await token_service.issue_token(session, AccountTokenPurpose.INVITE, email=email, grants_admin=grants_admin, created_by_user_id=created_by_user_id, now=now)
    logger.info("Invitation created", invite_id=issued.record.id, grants_admin=grants_admin, created_by_user_id=created_by_user_id)
    return issued


async def list_pending_invites(session: AsyncSession, *, now: Optional[datetime] = None) -> list[AccountToken]:
    """The live invitations, oldest first."""
    statement = select(AccountToken).where(*_live_invites(now or utcnow())).order_by(AccountToken.created_at, AccountToken.id)
    return list((await session.execute(statement)).scalars().all())


async def revoke_invite(session: AsyncSession, invite_id: int, *, now: Optional[datetime] = None) -> bool:
    """Revoke a live invitation (flushed, not committed); False when ``invite_id`` is not one."""
    moment = now or utcnow()
    invite = await session.get(AccountToken, invite_id)
    if invite is None or invite.purpose != AccountTokenPurpose.INVITE or invite.consumed_at is not None or invite.revoked_at is not None or ensure_utc(invite.expires_at) <= ensure_utc(moment):
        return False
    revoked = await token_service.revoke_tokens(session, token_id=invite_id, purpose=AccountTokenPurpose.INVITE, now=moment)
    if revoked:
        logger.info("Invitation revoked", invite_id=invite_id)
    return revoked == 1


async def _admission(session: AsyncSession, invite_token: Optional[str], now: datetime) -> tuple[bool, bool, bool]:
    """Whether the new account is the instance's first, comes with an invitation, and is an administrator.

    Raises ``RegistrationError`` when the mode or the invitation refuses it.
    """
    if await user_service.count_users(session) == 0:
        return True, False, True
    mode = (await effective_registration_mode(session)).mode
    if mode == "disabled":
        raise RegistrationError("REGISTRATION_DISABLED", "New user registration is disabled")
    if not invite_token:
        if mode == "invite":
            raise RegistrationError("INVITE_REQUIRED", "Registration requires an invitation")
        return False, False, False
    inspection = await token_service.inspect_token(session, invite_token, AccountTokenPurpose.INVITE, now=now)
    if inspection.status != token_service.TokenStatus.VALID or inspection.record is None:
        raise RegistrationError("INVITE_INVALID", "This invitation is not valid")
    return False, True, inspection.record.grants_admin


async def register_user(
    session: AsyncSession,
    *,
    username: str,
    email: str,
    password: str,
    invite_token: Optional[str] = None,
    now: Optional[datetime] = None,
) -> User:
    """Create an account through registration, under the registration mode and the limit; commits.

    The first account of an empty instance is an administrator, whatever the mode. Otherwise ``disabled`` refuses
    everyone, ``invite`` requires a valid invitation, and ``open`` accepts anyone, with an invitation optional but
    valid when given. A valid invitation sets the role and already holds its place; without one, the limit is checked
    after the account is written, in the same transaction, so two registrations racing for the last place cannot both
    take it: the first to write holds SQLite's write lock until it commits.
    """
    moment = now or utcnow()
    first, invited, grants_admin = await _admission(session, invite_token, moment)

    user, error = await user_service.create_user(session, username, email, password, is_superuser=grants_admin, commit=False)
    if user is None:
        await session.rollback()
        raise RegistrationError("ACCOUNT_EXISTS", error)
    if invited and await token_service.consume_token(session, invite_token or "", AccountTokenPurpose.INVITE, consumed_by_user_id=user.id, now=moment) is None:
        await session.rollback()
        raise RegistrationError("INVITE_INVALID", "This invitation is not valid")
    if not invited and not first:
        usage = await user_usage(session, now=moment)
        if usage.max_users is not None and usage.used > usage.max_users:
            await session.rollback()
            raise RegistrationError("USER_LIMIT_REACHED", "The instance has reached its maximum number of users")
    await session.commit()
    await session.refresh(user)
    logger.info("User registered", user_id=user.id, username=user.username, is_superuser=user.is_superuser, invited=invited, first_user=first)
    return user
