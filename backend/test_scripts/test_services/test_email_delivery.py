"""``backend.app.services.email.smtp`` and ``.delivery``: sending an e-mail, or saying exactly why not (plan phase01Email §3.2, decisions D-E1, D-E2, D-E4, D-E5, lot E1).

``smtp.deliver`` talks to the server with the standard library's ``smtplib``, blocking; ``delivery.send_email`` decides
whether an e-mail may leave — configuration, recipient, hourly budget — and runs ``deliver`` on a worker thread, never
on the event loop. Every SMTP conversation here is with ``FakeSmtpServer`` (``backend/test_scripts/fixtures/email``)
on 127.0.0.1, on a port the OS picks: nothing reaches the network. The contract pinned here:

1. The fake server first: it speaks SMTP to ``smtplib`` — envelope, dot-unstuffing, every form of ``AUTH PLAIN`` and
   ``AUTH LOGIN``, ``530`` before authentication, the refusals it is told to give (a refused recipient quoted in the
   reply, as real servers quote it), its ``QUIT`` code, ``STARTTLS`` only with a context, ``8BITMIME`` and ``SMTPUTF8``
   unless told not to — and it stops without leaving a thread behind. A red here is the fake's, not the
   implementation's.
2. ``smtp``'s vocabulary: ``SMTP_TIMEOUT_SECONDS`` 20.0; ``SmtpErrorCode``, seven codes whose value is their name;
   ``SmtpServer``, frozen, its password out of ``repr``; ``SmtpDeliveryError`` and the ``EmailError`` family.
3. ``deliver``: plain mode delivers, the From address as envelope sender and the To address as recipient; with a user it
   authenticates, a wrong password is ``AUTH_FAILED``; ``starttls`` towards a server that does not offer it, and
   implicit ``tls`` towards a plain one, are ``TLS_FAILED`` with no message and no ``AUTH`` sent — never a fallback to
   plain text; a port that refuses connections is ``CONNECTION_FAILED`` whatever the mode; a server that never greets
   is ``TIMEOUT``;
   ``550`` to ``RCPT`` / ``MAIL`` and ``554`` to ``DATA`` are ``RECIPIENT_REFUSED`` / ``SENDER_REFUSED`` /
   ``SEND_FAILED``; ``str()`` of the error is its code alone, ``detail`` holds the server's text; a ``QUIT`` answered
   with anything but ``221`` after the message was accepted is a success. An address beyond ASCII (RFC 6531) goes out
   through a server that advertises ``SMTPUTF8``, with ``SMTPUTF8 BODY=8BITMIME`` on ``MAIL`` and its ``To`` line in
   UTF-8; towards one that does not, ``smtplib`` refuses it on its own side, before ``MAIL``: ``SEND_FAILED``, nothing
   sent. An all-ASCII address goes with no parameter on ``MAIL``, even towards a server that advertises the extension:
   the client of every other test sends what it sent before. With ``cryptography`` installed (it is not a dependency),
   ``STARTTLS`` succeeds against a certificate the client trusts, before authenticating.
4. ``email_config_state`` never raises: off without a host — whatever else is set —; usable, with the server built
   from the accessors and ``smtp.SMTP_TIMEOUT_SECONDS`` read at call time; or configured with one ``problem`` and the
   ``variable`` at fault, for each fault alone.
5. An invalid configuration is logged once per process per (variable, problem, reason), as an ``error`` naming the
   variable and the problem, never with the password: the same fault read again is not logged again, but a new reason
   for the same problem — the password file now empty where it was missing — is new information, and is logged
   (``delivery._report_invalid``, a ``functools.cache``, emptied around every test).
6. ``INSTANCE_BUDGET`` is a sliding window of an hour, read by ``send_email`` at call time; ``budget_status`` peeks it
   with the configured hourly limit and never counts.
7. ``send_email``: e-mail not usable is ``EmailUnavailableError`` (its problem, or ``EMAIL_NOT_CONFIGURED``) and spends
   nothing; a bad recipient is a ``ValueError`` and spends nothing; a spent budget is ``EmailRateLimitedError`` with the
   limiter's ``retry_after`` and opens no connection, until the window moves on; otherwise one unit is spent and
   ``smtplib`` runs on a worker thread; a failure is ``EmailDeliveryError`` with the SMTP code, the unit still spent.
8. The logs of a send — success, failure, refusal — hold no SMTP password, no link, no token and no body; the success
   is logged with the kind, the recipient's domain and the user id. Nor do they hold the recipient's full address: the
   recipient is a user id or a domain (plan §3.2), and where the server's words quote a refused address, the logged
   ``detail`` masks it as ``***@<domain>``; ``SmtpDeliveryError.detail`` itself stays the server's text, raw. The mask,
   ``delivery._redacted``, is tested on its own too: the password becomes ``***`` and the address ``***@<domain>``, in
   any letter case, and nothing else changes.
9. ``closed_port()``, the fixture's closed port: refused at once, and taken by no ``bind`` without ``SO_REUSEADDR`` until
   the block is left; free again right after.
10. A blocked instance sends nothing (D-E13, lot E3): while ``LIBREFOLIO_BLOCKED`` blocks it — ``1``, ``true``, ``yes``
    or ``on``, in any case, spaces around ignored — or cannot be read, ``send_email`` raises ``EmailUnavailableError``
    with the code ``INSTANCE_BLOCKED`` before anything else: e-mail off, an unusable configuration, a recipient that is
    not one address, the hourly budget spent — the block is what the caller hears, never a ``ValueError`` —; nothing is
    spent and no connection opened. Unset, blank, ``0``, ``false``, ``no`` or ``off``: the e-mail goes out.
    ``sending_blocked()`` says exactly that — true when blocked or unreadable, false otherwise — and never raises: the
    flows ask it before anything else.
11. ``mailbox_budget_key(address)`` (E-9 a) is the key of the three per-mailbox limiters, folding the aliases of one
    mailbox: stripped and case-folded; without an ``@`` as it is; else split at the last ``@``, the local part cut at
    its first ``+`` unless nothing comes before it, ``googlemail.com`` read as ``gmail.com``, and on ``gmail.com`` every
    dot of the local part removed. Dots matter on every other domain, a subdomain or a look-alike of Gmail included, and
    a domain beyond ASCII is case-folded, never IDNA-encoded. Pure, it never raises on a ``str``. Red while it does not
    exist: each test fails naming it.

Pure: no database, no server of the lane, no network beyond 127.0.0.1. An autouse fixture removes every inherited
``LIBREFOLIO_SMTP_*`` and ``LIBREFOLIO_BLOCKED`` (until C-96 lands a lane carries the developer's ``.env``) and each test
sets its own; another
replaces ``delivery.INSTANCE_BUDGET`` with a private limiter on a fake clock; ``smtp.SMTP_TIMEOUT_SECONDS`` is 5 s
here, a bound for a defect that hangs, never a wait. The only real wait is the timeout test: 0.2 s. A refused
connection is held by ``closed_port()`` for the whole test, so no listener started meanwhile can take its port.

Red until ``backend/app/services/email/`` exists: the package does not import.
"""

from __future__ import annotations

import asyncio
import dataclasses
import errno
import ipaddress
import logging
import os
import smtplib
import socket
import ssl
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from enum import StrEnum
from pathlib import Path

import pytest
import structlog
from structlog.testing import capture_logs

from backend.app.config.platform import instance_blocked
from backend.app.services.email import delivery, smtp
from backend.app.services.email.delivery import (
    EmailConfigState,
    EmailDeliveryError,
    EmailError,
    EmailRateLimitedError,
    EmailUnavailableError,
    budget_status,
    email_config_state,
    send_email,
    sending_blocked,
)
from backend.app.services.email.messages import EmailContent, EmailKind
from backend.app.services.email.smtp import SmtpDeliveryError, SmtpErrorCode, SmtpServer, deliver
from backend.app.utils.runtime.rate_window import RateDecision, SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer, closed_port
from backend.test_scripts.test_utils import print_section, print_success

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
HOST = "LIBREFOLIO_SMTP_HOST"
TLS = "LIBREFOLIO_SMTP_TLS"
PORT = "LIBREFOLIO_SMTP_PORT"
USER = "LIBREFOLIO_SMTP_USER"
PASSWORD = "LIBREFOLIO_SMTP_PASSWORD"
PASSWORD_FILE = "LIBREFOLIO_SMTP_PASSWORD_FILE"
FROM = "LIBREFOLIO_SMTP_FROM"
REPLY_TO = "LIBREFOLIO_SMTP_REPLY_TO"
MAX_PER_HOUR = "LIBREFOLIO_SMTP_MAX_PER_HOUR"
#: The hosting provider's block (``config.platform.instance_blocked``): a blocked instance sends nothing.
BLOCKED = "LIBREFOLIO_BLOCKED"

DELIVERY_LOGGER = "backend.app.services.email.delivery"
SMTP_LOGGER = "backend.app.services.email.smtp"
CANARY = "canary: the capture reaches the e-mail delivery's logger"
#: Logged by EMD-037 itself, with ``to=<the recipient>``: what a send that logged ``to`` would write.
ADDRESS_CONTROL = "control: an event that names the recipient, as a send that logged it would"

