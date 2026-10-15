"""
The app's startup and shutdown, its middleware and its static site (workstream H, platform, checkpoint CP2b).

Under test: ``backend/app/services/platform/lifecycle.py`` (the runner of the steps), ``app_lifespan.py`` (the app's
steps), ``middleware.py`` and ``static_site.py``, cut out of ``backend/app/main.py``. The contract:

(a) Startup: the steps run in order, each to its end; what ``run()`` returns is awaited when it is a coroutine or a
    ``Task``, ignored when it is a plain value (a watchdog, say); ``blocking`` changes nothing. An exception stops the
    startup: it propagates and the later steps never run. ``current_step()`` is ``"startup:<name>"`` inside a step and
    ``None`` after, an exception included.
(b) Shutdown without a deadline: every step runs, in order, to its end, a blocking one on the event loop's thread; a
    plain value a step returns is ignored, here and under a deadline, blocking or not. A step that raises is reported
    (``error``, its repr) and logged as an error, and the next steps still run; every outcome is ``finished``.
    ``current_step()`` is ``"shutdown:<name>"`` inside a step, read from a worker thread too, ``None`` after.
(c) Shutdown under a deadline (an instant on ``time.monotonic()``): a step past it is cut, ``finished`` False and a
    warning logged, and the next step runs; a ``Task`` it returned is cancelled; a blocking step runs in a worker thread,
    left behind when it is cut, and a coroutine its ``run()`` returns is awaited, as without a deadline, never dropped
    un-awaited; a step that is not blocking stays on the event loop. A deadline already past still gives each step
    ``MIN_STEP_SECONDS``: a quick step finishes. A step raising a ``TimeoutError`` of its own is an error, not a cut.
(d) The app's steps (``app_lifespan``), never run as a whole: the names unique in each tuple, and across
    ``FINALLY_STEPS`` and ``SHUTDOWN_STEPS``, which both report as ``shutdown:<name>``; every ``run`` callable without
    arguments; the steps of CP2b keep their relative order, checked as a subsequence so that a workstream adds a
    step, and a test of its own constraint with ``assert_in_relative_order``, without touching this file's tests;
    ``FINALLY_STEPS`` is the tool executor alone; the BRIM parse pool is released off the event loop under a deadline;
    no shutdown deadline yet. A step reaches its function through the module's name when it runs, so
    ``monkeypatch.setattr(app_lifespan, "<name>", ...)`` replaces it.
(e) Middleware: GZip outside CORS, with their options; ``install_middleware`` adds any stack with its first entry
    outermost; the app of ``backend.app.main`` carries ``MIDDLEWARE_STACK``.
(f) Static site: ``install_static_site`` registers ``/mkdocs``, ``/mkdocs/{path:path}``, ``/``, the ``/_app`` mount when the
    build has ``index.html`` and ``_app/``, the SPA catch-all last. On the app of ``backend.app.main``, imported as
    ``test_static_route_confinement`` imports it, the catch-all is the last route and the site comes after every
    ``/api/v1`` route.

Pure: no database, no server, no network; the app's lifespan never runs. Every wait is bounded by an event or a deadline
of a few tenths of a second, and no assertion depends on an exact duration. The runner's log is read with
``structlog.testing.capture_logs`` behind a barrier: a canary logged through the runner's own logger must reach the
capture, or "nothing was logged" would prove nothing. A coroutine never awaited is looked for the same way, with
``warnings.catch_warnings``: a canary coroutine dropped un-awaited must be reported.
"""

from __future__ import annotations

import asyncio
import gc
import inspect
import threading
import time
import warnings
import weakref
from collections.abc import Coroutine, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.routing import iter_route_contexts
from starlette.routing import Mount
from structlog.testing import capture_logs

import backend.app.main as app_main
from backend.app.config import API_V1_PREFIX
from backend.app.services.platform import app_lifespan, lifecycle, static_site
from backend.app.services.platform.lifecycle import MIN_STEP_SECONDS, Step, current_step, run_shutdown_steps, run_startup_steps
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, MiddlewareEntry, install_middleware
from backend.test_scripts.test_utils import print_section, print_success

#: The startup steps of CP2b, in their order. A step a workstream adds may stand anywhere among them: the order of these
#: is what is kept (``assert_in_relative_order``), never the whole tuple.
CORE_STARTUP_ORDER = (
    "announce",
    "configuration-checks",
    "signal-plugins",
    "tool-catalog",
    "data-directories",
    "risk-scenarios",
    "default-avatars",
    "database",
    "post-migration-fixes",
    "global-settings",
    "provider-prewarm",
    "market-holidays",
    "scheduler",
)

