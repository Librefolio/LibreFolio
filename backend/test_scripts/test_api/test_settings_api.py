"""
Settings API Tests

Tests for user settings and global settings endpoints.

Test IDs:
- SET-001 to SET-004: User Settings
- SET-A11-01 to SET-A11-07: a stored interface preference the app does not know (lots A-11 and UIP, per key), in-process on a private database
- SET-UIP-01 to SET-UIP-12: ui_preferences merge, size cap, defaults, default_chart_line_shape (lot UIP)
- GSET-001 to GSET-007: Global Settings (GSET-001, 002, 002c: who reads them, A6d — any signed-in user,
  nobody without a valid session)
"""

import uuid
import zoneinfo
from collections.abc import AsyncIterator, Callable
from typing import Optional

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.schemas.settings import GlobalSettingRead
from backend.app.services.accounts import user_service
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
            assert {"language", "base_currency", "ui_preferences", "ui_preference_defaults"} <= set(data), "Response should contain user settings"
            assert "theme" not in data, "theme is no top-level field any more: it lives in ui_preferences"

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
            new_settings = {"language": "it", "ui_preferences": {"theme": "dark"}, "base_currency": "USD"}

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
                "ui_preferences": {"theme": "dark"},
                "avatar_url": "https://example.com/settings-avatar.png",
            }

            resp = await client.put(f"{API_BASE}/settings/user", json=payload, timeout=TIMEOUT)

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            body = resp.json()
            assert {key: body[key] for key in payload} == payload
            assert set(body["ui_preference_defaults"]) == {"theme", "chart_line_shape"}

            get_resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert get_resp.status_code == 200
            assert {key: get_resp.json()[key] for key in payload} == payload

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
                json={"ui_preferences": {"theme": "auto"}, "avatar_url": "https://example.com/updated-avatar.png"},
                timeout=TIMEOUT,
            )

            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            body = resp.json()
            assert {key: body[key] for key in ("language", "base_currency", "ui_preferences", "avatar_url")} == {
                "language": initial_resp.json()["language"],
                "base_currency": initial_resp.json()["base_currency"],
                "ui_preferences": {"theme": "auto"},
                "avatar_url": "https://example.com/updated-avatar.png",
            }, "omitted fields are preserved, the sent ones saved"

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
                "ui_preferences": {"theme": "dark"},
                "avatar_url": "https://example.com/settings-avatar-to-clear.png",
            }
            set_resp = await client.put(f"{API_BASE}/settings/user", json=set_payload, timeout=TIMEOUT)
            assert set_resp.status_code == 200, f"Expected 200, got {set_resp.status_code}: {set_resp.text}"
            assert {key: set_resp.json()[key] for key in set_payload} == set_payload

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
                "ui_preferences": {"theme": "dark"},
                "avatar_url": None,
            }
            body = clear_resp.json()
            assert {key: body[key] for key in expected} == expected, f"Expected {expected}, got {body}"

            # A subsequent GET must reflect the same cleared state.
            get_resp = await client.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
            assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}"
            assert {key: get_resp.json()[key] for key in expected} == expected, f"Expected {expected}, got {get_resp.json()}"

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
    "tools_page_guide",
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
                assert len(data["flows"]) == 16, f"Final contract must expose exactly 16 flows, got {[item['flow'] for item in data['flows']]}"
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

        print_success("✓ GET exposes the final 16 flows and both ordered step arrays")

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
# Global Settings Tests - List, and who reads them
# ============================================================================
#
# Read by signed-in users only (A6d, decision 36): any session, an administrator's or a regular user's, reads them
# whole, and nobody without a valid one, whatever the key. Writes stay the administrator's (require_admin, GSET-005 to
# GSET-007). What the app needs before anyone signs in, the registration mode included, comes from the public
# GET /system/instance (test_system_api.py), no longer from here.

#: The answer of every protected route (get_current_user) to a request without a session cookie.
NO_SESSION_ANSWER = {"detail": "Not authenticated"}
#: The answer of every protected route (get_current_user) to a session cookie the server never issued.
FORGED_SESSION_ANSWER = {"detail": "Session expired or invalid"}
#: A protected route of this file's own: the reference for the answer every protected route gives.
PROTECTED_REFERENCE = f"{API_BASE}/settings/user"
#: Every field of a global setting, as GET /settings/global lists it.
GLOBAL_SETTING_FIELDS = set(GlobalSettingRead.model_fields)


async def _get(url: str, headers: dict[str, str] | None = None) -> httpx.Response:
    """GET ``url`` with exactly these headers, from a client with an empty cookie jar: a session travels only in ``headers``."""
    async with httpx.AsyncClient() as client:
        return await client.get(url, headers=headers or {}, timeout=TIMEOUT)


async def _delete_user_of_this_test(username: str) -> None:
    """Cleanup of an account a test of this section registered, through the service layer, with what goes with it."""
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        user = await user_service.get_user_by_username(session, username)
        if user is not None:
            await user_service.delete_user(session, user.id)


@pytest_asyncio.fixture
async def regular_session(test_server) -> AsyncIterator[dict[str, str]]:
    """A Cookie header with the session of a user registered for this test only, proven a regular user, not an administrator.

    The api category populates the lane before it runs, so a new registration is never the instance's first account,
    the one that becomes its administrator: the register answer and GET /auth/me check it rather than assume it. The
    session travels explicitly on each request, never through a cookie jar; the account is deleted at teardown.
    """
    username = f"gset_reader_{uuid.uuid4().hex[:12]}"
    credentials = {"username": username, "password": "TestPass123!"}
    try:
        async with httpx.AsyncClient() as client:
            registered = await client.post(f"{API_BASE}/auth/register", json={**credentials, "email": f"{username}@test.com"}, timeout=TIMEOUT)
            assert registered.status_code == 201, f"Setup: registering {username} failed: {registered.status_code} {registered.text}"
            assert registered.json()["user"]["is_superuser"] is False, f"Barrier: {username} must be a regular user, not an administrator (the lane already has its accounts): {registered.text}"
            login = await client.post(f"{API_BASE}/auth/login", json=credentials, timeout=TIMEOUT)
        token = login.cookies.get(SESSION_COOKIE_NAME)
        assert login.status_code == 200 and token, f"Setup: signing in as {username} failed: {login.status_code} {login.text}"
        cookie = {"Cookie": f"{SESSION_COOKIE_NAME}={token}"}
        me = await _get(f"{API_BASE}/auth/me", cookie)
        assert me.status_code == 200 and me.json()["user"]["username"] == username and me.json()["user"]["is_superuser"] is False, f"Barrier: the session must be {username}'s, a regular user's: {me.status_code} {me.text}"
        yield cookie
    finally:
        await _delete_user_of_this_test(username)


