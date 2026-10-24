"""Single-use account tokens: invitations, password-reset links, email verification, admin setup, the owner's email change.

A token is 32 random bytes in URL-safe text, shown once to whoever asked for it; the database keeps
only its SHA-256. Each token serves one purpose — a reset link is never an invitation — and has an
expiry, and it is spent at most once: consuming it is one conditional UPDATE, so two requests racing
for the same link cannot both win.

These functions flush and never commit. The caller commits, so spending an invitation and creating
the account it opens share one transaction, and fail together. The plaintext token is never logged.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Optional
from urllib.parse import urlencode

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AccountToken, AccountTokenPurpose
from backend.app.utils.datetime_utils import ensure_utc, utcnow

logger = structlog.get_logger(__name__)

# How long a token lives when the caller does not say. Email verification is workstream E's to tune.
DEFAULT_TTL: dict[AccountTokenPurpose, timedelta] = {
    AccountTokenPurpose.INVITE: timedelta(days=7),
    AccountTokenPurpose.PASSWORD_RESET: timedelta(minutes=30),
    AccountTokenPurpose.ADMIN_SETUP: timedelta(hours=72),
    AccountTokenPurpose.EMAIL_VERIFICATION: timedelta(hours=24),
    # The host changed the owner's address: a week, as an invitation. The restart that issues it may be days before the click.
    AccountTokenPurpose.EMAIL_CHANGE: timedelta(days=7),
}

# The page of the web interface that receives each kind of link. The API client's `LINK_PAGES`
# (`frontend/src/lib/api/zodios-client.ts`) lists the same pages: a 401 there never goes to the login, which would lose
# the token. `test_account_tokens.py` checks that the two lists agree.
_TOKEN_PATHS: dict[AccountTokenPurpose, str] = {
    AccountTokenPurpose.INVITE: "/invite",
    AccountTokenPurpose.PASSWORD_RESET: "/reset-password",
    AccountTokenPurpose.ADMIN_SETUP: "/setup",
    AccountTokenPurpose.EMAIL_VERIFICATION: "/verify-email",
    AccountTokenPurpose.EMAIL_CHANGE: "/confirm-email-change",
}


class TokenStatus(StrEnum):
    """What a token is worth right now, for the purpose it was looked up with."""

    VALID = "valid"
    EXPIRED = "expired"
    CONSUMED = "consumed"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class IssuedToken:
    """A new token: ``token`` is the plaintext, never stored, to hand over once."""

    token: str
    record: AccountToken


@dataclass(frozen=True)
class TokenInspection:
    """The status of a token, with its row unless the token is unknown for that purpose."""

    status: TokenStatus
    record: Optional[AccountToken]


def hash_token(token: str) -> str:
    """The SHA-256 of a token, as stored: 64 lowercase hex characters."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_path(purpose: AccountTokenPurpose, token: str) -> str:
    """The path of the web page that takes this token, the token in the fragment.

    A browser never sends the fragment to the server: the token stays out of access logs, proxy logs and the
    ``Referer`` of a link followed from the page, which reads it with JavaScript.
    """
    return f"{_TOKEN_PATHS[purpose]}#{urlencode({'token': token})}"


async def issue_token(
    session: AsyncSession,
    purpose: AccountTokenPurpose,
    *,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    grants_admin: bool = False,
    created_by_user_id: Optional[int] = None,
    ttl: Optional[timedelta] = None,
    now: Optional[datetime] = None,
    token: Optional[str] = None,
) -> IssuedToken:
    """Create a token for ``purpose`` and return its plaintext with its row (flushed, not committed).

    ``token``, when given, is stored instead of a generated one: the setup link a hosting panel hands over with
    ``LIBREFOLIO_ADMIN_BOOTSTRAP_TOKEN`` (F02). Its format is the configuration's to check.

    An invitation opens an account that does not exist yet, so it takes no ``user_id`` and may grant
    the administrator role; every other purpose acts on an existing account (``user_id`` required) and
    grants nothing.
    """
    if purpose == AccountTokenPurpose.INVITE:
        if user_id is not None:
            raise ValueError("an invitation opens an account that does not exist yet: it takes no user_id")
    else:
        if user_id is None:
            raise ValueError(f"a {purpose.value} token acts on an existing account: user_id is required")
        if grants_admin:
            raise ValueError("only an invitation grants a role")
    lifetime = DEFAULT_TTL[purpose] if ttl is None else ttl
    if lifetime <= timedelta(0):
        raise ValueError("a token must live for a positive time")

    if token is not None and not token:
        raise ValueError("a given token cannot be empty")
    issued_at = now or utcnow()
    plaintext = token if token is not None else secrets.token_urlsafe(32)
    record = AccountToken(
        purpose=purpose,
        token_hash=hash_token(plaintext),
        user_id=user_id,
        email=email,
        grants_admin=grants_admin,
        created_by_user_id=created_by_user_id,
        created_at=issued_at,
        expires_at=issued_at + lifetime,
    )
    session.add(record)
    await session.flush()
    logger.info("Account token issued", token_id=record.id, purpose=purpose.value, user_id=user_id, created_by_user_id=created_by_user_id, expires_at=record.expires_at.isoformat())
    return IssuedToken(token=plaintext, record=record)


