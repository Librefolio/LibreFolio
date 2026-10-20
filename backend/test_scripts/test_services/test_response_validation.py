"""A response that breaks its model is answered 500 and logged without its content (H-33, from E's security review R13-SEC4).

FastAPI 0.141.1 registers handlers for ``HTTPException``, ``RequestValidationError`` and the WebSocket one, none for
``fastapi.exceptions.ResponseValidationError``, which it raises when an endpoint returns what its ``response_model``
refuses. Unhandled, the exception reaches Starlette's ``ServerErrorMiddleware``, which answers ``500`` ``Internal Server
Error`` in plain text and raises it again for the server to log: uvicorn writes its traceback, whose message is
``str(exc)`` — and ``ValidationException.__str__`` writes every error whole, ``input`` included: the refused value, and for
a missing field the whole object it is missing from. That is the response's content, user data, in the server's log. The
exception also carries ``.body``, the whole response.

The contract: ``backend/app/api/response_validation.py`` gives ``install_response_validation_handler(app)``, called once in
``backend/app/main.py`` beside A's ``install_validation_error_handler(app)``. It registers, for ``ResponseValidationError``
and nothing else, a handler that answers ``500`` and keeps the exception inside the app, so the server has nothing to
log. Since H-60 (§6) the answer is JSON, ``{"detail": "Internal Server Error", "request_id": <the request's id>,
"error_type": "ResponseValidationError"}``, ``request_id`` absent when the request has none — as on the fresh apps here,
which hold no request-id middleware (``test_server_errors.py`` asks it with one); before H-60 it was what
``ServerErrorMiddleware`` answers, ``Internal Server Error`` in plain text. The handler logs one event,
``A response does not match its model``, at level error, through the project's logger (``get_logger(__name__)``: the
logger named after the module), with ``method``, the request's; ``route``, the route's full template
(``/api/v1/h33/items/{item_id}`` for a route of a router included under ``/api/v1``), never the concrete path;
``endpoint``, FastAPI's ``endpoint_function``, the endpoint's ``__name__``; and ``errors``, each error's ``type`` and
``loc``. Never logged: an error's ``input``, ``msg`` or ``ctx``, the exception's ``body``, a traceback (no ``exc_info``:
its message is ``str(exc)``), nor any value of the response.

1. **The install**, on a fresh ``FastAPI()``: one handler more, for ``ResponseValidationError``; every other as it was.
2. **The app**, ``backend.app.main`` as the server runs it: for ``ResponseValidationError`` it holds the very function the
   install registers. Guard, green before and after: for ``RequestValidationError`` it still holds A's (A-35).
3. **In process**, fresh apps, requests through httpx's ASGI transport. Three routes whose model, ``_H33Item``, is a text
   and a number: ``GET /h33/broken`` and ``GET /h33/valid`` on the app, ``GET /h33/items/{item_id}`` on an ``APIRouter``
   included under ``/api/v1``. The broken ones return a body built around a unique secret — a text where the number is
   due, or the number missing. With the install: the JSON 500 of H-60, ``{"detail": "Internal Server Error",
   "error_type": "ResponseValidationError"}`` (no request id on these apps), the exception kept inside the app, exactly
   the one event above, and the secret nowhere — not in the answer, in no captured structlog event, in no Python logging
   record (``caplog`` at DEBUG on the root, proved live by a barrier record). Through the included router the event
   names the full template. A valid response is answered as without the install, and logs nothing.
4. **Control and premise**, green before and after. Without the install, the same broken route gets Starlette's plain 500 and
   the exception leaves the app carrying the response: ``str(exc)`` and the traceback a server writes hold the secret,
   ``exc.body`` is the whole body. Premise of the included-router case: FastAPI 0.141.1 puts in ``scope["route"]`` the
   included router's own ``APIRoute``, whose ``path`` lacks the include prefix; the full template is in the exception's
   ``endpoint_path``.

Red until H-33: 1, 2 but its guard, and 3, each on the barrier "H-33: backend/app/api/response_validation.py is missing":
the module is imported inside the tests, so the file is collected all the same and each test fails on its own; 2 then
on the missing handler until ``main.py`` calls the install. Red until H-60: the three tests of 3, on the answer —
``Internal Server Error`` in plain text until then, the JSON of §6 after (``_assert_json_500``); every log assertion is
the same before and after.

The routes' endpoints are module-level functions that read their body from ``app.state``: FastAPI caches the endpoint
context it puts in the exception, ``endpoint_function`` included, by the ``id()`` of the endpoint and never drops it, so a
function created per test and then freed could lend its id, and its name, to the next one. No request carries the secret.

Isolation: pure, parallel-safe. No server, no database, no network, nothing shared is written: the apps live in the
test's process, the real app is only read. Importing ``backend.app.main`` configures the logging, as for every module
that imports it; structlog's capture drops what it captures, and the only record the cases send to Python logging is the
barrier's, at DEBUG.
"""

