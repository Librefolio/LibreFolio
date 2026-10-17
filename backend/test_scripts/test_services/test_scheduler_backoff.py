"""``backend.app.services.platform.scheduler.scheduler``: the scheduler respects the providers' pauses after HTTP 429 and
backs off after a job that raises (plan phase01SleepWake §Z7b, decision D-Z7-4, lot Z7b).

A job whose items a provider refused for too many requests (``error_code == "RATE_LIMITED"``) writes into its
``JobState`` how many it deferred (``last_items_deferred``) and ``retry_at``, the end of the shortest pause; a job that
raises is held back by ``consecutive_failures`` and ``next_attempt_at``. The jobs' side is ``test_scheduler_jobs.py``,
the state file's ``test_scheduler_state.py``. The contract pinned here:

(C) ``due_current_price(now, settings, state)`` and ``due_history_sync(now, settings, state)`` check two rules first,
    before the rule of today: (1) ``next_attempt_at`` set and ``now < next_attempt_at`` → not due, held back after a
    failure, even if ``retry_at`` has passed and even if the regular rule says due; (2) else ``retry_at`` set and
    ``now >= retry_at`` → due: deferred items get their retry before the regular round, never after; (3) else the
    regular rule, unchanged (for history D-Z3-1's missed slot: ``test_scheduler_due.py``). A timestamp of these two
    fields that cannot be read counts as absent.
(D) In ``run_due_jobs``, a due job that raises an ``Exception``: its ``JobState`` is the previous one, with
    ``consecutive_failures`` + 1, ``next_attempt_at`` = ``utc_now()`` + the backoff, ``last_status`` "error",
    ``last_error`` the exception's class name, never its message, ``last_run_at`` unchanged — a missed slot stays due —,
    and the state is saved. When the job returns and ``save_state`` then raises, the job did complete: the fresh
    ``JobState`` it wrote, with its new ``last_run_at``, is the base of the same record. The backoff is
    60 s × 2^(failures − 1), capped at 3600 s for ``history_sync`` and at ``current_price_frequency_minutes`` × 60 for
    ``current_price``: 60, 120, 240 s…, and no more than 600 s with a price every 10 minutes. Before ``next_attempt_at``
    the job is not due; from it on, it runs again; a run that ends writes a fresh ``JobState``, which resets both fields.
    Each job's backoff is its own. The failure is still logged — ERROR, "Scheduler job failed", ``job=<name>`` — and
    reported as "error" with the class name.
(E) ``JobOutcome`` ends with ``items_deferred`` (0) and ``retry_at`` (None, else an aware datetime in UTC): a job that ran
    copies its ``last_items_deferred`` and its ``retry_at`` parsed; a job that raised gives its new ``next_attempt_at``; a
    job not due gives the time it is pending until — ``next_attempt_at`` if in the future, else ``retry_at`` if in the
    future, else None — and ``items_deferred`` 0. The due rules are the same whatever the run's reason: a return and a
    wake-up (lots Z3, Z4) see a job held back as not due.

Pure: no database, no server, no lane port, no network. (C) calls the two due functions as they are. (D) and (E) go
through ``run_due_jobs`` with every collaborator but the due functions faked on the module with ``monkeypatch``, as in
``test_scheduler_catchup.py``: the switches let the run through, the settings are a test's, a state store in memory
hands out and keeps deep copies as a file would, the lock across processes (Z-11) is a no-op stand-in that writes no
file, ``utc_now`` is a wall clock that moves only when the test moves it, and the two jobs record their call, then
raise, or write a fresh ``JobState`` — ``last_run_at`` the wall clock's time —
as the real ones will. The real due functions decide what runs. Each test has its own ``Activity`` on a fake clock in
place of the process's. Nothing sleeps, and no assertion depends on a duration: every moment is the fake wall clock's.
The log is read with ``structlog.testing.capture_logs`` behind a barrier: a canary logged through the scheduler's own
``logger`` must reach the capture.

Red until the code of Z7b exists: ``JobState`` does not take its four new fields nor ``JobOutcome`` its two, a
``TypeError`` wherever a test builds one; the due functions ignore ``retry_at`` and ``next_attempt_at``; a job that
raises leaves its state as it was, unsaved.
"""

from __future__ import annotations

import asyncio
import copy
import dataclasses
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from structlog.testing import capture_logs

from backend.app.services.platform.scheduler import scheduler
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import JobState, SchedulerState
from backend.app.services.platform.sleep_wake import activity as activity_module
from backend.app.services.platform.sleep_wake.activity import Activity
from backend.test_scripts.test_utils import print_section, print_success

JOBS = ("current_price", "history_sync")
REASONS = ("startup", "tick", "return", "wake")
JOB_FAILED = "Scheduler job failed"
SCHEDULER_CANARY = "scheduler backoff test: canary through the scheduler's logger"

