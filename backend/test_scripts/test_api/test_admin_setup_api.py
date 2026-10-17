"""
Admin setup API — release 1.3, workstream A, lot A7a (plan phase01Accounts §4.7 and A7, contract C3, the API part): F02,
the initial administrator, who activates the account through a single-use ``/setup`` link.

With F02 on, an empty instance starts with a pending administrator — an inactive superuser whose password is a random
secret nobody knows — and an ``admin_setup`` token valid 72 hours: the one the configuration gives, or one the instance
generates (``bootstrap_admin_service.run_admin_bootstrap``). Whoever holds the link chooses the password and is signed
in. The public endpoints of that, pinned here:

1. ``POST /auth/setup`` takes ``{token, new_password}``: the token 1 to 200 characters, the password at least one. A field
   missing, or out of those bounds, is a request validation error, 422.
2. The password rules come first (lot A6c, decision 37): a new password that misses one is 400 ``PASSWORD_TOO_WEAK``,
   ``detail: {error_code, message, rules}`` — ``rules`` the codes missed, in the policy's order —, before the token is
   read: with an unknown token too; and a valid token stays valid.
3. A token that is not a live ``admin_setup`` token — never issued, consumed, expired, revoked, an invitation, a
   password-reset link — is 400 ``TOKEN_INVALID``, ``detail: {error_code, message}``, and nothing changes: the account
   stays inactive, its password and session version as they were, every token as it was.
4. Night decision 6, to review: the live setup link of an account already active is 400 ``TOKEN_INVALID`` too, and that
   link is now revoked; the account keeps its password.
5. A live link: 200 with the body of ``POST /auth/login`` (``AuthLoginResponse``: ``user`` — the pending account, now
   active, an administrator —, ``user_settings``, ``message``, ``show_donation_popup``) and the login's session cookie,
   the same name with the same attributes: with it alone ``GET /auth/me`` answers that account. The link is consumed — it
   works once —, the account's other live setup links are revoked, and the new password signs in. The new password is
   hashed off the event loop (the plan's C3, as every new password).
6. ``POST /auth/tokens/inspect`` takes ``purpose: admin_setup``. A live setup link → ``{status: valid, purpose:
   admin_setup, expires_at, username}``: no ``email`` and no ``grants_admin`` — they are the invitation's, and the address
   of the pending administrator is not for whoever holds a link. Consumed, expired, revoked or unknown → that status and
   nothing more. A setup link asked as another purpose, and another purpose's link asked as a setup link, are ``unknown``.
7. Lot A7b-2 (A-32, decision N60): once the account is set up another way than its link — activated (the Users tab's
   ``PATCH``, ``./dev.py user activate``) or given a password (``./dev.py user reset``, a reset link spent, a change of
   its own password) —, its setup links are retired, revoked and consumed in the same transaction. The old link then
   inspects ``revoked``, and ``POST /auth/setup`` with it is 400 ``TOKEN_INVALID`` and changes nothing, the account
   inactive again too: whoever holds the link — it was in the log as well — no longer takes the account over. A
   reset link issued and not spent, or refused, retires nothing: the account still waits, and its link works.
8. Lot A-42 + A-43 (the setup link's lifecycle; contract approved by the coordinator, 17/10). Spending (A-42): the setup
   link of an account another setup link of which is already consumed — set up before, or its links retired — is
   refused, 400 ``TOKEN_INVALID``: nothing changes (the password, the active flag, the session version), and the
   account's never-consumed setup links are retired. Deactivation (A-43): ``./dev.py user deactivate`` on the pending
   administrator revokes its live setup links — its link inspects ``revoked``, ``POST /auth/setup`` with it is 400
   ``TOKEN_INVALID`` — and the account still waits: ``./dev.py user setup-link`` gives it a new link, which works.
   Demotion (A-43): ``./dev.py user demote`` refuses the pending administrator — falsy, a line starting with ❌,
   nothing changed —: its link still works, and sets up an administrator.

Coded refusals are read from ``detail.error_code``, the shape ``POST /auth/password-reset`` gives ``TOKEN_INVALID``; a
refusal sets no session cookie. Not here: ``/auth/setup`` on a blocked instance. It stays off the routes allowed while
blocked (decision P16(d)): a caller without a session gets the 401 of ``get_current_user``, as every public route
outside ``ALLOWED_WHEN_BLOCKED`` does; ``test_instance_block.py`` pins that list by name and by route, so adding the
setup to it would show there.

Where each case runs, and why. A pending administrator is a row of ``users``, an inactive superuser: in the lane's
database it would be one more administrator account for every concurrent unit to see, a setup would make it an active
one, and a run killed mid-test would leave it behind. So every case that needs one runs in-process: the real auth
router, mounted as ``api/v1/router.py`` mounts it, in an app of this test whose ``get_session_generator`` is a private
SQLite file under ``tmp_path``, seeded as a new install (the global settings, no account). There the pending
administrator is made by the bootstrap itself — ``run_admin_bootstrap`` on the empty instance, with a token the
configuration gives (``secrets.token_urlsafe(32)``), so that the test holds the link —, and the other tokens by the token
service; an expired one is issued 72 hours and one second ago, never waited for. The F02 variables
(``LIBREFOLIO_ADMIN_*``) and the accounts variables are removed from this process for the private instance: the
configuration is handed to the service, and without ``LIBREFOLIO_PUBLIC_URL`` no email leaves. On the lane's server run
only refusals that write nothing and the inspection of a token never issued: the unit writes nothing in the lane's
database. Lot A7b-2's cases run in-process too: the commands (``./dev.py user …``) as the calls they make
(``user_service``), and a reset link as ``POST /users/{id}/password-reset-link`` issues it
(``user_service.create_password_reset``) — the users router is not mounted here; ``test_users_admin_api.py`` issues it
through the route. Lot A-42/A-43's commands run as the commands themselves: ``scripts/user_cli.py``'s ``cmd_set_admin``,
``cmd_set_user_active`` and ``cmd_setup_link``, in-process, their ``get_async_engine`` the private file's (the
``commands`` fixture). Their contract is what the command answers and prints — a refused ``user demote`` is falsy and
prints a line starting with ❌ —, whichever layer holds the refusal, so the call it makes would not be enough.

bcrypt runs at its lowest cost in this process (``auth_service.BCRYPT_ROUNDS = 4``); the lane's server keeps its own.

What A7a adds — ``AdminBootstrapConfig`` in ``config/accounts.py`` and ``services/accounts/bootstrap_admin_service.py``
— is imported inside the one helper that runs the bootstrap: each case fails on its own, and the module always loads.

Red until A7a, every case. In-process: at their setup while the bootstrap does not exist (SETUP-009's second origin
excepted: its active account is made of rows), then on the route — ``POST /auth/setup`` is a 404 — and on the inspection
— ``purpose: admin_setup`` is a 422. On the lane: SETUP-011 to SETUP-013 on the missing route, INSPECT-013 on the 422. Two
parameters of INSPECT-012 are guards once the bootstrap exists: a setup link asked as ``invite`` or as
``password_reset`` is ``unknown`` already. The INSPECT numbers start at 010: INSPECT-001 to INSPECT-006 are in
``test_registration_api.py``.

Red until A7b-2: SETUP-014 and SETUP-015, on the takeover itself — nothing retires the setup link today, and ``POST
/auth/setup`` with it answers 200 —. SETUP-016 is their guard, green today: what must retire nothing.

Red until A-42/A-43 (label ``# red until A-42/A-43``): SETUP-017 — ``./dev.py user deactivate`` leaves the pending
administrator's link valid today —, SETUP-018 — the stray link of an account set up before answers 200 today and
re-activates it —, and SETUP-016's ``user-demote-refused`` variant — the command demotes today. SETUP-016 changed by
construction: its ``user-deactivate`` variant left it for SETUP-017 (the link is now revoked), and its ``user-demote``
variant now expects the refusal, the account still an administrator once set up; its two other variants stay guards.
"""

from __future__ import annotations

import contextlib
import importlib
import os
import re
import secrets
import threading
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, Optional
from urllib.parse import parse_qs

import bcrypt
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import get_session_generator
from backend.app.schemas.auth import AuthLoginResponse, AuthUserResponse
from backend.app.services.accounts import auth_service, registration_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus, consume_token, inspect_token, issue_token, retire_tokens, revoke_tokens
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

ADMIN_SETUP = AccountTokenPurpose.ADMIN_SETUP
INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET

#: The administrator the configuration of the private instance names (LIBREFOLIO_ADMIN_USERNAME, LIBREFOLIO_ADMIN_EMAIL), handed to the bootstrap.
ADMIN_USERNAME = "setup_admin"
ADMIN_EMAIL = "setup-admin@example.com"
#: Every F02 variable starts so: none may reach the private instance, whose configuration is handed to the service.
F02_VARIABLE_PREFIX = "LIBREFOLIO_ADMIN_"
#: Nor may the accounts variables: the mode, the limit, the links (without LIBREFOLIO_PUBLIC_URL no email leaves).
ACCOUNTS_VARIABLES = ("LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BILLING_URL")

