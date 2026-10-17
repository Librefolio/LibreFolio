"""``backend.app.services.platform.scheduler.scheduler``: «Aggiornamento prezzi…», what the web app is told while the
scheduler catches up (plan phase01SleepWake §Z5, night decisions N-Z5-1…N-Z5-5, lot Z5).

At startup, on the user's return after a silence and on a scheduled wake-up, ``run_due_jobs`` catches up the missing
prices in the background; the process's ``PRICE_REFRESH`` tracker knows whether such a catch-up is pending and which job
runs, the loop publishes it as the ``X-LibreFolio-Price-Refresh`` header of every API answer (through the activity
record), and ``GET /system/price-refresh`` answers its snapshot. Only catch-ups count, never a regular tick (N-Z5-1). The
contract pinned here:

(a) ``PRICE_REFRESH_HEADER`` "X-LibreFolio-Price-Refresh"; ``CATCH_UP_REASONS`` the frozenset {"startup", "return",
    "wake"}; ``PriceRefreshState`` the literal "idle" | "starting" | "running"; ``PriceRefreshProgress(state, reason, job,
    since, last_finished_at, last_refreshed)`` a frozen dataclass with these fields in this order; ``PRICE_REFRESH`` a
    ``PriceRefreshTracker``, and ``price_refresh_progress()`` its snapshot.
(b) A new tracker is idle: every field None, ``last_refreshed`` False, no header.
(c) ``announce(reason)``: idle → "starting" with the reason and ``since = clock()``; while a catch-up is pending nothing
    changes, the first reason and ``since`` kept. ``announce`` and ``run_started`` refuse a reason outside
    ``CATCH_UP_REASONS`` — "tick" included — with a ``ValueError``, and nothing is counted.
(d) ``run_started(reason)`` counts a catch-up run (runs overlap) and, when idle, starts the catch-up as ``announce`` does.
    ``run_finished()`` ends one counted run; when the last one ends the catch-up is over: idle, and — when at least one
    job finished while it was pending — ``last_finished_at = clock()`` and ``last_refreshed`` = one of them had
    ``items_ok > 0``; otherwise both keep their previous values. With no counted run it is a no-op, never negative: an
    ``announce`` alone is ended by the next ``run_started``…``run_finished`` pair.
(e) ``job_started(name)`` / ``job_finished(items_ok)``: any job of any run. A job finishing while a catch-up is pending
    counts as ran; ``items_ok > 0`` marks the catch-up refreshed; ``None`` (cancelled) ran, not refreshed. A job
    finishing while idle changes nothing visible.
(f) ``snapshot().state``: "running" when pending with a current job (a tick's job running when a return is announced
    shows at once, with its name), "starting" when pending without one, else "idle"; ``job`` only in "running".
    ``header_value()`` "starting" / "running", None when idle. ``reset()`` is (b) again, the run count and the current
    job forgotten.
(g) The wiring of ``run_due_jobs(reason)``: for a catch-up reason ``run_started(reason)`` at entry — before the clock
    settle — and ``run_finished()`` in a ``finally``, also when the run raises or is cancelled; "tick" calls neither.
    Each job: ``job_started(name)`` before, ``job_finished(outcome.items_ok)`` after, ``None`` when cancelled.
(h) The wiring of ``scheduler_loop``: it announces "startup" and registers ``PRICE_REFRESH_HEADER`` with
    ``PRICE_REFRESH.header_value`` on ``current_activity()`` when it starts; its return listener announces "return" on
    the request's own thread, so the very answer to the first request after a silence says "starting"; when it ends the
    header is removed and ``PRICE_REFRESH`` reset.

Pure: no database, no server, no lane port, no network. The tracker cases (a)-(f) build trackers of their own on a fake
wall clock; the process's ``PRICE_REFRESH`` is reset before and after every test (autouse fixture). For (g) every
collaborator of ``run_due_jobs`` past ``PRICE_REFRESH`` is a fake set with ``monkeypatch`` — switches, leader, settings, a
state store in memory, the due functions, the two jobs (each writes the ``items_ok`` the test chose), ``settle_clock``
and the lock across processes (Z-11), a no-op that writes no file — and the fakes read the tracker from inside the
run. For (h) the loop runs as a task of the test's event loop, on the
real ``run_due_jobs`` over the same fakes, behind a recorder that signals each run's end; the process's ``ACTIVITY`` is
replaced only through ``monkeypatch`` by an ``Activity`` on a fake clock. Nothing sleeps: every wait is on an event, with
a bounded timeout.

Red until the code of Z5 exists: the new names are missing from the module (``AttributeError`` in the autouse fixture,
so every case errors), then the loop's cases need ``Activity.register_response_header``.
"""

from __future__ import annotations

import asyncio
import copy
import dataclasses
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, time, timedelta
from typing import Any, get_args

import httpx
import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from backend.app.config import API_V1_PREFIX
from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import JobState, SchedulerState
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.services.platform.sleep_wake.activity import Activity, ActivityMiddleware
from backend.test_scripts.test_utils import print_section, print_success

#: The literals of the contract, never read from the module under test.
HEADER = "X-LibreFolio-Price-Refresh"
CATCH_UP = ("startup", "return", "wake")
SETTLING = ("return", "wake")
STATES = ("idle", "starting", "running")
JOBS = ("current_price", "history_sync")
FIELDS = ("state", "reason", "job", "since", "last_finished_at", "last_refreshed")

#: The longest a test waits for anything: a run, a task.
WAIT_SECONDS = 30.0
#: The fake wall clock of the tracker cases: it moves only when the test moves it.
T0 = datetime(2026, 10, 16, 6, 0, tzinfo=UTC)
#: The activity's fake clock, in seconds, and a silence well past the catch-up threshold of 60 s.
START = 1_000.0
LONG_SILENCE = 600.0
#: A user route under the API prefix, for the cases served through ``ActivityMiddleware``.
API_ROUTE = f"{API_V1_PREFIX}/z5-probe-of-the-test"


class ProviderExploded(Exception):
    """A job's failure."""


@asynccontextmanager
async def _no_cross_process_lock(*_args: object, **_kwargs: object) -> AsyncIterator[None]:
    """``scheduler_run_lock`` stood in for (Z-11, N71): held at once, no file written; ``test_scheduler_run_lock.py`` tests the real one."""
    yield


