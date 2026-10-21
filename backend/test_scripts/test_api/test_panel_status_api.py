"""
The hosting panel's status route, ``GET /api/v1/panel/status`` (LibreFolio 1.3, workstream H, lot H-61, checkpoint 1,
R1): contract §4, with §2 for its access and §3 for the blocked instance.

Under test: ``backend/app/api/v1/panel.py`` (``get_panel_status``, included by ``api/v1/router.py`` with the prefix
``/panel``), its answer ``PanelStatusResponse`` (``backend/app/schemas/hosting_panel.py``), and its dependency
``panel_access(PanelScope.STATUS)`` (``services/platform/hosting_panel/access.py``) as the route meets it. The contract:

- Off: with no ``LIBREFOLIO_PANEL_STATUS_TOKEN`` (nor its ``_FILE``; empty or blank counts as unset) the route answers
  ``404 {"detail": "Not Found"}``, as a path that does not exist, whatever the request carries, the token of a scope
  that is on included (Q3). A's function is never called.
- On: a request without the status token gets the scope's own 401, whole, ``{"detail": {"code":
  "panel_status_unauthorized", "message": "A valid panel status token is required"}}`` with ``WWW-Authenticate:
  Bearer``: no ``Authorization``, a token of nobody, the wake-up's or the backup's token (Q2: a token of its own), the
  status token in another scheme or in the query string. A's function is never called.
- With ``Authorization: Bearer <the status token>``: 200 with exactly ``admin_setup`` (the ``value`` of the state
  ``admin_setup_status`` reads: ``none``, ``pending``, ``done`` or ``expired``) and ``setup_expires_at``: the expiry of
  a ``pending`` setup, in ISO 8601 with the UTC offset, and null for the three other states even when the status holds
  a date (Q10). A's function is called once, with the request's own database session and a ``now`` keyword: the moment
  of the request, in UTC.
- No personal data: a status read from the row of an account never shows its username or its email, in the answer or
  in a line the request writes.
- Blocked (``LIBREFOLIO_BLOCKED=1``): the route is allowed (``ALLOWED_WHEN_BLOCKED``, pinned by
  ``test_instance_block.py``) and answers on its own terms only: 200 with its token, a session or not; without it, the
  scope's 401, never the 423 of the block, even to a signed-in caller the block refuses elsewhere.
- OpenAPI: the 200 is ``PanelStatusResponse``, with exactly ``admin_setup``, an enum of the four states, and
  ``setup_expires_at``, a date-time or null, and no other property; the responses documented are exactly 200, 401,
  404, 429 and 503. The route's only tag is «Hosting panel», its one security scheme ``PanelStatusToken``, an HTTP
  bearer of its own.

Not here: «not a visit» (§3, Q5), which waits for workstream Z's answer; the limiter, the log line and the 503 of an
unusable token, which belong to the dependency (§2) and hold for its three scopes alike.

How. The app of ``backend/app/main.py`` runs in this process through ``httpx.ASGITransport`` (its lifespan does not
run). ``admin_setup_status``, A's function (``services/accounts/bootstrap_admin_service.py``, not written yet), is
replaced in the route's module by a recording stand-in that answers objects shaped like A's ``AdminSetupStatus``:
``state``, a ``StrEnum`` with A's four values, and ``setup_expires_at``. So the route must read the state by its value,
as the contract says (``status.state.value``), never by the identity of A's members. Every request of a test gets one
database session, on an in-memory database with the ORM schema (``dependency_overrides`` of ``get_session_generator``,
through monkeypatch): the stand-in tells by identity that it got the request's own; the blocked case signs in an account
of that database with a session cookie this process mints, as a login would. The tokens and the block are environment
variables, read at each request and set through monkeypatch. Every request counts on an activity record
(``activity.ACTIVITY``) and a panel attempts limiter (``access.PANEL_ATTEMPTS``, ``SlidingWindowLimiter(20, 600)`` on a
clock that never moves) of the test's own, as the contract lets a test replace them: the process's record of sleep and
wake is never touched, and the refusals other files count in this process never turn an answer of this one into a 429.
Each request runs inside a log capture, so no line reaches a log file.

Isolation: pure. No server, no lane database, no network, no file: the in-memory database goes with its engine,
disposed at teardown, and every change to the process (variables, the route's function, the limiter, the activity
record, the dependency override, structlog's processors) is undone after each test.

Red today: ``backend/app/api/v1/panel.py`` does not exist. R1-01 to R1-05 fail on their first step, installing the
stand-in in the route's module; R1-06 and R1-07 on the OpenAPI document, which has no ``GET /api/v1/panel/status``.
"""

