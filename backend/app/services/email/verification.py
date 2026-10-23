"""Email verification (developer decision 44, lot E5): with ``require_email_verification`` on, an account created by
signing up waits for its owner to click a link before it can sign in.

The wait has no column of its own: an account **waits** when it is inactive and holds an email-verification token that
is neither consumed nor revoked, live or expired. Every change of status an administrator makes revokes those tokens,
so a deactivated account never waits, and an old link never wakes it up. ``users.email_verified_at`` (migration 005,
NULL for every account that existed before) records when a link was clicked.

- ``hold_for_verification()`` — inside ``register_user``'s transaction: the account inactive, and a token without an
  ``email`` (the «hold»), whose text never leaves. It marks the wait and, while live, holds the account's place under
  ``LIBREFOLIO_MAX_USERS``.
- ``registration_email_work()`` — after the answer, in the background: a token carrying the account's address replaces
  the hold and goes by email. When the email does not go, the token loses its address and stays as a hold: the
  account still waits, and «resend» works at once.
- ``confirm_email()`` — the link: the account active, ``email_verified_at`` set, its other verification tokens revoked.
- ``resend_verification()`` — the login's «resend»: the password checked as the login checks it, then a new link.
- ``registration_email_verdict()`` — whether a registration's email may go: the client address's counter and the
  instance's hourly budget, the same two «resend» looks at, and the wait when either refuses.
- ``ensure_verification_can_be_enabled()`` — the option turns on only while an email with a link can go out.

Every link comes from ``links.email_link`` (``LIBREFOLIO_PUBLIC_URL``, developer decision 45). No log line holds a
token, an address or an identifier.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import login_throttle, token_service, user_service
from backend.app.services.accounts.auth_service import verify_password_or_dummy
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.services.email import delivery
from backend.app.services.email.delivery import EmailError, EmailRateLimitedError, send_email
from backend.app.services.email.flows import account_language, link_ttl, require_email
from backend.app.services.email.links import email_link, links_state, require_links
from backend.app.services.email.messages import build_verification
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

logger = structlog.get_logger(__name__)

VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION

#: Per account, counted on the verification links already emailed: one every 5 minutes, 3 an hour.
VERIFICATION_EMAIL_MIN_INTERVAL = timedelta(minutes=5)
VERIFICATION_EMAILS_PER_HOUR = 3
#: Per recipient mailbox (``delivery.mailbox_budget_key()``: the aliases of one mailbox count together): 3 verification
#: emails an hour, whatever account they are for, since several accounts may give the same mailbox, as with
#: ``flows.FORGOT_BY_MAILBOX``. Counted on the emails that went out.
VERIFICATION_BY_MAILBOX = SlidingWindowLimiter(3, 60 * 60)
# The activation emails per client address are counted by ``delivery.ADDRESS_BUDGET`` (``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``,
# 20 an hour by default, developer decision 23/10), the one count shared by a registration, «send the link again» and
# «forgot password»; past it the account of a registration is still created and waits, its email held.


class EmailVerificationUnavailableError(EmailError):
    """The option needs an email with a link, and none can go out now (email off or not working, no usable
    ``LIBREFOLIO_PUBLIC_URL``, a blocked instance)."""

    def __init__(self) -> None:
        super().__init__("EMAIL_VERIFICATION_UNAVAILABLE")


class EmailVerificationLinkInvalidError(EmailError):
    """The link is not a live verification link of the account as it is now: ``code`` is the token's status."""


class EmailVerificationNotNeededError(EmailError):
    """The account is active: there is nothing to verify before signing in."""

    def __init__(self) -> None:
        super().__init__("EMAIL_VERIFICATION_NOT_NEEDED")


class VerificationCredentialsError(EmailError):
    """The username or email address and the password do not match an account: the login's answer."""

    def __init__(self) -> None:
        super().__init__("INVALID_CREDENTIALS")


class VerificationAccountDisabledError(EmailError):
    """The account is inactive and does not wait for a link: an administrator deactivated it."""

    def __init__(self) -> None:
        super().__init__("ACCOUNT_DISABLED")


class VerificationUserLimitError(EmailError):
    """The account's link expired, and with it its place: the instance is full now."""

    def __init__(self) -> None:
        super().__init__("USER_LIMIT_REACHED")


async def verification_required(session: AsyncSession) -> bool:
    """Whether the option ``require_email_verification`` is on."""
    return bool(await get_setting_value(session, SETTINGS_REGISTRY.global_.REQUIRE_EMAIL_VERIFICATION.key, False))


