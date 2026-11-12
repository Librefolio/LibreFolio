"""The Profile routes of a verified change of address (release 1.4, project 71, block 2, step 2.4).

With email working (an SMTP server and ``LIBREFOLIO_PUBLIC_URL``) ``PUT /auth/profile`` with a new address does not change
the account: it answers 200 with ``email_change: "pending"``, sets no new cookie, and the account shows the change it waits
for in ``user.pending_email_change`` ``{email, expires_at}`` — in this answer, in ``GET /auth/me`` and at the sign-in. The
contract pinned here:

1. Names: ``PUT /auth/profile`` (``UpdateProfileResponse.email_change``: ``applied`` | ``pending`` | null);
   ``DELETE /auth/profile/email-change`` (``cancel_pending_email_change``, 204); ``POST /auth/profile/email-change/resend``
   (``resend_pending_email_change``, 200 ``PendingEmailChangeRead``); ``AuthUserResponse.pending_email_change`` optional,
   default null, so a hand-written ``/auth/me`` without it stays valid.
2. Email on: 200 ``pending``, the address unchanged, no ``Set-Cookie``, the confirmation to the NEW address, the notice to
   the old one scheduled after the answer (``email_change_requested_work``). Email off, or SMTP without
   ``LIBREFOLIO_PUBLIC_URL``: ``applied`` as before 1.4 — the address moves, a new cookie, the emails of a completed change.
3. Refusals with email on, in the order of the PUT: 409 ``ACCOUNT_PROTECTED`` before the password; the password; then
   the address and the limits read without writing — a taken address is the 400 of today, 429 ``EMAIL_RATE_LIMITED`` with
   ``Retry-After`` and ``retry_after`` — and on such a refusal a username sent with it is NOT saved; then the username
   saved; then the link: 502 ``EMAIL_DELIVERY_FAILED`` without ``smtp_code`` when the server refuses — nothing waits, the
   username stays saved (two saves, plan §8.4).
5. (step 2.5) ``POST /email/email-change/confirm`` routes a Profile link with the session: with the cookie of the link's
   account 200 ``{username}``, the address moved, the emails of a completed change scheduled with ``by_host=False``;
   without a cookie, with a cookie no longer valid or with another account's: 403
   ``{"error_code": "EMAIL_CHANGE_SIGN_IN_REQUIRED", …}``, the same body in the three cases, the link still working for its
   account; a dead link 400 ``TOKEN_INVALID`` with the keys of the owner flow, even without a cookie. The owner's link
   still needs no session.
4. ``DELETE`` 204 always, idempotent, no email. ``resend``: 200 with a new expiry once 60 seconds passed; 404
   ``EMAIL_CHANGE_NOT_PENDING``; 409 ``EMAIL_TAKEN`` (the waiting link revoked); 429 within 60 seconds.

Pure: the real auth router runs in-process on a private SQLite file under ``tmp_path``; accounts are rows with a real
bcrypt hash at cost 4; the service's ``send_email`` is an outbox, the SMTP transport a tripwire, every limit a private one;
the background emails are recorders; the service's clock is the test's. The lane's backend is never called.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import email as email_api
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service, email_change, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.email import delivery, flows, smtp
from backend.app.services.email.delivery import EmailDeliveryError
from backend.app.services.email.messages import EmailContent
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success, unique_id

PROFILE = f"{API_V1_PREFIX}/auth/profile"
CANCEL = f"{API_V1_PREFIX}/auth/profile/email-change"
RESEND = f"{API_V1_PREFIX}/auth/profile/email-change/resend"
LOGIN = f"{API_V1_PREFIX}/auth/login"
ME = f"{API_V1_PREFIX}/auth/me"
CONFIRM = f"{API_V1_PREFIX}/email/email-change/confirm"
BASE_URL = "http://test"
TIMEOUT = 30.0

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
ADMIN_PREFIX = "LIBREFOLIO_ADMIN_"
INHERITED = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_PROFILE")
PUBLIC_URL = "https://folio.zq-pec.example.com"
PASSWORD = "Pec-Api-Pass-2026"
NEW_EMAIL = "zq.new-pec@zq-pec.example.com"
CHANGE = AccountTokenPurpose.EMAIL_CHANGE


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


def _email_on(monkeypatch: pytest.MonkeyPatch, *, links: bool = True) -> None:
    monkeypatch.setenv(f"{SMTP_PREFIX}HOST", "smtp.zq-pec.example.com")
    monkeypatch.setenv(f"{SMTP_PREFIX}FROM", "LibreFolio <noreply@example.com>")
    if links:
        monkeypatch.setenv("LIBREFOLIO_PUBLIC_URL", PUBLIC_URL)


class Clock:
    """The service's clock: the real time when the test starts, moved forward by the test."""

    def __init__(self) -> None:
        self.now = utcnow()

    def __call__(self) -> datetime:
        return self.now


