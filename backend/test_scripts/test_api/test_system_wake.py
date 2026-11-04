"""
The scheduled wake-up (workstream Z, lot Z4): ``POST /api/v1/system/wake-sync``, which a hosting panel, or the cron of a
homelab, calls with a token of its own to run the scheduler's due jobs, and which answers while they run.

Under test: ``backend/app/config/sleep_wake.py`` (``WAKE_TOKEN_VARIABLE``, ``wake_token``) and
``backend/app/api/v1/system/wake.py`` (``wake_router``, ``wake_sync``), composed into the system router by
``api/v1/system/__init__.py``; plan phase01SleepWake §Z4, decisions D-W1…D-W3 and N-Z4-1…6.

- WAKE-001..010, ``wake_token()``: ``LIBREFOLIO_WAKE_TOKEN`` as written, read at every call, or else the text of the
  file its ``_FILE`` names, without a leading BOM and its trailing line breaks; the variable wins over the file, and a
  blank one leaves the file in charge; neither set, or both blank, is None. The rules are those of the panel's backup
  token (``config/backup.py``: ``PANEL_TOKEN_CHARACTERS``, ``PANEL_TOKEN_MIN_LENGTH``), whose outcomes it shares value
  for value: anything but visible ASCII (``!`` 0x21 to ``~`` 0x7E) raises ``SleepWakeConfigError``
  ``WAKE_TOKEN_NOT_VISIBLE_ASCII``, checked first; under 32 characters ``WAKE_TOKEN_TOO_SHORT``; ``variable`` the
  variable, which the message names, never the value. 32 visible characters are taken as written. A file that cannot
  give the token (missing, unreadable, empty, blank) raises ``SecretFileError``, naming the ``_FILE``.
- WAKE-011, the route off: without a token it answers 404 ``{"detail": "Not Found"}``, the answer of a path that does
  not exist, whatever the request carries, a token that used to be right included; no run starts.
- WAKE-012, a token the server cannot use (too short, from the variable or its file; spaces around it; a character
  outside ASCII; its file missing, unreadable, empty or blank): 503 ``wake_unavailable`` with or without a token
  presented, the configured value itself included; each request logs one error naming the variable, never its value
  (the file's path may be there, for the administrator); the answer never holds the value nor the file's path; no run
  starts.
- WAKE-013, the token missing or wrong (no ``Authorization``, the token under ``Basic``, ``Bearer`` with nothing,
  another token, a prefix, an extension or the capitals of the token, the token in the query string): 401
  ``wake_unauthorized`` with ``WWW-Authenticate: Bearer``; no run starts.
- WAKE-014, the token read from its file opens the route as the variable does, and the variable wins.
- WAKE-015, the token, and whatever the caller presented, never shows in an answer, its body or its headers, nor in the
  log: every request of this module checks it, and one test covers a 401, a 503 and a 200 together.
- WAKE-016..019, with the token and no run in progress: 200, ``application/json``, ``Cache-Control: no-store``; the run
  is ``run_due_jobs("wake")``, started as a task. The body streams: a space at once, before the run ends, then one every
  ``WAKE_KEEPALIVE_SECONDS`` while it lasts, then the JSON of ``WakeSyncResponse``: ``status``, ``started_at``,
  ``finished_at`` (ISO 8601 with the UTC offset), ``error`` (null) and ``jobs``, each with ``name``, ``status``,
  ``started_at``, ``duration_s``, ``items_ok``, ``items_err``, ``error``, ``items_deferred`` and ``retry_at`` (both
  since lot Z7b; ``retry_at`` ISO 8601 with the UTC offset, or null), exactly these keys, holding the values of
  the ``RunReport`` the run returned; its status whatever it is (``ok``, ``partial``, ``error``, ``disabled``,
  ``not_leader``, ``blocked``), always with 200.
- WAKE-020..021, one wake-up at a time in the process (D-W1): while a run is in progress the token is still checked
  first (401, 404, 503 as without a run), then the right token answers 409 ``wake_in_progress`` and starts nothing.
  The gate reopens when the run ends, not when its answer ends: a client that disconnects mid-stream leaves its run to
  its end, never cancelled, a call meanwhile meets 409, "finished" is logged at the run's end, and the next call is
  served.
- WAKE-022, a run that raises: still 200, ``status`` "error", ``error`` its class name only, never its message,
  ``jobs`` empty, ``started_at <= finished_at`` in UTC; logged at error, "Wake-up run failed"; the next call is served.
- WAKE-023, the log of a run: "Wake-up run started", then "Wake-up run finished" with a ``status``, both INFO, once each.
- WAKE-024, D-W3 with the real ``run_due_jobs``: on a blocked instance, 200 with ``status`` "blocked" and no job, and
  nothing of the scheduler past its two switches is reached.
- WAKE-025..026, OpenAPI and the composition: ``POST /api/v1/system/wake-sync``, tag Hosting panel alone, asks for the ``WakeToken``
  bearer scheme and no other, which no other route of the system router asks for; its 200 is ``WakeSyncResponse``,
  exactly the keys above, and 401, 404, 409 and 503 are documented. ``wake_router`` serves ``POST /wake-sync`` with
  ``wake_sync``, which the system router serves under ``/api/v1/system``; the module ships ``WAKE_KEEPALIVE_SECONDS``
  15.0 and the scheduler's own ``run_due_jobs``.
- WAKE-027..028, through the real middleware stack (``install_middleware``): while its run lasts the wake-up is in
  flight but not the user's presence (D-S1); with ``Accept-Encoding: gzip`` its first chunk still leaves before the run
  ends, and decompresses to a space.
- WAKE-029, Z-11 (night decision N71) with the real ``run_due_jobs``, on a worker whose ``am_i_leader`` answers no: with
  ``fcntl`` (``cross_process_lock_available()``) the leader is never asked, the run takes the lock across processes and
  runs its jobs: 200, ``status`` "ok", both jobs reported. Without ``fcntl``, the fallback: 200, ``status``
  "not_leader", no job — the one way a run still answers "not_leader".

Pure: an app of each test holds the system router under ``/api/v1``, as ``router.py`` mounts it, and nothing else;
``install_middleware`` is added where the stack is under test. In every test ``run_due_jobs`` is replaced on the wake
module by a fake that records its reason and the task it runs in, may be held on an event until the test releases it
(a bounded wait), records whether it was cancelled, and returns a real ``RunReport``; ``LIBREFOLIO_NO_SCHEDULER`` is
set besides, so that not even the real one could reach anything. The tests of the real run (WAKE-024, WAKE-029) put it
back: WAKE-024 with the instance blocked, the settle a no-op and every collaborator past the switches a trap; WAKE-029
with the switches open, the settle a no-op, the settings, the state store, the due functions and the jobs fakes in
memory, ``PRICE_REFRESH`` a tracker of the test, and the lock across processes a stand-in that writes no file. The token
variables, the panel's included, are deleted before each test, then set through ``monkeypatch``; the process's
``ACTIVITY`` is a fresh ``Activity`` in each test. No data directory, database, server or network is reached.

The requests run behind ``httpx.ASGITransport`` (``raise_app_exceptions=False``), which collects a whole body before it
returns. Where a body must be seen while the run lasts, or the client must go away, the request is driven straight into
the app's ASGI callable, as uvicorn hands it over (ASGI spec 2.3: Starlette then listens to ``receive`` for the
disconnect), every message recorded as it is sent. Nothing sleeps: every wait is on an event or a task, bounded by
``WAIT_SECONDS``, and no assertion depends on a duration; every task a test starts is awaited or cancelled before it
ends, and every held run is released. The log is read with ``structlog.testing.capture_logs`` behind a barrier: a canary
logged through the wake module's own ``logger`` must reach the capture, or "never in the log" would prove nothing.

Red until the code of Z4 exists: ``backend.app.api.v1.system.wake`` does not import, nor do ``WAKE_TOKEN_VARIABLE`` and
``wake_token``: a collection error. Since Z-11, WAKE-029's "cross-process-lock" case is red until ``_run_locked`` skips
``am_i_leader`` where ``cross_process_lock_available()``: before, the worker answers "not_leader"; its fallback case
passes before and after (the stand-ins are set with ``raising=False``).
"""

from __future__ import annotations

import asyncio
import json
import secrets
import zlib
from collections.abc import AsyncIterator, Awaitable, Callable, Iterable, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, NoReturn

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import iter_route_contexts
from structlog.testing import capture_logs

from backend.app.api.v1.system import router as system_router
from backend.app.api.v1.system import wake
from backend.app.config import API_V1_PREFIX, SecretFileError
from backend.app.config.backup import PANEL_TOKEN_CHARACTERS, PANEL_TOKEN_MIN_LENGTH, BackupConfigError, backup_download_token
from backend.app.config.sleep_wake import WAKE_TOKEN_VARIABLE, SleepWakeConfigError, wake_token
from backend.app.services.platform.middleware import MIDDLEWARE_STACK, install_middleware
from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.scheduler.scheduler import JobOutcome, RunReport
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import JobState, SchedulerState
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.services.platform.sleep_wake.activity import Activity
from backend.test_scripts.test_utils import print_section, print_success

#: The variables of the token, as .env.example and the deployments write them: spelled out here, so a rename shows.
TOKEN_VARIABLE = "LIBREFOLIO_WAKE_TOKEN"
TOKEN_FILE_VARIABLE = "LIBREFOLIO_WAKE_TOKEN_FILE"
#: The panel's backup token (workstream B), whose rule the wake token shares: cleared too, set only where WAKE-010 sets it.
PANEL_TOKEN_VARIABLES = ("LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN", "LIBREFOLIO_BACKUP_DOWNLOAD_TOKEN_FILE")
#: The shortest token the server takes.
MIN_LENGTH = 32

WAKE_SYNC = f"{API_V1_PREFIX}/system/wake-sync"

#: The route off: the answer of a path that does not exist, whole.
OFF_ANSWER = (404, {"detail": "Not Found"})
#: Status, ``detail.code``, and a detail of exactly a code and a non-empty message (``shape``).
UNAUTHORIZED = (401, "wake_unauthorized", True)
UNAVAILABLE = (503, "wake_unavailable", True)
IN_PROGRESS = (409, "wake_in_progress", True)

#: The keys of ``WakeSyncResponse`` and of each of its jobs, exactly: no ``reason``, no ``next_wake_at``. A job's last
#: two since lot Z7b.
BODY_KEYS = frozenset({"status", "started_at", "finished_at", "error", "jobs"})
JOB_KEYS = frozenset({"name", "status", "started_at", "duration_s", "items_ok", "items_err", "error", "items_deferred", "retry_at"})

RUN_STARTED = "Wake-up run started"
RUN_FINISHED = "Wake-up run finished"
RUN_FAILED = "Wake-up run failed"
LOG_CANARY = "wake-sync test: canary through the wake module's logger"

#: The longest a test waits for anything: a run, a message, a task.
WAIT_SECONDS = 30.0
#: ``WAKE_KEEPALIVE_SECONDS`` where the spaces are counted, and where a second space must not come during the test.
FAST_KEEPALIVE_SECONDS = 0.005
SLOW_KEEPALIVE_SECONDS = 3_600.0
#: How many spaces a held run must see go out before the test releases it.
KEEPALIVES = 3
#: In the message of the failure a run raises: it must never reach a body.
SECRET_MESSAGE = "token=SECRET-in-message"

