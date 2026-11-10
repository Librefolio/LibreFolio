"""C-54 over HTTP: ``user.whats_new`` in the answers that carry the account, and ``POST /auth/whats-new/seen`` (release 1.3, workstream A, lot C-54 — A11 of the plan; the coordinator's GO and its correction, 17/10).

Until C-54 ``users.last_seen_version`` is neither read nor written, and ``AuthUserResponse`` says nothing of it. The
contract over HTTP — the service's own rules (the base release of a version, the comparison by release, the switch, the
unknown running release) are pinned in ``test_services/test_whats_new_service.py``, WN-001 to WN-010:

1. ``AuthUserResponse.whats_new`` (``schemas/auth.py``): ``WhatsNewRead {since, release}``, or null, decided by the
   server from ``whats_new_service.pending_for(user)`` — never the raw column — in the answers of ``POST /auth/register``,
   ``POST /auth/login``, ``GET /auth/me`` and ``POST /auth/setup`` (``api/v1/auth.py``, where each builds
   ``AuthUserResponse`` today).
   - A fresh account has null: ``create_user`` wrote the running release into its row — in the registration's answer,
     its login's and its ``/auth/me``'s.
   - An account written as a row with ``last_seen_version`` NULL — from before C-54 — has
     ``{"since": null, "release": <running>}``; with an older release, ``{"since": <it>, "release": <running>}``: at its
     login, and at every ``/auth/me`` — a session that outlived the update learns it at the next load —, which marks
     nothing seen: only the app's POST does.
   - ``LIBREFOLIO_DISABLE_WHATS_NEW=1`` makes it null — the lanes run with it, their accounts all NULL —, and removing
     it brings it back (a barrier): the switch hides, it marks nothing.
2. ``POST /api/v1/auth/whats-new/seen``: a signed-in account only — 401 without a session, nothing written —; 204, the
   caller's ``last_seen_version`` the running release (``mark_seen``), nobody else's; ``/auth/me`` then answers null.
   Again: 204, nothing changes. A version the client sends, in a body or in the query, is never taken (WN-API-07).

Where it runs: in-process only, never on the lane. Each case has a private SQLite file under ``tmp_path`` (NullPool,
disposed at teardown) with the schema and default settings of a new install, served by the real auth router mounted
under the API prefix as ``api/v1/router.py`` mounts it, its ``get_session_generator`` opening sessions on that file. The
new route is expected on that router (``backend/app/api/v1/auth.py``), as every ``/auth`` route. The accounts of a scene
are rows written directly, with the ``last_seen_version`` the scene needs: the lane's shared database is no place for
them. The running version is ``backend.app.config.get_version`` patched through ``monkeypatch`` for every case:
``v1.3.0-7-gabc1234`` — git describe, seven commits after the tag ``v1.3.0`` —, release ``1.3.0``; the routes read it
through ``whats_new_service`` at each request, so a module that binds ``get_version`` by name at import answers the
checkout's own release instead (WN-002 of the services file says why). Process-wide state is replaced through
``monkeypatch`` and put back, as ``test_username_rules_api.py`` does: bcrypt at cost 4 with a private dummy hash of cost
4; the two limiters of ``login_throttle`` by fresh ones of the shipped size; the session cookie's Secure mode on ``auto``
(plain HTTP here; the cookie is read from ``Set-Cookie`` and sent explicitly); ``get_async_engine`` a tripwire. The
switch, and the accounts and email variables of the shell, are removed: email is off, so registration verifies nothing.
Every request comes from one documentation address of this file's own and carries no forwarding header. «Nothing
written» is every row of every table, ``sqlite_sequence`` included, read by SQLite from the file before and after;
after a write, «nothing else» is the same comparison with ``users.last_seen_version`` and ``users.updated_at`` set aside
— ``updated_at`` is the implementer's call —, every account's ``last_seen_version`` compared on its own. Nothing waits.

Red until C-54, each test on its own, at its first assertion: today the answers carry no ``user.whats_new`` (WN-API-01
to 04) and ``POST /auth/whats-new/seen`` is a 404 (WN-API-05 to 07). WN-API-04 — the setup answer — and WN-API-07 — a
client's version never taken — extend the brief's list with what the contract names: drop them if the coordinator does.

Reviewer E's note 1 on C-54 — ``mark_seen`` monotonic (the coordinator's contract, 17/10; the service's side, with the
window of the write lock, is WN-MONO-01 to 06 of the services file) — adds section 3 over HTTP: ``POST
/auth/whats-new/seen`` by an account that saw a release newer than the running one is 204 and writes nothing — its
``last_seen_version`` kept, every row as it was — (WNAPI-MONO-01, NEW, red until the cure: today the row is lowered to
the running release); ``GET /auth/me`` then still answers null (WNAPI-MONO-02, a GUARD, green today and after); and
after the next upgrade the release it saw is not shown again (WNAPI-MONO-03, NEW, red until the cure — the harm of
WNAPI-MONO-01 as the user meets it, an extension of the brief's list: drop it if the coordinator does).
"""

