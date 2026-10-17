"""The routes that serve files by request path never leave their folder (``backend/app/services/platform/static_site.py``, ``backend/app/api/v1/uploads.py``).

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

Inside the build, the catch-all serves no hidden file either (H-28): a path that, once its dot
segments are resolved, has a part below the build folder starting with ``.`` — dev.py's
``.build-debug`` and ``.build-version``, the ``.tool-contract-inputs`` a build records, the emoji
font's ``.cache_manifest.json``, anything in a hidden folder — gets the SPA fallback, as a path
leaving the folder does. Each such case first writes the file into the build with a content of its
own, so the fallback never stands for a file that is not there; a name with a dot anywhere else
(``robots.txt``, a ``v1.2`` folder) is still served.

Nor do the documentation and the build's ``/_app`` mount serve a hidden file (H-29): a path with a part below the site
folder starting with ``.`` (a Finder ``.DS_Store``, a file in a hidden folder, a hidden folder's ``index.html``, the same
through parent segments) gets the documentation's 404, and one below ``_app`` the mount's, each as a file its tree does
not hold. Each case writes its file with a content of its own and compares the answer with a missing file's, once the
route is proved to serve the fake tree; a ``style.css``, a folder's ``index.html``, a ``v1.2`` folder are still served.

The requests are raw ASGI calls. An HTTP client normalises dot segments before sending, so the route
would not receive the path written in the test; here ``path`` reaches the app as the server hands it
over once percent-decoded. A plain ``http`` scope never runs the lifespan, and without
``Accept-Encoding`` the GZip middleware leaves the body as it is.

The folders are built under ``tmp_path`` and swapped in for the module globals the routes read at
call time (``FRONTEND_BUILD_DIR`` and ``SITE_DIR`` of ``backend.app.services.platform.static_site``, ``PLUGIN_STATIC_DIRS`` of
``backend.app.api.v1.uploads``). The catch-all and the documentation are called on the global app as it is
(``backend.app.main``). The ``/_app`` mount fixes its folder when ``install_static_site()`` runs, so the global app's
mount serves the real build: the mount is called on a fresh app holding the static site of the fake build. The plugin
route is mounted on a fresh app whose sign-in dependency is overridden. Only these modules are imported, never the
helper behind the routes. No DB, no server, no network.
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
from starlette.routing import Mount

import backend.app.api.v1.uploads as uploads
import backend.app.main as app_main
import backend.app.services.platform.static_site as static_site

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

    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build)
    monkeypatch.setattr(static_site, "SITE_DIR", site)
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


# ---------------------------------------------------------------------------
# Frontend catch-all: the hidden files of the build (H-28)
# ---------------------------------------------------------------------------

#: The hidden files a build holds, by path relative to it, each with what it is: only the tooling reads them, from disk,
#: and the app never requests one.
HIDDEN_BUILD_FILES = {
    ".build-debug": "dev.py's mark of a debug or production build, written after every build",
    ".build-version": "the version an image-bound build carries, written by dev.py",
    ".tool-contract-inputs": "the listing of the Tool codegen inputs the last build recorded (H-24r)",
    "fonts/noto-color-emoji/.cache_manifest.json": "the JS cache's manifest, shipped from frontend/static",
    ".hidden-dir/file.txt": "a file inside a hidden folder",
}

#: Files the app may request, whose names hold a dot that starts no part of their path: served before H-28 and after.
DOTTED_BUILD_FILES = {
    "robots.txt": "a dot in the name",
    "fonts/noto-color-emoji/noto-color-emoji.0.woff2": "the font beside the hidden manifest",
    "fonts/v1.2/x.woff2": "a dot inside a folder's name",
}


def add_file(folder: Path, relative: str, tree: str) -> bytes:
    """Write ``relative`` into ``folder``, the ``tree``, with a content no other file holds, prove it is a file inside, return the content.

    A refusal then never stands for a file that is not there, and a reply can carry that content only if the route sent
    this very file.
    """
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"content of the {tree} file {relative}".encode()
    path.write_bytes(content)
    assert path.is_file() and path.read_bytes() == content, f"premise: {relative} is a file of the {tree}"
    assert path.resolve().is_relative_to(folder), f"premise: {relative} lies inside the {tree} folder"
    return content


def add_build_file(served: Served, relative: str) -> bytes:
    """Write ``relative`` into the build with a content no other file holds, prove it is a file inside, return the content.

    A fallback then never stands for a file that is not there, and a reply can carry that content only if the route
    sent this very file.
    """
    return add_file(served.build, relative, "build")


@pytest.mark.asyncio
@pytest.mark.parametrize("relative", list(HIDDEN_BUILD_FILES))
async def test_frontend_route_never_serves_a_hidden_file_of_the_build(served: Served, relative: str) -> None:
    content = add_build_file(served, relative)

    reply = await raw_get(app_main.app, "/" + relative)

    assert content not in reply.body, f"H-28: GET /{relative} sent {HIDDEN_BUILD_FILES[relative]}"
    assert reply.status == 200
    assert reply.body == FALLBACK_HTML


@pytest.mark.asyncio
async def test_frontend_route_resolves_parent_segments_before_it_judges_a_hidden_file(served: Served) -> None:
    # /assets/../favicon.png is served (above): the same segments landing on a hidden file get the SPA fallback.
    content = add_build_file(served, ".build-debug")
    relative = "assets/../.build-debug"
    assert (served.build / relative).resolve() == served.build / ".build-debug", f"premise: {relative} lands on the hidden file"

    reply = await raw_get(app_main.app, "/" + relative)

    assert content not in reply.body, f"H-28: GET /{relative} sent {HIDDEN_BUILD_FILES['.build-debug']}"
    assert reply.status == 200
    assert reply.body == FALLBACK_HTML


@pytest.mark.asyncio
async def test_frontend_route_without_200_html_answers_a_hidden_file_with_index_html(served: Served) -> None:
    (served.build / "200.html").unlink()
    content = add_build_file(served, ".tool-contract-inputs")

    reply = await raw_get(app_main.app, "/.tool-contract-inputs")

    assert content not in reply.body, f"H-28: GET /.tool-contract-inputs sent {HIDDEN_BUILD_FILES['.tool-contract-inputs']}"
    assert reply.status == 200
    assert reply.body == INDEX_HTML


@pytest.mark.asyncio
@pytest.mark.parametrize("relative", list(DOTTED_BUILD_FILES))
async def test_frontend_route_still_serves_a_dotted_name_that_is_not_hidden(served: Served, relative: str) -> None:
    # Green before H-28 and after it: only a part of the path that starts with a dot hides a file.
    content = add_build_file(served, relative)

    reply = await raw_get(app_main.app, "/" + relative)

    assert reply.status == 200, f"GET /{relative} ({DOTTED_BUILD_FILES[relative]}) was not served"
    assert reply.body == content


# ---------------------------------------------------------------------------
# Documentation and the /_app mount: the hidden files of their trees (H-29)
# ---------------------------------------------------------------------------


def answer(reply: Reply) -> tuple[int, str | None, bytes]:
    """What a reply tells the client: its status, its type, its body."""
    return reply.status, reply.headers.get("content-type"), reply.body


#: The hidden files of a documentation site, by the path requested below ``/mkdocs/``: (the file it names in the site,
#: what it is). MkDocs writes none; the Finder of a Mac leaves a ``.DS_Store`` in a folder it shows.
HIDDEN_SITE_PATHS = {
    ".DS_Store": (".DS_Store", "the Finder's record of the site folder"),
    "assets/.hidden.css": ("assets/.hidden.css", "a hidden file in a folder of the site"),
    ".hidden-dir/page.html": (".hidden-dir/page.html", "a page inside a hidden folder"),
    ".hidden-dir/": (".hidden-dir/index.html", "the index.html of a hidden folder"),
    "assets/../.DS_Store": (".DS_Store", "the Finder's record of the site folder, reached through parent segments"),
}

#: Paths the documentation serves before H-29 and after it: (the file each names in the site, what it is).
VISIBLE_SITE_PATHS = {
    "assets/style.css": ("assets/style.css", "a style sheet of the site"),
    "guide/": ("guide/index.html", "the index.html of a folder"),
    "v1.2/page.html": ("v1.2/page.html", "a page in a folder whose name holds a dot"),
}

#: A page the site does not hold.
MISSING_PAGE = "no-such-page.html"


def add_site_file(served: Served, relative: str) -> bytes:
    """Write ``relative`` into the site with a content no other file holds, prove it is a file inside, return the content."""
    return add_file(served.site, relative, "site")


def docs_target(site: Path, requested: str) -> Path:
    """The file ``/mkdocs/<requested>`` names when joined to ``site`` without any check: dot segments resolved, a folder standing for its ``index.html``."""
    target = (site / requested).resolve()
    return target / "index.html" if target.is_dir() else target


async def docs_not_found(served: Served) -> Reply:
    """The documentation's 404, the answer to a page the site does not hold, as to a path leaving it.

    A barrier first proves that the route serves the fake site: another site holds none of the case's files either, and
    its 404 would make a refusal vacuous.
    """
    home = await raw_get(app_main.app, "/mkdocs/")
    assert (home.status, home.body) == (200, SITE_INDEX_HTML), f"barrier: GET /mkdocs/ answered {home.status}, not the index of the fake site"
    assert not (served.site / MISSING_PAGE).exists(), f"premise: the site holds no {MISSING_PAGE}"
    reply = await raw_get(app_main.app, "/mkdocs/" + MISSING_PAGE)
    assert reply.status == 404, f"premise: GET /mkdocs/{MISSING_PAGE} answered {reply.status}, not the documentation's 404"
    return reply


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", list(HIDDEN_SITE_PATHS))
async def test_docs_route_never_serves_a_hidden_file_of_the_site(served: Served, requested: str) -> None:
    relative, what = HIDDEN_SITE_PATHS[requested]
    (served.site / "assets").mkdir()  # a folder of the site, as a built documentation has: parent segments climb out of it
    content = add_site_file(served, relative)
    assert docs_target(served.site, requested) == served.site / relative, f"premise: /mkdocs/{requested} names {relative}"
    not_found = await docs_not_found(served)

    reply = await raw_get(app_main.app, "/mkdocs/" + requested)

    assert content not in reply.body, f"H-29: GET /mkdocs/{requested} sent {what}"
    assert reply.status == 404
    assert answer(reply) == answer(not_found), f"H-29: GET /mkdocs/{requested} was not answered with the documentation's 404"


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", list(VISIBLE_SITE_PATHS))
async def test_docs_route_still_serves_a_file_that_is_not_hidden(served: Served, requested: str) -> None:
    # Green before H-29 and after it: only a part of the path that starts with a dot hides a file.
    relative, what = VISIBLE_SITE_PATHS[requested]
    content = add_site_file(served, relative)

    reply = await raw_get(app_main.app, "/mkdocs/" + requested)

    assert reply.status == 200, f"GET /mkdocs/{requested} ({what}) was not served"
    assert reply.body == content


#: The hidden files under ``_app``, by the path requested below ``/_app/``: (the file it names in the build, what it is).
#: SvelteKit writes none; the Finder of a Mac leaves a ``.DS_Store`` in a folder it shows.
HIDDEN_APP_PATHS = {
    ".DS_Store": ("_app/.DS_Store", "the Finder's record of the _app folder"),
    "immutable/.hidden.js": ("_app/immutable/.hidden.js", "a hidden script among the immutable chunks"),
    ".hidden-dir/x.js": ("_app/.hidden-dir/x.js", "a script inside a hidden folder"),
    "immutable/../.DS_Store": ("_app/.DS_Store", "the Finder's record of the _app folder, through parent segments Starlette normalises away"),
}

#: Paths the mount serves before H-29 and after it: (the file each names in the build, what it is).
VISIBLE_APP_PATHS = {
    "immutable/chunk.js": ("_app/immutable/chunk.js", "an immutable chunk"),
    "version.json": ("_app/version.json", "the version file of the build"),
    "v1.2/x.js": ("_app/v1.2/x.js", "a script in a folder whose name holds a dot"),
}

#: A file ``_app`` does not hold.
MISSING_CHUNK = "immutable/no-such-chunk.js"


@pytest.fixture
def app_mount(served: Served) -> FastAPI:
    """A fresh app holding the static site of the fake build, its ``/_app`` mounted on the build's ``_app`` folder.

    ``install_static_site()`` fixes the mount's folder when it runs, so the global app, made at import, mounts the real
    build. ``served`` has swapped the fake build (``index.html``, ``200.html``) in for ``FRONTEND_BUILD_DIR``; given an
    ``_app/immutable/`` folder, as a real build has, a fresh app mounts it, as test_nosniff_content_types.py builds one.
    """
    app_folder = served.build / "_app"
    (app_folder / "immutable").mkdir(parents=True)
    app = FastAPI()
    static_site.install_static_site(app)
    mounted = [getattr(route.app, "directory", None) for route in app.routes if isinstance(route, Mount) and route.path == "/_app"]
    assert mounted == [app_folder], f"premise: /_app is mounted once, on the _app folder of the fake build, not on {mounted}"
    return app


async def app_not_found(app: FastAPI, served: Served) -> Reply:
    """The mount's 404, the answer to a file ``_app`` does not hold: Starlette's ``HTTPException``, rendered by FastAPI."""
    assert not (served.build / "_app" / MISSING_CHUNK).exists(), f"premise: _app holds no {MISSING_CHUNK}"
    reply = await raw_get(app, "/_app/" + MISSING_CHUNK)
    assert reply.status == 404, f"premise: GET /_app/{MISSING_CHUNK} answered {reply.status}, not a 404"
    return reply


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", list(HIDDEN_APP_PATHS))
async def test_app_mount_never_serves_a_hidden_file_of_the_build(served: Served, app_mount: FastAPI, requested: str) -> None:
    relative, what = HIDDEN_APP_PATHS[requested]
    content = add_build_file(served, relative)
    assert (served.build / "_app" / requested).resolve() == served.build / relative, f"premise: /_app/{requested} names {relative}"
    not_found = await app_not_found(app_mount, served)

    reply = await raw_get(app_mount, "/_app/" + requested)

    assert content not in reply.body, f"H-29: GET /_app/{requested} sent {what}"
    assert reply.status == 404
    assert answer(reply) == answer(not_found), f"H-29: GET /_app/{requested} was not answered as a file _app does not hold"


@pytest.mark.asyncio
@pytest.mark.parametrize("requested", list(VISIBLE_APP_PATHS))
async def test_app_mount_still_serves_a_file_that_is_not_hidden(served: Served, app_mount: FastAPI, requested: str) -> None:
    # Green before H-29 and after it: only a part of the path that starts with a dot hides a file.
    relative, what = VISIBLE_APP_PATHS[requested]
    content = add_build_file(served, relative)

    reply = await raw_get(app_mount, "/_app/" + requested)

    assert reply.status == 200, f"GET /_app/{requested} ({what}) was not served"
    assert reply.body == content
