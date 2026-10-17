"""``POST /email/verification/confirm`` and ``POST /email/verification/resend``: the verification of an email address at sign-up over HTTP (developer decision 44, plan phase01Email lot E5a).

The flow itself — the hold, the emailed link, the limits — is pinned in ``test_services/test_email_verification.py``;
this module pins what the two routes answer. A's hooks (``register_user``, the login's 403 ``EMAIL_NOT_VERIFIED``) are
not written yet: an account that waits is written as ``hold_for_verification`` leaves it. The contract:

1. Both routes are anonymous: they answer without a session cookie and never set one.
2. ``confirm``: 200 ``{"username"}`` for a live link emailed to the account's address — the account then active,
   verified, and able to sign in; 400 ``{"detail": {"error_code": "TOKEN_INVALID", "status", "message"}}`` with the
   token's status otherwise (``expired``, ``consumed``, ``revoked``, ``unknown``; another purpose's token ``unknown``; a
   token without an address — the hold — ``revoked`` and left live; a link emailed to another address ``revoked``
   and revoked); 422 for a body that is not ``{token}`` (missing, empty, longer than 256, another field).
3. ``resend``: 200 ``{"language"}`` and one email for a waiting account; 401 ``{"detail": {"error_code":
   "INVALID_CREDENTIALS", "message": "Invalid credentials"}}`` for an unknown account or a wrong password, one answer
   for both, with the login's status and content type — coded since lot E-11: the web app reads any other 401 of this
   public route, such as the plain-string one of ``get_current_user`` that a blocked instance answers a caller without
   a session, as the instance's block —; 403 ``ACCOUNT_DISABLED`` for a deactivated account, the login's answer; 409
   ``EMAIL_VERIFICATION_NOT_NEEDED`` for an active account; 409 ``EMAIL_UNAVAILABLE`` and ``EMAIL_LINKS_UNAVAILABLE``
   with ``{error_code, message}`` only — no ``problem``: whoever asks is not an administrator —; 409
   ``USER_LIMIT_REACHED``; 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` and the same whole seconds, at least 1, in
   ``Retry-After`` — per client address (before the password), per account, for the hourly budget, per recipient
   mailbox (three verification emails an hour, whatever accounts share it: the same answer as every other limit) —;
   502 ``EMAIL_DELIVERY_FAILED`` with ``{error_code, message}`` only — no ``smtp_code`` either —, after which «resend»
   works at once; 422 ``EMAIL_RECIPIENT_INVALID``; 422 for a body that is not ``{username, password}``. Accounts and
   limits are asked before the configuration: an unknown account is 401 whatever email can do.
4. The client address is H's ``client_address(request)`` (the connection's address while
   ``LIBREFOLIO_CLIENT_IP_HEADER`` is unset, as here), keyed by H's ``client_rate_key`` (decision P17): one IPv6 /64 is
   one client; a request without an address (a unix socket) is not counted per address.
5. No log event holds a token, a password, an identifier or an address.
6. Neither route is in ``instance_block.ALLOWED_WHEN_BLOCKED`` (lots E-10, E-11): on a blocked instance the block, not
   the route, answers them — a caller without a session gets the plain-string 401 of ``get_current_user`` —, and the web
   app reads a 401 of theirs that is not E's own refusal as that block. This module mounts the routers without the
   block's dependency, so its ``blocked`` cases read the routes' own answers; behind ``/api/v1`` the block answers first.
7. Behind a reverse proxy LibreFolio does not trust (decision N70; lot E-13, on H's helper H-36) — the usual deployment:
   the Docker image behind the proxy HTTPS needs, neither ``LIBREFOLIO_CLIENT_IP_HEADER`` nor ``FORWARDED_ALLOW_IPS``
   set —, every visitor arrives from the proxy's private address with an ``X-Forwarded-For`` the app does not trust.
   Two visitors behind one private proxy never share one «resend» budget: the route counts H-36's
   ``rate_limit_address(request)``, the address of 4 but for a request from a local peer (``classify_ip``: loopback,
   private, link-local, unique-local, CGNAT) carrying ``X-Forwarded-For``, ``Forwarded`` or ``X-Real-IP`` whose
   address neither ``LIBREFOLIO_CLIENT_IP_HEADER`` nor uvicorn gave: ``None``, counted under no address. A public
   address's own forwarding headers move nothing, and a private address without one — a device of the local network
   talking to LibreFolio directly — keeps its own budget. EVA-018 pins the skip, red before the cure; EVA-019 and
   EVA-020 are guards, green before and after.

Pure: the real auth and email routers run in-process on a private SQLite file under ``tmp_path`` (NullPool, disposed
at teardown); accounts are rows with a real bcrypt hash at cost 4; tokens are issued by A's token service. An autouse
fixture removes every inherited ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL``, ``LIBREFOLIO_BLOCKED``,
``LIBREFOLIO_MAX_USERS`` and ``LIBREFOLIO_REGISTRATION``; each test sets its own with ``monkeypatch``. The hourly budget,
``verification.RESEND_BY_ADDRESS`` and ``verification.VERIFICATION_BY_MAILBOX`` are private limiters on a fake clock;
``socket.getaddrinfo`` resolves the loopback only; every SMTP conversation is with ``FakeSmtpServer`` on 127.0.0.1. The
lane's backend is never called. Nothing is timed.
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
from fastapi.routing import APIRoute
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1 import email as email_api
from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import AccountToken, AccountTokenPurpose, User, UserSettings
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.accounts.token_service import DEFAULT_TTL, IssuedToken, TokenStatus
from backend.app.services.email import delivery, smtp, verification
from backend.app.services.email.links import email_link
from backend.app.services.email.messages import build_verification
from backend.app.services.platform.client_address import _untrusted_forwarding, untrusted_forwarding_seen
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.fixtures.email.fake_smtp import FakeSmtpServer
from backend.test_scripts.test_utils import print_section, print_success

LOGIN = f"{API_V1_PREFIX}/auth/login"
CONFIRM = f"{API_V1_PREFIX}/email/verification/confirm"
RESEND = f"{API_V1_PREFIX}/email/verification/resend"
BASE_URL = "http://test"
TIMEOUT = 30.0

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
PUBLIC_URL_VARIABLE = "LIBREFOLIO_PUBLIC_URL"
BLOCKED_VARIABLE = "LIBREFOLIO_BLOCKED"
MAX_USERS_VARIABLE = "LIBREFOLIO_MAX_USERS"
INHERITED = (PUBLIC_URL_VARIABLE, BLOCKED_VARIABLE, MAX_USERS_VARIABLE, "LIBREFOLIO_REGISTRATION")

PUBLIC_URL = "https://folio.zq-public.example.com:8443/app"
PUBLIC_HOST = "folio.zq-public.example.com:8443"
NO_LINK_FROM_IT = "https://folio.zq-space.example.com/my folio"
SENDER_HEADER = "LibreFolio <noreply@example.com>"
UNUSED_HOST = "smtp.zq-host.example.com"
LOOPBACK_NAMES = frozenset({"127.0.0.1", "::1", "localhost"})

ACCOUNT_PASSWORD = "Verify-Api-Pass-2026"
WRONG_PASSWORD = "Not-The-Api-Pass-2026"
#: Alice waits for her link, Bob is active, Carol was deactivated by an administrator.
ALICE = "zq_alice"
BOB = "zq_bob"
CAROL = "zq_carol"
ADMIN = "zq_admin"
NOBODY = "zq_nobody"

VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
TTL = DEFAULT_TTL[VERIFICATION]
PAGE = "/verify-email"
NEVER_ISSUED = "never-issued-verification-api-0123456789abcdef"

#: The addresses the app sees requests come from (``request.client``); None is a request without one (a unix socket).
FIRST_CLIENT = ("198.51.100.7", 40001)
SECOND_CLIENT = ("203.0.113.9", 40002)
SAME_64_CLIENTS = (("2001:db8:1:2::10", 40003), ("2001:db8:1:2:ffff::1", 40004))

INVALID_TOKEN_MESSAGE = "This verification link is not valid"
RATE_LIMITED_MESSAGE = "Too many requests: try again later"
#: «resend»'s own refusal of wrong credentials, coded since lot E-11 like E's other refusals: the web app tells it from
#: the plain-string 401 of ``get_current_user`` — what a blocked instance answers a caller without a session — by the code.
INVALID_CREDENTIALS_ANSWER = {"detail": {"error_code": "INVALID_CREDENTIALS", "message": "Invalid credentials"}}

SHIPPED_RESEND = verification.RESEND_BY_ADDRESS
#: The process's limiter of verification emails per recipient mailbox, as shipped (a fixture below replaces it too).
SHIPPED_MAILBOX = verification.VERIFICATION_BY_MAILBOX
#: One mailbox written four ways, each the address of an account of its own: the limiter keys them all as MAILBOX. The
#: ways differ in the case of ``ï`` and ``ç`` alone, in NFC (one code point each): since P18 an address is unique
#: regardless of A–Z case (``ux_users_email_lower``).
MAILBOX_VARIANTS = ("zq-v\u00cf\u00e7@example.com", "zq-v\u00ef\u00e7@example.com", "zq-v\u00cf\u00c7@example.com", "zq-v\u00ef\u00c7@example.com")
MAILBOX = "zq-v\u00ef\u00e7@example.com"
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
    """Every ``LIBREFOLIO_SMTP_*`` and every variable of INHERITED the lane inherited is removed: a test sees only the variables it sets itself."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in INHERITED:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _nothing_reported_yet() -> Iterator[None]:
    """``delivery._report_invalid`` remembers for the whole process what it logged: each test starts, and leaves, with nothing reported."""
    delivery._report_invalid.cache_clear()
    yield
    delivery._report_invalid.cache_clear()


