"""
The headers of the managed profile (workstream H, platform, checkpoint CP7b-2; developer decision D5, its «managed» part),
and the enforced policy of an HTML document (lot H-42), of every document and never on a 304 (lot H-45).

Under test: ``SecurityHeadersMiddleware`` (``backend/app/services/platform/security_headers.py``, CP7b-1), which reads the
settings ``LIBREFOLIO_FRAME_PROTECTION`` and ``LIBREFOLIO_CSP_REPORT_ONLY`` (``PROFILE_DEFAULTS``: off in self-hosted, on
in managed) once, when it is built: ``SecurityHeadersMiddleware(app)`` calls ``get_settings()`` in ``__init__``. The
contract:

(a) Frame protection. On (``managed``, or ``LIBREFOLIO_FRAME_PROTECTION=true`` under self-hosted): every HTTP response
    carries ``X-Frame-Options: SAMEORIGIN`` and one enforced ``Content-Security-Policy``, once each, whose value follows
    the type of the response (H-42). An HTML document, a ``Content-Type`` starting with ``text/html`` in any case,
    parameters such as ``; charset=utf-8`` allowed, carries exactly ``PAGE_POLICY``, ``frame-ancestors 'self';
    object-src 'none'; base-uri 'self'; form-action 'self'``: here ``/``, a client-side route answered by the catch-all
    (also gzip-compressed), ``/200.html``, the documentation under ``/mkdocs``, Swagger UI and ReDoc under ``/api/v1``,
    the catch-all's HTML 404 of an unknown API path. Every other response carries exactly ``frame-ancestors 'self'``,
    as before H-42: here a text file, an image and a JavaScript chunk of the build, the API's JSON, a CORS preflight, a
    500. Off (self-hosted, or ``false`` over ``managed``): neither header, on any response.
    Why the three directives go on documents only (H-42, security review E, design approved by the coordinator): they
    touch no script, and they mean something only for a document: no plugin content (``object-src 'none'``), no
    injected ``<base>`` retargeting the relative URLs (``base-uri 'self'``), no form sent to another origin
    (``form-action 'self'``). Anywhere else they protect nothing and can break something: Chromium counts its built-in
    PDF viewer as a plugin, so ``object-src 'none'`` on a PDF could stop it showing the PDF inline. The report-only
    policy of (b) and (c) is unchanged by H-42.
(b) The report-only policy. On (``managed``, or ``LIBREFOLIO_CSP_REPORT_ONLY=true``): ``Content-Security-Policy-Report-Only``
    is on the web app's HTML, the responses whose ``Content-Type`` is ``text/html`` outside ``/mkdocs`` and ``/api/``:
    ``/``, a client-side route answered by the catch-all (also gzip-compressed) and ``/200.html``. It is on no other
    response: not the documentation's HTML, not the API's JSON nor its HTML (Swagger UI, ReDoc, the catch-all's HTML 404
    for an unknown API path), not a JavaScript chunk under ``/_app``, an image or a text file of the build, a CORS
    preflight or a 500. Off: on no response. The two switches are independent of each other.
(c) The report-only policy, read directive by directive and never as a string: ``default-src 'self'``, ``object-src
    'none'``, ``base-uri 'self'``, ``frame-ancestors 'self'``, and ``script-src`` with ``'self'`` among its sources; each
    directive once; no ``report-uri`` nor ``report-to`` and no ``Report-To``/``Reporting-Endpoints`` header (decision:
    violations go to the browser's console only).
(d) A header the route set is kept, never overwritten nor repeated, as in CP7b-1: ``X-Frame-Options``,
    ``Content-Security-Policy``, ``Content-Security-Policy-Report-Only``; the middleware still adds the other two, its
    enforced policy on these HTML pages being ``PAGE_POLICY`` (H-42). A route's own ``Content-Security-Policy`` on an HTML
    page stays as the route set it, alone, never replaced by ``PAGE_POLICY``, in both configurations with frame
    protection on.
(e) The settings are read when the middleware is built, never per request: built under one configuration and called
    under the other, it answers as it was built.
(f) CP7b-1's ``X-Content-Type-Options: nosniff`` and ``Referrer-Policy: strict-origin-when-cross-origin`` stay on every
    response, in every configuration. They are also the barrier before every absence: the middleware saw this response.
(g) H-42: the type alone decides the enforced policy, whatever the path. The middleware alone, around a bare ASGI app
    answering one type at a path where the app serves that type, in every configuration: ``text/html``, ``text/html;
    charset=utf-8``, ``TEXT/HTML`` and ``Text/HTML; Charset=UTF-8`` carry ``PAGE_POLICY``; ``application/pdf`` (a
    broker's file shown inline), ``image/png``, ``text/javascript``, ``text/css``, ``application/json`` and a 204
    without ``Content-Type`` carry ``frame-ancestors 'self'``; with frame protection off, none carries either header.
    And ``security_headers.PAGE_POLICY`` is pinned by value: the exact string of (a).
(h) H-45: every document, not HTML only (security review E): opened directly, an XHTML page, an SVG image or an XML file
    is a document too. With frame protection on, a response whose media type (the first ``Content-Type`` before any
    ``;``, stripped, in any case) is in ``security_headers.DOCUMENT_MEDIA_TYPES`` (``text/html``,
    ``application/xhtml+xml``, ``image/svg+xml``, ``application/xml``, ``text/xml``) or ends with
    ``DOCUMENT_MEDIA_TYPE_SUFFIX``, ``+xml`` (Atom, RSS), carries ``PAGE_POLICY``: rows of (g)'s table, beside
    ``application/problem+json``, ``text/plain`` and ``text/htmlx`` (the exact type, never a prefix), which keep
    ``frame-ancestors 'self'``. The two constants are pinned by value, read by name as ``PAGE_POLICY`` is. The report-only
    policy stays on a media type exactly ``text/html``: at a path of the web app where an HTML page carries it (the
    barrier), an SVG, an XHTML page or ``text/htmlx`` carries none.
(i) H-45: no policy on a 304. A browser freshens its cached response with the header fields of a 304 (RFC 9111, 3.2): a
    304 with ``frame-ancestors 'self'`` alone replaces a cached page's ``PAGE_POLICY`` (E's probe, Chromium 149: an
    injected ``<base>`` is no longer blocked after the revalidation). So a 304 gets neither policy from the middleware,
    with or without a ``Content-Type`` (Starlette's ``NotModifiedResponse`` has none; a ``FileResponse`` answering
    conditional requests could send ``text/html``), in every configuration; ``X-Frame-Options``, ``nosniff`` and
    ``Referrer-Policy`` as on any response; a policy its route set kept as written. Alone, the middleware answers each
    304 after the same answer as a 200 (the barrier: what the configuration gives); through the stack, in ``managed``,
    the ``/_app`` mount (``ImmutableStaticFiles``, the one part of the app answering 304) revalidates a JavaScript chunk
    and an SVG image of the fake build, whose 200 carries ``PAGE_POLICY``.

How. Each case first sets its configuration with ``monkeypatch``: ``LIBREFOLIO_TEST_MODE=1`` (``get_settings()`` has no
``_env_file`` argument, and in test mode it reads no ``.env``) and ``LIBREFOLIO_TEST_DATA_DIR`` under ``tmp_path`` (so it
never looks at the lane's data), the profile and the two switches removed, then set as the case says; ``get_settings()``
must resolve the two switches as the case expects (a barrier, so that an absence is never the effect of a variable
nobody read). Then it builds a fresh ``FastAPI()`` assembled as ``backend/app/main.py`` assembles the app: the entries
``security_headers``, ``gzip`` and ``cors`` of ``MIDDLEWARE_STACK`` with their options (as ``test_security_headers``
does), the API docs under ``/api/v1`` (Swagger UI and ReDoc, as in ``main.py``), a few routes, and the static site of a
fake build and a fake documentation under ``tmp_path`` (``FRONTEND_BUILD_DIR`` and ``SITE_DIR`` swapped as in
``test_static_cache_policy``). Starlette builds the middleware at the app's first request, with the configuration in
place. The app of ``backend.app.main`` is never used: its middleware is built once per process, with whatever
configuration came first. (e) and (g) build the middleware alone, around a bare ASGI app, after the configuration is
set. Requests are raw ASGI calls, so every header line is seen as it was sent, duplicates included; each is bounded by
a deadline; the lifespan never runs. A barrier precedes every header: the response is the one its case names (status,
type, body). The module of CP7b-1 is imported when a test runs, so this file collects before it exists; its
``PAGE_POLICY`` (H-42) is read by name, with ``getattr``, in the one test that pins it, so that before H-42 that test
fails naming H-42 while every other test still collects and runs (the others compare each header with this file's own
copy of the value). No DB, no server, no network.
"""

