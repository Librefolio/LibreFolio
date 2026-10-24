"""The initial administrator of a new instance, from environment variables (F02, release 1.3, workstream A, lot A7).

``LIBREFOLIO_ADMIN_EMAIL`` turns it on (``admin_bootstrap_config`` in ``backend/app/config/accounts.py``). On an
instance without accounts the startup step ``admin-bootstrap`` creates the administrator inactive, with the password
hash of a random secret nobody knows, sets registration to invitations only, and issues a single-use ``admin_setup``
link valid 72 hours. The link carries the token of ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`` when the hosting panel gives
one, and the panel delivers it; otherwise a generated token, logged once and emailed when email works.
``POST /auth/setup`` spends the link: the administrator chooses the password, the account becomes active, and signs in.

While the administrator waits, a restart issues nothing new. A token of the variable never seen before re-arms the link
for 72 hours, and ``./dev.py user setup-link`` issues a new one. An instance that already has other accounts ignores
the variables. With more than one worker only one creates the account and delivers its link: the creation takes
SQLite's write lock before it looks at the accounts, so the other worker finds the account waiting.

On a managed instance (``LIBREFOLIO_PROFILE=managed``) the account it creates is also recorded as the instance owner
(``users.is_instance_owner``): ``instance_owner.py`` (startup step ``owner-sync``) takes over once the account is active.
While it waits, a change of the variables follows the logic above, not the owner's confirmation link.

``admin_setup_status`` tells a hosting panel where the setup stands (H-61): none, pending until when, done, expired.
"""

import asyncio
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.config import get_settings
from backend.app.config.accounts import ADMIN_BOOTSTRAP_TOKEN_VARIABLE, AdminBootstrapConfig, admin_bootstrap_config
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS
from backend.app.services.accounts import registration_service, token_service, user_service
from backend.app.services.accounts.auth_service import hash_password
from backend.app.services.email.delivery import send_email
from backend.app.services.email.flows import instance_language, require_email
from backend.app.services.email.links import email_link, require_links
from backend.app.services.email.messages import build_admin_setup
from backend.app.utils.datetime_utils import ensure_utc, utcnow

logger = structlog.get_logger(__name__)

_SETUP = AccountTokenPurpose.ADMIN_SETUP
_SETUP_LINK_COMMAND = "./dev.py user setup-link"
_REGISTRATION_KEY = "registration_mode"


class BootstrapAction(StrEnum):
    """What the startup did with the F02 variables."""

    OFF = "off"
    IGNORED = "ignored"
    CREATED = "created"
    REARMED = "rearmed"
    PENDING = "pending"
    EXPIRED = "expired"


@dataclass(frozen=True)
class BootstrapResult:
    """The outcome of ``run_admin_bootstrap``; ``link_token`` is the plaintext of a generated link, only after CREATED."""

    action: BootstrapAction
    user_id: Optional[int] = None
    username: Optional[str] = None
    link_token: Optional[str] = None
    expires_at: Optional[datetime] = None


class AdminSetupState(StrEnum):
    """Where the setup of the initial administrator stands, for a hosting panel (H-61)."""

    NONE = "none"
    PENDING = "pending"
    DONE = "done"
    EXPIRED = "expired"


@dataclass(frozen=True)
class AdminSetupStatus:
    """The answer of ``admin_setup_status``: ``setup_expires_at``, in UTC, only while the setup waits (``pending``)."""

    state: AdminSetupState
    setup_expires_at: Optional[datetime] = None