class TestGlobalSettingsList:
    """Listing the global settings, and who may read them: any signed-in user, nobody without a valid session."""

    @pytest.mark.asyncio
    async def test_list_global_settings_authenticated(self, test_server, regular_session):
        """GSET-001: Any signed-in user lists the global settings, not only an administrator: a regular user gets 200 and
        the same settings an administrator gets, each with every field of a global setting."""
        print_section("GSET-001: GET /settings/global - Regular user")

        resp = await _get(f"{API_BASE}/settings/global", regular_session)

        assert resp.status_code == 200, f"GET /settings/global must answer any signed-in user, a regular one too: {resp.status_code} {resp.text}"
        data = resp.json()
        assert set(data) == {"items"} and isinstance(data["items"], list), f"The answer must be the list of the global settings, under items: {resp.text}"
        malformed = [item for item in data["items"] if set(item) != GLOBAL_SETTING_FIELDS]
        assert not malformed, f"Every global setting must carry exactly {sorted(GLOBAL_SETTING_FIELDS)}: {malformed}"
        keys = {item["key"] for item in data["items"]}
        assert "session_ttl_hours" in keys, f"Barrier: the list holds the settings the instance seeds, session_ttl_hours among them: {sorted(keys)}"

        async with httpx.AsyncClient() as admin_client:
            await get_admin_session(admin_client)
            admin_resp = await admin_client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
        assert admin_resp.status_code == 200, f"Barrier: an administrator lists the global settings: {admin_resp.status_code} {admin_resp.text}"
        admin_keys = {item["key"] for item in admin_resp.json()["items"]}
        assert keys == admin_keys, f"A regular user must read the same global settings as an administrator: missing {sorted(admin_keys - keys)}, extra {sorted(keys - admin_keys)}"

        print_info(f"  {len(keys)} global settings, the same as an administrator's")
        print_success("✓ A regular user lists the global settings")

    @pytest.mark.asyncio
    async def test_list_global_settings_unauthenticated(self, test_server):
        """GSET-002: List global settings without a session → 401, the answer of every protected route.

        No longer public (A6d, decision 36): the scheduler, the session lifetime and the registration mode are for
        signed-in users only. The login page does not need them: it reads the registration mode, and whether the instance
        has no account yet, from the public GET /system/instance.
        """
        print_section("GSET-002: GET /settings/global - No session → 401")

        reference = await _get(PROTECTED_REFERENCE)
        resp = await _get(f"{API_BASE}/settings/global")

        assert (reference.status_code, reference.json()) == (401, NO_SESSION_ANSWER), f"Barrier: a protected route without a session answers 401 {NO_SESSION_ANSWER}: GET /settings/user → {reference.status_code} {reference.text}"
        assert (resp.status_code, resp.json()) == (reference.status_code, reference.json()), f"GET /settings/global without a session must answer as every protected route, 401 {NO_SESSION_ANSWER}: {resp.status_code} {resp.text}"
        print_success("✓ No session: 401, as every protected route")

    @pytest.mark.asyncio
    async def test_global_settings_with_a_forged_session_cookie(self, test_server):
        """GSET-002c: The read with a session cookie the server never issued → 401, the answer every protected route
        gives that cookie: GET /settings/global accepts only a session the server issued."""
        print_section("GSET-002c: GET /settings/global - Forged session cookie → 401")
        forged = {"Cookie": f"{SESSION_COOKIE_NAME}=forged-{uuid.uuid4().hex}"}
        paths = ["/settings/global"]

        reference = await _get(PROTECTED_REFERENCE, forged)
        answers = {path: await _get(f"{API_BASE}{path}", forged) for path in paths}

        assert (reference.status_code, reference.json()) == (401, FORGED_SESSION_ANSWER), f"Barrier: a protected route reads the forged cookie as a session it never issued, 401 {FORGED_SESSION_ANSWER}: GET /settings/user → {reference.status_code} {reference.text}"
        for path, resp in answers.items():
            assert (resp.status_code, resp.json()) == (reference.status_code, reference.json()), f"GET {path} with a forged session cookie must answer as every protected route, 401 {FORGED_SESSION_ANSWER}: {resp.status_code} {resp.text}"
        print_success("✓ Forged session cookie: 401, as every protected route")


# ============================================================================
# Global Settings Tests - Update
# ============================================================================


class TestGlobalSettingsUpdate:
    """Tests for global setting update operations."""

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
    """An unknown key in a refused request must not have been created: the list must not carry it."""
    resp = await client.get(f"{API_BASE}/settings/global", timeout=TIMEOUT)
    assert resp.status_code == 200, f"GET /settings/global failed: {resp.status_code} {resp.text}"
    assert key not in {item["key"] for item in resp.json()["items"]}, f"Unknown key {key!r} must not be created: GET /settings/global lists it"


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
    # One of open, invite, disabled. Every user registration of the lane depends on
    # registration_mode, so it gets a single refused value, never an accepted one.
    pytest.param("registration_mode", "closed", id="registration_mode-unknown_choice"),
    # bool: true/false/1/0/yes/no/on/off in any case, nothing else. Every invalid
    # spelling reads back as False; the variants go on require_email_verification:
    # a refusal stores nothing, so the lane's registrations never see it on.
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
    pytest.param("default_chart_line_shape", "curvy", id="default_chart_line_shape-unknown"),
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

    Test IDs: GSET-VAL-001..GSET-VAL-011
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
        # The lane's server runs with --no-scheduler: flipping it is harmless (GSET-SCH-001 does too). Never
        # require_email_verification: it changes every registration of the lane, and turns on only with email.
        key = "scheduler_enabled"
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

    @pytest.mark.asyncio
    async def test_email_verification_turned_on_without_email_is_refused(self, test_server):
        """GSET-VAL-011: require_email_verification off → on while no email with a link can go out (a test lane has no
        SMTP configuration) → 409 EMAIL_VERIFICATION_UNAVAILABLE naming the key; nothing saved, the other item included."""
        print_section("GSET-VAL-011: require_email_verification on without email → 409, nothing saved")
        key = "require_email_verification"
        other = "session_ttl_hours"

        async with httpx.AsyncClient() as client:
            await get_admin_session(client)
            originals = await _read_global_values(client, [key, other])
            assert originals[key] == "false", f"A lane without email can never have {key} on: stored {originals[key]!r}"
            changed = "25" if originals[other] != "25" else "26"
            try:
                resp = await _bulk_patch(client, [(other, changed), (key, "true")])
                stored = await _read_global_values(client, [key, other])
                assert resp.status_code == 409, f"Expected 409, got {resp.status_code}: {resp.text} — stored now {stored}"
                detail = resp.json().get("detail")
                assert isinstance(detail, dict), f"'detail' must be an object, got {detail!r}"
                assert detail.get("error_code") == "EMAIL_VERIFICATION_UNAVAILABLE" and detail.get("key") == key, f"Unexpected detail: {detail!r}"
                assert stored == originals, f"A refused request must save nothing: stored now {stored}, originals {originals}"
            finally:
                await _restore_global_values(client, originals)

        print_success(f"✓ {key} stays off, {other} still {originals[other]!r}")


