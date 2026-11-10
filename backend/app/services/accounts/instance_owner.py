"""The owner of a managed instance, and the change of its address from the host (release 1.3, workstream A, lot A5-1b part 2).

On a managed instance (``LIBREFOLIO_PROFILE=managed``) the hoster names the paying administrator in
``LIBREFOLIO_ADMIN_EMAIL``; that account is the *owner*, recorded in ``users.is_instance_owner`` (migration 005, at most
one row) because the variable's address cannot identify it once the variable has changed. The owner cannot change its
own address from the app (409 ``ACCOUNT_PROTECTED``): the real change starts from the host.

The flow. The hoster updates the variable and restarts the instance. At that start the step ``owner-sync`` (after
``restore-commit``: a restore's commit revokes every live one-time link, so a link issued earlier would arrive dead)
(``startup_owner_sync``) compares the variable with the recorded owner, managed only:

(a) the initial administrator still waits for its setup (``pending_admin``): nothing here; ``bootstrap_admin_service``
    follows the variable as it always did, and the owner flag is already on that account;
(b) no owner recorded: the account holding the variable's address is recorded as the owner (self-healing; it also covers
    an instance created before the flag existed) only if it is an ACTIVE ADMINISTRATOR; otherwise an error is logged
    (no address, no name) and nobody is recorded. Nothing else;
(c) the owner holds the variable's address (A–Z case aside): nothing; links left from an earlier value are revoked;
(d) the address differs: another account holds the variable's address, or is a username that would shadow it → ``blocked``
    (an error line, no change; ``owner_change_status`` shows it); a live ``email_change`` link of the owner already
    carries it → ``waiting`` (nothing is resent at every restart: the plaintext is not kept); otherwise the owner's older
    links are revoked and a new one is issued — 7 days, carrying the new address — and goes by email to the NEW address.
    The link goes in the startup log (a warning) only when that email did not go: email off or unusable, no usable
    ``LIBREFOLIO_PUBLIC_URL``, the hourly budget spent, the SMTP server refusing. It is how the operator gets it, as for the
    ``/setup`` link. The delivery runs in the background: an SMTP server slow to answer does not hold the start.

Until the click nothing changes — address, flag, sessions —, and the protection stays on the owner. The click
(``POST /email/email-change/confirm``, ``confirm_email_change``) needs no session; in one transaction it moves the owner to
the link's address, verified, ends its sessions and revokes its other change and reset links. The protection then follows
the new address as well as the flag. The notice to the old address is the route's, after the commit.

Why one module, not ``bootstrap_admin_service``: that file is the initial administrator's lifecycle (a waiting account);
this one is the active owner's, and the two meet only in ``pending_admin``. ``account_protection`` is told the owner's id by
the sync (``user_service.note_recorded_owner``): see its docstring for what that rule decides.

No log line holds a token or an address.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal, Optional

import structlog
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.config import get_settings
from backend.app.config.accounts import owner_admin_email
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import auth_service, registration_service, token_service, user_service
from backend.app.services.accounts.bootstrap_admin_service import pending_admin
from backend.app.services.email.delivery import EmailError, send_email
from backend.app.services.email.flows import account_language, require_email
from backend.app.services.email.links import email_link, require_links
from backend.app.services.email.messages import build_email_change_confirmation, build_password_reset_after_restore
from backend.app.utils.datetime_utils import ensure_utc, utcnow

logger = structlog.get_logger(__name__)

CHANGE = AccountTokenPurpose.EMAIL_CHANGE


class OwnerSyncAction(StrEnum):
    """What the startup did about the owner's address."""

    OFF = "off"
    PENDING_ADMIN = "pending_admin"
    NO_OWNER = "no_owner"
    HEALED = "healed"
    UNCHANGED = "unchanged"
    BLOCKED = "blocked"
    WAITING = "waiting"
    ISSUED = "issued"
    FAILED = "failed"


@dataclass(frozen=True)
class OwnerSyncResult:
    """The outcome of ``run_owner_sync``. ``link_token`` and ``new_address`` (the delivery's) exist only after ISSUED and never reach a log."""

    action: OwnerSyncAction
    user_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    link_token: Optional[str] = field(default=None, repr=False)
    new_address: Optional[str] = field(default=None, repr=False)


