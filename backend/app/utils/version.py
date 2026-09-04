"""
Version utilities for LibreFolio.

Gets version information from git tags, or from a pre-generated VERSION file
when git is not available (e.g. inside the Docker image, which has no .git/).
"""

import subprocess
from functools import lru_cache
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def get_git_version() -> str:
    """
    Get version from a pre-generated VERSION file, falling back to git describe.

    The Docker image has no .git/ (by design, to keep it small), so `git describe`
    can never succeed at container runtime. `./dev.py docker build`/`rebuild`
    freezes the version into a VERSION file on the host (where .git/ exists)
    before the image is built, and the Dockerfile COPYs it in. Local dev has no
    VERSION file, so it always falls through to `git describe` as before.

    Returns:
        Version string like 'v1.2.3' (on tag) or 'v1.2.3-5-gabcdef-dirty' (commits after tag)
        or 'unknown' if neither source is available.
    """
    project_root = Path(__file__).parent.parent.parent.parent

    version_file = project_root / "VERSION"
    try:
        if version_file.exists():
            content = version_file.read_text().strip()
            if content:
                return content
    except Exception:
        logger.debug("version_file_read_failed", path=str(version_file), exc_info=True)

    try:
        result = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], capture_output=True, text=True, cwd=project_root, timeout=5)
        if result.returncode != 0:
            return "unknown"

        version = result.stdout.strip()

        # Normalize hash-only output (no tags exist)
        if not version.startswith("v") and not version.startswith("V"):
            version = f"v0.0.0-g{version}"

        return version
    except Exception:
        logger.debug("git_describe_failed", cwd=str(project_root), exc_info=True)
    return "unknown"


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