#: Passwords that meet the rules (decision 37).
NEW_PASSWORD = "Setup-Admin-Pass-2026"
ANOTHER_PASSWORD = "Another-Setup-Pass-2026"
OLD_PASSWORD = "Already-Active-Pass-2026"
STRONG_PASSWORD = "Strong-Pass-123!"
#: The password an account gets another way than its setup link (lot A7b-2): a reset link, ``./dev.py user reset``, a change of its own.
OTHER_WAY_PASSWORD = "Set-Another-Way-2026"
#: Long enough, lowercase only: it misses three rules, listed in the policy's order.
WEAK_PASSWORD = "weakpassword"
WEAK_RULES = ["uppercase", "digit", "special"]
#: One password per rule, each missing that rule alone.
ONE_RULE_MISSED = [
    pytest.param("Short1!", ["min_length"], id="min_length"),
    pytest.param("setup-pass-2026", ["uppercase"], id="uppercase"),
    pytest.param("SETUP-PASS-2026", ["lowercase"], id="lowercase"),
    pytest.param("Setup-Pass-Now", ["digit"], id="digit"),
    pytest.param("Setup Pass 2026", ["special"], id="special-a-space-is-not-a-symbol"),
]

#: The detail of each coded refusal carries exactly these keys.
PASSWORD_TOO_WEAK_KEYS = frozenset({"error_code", "message", "rules"})
TOKEN_INVALID_KEYS = frozenset({"error_code", "message"})
#: The body of POST /auth/login and its user: what a setup answers.
LOGIN_RESPONSE_KEYS = frozenset(AuthLoginResponse.model_fields)
LOGIN_USER_KEYS = frozenset(AuthUserResponse.model_fields)
#: What only a valid token may show, besides its status and purpose.
TOKEN_DETAILS = ("expires_at", "grants_admin", "email", "username")
#: The tokens that are not a live setup link (_not_a_live_setup_link), and among them the setup links that are not valid.
NOT_A_LIVE_SETUP_LINK = ("unknown", "expired", "consumed", "revoked", "invitation", "password_reset")
DEAD_STATUSES = ("unknown", "expired", "consumed", "revoked")
#: Bodies of POST /auth/setup the schema refuses, built from the token of the live link.
MALFORMED_BODIES: dict[str, Callable[[str], dict[str, Any]]] = {
    "no-token": lambda token: {"new_password": NEW_PASSWORD},
    "no-new-password": lambda token: {"token": token},
    "empty-token": lambda token: {"token": "", "new_password": NEW_PASSWORD},
    "empty-new-password": lambda token: {"token": token, "new_password": ""},
    "token-over-200-characters": lambda token: {"token": "t" * 201, "new_password": NEW_PASSWORD},
}

# Paths of the in-process app, mounted as api/v1/router.py mounts the auth router.
SETUP = f"{API_V1_PREFIX}/auth/setup"
INSPECT = f"{API_V1_PREFIX}/auth/tokens/inspect"
LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
RESET_WITH_LINK = f"{API_V1_PREFIX}/auth/password-reset"
CHANGE_PASSWORD = f"{API_V1_PREFIX}/auth/change-password"


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the live cases only (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# THE PRIVATE INSTANCE: THE REAL AUTH ROUTER ON A DATABASE OF THIS TEST
# ============================================================================


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the auth router, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _app(engine: AsyncEngine) -> FastAPI:
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
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with, no account; no F02 or accounts variable in this process; bcrypt at cost 4, the cookie's Secure attribute on ``auto``. Disposed at teardown."""
    for name in [*ACCOUNTS_VARIABLES, *(variable for variable in os.environ if variable.startswith(F02_VARIABLE_PREFIX))]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'admin-setup.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_app(engine))
    finally:
        await engine.dispose()


@contextlib.asynccontextmanager
async def _browser(private: _Private) -> AsyncIterator[httpx.AsyncClient]:
    """A browser of its own on the private instance: its own cookie jar, no session until it signs in."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=private.app), base_url="http://test", timeout=TIMEOUT) as client:
        yield client


async def _post(private: _Private, path: str, body: dict[str, Any]) -> httpx.Response:
    """A POST from a browser of its own: no cookie, no session — whoever holds a link."""
    async with _browser(private) as stranger:
        return await stranger.post(path, json=body)


async def _setup(private: _Private, token: str, new_password: str) -> httpx.Response:
    return await _post(private, SETUP, {"token": token, "new_password": new_password})


async def _inspect(private: _Private, token: str, purpose: str) -> httpx.Response:
    return await _post(private, INSPECT, {"token": token, "purpose": purpose})


async def _sign_in(private: _Private, username: str, password: str) -> httpx.Response:
    return await _post(private, LOGIN, {"username": username, "password": password})


async def _me(private: _Private, cookie: str) -> httpx.Response:
    """GET /auth/me with one session cookie, sent explicitly from a browser of its own."""
    async with _browser(private) as device:
        return await device.get(ME, headers={"Cookie": f"{COOKIE}={cookie}"})


# ============================================================================
# STATE: ACCOUNTS AND TOKENS IN THE PRIVATE DATABASE
# ============================================================================


@dataclass(frozen=True)
class _AccountState:
    """What a refused setup leaves as it was: whether the account is active and an administrator, its password hash and its session version."""

    active: bool
    superuser: bool
    hashed_password: str
    session_version: int


async def _account_state(engine: AsyncEngine, user_id: int) -> _AccountState:
    """The state of an account, read fresh."""
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(User.is_active, User.is_superuser, User.hashed_password, User.session_version).where(User.id == user_id))).one()
    return _AccountState(active=bool(row[0]), superuser=bool(row[1]), hashed_password=row[2], session_version=row[3])


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose) -> TokenStatus:
    """The status of ``token`` for ``purpose``, read fresh."""
    async with AsyncSession(engine) as session:
        return (await inspect_token(session, token, purpose)).status


async def _footprint(engine: AsyncEngine, user_id: int, links: list[tuple[str, AccountTokenPurpose]]) -> tuple[_AccountState, list[TokenStatus]]:
    """What a refusal may not change: the state of the account, and the status of every token of ``links`` under its own purpose."""
    return await _account_state(engine, user_id), [await _status(engine, token, purpose) for token, purpose in links]


async def _token_record(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose) -> AccountToken:
    """The row of ``token`` for ``purpose``, read fresh."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        inspection = await inspect_token(session, token, purpose)
    assert inspection.record is not None, f"setup: the {purpose.value} token is not in the database"
    return inspection.record


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: Any) -> IssuedToken:
    """A token issued by the token service directly, committed: its plaintext and its row."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _add_user(engine: AsyncEngine, username: str, *, password: str, admin: bool = False) -> int:
    """An active account written as a row, ``<username>@example.com``, with a real bcrypt hash of ``password`` (cost 4), so that it can sign in."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password=auth_service.hash_password(password), is_superuser=admin, is_active=True)
        session.add(user)
        await session.commit()
    return user.id


async def _activate_by_hand(engine: AsyncEngine, user_id: int, password: str) -> None:
    """The account made active, with ``password`` (a real bcrypt hash, cost 4), by a row update: some other way than its setup link, which stays live."""
    async with AsyncSession(engine) as session:
        await session.execute(update(User).where(User.id == user_id).values(is_active=True, hashed_password=auth_service.hash_password(password)))
        await session.commit()


# ============================================================================
# THE PENDING ADMINISTRATOR, MADE BY THE BOOTSTRAP
# ============================================================================


@dataclass(frozen=True)
class _Pending:
    """The pending administrator of a private instance: its id, the address the bootstrap gave it, and the token of its live setup link."""

    user_id: int
    email: str
    token: str


async def _bootstrap(engine: AsyncEngine, *, token: Optional[str]) -> Any:
    """``run_admin_bootstrap`` on the private instance, for ADMIN_EMAIL and ADMIN_USERNAME, ``token`` as the configuration's (None: the instance generates one), at the present moment; committed. What it returned."""
    from backend.app.config.accounts import AdminBootstrapConfig  # noqa: PLC0415 — added by A7a: imported here, so that each case fails on its own and the module still loads
    from backend.app.services.accounts.bootstrap_admin_service import run_admin_bootstrap  # noqa: PLC0415 — added by A7a: imported here, so that each case fails on its own and the module still loads

    async with AsyncSession(engine, expire_on_commit=False) as session:
        result = await run_admin_bootstrap(session, AdminBootstrapConfig(email=ADMIN_EMAIL, username=ADMIN_USERNAME, token=token), now=utcnow())
        await session.commit()
    return result


