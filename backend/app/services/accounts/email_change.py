"""The change of address a user asks for from Profile, confirmed from the new mailbox (release 1.4, project 71, block 2).

With email working — an SMTP server usable and ``LIBREFOLIO_PUBLIC_URL`` valid, the very condition ``/system/instance``
gives the web app (``verification_mode``) — a new address written in Profile does not change the account. A link of 24
hours goes to the new address, a notice to the address the account has now, and the account waits:

- ``admit_request`` — the read-only half of a request: the address free (``user_service.email_refusal``), email and links
  usable, the instance's hourly budget, the new mailbox's limit and the account's own. Nothing is written: the route calls
  it before it saves a new username, so a refusal leaves the profile as it was.
- ``request_change`` — the request: in one commit the account's earlier Profile links are revoked and a new one is issued
  (``created_by_user_id`` = the account: that marks a Profile link), then the confirmation goes to the NEW address, at
  once. When it does not go, the new link is revoked and loses its address, and nothing waits — not even the earlier
  request. The notice to the old address goes in the background (``email_change_requested_work``).
- ``resend`` — «Send again», same address: a new link; the earlier one is revoked only once the new email went.
- ``cancel`` — every Profile link of the account revoked. ``pending`` — the live one, for Profile; ``pending_ids`` — the
  accounts that wait, for the administrator.
- ``confirm_profile_change`` — the click. A dead link (unknown, expired, revoked, spent) says why to anyone. A live link
  needs the session of its account (decision D10): without it — no session, another account — nothing is written and
  ``ProfileEmailChangeSignInRequiredError`` asks to sign in; the link stays live. With it, the link is spent (one conditional
  UPDATE: of two clicks only one wins), the conditions are read again, and in a savepoint the account moves to the new
  address, verified, its sessions end and its reset, setup and change links are revoked (``user_service.move_email``).
  When a condition fails — the account gone, inactive or protected, the address taken meanwhile (as an address, a username
  or the owner's reserved one), a link the account did not issue — the link is revoked in the same transaction.

Which flow a link belongs to: ``link_flow``. The instance owner's link (A5-1b, ``instance_owner``) is issued by the host and
carries no creator; it never comes here, and nothing here revokes it except ``move_email`` at a completed change, as
``update_profile`` always did.

Limits: per account, counted on its Profile rows that still carry an address (valid across processes, as the verification's
are; a send that failed drops its row's address, so it spends nothing): 5 confirmation emails an hour, requests and resends
together, and a resend not within 60 seconds of the last one. Per new mailbox: 3 confirmations an hour
(``EMAIL_CHANGE_LINKS_BY_MAILBOX``, ``delivery.mailbox_budget_key``). Per old mailbox: 3 notices an hour
(``EMAIL_CHANGE_REQUESTED_BY_MAILBOX``, apart from the notices of a completed change). And the instance's hourly budget.
A spent budget or a refusing server is an error: never a fallback to the immediate change, which would skip the check.

No log line holds an address or a token: ``user_id``, ``token_id`` and a ``reason`` word.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal, Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import token_service, user_service
from backend.app.services.email import delivery
from backend.app.services.email.delivery import EmailError, EmailRateLimitedError, send_email
from backend.app.services.email.flows import INSTANCE_FALLBACK, account_language, link_ttl, require_email
from backend.app.services.email.links import email_instance_config, email_link, links_state, require_links
from backend.app.services.email.messages import build_email_change_request_confirmation, build_email_change_requested
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

logger = structlog.get_logger(__name__)

CHANGE = AccountTokenPurpose.EMAIL_CHANGE

#: How long the link of a change asked from Profile lives (decision D5.2): as the verification at sign-up.
PROFILE_CHANGE_TTL = timedelta(hours=24)
#: Per account, counted on its Profile rows that carry an address: 5 confirmation emails an hour, requests and resends.
CONFIRMATIONS_PER_HOUR = 5
#: Per account: a resend not within this time of the last confirmation email.
RESEND_MIN_INTERVAL = timedelta(seconds=60)
#: Per new mailbox: 3 confirmation emails an hour, whatever account asks — several accounts may name the same mailbox.
EMAIL_CHANGE_LINKS_BY_MAILBOX = SlidingWindowLimiter(3, 60 * 60)
#: Per old mailbox: 3 notices «a change was requested» an hour, apart from ``flows.EMAIL_CHANGE_NOTICES_BY_MAILBOX``, so the
#: notices of a request do not use up those of a completed change.
EMAIL_CHANGE_REQUESTED_BY_MAILBOX = SlidingWindowLimiter(3, 60 * 60)

LinkFlow = Literal["profile", "owner"]


class ProfileEmailChangeLinkInvalidError(EmailError):
    """The link does not complete a change: ``code`` is its status (``expired``, ``consumed``, ``revoked``, ``unknown``);
    ``revoked`` also when a condition failed at the click and the link was revoked for it."""


class ProfileEmailChangeSignInRequiredError(EmailError):
    """A live link clicked without the session of its account (D10): nothing was written, the link stays live."""

    def __init__(self) -> None:
        super().__init__("EMAIL_CHANGE_SIGN_IN_REQUIRED")


class EmailChangeNotPendingError(EmailError):
    """«Send again» with no change waiting."""

    def __init__(self) -> None:
        super().__init__("EMAIL_CHANGE_NOT_PENDING")


class EmailChangeRefusedError(EmailError):
    """The account cannot take the address: ``code`` is the refusal's (``EMAIL_TAKEN``)."""


