#!/usr/bin/env python3
"""
Compose the icons of the broker import plugins: the broker's logo + an account badge.

A broker with two accounts gets one LibreFolio broker per account, and one BRIM plugin each:
Scalable Capital's broker account (``broker_scalable``) and its overnight account
(``broker_scalable_deposit``). The plugin's icon tells them apart: the broker's logo, untouched,
with a badge showing the account's icon in the LibreFolio exporter, the browser extension that
exports both accounts. As on the exporter's account tiles, the glyph is white on the account's
colour: ``chart-line-fill`` on blue for the broker account, ``piggy-bank-fill`` on orange for the
overnight account.

The app crops broker icons to a circle (``BrokerIcon``), which would cut a badge drawn in the
corner. So the badge sits on the bottom-right diagonal, just inside that circle.

The glyphs are Phosphor Icons (MIT, see ``scripts/assets/brokers/glyphs/LICENSE``):
``glyphs/<name>.svg`` is the source and ``glyphs/<name>.png`` its 512 px alpha mask, so building
needs Pillow only. After changing an SVG, rerender its mask:
``rsvg-convert -w 512 -h 512 -b none <name>.svg -o <name>.png``.

Outputs:
- ``backend/app/services/brim_providers/static/<broker>/<account>.png``: the plugin's
  ``icon_url`` (``BRIMProvider.generate_static_url``), served by
  ``/api/v1/uploads/plugin/brim/``. A broker without an icon of its own shows the icon of its
  default import plugin, so choosing the plugin is enough;
- ``frontend/static/icons/brokers/<broker>.png`` and ``<broker>-<account>.png``: the logo and the
  composites, for the user guide. ``dev.py mkdocs build`` copies ``frontend/static/icons/`` over
  ``mkdocs_src/docs/static/icons/``, so they are written to both, like the asset-type composites.

The logos live in ``scripts/assets/brokers/``, so building never depends on the network. They
are the brokers' own favicons, used unchanged to recognise the broker; LibreFolio is not
affiliated with them.

Usage:
    pipenv run python scripts/compose_broker_icons.py
    pipenv run python scripts/compose_broker_icons.py --check

``--check`` rebuilds every icon in memory and compares it with the files on disk without
writing anything.
"""

import argparse
import math
import sys
from pathlib import Path

from compose_asset_type_icons import CANVAS, differs, fit
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_DIR = REPO_ROOT / "scripts" / "assets" / "brokers"
GLYPH_DIR = LOGO_DIR / "glyphs"
PLUGIN_STATIC_DIR = REPO_ROOT / "backend" / "app" / "services" / "brim_providers" / "static"
DOCS_DIRS = (
    REPO_ROOT / "frontend" / "static" / "icons" / "brokers",
    REPO_ROOT / "mkdocs_src" / "docs" / "static" / "icons" / "brokers",
)

BADGE_RATIO = 0.52  # badge diameter / canvas side
BADGE_GLYPH_RATIO = 0.62  # glyph box (the icon's whole 256-unit grid) / badge diameter
BADGE_RING_RATIO = 0.06  # ring width / badge diameter
BADGE_RING = (255, 255, 255, 255)
GLYPH_COLOUR = (255, 255, 255, 255)
BROKER_BLUE = (58, 99, 168, 255)  # #3a63a8, the exporter's broker tile
DEPOSIT_ORANGE = (232, 120, 30, 255)  # #e8781e, the exporter's overnight tile

# broker logo (scripts/assets/brokers/<broker>.png) → {account: (glyph, badge colour)}
ACCOUNTS = {
    "scalable": {"broker": ("chart-line-fill", BROKER_BLUE), "deposit": ("piggy-bank-fill", DEPOSIT_ORANGE)},
}


def logo(broker: str) -> Image.Image:
    """The broker's logo, centred on the standard square canvas."""
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    base = fit(Image.open(LOGO_DIR / f"{broker}.png"), CANVAS)
    canvas.alpha_composite(base, ((CANVAS - base.width) // 2, (CANVAS - base.height) // 2))
    return canvas


def compose(broker: str, glyph: str, colour: tuple[int, int, int, int]) -> Image.Image:
    """The broker's logo with the account badge on its bottom-right diagonal."""
    canvas = logo(broker)
    disc = round(CANVAS * BADGE_RATIO)
    ring = max(2, round(disc * BADGE_RING_RATIO))
    # Badge centre on the diagonal, so that its edge stays 1 px inside the circle BrokerIcon crops to.
    centre = CANVAS / 2 + (CANVAS / 2 - disc / 2 - 1) / math.sqrt(2)
    left = top = round(centre - disc / 2)
    ImageDraw.Draw(canvas).ellipse((left, top, left + disc - 1, top + disc - 1), fill=colour, outline=BADGE_RING, width=ring)
    mask = fit(Image.open(GLYPH_DIR / f"{glyph}.png"), round(disc * BADGE_GLYPH_RATIO)).getchannel("A")
    paint = Image.new("RGBA", mask.size, GLYPH_COLOUR)
    paint.putalpha(mask)
    canvas.alpha_composite(paint, (left + (disc - mask.width) // 2, top + (disc - mask.height) // 2))
    return canvas


def plan() -> dict[Path, Image.Image]:
    """Every icon to write, by target path."""
    icons: dict[Path, Image.Image] = {}
    for broker, accounts in ACCOUNTS.items():
        for docs_dir in DOCS_DIRS:
            icons[docs_dir / f"{broker}.png"] = logo(broker)
        for account, (glyph, colour) in accounts.items():
            image = compose(broker, glyph, colour)
            icons[PLUGIN_STATIC_DIR / broker / f"{account}.png"] = image
            for docs_dir in DOCS_DIRS:
                icons[docs_dir / f"{broker}-{account}.png"] = image
    return icons


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--check", action="store_true", help="Compare the files on disk with a fresh build; write nothing")
    args = parser.parse_args()

    icons = plan()
    if args.check:
        stale = [str(path.relative_to(REPO_ROOT)) for path, image in icons.items() if differs(image, path)]
        if stale:
            print("❌ broker icons missing or out of date — rerun without --check:", *stale, sep="\n  ", file=sys.stderr)
            return 1
        print(f"✅ {len(icons)} broker icons up to date")
        return 0

    for path, image in icons.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, optimize=True)
        print(f"✅ {path.relative_to(REPO_ROOT)}  ({path.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
