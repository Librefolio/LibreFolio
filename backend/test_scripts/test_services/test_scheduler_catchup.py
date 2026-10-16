"""``backend.app.services.platform.scheduler.scheduler``: the scheduler's catch-up on return and its shared lock (plan
phase01SleepWake §Z3, decisions D-Z3-1…D-Z3-4, lot Z3).

``run_due_jobs(reason)`` is the one way in to the two market-data jobs: the loop goes through it at startup and at each
tick, the return listener nudges the loop through it when the user comes back after a silence, and ``wake-sync`` (lot Z4)
will go through it on a scheduled wake-up. The contract pinned here:

(a) The module's constants, read at call time so a test can set them: ``CATCH_UP_AFTER_SECONDS`` 60.0,
    ``CLOCK_SETTLE_SECONDS`` 2.0, ``TICK_SECONDS`` 60.0, ``FIRST_RUN_DELAY_SECONDS`` 5.0, ``MISSED_SLOT_LOOKBACK_DAYS`` 7,
    ``CATCH_UP_LISTENER`` "scheduler-catch-up", ``BUSY_REASON`` "scheduler", ``JOB_NAMES`` ("current_price",
    "history_sync"). A ``RunReason`` is "startup", "tick", "return" or "wake".
(b) ``JobOutcome(name, status, started_at=None, duration_s=None, items_ok=0, items_err=0, error=None)`` and
    ``RunReport(reason, status, started_at, finished_at, jobs=())`` are frozen dataclasses with these fields, in this
    order. ``utc_now()`` reads the wall clock, an aware datetime in UTC; ``settle_clock()`` is a coroutine that waits
    ``CLOCK_SETTLE_SECONDS``, read at the call.
(c) ``run_due_jobs(reason)``: an unknown reason is a ``ValueError`` before anything happens — no busy span, no
    collaborator called.
(d) The whole call runs inside ``current_activity().busy(BUSY_REASON)``: "scheduler" is listed from the start — during
    the settle, and while the run waits for the lock — to the end, and no longer after, whether the run returns, raises
    or is cancelled.
(e) "return" and "wake" first await ``settle_clock()``, "startup" and "tick" never. The settle comes before the clock is
    read for the due checks, so a wall clock corrected during the settle — Fly after a resume — is the one the due
    functions see; and before the lock, so a run settles while another one holds it.
(f) Then one ``asyncio.Lock`` per event loop: two runs in one loop never overlap — the second goes past the lock once
    the first is done, and loads the state the first saved —; two successive event loops, each with two runs
    contending, both work.
(g) Under the lock, in this order, each answer short-circuiting with ``jobs == ()``, without loading the state or running
    a job, whatever the reason: ``scheduler_disabled()`` → "disabled", ``instance_blocked()`` → "blocked", not
    ``am_i_leader()`` → "not_leader", ``load_scheduler_settings()`` with ``scheduler_enabled`` false → "disabled".
(h) ``am_i_leader``, ``load_state`` and ``save_state`` run off the event loop's thread.
(i) Otherwise ``load_state()``, then one ``now = utc_now()`` given to both due functions with the settings and the
    loaded state, then the jobs, ``current_price`` then ``history_sync``. One not due is ``JobOutcome(name, "not_due")``;
    one due is awaited on that state — ``run_history_sync`` with ``horizon_days=settings.history_sync_horizon_days`` —,
    then the state is saved; its outcome copies the ``JobState`` the job wrote — status ``last_status`` ("ok" when
    None), ``duration_s``, items, error — with ``started_at`` from ``utc_now()``, in UTC.
(j) A job raising an ``Exception``, or ``save_state`` raising after it: outcome "error", ``error`` the exception's class
    name and never its message, ``duration_s`` a float ≥ 0, logged — ERROR, "Scheduler job failed", ``job=<name>``
    —; the next job still runs, and the report is made.
(k) A cancellation goes through: the run ends cancelled, "scheduler" is no longer listed, the lock is free.
(l) ``RunReport``: ``reason`` echoed, ``started_at <= finished_at``, aware UTC datetimes, ``jobs`` both outcomes in
    order once the run reached them. ``status`` "ok" when no job ran or every job that ran is "ok", "error" when every
    job that ran is "error", "partial" otherwise.
(m) D-Z3-4 with D-Z3-1: a blocked instance runs nothing and leaves the state as it was; unblocked, its first run catches
    up the history slot it missed, on a day that is not configured.
(n) ``scheduler_loop(shutdown_event)``: under ``scheduler_disabled()`` it returns at once and registers nothing. Else it
    registers the return listener ``CATCH_UP_LISTENER`` at ``CATCH_UP_AFTER_SECONDS`` on ``current_activity()``, runs
    "startup" after ``FIRST_RUN_DELAY_SECONDS`` or earlier on a nudge — no run if the shutdown comes first —, then waits
    ``TICK_SECONDS``, a nudge or the shutdown: "tick" on the timeout, "return" on a nudge. A user request after at least
    ``CATCH_UP_AFTER_SECONDS`` of silence nudges it, from any thread; one after less does not. The nudge is cleared as a
    run starts: two nudges during a run make one run after it. A run that raises is logged — ERROR, "Scheduler run
    failed" — and the loop goes on. The shutdown ends it promptly, with no further run, and removes the listener.

Pure: no database, no server, no lane port, no network. Every collaborator of ``run_due_jobs`` is a fake set on the module
with ``monkeypatch``: the switches, the leader, the settings, a state store in memory, the two jobs, the due functions —
due when the state says the job never ran; the real ones serve only in (m) —, ``utc_now`` on a fake wall clock and
``settle_clock`` as a recorder. Each test has its own ``Activity`` on a fake clock in place of the process's
``ACTIVITY``; it also counts the busy spans open per reason and records the return listeners and their calls. The loop
tests put a recorder in place of ``run_due_jobs``, with ``FIRST_RUN_DELAY_SECONDS`` 0 and ``TICK_SECONDS`` 3600 — 0.05
where a tick is the event awaited, the marker that the loop went back to waiting —, and wait for a run on an event with a
bounded timeout. Nothing sleeps, and no assertion depends on a duration: the one bound of (b) is a timer of the loop,
which never fires before the callbacks already due. The log is read with ``structlog.testing.capture_logs`` behind a
barrier: a canary logged through each module's own ``logger`` must reach the capture.

Red until the code of Z3 exists: the new names are missing from the module, an ``AttributeError`` where a test or a
fixture sets or reads one; then the loop's exit needs ``Activity.remove_return_listener``.
"""

from __future__ import annotations

import asyncio
import copy
import dataclasses
import inspect
import threading
from collections import Counter, defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import AbstractContextManager, asynccontextmanager, contextmanager
from datetime import UTC, datetime, time, timedelta
from typing import Any, get_args
from zoneinfo import ZoneInfo

import pytest
from structlog.testing import capture_logs

from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import JobState, SchedulerState
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.services.platform.sleep_wake.activity import Activity
from backend.test_scripts.test_utils import print_section, print_success

REASONS = ("startup", "tick", "return", "wake")
SETTLING_REASONS = ("return", "wake")
JOBS = ("current_price", "history_sync")
#: The literals of the contract, never read from the module under test.
SCHEDULER_REASON = "scheduler"
LISTENER_NAME = "scheduler-catch-up"
CATCH_UP_AFTER = 60.0
JOB_FAILED = "Scheduler job failed"
RUN_FAILED = "Scheduler run failed"
LISTENER_FAILED = "Return listener failed"
SCHEDULER_CANARY = "scheduler catch-up test: canary through the scheduler's logger"
ACTIVITY_CANARY = "scheduler catch-up test: canary through the activity's logger"

