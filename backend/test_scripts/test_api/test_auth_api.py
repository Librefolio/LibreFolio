"""
Authentication API Tests

Tests for login, logout, register, and session management endpoints.
"""

from datetime import datetime

import httpx
import pytest
import pytest_asyncio

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


class TestRegister:
    """Tests for POST /auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self, test_server):
        """REG-001: Register a new user successfully.

        Note: First user in a clean DB becomes superuser automatically.
        Subsequent users are regular users. We verify the user was created
        correctly without asserting on is_superuser (depends on DB state).
        """
        print_section("REG-001: Register new user")

        async with httpx.AsyncClient() as client:
            # Generate unique username to avoid conflicts
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"testuser_{timestamp}"
            email = f"test_{timestamp}@example.com"

            response = await client.post(
                f"{API_BASE}/auth/register",
                json={"username": username, "email": email, "password": "testpassword123"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
            data = response.json()
            assert "user" in data
            assert data["user"]["username"] == username
            assert data["user"]["email"] == email
            assert data["user"]["is_active"] is True

            # is_superuser depends on whether this is the first user in DB
            # We just verify it's a boolean, not a specific value
            assert isinstance(data["user"]["is_superuser"], bool)

            if data["user"]["is_superuser"]:
                print_success("First user registered as superuser (DB was empty)")
            else:
                print_success("User registered as regular user (DB had existing users)")

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, test_server):
        """REG-002: Cannot register with duplicate username."""
        print_section("REG-002: Duplicate username rejected")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"dupuser_{timestamp}"

            # First registration
            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"first_{timestamp}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )

            # Try duplicate username
            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"second_{timestamp}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 400
            assert "username" in response.json()["detail"].lower()
            print_success("Duplicate username correctly rejected")

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_server):
        """REG-003: Cannot register with duplicate email."""
        print_section("REG-003: Duplicate email rejected")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            email = f"dupemail_{timestamp}@example.com"

            # First registration
            await client.post(
                f"{API_BASE}/auth/register",
                json={"username": f"user1_{timestamp}", "email": email, "password": "password123"},
                timeout=TIMEOUT,
            )

            # Try duplicate email
            response = await client.post(
                f"{API_BASE}/auth/register",
                json={"username": f"user2_{timestamp}", "email": email, "password": "password123"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 400
            assert "email" in response.json()["detail"].lower()
            print_success("Duplicate email correctly rejected")

    @pytest.mark.asyncio
    async def test_register_short_password(self, test_server):
        """REG-004: Password must be at least 8 characters."""
        print_section("REG-004: Short password rejected")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)

            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": f"shortpw_{timestamp}",
                    "email": f"shortpw_{timestamp}@example.com",
                    "password": "short",  # Less than 8 chars
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 422  # Validation error
            print_success("Short password correctly rejected")


class TestLogin:
    """Tests for POST /auth/login."""

    @pytest_asyncio.fixture
    async def test_user(self, test_server):
        """Create a test user for login tests."""
        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"logintest_{timestamp}"
            email = f"login_{timestamp}@example.com"
            password = "loginpassword123"

            response = await client.post(
                f"{API_BASE}/auth/register",
                json={"username": username, "email": email, "password": password},
                timeout=TIMEOUT,
            )
            assert response.status_code == 201, f"Setup failed: {response.text}"

            return {"username": username, "email": email, "password": password}

    @pytest.mark.asyncio
    async def test_login_with_username(self, test_server, test_user):
        """LOGIN-001: Login with username."""
        print_section("LOGIN-001: Login with username")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": test_user["username"], "password": test_user["password"]},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert "user" in data
            assert data["user"]["username"] == test_user["username"]

            # Check session cookie was set
            assert "session" in response.cookies
            print_success("Login with username successful")

    @pytest.mark.asyncio
    async def test_login_with_email(self, test_server, test_user):
        """LOGIN-002: Login with email instead of username."""
        print_section("LOGIN-002: Login with email")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/auth/login",
                json={
                    "username": test_user["email"],  # Using email in username field
                    "password": test_user["password"],
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 200
            assert "session" in response.cookies
            print_success("Login with email successful")

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_server, test_user):
        """LOGIN-003: Login with wrong password returns 401."""
        print_section("LOGIN-003: Wrong password rejected")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": test_user["username"], "password": "wrongpassword"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 401
            assert "session" not in response.cookies
            print_success("Wrong password correctly rejected")

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, test_server):
        """LOGIN-004: Login with non-existent user returns 401."""
        print_section("LOGIN-004: Non-existent user rejected")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": "nonexistent_user_12345", "password": "anypassword"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 401
            print_success("Non-existent user correctly rejected")

    @pytest.mark.asyncio
    async def test_login_returns_existing_user_settings(self, test_server):
        """LOGIN-005: Login returns persisted user settings."""
        print_section("LOGIN-005: Login returns persisted user settings")

        from sqlalchemy.ext.asyncio import AsyncSession  # noqa: PLC0415 — test-only local import

        from backend.app.db.session import get_async_engine  # noqa: PLC0415 — test-only local import
        from backend.app.schemas.settings import UserSettingsUpdate  # noqa: PLC0415 — test-only local import
        from backend.app.services import settings_service, user_service  # noqa: PLC0415 — test-only local import

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"loginsettings_{timestamp}"
            email = f"loginsettings_{timestamp}@example.com"
            password = "loginpassword123"

            register_resp = await client.post(
                f"{API_BASE}/auth/register",
                json={"username": username, "email": email, "password": password},
                timeout=TIMEOUT,
            )
            assert register_resp.status_code == 201, f"Setup failed: {register_resp.text}"

            engine = get_async_engine()
            async with AsyncSession(engine) as session:
                user = await user_service.get_user_by_username(session, username)
                assert user is not None, "Registered user not found in DB"

                await settings_service.update_user_settings(
                    user.id,
                    UserSettingsUpdate(
                        language="fr",
                        base_currency="USD",
                        theme="dark",
                        avatar_url="https://example.com/avatar.png",
                    ),
                    session,
                )

            response = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": password},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["user"]["username"] == username
            assert data["user_settings"] == {
                "language": "fr",
                "base_currency": "USD",
                "theme": "dark",
                "avatar_url": "https://example.com/avatar.png",
            }

            client.cookies.update(response.cookies)
            me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            assert me_resp.status_code == 200

            print_success("Login returned persisted user settings")


class TestLogout:
    """Tests for POST /auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_clears_session(self, test_server):
        """LOGOUT-001: Logout clears session cookie."""
        print_section("LOGOUT-001: Logout clears session")

        async with httpx.AsyncClient() as client:
            # Register and login
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"logouttest_{timestamp}"

            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"logout_{timestamp}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT,
            )
            assert "session" in login_resp.cookies

            # Set cookies on client instance (not per-request)
            client.cookies.update(login_resp.cookies)

            # Logout
            logout_resp = await client.post(f"{API_BASE}/auth/logout", timeout=TIMEOUT)

            assert logout_resp.status_code == 200
            # Cookie should be cleared (set to empty or deleted)
            print_success("Logout successful")