@dataclass(frozen=True)
class PendingEmailChange:
    """The change an account waits for: the new address and when its link expires."""

    email: str = field(repr=False)
    expires_at: datetime


@dataclass(frozen=True)
class ConfirmedProfileChange:
    """What the click changed: the account as it is now, and the address it had."""

    user: User
    old_email: str = field(repr=False)


async def verification_mode() -> Literal["verified", "immediate"]:
    """``verified`` when a change of address waits for its link (email usable and links ready, as ``/system/instance``
    says), ``immediate`` otherwise. The configuration alone decides: a spent budget or a refusing server never makes a
    change immediate."""
    config = await asyncio.to_thread(email_instance_config)
    return "verified" if config.links else "immediate"


def _own_links(user_id: int):  # noqa: ANN202 — a tuple of SQL conditions
    """The ``email_change`` rows the account issued for itself: the mark of a Profile link."""
    return (AccountToken.purpose == CHANGE, AccountToken.user_id == user_id, AccountToken.created_by_user_id == user_id)


def _live(moment: datetime):  # noqa: ANN202 — a tuple of SQL conditions
    return (AccountToken.consumed_at.is_(None), AccountToken.revoked_at.is_(None), AccountToken.expires_at > moment)  # type: ignore[union-attr]


async def _live_links(session: AsyncSession, user_id: int, moment: datetime) -> list[AccountToken]:
    """The account's live Profile links that carry an address, newest first."""
    statement = select(AccountToken).where(*_own_links(user_id), *_live(moment), AccountToken.email.is_not(None)).order_by(AccountToken.created_at.desc(), AccountToken.id.desc()).execution_options(populate_existing=True)  # type: ignore[union-attr]
    return list((await session.execute(statement)).scalars().all())


async def pending(session: AsyncSession, user_id: int, *, now: Optional[datetime] = None) -> Optional[PendingEmailChange]:
    """The change ``user_id`` waits for: its newest live Profile link, or None."""
    links = await _live_links(session, user_id, now or utcnow())
    if not links:
        return None
    return PendingEmailChange(email=links[0].email or "", expires_at=ensure_utc(links[0].expires_at))


async def pending_ids(session: AsyncSession, *, now: Optional[datetime] = None) -> set[int]:
    """The accounts that wait for a change asked from Profile (a live link they issued for themselves)."""
    statement = select(AccountToken.user_id).where(AccountToken.purpose == CHANGE, AccountToken.created_by_user_id == AccountToken.user_id, *_live(now or utcnow()), AccountToken.email.is_not(None)).distinct()  # type: ignore[union-attr]
    return {user_id for user_id in (await session.execute(statement)).scalars().all() if user_id is not None}


