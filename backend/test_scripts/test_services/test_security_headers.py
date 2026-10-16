"""
The security headers every response carries (workstream H, platform, checkpoint CP7b-1, F15; decision D5, its «always» part).

Under test: ``SecurityHeadersMiddleware``, a pure ASGI middleware of the new module
``backend/app/services/platform/security_headers.py``, and its entry ``security_headers`` in ``MIDDLEWARE_STACK``
(``middleware.py``). The contract:

(a) ``MIDDLEWARE_STACK`` holds one entry named ``security_headers``, of class ``SecurityHeadersMiddleware``, outside
    ``gzip``: checked with ``assert_in_relative_order`` of ``test_app_lifecycle``, so that an entry of another workstream
    (Z's ``activity``) may stand before, between or after. The app of ``backend.app.main`` carries it outside GZip.
(b) Every HTTP response carries ``X-Content-Type-Options: nosniff`` and ``Referrer-Policy: strict-origin-when-cross-origin``,
    each exactly once: a JSON response, an HTML one, a streamed one (several body messages, no ``Content-Length``), the
    router's 404, a CORS preflight that the CORS middleware answers itself, a body over 1024 bytes that GZip compresses
    (``Content-Encoding: gzip``, the body the gzip of what the route returned), and a response start without ``headers``,
    which ASGI allows ("Optional; if missing defaults to an empty list").
(c) A header a route set is never overwritten nor repeated: a route's ``Referrer-Policy: no-referrer`` stays the only
    ``Referrer-Policy``, a route's ``X-Content-Type-Options: nosniff`` stays the only one, and the other header is added.
(d) A scope that is not HTTP (``lifespan``, ``websocket``) reaches the app untouched: the same scope, unchanged, the same
    ``receive`` and ``send``, every message the app sends unchanged (a WebSocket accept gets no header).
(e) The app of ``backend.app.main``: a route of the API that needs no login (``GET /api/v1/system/health``) and the SPA
    catch-all carry both headers, and so does the 500 Starlette sends for an exception, which still reaches the server.

The module is imported inside each test, so this file collects before the module exists and each test fails on its own.
(b), (c) and (d) run the middleware on a fresh app holding the entries ``security_headers``, ``gzip`` and ``cors`` of
``MIDDLEWARE_STACK``, in the stack's order and with its options (the entries of other workstreams are theirs to test), or
around a bare ASGI app. The 500 is checked on the app of ``backend.app.main`` alone: Starlette's ``ServerErrorMiddleware``
stands outside every middleware of the stack and sends its 500 through the server's own ``send``, so where the headers get
onto that response (the middleware, an exception handler of the app) is the implementation's choice; what is pinned is
what the client receives. Its exception is raised in the catch-all, ``static_site.frontend_available`` being replaced
with ``monkeypatch``; the health route's database session is overridden the same way (``get_session_generator``, so no
engine is made), and ``LIBREFOLIO_BLOCKED`` is unset. Requests are raw ASGI calls, so that every header line is seen as
it was sent, duplicates included, together with what the app raises to the server; the lifespan never runs, and every
call is bounded by a deadline. No DB, no server, no network.
"""

from __future__ import annotations

import asyncio
import copy
import gzip
import importlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse

import backend.app.main as app_main
from backend.app.config import API_V1_PREFIX
from backend.app.db.session import get_session_generator
from backend.app.services.platform import static_site
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, MiddlewareEntry, install_middleware
from backend.test_scripts.test_services.test_app_lifecycle import assert_in_relative_order
from backend.test_scripts.test_utils import print_section, print_success

SECURITY_MODULE = "backend.app.services.platform.security_headers"
CLASS_NAME = "SecurityHeadersMiddleware"
ENTRY_NAME = "security_headers"

NOSNIFF = "nosniff"
REFERRER_POLICY = "strict-origin-when-cross-origin"

#: Every raw call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0

PAGE_HTML = b"<!doctype html><title>page</title>"
STREAM_CHUNKS = (b"first chunk\n", b"second chunk\n", b"third chunk\n")
#: Over GZip's minimum_size (1024 in MIDDLEWARE_STACK), of a type it compresses.
LARGE_TEXT = b"LibreFolio sends its security headers with every response. " * 80
INDEX_HTML = b"<!doctype html><title>index</title>"
FALLBACK_HTML = b"<!doctype html><title>spa fallback</title>"
PROVOKED = "provoked: the catch-all fails"


