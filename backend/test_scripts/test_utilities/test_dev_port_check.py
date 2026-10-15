"""``dev.py``'s ``check_port_in_use(port)`` must see who holds a TCP port on Linux as on macOS (N, R2), and count only who listens on it (H-12).

``dev.py server`` (``cmd_server``) calls it right before binding, and ``dev.py mkdocs gallery`` before starting its test
server: a non-empty answer is printed under «Port … is already in use!» and the start is refused, and it is the list
``--force`` kills.

N, R2 (fixed): the Linux branch ran ``subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True,
stderr=subprocess.DEVNULL)``. Python refuses ``capture_output`` together with ``stdout`` or ``stderr`` before starting
anything (``ValueError: stdout and stderr arguments may not be used with capture_output.``), and the function's
``except Exception: pass`` swallowed the error. On Linux it therefore returned ``[]`` for every port: a held port was
reported free, and ``--force`` killed nothing.

H-12: a port is in use when something listens on it. On macOS the function runs ``lsof -i :PORT -t``, which lists every
socket whose local or remote port is PORT, in any state: a client connected to the port, or the accepted connection of
a server that has closed its listener but not yet exited, is enough for ``cmd_server`` to refuse to start, and lands in
what ``--force`` kills. The test runner checks the lane with its own ``port_holders`` (``scripts/test_runner/_server.py``,
``lsof -nP -iTCP:PORT -sTCP:LISTEN -t``), which counts listeners only, then starts the shared test server through
``dev.py server --test`` with its output discarded: right after another server on the lane has stopped, the runner can
find the port free and ``cmd_server`` refuse it, with a message nobody sees. Wherever ``lsof`` exists, on any OS,
``check_port_in_use`` must count listeners only. On Linux without ``lsof`` it falls back to ``fuser PORT/tcp``, which
names every socket whose local port is PORT, in any state, the connection a server has accepted as well as its
listener: documented here, not asserted.

Platforms: development runs on macOS and CI on Linux, so every red has to show on macOS too.

* (a) runs on every OS, on a simulated Linux host with ``fuser`` and without ``lsof``: ``platform.system()`` says
  ``"Linux"``, ``shutil.which`` finds ``fuser`` and not ``lsof``, and an ``lsof`` call fails as it would there. The
  ``fuser`` call is handed to the real ``subprocess.run`` with every keyword as written; only argv is swapped, for a
  Python child that prints this process's pid. What used to reject the call is Python's own argument check, the same
  on every OS: (a) needs neither Linux nor a ``fuser`` binary, does not depend on whether the host has ``lsof``, and
  reads no port table.
* (b) and (c) run the host's real branch against a socket of their own on ``127.0.0.1``, with the tool
  ``check_port_in_use`` picks there. They run on macOS with ``lsof`` and on Linux with ``fuser``, and skip on any
  other host.
* (d) parses ``dev.py``: no call may pass ``capture_output`` together with ``stdout=`` or ``stderr=``.
* (e) runs wherever ``lsof`` is on PATH, on any OS, and skips elsewhere with the reason: on Linux without ``lsof`` the
  ``fuser`` fallback still names the accepted connection, by design.

PURE: no DB, no server, nothing written. The sockets bind ``127.0.0.1`` on ports the OS picks, and (e)'s client
connects only to (e)'s own listener; the only child processes are ``lsof``/``fuser`` and ``ps`` (read-only) and, in
(a), a Python child that prints a number.
"""

import ast
import errno
import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

import dev

PROJECT_ROOT = Path(__file__).resolve().parents[3]
#: The module the cases exercise; (d) parses this very file.
DEV_PY = Path(dev.__file__).resolve()

#: The real ``subprocess.run`` and ``shutil.which``, taken at import, before any test patches them.
REAL_RUN = subprocess.run
REAL_WHICH = shutil.which

#: (a)'s port. Never probed: the stand-in replaces ``fuser`` and ``lsof``, so no port table is read.
UNPROBED_PORT = 54_321

#: Where (a)'s simulated Linux host keeps ``fuser``. Never executed: the stand-in swaps argv for any program named ``fuser``.
SIMULATED_FUSER = "/usr/bin/fuser"

