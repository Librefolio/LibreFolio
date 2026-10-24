"""
Authentication Service

Provides password hashing/verification and JWT token management.
"""

import functools
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import bcrypt
import jwt
import structlog

from backend.app.config.platform import configured_jwt_secret
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
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def unusable_password_hash() -> str:
    """A password hash that no password produces: the bcrypt hash of a random secret nobody ever sees (as the initial
    administrator waiting for its setup gets), of the cost every password gets.

    A real hash, not a marker: a sign-in attempt costs what it costs for any account. Synchronous and slow on purpose
    (bcrypt): an async caller runs it with ``asyncio.to_thread``.
    """
    return hash_password(secrets.token_urlsafe(32))


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
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.warning("Password verification failed", error=str(e))
        return False


@functools.cache
def _dummy_password_hash() -> str:
    """A bcrypt hash of a random password, of the cost every password gets: computed once, never matched."""
    return hash_password(secrets.token_urlsafe(32))


def verify_password_or_dummy(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a password even when there is no account to check it against.

    Without an account (``hashed_password`` is None) the password is checked against a dummy hash
    of the same cost and the answer is False: an unknown login takes as long as a wrong password,
    so the response time does not tell which accounts exist.
    """
    if hashed_password is None:
        verify_password(plain_password, _dummy_password_hash())
        return False
    return verify_password(plain_password, hashed_password)


# =============================================================================
# JWT Token Management (Stateless)
#
# Tokens are signed with HMAC-SHA256 using a shared secret.
#
# The secret is read from the JWT_SECRET environment variable, which must
# be set by the launcher (dev.py) BEFORE starting uvicorn. This is critical
# for multi-worker: on macOS Python uses 'spawn' (not fork), so each worker
# is a fresh process that re-imports all modules. Without a shared env var,
# each worker would generate its own random secret → tokens from worker A
# would be invalid on worker B.
#
# If JWT_SECRET is not set, or blank (e.g. single-worker dev mode, or a
# `JWT_SECRET=   ` line in a Docker env file), a random one is generated.
# On server restart, a new secret = all tokens invalidated.
# =============================================================================

# Shared secret: from env var (multi-worker safe) or random (single-worker fallback)
_JWT_SECRET: str = configured_jwt_secret() or secrets.token_urlsafe(64)
_JWT_ALGORITHM: str = "HS256"


@dataclass(frozen=True)
class SessionClaims:
    """What a valid session token says: whose session it is, and of which session version of the account."""

    user_id: int
    session_version: int


def create_jwt_token(user_id: int, ttl_hours: int, session_version: int) -> str:
    """
    Create a signed JWT token for a user.

    Args:
        user_id: ID of the authenticated user
        ttl_hours: Token TTL in hours (read from global settings by caller)
        session_version: The account's current ``users.session_version``, carried as the ``sv`` claim:
            raising it ends every session issued before

    Returns:
        Encoded JWT token string (to be stored in cookie)
    """
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "sv": session_version,
        "iat": now,
        "exp": now + timedelta(hours=ttl_hours),
    }
    token = jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
    logger.debug("JWT token created", user_id=user_id)
    return token


def decode_jwt_token(token: str) -> Optional[SessionClaims]:
    """
    Decode and validate a JWT token.

    A token without the ``sv`` claim was issued before session versions existed: it belongs to session
    version 0, so the upgrade signs nobody out.

    Args:
        token: Encoded JWT token from cookie

    Returns:
        The session claims, or None if the token is invalid or expired
    """
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("JWT token invalid", error=str(e))
        return None
    session_version = payload.get("sv", 0)
    # bool is an int in Python: a token saying "sv": true is malformed, not version 1.
    if isinstance(session_version, bool) or not isinstance(session_version, int):
        logger.debug("JWT token invalid", error="the session version is not an integer")
        return None
    try:
        return SessionClaims(user_id=int(payload["sub"]), session_version=session_version)
    except (KeyError, TypeError, ValueError):
        logger.debug("JWT token invalid", error="no numeric subject")
        return None
