"""Email administration API — ``GET /email/status`` and ``POST /email/test`` (plan phase01Email §3.3, decisions D-E4, D-E5, D-E9, lot E2a).

An administrator sees whether the instance's email is off, ready or unusable — never its configuration — and sends a
test email to their own address. The routes are in ``backend/app/api/v1/email.py``, the schemas in ``schemas/email.py``.
The contract pinned here:

1. Admin only: both routes answer 401 without a session and 403 to a signed-in account that is not an administrator,
   and then send nothing and spend nothing; an administrator gets 200 from both.
2. ``GET /email/status`` answers ``{state, problem, variable, checks, budget}``, each check ``{check_id, severity,
   i18n_key, detail}`` — the two of ``EMAIL_CONFIG_CHECKS``, never their log summary:
   - off (no host, whatever else is set): ``state="off"``, no problem, no variable, no budget; ``email.smtp`` ok
     ``email.checks.smtp.off``, ``email.smtp_encryption`` ok ``email.checks.smtpEncryption.ok``;
   - invalid: ``state="invalid"``, the problem and the variable at fault, no budget; ``email.smtp`` error
     ``email.checks.smtp.invalid`` with ``detail == {problem, variable}``, the encryption check ok;
   - ready: ``state="ready"``, no problem, no variable; ``email.smtp`` ok ``email.checks.smtp.ok``; the encryption check
     ok — ``localPlain`` for plain text to the loopback —, or a ``warning`` ``email.checks.smtpEncryption.plain`` with an
     empty detail for plain text to a host outside the local network;
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
   - a settings row the read model ``UserSettingsRead`` refuses (a theme outside light/dark/auto) still gives its
     language: 200, not 422;
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
5. ``GET /system/instance`` carries ``email: {available}``, public — no session —: ``true`` exactly when the configuration
   can be used (a host set and every variable usable, plain text to a public host included), ``false`` when email is
   off, invalid (a bad port, a bad host) or its password file cannot be read. It never holds the host, the port, the
   user, the sender, the Reply-To, the password nor the path of a password file, resolves no name, never contacts the
   server, and reads the configuration — the password file included — off the event loop (``asyncio.to_thread``). An
   answer built without ``email`` serializes ``{"available": false}``, and the OpenAPI does not require it.

In-process: the real routers of auth and email, and the instance route of the system router (``instance_router``, under
``/system``), mounted under the API prefix as ``api/v1/router.py`` mounts them, in an
app of this test whose ``get_session_generator`` opens sessions on a private SQLite file under ``tmp_path`` (NullPool,
disposed at teardown) holding the default global settings. Accounts are written as rows with a real bcrypt hash at cost
4 (``auth_service.BCRYPT_ROUNDS``), sign in through ``POST /auth/login`` and keep their cookie in an
``httpx.AsyncClient`` over ``httpx.ASGITransport`` (the session cookie's Secure attribute on ``auto``, as shipped, so
that ``http://test`` gets it back). The lane's backend is never called: the SMTP variables are those of this process.
An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*`` and each test sets its own (monkeypatch);
``delivery.INSTANCE_BUDGET`` is a private limiter on a fake clock; ``smtp.SMTP_TIMEOUT_SECONDS`` is 5 s, a bound,
never a wait; ``socket.getaddrinfo`` resolves the loopback only and records any other name, so a host name configured
for the status is never looked up, let alone contacted. Every SMTP conversation is with ``FakeSmtpServer`` on
127.0.0.1, on a port the OS picks; a refused connection is ``closed_port()``. Nothing is timed.
"""

from __future__ import annotations

import asyncio
import contextlib
import math
import os
import socket
import threading
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import email as email_api
from backend.app.api.v1.system import instance as instance_api
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User, UserSettings
from backend.app.db.session import get_session_generator
from backend.app.schemas.auth import AccountsInstanceConfig
from backend.app.schemas.settings import SETTINGS_REGISTRY, UserSettingsRead
from backend.app.schemas.system import InstanceConfigResponse
from backend.app.services.accounts import auth_service
from backend.app.services.accounts.settings_service import get_user_settings, initialize_global_settings
from backend.app.services.email import delivery, flows, smtp
from backend.app.services.email.messages import EmailRecipientError, build_test_message
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer, closed_port
from backend.test_scripts.test_utils import print_section, print_success

