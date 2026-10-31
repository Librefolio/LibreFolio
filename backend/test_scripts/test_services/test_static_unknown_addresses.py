"""An address the backend does not know leads a browser to the app, and tells a client the truth (workstream H, checkpoint 1, lot FB-23).

Under test: ``backend/app/services/platform/static_site.py`` (``frontend_catchall`` and ``mkdocs_static``, installed by
``install_static_site``) behind ``install_api_docs`` (``backend/app/api/api_docs.py``). Today a person who types or follows an
address that is not ours (``/api/v1/xyz``, ``/api/v1/docs`` on an instance whose API documentation is off, a documentation page that
does not exist) lands on a bare white page, ``<h1>Not Found</h1>``, with nowhere to go. The contract:

(a) For a missing address under ``api/`` (every unknown ``/api/v1/...``, and ``/api/v1/docs``, ``/api/v1/redoc`` and
    ``/api/v1/openapi.json`` when the API documentation is off) and for a missing file under ``/mkdocs/``:

    - a BROWSER NAVIGATION gets a redirect, ``302`` with ``Location: /``;
    - every other request gets a JSON 404, ``{"detail": "Not Found"}``, ``Content-Type: application/json``.

(b) A browser navigation is a request with ``Sec-Fetch-Mode: navigate``; or with no ``Sec-Fetch-Mode`` header at all and an
    ``Accept`` that contains ``text/html``. httpx's default ``Accept: */*`` is not a navigation, nor is a request with another
    ``Sec-Fetch-Mode`` (a ``fetch()`` of the web app: ``cors``, ``same-origin``, ``no-cors``) even when its ``Accept`` names ``text/html``.
(c) Nothing that exists changes: the SPA fallback (200) for a non-API path, the documentation's pages and its index, a real API
    route, and the API documentation pages themselves when they are on. A missing chunk under ``/_app`` stays Starlette's plain 404
    (a navigation header there is not our case and is not tested).

Each case runs on a fresh ``FastAPI()`` as ``main.py`` builds its own (no FastAPI pages, no schema address), with a real API
route ``/api/v1/probe``, ``install_api_docs`` (off, but for the controls) and then ``install_static_site`` over a fake build and a fake
documentation site under ``tmp_path`` (``FRONTEND_BUILD_DIR`` and ``SITE_DIR`` swapped in with ``monkeypatch``, as
``test_static_cache_policy`` does). Requests go through ``httpx.ASGITransport``; the lifespan never runs. No DB, no server, no network.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from backend.app.api.api_docs import install_api_docs
from backend.app.config import API_V1_PREFIX
from backend.app.services.platform import static_site
from backend.test_scripts.test_utils import print_section, print_success

INDEX_HTML = b"<!doctype html><title>index</title>"
FALLBACK_HTML = b"<!doctype html><title>spa fallback</title>"
DOCS_INDEX_HTML = b"<!doctype html><title>docs home</title>"
DOCS_PAGE_HTML = b"<!doctype html><title>docs user guide</title>"
JSON_404 = {"detail": "Not Found"}

#: The addresses that are not ours: unknown API paths, the API documentation (off here), a missing documentation file.
MISSING_ADDRESSES = {
    "api-unknown-route": f"{API_V1_PREFIX}/xyz",
    "api-unknown-below-a-real-route": f"{API_V1_PREFIX}/probe/xyz",
    "api-prefix-only": "/api/",
    "api-other-version": "/api/v2/anything",
    "api-docs-off": f"{API_V1_PREFIX}/docs",
    "api-redoc-off": f"{API_V1_PREFIX}/redoc",
    "api-openapi-json-off": f"{API_V1_PREFIX}/openapi.json",
    "api-docs-start-script-off": f"{API_V1_PREFIX}/docs/swagger-init.js",
    "mkdocs-missing-page": "/mkdocs/no-such-page.html",
    "mkdocs-missing-folder": "/mkdocs/no-such-folder/",
    "mkdocs-missing-deep": "/mkdocs/user/no/such/page/",
}

#: Requests that are a browser navigation (b), by what they send.
NAVIGATIONS = {
    "sec-fetch-mode-navigate": {"Sec-Fetch-Mode": "navigate"},
    "sec-fetch-mode-navigate-with-accept-any": {"Sec-Fetch-Mode": "navigate", "Accept": "*/*"},
    "accept-html-without-sec-fetch": {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
    "accept-only-html-without-sec-fetch": {"Accept": "text/html"},
}
#: Requests that are not (b): the client, a script, a probe, a fetch() of the web app.
CLIENTS = {
    "httpx-default-accept-any": {},
    "accept-json": {"Accept": "application/json"},
    "accept-any-explicit": {"Accept": "*/*"},
    "fetch-cors-asking-html": {"Sec-Fetch-Mode": "cors", "Accept": "text/html"},
    "fetch-same-origin": {"Sec-Fetch-Mode": "same-origin"},
    "fetch-no-cors-asking-html": {"Sec-Fetch-Mode": "no-cors", "Accept": "text/html,*/*"},
}


def _build(tmp_path: Path) -> tuple[Path, Path]:
    """A fake build (index, SPA fallback, one chunk) and a fake documentation site (home, one page)."""
    build, site = tmp_path / "build", tmp_path / "site"
    files = {
        build / "index.html": INDEX_HTML,
        build / "200.html": FALLBACK_HTML,
        build / "_app" / "immutable" / "chunks" / "a1b2.js": b"export const chunk = 'a1b2';\n",
        site / "index.html": DOCS_INDEX_HTML,
        site / "user" / "index.html": DOCS_PAGE_HTML,
    }
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return build, site


def _app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, api_docs: bool) -> FastAPI:
    """A fresh app as ``main.py`` builds its own: a real API route, our API pages (or not), then the static site."""
    build, site = _build(tmp_path)
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build)
    monkeypatch.setattr(static_site, "SITE_DIR", site)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get(f"{API_V1_PREFIX}/probe")
    async def probe() -> dict[str, bool]:
        return {"ok": True}

    install_api_docs(app, enabled=api_docs)
    static_site.install_static_site(app)
    return app


async def _get(app: FastAPI, path: str, headers: dict[str, str] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        return await client.get(path, headers=headers)


@pytest.fixture
def site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """The app with the API documentation off, and the barrier that makes every negative case mean something: the fake build and the fake documentation are the ones served."""
    return _app(tmp_path, monkeypatch, api_docs=False)


async def _assert_served_controls(app: FastAPI) -> None:
    """Barrier: the SPA fallback, the documentation's home and page, and a real API route are served, so a 404 or a redirect below comes from the address, not from a broken fixture."""
    checks = {"/some/client/route": FALLBACK_HTML, "/mkdocs/": DOCS_INDEX_HTML, "/mkdocs/user/": DOCS_PAGE_HTML}
    for path, body in checks.items():
        response = await _get(app, path)
        assert (response.status_code, response.content) == (200, body), f"barrier: GET {path} answered {response.status_code} {response.content[:60]!r}, not the fake build's own file"
    probe = await _get(app, f"{API_V1_PREFIX}/probe")
    assert (probe.status_code, probe.json()) == (200, {"ok": True}), f"barrier: the real API route answers: {probe.status_code} {probe.text}"


