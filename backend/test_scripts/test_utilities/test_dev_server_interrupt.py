"""Ctrl+C on ``./dev.py server`` lets the server finish its own shutdown, and a SIGTERM to ``dev.py`` reaches it (Z-10).

The defect: ``cmd_server`` (``dev.py``) starts uvicorn through ``run_command_live`` (``scripts/cli_base.py``), that is
``subprocess.run``; ``pipenv run`` replaces itself with uvicorn, so uvicorn is ``dev.py``'s own child. Ctrl+C sends
SIGINT to the whole foreground group: uvicorn starts its graceful shutdown, whose budget is
``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`` (8 s by default, ``backend/app/config/sleep_wake.py``), while ``subprocess.run``
catches the ``KeyboardInterrupt``, waits for its child 0.25 s (CPython's ``Popen._sigint_wait_secs``) and SIGKILLs it:
no drain, jobs not stopped in order, writes cut. A SIGTERM sent to ``dev.py`` alone, as a process supervisor sends it,
kills ``dev.py`` (default action) and leaves the server running without a parent.

The contract (Z-10, decisions N-Z10-1 and N-Z10-2):

* ``scripts.cli_base.run_server_live(cmd, env=None, grace_seconds=None) -> int`` starts ``cmd`` with ``Popen`` in the
  project root, with ``os.environ`` plus ``env``, and returns the child's exit code when the child stops by itself, 1
  when it cannot start. The first Ctrl+C is not forwarded: the terminal already gave it to the whole group, and uvicorn
  forces its exit at a second SIGINT. It prints a line holding ``Interrupted``, waits for the child up to
  ``grace_seconds`` (None: no limit) and returns 130. A SIGTERM is forwarded to the child, a line holding ``SIGTERM`` is
  printed, the wait is the same, and it returns 143; a child that stops by itself after that first signal still gives
  130 or 143. A second signal (Ctrl+C or SIGTERM) while waiting, or the grace running out, SIGKILLs the child and waits
  for it; the code stays the first signal's. It takes over SIGINT and SIGTERM during the call only, in the main thread
  only, and only where their handlers are the usual ones (``signal.default_int_handler``, ``signal.SIG_DFL``): an
  ignored or custom handler stays. The handlers in force before the call are back when it returns.
  ``run_command_live`` stays as it is.
* ``dev._server_stop_grace(env)``: the shutdown budget ``shutdown_timeout_seconds(env)`` plus 2 s; unset or blank 10.0,
  ``5`` 7.0, ``2`` 4.0, ``0`` None (no limit), a value that cannot be used 10.0 (the default 8, plus 2).
* ``cmd_server`` launches uvicorn with ``run_server_live(uvicorn_cmd, env=env, grace_seconds=_server_stop_grace(env))``,
  never with ``run_command_live``; ``--coverage`` still replaces ``dev.py`` with ``coverage run`` (``os.execvpe``).

The signal cases (a to f) run two Python scripts written under ``tmp_path``: a wrapper standing in for ``dev.py`` and a
fake server. The wrapper starts in a session of its own (``start_new_session=True``), sets the usual SIGINT and SIGTERM
handlers, the ones ``dev.py`` has from a terminal and ``run_server_live`` takes over (the test process may ignore SIGINT
or block a signal, and a child inherits both), runs the fake server through ``run_server_live``, reports whether both
handlers are back once the call has returned, and exits with what the call returned. The fake server records every
SIGINT and SIGTERM it gets, starts its shutdown at the first and writes ``done`` when the shutdown is over. Signals go
to the wrapper's process group, as the terminal's Ctrl+C and the test runner's stop send them, or to the wrapper's pid
alone, as a supervisor sends them: never anywhere else. Every step waits for a handshake (the fake server's ``ready``,
its record of a signal, the wrapper's line), polled against a deadline; the line is read only to sequence a second
signal, since two signals sent back to back may arrive as one. The bounds only separate «waited for the shutdown» from
«killed at once» and «forced» from «waited for the whole grace»: the machine may be loaded. Whatever of a run is still
alive when its case ends is SIGKILLed through that run's own process group.

The other cases run in this process: (g, h) ``run_server_live`` on a child that stops at once or on a program that does
not exist, from the usual handlers and, in (g), from handlers of the test's own; (i) ``_server_stop_grace`` on each
value; (j) ``cmd_server`` with its builds, port check and launchers stood in for and every real process, exec and
signal forbidden.

PURE: no DB, no server, no network, no port, nothing written outside ``tmp_path``; the children start without the
runner's coverage wiring.
"""

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

import dev
import scripts.cli_base as cli_base
from backend.test_scripts.test_utils import print_info, print_section, print_success

PROJECT_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Timings: generous, since the machine may be loaded; each one only separates two outcomes
# ---------------------------------------------------------------------------

#: Seconds the fake server's shutdown takes when it is let finish: a server's drain and stop, shortened.
SHORT_WORK = 1.0
#: A shutdown longer than every bound: within EXIT_BOUND, only a SIGKILL ends it.
LONG_WORK = 60.0
#: The grace when the server is to be waited for (a, d, e): longer than EXIT_BOUND, so a wrapper that sits out the whole
#: grace instead of returning when its server stopped fails too.
WAIT_GRACE = 30.0
#: The grace that runs out first (b).
SHORT_GRACE = 1.0
#: The grace when only a second signal can end the wait (c, f): longer than LONG_WORK.
FORCE_GRACE = 120.0
#: Seconds within which the wrapper must exit after the signal that ends its wait: 20 times SHORT_WORK and SHORT_GRACE,
#: a third of LONG_WORK, two thirds of WAIT_GRACE.
EXIT_BOUND = 20.0
#: Seconds for two interpreters to start on a loaded machine, the wrapper importing scripts.cli_base.
READY_DEADLINE = 30.0
#: Seconds for a first signal's effects to show (the fake server's record, the wrapper's line).
HANDSHAKE_DEADLINE = 20.0
#: Seconds the cleanup waits for a SIGKILLed run to be reaped and for its output to end.
CLEANUP_DEADLINE = 10.0
#: Seconds between two looks at a condition; each pause is a wait on the wrapper, so its exit is seen at once.
POLL = 0.05
#: Tolerance of (b)'s lower bound: two processes reading the same machine's monotonic clock.
CLOCK_SLACK = 0.05

#: What the wrapper exits with: run_server_live's codes after Ctrl+C and after SIGTERM, and its own when it cannot
#: import run_server_live.
CTRL_C_CODE = 130
SIGTERM_CODE = 143
IMPORT_FAILED_CODE = 86
IMPORT_FAILED_MARK = "Z10-WRAPPER-IMPORT-FAILED"
#: The tokens of the line run_server_live prints at a first signal, before it waits. Read only to sequence a second one.
CTRL_C_LINE_TOKEN = "Interrupted"
SIGTERM_LINE_TOKEN = "SIGTERM"
#: Characters of the wrapper's output quoted by a failure message.
TAIL = 4000

