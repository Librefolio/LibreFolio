"""PWA icons and the service-worker stamp: what an installed LibreFolio shows (K, R2 step 13, item 1; H-52).

Both defects live where no browser tab looks, on a home screen and in a service
worker's cache, so neither had ever turned a test red.

**The icons: developer decision D1 (30/09).** ``dev.py`` ``generate_pwa_icons()``
pastes the RGBA logo onto a white RGBA canvas with ``paste(..., mask)``, and that
call *blends* the alpha channel: 12.6 % of ``icon-192.png``'s pixels (4.7 % of
``icon-512.png``'s) came out translucent, alpha down to 198. What shows behind a
pixel that is not opaque is the platform's choice: iOS paints it black, and the
Android splash showed dark corners. The manifest also listed the same
``icon-512.png`` twice, as ``any`` and as ``maskable``, two contracts one file
cannot honour. A launcher crops a maskable icon to a shape of its own, and only a
centred circle of radius 0.40 × size is sure to survive the crop; the logo reached
0.48 × size from the centre.

D1 gives each purpose its own file, and every file is opaque:

* ``icon-192.png`` / ``icon-512.png``, purpose ``any``: RGB, no alpha channel.
* ``icon-maskable-192.png`` / ``icon-maskable-512.png``, purpose ``maskable``
  (new): RGB, painted edge to edge in the splash beige ``#f5f4ef`` (the manifest's
  ``background_color``), the logo within 0.38 × size of the centre. Nothing but
  beige may lie beyond 0.40 × size: the 0.02 in between is for the antialiasing
  at the logo's edge. A blank beige square would pass all of that, so the logo
  must also be *there*.
* ``apple-touch-icon.png`` (new): 180×180 RGB, linked from ``app.html`` with
  ``sizes="180x180"`` instead of lending iOS the 192 ``any`` icon.
* ``manifest.json``: one ``any`` and one ``maskable`` entry per size (192, 512),
  each ``src`` a real PNG of the declared size, no file serving both purposes.

Opacity is read from the file, not from how it looks: the mode must be ``RGB``,
and no ``tRNS`` colour key may turn one RGB colour transparent again.

**The stamp.** ``sw.js`` caches ``offline.html`` when it installs, and a browser
installs a service worker again only when the script's bytes change. So
``dev.py`` ``stamp_service_worker()`` writes ``// build: <md5(offline.html)[:8]>``
into ``sw.js``, and editing the page changes the worker. Edit the page without
restamping, and every installed client keeps the old offline page until
something else touches ``sw.js``. It happened on 29/09: K step 12b's flags-only
face edited ``offline.html`` and left ``sw.js`` at ``450af3dd`` while the page
hashed to ``3e7bd439``, and nothing noticed. This module notices the next one.

**Stamping writes only a change, and every frontend build stamps (H-52).**
``stamp_service_worker()`` runs with every docs build (``copy_docs_assets()``,
``dev.py server``'s ``auto_build_mkdocs()`` included), and it rewrote ``sw.js``
every time, the very bytes it held included. Since H-52
``check_frontend_needs_build()`` (``scripts/cli_base.py``) also watches
``frontend/static/``: a static file newer than ``build/index.html`` makes the
build stale, so that rewrite cost a frontend rebuild after every docs build.
With ``offline.html`` unchanged, a second stamp leaves ``sw.js`` as it was, its
bytes and its mtime; an edited page is stamped on line 2, the rest of ``sw.js``
kept; a missing ``sw.js`` or ``offline.html`` writes nothing and raises nothing.
And ``cmd_fe_build`` generated the favicon but never stamped, so a frontend
build could ship a ``sw.js`` stamped for another ``offline.html`` than the one
it shipped, until a later docs build restamped it: it stamps before its npm
build.

PURE: no DB, no server, no network. The checks of the committed files read
``frontend/static/`` and ``frontend/src/app.html``, which is what a browser
gets, and never run the generator on them: ``copy_docs_assets()`` rewrites the
icons and restamps ``sw.js``, and a test that ran it there would only be
comparing the generator with itself. The stamping cases run dev.py's own
``stamp_service_worker()`` in this process, on copies of ``sw.js`` and
``offline.html`` under ``tmp_path`` with ``dev.PROJECT_ROOT`` pointed there;
``cmd_fe_build``'s other steps are stood in for, and a real process fails the
test. Nothing outside ``tmp_path`` is written.
"""

