"""WebP copies of the documentation gallery, written beside the PNGs the gallery produces.

``./dev.py mkdocs gallery`` keeps writing PNG: Playwright cannot write WebP, and
``scripts/visual_review/*`` read the PNGs. At the end of the run the PNGs are
converted to WebP at quality 85, which is visually the same picture at about a third
of the weight (518 MB of PNG became about 178 MB, measured on 40 shots). The
documentation pages ask for the ``.webp`` (``javascripts/gallery-img-loader.js``); the
site keeps both files, because the images already released, and the README, read the
``.png`` from GitHub Pages.

Only what needs work is converted: a PNG with no WebP, or newer than its WebP. A
partial gallery run (``-f``) therefore converts just its own shots, and running the
conversion again does nothing.

A WebP is written under a temporary name and renamed when complete, so a crash never
leaves a half-written file that looks up to date. A PNG that cannot be read is reported
and left without a WebP; it stops nothing else.
"""

from __future__ import annotations

import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PIL import Image

#: WebP quality of the gallery: measured on 40 shots, indistinguishable from the PNG by eye.
WEBP_QUALITY = 85

#: Suffix of the temporary file a WebP is written to before it takes its final name.
_TMP_SUFFIX = ".webp.tmp"


@dataclass
class ConversionReport:
    """What one run of :func:`convert_gallery_webp` did."""

    converted: int = 0
    up_to_date: int = 0
    #: ``(png path, reason)`` of each PNG that could not be converted.
    failed: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.converted + self.up_to_date + len(self.failed)


def webp_path(png: Path) -> Path:
    """The WebP that goes with a PNG: same folder, same name."""
    return png.with_suffix(".webp")


def needs_conversion(png: Path) -> bool:
    """True when the PNG has no WebP, or is newer than it."""
    webp = webp_path(png)
    try:
        return png.stat().st_mtime_ns > webp.stat().st_mtime_ns
    except FileNotFoundError:
        return True


def convert_one(png: Path, quality: int = WEBP_QUALITY) -> Optional[str]:
    """Write the WebP of one PNG. Returns ``None`` on success, the reason on failure."""
    webp = webp_path(png)
    tmp = png.with_suffix(_TMP_SUFFIX)
    try:
        with Image.open(png) as image:
            image.load()
            # WebP holds RGB and RGBA: anything else (palette, grayscale) goes to one of them.
            has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
            image = image.convert("RGBA" if has_alpha else "RGB")
            image.save(tmp, format="WEBP", quality=quality)
        os.replace(tmp, webp)
        return None
    except Exception as exc:  # a broken PNG must not stop the others
        tmp.unlink(missing_ok=True)
        return f"{type(exc).__name__}: {exc}"


def _convert_task(args: tuple[str, int]) -> tuple[str, Optional[str]]:
    png, quality = args
    return png, convert_one(Path(png), quality)


def convert_gallery_webp(root: Path, *, quality: int = WEBP_QUALITY, workers: Optional[int] = None) -> ConversionReport:
    """Convert the PNGs under ``root`` that have no up-to-date WebP, in parallel.

    ``workers`` defaults to the CPU count. The report says how many were converted, how many
    were already up to date and which failed.
    """
    report = ConversionReport()
    pending: list[Path] = []
    for png in sorted(root.rglob("*.png")):
        if needs_conversion(png):
            pending.append(png)
        else:
            report.up_to_date += 1
    if not pending:
        return report

    count = max(1, min(workers or os.cpu_count() or 1, len(pending)))
    tasks = [(str(png), quality) for png in pending]
    if count == 1:
        results = [_convert_task(task) for task in tasks]
    else:
        # "spawn" on every platform: it is the macOS default, where the developer runs the gallery, and the tests then walk
        # the same path as the Mac (each worker imports this module, and dev.py as __mp_main__, behind its __main__ guard).
        with ProcessPoolExecutor(max_workers=count, mp_context=multiprocessing.get_context("spawn")) as pool:
            results = list(pool.map(_convert_task, tasks, chunksize=4))
    for png, reason in results:
        if reason is None:
            report.converted += 1
        else:
            report.failed.append((Path(png), reason))
    return report
