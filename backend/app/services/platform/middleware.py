"""The app's middleware, outermost first.

Owner: workstream H (platform), CP2b. ``MIDDLEWARE_STACK`` lists every middleware of the app in order: the first entry
is the outermost, the first to see a request and the last to see its response. A workstream adds one entry where its
middleware belongs. Today: the activity tracking of sleep and wake, the security headers, GZip, CORS.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from backend.app.services.platform.security_headers import SecurityHeadersMiddleware
from backend.app.services.platform.sleep_wake.activity import ActivityMiddleware


@dataclass(frozen=True)
class MiddlewareEntry:
    """One middleware: a name for the docs and the tests, its class, and the options it is built with."""

    name: str
    cls: type
    options: Mapping[str, Any] = field(default_factory=dict)


MIDDLEWARE_STACK: tuple[MiddlewareEntry, ...] = (
    # The user's presence and the requests in flight (workstream Z, decision D-S1): outermost, so it sees every
    # request first and counts the compression of a response as in flight; the probes are not counted.
    MiddlewareEntry("activity", ActivityMiddleware),
    # nosniff and Referrer-Policy on every response, the 500s and the compressed ones included; with their switches on
    # (the managed profile), frame protection and the report-only CSP of the web app's pages (D5)
    MiddlewareEntry("security_headers", SecurityHeadersMiddleware),
    # Compress responses (API JSON, SvelteKit JS/CSS, docs HTML) for clients that accept
    # gzip: a first visit drops from ~7.5 MB to ~2.8 MB. Starlette leaves images, fonts,
    # archives, Server-Sent Events, 206 range replies and pre-encoded responses alone,
    # adds `Vary: Accept-Encoding`, and compresses bodies >= 128 KiB off the event loop.
    # Level 6 compresses as well as 9 on these bodies for a third of the CPU.
    MiddlewareEntry("gzip", GZipMiddleware, {"minimum_size": 1024, "compresslevel": 6}),
    # Configure CORS
    MiddlewareEntry("cors", CORSMiddleware, {"allow_credentials": True, "allow_methods": ["*"], "allow_headers": ["*"]}),
)


def install_middleware(app: FastAPI, stack: Sequence[MiddlewareEntry] | None = None) -> None:
    """Add ``stack`` (default ``MIDDLEWARE_STACK``) to ``app``, its first entry outermost.

    Starlette puts each middleware added outside the ones added before it, so the entries are added from the last.
    """
    for entry in reversed(MIDDLEWARE_STACK if stack is None else stack):
        app.add_middleware(entry.cls, **entry.options)