#: The longest a test waits for a run.
WAIT_SECONDS = 30.0
#: Where the wall clock of the run tests starts: Monday 2026-06-08 10:00 UTC, after the 06:00 slot, before the 23:00 one.
MONDAY_10 = datetime(2026, 6, 8, 10, 0, tzinfo=UTC)
#: The current-price frequency of the settings, in minutes: its backoff stops at 600 s.
FREQUENCY_MINUTES = 10
HORIZON_DAYS = 21
#: In the message of every failure provoked here: it must reach neither the state nor a report.
SECRET = "token=SECRET"
#: A timestamp that cannot be read: it counts as absent.
UNREADABLE = "not a timestamp"
#: The ``last_run_at`` of a job that never ran.
NEVER = None
ROME = ZoneInfo("Europe/Rome")
#: What a fake job writes into its ``JobState`` when it returns, besides ``last_run_at``: a fresh ``JobState``, so its
#: ``consecutive_failures`` and ``next_attempt_at`` are back at their defaults, as the real jobs' will be.
WRITTEN: dict[str, dict[str, Any]] = {
    "current_price": {"last_duration_s": 1.25, "last_status": "ok", "last_items_ok": 7, "last_items_err": 0, "last_error": None},
    "history_sync": {"last_duration_s": 3.5, "last_status": "ok", "last_items_ok": 40, "last_items_err": 0, "last_error": None},
}

#: The real due functions, read before any test replaces them: the run tests put them back in place.
REAL_DUE_CURRENT_PRICE = scheduler.due_current_price
REAL_DUE_HISTORY_SYNC = scheduler.due_history_sync


class ProviderExploded(Exception):
    """A job's failure, named so that its class is recognisable in a state and in an outcome."""


@asynccontextmanager
async def _no_cross_process_lock(*_args: object, **_kwargs: object) -> AsyncIterator[None]:
    """``scheduler_run_lock`` stood in for (Z-11, N71): held at once, no file written; ``test_scheduler_run_lock.py`` tests the real one."""
    yield


# =============================================================================
# FAKES
# =============================================================================


class WallClock:
    """``utc_now()`` of the run under test: an aware UTC datetime that moves only when the test moves it."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now


def _settings(*, frequency_minutes: int = FREQUENCY_MINUTES) -> SchedulerSettings:
    """Days Monday to Saturday, slots 06:00 and 23:00 in UTC, a current price every ``frequency_minutes``."""
    return SchedulerSettings(
        scheduler_enabled=True,
        current_price_frequency_minutes=frequency_minutes,
        history_sync_times=[time(6, 0), time(23, 0)],
        history_sync_days=["mon", "tue", "wed", "thu", "fri", "sat"],
        history_sync_horizon_days=HORIZON_DAYS,
        scheduler_timezone="UTC",
    )


class World:
    """Every collaborator of ``run_due_jobs`` but the two due functions, faked; the real due functions decide what runs.

    The switches let the run through and the settings are ``settings``. The state store keeps a deep copy of what was
    saved, in ``stored``, and hands out a deep copy of it, as a file would; the first saves raise ``save_failures``, in
    order. ``utc_now`` is ``wall``. A job records its name in ``calls``, then raises ``failures[name]`` if there is one,
    or else writes a fresh ``JobState`` — ``last_run_at`` the wall clock's time, then ``writes[name]`` —, as the real
    jobs do: a run that ends resets the backoff. The settle of "return" and "wake" is a no-op.
    """

    def __init__(self) -> None:
        self.wall = WallClock(MONDAY_10)
        self.settings = _settings()
        self.stored = SchedulerState()
        self.writes: dict[str, dict[str, Any]] = {name: dict(values) for name, values in WRITTEN.items()}
        self.failures: dict[str, BaseException] = {}
        self.save_failures: list[BaseException] = []
        self.calls: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        fakes: dict[str, object] = {
            "scheduler_disabled": lambda: False,
            "instance_blocked": lambda: False,
            "am_i_leader": lambda: True,
            "load_scheduler_settings": self.load_scheduler_settings,
            "load_state": self.load_state,
            "save_state": self.save_state,
            "run_current_price_refresh": self.run_current_price_refresh,
            "run_history_sync": self.run_history_sync,
            "settle_clock": self.settle_clock,
            "utc_now": self.wall,
            "due_current_price": REAL_DUE_CURRENT_PRICE,
            "due_history_sync": REAL_DUE_HISTORY_SYNC,
        }
        for name, fake in fakes.items():
            monkeypatch.setattr(scheduler, name, fake)
        # Z-11 (N71): with fcntl the run takes the lock across processes; stood in for, so that no .scheduler.lock is
        # written in the lane's data directory. raising=False: the name exists only once Z-11 does.
        monkeypatch.setattr(scheduler, "scheduler_run_lock", _no_cross_process_lock, raising=False)

    def ran(self, name: str, when: datetime | None, **fields: Any) -> JobState:
        """The stored state says ``name`` last ran at ``when`` — never, when None —, with ``fields`` besides; returns that ``JobState``."""
        job_state = JobState(last_run_at=None if when is None else when.isoformat(), **fields)
        setattr(self.stored, name, job_state)
        return job_state

    def just_ran(self, name: str) -> None:
        """``name`` ran at the wall clock's time: by the regular rule it is not due for the rest of a test, which lasts minutes on a Monday from 10:00."""
        self.ran(name, self.wall.now, last_status="ok")

    async def load_scheduler_settings(self) -> SchedulerSettings:
        return self.settings

    def load_state(self) -> SchedulerState:
        return copy.deepcopy(self.stored)

    def save_state(self, state: SchedulerState) -> None:
        if self.save_failures:
            raise self.save_failures.pop(0)
        self.stored = copy.deepcopy(state)

    async def run_current_price_refresh(self, state: SchedulerState) -> None:
        self._job("current_price", state)

    async def run_history_sync(self, state: SchedulerState, horizon_days: int | None = None) -> None:
        self._job("history_sync", state)

    def _job(self, name: str, state: SchedulerState) -> None:
        self.calls.append(name)
        failure = self.failures.get(name)
        if failure is not None:
            raise failure
        setattr(state, name, JobState(last_run_at=self.wall.now.isoformat(), **self.writes[name]))

    async def settle_clock(self) -> None:
        return None


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def activity(monkeypatch: pytest.MonkeyPatch) -> Activity:
    """The test's own ``Activity``, on a clock that never moves, in place of the process's ``ACTIVITY``: the run's busy span opens and closes there."""
    mine = Activity(clock=lambda: 1_000.0)
    monkeypatch.setattr(activity_module, "ACTIVITY", mine)
    return mine


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> World:
    """Every collaborator of ``run_due_jobs`` but the due functions replaced on the module by the fakes of a ``World``."""
    fakes = World()
    fakes.install(monkeypatch)
    return fakes


