"""
Authentication API Tests

Tests for login, logout, register, and session management endpoints.

Since lot A6c (decision 37) the API applies the backend's password rules to every new password: REG-004, CHPWD-005
and PWD-001..PWD-008 pin it on register and change-password (the reset link is in test_registration_api.py). Every
other password this module registers meets the rules, which the API checks before anything else of the request.
"""

import asyncio
import contextlib
import inspect
import itertools
import re
import time
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Optional, Union

import httpx
import pytest
import pytest_asyncio
from fastapi import BackgroundTasks, HTTPException, Request, Response
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.config import Settings, get_settings
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import GlobalSetting, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.auth import AuthLoginRequest, AuthLoginResponse, AuthRegisterRequest, ChangePasswordRequest
from backend.app.services.accounts import auth_service, user_service
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 10.0
#: The global setting that decides who may register (release 1.3: open, invite or disabled), and its row's key.
REGISTRATION_MODE_KEY = "registration_mode"


def _register_http_request() -> Request:
    """The HTTP request ``auth_api.register`` reads the client address from, as FastAPI hands it over (E5b: the limit
    of registration emails per client address)."""
    return Request({"type": "http", "method": "POST", "path": "/api/v1/auth/register", "headers": [], "client": ("127.0.0.1", 50000)})


def _error_code(response: httpx.Response) -> Optional[str]:
    """``detail.error_code`` of a coded refusal (as ACCOUNT_DISABLED is given), or None."""
    detail = response.json().get("detail")
    return detail.get("error_code") if isinstance(detail, dict) else None


