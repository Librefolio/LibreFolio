"""
Pacing between calls (plan 68, C5): ``backend/app/utils/runtime/pacing.py``.

A ``Pacer`` keeps at least ``interval_seconds`` between two calls of one key, across threads: an enricher holds one at
module level and waits on it before every call to its site, so a user's «Aggiorna» and the weekly read, each in its own
worker thread, never call the site closer than the interval (the round-30 rule: the plugin paces its own calls). It
counts with ``SlidingWindowLimiter`` (limit 1, window = the interval): only the wait is its own.

Pinned, with an injectable clock and sleep (no real waiting):
- the first call of a key does not wait; a second one inside the interval waits what is left; one after it does not;
- keys are independent; two pacers (two plugins) never wait for each other;
- two threads calling at once are spaced by at least the interval;
- the interval must be positive.
"""

import threading

import pytest

from backend.app.utils.runtime.pacing import Pacer


class FakeTime:
    """A clock that only moves when someone sleeps: shared by threads, guarded by a lock."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []
        self._lock = threading.Lock()

    def clock(self) -> float:
        with self._lock:
            return self.now

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.slept.append(seconds)
            self.now += seconds

    def advance(self, seconds: float) -> None:
        with self._lock:
            self.now += seconds


def _pacer(fake: FakeTime, interval: float = 2.0) -> Pacer:
    return Pacer(interval, clock=fake.clock, sleep=fake.sleep)


def test_first_call_does_not_wait():
    fake = FakeTime()
    assert _pacer(fake).wait() == 0
    assert fake.slept == []


def test_a_second_call_inside_the_interval_waits_what_is_left():
    fake = FakeTime()
    pacer = _pacer(fake, 2.0)
    pacer.wait()
    fake.advance(0.5)
    waited = pacer.wait()
    assert waited == pytest.approx(1.5)
    assert sum(fake.slept) == pytest.approx(1.5)


def test_a_call_after_the_interval_does_not_wait():
    fake = FakeTime()
    pacer = _pacer(fake, 2.0)
    pacer.wait()
    fake.advance(2.0)
    assert pacer.wait() == 0


def test_keys_are_independent():
    fake = FakeTime()
    pacer = _pacer(fake)
    pacer.wait("site-a")
    assert pacer.wait("site-b") == 0
    assert pacer.wait("site-a") > 0


def test_two_pacers_never_wait_for_each_other():
    """Two plugins, two module-level pacers: one's call does not delay the other's."""
    fake = FakeTime()
    first, second = _pacer(fake), _pacer(fake)
    first.wait()
    assert second.wait() == 0


def test_two_threads_at_once_are_spaced_by_the_interval():
    """«Aggiorna» and the weekly read, each in its worker thread: their calls are at least the interval apart."""
    fake = FakeTime()
    pacer = _pacer(fake, 2.0)
    start = threading.Barrier(3)
    calls: list[float] = []
    lock = threading.Lock()

    def worker() -> None:
        start.wait()
        for _ in range(3):
            pacer.wait()
            with lock:
                calls.append(fake.clock())

    threads = [threading.Thread(target=worker) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads), "a worker is stuck"
    calls.sort()
    assert len(calls) == 9
    gaps = [later - earlier for earlier, later in zip(calls, calls[1:], strict=False)]
    assert all(gap >= 2.0 - 1e-9 for gap in gaps), f"calls closer than the interval: {gaps}"


@pytest.mark.parametrize("interval", [0, -1.0])
def test_the_interval_must_be_positive(interval):
    with pytest.raises(ValueError):
        Pacer(interval)
