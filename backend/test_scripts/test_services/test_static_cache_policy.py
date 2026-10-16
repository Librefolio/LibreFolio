"""
The cache policy of the web app's files (workstream H, platform, checkpoint CP7b-1, F28).

Under test: ``backend/app/services/platform/static_site.py``, the ``/_app`` mount that ``install_static_site`` adds when the
build has ``index.html`` and ``_app/`` (``ImmutableStaticFiles`` today), and the HTML documents of the build. The contract:

(a) A file under ``/_app/immutable/`` carries its content's hash in its name: a new build, a new name. It is sent with
    ``Cache-Control: public, max-age=31536000, immutable``, as today, and so is the 304 that answers its revalidation.
(b) Any other file under ``/_app`` keeps its name from one build to the next: SvelteKit's ``env.js`` and ``version.json``,
    and ``immutable.json``, a file whose name only begins like the folder. Its only ``Cache-Control`` has ``no-cache``
    among its directives, and neither ``immutable`` nor ``max-age=31536000``: the browser revalidates it at every use.
    The 304 that answers the revalidation says the same, or the browser would keep its copy for a year from then on.
(c) The HTML documents (``/``, ``/index.html``, the SPA fallback of a client-side route) keep ``Cache-Control: no-cache,
    must-revalidate`` (``REVALIDATE_HTML``), as today.

Each case runs on a fresh ``FastAPI()`` holding the static site of a fake build under ``tmp_path``, twice: the build folder
itself, and the same build reached through a symlink, as a release folder behind a ``current`` link (``StaticFiles``
resolves the path of the file it serves, never the folder it was given). ``FRONTEND_BUILD_DIR`` is swapped in with
``monkeypatch`` before ``install_static_site`` runs, as ``test_app_lifecycle`` does; requests go through
``httpx.ASGITransport``, and the lifespan never runs. A barrier comes before every assertion on a header: the ``/_app``
mount exists, and the file itself was sent (status and body), so neither a fallback nor a 404 satisfies an absence.
No DB, no server, no network.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from starlette.routing import Mount

from backend.app.services.platform import static_site
from backend.test_scripts.test_utils import print_section, print_success

#: What a file named after its content is sent with, as today.
IMMUTABLE = "public, max-age=31536000, immutable"
#: What an HTML document of the build is sent with, as today (``REVALIDATE_HTML``).
REVALIDATED_HTML = "no-cache, must-revalidate"

INDEX_HTML = b"<!doctype html><title>index</title>"

#: The fake build: path relative to the build folder, and content.
BUILD_FILES: dict[str, bytes] = {
    "index.html": INDEX_HTML,
    "_app/immutable/chunks/a1b2.js": b"export const chunk = 'a1b2';\n",
    "_app/immutable/assets/start.Cf3a1b2c.css": b"body { margin: 0 }\n",
    "_app/env.js": b"export const env={}\n",
    "_app/version.json": b'{"version":"1760572800000"}',
    "_app/immutable.json": b'{"named":"like the folder, and not in it"}',
}

#: Under /_app/immutable/: the hash is in the name.
HASHED = {"chunk-js": "/_app/immutable/chunks/a1b2.js", "asset-css": "/_app/immutable/assets/start.Cf3a1b2c.css"}
#: The rest of /_app: the same name in every build.
UNHASHED = {"env-js": "/_app/env.js", "version-json": "/_app/version.json", "named-like-the-folder": "/_app/immutable.json"}
#: HTML documents: the URL, and the file that answers it (the build has no 200.html, so the SPA fallback is index.html).
HTML_DOCUMENTS = {"root": ("/", "index.html"), "index-html": ("/index.html", "index.html"), "spa-fallback": ("/settings/profile", "index.html")}


@pytest.fixture(params=["build-folder", "build-behind-a-symlink"])
def site(request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """A fresh app holding the static site of the fake build, the build reached directly or through a symlink."""
    build = tmp_path / "release-1"
    for relative, content in BUILD_FILES.items():
        (build / relative).parent.mkdir(parents=True, exist_ok=True)
        (build / relative).write_bytes(content)
    served = build
    if request.param == "build-behind-a-symlink":
        served = tmp_path / "current"
        served.symlink_to(build, target_is_directory=True)
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", served)

    app = FastAPI()
    static_site.install_static_site(app)

    mounts = [route.path for route in app.routes if isinstance(route, Mount)]
    assert mounts == ["/_app"], f"barrier: the static site of a complete build mounts /_app, found {mounts}: without it the catch-all would send these files and prove nothing about the mount"
    return app


# =============================================================================
# HELPERS
# =============================================================================


async def _get(app: FastAPI, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        return await client.get(url, headers=headers)


def _assert_sent(response: httpx.Response, url: str, relative: str) -> None:
    """Barrier: ``url`` was answered 200 with the build's file ``relative``."""
    assert response.status_code == 200, f"GET {url}: {response.status_code}, the file was not sent"
    assert response.content == BUILD_FILES[relative], f"GET {url} sent something other than {relative}: {response.content[:80]!r}"