#: The moments of the reports the fake run returns, in UTC and to the second, so that a mirror shows whatever its format.
STARTED_AT = datetime(2026, 10, 16, 3, 0, 0, tzinfo=UTC)
JOB_STARTED_AT = datetime(2026, 10, 16, 3, 0, 2, tzinfo=UTC)
FINISHED_AT = datetime(2026, 10, 16, 3, 0, 9, tzinfo=UTC)
#: Outcomes whose every field differs from its default where it can: a mirror that drops or renames one shows. The two
#: fields of lot Z7b stay at their defaults here; ``deferring(RAN_PARTLY)`` moves them too.
RAN_PARTLY = JobOutcome(name="current_price", status="partial", started_at=JOB_STARTED_AT, duration_s=1.25, items_ok=7, items_err=2, error="QuotaExceeded")
RAN_OK = JobOutcome(name="current_price", status="ok", started_at=JOB_STARTED_AT, duration_s=0.5, items_ok=12, items_err=0, error=None)
RAN_INTO_ERRORS = JobOutcome(name="current_price", status="error", started_at=JOB_STARTED_AT, duration_s=0.75, items_ok=0, items_err=12, error="ProviderExploded")
RAISED = JobOutcome(name="history_sync", status="error", started_at=FINISHED_AT, duration_s=3.5, items_ok=0, items_err=0, error="PermissionError")
NOT_DUE = JobOutcome(name="history_sync", status="not_due")
#: When the deferred items of a run may be retried (lot Z7b), in UTC and to the second.
RETRY_AT = datetime(2026, 10, 16, 3, 5, 0, tzinfo=UTC)


def deferring(outcome: JobOutcome) -> JobOutcome:
    """``outcome`` with three items deferred until ``RETRY_AT`` (lot Z7b): ``deferring(RAN_PARTLY)`` has every field away
    from its default. Built at the call, so that only the test using it needs the fields of Z7b."""
    return replace(outcome, items_deferred=3, retry_at=RETRY_AT)


#: What the wake module ships with, and the scheduler's own run, read at import, before any fixture replaces them.
SHIPPED_RUN_DUE_JOBS = getattr(wake, "run_due_jobs", None)
SHIPPED_KEEPALIVE_SECONDS = getattr(wake, "WAKE_KEEPALIVE_SECONDS", None)
REAL_RUN_DUE_JOBS = scheduler.run_due_jobs
#: What the scheduler reaches past its two switches (``scheduler_disabled``, ``instance_blocked``): none of it on a
#: blocked instance.
PAST_THE_SWITCHES = ("am_i_leader", "load_scheduler_settings", "load_state", "save_state", "due_current_price", "due_history_sync", "run_current_price_refresh", "run_history_sync")

#: Files that cannot give a token, by what is wrong with them: each builder leaves such a thing at ``path``.
BROKEN_FILES: dict[str, Callable[[Path], object]] = {
    "file-missing": lambda path: None,
    "file-unreadable": lambda path: path.mkdir(),
    "file-empty": lambda path: path.write_bytes(b""),
    "file-blank": lambda path: path.write_bytes(b" \n\r\n"),
}


def a_token() -> str:
    """A token as the documentation suggests one (``openssl rand -hex 32``): 64 characters, new at each call."""
    return secrets.token_hex(32)


# =============================================================================
# Waiting without sleeping
# =============================================================================


async def within(awaitable: Awaitable[Any], what: str | Callable[[], str]) -> Any:
    """What ``awaitable`` gives, or a red naming ``what`` after ``WAIT_SECONDS``: a hang fails the test instead of the run."""
    try:
        return await asyncio.wait_for(awaitable, WAIT_SECONDS)
    except TimeoutError:
        pytest.fail(f"{what() if callable(what) else what}: nothing within {WAIT_SECONDS} s")


class Changes:
    """Something a test waits for changed: a run started or ended, the app sent a message, a task ended. Every coroutine
    waiting in ``until`` re-checks its condition at each change, within the deadline."""

    def __init__(self) -> None:
        self._event: asyncio.Event | None = None

    def notify(self, *_ignored: object) -> None:
        """A change: every waiter wakes up and re-checks. Also a done callback, which is given the task."""
        event, self._event = self._event, None
        if event is not None:
            event.set()

    def watch(self, task: asyncio.Task[Any]) -> asyncio.Task[Any]:
        """``task``, whose end is a change."""
        task.add_done_callback(self.notify)
        return task

    async def until(self, condition: Callable[[], bool], what: Callable[[], str]) -> None:
        """Until ``condition()`` holds, within ``WAIT_SECONDS``; a red naming ``what()`` after."""

        async def reached() -> None:
            while not condition():
                if self._event is None:
                    self._event = asyncio.Event()
                await self._event.wait()

        await within(reached(), what)


def ending_of(task: asyncio.Task[Any] | None) -> str:
    """How ``task`` ended, for a message."""
    if task is None or not task.done():
        return "still running"
    if task.cancelled():
        return "cancelled"
    error = task.exception()
    return "returned" if error is None else f"raised {type(error).__name__}: {error}"


async def settle(task: asyncio.Task[Any]) -> None:
    """``task`` done before the test ends: cancelled if it still runs, then waited for within the deadline. What it raised
    is retrieved here, so that asyncio does not report it again: the test has reported its own red."""
    if not task.done():
        task.cancel()
    await asyncio.wait({task}, timeout=WAIT_SECONDS)
    if task.done() and not task.cancelled():
        task.exception()


# =============================================================================
# The run replaced, and a request driven on the wire
# =============================================================================


class FakeRun:
    """``run_due_jobs`` of the wake module, replaced in every test but WAKE-024.

    Each call records its reason and the task it runs in (``asyncio.current_task()``: the run's task), and says that it
    started; run number ``n`` then waits on ``gates[n]`` when the test holds it (``hold``), at most ``WAIT_SECONDS``.
    Then it raises ``failure``, or returns a real ``RunReport`` of ``status`` and ``jobs``, kept in ``returned``.
    ``cancelled`` records, run by run, whether a cancellation went through it; ``ended`` counts the runs over, however
    they ended. Every start and every end is a change of ``changes``.
    """

    def __init__(self) -> None:
        self.changes = Changes()
        self.reasons: list[str] = []
        self.tasks: list[asyncio.Task[Any] | None] = []
        self.cancelled: list[bool] = []
        self.returned: list[RunReport] = []
        self.ended = 0
        self.gates: dict[int, asyncio.Event] = {}
        self.failure: Exception | None = None
        self.status = "partial"
        self.jobs: tuple[JobOutcome, ...] = (RAN_PARTLY, NOT_DUE)

    def hold(self, number: int = 1) -> asyncio.Event:
        """Run ``number``, once started, waits until the event returned is set."""
        gate = asyncio.Event()
        self.gates[number] = gate
        return gate

    async def __call__(self, reason: str) -> RunReport:
        self.reasons.append(reason)
        number = len(self.reasons)
        self.tasks.append(asyncio.current_task())
        self.changes.notify()
        cancelled = False
        try:
            gate = self.gates.get(number)
            if gate is not None:
                await asyncio.wait_for(gate.wait(), WAIT_SECONDS)
            if self.failure is not None:
                raise self.failure
            report = RunReport(reason=reason, status=self.status, started_at=STARTED_AT, finished_at=FINISHED_AT, jobs=self.jobs)
            self.returned.append(report)
            return report
        except asyncio.CancelledError:
            cancelled = True
            raise
        finally:
            self.cancelled.append(cancelled)
            self.ended += 1
            self.changes.notify()

    async def until_started(self, count: int, *, unless: asyncio.Task[Any] | None = None) -> None:
        """Until run ``count`` has started, within the deadline; a red at once if ``unless``, the request, ended first."""
        await self.changes.until(lambda: len(self.reasons) >= count or (unless is not None and unless.done()), lambda: f"run #{count} started? the runs so far: {self.reasons}")
        if len(self.reasons) < count:
            pytest.fail(f"the request ended ({ending_of(unless)}) before run #{count} started; the runs so far: {self.reasons}")

    async def task_done(self, number: int) -> asyncio.Task[Any]:
        """The task run ``number`` ran in, once it is done: the callbacks it held when it ended (a gate's) have run."""
        if len(self.tasks) < number or self.tasks[number - 1] is None:
            pytest.fail(f"run #{number} never started in a task: the runs so far: {self.reasons}")
        task = self.tasks[number - 1]
        done, _ = await asyncio.wait({task}, timeout=WAIT_SECONDS)
        if not done:
            pytest.fail(f"the task of run #{number} was still running {WAIT_SECONDS} s after the test released it")
        return task

    @asynccontextmanager
    async def cleanup(self) -> AsyncIterator[None]:
        """However the block ends, every held run is released, and every run's task is done within the deadline, or
        cancelled: no run of a test outlives it."""
        try:
            yield
        finally:
            for gate in self.gates.values():
                gate.set()
            here = asyncio.current_task()
            pending = {task for task in self.tasks if task is not None and task is not here and not task.done()}
            if pending:
                _, late = await asyncio.wait(pending, timeout=WAIT_SECONDS)
                for task in late:
                    task.cancel()
                if late:
                    await asyncio.wait(late, timeout=WAIT_SECONDS)


