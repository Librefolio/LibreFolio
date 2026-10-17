"""Shared paths for the visual review tools.

Outputs (snapshots, diffs, packages, inventories) are large and never belong to the repository. They go to
``--work-dir``, else ``$LF_VISUAL_REVIEW_DIR``, else ``<folder of the main checkout>/LibreFolio_subRepo/LibreFolio_visual_review``
when ``LibreFolio_subRepo`` exists next to the main checkout (the developer's layout), else ``~/LibreFolio_visual_review``.
Worktrees resolve the main checkout through git, so every checkout of the repo shares the same default.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data"


def main_checkout() -> Path:
    """The main checkout of this repository, also when running from a linked worktree."""
    try:
        common = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
        return Path(common).parent
    except (OSError, subprocess.CalledProcessError):
        return REPO


def default_work_dir() -> Path:
    sub_repo = main_checkout().parent / "LibreFolio_subRepo"
    return sub_repo / "LibreFolio_visual_review" if sub_repo.is_dir() else Path.home() / "LibreFolio_visual_review"


def work_dir(override: str | None = None) -> Path:
    """Resolve and create the output root; refuse a path inside the repository."""
    raw = override or os.environ.get("LF_VISUAL_REVIEW_DIR") or str(default_work_dir())
    path = Path(raw).expanduser().resolve()
    if path == REPO or REPO in path.parents:
        raise SystemExit(f"work dir {path} is inside the repository {REPO}: choose a path outside it")
    path.mkdir(parents=True, exist_ok=True)
    return path