def _variable() -> Optional[str]:
    """``LIBREFOLIO_ADMIN_EMAIL`` when this instance is managed and the variable is usable; None otherwise."""
    if get_settings().LIBREFOLIO_PROFILE != "managed":
        return None
    return owner_admin_email()


async def recorded_owner(session: AsyncSession) -> Optional[User]:
    """The account recorded as the instance owner, read fresh; None when nobody is."""
    statement = select(User).where(User.is_instance_owner == True).execution_options(populate_existing=True)  # type: ignore[arg-type]  # noqa: E712 — SQL `= 1`, the term of the partial index
    return (await session.execute(statement)).scalars().first()


async def _address_taken(session: AsyncSession, address: str, owner_id: int) -> bool:
    """Whether an account other than the owner holds ``address``, or has it as its username (A-21a, rule 2)."""
    holder = await user_service.get_user_by_email(session, address)
    if holder is not None and holder.id != owner_id:
        return True
    return await user_service.address_is_a_username(session, address, other_than=owner_id)


async def _live_links(session: AsyncSession, owner_id: int, now: datetime) -> list[AccountToken]:
    """The owner's ``email_change`` links neither spent nor revoked nor expired."""
    statement = (
        select(AccountToken)
        .where(
            AccountToken.user_id == owner_id,
            AccountToken.purpose == CHANGE,
            AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
            AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
            AccountToken.expires_at > now,
        )
        .execution_options(populate_existing=True)
    )
    return list((await session.execute(statement)).scalars().all())


def _carrying(links: list[AccountToken], address: str) -> Optional[AccountToken]:
    return next((link for link in links if link.email is not None and user_service.same_email(link.email, address)), None)


def _log_blocked(owner_id: int) -> None:
    """The one error line of a change that cannot go on because another account holds the variable's address: no address, no name."""
    logger.error(
        "LIBREFOLIO_ADMIN_EMAIL belongs to another account: the instance owner keeps its address and its protection, no confirmation link is sent. Free the address or change the variable",
        owner_id=owner_id,
    )


async def _heal(session: AsyncSession, variable: str) -> OwnerSyncResult:
    """No owner recorded: the ACTIVE ADMINISTRATOR with the variable's address becomes it; nobody else does.

    An ordinary account that put a free address equal to the variable in its profile, or a self-hosted backup restored on a
    managed instance, must not become the permanent owner: the account is recorded only when it is an administrator and
    active. The owner the bootstrap creates is flagged by the bootstrap itself, not here.
    """
    holder = await user_service.get_user_by_email(session, variable)
    if holder is None:
        user_service.note_recorded_owner(None)
        return OwnerSyncResult(OwnerSyncAction.NO_OWNER)
    if not (holder.is_superuser and holder.is_active):
        logger.error("The account with LIBREFOLIO_ADMIN_EMAIL is not an active administrator: the owner is not recorded", account_id=holder.id)
        user_service.note_recorded_owner(None)
        return OwnerSyncResult(OwnerSyncAction.NO_OWNER)
    holder_id = holder.id
    holder.is_instance_owner = True
    session.add(holder)
    try:
        await session.commit()
    except IntegrityError:
        # Another worker of the same start recorded another account first: the index allows one owner.
        await session.rollback()
        other = await recorded_owner(session)
        other_id = other.id if other is not None else None
        user_service.note_recorded_owner(other_id)
        return OwnerSyncResult(OwnerSyncAction.UNCHANGED, user_id=other_id)
    user_service.note_recorded_owner(holder_id)
    logger.info("Instance owner recorded: the account with the address of LIBREFOLIO_ADMIN_EMAIL", user_id=holder_id)
    return OwnerSyncResult(OwnerSyncAction.HEALED, user_id=holder_id)


async def _drop_stale_links(session: AsyncSession, owner_id: int, now: datetime) -> None:
    """The owner holds the variable's address: a live link from an earlier value of the variable is revoked (written only when there is one)."""
    if await _live_links(session, owner_id, now):
        await token_service.revoke_tokens(session, user_id=owner_id, purpose=CHANGE, now=now)
        await session.commit()
        logger.info("Links of an earlier LIBREFOLIO_ADMIN_EMAIL revoked: the owner holds the current address", user_id=owner_id)