async def _within(awaitable: Awaitable[Any], what: str | Callable[[], str]) -> Any:
    """What ``awaitable`` gives, or a failure naming ``what`` after ``WAIT_SECONDS``: a hang fails the test instead of the run."""
    try:
        return await asyncio.wait_for(awaitable, WAIT_SECONDS)
    except TimeoutError:
        pytest.fail(f"{what() if callable(what) else what}: nothing within {WAIT_SECONDS} s")


async def _run(world: World, at: datetime | None = None, *, reason: str = "tick") -> tuple[Any, list[str]]:
    """One ``run_due_jobs(reason)``, at ``at`` by the wall clock when given: its report, and the jobs it ran, in order."""
    if at is not None:
        world.wall.now = at
    mark = len(world.calls)
    report = await _within(scheduler.run_due_jobs(reason), lambda: f"the {reason} run at {world.wall.now.isoformat()}")
    return report, world.calls[mark:]


@contextmanager
def _captured_log() -> Iterator[list[dict[str, Any]]]:
    """What the scheduler logs inside the block, behind a barrier: a canary logged through its own logger must arrive first."""
    with capture_logs() as events:
        scheduler.logger.debug(SCHEDULER_CANARY)
        assert SCHEDULER_CANARY in {event.get("event") for event in events}, f"barrier: the scheduler's logger does not reach capture_logs, so what this test reads of the log proves nothing: {events}"
        yield events


def _logged(events: list[dict[str, Any]], event: str, key: str) -> list[tuple[Any, Any]]:
    """``(<key>, level)`` of every captured ``event``, in order."""
    return [(entry.get(key), entry.get("log_level")) for entry in events if entry.get("event") == event]


def _outcome(report: Any, name: str) -> Any:
    return next(outcome for outcome in report.jobs if outcome.name == name)


def _other(name: str) -> str:
    return next(job for job in JOBS if job != name)


def _assert_utc(moment: object, what: str) -> None:
    assert isinstance(moment, datetime) and moment.tzinfo is not None and moment.utcoffset() == timedelta(0), f"{what}: {moment!r} is not an aware datetime in UTC"


def _instant(value: object, what: str) -> datetime:
    """A timestamp of the state, ISO-8601 and aware, read as an instant; a red naming ``what`` when it is not one."""
    assert isinstance(value, str), f"{what}: an ISO-8601 timestamp expected, got {value!r}"
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        pytest.fail(f"{what}: {value!r} is not ISO-8601")
    assert moment.utcoffset() is not None, f"{what}: {value!r} is not aware"
    return moment


def _at(now: datetime, offset: int | str | None) -> str | None:
    """How a state stores the moment ``offset`` seconds from ``now``: ISO-8601, aware; None and ``UNREADABLE`` stay as they are."""
    if offset is None or isinstance(offset, str):
        return offset
    return (now + timedelta(seconds=offset)).isoformat()


def _stored(value: datetime | str | None) -> str | None:
    """How a state stores ``value``: a datetime as ISO-8601; None and ``UNREADABLE`` as they are."""
    return value.isoformat() if isinstance(value, datetime) else value


def _last_success(name: str, now: datetime) -> datetime:
    """A last run after which ``name`` is due by the regular rule at ``now``, a Monday at 10:00: an hour before for the price, 05:00 — before the 06:00 slot — for the history."""
    return now - timedelta(hours=1) if name == "current_price" else now.replace(hour=5, minute=0)


def _record(base: JobState, *, failures: int, error: str, saved: JobState) -> JobState:
    """``base`` with the record of a failure: ``failures``, "error" and ``error``; ``next_attempt_at`` as ``saved`` holds it, its instant being checked apart."""
    return dataclasses.replace(base, consecutive_failures=failures, next_attempt_at=saved.next_attempt_at, last_status="error", last_error=error)