needs_posix_signals = pytest.mark.skipif(not (hasattr(os, "killpg") and hasattr(signal, "pthread_sigmask")), reason="the signal cases need POSIX process groups and signal masks (os.killpg, signal.pthread_sigmask)")

# ---------------------------------------------------------------------------
# The two scripts of a signal case
# ---------------------------------------------------------------------------

#: The fake server. argv: the state folder, the seconds its shutdown takes.
FAKE_SERVER = r'''"""Z-10's fake server: a server's answer to SIGINT and SIGTERM, reduced to files in the state folder (argv[1]).

Every SIGINT or SIGTERM is appended to ``signals``, one name per line: the first starts the shutdown, which takes
argv[2] seconds, the later ones are only recorded. ``pid`` then ``ready`` are written once the handlers are installed,
``done`` once the shutdown is over; then the process exits 0. A SIGKILL leaves no ``done``. Prints nothing.
"""
import os
import signal
import sys
import time
from pathlib import Path

STATE = Path(sys.argv[1])
SHUTDOWN_SECONDS = float(sys.argv[2])
stopping = False


def publish(name, text):
    """Write a file whole: under a temporary name, then renamed, so that a reader never sees half of it."""
    temporary = STATE / ("." + name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, STATE / name)


def on_signal(signum, _frame):
    global stopping
    with open(STATE / "signals", "a", encoding="utf-8") as record:
        record.write(signal.Signals(signum).name + "\n")
    stopping = True


signal.signal(signal.SIGINT, on_signal)
signal.signal(signal.SIGTERM, on_signal)
signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})
publish("pid", str(os.getpid()))
publish("ready", "ready")
while not stopping:
    time.sleep(0.05)
# The shutdown itself, the time uvicorn spends draining its requests and the app stopping its jobs.
end = time.monotonic() + SHUTDOWN_SECONDS
while time.monotonic() < end:
    time.sleep(min(0.05, max(0.0, end - time.monotonic())))
publish("done", "done")
'''

#: The wrapper standing in for ``dev.py server``. argv: the project root, the fake server's script, the state folder,
#: the seconds of the fake server's shutdown, the grace (``none``: no limit).
WRAPPER = r'''"""Z-10's stand-in for ``dev.py server``: runs the fake server through ``scripts.cli_base.run_server_live``.

Exits with what ``run_server_live`` returned. Once the call has returned, writes ``signal-handlers`` in the state
folder: ``restored`` when the SIGINT and SIGTERM handlers are the ones in force before the call, otherwise the changes.
"""
import signal
import sys
from pathlib import Path

ROOT, FAKE_SERVER, STATE, SHUTDOWN_SECONDS, GRACE = sys.argv[1:6]
sys.path.insert(0, ROOT)

# The usual handlers, as dev.py has them when started from a terminal: default_int_handler for SIGINT, the default
# action for SIGTERM, neither signal blocked. run_server_live takes over only these, and the test process may run with
# SIGINT ignored or a signal blocked, which a child inherits: so they are set here explicitly.
signal.signal(signal.SIGINT, signal.default_int_handler)
signal.signal(signal.SIGTERM, signal.SIG_DFL)
signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGINT, signal.SIGTERM})

try:
    from scripts.cli_base import run_server_live
except ImportError as exc:
    print("@MARK@: " + repr(exc), file=sys.stderr, flush=True)
    raise SystemExit(@CODE@)

WATCHED = (signal.SIGINT, signal.SIGTERM)
before = {signum: signal.getsignal(signum) for signum in WATCHED}
code = run_server_live([sys.executable, FAKE_SERVER, STATE, SHUTDOWN_SECONDS], grace_seconds=None if GRACE == "none" else float(GRACE))
after = {signum: signal.getsignal(signum) for signum in WATCHED}
changes = [signum.name + ": " + repr(before[signum]) + " before, " + repr(after[signum]) + " after" for signum in WATCHED if after[signum] is not before[signum]]
Path(STATE, "signal-handlers").write_text("; ".join(changes) or "restored", encoding="utf-8")
raise SystemExit(code)
'''.replace("@MARK@", IMPORT_FAILED_MARK).replace("@CODE@", str(IMPORT_FAILED_CODE))


# ---------------------------------------------------------------------------
# Running a signal case
# ---------------------------------------------------------------------------


def describe_exit(code: int | None) -> str:
    """An exit code as the messages name it: a negative one is a death by signal."""
    if code is None:
        return "still running"
    if code < 0:
        try:
            return f"killed by {signal.Signals(-code).name} ({code})"
        except ValueError:
            return f"killed by signal {-code} ({code})"
    return f"exit code {code}"


def grace_label(grace: float | None) -> str:
    return "no limit" if grace is None else f"{grace:g} s"


def group_of(pid: int) -> int | None:
    """The process group of ``pid``; None once no such process exists."""
    try:
        return os.getpgid(pid)
    except ProcessLookupError:
        return None


class WrapperOutput:
    """The wrapper's stdout and stderr (one pipe, the fake server's too), read line by line on a thread as it comes."""

    def __init__(self, stream):
        self._lines: list[str] = []
        self._lock = threading.Lock()
        self._reader = threading.Thread(target=self._drain, args=(stream,), name="z10-wrapper-output", daemon=True)
        self._reader.start()

    def _drain(self, stream) -> None:
        for line in stream:
            with self._lock:
                self._lines.append(line)

    def text(self) -> str:
        with self._lock:
            return "".join(self._lines)

    def holds(self, token: str) -> bool:
        return token in self.text()

    def finish(self, timeout: float) -> bool:
        """Wait up to ``timeout`` for the output to end (every writer gone); True when it has."""
        self._reader.join(timeout)
        return not self._reader.is_alive()


