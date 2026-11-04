"""
Profile Update API Tests

Tests for PUT /auth/profile endpoint.

Lot A6e (release 1.3, workstream A; security review of E3): the session cookie alone no longer changes the email.
Before, a short access to someone else's session became a permanent takeover: change the email, ask for a password
reset, choose the password. The contract, over HTTP on the lane's server:

- C1: the body may carry ``current_password`` (at least one character);
- C2: an email change — ``email`` given and different from the stored one, compared exactly — needs the current
  password, checked before anything else, uniqueness included: missing → 400 ``CURRENT_PASSWORD_REQUIRED``, wrong →
  400 ``CURRENT_PASSWORD_INVALID``, both as ``{"detail": {"error_code": ..., "message": ...}}``, and nothing is
  written. So nobody without the password learns whether an address is already registered. A username-only change,
  or the account's own email sent again, needs no password, as before;
- C3: after an email change every other session of the account is refused (401), and the response sets a new
  ``session`` cookie that keeps the current device signed in. A username-only change ends no session.

C6 (an email change resets ``email_verified_at``) is a service test, in test_services/test_user_profile.py.
The tests of TestEmailChangeNeedsThePassword own their accounts: registered here, deleted at teardown, after a red too.
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import httpx
import pytest
import pytest_asyncio

from backend.app.api.v1.auth import SESSION_COOKIE_NAME
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 10.0
#: The password create_and_login_user gives every account it creates; no test of this file changes it.
TEST_PASSWORD = "TestPass123!"


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
    # Time and randomness: a timestamp alone collides when two accounts are created in the same millisecond.
    tag = f"{int(datetime.now().timestamp() * 1000)}_{uuid.uuid4().hex[:8]}"
    username = f"profiletest_{tag}"
    email = f"profiletest_{tag}@example.com"
    password = TEST_PASSWORD

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
        """PROF-002: Update email successfully, with the right current password (required for an email change since A6e)."""
        print_section("PROF-002: Update email")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            timestamp = int(datetime.now().timestamp() * 1000)
            new_email = f"newemail_{timestamp}@example.com"

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={"email": new_email, "current_password": TEST_PASSWORD},
                    timeout=TIMEOUT,
                )

            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            assert data["user"]["email"] == new_email
            assert data["user"]["username"] == user_data["username"]  # unchanged
            print_success(f"Email updated to {new_email}")

    @pytest.mark.asyncio
    async def test_update_both(self, test_server):
        """PROF-003: Update both username and email, with the right current password (required for an email change since A6e)."""
        print_section("PROF-003: Update username and email")

        async with httpx.AsyncClient() as client:
            user_data, auth_client = await create_and_login_user(client)

            timestamp = int(datetime.now().timestamp() * 1000)
            new_username = f"bothuser_{timestamp}"
            new_email = f"both_{timestamp}@example.com"

            async with auth_client:
                response = await auth_client.put(
                    f"{API_BASE}/auth/profile",
                    json={"username": new_username, "email": new_email, "current_password": TEST_PASSWORD},
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
        """PROF-009: Reject duplicate email.

        With the right current password: since A6e the password is checked first, so only a request that passes it
        reaches the uniqueness check (without it, see PROF-012).
        """
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
                    json={"email": user1_data["email"], "current_password": TEST_PASSWORD},
                    timeout=TIMEOUT,
                )

            # Clean up auth_client1
            await auth_client1.aclose()

            assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
            assert "already registered" in response.json()["detail"].lower()
            print_success("Duplicate email rejected")


# ============================================================================
# THE EMAIL CHANGE ASKS FOR THE PASSWORD — lot A6e (C1, C2, C3)
# ============================================================================
# These helpers serve TestEmailChangeNeedsThePassword only, so they live next to it.


@dataclass
class _Account:
    """An account one test registered with create_and_login_user, and the device it signed in with.

    ``usernames``: every username the test gave the account, the registered one first, so that the teardown signs in
    under whichever one it has by then.
    """

    user_id: int
    username: str
    email: str
    device: httpx.AsyncClient
    usernames: list[str]


async def _delete_account(account: _Account) -> Optional[str]:
    """Sign in afresh as ``account``, under the newest username that works, and DELETE /auth/users/me; the failure, None once deleted."""
    async with httpx.AsyncClient() as client:
        for username in reversed(account.usernames):
            login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": TEST_PASSWORD}, timeout=TIMEOUT)
            if login.status_code == 200:
                deleted = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)
                return None if deleted.status_code == 200 else f"user {account.user_id}: DELETE /auth/users/me {deleted.status_code} {deleted.text}"
    return f"user {account.user_id}: no login under {account.usernames}"


class _Accounts:
    """The accounts and devices of one test: every device closed and every account deleted at teardown, after a red too."""

    def __init__(self) -> None:
        self.registered: list[_Account] = []
        self.devices: list[httpx.AsyncClient] = []

    async def register(self) -> _Account:
        """A new account, signed in on its first device by the file's create_and_login_user."""
        async with httpx.AsyncClient() as client:
            user_data, device = await create_and_login_user(client)
        self.devices.append(device)
        account = _Account(user_id=user_data["id"], username=user_data["username"], email=user_data["email"], device=device, usernames=[user_data["username"]])
        self.registered.append(account)
        return account

    async def new_device(self, account: _Account) -> httpx.AsyncClient:
        """Another session of ``account``, opened now: a login of its own, its cookie in a client of its own."""
        async with httpx.AsyncClient() as client:
            login = await client.post(f"{API_BASE}/auth/login", json={"username": account.username, "password": TEST_PASSWORD}, timeout=TIMEOUT)
        assert login.status_code == 200, f"Setup: a second login as {account.username} failed: {login.status_code} {login.text}"
        device = httpx.AsyncClient(cookies=login.cookies)
        self.devices.append(device)
        return device

    async def close(self) -> list[str]:
        """Close every device, then delete every account; what failed."""
        for device in self.devices:
            await device.aclose()
        errors: list[str] = []
        for account in self.registered:
            error = await _delete_account(account)
            if error:
                errors.append(error)
        return errors