def _held(world: World, name: str) -> tuple[int, datetime]:
    """The stored ``consecutive_failures`` of ``name``, and its ``next_attempt_at`` read as an instant."""
    job_state = getattr(world.stored, name)
    return job_state.consecutive_failures, _instant(job_state.next_attempt_at, f"{name}.next_attempt_at")


def _seconds(count: float) -> timedelta:
    return timedelta(seconds=count)


# =============================================================================
# (C) THE DUE RULES
# =============================================================================

#: ``due_current_price`` every 10 minutes, now Monday 10:00: the last run, ``retry_at`` and ``next_attempt_at`` in
#: seconds from now (None absent, ``UNREADABLE`` as stored), and whether it is due. A run 60 s ago is not due by the
#: regular rule, one 900 s ago is.
PRICE_DUE = [
    pytest.param(-60, -30, None, True, id="retry-30s-ago-after-a-run-1-min-ago-is-due"),
    pytest.param(-60, 30, None, False, id="retry-in-30s-regular-not-due-is-not-due"),
    pytest.param(-60, 0, None, True, id="due-at-the-retry-instant"),
    pytest.param(-900, 30, None, True, id="a-retry-ahead-never-delays-the-regular-round"),
    pytest.param(-900, None, 300, False, id="held-though-the-regular-round-is-overdue"),
    pytest.param(-60, -30, 300, False, id="held-though-the-retry-has-passed"),
    pytest.param(NEVER, None, 300, False, id="held-though-it-never-ran"),
    pytest.param(-900, None, 0, True, id="the-hold-ends-at-the-next-attempt"),
    pytest.param(-60, None, -1, False, id="hold-over-the-regular-rule-not-due"),
    pytest.param(-900, None, -1, True, id="hold-over-the-regular-rule-due"),
    pytest.param(-60, -30, -1, True, id="hold-over-the-retry-passed"),
    pytest.param(-60, UNREADABLE, None, False, id="an-unreadable-retry-is-absent-not-due"),
    pytest.param(-900, UNREADABLE, None, True, id="an-unreadable-retry-is-absent-overdue"),
    pytest.param(-60, None, UNREADABLE, False, id="an-unreadable-hold-is-absent-not-due"),
    pytest.param(-900, None, UNREADABLE, True, id="an-unreadable-hold-is-absent-overdue"),
    pytest.param(-60, -30, UNREADABLE, True, id="an-unreadable-hold-is-absent-retry-passed"),
]


@pytest.mark.parametrize(("last_run", "retry", "next_attempt", "due"), PRICE_DUE)
def test_due_current_price_holds_back_after_a_failure_and_retries_deferred_items_first(last_run: int | None, retry: int | str | None, next_attempt: int | str | None, due: bool) -> None:
    """SBO-001 — contract (C) on ``due_current_price``, every 10 minutes, now Monday 10:00: a ``next_attempt_at`` ahead holds the job back, whatever ``retry_at`` and the regular rule say, and until that very instant only; else a ``retry_at`` reached makes it due, one ahead delays nothing; else the regular rule. A timestamp that cannot be read is no timestamp."""
    print_section(f"SBO-001: due_current_price, last run {last_run}, retry {retry}, next attempt {next_attempt} → {due}")
    now = MONDAY_10
    state = SchedulerState(current_price=JobState(last_run_at=_at(now, last_run), retry_at=_at(now, retry), next_attempt_at=_at(now, next_attempt)))

    assert REAL_DUE_CURRENT_PRICE(now, _settings(), state) is due
    print_success("due" if due else "not due")


def _utc(day: int, hour: int, minute: int, second: int = 0) -> datetime:
    """A moment of June 2026 in UTC: the 8th is a Monday, the 13th a Saturday, the 14th a Sunday."""
    return datetime(2026, 6, day, hour, minute, second, tzinfo=UTC)


#: ``due_history_sync``, days Monday to Saturday, slots 06:00 and 23:00 in UTC: now, the last run, ``retry_at``,
#: ``next_attempt_at`` (None absent, ``UNREADABLE`` as stored), and whether it is due.
HISTORY_DUE = [
    pytest.param(_utc(8, 23, 6), _utc(8, 23, 0, 30), _utc(8, 23, 5), None, True, id="deferred-at-23-00-retried-at-23-05-not-at-06-00"),
    pytest.param(_utc(8, 23, 4), _utc(8, 23, 0, 30), _utc(8, 23, 5), None, False, id="before-its-retry-not-due-until-06-00"),
    pytest.param(_utc(8, 23, 5), _utc(8, 23, 0, 30), _utc(8, 23, 5), None, True, id="due-at-the-retry-instant"),
    pytest.param(_utc(9, 2, 0), _utc(8, 23, 0, 30), _utc(8, 23, 5), None, True, id="a-retry-passed-in-the-night-is-still-due"),
    pytest.param(_utc(8, 23, 5), _utc(8, 7, 0), None, _utc(8, 23, 10), False, id="held-though-the-23-00-slot-is-due"),
    pytest.param(_utc(8, 23, 10), _utc(8, 7, 0), None, _utc(8, 23, 10), True, id="the-hold-ends-the-23-00-slot-is-due"),
    pytest.param(_utc(8, 23, 6), _utc(8, 23, 0, 30), _utc(8, 23, 5), _utc(8, 23, 10), False, id="held-though-the-retry-has-passed"),
    pytest.param(_utc(8, 23, 20), _utc(8, 23, 0, 30), None, _utc(8, 23, 10), False, id="hold-over-the-slot-already-run"),
    pytest.param(_utc(14, 10, 0), _utc(13, 6, 5), None, _utc(14, 10, 30), False, id="held-though-a-missed-slot-is-due-D-Z3-1"),
    pytest.param(_utc(14, 10, 30), _utc(13, 6, 5), None, _utc(14, 10, 30), True, id="the-hold-ends-the-missed-slot-is-due-D-Z3-1"),
    pytest.param(_utc(8, 23, 6), _utc(8, 23, 0, 30), UNREADABLE, None, False, id="an-unreadable-retry-is-absent"),
    pytest.param(_utc(8, 23, 5), _utc(8, 7, 0), None, UNREADABLE, True, id="an-unreadable-hold-is-absent"),
]