#: The longest a test waits for anything: a run, a task, a thread.
WAIT_SECONDS = 30.0
#: The wall clock of the run tests, which moves only when a test or the settle recorder moves it: Monday 2026-06-08.
WALL_START = datetime(2026, 6, 8, 10, 0, tzinfo=UTC)
#: What the settle recorder moves the wall clock by, where a test asks it to: Fly correcting the clock after a resume.
CLOCK_CORRECTION = timedelta(minutes=90)
#: The activity's fake clock, in seconds, and a silence well past the catch-up threshold.
START = 1_000.0
LONG_SILENCE = 600.0
#: Distinctive, so that a run passing the default 14 instead shows.
HORIZON_DAYS = 21
#: In the message of every failure provoked here: it must never reach a report.
SECRET = "token=SECRET"
ROME = ZoneInfo("Europe/Rome")
#: What a fake job writes into its ``JobState`` when it runs, besides ``last_run_at``: distinctive values, so that an
#: outcome copying them shows it.
WRITTEN: dict[str, dict[str, Any]] = {
    "current_price": {"last_duration_s": 1.25, "last_status": "ok", "last_items_ok": 7, "last_items_err": 0, "last_error": None},
    "history_sync": {"last_duration_s": 3.5, "last_status": "ok", "last_items_ok": 40, "last_items_err": 0, "last_error": None},
}
#: What ``dataclasses.fields`` shows for a field without a default.
REQUIRED = "<required>"
#: ``horizon_days`` when the run does not pass it.
NOT_GIVEN = "<not given>"

#: The real due functions, read before any test replaces them: (m) runs on them.
REAL_DUE_CURRENT_PRICE = scheduler.due_current_price
REAL_DUE_HISTORY_SYNC = scheduler.due_history_sync


class ProviderExploded(Exception):
    """A job's failure, named so that its class is recognisable in an outcome."""


# =============================================================================
# FAKES
# =============================================================================


class FakeClock:
    """The activity's clock: it moves only when the test sets it, ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class WallClock:
    """``utc_now()`` for the run under test: an aware UTC datetime that moves only when the test or the settle recorder moves it; with a ``step``, each reading moves it on by the step after answering."""

    def __init__(self, start: datetime = WALL_START) -> None:
        self.now = start
        self.step: timedelta | None = None
        self.readings: list[datetime] = []

    def __call__(self) -> datetime:
        reading = self.now
        self.readings.append(reading)
        if self.step is not None:
            self.now = reading + self.step
        return reading


class RecordingActivity(Activity):
    """The test's ``Activity`` on a fake clock, which also counts the busy spans open per reason and records the return listeners registered and every call to them.

    Two runs inside ``busy("scheduler")`` list the reason once: the count tells them apart. Each listener registered is
    wrapped, so that a call to it is recorded — name, silence, thread — before its callback runs.
    """

    def __init__(self, clock: FakeClock) -> None:
        super().__init__(clock=clock)
        self.clock = clock
        self._counts = threading.Lock()
        self.open_spans: Counter[str] = Counter()
        self.spans_opened: list[str] = []
        self.registrations: list[tuple[str, float]] = []
        self.listener_calls: list[tuple[str, float, int]] = []
        #: Set at each registration, on the loop that registers: a loop test waits on it.
        self.registered = asyncio.Event()

    def busy(self, reason: str) -> AbstractContextManager[None]:
        return self._counted(reason, super().busy(reason))

    @contextmanager
    def _counted(self, reason: str, span: AbstractContextManager[None]) -> Iterator[None]:
        with span:
            with self._counts:
                self.open_spans[reason] += 1
                self.spans_opened.append(reason)
            try:
                yield
            finally:
                with self._counts:
                    self.open_spans[reason] -= 1

    def register_return_listener(self, name: str, after_seconds: float, callback: Callable[[float], object]) -> None:
        def recorded(silence: float) -> object:
            self.listener_calls.append((name, silence, threading.get_ident()))
            return callback(silence)

        super().register_return_listener(name, after_seconds, recorded)
        self.registrations.append((name, after_seconds))
        self.registered.set()


def _settings(*, enabled: bool = True, scheduler_timezone: str = "UTC") -> SchedulerSettings:
    """Days Monday to Saturday, slots 06:00 and 23:00, a ten-minute price refresh, a horizon of ``HORIZON_DAYS``."""
    return SchedulerSettings(
        scheduler_enabled=enabled,
        current_price_frequency_minutes=10,
        history_sync_times=[time(6, 0), time(23, 0)],
        history_sync_days=["mon", "tue", "wed", "thu", "fri", "sat"],
        history_sync_horizon_days=HORIZON_DAYS,
        scheduler_timezone=scheduler_timezone,
    )


class World:
    """Every collaborator of ``run_due_jobs``, faked: a test sets what each one answers, and reads what each one saw.

    ``timeline`` records the calls in order — ``("settle",)``, ``("disabled",)``, ``("blocked",)``, ``("leader",)``,
    ``("settings",)``, ``("load",)``, ``("due", name)``, ``("job", name)``, ``("save",)`` —; the clock readings are kept
    apart, in ``wall.readings``. The state store keeps a deep copy of what was saved and hands out a deep copy of it,
    as a file would. A job is due when the state it is given says it never ran.
    """

    def __init__(self, activity: RecordingActivity) -> None:
        self.activity = activity
        self.wall = WallClock()
        self.disabled = False
        self.blocked = False
        self.leader = True
        self.settings = _settings()
        self.settings_failure: BaseException | None = None
        self.settle_shift = timedelta(0)
        self.writes = {name: dict(values) for name, values in WRITTEN.items()}
        self.failures: dict[str, BaseException] = {}
        self.save_failures: list[BaseException] = []
        self.reset()

    def reset(self) -> None:
        """A state never run and nothing recorded: the next run starts as the first one did."""
        self.stored = SchedulerState()
        self.on_settle: Callable[[], None] | None = None
        self.gates: dict[str, tuple[asyncio.Event, asyncio.Event]] = {}
        self.timeline: list[tuple[str, ...]] = []
        self.threads: dict[str, list[int]] = {"leader": [], "load": [], "save": []}
        self.busy_seen: defaultdict[str, list[bool]] = defaultdict(list)
        self.loaded: list[SchedulerState] = []
        self.saved: list[SchedulerState] = []
        self.due_calls: list[tuple[str, datetime, SchedulerSettings, SchedulerState]] = []
        self.job_calls: list[tuple[str, SchedulerState, object]] = []

    def ran_before(self, name: str, when: datetime) -> None:
        """The stored state says ``name`` ran at ``when``: it is not due."""
        setattr(self.stored, name, JobState(last_run_at=when.isoformat(), last_duration_s=0.5, last_status="ok", last_items_ok=1))

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in ("scheduler_disabled", "instance_blocked", "am_i_leader", "load_scheduler_settings", "load_state", "save_state", "run_current_price_refresh", "run_history_sync", "settle_clock"):
            monkeypatch.setattr(scheduler, name, getattr(self, name))
        monkeypatch.setattr(scheduler, "due_current_price", self._due("current_price"))
        monkeypatch.setattr(scheduler, "due_history_sync", self._due("history_sync"))
        monkeypatch.setattr(scheduler, "utc_now", self.wall)

    def _listed(self, where: str) -> None:
        self.busy_seen[where].append(SCHEDULER_REASON in self.activity.busy_reasons())

    def scheduler_disabled(self) -> bool:
        self.timeline.append(("disabled",))
        return self.disabled

    def instance_blocked(self) -> bool:
        self.timeline.append(("blocked",))
        return self.blocked

    def am_i_leader(self) -> bool:
        self.timeline.append(("leader",))
        self.threads["leader"].append(threading.get_ident())
        self._listed("leader")
        return self.leader

    async def load_scheduler_settings(self) -> SchedulerSettings:
        self.timeline.append(("settings",))
        if self.settings_failure is not None:
            raise self.settings_failure
        return self.settings

    def load_state(self) -> SchedulerState:
        self.timeline.append(("load",))
        self.threads["load"].append(threading.get_ident())
        state = copy.deepcopy(self.stored)
        self.loaded.append(state)
        return state

    def save_state(self, state: SchedulerState) -> None:
        self.timeline.append(("save",))
        self.threads["save"].append(threading.get_ident())
        self._listed("save")
        self.saved.append(state)
        if self.save_failures:
            raise self.save_failures.pop(0)
        self.stored = copy.deepcopy(state)

    def _due(self, name: str) -> Callable[[datetime, SchedulerSettings, SchedulerState], bool]:
        def due(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
            self.timeline.append(("due", name))
            self.due_calls.append((name, now, settings, state))
            return getattr(state, name).last_run_at is None

        return due

    async def run_current_price_refresh(self, state: SchedulerState) -> None:
        await self._job("current_price", state, None)

    async def run_history_sync(self, state: SchedulerState, horizon_days: object = NOT_GIVEN) -> None:
        await self._job("history_sync", state, horizon_days)

    async def _job(self, name: str, state: SchedulerState, horizon_days: object) -> None:
        """As a real job does: it writes its ``JobState`` into the state it is given, then returns; or it raises, or it first waits on its gate."""
        self.timeline.append(("job", name))
        self.job_calls.append((name, state, horizon_days))
        self._listed(f"job:{name}")
        gate = self.gates.get(name)
        if gate is not None:
            entered, release = gate
            entered.set()
            await release.wait()
        failure = self.failures.get(name)
        if failure is not None:
            raise failure
        setattr(state, name, JobState(last_run_at=self.wall.now.isoformat(), **self.writes[name]))

    async def settle_clock(self) -> None:
        """Records the settle, moves the wall clock on by ``settle_shift``, and calls ``on_settle``: it never waits."""
        self.timeline.append(("settle",))
        self._listed("settle")
        self.wall.now += self.settle_shift
        if self.on_settle is not None:
            self.on_settle()


class RunRecorder:
    """``run_due_jobs`` in the loop tests: it records each reason, and a test may hold a run on a gate or make it raise."""

    def __init__(self, activity: RecordingActivity) -> None:
        self.activity = activity
        self.disabled = False
        self.reasons: list[str] = []
        self.registrations_seen: list[list[tuple[str, float]]] = []
        self.ended = 0
        self.gates: dict[int, asyncio.Event] = {}
        self.failures: dict[int, BaseException] = {}
        self._changed: asyncio.Event | None = None

    def _signal(self) -> None:
        if self._changed is not None:
            self._changed.set()

    async def __call__(self, reason: str) -> Any:
        self.reasons.append(reason)
        number = len(self.reasons)
        self.registrations_seen.append(list(self.activity.registrations))
        self._signal()
        try:
            gate = self.gates.get(number)
            if gate is not None:
                await gate.wait()
            failure = self.failures.get(number)
            if failure is not None:
                raise failure
            moment = datetime.now(UTC)
            return scheduler.RunReport(reason=reason, status="ok", started_at=moment, finished_at=moment)
        finally:
            self.ended += 1
            self._signal()

    async def wait_for(self, count: int, *, ended: bool = False) -> None:
        """Until the ``count``-th run has started — or ended —, within the deadline."""
        if self._changed is None:
            self._changed = asyncio.Event()
        changed = self._changed

        async def reached() -> None:
            while (self.ended if ended else len(self.reasons)) < count:
                changed.clear()
                await changed.wait()

        await _within(reached(), lambda: f"run #{count} {'ended' if ended else 'started'}? the runs so far: {self.reasons}")


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def activity(monkeypatch: pytest.MonkeyPatch) -> RecordingActivity:
    """The test's own ``Activity``, on a fake clock, in place of the process's ``ACTIVITY``: ``current_activity()`` answers it."""
    mine = RecordingActivity(FakeClock())
    monkeypatch.setattr(activity_module, "ACTIVITY", mine)
    return mine


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity) -> World:
    """Every collaborator of ``run_due_jobs`` replaced on the module by the fakes of a ``World``."""
    fakes = World(activity)
    fakes.install(monkeypatch)
    return fakes


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity) -> RunRecorder:
    """The loop's collaborators: a ``RunRecorder`` in place of ``run_due_jobs``, the switch it reads, the first run at once and a tick of an hour."""
    recorder = RunRecorder(activity)
    monkeypatch.setattr(scheduler, "scheduler_disabled", lambda: recorder.disabled)
    monkeypatch.setattr(scheduler, "run_due_jobs", recorder)
    monkeypatch.setattr(scheduler, "FIRST_RUN_DELAY_SECONDS", 0.0)
    monkeypatch.setattr(scheduler, "TICK_SECONDS", 3_600.0)
    return recorder


