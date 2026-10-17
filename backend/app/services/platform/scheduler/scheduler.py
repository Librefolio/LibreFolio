"""The market-data scheduler: an asyncio loop in the app's process, and the one way to run the jobs that are due.

Owner: workstream Z (release 1.3). ``run_due_jobs(reason)`` runs the jobs that are due, one run at a time in this
process: at startup (``"startup"``), at the loop's tick every 60 s (``"tick"``), on the user's return after a silence
(``"return"``), and for a scheduled wake-up (``"wake"``, the route ``wake-sync``). Each job runs in a ``try`` of its
own and reports a generic ``JobOutcome``, so a future job (notifications, say) is one more entry. The whole run is
busy work (``ACTIVITY.busy("scheduler")``): the idle monitor never suspends the machine in the middle of it.

Nothing runs with the scheduler off (``LIBREFOLIO_NO_SCHEDULER`` or the setting) or on a blocked instance
(``LIBREFOLIO_BLOCKED``: a blocked instance does not update its prices). With several workers any of them may run the
jobs, one run at a time for the data directory: a run holds the lock of ``run_lock.py`` from the moment it reads the
state, and one that waited reads what the first one saved (Z-11). Where that lock is not available (no ``fcntl``:
Windows), only the leader worker runs them, and another answers ``not_leader``. A run waits at most
``LOCK_WAIT_SECONDS`` (ten minutes) for another run, of this process or of another: then it runs nothing, logs a
warning and answers ``not_leader`` as well, and the next tick tries again (Z-26). The jobs themselves have no limit.

After a Fly resume the wall clock is corrected within a few hundred milliseconds, and a request may be served before:
a run for ``"return"`` or ``"wake"`` waits ``CLOCK_SETTLE_SECONDS`` before it reads the time. A history-sync slot missed
while the machine slept or the server was off is due at the next run (``due_history_sync``), not at the next slot.

A catch-up — a run at startup, on a return or for a wake-up — is what a user waits for: ``PRICE_REFRESH`` follows it,
from the moment it is announced to the end of its run, and every ``/api/`` response says so in
``X-LibreFolio-Price-Refresh`` while it lasts. The web app then shows «Updating prices…» while one of its jobs runs
(``GET /system/price-refresh``, lot Z5). A regular tick is not followed.
"""

import asyncio
import threading
import time as time_module
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from typing import Literal, get_args
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog

from backend.app.config.platform import instance_blocked, scheduler_disabled
from backend.app.services.platform.scheduler.jobs import run_current_price_refresh, run_history_sync
from backend.app.services.platform.scheduler.leader import am_i_leader
from backend.app.services.platform.scheduler.run_lock import LOCK_WAIT_SECONDS, SchedulerRunLockTimeout, cross_process_lock_available, scheduler_run_lock
from backend.app.services.platform.scheduler.settings import SchedulerSettings, load_scheduler_settings
from backend.app.services.platform.scheduler.state import JobState, SchedulerState, load_state, save_state
from backend.app.services.platform.sleep_wake.activity import current_activity

logger = structlog.get_logger(__name__)

#: A user request after this much silence nudges the loop into a run now, instead of at its next tick.
CATCH_UP_AFTER_SECONDS = 60.0
#: How long a run for a return or a wake-up waits before reading the time: Fly corrects the clock after a resume.
CLOCK_SETTLE_SECONDS = 2.0
#: The loop's period.
TICK_SECONDS = 60.0
#: The wait before the first run, while the application finishes starting.
FIRST_RUN_DELAY_SECONDS = 5.0
#: How many days before today a missed history-sync slot is looked for: a week holds every configured day.
MISSED_SLOT_LOOKBACK_DAYS = 7
#: The name of the loop's return listener, and the reason it gives while a run is in progress.
CATCH_UP_LISTENER = "scheduler-catch-up"
BUSY_REASON = "scheduler"
#: The wait before a job that raised runs again, doubled at each failure in a row (release 1.3, Z7b).
FAILURE_BACKOFF_BASE_SECONDS = 60
#: The longest such wait for the history sync; the current price waits at most its own frequency.
FAILURE_BACKOFF_MAX_SECONDS = 3600

