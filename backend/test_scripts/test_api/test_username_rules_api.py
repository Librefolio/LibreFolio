"""A-21a over HTTP: no new username with an @, no address that is another account's username, and a sign-in that reads an address first (release 1.3, workstream A, lot A-21a; workstream E's review, point c).

Until A-21a ``POST /auth/register`` and ``PUT /auth/profile`` take any username of 3 to 50 characters, ``@`` included,
and ``POST /auth/login`` looks what is typed up as a username OR an address
(``user_service.get_user_by_username_or_email``), the username's index first. So account A, named ``bob@example.com``,
signs in with B's address and A's password, and B, typing its own address, gets 401 (workstream E's review, MEDIUM
8/10). The contract of A-21a, over HTTP:

1. No ``@`` in a NEW username. ``POST /auth/register`` — registration ``open``, or by invitation with a valid one — with a
   username holding an ``@`` is refused, 422 (the schema) or 400 (the service), whichever the implementer chooses; a
   422 is about ``username``. Nothing is created and the invitation stays live. ``PUT /auth/profile`` with such a
   username is refused, 422 or 400, nothing changed. Spaces and accents stay allowed (GUARDS). A legacy account named
   with an ``@`` keeps its name and its profile: it changes its address as anyone does (GUARD).
2. No address equal to an existing username, A–Z case aside. ``POST /auth/register`` with an address that is a legacy
   account's username — as written, or in another A–Z case — is 400 with ``detail`` ``EMAIL_TAKEN_DETAIL``, the answer to
   an address already registered, which the registration card and the profile already translate (a code of its own is
   the other admissible decision: one constant); nothing created. ``PUT /auth/profile`` changing the address to such a
   string, with the right current password, is 400 with the same ``detail``; nothing changed.
3. The sign-in reads an identifier with an ``@`` as an address first, then as a legacy username. E's point (c):
   - B registers first, then A tries B's address as its username — as B wrote it, or in another A–Z case —: refused by
     rule 1, nothing created; B signs in with its address, in both forms, as B.
   - A is a legacy account named with B's address — as B writes it, or in another A–Z case —, both written as rows, in
     either order: B typing its address exactly as A's name is written, with B's password, signs in as B (200, B's id);
     A typing that same name with A's password gets 401 — the address is B's. A signs in with its own address, and B
     with its address typed in the other form (GUARDS).
   - The reverse case: a legacy name with an ``@`` that is nobody's address still signs its account in, typed exactly;
     in another A–Z case it is 401 — the fallback is exact (GUARD).

Every refusal leaves the database unchanged: every row of every table, ``sqlite_sequence`` included, read by SQLite from
the file before and after. Each refusal carries a barrier, run after it: the same request with the ``@`` replaced, or
with a fresh address, goes through — so the refusal is the rule's, not the scene's.

Where it runs: in-process only, never on the lane. Each case has a private SQLite file under ``tmp_path`` (NullPool,
disposed at teardown) with the schema and default settings of a new install, served by the real auth router mounted under
the API prefix as ``api/v1/router.py`` mounts it, its ``get_session_generator`` opening sessions on that file. The
legacy accounts are rows written directly, as an install from before A-21a holds them: the lane's shared database is no
place for them. Process-wide state is replaced through ``monkeypatch`` and put back: bcrypt at cost 4 and a private dummy
hash of cost 4 (the process's cached one is left as it was: LOGIN-024 of ``test_auth_api.py`` reads its cost); the two
limiters of ``login_throttle`` by fresh ones of the shipped size, so no failure here counts in the process's own (the
limit stays on, as it ships); the session cookie's Secure mode on ``auto`` (plain HTTP here; the cookie is read from
``Set-Cookie`` and sent explicitly); ``get_async_engine`` a tripwire in the session module and in workstream E's modules.
The accounts and email variables of the shell are removed: email is off, so registration verifies nothing and the
notice of an address change sends nothing. Every request comes from one documentation address of this file's own and
carries no forwarding header. Every name and address carries a random tag. Nothing waits.

Red until A-21a, each test on its own, at its first assertion: today the registration with an ``@`` answers 201
(UNAME-API-01 and 08), with a legacy name for address 201 (UNAME-API-03), the profile 200 (UNAME-API-04 and 06), and B's
sign-in 401 (UNAME-API-09). UNAME-API-02, 05, 07, 10 and 11 are GUARDS, green today and to stay green.
"""