async def _find(session: AsyncSession, token: str, purpose: AccountTokenPurpose) -> Optional[AccountToken]:
    """The row of ``token`` for ``purpose``, read fresh from the database (never a stale copy)."""
    statement = select(AccountToken).where(AccountToken.token_hash == hash_token(token), AccountToken.purpose == purpose).execution_options(populate_existing=True)
    return (await session.execute(statement)).scalars().first()


async def inspect_token(session: AsyncSession, token: str, purpose: AccountTokenPurpose, *, now: Optional[datetime] = None) -> TokenInspection:
    """The status of ``token`` for ``purpose``, without changing it. Another purpose's token is unknown."""
    record = await _find(session, token, purpose)
    if record is None:
        return TokenInspection(status=TokenStatus.UNKNOWN, record=None)
    if record.revoked_at is not None:
        status = TokenStatus.REVOKED
    elif record.consumed_at is not None:
        status = TokenStatus.CONSUMED
    elif ensure_utc(record.expires_at) <= ensure_utc(now or utcnow()):
        status = TokenStatus.EXPIRED
    else:
        status = TokenStatus.VALID
    return TokenInspection(status=status, record=record)


async def consume_token(
    session: AsyncSession,
    token: str,
    purpose: AccountTokenPurpose,
    *,
    consumed_by_user_id: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Optional[AccountToken]:
    """Spend ``token`` for ``purpose``: its row, or None when it is not valid. Not committed.

    One conditional UPDATE does it: of two requests racing for the same token, only the one whose
    UPDATE changes the row gets it.
    """
    consumed_at = now or utcnow()
    statement = (
        update(AccountToken)
        .where(
            AccountToken.token_hash == hash_token(token),
            AccountToken.purpose == purpose,
            AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
            AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
            AccountToken.expires_at > consumed_at,
        )
        .values(consumed_at=consumed_at, consumed_by_user_id=consumed_by_user_id)
        .execution_options(synchronize_session=False)
    )
    if (await session.execute(statement)).rowcount != 1:
        return None
    record = await _find(session, token, purpose)
    if record is not None:
        logger.info("Account token consumed", token_id=record.id, purpose=purpose.value, consumed_by_user_id=consumed_by_user_id)
    return record


async def revoke_tokens(
    session: AsyncSession,
    *,
    token_id: Optional[int] = None,
    user_id: Optional[int] = None,
    purpose: Optional[AccountTokenPurpose] = None,
    now: Optional[datetime] = None,
) -> int:
    """Revoke the live tokens — not consumed, not revoked — of one id or of one user; how many. Not committed."""
    if token_id is None and user_id is None:
        raise ValueError("revoke by token id or by user, never every token at once")
    conditions = [AccountToken.consumed_at.is_(None), AccountToken.revoked_at.is_(None)]  # type: ignore[union-attr]
    if token_id is not None:
        conditions.append(AccountToken.id == token_id)
    if user_id is not None:
        conditions.append(AccountToken.user_id == user_id)
    if purpose is not None:
        conditions.append(AccountToken.purpose == purpose)
    # Always this one UPDATE, even when no live token can match: it takes SQLite's write lock, and the setup-link callers
    # read «waiting» again under it (A-42). Never select the live ids first and skip the UPDATE when there are none.
    statement = update(AccountToken).where(*conditions).values(revoked_at=now or utcnow()).execution_options(synchronize_session=False)
    revoked = (await session.execute(statement)).rowcount
    if revoked:
        logger.info("Account tokens revoked", count=revoked, token_id=token_id, user_id=user_id, purpose=purpose.value if purpose else None)
    return revoked


async def retire_tokens(session: AsyncSession, *, user_id: int, purpose: AccountTokenPurpose, now: Optional[datetime] = None) -> int:
    """Retire the tokens of one user and purpose never consumed: revoked and consumed at once; how many. Not committed.

    For links whose purpose was fulfilled another way — the initial administrator activated, or given a password,
    without its setup link (A-32): such a link reads as withdrawn (``inspect_token`` reads the revocation first), can
    no longer be consumed, and counts as used where that matters (``pending_admin_filter``: the account waits no more).
    An earlier revocation keeps its moment; ``consumed_by_user_id`` stays empty, for nobody spent the link.
    """
    moment = now or utcnow()
    unconsumed = (AccountToken.user_id == user_id, AccountToken.purpose == purpose, AccountToken.consumed_at.is_(None))  # type: ignore[union-attr]
    await session.execute(update(AccountToken).where(*unconsumed, AccountToken.revoked_at.is_(None)).values(revoked_at=moment).execution_options(synchronize_session=False))  # type: ignore[union-attr]
    retired = (await session.execute(update(AccountToken).where(*unconsumed).values(consumed_at=moment).execution_options(synchronize_session=False))).rowcount
    if retired:
        logger.info("Account tokens retired", count=retired, user_id=user_id, purpose=purpose.value)
    return retired
