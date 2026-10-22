"""
The API documentation served by us, and off without the debug flag (workstream H, platform, lot H-55 R5).

Under test: ``backend/app/api/api_docs.py`` (``install_api_docs``), the switch ``api_docs_enabled()`` and its setting
``LIBREFOLIO_API_DOCS`` (``backend/app/config``), and the wiring of ``backend/app/main.py``. Developer decisions Q-C and Q-D
(22/10): FastAPI's own pages load Swagger UI and ReDoc from jsDelivr with an unpinned version, no integrity check and an
inline start script that the enforced policy cannot allow, and every instance, a self-hosted Docker one included, published
``/api/v1/docs``, ``/api/v1/redoc`` and ``/api/v1/openapi.json``. Now the pages are ours: they load the three libraries from
jsDelivr at an exact version with Subresource Integrity, their start scripts are served by the backend itself, and they exist
only where the operator asked for them. The contract:

(a) The switch. ``api_docs_enabled()`` is True when ``LIBREFOLIO_API_DOCS`` is on (the ``Settings`` field, a bool, off by
    default, read at every call) or test mode is on (``is_test_mode()``: the API tests read ``/api/v1/openapi.json`` from
    the lane's server), False otherwise. The managed profile keeps the code default (no ``PROFILE_DEFAULTS`` entry), and
    ``.env.example`` documents the variable, commented.
(b) Our pages. ``install_api_docs(app, *, enabled=True)`` registers ``GET /api/v1/docs`` (Swagger UI) and
    ``GET /api/v1/redoc`` (ReDoc), and their start scripts ``GET /api/v1/docs/swagger-init.js`` and
    ``GET /api/v1/redoc/redoc-init.js`` (``text/javascript``), all out of the OpenAPI schema. The pages are ``text/html`` of
    our own: no inline script and no inline event handler; the only external URLs are exactly the three of the contract
    (``swagger-ui-dist@5.33.1`` bundle and style sheet, ``redoc@2.5.4`` standalone bundle, on ``cdn.jsdelivr.net``), each
    with an exact version, its ``integrity="sha384-..."`` (the hash written here) and ``crossorigin="anonymous"``; every
    other script, style sheet and image from the same origin; the OpenAPI address in a ``data-openapi-url`` attribute
    (read by the start script); no Google Fonts, no ``fastapi.tiangolo.com`` favicon. The start scripts name no third party
    (Swagger's ``validatorUrl`` is null).
(c) ``enabled=False`` registers nothing: the app answers 404, as for a path that does not exist.
(d) The wiring of ``main.py``: FastAPI is built with ``docs_url=None`` and ``redoc_url=None`` always and an
    ``openapi_url`` that depends on ``api_docs_enabled()`` (``/api/v1/openapi.json`` when on, ``None`` off), and
    ``install_api_docs(app, enabled=api_docs_enabled())`` runs before ``install_static_site(app)``, whose catch-all must stay
    the last route. ``main.py`` builds its app once, at import, with the configuration of the process, and exposes no
    factory: the flag-off behaviour of the real wiring is therefore guarded at its source, by reading ``main.py`` with
    ``ast`` and evaluating its own ``openapi_url`` expression under each configuration; the behaviour of the pages with the
    switch off is tested on fresh apps (c). The real app in process (test mode, so the switch is on) serves the pages.
(e) ``app.openapi()`` keeps working when the app has no ``openapi_url`` (``scripts/list_api_endpoints.py``, ``dev.py api
    sync``), on a fresh app and on the real one, and the documentation pages are no operation of it.

PURE: no database, no server, no network. The apps are in process through ``httpx.ASGITransport`` (their lifespan does not
run); the switch is tested with ``monkeypatch`` on the environment, and ``Settings`` reads no ``.env`` file there. The
new names (``backend.app.api.api_docs``, ``api_docs_enabled``, ``LIBREFOLIO_API_DOCS``) are read when a test runs, so this
file collects before they exist and each test fails naming what is missing.
"""

from __future__ import annotations

import ast
import importlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute

from backend.app.config import API_V1_PREFIX, PROFILE_DEFAULTS, PROJECT_ROOT, Settings, is_test_mode
from backend.test_scripts.test_utils import print_section, print_success

TIMEOUT = 30
API_DOCS_MODULE = "backend.app.api.api_docs"
#: Where ``api_docs_enabled`` may live: the contract names either module.
SWITCH_MODULES = ("backend.app.config", "backend.app.config.platform")
FLAG = "LIBREFOLIO_API_DOCS"
TEST_MODE = "LIBREFOLIO_TEST_MODE"
PROFILE = "LIBREFOLIO_PROFILE"
MAIN_PY = PROJECT_ROOT / "backend" / "app" / "main.py"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"

DOCS_PATH = f"{API_V1_PREFIX}/docs"
REDOC_PATH = f"{API_V1_PREFIX}/redoc"
OPENAPI_PATH = f"{API_V1_PREFIX}/openapi.json"
FAVICON_PATH = "/favicon.png"