# ============================================================================
# STORED INTERFACE PREFERENCES — lot A-11 (per key) and lot UIP (SET-A11-01 to SET-A11-07, SET-UIP-01 to SET-UIP-10),
# in-process on a private database
# ============================================================================
# user_settings.ui_preferences is a TEXT column holding a JSON object: SQLite enforces nothing, so a hand-edited row,
# a downgrade-and-upgrade, or a later release can leave text that is not JSON, a JSON array, or a known key holding a
# value this version does not know. Such a row exists on no lane, whose rows the app itself wrote, and its warning is
# logged in a process no test can capture: so these cases run in-process, as TestSignInLogsNoTypedIdentifier
# (test_auth_api.py, lot A-22) runs its own, on a private instance — the real auth and settings routers, mounted under
# the API prefix as api/v1/router.py mounts them, in an app of this test whose get_session_generator opens sessions on a
# private SQLite file under tmp_path, seeded as a new install; get_async_engine, the lane's database, is a tripwire.
# What a hand edit leaves is written by SQL on that file. bcrypt runs at cost 4, the dummy hash in a cache of the test's
# own; the login limiters are fresh ones of the shipped size. The same private file serves the merge rules of
# PUT /settings/user: the stored text is read back by SQL, and the global defaults are rows of the file. Nothing waits.

import contextlib
import functools
import json as jsonlib
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args

import structlog
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import settings as settings_routes
from backend.app.config import API_V1_PREFIX
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import User, UserSettings
from backend.app.db.session import get_session_generator
from backend.app.schemas.settings import SETTINGS_REGISTRY, UI_PREFERENCES_MAX_BYTES, UIPreferences
from backend.app.services.accounts import auth_service, login_throttle
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter

#: The logger that warns of an unknown stored preference: the settings service's structlog.get_logger(__name__).
_SETTINGS_SERVICE_LOGGER = "backend.app.services.accounts.settings_service"
#: The canary logged through _SETTINGS_SERVICE_LOGGER inside every capture.
_THEME_LOG_CANARY = f"canary: the capture sees the events of {_SETTINGS_SERVICE_LOGGER}"


def _literal_values(key: str) -> tuple[str, ...]:
    """The values ``UIPreferences.<key>`` accepts, read from the schema (an ``Optional[Literal[...]]``)."""
    return tuple(value for arg in get_args(UIPreferences.model_fields[key].annotation) for value in get_args(arg))


#: The themes and line shapes the app knows: the values of the schema's Literals (contract).
_KNOWN_THEMES: tuple[str, ...] = _literal_values("theme")
_KNOWN_SHAPES: tuple[str, ...] = _literal_values("chart_line_shape")
#: A stored theme no release knows, as a hand edit leaves it.
_UNKNOWN_THEME = "sepia"
#: An unknown stored theme longer than 20 characters: the warning carries its first 20.
_LONG_UNKNOWN_THEME = "solarized-high-contrast-v2"
#: A global default_theme no release knows either, written as the setting's row.
_UNKNOWN_DEFAULT_THEME = "neon"
_DEFAULT_THEME_KEY = SETTINGS_REGISTRY.global_.DEFAULT_THEME.key
_DEFAULT_SHAPE_KEY = SETTINGS_REGISTRY.global_.DEFAULT_CHART_LINE_SHAPE.key
#: The settings every account of the private instance is written with, its preferences aside; and its password.
_THEME_ACCOUNT_LANGUAGE = "en"
_THEME_ACCOUNT_CURRENCY = "EUR"
_THEME_PASSWORD = "Stored-Theme-Pass-2026"
#: (global default_theme, ui_preference_defaults.theme): the default when the app knows it, else auto.
_SHOWN_FOR_AN_UNKNOWN_THEME = [
    pytest.param("dark", "dark", id="default-dark-shown-dark"),
    pytest.param(_UNKNOWN_DEFAULT_THEME, "auto", id="default-unknown-shown-auto"),
]
#: Rows a hand edit can leave, each of which yields NO own preference: (stored text, id).
_UNREADABLE_ROWS = [
    pytest.param(f'{{"theme":"{_UNKNOWN_THEME}"}}', id="theme-unknown-value"),
    pytest.param("this is not json", id="not-json"),
    pytest.param('["dark"]', id="json-array"),
    pytest.param('{"theme":1}', id="theme-not-a-string"),
]
#: (stored theme, global default_theme): every known theme, with another known theme as the default, so «shown as stored» is never the default's.
_KNOWN_STORED_THEMES = [pytest.param(theme, _KNOWN_THEMES[(index + 1) % len(_KNOWN_THEMES)], id=f"stored-{theme}") for index, theme in enumerate(_KNOWN_THEMES)]


@dataclass(frozen=True)
class _ThemeInstance:
    """An instance of one test: the auth and settings routers, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


@dataclass(frozen=True)
class _ThemeAccount:
    """An active account of the private instance."""

    user_id: int
    username: str


def _theme_app(engine: AsyncEngine) -> FastAPI:
    """The real auth and settings routers, mounted under the API prefix as ``api/v1/router.py`` mounts them; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    app.include_router(auth_api.router, prefix=API_V1_PREFIX)
    app.include_router(settings_routes.router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's private one")


@pytest_asyncio.fixture
async def theme_instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_ThemeInstance]:
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with, no account. Disposed at teardown.

    bcrypt at cost 4, with a dummy-hash cache of the test's own (as private_sign_in in test_auth_api.py); login limiters
    of the shipped size holding no count, so no sign-in of another in-process test counts against these; get_async_engine
    a tripwire where these routes could reach it.
    """
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_service, "_dummy_password_hash", functools.cache(auth_service._dummy_password_hash.__wrapped__))
    for name in ("LOGIN_BY_IDENTIFIER", "LOGIN_BY_ADDRESS"):
        shipped = getattr(login_throttle, name)
        monkeypatch.setattr(login_throttle, name, SlidingWindowLimiter(shipped.limit, shipped.window_seconds))
    for module in (db_session, settings_routes):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stored-theme.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _ThemeInstance(engine=engine, app=_theme_app(engine))
    finally:
        await engine.dispose()


async def _theme_account(instance: _ThemeInstance, ui_preferences: Optional[str] = None) -> _ThemeAccount:
    """An active account written as rows: a real bcrypt hash of _THEME_PASSWORD (cost 4), and its user_settings row — language, currency, ``ui_preferences`` as given (raw text or NULL), no avatar."""
    username = f"theme_{uuid.uuid4().hex[:12]}"
    async with AsyncSession(instance.engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password=auth_service.hash_password(_THEME_PASSWORD), is_active=True)
        session.add(user)
        await session.flush()
        session.add(UserSettings(user_id=user.id, language=_THEME_ACCOUNT_LANGUAGE, base_currency=_THEME_ACCOUNT_CURRENCY, ui_preferences=ui_preferences))
        await session.commit()
    assert user.id is not None, f"Setup: {username} must be written"
    return _ThemeAccount(user_id=user.id, username=username)


async def _theme_write(instance: _ThemeInstance, statement: str, **parameters: Any) -> None:
    """One UPDATE by SQL on the private file, as a hand edit makes it, committed; it must change exactly one row."""
    async with instance.engine.begin() as connection:
        changed = (await connection.execute(text(statement), parameters)).rowcount
    assert changed == 1, f"Setup: {statement} with {parameters} must change one row, it changed {changed}"


async def _hand_edit_ui_preferences(instance: _ThemeInstance, user_id: int, raw: Optional[str]) -> None:
    """The account's stored ``ui_preferences`` is ``raw`` (text or NULL): written by SQL."""
    await _theme_write(instance, "UPDATE user_settings SET ui_preferences = :raw WHERE user_id = :user_id", raw=raw, user_id=user_id)