@pytest.mark.parametrize(("now", "last_run", "retry", "next_attempt", "due"), HISTORY_DUE)
def test_due_history_sync_holds_back_after_a_failure_and_retries_deferred_items_before_the_next_slot(now: datetime, last_run: datetime, retry: datetime | str | None, next_attempt: datetime | str | None, due: bool) -> None:
    """SBO-002 — contract (C) on ``due_history_sync``: a sync run at 23:00:30 that deferred items until 23:05 is due again from 23:05 — not at 06:00 the next day —, and still due at night if nothing ran it; a ``next_attempt_at`` ahead holds it back though a slot, missed or not (D-Z3-1), or a retry is due, until that very instant; past it, the regular rule. A timestamp that cannot be read is no timestamp."""
    print_section(f"SBO-002: due_history_sync at {now.isoformat()}, last run {last_run.isoformat()}, retry {retry}, next attempt {next_attempt} → {due}")
    state = SchedulerState(history_sync=JobState(last_run_at=last_run.isoformat(), retry_at=_stored(retry), next_attempt_at=_stored(next_attempt)))

    assert REAL_DUE_HISTORY_SYNC(now, _settings(), state) is due
    print_success("due" if due else "not due")


# =============================================================================
# (D) A JOB, OR ITS SAVE, THAT RAISES
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("failing", JOBS)
async def test_a_job_that_raises_records_its_failure_on_its_previous_state_and_saves_it(world: World, failing: str) -> None:
    """SBO-003 — contracts (D) and (E): the job, after two failures and with a retry passed, raises ``ProviderExploded`` with a secret in its message. Saved: its previous ``JobState`` — ``last_run_at`` and every other field as they were — with ``consecutive_failures`` 3, ``next_attempt_at`` now + 240 s, ``last_status`` "error", ``last_error`` "ProviderExploded". The outcome is "error" by the class name, its ``retry_at`` that next attempt, in UTC; the failure is logged once; the secret is neither in the state nor in the report."""
    print_section(f"SBO-003: {failing} raises after two failures")
    now = world.wall.now
    world.just_ran(_other(failing))
    previous = world.ran(
        failing,
        _last_success(failing, now),
        last_duration_s=2.5,
        last_status="partial",
        last_items_ok=4,
        last_items_err=1,
        last_items_deferred=2,
        retry_at=(now - timedelta(minutes=30)).isoformat(),
        consecutive_failures=2,
        next_attempt_at=(now - timedelta(seconds=1)).isoformat(),
    )
    world.failures[failing] = ProviderExploded(f"provoked: {SECRET}")

    with _captured_log() as events:
        report, ran = await _run(world)

    saved = getattr(world.stored, failing)
    assert ran == [failing]
    assert saved == _record(previous, failures=3, error="ProviderExploded", saved=saved), f"the previous JobState with the failure's record, saved: {saved}"
    assert _instant(saved.next_attempt_at, "next_attempt_at") == now + _seconds(240)
    failed = _outcome(report, failing)
    assert (failed.status, failed.error, failed.retry_at) == ("error", "ProviderExploded", now + _seconds(240)), failed
    _assert_utc(failed.retry_at, "the outcome's retry_at")
    assert _logged(events, JOB_FAILED, "job") == [(failing, "error")]
    assert SECRET not in repr(world.stored) and SECRET not in repr(report)
    print_success("third failure: held 240 s, last_run_at kept, saved, logged")