async def _pending_from(engine: AsyncEngine, token: str, result: Any) -> _Pending:
    """Barrier after the bootstrap: ADMIN_USERNAME is an inactive superuser, and ``token`` a live ``admin_setup`` token of that account."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        account = (await session.execute(select(User).where(User.username == ADMIN_USERNAME))).scalars().first()
        inspection = await inspect_token(session, token, ADMIN_SETUP)
    assert account is not None and account.id is not None, f"setup: run_admin_bootstrap on an empty instance must create the pending administrator {ADMIN_USERNAME!r}; it returned {result!r}"
    assert (account.is_active, account.is_superuser) == (False, True), f"setup: the pending administrator is an inactive superuser: is_active {account.is_active}, is_superuser {account.is_superuser}; the bootstrap returned {result!r}"
    owner = inspection.record.user_id if inspection.record is not None else None
    assert (inspection.status, owner) == (TokenStatus.VALID, account.id), f"setup: the bootstrap's link must be a live admin_setup token of the pending administrator (id {account.id}): status {inspection.status.value}, owner {owner}; the bootstrap returned {result!r}"
    return _Pending(user_id=account.id, email=account.email, token=token)


async def _pending_admin(private: _Private) -> _Pending:
    """The pending administrator F02 makes on the empty private instance, the token of its setup link given by the configuration (``secrets.token_urlsafe(32)``: 43 URL-safe characters), so that the test holds the link."""
    token = secrets.token_urlsafe(32)
    return await _pending_from(private.engine, token, await _bootstrap(private.engine, token=token))


@pytest_asyncio.fixture
async def pending(private: _Private) -> _Pending:
    """The private instance's pending administrator, made by the bootstrap (``_pending_admin``)."""
    return await _pending_admin(private)


async def _not_a_live_setup_link(engine: AsyncEngine, kind: str, owner: int) -> tuple[str, AccountTokenPurpose]:
    """A token that is not a live setup link, of one ``kind``, with the purpose it was issued for: its status is read under that purpose.

    ``unknown``: never issued. ``expired``, ``consumed``, ``revoked``: a setup link of ``owner``, issued 72 hours and one
    second ago, spent through the token service, or revoked. ``invitation``: a live invitation, an administrator's.
    ``password_reset``: a live password-reset link of ``owner``.
    """
    assert kind in NOT_A_LIVE_SETUP_LINK, f"no such kind of token: {kind!r}"
    if kind == "unknown":
        return secrets.token_urlsafe(32), ADMIN_SETUP
    if kind == "invitation":
        return (await _issue(engine, INVITE, grants_admin=True)).token, INVITE
    if kind == "password_reset":
        return (await _issue(engine, PASSWORD_RESET, user_id=owner)).token, PASSWORD_RESET
    if kind == "expired":
        return (await _issue(engine, ADMIN_SETUP, user_id=owner, now=utcnow() - DEFAULT_TTL[ADMIN_SETUP] - timedelta(seconds=1))).token, ADMIN_SETUP
    issued = await _issue(engine, ADMIN_SETUP, user_id=owner)
    async with AsyncSession(engine) as session:
        if kind == "consumed":
            assert await consume_token(session, issued.token, ADMIN_SETUP) is not None, "setup: the setup link must be consumed"
        else:
            assert await revoke_tokens(session, token_id=issued.record.id) == 1, "setup: the setup link must be revoked"
        await session.commit()
    return issued.token, ADMIN_SETUP


async def _active_account_with_a_setup_link(private: _Private, origin: str) -> tuple[int, str, str]:
    """An active administrator holding a live setup link, its password OLD_PASSWORD: ``(user_id, username, token)``.

    ``pending-administrator-activated-since``: the bootstrap's pending administrator, made active since some other way (a
    row update), its setup link left live. ``active-administrator-with-a-setup-link``: an active administrator written as
    rows, given a setup link by the token service — no bootstrap.
    """
    if origin == "pending-administrator-activated-since":
        pending = await _pending_admin(private)
        await _activate_by_hand(private.engine, pending.user_id, OLD_PASSWORD)
        return pending.user_id, ADMIN_USERNAME, pending.token
    user_id = await _add_user(private.engine, "active_admin", password=OLD_PASSWORD, admin=True)
    return user_id, "active_admin", (await _issue(private.engine, ADMIN_SETUP, user_id=user_id)).token


# ============================================================================
# READING THE ANSWERS
# ============================================================================


def _error_code(response: httpx.Response) -> Optional[str]:
    """``detail.error_code`` of a refusal, or None when the body has none."""
    try:
        body = response.json()
    except ValueError:
        return None
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail.get("error_code") if isinstance(detail, dict) else None


def _session_set_cookies(response: httpx.Response) -> list[tuple[str, dict[str, str]]]:
    """Every Set-Cookie of ``response`` that writes the session cookie, matched by name: its value, and its attributes by lower-cased name ("" for a flag).

    Parsed by name, never by position: the attribute order is http.cookies', not a contract.
    """
    cookies: list[tuple[str, dict[str, str]]] = []
    for header in response.headers.get_list("set-cookie"):
        pair, *attributes = (part.strip() for part in header.split(";"))
        name, _, value = pair.partition("=")
        if name.strip() == COOKIE:
            cookies.append((value.strip(), {key.strip().lower(): setting.strip() for key, _, setting in (attribute.partition("=") for attribute in attributes if attribute)}))
    return cookies


def _the_session_cookie(response: httpx.Response, request: str) -> tuple[str, dict[str, str]]:
    """The one session Set-Cookie of ``response``: its value and its attributes."""
    cookies = _session_set_cookies(response)
    assert len(cookies) == 1 and cookies[0][0], f"{request}: expected exactly one {COOKIE} Set-Cookie with a value, got {response.headers.get_list('set-cookie')}"
    return cookies[0]


def _assert_password_too_weak(response: httpx.Response, rules: list[str], request: str) -> None:
    """``response`` is decision 37's refusal: 400 ``PASSWORD_TOO_WEAK``, a message, ``rules`` exactly — the codes missed, in the policy's order —, and no session cookie."""
    assert (response.status_code, _error_code(response)) == (400, "PASSWORD_TOO_WEAK"), f"{request}: expected 400 PASSWORD_TOO_WEAK, got {response.status_code} {response.text}"
    detail = response.json()["detail"]
    assert set(detail) == PASSWORD_TOO_WEAK_KEYS, f"{request}: the refusal must carry exactly {sorted(PASSWORD_TOO_WEAK_KEYS)}: {detail}"
    assert isinstance(detail["message"], str) and detail["message"].strip(), f"{request}: the refusal must carry a message: {detail}"
    assert detail["rules"] == rules, f"{request}: rules must be exactly the codes missed, in the policy's order, {rules}: got {detail['rules']}"
    assert _session_set_cookies(response) == [], f"{request}: a refusal must set no session cookie: Set-Cookie {response.headers.get_list('set-cookie')}"


def _assert_token_invalid(response: httpx.Response, request: str) -> None:
    """``response`` is the refusal of a link that is not valid, as POST /auth/password-reset gives it: 400 ``TOKEN_INVALID`` and a message, nothing more, and no session cookie."""
    assert (response.status_code, _error_code(response)) == (400, "TOKEN_INVALID"), f"{request}: expected 400 TOKEN_INVALID, got {response.status_code} {response.text}"
    detail = response.json()["detail"]
    assert set(detail) == TOKEN_INVALID_KEYS, f"{request}: the refusal must carry exactly {sorted(TOKEN_INVALID_KEYS)}: {detail}"
    assert isinstance(detail["message"], str) and detail["message"].strip(), f"{request}: the refusal must carry a message: {detail}"
    assert _session_set_cookies(response) == [], f"{request}: a refusal must set no session cookie: Set-Cookie {response.headers.get_list('set-cookie')}"


def _details_shown(body: dict[str, Any]) -> dict[str, Any]:
    """The details a body shows beyond status and purpose: every detail key present with a value."""
    return {key: body[key] for key in TOKEN_DETAILS if body.get(key) is not None}


def _instant(text: Any) -> Optional[datetime]:
    """An API timestamp as an aware UTC datetime (a naive one is UTC); None when it is not a timestamp."""
    if not isinstance(text, str):
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


# ============================================================================
# 1. POST /auth/setup — A LIVE LINK, IN-PROCESS
# ============================================================================


