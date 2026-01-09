"""
Authentication Service

Provides password hashing/verification and session management.
"""
import secrets
from datetime import timedelta
from typing import Optional

import bcrypt
import structlog

from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)

# Password hashing configuration
# Using bcrypt with cost factor 12 (good balance of security and speed)
BCRYPT_ROUNDS = 12


# =============================================================================
# Password Hashing
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # bcrypt has a 72-byte limit, truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hash to verify against

    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.warning("Password verification failed", error=str(e))
        return False


# =============================================================================
# Session Management (In-Memory)
# =============================================================================

# Session storage: {session_id: {"user_id": int, "created_at": datetime, "expires_at": datetime}}
_sessions: dict[str, dict] = {}

# Session configuration
SESSION_EXPIRE_HOURS = 24
SESSION_ID_LENGTH = 64  # 256 bits of entropy


def create_session(user_id: int) -> str:
    """
    Create a new session for a user.

    Args:
        user_id: ID of the authenticated user

    Returns:
        Session ID (to be stored in cookie)
    """
    session_id = secrets.token_urlsafe(SESSION_ID_LENGTH)
    now = utcnow()

    _sessions[session_id] = {
        "user_id": user_id,
        "created_at": now,
        "expires_at": now + timedelta(hours=SESSION_EXPIRE_HOURS)
    }

    logger.info("Session created", user_id=user_id, session_id=session_id[:8] + "...")
    return session_id


def get_session(session_id: str) -> Optional[dict]:
    """
    Get session data if valid and not expired.

    Args:
        session_id: Session ID from cookie

    Returns:
        Session data dict or None if invalid/expired
    """
    session = _sessions.get(session_id)

    if not session:
        return None

    # Check expiration
    if utcnow() > session["expires_at"]:
        # Session expired - clean it up
        delete_session(session_id)
        return None

    return session


def get_user_id_from_session(session_id: str) -> Optional[int]:
    """
    Get user ID from a valid session.

    Args:
        session_id: Session ID from cookie

    Returns:
        User ID or None if session invalid
    """
    session = get_session(session_id)
    return session["user_id"] if session else None


def delete_session(session_id: str) -> bool:
    """
    Delete a session (logout).

    Args:
        session_id: Session ID to delete

    Returns:
        True if session was deleted, False if not found
    """
    if session_id in _sessions:
        del _sessions[session_id]
        logger.info("Session deleted", session_id=session_id[:8] + "...")
        return True
    return False


def delete_user_sessions(user_id: int) -> int:
    """
    Delete all sessions for a user.

    Args:
        user_id: User ID whose sessions to delete

    Returns:
        Number of sessions deleted
    """
    to_delete = [
        sid for sid, data in _sessions.items()
        if data["user_id"] == user_id
    ]

    for sid in to_delete:
        del _sessions[sid]

    if to_delete:
        logger.info("User sessions deleted", user_id=user_id, count=len(to_delete))

    return len(to_delete)


def cleanup_expired_sessions() -> int:
    """
    Remove all expired sessions.
    Should be called periodically (e.g., via scheduler).

    Returns:
        Number of sessions cleaned up
    """
    now = utcnow()
    to_delete = [
        sid for sid, data in _sessions.items()
        if now > data["expires_at"]
    ]

    for sid in to_delete:
        del _sessions[sid]

    if to_delete:
        logger.info("Expired sessions cleaned up", count=len(to_delete))

    return len(to_delete)


def get_active_session_count() -> int:
    """Get count of active sessions."""
    return len(_sessions)

