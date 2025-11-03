"""
Test Server Helper

Utilities for managing backend server during API tests.
Auto-starts server on a separate TEST PORT, and stops it after tests.

Test server uses port from TEST_PORT in config.py (default: 8001)
Production server uses PORT from config.py (default: 8000)
Both configurable via environment variables.
"""
import os
import subprocess
import time
from pathlib import Path

import httpx

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
    print(f"\n{'='*60}")
    print(f"⚠️  ERROR: Port {port} is already in use")
    print(f"{'='*60}")
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
    print(f"{'='*60}\n")


class TestServerManager:
    """
    Manages backend server lifecycle for tests.

    - ALWAYS starts fresh server on TEST_PORT for each test
    - ALWAYS stops server at end of test
    - Uses test database (configured via DATABASE_URL)
    - Avoids conflicts with production server (PORT, default: 8000)
    """

    def __init__(self):
        self.server_process = None
        self.project_root = Path(__file__).parent.parent.parent
        self.health_url = f"{TEST_API_BASE_URL}/health"

    def is_server_running(self) -> bool:
        """Check if test server is responding on TEST_SERVER_PORT."""
        try:
            response = httpx.get(self.health_url, timeout=2.0)
            return response.status_code == 200
        except:
            return False

    def start_server(self) -> bool:
        """
        Start backend server for testing on TEST_PORT.

        Returns:
            bool: True if server started successfully
        """
        # Check if port is available before starting
        is_available, process_info = check_port_available(TEST_SERVER_PORT)
        if not is_available:
            print_port_occupied_help(TEST_SERVER_PORT, process_info)
            return False

        # Prepare environment with test port
        env = os.environ.copy()
        # Ensure TEST_PORT is used (already set in config, but can be overridden)

        # Start server in background
        self.server_process = subprocess.Popen(
            [
                "pipenv", "run", "uvicorn", "backend.app.main:app",
                "--host", TEST_SERVER_HOST, "--port", str(TEST_SERVER_PORT)
                ],
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env
            )

        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < SERVER_START_TIMEOUT:
            if self.is_server_running():
                return True
            
            # Check if process crashed
            if self.server_process.poll() is not None:
                # Process exited
                stdout, stderr = self.server_process.communicate()
                print(f"\n{'='*60}")
                print("⚠️  Server process exited unexpectedly")
                print(f"{'='*60}")
                print("\n📋 Server STDOUT:")
                print(stdout[-500:] if stdout else "(empty)")
                print("\n📋 Server STDERR:")
                print(stderr[-500:] if stderr else "(empty)")
                print(f"{'='*60}\n")
                return False
            
            time.sleep(0.5)

        # Server didn't start in time - show logs
        stdout, stderr = self.server_process.communicate(timeout=1)
        print(f"\n{'='*60}")
        print(f"⚠️  Server didn't start within {SERVER_START_TIMEOUT} seconds")
        print(f"{'='*60}")
        print("\n📋 Server STDOUT:")
        print(stdout[-500:] if stdout else "(empty)")
        print("\n📋 Server STDERR:")
        print(stderr[-500:] if stderr else "(empty)")
        print(f"{'='*60}\n")
        
        self.stop_server()
        return False

    def stop_server(self):
        """Stop backend server (always stops at end of test)."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None

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
