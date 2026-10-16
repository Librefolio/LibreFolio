"""``backend.app.services.platform.sleep_wake.idle_monitor`` and ``suspend``: an instance that asks Fly.io to suspend its own
machine after N minutes without a request of the user, when it is enabled (plan phase01SleepWake §Z2b, lot Z2b).

The user's presence and the work in progress come from ``activity`` (lot Z2a): the monitor suspends only when nothing is
busy and the user has been silent for N minutes; the scheduled wake-up (lot Z4) asks for a check once its run is over, so
that a machine its hosting panel woke goes back to sleep. The contract pinned here:

(a) ``config/sleep_wake.py``, read from the process environment at every call. ``idle_suspend_mode()``:
    ``LIBREFOLIO_IDLE_SUSPEND_MODE`` unset or blank is "none"; "none" or "fly", in any case and with spaces around, is
    "none" or "fly"; any other value raises ``SleepWakeConfigError`` — ``variable`` the variable, which the message names,
    ``code`` ``IDLE_SUSPEND_MODE_INVALID``. ``idle_suspend_minutes()``: ``LIBREFOLIO_IDLE_SUSPEND_MINUTES`` unset or blank
    is ``DEFAULT_IDLE_SUSPEND_MINUTES``, 5; ASCII digits worth 1 to 1440 — spaces around and leading zeros allowed, as the
    other values of the module — are that int; anything else — 0, 1441, a sign, a decimal, a word, an exponent, a digit
    outside ASCII, an underscore — raises ``SleepWakeConfigError`` ``IDLE_SUSPEND_MINUTES_INVALID``.
(b) ``suspend.py``: ``FLY_API_SOCKET`` "/.fly/api"; ``SuspendError(Exception)`` carries ``reason``, a short code.
    ``FlySuspender(*, transport=None, environ=None, timeout=10.0)``: ``transport_factory()`` returns the transport given,
    or else builds ``httpx.AsyncHTTPTransport(uds="/.fly/api")`` — the class read through ``httpx`` at the call —, the one
    ``suspend()`` sends through. ``suspend()`` reads ``FLY_APP_NAME`` and ``FLY_MACHINE_ID`` from ``environ`` —
    ``os.environ`` when None — at each call, and sends one ``POST http://flaps/v1/apps/<app>/machines/<id>/suspend``: no
    body, no ``Authorization``, ``timeout`` on every phase of the request. A 2xx returns None; another status raises
    ``SuspendError`` "http_<status>"; an ``httpx.HTTPError`` "connection"; a variable missing or blank "not_on_fly", before
    any request.
(c) ``idle_monitor.py``: ``IDLE_CHECK_SECONDS`` 30.0, ``RESUME_GRACE_SECONDS`` 60.0, ``FAILURE_BACKOFF_FIRST_SECONDS``
    30.0, ``FAILURE_BACKOFF_MAX_SECONDS`` 600.0, ``WAKE_CHECK_DELAY_SECONDS`` 2.0, read at call time.
    ``IdleMonitor(*, activity, suspender, minutes, sleep=asyncio.sleep, monotonic=time.monotonic)``.
(d) ``check()`` answers "busy", "active", "waiting", "suspended" or "failed". While ``monotonic() < retry_not_before``,
    "waiting", and nothing is read or called. Else the busy reasons, read off the event loop's thread: any reason — a
    request in flight included — is "busy", whatever the idle time. Else an idle time under ``minutes * 60`` is "active".
    Else ``suspender.suspend()``: once it returns, "suspended", logged — INFO, "Idle suspend requested", ``idle_s`` and
    ``minutes`` —, and the streak of failures is over.
(e) A ``SuspendError`` is "failed": no attempt before ``monotonic() + backoff``, the backoff 30 s at the first failure of
    a streak, then doubled up to 600 s — 30, 60, 120, 240, 480, 600, 600 —, both bounds read at the call; one WARNING per
    streak, at its first failure — "Idle suspend failed", ``reason`` and ``retry_in_s`` —; after a success the next
    failure starts a new streak at 30 s. Any other ``Exception`` of the suspender is a failure of reason "error"; nothing
    propagates out of ``check()``.
(f) ``run(stop)`` checks at once, then waits through the injected ``sleep``: ``IDLE_CHECK_SECONDS`` after "busy",
    "active" and "waiting", at least ``RESUME_GRACE_SECONDS`` after "suspended" and "failed" — the request that woke a
    resumed machine must count first. A wait, the grace included, ends early on ``stop`` — the loop returns None, also
    when the stop comes during a check, or before the loop starts — or on a requested check. A ``check()`` that raises is
    logged ("Idle check failed") and the loop goes on: ``run`` never raises.
(g) ``request_check(delay)``, from any thread: the loop runs a check ``delay`` seconds from now, earlier than its regular
    wait, and earlier than the grace (decision of 16/10/2026): the grace protects the request that woke the machine, and
    the check a wake-up asks for comes after that request, so that a machine nobody uses goes back to sleep at once.
    Requests made before a check — while one runs included — make one check after it.
(h) The module's functions read ``idle_suspend_mode``, ``idle_suspend_minutes``, ``FlySuspender``, ``current_activity``,
    ``get_tool_executor`` and ``backup_in_progress`` as module globals at the call. ``start_idle_monitor()`` always
    returns None: H's startup runner awaits what a step returns, and the monitor never ends. In "none" mode it starts
    nothing and registers nothing; an invalid mode is logged once, at ERROR, and taken as "none". In "fly" mode it builds
    ``FlySuspender()``, registers the busy checks "tools" and "backup" on ``current_activity()``, starts the monitor's
    ``run`` as a task, which ``idle_monitor_task()`` returns, and logs INFO "Idle monitor started", ``mode`` and
    ``minutes``; an invalid number of minutes is logged once, at WARNING or ERROR, and 5 is used. ``stop_idle_monitor()``
    sets the stop and returns the task. ``request_idle_check(delay=2.0)`` forwards to the running monitor, from any thread.
    In a fresh interpreter ``idle_monitor_task()`` and ``stop_idle_monitor()`` are None and ``request_idle_check`` does
    nothing.
(i) The busy checks: "tools" is listed while the tool executor's snapshot has ``pending > 0``, "backup" while
    ``backup_in_progress()`` answers True. The monitor started in "fly" mode never suspends while any reason is listed —
    a request in flight included —, and suspends once they are gone with the idle time past the threshold.
(j) Acceptance: with mode fly and N minutes, an activity silent for exactly N×60 s, nothing busy, is suspended at that
    check; at N×60 − 1 s it is not. With a check every 30 s, the machine is therefore suspended within N minutes and 30 s
    of the user's last request (no timing is asserted).
(k) The wake-up (``api/v1/system/wake.py``): at the end of each run — one that raised included —, in the run's task, after
    "Wake-up run finished", ``idle_monitor.request_idle_check(2.0)``, read through the module at the call. With no
    monitor running, the real one does nothing, and the wake-up answers as before.
(l) The lifespan (``app_lifespan.py``): ``Step("idle-monitor", ...)`` right after "scheduler" in ``STARTUP_STEPS``, and
    first in ``SHUTDOWN_STEPS``, before "scheduler", on the event loop (not blocking); each reaches
    ``start_idle_monitor`` / ``stop_idle_monitor`` through ``app_lifespan``'s name when it runs, and returns what it
    returns. The startup step, run by ``lifecycle.run_startup_steps``, completes while the monitor keeps running.

Pure: no database, no server, no lane port, no network. The Machines API is an ``httpx.MockTransport``, and the class of
the socket's transport a recorder. Every ``Activity`` is the test's own, on a fake clock, in place of the process's
``ACTIVITY``. A monitor under test has a fake monotonic clock and a recording ``sleep``: a wait of up to a second is
real, a longer one lasts until the test ends, so each test sets the constants short or long as it needs. A monitor that
``start_idle_monitor()`` starts gets its collaborators replaced on its module. The wake-up runs in an app of the test,
served in this process, with ``run_due_jobs`` replaced. One test starts a fresh interpreter of its own. Nothing sleeps
to synchronise: every wait is on the timeline of what the fakes saw, an event or a task, bounded by ``WAIT_SECONDS``,
and no assertion depends on a duration; a check held at a gate is released before its test ends. The log is read with
``structlog.testing.capture_logs`` behind a barrier: a canary logged through the module's own ``logger`` must reach the
capture, or "logged once" would prove nothing.

Red until the code of Z2b exists: ``sleep_wake/suspend.py`` and ``sleep_wake/idle_monitor.py`` do not import, a
collection error. Then (a) is red until the two functions exist, (k) until ``wake.py`` calls the hook, and (l) until
``app_lifespan.py`` holds the two steps. SWS-046 was written once the code existed, to pin the decision that a requested
check ends the grace: green on arrival, it turns red, at the end of its bounded wait, if the grace stops ending on one.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Sequence
from contextlib import ExitStack, asynccontextmanager, contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from structlog.testing import capture_logs

from backend.app.api.v1.system import router as system_router
from backend.app.api.v1.system import wake
from backend.app.config import API_V1_PREFIX
from backend.app.config import sleep_wake as sleep_wake_config
from backend.app.config.sleep_wake import SleepWakeConfigError
from backend.app.services.platform import app_lifespan, lifecycle
from backend.app.services.platform.lifecycle import Step
from backend.app.services.platform.scheduler.scheduler import RunReport
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.services.platform.sleep_wake import idle_monitor
from backend.app.services.platform.sleep_wake import suspend as suspend_module
from backend.app.services.platform.sleep_wake.activity import Activity
from backend.test_scripts.test_utils import print_section, print_success

#: The classes under test, read from their modules: imported through the package, which exists, so that the order of the
#: imports is the same before and after the modules of Z2b are written.
IdleMonitor = idle_monitor.IdleMonitor
FlySuspender = suspend_module.FlySuspender
SuspendError = suspend_module.SuspendError

#: The variables, spelled out here: a rename shows.
MODE_VARIABLE = "LIBREFOLIO_IDLE_SUSPEND_MODE"
MINUTES_VARIABLE = "LIBREFOLIO_IDLE_SUSPEND_MINUTES"
APP_VARIABLE = "FLY_APP_NAME"
MACHINE_VARIABLE = "FLY_MACHINE_ID"
WAKE_TOKEN_VARIABLE = "LIBREFOLIO_WAKE_TOKEN"
#: Removed before every test, so that nothing comes from the runner's environment; the proxies too, or httpx would build
#: transports of its own for them.
CLEARED_VARIABLES = (MODE_VARIABLE, MINUTES_VARIABLE, APP_VARIABLE, MACHINE_VARIABLE, WAKE_TOKEN_VARIABLE, f"{WAKE_TOKEN_VARIABLE}_FILE", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")

FLY_SOCKET = "/.fly/api"
APP_NAME = "librefolio-z2b"
MACHINE_ID = "6e82d4d6c71e48"
ON_FLY = {APP_VARIABLE: APP_NAME, MACHINE_VARIABLE: MACHINE_ID}
SUSPEND_URL = f"http://flaps/v1/apps/{APP_NAME}/machines/{MACHINE_ID}/suspend"
#: ``(method, URL, Authorization present, body)`` of the one request ``suspend()`` sends.
SUSPEND_REQUEST = ("POST", SUSPEND_URL, False, b"")

#: The literals of the contract, never read from the modules under test.
OUTCOMES = frozenset({"busy", "active", "waiting", "suspended", "failed"})
SUSPEND_REQUESTED = "Idle suspend requested"
SUSPEND_FAILED = "Idle suspend failed"
CHECK_FAILED = "Idle check failed"
MONITOR_STARTED = "Idle monitor started"
RUN_FINISHED = "Wake-up run finished"
RUN_FAILED = "Wake-up run failed"
STEP_NAME = "idle-monitor"
MONITOR_CANARY = "sleep-wake suspend test: canary through the idle monitor's logger"
WAKE_CANARY = "sleep-wake suspend test: canary through the wake module's logger"
WAKE_SYNC = f"{API_V1_PREFIX}/system/wake-sync"

#: The longest a test waits for anything: a check, a task, a thread, a request.
WAIT_SECONDS = 30.0
#: The longest the fresh interpreter of SWS-038 may take, its imports included.
PROCESS_WAIT_SECONDS = 120.0
#: A recorded sleep up to this long really waits; a longer one lasts until its test ends.
REAL_SLEEP_LIMIT = 1.0
#: ``IDLE_CHECK_SECONDS`` where checks must follow one another by themselves...
SHORT_CHECK_SECONDS = 0.01
#: ...where a check after a regular wait is the marker that the loop went back to waiting...
MARKER_CHECK_SECONDS = 0.05
#: ...and where only a request or the stop may end a wait. ``RESUME_GRACE_SECONDS`` longer still, to tell them apart.
LONG_CHECK_SECONDS = 1_000.0
LONG_GRACE_SECONDS = 2_000.0
#: The first backoff in SWS-028: shorter than the grace, so that the wait after a failure is the grace.
SHORT_BACKOFF_SECONDS = 50.0

#: The activity's wall clock, the monitor's monotonic clock, the threshold, and an idle time far past it.
START = 1_000.0
MONOTONIC_START = 5_000.0
MINUTES = 5
THRESHOLD_SECONDS = MINUTES * 60
LONG_IDLE = 10_000.0
#: The backoffs of a streak of failures, at the shipped bounds 30 and 600 s.
BACKOFFS = (30.0, 60.0, 120.0, 240.0, 480.0, 600.0, 600.0)
#: The minutes of the acceptance test through the environment, and of the module's globals in SWS-035: distinctive.
ACCEPTANCE_MINUTES = 7
GLOBALS_MINUTES = 9

STARTED_AT = datetime(2026, 10, 16, 3, 0, 0, tzinfo=UTC)
FINISHED_AT = datetime(2026, 10, 16, 3, 0, 9, tzinfo=UTC)

REPO_ROOT = Path(__file__).resolve().parents[3]
PROBE_MARK = "IDLE-MONITOR-PROBE "
#: Run by a fresh interpreter in SWS-038: what the module answers before any monitor was ever started.
FRESH_INTERPRETER_PROBE = """
import asyncio
import json