async def _issue_link(session: AsyncSession, owner_id: int, variable: str, now: datetime) -> OwnerSyncResult:
    """Issue the link for ``variable`` under SQLite's write lock, so that two workers of one start issue one."""
    # The reads before this end here; the first write takes the lock, and what follows sees what another worker committed.
    await session.commit()
    users = User.__table__  # type: ignore[attr-defined]
    await session.execute(users.update().where(users.c.id == owner_id).values(updated_at=users.c.updated_at))
    links = await _live_links(session, owner_id, now)
    waiting = _carrying(links, variable)
    if waiting is not None:
        # Read before the rollback: it expires the row, and an async session cannot reload it
        expires_at = ensure_utc(waiting.expires_at)
        await session.rollback()
        return OwnerSyncResult(OwnerSyncAction.WAITING, user_id=owner_id, expires_at=expires_at)
    if await _address_taken(session, variable, owner_id):
        await session.rollback()
        _log_blocked(owner_id)
        return OwnerSyncResult(OwnerSyncAction.BLOCKED, user_id=owner_id)
    await token_service.revoke_tokens(session, user_id=owner_id, purpose=CHANGE, now=now)
    issued = await token_service.issue_token(session, CHANGE, user_id=owner_id, email=variable, now=now)
    expires_at = issued.record.expires_at
    await session.commit()
    logger.info("Confirmation link for the instance owner's new address issued", user_id=owner_id, expires_at=expires_at.isoformat())
    return OwnerSyncResult(OwnerSyncAction.ISSUED, user_id=owner_id, expires_at=expires_at, link_token=issued.token, new_address=variable)


async def run_owner_sync(session: AsyncSession, *, now: Optional[datetime] = None) -> OwnerSyncResult:
    """Apply the module docstring's branches (a) to (d); commits what it writes. Nothing outside a managed instance."""
    variable = _variable()
    if variable is None:
        return OwnerSyncResult(OwnerSyncAction.OFF)
    moment = now or utcnow()
    if await pending_admin(session) is not None:
        return OwnerSyncResult(OwnerSyncAction.PENDING_ADMIN)
    owner = await recorded_owner(session)
    if owner is None:
        return await _heal(session, variable)
    owner_id, owner_email = owner.id, owner.email
    user_service.note_recorded_owner(owner_id)
    if user_service.same_email(owner_email, variable):
        await _drop_stale_links(session, owner_id, moment)
        return OwnerSyncResult(OwnerSyncAction.UNCHANGED, user_id=owner_id)
    if await _address_taken(session, variable, owner_id):
        _log_blocked(owner_id)
        return OwnerSyncResult(OwnerSyncAction.BLOCKED, user_id=owner_id)
    waiting = _carrying(await _live_links(session, owner_id, moment), variable)
    if waiting is not None:
        return OwnerSyncResult(OwnerSyncAction.WAITING, user_id=owner_id, expires_at=ensure_utc(waiting.expires_at))
    return await _issue_link(session, owner_id, variable, moment)


async def owner_change_status(session: AsyncSession) -> Literal["pending", "blocked"] | None:
    """Where the change of the owner's address stands, for the security checks and the hosting panel. Reads only.

    ``"pending"``: managed, an owner recorded, its address is not the variable's and the change is not completed, whether or
    not a live link exists. ``"blocked"``: the same, and another account holds the variable's address (the sync does not
    move). ``None`` otherwise: another profile, no usable variable, no owner recorded, the same address, or the initial
    administrator still waiting for its setup. It never returns or logs an address.
    """
    variable = _variable()
    if variable is None or await pending_admin(session) is not None:
        return None
    owner = await recorded_owner(session)
    if owner is None or user_service.same_email(owner.email, variable):
        return None
    return "blocked" if await _address_taken(session, variable, owner.id) else "pending"


