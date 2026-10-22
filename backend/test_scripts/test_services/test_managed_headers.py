"""
The headers of the managed profile (workstream H, platform, checkpoint CP7b-2; developer decision D5, its «managed» part),
and the enforced policy of an HTML document (lot H-42), of every document and never on a 304 (lot H-45), and the inline
scripts of the build allowed by hash in the report-only policy (lot H-52).

H-55 v2 (the Content-Security-Policy always enforced, developer decision 19/10) supersedes, in the text below, everything it
says about ``PAGE_POLICY``, about frame protection being the only switch of an enforced policy, and about the build being
read once, when the middleware is built. Now, in every profile and with no switch: one enforced ``Content-Security-Policy``
per response, whose directives (each directive and its sources pinned exactly, the order between directives free) are
``object-src 'none'; base-uri 'self'; form-action 'self'`` on every document (also ``/mkdocs`` and the API docs, frame
protection on or off), in addition ``script-src 'self' 'wasm-unsafe-eval' 'report-sample'`` and the hashes of the build as
it is now, ``worker-src 'self' blob:`` and ``connect-src 'self'`` (+ the origin of LIBREFOLIO_PUBLIC_URL when valid, +
``https://api.github.com`` in the self-hosted profile) on a web app page, and ``frame-ancestors 'self'`` (with
``X-Frame-Options``) on any response when frame protection is on; never ``default-src``, ``style-src``, ``img-src``,
``font-src`` or ``frame-src``; a non-document with frame protection off has none; a 304 gets neither policy; a header a
route set is kept. The hashes follow the build through a cache keyed by the build's signature (section (k), step 1); the
report-only policy is as before plus the same extra ``connect-src`` sources, on web app pages only. Where (a), (d), (e),
(g), (h), (i) and (j) below still say ``PAGE_POLICY``, «once, when built» or «frame protection off: no header», read this
paragraph: the tests were rewritten for it (``expected_enforced`` is the table). The old pin of ``PAGE_POLICY`` by value is
gone. Section (k), at the end, holds the new cases (step 1: the hashes; step 3: the table and the connect sources).

H-55 wave 4, R4 (a policy for the workers, section (l)) adds one more kind to the table: a JavaScript response (``text/javascript``
or ``application/javascript``, parameters ignored) at a path under ``/_app/`` is not «a response that is no document», it
carries the policy of a worker (``expected_worker_policy``: ``script-src 'self'``, ``connect-src`` as a web app page's,
``worker-src 'self' blob:``, ``object-src 'none'``, ``base-uri 'self'``, + ``frame-ancestors 'self'`` with frame protection on).
Where (a), (g), (i) and the like say that a script under ``/_app`` carries ``frame-ancestors`` alone, read this paragraph:
``expected_enforced`` (``worker_script=True``) is the table.

H-55 wave 5, R5 (the API docs served by us, section (m)) adds one more kind to the table: the two pages of ``install_api_docs``
(``backend/app/api/api_docs.py``), exactly ``/api/v1/docs`` and ``/api/v1/redoc`` answered ``text/html`` (parameters ignored, any
case), are documents that load Swagger UI and ReDoc from jsDelivr (exact version, Subresource Integrity), run start scripts
served by the backend itself and start ReDoc's search worker from a blob. Beyond the document trio they carry
``script-src 'self' https://cdn.jsdelivr.net`` (never a hash, never ``'wasm-unsafe-eval'``), ``worker-src 'self' blob:`` and
``connect-src 'self'`` alone (the public origin and GitHub's API are the
web app's), plus ``frame-ancestors 'self'`` with frame protection, in one field; no report-only policy. Any other document under
``/api/`` (and the same paths with another type, a trailing slash or another prefix) keeps the trio alone, and
``/api/v1/openapi.json`` (JSON) is no document. The API docs of the app below are therefore our pages (``site_app(api_docs=True)``),
not FastAPI's, which ``main.py`` no longer builds; where (a), (b), (g) and (k) say «Swagger UI and ReDoc under ``/api/v1``» with the
trio alone, read this paragraph: ``expected_enforced`` (``api_docs_page=True``) is the table.

Under test: ``SecurityHeadersMiddleware`` (``backend/app/services/platform/security_headers.py``, CP7b-1), which reads the
settings ``LIBREFOLIO_FRAME_PROTECTION`` and ``LIBREFOLIO_CSP_REPORT_ONLY`` (``PROFILE_DEFAULTS``: off in self-hosted, on
in managed) once, when it is built: ``SecurityHeadersMiddleware(app)`` calls ``get_settings()`` in ``__init__``. The
contract:

(a) Frame protection. On (``managed``, or ``LIBREFOLIO_FRAME_PROTECTION=true`` under self-hosted): every HTTP response
    carries ``X-Frame-Options: SAMEORIGIN`` and one enforced ``Content-Security-Policy``, once each, whose value follows
    the type of the response (H-42). An HTML document, a ``Content-Type`` starting with ``text/html`` in any case,
    parameters such as ``; charset=utf-8`` allowed, carries exactly ``PAGE_POLICY``, ``frame-ancestors 'self';
    object-src 'none'; base-uri 'self'; form-action 'self'``: here ``/``, a client-side route answered by the catch-all
    (also gzip-compressed), ``/200.html``, ``/offline.html``, the documentation under ``/mkdocs``, Swagger UI and ReDoc
    under ``/api/v1``, the catch-all's HTML 404 of an unknown API path. Every other response carries exactly
    ``frame-ancestors 'self'``, as before H-42: here a text file, an image and a JavaScript chunk of the build, the API's
    JSON, a CORS preflight, a 500. Off (self-hosted, or ``false`` over ``managed``): neither header, on any response.
    Why the three directives go on documents only (H-42, security review E, design approved by the coordinator): they
    touch no script, and they mean something only for a document: no plugin content (``object-src 'none'``), no
    injected ``<base>`` retargeting the relative URLs (``base-uri 'self'``), no form sent to another origin
    (``form-action 'self'``). Anywhere else they protect nothing and can break something: Chromium counts its built-in
    PDF viewer as a plugin, so ``object-src 'none'`` on a PDF could stop it showing the PDF inline. The report-only
    policy of (b) and (c) is unchanged by H-42.
(b) The report-only policy. On (``managed``, or ``LIBREFOLIO_CSP_REPORT_ONLY=true``): ``Content-Security-Policy-Report-Only``
    is on the web app's HTML, the responses whose ``Content-Type`` is ``text/html`` outside ``/mkdocs`` and ``/api/``:
    ``/``, a client-side route answered by the catch-all (also gzip-compressed), ``/200.html`` and ``/offline.html``. It
    is on no other response: not the documentation's HTML, not the API's JSON nor its HTML (Swagger UI, ReDoc, the
    catch-all's HTML 404 for an unknown API path), not a JavaScript chunk under ``/_app``, an image or a text file of the
    build, a CORS preflight or a 500. Off: on no response. The two switches are independent of each other.
(c) The report-only policy, read directive by directive and never as a string: ``default-src 'self'``, ``object-src
    'none'``, ``base-uri 'self'``, ``frame-ancestors 'self'``, and ``script-src`` exactly ``'self' 'wasm-unsafe-eval'
    'report-sample'``, then the hash of every inline script of the fake build's pages, each once, sorted (H-52, see (j));
    each directive once; no ``report-uri`` nor ``report-to`` and no ``Report-To``/``Reporting-Endpoints`` header
    (decision: violations go to the browser's console only, the sample ``'report-sample'`` asks for included).
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
    broker's file shown inline), ``image/png``, ``text/javascript`` (outside ``/_app/``; under it, since R4, the policy of a
    worker, section (l)), ``text/css``, ``application/json`` and a 204 without ``Content-Type`` carry ``frame-ancestors
    'self'``; with frame protection off, none carries either header.
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
(j) H-52: the inline scripts of the build, allowed by hash. ``static_site.spa_inline_script_hashes(build_dir)``, pure,
    reads every ``*.html`` directly in ``build_dir``, never one in a subfolder, as the stdlib's ``html.parser`` reads a
    page (a script inside a comment is none, a ``>`` in a quoted attribute value ends no tag, ``<SCRIPT>`` is a script),
    and returns the CSP source expression ``'sha256-<base64>'`` of every inline script, a ``<script>`` whose start tag
    has no ``src`` attribute, whatever its ``type`` (a data block's hash is harmless): its text with the line ends of the
    HTML parser (CR LF and a lone CR become LF), as UTF-8; each expression once, sorted, in a tuple. No build, or no page
    at its top, gives ``()``; a page that cannot be decoded as UTF-8 is skipped with one warning, the others still
    count. Every expected expression is computed here, with hashlib and base64, and the computation is checked once
    against a published vector. ``security_headers.report_only_policy(script_hashes)`` is ``CSP_REPORT_ONLY_POLICY``,
    whose ``script-src`` is now ``'self' 'wasm-unsafe-eval' 'report-sample'``, with the given expressions appended to
    ``script-src`` in the order given, every other directive unchanged and in place; given none, the constant itself;
    given as a tuple, a list or an iterator read once alike (any ``Iterable[str]``). The middleware, the report-only
    policy on, builds its header once, when it is built, from the build that ``static_site.FRONTEND_BUILD_DIR`` names
    then: the web app's pages carry that build's hashes, the documentation's and the API's HTML no policy; a build
    changed afterwards (rewritten, removed, another one named) leaves the header as it was, a restart takes it; a build
    without an inline script (none, no page, an undecodable page) gives the policy without a hash, and the middleware
    is built all the same; with the policy off, the build is never read.

How. Each case first sets its configuration with ``monkeypatch``: ``LIBREFOLIO_TEST_MODE=1`` (``get_settings()`` has no
``_env_file`` argument, and in test mode it reads no ``.env``) and ``LIBREFOLIO_TEST_DATA_DIR`` under ``tmp_path`` (so it
never looks at the lane's data), the profile and the two switches removed, then set as the case says, and
``static_site.FRONTEND_BUILD_DIR``, the build the middleware hashes when it is built (H-52), a missing folder under
``tmp_path``, never the checkout's build (a case wanting one names its own afterwards); ``get_settings()`` must resolve
the two switches as the case expects (a barrier, so that an absence is never the effect of a variable nobody read).
Then it builds a fresh ``FastAPI()`` assembled as ``backend/app/main.py`` assembles the app: the entries
``security_headers``, ``gzip`` and ``cors`` of ``MIDDLEWARE_STACK`` with their options (as ``test_security_headers``
does), the API docs under ``/api/v1`` (Swagger UI and ReDoc, as in ``main.py``), a few routes, and the static site of a
fake build and a fake documentation under ``tmp_path`` (``FRONTEND_BUILD_DIR`` and ``SITE_DIR`` swapped as in
``test_static_cache_policy``). The fake build's three pages carry the inline scripts of today's build (H-52): app.html's
anti-FOUC in ``index.html`` and ``200.html``, SvelteKit's bootstrap, different in each, and ``offline.html``'s own.
Starlette builds the middleware at the app's first request, with the configuration in place. The app of
``backend.app.main`` is never used: its middleware is built once per process, with whatever configuration came first.
(e), (g) and most of (j) build the middleware alone, around a bare ASGI app, after the configuration is set. Requests
are raw ASGI calls, so every header line is seen as it was sent, duplicates included; each is bounded by a deadline;
the lifespan never runs. A barrier precedes every header: the response is the one its case names (status, type, body).
The module of CP7b-1 is imported when a test runs, so this file collects before it exists; every enforced header is
compared with this file's own copy of the contract (``expected_enforced``), never with a constant of the module.
H-52's ``static_site.spa_inline_script_hashes``, ``report_only_policy`` and ``CSP_REPORT_ONLY_POLICY`` are read by
name too, in the tests of (j): before H-52 those fail naming H-52, and so does (c), whose ``script-src`` is now exact,
while every other test still runs. The logs of (j) are read with ``structlog.testing.capture_logs`` and pytest's
``caplog``, each behind a canary, as in ``test_backup_outcome``. No DB, no server, no network.
"""

from __future__ import annotations

import asyncio
import base64
import gzip
import hashlib
import importlib
import json
import logging
import os
import re
import shutil
import threading
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.routing import Mount
from structlog.testing import capture_logs

from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.logging_config import get_logger
from backend.app.services.platform import static_site
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, MiddlewareEntry, install_middleware
from backend.test_scripts.test_utils import print_section, print_success

SECURITY_MODULE = "backend.app.services.platform.security_headers"
CLASS_NAME = "SecurityHeadersMiddleware"
ENTRY_NAME = "security_headers"
#: H-45: the constants of SECURITY_MODULE naming the media types of a document, read by name when their test runs.
DOCUMENT_MEDIA_TYPES_NAME = "DOCUMENT_MEDIA_TYPES"
DOCUMENT_MEDIA_TYPE_SUFFIX_NAME = "DOCUMENT_MEDIA_TYPE_SUFFIX"
#: The entries of MIDDLEWARE_STACK a fresh app holds: this one, and the two whose responses it must see.
STACK_ENTRIES = (ENTRY_NAME, "gzip", "cors")

PROFILE = "LIBREFOLIO_PROFILE"
FRAME_PROTECTION = "LIBREFOLIO_FRAME_PROTECTION"
CSP_REPORT_ONLY = "LIBREFOLIO_CSP_REPORT_ONLY"
#: H-55 v2: the address users reach the instance at (``backend.app.config.accounts.public_url()``), whose origin the
#: ``connect-src`` of a web app page holds when it is valid.
PUBLIC_URL = "LIBREFOLIO_PUBLIC_URL"
#: H-55 v2: the address of the update check the browser makes outside the managed profile: a connect source there only.
GITHUB_API = "https://api.github.com"

# CP7b-1: on every response, in every configuration
NOSNIFF = "nosniff"
REFERRER_POLICY = "strict-origin-when-cross-origin"

# (a) Frame protection, and since H-55 v2 the enforced policy by response (the table of (k))
FRAME_OPTIONS = "SAMEORIGIN"
#: With frame protection on, every response: who may frame the app (the one directive of a non-document).
FRAME_ANCESTORS = ("'self'",)
#: H-55 v2: the three directives of every document (a response of ``DOCUMENT_MEDIA_TYPES`` or ``+xml``), in every profile
#: and at every path, the documentation and the API docs included, frame protection on or off: no plugin content, no
#: ``<base>`` retargeting the relative URLs, no form sent to another origin. They touch no script.
DOCUMENT_TRIO: dict[str, tuple[str, ...]] = {"object-src": ("'none'",), "base-uri": ("'self'",), "form-action": ("'self'",)}
#: H-55 v2: what a web app page (``text/html`` exactly, outside ``/mkdocs`` and ``/api``) adds: ``script-src`` is
#: ``SCRIPT_SRC`` and the hashes of the build now, ``connect-src`` is ``CONNECT_SRC`` and the connect sources of the
#: configuration (``Mode.connect_sources``).
WORKER_SRC = ("'self'", "blob:")
CONNECT_SRC = ("'self'",)
#: H-55 R5: what the two API docs pages add to the document trio: scripts from ``'self'`` and jsDelivr (no hash, no wasm),
#: ReDoc's search worker (``WORKER_SRC``) and ``connect-src 'self'`` alone, whatever the public address or the profile.
API_DOCS_SCRIPT_SRC = ("'self'", "https://cdn.jsdelivr.net")
API_DOCS_PATHS = (f"{API_V1_PREFIX}/docs", f"{API_V1_PREFIX}/redoc")
#: H-55 v2: directives the enforced header never holds: styles, images, fonts and frames stay free (embedding the app is a
#: legitimate self-hosted use); they stay in the report-only policy alone.
NEVER_ENFORCED = ("default-src", "style-src", "img-src", "font-src", "frame-src")
#: H-45: the media types of a document, exactly (``security_headers.DOCUMENT_MEDIA_TYPES``): opened directly, an XHTML
#: page, an SVG image and an XML file are documents as an HTML page is, so they carry the document trio.
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
#: ``script-src``, exactly these sources (H-52: ``'report-sample'`` asks the browser to put the first characters of what it
#: would block in its report), then the hash of every inline script of the build the middleware was built on, sorted.
SCRIPT_SRC = ("'self'", "'wasm-unsafe-eval'", "'report-sample'")
#: Decision: the violations go to the browser's console, and nowhere else.
NO_REPORT_DIRECTIVES = ("report-uri", "report-to")
NO_REPORT_HEADERS = ("report-to", "reporting-endpoints")

#: The three headers of D5 for the managed profile, as they appear in a raw ASGI message.
D5_HEADERS = ("x-frame-options", "content-security-policy", "content-security-policy-report-only")

#: Every raw call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0

PAGE_HTML = b"<!doctype html><title>page</title>"

# H-52: the pages of a build carry inline scripts, as today's frontend/build does; the middleware hashes them when built
#: The build's name, as SvelteKit writes one into its bootstrap and into the chunks' names; and the next build's.
BUILD_ID = "a1b2"
NEXT_BUILD_ID = "c3d4"
#: app.html's anti-FOUC, inline in both entry pages (index.html and 200.html), the same in every build.
ANTI_FOUC_SCRIPT = "\n            // Anti-FOUC: apply the theme class before the first paint.\n            document.documentElement.classList.add(localStorage.getItem('librefolio-theme') === 'dark' ? 'dark' : 'light');\n        "
#: The ``base`` of SvelteKit's bootstrap: index.html's, then 200.html's (the SPA fallback, answered at any depth).
INDEX_BASE = 'new URL(".", location).pathname.slice(0, -1)'
FALLBACK_BASE = '""'
#: The one inline script of offline.html, the service worker's offline page, served as a page of the web app too.
OFFLINE_SCRIPT = "\n        document.getElementById('retry').addEventListener('click', () => location.reload());\n    "
OFFLINE_HTML = f'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8" />\n<title>offline</title>\n</head>\n<body>\n<button id="retry">Retry</button>\n<script>{OFFLINE_SCRIPT}</script>\n</body>\n</html>\n'.encode()


def sha256_source(script: str) -> str:
    """H-52: the CSP source expression allowing an inline script whose text, as the browser parses it, is ``script``:
    ``'sha256-``, the base64 of the SHA-256 digest of its UTF-8 bytes, ``'``. Computed here, with hashlib and base64,
    never with the function under test."""
    digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
    return f"'sha256-{digest}'"


def bootstrap_script(base: str, build_id: str) -> str:
    """H-52: SvelteKit's inline bootstrap of an entry page, the shape of today's: it names its build (``build_id``, as the
    chunks' names do), so its hash changes with every build, and its ``base`` differs between index.html and 200.html."""
    start_chunk, app_chunk = f"./_app/immutable/entry/start.{build_id}.js", f"./_app/immutable/entry/app.{build_id}.js"
    return f"\n\t\t\t{{\n\t\t\t\t__sveltekit_{build_id} = {{ base: {base} }};\n\t\t\t\tconst element = document.currentScript.parentElement;\n\t\t\t\tPromise.all([import({start_chunk!r}), import({app_chunk!r})]).then(([kit, app]) => kit.start(app, element));\n\t\t\t}}\n\t\t"