#: The shutdown steps of CP2b, in their order, kept the same way.
CORE_SHUTDOWN_ORDER = ("scheduler", "providers", "brim-parse-pool", "quant-pools", "market-holidays", "caches")

#: A deadline this close has passed before a stuck step ends: the step gets ``MIN_STEP_SECONDS``, then it is cut.
SHORT_SECONDS = 0.05
#: Far more than any step of these tests takes: under it nothing is cut.
GENEROUS_SECONDS = 5.0
#: The longest a worker thread held by a test waits for its release: never a thread left blocked for good.
THREAD_HOLD_SECONDS = 10.0

FAILED_EVENT = "Shutdown step failed"
CUT_EVENT = "Shutdown step cut by the deadline"
LOG_CANARY = "app-lifecycle test: canary through the runner's logger"

#: A value a step returns that is not awaitable, as a ``shutdown-watchdog`` startup step returns the watchdog it installs:
#: the runners ignore it, at startup and at shutdown, under a deadline or not, blocking or not.
PLAIN_VALUE = SimpleNamespace(kind="watchdog")


# =============================================================================
# HELPERS
# =============================================================================


def step_names(steps: Sequence[Step]) -> list[str]:
    """The names of ``steps``, in their order."""
    return [step.name for step in steps]


def assert_in_relative_order(steps: Sequence[Step], expected: Sequence[str], what: str = "steps") -> None:
    """The names ``expected`` are among ``steps``, in this relative order; any other step may stand before, between or after.

    A workstream checks a constraint of its own with it, in a test of its own: a step that must run between two others is
    ``assert_in_relative_order(app_lifespan.STARTUP_STEPS, ("tool-catalog", "pending-restore", "data-directories"))``.
    """
    names = step_names(steps)
    missing = [name for name in expected if name not in names]
    assert not missing, f"{what}: {missing} missing from {names}"
    positions = [names.index(name) for name in expected]
    assert positions == sorted(positions), f"{what}: {list(expected)} must keep this relative order, found {[names[position] for position in sorted(positions)]} in {names}"


def _step(steps: Sequence[Step], name: str) -> Step:
    """The one step called ``name``."""
    matching = [step for step in steps if step.name == name]
    assert len(matching) == 1, f"{len(matching)} steps named {name!r} in {step_names(steps)}"
    return matching[0]


@contextmanager
def _runner_log() -> Iterator[list[dict[str, Any]]]:
    """What the runner logs inside the block, behind a barrier: a canary logged through its own logger must arrive first."""
    with capture_logs() as events:
        lifecycle.logger.debug(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the runner's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


def _logged(events: list[dict[str, Any]], event: str) -> list[tuple[Any, Any]]:
    """``(step, level)`` of every captured ``event``, in order."""
    return [(entry.get("step"), entry.get("log_level")) for entry in events if entry.get("event") == event]


def _record_current_step(seen: list[str | None]) -> None:
    seen.append(current_step())


async def _never_awaited_canary() -> None:
    """Dropped un-awaited on purpose: its warning proves that a capture sees the warning of a coroutine never awaited."""


async def _until_collected(ref: weakref.ref[Any], what: str) -> None:
    """Collect garbage until the object ``ref`` names is gone, within a deadline: by then it has been finalized."""
    deadline = time.monotonic() + GENEROUS_SECONDS
    while ref() is not None:
        assert time.monotonic() < deadline, f"{what} was still alive {GENEROUS_SECONDS}s later"
        gc.collect()
        await asyncio.sleep(0.01)


# =============================================================================
# (a) STARTUP
# =============================================================================


@pytest.mark.asyncio
async def test_startup_runs_the_steps_in_order_and_awaits_what_they_return() -> None:
    print_section("Startup: steps in order, coroutines and tasks awaited, a plain value ignored")
    ran: list[str] = []

    async def coroutine() -> None:
        await asyncio.sleep(0)
        ran.append("coroutine")

    async def task_body() -> None:
        await asyncio.sleep(0)
        ran.append("task")

    def returns_a_plain_value() -> SimpleNamespace:
        ran.append("value")
        return PLAIN_VALUE

    steps = (
        Step("sync", lambda: ran.append("sync")),
        Step("coroutine", coroutine),
        Step("task", lambda: asyncio.get_running_loop().create_task(task_body())),
        Step("value", returns_a_plain_value),
        Step("last", lambda: ran.append("last")),
    )

    await run_startup_steps(steps)

    # A task left running would let "last" in before "task"; a coroutine never awaited would never append; a plain value
    # awaited would raise before "last".
    assert ran == ["sync", "coroutine", "task", "value", "last"]
    print_success("✓ every step ran to its end before the next one, the plain value ignored")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["sync", "coroutine"])