from __future__ import annotations

import contextlib
import functools
import os
import sqlite3
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import bcrypt
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app import config as app_config
from backend.app.api.v1 import auth as auth_api
from backend.app.config import API_V1_PREFIX
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountTokenPurpose, GlobalSetting, User
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service, login_throttle, token_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.email import flows as email_flows
from backend.app.services.email import verification as email_verification
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

# =============================================================================
# THE CONTRACT'S VALUES — a different decision is an edit here
# =============================================================================

#: The hidden switch (D-A7): the lanes run with it, their accounts all NULL.
SWITCH = "LIBREFOLIO_DISABLE_WHATS_NEW"
#: The running version of every case, as backend.app.config.get_version answers it here, and its release.
RUNNING_VERSION = "v1.3.0-7-gabc1234"
RUNNING_RELEASE = "1.3.0"
#: A release before the running one: not the lane's own 1.2.1, so an unpatched version shows in a failure.
OLDER_RELEASE = "1.2.0"
#: A release after the running one — an account that saw it before a downgrade, or on a newer worker during a rolling
#: update —, and the version the instance runs once it is upgraded to it.
NEWER_RELEASE = "1.4.0"
NEWER_VERSION = "v1.4.0"
#: The last_seen_version of an account behind the running release: NULL — from before C-54 — or an older release.
BEHIND = [pytest.param(None, id="null-from-before-c54"), pytest.param(OLDER_RELEASE, id="an-older-release")]
#: What a client might send as the version it saw: never taken.
FORGED_VERSION = "9.9.9"

REGISTER = f"{API_V1_PREFIX}/auth/register"
LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
SETUP = f"{API_V1_PREFIX}/auth/setup"
SEEN = f"{API_V1_PREFIX}/auth/whats-new/seen"
COOKIE = auth_api.SESSION_COOKIE_NAME
BASE_URL = "http://test"
TIMEOUT = 30.0
#: Where the requests come from, as the app sees them (the ASGI ``client``): a documentation address of this file's own.
CLIENT = ("198.51.100.154", 42154)
#: A password that meets the rules (decision 37): every account of a scene signs in with it.
PASSWORD = "Whats-New-Api-Pass-2026!"
#: A write's «nothing else»: these columns set aside — the one written, and updated_at, the implementer's call.
UPDATED_AT = "users.updated_at"
MARKED = ("users.last_seen_version", UPDATED_AT)
#: Removed before every test: the switch, and what changes what registration, the sign-in or an email decide.
INHERITED_PREFIXES = ("LIBREFOLIO_SMTP_", "LIBREFOLIO_ADMIN_")
INHERITED_VARIABLES = (SWITCH, "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BILLING_URL", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_LOGIN_LIMIT")


# =============================================================================
# FIXTURES: THE VARIABLES, THE RUNNING VERSION, THE PROCESS'S STATE, THE PRIVATE INSTANCE
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the switch, accounts and email variables of the shell that started the run: the lanes set the switch."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def running_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """``backend.app.config.get_version`` answers ``RUNNING_VERSION`` in every case: never the checkout's own version."""
    monkeypatch.setattr(app_config, "get_version", lambda: RUNNING_VERSION)


@functools.cache
def _cheap_dummy_hash() -> str:
    """This module's dummy hash: bcrypt of cost 4 of a random password, computed once, never matched."""
    return bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt(rounds=4)).decode()


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's private one")