import importlib
import logging
import uuid
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import Any

import httpx
import pytest
import structlog
from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from pydantic import BaseModel
from structlog.testing import capture_logs

import backend.app.main as app_main
from backend.app.api.validation_errors import install_validation_error_handler
from backend.test_scripts.test_utils import print_section, print_success

#: The module H-33 adds; its handler logs on the logger named after it (get_logger(__name__)).
MODULE = "backend.app.api.response_validation"
#: The one event the handler logs for each response its model refuses.
EVENT = "A response does not match its model"
#: H-60 (§6): what the handler answers on these fresh apps, which hold no request-id middleware: no request_id key.
JSON_500 = {"detail": "Internal Server Error", "error_type": "ResponseValidationError"}
#: Keys under which a response's content travels: pydantic's input, msg and ctx, the exception's body, a traceback.
CONTENT_KEYS = frozenset({"input", "msg", "ctx", "body", "exc_info", "exception"})

#: The routes of the fresh apps: two on the app itself, one on a router included under PREFIX, as the real app includes
#: its API router under /api/v1.
BROKEN_PATH = "/h33/broken"
VALID_PATH = "/h33/valid"
PREFIX = "/api/v1"
#: The template the APIRouter declares, and the route's full template once the router is included.
ITEM_TEMPLATE = "/h33/items/{item_id}"
ITEM_ROUTE = PREFIX + ITEM_TEMPLATE
#: A concrete path of that route: the log names the template, never this.
ITEM_PATH = f"{PREFIX}/h33/items/7"


class _H33Item(BaseModel):
    """The response model of every route: a text and a number."""

    name: str
    count: int


#: What ``GET /h33/valid`` returns: a body ``_H33Item`` accepts.
VALID_BODY = {"name": "a valid name", "count": 3}


def _secret() -> str:
    """A value no log may hold: unique across workers and runs."""
    return f"h33-secret-{uuid.uuid4().hex}"


@dataclass(frozen=True)
class _Breakage:
    """A body ``_H33Item`` refuses, each of its values built around one secret, and what FastAPI makes of it."""

    #: The body the broken routes return, given the secret.
    body: Callable[[str], dict[str, str]]
    #: What the handler logs of the errors: each one's ``type`` and ``loc``, nothing else.
    logged: list[dict[str, Any]]
    #: The ``input`` FastAPI keeps in the error, given the body: what ``str(exc)`` writes out.
    input_of: Callable[[dict[str, str]], object]


TEXT_FOR_A_NUMBER = "a-text-where-a-number-is-due"
_BREAKAGES: dict[str, _Breakage] = {
    # The error's input is the refused value; the valid name travels in exc.body only.
    TEXT_FOR_A_NUMBER: _Breakage(
        body=lambda secret: {"name": f"{secret}-name", "count": f"{secret}-count"},
        logged=[{"type": "int_parsing", "loc": ["response", "count"]}],
        input_of=lambda body: body["count"],
    ),
    # The error's input is the whole object the number is missing from: its valid name too.
    "a-missing-number": _Breakage(
        body=lambda secret: {"name": f"{secret}-name"},
        logged=[{"type": "missing", "loc": ["response", "count"]}],
        input_of=lambda body: body,
    ),
}


# =============================================================================
# THE FRESH APPS
# =============================================================================
#
# Module-level endpoints: FastAPI caches the context it puts in a ResponseValidationError (endpoint_function included)
# by the id() of the endpoint and never drops it, so a function created per test and then freed could lend its id, and
# with it its name, to the next one. These live as long as the process. They read the body from their app's state: no
# request carries the secret, so no request line can log it.


async def h33_broken(request: Request) -> Any:
    """``GET /h33/broken``: its app's body, which ``_H33Item`` refuses."""
    return dict(request.app.state.h33_body)


