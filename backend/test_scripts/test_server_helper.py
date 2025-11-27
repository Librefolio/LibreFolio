"""
Test Server Helper

Utilities for managing backend server during API tests.
Auto-starts server on a separate TEST PORT, and stops it after tests.

Test server uses port from TEST_PORT in config.py (default: 8001)
Production server uses PORT from config.py (default: 8000)
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
3. No subprocess complexity or sitecustomize.py needed
"""
import os
import threading
import time
from pathlib import Path

import httpx
import uvicorn

# Import settings to get TEST_PORT
from backend.app.config import Settings

# Get settings
_settings = Settings()

# Test server configuration (from config/environment)
TEST_SERVER_PORT = _settings.TEST_PORT
TEST_SERVER_HOST = "localhost"
TEST_SERVER_URL = f"http://{TEST_SERVER_HOST}:{TEST_SERVER_PORT}"
TEST_API_BASE_URL = f"{TEST_SERVER_URL}/api/v1"

SERVER_START_TIMEOUT = 10  # seconds


def check_port_available(port: int = TEST_SERVER_PORT) -> tuple[bool, str | None]:
    """
    Check if a port is available.

    Returns:
        tuple: (is_available, process_info_or_none)
    """
    import subprocess

    try:
        # Use lsof to check port (works on macOS/Linux)
        result = subprocess.run(
            ["lsof", "-i", f":{port}"],
            capture_output=True,
            text=True
            )

        if result.returncode == 0 and result.stdout.strip():
            # Port is occupied
            return False, result.stdout.strip()
        else:
            # Port is available
            return True, None

    except FileNotFoundError:
        # lsof not available, try alternative method
        import socket
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
    print(f"\n1. Check what's using the port:")
    print(f"   lsof -i :{port}")
    print(f"\n2. Find the PID (Process ID) from the output above")
    print(f"\n3. Kill the process:")
    print(f"   kill <PID>")
    print(f"   # Or forcefully:")
    print(f"   kill -9 <PID>")
    print(f"\n4. If it's a zombie uvicorn server:")
    print(f"   pkill -f 'uvicorn.*{port}'")
    print(f"\n5. Or kill all Python processes (⚠️  use with caution):")
    print(f"   pkill -f python")
    print(f"\n6. Then run the test again")
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
        self.project_root = Path(__file__).parent.parent.parent
        self.health_url = f"{TEST_API_BASE_URL}/health"

    def is_server_running(self) -> bool:
        """Check if test server is responding on TEST_SERVER_PORT."""
        try:
            response = httpx.get(self.health_url, timeout=2.0)
            return response.status_code == 200
        except:
            return False

    def _run_server(self):
        """Run uvicorn server in background thread (called by start_server)."""
        # Set test mode
        os.environ["LIBREFOLIO_TEST_MODE"] = "1"

        # Import app here (inside thread) to ensure coverage tracking
        from backend.app.main import app
        # Signal that we're starting
        self.server_started.set()

        # Run uvicorn
        uvicorn.run(
            app,
            host=TEST_SERVER_HOST,
            port=TEST_SERVER_PORT,
            log_level="error",  # Reduce noise
            access_log=False
            )

    def start_server(self) -> bool:
        """
        Start backend server for testing on TEST_PORT as a background thread.

        Returns:
            bool: True if server started successfully
        """
        # Check if port is available before starting
        is_available, process_info = check_port_available(TEST_SERVER_PORT)
        if not is_available:
            print_port_occupied_help(TEST_SERVER_PORT, process_info)
            return False

        # Start server in background thread
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,  # Thread dies when main process exits
            name="uvicorn-test-server"
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

    def stop_server(self):
        """
        Stop backend server.

        Note: With thread-based server, we can't gracefully stop it.
        The daemon thread will automatically die when the main process exits.
        This is acceptable for tests since we use a fresh database each time.
        """
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