async def admin_setup_status(session: AsyncSession, *, now: Optional[datetime] = None) -> AdminSetupStatus:
    """Where the setup of the initial administrator stands, read from its ``admin_setup`` links (H-61).

    None ever issued: ``none``. Any link consumed: ``done`` — spent by the setup, or retired because the account was
    activated or given a password another way (A-32). A consumption is final: no link is issued after one
    (``pending_admin`` wants none consumed), so a stray newer link left revoked does not undo it. Otherwise the latest
    link, by creation then id, decides: revoked without use — the setup cancelled (A-43), the address changed (A-33)
    — or past its expiry, ``expired``; else the setup waits, ``pending`` until ``setup_expires_at``. A replaced link
    is revoked, but the newer one is the latest and decides. Reads only: no write, no commit, no write lock.
    """
    moment = ensure_utc(now or utcnow())
    spent = await session.execute(select(AccountToken.id).where(AccountToken.purpose == _SETUP, AccountToken.consumed_at.is_not(None)).limit(1))  # type: ignore[union-attr]
    if spent.first() is not None:
        return AdminSetupStatus(AdminSetupState.DONE)
    result = await session.execute(select(AccountToken.revoked_at, AccountToken.expires_at).where(AccountToken.purpose == _SETUP).order_by(AccountToken.created_at.desc(), AccountToken.id.desc()).limit(1))  # type: ignore[union-attr]
    latest = result.first()
    if latest is None:
        return AdminSetupStatus(AdminSetupState.NONE)
    expires_at = ensure_utc(latest.expires_at)
    if latest.revoked_at is not None or expires_at <= moment:
        return AdminSetupStatus(AdminSetupState.EXPIRED)
    return AdminSetupStatus(AdminSetupState.PENDING, setup_expires_at=expires_at)


async def pending_admin(session: AsyncSession) -> Optional[User]:
    """The account waiting for its setup: inactive, with an ``admin_setup`` link, none of them used."""
    result = await session.execute(select(User).where(*registration_service.pending_admin_filter()).order_by(User.id).limit(1))  # type: ignore[arg-type]
    return result.scalars().first()


async def _live_setup_token(session: AsyncSession, user_id: int, now: datetime) -> Optional[AccountToken]:
    result = await session.execute(
        select(AccountToken).where(
            AccountToken.user_id == user_id,
            AccountToken.purpose == _SETUP,
            AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
            AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
            AccountToken.expires_at > now,
        )
    )
    return result.scalars().first()


async def _latest_setup_withdrawn(session: AsyncSession, user_id: int) -> bool:
    """Whether the account's latest setup link was revoked and never consumed: withdrawn, not expired (A-50).

    The setup cancelled (A-43), or the address changed at an earlier start (A-33): either revokes the live links.
    """
    result = await session.execute(select(AccountToken.revoked_at, AccountToken.consumed_at).where(AccountToken.user_id == user_id, AccountToken.purpose == _SETUP).order_by(AccountToken.created_at.desc(), AccountToken.id.desc()).limit(1))  # type: ignore[union-attr]
    latest = result.first()
    return latest is not None and latest.revoked_at is not None and latest.consumed_at is None


async def _token_known(session: AsyncSession, token: str) -> bool:
    """Whether ``token`` was ever stored, for any account or purpose: the same value is never stored twice."""
    result = await session.execute(select(AccountToken.id).where(AccountToken.token_hash == token_service.hash_token(token)))
    return result.first() is not None


async def _require_invitations(session: AsyncSession, now: datetime) -> None:
    """Write ``registration_mode`` = ``invite``, the row created when missing. ``LIBREFOLIO_REGISTRATION`` still wins."""
    default = GLOBAL_SETTINGS_DEFAULTS[_REGISTRATION_KEY]
    statement = (
        sqlite_insert(GlobalSetting)
        .values(key=_REGISTRATION_KEY, value="invite", value_type=default["type"], description=default["description"], updated_at=now, updated_by_user_id=None)
        .on_conflict_do_update(index_elements=["key"], set_={"value": "invite", "updated_at": now, "updated_by_user_id": None})
    )
    await session.execute(statement)