# Paths of the in-process app, mounted as api/v1/router.py mounts the routers.
LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
STATUS = f"{API_V1_PREFIX}/email/status"
SEND_TEST = f"{API_V1_PREFIX}/email/test"
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
STATUS_KEYS = {"state", "problem", "variable", "checks", "budget"}
CHECK_KEYS = {"check_id", "severity", "i18n_key", "detail"}

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
def _no_inherited_smtp_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX):
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
    limiter = SlidingWindowLimiter(50, WINDOW, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


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


async def _add_account(engine: AsyncEngine, username: str, *, admin: bool = False, email: str | None = None) -> _Account:
    """An active account written as a row, ``<username>@example.com`` unless ``email`` says otherwise, with a real bcrypt hash of ACCOUNT_PASSWORD (cost 4)."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@example.com", hashed_password=auth_service.hash_password(ACCOUNT_PASSWORD), is_superuser=admin)
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
async def _browser(private: _Private, base_url: str = BASE_URL, *, raise_app_exceptions: bool = True) -> AsyncIterator[httpx.AsyncClient]:
    """A browser of its own on the private instance: its own cookie jar, no session until it signs in. With ``raise_app_exceptions=False`` an error the app does not handle reaches it as the 500 a browser would get, instead of being raised in the test."""
    transport = httpx.ASGITransport(app=private.app, raise_app_exceptions=raise_app_exceptions)
    async with httpx.AsyncClient(transport=transport, base_url=base_url, timeout=TIMEOUT) as client:
        yield client


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


async def _refused_by_the_read_model(engine: AsyncEngine, user_id: int) -> str:
    """The precondition, verified: ``get_user_settings``, the read model the rest of the app reads the row through, refuses the account's row; what it said."""
    async with AsyncSession(engine) as session:
        with pytest.raises(ValidationError) as refused:
            await get_user_settings(user_id, session)
    return str(refused.value)


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
    """EMA-004 — contract 2: no host — even with every other variable set, an invalid TLS mode included —: ``state="off"``, no problem, no variable, no budget; ``email.smtp`` ok/off, ``email.smtp_encryption`` ok/ok, both with an empty detail; exactly the five keys of the status and the four of a check."""
    print_section("EMA-004: off")
    _configure(monkeypatch, variables)

    body = (await _status_as_admin(private)).json()

    assert set(body) == STATUS_KEYS, body
    assert (body["state"], body["problem"], body["variable"], body["budget"]) == ("off", None, None, None), body
    assert [set(check) for check in body["checks"]] == [CHECK_KEYS, CHECK_KEYS], body["checks"]
    assert _checks(body) == {"email.smtp": SMTP_OFF, "email.smtp_encryption": ENCRYPTION_OK}
    print_success("off, two ok checks")


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
    """EMA-005 — contract 2: one fault on a usable configuration towards a public host: ``state="invalid"``, the problem and the variable at fault, no budget; ``email.smtp`` error ``email.checks.smtp.invalid`` with ``detail == {problem, variable}``; the encryption check ok; no name resolved."""
    print_section(f"EMA-005: {problem}")
    _configure(monkeypatch, {**PUBLIC_CONFIGURATION, **overrides}, tmp_path)

    body = (await _status_as_admin(private)).json()

    assert (body["state"], body["problem"], body["variable"], body["budget"]) == ("invalid", problem, variable, None), body
    invalid = _check("email.smtp", "error", "email.checks.smtp.invalid", {"problem": problem, "variable": variable})
    assert _checks(body) == {"email.smtp": invalid, "email.smtp_encryption": ENCRYPTION_OK}
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
    """EMA-006 — contract 2: ``state="ready"``, no problem, no variable; ``email.smtp`` ok/ok; the encryption check ``localPlain`` for plain text to the fake on 127.0.0.1, ``ok`` for starttls and tls, a ``warning`` ``plain`` with an empty detail for plain text to a public host; the budget whole, ``{9, 9, 0}``. A fake runs in every case, and the status opened no connection to it and resolved no name — the public host is never even looked up."""
    print_section(f"EMA-006: ready, {target}, tls {tls!r}")

    with FakeSmtpServer() as fake:
        if target == "loopback":
            _point_at(monkeypatch, fake, max_per_hour="9")
        else:
            _configure(monkeypatch, {**PUBLIC_CONFIGURATION, "tls": tls})
        body = (await _status_as_admin(private)).json()

    assert (body["state"], body["problem"], body["variable"]) == ("ready", None, None), body
    assert body["budget"] == {"max_per_hour": 9, "remaining": 9, "retry_after_seconds": 0}
    assert _checks(body) == {"email.smtp": SMTP_OK, "email.smtp_encryption": encryption}
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
async def test_a_settings_row_the_read_model_refuses_still_gives_the_test_email_its_language(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EMA-017 — contract 3: the instance says ``es``; once the administrator has signed in, their ``user_settings`` row says ``it`` with a theme outside light/dark/auto (``sepia``, written as a row). ``POST /email/test``: 200 ``{language: "it"}`` — not 422 —, one message, its subject and text the Italian test email; one unit spent; the row left as it was.

    Barrier first: ``get_user_settings``, the read model the rest of the app reads the row through, refuses that row
    with a ``ValidationError`` naming the theme. The row is written after the sign-in because ``POST /auth/login`` reads
    the row through that same read model.
    """
    print_section("EMA-017: a settings row the read model refuses")
    await _set_default_language(private.engine, "es")
    expected = build_test_message(language="it", username=ADMIN, instance=INSTANCE_LABEL)

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private) as client:
            await _sign_in(client, private.admin)
            await _set_account_language(private.engine, private.admin.id, "it", theme=STALE_THEME)
            refusal = await _refused_by_the_read_model(private.engine, private.admin.id)
            response = await client.post(SEND_TEST)

    assert "theme" in refusal, f"barrier: the read model must refuse the row for its theme: {refusal}"
    assert response.status_code == 200, f"a settings row the read model refuses must not stop the test email: {response.status_code} {response.text}"
    assert response.json()["language"] == "it", response.text
    assert [received.message["Subject"] for received in fake.messages] == [expected.subject]
    assert _lines(fake.messages[0].message.get_body(preferencelist=("plain",)).get_content()) == _lines(expected.text)
    assert budget.count() == 1
    assert await _settings_row(private.engine, private.admin.id) == ("it", STALE_THEME), "the test email must leave the row as it was"
    print_success("200 in Italian from a row the read model refuses; the row untouched")


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
    """EMA-019 — contract 5: without a session, ``GET /system/instance`` answers 200 with ``email`` exactly ``{"available": available}``, a bool — ``true`` for a usable configuration, plain text to a public host included, ``false`` when email is off (even with every other variable set), invalid or its password file cannot be read —; its raw JSON holds neither the host, the port, the user, the password, the sender, the Reply-To nor the folder of a password file, and no name was resolved."""
    print_section(f"EMA-019: /system/instance, available={available}")
    _configure(monkeypatch, variables, tmp_path)

    async with _browser(private) as client:
        response = await client.get(INSTANCE)

    assert response.status_code == 200, f"GET /system/instance is public: {response.status_code} {response.text}"
    email = response.json().get("email")
    assert email == {"available": available} and type(email["available"]) is bool, f"email must be exactly {{'available': {available}}}: {response.text}"
    leaked = _leaks(response.text, {**NOT_IN_A_STATUS, "the folder of the password file": str(tmp_path)})
    assert leaked == [], f"the public configuration holds {leaked}: {response.text}"
    assert network == [], f"the public configuration resolved {network}"
    print_success(f"email {email}, nothing of the configuration")


@pytest.mark.asyncio
async def test_the_public_configuration_never_contacts_the_smtp_server(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str]) -> None:
    """EMA-020 — contract 5: email ready towards a running fake on the loopback: ``available`` is ``true`` and the fake accepted no connection — whether email is available is read from the configuration, never by trying the server."""
    print_section("EMA-020: /system/instance never contacts the server")

    with FakeSmtpServer() as fake:
        _point_at(monkeypatch, fake)
        async with _browser(private) as client:
            response = await client.get(INSTANCE)

    assert response.status_code == 200 and response.json().get("email") == {"available": True}, f"{response.status_code} {response.text}"
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

    assert response.status_code == 200 and response.json().get("email") == {"available": True}, f"{response.status_code} {response.text}"
    assert reads, "barrier: GET /system/instance never read the password through delivery.smtp_password"
    on_the_loop = [(thread, running) for thread, running in reads if thread == loop_thread or running]
    assert on_the_loop == [], f"{len(on_the_loop)} of {len(reads)} configuration reads ran on the event loop: the password file must be read through asyncio.to_thread"
    print_success(f"{len(reads)} read(s), none on the loop")


def test_an_answer_built_without_email_says_email_is_off_and_the_openapi_does_not_require_it() -> None:
    """EMA-022 — contract 5: ``InstanceConfigResponse(profile=..., accounts=...)`` without ``email`` serializes ``email`` as ``{"available": false}`` — an answer that forgets it, or a client reading an older server, says nothing can be sent —; and in the OpenAPI of the route the response schema lists ``email`` without requiring it."""
    print_section("EMA-022: email defaults to off and is optional in the OpenAPI")
    answer = InstanceConfigResponse(profile="selfhosted", accounts=AccountsInstanceConfig(registration_mode="open", registration_locked=False))
    app = FastAPI()
    app.include_router(instance_api.instance_router, prefix=f"{API_V1_PREFIX}/system")

    document = app.openapi()

    assert answer.model_dump(mode="json")["email"] == {"available": False}, answer.model_dump(mode="json")
    reference = document["paths"][INSTANCE]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    schema = document["components"]["schemas"][reference.rsplit("/", 1)[-1]]
    assert "email" in schema["properties"], f"the response schema must declare email: {schema}"
    assert "email" not in schema.get("required", []), f"email must stay optional in the OpenAPI: {schema.get('required')}"
    print_success(f"email {answer.model_dump(mode='json')['email']}; required: {schema.get('required')}")