@pytest_asyncio.fixture
async def accounts(test_server) -> AsyncIterator[_Accounts]:
    """The accounts of one test, registered on the lane's server and deleted at teardown, after a red too."""
    registry = _Accounts()
    try:
        yield registry
    finally:
        errors = await registry.close()
        assert not errors, f"Cleanup: {errors}"


def _answer(response: httpx.Response) -> tuple[int, Any]:
    """What a client is told: the status code and the JSON body (the text when it is not JSON)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


def _session_set_cookies(response: httpx.Response) -> list[str]:
    """The value of every Set-Cookie of ``response`` that writes the session cookie, matched by name: [] when there is none."""
    values: list[str] = []
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == SESSION_COOKIE_NAME:
            values.append(value.strip())
    return values


async def _put_profile(device: httpx.AsyncClient, body: dict[str, Any]) -> httpx.Response:
    """PUT /auth/profile from ``device``, with the session cookie it holds; a session Set-Cookie of the answer replaces it, as in a browser."""
    return await device.put(f"{API_BASE}/auth/profile", json=body, timeout=TIMEOUT)


async def _me(device: httpx.AsyncClient) -> tuple[int, Any]:
    """GET /auth/me from ``device``, with the session cookie it holds."""
    return _answer(await device.get(f"{API_BASE}/auth/me", timeout=TIMEOUT))


async def _me_with_cookie(cookie_value: str) -> tuple[int, Any]:
    """GET /auth/me with this session cookie only, sent explicitly from an empty client: no cookie jar decides what is sent."""
    async with httpx.AsyncClient() as client:
        return _answer(await client.get(f"{API_BASE}/auth/me", headers={"Cookie": f"{SESSION_COOKIE_NAME}={cookie_value}"}, timeout=TIMEOUT))


def _profile(answer: tuple[int, Any], account: _Account) -> Optional[tuple[Any, Any]]:
    """(username, email) of a GET /auth/me answer that is a session of ``account`` (200, its id); None for any other answer."""
    status, body = answer
    user = body.get("user") if status == 200 and isinstance(body, dict) else None
    if not isinstance(user, dict) or user.get("id") != account.user_id:
        return None
    return user.get("username"), user.get("email")


def _assert_password_refusal(answer: tuple[int, Any], error_code: str, request: str) -> None:
    """``answer`` is a coded 400 of C2: ``{"detail": {"error_code": error_code, "message": a text}}``."""
    status, body = answer
    detail = body.get("detail") if isinstance(body, dict) else None
    assert status == 400 and isinstance(detail, dict) and detail.get("error_code") == error_code, f"{request} must be refused with 400 and error_code {error_code}: got {status} {body}"
    assert isinstance(detail.get("message"), str) and detail["message"].strip(), f"The refusal must carry a message beside its error_code: {body}"


async def _assert_nothing_written(account: _Account, request: str) -> None:
    """The account's own device is still signed in, with the username and the email the account had: ``request`` wrote nothing."""
    answer = await _me(account.device)
    assert _profile(answer, account) == (account.username, account.email), f"{request} must change nothing: the device must still be signed in as {account.username} <{account.email}>, GET /auth/me {answer}"


def _new_email(prefix: str) -> str:
    """An address nobody has, in lower case: stored as sent, so the server's exact comparison sees the same text."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"


def _new_username(prefix: str) -> str:
    """A username nobody has."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _wrong_password() -> str:
    """A password that is not TEST_PASSWORD."""
    return f"Wrong-{uuid.uuid4().hex[:12]}"


