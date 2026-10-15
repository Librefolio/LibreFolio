"""
Users Admin API — release 1.3, workstream A, lot A5a (plan phase01Accounts, A5.1, contract point 5, the administrator's part).

An administrator manages the accounts from the API. Every route below sits behind ``require_admin`` in
``api/v1/users.py``, its static routes declared before ``{user_id}``:

1. ``GET /users/invites`` → ``{items: [{id, grants_admin, email, created_at, expires_at, created_by_user_id}], usage:
   {used, max_users, billing_url}}``: the live invitations only (neither consumed, nor revoked, nor expired), whoever
   issued them. ``used`` counts the active accounts plus the live invitations; ``max_users`` is ``LIBREFOLIO_MAX_USERS``
   (null without a limit, 0 when the variable is not valid: a bad limit closes); ``billing_url`` is
   ``LIBREFOLIO_BILLING_URL``, null when unset.
2. ``POST /users/invites`` ``{grants_admin=false, email?}`` → 201 ``{invite, token, path, url}``: ``invite`` as listed,
   ``token`` the plaintext shown once, ``path`` its page with the token in the URL fragment (``/invite#token=…``: a
   browser never sends a fragment, so the token stays out of the access log and of proxy logs), ``url`` the public URL
   plus the path, null
   without ``LIBREFOLIO_PUBLIC_URL``. An invitation lives 7 days and only its hash is stored. 409 ``USER_LIMIT_REACHED``
   with ``limit``, ``used`` and ``billing_url`` when ``used >= max_users`` (the caller is an administrator: the counts and
   the subscription link are for them); 409 ``REGISTRATION_DISABLED`` while registration is ``disabled``, by the row or
   by ``LIBREFOLIO_REGISTRATION``. A refusal issues nothing.
3. ``DELETE /users/invites/{invite_id}`` → 204, and the invitation opens nothing any more; 404 when the id is not a live
   invitation: revoked, consumed, expired, never issued, or a token of another purpose (which stays as it was).
4. ``GET /users`` → ``{items: [{id, username, email, is_active, is_superuser, created_at}], usage}``: every account,
   active or not; no hash, no secret.
5. ``PATCH /users/{user_id}`` ``{is_active?, is_superuser?}`` → 200 with the account as ``GET /users`` lists it; 404; 409
   ``LAST_ADMIN`` to deactivate or demote the last active administrator; 409 ``USER_LIMIT_REACHED`` (with the counts) to
   reactivate an account over the limit, which blocks nothing else. Deactivation and demotion end the account's sessions
   (A4b); activation and promotion end none, and a reactivation does not bring the old sessions back.
6. ``POST /users/{user_id}/password-reset-link`` → 201 ``{token, path, url, expires_at}``, ``path`` being
   ``/reset-password#token=…``, 30 minutes, after revoking the account's other live reset links (another account's
   stay); the link works once with ``POST /auth/password-reset``. 404.
7. ``POST /users/{user_id}/sessions/revoke`` → 204: every session of that account ends, no other one; 404.
8. ``POST /users/{user_id}/onboarding/reset`` ``{flow?}`` → 204: every flow, steps included, or only the one named, back
   to ``pending``, as the account itself reads it from ``GET /settings/onboarding`` (21-5); an unknown flow is a 422 that
   resets nothing; 404.
9. Every action writes a structured log event, and no log carries a token. The plaintext (hence neither the path nor the
   URL) appears in no structlog event and no stdlib record, whatever the logger. Its hash appears in no structlog event
   and in no record of the application's loggers. The third-party loggers that ``configure_logging`` silences to WARNING
   (``aiosqlite``, ``sqlalchemy.engine``, …) are excluded: they log every statement with its parameters, the stored
   hash included, so a running server never emits those records.

Coded refusals are read from ``detail.error_code``, the shape ``POST /auth/login`` gives ``ACCOUNT_DISABLED`` and
``test_registration_api.py`` reads; the administrator's ``USER_LIMIT_REACHED`` carries ``limit``, ``used`` and
``billing_url`` in the same ``detail``.

Where each case runs, and why. The lane is shared: its registration mode is one row on which every unit's
registrations depend, the ``LIBREFOLIO_*`` variables are read by the lane's server (another process), and «the last
active administrator» depends on every account of the lane's database. So:

- **on the lane's server** run only the cases that hold whatever the neighbours do. Each test registers its own accounts
  (its administrator promoted through ``user_service``, never a shared E2E user), acts only on them and on the tokens
  they hold or issue, finds every row by id, and never counts the lane: ``used`` is only bounded below by the test's own
  active accounts. Deactivating or demoting one of its accounts is deterministic there, because the caller is an active
  administrator who is never the target. The lane must be ``open``, as every unit that registers its users needs it;
  nothing here writes a setting. Teardown deletes the test's tokens (by id, issuer, consumer and marker e-mail), then its
  accounts, after a red too;
- **in-process**, on a private SQLite file under ``tmp_path``, run the cases that need a mode, a limit, a public or
  billing URL, «the last administrator», an expired token or exact counts: the real routers of auth, users and settings,
  mounted as ``api/v1/router.py`` mounts them, in an app of this test whose ``get_session_generator`` opens sessions on
  that file. The variables are set with ``monkeypatch`` in this process only. Two assumptions follow: the endpoints take
  their session from ``get_session_generator``, as every handler does, and the accessors of ``config/accounts.py`` read
  the environment at each call.

The unit is therefore write-scoped (the ``api`` category's default), with no ``exclusive_because``. bcrypt runs at its
lowest cost in this process (``auth_service.BCRYPT_ROUNDS = 4``, as in ``test_registration_api.py``); the lane's server
keeps its own.

Red until A5a: the routes do not exist.
"""

import ast
import inspect
import logging
import re
import textwrap
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import pytest_asyncio
import structlog
from fastapi import FastAPI
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app import logging_config
from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import settings as settings_api
from backend.app.api.v1 import users as users_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, OnboardingFlow, User, UserOnboardingProgress
from backend.app.db.session import get_async_engine, get_session_generator
from backend.app.services.accounts import auth_service, user_service
from backend.app.services.accounts.onboarding_service import ONBOARDING_FLOW_STEPS, ONBOARDING_FLOW_VERSIONS
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, consume_token, hash_token, issue_token
from backend.app.utils.datetime_utils import utcnow
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET

REGISTRATION_VARIABLE = "LIBREFOLIO_REGISTRATION"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BILLING_URL_VARIABLE = "LIBREFOLIO_BILLING_URL"
ACCOUNTS_VARIABLES = (REGISTRATION_VARIABLE, MAX_USERS_VARIABLE, PUBLIC_URL_VARIABLE, BILLING_URL_VARIABLE)
MODE_KEY = "registration_mode"

#: Set with a trailing slash on purpose: a link is the URL without it, then the path.
PUBLIC_URL = "https://librefolio.example.test/base/"
PUBLIC_ORIGIN = "https://librefolio.example.test/base"
BILLING_LINK = "https://billing.example.test/plans/family"

USER_ITEM_KEYS = frozenset({"id", "username", "email", "is_active", "is_superuser", "created_at"})
INVITE_ITEM_KEYS = frozenset({"id", "grants_admin", "email", "created_at", "expires_at", "created_by_user_id"})
USAGE_KEYS = frozenset({"used", "max_users", "billing_url"})
ISSUED_INVITE_KEYS = frozenset({"invite", "token", "path", "url"})
RESET_LINK_KEYS = frozenset({"token", "path", "url", "expires_at"})
#: secrets.token_urlsafe(32): 43 URL-safe characters.
TOKEN_SHAPE = re.compile(r"[A-Za-z0-9_-]{43}")
#: The page of each kind of link; the token follows in the fragment, ``#token=…``.
LINK_PAGES = {INVITE: "/invite", PASSWORD_RESET: "/reset-password"}
#: GET /auth/me's answer to a cookie whose session was ended.
SESSION_EXPIRED = (401, {"detail": "Session expired or invalid"})

PRIVATE_PASSWORD = "Users-Admin-Api-2026"
NEW_PASSWORD = "Reset-By-Link-2026"
THIRD_PASSWORD = "Reset-Again-2026"
#: Far above any id a private database of a few rows reaches.
NEVER_ISSUED_ID = 987_654_321
CANARY = "canary: the capture sees the events of the admin endpoints' logger"