SMTP_USER_NAME = "mailer"
#: Recognisable: a log line, an error or a repr that holds it would show it.
SMTP_PASSWORD = "c4nary-SMTP-p4ss-never-logged"
SENDER_HEADER = "LibreFolio <noreply@mail.example.org>"
SENDER = ("LibreFolio", "noreply@mail.example.org")
REPLY_TO_HEADER = "LibreFolio Support <support@example.org>"
REPLY_TO_MAILBOX = ("LibreFolio Support", "support@example.org")
#: The recipient's domain differs from the sender's, so that a domain found in a log is the recipient's.
RECIPIENT = "alice@example.com"
REFUSED_RECIPIENT = "refused@example.com"
#: A local part beyond ASCII (RFC 6531), in NFC — ``ä`` and ``ö`` one code point each: ``smtplib`` sends it only to a
#: server that advertises ``SMTPUTF8``.
INTERNATIONAL_RECIPIENT = "zq-sh\u00e4r\u00f6d@example.com"
#: What ``smtplib`` adds after the sender's address on ``MAIL`` for such an address, towards such a server.
SMTPUTF8_MAIL_OPTIONS = ("SMTPUTF8", "BODY=8BITMIME")
TOKEN = "Zm9v_YmFy-0123456789abcdefghijklmnopqrstuv"
LINK = f"https://folio.example.com/reset-password#token={TOKEN}"
#: Built by hand, so that delivery is tested apart from the builders.
CONTENT = EmailContent(
    kind=EmailKind.PASSWORD_RESET,
    language="en",
    subject="Reset your LibreFolio password",
    text=f"Hello alice,\nopen this link to choose a new password:\n{LINK}\nIt expires in 30 minutes.\n",
    html=f'<!DOCTYPE html>\n<html lang="en"><body><p>Hello alice,</p><p><a href="{LINK}">Choose a new password</a></p><p>It expires in 30 minutes.</p></body></html>\n',
)
#: A body line starting with a dot: smtplib doubles it on the wire, the server must undouble it.
DOT_LINE = ".a line that starts with a dot"

#: What the modules ship with, read at import, before any fixture replaces it.
SHIPPED_BUDGET = getattr(delivery, "INSTANCE_BUDGET", None)
SHIPPED_TIMEOUT = getattr(smtp, "SMTP_TIMEOUT_SECONDS", None)

ERROR_CODES = ("CONNECTION_FAILED", "TLS_FAILED", "AUTH_FAILED", "SENDER_REFUSED", "RECIPIENT_REFUSED", "TIMEOUT", "SEND_FAILED")

#: A valid configuration, the base each fault is added to.
BASE = {"host": "smtp.example.com", "from": SENDER_HEADER}
MISSING_FILE = "<a password file that does not exist>"
EMPTY_FILE = "<an empty password file>"
#: One fault each, on top of ``BASE``: the problem ``email_config_state`` reports and the variable it names.
PROBLEMS = [
    pytest.param({"host": "smtp://smtp.example.com"}, "SMTP_HOST_INVALID", HOST, id="host-invalid"),
    pytest.param({"tls": "ssl"}, "SMTP_TLS_INVALID", TLS, id="tls-invalid"),
    pytest.param({"port": "65536"}, "SMTP_PORT_INVALID", PORT, id="port-invalid"),
    pytest.param({"from": None}, "SMTP_FROM_MISSING", FROM, id="from-missing"),
    pytest.param({"from": "   "}, "SMTP_FROM_MISSING", FROM, id="from-blank"),
    pytest.param({"from": "noreply"}, "SMTP_FROM_INVALID", FROM, id="from-invalid"),
    pytest.param({"reply_to": "a@example.com, b@example.com"}, "SMTP_REPLY_TO_INVALID", REPLY_TO, id="reply-to-invalid"),
    pytest.param({"max_per_hour": "0"}, "SMTP_MAX_PER_HOUR_INVALID", MAX_PER_HOUR, id="max-per-hour-invalid"),
    pytest.param({"user": SMTP_USER_NAME, "password_file": MISSING_FILE}, "SMTP_PASSWORD_UNREADABLE", PASSWORD_FILE, id="password-file-missing"),
    pytest.param({"user": SMTP_USER_NAME, "password_file": EMPTY_FILE}, "SMTP_PASSWORD_UNREADABLE", PASSWORD_FILE, id="password-file-empty"),
    pytest.param({"user": SMTP_USER_NAME}, "SMTP_CREDENTIALS_INCOMPLETE", USER, id="user-without-password"),
    pytest.param({"password": SMTP_PASSWORD}, "SMTP_CREDENTIALS_INCOMPLETE", PASSWORD, id="password-without-user"),
]


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_smtp_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` and ``LIBREFOLIO_BLOCKED`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name == BLOCKED:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    """``delivery._report_invalid`` remembers for the whole process what it logged: each test starts, and leaves, with nothing reported."""
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private hourly budget on the fake clock in place of the process's: no test spends, or depends on, the real one."""
    limiter = SlidingWindowLimiter(50, 3600, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


@pytest.fixture(autouse=True)
def _bounded_smtp_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """5 s instead of 20: a defect that hangs fails sooner. No test waits for it."""
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 5.0)


def _configure(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None], tmp_path: Path | None = None) -> None:
    """Set ``LIBREFOLIO_SMTP_<NAME>`` for each ``name: value``, ``None`` leaving it unset; the file markers become files in ``tmp_path``."""
    for name, value in variables.items():
        if value == MISSING_FILE:
            value = str(tmp_path / "no-such-password-file")
        elif value == EMPTY_FILE:
            value = str(tmp_path / "empty-password-file")
            Path(value).write_text("", encoding="utf-8")
        variable = SMTP_PREFIX + name.upper()
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)


def _point_at(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer, **extra: str | None) -> None:
    """E-mail configured to go through ``fake``: its address and port, no TLS on the loopback, this module's sender; ``extra`` on top."""
    _configure(monkeypatch, {"host": fake.host, "port": str(fake.port), "tls": "none", "from": SENDER_HEADER, **extra})


def _server(fake: FakeSmtpServer, **overrides: object) -> SmtpServer:
    """``SmtpServer`` for ``fake``, plain mode and a 5 s bound unless ``overrides`` say otherwise."""
    return SmtpServer(**{"host": fake.host, "port": fake.port, "tls": "none", "timeout": 5.0, **overrides})


def _message(to: str = RECIPIENT) -> EmailMessage:
    """A plain message, its body holding a line that starts with a dot."""
    message = EmailMessage()
    message["Subject"] = "Delivery test"
    message["From"] = SENDER_HEADER
    message["To"] = to
    message.set_content(f"A message for the fake server.\n{DOT_LINE}\n")
    return message


def _delivery_error(server: SmtpServer, to: str = RECIPIENT) -> SmtpDeliveryError:
    """The ``SmtpDeliveryError`` ``deliver`` raises for ``server`` and a message to ``to``; failing if it delivers, or raises anything else."""
    with pytest.raises(SmtpDeliveryError) as caught:
        deliver(server, _message(to))
    return caught.value


def _mailboxes(header: object) -> list[tuple[str, str]]:
    return [(address.display_name, address.addr_spec) for address in header.addresses]


def _lines(text: str) -> str:
    """``text`` without the line-ending differences of a MIME round trip."""
    return text.replace("\r\n", "\n").rstrip("\n")


def _texts(value: object) -> Iterator[str]:
    """Every piece of text in a log event or record, nested containers included: the ``str`` and the ``repr`` of each leaf."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _texts(item)
    elif isinstance(value, list | tuple | set | frozenset):
        for item in value:
            yield from _texts(item)
    else:
        yield str(value)
        yield repr(value)


def _holds(value: object, needle: str) -> bool:
    return any(needle in text for text in _texts(value))


def _names_an_address(value: object, addresses: tuple[str, ...]) -> bool:
    """Whether a log event or record names one of ``addresses``, in any letter case: servers and clients change it."""
    return any(address.casefold() in text.casefold() for text in _texts(value) for address in addresses)


def _open_delivery_logs(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Every record of the e-mail's loggers reaches ``caplog``, at DEBUG: a logging configuration may have disabled them."""
    for name in (DELIVERY_LOGGER, SMTP_LOGGER):
        monkeypatch.setattr(logging.getLogger(name), "disabled", False)
        caplog.set_level(logging.DEBUG, logger=name)
    caplog.set_level(logging.DEBUG)


async def _send_three_outcomes(monkeypatch: pytest.MonkeyPatch) -> FakeSmtpServer:
    """A success to ``RECIPIENT`` (user 42), a failure to ``REFUSED_RECIPIENT`` (user 43), whom the fake refuses and names in its reply, and a refusal of the hourly budget of 2, spent (user 44); the fake, stopped."""
    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD), refuse_recipients={REFUSED_RECIPIENT}) as fake:
        _point_at(monkeypatch, fake, user=SMTP_USER_NAME, password=SMTP_PASSWORD, max_per_hour="2")
        await send_email(CONTENT, to=RECIPIENT, user_id=42)
        with pytest.raises(EmailDeliveryError):
            await send_email(CONTENT, to=REFUSED_RECIPIENT, user_id=43)
        with pytest.raises(EmailRateLimitedError):
            await send_email(CONTENT, to=RECIPIENT, user_id=44)
    return fake