SWAGGER_BUNDLE = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.1/swagger-ui-bundle.js"
SWAGGER_CSS = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.33.1/swagger-ui.css"
REDOC_BUNDLE = "https://cdn.jsdelivr.net/npm/redoc@2.5.4/bundles/redoc.standalone.js"
#: The only external URLs of the pages, with the integrity of each (computed by the developer from the published files).
PINNED_INTEGRITY: dict[str, str] = {
    SWAGGER_BUNDLE: "sha384-ZPehFMQommnnuaZ4rpxgkgTT2DKFVp4hZC/7pLit+9Lek9T1YGSo23eHFbvNkXkw",
    SWAGGER_CSS: "sha384-Ov4/wv3j2bmct8cDc5X4ngJZohVPzEmc6uDPH8WeljUxO5vtoykvMEfbu9Vh6RaW",
    REDOC_BUNDLE: "sha384-w447zOpYfw/1Tv/5AK9NfHTlQIqE3RVR6KY62jCyy9zNDgO64cMwGGP1Fj0zJVf5",
}
SWAGGER_INIT_PATH = f"{DOCS_PATH}/swagger-init.js"
REDOC_INIT_PATH = f"{REDOC_PATH}/redoc-init.js"
START_SCRIPT_PATHS = (SWAGGER_INIT_PATH, REDOC_INIT_PATH)
#: Every route ``install_api_docs`` adds.
DOCS_ROUTES = (DOCS_PATH, REDOC_PATH, SWAGGER_INIT_PATH, REDOC_INIT_PATH)


@dataclass(frozen=True)
class Page:
    """One of our two pages: where it is, its start script (ours), and the external files it loads (the contract's, written here)."""

    name: str
    path: str
    init_path: str
    external_scripts: frozenset[str]
    external_stylesheets: frozenset[str]

    @property
    def scripts(self) -> frozenset[str]:
        return self.external_scripts | {self.init_path}

    @property
    def stylesheets(self) -> frozenset[str]:
        return self.external_stylesheets

    @property
    def external(self) -> frozenset[str]:
        return self.external_scripts | self.external_stylesheets


PAGES: dict[str, Page] = {
    "swagger-ui": Page("swagger-ui", DOCS_PATH, SWAGGER_INIT_PATH, external_scripts=frozenset({SWAGGER_BUNDLE}), external_stylesheets=frozenset({SWAGGER_CSS})),
    "redoc": Page("redoc", REDOC_PATH, REDOC_INIT_PATH, external_scripts=frozenset({REDOC_BUNDLE}), external_stylesheets=frozenset()),
}
PAGE_IDS = list(PAGES)

#: What a page never names: other CDNs, Google's fonts, FastAPI's favicon host (lower case; the body is compared lower-cased).
THIRD_PARTY_NAMES = ("fonts.googleapis", "fonts.gstatic", "fastapi.tiangolo.com", "unpkg.com", "cdnjs.cloudflare.com")
#: An exact version: ``@major.minor.patch`` followed by the path, never ``@5``, ``@latest`` or none.
EXACT_VERSION = re.compile(r"/npm/[^/@]+@\d+\.\d+\.\d+/")
ABSOLUTE_URL = re.compile(r"https?://[^\s\"'<>)]+", re.IGNORECASE)

#: Elements whose ``src``/``href``/``action``/... loads or navigates; each such URL is same-origin, but the three pinned files.
URL_ATTRIBUTES: dict[str, tuple[str, ...]] = {
    "script": ("src",),
    "link": ("href",),
    "img": ("src", "srcset"),
    "iframe": ("src",),
    "source": ("src", "srcset"),
    "embed": ("src",),
    "object": ("data",),
    "form": ("action",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "base": ("href",),
}


# =============================================================================
# THE NEW NAMES, READ WHEN A TEST RUNS
# =============================================================================


def install_function() -> Callable[..., None]:
    """``install_api_docs``: before its module exists, the test that asks for it fails, and only that test."""
    module = importlib.import_module(API_DOCS_MODULE)
    install = getattr(module, "install_api_docs", None)
    assert callable(install), f"{API_DOCS_MODULE} has no function install_api_docs"
    return install


def switch_function() -> Callable[[], bool]:
    """``api_docs_enabled``, in ``backend.app.config`` or in ``backend.app.config.platform``."""
    for name in SWITCH_MODULES:
        found = getattr(importlib.import_module(name), "api_docs_enabled", None)
        if callable(found):
            return found
    pytest.fail(f"api_docs_enabled() is in none of {SWITCH_MODULES}")


def configure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, flag: str | None, test_mode: bool, profile: str | None = None) -> None:
    """The environment the switch reads: ``LIBREFOLIO_API_DOCS`` as written (``None``: unset), test mode on or off, a profile.

    ``Settings`` reads no ``.env`` of the checkout (its ``env_file`` points under ``tmp_path``), whatever the mode, so an
    absence is never the effect of a file nobody wrote here; the test data directory is under ``tmp_path``.
    """
    monkeypatch.setitem(Settings.model_config, "env_file", str(tmp_path / "no-such.env"))
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(TEST_MODE, "1" if test_mode else "0")
    monkeypatch.delenv(PROFILE, raising=False)
    if profile is not None:
        monkeypatch.setenv(PROFILE, profile)
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)
    assert is_test_mode() is test_mode, f"barrier: test mode is {is_test_mode()}, not {test_mode}"