from __future__ import annotations

import contextlib
import functools
import os
import sqlite3
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import bcrypt
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

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
# THE RULES' VALUES — a different decision is an edit here
# =============================================================================

#: The one character rule 1 refuses in a new username.
AT = "@"
#: What stands for the ``@`` in a barrier's username: the same name without the one character rule 1 refuses.
NOT_AT = "-"
#: How a new username with an ``@`` may be refused: by the schema (422) or by the service (400), the implementer's call.
USERNAME_REFUSALS = frozenset({400, 422})
#: The ``detail`` of the 400 that refuses an address equal to another account's username (rule 2): the answer to an
#: address already registered. A code of its own is the other admissible decision: then change this.
EMAIL_TAKEN_DETAIL = "Email already registered"
#: New usernames with an ``@``, as templates of a fresh tag: 3 to 50 characters each, so only the ``@`` can refuse them.
AT_USERNAMES = [
    pytest.param("squat.{tag}@example.com", id="an-address"),
    pytest.param("name@{tag}", id="name-at-tag"),
    pytest.param("@{tag}", id="leading-at"),
    pytest.param("{tag}@", id="trailing-at"),
]
#: New usernames rule 1 leaves alone (GUARDS): spaces, accents, and the punctuation an address holds besides the ``@``.
ALLOWED_USERNAMES = [
    pytest.param("José María {tag}", id="spaces-and-accents"),
    pytest.param("Zoë_Ångström-{tag}", id="accents-underscore-hyphen"),
    pytest.param("first.last+{tag}", id="dot-and-plus"),
]

REGISTER = f"{API_V1_PREFIX}/auth/register"
LOGIN = f"{API_V1_PREFIX}/auth/login"
PROFILE = f"{API_V1_PREFIX}/auth/profile"
COOKIE = auth_api.SESSION_COOKIE_NAME
BASE_URL = "http://test"
TIMEOUT = 30.0
#: Where the requests come from, as the app sees them (the ASGI ``client``): a documentation address of this file's own.
CLIENT = ("198.51.100.121", 42121)
INVALID_CREDENTIALS = "Invalid credentials"