class TestSetup:
    """POST /auth/setup with the pending administrator's live link: the account activated and signed in, once."""

    @pytest.mark.asyncio
    async def test_a_live_link_activates_the_pending_administrator_and_answers_as_the_login(self, private: _Private, pending: _Pending) -> None:
        """SETUP-001: the pending administrator's live link and a new password that meets the rules → 200 with the body of POST /auth/login — exactly ``user``, ``user_settings``, ``message`` and ``show_donation_popup`` (``AuthLoginResponse``), ``user`` exactly the fields of ``AuthUserResponse`` —: ``user`` the pending account (its id, username and address), active and an administrator; a message; the popup flag a boolean; the settings an object or null. In the database the account is active, still a superuser."""
        print_section("SETUP-001: a live setup link activates the pending administrator")

        response = await _setup(private, pending.token, NEW_PASSWORD)
        state = await _account_state(private.engine, pending.user_id)

        assert response.status_code == 200, f"POST /auth/setup with a live link and a password that meets the rules: {response.status_code} {response.text}"
        body = response.json()
        assert set(body) == LOGIN_RESPONSE_KEYS, f"the setup answers as POST /auth/login does, exactly {sorted(LOGIN_RESPONSE_KEYS)}: {body}"
        user = body["user"]
        assert isinstance(user, dict) and set(user) == LOGIN_USER_KEYS, f"user is the login's, exactly {sorted(LOGIN_USER_KEYS)}: {user}"
        assert (user["id"], user["username"], user["email"], user["is_active"], user["is_superuser"]) == (pending.user_id, ADMIN_USERNAME, pending.email, True, True), f"user must be the pending account, now active, an administrator: {user}"
        assert isinstance(body["message"], str) and body["message"].strip(), f"the answer carries a message, as the login's: {body}"
        assert isinstance(body["show_donation_popup"], bool), f"show_donation_popup is a boolean, as the login's: {body}"
        assert body["user_settings"] is None or isinstance(body["user_settings"], dict), f"user_settings is the login's: the account's settings, or null: {body}"
        assert (state.active, state.superuser) == (True, True), f"in the database the account must be active and still a superuser: active {state.active}, superuser {state.superuser}"
        print_success("200, the login's body, the pending administrator active")

    @pytest.mark.asyncio
    async def test_the_setup_signs_in_with_the_login_cookie(self, private: _Private, pending: _Pending) -> None:
        """SETUP-002: the 200 sets exactly one session cookie, under the login's name and with the login's attributes — compared attribute by attribute with those of a POST /auth/login of the same account afterwards —; GET /auth/me with that cookie alone answers that account, active and an administrator."""
        print_section("SETUP-002: the setup signs the administrator in")

        setup = await _setup(private, pending.token, NEW_PASSWORD)
        assert setup.status_code == 200, f"POST /auth/setup with a live link: {setup.status_code} {setup.text}"
        cookie, attributes = _the_session_cookie(setup, "POST /auth/setup")
        me = await _me(private, cookie)
        login = await _sign_in(private, ADMIN_USERNAME, NEW_PASSWORD)
        assert login.status_code == 200, f"barrier: the administrator signs in with the password the setup set: {login.status_code} {login.text}"
        _, login_attributes = _the_session_cookie(login, "POST /auth/login")

        me_user = me.json().get("user") if me.status_code == 200 else None
        assert isinstance(me_user, dict), f"GET /auth/me with the setup's cookie alone must answer the account: {me.status_code} {me.text}"
        assert (me_user.get("id"), me_user.get("username"), me_user.get("is_active"), me_user.get("is_superuser")) == (pending.user_id, ADMIN_USERNAME, True, True), f"the setup's cookie is a session of the pending account, now active, an administrator: {me_user}"
        assert attributes == login_attributes, f"the setup's session cookie must carry the login's attributes, every one: setup {attributes}, login {login_attributes}"
        print_success("one session cookie, the login's attributes; /auth/me answers the administrator")

    @pytest.mark.asyncio
    async def test_the_link_works_once_and_the_other_setup_links_are_revoked(self, private: _Private, pending: _Pending) -> None:
        """SETUP-003: after a setup the link is ``consumed`` — the same link again, with another password, → 400 ``TOKEN_INVALID`` —, the account's other live setup link is ``revoked``, and POST /auth/login with the new password answers the account the setup answered; the second password signs nothing in."""
        print_section("SETUP-003: the link works once")
        other = await _issue(private.engine, ADMIN_SETUP, user_id=pending.user_id)
        assert await _status(private.engine, other.token, ADMIN_SETUP) == TokenStatus.VALID, "setup: the pending administrator holds a second live setup link"

        first = await _setup(private, pending.token, NEW_PASSWORD)
        again = await _setup(private, pending.token, ANOTHER_PASSWORD)
        statuses = {"the link": await _status(private.engine, pending.token, ADMIN_SETUP), "the other setup link": await _status(private.engine, other.token, ADMIN_SETUP)}
        with_new, with_another = await _sign_in(private, ADMIN_USERNAME, NEW_PASSWORD), await _sign_in(private, ADMIN_USERNAME, ANOTHER_PASSWORD)

        assert first.status_code == 200, f"{first.status_code} {first.text}"
        _assert_token_invalid(again, "POST /auth/setup with a link already used")
        assert statuses == {"the link": TokenStatus.CONSUMED, "the other setup link": TokenStatus.REVOKED}, statuses
        assert with_new.status_code == 200, f"the new password must sign in: {with_new.status_code} {with_new.text}"
        assert with_new.json().get("user") == first.json().get("user"), f"the login must answer the account the setup answered: login {with_new.json().get('user')}, setup {first.json().get('user')}"
        assert with_another.status_code == 401, f"the refused second setup must change nothing, its password signs nothing in: {with_another.status_code} {with_another.text}"
        print_success("consumed, the other setup link revoked, the new password signs in")

    @pytest.mark.asyncio
    async def test_the_link_the_instance_generated_activates_the_pending_administrator(self, private: _Private) -> None:
        """SETUP-004: no token in the configuration — the bootstrap generates the link and returns its token as ``link_token`` —: POST /auth/setup with that token → 200, the pending account active and an administrator."""
        result = await _bootstrap(private.engine, token=None)
        link_token = getattr(result, "link_token", None)
        assert isinstance(link_token, str) and link_token, f"setup: without a token in the configuration, run_admin_bootstrap must return the token it generated as link_token: {result!r}"
        pending = await _pending_from(private.engine, link_token, result)

        response = await _setup(private, link_token, NEW_PASSWORD)

        assert response.status_code == 200, f"POST /auth/setup with the link the instance generated: {response.status_code} {response.text}"
        user = response.json().get("user") or {}
        assert (user.get("id"), user.get("username"), user.get("is_active"), user.get("is_superuser")) == (pending.user_id, ADMIN_USERNAME, True, True), f"the generated link activates the pending administrator: {user}"

    @pytest.mark.asyncio
    async def test_the_new_password_is_hashed_off_the_event_loop(self, private: _Private, pending: _Pending, monkeypatch: pytest.MonkeyPatch) -> None:
        """SETUP-005 (the plan's C3): ``bcrypt.hashpw`` — where every hashing path ends — runs in a worker thread, never on the event loop serving the setup."""
        threads: list[int] = []
        real_hashpw = bcrypt.hashpw

        def spying_hashpw(password: bytes, salt: bytes) -> bytes:
            threads.append(threading.get_ident())
            return real_hashpw(password, salt)

        monkeypatch.setattr(bcrypt, "hashpw", spying_hashpw)
        loop_thread = threading.get_ident()
        response = await _setup(private, pending.token, NEW_PASSWORD)

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        assert threads, "barrier: bcrypt.hashpw was never called"
        assert loop_thread not in threads, "the setup hashed the password on the event loop: it belongs in await asyncio.to_thread(...)"


# ============================================================================
# 2. POST /auth/setup — REFUSALS, IN-PROCESS
# ============================================================================


