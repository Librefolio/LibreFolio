"""What LibreFolio sends, and to whom: one function per email that an action of the application sends.

Every email of an account goes out in the account's language: its own (``user_settings.language``), otherwise the
instance's ``default_language``, otherwise English. A language that names none of the four counts as unset. The
functions here only decide content, recipient and language; ``delivery.send_email`` checks the configuration and the
hourly budget, sends, and logs. Every link an email carries comes from ``links.email_link``: only
``LIBREFOLIO_PUBLIC_URL`` (developer decision 45).
"""

from __future__ import annotations

import asyncio
import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.db.models import AccountToken, AccountTokenPurpose, User, UserSettings
from backend.app.db.session import get_async_engine
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import token_service, user_service
from backend.app.services.accounts.global_settings_service import get_setting_value
from backend.app.services.email import delivery
from backend.app.services.email.delivery import EmailError, EmailRateLimitedError, EmailUnavailableError, send_email
from backend.app.services.email.links import email_link, require_links
from backend.app.services.email.messages import build_invite, build_password_reset, build_test_message, email_language, supported_email_language
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

logger = structlog.get_logger(__name__)

LinkPurpose = Literal["invite", "password_reset"]

_PURPOSES: dict[str, AccountTokenPurpose] = {"invite": AccountTokenPurpose.INVITE, "password_reset": AccountTokenPurpose.PASSWORD_RESET}

#: «Forgot password» is held: ``POST /email/password-reset`` answers 409 ``FORGOT_PASSWORD_DISABLED`` until workstream A
#: asks for the current password to change an account's email (security review of E3, coordinator's decision, 15/10).
#: Without that, a moment inside someone's session (a stolen cookie, an unlocked machine) would be enough to put an
#: address of one's own on the account and then reset its password from it: a lasting takeover. Lifted with lot E4.
FORGOT_PASSWORD_HELD = True

#: «Forgot password», per client address: 10 requests every 15 minutes; an IPv6 client counts by its /64, which one
#: subscriber usually holds whole. The address is the one uvicorn gives the request (``request.client.host``): it follows
#: ``X-Forwarded-For`` only from the proxies it trusts (``FORWARDED_ALLOW_IPS``), so a forged header does not move it.
FORGOT_BY_ADDRESS = SlidingWindowLimiter(10, 15 * 60)
#: «Forgot password», per identifier as written (case-insensitive): 3 requests an hour, whether an account matches or not.
FORGOT_BY_IDENTIFIER = SlidingWindowLimiter(3, 60 * 60)
#: «Forgot password», per recipient mailbox (case-insensitive): 3 emails an hour, whatever account they are for — several
#: accounts may give the same mailbox.
FORGOT_BY_MAILBOX = SlidingWindowLimiter(3, 60 * 60)
#: Per account, counted on its reset links: at most one email every 5 minutes, and 3 an hour; past them, in silence.
RESET_EMAIL_MIN_INTERVAL = timedelta(minutes=5)
RESET_EMAILS_PER_HOUR = 3


class ForgottenPasswordHeldError(EmailError):
    """«Forgot password» is held (``FORGOT_PASSWORD_HELD``)."""

    def __init__(self) -> None:
        super().__init__("FORGOT_PASSWORD_DISABLED")


class EmailAccountInactiveError(EmailError):
    """A password-reset link of an account that is not active: it would set a password nobody can use yet."""

    def __init__(self) -> None:
        super().__init__("EMAIL_ACCOUNT_INACTIVE")


def address_key(address: str | None) -> str | None:
    """The key of ``address`` for the per-address limit: an IPv4 address as is, an IPv6 one by its /64, anything else
    (a name, a unix socket) as written; ``None`` without an address, an empty one included."""
    if not address:
        return None
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return address
    if not isinstance(ip, ipaddress.IPv6Address):
        return str(ip)
    if ip.ipv4_mapped is not None:
        return str(ip.ipv4_mapped)
    # From the integer, so a zone (``fe80::1%eth0``) does not get in the way.
    return str(ipaddress.IPv6Network((int(ip) >> 64 << 64, 64)))