def _tls_material(directory: Path) -> tuple[Path, ssl.SSLContext]:
    """A certificate authority made now, and a server certificate for 127.0.0.1 it signs: the authority's PEM file, and the fake's server context."""
    from cryptography import x509  # noqa: PLC0415 — optional: imported only once importorskip found it
    from cryptography.hazmat.primitives import hashes, serialization  # noqa: PLC0415 — idem
    from cryptography.hazmat.primitives.asymmetric import ec  # noqa: PLC0415 — idem
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID  # noqa: PLC0415 — idem

    def key_usage(*, signs_certificates: bool) -> x509.KeyUsage:
        return x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            key_cert_sign=signs_certificates,
            crl_sign=signs_certificates,
            encipher_only=False,
            decipher_only=False,
        )

    now = datetime.now(UTC)
    authority_key = ec.generate_private_key(ec.SECP256R1())
    authority_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "LibreFolio test authority")])
    authority_key_id = x509.SubjectKeyIdentifier.from_public_key(authority_key.public_key())
    authority = (
        x509.CertificateBuilder()
        .subject_name(authority_name)
        .issuer_name(authority_name)
        .public_key(authority_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(key_usage(signs_certificates=True), critical=True)
        .add_extension(authority_key_id, critical=False)
        .sign(authority_key, hashes.SHA256())
    )
    server_key = ec.generate_private_key(ec.SECP256R1())
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "127.0.0.1")]))
        .issuer_name(authority_name)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(key_usage(signs_certificates=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address("127.0.0.1")), x509.DNSName("localhost")]), critical=False)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_subject_key_identifier(authority_key_id), critical=False)
        .sign(authority_key, hashes.SHA256())
    )
    authority_file, certificate_file, key_file = directory / "authority.pem", directory / "server.pem", directory / "server.key"
    authority_file.write_bytes(authority.public_bytes(serialization.Encoding.PEM))
    certificate_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(server_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=certificate_file, keyfile=key_file)
    return authority_file, context


# =============================================================================
# 1. THE FAKE SERVER
# =============================================================================


def test_the_fake_server_speaks_smtp_to_smtplib() -> None:
    """EMD-001 — contract 1: ``EHLO`` advertises ``AUTH PLAIN LOGIN`` and no ``STARTTLS``; ``NOOP`` and ``RSET`` are 250, anything else 502; a message lands with its envelope, its dot-unstuffed bytes and its parsing; one connection counted; no thread left once stopped."""
    print_section("EMD-001: the fake server and smtplib")

    with FakeSmtpServer() as fake:
        with smtplib.SMTP(fake.host, fake.port, timeout=5) as client:
            client.ehlo()
            features = dict(client.esmtp_features)
            replies = {"NOOP": client.noop()[0], "RSET": client.rset()[0], "VRFY": client.docmd("VRFY", RECIPIENT)[0]}
            client.send_message(_message())

    assert features.get("auth", "").split() == ["PLAIN", "LOGIN"] and "starttls" not in features
    assert replies == {"NOOP": 250, "RSET": 250, "VRFY": 502}
    assert (fake.connections, len(fake.messages)) == (1, 1)
    received = fake.messages[0]
    assert (received.mail_from, received.rcpt_tos, received.user, received.tls) == (SENDER[1], [RECIPIENT], None, False)
    assert received.message["Subject"] == "Delivery test"
    assert DOT_LINE in received.message.get_content()
    assert f"\r\n{DOT_LINE}".encode() in received.data and f"\r\n.{DOT_LINE}".encode() not in received.data
    assert [thread.name for thread in threading.enumerate() if thread.name.startswith(f"fake-smtp-{fake.port}-")] == []
    print_success("EHLO, NOOP, RSET, 502, a message recorded, threads joined")


@pytest.mark.parametrize(("mechanism", "initial_response"), [("PLAIN", True), ("PLAIN", False), ("LOGIN", True), ("LOGIN", False)])
def test_the_fake_server_reads_every_form_of_auth(mechanism: str, initial_response: bool) -> None:
    """EMD-002 — contract 1: with credentials, ``MAIL`` before ``AUTH`` is 530, a wrong password 535, the right one 235 — whether the client sends the initial response or waits for a 334 — and every attempt is recorded."""
    print_section(f"EMD-002: AUTH {mechanism}, initial response {initial_response}")

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        with smtplib.SMTP(fake.host, fake.port, timeout=5) as client:
            client.ehlo()
            before_auth = client.mail(SENDER[1])[0]
            authenticate = getattr(client, f"auth_{mechanism.lower()}")
            client.user, client.password = SMTP_USER_NAME, "wrong-password"
            with pytest.raises(smtplib.SMTPAuthenticationError) as refused:
                client.auth(mechanism, authenticate, initial_response_ok=initial_response)
            client.user, client.password = SMTP_USER_NAME, SMTP_PASSWORD
            accepted = client.auth(mechanism, authenticate, initial_response_ok=initial_response)[0]
            client.send_message(_message())

    assert (before_auth, refused.value.smtp_code, accepted) == (530, 535, 235)
    assert fake.auth_attempts == [(SMTP_USER_NAME, "wrong-password"), (SMTP_USER_NAME, SMTP_PASSWORD)]
    assert [message.user for message in fake.messages] == [SMTP_USER_NAME]
    print_success("530, 535, 235; two attempts recorded")


@pytest.mark.parametrize(
    ("options", "error", "code", "words"),
    [
        pytest.param({"refuse_sender": True}, smtplib.SMTPSenderRefused, 550, "Sender refused by the fake server", id="sender"),
        pytest.param({"refuse_recipients": {RECIPIENT}}, smtplib.SMTPRecipientsRefused, 550, f"<{RECIPIENT}>: Recipient address rejected", id="recipient"),
        pytest.param({"refuse_data": True}, smtplib.SMTPDataError, 554, "Message refused by the fake server", id="data"),
    ],
)
def test_the_fake_server_refuses_on_demand(options: dict, error: type[Exception], code: int, words: str) -> None:
    """EMD-003 — contract 1: ``refuse_sender`` → 550 to ``MAIL``, ``refuse_recipients`` → 550 to ``RCPT`` naming the refused address as Postfix does, ``refuse_data`` → 554 once the data is in; nothing is recorded."""
    print_section(f"EMD-003: refusing {options}")

    with FakeSmtpServer(**options) as fake:
        with smtplib.SMTP(fake.host, fake.port, timeout=5) as client:
            with pytest.raises(error) as refused:
                client.send_message(_message())

    if isinstance(refused.value, smtplib.SMTPRecipientsRefused):
        reply_code, reply_words = refused.value.recipients[RECIPIENT]
    else:
        reply_code, reply_words = refused.value.smtp_code, refused.value.smtp_error
    reply_words = reply_words.decode() if isinstance(reply_words, bytes) else reply_words
    assert reply_code == code
    assert words in reply_words, reply_words
    assert fake.messages == []
    print_success(f"{code} {reply_words!r}, nothing recorded")


def test_the_fake_server_answers_quit_with_its_code_and_offers_starttls_only_with_a_context() -> None:
    """EMD-004 — contract 1: ``quit_code`` is the reply to ``QUIT`` after the message was accepted; ``STARTTLS`` is advertised once the fake holds an ``SSLContext``."""
    print_section("EMD-004: QUIT code and STARTTLS")

    with FakeSmtpServer(quit_code=421) as fake:
        client = smtplib.SMTP(fake.host, fake.port, timeout=5)
        try:
            client.send_message(_message())
            quit_reply = client.quit()[0]
        finally:
            client.close()
    with FakeSmtpServer(tls_context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)) as offering:
        with smtplib.SMTP(offering.host, offering.port, timeout=5) as client:
            client.ehlo()
            offers_starttls = client.has_extn("starttls")

    assert (quit_reply, len(fake.messages)) == (421, 1)
    assert offers_starttls
    print_success("QUIT 421 after a message; STARTTLS offered with a context")


def test_the_fake_server_advertises_smtputf8_and_8bitmime_unless_told_not_to() -> None:
    """EMD-049 — contract 1: ``EHLO`` advertises ``8BITMIME`` and ``SMTPUTF8`` by default, as Postfix does, and neither with ``smtputf8=False``; ``AUTH`` in both answers — the sibling that proves the second answer was read, not merely empty."""
    print_section("EMD-049: 8BITMIME and SMTPUTF8 in the EHLO")

    def advertised(fake: FakeSmtpServer) -> dict[str, bool]:
        with smtplib.SMTP(fake.host, fake.port, timeout=5) as client:
            client.ehlo()
            return {extension: client.has_extn(extension) for extension in ("auth", "8bitmime", "smtputf8")}

    with FakeSmtpServer() as by_default:
        offered_by_default = advertised(by_default)
    with FakeSmtpServer(smtputf8=False) as told_not_to:
        offered_without = advertised(told_not_to)

    assert offered_by_default == {"auth": True, "8bitmime": True, "smtputf8": True}
    assert offered_without == {"auth": True, "8bitmime": False, "smtputf8": False}
    print_success("8BITMIME and SMTPUTF8 by default, neither with smtputf8=False, AUTH in both")


# =============================================================================
# 2. THE VOCABULARY OF smtp AND delivery
# =============================================================================


def test_the_smtp_timeout_is_twenty_seconds() -> None:
    """EMD-005 — contract 2: ``smtp.SMTP_TIMEOUT_SECONDS`` ships as 20.0, a float."""
    print_section("EMD-005: SMTP_TIMEOUT_SECONDS")

    assert isinstance(SHIPPED_TIMEOUT, float) and SHIPPED_TIMEOUT == 20.0
    print_success("20.0 s")


def test_the_smtp_error_codes_are_their_names() -> None:
    """EMD-006 — contract 2: seven codes, a StrEnum whose values are the names — what an API response and a log carry."""
    print_section("EMD-006: SmtpErrorCode")

    assert issubclass(SmtpErrorCode, StrEnum)
    assert {code.name: code.value for code in SmtpErrorCode} == dict(zip(ERROR_CODES, ERROR_CODES, strict=True))
    print_success(", ".join(ERROR_CODES))