STEP_FLOWS = {flow.value: tuple(steps) for flow, steps in ONBOARDING_FLOW_STEPS.items()}


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the lane cases only (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# SHARED HELPERS
# ============================================================================


@dataclass(frozen=True)
class _Account:
    """An account one test created."""

    user_id: int
    username: str
    email: str
    password: str


@dataclass(frozen=True)
class _Signed:
    """An account with the session cookie of one device."""

    account: _Account
    cookie: str


def _expect(violations: list[str], ok: bool, message: str) -> None:
    """Record a broken expectation instead of stopping at the first one: the red lists them all."""
    if not ok:
        violations.append(message)


def _verdict(violations: list[str]) -> str:
    return "\n- " + "\n- ".join(violations)


def _detail(response: httpx.Response) -> dict[str, Any]:
    """``detail`` of a coded refusal as a mapping; {} when the body carries none."""
    try:
        body = response.json()
    except ValueError:
        return {}
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail if isinstance(detail, dict) else {}


def _refusal(response: httpx.Response) -> tuple[int, Optional[str]]:
    """(status, ``detail.error_code``): (201, None) for a success."""
    return response.status_code, _detail(response).get("error_code")


def _counts(response: httpx.Response) -> dict[str, Any]:
    """What the administrator's ``USER_LIMIT_REACHED`` says, read from ``detail``: the code, the limit, the seats used, the billing link."""
    detail = _detail(response)
    return {key: detail.get(key) for key in ("error_code", "limit", "used", "billing_url")}


def _answer(response: httpx.Response) -> tuple[int, Any]:
    """The status and the JSON body (the text when it is not JSON)."""
    try:
        return response.status_code, response.json()
    except ValueError:
        return response.status_code, response.text


def _session_cookie(response: httpx.Response) -> Optional[str]:
    """The value of the response's ``session`` Set-Cookie, parsed by name; None when there is none."""
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE and value:
            return value
    return None


def _instant(text: Any) -> Optional[datetime]:
    """An API timestamp as an aware UTC datetime (a naive one is UTC); None when it is not a timestamp."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _comparable(item: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """An item with its timestamps as instants: two serialisations of the same moment compare equal."""
    if item is None:
        return None
    return {key: _instant(value) if key.endswith("_at") else value for key, value in item.items()}


def _user_item_violations(item: Any, account: _Account, *, active: bool, superuser: bool) -> list[str]:
    """What is wrong with an account as GET /users lists it, and PATCH answers it: exactly its six fields, with these values."""
    if not isinstance(item, dict) or set(item) != USER_ITEM_KEYS:
        return [f"{account.username}: an account must be exactly {sorted(USER_ITEM_KEYS)}, no hash and no secret: {item}"]
    expected = {"id": account.user_id, "username": account.username, "email": account.email, "is_active": active, "is_superuser": superuser}
    found = {key: item[key] for key in expected}
    violations = [] if found == expected else [f"{account.username}: expected {expected}, got {found}"]
    _expect(violations, _instant(item["created_at"]) is not None, f"{account.username}: created_at is not a timestamp: {item['created_at']!r}")
    return violations


def _link_path_violations(path: Any, purpose: AccountTokenPurpose, token: str) -> list[str]:
    """What is wrong with a link's ``path``: the purpose's page, no query, and the token alone in the URL fragment (``#token=…``).

    The fragment because a browser never sends it: the token stays out of the access log and of every proxy's log.
    """
    if not isinstance(path, str):
        return [f"path: a string expected, got {path!r}"]
    parts = urlparse(path)
    found = {"page": (parts.scheme, parts.netloc, parts.path), "query": parts.query, "fragment": parse_qs(parts.fragment)}
    expected = {"page": ("", "", LINK_PAGES[purpose]), "query": "", "fragment": {"token": [token]}}
    return [] if found == expected else [f"path: expected {LINK_PAGES[purpose]}#token=<the token>, nothing in the query; got {path!r}, read as {found}"]


def _issued_invite_violations(issued: Any, *, grants_admin: bool, email: Optional[str], created_by: int) -> list[str]:
    """What is wrong with the 201 of POST /users/invites: its keys, the token, its path, the invitation and its seven days."""
    if not isinstance(issued, dict) or set(issued) != ISSUED_INVITE_KEYS:
        return [f"the 201 body must be exactly {sorted(ISSUED_INVITE_KEYS)}: {issued}"]
    token, invite = str(issued["token"]), issued["invite"]
    violations: list[str] = []
    _expect(violations, TOKEN_SHAPE.fullmatch(token) is not None, f"token: 43 URL-safe characters expected, got {token!r}")
    violations += _link_path_violations(issued["path"], INVITE, token)
    if not isinstance(invite, dict) or set(invite) != INVITE_ITEM_KEYS:
        return [*violations, f"invite: exactly {sorted(INVITE_ITEM_KEYS)} expected, got {invite}"]
    found = (invite["grants_admin"], invite["email"], invite["created_by_user_id"])
    _expect(violations, found == (grants_admin, email, created_by), f"invite: (grants_admin, email, created_by_user_id) must be {(grants_admin, email, created_by)}, got {found}")
    created, expires = _instant(invite["created_at"]), _instant(invite["expires_at"])
    lives = None if created is None or expires is None else expires - created
    _expect(violations, lives == DEFAULT_TTL[INVITE], f"invite: an invitation lives {DEFAULT_TTL[INVITE]} from its creation, this one {lives}: {invite}")
    return violations


def _reset_link_violations(link: Any) -> list[str]:
    """What is wrong with the 201 of POST /users/{id}/password-reset-link: its keys, the token, its path, its expiry."""
    if not isinstance(link, dict) or set(link) != RESET_LINK_KEYS:
        return [f"the 201 body must be exactly {sorted(RESET_LINK_KEYS)}: {link}"]
    token = str(link["token"])
    violations: list[str] = []
    _expect(violations, TOKEN_SHAPE.fullmatch(token) is not None, f"token: 43 URL-safe characters expected, got {token!r}")
    violations += _link_path_violations(link["path"], PASSWORD_RESET, token)
    _expect(violations, _instant(link["expires_at"]) is not None, f"expires_at is not a timestamp: {link['expires_at']!r}")
    return violations


def _url_violations(body: dict[str, Any], public_origin: Optional[str]) -> list[str]:
    """``url`` is the public URL (its trailing slash dropped) plus ``path``, the token still in the fragment; or null without a public URL."""
    expected = None if public_origin is None else f"{public_origin}{body.get('path')}"
    if body.get("url") != expected:
        return [f"url: expected {expected!r}, got {body.get('url')!r} (path {body.get('path')!r})"]
    url_parts = urlparse(expected) if expected else None
    in_the_fragment = url_parts is None or (url_parts.query == "" and parse_qs(url_parts.fragment) == {"token": [str(body.get("token"))]})
    return [] if in_the_fragment else [f"url: the token must travel in the fragment, not in the query: {expected!r}"]


def _onboarding_reading(body: Any) -> dict[str, tuple[str, dict[str, str]]]:
    """GET /settings/onboarding as {flow: (status, {step: status})}, steps empty for a flow without them."""
    return {item["flow"]: (item["status"], {step["step_id"]: step["status"] for step in item.get("steps") or []}) for item in body["flows"]}


def _pending(flow: str) -> tuple[str, dict[str, str]]:
    """A flow as a never-touched account reads it: pending, and every step of it pending."""
    return "pending", dict.fromkeys(STEP_FLOWS.get(flow, ()), "pending")


# ============================================================================
# THE LANE: ITS SERVER AND ITS DATABASE
# ============================================================================


def _lane_engine() -> AsyncEngine:
    """The lane's test database, the one its server serves: the lane cases read and delete their own rows there, nowhere else."""
    is_test_db, database_url = verify_test_database()
    assert is_test_db, f"Refusing to touch a database that is not the lane's test database: {database_url}"
    return get_async_engine()


@dataclass
class _LaneRows:
    """What a lane case wrote: accounts by name (even one a red let through), tokens by id, the marker e-mails of invitations."""

    usernames: list[str] = field(default_factory=list)
    token_ids: list[int] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)

    def new_username(self, prefix: str) -> str:
        username = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self.usernames.append(username)
        return username

    def new_email(self, prefix: str) -> str:
        email = f"{prefix}_{uuid.uuid4().hex[:12]}@example.com"
        self.emails.append(email)
        return email


async def _delete_lane_rows(rows: _LaneRows) -> list[str]:
    """Delete the case's tokens (by id, issued or consumed by its accounts, or to its marker e-mails), then its accounts; what failed."""
    errors: list[str] = []
    engine = _lane_engine()
    async with AsyncSession(engine) as session:
        user_ids = list((await session.execute(select(User.id).where(User.username.in_(rows.usernames)))).scalars().all())
        mine = or_(AccountToken.id.in_(rows.token_ids), AccountToken.email.in_(rows.emails), AccountToken.created_by_user_id.in_(user_ids), AccountToken.consumed_by_user_id.in_(user_ids))
        try:
            await session.execute(delete(AccountToken).where(mine))
            await session.commit()
        except Exception as exc:  # the accounts still get their attempt; every failure is reported together
            errors.append(f"tokens: {exc!r}")
    for user_id in user_ids:
        async with AsyncSession(engine) as session:
            try:
                await user_service.delete_user(session, user_id)
            except Exception as exc:
                errors.append(f"user {user_id}: {exc!r}")
    return errors


@pytest_asyncio.fixture
async def lane(test_server) -> AsyncIterator[_LaneRows]:
    """The lane's server, in its own mode (open); what the case writes there is deleted at teardown, after a red too."""
    rows = _LaneRows()
    try:
        yield rows
    finally:
        errors = await _delete_lane_rows(rows)
        assert not errors, f"Teardown: could not delete what this test wrote in the lane: {errors}"


async def _live(method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request to the lane's server from a client of its own: no cookie jar, the session (if any) sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    async with httpx.AsyncClient() as client:
        return await client.request(method, f"{API_BASE}{path}", json=json, headers=headers, timeout=TIMEOUT)


async def _live_register(lane: _LaneRows, prefix: str) -> _Account:
    """A regular account of this case, registered over HTTP in the lane's own mode, which must be open."""
    username = lane.new_username(prefix)
    email, password = f"{username}@example.com", f"Initial-{uuid.uuid4().hex[:12]}"
    response = await _live("POST", "/auth/register", json={"username": username, "email": email, "password": password})
    assert response.status_code == 201, f"Setup: registering {username} on the lane failed; its mode must be open, as every unit registering its own users needs it: {response.status_code} {response.text}"
    user = response.json()["user"]
    assert user["is_superuser"] is False, f"Precondition: {username} registered as the lane's first account, hence its administrator: the api setup (db populate) did not run on this lane"
    return _Account(user_id=user["id"], username=username, email=email, password=password)


async def _live_login(account: _Account, password: Optional[str] = None) -> httpx.Response:
    """POST /auth/login from a client of its own: a new device."""
    return await _live("POST", "/auth/login", json={"username": account.username, "password": password or account.password})


async def _live_sign_in(account: _Account, password: Optional[str] = None) -> str:
    """A new device of ``account``: a login, and the session cookie it sets."""
    response = await _live_login(account, password)
    cookie = _session_cookie(response)
    assert response.status_code == 200 and cookie, f"Login as {account.username} failed: {response.status_code} {response.text}"
    return cookie


async def _live_member(lane: _LaneRows, prefix: str) -> _Signed:
    """A regular account of this case, signed in on one device."""
    account = await _live_register(lane, prefix)
    return _Signed(account, await _live_sign_in(account))


async def _lane_set(username: str, *, admin: Optional[bool] = None, active: Optional[bool] = None) -> None:
    """Promote, demote, activate or deactivate one of this case's accounts through user_service, in the lane's database."""
    async with AsyncSession(_lane_engine()) as session:
        if admin is not None:
            done, error = await user_service.set_user_admin(session, username, admin)
            assert done, f"Setup: set_user_admin({username!r}, {admin}) failed: {error}"
        if active is not None:
            done, error = await user_service.set_user_active(session, username, active)
            assert done, f"Setup: set_user_active({username!r}, {active}) failed: {error}"


async def _live_admin(lane: _LaneRows) -> _Signed:
    """An administrator of this case: registered, promoted through user_service, then signed in."""
    account = await _live_register(lane, "uadm_admin")
    await _lane_set(account.username, admin=True)
    cookie = await _live_sign_in(account)
    status, body = await _live_me(cookie)
    assert status == 200 and body["user"]["is_superuser"] is True, f"Setup: {account.username} must be signed in as an administrator: {status} {body}"
    return _Signed(account, cookie)


async def _live_me(cookie: str) -> tuple[int, Any]:
    """GET /auth/me with this session cookie only."""
    return _answer(await _live("GET", "/auth/me", cookie=cookie))


async def _live_me_id(cookie: str) -> Optional[int]:
    """The id of the account this cookie is a session of; None when GET /auth/me refuses it."""
    status, body = await _live_me(cookie)
    return body["user"]["id"] if status == 200 else None


async def _listed(cookie: str, path: str, item_id: int) -> Optional[dict[str, Any]]:
    """The item of id ``item_id`` in GET ``path`` (/users or /users/invites) as this administrator sees it, found by id; None when absent."""
    response = await _live("GET", path, cookie=cookie)
    assert response.status_code == 200, f"GET {path} as an administrator: expected 200, got {response.status_code} {response.text}"
    return next((item for item in response.json()["items"] if item.get("id") == item_id), None)


async def _live_register_with(lane: _LaneRows, prefix: str, invite_token: str) -> tuple[str, httpx.Response]:
    """POST /auth/register with ``invite_token``, for a new username of this case."""
    username = lane.new_username(prefix)
    body = {"username": username, "email": f"{username}@example.com", "password": f"Invited-{uuid.uuid4().hex[:12]}", "invite_token": invite_token}
    return username, await _live("POST", "/auth/register", json=body)


async def _live_reset_password(token: str, new_password: str) -> httpx.Response:
    """POST /auth/password-reset, anonymous: whoever holds the link."""
    return await _live("POST", "/auth/password-reset", json={"token": token, "new_password": new_password})


async def _admin_reset_link(admin: _Signed, user_id: int) -> str:
    """A reset link for ``user_id``, issued by ``admin`` through the API: its token."""
    response = await _live("POST", f"/users/{user_id}/password-reset-link", cookie=admin.cookie)
    assert response.status_code == 201, f"POST /users/{user_id}/password-reset-link: expected 201, got {response.status_code} {response.text}"
    return response.json()["token"]


async def _live_onboarding(cookie: str) -> dict[str, tuple[str, dict[str, str]]]:
    """The account's own onboarding, read from GET /settings/onboarding with its session."""
    response = await _live("GET", "/settings/onboarding", cookie=cookie)
    assert response.status_code == 200, f"GET /settings/onboarding: {response.status_code} {response.text}"
    return _onboarding_reading(response.json())


async def _live_onboarding_move(cookie: str, flow: OnboardingFlow, action: str, step: Optional[str] = None) -> None:
    """Complete or skip a flow, or one of its steps, as the account itself does from the app."""
    path = f"/settings/onboarding/{flow.value}/{action}" if step is None else f"/settings/onboarding/{flow.value}/steps/{step}/{action}"
    response = await _live("POST", path, cookie=cookie, json={"expected_version": ONBOARDING_FLOW_VERSIONS[flow]})
    assert response.status_code == 200, f"Setup: POST {path}: {response.status_code} {response.text}"


async def _lane_user(user_id: int) -> tuple[bool, bool, int]:
    """(is_active, is_superuser, session_version) of one of this case's accounts, read fresh from the lane's database."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one()
    return bool(row[0]), bool(row[1]), int(row[2])


async def _lane_user_id(username: str) -> Optional[int]:
    async with AsyncSession(_lane_engine()) as session:
        return (await session.execute(select(User.id).where(User.username == username))).scalar_one_or_none()


async def _lane_issue(lane: _LaneRows, purpose: AccountTokenPurpose, **arguments: Any) -> IssuedToken:
    """A token issued by token_service directly in the lane's database, committed, and recorded for the teardown."""
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    lane.token_ids.append(issued.record.id)
    return issued


async def _lane_consume(token: str, purpose: AccountTokenPurpose, consumed_by_user_id: int) -> None:
    async with AsyncSession(_lane_engine()) as session:
        record = await consume_token(session, token, purpose, consumed_by_user_id=consumed_by_user_id)
        await session.commit()
    assert record is not None, "Setup: the token must be consumed"


async def _lane_token_of(token: str) -> Optional[AccountToken]:
    """The lane's row of a plaintext token, found by its hash as stored."""
    async with AsyncSession(_lane_engine(), expire_on_commit=False) as session:
        return (await session.execute(select(AccountToken).where(AccountToken.token_hash == hash_token(token)))).scalars().first()


async def _lane_token_state(token_id: int) -> tuple[Any, Any, Any]:
    """(purpose, consumed_at, revoked_at) of one of this case's tokens."""
    async with AsyncSession(_lane_engine()) as session:
        row = (await session.execute(select(AccountToken.purpose, AccountToken.consumed_at, AccountToken.revoked_at).where(AccountToken.id == token_id))).one()
    return row[0], row[1], row[2]


async def _lane_reset_links(user_id: int) -> int:
    """How many reset links this case's account has ever had: it owns them all."""
    async with AsyncSession(_lane_engine()) as session:
        statement = select(func.count()).select_from(AccountToken).where(AccountToken.user_id == user_id, AccountToken.purpose == PASSWORD_RESET.value)
        return int((await session.execute(statement)).scalar_one())


# ============================================================================
# LANE: ONLY AN ADMINISTRATOR, AND A REFUSED CALL CHANGES NOTHING
# ============================================================================


@dataclass(frozen=True)
class _Scene:
    """An administrator, an ordinary account (the refused caller), a target account signed in with intro_tour completed, a live invitation, and an e-mail no invitation carries yet."""

    admin: _Signed
    member: _Signed
    target: _Signed
    invite_id: int
    marker_email: str


async def _scene(lane: _LaneRows) -> _Scene:
    admin = await _live_admin(lane)
    member = await _live_member(lane, "uadm_member")
    target = await _live_member(lane, "uadm_target")
    await _live_onboarding_move(target.cookie, OnboardingFlow.INTRO_TOUR, "complete")
    invite = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
    return _Scene(admin=admin, member=member, target=target, invite_id=invite.record.id, marker_email=lane.new_email("uadm_marker"))


async def _footprint(scene: _Scene) -> dict[str, Any]:
    """Everything an admin route could change in the scene, read fresh from the lane's database."""
    target_id = scene.target.account.user_id
    async with AsyncSession(_lane_engine()) as session:
        target = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == target_id))).one()
        invite = (await session.execute(select(AccountToken.consumed_at, AccountToken.revoked_at).where(AccountToken.id == scene.invite_id))).one()
        marker = (await session.execute(select(func.count()).select_from(AccountToken).where(AccountToken.email == scene.marker_email))).scalar_one()
        tour = (await session.execute(select(UserOnboardingProgress.status).where(UserOnboardingProgress.user_id == target_id, UserOnboardingProgress.flow == OnboardingFlow.INTRO_TOUR.value))).scalar_one_or_none()
    return {
        "the target (is_active, is_superuser, session_version)": tuple(target),
        "the scene's invitation (consumed_at, revoked_at)": tuple(invite),
        "invitations to the marker e-mail": marker,
        "reset links of the target": await _lane_reset_links(target_id),
        "the target's intro_tour": tour,
    }