def _fresh(shipped: SlidingWindowLimiter) -> SlidingWindowLimiter:
    """A limiter of the shipped one's size, holding no count."""
    return SlidingWindowLimiter(shipped.limit, shipped.window_seconds)


@pytest.fixture
def process_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at cost 4 with a private dummy hash; fresh login limiters; the cookie's Secure mode on ``auto``; ``get_async_engine`` a tripwire."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_service, "_dummy_password_hash", _cheap_dummy_hash)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")
    monkeypatch.setattr(login_throttle, "LOGIN_BY_IDENTIFIER", _fresh(login_throttle.LOGIN_BY_IDENTIFIER))
    monkeypatch.setattr(login_throttle, "LOGIN_BY_ADDRESS", _fresh(login_throttle.LOGIN_BY_ADDRESS))
    for module in (db_session, email_flows, email_verification):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire, raising=False)


@dataclass(frozen=True)
class _Private:
    """An instance of one case: the auth router, every session on ``engine``, the file at ``db_path``."""

    engine: AsyncEngine
    app: FastAPI
    db_path: Path


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
async def private(tmp_path: Path, process_state: None) -> AsyncIterator[_Private]:
    """A private SQLite file under tmp_path — the schema and default settings a new install starts with, no account — served by the auth router; disposed at the end."""
    db_path = tmp_path / "whats-new-api.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_app(engine), db_path=db_path)
    finally:
        await engine.dispose()


# =============================================================================
# HELPERS — the database, read by SQLite, and the scenes as rows
# =============================================================================

Rows = dict[str, list[tuple[Any, ...]]]


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


def _address(prefix: str) -> str:
    """An address nobody has: ``prefix``, a tag of its own, at ``example.com``."""
    return f"{prefix}.{_tag()}@example.com"


def _rows(db_path: Path, ignoring: tuple[str, ...] = ()) -> Rows:
    """Every row of every table, ``sqlite_sequence`` included, read by SQLite from the file: what «nothing written»
    compares. A column named in ``ignoring``, as ``table.column``, reads NULL in every row."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        tables = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {table: _table_rows(conn, table, ignoring) for table in tables}


def _table_rows(conn: sqlite3.Connection, table: str, ignoring: tuple[str, ...]) -> list[tuple[Any, ...]]:
    columns = [info[1] for info in conn.execute(f'PRAGMA table_info("{table}")')]
    selected = ", ".join("NULL" if f"{table}.{column}" in ignoring else f'"{column}"' for column in columns)
    return sorted(conn.execute(f'SELECT {selected} FROM "{table}"').fetchall(), key=repr)


def _changed(before: Rows, after: Rows) -> list[str]:
    """The tables whose rows differ between ``before`` and ``after``."""
    return sorted(table for table in set(before) | set(after) if before.get(table) != after.get(table))


def _last_seen(db_path: Path) -> dict[int, Optional[str]]:
    """Every account's ``last_seen_version``, by id, read by SQLite from the file: only what was committed."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        return dict(conn.execute("SELECT id, last_seen_version FROM users").fetchall())


async def _add_user(engine: AsyncEngine, *, email: str, last_seen_version: Optional[str], active: bool = True, superuser: bool = False) -> int:
    """An account written as a row — as an install from before C-54 holds one (NULL), or as the scene needs it —, a fresh
    name, the address ``email``, a real bcrypt hash of ``PASSWORD`` (cost 4). Its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=f"member_{_tag()}", email=email, hashed_password=auth_service.hash_password(PASSWORD), is_active=active, is_superuser=superuser, last_seen_version=last_seen_version)
        session.add(user)
        await session.commit()
    return user.id


async def _registration_open(engine: AsyncEngine) -> None:
    """``registration_mode`` = ``open``, on the row the startup seeded: a registration needs no invitation."""
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, "registration_mode")
        assert row is not None, "setup: initialize_global_settings seeded no registration_mode row"
        row.value = "open"
        session.add(row)
        await session.commit()


async def _setup_link(engine: AsyncEngine, user_id: int) -> str:
    """A live setup link of ``user_id``, issued by the token service directly and committed: the scene is set without the route under test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, AccountTokenPurpose.ADMIN_SETUP, user_id=user_id)
        await session.commit()
    return issued.token