class EmailLinkInvalidError(EmailError):
    """The token is not a live link of that purpose: ``code`` is its status (``expired``, ``consumed``, ``revoked``, ``unknown``)."""


class EmailRecipientRequiredError(EmailError):
    """An invitation without an address to send it to: none given, and none written in the invitation."""

    def __init__(self) -> None:
        super().__init__("EMAIL_RECIPIENT_REQUIRED")


class EmailRecipientNotAllowedError(EmailError):
    """A password-reset link goes only to the address of its account: another address is refused."""

    def __init__(self) -> None:
        super().__init__("EMAIL_RECIPIENT_NOT_ALLOWED")


@dataclass(frozen=True)
class LinkEmailSent:
    """Where a link went, and in which language."""

    to: str
    language: str


async def account_language(session: AsyncSession, user_id: int) -> str:
    """The language of the emails of an account: its own, else the instance's ``default_language``, else English.

    Reads the language column alone: a settings row that no longer validates (an old theme, say) never stops an email.
    Creates nothing.
    """
    own = (await session.execute(select(UserSettings.language).where(UserSettings.user_id == user_id))).scalar_one_or_none()
    language = supported_email_language(own)
    if language is not None:
        return language
    return await instance_language(session)


async def instance_language(session: AsyncSession) -> str:
    """The instance's ``default_language``, else English: the language of an email to someone without an account."""
    return email_language(await get_setting_value(session, SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key, "en"))


async def send_test_email(session: AsyncSession, user: User, *, instance: str) -> str:
    """Send the test email to ``user``'s own address, in their language; returns that language.

    ``instance`` names the instance in the text. Raises what ``delivery.send_email`` raises.
    """
    language = await account_language(session, user.id)
    content = build_test_message(language=language, username=user.username, instance=instance)
    await send_email(content, to=user.email, user_id=user.id)
    return language


async def _require_email() -> delivery.EmailConfigState:
    """The configuration when email can be used now, else ``EmailUnavailableError`` (``INSTANCE_BLOCKED`` while the
    hosting provider blocks the instance); read off the event loop."""
    if delivery.sending_blocked():
        raise EmailUnavailableError("INSTANCE_BLOCKED")
    state = await asyncio.to_thread(delivery.email_config_state)
    if not state.usable:
        raise EmailUnavailableError(state.problem or "EMAIL_NOT_CONFIGURED")
    return state


def _remaining(record: AccountToken, now: datetime) -> timedelta:
    return max(ensure_utc(record.expires_at) - ensure_utc(now), timedelta(0))