async def links_can_go() -> bool:
    """Whether an email with a link can go out now: email usable, ``LIBREFOLIO_PUBLIC_URL`` usable, instance not
    blocked. Reads the configuration off the event loop."""
    if delivery.sending_blocked():
        return False
    state = await asyncio.to_thread(delivery.email_config_state)
    return state.usable and links_state().ready


async def ensure_verification_can_be_enabled() -> None:
    """Raises ``EmailVerificationUnavailableError`` unless an email with a link can go out now."""
    if not await links_can_go():
        raise EmailVerificationUnavailableError()


def _unspent(user_id: int) -> tuple:
    """The conditions of a verification token of ``user_id`` neither consumed nor revoked."""
    return (
        AccountToken.purpose == VERIFICATION,
        AccountToken.user_id == user_id,
        AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
        AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
    )


async def awaiting_verification(session: AsyncSession, user: User) -> bool:
    """Whether ``user`` waits for its verification link: inactive, with an unspent verification token."""
    if user.is_active:
        return False
    return (await session.execute(select(AccountToken.id).where(*_unspent(user.id)).limit(1))).first() is not None


async def _holds_live_link(session: AsyncSession, user_id: int, now: datetime) -> bool:
    """Whether a verification token of the account still holds its place: unspent and not expired."""
    statement = select(AccountToken.id).where(*_unspent(user_id), AccountToken.expires_at > now).limit(1)
    return (await session.execute(statement)).first() is not None


async def place_holders(session: AsyncSession, *, now: datetime | None = None) -> set[int]:
    """The ids of the inactive accounts whose live verification link holds their place, in one query (for a list)."""
    statement = (
        select(AccountToken.user_id)
        .distinct()
        .join(User, User.id == AccountToken.user_id)  # type: ignore[arg-type]
        .where(
            AccountToken.purpose == VERIFICATION,
            AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
            AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
            AccountToken.expires_at > (now or utcnow()),
            User.is_active.is_(False),  # type: ignore[attr-defined]
        )
    )
    return {user_id for user_id in (await session.execute(statement)).scalars().all() if user_id is not None}


async def waiting_ids(session: AsyncSession) -> set[int]:
    """The ids of the inactive accounts waiting for their verification, in one query (for a list): ``awaiting_verification``
    for every account at once, an unspent link live or expired (E-7)."""
    statement = (
        select(AccountToken.user_id)
        .distinct()
        .join(User, User.id == AccountToken.user_id)  # type: ignore[arg-type]
        .where(
            AccountToken.purpose == VERIFICATION,
            AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
            AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
            User.is_active.is_(False),  # type: ignore[attr-defined]
        )
    )
    return {user_id for user_id in (await session.execute(statement)).scalars().all() if user_id is not None}


async def holds_place(session: AsyncSession, user: User, *, now: datetime | None = None) -> bool:
    """Whether ``user`` already holds a place under ``LIBREFOLIO_MAX_USERS`` without being active: it waits for its
    verification with a live link, which ``registration_service.user_usage`` counts. Activating it takes no new place."""
    return not user.is_active and await _holds_live_link(session, user.id, now or utcnow())


async def hold_for_verification(session: AsyncSession, user: User, *, first: bool, now: datetime | None = None) -> bool:
    """Inside ``register_user``'s transaction, once the account is written: whether it must wait for its link.

    Never the instance's first account. With the option on, an email with a link must be able to go out: otherwise the
    registration is refused with ``RegistrationError("EMAIL_VERIFICATION_UNAVAILABLE")`` (decision of the coordinator:
    the safe side). The account becomes inactive and gets the hold token (flushed, not committed).
    """
    if first or not await verification_required(session):
        return False
    if not await links_can_go():
        from backend.app.services.accounts.registration_service import RegistrationError  # noqa: PLC0415 — it calls this module

        raise RegistrationError("EMAIL_VERIFICATION_UNAVAILABLE", "This instance cannot send the verification email now")
    user.is_active = False
    session.add(user)
    await session.flush()
    await token_service.issue_token(session, VERIFICATION, user_id=user.id, now=now)
    logger.info("Registration waits for email verification", user_id=user.id)
    return True


async def _emailed_in_last_hour(session: AsyncSession, user_id: int, now: datetime) -> list[datetime]:
    """When the verification links of the account emailed in the last hour were created: tokens carrying an address."""
    statement = select(AccountToken.created_at).where(
        AccountToken.purpose == VERIFICATION,
        AccountToken.user_id == user_id,
        AccountToken.email.is_not(None),  # type: ignore[union-attr]
        AccountToken.created_at > now - timedelta(hours=1),
    )
    return [ensure_utc(value) for value in (await session.execute(statement)).scalars().all()]


