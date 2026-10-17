"""``backend.app.services.platform.scheduler.run_lock``: the scheduler's lock across processes (plan phase01SleepWake,
item Z-11, night decision N71).

Each uvicorn worker runs a scheduler loop of its own, with an ``asyncio.Lock`` of its own: only the leader election
(``leader.py``, the lowest PID among the master's children) kept two workers from running the same job at once, and a
wake-up that reached another worker answered ``not_leader``. With ``fcntl`` the workers share one lock file in the data
directory instead, held for a whole run: the worker that holds it runs the jobs that are due, the others wait for it,
then find them done. The contract pinned here:

(a) ``LOCK_FILE_NAME`` ".scheduler.lock", ``POLL_SECONDS`` 0.2. ``fcntl`` is imported with a guard: None where it cannot
    be imported. ``cross_process_lock_available()`` is true when ``fcntl`` is there, read at the call (a test may set
    ``run_lock.fcntl = None``); ``run_lock_path()`` is ``get_data_dir() / LOCK_FILE_NAME``, read at the call.
(b) ``scheduler_run_lock(path=None)`` is an async context manager on ``path``, ``run_lock_path()`` when None. Each attempt
    opens the file — ``O_RDWR | O_CREAT | O_NOFOLLOW``, mode 0o600, its folder created if missing — and tries
    ``flock(LOCK_EX | LOCK_NB)``, in a worker thread; refused, it awaits ``POLL_SECONDS`` and tries again. The block runs
    only once the lock is held: while another process holds it, the block does not start; it starts once that process
    lets go, by releasing the lock or by dying (the kernel releases the locks of a dead process).
(c) The release — ``LOCK_UN``, then the descriptor closed — is in a ``finally``, also in a thread: an exception of the
    block goes through, and the lock is free at once.
(d) A cancellation while waiting goes through, never runs the block, and leaves no lock held and no descriptor open in
    the process: an attempt in flight at that moment that does take the lock releases it.
(e) The lock file stays: created 0o600, never deleted. A symbolic link at the path raises ``OSError`` at once, never
    retried, and nothing behind the link is created or locked.
(f) ``os.open``, ``fcntl.flock`` and ``os.close`` of the lock never run on the event loop's thread.
(g) Z-26 (night decision N79): ``LOCK_WAIT_SECONDS`` 600.0, the longest a scheduler run waits for another run, both of
    its waits together; ``SchedulerRunLockTimeout``, a ``TimeoutError``, raised when another process held the lock past
    the deadline; ``scheduler_run_lock(path=None, *, deadline=None)``, the deadline a keyword only, None by default.
(h) ``deadline`` is an instant of ``time.monotonic()``. None waits as long as it takes, as in (b). With one, each attempt
    is as in (b); once an attempt is refused at or past the deadline, ``SchedulerRunLockTimeout`` is raised — no attempt
    in flight then, the refused attempt's descriptor already closed, the block never run, the other process's lock
    untouched —; before it, the next attempt comes ``min(POLL_SECONDS, deadline - now)`` later, ``POLL_SECONDS`` read at
    each wait. An attempt in flight when the deadline passes is awaited, never abandoned, and none follows it once it is
    refused. At least one attempt always: a free lock is taken even with the deadline already past. A cancellation is as
    in (d).

Pure: no database, no server, no lane port, no network; every file under the test's ``tmp_path``. An autouse fixture
points the data directory (``LIBREFOLIO_TEST_MODE``, ``LIBREFOLIO_TEST_DATA_DIR``) at ``tmp_path`` as well, for this
process and its children, so that even a lock ignoring its ``path`` could never leave a ``.scheduler.lock`` in the
lane's. The other processes are real: scripts written under ``tmp_path`` and run by ``sys.executable`` with the project
root on ``sys.path`` and without the coverage variables — a holder that takes ``scheduler_run_lock(path)`` and keeps it
until a ``release`` file appears, a probe that tries ``LOCK_EX | LOCK_NB`` once from a descriptor of its own. They are
coordinated by files, polled against generous deadlines, since the machine may be loaded far past its cores; a holder
also gives up by itself after ``HOLD_SECONDS``, and every child is killed and reaped in a ``finally``. Inside this process
a new descriptor on the file competes as another process does (``flock`` locks belong to the open file, not to the
process), so the test also probes from here. The lock is watched through ``run_lock.fcntl`` and ``run_lock.os`` replaced
by recorders that delegate to the real modules, each ``flock``, ``open`` and ``close`` recorded with its thread and its
outcome: a refused attempt is the barrier that proves a wait, never a duration. Nothing sleeps but the polling of a
condition; the durations asserted are lower bounds a loaded machine can only lengthen — the gap between two attempts, set
by a timer of the loop; the moment a wait gives up, never before its deadline, which the lock reads on the same
``time.monotonic()`` —, and the deadlines of (h) are either long past, ``NEAR_SECONDS`` away or ``FAR_SECONDS`` away,
far inside or far outside the test's own bound on any wait, ``WAIT_SECONDS``.

Red until Z-11 exists: the module does not import, and every test fails naming it. Red before Z-26 (N79): RL-010 on the
names it reads; RL-011…RL-016 at their first line, naming what is missing — ``SchedulerRunLockTimeout``, the keyword
``deadline`` — before any child is started or any lock taken.
"""

from __future__ import annotations

import asyncio
import contextlib
import fcntl
import importlib
import inspect
import json
import os
import signal
import stat
import subprocess
import sys
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import psutil
import pytest

from backend.app.config import get_data_dir
from backend.test_scripts.test_utils import print_section, print_success

RUN_LOCK_MODULE = "backend.app.services.platform.scheduler.run_lock"
RUN_LOCK_FILE = "backend/app/services/platform/scheduler/run_lock.py"
REPO_ROOT = Path(__file__).resolve().parents[3]

#: The literals of the contract, never read from the module under test.
LOCK_FILE_NAME = ".scheduler.lock"
POLL_SECONDS = 0.2
LOCK_MODE = 0o600
#: Z-26 (N79): the longest a scheduler run waits for another run, both of its waits together.
LOCK_WAIT_SECONDS = 600.0

#: The longest the test waits for anything of this process: an attempt, the block, a task's end.
WAIT_SECONDS = 60.0
#: The longest a child may take to hold the lock or to end, its interpreter and imports included, on a loaded machine.
CHILD_SECONDS = 180.0
#: How long a holder keeps the lock at most when nobody tells it to let go: then it gives up by itself, so that a test
#: killed before its ``finally`` never leaves a lock held for long.
HOLD_SECONDS = 600.0
#: How long a killed child may take to be reaped.
REAP_SECONDS = 30.0
#: How often a condition is polled.
POLL_STEP = 0.02
#: Refused attempts seen before a wait counts as one: three, so the loop's own wait came between them twice.
REFUSALS = 3
#: The most a timer of the loop fires early by: a gap between two attempts can only get longer under load.
TIMER_SLACK = 0.01
#: Turns of the event loop given to a cancellation before the attempt in flight is let go.
LOOP_TURNS = 5
#: What a file behind a symbolic link holds, and its mode: a lock that followed the link would show on them.
BEHIND_THE_LINK = b"not a lock file: behind a symbolic link\n"
BEHIND_THE_LINK_MODE = 0o644
#: The deadlines of (h), Z-26: one already this far behind; one this close, which a wait reaches long before any holder
#: lets go; one this far, which no wait reaches before its holder lets go, however loaded the machine.
PAST_SECONDS = 1.0
NEAR_SECONDS = 0.5
FAR_SECONDS = 300.0
#: ``POLL_SECONDS`` raised to an hour: only a wait cut to its deadline ends within ``WAIT_SECONDS``.
POLL_HOUR = 3_600.0
#: How long past a deadline crossed during an attempt in flight the test watches the wait go on waiting for that attempt.
WATCH_SECONDS = 0.5

