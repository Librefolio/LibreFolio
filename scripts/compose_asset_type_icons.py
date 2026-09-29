#!/usr/bin/env python3
"""
Compose the asset-type icons of the subtypes: container icon + content pastille.

An ETF that holds equity is still an ETF, so its icon stays the ETF tag; what it holds is a
small pastille in the bottom-right corner, drawn from the icon of the base type it contains
(decisions D52/D61 of the risk campaign, delivered by workstream K as R16). The same rule
applies to every family: ``CROWDFUND_REAL_ESTATE`` is the crowdfunding icon with the
real-estate pastille.

The composites are static PNG files, not an overlay drawn at runtime, because the asset-type
icon is rendered by about twenty call sites with three different technologies (Svelte
``<img>``, hand-built HTML table cells, ECharts rich text). All of them go through
``getAssetTypeIconUrl()``, so a file per subtype reaches every one of them unchanged.

Single source of truth: the mappings are read, as text, from
``frontend/src/lib/utils/assetTypes.ts`` — ``PNG_MAP`` (file names), ``ASSET_TYPE_FAMILY``
(subtype → container type) and ``ASSET_TYPE_CONTENT_ICON`` (subtype → content icon). The
composite of a subtype is named ``{container file}-{content file}.png`` and ``PNG_MAP`` must
name exactly that file; the script refuses to run otherwise. The frontend gate
``assetTypeTables.test.ts`` checks the same convention and that every file exists.

Usage:
    pipenv run python scripts/compose_asset_type_icons.py
    pipenv run python scripts/compose_asset_type_icons.py --check

Run it again whenever a base icon or one of the three mappings changes. ``--check`` rebuilds
every composite in memory and compares it with the files on disk without writing anything.
"""

import argparse
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSET_TYPES_TS = REPO_ROOT / "frontend" / "src" / "lib" / "utils" / "assetTypes.ts"
ICON_DIRS = (
    REPO_ROOT / "frontend" / "static" / "icons" / "asset-types",
    REPO_ROOT / "mkdocs_src" / "docs" / "static" / "icons" / "asset-types",
)
SOURCE_DIR = ICON_DIRS[0]

CANVAS = 192
PASTILLE_RATIO = 0.50  # disc diameter / canvas side
GLYPH_RATIO = 0.66  # content icon / disc diameter
RING_RATIO = 0.06  # ring width / disc diameter
DISC_FILL = (255, 255, 255, 255)
RING_COLOUR = (71, 85, 105, 255)  # slate-600: separates a green glyph from a green container in both themes
PIXEL_TOLERANCE = 2  # --check: largest per-channel difference accepted (resampling across Pillow builds)


class ComposeError(RuntimeError):
    """The mappings in assetTypes.ts cannot produce a consistent set of composites."""


def read_record(source: str, name: str) -> dict[str, str]:
    """Scrape one ``const NAME: … = { KEY: 'value', … };`` object literal from the TypeScript source."""
    matches = list(re.finditer(rf"(?:export\s+)?const\s+{name}\s*:[^=]*=\s*\{{", source))
    if len(matches) != 1:
        raise ComposeError(f"{ASSET_TYPES_TS.name}: expected exactly one declaration of {name}, found {len(matches)}")
    start = matches[0].end()
    end = source.find("};", start)
    if end == -1:
        raise ComposeError(f"{ASSET_TYPES_TS.name}: the object literal of {name} is never closed with '}};'")
    entries = dict(re.findall(r"^\s*([A-Z][A-Z0-9_]*)\s*:\s*'([^']+)'", source[start:end], flags=re.MULTILINE))
    if not entries:
        raise ComposeError(f"{ASSET_TYPES_TS.name}: {name} parsed as empty — the scrape no longer matches the source")
    return entries


