"""The shutdown budget: ``config.sleep_wake``, ``services.platform.shutdown_budget``, ``entrypoint.sh`` and the shutdown grace of the runner and of Playwright — the server exits within about 8 s of SIGTERM or SIGINT, for every install (plan phase01SleepWake §Z6b, decision 35, lot Z6b).

One variable sizes the budget. uvicorn drains the requests in flight for 3/8 of it, the lifespan's steps share what is
left, and in a process uvicorn serves from its main thread a watchdog armed by the first SIGTERM or SIGINT ends the
process with exit code 1 once the whole budget is spent, whatever still holds it. The contract pinned here:

1. ``config.sleep_wake``: ``DEFAULT_SHUTDOWN_TIMEOUT_SECONDS`` 8, ``SHUTDOWN_TIMEOUT_MIN_SECONDS`` 2,
   ``SHUTDOWN_TIMEOUT_MAX_SECONDS`` 600.
2. ``shutdown_timeout_seconds(environ=None)``: ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`` of ``environ`` — ``os.environ``,
   read at each call, when None —, stripped. Unset or blank is 8; "0" is 0, no limit; ASCII digits from 2 to 600,
   leading zeros allowed ("008" is 8); anything else is ``SleepWakeConfigError`` on that variable with
   ``SHUTDOWN_TIMEOUT_INVALID``.
3. ``shutdown_drain_seconds(budget)``: what uvicorn may spend draining the requests in flight,
   ``max(1, budget * 3 // 8)``; None for a budget of 0.
4. ``uvicorn_drain_env(environ=None)``: what a launcher adds to uvicorn's environment,
   ``{"UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "<drain>"}``; ``{}`` when that variable is already set and not blank — a
   value set by hand wins — and with a budget of 0. A budget that cannot be used counts as the default: it never raises,
   and never changes the mapping it reads.
5. ``entrypoint.sh``, run by a non-root user, exports that drain before it ``exec``s its command, which still runs: the
   cases of 4 that do not hinge on whitespace, through ``sh`` and, where installed, ``dash`` — the ``/bin/sh`` of the
   Debian-based Docker image.
6. The grace before a SIGKILL — ``SHUTDOWN_GRACE_PLAIN`` in ``scripts/test_runner/_server.py``, the plain
   ``gracefulShutdown`` timeout of ``frontend/playwright.config.ts`` — is at least the default budget plus 2 s; each
   coverage grace is at least its plain one.
7. ``shutdown_budget_seconds()``: ``shutdown_timeout_seconds()`` that never raises: an unusable value is 8, and is logged
   once per (variable, code) per process.
8. ``ShutdownWatchdog(budget_seconds, *, clock, exit, terminate_children, current_step)``: ``budget_seconds``;
   ``deadline`` is None until it is armed. ``arm()`` is idempotent: the first call fixes ``deadline = clock() + budget``
   and starts one daemon thread, "shutdown-watchdog", which calls ``fire()`` at the deadline; every call returns the
   deadline. ``arm()`` runs inside a signal handler, so a signal can run it again while it runs: no deadlock, still one
   thread.
9. ``fire()`` runs at most once, whoever calls it: an ERROR log naming the step in progress, the live threads and the
   child processes, written before they are terminated; ``terminate_children(0.5)``; the coverage data saved only when
   ``coverage`` is already imported and ``coverage.Coverage.current()`` exists; stdout, stderr and the logging handlers
   flushed; then ``exit(1)``, even when a step before it fails.
10. ``install_shutdown_watchdog(*, budget_seconds=None)``: a budget of None is ``shutdown_budget_seconds()``. A budget of
    0, or a thread other than the main one: None, no handler changed. Otherwise SIGTERM decides: unless its handler is
    uvicorn's exit handler — ``handle_exit`` bound to a ``uvicorn.Server``, of a subclass too —, None and no handler
    changed, whatever SIGINT has. Not uvicorn's: SIG_DFL with ``signal.default_int_handler`` on SIGINT, as in pytest's
    main thread; SIG_IGN; a function; another class's method, even one named ``handle_exit``; a uvicorn server's other
    method. With it, SIGTERM's handler, and SIGINT's when it is uvicorn's too, is replaced by a wrapper that arms the
    watchdog, then calls the handler it replaced with ``(signum, frame)``; any other SIGINT handler is left alone. The
    watchdog returned is the one the module keeps, ``shutdown_budget._watchdog``, which ``shutdown_deadline()`` (11)
    and the child-processes step (13) read; returning None, it installs none.
11. ``shutdown_deadline(*, clock=time.monotonic)``, on the monotonic clock. Once a signal armed the watchdog, its
    deadline minus ``CLEANUP_MARGIN_SECONDS``, 0.75, whatever the clock passed. Otherwise — no watchdog, or one no signal
    armed —: None with a budget of 0, else ``clock() + budget - drain``, counted afresh at each call, the clock and the
    variable read again. It never arms a watchdog: a shutdown that came without a signal ends no process.
12. ``terminate_child_processes(timeout, *, keep=None)``: every child process, recursively, except those ``keep``
    accepts — by default multiprocessing's resource tracker, ``resource_tracker`` in its command line — is terminated,
    given ``timeout`` seconds, then killed; it returns the pids it had to kill.
13. ``child_processes_step()``: a ``lifecycle.Step`` named "child-processes", the last step of the lifespan's shutdown.
    With no watchdog installed — in every process but a server under uvicorn — its ``run`` terminates nothing. What it
    does with one, terminating the children still alive, is pinned in a server process of its own by
    ``test_shutdown_budget_process.py`` (SDP-004), never in this one.

PURE: no database, no server, no lane port. An autouse fixture removes every ``LIBREFOLIO_SHUTDOWN_*`` and ``UVICORN_*``
the lane inherited; another puts a stand-in ``coverage`` in ``sys.modules``, so that no ``fire()`` saves the coverage
data of the run measuring this file; a third puts None in ``shutdown_budget._watchdog`` with ``monkeypatch``, which puts
back what it found once the test is over — the module has no function that forgets its watchdog, nor one that returns
it (N58): the tests read that attribute themselves, where ``shutdown_deadline()`` and the last step read it. The real
``os._exit`` and the default ``terminate_children`` never run in this process: every watchdog gets recorders instead.
``install_shutdown_watchdog`` accepts no injection, so the tests replace ``shutdown_budget.ShutdownWatchdog`` — the name
it builds through, looked up at call time — with a subclass that hands the recorders to the constructor, and refuse to
arm any other watchdog. Every watchdog a test arms fires on its recorders before the test ends. uvicorn's exit handler is
the ``handle_exit`` of a real ``uvicorn.Server``, never started, built with ``log_config=None``: uvicorn's default would
reconfigure this process's logging. SIGTERM's and SIGINT's handlers are saved and put back around each test that touches
them; a test leaves its stand-ins on the signals only while ``install_shutdown_watchdog`` looks at them, puts back those
it found, then calls the wrappers directly. No signal is ever delivered; one sent to this process in that short window
would reach the stand-in — uvicorn's records it on a server that never runs. The real children are short-lived
``python -I`` processes of the test, killed and reaped at its teardown; ``terminate_child_processes`` runs here with a
``keep`` that spares every process but the test's own — under the child-processes step, through a guard put in its
place —, and with its default ``keep`` only in a fresh interpreter (``sys.executable``, run in ``tmp_path``) — like the
once-per-process log and the watchdog's ERROR log.

Red until ``config/sleep_wake.py`` has the budget and ``services/platform/shutdown_budget.py`` exists: the module does
not import. Then the cases of ``entrypoint.sh`` stay red until it exports the drain, and the graces until the runner and
Playwright wait at least 10 s.
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import logging
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import threading
import time
import types
from collections.abc import Callable, Iterator
from pathlib import Path

import psutil
import pytest
import uvicorn

from backend.app.config.sleep_wake import (
    DEFAULT_SHUTDOWN_TIMEOUT_SECONDS,
    SHUTDOWN_TIMEOUT_MAX_SECONDS,
    SHUTDOWN_TIMEOUT_MIN_SECONDS,
    SleepWakeConfigError,
    shutdown_drain_seconds,
    shutdown_timeout_seconds,
    uvicorn_drain_env,
)
from backend.app.services.platform import lifecycle, shutdown_budget
from backend.app.services.platform.shutdown_budget import (
    CLEANUP_MARGIN_SECONDS,
    ShutdownWatchdog,
    child_processes_step,
    install_shutdown_watchdog,
    shutdown_budget_seconds,
    shutdown_deadline,
    terminate_child_processes,
)
from backend.test_scripts.test_utils import print_section, print_success
from scripts.test_runner import _server as test_runner_server

REPO_ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = REPO_ROOT / "entrypoint.sh"
PLAYWRIGHT_CONFIG = REPO_ROOT / "frontend" / "playwright.config.ts"

#: Written out, not imported: the fixture that empties the environment must not trust the module under test.
TIMEOUT_VARIABLE = "LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS"
DRAIN_VARIABLE = "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN"
TIMEOUT_INVALID = "SHUTDOWN_TIMEOUT_INVALID"
INHERITED_PREFIXES = ("LIBREFOLIO_SHUTDOWN_", "UVICORN_")
WATCHDOG_THREAD = "shutdown-watchdog"
#: The seconds ``fire()`` gives the children between SIGTERM and SIGKILL.
CHILDREN_GRACE = 0.5
HANDLED_SIGNALS = (signal.SIGTERM, signal.SIGINT)
START = 1_000.0
#: The step a watchdog built by ``install_shutdown_watchdog`` reports during these tests.
INSTALL_STEP = "sdb-install-step"

#: Values outside contract 2, each with an id: below the minimum, above the maximum, a word, a negative, a decimal, a
#: sign, Python's digit separator, a unit, non-ASCII digits, a number too long for a shell's arithmetic.
UNUSABLE_TIMEOUTS = [
    ("1", "1-below-the-minimum"),
    ("601", "601-above-the-maximum"),
    ("abc", "a-word"),
    ("-3", "negative"),
    ("2.5", "decimal"),
    ("+5", "sign"),
    ("1_0", "digit-separator"),
    ("8s", "unit"),
    ("\uff11\uff10", "non-ascii-digits"),
    ("99999999999999999999", "twenty-digits"),
]

#: ``(id, environment, the drain uvicorn_drain_env adds — None: nothing —, what the command entrypoint.sh runs reads)``.
DRAIN_CASES: list[tuple[str, dict[str, str], str | None, str]] = [
    ("unset", {}, "3", "3"),
    ("budget-8", {TIMEOUT_VARIABLE: "8"}, "3", "3"),
    ("budget-16", {TIMEOUT_VARIABLE: "16"}, "6", "6"),
    ("budget-2", {TIMEOUT_VARIABLE: "2"}, "1", "1"),
    ("budget-3", {TIMEOUT_VARIABLE: "3"}, "1", "1"),
    ("budget-600", {TIMEOUT_VARIABLE: "600"}, "225", "225"),
    ("budget-008", {TIMEOUT_VARIABLE: "008"}, "3", "3"),
    ("budget-0-no-limit", {TIMEOUT_VARIABLE: "0"}, None, "UNSET"),
    ("budget-empty", {TIMEOUT_VARIABLE: ""}, "3", "3"),
    # A budget that cannot be used counts as the default, 8, which drains 3.
    *((f"unusable-{case_id}", {TIMEOUT_VARIABLE: value}, "3", "3") for value, case_id in UNUSABLE_TIMEOUTS),
    # Set by hand, the drain wins whatever the budget.
    ("set-by-hand", {DRAIN_VARIABLE: "7"}, None, "7"),
    ("set-by-hand-budget-16", {DRAIN_VARIABLE: "7", TIMEOUT_VARIABLE: "16"}, None, "7"),
    ("set-by-hand-budget-0", {DRAIN_VARIABLE: "7", TIMEOUT_VARIABLE: "0"}, None, "7"),
    ("set-by-hand-budget-unusable", {DRAIN_VARIABLE: "7", TIMEOUT_VARIABLE: "abc"}, None, "7"),
    # Set but empty: as if unset.
    ("drain-empty", {DRAIN_VARIABLE: ""}, "3", "3"),
    ("drain-empty-budget-16", {DRAIN_VARIABLE: "", TIMEOUT_VARIABLE: "16"}, "6", "6"),
]
PYTHON_DRAIN_CASES = [
    *(pytest.param(environment, drain, id=case_id) for case_id, environment, drain, _ in DRAIN_CASES),
    # Whitespace, as config.sleep_wake strips it: the Python side only, the shell's is not pinned.
    pytest.param({TIMEOUT_VARIABLE: " 16 "}, "6", id="budget-16-stripped"),
    pytest.param({TIMEOUT_VARIABLE: "   "}, "3", id="budget-blank"),
    pytest.param({DRAIN_VARIABLE: "   "}, "3", id="drain-blank"),
]
SHELL_DRAIN_CASES = [pytest.param(environment, seen, id=case_id) for case_id, environment, _, seen in DRAIN_CASES]
#: What entrypoint.sh is given to run: it prints the drain it was handed, or UNSET.
PRINT_DRAIN = 'printf "%s" "${UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN-UNSET}"'
SHELLS = [pytest.param("sh", id="sh"), pytest.param("dash", id="dash")]

#: ``gracefulShutdown: {signal: 'SIGTERM', timeout: process.env.COVERAGE_BACKEND ? <coverage> : <plain>}``, spaces and
#: line breaks anywhere, numeric separators allowed.
GRACEFUL_SHUTDOWN = re.compile(r"gracefulShutdown\s*:\s*\{\s*signal\s*:\s*(['\"`])SIGTERM\1\s*,\s*timeout\s*:\s*process\.env\.COVERAGE_BACKEND\s*\?\s*(?P<coverage>[0-9][0-9_]*)\s*:\s*(?P<plain>[0-9][0-9_]*)\s*,?\s*\}")

#: The children's whole environment: no coverage start-up, no lane variable, nothing inherited but PATH.
CHILD_ENV = {"PATH": os.environ.get("PATH", os.defpath)}
#: Ignores SIGTERM, says so, then waits for its stdin to close: only SIGKILL — or the end of the test process, which
#: closes the pipe — ends it.
STUBBORN_CHILD = "import signal, sys; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready', flush=True); sys.stdin.read()"
#: Keeps SIGTERM's default action: a terminate() ends it.
COOPERATIVE_CHILD = "import signal, sys; signal.signal(signal.SIGTERM, signal.SIG_DFL); print('ready', flush=True); sys.stdin.read()"
#: Keeps SIGTERM's default action and answers each line it reads with ``alive <line>``: an answer proves that it still
#: runs, and that no SIGTERM reached it before the question.
ANSWERING_CHILD = "import signal, sys\nsignal.signal(signal.SIGTERM, signal.SIG_DFL)\nprint('ready', flush=True)\nfor line in sys.stdin:\n    print('alive', line.strip(), flush=True)\n"
#: Ignores SIGTERM and starts a grandchild that ignores it too and sleeps a minute at most; prints the grandchild's pid
#: once both are ready.
STUBBORN_PARENT = """
import signal, subprocess, sys
signal.signal(signal.SIGTERM, signal.SIG_IGN)
code = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); print('ready', flush=True); time.sleep(60)"
grandchild = subprocess.Popen([sys.executable, "-I", "-c", code], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
if grandchild.stdout.readline().strip() != "ready":
    sys.exit("the grandchild did not start")
print("ready", grandchild.pid, flush=True)
sys.stdin.read()
"""

PROBE_MARKER = "SHUTDOWN-BUDGET-PROBE "
#: The start of every probe: what is logged, through structlog (captured) or the standard library (a root handler at
#: WARNING and above), comes back as event dicts — the contract does not say which of the two the module uses.
PROBE_PRELUDE = """
import json, logging, os, subprocess, sys, threading

from structlog.testing import capture_logs


class StdlibRecords(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.events = []
        self.standard = set(vars(logging.makeLogRecord({})))

    def emit(self, record):
        event = {key: value for key, value in vars(record).items() if key not in self.standard}
        event.update(event=record.getMessage(), log_level=record.levelname.lower())
        self.events.append(event)


stdlib = StdlibRecords()
logging.getLogger().addHandler(stdlib)


def logged(events):
    return list(events) + stdlib.events
"""


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class ReentrantClock(FakeClock):
    """A fake clock whose first reading runs ``arm()`` of ``watchdog``: a signal handler running ``arm()`` again between two bytecodes of ``arm()``."""

    def __init__(self) -> None:
        super().__init__()
        self.watchdog: ShutdownWatchdog | None = None
        self.reentered = False

    def __call__(self) -> float:
        if self.watchdog is not None and not self.reentered:
            self.reentered = True
            self.watchdog.arm()
        return self.now


def _nothing_seen() -> None:
    """What a test that does not look records at each ``arm()``."""
    return None


class Effects:
    """What a watchdog does to the process, recorded in order instead of done: ``exit`` stands for ``os._exit``.

    The watchdogs ``install_shutdown_watchdog`` builds also read ``clock`` — the real one unless a test sets another
    before it installs — and append what ``seen_at_arm()`` returns to ``arms`` at each ``arm()``, before arming.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.exit_times: list[float] = []
        self.exited = threading.Event()
        self.clock: Callable[[], float] = time.monotonic
        self.seen_at_arm: Callable[[], object] = _nothing_seen
        self.arms: list[object] = []

    def exit(self, code: int) -> None:
        self.exit_times.append(time.monotonic())
        self.calls.append(("exit", code))
        self.exited.set()

    def terminate_children(self, timeout: float) -> list[int]:
        self.calls.append(("terminate_children", timeout))
        return []

    def of(self, kind: str) -> list[tuple[object, ...]]:
        return [call for call in self.calls if call[0] == kind]

    def wait_for_exit(self, seconds: float) -> None:
        assert self.exited.wait(seconds), f"the watchdog did not fire within {seconds} s; recorded so far: {self.calls}"


async def _never_served(scope: dict, receive: Callable, send: Callable) -> None:
    """The ASGI app of the uvicorn servers built here: none is ever started, so nothing calls it."""
    raise AssertionError("a uvicorn server built by test_shutdown_budget.py was started")


def _uvicorn_config() -> uvicorn.Config:
    """The configuration of a server that is never started. ``log_config=None``: building it leaves this process's logging as it is, where uvicorn's default would reconfigure its loggers."""
    return uvicorn.Config(app=_never_served, log_config=None)


def _uvicorn_server() -> uvicorn.Server:
    """A real uvicorn server, never started: its ``handle_exit`` is the exit handler uvicorn puts on SIGTERM and SIGINT while it serves."""
    return uvicorn.Server(_uvicorn_config())


class FrameRecordingServer(uvicorn.Server):
    """A subclass of uvicorn's server: its ``handle_exit`` records the signal and the frame it is given, then runs uvicorn's."""

    def __init__(self, config: uvicorn.Config) -> None:
        super().__init__(config)
        self.given: list[tuple[int, object]] = []

    def handle_exit(self, sig: int, frame: types.FrameType | None) -> None:
        self.given.append((sig, frame))
        super().handle_exit(sig, frame)


class ServerWithAnotherHandler(uvicorn.Server):
    """A uvicorn server with a signal handler of its own besides ``handle_exit``."""

    def on_signal(self, signum: int, frame: types.FrameType | None) -> None:
        """A uvicorn server's method that is not its exit handler."""


class NotUvicorn:
    """Not a uvicorn server, though one of its methods is named as uvicorn's exit handler."""

    def handle_exit(self, signum: int, frame: types.FrameType | None) -> None:
        """Named as uvicorn's handler, on another class."""

    def on_signal(self, signum: int, frame: types.FrameType | None) -> None:
        """Another class's handler."""


def _a_function(signum: int, frame: types.FrameType | None) -> None:
    """A handler that is a plain function."""


#: Handlers that are not uvicorn's exit handler, by kind, each built when a test asks for it.
NOT_UVICORN: dict[str, Callable[[], object]] = {
    "SIG_DFL": lambda: signal.SIG_DFL,
    "SIG_IGN": lambda: signal.SIG_IGN,
    "default_int_handler": lambda: signal.default_int_handler,
    "a-function": lambda: _a_function,
    "another-class-method": lambda: NotUvicorn().on_signal,
    "handle_exit-of-another-class": lambda: NotUvicorn().handle_exit,
    "another-method-of-a-uvicorn-server": lambda: ServerWithAnotherHandler(_uvicorn_config()).on_signal,
}


class CoverageRecorder:
    """Stands for a running ``coverage.Coverage``: ``stop`` and ``save`` recorded in the order of ``calls``."""

    def __init__(self, calls: list[tuple[object, ...]]) -> None:
        self.calls = calls

    def stop(self) -> None:
        self.calls.append(("coverage.stop",))

    def save(self) -> None:
        self.calls.append(("coverage.save",))


class FailingCoverage(CoverageRecorder):
    """A running measurement whose data cannot be saved."""

    def save(self) -> None:
        raise OSError("sdb: the coverage data cannot be written")


class RecordingStream(io.StringIO):
    """Stands for ``sys.stdout`` or ``sys.stderr``: what is written is kept, each flush recorded in ``calls``."""

    def __init__(self, name: str, calls: list[tuple[object, ...]]) -> None:
        super().__init__()
        self.label = name
        self.calls = calls

    def flush(self) -> None:
        self.calls.append((f"{self.label}.flush",))
        super().flush()


class RecordingHandler(logging.Handler):
    """A logging handler on the root logger: each record (by level) and each flush recorded in ``calls``."""

    def __init__(self, calls: list[tuple[object, ...]]) -> None:
        super().__init__(logging.NOTSET)
        self.calls = calls

    def emit(self, record: logging.LogRecord) -> None:
        self.calls.append(("log", record.levelno))

    def flush(self) -> None:
        self.calls.append(("handler.flush",))


class Children:
    """The processes a test starts, killed and reaped at its teardown whatever happened."""

    def __init__(self) -> None:
        self.started: list[subprocess.Popen[str]] = []
        self.adopted: list[psutil.Process] = []

    def start(self, code: str) -> subprocess.Popen[str]:
        process = subprocess.Popen([sys.executable, "-I", "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=CHILD_ENV, text=True)
        self.started.append(process)
        return process

    def adopt(self, pid: int) -> psutil.Process:
        """A grandchild, known by the pid its parent printed, killed at teardown too."""
        process = psutil.Process(pid)
        self.adopted.append(process)
        return process

    def reap(self) -> None:
        for process in self.adopted:
            with contextlib.suppress(psutil.Error):
                process.kill()
        for process in self.started:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)


def _texts(value: object) -> Iterator[str]:
    """Every piece of text in a decoded log event: its keys, and each leaf as ``str``."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _texts(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _texts(item)
    else:
        yield str(value)


def _holds(value: object, needle: str) -> bool:
    return any(needle in text for text in _texts(value))


def _holds_pid(value: object, pid: int) -> bool:
    """``pid`` appears in ``value`` as a whole number, not as the digits of a longer one."""
    pattern = re.compile(rf"(?<![0-9]){pid}(?![0-9])")
    return any(pattern.search(text) for text in _texts(value))


def _probe(code: str, tmp_path: Path, *args: str) -> dict:
    """Run ``code`` in a fresh interpreter, in ``tmp_path``, and return the JSON it printed after ``PROBE_MARKER``.

    Its environment is a copy of this one without the variables of this file: under ``--coverage`` it is measured too.
    """
    env = {name: value for name, value in os.environ.items() if not name.startswith(INHERITED_PREFIXES)}
    env["PYTHONPATH"] = os.pathsep.join(part for part in (str(REPO_ROOT), os.environ.get("PYTHONPATH")) if part)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    done = subprocess.run([sys.executable, "-c", code, *args], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=60, check=False)
    assert done.returncode == 0, f"the probe failed:\n{done.stdout}\n{done.stderr}"
    lines = [line for line in done.stdout.splitlines() if line.startswith(PROBE_MARKER)]
    assert len(lines) == 1, f"the probe printed no result:\n{done.stdout}\n{done.stderr}"
    return json.loads(lines[0].removeprefix(PROBE_MARKER))


def _watchdog(effects: Effects, budget: float, *, clock: Callable[[], float] = time.monotonic, step: str = "sdb-step") -> ShutdownWatchdog:
    """A watchdog whose every effect on the process is one of ``effects``' recorders."""
    return ShutdownWatchdog(budget, clock=clock, exit=effects.exit, terminate_children=effects.terminate_children, current_step=lambda: step)


def _watchdog_threads(started: list[threading.Thread]) -> list[threading.Thread]:
    return [thread for thread in started if thread.name == WATCHDOG_THREAD]


def _join(threads: list[threading.Thread], seconds: float = 5.0) -> None:
    """Every thread of ``threads`` ends within ``seconds``: no watchdog outlives its test."""
    deadline = time.monotonic() + seconds
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    assert not [thread.name for thread in threads if thread.is_alive()], f"still running after {seconds} s: {threads}"


def _install_step() -> str:
    return INSTALL_STEP


def _coverage_module(current: object | None) -> types.ModuleType:
    """A stand-in for the ``coverage`` package: ``coverage.Coverage.current()`` is ``current``."""
    module = types.ModuleType("coverage")

    class Coverage:
        @staticmethod
        def current() -> object | None:
            return current

    module.Coverage = Coverage
    return module


def _handlers() -> dict[int, object]:
    return {signum: signal.getsignal(signum) for signum in HANDLED_SIGNALS}


def _put_back(saved: dict[int, object]) -> None:
    """SIGTERM's and SIGINT's handlers as the test found them, at once."""
    for signum, handler in saved.items():
        signal.signal(signum, handler)


def _install(saved: dict[int, object], stand_ins: dict[int, object], *, budget_seconds: int | None = None) -> tuple[ShutdownWatchdog | None, dict[int, object]]:
    """Put each stand-in on its signal, call ``install_shutdown_watchdog(budget_seconds=…)``, read the handlers it left, then put back ``saved`` — whatever happened.

    The stand-ins stay on the signals only while ``install_shutdown_watchdog`` looks at them: the wrappers it built are
    then called directly, no longer installed. Returns what it returned and the handlers read.
    """
    for signum, handler in stand_ins.items():
        signal.signal(signum, handler)
    try:
        return install_shutdown_watchdog(budget_seconds=budget_seconds), _handlers()
    finally:
        _put_back(saved)


def _injected(watchdog: object, injected: type[ShutdownWatchdog]) -> ShutdownWatchdog:
    """The watchdog ``install_shutdown_watchdog`` returned, once proven to run on the recorders; otherwise the test stops before anything can arm it."""
    if watchdog is None:
        pytest.fail("install_shutdown_watchdog() returned None on the main thread, with a budget above 0 and uvicorn's exit handler on SIGTERM")
    if type(watchdog) is not injected:
        pytest.fail(
            f"install_shutdown_watchdog() returned {watchdog!r}, not the {injected.__name__} put in place of shutdown_budget.ShutdownWatchdog: it must build its "
            "watchdog through that module name, looked up at each call — the only seam that lets a test fake os._exit. Nothing was armed: a watchdog on "
            "the real os._exit would end this test process."
        )
    return watchdog


def _installed_watchdog() -> ShutdownWatchdog | None:
    """The watchdog this process has installed, looked up at each call in ``shutdown_budget._watchdog`` — the attribute ``shutdown_deadline()`` and the child-processes step read —: the module has no function that returns it (N58), so the test reads it there."""
    return shutdown_budget._watchdog


def _ready(process: subprocess.Popen[str], seconds: float = 10.0) -> list[str]:
    """The words after ``ready`` on the first line ``process`` prints, waited for ``seconds`` at most."""
    readable, _, _ = select.select([process.stdout], [], [], seconds)
    assert readable, f"pid {process.pid} printed nothing in {seconds} s"
    line = process.stdout.readline()
    words = line.split()
    stderr = process.stderr.read() if process.poll() is not None else ""
    assert words[:1] == ["ready"], f"pid {process.pid} did not start: {line!r} {stderr}"
    return words[1:]


def _answer(process: subprocess.Popen[str], question: str, seconds: float = 10.0) -> str:
    """What ``process`` answers to ``question``, a line on its stdin, waited for ``seconds`` at most; empty once it has ended."""
    with contextlib.suppress(BrokenPipeError):
        process.stdin.write(f"{question}\n")
        process.stdin.flush()
    readable, _, _ = select.select([process.stdout], [], [], seconds)
    assert readable, f"pid {process.pid} did not answer in {seconds} s"
    return process.stdout.readline().strip()


def _assert_gone(process: subprocess.Popen[str] | psutil.Process, seconds: float = 5.0) -> None:
    """``process`` has ended within ``seconds`` — reaped already, or reaped now by whoever is its parent."""
    try:
        process.wait(timeout=seconds)
    except (subprocess.TimeoutExpired, psutil.TimeoutExpired):
        pytest.fail(f"pid {process.pid} still runs {seconds} s after terminate_child_processes() returned")


@pytest.fixture(autouse=True)
def _no_inherited_shutdown_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SHUTDOWN_*`` and ``UVICORN_*`` the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _coverage_stand_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """``coverage`` is a stand-in without a current measurement: no ``fire()`` saves the coverage data of the run measuring this file."""
    monkeypatch.setitem(sys.modules, "coverage", _coverage_module(None))


@pytest.fixture(autouse=True)
def _fresh_budget_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """No installed watchdog while each test runs: ``shutdown_budget._watchdog`` is None, put there with ``monkeypatch``, which puts back what it found once the test is over — the module has no function that forgets it (N58). The handlers are ``signal_handlers``' business."""
    monkeypatch.setattr(shutdown_budget, "_watchdog", None)


@pytest.fixture
def effects() -> Effects:
    return Effects()


@pytest.fixture
def started_threads(monkeypatch: pytest.MonkeyPatch) -> list[threading.Thread]:
    """Every thread started during the test, in order: ``threading.Thread.start`` records it, then starts it."""
    started: list[threading.Thread] = []
    original = threading.Thread.start

    def start(thread: threading.Thread) -> None:
        started.append(thread)
        original(thread)

    monkeypatch.setattr(threading.Thread, "start", start)
    return started


@pytest.fixture
def signal_handlers() -> Iterator[dict[int, object]]:
    """SIGTERM's and SIGINT's handlers as the test found them, put back after it — and at once by ``_install``. Nothing here delivers a signal."""
    if threading.current_thread() is not threading.main_thread():
        pytest.skip("signal handlers can only be changed from the main thread")
    saved = _handlers()
    if any(handler is None for handler in saved.values()):
        pytest.skip(f"a handler that was not installed from Python cannot be put back: {saved}")
    yield saved
    _put_back(saved)


@pytest.fixture
def injected(monkeypatch: pytest.MonkeyPatch, effects: Effects) -> type[ShutdownWatchdog]:
    """``shutdown_budget.ShutdownWatchdog`` replaced by a subclass that hands ``effects``' recorders and clock to the constructor, whatever ``install_shutdown_watchdog`` passes, and records ``effects.seen_at_arm()`` at each ``arm()``, before arming."""

    class InjectedWatchdog(ShutdownWatchdog):
        def __init__(self, budget_seconds: float, **kwargs: object) -> None:
            kwargs.update(clock=effects.clock, exit=effects.exit, terminate_children=effects.terminate_children, current_step=_install_step)
            super().__init__(budget_seconds, **kwargs)

        def arm(self) -> float:
            effects.arms.append(effects.seen_at_arm())
            return super().arm()

    monkeypatch.setattr(shutdown_budget, "ShutdownWatchdog", InjectedWatchdog)
    return InjectedWatchdog


@pytest.fixture
def children() -> Iterator[Children]:
    owned = Children()
    yield owned
    owned.reap()


# =============================================================================
# 1-4. config.sleep_wake
# =============================================================================


def test_the_budget_constants() -> None:
    """SDB-001 — contract 1: 8 s by default; from 2 to 600, 0 apart."""
    print_section("SDB-001: shutdown budget constants")

    assert (DEFAULT_SHUTDOWN_TIMEOUT_SECONDS, SHUTDOWN_TIMEOUT_MIN_SECONDS, SHUTDOWN_TIMEOUT_MAX_SECONDS) == (8, 2, 600)
    print_success("8, 2, 600")


@pytest.mark.parametrize("value", [None, "", "   "], ids=["unset", "empty", "blank"])
def test_a_blank_budget_is_the_default(monkeypatch: pytest.MonkeyPatch, value: str | None) -> None:
    """SDB-002 — contract 2: unset, empty or blank is 8, an ``int``."""
    print_section(f"SDB-002: {TIMEOUT_VARIABLE}={value!r}")
    if value is not None:
        monkeypatch.setenv(TIMEOUT_VARIABLE, value)

    result = shutdown_timeout_seconds()
    assert result == 8 and type(result) is int
    print_success("8")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param("0", 0, id="0-no-limit"),
        pytest.param("2", 2, id="2-the-minimum"),
        pytest.param("3", 3, id="3"),
        pytest.param("8", 8, id="8"),
        pytest.param("008", 8, id="8-leading-zeros"),
        pytest.param(" 16 ", 16, id="16-stripped"),
        pytest.param("600", 600, id="600-the-maximum"),
        pytest.param("0600", 600, id="600-leading-zero"),
    ],
)
def test_the_budget_is_0_or_a_whole_number_from_2_to_600(monkeypatch: pytest.MonkeyPatch, value: str, expected: int) -> None:
    """SDB-003 — contract 2: "0" turns the limit off; ASCII digits from 2 to 600 are the budget, stripped, leading zeros allowed; an ``int``."""
    print_section(f"SDB-003: {TIMEOUT_VARIABLE}={value!r}")
    monkeypatch.setenv(TIMEOUT_VARIABLE, value)

    result = shutdown_timeout_seconds()
    assert result == expected and type(result) is int
    print_success(f"{expected}")


@pytest.mark.parametrize("value", [pytest.param(value, id=case_id) for value, case_id in UNUSABLE_TIMEOUTS])
def test_the_budget_refuses_anything_else(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """SDB-004 — contract 2: 1, 601, a word, a negative, a decimal, a sign, Python's digit separator, a unit, non-ASCII digits or twenty digits are ``SHUTDOWN_TIMEOUT_INVALID`` on the variable, never a guess."""
    print_section(f"SDB-004: {TIMEOUT_VARIABLE}={value!r}")
    monkeypatch.setenv(TIMEOUT_VARIABLE, value)

    with pytest.raises(SleepWakeConfigError) as caught:
        shutdown_timeout_seconds()
    assert (caught.value.variable, caught.value.code) == (TIMEOUT_VARIABLE, TIMEOUT_INVALID)
    assert TIMEOUT_VARIABLE in str(caught.value)
    print_success(TIMEOUT_INVALID)


def test_a_mapping_given_is_read_instead_of_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """SDB-005 — contract 2: a mapping given is the only one read — an empty one is the default, a read-only one works, its values follow the same rules —; None reads ``os.environ``, at each call."""
    print_section("SDB-005: environ given, or os.environ at each call")
    monkeypatch.setenv(TIMEOUT_VARIABLE, "abc")

    assert shutdown_timeout_seconds({}) == 8
    assert shutdown_timeout_seconds(types.MappingProxyType({TIMEOUT_VARIABLE: "16"})) == 16
    with pytest.raises(SleepWakeConfigError) as caught:
        shutdown_timeout_seconds({TIMEOUT_VARIABLE: "601"})
    assert (caught.value.variable, caught.value.code) == (TIMEOUT_VARIABLE, TIMEOUT_INVALID)

    monkeypatch.setenv(TIMEOUT_VARIABLE, "16")
    assert shutdown_timeout_seconds() == 16
    monkeypatch.setenv(TIMEOUT_VARIABLE, "4")
    assert shutdown_timeout_seconds(None) == 4
    monkeypatch.delenv(TIMEOUT_VARIABLE)
    assert shutdown_timeout_seconds() == 8
    print_success("the mapping given; else os.environ as it is at each call")


@pytest.mark.parametrize(("budget", "drain"), [(2, 1), (3, 1), (4, 1), (5, 1), (6, 2), (8, 3), (10, 3), (16, 6), (600, 225)])
def test_the_drain_is_three_eighths_of_the_budget_and_at_least_1(budget: int, drain: int) -> None:
    """SDB-006 — contract 3: 8 drains 3, 16 drains 6, 600 drains 225; 2 to 5 drain 1, the floor; an ``int``."""
    print_section(f"SDB-006: drain of {budget}")

    result = shutdown_drain_seconds(budget)
    assert result == drain and type(result) is int
    print_success(f"{drain}")


def test_every_budget_drains_by_the_formula_and_0_drains_nothing() -> None:
    """SDB-007 — contract 3: every budget from 2 to 600 drains ``max(1, budget * 3 // 8)`` — always less than the budget, which leaves the lifespan its share —; a budget of 0 drains None."""
    print_section("SDB-007: the drain of every budget")

    assert shutdown_drain_seconds(0) is None
    wrong = {budget: drain for budget in range(2, 601) if (drain := shutdown_drain_seconds(budget)) != max(1, budget * 3 // 8)}
    assert wrong == {}, f"budget: drain, against the formula: {wrong}"
    assert all(shutdown_drain_seconds(budget) < budget for budget in range(2, 601))
    print_success("599 budgets by the formula; 0 → None")


@pytest.mark.parametrize(("environment", "drain"), PYTHON_DRAIN_CASES)
def test_uvicorn_drain_env_adds_the_drain_unless_set_by_hand_or_unlimited(environment: dict[str, str], drain: str | None) -> None:
    """SDB-008 — contract 4: the drain of the budget, as text, under ``UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN``; nothing with a budget of 0 or a value set by hand; an unusable budget drains 3 without raising; a blank value is no value. The mapping read is left as it was."""
    print_section(f"SDB-008: uvicorn_drain_env({environment!r})")
    given = dict(environment)

    result = uvicorn_drain_env(given)
    assert result == ({} if drain is None else {DRAIN_VARIABLE: drain})
    assert type(result) is dict and result is not given
    assert given == environment, f"uvicorn_drain_env changed the mapping it read: {given}"
    print_success(f"{result}")


def test_uvicorn_drain_env_reads_the_process_environment_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """SDB-009 — contract 4: with no mapping, ``os.environ`` as it is at each call; it says what to add and sets nothing itself."""
    print_section("SDB-009: uvicorn_drain_env() on os.environ")

    assert uvicorn_drain_env() == {DRAIN_VARIABLE: "3"}
    monkeypatch.setenv(TIMEOUT_VARIABLE, "16")
    assert uvicorn_drain_env() == {DRAIN_VARIABLE: "6"}
    monkeypatch.setenv(TIMEOUT_VARIABLE, "abc")
    assert uvicorn_drain_env(None) == {DRAIN_VARIABLE: "3"}
    monkeypatch.setenv(DRAIN_VARIABLE, "7")
    assert uvicorn_drain_env() == {}
    monkeypatch.delenv(DRAIN_VARIABLE)
    monkeypatch.setenv(TIMEOUT_VARIABLE, "0")
    assert uvicorn_drain_env() == {}
    assert DRAIN_VARIABLE not in os.environ, "uvicorn_drain_env set the variable itself"
    print_success("3, 6, 3, then nothing by hand or without a limit")


# =============================================================================
# 5. entrypoint.sh
# =============================================================================


@pytest.mark.parametrize("shell", SHELLS)
@pytest.mark.parametrize(("environment", "seen"), SHELL_DRAIN_CASES)
def test_the_entrypoint_exports_the_drain_then_runs_its_command(tmp_path: Path, shell: str, environment: dict[str, str], seen: str) -> None:
    """SDB-010 — contract 5: the command ``entrypoint.sh`` execs reads the drain ``uvicorn_drain_env`` gives — UNSET where it gives nothing and no value was set — and exits 0.

    The environment is PATH, HOME and the case's variables only. ``dash`` is the ``/bin/sh`` of the Debian-based image: a
    bash-only construct, an octal "008" or a twenty-digit number must not stop the container from starting.
    """
    print_section(f"SDB-010: {shell} entrypoint.sh with {environment!r}")
    if os.geteuid() == 0:
        pytest.skip("run as root, entrypoint.sh takes the branch that execs gosu")
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} is not installed here")
    env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": os.environ.get("HOME", str(tmp_path)), **environment}

    done = subprocess.run([executable, str(ENTRYPOINT), "sh", "-c", PRINT_DRAIN], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30, check=False)
    assert done.returncode == 0, f"entrypoint.sh exited {done.returncode}:\n{done.stdout}\n{done.stderr}"
    assert done.stdout == seen, f"the command saw {DRAIN_VARIABLE}={done.stdout!r}, expected {seen!r}; stderr:\n{done.stderr}"
    print_success(f"{DRAIN_VARIABLE}={seen}")


# =============================================================================
# 6. THE GRACE BEFORE A SIGKILL
# =============================================================================


def test_the_runner_waits_for_the_whole_budget_before_a_sigkill() -> None:
    """SDB-011 — contract 6: the shared test backend gets its whole default budget plus 2 s after SIGTERM, more under coverage — otherwise «ignored SIGTERM» reports a server that was still within its budget."""
    print_section("SDB-011: SHUTDOWN_GRACE_PLAIN and SHUTDOWN_GRACE_COVERAGE")
    plain, coverage = test_runner_server.SHUTDOWN_GRACE_PLAIN, test_runner_server.SHUTDOWN_GRACE_COVERAGE

    assert plain >= DEFAULT_SHUTDOWN_TIMEOUT_SECONDS + 2, f"SHUTDOWN_GRACE_PLAIN is {plain} s, below the {DEFAULT_SHUTDOWN_TIMEOUT_SECONDS} s budget plus 2 s"
    assert coverage >= plain, f"SHUTDOWN_GRACE_COVERAGE ({coverage} s) is shorter than SHUTDOWN_GRACE_PLAIN ({plain} s)"
    print_success(f"{plain} s, {coverage} s under coverage")


def test_playwright_waits_for_the_whole_budget_before_a_sigkill() -> None:
    """SDB-012 — contract 6: the webServer Playwright starts gets the default budget plus 2 s after SIGTERM, in milliseconds, more under coverage. The pattern is read as text: if it is not found, the shape changed, and this guard must follow it rather than pass."""
    print_section("SDB-012: gracefulShutdown in frontend/playwright.config.ts")
    text = PLAYWRIGHT_CONFIG.read_text(encoding="utf-8")

    matches = list(GRACEFUL_SHUTDOWN.finditer(text))
    shape = "gracefulShutdown: {signal: 'SIGTERM', timeout: process.env.COVERAGE_BACKEND ? <coverage> : <plain>}"
    assert matches, f"the pattern changed: frontend/playwright.config.ts no longer has {shape} — update GRACEFUL_SHUTDOWN to the new shape"
    floor = (DEFAULT_SHUTDOWN_TIMEOUT_SECONDS + 2) * 1000
    for match in matches:
        coverage, plain = int(match["coverage"].replace("_", "")), int(match["plain"].replace("_", ""))
        assert plain >= floor, f"the plain gracefulShutdown timeout is {plain} ms, below {floor} ms"
        assert coverage >= plain, f"the coverage gracefulShutdown timeout ({coverage} ms) is shorter than the plain one ({plain} ms)"
    print_success(f"{len(matches)} webServer grace(s) of at least {floor} ms")


# =============================================================================
# 7. shutdown_budget_seconds
# =============================================================================


@pytest.mark.parametrize(
    ("value", "budget"),
    [
        pytest.param(None, 8, id="unset"),
        pytest.param("", 8, id="empty"),
        pytest.param("0", 0, id="0-no-limit"),
        pytest.param("2", 2, id="2"),
        pytest.param("16", 16, id="16"),
        pytest.param("600", 600, id="600"),
        *(pytest.param(value, 8, id=f"unusable-{case_id}") for value, case_id in UNUSABLE_TIMEOUTS),
    ],
)
def test_shutdown_budget_seconds_never_raises(monkeypatch: pytest.MonkeyPatch, value: str | None, budget: int) -> None:
    """SDB-013 — contract 7: the budget of contract 2, and 8 for every value contract 2 refuses — no exception."""
    print_section(f"SDB-013: shutdown_budget_seconds() with {TIMEOUT_VARIABLE}={value!r}")
    if value is not None:
        monkeypatch.setenv(TIMEOUT_VARIABLE, value)

    assert shutdown_budget_seconds() == budget
    print_success(f"{budget}")


def test_shutdown_budget_seconds_reads_the_environment_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """SDB-014 — contract 7: a change of the variable is seen by the next call, and so is its removal."""
    print_section("SDB-014: shutdown_budget_seconds() read at each call")

    monkeypatch.setenv(TIMEOUT_VARIABLE, "16")
    assert shutdown_budget_seconds() == 16
    monkeypatch.setenv(TIMEOUT_VARIABLE, "abc")
    assert shutdown_budget_seconds() == 8
    monkeypatch.setenv(TIMEOUT_VARIABLE, "4")
    assert shutdown_budget_seconds() == 4
    monkeypatch.delenv(TIMEOUT_VARIABLE)
    assert shutdown_budget_seconds() == 8
    print_success("16, 8, 4, 8")


#: The probe's steps — the variable's value, None leaving it unset — with the budgets expected and the fault events so far.
BUDGET_LOG_STEPS = [
    ("abc", 8, 1),  # SHUTDOWN_TIMEOUT_INVALID, the first time in the process: logged
    ("1", 8, 1),  # the same variable and code with another value: not again
    ("601", 8, 1),  # idem
    (None, 8, 1),  # unset: nothing to report
    ("16", 16, 1),  # valid: nothing to report
    ("-3", 8, 1),  # invalid again, still the same variable and code
]

#: Runs in the child, a fresh interpreter where nothing was logged yet. argv[1]: the JSON list of the steps' values.
BUDGET_LOG_PROBE = PROBE_PRELUDE + """
from backend.app.services.platform.shutdown_budget import shutdown_budget_seconds

name = "LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS"
levels = ("warning", "error", "critical")
budgets, faults_after_step = [], []
with capture_logs() as events:
    for value in json.loads(sys.argv[1]):
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
        budgets.append([shutdown_budget_seconds() for _ in range(3)])
        faults_after_step.append(sum(1 for event in logged(events) if event.get("log_level") in levels and name in json.dumps(event, default=repr)))
faults = [event for event in logged(events) if event.get("log_level") in levels]
print("RESULT_MARKER" + json.dumps({"budgets": budgets, "faults_after_step": faults_after_step, "faults": faults}, default=repr))
""".replace("RESULT_MARKER", PROBE_MARKER)


def test_an_unusable_budget_is_logged_once_per_variable_and_code_per_process(tmp_path: Path) -> None:
    """SDB-015 — contract 7: in a fresh interpreter, four unusable values, each read three times, among an unset and a valid one: one event at WARNING or above names the variable, at the first unusable value, and every read gives 8 until the valid 16.

    A fresh interpreter, because "once per process" can only start over in a new one: in this process an earlier test
    may have logged the same fault already. The level is not pinned, only that the fault is reported, once.
    """
    print_section("SDB-015: logged once per (variable, code) per process")

    result = _probe(BUDGET_LOG_PROBE, tmp_path, json.dumps([value for value, _, _ in BUDGET_LOG_STEPS]))
    assert result["budgets"] == [[budget] * 3 for _, budget, _ in BUDGET_LOG_STEPS], "barrier: every step ran, the unusable ones on the default"
    assert result["faults_after_step"] == [count for _, _, count in BUDGET_LOG_STEPS], result["faults"]
    print_success("one fault event, at the first unusable value")


# =============================================================================
# 8. ShutdownWatchdog: arming
# =============================================================================


@pytest.mark.parametrize("budget", [0.25, 8])
def test_a_new_watchdog_is_not_armed(effects: Effects, started_threads: list[threading.Thread], budget: float) -> None:
    """SDB-016 — contract 8: ``budget_seconds`` as given; no ``deadline``, no thread and no effect until ``arm()``."""
    print_section(f"SDB-016: ShutdownWatchdog({budget})")

    watchdog = _watchdog(effects, budget)
    assert watchdog.budget_seconds == budget
    assert watchdog.deadline is None
    assert _watchdog_threads(started_threads) == []
    assert effects.calls == []
    print_success("not armed")


def test_arm_fixes_the_deadline_once_on_the_watchdog_clock(effects: Effects, started_threads: list[threading.Thread]) -> None:
    """SDB-017 — contract 8: on a fake clock at 1000, ``arm()`` returns 1000.25 for a budget of 0.25 — the clock's time plus the budget, which ``deadline`` gives too — and starts one daemon thread, "shutdown-watchdog"; armed again once the clock moved, it changes nothing — the same deadline — and starts nothing. With the clock past the deadline, it fires: children, then exit 1."""
    print_section("SDB-017: arm() on a fake clock, twice")
    clock = FakeClock()
    watchdog = _watchdog(effects, 0.25, clock=clock)

    assert watchdog.arm() == 1_000.25
    assert watchdog.deadline == 1_000.25
    clock.now = 1_000.125
    assert watchdog.arm() == 1_000.25
    assert watchdog.deadline == 1_000.25
    threads = _watchdog_threads(started_threads)
    assert [(thread.name, thread.daemon) for thread in threads] == [(WATCHDOG_THREAD, True)]

    clock.now = 1_001.0
    effects.wait_for_exit(5.0)
    _join(threads)
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    print_success("deadline 1000.25, fixed once; one daemon thread")


def test_an_armed_watchdog_fires_at_its_deadline(effects: Effects, started_threads: list[threading.Thread]) -> None:
    """SDB-018 — contract 8: on the real monotonic clock with a budget of 0.2 s, ``arm()`` fixes the deadline 0.2 s after its call, the one ``deadline`` gives; the watchdog terminates the children once with 0.5 and exits once with 1, not before its deadline and within 2 s after it; then its thread ends."""
    print_section("SDB-018: arm() on the real clock")
    watchdog = _watchdog(effects, 0.2)

    before = time.monotonic()
    deadline = watchdog.arm()
    after = time.monotonic()
    assert deadline == watchdog.deadline
    assert before + 0.2 - 1e-6 <= deadline <= after + 0.2 + 1e-6, f"deadline {deadline}, not 0.2 s after arm() ({before} to {after})"

    effects.wait_for_exit(deadline - time.monotonic() + 2.0)
    _join(_watchdog_threads(started_threads))
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    assert effects.exit_times[0] >= deadline - 0.01, f"fired {deadline - effects.exit_times[0]:.3f} s before its deadline"
    print_success(f"fired {effects.exit_times[0] - deadline:.3f} s after its deadline")


def test_arm_survives_a_signal_handler_arming_it_while_it_runs(effects: Effects, started_threads: list[threading.Thread]) -> None:
    """SDB-019 — contract 8: the SIGTERM/SIGINT wrapper runs ``arm()`` on the main thread, between two bytecodes of whatever runs there — ``arm()`` itself included, run by the wrapper of a first signal when a second one comes. A clock that runs ``arm()`` the first time it is read plays that signal: ``arm()`` returns, one thread is started, one deadline fixed. A lock a thread cannot take twice would hang the process here, with no watchdog left to end it.

    The arming runs in a thread of the test, so that a deadlock fails this test instead of hanging the run.
    """
    print_section("SDB-019: arm() re-entered by a signal handler")
    clock = ReentrantClock()
    watchdog = _watchdog(effects, 0.25, clock=clock)
    clock.watchdog = watchdog
    outcome: list[float] = []

    caller = threading.Thread(target=lambda: outcome.append(watchdog.arm()), name="sdb-arming", daemon=True)
    caller.start()
    caller.join(5.0)
    assert not caller.is_alive(), "arm() never returned once re-entered: a lock a signal handler cannot take a second time?"
    assert clock.reentered, "barrier: arm() never read its clock"
    assert outcome == [1_000.25]
    assert watchdog.deadline == 1_000.25
    assert len(_watchdog_threads(started_threads)) == 1

    clock.now = 1_001.0
    effects.wait_for_exit(5.0)
    _join(_watchdog_threads(started_threads))
    assert effects.of("exit") == [("exit", 1)]
    print_success("returned; one thread, one deadline")


# =============================================================================
# 9. ShutdownWatchdog: firing
# =============================================================================


def test_fire_runs_once_however_often_it_is_called(effects: Effects) -> None:
    """SDB-020 — contract 9: called twice, ``fire()`` terminates the children once and exits once."""
    print_section("SDB-020: fire() twice")
    watchdog = _watchdog(effects, 8)

    watchdog.fire()
    watchdog.fire()
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    print_success("once")


def test_a_watchdog_fired_early_does_not_fire_again_at_its_deadline(effects: Effects, started_threads: list[threading.Thread]) -> None:
    """SDB-021 — contract 9: armed with 0.3 s, then fired at once by hand: the thread reaches the deadline, finds the work done, and ends without a second exit."""
    print_section("SDB-021: fire() before the deadline, then the deadline")
    watchdog = _watchdog(effects, 0.3)

    watchdog.arm()
    watchdog.fire()
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    _join(_watchdog_threads(started_threads))
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    print_success("one exit; the thread ended")


def test_fire_terminates_then_saves_coverage_then_flushes_then_exits(monkeypatch: pytest.MonkeyPatch, effects: Effects) -> None:
    """SDB-022 — contract 9: with a measurement running, ``fire()`` terminates the children with 0.5, saves the coverage data once, flushes stdout, stderr and the root logger's handlers after that, and exits with 1 as its very last act."""
    print_section("SDB-022: what fire() does, in order")
    watchdog = _watchdog(effects, 8)
    handler = RecordingHandler(effects.calls)
    root = logging.getLogger()

    with monkeypatch.context() as patch:
        patch.setitem(sys.modules, "coverage", _coverage_module(CoverageRecorder(effects.calls)))
        patch.setattr(sys, "stdout", RecordingStream("stdout", effects.calls))
        patch.setattr(sys, "stderr", RecordingStream("stderr", effects.calls))
        root.addHandler(handler)
        try:
            watchdog.fire()
        finally:
            root.removeHandler(handler)

    kinds = [call[0] for call in effects.calls]
    assert effects.of("terminate_children") == [("terminate_children", CHILDREN_GRACE)]
    assert effects.of("coverage.save") == [("coverage.save",)], kinds
    assert effects.of("exit") == [("exit", 1)] and kinds[-1] == "exit", f"exit(1) is not the last thing fire() does: {kinds}"
    saved = kinds.index("coverage.save")
    assert kinds.index("terminate_children") < saved, f"the coverage data was saved before the children were terminated: {kinds}"
    for flush in ("stdout.flush", "stderr.flush", "handler.flush"):
        assert flush in kinds, f"{flush} never happened: {kinds}"
        assert saved < len(kinds) - 1 - kinds[::-1].index(flush), f"no {flush} after the coverage data was saved: {kinds}"
    print_success(" → ".join(kind for kind in kinds if kind != "log"))


@pytest.mark.parametrize("imported", [False, True], ids=["coverage-not-imported", "coverage-imported-not-measuring"])
def test_fire_saves_no_coverage_unless_a_measurement_runs(monkeypatch: pytest.MonkeyPatch, effects: Effects, imported: bool) -> None:
    """SDB-023 — contract 9: with ``coverage`` imported but no current measurement, nothing is saved; with ``coverage`` not imported, ``fire()`` does not import it. It still exits with 1."""
    print_section(f"SDB-023: fire() with coverage {'imported, not measuring' if imported else 'not imported'}")
    if not imported:
        monkeypatch.delitem(sys.modules, "coverage")
    watchdog = _watchdog(effects, 8)

    watchdog.fire()
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    if not imported:
        assert "coverage" not in sys.modules, "fire() imported coverage: it may only save a measurement that already runs"
    print_success("nothing saved; exit 1")


def _fail_step() -> str:
    raise RuntimeError("sdb: the lifecycle cannot tell its step")


def _fail_terminate(timeout: float) -> list[int]:
    raise psutil.AccessDenied(pid=1, name="sdb-unreachable-child")


@pytest.mark.parametrize("failing", ["current_step", "terminate_children", "coverage.save"])
def test_fire_exits_even_when_a_step_before_the_exit_fails(monkeypatch: pytest.MonkeyPatch, effects: Effects, failing: str) -> None:
    """SDB-024 — contract 9: the exit is what the watchdog is for. Whether the step in progress cannot be read, a child cannot be terminated or the coverage data cannot be written, ``exit(1)`` still comes, once.

    The test says nothing of what ``fire()`` does with the error besides: it may log it, or let it go after the exit.
    """
    print_section(f"SDB-024: fire() when {failing} fails")
    if failing == "coverage.save":
        monkeypatch.setitem(sys.modules, "coverage", _coverage_module(FailingCoverage(effects.calls)))
    watchdog = ShutdownWatchdog(
        8,
        exit=effects.exit,
        terminate_children=_fail_terminate if failing == "terminate_children" else effects.terminate_children,
        current_step=_fail_step if failing == "current_step" else _install_step,
    )

    with contextlib.suppress(Exception):
        watchdog.fire()
    assert effects.of("exit") == [("exit", 1)], f"no exit after {failing} failed: {effects.calls}"
    print_success("exit 1")


PROBE_STEP = "sdb-probe-step"
PROBE_THREAD = "sdb-probe-worker"

#: Runs in the child, a fresh interpreter where structlog's logger cache holds nothing. argv[1]: names and the child's code.
FIRE_LOG_PROBE = PROBE_PRELUDE + """
from backend.app.services.platform.shutdown_budget import ShutdownWatchdog

given = json.loads(sys.argv[1])
release = threading.Event()
worker = threading.Thread(target=release.wait, name=given["thread"], daemon=True)
worker.start()
child = subprocess.Popen([sys.executable, "-I", "-c", given["child"]], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env={"PATH": os.environ.get("PATH", os.defpath)}, text=True)
calls = []
try:
    if child.stdout.readline().strip() != "ready":
        sys.exit("the child did not start")
    with capture_logs() as events:

        def errors_so_far():
            return sum(1 for event in logged(events) if event.get("log_level") == "error")

        watchdog = ShutdownWatchdog(
            8,
            exit=lambda code: calls.append(["exit", code, errors_so_far()]),
            terminate_children=lambda timeout: calls.append(["terminate_children", timeout, errors_so_far()]),
            current_step=lambda: given["step"],
        )
        watchdog.fire()
finally:
    release.set()
    child.kill()
    child.communicate(timeout=10)
errors = [event for event in logged(events) if event.get("log_level") == "error"]
print("RESULT_MARKER" + json.dumps({"child": child.pid, "calls": calls, "errors": errors}, default=repr))
""".replace("RESULT_MARKER", PROBE_MARKER)


def test_fire_logs_the_step_the_threads_and_the_children_before_terminating_them(tmp_path: Path) -> None:
    """SDB-025 — contract 9: in a fresh interpreter with a thread "sdb-probe-worker" and a child process alive, ``fire()`` logs at ERROR the step ``current_step()`` gives, that thread's name and the child's pid, before ``terminate_children`` runs; then it exits with 1.

    A fresh interpreter, so that the capture sees the module's logger whatever this process configured before.
    """
    print_section("SDB-025: the ERROR log of fire()")

    result = _probe(FIRE_LOG_PROBE, tmp_path, json.dumps({"step": PROBE_STEP, "thread": PROBE_THREAD, "child": COOPERATIVE_CHILD}))
    assert [call[:2] for call in result["calls"]] == [["terminate_children", CHILDREN_GRACE], ["exit", 1]], result["calls"]
    errors = result["errors"]
    assert errors, "fire() logged nothing at ERROR"
    assert result["calls"][0][2] >= 1, f"the children were terminated before the ERROR log named them: {errors}"
    assert _holds(errors, PROBE_STEP), f"the step in progress is not in the ERROR log: {errors}"
    assert _holds(errors, PROBE_THREAD), f"the live thread {PROBE_THREAD!r} is not in the ERROR log: {errors}"
    assert _holds_pid(errors, result["child"]), f"the child process {result['child']} is not in the ERROR log: {errors}"
    print_success(f"{len(errors)} ERROR event(s): the step, the thread, the child — then terminate, then exit")


# =============================================================================
# 10. install_shutdown_watchdog
# =============================================================================


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGINT], ids=["SIGTERM", "SIGINT"])
def test_the_wrapper_arms_the_watchdog_then_calls_uvicorns_handler(
    signal_handlers: dict[int, object],
    injected: type[ShutdownWatchdog],
    effects: Effects,
    started_threads: list[threading.Thread],
    signum: int,
) -> None:
    """SDB-026 — contract 10: uvicorn's exit handler on each signal — the ``handle_exit`` of a real ``uvicorn.Server``, one server per signal —: ``install_shutdown_watchdog(budget_seconds=1)`` wraps both and returns the watchdog it installed, not armed. Called as the signal would call it, a wrapper arms the watchdog first — its deadline one second after the call —, then runs the ``handle_exit`` it replaced, once, with its signal: that server is asked to exit — ``should_exit``, the signal in ``_captured_signals`` —, the other is not. The watchdog fires one second later."""
    print_section(f"SDB-026: the {signal.Signals(signum).name} wrapper")
    servers = {number: _uvicorn_server() for number in HANDLED_SIGNALS}
    exit_handlers = {number: server.handle_exit for number, server in servers.items()}
    result, wrappers = _install(signal_handlers, exit_handlers, budget_seconds=1)
    watchdog = _injected(result, injected)
    assert watchdog.budget_seconds == 1
    assert _installed_watchdog() is watchdog
    assert watchdog.deadline is None, "installing is not arming"
    assert all(callable(wrapper) and wrapper is not exit_handlers[number] for number, wrapper in wrappers.items()), f"not both wrapped: {wrappers}"
    server = servers[signum]
    effects.seen_at_arm = lambda: (list(server._captured_signals), server.should_exit)

    before = time.monotonic()
    wrappers[signum](signum, None)
    after = time.monotonic()
    assert effects.arms == [([], False)], f"uvicorn's handler ran before the watchdog was armed: {effects.arms}"
    assert (server._captured_signals, server.should_exit) == ([signum], True), "the wrapper did not run uvicorn's handle_exit once, with its signal"
    others = [(other._captured_signals, other.should_exit) for number, other in servers.items() if number != signum]
    assert others == [([], False)], f"the wrapper ran the other signal's handler: {others}"
    assert watchdog.deadline is not None and before + 1 - 1e-6 <= watchdog.deadline <= after + 1 + 1e-6, f"deadline {watchdog.deadline}, not 1 s after the wrapper's call ({before} to {after})"
    assert len(_watchdog_threads(started_threads)) == 1

    effects.wait_for_exit(watchdog.deadline - time.monotonic() + 3.0)
    _join(_watchdog_threads(started_threads))
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    print_success("armed, then uvicorn's handle_exit(signum, None); fired at the deadline")


@pytest.mark.parametrize(
    ("value", "budget"),
    [
        pytest.param(None, 8, id="unset"),
        pytest.param("16", 16, id="16"),
        pytest.param("2", 2, id="2"),
        pytest.param("abc", 8, id="unusable-word"),
        pytest.param("601", 8, id="unusable-601"),
    ],
)
def test_install_takes_its_budget_from_the_environment(monkeypatch: pytest.MonkeyPatch, signal_handlers: dict[int, object], injected: type[ShutdownWatchdog], value: str | None, budget: int) -> None:
    """SDB-027 — contract 10: with no budget given, the watchdog's is ``shutdown_budget_seconds()``: the variable's, or 8 when unset or unusable, without raising."""
    print_section(f"SDB-027: install_shutdown_watchdog() with {TIMEOUT_VARIABLE}={value!r}")
    if value is not None:
        monkeypatch.setenv(TIMEOUT_VARIABLE, value)
    server = _uvicorn_server()

    result, _ = _install(signal_handlers, dict.fromkeys(HANDLED_SIGNALS, server.handle_exit))
    watchdog = _injected(result, injected)
    assert watchdog.budget_seconds == budget
    assert watchdog.deadline is None
    print_success(f"budget {budget}")


@pytest.mark.parametrize("source", ["argument", "environment"])
def test_with_a_budget_of_0_install_changes_nothing(monkeypatch: pytest.MonkeyPatch, signal_handlers: dict[int, object], injected: type[ShutdownWatchdog], source: str) -> None:
    """SDB-028 — contract 10: a budget of 0 — given, or read as "0" — means no limit: None, uvicorn's handlers as they were, no watchdog installed."""
    print_section(f"SDB-028: a budget of 0 from the {source}")
    stand_ins = dict.fromkeys(HANDLED_SIGNALS, _uvicorn_server().handle_exit)
    if source == "environment":
        monkeypatch.setenv(TIMEOUT_VARIABLE, "0")

    result, after = _install(signal_handlers, stand_ins, budget_seconds=None if source == "environment" else 0)
    assert result is None
    assert after == stand_ins
    assert _installed_watchdog() is None
    print_success("None; nothing wrapped")


def test_off_the_main_thread_install_changes_nothing(signal_handlers: dict[int, object], injected: type[ShutdownWatchdog]) -> None:
    """SDB-029 — contract 10: called from another thread — the API tests run uvicorn in one, inside the test process — it returns None without raising, wraps nothing and installs nothing, uvicorn's handlers on both signals notwithstanding."""
    print_section("SDB-029: install_shutdown_watchdog() off the main thread")
    stand_ins = dict.fromkeys(HANDLED_SIGNALS, _uvicorn_server().handle_exit)
    outcome: list[object] = []

    def install() -> None:
        try:
            outcome.append(install_shutdown_watchdog(budget_seconds=1))
        except Exception as error:
            outcome.append(error)

    worker = threading.Thread(target=install, name="sdb-not-main", daemon=True)
    for signum, handler in stand_ins.items():
        signal.signal(signum, handler)
    try:
        worker.start()
        worker.join(5.0)
        after = _handlers()
    finally:
        _put_back(signal_handlers)
    assert not worker.is_alive(), "install_shutdown_watchdog() did not return"
    assert outcome == [None]
    assert after == stand_ins
    assert _installed_watchdog() is None
    print_success("None; nothing wrapped")


@pytest.mark.parametrize("kind", ["SIG_DFL", "SIG_IGN", "default_int_handler", "a-function"])
def test_install_wraps_sigterm_and_leaves_a_sigint_that_is_not_uvicorns(signal_handlers: dict[int, object], injected: type[ShutdownWatchdog], kind: str) -> None:
    """SDB-030 — contract 10: uvicorn's exit handler on SIGTERM, another handler on SIGINT — SIG_DFL, SIG_IGN, Python's ``default_int_handler``, a function —: the watchdog is installed and SIGTERM wrapped; SIGINT keeps its handler."""
    print_section(f"SDB-030: SIGINT on {kind}")
    stand_ins = {signal.SIGTERM: _uvicorn_server().handle_exit, signal.SIGINT: NOT_UVICORN[kind]()}

    result, after = _install(signal_handlers, stand_ins, budget_seconds=1)
    watchdog = _injected(result, injected)
    assert after[signal.SIGINT] == stand_ins[signal.SIGINT], f"SIGINT's handler changed: {after[signal.SIGINT]!r}"
    wrapper = after[signal.SIGTERM]
    assert callable(wrapper) and wrapper != stand_ins[signal.SIGTERM], f"SIGTERM not wrapped: {wrapper!r}"
    assert _installed_watchdog() is watchdog
    print_success(f"SIGTERM wrapped, SIGINT left on {kind}")


@pytest.mark.parametrize(
    ("term", "interrupt"),
    [(signal.SIG_DFL, signal.SIG_DFL), (signal.SIG_IGN, signal.SIG_DFL), (signal.SIG_DFL, signal.SIG_IGN)],
    ids=["both-SIG_DFL", "SIGTERM-SIG_IGN", "SIGINT-SIG_IGN"],
)
def test_with_no_handler_to_wrap_install_returns_none(signal_handlers: dict[int, object], injected: type[ShutdownWatchdog], term: object, interrupt: object) -> None:
    """SDB-031 — contract 10: when neither signal has a callable handler — no uvicorn to call through — there is nothing to arm from: None, both handlers untouched, no watchdog installed."""
    print_section(f"SDB-031: SIGTERM {term!r}, SIGINT {interrupt!r}")
    stand_ins = {signal.SIGTERM: term, signal.SIGINT: interrupt}

    result, after = _install(signal_handlers, stand_ins, budget_seconds=1)
    assert result is None
    assert after == stand_ins
    assert _installed_watchdog() is None
    print_success("None; nothing wrapped")


#: ``(SIGTERM's handler, SIGINT's)``, as kinds of ``NOT_UVICORN``, or "uvicorn" — a real server's ``handle_exit`` —, or
#: "found" — the one the test found.
SIGTERM_NOT_UVICORN = [
    pytest.param("SIG_DFL", "default_int_handler", id="pytest-main-thread"),
    pytest.param("found", "found", id="this-process-as-it-is"),
    *(pytest.param(kind, "uvicorn", id=f"{kind}-with-uvicorn-on-SIGINT") for kind in ("SIG_DFL", "SIG_IGN", "a-function", "another-class-method", "handle_exit-of-another-class", "another-method-of-a-uvicorn-server")),
]


@pytest.mark.parametrize(("term", "interrupt"), SIGTERM_NOT_UVICORN)
def test_without_uvicorns_handler_on_sigterm_install_changes_nothing(signal_handlers: dict[int, object], injected: type[ShutdownWatchdog], term: str, interrupt: str) -> None:
    """SDB-042 — contract 10: SIGTERM decides. When its handler is not uvicorn's exit handler, ``install_shutdown_watchdog(budget_seconds=1)`` returns None on the main thread, changes no handler and installs nothing — not even with uvicorn's on SIGINT, which is never wrapped alone.

    ``pytest-main-thread``: SIG_DFL and Python's ``default_int_handler``. ``this-process-as-it-is``: the handlers this
    test process has — SIG_DFL on SIGTERM, or coverage's in a measured run —, those ``test_post_migration``,
    ``test_signal_runtime``, ``test_risk_scenario_catalog`` and ``test_market_calendar`` find when they run the real
    lifespan in pytest's main thread: its first step installs nothing there, so no watchdog can end this process.
    """
    print_section(f"SDB-042: SIGTERM on {term}, SIGINT on {interrupt}")

    def handler(kind: str, signum: int) -> object:
        if kind == "found":
            return signal_handlers[signum]
        return _uvicorn_server().handle_exit if kind == "uvicorn" else NOT_UVICORN[kind]()

    stand_ins = {signum: handler(kind, signum) for signum, kind in ((signal.SIGTERM, term), (signal.SIGINT, interrupt))}

    result, after = _install(signal_handlers, stand_ins, budget_seconds=1)
    assert result is None, f"install_shutdown_watchdog() installed {result!r} with {stand_ins[signal.SIGTERM]!r} on SIGTERM"
    assert after == stand_ins, f"a handler changed: {after}"
    assert _installed_watchdog() is None
    print_success("None; nothing wrapped")


def test_a_subclass_of_uvicorns_server_counts_and_is_given_the_frame(signal_handlers: dict[int, object], injected: type[ShutdownWatchdog], effects: Effects, started_threads: list[threading.Thread]) -> None:
    """SDB-043 — contract 10: the ``handle_exit`` of a subclass of ``uvicorn.Server`` — overridden, under the same name — is uvicorn's exit handler too: the watchdog is installed and both signals are wrapped. Each wrapper hands that handler the signal and the frame it was given, as they came, and uvicorn's own ``handle_exit`` still runs under the override. Armed twice, the watchdog starts one thread, which fires — on a fake clock, moved past its deadline."""
    print_section("SDB-043: a subclass of uvicorn.Server")
    clock = FakeClock()
    effects.clock = clock
    server = FrameRecordingServer(_uvicorn_config())
    exit_handler = server.handle_exit
    result, wrappers = _install(signal_handlers, dict.fromkeys(HANDLED_SIGNALS, exit_handler), budget_seconds=1)
    watchdog = _injected(result, injected)
    assert all(callable(wrapper) and wrapper is not exit_handler for wrapper in wrappers.values()), f"not both wrapped: {wrappers}"
    #: Stand for the frames a delivery passes: one per signal, so that each is followed to its handler.
    frames = {signum: object() for signum in HANDLED_SIGNALS}

    for signum in HANDLED_SIGNALS:
        wrappers[signum](signum, frames[signum])
    assert server.given == [(signum, frames[signum]) for signum in HANDLED_SIGNALS]
    assert server._captured_signals == list(HANDLED_SIGNALS), "uvicorn's handle_exit did not run under the override"
    assert watchdog.deadline == START + 1
    assert len(_watchdog_threads(started_threads)) == 1

    clock.now = START + 2
    effects.wait_for_exit(5.0)
    _join(_watchdog_threads(started_threads))
    assert effects.calls == [("terminate_children", CHILDREN_GRACE), ("exit", 1)]
    print_success("wrapped; each handler given its signal and frame; one thread, fired")


# =============================================================================
# 11. shutdown_deadline
# =============================================================================


def test_the_cleanup_margin() -> None:
    """SDB-033 — contract 11: the lifespan's steps end 0.75 s before the watchdog fires, which leaves its cleanup that long."""
    print_section("SDB-033: CLEANUP_MARGIN_SECONDS")

    assert CLEANUP_MARGIN_SECONDS == 0.75
    print_success("0.75 s")


@pytest.mark.parametrize(
    ("value", "deadline"),
    [
        pytest.param(None, 1_005.0, id="unset-8-less-3"),
        pytest.param("16", 1_010.0, id="16-less-6"),
        pytest.param("2", 1_001.0, id="2-less-1"),
        pytest.param("600", 1_375.0, id="600-less-225"),
        pytest.param("abc", 1_005.0, id="unusable-8-less-3"),
    ],
)
def test_without_a_watchdog_the_deadline_is_the_budget_less_the_drain(monkeypatch: pytest.MonkeyPatch, value: str | None, deadline: float) -> None:
    """SDB-034 — contract 11: with no watchdog installed, the lifespan's deadline is ``clock() + budget - drain`` — uvicorn spent the drain before the lifespan's shutdown began."""
    print_section(f"SDB-034: shutdown_deadline() with {TIMEOUT_VARIABLE}={value!r}")
    if value is not None:
        monkeypatch.setenv(TIMEOUT_VARIABLE, value)

    assert shutdown_deadline(clock=FakeClock()) == deadline
    print_success(f"{deadline}")


def test_without_a_watchdog_the_deadline_is_counted_afresh_at_each_call(monkeypatch: pytest.MonkeyPatch) -> None:
    """SDB-045 — contract 11: with no watchdog, each call reads the clock and the variable again — a later shutdown of the same process, as an API test server's, gets its own deadline, never one already past —: 1005 at 1000, 1009 at 1004, 1014 once the budget is 16, None once it is 0, 1009 again once unset. With no clock given, the monotonic clock plus 5 s."""
    print_section("SDB-045: shutdown_deadline() counted at each call")
    clock = FakeClock()

    assert shutdown_deadline(clock=clock) == 1_005.0
    clock.now = 1_004.0
    assert shutdown_deadline(clock=clock) == 1_009.0
    monkeypatch.setenv(TIMEOUT_VARIABLE, "16")
    assert shutdown_deadline(clock=clock) == 1_014.0
    monkeypatch.setenv(TIMEOUT_VARIABLE, "0")
    assert shutdown_deadline(clock=clock) is None
    monkeypatch.delenv(TIMEOUT_VARIABLE)
    assert shutdown_deadline(clock=clock) == 1_009.0

    before = time.monotonic()
    deadline = shutdown_deadline()
    after = time.monotonic()
    assert deadline is not None and before + 5 - 1e-6 <= deadline <= after + 5 + 1e-6, f"{deadline} is not the monotonic clock plus 5 s ({before} to {after})"
    print_success("1005, 1009, 1014, None, 1009; the monotonic clock by default")


def test_with_a_budget_of_0_there_is_no_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    """SDB-036 — contract 11: no limit, no deadline — at each call."""
    print_section("SDB-036: shutdown_deadline() without a limit")
    monkeypatch.setenv(TIMEOUT_VARIABLE, "0")

    assert shutdown_deadline(clock=FakeClock()) is None
    assert shutdown_deadline(clock=FakeClock()) is None
    print_success("None")


def test_with_an_armed_watchdog_the_deadline_is_its_own_less_the_cleanup_margin(
    signal_handlers: dict[int, object],
    injected: type[ShutdownWatchdog],
    effects: Effects,
    started_threads: list[threading.Thread],
) -> None:
    """SDB-037 — contract 11: once a signal armed the watchdog — its SIGTERM wrapper called —, the deadline is the watchdog's minus 0.75 s, on the watchdog's clock — not the one passed —, and the same at each call. Asking does not arm it again: one ``arm()``, the signal's, one thread, which fires."""
    print_section("SDB-037: shutdown_deadline() once a signal armed the watchdog")
    result, wrappers = _install(signal_handlers, dict.fromkeys(HANDLED_SIGNALS, _uvicorn_server().handle_exit), budget_seconds=1)
    watchdog = _injected(result, injected)
    wrappers[signal.SIGTERM](signal.SIGTERM, None)
    armed_deadline = watchdog.deadline
    assert armed_deadline is not None, "barrier: the SIGTERM wrapper armed the watchdog"

    deadline = shutdown_deadline(clock=FakeClock())
    assert deadline == pytest.approx(armed_deadline - CLEANUP_MARGIN_SECONDS, abs=1e-6)
    assert shutdown_deadline() == pytest.approx(deadline, abs=1e-6)
    assert watchdog.deadline == armed_deadline and effects.arms == [None], f"shutdown_deadline() armed the watchdog again: {len(effects.arms)} arm() calls"
    assert len(_watchdog_threads(started_threads)) == 1

    effects.wait_for_exit(watchdog.deadline - time.monotonic() + 3.0)
    _join(_watchdog_threads(started_threads))
    assert effects.of("exit") == [("exit", 1)]
    print_success("the watchdog's deadline less 0.75 s")


def test_a_watchdog_no_signal_armed_stays_unarmed_and_the_deadline_counts_from_the_clock(
    monkeypatch: pytest.MonkeyPatch,
    signal_handlers: dict[int, object],
    injected: type[ShutdownWatchdog],
    effects: Effects,
    started_threads: list[threading.Thread],
) -> None:
    """SDB-044 — contract 11: a watchdog installed that no signal armed — a shutdown that did not come from a signal: a test, a server at its request limit — is left as it is by ``shutdown_deadline()``: no ``arm()``, no ``deadline``, no thread, nothing fired, still the watchdog installed. The deadline is the one without a watchdog, counted at each call: 1010 at 1000 for a budget of 16, 1014 at 1004."""
    print_section("SDB-044: shutdown_deadline() with a watchdog no signal armed")
    monkeypatch.setenv(TIMEOUT_VARIABLE, "16")
    result, _ = _install(signal_handlers, dict.fromkeys(HANDLED_SIGNALS, _uvicorn_server().handle_exit))
    watchdog = _injected(result, injected)
    assert watchdog.budget_seconds == 16, "barrier: the watchdog has the budget in force"
    clock = FakeClock()

    assert shutdown_deadline(clock=clock) == 1_010.0
    clock.now = 1_004.0
    assert shutdown_deadline(clock=clock) == 1_014.0
    assert effects.arms == [], f"shutdown_deadline() called arm() {len(effects.arms)} time(s)"
    assert watchdog.deadline is None, "shutdown_deadline() armed the watchdog"
    assert _watchdog_threads(started_threads) == []
    assert effects.calls == []
    assert _installed_watchdog() is watchdog
    print_success("not armed; 1010, then 1014")


# =============================================================================
# 12. terminate_child_processes
# =============================================================================


def test_children_that_ignore_sigterm_are_killed_after_the_timeout_grandchildren_included(children: Children) -> None:
    """SDB-038 — contract 12: a child that ignores SIGTERM, and its grandchild that ignores it too, are given the timeout, then killed: both gone, both pids returned.

    ``keep`` spares every process but these two: other children of this process — a neighbour's pool, the resource
    tracker — are never touched.
    """
    print_section("SDB-038: SIGTERM ignored, then SIGKILL, recursively")
    parent = children.start(STUBBORN_PARENT)
    (grandchild_pid,) = _ready(parent)
    grandchild = children.adopt(int(grandchild_pid))
    assert grandchild.ppid() == parent.pid, "barrier: the grandchild is the child's"
    mine = {parent.pid, grandchild.pid}

    started = time.monotonic()
    killed = terminate_child_processes(CHILDREN_GRACE, keep=lambda process: process.pid not in mine)
    elapsed = time.monotonic() - started
    assert isinstance(killed, list) and sorted(killed) == sorted(mine), f"killed {killed}, expected {sorted(mine)}"
    assert elapsed >= CHILDREN_GRACE * 0.8, f"killed after {elapsed:.3f} s: SIGTERM was not given its {CHILDREN_GRACE} s"
    _assert_gone(parent)
    _assert_gone(grandchild)
    print_success(f"both killed after {elapsed:.3f} s")


def test_a_child_that_heeds_sigterm_ends_without_being_killed(children: Children) -> None:
    """SDB-039 — contract 12: a child with SIGTERM's default action ends on ``terminate()``: gone, and not among the pids that had to be killed."""
    print_section("SDB-039: SIGTERM heeded")
    child = children.start(COOPERATIVE_CHILD)
    _ready(child)

    killed = terminate_child_processes(CHILDREN_GRACE, keep=lambda process: process.pid != child.pid)
    assert killed == [], f"a child that heeds SIGTERM was killed: {killed}"
    _assert_gone(child)
    print_success("terminated, not killed")


def test_a_child_keep_accepts_is_left_running(children: Children) -> None:
    """SDB-040 — contract 12: ``keep`` is asked about every child, as a ``psutil.Process``; the one it accepts still runs afterwards — the test ends it itself —, the other is gone."""
    print_section("SDB-040: keep")
    kept = children.start(COOPERATIVE_CHILD)
    target = children.start(COOPERATIVE_CHILD)
    _ready(kept)
    _ready(target)
    asked: list[object] = []

    def keep(process: psutil.Process) -> bool:
        asked.append(process)
        return getattr(process, "pid", None) != target.pid

    killed = terminate_child_processes(CHILDREN_GRACE, keep=keep)
    assert all(isinstance(process, psutil.Process) for process in asked), asked
    assert {kept.pid, target.pid} <= {process.pid for process in asked}
    assert killed == []
    _assert_gone(target)
    assert kept.poll() is None, "the child keep accepted was ended"
    print_success("the kept child runs; the other is gone")


#: Runs in the child, a fresh interpreter whose only children are its own. argv[1]: the codes of its two children.
KEEP_PROBE = """
import json, os, subprocess, sys
from multiprocessing import resource_tracker

import psutil

from backend.app.services.platform.shutdown_budget import terminate_child_processes

codes = json.loads(sys.argv[1])
resource_tracker.ensure_running()
me = psutil.Process()
trackers = [child.pid for child in me.children() if "resource_tracker" in " ".join(child.cmdline())]
env = {"PATH": os.environ.get("PATH", os.defpath)}
started = {name: subprocess.Popen([sys.executable, "-I", "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env, text=True) for name, code in codes.items()}


def running(process):
    try:
        return process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


try:
    ready = {name: process.stdout.readline().strip() for name, process in started.items()}
    killed = terminate_child_processes(0.5)
    survivors = [child.pid for child in me.children(recursive=True) if running(child)]
finally:
    for process in started.values():
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=10)
pids = {name: process.pid for name, process in started.items()}
print("RESULT_MARKER" + json.dumps({"trackers": trackers, "ready": ready, "pids": pids, "killed": killed, "survivors": survivors}))
""".replace("RESULT_MARKER", PROBE_MARKER)


def test_by_default_every_child_but_the_resource_tracker_is_terminated(tmp_path: Path) -> None:
    """SDB-041 — contract 12: with the default ``keep``, in a fresh interpreter, multiprocessing's resource tracker — which ignores SIGTERM — still runs afterwards; a child that ignores SIGTERM is killed, one that heeds it is terminated, and only the first is returned.

    A fresh interpreter, because the default ``keep`` spares nothing else: run here, it would end the children of every
    other test sharing this process.
    """
    print_section("SDB-041: the default keep")

    result = _probe(KEEP_PROBE, tmp_path, json.dumps({"stubborn": STUBBORN_CHILD, "cooperative": COOPERATIVE_CHILD}))
    assert result["ready"] == {"stubborn": "ready", "cooperative": "ready"}, "barrier: both children started"
    assert result["trackers"], "barrier: no resource tracker among the probe's children"
    pids = result["pids"]
    assert result["killed"] == [pids["stubborn"]], f"killed {result['killed']}; stubborn {pids['stubborn']}, cooperative {pids['cooperative']}, tracker {result['trackers']}"
    assert set(result["trackers"]) <= set(result["survivors"]), f"the resource tracker was ended: survivors {result['survivors']}"
    assert not set(pids.values()) & set(result["survivors"]), f"a child survived: {result['survivors']}"
    print_success("the tracker spared; the stubborn child killed, the other terminated")


# =============================================================================
# 13. child_processes_step
# =============================================================================


def test_without_a_watchdog_the_child_processes_step_terminates_nothing(monkeypatch: pytest.MonkeyPatch, children: Children) -> None:
    """SDB-046 — contract 13: ``child_processes_step()`` is a ``lifecycle.Step`` named "child-processes". With no watchdog installed — this process's case, and that of every test that runs the real lifespan — its ``run``, run as the lifespan runs it, terminates nothing: a child of this process that heeds SIGTERM still answers afterwards.

    ``terminate_child_processes`` is replaced by a guard that records each call and spares every process but that
    child: were the step to terminate children here, it would end the test's own, never a neighbour's. What the step
    does with a watchdog is SDP-004's, in a server process of its own. The child is reaped at teardown, whatever happened.
    """
    print_section("SDB-046: the child-processes step without a watchdog")
    step = child_processes_step()
    assert isinstance(step, lifecycle.Step) and step.name == "child-processes"
    child = children.start(ANSWERING_CHILD)
    _ready(child)
    terminate = shutdown_budget.terminate_child_processes
    guarded: list[float] = []

    def confined(timeout: float, *, keep: Callable[[psutil.Process], bool] | None = None) -> list[int]:
        """Record the call, then terminate that child at most, whatever ``keep`` was given."""
        guarded.append(timeout)
        return terminate(timeout, keep=lambda process: process.pid != child.pid)

    monkeypatch.setattr(shutdown_budget, "terminate_child_processes", confined)
    assert _installed_watchdog() is None, "barrier: no watchdog is installed"

    outcomes = asyncio.run(lifecycle.run_shutdown_steps((step,), shutdown_deadline()))
    assert [(outcome.name, outcome.finished, outcome.error) for outcome in outcomes] == [("child-processes", True, None)]
    assert guarded == [], f"the step called terminate_child_processes without a watchdog: {guarded}"
    assert _answer(child, "after-the-step") == "alive after-the-step", f"pid {child.pid} no longer answers: the step ended it"
    print_success("nothing terminated: the child still answers")
