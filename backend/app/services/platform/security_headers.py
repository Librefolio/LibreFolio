"""Security headers on every HTTP response: decision D5, and the Content-Security-Policy always enforced (H-55 v2).

Owner: workstream H (platform), CP7b-1 and CP7b-2. ``SecurityHeadersMiddleware`` is an entry of ``MIDDLEWARE_STACK``,
outside GZip, and adds to every HTTP response:

- ``X-Content-Type-Options: nosniff``: a browser uses the type the server sends and never guesses one, so an upload
  is never run as a script or a page, and a script or a style sheet sent with another type is refused.
  ``register_served_types()`` gives the app the right type for every file it serves, so nothing the web app or the
  documentation loads goes out as ``application/octet-stream``;
- ``Referrer-Policy: strict-origin-when-cross-origin``: another site learns at most the origin, never a page's path
  or query.

The Content-Security-Policy is enforced in every profile, directive by directive, without a switch (decision of the
developer, 19/10: on by default, a mesh widened only where it is truly needed). One ``Content-Security-Policy`` field per
response:

- a **document** (``DOCUMENT_MEDIA_TYPES``, or a type ending with ``+xml``, H-45: the web app's pages, the
  documentation, the API's Swagger UI and ReDoc, an XHTML, SVG or XML file opened directly) gets
  ``DOCUMENT_DIRECTIVES``, three directives that touch no script (H-42): ``object-src 'none'``, ``base-uri 'self'`` and
  ``form-action 'self'``, against plugin content, an injected ``<base>`` and a form sent to another site. Not a PDF:
  Chromium shows an inline PDF with a viewer it treats as a plugin, which ``object-src 'none'`` on the PDF's own answer
  could stop;
- a **page of the web app** (``text/html`` exactly, never ``/mkdocs`` or ``/api/``) gets in addition
  ``script-src 'self' 'wasm-unsafe-eval' 'report-sample'`` with the hashes of the build's inline scripts,
  ``worker-src 'self' blob:`` (the PDF viewer's workers) and ``connect-src 'self'`` with the origin of
  ``LIBREFOLIO_PUBLIC_URL`` and, self-hosted, ``https://api.github.com`` (the update check, run in the administrator's
  browser). A script the app did not send (a proxy's, a CDN's, an extension's) is blocked; the page reports it in the
  console and in the Security tab (``app.html``, ``lib/features/security/cspNotice.ts``);
- the API's **documentation pages** (debug instances only) get ``api_docs_policy()``: scripts of the instance and of the
  pinned jsDelivr files they load with Subresource Integrity (R5);
- a **script of the build** (JavaScript under ``/_app/``) gets ``worker_policy()``: a browser applies it only to a worker
  started from that script (R4): the build's own modules, ``connect-src`` like the pages, nothing from elsewhere;
- with ``LIBREFOLIO_FRAME_PROTECTION`` (on in the managed profile), every response also gets ``frame-ancestors 'self'``
  and ``X-Frame-Options: SAMEORIGIN``: only the app's own pages may frame it. Off, framing stays free: embedding the app
  (a Home Assistant panel) is a legitimate self-hosted use.

No ``default-src`` and no ``style-src``, ``img-src``, ``font-src`` or ``frame-src`` are enforced: styles, images (asset
icons set by URL), fonts and frames stay free. ``LIBREFOLIO_CSP_REPORT_ONLY`` (on in the managed profile) adds, on the
web app's pages, ``Content-Security-Policy-Report-Only: CSP_REPORT_ONLY_POLICY``, the whole policy the app aims at,
with the same hashes and ``connect-src`` sources: nothing more is blocked, the browser reports each violation in its
console (no report endpoint).

The hashes follow the build (``_BuildScriptHashes``): each page of the web app ``stat``s the build's pages, and reads
them again only when their signature (name, ``st_mtime_ns``, ``st_size``) changed, so a build made while the server runs
is served with its own hashes. A page missing from the last good signature (a build being written) keeps the last good
hashes until it is back.

A ``304`` gets no policy (H-45). A browser freshens the response it cached with the header fields of a 304, and a 304
has no ``Content-Type`` (Starlette's ``NotModifiedResponse``): a policy on it would replace the cached document's,
which Chromium 149 does. Only ``StaticFiles`` (``/_app``) answers 304 today; ``FileResponse`` (the pages, the
documentation) never does.

A header a route already set is kept. Starlette sends its own 500 from ``ServerErrorMiddleware``, outside every
middleware of the stack: when a request fails before its answer started, this middleware sends the 500 itself, with
the headers, then lets the exception go on, so it is still logged.
"""