async def test_startup_stops_at_the_first_step_that_raises(kind: str) -> None:
    print_section(f"Startup: a {kind} step that raises stops the startup")
    ran: list[str] = []

    def broken_sync() -> None:
        ran.append("broken")
        raise RuntimeError("provoked: this step fails")

    async def broken_coroutine() -> None:
        await asyncio.sleep(0)
        ran.append("broken")
        raise RuntimeError("provoked: this step fails")

    steps = (
        Step("first", lambda: ran.append("first")),
        Step("broken", broken_sync if kind == "sync" else broken_coroutine),
        Step("never", lambda: ran.append("never")),
    )

    with pytest.raises(RuntimeError, match="provoked: this step fails"):
        await run_startup_steps(steps)

    assert ran == ["first", "broken"]
    assert current_step() is None, f"after a startup step raised, the step in progress still reads {current_step()!r}"
    print_success("✓ the exception propagated, the later step never ran, no step left in progress")


@pytest.mark.asyncio
async def test_startup_names_the_step_in_progress() -> None:
    print_section("Startup: current_step() inside a step and after")
    assert current_step() is None, f"precondition: a previous run left {current_step()!r} in progress"
    seen: list[str | None] = []

    async def beta() -> None:
        await asyncio.sleep(0)
        _record_current_step(seen)

    await run_startup_steps((Step("alpha", lambda: _record_current_step(seen)), Step("beta", beta)))

    assert seen == ["startup:alpha", "startup:beta"]
    assert current_step() is None
    print_success("✓ startup:<name> inside each step, None after")


@pytest.mark.asyncio
async def test_startup_runs_a_blocking_step_on_the_event_loop_thread() -> None:
    print_section("Startup: blocking changes nothing")
    loop_thread = threading.get_ident()
    threads: list[int] = []

    await run_startup_steps((Step("blocking", lambda: threads.append(threading.get_ident()), blocking=True),))

    assert threads == [loop_thread]
    print_success("✓ a blocking step runs inline at startup")


# =============================================================================
# (b) SHUTDOWN WITHOUT A DEADLINE
# =============================================================================


@pytest.mark.asyncio
async def test_shutdown_without_a_deadline_runs_every_step_in_order_past_one_that_raises() -> None:
    print_section("Shutdown, no deadline: a step that raises skips nothing")
    ran: list[str] = []
    failure = RuntimeError("provoked: this step fails")

    async def coroutine() -> None:
        await asyncio.sleep(0)
        ran.append("coroutine")

    async def task_body() -> None:
        await asyncio.sleep(0)
        ran.append("task")

    def broken() -> None:
        ran.append("broken")
        raise failure

    steps = (
        Step("first", lambda: ran.append("first")),
        Step("broken", broken),
        Step("coroutine", coroutine),
        Step("task", lambda: asyncio.get_running_loop().create_task(task_body())),
        Step("last", lambda: ran.append("last")),
    )

    with _runner_log() as events:
        outcomes = await run_shutdown_steps(steps)

    assert ran == ["first", "broken", "coroutine", "task", "last"]
    assert [outcome.name for outcome in outcomes] == step_names(steps)
    assert all(outcome.finished for outcome in outcomes), outcomes
    assert {outcome.name: outcome.error for outcome in outcomes if outcome.error is not None} == {"broken": repr(failure)}
    assert all(outcome.seconds >= 0 for outcome in outcomes), outcomes
    assert _logged(events, FAILED_EVENT) == [("broken", "error")]
    assert _logged(events, CUT_EVENT) == []
    print_success("✓ the failure is reported and logged as an error, every later step ran")


@pytest.mark.asyncio
@pytest.mark.parametrize("deadline_in", [None, GENEROUS_SECONDS], ids=["no-deadline", "under-a-deadline"])
async def test_shutdown_names_the_step_in_progress(deadline_in: float | None) -> None:
    print_section("Shutdown: current_step() inside a step, a worker thread included, and after")
    assert current_step() is None, f"precondition: a previous run left {current_step()!r} in progress"
    seen: list[str | None] = []

    async def beta() -> None:
        await asyncio.sleep(0)
        _record_current_step(seen)

    def broken() -> None:
        _record_current_step(seen)
        raise RuntimeError("provoked: this step fails")

    steps = (
        Step("alpha", lambda: _record_current_step(seen)),
        Step("beta", beta),
        Step("gamma", lambda: _record_current_step(seen), blocking=True),
        Step("broken", broken),
    )
    deadline = None if deadline_in is None else time.monotonic() + deadline_in

    with _runner_log():
        await run_shutdown_steps(steps, deadline)

    assert seen == ["shutdown:alpha", "shutdown:beta", "shutdown:gamma", "shutdown:broken"]
    assert current_step() is None, f"after the shutdown, the step in progress still reads {current_step()!r}"
    print_success("✓ shutdown:<name> inside each step, None after, a raising step included")


