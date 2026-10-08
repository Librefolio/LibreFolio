"""HTTP compression and HTML freshness on the live backend: what ``backend/app/main.py`` does to each kind of response (M, R2 P0; L, #26).

``app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)`` sits in front
of everything the backend serves, so its contract is as much about what it must leave
alone as about what it compresses. For a client that sends ``Accept-Encoding: gzip``:

* JSON above 1 KiB (``/api/v1/openapi.json``) travels gzip-encoded with
  ``Vary: Accept-Encoding`` and decodes to the very document an ``identity`` client gets;
  that client gets plain bytes, still with ``Vary``, so a shared cache keeps the two apart.
* A body under 1 KiB (``/api/v1/system/health``) is left alone.
* SvelteKit's hashed chunks (``/_app/immutable/*.js``) travel gzip-encoded and keep their
  year-long ``immutable`` Cache-Control and their ETag, so ``If-None-Match`` still answers
  304; a ``Range`` request gets 206 over the identity bytes, never a slice of gzip.
* PNG images are never compressed: they already are.
* The SPA fallback (``200.html``, served for client-side routes) travels gzip-encoded and
  stays ``no-cache``: it names the chunks of the current build.
* Server-Sent Events (``/api/v1/assets/provider/search/stream``) are never compressed:
  the search box reads each provider's results as they arrive.

Every HTML document the backend serves from the frontend build carries ``Cache-Control``
with both ``no-cache`` and ``must-revalidate`` (#26, «the plugin does not work on
Chromium»): ``/``, the exact ``.html`` files of the build root (``/index.html``,
``/200.html``, ``/offline.html``) and the SPA fallback. The entry documents name the
hashed chunks of the CURRENT build: one served without the header is reused from the
browser's heuristic cache (a fraction of its ``Last-Modified`` age), and with it the
previous build and every one of its year-long ``immutable`` chunks, until a manual
reload. Each document is requested as a browser requests it, gzip accepted, and must be
the app's own: ``text/html`` and, for the entry documents, naming at least one
``/_app/immutable/`` chunk, so a lane without a frontend build fails here instead of
passing on the JSON that ``/`` answers then. The cure stops at the documents: no chunk
that ``/`` names may turn ``no-cache`` (their ``immutable`` is pinned above).

Nothing here is hard-coded that the build decides: chunk URLs (content hashes) and PNG
URLs are read from the ``index.html`` the backend serves, and a candidate is used only
after its size proves it crosses the compression threshold; the HTML documents are the
ones ``main.py`` serves by name plus the ``offline.html`` of ``frontend/static``, and the
client-side route is a fresh one, so no file of the build can answer it. httpx decodes
gzip transparently, so every body is read with ``aiter_raw()``: the bytes that
travelled, not the header's claim about them.

The backend is the lane's shared one, started by the runner after ``./dev.py server
--test`` built the frontend. Every request is a GET on a public resource, except for the
SSE check: the stream needs a session, so that test registers its own user, searches
only the offline ``mockprov`` provider (fixed in-memory results, no network), and deletes
the user before it returns.
"""

import gzip
import json
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urljoin
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.services import user_service
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success

settings = get_settings()
SERVER_URL = f"http://localhost:{settings.TEST_PORT}"
API_BASE = f"{SERVER_URL}/api/v1"
TIMEOUT = 30.0

#: GZipMiddleware(minimum_size=...) in backend/app/main.py: the contract under test.
MINIMUM_SIZE = 1024
GZIP_MAGIC = b"\x1f\x8b"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# References in the served index.html, absolute ("/_app/…") or relative ("./_app/…").
IMMUTABLE_JS_REF = re.compile(r"""["']((?:\.{1,2}/|/)?_app/immutable/[^"'\s]+?\.js)["']""")
PNG_REF = re.compile(r"""(?:href|src)=["']([^"'\s]+?\.png)["']""")

#: #26: every HTML document of the frontend build is revalidated before a browser reuses it.
REVALIDATE = frozenset({"no-cache", "must-revalidate"})
#: The app's HTML entry points: ``/`` (index.html) and the two build-root files main.py names, requested
#: directly. Each names the hashed chunks of its build.
ENTRY_DOCUMENTS = ("/", "/index.html", "/200.html")
#: HTML files of the build root that are not the app: the service worker's offline page names no chunk.
STANDALONE_DOCUMENTS = ("/offline.html",)