# =============================================================================
# FAKES
# =============================================================================


class WallClock:
    """The tracker's ``clock``: an aware UTC datetime that moves only when the test sets ``now``."""

    def __init__(self, start: datetime = T0) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


class FakeClock:
    """The activity's clock, in seconds: it moves only when the test sets ``now``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class SignallingActivity(Activity):
    """The test's ``Activity`` on a fake clock; it sets ``header_registered`` when a response header is registered, so a loop test knows the loop has started."""

    def __init__(self, clock: FakeClock) -> None:
        super().__init__(clock=clock)
        self.clock = clock
        self.header_registered = asyncio.Event()

    def register_response_header(self, name: str, provider: Callable[[], str | None]) -> None:
        super().register_response_header(name, provider)
        self.header_registered.set()


def _settings() -> SchedulerSettings:
    return SchedulerSettings(
        scheduler_enabled=True,
        current_price_frequency_minutes=10,
        history_sync_times=[time(6, 0)],
        history_sync_days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        history_sync_horizon_days=14,
        scheduler_timezone="UTC",
    )


class Fakes:
    """Every collaborator of ``run_due_jobs`` past ``PRICE_REFRESH``, faked; each reads the process's tracker when it is called.

    ``due`` names the jobs due; a job run writes ``items_ok[name]`` into its ``JobState`` (so its outcome carries it),
    raises ``failures[name]``, or first waits on ``job_gates[name]``. ``settle_clock`` waits on ``settle_gate`` when one
    is set. ``seen`` holds ``(where, snapshot, header_value)`` at each call: ``"settle"``, ``"job:<name>"``.
    """

    def __init__(self) -> None:
        self.stored = SchedulerState()
        self.due: set[str] = set(JOBS)
        self.items_ok: dict[str, int] = {"current_price": 3, "history_sync": 0}
        self.failures: dict[str, BaseException] = {}
        self.settings_failure: BaseException | None = None
        self.job_gates: dict[str, tuple[asyncio.Event, asyncio.Event]] = {}
        self.settle_gate: asyncio.Event | None = None
        self.settle_entered = asyncio.Event()
        self.seen: list[tuple[str, Any, Any]] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(scheduler, "scheduler_disabled", lambda: False)
        monkeypatch.setattr(scheduler, "instance_blocked", lambda: False)
        monkeypatch.setattr(scheduler, "am_i_leader", lambda: True)
        monkeypatch.setattr(scheduler, "load_scheduler_settings", self.load_scheduler_settings)
        monkeypatch.setattr(scheduler, "load_state", lambda: copy.deepcopy(self.stored))
        monkeypatch.setattr(scheduler, "save_state", self.save_state)
        monkeypatch.setattr(scheduler, "due_current_price", lambda now, settings, state: "current_price" in self.due)
        monkeypatch.setattr(scheduler, "due_history_sync", lambda now, settings, state: "history_sync" in self.due)
        monkeypatch.setattr(scheduler, "run_current_price_refresh", self.run_current_price_refresh)
        monkeypatch.setattr(scheduler, "run_history_sync", self.run_history_sync)
        monkeypatch.setattr(scheduler, "settle_clock", self.settle_clock)
        # Z-11 (N71): with fcntl the run takes the lock across processes; stood in for, so that no .scheduler.lock is
        # written in the lane's data directory. raising=False: the name exists only once Z-11 does.
        monkeypatch.setattr(scheduler, "scheduler_run_lock", _no_cross_process_lock, raising=False)

    def _record(self, where: str) -> None:
        self.seen.append((where, scheduler.PRICE_REFRESH.snapshot(), scheduler.PRICE_REFRESH.header_value()))

    def at(self, where: str) -> list[tuple[Any, Any]]:
        """``(snapshot, header_value)`` of every call recorded at ``where``, in order."""
        return [(snapshot, header) for name, snapshot, header in self.seen if name == where]

    async def load_scheduler_settings(self) -> SchedulerSettings:
        if self.settings_failure is not None:
            raise self.settings_failure
        return _settings()

    def save_state(self, state: SchedulerState) -> None:
        self.stored = copy.deepcopy(state)

    async def run_current_price_refresh(self, state: SchedulerState) -> None:
        await self._job("current_price", state)

    async def run_history_sync(self, state: SchedulerState, horizon_days: object = None) -> None:
        await self._job("history_sync", state)

    async def _job(self, name: str, state: SchedulerState) -> None:
        self._record(f"job:{name}")
        gate = self.job_gates.get(name)
        if gate is not None:
            entered, release = gate
            entered.set()
            await release.wait()
        failure = self.failures.get(name)
        if failure is not None:
            raise failure
        setattr(state, name, JobState(last_run_at=datetime.now(UTC).isoformat(), last_duration_s=0.5, last_status="ok", last_items_ok=self.items_ok[name], last_items_err=0))

    async def settle_clock(self) -> None:
        self._record("settle")
        self.settle_entered.set()
        gate = self.settle_gate
        if gate is not None:
            await gate.wait()


class Runs:
    """``run_due_jobs`` in the loop cases: the real one, behind a recorder of each reason and of each run's end."""

    def __init__(self, real: Callable[[str], Awaitable[Any]]) -> None:
        self.real = real
        self.reasons: list[str] = []
        self.ended = 0
        self._changed: asyncio.Event | None = None

    def _signal(self) -> None:
        if self._changed is not None:
            self._changed.set()

    async def __call__(self, reason: str) -> Any:
        self.reasons.append(reason)
        self._signal()
        try:
            return await self.real(reason)
        finally:
            self.ended += 1
            self._signal()

    async def wait_ended(self, count: int, loop_task: asyncio.Task[None]) -> None:
        if self._changed is None:
            self._changed = asyncio.Event()
        changed = self._changed

        async def reached() -> None:
            while self.ended < count:
                changed.clear()
                await changed.wait()

        await _within(reached(), f"run #{count} ended? the runs so far: {self.reasons}, {self.ended} ended", loop_task=loop_task)


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def fresh_price_refresh() -> Iterator[None]:
    """The process's ``PRICE_REFRESH`` reset before and after every test: no case sees what another left."""
    scheduler.PRICE_REFRESH.reset()
    yield
    scheduler.PRICE_REFRESH.reset()