class Wire:
    """``POST /api/v1/system/wake-sync`` driven straight into the app's ASGI callable, as uvicorn hands a request over.

    The scope says ASGI spec 2.3, as uvicorn's does: Starlette then streams a body while listening to ``receive`` for the
    client's disconnect. ``receive`` gives the empty request body, then waits until the test calls ``disconnect()``.
    Every message the app sends is recorded as it is sent, and is a change of ``changes``, as the end of the app's call.
    """

    def __init__(self, app: FastAPI, changes: Changes, *, authorization: str, accept_encoding: str | None = None) -> None:
        headers = [(b"host", b"in-process"), (b"content-length", b"0"), (b"authorization", authorization.encode("latin-1"))]
        if accept_encoding is not None:
            headers.append((b"accept-encoding", accept_encoding.encode("latin-1")))
        self.scope: dict[str, Any] = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": WAKE_SYNC,
            "raw_path": WAKE_SYNC.encode(),
            "root_path": "",
            "query_string": b"",
            "headers": headers,
            "client": ("127.0.0.1", 50000),
            "server": ("in-process", 80),
        }
        self.app = app
        self.changes = changes
        self.messages: list[dict[str, Any]] = []
        self.task: asyncio.Task[Any] | None = None
        self._body_given = False
        self._gone = asyncio.Event()

    async def receive(self) -> dict[str, Any]:
        if not self._body_given:
            self._body_given = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await self._gone.wait()
        return {"type": "http.disconnect"}

    async def send(self, message: dict[str, Any]) -> None:
        self.messages.append(message)
        self.changes.notify()

    def disconnect(self) -> None:
        """The client goes away: the next ``receive`` answers ``http.disconnect``."""
        self._gone.set()

    @asynccontextmanager
    async def running(self) -> AsyncIterator[Wire]:
        """The app's call as a task of the test for the block; at its end, done within the deadline, or cancelled."""
        task = self.changes.watch(asyncio.create_task(self.app(self.scope, self.receive, self.send), name="wake-sync-on-the-wire"))
        self.task = task
        try:
            yield self
        finally:
            await settle(task)

    async def until_bodies(self, count: int) -> None:
        """Until the app has sent ``count`` body messages, within the deadline; a red at once if its call ended first."""
        task = self.task
        assert task is not None, "the request is not running"
        await self.changes.until(lambda: len(self.bodies) >= count or task.done(), lambda: f"{count} body message(s)? so far {self.chunks()}")
        if len(self.bodies) < count:
            pytest.fail(f"the request ended ({ending_of(task)}) after {self.chunks()}, before {count} body message(s)")

    async def ended(self) -> None:
        """The app's call returned, within the deadline; what it raised is raised here."""
        task = self.task
        assert task is not None, "the request is not running"
        done, _ = await asyncio.wait({task}, timeout=WAIT_SECONDS)
        if not done:
            pytest.fail(f"the request was still running {WAIT_SECONDS} s later, after {self.chunks()}")
        if task.cancelled():
            pytest.fail(f"the request's task was cancelled, after {self.chunks()}")
        error = task.exception()
        if error is not None:
            raise error

    @property
    def start(self) -> dict[str, Any]:
        """The ``http.response.start`` message, or an empty dict before it."""
        return next((message for message in self.messages if message["type"] == "http.response.start"), {})

    @property
    def status(self) -> int | None:
        return self.start.get("status")

    @property
    def headers(self) -> dict[str, str]:
        return {name.decode("latin-1").lower(): value.decode("latin-1") for name, value in self.start.get("headers", [])}

    @property
    def bodies(self) -> list[dict[str, Any]]:
        return [message for message in self.messages if message["type"] == "http.response.body"]

    def chunks(self) -> list[tuple[bytes, bool]]:
        """Each body message: its bytes, and whether more follow."""
        return [(bytes(message.get("body", b"")), bool(message.get("more_body", False))) for message in self.bodies]

    @property
    def body(self) -> bytes:
        return b"".join(chunk for chunk, _ in self.chunks())

    def shows(self, values: Iterable[str]) -> list[str]:
        """Where a value of ``values`` shows in the answer, its headers or its body, named by its position."""
        headers = "\n".join(f"{name}: {value}" for name, value in self.headers.items())
        return [f"value #{index} in the {place}" for index, value in enumerate(values) if value for place, shown in (("body", value.encode() in self.body), ("headers", value in headers)) if shown]


# =============================================================================
# The environment cleared, the app of a test, its requests, its log, its bodies
# =============================================================================


@pytest.fixture(autouse=True)
def run(monkeypatch: pytest.MonkeyPatch) -> FakeRun:
    """Every test of this module, the unit tests included: ``run_due_jobs`` replaced on the wake module, so that no
    request can start a real run. ``LIBREFOLIO_NO_SCHEDULER`` is set besides: should the route not read the module's
    ``run_due_jobs`` at call time, the real one would answer "disabled" before the leader lock, the database or a
    provider. WAKE-024 puts the real one back and clears the variable."""
    fake = FakeRun()
    monkeypatch.setattr(wake, "run_due_jobs", fake)
    monkeypatch.setenv("LIBREFOLIO_NO_SCHEDULER", "1")
    return fake


@pytest.fixture(autouse=True)
def activity(monkeypatch: pytest.MonkeyPatch) -> Activity:
    """A fresh ``Activity`` in place of the process's ``ACTIVITY`` in every test: what the middleware and the real run
    count lands here, never on the instance the process ships."""
    fresh = Activity()
    monkeypatch.setattr(activity_module, "ACTIVITY", fresh)
    return fresh


@pytest.fixture(autouse=True)
def no_inherited_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts with no variable of the wake token nor of the panel's: nothing comes from the runner's
    environment."""
    for name in (TOKEN_VARIABLE, TOKEN_FILE_VARIABLE, *PANEL_TOKEN_VARIABLES):
        monkeypatch.delenv(name, raising=False)


def system_app(*, middleware: bool = False) -> FastAPI:
    """The system router under ``/api/v1``, as ``router.py`` mounts it, in an app of the test and nothing else; with
    ``middleware``, the app's own stack (``install_middleware``) around it."""
    app = FastAPI()
    app.include_router(system_router, prefix=API_V1_PREFIX)
    if middleware:
        install_middleware(app)
    return app


@pytest.fixture
def app() -> FastAPI:
    return system_app()


def with_token(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    """A new token in the variable: the token, and the ``Authorization`` value that presents it."""
    token = a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, token)
    return token, f"Bearer {token}"


def write_token_file(tmp_path: Path, text: str) -> Path:
    """A file holding ``text``, as a Docker secret mounts one."""
    path = tmp_path / "wake-token"
    path.write_bytes(text.encode("utf-8"))
    return path


def set_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str, value: str) -> None:
    """``value`` as the token, from the variable or (followed by a line break) from the file of ``_FILE``."""
    if source == "variable":
        monkeypatch.setenv(TOKEN_VARIABLE, value)
    else:
        monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, value + "\n")))


@contextmanager
def captured_log() -> Iterator[list[dict[str, Any]]]:
    """What is logged inside the block, behind a barrier: a canary logged through the wake module's own logger must
    arrive first, or "never in the log" would prove nothing."""
    with capture_logs() as events:
        wake.logger.debug(LOG_CANARY)
        assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the wake module's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


@contextmanager
def request_log(log: list[dict[str, Any]] | None) -> Iterator[list[dict[str, Any]]]:
    """The events of one request: a capture of its own, behind the canary; or, inside the capture ``log`` a test holds
    around requests that overlap, what it received from the request's start to its end."""
    if log is None:
        with captured_log() as events:
            yield events
        return
    mark = len(log)
    window: list[dict[str, Any]] = []
    try:
        yield window
    finally:
        window.extend(log[mark:])


def levels(events: list[dict[str, Any]], event: str) -> list[Any]:
    """The level of every captured ``event``, in order."""
    return [entry.get("log_level") for entry in events if entry.get("event") == event]


@dataclass(frozen=True)
class Exchange:
    """One request answered behind ``httpx.ASGITransport``: the answer, and the events logged while it ran."""

    response: httpx.Response
    events: list[dict[str, Any]]

    @property
    def answer(self) -> tuple[int, object]:
        """Status and body: the JSON of a JSON answer, a streamed one included, else its first bytes, so a red reads."""
        if self.response.headers.get("content-type", "").startswith("application/json"):
            try:
                return self.response.status_code, self.response.json()
            except ValueError:
                return self.response.status_code, self.response.content[:300]
        return self.response.status_code, self.response.content[:300]

    @property
    def errors(self) -> list[dict[str, Any]]:
        """The events logged at error level."""
        return [event for event in self.events if event.get("log_level") == "error"]

    def shows(self, values: Iterable[str]) -> list[str]:
        """Where a value of ``values`` shows: the body, the headers (names and values), the log. Empty values are skipped,
        and a value is named by its position, never written out."""
        headers = "\n".join(f"{name}: {value}" for name, value in self.response.headers.multi_items())
        log = repr(self.events)
        places = []
        for index, value in enumerate(values):
            if not value:
                continue
            found = {"body": value.encode() in self.response.content, "headers": value in headers, "log": value in log}
            places.extend(f"value #{index} in the {place}" for place, shown in found.items() if shown)
        return places


def shape(exchange: Exchange) -> tuple[int, str | None, bool]:
    """Status, ``detail.code``, and whether ``detail`` holds exactly a code and a message, a non-empty string."""
    status, body = exchange.answer
    detail = body.get("detail") if isinstance(body, dict) else None
    if not isinstance(detail, dict):
        return status, None, False
    message = detail.get("message")
    return status, detail.get("code"), set(detail) == {"code", "message"} and isinstance(message, str) and bool(message.strip())


async def send(app: FastAPI, *, authorization: str | None = None, params: dict[str, str] | None = None, never: Iterable[str] = (), log: list[dict[str, Any]] | None = None, path: str = WAKE_SYNC) -> Exchange:
    """``POST path`` (wake-sync by default) on ``app``, in this process, with ``Authorization`` only when given.

    The log is captured meanwhile, behind the canary, or read from ``log`` (``request_log``). Ends on what every request
    of this module must hold: no value of ``never`` (the token, a configured value) in the answer nor in the log; what
    the caller presented, and the query string's values, are checked without being listed.
    """
    headers = {} if authorization is None else {"Authorization": authorization}
    presented = [] if authorization is None else [authorization.partition(" ")[2].strip()]
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    with request_log(log) as events:
        async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
            response = await client.post(path, headers=headers, params=params)
    exchange = Exchange(response, list(events))
    leaked = exchange.shows([*never, *presented, *(params or {}).values()])
    assert not leaked, f"POST {path}: a secret left the server: {leaked}"
    return exchange


def moment(value: object, where: str, *, nullable: bool = False) -> datetime | None:
    """An ISO 8601 string of a body as an aware datetime whose offset is UTC's; None only where ``nullable``."""
    if value is None and nullable:
        return None
    assert isinstance(value, str), f"{where}: an ISO 8601 string expected, got {value!r}"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        pytest.fail(f"{where}: {value!r} is not ISO 8601")
    assert parsed.utcoffset() == timedelta(0), f"{where}: {value!r} must carry the UTC offset"
    return parsed


def checked_keys(body: object) -> list[dict[str, Any]]:
    """The jobs of ``body``, once the body holds exactly the keys of ``WakeSyncResponse`` and each job those of a job,
    its items integers."""
    assert isinstance(body, dict) and set(body) == BODY_KEYS, f"the body holds exactly {sorted(BODY_KEYS)}: {body!r}"
    jobs = body["jobs"]
    assert isinstance(jobs, list) and all(isinstance(job, dict) and set(job) == JOB_KEYS for job in jobs), f"each job holds exactly {sorted(JOB_KEYS)}: {jobs!r}"
    assert all(type(job[key]) is int for job in jobs for key in ("items_ok", "items_err", "items_deferred")), f"items_ok, items_err and items_deferred are integers: {jobs!r}"
    return jobs


def read_result(raw: bytes) -> dict[str, Any]:
    """The JSON that ends a body, its leading spaces skipped (valid JSON whitespace), with its moments as datetimes."""
    try:
        body = json.loads(raw)
    except ValueError:
        pytest.fail(f"the body is not one JSON document after its leading spaces: {raw[:300]!r}")
    jobs = checked_keys(body)
    return {
        **body,
        "started_at": moment(body["started_at"], "started_at"),
        "finished_at": moment(body["finished_at"], "finished_at"),
        "jobs": [{**job, "started_at": moment(job["started_at"], f"jobs[{index}].started_at", nullable=True), "retry_at": moment(job["retry_at"], f"jobs[{index}].retry_at", nullable=True)} for index, job in enumerate(jobs)],
    }


def as_body(report: RunReport) -> dict[str, Any]:
    """The body ``report`` must give, its moments as datetimes, as ``read_result`` reads an answer: no top-level error,
    the run returned."""
    return {
        "status": report.status,
        "started_at": report.started_at,
        "finished_at": report.finished_at,
        "error": None,
        "jobs": [{"name": job.name, "status": job.status, "started_at": job.started_at, "duration_s": job.duration_s, "items_ok": job.items_ok, "items_err": job.items_err, "error": job.error, "items_deferred": job.items_deferred, "retry_at": job.retry_at} for job in report.jobs],
    }