class TestEmailChangeNeedsThePassword:
    """PUT /auth/profile under the contract of lot A6e (module docstring): C1, C2 and C3, on the lane's server.

    «NEW, red today» marks the contract: today the email changes with the session cookie alone, whatever the password
    (the unknown field is ignored), and no session ends. «GUARD» marks what holds today and must keep holding: a change
    that is no email change needs no password and ends no session.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("missing", ["absent", "null"])
    async def test_email_change_without_current_password_is_refused(self, accounts: _Accounts, missing: str):
        """PROF-010 — NEW, red today (200, the email changes): an email change without the current password — the
        field left out, or null — is refused with 400 CURRENT_PASSWORD_REQUIRED, and the email stays."""
        print_section(f"PROF-010: email change without current_password ({missing})")
        account = await accounts.register()
        body: dict[str, Any] = {"email": _new_email("nopass")}
        if missing == "null":
            body["current_password"] = None

        answer = _answer(await _put_profile(account.device, body))

        _assert_password_refusal(answer, "CURRENT_PASSWORD_REQUIRED", f"An email change without current_password ({missing})")
        await _assert_nothing_written(account, "The refused email change")
        print_success(f"✓ {missing}: 400 CURRENT_PASSWORD_REQUIRED, the email unchanged")

    @pytest.mark.asyncio
    async def test_email_change_with_a_wrong_current_password_writes_nothing(self, accounts: _Accounts):
        """PROF-011 — NEW, red today (200, the email changes whatever the password): a wrong current password is
        refused with 400 CURRENT_PASSWORD_INVALID, and nothing is written: the email stays, no session cookie is set,
        and a second session of the account, opened before, is still signed in."""
        print_section("PROF-011: email change with a wrong current_password")
        account = await accounts.register()
        second = await accounts.new_device(account)
        answer = await _me(second)
        assert _profile(answer, account) is not None, f"Precondition: the second session must be signed in as {account.username}: GET /auth/me {answer}"

        response = await _put_profile(account.device, {"email": _new_email("wrongpass"), "current_password": _wrong_password()})

        _assert_password_refusal(_answer(response), "CURRENT_PASSWORD_INVALID", "An email change with a wrong current password")
        assert _session_set_cookies(response) == [], f"A refused change must set no session cookie: Set-Cookie {response.headers.get_list('set-cookie')}"
        await _assert_nothing_written(account, "The refused email change")
        answer = await _me(second)
        assert _profile(answer, account) == (account.username, account.email), f"A refused change must end no session: the second session must still be signed in as {account.username}, GET /auth/me {answer}"
        print_success("✓ 400 CURRENT_PASSWORD_INVALID, nothing written, the second session still signed in")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("password", "error_code"), [("missing", "CURRENT_PASSWORD_REQUIRED"), ("wrong", "CURRENT_PASSWORD_INVALID")])
    async def test_a_taken_email_is_not_revealed_without_the_password(self, accounts: _Accounts, password: str, error_code: str):
        """PROF-012 — NEW, red today (400 «Email already registered»): the password is checked before uniqueness, so an
        address another account already uses, asked for without the right password, gets the password's refusal and
        never the uniqueness message: a session cookie alone cannot probe which addresses are registered."""
        print_section(f"PROF-012: a taken email, password {password}")
        account = await accounts.register()
        holder = await accounts.register()
        body: dict[str, Any] = {"email": holder.email}
        if password == "wrong":
            body["current_password"] = _wrong_password()

        answer = _answer(await _put_profile(account.device, body))

        assert "already registered" not in str(answer[1]).lower(), f"Without the right password the answer must not tell that {holder.email} is registered: {answer}"
        _assert_password_refusal(answer, error_code, f"An email change to a taken address, password {password},")
        await _assert_nothing_written(account, "The refused email change")
        print_success(f"✓ password {password}: 400 {error_code}, the taken address not revealed")

    @pytest.mark.asyncio
    async def test_email_change_with_the_right_password_ends_the_other_sessions(self, accounts: _Accounts):
        """PROF-013 — NEW, red today (200, but no cookie is set and every old session keeps working): with the right
        current password the email changes (200) and the response sets exactly one new session cookie, which keeps this
        device signed in with the new email; a second session opened before is refused (401), and so is the old cookie
        of this device, should anybody hold a copy of it.

        The server keeps no session: two logins in the same second may even get the same token. What ends them is the
        account's session version, which the new cookie carries already raised.
        """
        print_section("PROF-013: email change with the right password ends the other sessions")
        account = await accounts.register()
        second = await accounts.new_device(account)
        old_cookie = account.device.cookies.get(SESSION_COOKIE_NAME)
        assert old_cookie, f"Precondition: the first device must hold a {SESSION_COOKIE_NAME} cookie"
        for label, device in (("the first device", account.device), ("the second session", second)):
            answer = await _me(device)
            assert _profile(answer, account) is not None, f"Precondition: {label} must be signed in as {account.username}: GET /auth/me {answer}"
        new_email = _new_email("changed")

        response = await _put_profile(account.device, {"email": new_email, "current_password": TEST_PASSWORD})

        status, body = _answer(response)
        assert status == 200 and body["user"]["email"] == new_email, f"The email change with the right password must succeed: {status} {body}"
        reissued = _session_set_cookies(response)
        assert len(reissued) == 1 and reissued[0] and reissued[0] != old_cookie, f"The response must set exactly one new {SESSION_COOKIE_NAME} cookie, for the device that changed the email: Set-Cookie {response.headers.get_list('set-cookie')}"
        refused = {"The second session, opened before the change,": await _me(second), "The old cookie of the device that changed the email": await _me_with_cookie(old_cookie)}
        for label, answer in refused.items():
            assert answer[0] == 401, f"{label} must be refused (401) after an email change: GET /auth/me {answer}"
        signed_in = {"The cookie the response set": await _me_with_cookie(reissued[0]), "The device that changed the email, holding that cookie now,": await _me(account.device)}
        for label, answer in signed_in.items():
            assert _profile(answer, account) == (account.username, new_email), f"{label} must keep the account signed in, with the new email: GET /auth/me {answer}"
        print_success("✓ 200, a new cookie for this device, the second session and the old cookie refused")

    @pytest.mark.asyncio
    async def test_username_change_needs_no_password_and_ends_no_session(self, accounts: _Accounts):
        """PROF-014 — GUARD, green today and after: a username-only change needs no password (200) and ends no session:
        the device that made it and a second session opened before both stay signed in, under the new name."""
        print_section("PROF-014: username-only change, no password, no session ended")
        account = await accounts.register()
        second = await accounts.new_device(account)
        answer = await _me(second)
        assert _profile(answer, account) is not None, f"Precondition: the second session must be signed in as {account.username}: GET /auth/me {answer}"
        new_username = _new_username("renamed")
        account.usernames.append(new_username)  # the teardown signs in under the new name once the change is made

        status, body = _answer(await _put_profile(account.device, {"username": new_username}))

        assert status == 200, f"A username-only change needs no password: {status} {body}"
        for label, device in (("The device that made the change", account.device), ("The second session", second)):
            answer = await _me(device)
            assert _profile(answer, account) == (new_username, account.email), f"{label} must stay signed in as {new_username} <{account.email}>: a username-only change ends no session, GET /auth/me {answer}"
        print_success("✓ 200 without a password, both sessions still signed in")

    @pytest.mark.asyncio
    async def test_the_same_email_needs_no_password(self, accounts: _Accounts):
        """PROF-015 — GUARD, green today and after: the account's own email sent again, beside a new username, is no
        email change: no password (200), the username changes, the email stays, and a second session stays signed in."""
        print_section("PROF-015: the same email and a new username, no password")
        account = await accounts.register()
        second = await accounts.new_device(account)
        answer = await _me(second)
        assert _profile(answer, account) is not None, f"Precondition: the second session must be signed in as {account.username}: GET /auth/me {answer}"
        new_username = _new_username("sameemail")
        account.usernames.append(new_username)  # the teardown signs in under the new name once the change is made

        status, body = _answer(await _put_profile(account.device, {"username": new_username, "email": account.email}))

        assert status == 200, f"The account's own email sent again is no email change, so it needs no password: {status} {body}"
        for label, device in (("The device that made the change", account.device), ("The second session", second)):
            answer = await _me(device)
            assert _profile(answer, account) == (new_username, account.email), f"{label} must stay signed in as {new_username} <{account.email}>: no email change, no session ended, GET /auth/me {answer}"
        print_success("✓ 200 without a password, the email kept, both sessions still signed in")

    @pytest.mark.asyncio
    async def test_an_empty_current_password_is_invalid(self, accounts: _Accounts):
        """PROF-016 — NEW, red today (200: the unknown field is ignored and the email changes): current_password has at
        least one character (C1), so an empty one fails validation (422), and the email stays."""
        print_section("PROF-016: empty current_password")
        account = await accounts.register()

        status, body = _answer(await _put_profile(account.device, {"email": _new_email("empty"), "current_password": ""}))

        assert status == 422, f"An empty current_password must fail validation (422): {status} {body}"
        await _assert_nothing_written(account, "The rejected request")
        print_success("✓ 422, the email unchanged")


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


# ============================================================================
# NO ADDRESS IN THE LOGS — lot A7c (PROF-017 to PROF-019), in-process on a private database
# ============================================================================
# These imports and helpers serve TestProfileLogsNoAddress only, so they live next to it. The lane's server writes its
# logs in a process of its own, which no test can capture: so these cases run in-process, on a private instance — the
# real auth router, mounted as api/v1/router.py mounts it, in an app of this test whose get_session_generator opens
# sessions on a private SQLite file under tmp_path, seeded as a new install (the global settings, no account), as in
# test_admin_setup_api.py and test_users_admin_api.py. Nothing reaches the lane. bcrypt runs at its lowest cost in this
# process (auth_service.BCRYPT_ROUNDS = 4); the lane's server keeps its own. Each address has a local part of its own
# that no username shares: a log may carry the username, never the address, and the check looks for the local part
# alone too.

import logging
from collections.abc import Iterable
from pathlib import Path

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings

#: The loggers of PUT /auth/profile, both structlog.get_logger(__name__): the route's and update_profile's.
PROFILE_LOGGERS = (auth_api.__name__, user_service.__name__)
#: The event the route logs once the profile is updated, and the one update_profile logs, word for word.
PROFILE_UPDATED = "Profile updated"
USER_PROFILE_UPDATED = "User profile updated"
#: The SQL loggers. Below WARNING they print every statement with its parameters and every row read, so the addresses an
#: UPDATE writes and a SELECT reads too. configure_logging (backend/app/logging_config.py) sets them to WARNING: a running
#: server never writes those records, caplog sees them only because it lowers the root's level. UADM-030
#: (test_users_admin_api.py) pins that premise, read from configure_logging's source.
SQL_LOGGERS = ("aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool")


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the auth router, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _private_app(engine: AsyncEngine) -> FastAPI:
    """The real auth router, mounted under the API prefix as ``api/v1/router.py`` mounts it; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    app.include_router(auth_api.router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with, no account; bcrypt at cost 4. Disposed at teardown."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'profile-logs.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_private_app(engine))
    finally:
        await engine.dispose()


async def _in_process(private: _Private, method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request to the private instance, from a client of its own: no cookie jar, the session (if any) sent explicitly."""
    headers = {"Cookie": f"{SESSION_COOKIE_NAME}={cookie}"} if cookie else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=private.app), base_url="http://test", timeout=TIMEOUT) as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", json=json, headers=headers)


@dataclass(frozen=True)
class _PrivateAccount:
    """An account of the private instance, signed in with the session ``cookie``; its username and its address carry tags of their own."""

    user_id: int
    username: str
    email: str
    cookie: str


async def _signed_in_account(private: _Private) -> _PrivateAccount:
    """An account written as a row with a real bcrypt hash of TEST_PASSWORD (cost 4), then signed in through POST /auth/login: all before any capture."""
    username, email = _new_username("logs"), _new_email("inbox")
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(TEST_PASSWORD))
        session.add(user)
        await session.commit()
    login = await _in_process(private, "POST", "/auth/login", json={"username": username, "password": TEST_PASSWORD})
    cookies = _session_set_cookies(login)
    assert login.status_code == 200 and len(cookies) == 1 and cookies[0], f"Setup: {username} could not sign in to the private instance: {login.status_code} {login.text}"
    return _PrivateAccount(user_id=user.id, username=username, email=email, cookie=cookies[0])


def _canary(logger_name: str) -> str:
    """The canary logged through ``logger_name``, to both captures."""
    return f"canary: the capture sees the events of {logger_name}"


async def _logged_put_profile(private: _Private, cookie: str, body: dict[str, Any], caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> tuple[httpx.Response, list[dict[str, Any]], list[logging.LogRecord]]:
    """PUT /auth/profile on the private instance with the session ``cookie``, and everything that request logged, from the
    canaries to the answer: the structlog events (capture_logs) and the stdlib records (caplog at DEBUG, on the root and
    on the loggers of PROFILE_LOGGERS, enabled even if a configuration disabled them).

    Barriers first: a canary through each logger name of PROFILE_LOGGERS must reach both captures, or a capture that sees
    nothing would pass for a request that logs nothing.
    """
    for name in PROFILE_LOGGERS:
        monkeypatch.setattr(logging.getLogger(name), "disabled", False)
    caplog.set_level(logging.DEBUG)
    for name in PROFILE_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=name)
    caplog.clear()
    with capture_logs() as events:
        for name in PROFILE_LOGGERS:
            structlog.get_logger(name).debug(_canary(name))
            logging.getLogger(name).debug(_canary(name))
        response = await _in_process(private, "PUT", "/auth/profile", cookie=cookie, json=body)
    records = list(caplog.records)
    seen_events = {event.get("event") for event in events}
    seen_records = {(record.name, record.getMessage()) for record in records}
    for name in PROFILE_LOGGERS:
        assert _canary(name) in seen_events, f"barrier: structlog events of {name} do not reach capture_logs"
        assert (name, _canary(name)) in seen_records, f"barrier: stdlib records of {name} do not reach caplog at DEBUG"
    return response, events, records


def _shows_an_address(text: str, addresses: Iterable[str]) -> bool:
    """Whether ``text`` shows one of ``addresses``, whole or by its local part alone, compared in lower case."""
    lowered = text.lower()
    return any(address.lower() in lowered or address.lower().partition("@")[0] in lowered for address in addresses)


def _record_text(record: logging.LogRecord) -> str:
    """All a stdlib record shows: its message and every attribute."""
    return record.getMessage() + repr(vars(record))


def _written_by_a_server(record: logging.LogRecord) -> bool:
    """Whether a running server writes ``record``: every record but those below WARNING of the SQL loggers and their children."""
    of_sql = any(record.name == name or record.name.startswith(f"{name}.") for name in SQL_LOGGERS)
    return record.levelno >= logging.WARNING or not of_sql


def _assert_no_address(events: list[dict[str, Any]], records: list[logging.LogRecord], addresses: Iterable[str], call: str) -> None:
    """No structlog event, and no stdlib record a server would write, shows one of ``addresses``: in any key, value or
    message, whole or by its local part, in any case."""
    needles = sorted(set(addresses))
    leaked_events = [event for event in events if _shows_an_address(repr(event), needles)]
    leaked_records = [f"{record.name}: {record.getMessage()}" for record in records if _written_by_a_server(record) and _shows_an_address(_record_text(record), needles)]
    assert leaked_events == [], f"{call}: structlog events showing {needles}, whole or by the local part: {leaked_events}"
    assert leaked_records == [], f"{call}: stdlib records showing {needles}, whole or by the local part: {leaked_records}"


def _the_event(events: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """The event ``name`` of the capture, asserted to be there once."""
    matching = [event for event in events if event.get("event") == name]
    assert len(matching) == 1, f"The request must log «{name}» once: {matching}"
    return matching[0]


class TestProfileLogsNoAddress:
    """Lot A7c (release 1.3, workstream A): PUT /auth/profile writes no email address in any log — the rule of
    workstream E, which matters most on the hosted cloud. The route's «Profile updated» and update_profile's «User
    profile updated» keep ``user_id`` and ``username``, and ``email`` gives way to ``email_changed``: True when the
    address changed, False otherwise. The service's line alone is pinned in test_services/test_user_profile.py
    (UPROF-001, UPROF-002); here, the whole request and the route's line.

    What is checked is everything the request logged, captured at DEBUG by ``_logged_put_profile``: no structlog event
    and no stdlib record shows the old address or the new one, whole or by its local part, in any case — the SQL
    loggers' records below WARNING aside, which no server writes (``SQL_LOGGERS``).

    Today both lines log ``email=``: PROF-017 and PROF-018 are red on those two keywords alone (the request itself
    succeeds); the refusal of PROF-019 logs no address and is a guard.
    """

    @pytest.mark.asyncio
    async def test_an_email_change_logs_email_changed_never_an_address(self, private: _Private, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """PROF-017 — NEW, red today only because of the two ``email=`` keywords: update_profile's «User profile updated»
        and the route's «Profile updated» both carry the new address. A signed-in user changes the email with the right
        current password: 200, no event and no record of that request shows the old address or the new one, and
        «Profile updated» is there once, without ``email``, with ``email_changed`` exactly True and the account's
        ``user_id`` and ``username``."""
        print_section("PROF-017: an email change logs email_changed, no address")
        account = await _signed_in_account(private)
        new_email = _new_email("moved")

        response, events, records = await _logged_put_profile(private, account.cookie, {"email": new_email, "current_password": TEST_PASSWORD}, caplog, monkeypatch)

        status, body = _answer(response)
        assert status == 200 and body["user"]["email"] == new_email, f"barrier: the email change with the right password must succeed: {status} {body}"
        _assert_no_address(events, records, [account.email, new_email], "PUT /auth/profile changing the email")
        event = _the_event(events, PROFILE_UPDATED)
        assert "email" not in event, f"«{PROFILE_UPDATED}» must carry no 'email' key: {event}"
        assert event.get("email_changed") is True, f"«{PROFILE_UPDATED}» must carry email_changed=True, exactly, after an email change: {event}"
        assert (event.get("user_id"), event.get("username")) == (account.user_id, account.username), f"«{PROFILE_UPDATED}» keeps user_id and username: {event}"
        print_success(f"✓ 200; {len(events)} events and {len(records)} records without an address; email_changed True")

    @pytest.mark.asyncio
    async def test_a_username_change_logs_email_changed_false_never_the_address(self, private: _Private, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """PROF-018 — NEW, red today only because of the two ``email=`` keywords: both lines carry the address, unchanged.
        A username-only change: 200, no event and no record of that request shows the address, and «Profile updated» is
        there once, without ``email``, with ``email_changed`` exactly False, the account's ``user_id`` and the new
        ``username``."""
        print_section("PROF-018: a username-only change logs email_changed False, no address")
        account = await _signed_in_account(private)
        new_username = _new_username("renamed")

        response, events, records = await _logged_put_profile(private, account.cookie, {"username": new_username}, caplog, monkeypatch)

        status, body = _answer(response)
        assert status == 200 and (body["user"]["username"], body["user"]["email"]) == (new_username, account.email), f"barrier: the username-only change must succeed: {status} {body}"
        _assert_no_address(events, records, [account.email], "PUT /auth/profile changing the username only")
        event = _the_event(events, PROFILE_UPDATED)
        assert "email" not in event, f"«{PROFILE_UPDATED}» must carry no 'email' key: {event}"
        assert event.get("email_changed") is False, f"«{PROFILE_UPDATED}» must carry email_changed=False, exactly, after a username-only change: {event}"
        assert (event.get("user_id"), event.get("username")) == (account.user_id, new_username), f"«{PROFILE_UPDATED}» keeps user_id and the new username: {event}"
        print_success(f"✓ 200; {len(events)} events and {len(records)} records without the address; email_changed False")

    @pytest.mark.asyncio
    async def test_a_refused_email_change_logs_no_address(self, private: _Private, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch):
        """PROF-019 — GUARD, green today and after: an email change with a wrong current password is refused, 400
        CURRENT_PASSWORD_INVALID, and no event and no record of that request shows the old address or the one asked for;
        nothing is updated, so neither «Profile updated» nor «User profile updated» is logged."""
        print_section("PROF-019: a refused email change logs no address")
        account = await _signed_in_account(private)
        asked_for = _new_email("refused")

        response, events, records = await _logged_put_profile(private, account.cookie, {"email": asked_for, "current_password": _wrong_password()}, caplog, monkeypatch)

        _assert_password_refusal(_answer(response), "CURRENT_PASSWORD_INVALID", "An email change with a wrong current password")
        _assert_no_address(events, records, [account.email, asked_for], "The refused PUT /auth/profile")
        updates = [event for event in events if event.get("event") in (PROFILE_UPDATED, USER_PROFILE_UPDATED)]
        assert updates == [], f"A refused change updates nothing, so it logs neither «{PROFILE_UPDATED}» nor «{USER_PROFILE_UPDATED}»: {updates}"
        print_success(f"✓ 400 CURRENT_PASSWORD_INVALID; {len(events)} events and {len(records)} records without an address")


# ============================================================================
# THE SAME ADDRESS WHATEVER ITS A–Z CASE — P18 (PROF-020 to PROF-022), on the lane's server
# ============================================================================
# Developer decision P18 (release 1.3, workstream A; contract approved by the coordinator): two addresses are the same
# when they match once A–Z are folded to a–z, as SQLite's lower() folds them; letters outside ASCII compare as written, a
# documented limit not tested here. Its C5: changing one's own address in its A–Z case alone keeps the same address — no
# password, no session ended, the new form stored —, while another account's address, in any A–Z case, is taken. Until
# P18 addresses are compared exactly, as A6e's C2 in the module docstring still says. EmailStr lowercases the domain and
# never the local part, so the cases vary the case of the local part. The accounts are those of
# TestEmailChangeNeedsThePassword: registered on the lane's server by create_and_login_user, with a lower-case address,
# every device closed and every account deleted at teardown, after a red too. EMAIL_TAKEN and _local_part_in_capitals
# serve TestTheSameAddressWhateverItsCase only, so they live next to it.

#: The plain ``detail`` of PUT /auth/profile for an address another account has, as PROF-009 reads it: an API string.
EMAIL_TAKEN = "Email already registered"


def _local_part_in_capitals(address: str, suffix: str = "") -> str:
    """``address`` with its local part, ``suffix`` appended, in capitals and its domain as it is: the same address up to
    the A–Z case when ``suffix`` is empty, another address otherwise. The server keeps a local part as it is sent."""
    local, _, domain = address.rpartition("@")
    return f"{(local + suffix).upper()}@{domain}"


class TestTheSameAddressWhateverItsCase:
    """PUT /auth/profile under P18, on the lane's server: the own address in another A–Z case is the same address (C5),
    another account's address in another A–Z case is taken, and any other address is still an email change, which needs
    the password (A6e).

    «NEW, red until P18» marks the contract: today addresses are compared exactly, so the own address in capitals is an
    email change, which asks for the password, and another account's address in capitals is free, so it is taken, every
    other session ending. «GUARD» marks what holds today and must keep holding.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("password", ["absent", "wrong"])
    async def test_the_own_address_in_another_case_is_the_same_address(self, accounts: _Accounts, password: str):
        """PROF-020 — NEW, red until P18 (today 400 CURRENT_PASSWORD_REQUIRED, or CURRENT_PASSWORD_INVALID with the
        wrong one: compared exactly, it is an email change): the own address with its local part in capitals is the same
        address (P18, C5). Without current_password, or with a wrong one beside it — not checked, as for a username-only
        change —: 200, and the answer's user has the new form; the answer sets no session cookie; GET /auth/me returns
        the new form on this device and on a second one, signed in before: no session ended."""
        print_section(f"PROF-020: the own address in capitals, password {password}")
        account = await accounts.register()
        second = await accounts.new_device(account)
        answer = await _me(second)
        assert _profile(answer, account) is not None, f"Precondition: the second session must be signed in as {account.username}: GET /auth/me {answer}"
        new_form = _local_part_in_capitals(account.email)
        assert new_form != account.email and new_form.lower() == account.email, f"setup: {new_form} must be {account.email} in another A–Z case"
        sent: dict[str, Any] = {"email": new_form}
        if password == "wrong":
            sent["current_password"] = _wrong_password()

        response = await _put_profile(account.device, sent)

        status, body = _answer(response)
        assert status == 200 and (body["user"]["id"], body["user"]["email"]) == (account.user_id, new_form), f"The own address in another A–Z case needs no password, and the answer carries its new form {new_form}: {status} {body}"
        assert _session_set_cookies(response) == [], f"The same address is no email change: no session cookie may be set, Set-Cookie {response.headers.get_list('set-cookie')}"
        for label, device in (("This device", account.device), ("The second session, opened before,", second)):
            answer = await _me(device)
            assert _profile(answer, account) == (account.username, new_form), f"{label} must stay signed in, with the new form {new_form}: the same address ends no session, GET /auth/me {answer}"
        print_success(f"✓ password {password}: 200, the new form stored, no cookie set, both sessions signed in")

    @pytest.mark.asyncio
    async def test_another_accounts_address_in_another_case_is_taken(self, accounts: _Accounts):
        """PROF-021 — NEW, red until P18 (today 200: compared exactly, another account's address in capitals is free, so
        the email changes and the other sessions end): with the right current password, another account's address in
        another A–Z case — its local part and its domain in capitals — is refused as that address is: 400, ``detail`` the
        plain string «Email already registered»; nothing changes: no session cookie is set, and GET /auth/me still shows
        the old address."""
        print_section("PROF-021: another account's address in capitals")
        account = await accounts.register()
        holder = await accounts.register()
        taken = holder.email.upper()
        assert taken != holder.email and taken.lower() == holder.email, f"setup: {taken} must be {holder.email} in another A–Z case"

        response = await _put_profile(account.device, {"email": taken, "current_password": TEST_PASSWORD})

        status, body = _answer(response)
        detail = body.get("detail") if isinstance(body, dict) else body
        assert (status, detail) == (400, EMAIL_TAKEN), f"{taken} is the address of {holder.username} in another A–Z case: expected 400 {EMAIL_TAKEN!r}, as for that address itself, got {status} {body}"
        assert _session_set_cookies(response) == [], f"A refused change must set no session cookie: Set-Cookie {response.headers.get_list('set-cookie')}"
        await _assert_nothing_written(account, "The refused email change")
        print_success(f"✓ 400 «{EMAIL_TAKEN}», the address unchanged")

    @pytest.mark.asyncio
    async def test_another_address_still_needs_the_password(self, accounts: _Accounts):
        """PROF-022 — GUARD, green today and after (A6e, as PROF-010): the own address in capitals with one more letter
        is another address, not the same one in another case: without current_password it is refused with 400
        CURRENT_PASSWORD_REQUIRED, and nothing is written."""
        print_section("PROF-022: another address, without current_password")
        account = await accounts.register()
        other = _local_part_in_capitals(account.email, suffix="x")
        assert other.lower() != account.email, f"setup: {other} must be another address than {account.email}, whatever the case"

        answer = _answer(await _put_profile(account.device, {"email": other}))

        _assert_password_refusal(answer, "CURRENT_PASSWORD_REQUIRED", "An email change to another address without current_password")
        await _assert_nothing_written(account, "The refused email change")
        print_success("✓ 400 CURRENT_PASSWORD_REQUIRED, the email unchanged")
