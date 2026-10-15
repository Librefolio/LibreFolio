"""The shutdown budget in a real server process: SIGTERM and SIGINT under the uvicorn CLI, with a budget of 2 s (plan phase01SleepWake §Z6b, decision 35, lot Z6b part 2).

Each test starts its own server — ``_shutdown_budget_app.py``, the real pieces of ``lifecycle`` and ``shutdown_budget``
wired as ``app_lifespan`` wires them — waits until ``/ping`` answers on its Unix socket, signals it, and measures the time
to its exit. The environment is the server's whole environment: ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=2`` and what
``uvicorn_drain_env()`` adds for it, ``UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN=1``. Without the budget these servers stop after
30 s, or never; with it, within 6 s. The contract pinned here:

1. Barrier, for every server: ``/ping`` answers from the process the test started, with the budget it was given and a
   watchdog installed exactly when the budget is above 0 — under the uvicorn CLI, SIGTERM's and SIGINT's handlers are
   uvicorn's ``Server.handle_exit``, the only one ``install_shutdown_watchdog`` wraps.
2. (a) SIGTERM with ``/slow`` in flight: uvicorn drains it for 1 s, then cancels it — the handler sees the cancellation —
   and the server exits within 6 s.
3. (b) A shutdown step that never ends: it is cut at the steps' deadline, with a WARNING «Shutdown step cut by the
   deadline» naming it, and the server exits within 6 s.
4. (c) SIGINT with a non-daemon thread blocked: once uvicorn returns, the interpreter would wait for the thread forever.
   The watchdog ends the process at the budget: status 1, within 6 s, after an ERROR «Shutdown budget exhausted» naming
   the thread.
5. (d) A child process that ignores SIGTERM: the last step kills it, the server exits within 6 s, the child is gone, and
   the server says it killed it — in the last step's line or, when the watchdog ended the process, in that line or in
   the watchdog's report, which names only the children still alive when it fires.
6. (e) Budget 0: no watchdog and no drain variable; a 4 s shutdown step runs to its end: the server still runs 2.5 s after
   SIGTERM, exits after the step, within 10 s, with status -SIGTERM; nothing cut, no watchdog.
7. (f) Nothing pending: the server exits within 3 s, with status -SIGTERM; no watchdog.
8. (g) The wiring of ``app_lifespan``, in this process, no server: the watchdog is the first startup step, the child
   processes the last shutdown step, and ``app_lifespan.shutdown_deadline`` is ``shutdown_budget.shutdown_deadline``.

Every shutdown here begins with a signal, and the signal arms the watchdog. That a shutdown without one arms nothing —
the lifespan run by a test, a server at its request limit — is pinned in-process, by SDB-044 of
``test_shutdown_budget.py``.

The exit statuses, read in uvicorn 0.52.4 (``Server.capture_signals``) and Python 3.13 (``asyncio.Runner``):

- after SIGTERM, uvicorn puts back the handler it found — the default one, or coverage's in a measured run, which saves
  its data and sends SIGTERM again — and raises the signal once the lifespan is done: status -SIGTERM. With the budget
  above 0 the watchdog races that path: it ends the process at 2 s with status 1, logging «Shutdown budget exhausted».
  Cases (a), (b) and (d) take about 1.3 s, 1.4 s and 0.8 s of the 2 s, so either status is accepted there, the second
  only with the watchdog's report. Cases (e) (no watchdog) and (f) (about 0.3 s) pin -SIGTERM;
- after SIGINT, uvicorn raises it again into ``asyncio.Runner``'s handler, which turns it into a ``KeyboardInterrupt``
  that ``uvicorn.run`` swallows; the interpreter then waits for its non-daemon threads. Case (c) pins status 1: only the
  watchdog ends it.

PURE: no lane port, no database. Each server listens on a Unix socket in a short directory of its own under ``/tmp`` —
an AF_UNIX path holds 104 bytes on macOS, fewer than pytest's ``tmp_path`` there —; its data directory, its files and
its log are in ``tmp_path``. Its environment holds nothing of the lane's; in a measured run it also gets the coverage
start-up, as every child the runner starts. Every server is started in a session of its own and, at teardown, killed
with its whole process group if it still runs, then reaped; a child of the server the test learnt about is killed if it
is still the same process. No test waits on the clock: each wait is for a condition — an answer, a file, an exit — with
a deadline, but case (e), whose subject is the server still running at 2.5 s.

Each test starts one server (1–2 s) and waits for its exit (0.3–4.5 s); with the import of ``app_lifespan`` in (g), about
25 s in all.

Red until H's CP2b brings ``backend/app/services/platform/lifecycle.py`` and ``app_lifespan.py``: the server does not start
— its module does not import —, and (g) does not import the wiring.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any

import httpx
import psutil
import pytest

from backend.app.config.sleep_wake import uvicorn_drain_env
from backend.app.services.platform import shutdown_budget
from backend.test_scripts.test_utils import print_section, print_success

REPO_ROOT = Path(__file__).resolve().parents[3]
APP = "backend.test_scripts.test_services._shutdown_budget_app:app"
BASE_URL = "http://z6b"

#: Written out, not imported: the server's module configures logging at import, so this process never imports it.
APP_DIR_VARIABLE = "Z6B_APP_DIR"
HANGING_STEP_SWITCH = "Z6B_APP_HANGING_STEP"
SLEEP_STEP_SWITCH = "Z6B_APP_SLEEP_STEP_SECONDS"
BLOCKED_THREAD_SWITCH = "Z6B_APP_BLOCKED_THREAD"
STUBBORN_CHILD_SWITCH = "Z6B_APP_STUBBORN_CHILD"
HANGING_STEP = "z6b-hanging-step"
BLOCKED_THREAD = "z6b-blocked-thread"
BUDGET_VARIABLE = "LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS"
DRAIN_VARIABLE = "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN"

#: What the server logs, as read here: a step cut (``lifecycle``), the watchdog's exit and the children the last step
#: had to kill (``shutdown_budget``).
CUT_EVENT = "Shutdown step cut by the deadline"
WATCHDOG_EVENT = "Shutdown budget exhausted"
CHILDREN_KILLED_EVENT = "Child processes killed at shutdown"

BUDGET_SECONDS = 2
#: What ``uvicorn_drain_env()`` adds for a budget of 2 s.
DRAIN_SECONDS = "1"
#: An exit this soon after the signal proves the budget: without it these servers stop after 30 s, or never.
EXIT_BOUND_SECONDS = 6.0
QUICK_EXIT_SECONDS = 3.0
#: Budget 0: the shutdown step sleeps this long; the server must still run at ALIVE_AT_SECONDS, and be gone by
#: NO_LIMIT_EXIT_SECONDS.
SLEEP_STEP_SECONDS = 4
ALIVE_AT_SECONDS = 2.5
NO_LIMIT_EXIT_SECONDS = 10.0
#: How long a server may take to answer ``/ping``: the machine can be loaded.
STARTUP_SECONDS = 30.0
POLL_SECONDS = 0.05
REAP_SECONDS = 10.0
#: AF_UNIX paths hold 104 bytes on macOS (108 on Linux): the sockets go in a short directory, not in ``tmp_path``.
SHORT_TMP = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
SOCKET_PATH_LIMIT = 100

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="a server on a Unix socket, ended by POSIX signals")


def _tail(text: str, lines: int = 80) -> str:
    return "\n".join(text.splitlines()[-lines:])


def _lines(output: str, needle: str) -> list[str]:
    """The lines of ``output`` that contain ``needle``."""
    return [line for line in output.splitlines() if needle in line]


def _holds_pid(text: str, pid: int) -> bool:
    """``pid`` appears in ``text`` as a whole number, not as the digits of a longer one."""
    return re.search(rf"(?<![0-9]){pid}(?![0-9])", text) is not None


def _still_alive(process: psutil.Process) -> bool:
    """``process`` is still the same live process: not gone, not a zombie, its pid not reused."""
    try:
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def _gone_within(process: psutil.Process, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while _still_alive(process):
        if time.monotonic() >= deadline:
            return False
        with contextlib.suppress(psutil.TimeoutExpired, psutil.NoSuchProcess):
            process.wait(timeout=POLL_SECONDS)
    return True


def _server_env(root: Path, app_dir: Path, *, budget: int, switches: Mapping[str, str]) -> dict[str, str]:
    """The server's whole environment: nothing of the lane's — no UVICORN_*, no LIBREFOLIO_* but these —, its data in ``tmp_path``."""
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": os.environ.get("HOME", str(root)),
        "PYTHONPATH": str(REPO_ROOT),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "LIBREFOLIO_DATA_DIR": str(root / "data"),
        BUDGET_VARIABLE: str(budget),
        APP_DIR_VARIABLE: str(app_dir),
        **switches,
    }
    env.update(uvicorn_drain_env(env))
    if os.environ.get("COVERAGE_PROCESS_START"):
        # A measured run measures the server too, as every child the runner starts (_common.apply_subprocess_coverage_env):
        # coverage starts with the interpreter, its data lands beside this run's, and the watchdog saves it before
        # os._exit. The parent's PYTHONPATH carries the coverage start-up directory.
        env["COVERAGE_PROCESS_START"] = os.environ["COVERAGE_PROCESS_START"]
        if "COVERAGE_FILE" in os.environ:
            env["COVERAGE_FILE"] = os.environ["COVERAGE_FILE"]
        env["PYTHONPATH"] = os.pathsep.join([str(REPO_ROOT), *(part for part in os.environ.get("PYTHONPATH", "").split(os.pathsep) if part)])
    return env


class ServerProcess:
    """One server under the uvicorn CLI: its socket in a short directory, its data, files and log in ``root``."""

    def __init__(self, root: Path, socket: Path, *, budget: int, switches: Mapping[str, str]) -> None:
        assert len(os.fsencode(socket)) < SOCKET_PATH_LIMIT, f"barrier: the socket path {socket} is too long for AF_UNIX"
        self.root = root
        self.app_dir = root / "app"
        self.app_dir.mkdir(parents=True)
        (root / "data").mkdir()
        self.log_path = root / "server.log"
        self.socket = socket
        self.budget = budget
        self.env = _server_env(root, self.app_dir, budget=budget, switches=switches)
        self.process: subprocess.Popen[bytes] | None = None
        #: What ``/ping`` answered once the server served.
        self.info: dict[str, Any] = {}
        self.signalled_at: float | None = None
        #: Processes the server started, killed at teardown if they are still the same processes.
        self.others: list[psutil.Process] = []

    def start(self) -> None:
        """Start the server and wait until it serves; the barrier of contract 1 on what ``/ping`` answers."""
        expected_drain = DRAIN_SECONDS if self.budget == BUDGET_SECONDS else None
        assert self.env.get(DRAIN_VARIABLE) == expected_drain, f"barrier: uvicorn_drain_env() gave {self.env.get(DRAIN_VARIABLE)!r} for a budget of {self.budget}, not {expected_drain!r}"
        command = [sys.executable, "-m", "uvicorn", APP, "--uds", str(self.socket), "--lifespan", "on"]
        with self.log_path.open("wb") as log:
            self.process = subprocess.Popen(command, cwd=REPO_ROOT, env=self.env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self.info = info = self._wait_until_serving()
        assert info.get("pid") == self.process.pid, f"barrier: /ping answered from pid {info.get('pid')}, not from the server started here ({self.process.pid})"
        assert info.get("budget_seconds") == self.budget, f"barrier: the server read a budget of {info.get('budget_seconds')}, not {self.budget}"
        assert info.get("watchdog") is (self.budget > 0), f"barrier: watchdog installed {info.get('watchdog')} with a budget of {self.budget}"

    def client(self, timeout: float) -> httpx.Client:
        return httpx.Client(transport=httpx.HTTPTransport(uds=str(self.socket)), timeout=timeout)

    def output(self) -> str:
        return self.log_path.read_text(encoding="utf-8", errors="replace") if self.log_path.exists() else ""

    def _keeps_running(self, seconds: float, while_doing: str) -> None:
        """Wait ``seconds`` for the server to exit, and fail if it does: it was not meant to while ``while_doing``."""
        assert self.process is not None
        try:
            self.process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return
        pytest.fail(f"the server exited with status {self.process.returncode} while {while_doing}:\n{_tail(self.output())}")

    def _wait_until_serving(self) -> dict[str, Any]:
        deadline = time.monotonic() + STARTUP_SECONDS
        problem = "its socket was never created"
        while time.monotonic() < deadline:
            if self.socket.exists():
                try:
                    with self.client(timeout=5.0) as client:
                        response = client.get(f"{BASE_URL}/ping")
                    if response.status_code == 200:
                        return response.json()
                    problem = f"/ping answered {response.status_code}"
                except httpx.HTTPError as error:
                    problem = repr(error)
            self._keeps_running(POLL_SECONDS, "starting")
        pytest.fail(f"the server did not answer /ping within {STARTUP_SECONDS} s ({problem}):\n{_tail(self.output())}")

    def wait_for_file(self, name: str) -> Path:
        """``app_dir / name``, once the server has written it."""
        path = self.app_dir / name
        deadline = time.monotonic() + STARTUP_SECONDS
        while not path.exists():
            if time.monotonic() >= deadline:
                pytest.fail(f"the server did not write {name} within {STARTUP_SECONDS} s:\n{_tail(self.output())}")
            self._keeps_running(POLL_SECONDS, f"the test waited for {name}")
        return path

    def send(self, signum: int) -> None:
        assert self.process is not None
        self.signalled_at = time.monotonic()
        self.process.send_signal(signum)

    def since_signal(self) -> float:
        assert self.signalled_at is not None
        return time.monotonic() - self.signalled_at

    def still_runs_at(self, seconds: float) -> None:
        """The server is still running ``seconds`` after the signal."""
        self._keeps_running(max(0.0, seconds - self.since_signal()), f"it had to run at least {seconds} s after the signal")

    def exits_within(self, seconds: float) -> float:
        """Wait for the server to exit at most ``seconds`` after the signal; the seconds it took."""
        assert self.process is not None
        try:
            self.process.wait(timeout=max(0.0, seconds - self.since_signal()))
        except subprocess.TimeoutExpired:
            pytest.fail(f"the server still runs {seconds} s after the signal:\n{_tail(self.output())}")
        return self.since_signal()

    def cleanup(self) -> None:
        """Kill the server with its whole process group if it still runs, reap it, and kill what it left behind."""
        if self.process is not None:
            if self.process.poll() is None:
                # Not reaped yet, so its pid — the id of its group, the session it was started in — names nobody else.
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(self.process.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=REAP_SECONDS)
        for process in self.others:
            if _still_alive(process):
                with contextlib.suppress(psutil.Error):
                    process.kill()


class InFlightRequest:
    """A GET sent from a thread of the test, waiting for its answer while the test signals the server."""

    def __init__(self, server: ServerProcess, path: str) -> None:
        self.outcome: list[object] = []
        self._server = server
        self._path = path
        self._thread = threading.Thread(target=self._send, name="sdp-in-flight", daemon=True)
        self._thread.start()

    def _send(self) -> None:
        try:
            with self._server.client(timeout=60.0) as client:
                self.outcome.append(client.get(f"{BASE_URL}{self._path}").status_code)
        except httpx.HTTPError as error:
            self.outcome.append(error)

    def join(self) -> None:
        self._thread.join(REAP_SECONDS)


def _ended_by_the_signal_or_the_watchdog(server: ServerProcess) -> int:
    """After SIGTERM with a budget: uvicorn raised the signal again once the lifespan was done (-SIGTERM), or the watchdog ended the process first (1) and said so."""
    assert server.process is not None
    code = server.process.returncode
    if code == -signal.SIGTERM:
        return code
    output = server.output()
    assert code == 1, f"exit status {code}: neither -SIGTERM (uvicorn raising the signal again) nor 1 (the watchdog):\n{_tail(output)}"
    assert _lines(output, WATCHDOG_EVENT), f"exit status 1 without the watchdog's report:\n{_tail(output)}"
    return code


@pytest.fixture
def socket_dir() -> Iterator[Path]:
    directory = Path(tempfile.mkdtemp(prefix="lf-z6b-", dir=SHORT_TMP))
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


@pytest.fixture
def servers(tmp_path: Path, socket_dir: Path) -> Iterator[Callable[..., ServerProcess]]:
    """Start a server — budget 2 s unless given, with the case's switches —; at teardown, every server started is killed and reaped."""
    started: list[ServerProcess] = []

    def start(*, budget: int = BUDGET_SECONDS, switches: Mapping[str, str] | None = None) -> ServerProcess:
        index = len(started)
        server = ServerProcess(tmp_path / f"server-{index}", socket_dir / f"s{index}.sock", budget=budget, switches=switches or {})
        started.append(server)
        server.start()
        return server

    yield start
    for server in started:
        server.cleanup()