@pytest.fixture(autouse=True)
def activity(monkeypatch: pytest.MonkeyPatch) -> SignallingActivity:
    """The test's own ``Activity``, on a fake clock, in place of the process's ``ACTIVITY``: ``current_activity()`` answers it."""
    mine = SignallingActivity(FakeClock())
    monkeypatch.setattr(activity_module, "ACTIVITY", mine)
    return mine


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> Fakes:
    world = Fakes()
    world.install(monkeypatch)
    return world


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch, fakes: Fakes) -> Runs:
    """The loop's run: the real ``run_due_jobs`` over the fakes, recorded; the first run at once, a tick of an hour."""
    recorder = Runs(scheduler.run_due_jobs)
    monkeypatch.setattr(scheduler, "run_due_jobs", recorder)
    monkeypatch.setattr(scheduler, "FIRST_RUN_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(scheduler, "TICK_SECONDS", 3_600.0)
    return recorder


def _tracker(clock: WallClock | None = None) -> tuple[Any, WallClock]:
    wall = clock or WallClock()
    return scheduler.PriceRefreshTracker(clock=wall), wall


def _progress(state: str, reason: str | None = None, job: str | None = None, since: datetime | None = None, last_finished_at: datetime | None = None, last_refreshed: bool = False) -> Any:
    return scheduler.PriceRefreshProgress(state=state, reason=reason, job=job, since=since, last_finished_at=last_finished_at, last_refreshed=last_refreshed)


IDLE_NEVER = {"state": "idle", "reason": None, "job": None, "since": None, "last_finished_at": None, "last_refreshed": False}


def _fields(progress: Any) -> dict[str, Any]:
    return {name: getattr(progress, name) for name in FIELDS}


def _view(progress: Any) -> tuple[Any, Any, Any]:
    """``(state, reason, job)``."""
    return (progress.state, progress.reason, progress.job)


def _assert_utc(moment: object, what: str) -> None:
    assert isinstance(moment, datetime) and moment.tzinfo is not None and moment.utcoffset() == timedelta(0), f"{what}: {moment!r} is not an aware datetime in UTC"


def _header_of(activity: Activity) -> list[str]:
    """The values the activity's response headers give the price-refresh header now, its name matched case-insensitively."""
    return [value for name, value in activity.response_headers() if name.lower() == HEADER.lower()]


async def _within(awaitable: Awaitable[Any], what: str | Callable[[], str], *, loop_task: asyncio.Task[None] | None = None) -> Any:
    """What ``awaitable`` gives — or raises —, or a failure naming ``what`` after ``WAIT_SECONDS``; with ``loop_task``, also a failure as soon as the loop ends first (what it raised is then raised by ``_looping``)."""
    waiter = asyncio.ensure_future(awaitable)
    watched: set[asyncio.Future[Any]] = {waiter} if loop_task is None else {waiter, loop_task}
    done, _ = await asyncio.wait(watched, timeout=WAIT_SECONDS, return_when=asyncio.FIRST_COMPLETED)
    if waiter in done:
        return waiter.result()
    waiter.cancel()
    await asyncio.gather(waiter, return_exceptions=True)
    label = what() if callable(what) else what
    if loop_task is not None and loop_task in done:
        pytest.fail(f"{label}: the scheduler loop ended first")
    pytest.fail(f"{label}: nothing within {WAIT_SECONDS} s")


@asynccontextmanager
async def _looping(shutdown: asyncio.Event) -> AsyncIterator[asyncio.Task[None]]:
    """``scheduler_loop(shutdown)`` as a task of this test's event loop; at the end the shutdown is set and the task must end within the deadline."""
    task = asyncio.create_task(scheduler.scheduler_loop(shutdown), name="scheduler-loop-under-test")
    try:
        yield task
    finally:
        shutdown.set()
        done, _ = await asyncio.wait({task}, timeout=WAIT_SECONDS)
        if not done:
            task.cancel()
            await asyncio.wait({task}, timeout=WAIT_SECONDS)
            pytest.fail(f"the loop was still running {WAIT_SECONDS} s after its shutdown event was set")
        if not task.cancelled() and task.exception() is not None:
            raise task.exception()


def _return_after(activity: SignallingActivity, silence: float) -> None:
    """A request of the user after ``silence`` seconds by the activity's fake clock."""
    last = activity.last_user_request_at
    activity.clock.now = (activity.started_at if last is None else last) + silence
    with activity.request():
        pass


def _api_app() -> FastAPI:
    """One user route under the API prefix, behind ``ActivityMiddleware`` reading ``current_activity()``: the test's."""
    app = FastAPI()

    async def answer() -> PlainTextResponse:
        return PlainTextResponse("ok")

    app.add_api_route(API_ROUTE, answer, methods=["GET"])
    app.add_middleware(ActivityMiddleware)
    return app


def _client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")


# =============================================================================
# (a) NAMES AND TYPES
# =============================================================================


def test_the_header_the_reasons_the_states_and_the_process_tracker() -> None:
    """SPR-001 — contract (a): the header's name, the three catch-up reasons ("tick" is not one), the three states; ``PRICE_REFRESH`` is a tracker and ``price_refresh_progress()`` its snapshot."""
    print_section("SPR-001: PRICE_REFRESH_HEADER, CATCH_UP_REASONS, PriceRefreshState, PRICE_REFRESH")

    assert scheduler.PRICE_REFRESH_HEADER == HEADER
    assert isinstance(scheduler.CATCH_UP_REASONS, frozenset) and scheduler.CATCH_UP_REASONS == frozenset(CATCH_UP)
    assert set(get_args(getattr(scheduler.PriceRefreshState, "__value__", scheduler.PriceRefreshState))) == set(STATES)
    assert isinstance(scheduler.PRICE_REFRESH, scheduler.PriceRefreshTracker)
    assert scheduler.price_refresh_progress() == scheduler.PRICE_REFRESH.snapshot()
    scheduler.PRICE_REFRESH.announce("wake")
    assert _view(scheduler.price_refresh_progress()) == ("starting", "wake", None), "price_refresh_progress() is the process tracker's snapshot, read at the call"
    print_success("names, reasons, states; the process's tracker")


def test_the_progress_is_a_frozen_dataclass_with_the_contract_fields_in_order() -> None:
    """SPR-002 — contract (a): ``PriceRefreshProgress`` fields in the order of the contract, frozen."""
    print_section("SPR-002: PriceRefreshProgress")

    assert [field.name for field in dataclasses.fields(scheduler.PriceRefreshProgress)] == list(FIELDS)
    progress = _progress("idle")
    with pytest.raises(dataclasses.FrozenInstanceError):
        progress.state = "running"
    print_success("six fields, in order; frozen")


# =============================================================================
# (b), (c) IDLE AND ANNOUNCE
# =============================================================================


def test_a_new_tracker_is_idle_with_no_header() -> None:
    """SPR-003 — contract (b): idle, every field None, ``last_refreshed`` False; ``header_value()`` None."""
    print_section("SPR-003: a new tracker")
    tracker, _ = _tracker()

    assert _fields(tracker.snapshot()) == IDLE_NEVER
    assert tracker.header_value() is None
    print_success("idle, nothing remembered, no header")


@pytest.mark.parametrize("reason", CATCH_UP)
def test_announce_starts_a_catch_up_with_its_reason_and_the_clock(reason: str) -> None:
    """SPR-004 — contract (c): idle → "starting", the reason, ``since`` the clock's reading; no job; the header says "starting"."""
    print_section(f"SPR-004: announce({reason!r})")
    tracker, wall = _tracker()
    wall.now = T0 + timedelta(seconds=5)

    tracker.announce(reason)

    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "starting", "reason": reason, "since": T0 + timedelta(seconds=5)}
    assert tracker.header_value() == "starting"
    print_success("starting, since the clock's reading")