# =============================================================================
# THE MODULE UNDER TEST, IMPORTED WHEN A TEST RUNS
# =============================================================================


def middleware_class() -> type:
    """``SecurityHeadersMiddleware``: before its module exists, the test that asks for it fails, and only that test."""
    module = importlib.import_module(SECURITY_MODULE)
    cls = getattr(module, CLASS_NAME, None)
    assert isinstance(cls, type), f"{SECURITY_MODULE} has no class {CLASS_NAME}"
    return cls


def security_entry() -> MiddlewareEntry:
    """The one entry ``security_headers`` of ``MIDDLEWARE_STACK``, of class ``SecurityHeadersMiddleware``."""
    cls = middleware_class()
    entries = [entry for entry in MIDDLEWARE_STACK if entry.name == ENTRY_NAME]
    assert len(entries) == 1, f"{len(entries)} entries named {ENTRY_NAME!r} in MIDDLEWARE_STACK: {[entry.name for entry in MIDDLEWARE_STACK]}"
    assert entries[0].cls is cls, f"the entry {ENTRY_NAME!r} holds {entries[0].cls!r}, not {SECURITY_MODULE}.{CLASS_NAME}"
    return entries[0]


def wrap(app: Callable) -> Callable:
    """``app`` inside the middleware, built as the stack builds it: with the entry's options."""
    entry = security_entry()
    return entry.cls(app, **entry.options)


# =============================================================================
# RAW ASGI CALLS
# =============================================================================


@dataclass(frozen=True)
class Reply:
    """What the client of one raw ASGI call received, and what the app raised to the server after it."""

    starts: int  # http.response.start messages sent
    status: int | None
    headers: list[tuple[str, str]]  # every header line as sent, names lower-cased, duplicates kept
    body: bytes
    body_messages: int  # the http.response.body messages that carried the body
    raised: BaseException | None

    def values(self, name: str) -> list[str]:
        """Every value sent for the header ``name``, in order."""
        return [value for key, value in self.headers if key == name]