async def _within(awaitable: Awaitable[Any], what: str | Callable[[], str]) -> Any:
    """What ``awaitable`` gives, or a failure naming ``what`` after ``WAIT_SECONDS``: a hang fails the test instead of the run."""
    try:
        return await asyncio.wait_for(awaitable, WAIT_SECONDS)
    except TimeoutError:
        pytest.fail(f"{what() if callable(what) else what}: nothing within {WAIT_SECONDS} s")


@asynccontextmanager
async def _looping(shutdown: asyncio.Event) -> AsyncIterator[asyncio.Task[None]]:
    """``scheduler_loop(shutdown)`` as a task of this test's event loop; at the end the shutdown is set, and the task must end within the deadline — what it raised is raised here."""
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


def _return_after(activity: RecordingActivity, silence: float) -> None:
    """A request of the user after ``silence`` seconds of silence by the activity's fake clock: the clock moves on, then the request runs, its body moving nothing."""
    last = activity.last_user_request_at
    activity.clock.now = (activity.started_at if last is None else last) + silence
    with activity.request():
        pass


@contextmanager
def _captured_log() -> Iterator[list[dict[str, Any]]]:
    """What the scheduler and the activity log inside the block, behind a barrier: a canary logged through each module's own logger must arrive first."""
    with capture_logs() as events:
        scheduler.logger.debug(SCHEDULER_CANARY)
        activity_module.logger.debug(ACTIVITY_CANARY)
        arrived = {event.get("event") for event in events}
        assert {SCHEDULER_CANARY, ACTIVITY_CANARY} <= arrived, f"barrier: a module's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


def _logged(events: list[dict[str, Any]], event: str, key: str) -> list[tuple[Any, Any]]:
    """``(<key>, level)`` of every captured ``event``, in order."""
    return [(entry.get(key), entry.get("log_level")) for entry in events if entry.get("event") == event]


def _assert_utc(moment: object, what: str) -> None:
    assert isinstance(moment, datetime) and moment.tzinfo is not None and moment.utcoffset() == timedelta(0), f"{what}: {moment!r} is not an aware datetime in UTC"


def _assert_frame(report: Any, reason: str) -> None:
    """A ``RunReport`` echoing ``reason``, started no later than it finished, both in UTC."""
    assert isinstance(report, scheduler.RunReport), f"not a RunReport: {report!r}"
    assert report.reason == reason
    _assert_utc(report.started_at, "started_at")
    _assert_utc(report.finished_at, "finished_at")
    assert report.started_at <= report.finished_at, report


def _outcome(report: Any, name: str) -> Any:
    return next(outcome for outcome in report.jobs if outcome.name == name)


def _jobs_and_saves(world: World) -> list[tuple[str, ...]]:
    """The jobs run and the saves, in the order of the timeline."""
    return [entry for entry in world.timeline if entry[0] in ("job", "save")]


