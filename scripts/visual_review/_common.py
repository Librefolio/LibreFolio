"""Shared paths for the visual review tools.

Outputs (snapshots, diffs, packages, inventories) are large and never belong to the repository:
they go to ``--work-dir``, else ``$LF_VISUAL_REVIEW_DIR``, else ``~/LibreFolio_visual_review``.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"
DEFAULT_WORK_DIR = Path.home() / "LibreFolio_visual_review"


def work_dir(override: str | None = None) -> Path:
    """Resolve and create the output root; refuse a path inside the repository."""
    raw = override or os.environ.get("LF_VISUAL_REVIEW_DIR") or str(DEFAULT_WORK_DIR)
    path = Path(raw).expanduser().resolve()
    if path == REPO or REPO in path.parents:
        raise SystemExit(f"work dir {path} is inside the repository {REPO}: choose a path outside it")
    path.mkdir(parents=True, exist_ok=True)
    return path
