"""Email section of the configuration: the SMTP server LibreFolio sends its emails through.

Owner: workstream E (email). Read from the process environment only, never from ``.env`` nor from the database: the
SMTP configuration lives only in variables or secret files, is never stored, never shown in the interface and never
part of a backup (F04). The password also accepts ``LIBREFOLIO_SMTP_PASSWORD_FILE`` (``env_secret``).

With ``LIBREFOLIO_SMTP_HOST`` unset or blank, email is off and LibreFolio behaves as before release 1.3: every link
is copied by hand. A value that cannot be used raises ``EmailConfigError``, which names the variable and never holds a
secret; ``services/email/delivery.py`` turns it into an instance with email off, and says why in the log.

One variable of the section is not an SMTP one: ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``, how many registration emails
one client address may send in an hour. It follows the same rules (read at every call, blank is unset, a bad value is an
``EmailConfigError``), but it does not start with ``SMTP_ENV_PREFIX``.
"""

import os
import re
from email.utils import getaddresses

from backend.app.config import env_secret

#: Every variable of this section starts with it, but ``SIGNUP_EMAILS_PER_ADDRESS_VARIABLE``.
SMTP_ENV_PREFIX = "LIBREFOLIO_SMTP_"
#: ``starttls`` upgrades a plain connection and refuses to go on without it; ``tls`` is TLS from the first byte
#: (SMTPS); ``none`` sends in clear, for a relay on the same machine or the local network.
TLS_MODES: tuple[str, ...] = ("starttls", "tls", "none")
DEFAULT_SMTP_PORTS: dict[str, int] = {"starttls": 587, "tls": 465, "none": 25}
DEFAULT_SMTP_MAX_PER_HOUR = 50
#: How many registration emails one client address (an IPv6 one by its /64) may send in an hour, unless the variable says
#: otherwise: past it, the account is still created and waits, but its email is held.
SIGNUP_EMAILS_PER_ADDRESS_VARIABLE = "LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS"
DEFAULT_SIGNUP_EMAILS_PER_ADDRESS = 20

_HOST_PATTERN = re.compile(r"[A-Za-z0-9._:-]+")
_DIGITS = re.compile(r"[0-9]+")


class EmailConfigError(ValueError):
    """A ``LIBREFOLIO_SMTP_*`` value (or ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``) that cannot be used: ``variable`` names it, ``code`` says what is wrong.

    The message names the variable and the rule, never the value of a secret.
    """

    def __init__(self, variable: str, code: str, message: str):
        super().__init__(f"{variable}: {message}")
        self.variable = variable
        self.code = code


def _value(name: str) -> str | None:
    """The variable ``name`` stripped, or None when it is unset or blank."""
    return os.environ.get(name, "").strip() or None


def smtp_host() -> str | None:
    """``LIBREFOLIO_SMTP_HOST``: the SMTP server, a host name or an IP address. None when unset or blank: email off.

    ``name:port`` is refused: the port goes in ``LIBREFOLIO_SMTP_PORT`` (an IPv6 address has more than one colon).
    """
    host = _value("LIBREFOLIO_SMTP_HOST")
    if host is not None and (not _HOST_PATTERN.fullmatch(host) or host.count(":") == 1):
        raise EmailConfigError("LIBREFOLIO_SMTP_HOST", "SMTP_HOST_INVALID", "expected a host name or an IP address, without scheme, user, port or path (the port goes in LIBREFOLIO_SMTP_PORT)")
    return host


def smtp_tls_mode() -> str:
    """``LIBREFOLIO_SMTP_TLS``: ``starttls`` (default), ``tls`` or ``none``, in any case."""
    mode = (_value("LIBREFOLIO_SMTP_TLS") or "starttls").lower()
    if mode not in TLS_MODES:
        raise EmailConfigError("LIBREFOLIO_SMTP_TLS", "SMTP_TLS_INVALID", f"expected one of {', '.join(TLS_MODES)}")
    return mode