async def send_link_email(
    session: AsyncSession,
    *,
    admin: User,
    purpose: LinkPurpose,
    token: str,
    to: str | None = None,
    language: str | None = None,
    now: datetime | None = None,
) -> LinkEmailSent:
    """Email a link an administrator has just created, built from ``LIBREFOLIO_PUBLIC_URL`` alone.

    An invitation goes to ``to``, else to the address written in it, in ``language`` or the instance's; a
    password-reset link goes only to the address of its account, in the account's language. Raises
    ``EmailUnavailableError``, ``EmailLinksUnavailableError``, ``EmailLinkInvalidError`` (the token is not a live link of
    that purpose), ``EmailRecipientRequiredError``, ``EmailRecipientNotAllowedError``, ``EmailAccountInactiveError`` (a
    reset link of an inactive account), and what ``send_email`` raises.
    """
    await _require_email()
    links = require_links()
    moment = now or utcnow()
    inspection = await token_service.inspect_token(session, token, _PURPOSES[purpose], now=moment)
    if inspection.status != token_service.TokenStatus.VALID or inspection.record is None:
        raise EmailLinkInvalidError(inspection.status.value)
    record = inspection.record
    link = email_link(_PURPOSES[purpose], token)
    if purpose == "invite":
        recipient = to or record.email
        if not recipient:
            raise EmailRecipientRequiredError()
        lang = supported_email_language(language) or await instance_language(session)
        content = build_invite(language=lang, link=link, ttl=_remaining(record, moment), instance=links.instance, inviter=admin.username, grants_admin=record.grants_admin)
        user_id = None
    else:
        if to is not None:
            raise EmailRecipientNotAllowedError()
        user = await user_service.get_user_by_id(session, record.user_id) if record.user_id is not None else None
        if user is None:
            raise EmailLinkInvalidError(token_service.TokenStatus.UNKNOWN.value)
        if not user.is_active:
            raise EmailAccountInactiveError()
        recipient = user.email
        lang = await account_language(session, user.id)
        content = build_password_reset(language=lang, username=user.username, link=link, ttl=_remaining(record, moment), instance=links.instance)
        user_id = user.id
    await send_email(content, to=recipient, user_id=user_id)
    logger.info("Link emailed by an administrator", admin_id=admin.id, purpose=purpose, token_id=record.id, user_id=user_id, language=lang)
    return LinkEmailSent(to=recipient, language=lang)


async def admit_forgotten_password(address: str | None, identifier: str) -> None:
    """Whether a «forgot password» request may go on, before anything about the accounts is read.

    Raises ``ForgottenPasswordHeldError`` while the feature is held (``FORGOT_PASSWORD_HELD``),
    ``EmailUnavailableError`` or ``EmailLinksUnavailableError`` (the configuration, the same for everyone) and
    ``EmailRateLimitedError``: too many requests from this address or for this identifier, or the hourly budget of the
    instance spent. None of them depends on whether an account matches.
    """
    if FORGOT_PASSWORD_HELD:
        raise ForgottenPasswordHeldError()
    state = await _require_email()
    require_links()
    # Without an address (a unix socket), one shared count would let a single client block the feature for everyone:
    # the limits per identifier and per account, and the hourly budget, still apply.
    checks = ((FORGOT_BY_ADDRESS, address_key(address)), (FORGOT_BY_IDENTIFIER, identifier.strip().casefold()))
    for limiter, key in checks:
        if key is None:
            continue
        decision = limiter.hit(key)
        if not decision.allowed:
            raise EmailRateLimitedError(decision.retry_after)
    budget = delivery.budget_status(state.max_per_hour)
    if not budget.allowed:
        raise EmailRateLimitedError(budget.retry_after)


async def _recent_resets(session: AsyncSession, user_id: int, now: datetime) -> list[datetime]:
    """When the reset links of the account created in the last hour were created, whoever created them."""
    statement = select(AccountToken.created_at).where(
        AccountToken.purpose == AccountTokenPurpose.PASSWORD_RESET,
        AccountToken.user_id == user_id,
        AccountToken.created_at > now - timedelta(hours=1),
    )
    return [ensure_utc(value) for value in (await session.execute(statement)).scalars().all()]


async def _reset_emails_allowed(session: AsyncSession, user_id: int, now: datetime) -> bool:
    """At most one reset link every ``RESET_EMAIL_MIN_INTERVAL`` and ``RESET_EMAILS_PER_HOUR`` an hour, per account."""
    created = await _recent_resets(session, user_id, now)
    return len(created) < RESET_EMAILS_PER_HOUR and all(value <= now - RESET_EMAIL_MIN_INTERVAL for value in created)


async def _admin_link_live(session: AsyncSession, user_id: int, now: datetime) -> bool:
    """Whether an administrator gave the account a reset link that still works: a request must not cancel it."""
    statement = select(AccountToken.id).where(
        AccountToken.purpose == AccountTokenPurpose.PASSWORD_RESET,
        AccountToken.user_id == user_id,
        AccountToken.created_by_user_id.is_not(None),  # type: ignore[union-attr]
        AccountToken.consumed_at.is_(None),  # type: ignore[union-attr]
        AccountToken.revoked_at.is_(None),  # type: ignore[union-attr]
        AccountToken.expires_at > now,
    )
    return (await session.execute(statement.limit(1))).first() is not None


