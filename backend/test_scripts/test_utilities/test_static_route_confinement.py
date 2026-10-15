"""The routes that serve files by request path never leave their folder (``backend/app/main.py``, ``backend/app/api/v1/uploads.py``).

Three routes join a path taken from the request to a folder:

* the frontend catch-all ``/{path:path}`` (the build folder, no sign-in): a path that would land
  outside the folder gets the SPA fallback (``200.html``, else ``index.html``);
* the documentation ``/mkdocs/{path:path}`` (the site folder, no sign-in): the documentation's 404;
* the plugin icons ``/api/v1/uploads/plugin/{provider_type}/{path:path}`` (the plugin's ``static``
  folder, signed in): 403.

Whatever the path, content from outside the folder never travels, while the files of each folder
are still served: a build file, an SPA route, a documentation folder's index, the site index, a
plugin icon. Each case that expects a refusal first proves that its path, joined to the folder
without any check, names an existing file outside it, so a refusal is never satisfied by a path
that names nothing.

The requests are raw ASGI calls. An HTTP client normalises dot segments before sending, so the route
would not receive the path written in the test; here ``path`` reaches the app as the server hands it
over once percent-decoded. A plain ``http`` scope never runs the lifespan, and without
``Accept-Encoding`` the GZip middleware leaves the body as it is.

The folders are built under ``tmp_path`` and swapped in for the module globals the routes read at
call time (``FRONTEND_BUILD_DIR`` and ``SITE_DIR`` of ``backend.app.main``, ``PLUGIN_STATIC_DIRS`` of
``backend.app.api.v1.uploads``). The two public routes are called on the global app as it is; the
plugin route is mounted on a fresh app whose sign-in dependency is overridden. Only those two modules
are imported, never the helper behind the routes, so the file runs unchanged against older releases.
No DB, no server, no network.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from fastapi import FastAPI

import backend.app.api.v1.uploads as uploads
import backend.app.main as app_main

OUTSIDE_TEXT = b"content kept outside every served folder"
SIBLING_TEXT = b"content of the folder next to the plugin folder"
INDEX_HTML = b"<!doctype html><title>index</title>"
FALLBACK_HTML = b"<!doctype html><title>spa fallback</title>"
SITE_INDEX_HTML = b"<!doctype html><title>documentation home</title>"
GUIDE_INDEX_HTML = b"<!doctype html><title>documentation guide</title>"
FAVICON = b"\x89PNG\r\n\x1a\nfavicon"
ICON = b"\x89PNG\r\n\x1a\nplugin icon"

PLUGIN_TYPE = "brim"
PLUGIN_ROUTE = f"/api/v1/uploads/plugin/{PLUGIN_TYPE}/"


@dataclass(frozen=True)
class Served:
    """The folders of one case, all resolved: ``tmp_path`` itself may sit behind a symlink."""

    base: Path  # the case's tmp folder, parent of everything below
    build: Path  # FRONTEND_BUILD_DIR
    site: Path  # SITE_DIR
    static: Path  # PLUGIN_STATIC_DIRS[PLUGIN_TYPE]; ``static-other`` sits next to it
    outside: Path  # a file outside every served folder


@pytest.fixture
def served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Served:
    base = tmp_path.resolve()

    build = base / "build"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_bytes(INDEX_HTML)
    (build / "200.html").write_bytes(FALLBACK_HTML)
    (build / "favicon.png").write_bytes(FAVICON)
    (build / "assets" / "app.css").write_text("body {}\n")

    site = base / "site"
    (site / "guide").mkdir(parents=True)
    (site / "index.html").write_bytes(SITE_INDEX_HTML)
    (site / "guide" / "index.html").write_bytes(GUIDE_INDEX_HTML)

    static = base / "static"
    (static / "demo").mkdir(parents=True)
    (static / "demo" / "icon.png").write_bytes(ICON)
    (base / "static-other").mkdir()
    (base / "static-other" / "note.txt").write_bytes(SIBLING_TEXT)

    outside = base / "outside" / "marker.txt"
    outside.parent.mkdir()
    outside.write_bytes(OUTSIDE_TEXT)

    monkeypatch.setattr(app_main, "FRONTEND_BUILD_DIR", build)
    monkeypatch.setattr(app_main, "SITE_DIR", site)
    monkeypatch.setitem(uploads.PLUGIN_STATIC_DIRS, PLUGIN_TYPE, static)
    return Served(base=base, build=build, site=site, static=static, outside=outside)


# ---------------------------------------------------------------------------
# Raw ASGI requests
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Reply:
    status: int
    headers: dict[str, str]
    body: bytes


async def raw_get(app: Callable, path: str) -> Reply:
    """``GET path`` on ``app``, the path reaching the router exactly as written."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": quote(path).encode("ascii"),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    response_complete = asyncio.Event()
    request_sent = False
    status = 0
    headers: dict[str, str] = {}
    body = bytearray()

    async def receive() -> dict:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await response_complete.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
            headers.update({name.decode("latin-1").lower(): value.decode("latin-1") for name, value in message.get("headers", [])})
        elif message["type"] == "http.response.body":
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                response_complete.set()

    await app(scope, receive, send)
    assert response_complete.is_set(), f"GET {path!r}: the app returned without completing a response"
    return Reply(status=status, headers=headers, body=bytes(body))