#: Passwords that meet the rules (decision 37): one per account of a scene, so the answer tells whose was checked.
PASSWORD = "Username-Api-Pass-2026!"
OWNER_PASSWORD = "Owner-Bob-Pass-2026!"
SQUATTER_PASSWORD = "Squatter-Alice-Pass-2026!"
#: Removed before every test: each changes what registration, the sign-in or an email decide.
INHERITED_PREFIXES = ("LIBREFOLIO_SMTP_", "LIBREFOLIO_ADMIN_")
INHERITED_VARIABLES = ("LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BILLING_URL", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_LOGIN_LIMIT")


# =============================================================================
# NAMES AND ADDRESSES
# =============================================================================


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


def _address(prefix: str) -> str:
    """An address nobody has: ``prefix``, a tag of its own, at ``example.com``, all in lower case."""
    return f"{prefix}.{_tag()}@example.com"


def _named(template: str) -> str:
    """``template`` with a fresh tag: a name nobody has."""
    return template.format(tag=_tag())


def _without_at(name: str) -> str:
    """The barrier's name: ``name`` with each ``@`` replaced, nothing else changed."""
    return name.replace(AT, NOT_AT)


def _ascii_fold(text: str) -> str:
    """The fold of decision P18, written out: A–Z to a–z, every other character as it is."""
    return "".join(chr(ord(character) + 32) if "A" <= character <= "Z" else character for character in text)


def _as_written(address: str) -> str:
    return address


def _upper(address: str) -> str:
    return address.upper()


def _capitalized(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local.capitalize()}@{domain.capitalize()}"


Form = Callable[[str], str]

#: (how a legacy username writes an address, how the address is typed): the same address but for A–Z, both ways.
SQUAT_PAIRS = [
    pytest.param(_as_written, _as_written, id="typed-as-the-name-is-written"),
    pytest.param(_as_written, _upper, id="typed-in-UPPER"),
    pytest.param(_capitalized, _as_written, id="name-Capitalized-typed-in-lower"),
]
#: How the squatter's name writes B's address, in E's scenes: as B writes it, or in another A–Z case.
SQUATTER_FORMS = [pytest.param(_as_written, id="name-as-B-writes-it"), pytest.param(_upper, id="name-in-UPPER")]
SQUATTER_FIRST, OWNER_FIRST = "squatter-first", "owner-first"
ORDERS = [pytest.param(SQUATTER_FIRST, id=SQUATTER_FIRST), pytest.param(OWNER_FIRST, id=OWNER_FIRST)]


def _squat(name_form: Form, typed_form: Form) -> tuple[str, str]:
    """A legacy username holding an address, and that address as typed: checked to be the same address but for A–Z."""
    address = _address("squat")
    name, typed = name_form(address), typed_form(address)
    assert AT in name and _ascii_fold(name) == _ascii_fold(typed), f"test bug: {typed!r} is not the legacy name {name!r} but for A–Z"
    return name, typed


# =============================================================================
# FIXTURES: THE VARIABLES, THE PROCESS'S STATE, THE PRIVATE INSTANCE
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the accounts and email variables of the shell that started the run: email off, the login limit as it ships."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


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
    db_path = tmp_path / "username-rules-api.db"
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


def _rows(db_path: Path) -> Rows:
    """Every row of every table, ``sqlite_sequence`` included, read from the file: what «nothing written» compares."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        tables = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return {table: sorted(conn.execute(f'SELECT * FROM "{table}"').fetchall(), key=repr) for table in tables}


def _changed(before: Rows, after: Rows) -> list[str]:
    """The tables whose rows differ between ``before`` and ``after``."""
    return sorted(table for table in set(before) | set(after) if before.get(table) != after.get(table))


async def _add_user(engine: AsyncEngine, *, username: str, email: str, password: str = PASSWORD) -> int:
    """An account written as a row — as an install from before A-21a may hold it —, active, with a real bcrypt hash of ``password`` (cost 4): its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(password))
        session.add(user)
        await session.commit()
    return user.id


async def _username_of(engine: AsyncEngine, user_id: int) -> str:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(User.username).where(User.id == user_id))).scalar_one()


async def _email_of(engine: AsyncEngine, user_id: int) -> str:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(User.email).where(User.id == user_id))).scalar_one()


async def _registration_open(engine: AsyncEngine) -> None:
    """``registration_mode`` = ``open``, on the row the startup seeded: a registration needs no invitation."""
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, "registration_mode")
        assert row is not None, "setup: initialize_global_settings seeded no registration_mode row"
        row.value = "open"
        session.add(row)
        await session.commit()