def gunzip(chunks: list[bytes]) -> bytes:
    """What gzip ``chunks`` decompress to, read as a client reads them, chunk by chunk; a red when they are not gzip."""
    decompressor = zlib.decompressobj(wbits=31)
    try:
        return b"".join(decompressor.decompress(chunk) for chunk in chunks)
    except zlib.error as error:
        pytest.fail(f"not a gzip stream ({error}): {[chunk[:24] for chunk in chunks]}")


# =============================================================================
# WAKE-001..006: wake_token()
# =============================================================================


@pytest.mark.parametrize(
    "variables",
    [
        pytest.param({}, id="neither-variable"),
        pytest.param({TOKEN_VARIABLE: ""}, id="empty-variable"),
        pytest.param({TOKEN_VARIABLE: " \t "}, id="blank-variable"),
        pytest.param({TOKEN_FILE_VARIABLE: ""}, id="empty-file-variable"),
        pytest.param({TOKEN_FILE_VARIABLE: "   "}, id="blank-file-variable"),
        pytest.param({TOKEN_VARIABLE: " ", TOKEN_FILE_VARIABLE: " "}, id="both-blank"),
    ],
)
def test_no_token_when_neither_variable_gives_one(monkeypatch, variables):
    """WAKE-001: neither variable set, or blank, is no token at all: None, the route is off."""
    print_section("Wake token: wake_token()")
    for name, value in variables.items():
        monkeypatch.setenv(name, value)
    assert wake_token() is None, f"{sorted(variables)} set to blank values must count as unset"
    print_success(f"{variables or 'nothing set'}: None")


def test_the_variable_is_the_token_as_written_and_read_at_every_call(monkeypatch):
    """WAKE-002: ``WAKE_TOKEN_VARIABLE`` is ``LIBREFOLIO_WAKE_TOKEN``; the variable, when not blank, is the token as
    written; it is read at every call, so a new value is the token at the next one."""
    first, second = a_token(), a_token()
    monkeypatch.setenv(TOKEN_VARIABLE, first)
    read_first = wake_token()
    monkeypatch.setenv(TOKEN_VARIABLE, second)
    read_second = wake_token()

    assert WAKE_TOKEN_VARIABLE == TOKEN_VARIABLE, f"the variable of the wake token: {WAKE_TOKEN_VARIABLE}"
    assert read_first == first, f"{TOKEN_VARIABLE} must be the token as written"
    assert read_second == second, "the variable is read at every call: a new value is the token at the next one"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param("", "\n", id="line-break"),
        pytest.param("", "\r\n", id="crlf"),
        pytest.param("", "\n\n", id="two-line-breaks"),
        pytest.param("\ufeff", "\n", id="bom-and-line-break"),
        pytest.param("", "", id="no-line-break"),
    ],
)
def test_the_file_gives_the_token_without_its_bom_and_trailing_line_breaks(monkeypatch, tmp_path, before, after):
    """WAKE-003: the file named by ``_FILE`` holds the token; a leading BOM and the trailing line breaks are not part of
    it."""
    token = a_token()
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, before + token + after)))
    assert wake_token() == token, f"the token of a file holding {before!r} + token + {after!r}"


def test_the_variable_wins_over_the_file_and_a_blank_one_leaves_it_the_file(monkeypatch, tmp_path):
    """WAKE-004: both set, the variable is the token; blank, it counts as unset and the file is the token."""
    from_variable, from_file = a_token(), a_token()
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, from_file + "\n")))
    monkeypatch.setenv(TOKEN_VARIABLE, from_variable)
    both = wake_token()
    monkeypatch.setenv(TOKEN_VARIABLE, "  ")
    blank_variable = wake_token()

    assert both == from_variable, "both set: the variable wins over the file"
    assert blank_variable == from_file, "a blank variable counts as unset: the file gives the token"


@pytest.mark.parametrize("source", ["variable", "file"])
def test_31_characters_are_refused_without_the_value_and_32_are_a_token(monkeypatch, tmp_path, source):
    """WAKE-005: under 32 characters ``SleepWakeConfigError`` (code ``WAKE_TOKEN_TOO_SHORT``, ``variable`` the variable),
    its message naming the variable, never the value; 32 characters are a token. From the file, the line break that
    follows the value is not counted."""
    too_short, long_enough = a_token()[: MIN_LENGTH - 1], a_token()[:MIN_LENGTH]
    set_token(monkeypatch, tmp_path, source, too_short)
    with pytest.raises(SleepWakeConfigError) as refused:
        wake_token()
    set_token(monkeypatch, tmp_path, source, long_enough)
    taken = wake_token()

    error = refused.value
    assert (error.code, error.variable) == ("WAKE_TOKEN_TOO_SHORT", TOKEN_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert TOKEN_VARIABLE in str(error), f"the message names the variable: {error}"
    assert too_short not in f"{error} {error!r} {error.args}", "the message must never carry the value"
    assert taken == long_enough, f"{MIN_LENGTH} characters are a token"
    print_success(f"{source}: {MIN_LENGTH - 1} characters refused (code, variable, no value), {MIN_LENGTH} taken")


@pytest.mark.parametrize("problem", sorted(BROKEN_FILES))
def test_a_file_that_cannot_give_the_token_raises_secret_file_error(monkeypatch, tmp_path, problem):
    """WAKE-006: a ``_FILE`` that is missing, a folder, empty or blank cannot give the token: ``SecretFileError``, naming
    the ``_FILE`` variable."""
    path = tmp_path / "wake-token"
    BROKEN_FILES[problem](path)
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))
    with pytest.raises(SecretFileError) as raised:
        wake_token()
    assert TOKEN_FILE_VARIABLE in str(raised.value), f"the error names the variable: {raised.value}"


# =============================================================================
# WAKE-007..010: the characters of a token, and the rule of the panel's
# =============================================================================

#: The characters a token may hold, in order: the visible ASCII ones, from "!" (0x21) to "~" (0x7E).
VISIBLE_ASCII = "".join(chr(code) for code in range(0x21, 0x7F))

#: A character no token may hold, put on an otherwise valid token of 40 characters (``spoil(token)``): before it, after
#: it, or between its two halves. From the variable; and from the file, whose line break after the token goes
#: (``env_secret``) while the spaces before it stay.
NOT_VISIBLE_ASCII = [
    pytest.param("variable", lambda token: f" {token}", id="leading-space"),
    pytest.param("variable", lambda token: f"{token} ", id="trailing-space"),
    pytest.param("variable", lambda token: f"{token}\t", id="trailing-tab"),
    pytest.param("variable", lambda token: f"{token[:20]} {token[20:]}", id="inner-space"),
    pytest.param("variable", lambda token: f"{token[:20]}\u00e9{token[20:]}", id="e-acute-u00e9"),
    pytest.param("variable", lambda token: f"{token[:20]}\u20ac{token[20:]}", id="euro-sign-u20ac"),
    pytest.param("variable", lambda token: f"{token[:20]}\u00a0{token[20:]}", id="no-break-space-u00a0"),
    pytest.param("variable", lambda token: f"{token[:20]}\x7f{token[20:]}", id="del-0x7f"),
    pytest.param("variable", lambda token: f"{token[:20]}\x01{token[20:]}", id="control-0x01"),
    pytest.param("file", lambda token: f"{token}  ", id="file-spaces-before-the-line-break"),
]


@pytest.mark.parametrize(("source", "spoil"), NOT_VISIBLE_ASCII)
def test_a_token_holding_anything_but_visible_ascii_is_refused_without_the_value(monkeypatch, tmp_path, source, spoil):
    """WAKE-007: a token holds visible ASCII characters only. A space or a tab (around it or inside it), a character
    outside ASCII (é, €, a no-break space), DEL or another control character raises ``SleepWakeConfigError`` with the
    code ``WAKE_TOKEN_NOT_VISIBLE_ASCII`` and ``variable`` the variable; its message names the variable, never the value
    nor a part of it. Each value is an otherwise valid token of 40 characters, so its length is never the reason; from
    the file, the line break after the token goes and the spaces before it stay."""
    print_section("Wake token: visible ASCII characters only")
    valid = a_token()[:40]
    value = spoil(valid)
    set_token(monkeypatch, tmp_path, source, value)
    with pytest.raises(SleepWakeConfigError) as refused:
        wake_token()

    error = refused.value
    shown = [part for part in (value, valid[:20], valid[20:]) if part in f"{error} {error!r} {error.args}"]
    assert (error.code, error.variable) == ("WAKE_TOKEN_NOT_VISIBLE_ASCII", TOKEN_VARIABLE), f"the error's code and variable: {(error.code, error.variable)}"
    assert TOKEN_VARIABLE in str(error), f"the message names the variable: {error}"
    assert shown == [], f"the message must never carry the value, nor a part of it: {len(shown)} part(s) shown"
    print_success(f"{source}: refused, WAKE_TOKEN_NOT_VISIBLE_ASCII, the variable named, no value")


@pytest.mark.parametrize(
    "spoil",
    [
        pytest.param(lambda token: f"{token}\u00e9", id="short-and-non-ascii"),
        pytest.param(lambda token: f" {token}", id="short-with-a-leading-space"),
    ],
)
def test_the_characters_are_checked_before_the_length(monkeypatch, spoil):
    """WAKE-008: a value too short that also holds a character outside visible ASCII raises the code of the characters,
    ``WAKE_TOKEN_NOT_VISIBLE_ASCII``, checked first, never that of the length; never with the value."""
    short = a_token()[:10]
    value = spoil(short)
    assert len(value) < MIN_LENGTH, "Precondition: the value is too short as well"
    monkeypatch.setenv(TOKEN_VARIABLE, value)
    with pytest.raises(SleepWakeConfigError) as refused:
        wake_token()

    error = refused.value
    assert error.code == "WAKE_TOKEN_NOT_VISIBLE_ASCII", f"the characters are checked before the length: {error.code}"
    assert short not in f"{error} {error!r} {error.args}", "the message must never carry the value"


#: Tokens at the edges of the rule, each taken as written: 32 characters, the shortest token, from "!" (0x21) to "~"
#: (0x7E), the first and the last visible ASCII characters, with the punctuation of base64 and of its URL-safe variant
#: between them (1 + 6 + 24 + 1); and a token of every visible ASCII character.
EDGE_TOKENS = [
    pytest.param("!" + "+/=-_." + "0123456789abcdefABCDEFGH" + "~", id="32-characters-from-0x21-to-0x7e"),
    pytest.param(VISIBLE_ASCII, id="every-visible-ascii-character"),
]


@pytest.mark.parametrize("source", ["variable", "file"])
@pytest.mark.parametrize("token", EDGE_TOKENS)
def test_tokens_at_the_edges_of_visible_ascii_are_taken_as_written(monkeypatch, tmp_path, token, source):
    """WAKE-009: the edges are inside the rule: ``!``, ``~``, the punctuation of a generated token (``+/=-_.``) and every
    visible ASCII character, in a token of 32 characters or more, are returned as written, from the variable and from
    the file."""
    assert len(token) >= MIN_LENGTH and set(token) <= set(VISIBLE_ASCII), "Precondition: a token of visible ASCII characters, long enough"
    set_token(monkeypatch, tmp_path, source, token)
    assert wake_token() == token, f"{source}: a token of visible ASCII characters is returned as written"


