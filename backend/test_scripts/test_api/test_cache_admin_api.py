"""
Test: Cache Admin API endpoints.

Tests the cache administration endpoints under /settings/cache:
- GET  /settings/cache/status          — any authenticated user
- POST /settings/cache/clear-all       — admin only
- POST /settings/cache/clear/{name}    — admin only, 404 on unknown name

The functional test (CAPI-008) populates the ``upload_metadata`` cache through a
real upload (``save_upload`` caches the metadata sidecar on write), clears it
through the endpoint, and verifies via a second status read that the cache is
empty. A baseline clear establishes size 0 first, so the +1 the upload creates
is a count this test owns.

Test IDs: CAPI-001..CAPI-008
"""

from io import BytesIO
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

# Caches registered at module level by the services the app imports at startup.
# Caches register lazily, so tests assert an intersection with this set — never
# the full set.
KNOWN_CACHES = {
    "search_results",
    "search_queries",
    "asset_history_fetch",
    "asset_current_fetch",
    "asset_metadata_fetch",
    "fx_provider_responses",
    "portfolio_blob",
    "portfolio_layer2",
    "portfolio_wac",
    "upload_metadata",
    "yfinance_currency",
    "justetf_overview",
    "justetf_chart",
    "justetf_etf_list",
    "scheduled_investment",
}

# Preferred clear targets: cheap to repopulate, harmless to evict.
CLEAR_PREFERENCE = ["upload_metadata", "search_results", "fx_provider_responses", "portfolio_wac"]

BOGUS_CACHE_NAME = "definitely_not_a_real_cache_name"


