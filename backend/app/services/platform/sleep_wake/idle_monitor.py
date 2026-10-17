"""The idle monitor: the machine asks to be suspended after N minutes without the user (workstream Z, release 1.3, F26).

Owner: workstream Z. Off unless ``LIBREFOLIO_IDLE_SUSPEND_MODE=fly``: a self-hosted install runs as before. With it, a
task of the app (``app_lifespan``: started after the scheduler, stopped first at shutdown) checks every
``IDLE_CHECK_SECONDS``: when nothing is busy (``ACTIVITY.busy_reasons()``: requests in flight, the scheduler's run, the
tools' pending jobs, a backup) and no request of the user has arrived for ``LIBREFOLIO_IDLE_SUSPEND_MINUTES`` (5 by
default; the probes and the scheduled wake-up do not count), it asks Fly to suspend the machine (``suspend.py``).
After the jobs of a scheduled wake-up a check comes at once (``request_idle_check``), so a machine woken with nobody
around goes back to sleep. A suspension that fails is logged as a warning and tried again after a growing wait, up to
``FAILURE_BACKOFF_MAX_SECONDS`` (decision D-S3). After a suspension the next check waits ``RESUME_GRACE_SECONDS``: when
the machine is resumed, the request that woke it must count first.

The frontend stops polling in a hidden tab and after a few minutes without input (Z1), so an open tab nobody looks at
does not keep the machine awake; the polling of a tab in use does, as the user's presence.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable

from backend.app.config.sleep_wake import DEFAULT_IDLE_SUSPEND_MINUTES, SleepWakeConfigError, idle_suspend_minutes, idle_suspend_mode
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup.jobs import backup_in_progress
from backend.app.services.platform.sleep_wake.activity import Activity, current_activity
from backend.app.services.platform.sleep_wake.suspend import FlySuspender, SuspendError
from backend.app.services.tools.executor import get_tool_executor

logger = get_logger(__name__)

#: The period of the checks: the machine is suspended within the idle time plus this.
IDLE_CHECK_SECONDS = 30.0
#: The wait after a suspension (or a failed one) before the next check: the request that resumed the machine counts first.
RESUME_GRACE_SECONDS = 60.0
#: The wait after the first failed suspension of a streak, doubled at each one, up to the maximum (decision D-S3).
FAILURE_BACKOFF_FIRST_SECONDS = 30.0
FAILURE_BACKOFF_MAX_SECONDS = 600.0
#: The delay of the check after a scheduled wake-up: its request ends first.
WAKE_CHECK_DELAY_SECONDS = 2.0

CheckResult = str  # "busy" | "active" | "waiting" | "suspended" | "failed"


class IdleMonitor:
    """Checks the user's absence and the work in progress, and asks the suspender to suspend the machine."""

    def __init__(
        self,
        *,
        activity: Activity,
        suspender: FlySuspender,
        minutes: int,
        sleep: Callable[[float], Awaitable[object]] = asyncio.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.activity = activity
        self.suspender = suspender
        self.minutes = minutes
        self._sleep = sleep
        self._monotonic = monotonic
        #: No suspension is tried before this ``monotonic()`` instant, after a failure; None when none failed.
        self.retry_not_before: float | None = None
        self._failures = 0
        self._loop: asyncio.AbstractEventLoop | None = None
        self._wakeup: asyncio.Event | None = None
        self._check_timer: asyncio.TimerHandle | None = None

    async def check(self) -> CheckResult:
        """One check: ``waiting`` after a failure, ``busy``, ``active``, or the outcome of a suspension."""
        if self.retry_not_before is not None and self._monotonic() < self.retry_not_before:
            return "waiting"
        reasons = await asyncio.to_thread(self.activity.busy_reasons)
        if reasons:
            return "busy"
        idle = self.activity.idle_seconds()
        if idle < self.minutes * 60:
            return "active"
        logger.debug("Asking for the machine's suspension", idle_s=round(idle), minutes=self.minutes)
        try:
            await self.suspender.suspend()
        except SuspendError as exc:
            return self._failed(exc.reason)
        except Exception as exc:
            logger.debug("Idle suspend raised", error=type(exc).__name__)
            return self._failed("error")
        logger.info("Idle suspend requested", idle_s=round(idle), minutes=self.minutes)
        self._failures = 0
        self.retry_not_before = None
        return "suspended"

    def _failed(self, reason: str) -> CheckResult:
        self._failures += 1
        wait = min(FAILURE_BACKOFF_FIRST_SECONDS * 2 ** (self._failures - 1), FAILURE_BACKOFF_MAX_SECONDS)
        self.retry_not_before = self._monotonic() + wait
        if self._failures == 1:
            logger.warning("Idle suspend failed", reason=reason, retry_in_s=wait)
        else:
            logger.debug("Idle suspend failed again", reason=reason, retry_in_s=wait, failures=self._failures)
        return "failed"

    async def run(self, stop: asyncio.Event) -> None:
        """Check until ``stop`` is set: every ``IDLE_CHECK_SECONDS``, after a suspension ``RESUME_GRACE_SECONDS``."""
        self._loop = asyncio.get_running_loop()
        self._wakeup = asyncio.Event()
        while not stop.is_set():
            self._wakeup.clear()
            try:
                outcome = await self.check()
            except Exception:
                logger.exception("Idle check failed")
                outcome = "error"
            await self._wait(stop, RESUME_GRACE_SECONDS if outcome in ("suspended", "failed") else IDLE_CHECK_SECONDS)

    async def _wait(self, stop: asyncio.Event, seconds: float) -> None:
        assert self._wakeup is not None
        waiters = [asyncio.ensure_future(self._sleep(seconds)), asyncio.ensure_future(stop.wait()), asyncio.ensure_future(self._wakeup.wait())]
        try:
            await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for waiter in waiters:
                waiter.cancel()
            await asyncio.gather(*waiters, return_exceptions=True)

    def request_check(self, delay: float) -> None:
        """Run one check ``delay`` seconds from now, from any thread; requests before that check make one."""
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        try:
            loop.call_soon_threadsafe(self._arm_check, delay)
        except RuntimeError:  # the loop closed in between
            return

    def _arm_check(self, delay: float) -> None:
        if self._check_timer is not None or self._loop is None:
            return
        self._check_timer = self._loop.call_later(max(0.0, delay), self._fire_check)

    def _fire_check(self) -> None:
        self._check_timer = None
        if self._wakeup is not None:
            self._wakeup.set()


_running: tuple[IdleMonitor, asyncio.Event, asyncio.Task[None]] | None = None


def _mode() -> str:
    try:
        return idle_suspend_mode()
    except SleepWakeConfigError as exc:
        logger.error("Idle suspend mode cannot be used: the machine is never suspended", variable=exc.variable, code=exc.code, reason=str(exc))
        return "none"


def _minutes() -> int:
    try:
        return idle_suspend_minutes()
    except SleepWakeConfigError as exc:
        logger.error("Idle suspend minutes cannot be used: the default applies", variable=exc.variable, code=exc.code, reason=str(exc), minutes=DEFAULT_IDLE_SUSPEND_MINUTES)
        return DEFAULT_IDLE_SUSPEND_MINUTES


def start_idle_monitor() -> None:
    """Start the monitor when ``LIBREFOLIO_IDLE_SUSPEND_MODE=fly``; otherwise do nothing. Returns None: a startup step
    must not hand back a task that never ends, or the startup would wait for it (``lifecycle.run_startup_steps``)."""
    global _running
    mode = _mode()
    if mode != "fly":
        return None
    minutes = _minutes()
    activity = current_activity()
    activity.register_busy_check("tools", lambda: get_tool_executor().snapshot().pending > 0)
    activity.register_busy_check("backup", lambda: backup_in_progress())
    monitor = IdleMonitor(activity=activity, suspender=FlySuspender(), minutes=minutes)
    stop = asyncio.Event()
    task = asyncio.create_task(monitor.run(stop), name="idle-monitor")
    _running = (monitor, stop, task)
    logger.info("Idle monitor started", mode=mode, minutes=minutes)
    return None


def idle_monitor_task() -> asyncio.Task[None] | None:
    """The running monitor's task; None when none was started."""
    return _running[2] if _running is not None else None


def stop_idle_monitor() -> asyncio.Task[None] | None:
    """Ask the monitor to stop; its task is returned, for the shutdown runner to await. None when none was started."""
    if _running is None:
        return None
    _monitor, stop, task = _running
    stop.set()
    return task


def request_idle_check(delay: float = WAKE_CHECK_DELAY_SECONDS) -> None:
    """Ask the running monitor for a check ``delay`` seconds from now; nothing when no monitor runs."""
    if _running is not None:
        _running[0].request_check(delay)
