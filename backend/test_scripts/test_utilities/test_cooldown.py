"""``backend.app.utils.runtime.cooldown``: the pauses of a remote that answered «too many requests» (plan phase01SleepWake §Z7a, decision 34, lot Z7a).

A provider that refuses with HTTP 429 is left alone for a while by every caller of the process: the n-th consecutive
refusal pauses its key for ``base × 2^(n−1)`` seconds up to a ceiling, a ``Retry-After`` counting as a minimum, plus a
jitter; once the pause is over a single trial call goes through (half-open) and the other callers wait for its verdict.
The contract pinned here:

1. ``RateLimitedError(Exception)``, the marker of a remote refusal: ``__init__(*args, retry_after=None, scope=None)``,
   the two keyword-only and None unless given, ``*args`` handed to ``Exception``. It combines with a domain exception
   by multiple inheritance — here with a stand-in of ``AssetSourceError``, so that no service is imported.
2. ``retry_after_seconds(value, *, now=None)`` reads an HTTP ``Retry-After`` (RFC 9110): delta-seconds, decimals and
   surrounding spaces tolerated; an HTTP-date as the seconds from ``now`` (epoch seconds, ``time.time()`` by default)
   until it, 0 once past. ``None`` for nothing, blank, negative, non-finite or unreadable — a malformed date included.
3. ``CooldownState(key, refusals, remaining, trial_in_flight)``, frozen.
4. ``Cooldowns(base_seconds, max_seconds, *, hard_max_seconds=86_400, jitter=0.1, trial_seconds=60, max_keys=10_000,
   clock=time.time, rng=random.random)``: a ``ValueError`` for a base of 0 or less, a max below the base, a hard max
   below the max, a jitter outside [0, 1], a trial window of 0 or less, room for less than one key.
5. ``check(key)``: 0 when a call may go now. An unknown key is 0 and creates nothing. During a pause, the seconds left.
   Once it is over, the first caller gets 0 and holds the trial slot, every other caller the rest of the trial window
   (``trial_seconds`` at first); a trial without a verdict for ``trial_seconds`` frees the slot for the next caller.
6. ``refused(key, retry_after=None, *, base_seconds=None, max_seconds=None)`` once the key's pause is over — its trial
   taken or not — records the n-th refusal in a row and sets ``max(min(b·2^(n−1), m), min(retry_after, hard_max))``
   — ``retry_after`` only when positive and finite — times ``1 + jitter·rng()``, never above ``hard_max``, and returns
   it; a ``b`` or ``m`` given to a call replaces the instance's for that call only. ``check`` then counts it down, and
   the trial slot is free again. A refusal more than ``m`` after the end of the previous pause starts over from n = 1.
   No overflow, however long the streak.
7. While a pause runs — before its end; the trial window after it does not count — an answer comes from a call already
   in flight when the pause began. A refusal then counts nothing and never shortens the pause: only its own
   ``retry_after`` floor (positive and finite, at most ``hard_max``) ending later extends it, to ``now + floor``
   without jitter; it returns the seconds left. A success changes nothing and ``succeeded`` returns 0; ``released``
   changes nothing. Refusals in a row are therefore refusals of calls made after each pause ended.
8. A clock that goes backwards never makes the time left exceed the recorded wait.
9. Once the pause is over — its trial taken or not — ``succeeded(key)`` forgets the key and returns its refusals, 0
   when unknown. ``released(key)`` frees the trial slot of a call that ended without a verdict and keeps the count; it
   ignores an unknown key.
10. ``snapshot()``: one ``CooldownState`` per key, ``remaining`` 0 once the pause is over, ``trial_in_flight`` only
    while a slot is held and not expired. ``reset`` (one key) and ``len``; any hashable is a key — provider tuples,
    ``None`` — and keys are independent.
11. At most ``max_keys`` keys: a new key beyond them evicts the least recently used one — used meaning checked or
    refused, a refusal that counts nothing included — and its refusals are forgotten with it.
12. Thread-safe: once a pause is over, threads checking together let exactly one trial through, and threads refusing
    together count one refusal.

Every test drives an injected fake clock and a fixed random source (0.0, 1.0 or a written sequence) — but CDW-010,
which checks the real ones without waiting —: nothing waits for time to pass. Every escalation advances the fake clock
past each pause before the next refusal (contract 7). Pure: no database, no server, no network, no environment read.

Red until ``backend/app/utils/runtime/cooldown.py`` exists: the module does not import.
"""

from __future__ import annotations

import calendar
import dataclasses
import inspect
import itertools
import math
import random
import sys
import threading
import time
from collections.abc import Callable, Hashable
from email.utils import formatdate

import pytest

from backend.app.utils.runtime.cooldown import Cooldowns, CooldownState, RateLimitedError, retry_after_seconds
from backend.test_scripts.test_utils import print_section, print_success

START = 1_000.0
BASE = 60.0
MAX = 3_600.0
#: The first refusals in a row with the shipped values and no jitter: 60 s doubling, an hour at most.
DOUBLING = [60.0, 120.0, 240.0, 480.0, 960.0, 1_920.0, 3_600.0, 3_600.0]
#: Retry-After dates with their instants: the example of this contract and RFC 9110's own.
DATES = [
    pytest.param("Wed, 21 Oct 2015 07:28:00 GMT", calendar.timegm((2015, 10, 21, 7, 28, 0)), id="2015"),
    pytest.param("Fri, 31 Dec 1999 23:59:59 GMT", calendar.timegm((1999, 12, 31, 23, 59, 59)), id="rfc-9110"),
]


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _lowest() -> float:
    """The random source at its lowest: the jitter adds nothing."""
    return 0.0


def _highest() -> float:
    """The random source at its highest (``random.random`` only comes close): the jitter adds all it may."""
    return 1.0