RunReason = Literal["startup", "tick", "return", "wake"]
#: The runs a user waits for (lot Z5): a startup, a return after a silence, a scheduled wake-up. A tick is not one.
CATCH_UP_REASONS: frozenset[str] = frozenset({"startup", "return", "wake"})
#: The response header that tells the web app a catch-up is about to run or runs.
PRICE_REFRESH_HEADER = "X-LibreFolio-Price-Refresh"
PriceRefreshState = Literal["idle", "starting", "running"]
_SETTLING_REASONS = frozenset({"return", "wake"})
_DAY_CODES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

_shutdown_event: asyncio.Event | None = None
_run_lock_of_loop: tuple[asyncio.AbstractEventLoop, asyncio.Lock] | None = None


@dataclass(frozen=True)
class JobOutcome:
    """How one job ended in a run: ``ok``, ``partial``, ``error`` or ``not_due``; ``error`` is a class name, if any.

    ``items_deferred`` counts the items a provider's pause deferred. ``retry_at`` is when the job runs again before its
    regular round: the end of the shortest pause, the end of the wait after a failure, or, for a job not due, the one
    of them still ahead.
    """

    name: str
    status: str
    started_at: datetime | None = None
    duration_s: float | None = None
    items_ok: int = 0
    items_err: int = 0
    error: str | None = None
    items_deferred: int = 0
    retry_at: datetime | None = None


@dataclass(frozen=True)
class RunReport:
    """One run: why, how it ended overall, when, and each job's outcome (none when no job could run)."""

    reason: str
    status: str
    started_at: datetime
    finished_at: datetime
    jobs: tuple[JobOutcome, ...] = ()


@dataclass(frozen=True)
class _Job:
    name: str
    due: Callable[[datetime, SchedulerSettings, SchedulerState], bool]
    run: Callable[[SchedulerState, SchedulerSettings], Awaitable[None]]
    state_of: Callable[[SchedulerState], JobState]
    max_backoff_seconds: Callable[[SchedulerSettings], float]


def utc_now() -> datetime:
    """The wall clock, in UTC."""
    return datetime.now(UTC)


async def settle_clock() -> None:
    """Give the wall clock ``CLOCK_SETTLE_SECONDS`` to be corrected after a resume."""
    await asyncio.sleep(CLOCK_SETTLE_SECONDS)


@dataclass(frozen=True)
class PriceRefreshProgress:
    """The catch-up of the prices as the web app sees it: ``starting`` from its announcement, ``running`` while a job
    runs, ``idle`` otherwise; and how the last catch-up that ran a job ended (``last_refreshed``: it updated an item)."""

    state: PriceRefreshState
    reason: str | None = None
    job: str | None = None
    since: datetime | None = None
    last_finished_at: datetime | None = None
    last_refreshed: bool = False


