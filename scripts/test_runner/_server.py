"""
One test server for the whole run.

Until now every ``test_api`` module started its own uvicorn in a thread, so the
FastAPI app was imported from scratch 47 times per run — measured at roughly 11
of the 15 minutes those invocations cost. It also made the modules mutually
exclusive by construction: two of them could never be in flight at once.

The lifecycle here is not new. ``frontend/playwright.config.ts`` has been
starting the backend exactly this way for a long time, as an *external* process
under ``coverage run``, and that is the part worth copying rather than
reinventing — including the detail that kills runs silently:

    Playwright gracefulShutdown SIGTERM → /bin/sh exec → dev.py os.execvpe()
    → pipenv os.execvpe() → coverage run receives SIGTERM → writes .coverage.<pid>

Every link in that chain uses ``exec`` so the signal reaches ``coverage`` itself.
A SIGKILL anywhere along it discards the whole run's backend coverage without a
word — which is precisely how coverage vanished twice during P7.
"""

import atexit
import contextlib
import math
import os
import signal
import subprocess
import time
import urllib.error
import urllib.request

from ._common import PROJECT_ROOT, Colors, print_error, print_info, print_success

#: Read by backend/test_scripts/test_server_helper.py — see shared_server_mode().
SHARED_SERVER_ENV = "LIBREFOLIO_TEST_SHARED_SERVER"

STARTUP_TIMEOUT = 120
#: Flushing coverage takes real time; a SIGKILL during it loses everything.
SHUTDOWN_GRACE_COVERAGE = 30
SHUTDOWN_GRACE_PLAIN = 5

#: How many concurrent clients one uvicorn worker is expected to serve.
#: Browser workers spend most of their time rendering, so the gallery has long
#: used one server per four of them; API and E2E workers hit the backend far
#: harder, hence one per two.
CLIENTS_PER_SERVER_WORKER = 2
CLIENTS_PER_SERVER_WORKER_GALLERY = 4


def server_workers_for(client_workers: int, per_server: int = CLIENTS_PER_SERVER_WORKER) -> int:
    """Size the backend to the parallelism actually pointed at it.

    One worker is always guaranteed: a run with a single client still needs a
    server, and ``client_workers // per_server`` would otherwise hand back zero.
    """
    try:
        clients = max(1, int(client_workers or 1))
    except (TypeError, ValueError):
        clients = 1
    return max(1, math.ceil(clients / max(1, int(per_server))))


def test_port() -> int:
    try:
        from backend.app.config import Settings

        return int(Settings().TEST_PORT)
    except Exception:
        return int(os.environ.get("TEST_PORT", 6041))


def health_url(port: int | None = None) -> str:
    return f"http://localhost:{port or test_port()}/api/v1/system/health"


