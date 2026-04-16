"""
Tests for backup API endpoints (all placeholder/501).

Covers:
- GET /api/v1/backup/formats: list export formats
- GET /api/v1/backup/status: backup system status
- POST /api/v1/backup/export: export data (501)
- POST /api/v1/backup/restore: restore data (501)
"""

from datetime import datetime

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 10.0


@pytest.fixture(scope="module")
def test_server():
    """Start test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _register_and_login(client: httpx.AsyncClient) -> None:
    """Register a test user and login, setting cookies on the client."""
    timestamp = int(datetime.now().timestamp() * 1000)
    username = f"backup_test_{timestamp}"
    email = f"backup_test_{timestamp}@example.com"
    password = "testpassword123"

    await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    client.cookies.update(login_resp.cookies)


class TestBackupAPI:
    @pytest.mark.asyncio
    async def test_list_export_formats(self, test_server):
        print_section("BACKUP-001: List export formats")
        async with httpx.AsyncClient() as client:
            await _register_and_login(client)
            r = await client.get(f"{API_BASE}/backup/formats", timeout=TIMEOUT)
            assert r.status_code == 200
            data = r.json()
            assert "formats" in data
            assert len(data["formats"]) >= 3
            codes = [f["code"] for f in data["formats"]]
            assert "json" in codes
            assert "csv" in codes
            assert "sqlite" in codes
            print_success("Export formats listed successfully")

    @pytest.mark.asyncio
    async def test_backup_status(self, test_server):
        print_section("BACKUP-002: Backup status")
        async with httpx.AsyncClient() as client:
            await _register_and_login(client)
            r = await client.get(f"{API_BASE}/backup/status", timeout=TIMEOUT)
            assert r.status_code == 200
            data = r.json()
            assert data["status"] == "placeholder"
            print_success("Backup status returned successfully")

    @pytest.mark.asyncio
    async def test_export_data_not_implemented(self, test_server):
        print_section("BACKUP-003: Export returns 501")
        async with httpx.AsyncClient() as client:
            await _register_and_login(client)
            r = await client.post(
                f"{API_BASE}/backup/export",
                json={"format": "json", "scope": ["all"]},
                timeout=TIMEOUT,
            )
            assert r.status_code == 501
            print_success("Export correctly returns 501")

    @pytest.mark.asyncio
    async def test_restore_data_not_implemented(self, test_server):
        print_section("BACKUP-004: Restore returns 501")
        async with httpx.AsyncClient() as client:
            await _register_and_login(client)
            r = await client.post(
                f"{API_BASE}/backup/restore",
                json={"file_id": "nonexistent", "overwrite_existing": False},
                timeout=TIMEOUT,
            )
            assert r.status_code == 501
            print_success("Restore correctly returns 501")

    @pytest.mark.asyncio
    async def test_formats_requires_auth(self, test_server):
        print_section("BACKUP-005: Formats requires auth")
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{API_BASE}/backup/formats", timeout=TIMEOUT)
            assert r.status_code == 401
            print_success("Unauthenticated request correctly rejected")
