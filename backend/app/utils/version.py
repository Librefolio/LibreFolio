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
        Version string like 'v1.2.3' (on tag) or 'v1.2.3-5-gabcdef' (commits after tag)
        or 'unknown' if git is not available.
    """
    try:
        # Find project root (3 levels up from this file)
        project_root = Path(__file__).parent.parent.parent.parent
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            cwd=project_root,
            timeout=5
            )
        if result.returncode == 0:
            version = result.stdout.strip()
            # If no tags exist, git describe --always returns just the hash
            # Prefix with v0.0.0- for consistency
            if not version.startswith('v') and not version.startswith('V'):
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