from __future__ import annotations

import importlib
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from types import ModuleType
from typing import Any
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.config import API_V1_PREFIX, is_test_mode
from backend.app.config.platform import instance_blocked
from backend.app.db.base import SQLModel  # imports every model: the in-memory database gets the whole ORM schema
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.services.accounts.auth_service import create_jwt_token
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

STATUS_PATH = f"{API_V1_PREFIX}/panel/status"
#: A route outside ALLOWED_WHEN_BLOCKED: on a blocked instance a signed-in caller gets the 423 of the block there.
REFUSED_PATH = f"{API_V1_PREFIX}/brokers"

#: The modules R1 adds, imported by the tests that need them, and their files for the red message.
ROUTE_MODULE = "backend.app.api.v1.panel"
ACCESS_MODULE = "backend.app.services.platform.hosting_panel.access"
_MODULE_FILES = {ROUTE_MODULE: "backend/app/api/v1/panel.py", ACCESS_MODULE: "backend/app/services/platform/hosting_panel/access.py"}

#: The tokens of the three scopes of the hosting panel (contract §1, ``config/sleep_wake.py``, ``config/backup.py``);
#: ``env_secret`` also reads ``<variable>_FILE``.
STATUS_TOKEN_VARIABLE = "LIBREFOLIO_PANEL_STATUS_TOKEN"
WAKE_TOKEN_VARIABLE = "LIBREFOLIO_WAKE_TOKEN"
BACKUP_TOKEN_VARIABLE = "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN"
SECRET_FILE_SUFFIX = "_FILE"
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
DELETION_DATE_VARIABLE = "LIBREFOLIO_DELETION_DATE"

#: The route's answers, whole: off, and without its token; and the block's answer to a signed-in caller elsewhere.
OFF_ANSWER = {"detail": "Not Found"}
UNAUTHORIZED_ANSWER = {"detail": {"code": "panel_status_unauthorized", "message": "A valid panel status token is required"}}
BLOCKED_ANSWER = {"detail": {"code": "instance_blocked", "message": "This instance is blocked by its hosting provider"}}

#: The keys of the answer, exactly, and the four states of the initial administrator's setup (A's ``AdminSetupState``).
ANSWER_KEYS = {"admin_setup", "setup_expires_at"}
SETUP_STATES = ("none", "pending", "done", "expired")

#: The OpenAPI document: the route's responses, exactly; its one tag; the scheme of its token.
DOCUMENTED_RESPONSES = {"200", "401", "404", "429", "503"}
HOSTING_PANEL_TAG = "Hosting panel"
STATUS_SCHEME = "PanelStatusToken"

#: The panel's attempts limiter as the contract builds it (``PANEL_ATTEMPT_LIMIT``, ``PANEL_ATTEMPT_WINDOW_SECONDS``), on
#: a clock that never moves: nothing a test counts leaves the window, and nothing depends on how long a test takes.
ATTEMPT_LIMIT = 20
ATTEMPT_WINDOW_SECONDS = 600
FROZEN_CLOCK_SECONDS = 1_000_000.0

#: The expiry A gives a pending setup: an aware UTC instant, its microseconds included, as a stored link carries one.
SETUP_EXPIRES_AT = datetime(2026, 10, 23, 9, 41, 27, 125000, tzinfo=UTC)
#: A date the stand-in holds for a state that has none, which A never gives: the route must not hand it out.
STRAY_DATE = datetime(2026, 10, 17, 6, 5, 0, tzinfo=UTC)
#: The answer to the token while the setup waits, ``setup_expires_at`` read as an instant (``_status_answer``).
PENDING_ANSWER = {"admin_setup": "pending", "setup_expires_at": SETUP_EXPIRES_AT}

#: Logged through a logger of this file inside the capture first: a capture that sees nothing proves nothing.
LOG_CANARY = "R1-04 canary: a line written inside the capture reaches it"

TIMEOUT = 30
logger = get_logger(__name__)


# =============================================================================
# A's function, replaced: stand-ins shaped like AdminSetupState and AdminSetupStatus
# =============================================================================


class SetupStateStandIn(StrEnum):
    """Stand-in of A's ``AdminSetupState``: the same four values."""

    NONE = "none"
    PENDING = "pending"
    DONE = "done"
    EXPIRED = "expired"


@dataclass(frozen=True)
class SetupStatusStandIn:
    """Stand-in of A's ``AdminSetupStatus``: the same two attributes."""

    state: SetupStateStandIn
    setup_expires_at: datetime | None = None


