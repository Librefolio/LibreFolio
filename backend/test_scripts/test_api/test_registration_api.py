"""
Registration API — release 1.3, workstream A, lot A5a (plan phase01Accounts §17 A5.1, contract points 2 and 5, the public part).

Who may create an account is now one of three modes, an invitation can open an account, an administrator can hand out a
password-reset link, and the app learns the mode before anyone signs in. The public endpoints of that, pinned here:

1. ``POST /auth/register`` takes ``invite_token`` beside username, e-mail and password. Refusals:
   403 ``REGISTRATION_DISABLED``, 403 ``INVITE_REQUIRED``, 400 ``INVITE_INVALID``, 409 ``USER_LIMIT_REACHED`` — the
   last one without counts and without the billing link: whoever asks is anonymous (decision 15). A refusal creates no
   account and consumes no invitation. A valid invitation gives its role; the first account is the administrator in
   every mode, and spends the invitation it comes with like any other (review of 15/10).
2. ``POST /auth/tokens/inspect`` ``{token, purpose: invite|password_reset}`` → ``{status, purpose}``. Only a ``valid``
   token adds ``expires_at``, and ``grants_admin`` and ``email`` for an invitation or ``username`` for a reset link;
   any other status shows nothing more (each detail absent or null). Public — it answers only whoever holds the token —,
   it consumes nothing, and a token of the other purpose is ``unknown``.
3. ``POST /auth/password-reset`` ``{token, new_password}`` consumes the reset link and sets the password (bcrypt off the
   event loop), ends every session of the account — a cookie issued before is 401 —, and revokes the account's other
   live reset links, not another account's: 200. A link used, expired, revoked, unknown or of another purpose is 400
   ``TOKEN_INVALID`` and changes nothing. The new password follows the API's rule for now (at least 8 characters: 422).
4. ``GET /system/instance`` carries ``accounts: {registration_mode, registration_locked}`` — the effective mode, and
   whether the variable sets it —, public, and nothing about users: no count, no limit, no billing link.
5. ``PATCH /settings/global/bulk`` writing ``registration_mode`` while ``LIBREFOLIO_REGISTRATION`` sets it: 409
   ``SETTING_LOCKED_BY_ENV``, nothing saved — the other items of the request included. Without the variable the write
   goes through, within the three choices.
6. Review of 15/10: a new install seeds ``registration_mode`` as ``open`` with ``value_type`` ``str``, the type of every
   text setting; an invalid ``LIBREFOLIO_PUBLIC_URL`` or ``LIBREFOLIO_BILLING_URL`` costs its link and nothing else, so
   the instance answers open and registrations go through (what its log says is pinned in
   ``test_services/test_registration_service.py``).

Coded refusals are read from ``detail.error_code``, the shape ``POST /auth/login`` already gives ``ACCOUNT_DISABLED``.

Where each case runs, and why. The registration mode is one row shared by the whole lane, and every concurrent
registration of every unit depends on it; the variables are read by the lane's server, another process this test cannot
configure. So every case that needs another mode, a variable or a limit runs in-process: the real routers of auth,
settings and system, mounted as ``api/v1/router.py`` mounts them, in an app of this test whose
``get_session_generator`` is a private SQLite file under ``tmp_path``; the variables are set with ``monkeypatch`` in
this process only. On the lane's server run only the cases that need no global change, in the lane's mode, which must be
``open`` (asserted first, from ``GET /system/instance``): each registers its own account and issues its own tokens in
the lane's database, then deletes them, and never writes a setting. A case that opens an account first checks that the
lane already holds one — the api setup's (``db populate``) —, since on an empty lane it would be the first account,
hence the lane's administrator. The unit is therefore write-scoped, in the parallel pass, with no ``exclusive_because``.

bcrypt runs at its lowest cost in this process (``auth_service.BCRYPT_ROUNDS = 4``); the lane's server keeps its own.
"""

from __future__ import annotations

import contextlib
import threading
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import bcrypt
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import settings as settings_api
from backend.app.api.v1 import system as system_api
from backend.app.config import API_V1_PREFIX, get_settings
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User
from backend.app.db.session import get_async_engine, get_session_generator
from backend.app.services.accounts import auth_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus, consume_token, inspect_token, issue_token, revoke_tokens
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
COOKIE = auth_api.SESSION_COOKIE_NAME

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
MODE_KEY = "registration_mode"
REGISTRATION_VARIABLE = "LIBREFOLIO_REGISTRATION"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BILLING_URL_VARIABLE = "LIBREFOLIO_BILLING_URL"
ACCOUNTS_VARIABLES = (REGISTRATION_VARIABLE, MAX_USERS_VARIABLE, PUBLIC_URL_VARIABLE, BILLING_URL_VARIABLE)
BILLING_LINK = "https://billing.example.test/subscription/acme-family"

PASSWORD = "Registration-Api-2026"
NEW_PASSWORD = "Reset-Api-Pass-2026"
NEVER_ISSUED = "never-issued-api-0123456789abcdefghijklmnopq"
INVALID_INVITES = ("unknown", "expired", "consumed", "revoked", "password_reset")
DEAD_STATUSES = ("unknown", "expired", "consumed", "revoked")
#: What only a valid token may show, besides its status and purpose.
TOKEN_DETAILS = ("expires_at", "grants_admin", "email", "username")
#: What an anonymous refusal must never carry: the counts and the billing link are for the administrator only.
ADMIN_ONLY_KEYS = frozenset({"limit", "used", "max_users", "billing_url"})

# Paths of the in-process app, mounted as api/v1/router.py mounts the routers.
REGISTER = f"{API_V1_PREFIX}/auth/register"
INSPECT = f"{API_V1_PREFIX}/auth/tokens/inspect"
RESET = f"{API_V1_PREFIX}/auth/password-reset"
LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
INSTANCE = f"{API_V1_PREFIX}/system/instance"
BULK = f"{API_V1_PREFIX}/settings/global/bulk"
MODE_SETTING = f"{API_V1_PREFIX}/settings/global/{MODE_KEY}"