@dataclass
class World:
    """What the route sent and scheduled: the confirmations (outbox), the background notices, the clock."""

    sent: list[tuple[str, EmailContent]] = field(default_factory=list)
    failure: Optional[BaseException] = None
    requested: list[tuple[int, str]] = field(default_factory=list)
    changed: list[tuple[int, str, str]] = field(default_factory=list)
    changed_by_host: list[bool] = field(default_factory=list)
    clock: Clock = field(default_factory=Clock)


@pytest.fixture(autouse=True)
def world(monkeypatch: pytest.MonkeyPatch) -> World:
    state = World()

    async def send(content: EmailContent, *, to: str, user_id: Optional[int] = None) -> None:
        state.sent.append((to, content))
        if state.failure is not None:
            raise state.failure

    async def requested(user_id: int, old_address: str, *, engine: Any = None) -> None:
        state.requested.append((user_id, old_address))

    async def changed(user_id: int, old_address: str, new_address: str, *, engine: Any = None, by_host: bool = False) -> None:
        state.changed.append((user_id, old_address, new_address))
        state.changed_by_host.append(by_host)

    def refuse(_server: object, _message: object) -> None:
        raise AssertionError("a Profile email-change API test reached the SMTP transport")

    monkeypatch.setattr(email_change, "send_email", send)
    monkeypatch.setattr(email_change, "email_change_requested_work", requested)
    monkeypatch.setattr(flows, "email_changed_work", changed)
    monkeypatch.setattr(email_change, "utcnow", state.clock)
    monkeypatch.setattr(smtp, "deliver", refuse)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", SlidingWindowLimiter(50, 3600, max_keys=1))
    monkeypatch.setattr(email_change, "EMAIL_CHANGE_LINKS_BY_MAILBOX", SlidingWindowLimiter(3, 3600))
    if hasattr(user_service, "_recorded_owner"):
        monkeypatch.setattr(user_service, "_recorded_owner", user_service._recorded_owner)
    return state


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
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'profile-api.db'}", poolclass=NullPool)
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


async def _add_user(engine: AsyncEngine, *, email: Optional[str] = None, instance_owner: bool = False) -> User:
    name = f"zq_pec_{unique_id()}"
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=name, email=email or f"{name}@zq-pec.example.com", hashed_password=auth_service.hash_password(PASSWORD), is_active=True, is_superuser=instance_owner)
        if instance_owner:
            user.is_instance_owner = True
        session.add(user)
        await session.commit()
    return user


@contextlib.asynccontextmanager
async def _signed_in(private: _Private, user: User) -> AsyncIterator[httpx.AsyncClient]:
    """A browser signed in as ``user``: the session cookie of ``POST /auth/login`` in its jar."""
    transport = httpx.ASGITransport(app=private.app, client=("198.51.100.9", 40002))
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as browser:
        login = await browser.post(LOGIN, json={"username": user.username, "password": PASSWORD})
        assert login.status_code == 200, login.text
        yield browser


async def _put_email(browser: httpx.AsyncClient, address: str = NEW_EMAIL, **extra: Any) -> httpx.Response:
    return await browser.put(PROFILE, json={"email": address, "current_password": PASSWORD, **extra})


