"""``POST /email/email-change/confirm``: the click that completes the change of the owner's address (release 1.3, workstream A, lot A5-1b part 2).

The startup sync (``test_services/test_owner_email_change.py``) emails a link to the NEW address the host put in
``LIBREFOLIO_ADMIN_EMAIL``; this module pins what the public route answers when it is clicked. The contract:

1. The route is anonymous: no session needed, none set. Body ``{token}`` (1 to 256 characters, no other field → 422).
2. 200 ``{"username"}``. In ONE transaction: the token consumed; the owner's address becomes the token's address; the
   address is verified (``email_verified_at``); every session of the owner ends (``session_version`` raised: the cookie
   issued before is refused); the owner's other ``email_change`` links and its password-reset links (a mailbox that is
   no longer its own) are revoked. After the commit, the notice to the OLD address is scheduled (``email_changed_work``)
   as ``PUT /auth/profile`` does. The password is unchanged: the new address signs in, the old one does not. The owner
   stays protected: by its flag, and now by its address too.
3. 400 ``{"detail": {"error_code": "TOKEN_INVALID", "status", "message"}}`` exactly as the verification confirm:
   ``expired``, ``consumed``, ``revoked``, ``unknown``; a token of another purpose is ``unknown`` and left untouched.
   ``revoked`` also (the token revoked, nothing changed) when: the host changed the variable again, the profile is no
   longer managed, the token's account is no longer the recorded owner, or another account took the address meanwhile.
4. No log line holds the token or an address.
5. The route function is ``confirm_owner_email_change`` with ``EmailChangeConfirmRequest`` / ``EmailChangeConfirmResponse``
   (``username``): the client alias is ``confirm_owner_email_change_api_v1_email_email_change_confirm_post``.

Pure: the real auth and email routers run in-process on a private SQLite file under ``tmp_path``; accounts are rows with a
real bcrypt hash at cost 4; tokens are issued by the token service or by the owner sync. ``email_changed_work`` is
replaced by a recorder. The lane's backend is never called.
"""

from __future__ import annotations

import contextlib
import importlib
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import email as email_api
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import IssuedToken, TokenStatus
from backend.app.services.email import delivery, flows, smtp
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section

CONFIRM = f"{API_V1_PREFIX}/email/email-change/confirm"
LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
BASE_URL = "http://test"
TIMEOUT = 30.0

PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
SMTP_PREFIX = "LIBREFOLIO_SMTP_"
ADMIN_PREFIX = "LIBREFOLIO_ADMIN_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
INHERITED = (PUBLIC_URL_VARIABLE, "LIBREFOLIO_BLOCKED", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_REGISTRATION", PROFILE_VARIABLE)

OLD_EMAIL = "owner@zq-ownapi.example.com"
NEW_EMAIL = "new.owner@zq-ownapi.example.com"
NEWER_EMAIL = "newer.owner@zq-ownapi.example.com"
PASSWORD = "Owner-Api-Pass-2026"
OWNER = "ownapi_owner"
PUBLIC_URL = "https://folio.zq-ownapi.example.com:8443/app"

CHANGE = AccountTokenPurpose.EMAIL_CHANGE
NEVER_ISSUED = "never-issued-owner-change-0123456789abcdef"
INVALID_MESSAGE_KEYS = {"error_code", "status", "message"}


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def _environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in list(os.environ):
        if name.startswith((SMTP_PREFIX, ADMIN_PREFIX)) or name in INHERITED:
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LIBREFOLIO_TEST_MODE", "1")
    monkeypatch.setenv("LIBREFOLIO_TEST_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, NEW_EMAIL)


@pytest.fixture(autouse=True)
def _private_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """The recorded-owner knowledge of the process, the hourly budget and the SMTP transport: private, or refused."""
    if hasattr(user_service, "_recorded_owner"):
        monkeypatch.setattr(user_service, "_recorded_owner", user_service._recorded_owner)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", SlidingWindowLimiter(50, 3600, max_keys=1))

    def refuse(_server: object, _message: object) -> None:
        raise AssertionError("an owner-change API test reached the SMTP transport")

    monkeypatch.setattr(smtp, "deliver", refuse)


@dataclass
class Notices:
    """The calls of ``email_changed_work`` the route scheduled."""

    calls: list[tuple[int, str, str]]


@pytest.fixture(autouse=True)
def notices(monkeypatch: pytest.MonkeyPatch) -> Notices:
    recorded = Notices(calls=[])

    async def record(user_id: int, old_address: str, new_address: str, *, engine: Any = None) -> None:
        recorded.calls.append((user_id, old_address, new_address))

    monkeypatch.setattr(flows, "email_changed_work", record)
    return recorded


@dataclass(frozen=True)
class _Private:
    engine: AsyncEngine
    app: FastAPI


def _app(engine: AsyncEngine) -> FastAPI:
    app = FastAPI()
    for router in (auth_api.router, email_api.router):
        app.include_router(router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'owner-api.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_app(engine))
    finally:
        await engine.dispose()


# =============================================================================
# HELPERS
# =============================================================================


async def _add_user(engine: AsyncEngine, username: str, email: str, *, instance_owner: bool = False, admin: bool = False) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email, hashed_password=auth_service.hash_password(PASSWORD), is_active=True, is_superuser=admin)
        if instance_owner:
            user.is_instance_owner = True
        session.add(user)
        await session.commit()
    return user


async def _owner(engine: AsyncEngine) -> User:
    return await _add_user(engine, OWNER, OLD_EMAIL, instance_owner=True, admin=True)


async def _link(engine: AsyncEngine, user: User, email: str = NEW_EMAIL, *, purpose: AccountTokenPurpose = CHANGE, now: Any = None) -> IssuedToken:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, user_id=user.id, email=email, now=now or utcnow())
        await session.commit()
    return issued


async def _row(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        row = await session.get(User, user_id)
    assert row is not None
    return row


async def _tokens(engine: AsyncEngine, purpose: AccountTokenPurpose) -> list[AccountToken]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return list((await session.execute(select(AccountToken).where(AccountToken.purpose == purpose).order_by(AccountToken.id))).scalars().all())


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose = CHANGE) -> TokenStatus:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return (await token_service.inspect_token(session, token, purpose)).status


@contextlib.asynccontextmanager
async def _browser(private: _Private) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=private.app, client=("198.51.100.7", 40001))
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as browser:
        yield browser


async def _confirm(private: _Private, token: str) -> httpx.Response:
    async with _browser(private) as browser:
        return await browser.post(CONFIRM, json={"token": token})


def _detail(response: httpx.Response) -> dict[str, Any]:
    detail = response.json().get("detail")
    assert isinstance(detail, dict), f"expected a coded refusal in detail: {response.status_code} {response.text}"
    return detail


async def _refused(private: _Private, token: str, status: str) -> None:
    response = await _confirm(private, token)
    assert response.status_code == 400, response.text
    detail = _detail(response)
    assert set(detail) == INVALID_MESSAGE_KEYS and detail["error_code"] == "TOKEN_INVALID" and detail["status"] == status, detail


# =============================================================================
# THE ROUTE
# =============================================================================


