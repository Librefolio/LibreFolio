"""
User Service

Business logic for user management, used by both API and CLI.
"""

import asyncio
import string
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import structlog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from backend.app.config.accounts import USERNAME_RESERVED_CHARACTER, USERNAME_RESERVED_MESSAGE
from backend.app.db.models import AccountTokenPurpose, Broker, BrokerUserAccess, Transaction, User, UserRole, UserSettings
from backend.app.services.accounts import token_service
from backend.app.services.accounts.auth_service import hash_password
from backend.app.services.brim import brim_provider
from backend.app.services.brokers.broker_service import BrokerService
from backend.app.utils.datetime_utils import utcnow


@dataclass(frozen=True)
class AccountDeletion:
    """What deleting an account took with it (plan 34_accountAndIdReuse §2.1).

    ``deleted_broker_ids``: the brokers the user was the last owner of, deleted with the
    account (their transactions in the same commit, their BRIM files by the caller after it).
    """

    deleted_broker_ids: list[int] = field(default_factory=list)


class AccountDeletionError(Exception):
    """A broker of the account could not be released: nothing was deleted."""


@dataclass(frozen=True)
class BrokerDeletionItem:
    """A broker that goes with the account, which is its last owner, with its transactions."""

    broker_id: int
    name: str
    transactions: int


@dataclass(frozen=True)
class BrokerAccessItem:
    """A broker that stays: only the account's access to it goes."""

    broker_id: int
    name: str
    role: UserRole


@dataclass(frozen=True)
class AccountDeletionPreview:
    """What deleting an account would take with it, by the rule of ``delete_user``, computed without writing.

    ``transfers_unpaired``: the transactions that stay and are linked, in either direction, to one that goes — the
    halves of transfers left alone (backlog V-3).
    """

    user_id: int
    username: str
    brokers_deleted: list[BrokerDeletionItem]
    brokers_left: list[BrokerAccessItem]
    transfers_unpaired: int


@dataclass(frozen=True)
class AccountDeletionResult:
    """What a deletion took with it: the brokers it deleted, and their report files removed after the commit."""

    deleted_broker_ids: list[int]
    files_removed: int


logger = structlog.get_logger(__name__)


async def end_sessions(session: AsyncSession, user: User) -> None:
    """Raise the account's session version: every session token issued before it is refused at its next request.

    One increment in SQL (A-34): two changes that end the sessions at the same time raise it by two, so a session cookie
    issued between them does not survive the second. A Core statement on the session's own connection, in the caller's
    transaction: nothing the caller changed on ``user`` is flushed before its commit, and ``user`` then carries the new
    value without being marked as changed. Not committed: the caller commits it together with the change that asks for
    it.
    """
    users = User.__table__  # type: ignore[attr-defined]
    statement = users.update().where(users.c.id == user.id).values(session_version=users.c.session_version + 1).returning(users.c.session_version)
    connection = await session.connection()
    version = (await connection.execute(statement)).scalar_one()
    set_committed_value(user, "session_version", version)


_ASCII_FOLD = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def email_fold(address: str) -> str:
    """``address`` with A–Z folded to a–z and nothing else, as SQLite's ``lower()`` folds it (decision P18).

    Email addresses are unique regardless of case: the database holds a unique index on ``lower(email)``
    (``ux_users_email_lower``, migration 009). Letters outside ASCII compare as written: a documented limit.
    """
    return address.translate(_ASCII_FOLD)


