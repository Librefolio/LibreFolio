"""Whether this instance can send email, and the sending itself.

``email_config_state()`` reads the ``LIBREFOLIO_SMTP_*`` variables (and ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``) now and never raises: without a host email is off,
as before release 1.3; a value that cannot be used also turns it off, and is logged once per process with the variable
at fault (never its value when it is a secret). The server starts either way.

``send_email()`` sends one ``EmailContent`` to one address. Every attempt takes one unit of the hourly budget of the
instance (``LIBREFOLIO_SMTP_MAX_PER_HOUR``, 50 by default), a sliding window kept in this process: with N worker
processes the budget is N times as large. ``smtplib`` blocks, so the SMTP exchange runs in a worker thread, never on
the event loop. Every outcome is logged with the kind of email, the account and the domain of the recipient; never the
body, the link it carries, the recipient's full address nor the password of the SMTP server — not even inside the
server's own words, which often quote the address they refuse.

``mailbox_budget_key()`` is the key the per-mailbox limits of ``flows`` and ``verification`` count by: the aliases of
one mailbox share it (backlog E-9).
"""

from __future__ import annotations

import asyncio
import functools
import re
from dataclasses import dataclass

import structlog

from backend.app.config import SecretFileError
from backend.app.config.email import (
    DEFAULT_SIGNUP_EMAILS_PER_ADDRESS,
    DEFAULT_SMTP_MAX_PER_HOUR,
    EmailConfigError,
    signup_emails_per_address,
    smtp_host,
    smtp_max_per_hour,
    smtp_password,
    smtp_port,
    smtp_reply_to,
    smtp_sender,
    smtp_tls_mode,
    smtp_user,
)
from backend.app.config.platform import instance_blocked
from backend.app.services.email import smtp
from backend.app.services.email.messages import EmailContent, compose_message
from backend.app.services.platform.client_address import client_rate_key
from backend.app.utils.runtime.rate_window import RateDecision, SlidingWindowLimiter

logger = structlog.get_logger(__name__)

#: The window of the hourly budget, in seconds.
BUDGET_WINDOW_SECONDS = 3600.0

#: The emails this process sent in the last hour; read at call time, so a test can replace it.
INSTANCE_BUDGET = SlidingWindowLimiter(DEFAULT_SMTP_MAX_PER_HOUR, BUDGET_WINDOW_SECONDS, max_keys=1)

#: The activation and password-reset emails one client address may ask for in the last hour, one count shared by the
#: three ways to ask: a registration, «send the link again» from the sign-in page, and «forgot password». Keyed by
#: ``client_rate_key()`` (an IPv6 client by its /64). One limiter for the process, built with the default; its limit
#: is ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``, read from the environment at every call and passed to ``hit``/``peek``
#: (as ``send_email`` does with ``INSTANCE_BUDGET``): nothing is read at import, a change is seen at once, a test sets
#: the variable. The limiter is thread-safe. Read at call time, so a test can replace it.
ADDRESS_BUDGET = SlidingWindowLimiter(DEFAULT_SIGNUP_EMAILS_PER_ADDRESS, BUDGET_WINDOW_SECONDS)


@dataclass(frozen=True)
class EmailConfigState:
    """The email configuration as read now: off, usable, or set but unusable (``problem`` and ``variable`` say why)."""

    configured: bool
    problem: str | None = None
    variable: str | None = None
    server: smtp.SmtpServer | None = None
    sender: tuple[str, str] | None = None
    reply_to: tuple[str, str] | None = None
    max_per_hour: int = DEFAULT_SMTP_MAX_PER_HOUR

    @property
    def usable(self) -> bool:
        """A host is set and every value can be used."""
        return self.configured and self.problem is None


class EmailError(Exception):
    """An email that was not sent; ``code`` is what the API answers with."""

    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code


class EmailUnavailableError(EmailError):
    """The instance cannot send email: no SMTP server, or a configuration that cannot be used."""


class EmailRateLimitedError(EmailError):
    """The hourly budget of the instance is spent; ``retry_after`` is in seconds."""

    def __init__(self, retry_after: float):
        super().__init__("EMAIL_RATE_LIMITED")
        self.retry_after = retry_after


