"""
User Service

Business logic for user management, used by both API and CLI.
"""

from typing import Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import User, UserSettings, BrokerUserAccess
from backend.app.services.auth_service import hash_password, delete_user_sessions
from backend.app.utils.datetime_utils import utcnow

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

    # Invalidate all existing sessions for this user
    delete_user_sessions(user_id)

    logger.info("Password reset", user_id=user_id, username=username)
    return True, None


async def set_user_active(
    session: AsyncSession,
    username: str,
    active: bool,
    ) -> tuple[bool, Optional[str]]:
    """
    Activate or deactivate a user.

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

    user.is_active = active
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()

    # If deactivating, invalidate all sessions
    if not active:
        delete_user_sessions(user.id)

    status = "activated" if active else "deactivated"
    logger.info(f"User {status}", user_id=user.id, username=username)
    return True, None


async def set_user_admin(
    session: AsyncSession,
    username: str,
    is_admin: bool,
    ) -> tuple[bool, Optional[str]]:
    """
    Promote or demote a user to/from admin.

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

    logger.info(
        "User profile updated",
        user_id=user.id,
        username=user.username,
        email=user.email
        )
    return user, None


async def count_superusers(session: AsyncSession) -> int:
    """
    Count the number of superuser accounts.

    Args:
        session: Database session

    Returns:
        Number of superusers
    """
    stmt = select(func.count(User.id)).where(User.is_superuser == True)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """
    Delete a user and all associated data.

    This is a destructive operation that cascades to:
    - All brokers owned by the user
    - All transactions
    - All user settings
    - All sessions

    Args:
        session: Database session
        user_id: ID of user to delete

    Returns:
        True if deleted, False if user not found
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        return False

    # Delete all user sessions first
    delete_user_sessions(user_id)

    # Delete user (cascades to related data via DB constraints)
    await session.delete(user)
    await session.commit()

    logger.warning(
        "User deleted",
        user_id=user_id,
        username=user.username
        )
    return True


async def search_users(
    session: AsyncSession,
    query: str,
    exclude_broker_id: Optional[int] = None,
    ) -> list[dict]:
    """
    Search users by username (ILIKE). Does NOT expose email for privacy.

    Optionally excludes users already having access to a specific broker.

    Args:
        session: Database session
        query: Search string (min 2 chars, searches username)
        exclude_broker_id: If provided, exclude users already on this broker

    Returns:
        List of dicts with id, username, avatar_url
    """
    stmt = (
        select(User, UserSettings)
        .outerjoin(UserSettings, UserSettings.user_id == User.id)
        .where(
            User.is_active == True,
            User.username.ilike(f"%{query}%"),
        )
        .order_by(User.username)
    )

    if exclude_broker_id is not None:
        # Subquery to find users already on this broker
        broker_users_subq = (
            select(BrokerUserAccess.user_id)
            .where(BrokerUserAccess.broker_id == exclude_broker_id)
        ).scalar_subquery()
        stmt = stmt.where(User.id.notin_(broker_users_subq))

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "id": user.id,
            "username": user.username,
            "avatar_url": settings.avatar_url if settings else None,
        }
        for user, settings in rows
    ]

