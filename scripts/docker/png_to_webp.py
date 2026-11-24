"""Replace the PNGs of one folder with their WebP copies. Runs in a Docker build stage, never on the repository.

usage: python png_to_webp.py <folder> [quality]

The image carries the default avatars as WebP (quality 85: 24.7 MB of PNG become about 2.6 MB), while the repository keeps
the full-size PNGs, which the tests, the E2E specs and a development server read. The ``avatars-webp`` stage of the
Dockerfile copies the PNG folder in, runs this on the copy, and the final stage takes only the result: no PNG reaches
the image, and the repository is not touched.

Every PNG of the folder (no subfolder) is converted with the gallery's converter (``scripts/gallery_webp.py``: RGB or
RGBA, written under a temporary name and renamed when complete). The PNG is deleted only after its WebP is in place.
The run fails, with exit status 1 and the reason on stderr, when the folder is missing, holds no PNG, or a PNG cannot be
converted: a silent success would ship an image without avatars, or with the PNGs left in it.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The Docker stage copies this file and gallery_webp.py under the same layout as the repository.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.gallery_webp import WEBP_QUALITY, convert_one, webp_path  # noqa: E402


def convert_folder(folder: Path, quality: int = WEBP_QUALITY) -> list[str]:
    """Convert the PNGs directly inside ``folder`` and delete them. Returns the problems, empty on success."""
    if not folder.is_dir():
        return [f"{folder} is not a folder"]
    pngs = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".png")
    if not pngs:
        return [f"{folder} holds no PNG: nothing to convert"]
    problems: list[str] = []
    for png in pngs:
        reason = convert_one(png, quality)
        if reason is not None:
            problems.append(f"{png.name}: {reason}")
            continue
        if not webp_path(png).is_file() or webp_path(png).stat().st_size == 0:
            problems.append(f"{png.name}: the WebP is missing or empty")
            continue
        png.unlink()
    return problems


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__.split("\n\n")[0], file=sys.stderr)
        return 2
    quality = int(argv[2]) if len(argv) == 3 else WEBP_QUALITY
    problems = convert_folder(Path(argv[1]), quality)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    count = len(list(Path(argv[1]).glob("*.webp")))
    print(f"{count} PNG converted to WebP (quality {quality}) in {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
