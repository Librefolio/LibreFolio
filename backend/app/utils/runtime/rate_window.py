"""Sliding-window rate limits, in memory: how many hits a key had in the last ``window_seconds``.

One primitive for every limit of the application that counts events in a moving window — the hourly budget of the
emails an instance sends, the attempts of a login or of a «forgot password» per address and per user name. A hit
counts while ``clock() - hit_time < window_seconds``; a refused hit is not recorded, so a caller that keeps knocking
does not push its own unlock further away.

The counts live in this process: with N worker processes a limit is N times the configured one. The number of keys is
bounded (``max_keys``): a new key beyond it evicts the least recently used one. The clock is injectable, so a test
moves time instead of waiting for it. Thread-safe.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict, deque
from collections.abc import Callable, Hashable, Sequence
from dataclasses import dataclass


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
                    self._hits.popitem(last=False)
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