async def set_registration_mode(mode: str) -> None:
    """
    Put the registration gate in the state this module needs: ``open`` or ``disabled``.

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
        result = await session.execute(select(GlobalSetting).where(GlobalSetting.key == REGISTRATION_MODE_KEY))
        setting = result.scalar_one_or_none()
        if setting is None:
            spec = GLOBAL_SETTINGS_DEFAULTS.get(REGISTRATION_MODE_KEY, {})
            setting = GlobalSetting(
                key=REGISTRATION_MODE_KEY,
                value="open",
                value_type=spec.get("type", "string"),
                description=spec.get("description"),
            )
        setting.value = mode
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
async def registration_open_by_default(test_server):
    """Keep global registration state isolated between auth API tests."""
    await set_registration_mode("open")
    yield
    await set_registration_mode("open")


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
                json={"username": username, "email": email, "password": "TestPass123!"},
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
        """REG-005: Registration succeeds when registration_mode is open."""
        print_section("REG-005: Registration open allows new user")

        await set_registration_mode("open")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"enabledreg_{timestamp}"

            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"{username}@example.com",
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )

            assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
            assert response.json()["user"]["username"] == username
            print_success("Registration enabled allowed new user")

    @pytest.mark.asyncio
    async def test_register_disabled_rejects_when_users_exist(self, test_server):
        """REG-006: Disabled registration returns 403 REGISTRATION_DISABLED when at least one user exists."""
        print_section("REG-006: Disabled registration rejects non-bootstrap user")

        await set_registration_mode("open")

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            seed_username = f"disabledseed_{timestamp}"

            seed_response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": seed_username,
                    "email": f"{seed_username}@example.com",
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )
            assert seed_response.status_code == 201, f"Setup failed: {seed_response.text}"

            try:
                await set_registration_mode("disabled")
                username = f"disabledreg_{timestamp}"

                response = await client.post(
                    f"{API_BASE}/auth/register",
                    json={
                        "username": username,
                        "email": f"{username}@example.com",
                        # Meets the password rules (decision 37): they are checked first, and a weak password would be
                        # refused with PASSWORD_TOO_WEAK before the registration mode is read.
                        "password": "TestPass123!",
                    },
                    timeout=TIMEOUT,
                )

                assert (response.status_code, _error_code(response)) == (403, "REGISTRATION_DISABLED"), f"Expected 403 REGISTRATION_DISABLED, got {response.status_code}: {response.text}"
                print_success("Disabled registration rejected non-bootstrap user")
            finally:
                await set_registration_mode("open")

    @pytest.mark.asyncio
    async def test_register_disabled_allows_bootstrap_when_no_users(self, tmp_path, monkeypatch):
        """REG-007: Disabled registration still allows bootstrap when user count is zero.

        On a private database (a fresh SQLite file under tmp_path with the whole ORM schema), zero
        users and registration_mode=disabled are its real state, not a patched counter. The lane's
        users and global settings are never touched, and the bootstrap administrator no longer
        stays behind in the shared database. LIBREFOLIO_REGISTRATION is removed from this process,
        so that the row alone decides, whatever the shell that started the run had set.
        """
        print_section("REG-007: Disabled registration allows bootstrap user")
        from backend.app.services.accounts.registration_service import effective_registration_mode  # noqa: PLC0415 — release 1.3 module: only this test needs it, and its absence must fail this test alone

        monkeypatch.delenv("LIBREFOLIO_REGISTRATION", raising=False)
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'bootstrap.db'}", poolclass=NullPool)
        try:
            async with engine.begin() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)
            async with AsyncSession(engine) as session:
                session.add(GlobalSetting(key=REGISTRATION_MODE_KEY, value="disabled", value_type="string"))
                await session.commit()

            username = "bootstrapreg"
            async with AsyncSession(engine, expire_on_commit=False) as session:
                assert await user_service.count_users(session) == 0, "Precondition: the private database must have no user"
                assert (await effective_registration_mode(session)).mode == "disabled", "Precondition: registration must be disabled"
                # Keyword arguments, as FastAPI calls the route: E5b added ``background`` before ``session``.
                response = await auth_api.register(
                    AuthRegisterRequest(
                        username=username,
                        email=f"{username}@example.com",
                        password="TestPass123!",
                    ),
                    background=BackgroundTasks(),
                    http_request=_register_http_request(),
                    session=session,
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
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )

            # Try duplicate username
            response = await client.post(
                f"{API_BASE}/auth/register",
                json={
                    "username": username,
                    "email": f"second_{timestamp}@example.com",
                    "password": "TestPass123!",
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
                json={"username": f"user1_{timestamp}", "email": email, "password": "TestPass123!"},
                timeout=TIMEOUT,
            )

            # Try duplicate email
            response = await client.post(
                f"{API_BASE}/auth/register",
                json={"username": f"user2_{timestamp}", "email": email, "password": "TestPass123!"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 400
            assert "email" in response.json()["detail"].lower()
            print_success("Duplicate email correctly rejected")

    @pytest.mark.asyncio
    async def test_register_short_password(self, test_server, lane_accounts):
        """REG-004 — red until A6c (a 422 of the schema): a password of seven characters that meets every other rule → 400 PASSWORD_TOO_WEAK with rules exactly ["min_length"]; no account.

        Decision 37: the length is one of the password rules the backend applies (PWD-001 covers the others); the
        schema keeps only «not empty» (PWD-008).
        """
        print_section("REG-004: Short password rejected")
        username = lane_accounts.new_username("shortpw")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE}/auth/register",
                # Seven characters, with an uppercase and lowercase letters, a digit and a symbol: only the length is missing.
                json={"username": username, "email": f"{username}@example.com", "password": "Short1!"},
                timeout=TIMEOUT,
            )

        _assert_password_too_weak(response, ["min_length"], "POST /auth/register with seven characters")
        assert not await _lane_user_exists(username), f"a refused password must create no account, yet {username} exists"
        print_success("Short password correctly rejected: 400 PASSWORD_TOO_WEAK, rules [min_length]")


class TestLogin:
    """Tests for POST /auth/login."""

    @pytest_asyncio.fixture
    async def test_user(self, test_server):
        """Create a test user for login tests."""
        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"logintest_{timestamp}"
            email = f"login_{timestamp}@example.com"
            password = "LoginPass123!"

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
        from backend.app.services.accounts import settings_service, user_service  # noqa: PLC0415 — test-only local import

        async with httpx.AsyncClient() as client:
            timestamp = int(datetime.now().timestamp() * 1000)
            username = f"loginsettings_{timestamp}"
            email = f"loginsettings_{timestamp}@example.com"
            password = "LoginPass123!"

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
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "TestPass123!"},
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
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "TestPass123!"},
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
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )

            response = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "TestPass123!"},
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
                    "password": "TestPass123!",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "TestPass123!"},
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
            old_password = "OldPass123!"
            new_password = "NewPass456!"

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
                    "password": "CorrectPass123!",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "CorrectPass123!"},
                timeout=TIMEOUT,
            )
            client.cookies.update(login_resp.cookies)

            # Try to change with wrong current password; the new one meets the rules (decision 37), which are checked first
            response = await client.post(
                f"{API_BASE}/auth/change-password",
                json={"current_password": "wrongpassword", "new_password": "NewPass456!"},
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
            password = "SamePass123!"

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
                json={"current_password": "oldpass", "new_password": "NewPass123!"},
                timeout=TIMEOUT,
            )

            assert response.status_code == 401, f"Expected 401, got {response.status_code}"

            print_success("Unauthenticated request correctly rejected")

    @pytest.mark.asyncio
    async def test_change_password_too_short(self, test_server):
        """CHPWD-005 — red until A6c (a 422 of the schema): a new password of seven characters that meets every other rule → 400 PASSWORD_TOO_WEAK with rules exactly ["min_length"]; the password stays the old one.

        Decision 37: the length is one of the password rules the backend applies (PWD-003 covers the others).
        """
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
                    "password": "LongPass123!",
                },
                timeout=TIMEOUT,
            )

            login_resp = await client.post(
                f"{API_BASE}/auth/login",
                json={"username": username, "password": "LongPass123!"},
                timeout=TIMEOUT,
            )
            assert login_resp.status_code == 200, f"Setup: login failed: {login_resp.status_code} {login_resp.text}"
            client.cookies.update(login_resp.cookies)

            # Try short password: seven characters, with an uppercase and lowercase letters, a digit and a symbol
            response = await client.post(
                f"{API_BASE}/auth/change-password",
                json={"current_password": "LongPass123!", "new_password": "Short1!"},
                timeout=TIMEOUT,
            )

            _assert_password_too_weak(response, ["min_length"], "POST /auth/change-password with a new password of seven characters")
            client.cookies.clear()
            old_login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "LongPass123!"}, timeout=TIMEOUT)
            assert old_login.status_code == 200, f"A refused new password must leave the old one in place: login with it got {old_login.status_code} {old_login.text}"

            print_success("Short password correctly rejected: 400 PASSWORD_TOO_WEAK, rules [min_length], the old password kept")


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
        user = _DisposableUser(username=f"cookiesec_{uuid.uuid4().hex[:12]}", password="CookiePass123!")
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
        # A digit at the end whatever the hex holds: both must meet the password rules (decision 37) to register.
        active=_DisposableUser(username=f"loginon_{uuid.uuid4().hex[:12]}", password=f"Active-{uuid.uuid4().hex[:12]}-1"),
        disabled=_DisposableUser(username=f"loginoff_{uuid.uuid4().hex[:12]}", password=f"Disabled-{uuid.uuid4().hex[:12]}-1"),
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


# ============================================================================
# PASSWORD WORK OFF THE EVENT LOOP (V-16, plan 46 §12.7)
# ============================================================================
#
# bcrypt costs about a quarter of a second per call (BCRYPT_ROUNDS = 12), and login, register and
# change-password are `async def` handlers: a bcrypt call made in them holds the worker's event loop,
# which serves no other request meanwhile. The Async I/O Rule (copilot-instructions) wants the call
# in `await asyncio.to_thread(...)`. These tests replace the password function a handler calls with
# a stand-in that holds the thread calling it, as bcrypt does, and keep a heartbeat on the test's
# event loop while the handler runs in-process on a private database. Called in the loop, the
# stand-in leaves no heartbeat inside its run: the whole run is one stall, on any machine. Called in
# a worker thread, it leaves the heartbeat beating. Nothing here measures bcrypt.

#: How long each stand-in holds the thread that calls it: bcrypt's cost (~0.24 s), magnified so that a held loop cannot hide.
_PASSWORD_WORK_SECONDS = 0.4
#: The heartbeat's period on the test's event loop.
_HEARTBEAT_SECONDS = 0.01
#: The longest the event loop may go without a heartbeat while a stand-in runs: far above the period, well below the stand-in's run.
_MAX_STALL_SECONDS = 0.15


@dataclass
class _BlockingStandIn:
    """A password function's stand-in: it holds the thread calling it for _PASSWORD_WORK_SECONDS, as bcrypt does, then answers ``result``.

    Every call is recorded with its arguments bound by name to the real function's signature, so a
    positional and a keyword call read alike, and a call the real function would refuse fails here
    too; and with its run, (start, end) in perf_counter seconds, the heartbeat's clock.
    """

    label: str
    real: Callable[..., object]
    result: object
    calls: list[dict[str, object]] = field(default_factory=list)
    runs: list[tuple[float, float]] = field(default_factory=list)

    def __call__(self, *args: object, **kwargs: object) -> object:
        arguments = inspect.signature(self.real).bind(*args, **kwargs).arguments
        start = time.perf_counter()
        time.sleep(_PASSWORD_WORK_SECONDS)  # the work itself, not a wait for anything: the thread is held as bcrypt holds it
        self.runs.append((start, time.perf_counter()))
        self.calls.append(arguments)
        return self.result


def _block(monkeypatch: pytest.MonkeyPatch, module: ModuleType, name: str, result: object) -> _BlockingStandIn:
    """Replace ``module.name``, the name the handler calls, with a blocking stand-in answering ``result``; monkeypatch puts it back."""
    stand_in = _BlockingStandIn(label=f"{module.__name__}.{name}", real=getattr(module, name), result=result)
    monkeypatch.setattr(module, name, stand_in)
    return stand_in


@contextlib.asynccontextmanager
async def _heartbeat() -> AsyncIterator[list[float]]:
    """Beat on the running event loop every _HEARTBEAT_SECONDS while the body runs; the beats, in perf_counter seconds.

    The first beat is taken before the body starts and the last after it ends. The heartbeat is a task
    of the body's own loop: whatever holds the loop holds the heartbeat too.
    """
    ticks: list[float] = []
    beating = asyncio.Event()
    stop = asyncio.Event()

    async def beat() -> None:
        while True:
            ticks.append(time.perf_counter())
            beating.set()
            if stop.is_set():
                return
            await asyncio.sleep(_HEARTBEAT_SECONDS)

    task = asyncio.create_task(beat())
    await beating.wait()
    try:
        yield ticks
    finally:
        stop.set()
        await task


def _stall(ticks: list[float], run: tuple[float, float]) -> tuple[float, int]:
    """(the longest the event loop went without a beat during ``run``, the beats inside it).

    Only the run counts: what the loop did before or after the password work (a first SQL compile, an
    import) cannot make a stall here. A run held in the loop has no beat inside it: its stall is the
    whole run.
    """
    start, end = run
    inside = [tick for tick in ticks if start < tick < end]
    return max(later - earlier for earlier, later in itertools.pairwise([start, *inside, end])), len(inside)


def _assert_the_loop_kept_beating(handler: str, ticks: list[float], *stand_ins: _BlockingStandIn) -> str:
    """Assert that during each stand-in's run, one each (the caller checked), the loop never went _MAX_STALL_SECONDS without a beat; return what was measured."""
    measured = {stand_in.label: _stall(ticks, stand_in.runs[0]) for stand_in in stand_ins}
    held = {label: stall for label, (stall, _) in measured.items() if stall >= _MAX_STALL_SECONDS}
    assert not held, (
        f"{handler} held the event loop: "
        + "; ".join(f"{stall:.3f} s without a heartbeat while {label} ran" for label, stall in held.items())
        + f" (limit {_MAX_STALL_SECONDS} s; the stand-in holds its thread {_PASSWORD_WORK_SECONDS} s, as bcrypt does for ~0.24 s). Meanwhile the worker serves no other request: the call belongs in await asyncio.to_thread(...)"
    )
    return "; ".join(f"{label}: {beats} beats, longest stall {stall:.3f} s" for label, (stall, beats) in measured.items())