import asyncio
import mimetypes
import threading
from collections.abc import Iterable
from pathlib import Path

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.api.api_docs import DOCS_PATH, LIBRARY_ORIGIN, REDOC_PATH
from backend.app.config import get_settings
from backend.app.config.accounts import public_url
from backend.app.logging_config import get_logger
from backend.app.services.platform.failure_report import error_body, report_unhandled_error
from backend.app.services.platform.request_id import request_id_of
from backend.app.utils.runtime.origins import canonical_origin

logger = get_logger(__name__)

#: Added to every HTTP response that does not carry them already.
ALWAYS_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
)

_CSP_FIELD = b"content-security-policy"
_CSP_REPORT_ONLY_FIELD = b"content-security-policy-report-only"
_X_FRAME_OPTIONS = (b"x-frame-options", b"SAMEORIGIN")

#: Enforced on every response when frame protection is on: only the app's own pages may frame it.
FRAME_ANCESTORS = "frame-ancestors 'self'"
#: Enforced on every document, in every profile (H-42, H-55 v2): three directives that touch no script.
DOCUMENT_DIRECTIVES: tuple[str, ...] = ("object-src 'none'", "base-uri 'self'", "form-action 'self'")
#: The enforced policy of a document when frame protection is on.
PAGE_POLICY = "; ".join((FRAME_ANCESTORS, *DOCUMENT_DIRECTIVES))
#: The ``script-src`` of a page of the web app, before the hashes of the build's inline scripts. WebAssembly compiles for
#: the PDF viewer; ``'report-sample'`` puts the first 40 characters of a blocked script or eval in the page's own
#: violation event (no report endpoint: if one is ever added, those characters leave the browser with the report).
WEB_APP_SCRIPT_SRC = "script-src 'self' 'wasm-unsafe-eval' 'report-sample'"
#: Without it the workers follow ``script-src``, which has no ``blob:``, and the PDF viewer's workers are blocked.
WEB_APP_WORKER_SRC = "worker-src 'self' blob:"
#: Where the self-hosted administrator's browser asks for the latest release (the update check).
GITHUB_API_ORIGIN = "https://api.github.com"
SELF_HOSTED_PROFILE = "selfhosted"

#: The media types of a document (H-45); a type ending with ``DOCUMENT_MEDIA_TYPE_SUFFIX`` is one too
#: (``application/atom+xml``, ``application/rss+xml``). A PDF is not.
DOCUMENT_MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml", "image/svg+xml", "application/xml", "text/xml"})
DOCUMENT_MEDIA_TYPE_SUFFIX = "+xml"

#: The report-only policy of the web app's pages: the whole policy the app aims at. Images may come from any HTTPS
#: address (asset and broker icons set by URL); the inline styles of the app are allowed, its inline scripts only by
#: their hashes, which ``report_only_policy()`` adds (H-52), with the ``connect-src`` sources of the enforced policy.
CSP_REPORT_ONLY_POLICY = "; ".join(
    (
        "default-src 'self'",
        WEB_APP_SCRIPT_SRC,
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https:",
        "font-src 'self' data:",
        "connect-src 'self'",
        WEB_APP_WORKER_SRC,
        "frame-src 'self' blob:",
        *DOCUMENT_DIRECTIVES,
        FRAME_ANCESTORS,
    )
)


def _with_sources(directives: Iterable[str], extra: dict[str, Iterable[str]]) -> str:
    """``directives`` joined, each one named in ``extra`` (by its name, its first word) followed by those sources."""
    joined = []
    for directive in directives:
        sources = " ".join(extra.get(directive.split(" ", 1)[0], ()))
        joined.append(f"{directive} {sources}" if sources else directive)
    return "; ".join(joined)