@pytest.mark.asyncio
@pytest.mark.parametrize("returned", [None, PLAIN_VALUE], ids=["returns-none", "returns-a-plain-value"])
@pytest.mark.parametrize(
    ("deadline_in", "blocking", "on_the_loop"),
    [
        pytest.param(None, False, True, id="no-deadline-not-blocking-on-the-loop"),
        pytest.param(None, True, True, id="no-deadline-blocking-on-the-loop"),
        pytest.param(GENEROUS_SECONDS, True, False, id="deadline-blocking-in-a-worker-thread"),
        pytest.param(GENEROUS_SECONDS, False, True, id="deadline-not-blocking-on-the-loop"),
    ],
)
async def test_where_a_shutdown_step_runs(deadline_in: float | None, blocking: bool, on_the_loop: bool, returned: object) -> None:
    print_section(f"Shutdown: the thread a step runs on, the step returning {returned!r}")
    loop_thread = threading.get_ident()
    threads: list[int] = []
    deadline = None if deadline_in is None else time.monotonic() + deadline_in

    def where() -> object:
        threads.append(threading.get_ident())
        return returned  # not awaitable: the runner ignores it, whatever the deadline and the thread

    outcomes = await run_shutdown_steps((Step("where", where, blocking=blocking),), deadline)

    assert [(outcome.name, outcome.finished, outcome.error) for outcome in outcomes] == [("where", True, None)], f"a step returning {returned!r}: a value that is not awaitable is ignored, never an error"
    assert len(threads) == 1
    assert (threads[0] == loop_thread) is on_the_loop, f"blocking={blocking}, deadline={deadline_in}: the step ran {'off' if on_the_loop else 'on'} the event loop's thread"
    print_success("✓ blocking steps leave the loop only under a deadline, and a plain value they return is ignored")


# =============================================================================
# (c) SHUTDOWN UNDER A DEADLINE
# =============================================================================


@pytest.mark.asyncio
async def test_a_step_past_the_deadline_is_cut_and_the_next_step_still_runs() -> None:
    print_section("Shutdown, deadline: a stuck step is cut")
    never = asyncio.Event()
    ran: list[str] = []

    with _runner_log() as events:
        outcomes = await run_shutdown_steps((Step("stuck", never.wait), Step("next", lambda: ran.append("next"))), deadline=time.monotonic() + SHORT_SECONDS)

    assert [(outcome.name, outcome.finished, outcome.error) for outcome in outcomes] == [("stuck", False, None), ("next", True, None)]
    assert ran == ["next"]
    cuts = [entry for entry in events if entry.get("event") == CUT_EVENT]
    assert [(entry.get("step"), entry.get("log_level")) for entry in cuts] == [("stuck", "warning")]
    assert isinstance(cuts[0].get("seconds"), float), cuts[0]
    assert _logged(events, FAILED_EVENT) == []
    print_success("✓ cut, logged as a warning, and the next step ran")


@pytest.mark.asyncio
async def test_a_task_cut_by_the_deadline_is_cancelled() -> None:
    print_section("Shutdown, deadline: a cut task is cancelled")
    never = asyncio.Event()
    started: list[asyncio.Task] = []

    def start() -> asyncio.Task:
        task = asyncio.get_running_loop().create_task(never.wait())
        started.append(task)
        return task

    try:
        with _runner_log():
            outcomes = await run_shutdown_steps((Step("task", start),), deadline=time.monotonic() + SHORT_SECONDS)

        assert [(outcome.name, outcome.finished) for outcome in outcomes] == [("task", False)]
        assert len(started) == 1
        done, _pending = await asyncio.wait(started, timeout=GENEROUS_SECONDS)
        assert started[0] in done and started[0].cancelled(), f"the cut task did not end cancelled: {started[0]!r}"
    finally:
        for task in started:
            task.cancel()
    print_success("✓ the task was cancelled")