@pytest.fixture(autouse=True)
def _nothing_noted_yet(monkeypatch: pytest.MonkeyPatch) -> None:
    """H's ``_untrusted_forwarding`` (decision N70) holds fresh empty sets for each test, the process's own put back after it: the forwarding headers of section 6 — «local» from EVA-018, «public» from EVA-019 — leave no note, so a later reader's first noting of a class, the only one that logs its warning, still logs it."""
    monkeypatch.setitem(_untrusted_forwarding, "local", set())
    monkeypatch.setitem(_untrusted_forwarding, "public", set())


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture(autouse=True)
def budget(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private hourly budget on the fake clock in place of the process's."""
    limiter = SlidingWindowLimiter(50, 3600, max_keys=1, clock=clock)
    monkeypatch.setattr(delivery, "INSTANCE_BUDGET", limiter)
    return limiter


@pytest.fixture(autouse=True)
def resend_limit(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private «resend» limiter with the shipped limit, on the fake clock: no test counts in, or is counted by, the process's."""
    limiter = SlidingWindowLimiter(SHIPPED_RESEND.limit, SHIPPED_RESEND.window_seconds, clock=clock)
    monkeypatch.setattr(verification, "RESEND_BY_ADDRESS", limiter)
    return limiter


@pytest.fixture(autouse=True)
def mailbox_limit(monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> SlidingWindowLimiter:
    """A private per-mailbox limiter with the shipped limit, on the fake clock: an email of one test never counts against another's mailbox."""
    limiter = SlidingWindowLimiter(SHIPPED_MAILBOX.limit, SHIPPED_MAILBOX.window_seconds, clock=clock)
    monkeypatch.setattr(verification, "VERIFICATION_BY_MAILBOX", limiter)
    return limiter


@pytest.fixture(autouse=True)
def _bounded_smtp_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """5 s instead of 20: a defect that hangs fails sooner. No test waits for it."""
    monkeypatch.setattr(smtp, "SMTP_TIMEOUT_SECONDS", 5.0)


@pytest.fixture(autouse=True)
def network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """``socket.getaddrinfo`` resolves the loopback only; any other name is refused and recorded here."""
    resolve = socket.getaddrinfo
    refused: list[str] = []

    def loopback_only(host: Any, *args: Any, **kwargs: Any) -> Any:
        name = host.decode() if isinstance(host, bytes) else host
        if name is not None and name not in LOOPBACK_NAMES:
            refused.append(str(name))
            raise socket.gaierror(socket.EAI_NONAME, f"the email verification API tests resolve the loopback only, not {name!r}")
        return resolve(host, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", loopback_only)
    return refused


@dataclass(frozen=True)
class _Private:
    """An instance of one test: the routers of auth and email, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _app(engine: AsyncEngine) -> FastAPI:
    """The real routers of auth and email, mounted under the API prefix as ``api/v1/router.py`` mounts them; ``get_session_generator`` opens sessions on ``engine``."""
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
    """A private SQLite file under tmp_path, schema and default settings as a new install starts with; bcrypt at cost 4, the cookie's Secure attribute on ``auto``. Disposed at teardown."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'verification-api.db'}", poolclass=NullPool)
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


async def _add_user(engine: AsyncEngine, username: str, *, email: str | None = None, active: bool = True) -> User:
    """An account written as a row, ``<username>@example.com`` unless ``email`` says otherwise, with a real bcrypt hash of ACCOUNT_PASSWORD."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=email or f"{username}@example.com", hashed_password=auth_service.hash_password(ACCOUNT_PASSWORD), is_active=active)
        session.add(user)
        await session.commit()
    return user


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: object) -> IssuedToken:
    """A token issued by A's token service, committed."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _spend(engine: AsyncEngine, issued: IssuedToken, how: str) -> None:
    """``issued`` consumed or revoked, committed."""
    async with AsyncSession(engine) as session:
        if how == "consumed":
            assert await token_service.consume_token(session, issued.token, issued.record.purpose) is not None, "setup: consumed"
        else:
            assert await token_service.revoke_tokens(session, token_id=issued.record.id) == 1, "setup: revoked"
        await session.commit()


async def _waiting(engine: AsyncEngine, username: str = ALICE, *, created: datetime | None = None, email: str | None = None) -> tuple[User, IssuedToken]:
    """An account as ``hold_for_verification`` leaves it once committed: inactive, with a verification token without an address (the hold)."""
    user = await _add_user(engine, username, email=email, active=False)
    return user, await _issue(engine, VERIFICATION, user_id=user.id, now=created or utcnow())


async def _emailed(engine: AsyncEngine, user: User, *, created: datetime | None = None, how: str = "live", email: str | None = None) -> IssuedToken:
    """A verification link emailed to the account: a token carrying its address (or ``email``); ``how`` consumed or revoked spends it."""
    issued = await _issue(engine, VERIFICATION, user_id=user.id, email=email or user.email, now=created or utcnow())
    if how != "live":
        await _spend(engine, issued, how)
    return issued


async def _account(engine: AsyncEngine, user_id: int) -> User:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await session.get(User, user_id)


async def _rows(engine: AsyncEngine, user_id: int) -> list[AccountToken]:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        statement = select(AccountToken).where(AccountToken.purpose == VERIFICATION, AccountToken.user_id == user_id).order_by(AccountToken.id)
        return list((await session.execute(statement)).scalars().all())


async def _status(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose = VERIFICATION) -> TokenStatus:
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return (await token_service.inspect_token(session, token, purpose)).status


async def _awaits(engine: AsyncEngine, user_id: int) -> bool:
    async with AsyncSession(engine) as session:
        return await verification.awaiting_verification(session, await session.get(User, user_id))


def _configure(monkeypatch: pytest.MonkeyPatch, variables: dict[str, str | None]) -> None:
    for name, value in variables.items():
        variable = SMTP_PREFIX + name.upper()
        if value is None:
            monkeypatch.delenv(variable, raising=False)
        else:
            monkeypatch.setenv(variable, value)


def _ready(monkeypatch: pytest.MonkeyPatch, fake: FakeSmtpServer, **extra: str | None) -> None:
    """Email through ``fake`` (no TLS on the loopback, this module's sender, ``extra`` on top) and links ready on PUBLIC_URL."""
    _configure(monkeypatch, {"host": fake.host, "port": str(fake.port), "tls": "none", "from": SENDER_HEADER, **extra})
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)


def _set_up(monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    """The configuration a case names, on top of a usable one towards UNUSED_HOST with links ready (for answers that never send)."""
    if case == "email-off":
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
        return
    _configure(monkeypatch, {"host": UNUSED_HOST, "from": SENDER_HEADER})
    monkeypatch.setenv(PUBLIC_URL_VARIABLE, PUBLIC_URL)
    if case == "email-unusable":
        _configure(monkeypatch, {"tls": "ssl"})
    elif case == "links-missing":
        monkeypatch.delenv(PUBLIC_URL_VARIABLE, raising=False)
    elif case == "links-invalid":
        monkeypatch.setenv(PUBLIC_URL_VARIABLE, NO_LINK_FROM_IT)
    elif case == "blocked":
        monkeypatch.setenv(BLOCKED_VARIABLE, "1")
    else:
        assert case == "ready", case


@contextlib.asynccontextmanager
async def _browser(private: _Private, *, client: tuple[str, int] | None = FIRST_CLIENT) -> AsyncIterator[httpx.AsyncClient]:
    """A browser of its own without a session, its requests from ``client`` (the address the app sees; None: no address)."""
    transport = httpx.ASGITransport(app=private.app, client=client)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as browser:
        yield browser


async def _post(private: _Private, path: str, body: object, *, client: tuple[str, int] | None = FIRST_CLIENT, headers: dict[str, str] | None = None) -> httpx.Response:
    """One anonymous ``POST`` of ``body`` as JSON, from a fresh browser at ``client``, carrying ``headers``."""
    async with _browser(private, client=client) as browser:
        return await browser.post(path, json=body, headers=headers)


async def _confirm(private: _Private, token: str) -> httpx.Response:
    return await _post(private, CONFIRM, {"token": token})


async def _resend(private: _Private, username: str, password: str = ACCOUNT_PASSWORD, *, client: tuple[str, int] | None = FIRST_CLIENT, headers: dict[str, str] | None = None) -> httpx.Response:
    return await _post(private, RESEND, {"username": username, "password": password}, client=client, headers=headers)


def _detail(response: httpx.Response) -> dict[str, Any]:
    """``detail`` of a coded refusal: a mapping, not FastAPI's list of validation errors."""
    detail = response.json().get("detail")
    assert isinstance(detail, dict), f"expected a coded refusal in detail: {response.status_code} {response.text}"
    return detail


def _text(received: object) -> str:
    return received.message.get_body(preferencelist=("plain",)).get_content()


def _html(received: object) -> str:
    return received.message.get_body(preferencelist=("html",)).get_content()


def _lines(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip("\n")


def _token_in(text: str) -> str:
    """The token of the PUBLIC_URL verification link an email text carries; fails when it carries none."""
    match = re.search(re.escape(f"{PUBLIC_URL}{PAGE}#") + r"(\S+)", text)
    assert match, f"no {PUBLIC_URL}{PAGE} link in the email: {text!r}"
    return parse_qs(match.group(1))["token"][0]


def _assert_is_the_verification_email(received: object, *, language: str = "en", username: str = ALICE) -> str:
    """The message is exactly the verification email of the link it carries, greeting nobody by name — ``username``, the account's, in no part of it (decision N62) —; that link's token."""
    token = _token_in(_text(received))
    assert username not in received.message["Subject"] + _text(received) + _html(received), "the verification email greets nobody by name: whoever signs up chooses the username (N62)"
    expected = build_verification(language=language, link=email_link(VERIFICATION, token), ttl=TTL, instance=PUBLIC_HOST)
    assert received.message["Subject"] == expected.subject
    assert _lines(_text(received)) == _lines(expected.text)
    assert _lines(_html(received)) == _lines(expected.html)
    return token


def _holding(events: list[dict[str, Any]], *needles: str) -> list[dict[str, Any]]:
    return [event for event in events if any(needle in repr(event) for needle in needles)]


# =============================================================================
# 1. ANONYMOUS
# =============================================================================


@pytest.mark.asyncio
async def test_both_routes_answer_without_a_session_and_set_none(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVA-001 — contract 1: from a browser without any cookie, «resend» answers 200 and the link it emailed then confirms with 200; neither answer sets a cookie, and the browser holds none afterwards."""
    print_section("EVA-001: anonymous")
    alice, _hold = await _waiting(private.engine)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        async with _browser(private) as browser:
            resent = await browser.post(RESEND, json={"username": ALICE, "password": ACCOUNT_PASSWORD})
            confirmed = await browser.post(CONFIRM, json={"token": _token_in(_text(fake.messages[0]))})
            jar = list(browser.cookies.jar)

    assert (resent.status_code, confirmed.status_code) == (200, 200), (resent.text, confirmed.text)
    assert [response.headers.get_list("set-cookie") for response in (resent, confirmed)] == [[], []]
    assert jar == []
    print_success("200 twice, no cookie set")


# =============================================================================
# 2. CONFIRM
# =============================================================================


@pytest.mark.asyncio
async def test_a_live_link_confirms_with_the_username_and_the_account_signs_in(private: _Private) -> None:
    """EVA-002 — contract 2: a live link emailed to the account's address: 200 with ``{"username"}`` alone; the account is active and verified, the link consumed, and ``POST /auth/login`` then answers 200. The token is in no log event."""
    print_section("EVA-002: a live link")
    alice = await _add_user(private.engine, ALICE, active=False)
    link = await _emailed(private.engine, alice)
    before = utcnow()

    with capture_logs() as events:
        response = await _confirm(private, link.token)

    assert (response.status_code, response.json()) == (200, {"username": ALICE}), response.text
    account = await _account(private.engine, alice.id)
    assert account.is_active is True and ensure_utc(account.email_verified_at) >= before
    assert await _status(private.engine, link.token) == TokenStatus.CONSUMED
    signed_in = await _post(private, LOGIN, {"username": ALICE, "password": ACCOUNT_PASSWORD})
    assert signed_in.status_code == 200, signed_in.text
    assert _holding(events, link.token) == []
    print_success("200 {username}, active, verified, signs in")


async def _dead_link(private: _Private, kind: str) -> tuple[User, str]:
    """Alice, inactive, and a token that is not a live verification link of her address (EVA-003)."""
    moment = utcnow()
    alice = await _add_user(private.engine, ALICE, active=False)
    if kind == "expired":
        return alice, (await _emailed(private.engine, alice, created=moment - TTL - timedelta(hours=1))).token
    if kind in ("consumed", "revoked"):
        return alice, (await _emailed(private.engine, alice, how=kind)).token
    if kind == "never-issued":
        return alice, NEVER_ISSUED
    if kind == "the-accounts-reset-link":
        return alice, (await _issue(private.engine, PASSWORD_RESET, user_id=alice.id)).token
    if kind == "the-hold":
        return alice, (await _issue(private.engine, VERIFICATION, user_id=alice.id)).token
    assert kind == "emailed-to-another-address", kind
    return alice, (await _emailed(private.engine, alice, email="zq-old-alice@example.com")).token


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kind", "status", "after"),
    [
        pytest.param("expired", "expired", TokenStatus.EXPIRED, id="expired"),
        pytest.param("consumed", "consumed", TokenStatus.CONSUMED, id="consumed"),
        pytest.param("revoked", "revoked", TokenStatus.REVOKED, id="revoked"),
        pytest.param("never-issued", "unknown", None, id="never-issued"),
        pytest.param("the-accounts-reset-link", "unknown", None, id="the-accounts-reset-link"),
        pytest.param("the-hold", "revoked", TokenStatus.VALID, id="the-hold-left-live"),
        pytest.param("emailed-to-another-address", "revoked", TokenStatus.REVOKED, id="emailed-to-another-address-revoked"),
    ],
)
async def test_a_link_that_cannot_verify_answers_400_with_its_status(private: _Private, kind: str, status: str, after: TokenStatus | None) -> None:
    """EVA-003 — contract 2: 400 ``{"detail": {"error_code": "TOKEN_INVALID", "status", "message"}}`` with the token's status: expired, consumed, revoked, a token never issued or of another purpose (``unknown``), the hold (``revoked``, and left live: the account still waits), a link emailed to another address (``revoked``, and revoked). The account stays inactive and unverified; the token is in no log event."""
    print_section(f"EVA-003: {kind}")
    alice, token = await _dead_link(private, kind)

    with capture_logs() as events:
        response = await _confirm(private, token)

    assert response.status_code == 400, response.text
    assert response.json() == {"detail": {"error_code": "TOKEN_INVALID", "status": status, "message": INVALID_TOKEN_MESSAGE}}
    account = await _account(private.engine, alice.id)
    assert (account.is_active, account.email_verified_at) == (False, None)
    if after is not None:
        assert await _status(private.engine, token) == after
    if kind == "the-hold":
        assert await _awaits(private.engine, alice.id) is True
    assert _holding(events, token) == []
    print_success(f"400 TOKEN_INVALID {status}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="no-token"),
        pytest.param({"token": ""}, id="an-empty-token"),
        pytest.param({"token": "t" * 257}, id="a-token-of-257-characters"),
        pytest.param({"token": 12345}, id="a-token-that-is-not-text"),
        pytest.param({"token": "zq-token", "username": ALICE}, id="another-field"),
    ],
)
async def test_a_body_that_is_not_a_token_answers_422(private: _Private, body: dict[str, Any]) -> None:
    """EVA-004 — contract 2: a body that is not ``{token}`` — no token, an empty one, one longer than 256 characters, one that is not text, another field — is refused by validation, 422 with FastAPI's list of errors; nothing changes."""
    print_section(f"EVA-004: {sorted(body)}")
    alice = await _add_user(private.engine, ALICE, active=False)
    link = await _emailed(private.engine, alice)

    response = await _post(private, CONFIRM, body)

    assert response.status_code == 422 and isinstance(response.json().get("detail"), list), response.text
    assert await _status(private.engine, link.token) == TokenStatus.VALID
    assert (await _account(private.engine, alice.id)).is_active is False
    print_success("422")


# =============================================================================
# 3. RESEND
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(("own", "language"), [pytest.param(None, "en", id="the-instances-language"), pytest.param("it", "it", id="the-accounts-own-language")])
async def test_resend_answers_200_with_the_language_and_emails_the_link(private: _Private, monkeypatch: pytest.MonkeyPatch, own: str | None, language: str) -> None:
    """EVA-005 — contract 3: the right password for a waiting account: 200 ``{"language"}`` alone, the language of the email; one message to the account's address, exactly the verification email of a live link, greeting nobody by name (decision N62)."""
    print_section(f"EVA-005: {language}")
    alice, _hold = await _waiting(private.engine)
    if own is not None:
        async with AsyncSession(private.engine) as session:
            session.add(UserSettings(user_id=alice.id, language=own, theme="light"))
            await session.commit()

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        response = await _resend(private, ALICE)

    assert (response.status_code, response.json()) == (200, {"language": language}), response.text
    assert len(fake.messages) == 1 and fake.messages[0].rcpt_tos == [alice.email]
    token = _assert_is_the_verification_email(fake.messages[0], language=language)
    assert await _status(private.engine, token) == TokenStatus.VALID
    print_success(f"200 {language}, the link emailed")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("who", "password"),
    [
        pytest.param(NOBODY, ACCOUNT_PASSWORD, id="an-unknown-account"),
        pytest.param(ALICE, WRONG_PASSWORD, id="a-wrong-password-for-the-waiting-account"),
        pytest.param(BOB, WRONG_PASSWORD, id="a-wrong-password-for-an-active-account"),
        pytest.param(CAROL, WRONG_PASSWORD, id="a-wrong-password-for-a-deactivated-account"),
    ],
)
async def test_wrong_credentials_get_one_coded_401_whatever_the_account(private: _Private, monkeypatch: pytest.MonkeyPatch, who: str, password: str) -> None:
    """EVA-006 — contract 3: an unknown account, or a wrong password whatever the account: 401 ``{"detail": {"error_code": "INVALID_CREDENTIALS", "message": "Invalid credentials"}}``, one answer for all four, so that it never tells whether the account exists (and one cost: EMV-029 pins the single bcrypt check of each, a dummy hash's for an unknown account), with the status and the content type ``POST /auth/login`` answers to the same credentials. Coded since lot E-11, where it was the login's plain-string ``"Invalid credentials"``: the web app reads any other 401 of this public route — the plain-string one of ``get_current_user``, which a blocked instance answers a caller without a session — as the instance's block. Nothing sent."""
    print_section(f"EVA-006: {who}")
    await _waiting(private.engine)
    await _add_user(private.engine, BOB)
    await _add_user(private.engine, CAROL, active=False)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        resent = await _resend(private, who, password)
        login = await _post(private, LOGIN, {"username": who, "password": password})

    assert (resent.status_code, resent.json()) == (401, INVALID_CREDENTIALS_ANSWER), f"the route's own refusal of wrong credentials is coded INVALID_CREDENTIALS (lot E-11): a 401 with a plain-string detail is what the web app reads as the instance's block: {resent.status_code} {resent.text}"
    assert (resent.status_code, resent.headers.get("content-type")) == (login.status_code, login.headers.get("content-type")), f"the login's status and content type for the same credentials: {login.status_code} {login.headers.get('content-type')}"
    assert fake.connections == 0
    print_success("401 INVALID_CREDENTIALS, whatever the account")


@pytest.mark.asyncio
async def test_a_deactivated_account_gets_the_logins_403(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVA-007 — contract 3: the right password for an account an administrator deactivated (its link revoked): 403 ``ACCOUNT_DISABLED``, the same answer as ``POST /auth/login``; nothing sent."""
    print_section("EVA-007: deactivated")
    carol = await _add_user(private.engine, CAROL, active=False)
    await _emailed(private.engine, carol, how="revoked")

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        resent = await _resend(private, CAROL)
        login = await _post(private, LOGIN, {"username": CAROL, "password": ACCOUNT_PASSWORD})

    assert (resent.status_code, _detail(resent)) == (403, {"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}), resent.text
    assert (resent.status_code, resent.content) == (login.status_code, login.content)
    assert fake.connections == 0
    print_success("403 ACCOUNT_DISABLED, the login's answer")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "detail"),
    [
        pytest.param("an-active-account", {"error_code": "EMAIL_VERIFICATION_NOT_NEEDED", "message": "This account is active: sign in"}, id="an-active-account"),
        pytest.param("email-off", {"error_code": "EMAIL_UNAVAILABLE", "message": "This instance cannot send emails"}, id="email-off"),
        pytest.param("email-unusable", {"error_code": "EMAIL_UNAVAILABLE", "message": "This instance cannot send emails"}, id="email-unusable"),
        pytest.param("blocked", {"error_code": "EMAIL_UNAVAILABLE", "message": "This instance cannot send emails"}, id="blocked"),
        pytest.param("links-missing", {"error_code": "EMAIL_LINKS_UNAVAILABLE", "message": "This instance cannot send emails with a link"}, id="links-missing"),
        pytest.param("links-invalid", {"error_code": "EMAIL_LINKS_UNAVAILABLE", "message": "This instance cannot send emails with a link"}, id="links-invalid"),
        pytest.param("an-expired-link-on-a-full-instance", {"error_code": "USER_LIMIT_REACHED", "message": "The instance has reached its maximum number of users"}, id="an-expired-link-on-a-full-instance"),
    ],
)
async def test_each_409_answers_its_code_and_message_and_nothing_else(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], case: str, detail: dict[str, str]) -> None:
    """EVA-008 — contract 3: 409 with ``{error_code, message}`` and nothing else — ``EMAIL_VERIFICATION_NOT_NEEDED`` for an active account; ``EMAIL_UNAVAILABLE`` (email off, unusable, the instance blocked) and ``EMAIL_LINKS_UNAVAILABLE`` (missing, invalid) without the ``problem`` an administrator would read; ``USER_LIMIT_REACHED`` for a link that expired on a full instance. Nothing sent, no host looked up."""
    print_section(f"EVA-008: {case}")
    await _add_user(private.engine, ADMIN)
    if case == "an-active-account":
        await _add_user(private.engine, ALICE)
    else:
        await _waiting(private.engine, created=utcnow() - (TTL + timedelta(hours=1) if case.startswith("an-expired") else timedelta(minutes=5)))
    if case == "an-expired-link-on-a-full-instance":
        monkeypatch.setenv(MAX_USERS_VARIABLE, "1")
    _set_up(monkeypatch, case if case in ("email-off", "email-unusable", "blocked", "links-missing", "links-invalid") else "ready")

    response = await _resend(private, ALICE)

    assert (response.status_code, _detail(response)) == (409, detail), response.text
    assert network == []
    print_success(f"409 {detail['error_code']}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "seconds"),
    [
        pytest.param("per-address", 840, id="per-address"),
        pytest.param("per-address-a-fraction-left", 1, id="per-address-half-a-second-left-is-one"),
        pytest.param("per-account", 180, id="per-account"),
        pytest.param("budget", 3000, id="the-hourly-budget"),
    ],
)
async def test_each_limit_answers_429_with_retry_after(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter, limit: str, seconds: int) -> None:
    """EVA-009 — contract 3: 429 ``{"error_code": "EMAIL_RATE_LIMITED", "retry_after", "message"}`` with the same whole seconds — rounded up, at least 1 — in ``Retry-After``: ten requests from the client's address in a minute, the eleventh with the right password refused before its password is checked (840 s; half a second left is 1); a link emailed to the account two minutes ago (180 s); the hourly budget spent ten minutes ago (3000 s). Nothing sent."""
    print_section(f"EVA-009: {limit}")
    moment = utcnow()
    monkeypatch.setattr(verification, "utcnow", lambda: moment)
    alice = await _add_user(private.engine, ALICE, active=False)
    if limit == "per-account":
        await _emailed(private.engine, alice, created=moment - timedelta(minutes=2))
    else:
        await _issue(private.engine, VERIFICATION, user_id=alice.id, now=moment)
    checked: list[str] = []
    verify = verification.verify_password_or_dummy

    def recording(plain: str, hashed: str | None) -> bool:
        checked.append(plain)
        return verify(plain, hashed)

    monkeypatch.setattr(verification, "verify_password_or_dummy", recording)
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake, **({"max_per_hour": "1"} if limit == "budget" else {}))
        clock.now = START
        if limit.startswith("per-address"):
            for _attempt in range(10):
                assert (await _resend(private, ALICE, WRONG_PASSWORD)).status_code == 401
            clock.now = START + (60 if limit == "per-address" else 899.5)
        elif limit == "budget":
            assert budget.hit(limit=1).allowed, "setup: the only unit of the hour"
            clock.now = START + 600
        checked_before = len(checked)
        response = await _resend(private, ALICE)

    assert response.status_code == 429, response.text
    assert _detail(response) == {"error_code": "EMAIL_RATE_LIMITED", "retry_after": seconds, "message": RATE_LIMITED_MESSAGE}
    assert response.headers.get("retry-after") == str(seconds)
    if limit.startswith("per-address"):
        assert len(checked) == checked_before, "the limit per address comes before the password"
    assert fake.messages == []
    print_success(f"429, Retry-After {seconds}")


@pytest.mark.asyncio
async def test_a_refusal_of_the_smtp_server_answers_502_and_resend_works_at_once(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVA-010 — contract 3: the SMTP server refuses the account's address: 502 ``{"error_code": "EMAIL_DELIVERY_FAILED", "message"}`` and nothing else — whoever asks is not an administrator: no ``smtp_code``, no word of the server's reason anywhere in the answer —; the account still waits; asked again at once, the link goes out — 200, not 429."""
    print_section("EVA-010: 502, then 200")
    alice, _hold = await _waiting(private.engine)

    with FakeSmtpServer(refuse_recipients={alice.email}) as refusing:
        _ready(monkeypatch, refusing)
        refused = await _resend(private, ALICE)
    assert refused.status_code == 502, refused.text
    assert _detail(refused) == {"error_code": "EMAIL_DELIVERY_FAILED", "message": "The email could not be sent"}
    assert "RECIPIENT_REFUSED" not in refused.text and "smtp" not in refused.text.casefold(), refused.text
    assert await _awaits(private.engine, alice.id) is True
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        again = await _resend(private, ALICE)

    assert (again.status_code, again.json()) == (200, {"language": "en"}), again.text
    assert len(fake.messages) == 1
    print_success("502 without the SMTP reason, then 200")


@pytest.mark.asyncio
async def test_an_address_that_is_not_one_address_answers_422(private: _Private, monkeypatch: pytest.MonkeyPatch, budget: SlidingWindowLimiter) -> None:
    """EVA-011 — contract 3: the account's address is not one address: 422 ``{"error_code": "EMAIL_RECIPIENT_INVALID", "message"}``; no connection, nothing spent."""
    print_section("EVA-011: not one address")
    await _waiting(private.engine, email="zq_alice@example.com, zq-other@example.com")

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        response = await _resend(private, ALICE)

    assert response.status_code == 422, response.text
    assert _detail(response) == {"error_code": "EMAIL_RECIPIENT_INVALID", "message": "The address of this account is not a single email address"}
    assert (fake.connections, budget.count()) == (0, 0)
    print_success("422 EMAIL_RECIPIENT_INVALID")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="nothing"),
        pytest.param({"username": ALICE}, id="no-password"),
        pytest.param({"password": ACCOUNT_PASSWORD}, id="no-username"),
        pytest.param({"username": "", "password": ACCOUNT_PASSWORD}, id="an-empty-username"),
        pytest.param({"username": ALICE, "password": ""}, id="an-empty-password"),
        pytest.param({"username": "u" * 255, "password": ACCOUNT_PASSWORD}, id="a-username-of-255-characters"),
        pytest.param({"username": ALICE, "password": "p" * 1025}, id="a-password-of-1025-characters"),
        pytest.param({"username": ALICE, "password": ACCOUNT_PASSWORD, "token": "zq-token"}, id="another-field"),
    ],
)
async def test_a_body_that_is_not_credentials_answers_422_and_counts_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, resend_limit: SlidingWindowLimiter, body: dict[str, Any]) -> None:
    """EVA-012 — contract 3: a body that is not ``{username, password}`` — a field missing or empty, a username longer than 254 or a password longer than 1024 characters, another field — is refused by validation, 422 with FastAPI's list of errors, before the route: nothing counted for the client's address, nothing sent."""
    print_section(f"EVA-012: {sorted(body)}")
    await _waiting(private.engine)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        response = await _post(private, RESEND, body)

    assert response.status_code == 422 and isinstance(response.json().get("detail"), list), response.text
    assert (len(resend_limit), fake.connections) == (0, 0)
    print_success("422, nothing counted")