#: A child that takes ``scheduler_run_lock(<lock>)`` and keeps it until ``<folder>/release`` appears, saying what it does
#: with files of ``<folder>``: ``held`` once inside, ``released`` once out, ``gave-up`` after ``<hold seconds>``.
HOLDER = """
import asyncio
import os
import sys
import time
from pathlib import Path

root, lock, folder, hold_seconds = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), float(sys.argv[4])
sys.path.insert(0, root)

from backend.app.services.platform.scheduler.run_lock import scheduler_run_lock


def say(name):
    part = folder / (name + ".part")
    part.write_text(str(os.getpid()))
    os.replace(part, folder / name)


async def hold():
    deadline = time.monotonic() + hold_seconds
    async with scheduler_run_lock(lock):
        say("held")
        while not (folder / "release").exists():
            if time.monotonic() > deadline:
                say("gave-up")
                return 3
            await asyncio.sleep(0.02)
    say("released")
    return 0


sys.exit(asyncio.run(hold()))
"""

#: A child that tries ``LOCK_EX | LOCK_NB`` once on ``<path>`` from a descriptor of its own, read-only and without
#: ``O_CREAT`` so that it never leaves a file behind, and prints ``granted`` (released at once), ``refused`` or ``missing``.
PROBE = """
import fcntl
import os
import sys

try:
    fd = os.open(sys.argv[1], os.O_RDONLY)
except FileNotFoundError:
    print("missing")
    sys.exit(0)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    print("refused")
else:
    fcntl.flock(fd, fcntl.LOCK_UN)
    print("granted")
finally:
    os.close(fd)
"""

#: A child where ``fcntl`` cannot be imported, as on a platform without it: what the module makes of that.
WITHOUT_FCNTL_MARK = "WITHOUT-FCNTL "
WITHOUT_FCNTL = """
import json
import sys

sys.path.insert(0, sys.argv[1])
sys.modules["fcntl"] = None

from backend.app.services.platform.scheduler import run_lock

print("WITHOUT-FCNTL " + json.dumps({"fcntl": repr(run_lock.fcntl), "available": run_lock.cross_process_lock_available()}))
"""


class BlockExploded(Exception):
    """The failure provoked inside a block, named so that it is recognisable when it goes through."""


# =============================================================================
# RECORDERS
# =============================================================================


@dataclass(frozen=True)
class Call:
    """One call into ``fcntl`` or ``os`` from the lock: the function, its flags, how it ended, its thread, when it began."""

    function: str
    operation: int
    outcome: str
    thread: int
    at: float


class _Recorder:
    """A stand-in for a module of ``run_lock``: every attribute is the real module's, but those the subclass records."""

    def __init__(self, real: ModuleType) -> None:
        self._real = real
        self._guard = threading.Lock()
        self.calls: list[Call] = []

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._real, name)

    def _record(self, function: str, operation: int, outcome: str, at: float) -> None:
        with self._guard:
            self.calls.append(Call(function, operation, outcome, threading.get_ident(), at))

    def recorded(self) -> list[Call]:
        with self._guard:
            return list(self.calls)


class FlockRecorder(_Recorder):
    """``run_lock.fcntl`` for a test: the real ``fcntl``, each ``flock`` recorded — ``granted`` or ``refused`` for an
    exclusive attempt, ``released`` for ``LOCK_UN``, else the class of its error.

    ``hold_next_attempt()`` stops the next exclusive attempt in its thread just before the real ``flock``, its
    descriptor already open: it sets ``in_flight`` and waits for ``go``, at most ``WAIT_SECONDS``.
    """

    def __init__(self, real: ModuleType) -> None:
        super().__init__(real)
        self._gate: tuple[threading.Event, threading.Event] | None = None

    def hold_next_attempt(self) -> tuple[threading.Event, threading.Event]:
        gate = (threading.Event(), threading.Event())
        self._gate = gate
        return gate

    def flock(self, fd: int, operation: int) -> None:
        exclusive = bool(operation & self._real.LOCK_EX)
        gate, self._gate = (self._gate, None) if exclusive else (None, self._gate)
        if gate is not None:
            in_flight, go = gate
            in_flight.set()
            go.wait(WAIT_SECONDS)
        at = time.monotonic()
        try:
            self._real.flock(fd, operation)
        except BlockingIOError:
            self._record("flock", operation, "refused", at)
            raise
        except OSError as error:
            self._record("flock", operation, type(error).__name__, at)
            raise
        self._record("flock", operation, "granted" if exclusive else "released", at)

    def attempts(self) -> list[Call]:
        """The exclusive attempts, in order."""
        return [call for call in self.recorded() if call.operation & self._real.LOCK_EX]

    def refused(self) -> list[Call]:
        return [call for call in self.attempts() if call.outcome == "refused"]


