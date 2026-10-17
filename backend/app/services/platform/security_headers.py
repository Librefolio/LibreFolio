"""Security headers on every HTTP response: decision D5.

Owner: workstream H (platform), CP7b-1 and CP7b-2. ``SecurityHeadersMiddleware`` is an entry of ``MIDDLEWARE_STACK``,
outside GZip, and adds to every HTTP response:

- ``X-Content-Type-Options: nosniff``: a browser uses the type the server sends and never guesses one, so an upload
  is never run as a script or a page, and a script or a style sheet sent with another type is refused.
  ``register_served_types()`` gives the app the right type for every file it serves, so nothing the web app or the
  documentation loads goes out as ``application/octet-stream``;
- ``Referrer-Policy: strict-origin-when-cross-origin``: another site learns at most the origin, never a page's path
  or query.

Two more, read from the settings when the middleware is built, off for a self-hosted install and on for a managed
one (``PROFILE_DEFAULTS``), each settable on its own:

- ``LIBREFOLIO_FRAME_PROTECTION``: ``X-Frame-Options: SAMEORIGIN`` and ``Content-Security-Policy: frame-ancestors
  'self'``, enforced, on every response: only the app's own pages may frame it. A document gets ``PAGE_POLICY``
  instead, which adds three directives that touch no script (H-42): ``object-src 'none'``, ``base-uri 'self'`` and
  ``form-action 'self'``, against plugin content, an injected ``<base>`` and a form sent to another site. A document is
  a response whose media type is in ``DOCUMENT_MEDIA_TYPES`` or ends with ``+xml`` (H-45): the web app's pages, the
  documentation, the API's Swagger UI and ReDoc, and an XHTML, SVG or XML file, a document too when opened directly.
  Not a PDF: Chromium shows an inline PDF with a viewer it treats as a plugin, which ``object-src 'none'`` on the PDF's
  own answer could stop;
- ``LIBREFOLIO_CSP_REPORT_ONLY``: ``Content-Security-Policy-Report-Only: CSP_REPORT_ONLY_POLICY`` on the HTML pages of
  the web app (``text/html`` exactly), never on ``/mkdocs`` or ``/api/``, with the hashes of the inline scripts of the
  build's pages in its ``script-src`` (H-52, ``report_only_policy()``), read once, when the middleware is built: a new
  build takes a restart. Nothing is blocked; the browser reports each violation in its console (no report endpoint).

A ``304`` gets neither policy (H-45). A browser freshens the response it cached with the header fields of a 304, and
a 304 has no ``Content-Type`` (Starlette's ``NotModifiedResponse``): ``frame-ancestors 'self'`` alone on it would
replace the cached document's ``PAGE_POLICY``, which Chromium 149 does. Without a policy on the 304 the cached one
stays. Only ``StaticFiles`` (``/_app``) answers 304 today; ``FileResponse`` (the pages, the documentation) never does.

A header a route already set is kept. Starlette sends its own 500 from ``ServerErrorMiddleware``, outside every
middleware of the stack: when a request fails before its answer started, this middleware sends the 500 itself, with
the headers, then lets the exception go on, so it is still logged.
"""

import mimetypes
from collections.abc import Iterable

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.app.config import get_settings

#: Added to every HTTP response that does not carry them already.
ALWAYS_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
)

#: Added to every response when frame protection is on: only the app's own pages may frame it (enforced).
FRAME_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-frame-options", b"SAMEORIGIN"),
    (b"content-security-policy", b"frame-ancestors 'self'"),
)

#: The enforced policy of an HTML response when frame protection is on (H-42): ``frame-ancestors`` and three directives
#: that touch no script. ``script-src`` and the rest stay in the report-only policy below.
PAGE_POLICY = "; ".join(("frame-ancestors 'self'", "object-src 'none'", "base-uri 'self'", "form-action 'self'"))
#: ``FRAME_HEADERS`` for a document.
PAGE_FRAME_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-frame-options", b"SAMEORIGIN"),
    (b"content-security-policy", PAGE_POLICY.encode()),
)

#: The media types of a document, whose enforced policy is ``PAGE_POLICY`` (H-45); a type ending with
#: ``DOCUMENT_MEDIA_TYPE_SUFFIX`` is one too (``application/atom+xml``, ``application/rss+xml``). A PDF is not.
DOCUMENT_MEDIA_TYPES = frozenset({"text/html", "application/xhtml+xml", "image/svg+xml", "application/xml", "text/xml"})
DOCUMENT_MEDIA_TYPE_SUFFIX = "+xml"