class _AssetSourceErrorStandIn(Exception):
    """Mirrors ``AssetSourceError`` (``backend/app/services/assets/base.py``) without importing the services: ``super().__init__(message)``, then ``message``, ``error_code`` and ``details``."""

    def __init__(self, message: str, error_code: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class _AssetRateLimited(_AssetSourceErrorStandIn, RateLimitedError):
    """The combination the asset domain is to write (X1): the domain error first, the marker after it."""

    def __init__(self, message: str, *, retry_after: float | None = None, scope: str | None = None) -> None:
        # The domain __init__: its own super().__init__(message) reaches RateLimitedError.__init__ through the MRO.
        super().__init__(message, "RATE_LIMITED")
        self.retry_after = retry_after
        self.scope = scope


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def cooldowns(clock: FakeClock) -> Cooldowns:
    """The shipped values — 60 s doubling up to an hour — on the fake clock, without jitter."""
    return Cooldowns(BASE, MAX, clock=clock, rng=_lowest)


def _streak(cooldowns: Cooldowns, clock: FakeClock, key: Hashable, count: int, *, late: float = 0.0, retry_after: float | None = None, **overrides: float) -> list[float]:
    """``count`` refusals in a row as a remote gives them in service, and their waits.

    Refusals in a row are refusals of calls made after each pause ended (contract 7): each one here answers the trial
    call that ``check`` lets through once the previous pause is over, ``late`` seconds after its end (well inside the
    max: the streak goes on). The clock is left ``late`` seconds past the end of the last pause.
    """
    waits = []
    for _ in range(count):
        assert cooldowns.check(key) == 0.0, f"no trial let through for {key!r} at {clock.now}"
        wait = cooldowns.refused(key, retry_after, **overrides)
        waits.append(wait)
        clock.now += wait + late
    return waits


def _states(cooldowns: Cooldowns) -> dict[Hashable, CooldownState]:
    """The snapshot as ``{key: state}``, once checked to be a tuple of ``CooldownState`` holding each key once."""
    snapshot = cooldowns.snapshot()
    assert isinstance(snapshot, tuple), f"snapshot() returned a {type(snapshot).__name__}, not a tuple"
    assert all(isinstance(state, CooldownState) for state in snapshot), snapshot
    states = {state.key: state for state in snapshot}
    assert len(states) == len(snapshot), f"a key appears twice in the snapshot: {snapshot}"
    return states


def _race(workers: int, calls_each: int, call: Callable[[], float], name: str) -> list[float]:
    """``workers`` threads released together by a barrier, each making ``calls_each`` calls; every answer, once all are done.

    The interpreter's switch interval is lowered for the duration, so that threads change hands inside a call as often
    as possible: a test-then-act without the lock gets every chance to show.
    """
    barrier = threading.Barrier(workers, timeout=30)
    results: list[float] = []
    results_lock = threading.Lock()

    def run() -> None:
        barrier.wait()
        mine = [call() for _ in range(calls_each)]
        with results_lock:
            results.extend(mine)

    switch_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        threads = [threading.Thread(target=run, name=f"{name}-{index}") for index in range(workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
    finally:
        sys.setswitchinterval(switch_interval)

    assert not [thread.name for thread in threads if thread.is_alive()]
    assert len(results) == workers * calls_each, f"{len(results)} answers for {workers * calls_each} calls: a thread failed"
    return results


# =============================================================================
# 1. THE MARKER
# =============================================================================


def test_rate_limited_error_is_a_marker_with_two_keyword_only_attributes() -> None:
    """CDW-001 — contract 1: an ``Exception`` and nothing more; ``*args`` reach ``Exception`` as given; ``retry_after`` and ``scope`` keyword-only, None unless given."""
    print_section("CDW-001: RateLimitedError")

    assert RateLimitedError.__bases__ == (Exception,)
    parameters = inspect.signature(RateLimitedError.__init__).parameters
    assert [parameter.kind for parameter in parameters.values()].count(inspect.Parameter.VAR_POSITIONAL) == 1
    assert {name: parameter.default for name, parameter in parameters.items() if parameter.kind is inspect.Parameter.KEYWORD_ONLY} == {"retry_after": None, "scope": None}

    bare = RateLimitedError("the remote refused: too many calls")
    assert (str(bare), bare.args, bare.retry_after, bare.scope) == ("the remote refused: too many calls", ("the remote refused: too many calls",), None, None)
    full = RateLimitedError("slow down", retry_after=30.0, scope="example.com")
    assert (str(full), full.args, full.retry_after, full.scope) == ("slow down", ("slow down",), 30.0, "example.com")
    empty = RateLimitedError()
    assert (empty.args, empty.retry_after, empty.scope) == ((), None, None)
    print_success("Exception subclass, retry_after and scope keyword-only, None by default")


def test_rate_limited_error_combines_with_a_domain_exception() -> None:
    """CDW-002 — contract 1: ``class _AssetRateLimited(_AssetSourceErrorStandIn, RateLimitedError)`` — the stand-in mirrors ``AssetSourceError``, whose ``__init__`` calls ``super().__init__(message)`` — is both, reads as its message, keeps the domain's attributes and the marker's, and one ``except`` of either kind catches it."""
    print_section("CDW-002: multiple inheritance with a domain error")

    error = _AssetRateLimited("yahoo answered 429", retry_after=30.0, scope="query1.finance.yahoo.com")
    assert isinstance(error, RateLimitedError) and isinstance(error, _AssetSourceErrorStandIn)
    assert (str(error), error.args) == ("yahoo answered 429", ("yahoo answered 429",))
    assert (error.message, error.error_code, error.details) == ("yahoo answered 429", "RATE_LIMITED", {})
    assert (error.retry_after, error.scope) == (30.0, "query1.finance.yahoo.com")
    plain = _AssetRateLimited("again")
    assert (plain.retry_after, plain.scope, plain.error_code) == (None, None, "RATE_LIMITED")

    with pytest.raises(RateLimitedError):
        raise error
    with pytest.raises(_AssetSourceErrorStandIn):
        raise error
    print_success("an AssetSourceError-like error and a RateLimitedError at once")


# =============================================================================
# 2. retry_after_seconds
# =============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("120", 120.0, id="integer"),
        pytest.param("1.5", 1.5, id="decimal"),
        pytest.param(" 30 ", 30.0, id="surrounding-spaces"),
        pytest.param("0", 0.0, id="zero"),
    ],
)
def test_delta_seconds_are_read_as_seconds(value: str, expected: float) -> None:
    """CDW-003 — contract 2: a number of seconds is that many seconds, whatever ``now`` says."""
    print_section(f"CDW-003: Retry-After {value!r}")

    assert retry_after_seconds(value) == expected
    assert retry_after_seconds(value, now=START) == expected
    print_success(f"{value!r} → {expected} s")


@pytest.mark.parametrize(
    ("before", "expected"),
    [
        pytest.param(60.0, 60.0, id="a-minute-ahead"),
        pytest.param(29.5, 29.5, id="a-fraction-ahead"),
        pytest.param(86_400.0, 86_400.0, id="a-day-ahead"),
        pytest.param(0.0, 0.0, id="now"),
        pytest.param(-60.0, 0.0, id="a-minute-past"),
        pytest.param(-365 * 86_400.0, 0.0, id="a-year-past"),
    ],
)
@pytest.mark.parametrize(("date", "instant"), DATES)
def test_an_http_date_is_the_time_from_now_until_it(date: str, instant: int, before: float, expected: float) -> None:
    """CDW-004 — contract 2: an HTTP-date ``before`` seconds after ``now`` is ``before`` seconds; a date already past is 0, never negative."""
    print_section(f"CDW-004: {date!r}, now {before} s before it")

    assert retry_after_seconds(date, now=instant - before) == pytest.approx(expected, abs=1e-6)
    print_success(f"{expected} s")


def test_an_http_date_counts_from_the_wall_clock_by_default() -> None:
    """CDW-005 — contract 2: ``now`` is keyword-only and None by default, which means ``time.time()``: a date written an hour from the wall clock (to the second) is a little under 3600 s away — a monotonic clock would be decades off."""
    print_section("CDW-005: now defaults to the wall clock")

    parameter = inspect.signature(retry_after_seconds).parameters["now"]
    assert (parameter.kind, parameter.default) == (inspect.Parameter.KEYWORD_ONLY, None)
    in_an_hour = formatdate(time.time() + 3_600, usegmt=True)
    seconds = retry_after_seconds(in_an_hour)
    assert seconds is not None and 3_590.0 < seconds <= 3_600.0, f"{in_an_hour!r} read as {seconds} s"
    print_success(f"{in_an_hour!r} → {seconds:.3f} s")


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="blank"),
        pytest.param("-5", id="negative"),
        pytest.param("-0.5", id="negative-decimal"),
        pytest.param("inf", id="inf"),
        pytest.param("-inf", id="minus-inf"),
        pytest.param("nan", id="nan"),
        pytest.param("1e400", id="overflows-to-inf"),
        # Digits only, yet beyond any float: non-finite once read, and never an OverflowError.
        pytest.param("1" + "0" * 400, id="400-digits"),
        pytest.param("abc", id="abc"),
        pytest.param("soon", id="soon"),
        pytest.param("120 seconds", id="with-a-unit"),
        pytest.param("Wed, 32 Oct 2015 07:28:00 GMT", id="date-day-32"),
        pytest.param("Wed, 21 Oct 2015 25:28:00 GMT", id="date-hour-25"),
        pytest.param("Wed, 21 Foo 2015 07:28:00 GMT", id="date-unknown-month"),
        pytest.param("21 Oct 2015", id="date-incomplete"),
    ],
)
def test_anything_else_is_none(value: str | None) -> None:
    """CDW-006 — contract 2: nothing, blank, negative, non-finite or unreadable — a malformed date too — is None, with or without ``now``; never an exception."""
    print_section(f"CDW-006: Retry-After {value!r}"[:120])

    assert retry_after_seconds(value) is None
    assert retry_after_seconds(value, now=START) is None
    print_success("None")