def report_only_policy(script_hashes: Iterable[str], connect_sources: Iterable[str] = ()) -> str:
    """``CSP_REPORT_ONLY_POLICY`` with ``script_hashes`` (``'sha256-…'``) appended to its ``script-src`` and
    ``connect_sources`` to its ``connect-src``, in the order given."""
    return _with_sources(CSP_REPORT_ONLY_POLICY.split("; "), {"script-src": tuple(script_hashes), "connect-src": tuple(connect_sources)})


def web_app_policy(script_hashes: Iterable[str], connect_sources: Iterable[str], frame_protection: bool) -> str:
    """The enforced policy of a page of the web app: the document's directives, ``script-src`` with the hashes,
    ``worker-src`` and ``connect-src`` with ``connect_sources``; ``frame-ancestors`` first when frame protection is on."""
    directives = ((FRAME_ANCESTORS,) if frame_protection else ()) + DOCUMENT_DIRECTIVES + (WEB_APP_SCRIPT_SRC, WEB_APP_WORKER_SRC, "connect-src 'self'")
    return _with_sources(directives, {"script-src": tuple(script_hashes), "connect-src": tuple(connect_sources)})


#: The API's documentation pages (H-55 R5, ``api/api_docs.py``: debug instances only), whose policy is ``api_docs_policy()``.
API_DOCS_PAGES = frozenset({DOCS_PATH, REDOC_PATH})


def api_docs_policy(frame_protection: bool) -> str:
    """The enforced policy of the API's documentation pages: the document's directives, and scripts only of the instance
    and of the pinned files of jsDelivr the pages load with their integrity hashes (``api_docs.LIBRARIES``); ReDoc's
    search worker from a blob; the OpenAPI document from the instance."""
    directives = ((FRAME_ANCESTORS,) if frame_protection else ()) + DOCUMENT_DIRECTIVES + (f"script-src 'self' {LIBRARY_ORIGIN}", WEB_APP_WORKER_SRC, "connect-src 'self'")
    return "; ".join(directives)


#: The media types of a script: under ``/_app/`` one gets ``worker_policy()`` (R4).
SCRIPT_MEDIA_TYPES = frozenset({"text/javascript", "application/javascript"})
#: Where the build's scripts are served (the StaticFiles mount of the web app).
APP_ASSETS_PREFIX = "/_app/"


def worker_policy(connect_sources: Iterable[str], frame_protection: bool) -> str:
    """The enforced policy of a script of the web app's build, for when a browser runs it as a worker (R4).

    A browser applies a script response's policy only to a worker it starts from that script (``priceProcessing.worker``
    today); on any other script it is ignored. The worker may load the build's own modules and nothing else, connect
    where the pages connect, and start workers of its own from the build or a blob. The PDF engine's worker starts from a
    blob and keeps the page's policy.
    """
    directives = ((FRAME_ANCESTORS,) if frame_protection else ()) + ("script-src 'self'", "connect-src 'self'", WEB_APP_WORKER_SRC, "object-src 'none'", "base-uri 'self'")
    return _with_sources(directives, {"connect-src": tuple(connect_sources)})


def connect_sources(profile: str) -> tuple[str, ...]:
    """The sources a page of the web app may connect to beyond its own origin: the origin of ``LIBREFOLIO_PUBLIC_URL``
    (the address users reach the instance at, when the page was opened at another one: the design approved on 19/10;
    the address check no longer needs it, being an image, an open question for the developer) and, self-hosted, the
    GitHub API of the update check.

    A ``LIBREFOLIO_PUBLIC_URL`` that cannot be used adds nothing: it is logged here, and the server keeps serving.
    """
    sources: list[str] = []
    try:
        origin = canonical_origin(public_url())
    except ValueError as exc:
        logger.warning("LIBREFOLIO_PUBLIC_URL cannot be used: the Content-Security-Policy's connect-src gets no origin of it", error=str(exc))
        origin = None
    if origin:
        sources.append(origin)
    if profile == SELF_HOSTED_PROFILE:
        sources.append(GITHUB_API_ORIGIN)
    return tuple(sources)


def _build_signature(build_dir: Path) -> tuple[tuple[str, int, int], ...]:
    """The signature of the build's pages: ``(name, st_mtime_ns, st_size)`` of every ``*.html`` directly in
    ``build_dir`` whose name does not start with ``.``, sorted; a page that vanishes between the listing and its
    ``stat`` is left out. ``()`` without a build."""
    if not build_dir.is_dir():
        return ()
    signature = []
    for page in build_dir.glob("*.html"):
        if page.name.startswith("."):
            continue
        try:
            status = page.stat()
        except OSError:
            continue
        signature.append((page.name, status.st_mtime_ns, status.st_size))
    return tuple(sorted(signature))