async def _invitation(engine: AsyncEngine, creator: int) -> str:
    """A live invitation issued by the token service directly and committed: the scene is set without the route under test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, AccountTokenPurpose.INVITE, created_by_user_id=creator)
        await session.commit()
    return issued.token


async def _admission(private: _Private, with_invitation: bool) -> Optional[str]:
    """An instance that already has an account — so a newcomer is not its first, the administrator — and admits a registration: ``open``, or by invitation with a valid one (the default mode of a new install). The invitation, if any."""
    seed = await _add_user(private.engine, username=f"seed_{_tag()}", email=_address("seed"))
    if with_invitation:
        return await _invitation(private.engine, seed)
    await _registration_open(private.engine)
    return None


@dataclass(frozen=True)
class Squat:
    """B, who owns an address, and A, a legacy account named with that address in some A–Z case: rows with passwords of their own."""

    owner: int
    owner_email: str
    squatter: int
    squatter_name: str
    squatter_email: str


async def _squat_scene(private: _Private, form: Form, order: str) -> Squat:
    """E's scene: B owns ``bob.<tag>@example.com``; A is named with it as ``form`` writes it, A's own address elsewhere; both rows written, in ``order``."""
    tag = _tag()
    owner_email, squatter_email = f"bob.{tag}@example.com", f"alice.{tag}@example.org"
    squatter_name = form(owner_email)
    owner = {"username": f"bob_{tag}", "email": owner_email, "password": OWNER_PASSWORD}
    squatter = {"username": squatter_name, "email": squatter_email, "password": SQUATTER_PASSWORD}
    written = (squatter, owner) if order == SQUATTER_FIRST else (owner, squatter)
    ids = [await _add_user(private.engine, **account) for account in written]
    squatter_id, owner_id = ids if order == SQUATTER_FIRST else ids[::-1]
    return Squat(owner=owner_id, owner_email=owner_email, squatter=squatter_id, squatter_name=squatter_name, squatter_email=squatter_email)


# =============================================================================
# HELPERS — requests, and reading the answers
# =============================================================================


async def _request(private: _Private, method: str, path: str, *, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request from a client of its own at ``CLIENT``: no cookie jar, the session cookie, if any, sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    transport = httpx.ASGITransport(app=private.app, client=CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as client:
        return await client.request(method, path, json=json, headers=headers)


async def _register(private: _Private, username: str, email: str, invite_token: Optional[str] = None, password: str = PASSWORD) -> httpx.Response:
    body: dict[str, Any] = {"username": username, "email": email, "password": password}
    if invite_token is not None:
        body["invite_token"] = invite_token
    return await _request(private, "POST", REGISTER, json=body)


async def _login(private: _Private, identifier: str, password: str) -> httpx.Response:
    return await _request(private, "POST", LOGIN, json={"username": identifier, "password": password})


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


async def _signed_in(private: _Private, *, username: str, email: str) -> tuple[int, str]:
    """An account written as a row, signed in through ``POST /auth/login`` with its address — an address first, before A-21a and after. It ends on its promise: a 200 as that account, one session cookie. Its id and its cookie."""
    user_id = await _add_user(private.engine, username=username, email=email)
    response = await _login(private, email, PASSWORD)
    cookies = _session_cookies(response)
    assert _account_id(response) == user_id and len(cookies) == 1 and cookies[0], f"setup: #{user_id} signs in with its address: {response.status_code} {response.text}"
    return user_id, cookies[0]


def _assert_signed_in_as(response: httpx.Response, user_id: int, request: str) -> None:
    assert response.status_code == 200, f"{request}: expected 200 as #{user_id}, got {response.status_code} {response.text}"
    assert _account_id(response) == user_id and len(_session_cookies(response)) == 1, f"{request}: signed in as #{_account_id(response)}, with session cookies {_session_cookies(response)}: expected #{user_id}, one cookie"


def _assert_invalid_credentials(response: httpx.Response, request: str) -> None:
    assert response.status_code == 401, f"{request}: expected 401 {INVALID_CREDENTIALS}, got {response.status_code} {response.text}"
    assert response.json().get("detail") == INVALID_CREDENTIALS and _session_cookies(response) == [], f"{request}: the 401 says {INVALID_CREDENTIALS!r} and sets no session cookie: {response.text} {response.headers.get_list('set-cookie')}"


def _assert_username_refused(response: httpx.Response, request: str) -> None:
    """Rule 1's refusal: 400, or 422 — then about ``username``."""
    assert response.status_code in USERNAME_REFUSALS, f"red until A-21a: {request}: a new username with an @ must be refused, {sorted(USERNAME_REFUSALS)}; got {response.status_code} {response.text}"
    if response.status_code == 422:
        locations = [error.get("loc", []) for error in response.json().get("detail", [])]
        assert any("username" in location for location in locations), f"{request}: the 422 must be about the username: {response.text}"