def _rome(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=ROME)


# =============================================================================
# (a), (b) CONSTANTS, TYPES, CLOCK
# =============================================================================


def test_the_constants_have_their_values_and_a_reason_is_one_of_four() -> None:
    """SCU-001 — contract (a): the eight constants have the values of the contract; ``RunReason`` is "startup", "tick", "return" or "wake"."""
    print_section("SCU-001: the scheduler's constants and RunReason")
    expected = {
        "CATCH_UP_AFTER_SECONDS": CATCH_UP_AFTER,
        "CLOCK_SETTLE_SECONDS": 2.0,
        "TICK_SECONDS": 60.0,
        "FIRST_RUN_DELAY_SECONDS": 5.0,
        "MISSED_SLOT_LOOKBACK_DAYS": 7,
        "CATCH_UP_LISTENER": LISTENER_NAME,
        "BUSY_REASON": SCHEDULER_REASON,
        "JOB_NAMES": JOBS,
    }

    assert {name: getattr(scheduler, name, "<missing>") for name in expected} == expected
    assert set(get_args(getattr(scheduler.RunReason, "__value__", scheduler.RunReason))) == set(REASONS)
    print_success("eight constants; four reasons")


def test_job_outcome_and_run_report_are_frozen_dataclasses_with_the_contract_fields() -> None:
    """SCU-002 — contract (b): the fields of ``JobOutcome`` and ``RunReport``, in order, with their defaults; both frozen."""
    print_section("SCU-002: JobOutcome and RunReport")

    def shape(cls: type) -> list[tuple[str, object]]:
        return [(field.name, REQUIRED if field.default is dataclasses.MISSING else field.default) for field in dataclasses.fields(cls)]

    assert shape(scheduler.JobOutcome) == [("name", REQUIRED), ("status", REQUIRED), ("started_at", None), ("duration_s", None), ("items_ok", 0), ("items_err", 0), ("error", None)]
    assert shape(scheduler.RunReport) == [("reason", REQUIRED), ("status", REQUIRED), ("started_at", REQUIRED), ("finished_at", REQUIRED), ("jobs", ())]
    outcome = scheduler.JobOutcome("current_price", "not_due")
    report = scheduler.RunReport("tick", "ok", WALL_START, WALL_START)
    with pytest.raises(dataclasses.FrozenInstanceError):
        outcome.status = "ok"
    with pytest.raises(dataclasses.FrozenInstanceError):
        report.status = "error"
    assert (outcome.started_at, outcome.duration_s, outcome.items_ok, outcome.items_err, outcome.error, report.jobs) == (None, None, 0, 0, None, ())
    print_success("fields in order, defaults, frozen")


def test_utc_now_reads_the_wall_clock_in_utc() -> None:
    """SCU-003 — contract (b): ``utc_now()`` is an aware datetime in UTC, between two readings of the wall clock taken around it."""
    print_section("SCU-003: utc_now()")

    before = datetime.now(UTC)
    reading = scheduler.utc_now()
    after = datetime.now(UTC)

    _assert_utc(reading, "utc_now()")
    assert before <= reading <= after
    print_success("the wall clock, in UTC")


@pytest.mark.asyncio
async def test_settle_clock_waits_the_clock_settle_seconds_of_the_moment(monkeypatch: pytest.MonkeyPatch) -> None:
    """SCU-004 — contract (b): ``settle_clock`` is a coroutine function returning None. With ``CLOCK_SETTLE_SECONDS`` at 0 it is over before a timer of one second fires; at 3600 it is still waiting when a timer of 0.05 s gives up.

    Both bounds are timers of the loop, which never fire before the callbacks already due: a load spike can delay them,
    never reverse them.
    """
    print_section("SCU-004: settle_clock()")
    assert inspect.iscoroutinefunction(scheduler.settle_clock)

    monkeypatch.setattr(scheduler, "CLOCK_SETTLE_SECONDS", 0.0)
    assert await asyncio.wait_for(scheduler.settle_clock(), timeout=1.0) is None

    monkeypatch.setattr(scheduler, "CLOCK_SETTLE_SECONDS", 3_600.0)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(scheduler.settle_clock(), timeout=0.05)
    print_success("waits CLOCK_SETTLE_SECONDS, read at the call")


# =============================================================================
# (c), (d) THE REASON, THE BUSY SPAN
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", ["", "Tick", "tick ", "nudge", "catch-up"])
async def test_an_unknown_reason_is_refused_before_anything_happens(world: World, activity: RecordingActivity, reason: str) -> None:
    """SCU-005 — contract (c): a reason other than the four — another case, a trailing space, an empty string, a word of its own — is a ``ValueError``; no busy span was opened, no collaborator called, not even the settle."""
    print_section(f"SCU-005: run_due_jobs({reason!r})")

    with pytest.raises(ValueError):
        await _within(scheduler.run_due_jobs(reason), "a run with an unknown reason")

    assert world.timeline == []
    assert activity.spans_opened == []
    print_success("ValueError; nothing happened")


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", REASONS)
async def test_the_run_is_busy_from_the_settle_to_the_last_save_and_not_after(world: World, activity: RecordingActivity, reason: str) -> None:
    """SCU-006 — contract (d): "scheduler" is listed during the settle — for "return" and "wake" —, while the leader is asked, during each job and each save; once the run is over, no longer, and no span of it is left open."""
    print_section(f"SCU-006: busy('scheduler') through a {reason} run")

    report = await _within(scheduler.run_due_jobs(reason), f"the {reason} run")

    expected = {"leader": [True], "job:current_price": [True], "job:history_sync": [True], "save": [True, True]}
    if reason in SETTLING_REASONS:
        expected["settle"] = [True]
    assert dict(world.busy_seen) == expected
    assert SCHEDULER_REASON not in activity.busy_reasons()
    assert activity.open_spans[SCHEDULER_REASON] == 0
    _assert_frame(report, reason)
    print_success("listed from the start to the end, not after")


@pytest.mark.asyncio
async def test_an_exception_out_of_the_run_closes_its_busy_span_and_frees_the_lock(world: World, activity: RecordingActivity) -> None:
    """SCU-007 — contract (d): the settings cannot be read. Whether the run raises that very exception or reports it — the contract leaves it open —, the state was not loaded, "scheduler" is no longer listed, and the next run goes through the lock and runs both jobs."""
    print_section("SCU-007: an exception out of run_due_jobs")
    failure = RuntimeError(f"provoked: the settings cannot be read, {SECRET}")
    world.settings_failure = failure

    try:
        result = await _within(scheduler.run_due_jobs("tick"), "the run whose settings fail")
    except RuntimeError as raised:
        assert raised is failure
    else:
        assert isinstance(result, scheduler.RunReport) and result.jobs == (), result

    assert ("load",) not in world.timeline
    assert SCHEDULER_REASON not in activity.busy_reasons()
    assert activity.open_spans[SCHEDULER_REASON] == 0
    world.settings_failure = None
    report = await _within(scheduler.run_due_jobs("tick"), "the next run: is the lock still held?")
    assert [(outcome.name, outcome.status) for outcome in report.jobs] == [("current_price", "ok"), ("history_sync", "ok")]
    print_success("the span closed, the lock free")