# =============================================================================
# 2-7. A SERVER PROCESS, SIGNALLED
# =============================================================================


@POSIX_ONLY
def test_sigterm_cancels_a_request_in_flight_after_the_drain(servers: Callable[..., ServerProcess]) -> None:
    """SDP-001 — contract 2 (a): SIGTERM while ``/slow`` sleeps its 30 s: uvicorn drains it for 1 s, then cancels it — ``slow-cancelled``, never ``slow-finished`` —, and the server exits within 6 s, by the signal or by the watchdog.

    The cancellation is the drain's: the watchdog ends the process with ``os._exit``, which cancels nothing.
    """
    print_section("SDP-001: SIGTERM with a request in flight")
    server = servers()
    request = InFlightRequest(server, "/slow")
    server.wait_for_file("slow-started")

    server.send(signal.SIGTERM)
    elapsed = server.exits_within(EXIT_BOUND_SECONDS)
    request.join()

    assert (server.app_dir / "slow-cancelled").exists(), f"the request in flight was never cancelled (the client got {request.outcome}):\n{_tail(server.output())}"
    assert not (server.app_dir / "slow-finished").exists(), "the request in flight ran its 30 s to the end"
    code = _ended_by_the_signal_or_the_watchdog(server)
    print_success(f"cancelled after the drain; status {code} after {elapsed:.2f} s")