from __future__ import annotations

import asyncio
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
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount

from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.services.platform import static_site
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, MiddlewareEntry, install_middleware
from backend.test_scripts.test_utils import print_section, print_success

SECURITY_MODULE = "backend.app.services.platform.security_headers"
CLASS_NAME = "SecurityHeadersMiddleware"
ENTRY_NAME = "security_headers"
#: H-42: the constant of SECURITY_MODULE holding the enforced policy of an HTML document, read by name when its test runs.
PAGE_POLICY_NAME = "PAGE_POLICY"
#: H-45: the constants of SECURITY_MODULE naming the media types of a document, read by name when their test runs.
DOCUMENT_MEDIA_TYPES_NAME = "DOCUMENT_MEDIA_TYPES"
DOCUMENT_MEDIA_TYPE_SUFFIX_NAME = "DOCUMENT_MEDIA_TYPE_SUFFIX"
#: The entries of MIDDLEWARE_STACK a fresh app holds: this one, and the two whose responses it must see.
STACK_ENTRIES = (ENTRY_NAME, "gzip", "cors")

PROFILE = "LIBREFOLIO_PROFILE"
FRAME_PROTECTION = "LIBREFOLIO_FRAME_PROTECTION"
CSP_REPORT_ONLY = "LIBREFOLIO_CSP_REPORT_ONLY"

# CP7b-1: on every response, in every configuration
NOSNIFF = "nosniff"
REFERRER_POLICY = "strict-origin-when-cross-origin"

# (a) Frame protection
FRAME_OPTIONS = "SAMEORIGIN"
#: The enforced policy of every response that is not an HTML document, exactly: who may frame the app, and nothing else,
#: so that nothing else can break (H-42: ``object-src 'none'`` could stop Chromium's PDF viewer, a plugin).
FRAME_POLICY = "frame-ancestors 'self'"
#: H-42: the enforced policy of an HTML document, exactly this string, in this order (``security_headers.PAGE_POLICY``):
#: who may frame the app, then three directives that touch no script: no plugin content, no ``<base>`` retargeting the
#: relative URLs, no form sent to another origin.
PAGE_POLICY = "frame-ancestors 'self'; object-src 'none'; base-uri 'self'; form-action 'self'"
#: H-45: the media types of a document, exactly (``security_headers.DOCUMENT_MEDIA_TYPES``): opened directly, an XHTML
#: page, an SVG image and an XML file are documents as an HTML page is, so with frame protection on they carry PAGE_POLICY.
DOCUMENT_MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml", "image/svg+xml", "application/xml", "text/xml"})
#: H-45: and every media type of this structured syntax (``security_headers.DOCUMENT_MEDIA_TYPE_SUFFIX``), XML by its
#: name: ``application/atom+xml``, ``application/rss+xml``, ``application/mathml+xml``...
DOCUMENT_MEDIA_TYPE_SUFFIX = "+xml"

# (c) The report-only policy
#: These directives, with exactly these sources.
REPORT_ONLY_EXACT: dict[str, tuple[str, ...]] = {
    "default-src": ("'self'",),
    "object-src": ("'none'",),
    "base-uri": ("'self'",),
    "frame-ancestors": ("'self'",),
}
#: ``script-src``, with at least these sources.
SCRIPT_SRC_INCLUDES = ("'self'",)
#: Decision: the violations go to the browser's console, and nowhere else.
NO_REPORT_DIRECTIVES = ("report-uri", "report-to")
NO_REPORT_HEADERS = ("report-to", "reporting-endpoints")

#: The three headers of D5 for the managed profile, as they appear in a raw ASGI message.
D5_HEADERS = ("x-frame-options", "content-security-policy", "content-security-policy-report-only")

#: Every raw call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0

PAGE_HTML = b"<!doctype html><title>page</title>"
INDEX_HTML = b"<!doctype html><title>index</title>"
#: Over GZip's minimum_size (1024 in MIDDLEWARE_STACK): the client-side route asked with Accept-Encoding: gzip is compressed.
FALLBACK_HTML = b"<!doctype html><title>spa fallback</title>\n" + b"<p>LibreFolio keeps the history of your investments.</p>\n" * 40
ROBOTS_TXT = b"User-agent: *\nDisallow:\n"
#: An image of the build, answered by the catch-all as image/png (its extension): a PNG signature is enough.
FAVICON_PNG = b"\x89PNG\r\n\x1a\nfavicon"
CHUNK_JS = b"export const chunk = 'a1b2';\n"
#: H-45: an SVG image of the build under /_app, served by the mount (the one part of the app answering 304): a document.
LOGO_SVG_PATH = "/_app/immutable/assets/logo.a1b2.svg"
LOGO_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16"><circle cx="8" cy="8" r="7"/></svg>\n'
DOCS_INDEX_HTML = b"<!doctype html><title>documentation</title>"
DOCS_PAGE_HTML = b"<!doctype html><title>documentation: user guide</title>"
PROVOKED = "provoked: the API route fails"
#: What the page routes of (d) set themselves.
ROUTE_FRAME_OPTIONS = "DENY"
ROUTE_CSP = "frame-ancestors 'none'"
ROUTE_CSP_REPORT_ONLY = "default-src 'none'"

#: The fake build: path relative to the build folder, and content.
BUILD_FILES: dict[str, bytes] = {
    "index.html": INDEX_HTML,
    "200.html": FALLBACK_HTML,
    "robots.txt": ROBOTS_TXT,
    "favicon.png": FAVICON_PNG,
    "_app/immutable/chunks/a1b2.js": CHUNK_JS,
    LOGO_SVG_PATH.removeprefix("/"): LOGO_SVG,
}
#: The fake documentation: path relative to the site folder, and content.
SITE_FILES: dict[str, bytes] = {"index.html": DOCS_INDEX_HTML, "user/index.html": DOCS_PAGE_HTML}


# =============================================================================
# THE CONFIGURATIONS
# =============================================================================


@dataclass(frozen=True)
class Mode:
    """A configuration: the variables it sets (of the profile and the two switches, the others are unset), and the
    switches ``get_settings()`` must resolve them to."""

    env: tuple[tuple[str, str], ...]
    frame_protection: bool
    csp_report_only: bool

    def describe(self) -> str:
        return ", ".join(f"{name}={value}" for name, value in self.env) or "nothing set"


MODES: dict[str, Mode] = {
    "selfhosted-nothing-set": Mode((), frame_protection=False, csp_report_only=False),
    "selfhosted": Mode(((PROFILE, "selfhosted"),), frame_protection=False, csp_report_only=False),
    "managed": Mode(((PROFILE, "managed"),), frame_protection=True, csp_report_only=True),
    "selfhosted-frame-protection-true": Mode(((FRAME_PROTECTION, "true"),), frame_protection=True, csp_report_only=False),
    "selfhosted-csp-report-only-true": Mode(((CSP_REPORT_ONLY, "true"),), frame_protection=False, csp_report_only=True),
    "managed-both-switches-false": Mode(((PROFILE, "managed"), (FRAME_PROTECTION, "false"), (CSP_REPORT_ONLY, "false")), frame_protection=False, csp_report_only=False),
}
REPORT_ONLY_MODES = {name: mode for name, mode in MODES.items() if mode.csp_report_only}
FRAME_PROTECTION_MODES = {name: mode for name, mode in MODES.items() if mode.frame_protection}


