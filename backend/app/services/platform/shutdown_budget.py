"""The shutdown budget: the server stops within ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`` of a SIGTERM or a SIGINT.

Owner: workstream Z (decision 35, release 1.3: 8 seconds for every install; 0 removes the limit). Three layers share
the budget, counted from the signal:

1. uvicorn drains the requests in flight for 3/8 of it, then cancels them: ``UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN``, set
   by the launchers (``entrypoint.sh``, ``dev.py server``) from ``uvicorn_drain_env()``;
2. the lifespan runs its shutdown steps against one deadline, ``shutdown_deadline()``: each step gets the time left
   (``services/platform/lifecycle.py``), and the last one, ``child_processes_step()``, terminates the child processes
   still alive (parse workers, risk workers, a tool), so that none outlives the server;
3. a watchdog, armed by the first SIGTERM or SIGINT, ends the process when the budget runs out, whatever still holds
   it: a request uvicorn could not drain, a step that ignores cancellation, a thread the interpreter would wait for
   at exit (after a SIGINT, ``asyncio.run`` waits up to 300 s for the threads of its executor). It logs what it found,
   terminates the children, saves the coverage data when a test run measures it, and calls ``os._exit(1)``.

The watchdog exists only in a process uvicorn serves from its main thread: it wraps uvicorn's own exit handler
(``Server.handle_exit``), which still runs, and only a signal arms it, never a shutdown without one. Elsewhere nothing is
installed, so nothing ends the process and no child is terminated: the API tests run uvicorn in a thread of the pytest
process, and some tests run the lifespan itself in pytest's main thread. The shutdown steps still get a deadline there,
counted from the start of the shutdown.
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from types import FrameType

import psutil
from uvicorn.server import Server as UvicornServer

from backend.app.config.sleep_wake import DEFAULT_SHUTDOWN_TIMEOUT_SECONDS, SleepWakeConfigError, shutdown_drain_seconds, shutdown_timeout_seconds
from backend.app.logging_config import get_logger
from backend.app.services.platform import lifecycle

logger = get_logger(__name__)

#: The end of the budget kept for the last step, the child processes, before the watchdog fires.
CLEANUP_MARGIN_SECONDS = 0.75
#: How long a child process gets between ``terminate()`` and ``kill()``.
CHILD_TERMINATE_SECONDS = 0.5
#: How often the watchdog looks at its clock while it waits.
_POLL_SECONDS = 0.25

_reported: set[tuple[str, str]] = set()
_reported_lock = threading.Lock()
_state_lock = threading.Lock()
_watchdog: ShutdownWatchdog | None = None


def shutdown_budget_seconds() -> int:
    """The budget in force: the setting, or the default when it cannot be used (logged once per variable and problem)."""
    try:
        return shutdown_timeout_seconds()
    except SleepWakeConfigError as exc:
        with _reported_lock:
            first = (exc.variable, exc.code) not in _reported
            _reported.add((exc.variable, exc.code))
        if first:
            logger.error("Shutdown budget setting cannot be used: the default applies", variable=exc.variable, code=exc.code, reason=str(exc), budget_seconds=DEFAULT_SHUTDOWN_TIMEOUT_SECONDS)
        return DEFAULT_SHUTDOWN_TIMEOUT_SECONDS


def is_resource_tracker(process: psutil.Process) -> bool:
    """multiprocessing's resource tracker: it leaves with the server by itself, and ending it first only adds warnings."""
    try:
        return any("resource_tracker" in part for part in process.cmdline())
    except psutil.Error:
        return False


def terminate_child_processes(timeout: float, *, keep: Callable[[psutil.Process], bool] | None = None) -> list[int]:
    """Terminate the child processes of this one, recursively, but those ``keep`` accepts; kill those alive after ``timeout``.

    ``keep`` defaults to multiprocessing's resource tracker. Returns the pids that had to be killed.
    """
    accept = is_resource_tracker if keep is None else keep
    try:
        children = psutil.Process().children(recursive=True)
    except psutil.Error:
        return []
    targets = [child for child in children if not accept(child)]
    for child in targets:
        with contextlib.suppress(psutil.Error):
            child.terminate()
    _gone, alive = psutil.wait_procs(targets, timeout=max(0.0, timeout))
    killed: list[int] = []
    for child in alive:
        try:
            child.kill()
        except psutil.Error:
            continue
        killed.append(child.pid)
    if alive:
        psutil.wait_procs(alive, timeout=CHILD_TERMINATE_SECONDS)
    return killed


def _kill_every_child(timeout: float) -> None:
    terminate_child_processes(timeout, keep=lambda _process: False)


def _survivors() -> dict[str, list[str]]:
    threads = sorted(thread.name for thread in threading.enumerate() if thread is not threading.current_thread())
    try:
        children = [f"{child.pid} {child.name()}" for child in psutil.Process().children(recursive=True)]
    except psutil.Error:
        children = []
    return {"threads": threads, "children": children}


def _save_coverage() -> None:
    """Save the coverage data of a measured test run: ``os._exit`` skips the handlers that would."""
    coverage = sys.modules.get("coverage")
    if coverage is None:
        return
    with contextlib.suppress(Exception):
        current = coverage.Coverage.current()
        if current is not None:
            current.stop()
            current.save()


def _flush_output() -> None:
    for handler in logging.getLogger().handlers:
        with contextlib.suppress(Exception):
            handler.flush()
    for stream in (sys.stdout, sys.stderr):
        with contextlib.suppress(Exception):
            stream.flush()