async def h33_item(item_id: int, request: Request) -> Any:
    """``GET /h33/items/{item_id}`` on the included router: the same body. Records the ``path`` of the route FastAPI put
    in ``scope["route"]``, the scope the handler's request reads too."""
    request.app.state.h33_scope_route = getattr(request.scope.get("route"), "path", None)
    return dict(request.app.state.h33_body)


async def h33_valid() -> Any:
    """``GET /h33/valid``: a body ``_H33Item`` accepts."""
    return dict(VALID_BODY)


def _app(*, install: Callable[[FastAPI], None] | None, body: dict[str, str]) -> FastAPI:
    """A fresh app, ``install`` applied first if given: ``GET /h33/broken`` and ``GET /h33/valid`` on the app,
    ``GET /h33/items/{item_id}`` on an ``APIRouter`` included under ``/api/v1``; the broken two return ``body``."""
    app = FastAPI()
    if install is not None:
        install(app)
    app.state.h33_body = body
    app.add_api_route(BROKEN_PATH, h33_broken, methods=["GET"], response_model=_H33Item)
    app.add_api_route(VALID_PATH, h33_valid, methods=["GET"], response_model=_H33Item)
    router = APIRouter()
    router.add_api_route(ITEM_TEMPLATE, h33_item, methods=["GET"], response_model=_H33Item)
    app.include_router(router, prefix=PREFIX)
    return app


# =============================================================================
# HELPERS
# =============================================================================


def _response_validation() -> ModuleType:
    """``backend.app.api.response_validation``, imported when a test needs it: before H-33 it does not exist, and the
    rest of this file must still be collected."""
    try:
        return importlib.import_module(MODULE)
    except ModuleNotFoundError as error:
        if error.name != MODULE:
            raise
    pytest.fail("H-33: backend/app/api/response_validation.py is missing")


def _the_install() -> Callable[[FastAPI], None]:
    """``install_response_validation_handler``, read from the module when a test needs it."""
    install = getattr(_response_validation(), "install_response_validation_handler", None)
    if not callable(install):
        pytest.fail("H-33: backend/app/api/response_validation.py gives no install_response_validation_handler(app)")
    return install


def _registered_by(install: Callable[[FastAPI], None], exc_class: type[Exception]) -> Callable[..., Any]:
    """The very callable ``install`` registers for ``exc_class``, read on a fresh app: what the real app must hold."""
    fresh = FastAPI()
    before = fresh.exception_handlers.get(exc_class)
    install(fresh)
    registered = fresh.exception_handlers.get(exc_class)
    assert registered is not None and registered is not before, f"{getattr(install, '__name__', install)}(app) registers no handler of its own for {exc_class.__name__}"
    return registered


async def _get(app: FastAPI, path: str, *, raise_app_exceptions: bool = True) -> httpx.Response:
    """``GET path`` on ``app`` in process, through httpx's ASGI transport: no server, no database. An exception the app
    lets out — what a server would log, traceback and ``str(exc)`` — is raised here; with ``raise_app_exceptions`` off,
    the answer is what the app sent before letting it out."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=raise_app_exceptions)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.get(path)


async def _get_handled(app: FastAPI, path: str) -> httpx.Response:
    """``GET path``, the test failing if the ``ResponseValidationError`` leaves the app: a server logs the traceback of
    whatever the app lets out — also after a handler of ``500`` or ``Exception``, which ``ServerErrorMiddleware`` runs
    and then raises again."""
    try:
        return await _get(app, path)
    except ResponseValidationError:
        pytest.fail("H-33: the ResponseValidationError left the app, as with no handler: a server would log its traceback, whose message, str(exc), holds the refused response")


def _answer(response: httpx.Response) -> tuple[int, str | None, bytes]:
    """What a client receives: status, content type, bytes."""
    return response.status_code, response.headers.get("content-type"), response.content


def _assert_plain_500(answered: httpx.Response) -> None:
    """Starlette's answer to an error nobody handles: ``500``, ``Internal Server Error``, plain text."""
    content_type = answered.headers.get("content-type", "")
    assert (answered.status_code, answered.text) == (500, "Internal Server Error"), f"{answered.status_code} {answered.text}"
    assert content_type.split(";")[0].strip() == "text/plain", content_type


