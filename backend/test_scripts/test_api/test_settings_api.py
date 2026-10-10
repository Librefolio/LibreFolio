"""
Settings API Tests

Tests for user settings and global settings endpoints.

Test IDs:
- SET-001 to SET-004: User Settings
- GSET-001 to GSET-010: Global Settings
"""

import uuid
import zoneinfo
from collections.abc import Callable
from typing import Optional

import httpx
import pytest
import pytest_asyncio
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
    async def test_update_user_settings_creates_with_all_fields(self, test_server):
        """SET-003b: PUT /settings/user creates settings with provided values."""
        print_section("SET-003b: PUT /settings/user - Create with all fields")

        async with httpx.AsyncClient() as client:
            from uuid import uuid4  # noqa: PLC0415 — test-only local import

            username, email, session, _ = await get_or_create_test_user(client, f"settings_create_{uuid4().hex[:8]}")
            assert session is not None, "Failed to create test user"

            payload = {
                "language": "fr",
                "base_currency": "USD",
                "theme": "dark",
                "avatar_url": "https://example.com/settings-avatar.png",
            }

            resp = await client.put(f"{API_BASE}/settings/user", json=payload, timeout=TIMEOUT)

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            assert resp.json() == payload

            get_resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert get_resp.status_code == 200
            assert get_resp.json() == payload

            print_success("✓ User settings created with expected values")

    @pytest.mark.asyncio
    async def test_update_user_settings_updates_existing_record(self, test_server):
        """SET-003c: PUT /settings/user updates existing settings and preserves omitted fields."""
        print_section("SET-003c: PUT /settings/user - Update existing record")

        async with httpx.AsyncClient() as client:
            from uuid import uuid4  # noqa: PLC0415 — test-only local import

            username, email, session, _ = await get_or_create_test_user(client, f"settings_update_{uuid4().hex[:8]}")
            assert session is not None, "Failed to create test user"

            initial_resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert initial_resp.status_code == 200, f"Expected 200, got {initial_resp.status_code}"

            resp = await client.put(
                f"{API_BASE}/settings/user",
                json={"theme": "auto", "avatar_url": "https://example.com/updated-avatar.png"},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            assert resp.json() == {
                "language": "en",
                "base_currency": "EUR",
                "theme": "auto",
                "avatar_url": "https://example.com/updated-avatar.png",
            }

            print_success("✓ Existing user settings updated and partial fields preserved")

    @pytest.mark.asyncio
    async def test_update_user_settings_avatar_url_null_clears_it(self, test_server):
        """SET-003d: PUT /settings/user with avatar_url: null clears a previously set avatar."""
        print_section("SET-003d: PUT /settings/user - Clear avatar_url with null")

        async with httpx.AsyncClient() as client:
            from uuid import uuid4  # noqa: PLC0415 — test-only local import

            username, email, session, _ = await get_or_create_test_user(client, f"settings_avatar_clear_{uuid4().hex[:8]}")
            assert session is not None, "Failed to create test user"

            # First set a non-null avatar URL, alongside other settings we can verify are untouched later.
            set_payload = {
                "language": "fr",
                "base_currency": "USD",
                "theme": "dark",
                "avatar_url": "https://example.com/settings-avatar-to-clear.png",
            }
            set_resp = await client.put(f"{API_BASE}/settings/user", json=set_payload, timeout=TIMEOUT)
            assert set_resp.status_code == 200, f"Expected 200, got {set_resp.status_code}: {set_resp.text}"
            assert set_resp.json() == set_payload

            # Now clear only avatar_url via explicit null.
            clear_resp = await client.put(
                f"{API_BASE}/settings/user",
                json={"avatar_url": None},
                timeout=TIMEOUT,
            )

            assert clear_resp.status_code == 200, f"Expected 200, got {clear_resp.status_code}: {clear_resp.text}"
            expected = {
                "language": "fr",
                "base_currency": "USD",
                "theme": "dark",
                "avatar_url": None,
            }
            assert clear_resp.json() == expected, f"Expected {expected}, got {clear_resp.json()}"

            # A subsequent GET must reflect the same cleared state.
            get_resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
            assert get_resp.json() == expected, f"Expected {expected}, got {get_resp.json()}"

            print_success("✓ avatar_url cleared to null while other settings were preserved")

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
# Onboarding Progress Tests (Workstream J foundation)
# ============================================================================

ONBOARDING_FLOWS = (
    "welcome",
    "intro_tour",
    "transactions_page_guide",
    "transaction_create_guide",
    "transaction_bulk_guide",
    "import_guide",
    "broker_page_guide",
    "broker_guide",
    "broker_detail_guide",
    "fx_page_guide",
    "fx_guide",
    "fx_detail_guide",
    "asset_page_guide",
    "asset_guide",
    "asset_detail_guide",
)
REMOVED_ONBOARDING_DRAFT_FLOWS = {
    "transaction_bulk_validation_guide",
    "transaction_bulk_selection_guide",
    "transaction_bulk_save_guide",
}
ONBOARDING_STEPS = {
    "transaction_bulk_guide": (
        "transaction.bulk.workspace",
        "transaction.bulk.validation",
        "transaction.bulk.selection",
        "transaction.bulk.save",
    ),
    "import_guide": (
        "import.upload",
        "import.select",
        "import.analyze",
        "import.assets",
        "import.fix",
        "import.duplicates",
        "import.review",
        "import.gapFix",
        "import.bulk",
    ),
}
ONBOARDING_ITEM_KEYS = {
    "flow",
    "status",
    "version",
    "current_version",
    "update_available",
    "created_at",
    "updated_at",
}
ONBOARDING_STEP_ITEM_KEYS = {
    "step_id",
    "status",
    "version",
    "current_version",
    "update_available",
    "created_at",
    "updated_at",
}
_ONBOARDING_USERS_TO_DELETE: set[str] = set()


async def _get_onboarding_response(client: httpx.AsyncClient) -> dict:
    """GET the final onboarding contract."""
    resp = await client.get(f"{API_BASE}/settings/onboarding", timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


async def _get_onboarding_flows(client: httpx.AsyncClient) -> dict:
    """Index the final onboarding response by flow name."""
    data = await _get_onboarding_response(client)
    flows = {item["flow"]: item for item in data["flows"]}
    assert len(flows) == len(data["flows"]), "Onboarding response must not contain duplicate flow rows"
    return flows


async def _new_onboarding_user(client: httpx.AsyncClient, marker: str) -> str:
    """Register+login a fresh unique user and set the session cookie on client."""
    from uuid import uuid4  # noqa: PLC0415 — test-only local import

    username, _email, session, _is_admin = await get_or_create_test_user(client, f"onb_{marker}_{uuid4().hex[:8]}")
    _ONBOARDING_USERS_TO_DELETE.add(username)
    assert session is not None, "Failed to create test user"
    client.cookies.set("session", session)
    return username


async def _delete_onboarding_user(username: str) -> None:
    """Delete a user created by an onboarding API test and its cascading rows."""
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        user = await user_service.get_user_by_username(session, username)
        if user is not None:
            await session.delete(user)
            await session.commit()
    _ONBOARDING_USERS_TO_DELETE.discard(username)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_owned_onboarding_users():
    """Delete every account created through the onboarding-specific helper."""
    before = set(_ONBOARDING_USERS_TO_DELETE)
    yield
    for username in _ONBOARDING_USERS_TO_DELETE - before:
        await _delete_onboarding_user(username)


class TestOnboardingProgressApi:
    """Tests for final GET and flow/step transition endpoints."""

    @pytest.mark.asyncio
    async def test_get_onboarding_progress_requires_auth(self, test_server):
        """Unauthenticated GET /settings/onboarding -> 401, auth surface unchanged."""
        print_section("ONB-001: GET /settings/onboarding - Unauthenticated")

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/settings/onboarding", timeout=TIMEOUT)
            assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

        print_success("✓ Correctly rejected unauthenticated request")

    @pytest.mark.asyncio
    async def test_get_onboarding_progress_has_exact_flows_and_step_arrays(self, test_server):
        """ONB-002: GET returns the final 15-flow contract and managed steps."""
        print_section("ONB-002: GET /settings/onboarding - Final contract")

        async with httpx.AsyncClient() as client:
            username = await _new_onboarding_user(client, "get")
            try:
                data = await _get_onboarding_response(client)
                flows = {item["flow"]: item for item in data["flows"]}

                assert set(data) == {"flows"}
                assert len(data["flows"]) == 15, f"Final contract must expose exactly 15 flows, got {[item['flow'] for item in data['flows']]}"
                assert tuple(item["flow"] for item in data["flows"]) == ONBOARDING_FLOWS
                assert len(flows) == len(data["flows"]), "Final contract must not contain duplicate flow rows"
                assert set(flows).isdisjoint(REMOVED_ONBOARDING_DRAFT_FLOWS)
                for flow, expected_steps in ONBOARDING_STEPS.items():
                    assert set(flows[flow]) == ONBOARDING_ITEM_KEYS | {"steps"}
                    assert tuple(step["step_id"] for step in flows[flow]["steps"]) == expected_steps
                    assert all(step["status"] == "pending" for step in flows[flow]["steps"])
                    assert all(set(step) == ONBOARDING_STEP_ITEM_KEYS for step in flows[flow]["steps"])
                for flow in set(flows) - set(ONBOARDING_STEPS):
                    assert set(flows[flow]) == ONBOARDING_ITEM_KEYS
                    assert "steps" not in flows[flow]
            finally:
                await _delete_onboarding_user(username)

        print_success("✓ GET exposes the final 15 flows and both ordered step arrays")

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow(self, test_server):
        """ONB-003: POST /settings/onboarding/welcome/complete marks it completed."""
        print_section("ONB-003: POST /settings/onboarding/{flow}/complete")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "complete")
            flows = await _get_onboarding_flows(client)
            version = flows["welcome"]["current_version"]

            resp = await client.post(
                f"{API_BASE}/settings/onboarding/welcome/complete",
                json={"expected_version": version},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            item = resp.json()
            assert item["flow"] == "welcome"
            assert item["status"] == "completed"
            assert set(item) == ONBOARDING_ITEM_KEYS | {"completed_at"}
            assert item["completed_at"] is not None
            assert "skipped_at" not in item
            assert "steps" not in item
            assert item["update_available"] is False

            # Persisted: a fresh GET reflects the same terminal state.
            flows_after = await _get_onboarding_flows(client)
            assert flows_after["welcome"]["status"] == "completed"
            assert flows_after["intro_tour"]["status"] == "pending", "Other flows for this user must be untouched"

        print_success("✓ Onboarding flow completed and persisted")

    @pytest.mark.asyncio
    async def test_skip_onboarding_flow(self, test_server):
        """ONB-004: POST /settings/onboarding/{flow}/skip marks it skipped."""
        print_section("ONB-004: POST /settings/onboarding/{flow}/skip")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "skip")
            flows = await _get_onboarding_flows(client)
            version = flows["import_guide"]["current_version"]

            resp = await client.post(
                f"{API_BASE}/settings/onboarding/import_guide/skip",
                json={"expected_version": version},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            item = resp.json()
            assert item["flow"] == "import_guide"
            assert item["status"] == "skipped"
            assert set(item) == ONBOARDING_ITEM_KEYS | {"skipped_at"}
            assert item["skipped_at"] is not None
            assert "completed_at" not in item
            assert "steps" not in item
            persisted = await _get_onboarding_flows(client)
            assert all(step["status"] == "skipped" for step in persisted["import_guide"]["steps"])

        print_success("✓ Onboarding flow skipped and persisted")

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow_is_idempotent(self, test_server):
        """ONB-005: completing the same flow twice at the same version is a no-op repeat, not an error."""
        print_section("ONB-005: complete/complete - Idempotent repeat")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "complete_idem")
            flows = await _get_onboarding_flows(client)
            version = flows["intro_tour"]["current_version"]
            payload = {"expected_version": version}

            first = await client.post(f"{API_BASE}/settings/onboarding/intro_tour/complete", json=payload, timeout=TIMEOUT)
            second = await client.post(f"{API_BASE}/settings/onboarding/intro_tour/complete", json=payload, timeout=TIMEOUT)

            assert first.status_code == 200
            assert second.status_code == 200
            assert second.json() == first.json(), "Repeating the same completion must return the identical resource"

        print_success("✓ Repeat completion is idempotent")

    @pytest.mark.asyncio
    async def test_step_endpoints_are_idempotent_and_mixed_terminal_steps_complete_flow(self, test_server):
        """ONB-005b: complete/skip mutate only the addressed Import step; the
        aggregate stays pending until all eight are terminal, then completes."""
        print_section("ONB-005b: Import step complete/skip endpoints and aggregate")

        async with httpx.AsyncClient() as client:
            username = await _new_onboarding_user(client, "step_mixed")
            try:
                flows = await _get_onboarding_flows(client)
                version = flows["import_guide"]["current_version"]
                payload = {"expected_version": version}

                first = await client.post(
                    f"{API_BASE}/settings/onboarding/import_guide/steps/import.upload/complete",
                    json=payload,
                    timeout=TIMEOUT,
                )
                repeated = await client.post(
                    f"{API_BASE}/settings/onboarding/import_guide/steps/import.upload/complete",
                    json=payload,
                    timeout=TIMEOUT,
                )
                assert first.status_code == 200, first.text
                assert repeated.status_code == 200, repeated.text
                assert repeated.json() == first.json(), "Repeating a step completion must be idempotent"

                first_item = first.json()
                assert first_item["flow"] == "import_guide"
                assert first_item["status"] == "pending"
                assert set(first_item) == ONBOARDING_ITEM_KEYS | {"steps"}
                assert "steps" in first_item, "Step transitions must return the final flow shape"
                assert tuple(step["step_id"] for step in first_item["steps"]) == ONBOARDING_STEPS["import_guide"]
                first_steps = {step["step_id"]: step for step in first_item["steps"]}
                assert first_steps["import.upload"]["status"] == "completed"
                assert first_steps["import.upload"]["completed_at"] is not None
                assert set(first_steps["import.upload"]) == ONBOARDING_STEP_ITEM_KEYS | {"completed_at"}
                assert all(first_steps[step_id]["status"] == "pending" for step_id in ONBOARDING_STEPS["import_guide"] if step_id != "import.upload")
                assert all(set(first_steps[step_id]) == ONBOARDING_STEP_ITEM_KEYS for step_id in ONBOARDING_STEPS["import_guide"] if step_id != "import.upload")

                item = first_item
                for step_id in ONBOARDING_STEPS["import_guide"]:
                    if step_id == "import.upload":
                        continue
                    skipped = await client.post(
                        f"{API_BASE}/settings/onboarding/import_guide/steps/{step_id}/skip",
                        json=payload,
                        timeout=TIMEOUT,
                    )
                    assert skipped.status_code == 200, skipped.text
                    item = skipped.json()
                    if step_id != "import.bulk":
                        assert item["status"] == "pending"

                assert item["status"] == "completed"
                assert set(item) == ONBOARDING_ITEM_KEYS | {"completed_at", "steps"}
                assert item["completed_at"] is not None
                assert "skipped_at" not in item
                terminal_steps = {step["step_id"]: step for step in item["steps"]}
                assert terminal_steps["import.upload"]["status"] == "completed"
                assert all(terminal_steps[step_id]["status"] == "skipped" for step_id in ONBOARDING_STEPS["import_guide"] if step_id != "import.upload")

                persisted = await _get_onboarding_flows(client)
                assert persisted["import_guide"]["status"] == "completed"
                assert {step["step_id"]: step["status"] for step in persisted["import_guide"]["steps"]} == {step_id: ("completed" if step_id == "import.upload" else "skipped") for step_id in ONBOARDING_STEPS["import_guide"]}
            finally:
                await _delete_onboarding_user(username)

        print_success("✓ Step endpoints are idempotent and aggregate only after every step is terminal")

    @pytest.mark.asyncio
    async def test_all_skipped_bulk_steps_aggregate_to_skipped(self, test_server):
        """ONB-005c: the single Bulk flow is skipped only when all four steps are skipped."""
        print_section("ONB-005c: Bulk all-skipped aggregate")

        async with httpx.AsyncClient() as client:
            username = await _new_onboarding_user(client, "step_all_skipped")
            try:
                flows = await _get_onboarding_flows(client)
                version = flows["transaction_bulk_guide"]["current_version"]
                item = None
                for step_id in ONBOARDING_STEPS["transaction_bulk_guide"]:
                    response = await client.post(
                        f"{API_BASE}/settings/onboarding/transaction_bulk_guide/steps/{step_id}/skip",
                        json={"expected_version": version},
                        timeout=TIMEOUT,
                    )
                    assert response.status_code == 200, response.text
                    item = response.json()
                    if step_id != "transaction.bulk.save":
                        assert item["status"] == "pending"

                assert item is not None
                assert item["status"] == "skipped"
                assert item["skipped_at"] is not None
                assert "completed_at" not in item
                assert {step["step_id"]: step["status"] for step in item["steps"]} == dict.fromkeys(ONBOARDING_STEPS["transaction_bulk_guide"], "skipped")
            finally:
                await _delete_onboarding_user(username)

        print_success("✓ All-skipped Bulk steps aggregate to skipped")

    @pytest.mark.parametrize("action", ("complete", "skip"))
    @pytest.mark.asyncio
    async def test_step_transition_rejects_welcome_settings_without_mutation(self, test_server, action: str):
        """ONB-005d: step transitions strictly reject flow-only welcome settings."""
        print_section(f"ONB-005d: Step {action} rejects welcome_settings without mutation")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, f"step_schema_{action}")
            flow = "import_guide"
            step_id = "import.upload"

            flows_before = await _get_onboarding_flows(client)
            flow_before = flows_before[flow]
            steps_before = {step["step_id"]: step for step in flow_before["steps"]}
            step_before = steps_before[step_id]

            response = await client.post(
                f"{API_BASE}/settings/onboarding/{flow}/steps/{step_id}/{action}",
                json={
                    "expected_version": flow_before["current_version"],
                    "welcome_settings": {
                        "language": "en",
                        "base_currency": "EUR",
                        "avatar_url": None,
                    },
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"

            flows_after = await _get_onboarding_flows(client)
            flow_after = flows_after[flow]
            steps_after = {step["step_id"]: step for step in flow_after["steps"]}
            assert steps_after[step_id] == step_before, f"Rejected step {action} must not mutate the addressed step"
            assert flow_after == flow_before, f"Rejected step {action} must not mutate the owning flow"

        print_success(f"✓ Step {action} strictly rejected welcome_settings without mutation")

    @pytest.mark.asyncio
    async def test_skip_then_explicit_complete_transition_allowed(self, test_server):
        """ONB-006: replay-like skipped→completed explicit transition is allowed and
        clears skipped_at (never both timestamps set)."""
        print_section("ONB-006: skip then explicit complete - Replay-like transition")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "replay")
            flows = await _get_onboarding_flows(client)
            version = flows["welcome"]["current_version"]
            payload = {"expected_version": version}

            skip_resp = await client.post(f"{API_BASE}/settings/onboarding/welcome/skip", json=payload, timeout=TIMEOUT)
            assert skip_resp.status_code == 200
            assert skip_resp.json()["status"] == "skipped"

            complete_resp = await client.post(f"{API_BASE}/settings/onboarding/welcome/complete", json=payload, timeout=TIMEOUT)
            assert complete_resp.status_code == 200
            item = complete_resp.json()
            assert item["status"] == "completed"
            assert item["completed_at"] is not None
            assert "skipped_at" not in item

        print_success("✓ Explicit skip→complete transition applied")

    @pytest.mark.asyncio
    async def test_unknown_flow_returns_validation_error(self, test_server):
        """ONB-007: an unregistered flow name is rejected by path validation, not the service."""
        print_section("ONB-007: POST /settings/onboarding/{unknown}/complete - Validation")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "unknown_flow")

            resp = await client.post(
                f"{API_BASE}/settings/onboarding/not_a_real_flow/complete",
                json={"expected_version": 1},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

        print_success("✓ Unknown flow rejected by validation")

    @pytest.mark.asyncio
    async def test_onboarding_progress_isolated_per_user(self, test_server):
        """ONB-009: completing a flow for one user must not affect another user's progress."""
        print_section("ONB-009: Onboarding progress isolation across users")

        async with httpx.AsyncClient() as client_a, httpx.AsyncClient() as client_b:
            await _new_onboarding_user(client_a, "iso_a")
            await _new_onboarding_user(client_b, "iso_b")

            flows_a = await _get_onboarding_flows(client_a)
            version = flows_a["welcome"]["current_version"]

            resp = await client_a.post(
                f"{API_BASE}/settings/onboarding/welcome/complete",
                json={"expected_version": version},
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200

            flows_b_after = await _get_onboarding_flows(client_b)
            assert flows_b_after["welcome"]["status"] == "pending", "User B's flow must be unaffected by user A"

            flows_a_after = await _get_onboarding_flows(client_a)
            assert flows_a_after["welcome"]["status"] == "completed"

        print_success("✓ Onboarding progress is isolated per user")


class TestOnboardingWelcomeAtomicApi:
    """Tests for the atomic path: POST /settings/onboarding/welcome/complete with welcome_settings."""

    @pytest.mark.asyncio
    async def test_complete_welcome_with_settings_persists_atomically(self, test_server):
        """Completing welcome with welcome_settings must both complete the flow and
        persist the submitted preferences, visible from a follow-up GET /settings/user."""
        print_section("ONB-010: Atomic welcome completion persists preferences")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "atomic")
            flows = await _get_onboarding_flows(client)
            version = flows["welcome"]["current_version"]

            resp = await client.post(
                f"{API_BASE}/settings/onboarding/welcome/complete",
                json={
                    "expected_version": version,
                    "welcome_settings": {
                        "language": "fr",
                        "base_currency": "CHF",
                        "avatar_url": "https://example.com/onb-atomic-avatar.png",
                    },
                },
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            item = resp.json()
            assert item["flow"] == "welcome"
            assert item["status"] == "completed"
            assert item["completed_at"] is not None
            assert "skipped_at" not in item

            settings_resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert settings_resp.status_code == 200
            settings = settings_resp.json()
            assert settings["language"] == "fr"
            assert settings["base_currency"] == "CHF"
            assert settings["avatar_url"] == "https://example.com/onb-atomic-avatar.png"

            flows_after = await _get_onboarding_flows(client)
            assert flows_after["welcome"]["status"] == "completed"
            assert flows_after["intro_tour"]["status"] == "pending", "Other flows for this user must be untouched"

        print_success("✓ Atomic welcome completion persisted both progress and preferences")

    @pytest.mark.asyncio
    async def test_welcome_settings_on_skip_returns_422(self, test_server):
        """welcome_settings is only valid on a welcome *complete*; sending it on skip
        must be rejected with 422, not silently ignored or applied."""
        print_section("ONB-012: welcome_settings on skip - 422")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "atomic_skip")
            flows = await _get_onboarding_flows(client)
            version = flows["welcome"]["current_version"]

            resp = await client.post(
                f"{API_BASE}/settings/onboarding/welcome/skip",
                json={
                    "expected_version": version,
                    "welcome_settings": {
                        "language": "en",
                        "base_currency": "EUR",
                        "avatar_url": None,
                    },
                },
                timeout=TIMEOUT,
            )

            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

            flows_after = await _get_onboarding_flows(client)
            assert flows_after["welcome"]["status"] == "pending", "a rejected skip must not have applied any transition"

        print_success("✓ welcome_settings on skip rejected with 422")

    @pytest.mark.asyncio
    async def test_welcome_settings_on_non_welcome_flow_returns_422(self, test_server):
        """welcome_settings is only valid for the welcome flow; sending it while
        completing a different flow must be rejected with 422."""
        print_section("ONB-013: welcome_settings on non-welcome flow - 422")

        async with httpx.AsyncClient() as client:
            await _new_onboarding_user(client, "atomic_wrong_flow")
            flows = await _get_onboarding_flows(client)
            version = flows["intro_tour"]["current_version"]

            resp = await client.post(
                f"{API_BASE}/settings/onboarding/intro_tour/complete",
                json={
                    "expected_version": version,
                    "welcome_settings": {
                        "language": "en",
                        "base_currency": "EUR",
                        "avatar_url": None,
                    },
                },
                timeout=TIMEOUT,
            )

            assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

            flows_after = await _get_onboarding_flows(client)
            assert flows_after["intro_tour"]["status"] == "pending", "a rejected completion must not have applied"

        print_success("✓ welcome_settings on a non-welcome flow rejected with 422")

    @pytest.mark.asyncio
    async def test_complete_welcome_atomic_isolated_per_user(self, test_server):
        """Completing welcome atomically for one user must not affect another user's
        onboarding progress or settings."""
        print_section("ONB-014: Atomic welcome completion isolation across users")

        async with httpx.AsyncClient() as client_a, httpx.AsyncClient() as client_b:
            await _new_onboarding_user(client_a, "atomic_iso_a")
            await _new_onboarding_user(client_b, "atomic_iso_b")

            settings_b_before = await client_b.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert settings_b_before.status_code == 200

            flows_a = await _get_onboarding_flows(client_a)
            version = flows_a["welcome"]["current_version"]

            resp = await client_a.post(
                f"{API_BASE}/settings/onboarding/welcome/complete",
                json={
                    "expected_version": version,
                    "welcome_settings": {
                        "language": "fr",
                        "base_currency": "CHF",
                        "avatar_url": "https://example.com/onb-iso-avatar.png",
                    },
                },
                timeout=TIMEOUT,
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

            flows_b_after = await _get_onboarding_flows(client_b)
            assert flows_b_after["welcome"]["status"] == "pending", "User B's progress must be unaffected by user A's atomic completion"

            settings_b_after = await client_b.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert settings_b_after.status_code == 200
            assert settings_b_after.json() == settings_b_before.json(), "User B's settings must be unaffected by user A's welcome_settings"

        print_success("✓ Atomic welcome completion is isolated per user")


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
                restore_items = [{"key": k, "value": v} for k, v in originals.items() if v is not None]
                if restore_items:
                    await client.patch(
                        f"{API_BASE}/settings/global/bulk",
                        json={"items": restore_items},
                        timeout=TIMEOUT,
                    )

        print_success("GSET-SCH-006: All 5 scheduler keys bulk update OK ✓")


# ============================================================================
# Global Settings Tests - Bulk Validation and Atomicity
# ============================================================================
#
# These rows are instance-wide: every unit on the lane's backend reads them.
# Each test reads the original value of every key it touches first, and writes
# it back in `finally` through the bulk endpoint, then reads it back again.
# While the endpoint does not validate, it DOES store the invalid values below,
# so that restore is what keeps the lane healthy. The invalid values are chosen
# to be harmless for the few milliseconds they can sit in the row: "abc" or "0"
# for session_ttl_hours read back as the 24 h fallback, where a negative TTL
# would issue already-expired sessions to every later login.


def _as_is(value: str) -> str:
    """Identity parser: the stored spelling itself is the contract."""
    return value


def _csv_items(value: str) -> list[str]:
    """Non-empty, lower-cased elements of a comma-separated setting.

    For the list-valued scheduler keys the contract is the content, not the
    spelling it is stored under: "06:00," and "06:00" both mean one slot.
    """
    return [part.lower() for part in value.split(",") if part]


async def _bulk_patch(client: httpx.AsyncClient, items: list[tuple[str, str]]) -> httpx.Response:
    """PATCH /settings/global/bulk with the given (key, value) items, in this order."""
    return await client.patch(
        f"{API_BASE}/settings/global/bulk",
        json={"items": [{"key": key, "value": value} for key, value in items]},
        timeout=TIMEOUT,
    )


async def _read_global_values(client: httpx.AsyncClient, keys: list[str]) -> dict[str, str]:
    """Stored value of each key, looked up by key in GET /settings/global (never by position)."""
    resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /settings/global failed: {resp.status_code} {resp.text}"
    stored = {item["key"]: item["value"] for item in resp.json()["items"]}
    missing = [key for key in keys if key not in stored]
    assert not missing, f"Global settings {missing} not found: cannot read the originals this test must restore"
    return {key: stored[key] for key in keys}


async def _restore_global_values(client: httpx.AsyncClient, originals: dict[str, str]) -> None:
    """Write the original values back in one bulk request, then prove they are stored again."""
    resp = await _bulk_patch(client, list(originals.items()))
    assert resp.status_code == 200, f"RESTORE FAILED, the lane may be left modified: {resp.status_code} {resp.text} (originals {originals})"
    restored = await _read_global_values(client, list(originals))
    assert restored == originals, f"RESTORE FAILED, the lane is left modified: stored {restored}, originals {originals}"
    print_info(f"  restored {restored}")


def _other_value(choices: tuple[str, ...], current: str) -> str:
    """First choice that differs from the current value, so that saving it is observable."""
    return next(choice for choice in choices if choice != current)


async def _assert_refused_and_nothing_saved(client: httpx.AsyncClient, items: list[tuple[str, str]], originals: dict[str, str], *, status: int, named: list[str]) -> None:
    """Send `items`: expect `status`, a string `detail` naming every key in `named`, and every key in `originals` unchanged."""
    resp = await _bulk_patch(client, items)
    stored = await _read_global_values(client, list(originals))
    assert resp.status_code == status, f"Expected {status}, got {resp.status_code}: {resp.text} — stored now {stored}, originals {originals}"
    detail = resp.json().get("detail")
    assert isinstance(detail, str), f"'detail' must be a string, got {type(detail).__name__}: {detail!r}"
    unnamed = [key for key in named if key not in detail]
    assert not unnamed, f"'detail' does not name {unnamed}: {detail!r}"
    assert stored == originals, f"A refused request must save nothing: stored now {stored}, originals {originals}"


async def _assert_saved(client: httpx.AsyncClient, items: list[tuple[str, str]], expected: dict[str, object], parse: Callable[[str], object] = _as_is) -> None:
    """Send `items`: expect 200, `parse(stored) == expected` per key, and the response listing exactly those settings."""
    resp = await _bulk_patch(client, items)
    stored = await _read_global_values(client, list(expected))
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text} — stored now {stored}"
    assert {key: parse(value) for key, value in stored.items()} == expected, f"Sent {items}: stored {stored}, expected {expected}"
    returned = sorted((item["key"], parse(item["value"])) for item in resp.json())
    assert returned == sorted(expected.items()), f"Sent {items}: the response must list exactly the saved settings {expected}, got {resp.json()}"


async def _assert_key_absent(client: httpx.AsyncClient, key: str) -> None:
    """An unknown key in a refused request must not have been created."""
    resp = await client.get(f"{API_BASE}/settings/global/{key}", timeout=TIMEOUT)
    assert resp.status_code == 404, f"Unknown key {key!r} must not be created: GET returned {resp.status_code} {resp.text}"


def _unknown_key() -> str:
    """A key no instance has, unique to this call."""
    return f"gset_val_unknown_{uuid.uuid4().hex}"


_INVALID_GLOBAL_VALUES = [
    # int 1..8760. Never a negative TTL here (see the section note).
    pytest.param("session_ttl_hours", "abc", id="session_ttl_hours-not_an_int"),
    pytest.param("session_ttl_hours", "0", id="session_ttl_hours-below_min"),
    pytest.param("session_ttl_hours", "8761", id="session_ttl_hours-above_max"),
    # int 1..1024. "0" reads back as the 10 MB fallback; a negative size would refuse every upload.
    pytest.param("max_file_upload_mb", "0", id="max_file_upload_mb-below_min"),
    pytest.param("max_file_upload_mb", "1025", id="max_file_upload_mb-above_max"),
    # int 1..1440
    pytest.param("scheduler_current_price_frequency_minutes", "1.5", id="price_frequency_minutes-not_an_int"),
    pytest.param("scheduler_current_price_frequency_minutes", "0", id="price_frequency_minutes-below_min"),
    pytest.param("scheduler_current_price_frequency_minutes", "1441", id="price_frequency_minutes-above_max"),
    # int 1..365
    pytest.param("scheduler_history_sync_horizon_days", "0", id="sync_horizon_days-below_min"),
    pytest.param("scheduler_history_sync_horizon_days", "366", id="sync_horizon_days-above_max"),
    # bool: true/false/1/0/yes/no/on/off in any case, nothing else. Every invalid
    # spelling reads back as False, so enable_registration (which every user
    # registration depends on) gets a single typo; the variants go on
    # require_email_verification, which nothing reads yet.
    pytest.param("enable_registration", "ture", id="enable_registration-typo"),
    pytest.param("require_email_verification", "", id="require_email_verification-empty"),
    pytest.param("require_email_verification", "2", id="require_email_verification-not_0_or_1"),
    pytest.param("require_email_verification", "y", id="require_email_verification-y_is_not_yes"),
    pytest.param("scheduler_enabled", "enabled", id="scheduler_enabled-word"),
    # HH:MM list, 00:00..23:59; empty elements are ignored, at least one time
    pytest.param("scheduler_history_sync_times", "", id="sync_times-empty"),
    pytest.param("scheduler_history_sync_times", ",", id="sync_times-no_time"),
    pytest.param("scheduler_history_sync_times", "6", id="sync_times-hour_only"),
    pytest.param("scheduler_history_sync_times", "25:00", id="sync_times-hour_out_of_range"),
    pytest.param("scheduler_history_sync_times", "12:60", id="sync_times-minute_out_of_range"),
    pytest.param("scheduler_history_sync_times", "aa:bb", id="sync_times-not_digits"),
    pytest.param("scheduler_history_sync_times", "06:00,24:00", id="sync_times-second_element_invalid"),
    # mon..sun list in any case, at least one day
    pytest.param("scheduler_history_sync_days", "", id="sync_days-empty"),
    pytest.param("scheduler_history_sync_days", ",", id="sync_days-no_day"),
    pytest.param("scheduler_history_sync_days", "monday", id="sync_days-full_name"),
    pytest.param("scheduler_history_sync_days", "mon,xyz", id="sync_days-second_element_invalid"),
    # ISO 4217. "EURO" is the NAME of EUR: pycountry's fuzzy lookup() resolves it, so
    # Currency.validate_code alone lets it through. "XXX" is avoided: it is a real code.
    pytest.param("default_currency", "EURO", id="default_currency-name_not_code"),
    pytest.param("default_currency", "ABC", id="default_currency-not_iso4217"),
    pytest.param("default_language", "de", id="default_language-unsupported"),
    pytest.param("default_theme", "blue", id="default_theme-unknown"),
]

# Every accepted bool spelling, in mixed case, and the canonical value it must be stored as.
_BOOL_SPELLINGS = [
    pytest.param("1", "true", id="1-true"),
    pytest.param("0", "false", id="0-false"),
    pytest.param("TRUE", "true", id="TRUE-true"),
    pytest.param("False", "false", id="False-false"),
    pytest.param("Yes", "true", id="Yes-true"),
    pytest.param("no", "false", id="no-false"),
    pytest.param("on", "true", id="on-true"),
    pytest.param("OFF", "false", id="OFF-false"),
]

# The accepted side of each constraint (bounds are inclusive): (key, start, sent,
# parse, expected). The start value is valid and different, so the save is
# observable whatever the lane holds. All harmless to the lane while stored,
# which is why max_file_upload_mb has no lower bound here: a 1 MB cap would
# refuse a concurrent unit's upload.
_ACCEPTED_GLOBAL_VALUES = [
    pytest.param("session_ttl_hours", "24", "1", _as_is, "1", id="session_ttl_hours-min"),
    pytest.param("session_ttl_hours", "24", "8760", _as_is, "8760", id="session_ttl_hours-max"),
    pytest.param("max_file_upload_mb", "10", "1024", _as_is, "1024", id="max_file_upload_mb-max"),
    pytest.param("scheduler_current_price_frequency_minutes", "10", "1", _as_is, "1", id="price_frequency_minutes-min"),
    pytest.param("scheduler_current_price_frequency_minutes", "10", "1440", _as_is, "1440", id="price_frequency_minutes-max"),
    pytest.param("scheduler_history_sync_horizon_days", "14", "1", _as_is, "1", id="sync_horizon_days-min"),
    pytest.param("scheduler_history_sync_horizon_days", "14", "365", _as_is, "365", id="sync_horizon_days-max"),
    pytest.param("scheduler_history_sync_times", "06:00,23:00", "00:00,23:59", _csv_items, ["00:00", "23:59"], id="sync_times-bounds"),
    pytest.param("scheduler_history_sync_times", "06:00,23:00", "06:00,", _csv_items, ["06:00"], id="sync_times-empty_element_ignored"),
    pytest.param("scheduler_history_sync_days", "mon,tue,wed,thu,fri,sat", "MON,Tue", _csv_items, ["mon", "tue"], id="sync_days-any_case"),
    pytest.param("scheduler_timezone", "UTC", "Europe/Rome", _as_is, "Europe/Rome", id="scheduler_timezone-iana_name"),
]

_THEMES = ("dark", "light", "auto")


class TestGlobalSettingsBulkValidation:
    """PATCH /settings/global/bulk checks every value and applies a request all-or-nothing.

    Unknown keys are checked first (any → 404), then every value (any invalid →
    422, `detail` a string naming each rejected key). A refused request saves
    nothing, valid items included; an accepted one is saved whole and listed.

    Test IDs: GSET-VAL-001..GSET-VAL-010
    """

    @pytest.mark.parametrize(("key", "value"), _INVALID_GLOBAL_VALUES)
    @pytest.mark.asyncio
    async def test_invalid_value_is_refused_and_not_saved(self, test_server, key: str, value: str):
        """GSET-VAL-001: An invalid value → 422 whose detail names the key; the stored value is unchanged."""
        print_section(f"GSET-VAL-001: {key}={value!r} → 422, nothing saved")

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [key])
            try:
                await _assert_refused_and_nothing_saved(client, [(key, value)], originals, status=422, named=[key])
            finally:
                await _restore_global_values(client, originals)

        print_success(f"✓ {key}={value!r} refused, {key} still {originals[key]!r}")

    @pytest.mark.asyncio
    async def test_timezone_outside_iana_database_is_refused(self, test_server):
        """GSET-VAL-002: A scheduler_timezone missing from the server's IANA database → 422; stored value unchanged."""
        print_section("GSET-VAL-002: scheduler_timezone='Mars/Olympus' → 422, nothing saved")
        if not zoneinfo.available_timezones():
            pytest.skip("No IANA timezone database on this machine: the server then accepts any name, by design")

        key = "scheduler_timezone"
        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [key])
            try:
                await _assert_refused_and_nothing_saved(client, [(key, "Mars/Olympus")], originals, status=422, named=[key])
            finally:
                await _restore_global_values(client, originals)

        print_success("✓ Unknown timezone refused, nothing saved")

    @pytest.mark.asyncio
    async def test_every_invalid_key_is_named(self, test_server):
        """GSET-VAL-003: Two invalid values in one request → one 422 whose detail names both keys; nothing saved."""
        print_section("GSET-VAL-003: two invalid values → 422 naming both, nothing saved")
        items = [("scheduler_history_sync_days", "mon,xyz"), ("scheduler_current_price_frequency_minutes", "0")]
        keys = [key for key, _ in items]

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, keys)
            try:
                await _assert_refused_and_nothing_saved(client, items, originals, status=422, named=keys)
            finally:
                await _restore_global_values(client, originals)

        print_success("✓ Both rejected keys named, nothing saved")

    @pytest.mark.asyncio
    async def test_valid_item_not_saved_when_another_is_invalid(self, test_server):
        """GSET-VAL-004: A valid change followed by an invalid value → 422; the valid change is NOT saved."""
        print_section("GSET-VAL-004: valid + invalid → 422, the valid item is not saved")
        valid_key, invalid_key = "default_theme", "scheduler_history_sync_horizon_days"

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [valid_key, invalid_key])
            items = [(valid_key, _other_value(_THEMES, originals[valid_key])), (invalid_key, "0")]
            try:
                await _assert_refused_and_nothing_saved(client, items, originals, status=422, named=[invalid_key])
            finally:
                await _restore_global_values(client, originals)

        print_success("✓ Request refused as a whole, valid item not saved")

    @pytest.mark.asyncio
    async def test_valid_item_not_saved_when_a_key_is_unknown(self, test_server):
        """GSET-VAL-005: A valid change followed by an unknown key → 404; the valid change is NOT saved."""
        print_section("GSET-VAL-005: valid + unknown key → 404, the valid item is not saved")
        valid_key, unknown_key = "default_theme", _unknown_key()

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [valid_key])
            items = [(valid_key, _other_value(_THEMES, originals[valid_key])), (unknown_key, "1")]
            try:
                await _assert_refused_and_nothing_saved(client, items, originals, status=404, named=[unknown_key])
                await _assert_key_absent(client, unknown_key)
            finally:
                await _restore_global_values(client, originals)

        print_success("✓ Unknown key → 404, valid item not saved")

    @pytest.mark.asyncio
    async def test_unknown_key_is_checked_before_values(self, test_server):
        """GSET-VAL-006: An invalid value followed by an unknown key → 404, not 422 (keys come first); nothing saved."""
        print_section("GSET-VAL-006: invalid value + unknown key → 404, nothing saved")
        invalid_key, unknown_key = "scheduler_history_sync_horizon_days", _unknown_key()

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [invalid_key])
            try:
                await _assert_refused_and_nothing_saved(client, [(invalid_key, "0"), (unknown_key, "1")], originals, status=404, named=[unknown_key])
                await _assert_key_absent(client, unknown_key)
            finally:
                await _restore_global_values(client, originals)

        print_success("✓ Unknown key reported first, nothing saved")

    @pytest.mark.parametrize(("sent", "canonical"), _BOOL_SPELLINGS)
    @pytest.mark.asyncio
    async def test_bool_spelling_is_stored_canonical(self, test_server, sent: str, canonical: str):
        """GSET-VAL-007: Every accepted bool spelling → 200, stored and returned as canonical "true"/"false"."""
        print_section(f"GSET-VAL-007: {sent!r} → stored {canonical!r}")
        key = "require_email_verification"  # read nowhere yet: flipping it is harmless to the lane
        start = "false" if canonical == "true" else "true"

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [key])
            try:
                await _assert_saved(client, [(key, start)], {key: start})
                await _assert_saved(client, [(key, sent)], {key: canonical})
            finally:
                await _restore_global_values(client, originals)

        print_success(f"✓ {sent!r} stored as {canonical!r}")

    @pytest.mark.asyncio
    async def test_currency_is_stored_uppercase(self, test_server):
        """GSET-VAL-008: default_currency "usd" → 200, stored and returned as "USD"."""
        print_section("GSET-VAL-008: default_currency 'usd' → stored 'USD'")
        key = "default_currency"

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [key])
            try:
                await _assert_saved(client, [(key, "EUR")], {key: "EUR"})
                await _assert_saved(client, [(key, "usd")], {key: "USD"})
            finally:
                await _restore_global_values(client, originals)

        print_success("✓ 'usd' stored as 'USD'")

    @pytest.mark.asyncio
    async def test_valid_multi_key_save(self, test_server):
        """GSET-VAL-009 (control): Valid values for two keys in one request → 200, both stored and listed."""
        print_section("GSET-VAL-009: two valid values → 200, both saved")
        theme_key, horizon_key = "default_theme", "scheduler_history_sync_horizon_days"

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [theme_key, horizon_key])
            new_values = {
                theme_key: _other_value(_THEMES, originals[theme_key]),
                horizon_key: _other_value(("21", "30"), originals[horizon_key]),
            }
            try:
                await _assert_saved(client, list(new_values.items()), new_values)
            finally:
                await _restore_global_values(client, originals)

        print_success("✓ Both values saved")

    @pytest.mark.parametrize(("key", "start", "sent", "parse", "expected"), _ACCEPTED_GLOBAL_VALUES)
    @pytest.mark.asyncio
    async def test_value_inside_constraint_is_saved(self, test_server, key: str, start: str, sent: str, parse: Callable[[str], object], expected: object):
        """GSET-VAL-010 (control): A value on the accepted side of its constraint → 200 and stored."""
        print_section(f"GSET-VAL-010: {key}={sent!r} → 200, saved")

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [key])
            try:
                await _assert_saved(client, [(key, start)], {key: parse(start)}, parse)
                await _assert_saved(client, [(key, sent)], {key: expected}, parse)
            finally:
                await _restore_global_values(client, originals)

        print_success(f"✓ {key}={sent!r} saved")