class PriceRefreshTracker:
    """The catch-up in progress in this process (lot Z5); thread-safe, in memory.

    A catch-up is pending from ``announce()`` (the loop's start, a return) or ``run_started()`` until the last run
    counted by ``run_started()`` ends. A job that finishes meanwhile counts for it, a tick's included: the user waits
    for the prices, whatever run brings them.
    """

    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._reason: str | None = None
        self._since: datetime | None = None
        self._runs = 0
        self._job: str | None = None
        self._ran = False
        self._refreshed = False
        self._last_finished_at: datetime | None = None
        self._last_refreshed = False

    @staticmethod
    def _require_catch_up(reason: str) -> None:
        if reason not in CATCH_UP_REASONS:
            raise ValueError(f"not a catch-up reason: {reason!r}")

    def _begin_locked(self, reason: str) -> None:
        if self._reason is None:
            self._reason = reason
            self._since = self._clock()
            self._ran = False
            self._refreshed = False

    def announce(self, reason: str) -> None:
        """A catch-up is about to run: idle turns ``starting``; a pending catch-up keeps its reason and its start."""
        self._require_catch_up(reason)
        with self._lock:
            self._begin_locked(reason)

    def run_started(self, reason: str) -> None:
        """A catch-up run starts: it is counted until ``run_finished()``, and begins a catch-up if none is pending."""
        self._require_catch_up(reason)
        with self._lock:
            self._runs += 1
            self._begin_locked(reason)

    def run_finished(self) -> None:
        """A counted run ended; at the last one the catch-up is over, and remembered if a job ran during it."""
        with self._lock:
            if self._runs == 0:
                return
            self._runs -= 1
            if self._runs > 0:
                return
            if self._reason is not None and self._ran:
                self._last_finished_at = self._clock()
                self._last_refreshed = self._refreshed
            self._reason = None
            self._since = None
            self._ran = False
            self._refreshed = False

    def job_started(self, name: str) -> None:
        """A job of any run starts: it is the current job until it finishes."""
        with self._lock:
            self._job = name

    def job_finished(self, items_ok: int | None) -> None:
        """The current job finished (``items_ok`` None: cancelled); while a catch-up is pending, it ran for it."""
        with self._lock:
            self._job = None
            if self._reason is not None:
                self._ran = True
                if items_ok is not None and items_ok > 0:
                    self._refreshed = True

    def snapshot(self) -> PriceRefreshProgress:
        """The state now: ``running`` while a catch-up is pending and a job runs, ``starting`` while it is pending."""
        with self._lock:
            if self._reason is None:
                return PriceRefreshProgress("idle", last_finished_at=self._last_finished_at, last_refreshed=self._last_refreshed)
            running = self._job is not None
            return PriceRefreshProgress(
                "running" if running else "starting",
                self._reason,
                self._job if running else None,
                self._since,
                self._last_finished_at,
                self._last_refreshed,
            )

    def header_value(self) -> str | None:
        """``starting`` or ``running`` for ``X-LibreFolio-Price-Refresh``; None while idle."""
        state = self.snapshot().state
        return None if state == "idle" else state

    def reset(self) -> None:
        """Back to idle, with no catch-up remembered, no run counted and no current job."""
        with self._lock:
            self._reason = None
            self._since = None
            self._runs = 0
            self._job = None
            self._ran = False
            self._refreshed = False
            self._last_finished_at = None
            self._last_refreshed = False


#: The process's catch-up, read by ``GET /system/price-refresh`` and by the response header.
PRICE_REFRESH = PriceRefreshTracker()


def price_refresh_progress() -> PriceRefreshProgress:
    """The process's catch-up, now."""
    return PRICE_REFRESH.snapshot()