# =============================================================================
# (a) THE SWITCH
# =============================================================================

#: ``(flag as written, test mode)`` and what ``api_docs_enabled()`` answers: on when the flag is on or test mode is.
TRUTH_TABLE: dict[str, tuple[str | None, bool, bool]] = {
    "unset-test-off": (None, False, False),
    "false-test-off": ("false", False, False),
    "zero-test-off": ("0", False, False),
    "true-test-off": ("true", False, True),
    "one-test-off": ("1", False, True),
    "unset-test-on": (None, True, True),
    "false-test-on": ("false", True, True),
    "true-test-on": ("true", True, True),
    "one-test-on": ("1", True, True),
}


@pytest.mark.parametrize("row", list(TRUTH_TABLE))
def test_api_docs_enabled_follows_the_flag_or_test_mode(row: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The truth table: the flag on, or test mode on, turns the documentation on; neither leaves it off."""
    flag, test_mode, expected = TRUTH_TABLE[row]
    print_section(f"H-55 R5 api_docs_enabled(): {FLAG}={flag!r}, test mode {'on' if test_mode else 'off'}")
    switch = switch_function()
    configure(monkeypatch, tmp_path, flag=flag, test_mode=test_mode)

    enabled = switch()

    assert enabled is expected, f"api_docs_enabled() is {enabled!r} with {FLAG}={flag!r} and test mode {'on' if test_mode else 'off'}, wanted {expected}"
    print_success(f"api_docs_enabled() is {enabled}")


def test_api_docs_enabled_is_read_at_every_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No cache: the answer follows the environment as it is now (off, then on, then off again)."""
    switch = switch_function()
    configure(monkeypatch, tmp_path, flag=None, test_mode=False)
    assert switch() is False, "barrier: off with nothing set"

    monkeypatch.setenv(FLAG, "true")
    assert switch() is True, f"api_docs_enabled() stayed off after {FLAG}=true: it must read the environment at every call"

    monkeypatch.setenv(FLAG, "false")
    assert switch() is False, f"api_docs_enabled() stayed on after {FLAG}=false: it must read the environment at every call"


def test_the_managed_profile_keeps_the_code_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The managed profile gives the setting no value of its own (a hosting provider turns the documentation on only
    with the flag): off with the profile set and nothing else, and no ``PROFILE_DEFAULTS`` entry in any profile."""
    switch = switch_function()
    configure(monkeypatch, tmp_path, flag=None, test_mode=False, profile="managed")
    assert Settings().LIBREFOLIO_PROFILE == "managed", "barrier: the managed profile is the one read"

    assert switch() is False, "api_docs_enabled() is on under the managed profile with nothing set: the profile keeps the code default"
    held = {profile: values for profile, values in PROFILE_DEFAULTS.items() if FLAG in values}
    assert not held, f"PROFILE_DEFAULTS gives {FLAG} a value in {sorted(held)}: the managed profile keeps the code default (the module says why)"


def test_the_setting_is_a_bool_off_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``Settings.LIBREFOLIO_API_DOCS``: a bool whose code default is False."""
    configure(monkeypatch, tmp_path, flag=None, test_mode=False)
    field_info = Settings.model_fields.get(FLAG)
    assert field_info is not None, f"Settings has no field {FLAG}"
    assert field_info.annotation is bool, f"{FLAG} is annotated {field_info.annotation!r}, wanted bool"
    assert field_info.default is False, f"{FLAG} defaults to {field_info.default!r}, wanted False"
    assert getattr(Settings(), FLAG) is False, f"{FLAG} reads {getattr(Settings(), FLAG)!r} with nothing set"


def test_env_example_documents_the_variable_commented() -> None:
    """``.env.example`` lists ``LIBREFOLIO_API_DOCS``, as a commented line (a new line never changes an install)."""
    lines = ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()
    mentions = [line for line in lines if re.match(rf"^\s*#?\s*{FLAG}\s*=", line)]
    assert mentions, f"{ENV_EXAMPLE.name} does not document {FLAG}"
    assert all(line.lstrip().startswith("#") for line in mentions), f"{ENV_EXAMPLE.name}: {FLAG} must be commented: {mentions}"


# =============================================================================
# THE HTML OF A PAGE, AS A BROWSER'S PARSER READS IT
# =============================================================================


@dataclass
class Tag:
    name: str
    attrs: dict[str, str | None]


class Document(HTMLParser):
    """The start tags of a page, in order, with their attributes (names lower-cased by the parser)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[Tag] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(Tag(tag, dict(attrs)))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(Tag(tag, dict(attrs)))


def parse(html: str) -> Document:
    document = Document()
    document.feed(html)
    document.close()
    return document


def build_app(*, enabled: bool) -> FastAPI:
    """A fresh app as ``main.py`` builds its own (no FastAPI pages, no schema URL) with our pages installed (or not)."""
    install = install_function()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    install(app, enabled=enabled)
    return app


async def get(app: FastAPI, path: str, *, method: str = "GET") -> httpx.Response:
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://librefolio.test") as client:
        return await client.request(method, path, timeout=TIMEOUT)


async def page_of(page: Page) -> tuple[httpx.Response, Document]:
    """``page`` served by a fresh app with our pages on, past the barrier: 200, ``text/html``, parsed."""
    response = await get(build_app(enabled=True), page.path)
    assert response.status_code == 200, f"barrier: GET {page.path} answered {response.status_code}, not 200"
    assert response.headers.get("content-type", "").lower().startswith("text/html"), f"barrier: GET {page.path} answered {response.headers.get('content-type')!r}, not text/html"
    return response, parse(response.text)


# =============================================================================
# (b) OUR PAGES
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_the_page_is_ours_html_with_no_inline_script_and_no_inline_handler(page_name: str) -> None:
    """No ``<script>`` without ``src`` (the policy allows ``'self'`` and jsDelivr, nothing inline), no ``on*`` attribute on any tag."""
    page = PAGES[page_name]
    print_section(f"H-55 R5 {page.name}: no inline script, no inline handler")
    _, document = await page_of(page)

    scripts = [tag for tag in document.tags if tag.name == "script"]
    assert scripts, f"barrier: {page.path} has no <script> at all: it loads nothing"
    inline = [tag.attrs for tag in scripts if not tag.attrs.get("src")]
    assert not inline, f"{page.path}: inline <script> {inline}: the enforced policy allows no inline script"
    handlers = [(tag.name, name) for tag in document.tags for name in tag.attrs if name.lower().startswith("on")]
    assert not handlers, f"{page.path}: inline event handlers {handlers}"
    print_success(f"{len(scripts)} scripts, all with src; no handler")


def is_external(value: str) -> bool:
    parts = urlsplit(value.strip())
    return value.strip().startswith("//") or bool(parts.scheme) or bool(parts.netloc)


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_the_only_external_urls_are_the_pinned_files_and_the_rest_is_same_origin(page_name: str) -> None:
    """Every script, style sheet, image, frame and form target is a path of our origin, but the pinned files of the page: the
    external URLs of the tags are exactly those of the contract (the page's own), and no absolute URL appears anywhere else."""
    page = PAGES[page_name]
    print_section(f"H-55 R5 {page.name}: external URLs are the pinned files")
    response, document = await page_of(page)

    urls: list[tuple[str, str, str]] = []
    for tag in document.tags:
        for attribute in URL_ATTRIBUTES.get(tag.name, ()):
            value = tag.attrs.get(attribute)
            if value:
                urls.append((tag.name, attribute, value))
    assert any(name == "script" for name, _, _ in urls), f"barrier: no script URL found in {page.path}: nothing proves the others"
    external = {value.strip() for _, _, value in urls if is_external(value)}
    assert external == page.external, f"{page.path}: external URLs {sorted(external)}, wanted exactly {sorted(page.external)}"
    not_paths = [f"<{name} {attribute}={value!r}>" for name, attribute, value in urls if not is_external(value) and not urlsplit(value.strip()).path.startswith("/")]
    assert not not_paths, f"{page.path}: URLs that are neither a path of our origin nor a pinned file: {not_paths}"
    stray = set(ABSOLUTE_URL.findall(response.text)) - page.external
    assert not stray, f"{page.path}: absolute URLs outside the pinned files: {sorted(stray)}"
    print_success(f"{len(urls)} URLs, {len(external)} external, all pinned")


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_every_external_file_has_an_exact_version_its_integrity_and_crossorigin(page_name: str) -> None:
    """Each external script and style sheet: an exact version (``@5.33.1``, never ``@5`` or ``@latest``), the ``integrity``
    of the contract (``sha384-...``) and ``crossorigin="anonymous"``; an own start script needs none."""
    page = PAGES[page_name]
    print_section(f"H-55 R5 {page.name}: version, integrity, crossorigin")
    _, document = await page_of(page)

    checked = 0
    for tag in document.tags:
        value = tag.attrs.get("src") if tag.name == "script" else tag.attrs.get("href") if tag.name == "link" and "stylesheet" in (tag.attrs.get("rel") or "").lower().split() else None
        if not value or not is_external(value):
            continue
        checked += 1
        assert EXACT_VERSION.search(value), f"{page.path}: {value} has no exact version (@major.minor.patch)"
        assert value in PINNED_INTEGRITY, f"{page.path}: {value} is not one of the pinned files {sorted(PINNED_INTEGRITY)}"
        assert tag.attrs.get("integrity") == PINNED_INTEGRITY[value], f"{page.path}: {value} has integrity {tag.attrs.get('integrity')!r}, wanted {PINNED_INTEGRITY[value]!r}"
        assert (tag.attrs.get("crossorigin") or "").lower() == "anonymous", f"{page.path}: {value} has crossorigin {tag.attrs.get('crossorigin')!r}, wanted 'anonymous'"
    assert checked == len(page.external), f"{page.path}: {checked} external scripts and style sheets checked, wanted {len(page.external)}"
    print_success(f"{checked} external files, each pinned with SRI")


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_the_page_loads_exactly_the_contracts_files(page_name: str) -> None:
    """The pinned libraries and our start script, and nothing else loaded; an icon, if any, is ``/favicon.png``."""
    page = PAGES[page_name]
    print_section(f"H-55 R5 {page.name}: the files")
    _, document = await page_of(page)

    scripts = {tag.attrs["src"] for tag in document.tags if tag.name == "script" and tag.attrs.get("src")}
    links = [tag for tag in document.tags if tag.name == "link"]
    stylesheets = {tag.attrs.get("href") for tag in links if "stylesheet" in (tag.attrs.get("rel") or "").lower().split()}
    icons = {tag.attrs.get("href") for tag in links if "icon" in (tag.attrs.get("rel") or "").lower().split()}
    others = [tag.attrs for tag in links if "stylesheet" not in (tag.attrs.get("rel") or "").lower().split() and "icon" not in (tag.attrs.get("rel") or "").lower().split()]

    assert scripts == page.scripts, f"{page.path}: scripts {sorted(scripts)}, wanted exactly {sorted(page.scripts)}"
    assert stylesheets == page.stylesheets, f"{page.path}: style sheets {sorted(stylesheets, key=str)}, wanted exactly {sorted(page.stylesheets)}"
    assert icons <= {FAVICON_PATH}, f"{page.path}: icons {sorted(icons, key=str)}, wanted none or {FAVICON_PATH} (not FastAPI's favicon)"
    assert not others, f"{page.path}: other <link> elements {others}"
    print_success(f"scripts {sorted(scripts)}; style sheets {sorted(stylesheets, key=str)}")


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_the_openapi_address_is_in_a_data_attribute(page_name: str) -> None:
    """One element carries ``data-openapi-url="/api/v1/openapi.json"``, for the start script."""
    page = PAGES[page_name]
    print_section(f"H-55 R5 {page.name}: data-openapi-url")
    _, document = await page_of(page)

    carriers = [tag for tag in document.tags if "data-openapi-url" in tag.attrs]
    assert len(carriers) == 1, f"{page.path}: {len(carriers)} elements carry data-openapi-url, wanted one: {[tag.name for tag in carriers]}"
    assert carriers[0].attrs["data-openapi-url"] == OPENAPI_PATH, f"{page.path}: data-openapi-url is {carriers[0].attrs['data-openapi-url']!r}, wanted {OPENAPI_PATH!r}"
    print_success(f"<{carriers[0].name} data-openapi-url={OPENAPI_PATH!r}>")


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_the_page_names_no_other_third_party(page_name: str) -> None:
    """No Google Fonts, no FastAPI favicon, no other CDN, anywhere in the page; jsDelivr only through the pinned files."""
    page = PAGES[page_name]
    response, _ = await page_of(page)

    body = response.text.lower()
    named = [name for name in THIRD_PARTY_NAMES if name in body]
    assert not named, f"{page.path} names {named}: the only third party is jsDelivr, through the pinned files"
    assert body.count("jsdelivr") == len(page.external), f"{page.path} names jsDelivr {body.count('jsdelivr')} times, wanted once per pinned file ({len(page.external)})"


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_the_start_script_is_served_by_the_backend_as_javascript_and_names_no_third_party(page_name: str) -> None:
    """``GET`` of the page's start script answers 200 ``text/javascript``, not empty, naming no absolute URL and no third
    party; Swagger's also sets ``validatorUrl`` to null (no call to the online validator)."""
    page = PAGES[page_name]
    print_section(f"H-55 R5 {page.name}: the start script")
    response = await get(build_app(enabled=True), page.init_path)

    assert response.status_code == 200, f"GET {page.init_path} answered {response.status_code}, wanted 200"
    content_type = response.headers.get("content-type", "").partition(";")[0].strip().lower()
    assert content_type == "text/javascript", f"GET {page.init_path} answered {content_type!r}, wanted text/javascript"
    body = response.text
    assert body.strip(), f"GET {page.init_path} answered an empty script"
    assert not ABSOLUTE_URL.findall(body), f"{page.init_path} holds absolute URLs {ABSOLUTE_URL.findall(body)}: the start script names no third party"
    named = [name for name in (*THIRD_PARTY_NAMES, "jsdelivr") if name in body.lower()]
    assert not named, f"{page.init_path} names {named}"
    if page.name == "swagger-ui":
        assert re.search(r"validatorUrl\s*:\s*null", body), f"{page.init_path} does not set validatorUrl: null"
    print_success(f"{len(body)} bytes of text/javascript")


@pytest.mark.asyncio
async def test_the_docs_routes_are_get_routes_out_of_the_schema() -> None:
    """The four routes (two pages, two start scripts) are ``APIRoute`` GETs of the module, ``include_in_schema=False``, and the
    only routes the install adds; the schema of an app holding another route lists that route and none of them."""
    app = build_app(enabled=True)
    baseline = {route.path for route in FastAPI(docs_url=None, redoc_url=None, openapi_url=None).routes}
    added = [route for route in app.routes if route.path not in baseline]

    assert sorted(route.path for route in added) == sorted(DOCS_ROUTES), f"install_api_docs added the routes {sorted(route.path for route in added)}, wanted exactly {sorted(DOCS_ROUTES)}"
    for route in added:
        assert isinstance(route, APIRoute), f"{route.path} is a {type(route).__name__}, wanted an APIRoute"
        assert route.methods == {"GET"}, f"{route.path} answers {sorted(route.methods or ())}, wanted GET only"
        assert route.include_in_schema is False, f"{route.path} is in the OpenAPI schema"
        assert route.endpoint.__module__ == API_DOCS_MODULE, f"{route.path} is served by {route.endpoint.__module__}, wanted {API_DOCS_MODULE}"

    @app.get(f"{API_V1_PREFIX}/probe")
    async def probe() -> dict[str, bool]:
        return {"ok": True}

    paths = set(app.openapi()["paths"])
    assert f"{API_V1_PREFIX}/probe" in paths, f"barrier: the schema lists the probe route: {sorted(paths)}"
    assert not paths & set(DOCS_ROUTES), f"documentation routes are in the schema: {sorted(paths & set(DOCS_ROUTES))}"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", DOCS_ROUTES)
async def test_a_docs_route_answers_get_only(path: str) -> None:
    """Behind the barrier of a 200 GET, a POST is refused (405), not served."""
    app = build_app(enabled=True)
    assert (await get(app, path)).status_code == 200, f"barrier: GET {path} is served"

    response = await get(app, path, method="POST")

    assert response.status_code == 405, f"POST {path} answered {response.status_code}, wanted 405"


# =============================================================================
# (c) NOT ENABLED: NOTHING IS REGISTERED
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("path", DOCS_ROUTES)
async def test_not_enabled_the_route_does_not_exist(path: str) -> None:
    """``enabled=False``: the app answers 404 for the pages and the start scripts, and the same install with ``enabled=True``
    serves the path (the barrier)."""
    assert (await get(build_app(enabled=True), path)).status_code == 200, f"barrier: with enabled=True, GET {path} is served"

    response = await get(build_app(enabled=False), path)

    assert response.status_code == 404, f"GET {path} answered {response.status_code} with enabled=False, wanted 404"


def test_not_enabled_registers_no_route_at_all() -> None:
    """The routes of the app are those of a bare one: not even a hidden one."""
    off = build_app(enabled=False)
    bare = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    assert [route.path for route in off.routes] == [route.path for route in bare.routes], f"install_api_docs(enabled=False) added routes: {[route.path for route in off.routes]}"
    assert install_function()(FastAPI(docs_url=None, redoc_url=None, openapi_url=None), enabled=False) is None, "install_api_docs returns None"


def test_the_switch_is_a_keyword_only_argument() -> None:
    """A positional ``True`` is refused: ``install_api_docs(app, enabled=...)`` says what it switches."""
    with pytest.raises(TypeError):
        install_function()(FastAPI(docs_url=None, redoc_url=None, openapi_url=None), True)  # type: ignore[call-arg]


# =============================================================================
# (d) THE WIRING OF main.py, READ AT ITS SOURCE
# =============================================================================


def main_tree() -> ast.Module:
    return ast.parse(MAIN_PY.read_text(encoding="utf-8"), filename=str(MAIN_PY))


def module_assignments(tree: ast.Module) -> dict[str, ast.expr]:
    """The module-level ``name = expression`` statements of ``main.py``."""
    return {target.id: node.value for node in tree.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)}


def fastapi_call(tree: ast.Module) -> ast.Call:
    """The ``FastAPI(...)`` call that builds ``app``."""
    calls = [node.value for node in tree.body if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "app" for t in node.targets) and isinstance(node.value, ast.Call) and getattr(node.value.func, "id", None) == "FastAPI"]
    assert len(calls) == 1, f"main.py builds app with {len(calls)} FastAPI(...) calls at its top, wanted one"
    return calls[0]