import hashlib
import inspect
import json
import math
import os
import subprocess
from functools import cache
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

import dev

PROJECT_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = PROJECT_ROOT / "frontend" / "static"
ICONS_DIR = STATIC_DIR / "icons"
MANIFEST = STATIC_DIR / "manifest.json"
SERVICE_WORKER = STATIC_DIR / "sw.js"
OFFLINE_PAGE = STATIC_DIR / "offline.html"
APP_HTML = PROJECT_ROOT / "frontend" / "src" / "app.html"

#: The splash colour: the manifest's ``background_color``, and the ground of every maskable icon.
SPLASH_BEIGE = "#f5f4ef"
OPAQUE_SPLASH_BEIGE = (*bytes.fromhex(SPLASH_BEIGE[1:]), 255)

#: Maskable geometry, as a fraction of the icon size, measured from its centre.
LOGO_RADIUS = 0.38  # where D1 draws the logo
SAFE_ZONE_RADIUS = 0.40  # what every launcher's crop keeps; the gap is antialiasing
#: Today's logo, fitted to the 0.38 disc, covers 35-42 % of it; a blank or
#: speckled square covers next to nothing. A twentieth sits far from both.
MIN_LOGO_COVERAGE = 0.05

ANY_ICONS = {"icon-192.png": 192, "icon-512.png": 512}
MASKABLE_ICONS = {"icon-maskable-192.png": 192, "icon-maskable-512.png": 512}
APPLE_TOUCH_ICONS = {"apple-touch-icon.png": 180}
APPLE_TOUCH_HREF = "/icons/apple-touch-icon.png"

#: purpose → size → the one ``src`` the manifest may declare for it.
MANIFEST_ICONS = {
    "any": {192: "/icons/icon-192.png", 512: "/icons/icon-512.png"},
    "maskable": {192: "/icons/icon-maskable-192.png", 512: "/icons/icon-maskable-512.png"},
}

OPAQUE_HEADLINE = "D1: every icon is opaque RGB with no alpha channel; iOS paints transparency black and the Android splash showed dark corners:"

#: A timestamp no write leaves: a file is aged to it before a call, so a write shows whatever the filesystem's granularity.
AGED_NS = 946_684_800 * 10**9  # 2000-01-01T00:00:00Z
#: An edit to the copy of ``offline.html``: the copy of ``sw.js`` is then stamped for an earlier page.
PAGE_EDIT = b"<!-- an edit made after sw.js was stamped -->\n"
#: Another edit, made once the copy of ``sw.js`` carries the first edit's stamp.
LATER_PAGE_EDIT = b"<!-- a later edit -->\n"
#: The npm build ``cmd_fe_build`` runs, by its ``debug`` flag; ``npx svelte-check`` runs before it.
NPM_BUILD_COMMANDS = {True: ["npm", "run", "build:debug"], False: ["npm", "run", "build"]}
#: ``cmd_fe_build``'s steps a recorder stands in for, answering 0: the checks, the codegen fingerprint, the API sync, the favicon, the bookkeeping after the build.
FE_BUILD_STAND_INS = ("require_frontend_dependencies", "update_js_cache", "tool_contract_fingerprint", "cmd_api_sync", "generate_favicon", "_write_frontend_build_mode_marker", "record_tool_contract_inputs")


def _report(headline: str, problems: list[str]) -> str:
    return headline + "\n  " + "\n  ".join(problems)


def _served(url: str) -> Path:
    """The file behind a root-relative URL such as ``/icons/icon-192.png``."""
    return STATIC_DIR / url.lstrip("/")


def _present(icons: dict[str, int], problems: list[str]) -> dict[str, int]:
    """The icons that exist. Each absent one is recorded in ``problems``, never skipped in silence."""
    present = {}
    for name, size in icons.items():
        if (ICONS_DIR / name).is_file():
            present[name] = size
        else:
            problems.append(f"{name}: missing from frontend/static/icons/")
    return present


