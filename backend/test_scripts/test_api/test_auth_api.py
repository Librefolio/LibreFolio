"""
Authentication API Tests

Tests for login, logout, register, and session management endpoints.
"""

import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import httpx
import pytest
import pytest_asyncio
from fastapi import HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.config import Settings, get_settings
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.auth import AuthLoginRequest, AuthLoginResponse, AuthRegisterRequest
from backend.app.services import auth_service, user_service
from backend.app.services.global_settings_service import is_registration_enabled
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 10.0


async def set_registration_enabled(enabled: bool) -> None:
    """
    Put the registration gate in the state this module needs.

    The row is created when missing instead of being asserted into existence.
    Asserting worked only by accident: every module used to start its own server,
    whose startup re-seeded the global settings, so a neighbour that wiped the
    table was silently repaired before the next module looked. With one server for
    the whole run nobody repairs anything — and a fixture whose job is to *set* a
    value has no business requiring someone else to have created it first.
    """
    from backend.app.schemas.settings import GLOBAL_SETTINGS_DEFAULTS  # noqa: PLC0415 — test setup — imports after sys.path/db config

    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == "enable_registration"))
        setting = result.scalar_one_or_none()
        if setting is None:
            spec = GLOBAL_SETTINGS_DEFAULTS.get("enable_registration", {})
            setting = GlobalSetting(
                key="enable_registration",
                value="true",
                value_type=spec.get("type", "bool"),
                description=spec.get("description"),
            )
        setting.value = "true" if enabled else "false"
        session.add(setting)
        await session.commit()