@pytest.fixture(scope="module")
def test_server():
    """The lane's server, for the live cases only (attaches to the runner's shared backend)."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================================
# THE PRIVATE INSTANCE: THE REAL ROUTERS ON A DATABASE OF THIS TEST
# ============================================================================


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the routers of auth, settings and system, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _app(engine: AsyncEngine) -> FastAPI:
    """The real routers, mounted under the API prefix as ``api/v1/router.py`` mounts them; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    for router in (auth_api.router, settings_api.router, system_api.router):
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
        yield _Private(engine=engine, app=_app(engine))
    finally:
        await engine.dispose()


@contextlib.asynccontextmanager
async def _browser(private: _Private) -> AsyncIterator[httpx.AsyncClient]:
    """A browser of its own on the private instance: its own cookie jar, no session until it signs in."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=private.app), base_url="http://test", timeout=TIMEOUT) as client:
        yield client


async def _set_mode_row(engine: AsyncEngine, mode: str) -> None:
    """The ``registration_mode`` row says ``mode``: the seeded row updated, or created when missing."""
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, MODE_KEY)
        if row is None:
            row = GlobalSetting(key=MODE_KEY, value=mode, value_type="str", updated_at=utcnow())
        row.value = mode
        session.add(row)
        await session.commit()


async def _put_mode(private: _Private, monkeypatch: pytest.MonkeyPatch, mode: str, source: str) -> None:
    """Registration is ``mode``, said by the row ("row") or by the variable over a row that says otherwise ("env")."""
    if source == "row":
        await _set_mode_row(private.engine, mode)
        return
    await _set_mode_row(private.engine, "disabled" if mode == "open" else "open")
    monkeypatch.setenv(REGISTRATION_VARIABLE, mode)


async def _add_user(engine: AsyncEngine, username: str, *, password: Optional[str] = None, admin: bool = False) -> int:
    """An active account written as a row; with ``password``, a real bcrypt hash of it (cost 4), so that it can sign in."""
    hashed = auth_service.hash_password(password) if password else "$argon2id$seeded-account"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password=hashed, is_superuser=admin)
        session.add(user)
        await session.commit()
    return user.id


async def _usernames(engine: AsyncEngine) -> set[str]:
    async with AsyncSession(engine) as session:
        return set((await session.execute(select(User.username))).scalars().all())


async def _account(engine: AsyncEngine, user_id: int) -> tuple[str, int]:
    """``(hashed_password, session_version)`` of an account, read fresh."""
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(User.hashed_password, User.session_version).where(User.id == user_id))).one()
    return row[0], row[1]


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose = INVITE, **arguments: Any) -> IssuedToken:
    """A token issued by the token service directly, committed."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose = INVITE) -> TokenStatus:
    async with AsyncSession(engine) as session:
        return (await inspect_token(session, token, purpose)).status


async def _token_row(engine: AsyncEngine, token_id: int) -> AccountToken:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        record = await session.get(AccountToken, token_id)
    assert record is not None, f"token {token_id} is not in the database"
    return record


async def _dead_token(engine: AsyncEngine, purpose: AccountTokenPurpose, kind: str, owner: int) -> str:
    """A token of ``purpose`` that is not valid, of one ``kind``: never issued, expired, consumed or revoked."""
    if kind == "unknown":
        return NEVER_ISSUED
    user_id = None if purpose == INVITE else owner
    if kind == "expired":
        return (await _issue(engine, purpose, user_id=user_id, now=utcnow() - DEFAULT_TTL[purpose] - timedelta(days=1))).token
    issued = await _issue(engine, purpose, user_id=user_id)
    async with AsyncSession(engine) as session:
        if kind == "consumed":
            assert await consume_token(session, issued.token, purpose, consumed_by_user_id=owner) is not None, "setup: consumed"
        else:
            assert await revoke_tokens(session, token_id=issued.record.id) == 1, "setup: revoked"
        await session.commit()
    return issued.token


async def _invalid_invite(engine: AsyncEngine, kind: str, owner: int) -> str:
    """Not a valid invitation: a dead one, or a reset link offered as one."""
    if kind == "password_reset":
        return (await _issue(engine, PASSWORD_RESET, user_id=owner)).token
    return await _dead_token(engine, INVITE, kind, owner)


def _error_code(response: httpx.Response) -> Optional[str]:
    """``detail.error_code`` of a refusal, or None when the body has none."""
    try:
        body = response.json()
    except ValueError:
        return None
    detail = body.get("detail") if isinstance(body, dict) else None
    return detail.get("error_code") if isinstance(detail, dict) else None


def _keys(value: Any) -> set[str]:
    """Every key of every mapping inside ``value``, at any depth."""
    if isinstance(value, dict):
        return set(value).union(*(_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_keys(item) for item in value))
    return set()


def _instant(text: str) -> datetime:
    """An API timestamp as an aware UTC datetime (a naive one is UTC)."""
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


async def _register(client: httpx.AsyncClient, username: str, **body: Any) -> httpx.Response:
    """``POST /auth/register`` for ``username`` (``<username>@example.com``, the module's password), plus ``body``."""
    return await client.post(REGISTER, json={"username": username, "email": f"{username}@example.com", "password": PASSWORD, **body})


async def _inspect(client: httpx.AsyncClient, token: str, purpose: str) -> httpx.Response:
    return await client.post(INSPECT, json={"token": token, "purpose": purpose})


async def _sign_in(client: httpx.AsyncClient, username: str, password: str) -> httpx.Response:
    return await client.post(LOGIN, json={"username": username, "password": password})


# ============================================================================
# 1. POST /auth/register — IN-PROCESS
# ============================================================================


