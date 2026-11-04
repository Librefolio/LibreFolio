"""Keep a request-supplied path inside the folder it is meant to serve.

A path that comes from a request is joined to a fixed root only through ``confined_path``. It
resolves the candidate, symlinks included, and refuses anything that lands outside the root:
parent segments, an absolute path (``root / "/x"`` would drop the root) or an embedded NUL byte.
"""

from __future__ import annotations

from pathlib import Path


def confined_path(root: Path, relative: str) -> Path | None:
    """The resolved path that ``relative`` names inside ``root``, or ``None`` when it would leave it.

    The result may not exist: callers still check ``is_file()`` or ``is_dir()``. The root itself
    counts as inside, so an empty ``relative`` returns the resolved root.
    """
    try:
        base = root.resolve()
        candidate = (base / relative).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if not candidate.is_relative_to(base):
        return None
    return candidate
