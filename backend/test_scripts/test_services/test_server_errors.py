"""H-60 · readable errors, the server side (LibreFolio 1.3, workstream H): the request id, the 5xx answers and their
lines, the unhandled 500, the 500 of a response that breaks its model (H-33), and D4, the console level the public
configuration publishes; and H-60r, the cure of H-60's review: the safety net per request. The contracts are lot H-60's,
§3 to §7, with the §0 helper ``is_reported``, and lot H-60r's §2.

Under test:

- ``backend/app/services/platform/request_id.py`` (§3, amended 19/10). ``RequestIdMiddleware``, pure ASGI, is the
  second entry of ``MIDDLEWARE_STACK``, ``MiddlewareEntry("request_id", RequestIdMiddleware)``: right after
  ``activity``, which workstream Z's D-S1 keeps outermost (SWA-037 pins it), and before ``security_headers``, so every
  answer the app or the security headers send crosses it, the 500 of an error nobody handled included. For each HTTP
  request: a new id, ``secrets.token_hex(8)`` (16 lowercase hex characters), put in ``scope["state"]["request_id"]``,
  bound in structlog's contextvars for the whole request and unbound after, and sent back as ``X-Request-Id`` unless the
  app set one. An ``X-Request-Id`` the client sends is ignored; other scopes pass untouched; it logs nothing.
  ``request_id_of(source)``: the id of a ``Request`` or a scope, None without one.
- ``backend/app/api/server_errors.py`` (§4). ``install_server_error_handler(app)``: one handler for Starlette's
  ``HTTPException``, installed by ``main.py``. Below 500, FastAPI's own answer and no line. From 500, JSON
  ``{"detail", "request_id", "error_type"}`` with ``exc.headers``: ``request_id`` absent when the request has none,
  ``error_type`` the class of the root cause, absent without a visible cause. A visible cause nobody reported: one
  error «Request failed» (``request_id``, ``status``, ``method``, ``path`` without the query, ``error_type``,
  ``error_chain``, ``exc_info`` the shown error), then ``exc`` and the shown error are marked reported. No visible cause
  and nothing reported: one warning «Request answered a server error», no ``exc_info``. A chain already reported (the
  route logged it inside its ``except``): no line.
- ``backend/app/services/platform/security_headers.py`` (§5). An exception nobody handled is answered with a JSON 500
  ``{"detail": "Internal Server Error", "request_id", "error_type"}``, the security headers as before, and the
  ``X-Request-Id`` of its request: the security headers stand inside the request-id layer (§3). One error «Unhandled
  error» unless the exception is already reported; the exception marked reported, then raised again as before. After
  the answer started: no second answer, the same line, the mark, the raise.
- ``backend/app/api/response_validation.py`` (§6, H-33): the 500 is ``{"detail": "Internal Server Error", "request_id",
  "error_type": "ResponseValidationError"}``; its line unchanged, without the response's content.
- ``GET /api/v1/system/instance`` (§7, D4): ``client_log_level``, ``"debug"`` when the backend's ``LOG_LEVEL``
  (``LIBREFOLIO_LOG_LEVEL`` included) is DEBUG or TRACE, in any case, ``"error"`` otherwise: two states, never the level.
- Security (D2, the developer's question): no request header (``Authorization``, ``Cookie``), body, query string nor
  exception message in an answer; in a line, the message only inside ``exc_info``.
- H-60r §2, the safety net per request (``failure_report.py``). The «reported» mark records the requests whose lines
  have a failure, not only the object: an exception object several requests share — the single-flight builds of the
  portfolio and risk engines (MF-J45b/d) give every request waiting on a build that fails the build's own exception —
  must leave every request's id in the log, and its traceback once. For the request being answered, R, exactly one
  case. R's lines have the failure (``chain_reported_for``; for the unhandled 500 ``is_reported_for``, on the object
  itself): no line. Another request's line, or one outside any request, has it (``chain_reported``, ``is_reported``):
  one warning «Request failed with an error already logged», whole: ``request_id`` R, ``status`` (never for the
  unhandled 500), ``method``, ``path`` without the query, ``error_type`` and ``logged_with_request_id``, the first
  request that wrote the failure; no ``exc_info``, no ``error_chain``, no secret of the request nor the message.
  Otherwise H-60's line with the traceback, which now marks the chain that traceback renders too.

How. Fresh ``FastAPI()`` apps built as ``main.py`` builds its own — ``install_middleware(app)`` (the whole
``MIDDLEWARE_STACK``), A-35's 422 handler, H-33's handler and H-60's — with this file's routes, asked in process through
httpx's ASGI transport (``raise_app_exceptions`` off to read the answer an exception got, on to receive the exception a
server would log), or by raw ASGI calls where every response start must be counted. The routes are module-level
functions that read their canaries from their app's state: each app has canaries of its own. Lines are read with
``structlog.testing.capture_logs(processors=[merge_contextvars])``, so a line carries the request id its request bound;
every request that writes a line runs inside a capture, so no line reaches a log file. Every negative assertion stands
behind a barrier in the same capture: the expected line, or a canary. Two requests fail together as the portfolio
engine's single flight makes them fail (``_SharedFailure``): sent with ``asyncio.gather`` through one client, the build
of the request that leads awaits an ``asyncio.Event`` the other sets right before it awaits the build — no clock; which
request leads is recorded by the route, never assumed, and which one answers first is read from the lines. The real app
(``backend.app.main``) is read for its handler table and its stack, and asked ``GET /system/instance`` for D4 with its
database session replaced by one on an in-memory database with the ORM schema.

Red before H-60, each test on its first step: the tests of the fresh apps and of the install on «H-60:
backend/app/api/server_errors.py is missing»; the tests of the middleware alone on «H-60:
backend/app/services/platform/request_id.py is missing»; the app's test on the first of the two; the D4 tests on the
missing ``client_log_level`` (the schema declares none, the answer carries none). Red today, until H-60r, the tests of a
shared failure, the mark being the object's whichever request wrote it: two requests failing together on a build nobody
logged write «Request failed» twice, the traceback twice, when answered with a 503, and let go the second to answer
writes nothing, its id in no line; on a build that logged its failure the waiter writes nothing, its id in no line; one
object raised request after request is written again by every request through a 503, and let go by the first alone,
the others' ids in no line; the security test of the short line finds none.

Isolation: PURE. No lane database, no server, no network, no file of its own: the apps live in the test's process; the
real app gets a session on a private in-memory database for the D4 requests (``dependency_overrides``, through
monkeypatch) and is otherwise only read. Every request counts on an activity record of the test's own
(``activity.ACTIVITY`` replaced through monkeypatch: the process's record of sleep and wake is never touched). The
routes' logger is enabled from DEBUG for each test whatever the lane's ``LOG_LEVEL`` — the logging wrapper (§2) marks
the failure a line reports only when its logger writes that level — and its level is restored after. ``LOG_LEVEL`` and
``LIBREFOLIO_LOG_LEVEL`` are set through monkeypatch: ``get_settings()`` builds its settings at each call, so the
environment is the whole restore. Importing ``backend.app.main`` configures the logging, as for every module that
imports it; structlog's capture drops what it captures.
"""

import asyncio
import copy
import importlib
import logging
import re
import secrets
import traceback
import uuid
from collections.abc import AsyncIterator, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Self

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from starlette.exceptions import HTTPException as StarletteHTTPException
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

import backend.app.main as app_main
from backend.app.api.response_validation import install_response_validation_handler
from backend.app.api.validation_errors import install_validation_error_handler
from backend.app.config import get_settings
from backend.app.db.base import SQLModel  # imports every model: the in-memory database gets the whole ORM schema
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.auth import AccountsInstanceConfig
from backend.app.schemas.system import InstanceConfigResponse
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, MiddlewareEntry, install_middleware
from backend.app.services.platform.security_headers import SecurityHeadersMiddleware
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.test_scripts.test_utils import print_section, print_success

#: The modules H-60 adds, imported when a test needs them, and their files for the red message.
SERVER_ERRORS_MODULE = "backend.app.api.server_errors"
REQUEST_ID_MODULE = "backend.app.services.platform.request_id"
ERRORS_MODULE = "backend.app.utils.runtime.errors"
_MODULE_FILES = {
    SERVER_ERRORS_MODULE: "backend/app/api/server_errors.py",
    REQUEST_ID_MODULE: "backend/app/services/platform/request_id.py",
    ERRORS_MODULE: "backend/app/utils/runtime/errors.py",
}

#: The header of every answer, and the shape of its value: ``secrets.token_hex(8)``.
REQUEST_ID_HEADER = "x-request-id"
REQUEST_ID_SHAPE = re.compile(r"[0-9a-f]{16}")

#: The lines of the server-error handler (§4) and of the unhandled-error fallback (§5), and the short line either writes
#: since H-60r (§2): a request whose failure another request's line already has.
REQUEST_FAILED = "Request failed"
SERVER_ERROR_ANSWERED = "Request answered a server error"
UNHANDLED = "Unhandled error"
ALREADY_LOGGED = "Request failed with an error already logged"
SERVER_ERROR_LINES = frozenset({REQUEST_FAILED, SERVER_ERROR_ANSWERED, UNHANDLED, ALREADY_LOGGED})
#: H-33's line (``response_validation.py``), which H-60 leaves as it is.
MODEL_BROKEN = "A response does not match its model"

#: The routes' logger: structlog writes through the stdlib logger of the same name.
ROUTE_LOGGER = "backend.test_scripts.test_services.test_server_errors.routes"
ROUTE_LINE = "h60 route: answered"
ROUTE_WARNING = "h60 route: the key could not be read"
ROUTE_ERROR = "h60 route: failed"
#: The line of a shared build that logs its failure where it catches it (H-60r).
BUILD_FAILED = "h60r build: failed"
AFTER_LINE = "h60 test: a line after the request"
CAPTURE_CANARY = "h60 test: the capture sees the routes' logger"

INTERNAL = "Internal Server Error"
UNAVAILABLE_DETAIL = {"error_code": "H60_UNAVAILABLE", "message": "The service cannot answer now"}
UPSTREAM_DETAIL = {"error_code": "H60_UPSTREAM", "message": "A component could not be built"}
CONFLICT_DETAIL = {"error_code": "H60_CONFLICT", "message": "It is already there"}
BARE_DETAIL = "Failed"
RETRY_AFTER = "30"
CONFLICT_HEADER = ("x-h60-conflict", "kept")
#: An id an app sets itself, and a valid one for request_id_of.
APP_REQUEST_ID = "set-by-the-app"
KNOWN_REQUEST_ID = "0123456789abcdef"
CHAIN_COMPONENT = "h60.component"
FIRST_CHUNK = b"h60: the first chunk\n"

#: Every in-process call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0
BASE_URL = "http://h60.test"

OK_PATH = "/h60/ok"
COUNT_PATH = "/h60/count"
CONFLICT_PATH = "/h60/conflict"
FAILED_PATH = "/h60/failed"
FROM_NONE_PATH = "/h60/reported-from-none"
FROM_CAUSE_PATH = "/h60/reported-from-cause"
BARE_PATH = "/h60/bare"
CHAIN_PATH = "/h60/chain"
UNHANDLED_PATH = "/h60/unhandled"
LOGGED_UNHANDLED_PATH = "/h60/logged-then-raised"
STREAM_PATH = "/h60/broken-stream"
MODEL_PATH = "/h60/broken-model"
UNKNOWN_PATH = "/h60/nowhere"
BARE_ASGI_PATH = "/h60/bare-asgi"
#: H-60r: the routes of a failure several requests share (``_SharedFailure``), answered with a 503 or let go.
SHARED_HTTP_PATH = "/h60/shared-failure/http"
SHARED_UNHANDLED_PATH = "/h60/shared-failure/unhandled"
#: The requests that raise one exception object one after the other: the first writes the traceback, each later one its
#: short line.
SEQUENTIAL_REQUESTS = 3