@dataclass(frozen=True)
class _Route:
    """An admin route as the matrix calls it, with the status an administrator gets."""

    method: str
    path: Callable[[_Scene], str]
    body: Callable[[_Scene], Any]
    success: int


def _on_target(suffix: str) -> Callable[[_Scene], str]:
    return lambda scene: f"/users/{scene.target.account.user_id}{suffix}"


def _no_body(scene: _Scene) -> None:
    return None


ADMIN_ROUTES = [
    pytest.param(_Route("GET", lambda scene: "/users/invites", _no_body, 200), id="list-invites"),
    pytest.param(_Route("POST", lambda scene: "/users/invites", lambda scene: {"grants_admin": True, "email": scene.marker_email}, 201), id="create-invite"),
    pytest.param(_Route("DELETE", lambda scene: f"/users/invites/{scene.invite_id}", _no_body, 204), id="revoke-invite"),
    pytest.param(_Route("GET", lambda scene: "/users", _no_body, 200), id="list-users"),
    pytest.param(_Route("PATCH", _on_target(""), lambda scene: {"is_active": False}, 200), id="deactivate-user"),
    pytest.param(_Route("POST", _on_target("/password-reset-link"), _no_body, 201), id="reset-link"),
    pytest.param(_Route("POST", _on_target("/sessions/revoke"), _no_body, 204), id="revoke-sessions"),
    pytest.param(_Route("POST", _on_target("/onboarding/reset"), lambda scene: {}, 204), id="reset-onboarding"),
]