def test_a_second_announce_or_run_while_pending_keeps_the_first_reason_and_since() -> None:
    """SPR-005 — contract (c), (d): "startup" announced at T0; "return" announced and a "wake" run started later: still "startup", since T0."""
    print_section("SPR-005: the first reason and since are kept")
    tracker, wall = _tracker()
    tracker.announce("startup")

    wall.now = T0 + timedelta(seconds=30)
    tracker.announce("return")
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "starting", "reason": "startup", "since": T0}

    wall.now = T0 + timedelta(seconds=60)
    tracker.run_started("wake")
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "starting", "reason": "startup", "since": T0}
    print_success("first reason, first since")


@pytest.mark.parametrize("reason", ["tick", "unknown", "", "Return"], ids=["tick", "unknown", "empty", "another-case"])
def test_a_reason_that_is_not_a_catch_up_is_refused_and_nothing_is_counted(reason: str) -> None:
    """SPR-006 — contract (c): ``announce`` and ``run_started`` raise ``ValueError``; the tracker stays idle, and the refused run is not counted — one ``run_started``…``run_finished`` pair after it ends the catch-up."""
    print_section(f"SPR-006: announce / run_started({reason!r})")
    tracker, _ = _tracker()

    with pytest.raises(ValueError):
        tracker.announce(reason)
    with pytest.raises(ValueError):
        tracker.run_started(reason)

    assert _fields(tracker.snapshot()) == IDLE_NEVER
    assert tracker.header_value() is None
    tracker.run_started("return")
    tracker.run_finished()
    assert tracker.snapshot().state == "idle", "the refused run_started must not have been counted: one pair after it ends the catch-up"
    print_success("ValueError; nothing counted")


# =============================================================================
# (d) RUNS
# =============================================================================


def test_a_catch_up_run_without_a_job_starts_and_ends_and_remembers_nothing() -> None:
    """SPR-007 — contract (d): ``run_started("return")`` from idle → "starting", since the clock; ``run_finished()`` → idle; no job finished, so ``last_finished_at`` stays None and ``last_refreshed`` False."""
    print_section("SPR-007: a run with no job")
    tracker, wall = _tracker()

    tracker.run_started("return")
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "starting", "reason": "return", "since": T0}
    wall.now = T0 + timedelta(seconds=3)
    tracker.run_finished()

    assert _fields(tracker.snapshot()) == IDLE_NEVER
    assert tracker.header_value() is None
    print_success("starting, then idle; nothing remembered")


def test_a_catch_up_with_a_job_that_updated_items_is_refreshed() -> None:
    """SPR-008 — contract (d), (e), (f): a job started → "running" with its name and the header "running"; finished with 3 items → "starting", no job; the run ends at T0+9 s → idle, ``last_finished_at`` T0+9 s, ``last_refreshed`` True."""
    print_section("SPR-008: a refreshed catch-up")
    tracker, wall = _tracker()
    tracker.run_started("wake")

    tracker.job_started("current_price")
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "running", "reason": "wake", "job": "current_price", "since": T0}
    assert tracker.header_value() == "running"

    tracker.job_finished(3)
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "starting", "reason": "wake", "since": T0}
    assert tracker.header_value() == "starting"

    wall.now = T0 + timedelta(seconds=9)
    tracker.run_finished()
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "last_finished_at": T0 + timedelta(seconds=9), "last_refreshed": True}
    assert tracker.header_value() is None
    print_success("running, starting, idle and refreshed")


@pytest.mark.parametrize(("items", "refreshed"), [([0], False), ([None], False), ([0, 5], True), ([5, None], True), ([0, 0], False), ([None, 0], False)], ids=["nothing-updated", "cancelled", "the-second-updated", "the-first-updated-then-a-cancel", "two-without-updates", "cancel-and-nothing"])
def test_last_refreshed_is_whether_one_job_of_the_catch_up_updated_items(items: list[int | None], refreshed: bool) -> None:
    """SPR-009 — contract (d), (e): each job of the catch-up finished with ``items``; at the end ``last_finished_at`` is the clock — every job ran, a cancelled one too — and ``last_refreshed`` is whether one had ``items_ok > 0``."""
    print_section(f"SPR-009: jobs finished with {items}")
    tracker, wall = _tracker()
    tracker.run_started("startup")
    for index, value in enumerate(items):
        tracker.job_started(JOBS[index % 2])
        tracker.job_finished(value)

    wall.now = T0 + timedelta(minutes=2)
    tracker.run_finished()

    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "last_finished_at": T0 + timedelta(minutes=2), "last_refreshed": refreshed}
    print_success(f"ran; refreshed={refreshed}")