def keyword(call: ast.Call, name: str) -> ast.expr:
    found = [kw.value for kw in call.keywords if kw.arg == name]
    assert len(found) == 1, f"main.py: FastAPI(...) has {len(found)} {name}= keywords, wanted one"
    return found[0]


def is_none(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


def openapi_expression(tree: ast.Module) -> ast.expr:
    """What ``openapi_url=`` is, a conditional expression written in the call or in a module-level name the call uses."""
    value = keyword(fastapi_call(tree), "openapi_url")
    if isinstance(value, ast.Name):
        assignments = module_assignments(tree)
        assert value.id in assignments, f"main.py: openapi_url={value.id} is not a module-level assignment"
        value = assignments[value.id]
    assert isinstance(value, ast.IfExp), f"main.py: openapi_url is {ast.unparse(value)!r}, wanted a conditional on api_docs_enabled()"
    return value


def calls_switch(node: ast.AST) -> bool:
    return any(isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "api_docs_enabled" and not inner.args and not inner.keywords for inner in ast.walk(node))


def test_main_builds_fastapi_without_its_own_pages() -> None:
    """``docs_url=None`` and ``redoc_url=None`` always: FastAPI's pages load their libraries from jsDelivr."""
    call = fastapi_call(main_tree())

    assert is_none(keyword(call, "docs_url")), f"main.py: docs_url is {ast.unparse(keyword(call, 'docs_url'))!r}, wanted None"
    assert is_none(keyword(call, "redoc_url")), f"main.py: redoc_url is {ast.unparse(keyword(call, 'redoc_url'))!r}, wanted None"


def test_main_gives_the_schema_an_address_only_when_the_switch_is_on() -> None:
    """``openapi_url`` is a conditional on ``api_docs_enabled()``: the schema's address when on, ``None`` when off."""
    expression = openapi_expression(main_tree())

    assert calls_switch(expression.test), f"main.py: the condition of openapi_url is {ast.unparse(expression.test)!r}, wanted a call of api_docs_enabled()"
    assert is_none(expression.orelse), f"main.py: openapi_url is {ast.unparse(expression.orelse)!r} when the switch is off, wanted None"


@pytest.mark.parametrize("row", list(TRUTH_TABLE))
def test_main_openapi_url_expression_gives_the_address_or_none(row: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``main.py``'s own ``openapi_url`` expression, evaluated under each configuration of the table: ``/api/v1/openapi.json`` on, ``None`` off.

    The expression may use ``API_V1_PREFIX`` and ``api_docs_enabled`` only; another name stops the test, which must then
    be extended with it, not skipped.
    """
    flag, test_mode, expected = TRUTH_TABLE[row]
    expression = openapi_expression(main_tree())
    names = {node.id for node in ast.walk(expression) if isinstance(node, ast.Name)}
    assert names <= {"API_V1_PREFIX", "api_docs_enabled"}, f"main.py: the openapi_url expression uses {sorted(names - {'API_V1_PREFIX', 'api_docs_enabled'})}: extend this test with them"
    configure(monkeypatch, tmp_path, flag=flag, test_mode=test_mode)

    value = eval(compile(ast.Expression(body=expression), str(MAIN_PY), "eval"), {"API_V1_PREFIX": API_V1_PREFIX, "api_docs_enabled": switch_function()})  # noqa: S307 — main.py's own expression, evaluated with two names

    assert value == (OPENAPI_PATH if expected else None), f"main.py gives openapi_url={value!r} with {FLAG}={flag!r} and test mode {'on' if test_mode else 'off'}, wanted {OPENAPI_PATH if expected else None!r}"


def test_main_installs_our_pages_before_the_static_site() -> None:
    """``install_api_docs(app, enabled=api_docs_enabled())`` runs at the top of ``main.py`` before ``install_static_site(app)``,
    whose catch-all must stay the last route; and ``main.py`` imports ``install_api_docs`` from ``backend.app.api.api_docs``."""
    tree = main_tree()
    calls: dict[str, int] = {}
    for index, node in enumerate(tree.body):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            calls.setdefault(node.value.func.id, index)
            if node.value.func.id == "install_api_docs":
                call = node.value
                assert [ast.unparse(arg) for arg in call.args] == ["app"], f"main.py: install_api_docs({', '.join(ast.unparse(a) for a in call.args)}...) wanted app first and alone"
                enabled = [kw.value for kw in call.keywords if kw.arg == "enabled"]
                assert len(enabled) == 1 and calls_switch(enabled[0]) and isinstance(enabled[0], ast.Call), f"main.py: enabled= is {[ast.unparse(e) for e in enabled]}, wanted api_docs_enabled()"

    assert "install_api_docs" in calls, "main.py never calls install_api_docs(app, enabled=api_docs_enabled())"
    assert "install_static_site" in calls, "barrier: main.py never calls install_static_site(app)"
    assert calls["install_api_docs"] < calls["install_static_site"], "main.py installs the static site (whose catch-all stays last) before our pages"
    imported = [(node.module, alias.name) for node in tree.body if isinstance(node, ast.ImportFrom) for alias in node.names]
    assert (API_DOCS_MODULE, "install_api_docs") in imported, f"main.py does not import install_api_docs from {API_DOCS_MODULE}: {imported}"


# =============================================================================
# THE REAL APP, IN PROCESS (test mode: the switch is on)
# =============================================================================


@pytest.fixture(scope="module")
def real_app() -> FastAPI:
    """The app the server runs, in this process (test mode, so the documentation is on)."""
    assert is_test_mode(), "Precondition: test mode, so the switch of the real app is on"
    from backend.app.main import app  # noqa: PLC0415 — the server's own app, imported by the fixtures that need it

    return app


def test_the_real_app_has_none_of_fastapis_pages(real_app: FastAPI) -> None:
    """``docs_url`` and ``redoc_url`` are None on the real app, its schema is at ``/api/v1/openapi.json`` (the switch is on)."""
    assert real_app.docs_url is None, f"the real app's docs_url is {real_app.docs_url!r}"
    assert real_app.redoc_url is None, f"the real app's redoc_url is {real_app.redoc_url!r}"
    assert real_app.openapi_url == OPENAPI_PATH, f"the real app's openapi_url is {real_app.openapi_url!r}, wanted {OPENAPI_PATH!r} in test mode"


@pytest.mark.asyncio
@pytest.mark.parametrize("page_name", PAGE_IDS)
async def test_the_real_app_serves_our_page_with_a_policy_that_allows_its_scripts(real_app: FastAPI, page_name: str) -> None:
    """In process through the real stack: our page and one enforced policy whose ``script-src`` is ``'self' https://cdn.jsdelivr.net``."""
    page = PAGES[page_name]
    response = await get(real_app, page.path)

    assert response.status_code == 200 and response.headers.get("content-type", "").lower().startswith("text/html"), f"GET {page.path} answered {response.status_code} {response.headers.get('content-type')!r}"
    document = parse(response.text)
    assert {tag.attrs["src"] for tag in document.tags if tag.name == "script" and tag.attrs.get("src")} == page.scripts, f"GET {page.path} is not our page: {response.text[:200]!r}"
    policies = response.headers.get_list("content-security-policy")
    assert len(policies) == 1, f"GET {page.path}: Content-Security-Policy is {policies}, wanted one field"
    directives = {tokens[0].lower(): tokens[1:] for tokens in (part.split() for part in policies[0].split(";")) if tokens}
    assert directives.get("script-src") == ["'self'", "https://cdn.jsdelivr.net"], f"GET {page.path}: script-src is {directives.get('script-src')}, wanted ['self', 'https://cdn.jsdelivr.net'] in {policies[0]!r}"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", START_SCRIPT_PATHS)
async def test_the_real_app_serves_the_start_scripts(real_app: FastAPI, path: str) -> None:
    """In process through the real stack: each start script answers 200 ``text/javascript`` and is no operation of the schema."""
    response = await get(real_app, path)

    assert response.status_code == 200 and response.headers.get("content-type", "").lower().startswith("text/javascript"), f"GET {path} answered {response.status_code} {response.headers.get('content-type')!r}"
    assert path not in real_app.openapi()["paths"], f"{path} is in the OpenAPI schema"


@pytest.mark.asyncio
async def test_the_real_app_serves_its_schema_as_json(real_app: FastAPI) -> None:
    """``/api/v1/openapi.json`` answers the schema (test mode: on), and it lists the API without the documentation pages."""
    response = await get(real_app, OPENAPI_PATH)

    assert response.status_code == 200 and response.headers.get("content-type", "").lower().startswith("application/json"), f"GET {OPENAPI_PATH} answered {response.status_code} {response.headers.get('content-type')!r}"
    paths = set(response.json()["paths"])
    assert f"{API_V1_PREFIX}/system/block" in paths, "barrier: the schema lists the API"
    assert not paths & {*DOCS_ROUTES, OPENAPI_PATH}, f"the schema lists the documentation: {sorted(paths & {*DOCS_ROUTES, OPENAPI_PATH})}"


# =============================================================================
# (e) app.openapi() WITHOUT AN openapi_url
# =============================================================================


def test_openapi_works_on_an_app_without_an_openapi_url() -> None:
    """The path of ``dev.py api sync`` and ``scripts/list_api_endpoints.py``: an app built with ``openapi_url=None`` still
    produces its schema through ``app.openapi()``, with our pages installed or not, and never lists them."""
    for enabled in (True, False):
        app = build_app(enabled=enabled)

        @app.get(f"{API_V1_PREFIX}/probe")
        async def probe() -> dict[str, bool]:
            return {"ok": True}

        assert app.openapi_url is None, "barrier: the app has no openapi_url"
        document = app.openapi()
        assert document["openapi"].startswith("3."), f"enabled={enabled}: app.openapi() is not an OpenAPI document: {sorted(document)}"
        assert set(document["paths"]) == {f"{API_V1_PREFIX}/probe"}, f"enabled={enabled}: the schema lists {sorted(document['paths'])}, wanted the probe alone"


def test_openapi_works_on_the_real_app(real_app: FastAPI) -> None:
    """``app.openapi()`` on the real app returns the whole API, whatever its ``openapi_url``."""
    document = real_app.openapi()

    assert document["paths"], "the real app's schema has no path"
    assert f"{API_V1_PREFIX}/system/block" in document["paths"], "barrier: the schema lists the API"
    assert not set(document["paths"]) & set(DOCS_ROUTES), "the schema lists the documentation pages or their start scripts"