class ServerRun:
    """The wrapper standing in for ``dev.py server`` and its fake server: a session of their own, files under ``tmp_path``."""

    def __init__(self, tmp_path: Path, *, shutdown_seconds: float, grace: float | None):
        folder = tmp_path / "z10"
        self.state = folder / "state"
        self.state.mkdir(parents=True)
        wrapper_script, fake_server = folder / "dev_py_stand_in.py", folder / "fake_server.py"
        wrapper_script.write_text(WRAPPER, encoding="utf-8")
        fake_server.write_text(FAKE_SERVER, encoding="utf-8")
        argv = [sys.executable, "-u", str(wrapper_script), str(PROJECT_ROOT), str(fake_server), str(self.state), str(shutdown_seconds), "none" if grace is None else str(grace)]
        # Without the runner's coverage wiring: a measured interpreter installs coverage's own SIGTERM handler
        # (sigterm = true in .coveragerc) and writes its data file outside tmp_path. run_server_live hands the fake
        # server this environment too.
        environment = {name: value for name, value in os.environ.items() if not name.startswith("COVERAGE_")}
        self.started = time.monotonic()
        self.wrapper = subprocess.Popen(argv, cwd=folder, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", start_new_session=True)
        self.output = WrapperOutput(self.wrapper.stdout)

    # -- What the fake server and the wrapper wrote --

    def _read(self, name: str) -> str | None:
        with contextlib.suppress(FileNotFoundError):
            return (self.state / name).read_text(encoding="utf-8")
        return None

    def signals(self) -> list[str]:
        """The signals the fake server recorded, in order; a line still being written is left out."""
        return [line[:-1] for line in (self._read("signals") or "").splitlines(keepends=True) if line.endswith("\n")]

    def child_pid(self) -> int | None:
        text = self._read("pid")
        return int(text) if text else None

    def done(self) -> bool:
        return (self.state / "done").exists()

    def child_alive(self) -> bool:
        """Whether the fake server still exists in the wrapper's group: a number reused by another process does not count."""
        pid = self.child_pid()
        return pid is not None and group_of(pid) == self.wrapper.pid

    def signal_handlers(self) -> str | None:
        """The wrapper's report on the SIGINT and SIGTERM handlers, once run_server_live has returned."""
        return self._read("signal-handlers")

    # -- Driving it --

    def _exited_within(self, seconds: float) -> bool:
        """Wait up to ``seconds`` for the wrapper to exit (it is reaped then); True when it has."""
        try:
            self.wrapper.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            return False
        return True

    def _fail_waiting(self, what: str, why: str) -> None:
        """Fail a wait for ``what``; when the wrapper could not even import run_server_live, say that first."""
        if self.wrapper.returncode == IMPORT_FAILED_CODE:
            pytest.fail(f"scripts.cli_base has no run_server_live (Z-10's server launcher): the wrapper standing in for dev.py could not import it, while the test waited for {what}{self.report()}")
        pytest.fail(f"waiting for {what}: {why}{self.report()}")

    def wait_for(self, what: str, condition: Callable[[], bool], timeout: float) -> None:
        """Poll ``condition`` until it holds; fail naming ``what`` when ``timeout`` runs out or the wrapper exits first."""
        deadline = time.monotonic() + timeout
        while not condition():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._fail_waiting(what, f"not within {timeout:g} s")
            if self._exited_within(min(POLL, remaining)) and not condition():
                self._fail_waiting(what, "the wrapper exited first")

    def wait_ready(self) -> None:
        """Wait for the fake server's ``ready``: the wrapper is inside run_server_live, the server's handlers are in place.

        Then the premises of every signal case: the wrapper leads a process group of its own, not this test's, and the
        fake server is in it, as uvicorn is in ``dev.py``'s foreground group when the terminal sends Ctrl+C.
        """
        self.wait_for("the fake server's «ready», written once its signal handlers are installed", lambda: (self.state / "ready").exists(), READY_DEADLINE)
        group = group_of(self.wrapper.pid)
        assert group == self.wrapper.pid and group != os.getpgrp(), f"premise: the wrapper (pid {self.wrapper.pid}) must lead a process group of its own, not this test's ({os.getpgrp()}); it is in group {group}{self.report()}"
        pid = self.child_pid()
        server_group = None if pid is None else group_of(pid)
        assert server_group == self.wrapper.pid, f"run_server_live must start the server in dev.py's own process group, the one the terminal's Ctrl+C reaches: the fake server (pid {pid}) is in group {server_group}, the wrapper's is {self.wrapper.pid}{self.report()}"

    def _require_running(self, before: str) -> None:
        if self.wrapper.poll() is not None:
            pytest.fail(f"the wrapper exited before {before}{self.report()}")

    def signal_group(self, signum: signal.Signals) -> float:
        """Send ``signum`` to the wrapper's process group, as the terminal's Ctrl+C and the test runner's stop do.

        Returns the monotonic time read right before sending: the signal cannot have arrived earlier.
        """
        self._require_running(f"{signum.name} was sent to its process group")
        sent = time.monotonic()
        os.killpg(self.wrapper.pid, signum)
        return sent

    def signal_wrapper(self, signum: signal.Signals) -> float:
        """Send ``signum`` to the wrapper alone, as a process supervisor does; returns the time read right before."""
        self._require_running(f"{signum.name} was sent to it")
        sent = time.monotonic()
        os.kill(self.wrapper.pid, signum)
        return sent

    def wait_exit(self, after: str, since: float) -> int:
        """The wrapper's exit code; fails when it is still running EXIT_BOUND seconds after ``since`` (``after``)."""
        try:
            return self.wrapper.wait(timeout=max(0.0, since + EXIT_BOUND - time.monotonic()))
        except subprocess.TimeoutExpired:
            pytest.fail(f"the wrapper standing in for dev.py was still running {EXIT_BOUND:g} s after {after}{self.report()}")

    # -- Reporting and cleaning up --

    def report(self) -> str:
        """The run as a failure message shows it: the wrapper's exit, the fake server's files and state, the output."""
        code = self.wrapper.poll()
        if code is not None:
            self.output.finish(2.0)  # a writer just gone: let the last lines arrive
        pid = self.child_pid()
        server = "never started" if pid is None else f"pid {pid}, {'alive' if self.child_alive() else 'gone'}"
        files = sorted(path.name for path in self.state.iterdir() if not path.name.startswith("."))
        output = self.output.text()
        return "\n".join(
            [
                "",
                f"  wrapper (dev.py's stand-in, pid {self.wrapper.pid}): {describe_exit(code)}, {time.monotonic() - self.started:.1f} s after its start",
                f"  fake server: {server}; files {files}; signals recorded {self.signals()}",
                f"  signal handlers once run_server_live returned: {self.signal_handlers() or 'not reported'}",
                f"  wrapper output, stdout and stderr ({len(output)} characters, the last {TAIL} shown):",
                output[-TAIL:],
            ]
        )

    def close(self) -> None:
        """SIGKILL whatever of the run is still alive, through its own process group only; reap the wrapper; end the reader."""
        if self.wrapper.poll() is None:  # not reaped: its number is still its group's
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.wrapper.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                self.wrapper.wait(timeout=CLEANUP_DEADLINE)
        if self.child_alive():  # the wrapper is gone and the fake server is not: the orphan of the defect
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.wrapper.pid, signal.SIGKILL)
        if self.output.finish(CLEANUP_DEADLINE) and self.wrapper.stdout is not None:
            self.wrapper.stdout.close()


