"""
Version utilities for LibreFolio.

Gets the version from LF_APP_VERSION when a build froze it, else from git tags in a checkout, else from a
pre-generated VERSION file where there is no git repository (the Docker image, which has no .git/).
"""

import os
import subprocess
from functools import lru_cache
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


def _project_root() -> Path:
    """The directory that holds ``backend/``: the repository root, or the image's app root (``/app``).

    Derived from the module's dotted name, so a move inside the package keeps it right:
    ``backend.app.utils.runtime.version`` is five names deep, so the root is four directories up.
    """
    return Path(__file__).resolve().parents[__name__.count(".")]


def _git_describe(project_root: Path) -> str | None:
    """``git describe`` run in the project root, or None when git cannot answer."""
    try:
        result = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], capture_output=True, text=True, cwd=project_root, timeout=5)
    except Exception:
        logger.debug("git_describe_failed", cwd=str(project_root), exc_info=True)
        return None
    version = result.stdout.strip()
    if result.returncode != 0 or not version:
        return None
    # Normalize hash-only output (no tags exist)
    if not version.startswith(("v", "V")):
        version = f"v0.0.0-g{version}"
    return version


def _version_file(project_root: Path) -> str | None:
    """The content of the VERSION file, or None when it is missing, blank or unreadable."""
    version_file = project_root / "VERSION"
    try:
        content = version_file.read_text().strip()
    except FileNotFoundError:
        return None
    except Exception:
        logger.debug("version_file_read_failed", path=str(version_file), exc_info=True)
        return None
    return content or None


@lru_cache(maxsize=1)
def get_git_version() -> str:
    """
    Get the app version: from ``git describe`` in a checkout, from the VERSION file without one.

    ``LF_APP_VERSION``, when set, comes first: the release workflow freezes it from VERSION for every later
    step of its job, so a step that writes a tracked file cannot make the gallery's servers report ``-dirty``.
    A checkout has ``.git`` in the project root (a folder, or a file in a worktree or a submodule): there
    ``git describe`` decides, and a VERSION file left over by an earlier build cannot hide a newer commit.
    The VERSION file counts only without ``.git``, or when ``git describe`` fails. The Docker image has no
    .git/ (by design, to keep it small): ``./dev.py docker build`` and the release workflow freeze the
    version into VERSION on the host, and the Dockerfile COPYs it in.

    Returns:
        Version string like 'v1.2.3' (on tag) or 'v1.2.3-5-gabcdef-dirty' (commits after tag)
        or 'unknown' if neither source is available.
    """
    from backend.app.config.platform import frozen_app_version  # noqa: PLC0415 — backend.app.config imports this module

    frozen = frozen_app_version()
    if frozen:
        return frozen
    project_root = _project_root()
    if os.path.lexists(project_root / ".git"):
        described = _git_describe(project_root)
        if described:
            return described
    return _version_file(project_root) or "unknown"


def get_version_info() -> dict:
    """
    Get version information as a dict.

    Returns:
        Dict with version details.
    """
    version = get_git_version()
    return {
        "version": version,
        "is_dirty": version.endswith("-dirty"),
        "is_release": "-" not in version.replace("-dirty", ""),
    }
