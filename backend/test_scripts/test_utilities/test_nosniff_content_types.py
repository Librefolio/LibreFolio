"""
With ``X-Content-Type-Options: nosniff`` on every response (F15, workstream H, checkpoint CP7b-1, decision D5), a browser
refuses a script whose type is not a JavaScript MIME type and a style sheet whose type is not ``text/css`` (Fetch,
«should response to request be blocked due to nosniff?»); it does not refuse a font or a source map for its type. This
test checks all the same that every file the app serves has its right type, which keeps scripts and style sheets
loading, and keeps fonts, source maps and every other file from going out as ``application/octet-stream``.

The app serves its files through Starlette's ``FileResponse`` (the ``/_app`` mount, the SPA catch-all, ``/mkdocs``), which
takes the type from ``mimetypes.guess_type`` and falls back to ``application/octet-stream`` for a name it does not know.
``mimetypes`` reads Python's own table, then every ``mime.types`` file of the system it finds (``mimetypes.knownfiles``),
and keeps whatever the app registers with ``mimetypes.add_type``: the answer depends on the machine. The rules, on the
``Content-Type`` sent:

* ``.js``, ``.mjs``: a JavaScript MIME type (WHATWG MIME Sniffing: ``text/javascript`` and its legacy aliases);
* ``.css``: ``text/css``; ``.wasm``: ``application/wasm``; ``.woff``, ``.woff2``: ``font/…``;
* ``.json``, ``.webmanifest``: a JSON MIME type (``application/json``, ``text/json``, any ``+json``);
* ``.svg``: ``image/svg+xml``;
* any other extension (``.png``, ``.ico``, ``.html``, ``.map``, …): never ``application/octet-stream``.

Three checks:

(a) The extensions the rules name, each in a file of a fake build and a fake documentation site under ``tmp_path``,
    requested from a fresh app's static site at the three places that serve files: the SPA catch-all, the ``/_app``
    mount and ``/mkdocs``.
(b) Every extension present in ``frontend/build/`` and ``mkdocs_src/site/``; a tree that is not there (no ``index.html``,
    so the app serves none of it) is skipped, and says so; no hidden file of either tree (a part of its path starting
    with ``.``) is sampled, since no route serves one: the catch-all answers the SPA fallback (H-28), the ``/_app``
    mount and ``/mkdocs`` a 404 (H-29). One file of each extension, the smallest, is requested from a fresh app's
    static site over the real trees, and its body checked against the file before its type is judged. The
    extension of a compressed file keeps the suffix before it (``.xml.gz``): ``mimetypes`` types it by that one. The
    table of the extensions, their files and their types is printed in the test's output, whatever the verdict.
(c) The same extensions on a machine without any ``mime.types`` file, as the ``python:3.13-slim`` image the app ships in,
    whose Dockerfile installs no ``media-types``: a fresh interpreter empties ``mimetypes.knownfiles`` before importing
    ``backend.app.main``, so that Python's own table and what the app registers are all it has, then takes
    ``FileResponse``'s ``Content-Type`` for each file name. A barrier in that interpreter proves that no system file was
    read; another, here, that the app sends exactly ``FileResponse``'s type for each file, so that the probe computes
    what the app would send. On a Mac, ``/etc/apache2/mime.types`` types the fonts; without it, Python 3.13 has no type
    for ``.woff``, ``.woff2``, ``.ttf`` nor ``.map``.

No DB, no server, no network. The real trees are only read; the interpreter of (c) writes its data directory (its log)
under ``tmp_path``.
"""

from __future__ import annotations

import asyncio
import functools
import json
import mimetypes
import os
import platform
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pytest
from fastapi import FastAPI
from starlette.responses import FileResponse

from backend.app.config import PROJECT_ROOT
from backend.app.services.platform import static_site
from backend.test_scripts.test_utils import print_section, print_success

OCTET_STREAM = "application/octet-stream"