@contextlib.contextmanager
def server_run(tmp_path: Path, *, shutdown_seconds: float, grace: float | None) -> Iterator[ServerRun]:
    """A ``ServerRun`` whose leftovers are SIGKILLed when the block ends, however it ends."""
    run = ServerRun(tmp_path, shutdown_seconds=shutdown_seconds, grace=grace)
    try:
        yield run
    finally:
        run.close()


def assert_exited_with(run: ServerRun, code: int, expected: int, after: str) -> None:
    assert code == expected, f"after {after}, the wrapper standing in for dev.py must end with exit code {expected}, not {describe_exit(code)}{run.report()}"


def assert_server_gone(run: ServerRun) -> None:
    assert not run.child_alive(), f"the fake server (pid {run.child_pid()}) was still running once the wrapper had exited: dev.py must not return before its server is gone{run.report()}"


def assert_signal_handlers_restored(run: ServerRun) -> None:
    reported = run.signal_handlers()
    assert reported == "restored", f"once run_server_live has returned, the SIGINT and SIGTERM handlers must be the ones in force before the call; the wrapper reported {reported or 'nothing'}{run.report()}"


# ---------------------------------------------------------------------------
# (a) to (f): real signals, a real wrapper, a real fake server
# ---------------------------------------------------------------------------


@needs_posix_signals
@pytest.mark.parametrize("grace", [WAIT_GRACE, None], ids=["grace-30s", "no-limit"])
def test_ctrl_c_lets_the_server_finish_its_shutdown(tmp_path, grace):
    """(a), (a') Ctrl+C: the server gets it once, from the terminal, and ``dev.py`` waits for its shutdown: exit 130.

    SIGINT goes to the process group, as the terminal sends it; the fake server's shutdown takes SHORT_WORK, then it
    exits 0 by itself. Asserts that the wrapper exits 130 (the first signal's code, not the server's) within EXIT_BOUND,
    shorter than the 30 s grace, so it returned when its server stopped; that the fake server finished its shutdown
    (``done``) and is gone; that it got exactly one SIGINT, the terminal's (run_server_live forwards none: uvicorn forces
    its exit at a second); that the SIGINT and SIGTERM handlers are back. With no limit (a') the same.

    Red until ``run_server_live`` exists. Through ``run_command_live``, ``subprocess.run`` SIGKILLs the server 0.25 s
    after Ctrl+C, long before its shutdown is over.
    """
    print_section(f"Z-10 (a): Ctrl+C to the group, the server's {SHORT_WORK:g} s shutdown waited for (grace {grace_label(grace)})")
    with server_run(tmp_path, shutdown_seconds=SHORT_WORK, grace=grace) as run:
        run.wait_ready()
        sent = run.signal_group(signal.SIGINT)
        code = run.wait_exit("Ctrl+C", sent)
        print_info(f"{describe_exit(code)}, {time.monotonic() - sent:.2f} s after Ctrl+C")

        assert_exited_with(run, code, CTRL_C_CODE, "Ctrl+C")
        assert run.done(), f"the fake server never finished its {SHORT_WORK:g} s shutdown: dev.py must wait for it after Ctrl+C, not kill it{run.report()}"
        assert_server_gone(run)
        assert run.signals() == ["SIGINT"], f"the server must get Ctrl+C exactly once, from the terminal: run_server_live must not forward it (uvicorn forces its exit at a second SIGINT) nor send anything else; recorded {run.signals()}{run.report()}"
        assert_signal_handlers_restored(run)
    print_success("130 once the server had finished its shutdown; one SIGINT, the terminal's")


@needs_posix_signals
def test_ctrl_c_kills_a_server_that_outlasts_the_grace(tmp_path):
    """(b) Ctrl+C, and the server's shutdown outlasts the grace: ``dev.py`` waits the grace, then SIGKILLs it: exit 130.

    The fake server's shutdown takes LONG_WORK (60 s), the grace is SHORT_GRACE (1 s). Asserts that the wrapper exits 130
    within EXIT_BOUND, and no sooner than the grace after Ctrl+C; that the fake server is gone without finishing its
    shutdown (no ``done``: it was killed, the only end it cannot record); that it got only the terminal's SIGINT; that
    the SIGINT and SIGTERM handlers are back.

    Red until ``run_server_live`` exists.
    """
    print_section(f"Z-10 (b): Ctrl+C, a {LONG_WORK:g} s shutdown, a {SHORT_GRACE:g} s grace: killed when the grace runs out")
    with server_run(tmp_path, shutdown_seconds=LONG_WORK, grace=SHORT_GRACE) as run:
        run.wait_ready()
        sent = run.signal_group(signal.SIGINT)
        code = run.wait_exit(f"Ctrl+C with a {SHORT_GRACE:g} s grace", sent)
        elapsed = time.monotonic() - sent
        print_info(f"{describe_exit(code)}, {elapsed:.2f} s after Ctrl+C")

        assert_exited_with(run, code, CTRL_C_CODE, "Ctrl+C")
        assert elapsed >= SHORT_GRACE - CLOCK_SLACK, f"the wrapper exited {elapsed:.2f} s after Ctrl+C, before the {SHORT_GRACE:g} s grace had run out: the grace is the time the server is given{run.report()}"
        assert not run.done(), f"the fake server finished a {LONG_WORK:g} s shutdown although the grace was {SHORT_GRACE:g} s{run.report()}"
        assert_server_gone(run)
        assert run.signals() == ["SIGINT"], f"the server must get only the terminal's Ctrl+C: when the grace runs out run_server_live SIGKILLs it, and forwards nothing; recorded {run.signals()}{run.report()}"
        assert_signal_handlers_restored(run)
    print_success(f"130 after {elapsed:.2f} s, the server killed once the grace had run out")