def test_smtp_server_is_frozen_and_keeps_its_password_out_of_repr() -> None:
    """EMD-007 — contract 2: host, port, tls, user, password, timeout; no user, no password and 20 s by default; frozen; the password never in ``repr``."""
    print_section("EMD-007: SmtpServer")

    assert [field.name for field in dataclasses.fields(SmtpServer)] == ["host", "port", "tls", "user", "password", "timeout"]
    plain = SmtpServer(host="smtp.example.com", port=587, tls="starttls")
    assert (plain.user, plain.password, plain.timeout) == (None, None, 20.0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        plain.port = 25  # type: ignore[misc]
    secret = SmtpServer(host="smtp.example.com", port=587, tls="starttls", user=SMTP_USER_NAME, password=SMTP_PASSWORD)
    assert SMTP_PASSWORD not in repr(secret)
    print_success("frozen, password out of repr")


def test_the_errors_form_their_families() -> None:
    """EMD-008 — contract 2: ``SmtpDeliveryError`` is an ``Exception``; ``EmailUnavailableError``, ``EmailRateLimitedError`` and ``EmailDeliveryError`` are ``EmailError``, one ``except`` for a caller."""
    print_section("EMD-008: error families")

    assert issubclass(SmtpDeliveryError, Exception)
    assert issubclass(EmailError, Exception)
    assert all(issubclass(error, EmailError) for error in (EmailUnavailableError, EmailRateLimitedError, EmailDeliveryError))
    print_success("SmtpDeliveryError; EmailError ⊃ unavailable, rate limited, delivery")


# =============================================================================
# 3. deliver
# =============================================================================


def test_deliver_sends_in_plain_mode_with_the_envelope_of_the_headers() -> None:
    """EMD-009 — contract 3: ``tls="none"`` delivers; the envelope sender is the From address, the recipient the To address; no ``AUTH`` without a user."""
    print_section("EMD-009: plain delivery")

    with FakeSmtpServer() as fake:
        assert deliver(_server(fake), _message()) is None

    assert len(fake.messages) == 1
    received = fake.messages[0]
    assert (received.mail_from, received.rcpt_tos) == (SENDER[1], [RECIPIENT])
    assert received.message["Subject"] == "Delivery test"
    assert fake.auth_attempts == []
    print_success(f"{SENDER[1]} → {RECIPIENT}")


def test_deliver_authenticates_with_the_user_and_password() -> None:
    """EMD-010 — contract 3: with a user and a password, the server sees exactly those credentials and accepts the message of that user."""
    print_section("EMD-010: authentication")

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        deliver(_server(fake, user=SMTP_USER_NAME, password=SMTP_PASSWORD), _message())

    assert (SMTP_USER_NAME, SMTP_PASSWORD) in fake.auth_attempts
    assert [message.user for message in fake.messages] == [SMTP_USER_NAME]
    print_success("authenticated, delivered")


def test_a_wrong_password_is_auth_failed() -> None:
    """EMD-011 — contract 3: ``AUTH_FAILED``; ``str()`` is the code alone, ``detail`` the server's text; the password tried is in neither; nothing sent."""
    print_section("EMD-011: AUTH_FAILED")

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        error = _delivery_error(_server(fake, user=SMTP_USER_NAME, password="wrong-password"))

    assert error.code == SmtpErrorCode.AUTH_FAILED and isinstance(error.code, SmtpErrorCode)
    assert str(error) == "AUTH_FAILED"
    assert "Authentication credentials invalid" in error.detail
    assert "wrong-password" not in str(error) and "wrong-password" not in error.detail
    assert fake.messages == []
    print_success("AUTH_FAILED")


@pytest.mark.parametrize("tls", ["starttls", "tls"])
def test_tls_that_cannot_be_had_is_tls_failed_and_nothing_goes_in_clear(tls: str) -> None:
    """EMD-012 — contract 3: ``starttls`` towards a server that does not offer it, implicit ``tls`` towards a plain one: ``TLS_FAILED``, and the server got no ``AUTH`` and no message — never a fallback to plain text."""
    print_section(f"EMD-012: {tls} against a plain server")

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        error = _delivery_error(_server(fake, tls=tls, user=SMTP_USER_NAME, password=SMTP_PASSWORD))

    assert error.code == SmtpErrorCode.TLS_FAILED
    assert str(error) == "TLS_FAILED"
    assert (fake.auth_attempts, fake.messages) == ([], [])
    print_success("TLS_FAILED, nothing sent in clear")


@pytest.mark.parametrize("tls", ["none", "starttls", "tls"])
def test_a_closed_port_is_connection_failed(tls: str) -> None:
    """EMD-013 — contract 3: a port that refuses connections — held by ``closed_port()`` for the whole test, so no listener can take it meanwhile — is ``CONNECTION_FAILED`` in every mode: the TLS of an implicit-TLS server never started."""
    print_section(f"EMD-013: closed port, {tls}")

    with closed_port() as port:
        error = _delivery_error(SmtpServer(host="127.0.0.1", port=port, tls=tls, timeout=5.0))

    assert error.code == SmtpErrorCode.CONNECTION_FAILED
    assert str(error) == "CONNECTION_FAILED"
    print_success("CONNECTION_FAILED")


def test_a_server_that_never_greets_is_timeout() -> None:
    """EMD-014 — contract 3: connected and never greeted, ``timeout=0.2`` ends as ``TIMEOUT`` — the one real wait of the e-mail tests, 0.2 s."""
    print_section("EMD-014: TIMEOUT")

    with FakeSmtpServer(greet=False) as fake:
        error = _delivery_error(_server(fake, timeout=0.2))

    assert error.code == SmtpErrorCode.TIMEOUT
    assert str(error) == "TIMEOUT"
    assert fake.messages == []
    print_success("TIMEOUT after 0.2 s")


@pytest.mark.parametrize(
    ("options", "code", "server_text"),
    [
        pytest.param({"refuse_recipients": {RECIPIENT}}, SmtpErrorCode.RECIPIENT_REFUSED, f"<{RECIPIENT}>: Recipient address rejected: refused by the fake server", id="recipient"),
        pytest.param({"refuse_sender": True}, SmtpErrorCode.SENDER_REFUSED, "Sender refused by the fake server", id="sender"),
        pytest.param({"refuse_data": True}, SmtpErrorCode.SEND_FAILED, "Message refused by the fake server", id="data"),
    ],
)
def test_a_refusal_is_named_by_its_step(options: dict, code: SmtpErrorCode, server_text: str) -> None:
    """EMD-015 — contract 3: 550 to ``RCPT`` is ``RECIPIENT_REFUSED``, 550 to ``MAIL`` ``SENDER_REFUSED``, 554 to ``DATA`` ``SEND_FAILED``; the server's text is in ``detail``, not in ``str()`` — raw, the refused recipient quoted in full: masking it is the delivery log's job (EMD-037), not the transport's."""
    print_section(f"EMD-015: {code}")

    with FakeSmtpServer(**options) as fake:
        error = _delivery_error(_server(fake))

    assert error.code == code
    assert str(error) == code.value
    assert server_text in error.detail
    assert fake.messages == []
    print_success(f"{code}: {error.detail!r}")


@pytest.mark.parametrize("quit_code", [421, 554])
def test_a_failed_quit_after_the_message_was_accepted_is_a_success(quit_code: int) -> None:
    """EMD-016 — contract 3: the server took the message, then answered ``QUIT`` with ``quit_code``: ``deliver`` returns normally — the e-mail is sent."""
    print_section(f"EMD-016: QUIT answered {quit_code}")

    with FakeSmtpServer(quit_code=quit_code) as fake:
        assert deliver(_server(fake), _message()) is None

    assert len(fake.messages) == 1
    print_success("sent")


def test_an_address_beyond_ascii_goes_out_with_smtputf8() -> None:
    """EMD-046 — contract 3: ``zq-shäröd@example.com``, a local part beyond ASCII (RFC 6531), through the fake as it comes — it advertises ``SMTPUTF8`` —: one message; the envelope recipient exactly that address, the sender still the From address; ``SMTPUTF8`` and ``BODY=8BITMIME`` after it on ``MAIL``; the ``To`` line in UTF-8.

    The ``To`` line is read in ``data``, not in the parsed ``message``: ``BytesParser`` reads every byte beyond ASCII as a
    surrogate escape, so ``message["To"].addresses`` would hold escapes where ``ä`` and ``ö`` stand, and
    ``email.policy`` documents the header's text as turning them into U+FFFD. The raw bytes also prove that the header
    went as UTF-8 (``smtplib`` serializes with ``utf8=True``), not as an RFC 2047 encoded word.
    """
    print_section("EMD-046: an address beyond ASCII, with SMTPUTF8")

    with FakeSmtpServer() as fake:
        assert deliver(_server(fake), _message(INTERNATIONAL_RECIPIENT)) is None

    assert len(fake.messages) == 1
    received = fake.messages[0]
    assert (received.mail_from, received.rcpt_tos) == (SENDER[1], [INTERNATIONAL_RECIPIENT])
    assert set(SMTPUTF8_MAIL_OPTIONS) <= set(received.mail_options), received.mail_options
    assert f"\r\nTo: {INTERNATIONAL_RECIPIENT}\r\n".encode() in received.data
    print_success(f"{SENDER[1]} → {INTERNATIONAL_RECIPIENT}, MAIL with {' '.join(received.mail_options)}")


def test_an_address_beyond_ascii_towards_a_server_without_smtputf8_is_send_failed() -> None:
    """EMD-047 — contract 3: the same message through ``FakeSmtpServer(smtputf8=False)``, a server without the extension: ``SEND_FAILED``, its ``detail`` naming ``SMTPNotSupportedError`` and ``SMTPUTF8``, and no message. ``smtplib`` refuses on its own side — ``SMTPNotSupportedError``, raised in ``send_message`` once the ``EHLO`` answer lacks ``SMTPUTF8``, before ``MAIL`` is written —: one connection is opened, since it connects and says ``EHLO`` first, and nothing reaches ``MAIL``. The fake never names the extension in its replies: the words in ``detail`` are ``smtplib``'s, not the server's."""
    print_section("EMD-047: an address beyond ASCII, no SMTPUTF8")

    with FakeSmtpServer(smtputf8=False) as fake:
        error = _delivery_error(_server(fake), to=INTERNATIONAL_RECIPIENT)

    assert error.code == SmtpErrorCode.SEND_FAILED
    assert str(error) == "SEND_FAILED"
    assert "SMTPNotSupportedError" in error.detail and "SMTPUTF8" in error.detail, error.detail
    assert (fake.connections, fake.messages) == (1, [])
    print_success(f"SEND_FAILED: {error.detail!r}; one connection, nothing sent")


def test_an_ascii_address_goes_without_smtputf8_even_when_the_server_advertises_it() -> None:
    """EMD-048 — contract 3: through the fake as it comes, which advertises ``SMTPUTF8``, an all-ASCII recipient is delivered with no parameter on ``MAIL``: ``smtplib`` asks for the extension only for an address beyond ASCII, so the client of every other test sends what it sent before the fake advertised it — only the ``EHLO`` answer grew.

    Control first: a message to ``zq-shäröd@example.com`` through the same fake goes with ``SMTPUTF8`` and
    ``BODY=8BITMIME``: the fake advertises the extension and records what follows the address on ``MAIL``. Otherwise an
    empty ``mail_options`` would prove nothing.
    """
    print_section("EMD-048: an ASCII address, no SMTPUTF8")

    with FakeSmtpServer() as fake:
        deliver(_server(fake), _message(INTERNATIONAL_RECIPIENT))
        deliver(_server(fake), _message())

    assert [message.rcpt_tos for message in fake.messages] == [[INTERNATIONAL_RECIPIENT], [RECIPIENT]]
    control, received = fake.messages
    assert set(SMTPUTF8_MAIL_OPTIONS) <= set(control.mail_options), f"control: the message beyond ASCII went with {control.mail_options}"
    assert received.mail_options == ()
    print_success(f"{RECIPIENT}: MAIL with no parameter; the control went with {' '.join(control.mail_options)}")


def test_starttls_upgrades_before_authenticating(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """EMD-017 — contract 3, optional: with ``cryptography`` installed (it is not a dependency: skipped otherwise), a certificate authority made in the test, trusted by the client's default context, signs the fake's certificate for 127.0.0.1; ``starttls`` then delivers, and the session that authenticated and sent the message was the encrypted one."""
    pytest.importorskip("cryptography")
    print_section("EMD-017: STARTTLS")
    authority, server_context = _tls_material(tmp_path)
    default_context = ssl.create_default_context

    def trusting_the_test_authority(*args: object, **kwargs: object) -> ssl.SSLContext:
        context = default_context(*args, **kwargs)
        context.load_verify_locations(cafile=str(authority))
        return context

    monkeypatch.setattr(ssl, "create_default_context", trusting_the_test_authority)
    monkeypatch.setenv("SSL_CERT_FILE", str(authority))
    monkeypatch.delenv("SSL_CERT_DIR", raising=False)

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD), tls_context=server_context) as fake:
        deliver(_server(fake, tls="starttls", user=SMTP_USER_NAME, password=SMTP_PASSWORD), _message())

    assert [(message.tls, message.user) for message in fake.messages] == [(True, SMTP_USER_NAME)]
    assert fake.auth_attempts == [(SMTP_USER_NAME, SMTP_PASSWORD)]
    print_success("upgraded, then authenticated, then sent")


