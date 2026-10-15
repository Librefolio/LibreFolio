"""
Tests for backup API endpoints (all placeholder/501).

Covers:
- GET /api/v1/backup/formats: list export formats
- GET /api/v1/backup/status: backup system status
- POST /api/v1/backup/export: export data (501)
- POST /api/v1/backup/restore: restore data (501)
- the /backup router split one module per resource (C2): exactly the seven routes of backup.py, in their order, each
  with its method, the single Backup & Export tag and its endpoint module (pure: no server, no database)
"""

from datetime import datetime

import httpx
import pytest
from fastapi.routing import iter_route_contexts

import backend.app.api.v1.backup as backup_module
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


# ============================================================================
# THE /backup ROUTER, ONE MODULE PER RESOURCE (rule C2)
# ============================================================================
#
# backup.py became the package api/v1/backup/, whose __init__.py composes backup_router from instance.py (the
# full-instance placeholders) and then exports.py (the per-series exports). The composition must register the routes
# exactly as the single module did, in its order: the registration order is the order of the OpenAPI document and
# the order routes are matched in, and swapping the two include_router calls would change both without any error.
# Pure: the test reads the composed router object, so it requests neither test_server nor the database. With
# FastAPI 0.141 an included router is a wrapper in .routes: iter_route_contexts yields the effective routes, with
# the prefix and the tags applied.

#: The routes of the single backup.py, in registration order, as (method, path, endpoint), the endpoint that serves
#: the route now as <module>.<function> under backend.app.api.v1.backup.
BACKUP_ROUTES_OF_THE_SPLIT = [
    ("POST", "/backup/export", "instance.export_data"),
    ("POST", "/backup/restore", "instance.restore_data"),
    ("GET", "/backup/formats", "instance.list_export_formats"),
    ("GET", "/backup/status", "instance.backup_status"),
    ("GET", "/backup/asset/{asset_id}/prices", "exports.backup_asset_prices"),
    ("GET", "/backup/asset/{asset_id}/events", "exports.backup_asset_events"),
    ("GET", "/backup/fx/{base}/{quote}/rates", "exports.backup_fx_rates"),
]


def test_the_split_keeps_the_routes_of_backup_py_in_their_order():
    """C2: the composed backup_router registers exactly the seven routes of backup.py, in their order, each with its method, under the single Backup & Export tag, served by its resource's module."""
    print_section("BACKUP-006: The /backup router keeps the routes of backup.py in their order (C2)")
    contexts = list(iter_route_contexts(backup_module.backup_router.routes))
    served = [(",".join(sorted(ctx.methods or ())), ctx.path, f"{getattr(ctx.endpoint, '__module__', '?').removeprefix(backup_module.__name__ + '.')}.{getattr(ctx.endpoint, '__name__', '?')}") for ctx in contexts]
    assert served == BACKUP_ROUTES_OF_THE_SPLIT, f"the /backup router changed: the split must keep exactly the routes of backup.py, in their order:\n  expected {BACKUP_ROUTES_OF_THE_SPLIT}\n  got      {served}"
    tags = [(ctx.path, list(getattr(ctx, "tags", []))) for ctx in contexts]
    assert all(route_tags == ["Backup & Export"] for _path, route_tags in tags), f"each route of the /backup router must carry the single tag Backup & Export, and no other:\n  expected ['Backup & Export'] on each route\n  got      {tags}"
    print_success(f"{len(served)} routes of backup.py, in their order: {[path for _method, path, _endpoint in served]}")
