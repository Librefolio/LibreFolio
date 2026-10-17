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
  'self'``, enforced, on every response: only the app's own pages may frame it. An HTML response (the web app's pages,
  the documentation, the API's Swagger UI and ReDoc) gets ``PAGE_POLICY`` instead, which adds three directives that
  touch no script (H-42): ``object-src 'none'``, ``base-uri 'self'`` and ``form-action 'self'``, against plugin content,
  an injected ``<base>`` and a form sent to another site. Only HTML: Chromium shows an inline PDF with a viewer it
  treats as a plugin, which ``object-src 'none'`` on the PDF's own answer could stop;
- ``LIBREFOLIO_CSP_REPORT_ONLY``: ``Content-Security-Policy-Report-Only: CSP_REPORT_ONLY_POLICY`` on the HTML pages of
  the web app, never on ``/mkdocs`` or ``/api/``. Nothing is blocked; the browser reports each violation in its
  console (no report endpoint).

A header a route already set is kept. Starlette sends its own 500 from ``ServerErrorMiddleware``, outside every
middleware of the stack: when a request fails before its answer started, this middleware sends the 500 itself, with
the headers, then lets the exception go on, so it is still logged.
"""

import mimetypes

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
#: ``FRAME_HEADERS`` for an HTML response.
PAGE_FRAME_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-frame-options", b"SAMEORIGIN"),
    (b"content-security-policy", PAGE_POLICY.encode()),
)

#: The report-only policy of the web app's pages. Images may come from any HTTPS address (asset and broker icons set
#: by URL); WebAssembly compiles for the PDF viewer; the inline styles of the app are allowed, its inline scripts not.
CSP_REPORT_ONLY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self' 'wasm-unsafe-eval'",
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
_CSP_REPORT_ONLY_HEADER = (b"content-security-policy-report-only", CSP_REPORT_ONLY_POLICY.encode())

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


def _is_html(headers: list[tuple[bytes, bytes]]) -> bool:
    """Whether a response is an HTML document, by its ``content-type``."""
    content_type = next((value for name, value in headers if name.lower() == b"content-type"), b"")
    return content_type.lower().startswith(b"text/html")


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
        self.csp_report_only = settings.LIBREFOLIO_CSP_REPORT_ONLY

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
                added = self.page_headers if _is_html(headers) else self.headers
                headers.extend(header for header in added if header[0] not in present)
                if self.csp_report_only and _CSP_REPORT_ONLY_HEADER[0] not in present and _is_web_app_page(scope["path"], headers):
                    headers.append(_CSP_REPORT_ONLY_HEADER)
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            if not started:
                await PlainTextResponse("Internal Server Error", status_code=500)(scope, receive, send_with_headers)
            raise