async def link_flow(session: AsyncSession, token: str) -> LinkFlow:
    """Which flow ``token`` belongs to: ``profile`` for a link an account issued for itself, whatever its status;
    ``owner`` otherwise — the host's link of the instance owner, and an unknown token (the owner flow answers it as today)."""
    record = (await token_service.inspect_token(session, token, CHANGE)).record
    return "profile" if record is not None and record.created_by_user_id is not None and record.created_by_user_id == record.user_id else "owner"


async def _emails_in_last_hour(session: AsyncSession, user_id: int, moment: datetime) -> list[datetime]:
    """When the account's Profile links that went by email in the last hour were issued: rows that still carry an address."""
    statement = select(AccountToken.created_at).where(*_own_links(user_id), AccountToken.email.is_not(None), AccountToken.created_at > moment - timedelta(hours=1))  # type: ignore[union-attr]
    return [ensure_utc(value) for value in (await session.execute(statement)).scalars().all()]


def _account_wait(created: list[datetime], moment: datetime, *, resend: bool) -> Optional[float]:
    """Seconds until the account may get another confirmation email; None when it may now."""
    waits = []
    if len(created) >= CONFIRMATIONS_PER_HOUR:
        waits.append(min(created) + timedelta(hours=1) - moment)
    if resend and created and max(created) > moment - RESEND_MIN_INTERVAL:
        waits.append(max(created) + RESEND_MIN_INTERVAL - moment)
    return max(waits).total_seconds() if waits else None


async def _refused(session: AsyncSession, user: User, address: str) -> None:
    refusal = await user_service.email_refusal(session, user, address)
    if refusal is not None:
        raise EmailChangeRefusedError(refusal.code)


async def _admit_email(session: AsyncSession, user_id: int, address: str, moment: datetime, *, resend: bool) -> None:
    """Email, links, the instance's budget, the new mailbox's limit and the account's: an error when one refuses. Reads only."""
    state = await require_email()
    require_links()
    budget = delivery.budget_status(state.max_per_hour)
    if not budget.allowed:
        raise EmailRateLimitedError(budget.retry_after)
    by_mailbox = EMAIL_CHANGE_LINKS_BY_MAILBOX.peek(delivery.mailbox_budget_key(address))
    if not by_mailbox.allowed:
        raise EmailRateLimitedError(by_mailbox.retry_after)
    wait = _account_wait(await _emails_in_last_hour(session, user_id, moment), moment, resend=resend)
    if wait is not None:
        raise EmailRateLimitedError(wait)


async def admit_request(session: AsyncSession, user: User, new_address: str, *, now: Optional[datetime] = None) -> None:
    """Whether ``user`` may ask to move to ``new_address`` now; nothing is written.

    Raises ``EmailChangeRefusedError`` (the address is another account's, a username, or reserved for the owner of a managed
    instance), ``EmailUnavailableError`` / ``EmailLinksUnavailableError`` (no email with a link can go), or
    ``EmailRateLimitedError`` (the instance's budget, the new mailbox's limit, the account's limit).
    """
    if user_service.same_email(new_address, user.email):
        raise ValueError("the account already has this address: there is no change to ask for")
    await _refused(session, user, new_address)
    await _admit_email(session, user.id, new_address, now or utcnow(), resend=False)


async def _send_confirmation(session: AsyncSession, user_id: int, address: str, issued: token_service.IssuedToken, moment: datetime) -> None:
    """The confirmation email to the new address: built and sent, everything that can fail inside the caller's ``try``."""
    content = build_email_change_request_confirmation(
        language=await account_language(session, user_id),
        link=email_link(CHANGE, issued.token),
        ttl=link_ttl(issued.record, moment),
        instance=require_links().instance,
    )
    await send_email(content, to=address, user_id=user_id)


