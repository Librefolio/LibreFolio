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
import signal
import subprocess
import threading
import time

import httpx
import uvicorn

# Import settings to get TEST_PORT
from backend.app.config import PROJECT_ROOT, Settings

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

    try:
        # Use lsof to check port (works on macOS/Linux)
        result = subprocess.run(["lsof", "-i", f":{port}"], capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            # Port is occupied
            return False, result.stdout.strip()
        else:
            # Port is available
            return True, None

    except FileNotFoundError:
        # lsof not available, try alternative method
        import socket  # noqa: PLC0415 — test setup — imports after sys.path/db config

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                return True, None
            except OSError:
                return False, f"Port {port} is in use (unable to get process details)"


def print_port_occupied_help(port: int, process_info: str):
    """Print helpful instructions when port is occupied."""
    print(f"\n{'=' * 60}")
    print(f"⚠️  ERROR: Port {port} is already in use")
    print(f"{'=' * 60}")
    print("\n📋 Process using the port:")
    print(process_info)
    print("\n💡 How to fix this:")
    print("\n1. Check what's using the port:")
    print(f"   lsof -i :{port}")
    print("\n2. Find the PID (Process ID) from the output above")
    print("\n3. Kill the process:")
    print("   kill <PID>")
    print("   # Or forcefully:")
    print("   kill -9 <PID>")
    print("\n4. If it's a zombie uvicorn server:")
    print(f"   pkill -f 'uvicorn.*{port}'")
    print("\n5. Or kill all Python processes (⚠️  use with caution):")
    print("   pkill -f python")
    print("\n6. Then run the test again")
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
        self.health_url = f"{TEST_API_BASE_URL}/system/health"
        self.attached_to_shared = False

    def is_server_running(self) -> bool:
        """Check if test server is responding on TEST_SERVER_PORT."""
        try:
            response = httpx.get(self.health_url, timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False

    @staticmethod
    def _force_kill_port(port: int) -> bool:
        """
        Kill any *foreign* processes occupying the given port (zombie cleanup).

        Never kills the calling process. The test server runs as a thread inside
        this very process, so as soon as two API modules share a pytest process
        ``lsof`` reports our own PID — killing it would make the process SIGKILL
        itself and take the whole run (and its coverage) down with it.

        Returns:
            bool: True if the port is held by this process, in which case there
                  is nothing to clean up and the caller must not treat the port
                  as occupied by a zombie.
        """
        self_pid = os.getpid()
        held_by_self = False
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}", "-t"],
                capture_output=True,
                text=True,
            )
            if result.stdout.strip():
                pids = [int(p) for p in result.stdout.strip().split("\n") if p]
                for pid in pids:
                    if pid == self_pid:
                        held_by_self = True
                        continue
                    try:
                        os.kill(pid, signal.SIGKILL)
                        print(f"  ✗ Killed zombie PID {pid}")
                    except (ProcessLookupError, PermissionError):
                        pass
        except Exception:
            pass
        return held_by_self

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

    def start_server(self) -> bool:
        """
        Start backend server for testing on TEST_PORT as a background thread.

        Automatically kills zombie processes on the test port (--force behavior).

        Returns:
            bool: True if server started successfully
        """
        if shared_server_mode():
            return self._attach_to_shared_server()

        # Force-kill any zombie processes on the test port
        is_available, process_info = check_port_available(TEST_SERVER_PORT)
        if not is_available:
            print(f"\n⚠️  Port {TEST_SERVER_PORT} is occupied — killing zombie process(es)...")
            # Kills every *foreign* holder (--force behaviour): a leftover server
            # from a previous run must die even if it still answers, otherwise we
            # would test the stale code it has in memory. Only our own PID is
            # spared — see below.
            held_by_self = self._force_kill_port(TEST_SERVER_PORT)

            if held_by_self:
                # The port belongs to a server thread inside *this* process, so it
                # runs the very code under test: reusing it is correct, and killing
                # it would mean SIGKILLing ourselves.
                if self.is_server_running():
                    print(f"✅ Reusing test server already listening on port {TEST_SERVER_PORT}")
                    return True
                print(f"\n❌ Port {TEST_SERVER_PORT} is held by this very process (PID {os.getpid()}) but no server is answering.\n   A previous test server thread is still bound to the port; it cannot be freed without killing the test run itself.")
                return False

            time.sleep(1)
            # Re-check
            is_available, process_info = check_port_available(TEST_SERVER_PORT)
            if not is_available:
                print_port_occupied_help(TEST_SERVER_PORT, process_info)
                return False
            print(f"✅ Port {TEST_SERVER_PORT} is now free")

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
            if self.is_server_running():
                return True
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