#: D4: the public configuration's route, and the settings it reads.
INSTANCE_PATH = "/api/v1/system/instance"
LOG_LEVEL_VARIABLE = "LOG_LEVEL"
LOG_LEVEL_OVERRIDE = "LIBREFOLIO_LOG_LEVEL"


@dataclass(frozen=True)
class _Canaries:
    """Values no answer may carry, nor a line outside its ``exc_info``: new for each app, unique across workers and runs."""

    message: str  # the message of every exception the routes raise
    token: str  # sent as ?token=
    authorization: str  # sent as Authorization: Bearer
    cookie: str  # sent as Cookie: s=
    password: str  # sent in the body {"password": ...}

    @classmethod
    def new(cls) -> Self:
        tag = uuid.uuid4().hex
        return cls(message=f"canary-msg-{tag}", token=f"canary-token-{tag}", authorization=f"canary-auth-{tag}", cookie=f"canary-cookie-{tag}", password=f"canary-pw-{tag}")

    def every(self) -> tuple[str, ...]:
        return (self.message, self.token, self.authorization, self.cookie, self.password)


class H60RootError(Exception):
    """The root cause of the AI-Export-like chain."""


class H60ComponentError(Exception):
    """Like AI Export's ``RequiredComponentBuildError`` and ``ResourceLoadError``: its cause in ``cause``, never in ``__cause__``."""

    def __init__(self, component_id: str, cause: BaseException) -> None:
        super().__init__(f"component {component_id} was not built")
        self.component_id = component_id
        self.cause = cause


class H60SourceError(Exception):
    """What the chain's source raises, from the component's error."""


class H60BuildError(Exception):
    """What a shared build raises (H-60r): one object for every request that gets it."""


class H60Item(BaseModel):
    """The response model of ``GET /h60/broken-model``: a text and a number."""

    name: str
    count: int


@dataclass
class _SharedFailure:
    """A failure several requests share, the very same exception object, and what each request did with it (H-60r): put
    in its app's state by the test, read by the routes of the shared failure.

    ``held`` set: every call raises that one exception, requests one after the other. ``held`` None: the single flight of
    the portfolio engine (MF-J45b/d, ``financial_math/portfolio/engine.py``) over one key — the first request creates the
    future and runs the build, a request that finds the future awaits ``asyncio.shield`` on it, and the build's failure
    goes to the future (``set_exception``), so every waiting request receives the build's own exception. The build fails
    only once the second request waits: it awaits ``waiter_arrived``, which that request sets right before it awaits the
    future — no clock. With ``logs_its_failure`` the build logs its failure where it catches it, as code that follows the
    rule does: a warning with ``exc_info=True`` inside its ``except``, before the future gets it.
    """

    held: BaseException | None = None
    logs_its_failure: bool = False
    flight: asyncio.Future[None] | None = None
    waiter_arrived: asyncio.Event = field(default_factory=asyncio.Event)
    leader: str | None = None  # the request that ran the build, as its route recorded it
    waiter: str | None = None  # the request that waited on it
    got: dict[str | None, BaseException] = field(default_factory=dict)  # request id -> the exception its route received
    raised: dict[str | None, BaseException] = field(default_factory=dict)  # request id -> the exception its route raised


# =============================================================================
# THE ROUTES OF THE FRESH APPS
# =============================================================================
#
# Module-level endpoints (FastAPI caches the context of an endpoint by its id(): a function made per test and freed could
# lend its id to the next one). Each reads its canaries from its app's state, and leaves there the exception it raised.


def _route_logger() -> Any:
    """The routes' logger, asked at each use: never one structlog cached under an earlier configuration."""
    return get_logger(ROUTE_LOGGER)


async def h60_ok(request: Request) -> dict[str, Any]:
    """``GET /h60/ok``: one info line, and the request id its request's state holds."""
    _route_logger().info(ROUTE_LINE)
    return {"state_request_id": getattr(request.state, "request_id", None)}


async def h60_count(limit: int) -> dict[str, int]:
    """``GET /h60/count?limit=<int>``: anything else is FastAPI's 422."""
    return {"limit": limit}


async def h60_conflict() -> None:
    """``GET /h60/conflict``: a 409 of the route's own, with a header, raised from a cause: below 500 nothing changes."""
    try:
        raise LookupError("h60: the thing is already there")
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=CONFLICT_DETAIL, headers={CONFLICT_HEADER[0]: CONFLICT_HEADER[1]}) from exc


async def h60_failed(request: Request) -> None:
    """``/h60/failed``: a 503 with a ``Retry-After``, raised from a ``KeyError`` (the canary message) nobody logged."""
    await request.body()
    try:
        raise KeyError(request.app.state.canaries.message)
    except KeyError as exc:
        failure = HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL, headers={"Retry-After": RETRY_AFTER})
        request.app.state.raised = failure
        raise failure from exc


async def h60_reported_from_none(request: Request) -> None:
    """``GET /h60/reported-from-none``: the route logs a warning inside its ``except``, then raises its 503 ``from None``,
    as the app's routes do (AP-API-12, the backup routes)."""
    try:
        raise KeyError(request.app.state.canaries.message)
    except KeyError as exc:
        request.app.state.cause = exc
        _route_logger().warning(ROUTE_WARNING, route="from-none")
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from None


async def h60_reported_from_cause(request: Request) -> None:
    """``GET /h60/reported-from-cause``: the same warning, then the 503 raised ``from`` the ``KeyError``."""
    try:
        raise KeyError(request.app.state.canaries.message)
    except KeyError as exc:
        request.app.state.cause = exc
        _route_logger().warning(ROUTE_WARNING, route="from-cause")
        raise HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL) from exc


async def h60_bare(request: Request) -> None:
    """``/h60/bare``: a 500 the route means, ``HTTPException(500, "Failed")``, with no cause and nothing logged."""
    await request.body()
    failure = HTTPException(status_code=500, detail=BARE_DETAIL)
    request.app.state.raised = failure
    raise failure


async def h60_chain(request: Request) -> None:
    """``/h60/chain``: a 502 raised from an ``H60SourceError`` raised from an ``H60ComponentError``, which holds the root
    cause — an ``H60RootError`` with the canary message — in its ``cause`` attribute only, as AI Export's errors do."""
    await request.body()
    try:
        raise H60RootError(request.app.state.canaries.message)
    except H60RootError as caught:
        root = caught
    request.app.state.root = root
    # Raised outside the root's except: no __context__, the root is reachable through the attribute alone
    component_error = H60ComponentError(CHAIN_COMPONENT, root)
    try:
        try:
            raise component_error
        except H60ComponentError as built:
            raise H60SourceError("h60: the source failed") from built
    except H60SourceError as source:
        failure = HTTPException(status_code=502, detail=UPSTREAM_DETAIL)
        request.app.state.raised = failure
        raise failure from source


async def h60_unhandled(request: Request) -> None:
    """``/h60/unhandled``: a ``RuntimeError`` (the canary message) nobody handles."""
    await request.body()
    error = RuntimeError(request.app.state.canaries.message)
    request.app.state.raised = error
    raise error


async def h60_logged_then_raised(request: Request) -> None:
    """``GET /h60/logged-then-raised``: the route logs its ``RuntimeError`` at error with ``exc_info``, then lets it go."""
    try:
        raise RuntimeError(request.app.state.canaries.message)
    except RuntimeError as exc:
        request.app.state.raised = exc
        _route_logger().error(ROUTE_ERROR, exc_info=True)
        raise


async def h60_broken_stream(request: Request) -> StreamingResponse:
    """``GET /h60/broken-stream``: a streamed answer that sends its first chunk, then raises a ``RuntimeError``."""
    state = request.app.state
    message = state.canaries.message

    async def chunks() -> AsyncIterator[bytes]:
        yield FIRST_CHUNK
        error = RuntimeError(message)
        state.raised = error
        raise error

    return StreamingResponse(chunks(), media_type="text/plain")


async def h60_broken_model(request: Request) -> Any:
    """``GET /h60/broken-model``: a body ``H60Item`` refuses, the canary message where its number is due."""
    return {"name": "h60 item", "count": request.app.state.canaries.message}


async def _single_flight(request: Request, shared: _SharedFailure, request_id: str | None) -> None:
    """The build of ``shared``, one at a time for the requests that ask for it together, as MF-J45b/d runs it. It always
    fails, once the second request waits on it; which request leads is recorded, never assumed."""
    flight = shared.flight
    if flight is not None:
        # A build runs: wait for it, and let it fail now that this request waits
        shared.waiter = request_id
        shared.waiter_arrived.set()
        await asyncio.shield(flight)
        return
    flight = asyncio.get_running_loop().create_future()
    shared.flight = flight
    shared.leader = request_id
    try:
        await shared.waiter_arrived.wait()
        raise H60BuildError(request.app.state.canaries.message)
    except Exception as error:
        if shared.logs_its_failure:
            # The rule: logged once, where it is caught, with the traceback of the exception being handled
            _route_logger().warning(BUILD_FAILED, exc_info=True)
        # MF-J45d: the waiting requests get the build's own error, at once
        flight.set_exception(error)
        flight.exception()  # retrieved, as the engine does: no «never retrieved» warning
        raise


async def _the_shared_failure(request: Request, shared: _SharedFailure, request_id: str | None) -> None:
    """Raise the failure ``shared`` holds: its one held exception, or the single flight's."""
    if shared.held is not None:
        raise shared.held
    await _single_flight(request, shared, request_id)


async def h60_shared_failure_http(request: Request) -> None:
    """``/h60/shared-failure/http``: the failure its app's state shares (``_SharedFailure``), answered with a 503 of the
    route's own raised from it, as a route answers an engine's error; the route logs nothing."""
    await request.body()
    shared: _SharedFailure = request.app.state.shared_failure
    request_id = _request_id_of()(request)
    try:
        await _the_shared_failure(request, shared, request_id)
    except H60BuildError as exc:
        failure = HTTPException(status_code=503, detail=UNAVAILABLE_DETAIL)
        shared.got[request_id] = exc
        shared.raised[request_id] = failure
        raise failure from exc


async def h60_shared_failure_unhandled(request: Request) -> None:
    """``/h60/shared-failure/unhandled``: the failure its app's state shares, let go: nobody handles it, nobody logs it."""
    await request.body()
    shared: _SharedFailure = request.app.state.shared_failure
    request_id = _request_id_of()(request)
    try:
        await _the_shared_failure(request, shared, request_id)
    except H60BuildError as exc:
        shared.got[request_id] = exc
        shared.raised[request_id] = exc
        raise


#: (path, endpoint, methods, options) of every route of the fresh apps.
ROUTES: tuple[tuple[str, Callable[..., Any], tuple[str, ...], dict[str, Any]], ...] = (
    (OK_PATH, h60_ok, ("GET",), {}),
    (COUNT_PATH, h60_count, ("GET",), {}),
    (CONFLICT_PATH, h60_conflict, ("GET",), {}),
    (FAILED_PATH, h60_failed, ("GET", "POST"), {}),
    (FROM_NONE_PATH, h60_reported_from_none, ("GET",), {}),
    (FROM_CAUSE_PATH, h60_reported_from_cause, ("GET",), {}),
    (BARE_PATH, h60_bare, ("GET", "POST"), {}),
    (CHAIN_PATH, h60_chain, ("GET", "POST"), {}),
    (UNHANDLED_PATH, h60_unhandled, ("GET", "POST"), {}),
    (LOGGED_UNHANDLED_PATH, h60_logged_then_raised, ("GET",), {}),
    (STREAM_PATH, h60_broken_stream, ("GET",), {}),
    (MODEL_PATH, h60_broken_model, ("GET",), {"response_model": H60Item}),
    (SHARED_HTTP_PATH, h60_shared_failure_http, ("GET", "POST"), {}),
    (SHARED_UNHANDLED_PATH, h60_shared_failure_unhandled, ("GET", "POST"), {}),
)


# =============================================================================
# THE MODULES UNDER TEST, IMPORTED WHEN A TEST RUNS
# =============================================================================