@needs_posix_signals
def test_a_second_ctrl_c_forces_the_stop(tmp_path):
    """(c) A second Ctrl+C during the wait SIGKILLs the server at once: exit 130, well before the grace.

    The fake server's shutdown takes LONG_WORK (60 s) and the grace is FORCE_GRACE (120 s), so neither ends the wait
    within EXIT_BOUND. The second SIGINT goes to the group once the wrapper has printed its ``Interrupted`` line and the
    fake server has recorded the first: two SIGINTs sent back to back may arrive as one. Asserts that the wrapper exits
    130 within EXIT_BOUND of the second; that the fake server is gone without ``done``; that it got nothing but the
    terminal's SIGINTs; that the SIGINT and SIGTERM handlers are back.

    Red until ``run_server_live`` exists.
    """
    print_section(f"Z-10 (c): a second Ctrl+C forces the stop ({LONG_WORK:g} s shutdown, {FORCE_GRACE:g} s grace)")
    with server_run(tmp_path, shutdown_seconds=LONG_WORK, grace=FORCE_GRACE) as run:
        run.wait_ready()
        run.signal_group(signal.SIGINT)
        run.wait_for(f"the wrapper's line holding {CTRL_C_LINE_TOKEN!r} and the fake server's record of the SIGINT, after the first Ctrl+C", lambda: run.output.holds(CTRL_C_LINE_TOKEN) and run.signals()[:1] == ["SIGINT"], HANDSHAKE_DEADLINE)
        sent = run.signal_group(signal.SIGINT)
        code = run.wait_exit("the second Ctrl+C", sent)
        print_info(f"{describe_exit(code)}, {time.monotonic() - sent:.2f} s after the second Ctrl+C")

        assert_exited_with(run, code, CTRL_C_CODE, "two Ctrl+C")
        assert not run.done(), f"the fake server finished its {LONG_WORK:g} s shutdown: the second Ctrl+C must kill it{run.report()}"
        assert_server_gone(run)
        assert set(run.signals()) == {"SIGINT"}, f"the server must get only the terminal's SIGINTs: a second Ctrl+C makes run_server_live SIGKILL it, and nothing else is sent; recorded {run.signals()}{run.report()}"
        assert_signal_handlers_restored(run)
    print_success("130 right after the second Ctrl+C, the server killed")


@needs_posix_signals
def test_sigterm_to_dev_py_alone_is_forwarded_and_the_server_waited_for(tmp_path):
    """(d) SIGTERM to ``dev.py`` alone, as a process supervisor sends it: forwarded to the server, waited for: exit 143.

    The fake server's shutdown takes SHORT_WORK, the grace is WAIT_GRACE. Asserts that the wrapper exits 143 (the first
    signal's code, not the server's) within EXIT_BOUND; that the fake server got exactly one SIGTERM, the forwarded one
    (nothing else reaches it), finished its shutdown and is gone; that the SIGINT and SIGTERM handlers are back.

    Red until ``run_server_live`` exists. Through ``run_command_live``, the SIGTERM kills ``dev.py`` (its default action)
    and the server keeps running without a parent.
    """
    print_section("Z-10 (d): SIGTERM to dev.py alone, forwarded to the server and waited for")
    with server_run(tmp_path, shutdown_seconds=SHORT_WORK, grace=WAIT_GRACE) as run:
        run.wait_ready()
        sent = run.signal_wrapper(signal.SIGTERM)
        code = run.wait_exit("a SIGTERM to the wrapper alone", sent)
        print_info(f"{describe_exit(code)}, {time.monotonic() - sent:.2f} s after the SIGTERM")

        assert_exited_with(run, code, SIGTERM_CODE, "a SIGTERM to dev.py alone")
        assert run.signals() == ["SIGTERM"], f"a SIGTERM to dev.py alone must reach the server, forwarded once: recorded {run.signals()}{run.report()}"
        assert run.done(), f"the fake server never finished its {SHORT_WORK:g} s shutdown: dev.py must wait for it after a SIGTERM{run.report()}"
        assert_server_gone(run)
        assert_signal_handlers_restored(run)
    print_success("143 once the server had finished; the SIGTERM forwarded once")


@needs_posix_signals
def test_sigterm_to_the_whole_group_lets_the_server_finish(tmp_path):
    """(e) SIGTERM to the whole group, as the test runner stops its server: the server finishes its shutdown: exit 143.

    The fake server gets the group's SIGTERM and the forwarded one, possibly as one (signals are not queued); the second
    is harmless, only recorded. Asserts that the wrapper exits 143 within EXIT_BOUND; that the fake server recorded one
    or two SIGTERMs and nothing else, finished its shutdown (so it was not SIGKILLed) and is gone; that the SIGINT and
    SIGTERM handlers are back.

    Red until ``run_server_live`` exists.
    """
    print_section("Z-10 (e): SIGTERM to the whole group, the server's shutdown waited for")
    with server_run(tmp_path, shutdown_seconds=SHORT_WORK, grace=WAIT_GRACE) as run:
        run.wait_ready()
        sent = run.signal_group(signal.SIGTERM)
        code = run.wait_exit("a SIGTERM to the group", sent)
        print_info(f"{describe_exit(code)}, {time.monotonic() - sent:.2f} s after the SIGTERM; the server recorded {run.signals()}")

        assert_exited_with(run, code, SIGTERM_CODE, "a SIGTERM to the group")
        assert run.done(), f"the fake server never finished its {SHORT_WORK:g} s shutdown: dev.py must wait for it after a SIGTERM{run.report()}"
        recorded = run.signals()
        assert 1 <= len(recorded) <= 2 and set(recorded) == {"SIGTERM"}, f"the server must get the group's SIGTERM and at most the forwarded one, nothing else: recorded {recorded}{run.report()}"
        assert_server_gone(run)
        assert_signal_handlers_restored(run)
    print_success("143 once the server had finished its shutdown")


@needs_posix_signals
def test_a_second_sigterm_forces_the_stop(tmp_path):
    """(f) A second SIGTERM to ``dev.py`` during the wait SIGKILLs the server at once: exit 143, well before the grace.

    As (c), with SIGTERMs to the wrapper alone: the second goes once the wrapper has printed its ``SIGTERM`` line and the
    fake server has recorded the forwarded one. Asserts that the wrapper exits 143 within EXIT_BOUND of the second; that
    the fake server is gone without ``done``; that it got nothing but SIGTERMs; that the SIGINT and SIGTERM handlers are
    back.

    Red until ``run_server_live`` exists.
    """
    print_section(f"Z-10 (f): a second SIGTERM forces the stop ({LONG_WORK:g} s shutdown, {FORCE_GRACE:g} s grace)")
    with server_run(tmp_path, shutdown_seconds=LONG_WORK, grace=FORCE_GRACE) as run:
        run.wait_ready()
        run.signal_wrapper(signal.SIGTERM)
        run.wait_for(f"the wrapper's line holding {SIGTERM_LINE_TOKEN!r} and the fake server's record of the forwarded SIGTERM, after the first SIGTERM", lambda: run.output.holds(SIGTERM_LINE_TOKEN) and run.signals()[:1] == ["SIGTERM"], HANDSHAKE_DEADLINE)
        sent = run.signal_wrapper(signal.SIGTERM)
        code = run.wait_exit("the second SIGTERM", sent)
        print_info(f"{describe_exit(code)}, {time.monotonic() - sent:.2f} s after the second SIGTERM")

        assert_exited_with(run, code, SIGTERM_CODE, "two SIGTERMs")
        assert not run.done(), f"the fake server finished its {LONG_WORK:g} s shutdown: the second SIGTERM must kill it{run.report()}"
        assert_server_gone(run)
        assert set(run.signals()) == {"SIGTERM"}, f"the server must get only SIGTERMs: a second one makes run_server_live SIGKILL it; recorded {run.signals()}{run.report()}"
        assert_signal_handlers_restored(run)
    print_success("143 right after the second SIGTERM, the server killed")