class _BuildScriptHashes:
    """The hashes of the build's inline scripts, read again only when the build's pages change (H-55 v2)."""

    def __init__(self) -> None:
        self._signature: tuple[tuple[str, int, int], ...] | None = None
        self._hashes: tuple[str, ...] = ()
        # current() runs in worker threads (the middleware never reads the build on the event loop): one read at a time
        self._lock = threading.Lock()

    def current(self) -> tuple[str, ...]:
        """The hashes of the build as it is now; the last good ones while a page of the last good build is missing.

        Blocking file I/O: called through ``asyncio.to_thread``. Thread-safe: concurrent callers read a changed build once.
        """
        with self._lock:
            return self._current()

    def _current(self) -> tuple[str, ...]:
        from backend.app.services.platform import static_site  # noqa: PLC0415 — static_site imports this module

        build_dir = static_site.FRONTEND_BUILD_DIR
        signature = _build_signature(build_dir)
        if signature == self._signature:
            return self._hashes
        if self._signature and not {name for name, _, _ in self._signature} <= {name for name, _, _ in signature}:
            # A page of the last good build is missing: a build is being written. Checked again at the next page
            return self._hashes
        self._hashes = static_site.spa_inline_script_hashes(build_dir)
        self._signature = signature
        return self._hashes


#: The types of the files the app serves (the web app, the documentation, the plugins' assets). Python's own table
#: lacks the fonts and source maps, which without ``/etc/mime.types`` (a slim image) would go out as
#: ``application/octet-stream``; the others are named here so that a system table naming them differently cannot
#: change the type of a script or a style sheet, which ``nosniff`` makes a browser refuse.
SERVED_TYPES: tuple[tuple[str, str], ...] = (
    ("text/javascript", ".js"),
    ("text/javascript", ".mjs"),
    ("text/css", ".css"),
    ("application/json", ".json"),
    ("application/json", ".map"),
    ("application/manifest+json", ".webmanifest"),
    ("application/wasm", ".wasm"),
    ("image/svg+xml", ".svg"),
    ("font/woff", ".woff"),
    ("font/woff2", ".woff2"),
    ("font/ttf", ".ttf"),
    ("font/otf", ".otf"),
    ("application/vnd.ms-fontobject", ".eot"),
)


def register_served_types() -> None:
    """Make ``mimetypes`` (read by ``StaticFiles`` and ``FileResponse``) name every type in ``SERVED_TYPES``."""
    for mime_type, extension in SERVED_TYPES:
        mimetypes.add_type(mime_type, extension)


def _media_type(headers: list[tuple[bytes, bytes]]) -> str:
    """The media type of a response: its first ``content-type`` without parameters, stripped, lowercase; ``""`` without one."""
    content_type = next((value for name, value in headers if name.lower() == b"content-type"), b"")
    return content_type.split(b";", 1)[0].strip().lower().decode("latin-1")


def _is_document(headers: list[tuple[bytes, bytes]]) -> bool:
    """A document, whose enforced policy holds ``DOCUMENT_DIRECTIVES``: an HTML, XHTML, SVG or XML type (H-45)."""
    media_type = _media_type(headers)
    return media_type in DOCUMENT_MEDIA_TYPES or media_type.endswith(DOCUMENT_MEDIA_TYPE_SUFFIX)


def _is_app_script(path: str, headers: list[tuple[bytes, bytes]]) -> bool:
    """A script of the web app's build: a JavaScript response under ``/_app/``."""
    return path.startswith(APP_ASSETS_PREFIX) and _media_type(headers) in SCRIPT_MEDIA_TYPES


def _is_web_app_page(path: str, headers: list[tuple[bytes, bytes]]) -> bool:
    """An HTML response of the web app (``text/html`` exactly): not the documentation (``/mkdocs``), not the API (``/api/``)."""
    if path == "/mkdocs" or path.startswith("/mkdocs/") or path == "/api" or path.startswith("/api/"):
        return False
    return _media_type(headers) == "text/html"