def _per_account_retry_after(created: list[datetime], now: datetime) -> float | None:
    """Seconds until the account may get another verification email, None when it may now."""
    waits = []
    if len(created) >= VERIFICATION_EMAILS_PER_HOUR:
        waits.append(min(created) + timedelta(hours=1) - now)
    recent = [value for value in created if value > now - VERIFICATION_EMAIL_MIN_INTERVAL]
    if recent:
        waits.append(max(recent) + VERIFICATION_EMAIL_MIN_INTERVAL - now)
    return max(waits).total_seconds() if waits else None


async def _issue_and_send(session: AsyncSession, user: User, now: datetime, *, needs_place: bool = False, count_address: bool = False, client_address: str | None = None) -> str:
    """Email the account a new verification link, which replaces its others; returns the email's language.

    Configuration, links, hourly budget and the recipient's mailbox first: nothing is created when the email cannot go.
    The new token carries the account's address, and is committed before the email; when the email does not go, it
    loses its address and stays as a hold, so the account still waits. ``needs_place``: the account holds no place yet
    (its link expired), so the user limit is counted again inside the write transaction. ``count_address``: spend a unit of
    the client ``client_address``'s counter (``delivery.ADDRESS_BUDGET``) once every check has admitted the email, just before
    the commit and so before the email: a refusal then (another request took the last unit) rolls everything back. Only
    «resend» counts; ``registration_email_work`` does not, the registration counted at its answer. The unit stays spent if the
    SMTP server then fails: an email was tried. Raises what ``send_email``
    raises; ``EmailRateLimitedError`` when another request emailed a link meanwhile; ``VerificationUserLimitError`` when
    another took the last place meanwhile; ``EmailVerificationNotNeededError`` or ``VerificationAccountDisabledError``
    when the account stopped waiting meanwhile.
    """
    state = await require_email()
    links = require_links()
    budget = delivery.budget_status(state.max_per_hour)
    if not budget.allowed:
        raise EmailRateLimitedError(budget.retry_after)
    # Read now: a rollback expires ``user``, and an async session cannot reload it.
    user_id, address = user.id, user.email
    mailbox = delivery.mailbox_budget_key(address)
    by_mailbox = VERIFICATION_BY_MAILBOX.peek(mailbox)
    if not by_mailbox.allowed:
        raise EmailRateLimitedError(by_mailbox.retry_after)
    # The first write takes SQLite's lock: what follows sees every request that wrote before this one.
    if not await token_service.revoke_tokens(session, user_id=user_id, purpose=VERIFICATION, now=now):
        # No unspent link left: the account no longer waits (its link was clicked, or an administrator decided
        # meanwhile), and a new link would make it wait again.
        active = (await session.execute(select(User.is_active).where(User.id == user_id))).scalar_one_or_none()
        await session.rollback()
        raise EmailVerificationNotNeededError() if active else VerificationAccountDisabledError()
    issued = await token_service.issue_token(session, VERIFICATION, user_id=user_id, email=address, now=now)
    # Counted again inside the write transaction, the new link included: of two requests that passed the first count
    # together, the second sees the first one's link here and stops (SQLite writes one at a time).
    created = await _emailed_in_last_hour(session, user_id, now)
    if len(created) > VERIFICATION_EMAILS_PER_HOUR or sum(value > now - VERIFICATION_EMAIL_MIN_INTERVAL for value in created) > 1:
        await session.rollback()
        raise EmailRateLimitedError(VERIFICATION_EMAIL_MIN_INTERVAL.total_seconds())
    if needs_place:
        from backend.app.services.accounts.registration_service import user_usage  # noqa: PLC0415 — it calls this module

        # As ``register_user`` does: counted after the write, the new link included; of two requests that saw the same
        # free place, the second sees the first one's link here.
        usage = await user_usage(session, now=now)
        if usage.max_users is not None and usage.used > usage.max_users:
            await session.rollback()
            raise VerificationUserLimitError()
    if count_address:
        spent = delivery.address_budget_hit(client_address)
        if not spent.allowed:
            await session.rollback()
            raise EmailRateLimitedError(spent.retry_after)
    await session.commit()
    token_id = issued.record.id
    try:
        language = await account_language(session, user_id)
        content = build_verification(
            language=language,
            link=email_link(VERIFICATION, issued.token),
            ttl=link_ttl(issued.record, now),
            instance=links.instance,
        )
        await send_email(content, to=address, user_id=user_id)
    except Exception:
        # The email did not go, as far as LibreFolio knows: the token becomes a hold again (no address), so the account
        # still waits and the link does not count against the per-account limits. Should the email arrive after all (a
        # connection lost after the message), ``confirm_email`` refuses that link without revoking it.
        await session.rollback()
        await session.execute(update(AccountToken).where(AccountToken.id == token_id).values(email=None))
        await session.commit()
        raise
    VERIFICATION_BY_MAILBOX.hit(mailbox)
    logger.info("Verification link emailed", user_id=user_id, token_id=token_id, language=language)
    return language