#: Values set as both tokens, the wake one and the panel's, with the outcome the shared rule gives each: taken as
#: written, or refused for the reason its code names after ``_TOKEN_``.
SHARED_RULE = [
    pytest.param(a_token, "taken", id="64-hex-characters"),
    pytest.param(lambda: a_token()[:MIN_LENGTH], "taken", id="32-characters"),
    pytest.param(lambda: VISIBLE_ASCII, "taken", id="every-visible-ascii-character"),
    pytest.param(lambda: a_token()[: MIN_LENGTH - 1], "TOO_SHORT", id="31-characters"),
    pytest.param(lambda: f"{a_token()[:20]} {a_token()[:20]}", "NOT_VISIBLE_ASCII", id="inner-space"),
    pytest.param(lambda: f"{a_token()[:20]}\x7f{a_token()[:20]}", "NOT_VISIBLE_ASCII", id="del-0x7f"),
    pytest.param(lambda: f"{a_token()[:10]}\u00e9", "NOT_VISIBLE_ASCII", id="short-and-non-ascii"),
]


def outcome(read: Callable[[], str | None], refusal: type[Exception], value: str) -> str:
    """``taken`` when ``read()`` returns ``value``; for a refusal, the reason its code names after ``_TOKEN_``."""
    try:
        token = read()
    except refusal as refused:
        return getattr(refused, "code", "").partition("_TOKEN_")[2] or f"refused without a code: {type(refused).__name__}"
    return "taken" if token == value else "another value"


@pytest.mark.parametrize(("make", "expected"), SHARED_RULE)
def test_the_wake_token_follows_the_rule_of_the_panel_token_value_for_value(monkeypatch, make, expected):
    """WAKE-010 — D-W2: a token of its own, with the rules of the panel's backup token, one definition
    (``PANEL_TOKEN_CHARACTERS``, ``PANEL_TOKEN_MIN_LENGTH``): the same value set as both tokens is taken by both, or
    refused by both for the same reason, ``WAKE_TOKEN_*`` beside ``BACKUP_DOWNLOAD_TOKEN_*``."""
    assert (PANEL_TOKEN_MIN_LENGTH, PANEL_TOKEN_CHARACTERS) == (MIN_LENGTH, frozenset(VISIBLE_ASCII)), "Precondition: the panel's rule is the rule documented"
    value = make()
    monkeypatch.setenv(TOKEN_VARIABLE, value)
    monkeypatch.setenv(PANEL_TOKEN_VARIABLES[0], value)

    outcomes = {"wake": outcome(wake_token, SleepWakeConfigError, value), "panel": outcome(backup_download_token, BackupConfigError, value)}

    assert outcomes == {"wake": expected, "panel": expected}, f"the wake token and the panel's share one rule: {outcomes}, expected {expected}"


# =============================================================================
# WAKE-011..015: the route off, a token the server cannot use, a request without the token
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unset",
    [
        pytest.param({}, id="neither-variable"),
        pytest.param({TOKEN_VARIABLE: "   "}, id="blank-variable"),
        pytest.param({TOKEN_FILE_VARIABLE: " "}, id="blank-file-variable"),
    ],
)
async def test_without_a_token_the_route_answers_as_a_path_that_does_not_exist(app, monkeypatch, run, unset):
    """WAKE-011: no token, the route answers 404 ``{"detail": "Not Found"}`` whatever the request carries, as a path that
    does not exist; no run starts. Barriers: with a token set, the same path answers the route's 401; a path that does
    not exist answers that very 404."""
    print_section("Wake-up: the route off")
    token = a_token()
    with monkeypatch.context() as on:
        on.setenv(TOKEN_VARIABLE, token)
        mounted = await send(app, never=[token])
    for name, value in unset.items():
        monkeypatch.setenv(name, value)
    requests = [("no Authorization", None), ("Bearer, the token of before", f"Bearer {token}"), ("Bearer, another token", f"Bearer {a_token()}"), ("Basic", "Basic d2FrZTpwYXNzd29yZA==")]

    nowhere = await send(app, path=f"{WAKE_SYNC}/nowhere")
    answers = {label: (await send(app, authorization=authorization, never=[token])).answer for label, authorization in requests}

    assert shape(mounted) == UNAUTHORIZED, f"Barrier: with a token set, the path answers the route's 401, so the route is there: {mounted.answer}"
    assert nowhere.answer == OFF_ANSWER, f"Barrier: a path that does not exist answers {OFF_ANSWER}: {nowhere.answer}"
    assert answers == dict.fromkeys(answers, OFF_ANSWER), f"without a token the route must answer as a path that does not exist, {OFF_ANSWER}: {answers}"
    assert run.reasons == [], f"no run may start while the route is off: {run.reasons}"
    print_success(f"{len(answers)} requests without a token: 404 Not Found, no run")


@dataclass(frozen=True)
class Unusable:
    """A token the server cannot use, as a test set it: what must never show (the value, or its parts), what a caller
    may present as written, and its file, if any."""

    never: list[str]
    presentable: list[str]
    path: Path | None


UNUSABLE_KINDS = ["too-short", "too-short-in-its-file", "spaces-around", "e-acute-inside", *sorted(BROKEN_FILES)]


def set_unusable_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, kind: str) -> Unusable:
    """A token the server cannot use, by ``kind``: 31 characters in the variable or in its file; a valid token with spaces
    around it, or with an é inside, in the variable; or a file of ``BROKEN_FILES``."""
    valid = a_token()[:40]
    short = valid[: MIN_LENGTH - 1]
    if kind == "too-short":
        monkeypatch.setenv(TOKEN_VARIABLE, short)
        return Unusable([short], [short], None)
    if kind == "too-short-in-its-file":
        path = write_token_file(tmp_path, short + "\n")
        monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))
        return Unusable([short], [short], path)
    if kind == "spaces-around":
        monkeypatch.setenv(TOKEN_VARIABLE, f" {valid} ")
        return Unusable([f" {valid} ", valid], [f" {valid} ", valid], None)
    if kind == "e-acute-inside":
        monkeypatch.setenv(TOKEN_VARIABLE, f"{valid[:20]}\u00e9{valid[20:]}")
        return Unusable([f"{valid[:20]}\u00e9{valid[20:]}", valid[:20], valid[20:]], [], None)
    path = tmp_path / "wake-token"
    BROKEN_FILES[kind](path)
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(path))
    return Unusable([], [], path)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", UNUSABLE_KINDS)
async def test_a_token_the_server_cannot_use_answers_503_and_logs_one_error(app, monkeypatch, tmp_path, run, kind):
    """WAKE-012: the route answers 503 ``wake_unavailable`` (a code and a message), with or without a token presented, the
    configured value itself included; each request logs exactly one error, naming the variable and never its value
    (the barrier of the log: the canary of ``captured_log``); the answer never holds the value nor the file's path,
    which the log may hold; no run starts."""
    print_section(f"Wake-up: a token the server cannot use ({kind})")
    unusable = set_unusable_token(monkeypatch, tmp_path, kind)
    requests = [("no Authorization", None), ("Bearer, a token of the right length", f"Bearer {a_token()}"), ("Basic", f"Basic {a_token()}")]
    requests += [(f"Bearer, the configured value #{index}", f"Bearer {value}") for index, value in enumerate(unusable.presentable)]

    exchanges = {label: await send(app, authorization=authorization, never=unusable.never) for label, authorization in requests}

    shapes = {label: shape(exchange) for label, exchange in exchanges.items()}
    logged = {label: [TOKEN_VARIABLE in repr(event) for event in exchange.errors] for label, exchange in exchanges.items()}
    paths_shown = [label for label, exchange in exchanges.items() if unusable.path is not None and str(unusable.path) in f"{exchange.response.text}\n{exchange.response.headers}"]
    assert shapes == dict.fromkeys(shapes, UNAVAILABLE), f"the route must answer {UNAVAILABLE} whatever the request presents: {shapes}"
    assert logged == dict.fromkeys(logged, [True]), f"each request logs exactly one error, naming {TOKEN_VARIABLE}: {logged}"
    assert paths_shown == [], f"the path of the token's file may be in the log, never in an answer: {paths_shown}"
    assert run.reasons == [], f"no run may start with a token the server cannot use: {run.reasons}"
    print_success(f"{len(exchanges)} requests: 503 wake_unavailable, one error line each naming the variable")


@pytest.mark.asyncio
async def test_without_the_token_the_route_answers_401_and_starts_no_run(app, monkeypatch, run):
    """WAKE-013: the token missing or wrong, the route answers 401 ``wake_unauthorized`` (a code and a message) with
    ``WWW-Authenticate: Bearer``, and no run starts. Barrier: the right token then starts one, of reason "wake"."""
    print_section("Wake-up: a request without the token")
    token, bearer = with_token(monkeypatch)
    wrong = [
        ("no Authorization", None, None),
        ("Basic, the token", f"Basic {token}", None),
        ("Bearer with nothing", "Bearer", None),
        ("Bearer and a space", "Bearer ", None),
        ("Bearer, another token", f"Bearer {a_token()}", None),
        ("Bearer, a prefix of the token", f"Bearer {token[:-1]}", None),
        ("Bearer, an extension of the token", f"Bearer {token}0", None),
        ("Bearer, the token in capitals", f"Bearer {token.upper()}", None),
        ("the token in the query string", None, {"token": token, "access_token": token}),
    ]

    exchanges = {label: await send(app, authorization=authorization, params=params, never=[token]) for label, authorization, params in wrong}
    refused_runs = list(run.reasons)
    served = await send(app, authorization=bearer, never=[token])

    shapes = {label: shape(exchange) for label, exchange in exchanges.items()}
    challenges = {label: exchange.response.headers.get("www-authenticate") for label, exchange in exchanges.items()}
    assert shapes == dict.fromkeys(shapes, UNAUTHORIZED), f"the route must answer {UNAUTHORIZED} without the right token: {shapes}"
    assert challenges == dict.fromkeys(challenges, "Bearer"), f"each 401 must ask for a Bearer token: {challenges}"
    assert refused_runs == [], f"no run may start without the right token: {refused_runs}"
    assert (served.response.status_code, run.reasons) == (200, ["wake"]), f"Barrier: the right token starts one run, of reason wake: {served.answer}, runs {run.reasons}"
    print_success(f"{len(exchanges)} requests without the right token: 401 Bearer, no run")