#: (b) and (c) run where ``check_port_in_use`` is sure to find a real tool: ``lsof`` on macOS, ``fuser`` on Linux.
HOST_PORT_TOOL = {"Darwin": "lsof", "Linux": "fuser"}.get(platform.system())
needs_host_port_tool = pytest.mark.skipif(
    not ((platform.system() == "Darwin" and shutil.which("lsof")) or (platform.system() == "Linux" and shutil.which("fuser"))),
    reason=f"check_port_in_use reads ports with lsof on macOS and fuser on Linux: this host is {platform.system()}" + (f", without {HOST_PORT_TOOL} on PATH" if HOST_PORT_TOOL else ""),
)


# ---------------------------------------------------------------------------
# (a) The Linux fuser fallback, through Python's own argument check
# ---------------------------------------------------------------------------


@dataclass
class FuserCall:
    """One ``fuser`` call as ``check_port_in_use`` made it, and what the real ``subprocess.run`` raised on it, if anything."""

    argv: list[str]
    kwargs: dict[str, object]
    error: Exception | None = None


def which_on_simulated_linux(cmd, mode=os.F_OK | os.X_OK, path=None):
    """``shutil.which`` for (a)'s simulated Linux host: ``fuser`` is there, ``lsof`` is not; any other name gets the real answer."""
    name = Path(str(cmd)).name
    if name == "lsof":
        return None
    if name == "fuser":
        return SIMULATED_FUSER
    return REAL_WHICH(cmd, mode=mode, path=path)


def run_with_fuser_stand_in(fuser_calls: list[FuserCall], lsof_calls: list[list[str]]):
    """A ``subprocess.run`` for (a)'s simulated Linux host, recording every ``fuser`` call into ``fuser_calls`` and every ``lsof`` call into ``lsof_calls``.

    A ``fuser`` call goes to the real ``subprocess.run`` with every keyword as written, so Python's own argument check
    applies; only argv is swapped, for a Python child that prints this process's pid on stdout, where ``fuser`` prints
    its PIDs. An ``lsof`` call starts nothing and raises the ``FileNotFoundError`` the real call raises on a host
    without ``lsof``. Every other call (``ps -p …``) passes through untouched.
    """
    stand_in = [sys.executable, "-c", f"print({os.getpid()})"]

    def run(*popenargs, **kwargs):
        argv = popenargs[0] if popenargs else kwargs.get("args")
        program = Path(str(argv[0])).name if isinstance(argv, (list, tuple)) and argv else None
        if program == "lsof":
            lsof_calls.append([str(part) for part in argv])
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(argv[0]))
        if program != "fuser":
            return REAL_RUN(*popenargs, **kwargs)
        call = FuserCall(argv=[str(part) for part in argv], kwargs=dict(kwargs))
        fuser_calls.append(call)
        if popenargs:
            popenargs = (stand_in, *popenargs[1:])
        else:
            kwargs["args"] = stand_in
        try:
            return REAL_RUN(*popenargs, **kwargs)
        except Exception as exc:
            call.error = exc  # kept for the assertion message, then raised unchanged, as the real call would
            raise

    return run


def test_linux_branch_returns_the_pid_fuser_prints(monkeypatch):
    """(a) The Linux ``fuser`` fallback, through the real ``subprocess.run`` argument check, on every OS.

    The host is a simulated Linux without ``lsof``: ``platform.system()`` says ``"Linux"``, ``shutil.which`` finds
    ``fuser`` and not ``lsof``, and an ``lsof`` call raises ``FileNotFoundError`` as it would there, so the function
    reaches its ``fuser`` branch whether or not this host has ``lsof``, and however it looks for it (``shutil.which`` or
    trying the call). The ``fuser`` call reaches the real ``subprocess.run`` with its keywords as written, argv swapped
    for a Python child that prints this process's pid. ``ps -p <pid> -o comm=`` runs for real (it exists on macOS and
    Linux alike). Asserts that ``fuser`` was asked about ``<port>/tcp``, and that the function returns exactly one pair:
    this pid, with a non-empty process name. The count is the stand-in's, which prints one pid, so the test owns it.

    Guards N, R2: with ``capture_output=True`` and ``stderr=subprocess.DEVNULL`` the real ``subprocess.run`` raised
    ``ValueError`` before starting the child, ``except Exception: pass`` swallowed it, and the function returned ``[]``.
    """
    fuser_calls: list[FuserCall] = []
    lsof_calls: list[list[str]] = []
    monkeypatch.setattr(dev.platform, "system", lambda: "Linux")
    monkeypatch.setattr(dev.shutil, "which", which_on_simulated_linux)
    monkeypatch.setattr(dev.subprocess, "run", run_with_fuser_stand_in(fuser_calls, lsof_calls))

    holders = dev.check_port_in_use(UNPROBED_PORT)

    asked = [call.argv for call in fuser_calls]
    assert any(f"{UNPROBED_PORT}/tcp" in argv for argv in asked), f"on a simulated Linux host without lsof, check_port_in_use({UNPROBED_PORT}) never asked fuser about {UNPROBED_PORT}/tcp; fuser calls: {asked!r}, lsof calls (each failed as on a host without it): {lsof_calls!r}"

    rejected = next((call for call in fuser_calls if call.error is not None), None)
    cause = "" if rejected is None else f"; the real subprocess.run raised {rejected.error!r} on fuser's keywords {rejected.kwargs!r}, and the function's except Exception turned that into «nobody holds the port»"
    assert [pid for pid, _name in holders] == [os.getpid()], f"on the Linux branch, check_port_in_use({UNPROBED_PORT}) returned {holders!r}, not exactly one pair for this process (pid {os.getpid()}){cause}"
    assert all(isinstance(name, str) and name.strip() for _pid, name in holders), f"this process's pair carries no process name: {holders!r}"