class TestSetupRefusals:
    """POST /auth/setup refused: the password first, then the link. A refusal changes nothing — but night decision 6's revocation."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("password", "rules"), ONE_RULE_MISSED)
    async def test_a_password_that_breaks_the_rules_is_refused_and_keeps_the_link(self, private: _Private, pending: _Pending, password: str, rules: list[str]) -> None:
        """SETUP-006: the live link with a new password that misses one rule → 400 ``PASSWORD_TOO_WEAK``, ``rules`` exactly that rule; the link is not spent — inspected afterwards, still ``valid`` for the pending account —, the account as it was, still inactive; then the same link with a password that meets the rules → 200."""
        links = [(pending.token, ADMIN_SETUP)]
        before = await _footprint(private.engine, pending.user_id, links)

        refused = await _setup(private, pending.token, password)
        inspected = await _inspect(private, pending.token, "admin_setup")
        after = await _footprint(private.engine, pending.user_id, links)
        spent = await _setup(private, pending.token, NEW_PASSWORD)

        _assert_password_too_weak(refused, rules, f"POST /auth/setup with the live link and {password!r}")
        assert inspected.status_code == 200 and (inspected.json().get("status"), inspected.json().get("username")) == ("valid", ADMIN_USERNAME), f"a refused password must not spend the link: inspected, still valid for {ADMIN_USERNAME}: {inspected.status_code} {inspected.text}"
        assert after == before, f"a refused password must change neither the account nor the link: before {before}, after {after}"
        assert spent.status_code == 200, f"the link a refused password left valid must still activate the account: {spent.status_code} {spent.text}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", NOT_A_LIVE_SETUP_LINK)
    async def test_a_password_that_breaks_the_rules_is_refused_before_the_link_is_read(self, private: _Private, pending: _Pending, kind: str) -> None:
        """SETUP-007: a token that is not a live setup link — never issued, expired, consumed, revoked, an invitation, a password-reset link of the pending account — with a password that breaks the rules → 400 ``PASSWORD_TOO_WEAK``, the codes missed: the password is checked before the token; nothing changes."""
        offered = await _not_a_live_setup_link(private.engine, kind, pending.user_id)
        links = [(pending.token, ADMIN_SETUP), offered]
        before = await _footprint(private.engine, pending.user_id, links)

        response = await _setup(private, offered[0], WEAK_PASSWORD)
        after = await _footprint(private.engine, pending.user_id, links)

        _assert_password_too_weak(response, WEAK_RULES, f"POST /auth/setup with a {kind} token and {WEAK_PASSWORD!r}")
        assert after == before, f"a refused setup must change neither the account nor any token: before {before}, after {after}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", NOT_A_LIVE_SETUP_LINK)
    async def test_a_token_that_is_not_a_live_setup_link_answers_400_token_invalid_and_changes_nothing(self, private: _Private, pending: _Pending, kind: str) -> None:
        """SETUP-008: a token never issued, an expired, consumed or revoked setup link, an invitation, or a password-reset link of the pending account itself, with a password that meets the rules → 400 ``TOKEN_INVALID``; nothing changes: the account inactive, its password and session version as they were; the pending administrator's live link still valid; the token offered as it was — an invitation or a reset link still valid."""
        offered = await _not_a_live_setup_link(private.engine, kind, pending.user_id)
        links = [(pending.token, ADMIN_SETUP), offered]
        before = await _footprint(private.engine, pending.user_id, links)

        response = await _setup(private, offered[0], NEW_PASSWORD)
        after = await _footprint(private.engine, pending.user_id, links)

        _assert_token_invalid(response, f"POST /auth/setup with a {kind} token")
        assert after == before, f"a refused setup must change neither the account nor any token: before {before}, after {after}"
        assert after[0].active is False, "the account must stay inactive"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("origin", ["pending-administrator-activated-since", "active-administrator-with-a-setup-link"])
    async def test_the_setup_link_of_an_account_already_active_is_refused_and_revoked(self, private: _Private, origin: str) -> None:
        """SETUP-009 — night decision 6, to review: the live setup link of an account already active — the pending administrator made active since some other way, or an active administrator holding a setup link — with a password that meets the rules → 400 ``TOKEN_INVALID``, and that link is now ``revoked``; the account as it was — active, an administrator, its password and session version —: the new password signs nothing in, the old one still does."""
        print_section(f"SETUP-009: the setup link of an account already active ({origin})")
        user_id, username, token = await _active_account_with_a_setup_link(private, origin)
        before = await _account_state(private.engine, user_id)
        assert before.active is True and await _status(private.engine, token, ADMIN_SETUP) == TokenStatus.VALID, f"setup: an active account holding a live setup link: active {before.active}"

        response = await _setup(private, token, NEW_PASSWORD)
        status = await _status(private.engine, token, ADMIN_SETUP)
        after = await _account_state(private.engine, user_id)
        with_new, with_old = await _sign_in(private, username, NEW_PASSWORD), await _sign_in(private, username, OLD_PASSWORD)

        _assert_token_invalid(response, f"POST /auth/setup with the setup link of an account already active ({origin})")
        assert status == TokenStatus.REVOKED, f"the setup link of an account already active must be revoked (night decision 6): it is {status.value}"
        assert after == before, f"the account must stay as it was: before {before}, after {after}"
        assert (with_new.status_code, with_old.status_code) == (401, 200), f"the refused setup must not change the password: the new one {with_new.status_code}, the old one {with_old.status_code}"
        print_success("TOKEN_INVALID, the link revoked, the account untouched")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("case", list(MALFORMED_BODIES))
    async def test_a_malformed_body_is_a_request_validation_error(self, private: _Private, pending: _Pending, case: str) -> None:
        """SETUP-010: ``token`` or ``new_password`` missing, an empty one, or a token over 200 characters → 422, a request validation error before anything else; no session cookie, nothing changes, the live link still valid."""
        links = [(pending.token, ADMIN_SETUP)]
        before = await _footprint(private.engine, pending.user_id, links)

        response = await _post(private, SETUP, MALFORMED_BODIES[case](pending.token))
        after = await _footprint(private.engine, pending.user_id, links)

        assert response.status_code == 422, f"POST /auth/setup, {case}: expected 422, got {response.status_code} {response.text}"
        assert _session_set_cookies(response) == [], f"a refused request must set no session cookie: Set-Cookie {response.headers.get_list('set-cookie')}"
        assert after == before, f"a refused request must change neither the account nor the link: before {before}, after {after}"


# ============================================================================
# 3. POST /auth/tokens/inspect WITH purpose admin_setup — IN-PROCESS
# ============================================================================


class TestInspectSetupLink:
    """POST /auth/tokens/inspect with ``purpose: admin_setup``: the status of a setup link; its expiry and username only while it is valid."""

    @pytest.mark.asyncio
    async def test_a_live_setup_link_shows_its_expiry_and_username_only(self, private: _Private, pending: _Pending) -> None:
        """INSPECT-010: the pending administrator's live link, asked as ``admin_setup`` without any session → 200 ``{status: valid, purpose: admin_setup, expires_at, username}``: the link's own expiry, the pending account's username; no ``email`` and no ``grants_admin`` (absent or null), and the account's address nowhere in the body. Asked twice, the same answer: inspecting consumes nothing, the link still valid and the account still pending."""
        print_section("INSPECT-010: a live setup link")
        links = [(pending.token, ADMIN_SETUP)]
        before = await _footprint(private.engine, pending.user_id, links)
        record = await _token_record(private.engine, pending.token, ADMIN_SETUP)

        first = await _inspect(private, pending.token, "admin_setup")
        second = await _inspect(private, pending.token, "admin_setup")
        after = await _footprint(private.engine, pending.user_id, links)

        assert first.status_code == 200, f"{first.status_code} {first.text}"
        body = first.json()
        assert (body.get("status"), body.get("purpose"), body.get("username")) == ("valid", "admin_setup", ADMIN_USERNAME), f"a live setup link shows its status, its purpose and the pending account's username: {body}"
        assert _instant(body.get("expires_at")) == ensure_utc(record.expires_at), f"expires_at must be the link's own, {ensure_utc(record.expires_at)}: {body}"
        assert body.get("email") is None and body.get("grants_admin") is None, f"email and grants_admin are the invitation's: a setup link shows neither: {body}"
        assert pending.email not in first.text, f"the pending administrator's address must not reach whoever holds the link: {first.text}"
        assert second.status_code == 200 and second.json() == body, f"inspecting again must answer the same: {second.status_code} {second.text}"
        assert after == before, f"inspecting must consume nothing: the link still valid, the account still pending: before {before}, after {after}"
        print_success("valid, its expiry and username; no address")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", DEAD_STATUSES)
    async def test_a_setup_link_that_is_not_valid_shows_its_status_and_nothing_else(self, private: _Private, pending: _Pending, kind: str) -> None:
        """INSPECT-011: a setup link never issued, expired, consumed or revoked, asked as ``admin_setup`` → 200 with that status and ``purpose: admin_setup``, and no detail: no expiry, username, e-mail or role."""
        token, _ = await _not_a_live_setup_link(private.engine, kind, pending.user_id)

        response = await _inspect(private, token, "admin_setup")

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        body = response.json()
        assert (body.get("status"), body.get("purpose")) == (kind, "admin_setup"), body
        assert _details_shown(body) == {}, f"a {kind} setup link must show nothing but its status: {body}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("offered", "asked"),
        [
            pytest.param("setup_link", "password_reset", id="setup-link-as-password_reset"),
            pytest.param("setup_link", "invite", id="setup-link-as-invite"),
            pytest.param("password_reset", "admin_setup", id="reset-link-as-admin_setup"),
            pytest.param("invitation", "admin_setup", id="invitation-as-admin_setup"),
        ],
    )
    async def test_a_link_asked_as_another_purpose_is_unknown(self, private: _Private, pending: _Pending, offered: str, asked: str) -> None:
        """INSPECT-012: the pending administrator's live setup link asked as a reset link or as an invitation, and a live reset link of the same account or a live invitation asked as a setup link → 200 ``unknown``, the purpose asked, and nothing more. The first two are guards: ``unknown`` already, once the bootstrap exists."""
        token = pending.token if offered == "setup_link" else (await _not_a_live_setup_link(private.engine, offered, pending.user_id))[0]

        response = await _inspect(private, token, asked)

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        body = response.json()
        assert (body.get("status"), body.get("purpose"), _details_shown(body)) == ("unknown", asked, {}), f"a live {offered} asked as {asked} must be unknown and show nothing: {body}"


# ============================================================================
# 4. ON THE LANE'S SERVER — REFUSALS THAT WRITE NOTHING
# ============================================================================


async def _live_post(path: str, body: dict[str, Any]) -> httpx.Response:
    """An anonymous POST to the lane's server: a client of its own, no cookie."""
    async with httpx.AsyncClient() as client:
        return await client.post(f"{API_BASE}{path}", json=body, timeout=TIMEOUT)


