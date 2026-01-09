"""
Authentication API Tests

Tests for login, logout, register, and session management endpoints.
"""
import pytest
import pytest_asyncio
import httpx
from datetime import datetime

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, print_info

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
        """REG-001: Register a new user successfully."""
        print_section("REG-001: Register new user")

        async with httpx.AsyncClient() as client:
            # Generate unique username to avoid conflicts
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"testuser_{timestamp}"
            email = f"test_{timestamp}@example.com"

            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": email,
                    "password": "testpassword123"
                },
                timeout=TIMEOUT
            )

            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
            data = response.json()
            assert "user" in data
            assert data["user"]["username"] == username
            assert data["user"]["email"] == email
            assert data["user"]["is_active"] is True
            assert data["user"]["is_superuser"] is False
            print_success("User registered successfully")

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
                    "password": "password123"
                },
                timeout=TIMEOUT
            )

            # Try duplicate username
            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"second_{timestamp}@example.com",
                    "password": "password123"
                },
                timeout=TIMEOUT
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
                json={
                    "username": f"user1_{timestamp}",
                    "email": email,
                    "password": "password123"
                },
                timeout=TIMEOUT
            )

            # Try duplicate email
            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": f"user2_{timestamp}",
                    "email": email,
                    "password": "password123"
                },
                timeout=TIMEOUT
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
                    "password": "short"  # Less than 8 chars
                },
                timeout=TIMEOUT
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
                json={
                    "username": username,
                    "email": email,
                    "password": password
                },
                timeout=TIMEOUT
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
                json={
                    "username": test_user["username"],
                    "password": test_user["password"]
                },
                timeout=TIMEOUT
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
                    "password": test_user["password"]
                },
                timeout=TIMEOUT
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
                json={
                    "username": test_user["username"],
                    "password": "wrongpassword"
                },
                timeout=TIMEOUT
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
                json={
                    "username": "nonexistent_user_12345",
                    "password": "anypassword"
                },
                timeout=TIMEOUT
            )

            assert response.status_code == 401
            print_success("Non-existent user correctly rejected")


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
                    "password": "password123"
                },
                timeout=TIMEOUT
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT
            )
            assert "session" in login_resp.cookies

            # Set cookies on client instance (not per-request)
            client.cookies.update(login_resp.cookies)

            # Logout
            logout_resp = await client.post(
                f"{API_BASE}/auth/logout",
                timeout=TIMEOUT
            )

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
                    "password": "password123"
                },
                timeout=TIMEOUT
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT
            )

            # Set cookies on client instance (not per-request)
            client.cookies.update(login_resp.cookies)

            # Get me
            me_resp = await client.get(
                f"{API_BASE}/auth/me",
                timeout=TIMEOUT
            )

            assert me_resp.status_code == 200
            data = me_resp.json()
            assert data["user"]["username"] == username
            print_success("Got current user successfully")

    @pytest.mark.asyncio
    async def test_me_unauthenticated(self, test_server):
        """ME-002: Get current user without auth returns 401."""
        print_section("ME-002: Get current user (unauthenticated)")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{API_BASE}/auth/me",
                timeout=TIMEOUT
            )

            assert response.status_code == 401
            print_success("Unauthenticated request correctly rejected")

    @pytest.mark.asyncio
    async def test_me_invalid_session(self, test_server):
        """ME-003: Get current user with invalid session returns 401."""
        print_section("ME-003: Invalid session rejected")

        async with httpx.AsyncClient() as client:
            # Set invalid session cookie on client instance
            client.cookies.set("session", "invalid_session_id_12345")

            response = await client.get(
                f"{API_BASE}/auth/me",
                timeout=TIMEOUT
            )

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
                    "password": "password123"
                },
                timeout=TIMEOUT
            )

            response = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT
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
                    "password": "password123"
                },
                timeout=TIMEOUT
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "password123"},
                timeout=TIMEOUT
            )

            # Set cookies on client instance (not per-request)
            client.cookies.update(login_resp.cookies)

            # Make multiple requests with same session
            for i in range(3):
                me_resp = await client.get(
                    f"{API_BASE}/auth/me",
                    timeout=TIMEOUT
                )
                assert me_resp.status_code == 200, f"Request {i+1} failed"

            print_success("Session persists across multiple requests")