class OsRecorder(_Recorder):
    """``run_lock.os`` for a test: the real ``os``, each ``open`` (its flags) and ``close`` recorded."""

    def open(self, path: Any, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
        at = time.monotonic()
        try:
            fd = self._real.open(path, flags, mode, dir_fd=dir_fd)
        except OSError as error:
            self._record("open", flags, type(error).__name__, at)
            raise
        self._record("open", flags, "opened", at)
        return fd

    def close(self, fd: int) -> None:
        self._record("close", 0, "closed", time.monotonic())
        self._real.close(fd)


def _run_lock() -> ModuleType:
    """The module under test, or a red naming it while it does not exist."""
    try:
        return importlib.import_module(RUN_LOCK_MODULE)
    except ModuleNotFoundError as error:
        if error.name != RUN_LOCK_MODULE:
            raise
        pytest.fail(f"{RUN_LOCK_FILE} does not exist: the scheduler's lock across processes (Z-11, night decision N71) is not written yet")


def _record_flocks(monkeypatch: pytest.MonkeyPatch, run_lock: ModuleType) -> FlockRecorder:
    recorder = FlockRecorder(fcntl)
    monkeypatch.setattr(run_lock, "fcntl", recorder)
    return recorder


def _record_os(monkeypatch: pytest.MonkeyPatch, run_lock: ModuleType) -> OsRecorder:
    recorder = OsRecorder(os)
    monkeypatch.setattr(run_lock, "os", recorder)
    return recorder


# =============================================================================
# WAITING, PROBING, THE CHILDREN
# =============================================================================


async def _until(condition: Callable[[], bool], what: str | Callable[[], str], *, seconds: float = WAIT_SECONDS) -> None:
    """Until ``condition()`` holds, polled every ``POLL_STEP``; a red naming ``what`` after ``seconds``."""
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            pytest.fail(f"{what() if callable(what) else what}: not within {seconds:.0f} s")
        await asyncio.sleep(POLL_STEP)


async def _within(awaitable: Awaitable[Any], what: str) -> Any:
    """What ``awaitable`` gives, or a red naming ``what`` after ``WAIT_SECONDS``: a hang fails the test instead of the run."""
    try:
        return await asyncio.wait_for(awaitable, WAIT_SECONDS)
    except TimeoutError:
        pytest.fail(f"{what}: nothing within {WAIT_SECONDS:.0f} s")


def _ending(task: asyncio.Task[Any]) -> str:
    """How ``task`` ended, for a message."""
    if not task.done():
        return "still running"
    if task.cancelled():
        return "cancelled"
    error = task.exception()
    return "returned" if error is None else f"raised {type(error).__name__}: {error}"


def _probe_here(path: Path) -> str:
    """``LOCK_EX | LOCK_NB`` once from a new descriptor of this process: ``granted`` (released at once), ``refused`` or
    ``missing``. A ``flock`` lock belongs to the open file, not to the process: a new descriptor here competes as another
    process would. Opened read-only, without ``O_CREAT``: a probe never leaves a file behind."""
    try:
        fd = os.open(path, os.O_RDONLY)
    except FileNotFoundError:
        return "missing"
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return "refused"
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return "granted"
    finally:
        os.close(fd)


def _descriptors_on(path: Path) -> list[int]:
    """The descriptors this process holds open on the file at ``path``."""
    target = path.resolve()
    return [entry.fd for entry in psutil.Process().open_files() if Path(entry.path).resolve() == target]


def _descriptors() -> int:
    return psutil.Process().num_fds()


def _tail(log: Path, lines: int = 40) -> str:
    try:
        text = log.read_text(errors="replace")
    except FileNotFoundError:
        return "(no output)"
    return "\n".join(text.splitlines()[-lines:]) or "(no output)"


def _child_environment() -> dict[str, str]:
    """This process's environment, the data directory under ``tmp_path`` included, without the coverage variables: a
    child never starts a tracer of its own."""
    return {name: value for name, value in os.environ.items() if not name.startswith("COVERAGE_")}


class Children:
    """The child processes of one test: each a script written in the test's folder, run by ``sys.executable``, its output
    in a file there; killed and reaped at the end, whatever happened."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.processes: list[subprocess.Popen[bytes]] = []

    def start(self, name: str, script: str, *args: str) -> subprocess.Popen[bytes]:
        path = self.folder / f"{name}.py"
        path.write_text(script)
        with (self.folder / f"{name}.log").open("wb") as log:
            process = subprocess.Popen([sys.executable, "-u", str(path), *args], cwd=self.folder, env=_child_environment(), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        self.processes.append(process)
        return process

    def log(self, name: str) -> Path:
        return self.folder / f"{name}.log"

    async def run(self, name: str, script: str, *args: str) -> str:
        """A one-shot child, to its end: what it printed; a red if it fails or does not end within ``CHILD_SECONDS``."""
        process = self.start(name, script, *args)
        await _until(lambda: process.poll() is not None, lambda: f"the child {name} never ended: {_tail(self.log(name))}", seconds=CHILD_SECONDS)
        output = self.log(name).read_text(errors="replace")
        assert process.returncode == 0, f"the child {name} ended {process.returncode}: {_tail(self.log(name))}"
        return output

    async def probe(self, path: Path) -> str:
        """``_probe_here`` from another process: ``granted``, ``refused`` or ``missing``."""
        return (await self.run(f"probe-{len(self.processes)}", PROBE, str(path))).strip()

    def close(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=REAP_SECONDS)


@contextmanager
def _children(folder: Path) -> Iterator[Children]:
    children = Children(folder)
    try:
        yield children
    finally:
        children.close()


class Holder:
    """A child holding ``scheduler_run_lock(path)`` until told to let go; its own folder holds the files that say so."""

    def __init__(self, children: Children, path: Path, name: str = "holder") -> None:
        self.name = name
        self.folder = children.folder / name
        self.folder.mkdir()
        self.log = children.log(name)
        self.process = children.start(name, HOLDER, str(REPO_ROOT), str(path), str(self.folder), str(HOLD_SECONDS))

    def says(self, what: str) -> bool:
        return (self.folder / what).exists()

    def tail(self) -> str:
        return _tail(self.log)

    async def holding(self) -> None:
        """Until the holder says it holds the lock; a red at once if it ended before."""

        def held() -> bool:
            if self.says("held"):
                return True
            if self.process.poll() is not None and not self.says("held"):
                pytest.fail(f"the holder ended ({self.process.returncode}) without taking the lock: {self.tail()}")
            return False

        await _until(held, lambda: f"the holder never took the lock: {self.tail()}", seconds=CHILD_SECONDS)

    def release(self) -> None:
        (self.folder / "release").write_text("release")

    async def ended(self) -> None:
        """Until the holder has ended: it let go of the lock and exited cleanly."""
        await _until(lambda: self.process.poll() is not None, lambda: f"the holder never ended once released: {self.tail()}", seconds=CHILD_SECONDS)
        assert (self.process.returncode, self.says("released")) == (0, True), f"the holder let go of the lock and ended cleanly: {self.tail()}"


class Waiting:
    """``async with scheduler_run_lock(path)`` in a task of the test: ``entered`` once the block runs, which then waits
    for ``leave``."""

    def __init__(self, run_lock: ModuleType, path: Path | None) -> None:
        self.entered = asyncio.Event()
        self.leave = asyncio.Event()
        self.task = asyncio.create_task(self._hold(run_lock, path), name="scheduler-run-lock-under-test")

    async def _hold(self, run_lock: ModuleType, path: Path | None) -> None:
        lock = run_lock.scheduler_run_lock() if path is None else run_lock.scheduler_run_lock(path)
        async with lock:
            self.entered.set()
            await self.leave.wait()

    async def refused(self, flocks: FlockRecorder, count: int, holder: str) -> None:
        """Until ``count`` attempts were refused while the block waited; a red at once if the block ran or the task ended."""
        await _until(lambda: self.entered.is_set() or self.task.done() or len(flocks.refused()) >= count, lambda: f"{count} refused attempts while {holder} held the lock; so far {flocks.attempts()}")
        if self.entered.is_set():
            pytest.fail(f"the block ran while {holder} held the lock: attempts {flocks.attempts()}")
        if self.task.done():
            pytest.fail(f"the wait ended while {holder} held the lock: {_ending(self.task)}")

    async def runs(self, what: str) -> None:
        """Until the block runs; a red naming ``what`` if it does not, or at once if the task ended."""
        await _until(lambda: self.entered.is_set() or self.task.done(), what)
        if not self.entered.is_set():
            pytest.fail(f"{what}: the wait ended without running the block: {_ending(self.task)}")

    async def close(self) -> None:
        """The block left and the task over: a wait that never entered is cancelled at once, a block that runs is let go;
        within the deadline, or cancelled. What the task raised is retrieved here."""
        self.leave.set()
        if not self.entered.is_set():
            self.task.cancel()
        await asyncio.wait({self.task}, timeout=WAIT_SECONDS)
        if not self.task.done():
            self.task.cancel()
            await asyncio.wait({self.task}, timeout=WAIT_SECONDS)
        if self.task.done() and not self.task.cancelled():
            self.task.exception()


@asynccontextmanager
async def _waiting(run_lock: ModuleType, path: Path | None) -> AsyncIterator[Waiting]:
    waiting = Waiting(run_lock, path)
    try:
        yield waiting
    finally:
        await waiting.close()


# =============================================================================
# THE DEADLINE (Z-26, N79)
# =============================================================================


def _bounded_wait(run_lock: ModuleType) -> type[BaseException]:
    """``SchedulerRunLockTimeout``, once the lock has the bounded wait of Z-26 (N79); else a red naming what is missing,
    before any child is started or any lock taken."""
    timeout = getattr(run_lock, "SchedulerRunLockTimeout", None)
    deadline = inspect.signature(run_lock.scheduler_run_lock).parameters.get("deadline")
    missing: list[str] = []
    if not (isinstance(timeout, type) and issubclass(timeout, TimeoutError)):
        missing.append("SchedulerRunLockTimeout (a TimeoutError)")
    if deadline is None or deadline.kind is not inspect.Parameter.KEYWORD_ONLY:
        missing.append("keyword deadline in scheduler_run_lock(path=None, *, deadline=None)")
    if missing:
        pytest.fail(f"{RUN_LOCK_FILE} has no {' and no '.join(missing)}: the bounded wait of Z-26 (night decision N79) is not written")
    return timeout


@contextmanager
def _held_here(path: Path) -> Iterator[int]:
    """The lock held by this test from a descriptor of its own — one more open file, which competes as another process
    would — until the block ends: the descriptor."""
    mine = os.open(path, os.O_RDWR | os.O_CREAT, LOCK_MODE)
    try:
        fcntl.flock(mine, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield mine
    finally:
        os.close(mine)


def _left_open(path: Path, mine: int | None = None) -> list[int]:
    """The descriptors this process holds on the lock file, but the test's own."""
    return [fd for fd in _descriptors_on(path) if fd != mine]


class BoundedWait(Waiting):
    """``async with scheduler_run_lock(path, deadline=deadline)`` in a task of the test, as ``Waiting`` (Z-26, N79). If the
    wait gives up, the moment it did and what the recorders held are kept, read in the very step that raised, before the
    loop runs anything else."""

    def __init__(self, run_lock: ModuleType, path: Path, deadline: float, flocks: FlockRecorder, files: OsRecorder | None) -> None:
        self.deadline = deadline
        self.flocks = flocks
        self.files = files
        self.gave_up_at: float | None = None
        self.flocks_then: list[Call] = []
        self.files_then: list[Call] = []
        super().__init__(run_lock, path)

    async def _hold(self, run_lock: ModuleType, path: Path | None) -> None:
        try:
            async with run_lock.scheduler_run_lock(path, deadline=self.deadline):
                self.entered.set()
                await self.leave.wait()
        except TimeoutError:
            self.gave_up_at = time.monotonic()
            self.flocks_then = self.flocks.recorded()
            self.files_then = [] if self.files is None else self.files.recorded()
            raise

    async def gives_up(self, timeout: type[BaseException], what: str) -> None:
        """Until the wait is over; a red naming ``what`` unless it raised ``timeout`` without running the block, within
        ``WAIT_SECONDS``."""
        await _until(lambda: self.entered.is_set() or self.task.done(), lambda: f"{what}: still waiting; attempts so far {self.flocks.attempts()}")
        if self.entered.is_set():
            pytest.fail(f"{what}: the block ran instead of the wait giving up; attempts {self.flocks.attempts()}")
        error = None if self.task.cancelled() else self.task.exception()
        if not isinstance(error, timeout):
            pytest.fail(f"{what}: the wait {_ending(self.task)} instead of raising {timeout.__name__}; attempts {self.flocks.attempts()}")


@asynccontextmanager
async def _bounded(run_lock: ModuleType, path: Path, deadline: float, flocks: FlockRecorder, files: OsRecorder | None) -> AsyncIterator[BoundedWait]:
    waiting = BoundedWait(run_lock, path, deadline, flocks, files)
    try:
        yield waiting
    finally:
        await waiting.close()


def _assert_nothing_in_flight(waiting: BoundedWait) -> None:
    """At the moment the wait gave up, one descriptor opened per exclusive attempt made, and each already closed: no
    attempt was in flight then, and the refused one's descriptor was closed before the raise."""
    opened = sum(1 for call in waiting.files_then if call.function == "open")
    closed = sum(1 for call in waiting.files_then if call.function == "close")
    attempts = sum(1 for call in waiting.flocks_then if call.operation & fcntl.LOCK_EX)
    assert opened == closed == attempts >= 1, f"when the wait gave up every attempt was over, its descriptor closed: {opened} opened, {closed} closed, {attempts} attempt(s); {waiting.files_then}; {waiting.flocks_then}"


@pytest.fixture(autouse=True)
def data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """The data directory of every test, and of its children, under its ``tmp_path``: no lock of these tests can reach the
    lane's, even one that would ignore its ``path``."""
    folder = tmp_path / "data"
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(folder))
    return folder