def plugin_icon_app() -> FastAPI:
    """The uploads router on a fresh app, signed in: the global app is left untouched."""
    app = FastAPI()
    app.include_router(uploads.router, prefix="/api/v1")
    app.dependency_overrides[uploads.get_current_user] = lambda: SimpleNamespace(id=1, is_superuser=False)
    return app


# ---------------------------------------------------------------------------
# Paths that land outside a served folder
# ---------------------------------------------------------------------------


def _climb_to_filesystem_root(start: Path, target: Path) -> str:
    """A relative path from ``start`` up to the filesystem root, then down to ``target``."""
    return "../" * (len(start.parts) - 1) + target.relative_to(target.anchor).as_posix()


def _assert_names_a_file_outside(folder: Path, relative: str) -> None:
    """The case is not vacuous: joined without any check, ``relative`` names an existing file outside ``folder``."""
    joined = folder / relative
    assert joined.is_file(), f"{relative!r} names no file when joined to {folder}"
    assert not joined.resolve().is_relative_to(folder), f"{relative!r} stays inside {folder}"


#: (served tree, served folder, an existing subfolder of it) -> a path relative to the served folder.
Leaving = Callable[[Served, Path, str], str]

#: Paths that land outside the served folder: parent segments at several depths, or an absolute path.
LEAVING: dict[str, Leaving] = {
    "one-level-up": lambda s, folder, subfolder: "../outside/marker.txt",
    "through-a-subfolder": lambda s, folder, subfolder: f"{subfolder}/../../outside/marker.txt",
    "past-the-tmp-folder": lambda s, folder, subfolder: f"../../{s.base.name}/outside/marker.txt",
    "to-the-filesystem-root": lambda s, folder, subfolder: _climb_to_filesystem_root(folder, s.outside),
    "absolute-path": lambda s, folder, subfolder: str(s.outside),
}

#: The plugin folder also has a sibling whose name starts with its own.
PLUGIN_LEAVING: dict[str, Leaving] = {
    **LEAVING,
    "sibling-folder-sharing-the-name-prefix": lambda s, folder, subfolder: "../static-other/note.txt",
}


# ---------------------------------------------------------------------------
# Frontend catch-all: /{path:path}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("leaving", LEAVING.values(), ids=list(LEAVING))
async def test_frontend_route_never_serves_a_file_outside_the_build_folder(served: Served, leaving: Leaving) -> None:
    relative = leaving(served, served.build, "assets")
    _assert_names_a_file_outside(served.build, relative)

    reply = await raw_get(app_main.app, "/" + relative)

    assert OUTSIDE_TEXT not in reply.body, f"GET /{relative} sent a file from outside the build folder"
    assert reply.status == 200
    assert reply.body == FALLBACK_HTML