@pytest.fixture(scope="module")
def test_server():
    """Start test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


@pytest_asyncio.fixture(autouse=True)
async def registration_enabled_by_default(test_server):
    """Keep global registration state isolated between auth API tests."""
    await set_registration_enabled(True)
    yield
    await set_registration_enabled(True)


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
    async def test_register_succeeds_when_registration_enabled(self, test_server):
        """REG-005: Registration succeeds when enable_registration is true."""
        print_section("REG-005: Registration enabled allows new user")

        await set_registration_enabled(True)

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"enabledreg_{timestamp}"

            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"{username}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
            assert response.json()["user"]["username"] == username
            print_success("Registration enabled allowed new user")

    @pytest.mark.asyncio
    async def test_register_disabled_rejects_when_users_exist(self, test_server):
        """REG-006: Disabled registration returns 403 when at least one user exists."""
        print_section("REG-006: Disabled registration rejects non-bootstrap user")

        await set_registration_enabled(True)

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            seed_username = f"disabledseed_{timestamp}"

            seed_response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": seed_username,
                    "email": f"{seed_username}@example.com",
                    "password": "password123",
                },
                timeout=TIMEOUT,
            )
            assert seed_response.status_code == 201, f"Setup failed: {seed_response.text}"

            try:
                await set_registration_enabled(False)
                username = f"disabledreg_{timestamp}"

                response = await client.post(
                    f"{API_BASE}/auth/register",
                    json={
                        "username": username,
                        "email": f"{username}@example.com",
                        "password": "password123",
                    },
                    timeout=TIMEOUT,
                )

                assert response.status_code == 403
                assert "registration is disabled" in response.json()["detail"].lower()
                print_success("Disabled registration rejected non-bootstrap user")
            finally:
                await set_registration_enabled(True)

    @pytest.mark.asyncio
    async def test_register_disabled_allows_bootstrap_when_no_users(self, tmp_path):
        """REG-007: Disabled registration still allows bootstrap when user count is zero.

        On a private database (a fresh SQLite file under tmp_path with the whole ORM schema), zero
        users and enable_registration=false are its real state, not a patched counter. The lane's
        users and global settings are never touched, and the bootstrap administrator no longer
        stays behind in the shared database.
        """
        print_section("REG-007: Disabled registration allows bootstrap user")

        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'bootstrap.db'}", poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)
            async with AsyncSession(engine) as session:
                session.add(GlobalSetting(key="enable_registration", value="false", value_type="bool"))
                await session.commit()

            username = "bootstrapreg"
            async with AsyncSession(engine, expire_on_commit=False) as session:
                assert await user_service.count_users(session) == 0, "Precondition: the private database must have no user"
                assert await is_registration_enabled(session) is False, "Precondition: registration must be disabled"
                response = await auth_api.register(
                    AuthRegisterRequest(
                        username=username,
                        email=f"{username}@example.com",
                        password="password123",
                    ),
                    session,
                )

            assert response.user.username == username
            assert response.user.is_superuser is True
            print_success("Disabled registration allowed bootstrap user")
        finally:
            await engine.dispose()

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


# ============================================================================
# THE SESSION COOKIE'S SECURE ATTRIBUTE (plan 34 step 2, §7.3)
# ============================================================================

#: The lane's server by its IPv4 address, never "localhost": see TestSessionCookieSecure.
IPV4_API_BASE = f"http://127.0.0.1:{settings.TEST_PORT}/api/v1"
#: What a reverse proxy terminating TLS on the same host adds to the request it forwards.
FORWARDED_HTTPS = {"X-Forwarded-Proto": "https"}


@dataclass
class _DisposableUser:
    """A regular user one test registered; ``deleted`` once the test deleted the account itself."""

    username: str
    password: str
    deleted: bool = False

    @property
    def credentials(self) -> dict[str, str]:
        return {"username": self.username, "password": self.password}


def _session_set_cookie(response: httpx.Response) -> tuple[str, dict[str, str]]:
    """The response's ``session`` Set-Cookie: its value, and its attributes by lower-cased name ("" for a flag).

    Parsed by name, never by position: the attribute order is http.cookies', not a contract.
    """
    cookies: list[tuple[str, dict[str, str]]] = []
    for header in response.headers.get_list("set-cookie"):
        pair, *attributes = (part.strip() for part in header.split(";"))
        name, _, value = pair.partition("=")
        if name.strip() == auth_api.SESSION_COOKIE_NAME:
            cookies.append((value, {key.strip().lower(): attribute_value.strip() for key, _, attribute_value in (attribute.partition("=") for attribute in attributes if attribute)}))
    assert len(cookies) == 1, f"Expected exactly one {auth_api.SESSION_COOKIE_NAME} Set-Cookie, got {response.headers.get_list('set-cookie')}"
    return cookies[0]


async def _login(client: httpx.AsyncClient, user: _DisposableUser, headers: Optional[dict[str, str]] = None) -> httpx.Response:
    response = await client.post(f"{IPV4_API_BASE}/auth/login", json=user.credentials, headers=headers, timeout=TIMEOUT)
    assert response.status_code == 200, f"Login as {user.username} failed: {response.status_code} {response.text}"
    return response


def _request(scheme: str, forwarded_proto: Optional[str] = None, client_host: str = "127.0.0.1") -> Request:
    """A request as uvicorn hands it to the app: ``scheme`` is the one uvicorn left in the scope.

    Like every request uvicorn hands over, the scope carries a Host header and the server address,
    so request.url is absolute and request.url.scheme is the scheme. ``forwarded_proto`` adds an
    X-Forwarded-Proto header as received: uvicorn turns it into the scheme only for a client it
    trusts (FORWARDED_ALLOW_IPS), and leaves the header in the scope either way.
    """
    port = 443 if scheme == "https" else 80
    headers = [(b"host", b"librefolio.example")]
    if forwarded_proto is not None:
        headers.append((b"x-forwarded-proto", forwarded_proto.encode("latin-1")))
    scope = {
        "type": "http",
        "scheme": scheme,
        "method": "POST",
        "path": "/api/v1/auth/login",
        "root_path": "",
        "query_string": b"",
        "headers": headers,
        "client": (client_host, 50000),
        "server": ("librefolio.example", port),
    }
    return Request(scope)


class TestSessionCookieSecure:
    """The session cookie's Secure attribute, on the live test server (plan 34 step 2, §7.3).

    The developer's rule: secure by default, insecure only when turned off explicitly. Under the
    default SESSION_COOKIE_SECURE=auto, every session Set-Cookie (login, logout, account deletion)
    is Secure when the request arrived over HTTPS, or when the first value of its X-Forwarded-Proto
    says https — whoever sent the header, which can only switch Secure on (COOKIE-011).

    These tests reach the server at 127.0.0.1 (IPV4_API_BASE), a client uvicorn trusts by default
    (FORWARDED_ALLOW_IPS=127.0.0.1): there its proxy-headers handling also turns X-Forwarded-Proto
    into the request's scheme, so a forwarded request is https by both routes. Neither route is
    needed alone, and COOKIE-010 and COOKIE-011 pin each one in-process. They depend on the server
    listening on IPv4 (the runner's 0.0.0.0 with HOST unset, the in-process server's localhost) and
    on SESSION_COOKIE_SECURE unset or auto (checked, see lane_runs_auto).

    Write-safe: a login test registers a regular user of its own and deletes it at teardown;
    logout needs no session, the handler clears the cookie unconditionally.
    """

    @pytest.fixture(autouse=True)
    def lane_runs_auto(self):
        """Precondition: the default mode. The server reads the same .env and environment as this process."""
        mode = auth_api.SESSION_COOKIE_SECURE_MODE
        assert mode == "auto", f"Precondition: these tests need SESSION_COOKIE_SECURE=auto, the default; this lane runs {mode!r} (set in .env or in the environment)"

    @pytest_asyncio.fixture
    async def disposable_user(self, test_server):
        """A regular user of this test only, registered over plain HTTP, deleted at teardown.

        Teardown logs in over plain HTTP and sends the session explicitly, so the deletion works
        whatever the cookie's Secure says; a test that deleted the account itself marks it deleted.
        """
        user = _DisposableUser(username=f"cookiesec_{uuid.uuid4().hex[:12]}", password="cookiepassword123")
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{IPV4_API_BASE}/auth/register", json={**user.credentials, "email": f"{user.username}@example.com"}, timeout=TIMEOUT)
        assert response.status_code == 201, f"Setup failed: {response.status_code} {response.text}"
        assert response.json()["user"]["is_superuser"] is False, "Precondition: a regular user (the lane has its administrators), so its account deletion is never refused"

        yield user

        if user.deleted:
            return
        async with httpx.AsyncClient() as client:
            token, _ = _session_set_cookie(await _login(client, user))
            response = await client.delete(f"{IPV4_API_BASE}/auth/users/me", headers={"Cookie": f"{auth_api.SESSION_COOKIE_NAME}={token}"}, timeout=TIMEOUT)
        assert response.status_code == 200, f"Cleanup: deleting {user.username} failed: {response.status_code} {response.text}"

    @pytest.mark.asyncio
    async def test_login_over_plain_http_sets_no_secure_cookie(self, test_server, disposable_user):
        """COOKIE-001 — GUARD, green today and after: under auto, plain HTTP leaves Secure off.

        Browsers refuse a Secure cookie set by an http:// origin (localhost aside), so a plain-HTTP
        install (a LAN, a container without TLS) would never stay logged in.
        """
        print_section("COOKIE-001: login over plain HTTP sets no Secure cookie")
        async with httpx.AsyncClient() as client:
            response = await _login(client, disposable_user)

        token, attributes = _session_set_cookie(response)
        assert token, f"The login must set a session token: {attributes}"
        assert "secure" not in attributes, f"Over plain HTTP the session cookie must not be Secure under auto: {attributes}"
        assert "httponly" in attributes and attributes.get("samesite", "").lower() == "lax", f"The session cookie must stay HttpOnly and SameSite=Lax: {attributes}"

        print_success("✓ Plain HTTP: no Secure; HttpOnly and SameSite=Lax")

    @pytest.mark.asyncio
    async def test_login_behind_an_https_proxy_sets_a_secure_cookie(self, test_server, disposable_user):
        """COOKIE-002 — NEW, red today: behind a trusted proxy reporting HTTPS, the login cookie is Secure.

        X-Forwarded-Proto: https from 127.0.0.1 is what a reverse proxy on the same host sends, and
        uvicorn makes it the request's scheme. HttpOnly and SameSite=Lax stay as they are.

        Today the cookie is never Secure: the red lists its attributes, without "secure".
        """
        print_section("COOKIE-002: login behind an HTTPS proxy sets a Secure cookie")
        async with httpx.AsyncClient() as client:
            response = await _login(client, disposable_user, headers=FORWARDED_HTTPS)

        token, attributes = _session_set_cookie(response)
        assert token, f"The login must set a session token: {attributes}"
        assert "secure" in attributes, f"[new] Behind a trusted proxy reporting HTTPS (X-Forwarded-Proto: https from 127.0.0.1) the session cookie must be Secure under auto, the default: Set-Cookie attributes {attributes}"
        assert "httponly" in attributes and attributes.get("samesite", "").lower() == "lax", f"The session cookie must stay HttpOnly and SameSite=Lax: {attributes}"

        print_success("✓ HTTPS behind the proxy: Secure, HttpOnly and SameSite=Lax")

    @pytest.mark.asyncio
    async def test_logout_behind_an_https_proxy_clears_with_a_secure_cookie(self, test_server):
        """COOKIE-003 — NEW, red today: the Set-Cookie that clears the session is Secure over HTTPS too.

        Every session Set-Cookie written over HTTPS is Secure, the one that deletes it included.
        Presence barrier first: the response must be the deletion (Max-Age=0).
        """
        print_section("COOKIE-003: logout behind an HTTPS proxy clears with a Secure cookie")
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{IPV4_API_BASE}/auth/logout", headers=FORWARDED_HTTPS, timeout=TIMEOUT)
        assert response.status_code == 200, f"Logout failed: {response.status_code} {response.text}"

        _, attributes = _session_set_cookie(response)
        assert attributes.get("max-age") == "0", f"The logout must clear the session cookie (Max-Age=0): {attributes}"
        assert "secure" in attributes, f"[new] Behind a trusted proxy reporting HTTPS the Set-Cookie that clears the session must be Secure under auto: {attributes}"

        print_success("✓ HTTPS behind the proxy: the clearing Set-Cookie is Secure")

    @pytest.mark.asyncio
    async def test_logout_over_plain_http_clears_without_secure(self, test_server):
        """COOKIE-004 — GUARD, green today and after: over plain HTTP the clearing Set-Cookie is not Secure."""
        print_section("COOKIE-004: logout over plain HTTP clears without Secure")
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{IPV4_API_BASE}/auth/logout", timeout=TIMEOUT)
        assert response.status_code == 200, f"Logout failed: {response.status_code} {response.text}"

        _, attributes = _session_set_cookie(response)
        assert attributes.get("max-age") == "0", f"The logout must clear the session cookie (Max-Age=0): {attributes}"
        assert "secure" not in attributes, f"Over plain HTTP the clearing Set-Cookie must not be Secure under auto: {attributes}"

        print_success("✓ Plain HTTP: the clearing Set-Cookie has no Secure")

    @pytest.mark.asyncio
    async def test_account_deletion_behind_an_https_proxy_clears_with_a_secure_cookie(self, test_server, disposable_user):
        """COOKIE-005 — NEW, red today: DELETE /auth/users/me, the third session Set-Cookie, is Secure over HTTPS.

        The user logs in over plain HTTP and deletes the account through the proxy, the session
        sent explicitly. The account goes either way; the red is the clearing Set-Cookie without
        "secure".
        """
        print_section("COOKIE-005: account deletion behind an HTTPS proxy clears with a Secure cookie")
        async with httpx.AsyncClient() as client:
            token, _ = _session_set_cookie(await _login(client, disposable_user))
            response = await client.delete(f"{IPV4_API_BASE}/auth/users/me", headers={**FORWARDED_HTTPS, "Cookie": f"{auth_api.SESSION_COOKIE_NAME}={token}"}, timeout=TIMEOUT)
        disposable_user.deleted = response.status_code == 200
        assert response.status_code == 200, f"Account deletion failed: {response.status_code} {response.text}"

        _, attributes = _session_set_cookie(response)
        assert attributes.get("max-age") == "0", f"The account deletion must clear the session cookie (Max-Age=0): {attributes}"
        assert "secure" in attributes, f"[new] Behind a trusted proxy reporting HTTPS the Set-Cookie that clears the deleted account's session must be Secure under auto: {attributes}"

        print_success("✓ HTTPS behind the proxy: the account deletion's clearing Set-Cookie is Secure")


class TestSessionCookieSecureMode:
    """auth_api.session_cookie_secure(request), in-process: the mode decides; auto follows the scheme, or the first X-Forwarded-Proto."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("mode", "scheme", "secure"),
        [
            pytest.param("always", "http", True, id="always-http"),
            pytest.param("always", "https", True, id="always-https"),
            pytest.param("auto", "https", True, id="auto-https"),
            pytest.param("auto", "http", False, id="auto-http"),
            pytest.param("never", "https", False, id="never-https"),
            pytest.param("never", "http", False, id="never-http"),
        ],
    )
    async def test_secure_follows_the_mode_and_the_scheme(self, monkeypatch, mode, scheme, secure):
        """COOKIE-010 — always → True, never → False, auto → whether the request arrived over https.

        These requests carry no X-Forwarded-Proto (COOKIE-011 covers it). RED today on the three
        True cases: the stub answers False to everything. The three False cases are guards: auto
        stays off over plain HTTP, and never is the only way to turn it off over HTTPS.
        """
        print_section(f"COOKIE-010: SESSION_COOKIE_SECURE={mode} over {scheme}")
        monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", mode)
        request = _request(scheme)
        assert request.url.scheme == scheme, f"Precondition: the request must arrive over {scheme}: {request.url}"

        assert auth_api.session_cookie_secure(request) is secure, f"session_cookie_secure() with SESSION_COOKIE_SECURE={mode!r} over {scheme} must be {secure}"

        print_success(f"✓ {mode} over {scheme}: Secure={secure}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("mode", "scheme", "forwarded_proto", "secure"),
        [
            pytest.param("auto", "http", "https", True, id="auto-http-xfp-https"),
            pytest.param("auto", "http", "http, https", False, id="auto-http-xfp-http-then-https"),
            pytest.param("never", "http", "https", False, id="never-http-xfp-https"),
            pytest.param("auto", "http", "HTTPS , http", True, id="auto-http-xfp-first-value-trimmed-any-case"),
            pytest.param("auto", "https", "http", True, id="auto-https-xfp-http"),
            pytest.param("always", "http", "http", True, id="always-http-xfp-http"),
        ],
    )
    async def test_auto_also_follows_the_first_forwarded_proto(self, monkeypatch, mode, scheme, forwarded_proto, secure):
        """COOKIE-011 — in auto, the first X-Forwarded-Proto value, trimmed and in any case, switches Secure on.

        Whoever sent the header: the request comes from 203.0.113.7, an address uvicorn does not
        trust by default, so the scheme stays as uvicorn left it and only the app's own reading of
        the header can switch Secure on. Only the first comma-separated value counts. The header
        never switches Secure off: auto over https stays Secure. always and never ignore it, and
        never is the documented way out when a proxy claims https to a browser on plain HTTP.

        RED today on the True cases (the stub answers False); the False cases are guards.
        """
        print_section(f"COOKIE-011: SESSION_COOKIE_SECURE={mode} over {scheme}, X-Forwarded-Proto: {forwarded_proto}")
        monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", mode)
        request = _request(scheme, forwarded_proto=forwarded_proto, client_host="203.0.113.7")
        assert request.url.scheme == scheme, f"Precondition: the request must arrive over {scheme}: {request.url}"
        assert request.headers.get("x-forwarded-proto") == forwarded_proto, f"Precondition: the request must carry X-Forwarded-Proto: {forwarded_proto!r}: {request.headers}"

        assert auth_api.session_cookie_secure(request) is secure, f"session_cookie_secure() with SESSION_COOKIE_SECURE={mode!r} over {scheme} and X-Forwarded-Proto: {forwarded_proto!r} must be {secure}"

        print_success(f"✓ {mode} over {scheme}, X-Forwarded-Proto {forwarded_proto!r}: Secure={secure}")