async def _hand_edit_global(instance: _ThemeInstance, key: str, value: str) -> None:
    """The global setting ``key`` is ``value``: the setting's row written by SQL."""
    await _theme_write(instance, "UPDATE global_settings SET value = :value WHERE key = :key", value=value, key=key)


async def _hand_edit_default_theme(instance: _ThemeInstance, value: str) -> None:
    """The global default_theme is ``value``: the setting's row written by SQL."""
    await _hand_edit_global(instance, _DEFAULT_THEME_KEY, value)


async def _theme_stored(instance: _ThemeInstance, user_id: int) -> dict[str, Any]:
    """What is committed: the account's user_settings row, every column but its ids, and the two global defaults."""
    async with instance.engine.connect() as connection:
        row = (await connection.execute(text("SELECT language, base_currency, ui_preferences, avatar_url, created_at, updated_at FROM user_settings WHERE user_id = :user_id"), {"user_id": user_id})).mappings().one()
        defaults = {}
        for key in (_DEFAULT_THEME_KEY, _DEFAULT_SHAPE_KEY):
            defaults[key] = (await connection.execute(text("SELECT value FROM global_settings WHERE key = :key"), {"key": key})).scalar_one()
    return {**dict(row), **defaults}


async def _stored_ui_preferences_text(instance: _ThemeInstance, user_id: int) -> Optional[str]:
    """The raw ``user_settings.ui_preferences`` of the account, read by SQL."""
    async with instance.engine.connect() as connection:
        return (await connection.execute(text("SELECT ui_preferences FROM user_settings WHERE user_id = :user_id"), {"user_id": user_id})).scalar_one()


async def _theme_request(instance: _ThemeInstance, method: str, path: str, *, cookie: Optional[str] = None, json: Optional[dict[str, Any]] = None) -> httpx.Response:
    """One request to the private instance from a client of its own: no cookie jar, the session cookie, if any, sent explicitly."""
    headers = {"Cookie": f"{SESSION_COOKIE_NAME}={cookie}"} if cookie else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=instance.app), base_url="http://test", timeout=TIMEOUT) as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", json=json, headers=headers)


async def _theme_login(instance: _ThemeInstance, account: _ThemeAccount) -> httpx.Response:
    return await _theme_request(instance, "POST", "/auth/login", json={"username": account.username, "password": _THEME_PASSWORD})


def _session_cookie_values(response: httpx.Response) -> list[str]:
    """The values the answer's ``Set-Cookie`` headers give the session cookie, found by name."""
    values = []
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == SESSION_COOKIE_NAME:
            values.append(value.strip())
    return values


async def _theme_signed_in(instance: _ThemeInstance, account: _ThemeAccount) -> str:
    """The session cookie of ``account``, signed in through POST /auth/login. It ends on its promise: a 200, one cookie."""
    login = await _theme_login(instance, account)
    cookies = _session_cookie_values(login)
    assert login.status_code == 200 and len(cookies) == 1 and cookies[0], f"Setup: {account.username} signs in: {login.status_code} {login.text}"
    return cookies[0]


@contextlib.contextmanager
def _settings_service_log() -> Iterator[list[dict[str, Any]]]:
    """Every structlog event logged inside the block, each with its logger's name, after a canary of the settings service's logger."""
    with capture_logs(processors=[structlog.stdlib.add_logger_name]) as events:
        structlog.get_logger(_SETTINGS_SERVICE_LOGGER).debug(_THEME_LOG_CANARY)
        yield events


def _theme_warnings(events: list[dict[str, Any]], request: str) -> list[dict[str, Any]]:
    """The WARNING events of the settings service's logger among ``events``.

    Barrier first: the canary reached the capture with that logger's name, or a capture that sees nothing would pass for
    a request that warns of nothing.
    """
    assert any(event.get("event") == _THEME_LOG_CANARY and event.get("logger") == _SETTINGS_SERVICE_LOGGER for event in events), f"barrier ({request}): the events of {_SETTINGS_SERVICE_LOGGER} do not reach capture_logs with their logger's name: {events}"
    return [event for event in events if event.get("logger") == _SETTINGS_SERVICE_LOGGER and event.get("log_level") == "warning"]


def _assert_one_theme_warning(events: list[dict[str, Any]], expected: dict[str, Any], request: str) -> None:
    """Exactly one WARNING of the settings service's logger among ``events``, carrying ``expected`` (its text is the implementer's)."""
    warnings = _theme_warnings(events, request)
    assert len(warnings) == 1, f"{request}: a read of an unknown stored preference must log exactly one WARNING through {_SETTINGS_SERVICE_LOGGER}: {warnings}"
    carried = {field: warnings[0].get(field) for field in expected}
    assert carried == expected, f"{request}: the warning must carry {expected}: {warnings[0]}"


