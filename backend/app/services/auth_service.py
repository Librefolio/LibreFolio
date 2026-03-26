"""
Authentication Service

Provides password hashing/verification and JWT token management.
"""

import os
import secrets
from datetime import timedelta
from typing import Optional

import bcrypt
import jwt
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
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


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
# If JWT_SECRET is not set (e.g. single-worker dev mode), a random one is
# generated. On server restart, a new secret = all tokens invalidated.
# =============================================================================

# Shared secret: from env var (multi-worker safe) or random (single-worker fallback)
_JWT_SECRET: str = os.environ.get("JWT_SECRET") or secrets.token_urlsafe(64)
_JWT_ALGORITHM: str = "HS256"


def create_jwt_token(user_id: int, ttl_hours: int) -> str:
    """
    Create a signed JWT token for a user.

    Args:
        user_id: ID of the authenticated user
        ttl_hours: Token TTL in hours (read from global settings by caller)

    Returns:
        Encoded JWT token string (to be stored in cookie)
    """
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=ttl_hours),
        }
    token = jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)
    logger.info("JWT token created", user_id=user_id)
    return token


def decode_jwt_token(token: str) -> Optional[int]:
    """
    Decode and validate a JWT token.

    Args:
        token: Encoded JWT token from cookie

    Returns:
        User ID (int) or None if token is invalid/expired
    """
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except jwt.ExpiredSignatureError:
        logger.debug("JWT token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("JWT token invalid", error=str(e))
        return None
