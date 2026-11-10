"""Pauses after a refusal, in memory: how long a key must wait before a remote service is asked again.

One primitive for every pause the application takes after a remote service answers «too many requests» — a price
provider returning HTTP 429 (decision 34, release 1.3). The n-th refusal in a row pauses its key for
``base_seconds × 2^(n−1)``, capped at ``max_seconds``. A ``Retry-After`` the remote sent is a floor, honoured above the
cap up to ``hard_max_seconds``; on top comes a jitter of up to ``jitter`` of the wait, never past ``hard_max_seconds``.
A success forgets the key; a refusal that comes more than ``max_seconds`` after the previous pause ended starts over.
The refusals and answers of calls already in flight when a pause began neither escalate it nor lift it: only a later
``Retry-After`` extends it, so a burst of concurrent calls refused together pauses a key once.

When a pause ends, one caller at a time gets through (half-open): the others wait for its verdict, or for
``trial_seconds`` if none comes, so concurrent callers do not turn one expiry into several refusals.

The clock is the wall clock, not a monotonic one: a suspended virtual machine (``suspend`` on Fly) may not count the
time it spent suspended in ``time.monotonic()``, and a pause begun before a suspension must have run out when the
instance wakes up. A clock that goes back never makes a pause longer than the wait recorded for it.

The pauses live in this process: with N worker processes each one learns a pause by itself. The number of keys is
bounded (``max_keys``): a new key beyond it evicts the least recently used one. Clock and random source are
injectable, so a test moves time instead of waiting for it. Thread-safe.
"""

from __future__ import annotations

import math
import random
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime

#: Doubling reaches any cap long before this; the bound only keeps ``2 ** n`` finite after many refusals in a row.
_MAX_DOUBLINGS = 60


class RateLimitedError(Exception):
    """A remote refused for too many requests: ``retry_after`` is the wait it asked for, ``scope`` narrows the pause.

    A marker, combined with the exception of a domain (``AssetRateLimitedError(AssetSourceError, RateLimitedError)``),
    so that a caller recognises a refusal whatever the domain. ``retry_after`` is in seconds, None when the remote did
    not say; ``scope`` is the part of a provider the refusal is about (the host of a scraped site), None for all of it.
    """

    def __init__(self, *args: object, retry_after: float | None = None, scope: str | None = None) -> None:
        super().__init__(*args)
        self.retry_after = retry_after
        self.scope = scope


def retry_after_seconds(value: str | None, *, now: float | None = None) -> float | None:
    """The wait a ``Retry-After`` header asks for, in seconds; None when it says nothing usable.

    Both forms of RFC 9110: a number of seconds (decimals tolerated) or an HTTP date, measured from ``now`` (the wall
    clock by default); a date already past is 0. None for an absent, blank, negative, infinite or unreadable value.
    """
    if value is None or not value.strip():
        return None
    text = value.strip()
    try:
        seconds = float(text)
    except ValueError:
        pass
    else:
        return seconds if math.isfinite(seconds) and seconds >= 0 else None
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    reference = time.time() if now is None else now
    return max(0.0, when.timestamp() - reference)


@dataclass(frozen=True)
class CooldownState:
    """One key as ``snapshot()`` sees it: refusals in a row, seconds of pause left, whether a trial call is out."""

    key: Hashable
    refusals: int
    remaining: float
    trial_in_flight: bool


@dataclass
class _Pause:
    refusals: int
    wait: float
    until: float
    trial_until: float | None = None


def _check_bounds(base_seconds: float, max_seconds: float) -> None:
    if base_seconds <= 0:
        raise ValueError("base_seconds must be positive")
    if max_seconds < base_seconds:
        raise ValueError("max_seconds must be at least base_seconds")


