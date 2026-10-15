"""``backend.app.utils.runtime.rate_window``: the one sliding-window limiter of release 1.3 (plan phase01Email §3.2, decision D-E12, lot E1).

The hourly sending budget of the e-mail (workstream E) and the login limits of the accounts (A8) count with the same
primitive: hits of a key inside a sliding window, in memory, with a bounded number of keys and an injectable clock. The
contract pinned here:

1. ``RateDecision(allowed, remaining, retry_after)``, frozen.
2. ``SlidingWindowLimiter(limit, window_seconds, *, max_keys=10_000, clock=time.monotonic)``: ``limit < 1``,
   ``window_seconds <= 0`` or ``max_keys < 1`` is a ``ValueError``; ``limit`` and ``window_seconds`` are properties.
3. The window: a hit at ``t`` counts while ``clock() - t < window_seconds``; at exactly ``window_seconds`` later it no
   longer does.
4. ``peek`` decides and never counts. Allowed while ``count < L``, with ``remaining = L - count`` and ``retry_after``
   0; refused with ``remaining`` 0 and ``retry_after = ts[count - L] + window - now`` — the wait until enough hits leave.
5. ``hit`` decides the same way and records the hit only when allowed, then ``remaining = L - (count + 1)``. A refused
   hit records nothing: hammering a refused key never pushes its wait further.
6. A per-call ``limit`` replaces the default for that call only (``< 1`` is a ``ValueError``); lowered below the count,
   the wait is for enough hits to expire.
7. Keys are independent and ``None`` is a key like any other; ``count``, ``reset`` (one key), ``clear`` (every key)
   and ``len`` (the keys tracked).
8. At most ``max_keys`` keys: a new key beyond them evicts the least recently used one — used meaning peeked, hit or
   counted — and its hits are forgotten with it.
9. Thread-safe: threads hitting one key with a limit of N get exactly N hits allowed, each ``remaining`` value once.

Every test drives an injected fake clock: nothing waits for time to pass. Pure: no database, no server, no network.

Red until ``backend/app/utils/runtime/rate_window.py`` exists: the module does not import.
"""

from __future__ import annotations

import dataclasses
import inspect
import os
import sys
import threading
import time

import pytest

from backend.app.utils.runtime.rate_window import RateDecision, SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

#: Written out: the e-mail lot's modules all start from a lane without inherited SMTP variables.
SMTP_PREFIX = "LIBREFOLIO_SMTP_"
WINDOW = 60.0
START = 1_000.0


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