def _scheduler_zoneinfo(tz_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _parse_last_run(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return _as_utc(datetime.fromisoformat(value))
    except (ValueError, TypeError):
        return None


def get_shutdown_event() -> asyncio.Event:
    """Get or create the shutdown event (singleton per process).

    Resets the event if it was previously set (e.g., after hot-reload).
    """
    global _shutdown_event
    if _shutdown_event is None or _shutdown_event.is_set():
        _shutdown_event = asyncio.Event()
    return _shutdown_event


def _retry_rule(job: JobState, now: datetime) -> bool | None:
    """The retry rules, before the regular one: a failure's wait holds the job back, a provider's pause brings it forward.

    False while ``next_attempt_at`` is ahead; True once ``retry_at`` has come; None when the regular rule decides.
    """
    now_utc = _as_utc(now)
    next_attempt = _parse_last_run(job.next_attempt_at)
    if next_attempt is not None and now_utc < next_attempt:
        return False
    retry_at = _parse_last_run(job.retry_at)
    if retry_at is not None and now_utc >= retry_at:
        return True
    return None


def _pending_retry_at(job: JobState, now: datetime) -> datetime | None:
    """For a job not due: the wait after a failure if still ahead, else a deferred retry still ahead, else None."""
    now_utc = _as_utc(now)
    for value in (job.next_attempt_at, job.retry_at):
        moment = _parse_last_run(value)
        if moment is not None and moment > now_utc:
            return moment
    return None


def due_current_price(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
    """Check if current-price refresh is due: the retry rules first (``_retry_rule``), then its frequency."""
    retry = _retry_rule(state.current_price, now)
    if retry is not None:
        return retry
    last = state.current_price.last_run_at
    if last is None:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except (ValueError, TypeError):
        return True
    return (now - last_dt) >= timedelta(minutes=settings.current_price_frequency_minutes)


def _slots_of_day(day: date, settings: SchedulerSettings, scheduler_tz: ZoneInfo) -> list[datetime]:
    """The history-sync slots of ``day`` in UTC; none when ``day`` is not a configured day."""
    if _DAY_CODES[day.weekday()] not in settings.history_sync_days:
        return []
    return [datetime.combine(day, slot, tzinfo=scheduler_tz).astimezone(UTC) for slot in settings.history_sync_times]


def _latest_slot_at_or_before(now_utc: datetime, settings: SchedulerSettings) -> datetime | None:
    """The most recent slot at or before ``now_utc``, today or in the ``MISSED_SLOT_LOOKBACK_DAYS`` before."""
    scheduler_tz = _scheduler_zoneinfo(settings.scheduler_timezone)
    today = now_utc.astimezone(scheduler_tz).date()
    for days_back in range(MISSED_SLOT_LOOKBACK_DAYS + 1):
        passed = [slot for slot in _slots_of_day(today - timedelta(days=days_back), settings, scheduler_tz) if slot <= now_utc]
        if passed:
            return max(passed)
    return None


def due_history_sync(now: datetime, settings: SchedulerSettings, state: SchedulerState) -> bool:
    """Check if a history-sync slot is due.

    After a run, the most recent slot of a configured day, today or in the week before, is due when it fell after that
    run: a slot missed while the server was off or asleep is caught up at the next run (decision D-Z3-1). Before any
    run, or with an unreadable one, only today's slots count. The retry rules (``_retry_rule``) come first.
    """
    retry = _retry_rule(state.history_sync, now)
    if retry is not None:
        return retry
    now_utc = _as_utc(now)
    last_dt = _parse_last_run(state.history_sync.last_run_at)
    if last_dt is None:
        scheduler_tz = _scheduler_zoneinfo(settings.scheduler_timezone)
        today = now_utc.astimezone(scheduler_tz).date()
        return any(slot <= now_utc for slot in _slots_of_day(today, settings, scheduler_tz))
    latest = _latest_slot_at_or_before(now_utc, settings)
    return latest is not None and last_dt < latest


JOBS: tuple[_Job, ...] = (
    _Job(
        "current_price",
        lambda now, settings, state: due_current_price(now, settings, state),
        lambda state, settings: run_current_price_refresh(state),
        lambda state: state.current_price,
        lambda settings: settings.current_price_frequency_minutes * 60,
    ),
    _Job(
        "history_sync",
        lambda now, settings, state: due_history_sync(now, settings, state),
        lambda state, settings: run_history_sync(state, horizon_days=settings.history_sync_horizon_days),
        lambda state: state.history_sync,
        lambda settings: FAILURE_BACKOFF_MAX_SECONDS,
    ),
)
JOB_NAMES = tuple(job.name for job in JOBS)


def _run_lock() -> asyncio.Lock:
    """The lock of the running event loop: one run at a time; a new loop (a test, a reload) gets a new lock."""
    global _run_lock_of_loop
    loop = asyncio.get_running_loop()
    if _run_lock_of_loop is None or _run_lock_of_loop[0] is not loop:
        _run_lock_of_loop = (loop, asyncio.Lock())
    return _run_lock_of_loop[1]


def _overall_status(outcomes: tuple[JobOutcome, ...]) -> str:
    ran = {outcome.status for outcome in outcomes if outcome.status != "not_due"}
    if not ran or ran == {"ok"}:
        return "ok"
    if ran == {"error"}:
        return "error"
    return "partial"


async def _run_job(job: _Job, reason: str, state: SchedulerState, settings: SchedulerSettings) -> JobOutcome:
    PRICE_REFRESH.job_started(job.name)
    outcome: JobOutcome | None = None
    try:
        outcome = await _run_job_body(job, reason, state, settings)
        return outcome
    finally:
        PRICE_REFRESH.job_finished(outcome.items_ok if outcome is not None else None)


async def _run_job_body(job: _Job, reason: str, state: SchedulerState, settings: SchedulerSettings) -> JobOutcome:
    started_at = utc_now()
    started = time_module.monotonic()
    try:
        await job.run(state, settings)
        await asyncio.to_thread(save_state, state)
    except Exception as exc:
        # The message stays in the log (secrets masked there), never in the outcome a caller may pass on.
        logger.exception("Scheduler job failed", job=job.name, reason=reason)
        duration_s = round(time_module.monotonic() - started, 2)
        failed = await _record_failure(job, state, settings, type(exc).__name__)
        return JobOutcome(job.name, "error", started_at, duration_s, error=type(exc).__name__, retry_at=_parse_last_run(failed.next_attempt_at))
    job_state = job.state_of(state)
    return JobOutcome(
        job.name,
        job_state.last_status or "ok",
        started_at,
        job_state.last_duration_s,
        job_state.last_items_ok,
        job_state.last_items_err,
        job_state.last_error,
        job_state.last_items_deferred,
        _parse_last_run(job_state.retry_at),
    )


async def _record_failure(job: _Job, state: SchedulerState, settings: SchedulerSettings, error: str) -> JobState:
    """Record a job that raised: one more failure in a row, and no new attempt before a doubling wait.

    ``last_run_at`` and ``last_duration_s`` stay those of the last run that ended, so a missed slot stays due; the wait
    starts at ``FAILURE_BACKOFF_BASE_SECONDS`` and stops at the job's ceiling. The state is saved; a save that fails
    again is only logged.
    """
    previous = job.state_of(state)
    failures = previous.consecutive_failures + 1
    wait = min(FAILURE_BACKOFF_BASE_SECONDS * 2 ** (failures - 1), job.max_backoff_seconds(settings))
    failed = replace(
        previous,
        last_status="error",
        last_error=error,
        consecutive_failures=failures,
        next_attempt_at=(utc_now() + timedelta(seconds=wait)).isoformat(),
    )
    setattr(state, job.name, failed)
    try:
        await asyncio.to_thread(save_state, state)
    except Exception:
        logger.exception("Scheduler state not saved after a failed job", job=job.name)
    return failed


def _log_gave_up(reason: str, lock: str, deadline: float) -> None:
    """The warning of a run that gave up waiting for another run (Z-26, N79): what an operator sees of a stuck run."""
    waited_s = round(time_module.monotonic() - deadline + LOCK_WAIT_SECONDS, 1)
    logger.warning("Scheduler run gave up waiting for another run", reason=reason, lock=lock, waited_s=waited_s, limit_s=LOCK_WAIT_SECONDS)


async def _run_within_deadline(reason: str) -> RunReport:
    """The run under this process's lock, its two waits for the locks ended by one deadline (Z-26, N79).

    The deadline, ``LOCK_WAIT_SECONDS`` from now, ends the wait for this process's lock, then the one for the lock
    across processes; never the jobs. A run that reaches it runs nothing and reads no state: it logs a warning and
    answers ``not_leader``, as another run holds the jobs, and the next tick tries again.
    """
    deadline = time_module.monotonic() + LOCK_WAIT_SECONDS
    lock = _run_lock()
    try:
        async with asyncio.timeout(max(0.0, deadline - time_module.monotonic())):
            await lock.acquire()
    except TimeoutError:
        _log_gave_up(reason, "process", deadline)
        now = utc_now()
        return RunReport(reason, "not_leader", now, now, ())
    try:
        return await _run_locked(reason, deadline)
    finally:
        lock.release()


async def _run_locked(reason: str, deadline: float) -> RunReport:
    started_at = utc_now()

    def report(status: str, jobs: tuple[JobOutcome, ...] = ()) -> RunReport:
        return RunReport(reason, status, started_at, utc_now(), jobs)

    if scheduler_disabled():
        return report("disabled")
    if instance_blocked():
        return report("blocked")
    cross_process = cross_process_lock_available()
    if not cross_process and not await asyncio.to_thread(am_i_leader):
        return report("not_leader")
    settings = await load_scheduler_settings()
    if not settings.scheduler_enabled:
        return report("disabled")
    if not cross_process:
        return report(*await _run_due(reason, settings))
    try:
        async with scheduler_run_lock(deadline=deadline):
            return report(*await _run_due(reason, settings))
    except SchedulerRunLockTimeout:
        _log_gave_up(reason, "data_dir", deadline)
        return report("not_leader")


async def _run_due(reason: str, settings: SchedulerSettings) -> tuple[str, tuple[JobOutcome, ...]]:
    """Read the state and the time, then run the jobs that are due, in order: the overall status and each outcome.

    Under the lock across processes the state is read once the lock is held, so a run that waited for another
    process's run sees what that one saved, and finds its jobs not due.
    """
    state = await asyncio.to_thread(load_state)
    now = utc_now()
    outcomes: list[JobOutcome] = []
    for job in JOBS:
        if job.due(now, settings, state):
            outcomes.append(await _run_job(job, reason, state, settings))
        else:
            outcomes.append(JobOutcome(job.name, "not_due", retry_at=_pending_retry_at(job.state_of(state), now)))
    jobs = tuple(outcomes)
    return _overall_status(jobs), jobs


async def run_due_jobs(reason: RunReason) -> RunReport:
    """Run the jobs that are due, one run at a time in this process and for the data directory, and report how each ended.

    A run for a return or a wake-up first gives the clock ``CLOCK_SETTLE_SECONDS``. The run is busy work from start to
    end, the waits for the locks included: this process's, then the one across processes (``run_lock.py``). A job that raises is reported as ``error`` with its class name, and the next
    job still runs; a cancellation goes through. After the settle, one deadline, ``LOCK_WAIT_SECONDS`` away, ends the
    two waits: a run that reaches it gives up and answers ``not_leader`` (Z-26).
    """
    if reason not in get_args(RunReason):
        raise ValueError(f"unknown scheduler run reason {reason!r}")
    catch_up = reason in CATCH_UP_REASONS
    if catch_up:
        PRICE_REFRESH.run_started(reason)
    try:
        with current_activity().busy(BUSY_REASON):
            if reason in _SETTLING_REASONS:
                await settle_clock()
            result = await _run_within_deadline(reason)
    finally:
        if catch_up:
            PRICE_REFRESH.run_finished()
    ran = [outcome.name for outcome in result.jobs if outcome.status != "not_due"]
    log = logger.info if ran else logger.debug
    log("Scheduler run finished", reason=reason, status=result.status, jobs=ran)
    return result


async def _wait(shutdown_event: asyncio.Event, nudge: asyncio.Event, seconds: float) -> bool:
    """Wait ``seconds``, a nudge or the shutdown; True when nudged and not shutting down."""
    waiters = [asyncio.ensure_future(shutdown_event.wait()), asyncio.ensure_future(nudge.wait())]
    try:
        await asyncio.wait(waiters, timeout=seconds, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for waiter in waiters:
            waiter.cancel()
        await asyncio.gather(*waiters, return_exceptions=True)
    return nudge.is_set() and not shutdown_event.is_set()


async def scheduler_loop(shutdown_event: asyncio.Event) -> None:
    """The scheduler's loop, an asyncio task of the app (``app_lifespan``) until ``shutdown_event`` is set.

    A first run (``"startup"``) after ``FIRST_RUN_DELAY_SECONDS``, then one every ``TICK_SECONDS`` (``"tick"``), and
    one at once (``"return"``) when a user request ends at least ``CATCH_UP_AFTER_SECONDS`` of silence: after a Fly
    resume the loop's own timer, on the monotonic clock, did not count the time asleep. A run that raises is logged and
    the loop goes on. Disabled entirely when ``LIBREFOLIO_NO_SCHEDULER`` is set (test servers, the gallery).
    """
    if scheduler_disabled():
        logger.info("Scheduler disabled via LIBREFOLIO_NO_SCHEDULER — loop not started")
        return

    loop = asyncio.get_running_loop()
    nudge = asyncio.Event()

    def on_return(_silence: float) -> None:
        PRICE_REFRESH.announce("return")
        loop.call_soon_threadsafe(nudge.set)

    activity = current_activity()
    activity.register_return_listener(CATCH_UP_LISTENER, CATCH_UP_AFTER_SECONDS, on_return)
    activity.register_response_header(PRICE_REFRESH_HEADER, PRICE_REFRESH.header_value)
    PRICE_REFRESH.announce("startup")
    logger.info("Scheduler loop started")
    try:
        await _wait(shutdown_event, nudge, FIRST_RUN_DELAY_SECONDS)
        reason: RunReason = "startup"
        while not shutdown_event.is_set():
            nudge.clear()
            try:
                await run_due_jobs(reason)
            except Exception:
                logger.exception("Scheduler run failed", reason=reason)
            reason = "return" if await _wait(shutdown_event, nudge, TICK_SECONDS) else "tick"
    finally:
        activity.remove_return_listener(CATCH_UP_LISTENER)
        activity.remove_response_header(PRICE_REFRESH_HEADER)
        PRICE_REFRESH.reset()
        logger.info("Scheduler loop stopped")