def same_email(first: str, second: str) -> bool:
    """Whether two addresses are the same, regardless of the case of A–Z (``email_fold``)."""
    return email_fold(first) == email_fold(second)


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[User]:
    """
    Get user by username.

    Args:
        session: Database session
        username: Username to search

    Returns:
        User or None if not found
    """
    stmt = select(User).where(User.username == username)
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """
    Get user by email, regardless of the case of A–Z (decision P18: the index ``ux_users_email_lower``).

    Args:
        session: Database session
        email: Email to search

    Returns:
        User or None if not found
    """
    stmt = select(User).where(func.lower(User.email) == func.lower(email))
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_user_by_username_or_email(session: AsyncSession, identifier: str) -> Optional[User]:
    """
    The account an identifier typed at sign-in names: an address first, then a username (A-21a, rule 3).

    An identifier holding an ``@`` is the account whose email it is, regardless of the case of A–Z (decision P18); only
    when no account has that address, the account whose username it is exactly — a name from before A-21a, which refuses
    the ``@`` in new names. Without an ``@`` it is a username only, compared exactly, never an address. So no username
    stands in front of another account's address, whichever row was written first. Usernames regardless of case wait
    for their unique index (A-21b): folding the case here before it would let «Bob» stand in front of «bob».
    The sign-in, «forgot password» and the verification resend look an identifier up here.

    Args:
        session: Database session
        identifier: Username or email to search

    Returns:
        User or None if not found
    """
    if USERNAME_RESERVED_CHARACTER in identifier:
        user = await get_user_by_email(session, identifier)
        if user is not None:
            return user
    return await get_user_by_username(session, identifier)


async def address_is_a_username(session: AsyncSession, address: str, *, other_than: int | None = None) -> bool:
    """Whether ``address`` is the username of an account, regardless of the case of A–Z (A-21a, rule 2).

    Only a username from before A-21a holds an ``@``. An address equal to one would take that account's sign-in by name
    (``get_user_by_username_or_email`` reads an address first), so no account takes it as its email — the account
    ``other_than``, the name's own, apart. No index serves ``lower(username)``: the accounts of an instance are few.
    """
    stmt = select(User.id).where(func.lower(User.username) == func.lower(address))
    if other_than is not None:
        stmt = stmt.where(User.id != other_than)
    return (await session.execute(stmt.limit(1))).first() is not None


