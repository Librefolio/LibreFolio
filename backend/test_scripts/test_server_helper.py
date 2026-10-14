"""
Test Server Helper

Utilities for managing backend server during API tests.
Auto-starts server on a separate TEST PORT, and stops it after tests.

Test server uses port from TEST_PORT in config.py (default: 6041)
Production server uses PORT from config.py (default: 6040)
Both configurable via environment variables.

Coverage:
---------
Server runs as a THREAD (not subprocess) to enable pytest-cov tracking.
This allows full coverage of endpoint code (backend/app/api/v1/*.py).

With `concurrency = thread,gevent` in .coveragerc:
- ✅ Full async/await tracking in FastAPI handlers
- ✅ ~46-62% endpoint coverage (realistic, test-driven)
- ✅ Tracks all async context switches correctly

This is achieved by:
1. Running uvicorn.run() in a daemon thread (same process as pytest)
2. Using gevent for asyncio event loop instrumentation
3. No subprocess complexity needed
"""

import os
import threading
import time
import urllib.parse

import httpx
import uvicorn

# Import settings to get TEST_PORT
from backend.app.config import PROJECT_ROOT, TEST_LANE_HEADER, Settings
from scripts.cli_base import ensure_test_lane_id

# Get settings
_settings = Settings()

# Test server configuration (from config/environment)
TEST_SERVER_PORT = _settings.TEST_PORT
TEST_SERVER_HOST = "localhost"
TEST_SERVER_URL = f"http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}"
TEST_API_BASE_URL = f"{TEST_SERVER_URL}/api/v1"

SERVER_START_TIMEOUT = 10  # seconds

#: Set by the test runner when it has started one server for the whole run.
SHARED_SERVER_ENV = "LIBREFOLIO_TEST_SHARED_SERVER"


def shared_server_mode() -> bool:
    """
    True when the runner owns the server and test modules must not touch it.

    Every ``test_api`` module used to start its own uvicorn, which meant
    re-importing the whole FastAPI app once per module: measured at roughly 11 of
    the 15 minutes those 47 invocations took. Worse, it made the modules mutually
    exclusive, so they could only ever run one after the other.

    With one server for the whole run the modules become *clients*, which is also
    what they already were in spirit — they all talk HTTP to ``API_BASE``, never
    to the ASGI app in process. Several of them hitting it at once is not a
    compromise: it is the first time the backend's real concurrency is exercised.
    """
    return os.environ.get(SHARED_SERVER_ENV, "").strip().lower() in {"1", "true", "yes"}


def check_port_available(port: int = TEST_SERVER_PORT) -> tuple[bool, str | None]:
    """
    Check if a port is available.

    Returns:
        tuple: (is_available, process_info_or_none)
    """
    import subprocess  # noqa: PLC0415 — test setup — imports after sys.path/db config

    process_info = None
    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            process_info = result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass

    if process_info:
        return False, process_info

    # lsof may be unavailable or unable to identify another user's process.
    # Binding is the authoritative fallback: an unverifiable occupied port must
    # still fail closed rather than be treated as free.
    import socket  # noqa: PLC0415 — test setup — imports after sys.path/db config

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            # Ignore sockets left only in TIME_WAIT; a live listener still
            # makes bind fail, preserving the occupied-port guard.
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((TEST_SERVER_HOST, port))
            return True, None
        except OSError:
            return False, f"Port {port} is in use (unable to get process details)"