# =============================================================================
# 3. CooldownState
# =============================================================================


def test_cooldown_state_is_a_frozen_dataclass() -> None:
    """CDW-007 — contract 3: four fields in order, compared by value, never edited."""
    print_section("CDW-007: CooldownState")

    assert [field.name for field in dataclasses.fields(CooldownState)] == ["key", "refusals", "remaining", "trial_in_flight"]
    state = CooldownState(key=("asset", "yfinance", None), refusals=2, remaining=120.0, trial_in_flight=False)
    assert state == CooldownState(("asset", "yfinance", None), 2, 120.0, False)
    with pytest.raises(dataclasses.FrozenInstanceError):
        state.refusals = 0  # type: ignore[misc]
    print_success("frozen (key, refusals, remaining, trial_in_flight)")


# =============================================================================
# 4. THE CONSTRUCTOR
# =============================================================================


@pytest.mark.parametrize(
    ("arguments", "keywords"),
    [
        pytest.param((0, MAX), {}, id="base-0"),
        pytest.param((-1, MAX), {}, id="base-negative"),
        pytest.param((BASE, 59), {}, id="max-below-base"),
        pytest.param((BASE, MAX), {"hard_max_seconds": 3_599}, id="hard-max-below-max"),
        pytest.param((BASE, MAX), {"jitter": -0.1}, id="jitter-negative"),
        pytest.param((BASE, MAX), {"jitter": 1.5}, id="jitter-above-1"),
        pytest.param((BASE, MAX), {"trial_seconds": 0}, id="trial-0"),
        pytest.param((BASE, MAX), {"trial_seconds": -1}, id="trial-negative"),
        pytest.param((BASE, MAX), {"max_keys": 0}, id="max-keys-0"),
    ],
)
def test_cooldowns_refuse_a_meaningless_configuration(arguments: tuple, keywords: dict) -> None:
    """CDW-008 — contract 4: no base of 0 or less, no max below the base, no hard max below the max, no jitter outside [0, 1], no trial window of 0 or less, no room for less than one key."""
    print_section(f"CDW-008: Cooldowns{arguments} {keywords}")

    with pytest.raises(ValueError):
        Cooldowns(*arguments, **keywords)
    print_success("ValueError")


@pytest.mark.parametrize(
    ("arguments", "keywords"),
    [
        pytest.param((BASE, BASE), {}, id="max-equal-to-base"),
        pytest.param((BASE, MAX), {"hard_max_seconds": MAX}, id="hard-max-equal-to-max"),
        pytest.param((BASE, MAX), {"jitter": 0.0}, id="jitter-0"),
        pytest.param((BASE, MAX), {"jitter": 1.0}, id="jitter-1"),
        pytest.param((0.5, MAX), {"trial_seconds": 0.5}, id="fractions"),
        pytest.param((BASE, MAX), {"max_keys": 1}, id="one-key"),
    ],
)
def test_cooldowns_accept_the_edges_of_their_domain(clock: FakeClock, arguments: tuple, keywords: dict) -> None:
    """CDW-009 — contract 4: the edges themselves are allowed, and such an instance works: a first refusal without jitter waits the base."""
    print_section(f"CDW-009: Cooldowns{arguments} {keywords}")

    cooldowns = Cooldowns(*arguments, **keywords, clock=clock, rng=_lowest)
    assert cooldowns.check("k") == 0.0
    assert cooldowns.refused("k") == arguments[0]
    print_success(f"accepted, first wait {arguments[0]} s")


