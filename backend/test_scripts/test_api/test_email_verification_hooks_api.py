"""The hooks of email verification in workstream A's routes (lot E5b, developer decision 44), over HTTP, in-process.

With ``require_email_verification`` on, an account created by signing up waits for its link before it can sign in.
E5a pinned the flow (``test_services/test_email_verification.py``) and its two routes
(``test_api/test_email_verification_api.py``); this module pins what A's routes do with it once the hooks of E5b are
in place. The contract:

1. Registration (``POST /auth/register``), the option on, email and ``LIBREFOLIO_PUBLIC_URL`` ready: an account that is
   not the instance's first answers 201 with ``verification_required: true`` and is created inactive; after the answer
   one email goes to its address with a ``/verify-email#token=`` link built from ``LIBREFOLIO_PUBLIC_URL``. Signing in
   with the right password is 403 ``EMAIL_NOT_VERIFIED``; with a wrong one 401, byte for byte an unknown account's
   answer. «Resend» sends a new link that replaces the first; the click verifies the account, and the sign-in is 200.
   The instance's first account never waits. An invited registration waits too, and spends its invitation.
2. The option on and no email with a link able to go out (email off, or no public URL): 409
   ``EMAIL_VERIFICATION_UNAVAILABLE``, nothing created, an invitation given with it not spent. The option off:
   registration as before, ``verification_required: false``, active, no verification token, no email.
3. The limit (``LIBREFOLIO_MAX_USERS``): a waiting account takes a place while its link is live — ``GET /users`` counts
   it in ``usage.used``, and a registration that needs one more place is refused — and none once the link expired.
   ``GET /users`` says ``holds_place: true`` for it while its link is live, false once expired, false for any other
   account. ``PATCH /users/{id}`` ``{is_active: true}`` on a full instance is accepted for it while its link is live
   (no ``USER_LIMIT_REACHED``: its place is already counted), refused once the link expired; after such an activation
   its emailed link is ``TOKEN_INVALID`` ``revoked`` and the sign-in is 200. ``PATCH`` ``{is_active: false}`` on a
   waiting account — already inactive — changes nothing (night decision of 16/10): 200, its link still live and still
   counted, and still able to verify it; an unwanted sign-up is deleted, or ended by ``user deactivate`` on the CLI.
   The answer of ``PATCH /users/{id}`` carries the list's flag: ``holds_place: true`` for a waiting account with a live
   link — after that no-op, or after a promotion, which leaves it waiting —, false once its link expired.
4. ``PATCH /settings/global/bulk``: ``require_email_verification`` off → on without an email with a link able to go out
   is 409 ``{error_code: EMAIL_VERIFICATION_UNAVAILABLE, message, key}`` and nothing of the request is saved; with
   email and a public URL it is saved; turning it off is always saved; sending it on again while already on, email
   broken, saves (only off → on is checked).

Pure: the real auth, users, settings and email routers run in-process on a private SQLite file under ``tmp_path``
(NullPool, disposed at teardown), the option set in that file only; accounts are rows with a real bcrypt hash at cost
4. A new instance registers by invitation (workstream A): the cases that register without one set ``registration_mode``
to ``open`` in that file — never through ``LIBREFOLIO_REGISTRATION``, which would lock it —; the first account and the
invited cases keep the default. An autouse fixture removes every inherited ``LIBREFOLIO_SMTP_*``,
``LIBREFOLIO_PUBLIC_URL``, ``LIBREFOLIO_BLOCKED``, ``LIBREFOLIO_MAX_USERS`` and ``LIBREFOLIO_REGISTRATION``; each test
sets its own with ``monkeypatch``. The hourly budget and the «resend» limiter are private on a fake clock;
``socket.getaddrinfo`` resolves the loopback only; every SMTP conversation is with ``FakeSmtpServer`` on 127.0.0.1.
Where minutes must pass between two steps, ``verification.utcnow`` is a clock the test moves. Nothing is timed.

Red until E5b is applied (``AuthRegisterResponse.verification_required``, ``AdminUserRead.holds_place``).
"""

from __future__ import annotations