async def _create_pending_admin(session: AsyncSession, config: AdminBootstrapConfig, now: datetime) -> Optional[BootstrapResult]:
    """Create the waiting administrator on an empty instance; None when an account appeared meanwhile."""
    # The reads before this end here (committed, so nothing the caller left pending is lost), and the first statement
    # after is a write: it takes SQLite's write lock, so the count below sees what another worker committed, and only
    # one worker creates the account.
    await session.commit()
    await _require_invitations(session, now)
    if await user_service.count_users(session) > 0:
        await session.rollback()
        return None
    # A random secret nobody ever sees: a real bcrypt hash, so a login attempt costs what it costs for any account.
    user, error = await user_service.create_user(session, config.username, config.email, secrets.token_urlsafe(32), is_superuser=True, is_active=False, commit=False)
    if user is None:
        await session.rollback()
        logger.error("The initial administrator could not be created", error=error)
        return None
    if get_settings().LIBREFOLIO_PROFILE == "managed":
        # The account the hoster pays for is the instance owner (A5-1b): recorded from the start, so a later change of the
        # variable's address cannot lose who it is. Never in another profile.
        user.is_instance_owner = True
        session.add(user)
    given = config.token
    if given is not None and await _token_known(session, given):
        # A token is stored once: one already used (an earlier setup of an instance emptied since) is not handed out again.
        logger.warning(f"{ADMIN_BOOTSTRAP_TOKEN_VARIABLE} was already used: a new setup link is generated instead")
        given = None
    issued = await token_service.issue_token(session, _SETUP, user_id=user.id, token=given, now=now)
    user_id, username, expires_at = user.id, user.username, issued.record.expires_at
    await session.commit()
    logger.info(
        "Initial administrator created, waiting for its setup link",
        user_id=user_id,
        username=username,
        link_from=ADMIN_BOOTSTRAP_TOKEN_VARIABLE if given else "generated",
        expires_at=expires_at.isoformat(),
    )
    return BootstrapResult(BootstrapAction.CREATED, user_id=user_id, username=username, link_token=None if given else issued.token, expires_at=expires_at)


async def _follow_variables(session: AsyncSession, user: User, config: AdminBootstrapConfig, now: datetime) -> tuple[bool, bool]:
    """The waiting account takes the username and email of the variables, unless another account holds them.

    Whether anything changed, and whether the address did, beyond its case: the setup links handed over went to the
    earlier address, so they are revoked (A-33). The account still waits, for a link that reaches the new one.
    """
    changed = moved = False
    if user.username != config.username:
        if await user_service.get_user_by_username(session, config.username) is None:
            user.username, changed = config.username, True
        else:
            logger.error("LIBREFOLIO_ADMIN_USERNAME belongs to another account: the waiting administrator keeps its username", user_id=user.id)
    if user.email != config.email:
        # The same address in another case is this account's (decision P18): it takes the variable's form.
        same = user_service.same_email(user.email, config.email)
        if same or await user_service.get_user_by_email(session, config.email) is None:
            user.email, changed, moved = config.email, True, not same
        else:
            logger.error("LIBREFOLIO_ADMIN_EMAIL belongs to another account: the waiting administrator keeps its address", user_id=user.id)
    if moved:
        await token_service.revoke_tokens(session, user_id=user.id, purpose=_SETUP, now=now)
    if changed:
        user.updated_at = now
        session.add(user)
    return changed, moved


async def _keep_pending_admin(session: AsyncSession, user: User, config: AdminBootstrapConfig, now: datetime) -> BootstrapResult:
    """A restart while the administrator waits: follow the variables, re-arm with a new token, or say the link died."""
    user_id = user.id
    renamed, moved = await _follow_variables(session, user, config, now)
    username = user.username
    if config.token is not None and not await _token_known(session, config.token):
        await token_service.revoke_tokens(session, user_id=user_id, purpose=_SETUP, now=now)
        # The revocation took SQLite's write lock: «waiting» is read again under it (A-42), so a setup completed
        # since the first read leaves no live link behind
        if not await registration_service.is_pending_admin(session, user):
            await session.rollback()
            logger.info("LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN not re-armed: the initial administrator was set up meanwhile", user_id=user_id)
            return BootstrapResult(BootstrapAction.IGNORED)
        issued = await token_service.issue_token(session, _SETUP, user_id=user_id, token=config.token, now=now)
        expires_at = issued.record.expires_at
        await session.commit()
        logger.info("Setup link of the initial administrator re-armed from LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN", user_id=user_id, expires_at=expires_at.isoformat())
        return BootstrapResult(BootstrapAction.REARMED, user_id=user_id, username=username, expires_at=expires_at)
    live = await _live_setup_token(session, user_id, now)
    live_until = live.expires_at if live is not None else None
    if renamed:
        await session.commit()
    if live_until is not None:
        return BootstrapResult(BootstrapAction.PENDING, user_id=user_id, username=username, expires_at=live_until)
    remedy = f"run {_SETUP_LINK_COMMAND}" + (f", or set a new {ADMIN_BOOTSTRAP_TOKEN_VARIABLE}" if config.token is not None else "")
    if moved:
        logger.warning(f"The initial administrator's address changed: the setup link handed over before no longer works; {remedy}", user_id=user_id, username=username)
    elif await _latest_setup_withdrawn(session, user_id):
        logger.warning(f"The initial administrator's setup link was withdrawn (cancelled, or its address changed): {remedy}", user_id=user_id, username=username)
    else:
        logger.warning(f"The initial administrator's setup link has expired: {remedy}", user_id=user_id, username=username)
    return BootstrapResult(BootstrapAction.EXPIRED, user_id=user_id, username=username)