def _assert_email_taken(response: httpx.Response, request: str) -> None:
    """Rule 2's refusal: 400, ``detail`` ``EMAIL_TAKEN_DETAIL``."""
    assert response.status_code == 400, f"red until A-21a: {request}: an address that is another account's username, A–Z case aside, must be refused with 400; got {response.status_code} {response.text}"
    assert response.json().get("detail") == EMAIL_TAKEN_DETAIL, f"{request}: the refusal must be the answer to an address already registered, {EMAIL_TAKEN_DETAIL!r}: {response.text}"


# =============================================================================
# RULE 1 — NO @ IN A NEW USERNAME: POST /auth/register
# =============================================================================


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("with_invitation", [False, True], ids=["open-no-invitation", "a-valid-invitation"])
@pytest.mark.parametrize("template", AT_USERNAMES)
async def test_registration_refuses_a_new_username_with_an_at(private: _Private, template: str, with_invitation: bool) -> None:
    """UNAME-API-01 — rule 1, red until A-21a (today 201): an instance with an account, registration ``open`` or by invitation with a valid one; ``POST /auth/register`` with a username holding an ``@`` — an address, ``name@tag``, a leading or a trailing ``@`` — is refused, 422 about ``username`` or 400, and every row of every table is as it was: no account, the invitation not spent. Barrier: the same request with the ``@`` replaced is 201, the invitation spent by it."""
    print_section(f"UNAME-API-01: POST /auth/register with an @ in the username ({'invitation' if with_invitation else 'open'})")
    invitation = await _admission(private, with_invitation)
    name = _named(template)
    before = _rows(private.db_path)

    refused = await _register(private, name, _address("newcomer"), invitation)

    _assert_username_refused(refused, f"POST /auth/register as {name!r}")
    assert _changed(before, _rows(private.db_path)) == [], f"a refused registration must write nothing, the invitation included: {_changed(before, _rows(private.db_path))}"
    allowed = await _register(private, _without_at(name), _address("newcomer"), invitation)
    assert allowed.status_code == 201, f"barrier: the same registration with the @ replaced must be 201: {allowed.status_code} {allowed.text}"
    print_success(f"{name!r} refused ({refused.status_code}), nothing written; {_without_at(name)!r} registered")


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("template", ALLOWED_USERNAMES)
async def test_registration_still_takes_spaces_accents_and_punctuation(private: _Private, template: str) -> None:
    """UNAME-API-02 — rule 1, GUARD (green today; red if A-21a refuses more than the ``@``): ``POST /auth/register`` with a username holding spaces and accents, or ``.``, ``_``, ``-`` and ``+``, is 201, the username stored as sent."""
    await _admission(private, with_invitation=False)
    name = _named(template)

    response = await _register(private, name, _address("newcomer"))

    assert response.status_code == 201, f"POST /auth/register as {name!r} must be 201: {response.status_code} {response.text}"
    assert await _username_of(private.engine, _account_id(response)) == name, f"{name!r} must be stored as sent"