async def _row(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        row = await session.get(User, user_id)
    assert row is not None
    return row


async def _links(engine: AsyncEngine, user_id: int) -> list[AccountToken]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        statement = select(AccountToken).where(AccountToken.purpose == CHANGE, AccountToken.user_id == user_id).order_by(AccountToken.id)
        return list((await session.execute(statement)).scalars().all())


def _live(links: list[AccountToken]) -> list[AccountToken]:
    return [link for link in links if link.revoked_at is None and link.consumed_at is None]


def _detail(response: httpx.Response) -> dict[str, Any]:
    detail = response.json().get("detail")
    assert isinstance(detail, dict), f"expected a coded refusal: {response.status_code} {response.text}"
    return detail


# =============================================================================
# 1. NAMES AND MODELS
# =============================================================================


def test_the_routes_and_models_have_the_agreed_names() -> None:
    """PEC-001 — ``DELETE /auth/profile/email-change`` (``cancel_pending_email_change``, 204) and ``POST /auth/profile/email-change/resend`` (``resend_pending_email_change``, 200 ``PendingEmailChangeRead`` ``{email, expires_at}``); ``UpdateProfileResponse.email_change`` and ``AuthUserResponse.pending_email_change``, both optional (not required: a hand-written ``/auth/me`` without them stays valid)."""
    print_section("PEC-001: names and models")
    app = FastAPI()
    app.include_router(auth_api.router, prefix=API_V1_PREFIX)
    schema = app.openapi()
    paths, schemas = schema["paths"], schema["components"]["schemas"]

    assert set(paths[CANCEL]) == {"delete"} and set(paths[RESEND]) == {"post"}
    assert paths[CANCEL]["delete"]["operationId"] == "cancel_pending_email_change_api_v1_auth_profile_email_change_delete"
    assert "204" in paths[CANCEL]["delete"]["responses"]
    resend = paths[RESEND]["post"]
    assert resend["operationId"] == "resend_pending_email_change_api_v1_auth_profile_email_change_resend_post"
    assert resend["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("/PendingEmailChangeRead")
    assert set(schemas["PendingEmailChangeRead"]["properties"]) == {"email", "expires_at"}
    assert "email_change" in schemas["UpdateProfileResponse"]["properties"] and "email_change" not in schemas["UpdateProfileResponse"].get("required", [])
    assert "pending_email_change" in schemas["AuthUserResponse"]["properties"] and "pending_email_change" not in schemas["AuthUserResponse"].get("required", [])
    print_success("two routes, three models, the agreed names")


# =============================================================================
# 2. PUT /auth/profile
# =============================================================================


@pytest.mark.asyncio
async def test_with_email_on_a_new_address_waits_for_its_link(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-002 — email on: 200 ``email_change: "pending"``, the account's address unchanged, no ``Set-Cookie`` (the session goes on), ``user.pending_email_change`` with the new address and its expiry 24 hours on; the confirmation sent to the NEW address; the notice to the old one scheduled once; ``GET /auth/me`` and the sign-in show the same waiting change."""
    print_section("PEC-002: pending with email on")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)

    async with _signed_in(private, user) as browser:
        response = await _put_email(browser)
        assert response.status_code == 200, response.text
        body = response.json()
        me = (await browser.get(ME)).json()["user"]

    assert body["email_change"] == "pending" and "set-cookie" not in response.headers
    assert body["user"]["email"] == user.email and (await _row(private.engine, user.id)).email == user.email
    waiting = body["user"]["pending_email_change"]
    assert waiting["email"] == NEW_EMAIL
    assert abs((datetime.fromisoformat(waiting["expires_at"]) - ensure_utc(world.clock.now)) - timedelta(hours=24)) < timedelta(seconds=2)
    assert me["pending_email_change"] == waiting
    assert [to for to, _content in world.sent] == [NEW_EMAIL] and world.requested == [(user.id, user.email)] and world.changed == []
    async with _signed_in(private, user) as browser:
        login = await browser.post(LOGIN, json={"username": user.username, "password": PASSWORD})
    assert login.json()["user"]["pending_email_change"] == waiting
    print_success("pending, nothing changed, no cookie; /me and login show it")


@pytest.mark.asyncio
@pytest.mark.parametrize("configuration", ["email-off", "smtp-without-public-url"])
async def test_without_links_the_change_applies_at_once_as_before(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch, configuration: str) -> None:
    """PEC-003 — email off, or SMTP without ``LIBREFOLIO_PUBLIC_URL``: 200 ``email_change: "applied"``, the address moved, a new session cookie, the emails of a completed change scheduled, no link, nothing waiting."""
    print_section(f"PEC-003: applied with {configuration}")
    if configuration == "smtp-without-public-url":
        _email_on(monkeypatch, links=False)
    user = await _add_user(private.engine)

    async with _signed_in(private, user) as browser:
        response = await _put_email(browser)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["email_change"], body["user"]["email"], body["user"]["pending_email_change"]) == ("applied", NEW_EMAIL, None)
    assert "set-cookie" in response.headers
    assert (world.sent, world.requested, world.changed) == ([], [], [(user.id, user.email, NEW_EMAIL)])
    assert await _links(private.engine, user.id) == []
    print_success("applied, new cookie, no link")


@pytest.mark.asyncio
async def test_a_username_alone_says_no_email_change(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-004 — a PUT with a new username only: 200 ``email_change`` null, the username saved, no link."""
    print_section("PEC-004: a username alone")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)
    name = f"zq_renamed_{unique_id()}"

    async with _signed_in(private, user) as browser:
        response = await browser.put(PROFILE, json={"username": name})

    assert response.status_code == 200, response.text
    assert (response.json()["email_change"], response.json()["user"]["username"]) == (None, name)
    assert await _links(private.engine, user.id) == []
    print_success("null, username saved")


@pytest.mark.asyncio
async def test_a_refusal_before_the_link_leaves_the_profile_as_it_was(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-005 — with a new username in the same PUT: a taken address answers the 400 of today, and a spent hourly budget 429 ``EMAIL_RATE_LIMITED`` with ``Retry-After`` and ``retry_after``; in both the username is NOT saved, no link, no email."""
    print_section("PEC-005: refused before the link, nothing saved")
    _email_on(monkeypatch)
    other = await _add_user(private.engine)
    user = await _add_user(private.engine)

    async with _signed_in(private, user) as browser:
        taken = await _put_email(browser, other.email, username=f"zq_taken_{unique_id()}")
        monkeypatch.setenv(f"{SMTP_PREFIX}MAX_PER_HOUR", "1")
        delivery.INSTANCE_BUDGET.hit(limit=1)
        limited = await _put_email(browser, username=f"zq_limited_{unique_id()}")

    assert (taken.status_code, taken.json()["detail"]) == (400, "Email already registered")
    assert limited.status_code == 429, limited.text
    detail = _detail(limited)
    assert detail["error_code"] == "EMAIL_RATE_LIMITED" and int(limited.headers["retry-after"]) == detail["retry_after"] >= 1
    assert (await _row(private.engine, user.id)).username == user.username, "a refusal before the link saves no username"
    assert (await _links(private.engine, user.id), world.sent) == ([], [])
    print_success("400 and 429, nothing saved")


@pytest.mark.asyncio
async def test_a_refused_send_answers_502_and_keeps_the_username(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-006 — the SMTP server refuses the confirmation: 502 ``EMAIL_DELIVERY_FAILED`` without ``smtp_code``; nothing waits (``GET /auth/me``); the username sent with it stays saved (two saves, plan §8.4); the account's address unchanged."""
    print_section("PEC-006: 502")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)
    name = f"zq_kept_{unique_id()}"
    world.failure = EmailDeliveryError(smtp.SmtpErrorCode.RECIPIENT_REFUSED)

    async with _signed_in(private, user) as browser:
        response = await _put_email(browser, username=name)
        me = (await browser.get(ME)).json()["user"]

    assert response.status_code == 502, response.text
    detail = _detail(response)
    assert detail["error_code"] == "EMAIL_DELIVERY_FAILED" and "smtp_code" not in detail
    assert (me["pending_email_change"], me["username"], me["email"]) == (None, name, user.email)
    assert _live(await _links(private.engine, user.id)) == [] and world.requested == []
    print_success("502 without smtp_code; nothing waits; username kept")


@pytest.mark.asyncio
async def test_the_protected_owner_is_refused_before_the_password(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-007 — email on, a managed instance: the owner's new address is 409 ``ACCOUNT_PROTECTED`` without a password, and no link."""
    print_section("PEC-007: the protected owner")
    _email_on(monkeypatch)
    owner_address = f"zq-owner-{unique_id()}@zq-pec.example.com"
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv(f"{ADMIN_PREFIX}EMAIL", owner_address)
    owner = await _add_user(private.engine, email=owner_address, instance_owner=True)

    async with _signed_in(private, owner) as browser:
        response = await browser.put(PROFILE, json={"email": NEW_EMAIL})

    assert response.status_code == 409, response.text
    assert _detail(response)["error_code"] == "ACCOUNT_PROTECTED"
    assert await _links(private.engine, owner.id) == []
    print_success("409 before the password")


# =============================================================================
# 3. CANCEL AND RESEND
# =============================================================================


@pytest.mark.asyncio
async def test_cancel_is_204_twice_and_clears_the_wait(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-008 — ``DELETE /auth/profile/email-change``: 204 with a change waiting and 204 again with none; ``GET /auth/me`` then shows null; no email."""
    print_section("PEC-008: cancel")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)

    async with _signed_in(private, user) as browser:
        assert (await _put_email(browser)).status_code == 200
        first, second = await browser.delete(CANCEL), await browser.delete(CANCEL)
        me = (await browser.get(ME)).json()["user"]

    assert (first.status_code, second.status_code, first.content, me["pending_email_change"]) == (204, 204, b"", None)
    assert _live(await _links(private.engine, user.id)) == [] and len(world.sent) == 1
    print_success("204, 204, nothing waits")


@pytest.mark.asyncio
async def test_resend_answers_200_404_409_and_429(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-009 — ``POST /auth/profile/email-change/resend``: within 60 seconds 429 with ``Retry-After``; after, 200 ``{email, expires_at}`` with a later expiry and a second email; the address taken meanwhile 409 ``EMAIL_TAKEN`` and nothing waits any more; then 404 ``EMAIL_CHANGE_NOT_PENDING``."""
    print_section("PEC-009: resend")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)

    async with _signed_in(private, user) as browser:
        first = (await _put_email(browser)).json()["user"]["pending_email_change"]
        too_soon = await browser.post(RESEND)
        world.clock.now += timedelta(seconds=61)
        again = await browser.post(RESEND)
        await _add_user(private.engine, email=NEW_EMAIL)
        world.clock.now += timedelta(seconds=61)
        taken = await browser.post(RESEND)
        nothing = await browser.post(RESEND)

    assert too_soon.status_code == 429 and "retry-after" in too_soon.headers, too_soon.text
    assert again.status_code == 200, again.text
    assert again.json()["email"] == NEW_EMAIL and datetime.fromisoformat(again.json()["expires_at"]) > datetime.fromisoformat(first["expires_at"])
    assert [to for to, _content in world.sent] == [NEW_EMAIL, NEW_EMAIL]
    assert (taken.status_code, _detail(taken)["error_code"]) == (409, "EMAIL_TAKEN")
    assert (nothing.status_code, _detail(nothing)["error_code"]) == (404, "EMAIL_CHANGE_NOT_PENDING")
    print_success("429, 200, 409, 404")


@pytest.mark.asyncio
async def test_resend_with_email_off_is_409(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-010 — a change waits and email is turned off afterwards: ``resend`` is 409 ``EMAIL_UNAVAILABLE``, the link still waiting (plan §8.6)."""
    print_section("PEC-010: resend with email off")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)

    async with _signed_in(private, user) as browser:
        assert (await _put_email(browser)).status_code == 200
        monkeypatch.delenv(f"{SMTP_PREFIX}HOST")
        response = await browser.post(RESEND)

    assert (response.status_code, _detail(response)["error_code"]) == (409, "EMAIL_UNAVAILABLE")
    assert len(_live(await _links(private.engine, user.id))) == 1
    print_success("409 EMAIL_UNAVAILABLE, the link still waits")


@pytest.mark.asyncio
async def test_a_username_and_an_email_together_save_the_username_and_wait_for_the_email(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-011 — email on, a new username and a new address in one PUT: 200 ``pending``, the username saved, the address unchanged and waiting."""
    print_section("PEC-011: username and email together")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)
    name = f"zq_both_{unique_id()}"

    async with _signed_in(private, user) as browser:
        response = await _put_email(browser, username=name)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["email_change"], body["user"]["username"], body["user"]["email"], body["user"]["pending_email_change"]["email"]) == ("pending", name, user.email, NEW_EMAIL)
    row = await _row(private.engine, user.id)
    assert (row.username, row.email) == (name, user.email)
    print_success("username saved, address waiting")


@pytest.mark.asyncio
async def test_cancel_and_resend_need_a_session_and_touch_only_its_account(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-012 — without a session cookie ``DELETE`` and ``resend`` are 401; another account's ``DELETE`` and ``resend`` act on that account only (204, 404): the first account's link stays live and nothing is sent for it."""
    print_section("PEC-012: the session decides whose change")
    _email_on(monkeypatch)
    user, other = await _add_user(private.engine), await _add_user(private.engine)
    async with _signed_in(private, user) as browser:
        assert (await _put_email(browser)).status_code == 200

    transport = httpx.ASGITransport(app=private.app, client=("198.51.100.10", 40003))
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as anonymous:
        statuses = ((await anonymous.delete(CANCEL)).status_code, (await anonymous.post(RESEND)).status_code)
    async with _signed_in(private, other) as browser:
        world.clock.now += timedelta(seconds=61)
        others = ((await browser.delete(CANCEL)).status_code, (await browser.post(RESEND)).status_code)

    assert (statuses, others) == ((401, 401), (204, 404))
    assert len(_live(await _links(private.engine, user.id))) == 1 and len(world.sent) == 1
    print_success("401 without a session; another account touches only its own")


@pytest.mark.asyncio
async def test_email_turned_off_while_a_change_waits_applies_the_next_one_and_revokes_the_wait(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-013 — plan §8.6: a change waits, email is turned off, and a new PUT with another address applies at once (``applied``, a new cookie) and revokes the waiting link."""
    print_section("PEC-013: email off with a change waiting")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)
    other_address = f"zq-other-{unique_id()}@zq-pec.example.com"

    async with _signed_in(private, user) as browser:
        assert (await _put_email(browser)).status_code == 200
        monkeypatch.delenv(f"{SMTP_PREFIX}HOST")
        response = await _put_email(browser, other_address)

    assert response.status_code == 200, response.text
    assert (response.json()["email_change"], response.json()["user"]["email"], response.json()["user"]["pending_email_change"]) == ("applied", other_address, None)
    assert "set-cookie" in response.headers
    assert _live(await _links(private.engine, user.id)) == []
    print_success("applied, the waiting link revoked")


# =============================================================================
# 4. THE CLICK (step 2.5: POST /email/email-change/confirm routed with the session)
# =============================================================================

#: The keys of a refused confirmation, as the owner flow answers them (OWNAPI ``INVALID_MESSAGE_KEYS``).
INVALID_MESSAGE_KEYS = {"error_code", "status", "message"}


def _anonymous(private: _Private) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=private.app, client=("198.51.100.11", 40004))
    return httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT)