@pytest.mark.asyncio
async def test_a_blocking_step_cut_by_the_deadline_is_left_to_its_thread_and_the_next_step_runs() -> None:
    print_section("Shutdown, deadline: a blocking step past it")
    started, release, ended = threading.Event(), threading.Event(), threading.Event()
    ran: list[str] = []

    def held() -> None:
        started.set()
        release.wait(timeout=THREAD_HOLD_SECONDS)
        ended.set()

    try:
        with _runner_log():
            outcomes = await run_shutdown_steps((Step("held", held, blocking=True), Step("next", lambda: ran.append("next"))), deadline=time.monotonic() + SHORT_SECONDS)

        assert started.is_set(), "barrier: the blocking step never started in its thread, so the cut proves nothing"
        assert not ended.is_set(), "the thread ended before the runner moved on: the cut proves nothing"
        assert [(outcome.name, outcome.finished) for outcome in outcomes] == [("held", False), ("next", True)]
        assert ran == ["next"]
    finally:
        release.set()
    assert await asyncio.to_thread(ended.wait, GENEROUS_SECONDS), "the released thread never ended"
    print_success("✓ the runner moved on without the thread, which ended once released")


@pytest.mark.asyncio
async def test_a_deadline_already_past_still_gives_each_step_the_minimum() -> None:
    print_section("Shutdown, deadline already past: MIN_STEP_SECONDS per step")
    never = asyncio.Event()
    ran: list[str] = []
    steps = (
        Step("quick", lambda: ran.append("quick")),
        Step("slow", never.wait),
        Step("after", lambda: ran.append("after")),
    )

    with _runner_log():
        outcomes = await run_shutdown_steps(steps, deadline=time.monotonic() - 60)

    by_name = {outcome.name: outcome for outcome in outcomes}
    assert ran == ["quick", "after"]
    assert by_name["quick"].finished and by_name["after"].finished
    assert by_name["slow"].finished is False
    assert MIN_STEP_SECONDS / 2 <= by_name["slow"].seconds < 5, f"the slow step got {by_name['slow'].seconds:.3f}s, not about {MIN_STEP_SECONDS}s"
    print_success("✓ the quick steps finished, the slow one got about the minimum")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["coroutine", "blocking"])
async def test_a_step_raising_a_timeout_of_its_own_is_an_error_not_a_cut(kind: str) -> None:
    print_section(f"Shutdown, deadline: a {kind} step raising its own TimeoutError")
    never = asyncio.Event()
    ran: list[str] = []

    async def gives_up_on_its_own() -> None:
        async with asyncio.timeout(0.01):
            await never.wait()

    def times_out() -> None:
        raise TimeoutError("provoked: the step's own timeout")

    own = Step("own-timeout", gives_up_on_its_own) if kind == "coroutine" else Step("own-timeout", times_out, blocking=True)

    with _runner_log() as events:
        outcomes = await run_shutdown_steps((own, Step("next", lambda: ran.append("next"))), deadline=time.monotonic() + GENEROUS_SECONDS)

    by_name = {outcome.name: outcome for outcome in outcomes}
    assert by_name["own-timeout"].finished is True
    assert by_name["own-timeout"].error is not None and "TimeoutError" in by_name["own-timeout"].error
    assert ran == ["next"]
    assert _logged(events, FAILED_EVENT) == [("own-timeout", "error")]
    assert _logged(events, CUT_EVENT) == []
    print_success("✓ reported and logged as an error, not as a cut")