# ---------------------------------------------------------------------------
# (b), (c) The host's real branch, on a socket of the test's own
# ---------------------------------------------------------------------------


@needs_host_port_tool
def test_host_reports_this_process_while_it_listens():
    """(b) Real detection on the host: a listener of this process on ``127.0.0.1`` is reported with this pid.

    Binds a listening TCP socket on ``127.0.0.1``, on a port the OS picks, asks ``check_port_in_use`` about that port
    with the host's real tool, and closes the socket in a ``finally``. Asserts that this pid is among the holders. Only
    this one is asserted: other processes may hold the same number (``lsof -i`` also matches UDP sockets, other local
    addresses and remote ports), and the test owns none of them.

    Guards N, R2 on Linux, hence on CI: the ``fuser`` call used to raise the ``ValueError`` the function swallowed, and
    it returned ``[]``.
    """
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        holders = dev.check_port_in_use(port)
    finally:
        listener.close()

    assert os.getpid() in [pid for pid, _name in holders], f"check_port_in_use({port}) on {platform.system()} returned {holders!r} while this process (pid {os.getpid()}) was listening on 127.0.0.1:{port}"


@needs_host_port_tool
def test_host_no_longer_reports_this_process_once_the_port_is_released():
    """(c) A free port: once this process has closed its socket, the host's real tool no longer names it.

    Binds a TCP socket on ``127.0.0.1``, on a port the OS picks, closes it, then asks ``check_port_in_use`` about the
    port with the host's real tool. Asserts that this pid is not among the holders. With (b), same function and same
    host, it shows that the result follows the socket: a reading, not a constant.

    Not ``== []``: the port table is the machine's, not the test's. ``lsof -i :port`` also matches UDP sockets, other
    local addresses and remote ports, and under ``--workers`` another process may bind the number this one released;
    an exact empty list would fail on any of them. What the test owns is its own socket, so that is what it asserts.

    Green on macOS and on Linux.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    finally:
        probe.close()

    holders = dev.check_port_in_use(port)

    assert os.getpid() not in [pid for pid, _name in holders], f"check_port_in_use({port}) on {platform.system()} still names this process (pid {os.getpid()}) after it closed its socket on 127.0.0.1:{port}: {holders!r}"


# ---------------------------------------------------------------------------
# (d) Static guard
# ---------------------------------------------------------------------------


def capture_output_clashes(source: Path) -> list[str]:
    """Every call in ``source`` passing ``capture_output`` (anything but a literal ``False``) with ``stdout=`` or ``stderr=``.

    One ``file:line: call(...)`` per call, in source order.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    shown = source.relative_to(PROJECT_ROOT) if source.is_relative_to(PROJECT_ROOT) else source
    clashes: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        named = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg is not None}
        capture = named.get("capture_output")
        streams = [name for name in ("stdout", "stderr") if name in named]
        if capture is None or not streams or (isinstance(capture, ast.Constant) and capture.value is False):
            continue
        passed = ", ".join(f"{name}={ast.unparse(named[name])}" for name in ("capture_output", *streams))
        clashes.append((node.lineno, f"{shown}:{node.lineno}: {ast.unparse(node.func)}(..., {passed})"))
    return [text for _line, text in sorted(clashes)]