def _size_problems(icons: dict[str, int]) -> list[str]:
    problems: list[str] = []
    for name, size in _present(icons, problems).items():
        with Image.open(ICONS_DIR / name) as image:
            if image.size != (size, size):
                problems.append(f"{name}: {image.width}x{image.height}, expected {size}x{size}")
    return problems


def _alpha_note(image: Image.Image) -> str:
    """What the alpha channel actually does, for the failure message."""
    if "A" not in image.getbands():
        return ""
    histogram = image.getchannel("A").histogram()
    translucent = sum(histogram[:255])
    if not translucent:
        return ", every pixel opaque today but the channel is there"
    lowest = next(alpha for alpha, count in enumerate(histogram) if count)
    return f", {translucent / (image.width * image.height):.1%} of the pixels translucent, alpha down to {lowest}"


def _opacity_problems(icons: dict[str, int]) -> list[str]:
    problems: list[str] = []
    for name in _present(icons, problems):
        with Image.open(ICONS_DIR / name) as image:
            if image.mode != "RGB":
                problems.append(f"{name}: mode {image.mode!r}{_alpha_note(image)}")
            elif "transparency" in image.info:
                problems.append(f"{name}: mode 'RGB', but a tRNS chunk makes {image.info['transparency']} transparent")
    return problems


@cache
def _off_beige_radii(name: str) -> tuple[float, ...]:
    """Distance from the centre, as a fraction of the size, of every pixel that is not opaque splash beige."""
    with Image.open(ICONS_DIR / name) as image:
        rgba = image.convert("RGBA")
    pixels = rgba.load()
    half_width, half_height = rgba.width / 2, rgba.height / 2
    return tuple(math.hypot(x + 0.5 - half_width, y + 0.5 - half_height) / rgba.width for y in range(rgba.height) for x in range(rgba.width) if pixels[x, y] != OPAQUE_SPLASH_BEIGE)


def _edge_colours(name: str) -> set[tuple[int, ...]]:
    """Every colour on the outermost ring of pixels."""
    with Image.open(ICONS_DIR / name) as image:
        rgba = image.convert("RGBA")
    pixels = rgba.load()
    right, bottom = rgba.width - 1, rgba.height - 1
    ring = [(x, y) for x in range(rgba.width) for y in (0, bottom)] + [(x, y) for x in (0, right) for y in range(rgba.height)]
    return {pixels[x, y] for x, y in ring}


class _LinkTags(HTMLParser):
    """The attributes of every ``<link>`` in a document."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "link":
            self.links.append(dict(attrs))


def _apple_touch_links() -> list[dict[str, str | None]]:
    parser = _LinkTags()
    parser.feed(APP_HTML.read_text(encoding="utf-8"))
    parser.close()
    return [link for link in parser.links if "apple-touch-icon" in (link.get("rel") or "").lower().split()]


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _manifest_icons() -> list[dict]:
    icons = _manifest().get("icons")
    assert isinstance(icons, list) and icons, f"manifest.json declares no icons: {icons!r}"
    return icons


def _purposes(entry: dict) -> set[str]:
    """The purposes an entry serves: a space-separated list, ``any`` when omitted (W3C manifest)."""
    return set(entry.get("purpose", "any").split())


def _declared_srcs(purpose: str, size: int) -> list[str]:
    return [entry.get("src") for entry in _manifest_icons() if purpose in _purposes(entry) and f"{size}x{size}" in entry.get("sizes", "").split()]


def _purpose_problems(purpose: str) -> list[str]:
    return [f"{purpose} {size}x{size}: declares {found}, expected [{src!r}]" for size, src in MANIFEST_ICONS[purpose].items() if (found := _declared_srcs(purpose, size)) != [src]]


def _stamps(service_worker: Path = SERVICE_WORKER) -> list[str]:
    """Every ``// build:`` line of ``service_worker``: the lines ``stamp_service_worker()`` itself recognises and rewrites."""
    lines = service_worker.read_text(encoding="utf-8").splitlines()
    return [line.removeprefix("// build:").strip() for line in lines if line.startswith("// build:")]


def _offline_page_hash(page: Path = OFFLINE_PAGE) -> str:
    """What ``stamp_service_worker()`` writes for ``page``: the first 8 hex digits of its md5."""
    return hashlib.md5(page.read_bytes(), usedforsecurity=False).hexdigest()[:8]