@dataclass(frozen=True)
class _PrivateAccount:
    """A database one test owns entirely, under its tmp_path, with one active account.

    The stored hash is a marker, not a bcrypt hash: only the stand-ins receive it, and they never read it.
    """

    engine: AsyncEngine
    username: str
    password: str
    hashed_password: str


@pytest_asyncio.fixture
async def private_account(tmp_path: Path) -> AsyncIterator[_PrivateAccount]:
    """A fresh SQLite file under tmp_path with the whole ORM schema and one active account, written as a row: no bcrypt runs. Disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'loop.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        account = _PrivateAccount(engine=engine, username="loop_user", password="LoopPass123!", hashed_password="marker-hash-of-loop_user")
        async with AsyncSession(engine) as session:
            session.add(User(username=account.username, email=f"{account.username}@example.com", hashed_password=account.hashed_password))
            await session.commit()
        yield account
    finally:
        await engine.dispose()


async def _stored_hash(engine: AsyncEngine, username: str) -> Optional[str]:
    """The hashed_password the private database holds for ``username``, read in a fresh session; None without such a user."""
    async with AsyncSession(engine) as session:
        return (await session.execute(select(User.hashed_password).where(User.username == username))).scalar_one_or_none()


class TestPasswordWorkLeavesTheEventLoopFree:
    """login, register and change-password in-process, their password functions replaced by blocking stand-ins (V-16).

    Each test replaces the name its handler calls (monkeypatch), runs the handler on a private
    database (private_account) under a heartbeat, and checks, in this order: the handler's outcome
    (the stand-in's answer was used), the stand-in's calls (the handler did the work, once, with the
    right arguments), then the heartbeat during the stand-in's run. The stand-in sleeps because it is
    the work, not to wait for anything: a loop it holds gets no beat at all for the whole run, so the
    red does not depend on the machine's speed.

    Write-safe: everything a test writes is in its own tmp_path; monkeypatch puts the replaced names back.
    """

    @pytest.mark.asyncio
    async def test_the_heartbeat_tells_a_free_event_loop_from_a_held_one(self):
        """LOOP-000 — GUARD, green today and after: the instrument itself, both ways, in the same run.

        A stand-in run in a worker thread leaves the heartbeat beating under the limit; the same
        stand-in called in the loop gets no beat inside its run, a stall over the limit.
        """
        print_section("LOOP-000: the heartbeat tells a free event loop from a held one")
        in_a_thread = _BlockingStandIn(label="a stand-in in a worker thread", real=auth_service.hash_password, result="hash")
        in_the_loop = _BlockingStandIn(label="a stand-in in the event loop", real=auth_service.hash_password, result="hash")

        async with _heartbeat() as ticks:
            assert await asyncio.to_thread(in_a_thread, "password") == "hash", "The stand-in must answer its result from a worker thread"
            assert in_the_loop("password") == "hash", "The stand-in must answer its result in the loop"

        free = _assert_the_loop_kept_beating("asyncio.to_thread", ticks, in_a_thread)
        stall, beats = _stall(ticks, in_the_loop.runs[0])
        assert beats == 0 and stall >= _MAX_STALL_SECONDS, f"A stand-in called in the loop must hold it for its whole run: {beats} beats inside it, longest stall {stall:.3f} s (expected 0 beats, a stall of at least {_MAX_STALL_SECONDS} s)"

        print_success(f"✓ In a worker thread: {free}. In the loop: 0 beats, one stall of {stall:.3f} s")

    @pytest.mark.asyncio
    async def test_login_checks_the_password_off_the_event_loop(self, private_account, monkeypatch):
        """LOOP-001 — NEW, red today: POST /auth/login checks the password in a worker thread; the event loop keeps beating meanwhile.

        verify_password_or_dummy answers False: the login must be refused with the generic 401, after
        one check of the typed password against the account's stored hash. Today the check runs in the
        loop (auth.py, login), and the heartbeat stops for the whole check.
        """
        print_section("LOOP-001: login checks the password off the event loop")
        check = _block(monkeypatch, auth_api, "verify_password_or_dummy", result=False)

        async with _heartbeat() as ticks:
            outcome = await _login_in_process(private_account.engine, private_account.username, private_account.password)

        assert _refusal(outcome) == (401, "Invalid credentials"), f"With the password check answering False, login must refuse with 401 «Invalid credentials»: got {outcome!r}"
        assert check.calls == [{"plain_password": private_account.password, "hashed_password": private_account.hashed_password}], f"login must check the typed password against the account's stored hash, once: {check.calls}"
        measured = _assert_the_loop_kept_beating("login", ticks, check)

        print_success(f"✓ login: 401 after one password check, the loop kept beating ({measured})")

    @pytest.mark.asyncio
    async def test_register_hashes_the_password_off_the_event_loop(self, private_account, monkeypatch):
        """LOOP-002 — POST /auth/register hashes the password in a worker thread; the event loop keeps beating meanwhile.

        Whichever service computes the hash — user_service.create_user until 1.2, the registration
        service from 1.3, under whatever name it imports the function — the call ends in bcrypt's own
        hashpw: the stand-in replaces that one, answering bytes as bcrypt does, and the new user must be
        stored with the stand-in's hash. The accounts variables are removed from this process, and the
        private database's registration_mode row is written ``open`` (no limit): an open registration is
        what register meets. Since lot A6d a database without that row is ``invite`` (decision 36), and the
        private account makes this registration a second one, which would then need an invitation.
        """
        print_section("LOOP-002: register hashes the password off the event loop")
        for variable in ("LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS"):
            monkeypatch.delenv(variable, raising=False)
        async with AsyncSession(private_account.engine) as session:
            session.add(GlobalSetting(key=REGISTRATION_MODE_KEY, value="open", value_type="str"))
            await session.commit()
        stand_in_hash = b"stand-in-hash-of-loop_newcomer"
        hashing = _block(monkeypatch, auth_service.bcrypt, "hashpw", result=stand_in_hash)
        username, password = "loop_newcomer", "NewcomerPass123!"

        async with AsyncSession(private_account.engine, expire_on_commit=False) as session, _heartbeat() as ticks:
            response = await auth_api.register(AuthRegisterRequest(username=username, email=f"{username}@example.com", password=password), background=BackgroundTasks(), http_request=_register_http_request(), session=session)

        assert response.user.username == username, f"register must answer with the new user: got {response!r}"
        assert [call["password"] for call in hashing.calls] == [password.encode("utf-8")], f"register must hash the chosen password, once: {hashing.calls}"
        stored = await _stored_hash(private_account.engine, username)
        assert stored == stand_in_hash.decode("utf-8"), f"The new user must be stored with the hash bcrypt computed, {stand_in_hash!r}: got {stored!r}"
        measured = _assert_the_loop_kept_beating("register", ticks, hashing)

        print_success(f"✓ register: the user stored with the stand-in's hash, the loop kept beating ({measured})")

    @pytest.mark.asyncio
    async def test_change_password_checks_and_hashes_off_the_event_loop(self, private_account, monkeypatch):
        """LOOP-003 — NEW, red today: POST /auth/change-password checks the current password and hashes the new one in worker threads; the event loop keeps beating through both.

        verify_password answers True and hash_password a marker: the account must end up stored with
        that marker. Today both run in the loop (auth.py, change_password), each a stall of its own.
        """
        print_section("LOOP-003: change-password checks and hashes off the event loop")
        check = _block(monkeypatch, auth_api, "verify_password", result=True)
        hashing = _block(monkeypatch, auth_api, "hash_password", result="stand-in-hash-of-the-new-password")
        new_password = "ChangedPass123!"

        async with AsyncSession(private_account.engine, expire_on_commit=False) as session:
            user = await user_service.get_user_by_username(session, private_account.username)
            assert user is not None, f"Setup: {private_account.username} must be in the private database"
            async with _heartbeat() as ticks:
                # Since A4b the handler re-issues the session cookie on the response, its Secure decided by the request: FastAPI hands it both.
                await auth_api.change_password(request=ChangePasswordRequest(current_password=private_account.password, new_password=new_password), response=Response(), http_request=_request("http"), current_user=user, session=session)

        assert check.calls == [{"plain_password": private_account.password, "hashed_password": private_account.hashed_password}], f"change-password must check the current password against the stored hash, once: {check.calls}"
        assert hashing.calls == [{"password": new_password}], f"change-password must hash the new password, once: {hashing.calls}"
        stored = await _stored_hash(private_account.engine, private_account.username)
        assert stored == hashing.result, f"The account must be stored with the new password's hash, {hashing.result!r}: got {stored!r}"
        measured = _assert_the_loop_kept_beating("change_password", ticks, check, hashing)

        print_success(f"✓ change-password: the new hash stored, the loop kept beating ({measured})")


# ============================================================================
# THE PASSWORD RULES ON EVERY NEW PASSWORD (decision 37, lot A6c)
# ============================================================================
#
# The backend holds the password rules (services/accounts/password_policy.py: at least 8 characters, an uppercase and a
# lowercase letter, a digit, a symbol, with Unicode's classes) and applies them to every new password: POST
# /auth/register and POST /auth/change-password here, the reset link in test_registration_api.py, the command line in
# test_dev_cli_image.py. A password that breaks them is refused with 400 {"detail": {"error_code": "PASSWORD_TOO_WEAK",
# "message": ..., "rules": [the codes missed, in the policy's order]}}, before anything else of the request is looked
# at — the current password included —; the schemas keep only «not empty» (422). A password stored before keeps
# working: the login never checks the rules.
#
# On the lane's server, open while this module runs (registration_open_by_default). Every account a test registers or
# writes is named in lane_accounts before the request, and deleted at teardown, after a red too: a refused
# registration that a red lets through leaves nothing behind.

#: The refusal's detail carries exactly these keys.
PASSWORD_TOO_WEAK_KEYS = {"error_code", "message", "rules"}
#: (password, the codes it misses, in the policy's order): every rule alone — with ASCII, and with Unicode classes —, and several.
WEAK_PASSWORDS = [
    pytest.param("Short1!", ["min_length"], id="seven-characters"),
    pytest.param("lowercase-only-1", ["uppercase"], id="no-uppercase"),
    pytest.param("UPPERCASE-ONLY-1", ["lowercase"], id="no-lowercase"),
    pytest.param("No-Digits-Here", ["digit"], id="no-digit"),
    pytest.param("NoSymbols123", ["special"], id="no-symbol"),
    pytest.param("Ecrire12 ", ["special"], id="a-space-is-not-a-symbol"),
    pytest.param("écrire-12", ["uppercase"], id="e-acute-is-lowercase"),
    pytest.param("Écrire²²!", ["digit"], id="superscript-two-is-not-a-digit"),
    pytest.param("testpassword123", ["uppercase", "special"], id="this-modules-old-password"),
    pytest.param("short", ["min_length", "uppercase", "digit", "special"], id="four-rules"),
]
#: Passwords that meet every rule: ASCII, and Unicode classes (É uppercase, é lowercase, ٣ a digit, € a symbol).
STRONG_PASSWORDS = [
    pytest.param("Strong-Pass-2026", id="ascii"),
    pytest.param("Écrire٣٣€", id="unicode-classes"),
]
#: The password of the accounts these tests register: it meets every rule.
PWD_ACCOUNT_PASSWORD = "Before-Change-2026"
#: A password stored before decision 37 that breaks four rules: seven lowercase letters. No route accepts it any more.
LEGACY_PASSWORD = "oldpass"
LEGACY_RULES = ["min_length", "uppercase", "digit", "special"]
#: What the legacy account changes its weak password for: it meets every rule.
UPGRADED_PASSWORD = "Upgraded-Pass-2026"


def _detail(response: httpx.Response) -> object:
    """``detail`` of a JSON body; None for a body without one, or that is not JSON (a 500's text)."""
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("detail") if isinstance(body, dict) else None


def _assert_password_too_weak(response: httpx.Response, rules: list[str], request: str) -> None:
    """``response`` is decision 37's refusal: 400 PASSWORD_TOO_WEAK, a message, and ``rules`` exactly — the codes missed, in the policy's order."""
    detail = _detail(response)
    error_code = detail.get("error_code") if isinstance(detail, dict) else None
    assert (response.status_code, error_code) == (400, "PASSWORD_TOO_WEAK"), f"{request}: expected 400 PASSWORD_TOO_WEAK, got {response.status_code} {response.text}"
    assert isinstance(detail, dict) and set(detail) == PASSWORD_TOO_WEAK_KEYS, f"{request}: the refusal must carry exactly {sorted(PASSWORD_TOO_WEAK_KEYS)}: {detail}"
    assert isinstance(detail["message"], str) and detail["message"].strip(), f"{request}: the refusal must carry a message: {detail}"
    assert detail["rules"] == rules, f"{request}: rules must be exactly the codes missed, in the policy's order, {rules}: got {detail['rules']}"


async def _lane_user_exists(username: str) -> bool:
    """Whether the lane's database holds ``username``, read in a fresh session."""
    async with AsyncSession(get_async_engine()) as session:
        return await user_service.get_user_by_username(session, username) is not None


@dataclass
class _LaneAccounts:
    """The accounts one test registers or writes on the lane, by username: named before the request — a red may let one through —, deleted at teardown."""

    usernames: list[str] = field(default_factory=list)

    def new_username(self, prefix: str) -> str:
        username = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self.usernames.append(username)
        return username


async def _delete_lane_accounts(usernames: list[str]) -> list[str]:
    """Delete those of these accounts the lane holds, through user_service.delete_user, each in a session of its own; what failed."""
    errors: list[str] = []
    for username in usernames:
        async with AsyncSession(get_async_engine()) as session:
            try:
                user = await user_service.get_user_by_username(session, username)
                if user is not None:
                    await user_service.delete_user(session, user.id)
            except Exception as exc:  # every account gets its attempt; the failures are reported together
                errors.append(f"{username}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def lane_accounts(test_server) -> AsyncIterator[_LaneAccounts]:
    """The accounts this test registers or writes on the lane's server, deleted at teardown, after a red too."""
    accounts = _LaneAccounts()
    try:
        yield accounts
    finally:
        errors = await _delete_lane_accounts(accounts.usernames)
        assert not errors, f"Cleanup: could not delete what this test wrote on the lane: {errors}"


@pytest_asyncio.fixture
async def legacy_account(lane_accounts: _LaneAccounts) -> _DisposableUser:
    """An account of this test whose stored password predates decision 37 and breaks four rules (LEGACY_PASSWORD).

    Written as a row on the lane — no route accepts that password any more, and a row needs none —, with a real bcrypt
    hash of it, so that it signs in; lane_accounts deletes it at teardown.
    """
    user = _DisposableUser(username=lane_accounts.new_username("pwd_legacy"), password=LEGACY_PASSWORD)
    hashed = await asyncio.to_thread(auth_service.hash_password, user.password)
    async with AsyncSession(get_async_engine()) as session:
        session.add(User(username=user.username, email=f"{user.username}@example.com", hashed_password=hashed))
        await session.commit()
    assert await _lane_user_exists(user.username), f"Setup: {user.username} must be in the lane's database"
    return user


async def _register_on_lane(username: str, password: str) -> httpx.Response:
    """POST /auth/register on the lane's server from a client of its own: ``username``, ``<username>@example.com``, ``password``."""
    async with httpx.AsyncClient() as client:
        return await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password}, timeout=TIMEOUT)


async def _change_password_on_lane(token: str, current_password: str, new_password: str) -> httpx.Response:
    """POST /auth/change-password on the lane's server, the session token sent explicitly from a client of its own."""
    async with httpx.AsyncClient() as client:
        return await client.post(f"{API_BASE}/auth/change-password", json={"current_password": current_password, "new_password": new_password}, headers={"Cookie": f"{auth_api.SESSION_COOKIE_NAME}={token}"}, timeout=TIMEOUT)


async def _me_on_lane(token: str) -> int:
    """GET /auth/me with one session token, sent explicitly from a client of its own: the status code."""
    async with httpx.AsyncClient() as client:
        return (await client.get(f"{API_BASE}/auth/me", headers={"Cookie": f"{auth_api.SESSION_COOKIE_NAME}={token}"}, timeout=TIMEOUT)).status_code


async def _registered_and_signed_in(lane_accounts: _LaneAccounts, prefix: str) -> tuple[str, str]:
    """An account of this test registered on the lane with PWD_ACCOUNT_PASSWORD, then signed in: (username, session token)."""
    username = lane_accounts.new_username(prefix)
    registered = await _register_on_lane(username, PWD_ACCOUNT_PASSWORD)
    assert registered.status_code == 201, f"Setup: registering {username} failed: {registered.status_code} {registered.text}"
    signed_in = await _post_login(username, PWD_ACCOUNT_PASSWORD)
    assert signed_in.status_code == 200, f"Setup: signing in as {username} failed: {signed_in.status_code} {signed_in.text}"
    token, _ = _session_set_cookie(signed_in)
    return username, token


class TestPasswordRulesOnEveryNewPassword:
    """Decision 37 on the lane's server: register and change-password refuse a password that breaks the rules, and say which; the login never checks them."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("password", "rules"), WEAK_PASSWORDS)
    async def test_register_refuses_a_password_that_breaks_the_rules(self, lane_accounts, password, rules):
        """PWD-001 — NEW, red today (201, or a 422 of the schema under eight characters): POST /auth/register with a password that breaks the rules → 400 PASSWORD_TOO_WEAK, a message, and ``rules`` exactly the codes missed, in the policy's order; no account."""
        print_section(f"PWD-001: register refuses {password!r}")
        username = lane_accounts.new_username("pwd_register")

        response = await _register_on_lane(username, password)

        _assert_password_too_weak(response, rules, f"POST /auth/register with {password!r}")
        assert not await _lane_user_exists(username), f"a refused password must create no account, yet {username} exists"
        print_success(f"✓ {password!r}: 400 PASSWORD_TOO_WEAK, rules {rules}, no account")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("password", STRONG_PASSWORDS)
    async def test_register_accepts_a_password_that_meets_every_rule(self, lane_accounts, password):
        """PWD-002 — GUARD, green today and after: a password that meets every rule, with ASCII or with Unicode classes, registers (201) and signs in: the API applies the policy's classes, not ASCII ones."""
        print_section(f"PWD-002: register accepts {password!r}")
        username = lane_accounts.new_username("pwd_strong")

        registered = await _register_on_lane(username, password)
        signed_in = await _post_login(username, password)

        assert registered.status_code == 201, f"{password!r} meets every rule: POST /auth/register must answer 201, got {registered.status_code} {registered.text}"
        assert signed_in.status_code == 200, f"the account must sign in with {password!r}: {signed_in.status_code} {signed_in.text}"
        print_success(f"✓ {password!r}: registered and signed in")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("password", "rules"), WEAK_PASSWORDS)
    async def test_change_password_refuses_a_new_password_that_breaks_the_rules(self, lane_accounts, password, rules):
        """PWD-003 — NEW, red today (200, or a 422 of the schema under eight characters): POST /auth/change-password with a new password that breaks the rules → 400 PASSWORD_TOO_WEAK with exactly the codes missed; nothing changes: no session cookie set, the session still works, the old password still signs in and the refused one does not."""
        print_section(f"PWD-003: change-password refuses {password!r}")
        username, token = await _registered_and_signed_in(lane_accounts, "pwd_change")

        response = await _change_password_on_lane(token, PWD_ACCOUNT_PASSWORD, password)

        _assert_password_too_weak(response, rules, f"POST /auth/change-password with the new password {password!r}")
        assert _session_set_cookies(response) == [], f"a refused change must set no session cookie: {response.headers.get_list('set-cookie')}"
        assert await _me_on_lane(token) == 200, "a refused change must end no session: the session from before must still work"
        old, refused = await _post_login(username, PWD_ACCOUNT_PASSWORD), await _post_login(username, password)
        assert (old.status_code, refused.status_code) == (200, 401), f"the password must stay the old one: login with the old one {old.status_code}, with the refused one {refused.status_code}"
        print_success(f"✓ {password!r}: 400 PASSWORD_TOO_WEAK, rules {rules}; the password and the session as they were")

    @pytest.mark.asyncio
    async def test_change_password_checks_the_new_password_before_the_current_one(self, lane_accounts):
        """PWD-004 — NEW, red today (400 «Current password is incorrect»): a new password that breaks the rules with a wrong current password → 400 PASSWORD_TOO_WEAK: the new password is checked before anything else of the request; the password unchanged."""
        print_section("PWD-004: change-password checks the new password first")
        username, token = await _registered_and_signed_in(lane_accounts, "pwd_first")

        response = await _change_password_on_lane(token, _wrong_password(), "weakpassword")

        _assert_password_too_weak(response, ["uppercase", "digit", "special"], "POST /auth/change-password with a wrong current password and the new password 'weakpassword'")
        signed_in = await _post_login(username, PWD_ACCOUNT_PASSWORD)
        assert signed_in.status_code == 200, f"the password must stay the old one: {signed_in.status_code} {signed_in.text}"
        print_success("✓ wrong current password and a weak new one: PASSWORD_TOO_WEAK, the new password first")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("password", STRONG_PASSWORDS)
    async def test_change_password_accepts_a_new_password_that_meets_every_rule(self, lane_accounts, password):
        """PWD-005 — GUARD, green today and after: a new password that meets every rule, with ASCII or with Unicode classes → 200; the new password signs in, the old one does not."""
        print_section(f"PWD-005: change-password accepts {password!r}")
        username, token = await _registered_and_signed_in(lane_accounts, "pwd_changed")

        response = await _change_password_on_lane(token, PWD_ACCOUNT_PASSWORD, password)

        assert response.status_code == 200, f"{password!r} meets every rule: POST /auth/change-password must answer 200, got {response.status_code} {response.text}"
        new, old = await _post_login(username, password), await _post_login(username, PWD_ACCOUNT_PASSWORD)
        assert (new.status_code, old.status_code) == (200, 401), f"the new password must sign in and the old one must not: {new.status_code}, {old.status_code}"
        print_success(f"✓ {password!r}: changed, and signs in")

    @pytest.mark.asyncio
    async def test_a_stored_weak_password_still_signs_in(self, legacy_account):
        """PWD-006 — GUARD, green today and after: the login never checks the rules. An account whose stored password breaks four of them signs in with it: 200 and one session cookie."""
        print_section("PWD-006: a stored weak password still signs in")
        response = await _post_login(legacy_account.username, legacy_account.password)

        assert response.status_code == 200, f"a password stored before decision 37 must still sign in, the login never checks the rules: {response.status_code} {response.text}"
        assert len(_session_set_cookies(response)) == 1, f"the login must set one session cookie: {response.headers.get_list('set-cookie')}"
        print_success(f"✓ {LEGACY_PASSWORD!r}, stored before the rules: 200 and a session")

    @pytest.mark.asyncio
    async def test_a_stored_weak_password_is_changed_only_for_one_that_meets_the_rules(self, legacy_account):
        """PWD-007 — NEW, red today (a 422 of the schema, seven characters): signed in with its weak password, the account «changes» it to itself → 400 PASSWORD_TOO_WEAK with the four codes — the rules before «must be different» —; then to one that meets the rules → 200, the weak current password never judged. The new one signs in, the weak one no more."""
        print_section("PWD-007: a stored weak password is changed only for one that meets the rules")
        signed_in = await _post_login(legacy_account.username, legacy_account.password)
        assert signed_in.status_code == 200, f"Setup: the legacy account must sign in: {signed_in.status_code} {signed_in.text}"
        token, _ = _session_set_cookie(signed_in)

        same = await _change_password_on_lane(token, LEGACY_PASSWORD, LEGACY_PASSWORD)
        upgraded = await _change_password_on_lane(token, LEGACY_PASSWORD, UPGRADED_PASSWORD)

        _assert_password_too_weak(same, LEGACY_RULES, f"POST /auth/change-password from the stored weak password {LEGACY_PASSWORD!r} to itself")
        assert upgraded.status_code == 200, f"a weak current password is still the current password: changing it for one that meets the rules must answer 200, got {upgraded.status_code} {upgraded.text}"
        new, old = await _post_login(legacy_account.username, UPGRADED_PASSWORD), await _post_login(legacy_account.username, LEGACY_PASSWORD)
        assert (new.status_code, old.status_code) == (200, 401), f"the new password must sign in and the weak one must not: {new.status_code}, {old.status_code}"
        print_success("✓ to itself: PASSWORD_TOO_WEAK; to a password that meets the rules: 200")

    @pytest.mark.asyncio
    async def test_an_empty_password_is_still_a_schema_error(self, lane_accounts):
        """PWD-008 — GUARD, green today and after: the schemas keep «not empty». POST /auth/register with an empty password and POST /auth/change-password with an empty new password → 422, a request validation error, not PASSWORD_TOO_WEAK; no account."""
        print_section("PWD-008: an empty password is a 422 of the schema")
        _, token = await _registered_and_signed_in(lane_accounts, "pwd_empty")
        newcomer = lane_accounts.new_username("pwd_empty_new")

        registered = await _register_on_lane(newcomer, "")
        changed = await _change_password_on_lane(token, PWD_ACCOUNT_PASSWORD, "")

        assert registered.status_code == 422, f"an empty password is a request validation error: POST /auth/register must answer 422, got {registered.status_code} {registered.text}"
        assert changed.status_code == 422, f"an empty new password is a request validation error: POST /auth/change-password must answer 422, got {changed.status_code} {changed.text}"
        assert not await _lane_user_exists(newcomer), f"a refused registration must create no account, yet {newcomer} exists"
        print_success("✓ empty: 422 on both routes")