def test_the_defaults_are_keyword_only_and_the_real_clock_and_random_source_work() -> None:
    """CDW-010 — contract 4: ``base_seconds`` and ``max_seconds`` first; then, keyword-only, a hard max of 24 h, a jitter of 0.1, a trial window of 60 s, 10 000 keys, ``time.time`` and ``random.random``. With them nobody moves the clock: a first refusal waits 60 to 66 s, and ``check`` counts it down from there."""
    print_section("CDW-010: defaults")

    parameters = inspect.signature(Cooldowns).parameters
    assert [name for name, parameter in parameters.items() if parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD] == ["base_seconds", "max_seconds"]
    keyword_only = {name: parameter.default for name, parameter in parameters.items() if parameter.kind is inspect.Parameter.KEYWORD_ONLY}
    expected = {"hard_max_seconds": 86_400, "jitter": 0.1, "trial_seconds": 60, "max_keys": 10_000, "clock": time.time, "rng": random.random}
    assert {name: keyword_only.get(name, "<not keyword-only>") for name in expected} == expected

    real = Cooldowns(BASE, MAX)
    wait = real.refused("k")
    assert 60.0 <= wait <= 66.0
    assert 0.0 < real.check("k") <= wait
    print_success(f"keyword-only defaults; a real first wait of {wait:.3f} s")


# =============================================================================
# 5. check
# =============================================================================


def test_an_unknown_key_may_call_and_is_not_tracked(cooldowns: Cooldowns) -> None:
    """CDW-011 — contract 5: a key never refused may call now, and asking creates no entry."""
    print_section("CDW-011: an unknown key")

    for key in ("k", ("asset", "yfinance", None), None):
        assert cooldowns.check(key) == 0.0
    assert len(cooldowns) == 0
    assert cooldowns.snapshot() == ()
    print_success("0, nothing tracked")