def _files_under(root: Path) -> dict[str, tuple[str, int]]:
    """Every file under ``root``: the sha256 of its bytes and its mtime in ns."""
    return {path.relative_to(root).as_posix(): (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns) for path in sorted(root.rglob("*")) if path.is_file()}


def _age(root: Path) -> None:
    """Every file under ``root`` at ``AGED_NS``."""
    for path in root.rglob("*"):
        if path.is_file():
            os.utime(path, ns=(AGED_NS, AGED_NS))


@pytest.fixture
def static_copy(monkeypatch, tmp_path) -> SimpleNamespace:
    """Copies of ``sw.js`` and ``offline.html`` where dev.py looks for them, ``dev.PROJECT_ROOT`` pointed at ``tmp_path``.

    The copy of the page carries ``PAGE_EDIT``, so the copy of ``sw.js`` is stamped for an earlier page: a first stamp has
    something to write, which proves the call works on this tree before a case asserts that a call wrote nothing.
    """
    if "PROJECT_ROOT" not in inspect.getclosurevars(dev.stamp_service_worker).globals:
        pytest.fail("stamp_service_worker() no longer reads dev.PROJECT_ROOT when it runs: pointing that at tmp_path would not keep it off the real frontend/static/, so the case stops before calling it")
    static_dir = tmp_path / "frontend" / "static"
    static_dir.mkdir(parents=True)
    tree = SimpleNamespace(root=tmp_path, service_worker=static_dir / "sw.js", page=static_dir / "offline.html")
    tree.service_worker.write_bytes(SERVICE_WORKER.read_bytes())
    tree.page.write_bytes(OFFLINE_PAGE.read_bytes() + PAGE_EDIT)
    monkeypatch.setattr(dev, "PROJECT_ROOT", tmp_path)
    assert _stamps(tree.service_worker) != [_offline_page_hash(tree.page)], "premise: the copy of sw.js is stamped for an earlier offline.html"
    return tree


def _stamp_afresh(tree: SimpleNamespace) -> bytes:
    """dev.py's ``stamp_service_worker()`` on the tree's stale ``sw.js``, which it must stamp for the page (premise); the bytes it leaves."""
    dev.stamp_service_worker()
    stamps = _stamps(tree.service_worker)
    assert stamps == [_offline_page_hash(tree.page)], f"premise: stamp_service_worker() stamps the copy under tmp_path for its page; the copy carries {stamps}"
    return tree.service_worker.read_bytes()


def _stand_in_for_fe_build(monkeypatch, tree: SimpleNamespace) -> SimpleNamespace:
    """Every step of ``cmd_fe_build`` a recorder, but ``stamp_service_worker``: recorded, then run for real on ``tree``.

    ``events`` holds each step's name in the order it ran (``npx svelte-check`` as ``"svelte-check"``, the npm build as
    ``"npm build"``), ``stamps_at_build`` the ``// build:`` lines of the tree's ``sw.js`` as each npm build found them.
    Any other command fails the test, and so does a real process: one that started would build the frontend.
    """
    calls = SimpleNamespace(events=[], stamps_at_build=[])
    real_stamp_service_worker = dev.stamp_service_worker

    def step(name: str):
        def run(*_args, **_kwargs):
            calls.events.append(name)
            return 0

        return run

    def stamp_service_worker(*args, **kwargs):
        calls.events.append("stamp_service_worker")
        return real_stamp_service_worker(*args, **kwargs)

    def run_command_live(command, *_args, **_kwargs):
        if list(command[:2]) == ["npx", "svelte-check"]:
            return step("svelte-check")()
        if list(command) in NPM_BUILD_COMMANDS.values():
            calls.stamps_at_build.append(_stamps(tree.service_worker))
            return step("npm build")()
        pytest.fail(f"cmd_fe_build ran a command this test does not expect: {command}")

    def real_process(*_args, **_kwargs):
        pytest.fail("cmd_fe_build started a real process: it reached a step this test does not stand in for")

    for name in ("Popen", "run"):
        monkeypatch.setattr(subprocess, name, real_process)
    for name in FE_BUILD_STAND_INS:
        monkeypatch.setattr(dev, name, step(name))
    monkeypatch.setattr(dev.i18n_catalog, "build", step("i18n_catalog.build"))
    monkeypatch.setattr(dev, "run_command_live", run_command_live)
    monkeypatch.setattr(dev, "stamp_service_worker", stamp_service_worker)
    return calls