async def deliver_owner_change_link(result: OwnerSyncResult, *, engine: Optional[AsyncEngine] = None, now: Optional[datetime] = None) -> None:
    """Hand over a new link: by email to the new address, and in the startup log only when the email did not go. Never raises.

    It opens a session of its own: the startup runs it in the background, once the server is up.
    """
    if result.action != OwnerSyncAction.ISSUED or result.link_token is None or result.user_id is None or result.new_address is None:
        return
    moment = now or utcnow()
    token, user_id = result.link_token, result.user_id
    emailed = False
    try:
        await require_email()
        links = require_links()
        async with AsyncSession(engine or get_async_engine(), expire_on_commit=False) as session:
            owner = await user_service.get_user_by_id(session, user_id)
            if owner is None:
                raise LookupError("the owner is gone")
            ttl = max(ensure_utc(result.expires_at) - ensure_utc(moment), timedelta(0)) if result.expires_at else timedelta(0)
            content = build_email_change_confirmation(
                language=await account_language(session, user_id),
                username=owner.username,
                link=email_link(CHANGE, token),
                ttl=ttl,
                instance=links.instance,
            )
        await send_email(content, to=result.new_address, user_id=user_id)
        emailed = True
        logger.info("Confirmation link for the instance owner's new address emailed", user_id=user_id)
    except Exception as exc:  # noqa: BLE001 — isolation boundary of a background task: the link goes to the log below
        logger.info("Confirmation link for the instance owner's new address not emailed", user_id=user_id, reason=type(exc).__name__, code=getattr(exc, "code", None))
    if emailed:
        return
    path = token_service.token_path(CHANGE, token)
    url = registration_service.public_link(path)
    logger.warning(
        "Confirmation link for the instance owner's new email address, single use: open it from that address to complete the change",
        link=url or path,
        expires_at=result.expires_at.isoformat() if result.expires_at else None,
        note=None if url else "LIBREFOLIO_PUBLIC_URL is not set: put the address of your server in front of the path",
    )


#: The deliveries still running: a reference to each task, so none is garbage-collected before it ends.
_DELIVERIES: set[asyncio.Task] = set()


#: What this process's last run of the startup step found, for the synchronous configuration checks (they read no database):
#: see ``startup_change_state``. A worker runs its own step, so each knows its own start.
_startup_state: Optional[Literal["pending", "blocked"]] = None


def startup_change_state() -> Literal["pending", "blocked"] | None:
    """Where the change of the owner's address stood when this process started, for the security checks: ``"pending"`` while it
    waits for the owner's click (a link issued, or one still live), ``"blocked"`` when another account holds the new address,
    ``None`` otherwise — and ``None`` again once the owner has confirmed. Memory only: no database, never an address."""
    return _startup_state


def _remember(result: OwnerSyncResult) -> OwnerSyncResult:
    """Keep what the step found for ``startup_change_state``: only ISSUED/WAITING wait for the click, only BLOCKED is stuck."""
    global _startup_state  # noqa: PLW0603 — one state per process, set by the startup step and cleared by the confirmation
    if result.action in (OwnerSyncAction.ISSUED, OwnerSyncAction.WAITING):
        _startup_state = "pending"
    elif result.action == OwnerSyncAction.BLOCKED:
        _startup_state = "blocked"
    else:
        _startup_state = None
    return result


async def startup_owner_sync(engine: Optional[AsyncEngine] = None) -> OwnerSyncResult:
    """The startup step ``owner-sync``: the owner's address compared with the variable, a new link delivered in the background."""
    if _variable() is None:
        return _remember(OwnerSyncResult(OwnerSyncAction.OFF))
    engine = engine or get_async_engine()
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            result = await run_owner_sync(session)
    except OperationalError as exc:
        # Another worker of the same start holds SQLite's write lock and applies the same change.
        if "locked" not in str(exc):
            logger.error("Instance owner sync failed: the start goes on", error_type=type(exc).__name__)
            return _remember(OwnerSyncResult(OwnerSyncAction.FAILED))
        return _remember(OwnerSyncResult(OwnerSyncAction.WAITING))
    except Exception as exc:  # noqa: BLE001 — a fault here must not keep a hosted instance from starting; it is reported
        logger.error("Instance owner sync failed: the start goes on", exc_info=exc)
        return _remember(OwnerSyncResult(OwnerSyncAction.FAILED))
    _remember(result)
    if result.action == OwnerSyncAction.ISSUED and result.link_token is not None:
        # An SMTP server slow to answer must not hold the start: the link goes out once the server runs.
        task = asyncio.create_task(deliver_owner_change_link(result, engine=engine))
        _DELIVERIES.add(task)
        task.add_done_callback(_DELIVERIES.discard)
    return result


