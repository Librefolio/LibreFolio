"""Helpers for the ``identifier_other`` soft-identifier list.

``Asset.identifier_other`` holds a JSON list of "other" identifiers: technical codes
that have no dedicated column (e.g. a Borsa Italiana fund code) plus *soft* broker
labels extracted from import reports (e.g. ``"BTP 1/12/2026 1.25%"``). The list is
**additive**: several labels for the same instrument coexist instead of overwriting
each other, and any of them can later match an existing asset during BRIM import.

These helpers keep the list well-formed everywhere it is produced (DB model + Pydantic
schemas + BRIM import), so callers may pass a bare string, a list, or ``None`` and
always get back a clean, de-duplicated ``list[str]`` (or ``None`` when empty).
"""

from typing import Any, List, Optional


def normalize_other_identifiers(value: Any) -> Optional[List[str]]:
    """Coerce any input into a clean list of soft identifiers, or ``None`` when empty.

    Accepts a bare string (wrapped into a single-element list), an iterable of values,
    or ``None``. Each element is stringified, whitespace-trimmed and dropped when empty;
    duplicates are removed case-insensitively while preserving first-seen order and the
    original casing. Returns ``None`` (not ``[]``) when nothing remains, to keep NULLs
    clean in the database.
    """
    if value is None:
        return None
    if isinstance(value, str):
        items: List[Any] = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]

    out: List[str] = []
    seen: set[str] = set()
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out or None


def merge_other_identifiers(existing: Any, new: Any) -> Optional[List[str]]:
    """Additively merge two soft-identifier inputs, de-duplicated, existing first.

    Used when new labels for an already-known asset must be *added* rather than
    replace the current ones (the additive import semantics).
    """
    base = normalize_other_identifiers(existing) or []
    incoming = normalize_other_identifiers(new) or []
    return normalize_other_identifiers([*base, *incoming])