@POSIX_ONLY
def test_a_shutdown_step_that_never_ends_is_cut_at_the_deadline(servers: Callable[..., ServerProcess]) -> None:
    """SDP-002 — contract 3 (b): a shutdown step whose ``run`` returns ``asyncio.sleep(3600)``: after SIGTERM it is cut at the steps' deadline — a «Shutdown step cut by the deadline» line names it — and the server exits within 6 s."""
    print_section("SDP-002: a shutdown step that never ends")
    server = servers(switches={HANGING_STEP_SWITCH: "1"})

    server.send(signal.SIGTERM)
    elapsed = server.exits_within(EXIT_BOUND_SECONDS)

    output = server.output()
    cuts = _lines(output, CUT_EVENT)
    assert any(HANGING_STEP in line for line in cuts), f"no {CUT_EVENT!r} line names {HANGING_STEP}:\n{_tail(output)}"
    code = _ended_by_the_signal_or_the_watchdog(server)
    print_success(f"{HANGING_STEP} cut; status {code} after {elapsed:.2f} s")


@POSIX_ONLY
def test_sigint_with_a_blocked_thread_is_ended_by_the_watchdog(servers: Callable[..., ServerProcess]) -> None:
    """SDP-003 — contract 4 (c): SIGINT with a non-daemon thread blocked forever. uvicorn shuts down and returns, then the interpreter waits for the thread: only the watchdog ends the process, at the budget — status 1, not before 2 s, within 6 s — after an ERROR «Shutdown budget exhausted» that names the thread."""
    print_section("SDP-003: SIGINT with a blocked non-daemon thread")
    server = servers(switches={BLOCKED_THREAD_SWITCH: "1"})
    assert BLOCKED_THREAD in server.info.get("threads", []), f"barrier: {BLOCKED_THREAD} is not running: {server.info}"

    server.send(signal.SIGINT)
    elapsed = server.exits_within(EXIT_BOUND_SECONDS)

    assert server.process is not None
    output = server.output()
    assert server.process.returncode == 1, f"exit status {server.process.returncode}, not the watchdog's 1:\n{_tail(output)}"
    reports = _lines(output, WATCHDOG_EVENT)
    assert reports, f"no {WATCHDOG_EVENT!r} line:\n{_tail(output)}"
    assert any(BLOCKED_THREAD in line for line in reports), f"the watchdog's report does not name {BLOCKED_THREAD}: {reports}"
    assert elapsed >= BUDGET_SECONDS - 0.05, f"the process ended {elapsed:.2f} s after SIGINT, before the {BUDGET_SECONDS} s budget"
    print_success(f"ended by the watchdog after {elapsed:.2f} s, the thread named")