async def _drop_failed(session: AsyncSession, token_id: int, moment: datetime) -> None:
    """A link whose email did not go: revoked, and without its address, so it waits for nothing and spends no limit."""
    await session.rollback()
    await session.execute(update(AccountToken).where(AccountToken.id == token_id).values(email=None, revoked_at=moment).execution_options(synchronize_session=False))
    await session.commit()


async def request_change(session: AsyncSession, user: User, new_address: str, *, now: Optional[datetime] = None) -> PendingEmailChange:
    """Ask to move ``user`` to ``new_address``: the account's earlier Profile links revoked and a new one issued, in one
    commit; then the confirmation emailed to the new address. Nothing on the account changes.

    Raises what ``admit_request`` raises, with nothing written; ``EmailRateLimitedError`` when another request emailed meanwhile
    (rolled back); and what ``send_email`` raises — then the new link is revoked and loses its address, and nothing waits:
    the earlier request stays revoked. The notice to the old address is the caller's (``email_change_requested_work``).
    """
    moment = now or utcnow()
    await admit_request(session, user, new_address, now=moment)
    user_id = user.id
    # The first write takes SQLite's write lock: what follows sees every request that wrote before this one.
    await user_service.revoke_pending_email_change(session, user_id, now=moment)
    issued = await token_service.issue_token(session, CHANGE, user_id=user_id, email=new_address, created_by_user_id=user_id, ttl=PROFILE_CHANGE_TTL, now=moment)
    # Counted again under the lock, the new link included: of two requests that passed the first count, the second stops here.
    if len(await _emails_in_last_hour(session, user_id, moment)) > CONFIRMATIONS_PER_HOUR:
        await session.rollback()
        raise EmailRateLimitedError(RESEND_MIN_INTERVAL.total_seconds())
    # Read before the commit: what the answer needs, whatever the session does with its rows after it.
    token_id, expires_at = issued.record.id, ensure_utc(issued.record.expires_at)
    await session.commit()
    try:
        await _send_confirmation(session, user_id, new_address, issued, moment)
    except (EmailError, ValueError) as exc:
        await _drop_failed(session, token_id, moment)
        logger.warning("Email change confirmation not sent: nothing waits", user_id=user_id, token_id=token_id, reason=type(exc).__name__, code=getattr(exc, "code", None))
        raise
    except Exception:
        # Not an email refusal: the link is dropped all the same, and the error goes up whole, logged once by the platform.
        await _drop_failed(session, token_id, moment)
        raise
    EMAIL_CHANGE_LINKS_BY_MAILBOX.hit(delivery.mailbox_budget_key(new_address))
    logger.info("Email change requested from Profile, confirmation emailed", user_id=user_id, token_id=token_id)
    return PendingEmailChange(email=new_address, expires_at=expires_at)


