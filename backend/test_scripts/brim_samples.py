"""Where the BRIM sample reports are (U-B4): each plugin keeps its own in ``brim_providers/<plugin>/sample_reports/``.

The family root keeps ``sample_reports/`` too, for what belongs to no one plugin: the README and ``malformed/``.
``SampleDir`` is the corpus of all of them seen as one flat folder, for the tests that read every sample or look one up by
its file name. It stands where the old single ``SAMPLE_DIR`` stood: ``SAMPLE_DIR / "degiro-export.csv"``, ``glob``,
``rglob``, ``iterdir``, ``exists``, and ``relative_to(SAMPLE_DIR)`` (the path of a sample from the family root).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator, List

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIM_PROVIDERS_DIR = REPO_ROOT / "backend" / "app" / "services" / "brim_providers"
# What belongs to no plugin: the README and the deliberately broken fixtures.
SHARED_SAMPLES_DIR = BRIM_PROVIDERS_DIR / "sample_reports"


def plugin_samples_dir(plugin_folder: str) -> Path:
    """The ``sample_reports/`` folder of one plugin (``broker_degiro``)."""
    return BRIM_PROVIDERS_DIR / plugin_folder / "sample_reports"


def sample_dirs() -> List[Path]:
    """Every folder that holds samples: the shared one and each plugin's, in name order."""
    found = [path for path in sorted(BRIM_PROVIDERS_DIR.glob("*/sample_reports")) if path.is_dir()]
    return [SHARED_SAMPLES_DIR, *found]


class SampleDir(os.PathLike):
    """All the sample folders as one flat folder; as a path it is the family root, so ``path.relative_to(SAMPLE_DIR)`` names the plugin."""

    def __fspath__(self) -> str:
        return str(BRIM_PROVIDERS_DIR)

    def __str__(self) -> str:
        return str(BRIM_PROVIDERS_DIR)

    def __truediv__(self, name: str) -> Path:
        """The sample called ``name`` (a file name, ``malformed``, or a name no plugin owns: a path that does not exist)."""
        for folder in sample_dirs():
            candidate = folder / name
            if candidate.exists():
                return candidate
        return SHARED_SAMPLES_DIR / name

    def exists(self) -> bool:
        return SHARED_SAMPLES_DIR.is_dir()

    def is_dir(self) -> bool:
        return True

    def glob(self, pattern: str) -> Iterator[Path]:
        yield from sorted((path for folder in sample_dirs() for path in folder.glob(pattern)), key=lambda path: path.name)

    def rglob(self, pattern: str) -> Iterator[Path]:
        yield from sorted((path for folder in sample_dirs() for path in folder.rglob(pattern)), key=lambda path: path.name)

    def iterdir(self) -> Iterator[Path]:
        yield from sorted((path for folder in sample_dirs() for path in folder.iterdir()), key=lambda path: path.name)