@POSIX_ONLY
def test_a_child_that_ignores_sigterm_is_killed_before_the_server_exits(servers: Callable[..., ServerProcess]) -> None:
    """SDP-004 — contract 5 (d): the server started a child that ignores SIGTERM. After SIGTERM the server exits within 6 s, the child is gone, and the server says it killed it: the last step («Child processes killed at shutdown») when uvicorn ended it. When the watchdog did, either that line — the step killed the child before the watchdog fired, and its report names only the children still alive — or the watchdog's report."""
    print_section("SDP-004: a child that ignores SIGTERM")
    server = servers(switches={STUBBORN_CHILD_SWITCH: "1"})
    pid = int(server.wait_for_file("child.pid").read_text(encoding="utf-8"))
    child = psutil.Process(pid)
    server.others.append(child)
    assert server.process is not None and child.ppid() == server.process.pid, f"barrier: {pid} is not the server's child"

    server.send(signal.SIGTERM)
    elapsed = server.exits_within(EXIT_BOUND_SECONDS)

    output = server.output()
    assert _gone_within(child, 5.0), f"the child {pid} still runs after the server exited:\n{_tail(output)}"
    code = _ended_by_the_signal_or_the_watchdog(server)
    killers = (CHILDREN_KILLED_EVENT,) if code == -signal.SIGTERM else (CHILDREN_KILLED_EVENT, WATCHDOG_EVENT)
    named = [line for killer in killers for line in _lines(output, killer) if _holds_pid(line, pid)]
    assert named, f"no {' or '.join(map(repr, killers))} line names the child {pid}:\n{_tail(output)}"
    print_success(f"the child killed; status {code} after {elapsed:.2f} s")