import contextlib
import os
import re
import socket
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import email as email_api
from backend.app.api.v1 import settings as settings_api
from backend.app.api.v1 import users as users_api
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, GlobalSetting, User
from backend.app.db.session import get_session_generator
from backend.app.schemas.settings import SETTINGS_REGISTRY
from backend.app.services.accounts import auth_service, token_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import IssuedToken, TokenStatus
from backend.app.services.email import delivery, smtp, verification
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer
from backend.test_scripts.test_utils import print_section, print_success

LOGIN = f"{API_V1_PREFIX}/auth/login"
REGISTER = f"{API_V1_PREFIX}/auth/register"
USERS = f"{API_V1_PREFIX}/users"
BULK = f"{API_V1_PREFIX}/settings/global/bulk"
CONFIRM = f"{API_V1_PREFIX}/email/verification/confirm"
RESEND = f"{API_V1_PREFIX}/email/verification/resend"
BASE_URL = "http://test"
TIMEOUT = 30.0
CLIENT = ("198.51.100.7", 40001)

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
INHERITED = (PUBLIC_URL_VARIABLE, "LIBREFOLIO_BLOCKED", MAX_USERS_VARIABLE, "LIBREFOLIO_REGISTRATION")
PUBLIC_URL = "https://folio.zq-public.example.com:8443/app"
SENDER_HEADER = "LibreFolio <noreply@example.com>"
LOOPBACK_NAMES = frozenset({"127.0.0.1", "::1", "localhost"})

OPTION_KEY = SETTINGS_REGISTRY.global_.REQUIRE_EMAIL_VERIFICATION.key
#: Who may register. A new instance registers by invitation (workstream A): the cases that register without one set it
#: to ``open`` in their private file, as an administrator would; the invited ones keep the default.
REGISTRATION_MODE_KEY = SETTINGS_REGISTRY.global_.REGISTRATION_MODE.key
#: Another setting saved in the same bulk request: refused with it, or saved with it.
OTHER_KEY = SETTINGS_REGISTRY.global_.SESSION_TTL_HOURS.key