# ---------------------------------------------------------------------------
# (g), (h): run_server_live in this process, no signal sent
# ---------------------------------------------------------------------------

#: Runs as the child of (g'): reports its working directory and three variables into the file named by argv[1].
ENVIRONMENT_PROBE = "import json, os, sys; json.dump({'cwd': os.getcwd(), 'inherited': os.environ.get('Z10_INHERITED'), 'overridden': os.environ.get('Z10_OVERRIDDEN'), 'passed': os.environ.get('Z10_PASSED')}, open(sys.argv[1], 'w', encoding='utf-8'))"


def run_server_live_under_test() -> Callable[..., int]:
    """``scripts.cli_base.run_server_live``; fails the test, naming it, while it does not exist."""
    launcher = getattr(cli_base, "run_server_live", None)
    if launcher is None:
        pytest.fail("scripts.cli_base has no run_server_live (Z-10's server launcher)")
    return launcher


def _own_sigint_handler(signum, _frame):
    """A SIGINT handler of the test's own: a Ctrl+C meant for pytest still stops it."""
    raise KeyboardInterrupt(f"{signal.Signals(signum).name} while the test's own SIGINT handler was in force")


def _own_sigterm_handler(signum, _frame):
    """A SIGTERM handler of the test's own: a SIGTERM meant for pytest still stops it."""
    raise KeyboardInterrupt(f"{signal.Signals(signum).name} while the test's own SIGTERM handler was in force")


#: The handlers in force before an in-process call. ``usual``: the ones dev.py has from a terminal, which
#: run_server_live takes over during the call and must put back. ``own``: handlers of the test's own, which it leaves in
#: force, and must not reset to the usual ones either when it returns.
HANDLER_SETS = {
    "usual": {signal.SIGINT: signal.default_int_handler, signal.SIGTERM: signal.SIG_DFL},
    "own": {signal.SIGINT: _own_sigint_handler, signal.SIGTERM: _own_sigterm_handler},
}


@pytest.fixture
def handlers_before(request) -> Iterator[dict[signal.Signals, object]]:
    """Install the SIGINT and SIGTERM handlers in force before the call (``usual`` unless the case asks for ``own``).

    Yields them; puts back the process's own handlers afterwards, whatever the call left.
    """
    assert threading.current_thread() is threading.main_thread(), "premise: the test runs in the main thread, the only one where run_server_live takes over the signal handlers"
    installed = HANDLER_SETS[getattr(request, "param", "usual")]
    previous = {signum: signal.signal(signum, handler) for signum, handler in installed.items()}
    try:
        yield installed
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, signal.SIG_DFL if handler is None else handler)


def assert_handlers_back(before: dict[signal.Signals, object]) -> None:
    """The SIGINT and SIGTERM handlers in force are the very objects in force before the call."""
    after = {signum: signal.getsignal(signum) for signum in before}
    changed = {signum.name: f"{before[signum]!r} before, {after[signum]!r} after" for signum in before if after[signum] is not before[signum]}
    assert not changed, f"once run_server_live has returned, the SIGINT and SIGTERM handlers must be the ones in force before the call: {changed}"


@pytest.fixture
def unmeasured_children(monkeypatch):
    """The children of the test start without the runner's coverage wiring (``COVERAGE_PROCESS_START`` and the rest)."""
    for name in [name for name in os.environ if name.startswith("COVERAGE_")]:
        monkeypatch.delenv(name)


@pytest.mark.parametrize("handlers_before", list(HANDLER_SETS), indirect=True)
def test_a_server_that_stops_by_itself_gives_its_exit_code_and_the_handlers_back(handlers_before, unmeasured_children):
    """(g) A server that exits by itself, with code 3: ``run_server_live`` returns 3, and the handlers are back.

    After the call, ``signal.getsignal`` gives the very SIGINT and SIGTERM handlers in force before it: from the usual
    ones (``default_int_handler``, ``SIG_DFL``), which run_server_live takes over during the call, and from handlers of
    the test's own, which it leaves alone, so that resetting them to the usual ones when it returns fails too.

    Red until ``run_server_live`` exists.
    """
    print_section("Z-10 (g): the server's own exit code; the signal handlers given back")
    run_server_live = run_server_live_under_test()

    code = run_server_live([sys.executable, "-c", "raise SystemExit(3)"])

    assert code == 3, f"run_server_live must return the exit code of a server that stopped by itself (3), not {code!r}"
    assert_handlers_back(handlers_before)
    print_success("3, and the SIGINT and SIGTERM handlers of before the call")


def test_the_server_starts_in_the_project_root_with_this_environment_plus_env(monkeypatch, tmp_path, handlers_before, unmeasured_children):
    """(g') The server starts in the project root, with ``os.environ`` plus ``env``, a name of ``env`` winning.

    The test moves to ``tmp_path`` first, so that a server merely inheriting the working directory fails. The child
    reports its working directory and three variables: one only in ``os.environ``, one in both (``env`` must win), one
    only in ``env``. The usual handlers are back afterwards.

    Red until ``run_server_live`` exists.
    """
    print_section("Z-10 (g'): the server's working directory and environment")
    run_server_live = run_server_live_under_test()
    monkeypatch.setenv("Z10_INHERITED", "os.environ")
    monkeypatch.setenv("Z10_OVERRIDDEN", "os.environ")
    monkeypatch.delenv("Z10_PASSED", raising=False)
    monkeypatch.chdir(tmp_path)
    seen_file = tmp_path / "seen.json"

    code = run_server_live([sys.executable, "-c", ENVIRONMENT_PROBE, str(seen_file)], env={"Z10_OVERRIDDEN": "env", "Z10_PASSED": "env"})

    assert code == 0 and seen_file.exists(), f"the probe must run and report what it saw (exit code {code!r}, report {'written' if seen_file.exists() else 'missing'})"
    seen = json.loads(seen_file.read_text(encoding="utf-8"))
    assert Path(seen["cwd"]).resolve() == PROJECT_ROOT, f"run_server_live must start the server in the project root {PROJECT_ROOT}, not in {seen['cwd']}"
    variables = {name: seen[name] for name in ("inherited", "overridden", "passed")}
    assert variables == {"inherited": "os.environ", "overridden": "env", "passed": "env"}, f"run_server_live must hand the server os.environ updated with env: it saw {variables}"
    assert_handlers_back(handlers_before)
    print_success("the project root, os.environ updated with env")