def is_healthy(port: int | None = None, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(health_url(port), timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, ValueError):
        return False


def port_holders(port: int | None = None) -> list[str]:
    """PIDs currently holding the port, as strings. Empty when it is free."""
    try:
        out = subprocess.run(
            ["lsof", "-ti", f":{port or test_port()}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return [line for line in out.stdout.split() if line.strip()]
    except Exception:
        return []


class SharedTestServer:
    """Start one backend for the run and hand its address to every test unit."""

    def __init__(
        self,
        coverage: bool = False,
        workers: int | None = None,
        client_workers: int = 1,
        per_server: int = CLIENTS_PER_SERVER_WORKER,
        verbose: bool = False,
    ):
        self.coverage = coverage
        #: An explicit ``workers`` wins; otherwise the backend is sized to the
        #: number of clients that will be hitting it at once.
        self.workers = (
            max(1, int(workers))
            if workers
            else server_workers_for(client_workers, per_server)
        )
        self.client_workers = max(1, int(client_workers or 1))
        self.verbose = verbose
        self.port = test_port()
        self.proc: subprocess.Popen | None = None
        self.started_here = False

    def _command(self) -> str:
        cov = " --coverage" if self.coverage else ""
        # No reloader: it forks a supervisor that survives a signal aimed at the
        # front of the exec chain, and an ephemeral test server has nothing to
        # reload anyway.
        #
        # No scheduler either. populate_mock_data writes last_run_at=yesterday,
        # so every job is due the moment a test server starts: the loop wakes up
        # 5s in and starts refreshing prices against *live* providers. Measured,
        # that alone moved backend coverage by ~700-1300 lines between two
        # identical runs (asset_source.py: 542 then 234) and dragged the network
        # into the suite — one run recorded the Bank of England answering HTML.
        # None of it is attributable to a test. The gallery already disables the
        # scheduler for the same reason: it must not change data mid-run.
        return (
            "exec ./dev.py server --test --force --no-reload --no-scheduler "
            f"--workers {self.workers}{cov}"
        )

    def start(self) -> bool:
        if is_healthy(self.port) and not self.coverage:
            print_info(f"Reusing backend already healthy on port {self.port}")
            return True

        print_info(
            f"Starting shared test backend on port {self.port}"
            f"{' (coverage)' if self.coverage else ''}"
            f" — {self.workers} uvicorn worker(s) for {self.client_workers} client(s)"
        )
        # Its own process group: outside coverage mode dev.py starts uvicorn with
        # --reload, which spawns a supervisor plus the actual server. Signalling
        # only our direct child kills the front of that chain and leaves the rest
        # reparented to init, still holding the port — which is exactly the
        # "zombie server" that --force was invented to clean up afterwards.
        # Owning the group lets us take the whole tree down properly instead.
        self.proc = subprocess.Popen(
            self._command(),
            shell=True,
            cwd=PROJECT_ROOT,
            stdout=None if self.verbose else subprocess.DEVNULL,
            stderr=None if self.verbose else subprocess.DEVNULL,
            start_new_session=True,
        )
        self.started_here = True

        deadline = time.time() + STARTUP_TIMEOUT
        while time.time() < deadline:
            if is_healthy(self.port):
                print_success(f"Shared backend ready on port {self.port}")
                return True
            if self.proc.poll() is not None:
                print_error(f"Shared backend exited during startup (code {self.proc.returncode})")
                return False
            time.sleep(0.5)

        print_error(f"Shared backend did not answer within {STARTUP_TIMEOUT}s")
        self.stop()
        return False

    def stop(self) -> None:
        """SIGTERM the whole group and wait, so ``coverage run`` writes its data."""
        if not self.proc or not self.started_here:
            return
        if self.proc.poll() is not None:
            self.proc = None
            return

        grace = SHUTDOWN_GRACE_COVERAGE if self.coverage else SHUTDOWN_GRACE_PLAIN
        if not self._signal_group(signal.SIGTERM):
            self.proc = None
            return

        try:
            self.proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            print_error(f"Shared backend ignored SIGTERM for {grace}s — killing it")
            if self.coverage:
                print(f"   {Colors.YELLOW}⚠️  Backend coverage for this run is likely lost{Colors.NC}")
            self._signal_group(signal.SIGKILL)
            try:
                self.proc.wait(timeout=5)
            except Exception:
                pass
        finally:
            self.proc = None

        # Health going away is not enough: what the next run needs is the *port*
        # back. A process on its way out can stop answering while still holding
        # the socket, which is exactly the window that makes a following run find
        # the port busy and blame a zombie.
        deadline = time.time() + grace
        while time.time() < deadline and port_holders(self.port):
            time.sleep(0.25)
        holders = port_holders(self.port)
        if holders:
            print_error(f"Port {self.port} still held by PID(s) {', '.join(holders)} after shutdown")
        elif self.coverage:
            print_success("Shared backend stopped; coverage flushed")

    def _signal_group(self, sig) -> bool:
        """Signal the server's whole process group; fall back to the child alone."""
        if not self.proc:
            return False
        try:
            os.killpg(os.getpgid(self.proc.pid), sig)
            return True
        except (ProcessLookupError, PermissionError, OSError):
            try:
                self.proc.send_signal(sig)
                return True
            except ProcessLookupError:
                return False

    def env(self) -> dict:
        """Environment that tells test modules to attach instead of starting one."""
        env = os.environ.copy()
        env[SHARED_SERVER_ENV] = "1"
        return env

    def __enter__(self):
        if not self.start():
            raise RuntimeError("shared test backend failed to start")
        os.environ[SHARED_SERVER_ENV] = "1"
        _set_active(self)
        _install_last_resort_teardown()
        return self

    def __exit__(self, *exc):
        _set_active(None)
        os.environ.pop(SHARED_SERVER_ENV, None)
        self.stop()
        _remove_last_resort_teardown()
        return False


#: Signals that end the runner without unwinding the stack. `with` already covers
#: a normal return and any exception — including Ctrl-C, which arrives as
#: KeyboardInterrupt — but Python's default handling of SIGTERM and SIGHUP calls
#: no `__exit__` at all. The server was started with `start_new_session=True`, so
#: it is deliberately outside the terminal's foreground group: nothing else will
#: reach it. That is the whole of how a backend ends up reparented to init and
#: sitting on port 6041 for hours, serving stale code to every later run.
_TEARDOWN_SIGNALS = (signal.SIGTERM, signal.SIGHUP)

_previous_handlers: dict = {}
_atexit_registered = False


def _teardown_active(*_args) -> None:
    server = _ACTIVE
    if server is not None:
        server.stop()


def _signal_teardown(signum, _frame):
    _teardown_active()
    # Restore the default and re-raise, so the exit status still says "killed by
    # this signal" instead of pretending the run ended on its own terms.
    signal.signal(signum, _previous_handlers.get(signum, signal.SIG_DFL))
    os.kill(os.getpid(), signum)


def _install_last_resort_teardown() -> None:
    global _atexit_registered
    if not _atexit_registered:
        atexit.register(_teardown_active)
        _atexit_registered = True
    for sig in _TEARDOWN_SIGNALS:
        try:
            _previous_handlers[sig] = signal.signal(sig, _signal_teardown)
        except (ValueError, OSError):
            # Not the main thread, or the platform has no such signal.
            pass


def _remove_last_resort_teardown() -> None:
    for sig, previous in list(_previous_handlers.items()):
        try:
            signal.signal(sig, previous)
        except (ValueError, OSError):
            pass
        _previous_handlers.pop(sig, None)


#: The server this invocation is running, if any. A destructive database
#: operation needs to reach it, and threading a handle through six call sites
#: that do not otherwise care about servers would be worse than a module global.
_ACTIVE: "SharedTestServer | None" = None


def _set_active(server) -> None:
    global _ACTIVE
    _ACTIVE = server


@contextlib.contextmanager
def database_file_owned_exclusively(reason: str):
    """Step the shared backend aside for an operation that owns the database file.

    ``db create`` deletes ``app.db`` and rebuilds it from the migrations. A server
    attached to the old inode keeps writing to a file nobody can see, and
    ``dev.sh db:upgrade`` rightly refuses to run at all — so, before this existed,
    ``./dev.py test all-backend`` could not get past its own database category.

    Restarting is cheap and, under coverage, safe: ``stop()`` waits for
    ``coverage run`` to flush its ``.coverage.<pid>``, and the second process
    writes its own, which ``coverage combine`` merges. Nothing is discarded.
    """
    server = _ACTIVE
    if server is None:
        yield
        return

    print_info(f"Pausing the shared backend — {reason} needs the database file to itself")
    os.environ.pop(SHARED_SERVER_ENV, None)
    server.stop()
    try:
        yield
    finally:
        if server.start():
            os.environ[SHARED_SERVER_ENV] = "1"
            print_success("Shared backend resumed")
        else:
            _set_active(None)
            print_error("Shared backend did not come back up — the units that need it will say so")