class OwnerEmailChangeLinkInvalidError(EmailError):
    """The link is not a live change link of the owner as things are now: ``code`` is the token's status (``revoked`` when the conditions no longer hold)."""


@dataclass(frozen=True)
class ConfirmedEmailChange:
    """What the click changed: the owner as it is now, and the address it had."""

    user: User
    old_email: str


async def _refusal(session: AsyncSession, user: Optional[User], address: Optional[str]) -> Optional[str]:
    """Why the change cannot go on, as a stable word for the log; None when it can."""
    if get_settings().LIBREFOLIO_PROFILE != "managed":
        return "not_managed"
    if user is None or not user.is_instance_owner:
        return "not_owner"
    if address is None:
        return "no_address"
    variable = owner_admin_email()
    if variable is None or not user_service.same_email(address, variable):
        return "variable_changed"
    if await _address_taken(session, address, user.id):
        return "address_taken"
    return None


async def confirm_email_change(session: AsyncSession, token: str, *, now: Optional[datetime] = None) -> ConfirmedEmailChange:
    """Spend a change link: the owner moves to the link's address, verified, its sessions end; commits.

    Raises ``OwnerEmailChangeLinkInvalidError`` with the token's status when it is not a live ``email_change`` link, and
    with ``revoked`` — the link revoked, nothing changed — when it no longer matches the instance: not managed, the account
    is not the recorded owner, the link carries no address, the host changed the variable again, or another account took
    the address meanwhile. The owner's other change links and its password-reset links (a mailbox that is no longer its
    own) are revoked with the change.
    """
    moment = now or utcnow()
    # The write comes first: it takes SQLite's write lock, and of two clicks racing for the same link only one spends it.
    record = await token_service.consume_token(session, token, CHANGE, now=moment)
    if record is None:
        await session.rollback()
        inspection = await token_service.inspect_token(session, token, CHANGE, now=moment)
        status = inspection.status if inspection.status != token_service.TokenStatus.VALID else token_service.TokenStatus.CONSUMED
        raise OwnerEmailChangeLinkInvalidError(status.value)
    token_id, address, user_id = record.id, record.email, record.user_id
    user = await user_service.get_user_by_id(session, user_id) if user_id is not None else None
    reason = await _refusal(session, user, address)
    if reason is None and user is not None and address is not None:
        old_email = user.email
        try:
            # A savepoint: should the unique index on lower(email) catch an account that took the address after the check,
            # only the change is undone, and the link is revoked below in this same transaction
            async with session.begin_nested():
                user.email = address
                user.email_verified_at = moment
                user.updated_at = moment
                record.consumed_by_user_id = user.id
                session.add(user)
                session.add(record)
                await user_service.end_sessions(session, user)
                await token_service.revoke_tokens(session, user_id=user.id, purpose=CHANGE, now=moment)
                await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.PASSWORD_RESET, now=moment)
                await session.flush()
        except IntegrityError:
            reason = "address_taken"
        else:
            await session.commit()
            await session.refresh(user)
            logger.info("Instance owner's email changed through its confirmation link, sessions ended", user_id=user.id, token_id=token_id)
            global _startup_state  # noqa: PLW0603 — nothing waits for the owner's click any more
            _startup_state = None
            return ConfirmedEmailChange(user=user, old_email=old_email)
    # Not applied: the link was spent for nothing, so it is revoked, in this same transaction (the spending is undone in the
    # same statement, and committed once): there is no moment at which it is neither spent nor revoked
    await session.execute(update(AccountToken).where(AccountToken.id == token_id).values(consumed_at=None, consumed_by_user_id=None, revoked_at=moment).execution_options(synchronize_session=False))
    await session.commit()
    logger.info("Owner email change link refused and revoked", token_id=token_id, reason=reason)
    raise OwnerEmailChangeLinkInvalidError(token_service.TokenStatus.REVOKED.value)


