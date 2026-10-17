"""``backend.app.utils.runtime.rate_window``: the one sliding-window limiter of release 1.3 (plan phase01Email §3.2, decision D-E12, lot E1).

The hourly sending budget of the e-mail (workstream E) and the login limits of the accounts (A8) count with the same
primitive: hits of a key inside a sliding window, in memory, with a bounded number of keys and an injectable clock. The
contract pinned here:

1. ``RateDecision(allowed, remaining, retry_after)``, frozen.
2. ``SlidingWindowLimiter(limit, window_seconds, *, max_keys=10_000, eviction_scan=32, clock=time.monotonic)``:
   ``limit < 1``, ``window_seconds <= 0``, ``max_keys < 1`` or ``eviction_scan < 1`` is a ``ValueError``; ``limit``
   and ``window_seconds`` are properties.
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
8. At most ``max_keys`` keys, always: a new key is never refused for want of room, and after a ``hit`` the keys are
   never more than ``max_keys``. Room is made by evicting the least recently used key that is not full — used meaning
   peeked, hit or counted; full meaning that its hits still in the window at that moment are at least the limiter's
   own ``limit``: a per-call ``limit`` changes nothing here, and a key whose hits all left the window is not full. The
   search looks at the ``eviction_scan`` least recently used keys at most; when every key it looks at is full, the
   least recently used key goes, full or not, so that memory stays bounded. The new key is never the one evicted, and
   an evicted key's hits are forgotten with it. (N70, point 4, from review R13-SEC6: fresh keys sprayed at a per-key
   limit — the sign-in failures per identifier, for one — must not free a key that is locked.)
9. Thread-safe: threads hitting one key with a limit of N get exactly N hits allowed, each ``remaining`` value once.

Every test drives an injected fake clock: nothing waits for time to pass. Pure: no database, no server, no network.

Red until A8a (N70, point 4): today the limiter takes no ``eviction_scan``, and a new key evicts the least recently
used key, full or not. Red: RWL-002 (``eviction-scan-0``), RWL-003, RWL-018, RWL-019, RWL-020, RWL-022, RWL-023 and
RWL-024; RWL-014, RWL-015, RWL-016 and RWL-021 pin what holds before and after.
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
        pytest.param((1, WINDOW), {"eviction_scan": 0}, id="eviction-scan-0"),  # red until A8a (N70): no eviction_scan yet
    ],
)
def test_the_limiter_refuses_a_meaningless_configuration(arguments: tuple, keywords: dict) -> None:
    """RWL-002 — contract 2: no limit below 1, no window of zero or less, no room for less than one key, no search for a key to evict among less than one."""
    print_section(f"RWL-002: SlidingWindowLimiter{arguments} {keywords}")

    with pytest.raises(ValueError):
        SlidingWindowLimiter(*arguments, **keywords)
    print_success("ValueError")


# red until A8a (N70): SlidingWindowLimiter takes no eviction_scan yet
def test_the_limiter_exposes_its_limit_and_window_and_its_defaults() -> None:
    """RWL-003 — contract 2: ``limit`` and ``window_seconds`` as given; ``max_keys`` 10 000, ``eviction_scan`` 32 and ``clock`` ``time.monotonic`` by default, keyword-only. The real clock works without anybody moving it: two hits in an hour, the second refused for at most the hour."""
    print_section("RWL-003: properties and defaults")

    limiter = SlidingWindowLimiter(3, 3600.0)
    assert (limiter.limit, limiter.window_seconds) == (3, 3600.0)
    parameters = inspect.signature(SlidingWindowLimiter).parameters
    assert (parameters["max_keys"].default, parameters["max_keys"].kind) == (10_000, inspect.Parameter.KEYWORD_ONLY)
    assert (parameters["eviction_scan"].default, parameters["eviction_scan"].kind) == (32, inspect.Parameter.KEYWORD_ONLY)
    assert (parameters["clock"].default, parameters["clock"].kind) == (time.monotonic, inspect.Parameter.KEYWORD_ONLY)

    real = SlidingWindowLimiter(1, 3600.0)
    assert real.hit("k").allowed
    refused = real.hit("k")
    assert not refused.allowed and 0.0 < refused.retry_after <= 3600.0
    print_success("limit 3, window 3600, max_keys 10 000, eviction_scan 32, clock time.monotonic")


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


def test_a_new_key_beyond_max_keys_evicts_the_least_recently_used_key_not_full(clock: FakeClock) -> None:
    """RWL-014 — contract 8: with room for two and no key full (a limit of 5), ``c`` evicts the least recently used key not full: ``a``, the key nobody used since."""
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
    """RWL-015 — contract 8: no key full (a limit of 5); peeking, hitting or counting ``a`` makes ``b`` the least recently used, so ``c`` evicts ``b``."""
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


def test_when_the_only_other_key_is_full_it_is_evicted_all_the_same(clock: FakeClock) -> None:
    """RWL-016 — contract 8, the fallback: with room for one key, the only other key is full, and it goes all the same — memory stays bounded, and that bound is a bound on what is remembered: evicted, the full ``a`` is allowed again. The new key is never the one evicted."""
    print_section("RWL-016: the fallback evicts a full key")
    limiter = SlidingWindowLimiter(1, WINDOW, max_keys=1, clock=clock)

    assert limiter.hit("a").allowed
    assert not limiter.hit("a").allowed
    assert limiter.hit("b").allowed
    assert len(limiter) == 1
    assert limiter.count("b") == 1
    assert limiter.hit("a").allowed
    print_success("a full, evicted by b all the same: forgotten")


# red until A8a (N70): today the new key evicts the least recently used key, full or not
@pytest.mark.parametrize("not_full", ["b", None])
def test_a_new_key_evicts_the_key_not_full_and_spares_an_older_full_one(clock: FakeClock, not_full: str | None) -> None:
    """RWL-018 — contract 8: room for 2, one full and older (the least recently used) plus one not full: a new key evicts the one not full. ``a`` keeps its two hits and stays refused for the whole window, ``c`` is allowed; the key not full is ``b``, or ``None`` — a key like any other here too (contract 7)."""
    print_section(f"RWL-018: a full and older, {not_full!r} not full, then c")
    limiter = SlidingWindowLimiter(2, WINDOW, max_keys=2, clock=clock)
    assert [limiter.hit(key).remaining for key in ("a", "a", not_full)] == [1, 0, 1]

    assert limiter.hit("c") == RateDecision(True, 1, 0.0)

    assert limiter.peek("a") == RateDecision(False, 0, 60.0), f"a, full, was evicted although {not_full!r} was not full"
    assert limiter.count("a") == 2
    assert limiter.count(not_full) == 0
    assert limiter.count("c") == 1
    assert len(limiter) == 2
    print_success(f"{not_full!r} evicted; a kept, refused for 60 s")


# red until A8a (N70): today the new key evicts the least recently used key, full or not
@pytest.mark.parametrize("second_hit_of_a", [pytest.param(1_005.0, id="every-hit-expired"), pytest.param(1_040.0, id="one-hit-expired")])
def test_a_key_whose_hits_left_the_window_is_not_full(clock: FakeClock, second_hit_of_a: float) -> None:
    """RWL-019 — contract 8: full counts the hits still in the window when the room is made. ``a`` takes two hits (1000, then 1005 or 1040), ``b`` two at 1050, and ``a`` is peeked full at 1055 — ``b`` is now the least recently used. At 1070 the hit of 1000 has left the window, and that of 1005 with it: ``a`` is not full any more, ``b`` still is, and ``c`` evicts ``a``, not ``b``, which stays refused for 40 s."""
    print_section(f"RWL-019: a's hits at 1000 and {second_hit_of_a:g}, c at 1070")
    limiter = SlidingWindowLimiter(2, WINDOW, max_keys=2, clock=clock)
    clock.now = 1_000.0
    limiter.hit("a")
    clock.now = second_hit_of_a
    assert limiter.hit("a") == RateDecision(True, 0, 0.0)
    clock.now = 1_050.0
    limiter.hit("b")
    assert limiter.hit("b") == RateDecision(True, 0, 0.0)
    clock.now = 1_055.0
    assert not limiter.peek("a").allowed

    clock.now = 1_070.0
    assert limiter.hit("c") == RateDecision(True, 1, 0.0)

    assert limiter.peek("b") == RateDecision(False, 0, 40.0), "b, full in the window, was evicted although the hits of a had left it"
    assert limiter.count("a") == 0
    assert limiter.count("c") == 1
    assert len(limiter) == 2
    print_success("a evicted; b kept, refused for 40 s")


# red until A8a (N70): today the new key evicts the least recently used key, full or not
@pytest.mark.parametrize(("limit", "call_limit", "hits_of_b"), [pytest.param(2, 5, 1, id="higher-call-limit"), pytest.param(3, 2, 2, id="lower-call-limit")])
def test_full_is_measured_against_the_limiters_own_limit(clock: FakeClock, limit: int, call_limit: int, hits_of_b: int) -> None:
    """RWL-020 — contract 8: full is measured against the limiter's own ``limit``, whatever the call that makes the room. Room for three: ``a`` at the limit, ``b`` below it, ``c`` with one hit; the new ``d`` comes with a per-call limit. ``a`` stays, refused, and ``b`` goes: a per-call limit above the default does not make ``a`` evictable (measured by it, ``a`` would have room), one below does not make ``b`` full (measured by it, ``b`` would be, and ``c`` would go)."""
    print_section(f"RWL-020: limit {limit}, d hit with limit={call_limit}")
    limiter = SlidingWindowLimiter(limit, WINDOW, max_keys=3, clock=clock)
    for key in ["a"] * limit + ["b"] * hits_of_b + ["c"]:
        assert limiter.hit(key).allowed

    assert limiter.hit("d", limit=call_limit) == RateDecision(True, call_limit - 1, 0.0)

    assert limiter.peek("a") == RateDecision(False, 0, 60.0), f"a, at the limiter's limit of {limit}, was evicted"
    assert limiter.count("b") == 0, f"b, {hits_of_b} hit(s) for a limit of {limit}, is the key not full and must be the one evicted"
    assert (limiter.count("c"), limiter.count("d")) == (1, 1)
    assert len(limiter) == 3
    print_success(f"b evicted, a kept: full means {limit} hits, whatever limit d came with")