class TestSessionCookieSecureSetting:
    """Settings.SESSION_COOKIE_SECURE: auto by default, stripped and lower-cased, nothing but auto/always/never (guards).

    Every Settings here is built with _env_file=None: the repo's .env must not decide the outcome.
    """

    @pytest.mark.asyncio
    async def test_default_is_auto(self, monkeypatch):
        """COOKIE-020 — GUARD: unset, the mode is auto (neither .env nor the environment may set it here)."""
        print_section("COOKIE-020: SESSION_COOKIE_SECURE defaults to auto")
        monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)

        assert Settings(_env_file=None).SESSION_COOKIE_SECURE == "auto"

        print_success("✓ The default is auto")

    @pytest.mark.asyncio
    async def test_value_is_stripped_and_lower_cased(self, monkeypatch):
        """COOKIE-021 — GUARD: " ALWAYS " reads as always, passed to Settings or set in the environment (a Docker deployment)."""
        print_section("COOKIE-021: SESSION_COOKIE_SECURE is stripped and lower-cased")
        assert Settings(_env_file=None, SESSION_COOKIE_SECURE=" ALWAYS ").SESSION_COOKIE_SECURE == "always"

        monkeypatch.setenv("SESSION_COOKIE_SECURE", " Never ")
        assert Settings(_env_file=None).SESSION_COOKIE_SECURE == "never"

        print_success("✓ Stripped and lower-cased, from an argument and from the environment")

    @pytest.mark.asyncio
    async def test_unknown_value_is_rejected(self):
        """COOKIE-022 — GUARD: anything else is a ValidationError on SESSION_COOKIE_SECURE, so a wrong value stops the start."""
        print_section("COOKIE-022: an unknown SESSION_COOKIE_SECURE is rejected")
        with pytest.raises(ValidationError) as rejected:
            Settings(_env_file=None, SESSION_COOKIE_SECURE="sometimes")

        assert [error["loc"] for error in rejected.value.errors()] == [("SESSION_COOKIE_SECURE",)], f"Only SESSION_COOKIE_SECURE must be rejected: {rejected.value}"

        print_success("✓ 'sometimes' is a ValidationError on SESSION_COOKIE_SECURE")