def test_a_server_that_cannot_start_returns_1(tmp_path, capsys, handlers_before, unmeasured_children):
    """(h) A command that cannot start (a program that does not exist): ``run_server_live`` prints an error, returns 1.

    The usual handlers, taken over before the start, are back on this path too. Only that something was printed is
    checked, not what.

    Red until ``run_server_live`` exists.
    """
    print_section("Z-10 (h): a server that cannot start")
    run_server_live = run_server_live_under_test()
    missing = tmp_path / "no-such-server"
    capsys.readouterr()

    code = run_server_live([str(missing)])

    printed = capsys.readouterr()
    assert code == 1, f"run_server_live must return 1 when {missing} cannot start, not {code!r}"
    assert (printed.out + printed.err).strip(), f"run_server_live must print an error when {missing} cannot start; it printed nothing"
    assert_handlers_back(handlers_before)
    print_success("1, an error printed")


# ---------------------------------------------------------------------------
# (i) The grace: the shutdown budget plus 2 s
# ---------------------------------------------------------------------------

#: The variable of the shutdown budget (backend/app/config/sleep_wake.py, shutdown_timeout_seconds).
BUDGET_VARIABLE = "LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS"
#: The budget this process's own environment carries during (i): 302.0 would show the grace read from os.environ.
UNRELATED_BUDGET = "300"

#: Value of the variable in the env passed (None: absent) → the grace.
STOP_GRACES = {
    "unset": (None, 10.0),
    "empty": ("", 10.0),
    "blank": ("   ", 10.0),
    "5": ("5", 7.0),
    "5-padded": (" 5 ", 7.0),
    "2-minimum": ("2", 4.0),
    "600-maximum": ("600", 602.0),
    "0-no-limit": ("0", None),
    "abc": ("abc", 10.0),
    "601-over-the-maximum": ("601", 10.0),
    "1-under-the-minimum": ("1", 10.0),
}


def stop_grace_under_test() -> Callable[..., float | None]:
    """``dev._server_stop_grace``; fails the test, naming it, while it does not exist."""
    stop_grace = getattr(dev, "_server_stop_grace", None)
    if stop_grace is None:
        pytest.fail("dev.py has no _server_stop_grace (Z-10: the shutdown budget plus 2 s, the grace cmd_server gives run_server_live)")
    return stop_grace


@pytest.mark.parametrize(("value", "expected"), list(STOP_GRACES.values()), ids=list(STOP_GRACES))
def test_server_stop_grace_is_the_shutdown_budget_plus_two_seconds(monkeypatch, value, expected):
    """(i) ``_server_stop_grace(env)``: ``shutdown_timeout_seconds(env)`` plus 2 s; None for no limit (0); 10.0 when unusable.

    Read from the env it is given, the one cmd_server hands the server: this process's own environment carries another
    budget meanwhile (300, so 302.0 would show it).

    Red until ``_server_stop_grace`` exists.
    """
    monkeypatch.setenv(BUDGET_VARIABLE, UNRELATED_BUDGET)
    env = {} if value is None else {BUDGET_VARIABLE: value}

    grace = stop_grace_under_test()(env)

    if expected is None:
        assert grace is None, f"{BUDGET_VARIABLE}={value!r} means no limit: the grace must be None, not {grace!r}"
    else:
        assert grace == expected, f"{BUDGET_VARIABLE}={value!r} in the env given: the grace must be {expected:g} s, not {grace!r}"


# ---------------------------------------------------------------------------
# (j) cmd_server launches through run_server_live, with its grace
# ---------------------------------------------------------------------------

#: The port of the cmd_server cases. Never bound (the port check and the launchers are stood in for), neither 6040 nor
#: 6041, so a command carrying it comes from this run.
PORT = 6998
#: The database path the stood-in configuration gives. Only printed.
FAKE_DATABASE = "fake-lane/sqlite/app.db"


class _LaunchResult:
    """What the stood-in ``run_server_live`` returns: a cmd_server returning it handed the launch's result back."""

    def __repr__(self) -> str:
        return "<the stood-in launch's result>"


LAUNCH_RESULT = _LaunchResult()


@dataclass
class ServerLaunch:
    """One ``run_server_live`` call of cmd_server. Its ``env`` is never printed whole."""

    cmd: list[str]
    env: dict[str, str]
    grace_seconds: float | None


def forbid(monkeypatch, target, name: str, reason: str, *, raising: bool = True) -> None:
    """Make ``target.name`` fail the test with ``reason`` if the code under test reaches it.

    ``raising=False`` also forbids a name the code does not define yet: a guard that holds before and after it exists.
    """

    def refuse(*_args, **_kwargs):
        pytest.fail(reason)

    monkeypatch.setattr(target, name, refuse, raising=raising)