# =============================================================================
# RULE 2 — NO ADDRESS THAT IS ANOTHER ACCOUNT'S USERNAME: POST /auth/register
# =============================================================================


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("with_invitation", [False, True], ids=["open-no-invitation", "a-valid-invitation"])
@pytest.mark.parametrize(("name_form", "typed_form"), SQUAT_PAIRS)
async def test_registration_refuses_an_address_that_is_a_legacy_username(private: _Private, name_form: Form, typed_form: Form, with_invitation: bool) -> None:
    """UNAME-API-03 — rule 2, red until A-21a (today 201): a legacy account named with an address, written as a row; ``POST /auth/register`` of a new username with that address — as the name writes it or in another A–Z case —, ``open`` or with a valid invitation, is 400 ``EMAIL_TAKEN_DETAIL`` and writes nothing: the invitation not spent. Barrier: the same request with a fresh address is 201."""
    print_section("UNAME-API-03: POST /auth/register with a legacy username for address")
    invitation = await _admission(private, with_invitation)
    name, typed = _squat(name_form, typed_form)
    await _add_user(private.engine, username=name, email=_address("legacy"))
    newcomer = f"newcomer_{_tag()}"
    before = _rows(private.db_path)

    refused = await _register(private, newcomer, typed, invitation)

    _assert_email_taken(refused, f"POST /auth/register with {typed!r}, the legacy name {name!r} but for A–Z")
    assert _changed(before, _rows(private.db_path)) == [], f"a refused registration must write nothing, the invitation included: {_changed(before, _rows(private.db_path))}"
    allowed = await _register(private, newcomer, _address("fresh"), invitation)
    assert allowed.status_code == 201, f"barrier: the same registration with a fresh address must be 201: {allowed.status_code} {allowed.text}"
    print_success("refused as an address already registered, nothing written")


# =============================================================================
# RULES 1 AND 2 — PUT /auth/profile
# =============================================================================


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("template", AT_USERNAMES)
async def test_the_profile_refuses_a_new_username_with_an_at(private: _Private, template: str) -> None:
    """UNAME-API-04 — rule 1, red until A-21a (today 200): a signed-in account; ``PUT /auth/profile`` with a username holding an ``@`` is refused, 422 about ``username`` or 400, and every row of every table is as it was — its name, its session version. Barrier: the same request with the ``@`` replaced is 200, the name changed."""
    print_section("UNAME-API-04: PUT /auth/profile with an @ in the username")
    user_id, cookie = await _signed_in(private, username=f"member_{_tag()}", email=_address("member"))
    name = _named(template)
    before = _rows(private.db_path)

    refused = await _request(private, "PUT", PROFILE, cookie=cookie, json={"username": name})

    _assert_username_refused(refused, f"PUT /auth/profile with the username {name!r}")
    assert _changed(before, _rows(private.db_path)) == [], f"a refused change must write nothing: {_changed(before, _rows(private.db_path))}"
    allowed = await _request(private, "PUT", PROFILE, cookie=cookie, json={"username": _without_at(name)})
    assert allowed.status_code == 200 and await _username_of(private.engine, user_id) == _without_at(name), f"barrier: the same change with the @ replaced must be 200 and stored: {allowed.status_code} {allowed.text}"
    print_success(f"{name!r} refused ({refused.status_code}), nothing written")


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("template", ALLOWED_USERNAMES)
async def test_the_profile_still_takes_spaces_accents_and_punctuation(private: _Private, template: str) -> None:
    """UNAME-API-05 — rule 1, GUARD (green today; red if A-21a refuses more than the ``@``): ``PUT /auth/profile`` with a username holding spaces and accents, or ``.``, ``_``, ``-`` and ``+``, is 200, the name stored as sent."""
    user_id, cookie = await _signed_in(private, username=f"member_{_tag()}", email=_address("member"))
    name = _named(template)

    response = await _request(private, "PUT", PROFILE, cookie=cookie, json={"username": name})

    assert response.status_code == 200, f"PUT /auth/profile with the username {name!r} must be 200: {response.status_code} {response.text}"
    assert await _username_of(private.engine, user_id) == name, f"{name!r} must be stored as sent"


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize(("name_form", "typed_form"), SQUAT_PAIRS)
async def test_the_profile_refuses_an_address_that_is_a_legacy_username(private: _Private, name_form: Form, typed_form: Form) -> None:
    """UNAME-API-06 — rule 2, red until A-21a (today 200: the address changes): a legacy account named with an address, written as a row, and a signed-in account; ``PUT /auth/profile`` changing its address to that name — as written or in another A–Z case — with the right current password is 400 ``EMAIL_TAKEN_DETAIL``, and every row of every table is as it was: the address, its verification, the session version. Barrier: the same change to a fresh address is 200."""
    print_section("UNAME-API-06: PUT /auth/profile with a legacy username for address")
    name, typed = _squat(name_form, typed_form)
    await _add_user(private.engine, username=name, email=_address("legacy"))
    user_id, cookie = await _signed_in(private, username=f"member_{_tag()}", email=_address("member"))
    before = _rows(private.db_path)

    refused = await _request(private, "PUT", PROFILE, cookie=cookie, json={"email": typed, "current_password": PASSWORD})

    _assert_email_taken(refused, f"PUT /auth/profile with the address {typed!r}, the legacy name {name!r} but for A–Z")
    assert _changed(before, _rows(private.db_path)) == [], f"a refused change must write nothing: {_changed(before, _rows(private.db_path))}"
    fresh = _address("fresh")
    allowed = await _request(private, "PUT", PROFILE, cookie=cookie, json={"email": fresh, "current_password": PASSWORD})
    assert allowed.status_code == 200 and await _email_of(private.engine, user_id) == fresh, f"barrier: the same change to a fresh address must be 200 and stored: {allowed.status_code} {allowed.text}"
    print_success("refused as an address already registered, nothing written")