def _module(name: str) -> ModuleType:
    """The new module ``name``, imported when a test needs it: before H-60 it does not exist, and the rest of this file
    must still be collected."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        if error.name != name:
            raise
    pytest.fail(f"H-60: {_MODULE_FILES[name]} is missing")


def _given(module: ModuleType, name: str) -> Any:
    """``module.name``, the test failing when the module does not give it."""
    value = getattr(module, name, None)
    if value is None:
        pytest.fail(f"H-60: {module.__name__} gives no {name}")
    return value


def _install() -> Callable[[FastAPI], None]:
    return _given(_module(SERVER_ERRORS_MODULE), "install_server_error_handler")


def _middleware_class() -> type:
    return _given(_module(REQUEST_ID_MODULE), "RequestIdMiddleware")


def _request_id_of() -> Callable[[Any], str | None]:
    return _given(_module(REQUEST_ID_MODULE), "request_id_of")


def _is_reported() -> Callable[[BaseException], bool]:
    return _given(_module(ERRORS_MODULE), "is_reported")


# =============================================================================
# APPS, CALLS, READINGS
# =============================================================================


def _stack_entry(name: str) -> MiddlewareEntry:
    """The one entry ``name`` of ``MIDDLEWARE_STACK``."""
    entries = [entry for entry in MIDDLEWARE_STACK if entry.name == name]
    assert len(entries) == 1, f"MIDDLEWARE_STACK must hold one entry named {name!r}: {[entry.name for entry in MIDDLEWARE_STACK]}"
    return entries[0]


def _app(*, server_errors: bool = True, stack: Sequence[MiddlewareEntry] | None = None) -> FastAPI:
    """A fresh app built as ``main.py`` builds its own: ``stack`` (default ``MIDDLEWARE_STACK``: ``activity``, the request
    id, the security headers, then the rest), A-35's 422 handler, H-33's handler and — unless ``server_errors`` is off,
    for FastAPI's own answers — H-60's; then ``ROUTES``, with canaries of its own in its state."""
    app = FastAPI()
    install_middleware(app, stack)
    install_validation_error_handler(app)
    install_response_validation_handler(app)
    if server_errors:
        _install()(app)
    app.state.canaries = _Canaries.new()
    for path, endpoint, methods, options in ROUTES:
        app.add_api_route(path, endpoint, methods=list(methods), **options)
    return app


async def _request(app: Any, method: str, path: str, *, raise_app_exceptions: bool = True, **options: Any) -> httpx.Response:
    """``method path`` on ``app`` in process, through httpx's ASGI transport, within ``CALL_SECONDS``. The app runs in
    the test's own task, on its context: a request id bound and never unbound would show in the lines after."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
    try:
        async with asyncio.timeout(CALL_SECONDS):
            async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
                return await client.request(method, path, **options)
    except TimeoutError:
        pytest.fail(f"{method} {path}: no answer within {CALL_SECONDS} s")


async def _together(app: Any, method: str, path: str, **options: Any) -> list[httpx.Response]:
    """Two requests ``method path`` at once: ``asyncio.gather`` through one client on ``app``'s ASGI transport, within
    ``CALL_SECONDS``, each request in a task of its own (its own contextvars, so its own bound request id).
    ``raise_app_exceptions`` off: an exception that leaves the app is answered, never raised here."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with asyncio.timeout(CALL_SECONDS):
            async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
                return await asyncio.gather(*(client.request(method, path, **options) for _ in range(2)))
    except TimeoutError:
        pytest.fail(f"{method} {path}, twice at once: no two answers within {CALL_SECONDS} s — a build waiting for a second request that never came")


@dataclass(frozen=True)
class _RawReply:
    """What the client of one raw ASGI call received, and what the app raised after it."""

    starts: list[tuple[int, list[tuple[str, str]]]]  # each http.response.start: its status, its header lines
    body: bytes
    raised: BaseException | None


async def _raw_get(app: Any, path: str) -> _RawReply:
    """``GET path`` as a server hands it over (ASGI spec 2.4, no ``Accept-Encoding``): every message the app sends kept,
    so that every response start is counted; the exception the app raises kept, never raised again."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"h60.test")],
        "client": ("127.0.0.1", 50000),
        "server": ("h60.test", 80),
    }
    complete = asyncio.Event()
    asked: list[bool] = []
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        if not asked:
            asked.append(True)
            return {"type": "http.request", "body": b"", "more_body": False}
        await complete.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            complete.set()

    raised: BaseException | None = None
    try:
        async with asyncio.timeout(CALL_SECONDS):
            await app(scope, receive, send)
    except TimeoutError:
        pytest.fail(f"GET {path}: the app did not end within {CALL_SECONDS} s")
    except Exception as exc:  # what the server would log: kept for the test
        raised = exc
    starts = [(message["status"], [(bytes(name).decode("latin-1").lower(), bytes(value).decode("latin-1")) for name, value in message.get("headers", ())]) for message in sent if message["type"] == "http.response.start"]
    body = b"".join(message.get("body", b"") for message in sent if message["type"] == "http.response.body")
    return _RawReply(starts=starts, body=body, raised=raised)


def _answer_request_id(response: httpx.Response, what: str) -> str:
    """The answer's one ``X-Request-Id``, checked to be 16 lowercase hex characters."""
    values = response.headers.get_list(REQUEST_ID_HEADER)
    assert len(values) == 1 and REQUEST_ID_SHAPE.fullmatch(values[0]), f"H-60 §3: {what}: every answer carries exactly one X-Request-Id of 16 lowercase hex characters (secrets.token_hex(8)); got {values!r}"
    return values[0]


def _media_type(response: httpx.Response) -> str:
    return response.headers.get("content-type", "").split(";")[0].strip().lower()


def _headers_but_the_id(response: httpx.Response) -> list[tuple[str, str]]:
    """Every header line of ``response`` but ``X-Request-Id``, sorted: what two answers to the same request share."""
    return sorted((name, value) for name, value in response.headers.multi_items() if name != REQUEST_ID_HEADER)


def _summary(events: list[dict[str, Any]]) -> list[tuple[Any, Any]]:
    return [(event.get("event"), event.get("log_level")) for event in events]


def _the_line(events: list[dict[str, Any]], name: str, level: str) -> dict[str, Any]:
    """The one captured line ``name``, at ``level``."""
    found = [event for event in events if event.get("event") == name]
    assert len(found) == 1, f"H-60: exactly one {name!r} expected; the capture holds {_summary(events)}"
    (event,) = found
    assert event.get("log_level") == level, f"H-60: {name!r} is written at level {level}, not {event.get('log_level')!r}"
    return event