class ShutdownWatchdog:
    """Ends the process when the shutdown budget runs out, counted from ``arm()``."""

    def __init__(
        self,
        budget_seconds: float,
        *,
        clock: Callable[[], float] = time.monotonic,
        exit: Callable[[int], object] = os._exit,
        terminate_children: Callable[[float], object] = _kill_every_child,
        current_step: Callable[[], str | None] = lifecycle.current_step,
    ) -> None:
        if budget_seconds <= 0:
            raise ValueError("budget_seconds must be positive")
        self._budget = float(budget_seconds)
        self._clock = clock
        self._exit = exit
        self._terminate_children = terminate_children
        self._current_step = current_step
        # Set once by ``dict.setdefault``, a single call: a signal handler that arms again on the same thread, between
        # two bytecodes of an ``arm()`` in progress, cannot deadlock nor start a second thread. Each call offers a new
        # tuple, so the call whose tuple was kept is the one that starts the thread.
        self._armed: dict[str, tuple[float]] = {}
        self._fired = False
        self._fire_lock = threading.Lock()

    @property
    def budget_seconds(self) -> float:
        return self._budget

    @property
    def deadline(self) -> float | None:
        entry = self._armed.get("at")
        return None if entry is None else entry[0] + self._budget

    def arm(self) -> float:
        """Start counting, once: later calls change nothing. Returns the deadline, on the watchdog's clock."""
        offered = (self._clock(),)
        kept = self._armed.setdefault("at", offered)
        if kept is offered:
            threading.Thread(target=self._wait_then_fire, args=(kept[0] + self._budget,), name="shutdown-watchdog", daemon=True).start()
        return kept[0] + self._budget

    def _wait_then_fire(self, deadline: float) -> None:
        while (left := deadline - self._clock()) > 0:
            time.sleep(min(left, _POLL_SECONDS))
        self.fire()

    def fire(self) -> None:
        """Report, terminate the children, save the coverage, flush, and end the process with status 1. Once."""
        with self._fire_lock:
            if self._fired:
                return
            self._fired = True
        # Nothing may stop the exit: neither a report that fails nor a child that cannot be ended.
        with contextlib.suppress(Exception):
            logger.error("Shutdown budget exhausted: ending the process", budget_seconds=self._budget, step=self._current_step(), **_survivors())
        with contextlib.suppress(Exception):
            self._terminate_children(CHILD_TERMINATE_SECONDS)
        _save_coverage()
        _flush_output()
        self._exit(1)


def _arming_handler(watchdog: ShutdownWatchdog, previous: Callable[[int, FrameType | None], object]) -> Callable[[int, FrameType | None], None]:
    def handler(signum: int, frame: FrameType | None) -> None:
        watchdog.arm()
        previous(signum, frame)

    return handler


def _is_uvicorn_exit_handler(handler: object) -> bool:
    """Whether ``handler`` is the exit handler a uvicorn server installs while it serves: ``Server.handle_exit``."""
    return isinstance(getattr(handler, "__self__", None), UvicornServer) and getattr(handler, "__name__", "") == "handle_exit"


def install_shutdown_watchdog(*, budget_seconds: int | None = None) -> ShutdownWatchdog | None:
    """Arm a watchdog at the first SIGTERM or SIGINT of a uvicorn server, wrapping uvicorn's exit handler, which still runs.

    Only in a process uvicorn serves from its main thread: SIGTERM must be handled by uvicorn's ``Server.handle_exit``,
    and SIGINT is wrapped too when uvicorn handles it. Nothing with no limit (budget 0), off the main thread (a server in
    a thread of another process, as in the API tests) or under any other handler (a test running the lifespan in pytest's
    main thread). Returns the watchdog installed, or None.
    """
    global _watchdog
    budget = shutdown_budget_seconds() if budget_seconds is None else budget_seconds
    if budget <= 0 or threading.current_thread() is not threading.main_thread():
        return None
    if not _is_uvicorn_exit_handler(signal.getsignal(signal.SIGTERM)):
        return None
    watchdog = ShutdownWatchdog(budget)
    for signum in (signal.SIGTERM, signal.SIGINT):
        previous = signal.getsignal(signum)
        if _is_uvicorn_exit_handler(previous):
            signal.signal(signum, _arming_handler(watchdog, previous))
    with _state_lock:
        _watchdog = watchdog
    logger.debug("Shutdown watchdog installed", budget_seconds=budget)
    return watchdog


def shutdown_deadline(*, clock: Callable[[], float] = time.monotonic) -> float | None:
    """The deadline of the shutdown steps, absolute on the monotonic clock; None with no limit.

    After a signal, the armed watchdog's deadline less ``CLEANUP_MARGIN_SECONDS``. Otherwise (a shutdown without a
    signal, or no watchdog in this process) now plus the budget less uvicorn's drain share, counted afresh at each call:
    the lifespan calls it once per shutdown. It never arms the watchdog, so a process that stops its app without a
    signal (a test, a server that reached its request limit) is never ended by it.
    """
    watchdog = _watchdog
    if watchdog is not None and watchdog.deadline is not None:
        return watchdog.deadline - CLEANUP_MARGIN_SECONDS
    budget = shutdown_budget_seconds()
    if budget == 0:
        return None
    return clock() + budget - (shutdown_drain_seconds(budget) or 0)


def _terminate_leftover_children() -> None:
    if _watchdog is None:
        return
    killed = terminate_child_processes(CHILD_TERMINATE_SECONDS)
    if killed:
        logger.warning("Child processes killed at shutdown: they ignored the request to stop", pids=killed)


def child_processes_step() -> lifecycle.Step:
    """The last shutdown step: terminate the child processes still alive, only in a process uvicorn serves (a watchdog)."""
    return lifecycle.Step("child-processes", _terminate_leftover_children)
