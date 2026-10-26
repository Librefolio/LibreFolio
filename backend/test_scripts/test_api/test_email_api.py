"""Email administration API — ``GET /email/status``, ``POST /email/test``, ``POST /email/links`` and ``POST /email/password-reset`` (plan phase01Email §3.3, §3.4, decisions D-E4, D-E5, D-E9, developer decision 45, lots E2a, E2b, E3).

An administrator sees whether the instance's email is off, ready or unusable — never its configuration —, sends a
test email to their own address, and emails the invitation or password-reset link they have just created; anyone can
ask for a password-reset link for an account they name. The routes are in ``backend/app/api/v1/email.py``, the schemas
in ``schemas/email.py``. The contract pinned here:

1. Admin only: the status and the test email answer 401 without a session and 403 to a signed-in account that is not
   an administrator, and then send nothing and spend nothing; an administrator gets 200 from both.
2. ``GET /email/status`` answers ``{state, problem, variable, checks, budget, links}``, each check ``{check_id,
   severity, i18n_key, detail}`` — the three of ``EMAIL_CONFIG_CHECKS``, never their log summary:
   - off (no host, whatever else is set): ``state="off"``, no problem, no variable, no budget; ``email.smtp`` ok
     ``email.checks.smtp.off``, ``email.smtp_encryption`` ok ``email.checks.smtpEncryption.ok``, ``email.links`` ok;
   - invalid: ``state="invalid"``, the problem and the variable at fault, no budget; ``email.smtp`` error
     ``email.checks.smtp.invalid`` with ``detail == {problem, variable}``, the encryption and links checks ok;
   - ready: ``state="ready"``, no problem, no variable; ``email.smtp`` ok ``email.checks.smtp.ok``; the encryption check
     ok — ``localPlain`` for plain text to the loopback —, or a ``warning`` ``email.checks.smtpEncryption.plain`` with an
     empty detail for plain text to a host outside the local network;
   - ``links`` ``{ready, base, problem}``: ``LIBREFOLIO_PUBLIC_URL`` as read now, whatever the state of email — ready
     with the base (one trailing slash removed), else no base and ``PUBLIC_URL_MISSING`` (unset or blank) or
     ``PUBLIC_URL_INVALID`` (not http(s), or an http(s) address no link can start from: no host, a space inside, a
     query, a fragment), the value itself never echoed; ``email.links`` ok when email is not usable or the links are
     ready, else ``info`` ``email.checks.links.missing`` or ``warning`` ``email.checks.links.invalid``, with an empty
     detail;
   - the budget, when ready: ``{max_per_hour, remaining, retry_after_seconds}`` — the configured limit, one unit less
     after each test email, 0 seconds while one fits; spent, 0 remaining and ``ceil(3600 - elapsed)`` seconds, a whole
     number never rounded down; whole again an hour after the send;
   - the status opens no connection and resolves no name;
   - its JSON never holds the host, the port, the user, the sender, the Reply-To, the password nor the path of a password
     file, in any state.
3. ``POST /email/test``, one unit of the hourly budget:
   - ready: 200 ``{language, message}``; one message reached the server, to the administrator's own address, from the
     configured sender, its subject and text the test email of the administrator's language — their own
     ``user_settings.language`` when it names one of the four (a regional form: ``it-IT`` is ``it``), else the
     instance's ``default_language`` (an own ``de`` counts as unset) —, naming the administrator and the instance: the
     host the request was sent to, as written (``request.url.netloc``, port included);
   - a settings row whose theme this version does not know (outside light/dark/auto), which the schema
     ``UserSettingsRead`` refuses, still gives its language: 200, not 422;
   - off or unusable: 409 ``{error_code: EMAIL_UNAVAILABLE, problem}`` (``EMAIL_NOT_CONFIGURED`` or the problem of the
     configuration); no connection, nothing spent;
   - the hourly budget spent: 429 ``{error_code: EMAIL_RATE_LIMITED, retry_after}``, a whole number of seconds ≥ 1, the
     same in ``Retry-After``; no connection;
   - the server refused: 502 ``{error_code: EMAIL_DELIVERY_FAILED, smtp_code}`` — ``RECIPIENT_REFUSED``,
     ``AUTH_FAILED``, ``CONNECTION_FAILED``, ``SENDER_REFUSED``, ``SEND_FAILED``, ``TLS_FAILED`` —, the unit spent;
   - an administrator whose address is not one address: 422 ``EMAIL_RECIPIENT_INVALID`` — what the flow raised is an
     ``EmailRecipientError``, a ``ValueError`` —; no connection, nothing spent. Only that error is the 422: any other
     error of the flow, a plain ``ValueError`` or a pydantic ``ValidationError`` included, is an unhandled 500 (the
     backend installs no exception handler);
   - no answer holds the SMTP password, the host, the user, the sender nor the server's own words.
4. Both routes read the configuration — and the file of ``LIBREFOLIO_SMTP_PASSWORD_FILE`` — off the event loop: the
   status is a plain ``def`` (FastAPI's thread pool), ``send_email`` reads it through ``asyncio.to_thread``.
5. ``GET /system/instance`` carries ``email: {available, links}``, public — no session —: ``available`` true exactly
   when the configuration can be used (a host set and every variable usable, plain text to a public host included),
   false when email is off, invalid (a bad port, a bad host), its password file cannot be read or the instance is
   blocked (``LIBREFOLIO_BLOCKED`` blocking, or unreadable: nothing can be sent, so nothing is offered); ``links`` true
   exactly when ``available`` is and ``LIBREFOLIO_PUBLIC_URL`` is an http(s) address a link can start from. It never
   holds the host, the port, the user, the sender, the Reply-To, the password, the path of a password file nor
   ``LIBREFOLIO_PUBLIC_URL`` itself, resolves no name, never contacts the server, and reads the configuration — the
   password file included — off the event loop (``asyncio.to_thread``). An answer built without ``email`` serializes
   ``{"available": false, "links": false}``, and the OpenAPI does not require it.
6. ``POST /email/links`` ``{purpose, token, to?, language?}``, admin only (401, 403; nothing sent): the link of a token
   an administrator has just created, built from ``LIBREFOLIO_PUBLIC_URL`` alone — ``{base}/invite#token=…`` or
   ``{base}/reset-password#token=…`` —, never from the request: its ``Host``, ``Origin``, ``X-Forwarded-Host`` or
   ``Referer`` never reach the email. Checked in this order, each refusal before anything is sent or spent: email
   usable (409 ``EMAIL_UNAVAILABLE`` with the ``problem``), links ready (409 ``EMAIL_LINKS_UNAVAILABLE`` with the
   ``problem``), the token a live link of that purpose (409 ``EMAIL_LINK_INVALID`` with its ``status``: ``expired``,
   ``consumed``, ``revoked``, ``unknown`` — a token of the other purpose is ``unknown``), the recipient: an invitation
   goes to ``to``, else to the address written in it (neither: 422 ``EMAIL_RECIPIENT_REQUIRED``; not one address: 422
   ``EMAIL_RECIPIENT_INVALID``), in ``language`` else the instance's ``default_language``, with the administrator's role
   sentence when it grants the role; a reset link goes only to its account's address (any ``to``: 422
   ``EMAIL_RECIPIENT_NOT_ALLOWED``), in the account's language, and never for an inactive account (409
   ``EMAIL_ACCOUNT_INACTIVE``: it would set a password nobody can use yet). 200 ``{purpose, to, language}``; the email
   is exactly the builder's for that language, link and instance (the host of ``LIBREFOLIO_PUBLIC_URL``, with its
   port); the token stays live and never reaches the logs; a spent budget is 429 with ``Retry-After``, a refusal of the
   server 502. On a blocked instance (``LIBREFOLIO_BLOCKED``) sending itself refuses — the test email and a link alike
   —: 409 ``EMAIL_UNAVAILABLE`` with ``INSTANCE_BLOCKED``, nothing sent or spent, the link still live.
7. ``POST /email/password-reset`` ``{identifier}``, no session, ships open (lot E4 removed the hold and its 409
   ``FORGOT_PASSWORD_DISABLED`` once changing an account's email asked for the current password): 409
   ``EMAIL_UNAVAILABLE`` or ``EMAIL_LINKS_UNAVAILABLE``
   — no ``problem``, the configuration is not a stranger's business — when the instance cannot send such an email (a
   blocked instance included, should the request get past the guard of ``/api/v1``: refused at the admission, nothing
   counted); 429 ``EMAIL_RATE_LIMITED`` with ``Retry-After`` past 10 requests per client address in 15 minutes (the
   address the server sees: a forged ``X-Forwarded-For`` does not move it; an IPv6 client counts by its /64, an
   IPv4-mapped one as the IPv4; a request without one, as on a unix socket,
   is limited per identifier only), past 3 per identifier in an hour (case and surrounding spaces ignored), or with the
   hourly budget spent; otherwise 202 and the same body whether the identifier names an active account, an inactive
   one or none. The work runs after the answer: an active account, by username or by email, gets one email with a
   live reset link on ``LIBREFOLIO_PUBLIC_URL``, in its language; nobody else gets anything. The work reads the
   configuration again before it makes the link: email, links or the budget gone meanwhile, nothing is made and the
   account's earlier live link stays live; a link it made that could not be sent — whatever stopped it: a refusal of
   the server, an error while the email is built or while the account's language is read — is revoked, and an
   unexpected error is logged as its type alone, without a traceback. Nothing escapes the request; neither the
   identifier nor the token reaches the logs.
8. Behind a reverse proxy LibreFolio does not trust (decision N70; lot E-13, on H's helper H-36) — the usual deployment:
   the Docker image behind the proxy HTTPS needs, neither ``LIBREFOLIO_CLIENT_IP_HEADER`` nor ``FORWARDED_ALLOW_IPS``
   set —, every visitor arrives from the proxy's private address with an ``X-Forwarded-For`` the app does not trust.
   Two visitors behind one private proxy never share one «forgot password» budget per address: the route counts H-36's
   ``rate_limit_address(request)``, the address of 7 but for a request from a local peer (``classify_ip``: loopback,
   private, link-local, unique-local, CGNAT) carrying ``X-Forwarded-For``, ``Forwarded`` or ``X-Real-IP`` whose
   address neither ``LIBREFOLIO_CLIENT_IP_HEADER`` nor uvicorn gave: ``None``, counted under no address — the limit per
   identifier still holds, as for a request without an address (EMA-043). A public address's own forwarding headers
   move nothing, as 7 says (EMA-035), and a private address without one — a device of the local network talking to
   LibreFolio directly — keeps its own budget. EMA-050 pins the skip, red before the cure; EMA-051 and EMA-052 are
   guards, green before and after; the three set the limiter per address at one request.

In-process: the real routers of auth and email, and the instance route of the system router (``instance_router``, under
``/system``), mounted under the API prefix as ``api/v1/router.py`` mounts them, in an
app of this test whose ``get_session_generator`` opens sessions on a private SQLite file under ``tmp_path`` (NullPool,
disposed at teardown) holding the default global settings. Accounts are written as rows with a real bcrypt hash at cost
4 (``auth_service.BCRYPT_ROUNDS``), sign in through ``POST /auth/login`` and keep their cookie in an
``httpx.AsyncClient`` over ``httpx.ASGITransport`` (the session cookie's Secure attribute on ``auto``, as shipped, so
that ``http://test`` gets it back). ``ASGITransport`` awaits the whole ASGI call, background tasks included: when a
request returns, the work of «forgot password» has run, and an exception escaping it would be raised in the test; the
client address the app sees is the transport's ``client``. Tokens are issued by A's token service, as A's routes do.
The lane's backend is never called: the SMTP variables are those of this process. An autouse fixture removes every
inherited ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BLOCKED`` and each test sets its own
(monkeypatch); the app of this test mounts the routers without ``/api/v1``'s instance-block guard, so a blocked
instance is refused by the sending itself;
``delivery.INSTANCE_BUDGET`` and the three «forgot password» limiters are private limiters on a fake clock, with the
shipped limits — «forgot password» has no hold left to lift (lot E4) —; ``smtp.SMTP_TIMEOUT_SECONDS`` is 5 s, a bound, never a wait; ``socket.getaddrinfo`` resolves the
loopback only and records any other name, so a host name configured for the status is never looked up, let alone
contacted. Every SMTP conversation is with ``FakeSmtpServer`` on 127.0.0.1, on a port the OS picks; a refused
connection is ``closed_port()``. Nothing is timed.
"""

from __future__ import annotations

import asyncio
import contextlib
import html
import math
import os
import re
import socket
import threading
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import email as email_api
from backend.app.api.v1.system import instance as instance_api
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User, UserSettings
from backend.app.db.session import get_session_generator
from backend.app.schemas.auth import AccountsInstanceConfig
from backend.app.schemas.settings import SETTINGS_REGISTRY, UserSettingsRead
from backend.app.schemas.system import InstanceConfigResponse
from backend.app.services.accounts import auth_service, token_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus
from backend.app.services.email import delivery, flows, smtp
from backend.app.services.email.messages import EmailRecipientError, build_invite, build_password_reset, build_test_message
from backend.app.services.platform.client_address import _untrusted_forwarding, untrusted_forwarding_seen
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer, closed_port
from backend.test_scripts.test_utils import print_section, print_success

# Paths of the in-process app, mounted as api/v1/router.py mounts the routers.
LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
STATUS = f"{API_V1_PREFIX}/email/status"
SEND_TEST = f"{API_V1_PREFIX}/email/test"
LINKS = f"{API_V1_PREFIX}/email/links"
FORGOT = f"{API_V1_PREFIX}/email/password-reset"
INSTANCE = f"{API_V1_PREFIX}/system/instance"
BASE_URL = "http://test"
#: ``request.url.netloc`` of a request sent to BASE_URL: the instance the test email names.
INSTANCE_LABEL = "test"
TIMEOUT = 30.0

#: The password of every account here, hashed with bcrypt at cost 4.
ACCOUNT_PASSWORD = "Email-Api-Pass-2026"
ADMIN = "zq_admin"
MEMBER = "zq_member"
DEFAULT_LANGUAGE_KEY = SETTINGS_REGISTRY.global_.DEFAULT_LANGUAGE.key
#: A theme outside light/dark/auto, as an older or newer release could leave in a row: ``UserSettingsRead`` refuses it.
STALE_THEME = "sepia"

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
TLS_VARIABLE = "LIBREFOLIO_SMTP_TLS"
PORT_VARIABLE = "LIBREFOLIO_SMTP_PORT"
USER_VARIABLE = "LIBREFOLIO_SMTP_USER"
FROM_VARIABLE = "LIBREFOLIO_SMTP_FROM"
PASSWORD_FILE_VARIABLE = "LIBREFOLIO_SMTP_PASSWORD_FILE"

# Distinctive values: found in an answer, each is a leak. Their cores ("zq-host", "zq-sender"...) are searched, so that a
# value quoted in part is caught as surely as a whole one.
SMTP_USER_NAME = "zq-mailer"
SMTP_PASSWORD = "c4nary-SMTP-p4ss-never-in-an-answer"
SENDER_ADDRESS = "zq-sender@example.com"
SENDER_HEADER = f"Zq Sender <{SENDER_ADDRESS}>"
SENDER = ("Zq Sender", SENDER_ADDRESS)
REPLY_TO_ADDRESS = "zq-support@example.com"
REPLY_TO_HEADER = f"Zq Support <{REPLY_TO_ADDRESS}>"
#: A name outside the local network, for states the status reads without connecting: the guard on getaddrinfo proves it.
PUBLIC_HOST = "smtp.zq-host.example.com"
PUBLIC_PORT = "48613"
#: A usable configuration towards PUBLIC_HOST (starttls, the default), 9 an hour: the base of the states read without a server.
PUBLIC_CONFIGURATION = {
    "host": PUBLIC_HOST,
    "port": PUBLIC_PORT,
    "user": SMTP_USER_NAME,
    "password": SMTP_PASSWORD,
    "from": SENDER_HEADER,
    "reply_to": REPLY_TO_HEADER,
    "max_per_hour": "9",
}
MISSING_FILE = "<a password file that does not exist>"
PASSWORD_IN_FILE = "<the SMTP password, in a file>"

#: What no answer of POST /email/test may hold.
NOT_IN_AN_ANSWER = {
    "the SMTP password": SMTP_PASSWORD,
    "the SMTP user": SMTP_USER_NAME,
    "the SMTP host": "127.0.0.1",
    "the public SMTP host": "zq-host",
    "the sender": "zq-sender",
}
#: What no status may hold, in any state.
NOT_IN_A_STATUS = {
    "the host": "zq-host",
    "the port": PUBLIC_PORT,
    "the user": SMTP_USER_NAME,
    "the password": SMTP_PASSWORD,
    "the sender": "zq-sender",
    "the Reply-To": "zq-support",
}
STATUS_KEYS = {"state", "problem", "variable", "checks", "budget", "links"}
CHECK_KEYS = {"check_id", "severity", "i18n_key", "detail"}
LINKS_KEYS = {"ready", "base", "problem"}
INSTANCE_EMAIL_KEYS = {"available", "links"}

PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
#: The hosting provider's block: a blocked instance sends nothing.
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
#: The public address of the instance, with a port and a path prefix: every emailed link starts with it.
PUBLIC_URL = "https://folio.zq-public.example.com:8443/app"
#: How the emails name the instance: the host of PUBLIC_URL, with its port.
PUBLIC_URL_HOST = "folio.zq-public.example.com:8443"
NOT_A_PUBLIC_URL = "ftp://zq-not-public.example.com"
#: A stranger's site: sent as the Host, Origin, X-Forwarded-Host and Referer of a request, it must never reach an email.
ATTACKER_HOST = "evil.zq-attacker.example.com"
ATTACKER_HEADERS = {
    "Host": ATTACKER_HOST,
    "Origin": f"https://{ATTACKER_HOST}",
    "X-Forwarded-Host": ATTACKER_HOST,
    "X-Forwarded-Proto": "https",
    "Referer": f"https://{ATTACKER_HOST}/settings/users",
}
GUEST = "zq-guest@example.com"
OTHER_GUEST = "zq-other-guest@example.com"
NEVER_ISSUED = "never-issued-api-0123456789abcdefghijklmnopqrst"
INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
PURPOSES = {"invite": INVITE, "password_reset": PASSWORD_RESET}
PAGES = {INVITE: "/invite", PASSWORD_RESET: "/reset-password"}
DEAD_KINDS = ("expired", "consumed", "revoked", "unknown", "other-purpose")
#: The «forgot password» limiters as the module ships them, read before any fixture replaces them.
SHIPPED_BY_ADDRESS = delivery.ADDRESS_BUDGET
#: How many activation and reset emails one client address may ask for in an hour: 20 unset.
SIGNUP_PER_ADDRESS = "LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS"
SHIPPED_BY_IDENTIFIER = flows.FORGOT_BY_IDENTIFIER
SHIPPED_BY_MAILBOX = flows.FORGOT_BY_MAILBOX
#: The address httpx's ASGITransport gives a request unless told otherwise: «the client» of the in-process app.
TRANSPORT_CLIENT = ("127.0.0.1", 123)
#: Other clients of the in-process app, from the documentation ranges: «forgot password» counts per client address.
FIRST_CLIENT = ("198.51.100.7", 40001)
SECOND_CLIENT = ("203.0.113.9", 40002)
#: A name no account has, for «forgot password».
NOBODY = "zq_nobody"
#: What the fake server says when it refuses a recipient: never in an answer.
RECIPIENT_REFUSAL_WORDS = ("Recipient address rejected", "refused by the fake server", "5.1.1")

#: The only names socket.getaddrinfo may resolve here: the loopback the fake SMTP server and closed_port() use.
LOOPBACK_NAMES = frozenset({"127.0.0.1", "::1", "localhost"})

#: The fake clock's start, the time of the first send in the budget tests, and the window of the hourly budget.
START = 1_000.0
WINDOW = 3_600.0
#: (seconds between the only send of the hour and the question, the whole seconds the answer must name): ceil, never down.
SPENT = [
    pytest.param(30.75, 3570, id="half-a-minute-after-the-send"),
    pytest.param(3599.75, 1, id="a-quarter-second-before-the-hour"),
]


def _check(check_id: str, severity: str, i18n_key: str, detail: dict[str, str] | None = None) -> dict[str, Any]:
    """A check as the status answers it."""
    return {"check_id": check_id, "severity": severity, "i18n_key": i18n_key, "detail": detail or {}}


SMTP_OFF = _check("email.smtp", "ok", "email.checks.smtp.off")
SMTP_OK = _check("email.smtp", "ok", "email.checks.smtp.ok")
ENCRYPTION_OK = _check("email.smtp_encryption", "ok", "email.checks.smtpEncryption.ok")
ENCRYPTION_LOCAL_PLAIN = _check("email.smtp_encryption", "ok", "email.checks.smtpEncryption.localPlain")
ENCRYPTION_PLAIN = _check("email.smtp_encryption", "warning", "email.checks.smtpEncryption.plain")
LINKS_OK = _check("email.links", "ok", "email.checks.links.ok")
LINKS_MISSING = _check("email.links", "info", "email.checks.links.missing")
LINKS_INVALID = _check("email.links", "warning", "email.checks.links.invalid")