@pytest.mark.asyncio
async def test_the_client_address_is_keyed_and_a_request_without_one_is_not_counted(private: _Private, resend_limit: SlidingWindowLimiter) -> None:
    """EVA-013 — contract 4: two clients of one IPv6 /64 count as one — five requests each, the eleventh 429 —; requests without a client address (a unix socket) are not counted per address — twelve of them all reach the password (401)."""
    print_section("EVA-013: the client address")
    await _waiting(private.engine)
    first, second = SAME_64_CLIENTS

    statuses = [(await _resend(private, ALICE, WRONG_PASSWORD, client=first if attempt < 5 else second)).status_code for attempt in range(11)]
    assert statuses == [401] * 10 + [429], statuses
    without = [(await _resend(private, ALICE, WRONG_PASSWORD, client=None)).status_code for _attempt in range(12)]

    assert without == [401] * 12
    assert resend_limit.count("2001:db8:1:2::/64") == 10 and len(resend_limit) == 1
    print_success("one /64, one count; no address, no count")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("who", "case", "status", "body"),
    [
        pytest.param(NOBODY, "email-off", 401, INVALID_CREDENTIALS_ANSWER, id="an-unknown-account-email-off"),
        pytest.param(NOBODY, "blocked", 401, INVALID_CREDENTIALS_ANSWER, id="an-unknown-account-instance-blocked"),
        pytest.param(BOB, "email-off", 409, {"detail": {"error_code": "EMAIL_VERIFICATION_NOT_NEEDED", "message": "This account is active: sign in"}}, id="an-active-account-email-off"),
        pytest.param(CAROL, "email-off", 403, {"detail": {"error_code": "ACCOUNT_DISABLED", "message": "Account is disabled"}}, id="a-deactivated-account-email-off"),
    ],
)
async def test_the_accounts_come_before_the_configuration(private: _Private, monkeypatch: pytest.MonkeyPatch, network: list[str], who: str, case: str, status: int, body: dict[str, Any]) -> None:
    """EVA-014 — contract 3: what the instance cannot do is said only to the owner of a waiting account: with email off or the instance blocked (the route's own answers: this module mounts no block, contract 6), an unknown account is still the route's own 401, coded ``INVALID_CREDENTIALS`` since lot E-11, an active one 409 ``EMAIL_VERIFICATION_NOT_NEEDED``, a deactivated one 403 — an answer never tells who has an account by what email can do."""
    print_section(f"EVA-014: {who}, {case}")
    await _waiting(private.engine)
    await _add_user(private.engine, BOB)
    await _add_user(private.engine, CAROL, active=False)
    _set_up(monkeypatch, case)

    response = await _resend(private, who)

    assert (response.status_code, response.json()) == (status, body), f"the account's answer whatever email can do — for an unknown account the route's own 401, coded INVALID_CREDENTIALS since lot E-11: {response.status_code} {response.text}"
    assert network == []
    print_success(f"{status}")