def _assert_json_500(answered: httpx.Response) -> None:
    """H-60 (§6), the handler's answer on an app without a request id: ``500``, JSON, exactly ``JSON_500``."""
    content_type = answered.headers.get("content-type", "")
    assert (answered.status_code, content_type.split(";")[0].strip()) == (500, "application/json"), f"H-60: the 500 of a response that breaks its model is JSON: {answered.status_code} {content_type!r} {answered.text[:300]}"
    assert answered.json() == JSON_500, f"H-60: the body is exactly {JSON_500} (no request id on this app): {answered.text}"


def _the_event(events: list[dict[str, Any]]) -> dict[str, Any]:
    """The one ``EVENT`` among the captured ``events``: exactly one, at level error, on the module's own logger."""
    found = [event for event in events if event.get("event") == EVENT]
    assert len(found) == 1, f"H-33: exactly one {EVENT!r} expected; the capture holds {[(event.get('logger'), event.get('event')) for event in events]} (none at all: nothing was logged, or the module's logger does not reach structlog's capture)"
    (event,) = found
    assert (event.get("logger"), event.get("log_level")) == (MODULE, "error"), f"H-33: {EVENT!r} must be logged at level error on the module's own logger, get_logger(__name__): got {event.get('logger')!r} at {event.get('log_level')!r}"
    return event


def _logged_errors(event: dict[str, Any]) -> list[dict[str, Any]]:
    """The event's ``errors``, each checked to be its ``type`` and ``loc`` and nothing else; ``loc`` as a list."""
    errors = event.get("errors")
    assert isinstance(errors, list) and errors, f"H-33: 'errors' must list the refused response's errors: {errors!r}"
    for error in errors:
        assert isinstance(error, Mapping) and set(error) == {"type", "loc"}, f"H-33: each logged error is its type and loc, nothing else: {error!r}"
    return [{"type": error["type"], "loc": list(error["loc"])} for error in errors]


def _keys_anywhere(value: object) -> set[str]:
    """Every key of every mapping in ``value``, at any depth."""
    if isinstance(value, Mapping):
        return {str(key) for key in value} | {key for item in value.values() for key in _keys_anywhere(item)}
    if isinstance(value, (list, tuple, set, frozenset)):
        return {key for item in value for key in _keys_anywhere(item)}
    return set()