def test_dev_py_never_combines_capture_output_with_stdout_or_stderr():
    """(d) Static guard: the misuse cannot come back anywhere in ``dev.py``.

    Parses ``dev.py`` and asserts that no call passes ``capture_output`` (other than a literal ``False``) together with
    ``stdout=`` or ``stderr=``: ``subprocess.run`` rejects that with ``ValueError`` before starting anything, and a
    broad ``except`` turns it into a silent wrong answer, as it did in ``check_port_in_use``. The message names file
    and line.

    Guards N, R2: it was red on ``dev.py:100``, the ``fuser`` call of ``check_port_in_use``.
    """
    clashes = capture_output_clashes(DEV_PY)

    assert not clashes, "subprocess.run rejects capture_output together with stdout= or stderr= (ValueError, before anything runs):\n" + "\n".join(f"  {clash}" for clash in clashes)


# ---------------------------------------------------------------------------
# (e) H-12: only a listener makes the port «in use»
# ---------------------------------------------------------------------------

#: A deadline for (e)'s connect and accept on loopback, which complete at once: it only turns a hang into a red.
SOCKET_TIMEOUT = 10.0

needs_lsof = pytest.mark.skipif(
    not shutil.which("lsof"),
    reason=f"(e) needs lsof, the tool check_port_in_use prefers on every OS where it exists: this host is {platform.system()}, without lsof on PATH" + ("; its fuser fallback names the connection a server has accepted as well as its listener, by design" if platform.system() == "Linux" else ""),
)


def link(sock: socket.socket) -> str:
    """``local->remote`` of a connected socket, for messages."""
    (local_host, local_port), (remote_host, remote_port) = sock.getsockname()[:2], sock.getpeername()[:2]
    return f"{local_host}:{local_port}->{remote_host}:{remote_port}"


def pids(holders: list[tuple[int, str]]) -> list[int]:
    """The PIDs among ``check_port_in_use``'s ``(pid, name)`` pairs."""
    return [pid for pid, _name in holders]


@needs_lsof
def test_a_socket_holding_the_port_without_listening_is_not_reported():
    """(e) H-12: sockets of this process on a port it no longer listens on do not make that port «in use».

    Listens on ``127.0.0.1``, on a port P the OS picks, connects a client to it and accepts the connection. While the
    listener is open, this pid must be among the holders: the barrier showing that the function sees this process on P
    on this host, so that its silence afterwards means something. Then only the listening socket is closed. This process
    still holds P, through sockets that do not listen: the accepted connection, ESTABLISHED on local port P, as in a
    server that has closed its listener but not yet exited; and the client, connected to remote port P. Asserts that
    ``check_port_in_use(P)`` no longer names this pid. Every socket is closed in a ``finally``.

    Only this pid is asserted, as in (b) and (c): other processes may hold P, and the test owns none of them.

    Red today on macOS: ``lsof -i :P -t`` lists every socket whose local or remote port is P, in any state, so the two
    connections name this process. Red today on Linux too: the function asks ``fuser P/tcp``, which names the accepted
    connection. Green once ``check_port_in_use`` counts listeners only wherever ``lsof`` exists, as the runner's
    ``port_holders`` does (``-sTCP:LISTEN``).
    """
    pid = os.getpid()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client: socket.socket | None = None
    accepted: socket.socket | None = None
    try:
        listener.settimeout(SOCKET_TIMEOUT)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        client = socket.create_connection(("127.0.0.1", port), timeout=SOCKET_TIMEOUT)
        accepted, _peer = listener.accept()

        while_listening = dev.check_port_in_use(port)
        assert pid in pids(while_listening), f"barrier: check_port_in_use({port}) on {platform.system()} returned {while_listening!r} while this process (pid {pid}) was listening on 127.0.0.1:{port}: blind to this listener, its silence once the listener is closed would prove nothing"

        listener.close()
        held = f"the accepted connection {link(accepted)} and the client {link(client)}"
        assert accepted.getsockname()[1] == port and client.getpeername()[1] == port, f"precondition: with its listener closed, this process should still hold port {port} through {held}"

        holders = dev.check_port_in_use(port)
        assert pid not in pids(holders), f"check_port_in_use({port}) on {platform.system()} returned {holders!r}: it names this process (pid {pid}), which no longer listens on port {port} and holds it only through {held}; cmd_server would refuse to start, and --force kill this process"
    finally:
        for sock in (accepted, client, listener):
            if sock is not None:
                sock.close()