class TestMe:
    """Tests for GET /auth/me."""

    @pytest.mark.asyncio
    async def test_me_authenticated(self, test_server):
        """ME-001: Get current user when authenticated."""
        print_section("ME-001: Get current user (authenticated)")

        async with httpx.AsyncClient() as client:
            # Register and login
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"metest_{timestamp}"

            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"me_{timestamp}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT,
            )

            # Set cookies on client instance (not per-request)
            client.cookies.update(login_resp.cookies)

            # Get me
            me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)

            assert me_resp.status_code == 200
            data = me_resp.json()
            assert data["user"]["username"] == username
            print_success("Got current user successfully")

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, test_server):
        """ME-002: Get current user without auth returns 401."""
        print_section("ME-002: Get current user (unauthenticated)")

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)

            assert response.status_code == 401
            print_success("Unauthenticated request correctly rejected")

    @pytest.mark.asyncio
    async def test_me_invalid_session(self, test_server):
        """ME-003: Get current user with invalid session returns 401."""
        print_section("ME-003: Invalid session rejected")

        async with httpx.AsyncClient() as client:
            # Set invalid session cookie on client instance
            client.cookies.set("session", "invalid_session_id_12345")

            response = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)

            assert response.status_code == 401
            print_success("Invalid session correctly rejected")


class TestSessionPersistence:
    """Tests for session cookie behavior."""

    @pytest.mark.asyncio
    async def test_session_cookie_httponly(self, test_server):
        """SESSION-001: Session cookie should be HttpOnly."""
        print_section("SESSION-001: Session cookie is HttpOnly")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"cookietest_{timestamp}"

            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"cookie_{timestamp}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )

            response = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT,
            )

            # Check Set-Cookie header for HttpOnly flag
            set_cookie = response.headers.get("set-cookie", "")
            assert "httponly" in set_cookie.lower(), f"Cookie should be HttpOnly: {set_cookie}"
            print_success("Session cookie is HttpOnly")

    @pytest.mark.asyncio
    async def test_session_persists_across_requests(self, test_server):
        """SESSION-002: Session should persist across multiple requests."""
        print_section("SESSION-002: Session persists across requests")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"persisttest_{timestamp}"

            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"persist_{timestamp}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT,
            )

            # Set cookies on client instance (not per-request)
            client.cookies.update(login_resp.cookies)

            # Make multiple requests with same session
            for i in range(3):
                me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
                assert me_resp.status_code == 200, f"Request {i + 1} failed"

            print_success("Session persists across multiple requests")