PASSWORD = "HttpGzipPass123!"
SOLE_ADMIN_DELETE_DETAIL = "Cannot delete account: you are the only administrator"


@pytest.fixture(scope="module")
def test_server():
    """Attach to the runner-owned backend, or start its in-process test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ---------------------------------------------------------------------------
# Reading what travelled
# ---------------------------------------------------------------------------


async def fetch(client: httpx.AsyncClient, url: str, *, accept_encoding: str, headers: dict | None = None, params: dict | None = None) -> tuple[httpx.Response, bytes]:
    """GET ``url``; return the response and its body exactly as it travelled (no content decoding)."""
    request_headers = {"Accept-Encoding": accept_encoding, **(headers or {})}
    async with client.stream("GET", url, headers=request_headers, params=params, timeout=TIMEOUT) as response:
        wire = b"".join([chunk async for chunk in response.aiter_raw()])
    return response, wire


def vary(response: httpx.Response) -> set[str]:
    return {token.strip().lower() for value in response.headers.get_list("vary") for token in value.split(",") if token.strip()}


def cache_directives(response: httpx.Response) -> set[str]:
    return {token.strip().lower() for token in response.headers.get("cache-control", "").split(",") if token.strip()}


def gunzip_wire(response: httpx.Response, wire: bytes) -> bytes:
    """Check the body travelled gzip-encoded, smaller than it is, and return it decoded."""
    assert response.headers.get("content-encoding") == "gzip", f"{response.url}: not gzip-encoded (headers: {dict(response.headers)})"
    assert "accept-encoding" in vary(response), f"{response.url}: a compressed response must carry Vary: Accept-Encoding"
    assert wire[:2] == GZIP_MAGIC, f"{response.url}: Content-Encoding says gzip but the bytes that travelled are not a gzip stream"
    if "content-length" in response.headers:
        assert int(response.headers["content-length"]) == len(wire), f"{response.url}: Content-Length does not describe the compressed body"
    decoded = gzip.decompress(wire)
    assert len(wire) < len(decoded), f"{response.url}: gzip made the body larger ({len(wire)} >= {len(decoded)} bytes)"
    return decoded


def assert_frontend_served(response: httpx.Response) -> None:
    served = response.status_code == 200 and response.headers.get("content-type", "").startswith("text/html")
    hint = "Run `./dev.py test api http-compression`: its shared backend (`./dev.py server --test`) builds the frontend first."
    assert served, f"{response.url}: {response.status_code} {response.headers.get('content-type')} — the backend under test serves no frontend build. {hint}"


async def served_index(client: httpx.AsyncClient) -> str:
    response, wire = await fetch(client, f"{SERVER_URL}/", accept_encoding="identity")
    assert_frontend_served(response)
    return wire.decode("utf-8")


def received_text(response: httpx.Response, wire: bytes) -> str:
    """The text a browser reads from the bytes that travelled, gzip-encoded or not."""
    body = gzip.decompress(wire) if response.headers.get("content-encoding") == "gzip" else wire
    return body.decode("utf-8")


def assert_entry_document(response: httpx.Response, wire: bytes) -> None:
    """The app's HTML entry point: served from the build, and naming the hashed chunks of that build."""
    assert_frontend_served(response)
    assert IMMUTABLE_JS_REF.search(received_text(response, wire)), f"{response.url}: this HTML names no /_app/immutable/ chunk, so it is not the app's entry document"


async def largest_immutable_chunk(client: httpx.AsyncClient) -> tuple[str, bytes]:
    """The largest ``/_app/immutable/*.js`` chunk ``index.html`` references, with its identity bytes."""
    html = await served_index(client)
    urls = sorted({urljoin(f"{SERVER_URL}/", ref) for ref in IMMUTABLE_JS_REF.findall(html)})
    assert urls, "the served index.html references no /_app/immutable/*.js chunk"
    sized = []
    for url in urls:
        response, body = await fetch(client, url, accept_encoding="identity")
        assert response.status_code == 200, f"{url}: {response.status_code}"
        assert "content-encoding" not in response.headers, f"{url}: encoded although the client accepts identity only"
        sized.append((len(body), url, body))
    size, url, body = max(sized)
    assert size >= MINIMUM_SIZE, f"no referenced chunk reaches the {MINIMUM_SIZE}-byte threshold (largest: {url}, {size} bytes): nothing to prove"
    print_info(f"  chunk under test: {url} ({size} bytes, largest of {len(urls)} referenced)")
    return url, body