def _server_error_lines(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The lines of the server-error handler and of the unhandled-error fallback among ``events``, H-60r's short line
    included."""
    return [event for event in events if event.get("event") in SERVER_ERROR_LINES]


def _ids_not_in_the_log(events: list[dict[str, Any]], ids: Sequence[str]) -> list[str]:
    """The ids among ``ids`` that no captured line carries as its ``request_id``: ids a client sees and the log lacks."""
    logged = {event.get("request_id") for event in events}
    return [request_id for request_id in ids if request_id not in logged]


def _with_a_traceback(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The captured lines that carry a traceback: a true ``exc_info`` (an exception, a tuple, ``True``)."""
    return [event for event in events if event.get("exc_info")]


def _fields(event: Mapping[str, Any], *names: str) -> dict[str, Any]:
    return {name: event.get(name) for name in names}


def _exc_info_exception(event: Mapping[str, Any]) -> BaseException | None:
    """The exception a line's ``exc_info`` names: the exception itself, or the value of a ``(type, value, traceback)``
    tuple; None for anything else (absent, True, False)."""
    exc_info = event.get("exc_info")
    if isinstance(exc_info, BaseException):
        return exc_info
    if isinstance(exc_info, tuple) and len(exc_info) == 3 and isinstance(exc_info[1], BaseException):
        return exc_info[1]
    return None


def _formatted(exc: BaseException) -> str:
    """The traceback of ``exc`` as Python renders it, its own ``__cause__`` and ``__context__`` chain included."""
    return "".join(traceback.format_exception(exc))


def _texts(value: object) -> Iterator[str]:
    """``repr`` and ``str`` of ``value`` and of everything inside it, where a canary could hide."""
    yield repr(value)
    yield str(value)
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _texts(key)
            yield from _texts(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _texts(item)


def _keys_anywhere(value: object) -> set[str]:
    """Every key of every mapping in ``value``, at any depth."""
    if isinstance(value, Mapping):
        return {str(key) for key in value} | {key for item in value.values() for key in _keys_anywhere(item)}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {key for item in value for key in _keys_anywhere(item)}
    return set()


def _canaries_outside_exc_info(events: list[dict[str, Any]], canaries: Sequence[str]) -> list[str]:
    """Where a canary stands in a captured line outside its ``exc_info``, as ``<line>.<key>: <canary>``."""
    return sorted({f"{event.get('event')!r}.{key}: {canary}" for event in events for key, value in event.items() if key != "exc_info" for canary in canaries if any(canary in text for text in _texts(value))})


def _same_handler(held: Any, registered: Any) -> bool:
    """The same handler: the very callable, or one built from the same code (a closure the install makes per app)."""
    code = getattr(registered, "__code__", None)
    return held is registered or (code is not None and getattr(held, "__code__", None) is code)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def _private_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every request of the test counts on an activity record of its own: ``current_activity()`` reads the module's
    ``ACTIVITY`` at each request, so the process's record of sleep and wake (workstream Z) is never touched."""
    monkeypatch.setattr(activity_module, "ACTIVITY", activity_module.Activity())


@pytest.fixture(autouse=True)
def _routes_write_every_level() -> Iterator[None]:
    """The routes' stdlib logger enabled from DEBUG for the test, whatever the lane's ``LOG_LEVEL``: the logging wrapper
    (H-60 §2) marks the failure a warning or an error reports only when its logger writes that level. Restored after."""
    stdlib_logger = logging.getLogger(ROUTE_LOGGER)
    before = stdlib_logger.level
    stdlib_logger.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        stdlib_logger.setLevel(before)


@pytest_asyncio.fixture
async def instance_app(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FastAPI]:
    """The real app, its database session replaced for the test (``dependency_overrides``, through monkeypatch) by one on
    an in-memory database with the ORM schema: never the lane's database. The instance not blocked. The session closed
    and the engine disposed on the way out."""
    monkeypatch.delenv("LIBREFOLIO_BLOCKED", raising=False)
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            monkeypatch.setitem(app_main.app.dependency_overrides, get_session_generator, lambda: session)
            yield app_main.app
    finally:
        await engine.dispose()


# =============================================================================
# §3 — THE REQUEST ID
# =============================================================================

#: One request for each kind of answer: its method and path, its status.
EVERY_KIND_OF_ANSWER: dict[str, tuple[str, str, int]] = {
    "a route's 200": ("GET", OK_PATH, 200),
    "the router's 404": ("GET", UNKNOWN_PATH, 404),
    "FastAPI's 422": ("GET", f"{COUNT_PATH}?limit=not-a-number", 422),
    "a 5xx a route raised": ("GET", FAILED_PATH, 503),
    "the 500 of an unhandled error": ("GET", UNHANDLED_PATH, 500),
}


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_every_answer_carries_a_request_id_of_its_own_never_the_clients():
    """§3: a route's 200, the router's 404, FastAPI's 422, a 5xx a route raised and the 500 of an error nobody handled
    each carry one ``X-Request-Id`` of 16 lowercase hex characters, a different one for each request — the last one
    because the security headers, which send that 500, stand inside the request-id layer (§3, amended: ``activity``,
    ``request_id``, ``security_headers``). Every request sends an ``X-Request-Id`` of the client's own, 16 hex characters
    too: no answer carries it. The 200's route finds the answer's id in ``request.state.request_id``."""
    print_section("H-60 §3: an X-Request-Id on every answer, new for each request, never the client's")
    app = _app()
    client_id = secrets.token_hex(8)

    # Inside a capture: the lines of the failing requests go nowhere
    with capture_logs(processors=[merge_contextvars]):
        answers = {kind: await _request(app, method, path, headers={"X-Request-Id": client_id}, raise_app_exceptions=False) for kind, (method, path, _status) in EVERY_KIND_OF_ANSWER.items()}

    statuses = {kind: response.status_code for kind, response in answers.items()}
    assert statuses == {kind: status for kind, (_method, _path, status) in EVERY_KIND_OF_ANSWER.items()}, f"barrier: each request gets the answer of its kind: {statuses}"
    ids = {kind: _answer_request_id(response, kind) for kind, response in answers.items()}
    assert client_id not in ids.values(), f"H-60 §3: the X-Request-Id the client sent ({client_id}) is ignored, never answered back: {ids}"
    assert len(set(ids.values())) == len(ids), f"H-60 §3: a new id for each request: {ids}"
    seen_by_the_route, answered_id = answers["a route's 200"].json(), ids["a route's 200"]
    assert seen_by_the_route == {"state_request_id": answered_id}, f"H-60 §3: the route reads the answer's id in request.state.request_id: {seen_by_the_route!r}, answered {answered_id}"
    print_success("five answers, five ids of their own, none the client's; request.state.request_id is the answer's")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_a_line_written_during_a_request_carries_its_id_and_a_line_after_it_does_not():
    """§3: the id is bound in structlog's contextvars for the whole request and unbound after. Two requests to a route
    that writes one line: each line carries its own request's id, the one its answer carries; a line the test writes
    after them carries no ``request_id`` at all."""
    print_section("H-60 §3: the request's id in its lines, and only in them")
    app = _app()

    with capture_logs(processors=[merge_contextvars]) as events:
        first = await _request(app, "GET", OK_PATH)
        second = await _request(app, "GET", OK_PATH)
        _route_logger().info(AFTER_LINE)

    ids = [_answer_request_id(first, "the first request"), _answer_request_id(second, "the second request")]
    route_lines = [event for event in events if event.get("event") == ROUTE_LINE]
    assert [event.get("request_id") for event in route_lines] == ids, f"H-60 §3: each line written during a request carries that request's id: {[event.get('request_id') for event in route_lines]} != {ids}"
    after = [event for event in events if event.get("event") == AFTER_LINE]
    assert len(after) == 1, f"barrier: the line written after the requests reaches the capture: {_summary(events)}"
    assert "request_id" not in after[0], f"H-60 §3: the id is unbound once its request ends; a line written after it carries {after[0].get('request_id')!r}"
    print_success("each line carries its request's id; the line after carries none")


# red until H-60: backend/app/services/platform/request_id.py is missing
@pytest.mark.asyncio
async def test_the_request_id_middleware_gives_its_id_to_the_scope_the_request_and_the_lines_and_logs_nothing():
    """§3, the middleware alone around a bare ASGI app. For each request the app finds the answer's id in
    ``scope["state"]["request_id"]``, and ``request_id_of`` gives it from the scope and from a ``Request`` on it; the line
    the app writes carries it; the client's ``X-Request-Id`` is never used. The middleware writes nothing of its own: the
    app's two lines are the whole capture."""
    print_section("H-60 §3: RequestIdMiddleware alone")
    middleware = _middleware_class()
    request_id_of = _request_id_of()
    seen: list[dict[str, Any]] = []

    async def bare_app(scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
        seen.append({"state": (scope.get("state") or {}).get("request_id"), "scope": request_id_of(scope), "request": request_id_of(Request(scope, receive))})
        _route_logger().info(ROUTE_LINE)
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"ok"})

    app = middleware(bare_app)
    client_id = secrets.token_hex(8)
    with capture_logs(processors=[merge_contextvars]) as events:
        first = await _request(app, "GET", BARE_ASGI_PATH, headers={"X-Request-Id": client_id})
        second = await _request(app, "GET", BARE_ASGI_PATH)

    ids = [_answer_request_id(first, "the first request"), _answer_request_id(second, "the second request")]
    assert ids[0] != ids[1] and client_id not in ids, f"H-60 §3: a new id for each request, never the client's ({client_id}): {ids}"
    assert seen == [{"state": request_id, "scope": request_id, "request": request_id} for request_id in ids], f"H-60 §3: the app finds the answer's id in scope['state'], and request_id_of gives it from the scope and from a Request: {seen} for {ids}"
    lines = [(event.get("event"), event.get("request_id")) for event in events]
    assert lines == [(ROUTE_LINE, request_id) for request_id in ids], f"H-60 §3: the app's line carries its request's id, and the middleware writes nothing of its own: {lines}"
    print_success("the id in the scope, the request and the line; no line of the middleware's own")


# red until H-60: backend/app/services/platform/request_id.py is missing
@pytest.mark.asyncio
async def test_an_x_request_id_the_app_set_is_kept_and_never_repeated():
    """§3: the header is added «unless one is already there». An app that sets its own ``x-request-id`` answers with it,
    once. Control: the same middleware around the same app without the header adds one."""
    print_section("H-60 §3: an X-Request-Id the app set is kept")
    middleware = _middleware_class()

    def answering(headers: list[tuple[bytes, bytes]]) -> Callable[..., Any]:
        async def bare_app(scope: dict[str, Any], receive: Callable[..., Any], send: Callable[..., Any]) -> None:
            await send({"type": "http.response.start", "status": 200, "headers": list(headers)})
            await send({"type": "http.response.body", "body": b"ok"})

        return bare_app

    added = await _request(middleware(answering([(b"content-type", b"text/plain")])), "GET", BARE_ASGI_PATH)
    own = await _request(middleware(answering([(b"content-type", b"text/plain"), (REQUEST_ID_HEADER.encode("ascii"), APP_REQUEST_ID.encode("ascii"))])), "GET", BARE_ASGI_PATH)

    _answer_request_id(added, "control: the app sets no X-Request-Id")
    assert (own.status_code, own.text) == (200, "ok"), f"barrier: the app answered: {own.status_code} {own.text!r}"
    assert own.headers.get_list(REQUEST_ID_HEADER) == [APP_REQUEST_ID], f"H-60 §3: the app's own X-Request-Id stays, the only one: {own.headers.get_list(REQUEST_ID_HEADER)}"
    print_success("the app's X-Request-Id kept, alone; one added where the app set none")


# red until H-60: backend/app/services/platform/request_id.py is missing
def test_request_id_of_reads_the_id_of_a_scope_or_a_request_and_none_without_one():
    """§3: ``request_id_of`` gives the id a scope's state holds, from the scope or from a ``Request`` on it, and None for a
    scope or a request that has none."""
    print_section("H-60 §3: request_id_of")
    request_id_of = _request_id_of()
    bare = {"type": "http", "method": "GET", "path": "/", "headers": [], "query_string": b""}
    stated = {**bare, "state": {"request_id": KNOWN_REQUEST_ID}}

    assert (request_id_of(stated), request_id_of(Request(stated))) == (KNOWN_REQUEST_ID, KNOWN_REQUEST_ID), "H-60 §3: request_id_of reads scope['state']['request_id'], from the scope and from a Request"
    assert (request_id_of(dict(bare)), request_id_of(Request(dict(bare)))) == (None, None), "H-60 §3: request_id_of is None for a scope or a request without an id"
    print_success("the id of a scope or a request; None without one")


#: kind -> (scope, the message the app receives, the messages the app sends).
NON_HTTP: dict[str, tuple[dict[str, Any], dict[str, Any], tuple[dict[str, Any], ...]]] = {
    "lifespan": (
        {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}, "state": {}},
        {"type": "lifespan.startup"},
        ({"type": "lifespan.startup.complete"},),
    ),
    "websocket": (
        {
            "type": "websocket",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "scheme": "ws",
            "path": "/h60/ws",
            "raw_path": b"/h60/ws",
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", b"h60.test")],
            "client": ("127.0.0.1", 50000),
            "server": ("h60.test", 80),
            "subprotocols": [],
        },
        {"type": "websocket.connect"},
        ({"type": "websocket.accept", "subprotocol": None, "headers": [(b"x-app", b"as the app sent it")]}, {"type": "websocket.close", "code": 1000, "reason": ""}),
    ),
}


# red until H-60: backend/app/services/platform/request_id.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(NON_HTTP))
async def test_a_scope_that_is_not_http_passes_the_request_id_middleware_untouched(kind: str):
    """§3: «Other scope types pass untouched». A ``lifespan`` or ``websocket`` scope reaches the app as it is — the same
    scope, unchanged (no state, no id), the same ``receive`` and ``send`` —, every message the app sends goes out
    unchanged (a WebSocket accept gets no header), and the app's line carries no id: nothing is bound."""
    print_section(f"H-60 §3: a {kind} scope through RequestIdMiddleware")
    middleware = _middleware_class()
    scope, incoming, outgoing = copy.deepcopy(NON_HTTP[kind])
    scope_before, outgoing_before = copy.deepcopy(scope), copy.deepcopy(outgoing)
    seen: list[tuple[Any, Any, Any]] = []
    received: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []

    async def bare_app(inner_scope: dict[str, Any], inner_receive: Callable[..., Any], inner_send: Callable[..., Any]) -> None:
        seen.append((inner_scope, inner_receive, inner_send))
        _route_logger().info(ROUTE_LINE)
        received.append(await inner_receive())
        for message in outgoing:
            await inner_send(message)

    async def receive() -> dict[str, Any]:
        return incoming

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    with capture_logs(processors=[merge_contextvars]) as events:
        async with asyncio.timeout(CALL_SECONDS):
            await middleware(bare_app)(scope, receive, send)

    assert len(seen) == 1, f"the app was called {len(seen)} times"
    inner_scope, inner_receive, inner_send = seen[0]
    assert inner_scope is scope and scope == scope_before, f"H-60 §3: the {kind} scope was replaced or changed: {inner_scope}"
    assert inner_receive is receive and inner_send is send, f"H-60 §3: receive or send of a {kind} scope was wrapped"
    assert received == [incoming], f"the app received {received}"
    assert sent == list(outgoing_before) and all(got is message for got, message in zip(sent, outgoing, strict=True)), f"H-60 §3: the messages of a {kind} scope were changed: {sent}"
    lines = [(event.get("event"), "request_id" in event) for event in events]
    assert lines == [(ROUTE_LINE, False)], f"H-60 §3: the app's line, no id bound, and no line of the middleware's own: {lines}"
    print_success("the same scope, receive and send; every message as the app sent it; no id bound")


# =============================================================================
# §4 — THE HANDLER OF HTTPException
# =============================================================================


# red until H-60: backend/app/api/server_errors.py is missing
def test_the_install_replaces_fastapis_http_exception_handler_and_nothing_else():
    """§4: on a fresh ``FastAPI()``, ``install_server_error_handler(app)`` replaces FastAPI's own handler for Starlette's
    ``HTTPException`` — the key the router's 404 and 405 and every route's ``HTTPException`` reach — with a callable of its
    own, and adds or changes nothing else: neither ``Exception`` nor ``500``, whose handler Starlette's
    ``ServerErrorMiddleware`` would run (an error nobody handled is answered by the security headers middleware, §5)."""
    print_section("H-60 §4: the install")
    install = _install()
    app = FastAPI()
    before = dict(app.exception_handlers)
    assert before.get(StarletteHTTPException) is http_exception_handler, f"Precondition: a fresh FastAPI() answers HTTPException with FastAPI's own handler: {before.get(StarletteHTTPException)!r}"

    install(app)

    after = dict(app.exception_handlers)
    added = sorted(repr(key) for key in set(after) - set(before))
    assert not added, f"H-60 §4: the install registers one handler, for Starlette's HTTPException, and nothing else: added {added}"
    handler = after[StarletteHTTPException]
    assert callable(handler) and handler is not http_exception_handler, f"H-60 §4: the install puts a handler of its own in place of FastAPI's for HTTPException: {handler!r}"
    changed = sorted(repr(key) for key in before if key is not StarletteHTTPException and after.get(key) is not before[key])
    assert not changed, f"H-60 §4: every other handler as it was: changed {changed}"
    print_success("FastAPI's HTTPException handler replaced; nothing added, nothing else changed")