def _every_text(value: object) -> Iterator[str]:
    """``repr`` and ``str`` of ``value`` and of everything inside it — mapping keys and values, sequence and set items —
    where a secret could hide: the ``repr`` of an exception shows nothing, its ``str`` every input."""
    yield repr(value)
    yield str(value)
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _every_text(key)
            yield from _every_text(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _every_text(item)


def _assert_no_event_carries(secret: str, events: list[dict[str, Any]]) -> None:
    """No captured structlog event holds ``secret``: not the ``repr`` of the whole capture, nor the ``repr`` or ``str`` of
    anything inside an event."""
    assert secret not in repr(events), "H-33: the captured events carry the response's content"
    carrying = sorted({str(event.get("event")) for event in events if any(secret in text for text in _every_text(event))})
    assert not carrying, f"H-33: captured events carry the response's content: {carrying}"


def _caplog_is_capturing(caplog: pytest.LogCaptureFixture) -> None:
    """From here on, ``caplog`` at DEBUG on the root; presence barrier for the checks on Python logging: a DEBUG record of
    this file's logger is captured, so an empty capture would mean nothing was logged."""
    caplog.clear()
    caplog.set_level(logging.DEBUG)
    probe = f"h33 barrier {uuid.uuid4().hex}"
    logging.getLogger(__name__).debug(probe)
    assert any(record.getMessage() == probe for record in caplog.records), "barrier: caplog at DEBUG captured no DEBUG record of this file's logger: its silence would prove nothing"


def _record_text(record: logging.LogRecord) -> str:
    """All a record can write: its message, its attributes (``exc_text``, ``stack_info``, extras), its exception formatted."""
    texts = [record.getMessage(), repr(vars(record))]
    if record.exc_info and record.exc_info[1] is not None:
        texts.append(logging.Formatter().formatException(record.exc_info))
    return "\n".join(texts)


def _assert_no_record_carries(secret: str, caplog: pytest.LogCaptureFixture) -> None:
    """No Python logging record the test captured holds ``secret``, nor ``caplog``'s formatted text."""
    carrying = [f"{record.name} {record.levelname}" for record in caplog.records if secret in _record_text(record)]
    assert not carrying, f"H-33: Python logging records carry the response's content: {carrying}"
    assert secret not in caplog.text, "H-33: the text Python logging wrote carries the response's content"


# =============================================================================
# 1. THE INSTALL
# =============================================================================


# red until H-33: backend.app.api.response_validation does not exist yet
def test_the_install_adds_one_handler_for_response_validation_errors_and_changes_no_other():
    """``install_response_validation_handler(app)`` on a fresh ``FastAPI()``: one handler more, for
    ``ResponseValidationError`` — not for ``500`` nor ``Exception``, whose handler Starlette's ``ServerErrorMiddleware``
    runs and then raises the exception again for the server to log — and every other handler as it was: FastAPI's own
    for ``HTTPException``, ``RequestValidationError`` (A's install replaces it in the real app) and WebSockets."""
    print_section("H-33: the install")
    install = _the_install()
    app = FastAPI()
    before = dict(app.exception_handlers)
    assert ResponseValidationError not in before, "Precondition: FastAPI now registers a handler of its own for ResponseValidationError: re-read H-33"

    install(app)

    after = dict(app.exception_handlers)
    added = sorted(repr(key) for key in set(after) - set(before))
    assert set(after) - set(before) == {ResponseValidationError}, f"H-33: the install must add a handler for ResponseValidationError and for nothing else: added {added}"
    assert callable(after[ResponseValidationError]), f"H-33: the handler must be callable: {after[ResponseValidationError]!r}"
    changed = sorted(repr(key) for key in before if after.get(key) is not before[key])
    assert not changed, f"H-33: the install must leave every other handler as it was: changed {changed}"
    print_success("one handler more, for ResponseValidationError; every other untouched")


# =============================================================================
# 2. THE APP
# =============================================================================


# red until H-33: backend.app.api.response_validation does not exist yet, then until backend/app/main.py calls its install
def test_the_app_holds_the_handler_of_the_install():
    """The real app (``backend.app.main``) holds, for ``ResponseValidationError``, the very function
    ``install_response_validation_handler`` registers: ``main.py`` calls the install."""
    print_section("H-33: the app's handler for ResponseValidationError")
    registered = _registered_by(_the_install(), ResponseValidationError)

    held = app_main.app.exception_handlers.get(ResponseValidationError)

    assert held is not None, "H-33: the app holds no handler for ResponseValidationError: backend/app/main.py must call install_response_validation_handler(app)"
    assert held is registered, f"H-33: the app's handler for ResponseValidationError is {held!r}, not the install's {registered!r}"
    print_success("the app holds the install's handler")


# guard: green before and after H-33
def test_the_app_still_holds_the_422_handler_without_input():
    """No clobbering: for ``RequestValidationError`` the real app still holds the very function
    ``install_validation_error_handler`` registers (A-35, ``api/validation_errors.py``): the 422 without the request's
    input."""
    print_section("H-33 guard: the app's handler for RequestValidationError")
    registered = _registered_by(install_validation_error_handler, RequestValidationError)

    held = app_main.app.exception_handlers.get(RequestValidationError)

    assert held is registered, f"the app's handler for RequestValidationError is {held!r}, not A-35's {registered!r}: the 422 sends the request's input back again"
    print_success("the app still answers its 422 without the input")


# =============================================================================
# 3. IN PROCESS: FRESH APPS WITH THE INSTALL
# =============================================================================


# red until H-33: backend.app.api.response_validation does not exist yet; red again until H-60: the JSON 500 of §6
@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(_BREAKAGES))
async def test_a_response_that_breaks_its_model_is_logged_without_its_content(case: str, caplog: pytest.LogCaptureFixture):
    """With the install, a response ``_H33Item`` refuses — ``case``'s body, every value built around a secret — is
    answered ``500`` with the JSON of H-60 (§6), ``{"detail": "Internal Server Error", "error_type":
    "ResponseValidationError"}`` — no ``request_id``: this app holds no request-id middleware —, the secret not in it, and
    the exception stays inside the app.

    structlog's capture holds exactly one ``A response does not match its model``, at level error, on the module's own
    logger, with ``method`` ``GET``, ``route`` ``/h33/broken``, ``endpoint`` the endpoint's name (FastAPI's
    ``endpoint_function``) and ``errors`` the refused field's ``type`` and ``loc`` only; no ``input``, ``msg``, ``ctx``,
    ``body``, ``exc_info`` nor ``exception`` anywhere in it. The secret is in no captured event — the ``repr`` of the
    capture, the ``repr`` and ``str`` of anything inside it — and in no Python logging record, captured at DEBUG on the
    root once a barrier record proves the capture live: not in its message, its attributes (``exc_text`` included), its
    formatted exception, nor in ``caplog.text``."""
    print_section(f"H-33 in process: {case}")
    install = _the_install()
    breakage = _BREAKAGES[case]
    secret = _secret()
    body = breakage.body(secret)
    app = _app(install=install, body=body)
    _caplog_is_capturing(caplog)

    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as events:
        answered = await _get_handled(app, BROKEN_PATH)

    _assert_json_500(answered)
    assert secret not in answered.text, "H-60: the answer carries the response's content"
    event = _the_event(events)
    assert (event.get("method"), event.get("route"), event.get("endpoint")) == ("GET", BROKEN_PATH, h33_broken.__name__), f"H-33: method, route template and endpoint name: {event.get('method')!r}, {event.get('route')!r}, {event.get('endpoint')!r}"
    assert _logged_errors(event) == breakage.logged, f"H-33: the refused field's type and loc: {_logged_errors(event)} != {breakage.logged}"
    content_keys = sorted(CONTENT_KEYS & _keys_anywhere(event))
    assert not content_keys, f"H-33: the event must hold none of {sorted(CONTENT_KEYS)}: found {content_keys}"
    _assert_no_event_carries(secret, events)
    _assert_no_record_carries(secret, caplog)
    print_success("the JSON 500 without the content; one event with method, route, endpoint and each error's type and loc; the secret nowhere")