# =============================================================================
# (b) THE WAIT
# =============================================================================


@pytest.mark.asyncio
async def test_while_another_process_holds_the_lock_the_block_waits_then_runs_once_it_lets_go(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-001 — contract (b): a child holds ``scheduler_run_lock(path)``. Here the same lock is refused three attempts in a
    row — each ``LOCK_EX | LOCK_NB``, at least ``POLL_SECONDS`` apart — and the block has not run; the child lets go: the
    block runs, the lock refused to others while it runs, and free once it is over."""
    print_section("RL-001: a wait for another process's lock")
    run_lock = _run_lock()
    flocks = _record_flocks(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME

    with _children(tmp_path) as children:
        holder = Holder(children, path)
        await holder.holding()
        assert _probe_here(path) == "refused", "Precondition: the child's lock is refused to a descriptor of this process"
        async with _waiting(run_lock, path) as waiting:
            await waiting.refused(flocks, REFUSALS, "another process")
            refused = flocks.refused()
            gaps = [round(later.at - earlier.at, 3) for earlier, later in zip(refused, refused[1:], strict=False)]
            assert all(gap >= POLL_SECONDS - TIMER_SLACK for gap in gaps), f"an attempt follows a refused one after POLL_SECONDS ({POLL_SECONDS} s) at least: gaps {gaps}"
            assert all(call.operation & fcntl.LOCK_NB for call in flocks.attempts()), f"every attempt is LOCK_EX | LOCK_NB: a blocking flock in a thread could not be cancelled: {flocks.attempts()}"
            holder.release()
            await waiting.runs("the block never ran once the other process let go")
            assert _probe_here(path) == "refused", "while the block runs the lock is held"
        assert _probe_here(path) == "granted", "once the block is over the lock is free"
        await holder.ended()
    print_success(f"{len(refused)} attempts refused {gaps} s apart, then the block ran")


@pytest.mark.asyncio
async def test_a_holder_killed_while_holding_the_lock_lets_the_wait_go_on(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-002 — contract (b): the child holding the lock is killed (SIGKILL) while the block waits here: no ``finally`` of
    its own runs, the kernel releases its lock, and the block runs."""
    print_section("RL-002: the holder killed")
    run_lock = _run_lock()
    flocks = _record_flocks(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME

    with _children(tmp_path) as children:
        holder = Holder(children, path)
        await holder.holding()
        async with _waiting(run_lock, path) as waiting:
            await waiting.refused(flocks, 1, "another process")
            holder.process.kill()
            await _until(lambda: holder.process.poll() is not None, "the killed holder never exited", seconds=REAP_SECONDS)
            assert holder.process.returncode == -signal.SIGKILL, f"Precondition: the holder died of SIGKILL: {holder.process.returncode}"
            await waiting.runs("the block never ran once the holder was killed")
            assert _probe_here(path) == "refused", "while the block runs the lock is held"
    print_success("killed holder, lock taken")


# =============================================================================
# (d) A CANCELLED WAIT
# =============================================================================


@pytest.mark.asyncio
async def test_a_cancelled_wait_leaves_no_descriptor_and_no_lock_behind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-003 — contract (d): while a child holds the lock, the wait here is cancelled after two refused attempts: the task
    ends cancelled, the block never ran, and this process holds as many descriptors as before, none on the lock file. Once
    the child has let go, the lock is free to a new descriptor of this process — no holder was left behind — and a new
    ``scheduler_run_lock`` takes it at its first attempt."""
    print_section("RL-003: a wait cancelled")
    run_lock = _run_lock()
    flocks = _record_flocks(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME

    with _children(tmp_path) as children:
        holder = Holder(children, path)
        await holder.holding()
        before = _descriptors()
        async with _waiting(run_lock, path) as waiting:
            await waiting.refused(flocks, 2, "another process")
            waiting.task.cancel()
            await asyncio.wait({waiting.task}, timeout=WAIT_SECONDS)
            assert waiting.task.cancelled(), f"the cancellation of a wait goes through: {_ending(waiting.task)}"
            assert not waiting.entered.is_set(), "a cancelled wait never runs the block"
            await _until(lambda: _descriptors() == before and not _descriptors_on(path), lambda: f"the cancelled wait left descriptors open: {_descriptors()} instead of {before}, {_descriptors_on(path)} on the lock file")
        holder.release()
        await holder.ended()
        assert _probe_here(path) == "granted", "no holder of the lock was left in this process by the cancelled wait"
        mark = len(flocks.attempts())
        async with _waiting(run_lock, path) as again:
            await again.runs("a new wait never took the free lock")
            assert [call.outcome for call in flocks.attempts()[mark:]] == ["granted"], f"the free lock is taken at the first attempt: {flocks.attempts()[mark:]}"
    print_success("cancelled, nothing left open, the lock free")


@pytest.mark.asyncio
async def test_an_attempt_in_flight_when_the_wait_is_cancelled_releases_the_lock_it_took(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-008 — contract (d): the first attempt is stopped in its worker thread just before its ``flock``, its descriptor
    open, and the wait is cancelled there; let go, the attempt takes the lock — nothing else holds it. The task ends
    cancelled without running the block, and the lock the attempt took is not kept: the descriptor closed, as many as
    before, and the lock free to another process."""
    print_section("RL-008: an attempt in flight when the wait is cancelled")
    run_lock = _run_lock()
    flocks = _record_flocks(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME
    before = _descriptors()
    in_flight, go = flocks.hold_next_attempt()

    try:
        with _children(tmp_path) as children:
            async with _waiting(run_lock, path) as waiting:
                await _until(lambda: in_flight.is_set() or waiting.task.done(), "the first attempt never reached its flock")
                assert in_flight.is_set(), f"Precondition: the first attempt is in flight: {_ending(waiting.task)}"
                waiting.task.cancel()
                for _ in range(LOOP_TURNS):
                    await asyncio.sleep(0)
                go.set()
                await asyncio.wait({waiting.task}, timeout=WAIT_SECONDS)
                assert waiting.task.cancelled(), f"the cancellation of a wait goes through: {_ending(waiting.task)}"
                assert not waiting.entered.is_set(), "a cancelled wait never runs the block"
                await _until(lambda: [call.outcome for call in flocks.attempts()] == ["granted"], lambda: f"Barrier: the attempt in flight took the free lock: {flocks.attempts()}")
                await _until(lambda: _descriptors() == before and not _descriptors_on(path), lambda: f"the lock taken by the attempt in flight was kept: {_descriptors()} descriptors instead of {before}, {_descriptors_on(path)} on the lock file")
            assert await children.probe(path) == "granted", "the lock the attempt in flight took was released: another process takes it"
    finally:
        go.set()
    print_success("taken in flight, released, nothing left open")


# =============================================================================
# (c) THE RELEASE
# =============================================================================


@pytest.mark.asyncio
async def test_an_exception_in_the_block_goes_through_and_another_process_takes_the_lock_at_once(tmp_path: Path) -> None:
    """RL-004 — contract (c): inside the block another process is refused the lock; the block raises: that very exception
    comes out of ``async with``, and another process takes the lock at its first attempt."""
    print_section("RL-004: released on an exception")
    run_lock = _run_lock()
    path = tmp_path / LOCK_FILE_NAME
    inside: list[str] = []

    with _children(tmp_path) as children:

        async def explode() -> None:
            async with run_lock.scheduler_run_lock(path):
                inside.append(await children.probe(path))
                raise BlockExploded("provoked inside the block")

        with pytest.raises(BlockExploded):
            await _within(explode(), "the lock was never taken, though nothing else holds it")
        assert inside == ["refused"], f"Barrier: inside the block the lock is refused to another process: {inside}"
        assert await children.probe(path) == "granted", "once the block raised, another process takes the lock at once"
    print_success("the exception went through; the lock free at once")


# =============================================================================
# (e) THE FILE, A SYMBOLIC LINK
# =============================================================================


async def _refused_at_once(run_lock: ModuleType, link: Path) -> OSError:
    """``scheduler_run_lock(link)`` on a symbolic link: the ``OSError`` it raises; a red if the block runs or the attempts
    go on."""
    ran: list[bool] = []

    async def take() -> None:
        async with run_lock.scheduler_run_lock(link):
            ran.append(True)

    try:
        await asyncio.wait_for(take(), WAIT_SECONDS)
    except TimeoutError:
        pytest.fail(f"a symbolic link at the lock's path is refused at once with OSError, never retried: still trying after {WAIT_SECONDS:.0f} s")
    except OSError as error:
        assert not ran, f"the block ran before {type(error).__name__} was raised"
        return error
    pytest.fail(f"the lock followed the symbolic link {link} -> {os.readlink(link)}: the block ran")


@pytest.mark.asyncio
async def test_the_lock_file_is_created_private_and_kept_and_a_symbolic_link_is_refused(tmp_path: Path) -> None:
    """RL-005 — contract (e): in a folder that does not exist yet, the lock creates the folder and a regular file of mode
    0o600, held while the block runs; once out of the block the file is still there, the same one, and so it is after a
    second block. A symbolic link at the path raises ``OSError`` at once: a dangling link's target is not created; an
    existing file behind a link is neither changed nor locked."""
    print_section("RL-005: the lock file, and a symbolic link in its place")
    run_lock = _run_lock()
    folder = tmp_path / "a-data-directory-not-created-yet"
    path = folder / LOCK_FILE_NAME
    seen: list[tuple[bool, int, int, str]] = []

    async def take() -> None:
        async with run_lock.scheduler_run_lock(path):
            info = os.lstat(path)
            seen.append((stat.S_ISREG(info.st_mode), stat.S_IMODE(info.st_mode), info.st_ino, _probe_here(path)))

    try:
        await _within(take(), "the lock in a folder not created yet was never taken")
    except FileNotFoundError as error:
        pytest.fail(f"the lock creates its folder when it is missing: {error!r}")
    assert path.is_file() and not path.is_symlink(), "once the block is over the lock file is still there, never deleted"
    kept = os.lstat(path)
    await _within(take(), "the lock was never taken a second time")

    assert [(regular, oct(mode), probe) for regular, mode, _, probe in seen] == [(True, oct(LOCK_MODE), "refused")] * 2, f"a regular file of mode 0o600, held while the block runs: {seen}"
    assert {inode for _, _, inode, _ in seen} == {kept.st_ino} and path.exists(), "the lock file stays, the same file, never deleted nor replaced"
    assert _probe_here(path) == "granted", "once the block is over the lock is free"

    behind = tmp_path / "behind-the-links"
    behind.mkdir()
    never = behind / "never-created"
    dangling = tmp_path / "dangling" / LOCK_FILE_NAME
    dangling.parent.mkdir()
    dangling.symlink_to(never)
    first = await _refused_at_once(run_lock, dangling)
    assert not never.exists() and not never.is_symlink(), f"{type(first).__name__}, but the lock followed the link and created {never}"

    existing = behind / "existing-file"
    existing.write_bytes(BEHIND_THE_LINK)
    existing.chmod(BEHIND_THE_LINK_MODE)
    linked = tmp_path / "linked" / LOCK_FILE_NAME
    linked.parent.mkdir()
    linked.symlink_to(existing)
    second = await _refused_at_once(run_lock, linked)
    assert (existing.read_bytes(), oct(stat.S_IMODE(existing.stat().st_mode))) == (BEHIND_THE_LINK, oct(BEHIND_THE_LINK_MODE)), f"{type(second).__name__}, but the file behind the link was changed"
    assert (_descriptors_on(existing), _probe_here(existing)) == ([], "granted"), "nothing behind the link is locked or kept open"
    print_success(f"0o600, kept; links refused ({type(first).__name__}, {type(second).__name__})")


# =============================================================================
# (f) OFF THE LOOP
# =============================================================================


@pytest.mark.asyncio
async def test_open_flock_and_close_never_run_on_the_event_loop_thread(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-006 — contract (f): this test holds the lock from a descriptor of its own, so that the lock under test is refused
    at least once, then lets go; the block runs and ends. Every ``os.open``, ``fcntl.flock`` and ``os.close`` the lock made
    — the refused attempts, the one that took it, its release — ran in a thread other than the event loop's; and every
    descriptor it opened, it closed."""
    print_section("RL-006: open, flock and close off the loop")
    run_lock = _run_lock()
    flocks = _record_flocks(monkeypatch, run_lock)
    files = _record_os(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME
    loop_thread = threading.get_ident()

    mine = os.open(path, os.O_RDWR | os.O_CREAT, LOCK_MODE)
    try:
        fcntl.flock(mine, fcntl.LOCK_EX | fcntl.LOCK_NB)
        async with _waiting(run_lock, path) as waiting:
            await waiting.refused(flocks, 1, "this test")
            fcntl.flock(mine, fcntl.LOCK_UN)
            await waiting.runs("the block never ran once this test let go")
    finally:
        os.close(mine)

    calls = flocks.recorded() + files.recorded()
    outcomes = [call.outcome for call in flocks.recorded()]
    opened = [call for call in files.recorded() if call.function == "open"]
    closed = [call for call in files.recorded() if call.function == "close"]
    assert "refused" in outcomes and outcomes.count("granted") == 1 and outcomes[-1] == "released", f"Barrier: refused, then taken once, then released: {outcomes}"
    assert len(opened) >= 2 and len(closed) == len(opened), f"Barrier: each attempt opens the file, and each descriptor is closed: {files.recorded()}"
    on_the_loop = [(call.function, call.outcome) for call in calls if call.thread == loop_thread]
    assert on_the_loop == [], f"the event loop's thread ran {on_the_loop}: the lock's file I/O runs in a worker thread"
    print_success(f"{len(calls)} calls, none on the loop's thread")


# =============================================================================
# (a) THE MODULE
# =============================================================================


@pytest.mark.asyncio
async def test_the_constants_the_availability_and_the_path_of_the_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> None:
    """RL-007 — contract (a): ``LOCK_FILE_NAME`` ".scheduler.lock" and ``POLL_SECONDS`` 0.2. Here, on POSIX, the module holds
    ``fcntl`` and ``cross_process_lock_available()`` is true; with ``run_lock.fcntl`` None it is false, read at the call.
    ``run_lock_path()`` is the data directory's ``.scheduler.lock``, read at the call; ``scheduler_run_lock()`` without a
    path takes it there, creating the data directory."""
    print_section("RL-007: constants, availability, path")
    run_lock = _run_lock()

    assert (getattr(run_lock, "LOCK_FILE_NAME", None), getattr(run_lock, "POLL_SECONDS", None)) == (LOCK_FILE_NAME, POLL_SECONDS)
    assert run_lock.fcntl is fcntl, f"where fcntl can be imported the module holds it: {run_lock.fcntl!r}"
    assert run_lock.cross_process_lock_available() is True, "with fcntl the lock across processes is available"
    with monkeypatch.context() as patch:
        patch.setattr(run_lock, "fcntl", None)
        assert run_lock.cross_process_lock_available() is False, "without fcntl it is not, read at the call"

    expected = data_dir.resolve() / LOCK_FILE_NAME
    assert get_data_dir() / LOCK_FILE_NAME == expected, "Precondition: the data directory of this test is under its tmp_path"
    assert run_lock.run_lock_path() == expected, f"run_lock_path() is get_data_dir() / {LOCK_FILE_NAME}"
    elsewhere = tmp_path / "another-data-directory"
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(elsewhere))
    assert run_lock.run_lock_path() == elsewhere.resolve() / LOCK_FILE_NAME, "run_lock_path() reads the data directory at the call"
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(data_dir))

    held: list[str] = []

    async def take() -> None:
        async with run_lock.scheduler_run_lock():
            held.append(_probe_here(expected))

    await _within(take(), "the lock of the data directory was never taken")
    assert (held, expected.is_file(), _probe_here(expected)) == (["refused"], True, "granted"), f"scheduler_run_lock() without a path holds {expected}: {held}"
    print_success(f"{LOCK_FILE_NAME}, {POLL_SECONDS} s, available; the data directory's lock")


@pytest.mark.asyncio
async def test_where_fcntl_cannot_be_imported_the_module_imports_and_says_it_is_not_available(tmp_path: Path) -> None:
    """RL-009 — contract (a): in a fresh interpreter where ``import fcntl`` fails, as on a platform without it, the module
    still imports: its ``fcntl`` is None and ``cross_process_lock_available()`` false."""
    print_section("RL-009: a platform without fcntl")
    _run_lock()

    with _children(tmp_path) as children:
        output = await children.run("without-fcntl", WITHOUT_FCNTL, str(REPO_ROOT))

    lines = [line for line in output.splitlines() if line.startswith(WITHOUT_FCNTL_MARK)]
    assert len(lines) == 1, f"the child printed what the module made of it once: {output[-2000:]}"
    assert json.loads(lines[0][len(WITHOUT_FCNTL_MARK) :]) == {"fcntl": "None", "available": False}
    print_success("imported; fcntl None; not available")


# =============================================================================
# (g), (h) THE DEADLINE (Z-26, N79)
# =============================================================================


def test_the_limit_the_timeout_and_the_deadline_keyword() -> None:
    """RL-010 — contract (g), Z-26 (N79): ``LOCK_WAIT_SECONDS`` 600.0; ``SchedulerRunLockTimeout`` a class deriving from
    ``TimeoutError``; ``scheduler_run_lock`` takes ``path``, None by default, then ``deadline``, a keyword only, None by
    default.

    Red before Z-26: neither name exists, and the lock takes no deadline."""
    print_section("RL-010: LOCK_WAIT_SECONDS, SchedulerRunLockTimeout, the keyword deadline")
    run_lock = _run_lock()

    assert getattr(run_lock, "LOCK_WAIT_SECONDS", "<missing>") == LOCK_WAIT_SECONDS, "LOCK_WAIT_SECONDS, the longest a scheduler run waits for another run (Z-26, N79)"
    timeout = getattr(run_lock, "SchedulerRunLockTimeout", None)
    assert isinstance(timeout, type) and issubclass(timeout, TimeoutError), f"SchedulerRunLockTimeout, a TimeoutError raised when another process held the lock past the deadline (Z-26, N79): {timeout!r}"
    signature = inspect.signature(run_lock.scheduler_run_lock)
    shape = [(name, parameter.kind.name, parameter.default) for name, parameter in signature.parameters.items()]
    assert shape == [("path", "POSITIONAL_OR_KEYWORD", None), ("deadline", "KEYWORD_ONLY", None)], f"scheduler_run_lock(path=None, *, deadline=None) (Z-26, N79): {signature}"
    print_success(f"{LOCK_WAIT_SECONDS:.0f} s; {timeout.__name__}, a TimeoutError; scheduler_run_lock{signature}")


@pytest.mark.asyncio
async def test_a_deadline_reached_while_another_process_holds_the_lock_gives_up_and_leaves_nothing_behind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-011 — contract (h), Z-26 (N79): a child holds the lock. Here a wait whose deadline is ``NEAR_SECONDS`` away is
    refused at least once — every attempt ``LOCK_EX | LOCK_NB``, none granted — and gives up with
    ``SchedulerRunLockTimeout``, never before its deadline and within ``WAIT_SECONDS``; the block never ran. At that very
    moment one descriptor had been opened per attempt, and each was closed: no attempt in flight. After it this process
    holds as many descriptors as before, none on the lock file, and the child still holds its lock; once the child lets
    go, ``scheduler_run_lock()`` without a deadline takes the lock at its first attempt.

    Red before Z-26: the module has no ``SchedulerRunLockTimeout``, and its lock no ``deadline``."""
    print_section("RL-011: a deadline reached while another process holds the lock")
    run_lock = _run_lock()
    timeout = _bounded_wait(run_lock)
    flocks = _record_flocks(monkeypatch, run_lock)
    files = _record_os(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME

    with _children(tmp_path) as children:
        holder = Holder(children, path)
        await holder.holding()
        before = _descriptors()
        deadline = time.monotonic() + NEAR_SECONDS
        async with _bounded(run_lock, path, deadline, flocks, files) as waiting:
            await waiting.gives_up(timeout, "a wait whose deadline passed while another process held the lock")
        outcomes = [call.outcome for call in flocks.attempts()]
        assert outcomes and set(outcomes) == {"refused"}, f"Barrier: refused at least once, never granted: {flocks.attempts()}"
        assert all(call.operation & fcntl.LOCK_NB for call in flocks.attempts()), f"every attempt is LOCK_EX | LOCK_NB: {flocks.attempts()}"
        assert waiting.gave_up_at is not None and waiting.gave_up_at >= deadline, f"the wait gives up once its deadline is reached, never before: at {waiting.gave_up_at}, the deadline {deadline}"
        _assert_nothing_in_flight(waiting)
        await _until(lambda: _descriptors() == before and not _left_open(path), lambda: f"the wait that gave up left descriptors open: {_descriptors()} instead of {before}, {_left_open(path)} on the lock file")
        assert _probe_here(path) == "refused", "the other process's lock is untouched by the wait that gave up"
        holder.release()
        await holder.ended()
        mark = len(flocks.attempts())
        async with _waiting(run_lock, path) as again:
            await again.runs("once the other process let go, a wait without a deadline never took the lock")
            assert [call.outcome for call in flocks.attempts()[mark:]] == ["granted"], f"the free lock is taken at the first attempt: {flocks.attempts()[mark:]}"
    print_success(f"{len(outcomes)} attempt(s) refused, given up {waiting.gave_up_at - deadline:.3f} s past the deadline, nothing left; then taken once free")


@pytest.mark.asyncio
async def test_a_free_lock_is_taken_even_with_a_deadline_already_past(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-012 — contract (h), Z-26 (N79): nothing holds the lock, and the deadline is ``PAST_SECONDS`` behind. At least one
    attempt always: that one takes the lock; the block runs, the lock refused to others meanwhile and free once it is
    over; the wait ends without raising.

    Red before Z-26: the module has no ``SchedulerRunLockTimeout``, and its lock no ``deadline``."""
    print_section("RL-012: a free lock, a deadline already past")
    run_lock = _run_lock()
    _bounded_wait(run_lock)
    flocks = _record_flocks(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME
    inside: list[str] = []

    async with _bounded(run_lock, path, time.monotonic() - PAST_SECONDS, flocks, None) as waiting:
        await waiting.runs("with a deadline already past, a free lock was never taken")
        inside.append(_probe_here(path))

    assert (_ending(waiting.task), waiting.gave_up_at) == ("returned", None), f"the block left, the wait over without raising: {_ending(waiting.task)}"
    assert [call.outcome for call in flocks.attempts()] == ["granted"], f"at least one attempt always, and the free lock is taken at it: {flocks.attempts()}"
    assert inside == ["refused"], f"while the block runs the lock is held: {inside}"
    assert _probe_here(path) == "granted", "once the block is over the lock is free"
    print_success("one attempt, granted; the block ran")


@pytest.mark.asyncio
async def test_a_held_lock_with_a_deadline_already_past_is_tried_once_then_given_up(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-013 — contract (h), Z-26 (N79): this test holds the lock from a descriptor of its own, and the deadline is
    ``PAST_SECONDS`` behind: exactly one attempt, refused, then ``SchedulerRunLockTimeout``. The block never ran, nothing
    was in flight when it raised, nothing is left open, and the test's lock is still held. Barriers only: no duration.

    Red before Z-26: the module has no ``SchedulerRunLockTimeout``, and its lock no ``deadline``."""
    print_section("RL-013: a held lock, a deadline already past")
    run_lock = _run_lock()
    timeout = _bounded_wait(run_lock)
    flocks = _record_flocks(monkeypatch, run_lock)
    files = _record_os(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME

    with _held_here(path) as mine:
        before = _descriptors()
        async with _bounded(run_lock, path, time.monotonic() - PAST_SECONDS, flocks, files) as waiting:
            await waiting.gives_up(timeout, "a wait whose deadline was already past, the lock held")
        assert [call.outcome for call in flocks.attempts()] == ["refused"], f"one attempt, refused, then the timeout: none after the deadline: {flocks.attempts()}"
        _assert_nothing_in_flight(waiting)
        await _until(lambda: _descriptors() == before and not _left_open(path, mine), lambda: f"the wait that gave up left descriptors open: {_descriptors()} instead of {before}, {_left_open(path, mine)} on the lock file")
        assert _probe_here(path) == "refused", "the test's lock is untouched by the wait that gave up"
    print_success("one attempt, refused, given up; nothing left")


@pytest.mark.asyncio
async def test_a_holder_that_lets_go_before_the_deadline_lets_the_block_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-014 — contract (h), Z-26 (N79): a child holds the lock. Here a wait whose deadline is ``FAR_SECONDS`` away is
    refused three attempts in a row, each ``LOCK_EX | LOCK_NB``, at least ``POLL_SECONDS`` apart — far from the deadline,
    ``min(POLL_SECONDS, deadline - now)`` is ``POLL_SECONDS`` —, the block not run; the child lets go: the block runs,
    the lock refused to others while it runs and free once it is over, and the wait never gave up.

    Red before Z-26: the module has no ``SchedulerRunLockTimeout``, and its lock no ``deadline``."""
    print_section("RL-014: the holder lets go before the deadline")
    run_lock = _run_lock()
    _bounded_wait(run_lock)
    flocks = _record_flocks(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME

    with _children(tmp_path) as children:
        holder = Holder(children, path)
        await holder.holding()
        async with _bounded(run_lock, path, time.monotonic() + FAR_SECONDS, flocks, None) as waiting:
            await waiting.refused(flocks, REFUSALS, "another process")
            refused = flocks.refused()
            gaps = [round(later.at - earlier.at, 3) for earlier, later in zip(refused, refused[1:], strict=False)]
            assert all(gap >= POLL_SECONDS - TIMER_SLACK for gap in gaps), f"far from the deadline an attempt follows a refused one after POLL_SECONDS ({POLL_SECONDS} s) at least: gaps {gaps}"
            assert all(call.operation & fcntl.LOCK_NB for call in flocks.attempts()), f"every attempt is LOCK_EX | LOCK_NB: {flocks.attempts()}"
            holder.release()
            await waiting.runs("the block never ran once the other process let go before the deadline")
            assert _probe_here(path) == "refused", "while the block runs the lock is held"
        assert (_ending(waiting.task), waiting.gave_up_at) == ("returned", None), f"the wait never gave up: {_ending(waiting.task)}"
        assert _probe_here(path) == "granted", "once the block is over the lock is free"
        await holder.ended()
    print_success(f"{len(refused)} attempts refused {gaps} s apart, then the block ran; no timeout")


@pytest.mark.asyncio
async def test_an_attempt_in_flight_when_the_deadline_passes_is_awaited_and_none_follows_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-015 — contract (h), Z-26 (N79): this test holds the lock from a descriptor of its own. The wait's first attempt
    is stopped in its thread just before its ``flock``, its descriptor open, until the deadline — ``NEAR_SECONDS`` away —
    is ``WATCH_SECONDS`` past: all that time the wait is still on, waiting for its attempt. Let go, the attempt is refused
    and the wait gives up with ``SchedulerRunLockTimeout`` without another one: a single attempt, nothing in flight when it
    raised, nothing left open.

    Red before Z-26: the module has no ``SchedulerRunLockTimeout``, and its lock no ``deadline``."""
    print_section("RL-015: the deadline passes during an attempt")
    run_lock = _run_lock()
    timeout = _bounded_wait(run_lock)
    flocks = _record_flocks(monkeypatch, run_lock)
    files = _record_os(monkeypatch, run_lock)
    path = tmp_path / LOCK_FILE_NAME
    in_flight, go = flocks.hold_next_attempt()

    try:
        with _held_here(path) as mine:
            before = _descriptors()
            deadline = time.monotonic() + NEAR_SECONDS
            async with _bounded(run_lock, path, deadline, flocks, files) as waiting:
                await _until(lambda: in_flight.is_set() or waiting.task.done(), "the first attempt never reached its flock")
                assert in_flight.is_set(), f"Precondition: the first attempt is in flight: {_ending(waiting.task)}"
                await _until(lambda: time.monotonic() > deadline + WATCH_SECONDS or waiting.task.done(), "the deadline never passed")
                assert not waiting.task.done(), f"the wait gave up with its attempt in flight, its descriptor open: {_ending(waiting.task)}; recorded then {waiting.files_then}"
                go.set()
                await waiting.gives_up(timeout, "once its attempt in flight across the deadline was refused, the wait")
            assert [call.outcome for call in flocks.attempts()] == ["refused"], f"the attempt in flight was awaited, and none followed it past the deadline: {flocks.attempts()}"
            _assert_nothing_in_flight(waiting)
            await _until(lambda: _descriptors() == before and not _left_open(path, mine), lambda: f"the wait that gave up left descriptors open: {_descriptors()} instead of {before}, {_left_open(path, mine)} on the lock file")
    finally:
        go.set()
    print_success("the attempt in flight awaited past the deadline, refused, then given up without another")


@pytest.mark.asyncio
async def test_the_wait_before_an_attempt_is_cut_to_the_deadline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """RL-016 — contract (h), Z-26 (N79): ``POLL_SECONDS`` set to an hour — read at each wait — and the lock held by a
    descriptor of this test: a wait whose deadline is ``NEAR_SECONDS`` away still gives up with
    ``SchedulerRunLockTimeout`` within ``WAIT_SECONDS``, never before its deadline. The wait after a refused attempt is
    ``min(POLL_SECONDS, deadline - now)``, never a whole ``POLL_SECONDS`` past the deadline.

    Red before Z-26: the module has no ``SchedulerRunLockTimeout``, and its lock no ``deadline``."""
    print_section("RL-016: the wait before an attempt cut to the deadline")
    run_lock = _run_lock()
    timeout = _bounded_wait(run_lock)
    flocks = _record_flocks(monkeypatch, run_lock)
    monkeypatch.setattr(run_lock, "POLL_SECONDS", POLL_HOUR)
    path = tmp_path / LOCK_FILE_NAME

    with _held_here(path):
        deadline = time.monotonic() + NEAR_SECONDS
        async with _bounded(run_lock, path, deadline, flocks, None) as waiting:
            await waiting.gives_up(timeout, f"with POLL_SECONDS {POLL_HOUR:.0f} s, a wait whose deadline was {NEAR_SECONDS} s away: the wait before an attempt is min(POLL_SECONDS, deadline - now)")
        outcomes = [call.outcome for call in flocks.attempts()]
        assert outcomes and set(outcomes) == {"refused"}, f"Barrier: refused at least once, never granted: {flocks.attempts()}"
        assert waiting.gave_up_at is not None and waiting.gave_up_at >= deadline, f"the wait gives up once its deadline is reached, never before: at {waiting.gave_up_at}, the deadline {deadline}"
    print_success(f"{len(outcomes)} attempt(s) refused; given up {waiting.gave_up_at - deadline:.3f} s past the deadline, not an hour")