def entry_page(title: str, base: str, build_id: str, body: str = "") -> bytes:
    """H-52: an entry page of the build ``build_id`` (index.html, 200.html), the shape of today's: app.html's anti-FOUC in
    the head, the entry chunk preloaded by a link (no script), ``body``, then SvelteKit's bootstrap for ``base``."""
    head = f'<head>\n<meta charset="utf-8" />\n<title>{title}</title>\n<script>{ANTI_FOUC_SCRIPT}</script>\n<link rel="modulepreload" href="./_app/immutable/entry/start.{build_id}.js">\n</head>'
    return f'<!doctype html>\n<html lang="en">\n{head}\n<body>\n{body}<div style="display: contents"><script>{bootstrap_script(base, build_id)}</script></div>\n</body>\n</html>\n'.encode()


def build_pages(build_id: str) -> dict[str, bytes]:
    """H-52: the pages of the build ``build_id``, as today's build writes them: index.html and 200.html, each with app.html's
    anti-FOUC and a bootstrap of its own, and offline.html with its one script. 200.html, the SPA fallback, is over GZip's
    minimum_size (1024 in MIDDLEWARE_STACK): the client-side route asked with Accept-Encoding: gzip is compressed."""
    filler = "<p>LibreFolio keeps the history of your investments.</p>\n" * 40
    return {
        "index.html": entry_page("index", INDEX_BASE, build_id),
        "200.html": entry_page("spa fallback", FALLBACK_BASE, build_id, filler),
        "offline.html": OFFLINE_HTML,
    }


def build_scripts(build_id: str) -> tuple[str, ...]:
    """H-52: the inline scripts of the pages of the build ``build_id``, as the browser parses them: app.html's anti-FOUC
    (in two pages), the bootstraps of index.html and of 200.html, offline.html's script."""
    return (ANTI_FOUC_SCRIPT, bootstrap_script(INDEX_BASE, build_id), bootstrap_script(FALLBACK_BASE, build_id), OFFLINE_SCRIPT)


def build_sources(build_id: str) -> tuple[str, ...]:
    """H-52: what follows ``SCRIPT_SRC`` in script-src for the pages of the build ``build_id``, computed here: the expression
    of each of its inline scripts, each once, sorted. Four: the anti-FOUC once, though it is in two pages."""
    return tuple(sorted({sha256_source(script) for script in build_scripts(build_id)}))


#: The fake build's pages, and what follows SCRIPT_SRC in the script-src of a middleware built on them (H-52).
FAKE_BUILD_PAGES = build_pages(BUILD_ID)
FAKE_BUILD_SOURCES = build_sources(BUILD_ID)
INDEX_HTML = FAKE_BUILD_PAGES["index.html"]
FALLBACK_HTML = FAKE_BUILD_PAGES["200.html"]
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
    "offline.html": OFFLINE_HTML,
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
    """A configuration: the variables it sets (of the profile, the two switches and, H-55 v2, LIBREFOLIO_PUBLIC_URL, the
    others are unset), and the switches ``get_settings()`` must resolve them to. ``public_origin``: the origin of the
    valid LIBREFOLIO_PUBLIC_URL it sets, written here (``None``: none set, or an invalid one that adds nothing)."""

    env: tuple[tuple[str, str], ...]
    frame_protection: bool
    csp_report_only: bool
    public_origin: str | None = None

    def describe(self) -> str:
        return ", ".join(f"{name}={value}" for name, value in self.env) or "nothing set"

    @property
    def managed(self) -> bool:
        """The managed profile, as ``Settings`` reads the profile this configuration sets."""
        return dict(self.env).get(PROFILE, "").strip().lower() == "managed"

    @property
    def connect_sources(self) -> tuple[str, ...]:
        """H-55 v2: what follows ``CONNECT_SRC`` in the ``connect-src`` of a web app page built under this configuration,
        computed here: the origin of LIBREFOLIO_PUBLIC_URL when it is valid, then ``GITHUB_API`` in the self-hosted
        profile only (the update check runs in the browser there)."""
        return ((self.public_origin,) if self.public_origin is not None else ()) + (() if self.managed else (GITHUB_API,))


MODES: dict[str, Mode] = {
    "selfhosted-nothing-set": Mode((), frame_protection=False, csp_report_only=False),
    "selfhosted": Mode(((PROFILE, "selfhosted"),), frame_protection=False, csp_report_only=False),
    "managed": Mode(((PROFILE, "managed"),), frame_protection=True, csp_report_only=True),
    "selfhosted-frame-protection-true": Mode(((FRAME_PROTECTION, "true"),), frame_protection=True, csp_report_only=False),
    "selfhosted-csp-report-only-true": Mode(((CSP_REPORT_ONLY, "true"),), frame_protection=False, csp_report_only=True),
    "managed-both-switches-false": Mode(((PROFILE, "managed"), (FRAME_PROTECTION, "false"), (CSP_REPORT_ONLY, "false")), frame_protection=False, csp_report_only=False),
}
REPORT_ONLY_MODES = {name: mode for name, mode in MODES.items() if mode.csp_report_only}
REPORT_ONLY_OFF_MODES = {name: mode for name, mode in MODES.items() if not mode.csp_report_only}


#: H-52: what ``configure`` points ``static_site.FRONTEND_BUILD_DIR`` at, under ``tmp_path``: a folder that does not exist.
NO_BUILD = "no-build"


def configure(monkeypatch: pytest.MonkeyPatch, mode: Mode, tmp_path: Path) -> None:
    """Make ``mode`` the configuration ``get_settings()`` reads, and check that it reads it so. The build a middleware built
    afterwards hashes (H-52) is a missing folder under ``tmp_path``, never the checkout's: a case wanting one names it after."""
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")  # get_settings() reads no .env in test mode: only this environment
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))  # get_settings() never looks at the lane's data
    for name in (PROFILE, FRAME_PROTECTION, CSP_REPORT_ONLY, PUBLIC_URL):  # H-55 v2: no lane's public address reaches a case
        monkeypatch.delenv(name, raising=False)
    for name, value in mode.env:
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", tmp_path / NO_BUILD)  # H-52: never the checkout's frontend/build
    if mode.public_origin is not None:  # H-55 v2: the origin written here is the canonical form the hosting panel computes
        from backend.app.config.hosting_panel import panel_audience  # noqa: PLC0415

        assert panel_audience() == mode.public_origin, f"barrier: with {mode.describe()}, the canonical origin of {PUBLIC_URL} is {panel_audience()!r}, not the {mode.public_origin!r} this configuration expects"

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


def written_directives(value: str, what: str) -> dict[str, tuple[str, ...]]:
    """``directives`` with every source as written, only the directive names lower-cased (H-52): a hash source is base64,
    whose case is part of its value, so it is compared as sent. In the policy's order, each directive once."""
    parsed = [(tokens[0].lower(), tuple(tokens[1:])) for tokens in (part.split() for part in value.split(";")) if tokens]
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


async def api_other_html() -> HTMLResponse:
    """H-55 R5: an HTML document under ``/api/v1`` that is none of the API docs' two pages: it keeps the document trio alone."""
    return HTMLResponse(PAGE_HTML)


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
    f"{API_V1_PREFIX}/other": api_other_html,
    "/sets-frame-options": sets_frame_options,
    "/sets-csp": sets_csp,
    "/sets-csp-report-only": sets_csp_report_only,
}


def _write_tree(root: Path, files: dict[str, bytes]) -> Path:
    for relative, content in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_bytes(content)
    return root


def site_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, api_docs: bool = False) -> FastAPI:
    """A fresh app: the stack's ``security_headers``, ``gzip`` and ``cors``, ``ROUTES``, then (H-55 R5) our API docs pages when
    ``api_docs`` (``install_api_docs``, as ``main.py`` installs them: FastAPI builds none of its own), then the static site of
    a fake build and documentation. Its schema is at ``/api/v1/openapi.json``, as when the documentation is on. Its middleware
    is built at its first request, with the configuration then in place."""
    security_entry()
    stack = tuple(entry for entry in MIDDLEWARE_STACK if entry.name in STACK_ENTRIES)
    assert sorted(entry.name for entry in stack) == sorted(STACK_ENTRIES), f"MIDDLEWARE_STACK must hold {STACK_ENTRIES} once each: {[entry.name for entry in MIDDLEWARE_STACK]}"
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", _write_tree(tmp_path / "build", BUILD_FILES))
    monkeypatch.setattr(static_site, "SITE_DIR", _write_tree(tmp_path / "site", SITE_FILES))

    app = FastAPI(openapi_url=f"{API_V1_PREFIX}/openapi.json", docs_url=None, redoc_url=None)
    install_middleware(app, stack)
    for path, endpoint in ROUTES.items():
        app.add_api_route(path, endpoint, methods=["GET"])
    if api_docs:
        from backend.app.api.api_docs import install_api_docs  # noqa: PLC0415 — H-55 R5: read when a case needs it, so the other cases still run before the module exists

        install_api_docs(app, enabled=True)
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
    """H-55 R5: our Swagger UI page: it names its start script, which the backend serves (FastAPI's page started inline)."""
    assert reply.raised is None and reply.status == 200 and reply.media_type == "text/html", f"barrier: not the API docs' HTML: {reply.status} {reply.headers}, raised {reply.raised!r}"
    assert b"/api/v1/docs/swagger-init.js" in reply.body, f"barrier: not our Swagger UI page: {reply.body[:120]!r}"


def _is_redoc(reply: Reply) -> None:
    """H-55 R5: our ReDoc page: it names its start script, which the backend serves (FastAPI's page used a ``<redoc>`` tag)."""
    assert reply.raised is None and reply.status == 200 and reply.media_type == "text/html", f"barrier: not the API docs' HTML: {reply.status} {reply.headers}, raised {reply.raised!r}"
    assert b"/api/v1/redoc/redoc-init.js" in reply.body, f"barrier: not our ReDoc page: {reply.body[:120]!r}"


def _is_the_openapi_json(reply: Reply) -> None:
    assert reply.raised is None and reply.status == 200 and reply.media_type == "application/json", f"barrier: not the schema's JSON: {reply.status} {reply.headers}, raised {reply.raised!r}"
    assert "openapi" in json.loads(reply.body), f"barrier: not an OpenAPI document: {reply.body[:120]!r}"


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
    #: An HTML document (text/html, wherever it is): with frame protection on, it carries the document trio (H-55 v2).
    html: bool
    #: An HTML document of the web app (text/html, outside /mkdocs and /api/): where the report-only policy goes when on.
    web_app_html: bool
    method: str = "GET"
    headers: tuple[tuple[str, str], ...] = ()
    #: R4: a JavaScript response under /_app/, which carries the policy of a worker (never a document).
    worker_script: bool = False
    #: R5: one of the two pages of the API docs (``install_api_docs``), a document that adds script, worker and connect sources.
    api_docs: bool = False


CASES: dict[str, Case] = {
    # The web app's HTML documents
    "root": Case("/", answered(200, HTML, INDEX_HTML), html=True, web_app_html=True),
    "client-side-route": Case("/portfolio/overview", answered(200, HTML, FALLBACK_HTML), html=True, web_app_html=True),
    "client-side-route-gzipped": Case("/portfolio/overview", answered(200, HTML, FALLBACK_HTML, compressed=True), html=True, web_app_html=True, headers=(("Accept-Encoding", "gzip"),)),
    "200-html": Case("/200.html", answered(200, HTML, FALLBACK_HTML), html=True, web_app_html=True),
    "offline-html": Case("/offline.html", answered(200, HTML, OFFLINE_HTML), html=True, web_app_html=True),
    # Every other response
    "text-file-of-the-build": Case("/robots.txt", answered(200, TEXT, ROBOTS_TXT), html=False, web_app_html=False),
    "image-of-the-build": Case("/favicon.png", answered(200, IMAGE, FAVICON_PNG), html=False, web_app_html=False),
    "javascript-under-app": Case("/_app/immutable/chunks/a1b2.js", answered(200, JAVASCRIPT, CHUNK_JS), html=False, web_app_html=False, worker_script=True),
    "docs-root": Case("/mkdocs", answered(200, HTML, DOCS_INDEX_HTML), html=True, web_app_html=False),
    "docs-page": Case("/mkdocs/user/", answered(200, HTML, DOCS_PAGE_HTML), html=True, web_app_html=False),
    "api-json": Case(f"{API_V1_PREFIX}/things", _is_the_json, html=False, web_app_html=False),
    "api-html-swagger-ui": Case(f"{API_V1_PREFIX}/docs", _is_swagger_ui, html=True, web_app_html=False, api_docs=True),
    "api-html-redoc": Case(f"{API_V1_PREFIX}/redoc", _is_redoc, html=True, web_app_html=False, api_docs=True),
    "api-openapi-json": Case(f"{API_V1_PREFIX}/openapi.json", _is_the_openapi_json, html=False, web_app_html=False),
    "api-other-html-document": Case(f"{API_V1_PREFIX}/other", answered(200, HTML, PAGE_HTML), html=True, web_app_html=False),
    "api-unknown-path-html-404": Case(f"{API_V1_PREFIX}/no-such-route", _is_an_html_404, html=True, web_app_html=False),
    "api-cors-preflight": Case(f"{API_V1_PREFIX}/things", _is_a_preflight_answer, html=False, web_app_html=False, method="OPTIONS", headers=(("Origin", "http://elsewhere.test"), ("Access-Control-Request-Method", "GET"))),
    "api-500": Case(f"{API_V1_PREFIX}/boom", _is_the_500, html=False, web_app_html=False),
}
WEB_APP_HTML = {name: case for name, case in CASES.items() if case.web_app_html}