def smtp_port() -> int:
    """``LIBREFOLIO_SMTP_PORT``: 1–65535; unset or blank, the port of the TLS mode (587, 465 or 25)."""
    raw = _value("LIBREFOLIO_SMTP_PORT")
    if raw is None:
        return DEFAULT_SMTP_PORTS[smtp_tls_mode()]
    if not _DIGITS.fullmatch(raw) or not 1 <= int(raw) <= 65535:
        raise EmailConfigError("LIBREFOLIO_SMTP_PORT", "SMTP_PORT_INVALID", "expected a whole number from 1 to 65535")
    return int(raw)


def smtp_user() -> str | None:
    """``LIBREFOLIO_SMTP_USER``: the login of the SMTP server; None when unset or blank (no authentication)."""
    return _value("LIBREFOLIO_SMTP_USER")


def smtp_password() -> str | None:
    """``LIBREFOLIO_SMTP_PASSWORD`` as written, or the content of ``LIBREFOLIO_SMTP_PASSWORD_FILE``; None when neither.

    A ``_FILE`` that cannot give its secret raises ``SecretFileError`` (``env_secret``).
    """
    return env_secret("LIBREFOLIO_SMTP_PASSWORD")


def _mailbox(name: str, code: str) -> tuple[str, str] | None:
    """The one mailbox in the variable ``name`` as ``(display name, address)``; None when unset or blank."""
    raw = os.environ.get(name, "")
    if "\r" in raw or "\n" in raw:
        raise EmailConfigError(name, code, "a line break is not allowed")
    value = raw.strip()
    if not value:
        return None
    pairs = getaddresses([value])
    if len(pairs) != 1:
        raise EmailConfigError(name, code, "expected one address, such as LibreFolio <noreply@example.com>")
    display_name, address = pairs[0]
    local, at, domain = address.rpartition("@")
    if not at or not local or not domain or "@" in local or any(char.isspace() for char in address):
        raise EmailConfigError(name, code, "expected one address, such as LibreFolio <noreply@example.com>")
    return display_name.strip(), address


def smtp_sender() -> tuple[str, str] | None:
    """``LIBREFOLIO_SMTP_FROM``: who the emails come from, ``Name <address>`` or ``address``. Required with a host."""
    return _mailbox("LIBREFOLIO_SMTP_FROM", "SMTP_FROM_INVALID")


def smtp_reply_to() -> tuple[str, str] | None:
    """``LIBREFOLIO_SMTP_REPLY_TO``: where a reply goes, when not to the sender; None when unset or blank."""
    return _mailbox("LIBREFOLIO_SMTP_REPLY_TO", "SMTP_REPLY_TO_INVALID")


def smtp_max_per_hour() -> int:
    """``LIBREFOLIO_SMTP_MAX_PER_HOUR``: how many emails the instance may send in an hour; 50 when unset or blank."""
    raw = _value("LIBREFOLIO_SMTP_MAX_PER_HOUR")
    if raw is None:
        return DEFAULT_SMTP_MAX_PER_HOUR
    if not _DIGITS.fullmatch(raw) or int(raw) < 1:
        raise EmailConfigError("LIBREFOLIO_SMTP_MAX_PER_HOUR", "SMTP_MAX_PER_HOUR_INVALID", "expected a whole number of at least 1")
    return int(raw)


def signup_emails_per_address() -> int:
    """``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS``: how many registration emails one client address may send in an hour; 20
    when unset or blank.

    Not an SMTP variable (no ``LIBREFOLIO_SMTP_`` prefix), but validated with them: a value that cannot be used makes
    ``email_config_state()`` report it, and email stays off.
    """
    raw = _value(SIGNUP_EMAILS_PER_ADDRESS_VARIABLE)
    if raw is None:
        return DEFAULT_SIGNUP_EMAILS_PER_ADDRESS
    if not _DIGITS.fullmatch(raw) or int(raw) < 1:
        raise EmailConfigError(SIGNUP_EMAILS_PER_ADDRESS_VARIABLE, "SIGNUP_EMAILS_PER_ADDRESS_INVALID", "expected a whole number of at least 1")
    return int(raw)