# =============================================================================
# HELPERS — requests, and reading the answers
# =============================================================================


async def _request(private: _Private, method: str, path: str, *, cookie: Optional[str] = None, json: Any = None, params: Optional[dict[str, str]] = None) -> httpx.Response:
    """One request from a client of its own at ``CLIENT``: no cookie jar, the session cookie, if any, sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    transport = httpx.ASGITransport(app=private.app, client=CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as client:
        return await client.request(method, path, json=json, params=params, headers=headers)


async def _register(private: _Private, username: str, email: str) -> httpx.Response:
    return await _request(private, "POST", REGISTER, json={"username": username, "email": email, "password": PASSWORD})


async def _login(private: _Private, identifier: str) -> httpx.Response:
    return await _request(private, "POST", LOGIN, json={"username": identifier, "password": PASSWORD})


async def _me(private: _Private, cookie: str) -> httpx.Response:
    return await _request(private, "GET", ME, cookie=cookie)


def _session_cookies(response: httpx.Response) -> list[str]:
    """The values the answer's ``Set-Cookie`` headers give the session cookie, found by name."""
    values = []
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE:
            values.append(value.strip())
    return values


def _account_id(response: httpx.Response) -> Optional[int]:
    """``user.id`` of a 200 or a 201; None for any other answer."""
    if response.status_code not in (200, 201):
        return None
    return response.json().get("user", {}).get("id")


@dataclass(frozen=True)
class SignedIn:
    """An account written as a row and signed in: its id, its session cookie, and its login's answer."""

    user_id: int
    cookie: str
    login: httpx.Response


async def _signed_in(private: _Private, *, last_seen_version: Optional[str]) -> SignedIn:
    """An account written as a row with ``last_seen_version``, signed in through ``POST /auth/login`` with its address. It
    ends on its promise: a 200 as that account, one session cookie."""
    email = _address("member")
    user_id = await _add_user(private.engine, email=email, last_seen_version=last_seen_version)
    login = await _login(private, email)
    cookies = _session_cookies(login)
    assert _account_id(login) == user_id and len(cookies) == 1 and cookies[0], f"setup: #{user_id} signs in with its address: {login.status_code} {login.text}"
    return SignedIn(user_id=user_id, cookie=cookies[0], login=login)


def _pending(since: Optional[str]) -> dict[str, Optional[str]]:
    """``user.whats_new`` of an account behind the running release: since its own release — None for NULL —, the running one."""
    return {"since": since, "release": RUNNING_RELEASE}


def _assert_whats_new(response: httpx.Response, expected: Optional[dict[str, Optional[str]]], request: str) -> None:
    """The answer carries the account, and its ``user.whats_new`` is ``expected``: null, or ``{since, release}``."""
    assert response.status_code in (200, 201), f"setup: {request} must answer with the account: {response.status_code} {response.text}"
    user = response.json().get("user") or {}
    assert "whats_new" in user, f"red until C-54: {request}: the answer's user must carry whats_new — {expected!r} here —, decided by the server; it carries {sorted(user)}"
    assert user["whats_new"] == expected, f"{request}: user.whats_new must be {expected!r} — the running version {RUNNING_VERSION!r}, read through backend.app.config.get_version at each request —; got {user['whats_new']!r}"


# =============================================================================
# 1. user.whats_new IN THE ANSWERS — register, login, /auth/me, setup
# =============================================================================


# NEW — red until C-54
@pytest.mark.asyncio
async def test_a_fresh_account_has_nothing_new_to_see(private: _Private) -> None:
    """WN-API-01 — C-54, NEW, red until C-54 (today the answers carry no ``user.whats_new``): an instance with an account, registration ``open``. ``POST /auth/register`` of a fresh account is 201 with ``user.whats_new`` null, and its row holds the running release ``1.3.0`` (``create_user`` wrote it); its ``POST /auth/login`` and its ``GET /auth/me`` answer ``user.whats_new`` null too: a new account never sees the modal."""
    print_section("WN-API-01: a fresh account has nothing new to see")
    await _add_user(private.engine, email=_address("seed"), last_seen_version=None)
    await _registration_open(private.engine)
    email = _address("newcomer")

    registered = await _register(private, f"newcomer_{_tag()}", email)

    _assert_whats_new(registered, None, "POST /auth/register of a fresh account")
    user_id = _account_id(registered)
    stored = _last_seen(private.db_path).get(user_id)
    assert user_id is not None and stored == RUNNING_RELEASE, f"the new account's row must hold the running release {RUNNING_RELEASE!r}: #{user_id} holds {stored!r}"
    login = await _login(private, email)
    cookies = _session_cookies(login)
    assert _account_id(login) == user_id and len(cookies) == 1, f"setup: the new account signs in with its address: {login.status_code} {login.text}"
    _assert_whats_new(login, None, "POST /auth/login of a fresh account")
    _assert_whats_new(await _me(private, cookies[0]), None, "GET /auth/me of a fresh account")
    print_success(f"#{user_id}: last_seen_version {stored!r}, whats_new null in the three answers")