# =============================================================================
# (a) + (b): a navigation is sent to the app
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("navigation", NAVIGATIONS.values(), ids=list(NAVIGATIONS))
@pytest.mark.parametrize("address", MISSING_ADDRESSES.values(), ids=list(MISSING_ADDRESSES))
async def test_a_browser_navigation_to_an_unknown_address_is_redirected_to_the_app(site: FastAPI, address: str, navigation: dict[str, str]) -> None:
    """FB-23a: ``Sec-Fetch-Mode: navigate``, or an ``Accept`` with ``text/html`` and no ``Sec-Fetch-Mode``: ``302`` and ``Location: /``, whatever the missing address under ``api/`` or ``/mkdocs/``."""
    print_section(f"FB-23a: GET {address} {navigation}")
    await _assert_served_controls(site)

    response = await _get(site, address, navigation)

    assert response.status_code == 302, f"a navigation to {address} ({navigation}) is redirected: got {response.status_code} {response.headers.get('content-type')!r} {response.content[:80]!r}"
    assert response.headers.get_list("location") == ["/"], f"the redirect goes to the app's home: {response.headers.get_list('location')}"
    print_success("302 -> /")


# =============================================================================
# (a) + (b): everything else is told a JSON 404
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("client", CLIENTS.values(), ids=list(CLIENTS))
@pytest.mark.parametrize("address", MISSING_ADDRESSES.values(), ids=list(MISSING_ADDRESSES))
async def test_any_other_request_to_an_unknown_address_gets_a_json_404(site: FastAPI, address: str, client: dict[str, str]) -> None:
    """FB-23b: a client (httpx's default ``Accept: */*``, JSON, a ``fetch()`` of the web app with another ``Sec-Fetch-Mode`` even asking for HTML) gets ``404`` and ``{"detail": "Not Found"}`` as ``application/json``."""
    print_section(f"FB-23b: GET {address} {client}")
    await _assert_served_controls(site)

    response = await _get(site, address, client)

    assert response.status_code == 404, f"{address} ({client}) is a 404: got {response.status_code} {response.headers.get('location')!r}"
    assert response.headers.get("content-type", "").split(";")[0].strip() == "application/json", f"the 404 is JSON: {response.headers.get('content-type')!r} {response.content[:80]!r}"
    assert response.json() == JSON_404, f"the body is {JSON_404}: {response.text}"
    print_success("404 JSON")