@pytest.fixture(autouse=True)
def _no_inherited_smtp_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` the lane inherited is removed, as in every module of the e-mail lot: the limiter reads none, and must not start to unnoticed."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


# =============================================================================
# 1-2. THE TYPES
# =============================================================================


def test_rate_decision_is_a_frozen_dataclass() -> None:
    """RWL-001 — contract 1: three fields in order, compared by value, never edited."""
    print_section("RWL-001: RateDecision")

    assert [field.name for field in dataclasses.fields(RateDecision)] == ["allowed", "remaining", "retry_after"]
    decision = RateDecision(allowed=False, remaining=0, retry_after=12.5)
    assert decision == RateDecision(False, 0, 12.5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        decision.allowed = True  # type: ignore[misc]
    print_success("frozen (allowed, remaining, retry_after)")


@pytest.mark.parametrize(
    ("arguments", "keywords"),
    [
        pytest.param((0, WINDOW), {}, id="limit-0"),
        pytest.param((-1, WINDOW), {}, id="limit-negative"),
        pytest.param((1, 0), {}, id="window-0"),
        pytest.param((1, -1.0), {}, id="window-negative"),
        pytest.param((1, WINDOW), {"max_keys": 0}, id="max-keys-0"),
    ],
)
def test_the_limiter_refuses_a_meaningless_configuration(arguments: tuple, keywords: dict) -> None:
    """RWL-002 — contract 2: no limit below 1, no window of zero or less, no room for less than one key."""
    print_section(f"RWL-002: SlidingWindowLimiter{arguments} {keywords}")

    with pytest.raises(ValueError):
        SlidingWindowLimiter(*arguments, **keywords)
    print_success("ValueError")


def test_the_limiter_exposes_its_limit_and_window_and_its_defaults() -> None:
    """RWL-003 — contract 2: ``limit`` and ``window_seconds`` as given; ``max_keys`` 10 000 and ``clock`` ``time.monotonic`` by default, keyword-only. The real clock works without anybody moving it: two hits in an hour, the second refused for at most the hour."""
    print_section("RWL-003: properties and defaults")

    limiter = SlidingWindowLimiter(3, 3600.0)
    assert (limiter.limit, limiter.window_seconds) == (3, 3600.0)
    parameters = inspect.signature(SlidingWindowLimiter).parameters
    assert (parameters["max_keys"].default, parameters["max_keys"].kind) == (10_000, inspect.Parameter.KEYWORD_ONLY)
    assert (parameters["clock"].default, parameters["clock"].kind) == (time.monotonic, inspect.Parameter.KEYWORD_ONLY)

    real = SlidingWindowLimiter(1, 3600.0)
    assert real.hit("k").allowed
    refused = real.hit("k")
    assert not refused.allowed and 0.0 < refused.retry_after <= 3600.0
    print_success("limit 3, window 3600, max_keys 10 000, clock time.monotonic")


# =============================================================================
# 3-5. THE WINDOW, PEEK AND HIT
# =============================================================================


def test_a_fresh_key_is_allowed_with_the_whole_limit(clock: FakeClock) -> None:
    """RWL-004 — contract 4: nothing counted yet — allowed, ``remaining`` the limit, no wait."""
    print_section("RWL-004: a fresh key")
    limiter = SlidingWindowLimiter(3, WINDOW, clock=clock)

    assert limiter.peek("k") == RateDecision(True, 3, 0.0)
    assert limiter.count("k") == 0
    print_success("allowed, 3 remaining")


def test_hits_are_allowed_up_to_the_limit_then_refused_until_the_oldest_leaves(clock: FakeClock) -> None:
    """RWL-005 — contracts 4 and 5: three hits at 1000, 1001, 1002 leave 2, 1, 0; the fourth at 1003 is refused for 57 s — until the hit of 1000 leaves at 1060 — and is not counted."""
    print_section("RWL-005: up to the limit, then refused")
    limiter = SlidingWindowLimiter(3, WINDOW, clock=clock)

    decisions = []
    for moment in (1_000.0, 1_001.0, 1_002.0):
        clock.now = moment
        decisions.append(limiter.hit("k"))
    clock.now = 1_003.0
    refused = limiter.hit("k")

    assert decisions == [RateDecision(True, 2, 0.0), RateDecision(True, 1, 0.0), RateDecision(True, 0, 0.0)]
    assert refused == RateDecision(False, 0, 57.0)
    assert limiter.count("k") == 3
    print_success("2, 1, 0 remaining, then refused for 57 s")


def test_a_refused_hit_records_nothing(clock: FakeClock) -> None:
    """RWL-006 — contract 5: three refused hits later, the window still holds the two allowed ones only, so the key opens again as soon as the first of them leaves — a recorded refusal would have kept it shut."""
    print_section("RWL-006: a refused hit records nothing")
    limiter = SlidingWindowLimiter(2, WINDOW, clock=clock)
    clock.now = 1_000.0
    limiter.hit("k")
    clock.now = 1_010.0
    limiter.hit("k")

    for moment in (1_020.0, 1_030.0, 1_040.0):
        clock.now = moment
        assert not limiter.hit("k").allowed
    assert limiter.count("k") == 2

    clock.now = 1_060.0
    assert limiter.hit("k") == RateDecision(True, 0, 0.0)
    print_success("refusals not counted: open again at 1060")


def test_a_hit_counts_until_exactly_one_window_later(clock: FakeClock) -> None:
    """RWL-007 — contract 3: a hit at 1000 in a 60 s window still counts at 1059.5 (refused for 0.5 s) and no longer at 1060.0."""
    print_section("RWL-007: the edge of the window")
    limiter = SlidingWindowLimiter(1, WINDOW, clock=clock)
    clock.now = 1_000.0
    assert limiter.hit("k").allowed

    clock.now = 1_059.5
    assert limiter.count("k") == 1
    assert limiter.peek("k") == RateDecision(False, 0, 0.5)

    clock.now = 1_060.0
    assert limiter.count("k") == 0
    assert limiter.peek("k") == RateDecision(True, 1, 0.0)
    print_success("counted at 59.5 s, gone at 60 s")


def test_peek_decides_like_hit_and_never_counts(clock: FakeClock) -> None:
    """RWL-008 — contract 4: any number of peeks leaves the count alone; a full key peeks refused with the same wait a hit gets at that moment."""
    print_section("RWL-008: peek never counts")
    limiter = SlidingWindowLimiter(2, WINDOW, clock=clock)

    for _ in range(5):
        assert limiter.peek("k") == RateDecision(True, 2, 0.0)
    assert limiter.count("k") == 0

    clock.now = 1_000.0
    limiter.hit("k")
    assert limiter.peek("k") == RateDecision(True, 1, 0.0)
    assert limiter.peek("k") == RateDecision(True, 1, 0.0)
    clock.now = 1_015.0
    limiter.hit("k")

    clock.now = 1_020.0
    assert limiter.peek("k") == RateDecision(False, 0, 40.0)
    assert limiter.hit("k") == RateDecision(False, 0, 40.0)
    assert limiter.count("k") == 2
    print_success("peek = hit's decision, count untouched")


# =============================================================================
# 6. THE PER-CALL LIMIT
# =============================================================================


def test_a_lowered_limit_waits_for_enough_hits_to_leave(clock: FakeClock) -> None:
    """RWL-009 — contract 6: four hits (1000, 1010, 1020, 1030) under a default of 5; at 1040 a limit of 2 must wait for three of them to leave, so ``retry_after = ts[4 - 2] + 60 - 1040 = 40``. At 1079.5 two still count; at 1080 one does, and the default never changed."""
    print_section("RWL-009: a lowered per-call limit")
    limiter = SlidingWindowLimiter(5, WINDOW, clock=clock)
    for moment in (1_000.0, 1_010.0, 1_020.0, 1_030.0):
        clock.now = moment
        assert limiter.hit("k").allowed

    clock.now = 1_040.0
    assert limiter.peek("k", limit=2) == RateDecision(False, 0, 40.0)
    assert limiter.hit("k", limit=2) == RateDecision(False, 0, 40.0)
    assert limiter.count("k") == 4

    clock.now = 1_079.5
    assert limiter.peek("k", limit=2) == RateDecision(False, 0, 0.5)
    clock.now = 1_080.0
    assert limiter.peek("k", limit=2) == RateDecision(True, 1, 0.0)
    assert limiter.peek("k") == RateDecision(True, 4, 0.0)
    print_success("refused for 40 s, then open; the default limit untouched")


def test_a_raised_limit_applies_to_that_call_only(clock: FakeClock) -> None:
    """RWL-010 — contract 6: with a default of 1, a full key still takes a hit under ``limit=3``, leaving ``3 - 2 = 1``; the next default hit is refused again."""
    print_section("RWL-010: a raised per-call limit")
    limiter = SlidingWindowLimiter(1, WINDOW, clock=clock)

    assert limiter.hit("k") == RateDecision(True, 0, 0.0)
    assert not limiter.hit("k").allowed
    assert limiter.hit("k", limit=3) == RateDecision(True, 1, 0.0)
    assert not limiter.hit("k").allowed
    assert limiter.count("k") == 2
    print_success("limit=3 for one call, 1 again after")


@pytest.mark.parametrize("operation", ["peek", "hit"])
@pytest.mark.parametrize("limit", [0, -1])
def test_a_per_call_limit_below_1_is_refused(clock: FakeClock, operation: str, limit: int) -> None:
    """RWL-011 — contract 6: ``limit < 1`` on ``peek`` or ``hit`` is a ``ValueError``, and nothing is counted."""
    print_section(f"RWL-011: {operation}(limit={limit})")
    limiter = SlidingWindowLimiter(3, WINDOW, clock=clock)

    with pytest.raises(ValueError):
        getattr(limiter, operation)("k", limit=limit)
    assert limiter.count("k") == 0
    print_success("ValueError, nothing counted")


# =============================================================================
# 7. KEYS
# =============================================================================


def test_keys_are_independent_and_none_is_a_key(clock: FakeClock) -> None:
    """RWL-012 — contract 7: a full ``alice`` blocks neither ``bob`` nor ``None``; ``None`` is also the key of a call without one."""
    print_section("RWL-012: independent keys")
    limiter = SlidingWindowLimiter(1, WINDOW, clock=clock)

    assert limiter.hit("alice").allowed
    assert not limiter.hit("alice").allowed
    assert limiter.hit("bob").allowed
    assert limiter.hit(None).allowed
    assert not limiter.hit().allowed

    assert (limiter.count("alice"), limiter.count("bob"), limiter.count(None), limiter.count()) == (1, 1, 1, 1)
    print_success("alice, bob and None counted apart")


def test_reset_forgets_one_key_and_clear_forgets_them_all(clock: FakeClock) -> None:
    """RWL-013 — contract 7: ``len`` is the number of keys tracked; ``reset`` drops one (``None`` included, an unknown key quietly), ``clear`` drops all."""
    print_section("RWL-013: reset, clear, len")
    limiter = SlidingWindowLimiter(3, WINDOW, clock=clock)
    for key in ("alice", "alice", "bob", None):
        limiter.hit(key)
    assert len(limiter) == 3

    limiter.reset("alice")
    assert len(limiter) == 2
    assert (limiter.count("bob"), limiter.count(None)) == (1, 1)
    assert limiter.peek("alice") == RateDecision(True, 3, 0.0)

    limiter.reset("never-seen")
    limiter.reset()
    assert limiter.count("bob") == 1
    assert limiter.count(None) == 0

    limiter.clear()
    assert len(limiter) == 0
    assert limiter.count("bob") == 0
    print_success("reset one, clear all")


# =============================================================================
# 8. BOUNDED MEMORY
# =============================================================================


def test_a_new_key_beyond_max_keys_evicts_the_least_recently_used(clock: FakeClock) -> None:
    """RWL-014 — contract 8: with room for two, ``c`` evicts ``a``, the key nobody used since."""
    print_section("RWL-014: eviction")
    limiter = SlidingWindowLimiter(5, WINDOW, max_keys=2, clock=clock)
    for key in ("a", "b", "c"):
        limiter.hit(key)

    assert len(limiter) == 2
    assert (limiter.count("c"), limiter.count("b")) == (1, 1)
    assert limiter.count("a") == 0
    print_success("a evicted")


@pytest.mark.parametrize("use", ["peek", "hit", "count"])
def test_using_a_key_keeps_it(clock: FakeClock, use: str) -> None:
    """RWL-015 — contract 8: peeking, hitting or counting ``a`` makes ``b`` the least recently used, so ``c`` evicts ``b``."""
    print_section(f"RWL-015: {use} keeps a key")
    limiter = SlidingWindowLimiter(5, WINDOW, max_keys=2, clock=clock)
    limiter.hit("a")
    limiter.hit("b")

    getattr(limiter, use)("a")
    limiter.hit("c")

    assert len(limiter) == 2
    assert limiter.count("a") == (2 if use == "hit" else 1)
    assert limiter.count("c") == 1
    assert limiter.count("b") == 0
    print_success(f"{use}('a') → b evicted")


def test_an_evicted_key_starts_over(clock: FakeClock) -> None:
    """RWL-016 — contract 8: the bound on memory is a bound on what is remembered — a full key evicted by another is allowed again."""
    print_section("RWL-016: eviction forgets the hits")
    limiter = SlidingWindowLimiter(1, WINDOW, max_keys=1, clock=clock)

    assert limiter.hit("a").allowed
    assert not limiter.hit("a").allowed
    assert limiter.hit("b").allowed
    assert limiter.hit("a").allowed
    print_success("a forgotten with its eviction")


# =============================================================================
# 9. THREADS
# =============================================================================


def test_concurrent_hits_on_one_key_allow_exactly_the_limit(clock: FakeClock) -> None:
    """RWL-017 — contract 9: 8 threads released together by a barrier make 200 hits on one key with a limit of 20: exactly 20 are allowed, their ``remaining`` values are 19…0 once each, and the count is 20.

    The interpreter's switch interval is lowered for the duration, so that threads change hands inside ``hit`` as often
    as possible: a check-then-record without the lock gets every chance to let a 21st hit through.
    """
    print_section("RWL-017: thread safety")
    limit, workers, hits_each = 20, 8, 25
    limiter = SlidingWindowLimiter(limit, WINDOW, clock=clock)
    barrier = threading.Barrier(workers, timeout=30)
    decisions: list[RateDecision] = []
    decisions_lock = threading.Lock()

    def hammer() -> None:
        barrier.wait()
        mine = [limiter.hit("shared") for _ in range(hits_each)]
        with decisions_lock:
            decisions.extend(mine)

    switch_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        threads = [threading.Thread(target=hammer, name=f"rwl-017-{index}") for index in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
    finally:
        sys.setswitchinterval(switch_interval)

    assert not [thread.name for thread in threads if thread.is_alive()]
    assert len(decisions) == workers * hits_each
    allowed = [decision for decision in decisions if decision.allowed]
    assert len(allowed) == limit, f"{len(allowed)} hits allowed for a limit of {limit}"
    assert sorted(decision.remaining for decision in allowed) == list(range(limit))
    assert limiter.count("shared") == limit
    print_success(f"{limit} of {workers * hits_each} allowed, remaining 19…0 once each")