#: The 4xx answers: their method and path, their status.
FOUR_XX: dict[str, tuple[str, str, int]] = {
    "the router's 404": ("GET", UNKNOWN_PATH, 404),
    "the router's 405": ("DELETE", OK_PATH, 405),
    "FastAPI's 422, without input": ("GET", f"{COUNT_PATH}?limit=not-a-number", 422),
    "a route's 409 raised from a cause": ("GET", CONFLICT_PATH, 409),
}


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_a_4xx_is_answered_exactly_as_fastapi_answers_it_and_logs_nothing():
    """§4, below 500: FastAPI's own answer, and no line. The router's 404 and 405, FastAPI's 422 (A-35's, without
    ``input``) and a route's 409 raised from a cause, with a header of its own, get the very bytes and headers a twin app
    without H-60's handler gives them — but the ``X-Request-Id``, which each carries. Barrier for the silence: a canary
    through the routes' logger reaches the same capture."""
    print_section("H-60 §4: a 4xx is FastAPI's own answer, without a line")
    app, twin = _app(), _app(server_errors=False)

    with capture_logs(processors=[merge_contextvars]) as events:
        _route_logger().info(CAPTURE_CANARY)
        answers = {kind: await _request(app, method, path) for kind, (method, path, _status) in FOUR_XX.items()}
        expected = {kind: await _request(twin, method, path) for kind, (method, path, _status) in FOUR_XX.items()}

    statuses = {kind: response.status_code for kind, response in answers.items()}
    assert statuses == {kind: status for kind, (_method, _path, status) in FOUR_XX.items()}, f"barrier: each request gets its 4xx: {statuses}"
    for kind, answer in answers.items():
        _answer_request_id(answer, kind)
        twin_answer = expected[kind]
        assert (answer.content, _headers_but_the_id(answer)) == (twin_answer.content, _headers_but_the_id(twin_answer)), f"H-60 §4: {kind} is FastAPI's own answer: {answer.content!r} {_headers_but_the_id(answer)} != {twin_answer.content!r} {_headers_but_the_id(twin_answer)}"
    assert answers["the router's 404"].json() == {"detail": "Not Found"}, answers["the router's 404"].text
    conflict = answers["a route's 409 raised from a cause"]
    assert (conflict.json(), conflict.headers.get(CONFLICT_HEADER[0])) == ({"detail": CONFLICT_DETAIL}, CONFLICT_HEADER[1]), f"a 409 keeps its body and its header: {conflict.text} {conflict.headers}"
    unprocessable = answers["FastAPI's 422, without input"].json().get("detail")
    assert isinstance(unprocessable, list) and unprocessable and all("input" not in error for error in unprocessable), f"a 422 without the request's input (A-35): {unprocessable!r}"
    assert any(event.get("event") == CAPTURE_CANARY for event in events), f"barrier: the routes' logger reaches the capture: {_summary(events)}"
    lines = [event for event in events if event.get("event") != CAPTURE_CANARY]
    assert lines == [], f"H-60 §4: below 500, no line: {_summary(lines)}"
    print_success("404, 405, 422 and 409 as FastAPI answers them, each with its X-Request-Id; no line")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_a_5xx_raised_from_a_cause_nobody_logged_names_the_cause_and_is_logged_once():
    """§4: ``HTTPException(503, …, headers={"Retry-After": "30"}) from KeyError(<canary>)``, nothing logged, asked with
    ``?token=<canary>``. The answer: JSON ``{"detail", "request_id": <its X-Request-Id>, "error_type": "KeyError"}`` with
    the ``Retry-After``. The log: exactly one error «Request failed» with the request's id, ``status`` 503, ``method``,
    ``path`` without the query, ``error_type`` ``KeyError``, ``error_chain`` from the ``HTTPException`` to the
    ``KeyError``, and as ``exc_info`` the shown error — here the ``HTTPException`` itself, no ``cause`` attribute on the
    way —, which is then marked reported."""
    print_section("H-60 §4: a 5xx from a cause nobody logged")
    app = _app()
    is_reported = _is_reported()
    canaries = app.state.canaries

    with capture_logs(processors=[merge_contextvars]) as events:
        response = await _request(app, "GET", FAILED_PATH, params={"token": canaries.token})

    request_id = _answer_request_id(response, f"GET {FAILED_PATH}")
    assert (response.status_code, _media_type(response)) == (503, "application/json"), f"H-60 §4: a JSON answer with the exception's status: {response.status_code} {response.headers.get('content-type')!r}"
    assert response.json() == {"detail": UNAVAILABLE_DETAIL, "request_id": request_id, "error_type": "KeyError"}, f"H-60 §4: the body is the detail, the request's id and the class of the root cause, nothing else: {response.text}"
    assert response.headers.get("retry-after") == RETRY_AFTER, f"H-60 §4: the exception's headers stay: {response.headers}"
    event = _the_line(events, REQUEST_FAILED, "error")
    assert _fields(event, "request_id", "status", "method", "path", "error_type") == {"request_id": request_id, "status": 503, "method": "GET", "path": FAILED_PATH, "error_type": "KeyError"}, f"H-60 §4: the line's request_id, status, method, path (never the query) and error_type: {event!r}"
    assert list(event.get("error_chain") or ()) == ["HTTPException", "KeyError"], f"H-60 §4: error_chain, the class names from the HTTPException to the root: {event.get('error_chain')!r}"
    raised = app.state.raised
    assert _exc_info_exception(event) is raised, f"H-60 §4: exc_info is the shown error, here the HTTPException itself: {event.get('exc_info')!r}"
    assert is_reported(raised), "H-60 §4: once logged, the exception is marked reported"
    assert _server_error_lines(events) == [event], f"H-60 §4: one line, once: {_summary(events)}"
    print_success("503 with request_id and error_type KeyError; one «Request failed» with the chain and the exception")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "error_type"),
    [
        pytest.param(FROM_NONE_PATH, None, id="raised-from-None"),
        pytest.param(FROM_CAUSE_PATH, "KeyError", id="raised-from-the-cause"),
    ],
)
async def test_a_5xx_whose_failure_the_route_already_logged_writes_no_line_of_its_own(path: str, error_type: str | None):
    """§4, «chain_reported → no line»: the route logs a warning inside its ``except KeyError``, then raises its 503. Raised
    ``from None``, no cause is visible: the body is ``{"detail", "request_id"}``; raised ``from`` the ``KeyError``, it
    adds ``error_type`` ``KeyError``. In both, the handler writes no line: the route's warning, written while the
    ``KeyError`` was being handled, already reported it (premise: the ``KeyError`` is marked). Barrier: the route's
    warning is in the same capture, with the request's id."""
    print_section(f"H-60 §4: a 5xx the route already logged ({path})")
    app = _app()
    is_reported = _is_reported()

    with capture_logs(processors=[merge_contextvars]) as events:
        response = await _request(app, "GET", path)

    request_id = _answer_request_id(response, f"GET {path}")
    expected = {"detail": UNAVAILABLE_DETAIL, "request_id": request_id} | ({} if error_type is None else {"error_type": error_type})
    assert (response.status_code, response.json()) == (503, expected), f"H-60 §4: {path}: expected 503 {expected}, got {response.status_code} {response.text}"
    warning = _the_line(events, ROUTE_WARNING, "warning")
    assert warning.get("request_id") == request_id, f"barrier: the route's warning is captured, with its request's id: {warning!r}"
    assert is_reported(app.state.cause), "Premise (H-60 §2): a warning written while the KeyError was being handled marks it reported"
    assert _server_error_lines(events) == [], f"H-60 §4: the failure is already reported, the handler writes no line: {_summary(events)}"
    print_success(f"503 {sorted(expected)}; the route's warning alone")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_a_5xx_without_a_cause_is_answered_with_its_id_and_logged_as_a_warning():
    """§4: a bare ``HTTPException(500, "Failed")``, nothing logged, no cause. The body is ``{"detail": "Failed",
    "request_id"}`` — no ``error_type`` —, and the log one warning «Request answered a server error» with the request's
    id, ``status``, ``method`` and ``path``, without ``exc_info``: every 5xx's id is in at least one line."""
    print_section("H-60 §4: a 5xx without a cause")
    app = _app()

    with capture_logs(processors=[merge_contextvars]) as events:
        response = await _request(app, "GET", BARE_PATH)

    request_id = _answer_request_id(response, f"GET {BARE_PATH}")
    assert (response.status_code, response.json()) == (500, {"detail": BARE_DETAIL, "request_id": request_id}), f"H-60 §4: the detail and the request's id, no error_type: {response.status_code} {response.text}"
    event = _the_line(events, SERVER_ERROR_ANSWERED, "warning")
    assert _fields(event, "request_id", "status", "method", "path") == {"request_id": request_id, "status": 500, "method": "GET", "path": BARE_PATH}, f"H-60 §4: the warning's request_id, status, method and path: {event!r}"
    assert not event.get("exc_info"), f"H-60 §4: no exc_info on the warning: {event.get('exc_info')!r}"
    assert _server_error_lines(events) == [event], f"H-60 §4: one line: {_summary(events)}"
    print_success("500 with its request_id; one warning, no traceback")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_a_root_cause_held_in_a_cause_attribute_is_the_error_type_and_the_exc_info():
    """§4 with §0, an AI-Export-like chain: ``HTTPException(502) from H60SourceError from H60ComponentError``, the
    component's error holding the root cause, an ``H60RootError``, in its ``cause`` attribute only. ``error_type`` is the
    root's, in the body and in the one «Request failed»; ``error_chain`` names the four classes in order; ``exc_info`` is
    the root (the shown error: the last one reached through a ``cause`` attribute, whose traceback Python would never
    render from the ``HTTPException``). The ``HTTPException`` and the root are both marked reported."""
    print_section("H-60 §4: a root cause behind a cause attribute")
    app = _app()
    is_reported = _is_reported()

    with capture_logs(processors=[merge_contextvars]) as events:
        response = await _request(app, "GET", CHAIN_PATH)

    request_id = _answer_request_id(response, f"GET {CHAIN_PATH}")
    assert (response.status_code, response.json()) == (502, {"detail": UPSTREAM_DETAIL, "request_id": request_id, "error_type": "H60RootError"}), f"H-60 §4: error_type is the root cause's class, found through the cause attribute: {response.status_code} {response.text}"
    event = _the_line(events, REQUEST_FAILED, "error")
    assert _fields(event, "request_id", "status", "error_type") == {"request_id": request_id, "status": 502, "error_type": "H60RootError"}, f"H-60 §4: {event!r}"
    assert list(event.get("error_chain") or ()) == ["HTTPException", "H60SourceError", "H60ComponentError", "H60RootError"], f"H-60 §4: the chain from the HTTPException to the root: {event.get('error_chain')!r}"
    root = app.state.root
    assert _exc_info_exception(event) is root, f"H-60 §4: exc_info is the shown error, the root reached through the cause attribute: {event.get('exc_info')!r}"
    assert is_reported(app.state.raised) and is_reported(root), "H-60 §4: the HTTPException and the shown error are both marked reported"
    print_success("error_type H60RootError; the chain of four; exc_info the root, marked")