# GUARD — green today, must stay green
@pytest.mark.asyncio
async def test_a_legacy_account_named_with_an_at_keeps_its_name_and_changes_its_address(private: _Private) -> None:
    """UNAME-API-07 — rules 1 and 2, GUARD (green today; red if A-21a locks legacy accounts out of their profile): a legacy account named ``legacy.<tag>@example.net``, written as a row, signed in with its address; ``PUT /auth/profile`` with a fresh address and the right current password is 200: the address changes, the legacy name stays as it is — A-21a refuses NEW names with an ``@``, it renames none."""
    name = f"legacy.{_tag()}@example.net"
    user_id, cookie = await _signed_in(private, username=name, email=_address("legacy"))
    fresh = _address("fresh")

    response = await _request(private, "PUT", PROFILE, cookie=cookie, json={"email": fresh, "current_password": PASSWORD})

    assert response.status_code == 200, f"PUT /auth/profile of a legacy account with a fresh address must be 200: {response.status_code} {response.text}"
    assert (await _username_of(private.engine, user_id), await _email_of(private.engine, user_id)) == (name, fresh), "the legacy name stays, the address changes"


# =============================================================================
# RULE 3 — THE SIGN-IN, IN E'S SCENES (point c)
# =============================================================================


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("form", SQUATTER_FORMS)
async def test_b_registers_first_and_its_address_as_a_username_is_refused(private: _Private, form: Form) -> None:
    """UNAME-API-08 — E's point (c), the first order, red until A-21a (today A's registration is 201): an instance with an account, registration ``open``. B registers with ``bob.<tag>@example.com`` (201). A registers with B's address for username — as B wrote it, or in UPPER —: refused by rule 1, 422 about ``username`` or 400, and every row of every table as it was. B then signs in with its address, as it wrote it and in that other form: 200 as B, both times."""
    print_section("UNAME-API-08: B registers, then A tries B's address as its username")
    await _admission(private, with_invitation=False)
    owner_email = f"bob.{_tag()}@example.com"
    registered = await _register(private, f"bob_{_tag()}", owner_email, password=OWNER_PASSWORD)
    owner = _account_id(registered)
    assert registered.status_code == 201 and owner is not None, f"setup: B registers: {registered.status_code} {registered.text}"
    squatter_name = form(owner_email)
    before = _rows(private.db_path)

    refused = await _register(private, squatter_name, f"alice.{_tag()}@example.org", password=SQUATTER_PASSWORD)

    _assert_username_refused(refused, f"POST /auth/register as {squatter_name!r}, B's address")
    assert _changed(before, _rows(private.db_path)) == [], f"a refused registration must write nothing: {_changed(before, _rows(private.db_path))}"
    for typed in dict.fromkeys((owner_email, squatter_name)):
        _assert_signed_in_as(await _login(private, typed, OWNER_PASSWORD), owner, f"POST /auth/login as {typed!r}, B's address, with B's password")
    print_success("the squatting name refused; B signs in with its address")


