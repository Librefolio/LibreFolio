"""``dev.py``'s ``check_port_in_use(port)`` must see who holds a TCP port on Linux, not only on macOS (N, R2).

``dev.py server`` calls it right before binding, and ``dev.py mkdocs gallery`` before starting its test server: what it
returns is printed under «Port … is already in use!», and it is the list ``--force`` kills.

The defect: the Linux branch runs ``subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True,
stderr=subprocess.DEVNULL)``. Python refuses ``capture_output`` together with ``stdout`` or ``stderr`` before starting
anything (``ValueError: stdout and stderr arguments may not be used with capture_output.``), and the function's
``except Exception: pass`` swallows the error. On Linux it therefore returns ``[]`` for every port: a held port is
reported free, and ``--force`` kills nothing. The macOS branch (``lsof -i :port -t``) works.

Platforms: development runs on macOS and CI on Linux, so the red has to show on macOS too.

* (a) runs on every OS. It forces ``platform.system()`` to ``"Linux"`` and hands the ``fuser`` call to the real
  ``subprocess.run`` with every keyword as written; only argv is swapped, for a Python child that prints this
  process's pid. What rejects the call today is Python's own argument check, the same on every OS: (a) needs neither
  Linux nor a ``fuser`` binary, and reads no port table.
* (b) and (c) run the host's real branch against a socket of their own on ``127.0.0.1``: ``lsof`` on macOS, green
  today; ``fuser`` on Linux, where (b) stays red until the fix. Both skip on a host that has neither ``lsof`` on
  macOS nor ``fuser`` on Linux.
* (d) parses ``dev.py``: no call may pass ``capture_output`` together with ``stdout=`` or ``stderr=``.

PURE: no DB, no server, nothing written. The sockets bind ``127.0.0.1`` on ports the OS picks; the only child
processes are ``lsof``/``fuser`` and ``ps`` (read-only) and, in (a), a Python child that prints a number.
"""

import ast
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

#: The real ``subprocess.run``, taken at import, before any test patches it.
REAL_RUN = subprocess.run

#: (a)'s port. Never probed: the stand-in replaces ``fuser``, so no port table is read.
UNPROBED_PORT = 54_321

#: ``check_port_in_use`` reads ports with ``lsof`` on macOS and ``fuser`` on Linux; (b) and (c) need the host's one.
HOST_PORT_TOOL = {"Darwin": "lsof", "Linux": "fuser"}.get(platform.system())
needs_host_port_tool = pytest.mark.skipif(
    not ((platform.system() == "Darwin" and shutil.which("lsof")) or (platform.system() == "Linux" and shutil.which("fuser"))),
    reason=f"check_port_in_use reads ports with lsof on macOS and fuser on Linux: this host is {platform.system()}" + (f", without {HOST_PORT_TOOL} on PATH" if HOST_PORT_TOOL else ""),
)


# ---------------------------------------------------------------------------
# (a) The Linux branch, through Python's own argument check
# ---------------------------------------------------------------------------


@dataclass
class FuserCall:
    """One ``fuser`` call as ``check_port_in_use`` made it, and what the real ``subprocess.run`` raised on it, if anything."""

    argv: list[str]
    kwargs: dict[str, object]
    error: Exception | None = None


def run_with_fuser_stand_in(fuser_calls: list[FuserCall]):
    """A ``subprocess.run`` for (a), recording every ``fuser`` call into ``fuser_calls``.

    A ``fuser`` call goes to the real ``subprocess.run`` with every keyword as written, so Python's own argument check
    applies; only argv is swapped, for a Python child that prints this process's pid on stdout, where ``fuser`` prints
    its PIDs. Every other call (``ps -p …``) passes through untouched.
    """
    stand_in = [sys.executable, "-c", f"print({os.getpid()})"]

    def run(*popenargs, **kwargs):
        argv = popenargs[0] if popenargs else kwargs.get("args")
        if not (isinstance(argv, (list, tuple)) and argv and Path(str(argv[0])).name == "fuser"):
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
    """(a) The Linux branch, through the real ``subprocess.run`` argument check: red today on every OS.

    ``platform.system()`` says ``"Linux"``, and the ``fuser`` call reaches the real ``subprocess.run`` with its keywords
    as written, argv swapped for a Python child that prints this process's pid. ``ps -p <pid> -o comm=`` runs for real
    (it exists on macOS and Linux alike). Asserts that ``fuser`` was asked about ``<port>/tcp``, and that the function
    returns exactly one pair: this pid, with a non-empty process name. The count is the stand-in's, which prints one
    pid, so the test owns it.

    Red today: the real ``subprocess.run`` raises ``ValueError`` on ``capture_output=True`` with
    ``stderr=subprocess.DEVNULL`` before starting the child, ``except Exception: pass`` swallows it, and the function
    returns ``[]``.
    """
    fuser_calls: list[FuserCall] = []
    monkeypatch.setattr(dev.platform, "system", lambda: "Linux")
    monkeypatch.setattr(dev.subprocess, "run", run_with_fuser_stand_in(fuser_calls))

    holders = dev.check_port_in_use(UNPROBED_PORT)

    asked = [call.argv for call in fuser_calls]
    assert any(f"{UNPROBED_PORT}/tcp" in argv for argv in asked), f"on the Linux branch, check_port_in_use({UNPROBED_PORT}) never asked fuser about {UNPROBED_PORT}/tcp; fuser calls: {asked!r}"

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

    Green today on macOS (``lsof``). Red today on Linux, hence on CI: the ``fuser`` call raises the ``ValueError`` the
    function swallows, and it returns ``[]``.
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

    Green today and after the fix, on macOS and on Linux (where, today, every port comes back ``[]``).
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

    Red today: ``dev.py:100``, the ``fuser`` call of ``check_port_in_use``.
    """
    clashes = capture_output_clashes(DEV_PY)

    assert not clashes, "subprocess.run rejects capture_output together with stdout= or stderr= (ValueError, before anything runs):\n" + "\n".join(f"  {clash}" for clash in clashes)
