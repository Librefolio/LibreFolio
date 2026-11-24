"""One sync per FX pair at a time (81 U35).

The registry of the pairs being synced in this process: a sync claims its pairs before it starts and releases them when it
ends, whatever the end. A request for a pair that is already claimed is refused (``FxSyncBusy``, the API answers 409 with
the pair and when its sync began); the weekly job takes the free pairs and leaves the busy ones to the sync running.

In-process on purpose: it holds across browser tabs and users of one server process. With several workers each has its
own registry; two syncs of one pair on two workers still write the same rows by upsert, as before this guard.

Claiming is synchronous (no ``await`` between the check and the claim), so on the event loop it is atomic.
"""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

# pair key (alphabetical slug) → when the running sync of that pair began (UTC)
_in_flight: dict[str, datetime] = {}


class FxSyncBusy(Exception):
    """A pair asked for is already being synced: ``busy`` maps each such pair to when its sync began."""

    def __init__(self, busy: dict[str, datetime]) -> None:
        super().__init__(f"FX sync already in progress for: {', '.join(busy)}")
        self.busy = busy


def sync_pair_key(slug: str) -> str:
    """The pair as the registry keeps it: upper case, alphabetical (``usd-eur`` → ``EUR-USD``)."""
    parts = [part.strip().upper() for part in slug.split("-")]
    return "-".join(sorted(parts)) if len(parts) == 2 else slug.strip().upper()


def _keys(pairs: Iterable[str]) -> list[str]:
    """The distinct keys of ``pairs``, in the order first met."""
    return list(dict.fromkeys(sync_pair_key(pair) for pair in pairs))


@contextmanager
def claim_pairs(pairs: Iterable[str]) -> Iterator[None]:
    """Claim every pair of ``pairs`` for the length of the block, or none: ``FxSyncBusy`` names the busy ones."""
    keys = _keys(pairs)
    busy = {key: _in_flight[key] for key in keys if key in _in_flight}
    if busy:
        raise FxSyncBusy(busy)
    now = datetime.now(UTC)
    for key in keys:
        _in_flight[key] = now
    try:
        yield
    finally:
        for key in keys:
            _in_flight.pop(key, None)


@contextmanager
def claim_free_pairs(pairs: Iterable[str]) -> Iterator[tuple[list[str], dict[str, datetime]]]:
    """Claim the pairs of ``pairs`` that are free; yield them and the busy ones (with when their sync began)."""
    keys = _keys(pairs)
    busy = {key: _in_flight[key] for key in keys if key in _in_flight}
    free = [key for key in keys if key not in busy]
    now = datetime.now(UTC)
    for key in free:
        _in_flight[key] = now
    try:
        yield free, busy
    finally:
        for key in free:
            _in_flight.pop(key, None)


def reset_for_tests() -> None:
    """Forget every claim (tests only)."""
    _in_flight.clear()
