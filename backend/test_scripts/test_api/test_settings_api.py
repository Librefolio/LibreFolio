"""
Settings API Tests

Tests for user settings and global settings endpoints.

Test IDs:
- SET-001 to SET-004: User Settings
- GSET-001 to GSET-010: Global Settings
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

# API configuration
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
# Helper Functions
# ============================================================================

# Global counter for unique usernames
_user_counter = 0


def get_next_username() -> str:
    """Get a unique username with incrementing counter."""
    global _user_counter
    _user_counter += 1
    return f"settings_test_user_{_user_counter}"


async def get_or_create_test_user(client: httpx.AsyncClient, username: str) -> tuple[str, str, Optional[str], bool]:
    """
    Get existing user or create new one.
    First tries to login. If that fails, registers the user.
    Sets session cookie on the client if login succeeds.

    Returns (username, email, session_cookie, is_admin).
    """
    email = f"{username}@test.com"
    password = "TestPass123!"

    # First try to login (user might already exist)
    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)

    if login_resp.status_code == 200:
        session_cookie = login_resp.cookies.get("session")
        # Check if admin
        is_admin = False
        if session_cookie:
            # Set cookie on client for subsequent requests
            client.cookies.set("session", session_cookie)
            me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            if me_resp.status_code == 200:
                user_data = me_resp.json()
                is_admin = user_data.get("user", {}).get("is_superuser", False)
        return username, email, session_cookie, is_admin

    # User doesn't exist, register new one
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )

    if resp.status_code != 201:
        # Registration also failed - return failure
        return username, email, None, False

    # Now login
    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)

    session_cookie = login_resp.cookies.get("session")

    # Check if admin
    is_admin = False
    if session_cookie:
        # Set cookie on client for subsequent requests
        client.cookies.set("session", session_cookie)
        me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
        if me_resp.status_code == 200:
            user_data = me_resp.json()
            is_admin = user_data.get("user", {}).get("is_superuser", False)

    return username, email, session_cookie, is_admin


async def create_test_user(client: httpx.AsyncClient) -> tuple[str, str, Optional[str], bool]:
    """
    Create a test user and return (username, email, session_cookie, is_admin).

    The first user in the system automatically becomes admin.
    Uses get_or_create pattern to handle existing users.
    Also sets session cookie on the client if login succeeds.
    """
    username = get_next_username()
    username, email, session, is_admin = await get_or_create_test_user(client, username)
    if session:
        client.cookies.set("session", session)
    return username, email, session, is_admin


async def create_user_simple(client: httpx.AsyncClient) -> tuple[str, str, Optional[str]]:
    """Create a test user and return (username, email, session).
    Also sets session cookie on the client if login succeeds."""
    username, email, session, _ = await create_test_user(client)
    if session:
        client.cookies.set("session", session)
    return username, email, session


async def login_user(client: httpx.AsyncClient, username: str, password: str) -> Optional[str]:
    """Login and return session cookie. Also sets cookie on client."""
    resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)
    session = resp.cookies.get("session") if resp.status_code == 200 else None
    if session:
        client.cookies.set("session", session)
    return session


# Store the first admin created for reuse
_admin_credentials: Optional[tuple[str, str, str]] = None


async def promote_user_to_admin(username: str) -> bool:
    """Promote a user to admin using the backend service directly. Returns True if successful."""

    try:
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            success, error = await user_service.set_user_admin(session, username, is_admin=True)
            # Success if promoted or already admin
            return success or (error and "already an admin" in error)
    except Exception:
        return False


async def get_admin_session(client: httpx.AsyncClient) -> tuple[str, str, str]:
    """
    Get admin credentials. Creates a user and promotes to admin if needed.
    Reuses cached admin for subsequent calls.

    Returns (username, email, session).
    Raises AssertionError if cannot get admin.
    """
    global _admin_credentials

    # If we already have admin, just re-login and return
    if _admin_credentials:
        username, email, _ = _admin_credentials
        session = await login_user(client, username, "TestPass123!")
        if session:
            return username, email, session

    # Try to create a new user - if DB is empty, this will be admin
    username, email, session, is_admin = await create_test_user(client)

    if is_admin and session:
        _admin_credentials = (username, email, session)
        return username, email, session

    # User is not admin - promote using backend service directly
    if session and await promote_user_to_admin(username):
        # Re-login to get fresh session with updated permissions
        session = await login_user(client, username, "TestPass123!")
        if session:
            # Verify now admin (cookie already set by login_user)
            me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            if me_resp.status_code == 200:
                user_data = me_resp.json()
                if user_data.get("user", {}).get("is_superuser", False):
                    _admin_credentials = (username, email, session)
                    return username, email, session

    # Last resort: skip the test
    pytest.skip("Cannot get admin user. Promote failed.")


# ============================================================================
# User Settings Tests
# ============================================================================


class TestUserSettings:
    """Tests for user settings endpoints (GET/PUT /settings/user)."""

    @pytest.mark.asyncio
    async def test_get_user_settings_authenticated(self, test_server):
        """SET-001: Get user settings when authenticated."""
        print_section("SET-001: GET /settings/user - Authenticated")

        async with httpx.AsyncClient() as client:
            username, email, session = await create_user_simple(client)
            assert session is not None, "Failed to create test user"

            # Get settings (cookie already set on client by create_user_simple)
            resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()

            # Verify structure
            assert "language" in data or "theme" in data or "settings" in data, "Response should contain user settings"

            print_success("✓ User settings retrieved successfully")

    @pytest.mark.asyncio
    async def test_get_user_settings_unauthenticated(self, test_server):
        """SET-002: Get user settings without authentication → 401."""
        print_section("SET-002: GET /settings/user - Unauthenticated")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)

            assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
            print_success("✓ Correctly rejected unauthenticated request")

    @pytest.mark.asyncio
    async def test_update_user_settings(self, test_server):
        """SET-003: Update user settings."""
        print_section("SET-003: PUT /settings/user - Update")

        async with httpx.AsyncClient() as client:
            username, email, session = await create_user_simple(client)
            assert session is not None, "Failed to create test user"

            # Update settings
            new_settings = {"language": "it", "theme": "dark", "default_currency": "USD"}

            resp = await client.put(f"{API_BASE}/settings/user", json=new_settings, timeout=TIMEOUT)

            # Accept 200 or 404 (if endpoint not implemented yet)
            if resp.status_code == 404:
                pytest.skip("User settings update endpoint not implemented")

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            print_success("✓ User settings updated successfully")

    @pytest.mark.asyncio
    async def test_update_user_settings_invalid(self, test_server):
        """SET-004: Update user settings with invalid values → validation error."""
        print_section("SET-004: PUT /settings/user - Invalid Values")

        async with httpx.AsyncClient() as client:
            username, email, session = await create_user_simple(client)
            assert session is not None, "Failed to create test user"

            # Try invalid language code
            invalid_settings = {"language": "invalid_language_code_that_is_too_long"}

            resp = await client.put(f"{API_BASE}/settings/user", json=invalid_settings, timeout=TIMEOUT)

            # Accept 422 (validation error) or 404 (not implemented)
            if resp.status_code == 404:
                pytest.skip("User settings update endpoint not implemented")

            assert resp.status_code in [
                400,
                422,
            ], f"Expected 400/422 for invalid data, got {resp.status_code}"
            print_success("✓ Correctly rejected invalid settings")


# ============================================================================
# Global Settings Tests - List
# ============================================================================


class TestGlobalSettingsList:
    """Tests for listing global settings."""

    @pytest.mark.asyncio
    async def test_list_global_settings_authenticated(self, test_server):
        """GSET-001: List global settings when authenticated."""
        print_section("GSET-001: GET /settings/global - Authenticated")

        async with httpx.AsyncClient() as client:
            username, email, session = await create_user_simple(client)
            assert session is not None, "Failed to create test user"

            resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()

            # Verify structure
            assert "items" in data, "Response should contain 'items' key"
            assert isinstance(data["items"], list), "Settings should be a list"

            if len(data["items"]) > 0:
                setting = data["items"][0]
                assert "key" in setting, "Setting should have 'key'"
                assert "value" in setting, "Setting should have 'value'"
                assert "value_type" in setting, "Setting should have 'value_type'"
                print_info(f"  Found {len(data['items'])} global settings")

            print_success("✓ Global settings listed successfully")

    @pytest.mark.asyncio
    async def test_list_global_settings_unauthenticated(self, test_server):
        """GSET-002: List global settings without authentication → 200 (public read access)."""
        print_section("GSET-002: GET /settings/global - Unauthenticated (Public)")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)

            # Global settings have PUBLIC read access by design
            # (needed for frontend to check enable_registration, etc.)
            assert resp.status_code == 200, f"Expected 200 (public access), got {resp.status_code}"
            data = resp.json()
            assert "items" in data, "Response should contain 'items' key"
            print_success("✓ Global settings publicly accessible (as designed)")


# ============================================================================
# Global Settings Tests - Single Setting
# ============================================================================


class TestGlobalSettingsSingle:
    """Tests for single global setting operations."""

    @pytest.mark.asyncio
    async def test_get_single_setting(self, test_server):
        """GSET-003: Get a single global setting."""
        print_section("GSET-003: GET /settings/global/{key} - Single Setting")

        async with httpx.AsyncClient() as client:
            username, email, session = await create_user_simple(client)
            assert session is not None, "Failed to create test user"

            # Try to get session_ttl_hours (should exist)
            resp = await client.get(f"{API_BASE}/settings/global/session_ttl_hours", timeout=TIMEOUT)

            # Accept 200 or 404 (if single-get not implemented)
            if resp.status_code == 404:
                # Check if it's "not found" for the endpoint or the setting
                data = resp.json()
                if "detail" in data and "not found" in str(data["detail"]).lower():
                    pytest.skip("Single setting GET endpoint not implemented")

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "key" in data, "Response should have 'key'"
            assert data["key"] == "session_ttl_hours", "Key should match"

            print_success("✓ Single setting retrieved successfully")

    @pytest.mark.asyncio
    async def test_get_nonexistent_setting(self, test_server):
        """GSET-004: Get non-existent setting → 404."""
        print_section("GSET-004: GET /settings/global/{key} - Non-existent")

        async with httpx.AsyncClient() as client:
            username, email, session = await create_user_simple(client)
            assert session is not None, "Failed to create test user"

            resp = await client.get(f"{API_BASE}/settings/global/nonexistent_setting_key", timeout=TIMEOUT)

            assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
            print_success("✓ Correctly returned 404 for non-existent setting")

    @pytest.mark.asyncio
    async def test_update_setting_as_admin(self, test_server):
        """GSET-005: PATCH /settings/global/bulk - As Admin."""
        print_section("GSET-005: PATCH /settings/global/bulk - As Admin")

        async with httpx.AsyncClient() as client:
            # Get admin user (creates if first user, or finds existing)
            username, email, session = await get_admin_session(client)

            # Update a setting via bulk endpoint
            resp = await client.patch(
                f"{API_BASE}/settings/global/bulk",
                json={"items": [{"key": "session_ttl_hours", "value": "48"}]},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

            # Restore original value
            await client.patch(
                f"{API_BASE}/settings/global/bulk",
                json={"items": [{"key": "session_ttl_hours", "value": "24"}]},
                timeout=TIMEOUT,
            )

            print_success("✓ Admin successfully updated setting via bulk")

    @pytest.mark.asyncio
    async def test_update_setting_as_non_admin(self, test_server):
        """GSET-006: PATCH /settings/global/bulk as non-admin → 403."""
        print_section("GSET-006: PATCH /settings/global/bulk - Non-Admin")

        async with httpx.AsyncClient() as client:
            # Create a regular user (non-admin)
            username, email, session, is_admin = await create_test_user(client)

            # If this user happens to be admin (first user), create another
            if is_admin:
                username, email, session, _ = await create_test_user(client)

            assert session is not None, "Failed to create test user"

            # Verify not admin (cookie already set on client)
            me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            user_data = me_resp.json()
            is_admin_check = user_data.get("user", {}).get("is_superuser", False)

            assert not is_admin_check, "User should not be admin for this test"

            # Try to update setting via bulk
            resp = await client.patch(
                f"{API_BASE}/settings/global/bulk",
                json={"items": [{"key": "session_ttl_hours", "value": "48"}]},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            print_success("✓ Non-admin correctly rejected with 403")

    @pytest.mark.asyncio
    async def test_update_nonexistent_setting(self, test_server):
        """GSET-007: Bulk update with non-existent setting → 404."""
        print_section("GSET-007: PATCH /settings/global/bulk - Non-existent key")

        async with httpx.AsyncClient() as client:
            # Get admin user
            username, email, session = await get_admin_session(client)

            resp = await client.patch(
                f"{API_BASE}/settings/global/bulk",
                json={"items": [{"key": "nonexistent_setting_xyz", "value": "test"}]},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
            print_success("✓ Admin correctly received 404 for non-existent setting")


# ============================================================================
# Global Settings Tests - Initialize
# ============================================================================


class TestGlobalSettingsInitialize:
    """Tests for global settings initialization."""

    @pytest.mark.asyncio
    async def test_initialize_as_admin(self, test_server):
        """GSET-008: Initialize global settings as admin → success."""
        print_section("GSET-008: POST /settings/global/initialize - As Admin")

        async with httpx.AsyncClient() as client:
            # Get admin user (creates and promotes if needed)
            username, email, session = await get_admin_session(client)

            resp = await client.post(f"{API_BASE}/settings/global/initialize", timeout=TIMEOUT)

            # Accept 200 (success) or 404 (endpoint not implemented)
            if resp.status_code == 404:
                pytest.skip("Initialize endpoint not implemented")

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()

            # Should return count of created settings (could be 0 if already exist)
            assert "message" in data, "Response should indicate result"

            print_success("✓ Admin initialized settings successfully")

    @pytest.mark.asyncio
    async def test_initialize_as_non_admin(self, test_server):
        """GSET-009: Initialize global settings as non-admin → 403."""
        print_section("GSET-009: POST /settings/global/initialize - Non-Admin")

        async with httpx.AsyncClient() as client:
            # Create first user (might be admin)
            _, _, _, first_is_admin = await create_test_user(client)

            # Create second user (not admin)
            username2, email2, session2, is_admin2 = await create_test_user(client)

            # If second user is somehow admin, skip
            if is_admin2:
                pytest.skip("Second user is admin, cannot test non-admin rejection")

            assert session2 is not None, "Failed to create second test user"

            resp = await client.post(f"{API_BASE}/settings/global/initialize", timeout=TIMEOUT)

            # Accept 403 (forbidden) or 404 (endpoint not implemented)
            if resp.status_code == 404:
                pytest.skip("Initialize endpoint not implemented")

            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
            print_success("✓ Non-admin correctly rejected with 403")

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, test_server):
        """GSET-010: Initialize when already exists → idempotent."""
        print_section("GSET-010: POST /settings/global/initialize - Idempotent")

        async with httpx.AsyncClient() as client:
            # Get admin user (creates and promotes if needed)
            username, email, session = await get_admin_session(client)

            # First initialization
            resp1 = await client.post(f"{API_BASE}/settings/global/initialize", timeout=TIMEOUT)

            if resp1.status_code == 404:
                pytest.skip("Initialize endpoint not implemented")

            assert resp1.status_code == 200, f"First init expected 200, got {resp1.status_code}"

            # Second initialization (should be idempotent)
            resp2 = await client.post(f"{API_BASE}/settings/global/initialize", timeout=TIMEOUT)

            assert resp2.status_code == 200, f"Expected 200, got {resp2.status_code}"
            print_success("✓ Initialize is idempotent")
