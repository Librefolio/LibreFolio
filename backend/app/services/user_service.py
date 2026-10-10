"""
User Service

Business logic for user management, used by both API and CLI.
"""

from dataclasses import dataclass, field
from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import BrokerUserAccess, User, UserSettings
from backend.app.services.auth_service import hash_password
from backend.app.services.broker_service import BrokerService
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


logger = structlog.get_logger(__name__)


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
    Get user by email.

    Args:
        session: Database session
        email: Email to search

    Returns:
        User or None if not found
    """
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_user_by_username_or_email(session: AsyncSession, identifier: str) -> Optional[User]:
    """
    Get user by username OR email.

    Args:
        session: Database session
        identifier: Username or email to search

    Returns:
        User or None if not found
    """
    stmt = select(User).where((User.username == identifier) | (User.email == identifier))
    result = await session.execute(stmt)
    return result.scalars().first()


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
) -> tuple[Optional[User], Optional[str]]:
    """
    Create a new user.

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
    # Check if username exists
    existing = await get_user_by_username(session, username)
    if existing:
        return None, "Username already taken"

    # Check if email exists
    existing = await get_user_by_email(session, email)
    if existing:
        return None, "Email already registered"

    # Create user
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        is_active=is_active,
        is_superuser=is_superuser,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info("User created", user_id=user.id, username=user.username, is_superuser=is_superuser)
    return user, None


async def reset_password(
    session: AsyncSession,
    username: str,
    new_password: str,
) -> tuple[bool, Optional[str]]:
    """
    Reset a user's password.

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

    user.hashed_password = hash_password(new_password)
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()

    # Note: JWT tokens cannot be revoked server-side. Existing tokens
    # for this user will remain valid until they expire naturally.
    logger.info("Password reset", user_id=user_id, username=username)
    return True, None


async def set_user_active(
    session: AsyncSession,
    username: str,
    active: bool,
) -> tuple[bool, Optional[str]]:
    """
    Activate or deactivate a user.

    The last active administrator cannot be deactivated: an inactive user cannot log in, so the
    instance would be left with nobody to administer it.

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

    user.is_active = active
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
    administer it. Demoting an inactive administrator removes no active one, and is allowed.

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

    # Store user_id before commit (to avoid lazy load after commit)
    user_id = user.id

    user.is_superuser = is_admin
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

    # Check username uniqueness (if changing)
    if username is not None and username != user.username:
        existing = await get_user_by_username(session, username)
        if existing:
            return None, "Username already taken"
        user.username = username

    # Check email uniqueness (if changing)
    if email is not None and email != user.email:
        existing = await get_user_by_email(session, email)
        if existing:
            return None, "Email already registered"
        user.email = email

    # Update timestamp
    user.updated_at = utcnow()

    session.add(user)
    await session.commit()
    await session.refresh(user)

    logger.info("User profile updated", user_id=user.id, username=user.username, email=user.email)
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
