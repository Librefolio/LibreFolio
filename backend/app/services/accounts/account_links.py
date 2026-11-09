"""Every account link of the instance, as administrators see it (lot UA3): its purpose, whom it is for, who issued it,
its dates and its state, never its token nor its hash.

A link is one row of ``account_tokens``. Its state is read in ``token_service.inspect_token``'s order: a revocation
first (a retired link, revoked and consumed at once, reads as revoked), then the use, then the expiry.

Administrators revoke the open links of the purposes they handle from the Users tab: invitations, password-reset
links and email-verification links. The setup link of the initial administrator is cancelled from its account
(``PATCH /users/{id}`` with ``cancel_setup``), and the owner's email change follows the host's variable, which issues
it again at the next start: neither is revoked here.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.logging_config import get_logger
from backend.app.services.accounts import token_service
from backend.app.utils.datetime_utils import ensure_utc, utcnow

logger = get_logger(__name__)

#: The purposes whose open links an administrator may revoke from the Users tab.
REVOCABLE_PURPOSES: frozenset[AccountTokenPurpose] = frozenset({AccountTokenPurpose.INVITE, AccountTokenPurpose.PASSWORD_RESET, AccountTokenPurpose.EMAIL_VERIFICATION})


class LinkState(StrEnum):
    """Where a link stands now."""

    OPEN = "open"
    USED = "used"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass(frozen=True)
class AccountLinkView:
    """One link with the names it refers to; ``None`` for an account that no longer exists or was never named."""

    record: AccountToken
    state: LinkState
    username: Optional[str]
    created_by_username: Optional[str]
    used_by_user_id: Optional[int]
    used_by_username: Optional[str]

    @property
    def revocable(self) -> bool:
        return self.state == LinkState.OPEN and self.record.purpose in REVOCABLE_PURPOSES


def link_state(record: AccountToken, now: datetime) -> LinkState:
    """The state of ``record`` at ``now``: revoked, used, expired or open, in that order."""
    if record.revoked_at is not None:
        return LinkState.REVOKED
    if record.consumed_at is not None:
        return LinkState.USED
    if ensure_utc(record.expires_at) <= ensure_utc(now):
        return LinkState.EXPIRED
    return LinkState.OPEN


def _used_by(record: AccountToken) -> Optional[int]:
    """Who spent a used link: the account it recorded, or, for a link that acts on an existing account, that account
    (a password reset or a verification records nobody: only its own account can spend it)."""
    if record.consumed_by_user_id is not None:
        return record.consumed_by_user_id
    return record.user_id if record.purpose != AccountTokenPurpose.INVITE else None


async def list_links(session: AsyncSession, *, now: Optional[datetime] = None) -> list[AccountLinkView]:
    """Every account link, newest first, with its state at ``now`` and the usernames it refers to."""
    moment = now or utcnow()
    records = list((await session.execute(select(AccountToken).order_by(AccountToken.created_at.desc(), AccountToken.id.desc()))).scalars().all())  # type: ignore[attr-defined]
    states = {record.id: link_state(record, moment) for record in records}
    referenced: set[int] = set()
    for record in records:
        referenced.update(user_id for user_id in (record.user_id, record.created_by_user_id) if user_id is not None)
        if states[record.id] == LinkState.USED and (used_by := _used_by(record)) is not None:
            referenced.add(used_by)
    names: dict[int, str] = {}
    if referenced:
        rows = await session.execute(select(User.id, User.username).where(User.id.in_(referenced)))  # type: ignore[union-attr]
        names = {int(user_id): str(username) for user_id, username in rows.all()}
    views: list[AccountLinkView] = []
    for record in records:
        state = states[record.id]
        used_by = _used_by(record) if state == LinkState.USED else None
        views.append(
            AccountLinkView(
                record=record,
                state=state,
                username=names.get(record.user_id) if record.user_id is not None else None,
                created_by_username=names.get(record.created_by_user_id) if record.created_by_user_id is not None else None,
                used_by_user_id=used_by,
                used_by_username=names.get(used_by) if used_by is not None else None,
            )
        )
    return views


RevokeOutcome = Literal["revoked", "not_found", "not_revocable"]


async def revoke_link(session: AsyncSession, link_id: int, *, now: Optional[datetime] = None) -> RevokeOutcome:
    """Revoke the open link ``link_id`` (flushed, not committed).

    ``not_found`` when no such link is open (unknown, used, expired or revoked already); ``not_revocable`` for an open
    link of a purpose administrators do not revoke here (``REVOCABLE_PURPOSES``). The revocation is one conditional
    UPDATE: a link spent meanwhile is not revoked, and answers ``not_found``.
    """
    moment = now or utcnow()
    record = await session.get(AccountToken, link_id)
    if record is None or link_state(record, moment) != LinkState.OPEN:
        return "not_found"
    if record.purpose not in REVOCABLE_PURPOSES:
        return "not_revocable"
    purpose = AccountTokenPurpose(record.purpose)
    revoked = await token_service.revoke_tokens(session, token_id=link_id, purpose=purpose, now=moment)
    if revoked != 1:
        return "not_found"
    logger.info("Account link revoked", link_id=link_id, purpose=purpose.value)
    return "revoked"