@dataclass(frozen=True)
class RegistrationEmailVerdict:
    """Whether the verification email of a registration may go now, and if not, why and for how long."""

    allowed: bool
    #: Seconds until a new try could pass the counters that stopped this one; 0 when ``allowed``.
    retry_after: float = 0.0
    #: Which counters stopped it: the client address's, the instance's hourly budget, or both.
    by_address: bool = False
    by_instance: bool = False


async def registration_email_verdict(address: str | None) -> RegistrationEmailVerdict:
    """Whether a registration from the client ``address`` may send its verification email now; the address counted when it may.

    Two counters, the same as «send the link again» looks at: the client address's (``delivery.ADDRESS_BUDGET``,
    ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`` an hour, 20 by default, an IPv6 client by its /64; a request without an
    address is not limited by it) and the instance's hourly budget (``LIBREFOLIO_SMTP_MAX_PER_HOUR``). Both are peeked
    first; only when both admit is the address's hit recorded, so a refused registration spends nothing. When either
    refuses, ``retry_after`` is the longest of the waits of the counters that refused. Never raises.
    """
    state = await asyncio.to_thread(delivery.email_config_state)
    by_address = delivery.address_budget_peek(address)
    by_instance = delivery.instance_budget_peek(state)
    if by_address.allowed and (by_instance is None or by_instance.allowed):
        spent = delivery.address_budget_hit(address)
        if spent.allowed:
            return RegistrationEmailVerdict(allowed=True)
        # Another registration took the last unit between the peek and the hit
        by_address = spent
    return RegistrationEmailVerdict(
        allowed=False,
        retry_after=delivery.longest_wait(by_address, by_instance),
        by_address=not by_address.allowed,
        by_instance=by_instance is not None and not by_instance.allowed,
    )


async def registration_email_work(user_id: int, *, engine: AsyncEngine | None = None, now: datetime | None = None) -> None:
    """The verification email of a registration, after its answer, with a session of its own. Never raises.

    Nothing goes when the account no longer waits (an administrator changed its status meanwhile). A refusal or a
    failure is logged; the account keeps waiting, and its owner can ask for the link again from the sign-in page.
    """
    try:
        async with AsyncSession(engine or get_async_engine(), expire_on_commit=False) as session:
            user = await user_service.get_user_by_id(session, user_id)
            if user is None or not await awaiting_verification(session, user):
                logger.info("Verification email: the account no longer waits, nothing sent", user_id=user_id)
                return
            await _issue_and_send(session, user, now or utcnow())
    except (EmailVerificationNotNeededError, VerificationAccountDisabledError):
        # The account stopped waiting between the check above and the write: the same outcome, the same line.
        logger.info("Verification email: the account no longer waits, nothing sent", user_id=user_id)
    except (EmailError, ValueError) as exc:
        logger.warning("Verification email: not sent", user_id=user_id, reason=type(exc).__name__, code=getattr(exc, "code", None))
    except Exception as exc:  # noqa: BLE001 — a background task has nobody to raise to: log and end
        # No traceback: a database error would print its SQL parameters.
        logger.error("Verification email: the request failed", user_id=user_id, error=type(exc).__name__)