def configure(monkeypatch: pytest.MonkeyPatch, mode: Mode, tmp_path: Path) -> None:
    """Make ``mode`` the configuration ``get_settings()`` reads, and check that it reads it so."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # get_settings() reads no .env in test mode: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))  # get_settings() never looks at the lane's data
    for name in (PROFILE, FRAME_PROTECTION, CSP_REPORT_ONLY):
        monkeypatch.delenv(name, raising=False)
    for name, value in mode.env:
        monkeypatch.setenv(name, value)

    settings = get_settings()

    missing = [name for name in (FRAME_PROTECTION, CSP_REPORT_ONLY) if name not in type(settings).model_fields]
    assert not missing, f"barrier: Settings has no field {missing}: without the switches of D5 (CP7b-2) no configuration can be told from another"
    resolved = (getattr(settings, FRAME_PROTECTION), getattr(settings, CSP_REPORT_ONLY))
    assert resolved[0] is mode.frame_protection and resolved[1] is mode.csp_report_only, f"barrier: with {mode.describe()}, get_settings() resolves {FRAME_PROTECTION}={resolved[0]!r} and {CSP_REPORT_ONLY}={resolved[1]!r}, not {mode.frame_protection} and {mode.csp_report_only}"


# =============================================================================
# THE MIDDLEWARE OF CP7b-1, IMPORTED WHEN A TEST RUNS
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
    """``app`` inside the middleware, built now, as the stack builds it: with the entry's options."""
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
    raised: BaseException | None

    def values(self, name: str) -> list[str]:
        """Every value sent for the header ``name``, in order."""
        return [value for key, value in self.headers if key == name]

    @property
    def media_type(self) -> str:
        """The type of the body, lower-cased and without its parameters; empty without a Content-Type."""
        types = self.values("content-type")
        return types[0].partition(";")[0].strip().lower() if types else ""

    @property
    def content(self) -> bytes:
        """The body as the route wrote it: decompressed when it came gzip-compressed."""
        return gzip.decompress(self.body) if self.values("content-encoding") == ["gzip"] else self.body


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

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await complete.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        nonlocal starts, status
        if message["type"] == "http.response.start":
            starts += 1
            status = message["status"]
            sent_headers.extend((bytes(name).decode("latin-1").lower(), bytes(value).decode("latin-1")) for name, value in message.get("headers", ()))
        elif message["type"] == "http.response.body":
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
    return Reply(starts=starts, status=status, headers=sent_headers, body=bytes(body), raised=raised)


def assert_always_on(reply: Reply, what: str) -> None:
    """One response, with CP7b-1's two headers once each: the middleware saw it (the barrier before any absence)."""
    assert reply.starts == 1, f"{what}: {reply.starts} response starts were sent"
    assert reply.values("x-content-type-options") == [NOSNIFF], f"{what}: X-Content-Type-Options is {reply.values('x-content-type-options')}, wanted exactly one, {NOSNIFF!r}; headers {reply.headers}"
    assert reply.values("referrer-policy") == [REFERRER_POLICY], f"{what}: Referrer-Policy is {reply.values('referrer-policy')}, wanted exactly one, {REFERRER_POLICY!r}; headers {reply.headers}"


def parse_policy(value: str) -> list[tuple[str, tuple[str, ...]]]:
    """A CSP header value as ``[(directive, sources)]`` in order, lower-cased (CSP keywords ignore case); empty parts dropped."""
    parsed = []
    for part in value.split(";"):
        tokens = part.split()
        if tokens:
            parsed.append((tokens[0].lower(), tuple(token.lower() for token in tokens[1:])))
    return parsed


def directives(value: str, what: str) -> dict[str, tuple[str, ...]]:
    """``parse_policy`` as ``{directive: sources}``, each directive once: a browser ignores a repeated one, unseen."""
    parsed = parse_policy(value)
    names = [name for name, _ in parsed]
    repeated = sorted({name for name in names if names.count(name) > 1})
    assert not repeated, f"{what}: the directives {repeated} appear more than once in {value!r}"
    return dict(parsed)


def present(reply: Reply) -> dict[str, bool]:
    """Which of the three headers of D5 the reply carries."""
    return {name: bool(reply.values(name)) for name in D5_HEADERS}


# =============================================================================
# A FRESH APP, ASSEMBLED AS main.py ASSEMBLES ITS OWN
# =============================================================================


async def api_things() -> JSONResponse:
    return JSONResponse({"ok": True})


async def api_boom() -> JSONResponse:
    raise RuntimeError(PROVOKED)


async def sets_frame_options() -> HTMLResponse:
    return HTMLResponse(PAGE_HTML, headers={"X-Frame-Options": ROUTE_FRAME_OPTIONS})


async def sets_csp() -> HTMLResponse:
    return HTMLResponse(PAGE_HTML, headers={"Content-Security-Policy": ROUTE_CSP})


async def sets_csp_report_only() -> HTMLResponse:
    return HTMLResponse(PAGE_HTML, headers={"Content-Security-Policy-Report-Only": ROUTE_CSP_REPORT_ONLY})


#: Registered after the API docs and before the static site, whose catch-all stays last.
ROUTES: dict[str, Callable] = {
    f"{API_V1_PREFIX}/things": api_things,
    f"{API_V1_PREFIX}/boom": api_boom,
    "/sets-frame-options": sets_frame_options,
    "/sets-csp": sets_csp,
    "/sets-csp-report-only": sets_csp_report_only,
}


def _write_tree(root: Path, files: dict[str, bytes]) -> Path:
    for relative, content in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes(content)
    return root


def site_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """A fresh app: the stack's ``security_headers``, ``gzip`` and ``cors``, the API docs (Swagger UI and ReDoc, as in
    ``main.py``), ``ROUTES``, then the static site of a fake build and documentation. Its middleware is built at its first
    request, with the configuration then in place."""
    security_entry()
    stack = tuple(entry for entry in MIDDLEWARE_STACK if entry.name in STACK_ENTRIES)
    assert sorted(entry.name for entry in stack) == sorted(STACK_ENTRIES), f"MIDDLEWARE_STACK must hold {STACK_ENTRIES} once each: {[entry.name for entry in MIDDLEWARE_STACK]}"
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", _write_tree(tmp_path / "build", BUILD_FILES))
    monkeypatch.setattr(static_site, "SITE_DIR", _write_tree(tmp_path / "site", SITE_FILES))

    app = FastAPI(openapi_url=f"{API_V1_PREFIX}/openapi.json", docs_url=f"{API_V1_PREFIX}/docs", redoc_url=f"{API_V1_PREFIX}/redoc")
    install_middleware(app, stack)
    for path, endpoint in ROUTES.items():
        app.add_api_route(path, endpoint, methods=["GET"])
    static_site.install_static_site(app)

    mounts = [route.path for route in app.routes if isinstance(route, Mount)]
    assert mounts == ["/_app"], f"barrier: the static site of a complete build mounts /_app, found {mounts}: without it the catch-all would answer /_app and prove nothing about the mount"
    return app


# =============================================================================
# THE CASES: ONE REQUEST, AND THE BARRIER PROVING THE RESPONSE IS THE ONE IT NAMES
# =============================================================================

HTML = ("text/html",)
TEXT = ("text/plain",)
IMAGE = ("image/png",)
JAVASCRIPT = ("text/javascript", "application/javascript")
SVG = ("image/svg+xml",)


def answered(status: int, media_types: tuple[str, ...], body: bytes, *, compressed: bool = False) -> Callable[[Reply], None]:
    """Barrier: the answer is ``status``, of one of ``media_types``, with ``body``; gzip-compressed exactly when ``compressed``."""

    def check(reply: Reply) -> None:
        assert reply.raised is None, f"barrier: the app raised {reply.raised!r}"
        assert reply.status == status and reply.media_type in media_types, f"barrier: answered {reply.status} {reply.media_type!r}, not {status} {media_types}; headers {reply.headers}"
        assert (reply.values("content-encoding") == ["gzip"]) is compressed, f"barrier: Content-Encoding {reply.values('content-encoding')}, while compressed={compressed}"
        assert reply.content == body, f"barrier: not the expected body: {reply.content[:120]!r}"

    return check