@pytest.mark.parametrize("new", ["c", None])
def test_when_every_other_key_is_full_the_least_recently_used_goes(clock: FakeClock, new: str | None) -> None:
    """RWL-021 — contract 8, the fallback: room for two, ``a`` then ``b`` hit until full; the new key evicts the least recently used, ``a`` — memory stays bounded — and never itself: ``b`` stays refused, the new key keeps its hit (``None`` too), and ``a`` starts over."""
    print_section(f"RWL-021: every other key full, then {new!r}")
    limiter = SlidingWindowLimiter(2, WINDOW, max_keys=2, clock=clock)
    assert [limiter.hit(key).remaining for key in ("a", "a", "b", "b")] == [1, 0, 1, 0]

    assert limiter.hit(new) == RateDecision(True, 1, 0.0)

    assert len(limiter) == 2
    assert limiter.peek("b") == RateDecision(False, 0, 60.0)
    assert limiter.count(new) == 1
    assert limiter.peek("a") == RateDecision(True, 2, 0.0)
    print_success("a evicted, full as it was; b still refused, the new key kept")


# red until A8a (N70): SlidingWindowLimiter takes no eviction_scan yet
@pytest.mark.parametrize(("eviction_scan", "evicted"), [pytest.param(2, "a", id="scan-2"), pytest.param(3, "c", id="scan-3")])
def test_the_search_for_a_key_not_full_looks_at_eviction_scan_keys_at_most(clock: FakeClock, eviction_scan: int, evicted: str) -> None:
    """RWL-022 — contract 8: the search is bounded, so that a map of full keys cannot make every new key cost ``max_keys`` steps under the lock — the «forgot password» limits are hit on every request, before any bcrypt, and would turn that into a CPU amplifier. Room for four: ``a`` and ``b`` full and the least recently used, then ``c`` and ``d`` with one hit each. Looking at two keys, the search sees only full ones, and ``e`` evicts the least recently used, ``a``, although ``c`` beyond its reach is not full; looking at three, it reaches ``c`` and evicts it."""
    print_section(f"RWL-022: eviction_scan={eviction_scan} → {evicted} evicted")
    limiter = SlidingWindowLimiter(2, WINDOW, max_keys=4, eviction_scan=eviction_scan, clock=clock)
    assert [limiter.hit(key).remaining for key in ("a", "a", "b", "b", "c", "d")] == [1, 0, 1, 0, 1, 1]

    assert limiter.hit("e") == RateDecision(True, 1, 0.0)

    assert len(limiter) == 4
    assert {key: limiter.count(key) for key in "abcde"} == {"a": 2, "b": 2, "c": 1, "d": 1, "e": 1} | {evicted: 0}
    print_success(f"{evicted} evicted")