# =============================================================================
# A5-2: a restore on a managed instance gives the instance to the owner the administrator chose
# =============================================================================


class OwnerResetOutcome(StrEnum):
    """Where the owner's password link went: by email, or into the instance's log."""

    SENT = "sent"
    LINK_ONLY = "link_only"


@dataclass(frozen=True)
class OwnerResetResult:
    """The outcome of ``assign_owner_and_send_reset``. It holds nothing secret and its ``repr`` shows no address or name:
    the link is in the email or, when the email could not go, in the instance's log (``link_only``)."""

    outcome: OwnerResetOutcome
    user_id: int
    username: str = field(repr=False)
    email: str = field(repr=False)
    expires_at: Optional[datetime] = None


class OwnerAssignmentError(Exception):
    """A precondition of the assignment is missing; nothing was written. ``code``: ``NOT_MANAGED``, ``OWNER_EMAIL_NOT_SET``, ``USER_NOT_FOUND`` or ``EMAIL_TAKEN``."""

    def __init__(self, code: Literal["NOT_MANAGED", "OWNER_EMAIL_NOT_SET", "USER_NOT_FOUND", "EMAIL_TAKEN"]) -> None:
        super().__init__(code)
        self.code = code


async def _assign_account(session: AsyncSession, user: User, owner_email: str, moment: datetime) -> None:
    """Make ``user`` the owner: every other account loses the mark first (the unique index allows one), then ``user`` gets the
    owner's address, administrator and active, the mark, and a verified address."""
    users = User.__table__  # type: ignore[attr-defined]
    await session.execute(users.update().where(users.c.is_instance_owner == 1, users.c.id != user.id).values(is_instance_owner=False))
    user.email = owner_email
    user.is_superuser = True
    user.is_active = True
    user.is_instance_owner = True
    user.email_verified_at = moment
    user.updated_at = moment
    session.add(user)
    await session.flush()


async def _neutralise_tokens(session: AsyncSession, user_id: int, moment: datetime) -> None:
    """Whoever prepared a backup also wrote its tokens: the account's ``password_reset`` rows are DELETED (their history is
    unreliable, and a row dated in the future would hold «forgot password» back for ever), its live tokens of every other
    purpose are revoked."""
    await session.execute(delete(AccountToken).where(AccountToken.user_id == user_id, AccountToken.purpose == AccountTokenPurpose.PASSWORD_RESET).execution_options(synchronize_session=False))
    for purpose in AccountTokenPurpose:
        if purpose != AccountTokenPurpose.PASSWORD_RESET:
            await token_service.revoke_tokens(session, user_id=user_id, purpose=purpose, now=moment)


async def _deliver_reset_link(session: AsyncSession, user_id: int, owner_email: str, token: str, token_id: int, expires_at: datetime, moment: datetime) -> bool:
    """Email the reset link to the owner's address; when it cannot go — in any way — write the link in the instance's log (a
    warning, the hoster's channel, as ``deliver_owner_change_link`` does) and say False. Never raises. When the email went
    the link is in no log."""
    try:
        await require_email()
        links = require_links()
        content = build_password_reset_after_restore(
            language=await account_language(session, user_id),
            link=email_link(AccountTokenPurpose.PASSWORD_RESET, token),
            ttl=max(ensure_utc(expires_at) - ensure_utc(moment), timedelta(0)),
            instance=links.instance,
        )
        await send_email(content, to=owner_email, user_id=user_id)
    except Exception as exc:  # noqa: BLE001 — after the commit nothing may raise: the link goes to the log below
        logger.warning("Owner reset link not emailed: it is in the log of the instance", user_id=user_id, token_id=token_id, reason=type(exc).__name__, code=getattr(exc, "code", None))
        path = token_service.token_path(AccountTokenPurpose.PASSWORD_RESET, token)
        url = registration_service.public_link(path)
        logger.warning(
            "Password-reset link for the instance owner, single use: send it to the owner so that it chooses its password",
            link=url or path,
            expires_at=expires_at.isoformat(),
            note=None if url else "LIBREFOLIO_PUBLIC_URL is not set: put the address of your server in front of the path",
        )
        return False
    logger.info("Owner reset link emailed", user_id=user_id, token_id=token_id)
    return True