async def call(app: Callable, path: str, *, method: str = "GET", headers: Sequence[tuple[str, str]] = ()) -> Reply:
    """``method path`` on ``app``, as a server hands it over; what the app raises is kept in ``raised``, never re-raised."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": quote(path).encode("ascii"),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"testserver"), *((name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in headers)],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    complete = asyncio.Event()
    request_sent = False
    starts = 0
    status: int | None = None
    sent_headers: list[tuple[str, str]] = []
    body = bytearray()
    body_messages = 0

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await complete.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        nonlocal starts, status, body_messages
        if message["type"] == "http.response.start":
            starts += 1
            status = message["status"]
            sent_headers.extend((bytes(name).decode("latin-1").lower(), bytes(value).decode("latin-1")) for name, value in message.get("headers", ()))
        elif message["type"] == "http.response.body":
            body_messages += 1
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                complete.set()

    raised: BaseException | None = None
    try:
        await asyncio.wait_for(app(scope, receive, send), CALL_SECONDS)
    except TimeoutError:
        pytest.fail(f"{method} {path}: no answer within {CALL_SECONDS}s")
    except Exception as exc:  # Starlette re-raises after its 500, so that the server logs the error
        raised = exc
    return Reply(starts=starts, status=status, headers=sent_headers, body=bytes(body), body_messages=body_messages, raised=raised)


def assert_both_headers(reply: Reply, what: str, *, referrer_policy: str = REFERRER_POLICY) -> None:
    """One response, with ``X-Content-Type-Options: nosniff`` and ``Referrer-Policy`` once each."""
    assert reply.starts == 1, f"{what}: {reply.starts} response starts were sent"
    assert reply.values("x-content-type-options") == [NOSNIFF], f"{what}: X-Content-Type-Options is {reply.values('x-content-type-options')}, wanted exactly one, {NOSNIFF!r}; headers {reply.headers}"
    assert reply.values("referrer-policy") == [referrer_policy], f"{what}: Referrer-Policy is {reply.values('referrer-policy')}, wanted exactly one, {referrer_policy!r}; headers {reply.headers}"


# =============================================================================
# A FRESH APP WITH THE STACK'S OWN ENTRIES
# =============================================================================


async def json_route() -> JSONResponse:
    return JSONResponse({"ok": True})


async def html_route() -> HTMLResponse:
    return HTMLResponse(PAGE_HTML)


async def stream_route() -> StreamingResponse:
    async def chunks():
        for chunk in STREAM_CHUNKS:
            yield chunk

    return StreamingResponse(chunks(), media_type="text/plain")


async def large_route() -> PlainTextResponse:
    return PlainTextResponse(LARGE_TEXT)


async def referrer_policy_route() -> PlainTextResponse:
    return PlainTextResponse("kept", headers={"Referrer-Policy": "no-referrer"})


async def nosniff_route() -> PlainTextResponse:
    return PlainTextResponse("once", headers={"X-Content-Type-Options": NOSNIFF})


ROUTES: dict[str, Callable] = {
    "/json": json_route,
    "/html": html_route,
    "/stream": stream_route,
    "/large": large_route,
    "/sets-referrer-policy": referrer_policy_route,
    "/sets-nosniff": nosniff_route,
}

#: The entries of MIDDLEWARE_STACK the fresh app holds: this one, and the two whose responses it must see.
STACK_ENTRIES = (ENTRY_NAME, "gzip", "cors")


def stack_app() -> FastAPI:
    """A fresh app holding ``security_headers``, ``gzip`` and ``cors`` of ``MIDDLEWARE_STACK``, in its order, and ``ROUTES``."""
    security_entry()
    stack = tuple(entry for entry in MIDDLEWARE_STACK if entry.name in STACK_ENTRIES)
    assert sorted(entry.name for entry in stack) == sorted(STACK_ENTRIES), f"MIDDLEWARE_STACK must hold {STACK_ENTRIES} once each: {[entry.name for entry in MIDDLEWARE_STACK]}"
    app = FastAPI()
    install_middleware(app, stack)
    for path, endpoint in ROUTES.items():
        app.add_api_route(path, endpoint, methods=["GET"])
    return app


# Barriers: each proves the response is the kind its case names, before the headers are read.


def _is_the_json(reply: Reply) -> None:
    assert reply.status == 200 and reply.values("content-type") == ["application/json"], f"barrier: not the route's JSON: {reply.status} {reply.headers}"
    assert json.loads(reply.body) == {"ok": True}


def _is_the_html(reply: Reply) -> None:
    assert reply.status == 200 and reply.values("content-type") == ["text/html; charset=utf-8"], f"barrier: not the route's HTML: {reply.status} {reply.headers}"
    assert reply.body == PAGE_HTML


def _is_streamed(reply: Reply) -> None:
    assert reply.status == 200 and reply.body == b"".join(STREAM_CHUNKS), f"barrier: not the route's stream: {reply.status} {reply.body!r}"
    assert reply.body_messages > 1 and not reply.values("content-length"), f"barrier: sent whole ({reply.body_messages} body messages, Content-Length {reply.values('content-length')}), not streamed"


def _is_the_router_404(reply: Reply) -> None:
    assert reply.status == 404 and json.loads(reply.body) == {"detail": "Not Found"}, f"barrier: not the router's 404: {reply.status} {reply.body!r}"


def _is_a_preflight_answer(reply: Reply) -> None:
    assert reply.values("access-control-allow-methods"), f"barrier: the CORS middleware did not answer the preflight itself: {reply.status} {reply.headers}"


def _is_gzipped(reply: Reply) -> None:
    assert reply.status == 200 and reply.values("content-encoding") == ["gzip"], f"barrier: not compressed: {reply.status} {reply.headers}"
    assert gzip.decompress(reply.body) == LARGE_TEXT, "barrier: the compressed body is not the route's text"


@dataclass(frozen=True)
class Case:
    path: str
    is_the_kind: Callable[[Reply], None]
    method: str = "GET"
    headers: tuple[tuple[str, str], ...] = ()


CASES = {
    "json": Case("/json", _is_the_json),
    "html": Case("/html", _is_the_html),
    "streamed": Case("/stream", _is_streamed),
    "router-404": Case("/no-route-here", _is_the_router_404),
    "cors-preflight": Case("/json", _is_a_preflight_answer, method="OPTIONS", headers=(("Origin", "http://elsewhere.test"), ("Access-Control-Request-Method", "GET"))),
    "gzip-compressed": Case("/large", _is_gzipped, headers=(("Accept-Encoding", "gzip"),)),
}


# =============================================================================
# (a) THE STACK
# =============================================================================


def test_the_entry_stands_outside_gzip_in_the_stack_and_in_the_app() -> None:
    print_section("MIDDLEWARE_STACK: security_headers outside gzip")
    entry = security_entry()

    assert_in_relative_order(MIDDLEWARE_STACK, (ENTRY_NAME, "gzip"), "MIDDLEWARE_STACK")
    with pytest.raises(AssertionError, match="relative order"):
        assert_in_relative_order(MIDDLEWARE_STACK, ("gzip", ENTRY_NAME), "MIDDLEWARE_STACK")  # barrier: the check reads these entries

    classes = [middleware.cls for middleware in app_main.app.user_middleware]
    assert entry.cls in classes and GZipMiddleware in classes, f"the app of backend.app.main holds {classes}"
    assert classes.index(entry.cls) < classes.index(GZipMiddleware), f"the app of backend.app.main holds {classes}: the security headers must stand outside GZip"
    print_success("✓ outside gzip, in the stack and in the app")


# =============================================================================
# (b) EVERY RESPONSE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES.values(), ids=list(CASES))
async def test_every_response_carries_both_headers(case: Case) -> None:
    print_section(f"F15: {case.method} {case.path}")

    reply = await call(stack_app(), case.path, method=case.method, headers=case.headers)

    assert reply.raised is None, f"{case.method} {case.path} raised {reply.raised!r}"
    case.is_the_kind(reply)
    assert_both_headers(reply, f"{case.method} {case.path}")
    print_success("✓ nosniff and strict-origin-when-cross-origin, once each")


@pytest.mark.asyncio
async def test_a_response_start_without_headers_gets_both() -> None:
    print_section("F15: an http.response.start without headers")

    async def bare(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        await send({"type": "http.response.start", "status": 204})
        await send({"type": "http.response.body", "body": b""})

    reply = await call(wrap(bare), "/bare")

    assert (reply.raised, reply.status) == (None, 204), f"barrier: not the bare app's 204: {reply.status}, raised {reply.raised!r}"
    assert_both_headers(reply, "a response start without headers")
    print_success("✓ both added to a start that had none")


# =============================================================================
# (c) A HEADER THE ROUTE SET
# =============================================================================


@pytest.mark.asyncio
async def test_a_referrer_policy_the_route_set_is_kept() -> None:
    print_section("F15: the route sends Referrer-Policy: no-referrer")

    reply = await call(stack_app(), "/sets-referrer-policy")

    assert (reply.raised, reply.status, reply.body) == (None, 200, b"kept"), f"barrier: not the route's answer: {reply.status} {reply.body!r}, raised {reply.raised!r}"
    assert_both_headers(reply, "GET /sets-referrer-policy", referrer_policy="no-referrer")
    print_success("✓ no-referrer kept, alone; nosniff added")


@pytest.mark.asyncio
async def test_a_nosniff_the_route_set_is_not_repeated() -> None:
    print_section("F15: the route sends X-Content-Type-Options: nosniff")

    reply = await call(stack_app(), "/sets-nosniff")

    assert (reply.raised, reply.status, reply.body) == (None, 200, b"once"), f"barrier: not the route's answer: {reply.status} {reply.body!r}, raised {reply.raised!r}"
    assert_both_headers(reply, "GET /sets-nosniff")
    print_success("✓ one nosniff; Referrer-Policy added")


# =============================================================================
# (d) A SCOPE THAT IS NOT HTTP
# =============================================================================

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
            "path": "/ws",
            "raw_path": b"/ws",
            "root_path": "",
            "query_string": b"",
            "headers": [(b"host", b"testserver")],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
            "subprotocols": [],
        },
        {"type": "websocket.connect"},
        ({"type": "websocket.accept", "subprotocol": None, "headers": [(b"x-app", b"as the app sent it")]}, {"type": "websocket.close", "code": 1000, "reason": ""}),
    ),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", list(NON_HTTP))
async def test_a_scope_that_is_not_http_passes_through_untouched(kind: str) -> None:
    print_section(f"F15: a {kind} scope")
    scope, incoming, outgoing = copy.deepcopy(NON_HTTP[kind])
    scope_before, outgoing_before = copy.deepcopy(scope), copy.deepcopy(outgoing)
    seen: list[tuple[Any, Any, Any]] = []
    received: list[dict[str, Any]] = []
    sent: list[dict[str, Any]] = []

    async def app(inner_scope: dict[str, Any], inner_receive: Callable, inner_send: Callable) -> None:
        seen.append((inner_scope, inner_receive, inner_send))
        received.append(await inner_receive())
        for message in outgoing:
            await inner_send(message)

    async def receive() -> dict[str, Any]:
        return incoming

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await asyncio.wait_for(wrap(app)(scope, receive, send), CALL_SECONDS)

    assert len(seen) == 1, f"the app was called {len(seen)} times"
    inner_scope, inner_receive, inner_send = seen[0]
    assert inner_scope is scope and scope == scope_before, f"the {kind} scope was replaced or changed: {inner_scope}"
    assert inner_receive is receive and inner_send is send, f"receive or send of a {kind} scope was wrapped"
    assert received == [incoming]
    assert sent == list(outgoing_before) and all(got is message for got, message in zip(sent, outgoing, strict=True)), f"the messages of a {kind} scope were changed: {sent}"
    print_success("✓ the same scope, receive and send; every message as the app sent it")


# =============================================================================
# (e) THE APP OF backend.app.main
# =============================================================================


def _no_session() -> None:
    """In place of ``get_session_generator``: the instance block reads the session only when it is blocked."""
    return None


def _is_the_provoked_error(exc: BaseException | None) -> bool:
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_the_provoked_error(inner) for inner in exc.exceptions)
    return isinstance(exc, RuntimeError) and str(exc) == PROVOKED


@pytest.mark.asyncio
async def test_the_app_answers_an_api_route_without_login_with_both_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    url = f"{API_V1_PREFIX}/system/health"
    print_section(f"F15 on the app: GET {url}")
    security_entry()
    monkeypatch.delenv("LIBREFOLIO_BLOCKED", raising=False)
    monkeypatch.setitem(app_main.app.dependency_overrides, get_session_generator, _no_session)

    reply = await call(app_main.app, url)

    assert reply.raised is None and reply.status == 200, f"barrier: GET {url} answered {reply.status} {reply.body[:200]!r}, raised {reply.raised!r}"
    assert json.loads(reply.body) == {"status": "ok"}, f"barrier: not the health route's answer: {reply.body[:200]!r}"
    assert_both_headers(reply, f"GET {url} on the app")
    print_success("✓ both headers on an API route")


@pytest.mark.asyncio
async def test_the_app_answers_a_client_side_route_with_both_headers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    print_section("F15 on the app: GET /portfolio/overview, the SPA catch-all")
    security_entry()
    build = tmp_path / "build"
    build.mkdir()
    (build / "index.html").write_bytes(INDEX_HTML)
    (build / "200.html").write_bytes(FALLBACK_HTML)
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build)

    reply = await call(app_main.app, "/portfolio/overview")

    assert (reply.raised, reply.status, reply.body) == (None, 200, FALLBACK_HTML), f"barrier: not the SPA fallback: {reply.status} {reply.body[:200]!r}, raised {reply.raised!r}"
    assert_both_headers(reply, "GET /portfolio/overview on the app")
    print_success("✓ both headers on the SPA fallback")


@pytest.mark.asyncio
async def test_the_500_starlette_sends_for_an_exception_carries_both_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    print_section("F15 on the app: an exception in the catch-all, turned into a 500 by Starlette")
    security_entry()

    def broken() -> bool:
        raise RuntimeError(PROVOKED)

    monkeypatch.setattr(static_site, "frontend_available", broken)

    reply = await call(app_main.app, "/portfolio/overview")

    assert _is_the_provoked_error(reply.raised), f"the provoked exception never reached the server (raised {reply.raised!r}): Starlette re-raises it after its 500 so that the server logs it, and nothing may swallow it"
    assert reply.status == 500, f"barrier: the exception was answered {reply.status}, not 500"
    assert_both_headers(reply, "the 500 of an exception on the app")
    print_success("✓ both headers on the 500; the exception still reached the server")