class TestOnlyAnAdministrator:
    """Every admin route on the lane's server: anonymous 401, an ordinary account 403, neither changes anything; the administrator gets through."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("route", ADMIN_ROUTES)
    async def test_anonymous_401_ordinary_403_nothing_changes_and_the_administrator_gets_through(self, lane: _LaneRows, route: _Route) -> None:
        """UADM-001: no session → 401, an ordinary account's session → 403, and after each the scene is as it was (the target's state and sessions, the invitation, no invitation issued, no reset link, the onboarding); then the administrator gets the route's success status.

        Each call acts on what a wrongly open route would visibly change: the deactivation of the target, an invitation to a
        marker e-mail, the revocation of a live invitation, the target's sessions, reset links and completed intro_tour.
        """
        scene = await _scene(lane)
        path, body = route.path(scene), route.body(scene)
        print_section(f"UADM-001: {route.method} {path} is for administrators only")
        before = await _footprint(scene)

        anonymous = await _live(route.method, path, json=body)
        after_anonymous = await _footprint(scene)
        ordinary = await _live(route.method, path, cookie=scene.member.cookie, json=body)
        after_ordinary = await _footprint(scene)
        admin = await _live(route.method, path, cookie=scene.admin.cookie, json=body)

        violations: list[str] = []
        _expect(violations, anonymous.status_code == 401, f"anonymous: expected 401, got {anonymous.status_code} {anonymous.text}")
        _expect(violations, after_anonymous == before, f"the anonymous call changed the lane: {before} → {after_anonymous}")
        _expect(violations, ordinary.status_code == 403, f"an ordinary account: expected 403, got {ordinary.status_code} {ordinary.text}")
        _expect(violations, after_ordinary == before, f"the ordinary account's call changed the lane: {before} → {after_ordinary}")
        _expect(violations, admin.status_code == route.success, f"the administrator: expected {route.success}, got {admin.status_code} {admin.text}")
        assert not violations, f"{route.method} {path} must be an administrator's route only:{_verdict(violations)}"
        print_success(f"{route.method} {path}: 401, 403, nothing changed, then {route.success} for the administrator")

    @pytest.mark.asyncio
    async def test_an_ordinary_account_cannot_make_itself_an_administrator_nor_mint_its_own_reset_link(self, lane: _LaneRows) -> None:
        """UADM-002: an ordinary account aiming the routes at itself — PATCH {is_superuser: true}, POST its own reset link — gets 403 for both, and is still an ordinary account with no reset link."""
        print_section("UADM-002: no route makes an ordinary account an administrator of itself")
        member = await _live_member(lane, "uadm_climber")
        user_id = member.account.user_id
        before = await _lane_user(user_id)

        promote = await _live("PATCH", f"/users/{user_id}", cookie=member.cookie, json={"is_superuser": True})
        link = await _live("POST", f"/users/{user_id}/password-reset-link", cookie=member.cookie)

        violations: list[str] = []
        _expect(violations, promote.status_code == 403, f"PATCH /users/{{self}} {{is_superuser: true}}: expected 403, got {promote.status_code} {promote.text}")
        _expect(violations, link.status_code == 403, f"POST /users/{{self}}/password-reset-link: expected 403, got {link.status_code} {link.text}")
        _expect(violations, await _lane_user(user_id) == before, f"the account changed: {before} → {await _lane_user(user_id)}")
        _expect(violations, await _lane_reset_links(user_id) == 0, "a reset link was issued to the account that asked for it")
        assert not violations, f"An ordinary account must not reach the admin routes, not even about itself:{_verdict(violations)}"
        print_success("403 twice, still an ordinary account, no reset link")


# ============================================================================
# LANE: THE ACCOUNTS AND THE INVITATIONS
# ============================================================================


class TestAccountsListOnTheLane:
    @pytest.mark.asyncio
    async def test_lists_this_cases_accounts_with_their_flags_and_the_usage(self, lane: _LaneRows) -> None:
        """UADM-003: GET /users → {items, usage}; this case's four accounts are there, found by id — the caller, an ordinary account, a second administrator, an inactive account — each exactly {id, username, email, is_active, is_superuser, created_at} with the right flags; usage is {used, max_users, billing_url}, and used counts at least this case's three active accounts."""
        print_section("UADM-003: GET /users")
        admin = await _live_admin(lane)
        member = await _live_register(lane, "uadm_listed")
        second_admin = await _live_register(lane, "uadm_listed_admin")
        inactive = await _live_register(lane, "uadm_listed_off")
        await _lane_set(second_admin.username, admin=True)
        await _lane_set(inactive.username, active=False)

        response = await _live("GET", "/users", cookie=admin.cookie)

        assert response.status_code == 200, f"GET /users as an administrator: {response.status_code} {response.text}"
        body = response.json()
        assert isinstance(body, dict) and set(body) == {"items", "usage"}, f"GET /users must answer exactly {{items, usage}}: {body}"
        items = {item.get("id"): item for item in body["items"]}
        violations: list[str] = []
        for account, active, superuser in ((admin.account, True, True), (member, True, False), (second_admin, True, True), (inactive, False, False)):
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser)
        usage = body["usage"]
        _expect(violations, isinstance(usage, dict) and set(usage) == USAGE_KEYS, f"usage must be exactly {sorted(USAGE_KEYS)}: {usage}")
        _expect(violations, isinstance(usage, dict) and isinstance(usage.get("used"), int) and usage["used"] >= 3, f"usage.used counts the active accounts, this case's three at least: {usage}")
        assert not violations, f"GET /users broke its contract:{_verdict(violations)}"
        print_success("four accounts of this case listed with their flags, usage present")


class TestInvitationsOnTheLane:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("grants_admin", "with_email"), [pytest.param(False, False, id="user-invitation"), pytest.param(True, True, id="admin-invitation-with-email")])
    async def test_an_invitation_is_listed_opens_one_account_in_its_role_then_is_gone(self, lane: _LaneRows, grants_admin: bool, with_email: bool) -> None:
        """UADM-004: POST /users/invites → 201 {invite, token, path, url}; GET /users/invites lists exactly that invitation; its token registers one account through POST /auth/register, in the invitation's role; then the invitation is no longer listed, its row is consumed by that account, and the same token registers nobody else (400 INVITE_INVALID)."""
        print_section(f"UADM-004: the life of an invitation, grants_admin={grants_admin}")
        admin = await _live_admin(lane)
        email = lane.new_email("uadm_invitee") if with_email else None
        request = {"grants_admin": grants_admin, **({"email": email} if email else {})}

        created = await _live("POST", "/users/invites", cookie=admin.cookie, json=request)

        assert created.status_code == 201, f"POST /users/invites: expected 201, got {created.status_code} {created.text}"
        issued = created.json()
        violations = _issued_invite_violations(issued, grants_admin=grants_admin, email=email, created_by=admin.account.user_id)
        assert not violations, f"POST /users/invites answered a 201 that breaks its contract:{_verdict(violations)}"
        token, invite = issued["token"], issued["invite"]
        lane.token_ids.append(invite["id"])
        _expect(violations, issued["url"] is None or issued["url"].endswith(issued["path"]), f"url must be null or end with the path: {issued}")
        listed = await _listed(admin.cookie, "/users/invites", invite["id"])
        _expect(violations, _comparable(listed) == _comparable(invite), f"GET /users/invites must list the invitation as it was created: listed {listed}, created {invite}")
        row = await _lane_token_of(token)
        _expect(violations, row is not None and row.id == invite["id"] and row.purpose == INVITE.value and row.consumed_at is None, f"the token must be the stored hash of the live invitation {invite['id']}: {row}")
        assert not violations, f"the new invitation is not what was asked:{_verdict(violations)}"

        _, registered = await _live_register_with(lane, "uadm_invited", token)

        assert registered.status_code == 201, f"POST /auth/register with the invitation: expected 201, got {registered.status_code} {registered.text}"
        user = registered.json()["user"]
        _expect(violations, user["is_superuser"] is grants_admin, f"the account must take the invitation's role, is_superuser={grants_admin}: {user}")
        _expect(violations, await _listed(admin.cookie, "/users/invites", invite["id"]) is None, "a consumed invitation must no longer be listed")
        row = await _lane_token_of(token)
        _expect(violations, row is not None and row.consumed_by_user_id == user["id"], f"the invitation must be consumed by the account it opened: {row}")
        again_username, again = await _live_register_with(lane, "uadm_invited_again", token)
        _expect(violations, _refusal(again) == (400, "INVITE_INVALID"), f"a consumed invitation must register nobody else: {again.status_code} {again.text}")
        _expect(violations, await _lane_user_id(again_username) is None, f"{again_username} was created with a consumed invitation")
        assert not violations, f"An invitation must open one account, in its role, once:{_verdict(violations)}"
        print_success(f"listed, opened {user['username']} (is_superuser={grants_admin}), then gone and spent")

    @pytest.mark.asyncio
    async def test_a_revoked_invitation_is_gone_and_opens_nothing(self, lane: _LaneRows) -> None:
        """UADM-005: DELETE /users/invites/{id} → 204 with no body; the invitation is no longer listed and its row is revoked; a second DELETE → 404; its token → 400 INVITE_INVALID at POST /auth/register, and no account."""
        print_section("UADM-005: a revoked invitation")
        admin = await _live_admin(lane)
        created = await _live("POST", "/users/invites", cookie=admin.cookie, json={"grants_admin": False})
        assert created.status_code == 201, f"POST /users/invites: expected 201, got {created.status_code} {created.text}"
        invite_id, token = created.json()["invite"]["id"], created.json()["token"]
        lane.token_ids.append(invite_id)

        revoked = await _live("DELETE", f"/users/invites/{invite_id}", cookie=admin.cookie)
        again = await _live("DELETE", f"/users/invites/{invite_id}", cookie=admin.cookie)
        username, registered = await _live_register_with(lane, "uadm_revoked_invitee", token)

        violations: list[str] = []
        _expect(violations, (revoked.status_code, revoked.content) == (204, b""), f"DELETE: expected 204 with no body, got {revoked.status_code} {revoked.text}")
        _expect(violations, await _listed(admin.cookie, "/users/invites", invite_id) is None, "a revoked invitation must no longer be listed")
        purpose, consumed_at, revoked_at = await _lane_token_state(invite_id)
        _expect(violations, revoked_at is not None and consumed_at is None, f"the row must be revoked, not consumed: consumed_at={consumed_at}, revoked_at={revoked_at}")
        _expect(violations, again.status_code == 404, f"a second DELETE: expected 404, got {again.status_code} {again.text}")
        _expect(violations, _refusal(registered) == (400, "INVITE_INVALID"), f"a revoked invitation must register nobody: {registered.status_code} {registered.text}")
        _expect(violations, await _lane_user_id(username) is None, f"{username} was created with a revoked invitation")
        assert not violations, f"A revoked invitation must be gone:{_verdict(violations)}"
        print_success("204, unlisted, 404 the second time, its token opens nothing")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["consumed-invitation", "live-reset-link"])
    async def test_what_is_not_a_live_invitation_cannot_be_revoked_and_stays_as_it_was(self, lane: _LaneRows, kind: str) -> None:
        """UADM-006: DELETE /users/invites/{id} of a consumed invitation, or of the id of a live password-reset link → 404, and the row is untouched: the reset link stays live.

        Presence barrier first: a live invitation of this case is revoked with 204. A route that does not exist answers 404 too.
        """
        print_section(f"UADM-006: DELETE /users/invites/{{id}} of a {kind}")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_holder")
        barrier = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
        revoked = await _live("DELETE", f"/users/invites/{barrier.record.id}", cookie=admin.cookie)
        assert revoked.status_code == 204, f"Presence barrier: DELETE of a live invitation of this case must answer 204, or the 404 below proves nothing: {revoked.status_code} {revoked.text}"
        if kind == "live-reset-link":
            issued = await _lane_issue(lane, PASSWORD_RESET, user_id=holder.user_id)
        else:
            issued = await _lane_issue(lane, INVITE, created_by_user_id=admin.account.user_id)
            await _lane_consume(issued.token, INVITE, holder.user_id)
        before = await _lane_token_state(issued.record.id)

        response = await _live("DELETE", f"/users/invites/{issued.record.id}", cookie=admin.cookie)

        assert response.status_code == 404, f"only a live invitation can be revoked: expected 404 for a {kind}, got {response.status_code} {response.text}"
        assert await _lane_token_state(issued.record.id) == before, f"the {kind} changed: {before} → {await _lane_token_state(issued.record.id)}"
        print_success(f"{kind}: 404, untouched")


# ============================================================================
# LANE: STATE AND ROLE OF AN ACCOUNT
# ============================================================================


UNKNOWN_ACCOUNT_ROUTES = [
    pytest.param("PATCH", "", {"is_active": False}, 200, id="patch"),
    pytest.param("POST", "/password-reset-link", None, 201, id="reset-link"),
    pytest.param("POST", "/sessions/revoke", None, 204, id="revoke-sessions"),
    pytest.param("POST", "/onboarding/reset", {}, 204, id="reset-onboarding"),
]