@pytest.mark.asyncio
@pytest.mark.parametrize("failing", JOBS)
async def test_a_save_that_raises_after_the_job_records_the_failure_on_the_state_the_job_wrote(world: World, failing: str) -> None:
    """SBO-004 — contracts (D) and (E): the job never ran nor failed; it runs and returns, then ``save_state`` raises ``PermissionError`` with a secret in its message. The job did complete: saved, the fresh ``JobState`` it wrote — its new ``last_run_at`` included — with ``consecutive_failures`` 1, ``next_attempt_at`` now + 60 s, ``last_status`` "error", ``last_error`` "PermissionError". The outcome is "error" by the class name, its ``retry_at`` that next attempt; logged once; the secret nowhere."""
    print_section(f"SBO-004: the save after {failing} raises")
    now = world.wall.now
    world.just_ran(_other(failing))
    world.ran(failing, NEVER)
    world.save_failures = [PermissionError(f"provoked: {SECRET}")]

    with _captured_log() as events:
        report, ran = await _run(world)

    fresh = JobState(last_run_at=now.isoformat(), **WRITTEN[failing])
    saved = getattr(world.stored, failing)
    assert ran == [failing]
    assert saved.last_run_at == now.isoformat(), f"the job completed: the last_run_at it wrote is kept: {saved}"
    assert saved == _record(fresh, failures=1, error="PermissionError", saved=saved), f"the JobState the job wrote with the failure's record, saved: {saved}"
    assert _instant(saved.next_attempt_at, "next_attempt_at") == now + _seconds(60)
    failed = _outcome(report, failing)
    assert (failed.status, failed.error, failed.retry_at) == ("error", "PermissionError", now + _seconds(60)), failed
    assert _logged(events, JOB_FAILED, "job") == [(failing, "error")]
    assert SECRET not in repr(world.stored) and SECRET not in repr(report)
    print_success("the job's own state, held 60 s, saved")


