"""How many terms one SQL condition may hold, and the chunks the bulk statements use under it (R13-SEC9-2, MF-SEC9a).

SQLite parses ``a OR b OR c …`` as a chain one level deeper per term and refuses a chain of a thousand
(«Expression tree is too large (maximum depth 1000)»): a bulk statement with one OR term per item failed from 1 000
items, a 500 to the user. Every such statement runs once per chunk of ``OR_TERMS_PER_QUERY`` terms instead, in the
same transaction, and its caller merges the rows.
"""

from collections.abc import Iterator, Sequence

#: Terms of one OR condition per statement: half of SQLite's limit, so an extra term or two never matters.
OR_TERMS_PER_QUERY = 500


def chunks[T](items: Sequence[T], size: int = OR_TERMS_PER_QUERY) -> Iterator[Sequence[T]]:
    """``items`` in consecutive slices of at most ``size``, in order; nothing for an empty sequence."""
    if size < 1:
        raise ValueError("size must be at least 1")
    for start in range(0, len(items), size):
        yield items[start : start + size]
