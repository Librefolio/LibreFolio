"""Sliding-window rate limits, in memory: how many hits a key had in the last ``window_seconds``.

One primitive for every limit of the application that counts events in a moving window — the hourly budget of the
emails an instance sends, the attempts of a login or of a «forgot password» per address and per user name. A hit
counts while ``clock() - hit_time < window_seconds``; a refused hit is not recorded, so a caller that keeps knocking
does not push its own unlock further away.

The counts live in this process: with N worker processes a limit is N times the configured one. The number of keys is
bounded (``max_keys``): a new key beyond it evicts, among the ``eviction_scan`` least recently used, the first that is
not full — a full key is the one refusing, and forgetting it would hand its caller a fresh allowance (decision N70) —,
and the least recently used one when they are all full. The scan is bounded so that a spray of full keys cannot make
every hit walk the whole map under the lock. The clock is injectable, so a test moves time instead of waiting for it.
Thread-safe.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass

#: Stands for «no key yet» where ``None`` is a key like any other.
_NO_KEY = object()


@dataclass(frozen=True)
class RateDecision:
    """The answer for one key: whether a hit is allowed now, how many more fit, and how long until the next one fits."""

    allowed: bool
    remaining: int
    retry_after: float


class SlidingWindowLimiter:
    """At most ``limit`` hits per key in any ``window_seconds``; a call may pass its own limit."""

    def __init__(self, limit: int, window_seconds: float, *, max_keys: int = 10_000, eviction_scan: int = 32, clock: Callable[[], float] = time.monotonic) -> None:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_keys < 1:
            raise ValueError("max_keys must be at least 1")
        if eviction_scan < 1:
            raise ValueError("eviction_scan must be at least 1")
        self._limit = limit
        self._window = float(window_seconds)
        self._max_keys = max_keys
        self._eviction_scan = eviction_scan
        self._clock = clock
        self._hits: OrderedDict[Hashable, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def window_seconds(self) -> float:
        return self._window

    def __len__(self) -> int:
        with self._lock:
            return len(self._hits)

    def _resolve_limit(self, limit: int | None) -> int:
        if limit is None:
            return self._limit
        if limit < 1:
            raise ValueError("limit must be at least 1")
        return limit

    def _live(self, key: Hashable, now: float) -> deque[float] | None:
        """The hits of ``key`` still in the window, oldest first, or None. The key becomes the most recently used.

        Lock held. A key whose hits all expired is forgotten.
        """
        hits = self._hits.get(key)
        if hits is None:
            return None
        while hits and now - hits[0] >= self._window:
            hits.popleft()
        if not hits:
            del self._hits[key]
            return None
        self._hits.move_to_end(key)
        return hits

    def _evict_one(self, keep: Hashable, now: float) -> None:
        """Forget one key to make room for ``keep``, the key being added, which is never the one. Lock held.

        Among the ``eviction_scan`` least recently used keys, the first that is not full: fewer live hits than the
        limiter's own ``limit`` (expired hits do not count, a per-call limit does not change it). When those are all
        full, the least recently used key.
        """
        oldest: object = _NO_KEY
        scanned = 0
        for candidate, hits in self._hits.items():
            if candidate == keep:
                continue
            if oldest is _NO_KEY:
                oldest = candidate
            if scanned >= self._eviction_scan:
                break
            scanned += 1
            if sum(1 for hit_time in hits if now - hit_time < self._window) < self._limit:
                # Deleted and left at once: the iteration does not go on over the changed map
                del self._hits[candidate]
                return
        if oldest is not _NO_KEY:
            del self._hits[oldest]

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
                hits = deque()
                self._hits[key] = hits
                while len(self._hits) > self._max_keys:
                    self._evict_one(key, now)
            hits.append(now)
            return RateDecision(allowed=True, remaining=effective - len(hits), retry_after=0.0)

    def count(self, key: Hashable = None) -> int:
        """How many hits of ``key`` are in the window now."""
        with self._lock:
            return len(self._live(key, self._clock()) or ())

    def reset(self, key: Hashable = None) -> None:
        """Forget the hits of one key."""
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        """Forget every key."""
        with self._lock:
            self._hits.clear()