async def resend(session: AsyncSession, user: User, *, now: Optional[datetime] = None) -> PendingEmailChange:
    """«Send again»: a new link for the address the account waits for; the earlier one is revoked only once the new email went.

    Raises ``EmailChangeNotPendingError`` (nothing waits, also when a cancel or a password change committed meanwhile);
    ``EmailChangeRefusedError`` when the address was taken meanwhile — the waiting link is then revoked; what
    ``_admit_email`` raises (with the 60-second interval), nothing written; and what ``send_email`` raises — the new link is
    dropped and the earlier one stays valid.
    """
    moment = now or utcnow()
    user_id = user.id
    waiting = await pending(session, user_id, now=moment)
    if waiting is None:
        raise EmailChangeNotPendingError()
    address = waiting.email
    try:
        await _refused(session, user, address)
    except EmailChangeRefusedError:
        await user_service.revoke_pending_email_change(session, user_id, now=moment)
        await session.commit()
        logger.info("Email change resend refused, the request revoked", user_id=user_id, reason="address_taken")
        raise
    await _admit_email(session, user_id, address, moment, resend=True)
    issued = await token_service.issue_token(session, CHANGE, user_id=user_id, email=address, created_by_user_id=user_id, ttl=PROFILE_CHANGE_TTL, now=moment)
    # Under the lock: the request may have been cancelled meanwhile (a cancel, a password change): then nothing waits.
    earlier = [link for link in await _live_links(session, user_id, moment) if link.id != issued.record.id]
    if not earlier or not user_service.same_email(earlier[0].email or "", address):
        await session.rollback()
        raise EmailChangeNotPendingError()
    created = await _emails_in_last_hour(session, user_id, moment)
    if len(created) > CONFIRMATIONS_PER_HOUR or sum(value > moment - RESEND_MIN_INTERVAL for value in created) > 1:
        await session.rollback()
        raise EmailRateLimitedError(RESEND_MIN_INTERVAL.total_seconds())
    token_id, expires_at = issued.record.id, ensure_utc(issued.record.expires_at)
    await session.commit()
    try:
        await _send_confirmation(session, user_id, address, issued, moment)
    except (EmailError, ValueError) as exc:
        await _drop_failed(session, token_id, moment)
        logger.warning("Email change confirmation not resent: the earlier link stays", user_id=user_id, token_id=token_id, reason=type(exc).__name__, code=getattr(exc, "code", None))
        raise
    except Exception:
        await _drop_failed(session, token_id, moment)
        raise
    # The earlier links only: a newer request that committed during the send keeps its own.
    await session.execute(update(AccountToken).where(*_own_links(user_id), AccountToken.id < token_id, AccountToken.consumed_at.is_(None), AccountToken.revoked_at.is_(None)).values(revoked_at=moment).execution_options(synchronize_session=False))  # type: ignore[union-attr]
    await session.commit()
    EMAIL_CHANGE_LINKS_BY_MAILBOX.hit(delivery.mailbox_budget_key(address))
    logger.info("Email change confirmation resent", user_id=user_id, token_id=token_id)
    return PendingEmailChange(email=address, expires_at=expires_at)


async def cancel(session: AsyncSession, user_id: int, *, now: Optional[datetime] = None) -> None:
    """Revoke every Profile link of ``user_id``; commits. Nothing waiting is no error."""
    revoked = await user_service.revoke_pending_email_change(session, user_id, now=now)
    await session.commit()
    if revoked:
        logger.info("Email change request cancelled", user_id=user_id)


async def _refusal(session: AsyncSession, record: AccountToken, user: Optional[User]) -> Optional[str]:
    """Why a spent Profile link cannot move its account, as a stable word for the log; None when it can."""
    if user is None:
        return "no_account"
    if record.created_by_user_id != user.id:
        return "not_profile"
    if not user.is_active:
        return "inactive"
    if record.email is None:
        return "no_address"
    if await asyncio.to_thread(user_service.account_protection, user) is not None:
        return "protected"
    if await user_service.email_refusal(session, user, record.email) is not None:
        return "address_taken"
    return None