# =============================================================================
# §5 — AN ERROR NOBODY HANDLED
# =============================================================================


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_an_unhandled_error_is_a_json_500_logged_once_and_still_raised_marked():
    """§5: a ``RuntimeError`` nobody handles, asked with ``?token=<canary>``. With ``raise_app_exceptions`` off, the
    answer is a JSON 500 ``{"detail": "Internal Server Error", "request_id", "error_type": "RuntimeError"}``, ``nosniff``
    still on it, its ``X-Request-Id`` the body's ``request_id`` — the security headers that send it stand inside the
    request-id layer (§3, amended) —, and the log one error «Unhandled error» with the request's id, ``method``, ``path``
    without the query, ``error_type``, ``error_chain`` and the exception as ``exc_info``. With the default transport the
    very exception still reaches the caller — a server would log it, and the filter of §2 drops that duplicate —, marked
    reported."""
    print_section("H-60 §5: an error nobody handled")
    app = _app()
    is_reported = _is_reported()

    with capture_logs(processors=[merge_contextvars]) as events:
        answered = await _request(app, "GET", UNHANDLED_PATH, params={"token": app.state.canaries.token}, raise_app_exceptions=False)

    request_id = _answer_request_id(answered, f"GET {UNHANDLED_PATH}")
    assert (answered.status_code, _media_type(answered)) == (500, "application/json"), f"H-60 §5: a JSON 500: {answered.status_code} {answered.headers.get('content-type')!r} {answered.text[:300]}"
    assert answered.json() == {"detail": INTERNAL, "request_id": request_id, "error_type": "RuntimeError"}, f"H-60 §5: {answered.text}"
    assert answered.headers.get("x-content-type-options") == "nosniff", f"the security headers stay on the 500: {answered.headers}"
    event = _the_line(events, UNHANDLED, "error")
    assert _fields(event, "request_id", "method", "path", "error_type") == {"request_id": request_id, "method": "GET", "path": UNHANDLED_PATH, "error_type": "RuntimeError"}, f"H-60 §5: {event!r}"
    assert list(event.get("error_chain") or ()) == ["RuntimeError"], f"H-60 §5: {event.get('error_chain')!r}"
    assert _exc_info_exception(event) is app.state.raised, f"H-60 §5: exc_info is the exception: {event.get('exc_info')!r}"
    assert _server_error_lines(events) == [event], f"H-60 §5: one line: {_summary(events)}"

    with capture_logs(processors=[merge_contextvars]) as again, pytest.raises(RuntimeError) as raised:
        await _request(app, "GET", UNHANDLED_PATH)

    assert raised.value is app.state.raised, f"H-60 §5: the very exception is raised again, for the server: {raised.value!r}"
    assert is_reported(raised.value), "H-60 §5: the exception that leaves the app is marked reported, so uvicorn's duplicate is dropped"
    assert [event.get("event") for event in _server_error_lines(again)] == [UNHANDLED], f"H-60 §5: {_summary(again)}"
    print_success("JSON 500 with request_id and error_type; one «Unhandled error»; the exception still raised, marked")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_an_unhandled_error_after_the_answer_started_is_logged_once_and_still_raised():
    """§5, the answer already started: a streamed answer sends its start and its first chunk, then its generator raises a
    ``RuntimeError``. No second answer — one response start, 200, the first chunk only —; one error «Unhandled error»
    with the request's id, the path, ``RuntimeError`` and the exception as ``exc_info``; the very exception raised again
    to the server, marked reported. A raw ASGI call: every response start is counted."""
    print_section("H-60 §5: an error nobody handled, after the answer started")
    app = _app()
    is_reported = _is_reported()

    with capture_logs(processors=[merge_contextvars]) as events:
        reply = await _raw_get(app, STREAM_PATH)

    assert [status for status, _headers in reply.starts] == [200], f"H-60 §5: once the answer started, no second answer: response starts {reply.starts!r}"
    assert reply.body == FIRST_CHUNK, f"barrier: the stream sent its first chunk, then broke: {reply.body!r}"
    request_ids = [value for name, value in reply.starts[0][1] if name == REQUEST_ID_HEADER]
    assert len(request_ids) == 1 and REQUEST_ID_SHAPE.fullmatch(request_ids[0]), f"H-60 §3: the streamed answer carries its X-Request-Id: {request_ids}"
    raised = reply.raised
    assert isinstance(raised, RuntimeError) and raised is getattr(app.state, "raised", None), f"H-60 §5: the very exception still reaches the server: {raised!r}"
    event = _the_line(events, UNHANDLED, "error")
    assert _fields(event, "request_id", "method", "path", "error_type") == {"request_id": request_ids[0], "method": "GET", "path": STREAM_PATH, "error_type": "RuntimeError"}, f"H-60 §5: {event!r}"
    assert _exc_info_exception(event) is raised, f"H-60 §5: exc_info is the exception: {event.get('exc_info')!r}"
    assert is_reported(raised), "H-60 §5: marked reported, after a started answer too"
    print_success("one start, the first chunk; one «Unhandled error»; the exception still raised, marked")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_an_unhandled_error_the_route_already_logged_is_answered_but_not_logged_again():
    """§5, «unless is_reported(exc)»: the route logs its ``RuntimeError`` at error with ``exc_info`` and lets it go. The
    answer is the same JSON 500; the only line is the route's (premise: it marked the exception reported) — no
    «Unhandled error». Barrier: the route's line in the same capture."""
    print_section("H-60 §5: an error the route already logged")
    app = _app()
    is_reported = _is_reported()

    with capture_logs(processors=[merge_contextvars]) as events:
        answered = await _request(app, "GET", LOGGED_UNHANDLED_PATH, raise_app_exceptions=False)

    request_id = _answer_request_id(answered, f"GET {LOGGED_UNHANDLED_PATH}")
    assert (answered.status_code, answered.json()) == (500, {"detail": INTERNAL, "request_id": request_id, "error_type": "RuntimeError"}), f"H-60 §5: {answered.status_code} {answered.text}"
    route_error = _the_line(events, ROUTE_ERROR, "error")
    assert route_error.get("request_id") == request_id, f"barrier: the route's line is captured, with its request's id: {route_error!r}"
    assert is_reported(app.state.raised), "Premise (H-60 §2): an error written with exc_info=True marks the exception being handled"
    assert _server_error_lines(events) == [], f"H-60 §5: already reported, not logged again: {_summary(events)}"
    print_success("the JSON 500; the route's line alone")


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "status", "body"),
    [
        pytest.param(FAILED_PATH, 503, {"detail": UNAVAILABLE_DETAIL, "error_type": "KeyError"}, id="5xx-from-a-cause"),
        pytest.param(UNHANDLED_PATH, 500, {"detail": INTERNAL, "error_type": "RuntimeError"}, id="unhandled-error"),
    ],
)
async def test_without_a_request_id_a_5xx_body_has_no_request_id_key(path: str, status: int, body: dict[str, Any]):
    """§4 and §5, «request_id absent when the request has none»: on an app whose stack is the security headers alone —
    no request-id middleware —, a 5xx from a cause and an unhandled error are answered without a ``request_id`` key.
    Barriers: no ``X-Request-Id`` on the answer, ``nosniff`` on it."""
    print_section(f"H-60 §4-§5: GET {path} without a request id")
    app = _app(stack=(_stack_entry("security_headers"),))

    with capture_logs(processors=[merge_contextvars]):
        answered = await _request(app, "GET", path, raise_app_exceptions=False)

    assert REQUEST_ID_HEADER not in answered.headers, f"barrier: this app gives no request id: {answered.headers}"
    assert answered.headers.get("x-content-type-options") == "nosniff", f"barrier: the security headers answered: {answered.headers}"
    assert (answered.status_code, answered.json()) == (status, body), f"H-60: without a request id the body has no request_id key: {answered.status_code} {answered.text}"
    print_success(f"{status} {sorted(body)}")


# =============================================================================
# §6 — A RESPONSE THAT BREAKS ITS MODEL (H-33)
# =============================================================================


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
async def test_a_response_that_breaks_its_model_is_a_json_500_with_its_request_id():
    """§6: a route whose answer ``H60Item`` refuses (the canary message where a number is due) is answered with JSON
    ``{"detail": "Internal Server Error", "request_id": <its X-Request-Id>, "error_type": "ResponseValidationError"}``.
    Nowhere an ``input`` nor the refused value: not in the answer, not in a line. H-33's line is there once, with the
    request's id, and it is the only line: the error never reaches the fallback of §5."""
    print_section("H-60 §6: the 500 of a response that breaks its model")
    app = _app()
    refused = app.state.canaries.message

    with capture_logs(processors=[merge_contextvars]) as events:
        response = await _request(app, "GET", MODEL_PATH)

    request_id = _answer_request_id(response, f"GET {MODEL_PATH}")
    assert (response.status_code, _media_type(response)) == (500, "application/json"), f"H-60 §6: a JSON 500: {response.status_code} {response.headers.get('content-type')!r} {response.text[:300]}"
    assert response.json() == {"detail": INTERNAL, "request_id": request_id, "error_type": "ResponseValidationError"}, f"H-60 §6: {response.text}"
    assert refused not in response.text, "H-60 §6: the refused value is not in the answer"
    event = _the_line(events, MODEL_BROKEN, "error")
    assert event.get("request_id") == request_id, f"H-60 §3: H-33's line carries its request's id: {event!r}"
    assert "input" not in _keys_anywhere(events), f"H-33: no input in any line: {events!r}"
    assert not _canaries_outside_exc_info(events, (refused,)) and not any(captured.get("exc_info") for captured in events), "H-33: the refused value in no line, and no traceback"
    assert [captured.get("event") for captured in events] == [MODEL_BROKEN], f"H-60 §6: H-33's line alone: {_summary(events)}"
    print_success("JSON 500 with request_id and ResponseValidationError; H-33's line alone, without the value")


# =============================================================================
# SECURITY (D2): NO SECRET OF THE REQUEST IN AN ANSWER OR A LINE
# =============================================================================

#: The failing routes the security test asks: what each answers, the line it writes and that line's level.
LEAK_CASES = [
    pytest.param(FAILED_PATH, 503, REQUEST_FAILED, "error", id="5xx-from-a-cause-nobody-logged"),
    pytest.param(BARE_PATH, 500, SERVER_ERROR_ANSWERED, "warning", id="5xx-without-a-cause"),
    pytest.param(CHAIN_PATH, 502, REQUEST_FAILED, "error", id="5xx-from-a-cause-attribute-chain"),
    pytest.param(UNHANDLED_PATH, 500, UNHANDLED, "error", id="unhandled-error"),
]


# red until H-60: backend/app/api/server_errors.py is missing
@pytest.mark.asyncio
@pytest.mark.parametrize(("path", "status", "line", "level"), LEAK_CASES)
async def test_no_secret_of_the_request_reaches_an_answer_or_a_line_and_the_message_only_the_traceback(path: str, status: int, line: str, level: str):
    """D2, §4 and §5, the developer's question («quello che printiamo non viola la sicurezza esponendo dati sensibili
    vero?»). ``POST path?token=<canary>`` with ``Authorization: Bearer <canary>``, ``Cookie: s=<canary>`` and the body
    ``{"password": <canary>}``; the route's exception carries a canary message. No canary in the answer, body or header;
    none in any captured line outside its ``exc_info`` (the ``path`` without the query). The exception's message lives
    in the traceback only: a line about a cause renders it from its ``exc_info``. Barriers: the route answered its
    status, and its line is there."""
    print_section(f"H-60 security: POST {path} with a canary everywhere")
    app = _app()
    canaries = app.state.canaries

    with capture_logs(processors=[merge_contextvars]) as events:
        response = await _request(
            app,
            "POST",
            path,
            params={"token": canaries.token},
            headers={"Authorization": f"Bearer {canaries.authorization}", "Cookie": f"s={canaries.cookie}"},
            json={"password": canaries.password},
            raise_app_exceptions=False,
        )

    assert response.status_code == status, f"barrier: POST {path} answered {response.status_code}, not {status}: {response.text[:300]}"
    event = _the_line(events, line, level)
    assert _fields(event, "method", "path") == {"method": "POST", "path": path}, f"H-60: the line's method and path, without the query: {event!r}"
    answer = f"{response.text}\n{response.headers.multi_items()!r}"
    in_the_answer = [canary for canary in canaries.every() if canary in answer]
    assert not in_the_answer, f"H-60 (D2): the answer carries {in_the_answer}: {answer[:500]}"
    outside = _canaries_outside_exc_info(events, canaries.every())
    assert not outside, f"H-60: a line carries a secret of the request, or the exception's message, outside exc_info: {outside}"
    if line != SERVER_ERROR_ANSWERED:
        shown = _exc_info_exception(event)
        assert shown is not None and canaries.message in _formatted(shown), f"H-60: the exception's message lives in the traceback the line's exc_info renders: {event.get('exc_info')!r}"
    print_success(f"{status}: no canary in the answer; the message only in the traceback")