from backend.app.services.platform.sleep_wake import idle_monitor


async def probe():
    seen = {"task_before": repr(idle_monitor.idle_monitor_task()), "stop_before": repr(idle_monitor.stop_idle_monitor())}
    idle_monitor.request_idle_check()
    idle_monitor.request_idle_check(0.0)
    seen["start"] = repr(idle_monitor.start_idle_monitor())
    seen["task_after"] = repr(idle_monitor.idle_monitor_task())
    seen["stop_after"] = repr(idle_monitor.stop_idle_monitor())
    seen["other_tasks"] = len(asyncio.all_tasks()) - 1
    return seen


print(PROBE_MARK + json.dumps(asyncio.run(probe())))
""".replace("PROBE_MARK", repr(PROBE_MARK))

# =============================================================================
# FAKES
# =============================================================================


class FakeClock:
    """A clock that moves only when the test — or a recorded sleep — moves it: ``clock.now = …``."""

    def __init__(self, start: float) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class Timeline:
    """What the monitor and the fakes did, in order, from any thread: one tuple per event, its kind first.

    ``("reading", reasons, thread, label)`` a reading of the busy reasons; ``("suspend", n)`` a call to ``suspend()``;
    ``("sleep", s)``, ``("slept", s)``, ``("sleep-cancelled", s)`` a recorded sleep called, ended, cancelled;
    ``("gate-entered", n)`` a check held at the gate. A coroutine waits on it with ``until``: every ``add`` wakes it
    through ``call_soon_threadsafe``, so a worker thread adds as well as the event loop.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._entries: list[tuple[Any, ...]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._changed: asyncio.Event | None = None

    def add(self, *entry: Any) -> None:
        with self._lock:
            self._entries.append(entry)
            loop, changed = self._loop, self._changed
        if loop is not None and changed is not None and not loop.is_closed():
            with suppress(RuntimeError):  # the test's loop closed meanwhile: nobody waits any more
                loop.call_soon_threadsafe(changed.set)

    @property
    def entries(self) -> list[tuple[Any, ...]]:
        with self._lock:
            return list(self._entries)

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def kinds(self, kind: str, start: int = 0) -> list[tuple[int, tuple[Any, ...]]]:
        """``(position, entry)`` of every entry of ``kind``, from position ``start`` on."""
        return [(position, entry) for position, entry in enumerate(self.entries) if position >= start and entry[0] == kind]

    def count(self, kind: str, start: int = 0) -> int:
        return len(self.kinds(kind, start))

    async def until(self, condition: Callable[[], bool], what: str) -> None:
        """Until ``condition()`` holds, within ``WAIT_SECONDS``; a red naming ``what``, with the last entries, after."""
        with self._lock:
            if self._loop is None:
                self._loop, self._changed = asyncio.get_running_loop(), asyncio.Event()
            changed = self._changed
        assert changed is not None

        async def reached() -> None:
            while not condition():
                changed.clear()
                await changed.wait()

        await _within(reached(), lambda: f"{what}? the last entries: {self.entries[-12:]}")


class RecordingActivity(Activity):
    """An ``Activity`` on a fake clock that puts each reading of its busy reasons in the timeline — the reasons, the
    thread, its ``label`` — and counts the readings of its idle time. Each of ``idle_failures`` is raised by one reading
    of the idle time, in order; ``registered`` lists the names of the busy checks registered on it."""

    def __init__(self, clock: FakeClock, timeline: Timeline, label: str) -> None:
        super().__init__(clock=clock)
        self.clock = clock
        self.timeline = timeline
        self.label = label
        self.idle_reads = 0
        self.idle_failures: list[Exception] = []
        self.registered: list[str] = []

    def busy_reasons(self) -> tuple[str, ...]:
        reasons = super().busy_reasons()
        self.timeline.add("reading", reasons, threading.get_ident(), self.label)
        return reasons

    def idle_seconds(self, now: float | None = None) -> float:
        self.idle_reads += 1
        if self.idle_failures:
            raise self.idle_failures.pop(0)
        return super().idle_seconds(now)

    def register_busy_check(self, name: str, check: Callable[[], object]) -> None:
        super().register_busy_check(name, check)
        self.registered.append(name)


class FakeSuspender:
    """The monitor's suspender: each call is counted and put in the timeline; it raises what ``fail_with`` builds, while
    that is set, or else returns None."""

    def __init__(self, timeline: Timeline) -> None:
        self.timeline = timeline
        self.calls = 0
        self.fail_with: Callable[[], BaseException] | None = None

    async def suspend(self) -> None:
        self.calls += 1
        self.timeline.add("suspend", self.calls)
        if self.fail_with is not None:
            raise self.fail_with()


class RecordingSleep:
    """The monitor's ``sleep``: each call is put in the timeline, then waits — for real up to ``REAL_SLEEP_LIMIT``, longer
    until ``release()``, at the end of the test. Its end is put in the timeline too, and a sleep that ends moves the
    monitor's monotonic clock on by its seconds, so that the two clocks of the monitor agree."""

    def __init__(self, timeline: Timeline, monotonic: FakeClock) -> None:
        self.timeline = timeline
        self.monotonic = monotonic
        self._released: asyncio.Event | None = None

    async def __call__(self, delay: float, result: Any = None) -> Any:
        self.timeline.add("sleep", delay)
        try:
            if delay <= REAL_SLEEP_LIMIT:
                await asyncio.sleep(delay)
            else:
                if self._released is None:
                    self._released = asyncio.Event()
                await self._released.wait()
        except asyncio.CancelledError:
            self.timeline.add("sleep-cancelled", delay)
            raise
        self.monotonic.now += max(0.0, delay)
        self.timeline.add("slept", delay)
        return result

    def release(self) -> None:
        if self._released is not None:
            self._released.set()


class Gate:
    """A busy check, never busy, that holds a check in progress while it is armed: in the worker thread reading the busy
    reasons it says it was entered, then waits for its release, at most ``WAIT_SECONDS``. One hold per arming."""

    def __init__(self, timeline: Timeline) -> None:
        self.timeline = timeline
        self.entered = 0
        self._armed = threading.Event()
        self._released = threading.Event()

    def __call__(self) -> bool:
        if self._armed.is_set():
            self._armed.clear()
            self.entered += 1
            self.timeline.add("gate-entered", self.entered)
            self._released.wait(WAIT_SECONDS)
        return False

    def arm(self) -> None:
        self._released.clear()
        self._armed.set()

    def release(self) -> None:
        self._armed.clear()
        self._released.set()


class FakeExecutor:
    """``get_tool_executor()`` of the monitor's module: ``snapshot()`` answers ``pending`` as it is at the call."""

    def __init__(self) -> None:
        self.pending = 0
        self.snapshots = 0

    def snapshot(self) -> SimpleNamespace:
        self.snapshots += 1
        return SimpleNamespace(pending=self.pending)


class FakeBackup:
    """``backup_in_progress`` of the monitor's module: it answers ``answer`` and counts its calls."""

    def __init__(self) -> None:
        self.answer = False
        self.calls = 0

    def __call__(self, *args: Any, **kwargs: Any) -> bool:
        self.calls += 1
        return self.answer


class FlyFakes:
    """What ``start_idle_monitor()`` reaches in "fly" mode besides the configuration and the activity, replaced on the
    monitor's module: ``FlySuspender`` — a recorder of its arguments, building ``suspender`` —, ``get_tool_executor``
    and ``backup_in_progress``."""

    def __init__(self, timeline: Timeline) -> None:
        self.suspender = FakeSuspender(timeline)
        self.built: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.executor = FakeExecutor()
        self.backup = FakeBackup()

    def fly_suspender(self, *args: Any, **kwargs: Any) -> FakeSuspender:
        self.built.append((args, kwargs))
        return self.suspender

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(idle_monitor, "FlySuspender", self.fly_suspender)
        monkeypatch.setattr(idle_monitor, "get_tool_executor", lambda: self.executor)
        monkeypatch.setattr(idle_monitor, "backup_in_progress", self.backup)


class FlyApi:
    """The Machines API behind the socket, faked: each request is recorded with the transport that carried it, and
    answered ``status``, or what ``raises(request)`` builds is raised for it."""

    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.raises: Callable[[httpx.Request], Exception] | None = None
        self.requests: list[httpx.Request] = []
        self.carriers: list[object] = []
        self.transport = httpx.MockTransport(self.answer)

    def answer(self, request: httpx.Request, carrier: object = "given") -> httpx.Response:
        self.requests.append(request)
        self.carriers.append(carrier)
        if self.raises is not None:
            raise self.raises(request)
        return httpx.Response(self.status)


@dataclass(frozen=True)
class Built:
    """One construction of ``httpx.AsyncHTTPTransport``, replaced: its arguments and the transport it gave."""

    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    transport: httpx.MockTransport


class SocketTransports:
    """``httpx.AsyncHTTPTransport`` replaced: each construction is recorded and gives a ``MockTransport`` of its own in
    front of ``api``, which records the construction's number as the carrier of each request it serves."""

    def __init__(self, api: FlyApi) -> None:
        self.api = api
        self.built: list[Built] = []

    def __call__(self, *args: Any, **kwargs: Any) -> httpx.MockTransport:
        number = len(self.built)
        transport = httpx.MockTransport(lambda request: self.api.answer(request, carrier=number))
        self.built.append(Built(args, kwargs, transport))
        return transport


class FakeRun:
    """``run_due_jobs`` of the wake module, replaced: it records its reason and the task it runs in, raises ``failure``
    when set, or else returns a real ``RunReport``; ``ended`` counts the runs over, however they ended."""

    def __init__(self) -> None:
        self.reasons: list[str] = []
        self.tasks: list[asyncio.Task[Any] | None] = []
        self.ended = 0
        self.failure: Exception | None = None

    async def __call__(self, reason: str) -> RunReport:
        self.reasons.append(reason)
        self.tasks.append(asyncio.current_task())
        try:
            if self.failure is not None:
                raise self.failure
            return RunReport(reason=reason, status="ok", started_at=STARTED_AT, finished_at=FINISHED_AT)
        finally:
            self.ended += 1


@dataclass(frozen=True)
class HookCall:
    """One call of ``request_idle_check``, replaced: its arguments, the task it ran in, how many runs were over then, and
    the events logged until then."""

    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    task: asyncio.Task[Any] | None
    runs_ended: int
    logged: tuple[Any, ...]


class HookRecorder:
    """``idle_monitor.request_idle_check`` replaced: each call is recorded as a ``HookCall``."""

    def __init__(self, run: FakeRun, log: list[dict[str, Any]]) -> None:
        self.run = run
        self.log = log
        self.calls: list[HookCall] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        self.calls.append(HookCall(args, kwargs, asyncio.current_task(), self.run.ended, tuple(entry.get("event") for entry in self.log)))


@dataclass
class Rig:
    """A monitor under test and its fakes: the activity, the suspender, the monotonic clock, the recorded sleep, and a gate
    that a test registers on the activity to hold a check."""

    activity: RecordingActivity
    suspender: FakeSuspender
    monotonic: FakeClock
    sleep: RecordingSleep
    gate: Gate
    monitor: Any


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture
def timeline() -> Timeline:
    return Timeline()


@pytest.fixture(autouse=True)
def activity(monkeypatch: pytest.MonkeyPatch, timeline: Timeline) -> RecordingActivity:
    """The test's own ``Activity``, on a fake clock, in place of the process's ``ACTIVITY``: ``current_activity()`` answers it."""
    mine = RecordingActivity(FakeClock(START), timeline, "process")
    monkeypatch.setattr(activity_module, "ACTIVITY", mine)
    return mine


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts without the variables of this lot, of Fly, of the wake-up token and of the proxies."""
    for name in CLEARED_VARIABLES:
        monkeypatch.delenv(name, raising=False)


def _rig(activity: RecordingActivity, timeline: Timeline, *, minutes: int = MINUTES) -> Rig:
    """A monitor on ``activity`` with a fake suspender, a fake monotonic clock and a recorded sleep."""
    monotonic = FakeClock(MONOTONIC_START)
    sleeper = RecordingSleep(timeline, monotonic)
    suspender = FakeSuspender(timeline)
    monitor = IdleMonitor(activity=activity, suspender=suspender, minutes=minutes, sleep=sleeper, monotonic=monotonic)
    return Rig(activity, suspender, monotonic, sleeper, Gate(timeline), monitor)


@pytest.fixture
def rig(activity: RecordingActivity, timeline: Timeline) -> Rig:
    return _rig(activity, timeline)


async def _within(awaitable: Awaitable[Any], what: str | Callable[[], str]) -> Any:
    """What ``awaitable`` gives, or a red naming ``what`` after ``WAIT_SECONDS``: a hang fails the test instead of the run."""
    try:
        return await asyncio.wait_for(awaitable, WAIT_SECONDS)
    except TimeoutError:
        pytest.fail(f"{what() if callable(what) else what}: nothing within {WAIT_SECONDS} s")


def _set_or_unset(monkeypatch: pytest.MonkeyPatch, name: str, value: str | None) -> None:
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


@contextmanager
def _monitor_log() -> Iterator[list[dict[str, Any]]]:
    """What is logged inside the block, behind a barrier: a canary logged through the monitor's own logger must arrive first."""
    with capture_logs() as events:
        idle_monitor.logger.debug(MONITOR_CANARY)
        assert any(event.get("event") == MONITOR_CANARY for event in events), f"barrier: the idle monitor's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


@contextmanager
def _wake_log() -> Iterator[list[dict[str, Any]]]:
    """What is logged inside the block, behind a barrier: a canary logged through the wake module's own logger must arrive first."""
    with capture_logs() as events:
        wake.logger.debug(WAKE_CANARY)
        assert any(event.get("event") == WAKE_CANARY for event in events), f"barrier: the wake module's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


def _logged(events: list[dict[str, Any]], event: str) -> list[dict[str, Any]]:
    """Every captured ``event``, in order."""
    return [entry for entry in events if entry.get("event") == event]


def _levels(events: list[dict[str, Any]], *levels: str) -> list[Any]:
    """The level of every captured event at one of ``levels``, in order."""
    return [entry.get("log_level") for entry in events if entry.get("log_level") in levels]


async def _check(monitor: Any) -> str:
    """One ``check()``, within the deadline; what it answered, one of the five outcomes."""
    outcome = await _within(monitor.check(), "IdleMonitor.check()")
    assert outcome in OUTCOMES, f"check() answers one of {sorted(OUTCOMES)}, got {outcome!r}"
    return outcome


def _touched(rig: Rig, timeline: Timeline) -> tuple[int, int, int]:
    """What the checks touched so far: readings of the busy reasons, readings of the idle time, calls to ``suspend()``."""
    return timeline.count("reading"), rig.activity.idle_reads, rig.suspender.calls


def _readings(timeline: Timeline, start: int = 0) -> list[tuple[str, ...]]:
    """The busy reasons each reading answered, in order, from position ``start`` on."""
    return [entry[1] for _, entry in timeline.kinds("reading", start)]


def _first_long_sleep(timeline: Timeline, start: int) -> tuple[int, float] | None:
    """Position and seconds of the first sleep longer than ``REAL_SLEEP_LIMIT`` from ``start`` on — a regular wait, or
    the grace —; None before it."""
    return next(((position, entry[1]) for position, entry in timeline.kinds("sleep", start) if entry[1] > REAL_SLEEP_LIMIT), None)


def _checks_before_the_regular_wait(timeline: Timeline, held: int) -> int | None:
    """After the check held at position ``held``: how many checks ran before the end of the loop's first regular wait —
    once a check has followed that wait —; None until then."""
    entries = timeline.entries
    readings = [position for position, entry in enumerate(entries) if position > held and entry[0] == "reading"]
    if not readings:
        return None
    held_reading = readings[0]
    slept = next((position for position, entry in enumerate(entries) if position > held_reading and entry[0] == "slept" and abs(entry[1] - MARKER_CHECK_SECONDS) < 1e-6), None)
    if slept is None or readings[-1] < slept:
        return None
    return sum(1 for position in readings if held_reading < position < slept)


async def _checks_after(timeline: Timeline, mark: int, count: int, what: str) -> list[set[str]]:
    """Once ``count`` readings came after position ``mark``: the reasons of all of them but the first, which may have
    started before the change the test made at ``mark``; every one of these started after it."""
    await timeline.until(lambda: timeline.count("reading", mark) >= count, f"{count} checks of the monitor {what}")
    return [set(reasons) for reasons in _readings(timeline, mark)[1:count]]


def _readings_before_suspends(timeline: Timeline) -> list[tuple[str, ...] | None]:
    """For each call to ``suspend()``: the reasons of the last reading before it, the reading of the check that called it."""
    last: tuple[str, ...] | None = None
    seen: list[tuple[str, ...] | None] = []
    for entry in timeline.entries:
        if entry[0] == "reading":
            last = entry[1]
        elif entry[0] == "suspend":
            seen.append(last)
    return seen


async def _settle(task: asyncio.Task[Any], what: str) -> None:
    """``task`` done before the test ends: the deadline to end by itself, then cancelled. What it raised is raised here:
    the monitor's loop never raises."""
    if not task.done():
        await asyncio.wait({task}, timeout=WAIT_SECONDS)
    if not task.done():
        task.cancel()
        await asyncio.wait({task}, timeout=WAIT_SECONDS)
        pytest.fail(f"{what}: still running {WAIT_SECONDS} s later; cancelled")
    if not task.cancelled() and task.exception() is not None:
        raise task.exception()


async def _ended(task: asyncio.Task[Any], what: str) -> None:
    """``task`` returned None within the deadline: neither cancelled nor raising."""
    done, _ = await asyncio.wait({task}, timeout=WAIT_SECONDS)
    assert task in done, f"{what}: still running {WAIT_SECONDS} s later"
    assert not task.cancelled(), f"{what}: cancelled instead of returning"
    error = task.exception()
    if error is not None:
        raise error
    assert task.result() is None, f"{what}: returned {task.result()!r}, not None"


@asynccontextmanager
async def _running(rig: Rig, stop: asyncio.Event) -> AsyncIterator[asyncio.Task[None]]:
    """``rig.monitor.run(stop)`` as a task for the block. At its end the stop is set, the gate opened, and the task must
    end within the deadline — what it raised is raised here —; then the long sleeps are released."""
    task = asyncio.create_task(rig.monitor.run(stop), name="idle-monitor-loop-under-test")
    try:
        yield task
    finally:
        stop.set()
        rig.gate.release()
        try:
            await _settle(task, "the monitor's loop, after its stop event was set")
        finally:
            rig.sleep.release()


@asynccontextmanager
async def _started() -> AsyncIterator[asyncio.Task[Any] | None]:
    """``start_idle_monitor()`` for the block, which must return None; the block gets the monitor's task it started —
    ``idle_monitor_task()`` when new —, or None. At its end ``stop_idle_monitor()``, and that task must end within the
    deadline."""
    before = idle_monitor.idle_monitor_task()
    returned = idle_monitor.start_idle_monitor()
    current = idle_monitor.idle_monitor_task()
    started = current if current is not None and current is not before else None
    if started is None and isinstance(returned, asyncio.Task):
        started = returned
    try:
        assert returned is None, f"start_idle_monitor() returns None, in every mode: the startup runner awaits what a step returns, and the monitor never ends; got {returned!r}"
        yield started
    finally:
        if started is not None:
            idle_monitor.stop_idle_monitor()
            await _settle(started, "the idle monitor started for the test, after stop_idle_monitor()")


def _fly_environment(monkeypatch: pytest.MonkeyPatch, timeline: Timeline, *, mode: str = "fly", minutes: str | None = None) -> FlyFakes:
    """The "fly" mode through the environment, read by the real configuration; ``FlyFakes`` installed."""
    monkeypatch.setenv(MODE_VARIABLE, mode)
    _set_or_unset(monkeypatch, MINUTES_VARIABLE, minutes)
    fakes = FlyFakes(timeline)
    fakes.install(monkeypatch)
    return fakes


def _fly_globals(monkeypatch: pytest.MonkeyPatch, timeline: Timeline, *, minutes: int = MINUTES) -> FlyFakes:
    """The "fly" mode through the module's globals: ``idle_suspend_mode`` and ``idle_suspend_minutes`` replaced; ``FlyFakes`` installed."""
    monkeypatch.setattr(idle_monitor, "idle_suspend_mode", lambda: "fly")
    monkeypatch.setattr(idle_monitor, "idle_suspend_minutes", lambda: minutes)
    fakes = FlyFakes(timeline)
    fakes.install(monkeypatch)
    return fakes


def _http_503() -> SuspendError:
    return SuspendError(reason="http_503")


def _connection_lost() -> SuspendError:
    return SuspendError(reason="connection")


def _true_check() -> bool:
    return True


def _raising_check() -> bool:
    raise RuntimeError("provoked: the busy check fails")


@contextmanager
def _busy_by(activity: Activity, source: str) -> Iterator[None]:
    """``activity`` busy for the block by ``source``: a request in flight — the wake-up's or the user's —, a busy span
    "export", or a busy check "backup" answering True or raising."""
    if source in ("wake-request", "user-request"):
        with activity.request(presence=source == "user-request"):
            yield
        return
    if source == "span":
        with activity.busy("export"):
            yield
        return
    activity.register_busy_check("backup", _raising_check if source == "check-raising" else _true_check)
    yield


async def _prepare(rig: Rig, held: ExitStack, outcome: str) -> None:
    """Make the loop's first check end ``outcome``; a busy span stays open in ``held``."""
    activity = rig.activity
    if outcome == "busy":
        held.enter_context(activity.busy("held"))
    if outcome in ("waiting", "suspended", "failed"):
        activity.clock.now = activity.started_at + LONG_IDLE
    if outcome in ("waiting", "failed"):
        rig.suspender.fail_with = _http_503
    if outcome == "waiting":
        assert await _check(rig.monitor) == "failed", "Precondition: a failure before the loop starts, whose backoff still runs"


def _request_shape(request: httpx.Request) -> tuple[str, str, bool, bytes]:
    """Method, URL, whether ``Authorization`` is there, body."""
    return request.method, str(request.url), "authorization" in request.headers, request.content


def _system_app() -> FastAPI:
    """The system router under ``/api/v1``, as ``router.py`` mounts it, in an app of the test and nothing else."""
    app = FastAPI()
    app.include_router(system_router, prefix=API_V1_PREFIX)
    return app


def _wake_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """A new wake-up token in the variable, the route on; ``LIBREFOLIO_NO_SCHEDULER`` besides, as ``test_system_wake.py`` does."""
    token = secrets.token_hex(32)
    monkeypatch.setenv(WAKE_TOKEN_VARIABLE, token)
    monkeypatch.setenv("LIBREFOLIO_NO_SCHEDULER", "1")
    return token


async def _wake_up(app: FastAPI, token: str) -> httpx.Response:
    """``POST /api/v1/system/wake-sync`` with the token, served in this process; the whole answer, within the deadline."""
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        return await _within(client.post(WAKE_SYNC, headers={"Authorization": f"Bearer {token}"}), "POST wake-sync")


async def _run_task(run: FakeRun) -> asyncio.Task[Any]:
    """The task of the one wake-up run, once it is done, within the deadline."""
    assert len(run.tasks) == 1 and run.tasks[0] is not None, f"one wake-up run, in a task of its own: {run.reasons}"
    task = run.tasks[0]
    done, _ = await asyncio.wait({task}, timeout=WAIT_SECONDS)
    assert task in done, f"the wake-up run was still running {WAIT_SECONDS} s later"
    return task


def _names(steps: Sequence[Step]) -> list[str]:
    return [step.name for step in steps]


def _step(steps: Sequence[Step], name: str) -> Step:
    """The one step called ``name``."""
    matching = [step for step in steps if step.name == name]
    assert len(matching) == 1, f"{len(matching)} steps named {name!r} in {_names(steps)}"
    return matching[0]


def _assert_in_relative_order(steps: Sequence[Step], expected: Sequence[str], what: str) -> None:
    """The names ``expected`` are among ``steps``, in this relative order; any other step may stand around them."""
    names = _names(steps)
    missing = [name for name in expected if name not in names]
    assert not missing, f"{what}: {missing} missing from {names}"
    positions = [names.index(name) for name in expected]
    assert positions == sorted(positions), f"{what}: {list(expected)} must keep this relative order, found {names}"


def _call_recorder(calls: list[tuple[tuple[Any, ...], dict[str, Any]]], sentinel: object) -> Callable[..., object]:
    """A function that records its arguments in ``calls`` and returns ``sentinel``."""

    def record(*args: Any, **kwargs: Any) -> object:
        calls.append((args, kwargs))
        return sentinel

    return record


# =============================================================================
# (a) THE CONFIGURATION
# =============================================================================

BLANK = [pytest.param(None, id="unset"), pytest.param("", id="empty"), pytest.param("   ", id="spaces"), pytest.param("\t\n", id="whitespace")]
MODES = [
    pytest.param("none", "none", id="none"),
    pytest.param("NONE", "none", id="NONE"),
    pytest.param(" None ", "none", id="None-with-spaces"),
    pytest.param("fly", "fly", id="fly"),
    pytest.param("FLY", "fly", id="FLY"),
    pytest.param(" FLY ", "fly", id="FLY-with-spaces"),
    pytest.param("Fly", "fly", id="Fly"),
    pytest.param("\tfLy\n", "fly", id="fLy-with-whitespace"),
]
BAD_MODES = ["flyio", "fly.io", "on", "true", "1", "suspend", "fl y", "none fly", "nonee", "fly,none", "machines"]
GOOD_MINUTES = [
    pytest.param("1", 1, id="1"),
    pytest.param("5", 5, id="5"),
    pytest.param("30", 30, id="30"),
    pytest.param(" 30 ", 30, id="30-with-spaces"),
    pytest.param("\t60\n", 60, id="60-with-whitespace"),
    pytest.param("1440", 1440, id="1440-a-day"),
    pytest.param("0005", 5, id="leading-zeros"),
]
BAD_MINUTES = [
    pytest.param("0", id="zero"),
    pytest.param("1441", id="a-day-and-a-minute"),
    pytest.param("-3", id="negative"),
    pytest.param("+5", id="a-plus-sign"),
    pytest.param("5.5", id="a-decimal"),
    pytest.param("five", id="a-word"),
    pytest.param("\u0665", id="an-arabic-indic-digit"),
    pytest.param("\uff11\uff15", id="fullwidth-digits"),
    pytest.param("1e3", id="an-exponent"),
    pytest.param("5 min", id="a-unit"),
    pytest.param("0x10", id="hexadecimal"),
    pytest.param("1_0", id="an-underscore"),
    pytest.param("99999999999999999999", id="huge"),
]


@pytest.mark.parametrize("value", BLANK)
def test_the_mode_is_none_when_unset_or_blank(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """SWS-001 — contract (a): ``LIBREFOLIO_IDLE_SUSPEND_MODE`` unset or blank is "none": the feature stays off."""
    print_section(f"SWS-001: idle_suspend_mode() with {value!r}")
    _set_or_unset(monkeypatch, MODE_VARIABLE, value)

    assert sleep_wake_config.idle_suspend_mode() == "none"
    print_success("none")


@pytest.mark.parametrize(("value", "mode"), MODES)
def test_the_mode_is_none_or_fly_in_any_case_with_spaces_around(monkeypatch: pytest.MonkeyPatch, value: str, mode: str) -> None:
    """SWS-002 — contract (a): "none" and "fly", in any case, with spaces or whitespace around, are "none" and "fly"."""
    print_section(f"SWS-002: idle_suspend_mode() with {value!r}")
    monkeypatch.setenv(MODE_VARIABLE, value)

    assert sleep_wake_config.idle_suspend_mode() == mode
    print_success(mode)


@pytest.mark.parametrize("value", BAD_MODES)
def test_any_other_mode_is_refused_naming_the_variable(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """SWS-003 — contract (a): any other value — a near miss, a boolean, a list, a word of its own — raises ``SleepWakeConfigError``, ``variable`` the variable, ``code`` ``IDLE_SUSPEND_MODE_INVALID``, the message naming the variable."""
    print_section(f"SWS-003: idle_suspend_mode() with {value!r}")
    monkeypatch.setenv(MODE_VARIABLE, value)

    with pytest.raises(SleepWakeConfigError) as caught:
        sleep_wake_config.idle_suspend_mode()
    assert (caught.value.variable, caught.value.code) == (MODE_VARIABLE, "IDLE_SUSPEND_MODE_INVALID")
    assert MODE_VARIABLE in str(caught.value), f"the message names the variable: {caught.value}"
    print_success("IDLE_SUSPEND_MODE_INVALID")


def test_the_mode_is_read_at_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-004 — contract (a): the variable set, changed, removed, set again: each call answers the value of the moment."""
    print_section("SWS-004: idle_suspend_mode() at every call")
    seen: list[str] = []

    for value in ("fly", " none ", None, "FLY"):
        _set_or_unset(monkeypatch, MODE_VARIABLE, value)
        seen.append(sleep_wake_config.idle_suspend_mode())

    assert seen == ["fly", "none", "none", "fly"]
    print_success("fly, none, none, fly")


@pytest.mark.parametrize("value", BLANK)
def test_the_minutes_are_five_when_unset_or_blank(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """SWS-005 — contract (a): ``LIBREFOLIO_IDLE_SUSPEND_MINUTES`` unset or blank is ``DEFAULT_IDLE_SUSPEND_MINUTES``, 5, an int."""
    print_section(f"SWS-005: idle_suspend_minutes() with {value!r}")
    _set_or_unset(monkeypatch, MINUTES_VARIABLE, value)

    assert getattr(sleep_wake_config, "DEFAULT_IDLE_SUSPEND_MINUTES", "<missing>") == 5
    minutes = sleep_wake_config.idle_suspend_minutes()
    assert (minutes, type(minutes)) == (5, int)
    print_success("5")


@pytest.mark.parametrize(("value", "minutes"), GOOD_MINUTES)
def test_ascii_digits_from_1_to_1440_are_the_minutes(monkeypatch: pytest.MonkeyPatch, value: str, minutes: int) -> None:
    """SWS-006 — contract (a): ASCII digits worth 1 to 1440 are that int; spaces around and leading zeros are allowed, as for the other values of the module."""
    print_section(f"SWS-006: idle_suspend_minutes() with {value!r}")
    monkeypatch.setenv(MINUTES_VARIABLE, value)

    result = sleep_wake_config.idle_suspend_minutes()
    assert (result, type(result)) == (minutes, int)
    print_success(str(minutes))


@pytest.mark.parametrize("value", BAD_MINUTES)
def test_any_other_minutes_are_refused_naming_the_variable(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """SWS-007 — contract (a): 0, 1441, a sign, a decimal, a word, a digit outside ASCII — which ``int()`` would take —, an exponent, a unit, hexadecimal, an underscore — which ``int()`` takes too —, a huge number: ``SleepWakeConfigError`` ``IDLE_SUSPEND_MINUTES_INVALID`` naming the variable."""
    print_section(f"SWS-007: idle_suspend_minutes() with {value!r}")
    monkeypatch.setenv(MINUTES_VARIABLE, value)

    with pytest.raises(SleepWakeConfigError) as caught:
        sleep_wake_config.idle_suspend_minutes()
    assert (caught.value.variable, caught.value.code) == (MINUTES_VARIABLE, "IDLE_SUSPEND_MINUTES_INVALID")
    assert MINUTES_VARIABLE in str(caught.value), f"the message names the variable: {caught.value}"
    print_success("IDLE_SUSPEND_MINUTES_INVALID")


def test_the_minutes_are_read_at_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-008 — contract (a): the variable set, changed, removed: each call answers the value of the moment."""
    print_section("SWS-008: idle_suspend_minutes() at every call")
    seen: list[int] = []

    for value in ("10", "20", None):
        _set_or_unset(monkeypatch, MINUTES_VARIABLE, value)
        seen.append(sleep_wake_config.idle_suspend_minutes())

    assert seen == [10, 20, 5]
    print_success("10, 20, 5")


# =============================================================================
# (b) THE FLY SUSPENDER
# =============================================================================

#: Statuses other than 2xx: a redirect is not followed, a refusal and a failure are told apart by their status.
OTHER_STATUSES = [302, 400, 401, 404, 409, 429, 500, 503]
#: Errors of the transport, each an ``httpx.HTTPError``.
TRANSPORT_ERRORS = [
    pytest.param(lambda request: httpx.ConnectError("provoked: no socket", request=request), id="ConnectError"),
    pytest.param(lambda request: httpx.ConnectTimeout("provoked", request=request), id="ConnectTimeout"),
    pytest.param(lambda request: httpx.ReadTimeout("provoked", request=request), id="ReadTimeout"),
    pytest.param(lambda request: httpx.WriteTimeout("provoked", request=request), id="WriteTimeout"),
    pytest.param(lambda request: httpx.PoolTimeout("provoked", request=request), id="PoolTimeout"),
    pytest.param(lambda request: httpx.ReadError("provoked", request=request), id="ReadError"),
    pytest.param(lambda request: httpx.RemoteProtocolError("provoked", request=request), id="RemoteProtocolError"),
]
#: The two variables, one or both missing or blank: not a Fly machine.
NOT_ON_FLY = [
    pytest.param({}, id="neither"),
    pytest.param({APP_VARIABLE: APP_NAME}, id="no-machine-id"),
    pytest.param({MACHINE_VARIABLE: MACHINE_ID}, id="no-app-name"),
    pytest.param({APP_VARIABLE: "", MACHINE_VARIABLE: MACHINE_ID}, id="app-name-empty"),
    pytest.param({APP_VARIABLE: APP_NAME, MACHINE_VARIABLE: "   "}, id="machine-id-blank"),
    pytest.param({APP_VARIABLE: " \t", MACHINE_VARIABLE: "\n"}, id="both-blank"),
]


def test_the_suspender_module_ships_its_socket_its_error_and_a_keyword_only_constructor() -> None:
    """SWS-009 — contract (b): ``FLY_API_SOCKET`` is "/.fly/api"; ``SuspendError`` is an ``Exception`` carrying ``reason``; ``FlySuspender`` takes ``transport`` (None), ``environ`` (None) and ``timeout`` (10.0), keyword-only, and nothing else that is required; ``suspend`` is a coroutine function, ``transport_factory`` a method."""
    print_section("SWS-009: FLY_API_SOCKET, SuspendError, FlySuspender's signature")
    parameters = inspect.signature(FlySuspender).parameters
    keyword_only = inspect.Parameter.KEYWORD_ONLY

    assert getattr(suspend_module, "FLY_API_SOCKET", "<missing>") == FLY_SOCKET
    assert issubclass(SuspendError, Exception)
    assert SuspendError(reason="not_on_fly").reason == "not_on_fly"
    assert {name: (parameters[name].kind, parameters[name].default) for name in ("transport", "environ", "timeout") if name in parameters} == {"transport": (keyword_only, None), "environ": (keyword_only, None), "timeout": (keyword_only, 10.0)}
    assert all(parameter.default is not inspect.Parameter.empty for parameter in parameters.values()), f"nothing else is required: {parameters}"
    assert inspect.iscoroutinefunction(FlySuspender.suspend)
    assert callable(getattr(FlySuspender, "transport_factory", None))
    print_success("/.fly/api; SuspendError.reason; transport, environ, timeout=10.0")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [200, 202, 204])
async def test_on_fly_suspend_posts_once_to_its_machine_without_body_or_token_and_a_2xx_returns_none(status: int) -> None:
    """SWS-010 — contract (b): with both variables, one ``POST http://flaps/v1/apps/<app>/machines/<id>/suspend`` with no body and no ``Authorization``; a 2xx returns None."""
    print_section(f"SWS-010: suspend() answered {status}")
    api = FlyApi(status)

    result = await _within(FlySuspender(transport=api.transport, environ=dict(ON_FLY)).suspend(), "suspend()")

    assert result is None
    assert [_request_shape(request) for request in api.requests] == [SUSPEND_REQUEST]
    print_success(f"one POST to {SUSPEND_URL}; {status}: None")


@pytest.mark.asyncio
@pytest.mark.parametrize("status", OTHER_STATUSES)
async def test_another_status_raises_suspend_error_http_status(status: int) -> None:
    """SWS-011 — contract (b): a status other than 2xx, a redirect included, raises ``SuspendError`` of reason "http_<status>", after its one request."""
    print_section(f"SWS-011: suspend() answered {status}")
    api = FlyApi(status)

    with pytest.raises(SuspendError) as caught:
        await _within(FlySuspender(transport=api.transport, environ=dict(ON_FLY)).suspend(), "suspend()")

    assert caught.value.reason == f"http_{status}"
    assert [_request_shape(request) for request in api.requests] == [SUSPEND_REQUEST]
    print_success(f"http_{status}")


@pytest.mark.asyncio
@pytest.mark.parametrize("error", TRANSPORT_ERRORS)
async def test_an_error_of_the_transport_raises_suspend_error_connection(error: Callable[[httpx.Request], Exception]) -> None:
    """SWS-012 — contract (b): an ``httpx.HTTPError`` of the transport — connecting, a timeout of any phase, reading, the protocol — raises ``SuspendError`` of reason "connection"."""
    print_section("SWS-012: suspend() meets an error of the transport")
    api = FlyApi(200)
    api.raises = error

    with pytest.raises(SuspendError) as caught:
        await _within(FlySuspender(transport=api.transport, environ=dict(ON_FLY)).suspend(), "suspend()")

    assert caught.value.reason == "connection"
    assert len(api.requests) == 1, f"one request, which failed: {api.requests}"
    print_success("connection")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["mapping", "process"])
@pytest.mark.parametrize("variables", NOT_ON_FLY)
async def test_without_both_variables_suspend_raises_not_on_fly_before_any_request(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str], source: str) -> None:
    """SWS-013 — contract (b): a variable missing, empty or blank — given as ``environ``, or in the process environment — raises ``SuspendError`` of reason "not_on_fly", and no request leaves."""
    print_section(f"SWS-013: suspend() with {variables!r} from the {source}")
    api = FlyApi(200)
    if source == "mapping":
        suspender = FlySuspender(transport=api.transport, environ=dict(variables))
    else:
        for name, value in variables.items():
            monkeypatch.setenv(name, value)
        suspender = FlySuspender(transport=api.transport)

    with pytest.raises(SuspendError) as caught:
        await _within(suspender.suspend(), "suspend()")

    assert caught.value.reason == "not_on_fly"
    assert api.requests == []
    print_success("not_on_fly, no request")


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["mapping", "process"])
async def test_the_variables_are_read_at_each_call(monkeypatch: pytest.MonkeyPatch, source: str) -> None:
    """SWS-014 — contract (b): the suspender is built before any variable is set; then the variables are set, changed, one removed: each call reads them as they are — from the mapping given, or from ``os.environ`` without one."""
    print_section(f"SWS-014: the variables read at each call, from the {source}")
    api = FlyApi(200)
    environ: dict[str, str] = {}
    suspender = FlySuspender(transport=api.transport, environ=environ) if source == "mapping" else FlySuspender(transport=api.transport)

    def put(name: str, value: str | None) -> None:
        if source == "process":
            _set_or_unset(monkeypatch, name, value)
        elif value is None:
            environ.pop(name, None)
        else:
            environ[name] = value

    outcomes: list[str] = []
    for app, machine in (("first-app", "machine-1"), ("second-app", "machine-2"), ("second-app", None)):
        put(APP_VARIABLE, app)
        put(MACHINE_VARIABLE, machine)
        try:
            await _within(suspender.suspend(), "suspend()")
            outcomes.append("sent")
        except SuspendError as error:
            outcomes.append(error.reason)

    assert outcomes == ["sent", "sent", "not_on_fly"]
    assert [str(request.url) for request in api.requests] == ["http://flaps/v1/apps/first-app/machines/machine-1/suspend", "http://flaps/v1/apps/second-app/machines/machine-2/suspend"]
    print_success("first, second, then not_on_fly")