async def confirm_email(session: AsyncSession, token: str, *, now: datetime | None = None) -> User:
    """Spend a verification link: the account active, ``email_verified_at`` set, its other verification links revoked.

    Raises ``EmailVerificationLinkInvalidError`` with the token's status when it is not a live verification link; with
    ``revoked`` when it was emailed to an address the account no longer has (the link is revoked then), and when its
    email did not go as far as LibreFolio knows (the link is left as it is: the account keeps waiting). Commits.
    """
    moment = now or utcnow()
    inspection = await token_service.inspect_token(session, token, VERIFICATION, now=moment)
    if inspection.status != token_service.TokenStatus.VALID or inspection.record is None:
        raise EmailVerificationLinkInvalidError(inspection.status.value)
    record = inspection.record
    user = await user_service.get_user_by_id(session, record.user_id) if record.user_id is not None else None
    if user is None:
        raise EmailVerificationLinkInvalidError(token_service.TokenStatus.UNKNOWN.value)
    user_id, token_id = user.id, record.id
    if record.email is None:
        # A link whose email did not go, as far as LibreFolio knows: refused, but not revoked, for it may be the
        # account's only one, and revoking it would end the wait. Signing in offers a new link.
        logger.info("Email verification refused: the link's email did not go out", user_id=user_id, token_id=token_id)
        raise EmailVerificationLinkInvalidError(token_service.TokenStatus.REVOKED.value)
    # The address the link went to against the account's, as A compares two addresses (decision P18).
    if not user_service.same_email(record.email, user.email):
        await token_service.revoke_tokens(session, token_id=token_id, now=moment)
        await session.commit()
        logger.info("Email verification refused: the link was sent to another address", user_id=user_id, token_id=token_id)
        raise EmailVerificationLinkInvalidError(token_service.TokenStatus.REVOKED.value)
    if await token_service.consume_token(session, token, VERIFICATION, consumed_by_user_id=user_id, now=moment) is None:
        await session.rollback()
        raise EmailVerificationLinkInvalidError(token_service.TokenStatus.CONSUMED.value)
    # An account an administrator deactivated has no live link left: its change of status revoked them.
    user.is_active = True
    user.email_verified_at = moment
    session.add(user)
    await token_service.revoke_tokens(session, user_id=user_id, purpose=VERIFICATION, now=moment)
    await session.commit()
    await session.refresh(user)
    logger.info("Email verified", user_id=user_id, token_id=token_id)
    return user


async def resend_verification(session: AsyncSession, *, identifier: str, password: str, address: str | None, now: datetime | None = None) -> str:
    """The login's «resend»: a new verification link by email, for whoever gives the account's password.

    The counter per client address first (``delivery.ADDRESS_BUDGET``, shared with the registration and «forgot
    password»), only looked at: a full one refuses before the password is checked, with the longest wait of the address
    and the instance counters, and a try costs it nothing. It is spent by ``_issue_and_send`` when the email is about to
    leave, so wrong passwords never use it up (they have their own limit), then the sign-in's limit on failed passwords (``login_throttle``, F15: the same two counts as
    ``POST /auth/login``, by the identifier as typed and by the address), then the password as the login checks it (a
    dummy hash for an unknown account, the same refusal for both): a wrong one counts, the right one forgets the
    identifier's failures. Then: ``EmailVerificationNotNeededError`` for an active account, ``VerificationAccountDisabledError``
    for one that does not wait; the configuration, the per-account limits (``EmailRateLimitedError``), and a place
    again when the old link expired (``VerificationUserLimitError``). Returns the email's language; raises what
    ``send_email`` raises.
    """
    moment = now or utcnow()
    # Only looked at here, to answer at once with the time to wait: the address's counter counts the emails that go, not the
    # tries (wrong passwords have their own limit, ``login_throttle``). The hit is in ``_issue_and_send``, when the email
    # is about to leave.
    decision = delivery.address_budget_peek(address)
    if not decision.allowed:
        # The wait is the longest of the counters that stop the request: the instance's budget too, when it is spent
        state = await asyncio.to_thread(delivery.email_config_state)
        raise EmailRateLimitedError(delivery.longest_wait(decision, delivery.instance_budget_peek(state)))
    # The sign-in's limit (F15): the password is guessed no faster here than at the sign-in, refused before it is checked
    refused = login_throttle.refusal(identifier, address)
    if refused is not None:
        raise EmailRateLimitedError(refused.retry_after)
    user = await user_service.get_user_by_username_or_email(session, identifier)
    password_ok = await asyncio.to_thread(verify_password_or_dummy, password, user.hashed_password if user else None)
    if not password_ok or user is None:
        # An unknown identifier counts as a wrong password does: the count tells nothing of who has an account.
        login_throttle.record_failure(identifier, address)
        # Logged as the login logs its failures, without the identifier: monitoring that watches them sees these too.
        logger.warning("Verification resend refused: wrong credentials")
        raise VerificationCredentialsError()
    login_throttle.record_success(identifier)
    if user.is_active:
        raise EmailVerificationNotNeededError()
    if not await awaiting_verification(session, user):
        raise VerificationAccountDisabledError()
    await require_email()
    require_links()
    retry_after = _per_account_retry_after(await _emailed_in_last_hour(session, user.id, moment), moment)
    if retry_after is not None:
        raise EmailRateLimitedError(retry_after)
    needs_place = not await _holds_live_link(session, user.id, moment)
    if needs_place:
        from backend.app.services.accounts.registration_service import user_usage  # noqa: PLC0415 — it calls this module

        if (await user_usage(session, now=moment)).full:
            raise VerificationUserLimitError()
    return await _issue_and_send(session, user, moment, needs_place=needs_place, count_address=True, client_address=address)