#: WHATWG MIME Sniffing, «JavaScript MIME type»: the essences a browser runs as a script.
JAVASCRIPT_TYPES = frozenset(
    {
        "application/ecmascript",
        "application/javascript",
        "application/x-ecmascript",
        "application/x-javascript",
        "text/ecmascript",
        "text/javascript",
        "text/javascript1.0",
        "text/javascript1.1",
        "text/javascript1.2",
        "text/javascript1.3",
        "text/javascript1.4",
        "text/javascript1.5",
        "text/jscript",
        "text/livescript",
        "text/x-ecmascript",
        "text/x-javascript",
    }
)


def _is_json_type(essence: str) -> bool:
    """WHATWG MIME Sniffing, «JSON MIME type»: a subtype ending in ``+json``, or ``application/json``, ``text/json``."""
    return essence in ("application/json", "text/json") or (essence.count("/") == 1 and essence.endswith("+json"))


def _is_javascript_type(essence: str) -> bool:
    return essence in JAVASCRIPT_TYPES


def _is_font_type(essence: str) -> bool:
    return essence.startswith("font/")


def _is_exactly(wanted: str) -> Callable[[str], bool]:
    return lambda essence: essence == wanted


#: extension -> (what its type must be, the test on the type's essence).
RULES: dict[str, tuple[str, Callable[[str], bool]]] = {
    ".js": ("a JavaScript MIME type", _is_javascript_type),
    ".mjs": ("a JavaScript MIME type", _is_javascript_type),
    ".css": ("text/css", _is_exactly("text/css")),
    ".wasm": ("application/wasm", _is_exactly("application/wasm")),
    ".woff": ("font/…", _is_font_type),
    ".woff2": ("font/…", _is_font_type),
    ".json": ("a JSON MIME type", _is_json_type),
    ".webmanifest": ("a JSON MIME type", _is_json_type),
    ".svg": ("image/svg+xml", _is_exactly("image/svg+xml")),
}

#: The extensions the rules name, each checked in (a) and (c) whatever the trees hold.
NAMED_EXTENSIONS = (".js", ".mjs", ".css", ".wasm", ".woff", ".woff2", ".json", ".webmanifest", ".svg", ".png", ".ico", ".html", ".map")

#: Where the app serves a file: the URL of a file named ``name`` at the root of the build, of ``_app/immutable/``, of the site.
PLACES = {"spa-catch-all": "/{name}", "app-mount": "/_app/immutable/{name}", "mkdocs": "/mkdocs/{name}"}

#: A suffix ``mimetypes`` reads as an encoding: the type comes from the suffix before it.
COMPRESSION_SUFFIXES = frozenset({".gz", ".br", ".bz2", ".xz"})

INDEX_HTML = b"<!doctype html><title>index</title>"

#: Every raw call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 30.0
#: The probe of (c) imports the whole app in a fresh interpreter.
PROBE_SECONDS = 180

RESULT_MARKER = "NOSNIFF-TYPES-PROBE "

#: Runs in the child: argv[1] is the JSON list of file names; prints {name: Content-Type} after RESULT_MARKER.
PROBE = """
import json, mimetypes, sys

mimetypes.knownfiles = []  # a machine without any mime.types file: Python's own table, and what the app registers
mimetypes.init()
assert mimetypes.types_map == mimetypes.MimeTypes().types_map[True], "barrier: a mime.types file of the system was read"

import backend.app.main  # noqa: F401  the app, and every type it registers, wherever it does

from starlette.responses import FileResponse

names = json.loads(sys.argv[1])
print("RESULT_MARKER" + json.dumps({name: FileResponse(name).headers["content-type"] for name in names}))
""".replace("RESULT_MARKER", RESULT_MARKER)


# =============================================================================
# THE RULES
# =============================================================================