class TestAccountStateOnTheLane:
    """PATCH /users/{id} on this case's own accounts. The caller is an active administrator and never the target, so the last-administrator guard never applies here, whatever the lane holds."""

    @pytest.mark.asyncio
    async def test_deactivation_ends_the_sessions_and_reactivation_does_not_bring_them_back(self, lane: _LaneRows) -> None:
        """UADM-007: PATCH {is_active: false} → 200 with the account; its cookie is refused (401), its password gets 403 ACCOUNT_DISABLED, its session version rose by one. PATCH {is_active: true} → 200; the old cookie stays refused (401 «Session expired or invalid»), the version does not move, a new login works."""
        print_section("UADM-007: deactivate, then reactivate")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_paused")
        account, user_id = member.account, member.account.user_id
        _, _, version = await _lane_user(user_id)

        off = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_active": False})
        assert off.status_code == 200, f"PATCH {{is_active: false}}: expected 200, got {off.status_code} {off.text}"
        violations = _user_item_violations(off.json(), account, active=False, superuser=False)
        old_cookie_while_off = await _live_me(member.cookie)
        login_while_off = await _live_login(account)
        state_while_off = await _lane_user(user_id)
        on = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_active": True})

        _expect(violations, old_cookie_while_off[0] == 401, f"a deactivated account's cookie must be refused: GET /auth/me {old_cookie_while_off}")
        _expect(violations, _refusal(login_while_off) == (403, "ACCOUNT_DISABLED"), f"the right password of a deactivated account: expected 403 ACCOUNT_DISABLED, got {login_while_off.status_code} {login_while_off.text}")
        _expect(violations, state_while_off == (False, False, version + 1), f"deactivation must end the sessions, version + 1: {state_while_off}, version before {version}")
        assert on.status_code == 200, f"PATCH {{is_active: true}}: expected 200, got {on.status_code} {on.text}" + (" — the lane's server runs with LIBREFOLIO_MAX_USERS, which no unit may set" if _refusal(on) == (409, "USER_LIMIT_REACHED") else "")
        violations += _user_item_violations(on.json(), account, active=True, superuser=False)
        _expect(violations, await _live_me(member.cookie) == SESSION_EXPIRED, f"reactivation must not bring the old session back: GET /auth/me {await _live_me(member.cookie)}")
        _expect(violations, await _lane_user(user_id) == (True, False, version + 1), f"reactivation must not move the version: {await _lane_user(user_id)}")
        _expect(violations, await _live_me_id(await _live_sign_in(account)) == user_id, "a new login after the reactivation must work")
        assert not violations, f"Deactivation and reactivation broke their contract:{_verdict(violations)}"
        print_success("deactivated: sessions ended, login refused; reactivated: old cookie still refused, new login works")

    @pytest.mark.asyncio
    async def test_promotion_keeps_the_session_and_demotion_ends_it(self, lane: _LaneRows) -> None:
        """UADM-008: PATCH {is_superuser: true} → 200; the same cookie now reaches GET /users, the version unchanged. PATCH {is_superuser: false} → 200; that cookie is refused (401 «Session expired or invalid»), the version rose by one, and a new login gets 403 from GET /users."""
        print_section("UADM-008: promote, then demote")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_promoted")
        account, user_id = member.account, member.account.user_id
        _, _, version = await _lane_user(user_id)
        before = await _live("GET", "/users", cookie=member.cookie)

        up = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_superuser": True})
        assert up.status_code == 200, f"PATCH {{is_superuser: true}}: expected 200, got {up.status_code} {up.text}"
        violations = _user_item_violations(up.json(), account, active=True, superuser=True)
        promoted = await _live("GET", "/users", cookie=member.cookie)
        state_promoted = await _lane_user(user_id)
        down = await _live("PATCH", f"/users/{user_id}", cookie=admin.cookie, json={"is_superuser": False})

        _expect(violations, before.status_code == 403, f"Precondition: an ordinary account gets 403 from GET /users, got {before.status_code}")
        _expect(violations, promoted.status_code == 200, f"promotion ends no session: the same cookie must now reach GET /users, got {promoted.status_code} {promoted.text}")
        _expect(violations, state_promoted == (True, True, version), f"promotion must not move the version: {state_promoted}, before {version}")
        assert down.status_code == 200, f"PATCH {{is_superuser: false}}: expected 200, got {down.status_code} {down.text}"
        violations += _user_item_violations(down.json(), account, active=True, superuser=False)
        _expect(violations, await _live_me(member.cookie) == SESSION_EXPIRED, f"demotion must end the sessions: GET /auth/me {await _live_me(member.cookie)}")
        _expect(violations, await _lane_user(user_id) == (True, False, version + 1), f"demotion: version + 1: {await _lane_user(user_id)}")
        fresh = await _live_sign_in(account)
        _expect(violations, (await _live("GET", "/users", cookie=fresh)).status_code == 403, "after the demotion a new login must be an ordinary account again (403 from GET /users)")
        assert not violations, f"Promotion and demotion broke their contract:{_verdict(violations)}"
        print_success("promoted: same session, admin routes open; demoted: session ended, routes closed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("method", "suffix", "body", "success"), UNKNOWN_ACCOUNT_ROUTES)
    async def test_an_account_that_does_not_exist_is_404(self, lane: _LaneRows, method: str, suffix: str, body: Any, success: int) -> None:
        """UADM-009: the id of an account this case created and deleted (ids of users are never reused: AUTOINCREMENT) → 404.

        Presence barrier first: the same call on an existing account of this case gets the route's success status. A route
        that does not exist answers 404 too.
        """
        print_section(f"UADM-009: {method} /users/{{gone}}{suffix}")
        admin = await _live_admin(lane)
        present = await _live_register(lane, "uadm_present")
        barrier = await _live(method, f"/users/{present.user_id}{suffix}", cookie=admin.cookie, json=body)
        assert barrier.status_code == success, f"Presence barrier: {method} /users/{{id}}{suffix} on an existing account must answer {success}, or the 404 below proves nothing: {barrier.status_code} {barrier.text}"
        gone = await _live_register(lane, "uadm_gone")
        async with AsyncSession(_lane_engine()) as session:
            assert await user_service.delete_user(session, gone.user_id) is not None, f"Setup: {gone.username} must be deleted"

        response = await _live(method, f"/users/{gone.user_id}{suffix}", cookie=admin.cookie, json=body)

        assert response.status_code == 404, f"{method} /users/{gone.user_id}{suffix} of a deleted account: expected 404, got {response.status_code} {response.text}"
        print_success("404")


# ============================================================================
# LANE: RESET LINKS, SESSIONS, ONBOARDING
# ============================================================================


class TestResetLinksOnTheLane:
    @pytest.mark.asyncio
    async def test_a_reset_link_works_once(self, lane: _LaneRows) -> None:
        """UADM-010: POST /users/{id}/password-reset-link → 201 {token, path, url, expires_at}, the stored hash of a reset link of that account; POST /auth/password-reset with it → 200, the new password signs in and the old one no longer does; the same link again → 400 TOKEN_INVALID, and the password stays."""
        print_section("UADM-010: a reset link, once")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_forgetful")

        created = await _live("POST", f"/users/{holder.user_id}/password-reset-link", cookie=admin.cookie)

        assert created.status_code == 201, f"POST /users/{{id}}/password-reset-link: expected 201, got {created.status_code} {created.text}"
        link = created.json()
        violations = _reset_link_violations(link)
        assert not violations, f"the 201 breaks its contract:{_verdict(violations)}"
        _expect(violations, link["url"] is None or link["url"].endswith(link["path"]), f"url must be null or end with the path: {link}")
        row = await _lane_token_of(link["token"])
        _expect(violations, row is not None and (row.purpose, row.user_id, row.consumed_at, row.revoked_at) == (PASSWORD_RESET.value, holder.user_id, None, None), f"the token must be the stored hash of a live reset link of {holder.username}: {row}")
        used = await _live_reset_password(link["token"], NEW_PASSWORD)
        _expect(violations, used.status_code == 200, f"POST /auth/password-reset: expected 200, got {used.status_code} {used.text}")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "the new password must sign in")
        _expect(violations, (await _live_login(holder)).status_code == 401, "the old password must no longer sign in")
        reused = await _live_reset_password(link["token"], THIRD_PASSWORD)
        _expect(violations, _refusal(reused) == (400, "TOKEN_INVALID"), f"a used link: expected 400 TOKEN_INVALID, got {reused.status_code} {reused.text}")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "a refused second use must leave the password as it was")
        assert not violations, f"A reset link must work once:{_verdict(violations)}"
        print_success("201, used once, refused the second time")

    @pytest.mark.asyncio
    async def test_a_new_link_revokes_the_accounts_earlier_links_and_only_those(self, lane: _LaneRows) -> None:
        """UADM-011: a link for a bystander, then two for the holder: the holder's first is revoked (400 TOKEN_INVALID, the password unchanged), the second works; the bystander's link was not revoked and works."""
        print_section("UADM-011: a new link revokes the account's earlier ones, only those")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_reset_holder")
        bystander = await _live_register(lane, "uadm_reset_bystander")
        theirs = await _admin_reset_link(admin, bystander.user_id)
        first = await _admin_reset_link(admin, holder.user_id)
        second = await _admin_reset_link(admin, holder.user_id)

        violations: list[str] = []
        first_row, their_row = await _lane_token_of(first), await _lane_token_of(theirs)
        _expect(violations, first_row is not None and first_row.revoked_at is not None, f"the holder's earlier link must be revoked by the new one: {first_row}")
        _expect(violations, their_row is not None and their_row.revoked_at is None, f"another account's link must not be revoked: {their_row}")
        used_first = await _live_reset_password(first, NEW_PASSWORD)
        _expect(violations, _refusal(used_first) == (400, "TOKEN_INVALID"), f"the revoked link: expected 400 TOKEN_INVALID, got {used_first.status_code} {used_first.text}")
        _expect(violations, (await _live_login(holder)).status_code == 200, "a refused link must leave the password as it was")
        _expect(violations, (await _live_reset_password(second, NEW_PASSWORD)).status_code == 200, "the newest link must work")
        _expect(violations, (await _live_login(holder, NEW_PASSWORD)).status_code == 200, "the newest link must set the password")
        _expect(violations, (await _live_reset_password(theirs, NEW_PASSWORD)).status_code == 200, "the bystander's link must still work")
        _expect(violations, (await _live_login(bystander, NEW_PASSWORD)).status_code == 200, "the bystander's link must set the bystander's password")
        assert not violations, f"Only the newest link of an account may work, and only that account's are revoked:{_verdict(violations)}"
        print_success("earlier link revoked, newest works, the bystander's untouched")


class TestSessionsAndOnboardingOnTheLane:
    @pytest.mark.asyncio
    async def test_sessions_revoke_ends_every_session_of_the_account_and_no_other(self, lane: _LaneRows) -> None:
        """UADM-012: POST /users/{id}/sessions/revoke → 204 with no body; both devices of the account get 401 «Session expired or invalid», its version rose by one, it stays active and can sign in again; another account's session and version do not move."""
        print_section("UADM-012: sessions revoke")
        admin = await _live_admin(lane)
        holder = await _live_register(lane, "uadm_signed_out")
        bystander = await _live_member(lane, "uadm_signed_in")
        device_a, device_b = await _live_sign_in(holder), await _live_sign_in(holder)
        holder_before, bystander_before = await _lane_user(holder.user_id), await _lane_user(bystander.account.user_id)

        response = await _live("POST", f"/users/{holder.user_id}/sessions/revoke", cookie=admin.cookie)

        violations: list[str] = []
        _expect(violations, (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}")
        for label, cookie in (("device A", device_a), ("device B", device_b)):
            _expect(violations, await _live_me(cookie) == SESSION_EXPIRED, f"{label} of the account must be refused with {SESSION_EXPIRED}: {await _live_me(cookie)}")
        _expect(violations, await _lane_user(holder.user_id) == (holder_before[0], holder_before[1], holder_before[2] + 1), f"the account's version must rise by one, nothing else: {holder_before} → {await _lane_user(holder.user_id)}")
        _expect(violations, await _live_me_id(bystander.cookie) == bystander.account.user_id, "another account's session must not notice")
        _expect(violations, await _lane_user(bystander.account.user_id) == bystander_before, "another account's version must not move")
        _expect(violations, await _live_me_id(await _live_sign_in(holder)) == holder.user_id, "the account must be able to sign in again")
        assert not violations, f"POST /users/{{id}}/sessions/revoke broke its contract:{_verdict(violations)}"
        print_success("204: both devices out, the bystander in, a new login works")

    @pytest.mark.asyncio
    async def test_onboarding_reset_puts_every_flow_and_step_back_to_pending(self, lane: _LaneRows) -> None:
        """UADM-013: an account completed intro_tour and import_guide (with its steps), skipped fx_guide and one step of transaction_bulk_guide; POST /users/{id}/onboarding/reset {} → 204, and the account, signing in again, reads every flow and every step pending."""
        print_section("UADM-013: onboarding reset, every flow")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_onboarded")
        bulk_step = STEP_FLOWS[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][0]
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.FX_GUIDE, "skip")
        await _live_onboarding_move(member.cookie, OnboardingFlow.IMPORT_GUIDE, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.TRANSACTION_BULK_GUIDE, "skip", step=bulk_step)
        before = await _live_onboarding(member.cookie)
        assert before[OnboardingFlow.INTRO_TOUR.value][0] == "completed" and before[OnboardingFlow.FX_GUIDE.value][0] == "skipped", f"Precondition: {before}"
        assert before[OnboardingFlow.IMPORT_GUIDE.value][1] and set(before[OnboardingFlow.IMPORT_GUIDE.value][1].values()) == {"completed"}, f"Precondition: {before}"
        assert before[OnboardingFlow.TRANSACTION_BULK_GUIDE.value][1][bulk_step] == "skipped", f"Precondition: {before}"

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={})

        assert (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}"
        after = await _live_onboarding(await _live_sign_in(member.account))
        expected = {flow.value: _pending(flow.value) for flow in ONBOARDING_FLOW_VERSIONS}
        assert after == expected, f"every flow and step must be back to pending: {after}"
        print_success("every flow and every step pending")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("flow", [OnboardingFlow.INTRO_TOUR.value, OnboardingFlow.IMPORT_GUIDE.value])
    async def test_onboarding_reset_of_one_flow_leaves_the_others_as_they_were(self, lane: _LaneRows, flow: str) -> None:
        """UADM-014: intro_tour and import_guide completed, fx_guide skipped; {flow} → 204, that flow (with its steps, when it has any) back to pending, every other flow as it was."""
        print_section(f"UADM-014: onboarding reset of {flow}")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_one_flow")
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.IMPORT_GUIDE, "complete")
        await _live_onboarding_move(member.cookie, OnboardingFlow.FX_GUIDE, "skip")
        before = await _live_onboarding(member.cookie)
        assert before[flow][0] == "completed", f"Precondition: {flow} completed: {before}"

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={"flow": flow})

        assert (response.status_code, response.content) == (204, b""), f"expected 204 with no body, got {response.status_code} {response.text}"
        after = await _live_onboarding(await _live_sign_in(member.account))
        assert after == {**before, flow: _pending(flow)}, f"only {flow} must be back to pending: before {before}, after {after}"
        print_success(f"{flow} pending, the others untouched")

    @pytest.mark.asyncio
    async def test_onboarding_reset_of_an_unknown_flow_is_refused_and_resets_nothing(self, lane: _LaneRows) -> None:
        """UADM-015: {flow: "no_such_flow"} → 422, and the account's onboarding is as it was."""
        print_section("UADM-015: onboarding reset of an unknown flow")
        admin = await _live_admin(lane)
        member = await _live_member(lane, "uadm_unknown_flow")
        await _live_onboarding_move(member.cookie, OnboardingFlow.INTRO_TOUR, "complete")
        before = await _live_onboarding(member.cookie)

        response = await _live("POST", f"/users/{member.account.user_id}/onboarding/reset", cookie=admin.cookie, json={"flow": "no_such_flow"})

        assert response.status_code == 422, f"an unknown flow: expected 422, got {response.status_code} {response.text}"
        assert await _live_onboarding(await _live_sign_in(member.account)) == before, "a refused reset must reset nothing"
        print_success("422, nothing reset")


