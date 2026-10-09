#!/usr/bin/env python3
"""
Compose the icons of the broker import plugins: the broker's logo + an account pastille.

A broker with two accounts gets one LibreFolio broker per account, and one BRIM plugin each:
Scalable Capital's broker account (``broker_scalable``) and its overnight account
(``broker_scalable_deposit``). The plugin's icon tells them apart: the broker's logo, untouched,
with a pastille in the bottom-right corner drawn from the asset-type icon of what the account
holds — ``stock`` for the broker account, ``liquidity`` for the overnight account. The geometry
is the one of the asset-type composites (``compose_asset_type_icons.py``), whose constants and
helpers are reused.

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
import sys
from pathlib import Path

from compose_asset_type_icons import CANVAS, DISC_FILL, GLYPH_RATIO, PASTILLE_RATIO, RING_COLOUR, RING_RATIO, SOURCE_DIR, differs, fit
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_DIR = REPO_ROOT / "scripts" / "assets" / "brokers"
PLUGIN_STATIC_DIR = REPO_ROOT / "backend" / "app" / "services" / "brim_providers" / "static"
DOCS_DIRS = (
    REPO_ROOT / "frontend" / "static" / "icons" / "brokers",
    REPO_ROOT / "mkdocs_src" / "docs" / "static" / "icons" / "brokers",
)

# broker logo (scripts/assets/brokers/<broker>.png) → {account: asset-type icon of its pastille}
ACCOUNTS = {
    "scalable": {"broker": "stock", "deposit": "liquidity"},
}


def logo(broker: str) -> Image.Image:
    """The broker's logo, centred on the standard square canvas."""
    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    base = fit(Image.open(LOGO_DIR / f"{broker}.png"), CANVAS)
    canvas.alpha_composite(base, ((CANVAS - base.width) // 2, (CANVAS - base.height) // 2))
    return canvas


def compose(broker: str, glyph_file: str) -> Image.Image:
    """The broker's logo with the pastille of an asset-type icon in its bottom-right corner."""
    canvas = logo(broker)
    disc = round(CANVAS * PASTILLE_RATIO)
    ring = max(2, round(disc * RING_RATIO))
    left = top = CANVAS - disc
    ImageDraw.Draw(canvas).ellipse((left, top, CANVAS - 1, CANVAS - 1), fill=DISC_FILL, outline=RING_COLOUR, width=ring)
    glyph = fit(Image.open(SOURCE_DIR / f"{glyph_file}.png"), round(disc * GLYPH_RATIO))
    canvas.alpha_composite(glyph, (left + (disc - glyph.width) // 2, top + (disc - glyph.height) // 2))
    return canvas


def plan() -> dict[Path, Image.Image]:
    """Every icon to write, by target path."""
    icons: dict[Path, Image.Image] = {}
    for broker, accounts in ACCOUNTS.items():
        for docs_dir in DOCS_DIRS:
            icons[docs_dir / f"{broker}.png"] = logo(broker)
        for account, glyph_file in accounts.items():
            image = compose(broker, glyph_file)
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