@pytest.mark.asyncio
async def test_without_a_transport_the_suspender_sends_through_the_unix_socket_of_the_machines_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-015 — contract (b): ``transport_factory()`` returns a transport given as it is. Without one, it builds ``httpx.AsyncHTTPTransport(uds="/.fly/api")`` — the class replaced on ``httpx`` by a recorder —, and ``suspend()`` sends its request through a transport built that way."""
    print_section("SWS-015: the transport of the Machines API")
    api = FlyApi(200)
    sockets = SocketTransports(api)
    monkeypatch.setattr(httpx, "AsyncHTTPTransport", sockets)
    given = httpx.MockTransport(api.answer)

    assert FlySuspender(transport=given, environ=dict(ON_FLY)).transport_factory() is given
    suspender = FlySuspender(environ=dict(ON_FLY))
    built = suspender.transport_factory()
    await _within(suspender.suspend(), "suspend() through the socket's transport")

    assert sockets.built, "no transport built: without one, the suspender builds httpx.AsyncHTTPTransport(uds=...)"
    assert [construction.kwargs.get("uds") for construction in sockets.built] == [FLY_SOCKET] * len(sockets.built), f"every transport is built on the socket {FLY_SOCKET}: {[construction.kwargs for construction in sockets.built]}"
    assert any(built is construction.transport for construction in sockets.built), f"transport_factory() returns the transport it built: {built!r}"
    assert [_request_shape(request) for request in api.requests] == [SUSPEND_REQUEST]
    assert all(isinstance(carrier, int) for carrier in api.carriers), f"the request went through a transport built on the socket: {api.carriers}"
    print_success(f"AsyncHTTPTransport(uds={FLY_SOCKET!r}), and the request through it")


@pytest.mark.asyncio
@pytest.mark.parametrize(("given", "seconds"), [pytest.param(None, 10.0, id="default-10s"), pytest.param(2.5, 2.5, id="given-2.5s")])
async def test_the_request_carries_the_timeout_on_every_phase(given: float | None, seconds: float) -> None:
    """SWS-016 — contract (b): the request carries ``timeout`` — 10 s by default — for connecting, reading, writing and the pool."""
    print_section(f"SWS-016: the timeout, {seconds} s")
    api = FlyApi(200)
    options = {} if given is None else {"timeout": given}

    await _within(FlySuspender(transport=api.transport, environ=dict(ON_FLY), **options).suspend(), "suspend()")

    assert [request.extensions.get("timeout") for request in api.requests] == [{"connect": seconds, "read": seconds, "write": seconds, "pool": seconds}]
    print_success(f"{seconds} s on every phase")


# =============================================================================
# (c) THE MONITOR'S CONSTANTS AND SIGNATURES
# =============================================================================


def test_the_monitor_ships_its_constants_and_its_signatures() -> None:
    """SWS-017 — contracts (c), (h): the five constants have their values. ``IdleMonitor`` takes ``activity``, ``suspender``, ``minutes`` — required —, ``sleep`` (``asyncio.sleep``) and ``monotonic`` (``time.monotonic``), keyword-only; ``check`` and ``run`` are coroutine functions, ``request_check`` is not. ``start_idle_monitor``, ``stop_idle_monitor`` and ``idle_monitor_task`` are plain functions without parameters; ``request_idle_check`` is plain, its ``delay`` 2.0 by default."""
    print_section("SWS-017: the idle monitor's constants and signatures")
    expected = {"IDLE_CHECK_SECONDS": 30.0, "RESUME_GRACE_SECONDS": 60.0, "FAILURE_BACKOFF_FIRST_SECONDS": 30.0, "FAILURE_BACKOFF_MAX_SECONDS": 600.0, "WAKE_CHECK_DELAY_SECONDS": 2.0}
    parameters = inspect.signature(IdleMonitor).parameters
    empty, keyword_only = inspect.Parameter.empty, inspect.Parameter.KEYWORD_ONLY
    named = ("activity", "suspender", "minutes", "sleep", "monotonic")

    assert {name: getattr(idle_monitor, name, "<missing>") for name in expected} == expected
    assert {name: parameters[name].kind for name in named if name in parameters} == dict.fromkeys(named, keyword_only)
    assert [name for name in named if name in parameters and parameters[name].default is empty] == ["activity", "suspender", "minutes"]
    assert (parameters["sleep"].default, parameters["monotonic"].default) == (asyncio.sleep, time.monotonic)
    assert (inspect.iscoroutinefunction(IdleMonitor.check), inspect.iscoroutinefunction(IdleMonitor.run), inspect.iscoroutinefunction(IdleMonitor.request_check)) == (True, True, False)
    for name in ("start_idle_monitor", "stop_idle_monitor", "idle_monitor_task"):
        function = getattr(idle_monitor, name)
        assert not inspect.iscoroutinefunction(function) and not inspect.signature(function).parameters, f"{name}() is a plain function without parameters"
    assert not inspect.iscoroutinefunction(idle_monitor.request_idle_check)
    assert inspect.signature(idle_monitor.request_idle_check).parameters["delay"].default == 2.0
    print_success("30, 60, 30, 600, 2; the signatures")


# =============================================================================
# (d) A CHECK
# =============================================================================

#: What makes the activity busy, and the reason it lists.
BUSY_SOURCES = [
    pytest.param("wake-request", "requests", id="a-wake-request-in-flight"),
    pytest.param("user-request", "requests", id="a-user-request-in-flight"),
    pytest.param("span", "export", id="a-busy-span"),
    pytest.param("check-true", "backup", id="a-check-answering-true"),
    pytest.param("check-raising", "backup", id="a-check-that-raises"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("minutes", [1, MINUTES, 1440])
async def test_a_check_suspends_at_exactly_n_minutes_of_silence_and_not_a_second_before(activity: RecordingActivity, timeline: Timeline, minutes: int) -> None:
    """SWS-018 — contracts (d), (j): nothing busy, silent for N×60 − 1 s: "active", no call; silent for exactly N×60 s: "suspended", one call to ``suspend()`` — for N = 1, 5 and 1440."""
    print_section(f"SWS-018: the threshold of {minutes} minute(s)")
    rig = _rig(activity, timeline, minutes=minutes)

    activity.clock.now = activity.started_at + minutes * 60 - 1
    before = await _check(rig.monitor)
    calls_before = rig.suspender.calls
    activity.clock.now = activity.started_at + minutes * 60
    at = await _check(rig.monitor)

    assert (before, calls_before) == ("active", 0)
    assert (at, rig.suspender.calls) == ("suspended", 1)
    print_success(f"{minutes * 60 - 1} s: active; {minutes * 60} s: suspended")


@pytest.mark.asyncio
@pytest.mark.parametrize("idle", [pytest.param(0.0, id="silent-for-0s"), pytest.param(LONG_IDLE, id="silent-far-past-the-threshold")])
@pytest.mark.parametrize(("source", "reason"), BUSY_SOURCES)
async def test_a_check_is_busy_while_any_reason_is_listed_whatever_the_idle_time(rig: Rig, timeline: Timeline, source: str, reason: str, idle: float) -> None:
    """SWS-019 — contract (d): a request in flight — a wake-up's or the user's —, a busy span, a busy check answering True or raising: "busy", without calling ``suspend()``, whether the silence is 0 s or far past the threshold — the busy reasons come before the idle time."""
    print_section(f"SWS-019: busy by {source}, idle {idle} s")
    rig.activity.clock.now = rig.activity.started_at + idle

    with _busy_by(rig.activity, source):
        outcome = await _check(rig.monitor)

    assert outcome == "busy"
    assert rig.suspender.calls == 0
    assert reason in _readings(timeline)[-1], f"Precondition: the check read {reason!r} among the reasons: {_readings(timeline)}"
    print_success(f"busy ({reason})")


@pytest.mark.asyncio
async def test_a_check_reads_the_busy_reasons_off_the_event_loop_thread(rig: Rig, timeline: Timeline) -> None:
    """SWS-020 — contract (d): a busy check may read files: ``busy_reasons()`` runs in another thread than the event loop's."""
    print_section("SWS-020: busy_reasons() off the event loop")

    outcome = await _check(rig.monitor)

    threads = [entry[2] for _, entry in timeline.kinds("reading")]
    assert outcome == "active"
    assert threads and threading.get_ident() not in threads, f"read on the event loop's thread: {threads}"
    print_success("read in a worker thread")