@dataclass(frozen=True)
class RowBackedStatusStandIn(SetupStatusStandIn):
    """A status read from the row of an account, which it still holds: the row, its username and its email."""

    account: User | None = None
    username: str | None = None
    email: str | None = None


#: The default of the stand-in's ``now``: tells «not given» from any value the route could pass.
_NOT_GIVEN = object()


@dataclass(frozen=True)
class ReaderCall:
    """One call of the stand-in: the session and the ``now`` it got."""

    session: Any
    now: Any


class SetupStatusReader:
    """The stand-in of ``admin_setup_status(session, *, now=None)``: records each call, then answers ``answer``, or
    what ``answer`` builds from the session it gets when it is a coroutine function."""

    def __init__(self, answer: SetupStatusStandIn | Callable[[Any], Awaitable[SetupStatusStandIn]]) -> None:
        self._answer = answer
        self.calls: list[ReaderCall] = []
        self.answers: list[SetupStatusStandIn] = []

    async def __call__(self, session: Any, *, now: Any = _NOT_GIVEN) -> SetupStatusStandIn:
        self.calls.append(ReaderCall(session, now))
        answer = await self._answer(session) if callable(self._answer) else self._answer
        self.answers.append(answer)
        return answer


def _module(name: str) -> ModuleType:
    """The new module ``name``, imported by the test that needs it: before R1 it does not exist, and the rest of this
    file must still be collected."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name is None or not (name == error.name or name.startswith(f"{error.name}.")):
            raise
    pytest.fail(f"R1: {_MODULE_FILES[name]} is missing")


def _given(module: ModuleType, name: str) -> Any:
    """``module.name``, the test failing when the module does not give it."""
    if not hasattr(module, name):
        pytest.fail(f"R1: {module.__name__} gives no {name}")
    return getattr(module, name)


def _frozen_clock() -> float:
    return FROZEN_CLOCK_SECONDS


def _install_route(monkeypatch: pytest.MonkeyPatch, answer: SetupStatusStandIn | Callable[[Any], Awaitable[SetupStatusStandIn]]) -> SetupStatusReader:
    """Until the test ends, in this process: the route module's ``admin_setup_status`` is a recording stand-in answering
    ``answer``, and the panel's attempts limiter a new one of the test's own, as the contract lets a test replace it
    (``monkeypatch.setattr(access, "PANEL_ATTEMPTS", ...)``), so the refusals other tests counted in this process never
    turn an answer of this one into a 429. Returns the stand-in."""
    route = _module(ROUTE_MODULE)
    _given(route, "admin_setup_status")
    access = _module(ACCESS_MODULE)
    _given(access, "PANEL_ATTEMPTS")
    monkeypatch.setattr(access, "PANEL_ATTEMPTS", SlidingWindowLimiter(ATTEMPT_LIMIT, ATTEMPT_WINDOW_SECONDS, clock=_frozen_clock))
    reader = SetupStatusReader(answer)
    monkeypatch.setattr(route, "admin_setup_status", reader)
    return reader


# =============================================================================
# The tokens, the requests, the answers
# =============================================================================


def _token() -> str:
    """A token of this test: 64 hex characters, as ``openssl rand -hex 32`` writes one."""
    return secrets.token_hex(32)


@dataclass(frozen=True)
class PanelTokens:
    """A token of this test for each scope of the hosting panel, all different."""

    status: str
    wake: str
    backup: str

    @classmethod
    def new(cls) -> PanelTokens:
        return cls(status=_token(), wake=_token(), backup=_token())


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _no_panel_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """No token of the hosting panel (neither the variable nor its ``_FILE``) and no block, in this process, until the
    test sets them: nothing comes from the runner's environment."""
    for variable in (STATUS_TOKEN_VARIABLE, WAKE_TOKEN_VARIABLE, BACKUP_TOKEN_VARIABLE):
        monkeypatch.delenv(variable, raising=False)
        monkeypatch.delenv(variable + SECRET_FILE_SUFFIX, raising=False)
    monkeypatch.delenv(BLOCKED_VARIABLE, raising=False)
    monkeypatch.delenv(DELETION_DATE_VARIABLE, raising=False)