# ============================================================================
# NO TYPED IDENTIFIER IN THE LOG OF A SIGN-IN — lot A-22 (LOGIN-027 to LOGIN-033), in-process on a private database
# ============================================================================
# Workstream E's rule: no email address in any log. The login field takes a username or an email address, so a sign-in
# that logs what was typed writes an address whenever one was typed. These imports and helpers serve
# TestSignInLogsNoTypedIdentifier only, so they live next to it. The lane's server writes its logs in a process of its
# own, which no test can capture: so these cases run in-process, as TestProfileLogsNoAddress (test_profile_api.py, lot
# A7c) runs its own, on a private instance — the real auth router, mounted as api/v1/router.py mounts it, in an app of
# this test whose get_session_generator opens sessions on a private SQLite file under tmp_path, seeded as a new install
# (the default global settings, email verification off among them, no account). No sign-in reaches the lane. bcrypt
# runs at its lowest cost in this process (auth_service.BCRYPT_ROUNDS = 4), the dummy hash of an unknown login included,
# in a cache of the test's own; the lane's server keeps its own. Each address has a local part of its own that no
# username contains: a log may carry the stored username, never the address, and the check looks for the local part
# alone too.

import functools
import logging
from collections.abc import Iterable
from typing import Any

import structlog
from fastapi import FastAPI
from structlog.testing import capture_logs

