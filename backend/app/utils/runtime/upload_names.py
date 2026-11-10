"""On-disk names of uploaded files (lot L4).

An upload is stored as ``{id}{suffix}`` with a ``{id}.json`` metadata sidecar beside it. The suffix comes from the
client's file name, so it cannot be trusted as is: a ``.json`` upload would be written onto its own sidecar, and an
absurdly long or odd suffix would end up in a path. :func:`stored_suffix` is the one place that decides the suffix
used on disk; every writer and reader of an upload's data file goes through it.
"""

import re
from pathlib import Path

# Longest client suffix kept, dot included. Longer or odd ones fall back to the default.
MAX_SUFFIX_LENGTH = 16
_SAFE_SUFFIX = re.compile(r"^\.[a-z0-9]+$")

# The metadata sidecar is ``{id}.json``: the data file of a ``.json`` upload gets this suffix instead, so the two
# never share a path and a ``*.json`` scan never meets a data file.
JSON_DATA_SUFFIX = ".json.dat"


def stored_suffix(filename: str, default: str) -> str:
    """The suffix under which the data file of an upload named ``filename`` is stored.

    ``default`` is used when the name has no usable suffix (none, not ``[a-z0-9]`` after the dot, longer than
    :data:`MAX_SUFFIX_LENGTH`). A ``.json`` suffix is mapped to :data:`JSON_DATA_SUFFIX`.
    """
    suffix = Path(filename).suffix.lower()
    if not suffix or len(suffix) > MAX_SUFFIX_LENGTH or not _SAFE_SUFFIX.match(suffix):
        return default
    if suffix == ".json":
        return JSON_DATA_SUFFIX
    return suffix