# red until A8a (N70): today the third new key evicts the full one
def test_the_bound_holds_and_a_full_key_outlives_a_hundred_new_ones(clock: FakeClock) -> None:
    """RWL-023 — contract 8: room for three, ``full`` at its limit, then 100 new keys with one hit each. Every new key is allowed, the keys are two, then three after every hit and never more, and at the end ``full`` is still there and refused, beside the last two new keys."""
    print_section("RWL-023: a full key among 100 new ones")
    limiter = SlidingWindowLimiter(2, WINDOW, max_keys=3, clock=clock)
    assert [limiter.hit("full").remaining for _ in range(2)] == [1, 0]

    sizes = []
    for index in range(100):
        assert limiter.hit(f"new-{index}") == RateDecision(True, 1, 0.0)
        sizes.append(len(limiter))

    assert sizes == [2] + [3] * 99
    assert limiter.peek("full") == RateDecision(False, 0, 60.0), "the full key was evicted by new keys while keys not full were there to go"
    assert [limiter.count(f"new-{index}") for index in (97, 98, 99)] == [0, 1, 1]
    print_success("never more than 3 keys; full kept and refused")


# red until A8a (N70): today the 100th fresh identifier evicts the locked one
def test_a_locked_identifier_stays_locked_through_a_thousand_fresh_ones(clock: FakeClock) -> None:
    """RWL-024 — contract 8, review R13-SEC6 at scale: the sign-in failures per identifier (10 in 15 minutes, ``services/accounts/login_throttle.py``) with room for 100 keys. ``victim`` is locked by 10 failures; then 1 000 fresh identifiers fail once each, every failure counted. The spray must not free ``victim``: an 11th attempt is still refused for the whole window, and its 10 failures are all there."""
    print_section("RWL-024: a locked identifier through 1 000 fresh ones")
    limiter = SlidingWindowLimiter(10, 15 * 60, max_keys=100, clock=clock)
    assert [limiter.hit("victim").remaining for _ in range(10)] == list(range(9, -1, -1))

    refused = [index for index in range(1_000) if not limiter.hit(f"fresh-{index}").allowed]

    assert refused == []
    assert len(limiter) == 100
    assert limiter.hit("victim") == RateDecision(False, 0, 900.0), "1 000 fresh identifiers freed the locked one: it has 10 more attempts"
    assert limiter.count("victim") == 10
    print_success("victim still locked for 900 s after 1 000 fresh identifiers")


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