class TestRegisterByMode:
    """POST /auth/register against every mode, the variable and the limit, on a private instance."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("source", ["row", "env"])
    @pytest.mark.parametrize("with_invite", [pytest.param(False, id="no-invitation"), pytest.param(True, id="valid-invitation")])
    async def test_disabled_answers_403_registration_disabled_even_to_an_invitation(self, private: _Private, monkeypatch: pytest.MonkeyPatch, source: str, with_invite: bool) -> None:
        """REG-API-001: ``disabled`` (by the row or by the variable) → 403 ``REGISTRATION_DISABLED``, with or without a valid invitation; no account, the invitation still valid."""
        await _add_user(private.engine, "alice")
        issued = await _issue(private.engine, grants_admin=True)
        await _put_mode(private, monkeypatch, "disabled", source)

        async with _browser(private) as client:
            response = await _register(client, "newcomer", **({"invite_token": issued.token} if with_invite else {}))

        assert (response.status_code, _error_code(response)) == (403, "REGISTRATION_DISABLED"), f"registration disabled by the {source}: {response.status_code} {response.text}"
        assert await _usernames(private.engine) == {"alice"}
        assert await _status(private.engine, issued.token) == TokenStatus.VALID, "a refused registration must not consume the invitation"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("source", ["row", "env"])
    async def test_invite_mode_without_an_invitation_answers_403_invite_required(self, private: _Private, monkeypatch: pytest.MonkeyPatch, source: str) -> None:
        """REG-API-002: ``invite`` mode and no ``invite_token`` → 403 ``INVITE_REQUIRED``; no account."""
        await _add_user(private.engine, "alice")
        await _put_mode(private, monkeypatch, "invite", source)

        async with _browser(private) as client:
            response = await _register(client, "walkin")

        assert (response.status_code, _error_code(response)) == (403, "INVITE_REQUIRED"), f"{response.status_code} {response.text}"
        assert await _usernames(private.engine) == {"alice"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", ["open", "invite"])
    @pytest.mark.parametrize("kind", INVALID_INVITES)
    async def test_an_invalid_invitation_answers_400_invite_invalid(self, private: _Private, mode: str, kind: str) -> None:
        """REG-API-003: an invitation never issued, expired, consumed, revoked, or a reset link → 400 ``INVITE_INVALID``, in ``open`` mode too; no account."""
        owner = await _add_user(private.engine, "alice")
        await _set_mode_row(private.engine, mode)
        token = await _invalid_invite(private.engine, kind, owner)

        async with _browser(private) as client:
            response = await _register(client, "newcomer", invite_token=token)

        assert (response.status_code, _error_code(response)) == (400, "INVITE_INVALID"), f"{mode} mode, {kind} invitation: {response.status_code} {response.text}"
        assert await _usernames(private.engine) == {"alice"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", ["open", "invite"])
    @pytest.mark.parametrize("grants_admin", [pytest.param(False, id="user-invitation"), pytest.param(True, id="admin-invitation")])
    async def test_a_valid_invitation_registers_the_account_in_its_role_and_is_consumed(self, private: _Private, mode: str, grants_admin: bool) -> None:
        """REG-API-004: a valid invitation → 201, the account active with the invitation's role; the invitation consumed by that account."""
        await _add_user(private.engine, "alice")
        await _set_mode_row(private.engine, mode)
        issued = await _issue(private.engine, grants_admin=grants_admin)

        async with _browser(private) as client:
            response = await _register(client, "invited", invite_token=issued.token)

        assert response.status_code == 201, f"{mode} mode, a valid invitation: {response.status_code} {response.text}"
        user = response.json()["user"]
        assert (user["username"], user["is_active"], user["is_superuser"]) == ("invited", True, grants_admin), f"the account must take the invitation's role: {user}"
        assert (await _token_row(private.engine, issued.record.id)).consumed_by_user_id == user["id"], "the invitation must be consumed by the account it opened"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invite_field", [pytest.param({}, id="no-field"), pytest.param({"invite_token": None}, id="null")])
    async def test_open_mode_without_an_invitation_registers_a_regular_user(self, private: _Private, invite_field: dict[str, Any]) -> None:
        """REG-API-005: ``open`` — a new install's default — without an invitation, the field absent or null → 201, a regular user."""
        await _add_user(private.engine, "alice")

        async with _browser(private) as client:
            response = await _register(client, "walkin", **invite_field)

        assert response.status_code == 201, f"{response.status_code} {response.text}"
        assert response.json()["user"]["is_superuser"] is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("source", ["row", "env"])
    async def test_the_first_account_is_the_administrator_even_while_registration_is_disabled(self, private: _Private, monkeypatch: pytest.MonkeyPatch, source: str) -> None:
        """REG-API-006: no account at all and registration ``disabled`` (by the row or the variable) → 201, the administrator, without an invitation."""
        await _put_mode(private, monkeypatch, "disabled", source)

        async with _browser(private) as client:
            response = await _register(client, "founder")

        assert response.status_code == 201, f"the first account must be allowed in every mode: {response.status_code} {response.text}"
        assert response.json()["user"]["is_superuser"] is True

    @pytest.mark.asyncio
    async def test_the_first_account_spends_the_invitation_it_registers_with(self, private: _Private) -> None:
        """REG-API-008 (review of 15/10): on an empty instance, ``POST /auth/register`` with a valid invitation → 201, the administrator, and the invitation consumed by it; the same link again → 400 ``INVITE_INVALID``, no second account.

        An invitation can exist before anyone registered (``dev.py user invite``): given with the first registration, it
        is spent like any other, or its link would open a second account for the rest of its 7 days.
        """
        print_section("REG-API-008: the first account spends its invitation")
        issued = await _issue(private.engine)
        assert await _usernames(private.engine) == set(), "setup: the instance has no account"

        async with _browser(private) as client:
            first = await _register(client, "founder", invite_token=issued.token)
            stored = await _token_row(private.engine, issued.record.id)
            again = await _register(client, "second", invite_token=issued.token)

        assert first.status_code == 201 and first.json()["user"]["is_superuser"] is True, f"the first account is the administrator: {first.status_code} {first.text}"
        assert stored.consumed_by_user_id == first.json()["user"]["id"], f"the invitation must be consumed by the first account: consumed_by_user_id {stored.consumed_by_user_id}, consumed_at {stored.consumed_at}"
        assert (again.status_code, _error_code(again)) == (400, "INVITE_INVALID"), f"the spent link must open no second account: {again.status_code} {again.text}"
        assert await _usernames(private.engine) == {"founder"}
        print_success("201 administrator, the invitation consumed by it, the link refused the second time")

    @pytest.mark.asyncio
    async def test_the_limit_answers_409_to_an_anonymous_caller_without_counts_or_billing_link(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """REG-API-007: open mode, the limit reached, a billing link configured → 409 ``USER_LIMIT_REACHED``, with no ``limit``, ``used``, ``max_users`` nor ``billing_url`` anywhere in the body and the link nowhere in the text; no account.

        Decision 15: the counts and the subscription are the administrator's business; this caller is anonymous.
        """
        print_section("REG-API-007: the anonymous 409")
        await _add_user(private.engine, "alice")
        monkeypatch.setenv(MAX_USERS_VARIABLE, "1")
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        async with _browser(private) as client:
            response = await _register(client, "overflow")

        assert (response.status_code, _error_code(response)) == (409, "USER_LIMIT_REACHED"), f"{response.status_code} {response.text}"
        assert not _keys(response.json()) & ADMIN_ONLY_KEYS, f"an anonymous refusal must carry no count and no billing link: {response.text}"
        assert BILLING_LINK not in response.text, f"the billing link reached an anonymous caller: {response.text}"
        assert await _usernames(private.engine) == {"alice"}
        print_success("409 USER_LIMIT_REACHED, nothing for the administrator's eyes")


# ============================================================================
# 2. POST /auth/tokens/inspect — IN-PROCESS
# ============================================================================


def _details_shown(body: dict[str, Any]) -> dict[str, Any]:
    """The details a body shows beyond status and purpose: every detail key present with a value."""
    return {key: body[key] for key in TOKEN_DETAILS if body.get(key) is not None}


class TestInspect:
    """POST /auth/tokens/inspect: the status of a link, and its details only while it is valid."""

    @pytest.mark.asyncio
    async def test_a_valid_invitation_shows_its_expiry_role_and_email(self, private: _Private) -> None:
        """INSPECT-001: a valid invitation → 200 ``{status: valid, purpose: invite, expires_at, grants_admin, email}``, no username; asked without any session."""
        moment = utcnow()
        issued = await _issue(private.engine, grants_admin=True, email="invited@example.com", now=moment)

        async with _browser(private) as client:
            response = await _inspect(client, issued.token, "invite")

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        body = response.json()
        assert (body.get("status"), body.get("purpose")) == ("valid", "invite"), body
        assert _instant(body["expires_at"]) == moment + DEFAULT_TTL[INVITE], f"expires_at must be the invitation's: {body}"
        assert (body.get("grants_admin"), body.get("email"), body.get("username")) == (True, "invited@example.com", None), f"an invitation shows its role and e-mail, no username: {body}"

    @pytest.mark.asyncio
    async def test_a_valid_reset_link_shows_its_expiry_and_username_only(self, private: _Private) -> None:
        """INSPECT-002: a valid reset link → 200 ``{status: valid, purpose: password_reset, expires_at, username}``; no role, no e-mail."""
        owner = await _add_user(private.engine, "alice")
        issued = await _issue(private.engine, PASSWORD_RESET, user_id=owner)

        async with _browser(private) as client:
            response = await _inspect(client, issued.token, "password_reset")

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        body = response.json()
        assert (body.get("status"), body.get("purpose"), body.get("username")) == ("valid", "password_reset", "alice"), body
        assert _instant(body["expires_at"]) == ensure_utc(issued.record.expires_at)
        assert body.get("grants_admin") is None and body.get("email") is None, f"a reset link shows the username alone: {body}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("purpose", [INVITE, PASSWORD_RESET], ids=["invite", "password_reset"])
    @pytest.mark.parametrize("kind", DEAD_STATUSES)
    async def test_a_link_that_is_not_valid_shows_its_status_and_nothing_else(self, private: _Private, purpose: AccountTokenPurpose, kind: str) -> None:
        """INSPECT-003: unknown, expired, consumed or revoked → 200 with that status and the purpose asked, and no detail: no expiry, role, e-mail or username."""
        owner = await _add_user(private.engine, "alice")
        token = await _dead_token(private.engine, purpose, kind, owner)

        async with _browser(private) as client:
            response = await _inspect(client, token, purpose.value)

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        body = response.json()
        assert (body.get("status"), body.get("purpose")) == (kind, purpose.value), body
        assert _details_shown(body) == {}, f"a {kind} link must show nothing but its status: {body}"

    @pytest.mark.asyncio
    async def test_a_link_asked_as_the_other_purpose_is_unknown(self, private: _Private) -> None:
        """INSPECT-004: an invitation asked as a reset link, and a reset link asked as an invitation, are ``unknown`` and show nothing."""
        owner = await _add_user(private.engine, "alice")
        invitation = await _issue(private.engine, grants_admin=True, email="invited@example.com")
        reset_link = await _issue(private.engine, PASSWORD_RESET, user_id=owner)

        async with _browser(private) as client:
            crossed = [(await _inspect(client, invitation.token, "password_reset")).json(), (await _inspect(client, reset_link.token, "invite")).json()]

        assert [(body.get("status"), _details_shown(body)) for body in crossed] == [("unknown", {}), ("unknown", {})], crossed

    @pytest.mark.asyncio
    async def test_inspecting_consumes_nothing(self, private: _Private) -> None:
        """INSPECT-005: inspecting an invitation twice leaves it valid, unconsumed, and still good for a registration."""
        await _add_user(private.engine, "alice")
        issued = await _issue(private.engine)

        async with _browser(private) as client:
            statuses = [(await _inspect(client, issued.token, "invite")).json().get("status") for _ in range(2)]
            registered = await _register(client, "invited", invite_token=issued.token)

        assert statuses == ["valid", "valid"], statuses
        assert registered.status_code == 201, f"an inspected invitation must still open its account: {registered.status_code} {registered.text}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("purpose", ["magic_link", ""])
    async def test_a_purpose_outside_invite_and_password_reset_is_refused(self, private: _Private, purpose: str) -> None:
        """INSPECT-006: ``purpose`` is invite or password_reset: anything else is a request validation error, 422."""
        issued = await _issue(private.engine)

        async with _browser(private) as client:
            response = await _inspect(client, issued.token, purpose)

        assert response.status_code == 422, f"purpose {purpose!r}: {response.status_code} {response.text}"


# ============================================================================
# 3. POST /auth/password-reset — IN-PROCESS
# ============================================================================


@dataclass
class _ResetScene:
    """alice, signed in on a device before the reset, with two live reset links; bob with his own live reset link."""

    alice: int
    bob: int
    link: IssuedToken
    other_link: IssuedToken
    bobs_link: IssuedToken
    cookies: dict[str, str] = field(default_factory=dict)


async def _reset_scene(private: _Private) -> _ResetScene:
    alice = await _add_user(private.engine, "alice", password=PASSWORD)
    bob = await _add_user(private.engine, "bob", password=PASSWORD)
    scene = _ResetScene(
        alice=alice,
        bob=bob,
        link=await _issue(private.engine, PASSWORD_RESET, user_id=alice),
        other_link=await _issue(private.engine, PASSWORD_RESET, user_id=alice),
        bobs_link=await _issue(private.engine, PASSWORD_RESET, user_id=bob),
    )
    for name in ("alice", "bob"):
        async with _browser(private) as device:
            signed_in = await _sign_in(device, name, PASSWORD)
            assert signed_in.status_code == 200, f"setup: {name} must sign in: {signed_in.status_code} {signed_in.text}"
            scene.cookies[name] = signed_in.cookies[COOKIE]
    return scene


async def _me(private: _Private, cookie: str) -> int:
    """GET /auth/me with one session cookie, sent explicitly from a browser of its own: the status code."""
    async with _browser(private) as device:
        return (await device.get(ME, headers={"Cookie": f"{COOKIE}={cookie}"})).status_code


class TestPasswordReset:
    """POST /auth/password-reset: a reset link sets the password once, and signs every device out."""

    @pytest.mark.asyncio
    async def test_a_reset_sets_the_password_ends_every_session_and_revokes_the_other_links(self, private: _Private) -> None:
        """RESET-001: 200; the new password signs in and the old one does not; the cookie alice had is 401, bob's still works; the link is consumed, alice's other link revoked, bob's link still valid."""
        print_section("RESET-001: a password reset")
        scene = await _reset_scene(private)
        assert await _me(private, scene.cookies["alice"]) == 200, "barrier: alice's session works before the reset"

        async with _browser(private) as client:
            response = await client.post(RESET, json={"token": scene.link.token, "new_password": NEW_PASSWORD})
            with_new, with_old = await _sign_in(client, "alice", NEW_PASSWORD), await _sign_in(client, "alice", PASSWORD)

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        assert (with_new.status_code, with_old.status_code) == (200, 401), f"the new password must sign in and the old one must not: {with_new.status_code}, {with_old.status_code}"
        assert await _me(private, scene.cookies["alice"]) == 401, "a session issued before the reset must end"
        assert await _me(private, scene.cookies["bob"]) == 200, "another account's session must not notice"
        statuses = {name: await _status(private.engine, link.token, PASSWORD_RESET) for name, link in (("link", scene.link), ("other link", scene.other_link), ("bob's link", scene.bobs_link))}
        assert statuses == {"link": TokenStatus.CONSUMED, "other link": TokenStatus.REVOKED, "bob's link": TokenStatus.VALID}, statuses
        print_success("password set, sessions ended, the other link revoked, bob untouched")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("kind", [*DEAD_STATUSES, "invitation"])
    async def test_an_invalid_link_answers_400_token_invalid_and_changes_nothing(self, private: _Private, kind: str) -> None:
        """RESET-002: a link never issued, expired, consumed or revoked, or an invitation → 400 ``TOKEN_INVALID``; the password, the session version and alice's live link as they were."""
        scene = await _reset_scene(private)
        token = (await _issue(private.engine)).token if kind == "invitation" else await _dead_token(private.engine, PASSWORD_RESET, kind, scene.alice)
        before = await _account(private.engine, scene.alice)

        async with _browser(private) as client:
            response = await client.post(RESET, json={"token": token, "new_password": NEW_PASSWORD})

        assert (response.status_code, _error_code(response)) == (400, "TOKEN_INVALID"), f"{kind} link: {response.status_code} {response.text}"
        assert await _account(private.engine, scene.alice) == before, "a refused reset must change neither the password nor the session version"
        assert await _me(private, scene.cookies["alice"]) == 200
        assert await _status(private.engine, scene.link.token, PASSWORD_RESET) == TokenStatus.VALID

    @pytest.mark.asyncio
    async def test_a_link_works_once(self, private: _Private) -> None:
        """RESET-003: the same link a second time → 400 ``TOKEN_INVALID``; the password stays the first reset's."""
        scene = await _reset_scene(private)

        async with _browser(private) as client:
            first = await client.post(RESET, json={"token": scene.link.token, "new_password": NEW_PASSWORD})
            second = await client.post(RESET, json={"token": scene.link.token, "new_password": "Another-Pass-2026"})
            signed_in = await _sign_in(client, "alice", NEW_PASSWORD)

        assert first.status_code == 200, f"{first.status_code} {first.text}"
        assert (second.status_code, _error_code(second)) == (400, "TOKEN_INVALID"), f"{second.status_code} {second.text}"
        assert signed_in.status_code == 200, "the password must be the first reset's"

    @pytest.mark.asyncio
    async def test_a_password_shorter_than_the_api_rule_is_refused_and_keeps_the_link(self, private: _Private) -> None:
        """RESET-004: a 7-character password → 422 (the API's rule until decision 37); the link stays valid, the password unchanged."""
        scene = await _reset_scene(private)
        before = await _account(private.engine, scene.alice)

        async with _browser(private) as client:
            response = await client.post(RESET, json={"token": scene.link.token, "new_password": "Short1!"})

        assert response.status_code == 422, f"{response.status_code} {response.text}"
        assert await _status(private.engine, scene.link.token, PASSWORD_RESET) == TokenStatus.VALID
        assert await _account(private.engine, scene.alice) == before

    @pytest.mark.asyncio
    async def test_the_new_password_is_hashed_off_the_event_loop(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """RESET-005: ``bcrypt.hashpw`` — where every hashing path ends — runs in a worker thread, never on the event loop serving the request."""
        scene = await _reset_scene(private)
        threads: list[int] = []
        real_hashpw = bcrypt.hashpw

        def spying_hashpw(password: bytes, salt: bytes) -> bytes:
            threads.append(threading.get_ident())
            return real_hashpw(password, salt)

        monkeypatch.setattr(bcrypt, "hashpw", spying_hashpw)
        loop_thread = threading.get_ident()
        async with _browser(private) as client:
            response = await client.post(RESET, json={"token": scene.link.token, "new_password": NEW_PASSWORD})

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        assert threads, "barrier: bcrypt.hashpw was never called"
        assert loop_thread not in threads, "the reset hashed the password on the event loop: it belongs in await asyncio.to_thread(...)"


# ============================================================================
# 4. GET /system/instance — IN-PROCESS
# ============================================================================


class TestInstanceAccounts:
    """GET /system/instance: the effective registration mode, public, and nothing about users."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("row", "variable", "mode", "locked"),
        [
            pytest.param(None, None, "open", False, id="new-install-open"),
            pytest.param("invite", None, "invite", False, id="row-invite"),
            pytest.param("open", "disabled", "disabled", True, id="variable-disabled"),
            pytest.param("disabled", "invite", "invite", True, id="variable-invite"),
            pytest.param("open", "sometimes", "disabled", True, id="invalid-variable-closes"),
        ],
    )
    async def test_accounts_holds_the_effective_mode_and_whether_the_variable_locks_it(self, private: _Private, monkeypatch: pytest.MonkeyPatch, row: Optional[str], variable: Optional[str], mode: str, locked: bool) -> None:
        """INSTANCE-001: ``accounts`` is exactly ``{registration_mode, registration_locked}``, the effective mode and whether the variable sets it; no session needed."""
        if row is not None:
            await _set_mode_row(private.engine, row)
        if variable is not None:
            monkeypatch.setenv(REGISTRATION_VARIABLE, variable)

        async with _browser(private) as client:
            response = await client.get(INSTANCE)

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        assert response.json().get("accounts") == {"registration_mode": mode, "registration_locked": locked}, f"row {row!r}, {REGISTRATION_VARIABLE}={variable!r}: {response.text}"

    @pytest.mark.asyncio
    async def test_the_public_configuration_says_nothing_about_users(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """INSTANCE-002: with accounts, a live invitation, a limit and a billing link configured, the body is exactly ``profile``, ``accounts`` and ``email``, ``accounts`` exactly its two fields, and the link nowhere."""
        owner = await _add_user(private.engine, "alice", admin=True)
        await _issue(private.engine, created_by_user_id=owner)
        monkeypatch.setenv(MAX_USERS_VARIABLE, "5")
        monkeypatch.setenv(BILLING_URL_VARIABLE, BILLING_LINK)

        async with _browser(private) as client:
            response = await client.get(INSTANCE)

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        body = response.json()
        assert set(body) == {"profile", "accounts", "email"}, f"the public configuration holds nothing undeclared: {body}"
        assert set(body["accounts"]) == {"registration_mode", "registration_locked"}, f"accounts says nothing about users: {body['accounts']}"
        assert BILLING_LINK not in response.text


# ============================================================================
# 5. PATCH /settings/global/bulk — REGISTRATION_MODE LOCKED BY THE VARIABLE, IN-PROCESS
# ============================================================================


async def _admin_browser_cookie(private: _Private) -> str:
    """An administrator of the private instance, signed in: the session cookie."""
    await _add_user(private.engine, "admin", password=PASSWORD, admin=True)
    async with _browser(private) as device:
        signed_in = await _sign_in(device, "admin", PASSWORD)
    assert signed_in.status_code == 200, f"setup: the administrator must sign in: {signed_in.status_code} {signed_in.text}"
    return signed_in.cookies[COOKIE]


async def _bulk(private: _Private, cookie: str, items: list[tuple[str, str]]) -> httpx.Response:
    """PATCH /settings/global/bulk as the holder of ``cookie``, sent explicitly from a browser of its own."""
    async with _browser(private) as device:
        return await device.patch(BULK, json={"items": [{"key": key, "value": value} for key, value in items]}, headers={"Cookie": f"{COOKIE}={cookie}"})


async def _stored_settings(engine: AsyncEngine, *keys: str) -> dict[str, tuple[str, Optional[datetime], Optional[int]]]:
    """``{key: (value, updated_at, updated_by_user_id)}`` for ``keys``, read fresh."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(GlobalSetting).where(GlobalSetting.key.in_(keys)))).scalars().all()  # type: ignore[attr-defined]
    return {row.key: (row.value, row.updated_at, row.updated_by_user_id) for row in rows}


class TestRegistrationModeLockedByTheVariable:
    """PATCH /settings/global/bulk on ``registration_mode``: the variable wins, and says so."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("variable", [pytest.param("invite", id="variable-set"), pytest.param("sometimes", id="invalid-variable-locks-too")])
    async def test_writing_the_mode_while_the_variable_sets_it_answers_409_and_saves_nothing(self, private: _Private, monkeypatch: pytest.MonkeyPatch, variable: str) -> None:
        """LOCK-001: ``LIBREFOLIO_REGISTRATION`` set — valid, or invalid and therefore closing — → 409 ``SETTING_LOCKED_BY_ENV``; the row's value, time and author as they were."""
        cookie = await _admin_browser_cookie(private)
        before = await _stored_settings(private.engine, MODE_KEY)
        assert before.get(MODE_KEY, ("",))[0] == "open", f"barrier: a new install's registration_mode row is seeded open: {before}"
        monkeypatch.setenv(REGISTRATION_VARIABLE, variable)

        response = await _bulk(private, cookie, [(MODE_KEY, "disabled")])

        assert (response.status_code, _error_code(response)) == (409, "SETTING_LOCKED_BY_ENV"), f"{REGISTRATION_VARIABLE}={variable!r}: {response.status_code} {response.text}"
        assert await _stored_settings(private.engine, MODE_KEY) == before, "a locked write must save nothing"

    @pytest.mark.asyncio
    async def test_a_request_mixing_the_locked_mode_with_another_setting_saves_neither(self, private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """LOCK-002: ``registration_mode`` and ``session_ttl_hours`` in one request while the variable is set → 409, and neither is saved: the bulk update stays all or nothing."""
        cookie = await _admin_browser_cookie(private)
        before = await _stored_settings(private.engine, MODE_KEY, "session_ttl_hours")
        assert set(before) == {MODE_KEY, "session_ttl_hours"}, f"barrier: both rows are seeded: {before}"
        monkeypatch.setenv(REGISTRATION_VARIABLE, "invite")

        response = await _bulk(private, cookie, [("session_ttl_hours", "48"), (MODE_KEY, "disabled")])

        assert (response.status_code, _error_code(response)) == (409, "SETTING_LOCKED_BY_ENV"), f"{response.status_code} {response.text}"
        assert await _stored_settings(private.engine, MODE_KEY, "session_ttl_hours") == before, "nothing of a refused request may be saved"

    @pytest.mark.asyncio
    async def test_without_the_variable_the_mode_is_saved_within_its_choices(self, private: _Private) -> None:
        """LOCK-003: no variable: ``invite`` → 200 and saved, by the administrator; ``closed`` → 422, nothing saved."""
        cookie = await _admin_browser_cookie(private)

        saved = await _bulk(private, cookie, [(MODE_KEY, "invite")])
        after_save = await _stored_settings(private.engine, MODE_KEY)
        refused = await _bulk(private, cookie, [(MODE_KEY, "closed")])

        assert saved.status_code == 200, f"{saved.status_code} {saved.text}"
        assert after_save[MODE_KEY][0] == "invite" and after_save[MODE_KEY][2] is not None, f"saved, with its author: {after_save}"
        assert refused.status_code == 422, f"only open, invite and disabled: {refused.status_code} {refused.text}"
        assert await _stored_settings(private.engine, MODE_KEY) == after_save


# ============================================================================
# 5b. THE SETTING'S TYPE, AND THE URL VARIABLES (REVIEW OF 15/10) — IN-PROCESS
# ============================================================================


class TestReviewOfTheSettingAndTheUrls:
    """The ``registration_mode`` row a new install seeds, and what an invalid URL variable does to registration: nothing."""

    @pytest.mark.asyncio
    async def test_a_new_install_seeds_registration_mode_open_as_a_str_setting(self, private: _Private) -> None:
        """SETTING-001: on a new install, the public ``GET /settings/global/registration_mode`` answers ``open`` with ``value_type`` ``str`` — the documented type of every text setting ("str", "int", "bool", "json"), and the one migration 006 writes on an upgraded install."""
        async with _browser(private) as client:
            response = await client.get(MODE_SETTING)

        assert response.status_code == 200, f"{response.status_code} {response.text}"
        body = response.json()
        assert (body.get("key"), body.get("value"), body.get("value_type")) == (MODE_KEY, "open", "str"), f"a new install seeds {MODE_KEY} open, as a 'str' setting: {body}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("variable", [PUBLIC_URL_VARIABLE, BILLING_URL_VARIABLE])
    async def test_an_invalid_url_variable_leaves_registration_open(self, private: _Private, monkeypatch: pytest.MonkeyPatch, variable: str) -> None:
        """URL-001 — GUARD: an invalid ``LIBREFOLIO_PUBLIC_URL`` or ``LIBREFOLIO_BILLING_URL`` closes nothing: ``GET /system/instance`` still answers open, not locked, and an open ``POST /auth/register`` still creates a regular account.

        A guard: these endpoints do not read the URL variables today. It keeps a later "invalid account configuration →
        closed" from catching a mistyped link along with the settings that really close registration.
        """
        await _add_user(private.engine, "alice")
        monkeypatch.setenv(variable, "www.example.com/folio")

        async with _browser(private) as client:
            instance = await client.get(INSTANCE)
            registered = await _register(client, "walkin")

        assert instance.status_code == 200 and instance.json().get("accounts") == {"registration_mode": "open", "registration_locked": False}, f"an invalid {variable} must leave the instance open: {instance.status_code} {instance.text}"
        assert registered.status_code == 201, f"an invalid {variable} must not stop an open registration: {registered.status_code} {registered.text}"
        assert registered.json()["user"]["is_superuser"] is False


# ============================================================================
# 6. ON THE LANE'S SERVER — NOTHING GLOBAL CHANGES
# ============================================================================


def _lane_engine() -> AsyncEngine:
    """The lane's test database, the one its server serves: the live cases write their own rows there, and delete them."""
    is_test_db, database_url = verify_test_database()
    assert is_test_db, f"Refusing to write outside the lane's test database: {database_url}"
    return get_async_engine()


@dataclass
class _LaneRows:
    """What a live case wrote in the lane's database: accounts by name — even one a red let through —, invitations by id."""

    usernames: list[str] = field(default_factory=list)
    token_ids: list[int] = field(default_factory=list)

    def new_username(self, prefix: str) -> str:
        username = f"{prefix}_{uuid.uuid4().hex[:12]}"
        self.usernames.append(username)
        return username


async def _delete_lane_rows(rows: _LaneRows) -> list[str]:
    """Delete the accounts (through user_service.delete_user; their own tokens go with them) and then the tokens; what failed."""
    errors: list[str] = []
    engine = _lane_engine()
    for username in rows.usernames:
        async with AsyncSession(engine) as session:
            try:
                user = await user_service.get_user_by_username(session, username)
                if user is not None:
                    await user_service.delete_user(session, user.id)
            except Exception as exc:  # every row gets its attempt; the failures are reported together
                errors.append(f"user {username}: {exc!r}")
    if rows.token_ids:
        async with AsyncSession(engine) as session:
            await session.execute(delete(AccountToken).where(AccountToken.id.in_(rows.token_ids)))  # type: ignore[attr-defined]
            await session.commit()
    return errors


@pytest_asyncio.fixture
async def lane(test_server) -> AsyncIterator[_LaneRows]:
    """The lane's server in ``open`` mode, as every unit that registers its own users needs it — read from GET /system/instance, never set —; what the case writes is deleted at teardown, after a red too."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/system/instance", timeout=TIMEOUT)
    accounts = response.json().get("accounts") if response.status_code == 200 else None
    assert isinstance(accounts, dict) and accounts.get("registration_mode") == "open", f"Precondition: the lane's server must publish accounts.registration_mode = open in GET /system/instance (every unit registers its own users; nothing here changes the mode): {response.status_code} {response.text}"
    rows = _LaneRows()
    try:
        yield rows
    finally:
        errors = await _delete_lane_rows(rows)
        assert not errors, f"Teardown: could not delete what this test wrote in the lane: {errors}"


async def _assert_lane_has_an_account() -> None:
    """Precondition of a live registration, read in the lane's database before it: the lane already holds an account.

    On an empty lane the account about to register would be its first, hence its administrator in every mode, and with
    a valid invitation of any role, which it spends: the case would make the shared lane's administrator. An invalid
    invitation is refused even then, so LIVE-001 needs no check. Existence only, never a count: the lane is shared, and
    its accounts come and go with every concurrent unit.
    """
    async with AsyncSession(_lane_engine()) as session:
        someone = (await session.execute(select(User.id).limit(1))).scalar()
    assert someone is not None, "Precondition: the lane has no account yet, so this registration would make its administrator: the api setup (db populate) did not run on this lane"


async def _live_register(username: str, **body: Any) -> httpx.Response:
    async with httpx.AsyncClient() as client:
        return await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": PASSWORD, **body}, timeout=TIMEOUT)


async def _live_post(path: str, body: dict[str, Any]) -> httpx.Response:
    """An anonymous POST to the lane's server: a client of its own, no cookie."""
    async with httpx.AsyncClient() as client:
        return await client.post(f"{API_BASE}{path}", json=body, timeout=TIMEOUT)


async def _live_sign_in(username: str, password: str) -> httpx.Response:
    return await _live_post("/auth/login", {"username": username, "password": password})


async def _live_me(cookie: str) -> int:
    async with httpx.AsyncClient() as client:
        return (await client.get(f"{API_BASE}/auth/me", headers={"Cookie": f"{COOKIE}={cookie}"}, timeout=TIMEOUT)).status_code


class TestOnTheLane:
    """The public endpoints on the lane's real server, in its own mode: own accounts, own tokens, no setting written."""

    @pytest.mark.asyncio
    async def test_an_unknown_invitation_is_refused_and_creates_no_account(self, lane: _LaneRows) -> None:
        """LIVE-001: POST /auth/register with an invitation never issued → 400 ``INVITE_INVALID``, and the name stays free."""
        username = lane.new_username("live_unknown_invite")

        response = await _live_register(username, invite_token=NEVER_ISSUED)

        assert (response.status_code, _error_code(response)) == (400, "INVITE_INVALID"), f"{response.status_code} {response.text}"
        async with AsyncSession(_lane_engine()) as session:
            assert await user_service.get_user_by_username(session, username) is None, "a refused registration must create no account"

    @pytest.mark.asyncio
    async def test_an_invitation_opens_its_account_and_is_consumed_by_it(self, lane: _LaneRows) -> None:
        """LIVE-002: an invitation issued in the lane's database opens a regular account (201) and is consumed by that account. A user invitation: no administrator is ever made on the shared lane."""
        await _assert_lane_has_an_account()
        issued = await _issue(_lane_engine())
        lane.token_ids.append(issued.record.id)
        username = lane.new_username("live_invited")

        response = await _live_register(username, invite_token=issued.token)

        assert response.status_code == 201, f"{response.status_code} {response.text}"
        user = response.json()["user"]
        assert user["is_superuser"] is False, f"a user invitation opened an administrator account, {username}: the invitation's role was not applied, or {username} registered as the lane's first account, hence its administrator: the api setup (db populate) did not run on this lane"
        assert (await _token_row(_lane_engine(), issued.record.id)).consumed_by_user_id == user["id"], "the invitation must be consumed by the account it opened"

    @pytest.mark.asyncio
    async def test_a_reset_link_is_inspected_used_and_signs_the_account_out(self, lane: _LaneRows) -> None:
        """LIVE-003: an account of this test with two reset links: inspect → valid with its username; reset → 200; the session from before → 401; the new password signs in; the other link → revoked."""
        print_section("LIVE-003: a reset link on the lane's server")
        await _assert_lane_has_an_account()
        username = lane.new_username("live_reset")
        registered = await _live_register(username)
        assert registered.status_code == 201, f"setup: {registered.status_code} {registered.text}"
        user_id = registered.json()["user"]["id"]
        signed_in = await _live_sign_in(username, PASSWORD)
        assert signed_in.status_code == 200, f"setup: {signed_in.status_code} {signed_in.text}"
        old_cookie = signed_in.cookies[COOKIE]
        link = await _issue(_lane_engine(), PASSWORD_RESET, user_id=user_id)
        other_link = await _issue(_lane_engine(), PASSWORD_RESET, user_id=user_id)
        lane.token_ids.extend([link.record.id, other_link.record.id])

        inspected = await _live_post("/auth/tokens/inspect", {"token": link.token, "purpose": "password_reset"})
        reset = await _live_post("/auth/password-reset", {"token": link.token, "new_password": NEW_PASSWORD})
        old_session = await _live_me(old_cookie)
        with_new = await _live_sign_in(username, NEW_PASSWORD)
        other = await _live_post("/auth/tokens/inspect", {"token": other_link.token, "purpose": "password_reset"})

        assert inspected.status_code == 200 and (inspected.json().get("status"), inspected.json().get("username")) == ("valid", username), f"{inspected.status_code} {inspected.text}"
        assert reset.status_code == 200, f"{reset.status_code} {reset.text}"
        assert old_session == 401, "the session from before the reset must end"
        assert with_new.status_code == 200, f"the new password must sign in: {with_new.status_code} {with_new.text}"
        assert other.json().get("status") == "revoked", f"the account's other reset link must be revoked: {other.text}"
        print_success("inspected, reset, signed out, the other link revoked")