@pytest.mark.asyncio
async def test_a_suspend_that_returns_is_suspended_and_logged_with_the_idle_time_and_the_minutes(rig: Rig) -> None:
    """SWS-021 — contract (d): silent for 342 s past a threshold of 300, ``suspend()`` returns: "suspended", one call, logged once — INFO, "Idle suspend requested", ``minutes`` 5 and ``idle_s`` the silence, to the second."""
    print_section("SWS-021: Idle suspend requested")
    idle = THRESHOLD_SECONDS + 42.0
    rig.activity.clock.now = rig.activity.started_at + idle

    with _monitor_log() as events:
        outcome = await _check(rig.monitor)

    requested = _logged(events, SUSPEND_REQUESTED)
    assert (outcome, rig.suspender.calls) == ("suspended", 1)
    assert [(entry.get("log_level"), entry.get("minutes")) for entry in requested] == [("info", MINUTES)]
    assert requested[0].get("idle_s") == pytest.approx(idle, abs=1.0), f"idle_s is the silence: {requested[0]}"
    print_success(f"INFO, minutes {MINUTES}, idle_s {idle}")


# =============================================================================
# (e) A FAILED SUSPEND
# =============================================================================

#: Failures of the suspender that are not ``SuspendError``: all of reason "error".
OTHER_FAILURES = [
    pytest.param(lambda: RuntimeError("provoked"), id="RuntimeError"),
    pytest.param(lambda: OSError(5, "provoked"), id="OSError"),
    pytest.param(lambda: KeyError("provoked"), id="KeyError"),
    pytest.param(lambda: TimeoutError("provoked"), id="TimeoutError"),
    pytest.param(lambda: httpx.ConnectError("provoked"), id="an-httpx-error-not-wrapped"),
]