from backend.app.config import API_V1_PREFIX
from backend.app.db.models import AccountTokenPurpose
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import token_service
from backend.app.services.accounts.settings_service import initialize_global_settings

#: The logger of POST /auth/login: the auth routes' structlog.get_logger(__name__).
_SIGN_IN_LOGGER = auth_api.__name__
#: The canary logged through _SIGN_IN_LOGGER, to both captures.
_SIGN_IN_CANARY = f"canary: the capture sees the events of {_SIGN_IN_LOGGER}"
#: The events of POST /auth/login, word for word: the three failures of lot A-22, the refusal of an account waiting for
#: its email verification (lot E5b), and the success.
_LOGIN_FAILED_USER_NOT_FOUND = "Login failed: user not found"
_LOGIN_FAILED_WRONG_PASSWORD = "Login failed: wrong password"
_LOGIN_FAILED_USER_INACTIVE = "Login failed: user inactive"
_LOGIN_REFUSED_EMAIL_NOT_VERIFIED = "Login refused: email not verified"
_USER_LOGGED_IN = "User logged in"
#: The keys of a captured structlog event that are not fields of the call: the message, the level, a timestamp.
_STRUCTLOG_KEYS = frozenset({"event", "log_level", "timestamp"})
#: The SQL loggers. Below WARNING they print every statement with its parameters and every row read, so the identifier
#: the login's SELECT looks for and the address of the row it reads. configure_logging (backend/app/logging_config.py)
#: sets them to WARNING: a running server never writes those records, caplog sees them only because it lowers the root's
#: level. UADM-030 (test_users_admin_api.py) pins that premise, read from configure_logging's source.
_SIGN_IN_SQL_LOGGERS = ("aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool")
#: The password of every account of the private instance.
_SIGN_IN_PASSWORD = "Sign-In-Pass-2026"