async def run_admin_bootstrap(session: AsyncSession, config: Optional[AdminBootstrapConfig], *, now: Optional[datetime] = None) -> BootstrapResult:
    """Apply the F02 variables to the instance; commits what it writes. See the module docstring."""
    if config is None:
        return BootstrapResult(BootstrapAction.OFF)
    moment = now or utcnow()
    waiting = await pending_admin(session)
    if waiting is None:
        if await user_service.count_users(session) > 0:
            logger.info("LIBREFOLIO_ADMIN_* ignored: this instance already has accounts")
            return BootstrapResult(BootstrapAction.IGNORED)
        created = await _create_pending_admin(session, config, moment)
        if created is not None:
            return created
        waiting = await pending_admin(session)
        if waiting is None:
            logger.info("LIBREFOLIO_ADMIN_* ignored: this instance already has accounts")
            return BootstrapResult(BootstrapAction.IGNORED)
    user_id, username = waiting.id, waiting.username
    try:
        return await _keep_pending_admin(session, waiting, config, moment)
    except OperationalError as exc:
        # Another worker of the same start writes the same change and holds the lock: it applies it.
        if "locked" not in str(exc):
            raise
        await session.rollback()
        return BootstrapResult(BootstrapAction.PENDING, user_id=user_id, username=username)


async def deliver_setup_link(result: BootstrapResult, *, engine: Optional[AsyncEngine] = None, now: Optional[datetime] = None) -> None:
    """Hand over a generated setup link: in the log once, and by email when email works. Never raises.

    It opens a session of its own: the startup runs it in the background, once the server is up.
    """
    if result.action != BootstrapAction.CREATED or result.link_token is None or result.user_id is None:
        return
    moment = now or utcnow()
    path = token_service.token_path(_SETUP, result.link_token)
    url = registration_service.public_link(path)
    logger.warning(
        "Setup link of the initial administrator, single use: open it to choose the password",
        link=url or path,
        expires_at=result.expires_at.isoformat() if result.expires_at else None,
        note=None if url else "LIBREFOLIO_PUBLIC_URL is not set: put the address of your server in front of the path",
    )
    try:
        await require_email()
        links = require_links()
        async with AsyncSession(engine or get_async_engine(), expire_on_commit=False) as session:
            user = await user_service.get_user_by_id(session, result.user_id)
            if user is None:
                return
            ttl = max(ensure_utc(result.expires_at) - ensure_utc(moment), timedelta(0)) if result.expires_at else timedelta(0)
            content = build_admin_setup(language=await instance_language(session), username=user.username, link=email_link(_SETUP, result.link_token), ttl=ttl, instance=links.instance)
            address, user_id = user.email, user.id
        await send_email(content, to=address, user_id=user_id)
        logger.info("Setup link of the initial administrator emailed", user_id=user_id)
    except Exception as exc:  # noqa: BLE001 — the link is in the log already: an email that cannot go is only reported
        logger.info("Setup link of the initial administrator not emailed", reason=type(exc).__name__)


#: The deliveries still running: a reference to each task, so none is garbage-collected before it ends.
_DELIVERIES: set[asyncio.Task] = set()


