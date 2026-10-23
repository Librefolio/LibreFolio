"""What LibreFolio sends, and to whom: one function per email that an action of the application sends.

Every email of an account goes out in the account's language: its own (``user_settings.language``), otherwise the
instance's ``default_language``, otherwise English. A language that names none of the four counts as unset. The
functions here only decide content, recipient and language; ``delivery.send_email`` checks the configuration and the
hourly budget, sends, and logs. Every link an email carries comes from ``links.email_link``: only
``LIBREFOLIO_PUBLIC_URL`` (developer decision 45).
"""

from __future__ import annotations

import asyncio
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
from backend.app.services.email.links import email_link, links_state, require_links
from backend.app.services.email.messages import build_email_changed, build_invite, build_password_reset, build_test_message, email_language, supported_email_language
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

logger = structlog.get_logger(__name__)

LinkPurpose = Literal["invite", "password_reset"]

_PURPOSES: dict[str, AccountTokenPurpose] = {"invite": AccountTokenPurpose.INVITE, "password_reset": AccountTokenPurpose.PASSWORD_RESET}

# «Forgot password», per client address: not a limiter of its own. It spends the counter every activation and reset
# email asks for, ``delivery.ADDRESS_BUDGET`` (``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`` an hour, 20 by default),
# keyed by workstream H's ``client_rate_key()``: an IPv6 client counts by its /64, which one subscriber usually holds
# whole. The address is H's ``rate_limit_address()``, from ``client_address()``: the header a trusted proxy sets when
# ``LIBREFOLIO_CLIENT_IP_HEADER`` names it, otherwise the connection's, which follows ``X-Forwarded-For`` only from the
# proxies uvicorn trusts (``FORWARDED_ALLOW_IPS``).
#: «Forgot password», per identifier as written (case-insensitive): 3 requests an hour, whether an account matches or not.
FORGOT_BY_IDENTIFIER = SlidingWindowLimiter(3, 60 * 60)
#: «Forgot password», per recipient mailbox (``delivery.mailbox_budget_key()``: the aliases of one mailbox count
#: together): 3 emails an hour, whatever account they are for — several accounts may give the same mailbox.
FORGOT_BY_MAILBOX = SlidingWindowLimiter(3, 60 * 60)
#: Per account, counted on its reset links: at most one email every 5 minutes, and 3 an hour; past them, in silence.
RESET_EMAIL_MIN_INTERVAL = timedelta(minutes=5)
RESET_EMAILS_PER_HOUR = 3
#: Email-change notices: 3 an hour per account, and 3 an hour per recipient mailbox (``delivery.mailbox_budget_key()``).
#: Without them, an account could point its email at any address, change it again, and so have the instance write to
#: that address as often as the hourly budget allows. Counted on the notices that went out.
EMAIL_CHANGE_NOTICES_BY_ACCOUNT = SlidingWindowLimiter(3, 60 * 60)
EMAIL_CHANGE_NOTICES_BY_MAILBOX = SlidingWindowLimiter(3, 60 * 60)


class EmailAccountInactiveError(EmailError):
    """A password-reset link of an account that is not active: it would set a password nobody can use yet."""

    def __init__(self) -> None:
        super().__init__("EMAIL_ACCOUNT_INACTIVE")


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


async def require_email() -> delivery.EmailConfigState:
    """The configuration when email can be used now, else ``EmailUnavailableError`` (``INSTANCE_BLOCKED`` while the
    hosting provider blocks the instance); read off the event loop."""
    if delivery.sending_blocked():
        raise EmailUnavailableError("INSTANCE_BLOCKED")
    state = await asyncio.to_thread(delivery.email_config_state)
    if not state.usable:
        raise EmailUnavailableError(state.problem or "EMAIL_NOT_CONFIGURED")
    return state


def link_ttl(record: AccountToken, now: datetime) -> timedelta:
    """How long the link of ``record`` still works at ``now``: never negative."""
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
    await require_email()
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
        content = build_invite(language=lang, link=link, ttl=link_ttl(record, moment), instance=links.instance, inviter=admin.username, grants_admin=record.grants_admin)
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
        content = build_password_reset(language=lang, link=link, ttl=link_ttl(record, moment), instance=links.instance)
        user_id = user.id
    await send_email(content, to=recipient, user_id=user_id)
    logger.info("Link emailed by an administrator", admin_id=admin.id, purpose=purpose, token_id=record.id, user_id=user_id, language=lang)
    return LinkEmailSent(to=recipient, language=lang)