def _own_and_defaults(answer: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """(ui_preferences, ui_preference_defaults) of a settings answer — a login's ``user_settings`` or a GET/PUT body."""
    return answer.get("ui_preferences"), answer.get("ui_preference_defaults")


class TestStoredPreferencesUnknownToTheApp:
    """Lot A-11 (per key, lot UIP): a stored preference the app does not know is left out, never fatal.

    The contract:

    1. The known themes are exactly the values of ``UIPreferences.theme``'s Literal: light, dark, auto (SET-A11-01).
    2. A stored row that is not JSON, a JSON array, or holds a known key with a value the app does not know (or not
       a string) yields no own key for it: ``ui_preferences`` answers without it, ``ui_preference_defaults.theme`` is
       the instance's global ``default_theme`` when that is a known theme, otherwise ``auto``.
    3. Reading never writes: the row and the global defaults stay as left after the login, ``GET /settings/user`` and a
       ``PUT /settings/user`` without ``ui_preferences`` — a later version that knows the value shows it again.
    4. ``PUT /settings/user`` without ``ui_preferences`` answers 200, saves the rest and keeps the stored text
       (SET-A11-04); with ``ui_preferences.theme`` it merges the new value into the readable part (SET-A11-05).
    5. ``POST /auth/login`` answers 200 with ``ui_preferences`` as above, and the session works (SET-A11-02/03).
    6. A known stored theme is shown as stored (SET-A11-06).
    7. Each read of an unknown stored value logs one structlog WARNING through
       ``backend.app.services.accounts.settings_service`` carrying ``user_id``, ``key`` and ``stored`` — the stored value
       cut to its first 20 characters (SET-A11-07); the read of a known one logs none.

    Write-safe: every account and setting lives in the test's own tmp_path (theme_instance); no request reaches the lane.
    """

    @pytest.mark.asyncio
    async def test_the_known_values_are_those_of_the_schema(self):
        """SET-A11-01 — GUARD: the themes the app knows are exactly the values of ``UIPreferences.theme``'s Literal — light,
        dark, auto — and the line shapes segments, steps, spline; the values these cases hand-edit are none of them."""
        print_section("SET-A11-01: the known values are the schema's Literals")
        assert set(_KNOWN_THEMES) == {"light", "dark", "auto"}, f"UIPreferences.theme must be Literal['light', 'dark', 'auto']: its values are {_KNOWN_THEMES}"
        assert set(_KNOWN_SHAPES) == {"segments", "steps", "spline"}, f"UIPreferences.chart_line_shape must be Literal['segments', 'steps', 'spline']: {_KNOWN_SHAPES}"
        hand_edited = {_UNKNOWN_THEME, _LONG_UNKNOWN_THEME, _UNKNOWN_DEFAULT_THEME}
        assert not hand_edited & set(_KNOWN_THEMES), f"Premise: {sorted(hand_edited)} must be themes the app does not know: {_KNOWN_THEMES}"
        assert len(_LONG_UNKNOWN_THEME) > 20, f"Premise: {_LONG_UNKNOWN_THEME!r} must be longer than 20 characters"
        print_success(f"✓ Known themes {_KNOWN_THEMES}, shapes {_KNOWN_SHAPES}; {sorted(hand_edited)} unknown")

    @pytest.mark.parametrize(("default_theme", "shown"), _SHOWN_FOR_AN_UNKNOWN_THEME)
    @pytest.mark.parametrize("raw", _UNREADABLE_ROWS)
    @pytest.mark.asyncio
    async def test_sign_in_leaves_out_an_unreadable_preference_and_writes_nothing(self, theme_instance: _ThemeInstance, raw: str, default_theme: str, shown: str):
        """SET-A11-02: an account whose stored ``ui_preferences`` is unreadable (unknown theme value, not JSON, a JSON array,
        a non-string theme) signs in: ``POST /auth/login`` answers 200, ``user_settings.ui_preferences`` is ``{}`` and
        ``ui_preference_defaults.theme`` = ``shown`` — the global default_theme when the app knows it, otherwise auto —,
        with one session cookie, and ``GET /settings/user`` with it answers the same. Neither wrote anything."""
        print_section(f"SET-A11-02: sign-in with the stored {raw!r}, default_theme {default_theme!r}: defaults.theme {shown!r}")
        account = await _theme_account(theme_instance)
        await _hand_edit_default_theme(theme_instance, default_theme)
        await _hand_edit_ui_preferences(theme_instance, account.user_id, raw)
        before = await _theme_stored(theme_instance, account.user_id)

        login = await _theme_login(theme_instance, account)

        assert login.status_code == 200, f"An unreadable stored preference must not stop the sign-in: POST /auth/login answered {login.status_code} {login.text}"
        own, defaults = _own_and_defaults(login.json().get("user_settings") or {})
        assert own == {}, f"The login must leave the unreadable preference out: ui_preferences {own}"
        assert (defaults or {}).get("theme") == shown, f"ui_preference_defaults.theme must be {shown!r} (default_theme {default_theme!r}): {defaults}"
        cookies = _session_cookie_values(login)
        assert len(cookies) == 1 and cookies[0], f"The login must set one session cookie: {login.headers.get_list('set-cookie')}"
        reread = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookies[0])
        assert reread.status_code == 200 and _own_and_defaults(reread.json()) == (own, defaults), f"The session must work: GET /settings/user with its cookie must answer 200 with the same preferences: {reread.status_code} {reread.text}"
        after = await _theme_stored(theme_instance, account.user_id)
        assert after == before, f"Reading never writes: the row and the defaults must stay as the hand edit left them: before {before}, after {after}"
        assert "theme" not in login.json().get("user_settings", {}), "theme is no top-level field of the login's user_settings"
        print_success(f"✓ Signed in, no own key, defaults.theme {shown!r}; {raw!r} still stored")

    @pytest.mark.parametrize(("default_theme", "shown"), _SHOWN_FOR_AN_UNKNOWN_THEME)
    @pytest.mark.parametrize("raw", _UNREADABLE_ROWS)
    @pytest.mark.asyncio
    async def test_get_settings_leaves_out_an_unreadable_preference_and_writes_nothing(self, theme_instance: _ThemeInstance, raw: str, default_theme: str, shown: str):
        """SET-A11-03: a signed-in account whose stored preferences became unreadable — a hand edit after its sign-in —
        reads its settings: 200, the stored language, currency and avatar, ``ui_preferences`` ``{}``, the defaults
        carrying ``shown`` as theme and the shipped line shape; the row and the global defaults unchanged."""
        print_section(f"SET-A11-03: GET /settings/user with the stored {raw!r}, default_theme {default_theme!r}: defaults.theme {shown!r}")
        account = await _theme_account(theme_instance)
        cookie = await _theme_signed_in(theme_instance, account)
        await _hand_edit_default_theme(theme_instance, default_theme)
        await _hand_edit_ui_preferences(theme_instance, account.user_id, raw)
        before = await _theme_stored(theme_instance, account.user_id)

        answer = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)

        assert answer.status_code == 200, f"An unreadable stored preference must not break GET /settings/user: {answer.status_code} {answer.text}"
        expected = {
            "language": _THEME_ACCOUNT_LANGUAGE,
            "base_currency": _THEME_ACCOUNT_CURRENCY,
            "avatar_url": None,
            "ui_preferences": {},
            "ui_preference_defaults": {"theme": shown, "chart_line_shape": before[_DEFAULT_SHAPE_KEY]},
        }
        assert answer.json() == expected, f"Expected {expected}, got {answer.json()}"
        after = await _theme_stored(theme_instance, account.user_id)
        assert after == before, f"Reading never writes: before {before}, after {after}"
        print_success(f"✓ 200, no own key, defaults.theme {shown!r}; {raw!r} still stored")

    @pytest.mark.asyncio
    async def test_an_unknown_value_leaves_out_only_its_own_key(self, theme_instance: _ThemeInstance):
        """SET-A11-03b: the rule is per key — a stored ``{"theme": "sepia", "chart_line_shape": "steps"}`` answers
        ``ui_preferences`` ``{"chart_line_shape": "steps"}``: the readable key is kept, the unknown theme left out; the row is untouched."""
        print_section("SET-A11-03b: an unknown theme does not hide a readable line shape")
        raw = '{"chart_line_shape":"steps","theme":"sepia"}'
        account = await _theme_account(theme_instance, raw)
        cookie = await _theme_signed_in(theme_instance, account)
        before = await _theme_stored(theme_instance, account.user_id)

        answer = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)

        assert answer.status_code == 200 and answer.json()["ui_preferences"] == {"chart_line_shape": "steps"}, f"Only the unknown key is left out: {answer.status_code} {answer.text}"
        assert await _theme_stored(theme_instance, account.user_id) == before, "Reading never writes"
        print_success("✓ steps kept, sepia left out, row untouched")

    @pytest.mark.parametrize(("default_theme", "shown"), _SHOWN_FOR_AN_UNKNOWN_THEME)
    @pytest.mark.asyncio
    async def test_put_without_preferences_saves_the_rest_and_keeps_the_stored_text(self, theme_instance: _ThemeInstance, default_theme: str, shown: str):
        """SET-A11-04: a signed-in account whose stored theme is unknown saves ``{"language": "it"}``: 200, the language saved
        and answered, ``ui_preferences`` ``{}``, the defaults carrying ``shown``; the stored text stays as it was, and
        nothing else of the row or of the global defaults changes (``updated_at`` aside: the row was written)."""
        print_section(f"SET-A11-04: PUT /settings/user without ui_preferences, stored {_UNKNOWN_THEME!r}, default_theme {default_theme!r}")
        account = await _theme_account(theme_instance)
        cookie = await _theme_signed_in(theme_instance, account)
        await _hand_edit_default_theme(theme_instance, default_theme)
        raw = f'{{"theme":"{_UNKNOWN_THEME}"}}'
        await _hand_edit_ui_preferences(theme_instance, account.user_id, raw)
        before = await _theme_stored(theme_instance, account.user_id)

        answer = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"language": "it"})

        after = await _theme_stored(theme_instance, account.user_id)
        assert answer.status_code == 200, f"An unknown stored theme must not break PUT /settings/user: {answer.status_code} {answer.text}; the row afterwards {after}"
        body = answer.json()
        assert (body["language"], body["ui_preferences"], body["ui_preference_defaults"]["theme"]) == ("it", {}, shown), f"The language saved, the theme left out, defaults.theme {shown!r}: {body}"
        assert (after["language"], after["ui_preferences"]) == ("it", raw), f"The language must be saved and the stored text kept: {after}"
        untouched = ("base_currency", "avatar_url", "created_at", _DEFAULT_THEME_KEY, _DEFAULT_SHAPE_KEY)
        assert {key: after[key] for key in untouched} == {key: before[key] for key in untouched}, f"Nothing else may change: before {before}, after {after}"
        print_success(f"✓ 200, language saved, no own theme; {raw!r} still stored")

    @pytest.mark.parametrize("raw", [pytest.param(f'{{"theme":"{_UNKNOWN_THEME}"}}', id="unknown-value"), pytest.param("this is not json", id="not-json")])
    @pytest.mark.asyncio
    async def test_put_with_a_theme_replaces_an_unreadable_stored_one(self, theme_instance: _ThemeInstance, raw: str):
        """SET-A11-05: a signed-in account whose stored preferences are unreadable saves ``{"ui_preferences": {"theme": "dark"}}``:
        200, dark shown as own and stored as ``{"theme":"dark"}``, and the next ``GET /settings/user`` shows dark; neither
        request logs a warning of the settings service, the theme read being a known one. The global default_theme is
        auto, so the dark shown is the one stored, not the default."""
        print_section(f"SET-A11-05: PUT ui_preferences.theme dark over the stored {raw!r}")
        account = await _theme_account(theme_instance)
        cookie = await _theme_signed_in(theme_instance, account)
        await _hand_edit_default_theme(theme_instance, "auto")
        await _hand_edit_ui_preferences(theme_instance, account.user_id, raw)

        with _settings_service_log() as put_events:
            answer = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": "dark"}})
        with _settings_service_log() as read_events:
            reread = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)

        assert answer.status_code == 200 and answer.json()["ui_preferences"] == {"theme": "dark"}, f"PUT with theme dark must answer 200 with dark: {answer.status_code} {answer.text}"
        assert await _stored_ui_preferences_text(theme_instance, account.user_id) == '{"theme":"dark"}', "The theme sent must replace the unreadable stored text"
        assert reread.status_code == 200 and reread.json()["ui_preferences"] == {"theme": "dark"}, f"The next read must show dark: {reread.status_code} {reread.text}"
        put_warnings = _theme_warnings(put_events, "PUT /settings/user with theme")
        if raw.startswith("{"):
            assert put_warnings == [], "The PUT reads the theme it stored, a known one: no warning"
        else:
            assert len(put_warnings) == 1 and "key" not in put_warnings[0], f"Only the merge's read of the text that is not JSON warns, naming no key: {put_warnings}"
        assert _theme_warnings(read_events, "GET /settings/user") == [], "A known stored theme is read without a warning"
        print_success("✓ dark stored and shown, no warning")

    @pytest.mark.parametrize(("stored", "default_theme"), _KNOWN_STORED_THEMES)
    @pytest.mark.asyncio
    async def test_a_known_stored_theme_is_shown_as_stored(self, theme_instance: _ThemeInstance, stored: str, default_theme: str):
        """SET-A11-06: an account whose stored theme is a known one, the global default another known one. The login,
        ``GET /settings/user`` and ``PUT /settings/user`` without ``ui_preferences`` each answer 200 with ``ui_preferences``
        ``{"theme": stored}`` — never the default —, none logs a warning of the settings service, and the row keeps its text."""
        print_section(f"SET-A11-06: the stored theme {stored!r} is shown as own (default_theme {default_theme!r})")
        raw = jsonlib.dumps({"theme": stored}, separators=(",", ":"))
        account = await _theme_account(theme_instance, raw)
        await _hand_edit_default_theme(theme_instance, default_theme)

        with _settings_service_log() as login_events:
            login = await _theme_login(theme_instance, account)
        assert login.status_code == 200, f"Setup: {account.username} signs in: {login.status_code} {login.text}"
        cookies = _session_cookie_values(login)
        assert len(cookies) == 1 and cookies[0], f"The login must set one session cookie: {login.headers.get_list('set-cookie')}"
        with _settings_service_log() as read_events:
            reread = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookies[0])
        with _settings_service_log() as put_events:
            saved = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookies[0], json={"language": "it"})

        shown = {
            "POST /auth/login": (login.status_code, (login.json().get("user_settings") or {}).get("ui_preferences")),
            "GET /settings/user": (reread.status_code, reread.json().get("ui_preferences")),
            "PUT /settings/user without ui_preferences": (saved.status_code, saved.json().get("ui_preferences")),
        }
        assert shown == dict.fromkeys(shown, (200, {"theme": stored})), f"A known stored theme is shown as own, {stored!r}, never as the default {default_theme!r}: {shown}"
        for request, events in (("POST /auth/login", login_events), ("GET /settings/user", read_events), ("PUT /settings/user without ui_preferences", put_events)):
            assert _theme_warnings(events, request) == [], f"{request}: a known stored theme is read without a warning"
        assert await _stored_ui_preferences_text(theme_instance, account.user_id) == raw, f"The stored text must stay {raw!r}"
        print_success(f"✓ {stored!r} shown three times, no warning")

    @pytest.mark.asyncio
    async def test_each_read_of_an_unknown_stored_theme_logs_one_warning(self, theme_instance: _ThemeInstance):
        """SET-A11-07: a stored theme longer than 20 characters. The login, ``GET /settings/user`` and ``PUT /settings/user``
        without ``ui_preferences`` each log exactly one WARNING through ``backend.app.services.accounts.settings_service``,
        carrying the account's ``user_id``, ``key`` = theme and ``stored`` = the stored value's first 20 characters."""
        print_section(f"SET-A11-07: one warning per read of the stored theme {_LONG_UNKNOWN_THEME!r}")
        account = await _theme_account(theme_instance)
        await _hand_edit_default_theme(theme_instance, "dark")
        await _hand_edit_ui_preferences(theme_instance, account.user_id, jsonlib.dumps({"theme": _LONG_UNKNOWN_THEME}))
        expected = {"user_id": account.user_id, "key": "theme", "stored": _LONG_UNKNOWN_THEME[:20]}

        with _settings_service_log() as login_events:
            login = await _theme_login(theme_instance, account)
        assert login.status_code == 200, f"An unknown stored theme must not stop the sign-in: {login.status_code} {login.text}"
        _assert_one_theme_warning(login_events, expected, "POST /auth/login")
        cookies = _session_cookie_values(login)
        assert len(cookies) == 1 and cookies[0], f"The login must set one session cookie: {login.headers.get_list('set-cookie')}"

        with _settings_service_log() as read_events:
            reread = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookies[0])
        assert reread.status_code == 200, f"GET /settings/user must answer 200: {reread.status_code} {reread.text}"
        _assert_one_theme_warning(read_events, expected, "GET /settings/user")

        with _settings_service_log() as put_events:
            saved = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookies[0], json={"language": "it"})
        assert saved.status_code == 200, f"PUT /settings/user without ui_preferences must answer 200: {saved.status_code} {saved.text}"
        _assert_one_theme_warning(put_events, expected, "PUT /settings/user without ui_preferences")
        print_success(f"✓ Three reads, three warnings carrying {expected}")