# red until H-33: backend.app.api.response_validation does not exist yet; red again until H-60: the JSON 500 of §6
@pytest.mark.asyncio
async def test_a_route_of_an_included_router_is_logged_by_its_full_template():
    """A route of an ``APIRouter`` included under ``/api/v1`` — as the real app includes every API route — is logged by
    its full template, ``/api/v1/h33/items/{item_id}``: never the concrete path, nor the router's own
    ``/h33/items/{item_id}``. The handler cannot take it from ``scope["route"]`` alone: for an included router FastAPI
    0.141.1 puts there the router's own ``APIRoute``, whose ``path`` lacks the include prefix (premise below); a red
    names what ``scope["route"]`` held."""
    print_section("H-33 in process: a route of an included router")
    install = _the_install()
    breakage = _BREAKAGES[TEXT_FOR_A_NUMBER]
    secret = _secret()
    app = _app(install=install, body=breakage.body(secret))

    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as events:
        answered = await _get_handled(app, ITEM_PATH)

    _assert_json_500(answered)
    event = _the_event(events)
    logged, seen = event.get("route"), getattr(app.state, "h33_scope_route", None)
    why = f" — the path of the route FastAPI put in scope['route'] ({seen!r}), the included router's own, without the prefix {PREFIX!r} given to include_router" if logged == seen and seen != ITEM_ROUTE else ""
    assert logged == ITEM_ROUTE, f"H-33: the log must name the route by its full template {ITEM_ROUTE!r}, got {logged!r}{why}"
    assert (event.get("method"), event.get("endpoint")) == ("GET", h33_item.__name__), f"H-33: method and endpoint name: {event.get('method')!r}, {event.get('endpoint')!r}"
    assert _logged_errors(event) == breakage.logged, f"H-33: the refused field's type and loc: {_logged_errors(event)} != {breakage.logged}"
    _assert_no_event_carries(secret, events)
    print_success(f"the event names {ITEM_ROUTE}")


# red until H-33: backend.app.api.response_validation does not exist yet; red again until H-60: the JSON 500 of §6
@pytest.mark.asyncio
async def test_a_response_that_matches_its_model_is_untouched():
    """With the install, a response its model accepts is answered as without it — ``200``, the same type and bytes, the
    same JSON — and logs nothing. Barrier for that silence: in the same capture the broken route logs its one event, so
    the capture sees the handler's events, and that one is the only one."""
    print_section("H-33 in process: a valid response")
    install = _the_install()
    body = _BREAKAGES[TEXT_FOR_A_NUMBER].body(_secret())
    default = await _get(_app(install=None, body=body), VALID_PATH)
    app = _app(install=install, body=body)

    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as events:
        answered = await _get_handled(app, VALID_PATH)
        broken = await _get_handled(app, BROKEN_PATH)

    assert (answered.status_code, answered.json()) == (200, VALID_BODY), f"{answered.status_code} {answered.text}"
    assert _answer(answered) == _answer(default), f"a valid response must be answered as without the install: {_answer(answered)} != {_answer(default)}"
    _assert_json_500(broken)
    event = _the_event(events)
    assert event.get("route") == BROKEN_PATH, f"H-33: the one event must be the broken route's, none for the valid one: {event.get('route')!r}"
    print_success("200 and the same JSON as without the install; nothing logged for it")


