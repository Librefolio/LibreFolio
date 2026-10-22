"""
H-55 wave 4 · the PDF viewer's CJK fonts, served by the instance itself (LibreFolio 1.3, workstream H, platform). The
contract is the wave's: §1 «The hash list» and §2 «The font route».

Under test: ``backend/app/services/files/pdf_fonts.py`` (new) and ``backend/app/api/v1/pdf_fonts.py`` (new). The PDF
viewer's worker reads four packages of CJK fonts (``fonts-jp``, ``fonts-kr``, ``fonts-sc``, ``fonts-tc``, 26 files). The
page's ``connect-src`` stays ``'self'``, so the instance fetches each file once from jsDelivr, checks it against the
expected hash (a list generated from the copies in ``node_modules``, the version pinned,
``backend/app/services/files/pdf_font_hashes.json``), keeps it on the volume and serves it:

- the list: ``font_list()`` is the parsed JSON, a version and 26 entries ``{package, file, size, sha256}``; ``font_entry``
  gives an entry only for an exact name of the list (``..``, a ``/``, another package, another extension: ``None``);
  ``source_url(entry, version)`` is ``PDF_FONT_SOURCE/<package>@<version>/fonts/<file>``;
- ``cached_font(package, file)`` is blocking: the file ``<data dir>/cache/pdf-fonts/<package>/<file>`` when it exists with
  the entry's size, else one fetch (``fetch_font_bytes(url, max_bytes)``, ``max_bytes`` the entry's size), the sha256 checked
  BEFORE anything is written, a temporary name in the same folder renamed atomically, one fetch at a time per file; a
  mismatch raises ``PdfFontMismatch`` (logged as a warning naming package and file, nothing written), an unreachable
  source ``PdfFontUnavailable``, both propagating;
- the route ``GET /api/v1/files/pdf-fonts/{package}/{file}``: a session (401 without), 404 for a name not in the list, 503
  ``pdf_font_unavailable``, 502 ``pdf_font_mismatch``, else 200 ``font/otf`` with ``Cache-Control: private,
  max-age=31536000, immutable``; the blocking work off the event loop; out of the OpenAPI schema (the viewer's worker reads
  it, never the generated client).

The tests, with what each covers:

- PFT-001: the real list: 26 entries, the four packages, safe names, a hash and a size each, one version; it is the JSON.
- PFT-002: ``font_entry`` answers for every name of the list and for nothing else.
- PFT-003: ``source_url`` is exact for every entry; ``PDF_FONT_SOURCE`` is the jsDelivr address.
- PFT-004: ``cached_font`` fetches, checks, writes under the data directory and returns the path; a second call fetches nothing.
- PFT-005: wrong bytes raise ``PdfFontMismatch``, write nothing (no temporary file left), warn naming package and file, and
  poison nothing.
- PFT-006: an unreachable source raises ``PdfFontUnavailable``, writes nothing, and is retried by the next call.
- PFT-007: eight threads asking for one uncached file fetch once and get the same path.
- PFT-008: a cached file of another size than the entry's is fetched again.
- PFT-009: ``cached_font`` refuses a name that is not in the list: no fetch, nothing written.
- PFT-010: the route, 200: type, ``Cache-Control``, exact bytes, one fetch for two requests.
- PFT-011: the route needs a session: 401 without one, before any 404 or fetch.
- PFT-012: the route, 404 for every name not in the list, without a fetch.
- PFT-013: the route, 503 and 502 with their codes; nothing cached; no internal text in the body.
- PFT-014: the blocking fetch runs off the event loop's thread.
- PFT-015: the route is out of the OpenAPI schema, on its own router and on the app of ``backend.app.main``, where it is
  registered.

How. Pure: no network, no server, no lane database, no file outside ``tmp_path``. Each test has a data directory of its own
(``LIBREFOLIO_TEST_MODE``, ``LIBREFOLIO_TEST_DATA_DIR``), made empty with mode ``0700``. The network call is replaced by a
fake ``fetch_font_bytes`` (the module attribute the contract names), and, for every test that writes or serves a file, the
list by a small FAKE one holding the hash of bytes made here: never a real font, never the real network. This assumes
``font_entry`` and ``cached_font`` read the list through ``font_list()``, looked up in the module at each call, and call
``fetch_font_bytes`` the same way: both attributes are replaced with ``monkeypatch``. The routes are sent through
``httpx.ASGITransport`` to a fresh ``FastAPI`` app holding the router under ``/api/v1``, ``get_current_user`` overridden
for the signed-in cases and left alone for the 401 (``get_session_generator`` is overridden by a function that gives no
session: without a cookie ``get_current_user`` never reads it). The modules are imported when a test runs, so the file
collects before they exist.

Red today: neither module exists, so every test fails at its first line naming the missing file, except PFT-015's
real-app half, which fails on the missing route.
"""

import asyncio
import hashlib
import importlib
import json
import logging
import re
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import iter_route_contexts
from structlog.testing import capture_logs

from backend.app.api.v1.auth import get_current_user
from backend.app.config import PROJECT_ROOT, get_data_dir
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT, SPELLED OUT
# =============================================================================

FONTS_MODULE = "backend.app.services.files.pdf_fonts"
ROUTE_MODULE = "backend.app.api.v1.pdf_fonts"
_SOURCES = {FONTS_MODULE: "backend/app/services/files/pdf_fonts.py", ROUTE_MODULE: "backend/app/api/v1/pdf_fonts.py"}

#: The list on disk (§1), written by ``frontend/scripts/pdf-font-hashes.mjs``; this file reads it as data.
HASH_LIST_FILE = PROJECT_ROOT / "backend" / "app" / "services" / "files" / "pdf_font_hashes.json"
PACKAGES = frozenset({"fonts-jp", "fonts-kr", "fonts-sc", "fonts-tc"})
FILE_COUNT = 26
SAFE_NAME = re.compile(r"[A-Za-z0-9._-]+\.otf")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")