@pytest.mark.asyncio
async def test_a_failed_suspend_waits_out_its_backoff_touching_nothing_then_tries_again(rig: Rig, timeline: Timeline) -> None:
    """SWS-022 — contract (d), (e): ``suspend()`` raises ``SuspendError`` "http_503": "failed", ``retry_not_before`` 30 s on the monotonic clock. A millisecond before it: "waiting", and neither the busy reasons, nor the idle time, nor ``suspend()`` is read or called. At it: a new attempt."""
    print_section("SWS-022: failed, waiting, then a new attempt")
    rig.activity.clock.now = rig.activity.started_at + LONG_IDLE
    rig.suspender.fail_with = _http_503

    first = await _check(rig.monitor)
    retry_at = rig.monitor.retry_not_before
    touched = _touched(rig, timeline)
    rig.monotonic.now = retry_at - 0.001
    waiting = await _check(rig.monitor)
    touched_while_waiting = _touched(rig, timeline)
    rig.monotonic.now = retry_at
    again = await _check(rig.monitor)

    assert first == "failed"
    assert retry_at == pytest.approx(MONOTONIC_START + 30.0)
    assert waiting == "waiting"
    assert touched_while_waiting == touched, f"nothing read or called while waiting: {touched} → {touched_while_waiting}"
    assert (again, rig.suspender.calls) == ("failed", 2)
    print_success("failed; waiting, nothing touched; tried again at the retry")