async def get_user_by_id(session: AsyncSession, user_id: int) -> Optional[User]:
    """
    Get user by ID.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        User or None if not found
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalars().first()


async def list_users(session: AsyncSession) -> list[User]:
    """
    List all users.

    Args:
        session: Database session

    Returns:
        List of all users
    """
    stmt = select(User).order_by(User.id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_users(session: AsyncSession) -> int:
    """
    Count total users in the database.

    Args:
        session: Database session

    Returns:
        Number of users
    """
    stmt = select(func.count()).select_from(User)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def create_user(
    session: AsyncSession,
    username: str,
    email: str,
    password: str,
    is_superuser: bool = False,
    is_active: bool = True,
    commit: bool = True,
) -> tuple[Optional[User], Optional[str]]:
    """
    Create a new user.

    With ``commit=False`` the user is only flushed (it has its id), and the caller commits it together with what
    else the creation belongs to — an invitation spent, a limit checked.

    Args:
        session: Database session
        username: Username
        email: Email address
        password: Plain text password (will be hashed)
        is_superuser: Whether user is superuser
        is_active: Whether user is active

    Returns:
        Tuple of (User, None) on success or (None, error_message) on failure
    """
    # A new username holds no @: the sign-in reads an identifier with one as an address first (A-21a, rule 1)
    if USERNAME_RESERVED_CHARACTER in username:
        return None, USERNAME_RESERVED_MESSAGE

    # Check if username exists
    existing = await get_user_by_username(session, username)
    if existing:
        return None, "Username already taken"

    # Check if email exists, or is the username of an account from before A-21a (rule 2): the same answer
    existing = await get_user_by_email(session, email)
    if existing or await address_is_a_username(session, email):
        return None, "Email already registered"

    # Create user
    user = User(
        username=username,
        email=email,
        hashed_password=await asyncio.to_thread(hash_password, password),
        is_active=is_active,
        is_superuser=is_superuser,
    )

    session.add(user)
    if commit:
        await session.commit()
        await session.refresh(user)
    else:
        await session.flush()

    logger.info("User created", user_id=user.id, username=user.username, is_superuser=is_superuser)
    return user, None


async def reset_password(
    session: AsyncSession,
    username: str,
    new_password: str,
) -> tuple[bool, Optional[str]]:
    """
    Reset a user's password, and end every open session of the account.

    Args:
        session: Database session
        username: Username
        new_password: New plain text password (will be hashed)

    Returns:
        Tuple of (success, error_message)
    """
    user = await get_user_by_username(session, username)
    if not user:
        return False, f"User '{username}' not found"

    # Save user_id before commit (to avoid expired attribute access)
    user_id = user.id

    # bcrypt is slow on purpose: it runs off the event loop.
    user.hashed_password = await asyncio.to_thread(hash_password, new_password)
    await end_sessions(session, user)
    # The live password-reset links of the account die with the old password (A-27), in the same commit; a setup link
    # of the initial administrator is retired: given a password another way, the account is set up (A-32).
    await token_service.revoke_tokens(session, user_id=user_id, purpose=AccountTokenPurpose.PASSWORD_RESET)
    await token_service.retire_tokens(session, user_id=user_id, purpose=AccountTokenPurpose.ADMIN_SETUP)
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()

    logger.info("Password reset, sessions ended", user_id=user_id, username=username)
    return True, None


async def create_password_reset(
    session: AsyncSession,
    user: User,
    *,
    created_by_user_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> token_service.IssuedToken:
    """Issue a password-reset link for ``user``, revoking the live ones issued before; flushed, not committed."""
    await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.PASSWORD_RESET, now=now)
    issued = await token_service.issue_token(session, AccountTokenPurpose.PASSWORD_RESET, user_id=user.id, created_by_user_id=created_by_user_id, now=now)
    logger.info("Password reset link created", user_id=user.id, token_id=issued.record.id, created_by_user_id=created_by_user_id)
    return issued


async def complete_password_reset(session: AsyncSession, token: str, new_password: str, *, now: Optional[datetime] = None) -> Optional[User]:
    """Spend a password-reset link: set the new password, end every session, revoke the other live links; commits.

    None, and nothing changed, when the link is not valid.
    """
    record = await token_service.consume_token(session, token, AccountTokenPurpose.PASSWORD_RESET, now=now)
    user = await get_user_by_id(session, record.user_id) if record is not None and record.user_id is not None else None
    if user is None:
        await session.rollback()
        return None
    # bcrypt is slow on purpose: it runs off the event loop.
    user.hashed_password = await asyncio.to_thread(hash_password, new_password)
    await end_sessions(session, user)
    user.updated_at = utcnow()
    session.add(user)
    await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.PASSWORD_RESET, now=now)
    # Given a password through another link, the initial administrator is set up: its setup link is retired (A-32)
    await token_service.retire_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.ADMIN_SETUP, now=now)
    await session.commit()
    await session.refresh(user)
    logger.info("Password reset through a link, sessions ended", user_id=user.id, username=user.username)
    return user


async def update_user_status(
    session: AsyncSession,
    user: User,
    *,
    is_active: Optional[bool] = None,
    is_superuser: Optional[bool] = None,
) -> Optional[str]:
    """Change whether ``user`` is active and an administrator, all or nothing; commits.

    Returns ``"LAST_ADMIN"``, changing nothing, when the change would deactivate or demote the last active
    administrator; None otherwise. Deactivating or demoting ends every session of the account. A value equal to the
    current one changes nothing, except one thing: deactivating an account that waits for its email verification ends
    the wait, as ``user deactivate`` does. Activating or deactivating revokes the account's email-verification links:
    an administrator has decided, so the account no longer waits for one, and an old link cannot wake it (workstream E).
    Activating retires the setup links of the initial administrator: set up another way, it waits no more (A-32).
    Deactivating the initial administrator waiting for its setup, already inactive, revokes its setup links — the
    cancellation: it keeps waiting, and ``./dev.py user setup-link`` gives it a new one —; deactivating any other
    account retires the setup links it never used (A-43). Demoting the waiting administrator is refused by the caller.
    """
    deactivate = is_active is False and user.is_active
    demote = is_superuser is False and user.is_superuser
    if (deactivate or demote) and await _is_last_active_admin(session, user):
        return "LAST_ADMIN"
    # Read before any change: whether the account is the initial administrator waiting for its setup (F02)
    waiting = is_active is False and await _is_pending_admin(session, user)
    changed = False
    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        changed = True
        await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.EMAIL_VERIFICATION)
        # Activated another way, the initial administrator is set up (A-32); deactivated, a link left behind must not
        # set up the account again (A-43): either way its setup links are retired
        await token_service.retire_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.ADMIN_SETUP)
    elif is_active is False:
        if await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.EMAIL_VERIFICATION):
            # An account already inactive that waited for its email verification: its links stop working, its place is free.
            changed = True
        if await _end_setup_links(session, user, waiting):
            changed = True
    if is_superuser is not None and is_superuser != user.is_superuser:
        user.is_superuser = is_superuser
        changed = True
    if deactivate or demote:
        await end_sessions(session, user)
    if changed:
        user.updated_at = utcnow()
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("User status changed", user_id=user.id, username=user.username, is_active=user.is_active, is_superuser=user.is_superuser)
    return None


async def _is_pending_admin(session: AsyncSession, user: User) -> bool:
    """``registration_service.is_pending_admin``; imported when it runs: registration imports this module."""
    from backend.app.services.accounts.registration_service import is_pending_admin  # noqa: PLC0415

    return await is_pending_admin(session, user)


async def _end_setup_links(session: AsyncSession, user: User, waiting: bool) -> int:
    """Deactivating an account ends its setup links (A-43); how many. Not committed.

    The initial administrator waiting for its setup has its links **revoked**: that is the cancellation of the link handed
    over, and the account still waits, so ``./dev.py user setup-link`` gives it a new one. Any other account has the
    setup links it was never set up with **retired**: they count as used, and none can set it up again.
    """
    if waiting:
        revoked = await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.ADMIN_SETUP)
        if revoked:
            logger.warning("Setup link of the initial administrator revoked: its setup was cancelled; ./dev.py user setup-link gives a new one", user_id=user.id)
        return revoked
    return await token_service.retire_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.ADMIN_SETUP)


async def set_user_active(
    session: AsyncSession,
    username: str,
    active: bool,
) -> tuple[bool, Optional[str]]:
    """
    Activate or deactivate a user.

    The last active administrator cannot be deactivated: an inactive user cannot log in, so the
    instance would be left with nobody to administer it. Deactivating ends every session of the account,
    so that a later activation does not bring them back. Either way the account's email-verification links are
    revoked: the operator has decided, so the account no longer waits for one (workstream E). Activating retires the
    setup links of the initial administrator: set up another way, it waits no more (A-32). Deactivating the initial
    administrator waiting for its setup revokes its setup links — the cancellation: it keeps waiting —; deactivating
    any other account retires the setup links it never used (A-43). Protection is not checked: the operator's power.

    Args:
        session: Database session
        username: Username
        active: New active state

    Returns:
        Tuple of (success, error_message)
    """
    user = await get_user_by_username(session, username)
    if not user:
        return False, f"User '{username}' not found"

    if not active and await _is_last_active_admin(session, user):
        return False, f"User '{username}' is the last active administrator: promote or activate another administrator first"

    # Store user_id before commit (to avoid lazy load after commit)
    user_id = user.id
    # Read before any change: whether the account is the initial administrator waiting for its setup (F02)
    waiting = not active and await _is_pending_admin(session, user)

    user.is_active = active
    if not active:
        await end_sessions(session, user)
    await token_service.revoke_tokens(session, user_id=user_id, purpose=AccountTokenPurpose.EMAIL_VERIFICATION)
    if active:
        # Activated another way, the initial administrator is set up: its setup link is retired (A-32)
        await token_service.retire_tokens(session, user_id=user_id, purpose=AccountTokenPurpose.ADMIN_SETUP)
    else:
        # The waiting administrator's link revoked (the cancellation), any other account's retired (A-43)
        await _end_setup_links(session, user, waiting)
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()

    status = "activated" if active else "deactivated"
    logger.info(f"User {status}", user_id=user_id, username=username)
    return True, None


async def set_user_admin(
    session: AsyncSession,
    username: str,
    is_admin: bool,
) -> tuple[bool, Optional[str]]:
    """
    Promote or demote a user to/from admin.

    The last active administrator cannot be demoted: the instance would be left with nobody to
    administer it. Demoting an inactive administrator removes no active one, and is allowed, except the initial
    administrator waiting for its setup: it keeps its role until then (A-43). Demoting ends every session of the account.

    Args:
        session: Database session
        username: Username
        is_admin: True to promote, False to demote

    Returns:
        Tuple of (success, error_message)
    """
    user = await get_user_by_username(session, username)
    if not user:
        return False, f"User '{username}' not found"

    if user.is_superuser == is_admin:
        status = "already an admin" if is_admin else "not an admin"
        return False, f"User '{username}' is {status}"

    if not is_admin and await _is_last_active_admin(session, user):
        return False, f"User '{username}' is the last active administrator: promote another user first"

    if not is_admin and await _is_pending_admin(session, user):
        return False, f"User '{username}' is the initial administrator waiting for its setup: it keeps its role until then; deactivate it to cancel its setup link, or delete it from Settings › Administration › Users"

    # Store user_id before commit (to avoid lazy load after commit)
    user_id = user.id

    user.is_superuser = is_admin
    if not is_admin:
        await end_sessions(session, user)
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()

    status = "promoted to admin" if is_admin else "demoted from admin"
    logger.info(f"User {status}", user_id=user_id, username=username)
    return True, None


async def update_profile(
    session: AsyncSession,
    user_id: int,
    username: str | None = None,
    email: str | None = None,
) -> tuple[Optional[User], Optional[str]]:
    """
    Update user profile (username and/or email).

    Validates uniqueness constraints before committing.

    Args:
        session: Database session
        user_id: ID of user to update
        username: New username (optional)
        email: New email (optional)

    Returns:
        Tuple of (updated_user, None) on success or (None, error_message) on failure
    """
    # Get current user
    user = await get_user_by_id(session, user_id)
    if not user:
        return None, "User not found"

    # Nothing to update
    if username is None and email is None:
        return user, None

    # Check username uniqueness (if changing); a new name holds no @ (A-21a, rule 1), the name kept keeps its own
    if username is not None and username != user.username:
        if USERNAME_RESERVED_CHARACTER in username:
            return None, USERNAME_RESERVED_MESSAGE
        existing = await get_user_by_username(session, username)
        if existing:
            return None, "Username already taken"
        user.username = username

    # Check email uniqueness (if changing): the same address in another case is no change (decision P18). The username
    # of another account is taken too (A-21a, rule 2): the sign-in would read it as this address; the account's own is not.
    email_changed = email is not None and not same_email(email, user.email)
    if email_changed:
        existing = await get_user_by_email(session, email)
        if existing or await address_is_a_username(session, email, other_than=user.id):
            return None, "Email already registered"
        user.email = email
        # A new address is not verified (E5), every session opened with the old one ends (A6e), and so does every live
        # password-reset link (A-27: whoever holds the old mailbox cannot use one asked for before): committed below,
        # together with the address.
        user.email_verified_at = None
        await end_sessions(session, user)
        await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.PASSWORD_RESET)
        # The setup link of the waiting initial administrator went to the old address too: revoked, it waits for a new one (A-33)
        await token_service.revoke_tokens(session, user_id=user.id, purpose=AccountTokenPurpose.ADMIN_SETUP)
    elif email is not None:
        # The same address written in another case: the stored form follows, nothing else changes.
        user.email = email

    # Update timestamp
    user.updated_at = utcnow()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Never the address in the log (workstream E's rule): whether it changed is enough.
    logger.info("User profile updated", user_id=user.id, username=user.username, email_changed=email_changed)
    return user, None


async def count_superusers(session: AsyncSession) -> int:
    """
    Count the number of superuser accounts.

    Args:
        session: Database session

    Returns:
        Number of superusers
    """
    stmt = select(func.count(User.id)).where(User.is_superuser == True)  # noqa: E712 — SQLAlchemy filter
    result = await session.execute(stmt)
    return result.scalar() or 0


async def count_active_superusers(session: AsyncSession, *, excluding_user_id: Optional[int] = None) -> int:
    """The active superusers — those who can still administer the instance — with ``excluding_user_id`` left out."""
    stmt = select(func.count(User.id)).where(User.is_superuser == True, User.is_active == True)  # noqa: E712 — SQLAlchemy filter
    if excluding_user_id is not None:
        stmt = stmt.where(User.id != excluding_user_id)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def _is_last_active_admin(session: AsyncSession, user: User) -> bool:
    """True when ``user`` is an active administrator and no other active administrator remains."""
    return bool(user.is_superuser and user.is_active) and await count_active_superusers(session, excluding_user_id=user.id) == 0


async def delete_user(session: AsyncSession, user_id: int) -> Optional[AccountDeletion]:
    """
    Delete a user, applying the last-owner rule to every broker the user can access.

    Broker by broker, the same rule as leaving a broker (``BrokerService.leave_broker``, F4):
    a broker the user was the last OWNER of is deleted with its transactions; on any other
    broker only the user's access goes. Then the user, with the rows that cascade from it
    (settings, onboarding progress), and one commit.

    All or nothing: if a broker cannot be released, or anything fails, the session is rolled
    back and the error propagates — nothing is deleted. The deleted brokers' BRIM files live
    on disk: the caller removes them after this commit.

    Args:
        session: Database session
        user_id: ID of user to delete

    Returns:
        What went with the account, or ``None`` if the user does not exist
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        return None
    username = user.username

    broker_ids = (await session.execute(select(BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id).order_by(BrokerUserAccess.broker_id))).scalars().all()
    broker_service = BrokerService(session)
    deleted_broker_ids: list[int] = []
    try:
        for broker_id in broker_ids:
            success, message, broker_deleted = await broker_service.leave_broker(broker_id, user_id)
            if not success:
                raise AccountDeletionError(f"Broker {broker_id} could not be released: {message}")
            if broker_deleted:
                deleted_broker_ids.append(broker_id)
        await session.delete(user)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    logger.warning("User deleted", user_id=user_id, username=username, brokers_deleted=deleted_broker_ids)
    return AccountDeletion(deleted_broker_ids=deleted_broker_ids)