@pytest.mark.asyncio
async def test_a_blocking_step_under_a_deadline_has_the_coroutine_it_returns_awaited() -> None:
    """Under a deadline a blocking ``run()`` runs in a worker thread, and a coroutine it returns is awaited, as without one.

    No coroutine may be dropped un-awaited. That absence proves something only if the capture sees such a warning and
    the coroutine was finalized while it listened: a canary coroutine dropped un-awaited inside the block must be
    reported, and the coroutine ``run()`` returned must be gone before the block ends. ``simplefilter("error")`` would
    prove nothing: the warning is raised in the coroutine's finalizer, where an error goes to ``sys.unraisablehook``
    and never reaches the test.
    """
    print_section("Shutdown, deadline: a blocking step whose run() returns a coroutine")
    loop_thread = threading.get_ident()
    run_threads: list[int] = []
    returned: list[weakref.ref[Any]] = []
    ran: list[str] = []

    async def append_marker() -> None:
        await asyncio.sleep(0)
        ran.append("coroutine")

    def start() -> Coroutine[Any, Any, None]:
        run_threads.append(threading.get_ident())
        coroutine = append_marker()
        returned.append(weakref.ref(coroutine))
        return coroutine

    gc.collect()  # the garbage of earlier tests is finalized, and warned about, before the capture starts
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", RuntimeWarning)
        canary = _never_awaited_canary()
        canary_ref = weakref.ref(canary)
        del canary
        outcomes = await run_shutdown_steps((Step("returns-a-coroutine", start, blocking=True),), deadline=time.monotonic() + GENEROUS_SECONDS)
        ran_when_the_shutdown_ended = list(ran)
        assert len(returned) == 1, f"run() was called {len(returned)} times"
        await _until_collected(canary_ref, "the canary coroutine")
        await _until_collected(returned[0], "the coroutine run() returned")
    never_awaited = [str(entry.message) for entry in caught if issubclass(entry.category, RuntimeWarning) and "was never awaited" in str(entry.message)]
    canary_name = _never_awaited_canary.__qualname__

    assert run_threads and run_threads[0] != loop_thread, "barrier: run() ran on the event loop's thread, so the worker-thread path of a deadline was never taken"
    assert any(canary_name in message for message in never_awaited), f"barrier: the canary dropped un-awaited was not reported, so the capture would miss the warning: {never_awaited}"
    assert [(outcome.name, outcome.finished, outcome.error) for outcome in outcomes] == [("returns-a-coroutine", True, None)]
    assert ran_when_the_shutdown_ended == ["coroutine"], "the coroutine run() returned had not run to its end when the shutdown ended"
    assert [message for message in never_awaited if canary_name not in message] == [], "a coroutine was dropped un-awaited"
    print_success("✓ the coroutine was awaited to its end, none dropped un-awaited")


# =============================================================================
# (d) THE APP'S STEPS
# =============================================================================


@pytest.mark.parametrize("tuple_name", ["STARTUP_STEPS", "FINALLY_STEPS", "SHUTDOWN_STEPS"])
def test_the_names_are_unique_and_every_step_runs_without_arguments(tuple_name: str) -> None:
    print_section(f"{tuple_name}: unique names, run() without arguments")
    steps = getattr(app_lifespan, tuple_name)
    assert steps and all(isinstance(step, Step) for step in steps), f"{tuple_name} must be a non-empty tuple of Step"
    names = step_names(steps)
    assert len(set(names)) == len(names), f"{tuple_name}: a name used twice in {names}"
    for step in steps:
        assert callable(step.run), f"{tuple_name} {step.name!r}: run is not callable"
        try:
            inspect.signature(step.run).bind()
        except TypeError as exc:
            pytest.fail(f"{tuple_name} {step.name!r}: run() cannot be called without arguments ({exc})")
    print_success(f"✓ {len(names)} steps")


def test_finally_and_shutdown_steps_never_share_a_name() -> None:
    print_section("FINALLY_STEPS and SHUTDOWN_STEPS together: each name once")
    names = step_names(app_lifespan.FINALLY_STEPS) + step_names(app_lifespan.SHUTDOWN_STEPS)
    shared = sorted({name for name in names if names.count(name) > 1})
    assert not shared, f"{shared} used more than once across FINALLY_STEPS and SHUTDOWN_STEPS: both report as shutdown:<name> to current_step(), so a watchdog reading it could not tell which of them is in progress"
    print_success(f"✓ {len(names)} shutdown steps, each under its own name")


def test_the_steps_of_cp2b_keep_their_relative_order() -> None:
    print_section("The steps of CP2b keep their relative order")
    assert_in_relative_order(app_lifespan.STARTUP_STEPS, CORE_STARTUP_ORDER, "STARTUP_STEPS")
    assert_in_relative_order(app_lifespan.SHUTDOWN_STEPS, CORE_SHUTDOWN_ORDER, "SHUTDOWN_STEPS")
    assert step_names(app_lifespan.FINALLY_STEPS) == ["tool-executor"]
    print_success("✓ startup and shutdown keep the order of CP2b")


def test_the_order_check_allows_steps_between_and_refuses_a_swap_or_a_missing_step() -> None:
    print_section("assert_in_relative_order: negative controls")
    steps = tuple(Step(name, lambda: None) for name in ("a", "added", "b", "c"))

    assert_in_relative_order(steps, ("a", "b", "c"))
    with pytest.raises(AssertionError, match="relative order"):
        assert_in_relative_order(steps, ("b", "a"))
    with pytest.raises(AssertionError, match="missing"):
        assert_in_relative_order(steps, ("a", "gone"))
    print_success("✓ a step added between passes; a swap and a missing step fail")


def test_the_brim_parse_pool_is_released_off_the_event_loop_under_a_deadline() -> None:
    print_section("The BRIM parse pool step is blocking")
    # shutdown_pool(wait=True) joins the workers: under a deadline it must run in a thread for the deadline to hold.
    assert _step(app_lifespan.SHUTDOWN_STEPS, "brim-parse-pool").blocking is True
    print_success("✓ blocking=True")