def test_the_route_and_its_models_have_the_agreed_names() -> None:
    """OWNAPI-001: the route function is ``confirm_owner_email_change`` on ``POST /api/v1/email/email-change/confirm`` (operation id ``confirm_owner_email_change_api_v1_email_email_change_confirm_post``: the client alias the web app uses), with ``EmailChangeConfirmRequest`` / ``EmailChangeConfirmResponse`` (``username``)."""
    app = FastAPI()
    app.include_router(email_api.router, prefix=API_V1_PREFIX)
    schema = app.openapi()
    assert CONFIRM in schema["paths"], "red until A5-1b part 2: no POST /email/email-change/confirm"
    operation = schema["paths"][CONFIRM]["post"]
    assert set(schema["paths"][CONFIRM]) == {"post"}
    assert operation["operationId"] == "confirm_owner_email_change_api_v1_email_email_change_confirm_post"
    assert operation["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith("/EmailChangeConfirmRequest")
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/EmailChangeConfirmResponse")
    schemas = schema["components"]["schemas"]
    assert set(schemas["EmailChangeConfirmResponse"]["properties"]) == {"username"}
    assert set(schemas["EmailChangeConfirmRequest"]["properties"]) == {"token"}


@pytest.mark.asyncio
async def test_the_click_changes_the_address_and_ends_the_sessions(private: _Private, notices: Notices) -> None:
    """OWNAPI-010: a live link: 200 ``{username}``; the owner's address is the token's; verified; ``session_version`` raised and the cookie issued before refused; the password unchanged — the new address signs in, the old one does not —; the link consumed; the owner's other change links and its reset links revoked; the notice to the OLD address scheduled; no session needed or set."""
    print_section("OWNAPI-010: the click")
    owner = await _owner(private.engine)
    issued = await _link(private.engine, owner)
    older = await _link(private.engine, owner, NEWER_EMAIL)
    reset = await _link(private.engine, owner, OLD_EMAIL, purpose=AccountTokenPurpose.PASSWORD_RESET)
    async with _browser(private) as signed_in:
        login = await signed_in.post(LOGIN, json={"username": OLD_EMAIL, "password": PASSWORD})
        assert login.status_code == 200, login.text
        assert (await signed_in.get(ME)).status_code == 200, "barrier: the session works before the click"
        before = (await _row(private.engine, owner.id)).session_version

        response = await _confirm(private, issued.token)

        assert response.status_code == 200, response.text
        assert response.json() == {"username": OWNER}
        assert "set-cookie" not in response.headers, "the click needs no session and opens none"
        row = await _row(private.engine, owner.id)
        assert row.email == NEW_EMAIL and row.email_verified_at is not None and row.is_instance_owner is True
        assert row.session_version > before
        assert (await signed_in.get(ME)).status_code == 401, "the session issued before the click is refused"
    assert await _status(private.engine, issued.token) == TokenStatus.CONSUMED
    assert await _status(private.engine, older.token) == TokenStatus.REVOKED, "the owner's other change links are revoked"
    assert await _status(private.engine, reset.token, AccountTokenPurpose.PASSWORD_RESET) == TokenStatus.REVOKED, "a reset link asked to the old mailbox no longer works"
    assert notices.calls == [(owner.id, OLD_EMAIL, NEW_EMAIL)]
    async with _browser(private) as fresh:
        assert (await fresh.post(LOGIN, json={"username": OLD_EMAIL, "password": PASSWORD})).status_code == 401, "the old address no longer signs in"
        assert (await fresh.post(LOGIN, json={"username": NEW_EMAIL, "password": PASSWORD})).status_code == 200, "the new one does, with the same password"


@pytest.mark.asyncio
async def test_the_owner_is_protected_afterwards_by_flag_and_by_address(private: _Private) -> None:
    """OWNAPI-011: after the click the owner is protected by its flag AND its address equals the variable — taking away either still protects it."""
    owner = await _owner(private.engine)
    issued = await _link(private.engine, owner)
    assert user_service.account_protection(await _row(private.engine, owner.id)) == user_service.PAYING_ADMINISTRATOR, "barrier: protected before, by the flag"

    assert (await _confirm(private, issued.token)).status_code == 200

    row = await _row(private.engine, owner.id)
    assert user_service.account_protection(row) == user_service.PAYING_ADMINISTRATOR
    unflagged = User(id=row.id, username=row.username, email=row.email, hashed_password="x", is_instance_owner=False)
    assert user_service.account_protection(unflagged) == user_service.PAYING_ADMINISTRATOR, "by its address"
    elsewhere = User(id=row.id, username=row.username, email=OLD_EMAIL, hashed_password="x", is_instance_owner=True)
    assert user_service.account_protection(elsewhere) == user_service.PAYING_ADMINISTRATOR, "by its flag"


@pytest.mark.asyncio
async def test_the_token_is_not_in_the_log(private: _Private) -> None:
    """OWNAPI-012: neither the token nor an address is in any log line of a click, or of a refused one."""
    owner = await _owner(private.engine)
    issued = await _link(private.engine, owner)
    with capture_logs() as events:
        await _confirm(private, issued.token)
        await _confirm(private, issued.token)
    text = "\n".join(str(event) for event in events).lower()
    assert issued.token.lower() not in text and NEW_EMAIL not in text and OLD_EMAIL not in text


@pytest.mark.asyncio
@pytest.mark.parametrize("how", ["expired", "consumed", "revoked"])
async def test_a_dead_link_says_why(private: _Private, notices: Notices, how: str) -> None:
    """OWNAPI-020: an expired, spent or revoked link: 400 ``TOKEN_INVALID`` with that ``status``; nothing changes and no notice."""
    owner = await _owner(private.engine)
    issued = await _link(private.engine, owner, now=utcnow() - timedelta(days=8) if how == "expired" else None)
    if how != "expired":
        async with AsyncSession(private.engine) as session:
            if how == "consumed":
                assert await token_service.consume_token(session, issued.token, CHANGE) is not None
            else:
                assert await token_service.revoke_tokens(session, token_id=issued.record.id) == 1
            await session.commit()

    await _refused(private, issued.token, how)

    assert (await _row(private.engine, owner.id)).email == OLD_EMAIL and notices.calls == []


@pytest.mark.asyncio
async def test_an_unknown_token_is_unknown(private: _Private) -> None:
    """OWNAPI-021: a token nobody issued: ``unknown``."""
    await _owner(private.engine)
    await _refused(private, NEVER_ISSUED, "unknown")


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", [AccountTokenPurpose.EMAIL_VERIFICATION, AccountTokenPurpose.PASSWORD_RESET, AccountTokenPurpose.ADMIN_SETUP])
async def test_a_token_of_another_purpose_is_unknown_and_untouched(private: _Private, notices: Notices, purpose: AccountTokenPurpose) -> None:
    """OWNAPI-022: a verification, reset or setup token of the owner: ``unknown`` here, and still unspent afterwards."""
    owner = await _owner(private.engine)
    issued = await _link(private.engine, owner, NEW_EMAIL, purpose=purpose)
    await _refused(private, issued.token, "unknown")
    assert await _status(private.engine, issued.token, purpose) == TokenStatus.VALID
    assert (await _row(private.engine, owner.id)).email == OLD_EMAIL and notices.calls == []


@pytest.mark.asyncio
async def test_an_invitation_token_is_unknown_and_untouched(private: _Private) -> None:
    """OWNAPI-022b: an invitation, which belongs to no account: ``unknown``, unspent."""
    await _owner(private.engine)
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        invite = await token_service.issue_token(session, AccountTokenPurpose.INVITE, email=NEW_EMAIL)
        await session.commit()
    await _refused(private, invite.token, "unknown")
    assert await _status(private.engine, invite.token, AccountTokenPurpose.INVITE) == TokenStatus.VALID


@pytest.mark.asyncio
async def test_a_variable_changed_again_revokes_the_link(private: _Private, monkeypatch: pytest.MonkeyPatch, notices: Notices) -> None:
    """OWNAPI-030: the host put another address in the variable after this link was emailed: ``revoked``, the link revoked, nothing changed."""
    owner = await _owner(private.engine)
    issued = await _link(private.engine, owner, NEW_EMAIL)
    monkeypatch.setenv(ADMIN_EMAIL_VARIABLE, NEWER_EMAIL)
    version = (await _row(private.engine, owner.id)).session_version

    await _refused(private, issued.token, "revoked")

    row = await _row(private.engine, owner.id)
    assert (row.email, row.session_version) == (OLD_EMAIL, version) and notices.calls == []
    assert await _status(private.engine, issued.token) == TokenStatus.REVOKED


@pytest.mark.asyncio
async def test_an_address_taken_meanwhile_refuses_the_change(private: _Private, notices: Notices) -> None:
    """OWNAPI-031: another account took the address between the email and the click: ``revoked``, the link revoked, the owner's address and sessions as they were."""
    owner = await _owner(private.engine)
    issued = await _link(private.engine, owner)
    await _add_user(private.engine, "ownapi_stranger", NEW_EMAIL.upper().replace("ZQ-OWNAPI.EXAMPLE.COM", "zq-ownapi.example.com"))
    version = (await _row(private.engine, owner.id)).session_version

    await _refused(private, issued.token, "revoked")

    row = await _row(private.engine, owner.id)
    assert (row.email, row.session_version, row.email_verified_at) == (OLD_EMAIL, version, None) and notices.calls == []
    assert await _status(private.engine, issued.token) == TokenStatus.REVOKED


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["not-managed", "not-the-owner"])
async def test_a_link_outside_its_conditions_is_revoked(private: _Private, monkeypatch: pytest.MonkeyPatch, notices: Notices, case: str) -> None:
    """OWNAPI-032: the profile is no longer managed, or the token's account is not the recorded owner (a later change of owner): ``revoked``, nothing changed."""
    if case == "not-the-owner":
        user = await _add_user(private.engine, OWNER, OLD_EMAIL, admin=True)
    else:
        user = await _owner(private.engine)
        monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    issued = await _link(private.engine, user)

    await _refused(private, issued.token, "revoked")

    assert (await _row(private.engine, user.id)).email == OLD_EMAIL and notices.calls == []
    assert await _status(private.engine, issued.token) == TokenStatus.REVOKED