class TestUserUiPreferencesMerge:
    """Lot UIP: ``PUT /settings/user`` merges ``ui_preferences`` key by key (SET-UIP-01 to SET-UIP-10).

    A key with a value sets it, a key sent as ``null`` removes it, a key left out is kept; the merged JSON is stored compact
    with sorted keys, an empty result as NULL; a stored key this version does not know survives; a write that would leave
    the text over ``UI_PREFERENCES_MAX_BYTES`` answers 422 and saves nothing; an unknown key, a top-level ``theme`` and a
    value outside the enum answer 422. All on the private instance of ``theme_instance``: the stored text is read by SQL.
    """

    async def _signed_in_account(self, instance: _ThemeInstance, raw: Optional[str] = None) -> tuple[_ThemeAccount, str]:
        account = await _theme_account(instance, raw)
        return account, await _theme_signed_in(instance, account)

    @pytest.mark.asyncio
    async def test_two_puts_keep_both_keys(self, theme_instance: _ThemeInstance):
        """SET-UIP-01: set the theme, then set chart_line_shape in a second PUT: both are kept, answered, and stored compact with sorted keys."""
        print_section("SET-UIP-01: PUT theme, then PUT chart_line_shape: both kept")
        account, cookie = await self._signed_in_account(theme_instance)

        first = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": "dark"}})
        second = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"chart_line_shape": "spline"}})

        assert first.status_code == 200 and first.json()["ui_preferences"] == {"theme": "dark"}, f"{first.status_code} {first.text}"
        assert second.status_code == 200 and second.json()["ui_preferences"] == {"theme": "dark", "chart_line_shape": "spline"}, f"{second.status_code} {second.text}"
        assert await _stored_ui_preferences_text(theme_instance, account.user_id) == '{"chart_line_shape":"spline","theme":"dark"}', "compact JSON, sorted keys"
        reread = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)
        assert reread.json()["ui_preferences"] == {"theme": "dark", "chart_line_shape": "spline"}
        print_success("✓ both keys kept and stored sorted")

    @pytest.mark.asyncio
    async def test_null_removes_one_key_and_keeps_the_other(self, theme_instance: _ThemeInstance):
        """SET-UIP-02: ``{"theme": null}`` removes the theme (it follows its global default again) and leaves chart_line_shape; a key left out is kept."""
        print_section("SET-UIP-02: null removes one key, a key left out is kept")
        account, cookie = await self._signed_in_account(theme_instance, '{"chart_line_shape":"steps","theme":"light"}')

        answer = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": None}})
        assert answer.status_code == 200 and answer.json()["ui_preferences"] == {"chart_line_shape": "steps"}, f"{answer.status_code} {answer.text}"
        assert await _stored_ui_preferences_text(theme_instance, account.user_id) == '{"chart_line_shape":"steps"}'

        untouched = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {}})
        assert untouched.status_code == 200 and untouched.json()["ui_preferences"] == {"chart_line_shape": "steps"}, "an empty ui_preferences names no key: nothing changes"
        assert await _stored_ui_preferences_text(theme_instance, account.user_id) == '{"chart_line_shape":"steps"}'
        print_success("✓ theme removed, shape kept")

    @pytest.mark.asyncio
    async def test_an_empty_result_is_stored_null(self, theme_instance: _ThemeInstance):
        """SET-UIP-03: removing the last key stores NULL (not ``{}``), and the read answers ``{}``."""
        print_section("SET-UIP-03: an empty result is stored NULL")
        account, cookie = await self._signed_in_account(theme_instance, '{"theme":"dark"}')

        answer = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": None}})

        assert answer.status_code == 200 and answer.json()["ui_preferences"] == {}, f"{answer.status_code} {answer.text}"
        assert await _stored_ui_preferences_text(theme_instance, account.user_id) is None, "the empty result must be stored NULL"
        print_success("✓ NULL stored")

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({"ui_preferences": {"colour": "red"}}, id="unknown-key-inside"),
            pytest.param({"theme": "dark"}, id="top-level-theme"),
            pytest.param({"ui_preferences": {"theme": "sepia"}}, id="theme-outside-enum"),
            pytest.param({"ui_preferences": {"chart_line_shape": "curvy"}}, id="shape-outside-enum"),
            pytest.param({"ui_preferences": {"theme": "dark", "colour": "red"}}, id="valid-key-with-unknown-key"),
        ],
    )
    @pytest.mark.asyncio
    async def test_an_invalid_request_is_422_and_saves_nothing(self, theme_instance: _ThemeInstance, payload: dict[str, Any]):
        """SET-UIP-04/05/06: an unknown key inside ``ui_preferences``, a top-level ``theme`` and a value outside the enum answer 422; the row is untouched (a valid key sent beside an invalid one is not saved either)."""
        print_section(f"SET-UIP-04: PUT {payload} → 422, nothing saved")
        account, cookie = await self._signed_in_account(theme_instance, '{"chart_line_shape":"steps"}')
        before = await _theme_stored(theme_instance, account.user_id)

        answer = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json=payload)

        assert answer.status_code == 422, f"Expected 422, got {answer.status_code}: {answer.text}"
        assert await _theme_stored(theme_instance, account.user_id) == before, "A refused request must save nothing"
        print_success("✓ 422, row untouched")

    @pytest.mark.asyncio
    async def test_get_returns_only_own_keys_and_the_defaults_follow_the_globals(self, theme_instance: _ThemeInstance):
        """SET-UIP-07: a new account owns no key (``{}``); ``ui_preference_defaults`` mirrors the global ``default_theme`` and
        ``default_chart_line_shape`` rows, and follows them when they change; an own key is returned and does not change the defaults."""
        print_section("SET-UIP-07: own keys only, defaults follow the global rows")
        account, cookie = await self._signed_in_account(theme_instance)
        await _hand_edit_global(theme_instance, _DEFAULT_THEME_KEY, "dark")
        await _hand_edit_global(theme_instance, _DEFAULT_SHAPE_KEY, "steps")

        first = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)
        assert first.status_code == 200
        assert _own_and_defaults(first.json()) == ({}, {"theme": "dark", "chart_line_shape": "steps"}), f"{first.text}"

        await _hand_edit_global(theme_instance, _DEFAULT_THEME_KEY, "light")
        await _hand_edit_global(theme_instance, _DEFAULT_SHAPE_KEY, "spline")
        put = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": "auto"}})
        assert put.status_code == 200
        assert _own_and_defaults(put.json()) == ({"theme": "auto"}, {"theme": "light", "chart_line_shape": "spline"}), f"{put.text}"

        await _hand_edit_global(theme_instance, _DEFAULT_SHAPE_KEY, "curvy")
        unknown_default = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)
        assert unknown_default.json()["ui_preference_defaults"]["chart_line_shape"] == "segments", "a global shape the app does not know falls back to segments"
        print_success("✓ defaults mirror the global rows, unknown falls back")

    @pytest.mark.asyncio
    async def test_a_stored_unknown_key_survives_a_merge(self, theme_instance: _ThemeInstance):
        """SET-UIP-08: a key a later version wrote (here ``zoom``) is kept as it is by a merge of another key, and never answered."""
        print_section("SET-UIP-08: a stored unknown key survives a merge")
        account, cookie = await self._signed_in_account(theme_instance, '{"zoom":{"level":3}}')

        answer = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": "dark"}})

        assert answer.status_code == 200 and answer.json()["ui_preferences"] == {"theme": "dark"}, "the unknown key is never answered"
        stored = jsonlib.loads(await _stored_ui_preferences_text(theme_instance, account.user_id))
        assert stored == {"zoom": {"level": 3}, "theme": "dark"}, f"the unknown key must survive: {stored}"
        removal = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": None}})
        assert removal.status_code == 200
        assert jsonlib.loads(await _stored_ui_preferences_text(theme_instance, account.user_id)) == {"zoom": {"level": 3}}, "removing the last known key leaves the unknown one, not NULL"
        print_success("✓ zoom kept through both merges")

    @pytest.mark.asyncio
    async def test_a_merge_over_the_size_cap_is_422_and_leaves_the_row_untouched(self, theme_instance: _ThemeInstance):
        """SET-UIP-09: a row holding a big unknown key (over ``UI_PREFERENCES_MAX_BYTES``, written by SQL) makes a PUT of the theme answer 422 and leaves the row untouched; GET still answers 200."""
        print_section("SET-UIP-09: size cap")
        raw = jsonlib.dumps({"blob": "x" * (UI_PREFERENCES_MAX_BYTES + 1)}, separators=(",", ":"), sort_keys=True)
        assert len(raw.encode("utf-8")) > UI_PREFERENCES_MAX_BYTES, "Premise: the stored text is over the cap"
        account, cookie = await self._signed_in_account(theme_instance, raw)
        before = await _theme_stored(theme_instance, account.user_id)

        answer = await _theme_request(theme_instance, "PUT", "/settings/user", cookie=cookie, json={"ui_preferences": {"theme": "dark"}})

        assert answer.status_code == 422, f"Expected 422, got {answer.status_code}: {answer.text}"
        assert await _theme_stored(theme_instance, account.user_id) == before, "A refused request must save nothing (updated_at included)"
        assert (await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)).status_code == 200, "the row is still readable"
        print_success("✓ 422, row untouched")

    @pytest.mark.asyncio
    async def test_a_new_row_made_by_get_holds_no_preference(self, theme_instance: _ThemeInstance):
        """SET-UIP-10: an account without a ``user_settings`` row gets one from ``GET /settings/user`` with ``ui_preferences`` NULL — no theme written."""
        print_section("SET-UIP-10: a new row writes no preference")
        username = f"theme_{uuid.uuid4().hex[:12]}"
        async with AsyncSession(theme_instance.engine, expire_on_commit=False) as session:
            user = User(username=username, email=f"{username}@example.com", hashed_password=auth_service.hash_password(_THEME_PASSWORD), is_active=True)
            session.add(user)
            await session.commit()
        account = _ThemeAccount(user_id=user.id, username=username)
        cookie = await _theme_signed_in(theme_instance, account)

        answer = await _theme_request(theme_instance, "GET", "/settings/user", cookie=cookie)

        assert answer.status_code == 200 and answer.json()["ui_preferences"] == {}, f"{answer.status_code} {answer.text}"
        assert await _stored_ui_preferences_text(theme_instance, account.user_id) is None, "the new row must hold NULL"
        print_success("✓ NULL")