def test_a_catch_up_where_no_job_ran_keeps_the_previous_result_and_one_that_ran_replaces_it() -> None:
    """SPR-010 — contract (d): a refreshed catch-up ends at T1; a second one with no job keeps T1 and True; a third whose job updated nothing ends at T3 with False."""
    print_section("SPR-010: the previous result kept, then replaced")
    tracker, wall = _tracker()
    tracker.run_started("startup")
    tracker.job_started("current_price")
    tracker.job_finished(4)
    t1 = T0 + timedelta(seconds=10)
    wall.now = t1
    tracker.run_finished()

    wall.now = T0 + timedelta(minutes=5)
    tracker.announce("return")
    tracker.run_started("return")
    wall.now = T0 + timedelta(minutes=6)
    tracker.run_finished()
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "last_finished_at": t1, "last_refreshed": True}

    tracker.run_started("wake")
    tracker.job_started("history_sync")
    tracker.job_finished(0)
    t3 = T0 + timedelta(minutes=9)
    wall.now = t3
    tracker.run_finished()
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "last_finished_at": t3, "last_refreshed": False}
    print_success("kept when nothing ran; replaced when a job ran")


def test_overlapping_runs_end_the_catch_up_only_with_the_last() -> None:
    """SPR-011 — contract (d): a "wake" run, then a "return" run while it runs: the reason stays "wake"; the first ``run_finished`` leaves it pending, the second ends it."""
    print_section("SPR-011: overlapping runs")
    tracker, _ = _tracker()
    tracker.run_started("wake")
    tracker.run_started("return")

    tracker.job_started("current_price")
    tracker.job_finished(1)
    tracker.run_finished()
    assert _view(tracker.snapshot()) == ("starting", "wake", None), "one run is still counted: the catch-up is still pending"

    tracker.run_finished()
    assert tracker.snapshot().state == "idle"
    assert tracker.snapshot().last_refreshed is True
    print_success("pending until the last run ends")


def test_run_finished_without_a_counted_run_is_a_no_op_never_negative() -> None:
    """SPR-012 — contract (d): two ``run_finished()`` while idle change nothing; an ``announce`` then a ``run_finished()`` with no run counted leaves it pending; the next ``run_started``…``run_finished`` pair ends it."""
    print_section("SPR-012: run_finished with no counted run")
    tracker, _ = _tracker()
    tracker.run_finished()
    tracker.run_finished()
    assert _fields(tracker.snapshot()) == IDLE_NEVER

    tracker.announce("return")
    tracker.run_finished()
    assert _view(tracker.snapshot()) == ("starting", "return", None), "no run counted: run_finished is a no-op, the announce stays pending"

    tracker.run_started("return")
    tracker.run_finished()
    assert tracker.snapshot().state == "idle", "the count never went negative: one pair ends the catch-up"
    print_success("no-op; an announce ended by the next pair")


def test_an_announce_then_its_run_keeps_the_announce_since() -> None:
    """SPR-013 — contract (c), (d): "startup" announced at T0, its run started at T0+5 s: ``since`` stays T0; the run's end at T0+7 s ends the catch-up."""
    print_section("SPR-013: announce, then the run")
    tracker, wall = _tracker()
    tracker.announce("startup")
    wall.now = T0 + timedelta(seconds=5)

    tracker.run_started("startup")
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "starting", "reason": "startup", "since": T0}

    wall.now = T0 + timedelta(seconds=7)
    tracker.run_finished()
    assert _fields(tracker.snapshot()) == IDLE_NEVER
    print_success("since of the announce; ended by the run")


# =============================================================================
# (e), (f) JOBS AND STATES
# =============================================================================


def test_a_job_while_idle_changes_nothing_visible() -> None:
    """SPR-014 — contract (e), (f): a tick's job started and finished with 5 items while idle: idle throughout, no job shown; a catch-up after it with no job of its own remembers nothing."""
    print_section("SPR-014: a tick's job")
    tracker, _ = _tracker()

    tracker.job_started("current_price")
    assert _fields(tracker.snapshot()) == IDLE_NEVER
    assert tracker.header_value() is None
    tracker.job_finished(5)
    assert _fields(tracker.snapshot()) == IDLE_NEVER

    tracker.run_started("return")
    tracker.run_finished()
    assert _fields(tracker.snapshot()) == IDLE_NEVER, "the tick's job finished while idle: it is no part of the catch-up"
    print_success("idle; not counted")


def test_a_tick_job_running_when_a_return_is_announced_shows_running_at_once_and_counts() -> None:
    """SPR-015 — contract (e), (f): a tick's job running, then "return" announced → "running" at once with that job; it finishes with 2 items while pending: the catch-up's run, with no job of its own, ends refreshed."""
    print_section("SPR-015: a tick's job during an announced return")
    tracker, wall = _tracker()
    tracker.job_started("history_sync")

    tracker.announce("return")
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "state": "running", "reason": "return", "job": "history_sync", "since": T0}
    assert tracker.header_value() == "running"

    tracker.job_finished(2)
    assert _view(tracker.snapshot()) == ("starting", "return", None)
    tracker.run_started("return")
    wall.now = T0 + timedelta(seconds=4)
    tracker.run_finished()
    assert _fields(tracker.snapshot()) == {**IDLE_NEVER, "last_finished_at": T0 + timedelta(seconds=4), "last_refreshed": True}
    print_success("running at once; counted")


def test_the_current_job_is_the_last_started_and_not_yet_finished() -> None:
    """SPR-016 — contract (e), (f): ``current_price`` runs and finishes, then ``history_sync`` starts: "running" with ``history_sync``; finished: "starting", no job."""
    print_section("SPR-016: the current job")
    tracker, _ = _tracker()
    tracker.run_started("startup")

    tracker.job_started("current_price")
    tracker.job_finished(0)
    tracker.job_started("history_sync")
    assert _view(tracker.snapshot()) == ("running", "startup", "history_sync")
    tracker.job_finished(0)
    assert _view(tracker.snapshot()) == ("starting", "startup", None)
    print_success("the last started; none once finished")