class TestOnTheLane:
    """The lane's real server: refusals of POST /auth/setup and the inspection of a token never issued — nothing written in the lane's database, no setting changed."""

    @pytest.mark.asyncio
    async def test_an_unknown_link_with_a_weak_password_is_refused_for_the_password(self, test_server) -> None:
        """SETUP-011: POST /auth/setup with a token never issued and a password that breaks the rules → 400 ``PASSWORD_TOO_WEAK``, the codes missed: the password is read before the token. Writes nothing."""
        response = await _live_post("/auth/setup", {"token": secrets.token_urlsafe(32), "new_password": WEAK_PASSWORD})

        _assert_password_too_weak(response, WEAK_RULES, f"the lane's POST /auth/setup with a token never issued and {WEAK_PASSWORD!r}")

    @pytest.mark.asyncio
    async def test_an_unknown_link_with_a_strong_password_is_token_invalid(self, test_server) -> None:
        """SETUP-012: POST /auth/setup with a token never issued and a password that meets the rules → 400 ``TOKEN_INVALID``. Writes nothing."""
        response = await _live_post("/auth/setup", {"token": secrets.token_urlsafe(32), "new_password": STRONG_PASSWORD})

        _assert_token_invalid(response, "the lane's POST /auth/setup with a token never issued")

    @pytest.mark.asyncio
    async def test_a_body_without_new_password_is_a_request_validation_error(self, test_server) -> None:
        """SETUP-013: POST /auth/setup with a token and no ``new_password`` → 422. Writes nothing."""
        response = await _live_post("/auth/setup", {"token": secrets.token_urlsafe(32)})

        assert response.status_code == 422, f"the lane's POST /auth/setup without new_password: expected 422, got {response.status_code} {response.text}"

    @pytest.mark.asyncio
    async def test_a_token_never_issued_asked_as_a_setup_link_is_unknown(self, test_server) -> None:
        """INSPECT-013: POST /auth/tokens/inspect with a token never issued and ``purpose: admin_setup`` → 200 ``{status: unknown, purpose: admin_setup}``, and nothing more."""
        response = await _live_post("/auth/tokens/inspect", {"token": secrets.token_urlsafe(32), "purpose": "admin_setup"})

        assert response.status_code == 200, f"the lane's POST /auth/tokens/inspect with purpose admin_setup: {response.status_code} {response.text}"
        body = response.json()
        assert (body.get("status"), body.get("purpose"), _details_shown(body)) == ("unknown", "admin_setup", {}), f"a token never issued is unknown, and shows nothing: {body}"


# ============================================================================
# 5. THE LINK OF AN ACCOUNT SET UP ANOTHER WAY (lot A7b-2, A-32) — IN-PROCESS
# ============================================================================


#: How the pending administrator is set up without its link (A-32), ending inactive as it began (``_set_up_another_way``).
SET_UP_ANOTHER_WAY = ("a-reset-link-spent", "user-reset", "user-activate-then-user-deactivate")
#: What is neither an activation nor a password (``_leave_it_waiting``), with whether the account is an administrator
#: afterwards. Updated in A-42/A-43, by construction: ``./dev.py user demote`` of the pending administrator is refused now
#: — it stays an administrator —, and ``./dev.py user deactivate`` of the account already inactive revokes its link: that
#: variant left this guard for SETUP-017.
NEITHER_ACTIVATION_NOR_PASSWORD = [
    pytest.param("user-demote-refused", True, id="user-demote-refused"),
    pytest.param("reset-link-issued", True, id="a-reset-link-issued-not-spent"),
    pytest.param("expired-reset-link-refused", True, id="an-expired-reset-link-refused"),
]


async def _cli_set_active(engine: AsyncEngine, username: str, active: bool) -> None:
    """``./dev.py user activate`` or ``deactivate``: the call the command makes, ``user_service.set_user_active``. It ends on its promise: done, the account active or not as asked."""
    async with AsyncSession(engine) as session:
        done = await user_service.set_user_active(session, username, active)
        is_active = (await session.execute(select(User.is_active).where(User.username == username))).scalar_one()
    assert (done, bool(is_active)) == ((True, None), active), f"setup: user_service.set_user_active({username!r}, {active}) must succeed and leave the account so: answered {done}, is_active {is_active}"


async def _cli_reset_password(engine: AsyncEngine, username: str, password: str) -> None:
    """``./dev.py user reset``: the call the command makes, ``user_service.reset_password``. It ends on its promise: done, ``password`` the account's."""
    async with AsyncSession(engine) as session:
        done = await user_service.reset_password(session, username, password)
        hashed = (await session.execute(select(User.hashed_password).where(User.username == username))).scalar_one()
    assert done == (True, None) and auth_service.verify_password(password, hashed), f"setup: user_service.reset_password({username!r}) must succeed and set the password: answered {done}"


@dataclass(frozen=True)
class _Commands:
    """``scripts/user_cli.py`` in-process, its ``get_async_engine`` the private file's: what ``./dev.py user …`` runs (lot A-42/A-43)."""

    module: ModuleType
    capsys: pytest.CaptureFixture[str]

    async def run(self, command: str, *arguments: Any) -> tuple[Any, str]:
        """The command function ``command`` — ``cmd_set_admin``, ``cmd_set_user_active``, ``cmd_setup_link`` — called with ``arguments``: what it answered, and what it printed."""
        self.capsys.readouterr()
        answer = await getattr(self.module, command)(*arguments)
        return answer, self.capsys.readouterr().out