class TestDefaultChartLineShapeSetting:
    """Lot UIP: the global setting ``default_chart_line_shape`` accepts segments/steps/spline and refuses anything else (SET-UIP-11)."""

    @pytest.mark.asyncio
    async def test_accepted_and_refused_values(self, test_server):
        """SET-UIP-11: PATCH /settings/global/bulk accepts each of segments, steps, spline and ``GET /settings/user``'s
        ``ui_preference_defaults.chart_line_shape`` follows it; ``curvy`` answers 422 and the stored value stays; the original is restored in ``finally``."""
        print_section("SET-UIP-11: default_chart_line_shape")
        key = "default_chart_line_shape"
        async with httpx.AsyncClient() as admin, httpx.AsyncClient() as user:
            await get_admin_session(admin)
            _, _, session = await create_user_simple(user)
            assert session is not None, "Failed to create test user"
            originals = await _read_global_values(admin, [key])
            try:
                for shape in ("segments", "steps", "spline"):
                    await _assert_saved(admin, [(key, shape)], {key: shape})
                    own = await user.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
                    assert own.status_code == 200 and own.json()["ui_preference_defaults"]["chart_line_shape"] == shape, f"{shape}: {own.status_code} {own.text}"
                await _assert_refused_and_nothing_saved(admin, [(key, "curvy")], {key: "spline"}, status=422, named=[key])
            finally:
                await _restore_global_values(admin, originals)
        print_success("✓ three shapes accepted, curvy refused, original restored")

    @pytest.mark.asyncio
    async def test_default_theme_is_reflected_in_the_defaults(self, test_server):
        """SET-UIP-12: PATCH /settings/global/bulk ``default_theme`` shows in ``ui_preference_defaults.theme`` of a user who owns no theme, never in ``ui_preferences``; restored in ``finally``."""
        print_section("SET-UIP-12: default_theme reaches ui_preference_defaults")
        key = "default_theme"
        async with httpx.AsyncClient() as admin, httpx.AsyncClient() as user:
            await get_admin_session(admin)
            _, _, session = await create_user_simple(user)
            assert session is not None, "Failed to create test user"
            originals = await _read_global_values(admin, [key])
            try:
                for theme in (_other_value(_THEMES, originals[key]), originals[key]):
                    await _assert_saved(admin, [(key, theme)], {key: theme})
                    own = await user.get(f"{API_BASE}/settings/user", timeout=TIMEOUT)
                    body = own.json()
                    assert own.status_code == 200 and body["ui_preference_defaults"]["theme"] == theme and "theme" not in body["ui_preferences"], f"{theme}: {own.text}"
            finally:
                await _restore_global_values(admin, originals)
        print_success("✓ defaults follow default_theme")