# NEW — red until C-54
@pytest.mark.asyncio
@pytest.mark.parametrize("stored", BEHIND)
async def test_an_account_behind_the_running_release_has_something_new(private: _Private, stored: Optional[str]) -> None:
    """WN-API-02 — C-54, NEW, red until C-54 (today the answers carry no ``user.whats_new``): an account written as a row with ``last_seen_version`` NULL — from before C-54 — or an older release ``1.2.0``. Its ``POST /auth/login`` answers ``user.whats_new`` ``{"since": null, "release": "1.3.0"}``, or ``{"since": "1.2.0", "release": "1.3.0"}``; ``GET /auth/me`` the same, twice — a session that outlived the update learns it at the next load —, and asking writes nothing: every row of every table as it was, the account's NULL or ``1.2.0`` kept — nothing is marked seen until the app says so."""
    print_section(f"WN-API-02: an account with last_seen_version {stored!r}")
    member = await _signed_in(private, last_seen_version=stored)
    expected = _pending(stored)

    _assert_whats_new(member.login, expected, f"POST /auth/login of an account with last_seen_version {stored!r}")

    before = _rows(private.db_path)
    for attempt in ("first", "second"):
        _assert_whats_new(await _me(private, member.cookie), expected, f"GET /auth/me, the {attempt} time, of an account with last_seen_version {stored!r}")
    assert _changed(before, _rows(private.db_path)) == [], f"GET /auth/me reads: it must write nothing, nothing marked seen: {_changed(before, _rows(private.db_path))}"
    assert _last_seen(private.db_path)[member.user_id] == stored, f"the account keeps last_seen_version {stored!r} until the app marks it seen"
    print_success(f"whats_new {expected} at the login and at every /auth/me")


