"""SMTP transport: one message to one server, with the standard library, in the calling thread.

``deliver`` blocks (``smtplib`` is synchronous): call it through ``asyncio.to_thread`` — ``delivery.send_email``
does. The server's certificate is verified with the default TLS context. In ``starttls`` mode the connection is
upgraded before anything else is sent, and a server that does not offer STARTTLS is refused: the message never goes
out in clear by accident. A failure is a ``SmtpDeliveryError``: a code for the interface, and in ``detail`` the
server's own words, raw, for the log only — ``delivery`` masks the password and the recipient's address before it
logs them.
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from enum import StrEnum

#: Seconds allowed to connect and for each exchange with the server; read at call time by ``delivery``.
SMTP_TIMEOUT_SECONDS: float = 20.0


class SmtpErrorCode(StrEnum):
    """Why a message did not go out, in words an administrator can act on."""

    CONNECTION_FAILED = "CONNECTION_FAILED"
    TLS_FAILED = "TLS_FAILED"
    AUTH_FAILED = "AUTH_FAILED"
    SENDER_REFUSED = "SENDER_REFUSED"
    RECIPIENT_REFUSED = "RECIPIENT_REFUSED"
    TIMEOUT = "TIMEOUT"
    SEND_FAILED = "SEND_FAILED"


@dataclass(frozen=True)
class SmtpServer:
    """Where and how to send: ``tls`` is ``starttls``, ``tls`` or ``none``. The password stays out of ``repr``."""

    host: str
    port: int
    tls: str
    user: str | None = None
    password: str | None = field(default=None, repr=False)
    timeout: float = SMTP_TIMEOUT_SECONDS


class SmtpDeliveryError(Exception):
    """A message that did not go out: ``code`` for the interface, ``detail`` (the server's words) for the log."""

    def __init__(self, code: SmtpErrorCode, detail: str = ""):
        super().__init__(code.value)
        self.code = code
        self.detail = detail

    def __str__(self) -> str:
        return self.code.value


def _server_words(exc: BaseException) -> str:
    """What the server or the socket said, as text, for the log."""
    if isinstance(exc, smtplib.SMTPResponseException):
        message = exc.smtp_error.decode("utf-8", "replace") if isinstance(exc.smtp_error, bytes) else str(exc.smtp_error)
        return f"{exc.smtp_code} {message}"
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "; ".join(f"{code} {reply.decode('utf-8', 'replace') if isinstance(reply, bytes) else reply}" for code, reply in exc.recipients.values())
    return f"{type(exc).__name__}: {exc}"


# The code of a protocol failure depends on the step it happened in.
_STEP_CODES: dict[str, SmtpErrorCode] = {
    "connect": SmtpErrorCode.CONNECTION_FAILED,
    "tls": SmtpErrorCode.TLS_FAILED,
    "auth": SmtpErrorCode.AUTH_FAILED,
    "send": SmtpErrorCode.SEND_FAILED,
}


def _timed_out(exc: BaseException) -> bool:
    """Whether a timeout is behind ``exc``: ``smtplib`` turns a read that timed out into ``SMTPServerDisconnected``."""
    seen: BaseException | None = exc
    for _ in range(8):
        if seen is None:
            return False
        if isinstance(seen, TimeoutError):
            return True
        seen = seen.__cause__ or seen.__context__
    return False


def _classify(exc: BaseException, step: str) -> SmtpErrorCode:  # noqa: PLR0911 — one answer per kind of failure
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return SmtpErrorCode.AUTH_FAILED
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return SmtpErrorCode.SENDER_REFUSED
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return SmtpErrorCode.RECIPIENT_REFUSED
    if isinstance(exc, ssl.SSLError):
        return SmtpErrorCode.TLS_FAILED
    if _timed_out(exc):
        return SmtpErrorCode.TIMEOUT
    if isinstance(exc, smtplib.SMTPException):
        return _STEP_CODES[step]
    return SmtpErrorCode.TLS_FAILED if step == "tls" else SmtpErrorCode.CONNECTION_FAILED


def deliver(server: SmtpServer, message: EmailMessage) -> None:
    """Send ``message`` through ``server``, blocking. Raises ``SmtpDeliveryError``; returns once the server accepted it.

    A failure after the server accepted the message (a ``QUIT`` answered badly, a dropped connection) is not a
    failure of the delivery.
    """
    context = ssl.create_default_context()
    step = "connect"
    client: smtplib.SMTP | None = None
    try:
        if server.tls == "tls":
            client = smtplib.SMTP_SSL(server.host, server.port, timeout=server.timeout, context=context)
        else:
            client = smtplib.SMTP(server.host, server.port, timeout=server.timeout)
        client.ehlo()
        if server.tls == "starttls":
            step = "tls"
            client.starttls(context=context)
            client.ehlo()
        if server.user:
            step = "auth"
            client.login(server.user, server.password or "")
        step = "send"
        client.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        if client is not None:
            client.close()
        raise SmtpDeliveryError(_classify(exc, step), _server_words(exc)) from None
    try:
        client.quit()
    except (smtplib.SMTPException, OSError):
        client.close()