@pytest.mark.asyncio
async def test_the_token_from_its_file_opens_the_route_and_the_variable_wins(app, monkeypatch, tmp_path, run):
    """WAKE-014: the token read from the ``_FILE`` (a line break after it) opens the route; with the variable set too, the
    variable's token opens it and the file's no longer does."""
    from_file, from_variable = a_token(), a_token()
    monkeypatch.setenv(TOKEN_FILE_VARIABLE, str(write_token_file(tmp_path, from_file + "\n")))
    both = [from_file, from_variable]

    file_only = await send(app, authorization=f"Bearer {from_file}", never=both)
    await run.task_done(1)
    monkeypatch.setenv(TOKEN_VARIABLE, from_variable)
    variable = await send(app, authorization=f"Bearer {from_variable}", never=both)
    await run.task_done(2)
    file_after = await send(app, authorization=f"Bearer {from_file}", never=both)

    assert file_only.response.status_code == 200, f"the token of the file opens the route: {file_only.answer}"
    assert variable.response.status_code == 200, f"both set, the variable's token opens the route: {variable.answer}"
    assert shape(file_after) == UNAUTHORIZED, f"both set, the file's token no longer opens it: {file_after.answer}"
    assert run.reasons == ["wake", "wake"], f"one run for each request let through: {run.reasons}"


@pytest.mark.asyncio
async def test_the_token_never_shows_in_an_answer_or_the_log(app, monkeypatch, run):
    """WAKE-015: across a 401 (another token presented), a 503 (the configured value too short, presented itself) and a
    200 (the token), neither the token nor the configured value nor what was presented shows in the body, the headers
    or the log (``send`` checks each). The check read real events: the 503's error, the 200's start and end."""
    print_section("Wake-up: the token never shows")
    token, bearer = with_token(monkeypatch)
    short = token[: MIN_LENGTH - 1]

    refused = await send(app, authorization=f"Bearer {a_token()}", never=[token])
    with monkeypatch.context() as unusable_token:
        unusable_token.setenv(TOKEN_VARIABLE, short)
        unusable = await send(app, authorization=f"Bearer {short}", never=[token, short])
    served = await send(app, authorization=bearer, never=[token])

    statuses = (refused.response.status_code, unusable.response.status_code, served.response.status_code)
    assert statuses == (401, 503, 200), f"Precondition: a 401, a 503 and a 200: {statuses}"
    assert len(unusable.errors) == 1, f"Barrier: the 503's error line was captured: {unusable.events}"
    assert (levels(served.events, RUN_STARTED), levels(served.events, RUN_FINISHED)) == (["info"], ["info"]), f"Barrier: the 200's lines were captured: {served.events}"
    print_success("401, 503, 200: the token in no answer and no log line")


# =============================================================================
# WAKE-016..019: the answer, streamed
# =============================================================================


@pytest.mark.asyncio
async def test_with_the_token_the_run_starts_and_the_answer_is_its_report(app, monkeypatch, run):
    """WAKE-016: with the token and no run in progress, one run of reason "wake"; 200, ``application/json``,
    ``Cache-Control: no-store``; the body starts with a space and ends with the JSON of ``WakeSyncResponse``, exactly
    its keys, the values of the ``RunReport`` returned: its status, its moments (ISO 8601, UTC), no error, and each job
    with every field, a job not due included — the items deferred and their retry since lot Z7b."""
    print_section("Wake-up: the answer")
    token, bearer = with_token(monkeypatch)
    run.jobs = (deferring(RAN_PARTLY), NOT_DUE)

    exchange = await send(app, authorization=bearer, never=[token])

    headers = {name: exchange.response.headers.get(name) for name in ("content-type", "cache-control")}
    assert exchange.response.status_code == 200, f"with the token: 200: {exchange.answer}"
    assert headers == {"content-type": "application/json", "cache-control": "no-store"}, f"the answer's headers: {headers}"
    assert (run.reasons, len(run.returned)) == (["wake"], 1), f"one run, of reason wake: {run.reasons}"
    assert exchange.response.content[:1] == b" ", f"the body starts with the space sent at once: {exchange.response.content[:40]!r}"
    result = read_result(exchange.response.content)
    assert result == as_body(run.returned[0]), f"the body is the report returned: {exchange.response.content!r}"
    assert [(job["name"], job["items_deferred"], job["retry_at"]) for job in result["jobs"]] == [("current_price", 3, RETRY_AT), ("history_sync", 0, None)], f"lot Z7b: the items deferred and their retry, from each outcome: {result['jobs']}"
    print_success("200 application/json no-store; a space, then the report")


#: Reports of every status a run can end with, each with jobs that fit it.
REPORTED = [
    pytest.param("ok", (RAN_OK, NOT_DUE), id="ok"),
    pytest.param("partial", (RAN_PARTLY, NOT_DUE), id="partial"),
    pytest.param("error", (RAN_INTO_ERRORS, RAISED), id="error"),
    pytest.param("disabled", (), id="disabled"),
    # Only without fcntl, where the leader election is the fallback (Z-11, N71): with the lock across processes no run
    # answers not_leader any more (WAKE-029). The route mirrors it all the same.
    pytest.param("not_leader", (), id="not-leader"),
    pytest.param("blocked", (), id="blocked"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "jobs"), REPORTED)
async def test_whatever_the_status_of_the_run_the_answer_is_200_with_it(app, monkeypatch, run, status, jobs):
    """WAKE-017 — N-Z4-1: past the token and the gate the answer is 200 whatever the run's status, which the body carries
    with the run's jobs: after the first byte the status code cannot change."""
    token, bearer = with_token(monkeypatch)
    run.status, run.jobs = status, jobs

    exchange = await send(app, authorization=bearer, never=[token])

    assert exchange.response.status_code == 200, f"a run of status {status}: 200: {exchange.answer}"
    assert len(run.returned) == 1, f"one run: {run.reasons}"
    assert read_result(exchange.response.content) == as_body(run.returned[0]), f"the body is the report of status {status}: {exchange.response.content!r}"


@pytest.mark.asyncio
async def test_the_first_space_leaves_before_the_run_ends(app, monkeypatch, run):
    """WAKE-018 — N-Z4-6: with ``WAKE_KEEPALIVE_SECONDS`` at an hour and the run held, the start of a 200 answer
    (``application/json``, no-store) and one body message, exactly a space with more to follow, leave before the run is
    released, and nothing else: the panel has its 200 as soon as the request is accepted. Released, the body ends with
    the report's JSON."""
    print_section("Wake-up: the first space, at once")
    token, bearer = with_token(monkeypatch)
    monkeypatch.setattr(wake, "WAKE_KEEPALIVE_SECONDS", SLOW_KEEPALIVE_SECONDS)
    release = run.hold(1)
    wire = Wire(app, run.changes, authorization=bearer)

    async with run.cleanup(), wire.running():
        await run.until_started(1, unless=wire.task)
        await wire.until_bodies(1)
        held = (wire.status, wire.chunks(), run.ended)
        release.set()
        await wire.ended()

    status, chunks, ended = held
    headers = {name: wire.headers.get(name) for name in ("content-type", "cache-control")}
    assert ended == 0, "Precondition: the run was still held when the space was read"
    assert status == 200, f"the 200 leaves before the run ends: {wire.start}"
    assert chunks == [(b" ", True)], f"before the run ends, one space and nothing else: {chunks}"
    assert headers == {"content-type": "application/json", "cache-control": "no-store"}, f"the answer's headers: {headers}"
    assert wire.chunks()[-1][1] is False, f"the body ends once the run ends: {wire.chunks()}"
    assert read_result(wire.body) == as_body(run.returned[0]), f"after the space, the report: {wire.body!r}"
    assert wire.shows([token]) == [], "the token never shows in the answer"
    print_success("200 and a space before the run's end; then the report")


@pytest.mark.asyncio
async def test_a_space_leaves_at_every_keepalive_period_while_the_run_lasts(app, monkeypatch, run):
    """WAKE-019 — D7: with ``WAKE_KEEPALIVE_SECONDS`` at a few milliseconds, read at the call, at least three body
    messages leave while the run is held, each exactly a space with more to follow; released, the body ends with the
    report's JSON, the spaces before it valid JSON whitespace."""
    print_section("Wake-up: the keep-alive spaces")
    token, bearer = with_token(monkeypatch)
    monkeypatch.setattr(wake, "WAKE_KEEPALIVE_SECONDS", FAST_KEEPALIVE_SECONDS)
    release = run.hold(1)
    wire = Wire(app, run.changes, authorization=bearer)

    async with run.cleanup(), wire.running():
        await run.until_started(1, unless=wire.task)
        await wire.until_bodies(KEEPALIVES)
        while_held = (wire.chunks(), run.ended)
        release.set()
        await wire.ended()

    chunks, ended = while_held
    assert ended == 0, "Precondition: the run was still held when the spaces were read"
    assert len(chunks) >= KEEPALIVES and chunks == [(b" ", True)] * len(chunks), f"while the run lasts, spaces only, each with more to follow: {chunks}"
    assert wire.chunks()[-1][1] is False, f"the body ends once the run ends: {wire.chunks()}"
    assert read_result(wire.body) == as_body(run.returned[0]), f"after the spaces, the report: {wire.body!r}"
    print_success(f"{len(chunks)} spaces while the run lasted; then the report")


# =============================================================================
# WAKE-020..021: one wake-up at a time (D-W1)
# =============================================================================


@pytest.mark.asyncio
async def test_one_wake_up_at_a_time_and_the_token_is_checked_before_the_gate(app, monkeypatch, run):
    """WAKE-020 — D-W1: while a first wake-up's run is held, a request without the token or with another one answers
    401, with the token unset 404, with it too short 503, as without a run: the token is checked before anything else.
    With the right token, 409 ``wake_in_progress`` (a code and a message), and no run starts. Released, the first is
    served its report; once its run is over the next call is served too: two runs in all."""
    print_section("Wake-up: one at a time")
    token, bearer = with_token(monkeypatch)
    short = token[: MIN_LENGTH - 1]
    release = run.hold(1)

    with captured_log() as log:
        async with run.cleanup():
            first = run.changes.watch(asyncio.create_task(send(app, authorization=bearer, never=[token], log=log), name="first-wake-up"))
            try:
                await run.until_started(1, unless=first)
                stranger = await send(app, never=[token], log=log)
                wrong = await send(app, authorization=f"Bearer {a_token()}", never=[token], log=log)
                with monkeypatch.context() as meanwhile:
                    meanwhile.setenv(TOKEN_VARIABLE, "   ")
                    off = await send(app, authorization=bearer, never=[token], log=log)
                    meanwhile.setenv(TOKEN_VARIABLE, short)
                    unusable = await send(app, authorization=bearer, never=[token, short], log=log)
                busy = await send(app, authorization=bearer, never=[token], log=log)
                runs_while_held = list(run.reasons)
                release.set()
                served = await within(first, "the first wake-up never answered")
                await run.task_done(1)
                again = await send(app, authorization=bearer, never=[token], log=log)
            finally:
                await settle(first)

    assert (shape(stranger), shape(wrong)) == (UNAUTHORIZED, UNAUTHORIZED), f"during a run, no token or another one: 401 first: {stranger.answer}, {wrong.answer}"
    assert off.answer == OFF_ANSWER, f"during a run, the token unset: the route is off first: {off.answer}"
    assert shape(unusable) == UNAVAILABLE, f"during a run, a token too short: 503 first: {unusable.answer}"
    assert shape(busy) == IN_PROGRESS, f"during a run, the right token: {IN_PROGRESS}: {busy.answer}"
    assert runs_while_held == ["wake"], f"no request during the run started another: {runs_while_held}"
    assert served.response.status_code == 200 and read_result(served.response.content) == as_body(run.returned[0]), f"the first wake-up is served its report: {served.answer}"
    assert again.response.status_code == 200, f"once the run is over, the next call is served: {again.answer}"
    assert run.reasons == ["wake", "wake"], f"two runs in all, the 409 started none: {run.reasons}"
    print_success("during a run: 401, 404, 503 first, then 409; after it: 200")