def _only_cache_control(response: httpx.Response, url: str) -> str:
    """The value of the response's only ``Cache-Control``: a browser would merge two into one policy."""
    values = response.headers.get_list("cache-control")
    assert len(values) == 1, f"GET {url} answered {response.status_code} with {len(values)} Cache-Control headers: {values}"
    return values[0]


def _directives(value: str) -> dict[str, str | None]:
    """``Cache-Control`` as ``{directive: argument}``, names lower-cased, ``None`` for a directive without argument."""
    parsed: dict[str, str | None] = {}
    for part in value.split(","):
        name, has_argument, argument = part.strip().partition("=")
        if name.strip():
            parsed[name.strip().lower()] = argument.strip().strip('"') if has_argument else None
    return parsed


def _assert_revalidated(value: str, what: str) -> None:
    """``value`` makes a browser revalidate the file at every use, and never keep it for a year."""
    directives = _directives(value)
    assert "no-cache" in directives, f"{what}: Cache-Control {value!r} has no no-cache, yet this file keeps its name from one build to the next and must be revalidated"
    assert "immutable" not in directives, f"{what}: Cache-Control {value!r} is immutable, yet the name of this file does not change with its content"
    assert directives.get("max-age") != "31536000", f"{what}: Cache-Control {value!r} keeps this file for a year"


async def _revalidation(app: FastAPI, url: str) -> httpx.Response:
    """GET ``url``, then GET it again with the ETag it came with, as a browser revalidating its copy: the 304."""
    first = await _get(app, url)
    _assert_sent(first, url, url.removeprefix("/"))
    etag = first.headers.get("etag")
    assert etag, f"barrier: GET {url} came without an ETag, so there is nothing to revalidate with"
    again = await _get(app, url, headers={"If-None-Match": etag})
    assert again.status_code == 304, f"barrier: GET {url} with If-None-Match {etag} answered {again.status_code}, not 304: the revalidation path was not taken"
    return again


# =============================================================================
# (a) A FILE NAMED AFTER ITS CONTENT
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("url", HASHED.values(), ids=list(HASHED))
async def test_a_file_under_app_immutable_is_cached_for_a_year(site: FastAPI, url: str) -> None:
    print_section(f"F28: GET {url}, a file named after its content")

    response = await _get(site, url)

    _assert_sent(response, url, url.removeprefix("/"))
    assert _only_cache_control(response, url) == IMMUTABLE
    print_success(f"✓ {IMMUTABLE}")


@pytest.mark.asyncio
@pytest.mark.parametrize("url", HASHED.values(), ids=list(HASHED))
async def test_the_304_of_a_file_under_app_immutable_keeps_it_immutable(site: FastAPI, url: str) -> None:
    print_section(f"F28: GET {url} revalidated, a file named after its content")

    response = await _revalidation(site, url)

    assert _only_cache_control(response, url) == IMMUTABLE
    print_success(f"✓ the 304 is {IMMUTABLE}")


# =============================================================================
# (b) A FILE THAT KEEPS ITS NAME
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("url", UNHASHED.values(), ids=list(UNHASHED))
async def test_any_other_file_under_app_is_revalidated(site: FastAPI, url: str) -> None:
    print_section(f"F28: GET {url}, a file that keeps its name across builds")

    response = await _get(site, url)

    _assert_sent(response, url, url.removeprefix("/"))
    _assert_revalidated(_only_cache_control(response, url), f"GET {url}")
    print_success("✓ no-cache, never immutable nor a year")


@pytest.mark.asyncio
@pytest.mark.parametrize("url", UNHASHED.values(), ids=list(UNHASHED))
async def test_the_304_of_any_other_file_under_app_keeps_it_revalidated(site: FastAPI, url: str) -> None:
    print_section(f"F28: GET {url} revalidated, a file that keeps its name across builds")

    response = await _revalidation(site, url)

    _assert_revalidated(_only_cache_control(response, url), f"the 304 of GET {url}")
    print_success("✓ the 304 is no-cache, never immutable nor a year")


# =============================================================================
# (c) THE HTML DOCUMENTS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("url", "relative"), HTML_DOCUMENTS.values(), ids=list(HTML_DOCUMENTS))
async def test_an_html_document_is_revalidated_as_today(site: FastAPI, url: str, relative: str) -> None:
    print_section(f"F28: GET {url}, an HTML document")

    response = await _get(site, url)

    _assert_sent(response, url, relative)
    assert _only_cache_control(response, url) == REVALIDATED_HTML
    print_success(f"✓ {REVALIDATED_HTML}")