@pytest.mark.asyncio
async def test_frontend_route_without_200_html_falls_back_to_index_html(served: Served) -> None:
    (served.build / "200.html").unlink()
    relative = "../outside/marker.txt"
    _assert_names_a_file_outside(served.build, relative)

    reply = await raw_get(app_main.app, "/" + relative)

    assert OUTSIDE_TEXT not in reply.body, f"GET /{relative} sent a file from outside the build folder"
    assert reply.status == 200
    assert reply.body == INDEX_HTML


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/favicon.png", "/assets/../favicon.png"], ids=["direct", "parent-segments-staying-inside"])
async def test_frontend_route_serves_a_file_of_the_build_folder(served: Served, path: str) -> None:
    reply = await raw_get(app_main.app, path)

    assert reply.status == 200
    assert reply.body == FAVICON


@pytest.mark.asyncio
async def test_frontend_route_answers_a_client_side_route_with_the_spa_fallback(served: Served) -> None:
    reply = await raw_get(app_main.app, "/portfolio/overview")

    assert reply.status == 200
    assert reply.body == FALLBACK_HTML


# ---------------------------------------------------------------------------
# Documentation: /mkdocs/{path:path}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("leaving", LEAVING.values(), ids=list(LEAVING))
async def test_docs_route_never_serves_a_file_outside_the_site_folder(served: Served, leaving: Leaving) -> None:
    relative = leaving(served, served.site, "guide")
    _assert_names_a_file_outside(served.site, relative)

    reply = await raw_get(app_main.app, "/mkdocs/" + relative)

    assert OUTSIDE_TEXT not in reply.body, f"GET /mkdocs/{relative} sent a file from outside the site folder"
    assert reply.status == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "expected"),
    [("/mkdocs/", SITE_INDEX_HTML), ("/mkdocs/guide/", GUIDE_INDEX_HTML), ("/mkdocs/guide/index.html", GUIDE_INDEX_HTML)],
    ids=["empty-path-site-index", "folder-index", "file"],
)
async def test_docs_route_serves_the_files_of_the_site_folder(served: Served, path: str, expected: bytes) -> None:
    reply = await raw_get(app_main.app, path)

    assert reply.status == 200
    assert reply.body == expected


# ---------------------------------------------------------------------------
# Plugin icons: /api/v1/uploads/plugin/{provider_type}/{path:path}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("leaving", PLUGIN_LEAVING.values(), ids=list(PLUGIN_LEAVING))
async def test_plugin_icon_route_never_serves_a_file_outside_the_plugin_folder(served: Served, leaving: Leaving) -> None:
    relative = leaving(served, served.static, "demo")
    _assert_names_a_file_outside(served.static, relative)

    reply = await raw_get(plugin_icon_app(), PLUGIN_ROUTE + relative)

    assert OUTSIDE_TEXT not in reply.body, f"GET {PLUGIN_ROUTE}{relative} sent a file from outside the plugin folder"
    assert SIBLING_TEXT not in reply.body, f"GET {PLUGIN_ROUTE}{relative} sent a file from a folder next to the plugin folder"
    assert reply.status == 403


@pytest.mark.asyncio
async def test_plugin_icon_route_refuses_a_path_the_os_rejects(served: Served) -> None:
    reply = await raw_get(plugin_icon_app(), PLUGIN_ROUTE + "demo/icon\x00.png")

    assert reply.status == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("relative", ["demo/icon.png", "demo/../demo/icon.png"], ids=["direct", "parent-segments-staying-inside"])
async def test_plugin_icon_route_serves_an_icon_of_the_plugin(served: Served, relative: str) -> None:
    reply = await raw_get(plugin_icon_app(), PLUGIN_ROUTE + relative)

    assert reply.status == 200
    assert reply.body == ICON