def test_reset_forgets_everything_the_run_count_and_the_current_job_included() -> None:
    """SPR-017 — contract (f): from a refreshed catch-up remembered, two runs counted and a job running, ``reset()`` gives (b); an ``announce`` then shows "starting" (no job), and one ``run_started``…``run_finished`` pair ends it."""
    print_section("SPR-017: reset()")
    tracker, _ = _tracker()
    tracker.run_started("startup")
    tracker.job_started("current_price")
    tracker.job_finished(7)
    tracker.run_finished()
    tracker.run_started("return")
    tracker.run_started("wake")
    tracker.job_started("history_sync")
    assert tracker.snapshot().state == "running"

    tracker.reset()
    assert _fields(tracker.snapshot()) == IDLE_NEVER
    assert tracker.header_value() is None

    tracker.announce("return")
    assert _view(tracker.snapshot()) == ("starting", "return", None), "the current job must be forgotten by reset()"
    tracker.run_started("return")
    tracker.run_finished()
    assert tracker.snapshot().state == "idle", "the run count must be forgotten by reset()"
    print_success("back to a new tracker")


def test_the_default_clock_is_the_wall_clock_in_utc() -> None:
    """SPR-018 — contract (c), (d): a tracker without ``clock`` stamps ``since`` and ``last_finished_at`` with aware UTC datetimes of the wall clock."""
    print_section("SPR-018: the default clock")
    tracker = scheduler.PriceRefreshTracker()

    before = datetime.now(UTC)
    tracker.run_started("wake")
    tracker.job_started("current_price")
    tracker.job_finished(1)
    since = tracker.snapshot().since
    tracker.run_finished()
    after = datetime.now(UTC)

    finished = tracker.snapshot().last_finished_at
    _assert_utc(since, "since")
    _assert_utc(finished, "last_finished_at")
    assert before <= since <= finished <= after
    print_success("aware UTC, the wall clock")


# =============================================================================
# (g) THE WIRING OF run_due_jobs
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", CATCH_UP)
async def test_a_catch_up_run_shows_starting_then_each_job_running_then_idle_refreshed(reason: str, fakes: Fakes) -> None:
    """SPR-019 — contract (g): ``run_due_jobs(reason)`` for a catch-up: "starting" during the settle (return, wake), "running" with each job's name inside the job, the header saying so; idle at the end, ``last_refreshed`` True (``current_price`` updated 3), ``last_finished_at`` aware UTC."""
    print_section(f"SPR-019: run_due_jobs({reason!r})")

    await _within(scheduler.run_due_jobs(reason), f"run_due_jobs({reason!r})")

    settles = fakes.at("settle")
    if reason in SETTLING:
        assert [(_view(snapshot), header) for snapshot, header in settles] == [(("starting", reason, None), "starting")], "run_started must come before the clock settle"
    else:
        assert settles == []
    for job in JOBS:
        assert [(_view(snapshot), header) for snapshot, header in fakes.at(f"job:{job}")] == [(("running", reason, job), "running")]
    after = scheduler.PRICE_REFRESH.snapshot()
    assert _view(after) == ("idle", None, None) and after.since is None
    assert after.last_refreshed is True
    _assert_utc(after.last_finished_at, "last_finished_at")
    assert scheduler.PRICE_REFRESH.header_value() is None
    print_success("starting, running per job, idle and refreshed")


@pytest.mark.asyncio
async def test_a_tick_run_is_never_shown_and_remembers_nothing(fakes: Fakes) -> None:
    """SPR-020 — contract (g), N-Z5-1: ``run_due_jobs("tick")`` with both jobs updating items: idle and no header inside each job; nothing remembered after."""
    print_section("SPR-020: run_due_jobs('tick')")
    fakes.items_ok = {"current_price": 4, "history_sync": 6}

    await _within(scheduler.run_due_jobs("tick"), "run_due_jobs('tick')")

    for job in JOBS:
        assert [(_view(snapshot), header) for snapshot, header in fakes.at(f"job:{job}")] == [(("idle", None, None), None)]
    assert _fields(scheduler.PRICE_REFRESH.snapshot()) == IDLE_NEVER
    print_success("a tick is not a catch-up")


@pytest.mark.asyncio
async def test_an_unknown_reason_is_refused_before_the_tracker_counts_anything(fakes: Fakes) -> None:
    """SPR-032 — contract (g): ``run_due_jobs("nap")`` raises ``ValueError`` and the tracker stays idle; one catch-up run after it ends idle, so nothing was counted."""
    print_section("SPR-032: run_due_jobs('nap')")

    with pytest.raises(ValueError):
        await _within(scheduler.run_due_jobs("nap"), "run_due_jobs('nap')")

    assert _fields(scheduler.PRICE_REFRESH.snapshot()) == IDLE_NEVER
    fakes.due = set()
    await _within(scheduler.run_due_jobs("wake"), "run_due_jobs('wake')")
    assert _fields(scheduler.PRICE_REFRESH.snapshot()) == IDLE_NEVER
    print_success("refused; nothing counted")


@pytest.mark.asyncio
async def test_a_catch_up_whose_jobs_updated_nothing_or_where_nothing_was_due(fakes: Fakes) -> None:
    """SPR-021 — contract (d), (g): a "startup" run whose jobs updated nothing ends not refreshed, with ``last_finished_at``; a "return" run where nothing is due keeps that result."""
    print_section("SPR-021: nothing updated, then nothing due")
    fakes.items_ok = {"current_price": 0, "history_sync": 0}

    await _within(scheduler.run_due_jobs("startup"), "run_due_jobs('startup')")
    first = scheduler.PRICE_REFRESH.snapshot()
    assert first.state == "idle" and first.last_refreshed is False
    _assert_utc(first.last_finished_at, "last_finished_at")

    fakes.due = set()
    await _within(scheduler.run_due_jobs("return"), "run_due_jobs('return')")
    assert _fields(scheduler.PRICE_REFRESH.snapshot()) == {**IDLE_NEVER, "last_finished_at": first.last_finished_at, "last_refreshed": False}
    print_success("ran, not refreshed; then kept")