async def _count_unpaired_halves(session: AsyncSession, deleted_broker_ids: list[int]) -> int:
    """The transactions outside ``deleted_broker_ids`` linked, in either direction, to a transaction inside them."""
    if not deleted_broker_ids:
        return 0
    going = select(Transaction.id).where(Transaction.broker_id.in_(deleted_broker_ids))
    pointed_by_going = select(Transaction.related_transaction_id).where(Transaction.broker_id.in_(deleted_broker_ids), Transaction.related_transaction_id.is_not(None))
    staying = Transaction.broker_id.not_in(deleted_broker_ids)
    query = select(func.count(Transaction.id)).where(staying, or_(Transaction.related_transaction_id.in_(going), Transaction.id.in_(pointed_by_going)))
    return (await session.execute(query)).scalar_one()


async def preview_user_deletion(session: AsyncSession, user_id: int) -> Optional[AccountDeletionPreview]:
    """What ``delete_user`` would take with the account, without writing anything; ``None`` for an unknown user.

    The rule is ``BrokerService.leave_broker``'s, the one ``delete_user`` applies broker by broker: a broker the user
    is the last OWNER of goes, with its transactions; on any other broker only the user's access goes. Each broker is
    decided on its own, so evaluating them together gives what the deletion does one at a time.
    """
    user = await get_user_by_id(session, user_id)
    if user is None:
        return None
    accesses = (await session.execute(select(BrokerUserAccess.broker_id, BrokerUserAccess.role, Broker.name).join(Broker, Broker.id == BrokerUserAccess.broker_id).where(BrokerUserAccess.user_id == user_id).order_by(BrokerUserAccess.broker_id))).all()
    broker_ids = [row.broker_id for row in accesses]
    owners: dict[int, int] = {}
    if broker_ids:
        owner_rows = await session.execute(select(BrokerUserAccess.broker_id, func.count()).where(BrokerUserAccess.broker_id.in_(broker_ids), BrokerUserAccess.role == UserRole.OWNER).group_by(BrokerUserAccess.broker_id))
        owners = dict(owner_rows.tuples().all())
    deleted_ids = [row.broker_id for row in accesses if row.role == UserRole.OWNER and owners.get(row.broker_id, 0) <= 1]
    transactions: dict[int, int] = {}
    if deleted_ids:
        count_rows = await session.execute(select(Transaction.broker_id, func.count()).where(Transaction.broker_id.in_(deleted_ids)).group_by(Transaction.broker_id))
        transactions = dict(count_rows.tuples().all())
    deleted = set(deleted_ids)
    return AccountDeletionPreview(
        user_id=user.id,
        username=user.username,
        brokers_deleted=[BrokerDeletionItem(broker_id=row.broker_id, name=row.name, transactions=transactions.get(row.broker_id, 0)) for row in accesses if row.broker_id in deleted],
        brokers_left=[BrokerAccessItem(broker_id=row.broker_id, name=row.name, role=UserRole(row.role)) for row in accesses if row.broker_id not in deleted],
        transfers_unpaired=await _count_unpaired_halves(session, deleted_ids),
    )