async def confirm_profile_change(session: AsyncSession, token: str, *, acting_user_id: Optional[int], now: Optional[datetime] = None) -> ConfirmedProfileChange:
    """The click on a Profile link, by ``acting_user_id`` (the account of the request's session; None without one); commits.

    A dead link: ``ProfileEmailChangeLinkInvalidError`` with its status, to anyone, nothing written. A live link whose account
    is not ``acting_user_id``: ``ProfileEmailChangeSignInRequiredError``, nothing written — the link is read, never spent or
    revoked. Otherwise the link is spent, the conditions read again, and the account moves (``move_email``, verified now);
    when a condition fails the link is revoked in the same transaction and the error says ``revoked``.
    """
    moment = now or utcnow()
    inspection = await token_service.inspect_token(session, token, CHANGE, now=moment)
    record = inspection.record
    if inspection.status is not token_service.TokenStatus.VALID or record is None:
        await session.rollback()
        raise ProfileEmailChangeLinkInvalidError(inspection.status.value)
    if acting_user_id is None or record.user_id != acting_user_id:
        # Read before the rollback, which expires the row: an async session cannot reload it.
        token_id = record.id
        await session.rollback()
        logger.info("Email change link needs the session of its account: nothing changed", token_id=token_id)
        raise ProfileEmailChangeSignInRequiredError()
    # The write comes first: it takes SQLite's write lock, and of two clicks racing for the same link only one spends it.
    spent = await token_service.consume_token(session, token, CHANGE, consumed_by_user_id=acting_user_id, now=moment)
    if spent is None:
        await session.rollback()
        status = (await token_service.inspect_token(session, token, CHANGE, now=moment)).status
        raise ProfileEmailChangeLinkInvalidError((status if status is not token_service.TokenStatus.VALID else token_service.TokenStatus.CONSUMED).value)
    token_id, address = spent.id, spent.email
    user = (await session.execute(select(User).where(User.id == spent.user_id).execution_options(populate_existing=True))).scalars().first()
    reason = await _refusal(session, spent, user)
    if reason is None and user is not None and address is not None:
        old_email = user.email
        try:
            # A savepoint: should the unique index on lower(email) catch an account that took the address after the check,
            # only the change is undone, and the link is revoked below in this same transaction
            async with session.begin_nested():
                await user_service.move_email(session, user, address, verified_at=moment)
                user.updated_at = moment
                session.add(user)
                await session.flush()
        except IntegrityError:
            reason = "address_taken"
        else:
            await session.commit()
            await session.refresh(user)
            logger.info("Email changed from Profile through its confirmation link, sessions ended", user_id=user.id, token_id=token_id)
            return ConfirmedProfileChange(user=user, old_email=old_email)
    # Not applied: the link was spent for nothing, so it is revoked, in this same transaction: there is no moment at which
    # it is neither spent nor revoked
    await session.execute(update(AccountToken).where(AccountToken.id == token_id).values(consumed_at=None, consumed_by_user_id=None, revoked_at=moment).execution_options(synchronize_session=False))
    await session.commit()
    logger.info("Email change link refused and revoked", token_id=token_id, reason=reason)
    raise ProfileEmailChangeLinkInvalidError(token_service.TokenStatus.REVOKED.value)


async def email_change_requested_work(user_id: int, old_address: str, *, engine: Optional[AsyncEngine] = None) -> None:
    """The notice «a change of your address was requested» to the address the account has now, after the answer, with a
    session of its own (D5.1). No link and nothing of the new address (N62). Nothing goes when email is off, the account is
    gone, or the old mailbox had 3 such notices in the hour (``EMAIL_CHANGE_REQUESTED_BY_MAILBOX``). Never raises.
    """
    try:
        if not (await asyncio.to_thread(delivery.email_config_state)).configured:
            return
        mailbox = delivery.mailbox_budget_key(old_address)
        if not EMAIL_CHANGE_REQUESTED_BY_MAILBOX.peek(mailbox).allowed:
            logger.info("Email change requested notice: the mailbox is past its limit, not sent", user_id=user_id)
            return
        async with AsyncSession(engine or get_async_engine(), expire_on_commit=False) as session:
            if await user_service.get_user_by_id(session, user_id) is None:
                return
            language = await account_language(session, user_id)
        links = links_state()
        content = build_email_change_requested(language=language, instance=links.instance if links.ready else INSTANCE_FALLBACK)
        await send_email(content, to=old_address, user_id=user_id)
        EMAIL_CHANGE_REQUESTED_BY_MAILBOX.hit(mailbox)
        logger.info("Email change requested notice sent to the current address", user_id=user_id)
    except (EmailError, ValueError) as exc:
        logger.warning("Email change requested notice: not sent", user_id=user_id, reason=type(exc).__name__, code=getattr(exc, "code", None))
    except Exception as exc:  # noqa: BLE001 — a background task has nobody to raise to: log and end
        # No traceback: a database error would print its SQL parameters.
        logger.error("Email change requested notice: the request failed", user_id=user_id, error=type(exc).__name__)