# red until A-21a
@pytest.mark.asyncio
@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize("form", SQUATTER_FORMS)
async def test_b_signs_in_with_its_address_where_a_legacy_name_is_written_like_it(private: _Private, form: Form, order: str) -> None:
    """UNAME-API-09 — E's point (c), the second order, red until A-21a (today 401 for B, 200 for A: the username's index answers first): A, a legacy account named with B's address — as B writes it, or in UPPER —, and B, both written as rows, squatter first or owner first. B typing its address exactly as A's name is written, with B's password: 200 as B. A typing that same name with A's password: 401 ``Invalid credentials``, no session cookie — the address is B's."""
    print_section("UNAME-API-09: B signs in with its address where a legacy name is written like it")
    scene = await _squat_scene(private, form, order)

    owner = await _login(private, scene.squatter_name, OWNER_PASSWORD)

    _assert_signed_in_as(owner, scene.owner, f"red until A-21a: POST /auth/login as {scene.squatter_name!r} — B's address, A's legacy name — with B's password")
    _assert_invalid_credentials(await _login(private, scene.squatter_name, SQUATTER_PASSWORD), f"red until A-21a: POST /auth/login as {scene.squatter_name!r} — B's address — with A's password")
    print_success("B's address signs B in; A's legacy name no longer signs A in")


# GUARD — green today, must stay green
@pytest.mark.asyncio
@pytest.mark.parametrize("order", ORDERS)
@pytest.mark.parametrize("form", SQUATTER_FORMS)
async def test_in_the_squatter_scene_a_signs_in_with_its_address_and_b_with_another_form(private: _Private, form: Form, order: str) -> None:
    """UNAME-API-10 — E's point (c), GUARD (green today; red if A-21a stops folding addresses, or loses an account's own address): the scene of UNAME-API-09. A signs in with its own address and A's password: 200 as A. B signs in with its address typed in the form A's name is not written in — in UPPER when A's name is as B writes it, as B writes it when A's name is in UPPER —: 200 as B."""
    scene = await _squat_scene(private, form, order)
    other_form = scene.owner_email if scene.squatter_name != scene.owner_email else scene.owner_email.upper()

    _assert_signed_in_as(await _login(private, scene.squatter_email, SQUATTER_PASSWORD), scene.squatter, f"POST /auth/login as {scene.squatter_email!r}, A's own address, with A's password")
    _assert_signed_in_as(await _login(private, other_form, OWNER_PASSWORD), scene.owner, f"POST /auth/login as {other_form!r}, B's address in a form A's name is not, with B's password")


# GUARD — green today, must stay green
@pytest.mark.asyncio
async def test_a_legacy_name_with_an_at_that_is_nobodys_address_still_signs_in(private: _Private) -> None:
    """UNAME-API-11 — rule 3's fallback, E's reverse case, GUARD (green today; red if A-21a drops legacy names from the sign-in, or folds them): L, a legacy account named ``legacy.<tag>@example.net`` — nobody's address —, written as a row. L signs in with that name and its password: 200 as L. The name in UPPER, with the same password: 401 ``Invalid credentials`` — no account has that address, and the fallback compares the name as written."""
    name = f"legacy.{_tag()}@example.net"
    legacy = await _add_user(private.engine, username=name, email=_address("legacy"))

    _assert_signed_in_as(await _login(private, name, PASSWORD), legacy, f"POST /auth/login as {name!r}, L's legacy name, nobody's address")
    _assert_invalid_credentials(await _login(private, name.upper(), PASSWORD), f"POST /auth/login as {name.upper()!r}, L's legacy name in another A–Z case")