class TestAnyIcons:
    """``icon-192.png`` / ``icon-512.png``, purpose ``any``: shown whole, never cropped."""

    def test_they_have_their_exact_size(self):
        problems = _size_problems(ANY_ICONS)
        assert not problems, _report("an 'any' icon is exactly the size its name promises:", problems)

    def test_they_are_opaque_rgb_with_no_alpha_channel(self):
        problems = _opacity_problems(ANY_ICONS)
        assert not problems, _report(OPAQUE_HEADLINE, problems)


class TestMaskableIcons:
    """``icon-maskable-{192,512}.png`` (new in D1): splash beige to the edges, the logo inside the safe zone."""

    def test_they_exist(self):
        problems: list[str] = []
        _present(MASKABLE_ICONS, problems)
        assert not problems, _report("D1 adds one maskable icon per manifest size:", problems)

    def test_they_have_their_exact_size(self):
        problems = _size_problems(MASKABLE_ICONS)
        assert not problems, _report("a maskable icon is exactly the size its name promises:", problems)

    def test_they_are_opaque_rgb_with_no_alpha_channel(self):
        problems = _opacity_problems(MASKABLE_ICONS)
        assert not problems, _report(OPAQUE_HEADLINE, problems)

    def test_they_are_splash_beige_to_the_edges(self):
        problems: list[str] = []
        for name in _present(MASKABLE_ICONS, problems):
            stray = sorted(_edge_colours(name) - {OPAQUE_SPLASH_BEIGE})
            if stray:
                more = f" and {len(stray) - 3} more" if len(stray) > 3 else ""
                problems.append(f"{name}: edge colours other than the beige: {stray[:3]}{more}")
        assert not problems, _report(f"a maskable icon is painted to its edges in the opaque splash beige {SPLASH_BEIGE} {OPAQUE_SPLASH_BEIGE}, so the launcher's crop meets the splash without a seam:", problems)

    def test_the_logo_stays_inside_the_safe_zone(self):
        problems: list[str] = []
        for name in _present(MASKABLE_ICONS, problems):
            radii = _off_beige_radii(name)
            beyond = sum(1 for radius in radii if radius > SAFE_ZONE_RADIUS)
            if beyond:
                problems.append(f"{name}: farthest non-background pixel at {max(radii):.3f} × size; {beyond} pixels beyond {SAFE_ZONE_RADIUS:.2f} × size")
        assert not problems, _report(f"a maskable icon keeps its logo within {LOGO_RADIUS:.2f} × size of the centre and nothing but background beyond {SAFE_ZONE_RADIUS:.2f} × size (the gap is antialiasing): a launcher may crop anything farther:", problems)

    def test_the_logo_is_there(self):
        problems: list[str] = []
        for name, size in _present(MASKABLE_ICONS, problems).items():
            logo = sum(1 for radius in _off_beige_radii(name) if radius <= LOGO_RADIUS)
            coverage = logo / (math.pi * (LOGO_RADIUS * size) ** 2)
            if coverage < MIN_LOGO_COVERAGE:
                problems.append(f"{name}: {logo} non-background pixels within {LOGO_RADIUS:.2f} × size, {coverage:.1%} of that disc")
        assert not problems, _report(f"a maskable icon shows the logo, at least {MIN_LOGO_COVERAGE:.0%} of the {LOGO_RADIUS:.2f} × size disc not beige; a blank beige square would pass every other check:", problems)