@pytest.mark.asyncio
async def test_a_job_that_raises_finishes_with_no_items_and_the_next_job_counts(fakes: Fakes) -> None:
    """SPR-022 — contract (e), (g): ``current_price`` raises (its outcome has 0 items), ``history_sync`` updates 2: the run ends idle, refreshed; with ``history_sync`` at 0 instead, not refreshed."""
    print_section("SPR-022: a job that raises")
    fakes.failures["current_price"] = ProviderExploded("provoked")
    fakes.items_ok = {"current_price": 9, "history_sync": 2}

    await _within(scheduler.run_due_jobs("wake"), "run_due_jobs('wake')")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("idle", None, None)
    assert scheduler.PRICE_REFRESH.snapshot().last_refreshed is True
    assert [_view(snapshot) for snapshot, _ in fakes.at("job:history_sync")] == [("running", "wake", "history_sync")], "the job that raised must not stay current"

    fakes.stored = SchedulerState()
    fakes.items_ok = {"current_price": 9, "history_sync": 0}
    await _within(scheduler.run_due_jobs("wake"), "run_due_jobs('wake') again")
    assert scheduler.PRICE_REFRESH.snapshot().last_refreshed is False, "a job that raised updated nothing, whatever it would have written"
    print_success("raised: ran, not refreshed")


@pytest.mark.asyncio
async def test_a_catch_up_run_that_raises_still_ends_the_catch_up(fakes: Fakes) -> None:
    """SPR-023 — contract (g): the settings raise inside a "return" run: the exception goes through, and the catch-up is over — idle, no header."""
    print_section("SPR-023: a run that raises")
    fakes.settings_failure = ProviderExploded("provoked: settings")

    with pytest.raises(ProviderExploded):
        await _within(scheduler.run_due_jobs("return"), "run_due_jobs('return')")

    assert _fields(scheduler.PRICE_REFRESH.snapshot()) == IDLE_NEVER
    assert scheduler.PRICE_REFRESH.header_value() is None
    print_success("finally: run_finished")


@pytest.mark.asyncio
async def test_a_cancelled_catch_up_ends_with_its_job_ran_and_not_refreshed(fakes: Fakes) -> None:
    """SPR-024 — contract (e), (g): a "wake" run cancelled while ``current_price`` runs: the task ends cancelled; the tracker is idle, no job current, the catch-up ran (``last_finished_at`` set) and is not refreshed."""
    print_section("SPR-024: a cancelled catch-up")
    entered, release = asyncio.Event(), asyncio.Event()
    fakes.job_gates["current_price"] = (entered, release)
    task = asyncio.create_task(scheduler.run_due_jobs("wake"))
    await _within(entered.wait(), "current_price entered")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("running", "wake", "current_price")

    task.cancel()
    await asyncio.wait({task}, timeout=WAIT_SECONDS)
    assert task.cancelled()

    after = scheduler.PRICE_REFRESH.snapshot()
    assert _view(after) == ("idle", None, None)
    assert after.last_refreshed is False
    _assert_utc(after.last_finished_at, "last_finished_at")
    print_success("cancelled: idle, ran, not refreshed")


@pytest.mark.asyncio
async def test_a_cancelled_tick_leaves_no_current_job_behind(fakes: Fakes) -> None:
    """SPR-025 — contract (e), (g): a "tick" run cancelled inside ``current_price``; a return announced after it shows "starting", not a job that no longer runs."""
    print_section("SPR-025: a cancelled tick")
    entered, release = asyncio.Event(), asyncio.Event()
    fakes.job_gates["current_price"] = (entered, release)
    task = asyncio.create_task(scheduler.run_due_jobs("tick"))
    await _within(entered.wait(), "current_price entered")

    task.cancel()
    await asyncio.wait({task}, timeout=WAIT_SECONDS)
    assert task.cancelled()

    scheduler.PRICE_REFRESH.announce("return")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("starting", "return", None), "job_finished(None) must run when a job is cancelled"
    print_success("no ghost job")


@pytest.mark.asyncio
async def test_a_tick_job_running_when_a_return_is_announced_then_the_return_run(fakes: Fakes) -> None:
    """SPR-026 — contract (e), (f), (g): a tick's ``current_price`` held running; "return" announced → "running" with it; the tick ends (3 items) → "starting"; the return run, nothing due, ends the catch-up refreshed."""
    print_section("SPR-026: a return during a tick")
    fakes.due = {"current_price"}
    entered, release = asyncio.Event(), asyncio.Event()
    fakes.job_gates["current_price"] = (entered, release)
    tick = asyncio.create_task(scheduler.run_due_jobs("tick"))
    await _within(entered.wait(), "current_price entered")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("idle", None, None)

    scheduler.PRICE_REFRESH.announce("return")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("running", "return", "current_price")

    release.set()
    await _within(tick, "the tick run")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("starting", "return", None)

    fakes.due = set()
    await _within(scheduler.run_due_jobs("return"), "run_due_jobs('return')")
    after = scheduler.PRICE_REFRESH.snapshot()
    assert _view(after) == ("idle", None, None) and after.last_refreshed is True
    print_success("running at once; refreshed by the tick's job")


@pytest.mark.asyncio
async def test_a_wake_while_a_return_runs_keeps_the_catch_up_pending_until_both_end(fakes: Fakes) -> None:
    """SPR-027 — contract (d), (g): a "return" run holds ``current_price``; a "wake" run enters its settle; the return ends → still "starting" for "return" (the wake is counted, before its settle); the wake ends → idle."""
    print_section("SPR-027: overlapping catch-up runs")
    fakes.due = {"current_price"}
    entered, release = asyncio.Event(), asyncio.Event()
    fakes.job_gates["current_price"] = (entered, release)
    returning = asyncio.create_task(scheduler.run_due_jobs("return"))
    await _within(entered.wait(), "current_price entered")

    fakes.settle_entered.clear()
    fakes.settle_gate = asyncio.Event()
    waking = asyncio.create_task(scheduler.run_due_jobs("wake"))
    await _within(fakes.settle_entered.wait(), "the wake run's settle")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("running", "return", "current_price")

    release.set()
    await _within(returning, "the return run")
    assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("starting", "return", None), "the wake run is still counted"

    fakes.due = set()
    fakes.settle_gate.set()
    await _within(waking, "the wake run")
    after = scheduler.PRICE_REFRESH.snapshot()
    assert _view(after) == ("idle", None, None) and after.last_refreshed is True
    print_success("pending until the last run ends")