async def delete_account(session: AsyncSession, user: User) -> AccountDeletionResult:
    """Delete ``user`` by the rule of ``delete_user``, then remove the report files of the brokers it deleted.

    The files live on disk and go after the commit, off the event loop. A failure there is logged and leaves the
    deletion done: the account and its data are already gone.
    """
    deletion = await delete_user(session, user.id)
    deleted_ids = deletion.deleted_broker_ids if deletion else []
    files_removed = 0
    if deleted_ids:
        try:
            files_removed = await asyncio.to_thread(brim_provider.delete_files_for_brokers, deleted_ids)
        except Exception:
            logger.exception("The report files of the deleted brokers could not be removed", broker_ids=deleted_ids)
    return AccountDeletionResult(deleted_broker_ids=deleted_ids, files_removed=files_removed)


def account_protection(user: User) -> Optional[str]:
    """Why ``user`` may be neither deleted, deactivated nor demoted by anyone; ``None`` when nothing protects it.

    The hook of lot A7: on a managed instance the administrator created from the environment, who pays for it, is
    protected. Until then no account is.
    """
    return None


async def search_users(
    session: AsyncSession,
    query: str,
    exclude_broker_id: Optional[int] = None,
    admins_only: bool = False,
) -> list[dict]:
    """
    Search users by username (ILIKE). Does NOT expose email for privacy.

    Optionally excludes users already having access to a specific broker.

    Args:
        session: Database session
        query: Search string matched against username; empty string matches every active user
        exclude_broker_id: If provided, exclude users already on this broker
        admins_only: If provided and True, return only superusers and flag each row
            with is_admin=True (for the update-check hint shown to non-admins)

    Returns:
        List of dicts with id, username, avatar_url (+ is_admin when admins_only)
    """
    stmt = (
        select(User, UserSettings)
        .outerjoin(UserSettings, UserSettings.user_id == User.id)
        .where(
            User.is_active == True,  # noqa: E712 — SQLAlchemy filter
            User.username.ilike(f"%{query}%"),
        )
        .order_by(User.username)
    )

    if admins_only:
        stmt = stmt.where(User.is_superuser == True)  # noqa: E712 — SQLAlchemy filter

    if exclude_broker_id is not None:
        # Subquery to find users already on this broker
        broker_users_subq = (select(BrokerUserAccess.user_id).where(BrokerUserAccess.broker_id == exclude_broker_id)).scalar_subquery()
        stmt = stmt.where(User.id.notin_(broker_users_subq))

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "avatar_url": settings.avatar_url if settings else None,
            **({"is_admin": user.is_superuser, "email": user.email} if admins_only else {}),
        }
        for user, settings in rows
    ]
