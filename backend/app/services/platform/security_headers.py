"""Security headers on every HTTP response: decision D5, the part that holds for every instance.

Owner: workstream H (platform), CP7b-1. ``SecurityHeadersMiddleware`` is an entry of ``MIDDLEWARE_STACK``, outside
GZip, and adds to every HTTP response:

- ``X-Content-Type-Options: nosniff``: a browser uses the type the server sends and never guesses one, so an upload
  is never run as a script or a page, and a script or a style sheet sent with another type is refused.
  ``register_served_types()`` gives the app the right type for every file it serves, so nothing the web app or the
  documentation loads goes out as ``application/octet-stream``;
- ``Referrer-Policy: strict-origin-when-cross-origin``: another site learns at most the origin, never a page's path
  or query.

A header a route already set is kept. Starlette sends its own 500 from ``ServerErrorMiddleware``, outside every
middleware of the stack: when a request fails before its answer started, this middleware sends the 500 itself, with
the headers, then lets the exception go on, so it is still logged.
"""

import mimetypes

from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: Added to every HTTP response that does not carry them already.
ALWAYS_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
)

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


class SecurityHeadersMiddleware:
    """Add ``ALWAYS_HEADERS`` to every HTTP response, keeping the ones a route set; other scopes pass untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

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
                headers.extend(header for header in ALWAYS_HEADERS if header[0] not in present)
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            if not started:
                await PlainTextResponse("Internal Server Error", status_code=500)(scope, receive, send_with_headers)
            raise
