"""
Version utilities for LibreFolio.

Gets version information from git tags.
"""

import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_git_version() -> str:
    """
    Get version from git describe.

    Returns:
        Version string like 'v1.2.3' (on tag) or 'v1.2.3-5-gabcdef-dirty' (commits after tag)
        or 'unknown' if git is not available.

    Note:
        When HEAD is exactly on a tag, '-dirty' is suppressed even if the
        working tree has changes (build artifacts like openapi.json always
        regenerate and would cause a false '-dirty' on every startup).
    """
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        # First: get clean version without --dirty
        clean = subprocess.run(["git", "describe", "--tags", "--always"], capture_output=True, text=True, cwd=project_root, timeout=5)
        if clean.returncode != 0:
            return "unknown"

        version = clean.stdout.strip()

        # Normalize hash-only output (no tags exist)
        if not version.startswith("v") and not version.startswith("V"):
            version = f"v0.0.0-g{version}"

        # If we're on an exact tag (no -N-gHASH suffix), skip dirty check
        # because build artifacts (openapi.json) always cause false dirty.
        clean_base = version.replace("-dirty", "")
        on_exact_tag = "-" not in clean_base

        if not on_exact_tag:
            # Between tags: check dirty state honestly
            dirty = subprocess.run(["git", "describe", "--tags", "--always", "--dirty"], capture_output=True, text=True, cwd=project_root, timeout=5)
            if dirty.returncode == 0:
                version = dirty.stdout.strip()
                if not version.startswith("v") and not version.startswith("V"):
                    version = f"v0.0.0-g{version}"

        return version
    except Exception:
        pass
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