@POSIX_ONLY
def test_with_a_budget_of_0_a_long_shutdown_step_runs_to_its_end(servers: Callable[..., ServerProcess]) -> None:
    """SDP-005 — contract 6 (e): ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS=0``, no drain variable, no watchdog. A shutdown step that sleeps 4 s runs to its end: the server still runs 2.5 s after SIGTERM, then exits after the step, within 10 s, with status -SIGTERM; nothing is cut and no watchdog reports."""
    print_section("SDP-005: no limit")
    server = servers(budget=0, switches={SLEEP_STEP_SWITCH: str(SLEEP_STEP_SECONDS)})
    assert DRAIN_VARIABLE not in server.env, "barrier: a drain variable without a limit"

    server.send(signal.SIGTERM)
    server.still_runs_at(ALIVE_AT_SECONDS)
    elapsed = server.exits_within(NO_LIMIT_EXIT_SECONDS)

    assert server.process is not None
    output = server.output()
    assert (server.app_dir / "sleep-step-finished").exists(), f"the {SLEEP_STEP_SECONDS} s step did not reach its end:\n{_tail(output)}"
    assert elapsed >= SLEEP_STEP_SECONDS - 0.1, f"the server exited {elapsed:.2f} s after SIGTERM, before its {SLEEP_STEP_SECONDS} s step could end"
    assert server.process.returncode == -signal.SIGTERM, f"exit status {server.process.returncode}, not -SIGTERM:\n{_tail(output)}"
    assert not _lines(output, CUT_EVENT), f"a step was cut without a limit: {_lines(output, CUT_EVENT)}"
    assert not _lines(output, WATCHDOG_EVENT), f"a watchdog fired without a limit: {_lines(output, WATCHDOG_EVENT)}"
    print_success(f"the step ran its {SLEEP_STEP_SECONDS} s; status -SIGTERM after {elapsed:.2f} s")


