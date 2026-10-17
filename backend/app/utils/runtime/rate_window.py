"""Sliding-window rate limits, in memory: how many hits a key had in the last ``window_seconds``.

One primitive for every limit of the application that counts events in a moving window — the hourly budget of the
emails an instance sends, the attempts of a login or of a «forgot password» per address and per user name. A hit
counts while ``clock() - hit_time < window_seconds``; a refused hit is not recorded, so a caller that keeps knocking
does not push its own unlock further away.

The counts live in this process: with N worker processes a limit is N times the configured one. The number of keys is
bounded (``max_keys``): a new key beyond it evicts the key with the fewest hits still in the window, and among those
the one used or regrouped longest ago: a key goes to the end of its group when it is peeked, hit or counted, and when a
hit of its leaves the window (lot E-14). A key sprayed to make room holds one hit, so a spray never frees a key that holds more: not
a locked one, nor one a hit short of its limit, whose caller would otherwise get its count back for the price of the
spray. To free a key with n hits, every other key must hold n hits too. Expiry is exact: a heap holds, for each key,
when its oldest hit leaves the window, so a key whose hits left keeps no protection, read or not. Nothing is searched,
so a new key costs the same however many keys there are. The clock is injectable, so a test moves time instead of
waiting for it. Thread-safe.
"""

from __future__ import annotations

import heapq
import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass

#: How many stale entries the expiry heap may hold beyond one per key before it is rebuilt from the keys.
_EXPIRY_SLACK = 64


@dataclass(frozen=True)
class RateDecision:
    """The answer for one key: whether a hit is allowed now, how many more fit, and how long until the next one fits."""

    allowed: bool
    remaining: int
    retry_after: float


class SlidingWindowLimiter:
    """At most ``limit`` hits per key in any ``window_seconds``; a call may pass its own limit."""

    def __init__(self, limit: int, window_seconds: float, *, max_keys: int = 10_000, clock: Callable[[], float] = time.monotonic) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_keys < 1:
            raise ValueError("max_keys must be at least 1")
        self._limit = limit
        self._window = float(window_seconds)
        self._max_keys = max_keys
        self._clock = clock
        # The hits of each key still in the window, oldest first: a key without one is not here.
        self._hits: dict[Hashable, deque[float]] = {}
        # The keys grouped by how many hits they hold, each group in the order its keys were last used or regrouped, oldest first.
        self._by_count: dict[int, OrderedDict[Hashable, None]] = {}
        # (oldest hit, serial, key) per key; an entry whose serial is not the key's in _serials is stale and skipped
        self._expiry: list[tuple[float, int, Hashable]] = []
        self._serials: dict[Hashable, int] = {}
        self._next_serial = 0
        self._lock = threading.Lock()

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window_seconds(self) -> float:
        return self._window

    def __len__(self) -> int:
        """The keys holding a hit still in the window."""
        with self._lock:
            self._expire(self._clock())
            return len(self._hits)

    def _resolve_limit(self, limit: int | None) -> int:
        if limit is None:
            return self._limit
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return limit

    def _regroup(self, key: Hashable, old: int, new: int) -> None:
        """Move ``key`` from the group of ``old`` hits to the end of the group of ``new``; 0 is no group. Lock held."""
        if old:
            group = self._by_count[old]
            del group[key]
            if not group:
                del self._by_count[old]
        if new:
            self._by_count.setdefault(new, OrderedDict())[key] = None

    def _schedule(self, key: Hashable, oldest: float) -> None:
        """Note when the oldest hit of ``key`` leaves the window, replacing the key's earlier entry. Lock held."""
        serial = self._next_serial
        self._next_serial += 1
        self._serials[key] = serial
        heapq.heappush(self._expiry, (oldest, serial, key))

    def _compact(self) -> None:
        """Rebuild the expiry heap from the keys once it holds more than two entries per key and a slack: the stale
        entries left by forgotten keys never pile up, however many keys come and go. Lock held."""
        if len(self._expiry) > 2 * len(self._hits) + _EXPIRY_SLACK:
            self._expiry = [(hits[0], self._serials[key], key) for key, hits in self._hits.items()]
            heapq.heapify(self._expiry)

    def _forget(self, key: Hashable) -> None:
        """Drop ``key`` and its hits; its heap entry becomes stale. Lock held."""
        self._regroup(key, len(self._hits.pop(key)), 0)
        del self._serials[key]
        self._compact()

    def _expire(self, now: float) -> None:
        """Take out of every key the hits that left the window, regrouping each key by what it still holds. Lock held."""
        while self._expiry and now - self._expiry[0][0] >= self._window:
            _, serial, key = heapq.heappop(self._expiry)
            if self._serials.get(key) != serial:
                continue
            hits = self._hits[key]
            held = len(hits)
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            if hits:
                self._regroup(key, held, len(hits))
                self._schedule(key, hits[0])
            else:
                self._regroup(key, held, 0)
                del self._hits[key]
                del self._serials[key]
        self._compact()

    def _live(self, key: Hashable, now: float) -> deque[float] | None:
        """The hits of ``key`` still in the window, oldest first, or None. The key becomes the most recently used of
        its group. Lock held."""
        self._expire(now)
        hits = self._hits.get(key)
        if hits is not None:
            self._by_count[len(hits)].move_to_end(key)
        return hits

    def _evict_one(self, keep: Hashable) -> bool:
        """Forget the key with the fewest hits, the one used or regrouped longest ago among them, never ``keep``; False when there is
        no other key. Lock held."""
        for count in sorted(self._by_count):
            for key in self._by_count[count]:
                if key != keep:
                    # Forgotten and left at once: the iteration does not go on over the changed group
                    self._forget(key)
                    return True
        return False

    def _decide(self, hits: Sequence[float], limit: int, now: float) -> RateDecision:
        count = len(hits)
        if count < limit:
            return RateDecision(allowed=True, remaining=limit - count, retry_after=0.0)
        return RateDecision(allowed=False, remaining=0, retry_after=hits[count - limit] + self._window - now)

    def peek(self, key: Hashable = None, *, limit: int | None = None) -> RateDecision:
        """The decision a hit would get now, without counting it."""
        effective = self._resolve_limit(limit)
        with self._lock:
            now = self._clock()
            return self._decide(self._live(key, now) or (), effective, now)

    def hit(self, key: Hashable = None, *, limit: int | None = None) -> RateDecision:
        """Count one hit for ``key`` when it is allowed; a refused hit is not counted."""
        effective = self._resolve_limit(limit)
        with self._lock:
            now = self._clock()
            hits = self._live(key, now)
            decision = self._decide(hits or (), effective, now)
            if not decision.allowed:
                return decision
            if hits is None:
                hits = deque((now,))
                self._hits[key] = hits
                self._regroup(key, 0, 1)
                self._schedule(key, now)
                while len(self._hits) > self._max_keys and self._evict_one(key):
                    pass
            else:
                self._regroup(key, len(hits), len(hits) + 1)
                hits.append(now)
            return RateDecision(allowed=True, remaining=effective - len(hits), retry_after=0.0)

    def count(self, key: Hashable = None) -> int:
        """How many hits of ``key`` are in the window now."""
        with self._lock:
            return len(self._live(key, self._clock()) or ())

    def reset(self, key: Hashable = None) -> None:
        """Forget the hits of one key."""
        with self._lock:
            if key in self._hits:
                self._forget(key)

    def clear(self) -> None:
        """Forget every key."""
        with self._lock:
            self._hits.clear()
            self._by_count.clear()
            self._expiry.clear()
            self._serials.clear()