def test_during_a_pause_check_gives_the_seconds_left(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-012 — contract 5: refused at 1000 for 60 s, the key waits 60 s at once, 45 s at 1015, 0.5 s at 1059.5."""
    print_section("CDW-012: the seconds left")

    assert cooldowns.refused("k") == 60.0
    assert cooldowns.check("k") == 60.0
    clock.now = 1_015.0
    assert cooldowns.check("k") == 45.0
    clock.now = 1_059.5
    assert cooldowns.check("k") == 0.5
    print_success("60, 45, 0.5")


@pytest.mark.parametrize("trial", [60.0, 15.0])
def test_once_a_pause_is_over_one_trial_goes_and_the_others_wait_for_it(clock: FakeClock, trial: float) -> None:
    """CDW-013 — contract 5: the pause of 60 s from 1000 ends at 1060. There the first ``check`` is 0 and takes the trial slot; the next ones get the rest of the trial window — ``trial`` at once, half of it halfway, 0.5 s just before its end. At its end, still without a verdict, the slot is free: one more 0, then a whole window again.

    At the very end of a pause or of a window, the first caller goes and the second does not: two calls let through at the same instant would be two trials.
    """
    print_section(f"CDW-013: one trial at a time, a window of {trial} s")
    cooldowns = Cooldowns(BASE, MAX, trial_seconds=trial, clock=clock, rng=_lowest)
    assert cooldowns.refused("k") == 60.0

    clock.now = 1_060.0
    assert cooldowns.check("k") == 0.0
    assert cooldowns.check("k") == trial
    clock.now = 1_060.0 + trial / 2
    assert cooldowns.check("k") == trial / 2
    clock.now = 1_060.0 + trial - 0.5
    assert cooldowns.check("k") == 0.5
    clock.now = 1_060.0 + trial
    assert cooldowns.check("k") == 0.0
    assert cooldowns.check("k") == trial
    print_success(f"0 then {trial}; free again after {trial} s without a verdict")


# =============================================================================
# 6. refused: THE WAIT
# =============================================================================


def test_consecutive_refusals_double_the_wait_up_to_the_max(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-014 — contract 6: with 60 s and an hour, no jitter, refusals in a row — each the answer of the trial let through once the previous pause is over — wait 60, 120, 240, 480, 960, 1920 s, then an hour, and an hour again; the snapshot counts eight."""
    print_section("CDW-014: doubling up to the max")

    assert _streak(cooldowns, clock, "k", 8) == DOUBLING
    assert _states(cooldowns)["k"].refusals == 8
    print_success("60 → 3600, then 3600")


def test_a_streak_of_any_length_stays_at_the_max(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-015 — contract 6: 1100 refusals in a row — past 2^1024, where a float power overflows — still wait the max, and are all counted."""
    print_section("CDW-015: no overflow")

    waits = _streak(cooldowns, clock, "k", 1_100)
    assert waits[:7] == DOUBLING[:7]
    assert set(waits[6:]) == {3_600.0}
    assert _states(cooldowns)["k"].refusals == 1_100
    print_success("1100 refusals, an hour each from the seventh on")


@pytest.mark.parametrize(
    ("retry_after", "expected"),
    [
        pytest.param(None, 60.0, id="none"),
        pytest.param(30.0, 60.0, id="below-the-step"),
        pytest.param(500.0, 500.0, id="above-the-step"),
        pytest.param(7_200.0, 7_200.0, id="above-the-max"),
        pytest.param(86_400.0, 86_400.0, id="at-the-hard-max"),
        pytest.param(200_000.0, 86_400.0, id="above-the-hard-max"),
        pytest.param(0.0, 60.0, id="zero"),
        pytest.param(-5.0, 60.0, id="negative"),
        pytest.param(math.inf, 60.0, id="inf"),
        pytest.param(math.nan, 60.0, id="nan"),
    ],
)
def test_retry_after_is_a_floor_up_to_the_hard_max(cooldowns: Cooldowns, retry_after: float | None, expected: float) -> None:
    """CDW-016 — contract 6: on a first refusal (step 60 s) a positive, finite ``retry_after`` is a minimum — honoured above the max, up to the hard max of 24 h —; zero, negative or non-finite counts for nothing. ``check`` gives the same wait."""
    print_section(f"CDW-016: retry_after {retry_after}")

    assert cooldowns.refused("k", retry_after) == expected
    assert cooldowns.check("k") == expected
    print_success(f"{expected} s")


def test_retry_after_does_not_reset_the_doubling(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-017 — contract 6: every refusal made after the previous pause counts, whatever set its wait: after 60 and 120, a third with ``retry_after`` 100 waits its step (240), a fourth with 1000 waits 1000 (above its step of 480), and a fifth without waits its step, 960."""
    print_section("CDW-017: Retry-After under the doubling")

    assert _streak(cooldowns, clock, "k", 2) == [60.0, 120.0]
    assert _streak(cooldowns, clock, "k", 1, retry_after=100.0) == [240.0]
    assert _streak(cooldowns, clock, "k", 1, retry_after=1_000.0) == [1_000.0]
    assert _streak(cooldowns, clock, "k", 1) == [960.0]
    assert _states(cooldowns)["k"].refusals == 5
    print_success("240, 1000, 960")


def test_a_per_call_base_and_max_apply_to_that_call_only(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-018 — contract 6: four refusals with ``base_seconds=10, max_seconds=40`` wait 10, 20, 40, 40; the fifth, without, uses the instance's 60 s and hour on the same count (960); another key starts at 60."""
    print_section("CDW-018: per-call base and max")

    assert _streak(cooldowns, clock, "k", 4, base_seconds=10.0, max_seconds=40.0) == [10.0, 20.0, 40.0, 40.0]
    assert _streak(cooldowns, clock, "k", 1) == [960.0]
    assert _streak(cooldowns, clock, "other", 1) == [60.0]
    assert _states(cooldowns)["k"].refusals == 5
    print_success("10, 20, 40, 40, then 960 with the instance's values")


@pytest.mark.parametrize(
    ("quiet", "expected", "refusals"),
    [
        pytest.param(3_600.0, 120.0, 2, id="max-later-goes-on"),
        pytest.param(3_600.5, 60.0, 1, id="more-than-max-later-starts-over"),
    ],
)
def test_a_refusal_after_more_than_max_of_quiet_starts_over(cooldowns: Cooldowns, clock: FakeClock, quiet: float, expected: float, refusals: int) -> None:
    """CDW-019 — contract 6: the pause of a first refusal ends at 1060. A refusal exactly an hour (the max) after that is the second in a row; half a second later it is a first one again."""
    print_section(f"CDW-019: a refusal {quiet} s after the end of the pause")

    assert cooldowns.refused("k") == 60.0
    clock.now = 1_060.0 + quiet
    assert cooldowns.check("k") == 0.0
    assert cooldowns.refused("k") == expected
    assert _states(cooldowns)["k"].refusals == refusals
    print_success(f"refusal number {refusals}: {expected} s")


def test_the_quiet_that_starts_over_is_the_max_of_the_call(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-020 — contract 6: with ``max_seconds=40`` given to the calls, 40.5 s of quiet after a pause start the count over; the same quiet under the instance's hour does not."""
    print_section("CDW-020: the quiet period follows the call's max")

    assert cooldowns.refused("short", base_seconds=10.0, max_seconds=40.0) == 10.0
    assert cooldowns.refused("long") == 60.0
    clock.now = 1_010.0 + 40.5
    assert cooldowns.check("short") == 0.0
    assert cooldowns.refused("short", base_seconds=10.0, max_seconds=40.0) == 10.0
    clock.now = 1_060.0 + 40.5
    assert cooldowns.check("long") == 0.0
    assert cooldowns.refused("long") == 120.0
    print_success("short starts over at 10 s, long goes on to 120 s")


# =============================================================================
# 6. refused: THE JITTER, AND THE TRIAL SLOT
# =============================================================================


@pytest.mark.parametrize(
    ("draw", "retry_after", "expected"),
    [
        pytest.param(1.0, None, 66.0, id="top-draw-adds-10-percent"),
        pytest.param(0.5, None, 63.0, id="middle-draw-adds-5-percent"),
        pytest.param(1.0, 500.0, 550.0, id="on-top-of-retry-after"),
        pytest.param(1.0, 80_000.0, 86_400.0, id="never-above-the-hard-max"),
        pytest.param(1.0, 200_000.0, 86_400.0, id="hard-max-floor-unmoved"),
    ],
)
def test_the_jitter_adds_up_to_its_fraction_of_the_wait(clock: FakeClock, draw: float, retry_after: float | None, expected: float) -> None:
    """CDW-021 — contract 6: the wait is ``max(step, floor) × (1 + 0.1 × draw)``, capped at the hard max — a ``Retry-After`` of 500 s with the top draw is 550 s, never less than 500 —, and ``check`` counts that wait."""
    print_section(f"CDW-021: draw {draw}, retry_after {retry_after}")
    cooldowns = Cooldowns(BASE, MAX, clock=clock, rng=lambda: draw)

    assert cooldowns.refused("k", retry_after) == pytest.approx(expected)
    assert cooldowns.check("k") == pytest.approx(expected)
    print_success(f"{expected} s")


def test_the_jitter_applies_above_the_max_too(clock: FakeClock) -> None:
    """CDW-022 — contract 6: the jitter comes after the max — only the hard max bounds it —: with the top draw the doubling reads 66, 132, … 2112, then 3960 s."""
    print_section("CDW-022: jitter on the capped step")
    cooldowns = Cooldowns(BASE, MAX, clock=clock, rng=_highest)

    assert _streak(cooldowns, clock, "k", 8, late=1.0) == pytest.approx([wait * 1.1 for wait in DOUBLING])
    print_success("3600 × 1.1 = 3960 at the top")


def test_the_jitter_never_takes_a_wait_below_retry_after(clock: FakeClock) -> None:
    """CDW-023 — contract 6: one draw per refusal, from 0 to just under 1, on a ``Retry-After`` of 500 s: every wait is ``500 × (1 + 0.1 × draw)``, the lowest exactly 500."""
    print_section("CDW-023: never below the floor")
    draws = [0.0, 0.25, 0.5, 0.75, 0.999]
    cooldowns = Cooldowns(BASE, MAX, clock=clock, rng=itertools.cycle(draws).__next__)

    waits = [cooldowns.refused(("k", index), 500.0) for index in range(len(draws))]
    assert waits == pytest.approx([500.0 * (1 + 0.1 * draw) for draw in draws])
    assert min(waits) == 500.0 and max(waits) < 550.0
    print_success(f"{min(waits)} … {max(waits):.2f} s")


def test_the_jitter_fraction_and_the_hard_max_belong_to_the_instance(clock: FakeClock) -> None:
    """CDW-024 — contract 6: ``jitter=0`` gives exact waits even with the top draw; ``jitter=1`` doubles a wait, and ``hard_max_seconds=7200`` caps both the jittered wait and the floor."""
    print_section("CDW-024: jitter 0 and 1, a hard max of 2 h")

    exact = Cooldowns(BASE, MAX, jitter=0.0, clock=clock, rng=_highest)
    assert _streak(exact, clock, "k", 3) == [60.0, 120.0, 240.0]

    doubling = Cooldowns(BASE, MAX, hard_max_seconds=7_200.0, jitter=1.0, clock=clock, rng=_highest)
    assert doubling.refused("a") == 120.0
    assert doubling.refused("b", 5_000.0) == 7_200.0
    assert doubling.refused("c", 10_000.0) == 7_200.0
    print_success("exact without jitter; 120 s, then 7200 s at most")


def test_a_refused_trial_starts_a_longer_pause_and_frees_the_slot(clock: FakeClock) -> None:
    """CDW-025 — contract 6: with a trial window of 600 s, the trial taken at 1060 is refused there: the key now waits its second pause, 120 s, counted down by ``check``; at 1180 a new trial goes — the old slot went with the refusal, though its window would have lasted until 1660."""
    print_section("CDW-025: a refused trial")
    cooldowns = Cooldowns(BASE, MAX, trial_seconds=600.0, clock=clock, rng=_lowest)
    assert cooldowns.refused("k") == 60.0

    clock.now = 1_060.0
    assert cooldowns.check("k") == 0.0
    assert cooldowns.refused("k") == 120.0
    assert cooldowns.check("k") == 120.0
    clock.now = 1_100.0
    assert cooldowns.check("k") == 80.0
    clock.now = 1_180.0
    assert cooldowns.check("k") == 0.0
    assert cooldowns.check("k") == 600.0
    print_success("120 s counted down, then a new trial")


# =============================================================================
# 7. A RUNNING PAUSE: THE ANSWERS OF CALLS ALREADY IN FLIGHT
# =============================================================================


@pytest.mark.parametrize("trial", [False, True], ids=["no-trial", "trial-taken"])
def test_a_refusal_while_the_pause_runs_counts_nothing_and_a_later_retry_after_extends_it(cooldowns: Cooldowns, clock: FakeClock, trial: bool) -> None:
    """CDW-036 — contract 7, the example of the contract: refused at 1000 → 60 s. At 1010 the refusal of a call in flight counts nothing and answers the 50 s left; one carrying ``Retry-After: 300`` extends the pause to 1310 and answers 300. Once the pause is over — its trial taken or not — the next refusal is the second in a row: 120 s."""
    print_section(f"CDW-036: refusals during a pause, {'a trial taken' if trial else 'no trial'} at its end")

    assert cooldowns.refused("k") == 60.0
    clock.now = 1_010.0
    assert cooldowns.refused("k") == 50.0
    assert _states(cooldowns)["k"].refusals == 1
    assert cooldowns.refused("k", 300.0) == 300.0
    assert cooldowns.check("k") == 300.0
    assert _states(cooldowns)["k"].refusals == 1

    clock.now = 1_309.5
    assert cooldowns.check("k") == 0.5
    clock.now = 1_310.0
    if trial:
        assert cooldowns.check("k") == 0.0
    assert cooldowns.refused("k") == 120.0
    assert _states(cooldowns)["k"].refusals == 2
    print_success("50 s left, extended to 300 s, then the second refusal: 120 s")


def test_a_burst_of_refusals_counts_one(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-037 — contract 7: five calls of one provider in flight together all come back 429 at 1000. The first refusal counts and sets 60 s; the four others count nothing and answer the same 60 s — not 120, 240, 480 and 960. Three more at 1030 answer the 30 s left, though one brings a per-call base and max of 1 s and another a ``Retry-After`` of 10 s: neither shortens the pause. At 1060, no trial taken, the next refusal is the second in a row: 120 s."""
    print_section("CDW-037: a burst of refusals")

    assert [cooldowns.refused("k") for _ in range(5)] == [60.0] * 5
    assert _states(cooldowns) == {"k": CooldownState("k", 1, 60.0, False)}

    clock.now = 1_030.0
    assert cooldowns.refused("k") == 30.0
    assert cooldowns.refused("k", base_seconds=1.0, max_seconds=1.0) == 30.0
    assert cooldowns.refused("k", 10.0) == 30.0
    assert cooldowns.check("k") == 30.0
    assert _states(cooldowns)["k"].refusals == 1

    clock.now = 1_060.0
    assert cooldowns.refused("k") == 120.0
    assert _states(cooldowns)["k"].refusals == 2
    print_success("eight refusals during one pause, one counted; then 120 s")


@pytest.mark.parametrize(
    ("retry_after", "expected"),
    [
        pytest.param(None, 56.0, id="none"),
        pytest.param(30.0, 56.0, id="ending-sooner"),
        pytest.param(56.0, 56.0, id="ending-with-the-pause"),
        pytest.param(300.0, 300.0, id="ending-later"),
        pytest.param(7_200.0, 7_200.0, id="above-the-max"),
        pytest.param(200_000.0, 86_400.0, id="above-the-hard-max"),
        pytest.param(0.0, 56.0, id="zero"),
        pytest.param(-5.0, 56.0, id="negative"),
        pytest.param(math.inf, 56.0, id="inf"),
        pytest.param(math.nan, 56.0, id="nan"),
    ],
)
def test_only_a_retry_after_ending_later_extends_a_running_pause_without_jitter(clock: FakeClock, retry_after: float | None, expected: float) -> None:
    """CDW-038 — contract 7: with the top draw a first refusal at 1000 waits 66 s, until 1066. At 1010 another refusal answers the 56 s left, unless its ``retry_after`` floor — positive and finite, at most the hard max — ends later: then the pause ends exactly ``floor`` from now, an extension taking no jitter (300, not 330). Either way nothing is counted."""
    print_section(f"CDW-038: retry_after {retry_after} during a pause")
    cooldowns = Cooldowns(BASE, MAX, clock=clock, rng=_highest)
    assert cooldowns.refused("k") == pytest.approx(66.0)

    clock.now = 1_010.0
    assert cooldowns.refused("k", retry_after) == pytest.approx(expected)
    assert cooldowns.check("k") == pytest.approx(expected)
    assert _states(cooldowns)["k"].refusals == 1
    print_success(f"{expected} s left, one refusal")


def test_after_an_extension_the_quiet_period_counts_from_the_extended_end(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-039 — contracts 6 and 7: refused at 1000 for 60 s, then extended at 1010 by a ``Retry-After`` of 7200 s, to 8210 — now the end of the pause. A refusal an hour (the max) after 8210 is still the second in a row, 120 s; counted from the first end, 1060, the quiet would have exceeded the max and started over at 60 s."""
    print_section("CDW-039: decay after an extension")

    assert cooldowns.refused("k") == 60.0
    clock.now = 1_010.0
    assert cooldowns.refused("k", 7_200.0) == 7_200.0
    clock.now = 8_210.0 + 3_600.0
    assert cooldowns.check("k") == 0.0
    assert cooldowns.refused("k") == 120.0
    print_success("the second refusal in a row, 120 s")


def test_a_success_while_the_pause_runs_changes_nothing(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-040 — contract 7: refused at 1000 for 60 s. At 1030 the answer of a call that left before arrives, a success: ``succeeded`` returns 0, the pause keeps its 30 s and its refusal; at 1059.5, half a second before the end, the same. At 1060 the pause is over, and the next refusal — no trial taken — is the second in a row: 120 s."""
    print_section("CDW-040: a success during a pause")

    assert cooldowns.refused("k") == 60.0
    clock.now = 1_030.0
    assert cooldowns.succeeded("k") == 0
    assert _states(cooldowns) == {"k": CooldownState("k", 1, 30.0, False)}
    assert cooldowns.check("k") == 30.0
    clock.now = 1_059.5
    assert cooldowns.succeeded("k") == 0
    assert cooldowns.check("k") == 0.5

    clock.now = 1_060.0
    assert cooldowns.refused("k") == 120.0
    assert _states(cooldowns)["k"].refusals == 2
    print_success("0 returned twice, the pause and its count kept; then 120 s")


# =============================================================================
# 8. A CLOCK GOING BACKWARDS
# =============================================================================


def test_a_clock_going_backwards_never_lengthens_a_wait(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-026 — contract 8: refused at 1000 for 60 s, then the clock is set back to 999, 900, even 0: the key still waits the 60 s recorded, never ``1060 - now``. A refusal arriving at 0 falls in the pause: it counts nothing and answers the same 60 s. At 1060 the pause is over as it was due, and the next refusal is the second in a row, 120 s."""
    print_section("CDW-026: a clock going backwards")

    assert cooldowns.refused("k") == 60.0
    for earlier in (999.0, 900.0, 0.0):
        clock.now = earlier
        assert cooldowns.check("k") == 60.0, f"at {earlier}"
    assert cooldowns.refused("k") == 60.0
    assert _states(cooldowns)["k"].refusals == 1

    clock.now = 1_060.0
    assert cooldowns.check("k") == 0.0
    assert cooldowns.refused("k") == 120.0
    print_success("60 s at most, over at 1060, then the second refusal")


# =============================================================================
# 9. succeeded AND released
# =============================================================================


@pytest.mark.parametrize("trial", [False, True], ids=["no-trial", "trial-taken"])
def test_once_the_pause_is_over_succeeded_forgets_the_key_and_returns_its_refusals(cooldowns: Cooldowns, clock: FakeClock, trial: bool) -> None:
    """CDW-027 — contract 9: three refusals in a row, then, once the last pause is over — its trial taken or not —, a success: 3, the key forgotten — no trial gate left —, and its next refusal is a first one again; an unknown or already forgotten key returns 0 and is not tracked."""
    print_section(f"CDW-027: succeeded after the pause, {'a trial taken' if trial else 'no trial'}")

    assert _streak(cooldowns, clock, "k", 3) == [60.0, 120.0, 240.0]
    if trial:
        assert cooldowns.check("k") == 0.0
    assert cooldowns.succeeded("k") == 3
    assert (cooldowns.check("k"), cooldowns.check("k")) == (0.0, 0.0)
    assert len(cooldowns) == 0
    assert (cooldowns.succeeded("k"), cooldowns.succeeded("never-seen")) == (0, 0)
    assert len(cooldowns) == 0
    assert cooldowns.refused("k") == 60.0
    print_success("3 refusals returned, the key forgotten")


def test_released_frees_the_trial_slot_and_keeps_the_count(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-028 — contract 9: at the end of a pause trial A goes and B waits; A ends without a verdict (a timeout): after ``released`` caller C takes the slot and D waits for it; C refused is the second refusal in a row, 120 s."""
    print_section("CDW-028: released")

    assert cooldowns.refused("k") == 60.0
    clock.now = 1_060.0
    assert cooldowns.check("k") == 0.0
    assert cooldowns.check("k") == 60.0
    assert cooldowns.released("k") is None
    assert cooldowns.check("k") == 0.0
    assert cooldowns.check("k") == 60.0
    assert cooldowns.refused("k") == 120.0
    print_success("slot freed, count kept")


def test_released_never_shortens_a_pause_and_ignores_an_unknown_key(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-029 — contracts 7 and 9: ``released`` on a key never refused raises nothing and tracks nothing; on a key 10 s into a pause of 60 — a call that started before the refusal, ending without a verdict — it changes nothing: the key still waits 50 s, its refusal counted."""
    print_section("CDW-029: released outside a trial")

    assert cooldowns.released("never-seen") is None
    assert len(cooldowns) == 0
    assert cooldowns.refused("k") == 60.0
    clock.now = 1_010.0
    cooldowns.released("k")
    assert cooldowns.check("k") == 50.0
    assert _states(cooldowns)["k"].refusals == 1
    print_success("the pause stands")


# =============================================================================
# 10. snapshot, KEYS, reset, len
# =============================================================================


def test_snapshot_gives_one_state_per_key(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-030 — contract 10: ``a`` and ``b`` refused at 1000; ``b``'s trial at 1060 refused again (120 s); ``a``'s trial taken at 1100. Each snapshot holds both keys with their refusals, the seconds left of their pause — 0 once it is over, never negative — and whether a trial is in flight, which stops once its window of 60 s has run out."""
    print_section("CDW-030: snapshot")

    assert cooldowns.snapshot() == ()
    cooldowns.refused("a")
    cooldowns.refused("b")
    clock.now = 1_030.0
    assert _states(cooldowns) == {"a": CooldownState("a", 1, 30.0, False), "b": CooldownState("b", 1, 30.0, False)}

    clock.now = 1_060.0
    assert cooldowns.check("b") == 0.0
    assert cooldowns.refused("b") == 120.0
    clock.now = 1_100.0
    assert cooldowns.check("a") == 0.0
    assert _states(cooldowns) == {"a": CooldownState("a", 1, 0.0, True), "b": CooldownState("b", 2, 80.0, False)}

    clock.now = 1_170.0
    assert _states(cooldowns) == {"a": CooldownState("a", 1, 0.0, False), "b": CooldownState("b", 2, 10.0, False)}
    print_success("refusals, remaining clamped at 0, trial_in_flight while its window lasts")


def test_keys_are_independent_and_any_hashable_is_one(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-031 — contract 10: provider tuples that differ by scope or domain, and ``None``, refused 10 s apart, each wait their own time; a shorter tuple or a string never refused waits nothing. At 1075 the pauses of the first two are over: a success of the second forgets it alone — the first lets its own trial through, the last two are still paused."""
    print_section("CDW-031: independent keys")
    keys = [("asset", "yfinance", None), ("asset", "yfinance", "example.com"), ("fx", "ECB", None), None]

    for offset, key in enumerate(keys):
        clock.now = START + 10.0 * offset
        assert cooldowns.refused(key) == 60.0
    clock.now = 1_040.0
    assert [cooldowns.check(key) for key in keys] == [20.0, 30.0, 40.0, 50.0]
    assert (cooldowns.check(("asset", "yfinance")), cooldowns.check("plain")) == (0.0, 0.0)

    clock.now = 1_075.0
    assert cooldowns.succeeded(keys[1]) == 1
    assert [cooldowns.check(key) for key in keys] == [0.0, 0.0, 5.0, 15.0]
    assert len(cooldowns) == 3
    print_success("four keys, four pauses; one success, one key forgotten")


def test_reset_forgets_one_key_and_len_counts_the_rest(cooldowns: Cooldowns) -> None:
    """CDW-032 — contract 10: ``len`` counts the keys tracked; ``reset`` forgets one (``None`` included, an unknown key quietly) with its refusals, and leaves the others as they were."""
    print_section("CDW-032: reset, len")

    for key in ("a", "b", None):
        cooldowns.refused(key)
    assert len(cooldowns) == 3

    cooldowns.reset("a")
    assert len(cooldowns) == 2
    assert (cooldowns.check("a"), cooldowns.check("b")) == (0.0, 60.0)
    cooldowns.reset("never-seen")
    cooldowns.reset(None)
    assert len(cooldowns) == 1
    assert cooldowns.check(None) == 0.0
    assert cooldowns.refused("a") == 60.0
    print_success("reset one, the others kept")


# =============================================================================
# 11. BOUNDED MEMORY
# =============================================================================


def test_a_new_key_beyond_max_keys_evicts_the_least_recently_used(clock: FakeClock) -> None:
    """CDW-033 — contract 11: with room for two, checking an unknown key takes no room; refusing ``c`` evicts ``a``, the key nobody used since, and ``a`` comes back as a first refusal."""
    print_section("CDW-033: eviction")
    cooldowns = Cooldowns(BASE, MAX, max_keys=2, clock=clock, rng=_lowest)

    cooldowns.refused("a")
    cooldowns.refused("b")
    assert cooldowns.check("unknown") == 0.0
    assert set(_states(cooldowns)) == {"a", "b"}

    cooldowns.refused("c")
    assert set(_states(cooldowns)) == {"b", "c"}
    assert cooldowns.check("a") == 0.0
    assert cooldowns.refused("a") == 60.0
    assert len(cooldowns) == 2
    print_success("a evicted, and forgotten")


@pytest.mark.parametrize(
    ("use", "moment", "refusals"),
    [
        pytest.param("check", START, 1, id="checked-during-its-pause"),
        pytest.param("refused", START, 1, id="refused-during-its-pause"),
        pytest.param("refused", 1_060.0, 2, id="refused-after-its-pause"),
    ],
)
def test_checking_or_refusing_a_key_keeps_it(clock: FakeClock, use: str, moment: float, refusals: int) -> None:
    """CDW-034 — contract 11: checking or refusing ``a`` makes ``b`` the least recently used, so ``c`` evicts ``b``. A refusal while ``a``'s pause runs counts nothing (contract 7), but uses the key all the same: a provider still answering 429 is the last one whose pause should be forgotten."""
    print_section(f"CDW-034: {use} at {moment} keeps a key")
    cooldowns = Cooldowns(BASE, MAX, max_keys=2, clock=clock, rng=_lowest)

    cooldowns.refused("a")
    cooldowns.refused("b")
    clock.now = moment
    getattr(cooldowns, use)("a")
    cooldowns.refused("c")
    states = _states(cooldowns)
    assert set(states) == {"a", "c"}
    assert states["a"].refusals == refusals
    print_success(f"{use}('a') → b evicted, a at {refusals} refusal(s)")


# =============================================================================
# 12. THREADS
# =============================================================================


def test_concurrent_checks_let_exactly_one_trial_through(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-035 — contract 12: once a pause is over, 8 threads released together by a barrier check one key 25 times each: exactly one ``check`` is 0, the other 199 wait the trial window, and the snapshot shows the trial in flight. With the switch interval lowered, a test-then-take of the slot without the lock gets every chance to let a second trial through."""
    print_section("CDW-035: thread safety, checks")
    workers, checks_each = 8, 25
    assert cooldowns.refused("shared") == 60.0
    clock.now = 1_060.0

    results = _race(workers, checks_each, lambda: cooldowns.check("shared"), "cdw-035")

    assert results.count(0.0) == 1, f"{results.count(0.0)} trials let through at once"
    assert sorted(results) == [0.0] + [60.0] * (workers * checks_each - 1)
    assert _states(cooldowns)["shared"].trial_in_flight
    print_success(f"1 trial of {workers * checks_each} checks, the others told to wait 60 s")


def test_concurrent_refusals_once_a_pause_is_over_count_one(cooldowns: Cooldowns, clock: FakeClock) -> None:
    """CDW-041 — contracts 7 and 12: once a pause is over, 8 threads released together by a barrier refuse one key 25 times each, at the same instant. The first refusal to get in is the second in a row and sets 120 s; every other one falls in that new pause, counts nothing and answers its 120 s. So all 200 answers are 120, the snapshot counts 2 refusals, and ``check`` waits 120 s: a test-then-count without the lock would count a burst, and double the wait for each."""
    print_section("CDW-041: thread safety, refusals")
    workers, refusals_each = 8, 25
    assert cooldowns.refused("shared") == 60.0
    clock.now = 1_060.0

    results = _race(workers, refusals_each, lambda: cooldowns.refused("shared"), "cdw-041")

    assert results == [120.0] * (workers * refusals_each), f"answers other than 120 s: {sorted(set(results))}"
    assert _states(cooldowns)["shared"].refusals == 2
    assert cooldowns.check("shared") == 120.0
    print_success(f"{workers * refusals_each} refusals at once, one counted: 120 s")
