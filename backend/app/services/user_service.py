"""
User Service

Business logic for user management, used by both API and CLI.
"""
from typing import Optional

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from backend.app.db.models import User
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
    stmt = select(User).where(
        (User.username == identifier) | (User.email == identifier)
    )
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

    user.hashed_password = hash_password(new_password)
    user.updated_at = utcnow()
    session.add(user)
    await session.commit()

    # Invalidate all existing sessions for this user
    delete_user_sessions(user.id)

    logger.info("Password reset", user_id=user.id, username=username)
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