#: (LIBREFOLIO_PUBLIC_URL — None: unset —, the ``links`` of the status, the ``email.links`` check once email is usable).
LINK_STATES = [
    pytest.param(None, {"ready": False, "base": None, "problem": "PUBLIC_URL_MISSING"}, LINKS_MISSING, id="unset"),
    pytest.param("   ", {"ready": False, "base": None, "problem": "PUBLIC_URL_MISSING"}, LINKS_MISSING, id="blank"),
    pytest.param(NOT_A_PUBLIC_URL, {"ready": False, "base": None, "problem": "PUBLIC_URL_INVALID"}, LINKS_INVALID, id="not-http"),
    pytest.param(f"{PUBLIC_URL}/", {"ready": True, "base": PUBLIC_URL, "problem": None}, LINKS_OK, id="ready-trailing-slash"),
]
#: The SMTP variables of each state of email, read without a server: off, invalid, usable towards a host never contacted.
EMAIL_STATES = {
    "off": {},
    "invalid": {**PUBLIC_CONFIGURATION, "tls": "ssl"},
    "ready": PUBLIC_CONFIGURATION,
}


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_email_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL`` and ``LIBREFOLIO_BLOCKED`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in (PUBLIC_URL_VARIABLE, BLOCKED_VARIABLE, SIGNUP_PER_ADDRESS):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    """``delivery._report_invalid`` remembers for the whole process what it logged: each test starts, and leaves, with nothing reported."""
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


@pytest.fixture(autouse=True)
def _nothing_noted_yet(monkeypatch: pytest.MonkeyPatch) -> None:
    """H's ``_untrusted_forwarding`` (decision N70) holds fresh empty sets for each test, the process's own put back after it: the forwarding headers this module sends — «local» from EMA-050, «public» from EMA-051 and EMA-035's forged one — leave no note, so a later reader's first noting of a class, the only one that logs its warning, still logs it."""
    monkeypatch.setitem(_untrusted_forwarding, "local", set())
    monkeypatch.setitem(_untrusted_forwarding, "public", set())


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private hourly budget on the fake clock in place of the process's: no test spends, or depends on, the real one."""
    limiter = SlidingWindowLimiter(50, WINDOW, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


@dataclass(frozen=True)
class ForgotLimits:
    """The three «forgot password» limiters of a test: per client address, per identifier, per recipient mailbox."""

    by_address: SlidingWindowLimiter
    by_identifier: SlidingWindowLimiter
    by_mailbox: SlidingWindowLimiter


@pytest.fixture(autouse=True)
def forgot_limits(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> ForgotLimits:
    """Private «forgot password» limiters with the shipped limits, on the fake clock: every request of this process comes from 127.0.0.1, and no test counts in, or is counted by, the process's limiters."""
    limits = ForgotLimits(
        by_address=SlidingWindowLimiter(SHIPPED_BY_ADDRESS.limit, SHIPPED_BY_ADDRESS.window_seconds, clock=clock),
        by_identifier=SlidingWindowLimiter(SHIPPED_BY_IDENTIFIER.limit, SHIPPED_BY_IDENTIFIER.window_seconds, clock=clock),
        by_mailbox=SlidingWindowLimiter(SHIPPED_BY_MAILBOX.limit, SHIPPED_BY_MAILBOX.window_seconds, clock=clock),
    )
    monkeypatch.setattr(delivery, "ADDRESS_BUDGET", limits.by_address)
    monkeypatch.setattr(flows, "FORGOT_BY_IDENTIFIER", limits.by_identifier)
    monkeypatch.setattr(flows, "FORGOT_BY_MAILBOX", limits.by_mailbox)
    return limits


@pytest.fixture(autouse=True)
def _bounded_smtp_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """5 s instead of 20: a defect that hangs fails sooner. No test waits for it."""
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 5.0)


@pytest.fixture(autouse=True)
def network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """``socket.getaddrinfo`` resolves the loopback only; any other name is refused and recorded here: a host name configured for the status is never looked up."""
    resolve = socket.getaddrinfo
    refused: list[str] = []

    def loopback_only(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and name not in LOOPBACK_NAMES:
            refused.append(str(name))
            raise socket.gaierror(socket.EAI_NONAME, f"the email API tests resolve the loopback only, not {name!r}")
        return resolve(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    return refused


@dataclass(frozen=True)
class _Account:
    id: int
    username: str
    email: str


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the routers of auth and email, every session on ``engine``; an administrator and a member."""

    engine: AsyncEngine
    app: FastAPI
    admin: _Account
    member: _Account


def _app(engine: AsyncEngine) -> FastAPI:
    """The real routers of auth and email, and the instance route of the system router, mounted under the API prefix as ``api/v1/router.py`` mounts them; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    for router in (auth_api.router, email_api.router):
        app.include_router(router, prefix=API_V1_PREFIX)
    app.include_router(instance_api.instance_router, prefix=f"{API_V1_PREFIX}/system")

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


async def _add_account(engine: AsyncEngine, username: str, *, admin: bool = False, email: str | None = None, active: bool = True) -> _Account:
    """An account written as a row, ``<username>@example.com`` unless ``email`` says otherwise, active unless ``active`` is false, with a real bcrypt hash of ACCOUNT_PASSWORD (cost 4)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@example.com", hashed_password=auth_service.hash_password(ACCOUNT_PASSWORD), is_superuser=admin, is_active=active)
        session.add(user)
        await session.commit()
    return _Account(id=user.id, username=user.username, email=user.email)


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with, an administrator and a member; bcrypt at cost 4, the cookie's Secure attribute on ``auto``. Disposed at teardown."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'instance.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        admin = await _add_account(engine, ADMIN, admin=True)
        member = await _add_account(engine, MEMBER)
        yield _Private(engine=engine, app=_app(engine), admin=admin, member=member)
    finally:
        await engine.dispose()


# =============================================================================
# HELPERS
# =============================================================================


@contextlib.asynccontextmanager
async def _browser(private: _Private, base_url: str = BASE_URL, *, raise_app_exceptions: bool = True, client: tuple[str, int] | None = TRANSPORT_CLIENT) -> AsyncIterator[httpx.AsyncClient]:
    """A browser of its own on the private instance: its own cookie jar, no session until it signs in, its requests from ``client`` (the address the app sees; ``None``: no address, as on a unix socket). With ``raise_app_exceptions=False`` an error the app does not handle reaches it as the 500 a browser would get, instead of being raised in the test."""
    transport = httpx.ASGITransport(app=private.app, raise_app_exceptions=raise_app_exceptions, client=client)
    async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=TIMEOUT) as browser:
        yield browser


async def _sign_in(client: httpx.AsyncClient, account: _Account) -> None:
    """``POST /auth/login`` as ``account``; the client keeps the session cookie."""
    response = await client.post(LOGIN, json={"username": account.username, "password": ACCOUNT_PASSWORD})
    assert response.status_code == 200, f"setup: {account.username} could not sign in: {response.status_code} {response.text}"


async def _status_as_admin(private: _Private) -> httpx.Response:
    """``GET /email/status`` as the administrator, 200 asserted."""
    async with _browser(private) as client:
        await _sign_in(client, private.admin)
        response = await client.get(STATUS)
    assert response.status_code == 200, f"{response.status_code} {response.text}"
    return response


async def _set_account_language(engine: AsyncEngine, user_id: int, language: str, *, theme: str = "light") -> None:
    """The account's ``user_settings`` row, its language ``language`` and its theme ``theme`` — written as a row: a table model does not validate —, the other columns at their defaults."""
    async with AsyncSession(engine) as session:
        session.add(UserSettings(user_id=user_id, language=language, theme=theme))
        await session.commit()


async def _settings_row(engine: AsyncEngine, user_id: int) -> tuple[str, str] | None:
    """``(language, theme)`` of the account's ``user_settings`` row, read fresh; ``None`` without a row."""
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(UserSettings.language, UserSettings.theme).where(UserSettings.user_id == user_id))).one_or_none()
    return None if row is None else tuple(row)


def _read_model_refusal() -> ValidationError:
    """The ``ValidationError`` the read model raises for a settings row with a theme outside light/dark/auto: a ``ValueError`` that is not a recipient error."""
    try:
        UserSettingsRead(language="it", base_currency="EUR", theme=STALE_THEME)
    except ValidationError as refusal:
        return refusal
    raise AssertionError(f"setup: UserSettingsRead accepted the theme {STALE_THEME!r}")


async def _set_default_language(engine: AsyncEngine, value: str) -> None:
    """The instance's ``default_language`` row says ``value``."""
    async with AsyncSession(engine) as session:
        result = await session.execute(update(GlobalSetting).where(GlobalSetting.key == DEFAULT_LANGUAGE_KEY).values(value=value))
        assert result.rowcount == 1, "setup: initialize_global_settings did not seed the default_language row"
        await session.commit()


def _configure(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None], tmp_path: Path | None = None) -> None:
    """Set ``LIBREFOLIO_SMTP_<NAME>`` for each ``name: value``, ``None`` leaving it unset; the file markers become paths in ``tmp_path``."""
    for name, value in variables.items():
        if value == MISSING_FILE:
            value = str(tmp_path / "zq-missing-password-file")
        elif value == PASSWORD_IN_FILE:
            password_file = tmp_path / "zq-password-file"
            password_file.write_text(f"{SMTP_PASSWORD}\n", encoding="utf-8")
            value = str(password_file)
        variable = SMTP_PREFIX + name.upper()
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)


def _point_at(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer, **extra: str | None) -> None:
    """Email configured to go through ``fake``: its address and port, no TLS on the loopback, this module's sender; ``extra`` on top."""
    _configure(monkeypatch, {"host": fake.host, "port": str(fake.port), "tls": "none", "from": SENDER_HEADER, **extra})


@contextlib.contextmanager
def _refusing(kind: str, monkeypatch: pytest.MonkeyPatch, recipient: str) -> Iterator[FakeSmtpServer | None]:
    """Email configured, with this module's SMTP user and password, towards a server that refuses as ``kind`` says; the fake, or None for a closed port."""
    credentials = {"user": SMTP_USER_NAME, "password": SMTP_PASSWORD}
    if kind == "closed-port":
        with closed_port() as port:
            _configure(monkeypatch, {"host": "127.0.0.1", "port": str(port), "tls": "none", "from": SENDER_HEADER, **credentials})
            yield None
        return
    accepted = (SMTP_USER_NAME, SMTP_PASSWORD)
    options = {
        "recipient": {"credentials": accepted, "refuse_recipients": {recipient}},
        "credentials": {"credentials": (SMTP_USER_NAME, "the-password-the-server-expects")},
        "sender": {"credentials": accepted, "refuse_sender": True},
        "data": {"credentials": accepted, "refuse_data": True},
        "starttls": {"credentials": accepted},
    }[kind]
    with FakeSmtpServer(**options) as fake:
        _point_at(monkeypatch, fake, tls="starttls" if kind == "starttls" else "none", **credentials)
        yield fake


def _checks(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """The checks of a status by id, each id once."""
    checks = body["checks"]
    by_id = {check["check_id"]: check for check in checks}
    assert len(by_id) == len(checks), f"a check appears twice: {checks}"
    return by_id


def _detail(response: httpx.Response) -> dict[str, Any]:
    """``detail`` of a coded refusal: a mapping, not FastAPI's list of validation errors."""
    body = response.json()
    detail = body.get("detail") if isinstance(body, dict) else None
    assert isinstance(detail, dict), f"expected a coded refusal in detail: {response.status_code} {response.text}"
    return detail


def _leaks(text: str, needles: dict[str, str]) -> list[str]:
    """The labels of the ``needles`` found in ``text``, in any letter case."""
    folded = text.casefold()
    return sorted(label for label, needle in needles.items() if needle.casefold() in folded)


def _mailboxes(header: object) -> list[tuple[str, str]]:
    return [(address.display_name, address.addr_spec) for address in header.addresses]


def _lines(text: str) -> str:
    """``text`` without the line-ending differences of a MIME round trip."""
    return text.replace("\r\n", "\n").rstrip("\n")


def _loop_running() -> bool:
    """Whether the calling thread runs an event loop right now."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _links_ready(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer, **extra: str | None) -> None:
    """Email through ``fake`` (``_point_at``, ``extra`` on top) and links ready on PUBLIC_URL."""
    _point_at(monkeypatch, fake, **extra)
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


def _set_public_url(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """``LIBREFOLIO_PUBLIC_URL`` set to ``value``; ``None`` leaves it unset."""
    if value is not None:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, value)


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: object) -> IssuedToken:
    """A token issued by A's token service, committed: what a route of A has just handed to the administrator."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


def _owned(purpose: AccountTokenPurpose, owner_id: int) -> dict[str, object]:
    """What a token of ``purpose`` needs: an invitation carries the guest's address, a reset link its account."""
    return {"email": GUEST} if purpose == INVITE else {"user_id": owner_id}


async def _dead_token(engine: AsyncEngine, purpose: AccountTokenPurpose, kind: str, owner_id: int) -> str:
    """A token that is not a live link of ``purpose``: never issued, expired, consumed, revoked, or a live token of the other purpose."""
    if kind == "unknown":
        return NEVER_ISSUED
    if kind == "other-purpose":
        other = PASSWORD_RESET if purpose == INVITE else INVITE
        return (await _issue(engine, other, **_owned(other, owner_id))).token
    if kind == "expired":
        return (await _issue(engine, purpose, now=utcnow() - DEFAULT_TTL[purpose] - timedelta(days=1), **_owned(purpose, owner_id))).token
    issued = await _issue(engine, purpose, **_owned(purpose, owner_id))
    async with AsyncSession(engine) as session:
        if kind == "consumed":
            assert await token_service.consume_token(session, issued.token, purpose) is not None, "setup: consumed"
        else:
            assert await token_service.revoke_tokens(session, token_id=issued.record.id) == 1, "setup: revoked"
        await session.commit()
    return issued.token


async def _reset_rows(engine: AsyncEngine, user_id: int) -> list[AccountToken]:
    """Every password-reset row of the account, oldest first, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        statement = select(AccountToken).where(AccountToken.purpose == PASSWORD_RESET, AccountToken.user_id == user_id).order_by(AccountToken.id)
        return list((await session.execute(statement)).scalars().all())


def _text(received: object) -> str:
    """The plain-text part of a received message."""
    return received.message.get_body(preferencelist=("plain",)).get_content()


def _html(received: object) -> str:
    """The HTML part of a received message."""
    return received.message.get_body(preferencelist=("html",)).get_content()


def _hrefs(document: str) -> list[str]:
    """Every ``href`` of an HTML part, unescaped: what a mail client opens."""
    return [html.unescape(value) for value in re.findall(r'href="([^"]*)"', document)]


def _token_in(text: str, purpose: AccountTokenPurpose) -> str:
    """The token of the PUBLIC_URL link of ``purpose`` an email text carries; fails when it carries none."""
    match = re.search(re.escape(f"{PUBLIC_URL}{PAGES[purpose]}#") + r"(\S+)", text)
    assert match, f"no {PUBLIC_URL}{PAGES[purpose]} link in the email: {text!r}"
    return parse_qs(match.group(1))["token"][0]


def _assert_is(received: object, expected: object) -> None:
    """The message is exactly the content a builder wrote: subject, text and HTML."""
    assert received.message["Subject"] == expected.subject
    assert _lines(_text(received)) == _lines(expected.text)
    assert _lines(_html(received)) == _lines(expected.html)


def _stranger_in(received: object) -> list[str]:
    """Where the stranger's site of ATTACKER_HEADERS appears in a received message: its headers, its text, its HTML, its raw bytes."""
    places = {
        "the headers": "\n".join(f"{name}: {value}" for name, value in received.message.items()),
        "the text": _text(received),
        "the HTML": _html(received),
        "the raw message": received.data.decode("utf-8", "replace"),
    }
    return sorted(place for place, content in places.items() if "zq-attacker" in content.casefold())


async def _token_status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose) -> TokenStatus:
    """What A's token service says of ``token`` as a link of ``purpose`` now, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return (await token_service.inspect_token(session, token, purpose)).status


async def _email_link_as_admin(private: _Private, purpose: str, token: str, *, headers: dict[str, str] | None = None, **fields: object) -> httpx.Response:
    """``POST /email/links`` ``{purpose, token, **fields}`` as the administrator, the request carrying ``headers``."""
    async with _browser(private) as client:
        await _sign_in(client, private.admin)
        return await client.post(LINKS, json={"purpose": purpose, "token": token, **fields}, headers=headers)


async def _forgot(private: _Private, identifier: str, *, client: tuple[str, int] | None = TRANSPORT_CLIENT, headers: dict[str, str] | None = None) -> httpx.Response:
    """``POST /email/password-reset`` for ``identifier``, from a browser without a session at the address ``client`` (``None``: no address)."""
    async with _browser(private, client=client) as browser:
        return await browser.post(FORGOT, json={"identifier": identifier}, headers=headers)


# =============================================================================
# 1. ACCESS
# =============================================================================


@pytest.mark.asyncio
async def test_without_a_session_both_routes_answer_401_and_send_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-001 — contract 1: email ready towards a running fake, no session cookie: ``GET /email/status`` and ``POST /email/test`` are 401; the fake accepted no connection and nothing was spent."""
    print_section("EMA-001: no session")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private) as client:
            status = await client.get(STATUS)
            sent = await client.post(SEND_TEST)

    assert (status.status_code, sent.status_code) == (401, 401), f"status {status.status_code} {status.text}; test {sent.status_code} {sent.text}"
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("401 and 401, nothing sent")


@pytest.mark.asyncio
async def test_a_signed_in_member_gets_403_from_both_routes_and_sends_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-002 — contract 1: the same configuration, a member whose session works (``GET /auth/me`` 200, the barrier: a broken session would be 401, not 403): both routes are 403; no connection, nothing spent."""
    print_section("EMA-002: a member")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private) as client:
            await _sign_in(client, private.member)
            me = await client.get(ME)
            status = await client.get(STATUS)
            sent = await client.post(SEND_TEST)

    assert me.status_code == 200 and me.json()["user"]["username"] == MEMBER, f"barrier: the member's session must work: {me.status_code} {me.text}"
    assert (status.status_code, sent.status_code) == (403, 403), f"status {status.status_code} {status.text}; test {sent.status_code} {sent.text}"
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("403 and 403, nothing sent")


@pytest.mark.asyncio
async def test_an_administrator_reaches_both_routes(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-003 — contract 1: the same configuration, the administrator: the status is 200 ``ready``, the test email 200, one message to the administrator's own address, one unit spent."""
    print_section("EMA-003: the administrator")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            status = await client.get(STATUS)
            sent = await client.post(SEND_TEST)

    assert status.status_code == 200 and status.json()["state"] == "ready", f"{status.status_code} {status.text}"
    assert sent.status_code == 200, f"{sent.status_code} {sent.text}"
    assert [message.rcpt_tos for message in fake.messages] == [[private.admin.email]]
    assert budget.count() == 1
    print_success("200 and 200, one message")


# =============================================================================
# 2. GET /email/status
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="nothing-set"),
        pytest.param({**PUBLIC_CONFIGURATION, "host": None, "tls": "ssl"}, id="everything-but-the-host-tls-invalid"),
    ],
)
async def test_without_a_host_the_status_is_off(private: _Private, monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None]) -> None:
    """EMA-004 — contract 2: no host — even with every other variable set, an invalid TLS mode included —: ``state="off"``, no problem, no variable, no budget; ``email.smtp`` ok/off, ``email.smtp_encryption`` ok/ok, ``email.links`` ok/ok (email is off: nothing to say about its links), each with an empty detail; exactly the six keys of the status and the four of a check."""
    print_section("EMA-004: off")
    _configure(monkeypatch, variables)

    body = (await _status_as_admin(private)).json()

    assert set(body) == STATUS_KEYS, body
    assert (body["state"], body["problem"], body["variable"], body["budget"]) == ("off", None, None, None), body
    assert [set(check) for check in body["checks"]] == [CHECK_KEYS, CHECK_KEYS, CHECK_KEYS], body["checks"]
    assert _checks(body) == {"email.smtp": SMTP_OFF, "email.smtp_encryption": ENCRYPTION_OK, "email.links": LINKS_OK}
    print_success("off, three ok checks")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "problem", "variable"),
    [
        pytest.param({"tls": "ssl"}, "SMTP_TLS_INVALID", TLS_VARIABLE, id="tls-invalid"),
        pytest.param({"port": "65536"}, "SMTP_PORT_INVALID", PORT_VARIABLE, id="port-invalid"),
        pytest.param({"from": None}, "SMTP_FROM_MISSING", FROM_VARIABLE, id="from-missing"),
        pytest.param({"password": None}, "SMTP_CREDENTIALS_INCOMPLETE", USER_VARIABLE, id="user-without-password"),
        pytest.param({"password": None, "password_file": MISSING_FILE}, "SMTP_PASSWORD_UNREADABLE", PASSWORD_FILE_VARIABLE, id="password-file-missing"),
    ],
)
async def test_an_unusable_configuration_is_invalid_with_its_problem_and_variable(private: _Private, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, network: list[str], overrides: dict[str, str | None], problem: str, variable: str) -> None:
    """EMA-005 — contract 2: one fault on a usable configuration towards a public host: ``state="invalid"``, the problem and the variable at fault, no budget; ``email.smtp`` error ``email.checks.smtp.invalid`` with ``detail == {problem, variable}``; the encryption and links checks ok (email is not usable); no name resolved."""
    print_section(f"EMA-005: {problem}")
    _configure(monkeypatch, {**PUBLIC_CONFIGURATION, **overrides}, tmp_path)

    body = (await _status_as_admin(private)).json()

    assert (body["state"], body["problem"], body["variable"], body["budget"]) == ("invalid", problem, variable, None), body
    invalid = _check("email.smtp", "error", "email.checks.smtp.invalid", {"problem": problem, "variable": variable})
    assert _checks(body) == {"email.smtp": invalid, "email.smtp_encryption": ENCRYPTION_OK, "email.links": LINKS_OK}
    assert network == [], f"the status resolved {network}"
    print_success(f"invalid: {problem} on {variable}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("target", "tls", "encryption"),
    [
        pytest.param("loopback", "none", ENCRYPTION_LOCAL_PLAIN, id="plain-to-the-loopback"),
        pytest.param("public", None, ENCRYPTION_OK, id="starttls-to-a-public-host"),
        pytest.param("public", "tls", ENCRYPTION_OK, id="implicit-tls-to-a-public-host"),
        pytest.param("public", "none", ENCRYPTION_PLAIN, id="plain-to-a-public-host"),
    ],
)
async def test_a_usable_configuration_is_ready_with_its_checks_and_a_whole_budget(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], target: str, tls: str | None, encryption: dict[str, Any]) -> None:
    """EMA-006 — contract 2: ``state="ready"``, no problem, no variable; ``email.smtp`` ok/ok; the encryption check ``localPlain`` for plain text to the fake on 127.0.0.1, ``ok`` for starttls and tls, a ``warning`` ``plain`` with an empty detail for plain text to a public host; ``email.links`` the ``info`` ``missing``, ``LIBREFOLIO_PUBLIC_URL`` being unset; the budget whole, ``{9, 9, 0}``. A fake runs in every case, and the status opened no connection to it and resolved no name — the public host is never even looked up."""
    print_section(f"EMA-006: ready, {target}, tls {tls!r}")

    with FakeSmtpServer() as fake:
        if target == "loopback":
            _point_at(monkeypatch, fake, max_per_hour="9")
        else:
            _configure(monkeypatch, {**PUBLIC_CONFIGURATION, "tls": tls})
        body = (await _status_as_admin(private)).json()

    assert (body["state"], body["problem"], body["variable"]) == ("ready", None, None), body
    assert body["budget"] == {"max_per_hour": 9, "remaining": 9, "retry_after_seconds": 0}
    assert _checks(body) == {"email.smtp": SMTP_OK, "email.smtp_encryption": encryption, "email.links": LINKS_MISSING}
    assert (fake.connections, network) == (0, []), f"the status connected ({fake.connections}) or resolved {network}"
    print_success(f"ready, {encryption['severity']} {encryption['i18n_key']}, no connection")


@pytest.mark.asyncio
async def test_each_test_email_takes_one_unit_of_the_budget_the_status_shows(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-007 — contract 2: ``LIBREFOLIO_SMTP_MAX_PER_HOUR=3``: the status says 3 of 3 left, then one ``POST /email/test`` goes out, then it says 2 of 3, 0 seconds to wait."""
    print_section("EMA-007: one test email, one unit")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake, max_per_hour="3")
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            before = await client.get(STATUS)
            sent = await client.post(SEND_TEST)
            after = await client.get(STATUS)

    assert sent.status_code == 200, f"{sent.status_code} {sent.text}"
    assert before.json()["budget"] == {"max_per_hour": 3, "remaining": 3, "retry_after_seconds": 0}, before.text
    assert after.json()["budget"] == {"max_per_hour": 3, "remaining": 2, "retry_after_seconds": 0}, after.text
    assert (len(fake.messages), budget.count()) == (1, 1)
    print_success("3 → 2 after one test email")


@pytest.mark.asyncio
@pytest.mark.parametrize(("elapsed", "wait"), SPENT)
async def test_a_spent_budget_shows_none_left_and_the_whole_seconds_to_wait(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, elapsed: float, wait: int) -> None:
    """EMA-008 — contract 2: ``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, the only unit spent at ``START``; ``elapsed`` seconds later the status says 0 left and ``ceil(3600 - elapsed)`` seconds to wait; an hour after the send it says 1 left and 0 seconds.

    The precondition is verified: for both cases the ceiling differs from the truncated and from the rounded value, so a
    status that rounded down, or to the nearest second, could not pass.
    """
    print_section(f"EMA-008: spent, {elapsed} s after the send")
    assert wait == math.ceil(WINDOW - elapsed) and wait not in (int(WINDOW - elapsed), round(WINDOW - elapsed)), "precondition: the case must tell ceil from int and round"

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake, max_per_hour="1")
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            clock.now = START
            sent = await client.post(SEND_TEST)
            clock.now = START + elapsed
            spent = await client.get(STATUS)
            clock.now = START + WINDOW
            whole_again = await client.get(STATUS)

    assert sent.status_code == 200 and len(fake.messages) == 1, f"setup: the only unit must go to a real send: {sent.status_code} {sent.text}"
    assert spent.json()["state"] == "ready", spent.text
    assert spent.json()["budget"] == {"max_per_hour": 1, "remaining": 0, "retry_after_seconds": wait}, spent.text
    assert whole_again.json()["budget"] == {"max_per_hour": 1, "remaining": 1, "retry_after_seconds": 0}, whole_again.text
    print_success(f"0 left, {wait} s to wait; whole again after the hour")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("variables", "state"),
    [
        pytest.param({**PUBLIC_CONFIGURATION, "host": None}, "off", id="off-everything-else-set"),
        pytest.param(PUBLIC_CONFIGURATION, "ready", id="ready-starttls"),
        pytest.param({**PUBLIC_CONFIGURATION, "tls": "none"}, "ready", id="ready-plain-to-a-public-host"),
        pytest.param({**PUBLIC_CONFIGURATION, "password": None, "password_file": PASSWORD_IN_FILE}, "ready", id="ready-password-in-a-file"),
        pytest.param({**PUBLIC_CONFIGURATION, "tls": "ssl"}, "invalid", id="invalid-tls"),
        pytest.param({**PUBLIC_CONFIGURATION, "host": f"smtp://{PUBLIC_HOST}"}, "invalid", id="invalid-host"),
        pytest.param({**PUBLIC_CONFIGURATION, "from": f"<{SENDER_ADDRESS}>, b@example.com"}, "invalid", id="invalid-from"),
        pytest.param({**PUBLIC_CONFIGURATION, "reply_to": f"{REPLY_TO_ADDRESS}, b@example.com"}, "invalid", id="invalid-reply-to"),
        pytest.param({**PUBLIC_CONFIGURATION, "password": None, "password_file": MISSING_FILE}, "invalid", id="invalid-password-file"),
        pytest.param({**PUBLIC_CONFIGURATION, "password": None}, "invalid", id="user-without-password"),
    ],
)
async def test_no_status_holds_the_smtp_configuration(private: _Private, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, network: list[str], variables: dict[str, str | None], state: str) -> None:
    """EMA-009 — contract 2: in every state — off with the rest set, ready (the plain-text warning, whose log summary names the host, included), invalid on the host, the sender, the Reply-To or the password file — the raw JSON of the status holds neither the host, the port, the user, the password, the sender, the Reply-To nor the folder of a password file; the status has its five keys and each check its four, no summary.

    Barrier first: the state is the one the case claims, so each case reads the state it is meant to.
    """
    print_section(f"EMA-009: no configuration in the {state} status")
    _configure(monkeypatch, variables, tmp_path)

    response = await _status_as_admin(private)

    body = response.json()
    assert body["state"] == state, f"barrier: the case must read the {state} state: {response.text}"
    assert set(body) == STATUS_KEYS and all(set(check) == CHECK_KEYS for check in body["checks"]), response.text
    leaked = _leaks(response.text, {**NOT_IN_A_STATUS, "the folder of the password file": str(tmp_path)})
    assert leaked == [], f"the status holds {leaked}: {response.text}"
    assert network == [], f"the status resolved {network}"
    print_success(f"{state}: nothing of the configuration")


# =============================================================================
# 3. POST /email/test
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("own", "language"),
    [
        pytest.param("it", "it", id="own-language-it"),
        pytest.param("it-IT", "it", id="own-regional-it-IT"),
        pytest.param("de", "es", id="own-unknown-de-is-unset-instance-es"),
        pytest.param(None, "es", id="no-row-instance-default-es"),
    ],
)
async def test_the_test_email_goes_to_the_administrator_in_their_language(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, own: str | None, language: str) -> None:
    """EMA-010 — contract 3: the instance's ``default_language`` is ``es`` and the member's own row ``fr``; the administrator's row says ``it``, its regional form ``it-IT``, ``de`` — a language the emails do not speak, so unset —, or there is none. 200 ``{language, message}``; the fake received one message, authenticated with the configured user, to the administrator's own address, from the configured sender with the configured Reply-To; its subject and text are the test email of ``language`` — the administrator's own when it names one of the four, else the instance's, never the member's —, the text naming the administrator and the instance (``test``, the host of ``http://test``); one unit spent; no secret in the answer.

    The precondition is verified: the expected subject differs from the English one, so an email always written in
    English could not pass.
    """
    print_section(f"EMA-010: the administrator's language, {language}")
    await _set_default_language(private.engine, "es")
    await _set_account_language(private.engine, private.member.id, "fr")
    if own is not None:
        await _set_account_language(private.engine, private.admin.id, own)
    expected = build_test_message(language=language, username=ADMIN, instance=INSTANCE_LABEL)
    assert expected.subject != build_test_message(language="en", username=ADMIN, instance=INSTANCE_LABEL).subject, f"precondition: the {language} subject must differ from the English one"

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        _point_at(monkeypatch, fake, user=SMTP_USER_NAME, password=SMTP_PASSWORD, reply_to=REPLY_TO_HEADER)
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            response = await client.post(SEND_TEST)

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    body = response.json()
    assert set(body) == {"language", "message"} and body["language"] == language, body
    assert isinstance(body["message"], str) and body["message"].strip(), body
    assert len(fake.messages) == 1
    received = fake.messages[0]
    assert (received.mail_from, received.rcpt_tos, received.user) == (SENDER_ADDRESS, [private.admin.email], SMTP_USER_NAME)
    message = received.message
    assert _mailboxes(message["From"]) == [SENDER]
    assert _mailboxes(message["To"]) == [("", private.admin.email)]
    assert _mailboxes(message["Reply-To"]) == [("Zq Support", REPLY_TO_ADDRESS)]
    assert message["Subject"] == expected.subject
    assert message["Content-Language"] == language
    text = message.get_body(preferencelist=("plain",)).get_content()
    assert _lines(text) == _lines(expected.text)
    assert ADMIN in text and INSTANCE_LABEL in text, f"the text must name the administrator and the instance: {text!r}"
    assert budget.count() == 1
    assert _leaks(response.text, NOT_IN_AN_ANSWER) == [], response.text
    print_success(f"{language}: {expected.subject!r} to {private.admin.email}")


@pytest.mark.asyncio
async def test_the_instance_is_the_host_the_request_was_sent_to(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str]) -> None:
    """EMA-011 — contract 3: a browser on ``http://zq-folio.example.com:8443``: the test email names ``zq-folio.example.com:8443`` — ``request.url.netloc``, the port included — and its text is exactly the English test email for that instance; the in-process transport resolved no name."""
    print_section("EMA-011: the instance is the request's host")
    host = "zq-folio.example.com:8443"
    expected = build_test_message(language="en", username=ADMIN, instance=host)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private, base_url=f"http://{host}") as client:
            await _sign_in(client, private.admin)
            response = await client.post(SEND_TEST)

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    assert len(fake.messages) == 1
    text = fake.messages[0].message.get_body(preferencelist=("plain",)).get_content()
    assert host in text, f"the text must name {host}: {text!r}"
    assert _lines(text) == _lines(expected.text)
    assert network == [], f"resolved {network}"
    print_success(f"the email names {host}")


@pytest.mark.asyncio
async def test_a_theme_this_version_does_not_know_still_gives_the_test_email_its_language(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-017 — contract 3: the instance says ``es``; once the administrator has signed in, their ``user_settings`` row says ``it`` with a theme this version does not know (``sepia``, written as a row). ``POST /email/test``: 200 ``{language: "it"}`` — not 422 —, one message, its subject and text the Italian test email; one unit spent; the row left as it was.

    Barrier first: the schema ``UserSettingsRead`` refuses that theme with a ``ValidationError`` naming it.
    """
    print_section("EMA-017: a theme this version does not know")
    refusal = str(_read_model_refusal())
    assert "theme" in refusal, f"barrier: the schema must refuse the theme: {refusal}"
    await _set_default_language(private.engine, "es")
    expected = build_test_message(language="it", username=ADMIN, instance=INSTANCE_LABEL)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            await _set_account_language(private.engine, private.admin.id, "it", theme=STALE_THEME)
            response = await client.post(SEND_TEST)

    assert response.status_code == 200, f"a theme this version does not know must not stop the test email: {response.status_code} {response.text}"
    assert response.json()["language"] == "it", response.text
    assert [received.message["Subject"] for received in fake.messages] == [expected.subject]
    assert _lines(fake.messages[0].message.get_body(preferencelist=("plain",)).get_content()) == _lines(expected.text)
    assert budget.count() == 1
    assert await _settings_row(private.engine, private.admin.id) == ("it", STALE_THEME), "the test email must leave the row as it was"
    print_success("200 in Italian from a row with a theme this version does not know; the row untouched")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "problem"),
    [
        pytest.param({"host": None}, "EMAIL_NOT_CONFIGURED", id="off"),
        pytest.param({"tls": "ssl"}, "SMTP_TLS_INVALID", id="tls-invalid"),
        pytest.param({"port": "65536"}, "SMTP_PORT_INVALID", id="port-invalid"),
        pytest.param({"from": None}, "SMTP_FROM_MISSING", id="from-missing"),
        pytest.param({"password": None}, "SMTP_CREDENTIALS_INCOMPLETE", id="user-without-password"),
        pytest.param({"host": f"smtp://{PUBLIC_HOST}"}, "SMTP_HOST_INVALID", id="host-invalid"),
        pytest.param({"host": PUBLIC_HOST, "tls": "ssl"}, "SMTP_TLS_INVALID", id="public-host-tls-invalid"),
    ],
)
async def test_email_off_or_unusable_answers_409_and_opens_no_connection(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, network: list[str], overrides: dict[str, str | None], problem: str) -> None:
    """EMA-012 — contract 3: every variable points at a running fake, with the SMTP user and password, but one: the host unset (off) or one value unusable. 409 ``{error_code: EMAIL_UNAVAILABLE, problem}``; the fake accepted no connection, nothing was spent, no name was resolved; the answer holds no password, user, host nor sender."""
    print_section(f"EMA-012: 409 {problem}")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake, **{"user": SMTP_USER_NAME, "password": SMTP_PASSWORD, **overrides})
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            response = await client.post(SEND_TEST)

    assert response.status_code == 409, f"{response.status_code} {response.text}"
    detail = _detail(response)
    assert (detail.get("error_code"), detail.get("problem")) == ("EMAIL_UNAVAILABLE", problem), detail
    assert (fake.connections, fake.messages, budget.count(), network) == (0, [], 0, [])
    assert _leaks(response.text, NOT_IN_AN_ANSWER) == [], response.text
    print_success(f"409 {problem}: no connection, nothing spent")


@pytest.mark.asyncio
@pytest.mark.parametrize(("elapsed", "wait"), SPENT)
async def test_a_spent_budget_answers_429_with_retry_after_and_opens_no_connection(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter, elapsed: float, wait: int) -> None:
    """EMA-013 — contract 3: ``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, the only unit spent by a test email at ``START``; ``elapsed`` seconds later the next one is 429 ``{error_code: EMAIL_RATE_LIMITED, retry_after}``, ``retry_after`` the integer ``ceil(3600 - elapsed)`` (at least 1) and ``Retry-After`` the same; no new connection, nothing more spent, no secret in the answer."""
    print_section(f"EMA-013: 429, {elapsed} s after the send")
    assert wait == math.ceil(WINDOW - elapsed) and wait >= 1, "precondition"

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        _point_at(monkeypatch, fake, user=SMTP_USER_NAME, password=SMTP_PASSWORD, max_per_hour="1")
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            clock.now = START
            first = await client.post(SEND_TEST)
            connections_before = fake.connections
            clock.now = START + elapsed
            refused = await client.post(SEND_TEST)

    assert first.status_code == 200 and connections_before == 1, f"setup: the only unit must go to a real send: {first.status_code} {first.text}"
    assert refused.status_code == 429, f"{refused.status_code} {refused.text}"
    detail = _detail(refused)
    retry_after = detail.get("retry_after")
    assert detail.get("error_code") == "EMAIL_RATE_LIMITED", detail
    assert type(retry_after) is int and retry_after == wait, f"retry_after must be the integer {wait}: {retry_after!r}"
    assert refused.headers.get("Retry-After") == str(wait), refused.headers
    assert (fake.connections, len(fake.messages), budget.count()) == (1, 1, 1)
    assert _leaks(refused.text, NOT_IN_AN_ANSWER) == [], refused.text
    print_success(f"429, retry after {wait} s, no connection")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "smtp_code", "server_words"),
    [
        pytest.param("recipient", "RECIPIENT_REFUSED", ("Recipient address rejected", "refused by the fake server", "5.1.1"), id="recipient-refused"),
        pytest.param("credentials", "AUTH_FAILED", ("Authentication credentials invalid", "5.7.8"), id="wrong-credentials"),
        pytest.param("closed-port", "CONNECTION_FAILED", ("ConnectionRefusedError", "Connection refused", "Errno"), id="closed-port"),
        pytest.param("sender", "SENDER_REFUSED", ("Sender refused", "5.7.1"), id="sender-refused"),
        pytest.param("data", "SEND_FAILED", ("Message refused", "5.6.0"), id="data-refused"),
        pytest.param("starttls", "TLS_FAILED", ("SMTPNotSupportedError", "STARTTLS extension not supported"), id="starttls-not-offered"),
    ],
)
async def test_a_refusal_of_the_smtp_server_answers_502_with_its_code(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, kind: str, smtp_code: str, server_words: tuple[str, ...]) -> None:
    """EMA-014 — contract 3: the server refuses the administrator's address, the configured password, the sender or the data, the port refuses connections, or ``starttls`` meets a server that does not offer it: 502 ``{error_code: EMAIL_DELIVERY_FAILED, smtp_code}``; the attempt cost its unit; the answer holds neither the password, the user, the host nor the server's own words.

    Barriers: where a fake runs, the refusal came on the one connection the send opened and no message was taken; for
    wrong credentials, the configured user and password are what reached the server.
    """
    print_section(f"EMA-014: 502 {smtp_code}")

    with _refusing(kind, monkeypatch, private.admin.email) as fake:
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            response = await client.post(SEND_TEST)

    assert response.status_code == 502, f"{response.status_code} {response.text}"
    detail = _detail(response)
    assert (detail.get("error_code"), detail.get("smtp_code")) == ("EMAIL_DELIVERY_FAILED", smtp_code), detail
    assert budget.count() == 1, "a refused attempt still costs its unit"
    if fake is not None:
        assert (fake.connections, fake.messages) == (1, []), f"barrier: {fake.connections} connection(s), {len(fake.messages)} message(s)"
    if kind == "credentials":
        assert fake.auth_attempts and set(fake.auth_attempts) == {(SMTP_USER_NAME, SMTP_PASSWORD)}, f"barrier: the configured credentials must reach the server: {fake.auth_attempts}"
    needles = {**NOT_IN_AN_ANSWER, **{f"the server's words {words!r}": words for words in server_words}}
    assert _leaks(response.text, needles) == [], response.text
    print_success(f"502 {smtp_code}, nothing of the server's words")


@pytest.mark.asyncio
async def test_an_administrator_whose_address_is_not_one_address_gets_422(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-015 — contract 3: an administrator whose stored address has no domain (a row no form would write, signing in by user name): 422 ``EMAIL_RECIPIENT_INVALID``; no connection, nothing spent. The 422 is the path of ``EmailRecipientError``: that is what the flow raised (``flows.send_test_email``, wrapped: the real one runs), exactly one, and it is a ``ValueError``."""
    print_section("EMA-015: 422 for an address that is not one address")
    odd = await _add_account(private.engine, "zq_oddmail", admin=True, email="zq-oddmail-without-a-domain")
    raised: list[BaseException] = []
    send_test_email = flows.send_test_email

    async def recording_send_test_email(*args: Any, **kwargs: Any) -> str:
        try:
            return await send_test_email(*args, **kwargs)
        except Exception as error:
            raised.append(error)
            raise

    monkeypatch.setattr(flows, "send_test_email", recording_send_test_email)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private) as client:
            await _sign_in(client, odd)
            response = await client.post(SEND_TEST)

    assert response.status_code == 422, f"{response.status_code} {response.text}"
    assert _detail(response).get("error_code") == "EMAIL_RECIPIENT_INVALID", response.text
    assert [type(error) for error in raised] == [EmailRecipientError], f"the 422 must come from an EmailRecipientError of the flow: {raised!r}"
    assert issubclass(EmailRecipientError, ValueError)
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("422 EMAIL_RECIPIENT_INVALID from an EmailRecipientError, a ValueError; nothing spent")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        pytest.param(lambda: ValueError("zq-an-unrelated-value-error"), id="plain-value-error"),
        pytest.param(_read_model_refusal, id="pydantic-validation-error"),
    ],
)
async def test_any_other_error_of_the_flow_is_not_the_recipient_422(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, error: Any) -> None:
    """EMA-018 — contract 3: email ready towards a running fake; reading the administrator's language fails (``flows.account_language`` replaced) with a ``ValueError`` that is not an ``EmailRecipientError`` — a plain one, or the pydantic ``ValidationError`` the read model raises for a settings row it refuses, the very error the 422 used to swallow. The answer is the unhandled 500, not the 422 ``EMAIL_RECIPIENT_INVALID``: no error is passed off as a bad address. No connection, nothing spent.

    The browser takes the 500 as a browser would (``raise_app_exceptions=False``); the precondition is verified: the
    injected error is a ``ValueError`` and not an ``EmailRecipientError``, so only the narrowed ``except`` tells them apart.
    """
    raised = error()
    print_section(f"EMA-018: {type(raised).__name__} is not the 422")
    assert isinstance(raised, ValueError) and not isinstance(raised, EmailRecipientError), f"precondition: {raised!r}"

    async def failing_account_language(*args: Any, **kwargs: Any) -> str:
        raise raised

    monkeypatch.setattr(flows, "account_language", failing_account_language)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private, raise_app_exceptions=False) as client:
            await _sign_in(client, private.admin)
            response = await client.post(SEND_TEST)

    assert response.status_code == 500, f"{type(raised).__name__} must stay an unhandled error: {response.status_code} {response.text}"
    assert "EMAIL_RECIPIENT_INVALID" not in response.text, response.text
    assert (fake.connections, fake.messages, budget.count()) == (0, [], 0)
    print_success(f"{type(raised).__name__}: 500, not EMAIL_RECIPIENT_INVALID; nothing spent")


# =============================================================================
# 4. OFF THE EVENT LOOP
# =============================================================================


@pytest.mark.asyncio
async def test_both_routes_read_the_configuration_off_the_event_loop(private: _Private, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """EMA-016 — contract 4: the password comes from ``LIBREFOLIO_SMTP_PASSWORD_FILE``; every read of it (``delivery.smtp_password``, wrapped) during ``GET /email/status`` and during ``POST /email/test`` happens on a thread that is not the loop's and runs no loop; the server saw that password.

    Barrier first: each route read the password at least once through ``delivery.smtp_password`` — otherwise «none on
    the loop» would hold for a route that never read it there.
    """
    print_section("EMA-016: configuration read off the event loop")
    password_file = tmp_path / "zq-smtp-password"
    password_file.write_text(f"{SMTP_PASSWORD}\n", encoding="utf-8")
    loop_thread = threading.get_ident()
    reads: list[tuple[int, bool]] = []
    read_password = delivery.smtp_password

    def recording_password() -> str | None:
        reads.append((threading.get_ident(), _loop_running()))
        return read_password()

    monkeypatch.setattr(delivery, "smtp_password", recording_password)

    with FakeSmtpServer(credentials=(SMTP_USER_NAME, SMTP_PASSWORD)) as fake:
        _point_at(monkeypatch, fake, user=SMTP_USER_NAME, password_file=str(password_file))
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            reads.clear()
            status = await client.get(STATUS)
            status_reads = list(reads)
            reads.clear()
            sent = await client.post(SEND_TEST)
            test_reads = list(reads)

    assert (status.status_code, status.json().get("state"), sent.status_code) == (200, "ready", 200), f"status {status.text}; test {sent.text}"
    assert status_reads and test_reads, f"barrier: a route never read the password through delivery.smtp_password (status {len(status_reads)}, test {len(test_reads)})"
    routes = {"GET /email/status": status_reads, "POST /email/test": test_reads}
    on_the_loop = {route: [(thread, running) for thread, running in route_reads if thread == loop_thread or running] for route, route_reads in routes.items()}
    assert on_the_loop == {"GET /email/status": [], "POST /email/test": []}, f"configuration reads on the event loop: {on_the_loop}"
    assert [message.user for message in fake.messages] == [SMTP_USER_NAME]
    print_success(f"status {len(status_reads)} read(s), test {len(test_reads)} read(s), none on the loop")


# =============================================================================
# 5. GET /system/instance: email.available
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("variables", "available"),
    [
        pytest.param({}, False, id="off-nothing-set"),
        pytest.param({**PUBLIC_CONFIGURATION, "host": None}, False, id="off-everything-else-set"),
        pytest.param(PUBLIC_CONFIGURATION, True, id="ready-starttls"),
        pytest.param({**PUBLIC_CONFIGURATION, "tls": "none"}, True, id="ready-plain-to-a-public-host"),
        pytest.param({**PUBLIC_CONFIGURATION, "password": None, "password_file": PASSWORD_IN_FILE}, True, id="ready-password-in-a-file"),
        pytest.param({**PUBLIC_CONFIGURATION, "port": "65536"}, False, id="invalid-port"),
        pytest.param({**PUBLIC_CONFIGURATION, "host": f"smtp://{PUBLIC_HOST}"}, False, id="invalid-host"),
        pytest.param({**PUBLIC_CONFIGURATION, "password": None, "password_file": MISSING_FILE}, False, id="unreadable-password-file"),
    ],
)
async def test_anyone_reads_whether_email_is_available_and_nothing_else_of_it(private: _Private, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, network: list[str], variables: dict[str, str | None], available: bool) -> None:
    """EMA-019 — contract 5: without a session, ``GET /system/instance`` answers 200 with ``email`` exactly ``{"available": available, "links": false}``, bools — ``available`` true for a usable configuration, plain text to a public host included, false when email is off (even with every other variable set), invalid or its password file cannot be read; ``links`` false, ``LIBREFOLIO_PUBLIC_URL`` being unset —; its raw JSON holds neither the host, the port, the user, the password, the sender, the Reply-To nor the folder of a password file, and no name was resolved."""
    print_section(f"EMA-019: /system/instance, available={available}")
    _configure(monkeypatch, variables, tmp_path)

    async with _browser(private) as client:
        response = await client.get(INSTANCE)

    assert response.status_code == 200, f"GET /system/instance is public: {response.status_code} {response.text}"
    email = response.json().get("email")
    assert email == {"available": available, "links": False} and type(email["available"]) is bool, f"email must be exactly {{'available': {available}, 'links': False}}: {response.text}"
    leaked = _leaks(response.text, {**NOT_IN_A_STATUS, "the folder of the password file": str(tmp_path)})
    assert leaked == [], f"the public configuration holds {leaked}: {response.text}"
    assert network == [], f"the public configuration resolved {network}"
    print_success(f"email {email}, nothing of the configuration")


@pytest.mark.asyncio
async def test_the_public_configuration_never_contacts_the_smtp_server(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str]) -> None:
    """EMA-020 — contract 5: email ready towards a running fake on the loopback, links ready: ``available`` and ``links`` are ``true`` and the fake accepted no connection — whether email works is read from the configuration, never by trying the server."""
    print_section("EMA-020: /system/instance never contacts the server")

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        async with _browser(private) as client:
            response = await client.get(INSTANCE)

    assert response.status_code == 200 and response.json().get("email") == {"available": True, "links": True}, f"{response.status_code} {response.text}"
    assert (fake.connections, network) == (0, []), f"the public configuration connected ({fake.connections}) or resolved {network}"
    print_success("available, no connection")


@pytest.mark.asyncio
async def test_the_public_configuration_reads_the_password_file_off_the_event_loop(private: _Private, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """EMA-021 — contract 5: the password comes from ``LIBREFOLIO_SMTP_PASSWORD_FILE``; every read of it (``delivery.smtp_password``, wrapped) during ``GET /system/instance`` happens on a thread that is not the loop's and runs no loop; the answer is ``available``.

    Barrier first: the route read the password at least once through ``delivery.smtp_password`` — otherwise «none on
    the loop» would hold for a route that never read it there.
    """
    print_section("EMA-021: /system/instance reads the configuration off the event loop")
    password_file = tmp_path / "zq-smtp-password"
    password_file.write_text(f"{SMTP_PASSWORD}\n", encoding="utf-8")
    loop_thread = threading.get_ident()
    reads: list[tuple[int, bool]] = []
    read_password = delivery.smtp_password

    def recording_password() -> str | None:
        reads.append((threading.get_ident(), _loop_running()))
        return read_password()

    monkeypatch.setattr(delivery, "smtp_password", recording_password)
    _configure(monkeypatch, {**PUBLIC_CONFIGURATION, "password": None, "password_file": str(password_file)})

    async with _browser(private) as client:
        response = await client.get(INSTANCE)

    assert response.status_code == 200 and response.json().get("email") == {"available": True, "links": False}, f"{response.status_code} {response.text}"
    assert reads, "barrier: GET /system/instance never read the password through delivery.smtp_password"
    on_the_loop = [(thread, running) for thread, running in reads if thread == loop_thread or running]
    assert on_the_loop == [], f"{len(on_the_loop)} of {len(reads)} configuration reads ran on the event loop: the password file must be read through asyncio.to_thread"
    print_success(f"{len(reads)} read(s), none on the loop")


def test_an_answer_built_without_email_says_email_is_off_and_the_openapi_does_not_require_it() -> None:
    """EMA-022 — contract 5: ``InstanceConfigResponse(profile=..., accounts=...)`` without ``email`` serializes ``email`` as ``{"available": false, "links": false}`` — an answer that forgets it, or a client reading an older server, says nothing can be sent —; and in the OpenAPI of the route the response schema lists ``email`` without requiring it, and ``EmailInstanceConfig`` declares ``available`` and ``links``, neither required."""
    print_section("EMA-022: email defaults to off and is optional in the OpenAPI")
    answer = InstanceConfigResponse(profile="selfhosted", accounts=AccountsInstanceConfig(registration_mode="open", registration_locked=False))
    app = FastAPI()
    app.include_router(instance_api.instance_router, prefix=f"{API_V1_PREFIX}/system")

    document = app.openapi()

    assert answer.model_dump(mode="json")["email"] == {"available": False, "links": False}, answer.model_dump(mode="json")
    reference = document["paths"][INSTANCE]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    schema = document["components"]["schemas"][reference.rsplit("/", 1)[-1]]
    assert "email" in schema["properties"], f"the response schema must declare email: {schema}"
    assert "email" not in schema.get("required", []), f"email must stay optional in the OpenAPI: {schema.get('required')}"
    email_schema = document["components"]["schemas"]["EmailInstanceConfig"]
    assert set(email_schema["properties"]) == INSTANCE_EMAIL_KEYS and not email_schema.get("required"), f"available and links, both optional: {email_schema}"
    print_success(f"email {answer.model_dump(mode='json')['email']}; required: {schema.get('required')}")


# =============================================================================
# 6. LINKS: GET /email/status links, GET /system/instance email.links
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("email_state", list(EMAIL_STATES))
@pytest.mark.parametrize(("public_url", "links", "usable_check"), LINK_STATES)
async def test_the_status_says_whether_emails_can_carry_links_whatever_the_state_of_email(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], email_state: str, public_url: str | None, links: dict[str, Any], usable_check: dict[str, Any]) -> None:
    """EMA-023 — contract 2: ``links`` is exactly ``{ready, base, problem}`` and says what ``LIBREFOLIO_PUBLIC_URL`` is now, whatever the state of email: ready with the base, one trailing slash removed; else no base and ``PUBLIC_URL_MISSING`` (unset or blank) or ``PUBLIC_URL_INVALID`` (not http(s)). The ``email.links`` check is ok while email is off or invalid; with email usable it is ok, ``info`` missing or ``warning`` invalid, with an empty detail. The value of an invalid variable is never echoed; nothing was resolved."""
    print_section(f"EMA-023: links {links['problem'] or 'ready'}, email {email_state}")
    _configure(monkeypatch, EMAIL_STATES[email_state])
    _set_public_url(monkeypatch, public_url)

    response = await _status_as_admin(private)
    body = response.json()

    assert body["state"] == email_state, body
    assert set(body["links"]) == LINKS_KEYS and body["links"] == links, body["links"]
    check = _checks(body)["email.links"]
    assert check == (usable_check if email_state == "ready" else LINKS_OK), body["checks"]
    assert "zq-not-public" not in response.text.casefold(), f"the status echoes an invalid LIBREFOLIO_PUBLIC_URL: {response.text}"
    assert network == [], f"the status resolved {network}"
    print_success(f"links {body['links']}, {check['severity']} {check['i18n_key']}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email_state", "public_url", "email"),
    [
        pytest.param("off", PUBLIC_URL, {"available": False, "links": False}, id="email-off-links-ready"),
        pytest.param("invalid", PUBLIC_URL, {"available": False, "links": False}, id="email-invalid-links-ready"),
        pytest.param("ready", None, {"available": True, "links": False}, id="links-missing"),
        pytest.param("ready", NOT_A_PUBLIC_URL, {"available": True, "links": False}, id="links-invalid"),
        pytest.param("ready", f"{PUBLIC_URL}/", {"available": True, "links": True}, id="email-and-links-ready"),
    ],
)
async def test_anyone_reads_whether_emails_with_a_link_can_go_out_never_the_public_url(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], email_state: str, public_url: str | None, email: dict[str, bool]) -> None:
    """EMA-024 — contract 5: without a session, ``email`` is exactly ``{available, links}``, two bools: ``links`` is true exactly when email is available and ``LIBREFOLIO_PUBLIC_URL`` is an http(s) address — links ready with email off or invalid is false —. The raw JSON never holds ``LIBREFOLIO_PUBLIC_URL``, valid or not — the base is for the administrator's status only —, nor anything of the SMTP configuration; no name was resolved."""
    print_section(f"EMA-024: /system/instance, email {email_state}, {email}")
    _configure(monkeypatch, EMAIL_STATES[email_state])
    _set_public_url(monkeypatch, public_url)

    async with _browser(private) as client:
        response = await client.get(INSTANCE)

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    body = response.json()["email"]
    assert set(body) == INSTANCE_EMAIL_KEYS and body == email and all(type(value) is bool for value in body.values()), response.text
    leaked = _leaks(response.text, {**NOT_IN_A_STATUS, "LIBREFOLIO_PUBLIC_URL": "zq-public", "an invalid LIBREFOLIO_PUBLIC_URL": "zq-not-public"})
    assert leaked == [], f"the public configuration holds {leaked}: {response.text}"
    assert network == [], f"the public configuration resolved {network}"
    print_success(f"email {body}, no address")


# =============================================================================
# 7. POST /email/links
# =============================================================================


@pytest.mark.asyncio
async def test_only_an_administrator_emails_a_link(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-025 — contract 6: email and links ready towards a running fake; a live invitation and a live reset link of the member. Without a session ``POST /email/links`` is 401 for both; for the member — whose session works (``GET /auth/me`` 200, the barrier) and whose own link one of them is — 403 for both. The fake accepted no connection, nothing was spent, both links are still live."""
    print_section("EMA-025: /email/links is for administrators")
    invitation = await _issue(private.engine, INVITE, email=GUEST, created_by_user_id=private.admin.id)
    reset = await _issue(private.engine, PASSWORD_RESET, user_id=private.member.id)
    bodies = [{"purpose": "invite", "token": invitation.token}, {"purpose": "password_reset", "token": reset.token}]

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        async with _browser(private) as anonymous:
            without = [(await anonymous.post(LINKS, json=body)).status_code for body in bodies]
        async with _browser(private) as member:
            await _sign_in(member, private.member)
            me = await member.get(ME)
            as_member = [(await member.post(LINKS, json=body)).status_code for body in bodies]

    assert me.status_code == 200 and me.json()["user"]["username"] == MEMBER, f"barrier: the member's session must work: {me.status_code} {me.text}"
    assert (without, as_member) == ([401, 401], [403, 403])
    assert (fake.connections, budget.count()) == (0, 0)
    statuses = (await _token_status(private.engine, invitation.token, INVITE), await _token_status(private.engine, reset.token, PASSWORD_RESET))
    assert statuses == (TokenStatus.VALID, TokenStatus.VALID), statuses
    print_success("401 and 403 for both; nothing sent, both links live")


@pytest.mark.asyncio
@pytest.mark.parametrize("token_kind", ["live", "never-issued"])
@pytest.mark.parametrize(
    ("email_state", "public_url", "error_code", "problem"),
    [
        pytest.param("off", PUBLIC_URL, "EMAIL_UNAVAILABLE", "EMAIL_NOT_CONFIGURED", id="email-off"),
        pytest.param("off", None, "EMAIL_UNAVAILABLE", "EMAIL_NOT_CONFIGURED", id="email-off-before-links-missing"),
        pytest.param("invalid", NOT_A_PUBLIC_URL, "EMAIL_UNAVAILABLE", "SMTP_TLS_INVALID", id="email-invalid-before-links-invalid"),
        pytest.param("ready", None, "EMAIL_LINKS_UNAVAILABLE", "PUBLIC_URL_MISSING", id="links-missing"),
        pytest.param("ready", "   ", "EMAIL_LINKS_UNAVAILABLE", "PUBLIC_URL_MISSING", id="links-blank"),
        pytest.param("ready", NOT_A_PUBLIC_URL, "EMAIL_LINKS_UNAVAILABLE", "PUBLIC_URL_INVALID", id="links-invalid"),
    ],
)
async def test_email_then_links_are_checked_before_the_token(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, email_state: str, public_url: str | None, error_code: str, problem: str, token_kind: str) -> None:
    """EMA-026 — contract 6: email off or unusable is 409 ``EMAIL_UNAVAILABLE`` with its problem, whatever the links; email usable with links missing or invalid is 409 ``EMAIL_LINKS_UNAVAILABLE`` with ``PUBLIC_URL_MISSING`` or ``PUBLIC_URL_INVALID``; both come before the token — a live invitation and a token never issued get the same answer. A fake runs: no connection, nothing spent, the live invitation still live; neither an invalid address nor the token is echoed."""
    print_section(f"EMA-026: email {email_state}, public URL {public_url!r}, {token_kind} token")
    token = (await _issue(private.engine, INVITE, email=GUEST, created_by_user_id=private.admin.id)).token if token_kind == "live" else NEVER_ISSUED

    with FakeSmtpServer() as fake:
        if email_state != "off":
            _point_at(monkeypatch, fake, tls="ssl" if email_state == "invalid" else "none")
        _set_public_url(monkeypatch, public_url)
        response = await _email_link_as_admin(private, "invite", token)

    assert response.status_code == 409, f"{response.status_code} {response.text}"
    detail = _detail(response)
    assert (detail.get("error_code"), detail.get("problem")) == (error_code, problem), detail
    assert (fake.connections, budget.count()) == (0, 0)
    if token_kind == "live":
        assert await _token_status(private.engine, token, INVITE) == TokenStatus.VALID
    assert "zq-not-public" not in response.text.casefold() and token not in response.text, response.text
    print_success(f"409 {error_code} {problem}")


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", list(PURPOSES))
@pytest.mark.parametrize("kind", DEAD_KINDS)
async def test_a_token_that_is_not_a_live_link_of_that_purpose_is_409_with_its_status(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, purpose: str, kind: str) -> None:
    """EMA-027 — contract 6: email and links ready; a token expired, consumed, revoked, never issued, or a live token of the other purpose: 409 ``{error_code: EMAIL_LINK_INVALID, status}`` with the status the token service gives — ``unknown`` for the other purpose's token —; nothing sent, nothing spent; the token is not in the answer."""
    print_section(f"EMA-027: {purpose}, {kind}")
    token = await _dead_token(private.engine, PURPOSES[purpose], kind, private.member.id)
    status = "unknown" if kind == "other-purpose" else kind

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        response = await _email_link_as_admin(private, purpose, token)

    assert response.status_code == 409, f"{response.status_code} {response.text}"
    detail = _detail(response)
    assert (detail.get("error_code"), detail.get("status")) == ("EMAIL_LINK_INVALID", status), detail
    assert (fake.connections, budget.count()) == (0, 0)
    assert token not in response.text, response.text
    print_success(f"409 EMAIL_LINK_INVALID {status}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "error_code"),
    [
        pytest.param("invitation-without-an-address", "EMAIL_RECIPIENT_REQUIRED", id="invitation-without-an-address"),
        pytest.param("invitation-written-to-two-addresses", "EMAIL_RECIPIENT_INVALID", id="invitation-written-to-two-addresses"),
        pytest.param("reset-link-to-another-address", "EMAIL_RECIPIENT_NOT_ALLOWED", id="reset-link-to-another-address"),
        pytest.param("reset-link-to-its-own-address", "EMAIL_RECIPIENT_NOT_ALLOWED", id="reset-link-to-its-own-address"),
    ],
)
async def test_a_recipient_that_cannot_be_used_is_422_before_anything_is_sent(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, case: str, error_code: str) -> None:
    """EMA-028 — contract 6: email and links ready, live tokens. An invitation without ``to`` and without an address written in it is 422 ``EMAIL_RECIPIENT_REQUIRED``; one written to two addresses (a row no form would write) 422 ``EMAIL_RECIPIENT_INVALID``; a reset link with a ``to`` — another address, or even its account's own — 422 ``EMAIL_RECIPIENT_NOT_ALLOWED``. No connection, nothing spent, the token still live."""
    print_section(f"EMA-028: {case}")
    if case.startswith("invitation"):
        purpose, name, fields = INVITE, "invite", {}
        written = None if case == "invitation-without-an-address" else f"{GUEST}, {OTHER_GUEST}"
        issued = await _issue(private.engine, INVITE, email=written, created_by_user_id=private.admin.id)
    else:
        purpose, name = PASSWORD_RESET, "password_reset"
        fields = {"to": OTHER_GUEST if case == "reset-link-to-another-address" else private.member.email}
        issued = await _issue(private.engine, PASSWORD_RESET, user_id=private.member.id)

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        response = await _email_link_as_admin(private, name, issued.token, **fields)

    assert response.status_code == 422, f"{response.status_code} {response.text}"
    assert _detail(response).get("error_code") == error_code, response.text
    assert (fake.connections, budget.count()) == (0, 0)
    assert await _token_status(private.engine, issued.token, purpose) == TokenStatus.VALID
    print_success(f"422 {error_code}, nothing sent")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"purpose": "signup"}, id="a-purpose-of-no-link"),
        pytest.param({"token": ""}, id="an-empty-token"),
        pytest.param({"to": f"{GUEST}, {OTHER_GUEST}"}, id="to-two-addresses"),
        pytest.param({"language": "de"}, id="a-language-outside-the-four"),
        pytest.param({"base": f"https://{ATTACKER_HOST}"}, id="a-base-of-the-callers-choice"),
        pytest.param({"link": f"https://{ATTACKER_HOST}/invite"}, id="a-link-of-the-callers-choice"),
    ],
)
async def test_a_body_outside_the_schema_is_refused_before_anything_is_sent(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, fields: dict[str, str]) -> None:
    """EMA-029 — contract 6: email and links ready, a live invitation. A body naming a purpose of no link, an empty token, a ``to`` that is not one address or a language outside the four — or carrying a field of its own, a ``base`` or a ``link``: the caller never chooses where a link points —: FastAPI's 422 (a list of errors); no connection, nothing spent, the invitation still live."""
    print_section(f"EMA-029: {sorted(fields)}")
    issued = await _issue(private.engine, INVITE, email=GUEST, created_by_user_id=private.admin.id)

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            response = await client.post(LINKS, json={"purpose": "invite", "token": issued.token, **fields})

    assert response.status_code == 422 and isinstance(response.json().get("detail"), list), f"{response.status_code} {response.text}"
    assert (fake.connections, budget.count()) == (0, 0)
    assert await _token_status(private.engine, issued.token, INVITE) == TokenStatus.VALID
    print_success("422, nothing sent")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("to", "language", "grants_admin", "recipient", "written_in"),
    [
        pytest.param(None, None, False, GUEST, "fr", id="to-its-address-in-the-instance-language"),
        pytest.param(OTHER_GUEST, "it", True, OTHER_GUEST, "it", id="to-the-address-given-in-the-language-given-with-the-admin-role"),
    ],
)
async def test_an_invitation_goes_out_with_the_public_url_link_and_nothing_of_the_request(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, to: str | None, language: str | None, grants_admin: bool, recipient: str, written_in: str) -> None:
    """EMA-030 — contract 6: the instance's ``default_language`` ``fr``; a live invitation written to GUEST, granting the administrator role or not; the request names a stranger's site as its Host, Origin, X-Forwarded-Host and Referer.

    200 ``{purpose: invite, to, language}``: to ``to`` when given, else to the invitation's address; in ``language``
    when given, else ``fr``. One message, from the configured sender, exactly ``build_invite`` for that language with
    the link ``{PUBLIC_URL}/invite#token=…``, the instance ``folio.zq-public.example.com:8443`` (the host of
    ``LIBREFOLIO_PUBLIC_URL``), the administrator as inviter and the role sentence exactly when the invitation grants
    it; every link a mail client opens is that one; nothing of the stranger's site anywhere in the message. One unit
    spent; the invitation is still live — emailing a link spends nothing of it —; the token is in no log event
    (barrier: ``Link emailed by an administrator`` with the token's id was captured).
    """
    print_section(f"EMA-030: an invitation to {recipient} in {written_in}")
    await _set_default_language(private.engine, "fr")
    issued = await _issue(private.engine, INVITE, email=GUEST, grants_admin=grants_admin, created_by_user_id=private.admin.id)
    link = f"{PUBLIC_URL}/invite#token={issued.token}"
    expected = build_invite(language=written_in, link=link, ttl=DEFAULT_TTL[INVITE], instance=PUBLIC_URL_HOST, inviter=ADMIN, grants_admin=grants_admin)
    fields = {name: value for name, value in (("to", to), ("language", language)) if value is not None}

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        with capture_logs() as events:
            response = await _email_link_as_admin(private, "invite", issued.token, headers=ATTACKER_HEADERS, **fields)

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    assert response.json() == {"purpose": "invite", "to": recipient, "language": written_in}, response.text
    assert [message.rcpt_tos for message in fake.messages] == [[recipient]], f"{len(fake.messages)} message(s)"
    received = fake.messages[0]
    assert _mailboxes(received.message["From"]) == [SENDER]
    _assert_is(received, expected)
    opened = [href for href in _hrefs(_html(received)) if "token=" in href]
    assert opened and set(opened) == {link}, f"the links a mail client opens: {opened}"
    assert _token_in(_text(received), INVITE) == issued.token
    assert _stranger_in(received) == [], f"the stranger's site is in {_stranger_in(received)}"
    assert budget.count() == 1
    assert await _token_status(private.engine, issued.token, INVITE) == TokenStatus.VALID
    emailed = [event.get("token_id") for event in events if event.get("event") == "Link emailed by an administrator"]
    assert emailed == [issued.record.id], f"barrier: the send is logged with the token's id: {events}"
    assert [event for event in events if issued.token in repr(event)] == [], "a log event holds the token"
    print_success(f"to {recipient}, in {written_in}, the PUBLIC_URL link")


@pytest.mark.asyncio
async def test_a_password_reset_link_goes_to_its_account_in_its_language_with_the_public_url_link(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-031 — contract 6: the member's live reset link, the member's language ``it``, the instance's ``fr``; the request names a stranger's site as its Host, Origin, X-Forwarded-Host and Referer.

    200 ``{purpose: password_reset, to: <the member's address>, language: it}``; one message, to the member's address,
    exactly ``build_password_reset`` in Italian with ``{PUBLIC_URL}/reset-password#token=…`` and the instance of
    ``LIBREFOLIO_PUBLIC_URL``, greeting nobody by name — the member's username in no part of it (decision N62) —; every
    link a mail client opens is that one; nothing of the stranger's site; one unit spent; the link still live, its token
    in no log event (barrier: the send was captured with its id).
    """
    print_section("EMA-031: a reset link to its account")
    await _set_default_language(private.engine, "fr")
    await _set_account_language(private.engine, private.member.id, "it")
    issued = await _issue(private.engine, PASSWORD_RESET, user_id=private.member.id, created_by_user_id=private.admin.id)
    link = f"{PUBLIC_URL}/reset-password#token={issued.token}"

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        with capture_logs() as events:
            response = await _email_link_as_admin(private, "password_reset", issued.token, headers=ATTACKER_HEADERS)

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    assert response.json() == {"purpose": "password_reset", "to": private.member.email, "language": "it"}, response.text
    assert [message.rcpt_tos for message in fake.messages] == [[private.member.email]], f"{len(fake.messages)} message(s)"
    received = fake.messages[0]
    assert _mailboxes(received.message["From"]) == [SENDER]
    assert MEMBER not in _text(received) + _html(received), "a reset email greets nobody by name: the username is text its owner chose (N62)"
    _assert_is(received, build_password_reset(language="it", link=link, ttl=DEFAULT_TTL[PASSWORD_RESET], instance=PUBLIC_URL_HOST))
    opened = [href for href in _hrefs(_html(received)) if "token=" in href]
    assert opened and set(opened) == {link}, f"the links a mail client opens: {opened}"
    assert _stranger_in(received) == [], f"the stranger's site is in {_stranger_in(received)}"
    assert budget.count() == 1
    assert await _token_status(private.engine, issued.token, PASSWORD_RESET) == TokenStatus.VALID
    emailed = [event.get("token_id") for event in events if event.get("event") == "Link emailed by an administrator"]
    assert emailed == [issued.record.id], f"barrier: the send is logged with the token's id: {events}"
    assert [event for event in events if issued.token in repr(event)] == [], "a log event holds the token"
    print_success("to the member, in it, the PUBLIC_URL link")


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", list(PURPOSES))
@pytest.mark.parametrize("failure", ["budget-spent", "recipient-refused"])
async def test_a_spent_budget_is_429_and_a_refusal_of_the_server_502_the_link_still_live(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter, purpose: str, failure: str) -> None:
    """EMA-032 — contract 6: the hourly budget spent (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, its unit spent at ``START``, the request 30.75 s later) is 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 3570 and the same ``Retry-After``, no connection, nothing more spent; the server refusing the recipient is 502 ``EMAIL_DELIVERY_FAILED`` ``RECIPIENT_REFUSED``, the unit spent, no message taken, neither the server's words nor the SMTP password, user, host or sender in the answer. Either way the link stays live: the administrator may send it again."""
    print_section(f"EMA-032: {purpose}, {failure}")
    issued = await _issue(private.engine, PURPOSES[purpose], **_owned(PURPOSES[purpose], private.member.id))
    recipient = GUEST if purpose == "invite" else private.member.email

    if failure == "budget-spent":
        with FakeSmtpServer() as fake:
            _links_ready(monkeypatch, fake, max_per_hour="1")
            clock.now = START
            assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
            clock.now = START + 30.75
            response = await _email_link_as_admin(private, purpose, issued.token)
        assert response.status_code == 429, f"{response.status_code} {response.text}"
        detail = _detail(response)
        assert (detail.get("error_code"), detail.get("retry_after")) == ("EMAIL_RATE_LIMITED", 3570), detail
        assert response.headers.get("Retry-After") == "3570", response.headers
        assert (fake.connections, budget.count()) == (0, 1)
    else:
        with _refusing("recipient", monkeypatch, recipient) as fake:
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
            response = await _email_link_as_admin(private, purpose, issued.token)
        assert response.status_code == 502, f"{response.status_code} {response.text}"
        detail = _detail(response)
        assert (detail.get("error_code"), detail.get("smtp_code")) == ("EMAIL_DELIVERY_FAILED", "RECIPIENT_REFUSED"), detail
        assert (fake.connections, fake.messages, budget.count()) == (1, [], 1)
        needles = {**NOT_IN_AN_ANSWER, **{f"the server's words {words!r}": words for words in RECIPIENT_REFUSAL_WORDS}}
        assert _leaks(response.text, needles) == [], response.text
    assert await _token_status(private.engine, issued.token, PURPOSES[purpose]) == TokenStatus.VALID
    print_success(f"{response.status_code} {detail.get('error_code')}, the link still live")


# =============================================================================
# 8. POST /email/password-reset
# =============================================================================


def _failures_of_the_work(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The warnings and errors the «forgot password» work logged."""
    return [event for event in events if str(event.get("event", "")).startswith("Forgotten password") and event.get("log_level") in ("warning", "error")]


@pytest.mark.asyncio
async def test_forgot_password_answers_the_same_for_an_active_an_inactive_and_an_unknown_account(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-033 — contract 7: email and links ready towards a running fake; no session. The member's username, the username of an inactive account and a name no account has each get 202 and the same body, ``{message}`` alone: status and body identical, nothing tells them apart. Once the three requests have returned, exactly one email went out, to the member; only the member has a reset row; one unit spent."""
    print_section("EMA-033: the same answer for everyone")
    dormant = await _add_account(private.engine, "zq_dormant", active=False)

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        answers = {kind: await _forgot(private, identifier) for kind, identifier in (("active", MEMBER), ("inactive", dormant.username), ("unknown", NOBODY))}

    shapes = {kind: (response.status_code, response.json()) for kind, response in answers.items()}
    assert shapes["active"][0] == 202 and set(shapes["active"][1]) == {"message"}, shapes
    assert shapes["inactive"] == shapes["active"] and shapes["unknown"] == shapes["active"], f"the answers tell the accounts apart: {shapes}"
    assert [message.rcpt_tos for message in fake.messages] == [[private.member.email]], f"{len(fake.messages)} message(s)"
    assert (len(await _reset_rows(private.engine, private.member.id)), await _reset_rows(private.engine, dormant.id)) == (1, [])
    assert budget.count() == 1
    print_success("202 three times, one body; one email, to the member")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("email_state", "public_url", "error_code", "problem"),
    [
        pytest.param("off", PUBLIC_URL, "EMAIL_UNAVAILABLE", "EMAIL_NOT_CONFIGURED", id="email-off"),
        pytest.param("invalid", PUBLIC_URL, "EMAIL_UNAVAILABLE", "SMTP_TLS_INVALID", id="email-invalid"),
        pytest.param("ready", None, "EMAIL_LINKS_UNAVAILABLE", "PUBLIC_URL_MISSING", id="links-missing"),
        pytest.param("ready", NOT_A_PUBLIC_URL, "EMAIL_LINKS_UNAVAILABLE", "PUBLIC_URL_INVALID", id="links-invalid"),
    ],
)
async def test_forgot_password_on_an_instance_that_cannot_send_it_is_409_without_the_problem(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits, email_state: str, public_url: str | None, error_code: str, problem: str) -> None:
    """EMA-034 — contract 7: for the member's username, email off or unusable is 409 ``EMAIL_UNAVAILABLE``, links missing or invalid 409 ``EMAIL_LINKS_UNAVAILABLE``; the refusal is exactly ``{error_code, message}``: the code of the configuration's problem, the name of a variable and an invalid address appear nowhere in it. No connection, nothing spent, nothing counted by either limiter, no reset row."""
    print_section(f"EMA-034: 409 {error_code}, {problem} kept out")

    with FakeSmtpServer() as fake:
        if email_state != "off":
            _point_at(monkeypatch, fake, tls="ssl" if email_state == "invalid" else "none")
        _set_public_url(monkeypatch, public_url)
        response = await _forgot(private, MEMBER)

    assert response.status_code == 409, f"{response.status_code} {response.text}"
    detail = _detail(response)
    assert set(detail) == {"error_code", "message"} and detail["error_code"] == error_code, detail
    assert _leaks(response.text, {"the problem": problem, "a variable": "LIBREFOLIO_", "an invalid address": "zq-not-public"}) == [], response.text
    assert (fake.connections, budget.count(), len(forgot_limits.by_address), len(forgot_limits.by_identifier)) == (0, 0, 0, 0)
    assert await _reset_rows(private.engine, private.member.id) == []
    print_success(f"409 {error_code}, no problem, nothing counted")


@pytest.mark.asyncio
async def test_forgot_password_allows_twenty_emails_per_client_address_in_an_hour(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, forgot_limits: ForgotLimits) -> None:
    """EMA-035 — contract 7: the counter per client address counts the emails that go, not the requests. From one IPv4 client address, twenty requests for twenty names no account has are 202 and leave the counter at 0. With the counter holding twenty emails since ``START``, a request 120 s later — for the member's username, with a forged ``X-Forwarded-For`` naming a second address — is 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 3480 and ``Retry-After: 3480`` (3600 - 120), and runs no work: the route counts the address the server gives the request (in production uvicorn rewrites it only for the proxies of ``FORWARDED_ALLOW_IPS``), never the header itself; a name no account has is refused alike. The second address, for real, gets 202 at once and the member their email, which counts one unit under it."""
    print_section("EMA-035: 20 emails per client address in an hour")

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        clock.now = START
        strangers = [await _forgot(private, f"{NOBODY}_{index}", client=FIRST_CLIENT) for index in range(20)]
        counted_by_the_strangers = forgot_limits.by_address.count(FIRST_CLIENT[0])
        for _email in range(20):
            assert delivery.address_budget_hit(FIRST_CLIENT[0]).allowed, "setup: twenty emails of the address"
        clock.now = START + 120
        refused = await _forgot(private, MEMBER, client=FIRST_CLIENT, headers={"X-Forwarded-For": SECOND_CLIENT[0]})
        refused_stranger = await _forgot(private, f"{NOBODY}_x", client=FIRST_CLIENT)
        sent_before = len(fake.messages)
        elsewhere = await _forgot(private, MEMBER, client=SECOND_CLIENT)

    assert [response.status_code for response in strangers] == [202] * 20, [response.text for response in strangers]
    assert counted_by_the_strangers == 0, "a request for a name no account has costs the counter nothing"
    assert refused.status_code == 429 and refused_stranger.status_code == 429, f"{refused.status_code} {refused.text}; {refused_stranger.status_code}"
    for response in (refused, refused_stranger):
        detail = _detail(response)
        assert (detail.get("error_code"), detail.get("retry_after")) == ("EMAIL_RATE_LIMITED", 3480), detail
        assert response.headers.get("Retry-After") == "3480", response.headers
    assert sent_before == 0, "the refused request ran the work"
    assert elsewhere.status_code == 202, f"{elsewhere.status_code} {elsewhere.text}"
    assert [message.rcpt_tos for message in fake.messages] == [[private.member.email]]
    assert (forgot_limits.by_address.count(FIRST_CLIENT[0]), forgot_limits.by_address.count(SECOND_CLIENT[0])) == (20, 1)
    print_success("202 twenty times for nobody, 0 counted; 429 for 3480 s whatever the header; another address 202 and one unit")


@pytest.mark.asyncio
async def test_forgot_password_answers_alike_whether_an_account_matches_and_counts_only_an_email_that_goes(private: _Private, monkeypatch: pytest.MonkeyPatch, forgot_limits: ForgotLimits) -> None:
    """EMA-053 — the answer never depends on the address's counter being spent by the work: a request for the member's username and one for a name no account has, from the same address, both answer 202 with the same body; the member's email goes and costs the counter one unit, the stranger's costs none. Fully full, the counter answers both alike, 429."""
    print_section("EMA-053: the same answer; only an email that goes is counted")
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "1")

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        stranger = await _forgot(private, f"{NOBODY}_a", client=FIRST_CLIENT)
        counted_after_the_stranger = forgot_limits.by_address.count(FIRST_CLIENT[0])
        member = await _forgot(private, MEMBER, client=FIRST_CLIENT)
        counted_after_the_member = forgot_limits.by_address.count(FIRST_CLIENT[0])
        member_again = await _forgot(private, MEMBER, client=FIRST_CLIENT)
        stranger_again = await _forgot(private, f"{NOBODY}_b", client=FIRST_CLIENT)

    assert (stranger.status_code, stranger.json()) == (member.status_code, member.json()) == (202, stranger.json())
    assert (counted_after_the_stranger, counted_after_the_member) == (0, 1)
    assert [message.rcpt_tos for message in fake.messages] == [[private.member.email]]
    assert (member_again.status_code, stranger_again.status_code) == (429, 429)
    assert _detail(member_again) == _detail(stranger_again), "a full counter answers alike whether an account matches"
    print_success("202 alike; 1 unit for the email that went; 429 alike once full")


@pytest.mark.asyncio
async def test_forgot_password_allows_three_requests_per_identifier_in_an_hour_whatever_its_case(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, forgot_limits: ForgotLimits) -> None:
    """EMA-036 — contract 7: the member's address written four ways — as stored, in capitals, title-cased between spaces, capitalised between a tab and a newline —, each from a client address of its own.

    The first three are 202 (the first at ``START``, the others 60 s later); the fourth, 60 s after the first, is 429
    ``EMAIL_RATE_LIMITED`` with ``retry_after`` 3540 and the same ``Retry-After``: the limit counts the identifier
    without case or surrounding spaces. One email in all, to the member, from the first request: the next two matched
    no account, or met the account's own limit.
    """
    print_section("EMA-036: 3 per identifier in an hour")
    address = private.member.email
    ways = [address, address.upper(), f"  {address.title()}  ", f"\t{address.capitalize()}\n"]
    clients = [(f"198.51.100.{20 + index}", 41000 + index) for index in range(len(ways))]

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        clock.now = START
        answers = [await _forgot(private, ways[0], client=clients[0])]
        clock.now = START + 60
        answers += [await _forgot(private, way, client=client) for way, client in zip(ways[1:], clients[1:], strict=True)]

    assert [response.status_code for response in answers] == [202, 202, 202, 429], [response.text for response in answers]
    detail = _detail(answers[3])
    assert (detail.get("error_code"), detail.get("retry_after")) == ("EMAIL_RATE_LIMITED", 3540), detail
    assert answers[3].headers.get("Retry-After") == "3540", answers[3].headers
    assert forgot_limits.by_identifier.count(address) == 3
    assert [message.rcpt_tos for message in fake.messages] == [[address]]
    print_success("202 three times, then 429 for 3540 s; one email")


@pytest.mark.asyncio
async def test_forgot_password_with_the_hourly_budget_spent_is_429_and_spends_nothing_more(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter) -> None:
    """EMA-037 — contract 7: ``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``, its only unit spent at ``START``; 30.75 s later a request for the member is 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 3570 and the same ``Retry-After``: the budget is only looked at — nothing more spent —; no connection, no reset row."""
    print_section("EMA-037: the hourly budget spent")

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake, max_per_hour="1")
        clock.now = START
        assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
        clock.now = START + 30.75
        response = await _forgot(private, MEMBER)

    assert response.status_code == 429, f"{response.status_code} {response.text}"
    detail = _detail(response)
    assert (detail.get("error_code"), detail.get("retry_after")) == ("EMAIL_RATE_LIMITED", 3570), detail
    assert response.headers.get("Retry-After") == "3570", response.headers
    assert (fake.connections, budget.count()) == (0, 1)
    assert await _reset_rows(private.engine, private.member.id) == []
    print_success("429 for 3570 s, nothing sent")


@pytest.mark.asyncio
@pytest.mark.parametrize("named_by", ["username", "email"])
async def test_forgot_password_emails_the_account_a_live_link_on_the_public_url(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, named_by: str) -> None:
    """EMA-038 — contract 7: the member's language ``es``, the instance's ``fr``; the member has a reset link made 10 minutes ago, still live.

    A request naming the member by username, or by address, with a stranger's site as its Host, Origin,
    X-Forwarded-Host and Referer: 202, and once it has returned one message went to the member's address — exactly
    ``build_password_reset`` in Spanish, greeting nobody by name (the member's username in no part of it: decision N62),
    with ``{PUBLIC_URL}/reset-password#token=…`` and the instance of ``LIBREFOLIO_PUBLIC_URL``; every link a mail
    client opens is that one; nothing of the stranger's site. Its token
    is a live reset link of the member, the earlier link is revoked, the member has those two rows; one unit spent.
    Neither the identifier nor the token is in any log event (barrier: ``Forgotten password: reset link emailed`` was
    captured).
    """
    print_section(f"EMA-038: forgot password, by {named_by}")
    await _set_default_language(private.engine, "fr")
    await _set_account_language(private.engine, private.member.id, "es")
    earlier = await _issue(private.engine, PASSWORD_RESET, user_id=private.member.id, now=utcnow() - timedelta(minutes=10))
    identifier = MEMBER if named_by == "username" else private.member.email

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        with capture_logs() as events:
            response = await _forgot(private, identifier, headers=ATTACKER_HEADERS)

    assert response.status_code == 202, f"{response.status_code} {response.text}"
    assert [message.rcpt_tos for message in fake.messages] == [[private.member.email]], f"{len(fake.messages)} message(s)"
    received = fake.messages[0]
    token = _token_in(_text(received), PASSWORD_RESET)
    link = f"{PUBLIC_URL}/reset-password#token={token}"
    assert _mailboxes(received.message["From"]) == [SENDER]
    assert MEMBER not in _text(received) + _html(received), "a reset email greets nobody by name: the username is text its owner chose (N62)"
    _assert_is(received, build_password_reset(language="es", link=link, ttl=DEFAULT_TTL[PASSWORD_RESET], instance=PUBLIC_URL_HOST))
    opened = [href for href in _hrefs(_html(received)) if "token=" in href]
    assert opened and set(opened) == {link}, f"the links a mail client opens: {opened}"
    assert _stranger_in(received) == [], f"the stranger's site is in {_stranger_in(received)}"
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        inspection = await token_service.inspect_token(session, token, PASSWORD_RESET)
    assert inspection.status == TokenStatus.VALID and inspection.record.user_id == private.member.id, inspection
    assert await _token_status(private.engine, earlier.token, PASSWORD_RESET) == TokenStatus.REVOKED
    assert [row.id for row in await _reset_rows(private.engine, private.member.id)] == [earlier.record.id, inspection.record.id]
    assert budget.count() == 1
    assert any(event.get("event") == "Forgotten password: reset link emailed" for event in events), f"barrier: the work's success is not among the captured events: {events}"
    leaked = [event for event in events if token in repr(event) or identifier in repr(event)]
    assert leaked == [], f"a log event holds the token or the identifier: {leaked}"
    print_success("one email to the member, the PUBLIC_URL link; the earlier link revoked")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "ages",
    [
        pytest.param((1,), id="a-link-a-minute-ago"),
        pytest.param((50, 30, 10), id="three-links-this-hour"),
    ],
)
async def test_forgot_password_past_the_limits_of_the_account_answers_the_same_and_sends_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, ages: tuple[int, ...]) -> None:
    """EMA-039 — contract 7: the member already has reset links made ``ages`` minutes ago — one a minute ago (within 5 minutes), or three within the hour, each older than 5 minutes —: a request for the member is 202 with the same body as one for a name no account has; nothing sent, nothing spent, no new row."""
    print_section(f"EMA-039: reset links {ages} minutes ago")
    made = [await _issue(private.engine, PASSWORD_RESET, user_id=private.member.id, now=utcnow() - timedelta(minutes=age)) for age in ages]

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        for_the_member = await _forgot(private, MEMBER)
        for_nobody = await _forgot(private, NOBODY)

    assert for_the_member.status_code == 202 and (for_the_member.status_code, for_the_member.json()) == (for_nobody.status_code, for_nobody.json()), f"{for_the_member.text} / {for_nobody.text}"
    assert (fake.connections, budget.count()) == (0, 0)
    assert [row.id for row in await _reset_rows(private.engine, private.member.id)] == [issued.record.id for issued in made]
    print_success("202 as for nobody; nothing sent, no new row")


@pytest.mark.asyncio
@pytest.mark.parametrize("gone", ["email", "links", "budget"])
async def test_forgot_password_whose_configuration_goes_away_before_the_work_makes_nothing_and_raises_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, gone: str) -> None:
    """EMA-040 — contract 7: the member has a live reset link an earlier request made ten minutes ago (no administrator made it); a request for the member is admitted with email and links ready and the budget whole (``LIBREFOLIO_SMTP_MAX_PER_HOUR=1``); between the admission and the work ``LIBREFOLIO_SMTP_HOST`` or ``LIBREFOLIO_PUBLIC_URL`` is removed, or the hourly budget's only unit is spent. 202; nothing raised out of the request (the transport would raise it here); no connection, no message; the work checks again and makes nothing — no new reset row, the earlier link still live —, and logs why it stopped (the barrier that it ran)."""
    print_section(f"EMA-040: {gone} gone before the work")
    earlier = await _issue(private.engine, PASSWORD_RESET, user_id=private.member.id, now=utcnow() - timedelta(minutes=10))
    admit = flows.admit_forgotten_password

    async def admit_then_lose_the_configuration(address: str | None, identifier: str) -> None:
        await admit(address, identifier)
        if gone == "budget":
            assert budget.hit(limit=1).allowed, "setup: the only unit of the hour, taken after the admission"
        else:
            monkeypatch.delenv(f"{SMTP_PREFIX}HOST" if gone == "email" else PUBLIC_URL_VARIABLE)

    monkeypatch.setattr(flows, "admit_forgotten_password", admit_then_lose_the_configuration)
    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake, max_per_hour="1")
        with capture_logs() as events:
            response = await _forgot(private, MEMBER)

    assert response.status_code == 202, f"{response.status_code} {response.text}"
    assert (fake.connections, fake.messages) == (0, [])
    failures = _failures_of_the_work(events)
    assert failures, f"barrier: the work ran and stopped on what was gone: {events}"
    assert [row.id for row in await _reset_rows(private.engine, private.member.id)] == [earlier.record.id], "nothing may be made when the email cannot go"
    assert await _token_status(private.engine, earlier.token, PASSWORD_RESET) == TokenStatus.VALID, "the earlier link must stay live"
    print_success(f"202, nothing made, nothing raised: {failures[-1]['event']}")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["recipient-refused", "closed-port", "value-error-while-building", "unexpected-error-while-building", "language-fails-after-reading"])
async def test_forgot_password_whose_email_fails_answers_202_raises_nothing_and_revokes_the_link(private: _Private, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    """EMA-041 — contract 7: email and links ready; after the work made the link, the server refuses the member's address, the port refuses connections, a ``ValueError`` or an unexpected ``RuntimeError`` happens while the email is built, or reading the member's language fails once it has queried the database. 202 — decided before the work —; nothing raised out of the request (the transport would raise it here); no message taken; the failure is logged (the barrier), without the identifier — an unexpected one as its type alone, without a traceback. Whatever stopped it, the link the work made — the member's only reset row — is revoked: no live link reaches nobody."""
    print_section(f"EMA-041: {failure}")

    def failing_builder(**arguments: object) -> object:
        raise ValueError("zq-value-error") if failure == "value-error-while-building" else RuntimeError("zq-unexpected failure")

    async def failing_language(session: AsyncSession, user_id: int) -> str:
        await session.execute(select(UserSettings.language).where(UserSettings.user_id == user_id))
        raise RuntimeError("zq-language failure")

    kind = "closed-port" if failure == "closed-port" else "recipient"
    refused = private.member.email if failure == "recipient-refused" else GUEST
    with _refusing(kind, monkeypatch, refused) as fake:
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
        if failure.endswith("while-building"):
            monkeypatch.setattr(flows, "build_password_reset", failing_builder)
        elif failure == "language-fails-after-reading":
            monkeypatch.setattr(flows, "account_language", failing_language)
        with capture_logs() as events:
            response = await _forgot(private, MEMBER)

    assert response.status_code == 202, f"{response.status_code} {response.text}"
    if fake is not None:
        assert fake.messages == [], f"{len(fake.messages)} message(s) taken"
    failures = _failures_of_the_work(events)
    assert failures, f"barrier: the failure must be logged: {events}"
    assert [event for event in events if MEMBER in repr(event)] == [], f"a log event holds the identifier: {events}"
    rows = await _reset_rows(private.engine, private.member.id)
    assert len(rows) == 1 and rows[0].revoked_at is not None, f"the link that reached nobody must be revoked: {[(row.id, row.revoked_at) for row in rows]}; the work logged {failures}"
    if failure in ("unexpected-error-while-building", "language-fails-after-reading"):
        logged = failures[-1]
        assert (logged.get("event"), logged.get("log_level"), logged.get("error")) == ("Forgotten password: the request failed", "error", "RuntimeError"), logged
        assert "exc_info" not in logged, f"an unexpected failure is logged as its type alone, without a traceback: {logged}"
    print_success(f"202, {failures[-1]['event']}, the link revoked, nothing raised")


# =============================================================================
# 9. A PUBLIC URL NO LINK CAN START FROM, A CLIENT WITHOUT AN ADDRESS, A BLOCKED INSTANCE
# =============================================================================

#: (an http(s) address no link can start from — it passes the scheme check alone —, its distinctive part: echoed, a leak).
NO_LINK_FROM_THEM = [
    pytest.param("https://", None, id="the-scheme-alone"),
    pytest.param("https://folio.zq-space.example.com/my folio", "zq-space", id="a-space-inside"),
    pytest.param("https://folio.zq-query.example.com/app?lang=it", "zq-query", id="a-query"),
    pytest.param("https://folio.zq-fragment.example.com/app#top", "zq-fragment", id="a-fragment"),
    pytest.param("https://folio.zq-qmark.example.com/app?", "zq-qmark", id="an-empty-query"),
    pytest.param("https://folio.zq-hash.example.com/app#", "zq-hash", id="an-empty-fragment"),
    pytest.param("https://folio.zq-port.example.com:99999/app", "zq-port", id="a-port-out-of-range"),
    pytest.param("https://folio.zq-port.example.com:abc/", "zq-port", id="a-port-that-is-not-a-number"),
    pytest.param("https://zq-user:zq-secret@folio.example.com/app", "zq-secret", id="credentials"),
    pytest.param("https://[::1", None, id="an-unclosed-ipv6-bracket"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("public_url", "core"), NO_LINK_FROM_THEM)
async def test_a_public_url_no_link_can_start_from_is_invalid_on_every_route(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits, public_url: str, core: str | None) -> None:
    """EMA-042 — contracts 2, 5, 6 and 7: email ready towards a running fake, ``LIBREFOLIO_PUBLIC_URL`` an http(s) address no link can start from.

    The status's ``links`` is ``{ready: false, base: null, problem: PUBLIC_URL_INVALID}`` and ``email.links`` the
    ``warning`` ``invalid``; ``/system/instance`` answers ``{available: true, links: false}``; emailing a live invitation
    is 409 ``EMAIL_LINKS_UNAVAILABLE`` with ``PUBLIC_URL_INVALID`` — never the 500 of a link the message builders
    refuse —, the invitation still live; «forgot password» is 409 ``EMAIL_LINKS_UNAVAILABLE`` without a problem, nothing
    counted. No answer echoes the value; no connection, nothing spent, no reset row.
    """
    print_section(f"EMA-042: LIBREFOLIO_PUBLIC_URL={public_url!r}")
    issued = await _issue(private.engine, INVITE, email=GUEST, created_by_user_id=private.admin.id)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)
        async with _browser(private, raise_app_exceptions=False) as client:
            await _sign_in(client, private.admin)
            status = await client.get(STATUS)
            sent = await client.post(LINKS, json={"purpose": "invite", "token": issued.token})
        async with _browser(private, raise_app_exceptions=False) as anonymous:
            instance = await anonymous.get(INSTANCE)
            forgot = await anonymous.post(FORGOT, json={"identifier": MEMBER})

    assert status.status_code == 200 and status.json()["links"] == {"ready": False, "base": None, "problem": "PUBLIC_URL_INVALID"}, f"{status.status_code} {status.text}"
    assert _checks(status.json())["email.links"] == LINKS_INVALID, status.json()["checks"]
    assert instance.status_code == 200 and instance.json()["email"] == {"available": True, "links": False}, f"{instance.status_code} {instance.text}"
    assert sent.status_code == 409, f"{sent.status_code} {sent.text}"
    assert (_detail(sent).get("error_code"), _detail(sent).get("problem")) == ("EMAIL_LINKS_UNAVAILABLE", "PUBLIC_URL_INVALID"), sent.text
    assert forgot.status_code == 409, f"{forgot.status_code} {forgot.text}"
    assert set(_detail(forgot)) == {"error_code", "message"} and _detail(forgot)["error_code"] == "EMAIL_LINKS_UNAVAILABLE", forgot.text
    if core is not None:
        echoed = [name for name, response in (("the status", status), ("/system/instance", instance), ("/email/links", sent), ("«forgot password»", forgot)) if core in response.text]
        assert echoed == [], f"the value is echoed by {echoed}"
    assert (fake.connections, budget.count(), len(forgot_limits.by_address), len(forgot_limits.by_identifier)) == (0, 0, 0, 0)
    assert await _token_status(private.engine, issued.token, INVITE) == TokenStatus.VALID
    assert await _reset_rows(private.engine, private.member.id) == []
    print_success("invalid on every route, never echoed, nothing sent")


@pytest.mark.asyncio
async def test_forgot_password_from_a_client_without_an_address_is_limited_per_identifier_only(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, forgot_limits: ForgotLimits) -> None:
    """EMA-043 — contract 7: requests whose client the server cannot name — no ``client`` in the ASGI scope, as on a unix socket —: twenty-one for twenty-one names no account has are 202, more than the twenty one address may make, and the limiter per address holds no key, not even a shared one; three for the member's username are 202 and the fourth, a minute later, is 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 3540 and the same ``Retry-After``: the limit per identifier still holds. The member got exactly one email, from the first of the three."""
    print_section("EMA-043: no client address")

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        clock.now = START
        strangers = [await _forgot(private, f"{NOBODY}_{index}", client=None) for index in range(21)]
        for_the_member = [await _forgot(private, MEMBER, client=None) for _ in range(3)]
        clock.now = START + 60
        refused = await _forgot(private, MEMBER, client=None)

    answered = strangers + for_the_member
    assert [response.status_code for response in answered] == [202] * len(answered), [response.text for response in answered]
    assert len(forgot_limits.by_address) == 0, "a request without an address must be counted under no key"
    assert refused.status_code == 429, f"{refused.status_code} {refused.text}"
    detail = _detail(refused)
    assert (detail.get("error_code"), detail.get("retry_after")) == ("EMAIL_RATE_LIMITED", 3540), detail
    assert refused.headers.get("Retry-After") == "3540", refused.headers
    assert [message.rcpt_tos for message in fake.messages] == [[private.member.email]]
    print_success("202 for every request without an address, no key per address; the fourth for one identifier 429")


@pytest.mark.asyncio
async def test_on_a_blocked_instance_the_routes_send_nothing_and_say_why(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter, forgot_limits: ForgotLimits) -> None:
    """EMA-044 — contracts 6 and 7: email and links ready towards a running fake, the administrator signed in; then ``LIBREFOLIO_BLOCKED=1`` on this app, which mounts no instance-block guard — the routes the guard of ``/api/v1`` would refuse, reached anyway —: ``POST /email/test`` and ``POST /email/links`` for a live invitation are 409 ``{error_code: EMAIL_UNAVAILABLE, problem: INSTANCE_BLOCKED}``, the sending itself refusing; «forgot password» for the member is 409 ``EMAIL_UNAVAILABLE`` without a problem, refused at the admission: nothing counted, no work, no reset row. No connection, nothing spent, the invitation still live."""
    print_section("EMA-044: a blocked instance")
    issued = await _issue(private.engine, INVITE, email=GUEST, created_by_user_id=private.admin.id)

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            monkeypatch.setenv(BLOCKED_VARIABLE, "1")
            tested = await client.post(SEND_TEST)
            linked = await client.post(LINKS, json={"purpose": "invite", "token": issued.token})
        forgot = await _forgot(private, MEMBER)

    for response in (tested, linked):
        assert response.status_code == 409, f"{response.status_code} {response.text}"
        assert (_detail(response).get("error_code"), _detail(response).get("problem")) == ("EMAIL_UNAVAILABLE", "INSTANCE_BLOCKED"), response.text
    assert forgot.status_code == 409, f"{forgot.status_code} {forgot.text}"
    assert set(_detail(forgot)) == {"error_code", "message"} and _detail(forgot)["error_code"] == "EMAIL_UNAVAILABLE", forgot.text
    assert (fake.connections, budget.count(), len(forgot_limits.by_address), len(forgot_limits.by_identifier)) == (0, 0, 0, 0)
    assert await _token_status(private.engine, issued.token, INVITE) == TokenStatus.VALID
    assert await _reset_rows(private.engine, private.member.id) == []
    print_success("409 INSTANCE_BLOCKED twice, 409 for «forgot password»; nothing sent, nothing made")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("block", "email"),
    [
        pytest.param("1", {"available": False, "links": False}, id="blocked"),
        pytest.param("maybe", {"available": False, "links": False}, id="unreadable"),
        pytest.param("0", {"available": True, "links": True}, id="not-blocked"),
    ],
)
async def test_a_blocked_instance_offers_no_email_in_its_public_configuration(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], block: str, email: dict[str, bool]) -> None:
    """EMA-045 — contract 5: email and links ready (towards a host never contacted), ``LIBREFOLIO_BLOCKED`` blocking or unreadable: ``GET /system/instance`` — which answers on a blocked instance — gives ``email`` ``{available: false, links: false}``: nothing can be sent, so nothing is offered; ``0`` does not block, and both are true. No session, nothing resolved."""
    print_section(f"EMA-045: /system/instance, LIBREFOLIO_BLOCKED={block!r}")
    _configure(monkeypatch, PUBLIC_CONFIGURATION)
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    monkeypatch.setenv(BLOCKED_VARIABLE, block)

    async with _browser(private) as client:
        response = await client.get(INSTANCE)

    assert response.status_code == 200, f"{response.status_code} {response.text}"
    assert response.json()["email"] == email, response.text
    assert network == [], f"the public configuration resolved {network}"
    print_success(f"email {response.json()['email']}")


# =============================================================================
# 10. AFTER THE SECURITY REVIEW OF E3
# =============================================================================


@pytest.mark.asyncio
async def test_forgot_password_counts_an_ipv6_client_by_its_64_and_a_mapped_ipv4_as_the_ipv4(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, forgot_limits: ForgotLimits) -> None:
    """EMA-047 — contract 7: twenty emails spent from twenty addresses of one IPv6 /64 (``delivery.address_budget_hit``) fill one count; a request from yet another address of that /64 is 429 — one subscriber, one count —, while an address of the next /64 gets 202. Likewise an IPv4 client and its IPv4-mapped form share one count: twenty emails from the two in turn fill it, the next request is 429. The counts are under ``2001:db8:1:2::/64`` and ``198.51.100.70``."""
    print_section("EMA-047: IPv6 by its /64, a mapped IPv4 as the IPv4")

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        clock.now = START
        for index in range(20):
            assert delivery.address_budget_hit(f"2001:db8:1:2::{index + 1:x}").allowed, "setup: twenty emails of one /64"
        same_64 = [202] * 20
        one_more = await _forgot(private, f"{NOBODY}_v6_10", client=("2001:db8:1:2:ffff::1", 40010))
        next_64 = await _forgot(private, f"{NOBODY}_v6_11", client=("2001:db8:1:3::1", 40011))
        for address in ["198.51.100.70", "::ffff:198.51.100.70"] * 10:
            assert delivery.address_budget_hit(address).allowed, "setup: twenty emails of an IPv4 address and its mapped form"
        both_forms = [202] * 20
        mapped_more = await _forgot(private, f"{NOBODY}_v4_10", client=("::ffff:198.51.100.70", 41010))

    assert same_64 == [202] * 20
    assert (one_more.status_code, next_64.status_code) == (429, 202), f"{one_more.status_code} {one_more.text}; {next_64.status_code} {next_64.text}"
    assert both_forms == [202] * 20
    assert mapped_more.status_code == 429, f"{mapped_more.status_code} {mapped_more.text}"
    assert (forgot_limits.by_address.count("2001:db8:1:2::/64"), forgot_limits.by_address.count("198.51.100.70")) == (20, 20)
    assert fake.messages == []
    print_success("one count per /64, one count for an IPv4 address and its mapped form")


@pytest.mark.asyncio
async def test_a_reset_link_of_an_inactive_account_is_409_and_not_emailed(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-048 — contract 6: email and links ready towards a running fake; the administrator emails the live reset link of an inactive account: 409 ``{error_code: EMAIL_ACCOUNT_INACTIVE}`` — it would set a password nobody can use yet —; no connection, nothing spent, the link still live."""
    print_section("EMA-048: a reset link of an inactive account")
    dormant = await _add_account(private.engine, "zq_dormant", active=False)
    issued = await _issue(private.engine, PASSWORD_RESET, user_id=dormant.id, created_by_user_id=private.admin.id)

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        response = await _email_link_as_admin(private, "password_reset", issued.token)

    assert response.status_code == 409, f"{response.status_code} {response.text}"
    assert _detail(response).get("error_code") == "EMAIL_ACCOUNT_INACTIVE", response.text
    assert (fake.connections, budget.count()) == (0, 0)
    assert await _token_status(private.engine, issued.token, PASSWORD_RESET) == TokenStatus.VALID
    print_success("409 EMAIL_ACCOUNT_INACTIVE, nothing sent, the link live")


# =============================================================================
# 11. «FORGOT PASSWORD» SHIPS OPEN (lot E4b)
# =============================================================================


@pytest.mark.asyncio
async def test_forgot_password_ships_open_with_email_and_a_public_url(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-049 — contract 7: as shipped — ``flows`` carries no hold any more (no ``FORGOT_PASSWORD_HELD``, no ``ForgottenPasswordHeldError``) and nothing in this module lifts one —, email ready towards a running fake and ``LIBREFOLIO_PUBLIC_URL`` set: ``POST /email/password-reset`` for the member's username, without a session, is 202 ``{message}``; once it has returned one email went to the member's address, carrying a ``{PUBLIC_URL}/reset-password#token=…`` link whose token is a live reset link of the member, its only reset row; one unit of the budget spent. Where the hold used to answer first (EMA-046, removed with it) the configuration now answers, as EMA-034 (email off or unusable, links missing or invalid) and EMA-044 (a blocked instance) pin."""
    print_section("EMA-049: «forgot password» ships open")
    leftovers = [name for name in ("FORGOT_PASSWORD_HELD", "ForgottenPasswordHeldError") if hasattr(flows, name)]

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        response = await _forgot(private, MEMBER)

    assert leftovers == [], f"«forgot password» ships open since lot E4: flows still carries {leftovers}"
    assert (response.status_code, set(response.json())) == (202, {"message"}), f"{response.status_code} {response.text}"
    assert [message.rcpt_tos for message in fake.messages] == [[private.member.email]], f"{len(fake.messages)} message(s)"
    token = _token_in(_text(fake.messages[0]), PASSWORD_RESET)
    rows = await _reset_rows(private.engine, private.member.id)
    assert await _token_status(private.engine, token, PASSWORD_RESET) == TokenStatus.VALID
    assert len(rows) == 1, f"the member's reset rows: {[row.id for row in rows]}"
    assert budget.count() == 1
    print_success("202, one email to the member with a live reset link on the public URL")


# =============================================================================
# 12. BEHIND A PROXY LIBREFOLIO DOES NOT TRUST (DECISION N70, LOT E-13)
# =============================================================================

#: The address every request comes from behind a reverse proxy LibreFolio does not trust: the proxy's own, private —
#: the Docker bridge's, or an IPv6 unique-local one. Any port: the key of an address never holds it.
PRIVATE_PROXIES = [pytest.param("172.17.0.1", id="docker-bridge-ipv4"), pytest.param("fd00::2", id="unique-local-ipv6")]
PROXY_PORT = 40100
#: Two visitors, as a forwarding header names them: A asks first, B after.
VISITOR_A = "203.0.113.10"
VISITOR_B = "203.0.113.20"
#: A device of the local network that talks to LibreFolio directly: a private address, and no forwarding header.
LAN_DEVICE = ("192.168.1.5", 40200)
#: H-36's forwarding headers, exactly its list: (the header, what precedes the address in it). A reverse proxy writes
#: them for the visitor it forwards.
FORWARDING_HEADERS = [
    pytest.param("X-Forwarded-For", "", id="x-forwarded-for"),
    pytest.param("Forwarded", "for=", id="forwarded"),
    pytest.param("X-Real-IP", "", id="x-real-ip"),
]
#: The forwarding headers a client at a public address may write itself: the same three.
OWN_FORWARDING_HEADERS = FORWARDING_HEADERS


def _one_request_an_hour(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """One request an hour per client address, on a private counter on the fake clock: the limit is ``LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS=1``, which a request reads when it asks — the counter's own limit is not what decides."""
    monkeypatch.setenv(SIGNUP_PER_ADDRESS, "1")
    limiter = SlidingWindowLimiter(1, SHIPPED_BY_ADDRESS.window_seconds, clock=clock)
    monkeypatch.setattr(delivery, "ADDRESS_BUDGET", limiter)
    return limiter


@pytest.mark.asyncio
@pytest.mark.parametrize(("header", "prefix"), FORWARDING_HEADERS)
@pytest.mark.parametrize("proxy", PRIVATE_PROXIES)
async def test_forgot_password_two_visitors_behind_one_private_proxy_do_not_share_a_budget(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, proxy: str, header: str, prefix: str) -> None:
    """EMA-050 — contract 8, red before the cure of decision N70 (H-36's ``rate_limit_address``): ``delivery.ADDRESS_BUDGET`` at one request for this test — the limiter per identifier the fixture's, with its shipped limit —, email and links ready towards a running fake. Both requests come from the proxy's private address — ``172.17.0.1``, the Docker bridge; ``fd00::2``, an IPv6 unique-local one —, each with a forwarding header naming its visitor and each for another name no account has. Visitor A: 202. Visitor B, through the same proxy: 202 too, the same body, never 429. Then the skip itself, which B's answer alone would not prove: the limiter per address holds no key at all — neither visitor counted under an address, the proxy's or their own. Nothing sent. The headers are exactly H-36's list — ``X-Forwarded-For``, ``Forwarded`` (``for=…``), ``X-Real-IP`` —, crossed with the two peers: six cases."""
    print_section(f"EMA-050: two visitors behind {proxy}, {header}")
    by_address = _one_request_an_hour(monkeypatch, clock)
    peer = (proxy, PROXY_PORT)
    assert delivery.address_budget_hit(proxy).allowed, "setup: the only unit of the proxy's own address is spent, so a request counted under it would be refused"

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        first = await _forgot(private, f"{NOBODY}_a", client=peer, headers={header: f"{prefix}{VISITOR_A}"})
        second = await _forgot(private, f"{NOBODY}_b", client=peer, headers={header: f"{prefix}{VISITOR_B}"})

    assert (first.status_code, set(first.json())) == (202, {"message"}), f"barrier: visitor A is admitted: {first.status_code} {first.text}"
    assert second.status_code != 429, f"two visitors behind one private proxy ({proxy}) shared one per-address budget: visitor B was refused because visitor A had asked: {second.text}"
    assert (second.status_code, second.json()) == (202, first.json()), f"{second.status_code} {second.text}"
    assert len(by_address) == 1, f"a request through a reverse proxy LibreFolio does not trust ({proxy}, {header}) is counted under no address (N70): the limiter per address holds {len(by_address)} key(s)"
    assert untrusted_forwarding_seen("local") == (header,), f"N70's skip notes the {header} of a local peer: noted {untrusted_forwarding_seen('local')}"
    assert fake.messages == []
    print_success("202 for each visitor, and no key in the limiter per address: the skip")


@pytest.mark.asyncio
@pytest.mark.parametrize(("header", "prefix"), OWN_FORWARDING_HEADERS)
async def test_forgot_password_a_public_clients_own_forwarding_header_moves_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, header: str, prefix: str) -> None:
    """EMA-051 — contract 8, a guard, green before and after the cure: ``delivery.ADDRESS_BUDGET`` at one request for this test, email and links ready towards a running fake. A client at the public address ``198.51.100.7`` writes a forwarding header itself — ``X-Forwarded-For``, ``Forwarded`` (``for=…``) or ``X-Real-IP`` —, naming ``203.0.113.10``, then ``203.0.113.20``, each time for another name no account has: 202, then 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 3600 and ``Retry-After: 3600`` — the whole window, counted from the first —: what a client writes never moves its own budget, as EMA-035 pins at the shipped limit. Nothing sent. The forwarding headers that count follow H-36, and the cure may extend the parametrization."""
    print_section(f"EMA-051: a public client's own {header}")
    _one_request_an_hour(monkeypatch, clock)
    assert delivery.address_budget_hit(FIRST_CLIENT[0]).allowed, "setup: the only unit of the client's real address is spent"

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        first = await _forgot(private, f"{NOBODY}_a", client=FIRST_CLIENT, headers={header: f"{prefix}{VISITOR_A}"})
        second = await _forgot(private, f"{NOBODY}_b", client=FIRST_CLIENT, headers={header: f"{prefix}{VISITOR_B}"})

    assert first.status_code == 429, f"a client at a public address chose its own budget with a {header} header it wrote itself: {first.status_code} {first.text}"
    assert second.status_code == 429, f"a client at a public address chose its own budget with a {header} header it wrote itself: {second.status_code} {second.text}"
    detail = _detail(second)
    assert (detail.get("error_code"), detail.get("retry_after")) == ("EMAIL_RATE_LIMITED", 3600), detail
    assert second.headers.get("Retry-After") == "3600", second.headers
    assert fake.messages == []
    print_success(f"429 twice whatever its own {header} says")


@pytest.mark.asyncio
async def test_forgot_password_a_private_client_without_a_forwarding_header_keeps_its_own_budget(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> None:
    """EMA-052 — contract 8, a guard, green before and after the cure: ``delivery.ADDRESS_BUDGET`` at one request for this test, email and links ready towards a running fake. A device of the local network talks to LibreFolio directly — the private address ``192.168.1.5``, no forwarding header —, each time for another name no account has: 202, then 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 3600 and ``Retry-After: 3600``: a private address alone is not a proxy, and keeps its own budget. Nothing sent. The forwarding headers that count follow H-36, and the cure may extend the parametrization."""
    print_section("EMA-052: a device of the local network")
    _one_request_an_hour(monkeypatch, clock)
    assert delivery.address_budget_hit(LAN_DEVICE[0]).allowed, "setup: the only unit of the device's address is spent"

    with FakeSmtpServer() as fake:
        _links_ready(monkeypatch, fake)
        first = await _forgot(private, f"{NOBODY}_a", client=LAN_DEVICE)
        second = await _forgot(private, f"{NOBODY}_b", client=LAN_DEVICE)

    assert first.status_code == 429, f"{first.status_code} {first.text}"
    assert second.status_code == 429, f"a private address without a forwarding header lost its own budget: {second.status_code} {second.text}"
    detail = _detail(second)
    assert (detail.get("error_code"), detail.get("retry_after")) == ("EMAIL_RATE_LIMITED", 3600), detail
    assert second.headers.get("Retry-After") == "3600", second.headers
    assert fake.messages == []
    print_success("429: its own budget")