@pytest.mark.asyncio
async def test_a_client_that_disconnects_leaves_its_run_to_end_and_the_gate_closed_until_then(app, monkeypatch, run):
    """WAKE-021 — D-W1, N-Z4-3: the client goes away after the first space, the run held. The answer ends, the run does
    not: it is never cancelled; a call meanwhile meets 409 and "Wake-up run finished" is not logged yet. Released, the
    run ends: "finished" is logged once, at INFO, and the next call is served."""
    print_section("Wake-up: the client goes away")
    token, bearer = with_token(monkeypatch)
    monkeypatch.setattr(wake, "WAKE_KEEPALIVE_SECONDS", SLOW_KEEPALIVE_SECONDS)
    release = run.hold(1)
    wire = Wire(app, run.changes, authorization=bearer)

    with captured_log() as log:
        async with run.cleanup(), wire.running():
            await run.until_started(1, unless=wire.task)
            await wire.until_bodies(1)
            wire.disconnect()
            await wire.ended()
            runs_over_when_the_answer_ended = run.ended
            meanwhile = await send(app, authorization=bearer, never=[token], log=log)
            finished_while_held = levels(log, RUN_FINISHED)
            release.set()
            task = await run.task_done(1)
            finished_once_over = levels(log, RUN_FINISHED)
            after = await send(app, authorization=bearer, never=[token], log=log)

    assert (wire.status, wire.chunks()[:1]) == (200, [(b" ", True)]), f"Precondition: the client went away mid-stream: {wire.start}, {wire.chunks()}"
    assert runs_over_when_the_answer_ended == 0, f"the answer ended, the run must go on: cancelled with it? {run.cancelled}"
    assert shape(meanwhile) == IN_PROGRESS, f"the run still going, a call meets {IN_PROGRESS}: {meanwhile.answer}"
    assert finished_while_held == [], f"the run is not finished while it is held: {finished_while_held}"
    assert (run.cancelled[:1], task.cancelled()) == ([False], False), f"the run must never be cancelled by its client's going: {run.cancelled}, {ending_of(task)}"
    assert finished_once_over == ["info"], f"the run's end is logged once, at INFO, the client gone: {finished_once_over}"
    assert after.response.status_code == 200, f"once the run is over, the next call is served: {after.answer}"
    assert run.reasons == ["wake", "wake"], f"two runs in all: {run.reasons}"
    assert wire.shows([token]) == [], "the token never shows in the answer"
    print_success("disconnected: the run went on, 409 meanwhile, finished logged, then 200")


# =============================================================================
# WAKE-022..024: a run that raises, the log, a blocked instance (D-W3)
# =============================================================================


@pytest.mark.asyncio
async def test_a_run_that_raises_answers_200_error_by_its_class_name_only(app, monkeypatch, run):
    """WAKE-022 — N-Z4-2: the run raises ``RuntimeError`` with a secret in its message. Still 200: ``status`` "error",
    ``error`` "RuntimeError", ``jobs`` empty, ``started_at <= finished_at`` in UTC, the message nowhere in the body; the
    failure logged at error, "Wake-up run failed". The gate reopened: the next call is served."""
    print_section("Wake-up: a run that raises")
    token, bearer = with_token(monkeypatch)
    run.failure = RuntimeError(SECRET_MESSAGE)

    failed = await send(app, authorization=bearer, never=[token])
    await run.task_done(1)
    run.failure = None
    next_call = await send(app, authorization=bearer, never=[token])

    assert failed.response.status_code == 200, f"a run that raises still answers 200: {failed.answer}"
    body = read_result(failed.response.content)
    assert (body["status"], body["error"], body["jobs"]) == ("error", "RuntimeError", []), f"status error, the class name only, no job: {body}"
    assert body["started_at"] <= body["finished_at"], f"started no later than it finished: {body}"
    assert b"SECRET" not in failed.response.content, f"the exception's message never reaches the body: {failed.response.content!r}"
    assert levels(failed.events, RUN_FAILED) == ["error"], f"the failure is logged once, at error: {failed.events}"
    assert (next_call.response.status_code, run.reasons) == (200, ["wake", "wake"]), f"the gate reopened after the failed run: {next_call.answer}, runs {run.reasons}"
    print_success("200, status error, RuntimeError, no message; logged; the next call served")


@pytest.mark.asyncio
async def test_a_run_is_logged_started_then_finished_with_its_status(app, monkeypatch, run):
    """WAKE-023: "Wake-up run started", then "Wake-up run finished", both at INFO, once each; the second carries a
    ``status``. Event names and levels only: the words of the lines are free."""
    token, bearer = with_token(monkeypatch)

    exchange = await send(app, authorization=bearer, never=[token])

    lines = [(entry.get("event"), entry.get("log_level")) for entry in exchange.events if entry.get("event") in (RUN_STARTED, RUN_FINISHED)]
    finished = [entry for entry in exchange.events if entry.get("event") == RUN_FINISHED]
    assert exchange.response.status_code == 200, f"Precondition: the run was served: {exchange.answer}"
    assert lines == [(RUN_STARTED, "info"), (RUN_FINISHED, "info")], f"started, then finished, at INFO: {lines}"
    assert all("status" in entry for entry in finished), f"the end of a run is logged with its status: {finished}"


async def settled_at_once() -> None:
    """``settle_clock`` without its wait: a run of reason "wake" settles first."""


def trap(name: str, reached: list[str]) -> Callable[..., NoReturn]:
    """A collaborator of the scheduler that must not be reached: a call is recorded, and raises."""

    def trapped(*_args: object, **_kwargs: object) -> NoReturn:
        reached.append(name)
        raise AssertionError(f"scheduler.{name} was reached past the switches")

    return trapped


@pytest.mark.asyncio
async def test_on_a_blocked_instance_the_real_run_answers_blocked_and_reaches_nothing_past_the_switches(app, monkeypatch, run):
    """WAKE-024 — D-W3, with the real ``run_due_jobs`` put back on the wake module: ``LIBREFOLIO_NO_SCHEDULER`` cleared,
    the instance blocked (``scheduler.instance_blocked``), the settle a no-op, and every collaborator past the two
    switches a trap — the lock across processes of Z-11 included. The answer is 200 with ``status`` "blocked", no job
    and no error; no trap was reached."""
    print_section("Wake-up: a blocked instance, the real scheduler")
    assert SHIPPED_RUN_DUE_JOBS is REAL_RUN_DUE_JOBS, "Precondition: the wake module ships the scheduler's run_due_jobs, which this test puts back"
    monkeypatch.setattr(wake, "run_due_jobs", REAL_RUN_DUE_JOBS)
    monkeypatch.delenv("LIBREFOLIO_NO_SCHEDULER", raising=False)
    monkeypatch.setattr(scheduler, "instance_blocked", lambda: True)
    monkeypatch.setattr(scheduler, "settle_clock", settled_at_once)
    reached: list[str] = []
    for name in PAST_THE_SWITCHES:
        monkeypatch.setattr(scheduler, name, trap(name, reached))
    # Z-11 (N71): the lock across processes is past the switches too; raising=False, the name exists once Z-11 does.
    monkeypatch.setattr(scheduler, "scheduler_run_lock", trap("scheduler_run_lock", reached), raising=False)
    token, bearer = with_token(monkeypatch)

    exchange = await send(app, authorization=bearer, never=[token])

    assert exchange.response.status_code == 200, f"a blocked instance still answers 200: {exchange.answer}"
    body = read_result(exchange.response.content)
    assert (body["status"], body["jobs"], body["error"]) == ("blocked", [], None), f"status blocked, no job, no error: {body}"
    assert body["started_at"] <= body["finished_at"], f"started no later than it finished: {body}"
    assert reached == [], f"nothing past the switches may be reached on a blocked instance: {reached}"
    assert run.reasons == [], f"the real run answered, not the fake: {run.reasons}"
    print_success("blocked: 200, status blocked, no job, nothing past the switches")


class RunCollaborators:
    """What the real run reaches past its switches, for WAKE-029, in memory: the settings enabled; a state store; both jobs
    due until they ran, run as fakes that write their ``JobState``; ``am_i_leader`` answering no, its calls counted; the
    lock across processes a stand-in that counts its entries and exits, and writes no file."""

    def __init__(self) -> None:
        self.stored = SchedulerState()
        self.leader_asked = 0
        self.locks_entered = 0
        self.locks_left = 0

    def install(self, monkeypatch: pytest.MonkeyPatch, *, lock_available: bool) -> None:
        settings = SchedulerSettings(scheduler_enabled=True, current_price_frequency_minutes=10, history_sync_times=[], history_sync_days=["mon"], history_sync_horizon_days=14, scheduler_timezone="UTC")

        async def enabled_settings() -> SchedulerSettings:
            return settings

        monkeypatch.setattr(scheduler, "instance_blocked", lambda: False)
        monkeypatch.setattr(scheduler, "settle_clock", settled_at_once)
        monkeypatch.setattr(scheduler, "PRICE_REFRESH", scheduler.PriceRefreshTracker())
        monkeypatch.setattr(scheduler, "am_i_leader", self.am_i_leader)
        monkeypatch.setattr(scheduler, "load_scheduler_settings", enabled_settings)
        monkeypatch.setattr(scheduler, "load_state", lambda: replace(self.stored))
        monkeypatch.setattr(scheduler, "save_state", self.save_state)
        monkeypatch.setattr(scheduler, "due_current_price", lambda now, settings, state: state.current_price.last_run_at is None)
        monkeypatch.setattr(scheduler, "due_history_sync", lambda now, settings, state: state.history_sync.last_run_at is None)
        monkeypatch.setattr(scheduler, "run_current_price_refresh", self.current_price)
        monkeypatch.setattr(scheduler, "run_history_sync", self.history_sync)
        # Z-11 (N71): names the scheduler has only once the lock across processes exists, hence raising=False.
        monkeypatch.setattr(scheduler, "cross_process_lock_available", lambda: lock_available, raising=False)
        monkeypatch.setattr(scheduler, "scheduler_run_lock", self.scheduler_run_lock, raising=False)

    def am_i_leader(self) -> bool:
        self.leader_asked += 1
        return False

    def save_state(self, state: SchedulerState) -> None:
        self.stored = replace(state)

    @asynccontextmanager
    async def scheduler_run_lock(self, *_args: object, **_kwargs: object) -> AsyncIterator[None]:
        self.locks_entered += 1
        try:
            yield
        finally:
            self.locks_left += 1

    async def current_price(self, state: SchedulerState) -> None:
        state.current_price = JobState(last_run_at=datetime.now(UTC).isoformat(), last_duration_s=0.5, last_status="ok", last_items_ok=1)

    async def history_sync(self, state: SchedulerState, horizon_days: object = None) -> None:
        state.history_sync = JobState(last_run_at=datetime.now(UTC).isoformat(), last_duration_s=0.5, last_status="ok", last_items_ok=1)