# =============================================================================
# (e) THE SETTLE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", REASONS)
async def test_return_and_wake_settle_first_and_the_due_checks_read_the_corrected_clock(world: World, reason: str) -> None:
    """SCU-008 — contract (e): the settle recorder moves the wall clock on by 90 minutes, as Fly corrects it after a resume. A "return" or "wake" run settles once, before anything else, and both due checks and both jobs' ``started_at`` read the corrected time; a "startup" or "tick" run never settles, and reads the time as it was."""
    print_section(f"SCU-008: the settle of a {reason} run")
    world.settle_shift = CLOCK_CORRECTION
    settles = reason in SETTLING_REASONS
    expected_now = WALL_START + CLOCK_CORRECTION if settles else WALL_START

    report = await _within(scheduler.run_due_jobs(reason), f"the {reason} run")

    assert world.timeline.count(("settle",)) == (1 if settles else 0)
    assert (world.timeline[0] == ("settle",)) is settles, world.timeline
    assert [now for _, now, _, _ in world.due_calls] == [expected_now, expected_now]
    assert [outcome.started_at for outcome in report.jobs] == [expected_now, expected_now]
    print_success("settled first, then the clock read" if settles else "no settle")


# =============================================================================
# (f) THE LOCK
# =============================================================================


async def _contended_pair(world: World) -> tuple[list[tuple[str, ...]], int, Any, Any]:
    """Run A, "tick", holds the lock inside its current_price job; run B, "return", settles and goes to the lock; then A is released.

    Returns what was called after B's settle at the moment B was left standing — B's settle recorder releases the test
    and B goes on to the lock without any other await, so a run with no lock would already have asked its switches —,
    the "scheduler" spans open at that moment, and both reports. The gates and events are created in the running loop.
    """
    entered, release, settled = asyncio.Event(), asyncio.Event(), asyncio.Event()
    world.gates["current_price"] = (entered, release)
    world.on_settle = settled.set
    first = asyncio.create_task(scheduler.run_due_jobs("tick"), name="run-a")
    try:
        await _within(entered.wait(), "run A never started its current_price job")
        second = asyncio.create_task(scheduler.run_due_jobs("return"), name="run-b")
        await _within(settled.wait(), "run B never settled its clock")
        past_the_settle = world.timeline[world.timeline.index(("settle",)) + 1 :]
        spans = world.activity.open_spans[SCHEDULER_REASON]
    finally:
        release.set()
    return past_the_settle, spans, await _within(first, "run A to its end"), await _within(second, "run B to its end")


def _assert_serialised(world: World, past_the_settle: list[tuple[str, ...]], spans: int, first: Any, second: Any) -> None:
    """B waited at the lock, its span open, while A held it; B loaded the state A had saved, and found nothing due."""
    assert past_the_settle == [], f"run B went past the lock while run A held it: {past_the_settle}"
    assert spans == 2, f"while B waited for the lock, {spans} 'scheduler' span(s) were open instead of A's and B's"
    assert [(outcome.name, outcome.status) for outcome in first.jobs] == [("current_price", "ok"), ("history_sync", "ok")]
    assert second.jobs == (scheduler.JobOutcome("current_price", "not_due"), scheduler.JobOutcome("history_sync", "not_due"))
    assert (first.status, second.status) == ("ok", "ok")
    loads = [index for index, entry in enumerate(world.timeline) if entry == ("load",)]
    saves = [index for index, entry in enumerate(world.timeline) if entry == ("save",)]
    assert (len(loads), len(saves)) == (2, 2) and loads[1] > saves[-1], f"B loaded before A's last save: {world.timeline}"
    assert [entry for entry in world.timeline if entry[0] == "job"] == [("job", "current_price"), ("job", "history_sync")]


@pytest.mark.asyncio
async def test_two_runs_in_one_loop_never_overlap_and_the_second_loads_what_the_first_saved(world: World) -> None:
    """SCU-009 — contracts (d), (e) and (f): while run A holds the lock inside a job, run B settles — before the lock — and stops there, its own span open: nothing of B is called past its settle. Released, A ends with both jobs run and saved; B then loads that state, and finds both jobs not due."""
    print_section("SCU-009: two runs contending in one loop")

    past_the_settle, spans, first, second = await _contended_pair(world)

    _assert_serialised(world, past_the_settle, spans, first, second)
    print_success("one after the other; the second saw the first's state")


def test_runs_contending_in_two_successive_event_loops_both_work(world: World) -> None:
    """SCU-010 — contract (f): the pair of SCU-009 in a first ``asyncio.run``, then again in a second one, the state reset in between: both serialise, and the second loop meets no lock bound to the first."""
    print_section("SCU-010: two event loops in a row, contention in each")

    for loop_number in (1, 2):
        world.reset()
        past_the_settle, spans, first, second = asyncio.run(_contended_pair(world))
        _assert_serialised(world, past_the_settle, spans, first, second)
        print_success(f"event loop {loop_number}: serialised")


# =============================================================================
# (g) THE SHORT CIRCUITS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", REASONS)
@pytest.mark.parametrize(
    ("disabled", "blocked", "leader", "enabled", "status", "calls"),
    [
        # Every later answer would stop the run too: the order decides.
        pytest.param(True, True, False, False, "disabled", ["disabled"], id="scheduler-disabled"),
        pytest.param(False, True, False, False, "blocked", ["disabled", "blocked"], id="instance-blocked"),
        pytest.param(False, False, False, False, "not_leader", ["disabled", "blocked", "leader"], id="not-the-leader"),
        pytest.param(False, False, True, False, "disabled", ["disabled", "blocked", "leader", "settings"], id="setting-off"),
    ],
)
async def test_each_short_circuit_answers_in_order_without_loading_the_state(world: World, activity: RecordingActivity, reason: str, disabled: bool, blocked: bool, leader: bool, enabled: bool, status: str, calls: list[str]) -> None:
    """SCU-011 — contract (g): the switches are asked in their order, the first that says stop is the status, and nothing after it is asked; the state is neither loaded nor saved, no job runs, ``jobs`` is empty — whatever the reason, the settle of "return" and "wake" first. "scheduler" is not listed after."""
    print_section(f"SCU-011: {reason} run → {status} after {calls}")
    world.disabled, world.blocked, world.leader = disabled, blocked, leader
    world.settings = _settings(enabled=enabled)

    report = await _within(scheduler.run_due_jobs(reason), f"the {reason} run")

    _assert_frame(report, reason)
    assert (report.status, report.jobs) == (status, ())
    settle = [("settle",)] if reason in SETTLING_REASONS else []
    assert world.timeline == settle + [(call,) for call in calls]
    assert SCHEDULER_REASON not in activity.busy_reasons()
    print_success(f"{status}, nothing loaded, nothing run")


# =============================================================================
# (h) OFF THE LOOP
# =============================================================================


@pytest.mark.asyncio
async def test_the_leader_and_the_state_store_run_off_the_event_loop_thread(world: World) -> None:
    """SCU-012 — contract (h): ``am_i_leader``, ``load_state`` and both ``save_state`` calls ran in threads other than the one running the event loop."""
    print_section("SCU-012: am_i_leader, load_state, save_state off the loop")
    loop_thread = threading.get_ident()

    await _within(scheduler.run_due_jobs("tick"), "the run")

    assert {where: len(threads) for where, threads in world.threads.items()} == {"leader": 1, "load": 1, "save": 2}
    assert {where: [thread == loop_thread for thread in threads] for where, threads in world.threads.items()} == {"leader": [False], "load": [False], "save": [False, False]}
    print_success("three collaborators, four calls, none on the loop's thread")


# =============================================================================
# (i) THE JOBS
# =============================================================================