def test_starttls_refuses_a_certificate_it_cannot_verify(tmp_path: Path) -> None:
    """EMD-018 — contract 3, optional like EMD-017: the same fake, its authority trusted by nobody: ``TLS_FAILED``, no ``AUTH`` and no message. The certificate is verified (plan §3.2) — ``smtplib``'s own default for ``starttls()`` and ``SMTP_SSL`` is an unverified context, so EMD-017 alone would also pass without verification."""
    pytest.importorskip("cryptography")
    print_section("EMD-018: STARTTLS with an untrusted certificate")
    _authority, server_context = _tls_material(tmp_path)

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD), tls_context=server_context) as fake:
        error = _delivery_error(_server(fake, tls="starttls", user=SMTP_USER_NAME, password=SMTP_PASSWORD))

    assert error.code == SmtpErrorCode.TLS_FAILED
    assert (fake.auth_attempts, fake.messages) == ([], [])
    print_success("TLS_FAILED, nothing sent")


# =============================================================================
# 4. THE STATE OF THE CONFIGURATION
# =============================================================================


def test_email_config_state_is_a_frozen_dataclass_with_usable() -> None:
    """EMD-019 — contract 4: seven fields in order with their defaults; ``usable`` is configured and without a problem; frozen."""
    print_section("EMD-019: EmailConfigState")

    assert [field.name for field in dataclasses.fields(EmailConfigState)] == ["configured", "problem", "variable", "server", "sender", "reply_to", "max_per_hour"]
    off = EmailConfigState(configured=False)
    assert (off.problem, off.variable, off.server, off.sender, off.reply_to, off.max_per_hour) == (None, None, None, None, None, 50)
    assert (off.usable, EmailConfigState(configured=True, problem="SMTP_TLS_INVALID").usable, EmailConfigState(configured=True).usable) == (False, False, True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        off.configured = True  # type: ignore[misc]
    print_success("frozen, usable = configured and no problem")


@pytest.mark.parametrize("host", [None, "", "   "], ids=["unset", "empty", "blank"])
def test_without_a_host_email_is_off_whatever_else_is_set(monkeypatch: pytest.MonkeyPatch, host: str | None) -> None:
    """EMD-020 — contract 4: no host, no e-mail: ``configured=False`` and no problem, even with invalid values in the other variables — nothing is reported for a feature that is off."""
    print_section(f"EMD-020: host {host!r}")
    _configure(monkeypatch, {"host": host, "tls": "ssl", "port": "0", "from": "not-an-address"})

    with capture_logs() as events:
        state = email_config_state()

    assert (state.configured, state.problem, state.server, state.usable) == (False, None, None, False)
    assert [event for event in events if event.get("log_level") == "error"] == []
    print_success("off, nothing reported")


def test_a_valid_configuration_is_usable(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMD-021 — contract 4: every variable read through its accessor; the server's timeout is ``smtp.SMTP_TIMEOUT_SECONDS`` at the time of the call."""
    print_section("EMD-021: a usable configuration")
    _configure(
        monkeypatch,
        {
            "host": "smtp.example.com",
            "port": "2525",
            "tls": "tls",
            "user": SMTP_USER_NAME,
            "password": SMTP_PASSWORD,
            "from": SENDER_HEADER,
            "reply_to": REPLY_TO_HEADER,
            "max_per_hour": "7",
        },
    )
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 7.5)

    state = email_config_state()

    assert state == EmailConfigState(
        configured=True,
        server=SmtpServer(host="smtp.example.com", port=2525, tls="tls", user=SMTP_USER_NAME, password=SMTP_PASSWORD, timeout=7.5),
        sender=SENDER,
        reply_to=REPLY_TO_MAILBOX,
        max_per_hour=7,
    )
    assert state.usable
    print_success("usable, timeout 7.5 read at call time")


def test_a_minimal_configuration_takes_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMD-022 — contract 4: a host and a sender are enough — ``starttls`` on 587, no authentication, no Reply-To, 50 an hour."""
    print_section("EMD-022: host and sender only")
    _configure(monkeypatch, {"host": "smtp.example.com", "from": SENDER[1]})

    state = email_config_state()

    assert state == EmailConfigState(configured=True, server=SmtpServer(host="smtp.example.com", port=587, tls="starttls", timeout=5.0), sender=("", SENDER[1]))
    print_success("starttls:587, 50 per hour")


@pytest.mark.parametrize(("overrides", "problem", "variable"), PROBLEMS)
def test_each_fault_is_named_alone_with_its_variable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, overrides: dict, problem: str, variable: str) -> None:
    """EMD-023 — contract 4: one fault on a valid configuration is ``configured=True``, no server, the fault's problem and the variable at fault — for credentials, the one present without its partner; for an unreadable password file, ``LIBREFOLIO_SMTP_PASSWORD_FILE``."""
    print_section(f"EMD-023: {problem}")
    _configure(monkeypatch, {**BASE, **overrides}, tmp_path)

    state = email_config_state()

    assert (state.configured, state.problem, state.variable, state.server, state.usable) == (True, problem, variable, None, False)
    print_success(f"{problem} on {variable}")


# =============================================================================
# 5. AN INVALID CONFIGURATION IN THE LOG
# =============================================================================


@pytest.mark.parametrize(("overrides", "problem", "variable"), PROBLEMS)
def test_an_invalid_configuration_is_logged_once_and_never_with_the_password(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, overrides: dict, problem: str, variable: str) -> None:
    """EMD-024 — contract 5: three reads of the same fault log one ``error``, naming the variable and the problem; no event holds the SMTP password, set beside the fault whenever the fault leaves room for it."""
    print_section(f"EMD-024: {problem} in the log")
    credentials = {} if {"user", "password", "password_file"} & set(overrides) else {"user": SMTP_USER_NAME, "password": SMTP_PASSWORD}
    _configure(monkeypatch, {**BASE, **credentials, **overrides}, tmp_path)

    with capture_logs() as events:
        for _ in range(3):
            email_config_state()

    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 1, f"{len(errors)} error events for one fault read three times: {errors}"
    assert _holds(errors[0], variable) and _holds(errors[0], problem), errors[0]
    assert [event for event in events if _holds(event, SMTP_PASSWORD)] == []
    print_success("one error event, no password")


def test_each_problem_is_logged_once_per_process(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMD-025 — contract 5: a TLS fault, then a port fault, then the TLS fault again: two error events — the second TLS fault was already reported by this process."""
    print_section("EMD-025: once per fault")
    _configure(monkeypatch, BASE)

    with capture_logs() as events:
        monkeypatch.setenv(TLS, "ssl")
        for _ in range(3):
            email_config_state()
        monkeypatch.delenv(TLS)
        monkeypatch.setenv(PORT, "0")
        for _ in range(3):
            email_config_state()
        monkeypatch.delenv(PORT)
        monkeypatch.setenv(TLS, "ssl")
        email_config_state()

    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 2, errors
    assert sum(1 for event in errors if _holds(event, TLS) and _holds(event, "SMTP_TLS_INVALID")) == 1
    assert sum(1 for event in errors if _holds(event, PORT) and _holds(event, "SMTP_PORT_INVALID")) == 1
    print_success("two faults, two events")


def test_a_new_reason_for_the_same_problem_is_logged_again(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """EMD-039 — contract 5: ``LIBREFOLIO_SMTP_PASSWORD_FILE`` naming a missing file, then an empty one, then the missing one again is ``SMTP_PASSWORD_UNREADABLE`` all three times, but two error events: the empty file is a new reason, so new information; the missing file read again is not."""
    print_section("EMD-039: once per (variable, problem, reason)")
    missing, empty = tmp_path / "no-such-password-file", tmp_path / "empty-password-file"
    empty.write_text("", encoding="utf-8")
    _configure(monkeypatch, {**BASE, "user": SMTP_USER_NAME})

    states = []
    with capture_logs() as events:
        for password_file in (missing, empty, missing):
            monkeypatch.setenv(PASSWORD_FILE, str(password_file))
            states.append(email_config_state())

    assert [(state.problem, state.variable) for state in states] == [("SMTP_PASSWORD_UNREADABLE", PASSWORD_FILE)] * 3
    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 2, errors
    assert all(_holds(event, PASSWORD_FILE) and _holds(event, "SMTP_PASSWORD_UNREADABLE") for event in errors), errors
    assert errors[0] != errors[1], f"the second error event repeats the first instead of carrying its new reason: {errors}"
    print_success("missing, empty, missing again: three refusals, two error events")


# =============================================================================
# 6. THE BUDGET
# =============================================================================


def test_the_instance_budget_is_an_hourly_sliding_window() -> None:
    """EMD-026 — contract 6: ``delivery.INSTANCE_BUDGET``, as shipped, is a ``SlidingWindowLimiter`` over 3600 s."""
    print_section("EMD-026: INSTANCE_BUDGET")

    assert isinstance(SHIPPED_BUDGET, SlidingWindowLimiter)
    assert SHIPPED_BUDGET.window_seconds == 3600
    print_success("sliding window of an hour")


def test_budget_status_peeks_with_the_configured_limit(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, clock: FakeClock) -> None:
    """EMD-027 — contract 6: ``budget_status`` decides with ``LIBREFOLIO_SMTP_MAX_PER_HOUR`` and never counts; spent, it tells how long until the oldest send leaves the hour."""
    print_section("EMD-027: budget_status")
    _configure(monkeypatch, {**BASE, "max_per_hour": "3"})

    assert budget_status() == RateDecision(True, 3, 0.0)
    budget.hit(limit=3)
    assert budget_status() == RateDecision(True, 2, 0.0)
    assert budget_status() == RateDecision(True, 2, 0.0)
    assert budget.count() == 1
    clock.now = 1_010.0
    budget.hit(limit=3)
    budget.hit(limit=3)
    clock.now = 1_030.0
    assert budget_status() == RateDecision(False, 0, 3_570.0)
    assert budget.count() == 3
    print_success("3, 2, 2, then refused for 3570 s; never counted")


# =============================================================================
# 7. send_email
# =============================================================================


@pytest.mark.asyncio
async def test_send_email_refuses_when_email_is_off(budget: SlidingWindowLimiter) -> None:
    """EMD-028 — contract 7: no host is ``EmailUnavailableError("EMAIL_NOT_CONFIGURED")``, and nothing is spent."""
    print_section("EMD-028: e-mail off")

    with pytest.raises(EmailUnavailableError) as caught:
        await send_email(CONTENT, to=RECIPIENT)

    assert isinstance(caught.value, EmailError)
    assert caught.value.code == "EMAIL_NOT_CONFIGURED"
    assert budget.count() == 0
    print_success("EMAIL_NOT_CONFIGURED, nothing spent")


@pytest.mark.asyncio
async def test_send_email_refuses_an_invalid_configuration_without_connecting(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMD-029 — contract 7: an invalid configuration is ``EmailUnavailableError`` with its problem; the server it names is never contacted and nothing is spent."""
    print_section("EMD-029: invalid configuration")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake, tls="ssl")
        with pytest.raises(EmailUnavailableError) as caught:
            await send_email(CONTENT, to=RECIPIENT)

    assert caught.value.code == "SMTP_TLS_INVALID"
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("SMTP_TLS_INVALID, no connection, nothing spent")


@pytest.mark.asyncio
@pytest.mark.parametrize("to", ["alice@example.com, bob@example.com", "alice@example.com\r\nBcc: eve@example.org", "alice"], ids=["two", "crlf", "no-at"])
async def test_send_email_refuses_a_bad_recipient_before_spending_anything(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, to: str) -> None:
    """EMD-030 — contract 7: ``compose_message`` refuses the recipient with a ``ValueError`` before any budget is spent or any connection opened."""
    print_section(f"EMD-030: to={to!r}")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        with pytest.raises(ValueError):
            await send_email(CONTENT, to=to)

    assert (fake.connections, budget.count()) == (0, 0)
    print_success("ValueError, no connection, nothing spent")


@pytest.mark.asyncio
async def test_send_email_delivers_through_the_configured_server(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMD-031 — contract 7: authenticated with the configured user, the message carries the configured sender and Reply-To, the recipient, the subject and both parts of the content; one unit of budget spent."""
    print_section("EMD-031: send_email delivers")

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        _point_at(monkeypatch, fake, user=SMTP_USER_NAME, password=SMTP_PASSWORD, reply_to=REPLY_TO_HEADER)
        returned = await send_email(CONTENT, to=RECIPIENT, user_id=42)

    assert returned is None
    assert len(fake.messages) == 1
    received = fake.messages[0]
    assert (received.mail_from, received.rcpt_tos, received.user) == (SENDER[1], [RECIPIENT], SMTP_USER_NAME)
    message = received.message
    assert message["Subject"] == CONTENT.subject
    assert _mailboxes(message["From"]) == [SENDER]
    assert _mailboxes(message["To"]) == [("", RECIPIENT)]
    assert _mailboxes(message["Reply-To"]) == [REPLY_TO_MAILBOX]
    assert _lines(message.get_body(preferencelist=("plain",)).get_content()) == _lines(CONTENT.text)
    assert _lines(message.get_body(preferencelist=("html",)).get_content()) == _lines(CONTENT.html)
    assert budget.count() == 1
    print_success("delivered, one unit spent")


@pytest.mark.asyncio
async def test_smtplib_never_runs_on_the_event_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """EMD-032 — contract 7: ``smtplib.SMTP.connect`` (implicit TLS included: ``SMTP_SSL`` inherits it) is called on a thread that is not the loop's and has no running loop — ``deliver`` went through ``asyncio.to_thread``."""
    print_section("EMD-032: off the event loop")
    loop_thread = threading.get_ident()
    calls: list[tuple[int, bool]] = []
    connect = smtplib.SMTP.connect

    def recording_connect(self: smtplib.SMTP, *args: object, **kwargs: object) -> object:
        try:
            asyncio.get_running_loop()
            loop_running = True
        except RuntimeError:
            loop_running = False
        calls.append((threading.get_ident(), loop_running))
        return connect(self, *args, **kwargs)

    monkeypatch.setattr(smtplib.SMTP, "connect", recording_connect)
    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        await send_email(CONTENT, to=RECIPIENT)

    assert calls, "barrier: smtplib.SMTP.connect was never called"
    assert [(thread, running) for thread, running in calls if thread == loop_thread or running] == []
    assert len(fake.messages) == 1
    print_success(f"{len(calls)} connect call(s), none on the loop")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("options", "code"),
    [
        pytest.param({"refuse_recipients": {RECIPIENT}}, "RECIPIENT_REFUSED", id="recipient"),
        pytest.param({"refuse_sender": True}, "SENDER_REFUSED", id="sender"),
        pytest.param({"refuse_data": True}, "SEND_FAILED", id="data"),
    ],
)
async def test_a_failed_delivery_is_an_email_delivery_error_and_still_costs_a_unit(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, options: dict, code: str) -> None:
    """EMD-033 — contract 7: an ``SmtpDeliveryError`` reaches the caller as ``EmailDeliveryError`` with the same code; the attempt spent its unit."""
    print_section(f"EMD-033: {code}")

    with FakeSmtpServer(**options) as fake:
        _point_at(monkeypatch, fake)
        with pytest.raises(EmailDeliveryError) as caught:
            await send_email(CONTENT, to=RECIPIENT)

    assert isinstance(caught.value, EmailError)
    assert caught.value.code == code
    assert fake.messages == []
    assert budget.count() == 1
    print_success(f"EmailDeliveryError({code}), one unit spent")


@pytest.mark.asyncio
async def test_an_unreachable_server_is_connection_failed_and_still_costs_a_unit(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMD-034 — contract 7: a configured port that refuses connections — held by ``closed_port()`` for the whole test — is ``EmailDeliveryError("CONNECTION_FAILED")``, the unit spent."""
    print_section("EMD-034: unreachable server")

    with closed_port() as port:
        _configure(monkeypatch, {"host": "127.0.0.1", "port": str(port), "tls": "none", "from": SENDER_HEADER})
        with pytest.raises(EmailDeliveryError) as caught:
            await send_email(CONTENT, to=RECIPIENT)

    assert caught.value.code == "CONNECTION_FAILED"
    assert budget.count() == 1
    print_success("CONNECTION_FAILED, one unit spent")


@pytest.mark.asyncio
async def test_the_hourly_budget_refuses_without_connecting_then_reopens(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, clock: FakeClock) -> None:
    """EMD-035 — contract 7: with ``LIBREFOLIO_SMTP_MAX_PER_HOUR=2``, sends at 1000 and 1010 pass; at 1030 the third is ``EmailRateLimitedError`` with ``retry_after = 3600 - 30`` and opens no connection; past the hour of the first send, the next one passes."""
    print_section("EMD-035: the hourly budget")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake, max_per_hour="2")
        clock.now = 1_000.0
        await send_email(CONTENT, to=RECIPIENT)
        clock.now = 1_010.0
        await send_email(CONTENT, to=RECIPIENT)
        clock.now = 1_030.0
        with pytest.raises(EmailRateLimitedError) as caught:
            await send_email(CONTENT, to=RECIPIENT)
        connections_when_refused = fake.connections
        clock.now = 1_000.0 + 3_600.0 + 1.0
        await send_email(CONTENT, to=RECIPIENT)

    assert isinstance(caught.value, EmailError)
    assert caught.value.code == "EMAIL_RATE_LIMITED"
    assert caught.value.retry_after == pytest.approx(3_600.0 - 30.0)
    assert connections_when_refused == 2
    assert (fake.connections, len(fake.messages)) == (3, 3)
    print_success("2 sent, the third refused for 3570 s without a connection, the fourth sent an hour later")


# =============================================================================
# 8. THE LOGS OF A SEND
# =============================================================================


@pytest.mark.asyncio
async def test_no_send_logs_the_password_the_link_or_the_body(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """EMD-036 — contract 8: a success (user 42), a failure (a refused recipient) and a refusal (the hourly budget of 2 spent) leave no structlog event and no stdlib record holding the SMTP password, the link, its token, the text or the HTML; the success is logged with ``kind``, the recipient's domain ``example.com`` and ``user_id``.

    Barriers first: a canary logged through the delivery's logger name reaches both captures at DEBUG. Otherwise a
    capture that sees nothing would pass for a sender that logs nothing.
    """
    print_section("EMD-036: the logs of a send")
    _open_delivery_logs(monkeypatch, caplog)

    with capture_logs() as events:
        structlog.get_logger(DELIVERY_LOGGER).debug(CANARY)
        logging.getLogger(DELIVERY_LOGGER).debug(CANARY)
        fake = await _send_three_outcomes(monkeypatch)

    assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the delivery's logger do not reach capture_logs"
    assert any(record.name == DELIVERY_LOGGER and record.getMessage() == CANARY for record in caplog.records), "barrier: stdlib records of the delivery's logger do not reach caplog at DEBUG"
    secrets = {"the SMTP password": SMTP_PASSWORD, "the link": LINK, "the token": TOKEN, "the text": CONTENT.text, "the HTML": CONTENT.html}
    leaked_events = [(label, event) for event in events for label, secret in secrets.items() if _holds(event, secret)]
    leaked_records = [(label, record.name, record.getMessage()) for record in caplog.records for label, secret in secrets.items() if secret in record.getMessage() or _holds(vars(record), secret)]
    assert leaked_events == [], f"structlog events carrying a secret: {leaked_events}"
    assert leaked_records == [], f"stdlib records carrying a secret: {leaked_records}"
    successes = [event for event in events if event.get("kind") == CONTENT.kind and event.get("user_id") == 42 and "example.com" in event.values()]
    assert successes, f"no event of the send to user 42 with kind and the recipient's domain: {events}"
    assert len(fake.messages) == 1
    print_success(f"{len(events)} events and {len(caplog.records)} records checked: no secret; the success logged")


@pytest.mark.asyncio
async def test_no_send_logs_the_full_recipient_address(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """EMD-037 — contract 8: the same success, failure and refusal as EMD-036 leave no structlog event and no stdlib record naming a full recipient address — ``alice@example.com`` nor ``refused@example.com``, in any letter case —: the recipient is a user id or a domain (plan §3.2).

    The failure meets a fake that quotes the refused address in its 550, as real servers do
    (``550 5.1.1 <refused@example.com>: Recipient address rejected: …``), and the server's words are logged as ``detail``:
    there the address must be masked and its domain kept, ``***@example.com``.

    Control and barrier first. An event and a record of the delivery's logger carrying ``to=alice@example.com``, written
    by the test itself as a send that logged ``to`` would write them, are flagged by the scan: otherwise a scan blind to
    an address would pass for a sender that never logs one. And the refused recipient's failure is logged with the
    server's words, the one place the address could come back through: otherwise its absence there would prove nothing.
    """
    print_section("EMD-037: no full recipient address in the logs")
    _open_delivery_logs(monkeypatch, caplog)
    addresses = (RECIPIENT, REFUSED_RECIPIENT)
    masked = f"***@{REFUSED_RECIPIENT.rpartition('@')[2]}"

    with capture_logs() as events:
        structlog.get_logger(DELIVERY_LOGGER).info(ADDRESS_CONTROL, to=RECIPIENT)
        logging.getLogger(DELIVERY_LOGGER).info(ADDRESS_CONTROL, extra={"to": RECIPIENT})
        fake = await _send_three_outcomes(monkeypatch)

    control_events = [event for event in events if event.get("event") == ADDRESS_CONTROL]
    control_records = [record for record in caplog.records if record.name == DELIVERY_LOGGER and record.getMessage() == ADDRESS_CONTROL]
    assert control_events and all(_names_an_address(event, addresses) for event in control_events), "control: the scan does not see the address in a structlog event that carries it"
    assert control_records and all(_names_an_address(vars(record), addresses) for record in control_records), "control: the scan does not see the address in a stdlib record that carries it"
    refused_failures = [event for event in events if event.get("user_id") == 43 and "detail" in event]
    assert refused_failures, f"barrier: the refused recipient's failure (user 43) is not logged with the server's words: {events}"
    assert all(masked.casefold() in str(event["detail"]).casefold() for event in refused_failures), f"the logged detail does not keep the domain as {masked}: {refused_failures}"
    leaked_events = [event for event in events if event.get("event") != ADDRESS_CONTROL and _names_an_address(event, addresses)]
    leaked_records = [(record.name, record.levelname, record.getMessage()) for record in caplog.records if record.getMessage() != ADDRESS_CONTROL and (_names_an_address(record.getMessage(), addresses) or _names_an_address(vars(record), addresses))]
    assert leaked_events == [], f"structlog events naming a full recipient address: {leaked_events}"
    assert leaked_records == [], f"stdlib records naming a full recipient address: {leaked_records}"
    assert len(fake.messages) == 1
    print_success(f"{len(events)} events and {len(caplog.records)} records checked: no full address, the refused one logged as {masked}, the control seen")


def test_redacted_masks_the_password_and_the_address_in_any_case_and_nothing_else() -> None:
    """EMD-040 — contract 8: ``delivery._redacted``, the mask of the logged ``detail``, on its own. The SMTP password becomes ``***`` and every quote of the recipient's address ``***@<its domain>``, whatever their letter case in the server's words (``ALICE@Example.COM`` for ``alice@example.com``), and a password full of regular-expression characters is taken literally. The domain alone (``mx.example.com``) and the rest of the text are untouched; with ``password=None`` only the address is masked."""
    print_section("EMD-040: delivery._redacted")
    password = "Tr0ub4dor&3.(x)+[y]?"
    detail = "535 5.7.8 Authentication failed for tR0UB4DOR&3.(X)+[Y]? — 550 5.1.1 <ALICE@Example.COM>: Recipient address rejected (alice@EXAMPLE.com unknown) by mx.example.com"
    # The precondition, verified: the server's words quote both in another letter case, or this tests nothing about case.
    assert password not in detail and password.swapcase() in detail
    assert RECIPIENT not in detail and RECIPIENT.casefold() in detail.casefold()

    assert delivery._redacted(detail, password=password, recipient=RECIPIENT) == ("535 5.7.8 Authentication failed for *** — 550 5.1.1 <***@example.com>: Recipient address rejected (***@example.com unknown) by mx.example.com")
    assert delivery._redacted(detail, password=None, recipient=RECIPIENT) == ("535 5.7.8 Authentication failed for tR0UB4DOR&3.(X)+[Y]? — 550 5.1.1 <***@example.com>: Recipient address rejected (***@example.com unknown) by mx.example.com")
    print_success("password → ***, address → ***@example.com, in any case; the domain alone and the rest untouched")


# =============================================================================
# 9. THE CLOSED PORT
# =============================================================================


def test_closed_port_refuses_holds_and_releases_its_port() -> None:
    """EMD-038 — contract 9: inside the block, a connection to the port is refused at once, and a ``bind`` of the same address without ``SO_REUSEADDR`` fails with ``EADDRINUSE``: the port is held, so a listener started meanwhile cannot take it; once the block is left, the same ``bind`` succeeds at once — the holder is closed, not left in ``TIME_WAIT``."""
    print_section("EMD-038: closed_port")

    with closed_port() as port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(5.0)
            with pytest.raises(ConnectionRefusedError):
                client.connect(("127.0.0.1", port))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as intruder:
            with pytest.raises(OSError) as taken:
                intruder.bind(("127.0.0.1", port))
        assert taken.value.errno == errno.EADDRINUSE, taken.value
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as successor:
        successor.bind(("127.0.0.1", port))
    print_success(f"port {port}: refused, held, then released")


# =============================================================================
# 10. A BLOCKED INSTANCE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["1", "true", " YES ", "On"])
async def test_a_blocked_instance_sends_nothing(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, value: str) -> None:
    """EMD-041 — contract 10: e-mail ready towards a running fake, ``LIBREFOLIO_BLOCKED`` set to ``value``: ``send_email`` raises ``EmailUnavailableError`` — an ``EmailError`` — with the code ``INSTANCE_BLOCKED``; the fake accepted no connection and nothing was spent."""
    print_section(f"EMD-041: LIBREFOLIO_BLOCKED={value!r}")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        monkeypatch.setenv(BLOCKED, value)
        with pytest.raises(EmailUnavailableError) as caught:
            await send_email(CONTENT, to=RECIPIENT)

    assert isinstance(caught.value, EmailError) and caught.value.code == "INSTANCE_BLOCKED", caught.value
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("INSTANCE_BLOCKED, no connection, nothing spent")


@pytest.mark.asyncio
@pytest.mark.parametrize("also", ["email-off", "configuration-invalid", "recipient-not-one-address", "budget-spent"])
async def test_the_block_is_refused_before_anything_else(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, also: str) -> None:
    """EMD-042 — contract 10: blocked and, besides, e-mail off, an invalid configuration, a recipient that is not one address, or the hourly budget spent: still ``INSTANCE_BLOCKED`` — not ``EMAIL_NOT_CONFIGURED``, ``SMTP_TLS_INVALID``, a ``ValueError`` nor ``EMAIL_RATE_LIMITED`` —: the block is checked first. Nothing more spent, no connection."""
    print_section(f"EMD-042: blocked, and {also}")
    monkeypatch.setenv(BLOCKED, "1")
    to = "alice@example.com, bob@example.com" if also == "recipient-not-one-address" else RECIPIENT

    with FakeSmtpServer() as fake:
        if also != "email-off":
            _point_at(monkeypatch, fake, tls="ssl" if also == "configuration-invalid" else "none", max_per_hour="1")
        if also == "budget-spent":
            assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
        spent = budget.count()
        with pytest.raises(EmailUnavailableError) as caught:
            await send_email(CONTENT, to=to)

    assert caught.value.code == "INSTANCE_BLOCKED", caught.value
    assert (fake.connections, budget.count()) == (0, spent)
    print_success(f"INSTANCE_BLOCKED before {also}")


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["maybe", "2", "blocked"])
async def test_a_block_that_cannot_be_read_counts_as_blocked(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, value: str) -> None:
    """EMD-043 — contract 10: ``LIBREFOLIO_BLOCKED`` that cannot be read — ``instance_blocked()`` raises ``ValueError`` on it, the precondition —: ``send_email`` raises ``EmailUnavailableError("INSTANCE_BLOCKED")``, never that ``ValueError``, which a caller would take for a bad recipient; nothing spent, no connection."""
    print_section(f"EMD-043: LIBREFOLIO_BLOCKED={value!r}")
    monkeypatch.setenv(BLOCKED, value)
    with pytest.raises(ValueError):
        instance_blocked()

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        with pytest.raises(EmailUnavailableError) as caught:
            await send_email(CONTENT, to=RECIPIENT)

    assert caught.value.code == "INSTANCE_BLOCKED", caught.value
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("unreadable: INSTANCE_BLOCKED, nothing sent")


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "", "   ", "0", "false", "No", " off "], ids=["unset", "empty", "blank", "0", "false", "No", "off-with-spaces"])
async def test_an_instance_that_is_not_blocked_sends(monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, value: str | None) -> None:
    """EMD-044 — contract 10: ``LIBREFOLIO_BLOCKED`` unset, empty, blank, ``0``, ``false``, ``No`` or `` off ``: the e-mail goes out — one message to the recipient, one unit spent."""
    print_section(f"EMD-044: LIBREFOLIO_BLOCKED={value!r}")
    if value is not None:
        monkeypatch.setenv(BLOCKED, value)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        await send_email(CONTENT, to=RECIPIENT)

    assert ([message.rcpt_tos for message in fake.messages], budget.count()) == ([[RECIPIENT]], 1)
    print_success("not blocked: sent")


@pytest.mark.parametrize(
    ("value", "blocked"),
    [
        pytest.param(None, False, id="unset"),
        pytest.param("   ", False, id="blank"),
        pytest.param("0", False, id="0"),
        pytest.param(" Off ", False, id="off"),
        pytest.param("1", True, id="1"),
        pytest.param(" YES ", True, id="yes"),
        pytest.param("maybe", True, id="unreadable"),
    ],
)
def test_sending_blocked_is_true_when_blocked_or_unreadable_and_never_raises(monkeypatch: pytest.MonkeyPatch, value: str | None, blocked: bool) -> None:
    """EMD-045 — contract 10: ``sending_blocked()`` — what every flow asks first — is ``True`` for a value that blocks and for one that cannot be read, ``False`` when unset, blank or a value that does not block; it never raises, not even where ``instance_blocked()`` would."""
    print_section(f"EMD-045: sending_blocked() with LIBREFOLIO_BLOCKED={value!r}")
    if value is not None:
        monkeypatch.setenv(BLOCKED, value)

    answer = sending_blocked()

    assert answer is blocked, f"sending_blocked() is {answer!r} for {value!r}"
    print_success(f"{answer}")


# =============================================================================
# 11. THE KEY OF A MAILBOX'S BUDGET (E-9 a)
# =============================================================================

#: An address and the key ``mailbox_budget_key`` gives it: the aliases of one mailbox fold into one key.
MAILBOX_BUDGET_KEYS = [
    pytest.param("Victim.Name+News@GoogleMail.com", "victimname@gmail.com", id="googlemail-dots-tag-and-case"),
    pytest.param("victim@gmail.com", "victim@gmail.com", id="gmail-as-it-is"),
    pytest.param("v.i.c.t.i.m@gmail.com", "victim@gmail.com", id="gmail-every-dot-removed"),
    pytest.param("victim+1@gmail.com", "victim@gmail.com", id="gmail-tag-cut"),
    pytest.param("zq.victim+2@googlemail.com", "zqvictim@gmail.com", id="googlemail-is-gmail"),
    pytest.param("zq-victim+a+b@outlook.com", "zq-victim@outlook.com", id="cut-at-the-first-plus"),
    pytest.param("first.last@outlook.com", "first.last@outlook.com", id="dots-matter-outside-gmail"),
    pytest.param("first.last+x@example.org", "first.last@example.org", id="tag-cut-on-any-domain-dots-kept"),
    pytest.param("+tag@example.org", "+tag@example.org", id="an-empty-base-keeps-its-tag"),
    pytest.param("  Alice@Example.COM  ", "alice@example.com", id="stripped-and-case-folded"),
    pytest.param("a.b@mail.gmail.com", "a.b@mail.gmail.com", id="a-subdomain-of-gmail-is-not-gmail"),
    pytest.param("a.b@notgmail.com", "a.b@notgmail.com", id="a-look-alike-of-gmail-is-not-gmail"),
    pytest.param("user@B\u00fccher.de", "user@b\u00fccher.de", id="case-folded-never-idna"),
    pytest.param("not-an-address", "not-an-address", id="no-at-sign-as-it-is"),
    pytest.param("", "", id="empty"),
]


def _budget_key(address: str) -> str:
    """``delivery.mailbox_budget_key(address)``; fails, naming it, while the function does not exist."""
    function = getattr(delivery, "mailbox_budget_key", None)
    if function is None:
        pytest.fail("delivery.mailbox_budget_key does not exist: the per-mailbox limiters still give every alias of a mailbox a budget of its own (E-9 a)")
    return function(address)


@pytest.mark.parametrize(("address", "key"), MAILBOX_BUDGET_KEYS)
def test_mailbox_budget_key_folds_the_aliases_of_a_mailbox(address: str, key: str) -> None:
    """EMD-050 — contract 11: ``mailbox_budget_key(address)`` is ``key``, a ``str``: the ``+tag`` cut on every domain unless nothing comes before it, the dots of a ``gmail.com`` local part removed, ``googlemail.com`` read as ``gmail.com``, the address stripped and case-folded; dots kept everywhere else — on a subdomain or a look-alike of Gmail too —, a domain beyond ASCII case-folded and not IDNA-encoded, a value without an ``@`` as it is."""
    print_section(f"EMD-050: mailbox_budget_key({address!r})")

    folded = _budget_key(address)

    assert isinstance(folded, str) and folded == key, f"mailbox_budget_key({address!r}) is {folded!r}, not {key!r}"
    print_success(f"→ {key!r}")


def test_aliases_of_one_mailbox_share_a_key_and_two_mailboxes_do_not() -> None:
    """EMD-051 — contract 11: the table's three ways of writing one Gmail mailbox — ``victim@gmail.com``, ``v.i.c.t.i.m@gmail.com``, ``victim+1@gmail.com`` — share one key, so one budget; ``zq.a@outlook.com`` and ``zqa@outlook.com``, two mailboxes outside Gmail, apart in a dot alone, have two."""
    print_section("EMD-051: one mailbox, one key; two mailboxes, two keys")

    aliases = {address: _budget_key(address) for address in ("victim@gmail.com", "v.i.c.t.i.m@gmail.com", "victim+1@gmail.com")}

    assert len(set(aliases.values())) == 1, f"three aliases of one mailbox, three budgets: {aliases}"
    assert _budget_key("zq.a@outlook.com") != _budget_key("zqa@outlook.com"), "outside Gmail a dot is part of the mailbox: zq.a@ and zqa@outlook.com must keep two budgets"
    print_success(f"one key {set(aliases.values())}; zq.a@ and zqa@outlook.com apart")