def plan_composites(source: str) -> dict[str, tuple[str, str]]:
    """Map every composite file name to its (container file, content file) pair, validating the three tables."""
    png_map = read_record(source, "PNG_MAP")
    family = read_record(source, "ASSET_TYPE_FAMILY")
    content = read_record(source, "ASSET_TYPE_CONTENT_ICON")

    if set(family) != set(content):
        raise ComposeError(f"ASSET_TYPE_FAMILY and ASSET_TYPE_CONTENT_ICON disagree on the subtypes: only in FAMILY {sorted(set(family) - set(content))}, only in CONTENT_ICON {sorted(set(content) - set(family))}")

    plan: dict[str, tuple[str, str]] = {}
    for subtype in sorted(family):
        container_type = family[subtype]
        if container_type not in png_map:
            raise ComposeError(f"{subtype}: container type {container_type} has no PNG_MAP entry")
        container_file = png_map[container_type]
        expected = f"{container_file}-{content[subtype]}"
        if png_map.get(subtype) != expected:
            raise ComposeError(f"{subtype}: PNG_MAP names {png_map.get(subtype)!r}, the composite convention requires {expected!r}")
        for base in (container_file, content[subtype]):
            if not (SOURCE_DIR / f"{base}.png").is_file():
                raise ComposeError(f"{subtype}: base icon {base}.png is missing from {SOURCE_DIR.relative_to(REPO_ROOT)}")
        plan[expected] = (container_file, content[subtype])
    return plan


def fit(image: Image.Image, box: int) -> Image.Image:
    """Scale into a ``box``×``box`` square keeping the aspect ratio (CSS ``object-contain``)."""
    image = image.convert("RGBA")
    ratio = min(box / image.width, box / image.height)
    size = (max(1, round(image.width * ratio)), max(1, round(image.height * ratio)))
    return image.resize(size, Image.Resampling.LANCZOS)


def compose(container_file: str, content_file: str) -> Image.Image:
    """Draw the container icon on a square canvas and the content pastille in its bottom-right corner."""
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    base = fit(Image.open(SOURCE_DIR / f"{container_file}.png"), CANVAS)
    canvas.alpha_composite(base, ((CANVAS - base.width) // 2, (CANVAS - base.height) // 2))

    disc = round(CANVAS * PASTILLE_RATIO)
    ring = max(2, round(disc * RING_RATIO))
    left = top = CANVAS - disc
    ImageDraw.Draw(canvas).ellipse((left, top, CANVAS - 1, CANVAS - 1), fill=DISC_FILL, outline=RING_COLOUR, width=ring)
    glyph = fit(Image.open(SOURCE_DIR / f"{content_file}.png"), round(disc * GLYPH_RATIO))
    canvas.alpha_composite(glyph, (left + (disc - glyph.width) // 2, top + (disc - glyph.height) // 2))
    return canvas


def differs(expected: Image.Image, path: Path) -> bool:
    """True when the file on disk is not the composite this script would write."""
    if not path.is_file():
        return True
    actual = Image.open(path).convert("RGBA")
    if actual.size != expected.size:
        return True
    extrema = ImageChops.difference(expected, actual).getextrema()
    return max(high for _low, high in extrema) > PIXEL_TOLERANCE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="Compare the files on disk with a fresh build; write nothing")
    args = parser.parse_args()

    try:
        plan = plan_composites(ASSET_TYPES_TS.read_text(encoding="utf-8"))
    except ComposeError as error:
        print(f"❌ {error}", file=sys.stderr)
        return 2

    stale: list[str] = []
    for name, (container_file, content_file) in plan.items():
        image = compose(container_file, content_file)
        for directory in ICON_DIRS:
            target = directory / f"{name}.png"
            if args.check:
                if differs(image, target):
                    stale.append(str(target.relative_to(REPO_ROOT)))
                continue
            directory.mkdir(parents=True, exist_ok=True)
            image.save(target, optimize=True)
            print(f"✅ {target.relative_to(REPO_ROOT)}  ({target.stat().st_size} B)  = {container_file} + {content_file}")

    if args.check:
        if stale:
            print("❌ composites missing or out of date — rerun without --check:", *stale, sep="\n  ", file=sys.stderr)
            return 1
        print(f"✅ {len(plan)} composites × {len(ICON_DIRS)} directories up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