def port_holder_pids(port: int = TEST_SERVER_PORT) -> set[int] | None:
    """Return listening PIDs, or ``None`` when ownership cannot be verified."""
    import subprocess  # noqa: PLC0415 — test setup — imports after sys.path/db config

    try:
        result = subprocess.run(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if result.returncode not in (0, 1):
        return None

    holders: set[int] = set()
    try:
        for raw_pid in result.stdout.split():
            holders.add(int(raw_pid))
    except ValueError:
        return None
    return holders


def print_port_occupied_help(port: int, process_info: str | None):
    """Print helpful instructions when port is occupied."""
    print(f"\n{'=' * 60}")
    print(f"⚠️  ERROR: Port {port} is already in use")
    print(f"{'=' * 60}")
    if process_info:
        print("\n📋 Process using the port:")
        print(process_info)
    print("\nRefusing to reuse or terminate the listener because it may belong")
    print("to another worktree's test lane.")
    print("\nUse a unique lane for each concurrent command:")
    print("   ./dev.py test --test-port <free-port> --data-dir <unique-dir> ...")
    print("\nTo inspect the current listener:")
    print(f"   lsof -i :{port}")
    print(f"{'=' * 60}\n")


class _TestingServerManager:
    """
    Manages backend server lifecycle for tests.

    - Starts server as background THREAD (for coverage tracking)
    - Uses TEST_PORT to avoid conflicts with production server
    - Uses test database (configured via DATABASE_URL)
    - Automatically stops server at end of test
    """

    def __init__(self):
        self.server_thread = None
        self.server_started = threading.Event()
        self.project_root = PROJECT_ROOT
        self.lane_id = ensure_test_lane_id()
        query = urllib.parse.urlencode({"token": self.lane_id})
        self.health_url = f"{TEST_API_BASE_URL}/system/test-lane-health?{query}"
        self.attached_to_shared = False

    def is_server_running(self) -> bool:
        """Check if test server is responding on TEST_SERVER_PORT."""
        try:
            response = httpx.get(self.health_url, timeout=2.0)
            return response.status_code == 200 and response.headers.get(TEST_LANE_HEADER) == self.lane_id
        except Exception:
            return False

    def _run_server(self):
        """Run uvicorn server in background thread (called by start_server)."""
        # Set test mode using the proper function (updates both env var and global flag)
        from backend.app.config import set_test_mode  # noqa: PLC0415 — test setup — imports after sys.path/db config

        set_test_mode(True)

        # Import app here (inside thread) to ensure coverage tracking
        from backend.app.main import app  # noqa: PLC0415 — test setup — imports after sys.path/db config

        # Signal that we're starting
        self.server_started.set()

        # Run uvicorn
        uvicorn.run(
            app,
            host=TEST_SERVER_HOST,
            port=TEST_SERVER_PORT,
            log_level="error",  # Reduce noise
            access_log=False,
        )

    @staticmethod
    def _reject_unowned_listener(
        holders: set[int] | None,
        process_info: str | None,
        *,
        healthy: bool,
    ) -> bool:
        """Report a foreign/unverifiable listener and fail without touching it."""
        foreign_pids = sorted(pid for pid in holders or set() if pid != os.getpid())
        if foreign_pids:
            if healthy:
                print(f"\n❌ Healthy listener on port {TEST_SERVER_PORT} is " f"held by foreign PID(s) " f"{', '.join(str(pid) for pid in foreign_pids)}.")
            else:
                print(f"\n❌ Port {TEST_SERVER_PORT} is held by foreign PID(s) " f"{', '.join(str(pid) for pid in foreign_pids)}.")
        elif healthy:
            print(f"\n❌ Could not verify ownership of healthy listener " f"on port {TEST_SERVER_PORT}.")
        else:
            print(f"\n❌ Could not verify ownership of occupied port {TEST_SERVER_PORT}.")
        print_port_occupied_help(TEST_SERVER_PORT, process_info)
        return False

    def _reuse_occupied_port(self, process_info: str | None) -> bool:
        """Reuse only a healthy listener owned solely by this process.

        ``port_holder_pids`` has three distinct outcomes here, and each is
        handled on its own terms:

        - ``None`` — lsof is unavailable/unusable, so ownership cannot be
          verified by PID at all. The only thing that can stand in for it is
          the lane-authenticated health check: only *our own* in-process
          server can answer its private lane token, so a success there is
          accepted as proof of ownership. Absent that proof, fail closed.
        - a concrete set equal to ``{os.getpid()}`` — verified as ours.
        - any other concrete set, including the *empty* set — lsof actually
          ran and positively identified the holder(s) as not us (an empty set
          still means "confirmed, and definitely not this process"). A
          concrete answer must fail closed regardless of health, because a
          foreign process could be relaying/proxying the health check.
        """
        holders = port_holder_pids(TEST_SERVER_PORT)

        if holders is None:
            if self.is_server_running():
                print(f"✅ Reusing test server already listening on port {TEST_SERVER_PORT} " "(lsof unavailable; ownership verified via authenticated health)")
                return True
            return self._reject_unowned_listener(None, process_info, healthy=False)

        if holders != {os.getpid()}:
            return self._reject_unowned_listener(
                holders,
                process_info,
                healthy=False,
            )

        # The port belongs to a server thread inside *this* process, so it runs
        # the very code under test: reusing it is correct, and killing it would
        # mean SIGKILLing ourselves.
        if self.is_server_running():
            print(f"✅ Reusing test server already listening on port {TEST_SERVER_PORT}")
            return True
        print(f"\n❌ Port {TEST_SERVER_PORT} is held by this very process " f"(PID {os.getpid()}) but no server is answering.\n" "   A previous test server thread is still bound to the port; " "it cannot be freed without killing the test run itself.")
        return False

    def _verify_new_listener(self, server_thread: threading.Thread) -> bool:
        """Accept post-launch health only when this live process owns the port.

        The caller only reaches this method after its own authenticated
        health probe has already succeeded (see ``start_server``). That still
        is not proof of ownership by itself — the free-port preflight and
        uvicorn's bind are not atomic, so a foreign process could have won
        that race and be answering in our stead. ``port_holder_pids`` settles
        it when it can: a concrete ``{os.getpid()}`` confirms us, any other
        concrete set (including empty) fails closed regardless of health. When
        it returns ``None`` (lsof unavailable/unusable), ownership cannot be
        verified by PID at all, so the launch thread being alive *and* the
        already-succeeded authenticated health check are accepted together as
        proof — only our own in-process server can answer that lane-specific
        token.
        """
        if not server_thread.is_alive():
            print(f"\n❌ Test server thread exited while another listener " f"answered on port {TEST_SERVER_PORT}.")
            return False

        holders = port_holder_pids(TEST_SERVER_PORT)
        if holders is None:
            return True
        if holders == {os.getpid()}:
            return True
        return self._reject_unowned_listener(holders, None, healthy=True)

    def start_server(self) -> bool:
        """
        Start backend server for testing on TEST_PORT as a background thread.

        An occupied port is reused only when this pytest process demonstrably
        owns it: either ``port_holder_pids`` names only this process, or — when
        lsof cannot verify ownership by PID at all — the lane-authenticated
        health check succeeds, which only our own in-process server could
        answer. A concrete foreign or unowned PID set is never signalled and
        must use a different test lane, even if a health probe answers.

        Returns:
            bool: True if server started successfully
        """
        if shared_server_mode():
            return self._attach_to_shared_server()

        is_available, process_info = check_port_available(TEST_SERVER_PORT)
        if not is_available:
            return self._reuse_occupied_port(process_info)

        # Start server in background thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,  # Thread dies when main process exits
            name="uvicorn-test-server",
        )
        self.server_thread.start()

        # Wait for thread to signal start
        self.server_started.wait(timeout=2)

        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < SERVER_START_TIMEOUT:
            server_thread = self.server_thread
            if server_thread is None or not server_thread.is_alive():
                print(f"\n❌ Test server thread exited before it owned a healthy " f"listener on port {TEST_SERVER_PORT}.")
                return False

            if self.is_server_running():
                # The free-port preflight and uvicorn's bind are not atomic. A
                # foreign process can win that race and answer our health probe
                # while this thread is still starting (or has already died).
                # Health is therefore necessary but not proof of ownership.
                return self._verify_new_listener(server_thread)
            time.sleep(0.5)

        # Server didn't start in time
        print(f"\n{'=' * 60}")
        print(f"⚠️  Server didn't start within {SERVER_START_TIMEOUT} seconds")
        print(f"{'=' * 60}\n")
        return False

    def _attach_to_shared_server(self) -> bool:
        """
        Use the server the runner already started, without starting or killing one.

        Failing loudly here matters: silently falling back to a private server
        would restore the per-module uvicorn this mode exists to remove, and the
        run would still be green — hiding the regression for good.
        """
        deadline = time.time() + SERVER_START_TIMEOUT
        while time.time() < deadline:
            if self.is_server_running():
                self.attached_to_shared = True
                return True
            time.sleep(0.25)

        print(f"\n{'=' * 60}")
        print(f"❌ {SHARED_SERVER_ENV} is set but no server answers on port {TEST_SERVER_PORT}.")
        print("   The runner is expected to own the server for the whole run.")
        print(f"{'=' * 60}\n")
        return False

    def stop_server(self):
        """
        Stop backend server.

        Note: With thread-based server, we can't gracefully stop it.
        The daemon thread will automatically die when the main process exits.
        This is acceptable for tests since we use a fresh database each time.

        In shared-server mode this is a no-op for a different reason: the server
        belongs to the runner, and tearing it down here would break every module
        scheduled after this one.
        """
        if self.attached_to_shared:
            return
        # Thread is daemon, will auto-stop when main process exits
        # We just clear our reference
        self.server_thread = None
        self.server_started.clear()

    def get_base_url(self) -> str:
        """Get the test server base URL."""
        return TEST_SERVER_URL

    def get_api_base_url(self) -> str:
        """Get the test API base URL."""
        return TEST_API_BASE_URL

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup server."""
        self.stop_server()