class TestAppleTouchIcon:
    """``apple-touch-icon.png`` (new in D1): the icon iOS puts on the home screen."""

    def test_it_is_180_pixels_square(self):
        problems = _size_problems(APPLE_TOUCH_ICONS)
        assert not problems, _report("iOS takes a 180x180 home-screen icon:", problems)

    def test_it_is_opaque_rgb_with_no_alpha_channel(self):
        problems = _opacity_problems(APPLE_TOUCH_ICONS)
        assert not problems, _report(OPAQUE_HEADLINE, problems)

    def test_app_html_links_it_at_180x180(self):
        links = _apple_touch_links()
        assert len(links) == 1, f"app.html carries {len(links)} rel=apple-touch-icon links, expected exactly one: {links}"
        href, sizes = links[0].get("href"), links[0].get("sizes")
        problems = []
        if href != APPLE_TOUCH_HREF:
            problems.append(f"href={href!r}, expected {APPLE_TOUCH_HREF!r}")
        if sizes != "180x180":
            problems.append(f"sizes={sizes!r}, expected '180x180'")
        if href and not _served(href).is_file():
            problems.append(f"{href} is not a file under frontend/static/")
        assert not problems, _report("app.html gives iOS its own 180x180 icon instead of the 192 'any' one:", problems)


class TestManifestIcons:
    """``manifest.json``: one file per purpose and size, each one what the entry says it is."""

    def test_the_splash_is_the_beige_the_maskable_icons_are_painted_in(self):
        colour = _manifest().get("background_color")
        assert isinstance(colour, str) and colour.lower() == SPLASH_BEIGE, f"background_color is {colour!r}: the maskable icons are painted in {SPLASH_BEIGE} to meet the splash without a seam, so change both or neither"

    def test_one_any_icon_per_size(self):
        problems = _purpose_problems("any")
        assert not problems, _report("exactly one 'any' entry per size, naming its own file:", problems)

    def test_one_maskable_icon_per_size(self):
        problems = _purpose_problems("maskable")
        assert not problems, _report("exactly one 'maskable' entry per size, naming its own file:", problems)

    def test_no_file_serves_both_purposes(self):
        purposes_by_src: dict[str, set[str]] = {}
        for entry in _manifest_icons():
            purposes_by_src.setdefault(entry.get("src"), set()).update(_purposes(entry))
        shared = sorted(src for src, purposes in purposes_by_src.items() if {"any", "maskable"} <= purposes)
        assert not shared, f"an 'any' icon fills its square and a 'maskable' one keeps a safe zone, so no file can be both; declared as both: {shared}"

    def test_every_entry_points_at_an_existing_file(self):
        missing = [entry.get("src") for entry in _manifest_icons() if not _served(entry.get("src") or "").is_file()]
        assert not missing, f"manifest icons with no file under frontend/static/: {missing}"

    def test_every_entry_declares_its_real_pixel_size(self):
        problems = []
        for entry in _manifest_icons():
            path = _served(entry.get("src") or "")
            if not path.is_file():
                problems.append(f"{entry.get('src')}: missing")
                continue
            with Image.open(path) as image:
                real = f"{image.width}x{image.height}"
            if entry.get("sizes") != real:
                problems.append(f"{entry.get('src')}: sizes={entry.get('sizes')!r}, the file is {real}")
        assert not problems, _report("each manifest entry declares the size of the file it names:", problems)

    def test_every_entry_is_a_png(self):
        problems = []
        for entry in _manifest_icons():
            src = entry.get("src")
            if entry.get("type") != "image/png":
                problems.append(f"{src}: type={entry.get('type')!r}, expected 'image/png'")
            path = _served(src or "")
            if not path.is_file():
                problems.append(f"{src}: missing")
                continue
            with Image.open(path) as image:
                if image.format != "PNG":
                    problems.append(f"{src}: the file is {image.format}, not PNG")
        assert not problems, _report("each manifest entry is typed image/png, and is one:", problems)


class TestServiceWorkerStamp:
    """``sw.js`` names the ``offline.html`` it caches, so that editing the page reaches installed clients."""

    def test_sw_js_carries_exactly_one_build_stamp(self):
        stamps = _stamps()
        assert len(stamps) == 1, f"sw.js carries {len(stamps)} '// build:' lines, expected exactly one: {stamps}"

    def test_the_stamp_is_the_md5_of_offline_html(self):
        expected = _offline_page_hash()
        stamps = _stamps()
        why = "a page edit that does not change sw.js never reaches installed clients, which keep the old offline page"
        fix = "restamp sw.js with dev.py's stamp_service_worker() and commit it together with the page"
        assert stamps and set(stamps) == {expected}, f"sw.js is stamped {stamps}, offline.html hashes to {expected!r}: {why}. Fix: {fix}."