@pytest.fixture
def commands(private: _Private, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> _Commands:
    """``./dev.py user …`` on the private instance: ``scripts/user_cli.py`` imported in-process, its ``get_async_engine`` the private engine — never the lane's database."""
    module = importlib.import_module("scripts.user_cli")
    monkeypatch.setattr(module, "get_async_engine", lambda: private.engine)
    return _Commands(module=module, capsys=capsys)


def _printed_setup_token(out: str) -> Optional[str]:
    """The token of the setup link a command printed — ``/setup#token=…``, the bare path without ``LIBREFOLIO_PUBLIC_URL`` —; None when it printed none."""
    printed = re.search(r"/setup#(\S+)", out)
    return parse_qs(printed.group(1)).get("token", [None])[0] if printed else None


async def _reset_link(engine: AsyncEngine, user_id: int, *, expired: bool = False) -> str:
    """A password-reset link of the account, issued as ``POST /users/{user_id}/password-reset-link`` issues it — ``user_service.create_password_reset`` —, committed: its token. ``expired``: issued its lifetime and a minute ago, never waited for. It ends on its promise: the link reads valid, or expired."""
    issued_at = utcnow() - DEFAULT_TTL[PASSWORD_RESET] - timedelta(minutes=1) if expired else None
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await user_service.get_user_by_id(session, user_id)
        assert user is not None, f"setup: no account {user_id} to issue a reset link for"
        issued = await user_service.create_password_reset(session, user, now=issued_at)
        await session.commit()
    expected = TokenStatus.EXPIRED if expired else TokenStatus.VALID
    status = await _status(engine, issued.token, PASSWORD_RESET)
    assert status == expected, f"setup: the reset link must read {expected.value}, it reads {status.value}"
    return issued.token


async def _change_password(private: _Private, cookie: str, current: str, new: str) -> httpx.Response:
    """POST /auth/change-password with one session cookie, sent explicitly from a browser of its own."""
    async with _browser(private) as device:
        return await device.post(CHANGE_PASSWORD, json={"current_password": current, "new_password": new}, headers={"Cookie": f"{COOKIE}={cookie}"})


async def _set_up_another_way(private: _Private, pending: _Pending, way: str) -> Optional[str]:
    """The pending administrator set up another way than its link, as ``way`` says: the password that way set, None when it sets none. It ends on its promise: the account inactive, as it began.

    ``a-reset-link-spent``: a reset link (``_reset_link``) spent through ``POST /auth/password-reset``. ``user-reset``:
    ``./dev.py user reset``. ``user-activate-then-user-deactivate``: ``./dev.py user activate`` then ``deactivate``,
    another active administrator written first — the command never deactivates the last one.
    """
    assert way in SET_UP_ANOTHER_WAY, f"no such way: {way!r}"
    password: Optional[str] = OTHER_WAY_PASSWORD
    if way == "a-reset-link-spent":
        spent = await _post(private, RESET_WITH_LINK, {"token": await _reset_link(private.engine, pending.user_id), "new_password": OTHER_WAY_PASSWORD})
        assert spent.status_code == 200, f"setup: POST /auth/password-reset with a reset link of the pending administrator: {spent.status_code} {spent.text}"
    elif way == "user-reset":
        await _cli_reset_password(private.engine, ADMIN_USERNAME, OTHER_WAY_PASSWORD)
    else:
        await _add_user(private.engine, "other_admin", password=OLD_PASSWORD, admin=True)
        await _cli_set_active(private.engine, ADMIN_USERNAME, True)
        await _cli_set_active(private.engine, ADMIN_USERNAME, False)
        password = None
    assert (await _account_state(private.engine, pending.user_id)).active is False, f"setup: set up another way ({way}), the account must end inactive, as it began"
    return password


async def _leave_it_waiting(private: _Private, pending: _Pending, action: str, commands: _Commands) -> None:
    """``action`` on the pending administrator, neither an activation nor a password (NEITHER_ACTIVATION_NOR_PASSWORD). It ends on its promise: the account still inactive.

    ``user-demote-refused``: ``./dev.py user demote``, the command itself — refused since A-43: falsy, a line starting
    with ❌, the account as it was. ``reset-link-issued``: a reset link issued, not spent. ``expired-reset-link-refused``:
    an expired reset link refused by ``POST /auth/password-reset`` (400 ``TOKEN_INVALID``): no password set.
    """
    if action == "user-demote-refused":
        before = await _account_state(private.engine, pending.user_id)
        answer, out = await commands.run("cmd_set_admin", ADMIN_USERNAME, False)
        after = await _account_state(private.engine, pending.user_id)
        assert not answer and any(line.startswith("❌") for line in out.splitlines()), f"red until A-43: ./dev.py user demote must refuse the pending administrator — falsy, a line starting with ❌ —: it answered {answer!r}: {out!r}"
        assert after == before, f"a refused demotion must change nothing: before {before}, after {after}"
    elif action == "reset-link-issued":
        await _reset_link(private.engine, pending.user_id)
    else:
        assert action == "expired-reset-link-refused", f"no such action: {action!r}"
        refused = await _post(private, RESET_WITH_LINK, {"token": await _reset_link(private.engine, pending.user_id, expired=True), "new_password": OTHER_WAY_PASSWORD})
        _assert_token_invalid(refused, "setup: POST /auth/password-reset with an expired reset link")
    assert (await _account_state(private.engine, pending.user_id)).active is False, f"setup: after {action} the pending administrator must still be inactive"


class TestSetUpAnotherWay:
    """Lot A7b-2 (A-32, decision N60): an account set up another way than its setup link has its setup links retired — revoked and consumed —, so that the old link sets nothing, the account inactive again too. In-process, as every case with a pending administrator."""

    # red until A7b-2
    @pytest.mark.asyncio
    @pytest.mark.parametrize("way", SET_UP_ANOTHER_WAY)
    async def test_the_link_of_an_account_set_up_another_way_is_retired_and_takes_nothing_over(self, private: _Private, pending: _Pending, way: str) -> None:
        """SETUP-014 (A-32): the pending administrator set up another way than its link — a reset link spent, ``./dev.py user reset``, or ``./dev.py user activate`` then ``deactivate`` —, inactive at the end as it began: its setup link is retired (decision N60). Inspected as ``admin_setup`` → ``revoked`` and nothing more; POST /auth/setup with it and a password that meets the rules → 400 ``TOKEN_INVALID``, and nothing changes: still inactive, its password and session version as they were, the link as it was. The setup's password signs nothing in (401); the password the other way set is still the account's — the login answers it as for any inactive account, 403 ``ACCOUNT_DISABLED``."""
        print_section(f"SETUP-014: the setup link of an account set up another way ({way})")
        password = await _set_up_another_way(private, pending, way)
        links = [(pending.token, ADMIN_SETUP)]

        inspected = await _inspect(private, pending.token, "admin_setup")
        before = await _footprint(private.engine, pending.user_id, links)
        response = await _setup(private, pending.token, NEW_PASSWORD)
        after = await _footprint(private.engine, pending.user_id, links)
        with_setup_password = await _sign_in(private, ADMIN_USERNAME, NEW_PASSWORD)
        with_its_password = None if password is None else await _sign_in(private, ADMIN_USERNAME, password)

        _assert_token_invalid(response, f"POST /auth/setup with the old link of an account set up another way ({way}), inactive: its holder must not take the account over")
        body = inspected.json() if inspected.status_code == 200 else {}
        assert (inspected.status_code, body.get("status"), body.get("purpose"), _details_shown(body)) == (200, "revoked", "admin_setup", {}), f"the setup link of an account set up another way must be retired: inspected, revoked and nothing more: {inspected.status_code} {inspected.text}"
        assert after == before and after[0].active is False, f"a refused setup must change nothing, the account still inactive: before {before}, after {after}"
        assert with_setup_password.status_code == 401, f"the refused setup's password must sign nothing in: {with_setup_password.status_code} {with_setup_password.text}"
        if with_its_password is not None:
            assert (with_its_password.status_code, _error_code(with_its_password)) == (403, "ACCOUNT_DISABLED"), f"the password set another way ({way}) must still be the account's, answered as for any inactive account: {with_its_password.status_code} {with_its_password.text}"
        print_success("the link retired: revoked, refused, nothing changed")

    # red until A7b-2
    @pytest.mark.asyncio
    async def test_a_change_of_password_retires_the_accounts_setup_links(self, private: _Private) -> None:
        """SETUP-015 (A-32, defense in depth): an active account with a known password holds a live setup link (written directly: no path of the product leaves one any more), signs in and changes its password through POST /auth/change-password (200): the link is retired — inspected right after, ``revoked`` and nothing more. Deactivated since (``./dev.py user deactivate``), so that night decision 6 — the link of an active account refused and revoked anyway (SETUP-009) — cannot answer for the retirement: POST /auth/setup with that link → 400 ``TOKEN_INVALID``, and nothing changes; the setup's password signs nothing in (401), the changed one is still the account's (403 ``ACCOUNT_DISABLED``, the account inactive)."""
        print_section("SETUP-015: a change of password retires the account's setup links")
        user_id = await _add_user(private.engine, "changer", password=OLD_PASSWORD)
        token = (await _issue(private.engine, ADMIN_SETUP, user_id=user_id)).token
        login = await _sign_in(private, "changer", OLD_PASSWORD)
        assert login.status_code == 200 and await _status(private.engine, token, ADMIN_SETUP) == TokenStatus.VALID, f"setup: an active account, signed in, holding a live setup link: login {login.status_code} {login.text}"
        cookie, _ = _the_session_cookie(login, "POST /auth/login")
        changed = await _change_password(private, cookie, OLD_PASSWORD, OTHER_WAY_PASSWORD)
        assert changed.status_code == 200, f"setup: POST /auth/change-password must succeed: {changed.status_code} {changed.text}"

        inspected = await _inspect(private, token, "admin_setup")
        await _cli_set_active(private.engine, "changer", False)
        links = [(token, ADMIN_SETUP)]
        before = await _footprint(private.engine, user_id, links)
        response = await _setup(private, token, NEW_PASSWORD)
        after = await _footprint(private.engine, user_id, links)
        with_setup_password, with_its_password = await _sign_in(private, "changer", NEW_PASSWORD), await _sign_in(private, "changer", OTHER_WAY_PASSWORD)

        _assert_token_invalid(response, "POST /auth/setup with the setup link of an account that changed its password, inactive since: its holder must not take the account over")
        body = inspected.json() if inspected.status_code == 200 else {}
        assert (inspected.status_code, body.get("status"), body.get("purpose"), _details_shown(body)) == (200, "revoked", "admin_setup", {}), f"a change of password must retire the account's setup links: inspected right after, revoked and nothing more: {inspected.status_code} {inspected.text}"
        assert after == before and after[0].active is False, f"a refused setup must change nothing, the account still inactive: before {before}, after {after}"
        assert with_setup_password.status_code == 401, f"the refused setup's password must sign nothing in: {with_setup_password.status_code} {with_setup_password.text}"
        assert (with_its_password.status_code, _error_code(with_its_password)) == (403, "ACCOUNT_DISABLED"), f"the changed password must still be the account's, answered as for any inactive account: {with_its_password.status_code} {with_its_password.text}"
        print_success("retired by the change of password: revoked, refused once inactive")

    # red until A-42/A-43 — its user-demote-refused variant, changed by construction; its two other variants stay guards
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("action", "superuser_after"), NEITHER_ACTIVATION_NOR_PASSWORD)
    async def test_what_is_neither_an_activation_nor_a_password_leaves_the_link_working(self, private: _Private, pending: _Pending, commands: _Commands, action: str, superuser_after: bool) -> None:
        """SETUP-016, guard of SETUP-014: what is neither an activation nor a password leaves the pending administrator waiting, and its link working — ``./dev.py user demote``, refused (lot A-43: falsy, a line starting with ❌, nothing changed), a reset link issued and not spent, an expired reset link refused by POST /auth/password-reset (400 ``TOKEN_INVALID``, no password set): inspected, still ``valid`` for the account; POST /auth/setup with it → 200, the account active and still an administrator. The retirement is an activation's and a new password's only.

        Changed in A-42/A-43, by construction: ``./dev.py user demote`` demoted the pending administrator until A-43, and
        its setup made an ordinary account; it is refused now, red until A-43. ``./dev.py user deactivate`` of the account
        already inactive left the link working until A-43; it revokes it now, and left this guard for SETUP-017.
        """
        print_section(f"SETUP-016: {action}, and the setup link still works")
        await _leave_it_waiting(private, pending, action, commands)

        inspected = await _inspect(private, pending.token, "admin_setup")
        response = await _setup(private, pending.token, NEW_PASSWORD)
        state = await _account_state(private.engine, pending.user_id)

        body = inspected.json() if inspected.status_code == 200 else {}
        assert (inspected.status_code, body.get("status"), body.get("username")) == (200, "valid", ADMIN_USERNAME), f"after {action} the setup link must still be valid, for {ADMIN_USERNAME}: {inspected.status_code} {inspected.text}"
        assert response.status_code == 200, f"after {action} the setup link must still set the account up: {response.status_code} {response.text}"
        user = response.json().get("user") or {}
        assert (user.get("id"), user.get("is_active"), user.get("is_superuser")) == (pending.user_id, True, superuser_after), f"the setup activates the account, an administrator or not as {action} left it: {user}"
        assert (state.active, state.superuser) == (True, superuser_after), f"in the database: active {state.active}, superuser {state.superuser}"
        print_success("the link still valid, and it sets the account up")