@pytest.mark.asyncio
async def test_no_log_event_holds_a_token_a_password_an_identifier_or_an_address(private: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
    """EVA-015 — contract 5: through «resend» (200, a wrong password, an unknown account) and two clicks (a link never issued, the emailed link): the routes' flow logs (the barrier), and no event holds the token, a password, an identifier, the account's address or the client's address."""
    print_section("EVA-015: the logs")
    alice, hold = await _waiting(private.engine)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        with capture_logs() as events:
            assert (await _resend(private, ALICE)).status_code == 200
            assert (await _resend(private, ALICE, WRONG_PASSWORD)).status_code == 401
            assert (await _resend(private, NOBODY)).status_code == 401
            token = _token_in(_text(fake.messages[0]))
            assert (await _confirm(private, NEVER_ISSUED)).status_code == 400
            assert (await _confirm(private, token)).status_code == 200

    assert [event.get("event") for event in events if event.get("event") in ("Verification link emailed", "Email verified")] == ["Verification link emailed", "Email verified"], f"barrier: the flow logged: {events}"
    secrets = (hold.token, token, NEVER_ISSUED, ACCOUNT_PASSWORD, WRONG_PASSWORD, alice.email, ALICE, NOBODY, FIRST_CLIENT[0])
    assert _holding(events, *secrets) == [], f"a log event holds a secret: {_holding(events, *secrets)}"
    print_success(f"{len(events)} events, none holding a secret")


# =============================================================================
# 4. AFTER THE SECURITY REVIEW OF E5b
# =============================================================================


@pytest.mark.asyncio
async def test_a_mailbox_with_three_verification_emails_this_hour_answers_429_as_any_limit(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, budget: SlidingWindowLimiter, mailbox_limit: SlidingWindowLimiter) -> None:
    """EVA-016 — contract 3: four waiting accounts whose addresses are one mailbox written four ways (``zq-vÏç@example.com``, ``zq-vïç@…``, ``zq-vÏÇ@…``, ``zq-vïÇ@…``: the case of ``ï`` and ``ç`` alone, since P18 makes an address unique regardless of A–Z case), the last with a link emailed two hours ago, still live. The first three ask «resend», a minute apart: 200 each, one email each. The fourth, a minute later, is 429 ``{"error_code": "EMAIL_RATE_LIMITED", "retry_after": 3420, "message"}`` with ``Retry-After: 3420`` — when the oldest of the three leaves the hour —: the answer of every other limit (EVA-009), so nothing tells whoever asks that other accounts share the mailbox. Nothing is created for that account: its tokens as they were, its link of two hours ago still live; no fourth message, no fourth unit of the budget; the mailbox counted three times."""
    print_section("EVA-016: three verification emails per mailbox")
    assert {written.casefold() for written in MAILBOX_VARIANTS} == {MAILBOX}, "precondition: four spellings of one mailbox"
    assert len({user_service.email_fold(written) for written in MAILBOX_VARIANTS}) == len(MAILBOX_VARIANTS), "precondition: four accounts on one mailbox: one casefold key, four addresses for the A–Z unique index (P18)"
    moment = utcnow()
    monkeypatch.setattr(verification, "utcnow", lambda: moment)
    accounts = [await _waiting(private.engine, f"zq_vic_{index}", created=moment - timedelta(hours=3), email=written) for index, written in enumerate(MAILBOX_VARIANTS)]
    last = accounts[-1][0]
    old_link = await _emailed(private.engine, last, created=moment - timedelta(hours=2))
    before = [(row.id, row.email, row.consumed_at, row.revoked_at) for row in await _rows(private.engine, last.id)]

    answers: list[httpx.Response] = []
    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        for index, (user, _hold) in enumerate(accounts):
            clock.now = START + 60 * index
            answers.append(await _resend(private, user.username))

    assert [answer.status_code for answer in answers[:3]] == [200, 200, 200], [answer.text for answer in answers[:3]]
    refused = answers[3]
    assert refused.status_code == 429, refused.text
    assert _detail(refused) == {"error_code": "EMAIL_RATE_LIMITED", "retry_after": 3420, "message": RATE_LIMITED_MESSAGE}
    assert refused.headers.get("retry-after") == "3420"
    assert [message.rcpt_tos for message in fake.messages] == [[written] for written in MAILBOX_VARIANTS[:3]]
    assert [(row.id, row.email, row.consumed_at, row.revoked_at) for row in await _rows(private.engine, last.id)] == before
    assert await _status(private.engine, old_link.token) == TokenStatus.VALID
    assert (budget.count(), mailbox_limit.count(MAILBOX)) == (3, 3)
    print_success("200 three times; the fourth 429 for 3420 s, nothing made for it")


# =============================================================================
# 5. THE INSTANCE BLOCK (LOTS E-10, E-11)
# =============================================================================


def test_neither_route_is_allowed_on_a_blocked_instance() -> None:
    """EVA-017 — contract 6, a guard, green before and after lot E-11: neither ``email.confirm_email_verification`` (lot E-10) nor ``email.resend_email_verification`` (lot E-11) is in ``instance_block.ALLOWED_WHEN_BLOCKED``. Why: the web app reads a 401 of these two public routes that is not E's own refusal as the instance's block (``frontend/src/lib/features/email/verificationApi.ts``) — ``readLinkRefusal`` any 401 of «confirm», which has none of its own; ``readResendFailure`` any 401 of «resend» but the coded ``INVALID_CREDENTIALS`` of EVA-006 —, and that reading holds only while the block, not the route, answers a caller without a session on a blocked instance: with the plain-string 401 of ``get_current_user``. Putting either route in the list changes what the web app must read, so its readers change with it. Barriers, so that the absence is not vacuous: the two functions are the endpoints of ``POST`` CONFIRM and RESEND, and the list holds endpoint functions, the sign-in's ``auth.login`` among them."""
    print_section("EVA-017: neither route in ALLOWED_WHEN_BLOCKED")
    served = {(method, f"{API_V1_PREFIX}{route.path}"): route.endpoint for route in email_api.router.routes if isinstance(route, APIRoute) for method in route.methods}
    assert served.get(("POST", CONFIRM)) is email_api.confirm_email_verification, f"barrier: POST {CONFIRM} is served by email.confirm_email_verification: {served.get(('POST', CONFIRM))!r}"
    assert served.get(("POST", RESEND)) is email_api.resend_email_verification, f"barrier: POST {RESEND} is served by email.resend_email_verification: {served.get(('POST', RESEND))!r}"
    assert auth_api.login in ALLOWED_WHEN_BLOCKED, "barrier: the list holds endpoint functions, the sign-in's among them"

    allowed = sorted(endpoint.__name__ for endpoint in (email_api.confirm_email_verification, email_api.resend_email_verification) if endpoint in ALLOWED_WHEN_BLOCKED)

    assert allowed == [], f"on a blocked instance the block, not the route, must answer these public routes: the web app reads a 401 of theirs that is not E's own refusal as the instance's block (lots E-10, E-11); in ALLOWED_WHEN_BLOCKED: {allowed}"
    print_success("neither route in the list: on a blocked instance the block answers them")


# =============================================================================
# 6. BEHIND A PROXY LIBREFOLIO DOES NOT TRUST (DECISION N70, LOT E-13)
# =============================================================================

#: The address every request comes from behind a reverse proxy LibreFolio does not trust: the proxy's own, private —
#: the Docker bridge's, or an IPv6 unique-local one. Any port: the key of an address never holds it.
PRIVATE_PROXIES = [pytest.param("172.17.0.1", id="docker-bridge-ipv4"), pytest.param("fd00::2", id="unique-local-ipv6")]
PROXY_PORT = 40100
#: Two visitors, as a forwarding header names them: A asks first, B after.
VISITOR_A = "203.0.113.10"
VISITOR_B = "203.0.113.20"
#: A device of the local network that talks to LibreFolio directly: a private address, and no forwarding header.
LAN_DEVICE = ("192.168.1.5", 40200)
#: H-36's forwarding headers, exactly its list: (the header, what precedes the address in it). A reverse proxy writes
#: them for the visitor it forwards.
FORWARDING_HEADERS = [
    pytest.param("X-Forwarded-For", "", id="x-forwarded-for"),
    pytest.param("Forwarded", "for=", id="forwarded"),
    pytest.param("X-Real-IP", "", id="x-real-ip"),
]
#: The forwarding headers a client at a public address may write itself: the same three.
OWN_FORWARDING_HEADERS = FORWARDING_HEADERS


@pytest.mark.asyncio
@pytest.mark.parametrize(("header", "prefix"), FORWARDING_HEADERS)
@pytest.mark.parametrize("proxy", PRIVATE_PROXIES)
async def test_two_visitors_behind_one_private_proxy_do_not_share_the_resend_budget(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, proxy: str, header: str, prefix: str) -> None:
    """EVA-018 — contract 7, red before the cure of decision N70 (H-36's ``rate_limit_address``): ``RESEND_BY_ADDRESS`` at one request for this test, email ready. Both requests come from the proxy's private address — ``172.17.0.1``, the Docker bridge; ``fd00::2``, an IPv6 unique-local one —, each with a forwarding header naming its visitor and each for a name no account has, so that no limit per account applies. Visitor A: 401 ``INVALID_CREDENTIALS``. Visitor B, through the same proxy: 401 too, never 429. Then the skip itself, which B's answer alone would not prove: the limiter per address holds no key at all — neither visitor counted under an address, the proxy's or their own. Nothing sent. The headers are exactly H-36's list — ``X-Forwarded-For``, ``Forwarded`` (``for=…``), ``X-Real-IP`` —, crossed with the two peers: six cases."""
    print_section(f"EVA-018: two visitors behind {proxy}, {header}")
    by_address = SlidingWindowLimiter(1, SHIPPED_RESEND.window_seconds, clock=clock)
    monkeypatch.setattr(verification, "RESEND_BY_ADDRESS", by_address)
    peer = (proxy, PROXY_PORT)

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        first = await _resend(private, f"{NOBODY}_a", client=peer, headers={header: f"{prefix}{VISITOR_A}"})
        second = await _resend(private, f"{NOBODY}_b", client=peer, headers={header: f"{prefix}{VISITOR_B}"})

    assert (first.status_code, first.json()) == (401, INVALID_CREDENTIALS_ANSWER), f"barrier: visitor A reaches the password check: {first.status_code} {first.text}"
    assert second.status_code != 429, f"two visitors behind one private proxy ({proxy}) shared one per-address budget: visitor B was refused because visitor A had asked: {second.text}"
    assert (second.status_code, second.json()) == (401, INVALID_CREDENTIALS_ANSWER), f"{second.status_code} {second.text}"
    assert len(by_address) == 0, f"a request through a reverse proxy LibreFolio does not trust ({proxy}, {header}) is counted under no address (N70): the limiter per address holds {len(by_address)} key(s)"
    assert untrusted_forwarding_seen("local") == (header,), f"N70's skip notes the {header} of a local peer: noted {untrusted_forwarding_seen('local')}"
    assert fake.connections == 0
    print_success("401 for each visitor, and no key in the limiter per address: the skip")


@pytest.mark.asyncio
@pytest.mark.parametrize(("header", "prefix"), OWN_FORWARDING_HEADERS)
async def test_a_public_clients_own_forwarding_header_moves_nothing(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock, header: str, prefix: str) -> None:
    """EVA-019 — contract 7, a guard, green before and after the cure: ``RESEND_BY_ADDRESS`` at one request for this test, email ready. A client at the public address ``198.51.100.7`` writes a forwarding header itself — ``X-Forwarded-For``, ``Forwarded`` (``for=…``) or ``X-Real-IP`` —, naming ``203.0.113.10``, then ``203.0.113.20``, each time for a name no account has: 401, then 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 900 and ``Retry-After: 900`` — the whole window, counted from the first —: what a client writes never moves its own budget. Nothing sent. The forwarding headers that count follow H-36, and the cure may extend the parametrization."""
    print_section(f"EVA-019: a public client's own {header}")
    monkeypatch.setattr(verification, "RESEND_BY_ADDRESS", SlidingWindowLimiter(1, SHIPPED_RESEND.window_seconds, clock=clock))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        first = await _resend(private, f"{NOBODY}_a", client=FIRST_CLIENT, headers={header: f"{prefix}{VISITOR_A}"})
        second = await _resend(private, f"{NOBODY}_b", client=FIRST_CLIENT, headers={header: f"{prefix}{VISITOR_B}"})

    assert (first.status_code, first.json()) == (401, INVALID_CREDENTIALS_ANSWER), f"barrier: the first request reaches the password check: {first.status_code} {first.text}"
    assert second.status_code == 429, f"a client at a public address chose its own budget with a {header} header it wrote itself: {second.status_code} {second.text}"
    assert _detail(second) == {"error_code": "EMAIL_RATE_LIMITED", "retry_after": 900, "message": RATE_LIMITED_MESSAGE}
    assert second.headers.get("retry-after") == "900"
    assert fake.connections == 0
    print_success(f"401, then 429 whatever its own {header} says")


@pytest.mark.asyncio
async def test_a_private_client_without_a_forwarding_header_keeps_its_own_budget(private: _Private, monkeypatch: pytest.MonkeyPatch, clock: FakeClock) -> None:
    """EVA-020 — contract 7, a guard, green before and after the cure: ``RESEND_BY_ADDRESS`` at one request for this test, email ready. A device of the local network talks to LibreFolio directly — the private address ``192.168.1.5``, no forwarding header —, twice for a name no account has: 401, then 429 ``EMAIL_RATE_LIMITED`` with ``retry_after`` 900 and ``Retry-After: 900``: a private address alone is not a proxy, and keeps its own budget. Nothing sent. The forwarding headers that count follow H-36, and the cure may extend the parametrization."""
    print_section("EVA-020: a device of the local network")
    monkeypatch.setattr(verification, "RESEND_BY_ADDRESS", SlidingWindowLimiter(1, SHIPPED_RESEND.window_seconds, clock=clock))

    with FakeSmtpServer() as fake:
        _ready(monkeypatch, fake)
        first = await _resend(private, f"{NOBODY}_a", client=LAN_DEVICE)
        second = await _resend(private, f"{NOBODY}_b", client=LAN_DEVICE)

    assert (first.status_code, first.json()) == (401, INVALID_CREDENTIALS_ANSWER), f"barrier: the first request reaches the password check: {first.status_code} {first.text}"
    assert second.status_code == 429, f"a private address without a forwarding header lost its own budget: {second.status_code} {second.text}"
    assert _detail(second) == {"error_code": "EMAIL_RATE_LIMITED", "retry_after": 900, "message": RATE_LIMITED_MESSAGE}
    assert second.headers.get("retry-after") == "900"
    assert fake.connections == 0
    print_success("401, then 429: its own budget")