# =============================================================================
# H-60r §2 — ONE FAILURE, SEVERAL REQUESTS: THE SAFETY NET PER REQUEST
# =============================================================================


@dataclass(frozen=True)
class _Branch:
    """How the routes of a shared failure answer it, and what the log then holds (H-60r §2): with a 503 of their own
    raised from it, answered by §4's handler (``report_server_error``), or not at all, the failure leaving the app for
    §5's fallback (``report_unhandled_error``), whose lines carry no ``status``."""

    path: str
    status: int
    detail: Any
    failed_line: str  # H-60's line of the request that answers the failure first: the one with the traceback
    error_chain: tuple[str, ...]  # that line's error_chain
    with_status: bool  # whether this branch's lines carry the status

    def about(self, request_id: str | None, method: str = "GET") -> dict[str, Any]:
        """The request a line of this branch is about: ``request_id``, ``status`` when the branch's lines carry it,
        ``method``, ``path`` without the query."""
        return {"request_id": request_id, **({"status": self.status} if self.with_status else {}), "method": method, "path": self.path}

    def short_line(self, request_id: str | None, logged_with: str | None, method: str = "GET") -> dict[str, Any]:
        """The short line of ``request_id`` as captured, whole (H-60r §2, case 2): its request, ``error_type`` the build's
        error and ``logged_with_request_id`` the request whose line has the failure; no ``exc_info``, no ``error_chain``,
        nothing else."""
        return {"event": ALREADY_LOGGED, "log_level": "warning", **self.about(request_id, method), "error_type": H60BuildError.__name__, "logged_with_request_id": logged_with}


#: The shared failure answered with ``raise HTTPException(503, ...) from`` it: §4's handler writes the lines.
HTTP_BRANCH = _Branch(path=SHARED_HTTP_PATH, status=503, detail=UNAVAILABLE_DETAIL, failed_line=REQUEST_FAILED, error_chain=("HTTPException", H60BuildError.__name__), with_status=True)
#: The shared failure let go: the security headers answer it and write the lines (§5), without a status.
UNHANDLED_BRANCH = _Branch(path=SHARED_UNHANDLED_PATH, status=500, detail=INTERNAL, failed_line=UNHANDLED, error_chain=(H60BuildError.__name__,), with_status=False)
BRANCHES = [pytest.param(HTTP_BRANCH, id="a-503-raised-from-it"), pytest.param(UNHANDLED_BRANCH, id="let-go-unhandled")]


def _shared_failure_answers(answers: Sequence[httpx.Response], branch: _Branch, method: str = "GET") -> list[str]:
    """The request ids of ``answers``, in their order: each answer is ``branch``'s JSON answer to the shared failure — its
    status, its detail, its own ``X-Request-Id`` as ``request_id``, ``error_type`` the build's error —, each id new."""
    ids: list[str] = []
    for answer in answers:
        request_id = _answer_request_id(answer, f"{method} {branch.path}")
        assert (answer.status_code, _media_type(answer)) == (branch.status, "application/json"), f"H-60: {method} {branch.path} is answered a JSON {branch.status}: {answer.status_code} {answer.headers.get('content-type')!r} {answer.text[:300]}"
        expected = {"detail": branch.detail, "request_id": request_id, "error_type": H60BuildError.__name__}
        assert answer.json() == expected, f"H-60: each answer carries its own request id and the build's error type: {answer.text} != {expected}"
        ids.append(request_id)
    assert len(set(ids)) == len(ids), f"H-60 §3: a new id for each request: {ids}"
    return ids


def _shared_by_both(shared: _SharedFailure, ids: Sequence[str]) -> None:
    """Premise of the concurrent tests: one request ran the build and the other waited on it, as the route recorded —
    never assumed —, and both received the very same exception object (MF-J45d)."""
    roles = [shared.leader, shared.waiter]
    assert None not in roles and sorted(roles) == sorted(ids), f"premise: one request led the build and the other waited on it: leader {shared.leader}, waiter {shared.waiter}, answers {ids}"
    error = shared.got.get(shared.leader)
    assert isinstance(error, H60BuildError) and shared.got.get(shared.waiter) is error, f"premise: the build's own exception, one object, reached both requests: {shared.got!r}"


def _check_the_failed_line(failed: Mapping[str, Any], branch: _Branch, shared: _SharedFailure, request_id: str) -> None:
    """``failed`` is H-60's line of ``branch`` for ``request_id``, which H-60r leaves as it is (case 3), whole: its
    request, ``error_type`` the build's error, ``error_chain``, and as ``exc_info``, by identity, the shown error — the
    exception that request's route raised, whose traceback renders the build's error."""
    rest = {key: value for key, value in failed.items() if key not in ("exc_info", "error_chain")}
    expected = {"event": branch.failed_line, "log_level": "error", **branch.about(request_id), "error_type": H60BuildError.__name__}
    assert rest == expected, f"H-60: the line with the traceback, whole but its exc_info and error_chain: {rest!r} != {expected!r}"
    assert list(failed.get("error_chain") or ()) == list(branch.error_chain), f"H-60: error_chain, from the exception answered to the build's: {failed.get('error_chain')!r}"
    shown = shared.raised.get(request_id)
    assert shown is not None and _exc_info_exception(failed) is shown, f"H-60: exc_info is the shown error, the exception the route of {request_id} raised: {failed.get('exc_info')!r}"


# red until H-60r: answered with a 503, both requests write «Request failed», the build's traceback twice; let go, the
# request that answers second writes nothing and its id is in no line
@pytest.mark.asyncio
@pytest.mark.parametrize("branch", BRANCHES)
async def test_two_requests_failing_together_on_one_build_nobody_logged_both_leave_their_id_and_one_traceback(branch: _Branch):
    """H-60r §2, the review's red: «two requests on the same build key that fail together must both leave their id in the
    log». Two requests at once, asked with ``?token=<canary>``, on one single-flight build (MF-J45b/d) that fails without
    a line; the same exception object reaches both (premise), whose routes answer it with a 503 raised from it, or let it
    go. Each answer carries its own id. The request that answers first — read from the line, never assumed — writes
    H-60's line with the traceback (case 3); the other writes the short line (case 2), whole: its own id, its request
    (``path`` without the query; ``status`` only through a 503), ``error_type``, and ``logged_with_request_id`` the first
    one's id; no ``exc_info``, no ``error_chain``. These are the two lines of the safety net, and the only traceback."""
    print_section(f"H-60r §2: two requests fail together on one build nobody logged ({branch.path})")
    app = _app()
    shared = app.state.shared_failure = _SharedFailure()

    with capture_logs(processors=[merge_contextvars]) as events:
        answers = await _together(app, "GET", branch.path, params={"token": app.state.canaries.token})

    ids = _shared_failure_answers(answers, branch)
    _shared_by_both(shared, ids)
    missing = _ids_not_in_the_log(events, ids)
    assert not missing, f"H-60r §2: every request id a client sees is in the log; in no line: {missing} — {_summary(events)}"
    failed = _the_line(events, branch.failed_line, "error")
    first = failed.get("request_id")
    assert first in ids, f"H-60r §2: the line with the traceback is one of the two requests': {first!r}, answers {ids}"
    (second,) = [request_id for request_id in ids if request_id != first]
    _check_the_failed_line(failed, branch, shared, first)
    short = _the_line(events, ALREADY_LOGGED, "warning")
    expected = branch.short_line(second, logged_with=first)
    assert short == expected, f"H-60r §2: the other request's short line, whole, pointing to the first: {short!r} != {expected!r}"
    others = [line for line in _server_error_lines(events) if line is not failed and line is not short]
    assert not others, f"H-60r §2: these two lines, nothing more: {_summary(others)}"
    tracebacks = _with_a_traceback(events)
    assert len(tracebacks) == 1 and tracebacks[0] is failed, f"H-60r: the build's traceback is written once: {_summary(tracebacks)}"
    print_success(f"two answers, two ids in the log: «{branch.failed_line}» with the traceback, one short line pointing to it")


# red until H-60r: the waiter writes nothing, its id is in no line
@pytest.mark.asyncio
@pytest.mark.parametrize("branch", BRANCHES)
async def test_two_requests_failing_together_on_one_build_that_logged_it_the_waiter_points_to_the_builds_line(branch: _Branch):
    """H-60r §2, the build following the rule: it logs its failure where it catches it, a warning with ``exc_info=True``
    inside its ``except``, before the request waiting on it gets the failure. That line carries the leader's id, bound in
    its request's contextvars, and the traceback (barrier). The leader's handler then writes nothing (case 1: its
    request's log has the failure); the waiter's writes the short line (case 2), whole, its own id and
    ``logged_with_request_id`` the leader's. Both ids are in the log, the traceback once: the build's line alone carries
    it."""
    print_section(f"H-60r §2: two requests fail together on one build that logged its failure ({branch.path})")
    app = _app()
    shared = app.state.shared_failure = _SharedFailure(logs_its_failure=True)

    with capture_logs(processors=[merge_contextvars]) as events:
        answers = await _together(app, "GET", branch.path, params={"token": app.state.canaries.token})

    ids = _shared_failure_answers(answers, branch)
    _shared_by_both(shared, ids)
    build_line = _the_line(events, BUILD_FAILED, "warning")
    without_exc_info = {key: value for key, value in build_line.items() if key != "exc_info"}
    assert without_exc_info == {"event": BUILD_FAILED, "log_level": "warning", "request_id": shared.leader} and build_line.get("exc_info"), f"barrier: the build logs its failure with the traceback, in the leader's request ({shared.leader}): {build_line!r}"
    missing = _ids_not_in_the_log(events, ids)
    assert not missing, f"H-60r §2: every request id a client sees is in the log; in no line: {missing} (the waiter: {shared.waiter}) — {_summary(events)}"
    short = _the_line(events, ALREADY_LOGGED, "warning")
    expected = branch.short_line(shared.waiter, logged_with=shared.leader)
    assert short == expected, f"H-60r §2: the waiter's short line, whole, pointing to the leader: {short!r} != {expected!r}"
    platform = _server_error_lines(events)
    assert len(platform) == 1 and platform[0] is short, f"H-60r §2: the leader's handler writes nothing, the waiter's the short line alone: {_summary(platform)}"
    tracebacks = _with_a_traceback(events)
    assert len(tracebacks) == 1 and tracebacks[0] is build_line, f"H-60r: the traceback is written once, by the build: {_summary(tracebacks)}"
    print_success("the build's line with the leader's id and the traceback; the waiter's short line points to it; the leader writes nothing")