#: The source of the fonts, and the route (§2): written here, never read from the modules.
PDF_FONT_SOURCE = "https://cdn.jsdelivr.net/npm/@embedpdf"
API_PREFIX = "/api/v1"
ROUTE_PREFIX = "/files/pdf-fonts"
ROUTE_TEMPLATE = f"{API_PREFIX}{ROUTE_PREFIX}/{{package}}/{{file}}"
CACHE_FOLDER = ("cache", "pdf-fonts")
FONT_MEDIA_TYPE = "font/otf"
FONT_CACHE_CONTROL = "private, max-age=31536000, immutable"
UNAVAILABLE_CODE = "pdf_font_unavailable"
MISMATCH_CODE = "pdf_font_mismatch"

#: The fake list's version and files: bytes made here, with their size and hash. Never a real font.
FAKE_VERSION = "9.9.9"
FAKE_PACKAGE = "fonts-jp"
FAKE_BYTES = {
    "Fake-Regular.otf": b"LibreFolio H-55 test: fake OTF bytes, regular. " * 8,
    "Fake-Bold.otf": b"LibreFolio H-55 test: fake OTF bytes, bold, another content. " * 11,
    "Fake-Light.otf": b"LibreFolio H-55 test: fake OTF bytes, light, a third content. " * 5,
}
OTHER_PACKAGE_FAKE = ("fonts-kr", "Fake-Korean.otf", b"LibreFolio H-55 test: fake OTF bytes, korean. " * 6)
#: What a test sends as a body that is not the file: the entry's size, other content / shorter / longer.
WRONG_BODIES = {
    "same-size-other-content": lambda good: bytes(reversed(good)),
    "shorter": lambda good: good[:-7],
    "longer": lambda good: good + b"!",
}

#: Every in-process call ends within this, or the test fails instead of hanging.
CALL_SECONDS = 10.0
BASE_URL = "http://pdf-fonts.test"
THREADS = 8
#: How long a fetch waits for its siblings in the concurrency test: they arrive only if nothing keeps them out.
SIBLINGS_SECONDS = 1.0
RACE_SECONDS = 30.0
LOG_CANARY = "H-55 w4 canary: what pdf_fonts logs reaches this test"


def _module(name: str) -> ModuleType:
    """The module ``name``, imported when a test needs it: before H-55 wave 4 it does not exist, and the rest of this file
    must still be collected."""
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        # The module itself missing is the red; a module it imports missing is a finding, raised as it is.
        if error.name != name:
            raise
    pytest.fail(f"H-55 wave 4: {_SOURCES[name]} is missing")


def _given(module: ModuleType, name: str) -> Any:
    """``module.name``, the test failing when the module does not give it."""
    value = getattr(module, name, None)
    if value is None:
        pytest.fail(f"H-55 wave 4: {module.__name__} gives no {name}")
    return value


def _field(entry: Any, name: str) -> Any:
    """``entry.name`` of an entry however the module represents it: a mapping (the parsed JSON) or an object."""
    return entry[name] if isinstance(entry, dict) else getattr(entry, name)


def _parts(font_list: Any) -> tuple[Any, list[Any]]:
    """``(version, entries)`` of what ``font_list()`` gives: the parsed JSON ``{"version", "files"}`` (§1), or an object
    with the same two members."""
    if isinstance(font_list, dict):
        return font_list.get("version"), list(font_list.get("files") or [])
    return getattr(font_list, "version", None), list(getattr(font_list, "files", None) or getattr(font_list, "entries", None) or [])


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A data directory of this test only, in test mode, made as a server makes one (``0700``) and empty: whatever the
    module writes there is visible."""
    monkeypatch.delenv("LIBREFOLIO_DATA_DIR", raising=False)
    folder = tmp_path / "data"
    folder.mkdir(mode=0o700)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(folder))
    data = folder.resolve()
    assert get_data_dir() == data, f"Precondition: the data directory of this test is its own, under tmp_path, not {get_data_dir()}"
    return data


@pytest.fixture
def fonts(data_dir: Path) -> ModuleType:
    """The service module, imported once this test's data directory is in place. Before H-55 wave 4 the test fails here."""
    module = _module(FONTS_MODULE)
    for name in ("font_list", "font_entry", "source_url", "cached_font", "fetch_font_bytes", "PDF_FONT_SOURCE", "PdfFontMismatch", "PdfFontUnavailable"):
        _given(module, name)
    return module


def _fake_list() -> dict[str, Any]:
    """The small FAKE list: three files of ``FAKE_PACKAGE`` and one of another package, each with the size and the hash of
    its bytes, one version."""
    files = [{"package": FAKE_PACKAGE, "file": name, "size": len(data), "sha256": _sha256(data)} for name, data in FAKE_BYTES.items()]
    package, name, data = OTHER_PACKAGE_FAKE
    files.append({"package": package, "file": name, "size": len(data), "sha256": _sha256(data)})
    return {"version": FAKE_VERSION, "files": files}