@pytest.mark.asyncio
async def test_due_jobs_run_in_order_on_the_loaded_state_each_saved_after_it(world: World) -> None:
    """SCU-013 — contract (i): after the switches, the state is loaded; each due function gets the settings and that very state, and is asked before its job runs; current_price runs, the state is saved, history_sync runs with ``horizon_days`` from the settings, the state is saved — the very object loaded, each time. Each outcome copies the ``JobState`` its job wrote, ``started_at`` the wall clock's time."""
    print_section("SCU-013: the jobs, their order, their saves, their outcomes")
    world.writes["current_price"] = {"last_duration_s": 1.25, "last_status": "partial", "last_items_ok": 7, "last_items_err": 2, "last_error": "QuotaExceeded"}

    report = await _within(scheduler.run_due_jobs("tick"), "the run")

    assert world.timeline[:5] == [("disabled",), ("blocked",), ("leader",), ("settings",), ("load",)]
    assert _jobs_and_saves(world) == [("job", "current_price"), ("save",), ("job", "history_sync"), ("save",)]
    assert all(world.timeline.index(("due", name)) < world.timeline.index(("job", name)) for name in JOBS), world.timeline
    (loaded,) = world.loaded
    assert sorted(name for name, _, _, _ in world.due_calls) == sorted(JOBS)
    assert all(settings is world.settings and state is loaded for _, _, settings, state in world.due_calls)
    assert [(name, state is loaded, horizon) for name, state, horizon in world.job_calls] == [("current_price", True, None), ("history_sync", True, HORIZON_DAYS)]
    assert [state is loaded for state in world.saved] == [True, True]
    assert report.jobs == (
        scheduler.JobOutcome("current_price", "partial", started_at=WALL_START, duration_s=1.25, items_ok=7, items_err=2, error="QuotaExceeded"),
        scheduler.JobOutcome("history_sync", "ok", started_at=WALL_START, duration_s=3.5, items_ok=40, items_err=0, error=None),
    )
    assert world.stored.history_sync.last_run_at == WALL_START.isoformat()
    _assert_frame(report, "tick")
    print_success("load, current_price, save, history_sync, save; outcomes copied")


@pytest.mark.asyncio
async def test_one_reading_of_the_clock_serves_both_due_checks(world: World) -> None:
    """SCU-014 — contract (i): the wall clock moves on by a second at each reading; both due functions still receive the same ``now``, one of its readings."""
    print_section("SCU-014: one now for both due checks")
    world.wall.step = timedelta(seconds=1)

    await _within(scheduler.run_due_jobs("tick"), "the run")

    nows = {now for _, now, _, _ in world.due_calls}
    assert len(world.due_calls) == 2 and len(nows) == 1, world.due_calls
    assert nows <= set(world.wall.readings)
    print_success("one reading, both checks")


@pytest.mark.asyncio
@pytest.mark.parametrize("not_due", [("current_price",), ("history_sync",), JOBS], ids=["current-price", "history-sync", "both"])
async def test_a_job_not_due_is_reported_not_due_and_neither_run_nor_saved(world: World, not_due: tuple[str, ...]) -> None:
    """SCU-015 — contract (i): a job its due function answers no to is ``JobOutcome(name, "not_due")`` — no start, no duration, no items, no error —, is not run, and no save follows it; both outcomes are there, in order, and the run is "ok"."""
    print_section(f"SCU-015: not due: {', '.join(not_due)}")
    for name in not_due:
        world.ran_before(name, WALL_START - timedelta(minutes=1))

    report = await _within(scheduler.run_due_jobs("tick"), "the run")

    assert [outcome.name for outcome in report.jobs] == list(JOBS)
    assert [_outcome(report, name) for name in not_due] == [scheduler.JobOutcome(name, "not_due") for name in not_due]
    assert _jobs_and_saves(world) == [entry for name in JOBS if name not in not_due for entry in (("job", name), ("save",))]
    assert report.status == "ok"
    print_success("not_due, not run, not saved")


@pytest.mark.asyncio
async def test_an_outcome_reads_ok_when_its_job_wrote_no_status(world: World) -> None:
    """SCU-016 — contract (i): current_price writes ``last_status`` None: its outcome is "ok", and so is the run."""
    print_section("SCU-016: last_status None reads ok")
    world.writes["current_price"]["last_status"] = None

    report = await _within(scheduler.run_due_jobs("tick"), "the run")

    assert (_outcome(report, "current_price").status, report.status) == ("ok", "ok")
    print_success("None → ok")


# =============================================================================
# (j) A JOB OR A SAVE THAT RAISES
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("failing", JOBS)
async def test_a_job_that_raises_is_an_error_outcome_logged_without_its_message(world: World, failing: str) -> None:
    """SCU-017 — contract (j): the job raises ``ProviderExploded`` with a secret in its message. Its outcome is "error", ``error`` "ProviderExploded", a float duration ≥ 0, a start in UTC; the other job runs and is "ok"; the run is "partial"; the failure is logged once — ERROR, "Scheduler job failed", ``job=<name>`` —; the message is nowhere in the report."""
    print_section(f"SCU-017: {failing} raises")
    world.failures[failing] = ProviderExploded(f"provoked: {SECRET}")

    with _captured_log() as events:
        report = await _within(scheduler.run_due_jobs("tick"), "the run")

    failed = _outcome(report, failing)
    assert (failed.status, failed.error) == ("error", "ProviderExploded")
    assert isinstance(failed.duration_s, float) and failed.duration_s >= 0, failed
    _assert_utc(failed.started_at, "started_at of the failed job")
    assert [(outcome.name, outcome.status) for outcome in report.jobs if outcome.name != failing] == [(name, "ok") for name in JOBS if name != failing]
    assert [entry for entry in world.timeline if entry[0] == "job"] == [("job", name) for name in JOBS]
    assert report.status == "partial"
    assert SECRET not in repr(report)
    assert _logged(events, JOB_FAILED, "job") == [(failing, "error")]
    print_success("error outcome by class name; the other job ran; logged once")


@pytest.mark.asyncio
async def test_a_save_that_raises_after_a_job_makes_that_job_an_error_and_the_next_one_runs(world: World) -> None:
    """SCU-018 — contract (j): the save after current_price raises ``PermissionError`` with a secret in its message: current_price is "error", ``error`` "PermissionError", a float duration ≥ 0; history_sync runs and is saved; the run is "partial"; logged once for current_price; the message is nowhere in the report."""
    print_section("SCU-018: save_state raises after current_price")
    world.save_failures = [PermissionError(f"provoked: {SECRET}")]

    with _captured_log() as events:
        report = await _within(scheduler.run_due_jobs("tick"), "the run")

    failed = _outcome(report, "current_price")
    assert (failed.status, failed.error) == ("error", "PermissionError")
    assert isinstance(failed.duration_s, float) and failed.duration_s >= 0, failed
    assert _outcome(report, "history_sync").status == "ok"
    assert _jobs_and_saves(world) == [("job", "current_price"), ("save",), ("job", "history_sync"), ("save",)]
    assert world.stored.history_sync.last_run_at == WALL_START.isoformat()
    assert report.status == "partial"
    assert SECRET not in repr(report)
    assert _logged(events, JOB_FAILED, "job") == [("current_price", "error")]
    print_success("the save's failure is the job's; the next job ran")


@pytest.mark.asyncio
async def test_both_jobs_raising_still_make_a_report(world: World) -> None:
    """SCU-019 — contracts (j) and (l): both jobs raise: both outcomes are "error", the run is "error", each failure is logged once, in order; the report is made all the same."""
    print_section("SCU-019: both jobs raise")
    for name in JOBS:
        world.failures[name] = ProviderExploded(f"provoked: {SECRET}")

    with _captured_log() as events:
        report = await _within(scheduler.run_due_jobs("wake"), "the run")

    _assert_frame(report, "wake")
    assert [(outcome.name, outcome.status, outcome.error) for outcome in report.jobs] == [(name, "error", "ProviderExploded") for name in JOBS]
    assert report.status == "error"
    assert SECRET not in repr(report)
    assert _logged(events, JOB_FAILED, "job") == [(name, "error") for name in JOBS]
    print_success("two errors, one report")