class EmailDeliveryError(EmailError):
    """The SMTP server did not take the message; ``code`` is a ``SmtpErrorCode`` value."""

    def __init__(self, code: smtp.SmtpErrorCode):
        super().__init__(code.value)


@functools.cache
def _report_invalid(variable: str, problem: str, reason: str) -> None:
    """Log an unusable configuration once per process: email stays off until it is fixed."""
    logger.error("Email configuration cannot be used: email stays off", variable=variable, problem=problem, reason=reason)


def _unusable(variable: str, problem: str, reason: str) -> EmailConfigState:
    _report_invalid(variable, problem, reason)
    return EmailConfigState(configured=True, problem=problem, variable=variable)


def email_config_state() -> EmailConfigState:  # noqa: PLR0911 — one return per state
    """The email configuration as the variables say now. Never raises."""
    try:
        host = smtp_host()
    except EmailConfigError as exc:
        return _unusable(exc.variable, exc.code, str(exc))
    if host is None:
        return EmailConfigState(configured=False)
    try:
        tls = smtp_tls_mode()
        port = smtp_port()
        user = smtp_user()
        password = smtp_password()
        sender = smtp_sender()
        reply_to = smtp_reply_to()
        max_per_hour = smtp_max_per_hour()
        # Not an SMTP variable, but checked with them: a value that cannot be used turns email off, like the others.
        # Only checked here: delivery.address_budget_limit() reads it again at every request.
        signup_emails_per_address()
    except EmailConfigError as exc:
        return _unusable(exc.variable, exc.code, str(exc))
    except SecretFileError as exc:
        return _unusable("LIBREFOLIO_SMTP_PASSWORD_FILE", "SMTP_PASSWORD_UNREADABLE", str(exc))
    if user and not password:
        return _unusable("LIBREFOLIO_SMTP_USER", "SMTP_CREDENTIALS_INCOMPLETE", "LIBREFOLIO_SMTP_USER is set without a password")
    if password and not user:
        return _unusable("LIBREFOLIO_SMTP_PASSWORD", "SMTP_CREDENTIALS_INCOMPLETE", "a password is set without LIBREFOLIO_SMTP_USER")
    if sender is None:
        return _unusable("LIBREFOLIO_SMTP_FROM", "SMTP_FROM_MISSING", "LIBREFOLIO_SMTP_FROM is required with LIBREFOLIO_SMTP_HOST")
    server = smtp.SmtpServer(host=host, port=port, tls=tls, user=user, password=password, timeout=smtp.SMTP_TIMEOUT_SECONDS)
    return EmailConfigState(configured=True, server=server, sender=sender, reply_to=reply_to, max_per_hour=max_per_hour)


def sending_blocked() -> bool:
    """Whether the hosting provider blocks the instance (``LIBREFOLIO_BLOCKED``): then nothing is sent (D-E13). An
    unreadable value counts as blocked: the startup checks stop the server on it, and nothing should go out meanwhile."""
    try:
        return instance_blocked()
    except ValueError:
        return True


def budget_status(max_per_hour: int | None = None) -> RateDecision:
    """What the hourly budget of the instance allows now, without spending it: against ``max_per_hour`` when given (a
    state already read), else against the configured limit."""
    return INSTANCE_BUDGET.peek(limit=max_per_hour if max_per_hour is not None else email_config_state().max_per_hour)


def address_budget_limit() -> int:
    """``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS`` now. A value that cannot be used never raises here: ``email_config_state()``
    has turned email off and reported it, so the default applies if a request gets this far."""
    try:
        return signup_emails_per_address()
    except EmailConfigError:
        return DEFAULT_SIGNUP_EMAILS_PER_ADDRESS


def address_budget_peek(address: str | None) -> RateDecision:
    """What the counter of the client ``address`` allows now, without spending it. Allowed when there is no address (a
    unix socket) or none to count by (behind a proxy nobody trusts): one shared count would let a client block everyone."""
    limit = address_budget_limit()
    key = client_rate_key(address)
    return RateDecision(allowed=True, remaining=limit, retry_after=0.0) if key is None else ADDRESS_BUDGET.peek(key, limit=limit)