async def startup_admin_bootstrap(engine: Optional[AsyncEngine] = None) -> BootstrapResult:
    """The startup step ``admin-bootstrap``: the F02 variables applied, a generated link delivered in the background."""
    config = admin_bootstrap_config()
    if config is None:
        return BootstrapResult(BootstrapAction.OFF)
    engine = engine or get_async_engine()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await run_admin_bootstrap(session, config)
    if result.action == BootstrapAction.CREATED and result.link_token is not None:
        # An SMTP server slow to answer must not hold the start: the link goes out once the server runs.
        task = asyncio.create_task(deliver_setup_link(result, engine=engine))
        _DELIVERIES.add(task)
        task.add_done_callback(_DELIVERIES.discard)
    return result


async def _setup_spent_before(session: AsyncSession, user_id: int, spent_id: int) -> bool:
    """Whether a setup link of the account other than ``spent_id`` was consumed: its setup happened, or its links were retired."""
    other = select(AccountToken.id).where(
        AccountToken.user_id == user_id,
        AccountToken.purpose == _SETUP,
        AccountToken.id != spent_id,
        AccountToken.consumed_at.is_not(None),  # type: ignore[union-attr]
    )
    return (await session.execute(other.limit(1))).first() is not None


async def complete_admin_setup(session: AsyncSession, token: str, new_password: str, *, now: Optional[datetime] = None) -> Optional[User]:
    """Spend a setup link: the password set, the account active, its sessions ended, its other links revoked; commits.

    None, and nothing changed, for a link that is not a live setup link. The link of an account already active is
    refused too, and every setup link of the account retired (A-32): once the account is set up, by any path, its links
    must not set its password again, and a later deactivation must not make it wait for its setup again.
    """
    moment = now or utcnow()
    # The write comes first, as for a reset link: it takes SQLite's write lock, and of two requests racing for the same
    # link only one spends it.
    record = await token_service.consume_token(session, token, _SETUP, now=moment)
    user = await user_service.get_user_by_id(session, record.user_id) if record is not None and record.user_id is not None else None
    if user is None or record is None:
        await session.rollback()
        return None
    if user.is_active:
        user_id = user.id
        await session.rollback()
        await token_service.retire_tokens(session, user_id=user_id, purpose=_SETUP, now=moment)
        await session.commit()
        logger.warning("Setup link refused and retired: the account is already active", user_id=user_id)
        return None
    if await _setup_spent_before(session, user.id, record.id):
        # Another setup link of the account was consumed — the setup done, or its links retired —: one left behind (a
        # race with a new link, a database of an earlier 1.3 build) must not set the password again (A-42)
        user_id = user.id
        await session.rollback()
        await token_service.retire_tokens(session, user_id=user_id, purpose=_SETUP, now=moment)
        await session.commit()
        logger.warning("Setup link refused and retired: the account was set up before", user_id=user_id)
        return None
    record.consumed_by_user_id = user.id
    session.add(record)
    # bcrypt is slow on purpose: it runs off the event loop.
    user.hashed_password = await asyncio.to_thread(hash_password, new_password)
    user.is_active = True
    await user_service.end_sessions(session, user)
    user.updated_at = moment
    session.add(user)
    await token_service.revoke_tokens(session, user_id=user.id, purpose=_SETUP, now=moment)
    await session.commit()
    await session.refresh(user)
    logger.info("Initial administrator set up through the setup link", user_id=user.id, username=user.username)
    return user


async def issue_setup_link(session: AsyncSession, *, now: Optional[datetime] = None) -> Optional[token_service.IssuedToken]:
    """A new generated setup link for the waiting administrator, the earlier ones revoked; None without one. Not committed."""
    user = await pending_admin(session)
    if user is None:
        return None
    moment = now or utcnow()
    user_id = user.id
    await token_service.revoke_tokens(session, user_id=user_id, purpose=_SETUP, now=moment)
    # The revocation took SQLite's write lock: «waiting» is read again under it (A-42), so a setup completed since the
    # first read gets no new link
    if not await registration_service.is_pending_admin(session, user):
        await session.rollback()
        logger.info("No setup link issued: the initial administrator was set up meanwhile", user_id=user_id)
        return None
    issued = await token_service.issue_token(session, _SETUP, user_id=user_id, now=moment)
    logger.info("New setup link for the initial administrator", user_id=user.id, expires_at=issued.record.expires_at.isoformat())
    return issued