@pytest.fixture(scope="module")
def test_server():
    """Start test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# Helpers (same pattern as test_scheduler_api.py)
# ============================================================================

_user_counter = 0
_admin_credentials: Optional[tuple[str, str, str]] = None


def _next_username() -> str:
    global _user_counter
    _user_counter += 1
    return f"cache_api_test_{_user_counter}"


async def _register_and_login(client: httpx.AsyncClient, username: str) -> Optional[str]:
    """Register (idempotent) and log in; return the session cookie and set it on the client."""
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


async def _status_by_name(client: httpx.AsyncClient) -> dict[str, dict]:
    """GET /settings/cache/status and index the items by cache name."""
    resp = await client.get(f"{API_BASE}/settings/cache/status", timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 from cache status, got {resp.status_code}: {resp.text}"
    items = resp.json()["items"]
    assert isinstance(items, list), "'items' must be a list"
    return {entry["name"]: entry for entry in items}


# ============================================================================
# CAPI-001/002: GET /settings/cache/status
# ============================================================================


class TestCacheStatus:
    """Tests for GET /settings/cache/status."""

    @pytest.mark.asyncio
    async def test_status_unauthenticated_401(self, test_server):
        """CAPI-001: No session cookie → GET /settings/cache/status → 401."""
        print_section("CAPI-001: GET /settings/cache/status — unauthenticated → 401")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/cache/status", timeout=TIMEOUT)

        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
        print_success("Unauthenticated correctly rejected with 401")

    @pytest.mark.asyncio
    async def test_status_normal_user_200(self, test_server):
        """CAPI-002: Normal user → 200, known caches present, entry fields typed."""
        print_section("CAPI-002: GET /settings/cache/status — normal user")

        async with httpx.AsyncClient() as client:
            await _get_normal_session(client)
            resp = await client.get(f"{API_BASE}/settings/cache/status", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "items" in data, "Response must have 'items' key"
        items = data["items"]
        assert isinstance(items, list), "'items' must be a list"

        for entry in items:
            assert isinstance(entry["name"], str) and entry["name"], "entry.name must be a non-empty string"
            assert isinstance(entry["current_size"], int) and entry["current_size"] >= 0, f"entry {entry['name']}: current_size must be a non-negative int"
            assert isinstance(entry["maxsize"], int) and entry["maxsize"] >= 1, f"entry {entry['name']}: maxsize must be a positive int"
            assert entry["ttl_seconds"] > 0, f"entry {entry['name']}: ttl_seconds must be positive"

        # Caches register lazily: at least one of the caches the app registers at
        # startup must be visible — never assert the full set.
        present = {entry["name"] for entry in items}
        known_present = present & KNOWN_CACHES
        assert known_present, f"None of the known startup caches appear in status. Got: {sorted(present)}"

        print_info(f"registered caches: {sorted(present)}")
        print_success(f"Status readable by any authenticated user, known caches present: {sorted(known_present)}")


# ============================================================================
# CAPI-003..005: POST /settings/cache/clear/{name}
# ============================================================================


class TestCacheClearByName:
    """Tests for POST /settings/cache/clear/{name}."""

    @pytest.mark.asyncio
    async def test_clear_by_name_non_admin_403(self, test_server):
        """CAPI-003: Non-admin → POST /settings/cache/clear/{name} → 403.

        Uses a bogus name: the admin check runs before the lookup, and even a
        broken check would clear nothing real.
        """
        print_section("CAPI-003: POST /settings/cache/clear/{name} — non-admin → 403")

        async with httpx.AsyncClient() as client:
            await _get_normal_session(client)
            resp = await client.post(f"{API_BASE}/settings/cache/clear/{BOGUS_CACHE_NAME}", timeout=TIMEOUT)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print_success("Non-admin correctly rejected with 403")

    @pytest.mark.asyncio
    async def test_clear_by_name_admin_200(self, test_server):
        """CAPI-004: Admin → clear a registered cache → 200, cleared_count == 1.

        The target is chosen from the server's own status listing (caches
        register lazily): prefer a cheap-to-repopulate one, else take whatever
        the registry declares.
        """
        print_section("CAPI-004: POST /settings/cache/clear/{name} — admin")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)

            by_name = await _status_by_name(client)
            assert by_name, "Status returned no registered caches — cannot pick a clear target"

            target = next((name for name in CLEAR_PREFERENCE if name in by_name), None) or next(iter(by_name))
            print_info(f"clearing cache: {target} (size before: {by_name[target]['current_size']})")

            resp = await client.post(f"{API_BASE}/settings/cache/clear/{target}", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["cleared_count"] == 1, f"clearing one cache must report cleared_count == 1, got {data['cleared_count']}"
        assert data["name"] == target, f"Response name must echo the cleared cache, got {data['name']!r}"
        assert data["message"], "Response must carry a human-readable message"
        print_success(f"Admin cleared '{target}', cleared_count == 1")

    @pytest.mark.asyncio
    async def test_clear_by_name_admin_unknown_404(self, test_server):
        """CAPI-005: Admin → clear an unknown cache name → 404."""
        print_section("CAPI-005: POST /settings/cache/clear/{name} — unknown name → 404")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.post(f"{API_BASE}/settings/cache/clear/{BOGUS_CACHE_NAME}", timeout=TIMEOUT)

        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"
        print_success("Unknown cache name correctly rejected with 404")


# ============================================================================
# CAPI-006/007: POST /settings/cache/clear-all
# ============================================================================


class TestCacheClearAll:
    """Tests for POST /settings/cache/clear-all."""

    @pytest.mark.asyncio
    async def test_clear_all_non_admin_403(self, test_server):
        """CAPI-006: Non-admin → POST /settings/cache/clear-all → 403."""
        print_section("CAPI-006: POST /settings/cache/clear-all — non-admin → 403")

        async with httpx.AsyncClient() as client:
            await _get_normal_session(client)
            resp = await client.post(f"{API_BASE}/settings/cache/clear-all", timeout=TIMEOUT)

        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
        print_success("Non-admin correctly rejected with 403")

    @pytest.mark.asyncio
    async def test_clear_all_admin_200(self, test_server):
        """CAPI-007: Admin → clear-all → 200, cleared_count >= 1, name is null."""
        print_section("CAPI-007: POST /settings/cache/clear-all — admin")

        async with httpx.AsyncClient() as client:
            await _get_admin_session(client)
            resp = await client.post(f"{API_BASE}/settings/cache/clear-all", timeout=TIMEOUT)

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["cleared_count"] >= 1, f"At least one cache is registered at startup, got cleared_count == {data['cleared_count']}"
        assert data["name"] is None, f"clear-all must report name == null, got {data['name']!r}"
        assert data["message"], "Response must carry a human-readable message"
        print_success(f"Admin cleared all caches ({data['cleared_count']})")


# ============================================================================
# CAPI-008: functional — populate, clear, verify empty
# ============================================================================


class TestCacheClearFunctional:
    """Functional test: a cleared cache is observably empty afterwards."""

    @pytest.mark.asyncio
    async def test_clear_empties_populated_cache(self, test_server):
        """CAPI-008: upload populates upload_metadata → clear → status reads size 0.

        Sequence: baseline clear (size 0, a state this test creates) → upload one
        small file (save_upload caches its metadata: exactly +1) → clear by name
        → the entry is still listed (clear does not deregister) with size 0.
        """
        print_section("CAPI-008: clear/{name} empties a populated cache")

        file_id: Optional[str] = None
        async with httpx.AsyncClient() as user_client, httpx.AsyncClient() as admin_client:
            await _get_normal_session(user_client)
            await _get_admin_session(admin_client)

            try:
                # Baseline: clear so the count below is one this test owns.
                baseline = await admin_client.post(f"{API_BASE}/settings/cache/clear/upload_metadata", timeout=TIMEOUT)
                assert baseline.status_code == 200, f"Baseline clear failed: {baseline.status_code}: {baseline.text}"
                before = await _status_by_name(user_client)
                assert before["upload_metadata"]["current_size"] == 0, f"Baseline clear must leave upload_metadata empty, got {before['upload_metadata']['current_size']}"

                # Populate through a real call: save_upload caches the metadata sidecar.
                files = {"file": ("capi_cache_probe.txt", BytesIO(b"cache admin probe"), "text/plain")}
                upload_resp = await user_client.post(f"{API_BASE}/uploads", files=files, timeout=TIMEOUT)
                assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.status_code}: {upload_resp.text}"
                file_id = upload_resp.json()["file"]["id"]

                populated = await _status_by_name(user_client)
                assert populated["upload_metadata"]["current_size"] == 1, f"One upload after a clear must read size 1, got {populated['upload_metadata']['current_size']}"
                print_info("upload_metadata populated: size 1")

                # Clear through the endpoint under test.
                clear_resp = await admin_client.post(f"{API_BASE}/settings/cache/clear/upload_metadata", timeout=TIMEOUT)
                assert clear_resp.status_code == 200, f"Expected 200, got {clear_resp.status_code}: {clear_resp.text}"
                assert clear_resp.json()["cleared_count"] == 1

                # The cache stays registered (clear does not deregister) with size 0.
                after = await _status_by_name(user_client)
                assert "upload_metadata" in after, "upload_metadata must still be listed after a clear"
                assert after["upload_metadata"]["current_size"] == 0, f"Cleared cache must read size 0, got {after['upload_metadata']['current_size']}"
                print_success("Populated cache observably empty after clear")

            finally:
                if file_id:
                    await user_client.delete(f"{API_BASE}/uploads/{file_id}", timeout=TIMEOUT)