def stand_in_for_the_server_start(monkeypatch, tmp_path: Path) -> None:
    """What ``cmd_server`` does before its launch, stood in for: nothing built, no port read, ``os.environ`` left alone.

    The runtime configuration (which writes ``os.environ``), the database path, the data directory and the host are
    fixed; the builds do nothing (``--rebuild``'s ``cmd_fe_build`` fails the test); nothing holds the port; the build
    carries no Designer Lab; ``dev.PROJECT_ROOT`` is ``tmp_path``.
    """

    def configure_runtime(port=None, data_dir=None, lane_settings=None):
        return port, tmp_path / "data"

    monkeypatch.setattr(dev, "PROJECT_ROOT", tmp_path)
    for name in ("configure_server_runtime", "configure_test_runtime"):
        monkeypatch.setattr(dev, name, configure_runtime)
    monkeypatch.setattr(dev, "get_database_path", lambda test_mode=False: FAKE_DATABASE)
    monkeypatch.setattr(dev, "get_data_dir", lambda test_mode=False: tmp_path / "data")
    monkeypatch.setattr(dev, "get_server_host", lambda: "127.0.0.1")
    monkeypatch.setattr(dev, "auto_build_frontend", lambda debug=False: None)
    forbid(monkeypatch, dev, "cmd_fe_build", "cmd_server rebuilt the frontend: no case here asks for --rebuild")
    monkeypatch.setattr(dev, "auto_build_mkdocs", lambda: None)
    monkeypatch.setattr(dev, "update_js_cache", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(dev, "check_port_in_use", lambda _port: [])
    monkeypatch.setattr(dev, "_frontend_build_has_designer_lab", lambda *_args, **_kwargs: False)


def run_cmd_server(monkeypatch, tmp_path: Path, *, launches: list[ServerLaunch] | None = None, execs: list[list[str]] | None = None, **options) -> object:
    """``dev.cmd_server(Namespace(port=PORT, **options))`` on a fake project; returns its result.

    Every real process, exec and signal fails the test, and so does ``run_command_live``. With ``launches``, each
    ``run_server_live`` call is recorded there and returns ``LAUNCH_RESULT``; without, reaching it fails the test. With
    ``execs``, each ``os.execvpe`` argv is recorded there (and returns, which the real one never does); without,
    reaching it fails the test. Fails the test when the call changed ``os.environ``.
    """
    for name in ("run", "Popen"):
        forbid(monkeypatch, subprocess, name, f"a real subprocess.{name} was reached: nothing may start here")
    for name in ("kill", "killpg"):
        forbid(monkeypatch, os, name, f"a real os.{name} was reached: nothing may be signalled here")
    if execs is None:
        forbid(monkeypatch, os, "execvpe", "cmd_server exec'd: only --coverage replaces dev.py with coverage run")
    else:
        monkeypatch.setattr(os, "execvpe", lambda _file, args, _env: execs.append(list(args)))
    forbid(monkeypatch, dev, "run_command_live", "cmd_server launched the server through run_command_live: its subprocess.run SIGKILLs the server 0.25 s after Ctrl+C and lets a SIGTERM to dev.py orphan it; the launch must go through run_server_live (Z-10)")
    if launches is None:
        forbid(monkeypatch, dev, "run_server_live", "cmd_server reached run_server_live under --coverage, which must replace dev.py with coverage run (os.execvpe)", raising=False)
    else:

        def run_server_live(cmd, env=None, grace_seconds=None):
            launches.append(ServerLaunch(cmd=list(cmd), env=dict(env or {}), grace_seconds=grace_seconds))
            return LAUNCH_RESULT

        # dev.py imports the name from scripts.cli_base: dev.run_server_live is the one cmd_server calls.
        monkeypatch.setattr(dev, "run_server_live", run_server_live, raising=False)
    stand_in_for_the_server_start(monkeypatch, tmp_path)

    environ_before = dict(os.environ)
    returned = dev.cmd_server(argparse.Namespace(port=PORT, **options))
    changed = sorted(name for name in environ_before.keys() | os.environ.keys() if environ_before.get(name) != os.environ.get(name))
    assert not changed, f"cmd_server changed os.environ, which none of its stand-ins writes (names only): {changed}"
    return returned


@pytest.mark.parametrize(("budget", "expected"), [("5", 7.0), ("0", None)], ids=["budget-5s", "no-limit"])
@pytest.mark.parametrize("test_mode", [False, True], ids=["server", "test-server"])
def test_cmd_server_launches_through_run_server_live_with_the_grace_of_its_budget(monkeypatch, tmp_path, test_mode, budget, expected):
    """(j) ``cmd_server`` hands uvicorn to ``run_server_live`` with ``grace_seconds=_server_stop_grace(env)``.

    ``LIBREFOLIO_SHUTDOWN_TIMEOUT_SECONDS`` is 5 (grace 7.0) or 0 (no limit, None), for ``server`` and ``server --test``.
    Asserts one launch, of ``backend.app.main:app`` on PORT; that the env it passes carries the budget; that its grace is
    the expected one and ``_server_stop_grace`` of that very env; that cmd_server returns the launch's result. Reaching
    ``run_command_live`` fails the test, as does any real process, exec or signal.

    Red today: cmd_server launches through ``run_command_live``.
    """
    print_section(f"Z-10 (j): cmd_server ({'--test' if test_mode else 'production'}), budget {budget}: run_server_live with grace {grace_label(expected)}")
    monkeypatch.setenv(BUDGET_VARIABLE, budget)
    launches: list[ServerLaunch] = []

    returned = run_cmd_server(monkeypatch, tmp_path, launches=launches, test=test_mode)

    assert len(launches) == 1, f"cmd_server must launch the server once through run_server_live: {[launch.cmd for launch in launches]}"
    (launch,) = launches
    assert "backend.app.main:app" in launch.cmd and launch.cmd[launch.cmd.index("--port") + 1] == str(PORT), f"the launch must be uvicorn on {PORT}: {launch.cmd}"
    assert launch.env.get(BUDGET_VARIABLE) == budget, f"premise: the env cmd_server hands the server carries {BUDGET_VARIABLE}={budget!r}; it has {launch.env.get(BUDGET_VARIABLE)!r}"
    if expected is None:
        assert launch.grace_seconds is None, f"{BUDGET_VARIABLE}=0 means no limit: run_server_live must get grace_seconds=None, not {launch.grace_seconds!r}"
    else:
        assert launch.grace_seconds == expected, f"{BUDGET_VARIABLE}={budget}: run_server_live must get grace_seconds={expected:g} (the budget plus 2 s), not {launch.grace_seconds!r}"
    from_env = stop_grace_under_test()(launch.env)
    assert launch.grace_seconds == from_env, f"the grace must be _server_stop_grace of the env cmd_server passes ({from_env!r}), not {launch.grace_seconds!r}"
    assert returned is LAUNCH_RESULT, f"cmd_server must return the launch's result, not {returned!r}"
    print_success(f"run_server_live(uvicorn, env, grace_seconds={launch.grace_seconds!r})")


def test_cmd_server_under_coverage_still_execs_coverage_run(monkeypatch, tmp_path):
    """(j') ``server --test --coverage`` still replaces ``dev.py`` with ``coverage run -m uvicorn``, with no launcher between.

    ``coverage run`` writes its data on SIGTERM only when the signal reaches it directly (the exec chain described in
    cmd_server). Asserts one ``os.execvpe`` of ``coverage run … -m uvicorn``; ``run_server_live`` and
    ``run_command_live`` are never reached.

    Green today: a guard, that Z-10 leaves this path as it is.
    """
    print_section("Z-10 (j'): --coverage still execs coverage run")
    execs: list[list[str]] = []

    run_cmd_server(monkeypatch, tmp_path, execs=execs, test=True, coverage=True)

    assert len(execs) == 1, f"cmd_server --coverage must exec once: {execs}"
    (argv,) = execs
    assert argv[argv.index("coverage") + 1] == "run" and argv[argv.index("-m") + 1] == "uvicorn", f"cmd_server --coverage must exec coverage run -m uvicorn: {argv}"
    print_success("os.execvpe(coverage run -m uvicorn)")