# =============================================================================
# the API documentation: off leads away, on is served to everyone
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("path", [f"{API_V1_PREFIX}/docs", f"{API_V1_PREFIX}/redoc", f"{API_V1_PREFIX}/openapi.json"])
async def test_the_api_documentation_is_served_to_a_navigation_when_it_is_on_and_is_a_redirect_when_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    """FB-23c: the same navigation to a documentation address: with ``install_api_docs(app, enabled=True)`` the two pages are 200 HTML (``openapi.json`` is not published by an app built with ``openapi_url=None``, on or off: it is a redirect for a navigation either way); with ``enabled=False`` all three are redirects to ``/``. Barrier: the page of the ``enabled=True`` app is our page (200)."""
    print_section(f"FB-23c: GET {path} with the API documentation on and off")
    navigation = NAVIGATIONS["sec-fetch-mode-navigate"]
    on = _app(tmp_path / "on", monkeypatch, api_docs=True)
    off = _app(tmp_path / "off", monkeypatch, api_docs=False)

    served = await _get(on, path, navigation)
    refused = await _get(off, path, navigation)

    if path.endswith("openapi.json"):
        assert served.status_code == 302, f"openapi.json is not published by an app built without openapi_url: a navigation is redirected, got {served.status_code}"
    else:
        assert served.status_code == 200 and served.headers.get("content-type", "").startswith("text/html"), f"barrier: with the API documentation on, a navigation to {path} gets our page: {served.status_code} {served.headers.get('content-type')!r}"
    assert (refused.status_code, refused.headers.get_list("location")) == (302, ["/"]), f"with the API documentation off, a navigation to {path} is redirected to /: {refused.status_code} {refused.text[:80]!r}"
    print_success(f"{path}: on {served.status_code}, off 302 -> /")


# =============================================================================
# (c): nothing that exists changes
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("headers", [*NAVIGATIONS.values(), *CLIENTS.values()], ids=[*NAVIGATIONS, *CLIENTS])
async def test_what_exists_is_served_as_before_to_navigations_and_clients_alike(site: FastAPI, headers: dict[str, str]) -> None:
    """FB-23d: the SPA fallback for a non-API path, the documentation's home and page, and a real API route answer 200 with their own content, whoever asks."""
    for path, body in {"/some/client/route": FALLBACK_HTML, "/mkdocs/": DOCS_INDEX_HTML, "/mkdocs/user/": DOCS_PAGE_HTML}.items():
        response = await _get(site, path, headers)
        assert (response.status_code, response.content) == (200, body), f"GET {path} ({headers}) is served as before: {response.status_code} {response.content[:60]!r}"
    probe = await _get(site, f"{API_V1_PREFIX}/probe", headers)
    assert (probe.status_code, probe.json()) == (200, {"ok": True}), f"the real API route answers: {probe.status_code} {probe.text}"
    print_success("fallback, documentation and API route unchanged")


@pytest.mark.asyncio
async def test_a_missing_chunk_under_app_stays_a_plain_404(site: FastAPI) -> None:
    """FB-23e: ``/_app/...`` is the mount's own 404 for a request that is no navigation (the case is not defined for a navigation): neither a redirect nor the app's HTML. Barrier: an existing chunk is served."""
    chunk = await _get(site, "/_app/immutable/chunks/a1b2.js")
    assert chunk.status_code == 200, f"barrier: the mounted chunk is served: {chunk.status_code}"

    missing = await _get(site, "/_app/immutable/chunks/missing.js")

    assert missing.status_code == 404 and not missing.headers.get("location"), f"a missing chunk is a 404, not a redirect: {missing.status_code} {missing.headers.get('location')!r}"
    print_success("missing chunk: 404")