# ============================================================================
# A LOGIN THAT DOES NOT REVEAL ACCOUNTS (plan 36, §2.5)
# ============================================================================
#
# The password is checked before the account's state. A wrong password gets one answer, status and
# body, whether the account is unknown, active or disabled; only the right password learns that an
# account is disabled, with a 403 ACCOUNT_DISABLED. Without an account bcrypt still runs, against a
# dummy hash of the same cost computed once, so the response time does not tell either (D5). These
# tests check that bcrypt ran, and against what; they never measure how long anything took.

#: B0: the answer to a wrong password, whether the account is unknown, active or disabled.
INVALID_CREDENTIALS = {"detail": "Invalid credentials"}
#: The 403 detail a disabled account gets, and only with the right password (plan 36, §0.1).
ACCOUNT_DISABLED_DETAIL = {"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}


def _wrong_password() -> str:
    """A password no account of this run has."""
    return f"Wrong-{uuid.uuid4().hex[:12]}"


def _session_set_cookies(response: httpx.Response) -> list[str]:
    """Every Set-Cookie of ``response`` that writes the session cookie, matched by name: [] when there is none."""
    return [header for header in response.headers.get_list("set-cookie") if header.split(";", 1)[0].partition("=")[0].strip() == auth_api.SESSION_COOKIE_NAME]


def _answer(response: httpx.Response) -> tuple[int, str]:
    """What a login tells its client: the status code and the body, byte for byte."""
    return response.status_code, response.text


async def _post_login(username: str, password: str) -> httpx.Response:
    """POST /auth/login on the lane's server, from a client with an empty cookie jar; the response whatever its status."""
    async with httpx.AsyncClient() as client:
        return await client.post(f"{IPV4_API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)


async def _b0() -> httpx.Response:
    """B0 as the lane answers it: an unknown username with a wrong password, checked to be the generic 401 without a session."""
    response = await _post_login(f"nobody_{uuid.uuid4().hex[:12]}", _wrong_password())
    assert (response.status_code, response.json()) == (401, INVALID_CREDENTIALS), f"B0, the answer to an unknown username, must be 401 {INVALID_CREDENTIALS}: got {response.status_code} {response.text}"
    assert _session_set_cookies(response) == [], f"A failed login must set no session cookie: {response.headers.get_list('set-cookie')}"
    return response


@dataclass(frozen=True)
class _LoginAccounts:
    """An active and a disabled regular account of one test."""

    active: _DisposableUser
    disabled: _DisposableUser


async def _active_flags(user_ids: list[int]) -> dict[int, bool]:
    """{user id: is_active} of these users of the lane, read in a fresh session."""
    async with AsyncSession(get_async_engine()) as session:
        result = await session.execute(select(User.id, User.is_active).where(User.id.in_(user_ids)))
        return dict(result.tuples().all())


async def _delete_users(user_ids: list[int]) -> list[str]:
    """Delete these users of the lane through user_service.delete_user, each in a session of its own; return what failed."""
    errors: list[str] = []
    for user_id in user_ids:
        async with AsyncSession(get_async_engine()) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:  # every account gets its attempt; the failures are reported together
                errors.append(f"user {user_id}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def login_accounts(test_server) -> AsyncIterator[_LoginAccounts]:
    """An active and a disabled account of this test only, both deleted at teardown, after a red too.

    Both are registered over HTTP as regular users. The disabled one is then deactivated through
    user_service.set_user_active on the lane's database, the path of `dev.py user deactivate`, and
    both states are read back before the test runs: a disabled account that was not disabled would
    let LOGIN-012 pass for the wrong reason. A disabled account cannot log in to delete itself, so
    teardown deletes both through user_service.delete_user, the service DELETE /auth/users/me calls.
    """
    accounts = _LoginAccounts(
        active=_DisposableUser(username=f"loginon_{uuid.uuid4().hex[:12]}", password=f"Active-{uuid.uuid4().hex[:12]}"),
        disabled=_DisposableUser(username=f"loginoff_{uuid.uuid4().hex[:12]}", password=f"Disabled-{uuid.uuid4().hex[:12]}"),
    )
    user_ids: list[int] = []
    try:
        async with httpx.AsyncClient() as client:
            for user in (accounts.active, accounts.disabled):
                response = await client.post(f"{IPV4_API_BASE}/auth/register", json={**user.credentials, "email": f"{user.username}@example.com"}, timeout=TIMEOUT)
                assert response.status_code == 201, f"Setup: registering {user.username} failed: {response.status_code} {response.text}"
                user_ids.append(response.json()["user"]["id"])
                assert response.json()["user"]["is_superuser"] is False, "Precondition: regular users (the lane has its administrators)"
        async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
            deactivated, error = await user_service.set_user_active(session, accounts.disabled.username, False)
        assert deactivated, f"Setup: set_user_active({accounts.disabled.username!r}, False) refused: {error}"
        flags = await _active_flags(user_ids)
        assert flags == {user_ids[0]: True, user_ids[1]: False}, f"Precondition: {accounts.active.username} active and {accounts.disabled.username} disabled, in the database the server reads: {flags}"

        yield accounts
    finally:
        errors = await _delete_users(user_ids)
        assert not errors, f"Cleanup: {errors}"


class TestLoginDoesNotRevealAccounts:
    """POST /auth/login on the lane's server: a wrong password gets one answer, whoever the account (plan 36, §2.5).

    B0 is the answer to an unknown username, 401 {"detail": "Invalid credentials"}. An active or a
    disabled account with a wrong password must answer exactly as B0, status and body byte for byte;
    only the right password learns that an account is disabled (403 ACCOUNT_DISABLED). No failed
    login sets a session cookie (guard), and the successful one does (LOGIN-014): that is what gives
    the absences meaning.

    Write-scoped: each test registers its own accounts and deletes them at teardown (login_accounts).
    """

    @pytest.mark.asyncio
    async def test_unknown_account_gets_the_generic_answer(self, test_server):
        """LOGIN-010 — GUARD, green today and after: an unknown username gets B0, 401 {"detail": "Invalid credentials"}, and no session."""
        print_section("LOGIN-010: an unknown username gets B0, the generic 401")
        await _b0()

        print_success("✓ Unknown username: 401 Invalid credentials, no session")

    @pytest.mark.asyncio
    async def test_active_account_with_a_wrong_password_answers_as_an_unknown_one(self, login_accounts):
        """LOGIN-011 — GUARD, green today and after: an active account with a wrong password answers exactly B0."""
        print_section("LOGIN-011: an active account with a wrong password answers as an unknown one")
        b0 = await _b0()

        response = await _post_login(login_accounts.active.username, _wrong_password())

        assert _answer(response) == _answer(b0), f"An active account with a wrong password must answer exactly as an unknown username, B0 {_answer(b0)}: got {_answer(response)}"
        assert _session_set_cookies(response) == [], f"A failed login must set no session cookie: {response.headers.get_list('set-cookie')}"

        print_success("✓ Active account, wrong password: B0, no session")

    @pytest.mark.asyncio
    async def test_disabled_account_with_a_wrong_password_answers_as_an_unknown_one(self, login_accounts):
        """LOGIN-012 — NEW, red today: a disabled account with a wrong password answers exactly B0.

        Today the account's state is checked before the password: anyone learns that the account
        exists and is disabled, from 401 {"detail": "Account is disabled"}.
        """
        print_section("LOGIN-012: a disabled account with a wrong password answers as an unknown one")
        b0 = await _b0()

        response = await _post_login(login_accounts.disabled.username, _wrong_password())

        assert _answer(response) == _answer(b0), f"[new] A disabled account with a wrong password must answer exactly as an unknown username, B0 {_answer(b0)}: got {_answer(response)}, which tells that the account exists and is disabled"
        assert _session_set_cookies(response) == [], f"A failed login must set no session cookie: {response.headers.get_list('set-cookie')}"

        print_success("✓ Disabled account, wrong password: B0, no session")

    @pytest.mark.asyncio
    async def test_disabled_account_with_the_right_password_is_told_it_is_disabled(self, login_accounts):
        """LOGIN-013 — NEW, red today: only the right password learns that the account is disabled, from a 403 ACCOUNT_DISABLED.

        A 403 says «right credentials, access denied», and its error_code is what the frontend maps
        to auth.accountDisabled. Today: 401 {"detail": "Account is disabled"}.
        """
        print_section("LOGIN-013: a disabled account with the right password gets 403 ACCOUNT_DISABLED")
        response = await _post_login(login_accounts.disabled.username, login_accounts.disabled.password)

        assert (response.status_code, response.json()) == (403, {"detail": ACCOUNT_DISABLED_DETAIL}), f"[new] A disabled account with the right password must get 403 with detail {ACCOUNT_DISABLED_DETAIL}: got {response.status_code} {response.text}"
        assert _session_set_cookies(response) == [], f"A disabled account must get no session cookie: {response.headers.get_list('set-cookie')}"

        print_success("✓ Disabled account, right password: 403 ACCOUNT_DISABLED, no session")

    @pytest.mark.asyncio
    async def test_active_account_with_the_right_password_logs_in(self, login_accounts):
        """LOGIN-014 — GUARD, green today and after: the active account with its password logs in and gets one session cookie.

        The presence barrier of this class: _session_set_cookies does find the session cookie when
        there is one, so the absences asserted on every failure are not an artefact of the lookup.
        """
        print_section("LOGIN-014: the active account with its password logs in")
        response = await _post_login(login_accounts.active.username, login_accounts.active.password)

        assert response.status_code == 200, f"The active account with its password must log in: {response.status_code} {response.text}"
        assert response.json()["user"]["username"] == login_accounts.active.username, f"The login must be the active account's: {response.text}"
        assert len(_session_set_cookies(response)) == 1, f"A successful login must set exactly one session cookie: {response.headers.get_list('set-cookie')}"
        token, _ = _session_set_cookie(response)
        assert token, f"The session cookie must carry a token: {response.headers.get_list('set-cookie')}"

        print_success("✓ Active account, right password: 200 and a session cookie")


@dataclass(frozen=True)
class _PrivateLogin:
    """A database one test owns entirely, under its tmp_path, with one active and one disabled account."""

    engine: AsyncEngine
    active: _DisposableUser
    disabled: _DisposableUser


@dataclass
class _CheckpwCall:
    """One bcrypt.checkpw call: its arguments as bcrypt received them, and what the real check raised, if anything."""

    password: bytes
    hashed_password: bytes
    raised: Optional[BaseException] = None


#: A well-formed bcrypt hash: $2a$, $2b$ or $2y$, a two-digit cost, then 53 characters of salt and digest.
_BCRYPT_HASH = re.compile(rb"\$2[aby]\$(\d{2})\$[./A-Za-z0-9]{53}")


def _bcrypt_cost(hashed_password: bytes) -> Optional[int]:
    """The cost of a well-formed bcrypt hash; None for anything else."""
    match = _BCRYPT_HASH.fullmatch(hashed_password)
    return int(match.group(1)) if match else None


@pytest_asyncio.fixture
async def private_login(tmp_path: Path) -> AsyncIterator[_PrivateLogin]:
    """A fresh SQLite file under tmp_path with the whole ORM schema, an active and a disabled account; disposed at teardown.

    The login handler runs on it in-process, as REG-007 runs registration: unknown, active and
    disabled are real states there, the bcrypt spy sees every check, and nothing reaches the lane.
    The accounts are created through user_service.create_user, the disabled one inactive from the
    start. NullPool as get_async_engine.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'login.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        instance = _PrivateLogin(engine=engine, active=_DisposableUser("active_user", "ActivePass123!"), disabled=_DisposableUser("disabled_user", "DisabledPass123!"))
        async with AsyncSession(engine, expire_on_commit=False) as session:
            for user, active in ((instance.active, True), (instance.disabled, False)):
                created, error = await user_service.create_user(session, username=user.username, email=f"{user.username}@example.com", password=user.password, is_active=active)
                assert created is not None and created.is_active is active, f"Setup: create_user({user.username!r}, is_active={active}) failed: {error}"
        yield instance
    finally:
        await engine.dispose()


@pytest.fixture
def checkpw_calls(monkeypatch: pytest.MonkeyPatch) -> list[_CheckpwCall]:
    """Spy on bcrypt.checkpw in the module object auth_service uses: the real check still runs, and every call is recorded.

    Whether bcrypt ran, and against what, is the contract (plan 36, D5); how long it took is never
    measured.
    """
    real_checkpw = auth_service.bcrypt.checkpw
    calls: list[_CheckpwCall] = []

    def checkpw(password: bytes, hashed_password: bytes) -> bool:
        call = _CheckpwCall(password=password, hashed_password=hashed_password)
        calls.append(call)
        try:
            return real_checkpw(password, hashed_password)
        except Exception as exc:
            call.raised = exc
            raise

    monkeypatch.setattr(auth_service.bcrypt, "checkpw", checkpw)
    return calls


async def _login_in_process(engine: AsyncEngine, username: str, password: str) -> Union[AuthLoginResponse, HTTPException]:
    """POST /auth/login's handler called as FastAPI wires it, on a private database; the outcome is returned, never raised."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            return await auth_api.login(request=AuthLoginRequest(username=username, password=password), response=Response(), http_request=_request("http"), session=session)
        except HTTPException as refusal:
            return refusal


def _refusal(outcome: Union[AuthLoginResponse, HTTPException]) -> Optional[tuple[int, object]]:
    """(status code, detail) of a refused login; None when the login went through."""
    return (outcome.status_code, outcome.detail) if isinstance(outcome, HTTPException) else None


class TestLoginAlwaysRunsBcrypt:
    """auth_api.login and verify_password_or_dummy in-process, with bcrypt.checkpw spied (plan 36, §2.5 and D5).

    The handler runs on a private database (private_login), and every login costs exactly one
    bcrypt check, whatever the account: without an account the password is checked against a dummy
    hash. Nothing here measures time.
    """

    @pytest.mark.asyncio
    async def test_unknown_account_is_refused_after_one_bcrypt_check(self, private_login, checkpw_calls):
        """LOGIN-020 — NEW, red today: an unknown username gets 401 «Invalid credentials» after exactly one bcrypt check.

        Without an account the password is checked against a dummy hash, so an unknown login costs
        what a wrong password costs. Today bcrypt does not run at all (0 calls), and the response
        time tells which accounts exist.
        """
        print_section("LOGIN-020: an unknown username is refused after one bcrypt check")
        outcome = await _login_in_process(private_login.engine, "nobody_here", _wrong_password())

        assert _refusal(outcome) == (401, "Invalid credentials"), f"An unknown username must get 401 «Invalid credentials»: got {outcome!r}"
        assert len(checkpw_calls) == 1, f"[new] An unknown username must still cost one bcrypt check, against a dummy hash: bcrypt.checkpw ran {len(checkpw_calls)} time(s)"

        print_success("✓ Unknown username: 401 Invalid credentials, one bcrypt check")

    @pytest.mark.asyncio
    async def test_active_account_with_a_wrong_password_is_refused_after_one_bcrypt_check(self, private_login, checkpw_calls):
        """LOGIN-021 — GUARD, green today and after: an active account with a wrong password gets 401 «Invalid credentials» after one bcrypt check."""
        print_section("LOGIN-021: an active account with a wrong password is refused after one bcrypt check")
        outcome = await _login_in_process(private_login.engine, private_login.active.username, _wrong_password())

        assert _refusal(outcome) == (401, "Invalid credentials"), f"An active account with a wrong password must get 401 «Invalid credentials»: got {outcome!r}"
        assert len(checkpw_calls) == 1, f"A wrong password is one bcrypt check: bcrypt.checkpw ran {len(checkpw_calls)} time(s)"

        print_success("✓ Active account, wrong password: 401 Invalid credentials, one bcrypt check")

    @pytest.mark.asyncio
    async def test_disabled_account_with_a_wrong_password_is_refused_as_an_unknown_one(self, private_login, checkpw_calls):
        """LOGIN-022 — NEW, red today: a disabled account with a wrong password gets 401 «Invalid credentials» after one bcrypt check.

        The password is checked before the account's state. Today the state comes first: 401
        «Account is disabled», and bcrypt never runs.
        """
        print_section("LOGIN-022: a disabled account with a wrong password is refused as an unknown one")
        outcome = await _login_in_process(private_login.engine, private_login.disabled.username, _wrong_password())

        assert _refusal(outcome) == (401, "Invalid credentials"), f"[new] A disabled account with a wrong password must get the 401 «Invalid credentials» an unknown one gets: got {outcome!r}"
        assert len(checkpw_calls) == 1, f"[new] The password must be checked before the account's state, one bcrypt check: bcrypt.checkpw ran {len(checkpw_calls)} time(s)"

        print_success("✓ Disabled account, wrong password: 401 Invalid credentials, one bcrypt check")

    @pytest.mark.asyncio
    async def test_disabled_account_with_the_right_password_gets_account_disabled(self, private_login, checkpw_calls):
        """LOGIN-023 — NEW, red today: a disabled account with the right password gets 403 ACCOUNT_DISABLED, once the password was checked.

        Today: 401 «Account is disabled», before the password is checked.
        """
        print_section("LOGIN-023: a disabled account with the right password gets 403 ACCOUNT_DISABLED")
        outcome = await _login_in_process(private_login.engine, private_login.disabled.username, private_login.disabled.password)

        assert _refusal(outcome) == (403, ACCOUNT_DISABLED_DETAIL), f"[new] A disabled account with the right password must get 403 with detail {ACCOUNT_DISABLED_DETAIL}: got {outcome!r}"
        assert len(checkpw_calls) == 1, f"[new] «Disabled» is told only once the password was checked, one bcrypt check: bcrypt.checkpw ran {len(checkpw_calls)} time(s)"

        print_success("✓ Disabled account, right password: 403 ACCOUNT_DISABLED, one bcrypt check")

    @pytest.mark.asyncio
    async def test_no_account_checks_the_password_against_a_dummy_hash(self, checkpw_calls):
        """LOGIN-024 — NEW, red today: verify_password_or_dummy("x", None) is False after one bcrypt check against a dummy hash of the same cost.

        The same cost: the dummy is a well-formed bcrypt hash of BCRYPT_ROUNDS, and the check runs to
        the end (an unreadable hash would fail at once, and the time would tell again). Today the
        stub answers False without running bcrypt.
        """
        print_section("LOGIN-024: without an account the password is checked against a dummy hash")
        assert auth_service.verify_password_or_dummy("x", None) is False, "Without an account the answer must be False"

        assert len(checkpw_calls) == 1, f"[new] Without an account bcrypt must still run once, against a dummy hash: bcrypt.checkpw ran {len(checkpw_calls)} time(s)"
        dummy = checkpw_calls[0]
        assert _bcrypt_cost(dummy.hashed_password) == auth_service.BCRYPT_ROUNDS, f"[new] The dummy hash must be a bcrypt hash of the cost every password gets, {auth_service.BCRYPT_ROUNDS}: got {dummy.hashed_password!r}"
        assert dummy.raised is None, f"[new] The check against the dummy hash must run to the end: bcrypt raised {dummy.raised!r}"

        print_success(f"✓ No account: one bcrypt check against a dummy hash of cost {auth_service.BCRYPT_ROUNDS}, and False")

    @pytest.mark.asyncio
    async def test_the_dummy_hash_is_computed_once(self, checkpw_calls):
        """LOGIN-025 — NEW, red today: two checks without an account use the same dummy hash, computed once.

        A dummy hashed anew on every call would add a bcrypt hashing to each unknown login, which would
        then take about twice a wrong password's time. Today the stub runs no check at all.
        """
        print_section("LOGIN-025: the dummy hash is computed once")
        for password in ("first-unknown-login", "second-unknown-login"):
            assert auth_service.verify_password_or_dummy(password, None) is False, "Without an account the answer must be False"

        assert len(checkpw_calls) == 2, f"[new] Each check without an account must run bcrypt once: bcrypt.checkpw ran {len(checkpw_calls)} time(s) for two checks"
        first, second = (call.hashed_password for call in checkpw_calls)
        assert first == second, f"[new] Both checks must use the one dummy hash, computed once: {first!r}, then {second!r}"

        print_success("✓ Two checks without an account, one dummy hash")

    @pytest.mark.asyncio
    async def test_a_real_hash_is_checked_as_before(self, checkpw_calls):
        """LOGIN-026 — GUARD, green today and after: with a real hash, True for the right password and False for a wrong one, one bcrypt check each."""
        print_section("LOGIN-026: with a real hash, verify_password_or_dummy is verify_password")
        hashed = auth_service.hash_password("RightPass123!")

        assert auth_service.verify_password_or_dummy("RightPass123!", hashed) is True, "The right password against its own hash must be True"
        assert auth_service.verify_password_or_dummy("WrongPass123!", hashed) is False, "A wrong password against a real hash must be False"
        assert len(checkpw_calls) == 2, f"One bcrypt check per verification: bcrypt.checkpw ran {len(checkpw_calls)} time(s) for two"

        print_success("✓ Real hash: True for the right password, False for a wrong one")
