"""PWA icons and the service-worker stamp: what an installed LibreFolio shows (K, R2 step 13, item 1).

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

PURE: it reads the committed files under ``frontend/static/`` and
``frontend/src/app.html``, which is what a browser gets. No DB, no server, no
network, no writes. It never runs the generator: ``copy_docs_assets()`` rewrites
the icons and restamps ``sw.js``, and a test that ran it would only be comparing
the generator with itself.
"""

import hashlib
import json
import math
from functools import cache
from html.parser import HTMLParser
from pathlib import Path

from PIL import Image

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


def _stamps() -> list[str]:
    """Every ``// build:`` line of ``sw.js``: the lines ``stamp_service_worker()`` itself recognises and rewrites."""
    lines = SERVICE_WORKER.read_text(encoding="utf-8").splitlines()
    return [line.removeprefix("// build:").strip() for line in lines if line.startswith("// build:")]


def _offline_page_hash() -> str:
    """What ``stamp_service_worker()`` writes: the first 8 hex digits of the page's md5."""
    return hashlib.md5(OFFLINE_PAGE.read_bytes(), usedforsecurity=False).hexdigest()[:8]


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