async def answer(case: Case, mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Reply:
    """``case`` on a fresh app built under ``mode``, past its barriers: the response is the one the case names, of the
    type the case declares (an HTML document or not), and the middleware saw it."""
    configure(monkeypatch, mode, tmp_path)
    reply = await call(site_app(tmp_path, monkeypatch, api_docs=case.api_docs), case.path, method=case.method, headers=case.headers)
    case.is_the_kind(reply)
    assert (reply.media_type == "text/html") is case.html, f"barrier: {case.method} {case.path} answered {reply.media_type!r}, while the case declares html={case.html}; headers {reply.headers}"
    assert_always_on(reply, f"{case.method} {case.path} with {mode.describe()}")
    return reply


# =============================================================================
# (a) THE ENFORCED POLICY BY RESPONSE (H-42, H-45, H-55 v2), THE FRAME PROTECTION, AND (f) THE HEADERS OF CP7b-1
# =============================================================================


def expected_enforced(mode: Mode, *, document: bool, web_app_page: bool, script_hashes: Sequence[str] = (), worker_script: bool = False, api_docs_page: bool = False) -> dict[str, tuple[str, ...]] | None:
    """H-55 v2, the table: the directives of the one enforced ``Content-Security-Policy`` of a response under ``mode``,
    ``{directive: sources}``, written here, never read from the module under test; ``None``: no policy at all.

    ``frame-ancestors 'self'`` whenever frame protection is on; a document adds the trio, in every profile, frame
    protection on or off; a web app page (``web_app_page``, a document by construction) adds ``script-src``
    (``SCRIPT_SRC`` then ``script_hashes``), ``worker-src`` and ``connect-src`` (``CONNECT_SRC`` then the connect sources
    of ``mode``). A non-document with frame protection off has no policy. R4 (wave 4): a JavaScript response under ``/_app/``
    (``worker_script``, never a document) carries the policy of a worker, ``expected_worker_policy``. R5 (wave 5): one of the two
    API docs pages (``api_docs_page``, a document, never a web app page) adds ``script-src 'self' https://cdn.jsdelivr.net``, ``worker-src`` and
    ``connect-src 'self'`` alone (no connect source of the configuration)."""
    assert document or not web_app_page, "barrier: a web app page is a document"
    assert document or not api_docs_page, "barrier: an API docs page is a document"
    assert not (api_docs_page and web_app_page), "barrier: an API docs page is no web app page"
    assert not (worker_script and document), "barrier: a script under /_app/ is no document"
    if worker_script:
        return expected_worker_policy(mode)
    expected: dict[str, tuple[str, ...]] = {}
    if mode.frame_protection:
        expected["frame-ancestors"] = FRAME_ANCESTORS
    if document:
        expected.update(DOCUMENT_TRIO)
    if web_app_page:
        expected["script-src"] = SCRIPT_SRC + tuple(script_hashes)
        expected["worker-src"] = WORKER_SRC
        expected["connect-src"] = CONNECT_SRC + mode.connect_sources
    if api_docs_page:
        expected["script-src"] = API_DOCS_SCRIPT_SRC
        expected["worker-src"] = WORKER_SRC
        expected["connect-src"] = CONNECT_SRC
    return expected or None


def assert_frame_protection(reply: Reply, mode: Mode, document: bool, what: str, *, web_app_page: bool = False, script_hashes: Sequence[str] = (), worker_script: bool = False, api_docs_page: bool = False) -> str:
    """The enforced headers of ``reply`` under ``mode``: ``X-Frame-Options: SAMEORIGIN`` once exactly when frame protection
    is on; at most one ``Content-Security-Policy`` field (never two), whose directives and the sources of each are
    exactly ``expected_enforced`` (the order between directives is free). Returns what it saw, for the log."""
    frame_options, policies = reply.values("x-frame-options"), reply.values("content-security-policy")
    assert frame_options == ([FRAME_OPTIONS] if mode.frame_protection else []), f"{what}: X-Frame-Options is {frame_options}, wanted {[FRAME_OPTIONS] if mode.frame_protection else []}: frame protection is {'on' if mode.frame_protection else 'off'}"
    expected = expected_enforced(mode, document=document, web_app_page=web_app_page, script_hashes=script_hashes, worker_script=worker_script, api_docs_page=api_docs_page)
    if expected is None:
        assert policies == [], f"{what}: a response that is no document, with frame protection off, carries no Content-Security-Policy, yet it is {policies}"
        return "no Content-Security-Policy"
    kind = "a web app page" if web_app_page else "an API docs page (R5)" if api_docs_page else "a document" if document else "a JavaScript response under /_app/ (R4: the policy of a worker)" if worker_script else "a response that is no document"
    assert len(policies) == 1, f"{what}: Content-Security-Policy is {policies}, wanted exactly one field: {kind} under {mode.describe()} carries {expected}"
    found = written_directives(policies[0], what)
    assert (
        found == expected
    ), f"{what}: the enforced policy {policies[0]!r} is not, directive by directive and source by source, {expected} ({kind}, H-55 v2: the document trio in every profile, frame-ancestors with frame protection on, a web app page adding script-src, worker-src and connect-src, R4: a script under /_app/ the policy of a worker); the order between directives is free"
    return f"{kind}: Content-Security-Policy {sorted(found)}, X-Frame-Options {frame_options}"


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES.values(), ids=list(CASES))
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_the_enforced_policy_follows_the_response_in_every_profile_and_the_frame_protection_adds_its_own(mode: Mode, case: Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-55 v2, the table over the app of ``main.py``'s shape: the document trio on every document (also ``/mkdocs`` and
    the API docs) with frame protection on or off; the web app page's script, worker and connect sources, with the hashes
    of the fake build; ``frame-ancestors`` with frame protection on; a non-document with it off: no policy; R4: a JavaScript
    chunk under ``/_app/`` the policy of a worker, whatever the frame protection."""
    what = f"{case.method} {case.path} with {mode.describe()}"
    print_section(f"H-55 v2 enforced policy: {what}")

    reply = await answer(case, mode, tmp_path, monkeypatch)

    print_success(f"✓ {assert_frame_protection(reply, mode, case.html, what, web_app_page=case.web_app_html, script_hashes=FAKE_BUILD_SOURCES, worker_script=case.worker_script, api_docs_page=case.api_docs)}; nosniff and Referrer-Policy")


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
    script_src, expected_script_src = written_directives(policies[0], what).get("script-src"), SCRIPT_SRC + FAKE_BUILD_SOURCES
    assert script_src == expected_script_src, f"{what}: script-src is {script_src} in {policies[0]!r}, not {expected_script_src}: H-52, {SCRIPT_SRC}, then the hash of every inline script of the fake build's pages, each once, sorted"
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
    the enforced policy of a web app page (H-55 v2), with the hashes of the fake build the route-set cases serve."""
    if len(values) != 1:
        return False
    if name == "x-frame-options":
        return values[0] == FRAME_OPTIONS
    if name == "content-security-policy":
        return written_directives(values[0], name) == expected_enforced(MODES["managed"], document=True, web_app_page=True, script_hashes=FAKE_BUILD_SOURCES)
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
    assert (
        not others
    ), f"GET {path}: the middleware must still add its own value of the other headers of D5, once each, on this web app page, its enforced Content-Security-Policy being the table's (H-55 v2: the trio, frame-ancestors, script-src with the build's hashes, worker-src, connect-src): {others}"
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
    # H-55 v2: the enforced policy is on every web app page in every profile, so Content-Security-Policy is always present
    expected = dict(zip(D5_HEADERS, (MODES[built].frame_protection, True, MODES[built].csp_report_only), strict=True))
    assert present(reply) == expected, f"built {built} and called {called}, the headers of D5 present are {present(reply)}, not those of the configuration it was built with, {expected}: the settings must be read once, in __init__"
    assert_frame_protection(reply, MODES[built], True, f"GET / built {built}, called {called}", web_app_page=True)  # frame-ancestors and connect-src (the profile's) as built
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
    ``Content-Type`` at all) and ``body``. ``document``: a document, which carries the document trio: an HTML
    page (H-42), and since H-45 an XHTML page, an SVG image, an XML file, any media type ending with ``+xml``."""

    path: str
    content_type: str | None
    body: bytes
    document: bool
    status: int = 200

    @property
    def web_app_page(self) -> bool:
        """H-55 v2: a page of the web app, which adds script, worker and connect sources: ``text/html`` exactly (any case,
        parameters allowed), at a path outside ``/mkdocs`` and ``/api``. Written here, from the contract."""
        media_type = (self.content_type or "").partition(";")[0].strip().lower()
        outside = not (self.path == "/mkdocs" or self.path.startswith("/mkdocs/") or self.path == "/api" or self.path.startswith("/api/"))
        return media_type == "text/html" and outside

    @property
    def api_docs_page(self) -> bool:
        """R5 (wave 5): one of the API docs' two pages: ``text/html`` exactly (any case, parameters allowed) at exactly
        ``/api/v1/docs`` or ``/api/v1/redoc``. Written here, from the contract."""
        media_type = (self.content_type or "").partition(";")[0].strip().lower()
        return media_type == "text/html" and self.path in API_DOCS_PATHS

    @property
    def worker_script(self) -> bool:
        """R4 (wave 4): a JavaScript response under ``/_app/``: ``text/javascript`` or ``application/javascript``, parameters
        ignored, any case, at a path starting with ``/_app/``. Written here, from the contract."""
        media_type = (self.content_type or "").partition(";")[0].strip().lower()
        return media_type in ("text/javascript", "application/javascript") and self.path.startswith("/_app/")


#: Each type at a path where the app serves it, or could, HTML under /mkdocs and /api/ too: the type decides, never the path.
TYPED_ANSWERS: dict[str, TypedAnswer] = {
    # HTML documents: text/html in any case, parameters allowed
    "text-html": TypedAnswer("/", "text/html", PAGE_HTML, document=True),
    "text-html-charset-utf-8": TypedAnswer("/portfolio/overview", "text/html; charset=utf-8", PAGE_HTML, document=True),
    "uppercase-TEXT-HTML": TypedAnswer("/mkdocs/user/", "TEXT/HTML", PAGE_HTML, document=True),
    "mixed-case-with-charset": TypedAnswer(f"{API_V1_PREFIX}/other", "Text/HTML; Charset=UTF-8", PAGE_HTML, document=True),  # R5: /api/v1/docs is one of the API docs' two pages now (section (m))
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


@pytest.mark.asyncio
@pytest.mark.parametrize("typed", TYPED_ANSWERS.values(), ids=list(TYPED_ANSWERS))
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_the_enforced_policy_follows_the_type_of_the_response(mode: Mode, typed: TypedAnswer, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-42/H-45, and since H-55 v2 in every profile: the type alone (with the path telling a web app page from the
    documentation's and the API's HTML) decides the enforced policy: the trio on a document, script, worker and connect
    sources on a web app page (no build here, so no hash), the policy of a worker on a JavaScript response under ``/_app/``
    (R4), ``frame-ancestors`` with frame protection on, nothing else."""
    what = f"GET {typed.path} answered {typed.status} {typed.content_type or 'without Content-Type'} with {mode.describe()}"
    print_section(f"H-42/H-45/H-55 v2 enforced policy by type: {what}")
    configure(monkeypatch, mode, tmp_path)

    reply = await call(wrap(answering(typed)), typed.path)  # SecurityHeadersMiddleware(app) built here, configuration in place

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    print_success(f"✓ {assert_frame_protection(reply, mode, typed.document, what, web_app_page=typed.web_app_page, worker_script=typed.worker_script)}; nosniff and Referrer-Policy")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_an_html_page_keeps_the_policy_its_route_set(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path, value = ROUTE_SETS["content-security-policy"]
    what = f"GET {path} with {mode.describe()}"
    print_section(f"H-42: an HTML page whose route set its own Content-Security-Policy, {value}: {what}")
    page = Case(path, answered(200, HTML, PAGE_HTML), html=True, web_app_html=True)

    reply = await answer(page, mode, tmp_path, monkeypatch)

    policies = reply.values("content-security-policy")
    assert policies == [value], f"{what}: Content-Security-Policy is {policies}; the route's {value!r} must stay, alone, on an HTML page too: never replaced by the middleware's policy, never joined by a second policy"
    expected_frame_options = [FRAME_OPTIONS] if mode.frame_protection else []  # H-55 v2: the policy is enforced in every profile, X-Frame-Options follows the frame protection
    assert reply.values("x-frame-options") == expected_frame_options, f"{what}: X-Frame-Options is {reply.values('x-frame-options')}, wanted {expected_frame_options}"
    print_success(f"✓ the route's {value!r} kept alone; X-Frame-Options {expected_frame_options}")


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

    assert media_types is not None, f"H-45: {SECURITY_MODULE} has no {DOCUMENT_MEDIA_TYPES_NAME}, the media types of a document, which carries the document trio; wanted the frozenset of {sorted(DOCUMENT_MEDIA_TYPES)}"
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
    the web app an SVG or an XHTML document carries the document trio, never the report-only policy."""
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
    print_success(f"✓ no Content-Security-Policy-Report-Only; {assert_frame_protection(reply, mode, typed.document, what)}")


# =============================================================================
# (i) H-45: NO POLICY ON A 304
# =============================================================================

#: The two policies of D5: a 304 gets neither from the middleware (H-45), and keeps the one its route set.
POLICY_HEADERS = ("content-security-policy", "content-security-policy-report-only")


@dataclass(frozen=True)
class Revalidated:
    """What a bare ASGI app answers at ``path``, revalidated or not: ``headers`` as written, the same on its 200 and on its
    304, an ``etag`` among them; ``body`` on the 200 only. As a 200 it is a ``document`` (the document trio among its
    enforced directives) or not, and ``web_app_html`` (an HTML page of the web app: the report-only policy's place) or not."""

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
    """Barrier: ``revalidated`` answered 200 carries the policies ``mode`` gives it: the route's own, else the enforced
    policy of its response (H-55 v2: the trio on a document, a web app page's sources, frame-ancestors with frame
    protection on, none for a non-document without it), and the middleware's report-only policy on an HTML page of the
    web app with it on."""
    own_policy = revalidated.own("content-security-policy")
    if own_policy:
        assert reply.values("content-security-policy") == own_policy, f"barrier: {what}: Content-Security-Policy is {reply.values('content-security-policy')}, not the route's own {own_policy}: the 304 would test the harness, not the guard"
    else:
        assert_frame_protection(reply, mode, revalidated.document, f"barrier: {what}", web_app_page=revalidated.web_app_html)  # the 304 would test the harness, not the guard
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
    cached page's policy: the middleware adds neither policy to a 304, in every configuration; the rest as ever."""
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
    #: R4: a JavaScript file under /_app/, whose 200 carries the policy of a worker (its 304 none).
    worker_script: bool = False


MOUNTED_FILES: dict[str, MountedFile] = {
    "javascript-chunk": MountedFile("/_app/immutable/chunks/a1b2.js", JAVASCRIPT, CHUNK_JS, document=False, worker_script=True),
    "svg-image": MountedFile(LOGO_SVG_PATH, SVG, LOGO_SVG, document=True),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("mounted", MOUNTED_FILES.values(), ids=list(MOUNTED_FILES))
async def test_the_real_304_of_the_app_mount_carries_no_policy(mounted: MountedFile, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-45, through the stack in managed: the /_app mount (ImmutableStaticFiles, the one part of the app answering 304)
    revalidates a file of the build; its 200 carries the policy of its type (the document trio on the SVG, a document; the policy
    of a worker on the JavaScript chunk, R4), its 304 none."""
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
    enforced = assert_frame_protection(first, mode, mounted.document, what, worker_script=mounted.worker_script)
    assert first.values("content-security-policy-report-only") == [], f"{what}: Content-Security-Policy-Report-Only is {first.values('content-security-policy-report-only')}, wanted none: {first.media_type!r} is not the web app's HTML"
    for name in POLICY_HEADERS:
        assert again.values(name) == [], f"{again_what}: {name} is {again.values(name)}, wanted none; H-45: the browser freshens its cached copy, whose policy is {first.values('content-security-policy')}, with the header fields of this 304 (RFC 9111, 3.2)"
    assert again.values("x-frame-options") == [FRAME_OPTIONS], f"{again_what}: X-Frame-Options is {again.values('x-frame-options')}, wanted exactly one, {FRAME_OPTIONS!r}: frame protection is on, and a 304 gets it as any answer does"
    print_success(f"✓ the 200: {enforced}; its 304, {again.values('content-type') or 'without Content-Type'}: X-Frame-Options and no policy")


# =============================================================================
# (j) H-52: spa_inline_script_hashes, PURE
# =============================================================================

#: H-52: names read when a test runs, as DOCUMENT_MEDIA_TYPES_NAME is: before H-52 their tests fail naming H-52, the rest still runs.
SPA_HASHES_NAME = "spa_inline_script_hashes"
REPORT_ONLY_POLICY_FUNCTION_NAME = "report_only_policy"
CSP_REPORT_ONLY_POLICY_NAME = "CSP_REPORT_ONLY_POLICY"
#: A CSP hash source: ``'sha256-``, the base64 of a SHA-256 digest (43 characters and a ``=``), ``'``.
SHA256_SOURCE = re.compile(r"'sha256-[A-Za-z0-9+/]{43}='")
#: A published vector, the CSP specification's own example: the expression allowing this inline script.
KNOWN_SCRIPT = "alert('Hello, world.');"
KNOWN_SOURCE = "'sha256-qznLcsROx4GACP2dm0UCKCzCG+HiZ1guq6ZZDob/Tng='"
#: More inline scripts: a module, a data block, text beyond ASCII, lines whose ends the parser rewrites (then a CR and a
#: CR LF where the blank line was), the text of a script a src makes external, one inside a comment, one in a subfolder.
MODULE_SCRIPT = 'import { start } from "./_app/immutable/entry/start.a1b2.js";\nstart(document.body);'
DATA_BLOCK = '{"type":"data","nodes":[{"type":"data","data":{"theme":"dark"}}]}'
NON_ASCII_SCRIPT = 'document.title = "LibreFolio — il portafoglio: 1 000 €, Grüße, 日本語";'
LINES_SCRIPT = "\n  const lines = [1, 2];\n\n  lines.forEach((line) => console.log(line));\n"
CR_CRLF_SCRIPT = LINES_SCRIPT.replace("\n\n", "\r\r\n")
NEVER_RUN = 'console.log("never run: a src wins over the text")'
COMMENTED_OUT = 'alert("commented out")'
NESTED_SCRIPT = "console.log('a page in a subfolder')"
#: A service worker of the build: JavaScript, never a page.
SW_JS = b"self.addEventListener('fetch', (event) => event.respondWith(fetch(event.request)));\n"
#: A page in Latin-1, not UTF-8: its é is the one byte E9, which opens a UTF-8 sequence the next byte does not continue.
LATIN_1_PAGE = b"<!doctype html>\n<html><body><script>document.title = 'caf\xe9';</script></body></html>\n"
#: Logged through a logger of static_site's name before a call: the barrier proving that what the module logs reaches us.
LOG_CANARY = "H-52 canary: what static_site logs reaches this test"


def page_of(*parts: str) -> bytes:
    """A page of a build, in UTF-8: a doctype, a title, then ``parts`` as written, one per line."""
    return ("<!doctype html>\n<html>\n<head><title>page</title></head>\n<body>\n" + "\n".join(parts) + "\n</body>\n</html>\n").encode()


def one_page(*parts: str) -> tuple[tuple[str, bytes], ...]:
    """The files of a build of one page, index.html, holding ``parts``."""
    return (("index.html", page_of(*parts)),)


#: A page whose one inline script is the published vector's; one whose script is never read, as it sits in a subfolder.
KNOWN_PAGE = page_of(f"<script>{KNOWN_SCRIPT}</script>")
NESTED_PAGE = page_of(f"<script>{NESTED_SCRIPT}</script>")


def spa_hashes_function() -> Callable[[Path], tuple[str, ...]]:
    """``static_site.spa_inline_script_hashes``, read by name when a test runs: before H-52 the test asking for it fails,
    naming H-52, while the rest of the file runs."""
    function = getattr(static_site, SPA_HASHES_NAME, None)
    assert callable(function), f"H-52: {static_site.__name__} has no function {SPA_HASHES_NAME}(build_dir), the CSP hash expression of every inline script of the build's pages, for the middleware's script-src"
    return function


def inline_script_sources(build_dir: Path, what: str) -> tuple[str, ...]:
    """``spa_inline_script_hashes(build_dir)``, its form checked whatever the build: a tuple of CSP hash sources,
    ``'sha256-'`` and the base64 of a SHA-256 digest between single quotes, each once, sorted."""
    found = spa_hashes_function()(build_dir)
    assert isinstance(found, tuple), f"{what}: returned {type(found).__name__} {found!r}, not a tuple"
    malformed = [source for source in found if not (isinstance(source, str) and SHA256_SOURCE.fullmatch(source))]
    assert not malformed, f"{what}: not CSP hash sources, 'sha256-' and the base64 of a SHA-256 digest between single quotes: {malformed}"
    assert list(found) == sorted(set(found)), f"{what}: {found} is not each expression once, sorted"
    return found


@contextmanager
def static_site_warnings(caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[], list[tuple[str, str]]]]:
    """What ``static_site`` logs inside the block as a warning or worse, read both ways a module of the app may log: the
    structlog events (``capture_logs``) and the stdlib records (``caplog``). Each behind a barrier, as in
    ``test_backup_outcome``: a canary through a logger of the module's name reaches it, or "one warning" would count
    nothing. Yields a function listing (level, message) of what was logged since, the canary left out."""
    name = static_site.__name__
    monkeypatch.setattr(logging.getLogger(name), "disabled", False)
    caplog.set_level(logging.WARNING)
    caplog.set_level(logging.WARNING, logger=name)
    with capture_logs() as events:
        get_logger(name).warning(LOG_CANARY)
        logging.getLogger(name).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: a structlog logger of {name} does not reach capture_logs: {events}"
        assert any(record.name == name and record.getMessage() == LOG_CANARY for record in caplog.records), f"barrier: a stdlib logger of {name} does not reach caplog"

        def logged() -> list[tuple[str, str]]:
            structured = [(str(event.get("log_level")), str(event.get("event"))) for event in events if event.get("event") != LOG_CANARY and event.get("log_level") in ("warning", "error", "exception", "critical")]
            return structured + [(record.levelname.lower(), record.getMessage()) for record in caplog.records if record.levelno >= logging.WARNING and record.getMessage() != LOG_CANARY]

        yield logged


@dataclass(frozen=True)
class InlineBuild:
    """A build for ``spa_inline_script_hashes``: its files (path in the build, content), the text of every inline script it
    must hash as the browser parses it (LF line ends), and why. What it must return is computed here: the expressions of
    ``scripts``, each once, sorted."""

    files: tuple[tuple[str, bytes], ...]
    scripts: tuple[str, ...]
    why: str

    @property
    def expected(self) -> tuple[str, ...]:
        return tuple(sorted({sha256_source(script) for script in self.scripts}))


#: H-52: a build for each rule of spa_inline_script_hashes.
INLINE_BUILDS: dict[str, InlineBuild] = {
    "classic-inline-script": InlineBuild(one_page(f"<script>{KNOWN_SCRIPT}</script>"), (KNOWN_SCRIPT,), "an inline script is hashed"),
    "type-module": InlineBuild(one_page(f'<script type="module">{MODULE_SCRIPT}</script>'), (MODULE_SCRIPT,), "an inline module is an inline script"),
    "src-skipped": InlineBuild(one_page(f'<script src="/_app/start.js">{NEVER_RUN}</script>', '<script type="module" src="/_app/app.js"></script>', f"<script>{KNOWN_SCRIPT}</script>"), (KNOWN_SCRIPT,), "a script with a src is external: its text never runs, never hashed"),
    "data-block-hashed": InlineBuild(one_page(f'<script type="application/json" data-sveltekit-fetched data-url="/api/v1/things">{DATA_BLOCK}</script>'), (DATA_BLOCK,), "a script without a src is hashed whatever its type: a data block's hash is harmless"),
    "same-script-in-two-files": InlineBuild((("a.html", KNOWN_PAGE), ("b.html", KNOWN_PAGE)), (KNOWN_SCRIPT,), "a script in two pages is one expression"),
    "same-script-twice-in-a-page": InlineBuild(one_page(f"<script>{KNOWN_SCRIPT}</script>", f"<script>{KNOWN_SCRIPT}</script>"), (KNOWN_SCRIPT,), "a script twice in a page is one expression"),
    "todays-build": InlineBuild((*FAKE_BUILD_PAGES.items(), ("sw.js", SW_JS), ("robots.txt", ROBOTS_TXT)), build_scripts(BUILD_ID), "today's pages: the anti-FOUC once though in two of them, the two bootstraps, offline.html's script; sw.js is no page"),
    "crlf-line-ends": InlineBuild((("index.html", page_of(f"<script>{LINES_SCRIPT}</script>").replace(b"\n", b"\r\n")),), (LINES_SCRIPT,), "a CR LF is a LF, as the HTML parser makes it"),
    "lone-cr-line-ends": InlineBuild((("index.html", page_of(f"<script>{LINES_SCRIPT}</script>").replace(b"\n", b"\r")),), (LINES_SCRIPT,), "a lone CR is a LF, as the HTML parser makes it"),
    "cr-then-crlf": InlineBuild(one_page(f"<script>{CR_CRLF_SCRIPT}</script>"), (LINES_SCRIPT,), "a CR then a CR LF are two LF, not three, as the HTML parser makes them"),
    "non-ascii-text": InlineBuild(one_page(f"<script>{NON_ASCII_SCRIPT}</script>"), (NON_ASCII_SCRIPT,), "the text is hashed as its UTF-8 bytes"),
    "greater-than-in-a-quoted-attribute": InlineBuild(one_page(f'<script data-x="a>b">{KNOWN_SCRIPT}</script>'), (KNOWN_SCRIPT,), "a > in a quoted attribute value ends no start tag: the text is the script's alone"),
    "script-in-an-html-comment": InlineBuild(one_page(f"<!-- <script>{COMMENTED_OUT}</script> -->", f"<script>{KNOWN_SCRIPT}</script>"), (KNOWN_SCRIPT,), "a script inside an HTML comment is no script"),
    "uppercase-SCRIPT": InlineBuild(one_page(f"<SCRIPT>{KNOWN_SCRIPT}</SCRIPT>", f'<SCRIPT SRC="/_app/start.js">{NEVER_RUN}</SCRIPT>'), (KNOWN_SCRIPT,), "names ignore case: <SCRIPT> is a script, SRC a src"),
    "pages-in-subfolders-not-read": InlineBuild((("index.html", KNOWN_PAGE), ("_app/immutable/nodes/page.html", NESTED_PAGE), ("data/page.html", NESTED_PAGE)), (KNOWN_SCRIPT,), "only the pages at the top of the build are read, never one in a subfolder"),
}
#: H-52: builds without a page at their top, each giving ``()``: missing (``None``: no folder at all), an empty folder,
#: other files only (JavaScript among them), pages in subfolders only.
NO_PAGE_BUILDS: dict[str, tuple[tuple[str, bytes], ...] | None] = {
    "missing": None,
    "empty-folder": (),
    "other-files-only": (("sw.js", SW_JS), ("robots.txt", ROBOTS_TXT), ("favicon.png", FAVICON_PNG), ("manifest.json", b'{"name": "LibreFolio"}')),
    "pages-in-subfolders-only": (("_app/immutable/nodes/page.html", NESTED_PAGE), ("data/page.html", NESTED_PAGE)),
}
#: H-52: a build whose middle page by name, b.html, cannot be decoded, between two pages in UTF-8.
UNDECODABLE_BUILD: dict[str, bytes] = {"a.html": KNOWN_PAGE, "b.html": LATIN_1_PAGE, "c.html": page_of(f'<script type="module">{MODULE_SCRIPT}</script>')}


class TestSpaInlineScriptHashes:
    """H-52, (j): ``static_site.spa_inline_script_hashes(build_dir)``, pure, on builds written under ``tmp_path``. Every
    answer is checked for its form first (``inline_script_sources``): a tuple of ``'sha256-...'`` sources, single quotes
    included, each once, sorted. Red before H-52, every one: the function does not exist."""

    @pytest.mark.parametrize("build", INLINE_BUILDS.values(), ids=list(INLINE_BUILDS))
    def test_every_inline_script_of_a_top_level_page_is_hashed_and_nothing_else(self, build: InlineBuild, tmp_path: Path) -> None:
        what = f"{SPA_HASHES_NAME} on a build of {[name for name, _ in build.files]}"
        print_section(f"H-52: {what}")
        build_dir = _write_tree(tmp_path / "build", dict(build.files))

        found = inline_script_sources(build_dir, what)

        missing, unexpected = sorted(set(build.expected) - set(found)), sorted(set(found) - set(build.expected))
        assert found == build.expected, f"{what}: {found}, not {build.expected}, as {build.why}: missing {missing}, unexpected {unexpected}"
        print_success(f"✓ {build.why}: {found}")

    def test_a_published_vector(self, tmp_path: Path) -> None:
        what = f"{SPA_HASHES_NAME} on a page whose one inline script is {KNOWN_SCRIPT!r}"
        print_section(f"H-52: {what}")
        # The barrier: this file's own computation, which every other case expects, gives the published expression
        assert sha256_source(KNOWN_SCRIPT) == KNOWN_SOURCE, f"barrier: sha256_source({KNOWN_SCRIPT!r}) is {sha256_source(KNOWN_SCRIPT)}, not the published {KNOWN_SOURCE}"
        build_dir = _write_tree(tmp_path / "build", {"index.html": KNOWN_PAGE})

        found = inline_script_sources(build_dir, what)

        assert found == (KNOWN_SOURCE,), f"{what}: {found}, not ({KNOWN_SOURCE},), the CSP specification's own example"
        print_success(f"✓ {KNOWN_SOURCE}")

    @pytest.mark.parametrize("build", list(NO_PAGE_BUILDS))
    def test_no_build_or_no_page_at_its_top_gives_no_hash(self, build: str, tmp_path: Path) -> None:
        what = f"{SPA_HASHES_NAME} on a build {build}"
        print_section(f"H-52: {what}")
        with_a_page = _write_tree(tmp_path / "with-a-page", {"index.html": KNOWN_PAGE})
        assert inline_script_sources(with_a_page, f"{SPA_HASHES_NAME} on a build of one page") == (KNOWN_SOURCE,), "barrier: a build of one page gives its one expression, so the () below is the build's doing"
        build_dir, files = tmp_path / "build", NO_PAGE_BUILDS[build]
        if files is not None:
            build_dir.mkdir()
            _write_tree(build_dir, dict(files))

        found = inline_script_sources(build_dir, what)

        assert found == (), f"{what}: {found}, wanted (): no page at the top of the build, no inline script to allow"
        print_success("✓ ()")

    def test_an_undecodable_page_is_skipped_with_one_warning_and_the_others_still_count(self, tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
        what = f"{SPA_HASHES_NAME} on a build whose b.html is in Latin-1, between a.html and c.html in UTF-8"
        print_section(f"H-52: {what}")
        build_dir = _write_tree(tmp_path / "build", UNDECODABLE_BUILD)
        with pytest.raises(UnicodeDecodeError):  # the barrier: b.html really is no UTF-8
            LATIN_1_PAGE.decode("utf-8")

        with static_site_warnings(caplog, monkeypatch) as logged:
            found = inline_script_sources(build_dir, what)
            warned = logged()

        expected = tuple(sorted({sha256_source(KNOWN_SCRIPT), sha256_source(MODULE_SCRIPT)}))
        assert found == expected, f"{what}: {found}, not {expected}: b.html is skipped, a.html and c.html still count"
        assert [level for level, _ in warned] == ["warning"], f"{what}: logged {warned} as a warning or worse, wanted exactly one warning, for b.html: skipped, and the server starts all the same"
        print_success(f"✓ {found}; one warning: {warned[0][1]}")


# =============================================================================
# (j) H-52: report_only_policy, CSP_REPORT_ONLY_POLICY WITH THE BUILD'S HASHES
# =============================================================================

#: H-52: two expressions given in an order that is not sorted, so that the order given can be told from a sort.
GIVEN_SOURCES = tuple(sorted({sha256_source(KNOWN_SCRIPT), sha256_source(MODULE_SCRIPT)}, reverse=True))
#: H-52: how they may be given, report_only_policy taking any ``Iterable[str]``: a tuple (as spa_inline_script_hashes
#: returns them), a list, an iterator that can be read once.
CONTAINERS: dict[str, Callable[[tuple[str, ...]], Iterable[str]]] = {"tuple": tuple, "list": list, "iterator": iter}


def report_only_policy_function() -> Callable[[Iterable[str]], str]:
    """``security_headers.report_only_policy``, read by name when a test runs: before H-52 the test asking for it fails,
    naming H-52, while the rest of the file runs."""
    function = getattr(importlib.import_module(SECURITY_MODULE), REPORT_ONLY_POLICY_FUNCTION_NAME, None)
    assert callable(function), f"H-52: {SECURITY_MODULE} has no function {REPORT_ONLY_POLICY_FUNCTION_NAME}(script_hashes), {CSP_REPORT_ONLY_POLICY_NAME} with the given hash expressions appended to script-src"
    return function


def csp_report_only_policy() -> str:
    """``security_headers.CSP_REPORT_ONLY_POLICY``, read by name when a test runs: the report-only policy without a hash."""
    policy = getattr(importlib.import_module(SECURITY_MODULE), CSP_REPORT_ONLY_POLICY_NAME, None)
    assert isinstance(policy, str), f"{SECURITY_MODULE} has no str {CSP_REPORT_ONLY_POLICY_NAME}, the report-only policy without a hash: {policy!r}"
    return policy


@pytest.mark.parametrize("given", list(CONTAINERS))
def test_report_only_policy_given_no_hash_is_the_constant_whose_script_src_has_report_sample(given: str) -> None:
    what = f"{REPORT_ONLY_POLICY_FUNCTION_NAME}(an empty {given})"
    print_section(f"H-52: {what}")
    constant = csp_report_only_policy()

    policy = report_only_policy_function()(CONTAINERS[given](()))

    assert policy == constant, f"{what} is {policy!r}, not {CSP_REPORT_ONLY_POLICY_NAME}, {constant!r}: given no hash, the policy is the constant itself"
    script_src = written_directives(constant, CSP_REPORT_ONLY_POLICY_NAME).get("script-src")
    assert script_src == SCRIPT_SRC, f"{CSP_REPORT_ONLY_POLICY_NAME}: script-src is {script_src}, not {SCRIPT_SRC}: H-52 adds 'report-sample', and no hash"
    print_success(f"✓ {CSP_REPORT_ONLY_POLICY_NAME}: {constant}")


@pytest.mark.parametrize("given", list(CONTAINERS))
def test_report_only_policy_appends_the_hashes_to_script_src_in_the_order_given(given: str) -> None:
    what = f"{REPORT_ONLY_POLICY_FUNCTION_NAME}({given}: {list(GIVEN_SOURCES)})"
    print_section(f"H-52: {what}")
    assert list(GIVEN_SOURCES) != sorted(GIVEN_SOURCES), f"barrier: {GIVEN_SOURCES} are given sorted: the order given could not be told from a sort"
    constant = written_directives(csp_report_only_policy(), CSP_REPORT_ONLY_POLICY_NAME)
    expected = {name: SCRIPT_SRC + GIVEN_SOURCES if name == "script-src" else sources for name, sources in constant.items()}

    policy = report_only_policy_function()(CONTAINERS[given](GIVEN_SOURCES))

    assert isinstance(policy, str), f"{what} returned {type(policy).__name__} {policy!r}, not a str"
    found = written_directives(policy, what)
    assert found.get("script-src") == SCRIPT_SRC + GIVEN_SOURCES, f"{what}: script-src is {found.get('script-src')} in {policy!r}, not {SCRIPT_SRC + GIVEN_SOURCES}: {SCRIPT_SRC}, then the expressions in the order given"
    assert list(found.items()) == list(expected.items()), f"{what}: {policy!r} is not {CSP_REPORT_ONLY_POLICY_NAME} with the expressions in script-src, every other directive unchanged and in place: {list(constant.items())}"
    print_success(f"✓ script-src {found['script-src']}; every other directive as in {CSP_REPORT_ONLY_POLICY_NAME}")


# =============================================================================
# (j) H-52, AND H-55 v2 STEP 1: THE MIDDLEWARE HASHES THE BUILD AS IT IS NOW (a cache keyed by the build's signature)
# =============================================================================

#: H-52: paths at which the bare app answers an HTML page: the web app's, which carry the report-only policy with the
#: build's hashes (and, H-55 v2, the enforced one); the documentation's and the API's, which carry neither.
WEB_APP_PAGE_PATHS = ("/", "/portfolio/overview", "/200.html", "/offline.html")
NOT_WEB_APP_PAGE_PATHS = ("/mkdocs", "/mkdocs/user/", f"{API_V1_PREFIX}/docs", f"{API_V1_PREFIX}/redoc")


def spy_on_spa_hashes(monkeypatch: pytest.MonkeyPatch) -> list[Any]:
    """Watch ``spa_inline_script_hashes``: a spy answering as the real one takes its place in ``static_site``, and in the
    security module too when that module holds the name (imported with ``from``). Returns the list of the build folders
    it is called with, in order."""
    real = spa_hashes_function()
    calls: list[Any] = []

    def spy(*args: Any, **kwargs: Any) -> tuple[str, ...]:
        calls.append(args[0] if args else kwargs.get("build_dir"))
        return real(*args, **kwargs)

    monkeypatch.setattr(static_site, SPA_HASHES_NAME, spy)
    security_module = importlib.import_module(SECURITY_MODULE)
    if hasattr(security_module, SPA_HASHES_NAME):
        monkeypatch.setattr(security_module, SPA_HASHES_NAME, spy)
    return calls


def built_on(build_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Callable:
    """The middleware around ``html_page``, built now on the build ``build_dir``: ``static_site.FRONTEND_BUILD_DIR`` names
    it while the middleware is built, as it does when the server starts."""
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build_dir)
    return wrap(html_page)


async def page_report_only(middleware: Callable, path: str, what: str) -> list[str]:
    """The ``Content-Security-Policy-Report-Only`` lines ``middleware`` sent with the bare app's HTML page at ``path``,
    past the barriers: the answer is the bare app's page, and the middleware saw it."""
    reply = await call(middleware, path)
    answered(200, HTML, PAGE_HTML)(reply)
    assert_always_on(reply, f"GET {path}, {what}")
    return reply.values("content-security-policy-report-only")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", REPORT_ONLY_MODES.values(), ids=list(REPORT_ONLY_MODES))
async def test_the_build_is_hashed_once_per_signature_and_only_the_web_apps_pages_carry_it(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-52, changed by H-55 v2: no longer «once, when the middleware is built» (a build made while the server runs left a
    blank page): the build is read for the first web app page and not again while its signature stays; the report-only
    policy and the enforced one carry the same hashes there, the documentation's and the API's pages neither."""
    what = f"the middleware built with {mode.describe()} on a build of {sorted(FAKE_BUILD_PAGES)}"
    print_section(f"H-52/H-55 v2: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = _write_tree(tmp_path / "build", FAKE_BUILD_PAGES)
    calls = spy_on_spa_hashes(monkeypatch)

    middleware = built_on(build_dir, monkeypatch)

    expected = SCRIPT_SRC + FAKE_BUILD_SOURCES
    for path in WEB_APP_PAGE_PATHS:
        reply = await call(middleware, path)
        answered(200, HTML, PAGE_HTML)(reply)
        assert_always_on(reply, f"GET {path}, {what}")
        policies = reply.values("content-security-policy-report-only")
        script_src = written_directives(policies[0], f"GET {path}, {what}").get("script-src") if len(policies) == 1 else policies
        assert script_src == expected, f"GET {path}, {what}: carries {policies}, not one policy whose script-src is {expected}: {SCRIPT_SRC}, then the hash of every inline script of the build, each once, sorted"
        enforced = reply.values("content-security-policy")
        enforced_script_src = written_directives(enforced[0], f"GET {path}, {what}").get("script-src") if len(enforced) == 1 else enforced
        assert enforced_script_src == expected, f"GET {path}, {what}: the enforced policy is {enforced}, not one whose script-src is {expected} (H-55 v2: the same hashes as the report-only policy)"
    for path in NOT_WEB_APP_PAGE_PATHS:
        policies = await page_report_only(middleware, path, what)
        assert policies == [], f"GET {path}, {what}: Content-Security-Policy-Report-Only is {policies}, wanted none: not a page of the web app"
    assert calls == [build_dir], f"{what}: {SPA_HASHES_NAME} was called with {calls}, not once with {build_dir}: the build is read for the first web app page, and not again while its signature (name, mtime, size of every *.html) stays"
    print_success(f"✓ the build read once; script-src {expected} on {WEB_APP_PAGE_PATHS}, no report-only policy on {NOT_WEB_APP_PAGE_PATHS}")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", REPORT_ONLY_OFF_MODES.values(), ids=list(REPORT_ONLY_OFF_MODES))
async def test_with_the_report_only_policy_off_the_enforced_policy_still_carries_the_build_hashes(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Replaces «with the report-only policy off the build is never read» (H-52): since H-55 v2 the enforced policy of a web
    app page needs the build's hashes in every profile, whatever the report-only switch says."""
    what = f"the middleware built with {mode.describe()} on a build of {sorted(FAKE_BUILD_PAGES)}"
    print_section(f"H-55 v2: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = _write_tree(tmp_path / "build", FAKE_BUILD_PAGES)
    calls = spy_on_spa_hashes(monkeypatch)

    middleware = built_on(build_dir, monkeypatch)
    reply = await call(middleware, "/")

    answered(200, HTML, PAGE_HTML)(reply)
    assert_always_on(reply, f"GET /, {what}")
    assert reply.values("content-security-policy-report-only") == [], f"{what}: Content-Security-Policy-Report-Only is {reply.values('content-security-policy-report-only')}, yet the policy is off"
    enforced = reply.values("content-security-policy")
    script_src = written_directives(enforced[0], what).get("script-src") if len(enforced) == 1 else enforced
    assert script_src == SCRIPT_SRC + FAKE_BUILD_SOURCES, f"{what}: the enforced policy is {enforced}, not one whose script-src is {SCRIPT_SRC + FAKE_BUILD_SOURCES}: H-55 v2, the hashes of the build now, with the report-only policy off too"
    assert calls == [build_dir], f"{what}: {SPA_HASHES_NAME} was called with {calls}, not once with {build_dir}"
    print_success(f"✓ no report-only policy; enforced script-src {script_src}")


#: H-52: builds without an inline script to allow: none at all (``None``), a folder without a page, a page that cannot be
#: decoded (skipped with a warning).
SCRIPTLESS_BUILDS: dict[str, dict[str, bytes] | None] = {
    "missing": None,
    "without-a-page": {"robots.txt": ROBOTS_TXT, "favicon.png": FAVICON_PNG},
    "with-an-undecodable-page-only": {"index.html": LATIN_1_PAGE},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("build", list(SCRIPTLESS_BUILDS))
@pytest.mark.parametrize("mode", REPORT_ONLY_MODES.values(), ids=list(REPORT_ONLY_MODES))
async def test_a_build_without_an_inline_script_gives_the_policy_without_a_hash(mode: Mode, build: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """H-52, and since H-55 v2: the report-only policy is the constant with, in ``connect-src``, the connect sources of the
    configuration (``https://api.github.com`` in the self-hosted profile, nothing in the managed one: no public URL
    here), and the enforced policy of the page has a ``script-src`` without a hash."""
    what = f"the middleware built with {mode.describe()} on a build {build}"
    print_section(f"H-52/H-55 v2: {what}")
    configure(monkeypatch, mode, tmp_path)
    files = SCRIPTLESS_BUILDS[build]
    build_dir = tmp_path / "build" if files is None else _write_tree(tmp_path / "build", files)
    constant = written_directives(csp_report_only_policy(), CSP_REPORT_ONLY_POLICY_NAME)
    expected = {name: CONNECT_SRC + mode.connect_sources if name == "connect-src" else sources for name, sources in constant.items()}

    middleware = built_on(build_dir, monkeypatch)  # the server starts all the same
    reply = await call(middleware, "/")
    answered(200, HTML, PAGE_HTML)(reply)
    assert_always_on(reply, f"GET /, {what}")
    policies = reply.values("content-security-policy-report-only")

    assert len(policies) == 1, f"{what}: {len(policies)} Content-Security-Policy-Report-Only on GET /: {policies}"
    found = written_directives(policies[0], what)
    assert found.get("script-src") == SCRIPT_SRC, f"{what}: script-src is {found.get('script-src')}, not {SCRIPT_SRC}: H-52, 'report-sample' and no hash, the build having no inline script"
    assert list(found.items()) == list(expected.items()), f"{what}: the policy is {policies[0]!r}, not {CSP_REPORT_ONLY_POLICY_NAME} directive by directive with the connect sources in connect-src, {list(expected.items())}"
    assert_frame_protection(reply, mode, True, f"GET /, {what}", web_app_page=True)  # H-55 v2: script-src without a hash, connect-src as the profile gives it
    print_success(f"✓ {CSP_REPORT_ONLY_POLICY_NAME}, no hash, the connect sources {mode.connect_sources}: {policies[0]}")


# =============================================================================
# (k) H-55 v2, STEP 1: THE INLINE-SCRIPT HASHES FOLLOW THE BUILD
# =============================================================================
#: The hashes the middleware puts in ``script-src`` (the enforced header, and the report-only one when on) are those of the
#: build as it is now, through a cache keyed by the build's signature: for every ``*.html`` directly in
#: ``static_site.FRONTEND_BUILD_DIR`` whose name does not start with ``.``, ``(name, st_mtime_ns, st_size)``. Same signature,
#: no page read again (``static_site.spa_inline_script_hashes`` not called: the middleware looks it up as a module attribute
#: at each cache miss, so ``spy_on_spa_hashes`` counts its calls); another signature, the hashes recomputed and used from that
#: response on; a page of the last good signature missing (the build being written), the last good hashes stay and the next
#: web app response checks again; no build at all, no hash; only web app HTML responses look at the build.
#: Each case builds its own middleware: the tests assume a middleware starts with no «last good» hashes of its own.

#: Seconds of the modification time a build's files get: a signature never depends on how fast a test wrote two builds.
STAMP_0, STAMP_1 = 1_700_000_000, 1_700_001_000
NANOSECONDS = 10**9
#: The modes of the hash cases: self-hosted, enforced policy alone; managed, enforced and report-only.
HASH_MODES = {name: MODES[name] for name in ("selfhosted-nothing-set", "managed")}
#: An inline script written to a build after the middleware read it, and the expression allowing it.
EXTRA_SCRIPT = "document.title = 'a page written later';"
EXTRA_PAGE = page_of(f"<script>{EXTRA_SCRIPT}</script>")
EXTRA_SOURCE = sha256_source(EXTRA_SCRIPT)


def write_build(build_dir: Path, pages: dict[str, bytes], stamp: int) -> Path:
    """``pages`` written under ``build_dir`` and their modification time set to ``stamp`` seconds: the signature of a file
    (name, mtime, size) changes when a case says so, never by the clock's grain."""
    _write_tree(build_dir, pages)
    for relative in pages:
        os.utime(build_dir / relative, ns=(stamp * NANOSECONDS, stamp * NANOSECONDS))
    return build_dir


def script_src_of(reply: Reply, field: str, what: str) -> tuple[str, ...]:
    """The hashes after ``SCRIPT_SRC`` in the ``script-src`` of the one ``field`` policy ``reply`` carries."""
    values = reply.values(field)
    assert len(values) == 1, f"{what}: {field} is {values}, wanted exactly one policy (H-55 v2: the enforced policy of a web app page, with the hashes of the build now)"
    script_src = written_directives(values[0], what).get("script-src")
    assert script_src is not None and script_src[: len(SCRIPT_SRC)] == SCRIPT_SRC, f"{what}: the script-src of {field} is {script_src}, not {SCRIPT_SRC} then the hashes of the build"
    return script_src[len(SCRIPT_SRC) :]


async def hashes_now(middleware: Callable, mode: Mode, what: str, path: str = "/") -> tuple[str, ...]:
    """The hashes the web app page at ``path`` carries now, in the enforced policy and, when the report-only policy is on,
    the same ones in that policy: ``middleware`` answered the bare app's page and saw it."""
    reply = await call(middleware, path)
    answered(200, HTML, PAGE_HTML)(reply)
    assert_always_on(reply, f"GET {path}, {what}")
    enforced = script_src_of(reply, "content-security-policy", f"GET {path}, {what}")
    if mode.csp_report_only:
        report_only = script_src_of(reply, "content-security-policy-report-only", f"GET {path}, {what}")
        assert report_only == enforced, f"GET {path}, {what}: the report-only policy has the hashes {report_only}, the enforced one {enforced}: both are those of the build now"
    return enforced


@pytest.mark.asyncio
@pytest.mark.parametrize("before", ["another-build-was-there", "no-build-yet"])
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_a_build_written_after_the_middleware_was_built_is_the_one_hashed(mode: Mode, before: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()} ({before}), then the build {NEXT_BUILD_ID} written"
    print_section(f"H-55 v2 step 1: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = tmp_path / "build"
    if before == "another-build-was-there":
        write_build(build_dir, build_pages(BUILD_ID), STAMP_0)
    middleware = built_on(build_dir, monkeypatch)

    write_build(build_dir, build_pages(NEXT_BUILD_ID), STAMP_1)  # a build made while the server runs
    found = await hashes_now(middleware, mode, what)

    assert found == build_sources(NEXT_BUILD_ID), f"{what}: the hashes are {found}, not those of the build as it is now, {build_sources(NEXT_BUILD_ID)}: a build made while the server runs must not leave a blank page under the enforced policy"
    print_success(f"✓ the hashes of the build now: {found}")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_with_the_same_signature_no_page_is_read_again(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()} on the build {BUILD_ID}, untouched"
    print_section(f"H-55 v2 step 1: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    calls = spy_on_spa_hashes(monkeypatch)
    middleware = built_on(build_dir, monkeypatch)

    seen = [await hashes_now(middleware, mode, what, path) for path in WEB_APP_PAGE_PATHS * 2]

    assert seen == [build_sources(BUILD_ID)] * len(seen), f"{what}: the hashes are {seen}, not always those of the build, {build_sources(BUILD_ID)}"
    assert calls == [build_dir], f"{what}: {SPA_HASHES_NAME} was called with {calls} for {len(seen)} web app responses, wanted once with {build_dir}: a build whose signature (name, mtime, size of every *.html) did not change is not read again"
    print_success(f"✓ {len(seen)} responses, the build read once")


async def _touch_a_page(build_dir: Path) -> tuple[tuple[str, ...], bool]:
    os.utime(build_dir / "index.html", ns=(STAMP_1 * NANOSECONDS, STAMP_1 * NANOSECONDS))  # same text, a newer mtime
    return build_sources(BUILD_ID), True


async def _resize_a_page(build_dir: Path) -> tuple[tuple[str, ...], bool]:
    page = build_dir / "index.html"
    page.write_bytes(page.read_bytes().replace(b"</body>", f"<script>{EXTRA_SCRIPT}</script></body>".encode()))
    os.utime(page, ns=(STAMP_0 * NANOSECONDS, STAMP_0 * NANOSECONDS))  # the mtime it had: only the size changed
    return tuple(sorted({*build_sources(BUILD_ID), EXTRA_SOURCE})), True


async def _add_a_page(build_dir: Path) -> tuple[tuple[str, ...], bool]:
    write_build(build_dir, {"extra.html": EXTRA_PAGE}, STAMP_0)
    return tuple(sorted({*build_sources(BUILD_ID), EXTRA_SOURCE})), True


async def _write_the_next_build(build_dir: Path) -> tuple[tuple[str, ...], bool]:
    write_build(build_dir, build_pages(NEXT_BUILD_ID), STAMP_1)  # same sizes as the first build: only the mtime says it changed
    return build_sources(NEXT_BUILD_ID), True


async def _add_a_hidden_page(build_dir: Path) -> tuple[tuple[str, ...], bool]:
    write_build(build_dir, {".hidden.html": EXTRA_PAGE}, STAMP_1)  # a name starting with «.» is no page of the signature
    return build_sources(BUILD_ID), False


async def _add_a_page_in_a_subfolder(build_dir: Path) -> tuple[tuple[str, ...], bool]:
    write_build(build_dir, {"nested/page.html": EXTRA_PAGE}, STAMP_1)  # only *.html directly in the build count
    return build_sources(BUILD_ID), False


async def _change_files_that_are_no_page(build_dir: Path) -> tuple[tuple[str, ...], bool]:
    write_build(build_dir, {"robots.txt": b"User-agent: *\nDisallow: /\n", "new-chunk.js": CHUNK_JS}, STAMP_1)
    return build_sources(BUILD_ID), False


#: A change made to the build between two responses: what the hashes are after it (computed here), and whether the
#: signature changed, so the pages are read again.
BUILD_MUTATIONS: dict[str, Callable[[Path], Any]] = {
    "a-page-touched": _touch_a_page,
    "a-page-resized-at-the-same-mtime": _resize_a_page,
    "a-page-added": _add_a_page,
    "the-next-build-written": _write_the_next_build,
    "a-hidden-page-added": _add_a_hidden_page,
    "a-page-in-a-subfolder-added": _add_a_page_in_a_subfolder,
    "files-that-are-no-page-changed": _change_files_that_are_no_page,
}


@pytest.mark.asyncio
@pytest.mark.parametrize("change", list(BUILD_MUTATIONS))
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_a_changed_signature_recomputes_the_hashes_from_the_next_response_on(mode: Mode, change: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()} on the build {BUILD_ID}, then {change}"
    print_section(f"H-55 v2 step 1: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    calls = spy_on_spa_hashes(monkeypatch)
    middleware = built_on(build_dir, monkeypatch)
    first = await hashes_now(middleware, mode, what)
    assert first == build_sources(BUILD_ID) and calls == [build_dir], f"barrier: on the build {BUILD_ID} the first response has the hashes {first} after {calls} reads, not {build_sources(BUILD_ID)} after one read of {build_dir}"

    expected, recomputed = await BUILD_MUTATIONS[change](build_dir)
    second = await hashes_now(middleware, mode, what)

    assert second == expected, f"{what}: the next response has the hashes {second}, not {expected}"
    reads = 2 if recomputed else 1
    why = "the signature (name, mtime, size of every *.html directly in the build, none starting with «.») changed: the pages are read again" if recomputed else "the signature did not change: no page is read again"
    assert calls == [build_dir] * reads, f"{what}: {SPA_HASHES_NAME} was called with {calls}, wanted {reads} read(s) of {build_dir}: {why}"
    print_success(f"✓ {'recomputed' if recomputed else 'not read again'}: {second}")


async def _remove_a_page(build_dir: Path) -> None:
    (build_dir / "200.html").unlink()  # the build being written: a page of the last good signature is not there


async def _remove_the_build(build_dir: Path) -> None:
    shutil.rmtree(build_dir)


@pytest.mark.asyncio
@pytest.mark.parametrize("removal", [pytest.param(_remove_a_page, id="a-page-missing"), pytest.param(_remove_the_build, id="the-whole-build-missing")])
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_a_page_of_the_last_good_build_missing_keeps_the_last_good_hashes_and_the_next_response_checks_again(mode: Mode, removal: Callable[[Path], Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()} on the build {BUILD_ID}, then {removal.__name__.removeprefix('_')}"
    print_section(f"H-55 v2 step 1: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    middleware = built_on(build_dir, monkeypatch)
    last_good = await hashes_now(middleware, mode, what)
    assert last_good == build_sources(BUILD_ID), f"barrier: on the build {BUILD_ID} the response has the hashes {last_good}, not {build_sources(BUILD_ID)}"

    await removal(build_dir)
    while_missing = [await hashes_now(middleware, mode, what, path) for path in ("/", "/offline.html")]

    assert while_missing == [last_good] * 2, f"{what}: while the build is incomplete the hashes are {while_missing}, not the last good ones, {last_good}: a page of the last good signature missing (the build being written) keeps them, the hashes of the pages left would block the others"

    write_build(build_dir, build_pages(NEXT_BUILD_ID), STAMP_1)
    written = await hashes_now(middleware, mode, what)

    assert written == build_sources(NEXT_BUILD_ID), f"{what}: once the next build is written the hashes are {written}, not {build_sources(NEXT_BUILD_ID)}: the next web app response checks the build again"
    print_success(f"✓ last good kept while incomplete: {last_good}; then {written}")


#: A folder or a build that gives no inline script, never a build before: no hash at all.
NEVER_A_BUILD: dict[str, dict[str, bytes] | None] = {
    "missing-folder": None,
    "folder-without-a-page": {"robots.txt": ROBOTS_TXT, "favicon.png": FAVICON_PNG},
    "folder-with-a-hidden-page-only": {".hidden.html": EXTRA_PAGE},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("build", list(NEVER_A_BUILD))
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_with_no_build_there_is_no_hash_and_the_page_is_still_served(mode: Mode, build: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()} on a build {build}"
    print_section(f"H-55 v2 step 1: {what}")
    configure(monkeypatch, mode, tmp_path)
    files = NEVER_A_BUILD[build]
    build_dir = tmp_path / "build" if files is None else write_build(tmp_path / "build", files, STAMP_0)
    middleware = built_on(build_dir, monkeypatch)

    found = await hashes_now(middleware, mode, what)

    assert found == (), f"{what}: the hashes are {found}, not none: no build, no hash (script-src is {SCRIPT_SRC} alone)"

    write_build(build_dir, build_pages(BUILD_ID), STAMP_1)
    later = await hashes_now(middleware, mode, what)

    assert later == build_sources(BUILD_ID), f"{what}: once a build is written the hashes are {later}, not {build_sources(BUILD_ID)}: no build is not remembered"
    print_success(f"✓ no hash without a build; then {later}")


#: What answers at each path of ``test_only_web_app_html_responses_look_at_the_build``: the web app's page, then answers that are none.
CHEAP_ANSWERS = ("uppercase-TEXT-HTML", "mixed-case-with-charset", "application-json", "image-png", "text-javascript", "image-svg-xml-charset-utf-8", "application-pdf", "application-xhtml-xml")


def routing(answers: Iterable[TypedAnswer]) -> Callable:
    """A bare ASGI app answering, at each path of ``answers``, that answer (the paths are distinct)."""
    by_path = {typed.path: typed for typed in answers}

    async def app(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        await answering(by_path[scope["path"]])(scope, receive, send)

    return app


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_only_web_app_html_responses_look_at_the_build(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Only a web app HTML response pays for the build's signature: never an asset, an API answer, a document that is
    not the app's page (``/mkdocs``, the API docs, an SVG, an XHTML page), a PDF. Seen by the next build written between two
    web app responses: nothing in between reads it, so the hashes it gives are used by the next web app page alone."""
    what = f"the middleware built with {mode.describe()}"
    print_section(f"H-55 v2 step 1: {what}: who looks at the build")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    calls = spy_on_spa_hashes(monkeypatch)
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build_dir)
    middleware = wrap(routing([TYPED_ANSWERS["text-html"], *(TYPED_ANSWERS[key] for key in CHEAP_ANSWERS)]))
    first = await hashes_now(middleware, mode, what)
    assert first == build_sources(BUILD_ID) and calls == [build_dir], f"barrier: on the build {BUILD_ID} the first response has the hashes {first} after {calls} reads"

    write_build(build_dir, build_pages(NEXT_BUILD_ID), STAMP_1)
    for key in CHEAP_ANSWERS:
        typed = TYPED_ANSWERS[key]
        reply = await call(middleware, typed.path)
        assert_bare_answer(reply, typed, f"GET {typed.path}, {what}")
        assert_always_on(reply, f"GET {typed.path}, {what}")
        assert calls == [build_dir], f"GET {typed.path} answered {typed.content_type}, {what}: {SPA_HASHES_NAME} was called with {calls}: only a web app HTML response looks at the build"
    later = await hashes_now(middleware, mode, what)

    assert later == build_sources(NEXT_BUILD_ID) and calls == [build_dir] * 2, f"{what}: the web app page after them has the hashes {later} after {len(calls)} reads, not {build_sources(NEXT_BUILD_ID)} after 2"
    print_success(f"✓ {len(CHEAP_ANSWERS)} other answers never looked at the build; the next page did: {later}")


# =============================================================================
# (k) H-55 v2, STEP 3: THE ENFORCED POLICY, ALWAYS (the table, the connect sources)
# =============================================================================
#: One ``Content-Security-Policy`` field per response, in every profile: a document carries the trio, a web app page adds
#: script, worker and connect sources, frame protection adds ``frame-ancestors 'self'`` (and ``X-Frame-Options``) to any
#: response; never ``default-src``, ``style-src``, ``img-src``, ``font-src`` nor ``frame-src`` in it. The full table over the
#: app is ``test_the_enforced_policy_follows_the_response_in_every_profile_and_the_frame_protection_adds_its_own``; here the
#: same table written out as literals, then the directives that never go in, then the connect sources.

#: The answers of ``TYPED_ANSWERS`` the literal table reads, each with its kind: the web app's page; a document that is
#: not (the documentation, the API docs, an SVG image); an answer that is no document.
LITERAL_KINDS = {
    "text-html": "web app page",
    "uppercase-TEXT-HTML": "document",  # at /mkdocs/user/
    "mixed-case-with-charset": "document",  # at /api/v1/other (R5: not one of the API docs' two pages)
    "image-svg-xml": "document",
    "application-pdf": "other",
    "application-json": "other",
    "no-content-type": "other",
}
LITERAL_MODES = ("selfhosted-nothing-set", "selfhosted-frame-protection-true", "managed", "managed-both-switches-false")


def literal_policy(kind: str, *, frame_protection: bool, managed: bool) -> dict[str, tuple[str, ...]] | None:
    """The enforced policy the contract writes for ``kind``: as literals, not through ``expected_enforced``."""
    policy: dict[str, tuple[str, ...]] = {"frame-ancestors": ("'self'",)} if frame_protection else {}
    if kind in ("document", "web app page"):
        policy |= {"object-src": ("'none'",), "base-uri": ("'self'",), "form-action": ("'self'",)}
    if kind == "web app page":
        policy |= {
            "script-src": ("'self'", "'wasm-unsafe-eval'", "'report-sample'"),  # no build here: no hash
            "worker-src": ("'self'", "blob:"),
            "connect-src": ("'self'",) if managed else ("'self'", "https://api.github.com"),
        }
    return policy or None


@pytest.mark.asyncio
@pytest.mark.parametrize("key", list(LITERAL_KINDS))
@pytest.mark.parametrize("mode_name", LITERAL_MODES)
async def test_the_enforced_header_is_exactly_this_set_of_directives_and_sources(mode_name: str, key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mode, typed, kind = MODES[mode_name], TYPED_ANSWERS[key], LITERAL_KINDS[key]
    what = f"GET {typed.path} answered {typed.content_type or 'without Content-Type'} ({kind}) with {mode.describe()}"
    print_section(f"H-55 v2 the table, literally: {what}")
    configure(monkeypatch, mode, tmp_path)

    reply = await call(wrap(answering(typed)), typed.path)

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    expected = literal_policy(kind, frame_protection=mode.frame_protection, managed=mode.managed)
    policies = reply.values("content-security-policy")
    if expected is None:
        assert policies == [], f"{what}: a response that is no document, with frame protection off, carries no Content-Security-Policy; it is {policies}"
    else:
        assert len(policies) == 1, f"{what}: Content-Security-Policy is {policies}, wanted exactly one field"
        found = written_directives(policies[0], what)
        assert found == expected, f"{what}: the enforced policy {policies[0]!r} is {found}, not this exact set of directives with exactly these sources, {expected} (the order between directives is free)"
    print_success(f"✓ {sorted(expected) if expected else 'no Content-Security-Policy'}")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES.values(), ids=list(CASES))
@pytest.mark.parametrize("mode", MODES.values(), ids=list(MODES))
async def test_the_enforced_header_never_holds_default_style_img_font_or_frame_sources(mode: Mode, case: Case, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"{case.method} {case.path} with {mode.describe()}"
    print_section(f"H-55 v2 what is never enforced: {what}")

    reply = await answer(case, mode, tmp_path, monkeypatch)

    policies = reply.values("content-security-policy")
    assert len(policies) <= 1, f"{what}: Content-Security-Policy is {policies}: never two fields on a response"
    found = written_directives(policies[0], what) if policies else {}
    if case.web_app_html:
        assert "worker-src" in found and "script-src" in found, f"barrier: {what}: the enforced policy {policies} is not a web app page's (no script-src, worker-src): nothing below proves the styles, images, fonts and frames stay free"
    if case.worker_script:
        assert "worker-src" in found and "script-src" in found, f"barrier: {what}: the enforced policy {policies} is not a worker's (R4: no script-src, worker-src): nothing below proves the styles, images, fonts and frames stay free"
    if case.api_docs:
        assert "worker-src" in found and "script-src" in found, f"barrier: {what}: the enforced policy {policies} is not an API docs page's (R5: no script-src, worker-src): nothing below proves the styles, images, fonts and frames stay free"
    held = [name for name in NEVER_ENFORCED if name in found]
    assert not held, f"{what}: the enforced policy {policies} holds {held}: styles, images, fonts and frames stay free (embedding the app is a legitimate self-hosted use); they belong to the report-only policy alone"
    reporting = [name for name in NO_REPORT_DIRECTIVES if name in found]
    assert not reporting, f"{what}: {reporting} in the enforced policy {policies}: nothing is reported anywhere"
    print_success(f"✓ {sorted(found) or 'no policy'}: none of {NEVER_ENFORCED}")


# A public address as an operator may write it, the origin its connect source is (written here), the profile's own sources after it.
#: ``(None, None)``: the variable unset. The origin: scheme, host, port; lower case, without the scheme's default port, and
#: without a path, a query or a trailing slash (the canonical form of ``config.hosting_panel.panel_audience``).
PUBLIC_URLS: dict[str, tuple[str | None, str | None]] = {
    "unset": (None, None),
    "https-with-a-port-a-path-and-a-query": ("https://librefolio.example.org:8443/portfolio/?from=mail", "https://librefolio.example.org:8443"),
    "https-with-a-trailing-slash": ("https://librefolio.example.org/", "https://librefolio.example.org"),
    "upper-case-and-the-default-port": ("HTTPS://LibreFolio.Example.ORG:443/app", "https://librefolio.example.org"),
    "http-and-the-default-port": ("http://librefolio.example.org:80", "http://librefolio.example.org"),
    "http-address-and-port": ("http://192.0.2.10:6040", "http://192.0.2.10:6040"),
    "ipv6-address-and-port": ("http://[2001:db8::10]:6040/x", "http://[2001:db8::10]:6040"),
}
#: Written so that none can start a link or be an origin; each leaves the connect sources as without the variable.
INVALID_PUBLIC_URLS: dict[str, str] = {
    "no-scheme": "librefolio.example.org",
    "not-http": "ftp://librefolio.example.org",
    "no-host": "https://",
    "with-user-info": "https://operator:s3cret-pw@librefolio.example.org",
    "with-a-space": "https://librefolio example.org",
}


def connect_mode(profile: str, public_url: str | None, origin: str | None) -> Mode:
    """The configuration of a connect-sources case: ``profile``, the report-only switch on (both policies are read),
    LIBREFOLIO_PUBLIC_URL as written when ``public_url`` is given; frame protection as the profile gives it."""
    env = ((PROFILE, profile), (CSP_REPORT_ONLY, "true"), *(((PUBLIC_URL, public_url),) if public_url is not None else ()))
    return Mode(env, frame_protection=profile == "managed", csp_report_only=True, public_origin=origin)


async def assert_connect_sources(middleware: Callable, mode: Mode, what: str) -> None:
    """The web app's page at ``/`` and the documentation's at ``/mkdocs/user/`` through ``middleware`` (a ``routing`` of
    both): the page's enforced policy is the table's with ``connect-src`` ``CONNECT_SRC`` and ``mode.connect_sources``; its
    report-only policy is ``CSP_REPORT_ONLY_POLICY`` with the same ``connect-src``, every other directive in place; the
    documentation's page has no ``connect-src`` and no report-only policy."""
    page, docs = await call(middleware, "/"), await call(middleware, "/mkdocs/user/")
    for reply, path in ((page, "/"), (docs, "/mkdocs/user/")):
        answered(200, HTML, PAGE_HTML)(reply)
        assert_always_on(reply, f"GET {path}, {what}")
    expected_connect = CONNECT_SRC + mode.connect_sources
    enforced = page.values("content-security-policy")
    connect_src = written_directives(enforced[0], what).get("connect-src") if len(enforced) == 1 else enforced
    assert connect_src == expected_connect, f"GET /, {what}: connect-src of the enforced policy is {connect_src}, not {expected_connect}: 'self', the origin of {PUBLIC_URL} when valid ({mode.public_origin or 'none'}), {GITHUB_API} in the self-hosted profile only"
    assert_frame_protection(page, mode, True, f"GET /, {what}", web_app_page=True)
    report_only = page.values("content-security-policy-report-only")
    assert len(report_only) == 1, f"GET /, {what}: Content-Security-Policy-Report-Only is {report_only}, wanted exactly one"
    constant = written_directives(csp_report_only_policy(), CSP_REPORT_ONLY_POLICY_NAME)
    expected = {name: expected_connect if name == "connect-src" else sources for name, sources in constant.items()}
    found = written_directives(report_only[0], what)
    assert list(found.items()) == list(expected.items()), f"GET /, {what}: the report-only policy {report_only[0]!r} is not {CSP_REPORT_ONLY_POLICY_NAME} with the same connect-src, {expected_connect}, every other directive unchanged and in place"
    assert_frame_protection(docs, mode, True, f"GET /mkdocs/user/, {what}")
    assert docs.values("content-security-policy-report-only") == [], f"GET /mkdocs/user/, {what}: Content-Security-Policy-Report-Only is {docs.values('content-security-policy-report-only')}, wanted none: the connect sources go on web app pages only"


@pytest.mark.asyncio
@pytest.mark.parametrize("public_url", list(PUBLIC_URLS))
@pytest.mark.parametrize("profile", ["selfhosted", "managed"])
async def test_connect_src_is_self_then_the_public_origin_then_github_only_self_hosted(profile: str, public_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    url, origin = PUBLIC_URLS[public_url]
    mode = connect_mode(profile, url, origin)
    what = f"with {mode.describe()}"
    print_section(f"H-55 v2 the connect sources: {what}")
    configure(monkeypatch, mode, tmp_path)

    await assert_connect_sources(wrap(routing([TYPED_ANSWERS["text-html"], TYPED_ANSWERS["uppercase-TEXT-HTML"]])), mode, what)

    print_success(f"✓ connect-src {CONNECT_SRC + mode.connect_sources} in both policies of the page, nowhere on the documentation")


@pytest.mark.asyncio
@pytest.mark.parametrize("public_url", list(INVALID_PUBLIC_URLS))
@pytest.mark.parametrize("profile", ["selfhosted", "managed"])
async def test_an_invalid_public_url_adds_nothing_and_the_server_keeps_serving(profile: str, public_url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    raw = INVALID_PUBLIC_URLS[public_url]
    mode = connect_mode(profile, raw, None)
    what = f"with {mode.describe()}"
    print_section(f"H-55 v2 an invalid {PUBLIC_URL}: {what}")
    configure(monkeypatch, mode, tmp_path)

    middleware = wrap(routing([TYPED_ANSWERS["text-html"], TYPED_ANSWERS["uppercase-TEXT-HTML"]]))  # built all the same
    await assert_connect_sources(middleware, mode, what)

    page = await call(middleware, "/")
    for name in ("content-security-policy", "content-security-policy-report-only"):
        for value in page.values(name):
            assert "s3cret" not in value and "operator" not in value, f"{what}: {name} {value!r} leaks the user info of the invalid address"
            assert "example.org" not in value, f"{what}: {name} {value!r} names the host of an invalid address: nothing is added for it"
    print_success(f"✓ connect-src {CONNECT_SRC + mode.connect_sources}: nothing added, the page served")


@pytest.mark.asyncio
@pytest.mark.parametrize(("built_profile", "called_profile"), [("selfhosted", "managed"), ("managed", "selfhosted")])
async def test_the_public_url_and_the_profile_are_read_when_the_middleware_is_built(built_profile: str, called_profile: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    built = connect_mode(built_profile, "https://built.example.org/librefolio", "https://built.example.org")
    called = connect_mode(called_profile, "https://moved.example.org:9443/librefolio", "https://moved.example.org:9443")
    what = f"built with {built.describe()}, called with {called.describe()}"
    print_section(f"H-55 v2 the connect sources are read when built: {what}")
    configure(monkeypatch, built, tmp_path)
    middleware = wrap(routing([TYPED_ANSWERS["text-html"], TYPED_ANSWERS["uppercase-TEXT-HTML"]]))  # the settings are read here
    configure(monkeypatch, called, tmp_path)  # barrier inside: the environment now says the other

    await assert_connect_sources(middleware, built, what)  # answers as built: its origin, its profile's sources, its frame protection

    print_success(f"✓ answered as built: connect-src {CONNECT_SRC + built.connect_sources}")


# =============================================================================
# (l) H-55 v2, REVIEW CURE R2: THE ERROR PATH, AND THE BUILD OFF THE EVENT LOOP
# =============================================================================
#: Computing the headers of a response never costs the response its headers: if the web app's policy cannot be computed
#: (reading the build fails), the page still gets every header with the policy WITHOUT hashes (fail closed: the app's inline
#: scripts are blocked, never a policy-less page) and the failure is logged, once, as a warning with its traceback. The
#: build's signature (``glob`` + ``stat``) and its re-read run in a thread, never on the event loop, and one re-read serves
#: every request that waited for it. Imports of the module's names are made inside the tests (a missing name fails the
#: test that needs it, never the collection).

#: How many web app requests are in flight together in the concurrency cases.
CONCURRENT_REQUESTS = 8
#: How long the slow re-read of the unit case waits for its siblings: it ends at once if they all arrive (no lock), and
#: after this when the lock keeps them out (the wait costs only a green run, and a slow machine can only make a red green).
SIBLINGS_SECONDS = 1.0
#: The failure a build that cannot be read raises.
BUILD_UNREADABLE = "provoked: the build cannot be read"


def _unreadable_build(build_dir: Path) -> tuple[str, ...]:
    raise OSError(BUILD_UNREADABLE)


def spa_hashes_run_in_threads(monkeypatch: pytest.MonkeyPatch, *, delay: Callable[[], None] | None = None) -> list[tuple[int, Path]]:
    """Watch ``static_site.spa_inline_script_hashes``: answers as the real one (after ``delay``, when given) and records
    ``(thread id, build folder)`` of every call, in order."""
    real = spa_hashes_function()
    calls: list[tuple[int, Path]] = []

    def spy(build_dir: Path) -> tuple[str, ...]:
        calls.append((threading.get_ident(), build_dir))
        if delay is not None:
            delay()
        return real(build_dir)

    monkeypatch.setattr(static_site, SPA_HASHES_NAME, spy)
    return calls


def stats_of_pages_in_threads(monkeypatch: pytest.MonkeyPatch, build_dir: Path) -> list[int]:
    """Watch the ``stat`` of the build's pages (``Path.stat`` on a path under ``build_dir``): the id of the thread of each."""
    real = Path.stat
    seen: list[int] = []

    def watching(self: Path, *args: Any, **kwargs: Any) -> os.stat_result:
        if self.suffix == ".html" and build_dir in self.parents:
            seen.append(threading.get_ident())
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", watching)
    return seen


@contextmanager
def security_warnings() -> Iterator[Callable[[], list[dict[str, Any]]]]:
    """The structlog events logged inside the block as a warning or worse, behind a canary of the middleware's module."""
    with capture_logs() as events:
        get_logger(SECURITY_MODULE).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: a structlog logger of {SECURITY_MODULE} does not reach capture_logs: {events}"

        def logged() -> list[dict[str, Any]]:
            return [event for event in events if event.get("event") != LOG_CANARY and event.get("log_level") in ("warning", "error", "exception", "critical")]

        yield logged


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_a_build_that_cannot_be_read_still_gets_every_header_with_a_policy_without_hashes(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()} on the build {BUILD_ID}, whose reading raises"
    print_section(f"H-55 v2 R2: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    middleware = built_on(build_dir, monkeypatch)
    monkeypatch.setattr(static_site, SPA_HASHES_NAME, _unreadable_build)

    with security_warnings() as logged:
        reply = await call(middleware, "/")
        warned = logged()

    answered(200, HTML, PAGE_HTML)(reply)  # the page itself is served: the failure costs it its hashes, never its answer
    assert_always_on(reply, f"GET /, {what}")
    assert_frame_protection(reply, mode, True, f"GET /, {what}", web_app_page=True, script_hashes=())
    script_src = written_directives(reply.values("content-security-policy")[0], what).get("script-src")
    assert script_src == SCRIPT_SRC, f"{what}: script-src is {script_src}, exactly {SCRIPT_SRC} wanted: fail closed, no hash, the app's inline scripts are blocked and the page is never policy-less"
    if mode.csp_report_only:
        report_only = reply.values("content-security-policy-report-only")
        assert len(report_only) == 1, f"{what}: Content-Security-Policy-Report-Only is {report_only}, wanted one policy"
        assert written_directives(report_only[0], what).get("script-src") == SCRIPT_SRC, f"{what}: the report-only policy {report_only[0]!r} has hashes: no build could be read"
    with_trace = [event for event in warned if event.get("log_level") == "warning" and event.get("exc_info")]
    assert len(with_trace) == 1, f"{what}: logged {[(event.get('log_level'), event.get('event'), bool(event.get('exc_info'))) for event in warned]}, wanted exactly one warning with exc_info: the failure is logged once, with its traceback"
    print_success(f"✓ every header, script-src {script_src}, one warning with its traceback")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_after_a_failed_build_read_the_next_pages_still_answer_and_the_hashes_come_back_with_the_build(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()} on the build {BUILD_ID}, whose reading fails twice, then works"
    print_section(f"H-55 v2 R2: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    middleware = built_on(build_dir, monkeypatch)
    real = spa_hashes_function()
    monkeypatch.setattr(static_site, SPA_HASHES_NAME, _unreadable_build)

    for path in ("/", "/portfolio/overview"):  # a failure does not wedge the middleware: the next page answers all the same
        reply = await call(middleware, path)
        answered(200, HTML, PAGE_HTML)(reply)
        assert_always_on(reply, f"GET {path}, {what}")
        assert_frame_protection(reply, mode, True, f"GET {path}, {what}", web_app_page=True, script_hashes=())
    monkeypatch.setattr(static_site, SPA_HASHES_NAME, real)  # the build is readable again

    found = await hashes_now(middleware, mode, what)

    assert found == build_sources(BUILD_ID), f"{what}: the hashes are {found}, not those of the build, {build_sources(BUILD_ID)}: a failed read is not remembered as the build's signature"
    print_success(f"✓ two pages answered after the failure; then the hashes of the build: {found}")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_the_build_is_read_off_the_event_loop(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"the middleware built with {mode.describe()}, a web app page asked on the build {BUILD_ID}"
    print_section(f"H-55 v2 R2: {what}: which thread reads the build")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    reads = spa_hashes_run_in_threads(monkeypatch)
    stats = stats_of_pages_in_threads(monkeypatch, build_dir)
    middleware = built_on(build_dir, monkeypatch)
    loop_thread = threading.get_ident()

    found = await hashes_now(middleware, mode, what)

    assert found == build_sources(BUILD_ID), f"barrier: the hashes are {found}, not those of the build, {build_sources(BUILD_ID)}"
    assert [build for _, build in reads] == [build_dir] and stats, f"barrier: {SPA_HASHES_NAME} was called with {[build for _, build in reads]} and {len(stats)} pages were stat-ed"
    assert [thread for thread, _ in reads] != [loop_thread], f"{what}: {SPA_HASHES_NAME} ran on the event loop's thread: reading the pages is blocking I/O, to be awaited through asyncio.to_thread"
    assert loop_thread not in stats, f"{what}: the build's signature (glob and stat of its pages) was computed on the event loop's thread: to be awaited through asyncio.to_thread"
    print_success(f"✓ read in thread {reads[0][0]}, signature in {sorted(set(stats))}, the loop is {loop_thread}")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", HASH_MODES.values(), ids=list(HASH_MODES))
async def test_concurrent_web_app_requests_with_a_changed_build_read_it_once_and_off_the_loop(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    what = f"{CONCURRENT_REQUESTS} web app requests at once on the middleware built with {mode.describe()}, after the build {NEXT_BUILD_ID} replaced {BUILD_ID}"
    print_section(f"H-55 v2 R2: {what}")
    configure(monkeypatch, mode, tmp_path)
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    middleware = built_on(build_dir, monkeypatch)
    first = await hashes_now(middleware, mode, what)
    assert first == build_sources(BUILD_ID), f"barrier: the first response has the hashes {first}, not those of the build {BUILD_ID}"
    write_build(build_dir, build_pages(NEXT_BUILD_ID), STAMP_1)  # a build made while the server runs
    reads = spa_hashes_run_in_threads(monkeypatch)
    loop_thread = threading.get_ident()

    replies = await asyncio.gather(*(call(middleware, WEB_APP_PAGE_PATHS[index % len(WEB_APP_PAGE_PATHS)]) for index in range(CONCURRENT_REQUESTS)))

    for reply in replies:
        answered(200, HTML, PAGE_HTML)(reply)
        assert_always_on(reply, what)
        assert script_src_of(reply, "content-security-policy", what) == build_sources(NEXT_BUILD_ID), f"{what}: a response carries {reply.values('content-security-policy')}, not the hashes of the build now, {build_sources(NEXT_BUILD_ID)}"
    assert len(reads) == 1, f"{what}: {SPA_HASHES_NAME} was called {len(reads)} times, wanted once: one read per change of the build's signature, however many requests find it changed together"
    assert reads[0][0] != loop_thread, f"{what}: the one read ran on the event loop's thread: to be awaited through asyncio.to_thread"
    print_success(f"✓ {CONCURRENT_REQUESTS} responses, the build read once, off the loop")


def test_the_build_hashes_cache_reads_once_when_threads_ask_together(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``_BuildScriptHashes`` is safe under concurrent threads: a lock, and one read of a changed build even when several
    threads ask at the same moment. The read is slow on purpose: it waits for its siblings, which arrive only if nothing
    keeps them out."""
    what = f"{CONCURRENT_REQUESTS} threads asking the hashes of the build {BUILD_ID} together"
    print_section(f"H-55 v2 R2: {what}")
    security_module = importlib.import_module(SECURITY_MODULE)
    cache_class = getattr(security_module, "_BuildScriptHashes", None)
    assert isinstance(cache_class, type), f"{SECURITY_MODULE} has no class _BuildScriptHashes"
    build_dir = write_build(tmp_path / "build", build_pages(BUILD_ID), STAMP_0)
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build_dir)
    siblings = threading.Barrier(CONCURRENT_REQUESTS)

    def wait_for_siblings() -> None:
        try:
            siblings.wait(timeout=SIBLINGS_SECONDS)
        except threading.BrokenBarrierError:
            pass  # alone: nobody else got in

    reads = spa_hashes_run_in_threads(monkeypatch, delay=wait_for_siblings)
    cache = cache_class()
    start = threading.Barrier(CONCURRENT_REQUESTS)

    def ask() -> tuple[str, ...]:
        start.wait(timeout=SIBLINGS_SECONDS * 5)
        return cache.current()

    with ThreadPoolExecutor(max_workers=CONCURRENT_REQUESTS) as pool:
        answers = [future.result(timeout=SIBLINGS_SECONDS * 10) for future in [pool.submit(ask) for _ in range(CONCURRENT_REQUESTS)]]

    assert answers == [build_sources(BUILD_ID)] * CONCURRENT_REQUESTS, f"{what}: the answers are {answers}, not always those of the build, {build_sources(BUILD_ID)}"
    assert len(reads) == 1, f"{what}: {SPA_HASHES_NAME} was called {len(reads)} times, wanted once: the cache holds a lock, and one read serves the threads that asked for the same signature"
    print_success("✓ one read for all the threads")


# =============================================================================
# (l) H-55 WAVE 4, R4: A POLICY FOR THE WORKERS (JavaScript under /_app/)
# =============================================================================
#
# A browser applies the Content-Security-Policy of a *script response* to a worker started from it, and ignores it on any
# other script. The web app's only URL worker (``priceProcessing.worker``) is served by ``/_app/``; today that response
# carries no policy, so the worker runs under none. Contract (wave 4, §4): every JavaScript response (``text/javascript`` or
# ``application/javascript``, parameters ignored) at a path starting with ``/_app/`` gets, besides the base headers, ONE
# enforced ``Content-Security-Policy`` with exactly these directives, the order between them free:
#
#   script-src 'self'; connect-src 'self' <the web-app page's connect sources>; worker-src 'self' blob:;
#   object-src 'none'; base-uri 'self'          (+ frame-ancestors 'self' when frame protection is on)
#
# never ``default-src``, ``'unsafe-inline'``, ``'unsafe-eval'`` or ``'wasm-unsafe-eval'`` (the worker compiles no
# WebAssembly; the PDF engine's worker is a blob worker under the page's policy). None on a 304 (H-45), none on JavaScript
# outside ``/_app/`` (plugin assets, ``/mkdocs``), a route's own policy kept. Everything here is written from the contract,
# never read from the module; the presence barrier of each absence is a JavaScript response under ``/_app/`` carrying the
# policy, so an absence is never the effect of the feature not existing.
#
# R4 has shipped: the cases of sections (a), (g) and (i) that serve a JavaScript chunk under ``/_app/``
# (CASES["javascript-under-app"], TYPED_ANSWERS["text-javascript"], MOUNTED_FILES["javascript-chunk"]) expect this same
# policy, through ``expected_enforced(worker_script=True)``, which reads ``expected_worker_policy`` below.

WORKER_SCRIPT = b"self.onmessage = (event) => self.postMessage(event.data);\n"
#: The two places of a worker's script and of a chunk under the build's immutable folder, as SvelteKit writes them.
WORKER_PATH = "/_app/immutable/workers/x.js"
CHUNK_PATH = "/_app/immutable/chunks/y.js"
SCRIPT_PATHS: dict[str, str] = {"worker": WORKER_PATH, "chunk": CHUNK_PATH}
#: Both JavaScript media types of the contract, the second with a parameter, which is ignored.
SCRIPT_TYPES: dict[str, str] = {"text-javascript": "text/javascript", "application-javascript-charset": "application/javascript; charset=utf-8"}
#: What a worker's policy holds besides ``frame-ancestors`` and ``connect-src``, which follow the configuration.
WORKER_FIXED: dict[str, tuple[str, ...]] = {"script-src": ("'self'",), "worker-src": WORKER_SRC, "object-src": ("'none'",), "base-uri": ("'self'",)}
#: What a policy of a worker never holds, as a token anywhere in it.
WORKER_FORBIDDEN = ("default-src", "'unsafe-inline'", "'unsafe-eval'", "'wasm-unsafe-eval'", *NEVER_ENFORCED, "form-action", "report-uri", "report-to")
#: The configurations of R4: every one the file parametrizes, and a valid public address in each profile (a connect source).
R4_MODES: dict[str, Mode] = {
    **MODES,
    "selfhosted-public-url": connect_mode("selfhosted", "https://librefolio.example.org:8443/portfolio", "https://librefolio.example.org:8443"),
    "managed-public-url": connect_mode("managed", "https://librefolio.example.org/", "https://librefolio.example.org"),
}


def script_answer(path: str, content_type: str, body: bytes = WORKER_SCRIPT) -> TypedAnswer:
    """A bare app's answer at ``path``: ``content_type`` as written, ``body``; no document."""
    return TypedAnswer(path, content_type, body, document=False)


def expected_worker_policy(mode: Mode) -> dict[str, tuple[str, ...]]:
    """R4: the directives of the policy of a JavaScript response under ``/_app/`` under ``mode``, ``{directive: sources}``,
    written here: ``frame-ancestors 'self'`` only with frame protection on, ``connect-src`` as the web app's page has it."""
    expected: dict[str, tuple[str, ...]] = {"frame-ancestors": FRAME_ANCESTORS} if mode.frame_protection else {}
    expected.update(WORKER_FIXED)
    expected["connect-src"] = CONNECT_SRC + mode.connect_sources
    return expected


def assert_worker_policy(reply: Reply, mode: Mode, what: str) -> dict[str, tuple[str, ...]]:
    """``reply`` carries the worker's policy of ``mode``: one ``Content-Security-Policy`` whose directives and sources are
    exactly ``expected_worker_policy``, ``X-Frame-Options`` once exactly with frame protection, no report-only policy.
    Returns the directives found."""
    policies = reply.values("content-security-policy")
    assert len(policies) == 1, f"{what}: Content-Security-Policy is {policies}, wanted exactly one field: R4 gives a JavaScript response under /_app/ the policy of a worker, {expected_worker_policy(mode)}"
    found = written_directives(policies[0], what)
    expected = expected_worker_policy(mode)
    assert found == expected, f"{what}: the policy {policies[0]!r} is not, directive by directive and source by source, {expected} (R4; the order between directives is free)"
    assert reply.values("x-frame-options") == ([FRAME_OPTIONS] if mode.frame_protection else []), f"{what}: X-Frame-Options is {reply.values('x-frame-options')}, wanted {[FRAME_OPTIONS] if mode.frame_protection else []}: frame protection is {'on' if mode.frame_protection else 'off'}"
    assert reply.values("content-security-policy-report-only") == [], f"{what}: Content-Security-Policy-Report-Only is {reply.values('content-security-policy-report-only')}, wanted none: it is the web app's pages' alone"
    return found


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", SCRIPT_TYPES.values(), ids=list(SCRIPT_TYPES))
@pytest.mark.parametrize("path", SCRIPT_PATHS.values(), ids=list(SCRIPT_PATHS))
@pytest.mark.parametrize("mode", R4_MODES.values(), ids=list(R4_MODES))
async def test_r4_a_javascript_response_under_app_gets_exactly_the_workers_policy(mode: Mode, path: str, content_type: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4: ``text/javascript`` and ``application/javascript; charset=utf-8``, at a worker's place and at a chunk's under
    ``/_app/``, in every configuration (profile, switches, a public address): one policy, ``script-src 'self'``,
    ``connect-src`` with the web app page's sources (``'self'``, the public origin when valid, GitHub's API self-hosted),
    ``worker-src 'self' blob:``, ``object-src 'none'``, ``base-uri 'self'``, plus ``frame-ancestors 'self'`` exactly with
    frame protection; no report-only policy."""
    typed = script_answer(path, content_type)
    what = f"GET {path} answered {content_type} with {mode.describe()}"
    print_section(f"H-55 w4 R4 the workers' policy: {what}")
    configure(monkeypatch, mode, tmp_path)

    reply = await call(wrap(answering(typed)), path)  # SecurityHeadersMiddleware(app) built here, configuration in place

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    found = assert_worker_policy(reply, mode, what)
    print_success(f"✓ {sorted(found)}; connect-src {found['connect-src']}")


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", SCRIPT_TYPES.values(), ids=list(SCRIPT_TYPES))
@pytest.mark.parametrize("mode", R4_MODES.values(), ids=list(R4_MODES))
async def test_r4_the_workers_policy_never_holds_default_src_or_an_unsafe_or_wasm_source(mode: Mode, content_type: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4: the policy of a worker holds no ``default-src`` (styles, images, fonts and frames stay free), no
    ``'unsafe-inline'``, no ``'unsafe-eval'``, no ``'wasm-unsafe-eval'`` (the only URL worker compiles no WebAssembly), and
    none of the other directives the app leaves free. Behind its barrier: it is the worker's policy, with its ``script-src``."""
    typed = script_answer(WORKER_PATH, content_type)
    what = f"GET {WORKER_PATH} answered {content_type} with {mode.describe()}"
    print_section(f"H-55 w4 R4 what the workers' policy never holds: {what}")
    configure(monkeypatch, mode, tmp_path)

    reply = await call(wrap(answering(typed)), WORKER_PATH)

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    policies = reply.values("content-security-policy")
    assert len(policies) == 1 and "script-src" in written_directives(policies[0], what) and "worker-src" in written_directives(policies[0], what), f"barrier: {what}: Content-Security-Policy is {policies}, not a worker's policy (no script-src, worker-src): nothing below proves what it never holds"
    held = [token for token in WORKER_FORBIDDEN if token in policies[0].lower()]
    assert not held, f"{what}: the policy {policies[0]!r} holds {held}: R4 gives a worker script-src, connect-src, worker-src, object-src and base-uri, and nothing else but frame-ancestors with frame protection"
    print_success(f"✓ none of {WORKER_FORBIDDEN}")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", SCRIPT_PATHS.values(), ids=list(SCRIPT_PATHS))
@pytest.mark.parametrize("mode", [R4_MODES["managed"], R4_MODES["selfhosted"], R4_MODES["managed-both-switches-false"]], ids=["managed", "selfhosted", "managed-both-switches-false"])
async def test_r4_the_mount_of_the_app_serves_a_script_with_the_workers_policy(mode: Mode, path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4, through the stack (``security_headers``, gzip, cors, the static site of the fake build): the ``/_app`` mount
    (``ImmutableStaticFiles``) serves a worker's script and a chunk as JavaScript, and the response carries the worker's
    policy; the mount's own headers (ETag, immutable ``Cache-Control``) stay."""
    what = f"GET {path} through the stack with {mode.describe()}"
    print_section(f"H-55 w4 R4 through the stack: {what}")
    configure(monkeypatch, mode, tmp_path)
    app = site_app(tmp_path, monkeypatch)
    _write_tree(tmp_path / "build", {path.removeprefix("/"): WORKER_SCRIPT})

    reply = await call(app, path)

    answered(200, JAVASCRIPT, WORKER_SCRIPT)(reply)
    assert_always_on(reply, what)
    assert reply.values("cache-control") == [static_site.IMMUTABLE_CACHE_CONTROL], f"barrier: {what}: not the mount's answer, Cache-Control is {reply.values('cache-control')}"
    found = assert_worker_policy(reply, mode, what)
    print_success(f"✓ {sorted(found)}; the mount's Cache-Control kept")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", SCRIPT_PATHS.values(), ids=list(SCRIPT_PATHS))
@pytest.mark.parametrize("mode", R4_MODES.values(), ids=list(R4_MODES))
async def test_r4_a_304_of_a_script_gets_no_policy_while_its_200_carries_the_workers(mode: Mode, path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4 and H-45: a browser freshens its cached response with the header fields of a 304, so a policy on a 304, with or
    without a ``Content-Type``, would replace the cached script's. The same script as a 200 (the barrier) carries the worker's
    policy; revalidated, its 304 carries neither policy and keeps the route's headers, ``X-Frame-Options`` as any answer."""
    revalidated = Revalidated(path, (("content-type", "text/javascript; charset=utf-8"), ("etag", '"w1"'), ("cache-control", static_site.IMMUTABLE_CACHE_CONTROL)), WORKER_SCRIPT, document=False, web_app_html=False)
    what = f"GET {path} with If-None-Match: {revalidated.etag}, answered 304, with {mode.describe()}"
    print_section(f"H-55 w4 R4 no policy on a 304: {what}")
    configure(monkeypatch, mode, tmp_path)
    middleware = wrap(revalidating(revalidated))  # SecurityHeadersMiddleware(app) built here, configuration in place

    fresh = await call(middleware, path)

    assert fresh.raised is None and fresh.status == 200 and fresh.body == WORKER_SCRIPT, f"barrier: {what}: not the bare app's 200: {fresh.status} {fresh.body[:120]!r}, raised {fresh.raised!r}"
    assert_always_on(fresh, f"GET {path} answered 200, with {mode.describe()}")
    assert_worker_policy(fresh, mode, f"barrier: GET {path} answered 200, with {mode.describe()}")

    reply = await call(middleware, path, headers=(("If-None-Match", revalidated.etag),))

    assert reply.raised is None and reply.status == 304 and reply.body == b"", f"barrier: {what}: not the bare app's 304: {reply.status} {reply.body[:120]!r}, raised {reply.raised!r}"
    assert_always_on(reply, what)
    for name in POLICY_HEADERS:
        assert reply.values(name) == [], f"{what}: {name} is {reply.values(name)}, wanted none; H-45: a browser freshens its cached copy with the header fields of a 304, so a policy there replaces the worker's"
    frame_options = [FRAME_OPTIONS] if mode.frame_protection else []
    assert reply.values("x-frame-options") == frame_options, f"{what}: X-Frame-Options is {reply.values('x-frame-options')}, wanted {frame_options}"
    print_success("✓ the 200 carries the workers' policy, the 304 none")


#: JavaScript where R4 does not reach: a plugin's asset, the documentation's, and paths that only look like ``/_app/``.
OUTSIDE_APP_PATHS: dict[str, str] = {
    "plugin-asset": "/plugins/x.js",
    "documentation-asset": "/mkdocs/assets/z.js",
    "path-starting-like-app": "/_apple/immutable/workers/x.js",
    "app-not-at-the-start": "/other/_app/immutable/workers/x.js",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("key", list(OUTSIDE_APP_PATHS))
@pytest.mark.parametrize("mode", R4_MODES.values(), ids=list(R4_MODES))
async def test_r4_javascript_outside_app_gets_only_what_frame_protection_gives_a_non_document(mode: Mode, key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4: JavaScript at a plugin's asset path, under ``/mkdocs``, or at a path that merely starts like ``/_app/``, gets what
    any non-document gets (``frame-ancestors 'self'`` with frame protection on, no policy off): never the worker's policy. The
    barrier, on the same middleware: a script under ``/_app/`` answered the same type carries it, so the absence is R4's
    boundary and not a feature that does not exist."""
    path = OUTSIDE_APP_PATHS[key]
    inside, outside = script_answer(WORKER_PATH, "text/javascript"), script_answer(path, "text/javascript")
    what = f"GET {path} answered text/javascript with {mode.describe()}"
    print_section(f"H-55 w4 R4 outside /_app/: {what}")
    configure(monkeypatch, mode, tmp_path)
    middleware = wrap(routing([inside, outside]))

    barrier = await call(middleware, WORKER_PATH)

    assert_bare_answer(barrier, inside, f"barrier: GET {WORKER_PATH}")
    assert_always_on(barrier, f"barrier: GET {WORKER_PATH}, with {mode.describe()}")
    assert_worker_policy(barrier, mode, f"barrier: GET {WORKER_PATH}, with {mode.describe()}")

    reply = await call(middleware, path)

    assert_bare_answer(reply, outside, what)
    assert_always_on(reply, what)
    print_success(f"✓ {assert_frame_protection(reply, mode, False, what)}; nosniff and Referrer-Policy")


#: What else is served under ``/_app/`` and is no script: a style sheet, JSON, WebAssembly, a source map; R4 is for scripts.
NON_SCRIPT_TYPES: dict[str, TypedAnswer] = {
    "css": TypedAnswer("/_app/immutable/assets/app.css", "text/css; charset=utf-8", APP_CSS, document=False),
    "json": TypedAnswer("/_app/version.json", "application/json", API_JSON, document=False),
    "wasm": TypedAnswer("/_app/immutable/assets/engine.wasm", "application/wasm", b"\x00asm\x01\x00\x00\x00", document=False),
    "source-map": TypedAnswer("/_app/immutable/chunks/y.js.map", "application/json", API_JSON, document=False),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("key", list(NON_SCRIPT_TYPES))
@pytest.mark.parametrize("mode", [R4_MODES["managed"], R4_MODES["selfhosted"]], ids=["managed", "selfhosted"])
async def test_r4_what_is_no_script_under_app_does_not_get_the_workers_policy(mode: Mode, key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4: the type decides, not the path alone: a style sheet, JSON, a WebAssembly module or a source map under ``/_app/``
    gets what any non-document gets. Barrier on the same middleware: a script under ``/_app/`` carries the worker's policy."""
    typed, script = NON_SCRIPT_TYPES[key], script_answer(WORKER_PATH, "text/javascript")
    what = f"GET {typed.path} answered {typed.content_type} with {mode.describe()}"
    print_section(f"H-55 w4 R4 not a script under /_app/: {what}")
    configure(monkeypatch, mode, tmp_path)
    middleware = wrap(routing([script, typed]))

    barrier = await call(middleware, WORKER_PATH)

    assert_bare_answer(barrier, script, f"barrier: GET {WORKER_PATH}")
    assert_always_on(barrier, f"barrier: GET {WORKER_PATH}, with {mode.describe()}")
    assert_worker_policy(barrier, mode, f"barrier: GET {WORKER_PATH}, with {mode.describe()}")

    reply = await call(middleware, typed.path)

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    print_success(f"✓ {assert_frame_protection(reply, mode, False, what)}; nosniff and Referrer-Policy")


def sets_its_own_policy() -> Callable:
    """A bare ASGI app answering JavaScript at two places under ``/_app/``: one whose route sets its own
    ``Content-Security-Policy`` (``ROUTE_CSP``), one that sets none."""

    async def app(scope: dict[str, Any], receive: Callable, send: Callable) -> None:
        own = scope["path"] == "/_app/immutable/workers/own.js"
        headers = [(b"content-type", b"text/javascript")] + ([(b"content-security-policy", ROUTE_CSP.encode())] if own else [])
        await send({"type": "http.response.start", "status": 200, "headers": headers})
        await send({"type": "http.response.body", "body": WORKER_SCRIPT})

    return app


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", R4_MODES.values(), ids=list(R4_MODES))
async def test_r4_a_policy_the_route_set_on_a_script_is_kept_alone(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R4, as for every header of D5 (d): a JavaScript response under ``/_app/`` whose route set its own
    ``Content-Security-Policy`` keeps it, alone, never replaced by the worker's policy, never joined by a second field;
    ``X-Frame-Options`` follows the frame protection. Barrier, same middleware: the sibling without one gets the worker's."""
    own_path, plain_path = "/_app/immutable/workers/own.js", "/_app/immutable/workers/plain.js"
    what = f"GET {own_path} (the route sets {ROUTE_CSP!r}) with {mode.describe()}"
    print_section(f"H-55 w4 R4 a route's own policy on a script: {what}")
    configure(monkeypatch, mode, tmp_path)
    middleware = wrap(sets_its_own_policy())

    plain = await call(middleware, plain_path)

    assert plain.raised is None and plain.status == 200 and plain.body == WORKER_SCRIPT, f"barrier: GET {plain_path}: not the bare app's answer: {plain.status} {plain.body[:120]!r}, raised {plain.raised!r}"
    assert_always_on(plain, f"barrier: GET {plain_path}, with {mode.describe()}")
    assert_worker_policy(plain, mode, f"barrier: GET {plain_path}, with {mode.describe()}")

    reply = await call(middleware, own_path)

    assert reply.raised is None and reply.status == 200 and reply.body == WORKER_SCRIPT, f"barrier: {what}: not the bare app's answer: {reply.status} {reply.body[:120]!r}, raised {reply.raised!r}"
    assert_always_on(reply, what)
    assert reply.values("content-security-policy") == [ROUTE_CSP], f"{what}: Content-Security-Policy is {reply.values('content-security-policy')}; the route's {ROUTE_CSP!r} must stay, alone: never replaced by the worker's policy, never joined by a second field"
    frame_options = [FRAME_OPTIONS] if mode.frame_protection else []
    assert reply.values("x-frame-options") == frame_options, f"{what}: X-Frame-Options is {reply.values('x-frame-options')}, wanted {frame_options}"
    print_success(f"✓ the route's {ROUTE_CSP!r} kept alone; X-Frame-Options {frame_options}")


# =============================================================================
# (m) H-55 WAVE 5, R5: THE API DOCS' TWO PAGES (scripts of our own origin, ReDoc's search worker)
# =============================================================================
#
# FastAPI's Swagger UI and ReDoc pages loaded their libraries from jsDelivr unpinned, with an inline start script, which the
# enforced policy could not carry. Now ``install_api_docs`` serves both pages with no inline script (their start scripts come
# from the backend, ``/api/v1/docs/swagger-init.js`` and ``/api/v1/redoc/redoc-init.js``) and the libraries come from jsDelivr
# at an exact version with Subresource Integrity, and the two pages, exactly ``/api/v1/docs`` and ``/api/v1/redoc`` answered ``text/html`` (parameters ignored, any case), carry, beyond the
# document trio (and ``frame-ancestors 'self'`` with frame protection), ``script-src 'self' https://cdn.jsdelivr.net``, ``worker-src 'self' blob:``
# (ReDoc's search worker) and ``connect-src 'self'`` (Swagger's «Try it out» and the schema's fetch, same origin), in ONE field.
# Nothing else changes: any other document, under ``/api/`` or elsewhere, keeps the trio alone; ``/api/v1/openapi.json`` is JSON,
# no document. Written from the contract (``expected_enforced`` with ``api_docs_page=True`` is the table, and the literals below
# are the contract's words); the through-the-stack cases are ``CASES["api-html-swagger-ui"]`` and ``["api-html-redoc"]`` of
# section (a), served by ``install_api_docs`` itself.

#: The kinds of ``text/html`` the pages may be answered as: the type decides, in any case, parameters allowed.
DOCS_PAGE_TYPES: dict[str, str] = {"plain": "text/html", "charset": "text/html; charset=utf-8", "upper-case": "TEXT/HTML", "mixed-case-with-charset": "Text/HTML; Charset=UTF-8"}


def docs_page_answer(path: str, content_type: str = "text/html") -> TypedAnswer:
    """A bare app's HTML page at one of the API docs' paths."""
    return TypedAnswer(path, content_type, PAGE_HTML, document=True)


def literal_docs_policy(mode: Mode) -> dict[str, tuple[str, ...]]:
    """The contract's policy of an API docs page, written out: the trio, ``script-src 'self' https://cdn.jsdelivr.net``, ``worker-src 'self' blob:``,
    ``connect-src 'self'``, and ``frame-ancestors 'self'`` exactly with frame protection."""
    policy: dict[str, tuple[str, ...]] = {"frame-ancestors": ("'self'",)} if mode.frame_protection else {}
    policy |= {
        "object-src": ("'none'",),
        "base-uri": ("'self'",),
        "form-action": ("'self'",),
        "script-src": ("'self'", "https://cdn.jsdelivr.net"),
        "worker-src": ("'self'", "blob:"),
        "connect-src": ("'self'",),
    }
    return policy


@pytest.mark.asyncio
@pytest.mark.parametrize("content_type", DOCS_PAGE_TYPES.values(), ids=list(DOCS_PAGE_TYPES))
@pytest.mark.parametrize("path", API_DOCS_PATHS)
@pytest.mark.parametrize("mode", R4_MODES.values(), ids=list(R4_MODES))
async def test_r5_an_api_docs_page_gets_exactly_the_docs_policy(mode: Mode, path: str, content_type: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R5: ``/api/v1/docs`` and ``/api/v1/redoc`` answered ``text/html`` get, in every configuration (profile, switches, a public
    address), the document trio, ``script-src 'self' https://cdn.jsdelivr.net``, ``worker-src 'self' blob:``, ``connect-src 'self'`` alone (the public
    origin and GitHub's API are the web app's) and ``frame-ancestors 'self'`` exactly with frame protection; one field, no
    report-only policy, ``X-Frame-Options`` exactly with frame protection."""
    typed = docs_page_answer(path, content_type)
    what = f"GET {path} answered {content_type} with {mode.describe()}"
    print_section(f"H-55 w5 R5 the API docs page's policy: {what}")
    configure(monkeypatch, mode, tmp_path)

    reply = await call(wrap(answering(typed)), path)

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    assert typed.api_docs_page, f"barrier: {what}: the case is one of the API docs' two pages"
    print_success(f"✓ {assert_frame_protection(reply, mode, True, what, api_docs_page=True)}")
    found = written_directives(reply.values("content-security-policy")[0], what)
    assert found == literal_docs_policy(mode), f"{what}: the enforced policy {reply.values('content-security-policy')} is {found}, not this exact set of directives with exactly these sources, {literal_docs_policy(mode)} (R5; the order between directives is free)"
    assert reply.values("content-security-policy-report-only") == [], f"{what}: Content-Security-Policy-Report-Only is {reply.values('content-security-policy-report-only')}, wanted none: it is the web app's pages' alone"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", API_DOCS_PATHS)
@pytest.mark.parametrize("mode", [R4_MODES["managed"], R4_MODES["selfhosted"], R4_MODES["managed-public-url"]], ids=["managed", "selfhosted", "managed-public-url"])
async def test_r5_the_docs_pages_script_src_is_self_and_jsdelivr_while_the_web_app_page_beside_it_carries_the_hashes(mode: Mode, path: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R5: the API docs page carries no hash of the build, no ``'wasm-unsafe-eval'``, no ``'report-sample'``, no ``'unsafe-inline'``
    nor ``'unsafe-eval'``, no ``default-src``: ``script-src 'self' https://cdn.jsdelivr.net`` and nothing more. Barrier on the same middleware, built on a build
    with inline scripts: the web app page at ``/`` carries them in its ``script-src``, so the docs page's absence is R5's rule."""
    docs, page = docs_page_answer(path), TYPED_ANSWERS["text-html"]
    what = f"GET {path} (an API docs page) beside GET / with {mode.describe()}"
    print_section(f"H-55 w5 R5 script-src of the docs page: {what}")
    configure(monkeypatch, mode, tmp_path)
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", _write_tree(tmp_path / "build", FAKE_BUILD_PAGES))
    middleware = wrap(routing([page, docs]))

    barrier = await call(middleware, page.path)

    assert_bare_answer(barrier, page, f"barrier: GET {page.path}")
    assert_always_on(barrier, f"barrier: GET {page.path}, {what}")
    assert written_directives(barrier.values("content-security-policy")[0], what).get("script-src") == SCRIPT_SRC + FAKE_BUILD_SOURCES, f"barrier: {what}: the web app page does not carry the hashes of the build ({FAKE_BUILD_SOURCES}): nothing proves the docs page's absence"

    reply = await call(middleware, path)

    assert_bare_answer(reply, docs, what)
    assert_always_on(reply, what)
    policies = reply.values("content-security-policy")
    assert len(policies) == 1, f"{what}: Content-Security-Policy is {policies}, wanted one field"
    found = written_directives(policies[0], what)
    assert found.get("script-src") == ("'self'", "https://cdn.jsdelivr.net"), f"{what}: script-src is {found.get('script-src')} in {policies[0]!r}, wanted ('self', 'https://cdn.jsdelivr.net') and nothing more"
    forbidden = [token for token in ("default-src", "'unsafe-inline'", "'unsafe-eval'", "'wasm-unsafe-eval'", "'report-sample'", "sha256-", *NEVER_ENFORCED, *NO_REPORT_DIRECTIVES) if token in policies[0].lower()]
    assert not forbidden, f"{what}: the policy {policies[0]!r} holds {forbidden}"
    print_success(f"✓ script-src {found['script-src']}")


#: Not the API docs' two pages, though close: another path, another type, the same path with a suffix or a prefix. The page there
#: gets what the type gives it, never the docs page's scripts. ``(path, content_type, document)``.
NOT_API_DOCS_PAGES: dict[str, tuple[str, str, bool]] = {
    "another-html-document-under-api": (f"{API_V1_PREFIX}/other", "text/html", True),
    "docs-with-a-trailing-slash": (f"{API_V1_PREFIX}/docs/", "text/html", True),
    "redoc-with-a-trailing-slash": (f"{API_V1_PREFIX}/redoc/", "text/html", True),
    "a-path-starting-like-docs": (f"{API_V1_PREFIX}/docsx", "text/html", True),
    "the-swagger-oauth-redirect": (f"{API_V1_PREFIX}/docs/oauth2-redirect", "text/html", True),
    "the-swagger-start-script": (f"{API_V1_PREFIX}/docs/swagger-init.js", "text/javascript; charset=utf-8", False),
    "the-redoc-start-script": (f"{API_V1_PREFIX}/redoc/redoc-init.js", "application/javascript", False),
    "docs-under-mkdocs": (f"/mkdocs{API_V1_PREFIX}/docs", "text/html", True),
    "docs-answered-xhtml": (f"{API_V1_PREFIX}/docs", "application/xhtml+xml", True),
    "docs-answered-json": (f"{API_V1_PREFIX}/docs", "application/json", False),
    "redoc-answered-plain-text": (f"{API_V1_PREFIX}/redoc", "text/plain; charset=utf-8", False),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("key", list(NOT_API_DOCS_PAGES))
@pytest.mark.parametrize("mode", [R4_MODES["managed"], R4_MODES["selfhosted"], R4_MODES["selfhosted-frame-protection-true"]], ids=["managed", "selfhosted", "selfhosted-frame-protection-true"])
async def test_r5_what_is_not_an_api_docs_page_keeps_the_policy_of_its_type(mode: Mode, key: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R5's boundary: a document at another path under ``/api/`` (also ``/api/v1/docs/``, ``/api/v1/docsx``, Swagger's OAuth
    redirect, the documentation's copy of the path) or one of the two paths answered another type keeps what any such response
    gets (the trio for a document, ``frame-ancestors`` alone for the rest). Barrier, same middleware: the real docs page carries
    the docs policy, so the absence is the boundary and not a feature that does not exist."""
    path, content_type, document = NOT_API_DOCS_PAGES[key]
    # The barrier is the docs page at the other path: two routes at one path would answer with the first only
    typed, docs = TypedAnswer(path, content_type, PAGE_HTML, document=document), docs_page_answer(next(docs_path for docs_path in API_DOCS_PATHS if docs_path != path))
    what = f"GET {path} answered {content_type} with {mode.describe()}"
    print_section(f"H-55 w5 R5 not an API docs page: {what}")
    configure(monkeypatch, mode, tmp_path)
    middleware = wrap(routing([docs, typed]))

    barrier = await call(middleware, docs.path)

    assert_bare_answer(barrier, docs, f"barrier: GET {docs.path}")
    assert_always_on(barrier, f"barrier: GET {docs.path}, with {mode.describe()}")
    assert_frame_protection(barrier, mode, True, f"barrier: GET {docs.path}, with {mode.describe()}", api_docs_page=True)

    reply = await call(middleware, path)

    assert_bare_answer(reply, typed, what)
    assert_always_on(reply, what)
    assert not typed.api_docs_page, f"barrier: {what}: the case must not be one of the API docs' two pages"
    print_success(f"✓ {assert_frame_protection(reply, mode, document, what)}")


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", R4_MODES.values(), ids=list(R4_MODES))
async def test_r5_the_openapi_json_stays_a_response_that_is_no_document(mode: Mode, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """R5: ``/api/v1/openapi.json`` is JSON: with frame protection ``frame-ancestors 'self'`` alone, without it no policy, never
    the trio nor the docs page's scripts. Barrier, same middleware: the docs page carries the docs policy."""
    schema = TypedAnswer(f"{API_V1_PREFIX}/openapi.json", "application/json", API_JSON, document=False)
    docs = docs_page_answer(API_DOCS_PATHS[0])
    what = f"GET {schema.path} answered application/json with {mode.describe()}"
    print_section(f"H-55 w5 R5 the schema's JSON: {what}")
    configure(monkeypatch, mode, tmp_path)
    middleware = wrap(routing([docs, schema]))

    barrier = await call(middleware, docs.path)

    assert_bare_answer(barrier, docs, f"barrier: GET {docs.path}")
    assert_always_on(barrier, f"barrier: GET {docs.path}, with {mode.describe()}")
    assert_frame_protection(barrier, mode, True, f"barrier: GET {docs.path}, with {mode.describe()}", api_docs_page=True)

    reply = await call(middleware, schema.path)

    assert_bare_answer(reply, schema, what)
    assert_always_on(reply, what)
    print_success(f"✓ {assert_frame_protection(reply, mode, False, what)}")