async def forgotten_password_work(identifier: str, *, engine: AsyncEngine | None = None, now: datetime | None = None) -> None:
    """The work of a «forgot password» request, after its answer: a reset link by email to the account, if there is one.

    Runs in the background with a session of its own. It looks the account up as the login does; an unknown or
    inactive account, an account past its limits or holding an administrator's live reset link, a mailbox past its
    limit, a configuration changed meanwhile or a refused email end it in silence, logged without the identifier. The
    link is created only once the email can go out (configuration, links and hourly budget checked again), and revoked
    when the email does not go out after all. Never raises.
    """
    try:
        async with AsyncSession(engine or get_async_engine(), expire_on_commit=False) as session:
            user = await user_service.get_user_by_username_or_email(session, identifier.strip())
            if user is None or not user.is_active:
                logger.info("Forgotten password: no active account matches, nothing sent")
                return
            # Read now: a rollback expires ``user``, and an async session cannot reload it inside a log call.
            user_id = user.id
            moment = now or utcnow()
            if not await _reset_emails_allowed(session, user_id, moment):
                logger.info("Forgotten password: the account had a reset link moments ago, nothing sent", user_id=user_id)
                return
            if await _admin_link_live(session, user_id, moment):
                logger.info("Forgotten password: an administrator's reset link is still live, nothing sent", user_id=user_id)
                return
            # Checked again now, since the answer went out: nothing is created when the email cannot go.
            state = await _require_email()
            links = require_links()
            if not delivery.budget_status(state.max_per_hour).allowed:
                logger.warning("Forgotten password: the hourly limit of the instance is reached, nothing sent", user_id=user_id)
                return
            if not FORGOT_BY_MAILBOX.hit(user.email.strip().casefold()).allowed:
                logger.info("Forgotten password: the mailbox had reset emails moments ago, nothing sent", user_id=user_id)
                return
            issued = await user_service.create_password_reset(session, user, now=moment)
            # Counted again inside the write transaction, the new link included: of two requests that passed the first
            # count together, the second sees the first one's link here and stops (SQLite writes one at a time).
            created = await _recent_resets(session, user_id, moment)
            if len(created) > RESET_EMAILS_PER_HOUR or sum(value > moment - RESET_EMAIL_MIN_INTERVAL for value in created) > 1:
                await session.rollback()
                logger.info("Forgotten password: another request won the race, nothing sent", user_id=user_id)
                return
            await session.commit()
            # Read now: after a rollback the row is expired, and an async session cannot reload it inside the handler.
            token_id = issued.record.id
            try:
                language = await account_language(session, user_id)
                content = build_password_reset(
                    language=language,
                    username=user.username,
                    link=email_link(AccountTokenPurpose.PASSWORD_RESET, issued.token),
                    ttl=_remaining(issued.record, moment),
                    instance=links.instance,
                )
                await send_email(content, to=user.email, user_id=user_id)
            except Exception:
                # Whatever stopped it, the link reached nobody: it must not stay live.
                await session.rollback()
                await token_service.revoke_tokens(session, token_id=token_id)
                await session.commit()
                raise
            logger.info("Forgotten password: reset link emailed", user_id=user_id, token_id=token_id, language=language)
    except (EmailError, ValueError) as exc:
        logger.warning("Forgotten password: no email sent", reason=type(exc).__name__, code=getattr(exc, "code", None))
    except Exception as exc:  # noqa: BLE001 — a background task has nobody to raise to: log and end
        # No traceback: a database error would print its SQL parameters, the identifier among them.
        logger.error("Forgotten password: the request failed", error=type(exc).__name__)