async def admit_forgotten_password(address: str | None, identifier: str) -> None:
    """Whether a «forgot password» request may go on, before anything about the accounts is read.

    Raises ``EmailUnavailableError`` or ``EmailLinksUnavailableError`` (the configuration, the same for everyone) and
    ``EmailRateLimitedError``: too many requests from this address (the counter shared with the activation emails) or for
    this identifier, or the hourly budget of the instance spent; ``retry_after`` is the longest wait of the counters that
    refuse. None of them depends on whether an account matches.
    """
    state = await require_email()
    require_links()
    # The instance's budget and the address's counter are only peeked here: the address's unit is spent by
    # ``forgotten_password_work`` when a reset email really goes, so a request for an unknown account costs it nothing, and
    # the answer cannot depend on whether an account matches. The identifier's counter is hit (a refused hit is not
    # recorded). Without an address (a unix socket), the address counter does not apply: one shared count would let a
    # single client block the feature for everyone; the limits per identifier and per account, and the hourly budget,
    # still do.
    budget = delivery.budget_status(state.max_per_hour)
    identifier_key = identifier.strip().casefold()
    by_address = delivery.address_budget_peek(address)
    if not by_address.allowed:
        # The wait is the longest of the counters that stop the request (a peek: this request does not count there)
        raise EmailRateLimitedError(delivery.longest_wait(by_address, FORGOT_BY_IDENTIFIER.peek(identifier_key), budget))
    by_identifier = FORGOT_BY_IDENTIFIER.hit(identifier_key)
    if not by_identifier.allowed:
        raise EmailRateLimitedError(delivery.longest_wait(by_identifier, budget))
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


async def _held_back(session: AsyncSession, user_id: int, moment: datetime) -> str | None:
    """Why no reset email goes to the account now, as the line to log, or None: it had a reset link moments ago (the per-account limits), or an administrator's reset link is still live."""
    if not await _reset_emails_allowed(session, user_id, moment):
        return "Forgotten password: the account had a reset link moments ago, nothing sent"
    if await _admin_link_live(session, user_id, moment):
        return "Forgotten password: an administrator's reset link is still live, nothing sent"
    return None


def _reset_race_lost(created: list[datetime], moment: datetime) -> bool:
    """Whether the reset links of the account, the new one included, are past its per-account limits: another request won."""
    return len(created) > RESET_EMAILS_PER_HOUR or sum(value > moment - RESET_EMAIL_MIN_INTERVAL for value in created) > 1