#: A worker whose ``am_i_leader`` answers no, with and without ``fcntl`` (Z-11, N71): whether the lock across processes is
#: available; then the run's status, its jobs, how often the leader is asked and the lock entered.
NOT_THE_LEADER = [
    pytest.param(True, "ok", [("current_price", "ok"), ("history_sync", "ok")], 0, 1, id="cross-process-lock"),
    pytest.param(False, "not_leader", [], 1, 0, id="fallback-not-the-leader"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("lock_available", "status", "jobs", "asked", "locked"), NOT_THE_LEADER)
async def test_on_a_worker_that_is_not_the_leader_the_real_run_still_runs_its_jobs_behind_the_cross_process_lock(app, monkeypatch, run, lock_available, status, jobs, asked, locked):
    """WAKE-029 — Z-11 (N71), with the real ``run_due_jobs`` put back on the wake module, ``LIBREFOLIO_NO_SCHEDULER``
    cleared and every collaborator of the run past its switches a fake in memory (``RunCollaborators``), on a worker whose
    ``am_i_leader`` answers no. With ``fcntl`` the leader is never asked: the run enters the lock across processes once and
    runs its jobs, 200 with ``status`` "ok" and both jobs "ok". Without it, the fallback: the leader is asked once, 200
    with ``status`` "not_leader", no job, the lock never entered."""
    print_section(f"Wake-up: a worker that is not the leader, {'the cross-process lock' if lock_available else 'the fallback'}")
    assert SHIPPED_RUN_DUE_JOBS is REAL_RUN_DUE_JOBS, "Precondition: the wake module ships the scheduler's run_due_jobs, which this test puts back"
    monkeypatch.setattr(wake, "run_due_jobs", REAL_RUN_DUE_JOBS)
    monkeypatch.delenv("LIBREFOLIO_NO_SCHEDULER", raising=False)
    collaborators = RunCollaborators()
    collaborators.install(monkeypatch, lock_available=lock_available)
    token, bearer = with_token(monkeypatch)

    exchange = await send(app, authorization=bearer, never=[token])

    assert exchange.response.status_code == 200, f"the wake-up answers 200: {exchange.answer}"
    body = read_result(exchange.response.content)
    assert collaborators.leader_asked == asked, f"{'with fcntl available am_i_leader is never asked, the cross-process lock decides (Z-11, N71)' if lock_available else 'without fcntl the leader is asked once, the fallback'}: asked {collaborators.leader_asked} time(s); the body {body}"
    assert (body["status"], [(job["name"], job["status"]) for job in body["jobs"]], body["error"]) == (status, jobs, None), f"the run's status and jobs: {body}"
    assert (collaborators.locks_entered, collaborators.locks_left) == (locked, locked), f"the cross-process lock entered and left once with fcntl, never without: {collaborators.locks_entered}, {collaborators.locks_left}"
    assert run.reasons == [], f"the real run answered, not the fake: {run.reasons}"
    print_success(f"{status}, {len(jobs)} job(s); the leader asked {asked} time(s)")


# =============================================================================
# WAKE-025..026: OpenAPI, the composition, the module's globals
# =============================================================================


def dig(document: object, *keys: str) -> Any:
    """``document[key][key]…``, or None where a key is missing."""
    for key in keys:
        if not isinstance(document, dict) or key not in document:
            return None
        document = document[key]
    return document


def resolve(document: dict[str, Any], schema: object) -> dict[str, Any]:
    """``schema``, or the component its ``$ref`` names; an empty dict for anything else."""
    if isinstance(schema, dict) and "$ref" in schema:
        return dig(document, "components", "schemas", str(schema["$ref"]).rsplit("/", 1)[-1]) or {}
    return schema if isinstance(schema, dict) else {}


def test_openapi_documents_the_route_its_token_and_its_answer():
    """WAKE-025: ``POST /api/v1/system/wake-sync``, tag Hosting panel alone, asks for the ``WakeToken`` HTTP bearer scheme and nothing
    else, and no other route of the system router asks for it; its 200 is ``WakeSyncResponse``, exactly the keys of the
    body, its ``jobs`` an array of a model with exactly the keys of a job (its name is free); 401, 404, 409 and 503 are
    documented."""
    document = system_app().openapi()
    operation = dig(document, "paths", WAKE_SYNC, "post") or {}
    scheme = dig(document, "components", "securitySchemes", "WakeToken") or {}
    asking = sorted(f"{method.upper()} {path}" for path, item in document["paths"].items() for method, entry in item.items() if isinstance(entry, dict) and "WakeToken" in repr(entry.get("security")))
    answer = dig(operation, "responses", "200", "content", "application/json", "schema")
    response_model = dig(document, "components", "schemas", "WakeSyncResponse") or {}
    jobs = dig(response_model, "properties", "jobs") or {}
    job_model = resolve(document, jobs.get("items"))

    assert operation, f"POST {WAKE_SYNC} is documented: {sorted(document['paths'])}"
    assert operation.get("tags") == ["Hosting panel"], f"the route carries the Hosting panel tag alone: {operation.get('tags')}"
    assert operation.get("security") == [{"WakeToken": []}], f"the route asks for the WakeToken scheme and nothing else: {operation.get('security')}"
    assert (scheme.get("type"), scheme.get("scheme")) == ("http", "bearer"), f"WakeToken is an HTTP bearer scheme: {scheme}"
    assert asking == [f"POST {WAKE_SYNC}"], f"wake-sync, and only it, asks for WakeToken: {asking}"
    assert answer == {"$ref": "#/components/schemas/WakeSyncResponse"}, f"the 200 of wake-sync is WakeSyncResponse: {answer}"
    assert set(response_model.get("properties", {})) == BODY_KEYS, f"WakeSyncResponse holds exactly {sorted(BODY_KEYS)}: {response_model}"
    assert jobs.get("type") == "array" and set(job_model.get("properties", {})) == JOB_KEYS, f"jobs is an array of a model holding exactly {sorted(JOB_KEYS)}: {jobs}, {job_model}"
    assert {"401", "404", "409", "503"} <= set(operation.get("responses", {})), f"401, 404, 409 and 503 are documented: {sorted(operation.get('responses', {}))}"


def test_the_route_is_composed_into_the_system_router_and_the_module_ships_its_globals():
    """WAKE-026: ``wake_router`` is an ``APIRouter`` serving ``POST /wake-sync`` with ``wake_sync``; the system router,
    mounted under ``/api/v1`` as ``router.py`` mounts it, serves it at ``POST /api/v1/system/wake-sync`` (the
    composition line of ``api/v1/system/__init__.py``). As shipped, read at import before any test replaced them, the
    module holds ``WAKE_KEEPALIVE_SECONDS`` 15.0 and, as ``run_due_jobs``, the scheduler's own."""
    assert isinstance(wake.wake_router, APIRouter), f"wake_router is an APIRouter: {wake.wake_router!r}"
    own = sorted((sorted(context.methods or ()), context.path) for context in iter_route_contexts(wake.wake_router.routes) if context.endpoint is wake.wake_sync)
    composed = sorted((sorted(context.methods or ()), context.path) for context in iter_route_contexts(system_app().routes) if context.endpoint is wake.wake_sync)

    assert own == [(["POST"], "/wake-sync")], f"wake_router serves POST /wake-sync with wake_sync: {own}"
    assert composed == [(["POST"], WAKE_SYNC)], f"the system router serves wake_sync at POST {WAKE_SYNC}: {composed}"
    assert SHIPPED_KEEPALIVE_SECONDS == 15.0, f"WAKE_KEEPALIVE_SECONDS as shipped: {SHIPPED_KEEPALIVE_SECONDS!r}"
    assert SHIPPED_RUN_DUE_JOBS is REAL_RUN_DUE_JOBS, f"run_due_jobs as shipped is the scheduler's: {SHIPPED_RUN_DUE_JOBS!r}"


# =============================================================================
# WAKE-027..028: through the real middleware stack
# =============================================================================


@pytest.mark.asyncio
async def test_through_the_middleware_stack_a_wake_up_is_in_flight_but_not_the_users_presence(monkeypatch, run, activity):
    """WAKE-027 — D-S1: the app with its middleware stack; while the run is held, the first space gone, the wake-up is
    the one request in flight and the user's presence is untouched (no last request); once its answer ends, nothing is
    in flight and still no presence."""
    print_section("Wake-up: through the middleware stack")
    app = system_app(middleware=True)
    token, bearer = with_token(monkeypatch)
    monkeypatch.setattr(wake, "WAKE_KEEPALIVE_SECONDS", SLOW_KEEPALIVE_SECONDS)
    release = run.hold(1)
    wire = Wire(app, run.changes, authorization=bearer)

    async with run.cleanup(), wire.running():
        await run.until_started(1, unless=wire.task)
        await wire.until_bodies(1)
        during = (activity.in_flight, activity.last_user_request_at)
        release.set()
        await wire.ended()
    after = (activity.in_flight, activity.last_user_request_at)

    assert during == (1, None), f"during the run: the wake-up in flight, no presence: in_flight, last_user_request_at = {during}"
    assert after == (0, None), f"once answered: nothing in flight, still no presence: {after}"
    assert (wire.status, read_result(wire.body)) == (200, as_body(run.returned[0])), f"the answer through the stack: {wire.start}, {wire.body!r}"
    print_success("in flight 1 during the run, no presence; 0 after")


@pytest.mark.asyncio
async def test_through_the_middleware_stack_the_first_gzip_chunk_leaves_before_the_run_ends(monkeypatch, run):
    """WAKE-028: with ``Accept-Encoding: gzip`` and the run held, the first body message still leaves: non-empty, gzip
    (``Content-Encoding: gzip``), more to follow, and on its own it decompresses to a space (Starlette's GZip flushes
    each chunk with ``Z_SYNC_FLUSH``). Released, the whole body decompresses to the space and the report."""
    print_section("Wake-up: the first gzip chunk")
    assert "gzip" in [entry.name for entry in MIDDLEWARE_STACK], "Precondition: the middleware stack compresses"
    app = system_app(middleware=True)
    token, bearer = with_token(monkeypatch)
    monkeypatch.setattr(wake, "WAKE_KEEPALIVE_SECONDS", SLOW_KEEPALIVE_SECONDS)
    release = run.hold(1)
    wire = Wire(app, run.changes, authorization=bearer, accept_encoding="gzip")

    async with run.cleanup(), wire.running():
        await run.until_started(1, unless=wire.task)
        await wire.until_bodies(1)
        (first, more), ended = wire.chunks()[0], run.ended
        release.set()
        await wire.ended()

    assert ended == 0, "Precondition: the run was still held when the first chunk was read"
    assert (wire.status, wire.headers.get("content-encoding")) == (200, "gzip"), f"a gzip answer: {wire.start}"
    assert first != b"" and more is True, f"the first chunk is not empty, and more follow: {first!r}, {more}"
    assert gunzip([first]) == b" ", f"the first chunk decompresses to a space on its own: {first!r}"
    assert read_result(gunzip([chunk for chunk, _ in wire.chunks()])) == as_body(run.returned[0]), "the whole body decompresses to the space and the report"
    print_success("the first gzip chunk before the run's end, a space; then the report")