# ============================================================================
# THE PRIVATE INSTANCE: THE REAL ROUTERS ON A DATABASE OF THIS TEST
# ============================================================================


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the routers of auth, users and settings, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _private_app(engine: AsyncEngine) -> FastAPI:
    """The real routers, mounted under the API prefix as ``api/v1/router.py`` mounts them; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    for router in (auth_api.router, users_api.router, settings_api.router):
        app.include_router(router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with; no accounts variable; bcrypt at cost 4. Disposed at teardown."""
    for name in ACCOUNTS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'instance.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_private_app(engine))
    finally:
        await engine.dispose()


async def _call(private: _Private, method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request to the private instance, from a client of its own: no cookie jar, the session (if any) sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=private.app), base_url="http://test", timeout=TIMEOUT) as client:
        return await client.request(method, f"{API_V1_PREFIX}{path}", json=json, headers=headers)


async def _add_user(private: _Private, username: str, *, admin: bool = False, active: bool = True) -> _Account:
    """An account written as a row, with a real bcrypt hash of PRIVATE_PASSWORD (cost 4), so that it can sign in."""
    email = f"{username}@example.com"
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(PRIVATE_PASSWORD), is_active=active, is_superuser=admin)
        session.add(user)
        await session.commit()
    return _Account(user_id=user.id, username=username, email=email, password=PRIVATE_PASSWORD)


async def _sign_in(private: _Private, account: _Account) -> str:
    """A session of ``account`` on the private instance, through its POST /auth/login."""
    response = await _call(private, "POST", "/auth/login", json={"username": account.username, "password": account.password})
    cookie = _session_cookie(response)
    assert response.status_code == 200 and cookie, f"Setup: {account.username} could not sign in to the private instance: {response.status_code} {response.text}"
    return cookie


async def _admin(private: _Private, username: str = "root") -> tuple[_Account, str]:
    """An active administrator of the private instance, signed in."""
    account = await _add_user(private, username, admin=True)
    return account, await _sign_in(private, account)


async def _private_user(private: _Private, user_id: int) -> tuple[bool, bool, int]:
    """(is_active, is_superuser, session_version) of an account, read fresh."""
    async with AsyncSession(private.engine) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.session_version).where(User.id == user_id))).one()
    return bool(row[0]), bool(row[1]), int(row[2])


async def _private_issue(private: _Private, purpose: AccountTokenPurpose = INVITE, **arguments: Any) -> IssuedToken:
    """A token issued by token_service directly, committed."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _private_consume(private: _Private, token: str, consumed_by_user_id: int) -> None:
    async with AsyncSession(private.engine) as session:
        record = await consume_token(session, token, INVITE, consumed_by_user_id=consumed_by_user_id)
        await session.commit()
    assert record is not None, "Setup: the invitation must be consumed"


async def _private_tokens(private: _Private) -> list[AccountToken]:
    """Every token row of the private instance: this test owns them all."""
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        return list((await session.execute(select(AccountToken).order_by(AccountToken.id))).scalars().all())


async def _private_token_columns(private: _Private) -> list[dict[str, Any]]:
    """Every token row of the private instance as its raw column values, read from the table without the model: what the database holds."""
    async with AsyncSession(private.engine) as session:
        return [dict(row) for row in (await session.execute(select(AccountToken.__table__))).mappings().all()]


async def _invitation_count(private: _Private) -> int:
    return sum(1 for row in await _private_tokens(private) if row.purpose == INVITE.value)


async def _set_mode_row(private: _Private, mode: str) -> None:
    """The ``registration_mode`` row says ``mode``: the seeded row updated, or created when missing."""
    async with AsyncSession(private.engine) as session:
        row = await session.get(GlobalSetting, MODE_KEY)
        if row is None:
            row = GlobalSetting(key=MODE_KEY, value=mode, value_type="string", updated_at=utcnow())
        row.value = mode
        session.add(row)
        await session.commit()


# ============================================================================
# IN-PROCESS: THE LAST ACTIVE ADMINISTRATOR
# ============================================================================


class TestLastActiveAdministrator:
    """«The last active administrator» depends on every account of the instance: a real state only on a private one."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("change", [pytest.param({"is_active": False}, id="deactivate"), pytest.param({"is_superuser": False}, id="demote")])
    async def test_the_last_active_administrator_is_neither_deactivated_nor_demoted(self, private: _Private, change: dict[str, bool]) -> None:
        """UADM-020: root is the only active administrator (another administrator exists, inactive: it does not count); PATCH /users/{root} with the change → 409 LAST_ADMIN; root is as it was, version included, and its session still works."""
        print_section(f"UADM-020: {change} on the last active administrator")
        root, cookie = await _admin(private)
        dormant = await _add_user(private, "dormant", admin=True, active=False)
        await _add_user(private, "member")
        before = await _private_user(private, root.user_id)

        response = await _call(private, "PATCH", f"/users/{root.user_id}", cookie=cookie, json=change)

        violations: list[str] = []
        _expect(violations, _refusal(response) == (409, "LAST_ADMIN"), f"expected 409 LAST_ADMIN, got {response.status_code} {response.text}")
        _expect(violations, await _private_user(private, root.user_id) == before, f"a refused change must change nothing, the version included: {before} → {await _private_user(private, root.user_id)}")
        _expect(violations, (await _call(private, "GET", "/users", cookie=cookie)).status_code == 200, "a refused change must end no session: root must still be signed in as an administrator")
        _expect(violations, await _private_user(private, dormant.user_id) == (False, True, 0), "the inactive administrator must be untouched")
        assert not violations, f"The last active administrator must stay:{_verdict(violations)}"
        print_success("409 LAST_ADMIN, nothing changed")

    @pytest.mark.asyncio
    async def test_the_guard_follows_the_active_administrators(self, private: _Private) -> None:
        """UADM-021: root is the only active administrator. Demoting the inactive administrator → 200 (it removes no active one); promoting the member → 200; deactivating root → 200, the member remains; the member, now the last active administrator, demoting itself → 409 LAST_ADMIN."""
        print_section("UADM-021: the guard counts the active administrators")
        root, cookie = await _admin(private)
        dormant = await _add_user(private, "dormant", admin=True, active=False)
        member = await _add_user(private, "member")

        steps = {
            "demote the inactive administrator": (await _call(private, "PATCH", f"/users/{dormant.user_id}", cookie=cookie, json={"is_superuser": False})).status_code,
            "promote the member": (await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})).status_code,
            "deactivate root while the member is an active administrator": (await _call(private, "PATCH", f"/users/{root.user_id}", cookie=cookie, json={"is_active": False})).status_code,
        }
        last = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=await _sign_in(private, member), json={"is_superuser": False})

        flags = {name: (await _private_user(private, account.user_id))[:2] for name, account in (("root", root), ("dormant", dormant), ("member", member))}
        violations: list[str] = []
        _expect(violations, steps == dict.fromkeys(steps, 200), f"each step must be allowed: {steps}")
        _expect(violations, _refusal(last) == (409, "LAST_ADMIN"), f"the member is now the last active administrator: expected 409 LAST_ADMIN, got {last.status_code} {last.text}")
        _expect(violations, flags == {"root": (False, True), "dormant": (False, False), "member": (True, True)}, f"(is_active, is_superuser) afterwards: {flags}")
        assert not violations, f"The guard must count the active administrators, and only them:{_verdict(violations)}"
        print_success("allowed while another active administrator remains, refused for the last one")


# ============================================================================
# IN-PROCESS: THE USER LIMIT AND THE REGISTRATION MODE
# ============================================================================


REACTIVATION_CASES = [
    pytest.param("2", 0, True, id="at-the-limit"),
    pytest.param("3", 1, True, id="an-invitation-holds-the-last-seat"),
    pytest.param("3", 0, False, id="a-seat-left"),
]

INVITATION_LIMIT_CASES = [
    pytest.param("2", 0, BILLING_LINK, (409, 2, 2), id="at-the-limit"),
    pytest.param("1", 0, BILLING_LINK, (409, 1, 2), id="over-the-limit"),
    pytest.param("3", 1, None, (409, 3, 3), id="invitations-hold-the-seats"),
    pytest.param("not-a-number", 0, None, (409, 0, 2), id="an-invalid-limit-closes"),
    pytest.param("3", 0, BILLING_LINK, (201, None, None), id="a-seat-left"),
]

MODE_CASES = [
    pytest.param("open", "row", 201, id="open-by-the-row"),
    pytest.param("invite", "row", 201, id="invite-by-the-row"),
    pytest.param("disabled", "row", 409, id="disabled-by-the-row"),
    pytest.param("open", "variable", 201, id="open-by-the-variable"),
    pytest.param("invite", "variable", 201, id="invite-by-the-variable"),
    pytest.param("disabled", "variable", 409, id="disabled-by-the-variable"),
]


