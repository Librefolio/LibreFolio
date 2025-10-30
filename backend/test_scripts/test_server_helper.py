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
            time.sleep(0.5)

        # Server didn't start in time
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