def address_budget_hit(address: str | None) -> RateDecision:
    """Spend one unit of the counter of the client ``address`` when it has one left; a refused hit is not recorded.
    Allowed, and counting nothing, when there is no address (see ``address_budget_peek``)."""
    limit = address_budget_limit()
    key = client_rate_key(address)
    return RateDecision(allowed=True, remaining=limit, retry_after=0.0) if key is None else ADDRESS_BUDGET.hit(key, limit=limit)


def longest_wait(*decisions: RateDecision | None) -> float:
    """The seconds until a request refused by some of these counters can pass all of them: the longest ``retry_after``
    among the refusals (``None`` and allowed ones do not count). 0 when none refuses."""
    return max((decision.retry_after for decision in decisions if decision is not None and not decision.allowed), default=0.0)


def instance_budget_peek(state: EmailConfigState) -> RateDecision | None:
    """The hourly budget of the instance against the limit of ``state``, unspent; None when email is not usable."""
    return budget_status(state.max_per_hour) if state.usable else None


#: The two domains of one Gmail mailbox, which ignores the dots of its local part.
_GMAIL_DOMAINS = frozenset({"gmail.com", "googlemail.com"})


def mailbox_budget_key(address: str) -> str:
    """The key of the per-mailbox limits: the aliases of one mailbox give one key.

    Case-folded; the sub-address (``+tag``) cut on every domain, unless nothing would be left before it; for Gmail
    (``googlemail.com`` is ``gmail.com``) the dots of the local part removed. A key to count by, nothing more: the email
    still goes to the address as stored, and the key is never stored, logged nor shown. A value without ``@`` is only
    case-folded.
    """
    value = address.strip().casefold()
    local, at, domain = value.rpartition("@")
    if not at:
        return value
    local = local.split("+", 1)[0] or local
    if domain in _GMAIL_DOMAINS:
        domain = "gmail.com"
        local = local.replace(".", "")
    return f"{local}@{domain}"


def _redacted(detail: str, *, password: str | None, recipient: str) -> str:
    """The server's words for the log, without the SMTP password or the recipient's address, which servers quote back
    in their refusals (``550 <alice@example.com>: Recipient address rejected``): only its domain stays."""
    if password:
        detail = re.sub(re.escape(password), "***", detail, flags=re.IGNORECASE)
    domain = recipient.rpartition("@")[2]
    return re.sub(re.escape(recipient), f"***@{domain}", detail, flags=re.IGNORECASE)


async def send_email(content: EmailContent, *, to: str, user_id: int | None = None) -> None:
    """Send ``content`` to ``to``: one unit of the hourly budget per attempt, SMTP in a worker thread.

    Raises ``EmailUnavailableError`` (nothing spent; ``INSTANCE_BLOCKED`` while the hosting provider blocks the instance),
    ``EmailRecipientError`` (a ``ValueError``) for an address that is not one address (nothing spent),
    ``EmailRateLimitedError`` (budget spent: nothing sent) and ``EmailDeliveryError`` (the server refused).
    """
    # A blocked instance sends nothing (D-E13): its routes are refused already, and this holds for any other caller.
    if sending_blocked():
        raise EmailUnavailableError("INSTANCE_BLOCKED")
    # The configuration may come from a password file: read off the event loop.
    state = await asyncio.to_thread(email_config_state)
    if not state.usable or state.server is None or state.sender is None:
        raise EmailUnavailableError(state.problem or "EMAIL_NOT_CONFIGURED")
    message = compose_message(content, to=to, sender=state.sender, reply_to=state.reply_to)
    domain = to.strip().rpartition("@")[2].lower()
    decision = INSTANCE_BUDGET.hit(limit=state.max_per_hour)
    if not decision.allowed:
        logger.warning("Email not sent: the hourly limit of the instance is reached", kind=content.kind.value, user_id=user_id, recipient_domain=domain, retry_after=round(decision.retry_after))
        raise EmailRateLimitedError(decision.retry_after)
    try:
        await asyncio.to_thread(smtp.deliver, state.server, message)
    except smtp.SmtpDeliveryError as exc:
        logger.warning("Email not sent", kind=content.kind.value, code=exc.code.value, detail=_redacted(exc.detail, password=state.server.password, recipient=to), user_id=user_id, recipient_domain=domain)
        raise EmailDeliveryError(exc.code) from None
    logger.info("Email sent", kind=content.kind.value, language=content.language, user_id=user_id, recipient_domain=domain)