# NEW — red until C-54
@pytest.mark.asyncio
async def test_the_switch_leaves_whats_new_null(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """WN-API-03 — C-54, NEW, red until C-54 (today the answers carry no ``user.whats_new``): ``LIBREFOLIO_DISABLE_WHATS_NEW=1`` — the lanes run with it —, an account written as a row with NULL: ``POST /auth/login`` and ``GET /auth/me`` answer ``user.whats_new`` null, and the row keeps its NULL — off is not «seen». Barrier: the variable removed, the next ``GET /auth/me`` answers ``{"since": null, "release": "1.3.0"}`` — the null was the switch's."""
    monkeypatch.setenv(SWITCH, "1")
    member = await _signed_in(private, last_seen_version=None)

    _assert_whats_new(member.login, None, f"POST /auth/login with {SWITCH}=1")

    _assert_whats_new(await _me(private, member.cookie), None, f"GET /auth/me with {SWITCH}=1")
    assert _last_seen(private.db_path)[member.user_id] is None, f"{SWITCH} hides what is new, it marks nothing seen: the row must keep its NULL"
    monkeypatch.delenv(SWITCH)
    _assert_whats_new(await _me(private, member.cookie), _pending(None), f"barrier: GET /auth/me, {SWITCH} removed")


# NEW — red until C-54 (an extension of the brief's list: drop it if the coordinator does)
@pytest.mark.asyncio
async def test_the_setup_answer_carries_whats_new(private: _Private) -> None:
    """WN-API-04 — C-54, NEW, red until C-54 (today the answer carries no ``user.whats_new``); the contract names the setup answer among those that carry it (an extension of the brief's list: drop it if the coordinator does). F02's administrator waiting for its setup, written as a row — inactive, an administrator, ``last_seen_version`` ``1.2.0`` —, and a live setup link issued by the token service: ``POST /auth/setup`` with it is 200 as that account, ``user.whats_new`` ``{"since": "1.2.0", "release": "1.3.0"}``, as its login's would be."""
    waiting = await _add_user(private.engine, email=_address("admin"), last_seen_version=OLDER_RELEASE, active=False, superuser=True)
    token = await _setup_link(private.engine, waiting)

    response = await _request(private, "POST", SETUP, json={"token": token, "new_password": PASSWORD})

    assert _account_id(response) == waiting, f"setup: POST /auth/setup with a live link must sign the waiting administrator #{waiting} in: {response.status_code} {response.text}"
    _assert_whats_new(response, _pending(OLDER_RELEASE), "POST /auth/setup of an administrator with last_seen_version 1.2.0")


# =============================================================================
# 2. POST /auth/whats-new/seen
# =============================================================================


# NEW — red until C-54
@pytest.mark.asyncio
async def test_marking_seen_needs_a_session(private: _Private) -> None:
    """WN-API-05 — C-54, NEW, red until C-54 (today 404: the route does not exist): an account with NULL, signed in. ``POST /auth/whats-new/seen`` without a session cookie is 401 and writes nothing: every row of every table as it was. Barrier: the same request with the account's cookie is 204 — the 401 was the missing session's."""
    print_section("WN-API-05: POST /auth/whats-new/seen without a session")
    member = await _signed_in(private, last_seen_version=None)
    before = _rows(private.db_path)

    refused = await _request(private, "POST", SEEN)

    assert refused.status_code == 401, f"red until C-54: POST /auth/whats-new/seen without a session must be 401: got {refused.status_code} {refused.text}"
    assert _changed(before, _rows(private.db_path)) == [], f"a refused request must write nothing: {_changed(before, _rows(private.db_path))}"
    allowed = await _request(private, "POST", SEEN, cookie=member.cookie)
    assert allowed.status_code == 204, f"barrier: the same request with the account's cookie must be 204: {allowed.status_code} {allowed.text}"
    print_success("401 without a session, nothing written; 204 with one")


# NEW — red until C-54
@pytest.mark.asyncio
async def test_marking_seen_writes_the_running_release_once(private: _Private) -> None:
    """WN-API-06 — C-54, NEW, red until C-54 (today 404: the route does not exist): an account with NULL, signed in — its login answered ``{"since": null, "release": "1.3.0"}`` —, and another account with NULL. ``POST /auth/whats-new/seen`` with the account's cookie is 204: its row holds the running release ``1.3.0``, the other's is still NULL, nothing else is written (``updated_at`` aside: the implementer's call), and ``GET /auth/me`` then answers ``user.whats_new`` null. Again — idempotent —: 204, nothing changes (``updated_at`` aside), still null."""
    print_section("WN-API-06: POST /auth/whats-new/seen, twice")
    member = await _signed_in(private, last_seen_version=None)
    await _add_user(private.engine, email=_address("bystander"), last_seen_version=None)
    seen_before, rows_before = _last_seen(private.db_path), _rows(private.db_path, ignoring=MARKED)

    first = await _request(private, "POST", SEEN, cookie=member.cookie)

    assert first.status_code == 204, f"red until C-54: POST /auth/whats-new/seen, signed in, must be 204: got {first.status_code} {first.text}"
    _assert_whats_new(member.login, _pending(None), "precondition: the login's answer, before POST /auth/whats-new/seen")
    assert _last_seen(private.db_path) == {**seen_before, member.user_id: RUNNING_RELEASE}, f"the caller's last_seen_version must be the running release {RUNNING_RELEASE!r}, nobody else's: before {seen_before}, after {_last_seen(private.db_path)}"
    assert _changed(rows_before, _rows(private.db_path, ignoring=MARKED)) == [], f"marking seen writes last_seen_version and nothing else (updated_at aside): {_changed(rows_before, _rows(private.db_path, ignoring=MARKED))}"
    _assert_whats_new(await _me(private, member.cookie), None, "GET /auth/me after POST /auth/whats-new/seen")
    rows_seen = _rows(private.db_path, ignoring=(UPDATED_AT,))
    second = await _request(private, "POST", SEEN, cookie=member.cookie)
    assert second.status_code == 204, f"idempotent: a second POST /auth/whats-new/seen must be 204 too: {second.status_code} {second.text}"
    assert _changed(rows_seen, _rows(private.db_path, ignoring=(UPDATED_AT,))) == [], f"idempotent: a second POST changes nothing (updated_at aside): {_changed(rows_seen, _rows(private.db_path, ignoring=(UPDATED_AT,)))}"
    _assert_whats_new(await _me(private, member.cookie), None, "GET /auth/me after the second POST /auth/whats-new/seen")
    print_success(f"#{member.user_id}: NULL → {RUNNING_RELEASE!r}, then nothing new; a second POST changes nothing")


# NEW — red until C-54 (an extension of the brief's list: drop it if the coordinator does)
@pytest.mark.asyncio
async def test_marking_seen_never_takes_a_version_from_the_client(private: _Private) -> None:
    """WN-API-07 — C-54, NEW, red until C-54 (today 404: the route does not exist); the contract's «never a client value», over HTTP (an extension of the brief's list: drop it if the coordinator does). An account with NULL, signed in: ``POST /auth/whats-new/seen`` carrying ``9.9.9`` as ``version``, ``release``, ``since`` and ``last_seen_version``, in a JSON body and in the query, is 204, and the row holds the running release ``1.3.0`` — the server's, never the client's."""
    member = await _signed_in(private, last_seen_version=None)
    forged = {"version": FORGED_VERSION, "release": FORGED_VERSION, "since": FORGED_VERSION, "last_seen_version": FORGED_VERSION}

    response = await _request(private, "POST", SEEN, cookie=member.cookie, json=forged, params=forged)

    assert response.status_code == 204, f"red until C-54: POST /auth/whats-new/seen, signed in, must be 204 whatever the client sends: got {response.status_code} {response.text}"
    stored = _last_seen(private.db_path)[member.user_id]
    assert stored == RUNNING_RELEASE, f"the server writes its own running release {RUNNING_RELEASE!r}, never a version the client sends ({FORGED_VERSION!r}): the row holds {stored!r}"


# =============================================================================
# 3. NEVER BACKWARDS — E's note 1 on C-54, over HTTP
# =============================================================================


def _whats_new_in(response: httpx.Response, request: str) -> Any:
    """``user.whats_new`` of a 200 that carries the account."""
    user = (response.json().get("user") or {}) if response.status_code == 200 else {}
    assert "whats_new" in user, f"setup: {request} must answer 200 with the account and its whats_new: {response.status_code} {response.text}"
    return user["whats_new"]


# NEW — red until E's note 1 on C-54
@pytest.mark.asyncio
async def test_marking_seen_on_an_older_release_writes_nothing(private: _Private) -> None:
    """WNAPI-MONO-01 — E's note 1 on C-54, NEW, red until the cure (today the route lowers the row to the running ``1.3.0``): an account written as a row with ``last_seen_version`` ``1.4.0`` — it saw 1.4.0 before a downgrade, or on a newer worker during a rolling update —, signed in — its login answered ``user.whats_new`` null —, and another account with NULL. ``POST /auth/whats-new/seen`` with the account's cookie, served by a worker running ``v1.3.0-7-gabc1234``, is 204 and writes nothing: the account keeps ``1.4.0``, the last release it saw — every row of every table as it was, ``updated_at`` included."""
    print_section(f"WNAPI-MONO-01: POST /auth/whats-new/seen by an account that saw {NEWER_RELEASE}, running {RUNNING_RELEASE}")
    member = await _signed_in(private, last_seen_version=NEWER_RELEASE)
    await _add_user(private.engine, email=_address("bystander"), last_seen_version=None)
    _assert_whats_new(member.login, None, f"precondition: the login of an account that saw {NEWER_RELEASE!r}")
    before = _rows(private.db_path)

    response = await _request(private, "POST", SEEN, cookie=member.cookie)

    assert response.status_code == 204, f"POST /auth/whats-new/seen, signed in, must be 204: got {response.status_code} {response.text}"
    stored = _last_seen(private.db_path)[member.user_id]
    assert stored == NEWER_RELEASE, f"red until E's note 1 on C-54: the account saw {NEWER_RELEASE!r}; a worker running {RUNNING_RELEASE!r} must never lower it — after the next upgrade the account would see again what it saw —: the row holds {stored!r}"
    assert _changed(before, _rows(private.db_path)) == [], f"nothing to mark: every row of every table as it was, updated_at included: {_changed(before, _rows(private.db_path))}"
    print_success(f"#{member.user_id}: 204, {NEWER_RELEASE!r} kept, nothing written")


# GUARD — green today, must stay green
@pytest.mark.asyncio
async def test_after_marking_seen_on_an_older_release_nothing_is_new(private: _Private) -> None:
    """WNAPI-MONO-02 — E's note 1 on C-54, GUARD (green today and after the cure): an account written as a row with ``last_seen_version`` ``1.4.0``, signed in. After its ``POST /auth/whats-new/seen`` — 204 — on a worker running ``v1.3.0-7-gabc1234``, ``GET /auth/me`` answers ``user.whats_new`` null: the modal does not come back there. Today null because the row now holds the running release; after the cure because it keeps ``1.4.0``. Barrier: an account with NULL, signed in beside it, has ``{"since": null, "release": "1.3.0"}`` at the same moment — the null is the account's own, not the instance's."""
    member = await _signed_in(private, last_seen_version=NEWER_RELEASE)
    witness = await _signed_in(private, last_seen_version=None)

    response = await _request(private, "POST", SEEN, cookie=member.cookie)

    assert response.status_code == 204, f"POST /auth/whats-new/seen, signed in, must be 204: got {response.status_code} {response.text}"
    _assert_whats_new(await _me(private, member.cookie), None, f"GET /auth/me after POST /auth/whats-new/seen of an account that saw {NEWER_RELEASE!r}")
    _assert_whats_new(await _me(private, witness.cookie), _pending(None), "barrier: GET /auth/me of an account with NULL, at the same moment")


# NEW — red until E's note 1 on C-54 (an extension of the brief's list: drop it if the coordinator does)
@pytest.mark.asyncio
async def test_after_the_next_upgrade_the_release_seen_is_not_shown_again(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """WNAPI-MONO-03 — E's note 1 on C-54, NEW, red until the cure (today ``{"since": "1.3.0", "release": "1.4.0"}``: the 1.4.0 chapter again); the harm of WNAPI-MONO-01 as the user meets it — an extension of the brief's list: drop it if the coordinator does. An account written as a row with ``last_seen_version`` ``1.4.0``, signed in, closes the modal on a worker running ``v1.3.0-7-gabc1234`` — ``POST /auth/whats-new/seen``, 204 —; then the instance runs ``v1.4.0``, the rolling update done or the upgrade back: ``GET /auth/me`` answers ``user.whats_new`` null — it saw 1.4.0 already. Barrier: an account that saw ``1.3.0``, signed in beside it, has ``{"since": "1.3.0", "release": "1.4.0"}`` at the same moment — the upgrade is seen."""
    member = await _signed_in(private, last_seen_version=NEWER_RELEASE)
    witness = await _signed_in(private, last_seen_version=RUNNING_RELEASE)
    closed = await _request(private, "POST", SEEN, cookie=member.cookie)
    assert closed.status_code == 204, f"setup: POST /auth/whats-new/seen, signed in, must be 204: got {closed.status_code} {closed.text}"

    monkeypatch.setattr(app_config, "get_version", lambda: NEWER_VERSION)

    upgrade = {"since": RUNNING_RELEASE, "release": NEWER_RELEASE}
    seen = _whats_new_in(await _me(private, witness.cookie), "barrier: GET /auth/me of an account that saw 1.3.0")
    assert seen == upgrade, f"barrier: running {NEWER_VERSION!r}, an account that saw {RUNNING_RELEASE!r} must have {upgrade}: GET /auth/me answered whats_new {seen!r}"
    again = _whats_new_in(await _me(private, member.cookie), "GET /auth/me after the upgrade")
    assert again is None, f"red until E's note 1 on C-54: the account saw {NEWER_RELEASE!r} before it closed the modal on a worker running {RUNNING_RELEASE!r}; running {NEWER_VERSION!r} now, GET /auth/me must answer whats_new null, nothing it has not seen: it answered {again!r}"