def test_the_shutdown_has_no_deadline_yet() -> None:
    print_section("No shutdown budget in CP2b")
    assert app_lifespan.shutdown_deadline() is None
    print_success("✓ shutdown_deadline() is None")


@pytest.mark.parametrize(
    ("tuple_name", "step_name", "function_name"),
    [
        ("STARTUP_STEPS", "data-directories", "ensure_data_dirs"),
        ("FINALLY_STEPS", "tool-executor", "shutdown_tool_executor"),
        ("SHUTDOWN_STEPS", "market-holidays", "shutdown_market_holidays"),
    ],
)
def test_a_step_reaches_its_function_through_the_module_when_it_runs(tuple_name: str, step_name: str, function_name: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    print_section(f"{tuple_name} {step_name!r}: app_lifespan.{function_name} read when the step runs")
    # Were the step holding the real function, it could only meet a data dir in tmp_path.
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    calls: list[tuple[tuple, dict]] = []
    sentinel = object()

    def replacement(*args: Any, **kwargs: Any) -> object:
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(app_lifespan, function_name, replacement)

    result = _step(getattr(app_lifespan, tuple_name), step_name).run()
    if inspect.iscoroutine(result):  # the real coroutine function was reached: never run it
        result.close()

    assert calls == [((), {})], f"the step did not call app_lifespan.{function_name} as it is when the step runs"
    assert result is sentinel
    print_success("✓ the replaced function was called")


# =============================================================================
# (e) MIDDLEWARE
# =============================================================================


class _Tagging:
    """A pass-through ASGI middleware that writes its tag in ``seen`` when an HTTP request reaches it."""

    def __init__(self, app: Any, *, tag: str, seen: list[str]) -> None:
        self.app, self.tag, self.seen = app, tag, seen

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            self.seen.append(self.tag)
        await self.app(scope, receive, send)


class _First(_Tagging):
    pass


class _Second(_Tagging):
    pass


class _Third(_Tagging):
    pass


def test_the_middleware_stack_is_gzip_then_cors() -> None:
    print_section("MIDDLEWARE_STACK: gzip outermost, cors inside it")
    assert [entry.name for entry in MIDDLEWARE_STACK] == ["gzip", "cors"]
    print_success("✓ gzip, cors")


def test_install_middleware_adds_the_stack_with_its_options_first_outermost() -> None:
    print_section("install_middleware(app): GZip then CORS, with their options")
    app = FastAPI()

    install_middleware(app)

    assert [(middleware.cls, middleware.args, middleware.kwargs) for middleware in app.user_middleware] == [
        (GZipMiddleware, (), {"minimum_size": 1024, "compresslevel": 6}),
        (CORSMiddleware, (), {"allow_credentials": True, "allow_methods": ["*"], "allow_headers": ["*"]}),
    ]
    print_success("✓ user_middleware is [GZipMiddleware, CORSMiddleware]")


@pytest.mark.asyncio
async def test_install_middleware_keeps_a_custom_stack_in_order_first_outermost() -> None:
    print_section("install_middleware(app, stack): three entries, the first sees the request first")
    seen: list[str] = []
    stack = (
        MiddlewareEntry("first", _First, {"tag": "first", "seen": seen}),
        MiddlewareEntry("second", _Second, {"tag": "second", "seen": seen}),
        MiddlewareEntry("third", _Third, {"tag": "third", "seen": seen}),
    )
    app = FastAPI()

    install_middleware(app, stack)

    assert [middleware.cls for middleware in app.user_middleware] == [_First, _Second, _Third]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        await client.get("/no-route-here")
    assert seen == ["first", "second", "third"], "the first entry is the outermost: it must see the request first"
    print_success("✓ the stack's order is the order a request crosses it")


def test_the_app_is_built_with_the_middleware_stack() -> None:
    print_section("backend.app.main: the app carries MIDDLEWARE_STACK")
    assert [(middleware.cls, middleware.kwargs) for middleware in app_main.app.user_middleware] == [(entry.cls, dict(entry.options)) for entry in MIDDLEWARE_STACK]
    print_success("✓ the app's middleware is the declared stack")


# =============================================================================
# (f) STATIC SITE
# =============================================================================

SITE_ROUTES_WITH_THE_BUILD = [("route", "/mkdocs"), ("route", "/mkdocs/{path:path}"), ("route", "/"), ("mount", "/_app"), ("route", "/{path:path}")]
SITE_ROUTES_WITHOUT_THE_BUILD = [("route", "/mkdocs"), ("route", "/mkdocs/{path:path}"), ("route", "/"), ("route", "/{path:path}")]


def _kind_and_path(route: Any) -> tuple[str, str]:
    return ("mount" if isinstance(route, Mount) else "route", route.path)


def _installed_site(monkeypatch: pytest.MonkeyPatch, build: Path) -> tuple[FastAPI, list[Any]]:
    """A fresh app with the static site installed while ``FRONTEND_BUILD_DIR`` is ``build``, and the routes it added."""
    monkeypatch.setattr(static_site, "FRONTEND_BUILD_DIR", build)
    app = FastAPI()
    before = len(app.routes)
    static_site.install_static_site(app)
    return app, list(app.routes[before:])


def _served_path(context: Any) -> str | None:
    """The full path a route context serves: an included plain route or mount carries it on the Starlette route FastAPI
    builds for it (``starlette_route``), an included API route on the context itself (as in ``test_instance_block``)."""
    starlette_route = getattr(context, "starlette_route", None)
    return getattr(starlette_route, "path", None) if starlette_route is not None else context.path


def test_install_static_site_registers_the_site_then_the_chunks_then_the_catch_all(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    print_section("install_static_site with a build: /mkdocs, /mkdocs/{path}, /, /_app, then the catch-all")
    build = tmp_path / "build"
    (build / "_app" / "immutable").mkdir(parents=True)
    (build / "index.html").write_text("<!doctype html><title>index</title>")

    app, added = _installed_site(monkeypatch, build)

    assert [_kind_and_path(route) for route in added] == SITE_ROUTES_WITH_THE_BUILD
    assert {route.path: route.endpoint for route in added if not isinstance(route, Mount)} == {
        "/mkdocs": static_site.mkdocs_root,
        "/mkdocs/{path:path}": static_site.mkdocs_static,
        "/": static_site.root,
        "/{path:path}": static_site.frontend_catchall,
    }
    (mount,) = [route for route in added if isinstance(route, Mount)]
    assert mount.name == "frontend_app"
    assert isinstance(mount.app, static_site.ImmutableStaticFiles)
    assert Path(mount.app.directory) == build / "_app"
    assert (app.routes[-1].path, app.routes[-1].name) == ("/{path:path}", "frontend_catchall")
    print_success("✓ the chunks are mounted before the catch-all, which is last")


@pytest.mark.parametrize("build_files", [(), ("index.html",), ("_app/",)], ids=["no-build", "index-without-chunks", "chunks-without-index"])
def test_install_static_site_without_a_complete_build_mounts_no_chunks(build_files: tuple[str, ...], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    print_section(f"install_static_site without a complete build: {build_files or 'nothing'}")
    build = tmp_path / "build"
    for name in build_files:
        if name.endswith("/"):
            (build / name).mkdir(parents=True)
        else:
            build.mkdir(parents=True, exist_ok=True)
            (build / name).write_text("<!doctype html><title>index</title>")

    app, added = _installed_site(monkeypatch, build)

    assert [_kind_and_path(route) for route in added] == SITE_ROUTES_WITHOUT_THE_BUILD
    assert not [route for route in app.routes if isinstance(route, Mount)]
    assert (app.routes[-1].path, app.routes[-1].name) == ("/{path:path}", "frontend_catchall")
    print_success("✓ no mount, the catch-all still last")


def test_the_app_serves_the_site_after_every_api_route_and_the_catch_all_last() -> None:
    print_section("backend.app.main: the site after the API, the catch-all last")
    app = app_main.app
    last = app.routes[-1]
    assert (getattr(last, "path", None), getattr(last, "name", None)) == ("/{path:path}", "frontend_catchall"), f"the app's last route is {last!r}"

    served = [_served_path(context) for context in iter_route_contexts(app.routes)]
    api = [index for index, path in enumerate(served) if path is not None and (path == API_V1_PREFIX or path.startswith(f"{API_V1_PREFIX}/"))]
    assert api, f"barrier: no {API_V1_PREFIX} route found among {len(served)}, so 'after every API route' would prove nothing"
    for site_path in ("/mkdocs", "/mkdocs/{path:path}", "/"):
        positions = [index for index, path in enumerate(served) if path == site_path]
        assert len(positions) == 1, f"{site_path}: {len(positions)} routes"
        assert positions[0] > api[-1], f"{site_path} comes before the API route {served[api[-1]]}: an API path could reach the site"
    assert served[-1] == "/{path:path}"
    print_success(f"✓ {len(api)} API routes, then the site, then the catch-all")