# =============================================================================
# (k) A CANCELLATION
# =============================================================================


@pytest.mark.asyncio
async def test_a_cancelled_run_ends_cancelled_closes_its_span_and_frees_the_lock(world: World, activity: RecordingActivity) -> None:
    """SCU-020 — contract (k): the run's task is cancelled while current_price waits on its gate: the task ends cancelled — the cancellation went through —, nothing was saved, "scheduler" is no longer listed, and the next run goes through the lock and runs both jobs."""
    print_section("SCU-020: a run cancelled inside a job")
    entered, never = asyncio.Event(), asyncio.Event()
    world.gates["current_price"] = (entered, never)
    task = asyncio.create_task(scheduler.run_due_jobs("tick"), name="run-to-cancel")
    await _within(entered.wait(), "current_price never started")
    assert SCHEDULER_REASON in activity.busy_reasons()

    task.cancel()
    done, _ = await asyncio.wait({task}, timeout=WAIT_SECONDS)

    assert task in done and task.cancelled(), f"the run swallowed its cancellation: {task!r}"
    assert ("save",) not in world.timeline
    assert SCHEDULER_REASON not in activity.busy_reasons()
    assert activity.open_spans[SCHEDULER_REASON] == 0
    del world.gates["current_price"]
    report = await _within(scheduler.run_due_jobs("tick"), "the next run: is the lock still held?")
    assert [(outcome.name, outcome.status) for outcome in report.jobs] == [("current_price", "ok"), ("history_sync", "ok")]
    print_success("cancelled; the span closed; the lock free")


# =============================================================================
# (l) THE REPORT'S STATUS
# =============================================================================

#: The outcome each way of preparing a job gives: not due; run, writing that status; raising.
OUTCOME_OF = {"not_due": "not_due", "ok": "ok", "partial": "partial", "error": "error", "raises": "error"}


def _prepare(world: World, name: str, how: str) -> None:
    """``name`` not due, or raising ``ProviderExploded``, or run writing ``how`` as its ``last_status``."""
    if how == "not_due":
        world.ran_before(name, WALL_START - timedelta(minutes=1))
    elif how == "raises":
        world.failures[name] = ProviderExploded(f"provoked: {SECRET}")
    else:
        world.writes[name]["last_status"] = how


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("first", "second", "status"),
    [
        pytest.param("not_due", "not_due", "ok", id="nothing-due"),
        pytest.param("ok", "not_due", "ok", id="ok-alone"),
        pytest.param("not_due", "ok", "ok", id="ok-alone-second"),
        pytest.param("ok", "ok", "ok", id="ok-ok"),
        pytest.param("partial", "not_due", "partial", id="partial-alone"),
        pytest.param("ok", "partial", "partial", id="ok-partial"),
        pytest.param("partial", "partial", "partial", id="partial-partial"),
        pytest.param("raises", "not_due", "error", id="raises-alone"),
        pytest.param("not_due", "error", "error", id="writes-error-alone"),
        pytest.param("raises", "error", "error", id="raises-and-writes-error"),
        pytest.param("raises", "raises", "error", id="raises-raises"),
        pytest.param("ok", "raises", "partial", id="ok-then-raises"),
        pytest.param("error", "ok", "partial", id="writes-error-then-ok"),
        pytest.param("partial", "raises", "partial", id="partial-then-raises"),
    ],
)
async def test_the_report_status_follows_the_jobs_that_ran(world: World, first: str, second: str, status: str) -> None:
    """SCU-021 — contract (l): "ok" when no job ran or every job that ran is "ok"; "error" when every job that ran is "error", raised or written; "partial" otherwise — a "partial", or "ok" beside "error". Each outcome is the one its job gave."""
    print_section(f"SCU-021: current_price {first}, history_sync {second} → {status}")
    for name, how in zip(JOBS, (first, second), strict=True):
        _prepare(world, name, how)

    report = await _within(scheduler.run_due_jobs("tick"), "the run")

    assert [(outcome.name, outcome.status) for outcome in report.jobs] == [(name, OUTCOME_OF[how]) for name, how in zip(JOBS, (first, second), strict=True)]
    assert report.status == status
    print_success(status)


# =============================================================================
# (m) A BLOCKED INSTANCE, THEN THE MISSED SLOT (D-Z3-4, D-Z3-1)
# =============================================================================