class TestUserLimitAndRegistrationMode:
    """LIBREFOLIO_MAX_USERS, LIBREFOLIO_BILLING_URL, LIBREFOLIO_REGISTRATION and the registration_mode row, on a private instance. Every instance has root (an active administrator) and a member (active): two seats used; an inactive account takes none."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("max_users", "live_invitations", "refused"), REACTIVATION_CASES)
    async def test_a_reactivation_over_the_limit_is_refused_with_the_counts(self, private: _Private, monkeypatch: pytest.MonkeyPatch, max_users: str, live_invitations: int, refused: bool) -> None:
        """UADM-022: PATCH {is_active: true} of an inactive account with no seat left (the live invitations hold seats) → 409 USER_LIMIT_REACHED with limit, used and billing_url, and the account stays inactive; with a seat left → 200, active."""
        print_section(f"UADM-022: reactivation, LIBREFOLIO_MAX_USERS={max_users}, {live_invitations} live invitation(s)")
        root, cookie = await _admin(private)
        await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        for _ in range(live_invitations):
            await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, max_users)
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        response = await _call(private, "PATCH", f"/users/{dormant.user_id}", cookie=cookie, json={"is_active": True})

        is_active = (await _private_user(private, dormant.user_id))[0]
        if refused:
            expected = {"error_code": "USER_LIMIT_REACHED", "limit": int(max_users), "used": 2 + live_invitations, "billing_url": BILLING_LINK}
            assert (response.status_code, _counts(response)) == (409, expected), f"expected 409 with {expected}, got {response.status_code} {response.text}"
            assert is_active is False, "a refused reactivation must leave the account inactive"
        else:
            assert (response.status_code, is_active) == (200, True), f"with a seat left the reactivation goes through: {response.status_code} {response.text}, is_active={is_active}"
        print_success(f"{response.status_code}")

    @pytest.mark.asyncio
    async def test_the_limit_blocks_neither_a_promotion_nor_a_deactivation(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-023: two seats used, LIBREFOLIO_MAX_USERS=1 (over the limit): promoting the member → 200, then deactivating it → 200."""
        print_section("UADM-023: over the limit, promotion and deactivation still go through")
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        monkeypatch.setenv(MAX_USERS_VARIABLE, "1")

        promote = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_superuser": True})
        deactivate = await _call(private, "PATCH", f"/users/{member.user_id}", cookie=cookie, json={"is_active": False})

        assert (promote.status_code, deactivate.status_code) == (200, 200), f"the limit blocks invitations, open registration and reactivations only: promote {promote.status_code} {promote.text}, deactivate {deactivate.status_code} {deactivate.text}"
        assert (await _private_user(private, member.user_id))[:2] == (False, True), "the member must end up an inactive administrator"
        print_success("200, 200")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("max_users", "live_invitations", "billing", "outcome"), INVITATION_LIMIT_CASES)
    async def test_an_invitation_at_the_limit_is_refused_with_the_counts_and_the_billing_link(self, private: _Private, monkeypatch: pytest.MonkeyPatch, max_users: str, live_invitations: int, billing: Optional[str], outcome: tuple[int, Optional[int], Optional[int]]) -> None:
        """UADM-024: POST /users/invites with no seat left (an invalid LIBREFOLIO_MAX_USERS closes: limit 0) → 409 USER_LIMIT_REACHED with limit, used and billing_url (null without LIBREFOLIO_BILLING_URL), and no invitation issued; with a seat left → 201."""
        print_section(f"UADM-024: an invitation, LIBREFOLIO_MAX_USERS={max_users}, {live_invitations} live invitation(s)")
        root, cookie = await _admin(private)
        await _add_user(private, "member")
        await _add_user(private, "dormant", active=False)
        for _ in range(live_invitations):
            await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, max_users)
        if billing:
            monkeypatch.setenv(BILLING_URL_VARIABLE, billing)
        before = await _invitation_count(private)

        response = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": False})

        status, limit, used = outcome
        issued = await _invitation_count(private) - before
        if status == 201:
            assert (response.status_code, issued) == (201, 1), f"with a seat left the invitation is issued: {response.status_code} {response.text}, {issued} issued"
            return
        expected = {"error_code": "USER_LIMIT_REACHED", "limit": limit, "used": used, "billing_url": billing}
        assert (response.status_code, _counts(response)) == (409, expected), f"expected 409 with {expected}, got {response.status_code} {response.text}"
        assert issued == 0, f"a refused invitation must issue nothing: {issued} issued"
        print_success(f"409 with {expected}")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("mode", "source", "status"), MODE_CASES)
    async def test_an_invitation_is_refused_while_registration_is_disabled(self, private: _Private, monkeypatch: pytest.MonkeyPatch, mode: str, source: str, status: int) -> None:
        """UADM-025: registration disabled — by the row, or by LIBREFOLIO_REGISTRATION over a row that says open — → POST /users/invites 409 REGISTRATION_DISABLED and nothing issued; open or invite (the variable over a disabled row too) → 201."""
        print_section(f"UADM-025: an invitation while registration is {mode}, by the {source}")
        _, cookie = await _admin(private)
        if source == "row":
            await _set_mode_row(private, mode)
        else:
            await _set_mode_row(private, "open" if mode == "disabled" else "disabled")
            monkeypatch.setenv(REGISTRATION_VARIABLE, mode)
        before = await _invitation_count(private)

        response = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": True})

        expected = (201, None) if status == 201 else (409, "REGISTRATION_DISABLED")
        assert _refusal(response) == expected, f"registration {mode} by the {source}: expected {expected}, got {response.status_code} {response.text}"
        assert await _invitation_count(private) - before == (1 if status == 201 else 0), "a refused invitation must issue nothing, an accepted one exactly one"
        print_success(f"{expected}")


# ============================================================================
# IN-PROCESS: LINKS, LIFETIMES, WHAT IS LISTED AND COUNTED
# ============================================================================