async def forgotten_password_work(identifier: str, *, engine: AsyncEngine | None = None, now: datetime | None = None, address: str | None = None) -> None:
    """The work of a «forgot password» request, after its answer: a reset link by email to the account, if there is one.

    Runs in the background with a session of its own. It looks the account up as the login does; an unknown or
    inactive account, an account past its limits or holding an administrator's live reset link, a mailbox past its
    limit, a configuration changed meanwhile or a refused email end it in silence, logged without the identifier. The
    link is created only once the email can go out (configuration, links and hourly budget checked again), and revoked
    when the email does not go out after all. ``address`` is the client's: once every check has admitted the email, just
    before the commit, the work spends a unit of that address's counter (``delivery.ADDRESS_BUDGET``); if the counter
    filled meanwhile, nothing is sent and nothing is kept. Only an email that goes is counted, and the answer to the
    request never depends on it. Never raises.
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
            held_back = await _held_back(session, user_id, moment)
            if held_back is not None:
                logger.info(held_back, user_id=user_id)
                return
            # Checked again now, since the answer went out: nothing is created when the email cannot go.
            state = await require_email()
            links = require_links()
            if not delivery.budget_status(state.max_per_hour).allowed:
                logger.warning("Forgotten password: the hourly limit of the instance is reached, nothing sent", user_id=user_id)
                return
            if not FORGOT_BY_MAILBOX.hit(delivery.mailbox_budget_key(user.email)).allowed:
                logger.info("Forgotten password: the mailbox had reset emails moments ago, nothing sent", user_id=user_id)
                return
            issued = await user_service.create_password_reset(session, user, now=moment)
            # Counted again inside the write transaction, the new link included: of two requests that passed the first
            # count together, the second sees the first one's link here and stops (SQLite writes one at a time).
            created = await _recent_resets(session, user_id, moment)
            if _reset_race_lost(created, moment):
                await session.rollback()
                logger.info("Forgotten password: another request won the race, nothing sent", user_id=user_id)
                return
            if not delivery.address_budget_hit(address).allowed:
                await session.rollback()
                logger.info("Forgotten password: the client address had its emails moments ago, nothing sent", user_id=user_id)
                return
            await session.commit()
            # Read now: after a rollback the row is expired, and an async session cannot reload it inside the handler.
            token_id = issued.record.id
            try:
                language = await account_language(session, user_id)
                content = build_password_reset(
                    language=language,
                    link=email_link(AccountTokenPurpose.PASSWORD_RESET, issued.token),
                    ttl=link_ttl(issued.record, moment),
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


#: The name of the instance in an email that carries no link, when ``LIBREFOLIO_PUBLIC_URL`` gives none: never the host of a
#: request, which its sender writes (night decision of 15/10, to be reviewed).
INSTANCE_FALLBACK = "LibreFolio"


async def email_changed_work(user_id: int, old_address: str, new_address: str, *, engine: AsyncEngine | None = None) -> None:
    """The notice to the address an account had before its email changed, after the answer, with a session of its own.

    It goes only to the old address, in the account's language, and shows nothing of the new one (N62). It carries
    no link, so ``LIBREFOLIO_PUBLIC_URL`` is not needed: the instance is named by it when set, else «LibreFolio». Nothing
    goes when the addresses are the same (``user_service.same_email()``, the one rule of decision P18: A–Z in any case),
    email is off (an ``info`` line, not a warning: the self-hosted default), the account is gone, email cannot be used
    now, or the account or the old mailbox had 3 notices in the hour (``EMAIL_CHANGE_NOTICES_BY_ACCOUNT``,
    ``EMAIL_CHANGE_NOTICES_BY_MAILBOX``); a refusal or a failure is logged without either address. Never raises.
    """
    if user_service.same_email(old_address, new_address):
        return
    try:
        # Email off is the default of a self-hosted instance, not a fault: no warning for it.
        if not (await asyncio.to_thread(delivery.email_config_state)).configured:
            logger.info("Email change notice: email is off, nothing sent", user_id=user_id)
            return
        async with AsyncSession(engine or get_async_engine(), expire_on_commit=False) as session:
            user = await user_service.get_user_by_id(session, user_id)
            if user is None:
                logger.info("Email change notice: the account no longer exists, nothing sent", user_id=user_id)
                return
            await require_email()
            mailbox = delivery.mailbox_budget_key(old_address)
            if not (EMAIL_CHANGE_NOTICES_BY_ACCOUNT.peek(user_id).allowed and EMAIL_CHANGE_NOTICES_BY_MAILBOX.peek(mailbox).allowed):
                logger.info("Email change notice: past its limits, nothing sent", user_id=user_id)
                return
            language = await account_language(session, user_id)
            links = links_state()
            instance = links.instance if links.ready else INSTANCE_FALLBACK
            content = build_email_changed(language=language, instance=instance)
            await send_email(content, to=old_address, user_id=user_id)
            EMAIL_CHANGE_NOTICES_BY_ACCOUNT.hit(user_id)
            EMAIL_CHANGE_NOTICES_BY_MAILBOX.hit(mailbox)
            logger.info("Email change notice sent to the previous address", user_id=user_id, language=language)
    except (EmailError, ValueError) as exc:
        logger.warning("Email change notice: not sent", user_id=user_id, reason=type(exc).__name__, code=getattr(exc, "code", None))
    except Exception as exc:  # noqa: BLE001 — a background task has nobody to raise to: log and end
        # No traceback: a database error would print its SQL parameters.
        logger.error("Email change notice: the request failed", user_id=user_id, error=type(exc).__name__)
