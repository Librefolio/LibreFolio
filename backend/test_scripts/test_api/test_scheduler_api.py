"""
Test: Scheduler API endpoints.

Tests GET /settings/scheduler/state and GET /settings/scheduler/log.
Verifies admin-only access, response structure, and ?since= filter.

Test IDs: SAPI-001..SAPI-008
"""

from typing import Optional

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.services import user_service
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


@pytest.fixture(scope="module")
def test_server():
    """Start test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# Helpers (same pattern as test_settings_api.py)
# ============================================================================

_user_counter = 0
_admin_credentials: Optional[tuple[str, str, str]] = None


def _next_username() -> str:
    global _user_counter
    _user_counter += 1
    return f"sched_api_test_{_user_counter}"


async def _register_and_login(client: httpx.AsyncClient, username: str) -> Optional[str]:
    email = f"{username}@test.com"
    pwd = "TestPass123!"
    await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": email, "password": pwd}, timeout=TIMEOUT)
    resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": pwd}, timeout=TIMEOUT)
    session = resp.cookies.get("session") if resp.status_code == 200 else None
    if session:
        client.cookies.set("session", session)
    return session


async def _promote_to_admin(username: str) -> bool:
    try:
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            success, error = await user_service.set_user_admin(session, username, is_admin=True)
            return success or (error and "already an admin" in error)
    except Exception:
        return False


async def _get_admin_session(client: httpx.AsyncClient) -> str:
    """Get an admin session token, creating and promoting a user if needed."""
    global _admin_credentials

    if _admin_credentials:
        username, _, _ = _admin_credentials
        resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
        session = resp.cookies.get("session") if resp.status_code == 200 else None
        if session:
            client.cookies.set("session", session)
            return session

    username = _next_username()
    session = await _register_and_login(client, username)
    assert session, "Could not create user"

    # Check if already admin (first user in empty DB)
    me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    if me_resp.status_code == 200 and me_resp.json().get("user", {}).get("is_superuser"):
        _admin_credentials = (username, "", session)
        return session

    # Promote
    promoted = await _promote_to_admin(username)
    if promoted:
        resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
        session = resp.cookies.get("session") if resp.status_code == 200 else None
        if session:
            client.cookies.set("session", session)
            _admin_credentials = (username, "", session)
            return session

    pytest.skip("Cannot obtain admin session")


async def _get_normal_session(client: httpx.AsyncClient) -> str:
    """Create a fresh non-admin user and return session."""
    username = _next_username()
    session = await _register_and_login(client, username)
    assert session, f"Could not create user {username}"
    return session


# ============================================================================
# SAPI-001: Admin → GET /settings/scheduler/state → 200
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateAdminOk:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_admin_ok(self):
        """SAPI-001: Admin → GET /settings/scheduler/state → 200."""
        print_section("SAPI-001: GET /settings/scheduler/state — admin")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        print_success("Admin got 200 OK")


# ============================================================================
# SAPI-002: Non-admin → 403
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateNonAdmin:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_non_admin_403(self):
        """SAPI-002: Non-admin user → GET /settings/scheduler/state → 403."""
        print_section("SAPI-002: GET /settings/scheduler/state — non-admin → 403")

        async with httpx.AsyncClient() as client:
            await _get_normal_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print_success("Non-admin correctly rejected with 403")


# ============================================================================
# SAPI-003: Unauthenticated → 401
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateUnauthenticated:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_unauthenticated_401(self):
        """SAPI-003: No session cookie → GET /settings/scheduler/state → 401."""
        print_section("SAPI-003: GET /settings/scheduler/state — unauthenticated → 401")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print_success("Unauthenticated correctly rejected with 401")


# ============================================================================
# SAPI-004: Admin → GET /settings/scheduler/log → 200 + entries list
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogAdminOk:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_admin_ok(self):
        """SAPI-004: Admin → GET /settings/scheduler/log → 200, entries is a list."""
        print_section("SAPI-004: GET /settings/scheduler/log — admin")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/log", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "entries" in data, "Response must have 'entries' key"
        assert isinstance(data["entries"], list), "'entries' must be a list"
        print_success(f"Admin got 200 OK, entries: {len(data['entries'])} items")


# ============================================================================
# SAPI-005: ?since= future date → entries: []
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogSinceFilter:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_since_future(self):
        """SAPI-005: ?since=2099-01-01T00:00:00Z → entries: [] (no future log entries)."""
        print_section("SAPI-005: GET /settings/scheduler/log?since=2099... → empty")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(
                f"{API_BASE}/settings/scheduler/log",
                params={"since": "2099-01-01T00:00:00Z"},
                timeout=TIMEOUT,
            )

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data["entries"] == [], f"Expected empty entries for far-future since, got: {data['entries']}"
        print_success("?since=2099 → empty entries list ✓")


# ============================================================================
# SAPI-006: Non-admin log → 403
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogNonAdmin:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_non_admin_403(self):
        """SAPI-006: Non-admin user → GET /settings/scheduler/log → 403."""
        print_section("SAPI-006: GET /settings/scheduler/log — non-admin → 403")

        async with httpx.AsyncClient() as client:
            await _get_normal_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/log", timeout=TIMEOUT)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print_success("Non-admin rejected with 403 ✓")


# ============================================================================
# SAPI-007: Unauthenticated log → 401
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerLogUnauthenticated:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_log_unauthenticated_401(self):
        """SAPI-007: No session → GET /settings/scheduler/log → 401."""
        print_section("SAPI-007: GET /settings/scheduler/log — unauthenticated → 401")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/scheduler/log", timeout=TIMEOUT)

        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print_success("Unauthenticated log request rejected with 401 ✓")


# ============================================================================
# SAPI-008: State response structure verification
# ============================================================================


@pytest.mark.asyncio
class TestSchedulerStateStructure:
    @pytest.fixture(autouse=True)
    def server(self, test_server):
        yield

    async def test_scheduler_state_structure(self):
        """SAPI-008: State response has required nested fields for both jobs."""
        print_section("SAPI-008: GET /settings/scheduler/state — structure validation")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.get(f"{API_BASE}/settings/scheduler/state", timeout=TIMEOUT)

        assert resp.status_code == 200
        data = resp.json()

        # Top-level keys
        assert "current_price" in data, "Missing 'current_price'"
        assert "history_sync" in data, "Missing 'history_sync'"
        assert "server_tz" in data, "Missing 'server_tz'"

        # current_price fields
        cp = data["current_price"]
        for field in ("last_run_at", "last_duration_s", "last_status", "last_items_ok", "last_items_err"):
            assert field in cp, f"current_price missing field: {field}"

        # history_sync fields
        hs = data["history_sync"]
        for field in ("last_run_at", "last_duration_s", "last_status", "last_items_ok", "last_items_err"):
            assert field in hs, f"history_sync missing field: {field}"

        # server_tz is a non-empty string
        assert isinstance(data["server_tz"], str), "server_tz must be string"
        assert len(data["server_tz"]) > 0, "server_tz must not be empty"

        print_info(f"server_tz: {data['server_tz']}")
        print_info(f"current_price.last_status: {cp['last_status']}")
        print_success("All required state fields present ✓")