@pytest.mark.asyncio
async def test_the_backoff_doubles_from_30_to_600_seconds(rig: Rig) -> None:
    """SWS-023 — contract (e): seven failures in a row, each tried at the moment its backoff allows: backoffs 30, 60, 120, 240, 480, 600, 600 s."""
    print_section("SWS-023: 30, 60, 120, 240, 480, 600, 600")
    rig.activity.clock.now = rig.activity.started_at + LONG_IDLE
    rig.suspender.fail_with = _http_503
    observed: list[tuple[str, float]] = []

    for _ in BACKOFFS:
        outcome = await _check(rig.monitor)
        observed.append((outcome, rig.monitor.retry_not_before - rig.monotonic.now))
        rig.monotonic.now = rig.monitor.retry_not_before

    assert [outcome for outcome, _ in observed] == ["failed"] * len(BACKOFFS)
    assert [backoff for _, backoff in observed] == pytest.approx(list(BACKOFFS))
    print_success(f"{[backoff for _, backoff in observed]}")


@pytest.mark.asyncio
async def test_the_bounds_of_the_backoff_are_read_at_the_call(rig: Rig, monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-024 — contract (e): with ``FAILURE_BACKOFF_FIRST_SECONDS`` 7 and ``FAILURE_BACKOFF_MAX_SECONDS`` 20 set on the module after the monitor was built: 7, 14, 20, 20."""
    print_section("SWS-024: the bounds read at the call")
    monkeypatch.setattr(idle_monitor, "FAILURE_BACKOFF_FIRST_SECONDS", 7.0)
    monkeypatch.setattr(idle_monitor, "FAILURE_BACKOFF_MAX_SECONDS", 20.0)
    rig.activity.clock.now = rig.activity.started_at + LONG_IDLE
    rig.suspender.fail_with = _http_503
    backoffs: list[float] = []

    for _ in range(4):
        assert await _check(rig.monitor) == "failed"
        backoffs.append(rig.monitor.retry_not_before - rig.monotonic.now)
        rig.monotonic.now = rig.monitor.retry_not_before

    assert backoffs == pytest.approx([7.0, 14.0, 20.0, 20.0])
    print_success("7, 14, 20, 20")


@pytest.mark.asyncio
async def test_one_warning_per_streak_of_failures_and_a_success_starts_a_new_streak(rig: Rig) -> None:
    """SWS-025 — contract (e): three failures "http_503", a success, two failures "connection". One WARNING "Idle suspend failed" per streak, at its first failure — ``reason`` and ``retry_in_s`` 30 —, none for the failures that follow in a streak; the success logs "Idle suspend requested", and the backoff starts again at 30 s."""
    print_section("SWS-025: one warning per streak")
    rig.activity.clock.now = rig.activity.started_at + LONG_IDLE
    steps: list[tuple[Callable[[], SuspendError] | None, str, float | None]] = [
        (_http_503, "failed", 30.0),
        (_http_503, "failed", 60.0),
        (_http_503, "failed", 120.0),
        (None, "suspended", None),
        (_connection_lost, "failed", 30.0),
        (_connection_lost, "failed", 60.0),
    ]
    observed: list[tuple[str, float | None]] = []

    with _monitor_log() as events:
        for fail_with, _, _ in steps:
            rig.suspender.fail_with = fail_with
            outcome = await _check(rig.monitor)
            backoff = rig.monitor.retry_not_before - rig.monotonic.now if outcome == "failed" else None
            observed.append((outcome, backoff))
            if outcome == "failed":
                rig.monotonic.now = rig.monitor.retry_not_before

    warnings = [(entry.get("reason"), entry.get("retry_in_s")) for entry in _logged(events, SUSPEND_FAILED) if entry.get("log_level") == "warning"]
    assert [outcome for outcome, _ in observed] == [outcome for _, outcome, _ in steps]
    assert [backoff for _, backoff in observed] == [pytest.approx(backoff) if backoff is not None else None for _, _, backoff in steps]
    assert warnings == [("http_503", 30.0), ("connection", 30.0)], f"one warning per streak, at its first failure: {_logged(events, SUSPEND_FAILED)}"
    assert [entry.get("log_level") for entry in _logged(events, SUSPEND_REQUESTED)] == ["info"]
    print_success("two streaks, two warnings; the backoff restarted at 30 s")


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", OTHER_FAILURES)
async def test_any_other_exception_of_the_suspender_is_a_failure_of_reason_error(rig: Rig, failure: Callable[[], BaseException]) -> None:
    """SWS-026 — contract (e): ``suspend()`` raises an ``Exception`` that is not a ``SuspendError`` — an httpx error it did not wrap included —: nothing propagates; "failed", the backoff 30 s, one WARNING of reason "error"."""
    print_section("SWS-026: another exception of the suspender")
    rig.activity.clock.now = rig.activity.started_at + LONG_IDLE
    rig.suspender.fail_with = failure

    with _monitor_log() as events:
        outcome = await _check(rig.monitor)

    assert outcome == "failed"
    assert rig.monitor.retry_not_before - rig.monotonic.now == pytest.approx(30.0)
    assert [(entry.get("reason"), entry.get("retry_in_s")) for entry in _logged(events, SUSPEND_FAILED) if entry.get("log_level") == "warning"] == [("error", 30.0)]
    print_success("failed, reason error")


# =============================================================================
# (f) THE LOOP
# =============================================================================

#: The loop's first check made to end each way; how many readings and calls to ``suspend()`` it shows; the wait after it.
WAITS = [
    pytest.param("active", (1, 0), "regular", id="after-active"),
    pytest.param("busy", (1, 0), "regular", id="after-busy"),
    pytest.param("waiting", (0, 0), "regular", id="after-waiting"),
    pytest.param("suspended", (1, 1), "grace", id="after-suspended"),
    pytest.param("failed", (1, 1), "grace", id="after-failed"),
]


@pytest.mark.asyncio
async def test_the_loop_checks_at_once_then_after_every_regular_wait_and_returns_on_its_stop(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-027 — contract (f): with checks every 10 ms, the loop's first check comes before any wait, and two more follow by themselves; once its stop event is set the loop returns None, within the deadline."""
    print_section("SWS-027: the loop")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", SHORT_CHECK_SECONDS)
    stop = asyncio.Event()

    async with _running(rig, stop) as task:
        await timeline.until(lambda: timeline.count("reading") >= 3, "three checks of the loop")
        stop.set()
        await _ended(task, "the loop, once its stop event was set")

    entries = timeline.entries
    first = next(position for position, entry in enumerate(entries) if entry[0] == "reading")
    assert [entry for entry in entries[:first] if entry[0] == "sleep" and entry[1] > 0] == [], f"the first check comes at once: {entries[: first + 1]}"
    assert rig.suspender.calls == 0
    print_success(f"{timeline.count('reading')} checks, the first at once; returned on its stop")


@pytest.mark.asyncio
@pytest.mark.parametrize(("outcome", "touched", "wait"), WAITS)
async def test_the_wait_after_a_check_is_the_regular_one_or_at_least_the_resume_grace(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch, outcome: str, touched: tuple[int, int], wait: str) -> None:
    """SWS-028 — contract (f): the loop's first check ends ``outcome``; the wait that follows, through the injected ``sleep``, is ``IDLE_CHECK_SECONDS`` (1000 here) after "active", "busy" and "waiting", at least ``RESUME_GRACE_SECONDS`` (2000 here) after "suspended" and "failed" — whose backoff, 50 s, is shorter than the grace."""
    print_section(f"SWS-028: the wait after {outcome}")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    monkeypatch.setattr(idle_monitor, "RESUME_GRACE_SECONDS", LONG_GRACE_SECONDS)
    monkeypatch.setattr(idle_monitor, "FAILURE_BACKOFF_FIRST_SECONDS", SHORT_BACKOFF_SECONDS)
    stop = asyncio.Event()

    with ExitStack() as held:
        await _prepare(rig, held, outcome)
        mark = len(timeline)
        async with _running(rig, stop):
            await timeline.until(lambda: _first_long_sleep(timeline, mark) is not None, f"the loop's wait after a check {outcome}, through its sleep")

    found = _first_long_sleep(timeline, mark)
    assert found is not None
    position, seconds = found
    first_check = timeline.entries[mark:position]
    shown = (sum(1 for entry in first_check if entry[0] == "reading"), sum(1 for entry in first_check if entry[0] == "suspend"))
    assert shown == touched, f"Precondition: the loop's first check ended {outcome}: {first_check}"
    if wait == "regular":
        assert seconds == pytest.approx(LONG_CHECK_SECONDS), f"after {outcome}: sleep(IDLE_CHECK_SECONDS), got sleep({seconds})"
    else:
        assert seconds >= LONG_GRACE_SECONDS - 1e-6, f"after {outcome}: at least RESUME_GRACE_SECONDS, got sleep({seconds})"
    print_success(f"sleep({seconds})")


@pytest.mark.asyncio
@pytest.mark.parametrize("when", ["during-a-wait", "during-a-check", "before-the-loop-starts"])
async def test_the_stop_ends_the_loop_promptly(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch, when: str) -> None:
    """SWS-029 — contract (f): with a regular wait of 1000 s, the stop ends the loop within the deadline, returning None: set during its first wait; set while its first check is held — the check ends, and no other follows —; or set before the loop starts."""
    print_section(f"SWS-029: the stop, {when}")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    rig.activity.register_busy_check("gate", rig.gate)
    stop = asyncio.Event()
    if when == "before-the-loop-starts":
        stop.set()
    if when == "during-a-check":
        rig.gate.arm()

    async with _running(rig, stop) as task:
        if when == "during-a-wait":
            await timeline.until(lambda: _first_long_sleep(timeline, 0) is not None, "the loop's first regular wait")
            stop.set()
        elif when == "during-a-check":
            await timeline.until(lambda: timeline.count("gate-entered") >= 1, "the loop's first check, held at the gate")
            stop.set()
            rig.gate.release()
        await _ended(task, f"the loop, stopped {when}")

    if when == "before-the-loop-starts":
        assert timeline.count("reading") <= 1
    else:
        assert timeline.count("reading") == 1, f"one check, then the stop: {_readings(timeline)}"
    print_success(f"returned; {timeline.count('reading')} check(s)")


@pytest.mark.asyncio
async def test_a_check_that_raises_is_logged_and_the_loop_goes_on(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-030 — contract (f): reading the idle time raises once, so the first check raises: logged once — "Idle check failed", at WARNING or ERROR —, and the loop goes on: two more checks, the task still running, until its stop."""
    print_section("SWS-030: a check that raises")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", SHORT_CHECK_SECONDS)
    monkeypatch.setattr(idle_monitor, "RESUME_GRACE_SECONDS", SHORT_CHECK_SECONDS)
    rig.activity.idle_failures.append(RuntimeError("provoked: reading the idle time fails"))
    stop = asyncio.Event()

    with _monitor_log() as events:
        async with _running(rig, stop) as task:
            await timeline.until(lambda: timeline.count("reading") >= 3, "two checks after the one that raised")
            still_running = not task.done()
            stop.set()
            await _ended(task, "the loop after a check that raised")

    failures = [entry.get("log_level") for entry in _logged(events, CHECK_FAILED)]
    assert rig.activity.idle_failures == [], "Precondition: the first check read the idle time, which raised"
    assert still_running
    assert len(failures) == 1 and failures[0] in ("warning", "error"), f"logged once, at WARNING or ERROR: {failures}"
    print_success(f"logged at {failures[0]}; the loop went on")


# =============================================================================
# (g) A REQUESTED CHECK
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("delay", [pytest.param(0.0, id="now"), pytest.param(0.05, id="in-50ms")])
async def test_a_requested_check_ends_the_regular_wait_early(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch, delay: float) -> None:
    """SWS-031 — contract (g): during a regular wait of 1000 s, ``request_check(delay)``: a check follows, and the regular wait never came to its end."""
    print_section(f"SWS-031: request_check({delay})")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    stop = asyncio.Event()

    async with _running(rig, stop):
        await timeline.until(lambda: _first_long_sleep(timeline, 0) is not None, "the loop's first regular wait")
        rig.monitor.request_check(delay)
        await timeline.until(lambda: timeline.count("reading") >= 2, f"the check requested in {delay} s")

    assert [entry for entry in timeline.entries if entry[0] == "slept" and entry[1] > REAL_SLEEP_LIMIT] == []
    print_success("checked before the end of the regular wait")


@pytest.mark.asyncio
async def test_a_check_requested_from_another_thread_follows(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-032 — contract (g): ``request_check(0.0)`` called from a worker thread during a regular wait of 1000 s: a check follows. The loop runs in debug mode, where a call into it from another thread that is not thread-safe raises instead of passing by luck."""
    print_section("SWS-032: request_check from another thread")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    loop = asyncio.get_running_loop()
    debug = loop.get_debug()
    loop.set_debug(True)
    stop = asyncio.Event()
    try:
        async with _running(rig, stop):
            await timeline.until(lambda: _first_long_sleep(timeline, 0) is not None, "the loop's first regular wait")
            await _within(asyncio.to_thread(rig.monitor.request_check, 0.0), "request_check(0.0) in a worker thread")
            await timeline.until(lambda: timeline.count("reading") >= 2, "the check requested from a worker thread")
    finally:
        loop.set_debug(debug)

    print_success("a check followed")


@pytest.mark.asyncio
async def test_requests_made_while_a_check_runs_make_one_check_after_it(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-033 — contract (g): while a check is held, four ``request_check(0.0)`` — three from the loop, one from a worker thread. Released, the held check is followed by exactly one check, then by the end of a regular wait (50 ms here), the marker that the loop went back to waiting: a second requested check would have come before it, a pending request ending a wait at once."""
    print_section("SWS-033: four requests, one check")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", MARKER_CHECK_SECONDS)
    rig.activity.register_busy_check("gate", rig.gate)
    stop = asyncio.Event()

    async with _running(rig, stop):
        await timeline.until(lambda: timeline.count("reading") >= 1, "the loop's first check")
        rig.gate.arm()
        await timeline.until(lambda: timeline.count("gate-entered") >= 1, "a check held at the gate")
        held = timeline.kinds("gate-entered")[0][0]
        for _ in range(3):
            rig.monitor.request_check(0.0)
        await _within(asyncio.to_thread(rig.monitor.request_check, 0.0), "request_check(0.0) in a worker thread")
        rig.gate.release()
        await timeline.until(lambda: _checks_before_the_regular_wait(timeline, held) is not None, "the held check, the requested one, then a check after a regular wait")

    between = _checks_before_the_regular_wait(timeline, held)
    assert between == 1, f"four requests during a check make one check after it, not {between}: {timeline.entries[held:][:20]}"
    print_success("one check, then the regular wait")


# =============================================================================
# (h) THE MODULE'S FUNCTIONS
# =============================================================================

#: The mode as the environment gives it, and the errors it logs: unset, "none", or a value that cannot be used.
NONE_MODES = [pytest.param(None, 0, id="unset"), pytest.param(" None ", 0, id="none"), pytest.param("hibernate", 1, id="invalid-logged-once")]


@pytest.mark.asyncio
@pytest.mark.parametrize(("value", "errors"), NONE_MODES)
async def test_in_none_mode_start_idle_monitor_starts_and_registers_nothing(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity, timeline: Timeline, value: str | None, errors: int) -> None:
    """SWS-034 — contract (h): the mode unset, "none", or invalid — logged once, at ERROR, and taken as "none" —: ``start_idle_monitor()`` returns None, starts no task, builds no suspender, registers no busy check, and logs no "Idle monitor started"."""
    print_section(f"SWS-034: start_idle_monitor() with the mode {value!r}")
    fakes = FlyFakes(timeline)
    fakes.install(monkeypatch)
    _set_or_unset(monkeypatch, MODE_VARIABLE, value)
    tasks_before = asyncio.all_tasks()

    with _monitor_log() as events:
        async with _started() as started:
            new_tasks = asyncio.all_tasks() - tasks_before

    assert (started, new_tasks) == (None, set()), f"no monitor started: {started}, {new_tasks}"
    assert (fakes.built, activity.registered) == ([], [])
    assert _logged(events, MONITOR_STARTED) == []
    assert _levels(events, "error", "critical") == ["error"] * errors, f"{errors} error(s) logged: {events}"
    print_success("nothing started" + (", the invalid mode logged once" if errors else ""))


@pytest.mark.asyncio
async def test_in_fly_mode_start_idle_monitor_reads_its_globals_at_the_call_and_starts_one_monitor(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity, timeline: Timeline) -> None:
    """SWS-035 — contract (h): every global of the module replaced — the mode "fly", 9 minutes, ``current_activity`` answering another activity than the process's, ``FlySuspender``, ``get_tool_executor``, ``backup_in_progress`` —: ``start_idle_monitor()`` returns None and starts one task, ``idle_monitor_task()``; ``FlySuspender()`` built once, without arguments; "tools" and "backup" registered on the other activity, which the monitor reads, and whose checks call the replaced globals; "Idle monitor started" logged once, INFO, mode "fly", minutes 9. ``stop_idle_monitor()`` returns that task, which returns; then ``request_idle_check`` does nothing."""
    print_section("SWS-035: start_idle_monitor() in fly mode")
    other = RecordingActivity(FakeClock(START), timeline, "other")
    fakes = _fly_globals(monkeypatch, timeline, minutes=GLOBALS_MINUTES)
    monkeypatch.setattr(idle_monitor, "current_activity", lambda: other)
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)

    with _monitor_log() as events:
        async with _started() as task:
            assert isinstance(task, asyncio.Task), f"idle_monitor_task() is the monitor's task: {task!r}"
            running = not task.done()
            await timeline.until(lambda: timeline.count("reading") >= 1, "the monitor's first check")
            stopped = idle_monitor.stop_idle_monitor()
            await _ended(task, "the monitor, after stop_idle_monitor()")
    idle_monitor.request_idle_check(0.0)

    assert running and stopped is task
    assert fakes.built == [((), {})], f"FlySuspender() built once, without arguments: {fakes.built}"
    assert {"tools", "backup"} <= set(other.registered) and activity.registered == [], f"the checks on current_activity() as read at the call: {other.registered}, {activity.registered}"
    assert {entry[3] for _, entry in timeline.kinds("reading")} == {"other"}
    assert fakes.executor.snapshots >= 1 and fakes.backup.calls >= 1, "the checks call the replaced get_tool_executor and backup_in_progress"
    assert [(entry.get("log_level"), entry.get("mode"), entry.get("minutes")) for entry in _logged(events, MONITOR_STARTED)] == [("info", "fly", GLOBALS_MINUTES)]
    print_success("one task; FlySuspender(); tools and backup; started, fly, 9; stopped")


@pytest.mark.asyncio
async def test_invalid_minutes_are_logged_once_and_five_are_used(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity, timeline: Timeline) -> None:
    """SWS-036 — contract (h): mode "fly" and ``LIBREFOLIO_IDLE_SUSPEND_MINUTES=0`` in the environment: one warning or error logged, "Idle monitor started" with minutes 5, and an activity silent for exactly 300 s, nothing busy, is suspended at the first check — "Idle suspend requested", minutes 5."""
    print_section("SWS-036: invalid minutes, 5 used")
    fakes = _fly_environment(monkeypatch, timeline, minutes="0")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    activity.clock.now = activity.started_at + 5 * 60

    with _monitor_log() as events:
        async with _started():
            await timeline.until(lambda: fakes.suspender.calls >= 1, "the first check, at 300 s of silence, suspends")

    assert len(_levels(events, "warning", "error", "critical")) == 1, f"the invalid minutes logged once: {events}"
    assert [entry.get("minutes") for entry in _logged(events, MONITOR_STARTED)] == [5]
    assert [entry.get("minutes") for entry in _logged(events, SUSPEND_REQUESTED)] == [5]
    print_success("logged once; 5 minutes")


@pytest.mark.asyncio
async def test_request_idle_check_forwards_to_the_running_monitor_from_any_thread(monkeypatch: pytest.MonkeyPatch, timeline: Timeline) -> None:
    """SWS-037 — contract (h): the monitor started, in its regular wait of 1000 s: ``request_idle_check(0.0)`` from the event loop, then from a worker thread — the loop in debug mode —, each followed by a check."""
    print_section("SWS-037: request_idle_check() forwards")
    _fly_globals(monkeypatch, timeline)
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    loop = asyncio.get_running_loop()
    debug = loop.get_debug()
    loop.set_debug(True)
    try:
        async with _started():
            await timeline.until(lambda: timeline.count("reading") >= 1, "the monitor's first check")
            idle_monitor.request_idle_check(0.0)
            await timeline.until(lambda: timeline.count("reading") >= 2, "the check requested from the event loop")
            await _within(asyncio.to_thread(idle_monitor.request_idle_check, 0.0), "request_idle_check(0.0) in a worker thread")
            await timeline.until(lambda: timeline.count("reading") >= 3, "the check requested from a worker thread")
    finally:
        loop.set_debug(debug)

    print_success("two requests, two checks")


def test_in_a_fresh_interpreter_no_monitor_exists_and_requests_do_nothing() -> None:
    """SWS-038 — contract (h): a fresh interpreter, the mode unset, before any monitor: ``idle_monitor_task()`` and ``stop_idle_monitor()`` are None, ``request_idle_check()`` and ``request_idle_check(0.0)`` do nothing, ``start_idle_monitor()`` returns None and leaves them None, and no task was started."""
    print_section("SWS-038: a fresh interpreter")
    environment = {name: value for name, value in os.environ.items() if name not in (MODE_VARIABLE, MINUTES_VARIABLE)}

    completed = subprocess.run([sys.executable, "-c", FRESH_INTERPRETER_PROBE], cwd=REPO_ROOT, env=environment, capture_output=True, text=True, timeout=PROCESS_WAIT_SECONDS, check=False)

    lines = [line for line in completed.stdout.splitlines() if line.startswith(PROBE_MARK)]
    assert completed.returncode == 0 and len(lines) == 1, f"the probe ended {completed.returncode}: stdout {completed.stdout[-2000:]!r}, stderr {completed.stderr[-4000:]!r}"
    assert json.loads(lines[0][len(PROBE_MARK) :]) == {"task_before": "None", "stop_before": "None", "start": "None", "task_after": "None", "stop_after": "None", "other_tasks": 0}
    print_success("None, None, no-op, None, None, no task")


# =============================================================================
# (i) THE BUSY CHECKS
# =============================================================================

#: ``((pending tools, backup in progress), the reasons of the two listed)``, in order.
BUSY_SCRIPT = [
    ((0, False), set()),
    ((3, False), {"tools"}),
    ((0, False), set()),
    ((0, True), {"backup"}),
    ((1, True), {"tools", "backup"}),
    ((0, False), set()),
]


@pytest.mark.asyncio
async def test_started_in_fly_mode_the_monitor_lists_tools_and_backup_while_they_run(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity, timeline: Timeline) -> None:
    """SWS-039 — contract (i): started in "fly" mode from the environment, on the process's activity: "tools" is listed while the tool executor's snapshot has ``pending > 0``, "backup" while ``backup_in_progress()`` answers True, both together, and neither otherwise."""
    print_section("SWS-039: the busy checks tools and backup")
    fakes = _fly_environment(monkeypatch, timeline)
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    listed: list[set[str]] = []

    async with _started():
        await timeline.until(lambda: timeline.count("reading") >= 1, "the monitor's first check")
        for (pending, backup), _ in BUSY_SCRIPT:
            fakes.executor.pending, fakes.backup.answer = pending, backup
            listed.append(set(activity.busy_reasons()) & {"tools", "backup"})

    assert {"tools", "backup"} <= set(activity.registered), f"registered on current_activity(): {activity.registered}"
    assert listed == [reasons for _, reasons in BUSY_SCRIPT]
    print_success("tools while pending, backup while in progress")


@pytest.mark.asyncio
async def test_the_started_monitor_never_suspends_while_a_reason_is_listed(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity, timeline: Timeline) -> None:
    """SWS-040 — contract (i): silent far past the threshold from the start, with a wake-up request in flight, a tool pending and a backup in progress, the monitor started in "fly" mode checks every 10 ms. The reasons go one by one — the request, the tools, the backup —: no ``suspend()`` while any is listed, over two checks begun after each change; once none is, ``suspend()`` comes, and every call to it follows a reading that listed nothing."""
    print_section("SWS-040: never suspended while busy")
    fakes = _fly_environment(monkeypatch, timeline)
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", SHORT_CHECK_SECONDS)
    activity.clock.now = activity.started_at + LONG_IDLE
    fakes.executor.pending, fakes.backup.answer = 1, True
    phases: list[tuple[list[set[str]], int]] = []

    with ExitStack() as in_flight:
        in_flight.enter_context(activity.request(presence=False))
        async with _started():
            phases.append((await _checks_after(timeline, 0, 3, "with every reason"), fakes.suspender.calls))
            mark = len(timeline)
            in_flight.close()
            phases.append((await _checks_after(timeline, mark, 3, "once the request is over"), fakes.suspender.calls))
            mark = len(timeline)
            fakes.executor.pending = 0
            phases.append((await _checks_after(timeline, mark, 3, "once the tools are done"), fakes.suspender.calls))
            fakes.backup.answer = False
            await timeline.until(lambda: fakes.suspender.calls >= 1, "suspend() once nothing is listed")

    assert phases == [([{"requests", "tools", "backup"}] * 2, 0), ([{"tools", "backup"}] * 2, 0), ([{"backup"}] * 2, 0)]
    assert _readings_before_suspends(timeline) and set(_readings_before_suspends(timeline)) == {()}, f"suspend() only after a reading that listed nothing: {_readings_before_suspends(timeline)}"
    print_success("not while busy; suspended once nothing was listed")


# =============================================================================
# (j) ACCEPTANCE
# =============================================================================


@pytest.mark.asyncio
async def test_with_fly_and_seven_minutes_the_monitor_suspends_at_seven_minutes_of_silence_not_before(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity, timeline: Timeline) -> None:
    """SWS-041 — contract (j), end to end: " FLY " and 7 minutes in the environment, the user's last request at a moment of the fake clock, nothing busy. 419 s after it, two complete checks call nothing; at 420 s ``suspend()`` comes — "Idle suspend requested", minutes 7, idle_s 420. With a check every 30 s in production, that is within 7 minutes and 30 s of the last request."""
    print_section("SWS-041: fly, 7 minutes")
    fakes = _fly_environment(monkeypatch, timeline, mode=" FLY ", minutes=str(ACCEPTANCE_MINUTES))
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", SHORT_CHECK_SECONDS)
    activity.clock.now = START + 1_000.0
    with activity.request():
        pass
    last_request = activity.last_user_request_at
    assert last_request is not None
    activity.clock.now = last_request + ACCEPTANCE_MINUTES * 60 - 1

    with _monitor_log() as events:
        async with _started():
            before = await _checks_after(timeline, 0, 3, f"at {ACCEPTANCE_MINUTES * 60 - 1} s of silence")
            calls_before = fakes.suspender.calls
            activity.clock.now = last_request + ACCEPTANCE_MINUTES * 60
            await timeline.until(lambda: fakes.suspender.calls >= 1, f"suspend() at {ACCEPTANCE_MINUTES * 60} s of silence")

    requested = _logged(events, SUSPEND_REQUESTED)
    assert (before, calls_before) == ([set(), set()], 0), "419 s: nothing busy, nothing suspended"
    assert [entry.get("minutes") for entry in requested] == [ACCEPTANCE_MINUTES]
    assert requested[0].get("idle_s") == pytest.approx(ACCEPTANCE_MINUTES * 60, abs=1.0)
    print_success("419 s: not suspended; 420 s: suspended")


# =============================================================================
# (k) THE WAKE-UP
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("ending", ["returns", "raises"])
async def test_each_wake_up_asks_for_an_idle_check_in_its_run_once_the_run_finished(monkeypatch: pytest.MonkeyPatch, ending: str) -> None:
    """SWS-042 — contract (k): one wake-up, its run returning or raising, ``idle_monitor.request_idle_check`` replaced by a recorder: called once, with 2.0, in the run's task, once the run is over and "Wake-up run finished" logged — after "Wake-up run failed" when it raised. The answer is 200, its body the run's status."""
    print_section(f"SWS-042: the wake-up's hook, a run that {ending}")
    token = _wake_token(monkeypatch)
    run = FakeRun()
    if ending == "raises":
        run.failure = RuntimeError("provoked: the run fails")
    monkeypatch.setattr(wake, "run_due_jobs", run)

    with _wake_log() as log:
        hook = HookRecorder(run, log)
        monkeypatch.setattr(idle_monitor, "request_idle_check", hook)
        response = await _wake_up(_system_app(), token)
        run_task = await _run_task(run)

    assert response.status_code == 200, f"the wake-up answers as before: {response.status_code} {response.content[:300]!r}"
    assert json.loads(response.content)["status"] == ("ok" if ending == "returns" else "error")
    assert len(hook.calls) == 1, f"one request for a check per wake-up: {hook.calls}"
    call = hook.calls[0]
    assert (call.args, call.kwargs) in (((2.0,), {}), ((), {"delay": 2.0})), f"request_idle_check(WAKE_CHECK_DELAY_SECONDS), 2.0: {call.args}, {call.kwargs}"
    assert call.task is run_task, "called in the run's task"
    assert call.runs_ended == 1, "called once the run is over"
    assert RUN_FINISHED in call.logged, f"called after 'Wake-up run finished': {call.logged}"
    assert (RUN_FAILED in call.logged) is (ending == "raises")
    print_success("request_idle_check(2.0) in the run's task, after its end")


@pytest.mark.asyncio
async def test_with_no_monitor_running_a_wake_up_reaches_the_real_request_idle_check_and_answers_as_before(monkeypatch: pytest.MonkeyPatch, timeline: Timeline) -> None:
    """SWS-043 — contract (k): a monitor started then stopped, so none runs; a wake-up then reaches the real ``request_idle_check``, which does nothing: 200, status "ok", the run's task returned, "Wake-up run finished" logged once, no "Wake-up run failed"."""
    print_section("SWS-043: the real hook, no monitor running")
    _fly_globals(monkeypatch, timeline)
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    async with _started() as monitor_task:
        await timeline.until(lambda: timeline.count("reading") >= 1, "the monitor's first check")
    token = _wake_token(monkeypatch)
    run = FakeRun()
    monkeypatch.setattr(wake, "run_due_jobs", run)

    with _wake_log() as log:
        response = await _wake_up(_system_app(), token)
        run_task = await _run_task(run)

    assert monitor_task is not None and monitor_task.done(), "Precondition: the monitor was stopped"
    assert (response.status_code, json.loads(response.content)["status"]) == (200, "ok")
    assert not run_task.cancelled() and run_task.exception() is None, f"the run's task returned: {run_task}"
    assert [entry.get("log_level") for entry in _logged(log, RUN_FINISHED)] == ["info"]
    assert _logged(log, RUN_FAILED) == []
    print_success("200 ok; nothing raised")


# =============================================================================
# (l) THE LIFESPAN
# =============================================================================


def test_the_idle_monitor_steps_of_the_lifespan(monkeypatch: pytest.MonkeyPatch) -> None:
    """SWS-044 — contract (l): "idle-monitor" once in ``STARTUP_STEPS``, right after "scheduler"; once in ``SHUTDOWN_STEPS``, first, before "scheduler", not blocking — it hands the monitor's task to the runner, on the event loop. Each step, run with ``app_lifespan.start_idle_monitor`` / ``stop_idle_monitor`` replaced by a recorder, calls it once without arguments and returns what it returned."""
    print_section("SWS-044: the idle-monitor steps")
    startup, shutdown = _names(app_lifespan.STARTUP_STEPS), _names(app_lifespan.SHUTDOWN_STEPS)

    assert (startup.count(STEP_NAME), shutdown.count(STEP_NAME)) == (1, 1), f"one idle-monitor step in each: {startup}, {shutdown}"
    assert startup.index(STEP_NAME) == startup.index("scheduler") + 1, f"right after the scheduler: {startup}"
    assert shutdown[0] == STEP_NAME, f"the first shutdown step: {shutdown}"
    _assert_in_relative_order(app_lifespan.SHUTDOWN_STEPS, (STEP_NAME, "scheduler"), "SHUTDOWN_STEPS")
    assert _step(app_lifespan.SHUTDOWN_STEPS, STEP_NAME).blocking is False
    for steps, function_name in ((app_lifespan.STARTUP_STEPS, "start_idle_monitor"), (app_lifespan.SHUTDOWN_STEPS, "stop_idle_monitor")):
        calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        sentinel = object()
        monkeypatch.setattr(app_lifespan, function_name, _call_recorder(calls, sentinel))
        result = _step(steps, STEP_NAME).run()
        assert (calls, result) == ([((), {})], sentinel), f"the step calls app_lifespan.{function_name} as it is when the step runs, and returns what it returns: {calls}, {result!r}"
    print_success("after scheduler at startup, first at shutdown; both late-bound")


@pytest.mark.asyncio
async def test_start_returns_none_and_the_startup_step_completes_while_the_monitor_keeps_running(monkeypatch: pytest.MonkeyPatch, timeline: Timeline) -> None:
    """SWS-045 — contracts (h), (l): in "fly" mode, ``start_idle_monitor()`` returns None and its monitor runs. The "idle-monitor" step of ``STARTUP_STEPS``, run by ``lifecycle.run_startup_steps``, completes within the deadline while the monitor it started keeps running — a step returning the monitor's task would make the runner await it for ever. ``stop_idle_monitor()`` then returns that task, which returns."""
    print_section("SWS-045: the startup step does not wait for the monitor")
    _fly_environment(monkeypatch, timeline)
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    step = _step(app_lifespan.STARTUP_STEPS, STEP_NAME)

    async with _started() as direct:
        direct_running = direct is not None and not direct.done()
    before = idle_monitor.idle_monitor_task()
    try:
        await _within(lifecycle.run_startup_steps((step,)), "run_startup_steps((idle-monitor,)) did not complete: does the step hand it the monitor's task, which it awaits?")
        task = idle_monitor.idle_monitor_task()
        assert task is not None and task is not before, f"the startup step started a monitor: {task!r}"
        assert not task.done(), "the monitor keeps running once the startup step completed"
        assert idle_monitor.stop_idle_monitor() is task
        await _ended(task, "the monitor started by the startup step, after stop_idle_monitor()")
    finally:
        leftover = idle_monitor.idle_monitor_task()
        if leftover is not None and leftover is not before and not leftover.done():
            idle_monitor.stop_idle_monitor()
            await _settle(leftover, "the monitor started by the startup step")

    assert direct_running, "start_idle_monitor() itself started a monitor, which was running"
    print_success("None; the step completed, the monitor ran; stopped")


# =============================================================================
# (g) A CHECK REQUESTED DURING THE RESUME GRACE (decision of 16/10/2026)
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["suspended", "failed"])
async def test_a_requested_check_ends_the_resume_grace_early(rig: Rig, timeline: Timeline, monkeypatch: pytest.MonkeyPatch, outcome: str) -> None:
    """SWS-046 — contract (g): silent far past the threshold, nothing busy, the loop's first check ends ``outcome`` and the loop waits out the grace, 2000 s here, its recorded sleep held until the test ends. ``request_check(0.0)`` brings the next check at once, which asks for the suspension again: a machine a wake-up woke goes back to sleep without waiting out the grace, which protects only the request that woke it. The grace's sleep never came to its end. After "failed" the fake monotonic clock is first moved to the end of the backoff, 30 s, which the grace outlasts as with the shipped values (30 and 60 s): the next check tries again instead of answering "waiting"."""
    print_section(f"SWS-046: a check requested during the grace after {outcome}")
    monkeypatch.setattr(idle_monitor, "IDLE_CHECK_SECONDS", LONG_CHECK_SECONDS)
    monkeypatch.setattr(idle_monitor, "RESUME_GRACE_SECONDS", LONG_GRACE_SECONDS)
    rig.activity.clock.now = rig.activity.started_at + LONG_IDLE
    if outcome == "failed":
        rig.suspender.fail_with = _http_503
    stop = asyncio.Event()

    async with _running(rig, stop):
        await timeline.until(lambda: _first_long_sleep(timeline, 0) is not None, f"the loop's grace after a check {outcome}")
        found = _first_long_sleep(timeline, 0)
        assert found is not None
        grace_at, grace = found
        before_the_request = (timeline.count("reading"), rig.suspender.calls)
        if outcome == "failed":
            rig.monotonic.now = rig.monitor.retry_not_before
        rig.monitor.request_check(0.0)
        await timeline.until(lambda: timeline.count("suspend", grace_at) >= 1, f"the check requested during the grace after {outcome}, asking for the suspension again")
        released = [entry for entry in timeline.entries if entry[0] == "slept" and entry[1] > REAL_SLEEP_LIMIT]

    assert grace >= LONG_GRACE_SECONDS - 1e-6, f"Precondition: after {outcome} the loop waits out the grace: sleep({grace})"
    assert before_the_request == (1, 1), f"Precondition: one check, which ended {outcome}, then the grace: {timeline.entries[: grace_at + 1]}"
    assert released == [], f"the grace's sleep never came to its end, the request ended the wait: {released}"
    assert timeline.count("reading", grace_at) >= 1, "the requested check read the busy reasons, after the grace began"
    print_success(f"after {outcome}: the grace ended by the request; the suspension asked for again")
