"""
Profile Update API Tests

Tests for PUT /auth/profile endpoint.
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


async def create_and_login_user(client: httpx.AsyncClient) -> tuple[dict, httpx.AsyncClient]:
    """Helper: Create a unique user and login, return (user_data, client_with_cookies).

    Note: Returns a new client instance with cookies set to avoid deprecation warnings.
    """
    timestamp = int(datetime.now().timestamp() * 1000)
    username = f"profiletest_{timestamp}"
    email = f"profiletest_{timestamp}@example.com"
    password = "TestPass123!"

    # Register
    response = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert response.status_code == 201, f"Register failed: {response.text}"
    user_data = response.json()["user"]

    # Login
    response = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert response.status_code == 200, f"Login failed: {response.text}"

    # Create a new client with cookies set
    auth_client = httpx.AsyncClient(cookies=response.cookies)
    return user_data, auth_client


class TestUpdateProfile:
    """Tests for PUT /api/v1/auth/profile."""

    @pytest.mark.asyncio
    async def test_update_username(self, test_server):
        """PROF-001: Update username successfully."""
        print_section("PROF-001: Update username")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            timestamp = int(datetime.now().timestamp() * 1000)
            new_username = f"newuser_{timestamp}"

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={"username": new_username},
                    timeout=TIMEOUT,
                )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["user"]["username"] == new_username
            assert data["user"]["email"] == user_data["email"]  # unchanged
            assert data["message"] == "Profile updated successfully"
            print_success(f"Username updated to {new_username}")

    @pytest.mark.asyncio
    async def test_update_email(self, test_server):
        """PROF-002: Update email successfully."""
        print_section("PROF-002: Update email")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            timestamp = int(datetime.now().timestamp() * 1000)
            new_email = f"newemail_{timestamp}@example.com"

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={"email": new_email},
                    timeout=TIMEOUT,
                )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["user"]["email"] == new_email
            assert data["user"]["username"] == user_data["username"]  # unchanged
            print_success(f"Email updated to {new_email}")

    @pytest.mark.asyncio
    async def test_update_both(self, test_server):
        """PROF-003: Update both username and email."""
        print_section("PROF-003: Update username and email")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            timestamp = int(datetime.now().timestamp() * 1000)
            new_username = f"bothuser_{timestamp}"
            new_email = f"both_{timestamp}@example.com"

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={"username": new_username, "email": new_email},
                    timeout=TIMEOUT,
                )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["user"]["username"] == new_username
            assert data["user"]["email"] == new_email
            print_success(f"Both updated: {new_username}, {new_email}")

    @pytest.mark.asyncio
    async def test_no_changes(self, test_server):
        """PROF-004: Handle no changes gracefully."""
        print_section("PROF-004: No changes requested")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={},
                    timeout=TIMEOUT,
                )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["message"] == "No changes requested"
            print_success("No changes handled correctly")

    @pytest.mark.asyncio
    async def test_unauthenticated(self, test_server):
        """PROF-005: Reject unauthenticated requests."""
        print_section("PROF-005: Unauthenticated rejected")

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{API_BASE}/auth/profile",
                json={"username": "newname"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
            print_success("Unauthenticated request rejected")

    @pytest.mark.asyncio
    async def test_username_too_short(self, test_server):
        """PROF-006: Reject username too short."""
        print_section("PROF-006: Short username rejected")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={"username": "ab"},  # min 3 chars
                    timeout=TIMEOUT,
                )

            assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
            print_success("Short username validation works")

    @pytest.mark.asyncio
    async def test_invalid_email(self, test_server):
        """PROF-007: Reject invalid email format."""
        print_section("PROF-007: Invalid email rejected")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={"email": "not-an-email"},
                    timeout=TIMEOUT,
                )

            assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
            print_success("Invalid email validation works")

    @pytest.mark.asyncio
    async def test_username_taken(self, test_server):
        """PROF-008: Reject duplicate username."""
        print_section("PROF-008: Duplicate username rejected")

        async with httpx.AsyncClient() as client:
            # Create first user
            user1_data, auth_client1 = await create_and_login_user(client)

            # Create second user
            user2_data, auth_client2 = await create_and_login_user(client)

            # Try to change user2's username to user1's
            async with auth_client2:
                response = await auth_client2.put(
                    f"{API_BASE}/auth/profile",
                    json={"username": user1_data["username"]},
                    timeout=TIMEOUT,
                )

            # Clean up auth_client1
            await auth_client1.aclose()

            assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
            assert "already taken" in response.json()["detail"].lower()
            print_success("Duplicate username rejected")

    @pytest.mark.asyncio
    async def test_email_taken(self, test_server):
        """PROF-009: Reject duplicate email."""
        print_section("PROF-009: Duplicate email rejected")

        async with httpx.AsyncClient() as client:
            # Create first user
            user1_data, auth_client1 = await create_and_login_user(client)

            # Create second user
            user2_data, auth_client2 = await create_and_login_user(client)

            # Try to change user2's email to user1's
            async with auth_client2:
                response = await auth_client2.put(
                    f"{API_BASE}/auth/profile",
                    json={"email": user1_data["email"]},
                    timeout=TIMEOUT,
                )

            # Clean up auth_client1
            await auth_client1.aclose()

            assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
            assert "already registered" in response.json()["detail"].lower()
            print_success("Duplicate email rejected")


class TestDeleteAccount:
    """Tests for DELETE /api/v1/auth/users/me."""

    @pytest.mark.asyncio
    async def test_delete_own_account(self, test_server):
        """DEL-001: Successfully delete own account."""
        print_section("DEL-001: Delete own account")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)
            user_id = user_data["id"]

            async with auth_client:
                # Delete account
                response = await auth_client.delete(
                    f"{API_BASE}/auth/users/me",
                    timeout=TIMEOUT,
                )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["message"] == "Account deleted successfully"

            # Verify user can no longer authenticate
            async with httpx.AsyncClient() as verify_client:
                response = await verify_client.post(
                    f"{API_BASE}/auth/login",
                    json={"username": user_data["username"], "password": "TestPass123!"},
                    timeout=TIMEOUT,
                )
                # Should fail - user deleted
                assert response.status_code == 401, f"User should be deleted, got {response.status_code}"

            print_success(f"User {user_id} deleted successfully")

    @pytest.mark.asyncio
    async def test_delete_unauthenticated(self, test_server):
        """DEL-002: Reject delete without authentication."""
        print_section("DEL-002: Reject unauthenticated delete")

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{API_BASE}/auth/users/me",
                timeout=TIMEOUT,
            )

            assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"
            print_success("Unauthenticated delete rejected")

    @pytest.mark.asyncio
    async def test_session_invalidated_after_delete(self, test_server):
        """DEL-003: Session is invalidated after account deletion."""
        print_section("DEL-003: Session invalidated after delete")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            async with auth_client:
                # Delete account
                response = await auth_client.delete(
                    f"{API_BASE}/auth/users/me",
                    timeout=TIMEOUT,
                )
                assert response.status_code == 200

                # Try to use the same session
                response = await auth_client.get(
                    f"{API_BASE}/auth/me",
                    timeout=TIMEOUT,
                )
                # Should fail - session should be invalidated
                assert response.status_code == 401, f"Session should be invalid, got {response.status_code}"

            print_success("Session invalidated after account deletion")