class TestLinksAndInvitationsInProcess:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("public_url", [pytest.param(None, id="without-a-public-url"), pytest.param(PUBLIC_URL, id="with-a-public-url")])
    async def test_links_carry_the_public_url_when_it_is_set(self, private: _Private, monkeypatch: pytest.MonkeyPatch, public_url: Optional[str]) -> None:
        """UADM-026: the 201 of an invitation and of a reset link: ``path`` is the page with the token, ``url`` is LIBREFOLIO_PUBLIC_URL without its trailing slash plus the path, or null without the variable."""
        print_section(f"UADM-026: links, LIBREFOLIO_PUBLIC_URL={public_url}")
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        if public_url:
            monkeypatch.setenv(PUBLIC_URL_VARIABLE, public_url)

        invitation = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        link = await _call(private, "POST", f"/users/{member.user_id}/password-reset-link", cookie=cookie)

        assert (invitation.status_code, link.status_code) == (201, 201), f"invitation {invitation.status_code} {invitation.text}; reset link {link.status_code} {link.text}"
        origin = PUBLIC_ORIGIN if public_url else None
        violations: list[str] = []
        for label, body, purpose in (("invitation", invitation.json(), INVITE), ("reset link", link.json(), PASSWORD_RESET)):
            violations += [f"{label}: {problem}" for problem in _link_path_violations(body.get("path"), purpose, str(body.get("token")))]
            violations += [f"{label}: {problem}" for problem in _url_violations(body, origin)]
        assert not violations, f"The links must follow LIBREFOLIO_PUBLIC_URL:{_verdict(violations)}"
        print_success(f"url {'built on the public URL' if public_url else 'null'}")

    @pytest.mark.asyncio
    async def test_an_invitation_lives_seven_days_a_reset_link_thirty_minutes_and_only_hashes_are_stored(self, private: _Private) -> None:
        """UADM-027: the invitation is created now and lives 7 days, as asked (admin role, e-mail, its issuer); the reset link expires 30 minutes after it was asked for; each row holds the token's SHA-256, of its purpose and owner, and no column of any token row holds a plaintext."""
        print_section("UADM-027: lifetimes and hashes")
        root, cookie = await _admin(private)
        member = await _add_user(private, "member")

        started = utcnow()
        invitation = await _call(private, "POST", "/users/invites", cookie=cookie, json={"grants_admin": True, "email": "guest@example.com"})
        link = await _call(private, "POST", f"/users/{member.user_id}/password-reset-link", cookie=cookie)
        finished = utcnow()

        assert (invitation.status_code, link.status_code) == (201, 201), f"invitation {invitation.status_code} {invitation.text}; reset link {link.status_code} {link.text}"
        issued, reset = invitation.json(), link.json()
        violations = _issued_invite_violations(issued, grants_admin=True, email="guest@example.com", created_by=root.user_id) + _reset_link_violations(reset)
        assert not violations, f"the 201 bodies break their contract:{_verdict(violations)}"
        created, expires = _instant(issued["invite"]["created_at"]), _instant(reset["expires_at"])
        ttl = DEFAULT_TTL[PASSWORD_RESET]
        _expect(violations, created is not None and started <= created <= finished, f"the invitation must be created now, between {started} and {finished}: {created}")
        _expect(violations, expires is not None and started + ttl <= expires <= finished + ttl, f"the reset link must expire {ttl} after it was asked for, between {started + ttl} and {finished + ttl}: {expires}")
        rows = {row.token_hash: row for row in await _private_tokens(private)}
        invite_row, reset_row = rows.get(hash_token(issued["token"])), rows.get(hash_token(reset["token"]))
        _expect(violations, invite_row is not None and (invite_row.id, invite_row.purpose, invite_row.user_id) == (issued["invite"]["id"], INVITE.value, None), f"the invitation's row must hold its hash: {invite_row}")
        _expect(violations, reset_row is not None and (reset_row.purpose, reset_row.user_id) == (PASSWORD_RESET.value, member.user_id), f"the reset link's row must hold its hash, for the member: {reset_row}")
        stored = [f"{row['id']}.{column}" for row in await _private_token_columns(private) for column, value in row.items() if any(secret in str(value) for secret in (issued["token"], reset["token"]))]
        _expect(violations, stored == [], f"a plaintext token is stored in {stored}")
        assert not violations, f"Lifetimes and storage broke their contract:{_verdict(violations)}"
        print_success("7 days, 30 minutes, hashes only")

    @pytest.mark.asyncio
    async def test_only_live_invitations_are_listed_and_counted_and_every_account_is_listed(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """UADM-028: two administrators, a member, an inactive account; invitations live (one from the API, one by the other administrator), revoked, consumed and expired, and a reset link. GET /users/invites lists exactly the two live ones; GET /users exactly the four accounts with their flags; both say usage {used: 3 active + 2 live = 5, max_users: 10, billing_url}; without the variables {used: 5, max_users: null, billing_url: null}."""
        print_section("UADM-028: what is listed and what is counted")
        root, cookie = await _admin(private)
        other = await _add_user(private, "other_admin", admin=True)
        member = await _add_user(private, "member")
        dormant = await _add_user(private, "dormant", active=False)
        live = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        revoked = await _call(private, "POST", "/users/invites", cookie=cookie, json={})
        assert (live.status_code, revoked.status_code) == (201, 201), f"Setup: {live.status_code} {live.text}; {revoked.status_code} {revoked.text}"
        assert (await _call(private, "DELETE", f"/users/invites/{revoked.json()['invite']['id']}", cookie=cookie)).status_code == 204, "Setup: revoke"
        live_by_other = await _private_issue(private, INVITE, created_by_user_id=other.user_id)
        consumed = await _private_issue(private, INVITE, created_by_user_id=other.user_id)
        await _private_consume(private, consumed.token, member.user_id)
        await _private_issue(private, INVITE, created_by_user_id=other.user_id, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(minutes=1))
        await _private_issue(private, PASSWORD_RESET, user_id=member.user_id)
        monkeypatch.setenv(MAX_USERS_VARIABLE, "10")
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        invitations = await _call(private, "GET", "/users/invites", cookie=cookie)
        accounts = await _call(private, "GET", "/users", cookie=cookie)
        monkeypatch.delenv(MAX_USERS_VARIABLE)
        monkeypatch.delenv(BILLING_URL_VARIABLE)
        unlimited = await _call(private, "GET", "/users/invites", cookie=cookie)

        assert (invitations.status_code, accounts.status_code, unlimited.status_code) == (200, 200, 200), f"{invitations.text}; {accounts.text}; {unlimited.text}"
        usage = {"used": 5, "max_users": 10, "billing_url": BILLING_LINK}
        violations: list[str] = []
        listed = sorted(item["id"] for item in invitations.json()["items"])
        _expect(violations, listed == sorted([live.json()["invite"]["id"], live_by_other.record.id]), f"GET /users/invites must list the two live invitations only, whoever issued them: {listed}")
        _expect(violations, invitations.json()["usage"] == usage, f"GET /users/invites usage: expected {usage}, got {invitations.json()['usage']}")
        items = {item["id"]: item for item in accounts.json()["items"]}
        _expect(violations, sorted(items) == sorted(account.user_id for account in (root, other, member, dormant)), f"GET /users must list every account, active or not: {sorted(items)}")
        for account, active, superuser in ((root, True, True), (other, True, True), (member, True, False), (dormant, False, False)):
            violations += _user_item_violations(items.get(account.user_id), account, active=active, superuser=superuser)
        _expect(violations, accounts.json()["usage"] == usage, f"GET /users usage: expected {usage}, got {accounts.json()['usage']}")
        _expect(violations, unlimited.json()["usage"] == {"used": 5, "max_users": None, "billing_url": None}, f"without the variables: {unlimited.json()['usage']}")
        assert not violations, f"Listing and usage broke their contract:{_verdict(violations)}"
        print_success("two live invitations listed, four accounts, used 5")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", ["expired", "never-issued"])
    async def test_an_expired_or_never_issued_invitation_cannot_be_revoked(self, private: _Private, kind: str) -> None:
        """UADM-029: DELETE /users/invites/{id} of an expired invitation, or of an id never issued → 404, and nothing else is revoked.

        Presence barrier first: a live invitation is revoked with 204. A route that does not exist answers 404 too.
        """
        print_section(f"UADM-029: DELETE an {kind} invitation")
        root, cookie = await _admin(private)
        live = await _private_issue(private, INVITE, created_by_user_id=root.user_id)
        barrier = await _call(private, "DELETE", f"/users/invites/{live.record.id}", cookie=cookie)
        assert barrier.status_code == 204, f"Presence barrier: DELETE of a live invitation must answer 204, or the 404 below proves nothing: {barrier.status_code} {barrier.text}"
        invite_id = NEVER_ISSUED_ID
        if kind == "expired":
            invite_id = (await _private_issue(private, INVITE, created_by_user_id=root.user_id, now=utcnow() - DEFAULT_TTL[INVITE] - timedelta(minutes=1))).record.id
        revoked_before = {row.id for row in await _private_tokens(private) if row.revoked_at is not None}

        response = await _call(private, "DELETE", f"/users/invites/{invite_id}", cookie=cookie)

        assert response.status_code == 404, f"an {kind} invitation is not live: expected 404, got {response.status_code} {response.text}"
        assert {row.id for row in await _private_tokens(private) if row.revoked_at is not None} == revoked_before, "a refused revocation must revoke nothing"
        print_success("404")


# ============================================================================
# IN-PROCESS: STRUCTURED LOGS, AND NO TOKEN IN THEM
# ============================================================================


#: The SQL loggers: they print every statement with its parameters, the stored token_hash included.
SQL_LOGGERS = frozenset({"aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool"})


def _warning_target(node: ast.AST) -> Optional[ast.expr]:
    """The argument of ``logging.getLogger(<argument>).setLevel(logging.WARNING)`` when ``node`` is that call; None otherwise."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "setLevel" and node.args):
        return None
    level, getter = node.args[0], node.func.value
    if not (isinstance(level, ast.Attribute) and level.attr == "WARNING" and isinstance(getter, ast.Call) and getter.args):
        return None
    return getter.args[0] if isinstance(getter.func, ast.Attribute) and getter.func.attr == "getLogger" else None


def _silenced_by_the_app() -> frozenset[str]:
    """The third-party loggers that ``configure_logging`` (``backend/app/logging_config.py``) sets to WARNING, read from its source so that this list cannot drift from it.

    Two forms: ``logging.getLogger("name").setLevel(logging.WARNING)``, and the same call on the variable of a ``for``
    loop over a literal tuple of names.
    """
    tree = ast.parse(textwrap.dedent(inspect.getsource(logging_config.configure_logging)))
    loops = {node.target.id: [item.value for item in node.iter.elts if isinstance(item, ast.Constant)] for node in ast.walk(tree) if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and isinstance(node.iter, (ast.Tuple, ast.List))}
    names: set[str] = set()
    for node in ast.walk(tree):
        target = _warning_target(node)
        if isinstance(target, ast.Constant) and isinstance(target.value, str):
            names.add(target.value)
        elif isinstance(target, ast.Name):
            names.update(str(name) for name in loops.get(target.id, ()))
    return frozenset(names)


def _is_silenced(logger_name: str, silenced: frozenset[str]) -> bool:
    """Whether a logger is one of ``silenced`` or a child of one: a child inherits the WARNING level."""
    return any(logger_name == name or logger_name.startswith(f"{name}.") for name in silenced)


def _carries(record: logging.LogRecord, secrets: list[str]) -> bool:
    """Whether a stdlib record shows one of ``secrets``, in its message or anywhere among its attributes."""
    shown = record.getMessage() + repr(vars(record))
    return any(secret in shown for secret in secrets)


class TestStructuredLogs:
    @pytest.mark.asyncio
    async def test_every_admin_action_writes_a_structured_event_and_no_log_carries_a_token(self, private: _Private, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
        """UADM-030: each admin action — an invitation issued and revoked, two reset links, deactivation, reactivation, promotion, demotion, sessions revoked, onboarding reset (all, then one flow) — emits at least one structlog event with a field besides its message. No structlog event and no stdlib record carries a token's plaintext (hence neither its path nor its URL), whatever the logger. No structlog event, and no record of the application's own loggers, carries its hash.

        The hash is the value of the ``token_hash`` column, so the SQL loggers print it among the parameters of the INSERT.
        ``configure_logging`` silences them to WARNING (``backend/app/logging_config.py``), so a running server never emits
        those records: caplog sees them only because it lowers the level. Their names are read from that function's source
        (``_silenced_by_the_app``), and a record of one of them or of a child is left out of the hash check only.

        Barriers first: a canary through the users module's logger name reaches both captures, or a capture that sees
        nothing would pass for endpoints that log nothing.
        """
        print_section("UADM-030: structured logs without tokens")
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
        _, cookie = await _admin(private)
        member = await _add_user(private, "member")
        monkeypatch.setattr(logging.getLogger(users_api.__name__), "disabled", False)
        caplog.set_level(logging.DEBUG)
        caplog.set_level(logging.DEBUG, logger=users_api.__name__)
        actions: dict[str, list[dict[str, Any]]] = {}
        bodies: list[Any] = []

        with capture_logs() as events:
            structlog.get_logger(users_api.__name__).info(CANARY)
            logging.getLogger(users_api.__name__).info(CANARY)

            async def act(label: str, method: str, path: str, body: Any = None, status: int = 200) -> Any:
                start = len(events)
                response = await _call(private, method, path, cookie=cookie, json=body)
                assert response.status_code == status, f"{label}: expected {status}, got {response.status_code} {response.text}"
                actions[label] = list(events[start:])
                bodies.append(response.json() if response.content else None)
                return bodies[-1]

            invitation = await act("issue an invitation", "POST", "/users/invites", {"grants_admin": True, "email": "guest@example.com"}, 201)
            await act("revoke the invitation", "DELETE", f"/users/invites/{invitation['invite']['id']}", None, 204)
            first = await act("issue a reset link", "POST", f"/users/{member.user_id}/password-reset-link", None, 201)
            second = await act("issue another reset link", "POST", f"/users/{member.user_id}/password-reset-link", None, 201)
            await act("deactivate", "PATCH", f"/users/{member.user_id}", {"is_active": False})
            await act("reactivate", "PATCH", f"/users/{member.user_id}", {"is_active": True})
            await act("promote", "PATCH", f"/users/{member.user_id}", {"is_superuser": True})
            await act("demote", "PATCH", f"/users/{member.user_id}", {"is_superuser": False})
            await act("revoke the sessions", "POST", f"/users/{member.user_id}/sessions/revoke", None, 204)
            await act("reset the onboarding", "POST", f"/users/{member.user_id}/onboarding/reset", {}, 204)
            await act("reset one flow", "POST", f"/users/{member.user_id}/onboarding/reset", {"flow": OnboardingFlow.INTRO_TOUR.value}, 204)
            reads = [await _call(private, "GET", path, cookie=cookie) for path in ("/users/invites", "/users")]

        assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the users module's logger do not reach capture_logs"
        assert any(record.getMessage() == CANARY for record in caplog.records), "barrier: stdlib records of the users module's logger do not reach caplog"
        assert [read.status_code for read in reads] == [200, 200], f"the reads inside the capture: {[read.text for read in reads]}"
        silenced = _silenced_by_the_app()
        assert SQL_LOGGERS <= silenced, f"premise: configure_logging silences the SQL loggers {sorted(SQL_LOGGERS)} to WARNING, as read from its source: {sorted(silenced)}"
        silent = [label for label, captured in actions.items() if not any(set(event) - {"event", "log_level"} for event in captured)]
        tokens = [invitation["token"], first["token"], second["token"]]
        hashes = [hash_token(token) for token in tokens]
        plaintext_events = [event for event in events if any(token in repr(event) for token in tokens)]
        plaintext_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if _carries(record, tokens)]
        hash_events = [event for event in events if any(digest in repr(event) for digest in hashes)]
        hash_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if not _is_silenced(record.name, silenced) and _carries(record, hashes)]
        violations: list[str] = []
        _expect(violations, silent == [], f"these actions wrote no structured event: {silent}")
        _expect(violations, plaintext_events == [], f"structlog events carrying a plaintext token: {plaintext_events}")
        _expect(violations, plaintext_records == [], f"stdlib records carrying a plaintext token, whatever the logger: {plaintext_records}")
        _expect(violations, hash_events == [], f"structlog events carrying a token's hash: {hash_events}")
        _expect(violations, hash_records == [], f"records of the application's loggers carrying a token's hash: {hash_records}")
        assert not violations, f"Every admin action logs, and no log carries a token:{_verdict(violations)}"
        print_success(f"{len(actions)} actions logged; {len(events)} events and {len(caplog.records)} records without a plaintext, no hash outside {sorted(SQL_LOGGERS)}")