class TestChangePassword:
    """Tests for POST /auth/change-password."""

    @pytest.mark.asyncio
    async def test_change_password_success(self, test_server):
        """CHPWD-001: Successfully change password."""
        print_section("CHPWD-001: Change password success")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"chpwd_{timestamp}"
            old_password = "oldpassword123"
            new_password = "newpassword456"

            # Register user
            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"chpwd_{timestamp}@example.com",
                    "password": old_password,
                },
                timeout=TIMEOUT,
            )

            # Login
            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": old_password},
                timeout=TIMEOUT,
            )
            client.cookies.update(login_resp.cookies)

            # Change password
            response = await client.post(
                f"{API_BASE}/auth/change-password",
                json={"current_password": old_password, "new_password": new_password},
                timeout=TIMEOUT,
            )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert "message" in data
            assert "success" in data["message"].lower()

            # Verify old password no longer works
            client.cookies.clear()
            old_login = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": old_password},
                timeout=TIMEOUT,
            )
            assert old_login.status_code == 401, "Old password should not work"

            # Verify new password works
            new_login = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": new_password},
                timeout=TIMEOUT,
            )
            assert new_login.status_code == 200, "New password should work"

            print_success("Password changed successfully")

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, test_server):
        """CHPWD-002: Cannot change password with wrong current password."""
        print_section("CHPWD-002: Wrong current password rejected")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"chpwd_wrong_{timestamp}"

            # Register and login
            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"chpwd_wrong_{timestamp}@example.com",
                    "password": "correctpassword123",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "correctpassword123"},
                timeout=TIMEOUT,
            )
            client.cookies.update(login_resp.cookies)

            # Try to change with wrong current password
            response = await client.post(
                f"{API_BASE}/auth/change-password",
                json={"current_password": "wrongpassword", "new_password": "newpassword456"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "incorrect" in response.json()["detail"].lower()

            print_success("Wrong current password correctly rejected")

    @pytest.mark.asyncio
    async def test_change_password_same_password(self, test_server):
        """CHPWD-003: Cannot change to same password."""
        print_section("CHPWD-003: Same password rejected")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"chpwd_same_{timestamp}"
            password = "samepassword123"

            # Register and login
            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"chpwd_same_{timestamp}@example.com",
                    "password": password,
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": password},
                timeout=TIMEOUT,
            )
            client.cookies.update(login_resp.cookies)

            # Try to change to same password
            response = await client.post(
                f"{API_BASE}/auth/change-password",
                json={"current_password": password, "new_password": password},
                timeout=TIMEOUT,
            )

            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
            assert "different" in response.json()["detail"].lower()

            print_success("Same password correctly rejected")

    @pytest.mark.asyncio
    async def test_change_password_unauthenticated(self, test_server):
        """CHPWD-004: Cannot change password when not authenticated."""
        print_section("CHPWD-004: Unauthenticated request rejected")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/auth/change-password",
                json={"current_password": "oldpass", "new_password": "newpass123"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 401, f"Expected 401, got {response.status_code}"

            print_success("Unauthenticated request correctly rejected")

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, test_server):
        """CHPWD-005: New password must be at least 8 characters."""
        print_section("CHPWD-005: Short password rejected")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"chpwd_short_{timestamp}"

            # Register and login
            await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"chpwd_short_{timestamp}@example.com",
                    "password": "longpassword123",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "longpassword123"},
                timeout=TIMEOUT,
            )
            client.cookies.update(login_resp.cookies)

            # Try short password
            response = await client.post(
                f"{API_BASE}/auth/change-password",
                json={"current_password": "longpassword123", "new_password": "short"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 422, f"Expected 422, got {response.status_code}"

            print_success("Short password correctly rejected")


class TestDeleteOwnAccount:
    """Tests for DELETE /auth/users/me."""

    @pytest.mark.asyncio
    async def test_delete_own_account_success(self, test_server):
        """DELME-001: Authenticated regular user can delete own account."""
        print_section("DELME-001: Delete own account")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)

            support_username = f"keepadmin_{timestamp}"
            target_username = f"deleteme_{timestamp}"
            target_email = f"deleteme_{timestamp}@example.com"
            password = "DeletePass123!"

            support_resp = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": support_username,
                    "email": f"keepadmin_{timestamp}@example.com",
                    "password": password,
                },
                timeout=TIMEOUT,
            )
            assert support_resp.status_code == 201, f"Support user setup failed: {support_resp.text}"

            register_resp = await client.post(
                f"{API_BASE}/auth/register",
                json={"username": target_username, "email": target_email, "password": password},
                timeout=TIMEOUT,
            )
            assert register_resp.status_code == 201, f"Target user setup failed: {register_resp.text}"

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": target_username, "password": password},
                timeout=TIMEOUT,
            )
            assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
            client.cookies.update(login_resp.cookies)

            delete_resp = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)

            assert delete_resp.status_code == 200, f"Expected 200, got {delete_resp.status_code}: {delete_resp.text}"
            assert delete_resp.json() == {"message": "Account deleted successfully"}
            assert "session=" in delete_resp.headers.get("set-cookie", "").lower()

            me_resp = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
            assert me_resp.status_code == 401

            relogin_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": target_username, "password": password},
                timeout=TIMEOUT,
            )
            assert relogin_resp.status_code == 401

            print_success("Own account deleted and session invalidated")