def _essence(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def verdict(extension: str, content_type: str) -> str | None:
    """``None`` when ``content_type`` is right for a file of ``extension`` (a file without one is not judged), else what is wrong with it."""
    essence = _essence(content_type)
    if not extension:
        return None
    if extension in RULES:
        wanted, accepts = RULES[extension]
        return None if accepts(essence) else f"must be {wanted}"
    if essence == OCTET_STREAM:
        return f"{OCTET_STREAM}: the fallback for a name mimetypes has no type for"
    return None


def extension_of(name: str) -> str:
    """What the type of a file called ``name`` depends on: its last suffix, lower-cased, two for a compressed file; ``""`` when it has none."""
    suffixes = [suffix.lower() for suffix in Path(name).suffixes]
    if len(suffixes) >= 2 and suffixes[-1] in COMPRESSION_SUFFIXES:
        return "".join(suffixes[-2:])
    return suffixes[-1] if suffixes else ""


def system_mime_files() -> list[str]:
    """The ``mime.types`` files of this machine that ``mimetypes`` reads."""
    return [name for name in mimetypes.knownfiles if os.path.isfile(name)]


def platform_line() -> str:
    return f"Python {platform.python_version()}, mime.types read: {', '.join(system_mime_files()) or 'none'}"


# =============================================================================
# THE TREES
# =============================================================================


@dataclass(frozen=True)
class Tree:
    """A folder of files the app serves, and the URL a file of it is served under."""

    label: str
    root: Path
    url_prefix: str
    build_hint: str

    def served(self) -> bool:
        """The app serves the tree only when it has ``index.html`` (``frontend_available``, ``docs_available``)."""
        return (self.root / "index.html").is_file()


TREES = {
    "frontend-build": Tree("frontend/build", PROJECT_ROOT / "frontend" / "build", "/", "./dev.py front build"),
    "mkdocs-site": Tree("mkdocs_src/site", PROJECT_ROOT / "mkdocs_src" / "site", "/mkdocs/", "./dev.py mkdocs build"),
}

#: The SPA catch-all answers 404 to these paths (``static_site.frontend_catchall``): the app never serves such a file.
CATCH_ALL_REFUSES = ("api/", "mkdocs")


@dataclass(frozen=True)
class Sample:
    """One file standing for every file of its extension in a tree."""

    extension: str
    files: int  # the files of the tree with this extension
    path: Path  # the smallest of them
    url: str


@functools.cache
def samples_of(tree_key: str) -> tuple[Sample, ...]:
    """One sample per extension of the tree, the smallest file, extensions sorted."""
    tree = TREES[tree_key]
    groups: dict[str, list[tuple[int, str, Path]]] = {}
    for path in tree.root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(tree.root).as_posix()
        if tree.url_prefix == "/" and relative.startswith(CATCH_ALL_REFUSES):
            continue
        # Nor does any route serve a hidden file, one with a part of its path starting with ``.`` (``.build-debug``, a
        # Finder ``.DS_Store``), in either tree: the catch-all answers the SPA fallback (H-28), the ``/_app`` mount and
        # ``/mkdocs`` a 404 (H-29).
        if any(part.startswith(".") for part in relative.split("/")):
            continue
        groups.setdefault(extension_of(path.name), []).append((path.stat().st_size, relative, path))
    samples = []
    for extension, entries in sorted(groups.items()):
        _size, relative, path = min(entries)
        samples.append(Sample(extension=extension, files=len(entries), path=path, url=tree.url_prefix + relative))
    return tuple(samples)


def served_tree(tree_key: str) -> Tree:
    """The tree, or a skip that says why it is not checked here."""
    tree = TREES[tree_key]
    if not tree.served():
        pytest.skip(f"{tree.label} has no index.html, so the app serves none of it here: build it ({tree.build_hint}) to check its types")
    return tree


# =============================================================================
# REQUESTS
# =============================================================================


async def raw_get(app: Callable, path: str) -> tuple[int, dict[str, str], bytes]:
    """``GET path`` on ``app``, the path reaching the router as written: status, headers (names lower-cased), body."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.4"},
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
    complete = asyncio.Event()
    request_sent = False
    reply: dict[str, Any] = {"status": 0, "headers": {}, "body": bytearray()}

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await complete.wait()
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            reply["status"] = message["status"]
            reply["headers"].update({bytes(name).decode("latin-1").lower(): bytes(value).decode("latin-1") for name, value in message.get("headers", ())})
        elif message["type"] == "http.response.body":
            reply["body"].extend(message.get("body", b""))
            if not message.get("more_body", False):
                complete.set()

    try:
        await asyncio.wait_for(app(scope, receive, send), CALL_SECONDS)
    except TimeoutError:
        pytest.fail(f"GET {path}: no answer within {CALL_SECONDS}s")
    return reply["status"], reply["headers"], bytes(reply["body"])


def site_app(monkeypatch: pytest.MonkeyPatch, *, build: Path, site: Path) -> FastAPI:
    """A fresh app holding the static site of ``build`` and ``site``, swapped in for the module globals the routes read."""
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build)
    monkeypatch.setattr(static_site, "SITE_DIR", site)
    app = FastAPI()
    static_site.install_static_site(app)
    return app


async def served_headers(app: FastAPI, url: str, path: Path) -> tuple[str | None, dict[str, str]]:
    """``(problem, headers)`` of ``GET url``: the problem is set when the barrier fails, the file not being what came back."""
    status, headers, body = await raw_get(app, url)
    if status != 200 or body != path.read_bytes():
        return f"barrier: GET {url} answered {status} with {len(body)} bytes, not the file {path.name}: its type would say nothing about the file", headers
    return None, headers


def file_response_type(name: str | Path) -> str:
    """The Content-Type ``FileResponse`` gives a file of this name, in this process."""
    return FileResponse(name).headers["content-type"]


@dataclass(frozen=True)
class Judged:
    """The type one sample is sent with, and what is wrong with it."""

    sample: Sample
    content_type: str
    problem: str | None
    note: str = ""

    def verdict_text(self) -> str:
        if self.problem:
            return self.problem
        return "ok" if self.sample.extension else "not judged: no extension"

    def failure(self) -> str:
        return f"{self.sample.extension or '(no extension)'} ({self.sample.files} files, e.g. {self.sample.url}): {self.content_type!r}, {self.problem}"


def print_table(capsys: pytest.CaptureFixture[str], title: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    """``rows`` under ``title`` in the test's output, shown whatever the verdict."""
    widths = [max(len(str(cell)) for cell in column) for column in zip(header, *rows, strict=True)]
    lines = [title, "  " + "  ".join(cell.ljust(width) for cell, width in zip(header, widths, strict=True))]
    lines += ["  " + "  ".join(str(cell).ljust(width) for cell, width in zip(row, widths, strict=True)) for row in rows]
    with capsys.disabled():
        print("\n" + "\n".join(lines))


# =============================================================================
# (c) THE PROBE WITHOUT ANY mime.types FILE
# =============================================================================


@pytest.fixture(scope="module")
def types_without_system_files(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """``FileResponse``'s Content-Type for every file name (c) judges, in an interpreter that read no ``mime.types`` file."""
    names = {f"sample{extension}" for extension in NAMED_EXTENSIONS}
    names |= {sample.path.name for key, tree in TREES.items() if tree.served() for sample in samples_of(key)}
    workdir = tmp_path_factory.mktemp("nosniff-types-probe")
    env = {**os.environ, "LIBREFOLIO_TEST_MODE": "1", "LIBREFOLIO_TEST_DATA_DIR": str(workdir / "data"), "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    env["PYTHONPATH"] = os.pathsep.join(part for part in (str(PROJECT_ROOT), os.environ.get("PYTHONPATH")) if part)
    done = subprocess.run([sys.executable, "-c", PROBE, json.dumps(sorted(names))], cwd=workdir, env=env, capture_output=True, encoding="utf-8", errors="replace", timeout=PROBE_SECONDS, check=False)
    assert done.returncode == 0, f"the probe without system mime.types failed ({done.returncode}):\n{done.stderr[-4000:]}"
    lines = [line for line in done.stdout.splitlines() if line.startswith(RESULT_MARKER)]
    assert len(lines) == 1, f"the probe without system mime.types printed no result:\n{done.stdout[-4000:]}"
    return json.loads(lines[0].removeprefix(RESULT_MARKER))


# =============================================================================
# (a) THE EXTENSIONS THE RULES NAME
# =============================================================================


@pytest.fixture
def named_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """A fresh app over a fake build and a fake site holding ``sample<ext>`` for every named extension, in each of ``PLACES``."""
    build, site = tmp_path / "build", tmp_path / "site"
    (build / "_app" / "immutable").mkdir(parents=True)
    site.mkdir()
    (build / "index.html").write_bytes(INDEX_HTML)
    (site / "index.html").write_bytes(INDEX_HTML)
    for extension in NAMED_EXTENSIONS:
        for folder in (build, build / "_app" / "immutable", site):
            (folder / f"sample{extension}").write_bytes(f"a {extension} file\n".encode())
    return site_app(monkeypatch, build=build, site=site)


async def _named_types(app: FastAPI, extension: str) -> dict[str, str]:
    """``{place: Content-Type}`` of the sample of ``extension`` at each of ``PLACES``, after the barrier that the file came back."""
    types = {}
    for place, template in PLACES.items():
        url = template.format(name=f"sample{extension}")
        status, headers, body = await raw_get(app, url)
        assert (status, body) == (200, f"a {extension} file\n".encode()), f"barrier: GET {url} ({place}) answered {status} {body[:80]!r}, not the sample file"
        types[place] = headers.get("content-type", "")
    return types


@pytest.mark.asyncio
@pytest.mark.parametrize("extension", NAMED_EXTENSIONS)
async def test_an_extension_the_rules_name_is_served_with_its_right_type(named_site: FastAPI, extension: str) -> None:
    print_section(f"nosniff: a {extension} file, on this machine ({platform_line()})")

    types = await _named_types(named_site, extension)

    wrong = [f"{place} sends {content_type!r}, {verdict(extension, content_type)}" for place, content_type in types.items() if verdict(extension, content_type)]
    assert not wrong, f"{extension} on this machine ({platform_line()}): " + "; ".join(wrong)
    print_success(f"✓ {extension}: {sorted(set(types.values()))}")


@pytest.mark.asyncio
@pytest.mark.parametrize("extension", NAMED_EXTENSIONS)
async def test_an_extension_the_rules_name_keeps_its_type_without_a_system_mime_types_file(named_site: FastAPI, types_without_system_files: dict[str, str], extension: str) -> None:
    print_section(f"nosniff: a {extension} file, without any mime.types file of the system")
    name = f"sample{extension}"
    types = await _named_types(named_site, extension)
    assert set(types.values()) == {file_response_type(name)}, f"barrier: the app sends {types} for {name}, not FileResponse's {file_response_type(name)!r}: the probe would not compute what the app sends"

    content_type = types_without_system_files[name]

    problem = verdict(extension, content_type)
    assert problem is None, f"{extension} without a mime.types file of the system (as on python:3.13-slim): FileResponse sends {content_type!r}, {problem}"
    print_success(f"✓ {extension}: {content_type}")


# =============================================================================
# (b) EVERY EXTENSION OF THE REAL TREES, ON THIS MACHINE
# =============================================================================


def _encoding_note(sample: Sample, headers: dict[str, str]) -> str:
    """For a compressed file, what the app sends it as: ``mimetypes`` gives the type of the file inside."""
    _type, encoding = mimetypes.guess_type(sample.path.name)
    if not encoding:
        return ""
    return f"compressed ({encoding}): sent as {_essence(headers.get('content-type', ''))}, Content-Encoding {headers.get('content-encoding', 'absent')}"


async def _judged_here(app: FastAPI, sample: Sample) -> Judged:
    """The type ``app`` sends ``sample`` with on this machine, after the barrier that the file itself came back."""
    barrier, headers = await served_headers(app, sample.url, sample.path)
    content_type = headers.get("content-type", "")
    return Judged(sample=sample, content_type=content_type, problem=barrier or verdict(sample.extension, content_type), note=_encoding_note(sample, headers))


@pytest.mark.asyncio
@pytest.mark.parametrize("tree_key", list(TREES))
async def test_every_extension_of_the_tree_is_served_with_its_right_type(tree_key: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tree = served_tree(tree_key)
    print_section(f"nosniff: every extension of {tree.label}, on this machine")
    app = site_app(monkeypatch, build=TREES["frontend-build"].root, site=TREES["mkdocs-site"].root)
    samples = samples_of(tree_key)

    judged = [await _judged_here(app, sample) for sample in samples]

    debug_build = ", a debug build (.build-debug): its source maps are served too" if (tree.root / ".build-debug").is_file() else ""
    rows = [(entry.sample.extension or "(none)", str(entry.sample.files), entry.sample.url, entry.content_type, entry.verdict_text(), entry.note) for entry in judged]
    print_table(capsys, f"{tree.label}: {len(samples)} extensions, {sum(sample.files for sample in samples)} files; {platform_line()}{debug_build}", ("extension", "files", "sample", "served as", "verdict", "note"), rows)
    wrong = [entry.failure() for entry in judged if entry.problem]
    assert not wrong, f"{tree.label} on this machine ({platform_line()}), {len(wrong)} extension(s) with a wrong type:\n" + "\n".join(wrong)
    print_success(f"✓ {len(samples)} extensions, each with its right type")


# =============================================================================
# (c) EVERY EXTENSION OF THE REAL TREES, WITHOUT ANY mime.types FILE
# =============================================================================


async def _judged_without_system_files(app: FastAPI, sample: Sample, types_without_system_files: dict[str, str]) -> tuple[str, Judged]:
    """``(type here, judged type without any mime.types file)`` of ``sample``, after the barriers that the file came back
    and that the app sends ``FileResponse``'s type for it, which is what the probe computes."""
    barrier, headers = await served_headers(app, sample.url, sample.path)
    assert barrier is None, barrier
    here = headers.get("content-type", "")
    assert here == file_response_type(sample.path), f"barrier: the app sends {here!r} for {sample.url}, not FileResponse's {file_response_type(sample.path)!r}: the probe would not compute what the app sends"
    without = types_without_system_files[sample.path.name]
    return here, Judged(sample=sample, content_type=without, problem=verdict(sample.extension, without))


@pytest.mark.asyncio
@pytest.mark.parametrize("tree_key", list(TREES))
async def test_every_extension_of_the_tree_keeps_its_type_without_a_system_mime_types_file(tree_key: str, types_without_system_files: dict[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    tree = served_tree(tree_key)
    print_section(f"nosniff: every extension of {tree.label}, without any mime.types file of the system")
    app = site_app(monkeypatch, build=TREES["frontend-build"].root, site=TREES["mkdocs-site"].root)
    samples = samples_of(tree_key)

    judged = [await _judged_without_system_files(app, sample, types_without_system_files) for sample in samples]

    rows = [(entry.sample.extension or "(none)", str(entry.sample.files), entry.sample.path.name, here, entry.content_type, entry.verdict_text()) for here, entry in judged]
    print_table(capsys, f"{tree.label} without any mime.types file of the system, as on python:3.13-slim (here: {platform_line()})", ("extension", "files", "sample", "here", "without mime.types", "verdict"), rows)
    wrong = [entry.failure() for _here, entry in judged if entry.problem]
    assert not wrong, f"{tree.label} without a mime.types file of the system (as on python:3.13-slim), {len(wrong)} extension(s) with a wrong type:\n" + "\n".join(wrong)
    print_success(f"✓ {len(samples)} extensions, each with its right type on any machine")