# =============================================================================
# (h) THE WIRING OF scheduler_loop
# =============================================================================


@pytest.mark.asyncio
async def test_the_loop_announces_startup_and_publishes_the_header_then_removes_it_and_resets(monkeypatch: pytest.MonkeyPatch, activity: SignallingActivity, fakes: Fakes) -> None:
    """SPR-028 — contract (h): the first run an hour away: once the loop has started, "starting" for "startup" and the activity's headers give the price header "starting"; a result remembered meanwhile; the shutdown removes the header and resets ``PRICE_REFRESH``."""
    print_section("SPR-028: the loop's start and end")
    monkeypatch.setattr(scheduler, "FIRST_RUN_DELAY_SECONDS", 3_600.0)
    monkeypatch.setattr(scheduler, "TICK_SECONDS", 3_600.0)
    shutdown = asyncio.Event()

    async with _looping(shutdown) as loop_task:
        await _within(activity.header_registered.wait(), "the loop registered its response header", loop_task=loop_task)
        assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("starting", "startup", None)
        assert _header_of(activity) == ["starting"]
        scheduler.PRICE_REFRESH.run_started("startup")
        scheduler.PRICE_REFRESH.job_started("current_price")
        scheduler.PRICE_REFRESH.job_finished(2)
        scheduler.PRICE_REFRESH.run_finished()
        assert scheduler.PRICE_REFRESH.snapshot().last_refreshed is True
        assert _header_of(activity) == [], "idle: the provider answers None, and no header is given"

    assert _header_of(activity) == [], "the loop's end must remove its header"
    assert _fields(scheduler.PRICE_REFRESH.snapshot()) == IDLE_NEVER, "the loop's end must reset PRICE_REFRESH"
    print_success("announced, published; removed and reset")


@pytest.mark.asyncio
async def test_a_disabled_loop_announces_nothing_and_registers_no_header(monkeypatch: pytest.MonkeyPatch, activity: SignallingActivity) -> None:
    """SPR-029 — contract (h): under ``scheduler_disabled()`` the loop returns at once: idle, no header."""
    print_section("SPR-029: a disabled loop")
    monkeypatch.setattr(scheduler, "scheduler_disabled", lambda: True)

    await _within(scheduler.scheduler_loop(asyncio.Event()), "the disabled loop")

    assert _fields(scheduler.PRICE_REFRESH.snapshot()) == IDLE_NEVER
    assert not activity.header_registered.is_set()
    assert _header_of(activity) == []
    print_success("nothing")


@pytest.mark.asyncio
async def test_the_startup_run_then_a_return_announced_on_the_request_then_its_run(activity: SignallingActivity, fakes: Fakes, runs: Runs) -> None:
    """SPR-030 — contract (g), (h): the "startup" run shows ``current_price`` running and ends idle, refreshed; a user request after 600 s of silence leaves "starting" for "return" as it returns, before the loop runs again; the "return" run ends it."""
    print_section("SPR-030: startup, then a return")
    shutdown = asyncio.Event()

    async with _looping(shutdown) as loop_task:
        await runs.wait_ended(1, loop_task)
        assert runs.reasons == ["startup"]
        assert [_view(snapshot) for snapshot, _ in fakes.at("job:current_price")] == [("running", "startup", "current_price")]
        assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("idle", None, None)
        assert scheduler.PRICE_REFRESH.snapshot().last_refreshed is True

        fakes.due = set()
        _return_after(activity, LONG_SILENCE)
        assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("starting", "return", None), "the return listener announces the return on the request's own thread"
        assert _header_of(activity) == ["starting"]

        await runs.wait_ended(2, loop_task)
        assert runs.reasons == ["startup", "return"]
        assert _view(scheduler.PRICE_REFRESH.snapshot()) == ("idle", None, None)
    print_success("startup run; return announced at once; return run")


@pytest.mark.asyncio
async def test_the_first_answer_after_a_silence_says_starting_and_one_during_a_job_says_running(activity: SignallingActivity, fakes: Fakes, runs: Runs) -> None:
    """SPR-031 — contract (h) through ``ActivityMiddleware``: after the startup run, an API request after 600 s of silence gets ``x-librefolio-price-refresh: starting`` on its own answer (the return run held in its settle); while the return run's job runs, another answer says "running"; once it ended, no header."""
    print_section("SPR-031: the header on the answers")
    shutdown = asyncio.Event()
    app = _api_app()

    async with _looping(shutdown) as loop_task, _client(app) as client:
        await runs.wait_ended(1, loop_task)
        quiet = await client.get(API_ROUTE)
        assert quiet.status_code == 200 and "x-librefolio-price-refresh" not in quiet.headers, f"idle: no header, got {dict(quiet.headers)}"

        fakes.stored = SchedulerState()
        fakes.due = {"current_price"}
        entered, release = asyncio.Event(), asyncio.Event()
        fakes.job_gates["current_price"] = (entered, release)
        fakes.settle_entered.clear()
        fakes.settle_gate = asyncio.Event()
        activity.clock.now = activity.last_user_request_at + LONG_SILENCE
        first = await client.get(API_ROUTE)
        assert first.headers.get("x-librefolio-price-refresh") == "starting", f"the first answer after a silence: {dict(first.headers)}"

        await _within(fakes.settle_entered.wait(), "the return run's settle", loop_task=loop_task)
        fakes.settle_gate.set()
        await _within(entered.wait(), "current_price entered", loop_task=loop_task)
        during = await client.get(API_ROUTE)
        assert during.headers.get("x-librefolio-price-refresh") == "running", f"an answer while the job runs: {dict(during.headers)}"

        release.set()
        await runs.wait_ended(2, loop_task)
        after = await client.get(API_ROUTE)
        assert "x-librefolio-price-refresh" not in after.headers, f"after the catch-up: {dict(after.headers)}"
    print_success("starting, running, nothing")