async def assign_owner_and_send_reset(session: AsyncSession, user_id: int, *, now: Optional[datetime] = None) -> OwnerResetResult:
    """Give a managed instance restored from a backup to the account the owner chose (A5-2); commits once, then sends.

    Called by the restore (B), ONCE, at the first start after the database swap, with the id of the chosen account in the
    restored database. NOTHING in that database is trusted — a backup may come from anywhere, and whoever prepared it wrote
    its tokens too — so every call gives the full treatment, in one transaction under SQLite's write lock: the preconditions;
    the owner mark of every other account cleared, then the chosen account gets the owner's address, administrator, active,
    the mark; its password made unusable and its sessions ended; its ``password_reset`` rows deleted and its live tokens of
    every other purpose revoked (``_neutralise_tokens``); one new reset link, marked with the owner's address. Then the link
    is emailed to that address; if the email cannot go the outcome is ``link_only`` and the link is in the log of the
    instance (a warning), never in the result. The protection follows (``note_recorded_owner``).

    A second call repeats the treatment: the previous link dies and a new one is sent (one more email, no harm). At-most-once
    is the caller's, kept in the restore's own state, never in the database.

    The caller must know three things. (1) The first statement is a ``commit`` of the caller's session, which commits any
    work the session had pending: pass a session with nothing else in it. (2) The caller must repeat on the server the check
    of the choice the owner made in the restore's dialog — if an account already has the owner's address, the only valid
    choice is that account; this function answers ``EMAIL_TAKEN`` for any other — and must FAIL CLOSED: a restore on a
    managed instance whose call did not happen, or raised ``OwnerAssignmentError``, is not complete, and must not serve the
    restored accounts. (3) The password hash is never read.

    Raises ``OwnerAssignmentError`` before writing anything: ``NOT_MANAGED``, ``OWNER_EMAIL_NOT_SET``, ``USER_NOT_FOUND``,
    ``EMAIL_TAKEN`` (another account has the address, or has it as its username).
    """
    moment = now or utcnow()
    if get_settings().LIBREFOLIO_PROFILE != "managed":
        raise OwnerAssignmentError("NOT_MANAGED")
    owner_email = owner_admin_email()
    if owner_email is None:
        raise OwnerAssignmentError("OWNER_EMAIL_NOT_SET")
    # The reads before this end here; the first write takes the lock, and what follows sees what another call committed.
    await session.commit()
    users = User.__table__  # type: ignore[attr-defined]
    locked = await session.execute(users.update().where(users.c.id == user_id).values(updated_at=users.c.updated_at))
    if locked.rowcount == 0:
        await session.rollback()
        raise OwnerAssignmentError("USER_NOT_FOUND")
    user = (await session.execute(select(User).where(User.id == user_id).execution_options(populate_existing=True))).scalar_one()
    if await _address_taken(session, owner_email, user_id):
        await session.rollback()
        raise OwnerAssignmentError("EMAIL_TAKEN")
    username = user.username
    await _assign_account(session, user, owner_email, moment)
    # The preparer of the backup knows the password it carries: unusable until the owner chooses its own with the link
    user.hashed_password = await asyncio.to_thread(auth_service.unusable_password_hash)
    await user_service.end_sessions(session, user)
    await _neutralise_tokens(session, user_id, moment)
    issued = await user_service.create_password_reset(session, user, now=moment, email=owner_email)
    token, token_id, expires_at = issued.token, issued.record.id, ensure_utc(issued.record.expires_at)
    await session.commit()
    user_service.note_recorded_owner(user_id)
    logger.info("Instance owner assigned after a restore, reset link issued", user_id=user_id, token_id=token_id)
    outcome = OwnerResetOutcome.SENT if await _deliver_reset_link(session, user_id, owner_email, token, token_id, expires_at, moment) else OwnerResetOutcome.LINK_ONLY
    return OwnerResetResult(outcome, user_id, username, owner_email, expires_at=expires_at)