#: The report-only policy of the web app's pages. Images may come from any HTTPS address (asset and broker icons set
#: by URL); WebAssembly compiles for the PDF viewer; the inline styles of the app are allowed, its inline scripts only by
#: their hashes, which ``report_only_policy()`` adds (H-52). ``'report-sample'`` puts the first 40 characters of a
#: blocked script or eval in its report: the page's own event today, since the policy names no report endpoint; if one
#: is ever added, those characters leave the browser with the report.
CSP_REPORT_ONLY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self' 'wasm-unsafe-eval' 'report-sample'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "frame-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'self'",
    )
)
_CSP_REPORT_ONLY_FIELD = b"content-security-policy-report-only"


def report_only_policy(script_hashes: Iterable[str]) -> str:
    """``CSP_REPORT_ONLY_POLICY`` with ``script_hashes`` (``'sha256-…'``) appended to its ``script-src``, in the order given."""
    hashes = " ".join(script_hashes)
    if not hashes:
        return CSP_REPORT_ONLY_POLICY
    return "; ".join(f"{directive} {hashes}" if directive.startswith("script-src ") else directive for directive in CSP_REPORT_ONLY_POLICY.split("; "))


def _report_only_header() -> tuple[bytes, bytes]:
    """The report-only header of the web app's pages, with the hashes of the build's inline scripts read now (H-52)."""
    from backend.app.services.platform import static_site  # noqa: PLC0415 — static_site imports this module

    return (_CSP_REPORT_ONLY_FIELD, report_only_policy(static_site.spa_inline_script_hashes(static_site.FRONTEND_BUILD_DIR)).encode())


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
    """A document, whose enforced policy is ``PAGE_POLICY``: an HTML, XHTML, SVG or XML type (H-45)."""
    media_type = _media_type(headers)
    return media_type in DOCUMENT_MEDIA_TYPES or media_type.endswith(DOCUMENT_MEDIA_TYPE_SUFFIX)


def _is_html(headers: list[tuple[bytes, bytes]]) -> bool:
    """An HTML page: the media type is exactly ``text/html``."""
    return _media_type(headers) == "text/html"


def _is_web_app_page(path: str, headers: list[tuple[bytes, bytes]]) -> bool:
    """An HTML response of the web app: not the documentation (``/mkdocs``), not the API (``/api/``)."""
    if path == "/mkdocs" or path.startswith("/mkdocs/") or path == "/api" or path.startswith("/api/"):
        return False
    return _is_html(headers)


class SecurityHeadersMiddleware:
    """Add the security headers to every HTTP response, keeping the ones a route set; other scopes pass untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        # Read once: the switches cannot change while the app runs
        settings = get_settings()
        self.headers = ALWAYS_HEADERS + (FRAME_HEADERS if settings.LIBREFOLIO_FRAME_PROTECTION else ())
        self.page_headers = ALWAYS_HEADERS + (PAGE_FRAME_HEADERS if settings.LIBREFOLIO_FRAME_PROTECTION else ())
        # A 304 carries no policy (H-45): the browser keeps the one of the response it cached
        self.not_modified_headers = tuple(header for header in self.headers if header[0] != b"content-security-policy")
        self.csp_report_only = settings.LIBREFOLIO_CSP_REPORT_ONLY
        # With the hashes of the build's inline scripts, read once (H-52): never a read of the build per request
        self.csp_report_only_header = _report_only_header() if self.csp_report_only else None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = False

        async def send_with_headers(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                headers = list(message.get("headers") or [])
                present = {name.lower() for name, _ in headers}
                not_modified = message["status"] == 304
                if not_modified:
                    added = self.not_modified_headers
                else:
                    added = self.page_headers if _is_document(headers) else self.headers
                headers.extend(header for header in added if header[0] not in present)
                if self.csp_report_only_header and not not_modified and _CSP_REPORT_ONLY_FIELD not in present and _is_web_app_page(scope["path"], headers):
                    headers.append(self.csp_report_only_header)
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            if not started:
                await PlainTextResponse("Internal Server Error", status_code=500)(scope, receive, send_with_headers)
            raise
