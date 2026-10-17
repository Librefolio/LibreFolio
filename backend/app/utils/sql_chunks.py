"""How many terms one SQL condition may hold, and the chunks the bulk statements use under it (R13-SEC9-2, MF-SEC9a).

SQLite parses ``a OR b OR c …`` as a chain one level deeper per term and refuses a chain of a thousand
(«Expression tree is too large (maximum depth 1000)»): a bulk statement with one OR term per item failed from 1 000
items, a 500 to the user. The statements that build such a chain from a request's items run once per chunk of
``OR_TERMS_PER_QUERY`` terms instead, in the same transaction, and their caller merges the rows: the FX rate reads of
``convert_bulk`` and of the fixed-period changes, the FX rate writes and their sync, the price deletion, the BRIM
candidate search and the PAC planner's WAC evidence.

``chunks()`` counts elements, and SQLite counts terms: SQLAlchemy writes a nested ``or_()`` out flat, into the same
chain, so each element of a chunk must be one term (an ``and_()`` inside is fine: it adds depth, not length).
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