def _token_of(content: EmailContent) -> str:
    """The token of the confirmation email: the fragment of the link on its own line of the plain text."""
    link = next(line for line in content.text.splitlines() if line.startswith(PUBLIC_URL))
    return parse_qs(urlsplit(link).fragment)["token"][0]


async def _requested(private: _Private, world: World, user: User) -> str:
    """A change of ``user`` to ``NEW_EMAIL`` asked from Profile; the token its confirmation carries."""
    async with _signed_in(private, user) as browser:
        assert (await _put_email(browser)).status_code == 200
    return _token_of(world.sent[-1][1])


@pytest.mark.asyncio
async def test_a_profile_link_clicked_with_the_accounts_session_completes_the_change(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-020 — the Profile link clicked in a browser signed in as its account: 200 ``{username}``, the address moved and verified, the emails of a completed change scheduled once with ``by_host=False``."""
    print_section("PEC-020: the click with the account's session")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)
    token = await _requested(private, world, user)

    async with _signed_in(private, user) as browser:
        response = await browser.post(CONFIRM, json={"token": token})

    assert response.status_code == 200, response.text
    assert response.json() == {"username": user.username}
    row = await _row(private.engine, user.id)
    assert (row.email, row.email_verified_at is not None) == (NEW_EMAIL, True)
    assert (world.changed, world.changed_by_host) == ([(user.id, user.email, NEW_EMAIL)], [False])
    print_success("200, moved and verified, emails scheduled by_host=False")


@pytest.mark.asyncio
async def test_a_profile_link_without_the_accounts_session_is_403_and_stays_live(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-021 — D10: the Profile link clicked without a cookie, with a cookie no longer valid (the account's session version raised since) and with another account's cookie: 403 ``EMAIL_CHANGE_SIGN_IN_REQUIRED``, the same body in the three cases, nothing changed, no email scheduled; the link then works with the account's own session."""
    print_section("PEC-021: 403 without the account's session")
    _email_on(monkeypatch)
    user, other = await _add_user(private.engine), await _add_user(private.engine)
    token = await _requested(private, world, user)

    async with _anonymous(private) as anonymous:
        without = await anonymous.post(CONFIRM, json={"token": token})
    async with _signed_in(private, other) as browser:
        another = await browser.post(CONFIRM, json={"token": token})
    async with _signed_in(private, user) as browser:
        async with private.engine.begin() as connection:
            await connection.execute(text("UPDATE users SET session_version = session_version + 1 WHERE id = :id"), {"id": user.id})
        stale = await browser.post(CONFIRM, json={"token": token})

    bodies = [response.json() for response in (without, another, stale)]
    assert [response.status_code for response in (without, another, stale)] == [403, 403, 403], [response.text for response in (without, another, stale)]
    assert bodies[0]["detail"]["error_code"] == "EMAIL_CHANGE_SIGN_IN_REQUIRED" and bodies.count(bodies[0]) == 3, bodies
    assert ((await _row(private.engine, user.id)).email, world.changed) == (user.email, [])
    assert len(_live(await _links(private.engine, user.id))) == 1, "the link is neither spent nor revoked"

    async with _signed_in(private, user) as browser:
        response = await browser.post(CONFIRM, json={"token": token})
    assert response.status_code == 200, response.text
    print_success("403 three times, one body; then 200 with the account's session")


@pytest.mark.asyncio
@pytest.mark.parametrize("how", ["consumed", "revoked", "expired", "unknown"])
async def test_a_dead_profile_link_is_400_even_without_a_session(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch, how: str) -> None:
    """PEC-022 — a dead link answers 400 ``TOKEN_INVALID`` with its ``status`` and the keys of the owner flow, to a browser with no session: a Profile link already clicked, cancelled, past its 24 hours, or a token never issued."""
    print_section(f"PEC-022: a dead link, {how}")
    _email_on(monkeypatch)
    user = await _add_user(private.engine)
    token = await _requested(private, world, user) if how != "unknown" else "zq-never-issued-profile-change-0123456789"
    if how == "consumed":
        async with _signed_in(private, user) as browser:
            assert (await browser.post(CONFIRM, json={"token": token})).status_code == 200
    elif how == "revoked":
        async with _signed_in(private, user) as browser:
            assert (await browser.delete(CANCEL)).status_code == 204
    elif how == "expired":
        world.clock.now += timedelta(hours=24, seconds=1)

    async with _anonymous(private) as anonymous:
        response = await anonymous.post(CONFIRM, json={"token": token})

    assert response.status_code == 400, response.text
    detail = _detail(response)
    assert (set(detail), detail["error_code"], detail["status"]) == (INVALID_MESSAGE_KEYS, "TOKEN_INVALID", how)
    print_success(f"400 {how}")


@pytest.mark.asyncio
async def test_the_owners_link_still_needs_no_session(private: _Private, world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    """PEC-023 — the host's link of the managed instance's owner (no creator), clicked with no session: 200 as before (A5-1b), the emails scheduled with ``by_host=True``."""
    print_section("PEC-023: the owner's link, no session")
    monkeypatch.setenv("LIBREFOLIO_PROFILE", "managed")
    monkeypatch.setenv(f"{ADMIN_PREFIX}EMAIL", NEW_EMAIL)
    owner = await _add_user(private.engine, instance_owner=True)
    async with AsyncSession(private.engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, CHANGE, user_id=owner.id, email=NEW_EMAIL)
        await session.commit()

    async with _anonymous(private) as anonymous:
        response = await anonymous.post(CONFIRM, json={"token": issued.token})

    assert response.status_code == 200, response.text
    assert ((await _row(private.engine, owner.id)).email, world.changed_by_host) == (NEW_EMAIL, [True])
    print_success("200 without a session, by_host=True")