@pytest.mark.asyncio
async def test_a_link_without_an_address_is_refused(private: _Private) -> None:
    """OWNAPI-033: a change token carrying no address cannot say where to move the owner: ``revoked``."""
    owner = await _owner(private.engine)
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        bare = await token_service.issue_token(session, CHANGE, user_id=owner.id)
        await session.commit()
    await _refused(private, bare.token, "revoked")
    assert (await _row(private.engine, owner.id)).email == OLD_EMAIL


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{}, {"token": ""}, {"token": "x" * 257}, {"token": "abc", "extra": 1}, {"token": 5}], ids=["missing", "empty", "too-long", "extra-field", "not-a-string"])
async def test_a_body_that_is_not_a_token_is_422(private: _Private, body: dict[str, Any]) -> None:
    """OWNAPI-040: a body that is not exactly ``{token}`` is a 422."""
    async with _browser(private) as browser:
        assert (await browser.post(CONFIRM, json=body)).status_code == 422


@pytest.mark.asyncio
async def test_the_whole_flow_from_the_sync_to_the_click(private: _Private, monkeypatch: pytest.MonkeyPatch, notices: Notices) -> None:
    """OWNAPI-050: the startup sync issues and emails the link to the new address; the token read from that email is clicked; the owner's address is the variable's, the status is back to ``None``, and a second sync does nothing."""
    owner_module = importlib.import_module("backend.app.services.accounts.instance_owner")
    monkeypatch.setenv(f"{SMTP_PREFIX}HOST", "smtp.zq-ownapi.example.com")
    monkeypatch.setenv(f"{SMTP_PREFIX}FROM", "LibreFolio <noreply@example.com>")
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    sent: list[tuple[str, str]] = []

    async def outbox(content: Any, *, to: str, user_id: Optional[int] = None) -> None:
        sent.append((to, content.text))

    monkeypatch.setattr(owner_module, "send_email", outbox)
    owner = await _owner(private.engine)

    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        result = await owner_module.run_owner_sync(session)
        assert result.action == "issued"
        assert await owner_module.owner_change_status(session) == "pending"
    await owner_module.deliver_owner_change_link(result, engine=private.engine)

    assert [to for to, _ in sent] == [NEW_EMAIL]
    link = next(line.strip() for line in sent[0][1].splitlines() if line.startswith("http"))
    token = parse_qs(urlsplit(link).fragment)["token"][0]
    assert (await _confirm(private, token)).status_code == 200

    assert (await _row(private.engine, owner.id)).email == NEW_EMAIL
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        assert await owner_module.owner_change_status(session) is None
        again = await owner_module.run_owner_sync(session)
    assert again.action == "unchanged"
    assert notices.calls == [(owner.id, OLD_EMAIL, NEW_EMAIL)]