async def _request(app: FastAPI, method: str, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    """``method`` ``path`` on the app in process, from a client of its own: only ``headers`` decide what is sent."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://librefolio.test") as client:
        return await client.request(method, path, headers=headers or {}, timeout=TIMEOUT)


async def _send(app: FastAPI, method: str, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    """``_request`` inside a log capture: no line the request writes reaches a log file."""
    with capture_logs(processors=[merge_contextvars]):
        return await _request(app, method, path, headers)


def _answer(response: httpx.Response) -> tuple[int, Any]:
    """What a client is told: the status and the JSON body (the text when it is not JSON)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


def _utc_instant(value: Any) -> datetime | None:
    """An API timestamp in ISO 8601 with an explicit UTC offset (``Z`` or ``+00:00``) as an aware datetime; None for
    anything else, a naive timestamp included: a browser would read it in its own time zone."""
    if not isinstance(value, str):
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    return moment if moment.utcoffset() == timedelta(0) else None


def _status_answer(response: httpx.Response) -> tuple[int, Any]:
    """``_answer``, with a ``setup_expires_at`` written in ISO 8601 with the UTC offset read as that instant, so that an
    answer compares whole against a datetime. Any other text stays as written: it never passes for an instant or null."""
    status, body = _answer(response)
    if isinstance(body, dict) and isinstance(body.get("setup_expires_at"), str):
        instant = _utc_instant(body["setup_expires_at"])
        if instant is not None:
            body = {**body, "setup_expires_at": instant}
    return status, body


def _request_moment_problem(now: Any, before: datetime, after: datetime) -> str | None:
    """Why ``now`` is not the moment of the request in UTC (an aware datetime with the UTC offset, between ``before``
    and ``after``); None when it is."""
    if now is _NOT_GIVEN:
        return "no now keyword"
    if not isinstance(now, datetime) or now.utcoffset() != timedelta(0):
        return f"not an aware datetime in UTC: {now!r}"
    if not before <= now <= after:
        return f"{now.isoformat()} is not the request's moment, between {before.isoformat()} and {after.isoformat()}"
    return None


def _everything_shown(response: httpx.Response) -> str:
    """Everything an answer shows its client: the status, every header and the body."""
    headers = "\n".join(f"{name}: {value}" for name, value in response.headers.multi_items())
    return f"{response.status_code}\n{headers}\n{response.text}"


async def _signed_in(session: AsyncSession) -> dict[str, str]:
    """An active account of the in-memory database, and the Cookie header of a session this process mints for it, as a
    login would: the app in process signs and reads its sessions with the same secret."""
    username = f"r1_{uuid4().hex[:12]}"
    account = User(username=username, email=f"{username}@example.com", hashed_password="not-a-password-hash")
    session.add(account)
    await session.commit()
    with capture_logs():
        token = create_jwt_token(account.id, 1, account.session_version)
    return {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}


# =============================================================================
# The app in process
# =============================================================================


@pytest.fixture(scope="module")
def app() -> FastAPI:
    """The app the server runs, in this process. Test mode, so that importing it never reaches the production data
    directory; its requests never reach the lane's database either (``in_process``)."""
    assert is_test_mode(), "Precondition: test mode, so that the app in process never reaches the production data directory"
    from backend.app.main import app as main_app  # noqa: PLC0415 — the server's own app, imported by the fixture that needs it

    return main_app


@dataclass(frozen=True)
class InProcess:
    """The app in process, and the database session every request of the test gets."""

    app: FastAPI
    session: AsyncSession


@pytest_asyncio.fixture
async def in_process(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[InProcess]:
    """The real app, for this test: no panel token and no block until the test sets them; an activity record of its own
    (``current_activity()`` reads ``ACTIVITY`` at each request), so the process's record of sleep and wake is never
    touched; and every request's database session replaced (``dependency_overrides``, through monkeypatch) by one
    session on an in-memory database with the ORM schema, never the lane's database. The session is closed and the
    engine disposed on the way out."""
    _no_panel_variables(monkeypatch)
    assert not instance_blocked(), "Precondition: the instance is not blocked until a test blocks it"
    monkeypatch.setattr(activity_module, "ACTIVITY", activity_module.Activity())
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            monkeypatch.setitem(app.dependency_overrides, get_session_generator, lambda: session)
            yield InProcess(app, session)
    finally:
        await engine.dispose()


# =============================================================================
# R1-01 — off without its token
# =============================================================================


# red today: backend/app/api/v1/panel.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "", "   "], ids=["unset", "empty", "blank"])
async def test_the_route_answers_404_and_reads_nothing_while_its_token_is_off(in_process, monkeypatch, value):
    """R1-01 (§4, §2 step 1, Q3): without ``LIBREFOLIO_PANEL_STATUS_TOKEN`` (unset, empty or blank, which counts as
    unset) the route answers ``404 {"detail": "Not Found"}`` whole, as a path that does not exist, to a request without
    ``Authorization``, with a token of nobody, and with the wake-up's or the backup's token while those scopes are on: a
    scope is off on its own. A's function is never called. Barrier: the token set, the same app answers its request 200
    through the stand-in, so the 404 comes from the token being off, never from a route that is missing."""
    print_section("R1-01: GET /panel/status while its token is off")
    reader = _install_route(monkeypatch, SetupStatusStandIn(SetupStateStandIn.PENDING, SETUP_EXPIRES_AT))
    tokens = PanelTokens.new()
    monkeypatch.setenv(WAKE_TOKEN_VARIABLE, tokens.wake)
    monkeypatch.setenv(BACKUP_TOKEN_VARIABLE, tokens.backup)
    if value is not None:
        monkeypatch.setenv(STATUS_TOKEN_VARIABLE, value)
    requests = {"no Authorization": None, "a token of nobody": _bearer(_token()), "the wake-up's token": _bearer(tokens.wake), "the backup's token": _bearer(tokens.backup)}

    answers = {label: _answer(await _send(in_process.app, "GET", STATUS_PATH, headers)) for label, headers in requests.items()}
    read_while_off = list(reader.calls)
    monkeypatch.setenv(STATUS_TOKEN_VARIABLE, tokens.status)
    control = await _send(in_process.app, "GET", STATUS_PATH, _bearer(tokens.status))

    assert _status_answer(control) == (200, PENDING_ANSWER), f"Barrier: with its token set, GET {STATUS_PATH} answers the token 200 through the stand-in: {control.status_code} {control.text}"
    assert len(reader.calls) == 1, f"Barrier: the request with the token reached the stand-in of admin_setup_status once: {reader.calls}"
    assert answers == dict.fromkeys(answers, (404, OFF_ANSWER)), f"{STATUS_TOKEN_VARIABLE}={value!r}: the route is off and answers 404 Not Found, as a path that does not exist, whatever the request carries: {answers}"
    assert read_while_off == [], f"admin_setup_status must never be called while the route is off: {read_while_off}"
    print_success(f"{STATUS_TOKEN_VARIABLE}={value!r}: 404 Not Found to every request, the setup never read; 200 once the token is set")


# =============================================================================
# R1-02 — the scope's own 401 without the status token
# =============================================================================

#: A request that does not present the status token as the contract wants it, ``Authorization: Bearer <token>``.
REFUSED_CASES = ["no-authorization", "token-of-nobody", "wake-token", "backup-token", "status-token-as-basic", "status-token-in-query"]


def _refused_request(case: str, tokens: PanelTokens) -> tuple[str, dict[str, str] | None]:
    """The path and the headers of the request ``case``."""
    requests: dict[str, tuple[str, dict[str, str] | None]] = {
        "no-authorization": (STATUS_PATH, None),
        "token-of-nobody": (STATUS_PATH, _bearer(_token())),
        "wake-token": (STATUS_PATH, _bearer(tokens.wake)),
        "backup-token": (STATUS_PATH, _bearer(tokens.backup)),
        "status-token-as-basic": (STATUS_PATH, {"Authorization": f"Basic {tokens.status}"}),
        "status-token-in-query": (f"{STATUS_PATH}?token={tokens.status}", None),
    }
    return requests[case]


# red today: backend/app/api/v1/panel.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize("case", REFUSED_CASES)
async def test_a_request_without_the_status_token_gets_the_scopes_own_401_and_reads_nothing(in_process, monkeypatch, case):
    """R1-02 (§2 step 3, Q2): the three scopes on, each with a token of its own, a request that does not present the
    status token in ``Authorization: Bearer`` gets the scope's own 401, whole, ``panel_status_unauthorized``, with
    ``WWW-Authenticate: Bearer``: no ``Authorization``, a token of nobody, the wake-up's token, the backup's token, the
    status token in the Basic scheme, the status token in the query string. A's function is never called. Barrier: the
    status token's request, right after, answers 200 through the stand-in."""
    print_section(f"R1-02: GET /panel/status without the status token ({case})")
    reader = _install_route(monkeypatch, SetupStatusStandIn(SetupStateStandIn.PENDING, SETUP_EXPIRES_AT))
    tokens = PanelTokens.new()
    monkeypatch.setenv(STATUS_TOKEN_VARIABLE, tokens.status)
    monkeypatch.setenv(WAKE_TOKEN_VARIABLE, tokens.wake)
    monkeypatch.setenv(BACKUP_TOKEN_VARIABLE, tokens.backup)
    path, headers = _refused_request(case, tokens)

    refused = await _send(in_process.app, "GET", path, headers)
    read_when_refused = list(reader.calls)
    accepted = await _send(in_process.app, "GET", STATUS_PATH, _bearer(tokens.status))

    assert _status_answer(accepted) == (200, PENDING_ANSWER), f"Barrier: GET {STATUS_PATH} with the status token answers 200 through the stand-in: {accepted.status_code} {accepted.text}"
    assert len(reader.calls) == 1, f"Barrier: the request with the status token reached the stand-in of admin_setup_status once: {reader.calls}"
    assert _answer(refused) == (401, UNAUTHORIZED_ANSWER), f"{case}: the route answers the status scope's own 401, whole: {refused.status_code} {refused.text}"
    assert refused.headers.get_list("www-authenticate") == ["Bearer"], f"{case}: the 401 asks for a bearer token: {refused.headers.get_list('www-authenticate')}"
    assert read_when_refused == [], f"{case}: admin_setup_status must never be called without the status token: {read_when_refused}"
    print_success(f"{case}: 401 panel_status_unauthorized with WWW-Authenticate: Bearer, the setup never read")


# =============================================================================
# R1-03 — the answer: the setup's state, and the expiry of a pending setup only
# =============================================================================


# red today: backend/app/api/v1/panel.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "held", "answered"),
    [
        pytest.param("pending", SETUP_EXPIRES_AT, SETUP_EXPIRES_AT, id="pending-with-its-expiry"),
        pytest.param("none", STRAY_DATE, None, id="none-holding-a-date"),
        pytest.param("done", STRAY_DATE, None, id="done-holding-a-date"),
        pytest.param("expired", STRAY_DATE, None, id="expired-holding-a-date"),
    ],
)
async def test_the_status_answers_the_setup_state_and_the_expiry_of_a_pending_setup_only(in_process, monkeypatch, state, held, answered):
    """R1-03 (§4, Q10): with its token, the route answers 200 with exactly ``admin_setup`` and ``setup_expires_at``:
    ``admin_setup`` the value of the state A's function reads, ``setup_expires_at`` the expiry it gives, in ISO 8601 with
    the UTC offset (the very instant), for ``pending`` only; null for ``none``, ``done`` and ``expired``, even when the
    status holds a date. A's function is called once, with the request's own database session (the very object every
    dependency of the request got) and a ``now`` keyword: an aware UTC datetime taken during the request."""
    print_section(f"R1-03: GET /panel/status, the setup {state}")
    reader = _install_route(monkeypatch, SetupStatusStandIn(SetupStateStandIn(state), held))
    token = _token()
    monkeypatch.setenv(STATUS_TOKEN_VARIABLE, token)

    before = datetime.now(UTC)
    response = await _send(in_process.app, "GET", STATUS_PATH, _bearer(token))
    after = datetime.now(UTC)

    status, body = _status_answer(response)
    assert status == 200, f"GET {STATUS_PATH} with its token answers 200: {response.status_code} {response.text}"
    assert isinstance(body, dict) and set(body) == ANSWER_KEYS, f"the answer holds exactly {sorted(ANSWER_KEYS)}: {response.text}"
    assert body == {"admin_setup": state, "setup_expires_at": answered}, f"the setup {state}, its status holding {held.isoformat()}: expected admin_setup {state!r} and setup_expires_at {answered.isoformat() if answered else None} (ISO 8601 with the UTC offset, for pending only), got {response.text}"
    assert len(reader.calls) == 1, f"admin_setup_status is called once per request: {reader.calls}"
    call = reader.calls[0]
    assert call.session is in_process.session, f"admin_setup_status gets the request's own database session (get_session_generator), got {call.session!r}"
    problem = _request_moment_problem(call.now, before, after)
    assert problem is None, f"admin_setup_status gets now=, the moment of the request in UTC: {problem}"
    print_success(f"{state}: 200 {response.text}, the setup read once with the request's session and its moment")


# =============================================================================
# R1-04 — no personal data
# =============================================================================


# red today: backend/app/api/v1/panel.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize("state", SETUP_STATES)
async def test_the_status_never_shows_the_account_it_was_read_from(in_process, monkeypatch, state):
    """R1-04 (§4): no personal data. The stand-in reads the row of an account of the request's database, the waiting
    initial administrator, whose username and email are canaries of this test, and answers a status that holds the row,
    its username and its email. Neither canary is in the answer (status, headers, body) nor in a line the request writes.
    Barriers: the route got the status holding both canaries; the capture sees a line of this file written inside it."""
    print_section(f"R1-04: GET /panel/status shows no personal data ({state})")
    username, email = f"r1-canary-{uuid4().hex[:12]}", f"r1-canary-{uuid4().hex[:12]}@canary.example"
    account = User(username=username, email=email, hashed_password="not-a-password-hash", is_active=False, is_superuser=True)
    in_process.session.add(account)
    await in_process.session.commit()
    account_id = account.id

    async def read_from_the_row(session: Any) -> SetupStatusStandIn:
        row = await session.get(User, account_id)
        return RowBackedStatusStandIn(SetupStateStandIn(state), SETUP_EXPIRES_AT, account=row, username=row.username, email=row.email)

    reader = _install_route(monkeypatch, read_from_the_row)
    token = _token()
    monkeypatch.setenv(STATUS_TOKEN_VARIABLE, token)

    with capture_logs(processors=[merge_contextvars]) as events:
        logger.info(LOG_CANARY)
        response = await _request(in_process.app, "GET", STATUS_PATH, _bearer(token))

    held = [(getattr(answer, "username", None), getattr(answer, "email", None)) for answer in reader.answers]
    assert response.status_code == 200, f"Barrier: GET {STATUS_PATH} with its token answers 200: {response.status_code} {response.text}"
    assert held == [(username, email)], f"Barrier: the route got one status holding the account's username and email: {held}"
    assert any(event.get("event") == LOG_CANARY for event in events), f"Barrier: a line written inside the capture reaches it, so what it holds proves something: {events!r}"
    shown = _everything_shown(response)
    assert [canary for canary in (username, email) if canary in shown] == [], f"the answer shows the account's username or email: {shown}"
    logged = repr(events)
    assert [canary for canary in (username, email) if canary in logged] == [], f"a line of the request holds the account's username or email: {logged}"
    print_success(f"{state}: neither the username nor the email in the answer or in a line")


# =============================================================================
# R1-05 — a blocked instance
# =============================================================================


# red today: backend/app/api/v1/panel.py is missing
@pytest.mark.asyncio
async def test_on_a_blocked_instance_the_status_answers_its_token_and_its_own_401_never_the_423(in_process, monkeypatch):
    """R1-05 (§3, §4): ``LIBREFOLIO_BLOCKED=1``. The route is in ALLOWED_WHEN_BLOCKED, and wants its token, never a
    session: with the token it answers 200 as on any instance, with a session or without; without the token it answers
    the scope's own 401, whole, with ``WWW-Authenticate: Bearer``, to a caller without a session and to a signed-in one
    alike, never the 423 of the block. A's function is reached by the two requests with the token only. Barrier: the
    same signed-in caller gets the 423 of the block on a refused route, so the block is on and the session valid."""
    print_section("R1-05: GET /panel/status on a blocked instance")
    reader = _install_route(monkeypatch, SetupStatusStandIn(SetupStateStandIn.PENDING, SETUP_EXPIRES_AT))
    token = _token()
    monkeypatch.setenv(STATUS_TOKEN_VARIABLE, token)
    signed_in = await _signed_in(in_process.session)
    monkeypatch.setenv(BLOCKED_VARIABLE, "1")
    assert instance_blocked(), f"Precondition: {BLOCKED_VARIABLE}=1 blocks the instance"
    requests = {
        "the token": _bearer(token),
        "the token and a session": {**signed_in, **_bearer(token)},
        "no credential": None,
        "a session without the token": signed_in,
    }

    refused_elsewhere = await _send(in_process.app, "GET", REFUSED_PATH, signed_in)
    responses = {label: await _send(in_process.app, "GET", STATUS_PATH, headers) for label, headers in requests.items()}

    assert _answer(refused_elsewhere) == (423, BLOCKED_ANSWER), f"Barrier: the block is on and refuses this signed-in caller outside the list, GET {REFUSED_PATH} answers 423: {refused_elsewhere.status_code} {refused_elsewhere.text}"
    answers = {label: _status_answer(response) for label, response in responses.items()}
    expected = {"the token": (200, PENDING_ANSWER), "the token and a session": (200, PENDING_ANSWER), "no credential": (401, UNAUTHORIZED_ANSWER), "a session without the token": (401, UNAUTHORIZED_ANSWER)}
    assert answers == expected, f"on a blocked instance GET {STATUS_PATH} answers its token 200 and anyone else the scope's own 401, never the 423 of the block: {answers}"
    challenges = {label: responses[label].headers.get_list("www-authenticate") for label in ("no credential", "a session without the token")}
    assert challenges == dict.fromkeys(challenges, ["Bearer"]), f"each 401 asks for a bearer token: {challenges}"
    assert len(reader.calls) == 2, f"admin_setup_status is reached by the two requests with the token, and by no other: {reader.calls}"
    print_success("blocked: 200 with the token, a session or not; the scope's 401 without it, never 423")


# =============================================================================
# R1-06, R1-07 — the OpenAPI document
# =============================================================================


def _status_operation(document: dict[str, Any]) -> dict[str, Any]:
    """The OpenAPI operation of ``GET /api/v1/panel/status``; the test fails when the document has none."""
    paths = document.get("paths", {})
    operation = paths.get(STATUS_PATH, {}).get("get")
    assert isinstance(operation, dict), f"R1: the OpenAPI document has no GET {STATUS_PATH}; its panel paths: {sorted(path for path in paths if '/panel' in path)}"
    return operation


def _resolved(schema: dict[str, Any], document: dict[str, Any]) -> dict[str, Any]:
    """``schema``, or the component its ``$ref`` names."""
    reference = schema.get("$ref")
    if not isinstance(reference, str):
        return schema
    return document.get("components", {}).get("schemas", {}).get(reference.rsplit("/", 1)[-1], {})


# red today: the OpenAPI document has no GET /api/v1/panel/status
def test_openapi_documents_the_status_answer_and_its_five_responses(app):
    """R1-06 (§4): the 200 of ``GET /api/v1/panel/status`` is ``PanelStatusResponse``, with exactly two properties and no
    other (``extra="forbid"``): ``admin_setup``, required, a string enum of the four states, and ``setup_expires_at``, a
    date-time or null. The responses documented are exactly 200, 401, 404, 429 and 503."""
    print_section("R1-06: GET /panel/status in the OpenAPI document")
    document = app.openapi()
    operation = _status_operation(document)
    responses = operation.get("responses", {})
    assert set(responses) == DOCUMENTED_RESPONSES, f"the route documents exactly the responses {sorted(DOCUMENTED_RESPONSES)}: {sorted(responses)}"

    schema = responses["200"].get("content", {}).get("application/json", {}).get("schema")
    assert schema == {"$ref": "#/components/schemas/PanelStatusResponse"}, f"the 200 of GET {STATUS_PATH} is PanelStatusResponse: {schema}"
    component = document.get("components", {}).get("schemas", {}).get("PanelStatusResponse", {})
    properties = component.get("properties", {})
    assert set(properties) == ANSWER_KEYS, f"PanelStatusResponse has exactly the properties {sorted(ANSWER_KEYS)}: {component}"
    assert component.get("additionalProperties") is False, f"PanelStatusResponse forbids any other property (extra='forbid'): {component}"
    assert "admin_setup" in component.get("required", []), f"admin_setup is always in the answer: {component}"
    admin_setup = _resolved(properties["admin_setup"], document)
    assert (admin_setup.get("type"), sorted(admin_setup.get("enum", []))) == ("string", sorted(SETUP_STATES)), f"admin_setup is a string enum of the four states {list(SETUP_STATES)}: {admin_setup}"
    variants = properties["setup_expires_at"].get("anyOf", [])
    assert len(variants) == 2 and {"type": "string", "format": "date-time"} in variants and {"type": "null"} in variants, f"setup_expires_at is a date-time or null: {properties['setup_expires_at']}"
    print_success("PanelStatusResponse: admin_setup (four states), setup_expires_at (date-time or null); 200, 401, 404, 429, 503")


# red today: the OpenAPI document has no GET /api/v1/panel/status
def test_openapi_lists_the_status_route_under_the_hosting_panel_with_a_token_of_its_own(app):
    """R1-07 (§2, §3, Q2): the route's only tag is «Hosting panel», and its one security requirement is the scheme
    ``PanelStatusToken``, an HTTP bearer of its own: neither the backup's ``BackupPanelToken`` nor the wake-up's
    ``WakeToken``."""
    document = app.openapi()
    operation = _status_operation(document)
    scheme = document.get("components", {}).get("securitySchemes", {}).get(STATUS_SCHEME, {})

    assert operation.get("tags") == [HOSTING_PANEL_TAG], f"GET {STATUS_PATH} has the one tag {HOSTING_PANEL_TAG!r}: {operation.get('tags')}"
    assert operation.get("security") == [{STATUS_SCHEME: []}], f"GET {STATUS_PATH} asks for the status scope's own scheme {STATUS_SCHEME}: {operation.get('security')}"
    assert (scheme.get("type"), scheme.get("scheme")) == ("http", "bearer"), f"{STATUS_SCHEME} is an HTTP bearer scheme: {scheme}"
    print_success(f"GET {STATUS_PATH}: tag {HOSTING_PANEL_TAG!r}, scheme {STATUS_SCHEME} (bearer)")