# =============================================================================
# 4. CONTROL AND PREMISE: FASTAPI WITHOUT THE INSTALL
# =============================================================================


# control: green before and after H-33 — the defect the handler closes
@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(_BREAKAGES))
async def test_without_the_install_the_exception_carries_the_response_out(case: str):
    """The defect H-33 closes. FastAPI registers no handler for ``ResponseValidationError``: on an app without the
    install the same broken route gets Starlette's plain ``500`` from its ``ServerErrorMiddleware``, which then lets
    the exception out for the server to log. What it lets out carries the response: every error keeps its ``input`` — the
    refused value, and for a missing field the whole object, its valid values too — so ``str(exc)`` and the traceback a
    server writes (formatted as ``logging`` formats uvicorn's ``exc_info``) hold the secret, and ``exc.body`` is the
    whole body."""
    print_section(f"H-33 control, no handler: {case}")
    breakage = _BREAKAGES[case]
    secret = _secret()
    body = breakage.body(secret)
    assert ResponseValidationError not in FastAPI().exception_handlers, "Precondition: FastAPI now registers a handler of its own for ResponseValidationError: re-read H-33"

    answered = await _get(_app(install=None, body=body), BROKEN_PATH, raise_app_exceptions=False)
    with pytest.raises(ResponseValidationError) as raised:
        await _get(_app(install=None, body=body), BROKEN_PATH)

    _assert_plain_500(answered)
    exc = raised.value
    assert [error.get("input") for error in exc.errors()] == [breakage.input_of(body)], f"every error keeps its input: {exc.errors()}"
    traceback_text = logging.Formatter().formatException((type(exc), exc, exc.__traceback__))
    assert secret in str(exc), f"str(exc) must carry the response, as FastAPI writes it: {exc}"
    assert secret in traceback_text, "the traceback a server writes must carry the response, as its last line is str(exc)"
    assert exc.body == body, f"exc.body must be the whole response: {exc.body!r}"
    print_success("Starlette's plain 500; the exception leaves the app with the response in its message")


# premise: green before and after H-33 (FastAPI 0.141.1)
@pytest.mark.asyncio
async def test_premise_only_the_exception_names_an_included_route_in_full():
    """Premise of the included-router case (FastAPI 0.141.1): for a route of an ``APIRouter`` included under
    ``/api/v1``, ``scope["route"]`` is the router's own ``APIRoute``, whose ``path`` is ``/h33/items/{item_id}``, without
    the prefix; the full template is in the exception: ``endpoint_path`` ``GET /api/v1/h33/items/{item_id}`` (method,
    root path, template), beside ``endpoint_function``, the endpoint's ``__name__``. A red here means FastAPI changed
    where it keeps the template: re-read where the handler takes ``route`` from."""
    print_section("H-33 premise: where FastAPI keeps the template of an included route")
    app = _app(install=None, body=_BREAKAGES[TEXT_FOR_A_NUMBER].body(_secret()))

    with pytest.raises(ResponseValidationError) as raised:
        await _get(app, ITEM_PATH)

    seen = getattr(app.state, "h33_scope_route", None)
    assert seen == ITEM_TEMPLATE, f"scope['route'].path is {seen!r}, no longer the included router's own {ITEM_TEMPLATE!r}: FastAPI changed what it puts in scope['route'], from which the handler may now read the full template"
    exc = raised.value
    assert (exc.endpoint_function, exc.endpoint_path) == (h33_item.__name__, f"GET {ITEM_ROUTE}"), f"endpoint_function {exc.endpoint_function!r}, endpoint_path {exc.endpoint_path!r}"
    print_success(f"scope['route'].path {seen}; the exception's endpoint_path GET {ITEM_ROUTE}")