@dataclass
class Network:
    """The fake ``fetch_font_bytes``: what it was asked (url, ``max_bytes``, the thread it ran on), and what it answers.

    ``bodies`` gives the bytes of a URL; ``failure`` is raised instead of any body when set; ``before`` runs inside each
    call (the concurrency test waits there for its siblings)."""

    bodies: dict[str, bytes] = field(default_factory=dict)
    failure: BaseException | None = None
    before: Callable[[], None] | None = None
    calls: list[tuple[str, int, int]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __call__(self, url: str, max_bytes: int) -> bytes:
        with self._lock:
            self.calls.append((url, max_bytes, threading.get_ident()))
        if self.before is not None:
            self.before()
        if self.failure is not None:
            raise self.failure
        if url not in self.bodies:
            pytest.fail(f"the module fetched {url}, which no test gave a body: the fake network knows {sorted(self.bodies)}")
        return self.bodies[url]

    @property
    def urls(self) -> list[str]:
        return [url for url, _, _ in self.calls]


def _url(package: str, file: str) -> str:
    """The address of a file of the fake list, written here from the contract's template."""
    return f"{PDF_FONT_SOURCE}/{package}@{FAKE_VERSION}/fonts/{file}"


@pytest.fixture
def network(monkeypatch: pytest.MonkeyPatch, fonts: ModuleType) -> Network:
    """The module's list replaced by the fake one and its one network call by a ``Network`` that serves the right bytes of
    every file of the fake list; a test changes what it answers."""
    fake = _fake_list()
    monkeypatch.setattr(fonts, "font_list", lambda: fake)
    fake_network = Network(bodies={_url(FAKE_PACKAGE, name): data for name, data in FAKE_BYTES.items()})
    package, name, data = OTHER_PACKAGE_FAKE
    fake_network.bodies[_url(package, name)] = data
    monkeypatch.setattr(fonts, "fetch_font_bytes", fake_network)
    return fake_network


def _cache_path(data_dir: Path, package: str, file: str) -> Path:
    return data_dir.joinpath(*CACHE_FOLDER, package, file)


def _files_under(folder: Path) -> list[str]:
    """Every file under ``folder`` (a temporary one included), relative, sorted: none when the folder is absent."""
    return sorted(str(path.relative_to(folder)) for path in folder.rglob("*") if path.is_file()) if folder.exists() else []


@contextmanager
def _warnings_of(module_name: str, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[[], list[str]]]:
    """What ``module_name`` logs inside the block as a warning or worse, read both ways a module of the app may log: the
    structlog events (``capture_logs``) and the stdlib records (``caplog``). Each behind a canary, as in
    ``test_managed_headers``: a canary through a logger of the module's name reaches it, or an absence counts nothing.
    Yields a function listing the text of what was logged since, the canary left out."""
    monkeypatch.setattr(logging.getLogger(module_name), "disabled", False)
    caplog.set_level(logging.WARNING)
    caplog.set_level(logging.WARNING, logger=module_name)
    with capture_logs() as events:
        get_logger(module_name).warning(LOG_CANARY)
        logging.getLogger(module_name).warning(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: a structlog logger of {module_name} does not reach capture_logs: {events}"
        assert any(record.name == module_name and record.getMessage() == LOG_CANARY for record in caplog.records), f"barrier: a stdlib logger of {module_name} does not reach caplog"

        def logged() -> list[str]:
            structured = [json.dumps(event, default=str) for event in events if event.get("event") != LOG_CANARY and event.get("log_level") in ("warning", "error", "exception", "critical")]
            return structured + [f"{record.levelname.lower()} {record.getMessage()}" for record in caplog.records if record.levelno >= logging.WARNING and record.getMessage() != LOG_CANARY]

        yield logged


# =============================================================================
# PFT-001..003 (§1, §2): the list, the entries, the source
# =============================================================================


def test_the_list_is_the_26_files_of_four_packages_with_a_hash_and_a_size_each_and_one_version(fonts: ModuleType) -> None:
    """PFT-001 (§1): ``font_list()`` is the JSON written by ``pdf-font-hashes.mjs``: one version, 26 entries of exactly
    ``fonts-jp``, ``fonts-kr``, ``fonts-sc`` and ``fonts-tc`` (each present), every name a safe ``[A-Za-z0-9._-]+.otf`` (it
    goes into a URL and a path), a lower-case hex sha256 of 64 characters and a size above zero, no pair twice."""
    print_section("H-55 w4 PFT-001: the hash list")
    on_disk = json.loads(HASH_LIST_FILE.read_text(encoding="utf-8"))
    assert sorted(on_disk) == ["files", "version"], f"Precondition: {HASH_LIST_FILE.name} holds a version and the files, as §1 says: {sorted(on_disk)}"

    version, entries = _parts(fonts.font_list())

    assert isinstance(version, str) and version.strip(), f"the list has one version, a string: {version!r}"
    assert version == on_disk["version"], f"the list's version is the JSON's, {on_disk['version']!r}: {version!r}"
    assert len(entries) == FILE_COUNT, f"the list holds {FILE_COUNT} files (7 + 7 + 5 + 7), not {len(entries)}"
    packages = {_field(entry, "package") for entry in entries}
    assert packages == PACKAGES, f"the packages are exactly {sorted(PACKAGES)}: {sorted(packages)}"
    pairs = [(_field(entry, "package"), _field(entry, "file")) for entry in entries]
    assert len(set(pairs)) == len(pairs), f"a file appears twice in the list: {sorted(pair for pair in pairs if pairs.count(pair) > 1)}"
    for entry in entries:
        package, file, size, digest = (_field(entry, name) for name in ("package", "file", "size", "sha256"))
        assert isinstance(file, str) and SAFE_NAME.fullmatch(file), f"{package}/{file!r}: a name is [A-Za-z0-9._-]+ followed by .otf, nothing that can leave a folder or a URL"
        assert not file.startswith("."), f"{package}/{file}: a name never starts with a dot"
        assert isinstance(digest, str) and SHA256_HEX.fullmatch(digest), f"{package}/{file}: sha256 is 64 lower-case hex characters: {digest!r}"
        assert isinstance(size, int) and not isinstance(size, bool) and size > 0, f"{package}/{file}: size is an integer above zero: {size!r}"
    served = {tuple(_field(entry, name) for name in ("package", "file", "size", "sha256")) for entry in entries}
    written = {(item["package"], item["file"], item["size"], item["sha256"]) for item in on_disk["files"]}
    assert served == written, f"the entries are the JSON's, nothing added and nothing missing: {sorted(served ^ written)[:3]}"
    print_success(f"{len(entries)} files of {sorted(packages)}, version {version}")


def test_font_entry_answers_for_every_name_of_the_list(fonts: ModuleType) -> None:
    """PFT-002 (§2, half): ``font_entry(package, file)`` gives, for each pair of the list, the entry with that package, file,
    size and hash."""
    print_section("H-55 w4 PFT-002: font_entry for every name of the list")
    _, entries = _parts(fonts.font_list())
    assert entries, "Precondition: the list is not empty"

    for entry in entries:
        package, file = _field(entry, "package"), _field(entry, "file")
        found = fonts.font_entry(package, file)
        assert found is not None, f"{package}/{file} is in the list: font_entry gives its entry"
        assert [_field(found, name) for name in ("package", "file", "size", "sha256")] == [_field(entry, name) for name in ("package", "file", "size", "sha256")], f"{package}/{file}: font_entry gives another entry: {found!r}"
    print_success(f"{len(entries)} entries found")


def _names_not_in_the_list(entries: Sequence[Any]) -> list[tuple[str, str]]:
    """Pairs a request may carry that are not in the list, built from the list's own: a name of the list in any other
    package, the folder names, the other extension, the other case, the separators and the traversals."""
    first, korean = (next(entry for entry in entries if _field(entry, "package") == package) for package in ("fonts-jp", "fonts-kr"))
    jp_file, kr_file = _field(first, "file"), _field(korean, "file")
    stem = jp_file.removesuffix(".otf")
    return [
        ("fonts-jp", ".."),
        ("fonts-jp", "%2e%2e"),
        ("fonts-jp", "."),
        ("..", jp_file),
        ("%2e%2e", jp_file),
        ("fonts-jp", f"../fonts-kr/{kr_file}"),
        ("fonts-jp", f"..%2Ffonts-kr%2F{kr_file}"),
        ("fonts-jp", f"{jp_file}/"),
        ("fonts-jp/", jp_file),
        ("fonts-jp", f"/{jp_file}"),
        ("fonts-jp", f"{jp_file}\x00"),
        ("fonts-jp", f"{jp_file}%00"),
        ("fonts-jp", f" {jp_file}"),
        ("fonts-jp", ""),
        ("", jp_file),
        ("fonts-latin", jp_file),
        ("fonts-jp", kr_file),  # a name of the list, in another package
        ("fonts-kr", jp_file),
        ("FONTS-JP", jp_file),
        ("fonts-jp", jp_file.upper()),
        ("fonts-jp", f"{stem}.ttf"),
        ("fonts-jp", f"{stem}.otf.gz"),
        ("fonts-jp", f"{stem}.OTF"),
        ("fonts-jp", stem),
        ("fonts-jp", "package.json"),
        ("fonts-jp", "NotThere-Regular.otf"),
    ]


def test_font_entry_is_none_for_a_name_that_is_not_exactly_one_of_the_list(fonts: ModuleType) -> None:
    """PFT-002 (§2, half): only the exact names of the list: ``..``, a separator, a traversal, a NUL, another package (also a
    name of the list asked in the wrong one), another extension or case, an empty part: ``None``."""
    print_section("H-55 w4 PFT-002: font_entry is None for every name that is not in the list")
    _, entries = _parts(fonts.font_list())
    candidates = _names_not_in_the_list(entries)
    assert len(candidates) >= 20, f"Precondition: the table of names that are not in the list is not empty: {len(candidates)}"
    in_the_list = {(_field(entry, "package"), _field(entry, "file")) for entry in entries}
    assert not [pair for pair in candidates if pair in in_the_list], "Precondition: none of the candidates is a name of the list"

    given = [(package, file) for package, file in candidates if fonts.font_entry(package, file) is not None]

    assert not given, f"font_entry gives an entry for names that are not exactly one of the list: {given}"
    print_success(f"None for {len(candidates)} names")


def test_source_url_is_the_address_of_the_file_in_its_package_at_the_pinned_version(fonts: ModuleType) -> None:
    """PFT-003 (§2): ``PDF_FONT_SOURCE`` is ``https://cdn.jsdelivr.net/npm/@embedpdf`` and ``source_url(entry, version)`` is
    ``<source>/<package>@<version>/fonts/<file>``, exactly, for every entry of the list, with the list's version."""
    print_section("H-55 w4 PFT-003: source_url")
    assert fonts.PDF_FONT_SOURCE == PDF_FONT_SOURCE, f"PDF_FONT_SOURCE is {PDF_FONT_SOURCE}: {fonts.PDF_FONT_SOURCE!r}"
    version, entries = _parts(fonts.font_list())

    for entry in entries:
        package, file = _field(entry, "package"), _field(entry, "file")
        expected = f"https://cdn.jsdelivr.net/npm/@embedpdf/{package}@{version}/fonts/{file}"
        assert fonts.source_url(entry, version) == expected, f"source_url for {package}/{file} is {fonts.source_url(entry, version)!r}, not {expected!r}"
    other = fonts.source_url(entries[0], "0.0.1")
    assert other == f"https://cdn.jsdelivr.net/npm/@embedpdf/{_field(entries[0], 'package')}@0.0.1/fonts/{_field(entries[0], 'file')}", f"the version of the call is the one in the address, not a constant: {other!r}"
    print_success(f"{len(entries)} addresses, exact")


# =============================================================================
# PFT-004..009 (§2): cached_font
# =============================================================================


def test_cached_font_fetches_checks_writes_under_the_data_directory_and_serves_the_second_call_from_the_cache(fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-004 (§2): an uncached file is fetched once, from its address, asking at most its size; the bytes that match the
    entry's hash and size are written as ``<data dir>/cache/pdf-fonts/<package>/<file>`` and that path is returned; the second
    call returns it without fetching; nothing else is left in the folder (no temporary name)."""
    print_section("H-55 w4 PFT-004: cached_font fetches once and caches")
    name = "Fake-Regular.otf"
    good = FAKE_BYTES[name]
    expected_path = _cache_path(data_dir, FAKE_PACKAGE, name)
    assert not expected_path.exists(), "Precondition: the file is not cached"

    path = fonts.cached_font(FAKE_PACKAGE, name)

    assert isinstance(path, Path) and path == expected_path, f"cached_font returns the file under the data directory, {expected_path}: {path!r}"
    assert path.read_bytes() == good, "the file holds the fetched bytes"
    assert network.calls and network.urls == [_url(FAKE_PACKAGE, name)], f"one fetch, from {_url(FAKE_PACKAGE, name)}: {network.urls}"
    assert network.calls[0][1] == len(good), f"the fetch is bounded by the entry's size, {len(good)} bytes: max_bytes is {network.calls[0][1]}"
    assert _files_under(data_dir / CACHE_FOLDER[0]) == [f"pdf-fonts/{FAKE_PACKAGE}/{name}"], f"only the file is in the cache folder, no temporary name: {_files_under(data_dir / CACHE_FOLDER[0])}"

    again = fonts.cached_font(FAKE_PACKAGE, name)

    assert again == path and len(network.calls) == 1, f"the second call returns the same path and fetches nothing: {again!r}, {len(network.calls)} fetches"
    other_package, other_name, other_bytes = OTHER_PACKAGE_FAKE
    assert fonts.cached_font(other_package, other_name) == _cache_path(data_dir, other_package, other_name), "another package has its own folder"
    assert _cache_path(data_dir, other_package, other_name).read_bytes() == other_bytes and len(network.calls) == 2, "canary: another file is fetched on its own, so the first call's single fetch was the cache's"
    print_success("fetched once, written under the data directory, then served from the cache")


@pytest.mark.parametrize("kind", list(WRONG_BODIES))
def test_wrong_bytes_raise_a_mismatch_write_nothing_and_warn_naming_package_and_file(kind: str, fonts: ModuleType, network: Network, data_dir: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """PFT-005 (§2): bytes that are not the entry's (same size and other content, shorter, longer) raise ``PdfFontMismatch``;
    the hash is checked BEFORE writing, so no file is left, a temporary one included; a warning names the package and the
    file; and nothing is poisoned: the next call, the source now right, fetches again and caches the good file."""
    print_section(f"H-55 w4 PFT-005: a mismatch, {kind}")
    name = "Fake-Bold.otf"
    good = FAKE_BYTES[name]
    network.bodies[_url(FAKE_PACKAGE, name)] = WRONG_BODIES[kind](good)
    assert _sha256(network.bodies[_url(FAKE_PACKAGE, name)]) != _sha256(good), "Precondition: the body is not the file"

    with _warnings_of(FONTS_MODULE, caplog, monkeypatch) as logged:
        with pytest.raises(fonts.PdfFontMismatch):
            fonts.cached_font(FAKE_PACKAGE, name)
        warnings = logged()

    assert len(network.calls) == 1, f"one fetch: {network.urls}"
    assert _files_under(data_dir / CACHE_FOLDER[0]) == [], f"a mismatch writes nothing, no temporary file either: {_files_under(data_dir / CACHE_FOLDER[0])}"
    assert any(FAKE_PACKAGE in text and name in text for text in warnings), f"a warning names the package {FAKE_PACKAGE} and the file {name}: {warnings}"

    network.bodies[_url(FAKE_PACKAGE, name)] = good
    path = fonts.cached_font(FAKE_PACKAGE, name)

    assert path == _cache_path(data_dir, FAKE_PACKAGE, name) and path.read_bytes() == good, "canary: with the right bytes the same call caches the file, so the mismatch left nothing behind"
    assert len(network.calls) == 2, f"the file was fetched again after the mismatch: {network.urls}"
    print_success(f"{kind}: PdfFontMismatch, nothing written, warning logged, next call right")


def test_an_unreachable_source_raises_unavailable_writes_nothing_and_is_tried_again(fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-006 (§2): ``PdfFontUnavailable`` from the fetch propagates as it is; nothing is written; the failure is not cached:
    the next call fetches again, and once the source answers it caches the file."""
    print_section("H-55 w4 PFT-006: an unreachable source")
    name = "Fake-Light.otf"
    failure = fonts.PdfFontUnavailable("the source cannot be reached")
    network.failure = failure

    with pytest.raises(fonts.PdfFontUnavailable) as raised:
        fonts.cached_font(FAKE_PACKAGE, name)

    assert raised.value is failure, f"the error of the fetch propagates, not another one wrapped around it: {raised.value!r}"
    assert _files_under(data_dir / CACHE_FOLDER[0]) == [], f"nothing is written when the source cannot be reached: {_files_under(data_dir / CACHE_FOLDER[0])}"

    network.failure = None
    path = fonts.cached_font(FAKE_PACKAGE, name)

    assert path.read_bytes() == FAKE_BYTES[name] and len(network.calls) == 2, f"canary: the failure was not remembered, the next call fetches again and caches: {len(network.calls)} fetches"
    print_success("PdfFontUnavailable propagated, nothing written, retried")


def test_threads_asking_for_one_uncached_file_together_fetch_it_once_and_get_the_same_path(fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-007 (§2): the route runs ``cached_font`` in worker threads, so several may ask for one file together. ``THREADS``
    threads, released by a barrier, ask for one uncached file; the fake fetch waits for its siblings (a lock per file keeps
    them out, so it waits alone until its timeout; without one they all arrive and it returns at once): exactly one fetch,
    every thread gets the same path, the file is whole, nothing else is in the folder."""
    print_section(f"H-55 w4 PFT-007: {THREADS} threads, one file")
    name = "Fake-Regular.otf"
    siblings = threading.Barrier(THREADS)

    def wait_for_siblings() -> None:
        try:
            siblings.wait(timeout=SIBLINGS_SECONDS)
        except threading.BrokenBarrierError:
            pass  # alone: nobody else got in

    network.before = wait_for_siblings
    start = threading.Barrier(THREADS)
    results: list[Any] = [None] * THREADS

    def ask(index: int) -> None:
        try:
            start.wait(timeout=RACE_SECONDS)
            results[index] = fonts.cached_font(FAKE_PACKAGE, name)
        except Exception as exc:  # reported by the test, which asks every thread for an answer
            results[index] = f"{type(exc).__name__}: {exc}"

    threads = [threading.Thread(target=ask, args=(index,), name=f"pft-racer-{index}", daemon=True) for index in range(THREADS)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=RACE_SECONDS)
    stuck = [thread.name for thread in threads if thread.is_alive()]
    assert not stuck, f"threads still running after {RACE_SECONDS} s: {stuck}"

    expected_path = _cache_path(data_dir, FAKE_PACKAGE, name)
    assert results == [expected_path] * THREADS, f"every thread gets the same path, {expected_path}: {results}"
    assert len(network.calls) == 1, f"{THREADS} threads asking together fetch once, one lock per file: {len(network.calls)} fetches"
    assert expected_path.read_bytes() == FAKE_BYTES[name], "the file is whole"
    assert _files_under(data_dir / CACHE_FOLDER[0]) == [f"pdf-fonts/{FAKE_PACKAGE}/{name}"], f"nothing but the file is left in the cache folder: {_files_under(data_dir / CACHE_FOLDER[0])}"
    print_success(f"{THREADS} threads, one fetch, one path")


def test_a_cached_file_of_another_size_than_the_entrys_is_fetched_again(fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-008 (§2): the cache is the file «when it exists with the entry's size»: a cut-short file (a copy interrupted by a
    crash, a disk that filled) is fetched again, checked and replaced; a file of the right size is kept as it is."""
    print_section("H-55 w4 PFT-008: a cached file of the wrong size")
    name = "Fake-Light.otf"
    good = FAKE_BYTES[name]
    path = _cache_path(data_dir, FAKE_PACKAGE, name)
    path.parent.mkdir(parents=True, mode=0o700)
    path.write_bytes(good[: len(good) // 2])
    assert path.stat().st_size != len(good), "Precondition: the cached file is cut short"

    result = fonts.cached_font(FAKE_PACKAGE, name)

    assert result == path and path.read_bytes() == good, f"the cut-short file is replaced by the fetched bytes: {path.stat().st_size} bytes of {len(good)}"
    assert network.urls == [_url(FAKE_PACKAGE, name)], f"the file was fetched again, once: {network.urls}"
    assert _files_under(data_dir / CACHE_FOLDER[0]) == [f"pdf-fonts/{FAKE_PACKAGE}/{name}"], f"no temporary name is left: {_files_under(data_dir / CACHE_FOLDER[0])}"
    fonts.cached_font(FAKE_PACKAGE, name)
    assert len(network.calls) == 1, "canary: the whole file is then served from the cache"
    print_success("a file of the wrong size fetched again and replaced")


@pytest.mark.parametrize(
    ("package", "file"),
    [
        pytest.param("fonts-jp", "Unknown-Regular.otf", id="a-file-not-in-the-list"),
        pytest.param("fonts-jp", "../../secrets/instance.key", id="a-traversal"),
        pytest.param("fonts-jp", "..", id="dot-dot"),
        pytest.param("..", "Fake-Regular.otf", id="a-traversal-as-package"),
        pytest.param("fonts-kr", "Fake-Regular.otf", id="a-name-of-another-package"),
        pytest.param("fonts-jp", "Fake-Regular.ttf", id="another-extension"),
    ],
)
def test_cached_font_refuses_a_name_that_is_not_in_the_list_without_fetching_or_writing(package: str, file: str, fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-009 (§2): ``cached_font`` is the last guard before a path is built from a request: a name that is not exactly one
    of the list raises (``PdfFontUnknown``, or ``KeyError``), fetches nothing and writes nothing, nothing outside the cache
    folder either."""
    print_section(f"H-55 w4 PFT-009: cached_font({package!r}, {file!r}) is refused")
    unknown = getattr(fonts, "PdfFontUnknown", KeyError)

    with pytest.raises((unknown, KeyError)):
        fonts.cached_font(package, file)

    assert network.calls == [], f"no fetch for a name that is not in the list: {network.urls}"
    assert _files_under(data_dir) == [], f"nothing is written anywhere in the data directory: {_files_under(data_dir)}"
    print_success("refused, nothing fetched or written")


# =============================================================================
# THE ROUTE
# =============================================================================


def _no_session() -> None:
    """In place of ``get_session_generator``: without a cookie ``get_current_user`` never reads the session."""
    return None


def _app(route: ModuleType, *, signed_in: bool) -> FastAPI:
    """A fresh app holding the font router under ``/api/v1``, as the v1 router mounts it; ``get_current_user`` overridden by
    a user when ``signed_in``, left as it is otherwise (the 401 case): never the shared app."""
    app = FastAPI()
    app.include_router(_given(route, "router"), prefix=API_PREFIX)
    app.dependency_overrides[get_session_generator] = _no_session
    if signed_in:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, username="pft-user", is_active=True)
    return app


async def _get(app: FastAPI, path: str) -> httpx.Response:
    """``GET path`` in this process within ``CALL_SECONDS``: an exception the app does not handle comes back as its 500, never
    raised here."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with asyncio.timeout(CALL_SECONDS):
            async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as http:
                return await http.get(path)
    except TimeoutError:
        pytest.fail(f"GET {path}: no answer within {CALL_SECONDS} s")


def _font_path(package: str, file: str) -> str:
    return ROUTE_TEMPLATE.format(package=package, file=file)


@pytest.fixture
def route(fonts: ModuleType) -> ModuleType:
    """The route module, once the service module is in place (the router reads the list and the cache through it)."""
    return _module(ROUTE_MODULE)


def _body(response: httpx.Response) -> object:
    """The JSON body as a client reads it: None when there is none to read."""
    try:
        return response.json()
    except ValueError:
        return None


@pytest.mark.asyncio
async def test_the_route_serves_a_font_with_its_type_the_year_long_private_cache_and_the_exact_bytes(route: ModuleType, fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-010 (§2): a signed-in ``GET /api/v1/files/pdf-fonts/<package>/<file>``: 200, ``Content-Type: font/otf``,
    ``Cache-Control`` exactly ``private, max-age=31536000, immutable`` (a font behind a session is the user's own copy, never a
    shared cache's), the exact bytes; the second request is served from the volume: one fetch for two."""
    print_section("H-55 w4 PFT-010: the route serves a font")
    name = "Fake-Regular.otf"
    app = _app(route, signed_in=True)

    response = await _get(app, _font_path(FAKE_PACKAGE, name))

    assert response.status_code == 200, f"a font of the list is served: {response.status_code} {response.text[:200]!r}"
    assert response.headers.get("content-type") == FONT_MEDIA_TYPE, f"Content-Type is exactly {FONT_MEDIA_TYPE}: {response.headers.get('content-type')!r}"
    assert response.headers.get("cache-control") == FONT_CACHE_CONTROL, f"Cache-Control is exactly {FONT_CACHE_CONTROL!r}: {response.headers.get('cache-control')!r}"
    assert response.content == FAKE_BYTES[name], "the body is the file's exact bytes"
    assert _cache_path(data_dir, FAKE_PACKAGE, name).read_bytes() == FAKE_BYTES[name], "the file was cached under the data directory"

    again = await _get(app, _font_path(FAKE_PACKAGE, name))

    assert again.status_code == 200 and again.content == FAKE_BYTES[name] and len(network.calls) == 1, f"the second request is served from the cache: {again.status_code}, {len(network.calls)} fetches"
    assert again.headers.get("cache-control") == FONT_CACHE_CONTROL and again.headers.get("content-type") == FONT_MEDIA_TYPE, f"a cached answer carries the same headers: {dict(again.headers)}"
    print_success("200 font/otf, private immutable year, exact bytes, fetched once")


@pytest.mark.asyncio
@pytest.mark.parametrize("known", [True, False], ids=["a-font-of-the-list", "a-name-not-in-the-list"])
async def test_the_route_needs_a_session_and_answers_401_before_anything_else(known: bool, route: ModuleType, fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-011 (§2, Q-B (a)): without a session, a font of the list gets 401 and a name that is not in the list gets 401 too
    (the answer never tells a visitor which names exist): nothing is fetched, nothing is written, no byte of a font is in
    the answer. Canary: the same app with a user answers 200 for the font."""
    name = "Fake-Regular.otf" if known else "Unknown-Regular.otf"
    print_section(f"H-55 w4 PFT-011: no session, {name}")

    response = await _get(_app(route, signed_in=False), _font_path(FAKE_PACKAGE, name))

    assert response.status_code == 401, f"without a session the font route answers 401, never 200 nor 404: {response.status_code} {response.text[:200]!r}"
    assert network.calls == [], f"nothing is fetched for a visitor without a session: {network.urls}"
    assert _files_under(data_dir) == [], f"nothing is written for a visitor without a session: {_files_under(data_dir)}"
    assert FAKE_BYTES["Fake-Regular.otf"] not in response.content, "no byte of a font reaches a visitor without a session"
    if known:
        signed = await _get(_app(route, signed_in=True), _font_path(FAKE_PACKAGE, name))
        assert signed.status_code == 200 and signed.content == FAKE_BYTES[name], f"canary: with a user the same request answers 200, so the 401 above was the session's: {signed.status_code}"
    print_success("401 without a session, nothing fetched")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("package", "file"),
    [
        pytest.param("fonts-jp", "Unknown-Regular.otf", id="a-file-not-in-the-list"),
        pytest.param("fonts-jp", "%2e%2e", id="percent-encoded-dot-dot"),
        pytest.param("fonts-jp", "..", id="dot-dot"),
        pytest.param("fonts-jp", "..%2F..%2Fsecrets%2Finstance.key", id="an-encoded-traversal"),
        pytest.param("%2e%2e", "Fake-Regular.otf", id="a-traversal-as-package"),
        pytest.param("fonts-latin", "Fake-Regular.otf", id="a-package-not-in-the-list"),
        pytest.param("fonts-kr", "Fake-Regular.otf", id="a-name-of-another-package"),
        pytest.param("fonts-jp", "Fake-Regular.ttf", id="another-extension"),
        pytest.param("fonts-jp", "fake-regular.otf", id="another-case"),
    ],
)
async def test_the_route_answers_404_for_a_name_that_is_not_in_the_list_without_fetching(package: str, file: str, route: ModuleType, fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-012 (§2): a signed-in request for a name that is not exactly one of the list, a traversal included, gets 404:
    nothing is fetched, nothing is written, no byte of a font is in the answer."""
    print_section(f"H-55 w4 PFT-012: 404 for {package}/{file}")

    response = await _get(_app(route, signed_in=True), _font_path(package, file))

    assert response.status_code == 404, f"{package}/{file} is not in the list: 404, never 200, 500 or 502: {response.status_code} {response.text[:200]!r}"
    assert network.calls == [], f"nothing is fetched for a name that is not in the list: {network.urls}"
    assert _files_under(data_dir) == [], f"nothing is written for a name that is not in the list: {_files_under(data_dir)}"
    assert not any(data in response.content for data in FAKE_BYTES.values()), "no byte of a font is in a 404"
    print_success("404, nothing fetched or written")


@dataclass(frozen=True)
class Failure:
    """A way the fetch can end badly: the status and code the route answers, and the error the fake network raises."""

    status: int
    code: str
    error_name: str
    text: str


FAILURES = {
    "unavailable": Failure(503, UNAVAILABLE_CODE, "PdfFontUnavailable", "upstream said no to 10.255.0.7 port 4431"),
    "mismatch": Failure(502, MISMATCH_CODE, "PdfFontMismatch", "digest 0123abcd4567 is not the entry's"),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", list(FAILURES))
async def test_the_route_answers_503_or_502_with_the_code_and_no_internal_text(failure: str, route: ModuleType, fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-013 (§2): an unreachable source is 503 ``{"detail": {"code": "pdf_font_unavailable", …}}``; a body that is not the
    entry's is 502 ``{"detail": {"code": "pdf_font_mismatch", …}}``, the client getting a code and never the text of an
    internal error (the backend's rule on errors). Nothing is cached either way, and the next request, the source being
    right, is a 200."""
    case = FAILURES[failure]
    name = "Fake-Bold.otf"
    print_section(f"H-55 w4 PFT-013: {case.status} {case.code}")
    if failure == "unavailable":
        network.failure = fonts.PdfFontUnavailable(case.text)
    else:
        network.bodies[_url(FAKE_PACKAGE, name)] = bytes(reversed(FAKE_BYTES[name]))  # the right size, other content: the check fails
    app = _app(route, signed_in=True)

    response = await _get(app, _font_path(FAKE_PACKAGE, name))

    body = _body(response)
    detail = body.get("detail") if isinstance(body, dict) else None
    assert response.status_code == case.status, f"{case.error_name} is a {case.status}: {response.status_code} {response.text[:200]!r}"
    assert isinstance(detail, dict) and detail.get("code") == case.code, f"the body is {{'detail': {{'code': {case.code!r}, …}}}}: {body!r}"
    assert case.text not in response.text and "10.255.0.7" not in response.text, f"the text of the internal error never goes to the client: {response.text[:300]!r}"
    assert _files_under(data_dir) == [], f"nothing is cached after a {case.status}: {_files_under(data_dir)}"

    network.failure = None
    network.bodies[_url(FAKE_PACKAGE, name)] = FAKE_BYTES[name]
    recovered = await _get(app, _font_path(FAKE_PACKAGE, name))

    assert recovered.status_code == 200 and recovered.content == FAKE_BYTES[name], f"canary: the source right, the same request is a 200, so the {case.status} was the source's alone: {recovered.status_code}"
    print_success(f"{case.status} {case.code}, nothing cached, then 200")


@pytest.mark.asyncio
async def test_the_blocking_fetch_runs_off_the_event_loop(route: ModuleType, fonts: ModuleType, network: Network, data_dir: Path) -> None:
    """PFT-014 (§2): ``fetch_font_bytes`` is sync (httpx) and slow: it runs through ``asyncio.to_thread``, never on the event
    loop's thread, or every request of the instance would wait for a font. The fake records the thread it ran on; this
    test's thread is the loop's."""
    print_section("H-55 w4 PFT-014: the fetch runs off the event loop")
    loop_thread = threading.get_ident()
    name = "Fake-Light.otf"

    response = await _get(_app(route, signed_in=True), _font_path(FAKE_PACKAGE, name))

    assert response.status_code == 200 and response.content == FAKE_BYTES[name], f"barrier: the font is served: {response.status_code} {response.text[:200]!r}"
    assert len(network.calls) == 1, f"barrier: one fetch: {network.urls}"
    fetch_thread = network.calls[0][2]
    assert fetch_thread != loop_thread, f"the fetch ran on the event loop's thread ({loop_thread}): to be awaited through asyncio.to_thread"
    print_success("the fetch ran in another thread")


# =============================================================================
# PFT-015: out of the OpenAPI schema
# =============================================================================


def _served_path(context: Any) -> str | None:
    """The full path a route context serves: an included route is served by the Starlette route FastAPI builds for it
    (``starlette_route``), whose path carries the prefixes; the context's own path is None then."""
    starlette_route = getattr(context, "starlette_route", None)
    return getattr(starlette_route, "path", None) if starlette_route is not None else context.path


def test_the_route_is_out_of_the_openapi_schema_on_its_router_and_on_the_real_app(route: ModuleType) -> None:
    """PFT-015 (§2): ``include_in_schema=False``: the viewer's worker reads the route, never the generated client. On the
    router: every route is out of the schema of an app holding it (a canary route of the same router's prefix proves the
    schema is built). On the app of ``backend.app.main``: the route is registered at ``/api/v1/files/pdf-fonts/{package}/
    {file}`` (``backend/app/api/v1/router.py`` includes it) and no path of the generated schema starts with
    ``/api/v1/files/pdf-fonts``. The schema is built by ``get_openapi``, which caches nothing on the shared app."""
    print_section("H-55 w4 PFT-015: out of the OpenAPI schema")
    router = _given(route, "router")
    routes = [item for item in router.routes if getattr(item, "path", "").startswith(ROUTE_PREFIX)]
    assert routes, f"barrier: the router has a route under {ROUTE_PREFIX}: {[getattr(item, 'path', item) for item in router.routes]}"
    assert [item.path for item in routes] == [f"{ROUTE_PREFIX}/{{package}}/{{file}}"], f"the router holds the one font route: {[item.path for item in routes]}"
    assert [getattr(item, "include_in_schema", True) for item in routes] == [False], "the font route is include_in_schema=False"

    app = FastAPI()
    app.include_router(router, prefix=API_PREFIX)

    @app.get(f"{API_PREFIX}/pft-canary")
    def canary() -> dict[str, bool]:
        return {"ok": True}

    paths = get_openapi(title="pft", version="0", routes=app.routes)["paths"]
    assert f"{API_PREFIX}/pft-canary" in paths, f"barrier: the schema of the test app lists its routes: {sorted(paths)}"
    assert not [path for path in paths if ROUTE_PREFIX in path], f"the font route is not in the schema: {[path for path in paths if ROUTE_PREFIX in path]}"

    import backend.app.main as app_main  # noqa: PLC0415 — the real app is built when this test runs

    registered = [_served_path(context) for context in iter_route_contexts(app_main.app.routes)]  # an included router is a lazy object in app.routes: walked, never read flat
    assert ROUTE_TEMPLATE in registered, f"the app registers {ROUTE_TEMPLATE} (api/v1/router.py includes the font router): not among its routes"
    real_paths = get_openapi(title="real", version="0", routes=app_main.app.routes)["paths"]
    assert any(path.startswith(f"{API_PREFIX}/") for path in real_paths), f"barrier: the real app's schema lists API paths: {sorted(real_paths)[:5]}"
    leaked = [path for path in real_paths if path.startswith(f"{API_PREFIX}{ROUTE_PREFIX}")]
    assert not leaked, f"the real app's OpenAPI schema lists the font route, which the generated client would grow by: {leaked}"
    print_success("include_in_schema=False, registered on the app, absent from its schema")