@pytest.mark.asyncio
async def test_a_blocked_instance_runs_nothing_then_catches_up_the_missed_slot_once_unblocked(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """SCU-022 — contracts (g) and (m), on the real due functions: history ran on Saturday 06:05 in Rome, days Monday to Saturday, slots 06:00 and 23:00. At Saturday 23:01 the instance is blocked: "blocked", nothing loaded, run or saved, the state as it was. On Sunday 10:00, unblocked, the first "tick" runs history_sync: the Saturday 23:00 slot was missed — where the rule of the day alone would have waited for Monday 06:00, Sunday not being a configured day."""
    print_section("SCU-022: blocked on Saturday night, caught up on Sunday morning")
    monkeypatch.setattr(scheduler, "due_current_price", REAL_DUE_CURRENT_PRICE)
    monkeypatch.setattr(scheduler, "due_history_sync", REAL_DUE_HISTORY_SYNC)
    world.settings = _settings(scheduler_timezone="Europe/Rome")
    world.stored = SchedulerState(
        current_price=JobState(last_run_at=_rome(2026, 6, 13, 23, 0).isoformat(), last_status="ok"),
        history_sync=JobState(last_run_at=_rome(2026, 6, 13, 6, 5).isoformat(), last_status="ok"),
    )
    as_it_was = copy.deepcopy(world.stored)

    world.blocked = True
    world.wall.now = _rome(2026, 6, 13, 23, 1).astimezone(UTC)
    blocked = await _within(scheduler.run_due_jobs("tick"), "the run of the blocked instance")
    assert (blocked.status, blocked.jobs) == ("blocked", ())
    assert world.timeline == [("disabled",), ("blocked",)]
    assert world.stored == as_it_was

    world.blocked = False
    world.wall.now = _rome(2026, 6, 14, 10, 0).astimezone(UTC)
    caught_up = await _within(scheduler.run_due_jobs("tick"), "the first run once unblocked")
    history = _outcome(caught_up, "history_sync")
    assert (history.status, history.started_at) == ("ok", world.wall.now), history
    assert world.stored.history_sync.last_run_at == world.wall.now.isoformat()
    assert caught_up.status == "ok"
    print_success("blocked: nothing; unblocked on Sunday: the Saturday 23:00 slot caught up")


# =============================================================================
# (n) THE LOOP
# =============================================================================


@pytest.mark.asyncio
async def test_a_disabled_scheduler_loop_returns_at_once_and_registers_nothing(runs: RunRecorder, activity: RecordingActivity) -> None:
    """SCU-023 — contract (n): under ``scheduler_disabled()`` the loop returns without its shutdown being set; it registered no listener, so a return after a long silence calls nothing; no run."""
    print_section("SCU-023: scheduler_loop, disabled")
    runs.disabled = True

    await _within(scheduler.scheduler_loop(asyncio.Event()), "the disabled loop never returned")
    _return_after(activity, LONG_SILENCE)

    assert (activity.registrations, activity.listener_calls, runs.reasons) == ([], [], [])
    print_success("returned at once; nothing registered, nothing run")


@pytest.mark.asyncio
async def test_the_loop_registers_its_return_listener_before_its_startup_run(runs: RunRecorder) -> None:
    """SCU-024 — contract (n): the first run is "startup", and when it starts the return listener is registered: "scheduler-catch-up", at 60 s."""
    print_section("SCU-024: the listener, then the startup run")

    async with _looping(asyncio.Event()):
        await runs.wait_for(1)

    assert runs.reasons == ["startup"]
    assert runs.registrations_seen[0] == [(LISTENER_NAME, CATCH_UP_AFTER)]
    print_success("registered at 60 s; startup first")


@pytest.mark.asyncio
async def test_a_return_before_the_first_delay_runs_startup_at_once(runs: RunRecorder, activity: RecordingActivity, monkeypatch: pytest.MonkeyPatch) -> None:
    """SCU-025 — contract (n): the first delay is an hour; once the loop has registered its listener, a return after a long silence nudges it, and the first run comes without waiting the hour — and it is "startup"."""
    print_section("SCU-025: a nudge during the first delay")
    monkeypatch.setattr(scheduler, "FIRST_RUN_DELAY_SECONDS", 3_600.0)

    async with _looping(asyncio.Event()):
        await _within(activity.registered.wait(), "the loop never registered its return listener")
        _return_after(activity, LONG_SILENCE)
        await runs.wait_for(1)

    assert runs.reasons == ["startup"]
    print_success("startup, on the nudge")


@pytest.mark.asyncio
async def test_a_shutdown_during_the_first_delay_ends_the_loop_without_a_run(runs: RunRecorder, activity: RecordingActivity, monkeypatch: pytest.MonkeyPatch) -> None:
    """SCU-026 — contract (n): the first delay is an hour; the shutdown comes once the listener is registered: the loop ends within the deadline without any run, and its listener is gone — a return after a long silence calls nothing."""
    print_section("SCU-026: shutdown during the first delay")
    monkeypatch.setattr(scheduler, "FIRST_RUN_DELAY_SECONDS", 3_600.0)

    async with _looping(asyncio.Event()):
        await _within(activity.registered.wait(), "the loop never registered its return listener")
    _return_after(activity, LONG_SILENCE)

    assert (runs.reasons, activity.listener_calls) == ([], [])
    print_success("no run; the listener removed")


@pytest.mark.asyncio
async def test_after_the_startup_run_a_timeout_runs_tick(runs: RunRecorder, monkeypatch: pytest.MonkeyPatch) -> None:
    """SCU-027 — contract (n): with a tick of 0.05 s and no nudge, the second run is "tick", and so is every one after it."""
    print_section("SCU-027: the tick")
    monkeypatch.setattr(scheduler, "TICK_SECONDS", 0.05)

    async with _looping(asyncio.Event()):
        await runs.wait_for(2)

    assert runs.reasons[0] == "startup"
    assert set(runs.reasons[1:]) == {"tick"}, runs.reasons
    print_success(f"startup, then {len(runs.reasons) - 1} tick(s)")


@pytest.mark.asyncio
async def test_a_return_at_the_threshold_nudges_a_return_run_and_one_just_below_does_not(runs: RunRecorder, activity: RecordingActivity) -> None:
    """SCU-028 — contract (n): after the startup run, a return after 59 s of silence calls no listener, so nothing can nudge; the next, after 60 s, calls the loop's listener with 60.0, and a "return" run follows without waiting the hour's tick."""
    print_section("SCU-028: 59 s, then 60 s of silence")

    async with _looping(asyncio.Event()):
        await runs.wait_for(1, ended=True)
        _return_after(activity, CATCH_UP_AFTER - 1)
        assert activity.listener_calls == []
        _return_after(activity, CATCH_UP_AFTER)
        await runs.wait_for(2)

    assert runs.reasons == ["startup", "return"]
    assert [(name, silence) for name, silence, _ in activity.listener_calls] == [(LISTENER_NAME, CATCH_UP_AFTER)]
    print_success("59 s: nothing; 60 s: a return run")


@pytest.mark.asyncio
async def test_a_return_from_another_thread_nudges_the_loop(runs: RunRecorder, activity: RecordingActivity) -> None:
    """SCU-029 — contract (n): the return comes from a worker thread, and the listener runs there; the "return" run follows, and no listener failed.

    The loop runs in debug mode for the test: there a call into the loop from another thread that is not thread-safe
    raises — the listener would fail and be logged — instead of passing by luck when something else wakes the loop.
    """
    print_section("SCU-029: a return from another thread")
    loop = asyncio.get_running_loop()
    debug = loop.get_debug()
    loop.set_debug(True)
    try:
        with _captured_log() as events:
            async with _looping(asyncio.Event()):
                await runs.wait_for(1, ended=True)
                await _within(asyncio.to_thread(_return_after, activity, LONG_SILENCE), "the request in a worker thread")
                await runs.wait_for(2)
    finally:
        loop.set_debug(debug)

    assert runs.reasons == ["startup", "return"]
    assert [(name, thread == threading.get_ident()) for name, _, thread in activity.listener_calls] == [(LISTENER_NAME, False)]
    assert _logged(events, LISTENER_FAILED, "listener") == []
    print_success("nudged from a worker thread")


@pytest.mark.asyncio
async def test_two_returns_during_a_run_make_one_return_run_after_it(runs: RunRecorder, activity: RecordingActivity, monkeypatch: pytest.MonkeyPatch) -> None:
    """SCU-030 — contract (n): two returns after long silences come while the startup run is held: both call the listener. Released, the startup run is followed by one "return" run, then by ticks — 0.05 s here, the marker that the loop went back to waiting: a second "return" would have come before it."""
    print_section("SCU-030: two nudges during a run")
    monkeypatch.setattr(scheduler, "TICK_SECONDS", 0.05)
    release = asyncio.Event()
    runs.gates[1] = release

    async with _looping(asyncio.Event()):
        await runs.wait_for(1)
        _return_after(activity, LONG_SILENCE)
        _return_after(activity, LONG_SILENCE)
        release.set()
        await runs.wait_for(3)

    assert len(activity.listener_calls) == 2
    assert runs.reasons[:3] == ["startup", "return", "tick"], runs.reasons
    assert runs.reasons.count("return") == 1, runs.reasons
    print_success("two nudges, one return run")


@pytest.mark.asyncio
async def test_a_run_that_raises_is_logged_and_the_loop_goes_on(runs: RunRecorder, activity: RecordingActivity) -> None:
    """SCU-031 — contract (n): the startup run raises: it is logged once — ERROR, "Scheduler run failed" —, the loop goes on, and a return after a long silence brings a "return" run."""
    print_section("SCU-031: a run that raises")
    runs.failures[1] = RuntimeError("provoked: the run fails")

    with _captured_log() as events:
        async with _looping(asyncio.Event()):
            await runs.wait_for(1, ended=True)
            _return_after(activity, LONG_SILENCE)
            await runs.wait_for(2)

    assert runs.reasons == ["startup", "return"]
    assert [entry.get("log_level") for entry in events if entry.get("event") == RUN_FAILED] == ["error"]
    print_success("logged; the loop went on")


@pytest.mark.asyncio
async def test_the_shutdown_ends_the_loop_promptly_and_removes_its_listener(runs: RunRecorder, activity: RecordingActivity) -> None:
    """SCU-032 — contract (n): after the startup run the shutdown is set: the loop's task is done within the deadline, with no further run; a return after a long silence then calls nothing, and no listener failure is logged."""
    print_section("SCU-032: the shutdown")
    shutdown = asyncio.Event()

    with _captured_log() as events:
        async with _looping(shutdown) as task:
            await runs.wait_for(1, ended=True)
            shutdown.set()
            done, _ = await asyncio.wait({task}, timeout=WAIT_SECONDS)
            assert task in done, f"the loop was still running {WAIT_SECONDS} s after its shutdown"
        _return_after(activity, LONG_SILENCE)

    assert runs.reasons == ["startup"]
    assert activity.listener_calls == []
    assert _logged(events, LISTENER_FAILED, "listener") == []
    print_success("ended; the listener removed")