#: The job, the current-price frequency in minutes, the failures before this one, and the backoff after it, in seconds:
#: 60 × 2^(failures − 1), capped at the price's frequency for the price, at an hour for the history.
BACKOFF = [
    pytest.param("current_price", 10, 0, 60, id="price-1st-failure-60s"),
    pytest.param("current_price", 10, 1, 120, id="price-2nd-120s"),
    pytest.param("current_price", 10, 2, 240, id="price-3rd-240s"),
    pytest.param("current_price", 10, 3, 480, id="price-4th-480s"),
    pytest.param("current_price", 10, 4, 600, id="price-5th-capped-at-its-10-minutes"),
    pytest.param("current_price", 10, 99, 600, id="price-100th-still-10-minutes"),
    pytest.param("current_price", 3, 1, 120, id="price-every-3-minutes-2nd-120s"),
    pytest.param("current_price", 3, 2, 180, id="price-every-3-minutes-3rd-capped-at-180s"),
    pytest.param("history_sync", 10, 0, 60, id="history-1st-failure-60s"),
    pytest.param("history_sync", 10, 1, 120, id="history-2nd-120s"),
    pytest.param("history_sync", 10, 2, 240, id="history-3rd-240s"),
    pytest.param("history_sync", 10, 4, 960, id="history-5th-960s-past-the-price-cap"),
    pytest.param("history_sync", 10, 5, 1920, id="history-6th-1920s"),
    pytest.param("history_sync", 10, 6, 3600, id="history-7th-capped-at-an-hour"),
    pytest.param("history_sync", 10, 99, 3600, id="history-100th-still-an-hour"),
    pytest.param("history_sync", 3, 3, 480, id="history-cap-ignores-the-price-frequency"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("job", "frequency", "before", "seconds"), BACKOFF)
async def test_the_backoff_doubles_from_60_s_up_to_the_cap_of_its_job(world: World, job: str, frequency: int, before: int, seconds: int) -> None:
    """SBO-005 — contract (D): after ``before`` failures, its last next attempt passed, the job raises again: saved with ``consecutive_failures`` ``before`` + 1 and ``next_attempt_at`` now + ``seconds`` — 60, 120, 240 s…, capped at the price's frequency for the price, an hour for the history —, "error", the class name, ``last_run_at`` the last success's; the outcome's ``retry_at`` is that next attempt."""
    print_section(f"SBO-005: {job} every {frequency} min, failure #{before + 1} → {seconds} s")
    world.settings = _settings(frequency_minutes=frequency)
    now = world.wall.now
    world.just_ran(_other(job))
    previous = world.ran(
        job,
        _last_success(job, now),
        last_status="error" if before else "ok",
        last_error="ProviderExploded" if before else None,
        consecutive_failures=before,
        next_attempt_at=(now - timedelta(seconds=1)).isoformat() if before else None,
    )
    world.failures[job] = ProviderExploded("provoked")

    report, ran = await _run(world)

    saved = getattr(world.stored, job)
    assert ran == [job]
    assert (saved.consecutive_failures, saved.last_status, saved.last_error, saved.last_run_at) == (before + 1, "error", "ProviderExploded", previous.last_run_at), saved
    assert _instant(saved.next_attempt_at, "next_attempt_at") == now + _seconds(seconds)
    assert _outcome(report, job).retry_at == now + _seconds(seconds)
    print_success(f"held {seconds} s")


@pytest.mark.asyncio
@pytest.mark.parametrize("job", JOBS)
async def test_a_failing_job_waits_for_its_next_attempt_then_runs_and_a_run_that_ends_resets_it(world: World, job: str) -> None:
    """SBO-006 — contracts (C), (D) and (E), run after run on the real due functions: the job never ran, so the regular rule says due all along. It raises at T: held 60 s — at T+59 s not due, pending until T+60 s, not run —; at T+60 s it runs and raises again: held 120 s more; at T+179 s not due; at T+180 s it runs and returns: ``consecutive_failures`` 0, ``next_attempt_at`` None, "ok", no error, ``last_run_at`` T+180 s; at T+181 s not due, nothing pending."""
    print_section(f"SBO-006: {job} fails twice, waits, then succeeds")
    start = world.wall.now
    world.just_ran(_other(job))
    world.ran(job, NEVER)
    world.failures[job] = ProviderExploded("provoked")

    report, ran = await _run(world)
    assert (ran, _held(world, job)) == ([job], (1, start + _seconds(60)))

    report, ran = await _run(world, start + _seconds(59))
    assert ran == []
    assert _outcome(report, job) == scheduler.JobOutcome(job, "not_due", retry_at=start + _seconds(60))

    report, ran = await _run(world, start + _seconds(60))
    assert (ran, _held(world, job)) == ([job], (2, start + _seconds(180)))

    report, ran = await _run(world, start + _seconds(179))
    assert (ran, _outcome(report, job).status) == ([], "not_due")

    del world.failures[job]
    report, ran = await _run(world, start + _seconds(180))
    reset = getattr(world.stored, job)
    assert ran == [job]
    assert (reset.consecutive_failures, reset.next_attempt_at, reset.last_status, reset.last_error, reset.last_run_at) == (0, None, "ok", None, (start + _seconds(180)).isoformat()), reset
    assert (_outcome(report, job).status, _outcome(report, job).retry_at) == ("ok", None)

    report, ran = await _run(world, start + _seconds(181))
    assert ran == []
    assert _outcome(report, job) == scheduler.JobOutcome(job, "not_due")
    print_success("60 s, 120 s, then reset by a run that ends")


@pytest.mark.asyncio
async def test_a_history_sync_held_back_does_not_hold_back_the_current_price(world: World) -> None:
    """SBO-007 — contract (D): the history sync fails for the seventh time at 10:00 — held an hour —, the current price runs then and is left with no failure. At 10:10 the price is due again by its frequency and runs; the history, whose 06:00 slot is still uncovered, is not due, pending until 11:00."""
    print_section("SBO-007: each job's backoff is its own — history held, price runs")
    start = world.wall.now
    world.ran("current_price", start - timedelta(minutes=FREQUENCY_MINUTES), last_status="ok")
    world.ran("history_sync", _last_success("history_sync", start), last_status="error", last_error="ProviderExploded", consecutive_failures=6, next_attempt_at=(start - timedelta(seconds=1)).isoformat())
    world.failures["history_sync"] = ProviderExploded("provoked")

    report, ran = await _run(world)
    assert ran == list(JOBS)
    assert _held(world, "history_sync") == (7, start + _seconds(3_600))
    assert (world.stored.current_price.consecutive_failures, world.stored.current_price.next_attempt_at) == (0, None)

    report, ran = await _run(world, start + timedelta(minutes=FREQUENCY_MINUTES))
    assert ran == ["current_price"]
    assert _outcome(report, "current_price").status == "ok"
    assert _outcome(report, "history_sync") == scheduler.JobOutcome("history_sync", "not_due", retry_at=start + _seconds(3_600))
    print_success("history held an hour; the price ran")


@pytest.mark.asyncio
async def test_a_current_price_held_back_does_not_hold_back_the_history_sync(world: World) -> None:
    """SBO-008 — contract (D): Monday 22:59:30, the current price, never run, raises: held until 23:00:30. The history ran at 07:00. At 23:00 its slot is due and it runs; the price is not due, pending until 23:00:30."""
    print_section("SBO-008: each job's backoff is its own — price held, history runs")
    start = _utc(8, 22, 59, 30)
    world.wall.now = start
    world.ran("current_price", NEVER)
    world.ran("history_sync", _utc(8, 7, 0), last_status="ok")
    world.failures["current_price"] = ProviderExploded("provoked")

    report, ran = await _run(world)
    assert ran == ["current_price"]
    assert _held(world, "current_price") == (1, start + _seconds(60))

    report, ran = await _run(world, _utc(8, 23, 0))
    assert ran == ["history_sync"]
    assert _outcome(report, "history_sync").status == "ok"
    assert _outcome(report, "current_price") == scheduler.JobOutcome("current_price", "not_due", retry_at=start + _seconds(60))
    print_success("price held a minute; the history ran at its slot")


# =============================================================================
# (E) THE OUTCOMES
# =============================================================================


@pytest.mark.asyncio
async def test_the_outcome_of_a_job_that_ran_carries_its_deferred_items_and_their_retry_in_utc(world: World) -> None:
    """SBO-009 — contract (E): both jobs run. The current price writes four items deferred and a ``retry_at`` 90 s on, stored with the offset of Rome: its outcome carries ``items_deferred`` 4 and ``retry_at`` that instant, in UTC, besides what it copied before. The history deferred nothing: 0 and None."""
    print_section("SBO-009: the outcome of a job that ran")
    start = world.wall.now
    retry = start + _seconds(90)
    world.writes["current_price"] = {"last_duration_s": 1.25, "last_status": "partial", "last_items_ok": 5, "last_items_err": 1, "last_error": None, "last_items_deferred": 4, "retry_at": retry.astimezone(ROME).isoformat()}

    report, ran = await _run(world)

    assert ran == list(JOBS)
    assert report.jobs == (
        scheduler.JobOutcome("current_price", "partial", started_at=start, duration_s=1.25, items_ok=5, items_err=1, error=None, items_deferred=4, retry_at=retry),
        scheduler.JobOutcome("history_sync", "ok", started_at=start, duration_s=3.5, items_ok=40, items_err=0, error=None, items_deferred=0, retry_at=None),
    )
    _assert_utc(_outcome(report, "current_price").retry_at, "the outcome's retry_at")
    print_success("items_deferred and retry_at copied, retry_at in UTC")


#: ``next_attempt_at`` and ``retry_at`` of a job not due by the regular rule, in seconds from now (None absent,
#: ``UNREADABLE`` as stored), and which of the two its outcome reports as pending.
PENDING = [
    pytest.param(300, None, "next", id="held"),
    pytest.param(300, -30, "next", id="held-though-the-retry-passed"),
    pytest.param(300, 600, "next", id="held-the-retry-later"),
    pytest.param(300, 120, "next", id="held-the-retry-earlier"),
    pytest.param(None, 120, "retry", id="a-retry-ahead"),
    pytest.param(-60, 120, "retry", id="hold-over-a-retry-ahead"),
    pytest.param(UNREADABLE, 120, "retry", id="an-unreadable-hold-a-retry-ahead"),
    pytest.param(None, None, None, id="nothing-pending"),
    pytest.param(-60, None, None, id="hold-over-nothing-pending"),
    pytest.param(UNREADABLE, UNREADABLE, None, id="both-unreadable"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("job", JOBS)
@pytest.mark.parametrize(("next_attempt", "retry", "pending"), PENDING)
async def test_a_job_not_due_reports_what_it_is_pending_until(world: World, job: str, next_attempt: int | str | None, retry: int | str | None, pending: str | None) -> None:
    """SBO-010 — contract (E): a job not due is ``JobOutcome(name, "not_due", retry_at=…)``, every other field at its default: ``next_attempt_at`` when it is ahead, whatever ``retry_at`` says; else ``retry_at`` when it is ahead; else None. A timestamp that cannot be read is no timestamp. The job is not run."""
    print_section(f"SBO-010: {job} not due, next attempt {next_attempt}, retry {retry} → {pending}")
    now = world.wall.now
    world.just_ran(_other(job))
    world.ran(job, now, last_status="ok", consecutive_failures=1 if next_attempt is not None else 0, retry_at=_at(now, retry), next_attempt_at=_at(now, next_attempt))
    expected = {"next": now + _seconds(300), "retry": now + _seconds(120), None: None}[pending]

    report, ran = await _run(world)

    assert ran == []
    assert _outcome(report, job) == scheduler.JobOutcome(job, "not_due", retry_at=expected)
    print_success(f"pending until {expected}")


@pytest.mark.asyncio
@pytest.mark.parametrize("job", JOBS)
async def test_a_job_with_deferred_items_runs_again_at_its_retry_before_its_regular_round(world: World, job: str) -> None:
    """SBO-011 — contracts (C) and (E) through the run: the job runs at T and defers two items until T+90 s, which its outcome reports. At T+89 s it is not due, pending until T+90 s; at T+90 s it runs again — its regular round would have waited for 10:10 or for the 23:00 slot —, deferring nothing; at T+91 s it is not due and nothing is pending."""
    print_section(f"SBO-011: {job} retried at its retry_at")
    start = world.wall.now
    world.just_ran(_other(job))
    world.ran(job, NEVER)
    world.writes[job] = {**WRITTEN[job], "last_status": "partial", "last_items_deferred": 2, "retry_at": (start + _seconds(90)).isoformat()}

    report, ran = await _run(world)
    assert ran == [job]
    assert (_outcome(report, job).items_deferred, _outcome(report, job).retry_at) == (2, start + _seconds(90))

    world.writes[job] = dict(WRITTEN[job])
    report, ran = await _run(world, start + _seconds(89))
    assert ran == []
    assert _outcome(report, job) == scheduler.JobOutcome(job, "not_due", retry_at=start + _seconds(90))

    report, ran = await _run(world, start + _seconds(90))
    assert ran == [job]

    report, ran = await _run(world, start + _seconds(91))
    assert ran == []
    assert _outcome(report, job) == scheduler.JobOutcome(job, "not_due")
    print_success("deferred at T, retried at T+90 s")


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", REASONS)
async def test_a_job_held_back_is_not_due_whatever_the_reason_of_the_run(world: World, reason: str) -> None:
    """SBO-012 — contracts (C) and (E): the current price failed an hour after its last run and is held for 30 s more; a run of any reason — a return and a wake-up included — does not run it and reports it not due, pending until its next attempt."""
    print_section(f"SBO-012: a {reason} run and a job held back")
    now = world.wall.now
    world.ran("current_price", now - timedelta(hours=1), last_status="error", last_error="ProviderExploded", consecutive_failures=1, next_attempt_at=(now + _seconds(30)).isoformat())
    world.just_ran("history_sync")

    report, ran = await _run(world, reason=reason)

    assert ran == []
    assert _outcome(report, "current_price") == scheduler.JobOutcome("current_price", "not_due", retry_at=now + _seconds(30))
    print_success("held, whatever the reason")
