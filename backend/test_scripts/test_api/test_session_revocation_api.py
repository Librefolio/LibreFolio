"""
Session Revocation API Tests — release 1.3, workstream A, lot A4b (plan phase01Accounts §4.5, decision D-A17).

A session is the JWT in the ``session`` cookie: signed, stateless, good until its ``exp``. Until 1.3 a password change
ended nothing: a cookie stolen before it kept working after it, on every device. Each account now has a session version
(``users.session_version``) and each cookie carries the version it was issued at (the ``sv`` claim): raising the
account's version ends every session issued before, everywhere at once.

The contract, over HTTP on the lane's server:

- a successful ``POST /auth/change-password`` raises the account's version by exactly one, committed, and the same
  response sets a new ``session`` cookie at the new version, with the login cookie's attributes — the same name, path and
  domain are what make a browser replace the old cookie instead of keeping both —: the device that changed the password
  stays signed in;
- every other session of the account is refused, 401 «Session expired or invalid»: another device, and the very cookie
  the change was sent with, should anybody hold a copy. Other accounts' sessions are untouched;
- the next login is issued at the current version: the new password signs in and its session works; the old one does not;
- a refused change (wrong current password, the same password) raises nothing and sets no cookie: every device stays
  signed in, and the password is the one it was.

Only real logins here: the lane's server signs with a JWT secret ``dev.py`` generates when it starts it, so this process
cannot forge a cookie that server accepts. Cookies issued before 1.3 (no ``sv``) and version mismatches are tested
in-process, in ``test_services/test_session_version.py``.

A device is a session cookie of its own, from a login made by a client of its own; every request then sends one cookie
explicitly, from an empty client, so no cookie jar decides what is sent. The version is read from the database the server
serves, for this test's two accounts only.

Write-scoped: each test registers its own two regular users (unique names), reads only their rows, and deletes both at
teardown through ``user_service.delete_user`` — after a red too, whatever password and cookies they ended with. Changing
a password ends that account's sessions, so no shared E2E user is ever touched.
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Optional

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.api.v1 import auth as auth_api
from backend.app.config import get_settings
from backend.app.db.models import User
from backend.app.db.session import get_async_engine
from backend.app.services.accounts import user_service
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME
#: GET /auth/me's answer to a session that is no longer valid: the detail of an invalid token, nothing tells the holder why.
SESSION_EXPIRED = (401, {"detail": "Session expired or invalid"})


@pytest.fixture(scope="module")
def test_server():
    """Start test server for all tests in this module (attaches to the lane's shared backend under the runner)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# ACCOUNTS, DEVICES AND COOKIES
# ============================================================================


@dataclass(frozen=True)
class _Account:
    """A regular user one test registered."""

    user_id: int
    username: str
    password: str


@dataclass(frozen=True)
class _Accounts:
    """The account whose password changes, and another account, whose session must not notice."""

    owner: _Account
    bystander: _Account


@dataclass(frozen=True)
class _Cookie:
    """A ``session`` Set-Cookie: its value, and its attributes by lower-cased name ("" for a flag)."""

    value: str
    attributes: dict[str, str]


def _lane_engine() -> AsyncEngine:
    """The lane's test database, the one its server serves: this test's user rows are read and deleted there, nowhere else."""
    is_test_db, database_url = verify_test_database()
    assert is_test_db, f"Refusing to read or delete users outside the lane's test database: {database_url}"
    return get_async_engine()


async def _register(prefix: str, registered: list[int]) -> _Account:
    """Register a regular user with a unique name; its id goes into ``registered`` the moment it exists, for the teardown."""
    username = f"{prefix}_{uuid.uuid4().hex[:12]}"
    password = f"Initial-{uuid.uuid4().hex[:12]}1"
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": password}, timeout=TIMEOUT)
    assert response.status_code == 201, f"Setup: registering {username} failed: {response.status_code} {response.text}"
    user = response.json()["user"]
    registered.append(user["id"])
    assert user["is_superuser"] is False, f"Precondition: {username} must be a regular user; it registered as the instance's first user, hence its administrator: the api setup (db populate, e2e_test_admin) did not run on this lane"
    return _Account(user_id=user["id"], username=username, password=password)


async def _delete_users(user_ids: list[int]) -> list[str]:
    """Delete these users through user_service.delete_user, the service DELETE /auth/users/me calls, each in a session of its own; what failed."""
    errors: list[str] = []
    for user_id in user_ids:
        async with AsyncSession(_lane_engine()) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:  # every account gets its attempt; the failures are reported together
                errors.append(f"user {user_id}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def accounts(test_server) -> AsyncIterator[_Accounts]:
    """Two regular users of this test only, registered over HTTP, deleted at teardown — after a red too."""
    registered: list[int] = []
    try:
        owner = await _register("revoke_owner", registered)
        bystander = await _register("revoke_other", registered)
        yield _Accounts(owner=owner, bystander=bystander)
    finally:
        errors = await _delete_users(registered)
        assert not errors, f"Cleanup: {errors}"


def _session_cookies(response: httpx.Response) -> list[_Cookie]:
    """Every Set-Cookie of ``response`` that writes the session cookie, parsed by name, never by position: [] when there is none."""
    cookies: list[_Cookie] = []
    for header in response.headers.get_list("set-cookie"):
        pair, *attributes = (part.strip() for part in header.split(";"))
        name, _, value = pair.partition("=")
        if name.strip() == COOKIE:
            cookies.append(_Cookie(value=value, attributes={key.strip().lower(): attribute.strip() for key, _, attribute in (item.partition("=") for item in attributes if item)}))
    return cookies


def _without_lifetime(attributes: dict[str, str]) -> dict[str, str]:
    """A cookie's attributes without its lifetime (Max-Age, Expires): the TTL is a global setting another unit of the lane may change between two requests."""
    return {name: value for name, value in attributes.items() if name not in ("max-age", "expires")}


def _lasts_whole_hours(attributes: dict[str, str]) -> bool:
    """Whether the cookie's Max-Age follows the login's rule, session_ttl_hours × 3600: a positive number of whole hours."""
    max_age = attributes.get("max-age", "")
    return max_age.isdigit() and int(max_age) > 0 and int(max_age) % 3600 == 0


def _answer(response: httpx.Response) -> tuple[int, Any]:
    """What a client is told: the status code and the JSON body (the text when it is not JSON)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


async def _login(username: str, password: str) -> httpx.Response:
    """POST /auth/login from a client of its own, with an empty cookie jar: a new device."""
    async with httpx.AsyncClient() as client:
        return await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": password}, timeout=TIMEOUT)


async def _sign_in(account: _Account, password: Optional[str] = None) -> _Cookie:
    """A new device of ``account``: a login, and the one session cookie it sets."""
    response = await _login(account.username, password or account.password)
    assert response.status_code == 200, f"Login as {account.username} failed: {response.status_code} {response.text}"
    cookies = _session_cookies(response)
    assert len(cookies) == 1 and cookies[0].value, f"A login must set exactly one {COOKIE} cookie: {response.headers.get_list('set-cookie')}"
    return cookies[0]


async def _me(cookie_value: str) -> httpx.Response:
    """GET /auth/me with this session cookie only, sent explicitly from an empty client."""
    async with httpx.AsyncClient() as client:
        return await client.get(f"{API_BASE}/auth/me", headers={"Cookie": f"{COOKIE}={cookie_value}"}, timeout=TIMEOUT)


async def _signed_in_as(cookie_value: str, account: _Account) -> tuple[bool, tuple[int, Any]]:
    """Whether this cookie is a session of ``account`` — GET /auth/me 200 with its id — and what /auth/me answered."""
    answer = _answer(await _me(cookie_value))
    status, body = answer
    return status == 200 and isinstance(body, dict) and body.get("user", {}).get("id") == account.user_id, answer


async def _change_password(cookie_value: str, current_password: str, new_password: str) -> httpx.Response:
    """POST /auth/change-password from the device holding ``cookie_value``."""
    async with httpx.AsyncClient() as client:
        return await client.post(f"{API_BASE}/auth/change-password", json={"current_password": current_password, "new_password": new_password}, headers={"Cookie": f"{COOKIE}={cookie_value}"}, timeout=TIMEOUT)


async def _session_versions(accounts: _Accounts) -> dict[str, int]:
    """{username: session_version} of this test's two accounts, read in a fresh session from the database the server serves."""
    usernames = [accounts.owner.username, accounts.bystander.username]
    async with AsyncSession(_lane_engine()) as session:
        rows = await session.execute(select(User.username, User.session_version).where(User.username.in_(usernames)))
        return dict(rows.tuples().all())


def _expect(violations: list[str], ok: bool, message: str) -> None:
    """Record a broken expectation instead of stopping at the first one: the red lists them all."""
    if not ok:
        violations.append(message)


def _verdict(violations: list[str]) -> str:
    return "\n- " + "\n- ".join(violations)


# ============================================================================
# WHAT MUST HOLD AFTER A SUCCESSFUL CHANGE
# ============================================================================


async def _check_the_reissued_cookie(violations: list[str], response: httpx.Response, device_a: _Cookie, owner: _Account) -> None:
    """The change's response sets one new session cookie, with the login cookie's attributes and lifetime rule, and it is the owner's session."""
    reissued = _session_cookies(response)
    _expect(violations, len(reissued) == 1, f"[new] the response must set exactly one new {COOKIE} cookie, for the device that changed the password: Set-Cookie {response.headers.get_list('set-cookie')}")
    if len(reissued) != 1:
        return
    new = reissued[0]
    _expect(violations, bool(new.value) and new.value != device_a.value, f"[new] the re-issued cookie must be a new session, not the old one again: {new.value!r}")
    _expect(violations, _without_lifetime(new.attributes) == _without_lifetime(device_a.attributes), f"[new] the re-issued cookie must carry the login cookie's attributes, or a browser keeps both: re-issued {new.attributes}, login {device_a.attributes}")
    _expect(violations, _lasts_whole_hours(new.attributes), f"[new] the re-issued cookie must last as the login's does, Max-Age = session_ttl_hours × 3600: {new.attributes}")
    signed_in, answer = await _signed_in_as(new.value, owner)
    _expect(violations, signed_in, f"[new] the re-issued cookie must keep the device that changed the password signed in as {owner.username}: GET /auth/me {answer}")


async def _check_the_old_sessions(violations: list[str], device_a: _Cookie, device_b: _Cookie, other: _Cookie, bystander: _Account) -> None:
    """Every cookie the owner held before the change is refused; another account's session is not."""
    for label, cookie in (("device A's old cookie, the one the change was sent with,", device_a), ("device B, another device of the account,", device_b)):
        answer = _answer(await _me(cookie.value))
        _expect(violations, answer == SESSION_EXPIRED, f"[new] {label} must be refused with {SESSION_EXPIRED}: GET /auth/me {answer}")
    signed_in, answer = await _signed_in_as(other.value, bystander)
    _expect(violations, signed_in, f"[guard] another account's session must not notice: GET /auth/me {answer}")


async def _check_the_passwords(violations: list[str], owner: _Account, new_password: str) -> None:
    """The new password signs in, at the current version (its session works); the old one no longer does."""
    response = await _login(owner.username, new_password)
    cookies = _session_cookies(response)
    _expect(violations, response.status_code == 200 and len(cookies) == 1, f"[guard] the new password must log in, with one session cookie: {response.status_code} {response.text}")
    if response.status_code == 200 and len(cookies) == 1:
        signed_in, answer = await _signed_in_as(cookies[0].value, owner)
        _expect(violations, signed_in, f"[guard] the next login must be issued at the account's current version: its session must work, GET /auth/me {answer}")
    response = await _login(owner.username, owner.password)
    _expect(violations, response.status_code == 401, f"[guard] the old password must no longer log in: {response.status_code} {response.text}")


# ============================================================================
# TESTS
# ============================================================================


class TestPasswordChangeEndsTheOtherSessions:
    """POST /auth/change-password on the lane's server, the owner signed in on two devices and another account on a third.

    Expectations are collected, not stopped at the first, so that a red lists everything that differs: «[new]» marks the
    contract of A4b, «[guard]» what holds today and must keep holding.
    """

    @pytest.mark.asyncio
    async def test_a_password_change_ends_every_other_session_and_keeps_the_device_signed_in(self, accounts: _Accounts):
        """REVOKE-001 — NEW, red today: device A changes the password; it receives a new cookie in the same response and stays signed in; its old cookie and device B are refused; the other account is untouched; the version rose by one.

        Today the change sets no cookie and raises no version, and every old cookie keeps working: the red lists the
        missing cookie, the two old sessions still signed in and the version that did not move.
        """
        print_section("REVOKE-001: a password change ends every other session of the account")
        owner, bystander = accounts.owner, accounts.bystander
        # The server keeps no session: two logins in the same second may even get the same token. What ends them is the
        # account's version, not the token.
        device_a, device_b, other = await _sign_in(owner), await _sign_in(owner), await _sign_in(bystander)
        for label, cookie, account in (("device A", device_a, owner), ("device B", device_b, owner), ("the other account's device", other, bystander)):
            signed_in, answer = await _signed_in_as(cookie.value, account)
            assert signed_in, f"Precondition: {label} must be signed in as {account.username}: GET /auth/me {answer}"
        before = await _session_versions(accounts)
        new_password = f"Changed-{uuid.uuid4().hex[:12]}1"

        response = await _change_password(device_a.value, owner.password, new_password)

        assert response.status_code == 200, f"The password change itself must succeed: {response.status_code} {response.text}"
        violations: list[str] = []
        await _check_the_reissued_cookie(violations, response, device_a, owner)
        await _check_the_old_sessions(violations, device_a, device_b, other, bystander)
        after = await _session_versions(accounts)
        _expect(violations, after == {owner.username: before[owner.username] + 1, bystander.username: before[bystander.username]}, f"[new] the change must raise {owner.username}'s session version by exactly one, committed, and nobody else's: {before} → {after}")
        await _check_the_passwords(violations, owner, new_password)
        assert not violations, f"A successful password change must end every other session of the account, and only those:{_verdict(violations)}"
        print_success("✓ device A re-issued its cookie and stays signed in, its old cookie and device B refused, the other account untouched, version +1")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("refusal", ["wrong-current-password", "same-password"])
    async def test_a_refused_password_change_ends_no_session(self, accounts: _Accounts, refusal: str):
        """REVOKE-002 — GUARD, green today and after: a refused change (400) raises no version and sets no cookie; both devices stay signed in and the password is the one it was."""
        print_section(f"REVOKE-002: a refused password change ({refusal}) ends no session")
        owner = accounts.owner
        device_a, device_b = await _sign_in(owner), await _sign_in(owner)
        for label, cookie in (("device A", device_a), ("device B", device_b)):
            signed_in, answer = await _signed_in_as(cookie.value, owner)
            assert signed_in, f"Precondition: {label} must be signed in as {owner.username}: GET /auth/me {answer}"
        before = await _session_versions(accounts)
        if refusal == "wrong-current-password":
            current_password, new_password, reason = f"Wrong-{uuid.uuid4().hex[:12]}", f"Changed-{uuid.uuid4().hex[:12]}1", "incorrect"
        else:
            current_password, new_password, reason = owner.password, owner.password, "different"

        response = await _change_password(device_a.value, current_password, new_password)

        status, body = _answer(response)
        assert status == 400 and reason in str(body).lower(), f"The change must be refused with 400 ({reason}): {status} {body}"
        violations: list[str] = []
        _expect(violations, _session_cookies(response) == [], f"[guard] a refused change must set no session cookie: {response.headers.get_list('set-cookie')}")
        for label, cookie in (("device A", device_a), ("device B", device_b)):
            signed_in, answer = await _signed_in_as(cookie.value, owner)
            _expect(violations, signed_in, f"[guard] {label} must stay signed in: GET /auth/me {answer}")
        after = await _session_versions(accounts)
        _expect(violations, after == before, f"[guard] a refused change must raise no version: {before} → {after}")
        login = await _login(owner.username, owner.password)
        _expect(violations, login.status_code == 200, f"[guard] the password must still be the one it was: {login.status_code} {login.text}")
        if new_password != owner.password:
            login = await _login(owner.username, new_password)
            _expect(violations, login.status_code == 401, f"[guard] the refused new password must not log in: {login.status_code} {login.text}")
        assert not violations, f"A refused password change must end no session:{_verdict(violations)}"
        print_success(f"✓ {refusal}: 400, no cookie, no version raised, both devices still signed in")