# red until H-60r: let go, the later requests write nothing and their ids are in no line; answered with a 503, every
# request writes «Request failed» and the traceback again
@pytest.mark.asyncio
@pytest.mark.parametrize("branch", BRANCHES)
async def test_one_exception_object_raised_request_after_request_is_written_once_and_each_later_request_points_to_the_first(branch: _Branch):
    """H-60r §2, one object request after request: the route raises, on every call, the one ``H60BuildError`` its app's
    state holds, nobody logging it, and answers it with a 503 raised from it, or lets it go. Three requests, one after the
    other, each answered with its own id. The first writes H-60's line with the traceback (case 3); the second and the
    third each write the short line (case 2), whole, with their own id and ``logged_with_request_id`` the first one's —
    the request whose line has the traceback, never the latest one. These are the lines of the safety net, one for each
    request, and the only traceback."""
    print_section(f"H-60r §2: one exception object raised by request after request ({branch.path})")
    app = _app()
    held = H60BuildError(app.state.canaries.message)
    shared = app.state.shared_failure = _SharedFailure(held=held)

    with capture_logs(processors=[merge_contextvars]) as events:
        answers = [await _request(app, "GET", branch.path, raise_app_exceptions=False) for _ in range(SEQUENTIAL_REQUESTS)]

    ids = _shared_failure_answers(answers, branch)
    assert all(shared.got.get(request_id) is held for request_id in ids), f"premise: every request received the one held exception: {shared.got!r}"
    missing = _ids_not_in_the_log(events, ids)
    assert not missing, f"H-60r §2: every request id a client sees is in the log; in no line: {missing} — {_summary(events)}"
    first, *later = ids
    failed = _the_line(events, branch.failed_line, "error")
    _check_the_failed_line(failed, branch, shared, first)
    shorts = [event for event in events if event.get("event") == ALREADY_LOGGED]
    expected = [branch.short_line(request_id, logged_with=first) for request_id in later]
    assert shorts == expected, f"H-60r §2: each later request's short line, whole, pointing to the first: {shorts!r} != {expected!r}"
    platform = _server_error_lines(events)
    assert len(platform) == len(ids), f"H-60r §2: one line for each request, nothing more: {_summary(platform)}"
    tracebacks = _with_a_traceback(events)
    assert len(tracebacks) == 1 and tracebacks[0] is failed, f"H-60r: the traceback is written once, by the first request: {_summary(tracebacks)}"
    print_success(f"{len(ids)} requests, {len(ids)} ids in the log: «{branch.failed_line}» once, then short lines pointing to it")


# red until H-60r: the second request writes no short line
@pytest.mark.asyncio
@pytest.mark.parametrize("branch", BRANCHES)
async def test_the_short_line_holds_no_secret_of_the_request_nor_the_exceptions_message(branch: _Branch):
    """H-60r §2 with D2: «every short line holds no traceback, no exception message, no query string, no header and no
    body». Two ``POST path?token=<canary>`` one after the other, with ``Authorization: Bearer <canary>``, ``Cookie:
    s=<canary>`` and the body ``{"password": <canary>}``, on the route that raises the one held exception, its message a
    canary. Barrier: the second request's short line is there, pointing to the first. No canary anywhere in it, and it is
    whole the short line of a ``POST``; no canary in a line outside its ``exc_info``, none in an answer; the message lives
    in the first request's traceback only."""
    print_section(f"H-60r §2 security: the short line of POST {branch.path}, a canary everywhere")
    app = _app()
    canaries = app.state.canaries
    app.state.shared_failure = _SharedFailure(held=H60BuildError(canaries.message))
    secret_options = {"params": {"token": canaries.token}, "headers": {"Authorization": f"Bearer {canaries.authorization}", "Cookie": f"s={canaries.cookie}"}, "json": {"password": canaries.password}}

    with capture_logs(processors=[merge_contextvars]) as events:
        answers = [await _request(app, "POST", branch.path, raise_app_exceptions=False, **secret_options) for _ in range(2)]

    first, second = _shared_failure_answers(answers, branch, method="POST")
    short = _the_line(events, ALREADY_LOGGED, "warning")
    assert (short.get("request_id"), short.get("logged_with_request_id")) == (second, first), f"barrier: the second request's short line, pointing to the first: {short!r}"
    in_the_line = sorted({canary for canary in canaries.every() for text in _texts(short) if canary in text})
    assert not in_the_line, f"H-60r §2: the short line carries {in_the_line}: {short!r}"
    expected = branch.short_line(second, logged_with=first, method="POST")
    assert short == expected, f"H-60r §2: the short line of a POST, whole — no exc_info, no error_chain, nothing else: {short!r} != {expected!r}"
    outside = _canaries_outside_exc_info(events, canaries.every())
    assert not outside, f"H-60: a line carries a secret of the request, or the exception's message, outside exc_info: {outside}"
    answered = "\n".join(f"{answer.text}\n{answer.headers.multi_items()!r}" for answer in answers)
    in_the_answers = [canary for canary in canaries.every() if canary in answered]
    assert not in_the_answers, f"H-60 (D2): an answer carries {in_the_answers}"
    shown = _exc_info_exception(_the_line(events, branch.failed_line, "error"))
    assert shown is not None and canaries.message in _formatted(shown), "H-60: the exception's message lives in the traceback of the first request's line"
    print_success("the short line: no secret of the request, no message; the message in the first request's traceback alone")


# =============================================================================
# THE APP OF backend.app.main
# =============================================================================


# red until H-60: backend/app/api/server_errors.py is missing, then until main.py and MIDDLEWARE_STACK take them
def test_the_app_holds_the_handler_and_runs_the_request_id_middleware_right_inside_activity():
    """§3 (amended 19/10) and §4 on the real app. ``backend.app.main.app`` answers Starlette's ``HTTPException`` with the
    handler ``install_server_error_handler`` registers. ``MIDDLEWARE_STACK`` begins ``activity``, ``request_id``,
    ``security_headers``, in this order, every other entry after them: the request id is its second entry,
    ``MiddlewareEntry("request_id", RequestIdMiddleware)`` without options, named once. ``activity`` stays the outermost
    (workstream Z's D-S1): SWA-037 pins that in ``test_sleep_wake_activity.py``, not here. On the app,
    ``user_middleware`` holds ``RequestIdMiddleware`` right inside ``ActivityMiddleware``, and ``SecurityHeadersMiddleware``
    inside it: the 500 the security headers send for an error nobody handled crosses the request-id layer and carries
    its ``X-Request-Id`` (that answer is pinned on the fresh apps above, built from the same stack)."""
    print_section("H-60: the app's handler for HTTPException; the request id right inside activity")
    install = _install()
    middleware = _middleware_class()
    fresh = FastAPI()
    install(fresh)
    registered = fresh.exception_handlers[StarletteHTTPException]

    held = app_main.app.exception_handlers.get(StarletteHTTPException)

    assert _same_handler(held, registered), f"H-60 §4: the app answers HTTPException with {held!r}, not the install's {registered!r}: main.py must call install_server_error_handler(app)"
    names = [entry.name for entry in MIDDLEWARE_STACK]
    assert names[:3] == ["activity", "request_id", "security_headers"] and names.count("request_id") == 1, f"H-60 §3 (amended): MIDDLEWARE_STACK begins activity, request_id, security_headers, in this order, request_id named once, every other entry after them: {names}"
    second = MIDDLEWARE_STACK[1]
    assert (second.name, second.cls, dict(second.options)) == ("request_id", middleware, {}), f"H-60 §3: the second entry is MiddlewareEntry('request_id', RequestIdMiddleware), without options: {second!r}"
    layers = [entry.cls for entry in app_main.app.user_middleware]
    shown = [getattr(cls, "__name__", repr(cls)) for cls in layers]
    assert layers.count(activity_module.ActivityMiddleware) == 1 and layers.count(middleware) == 1, f"H-60 §3: the app holds ActivityMiddleware and RequestIdMiddleware once each: {shown}"
    inside_activity = layers.index(activity_module.ActivityMiddleware) + 1
    assert layers[inside_activity : inside_activity + 1] == [middleware], f"H-60 §3: on the app, RequestIdMiddleware stands right inside ActivityMiddleware: {shown}"
    assert SecurityHeadersMiddleware in layers[inside_activity + 1 :], f"H-60 §3: SecurityHeadersMiddleware stands inside RequestIdMiddleware, so the 500 it sends for an error nobody handled carries the request's X-Request-Id: {shown}"
    print_success("the install's handler; activity, request_id, security_headers; RequestIdMiddleware right inside ActivityMiddleware, the security headers inside it")


# =============================================================================
# §7 — D4: client_log_level
# =============================================================================


# red until H-60: InstanceConfigResponse declares no client_log_level
def test_client_log_level_is_declared_with_two_states_and_error_by_default():
    """§7: ``InstanceConfigResponse.client_log_level`` is ``"error"`` or ``"debug"``, ``"error"`` when not given; any
    other value — a level itself, ``"info"``, ``"DEBUG"`` — is refused: the level is never published. The JSON schema
    enumerates exactly the two states, ``"error"`` by default."""
    print_section("H-60 D4: client_log_level in the schema")
    assert "client_log_level" in InstanceConfigResponse.model_fields, "H-60 (D4): InstanceConfigResponse declares no client_log_level"
    accounts = AccountsInstanceConfig(registration_mode="open", registration_locked=False)

    assert InstanceConfigResponse(profile="selfhosted", accounts=accounts).client_log_level == "error", "H-60 (D4): client_log_level is 'error' unless given"
    assert [InstanceConfigResponse(profile="selfhosted", accounts=accounts, client_log_level=state).client_log_level for state in ("error", "debug")] == ["error", "debug"]
    for level in ("info", "warning", "DEBUG", "trace"):
        with pytest.raises(ValidationError):
            InstanceConfigResponse(profile="selfhosted", accounts=accounts, client_log_level=level)
    schema = InstanceConfigResponse.model_json_schema()["properties"]["client_log_level"]
    assert (sorted(schema.get("enum", [])), schema.get("default")) == (["debug", "error"], "error"), f"H-60 (D4): two states, 'error' by default: {schema}"
    print_success("'error' | 'debug', 'error' by default; a level refused")


# red until H-60: GET /system/instance answers no client_log_level
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("log_level", "override", "expected"),
    [
        pytest.param("DEBUG", None, "debug", id="DEBUG"),
        pytest.param("debug", None, "debug", id="debug-in-lower-case"),
        pytest.param("TRACE", None, "debug", id="TRACE"),
        pytest.param("INFO", None, "error", id="INFO"),
        pytest.param("WARNING", None, "error", id="WARNING"),
        pytest.param("ERROR", None, "error", id="ERROR"),
        pytest.param("CRITICAL", None, "error", id="CRITICAL"),
        pytest.param("INFO", "debug", "debug", id="LIBREFOLIO_LOG_LEVEL-debug-over-INFO"),
        pytest.param("DEBUG", "warning", "error", id="LIBREFOLIO_LOG_LEVEL-warning-over-DEBUG"),
    ],
)
async def test_client_log_level_follows_the_backend_log_level(instance_app: FastAPI, monkeypatch: pytest.MonkeyPatch, log_level: str, override: str | None, expected: str):
    """§7 (D4 a) on the real app: ``GET /api/v1/system/instance`` answers ``client_log_level`` ``"debug"`` when the
    backend's ``LOG_LEVEL`` is DEBUG or TRACE, in any case, ``"error"`` for INFO, WARNING, ERROR and CRITICAL;
    ``LIBREFOLIO_LOG_LEVEL`` replaces ``LOG_LEVEL`` both ways. Read at each request, as the profile is. Barrier: the
    settings the route reads hold the level the case sets."""
    print_section(f"H-60 D4: LOG_LEVEL={log_level}, {LOG_LEVEL_OVERRIDE}={override}")
    monkeypatch.setenv(LOG_LEVEL_VARIABLE, log_level)
    if override is None:
        monkeypatch.delenv(LOG_LEVEL_OVERRIDE, raising=False)
    else:
        monkeypatch.setenv(LOG_LEVEL_OVERRIDE, override)
    effective = override.upper() if override is not None else log_level
    assert get_settings().LOG_LEVEL == effective, f"barrier: get_settings() reads LOG_LEVEL {get_settings().LOG_LEVEL!r}, not {effective!r}"

    response = await _request(instance_app, "GET", INSTANCE_PATH)

    assert response.status_code == 200, f"GET {INSTANCE_PATH}: {response.status_code} {response.text[:300]}"
    body = response.json()
    assert "client_log_level" in body, f"H-60 (D4): GET /system/instance answers no client_log_level: {sorted(body)}"
    assert body["client_log_level"] == expected, f"H-60 (D4): the backend's LOG_LEVEL {effective!r} must be published as {expected!r}, got {body['client_log_level']!r}"
    print_success(f"LOG_LEVEL {effective} -> client_log_level {expected}")