@dataclass(frozen=True)
class _PrivateSignIn:
    """An instance of one test: the auth router, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _private_sign_in_app(engine: AsyncEngine) -> FastAPI:
    """The real auth router, mounted under the API prefix as ``api/v1/router.py`` mounts it; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    app.include_router(auth_api.router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private_sign_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_PrivateSignIn]:
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with, no account; bcrypt at cost 4. Disposed at teardown.

    The dummy hash an unknown login is checked against is computed once per process (functools.cache), at the cost of
    its first call: the test gets a cache of its own, so a dummy of cost 4 never outlives it (LOGIN-024 pins the real
    cost on the process's own).
    """
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_service, "_dummy_password_hash", functools.cache(auth_service._dummy_password_hash.__wrapped__))
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'sign-in-logs.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _PrivateSignIn(engine=engine, app=_private_sign_in_app(engine))
    finally:
        await engine.dispose()


@dataclass(frozen=True)
class _SignInAccount:
    """An account of the private instance: its id, its username, and its address, whose local part the username does not contain."""

    user_id: int
    username: str
    email: str


async def _sign_in_account(private: _PrivateSignIn, *, active: bool = True, awaiting_verification: bool = False) -> _SignInAccount:
    """An account written as a row with a real bcrypt hash of _SIGN_IN_PASSWORD (cost 4): all before any capture.

    ``active=False`` alone is a plainly deactivated account, as an administrator leaves it: no verification token.
    ``awaiting_verification`` adds one unspent email-verification token, the «hold» registration gives an account that
    waits for its link (email_verification.hold_for_verification); such an account is inactive.
    """
    assert not (active and awaiting_verification), "Setup: an account waiting for its email verification is inactive"
    username, email = f"signin_{uuid.uuid4().hex[:12]}", f"inbox_{uuid.uuid4().hex[:12]}@example.com"
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(_SIGN_IN_PASSWORD), is_active=active)
        session.add(user)
        await session.flush()
        if awaiting_verification:
            await token_service.issue_token(session, AccountTokenPurpose.EMAIL_VERIFICATION, user_id=user.id)
        await session.commit()
    assert user.id is not None and user.is_active is active, f"Setup: {username} must be written {'active' if active else 'inactive'}: {user!r}"
    return _SignInAccount(user_id=user.id, username=username, email=email)


async def _logged_sign_in(private: _PrivateSignIn, identifier: str, password: str, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> tuple[httpx.Response, list[dict[str, Any]], list[logging.LogRecord]]:
    """POST /auth/login on the private instance with ``identifier`` typed in the login field, from a client of its own,
    and everything that request logged, from the canary to the answer: the structlog events (capture_logs) and the stdlib
    records (caplog at DEBUG, on the root and on _SIGN_IN_LOGGER, enabled even if a configuration disabled it).

    Barrier first: the canary through _SIGN_IN_LOGGER must reach both captures, or a capture that sees nothing would pass
    for a request that logs nothing.
    """
    monkeypatch.setattr(logging.getLogger(_SIGN_IN_LOGGER), "disabled", False)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=_SIGN_IN_LOGGER)
    caplog.clear()
    with capture_logs() as events:
        structlog.get_logger(_SIGN_IN_LOGGER).debug(_SIGN_IN_CANARY)
        logging.getLogger(_SIGN_IN_LOGGER).debug(_SIGN_IN_CANARY)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=private.app), base_url="http://test", timeout=TIMEOUT) as client:
            response = await client.post(f"{API_V1_PREFIX}/auth/login", json={"username": identifier, "password": password})
    records = list(caplog.records)
    assert _SIGN_IN_CANARY in {event.get("event") for event in events}, f"barrier: structlog events of {_SIGN_IN_LOGGER} do not reach capture_logs"
    assert (_SIGN_IN_LOGGER, _SIGN_IN_CANARY) in {(record.name, record.getMessage()) for record in records}, f"barrier: stdlib records of {_SIGN_IN_LOGGER} do not reach caplog at DEBUG"
    return response, events, records


def _shows_the_identifier(text: str, identifiers: Iterable[str]) -> bool:
    """Whether ``text`` shows one of ``identifiers``, whole or, for an address, by its local part alone, compared in lower case."""
    lowered = text.lower()
    return any(identifier.lower() in lowered or identifier.lower().partition("@")[0] in lowered for identifier in identifiers)


def _sign_in_record_text(record: logging.LogRecord) -> str:
    """All a stdlib record shows: its message and every attribute."""
    return record.getMessage() + repr(vars(record))


def _sign_in_record_written_by_a_server(record: logging.LogRecord) -> bool:
    """Whether a running server writes ``record``: every record but those below WARNING of the SQL loggers and their children."""
    of_sql = any(record.name == name or record.name.startswith(f"{name}.") for name in _SIGN_IN_SQL_LOGGERS)
    return record.levelno >= logging.WARNING or not of_sql


def _assert_identifier_not_logged(events: list[dict[str, Any]], records: list[logging.LogRecord], identifiers: Iterable[str], call: str) -> None:
    """No structlog event, and no stdlib record a server would write, shows one of ``identifiers``: in any key, value or
    message, whole or, for an address, by its local part, in any case."""
    needles = sorted(set(identifiers))
    leaked_events = [event for event in events if _shows_the_identifier(repr(event), needles)]
    leaked_records = [f"{record.name}: {record.getMessage()}" for record in records if _sign_in_record_written_by_a_server(record) and _shows_the_identifier(_sign_in_record_text(record), needles)]
    assert leaked_events == [], f"{call}: structlog events showing {needles}, whole or by the local part: {leaked_events}"
    assert leaked_records == [], f"{call}: stdlib records showing {needles}, whole or by the local part: {leaked_records}"


def _the_sign_in_event(events: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """The event ``name`` of the capture, asserted to be there once."""
    matching = [event for event in events if event.get("event") == name]
    assert len(matching) == 1, f"The sign-in must log «{name}» once: {matching}"
    return matching[0]


def _own_fields(event: dict[str, Any]) -> set[str]:
    """The keys of a captured event beyond _STRUCTLOG_KEYS: the fields the logging call itself passed."""
    return set(event) - _STRUCTLOG_KEYS


class TestSignInLogsNoTypedIdentifier:
    """Lot A-22 (release 1.3, workstream A): POST /auth/login writes in no log the identifier typed in the login field —
    a username or an email address —, after workstream E's rule: no email address in any log. The three failures keep
    their messages word for word: «Login failed: user not found» carries nothing of what was typed (no ``username`` key,
    no key holding it); «Login failed: wrong password» and «Login failed: user inactive» carry the account's
    ``user_id`` and no ``username`` key. The success's «User logged in» keeps ``user_id`` and the stored ``username``.

    What is checked is everything the request logged, captured at DEBUG by ``_logged_sign_in``: no structlog event and
    no stdlib record shows the typed address (or the account's own address), whole or by its local part, in any case —
    the SQL loggers' records below WARNING aside, which no server writes (``_SIGN_IN_SQL_LOGGERS``).

    Today the three failures log ``username=`` with what was typed: LOGIN-027 to LOGIN-031 are red until A-22, on that
    keyword alone (every answer is already the contract's). LOGIN-032, the success, and LOGIN-033, the refusal of an
    account waiting for its email verification (lot E5b, ``user_id`` only), log no address today and are guards.

    Write-safe: every account lives in the test's own tmp_path (private_sign_in), and no sign-in reaches the lane.
    """

    @pytest.mark.asyncio
    async def test_an_unknown_address_is_not_logged(self, private_sign_in: _PrivateSignIn, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """LOGIN-027 — NEW, red until A-22, on the ``username=`` keyword alone: «Login failed: user not found» carries
        the address as typed. An address no account has, typed to sign in: 401 «Invalid credentials», no event and no
        record of that request shows the address, whole or by its local part, and «Login failed: user not found» is
        there once, without a ``username`` key."""
        print_section("LOGIN-027: an unknown address typed to sign in is not logged")
        typed = f"ghost.{uuid.uuid4().hex[:12]}@example.com"

        response, events, records = await _logged_sign_in(private_sign_in, typed, _wrong_password(), caplog, monkeypatch)

        assert response.status_code == 401 and response.json() == INVALID_CREDENTIALS, f"barrier: an unknown address must get 401 {INVALID_CREDENTIALS}: {response.status_code} {response.text}"
        _assert_identifier_not_logged(events, records, [typed], "POST /auth/login with an unknown address")
        event = _the_sign_in_event(events, _LOGIN_FAILED_USER_NOT_FOUND)
        assert "username" not in event, f"«{_LOGIN_FAILED_USER_NOT_FOUND}» must carry no 'username' key: {event}"
        print_success(f"✓ 401; {len(events)} events and {len(records)} records without the address; no username key")

    @pytest.mark.asyncio
    async def test_an_unknown_username_is_not_logged(self, private_sign_in: _PrivateSignIn, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """LOGIN-028 — NEW, red until A-22, on the ``username=`` keyword alone: «Login failed: user not found» carries
        the name as typed. A username no account has, typed to sign in: 401 «Invalid credentials», the typed name
        appears in no event and no record of that request, and «Login failed: user not found» is there once, without a
        ``username`` key."""
        print_section("LOGIN-028: an unknown username typed to sign in is not logged")
        typed = f"ghost_{uuid.uuid4().hex[:12]}"

        response, events, records = await _logged_sign_in(private_sign_in, typed, _wrong_password(), caplog, monkeypatch)

        assert response.status_code == 401 and response.json() == INVALID_CREDENTIALS, f"barrier: an unknown username must get 401 {INVALID_CREDENTIALS}: {response.status_code} {response.text}"
        _assert_identifier_not_logged(events, records, [typed], "POST /auth/login with an unknown username")
        event = _the_sign_in_event(events, _LOGIN_FAILED_USER_NOT_FOUND)
        assert "username" not in event, f"«{_LOGIN_FAILED_USER_NOT_FOUND}» must carry no 'username' key: {event}"
        print_success(f"✓ 401; {len(events)} events and {len(records)} records without the typed name; no username key")

    @pytest.mark.asyncio
    async def test_a_wrong_password_with_the_address_logs_the_user_id_not_the_address(self, private_sign_in: _PrivateSignIn, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """LOGIN-029 — NEW, red until A-22, on the ``username=`` keyword alone: «Login failed: wrong password» carries
        the address as typed. An active account signed in by its address with a wrong password: 401 «Invalid
        credentials», no event and no record of that request shows the address, and «Login failed: wrong password» is
        there once, with the account's ``user_id`` and without a ``username`` key."""
        print_section("LOGIN-029: a wrong password typed with the address logs the user_id, not the address")
        account = await _sign_in_account(private_sign_in)

        response, events, records = await _logged_sign_in(private_sign_in, account.email, _wrong_password(), caplog, monkeypatch)

        assert response.status_code == 401 and response.json() == INVALID_CREDENTIALS, f"barrier: a wrong password must get 401 {INVALID_CREDENTIALS}: {response.status_code} {response.text}"
        _assert_identifier_not_logged(events, records, [account.email], "POST /auth/login by the address with a wrong password")
        event = _the_sign_in_event(events, _LOGIN_FAILED_WRONG_PASSWORD)
        assert "username" not in event, f"«{_LOGIN_FAILED_WRONG_PASSWORD}» must carry no 'username' key: {event}"
        assert event.get("user_id") == account.user_id, f"«{_LOGIN_FAILED_WRONG_PASSWORD}» must carry the account's user_id, {account.user_id}: {event}"
        print_success(f"✓ 401; {len(events)} events and {len(records)} records without the address; user_id {account.user_id}")

    @pytest.mark.asyncio
    async def test_a_wrong_password_with_the_username_logs_only_the_user_id(self, private_sign_in: _PrivateSignIn, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """LOGIN-030 — NEW, red until A-22: «Login failed: wrong password» carries ``username``, here the name as typed,
        which is also the stored one. An active account signed in by its username with a wrong password: 401 «Invalid
        credentials», its address in no event and no record of that request, and «Login failed: wrong password» there
        once with exactly one field of its own, the account's ``user_id``: no ``username``, typed or stored."""
        print_section("LOGIN-030: a wrong password typed with the username logs the user_id only")
        account = await _sign_in_account(private_sign_in)

        response, events, records = await _logged_sign_in(private_sign_in, account.username, _wrong_password(), caplog, monkeypatch)

        assert response.status_code == 401 and response.json() == INVALID_CREDENTIALS, f"barrier: a wrong password must get 401 {INVALID_CREDENTIALS}: {response.status_code} {response.text}"
        _assert_identifier_not_logged(events, records, [account.email], "POST /auth/login by the username with a wrong password")
        event = _the_sign_in_event(events, _LOGIN_FAILED_WRONG_PASSWORD)
        assert _own_fields(event) == {"user_id"} and event["user_id"] == account.user_id, f"«{_LOGIN_FAILED_WRONG_PASSWORD}» must carry exactly one field beside {sorted(_STRUCTLOG_KEYS)}, user_id={account.user_id}, and no username: {event}"
        print_success(f"✓ 401; the event's own fields are exactly user_id={account.user_id}")

    @pytest.mark.asyncio
    async def test_a_deactivated_account_signed_in_by_address_logs_the_user_id_not_the_address(self, private_sign_in: _PrivateSignIn, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """LOGIN-031 — NEW, red until A-22, on the ``username=`` keyword alone: «Login failed: user inactive» carries
        the address as typed. A plainly deactivated account — inactive, without a verification token, as an
        administrator leaves it; an account waiting for its email verification gets EMAIL_NOT_VERIFIED instead
        (LOGIN-033) — signed in by its address with the right password: 403 ACCOUNT_DISABLED, no event and no record of
        that request shows the address, and «Login failed: user inactive» is there once, with the account's ``user_id``
        and without a ``username`` key."""
        print_section("LOGIN-031: a deactivated account signed in by its address logs the user_id, not the address")
        account = await _sign_in_account(private_sign_in, active=False)

        response, events, records = await _logged_sign_in(private_sign_in, account.email, _SIGN_IN_PASSWORD, caplog, monkeypatch)

        assert response.status_code == 403 and response.json() == {"detail": ACCOUNT_DISABLED_DETAIL}, f"barrier: a deactivated account with the right password must get 403 with detail {ACCOUNT_DISABLED_DETAIL}: {response.status_code} {response.text}"
        _assert_identifier_not_logged(events, records, [account.email], "POST /auth/login by the address of a deactivated account")
        event = _the_sign_in_event(events, _LOGIN_FAILED_USER_INACTIVE)
        assert "username" not in event, f"«{_LOGIN_FAILED_USER_INACTIVE}» must carry no 'username' key: {event}"
        assert event.get("user_id") == account.user_id, f"«{_LOGIN_FAILED_USER_INACTIVE}» must carry the account's user_id, {account.user_id}: {event}"
        print_success(f"✓ 403 ACCOUNT_DISABLED; {len(events)} events and {len(records)} records without the address; user_id {account.user_id}")

    @pytest.mark.asyncio
    async def test_a_sign_in_by_address_logs_the_stored_username_not_the_address(self, private_sign_in: _PrivateSignIn, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """LOGIN-032 — GUARD, green today and after: an active account signed in by its address with the right password:
        200, no event and no record of that request shows the address, and «User logged in» is there once with the
        account's ``user_id`` and its stored ``username`` — what a sign-in may log, never what was typed."""
        print_section("LOGIN-032: a sign-in by the address logs the stored username, not the address")
        account = await _sign_in_account(private_sign_in)

        response, events, records = await _logged_sign_in(private_sign_in, account.email, _SIGN_IN_PASSWORD, caplog, monkeypatch)

        assert response.status_code == 200 and response.json()["user"]["id"] == account.user_id, f"barrier: the account must sign in by its address with its password: {response.status_code} {response.text}"
        _assert_identifier_not_logged(events, records, [account.email], "POST /auth/login by the address with the right password")
        event = _the_sign_in_event(events, _USER_LOGGED_IN)
        assert (event.get("user_id"), event.get("username")) == (account.user_id, account.username), f"«{_USER_LOGGED_IN}» keeps user_id and the stored username: {event}"
        print_success(f"✓ 200; {len(events)} events and {len(records)} records without the address; user_id and the stored username")

    @pytest.mark.asyncio
    async def test_an_account_awaiting_verification_signed_in_by_address_logs_no_address(self, private_sign_in: _PrivateSignIn, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """LOGIN-033 — GUARD, green today and after: an account waiting for its email verification (lot E5b) — inactive,
        with an unspent verification token — signed in by its address with the right password: 403 EMAIL_NOT_VERIFIED,
        no event and no record of that request shows the address, and «Login refused: email not verified» is there
        once, with the account's ``user_id`` and without a ``username`` key."""
        print_section("LOGIN-033: an account awaiting its email verification, signed in by its address, logs no address")
        account = await _sign_in_account(private_sign_in, active=False, awaiting_verification=True)

        response, events, records = await _logged_sign_in(private_sign_in, account.email, _SIGN_IN_PASSWORD, caplog, monkeypatch)

        assert (response.status_code, _error_code(response)) == (403, "EMAIL_NOT_VERIFIED"), f"barrier: an account waiting for its email verification, with the right password, must get 403 EMAIL_NOT_VERIFIED: {response.status_code} {response.text}"
        _assert_identifier_not_logged(events, records, [account.email], "POST /auth/login by the address of an account waiting for its verification")
        event = _the_sign_in_event(events, _LOGIN_REFUSED_EMAIL_NOT_VERIFIED)
        assert "username" not in event and event.get("user_id") == account.user_id, f"«{_LOGIN_REFUSED_EMAIL_NOT_VERIFIED}» carries the account's user_id, {account.user_id}, and no 'username' key: {event}"
        print_success(f"✓ 403 EMAIL_NOT_VERIFIED; {len(events)} events and {len(records)} records without the address; user_id {account.user_id}")