@POSIX_ONLY
def test_with_nothing_pending_sigterm_ends_the_server_at_once(servers: Callable[..., ServerProcess]) -> None:
    """SDP-006 — contract 7 (f): no request, no step to wait for: the server exits within 3 s of SIGTERM, with status -SIGTERM — uvicorn raising the signal again, the watchdog never needed."""
    print_section("SDP-006: nothing pending")
    server = servers()

    server.send(signal.SIGTERM)
    elapsed = server.exits_within(QUICK_EXIT_SECONDS)

    assert server.process is not None
    output = server.output()
    assert server.process.returncode == -signal.SIGTERM, f"exit status {server.process.returncode}, not -SIGTERM:\n{_tail(output)}"
    assert not _lines(output, CUT_EVENT), f"a step was cut with nothing pending: {_lines(output, CUT_EVENT)}"
    assert not _lines(output, WATCHDOG_EVENT), f"the watchdog fired with nothing pending: {_lines(output, WATCHDOG_EVENT)}"
    print_success(f"status -SIGTERM after {elapsed:.2f} s")


# =============================================================================
# 8. THE WIRING OF app_lifespan
# =============================================================================


def test_the_lifespan_wires_the_watchdog_the_deadline_and_the_child_processes() -> None:
    """SDP-007 — contract 8 (g): in ``app_lifespan``, the watchdog is the first startup step, the child processes the last shutdown step, and ``shutdown_deadline`` is ``shutdown_budget.shutdown_deadline`` itself."""
    print_section("SDP-007: the wiring of app_lifespan")
    from backend.app.services.platform import app_lifespan  # noqa: PLC0415 — deliberate: only this test reads the wiring; imported at collection, a fault in it would stop the process tests too, which never load it

    startup = [step.name for step in app_lifespan.STARTUP_STEPS]
    shutdown = [step.name for step in app_lifespan.SHUTDOWN_STEPS]
    assert startup[:1] == ["shutdown-watchdog"], f"the first startup step is not the watchdog: {startup}"
    assert shutdown[-1:] == ["child-processes"], f"the last shutdown step is not the child processes: {shutdown}"
    assert app_lifespan.shutdown_deadline is shutdown_budget.shutdown_deadline, f"app_lifespan.shutdown_deadline is {app_lifespan.shutdown_deadline!r}, not shutdown_budget's"
    print_success(f"first {startup[0]}, last {shutdown[-1]}, the deadline of shutdown_budget")