PASSWORD = "Hooks-Pass-2026"
WRONG_PASSWORD = "Not-The-Hooks-Pass-2026"
ADMIN = "zq_admin"
VERA = "zq_vera"
NOBODY = "zq_nobody"
VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION
INVITE = AccountTokenPurpose.INVITE
SHIPPED_RESEND = verification.RESEND_BY_ADDRESS
START = 1_000.0


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in INHERITED:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    limiter = SlidingWindowLimiter(50, 3600, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


@pytest.fixture(autouse=True)
def _private_resend_limit(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> None:
    monkeypatch.setattr(verification, "RESEND_BY_ADDRESS", SlidingWindowLimiter(SHIPPED_RESEND.limit, SHIPPED_RESEND.window_seconds, clock=clock))


@pytest.fixture(autouse=True)
def _bounded_smtp_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 5.0)


@pytest.fixture(autouse=True)
def network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    resolve = socket.getaddrinfo
    refused: list[str] = []

    def loopback_only(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and name not in LOOPBACK_NAMES:
            refused.append(str(name))
            raise socket.gaierror(socket.EAI_NONAME, f"these tests resolve the loopback only, not {name!r}")
        return resolve(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    return refused


@dataclass
class _Moment:
    """The time ``verification`` reads: ``moment.now``, moved by the test."""

    now: datetime


@pytest.fixture
def moment(monkeypatch: pytest.MonkeyPatch) -> _Moment:
    """``verification.utcnow`` reads this clock: «resend» five minutes later is a line of the test, not a wait."""
    current = _Moment(now=utcnow())
    monkeypatch.setattr(verification, "utcnow", lambda: current.now)
    return current


@dataclass(frozen=True)
class _Private:
    engine: AsyncEngine
    app: FastAPI


def _app(engine: AsyncEngine) -> FastAPI:
    """The real routers of auth, users, settings and email under the API prefix; sessions on ``engine``."""
    app = FastAPI()
    for router in (auth_api.router, users_api.router, settings_api.router, email_api.router):
        app.include_router(router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@pytest_asyncio.fixture
async def private(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[_Private]:
    """An empty instance on a private SQLite file: schema and default settings, no account; bcrypt at cost 4."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'hooks.db'}", poolclass=NullPool)
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


async def _add_user(engine: AsyncEngine, username: str, *, admin: bool = False, active: bool = True) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password=auth_service.hash_password(PASSWORD), is_superuser=admin, is_active=active)
        session.add(user)
        await session.commit()
    return user


async def _option(engine: AsyncEngine, value: str) -> None:
    async with AsyncSession(engine) as session:
        result = await session.execute(update(GlobalSetting).where(GlobalSetting.key == OPTION_KEY).values(value=value))
        assert result.rowcount == 1, "setup: require_email_verification was not seeded"
        await session.commit()


async def _registration_open(engine: AsyncEngine) -> None:
    """``registration_mode`` set to ``open`` in the private file: a registration without an invitation is admitted.

    A new instance registers by invitation (``GLOBAL_SETTINGS_DEFAULTS``, workstream A): only the cases that register
    without one call this, as an administrator opening registration would; the invited cases keep the default.
    ``LIBREFOLIO_REGISTRATION`` stays unset: it would lock the mode.
    """
    async with AsyncSession(engine) as session:
        result = await session.execute(update(GlobalSetting).where(GlobalSetting.key == REGISTRATION_MODE_KEY).values(value="open"))
        assert result.rowcount == 1, "setup: registration_mode was not seeded"
        await session.commit()


async def _setting(engine: AsyncEngine, key: str) -> str:
    async with AsyncSession(engine) as session:
        return (await session.execute(select(GlobalSetting.value).where(GlobalSetting.key == key))).scalar_one()


async def _user(engine: AsyncEngine, username: str) -> User | None:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return (await session.execute(select(User).where(User.username == username))).scalars().first()


async def _verification_rows(engine: AsyncEngine, user_id: int) -> list[AccountToken]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        statement = select(AccountToken).where(AccountToken.purpose == VERIFICATION, AccountToken.user_id == user_id).order_by(AccountToken.id)
        return list((await session.execute(statement)).scalars().all())


async def _expire_links(engine: AsyncEngine, user_id: int) -> None:
    """Every verification link of the account expired a minute ago."""
    async with AsyncSession(engine) as session:
        await session.execute(update(AccountToken).where(AccountToken.purpose == VERIFICATION, AccountToken.user_id == user_id).values(expires_at=utcnow() - timedelta(minutes=1)))
        await session.commit()


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose) -> TokenStatus:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return (await token_service.inspect_token(session, token, purpose)).status


def _ready(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer) -> None:
    for name, value in {"HOST": fake.host, "PORT": str(fake.port), "TLS": "none", "FROM": SENDER_HEADER}.items():
        monkeypatch.setenv(SMTP_PREFIX + name, value)
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


def _email_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX):
            monkeypatch.delenv(name, raising=False)


@contextlib.asynccontextmanager
async def _browser(private: _Private) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=private.app, client=CLIENT)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as browser:
        yield browser


async def _post(private: _Private, path: str, body: object) -> httpx.Response:
    async with _browser(private) as browser:
        return await browser.post(path, json=body)


async def _register(private: _Private, username: str, *, invite_token: str | None = None) -> httpx.Response:
    body: dict[str, object] = {"username": username, "email": f"{username}@example.com", "password": PASSWORD}
    if invite_token is not None:
        body["invite_token"] = invite_token
    return await _post(private, REGISTER, body)


async def _login(private: _Private, username: str, password: str = PASSWORD) -> httpx.Response:
    return await _post(private, LOGIN, {"username": username, "password": password})


async def _as_admin(private: _Private, method: str, path: str, body: object | None = None) -> httpx.Response:
    """One request of the administrator, signed in on a browser of its own."""
    async with _browser(private) as browser:
        signed_in = await browser.post(LOGIN, json={"username": ADMIN, "password": PASSWORD})
        assert signed_in.status_code == 200, f"setup: the administrator could not sign in: {signed_in.text}"
        return await browser.request(method, path, json=body)


def _token_in(received: object) -> str:
    """The token of the PUBLIC_URL /verify-email link of a received message."""
    text = received.message.get_body(preferencelist=("plain",)).get_content()
    match = re.search(re.escape(f"{PUBLIC_URL}/verify-email#") + r"(\S+)", text)
    assert match, f"no {PUBLIC_URL}/verify-email link in the email: {text!r}"
    return parse_qs(match.group(1))["token"][0]


def _detail(response: httpx.Response) -> dict[str, Any]:
    detail = response.json().get("detail")
    assert isinstance(detail, dict), f"expected a coded refusal: {response.status_code} {response.text}"
    return detail


async def _listed(private: _Private) -> dict[str, Any]:
    """``GET /users`` as the administrator: ``{"usage": …, "holds_place": {username: bool}}``."""
    response = await _as_admin(private, "GET", USERS)
    assert response.status_code == 200, response.text
    body = response.json()
    return {"usage": body["usage"], "holds_place": {item["username"]: item["holds_place"] for item in body["items"]}}


# =============================================================================
# 1. REGISTRATION, SIGN-IN, RESEND, CLICK
# =============================================================================


@pytest.mark.asyncio
async def test_a_registration_waits_for_its_link_then_signs_in(private: _Private, monkeypatch: pytest.MonkeyPatch, moment: _Moment) -> None:
    """EVH-001 — contract 1: the option on, email and links ready, an administrator already there. Register: 201 ``verification_required: true``, the account inactive, one email to its address with a ``/verify-email`` link. Sign-in: right password 403 ``EMAIL_NOT_VERIFIED``; wrong password 401, the same bytes as an unknown account's. Six minutes later «resend» sends a new link; the first one is then ``revoked``; the new one verifies (200 ``{username}``), and the sign-in is 200."""
    print_section("EVH-001: register, wait, resend, click, sign in")
    await _add_user(private.engine, ADMIN, admin=True)
    await _option(private.engine, "true")
    await _registration_open(private.engine)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        registered = await _register(private, VERA)
        assert registered.status_code == 201, registered.text
        assert registered.json()["verification_required"] is True and registered.json()["user"]["is_active"] is False
        assert [message.rcpt_tos for message in fake.messages] == [[f"{VERA}@example.com"]], "one email after the answer"
        first = _token_in(fake.messages[0])

        refused = await _login(private, VERA)
        wrong = await _login(private, VERA, WRONG_PASSWORD)
        unknown = await _login(private, NOBODY, WRONG_PASSWORD)
        moment.now += timedelta(minutes=6)
        resent = await _post(private, RESEND, {"username": VERA, "password": PASSWORD})
        second = _token_in(fake.messages[-1])

    assert (refused.status_code, _detail(refused)["error_code"]) == (403, "EMAIL_NOT_VERIFIED"), refused.text
    assert (wrong.status_code, wrong.content) == (401, unknown.content) and unknown.status_code == 401
    assert resent.status_code == 200 and len(fake.messages) == 2, resent.text
    moment.now += timedelta(minutes=1)
    stale = await _post(private, CONFIRM, {"token": first})
    assert (stale.status_code, _detail(stale)["status"]) == (400, "revoked"), stale.text
    confirmed = await _post(private, CONFIRM, {"token": second})
    assert (confirmed.status_code, confirmed.json()) == (200, {"username": VERA}), confirmed.text
    assert (await _login(private, VERA)).status_code == 200
    print_success("201 waiting → 403 EMAIL_NOT_VERIFIED → resend → click → 200")


@pytest.mark.asyncio
async def test_the_first_account_never_waits(private: _Private) -> None:
    """EVH-002 — contract 1: on an empty instance, the option on and email off, the first registration is the administrator: 201 ``verification_required: false``, active, no verification token; it signs in."""
    print_section("EVH-002: the first account")
    await _option(private.engine, "true")

    registered = await _register(private, ADMIN)

    assert registered.status_code == 201, registered.text
    assert (registered.json()["verification_required"], registered.json()["user"]["is_active"], registered.json()["user"]["is_superuser"]) == (False, True, True)
    admin = await _user(private.engine, ADMIN)
    assert await _verification_rows(private.engine, admin.id) == []
    assert (await _login(private, ADMIN)).status_code == 200
    print_success("the first account is active at once")


@pytest.mark.asyncio
async def test_an_invited_registration_waits_too_and_spends_its_invitation(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-003 — contract 1: registration by invitation, the option on, email ready: 201 ``verification_required: true``, inactive, the email sent, and the invitation spent."""
    print_section("EVH-003: an invitation")
    admin = await _add_user(private.engine, ADMIN, admin=True)
    await _option(private.engine, "true")
    invitation = await _issue_invite(private.engine, admin.id)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        registered = await _register(private, VERA, invite_token=invitation.token)

    assert registered.status_code == 201 and registered.json()["verification_required"] is True, registered.text
    assert len(fake.messages) == 1
    assert await _status(private.engine, invitation.token, INVITE) == TokenStatus.CONSUMED
    print_success("waits, the invitation spent")


async def _issue_invite(engine: AsyncEngine, admin_id: int) -> IssuedToken:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, INVITE, created_by_user_id=admin_id)
        await session.commit()
    return issued


# =============================================================================
# 2. NO EMAIL WITH A LINK, OR THE OPTION OFF
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("case", "invited"), [("email-off", False), ("no-public-url", False), ("email-off", True)])
async def test_no_email_with_a_link_refuses_the_registration(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], case: str, invited: bool) -> None:
    """EVH-004 — contract 2: the option on, email off or no ``LIBREFOLIO_PUBLIC_URL``: 409 ``EMAIL_VERIFICATION_UNAVAILABLE``; no account written, no token; an invitation given with it still live."""
    print_section(f"EVH-004: {case}, invited={invited}")
    admin = await _add_user(private.engine, ADMIN, admin=True)
    await _option(private.engine, "true")
    invitation = await _issue_invite(private.engine, admin.id) if invited else None
    if not invited:
        await _registration_open(private.engine)
    if case == "no-public-url":
        for name, value in {"HOST": "smtp.zq-host.example.com", "FROM": SENDER_HEADER}.items():
            monkeypatch.setenv(SMTP_PREFIX + name, value)

    response = await _register(private, VERA, invite_token=invitation.token if invitation else None)

    assert (response.status_code, _detail(response)["error_code"]) == (409, "EMAIL_VERIFICATION_UNAVAILABLE"), response.text
    assert await _user(private.engine, VERA) is None
    if invitation is not None:
        assert await _status(private.engine, invitation.token, INVITE) == TokenStatus.VALID
    assert network == []
    print_success("409, nothing created")


@pytest.mark.asyncio
async def test_with_the_option_off_registration_is_as_before(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-005 — contract 2: the option off, email ready: 201 ``verification_required: false``, active, no verification token, no email; the sign-in is 200."""
    print_section("EVH-005: the option off")
    await _add_user(private.engine, ADMIN, admin=True)
    await _registration_open(private.engine)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        registered = await _register(private, VERA)

    assert registered.status_code == 201 and registered.json()["verification_required"] is False and registered.json()["user"]["is_active"] is True, registered.text
    assert fake.messages == [] and await _verification_rows(private.engine, (await _user(private.engine, VERA)).id) == []
    assert (await _login(private, VERA)).status_code == 200
    print_success("active at once")


# =============================================================================
# 3. THE LIMIT
# =============================================================================


async def _registered_and_waiting(private: _Private, monkeypatch: pytest.MonkeyPatch) -> tuple[User, str]:
    """The administrator, the option on, registration open, and Vera registered: waiting with the live link of her email."""
    await _add_user(private.engine, ADMIN, admin=True)
    await _option(private.engine, "true")
    await _registration_open(private.engine)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        registered = await _register(private, VERA)
        assert registered.status_code == 201 and registered.json()["verification_required"] is True, registered.text
        token = _token_in(fake.messages[0])
    return await _user(private.engine, VERA), token


@pytest.mark.asyncio
async def test_a_waiting_account_takes_a_place_while_its_link_is_live(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-006 — contract 3: ``LIBREFOLIO_MAX_USERS=2``, the administrator and Vera waiting: ``usage.used`` 2 and ``holds_place`` true for Vera only; a third registration is ``USER_LIMIT_REACHED``. Once her link expired: ``used`` 1, ``holds_place`` false, and the third registration goes through (waiting in turn)."""
    print_section("EVH-006: a place while the link is live")
    vera, _token = await _registered_and_waiting(private, monkeypatch)
    await _add_user(private.engine, "zq_carol", active=False)
    monkeypatch.setenv(MAX_USERS_VARIABLE, "2")

    live = await _listed(private)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        full = await _register(private, "zq_third")
        await _expire_links(private.engine, vera.id)
        expired = await _listed(private)
        freed = await _register(private, "zq_third")

    assert live["usage"]["used"] == 2 and live["holds_place"] == {ADMIN: False, VERA: True, "zq_carol": False}, live
    assert (full.status_code, _detail(full)["error_code"]) == (409, "USER_LIMIT_REACHED"), full.text
    assert expired["usage"]["used"] == 1 and expired["holds_place"][VERA] is False, expired
    assert freed.status_code == 201 and freed.json()["verification_required"] is True, freed.text
    print_success("counted while live, not once expired")


@pytest.mark.asyncio
async def test_reactivating_a_waiting_account_on_a_full_instance(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-007 — contract 3: the instance full (``LIBREFOLIO_MAX_USERS=2``: the administrator and Vera waiting with a live link): ``PATCH /users/{id}`` ``{is_active: true}`` is 200 — her place is already counted —; her emailed link is then ``TOKEN_INVALID`` ``revoked`` and she signs in."""
    print_section("EVH-007: reactivation while the link is live")
    vera, token = await _registered_and_waiting(private, monkeypatch)
    monkeypatch.setenv(MAX_USERS_VARIABLE, "2")

    activated = await _as_admin(private, "PATCH", f"{USERS}/{vera.id}", {"is_active": True})

    assert activated.status_code == 200 and activated.json()["is_active"] is True, activated.text
    clicked = await _post(private, CONFIRM, {"token": token})
    assert (clicked.status_code, _detail(clicked)["status"]) == (400, "revoked"), clicked.text
    assert (await _login(private, VERA)).status_code == 200
    print_success("200; the old link revoked; she signs in")


@pytest.mark.asyncio
async def test_reactivating_once_the_link_expired_needs_a_free_place(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-008 — contract 3: Vera's link expired, ``LIBREFOLIO_MAX_USERS=1`` reached by the administrator: ``PATCH /users/{id}`` ``{is_active: true}`` is 409 ``USER_LIMIT_REACHED``; she stays inactive."""
    print_section("EVH-008: reactivation once the link expired")
    vera, _token = await _registered_and_waiting(private, monkeypatch)
    await _expire_links(private.engine, vera.id)
    monkeypatch.setenv(MAX_USERS_VARIABLE, "1")

    refused = await _as_admin(private, "PATCH", f"{USERS}/{vera.id}", {"is_active": True})

    assert (refused.status_code, _detail(refused)["error_code"]) == (409, "USER_LIMIT_REACHED"), refused.text
    assert (await _user(private.engine, VERA)).is_active is False
    print_success("409 USER_LIMIT_REACHED")


@pytest.mark.asyncio
async def test_deactivating_a_waiting_account_changes_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-011 — contract 3 (night decision of 16/10): Vera waits, so she is already inactive: ``PATCH /users/{id}`` ``{is_active: false}`` is a no-op — 200, still inactive —; her link is still live, she is still counted (``holds_place`` true in ``GET /users``), and the link still verifies her. An unwanted sign-up is deleted, or ended by ``user deactivate`` on the command line."""
    print_section("EVH-011: deactivating a waiting account")
    vera, token = await _registered_and_waiting(private, monkeypatch)

    answered = await _as_admin(private, "PATCH", f"{USERS}/{vera.id}", {"is_active": False})

    assert answered.status_code == 200 and answered.json()["is_active"] is False, answered.text
    assert await _status(private.engine, token, VERIFICATION) == TokenStatus.VALID
    assert (await _listed(private))["holds_place"][VERA] is True
    confirmed = await _post(private, CONFIRM, {"token": token})
    assert (confirmed.status_code, confirmed.json()) == (200, {"username": VERA}), confirmed.text
    print_success("a no-op: the link live, counted, and it still verifies")


@pytest.mark.asyncio
async def test_the_patch_answer_says_whether_a_waiting_account_holds_its_place(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-012 — contract 3: the answer of ``PATCH /users/{id}`` replaces the account's row in the Users tab, so it carries the list's ``holds_place``. Vera waits with a live link: the no-op ``{is_active: false}`` and a promotion ``{is_superuser: true}`` — which leaves her inactive and her link live — each answer 200 with ``holds_place: true``, as ``GET /users`` says. Once her link expired, the same no-op answers ``holds_place: false``, as the list then does."""
    print_section("EVH-012: the PATCH answer carries holds_place")
    vera, token = await _registered_and_waiting(private, monkeypatch)

    kept = await _as_admin(private, "PATCH", f"{USERS}/{vera.id}", {"is_active": False})
    promoted = await _as_admin(private, "PATCH", f"{USERS}/{vera.id}", {"is_superuser": True})
    link_after_promotion = await _status(private.engine, token, VERIFICATION)
    listed_live = (await _listed(private))["holds_place"][VERA]
    await _expire_links(private.engine, vera.id)
    expired = await _as_admin(private, "PATCH", f"{USERS}/{vera.id}", {"is_active": False})
    listed_expired = (await _listed(private))["holds_place"][VERA]

    assert kept.status_code == 200 and (kept.json()["is_active"], kept.json()["holds_place"]) == (False, True), kept.text
    assert promoted.status_code == 200, promoted.text
    assert (promoted.json()["is_superuser"], promoted.json()["is_active"], promoted.json()["holds_place"]) == (True, False, True), promoted.text
    assert link_after_promotion == TokenStatus.VALID, "a promotion revokes no verification link: she still waits"
    assert listed_live is True, "the list says the same while the link is live"
    assert expired.status_code == 200 and (expired.json()["is_active"], expired.json()["holds_place"]) == (False, False), expired.text
    assert listed_expired is False, "the list says the same once the link expired"
    print_success("holds_place true in both answers while the link is live, false once it expired — as the list says")


# =============================================================================
# 4. THE SETTING
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["email-off", "no-public-url"])
async def test_turning_the_option_on_needs_an_email_with_a_link(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], case: str) -> None:
    """EVH-009 — contract 4: off → on without an email with a link able to go out: 409 ``{error_code: EMAIL_VERIFICATION_UNAVAILABLE, message, key}``; the option stays off and the other item of the request is not saved either."""
    print_section(f"EVH-009: {case}")
    await _add_user(private.engine, ADMIN, admin=True)
    if case == "no-public-url":
        for name, value in {"HOST": "smtp.zq-host.example.com", "FROM": SENDER_HEADER}.items():
            monkeypatch.setenv(SMTP_PREFIX + name, value)
    before = await _setting(private.engine, OTHER_KEY)

    refused = await _as_admin(private, "PATCH", BULK, {"items": [{"key": OTHER_KEY, "value": "48"}, {"key": OPTION_KEY, "value": "true"}]})

    assert refused.status_code == 409, refused.text
    detail = _detail(refused)
    assert (detail["error_code"], detail["key"], isinstance(detail.get("message"), str)) == ("EMAIL_VERIFICATION_UNAVAILABLE", OPTION_KEY, True)
    assert (await _setting(private.engine, OPTION_KEY), await _setting(private.engine, OTHER_KEY)) == ("false", before)
    assert network == []
    print_success("409, nothing saved")


@pytest.mark.asyncio
async def test_the_option_turns_on_with_email_off_always_and_on_again_whatever_email_does(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVH-010 — contract 4: with email and a public URL, off → on is saved (200). Email then broken: sending it on again, with another item, saves both (only off → on is checked); turning it off is saved."""
    print_section("EVH-010: on, on again, off")
    await _add_user(private.engine, ADMIN, admin=True)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        turned_on = await _as_admin(private, "PATCH", BULK, {"items": [{"key": OPTION_KEY, "value": "true"}]})
    _email_off(monkeypatch)
    again = await _as_admin(private, "PATCH", BULK, {"items": [{"key": OPTION_KEY, "value": "true"}, {"key": OTHER_KEY, "value": "48"}]})
    after_again = (await _setting(private.engine, OPTION_KEY), await _setting(private.engine, OTHER_KEY))
    turned_off = await _as_admin(private, "PATCH", BULK, {"items": [{"key": OPTION_KEY, "value": "false"}]})

    assert turned_on.status_code == 200, turned_on.text
    assert again.status_code == 200 and after_again == ("true", "48"), again.text
    assert turned_off.status_code == 200 and await _setting(private.engine, OPTION_KEY) == "false", turned_off.text
    print_success("on with email; on again without; off always")