def _is_the_json(reply: Reply) -> None:
    assert reply.raised is None and reply.status == 200 and reply.media_type == "application/json", f"barrier: not the route's JSON: {reply.status} {reply.headers}, raised {reply.raised!r}"
    assert json.loads(reply.body) == {"ok": True}, f"barrier: not the route's JSON: {reply.body[:120]!r}"


def _is_swagger_ui(reply: Reply) -> None:
    assert reply.raised is None and reply.status == 200 and reply.media_type == "text/html", f"barrier: not the API docs' HTML: {reply.status} {reply.headers}, raised {reply.raised!r}"
    assert b"swagger-ui" in reply.body, f"barrier: not Swagger UI: {reply.body[:120]!r}"


def _is_redoc(reply: Reply) -> None:
    assert reply.raised is None and reply.status == 200 and reply.media_type == "text/html", f"barrier: not the API docs' HTML: {reply.status} {reply.headers}, raised {reply.raised!r}"
    assert b"<redoc spec-url=" in reply.body, f"barrier: not ReDoc: {reply.body[:120]!r}"


def _is_an_html_404(reply: Reply) -> None:
    assert reply.raised is None and reply.status == 404 and reply.media_type == "text/html", f"barrier: not the catch-all's HTML 404 of an API path: {reply.status} {reply.headers} {reply.body[:120]!r}, raised {reply.raised!r}"


def _is_a_preflight_answer(reply: Reply) -> None:
    assert reply.raised is None and reply.values("access-control-allow-methods"), f"barrier: the CORS middleware did not answer the preflight itself: {reply.status} {reply.headers}, raised {reply.raised!r}"


def _is_the_provoked_error(exc: BaseException | None) -> bool:
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_the_provoked_error(inner) for inner in exc.exceptions)
    return isinstance(exc, RuntimeError) and str(exc) == PROVOKED


def _is_the_500(reply: Reply) -> None:
    assert _is_the_provoked_error(reply.raised), f"barrier: the route's exception never reached the server (raised {reply.raised!r})"
    assert reply.status == 500, f"barrier: the exception was answered {reply.status}, not 500"


@dataclass(frozen=True)
class Case:
    path: str
    is_the_kind: Callable[[Reply], None]
    #: An HTML document (text/html, wherever it is): with frame protection on, its enforced policy is PAGE_POLICY (H-42).
    html: bool
    #: An HTML document of the web app (text/html, outside /mkdocs and /api/): where the report-only policy goes when on.
    web_app_html: bool
    method: str = "GET"
    headers: tuple[tuple[str, str], ...] = ()


CASES: dict[str, Case] = {
    # The web app's HTML documents
    "root": Case("/", answered(200, HTML, INDEX_HTML), html=True, web_app_html=True),
    "client-side-route": Case("/portfolio/overview", answered(200, HTML, FALLBACK_HTML), html=True, web_app_html=True),
    "client-side-route-gzipped": Case("/portfolio/overview", answered(200, HTML, FALLBACK_HTML, compressed=True), html=True, web_app_html=True, headers=(("Accept-Encoding", "gzip"),)),
    "200-html": Case("/200.html", answered(200, HTML, FALLBACK_HTML), html=True, web_app_html=True),
    # Every other response
    "text-file-of-the-build": Case("/robots.txt", answered(200, TEXT, ROBOTS_TXT), html=False, web_app_html=False),
    "image-of-the-build": Case("/favicon.png", answered(200, IMAGE, FAVICON_PNG), html=False, web_app_html=False),
    "javascript-under-app": Case("/_app/immutable/chunks/a1b2.js", answered(200, JAVASCRIPT, CHUNK_JS), html=False, web_app_html=False),
    "docs-root": Case("/mkdocs", answered(200, HTML, DOCS_INDEX_HTML), html=True, web_app_html=False),
    "docs-page": Case("/mkdocs/user/", answered(200, HTML, DOCS_PAGE_HTML), html=True, web_app_html=False),
    "api-json": Case(f"{API_V1_PREFIX}/things", _is_the_json, html=False, web_app_html=False),
    "api-html-swagger-ui": Case(f"{API_V1_PREFIX}/docs", _is_swagger_ui, html=True, web_app_html=False),
    "api-html-redoc": Case(f"{API_V1_PREFIX}/redoc", _is_redoc, html=True, web_app_html=False),
    "api-unknown-path-html-404": Case(f"{API_V1_PREFIX}/no-such-route", _is_an_html_404, html=True, web_app_html=False),
    "api-cors-preflight": Case(f"{API_V1_PREFIX}/things", _is_a_preflight_answer, html=False, web_app_html=False, method="OPTIONS", headers=(("Origin", "http://elsewhere.test"), ("Access-Control-Request-Method", "GET"))),
    "api-500": Case(f"{API_V1_PREFIX}/boom", _is_the_500, html=False, web_app_html=False),
}
WEB_APP_HTML = {name: case for name, case in CASES.items() if case.web_app_html}