# ============================================================================
# 6. THE SETUP LINK'S LIFECYCLE (lot A-42 + A-43) — IN-PROCESS
# ============================================================================


#: How the other setup link of the account was spent before a stray one was left live (SETUP-018): through the account's
#: setup, or retired when the account was set up another way (A-32).
SPENT_BEFORE = [pytest.param("set-up-through-it", id="set-up-through-another-link"), pytest.param("retired", id="its-links-retired")]


async def _is_pending(engine: AsyncEngine, user_id: int) -> bool:
    """Whether the account waits for its setup, as ``registration_service.is_pending_admin`` says — the notion behind the Users tab's ``pending_setup``."""
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        assert user is not None, f"no account {user_id} in the private database"
        return await registration_service.is_pending_admin(session, user)


async def _set_up_before_with_a_stray_link(engine: AsyncEngine, spent: str) -> tuple[int, str, str]:
    """The initial administrator of SETUP-018, as rows: ``veteran``, OLD_PASSWORD its own, set up through its setup link L1 — consumed by the account (``set-up-through-it``), or retired, the account set up another way (``retired``) —, a stray setup link L2 issued afterwards and left live, as the race of A-42 or an earlier 1.3 build leaves it, the account then deactivated by root. ``(its id, L1, L2)``.

    It ends on its promise: the account inactive, L1 spent, L2 valid.
    """
    user_id = await _add_user(engine, "veteran", password=OLD_PASSWORD, admin=True)
    first = await _issue(engine, ADMIN_SETUP, user_id=user_id, now=utcnow() - timedelta(hours=3))
    async with AsyncSession(engine) as session:
        if spent == "set-up-through-it":
            assert await consume_token(session, first.token, ADMIN_SETUP, consumed_by_user_id=user_id, now=utcnow() - timedelta(hours=2)) is not None, "setup: the account's setup spends L1"
        else:
            assert await retire_tokens(session, user_id=user_id, purpose=ADMIN_SETUP, now=utcnow() - timedelta(hours=2)) == 1, "setup: L1 is retired"
        await session.commit()
    stray = await _issue(engine, ADMIN_SETUP, user_id=user_id, now=utcnow() - timedelta(hours=1))
    async with AsyncSession(engine) as session:
        await session.execute(update(User).where(User.id == user_id).values(is_active=False))
        await session.commit()
    statuses = (await _status(engine, first.token, ADMIN_SETUP), await _status(engine, stray.token, ADMIN_SETUP))
    spent_status = TokenStatus.CONSUMED if spent == "set-up-through-it" else TokenStatus.REVOKED
    assert statuses == (spent_status, TokenStatus.VALID) and (await _account_state(engine, user_id)).active is False, f"setup: the account inactive, L1 {spent_status.value} and L2 valid: {statuses}"
    return user_id, first.token, stray.token


class TestTheSetupLinkLifecycle:
    """Lot A-42 + A-43: a stray setup link of an account set up before is refused and retired; ``./dev.py user deactivate`` revokes the pending administrator's link, and ``./dev.py user setup-link`` gives it a new one. In-process, the commands included."""

    # red until A-42/A-43
    @pytest.mark.asyncio
    async def test_user_deactivate_revokes_the_link_and_setup_link_gives_a_new_one(self, private: _Private, pending: _Pending, commands: _Commands) -> None:
        """SETUP-017 (A-43; SETUP-016's ``user-deactivate`` variant until A-43, when the link kept working): ``./dev.py user deactivate`` on the pending administrator, already inactive, answers truthy and revokes its live setup link — inspected, ``revoked`` and nothing more —; POST /auth/setup with it and a password that meets the rules → 400 ``TOKEN_INVALID``, and nothing changes: the account inactive, its password and session version as they were, and that password signs nothing in (401). The account still waits for its setup — revoked, not retired —: ``./dev.py user setup-link`` prints a new link, and POST /auth/setup with it → 200, the account active and an administrator."""
        print_section("SETUP-017: user deactivate on the pending administrator, then user setup-link")
        deactivated, out = await commands.run("cmd_set_user_active", ADMIN_USERNAME, False)
        assert deactivated, f"setup: ./dev.py user deactivate must succeed on the pending administrator: it answered {deactivated!r}: {out!r}"
        links = [(pending.token, ADMIN_SETUP)]

        inspected = await _inspect(private, pending.token, "admin_setup")
        before = await _footprint(private.engine, pending.user_id, links)
        refused = await _setup(private, pending.token, NEW_PASSWORD)
        after = await _footprint(private.engine, pending.user_id, links)
        with_refused_password = await _sign_in(private, ADMIN_USERNAME, NEW_PASSWORD)
        waits = await _is_pending(private.engine, pending.user_id)
        issued, printed = await commands.run("cmd_setup_link")
        token = _printed_setup_token(printed)
        response = await _setup(private, token, ANOTHER_PASSWORD) if token else None
        state = await _account_state(private.engine, pending.user_id)

        body = inspected.json() if inspected.status_code == 200 else {}
        assert (inspected.status_code, body.get("status"), body.get("purpose"), _details_shown(body)) == (200, "revoked", "admin_setup", {}), f"red until A-43: ./dev.py user deactivate must revoke the pending administrator's live setup link: inspected {inspected.status_code} {inspected.text}"
        _assert_token_invalid(refused, "POST /auth/setup with the link ./dev.py user deactivate revoked")
        assert after == before and after[0].active is False, f"the refused setup must change nothing, the account still inactive: before {before}, after {after}"
        assert with_refused_password.status_code == 401, f"the refused setup's password must sign nothing in: {with_refused_password.status_code} {with_refused_password.text}"
        assert waits, "revoked, not retired: the account must still wait for its setup"
        assert issued and token, f"./dev.py user setup-link must print a new link for the account still waiting: it answered {issued!r}: {printed!r}"
        assert response is not None and response.status_code == 200, f"the new link must set the account up: {response.status_code if response is not None else None} {response.text if response is not None else ''}"
        assert (state.active, state.superuser) == (True, True), f"set up through the new link: active {state.active}, superuser {state.superuser}"
        print_success("revoked by user deactivate; a new link of user setup-link sets it up")

    # red until A-42/A-43
    @pytest.mark.asyncio
    @pytest.mark.parametrize("spent", SPENT_BEFORE)
    async def test_a_stray_setup_link_of_an_account_set_up_before_is_refused_and_retired(self, private: _Private, spent: str) -> None:
        """SETUP-018 (A-42): rows written directly, as the race of A-42 or an earlier 1.3 build leaves them — the initial administrator set up through its setup link L1 (consumed by the account; or its links retired, set up another way), OLD_PASSWORD its own, a stray setup link L2 left live, the account then deactivated by root (``_set_up_before_with_a_stray_link``). POST /auth/setup with L2 and a password that meets the rules → 400 ``TOKEN_INVALID``, and nothing changes: the account inactive, its password hash and session version as they were — its old password still its own (403 ``ACCOUNT_DISABLED``), the setup's signs nothing in (401) —, L1 as it was; and L2 is retired: inspected, ``revoked`` and nothing more, its row consumed and revoked, without a consumer. Today: 200, the account re-activated with the password of whoever held L2."""
        print_section(f"SETUP-018: the stray setup link of an account set up before ({spent})")
        user_id, first, stray = await _set_up_before_with_a_stray_link(private.engine, spent)
        before = await _footprint(private.engine, user_id, [(first, ADMIN_SETUP)])

        response = await _setup(private, stray, NEW_PASSWORD)

        after = await _footprint(private.engine, user_id, [(first, ADMIN_SETUP)])
        inspected = await _inspect(private, stray, "admin_setup")
        record = await _token_record(private.engine, stray, ADMIN_SETUP)
        with_setup_password, with_its_password = await _sign_in(private, "veteran", NEW_PASSWORD), await _sign_in(private, "veteran", OLD_PASSWORD)

        _assert_token_invalid(response, f"red until A-42: POST /auth/setup with a stray setup link of an account set up before ({spent})")
        assert after == before and after[0].active is False, f"the refused setup must change nothing — the account inactive, its password hash and session version, L1 —: before {before}, after {after}"
        body = inspected.json() if inspected.status_code == 200 else {}
        assert (inspected.status_code, body.get("status"), body.get("purpose"), _details_shown(body)) == (200, "revoked", "admin_setup", {}), f"the refused stray link must be retired: inspected, revoked and nothing more: {inspected.status_code} {inspected.text}"
        retired = (record.consumed_at is not None, record.revoked_at is not None, record.consumed_by_user_id)
        assert retired == (True, True, None), f"retired: consumed and revoked at once, without a consumer — (consumed, revoked, consumed_by_user_id) {retired}"
        assert with_setup_password.status_code == 401, f"the refused setup's password must sign nothing in: {with_setup_password.status_code} {with_setup_password.text}"
        assert (with_its_password.status_code, _error_code(with_its_password)) == (403, "ACCOUNT_DISABLED"), f"the old password must still be the account's, answered as for any inactive account: {with_its_password.status_code} {with_its_password.text}"
        print_success("TOKEN_INVALID; nothing changed; the stray link retired")
