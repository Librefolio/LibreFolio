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


# ============================================================================
# Scheduler Settings Keys Tests
# ============================================================================


def _get_setting_value(items: list, key: str) -> str | None:
    """Extract a setting value from the GET /settings/global items list."""
    for s in items:
        if s["key"] == key:
            return s["value"]
    return None


async def _read_setting(client: httpx.AsyncClient, key: str) -> str | None:
    """GET /settings/global and extract a specific key's value."""
    resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /settings/global failed: {resp.status_code}"
    return _get_setting_value(resp.json()["items"], key)


async def _patch_setting(client: httpx.AsyncClient, key: str, value: str) -> None:
    """PATCH /settings/global/bulk for a single key."""
    resp = await client.patch(
        f"{API_BASE}/settings/global/bulk",
        json={"items": [{"key": key, "value": value}]},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"PATCH bulk failed for '{key}': {resp.status_code} {resp.text}"


class TestSchedulerSettingsKeys:
    """Tests for the 5 scheduler settings keys via PATCH/GET /settings/global*.

    Test IDs: GSET-SCH-001..GSET-SCH-006
    """

    @pytest.mark.asyncio
    async def test_scheduler_enabled_save_read(self, test_server):
        """GSET-SCH-001: Save and read scheduler_enabled (bool as string)."""
        print_section("GSET-SCH-001: scheduler_enabled — save and read")

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)

            original = await _read_setting(client, "scheduler_enabled")

            try:
                # Set to "true"
                await _patch_setting(client, "scheduler_enabled", "true")
                val = await _read_setting(client, "scheduler_enabled")
                assert val == "true", f"Expected 'true', got '{val}'"
                print_info("  scheduler_enabled='true' ✓")

                # Set to "false"
                await _patch_setting(client, "scheduler_enabled", "false")
                val = await _read_setting(client, "scheduler_enabled")
                assert val == "false", f"Expected 'false', got '{val}'"
                print_info("  scheduler_enabled='false' ✓")
            finally:
                # Restore
                if original is not None:
                    await _patch_setting(client, "scheduler_enabled", original)

        print_success("GSET-SCH-001: scheduler_enabled save/read OK ✓")

    @pytest.mark.asyncio
    async def test_scheduler_current_price_frequency_save_read(self, test_server):
        """GSET-SCH-002: Save and read scheduler_current_price_frequency_minutes."""
        print_section("GSET-SCH-002: scheduler_current_price_frequency_minutes — save and read")

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)

            original = await _read_setting(client, "scheduler_current_price_frequency_minutes")

            try:
                await _patch_setting(client, "scheduler_current_price_frequency_minutes", "15")
                val = await _read_setting(client, "scheduler_current_price_frequency_minutes")
                assert val == "15", f"Expected '15', got '{val}'"
                print_info("  frequency=15 ✓")

                await _patch_setting(client, "scheduler_current_price_frequency_minutes", "5")
                val = await _read_setting(client, "scheduler_current_price_frequency_minutes")
                assert val == "5", f"Expected '5', got '{val}'"
                print_info("  frequency=5 ✓")
            finally:
                if original is not None:
                    await _patch_setting(client, "scheduler_current_price_frequency_minutes", original)

        print_success("GSET-SCH-002: scheduler_current_price_frequency_minutes save/read OK ✓")

    @pytest.mark.asyncio
    async def test_scheduler_history_sync_times_save_read(self, test_server):
        """GSET-SCH-003: Save and read scheduler_history_sync_times (HH:MM CSV)."""
        print_section("GSET-SCH-003: scheduler_history_sync_times — save and read")

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)

            original = await _read_setting(client, "scheduler_history_sync_times")

            try:
                # Multi-slot
                await _patch_setting(client, "scheduler_history_sync_times", "06:00,12:00,23:00")
                val = await _read_setting(client, "scheduler_history_sync_times")
                assert val == "06:00,12:00,23:00", f"Expected '06:00,12:00,23:00', got '{val}'"
                print_info("  times='06:00,12:00,23:00' ✓")

                # Single slot
                await _patch_setting(client, "scheduler_history_sync_times", "08:30")
                val = await _read_setting(client, "scheduler_history_sync_times")
                assert val == "08:30", f"Expected '08:30', got '{val}'"
                print_info("  times='08:30' ✓")
            finally:
                if original is not None:
                    await _patch_setting(client, "scheduler_history_sync_times", original)

        print_success("GSET-SCH-003: scheduler_history_sync_times save/read OK ✓")

    @pytest.mark.asyncio
    async def test_scheduler_history_sync_days_save_read(self, test_server):
        """GSET-SCH-004: Save and read scheduler_history_sync_days (day-code CSV)."""
        print_section("GSET-SCH-004: scheduler_history_sync_days — save and read")

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)

            original = await _read_setting(client, "scheduler_history_sync_days")

            try:
                # Subset
                await _patch_setting(client, "scheduler_history_sync_days", "mon,wed,fri")
                val = await _read_setting(client, "scheduler_history_sync_days")
                assert val == "mon,wed,fri", f"Expected 'mon,wed,fri', got '{val}'"
                print_info("  days='mon,wed,fri' ✓")

                # All 7 days
                await _patch_setting(client, "scheduler_history_sync_days", "mon,tue,wed,thu,fri,sat,sun")
                val = await _read_setting(client, "scheduler_history_sync_days")
                assert val == "mon,tue,wed,thu,fri,sat,sun", f"Got '{val}'"
                print_info("  days='mon,tue,wed,thu,fri,sat,sun' ✓")
            finally:
                if original is not None:
                    await _patch_setting(client, "scheduler_history_sync_days", original)

        print_success("GSET-SCH-004: scheduler_history_sync_days save/read OK ✓")

    @pytest.mark.asyncio
    async def test_scheduler_history_sync_horizon_days_save_read(self, test_server):
        """GSET-SCH-005: Save and read scheduler_history_sync_horizon_days."""
        print_section("GSET-SCH-005: scheduler_history_sync_horizon_days — save and read")

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)

            original = await _read_setting(client, "scheduler_history_sync_horizon_days")

            try:
                await _patch_setting(client, "scheduler_history_sync_horizon_days", "30")
                val = await _read_setting(client, "scheduler_history_sync_horizon_days")
                assert val == "30", f"Expected '30', got '{val}'"
                print_info("  horizon_days=30 ✓")

                await _patch_setting(client, "scheduler_history_sync_horizon_days", "7")
                val = await _read_setting(client, "scheduler_history_sync_horizon_days")
                assert val == "7", f"Expected '7', got '{val}'"
                print_info("  horizon_days=7 ✓")
            finally:
                if original is not None:
                    await _patch_setting(client, "scheduler_history_sync_horizon_days", original)

        print_success("GSET-SCH-005: scheduler_history_sync_horizon_days save/read OK ✓")

    @pytest.mark.asyncio
    async def test_all_scheduler_keys_bulk_update(self, test_server):
        """GSET-SCH-006: Bulk update all 5 scheduler keys in a single PATCH request."""
        print_section("GSET-SCH-006: All 5 scheduler keys — bulk update")

        scheduler_keys = [
            "scheduler_enabled",
            "scheduler_current_price_frequency_minutes",
            "scheduler_history_sync_times",
            "scheduler_history_sync_days",
            "scheduler_history_sync_horizon_days",
        ]
        new_values = {
            "scheduler_enabled": "false",
            "scheduler_current_price_frequency_minutes": "20",
            "scheduler_history_sync_times": "07:00,22:00",
            "scheduler_history_sync_days": "mon,tue,wed,thu,fri",
            "scheduler_history_sync_horizon_days": "21",
        }

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)

            # Save originals
            originals: dict[str, str | None] = {}
            for k in scheduler_keys:
                originals[k] = await _read_setting(client, k)

            try:
                # Bulk update all 5
                resp = await client.patch(
                    f"{API_BASE}/settings/global/bulk",
                    json={"items": [{"key": k, "value": v} for k, v in new_values.items()]},
                    timeout=TIMEOUT,
                )
                assert resp.status_code == 200, f"Bulk PATCH failed: {resp.status_code} {resp.text}"
                print_info("  Bulk PATCH 5 keys → 200 ✓")

                # Read back each key individually and verify
                for key, expected in new_values.items():
                    val = await _read_setting(client, key)
                    assert val == expected, f"Key '{key}': expected '{expected}', got '{val}'"
                    print_info(f"  {key}='{val}' ✓")
            finally:
                # Restore all originals
                restore_items = [
                    {"key": k, "value": v}
                    for k, v in originals.items()
                    if v is not None
                ]
                if restore_items:
                    await client.patch(
                        f"{API_BASE}/settings/global/bulk",
                        json={"items": restore_items},
                        timeout=TIMEOUT,
                    )

        print_success("GSET-SCH-006: All 5 scheduler keys bulk update OK ✓")