class SecurityHeadersMiddleware:
    """Add the security headers to every HTTP response, keeping the ones a route set; other scopes pass untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        # Read once: the settings cannot change while the app runs
        settings = get_settings()
        self.frame_protection = settings.LIBREFOLIO_FRAME_PROTECTION
        frame = (_X_FRAME_OPTIONS,) if self.frame_protection else ()
        self.headers = ALWAYS_HEADERS + frame + (((_CSP_FIELD, FRAME_ANCESTORS.encode()),) if self.frame_protection else ())
        self.document_headers = ALWAYS_HEADERS + frame + ((_CSP_FIELD, (PAGE_POLICY if self.frame_protection else "; ".join(DOCUMENT_DIRECTIVES)).encode()),)
        # A 304 carries no policy (H-45): the browser keeps the one of the response it cached
        self.not_modified_headers = ALWAYS_HEADERS + frame
        self.connect_sources = connect_sources(settings.LIBREFOLIO_PROFILE)
        self.api_docs_headers = ALWAYS_HEADERS + frame + ((_CSP_FIELD, api_docs_policy(self.frame_protection).encode()),)
        self.script_headers = ALWAYS_HEADERS + frame + ((_CSP_FIELD, worker_policy(self.connect_sources, self.frame_protection).encode()),)
        self.csp_report_only = settings.LIBREFOLIO_CSP_REPORT_ONLY
        self.script_hashes = _BuildScriptHashes()
        self._page_policies: tuple[tuple[str, ...], tuple[tuple[bytes, bytes], ...]] | None = None

    async def _script_hashes(self) -> tuple[str, ...]:
        """The hashes of the build as it is now, read off the event loop; none when the build cannot be read.

        Without hashes the app's inline scripts are blocked, never allowed: the page still gets every header (fail closed).
        """
        try:
            return await asyncio.to_thread(self.script_hashes.current)
        except Exception as exc:  # an isolation boundary: a page always gets its headers, whatever the build's state
            logger.warning("The build's inline scripts could not be hashed: the page's policy allows none of them", exc_info=exc)
            return ()

    def _web_app_policies(self, hashes: tuple[str, ...]) -> tuple[tuple[bytes, bytes], ...]:
        """The policy fields of a page of the web app for ``hashes``: rebuilt only when they change."""
        if self._page_policies is None or self._page_policies[0] != hashes:
            fields = [(_CSP_FIELD, web_app_policy(hashes, self.connect_sources, self.frame_protection).encode())]
            if self.csp_report_only:
                fields.append((_CSP_REPORT_ONLY_FIELD, report_only_policy(hashes, self.connect_sources).encode()))
            self._page_policies = (hashes, tuple(fields))
        return self._page_policies[1]

    async def _added(self, path: str, status: int, headers: list[tuple[bytes, bytes]]) -> tuple[tuple[bytes, bytes], ...]:
        """The headers a response of ``status`` and ``headers`` at ``path`` gets, before the ones it set are dropped."""
        if status == 304:
            return self.not_modified_headers
        if _is_web_app_page(path, headers):
            return ALWAYS_HEADERS + ((_X_FRAME_OPTIONS,) if self.frame_protection else ()) + self._web_app_policies(await self._script_hashes())
        if _is_app_script(path, headers):
            return self.script_headers
        if path in API_DOCS_PAGES and _media_type(headers) == "text/html":
            return self.api_docs_headers
        return self.document_headers if _is_document(headers) else self.headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = False

        async def send_with_headers(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                present = {name.lower() for name, _ in headers}
                headers.extend(header for header in await self._added(scope["path"], message["status"], headers) if header[0] not in present)
                message = {**message, "headers": headers}
                # Only once the headers are built: a failure before this point still gets the middleware's own 500
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception as exc:
            # Logged once, as JSON with the request id (H-60); uvicorn's own line for it is then dropped (logging_config.py)
            request_id = request_id_of(scope)
            error_type = report_unhandled_error(exc, method=scope.get("method"), path=scope.get("path"), request_id=request_id)
            if not started:
                await JSONResponse(error_body("Internal Server Error", request_id, error_type), status_code=500)(scope, receive, send_with_headers)
            raise