async def answer(case: Case, mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Reply:
    """``case`` on a fresh app built under ``mode``, past its barriers: the response is the one the case names, of the
    type the case declares (an HTML document or not), and the middleware saw it."""
    configure(monkeypatch, mode, tmp_path)
    reply = await call(site_app(tmp_path, monkeypatch), case.path, method=case.method, headers=case.headers)
    case.is_the_kind(reply)
    assert (reply.media_type == "text/html") is case.html, f"barrier: {case.method} {case.path} answered {reply.media_type!r}, while the case declares html={case.html}; headers {reply.headers}"
    assert_always_on(reply, f"{case.method} {case.path} with {mode.describe()}")
    return reply


# =============================================================================
# (a) FRAME PROTECTION, ITS POLICY BY TYPE (H-42), AND (f) THE HEADERS OF CP7b-1
# =============================================================================


def assert_frame_protection(reply: Reply, on: bool, document: bool, what: str) -> str:
    """Frame protection ``on``: ``X-Frame-Options: SAMEORIGIN`` and one enforced policy, the one of the response's type,
    exactly: ``PAGE_POLICY`` on a document (an HTML page, H-42; since H-45 also XHTML, SVG, XML, any ``+xml`` type),
    ``frame-ancestors 'self'`` alone on anything else (H-42). Off: neither header. Returns what it saw, for the log."""
    frame_options, policies = reply.values("x-frame-options"), reply.values("content-security-policy")
    if not on:
        assert frame_options == [] and policies == [], f"{what}: frame protection is off, yet X-Frame-Options is {frame_options} and Content-Security-Policy {policies}"
        return "neither X-Frame-Options nor Content-Security-Policy"
    if document:
        expected, why = PAGE_POLICY, "a document carries PAGE_POLICY, frame-ancestors then object-src, base-uri and form-action: an HTML page (H-42), and since H-45 any media type of DOCUMENT_MEDIA_TYPES or ending with +xml (XHTML, SVG, XML), in any case"
    else:
        expected, why = FRAME_POLICY, "a response that is not a document carries frame-ancestors 'self' and nothing else (H-42: object-src 'none' could stop Chromium's PDF viewer, a plugin; H-45: by its exact media type, never a prefix)"
    assert frame_options == [FRAME_OPTIONS], f"{what}: X-Frame-Options is {frame_options}, wanted exactly one, {FRAME_OPTIONS!r}"
    assert policies == [expected], f"{what}: Content-Security-Policy is {policies}, wanted exactly one, {expected!r}: {why}"
    return f"X-Frame-Options: {FRAME_OPTIONS} and Content-Security-Policy: {expected}, once each"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES.values(), ids=list(CASES))
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_frame_protection_is_on_every_response_when_on_and_on_none_when_off(mode: Mode, case: Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"{case.method} {case.path} with {mode.describe()}"
    print_section(f"D5 frame protection: {what}")

    reply = await answer(case, mode, tmp_path, monkeypatch)

    print_success(f"✓ {assert_frame_protection(reply, mode.frame_protection, case.html, what)}; nosniff and Referrer-Policy")


# =============================================================================
# (b) THE REPORT-ONLY POLICY: WHERE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES.values(), ids=list(CASES))
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_the_report_only_policy_is_only_on_the_web_apps_html_and_only_when_on(mode: Mode, case: Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"{case.method} {case.path} with {mode.describe()}"
    print_section(f"D5 report-only policy: {what}")

    reply = await answer(case, mode, tmp_path, monkeypatch)

    policies = reply.values("content-security-policy-report-only")
    if mode.csp_report_only and case.web_app_html:
        assert len(policies) == 1, f"{what}: an HTML document of the web app with the report-only policy on carries {len(policies)} Content-Security-Policy-Report-Only: {policies}"
        print_success("✓ one Content-Security-Policy-Report-Only")
    else:
        why = "the policy is off" if not mode.csp_report_only else f"{reply.media_type!r} under {case.path} is not an HTML document of the web app"
        assert policies == [], f"{what}: {why}, yet Content-Security-Policy-Report-Only is {policies}"
        print_success(f"✓ none: {why}")


# =============================================================================
# (c) THE REPORT-ONLY POLICY: WHAT
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", WEB_APP_HTML.values(), ids=list(WEB_APP_HTML))
@pytest.mark.parametrize("mode", REPORT_ONLY_MODES.values(), ids=list(REPORT_ONLY_MODES))
async def test_the_report_only_policy_has_the_key_directives_and_reports_nowhere(mode: Mode, case: Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"{case.method} {case.path} with {mode.describe()}"
    print_section(f"D5 report-only policy, its directives: {what}")

    reply = await answer(case, mode, tmp_path, monkeypatch)

    policies = reply.values("content-security-policy-report-only")
    assert len(policies) == 1, f"barrier: {what} carries {len(policies)} Content-Security-Policy-Report-Only: {policies}"
    policy = directives(policies[0], what)
    wrong = {name: policy.get(name) for name, sources in REPORT_ONLY_EXACT.items() if sorted(policy.get(name, ())) != sorted(sources)}
    assert not wrong, f"{what}: in {policies[0]!r} these directives are not as decided, {REPORT_ONLY_EXACT} ({{directive: sources found}}): {wrong}"
    script_src = policy.get("script-src", ())
    assert set(SCRIPT_SRC_INCLUDES) <= set(script_src), f"{what}: script-src is {script_src} in {policies[0]!r}, without {SCRIPT_SRC_INCLUDES}"
    reporting = [name for name in NO_REPORT_DIRECTIVES if name in policy]
    assert not reporting, f"{what}: {reporting} in {policies[0]!r}, yet violations go to the browser's console only"
    endpoints = {name: reply.values(name) for name in NO_REPORT_HEADERS if reply.values(name)}
    assert not endpoints, f"{what}: reporting endpoints are declared, yet violations go to the browser's console only: {endpoints}"
    print_success(f"✓ {policies[0]}")


# =============================================================================
# (d) A HEADER THE ROUTE SET
# =============================================================================

#: The header a page route sets, and its path and value.
ROUTE_SETS: dict[str, tuple[str, str]] = {
    "x-frame-options": ("/sets-frame-options", ROUTE_FRAME_OPTIONS),
    "content-security-policy": ("/sets-csp", ROUTE_CSP),
    "content-security-policy-report-only": ("/sets-csp-report-only", ROUTE_CSP_REPORT_ONLY),
}


def is_the_middlewares(name: str, values: list[str]) -> bool:
    """``values`` is the one value the middleware gives the header ``name`` of D5 on a page of the web app, in ``managed``:
    the page is an HTML document, so its enforced policy is ``PAGE_POLICY`` (H-42)."""
    if len(values) != 1:
        return False
    if name == "x-frame-options":
        return values[0] == FRAME_OPTIONS
    if name == "content-security-policy":
        return values[0] == PAGE_POLICY
    return dict(parse_policy(values[0])).get("default-src") == REPORT_ONLY_EXACT["default-src"]


@pytest.mark.asyncio
@pytest.mark.parametrize("header", list(ROUTE_SETS))
async def test_a_header_the_route_set_is_kept_and_the_others_are_added(header: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, value = ROUTE_SETS[header]
    print_section(f"D5, managed: the route {path} sends {header}: {value}")
    page = Case(path, answered(200, HTML, PAGE_HTML), html=True, web_app_html=True)

    reply = await answer(page, MODES["managed"], tmp_path, monkeypatch)

    assert reply.values(header) == [value], f"GET {path}: {header} is {reply.values(header)}; the route's {value!r} must stay, alone, as in CP7b-1"
    others = {name: reply.values(name) for name in D5_HEADERS if name != header and not is_the_middlewares(name, reply.values(name))}
    assert not others, f"GET {path}: the middleware must still add its own value of the other headers of D5, once each, on this HTML page Content-Security-Policy {PAGE_POLICY!r} (H-42): {others}"
    print_success(f"✓ the route's {header} kept alone; the other two added")


# =============================================================================
# (e) READ WHEN BUILT
# =============================================================================


async def html_page(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
    """A bare ASGI app answering an HTML page outside /mkdocs and /api/: where every header of D5 goes when it is on."""
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/html; charset=utf-8")]})
    await send({"type": "http.response.body", "body": PAGE_HTML})


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("built", "called"),
    [
        pytest.param("managed", "selfhosted-nothing-set", id="built-managed-called-selfhosted"),
        pytest.param("selfhosted-nothing-set", "managed", id="built-selfhosted-called-managed"),
    ],
)
async def test_the_settings_are_read_when_the_middleware_is_built_never_per_request(built: str, called: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    print_section(f"D5: the middleware built {built}, called {called}")
    configure(monkeypatch, MODES[built], tmp_path)
    middleware = wrap(html_page)  # SecurityHeadersMiddleware(app): the settings are read here
    configure(monkeypatch, MODES[called], tmp_path)  # barrier inside: get_settings() now resolves the other configuration

    reply = await call(middleware, "/")

    answered(200, HTML, PAGE_HTML)(reply)
    assert_always_on(reply, f"GET / built {built}, called {called}")
    expected = dict(zip(D5_HEADERS, (MODES[built].frame_protection, MODES[built].frame_protection, MODES[built].csp_report_only), strict=True))
    assert present(reply) == expected, f"built {built} and called {called}, the headers of D5 present are {present(reply)}, not those of the configuration it was built with, {expected}: the settings must be read once, in __init__"
    print_success(f"✓ answered as built: {expected}")


# =============================================================================
# (g) H-42, AND (h) H-45: THE ENFORCED POLICY FOLLOWS THE TYPE OF THE RESPONSE
# =============================================================================

#: A broker's file shown inline (``download=false``): Chromium shows it in its built-in PDF viewer, a plugin to CSP.
BROKER_FILE_PDF = b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
APP_CSS = b"body { margin: 0; }\n"
API_JSON = b'{"ok": true}'
#: H-45: documents that are not HTML, each opened directly: an XHTML page, the documentation's sitemap, a broker's XML
#: report shown inline, two feeds; and an API error in the problem format, JSON and no document.
XHTML_PAGE = b'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>page</title></head><body/></html>\n'
SITEMAP_XML = b'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/>\n'
BROKER_FILE_XML = b'<?xml version="1.0" encoding="UTF-8"?>\n<FlexQueryResponse queryName="activity" type="AF"/>\n'
ATOM_FEED = b'<?xml version="1.0" encoding="utf-8"?>\n<feed xmlns="http://www.w3.org/2005/Atom"><title>news</title></feed>\n'
RSS_FEED = b'<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel><title>news</title></channel></rss>\n'
PROBLEM_JSON = b'{"type": "about:blank", "title": "Not Found", "status": 404}'


@dataclass(frozen=True)
class TypedAnswer:
    """What a bare ASGI app answers at ``path``: ``status``, a ``Content-Type`` written as given (``None``: no
    ``Content-Type`` at all) and ``body``. ``document``: a document, whose enforced policy is ``PAGE_POLICY``: an HTML
    page (H-42), and since H-45 an XHTML page, an SVG image, an XML file, any media type ending with ``+xml``."""

    path: str
    content_type: str | None
    body: bytes
    document: bool
    status: int = 200


#: Each type at a path where the app serves it, or could, HTML under /mkdocs and /api/ too: the type decides, never the path.
TYPED_ANSWERS: dict[str, TypedAnswer] = {
    # HTML documents: text/html in any case, parameters allowed
    "text-html": TypedAnswer("/", "text/html", PAGE_HTML, document=True),
    "text-html-charset-utf-8": TypedAnswer("/portfolio/overview", "text/html; charset=utf-8", PAGE_HTML, document=True),
    "uppercase-TEXT-HTML": TypedAnswer("/mkdocs/user/", "TEXT/HTML", PAGE_HTML, document=True),
    "mixed-case-with-charset": TypedAnswer(f"{API_V1_PREFIX}/docs", "Text/HTML; Charset=UTF-8", PAGE_HTML, document=True),
    # Every other type, and none at all
    "application-pdf": TypedAnswer(f"{API_V1_PREFIX}/brokers/import/files/7/download", "application/pdf", BROKER_FILE_PDF, document=False),
    "image-png": TypedAnswer("/favicon.png", "image/png", FAVICON_PNG, document=False),
    "text-javascript": TypedAnswer("/_app/immutable/chunks/a1b2.js", "text/javascript; charset=utf-8", CHUNK_JS, document=False),
    "text-css": TypedAnswer("/_app/immutable/assets/app.css", "text/css; charset=utf-8", APP_CSS, document=False),
    "application-json": TypedAnswer(f"{API_V1_PREFIX}/things", "application/json", API_JSON, document=False),
    "no-content-type": TypedAnswer(f"{API_V1_PREFIX}/things/7", None, b"", document=False, status=204),
    # H-45, (h): the other documents, XHTML, SVG, XML and any +xml type, by the media type in any case, parameters allowed
    "application-xhtml-xml": TypedAnswer("/page.xhtml", "application/xhtml+xml", XHTML_PAGE, document=True),
    "image-svg-xml": TypedAnswer(f"{API_V1_PREFIX}/uploads/file/9", "image/svg+xml", LOGO_SVG, document=True),
    "image-svg-xml-charset-utf-8": TypedAnswer(LOGO_SVG_PATH, "image/svg+xml; charset=utf-8", LOGO_SVG, document=True),
    "mixed-case-Image-SVG-XML": TypedAnswer("/mkdocs/assets/images/logo.svg", "Image/SVG+XML", LOGO_SVG, document=True),
    "application-xml": TypedAnswer("/mkdocs/sitemap.xml", "application/xml", SITEMAP_XML, document=True),
    "text-xml-charset-utf-8": TypedAnswer(f"{API_V1_PREFIX}/brokers/import/files/8/download", "text/xml; charset=utf-8", BROKER_FILE_XML, document=True),
    "application-atom-xml": TypedAnswer("/feed.atom", "application/atom+xml", ATOM_FEED, document=True),
    "application-rss-xml-charset-utf-8": TypedAnswer("/feed.rss", "application/rss+xml; charset=utf-8", RSS_FEED, document=True),
    # H-45, (h): no documents, by the exact media type: a +json problem, a text file, a type only starting like HTML's
    "application-problem-json": TypedAnswer(f"{API_V1_PREFIX}/things/0", "application/problem+json", PROBLEM_JSON, document=False, status=404),
    "text-plain": TypedAnswer("/robots.txt", "text/plain; charset=utf-8", ROBOTS_TXT, document=False),
    "text-htmlx": TypedAnswer("/page.htmlx", "text/htmlx", PAGE_HTML, document=False),
}


def answering(typed: TypedAnswer) -> Callable:
    """A bare ASGI app answering ``typed``: its status, its Content-Type as written (none at all when ``None``), its body."""

    async def app(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        headers = [] if typed.content_type is None else [(b"content-type", typed.content_type.encode("latin-1"))]
        await send({"type": "http.response.start", "status": typed.status, "headers": headers})
        await send({"type": "http.response.body", "body": typed.body})

    return app


def assert_bare_answer(reply: Reply, typed: TypedAnswer, what: str) -> None:
    """Barrier: ``reply`` is the bare app's answer ``typed``: its status and its body, its Content-Type as written."""
    sent_type = [] if typed.content_type is None else [typed.content_type]
    assert reply.raised is None and reply.status == typed.status and reply.body == typed.body, f"barrier: {what}: not the bare app's answer: {reply.status} {reply.body[:120]!r}, raised {reply.raised!r}"
    assert reply.values("content-type") == sent_type, f"barrier: {what}: the Content-Type reached the client as {reply.values('content-type')}, not as written, {sent_type}"


def test_page_policy_is_pinned_by_value() -> None:
    print_section(f"H-42: {SECURITY_MODULE}.{PAGE_POLICY_NAME}, by value")

    # Read by name: before H-42 this test fails, naming H-42, while every other test of the file still collects and runs
    policy = getattr(importlib.import_module(SECURITY_MODULE), PAGE_POLICY_NAME, None)

    assert policy is not None, f"H-42: {SECURITY_MODULE} has no {PAGE_POLICY_NAME}, the enforced Content-Security-Policy of an HTML document when frame protection is on; wanted {PAGE_POLICY!r}"
    assert policy == PAGE_POLICY, f"H-42: {SECURITY_MODULE}.{PAGE_POLICY_NAME} is {policy!r}, not the string {PAGE_POLICY!r}: frame-ancestors 'self', then object-src 'none', base-uri 'self' and form-action 'self', in this order, separated by '; '"
    print_success(f"✓ {PAGE_POLICY_NAME} = {PAGE_POLICY!r}")


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", TYPED_ANSWERS.values(), ids=list(TYPED_ANSWERS))
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_the_enforced_policy_follows_the_type_of_the_response(mode: Mode, typed: TypedAnswer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"GET {typed.path} answered {typed.status} {typed.content_type or 'without Content-Type'} with {mode.describe()}"
    print_section(f"H-42/H-45 enforced policy by type: {what}")
    configure(monkeypatch, mode, tmp_path)

    reply = await call(wrap(answering(typed)), typed.path)  # SecurityHeadersMiddleware(app) built here, configuration in place

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    print_success(f"✓ {assert_frame_protection(reply, mode.frame_protection, typed.document, what)}; nosniff and Referrer-Policy")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", FRAME_PROTECTION_MODES.values(), ids=list(FRAME_PROTECTION_MODES))
async def test_an_html_page_keeps_the_policy_its_route_set(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, value = ROUTE_SETS["content-security-policy"]
    what = f"GET {path} with {mode.describe()}"
    print_section(f"H-42: an HTML page whose route set its own Content-Security-Policy, {value}: {what}")
    page = Case(path, answered(200, HTML, PAGE_HTML), html=True, web_app_html=True)

    reply = await answer(page, mode, tmp_path, monkeypatch)

    policies = reply.values("content-security-policy")
    assert policies == [value], f"{what}: Content-Security-Policy is {policies}; the route's {value!r} must stay, alone, on an HTML page too: never replaced by PAGE_POLICY, never joined by a second policy"
    assert reply.values("x-frame-options") == [FRAME_OPTIONS], f"{what}: X-Frame-Options is {reply.values('x-frame-options')}, wanted exactly one, {FRAME_OPTIONS!r}"
    print_success(f"✓ the route's {value!r} kept alone; X-Frame-Options: {FRAME_OPTIONS} added")


# =============================================================================
# (h) H-45: THE MEDIA TYPES OF A DOCUMENT, BY VALUE; THE REPORT-ONLY POLICY STAYS ON text/html
# =============================================================================


def test_the_document_media_types_are_pinned_by_value() -> None:
    """H-45: the media types of a document, by value: five exactly, ``DOCUMENT_MEDIA_TYPES``, and every one ending with
    ``DOCUMENT_MEDIA_TYPE_SUFFIX``, ``+xml``, the structured-syntax suffix of XML."""
    print_section(f"H-45: {SECURITY_MODULE}.{DOCUMENT_MEDIA_TYPES_NAME} and {DOCUMENT_MEDIA_TYPE_SUFFIX_NAME}, by value")

    # Read by name: before H-45 this test fails, naming H-45, while every other test of the file still collects and runs
    module = importlib.import_module(SECURITY_MODULE)
    media_types, suffix = getattr(module, DOCUMENT_MEDIA_TYPES_NAME, None), getattr(module, DOCUMENT_MEDIA_TYPE_SUFFIX_NAME, None)

    assert media_types is not None, f"H-45: {SECURITY_MODULE} has no {DOCUMENT_MEDIA_TYPES_NAME}, the media types of a document, which carries PAGE_POLICY when frame protection is on; wanted the frozenset of {sorted(DOCUMENT_MEDIA_TYPES)}"
    assert isinstance(media_types, frozenset) and media_types == DOCUMENT_MEDIA_TYPES, f"H-45: {SECURITY_MODULE}.{DOCUMENT_MEDIA_TYPES_NAME} is {media_types!r}, not the frozenset of these five str, {sorted(DOCUMENT_MEDIA_TYPES)}: HTML, XHTML, SVG, XML, lower-case"
    assert suffix is not None, f"H-45: {SECURITY_MODULE} has no {DOCUMENT_MEDIA_TYPE_SUFFIX_NAME}, the suffix making any other media type a document (application/atom+xml, application/rss+xml...); wanted {DOCUMENT_MEDIA_TYPE_SUFFIX!r}"
    assert suffix == DOCUMENT_MEDIA_TYPE_SUFFIX, f"H-45: {SECURITY_MODULE}.{DOCUMENT_MEDIA_TYPE_SUFFIX_NAME} is {suffix!r}, not the str {DOCUMENT_MEDIA_TYPE_SUFFIX!r}: the structured-syntax suffix of XML"
    print_success(f"✓ {DOCUMENT_MEDIA_TYPES_NAME} = {sorted(DOCUMENT_MEDIA_TYPES)}; {DOCUMENT_MEDIA_TYPE_SUFFIX_NAME} = {DOCUMENT_MEDIA_TYPE_SUFFIX!r}")


#: H-45: at paths of the web app (outside /mkdocs and /api/), where an HTML page carries the report-only policy when it is
#: on: two documents that are not HTML, and a type only starting like HTML's. None of them carries the report-only policy.
NOT_TEXT_HTML_AT_WEB_APP_PATHS: dict[str, TypedAnswer] = {
    "image-svg-xml": TypedAnswer("/favicon.svg", "image/svg+xml", LOGO_SVG, document=True),
    "application-xhtml-xml": TypedAnswer("/page.xhtml", "application/xhtml+xml", XHTML_PAGE, document=True),
    "text-htmlx": TypedAnswer("/page.htmlx", "text/htmlx", PAGE_HTML, document=False),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", NOT_TEXT_HTML_AT_WEB_APP_PATHS.values(), ids=list(NOT_TEXT_HTML_AT_WEB_APP_PATHS))
@pytest.mark.parametrize("mode", REPORT_ONLY_MODES.values(), ids=list(REPORT_ONLY_MODES))
async def test_the_report_only_policy_stays_on_text_html_not_on_every_document(mode: Mode, typed: TypedAnswer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-45: the report-only policy, written for the web app's pages, stays on a media type exactly text/html: at a path of
    the web app an SVG or an XHTML document carries PAGE_POLICY (frame protection on), never the report-only policy."""
    what = f"GET {typed.path} answered {typed.content_type} with {mode.describe()}"
    print_section(f"H-45 report-only policy, on text/html only: {what}")
    configure(monkeypatch, mode, tmp_path)
    page_there = TypedAnswer(typed.path, "text/html; charset=utf-8", PAGE_HTML, document=True)
    page_what = f"GET {typed.path} answered {page_there.content_type} with {mode.describe()}"

    page = await call(wrap(answering(page_there)), typed.path)  # the barrier: an HTML page at the same path carries it

    assert_bare_answer(page, page_there, page_what)
    page_report_only = page.values("content-security-policy-report-only")
    assert is_the_middlewares("content-security-policy-report-only", page_report_only), f"barrier: {page_what}: Content-Security-Policy-Report-Only is {page_report_only}, not the middleware's, once: the policy is on, the path the web app's, so an absence below is the type's doing"

    reply = await call(wrap(answering(typed)), typed.path)

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    report_only = reply.values("content-security-policy-report-only")
    kind = "a document, yet not HTML" if typed.document else "no document, the media type exactly and never a prefix"
    assert report_only == [], f"{what}: Content-Security-Policy-Report-Only is {report_only}, wanted none: H-45 leaves the report-only policy on a media type exactly text/html, and {typed.content_type!r} is {kind}"
    print_success(f"✓ no Content-Security-Policy-Report-Only; {assert_frame_protection(reply, mode.frame_protection, typed.document, what)}")


# =============================================================================
# (i) H-45: NO POLICY ON A 304
# =============================================================================

#: The two policies of D5: a 304 gets neither from the middleware (H-45), and keeps the one its route set.
POLICY_HEADERS = ("content-security-policy", "content-security-policy-report-only")


@dataclass(frozen=True)
class Revalidated:
    """What a bare ASGI app answers at ``path``, revalidated or not: ``headers`` as written, the same on its 200 and on its
    304, an ``etag`` among them; ``body`` on the 200 only. As a 200 it is a ``document`` (its policy ``PAGE_POLICY`` with
    frame protection on) or not, and ``web_app_html`` (an HTML page of the web app: the report-only policy's place) or not."""

    path: str
    headers: tuple[tuple[str, str], ...]
    body: bytes
    document: bool
    web_app_html: bool

    @property
    def etag(self) -> str:
        return dict(self.headers)["etag"]

    def own(self, name: str) -> list[str]:
        """What the route itself wrote for the header ``name``: kept as written, on the 200 and on the 304 alike."""
        return [value for key, value in self.headers if key == name]


#: Each at a path of the web app, where an HTML page carries every header of D5 that is on.
REVALIDATED: dict[str, Revalidated] = {
    # The 304 of the /_app mount today, Starlette's NotModifiedResponse: an ETag and a Cache-Control, no Content-Type
    "304-without-content-type": Revalidated("/_app/immutable/chunks/a1b2.js", (("etag", '"a1b2"'), ("cache-control", static_site.IMMUTABLE_CACHE_CONTROL)), CHUNK_JS, document=False, web_app_html=False),
    # An HTML page's 304 with its Content-Type, as a FileResponse answering conditional requests could send it
    "304-of-an-html-page": Revalidated("/", (("content-type", "text/html; charset=utf-8"), ("etag", '"index"'), ("cache-control", static_site.REVALIDATE_HTML["Cache-Control"])), INDEX_HTML, document=True, web_app_html=True),
    # An HTML page whose route set a policy itself, on its 304 too
    "304-with-the-routes-own-csp": Revalidated("/sets-csp", (("content-type", "text/html; charset=utf-8"), ("etag", '"page"'), ("content-security-policy", ROUTE_CSP)), PAGE_HTML, document=True, web_app_html=True),
    "304-with-the-routes-own-csp-report-only": Revalidated("/sets-csp-report-only", (("content-type", "text/html; charset=utf-8"), ("etag", '"page"'), ("content-security-policy-report-only", ROUTE_CSP_REPORT_ONLY)), PAGE_HTML, document=True, web_app_html=True),
}


def revalidating(revalidated: Revalidated) -> Callable:
    """A bare ASGI app answering ``revalidated``, its headers as written: a 304 without a body to a request carrying
    ``If-None-Match`` (a browser revalidating its copy), a 200 with the body to any other."""

    async def app(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        conditional = any(name == b"if-none-match" for name, _ in scope["headers"])
        headers = [(name.encode("latin-1"), value.encode("latin-1")) for name, value in revalidated.headers]
        await send({"type": "http.response.start", "status": 304 if conditional else 200, "headers": headers})
        await send({"type": "http.response.body", "body": b"" if conditional else revalidated.body})

    return app


def assert_the_200_carries_what_the_configuration_gives(reply: Reply, revalidated: Revalidated, mode: Mode, what: str) -> None:
    """Barrier: ``revalidated`` answered 200 carries the policies ``mode`` gives it: the route's own, else the policy of its
    type with frame protection on, and the middleware's report-only policy on an HTML page of the web app with it on."""
    by_type = [PAGE_POLICY if revalidated.document else FRAME_POLICY] if mode.frame_protection else []
    enforced = revalidated.own("content-security-policy") or by_type
    assert reply.values("content-security-policy") == enforced, f"barrier: {what}: Content-Security-Policy is {reply.values('content-security-policy')}, not {enforced}, what this configuration gives this answer: the 304 would test the harness, not the guard"
    own_report_only, report_only = revalidated.own("content-security-policy-report-only"), reply.values("content-security-policy-report-only")
    if mode.csp_report_only and revalidated.web_app_html and not own_report_only:
        assert is_the_middlewares("content-security-policy-report-only", report_only), f"barrier: {what}: Content-Security-Policy-Report-Only is {report_only}, not the middleware's, once, what this configuration gives an HTML page of the web app"
    else:
        assert report_only == own_report_only, f"barrier: {what}: Content-Security-Policy-Report-Only is {report_only}, not {own_report_only}, what this configuration gives this answer"


@pytest.mark.asyncio
@pytest.mark.parametrize("revalidated", REVALIDATED.values(), ids=list(REVALIDATED))
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_a_304_gets_no_policy_from_the_middleware(mode: Mode, revalidated: Revalidated, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-45: a browser freshens its cached response with the header fields of a 304, so a policy on a 304 would replace the
    cached page's PAGE_POLICY: the middleware adds neither policy to a 304, in every configuration; the rest as ever."""
    what = f"GET {revalidated.path} with If-None-Match: {revalidated.etag}, answered 304 with {list(revalidated.headers)}, with {mode.describe()}"
    print_section(f"H-45 no policy on a 304: {what}")
    configure(monkeypatch, mode, tmp_path)
    middleware = wrap(revalidating(revalidated))  # SecurityHeadersMiddleware(app) built here, configuration in place
    fresh_what = f"GET {revalidated.path} answered 200 with the same headers, with {mode.describe()}"

    fresh = await call(middleware, revalidated.path)  # the barrier: the same answer as a 200

    assert fresh.raised is None and fresh.status == 200 and fresh.body == revalidated.body, f"barrier: {fresh_what}: not the bare app's 200: {fresh.status} {fresh.body[:120]!r}, raised {fresh.raised!r}"
    assert_always_on(fresh, fresh_what)
    assert_the_200_carries_what_the_configuration_gives(fresh, revalidated, mode, fresh_what)

    reply = await call(middleware, revalidated.path, headers=(("If-None-Match", revalidated.etag),))

    assert reply.raised is None and reply.status == 304 and reply.body == b"", f"barrier: {what}: not the bare app's 304: {reply.status} {reply.body[:120]!r}, raised {reply.raised!r}"
    written = {name: [value] for name, value in revalidated.headers if name not in D5_HEADERS}
    assert {name: reply.values(name) for name in written} == written, f"barrier: {what}: the route's headers reached the client as {reply.headers}, not as written, {written}"
    assert_always_on(reply, what)
    for name in POLICY_HEADERS:
        own = revalidated.own(name)
        why = "the route's own, kept as written, alone" if own else "the middleware adds no policy to a 304"
        assert reply.values(name) == own, f"{what}: {name} is {reply.values(name)}, wanted {own}, {why}; H-45: a browser freshens its cached response with the header fields of a 304 (RFC 9111, 3.2), so a policy on a 304 replaces the cached page's PAGE_POLICY"
    frame_options = [FRAME_OPTIONS] if mode.frame_protection else []
    assert reply.values("x-frame-options") == frame_options, f"{what}: X-Frame-Options is {reply.values('x-frame-options')}, wanted {frame_options}: frame protection is {'on' if mode.frame_protection else 'off'}, and a 304 gets X-Frame-Options as any answer does"
    print_success(f"✓ the policies {[reply.values(name) for name in POLICY_HEADERS]}; X-Frame-Options {frame_options}; nosniff and Referrer-Policy")


@dataclass(frozen=True)
class MountedFile:
    """A file of the fake build under ``/_app``, served by the mount: its URL, its media types, its content, and whether it
    is a document (H-45: an SVG image is, a JavaScript chunk is not)."""

    path: str
    media_types: tuple[str, ...]
    body: bytes
    document: bool


MOUNTED_FILES: dict[str, MountedFile] = {
    "javascript-chunk": MountedFile("/_app/immutable/chunks/a1b2.js", JAVASCRIPT, CHUNK_JS, document=False),
    "svg-image": MountedFile(LOGO_SVG_PATH, SVG, LOGO_SVG, document=True),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("mounted", MOUNTED_FILES.values(), ids=list(MOUNTED_FILES))
async def test_the_real_304_of_the_app_mount_carries_no_policy(mounted: MountedFile, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-45, through the stack in managed: the /_app mount (ImmutableStaticFiles, the one part of the app answering 304)
    revalidates a file of the build; its 200 carries the policy of its type (PAGE_POLICY on the SVG, a document), its 304 none."""
    mode = MODES["managed"]
    what = f"GET {mounted.path} with {mode.describe()}"
    print_section(f"H-45 a real 304 through the stack: {what}, then again with its ETag")
    configure(monkeypatch, mode, tmp_path)
    app = site_app(tmp_path, monkeypatch)

    first = await call(app, mounted.path)

    answered(200, mounted.media_types, mounted.body)(first)
    assert_always_on(first, what)
    etags = first.values("etag")
    assert len(etags) == 1, f"barrier: {what} came with the ETags {etags}, not one: nothing to revalidate with"
    again_what = f"{what} and If-None-Match: {etags[0]}"

    again = await call(app, mounted.path, headers=(("If-None-Match", etags[0]),))

    assert again.raised is None and again.status == 304 and again.body == b"", f"barrier: {again_what} answered {again.status} {again.body[:120]!r}, raised {again.raised!r}, not 304: the revalidation path was not taken"
    assert again.values("etag") == etags and again.values("cache-control") == [static_site.IMMUTABLE_CACHE_CONTROL], f"barrier: {again_what}: not the 304 of ImmutableStaticFiles, with its ETag and the Cache-Control the mount gives a file of immutable/: {again.headers}"
    assert_always_on(again, again_what)
    enforced = assert_frame_protection(first, mode.frame_protection, mounted.document, what)
    assert first.values("content-security-policy-report-only") == [], f"{what}: Content-Security-Policy-Report-Only is {first.values('content-security-policy-report-only')}, wanted none: {first.media_type!r} is not the web app's HTML"
    for name in POLICY_HEADERS:
        assert again.values(name) == [], f"{again_what}: {name} is {again.values(name)}, wanted none; H-45: the browser freshens its cached copy, whose policy is {first.values('content-security-policy')}, with the header fields of this 304 (RFC 9111, 3.2)"
    assert again.values("x-frame-options") == [FRAME_OPTIONS], f"{again_what}: X-Frame-Options is {again.values('x-frame-options')}, wanted exactly one, {FRAME_OPTIONS!r}: frame protection is on, and a 304 gets it as any answer does"
    print_success(f"✓ the 200: {enforced}; its 304, {again.values('content-type') or 'without Content-Type'}: X-Frame-Options and no policy")