class Cooldowns:
    """Pauses per key after refusals: ``check`` before a call; ``refused``, ``succeeded`` or ``released`` after it."""

    def __init__(
        self,
        base_seconds: float,
        max_seconds: float,
        *,
        hard_max_seconds: float = 86_400.0,
        jitter: float = 0.1,
        trial_seconds: float = 60.0,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.time,
        rng: Callable[[], float] = random.random,
    ) -> None:
        _check_bounds(base_seconds, max_seconds)
        if hard_max_seconds < max_seconds:
            raise ValueError("hard_max_seconds must be at least max_seconds")
        if not 0 <= jitter <= 1:
            raise ValueError("jitter must be between 0 and 1")
        if trial_seconds <= 0:
            raise ValueError("trial_seconds must be positive")
        if max_keys < 1:
            raise ValueError("max_keys must be at least 1")
        self._base = float(base_seconds)
        self._max = float(max_seconds)
        self._hard_max = float(hard_max_seconds)
        self._jitter = float(jitter)
        self._trial = float(trial_seconds)
        self._max_keys = max_keys
        self._clock = clock
        self._rng = rng
        self._pauses: OrderedDict[Hashable, _Pause] = OrderedDict()
        self._lock = threading.Lock()

    def __len__(self) -> int:
        with self._lock:
            return len(self._pauses)

    @staticmethod
    def _left(pause: _Pause, now: float) -> float:
        """Seconds of pause left; a clock that went back never stretches it past the recorded wait."""
        return min(pause.until - now, pause.wait)

    def _trial_left(self, pause: _Pause, now: float) -> float:
        if pause.trial_until is None:
            return 0.0
        return min(pause.trial_until - now, self._trial)

    def check(self, key: Hashable) -> float:
        """0 when a call may go now, else the seconds to wait. When a pause ends, one caller at a time gets 0.

        That caller holds the trial: until it reports ``refused``, ``succeeded`` or ``released``, or for
        ``trial_seconds`` at most, the others are told to wait for it.
        """
        with self._lock:
            pause = self._pauses.get(key)
            if pause is None:
                return 0.0
            self._pauses.move_to_end(key)
            now = self._clock()
            left = self._left(pause, now)
            if left > 0:
                return left
            trial_left = self._trial_left(pause, now)
            if trial_left > 0:
                return trial_left
            pause.trial_until = now + self._trial
            return 0.0

    def refused(self, key: Hashable, retry_after: float | None = None, *, base_seconds: float | None = None, max_seconds: float | None = None) -> float:
        """Record a refusal of ``key`` and return the seconds of pause it leaves.

        A refusal that arrives while the key is already paused came from a call in flight when the pause began: it
        counts no new refusal and never shortens the pause, and only a ``Retry-After`` ending later extends it. So a
        burst of concurrent calls refused together pauses the key once, not once per call.

        ``base_seconds`` and ``max_seconds`` replace the instance's for this call only, so a caller applies settings
        read at call time.
        """
        base = self._base if base_seconds is None else float(base_seconds)
        cap = self._max if max_seconds is None else float(max_seconds)
        _check_bounds(base, cap)
        if cap > self._hard_max:
            raise ValueError("max_seconds must not exceed hard_max_seconds")
        floor = min(float(retry_after), self._hard_max) if retry_after is not None and math.isfinite(retry_after) and retry_after > 0 else 0.0
        with self._lock:
            now = self._clock()
            previous = self._pauses.get(key)
            if previous is not None:
                left = self._left(previous, now)
                if left > 0:
                    if floor > left:
                        previous.until = now + floor
                        previous.wait = floor
                        left = floor
                    self._pauses.move_to_end(key)
                    return left
            refusals = previous.refusals if previous is not None and now - previous.until <= cap else 0
            refusals += 1
            step = min(base * 2.0 ** min(refusals - 1, _MAX_DOUBLINGS), cap)
            wait = min(max(step, floor) * (1.0 + self._jitter * self._rng()), self._hard_max)
            self._pauses[key] = _Pause(refusals=refusals, wait=wait, until=now + wait)
            self._pauses.move_to_end(key)
            while len(self._pauses) > self._max_keys:
                self._pauses.popitem(last=False)
            return wait

    def succeeded(self, key: Hashable) -> int:
        """Forget ``key`` after an answer; return the refusals in a row it had, 0 when there was nothing to forget.

        While a pause is running an answer changes nothing: it came from a call in flight when the pause began, and
        does not show that the remote accepts calls again.
        """
        with self._lock:
            pause = self._pauses.get(key)
            if pause is None or self._left(pause, self._clock()) > 0:
                return 0
            del self._pauses[key]
            return pause.refusals

    def released(self, key: Hashable) -> None:
        """Free the trial of ``key`` after an end with no verdict (another error, a timeout): the next caller tries."""
        with self._lock:
            pause = self._pauses.get(key)
            if pause is not None:
                pause.trial_until = None

    def snapshot(self) -> tuple[CooldownState, ...]:
        """Every key tracked, least recently used first."""
        with self._lock:
            now = self._clock()
            return tuple(CooldownState(key=key, refusals=pause.refusals, remaining=max(0.0, self._left(pause, now)), trial_in_flight=self._trial_left(pause, now) > 0) for key, pause in self._pauses.items())

    def reset(self, key: Hashable) -> None:
        """Forget one key. Used by the tests only (N58 exception): the one public way to leave the process's instance clean after a refusal — ``succeeded`` keeps a running pause, ``released`` only frees the trial."""
        with self._lock:
            self._pauses.pop(key, None)