# ---------------------------------------------------------------------------
# A user of our own, for the one endpoint that needs a session
# ---------------------------------------------------------------------------


async def _register_and_login(client: httpx.AsyncClient) -> int:
    username = f"http_gzip_{uuid4().hex[:16]}"
    registered = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": PASSWORD}, timeout=TIMEOUT)
    assert registered.status_code == 201, registered.text
    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": PASSWORD}, timeout=TIMEOUT)
    assert login.status_code == 200, login.text
    session = login.cookies.get("session")
    assert session is not None
    client.cookies.set("session", session)
    return registered.json()["user"]["id"]


async def _delete_own_user(client: httpx.AsyncClient, user_id: int) -> None:
    """Delete only this test's account, with the exact sole-admin fallback."""
    response = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)
    if response.status_code == 400 and response.json().get("detail") == SOLE_ADMIN_DELETE_DETAIL:
        is_test_db, _ = verify_test_database()
        assert is_test_db, "Refusing sole-admin cleanup outside the test database"
        async with AsyncSession(get_async_engine()) as session:
            assert await user_service.delete_user(session, user_id)
        return
    assert response.status_code == 200, response.text


@asynccontextmanager
async def own_user() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        user_id = await _register_and_login(client)
        try:
            yield client
        finally:
            await _delete_own_user(client, user_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestApiJson:
    @pytest.mark.asyncio
    async def test_large_json_is_gzipped_for_gzip_clients_only(self, test_server):
        print_section("GZIP-001: openapi.json, gzip vs identity")
        url = f"{API_BASE}/openapi.json"
        async with httpx.AsyncClient() as client:
            plain, plain_wire = await fetch(client, url, accept_encoding="identity")
            packed, packed_wire = await fetch(client, url, accept_encoding="gzip")

        assert plain.status_code == 200 and packed.status_code == 200
        assert len(plain_wire) >= MINIMUM_SIZE, f"openapi.json is {len(plain_wire)} bytes: below the threshold, it proves nothing"
        assert "content-encoding" not in plain.headers, "an identity-only client received an encoded body"
        assert "accept-encoding" in vary(plain), "the identity response must also carry Vary: Accept-Encoding, or a shared cache could serve it to a gzip client and the reverse"
        assert json.loads(gunzip_wire(packed, packed_wire)) == json.loads(plain_wire)
        print_success(f"openapi.json: {len(plain_wire)} bytes identity, {len(packed_wire)} bytes gzip")

    @pytest.mark.asyncio
    async def test_small_json_is_left_alone(self, test_server):
        print_section("GZIP-002: a body under the threshold is not compressed")
        async with httpx.AsyncClient() as client:
            response, wire = await fetch(client, f"{API_BASE}/system/health", accept_encoding="gzip")

        assert response.status_code == 200
        assert "content-encoding" not in response.headers, f"a {len(wire)}-byte body was compressed"
        assert len(wire) < MINIMUM_SIZE, f"/system/health is {len(wire)} bytes: no longer a small body, pick another"
        assert json.loads(wire) == {"status": "ok"}
        print_success(f"/system/health: {len(wire)} bytes, sent as is")


class TestImmutableChunks:
    @pytest.mark.asyncio
    async def test_chunk_is_gzipped_and_keeps_its_cache_contract(self, test_server):
        print_section("GZIP-003: immutable chunk, gzip + Cache-Control immutable + ETag")
        async with httpx.AsyncClient() as client:
            url, identity = await largest_immutable_chunk(client)
            response, wire = await fetch(client, url, accept_encoding="gzip")

        assert response.status_code == 200
        assert gunzip_wire(response, wire) == identity
        assert "immutable" in cache_directives(response), f"Cache-Control lost on the gzip response: {response.headers.get('cache-control')!r}"
        assert response.headers.get("etag"), "the gzip response lost its ETag"
        print_success(f"{len(identity)} bytes → {len(wire)} gzip, Cache-Control {response.headers['cache-control']!r}")

    @pytest.mark.asyncio
    async def test_chunk_revalidates_with_304(self, test_server):
        print_section("GZIP-004: If-None-Match on a gzip client answers 304")
        async with httpx.AsyncClient() as client:
            url, _ = await largest_immutable_chunk(client)
            first, _ = await fetch(client, url, accept_encoding="gzip")
            etag = first.headers.get("etag")
            assert etag, f"{url}: no ETag to revalidate with"
            response, wire = await fetch(client, url, accept_encoding="gzip", headers={"If-None-Match": etag})

        assert response.status_code == 304, f"If-None-Match {etag} answered {response.status_code}"
        assert wire == b""
        assert "content-encoding" not in response.headers
        print_success(f"ETag {etag} → 304, empty body")

    @pytest.mark.asyncio
    async def test_range_request_gets_identity_bytes(self, test_server):
        print_section("GZIP-005: a Range request is answered with identity bytes")
        last = MINIMUM_SIZE - 1
        async with httpx.AsyncClient() as client:
            url, identity = await largest_immutable_chunk(client)
            response, wire = await fetch(client, url, accept_encoding="gzip", headers={"Range": f"bytes=0-{last}"})

        assert response.status_code == 206, f"Range bytes=0-{last} answered {response.status_code}"
        assert "content-encoding" not in response.headers, "a byte range of a gzip stream is not a byte range of the file"
        assert response.headers.get("content-range") == f"bytes 0-{last}/{len(identity)}"
        assert wire == identity[:MINIMUM_SIZE]
        print_success(f"206 {response.headers['content-range']}")


class TestUntouchedResponses:
    @pytest.mark.asyncio
    async def test_png_images_are_never_compressed(self, test_server):
        print_section("GZIP-006: PNG images travel as they are")
        sizes = {}
        async with httpx.AsyncClient() as client:
            html = await served_index(client)
            urls = sorted({urljoin(f"{SERVER_URL}/", ref) for ref in PNG_REF.findall(html)})
            assert urls, "the served index.html references no PNG"
            for url in urls:
                response, wire = await fetch(client, url, accept_encoding="gzip")
                assert response.status_code == 200, f"{url}: {response.status_code}"
                assert response.headers.get("content-type") == "image/png", f"{url}: {response.headers.get('content-type')}"
                assert wire.startswith(PNG_SIGNATURE), f"{url}: the bytes that travelled are not a PNG"
                assert "content-encoding" not in response.headers, f"{url}: a PNG was compressed"
                sizes[url] = len(wire)

        assert max(sizes.values()) >= MINIMUM_SIZE, f"no referenced PNG reaches the {MINIMUM_SIZE}-byte threshold: nothing to prove ({sizes})"
        print_success(f"{len(sizes)} PNG(s) sent as is: {sizes}")

    @pytest.mark.asyncio
    async def test_server_sent_events_are_never_compressed(self, test_server):
        print_section("GZIP-007: the search SSE stream travels as plain text")
        query = f"gzip{uuid4().hex[:8]}"
        async with own_user() as client:
            response, wire = await fetch(client, f"{API_BASE}/assets/provider/search/stream", accept_encoding="gzip", params={"q": query, "providers": "mockprov"})

        assert response.status_code == 200, wire[:500]
        assert response.headers.get("content-type", "").startswith("text/event-stream")
        assert "content-encoding" not in response.headers, "the SSE stream was compressed"
        events = [json.loads(line.removeprefix("data: ")) for line in wire.decode("utf-8").splitlines() if line.startswith("data: ")]
        mock_results = next((event for event in events if event.get("event") == "provider_results" and event.get("provider_code") == "mockprov"), None)
        assert mock_results is not None, f"no mockprov results in the stream: {events}"
        assert f"MOCK_{query.upper()}" in {item["identifier"] for item in mock_results["results"]}
        assert events[-1].get("event") == "done", f"the stream must end with its done event: {events}"
        print_success(f"{len(wire)} bytes of text/event-stream, {len(events)} events, not encoded")


class TestSpaFallback:
    @pytest.mark.asyncio
    async def test_spa_fallback_is_gzipped_and_never_cached(self, test_server):
        print_section("GZIP-008: a client-side route gets 200.html, gzip, no-cache")
        url = f"{SERVER_URL}/http-compression-probe/{uuid4().hex}"
        async with httpx.AsyncClient() as client:
            plain, plain_wire = await fetch(client, url, accept_encoding="identity")
            packed, packed_wire = await fetch(client, url, accept_encoding="gzip")

        assert_frontend_served(plain)
        assert_frontend_served(packed)
        assert len(plain_wire) >= MINIMUM_SIZE, f"the SPA fallback is {len(plain_wire)} bytes: below the threshold, it proves nothing"
        assert "no-cache" in cache_directives(plain), f"the fallback must not be cached: {plain.headers.get('cache-control')!r}"
        assert gunzip_wire(packed, packed_wire) == plain_wire
        assert "no-cache" in cache_directives(packed), f"Cache-Control lost on the gzip response: {packed.headers.get('cache-control')!r}"
        print_success(f"200.html: {len(plain_wire)} bytes identity, {len(packed_wire)} bytes gzip, Cache-Control {packed.headers['cache-control']!r}")


class TestHtmlRevalidation:
    """#26: the documents that name the chunks are revalidated on every load; the chunks they name are not."""

    @pytest.mark.asyncio
    async def test_every_html_document_revalidates(self, test_server):
        print_section("CACHE-001: every HTML document of the build carries no-cache, must-revalidate")
        # A fresh client-side route: no file of the build can answer it, only the SPA fallback.
        client_route = f"/settings/cache-probe-{uuid4().hex[:12]}"
        documents: dict[str, httpx.Response] = {}
        async with httpx.AsyncClient() as client:
            for path in (*ENTRY_DOCUMENTS, client_route, *STANDALONE_DOCUMENTS):
                # Requested as a browser requests it, gzip accepted: the response a browser stores.
                response, wire = await fetch(client, f"{SERVER_URL}{path}", accept_encoding="gzip")
                if path in STANDALONE_DOCUMENTS:
                    assert_frontend_served(response)
                else:
                    assert_entry_document(response, wire)
                documents[path] = response

        revalidated = {path: REVALIDATE <= cache_directives(response) for path, response in documents.items()}
        report = "\n".join(f"  {'✓' if ok else '✘'} GET {path} → Cache-Control: {documents[path].headers.get('cache-control')!r}" for path, ok in revalidated.items())
        print_info(f"Cache-Control of each HTML document:\n{report}")
        stale = [path for path, ok in revalidated.items() if not ok]
        assert not stale, (
            f"{len(stale)} of {len(documents)} HTML documents of the frontend build can be reused from the browser cache without asking the server. "
            "Each needs Cache-Control with both no-cache and must-revalidate: a browser that reuses a cached copy keeps the previous build, "
            f"and every /_app/immutable chunk it names, until a manual reload (#26).\n{report}"
        )
        print_success(f"{len(documents)} HTML documents, each revalidated before it is reused")

    @pytest.mark.asyncio
    async def test_chunks_the_root_names_are_never_no_cache(self, test_server):
        print_section("CACHE-002: the chunks the root names are never no-cache")
        chunks: dict[str, httpx.Response] = {}
        async with httpx.AsyncClient() as client:
            html = await served_index(client)
            urls = sorted({urljoin(f"{SERVER_URL}/", ref) for ref in IMMUTABLE_JS_REF.findall(html)})
            assert urls, "the served index.html references no /_app/immutable/*.js chunk"
            for url in urls:
                response, _ = await fetch(client, url, accept_encoding="gzip")
                assert response.status_code == 200, f"{url}: {response.status_code}"
                chunks[url] = response

        revalidated = [f"  GET {url} → Cache-Control: {response.headers.get('cache-control')!r}" for url, response in chunks.items() if "no-cache" in cache_directives(response)]
        assert not revalidated, "A content-hashed chunk never changes under its name: no-cache only costs one more round trip per chunk on every load. The #26 cure belongs to the HTML documents, not to /_app.\n" + "\n".join(revalidated)
        print_success(f"{len(chunks)} chunk(s) named by /, none no-cache (their immutable is GZIP-003's)")