class TestStampServiceWorker:
    """dev.py's ``stamp_service_worker()`` on copies under ``tmp_path``: ``sw.js`` is written when its stamp changes, and only then (H-52)."""

    def test_stamping_again_with_the_page_unchanged_leaves_sw_js_untouched(self, static_copy):
        stamped = _stamp_afresh(static_copy)
        _age(static_copy.root)

        dev.stamp_service_worker()

        assert static_copy.service_worker.read_bytes() == stamped, "a second stamp with offline.html unchanged changed the bytes of sw.js"
        mtime_ns = static_copy.service_worker.stat().st_mtime_ns
        why = "it runs with every docs build, and check_frontend_needs_build() watches frontend/static/: sw.js newer than build/index.html makes the next dev.py server rebuild the frontend for nothing"
        assert mtime_ns == AGED_NS, f"H-52: a second stamp with offline.html unchanged rewrote sw.js with the bytes it already held (mtime {AGED_NS} → {mtime_ns}): {why}"

    def test_an_edited_page_is_stamped_on_line_2_and_the_rest_of_sw_js_kept(self, static_copy):
        before = _stamp_afresh(static_copy).decode("utf-8").splitlines(keepends=True)
        static_copy.page.write_bytes(static_copy.page.read_bytes() + LATER_PAGE_EDIT)
        expected = _offline_page_hash(static_copy.page)
        assert _stamps(static_copy.service_worker) != [expected], "premise: the edit changes the page's hash"
        _age(static_copy.root)

        dev.stamp_service_worker()

        after = static_copy.service_worker.read_bytes().decode("utf-8").splitlines(keepends=True)
        assert after[1:2] == [f"// build: {expected}\n"], f"line 2 of sw.js is {after[1:2]}, expected the edited page's stamp {expected!r}"
        assert _stamps(static_copy.service_worker) == [expected], f"sw.js carries {_stamps(static_copy.service_worker)}, expected exactly one stamp, {expected!r}"
        assert after[:1] + after[2:] == before[:1] + before[2:], "restamping changed sw.js beyond its line 2"
        assert static_copy.service_worker.stat().st_mtime_ns != AGED_NS, "premise of the untouched case: on this filesystem a write moves sw.js off AGED_NS"

    @pytest.mark.parametrize("missing", ["sw.js", "offline.html"])
    def test_a_missing_sw_js_or_offline_html_writes_nothing(self, static_copy, missing):
        (static_copy.root / "frontend" / "static" / missing).unlink()
        _age(static_copy.root)
        before = _files_under(static_copy.root)

        dev.stamp_service_worker()  # a missing file is no error: an exception fails the case

        assert _files_under(static_copy.root) == before, f"with {missing} missing, stamp_service_worker() wrote under the copy of frontend/static/"


class TestFrontendBuildStampsServiceWorker:
    """``cmd_fe_build`` stamps ``sw.js`` before its npm build, so the build ships the stamp of the ``offline.html`` it ships (H-52)."""

    @pytest.mark.parametrize("debug", [True, False], ids=["debug-build", "production-build"])
    def test_sw_js_is_stamped_before_the_build_command_runs(self, monkeypatch, static_copy, debug):
        calls = _stand_in_for_fe_build(monkeypatch, static_copy)

        assert dev.cmd_fe_build(SimpleNamespace(debug=debug)) == 0

        assert "npm build" in calls.events, f"premise: cmd_fe_build reached its npm build: {calls.events}"
        build_at = calls.events.index("npm build")
        why = "the build ships a sw.js stamped for another offline.html than the one it ships, and installed clients keep their old offline page until a later docs build restamps sw.js"
        assert "stamp_service_worker" in calls.events[:build_at], f"H-52: cmd_fe_build ran {calls.events}, no stamp_service_worker() before its npm build: {why}"
        expected = _offline_page_hash(static_copy.page)
        assert calls.stamps_at_build == [[expected]], f"H-52: the npm build found sw.js stamped {calls.stamps_at_build}, the offline.html it ships hashing to {expected!r}: {why}"
