"""Pacing between calls, in memory: at least ``interval_seconds`` between two calls of one key, across threads.

One primitive for the plugins that must space their own calls to a site (plan 68, C5; the developer's round-30 rule:
the plugin paces its own calls, the core declares no site and no pause). An enricher holds one ``Pacer`` at module
level — the registry builds a new plugin instance for every call, so a pacer on ``self`` would never be shared — and
calls ``wait()`` right before each call to its site. A user's «Aggiorna» and the weekly read, each in its own worker
thread, then never reach the site closer than the interval. Each plugin picks its own interval.

The counting is ``SlidingWindowLimiter`` with a limit of one call per window of ``interval_seconds``
(``utils/runtime/rate_window.py``): it decides, under its lock, whether a key may call now and how long it must wait
otherwise. Only the wait is this module's: ``wait()`` sleeps that long and asks again, so two threads woken together
never both pass.

``wait()`` blocks its thread: call it from the worker thread a plugin's method runs in (the core runs every enricher
call away from the event loop), never from the event loop itself. The pacing lives in this process: with N worker
processes each one paces its own calls. Clock and sleep are injectable, so a test moves time instead of waiting for it.
Thread-safe.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Hashable

from backend.app.utils.runtime.rate_window import SlidingWindowLimiter


class Pacer:
    """At least ``interval_seconds`` between two calls of one key: ``wait(key)`` right before each call."""

    def __init__(
        self,
        interval_seconds: float,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._interval = float(interval_seconds)
        self._limiter = SlidingWindowLimiter(1, interval_seconds, max_keys=max_keys, clock=clock)
        self._sleep = sleep

    @property
    def interval_seconds(self) -> float:
        return self._interval

    def wait(self, key: Hashable = None) -> float:
        """Block until ``key`` may call, and count the call; the seconds waited (0 when it could call at once)."""
        waited = 0.0
        while True:
            decision = self._limiter.hit(key)
            if decision.allowed:
                return waited
            self._sleep(decision.retry_after)
            waited += decision.retry_after
