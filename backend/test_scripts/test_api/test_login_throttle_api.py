"""
Login limit API — release 1.3, workstream A, lot A8a (plan phase01Accounts §4.8, A8a C1–C4): F15, a limit on failed
sign-ins, and ``GET /api/v1/security/checks``, the administrator's list of the «Security» checks; then decision N70:
the limit per address behind a local reverse proxy LibreFolio does not trust.

The contract, over HTTP:

1. ``POST /auth/login``, the limit on. Ten wrong passwords for one identifier: the next attempt — the right password
   included — answers 429, ``detail.error_code`` ``TOO_MANY_ATTEMPTS`` (the code is the contract, never the wording),
   one ``Retry-After`` of a positive whole number of seconds, no session cookie. An identifier no account matches gets
   the same answer (no enumeration). The identifier counts with A–Z folded (``Alice`` and ``alice`` are one), from any
   address; another identifier, from the same address or another, still signs in. Nine wrong and one right reset the
   identifier. A refused attempt runs no password check — the 429 comes before bcrypt — and does not count, and
   ``Retry-After`` is the wait: that many seconds later the right password signs in, one second earlier it does not.
   The right password of an inactive account (403 ``ACCOUNT_DISABLED``) is not a failure: it neither counts nor resets
   the count (plan C1: only a 200 resets the identifier).
2. Per address: fifty failures from one address over different identifiers → the next attempt from that address, any
   identifier, is 429; another address is not affected.
3. ``POST /auth/change-password``: a wrong current password counts on the account's own identifier — its username,
   A–Z folded: the login's bucket, both ways — and on the address; at the limit, 429 even with the right current
   password, and the password stays; a successful change resets the account's count.
4. ``PUT /auth/profile`` with a real email change, the one change that asks for ``current_password``: a wrong current
   password counts the same way; at the limit, 429 and the address stays.
5. ``LIBREFOLIO_LOGIN_LIMIT``: unset is ``on``; ``off`` turns the limit off — sixty wrong passwords, sixty 401s.
6. ``GET /api/v1/security/checks``: 401 without a session, 403 for a member, 200 for an administrator with ``{"items":
   [...]}``: each item a ``check_id``, a ``severity`` (``ok``, ``info``, ``warning`` or ``error``), an ``i18n_key`` and
   a ``detail`` object, each check once — every check ``config_audit.run_config_checks()`` evaluates, as it evaluates
   it, and ``platform.plugin_secrets`` as ``check_plugin_secrets`` evaluates it on the database served. Among them A's
   ``accounts.login_limit``: ``ok`` with the limit on or unset, ``warning`` with ``off``. No secret value reaches the
   answer (``JWT_SECRET``, the SMTP password), nor the SMTP server and user a check's log summary names: an item is the
   check's i18n key and parameters, never its summary (F04, as ``GET /email/status``).
7. ``POST /email/verification/resend``, workstream E's «resend», checks the sign-in's credentials, so it is under the
   sign-in's limit, in its two buckets and both ways: the identifier as typed, stripped, A–Z folded — not the username
   of the account it finds —, and the address. A wrong password at the resend, or an identifier no account matches, is
   a failure in both: ten for an identifier, and the sign-in typed so is 429 ``TOO_MANY_ATTEMPTS``; forty-nine failed
   sign-ins from an address and one wrong resend from it lock that address. An attempt the limit refuses — ten failures
   for the identifier, or fifty from the address — is refused before the password: 429 ``detail.error_code``
   ``EMAIL_RATE_LIMITED``, the resend's answer to all its limits, with ``detail.retry_after`` and ``Retry-After`` the
   same whole seconds, the wait; one body for the right password and a wrong one, no ``bcrypt.checkpw``, nothing
   counted in either bucket; the wait over, the right password signs in. The right password at the resend forgets the
   identifier's failures whatever the answer then — 409 ``EMAIL_VERIFICATION_NOT_NEEDED`` for an active account, 403
   ``ACCOUNT_DISABLED`` for a deactivated one —: as a change of password does, unlike the sign-in's 403 (item 1). E's
   own limit per address, ten resends in 15 minutes, is E's to pin, not this file's.
8. Behind a local reverse proxy LibreFolio does not trust (decision N70 of 17/10, on workstream E's R13-SEC6) every
   visitor has the proxy's address, and fifty failures of anyone would refuse everyone. At its three places that check
   a password — the sign-in, the change of password, the change of email address — ``auth.py`` gives the throttle
   workstream H's ``rate_limit_address(request)`` (H-36): ``None`` for a request whose peer is local — ``classify_ip``
   of ``utils/runtime/network.py`` says ``lan``, ``loopback`` or ``vpn``, the CGNAT range included — and which carries
   a forwarding header nothing applied (``X-Forwarded-For``, ``Forwarded``, ``X-Real-IP``); ``client_address(request)``
   otherwise. ``None`` counts and refuses under the identifier alone. So: fifty wrong passwords through such a proxy,
   over fifty identifiers, lock nobody else out; a wrong password through it, at any of the three places, counts on its
   identifier and on no address; an address its own failures locked refuses its direct requests and lets through what
   the proxy forwards — decided per request —; ten wrong passwords for one identifier through the proxy still lock
   that identifier. A public peer is the client whatever it forwards: its failures lock it, and the header it forwards
   is not the key either. A local peer forwarding nothing is a client like any other. The resend behind a proxy is
   workstream E's (its lot E-13), and the once-per-process warning H's: neither is pinned here.

Where it runs: in-process only, never on the lane, whose server runs with the limit off (``dev.py server --test``):
``test_security_checks_api.py`` pins that line. Each case has a private SQLite file under ``tmp_path`` (NullPool,
disposed at teardown), the schema and default settings of a new install, accounts written as rows with a real bcrypt
hash. The login-limit cases mount the real auth router, as ``api/v1/router.py`` mounts it; the security-check cases the
whole ``/api/v1`` router of ``api/v1/router.py``, as ``main.py`` mounts it: whatever module A8a gives the route, the
path is the one the app serves, and the line of ``router.py`` is part of what is pinned. The resend cases mount the
whole ``/api/v1`` router as well: the sign-in and E's resend side by side, each at the path the app serves.

The harness:

- The limit is turned on explicitly (``LIBREFOLIO_LOGIN_LIMIT=on``), and ``login_throttle.LOGIN_BY_IDENTIFIER`` and
  ``LOGIN_BY_ADDRESS`` are replaced by fresh limiters of the contract's size — 10 and 50 failures in 15 minutes — on a
  fake clock only the test moves: a case starts clean, moves time instead of waiting for it, and never counts in, nor
  resets, the process's own limiters. The routes must read the two limiters through the module at request time (as
  E's routes read ``delivery.ADDRESS_BUDGET``, the counter per client address), not bind them at import. The security-check cases replace no
  limiter: they sign in with the limit off for that one request.
- In the resend cases E's ``delivery.ADDRESS_BUDGET`` — every resend hits it first — is replaced too, by a fresh
  limiter of its shipped size (its limit and window, never its counts) on the same fake clock: the process's own is
  neither counted nor consulted. No address sends more than two resends — a case that needs ten sends each from a
  documentation address of its own —, so E's limit never answers in place of A's.
- Addresses: each request comes from a client of its own whose ASGI ``client`` is a documentation address
  (``httpx.ASGITransport(client=…)``). No request carries the header ``LIBREFOLIO_CLIENT_IP_HEADER`` may name, so H's
  ``client_address(request)`` is the connection's whatever this process configured.
- The N70 cases are the exception: their proxies are local addresses (``10.0.0.7``, ``192.168.1.20``, ``127.0.0.1``,
  ``100.100.1.5``) and their requests carry forwarding headers, ``X-Real-IP`` among them. So they unset
  ``LIBREFOLIO_CLIENT_IP_HEADER`` — no header gives the address — and ``FORWARDED_ALLOW_IPS`` — uvicorn's default,
  which trusts none of those peers but ``127.0.0.1`` —, and start over, before and after, the reads H's module caches
  once per process (``untrusted_proxy``). No uvicorn stands in front of the app, so no header is applied: H's helper
  decides for real, through the routes, and nothing fakes it. ``127.0.0.1`` never forwards ``X-Forwarded-For`` here:
  uvicorn would have applied it, and what H's helper answers for a request it could not receive is H's to choose.
- bcrypt at cost 4, and the dummy hash an unknown identifier is checked against is a private one of cost 4: the
  process's own, computed once and cached (LOGIN-024 of ``test_auth_api.py`` checks it has the shipped cost), is left
  as it was.
- Session cookies are read from ``Set-Cookie`` and sent explicitly; a new one replaces the old, as a browser keeps it.
- ``bcrypt.checkpw`` — where every password check ends — is spied where a case counts checks.
- Every inherited ``LIBREFOLIO_SMTP_*``, ``LIBREFOLIO_PUBLIC_URL``, ``LIBREFOLIO_BLOCKED``, ``LIBREFOLIO_REGISTRATION``,
  ``LIBREFOLIO_MAX_USERS`` and ``LIBREFOLIO_LOGIN_LIMIT`` is removed: a case sets its own. Nothing waits.

Red until A8a, every case. The login-limit cases first at their setup: ``backend.app.services.accounts.login_throttle``
does not exist. Once it does, until the routes use it, at their first expected 429: today's routes answer 401, 400 or
200. LT-API-15 is a guard of the switch: its assertions hold today — there is no limit at all — and it is red only at
its setup, for the module whose limiters it replaces. The security-check cases on the route: 404.

The resend cases (LT-API-16 to 19, «red until A8a (resend)»), written once the rest of A8a was in, are red until
``resend_verification`` asks and counts in ``login_throttle``: it does neither — E's limit per address is its only
one —, so each fails at its first expectation of the sign-in's limit, never at its setup: the sign-in after ten wrong
resends answers 200, or 401 where no account matches (LT-API-16); the resend of a locked identifier or address answers
409 (LT-API-17); after the resend's 409 or 403 the second of ten wrong passwords is a 429, nothing forgotten
(LT-API-18); Carol's sign-in from an address with forty-nine failed sign-ins and a wrong resend answers 200
(LT-API-19).

The N70 cases (LT-API-20 to 25, item 8), written once the rest of A8a was in. The reds, «red until A8a (N70)»: today
the three places count and refuse every request under ``client_address(request)``, the proxy's address, so each fails
on the 429 that address answers — never at its setup: Carol's sign-in through the proxy after fifty failures through it
(LT-API-20); a newcomer's sign-in from the proxy's address after forty-nine failures of its own and one through the
proxy (LT-API-24); the request through the proxy from an address its own failures locked (LT-API-25). They stay red
until workstream H's ``rate_limit_address`` (H-36) is in this branch and ``auth.py`` gives it to the throttle.
LT-API-21, 22 and 23 are guards, green today and to stay green: the identifier's limit through the proxy, a public
peer's header, a local peer forwarding nothing.

Isolation: pure — no lane, no server, no shared row. Process-wide state — the variables, the two limiters and E's
resend limiter, bcrypt's cost and dummy hash, ``bcrypt.checkpw``, the cookie's Secure mode — is replaced through
``monkeypatch`` and put back; the reads H's module caches are started over around each N70 case.
"""

from __future__ import annotations

import contextlib
import functools
import importlib
import os
import re
import uuid
from collections import Counter
from collections.abc import AsyncIterator, Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import bcrypt
import httpx
import pytest
import pytest_asyncio
from fastapi import APIRouter, FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request

from backend.app.api.v1 import auth as auth_api
from backend.app.api.v1.router import router as api_v1_router
from backend.app.config import API_V1_PREFIX
from backend.app.db.base import SQLModel  # imports every model: SQLModel.metadata holds the whole schema
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.services.accounts import auth_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.app.services.email import delivery
from backend.app.services.platform import config_audit
from backend.app.services.platform.client_address import client_address
from backend.app.services.platform.plugin_secrets_check import check_plugin_secrets
from backend.app.utils.runtime.rate_window import SlidingWindowLimiter
from backend.test_scripts.test_utils import print_section, print_success

THROTTLE_MODULE = "backend.app.services.accounts.login_throttle"
LIMIT_VARIABLE = "LIBREFOLIO_LOGIN_LIMIT"
#: The contract's limits (plan §4.8, A8a C1): failures per identifier and per address, in a window of 15 minutes.
IDENTIFIER_LIMIT = 10
ADDRESS_LIMIT = 50
WINDOW_SECONDS = 15 * 60
#: Where the fake clock starts: a case's failures happen at START unless it moves the clock.
START = 1_000.0
#: How far into the window a case asks how long the wait is.
ASKED_AFTER_SECONDS = 600
#: Sixty failures from one address for one identifier: past both limits.
PAST_BOTH_LIMITS = 60

LOGIN = f"{API_V1_PREFIX}/auth/login"
CHANGE_PASSWORD = f"{API_V1_PREFIX}/auth/change-password"
PROFILE = f"{API_V1_PREFIX}/auth/profile"
SECURITY_CHECKS = f"{API_V1_PREFIX}/security/checks"
#: Workstream E's «resend»: the verification email again, for whoever gives the sign-in's credentials.
RESEND = f"{API_V1_PREFIX}/email/verification/resend"
COOKIE = auth_api.SESSION_COOKIE_NAME
BASE_URL = "http://test"
TIMEOUT = 30.0

#: The addresses requests come from, as the app sees them (the ASGI ``client``): documentation ranges.
ADDRESS_A = ("198.51.100.7", 41001)
ADDRESS_B = ("203.0.113.9", 41002)
#: The security-check cases sign in from an address of their own.
CHECKS_ADDRESS = ("192.0.2.80", 41080)

#: Passwords that meet the rules (decision 37); WRONG_PASSWORD is nobody's.
PASSWORD = "Throttle-Api-Pass-2026"
WRONG_PASSWORD = "Not-The-Api-Pass-2026"
NEW_PASSWORD = "Throttle-New-Pass-2026"
NEWER_PASSWORD = "Throttle-Newer-Pass-2026"

ALICE = "alice"
BOB = "bob"
CAROL = "carol"
#: An identifier no account matches.
NOBODY = "nobody_here"
#: Alice's username as it may be typed: A–Z folded, each one is ``alice``.
ALICE_TYPED = ("alice", "Alice", "ALICE", "aLiCe", "AlIcE")
#: Alice's username in capitals: usernames match exactly, so no account is named so, but A–Z folded it is hers.
ALICE_IN_CAPITALS = "ALICE"
#: The address Alice's email change asks for: a real change, so the current password is asked.
NEW_EMAIL = "alice.new@example.com"
#: Alice's address as ``_add_user`` writes it, and typed in capitals: an account matches it either way (P18), and A–Z
#: folded the two are one identifier — not her username, a key of its own.
ALICE_EMAIL = "alice@example.com"
ALICE_EMAIL_IN_CAPITALS = "ALICE@EXAMPLE.COM"
#: ``detail.error_code`` of the resend's 429, its answer to every one of its limits (workstream E).
EMAIL_RATE_LIMITED = "EMAIL_RATE_LIMITED"

SEVERITIES = frozenset({"ok", "info", "warning", "error"})
LOGIN_LIMIT_CHECK = "accounts.login_limit"
JWT_SECRET_CHECK = "platform.jwt_secret"
PLUGIN_SECRETS_CHECK = "platform.plugin_secrets"
SMTP_CHECK = "email.smtp"
SMTP_ENCRYPTION_CHECK = "email.smtp_encryption"

SMTP_PREFIX = "LIBREFOLIO_SMTP_"
#: The variables no case inherits: each case sets its own.
INHERITED = (LIMIT_VARIABLE, "LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_SIGNUP_EMAILS_PER_ADDRESS")


class FakeClock:
    """A clock that moves only when the test sets it: ``clock.now = …``."""

    def __init__(self, start: float = START) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


# ============================================================================
# FIXTURES: THE VARIABLES, BCRYPT, THE PRIVATE INSTANCE, THE LIMITERS
# ============================================================================


@pytest.fixture(autouse=True)
def _no_inherited_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every ``LIBREFOLIO_SMTP_*`` and every variable of INHERITED this process inherited is removed: a case sees only what it sets."""
    for name in list(os.environ):
        if name.startswith(SMTP_PREFIX) or name in INHERITED:
            monkeypatch.delenv(name, raising=False)


@functools.cache
def _cheap_dummy_hash() -> str:
    """This module's dummy hash: bcrypt of cost 4 of a random password, computed once, never matched."""
    return bcrypt.hashpw(uuid.uuid4().hex.encode(), bcrypt.gensalt(rounds=4)).decode()


@pytest.fixture
def cheap_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at cost 4, the hashes and the dummy hash alike — the process's cached dummy is left as it was —; the cookie's Secure attribute on ``auto`` (plain HTTP here)."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)
    monkeypatch.setattr(auth_service, "_dummy_password_hash", _cheap_dummy_hash)
    monkeypatch.setattr(auth_api, "SESSION_COOKIE_SECURE_MODE", "auto")


@dataclass(frozen=True)
class _Private:
    """An instance of one case: a router of the real app, every session on ``engine``."""

    engine: AsyncEngine
    app: FastAPI


def _app(engine: AsyncEngine, router: APIRouter) -> FastAPI:
    """``router`` mounted under the API prefix; ``get_session_generator`` opens sessions on ``engine``."""
    app = FastAPI()
    app.include_router(router, prefix=API_V1_PREFIX)

    async def private_session() -> AsyncIterator[AsyncSession]:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session_generator] = private_session
    return app


@contextlib.asynccontextmanager
async def _private_instance(tmp_path: Path, router: APIRouter) -> AsyncIterator[_Private]:
    """A private SQLite file under tmp_path — the schema and default settings a new install starts with, no account — served by ``router``; disposed at the end."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'login-throttle.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            await initialize_global_settings(session)
        yield _Private(engine=engine, app=_app(engine, router))
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def private(tmp_path: Path, cheap_passwords: None) -> AsyncIterator[_Private]:
    """The real auth router — login, change-password, profile — as ``api/v1/router.py`` mounts it, on a private database."""
    async with _private_instance(tmp_path, auth_api.router) as instance:
        yield instance


@pytest_asyncio.fixture
async def private_api(tmp_path: Path, cheap_passwords: None) -> AsyncIterator[_Private]:
    """The whole ``/api/v1`` router of ``api/v1/router.py``, as ``main.py`` mounts it, on a private database: the security checks answer at the path the app serves, wherever A8a puts the route."""
    async with _private_instance(tmp_path, api_v1_router) as instance:
        yield instance


@dataclass(frozen=True)
class _Throttle:
    """The two limiters the routes count on in a case, fresh, and the fake clock they read."""

    clock: FakeClock
    by_identifier: SlidingWindowLimiter
    by_address: SlidingWindowLimiter


def _login_throttle() -> ModuleType:
    """``services/accounts/login_throttle.py``, imported here and not at the top: until A8a each case that needs it fails on its own, and this module still loads."""
    try:
        return importlib.import_module(THROTTLE_MODULE)
    except ImportError as error:
        pytest.fail(f"{THROTTLE_MODULE} must exist, with LOGIN_BY_IDENTIFIER and LOGIN_BY_ADDRESS (A8a, C1): {error}")


@pytest.fixture
def throttle(monkeypatch: pytest.MonkeyPatch) -> _Throttle:
    """The limit on, explicitly — the lane's server runs with it off —, and ``LOGIN_BY_IDENTIFIER`` and ``LOGIN_BY_ADDRESS`` replaced by fresh limiters of the contract's size on a fake clock: a case starts clean, moves time instead of waiting, and never counts in the process's own limiters."""
    module = _login_throttle()
    for name in ("LOGIN_BY_IDENTIFIER", "LOGIN_BY_ADDRESS"):
        shipped = getattr(module, name, None)
        assert isinstance(shipped, SlidingWindowLimiter), f"login_throttle.{name} must be the module's SlidingWindowLimiter (A8a, C1): {shipped!r}"
    clock = FakeClock()
    limiters = _Throttle(
        clock=clock,
        by_identifier=SlidingWindowLimiter(IDENTIFIER_LIMIT, WINDOW_SECONDS, clock=clock),
        by_address=SlidingWindowLimiter(ADDRESS_LIMIT, WINDOW_SECONDS, clock=clock),
    )
    monkeypatch.setattr(module, "LOGIN_BY_IDENTIFIER", limiters.by_identifier)
    monkeypatch.setattr(module, "LOGIN_BY_ADDRESS", limiters.by_address)
    monkeypatch.setenv(LIMIT_VARIABLE, "on")
    return limiters


@pytest.fixture
def checkpw_calls(monkeypatch: pytest.MonkeyPatch) -> list[bytes]:
    """Every ``bcrypt.checkpw`` call — where every password check ends: ``verify_password``, and ``verify_password_or_dummy`` for an unknown identifier —, recorded by the hash it checked against; the real check still runs."""
    real_checkpw = bcrypt.checkpw
    calls: list[bytes] = []

    def spying_checkpw(password: bytes, hashed_password: bytes) -> bool:
        calls.append(hashed_password)
        return real_checkpw(password, hashed_password)

    monkeypatch.setattr(bcrypt, "checkpw", spying_checkpw)
    return calls


# ============================================================================
# HELPERS: ACCOUNTS, REQUESTS, BROWSERS
# ============================================================================


async def _add_user(engine: AsyncEngine, username: str, *, active: bool = True, admin: bool = False) -> int:
    """An account written as a row, ``<username>@example.com``, with a real bcrypt hash of PASSWORD (cost 4): its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.com", hashed_password=auth_service.hash_password(PASSWORD), is_active=active, is_superuser=admin)
        session.add(user)
        await session.commit()
    return user.id


async def _request(private: _Private, method: str, path: str, *, address: tuple[str, int], cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request from a client of its own at ``address`` (the ASGI ``client``): no cookie jar, the session cookie, if any, sent explicitly."""
    headers = {"Cookie": f"{COOKIE}={cookie}"} if cookie else {}
    transport = httpx.ASGITransport(app=private.app, client=address)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as client:
        return await client.request(method, path, json=json, headers=headers)


async def _login(private: _Private, identifier: str, password: str, *, address: tuple[str, int] = ADDRESS_A) -> httpx.Response:
    """``POST /auth/login`` with ``identifier`` and ``password``, from ``address``."""
    return await _request(private, "POST", LOGIN, address=address, json={"username": identifier, "password": password})


async def _fail_logins(private: _Private, identifiers: Iterable[str], *, address: tuple[str, int] = ADDRESS_A) -> None:
    """A wrong password for each of ``identifiers``, in order, from ``address``. It ends on its promise: each one answered 401, a failure the limit still allowed."""
    for number, identifier in enumerate(identifiers, start=1):
        response = await _login(private, identifier, WRONG_PASSWORD, address=address)
        assert response.status_code == 401, f"wrong password #{number} ({identifier!r} from {address[0]}): expected 401, a failure still allowed — got {response.status_code} {response.text}"


def _strangers(count: int) -> list[str]:
    """``count`` identifiers no account matches, each different: one failure each stays far from an identifier's limit."""
    return [f"stranger_{number:02d}" for number in range(count)]


def _session_cookies(response: httpx.Response) -> list[str]:
    """The values the answer's ``Set-Cookie`` headers give the session cookie, found by name."""
    values = []
    for header in response.headers.get_list("set-cookie"):
        name, _, value = header.split(";", 1)[0].partition("=")
        if name.strip() == COOKIE:
            values.append(value.strip())
    return values


@dataclass
class _Browser:
    """A browser signed in to the private instance: the account, the address it sends from, its session cookie — replaced when an answer sets a new one."""

    user_id: int
    username: str
    email: str
    address: tuple[str, int]
    cookie: str


async def _signed_in(private: _Private, username: str, *, address: tuple[str, int] = ADDRESS_A) -> _Browser:
    """An account written as a row and signed in through ``POST /auth/login`` from ``address``. It ends on its promise: a 200 and one session cookie."""
    user_id = await _add_user(private.engine, username)
    response = await _login(private, username, PASSWORD, address=address)
    cookies = _session_cookies(response)
    assert response.status_code == 200 and len(cookies) == 1 and cookies[0], f"setup: {username} signs in from {address[0]}: {response.status_code} {response.text}"
    return _Browser(user_id=user_id, username=username, email=f"{username}@example.com", address=address, cookie=cookies[0])


async def _as(private: _Private, browser: _Browser, method: str, path: str, body: dict[str, Any]) -> httpx.Response:
    """``method path`` with ``body`` from ``browser``: its address, its session cookie. A new session cookie in the answer replaces the browser's, as a browser keeps it."""
    response = await _request(private, method, path, address=browser.address, cookie=browser.cookie, json=body)
    renewed = [value for value in _session_cookies(response) if value]
    if renewed:
        browser.cookie = renewed[-1]
    return response


async def _change_password(private: _Private, browser: _Browser, current: str, new: str) -> httpx.Response:
    """``POST /auth/change-password`` from ``browser``."""
    return await _as(private, browser, "POST", CHANGE_PASSWORD, {"current_password": current, "new_password": new})


async def _change_email(private: _Private, browser: _Browser, current: str) -> httpx.Response:
    """``PUT /auth/profile`` from ``browser``, its address changed to NEW_EMAIL — a real change, so the current password is asked."""
    return await _as(private, browser, "PUT", PROFILE, {"email": NEW_EMAIL, "current_password": current})


async def _password_is(engine: AsyncEngine, user_id: int, password: str) -> bool:
    """Whether ``password`` is the account's now, read fresh."""
    async with AsyncSession(engine) as session:
        hashed = (await session.execute(select(User.hashed_password).where(User.id == user_id))).scalar_one()
    return auth_service.verify_password(password, hashed)


async def _email_of(engine: AsyncEngine, user_id: int) -> str:
    """The account's address now, read fresh."""
    async with AsyncSession(engine) as session:
        return (await session.execute(select(User.email).where(User.id == user_id))).scalar_one()


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


def _retry_after(response: httpx.Response) -> Optional[int]:
    """The one ``Retry-After`` header as whole seconds; None when it is missing, repeated, or anything but digits (an HTTP date included)."""
    values = response.headers.get_list("retry-after")
    if len(values) != 1 or not re.fullmatch(r"[0-9]+", values[0].strip()):
        return None
    return int(values[0])


def _assert_too_many_attempts(response: httpx.Response, request: str) -> int:
    """``response`` is the limit's refusal: 429, ``detail.error_code`` ``TOO_MANY_ATTEMPTS`` (the code, never the wording), one ``Retry-After`` of a positive whole number of seconds within the window, and no session cookie. Those seconds."""
    assert response.status_code == 429, f"{request}: expected 429 TOO_MANY_ATTEMPTS, got {response.status_code} {response.text}"
    assert _error_code(response) == "TOO_MANY_ATTEMPTS", f"{request}: the 429 carries detail.error_code TOO_MANY_ATTEMPTS: {response.text}"
    seconds = _retry_after(response)
    assert seconds is not None and 1 <= seconds <= WINDOW_SECONDS, f"{request}: Retry-After must be one positive whole number of seconds, at most the window ({WINDOW_SECONDS}): {response.headers.get_list('retry-after')}"
    assert _session_cookies(response) == [], f"{request}: a refusal sets no session cookie: Set-Cookie {response.headers.get_list('set-cookie')}"
    return seconds


# ============================================================================
# 1. POST /auth/login — THE LIMIT PER IDENTIFIER
# ============================================================================


class TestLoginLimit:
    """POST /auth/login, the limit on: ten failures for one identifier, then 429 — before bcrypt, for everyone alike."""

    # red until A8a
    @pytest.mark.asyncio
    @pytest.mark.parametrize("setting", ["on", None], ids=["on", "unset-is-on"])
    async def test_ten_wrong_passwords_lock_the_identifier_even_for_the_right_one(self, private: _Private, throttle: _Throttle, monkeypatch: pytest.MonkeyPatch, setting: Optional[str]) -> None:
        """LT-API-01: ten wrong passwords for ``alice`` → the eleventh attempt, her right password, → 429 ``TOO_MANY_ATTEMPTS`` with ``Retry-After``, no session cookie. ``LIBREFOLIO_LOGIN_LIMIT`` ``on``, or unset: on by default (C3). Barrier: the failures were counted on the limiters ``login_throttle`` holds at the request, one key in each."""
        print_section(f"LT-API-01: ten wrong passwords lock the identifier (limit {setting or 'unset'})")
        if setting is None:
            monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
        await _add_user(private.engine, ALICE)
        await _fail_logins(private, [ALICE] * IDENTIFIER_LIMIT)

        refused = await _login(private, ALICE, PASSWORD)

        _assert_too_many_attempts(refused, f"POST /auth/login as {ALICE!r} with the right password, after {IDENTIFIER_LIMIT} wrong ones")
        counted = (len(throttle.by_identifier), len(throttle.by_address))
        assert counted == (1, 1), f"the failures must be counted on login_throttle.LOGIN_BY_IDENTIFIER and LOGIN_BY_ADDRESS as the module holds them at the request — read through the module, never bound at import —: keys counted (identifier, address) {counted}"
        print_success("429 TOO_MANY_ATTEMPTS with Retry-After, the right password included")

    # red until A8a
    @pytest.mark.asyncio
    async def test_an_identifier_no_account_matches_gets_the_same_429(self, private: _Private, throttle: _Throttle, checkpw_calls: list[bytes]) -> None:
        """LT-API-02: ten wrong passwords for ``alice`` (an account) from one address, and for ``nobody_here`` (none) from another → the next attempt of each — Alice's right password, any password for nobody — is 429, the two bodies the same, both with ``Retry-After``: the limit tells nobody which accounts exist. Neither 429 runs a password check, the dummy one included."""
        print_section("LT-API-02: the same 429 whether an account exists or not")
        await _add_user(private.engine, ALICE)
        await _fail_logins(private, [ALICE] * IDENTIFIER_LIMIT, address=ADDRESS_A)
        await _fail_logins(private, [NOBODY] * IDENTIFIER_LIMIT, address=ADDRESS_B)
        checks_before = len(checkpw_calls)

        known = await _login(private, ALICE, PASSWORD, address=ADDRESS_A)
        unknown = await _login(private, NOBODY, PASSWORD, address=ADDRESS_B)
        checks = len(checkpw_calls) - checks_before

        _assert_too_many_attempts(known, f"POST /auth/login as {ALICE!r}, an account, after {IDENTIFIER_LIMIT} wrong passwords")
        _assert_too_many_attempts(unknown, f"POST /auth/login as {NOBODY!r}, no account, after {IDENTIFIER_LIMIT} wrong passwords")
        assert unknown.json() == known.json(), f"no enumeration: the 429 for an identifier no account matches must be the one an account gets: {unknown.json()} vs {known.json()}"
        assert checks == 0, f"the 429 comes before bcrypt, with or without an account: bcrypt.checkpw ran {checks} time(s) for the two refusals"
        print_success("one 429 for both, no password check")

    # red until A8a
    @pytest.mark.asyncio
    async def test_the_identifier_counts_with_a_to_z_folded(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-03: ten wrong passwords for Alice's username typed five ways — ``alice``, ``Alice``, ``ALICE``, ``aLiCe``, ``AlIcE``, twice each — → ``alice`` with the right password is 429: A–Z folded, they are one identifier."""
        print_section("LT-API-03: the identifier counts with A–Z folded")
        await _add_user(private.engine, ALICE)
        await _fail_logins(private, [ALICE_TYPED[number % len(ALICE_TYPED)] for number in range(IDENTIFIER_LIMIT)])

        refused = await _login(private, ALICE, PASSWORD)

        _assert_too_many_attempts(refused, f"POST /auth/login as {ALICE!r} after {IDENTIFIER_LIMIT} wrong passwords typed {list(ALICE_TYPED)}: A–Z folded, one identifier")

    # red until A8a
    @pytest.mark.asyncio
    async def test_the_lock_is_the_identifiers_from_any_address_and_no_one_elses(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-04: Alice locked by ten wrong passwords from address A → Alice from address B is 429 too (the identifier counts, wherever it comes from); Bob from address A — ten failures there, far from fifty — and Carol from address B sign in (200)."""
        print_section("LT-API-04: the lock is the identifier's, from any address")
        for username in (ALICE, BOB, CAROL):
            await _add_user(private.engine, username)
        await _fail_logins(private, [ALICE] * IDENTIFIER_LIMIT, address=ADDRESS_A)

        alice_elsewhere = await _login(private, ALICE, PASSWORD, address=ADDRESS_B)
        bob_same_address = await _login(private, BOB, PASSWORD, address=ADDRESS_A)
        carol_elsewhere = await _login(private, CAROL, PASSWORD, address=ADDRESS_B)

        _assert_too_many_attempts(alice_elsewhere, f"POST /auth/login as {ALICE!r} from another address after {IDENTIFIER_LIMIT} wrong passwords")
        assert bob_same_address.status_code == 200, f"another identifier from the same address signs in: {bob_same_address.status_code} {bob_same_address.text}"
        assert carol_elsewhere.status_code == 200, f"another identifier from another address signs in: {carol_elsewhere.status_code} {carol_elsewhere.text}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_a_refused_attempt_runs_no_password_check_and_does_not_count(self, private: _Private, throttle: _Throttle, checkpw_calls: list[bytes]) -> None:
        """LT-API-05: Alice locked by ten wrong passwords at START; one attempt a second for the next ten seconds, her right password and a wrong one in turn → ten 429s, and not one ``bcrypt.checkpw`` while they last. At START plus the window the ten failures have left it — the refused attempts, had they counted, would still be in it —: the right password signs in (200)."""
        print_section("LT-API-05: a refused attempt checks no password and does not count")
        await _add_user(private.engine, ALICE)
        await _fail_logins(private, [ALICE] * IDENTIFIER_LIMIT)
        checks_before = len(checkpw_calls)
        refused = []
        for second in range(1, IDENTIFIER_LIMIT + 1):
            throttle.clock.now = START + second
            refused.append(await _login(private, ALICE, PASSWORD if second % 2 else WRONG_PASSWORD))
        checks_while_locked = len(checkpw_calls) - checks_before
        throttle.clock.now = START + WINDOW_SECONDS
        after_the_window = await _login(private, ALICE, PASSWORD)

        for second, response in enumerate(refused, start=1):
            _assert_too_many_attempts(response, f"POST /auth/login as {ALICE!r} {second} s into the lock, the {'right' if second % 2 else 'wrong'} password")
        assert checks_while_locked == 0, f"a refused attempt runs no password check — the 429 comes before bcrypt —: bcrypt.checkpw ran {checks_while_locked} time(s) for {IDENTIFIER_LIMIT} refusals"
        assert after_the_window.status_code == 200, f"refused attempts do not count: once the ten failures have left the window, the right password signs in: {after_the_window.status_code} {after_the_window.text}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_retry_after_is_the_wait(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-06: Alice locked by ten wrong passwords at START; asked 600 seconds later, the 429's ``Retry-After`` is the wait, neither more nor less: one second before it is over, still 429; once it is over, her right password signs in (200)."""
        print_section("LT-API-06: Retry-After is the wait")
        await _add_user(private.engine, ALICE)
        await _fail_logins(private, [ALICE] * IDENTIFIER_LIMIT)
        throttle.clock.now = START + ASKED_AFTER_SECONDS
        first = await _login(private, ALICE, PASSWORD)
        wait = _assert_too_many_attempts(first, f"POST /auth/login as {ALICE!r} {ASKED_AFTER_SECONDS} s into the lock")

        throttle.clock.now = START + ASKED_AFTER_SECONDS + wait - 1
        a_second_early = await _login(private, ALICE, PASSWORD)
        throttle.clock.now = START + ASKED_AFTER_SECONDS + wait
        on_time = await _login(private, ALICE, PASSWORD)

        _assert_too_many_attempts(a_second_early, f"POST /auth/login one second before the {wait} s of Retry-After are over: the header must not overstate the wait")
        assert on_time.status_code == 200, f"once the {wait} s of Retry-After are over, the right password signs in — the wait it names is enough —: {on_time.status_code} {on_time.text}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_the_right_password_resets_the_identifier(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-07: nine wrong passwords leave the right one allowed (200), and the 200 resets the identifier: ten more wrong passwords are ten 401s — without the reset the second would be a 429 —, and only then is the next attempt 429, the barrier that the limit was on all along."""
        print_section("LT-API-07: a sign-in resets the identifier")
        await _add_user(private.engine, ALICE)
        await _fail_logins(private, [ALICE] * (IDENTIFIER_LIMIT - 1))
        signed_in = await _login(private, ALICE, PASSWORD)
        after_the_reset = [await _login(private, ALICE, WRONG_PASSWORD) for _ in range(IDENTIFIER_LIMIT)]
        refused = await _login(private, ALICE, PASSWORD)

        assert signed_in.status_code == 200, f"nine wrong passwords leave the right one allowed: {signed_in.status_code} {signed_in.text}"
        statuses = [response.status_code for response in after_the_reset]
        assert statuses == [401] * IDENTIFIER_LIMIT, f"after the 200, ten wrong passwords must be ten 401s — the right password resets the identifier —: {statuses}"
        _assert_too_many_attempts(refused, f"POST /auth/login after the reset and {IDENTIFIER_LIMIT} new wrong passwords (barrier: the limit is on)")

    # red until A8a
    @pytest.mark.asyncio
    async def test_the_right_password_of_an_inactive_account_is_not_a_failure(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-08: an inactive account; nine wrong passwords, then its right password three times → three 403 ``ACCOUNT_DISABLED`` — had the first counted, the second would be an attempt past ten failures, a 429. A tenth wrong password is still a 401, and then the limit holds, 429: the nine failures counted, and the 403s neither counted nor reset the count (plan C1: only a 200 resets the identifier)."""
        print_section("LT-API-08: the 403 of an inactive account is not a failure")
        await _add_user(private.engine, ALICE, active=False)
        await _fail_logins(private, [ALICE] * (IDENTIFIER_LIMIT - 1))
        disabled = [await _login(private, ALICE, PASSWORD) for _ in range(3)]
        tenth_failure = await _login(private, ALICE, WRONG_PASSWORD)
        refused = await _login(private, ALICE, PASSWORD)

        answers = [(response.status_code, _error_code(response)) for response in disabled]
        assert answers == [(403, "ACCOUNT_DISABLED")] * 3, f"the right password of an inactive account is 403 ACCOUNT_DISABLED every time, never counted as a failure: {answers}"
        assert tenth_failure.status_code == 401, f"after nine failures and three 403s, a wrong password is still allowed — the tenth failure —: {tenth_failure.status_code} {tenth_failure.text}"
        _assert_too_many_attempts(refused, "POST /auth/login after nine failures, three 403s and a tenth failure: the 403s neither counted nor reset the count")


# ============================================================================
# 2. POST /auth/login — THE LIMIT PER ADDRESS
# ============================================================================


class TestAddressLimit:
    """Fifty failures from one address, whatever identifiers they name, lock that address and no other."""

    # red until A8a
    @pytest.mark.asyncio
    async def test_fifty_failures_from_one_address_lock_the_address(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-09: fifty wrong passwords from address A, each for an identifier of its own (one failure each, far from an identifier's ten) → the next attempt from A is 429 whoever it names: Alice with her right password, a new identifier with any. Alice from address B signs in (200)."""
        print_section("LT-API-09: fifty failures lock the address")
        await _add_user(private.engine, ALICE)
        await _fail_logins(private, _strangers(ADDRESS_LIMIT), address=ADDRESS_A)

        alice_from_the_address = await _login(private, ALICE, PASSWORD, address=ADDRESS_A)
        newcomer_from_the_address = await _login(private, "newcomer", WRONG_PASSWORD, address=ADDRESS_A)
        alice_from_another_address = await _login(private, ALICE, PASSWORD, address=ADDRESS_B)

        _assert_too_many_attempts(alice_from_the_address, f"POST /auth/login as {ALICE!r}, the right password, from an address with {ADDRESS_LIMIT} failures")
        _assert_too_many_attempts(newcomer_from_the_address, f"POST /auth/login as a new identifier from an address with {ADDRESS_LIMIT} failures")
        assert alice_from_another_address.status_code == 200, f"another address is not affected: {alice_from_another_address.status_code} {alice_from_another_address.text}"


# ============================================================================
# 3. POST /auth/change-password — THE CURRENT PASSWORD, UNDER THE SAME LIMIT
# ============================================================================


class TestChangePassword:
    """A wrong current password counts on the account's username, A–Z folded — the login's bucket — and on the address."""

    # red until A8a
    @pytest.mark.asyncio
    async def test_wrong_current_passwords_lock_the_change_and_the_login(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-10: Alice signed in; ten wrong current passwords → ten 400s; then her right current password → 429 ``TOO_MANY_ATTEMPTS`` with ``Retry-After``, and her password stays. The failures counted on her own identifier, the login's: POST /auth/login with her right password, from another address, is 429 too."""
        print_section("LT-API-10: wrong current passwords lock the change and the login")
        alice = await _signed_in(private, ALICE)
        wrong = [await _change_password(private, alice, WRONG_PASSWORD, NEW_PASSWORD) for _ in range(IDENTIFIER_LIMIT)]
        refused = await _change_password(private, alice, PASSWORD, NEW_PASSWORD)
        password_kept = await _password_is(private.engine, alice.user_id, PASSWORD)
        login_elsewhere = await _login(private, ALICE, PASSWORD, address=ADDRESS_B)

        statuses = [response.status_code for response in wrong]
        assert statuses == [400] * IDENTIFIER_LIMIT, f"a wrong current password is a 400, ten of them still allowed: {statuses}"
        _assert_too_many_attempts(refused, f"POST /auth/change-password with the right current password after {IDENTIFIER_LIMIT} wrong ones")
        assert password_kept, "a refused change must leave the password as it was"
        _assert_too_many_attempts(login_elsewhere, f"POST /auth/login as {ALICE!r} from another address after {IDENTIFIER_LIMIT} wrong current passwords: one bucket, her username A–Z folded")

    # red until A8a
    @pytest.mark.asyncio
    async def test_failed_logins_lock_the_change_of_password(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-11: Alice signed in; then ten wrong passwords at the login typed ``ALICE`` — no account is named so, but A–Z folded it is her username — from another address → her change of password, with the right current password, is 429: the login and the change count in one bucket, the other way round."""
        print_section("LT-API-11: failed logins lock the change of password")
        alice = await _signed_in(private, ALICE)
        await _fail_logins(private, [ALICE_IN_CAPITALS] * IDENTIFIER_LIMIT, address=ADDRESS_B)

        refused = await _change_password(private, alice, PASSWORD, NEW_PASSWORD)

        _assert_too_many_attempts(refused, f"POST /auth/change-password with the right current password after {IDENTIFIER_LIMIT} failed logins as {ALICE_IN_CAPITALS!r}")

    # red until A8a
    @pytest.mark.asyncio
    async def test_a_wrong_current_password_counts_on_the_address(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-12: Alice signed in from address A; forty-nine wrong passwords at the login from A, each for an identifier of its own, and one wrong current password from A make fifty failures from A → Carol's right password from A is 429; from address B she signs in (200)."""
        print_section("LT-API-12: a wrong current password counts on the address")
        alice = await _signed_in(private, ALICE, address=ADDRESS_A)
        await _add_user(private.engine, CAROL)
        await _fail_logins(private, _strangers(ADDRESS_LIMIT - 1), address=ADDRESS_A)
        wrong_current = await _change_password(private, alice, WRONG_PASSWORD, NEW_PASSWORD)
        carol_from_the_address = await _login(private, CAROL, PASSWORD, address=ADDRESS_A)
        carol_elsewhere = await _login(private, CAROL, PASSWORD, address=ADDRESS_B)

        assert wrong_current.status_code == 400, f"the fiftieth failure from the address, a wrong current password, is still allowed: {wrong_current.status_code} {wrong_current.text}"
        _assert_too_many_attempts(carol_from_the_address, f"POST /auth/login as {CAROL!r} from an address with {ADDRESS_LIMIT - 1} failed logins and one wrong current password")
        assert carol_elsewhere.status_code == 200, f"another address is not affected: {carol_elsewhere.status_code} {carol_elsewhere.text}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_a_successful_change_resets_the_accounts_count(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-13: nine wrong current passwords leave the right one allowed, and the change goes through (200, a new session cookie) and resets the account's count: with the new password current, ten wrong current passwords are ten 400s — without the reset the second would be a 429 —, and only then is the next change, with the right current password, 429: the barrier that the limit was on all along."""
        print_section("LT-API-13: a successful change resets the count")
        alice = await _signed_in(private, ALICE)
        before = [await _change_password(private, alice, WRONG_PASSWORD, NEW_PASSWORD) for _ in range(IDENTIFIER_LIMIT - 1)]
        changed = await _change_password(private, alice, PASSWORD, NEW_PASSWORD)
        after = [await _change_password(private, alice, WRONG_PASSWORD, NEWER_PASSWORD) for _ in range(IDENTIFIER_LIMIT)]
        refused = await _change_password(private, alice, NEW_PASSWORD, NEWER_PASSWORD)

        assert [response.status_code for response in before] == [400] * (IDENTIFIER_LIMIT - 1), f"nine wrong current passwords, nine 400s: {[response.status_code for response in before]}"
        assert changed.status_code == 200, f"nine wrong current passwords leave the right one allowed: the change goes through: {changed.status_code} {changed.text}"
        statuses = [response.status_code for response in after]
        assert statuses == [400] * IDENTIFIER_LIMIT, f"after the change, ten wrong current passwords must be ten 400s — a successful change resets the account's count —: {statuses}"
        _assert_too_many_attempts(refused, f"POST /auth/change-password with the right current password after the reset and {IDENTIFIER_LIMIT} new wrong ones (barrier: the limit is on)")


# ============================================================================
# 4. PUT /auth/profile — THE CURRENT PASSWORD AN EMAIL CHANGE ASKS FOR
# ============================================================================


class TestProfile:
    """An email change asks for the current password: a wrong one counts as a failed sign-in does."""

    # red until A8a
    @pytest.mark.asyncio
    async def test_wrong_current_passwords_lock_the_email_change(self, private: _Private, throttle: _Throttle) -> None:
        """LT-API-14: Alice signed in; ``PUT /auth/profile`` changing her address — a real change, so the current password is asked — with a wrong current password ten times → ten 400 ``CURRENT_PASSWORD_INVALID``; then with her right current password → 429 ``TOO_MANY_ATTEMPTS``, and her address stays. Counted on her username A–Z folded: POST /auth/login with her right password, from another address, is 429 too."""
        print_section("LT-API-14: wrong current passwords lock the email change")
        alice = await _signed_in(private, ALICE)
        wrong = [await _change_email(private, alice, WRONG_PASSWORD) for _ in range(IDENTIFIER_LIMIT)]
        refused = await _change_email(private, alice, PASSWORD)
        email_now = await _email_of(private.engine, alice.user_id)
        login_elsewhere = await _login(private, ALICE, PASSWORD, address=ADDRESS_B)

        answers = [(response.status_code, _error_code(response)) for response in wrong]
        assert answers == [(400, "CURRENT_PASSWORD_INVALID")] * IDENTIFIER_LIMIT, f"a wrong current password on an email change is 400 CURRENT_PASSWORD_INVALID, ten of them still allowed: {answers}"
        _assert_too_many_attempts(refused, f"PUT /auth/profile, an email change with the right current password after {IDENTIFIER_LIMIT} wrong ones")
        assert email_now == alice.email, f"a refused change must leave the address as it was: {email_now!r}"
        _assert_too_many_attempts(login_elsewhere, f"POST /auth/login as {ALICE!r} from another address after {IDENTIFIER_LIMIT} wrong current passwords on an email change")


# ============================================================================
# 5. LIBREFOLIO_LOGIN_LIMIT=off
# ============================================================================


class TestSwitch:
    """``off`` turns the limit off (``on``, and unset, are LT-API-01)."""

    # guard of the switch — red until A8a only at its setup: login_throttle, whose limiters it replaces, does not exist yet
    @pytest.mark.asyncio
    async def test_with_the_limit_off_no_attempt_is_refused(self, private: _Private, throttle: _Throttle, monkeypatch: pytest.MonkeyPatch) -> None:
        """LT-API-15: ``LIBREFOLIO_LOGIN_LIMIT=off`` → sixty wrong passwords for Alice from one address — past the identifier's ten and the address's fifty — are sixty 401s, never a 429; then her right password signs in (200)."""
        print_section("LT-API-15: with the limit off, sixty failures, sixty 401s")
        monkeypatch.setenv(LIMIT_VARIABLE, "off")
        await _add_user(private.engine, ALICE)
        statuses = [(await _login(private, ALICE, WRONG_PASSWORD)).status_code for _ in range(PAST_BOTH_LIMITS)]
        signed_in = await _login(private, ALICE, PASSWORD)

        assert statuses == [401] * PAST_BOTH_LIMITS, f"with the limit off every wrong password is a 401, never a 429: {dict(Counter(statuses))}"
        assert signed_in.status_code == 200, f"with the limit off the right password signs in after any number of failures: {signed_in.status_code} {signed_in.text}"
        print_success("sixty 401s, then 200")


# ============================================================================
# 6. GET /api/v1/security/checks — THE WHOLE /api/v1 ROUTER, IN-PROCESS
# ============================================================================


def _unique(prefix: str) -> str:
    """A username of its own, unique across workers: whatever the process's limiters hold, no other case ever signed in with it."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def _signed_in_for_checks(private: _Private, monkeypatch: pytest.MonkeyPatch, *, admin: bool) -> str:
    """An administrator or a member written as a row, signed in from CHECKS_ADDRESS with the limit off for that one request — these cases replace no limiter, and never count in, nor reset, the process's own —: its session cookie. The variable is then as the case set it."""
    username = _unique("checks_admin" if admin else "checks_member")
    await _add_user(private.engine, username, admin=admin)
    with monkeypatch.context() as for_the_sign_in:
        for_the_sign_in.setenv(LIMIT_VARIABLE, "off")
        response = await _login(private, username, PASSWORD, address=CHECKS_ADDRESS)
    cookies = _session_cookies(response)
    assert response.status_code == 200 and len(cookies) == 1 and cookies[0], f"setup: {username} signs in: {response.status_code} {response.text}"
    return cookies[0]


async def _checks(private: _Private, cookie: Optional[str] = None) -> httpx.Response:
    """``GET /api/v1/security/checks`` with the session ``cookie``, or none."""
    return await _request(private, "GET", SECURITY_CHECKS, address=CHECKS_ADDRESS, cookie=cookie)


def _items(response: httpx.Response, request: str) -> dict[str, dict[str, Any]]:
    """The items of the 200, by ``check_id``, each checked: a ``check_id``, a ``severity`` of SEVERITIES, an ``i18n_key``, a ``detail`` object; each check once."""
    assert response.status_code == 200, f"{request}: expected 200, got {response.status_code} {response.text}"
    body = response.json()
    items = body.get("items") if isinstance(body, dict) else None
    assert isinstance(items, list), f"{request}: the answer is an object whose items are a list: {body}"
    for item in items:
        assert isinstance(item, dict) and isinstance(item.get("check_id"), str) and item["check_id"], f"{request}: every item has a check_id: {item}"
        assert item.get("severity") in SEVERITIES, f"{request}: the severity of {item['check_id']} is one of {sorted(SEVERITIES)}: {item}"
        assert isinstance(item.get("i18n_key"), str) and item["i18n_key"], f"{request}: {item['check_id']} has the i18n key of its message: {item}"
        assert isinstance(item.get("detail"), dict), f"{request}: the detail of {item['check_id']} is an object, the parameters of its message: {item}"
    by_id = {item["check_id"]: item for item in items}
    assert len(by_id) == len(items), f"{request}: each check once: {[item['check_id'] for item in items]}"
    return by_id


def _state(item: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """An item as a check's result: its severity, its i18n key, its detail."""
    return item["severity"], item["i18n_key"], item["detail"]


def _evaluated() -> dict[str, tuple[str, str, dict[str, Any]]]:
    """Every configuration check as ``config_audit.run_config_checks()`` evaluates it now, in this process — the environment the in-process route reads —, by id."""
    return {check.check_id: (check.severity, check.i18n_key, dict(check.detail)) for check in config_audit.run_config_checks()}


def _configure_plain_smtp(monkeypatch: pytest.MonkeyPatch, *, host: str, user: str, password: str) -> None:
    """A usable SMTP configuration of this test, in clear (``LIBREFOLIO_SMTP_TLS=none``) to ``host``: nothing connects to it, a check only reads the variables."""
    for name, value in {"HOST": host, "TLS": "none", "FROM": "LibreFolio <noreply@example.com>", "USER": user, "PASSWORD": password}.items():
        monkeypatch.setenv(SMTP_PREFIX + name, value)


class TestSecurityChecks:
    """GET /api/v1/security/checks: administrators only; every check with its severity; never a secret, never a log summary."""

    # red until A8a
    @pytest.mark.asyncio
    async def test_without_a_session_it_is_401(self, private_api: _Private) -> None:
        """SC-API-01: no session cookie → 401."""
        response = await _checks(private_api)

        assert response.status_code == 401, f"GET /api/v1/security/checks without a session: expected 401, got {response.status_code} {response.text}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_a_member_is_refused_with_403(self, private_api: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """SC-API-02: a member's session → 403."""
        cookie = await _signed_in_for_checks(private_api, monkeypatch, admin=False)

        response = await _checks(private_api, cookie)

        assert response.status_code == 403, f"GET /api/v1/security/checks as a member: expected 403, got {response.status_code} {response.text}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_an_administrator_gets_every_check_as_evaluated(self, private_api: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """SC-API-03: an administrator, the limit on → 200 ``{"items": [...]}``, each item well formed and each check once: ``accounts.login_limit``, ``platform.jwt_secret`` and ``platform.plugin_secrets`` among them; every check ``run_config_checks()`` evaluates, with its severity, i18n key and detail as evaluated around the request (before or after it: the instance key file may appear meanwhile); ``platform.plugin_secrets`` as ``check_plugin_secrets`` evaluates it on the database served — no secret stored, ``ok``."""
        print_section("SC-API-03: an administrator gets every check")
        monkeypatch.setenv(LIMIT_VARIABLE, "on")
        cookie = await _signed_in_for_checks(private_api, monkeypatch, admin=True)
        before = _evaluated()
        response = await _checks(private_api, cookie)
        after = _evaluated()
        async with AsyncSession(private_api.engine) as session:
            plugin_secrets = await check_plugin_secrets(session)

        by_id = _items(response, "GET /api/v1/security/checks as an administrator")
        named = [check_id for check_id in (LOGIN_LIMIT_CHECK, JWT_SECRET_CHECK, PLUGIN_SECRETS_CHECK) if check_id not in by_id]
        assert not named, f"the checks {named} must be listed: {sorted(by_id)}"
        missing = sorted(set(before) - set(by_id))
        assert not missing, f"every check run_config_checks() evaluates must be listed — the answer filters none, ok included —: missing {missing}"
        differing = {check_id: _state(by_id[check_id]) for check_id in before if _state(by_id[check_id]) not in (before[check_id], after.get(check_id))}
        assert not differing, f"each check as run_config_checks() evaluates it: {differing}, evaluated {({check_id: before[check_id] for check_id in differing})}"
        assert _state(by_id[PLUGIN_SECRETS_CHECK]) == (plugin_secrets.severity, plugin_secrets.i18n_key, dict(plugin_secrets.detail)), f"platform.plugin_secrets as check_plugin_secrets evaluates it on the database served: {by_id[PLUGIN_SECRETS_CHECK]}"
        print_success(f"{len(by_id)} checks, each as evaluated")

    # red until A8a
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("setting", "severity"), [("on", "ok"), (None, "ok"), ("off", "warning")], ids=["on", "unset-is-on", "off"])
    async def test_the_login_limit_check_follows_the_switch(self, private_api: _Private, monkeypatch: pytest.MonkeyPatch, setting: Optional[str], severity: str) -> None:
        """SC-API-04: ``accounts.login_limit`` is ``ok`` with ``LIBREFOLIO_LOGIN_LIMIT=on`` or unset — on by default —, ``warning`` with ``off``."""
        if setting is None:
            monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
        else:
            monkeypatch.setenv(LIMIT_VARIABLE, setting)
        cookie = await _signed_in_for_checks(private_api, monkeypatch, admin=True)

        by_id = _items(await _checks(private_api, cookie), f"GET /api/v1/security/checks, the limit {setting or 'unset'}")

        item = by_id.get(LOGIN_LIMIT_CHECK)
        assert item is not None, f"{LOGIN_LIMIT_CHECK} must be listed: {sorted(by_id)}"
        assert item["severity"] == severity, f"{LOGIN_LIMIT_CHECK} with {LIMIT_VARIABLE} {setting or 'unset'} must be {severity}: {item}"

    # red until A8a
    @pytest.mark.asyncio
    async def test_no_secret_value_reaches_the_answer(self, private_api: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """SC-API-05: a ``JWT_SECRET`` of this test, too short — so ``platform.jwt_secret`` reports it, with its source and length —, and the SMTP password of a usable configuration of this test → neither value anywhere in the answer. Barriers: ``platform.jwt_secret`` is not ``ok`` (the check read this secret), ``email.smtp`` is the usable configuration's (it read this password)."""
        print_section("SC-API-05: no secret value in the answer")
        jwt_secret = f"zq-jwt-{uuid.uuid4().hex[:16]}"
        smtp_password = f"zq-smtp-password-{uuid.uuid4().hex}"
        monkeypatch.setenv("JWT_SECRET", jwt_secret)
        _configure_plain_smtp(monkeypatch, host=f"smtp-{uuid.uuid4().hex[:12]}.zq-plain.example.com", user=f"zq-user-{uuid.uuid4().hex[:12]}", password=smtp_password)
        cookie = await _signed_in_for_checks(private_api, monkeypatch, admin=True)

        response = await _checks(private_api, cookie)

        by_id = _items(response, "GET /api/v1/security/checks with a short JWT_SECRET and an SMTP password")
        jwt_check = by_id.get(JWT_SECRET_CHECK, {})
        assert jwt_check.get("severity") in ("warning", "error"), f"barrier: {JWT_SECRET_CHECK} must report this test's secret, {len(jwt_secret)} characters, as too short: {jwt_check}"
        smtp_check = by_id.get(SMTP_CHECK, {})
        assert (smtp_check.get("severity"), smtp_check.get("i18n_key")) == ("ok", "email.checks.smtp.ok"), f"barrier: {SMTP_CHECK} must have read this test's usable configuration, its password included: {smtp_check}"
        leaked = [name for name, value in (("JWT_SECRET", jwt_secret), ("LIBREFOLIO_SMTP_PASSWORD", smtp_password)) if value in response.text]
        assert not leaked, f"no secret value may reach the answer: the value of {leaked} is in it"
        print_success("neither JWT_SECRET nor the SMTP password in the answer")

    # red until A8a
    @pytest.mark.asyncio
    async def test_the_smtp_configuration_stays_out_of_the_answer(self, private_api: _Private, monkeypatch: pytest.MonkeyPatch) -> None:
        """SC-API-06 (F04): SMTP in clear to a server outside the local network, with a user of this test — ``email.smtp_encryption`` warns, and its log summary names the server — → neither the server nor the user anywhere in the answer: an item carries a check's i18n key and parameters, never its log summary, as ``GET /email/status`` does. Barrier: ``email.smtp_encryption`` is that warning."""
        print_section("SC-API-06: the SMTP configuration stays out of the answer")
        host = f"smtp-{uuid.uuid4().hex[:12]}.zq-plain.example.com"
        user = f"zq-user-{uuid.uuid4().hex[:12]}"
        _configure_plain_smtp(monkeypatch, host=host, user=user, password=f"zq-smtp-password-{uuid.uuid4().hex}")
        cookie = await _signed_in_for_checks(private_api, monkeypatch, admin=True)

        response = await _checks(private_api, cookie)

        by_id = _items(response, "GET /api/v1/security/checks with SMTP in clear to an outside server")
        encryption = by_id.get(SMTP_ENCRYPTION_CHECK, {})
        assert encryption.get("severity") == "warning", f"barrier: {SMTP_ENCRYPTION_CHECK} must warn of SMTP in clear to {host}, the warning whose log summary names it: {encryption}"
        shown = [name for name, value in (("the SMTP server", host), ("the SMTP user", user)) if value in response.text]
        assert not shown, f"the SMTP configuration is never returned (F04): {shown} in the answer — an item is the check's i18n key and detail, never its log summary"
        print_success("neither the SMTP server nor its user in the answer")

    # red until H5-4
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("state", "severity", "key"), [(None, "ok", "ok"), ("pending", "info", "pending"), ("blocked", "warning", "blocked")], ids=["none-ok", "pending-info", "blocked-warning"])
    async def test_the_owner_email_change_check_follows_the_startup_state(self, private_api: _Private, monkeypatch: pytest.MonkeyPatch, state: Optional[str], severity: str, key: str) -> None:
        """SC-API-OE: ``accounts.owner_email_change`` (H5-4) is listed once, well formed (a severity, an i18n key, a detail object), with the severity and key of ``instance_owner.startup_change_state()`` — patched here, the app runs in this process —: ``ok`` / ``auth.checks.ownerEmailChange.ok`` for None, ``info`` / ``.pending``, ``warning`` / ``.blocked``; its item holds no ``@``."""
        owner_module = importlib.import_module("backend.app.services.accounts.instance_owner")
        monkeypatch.setattr(owner_module, "startup_change_state", lambda: state)
        cookie = await _signed_in_for_checks(private_api, monkeypatch, admin=True)

        by_id = _items(await _checks(private_api, cookie), f"GET /api/v1/security/checks, the owner's email change {state!r}")

        item = by_id.get("accounts.owner_email_change")
        assert item is not None, f"red until H5-4: accounts.owner_email_change must be listed: {sorted(by_id)}"
        assert isinstance(item.get("detail"), dict) and item.get("severity") in SEVERITIES, f"well formed: {item}"
        assert (item["severity"], item["i18n_key"]) == (severity, f"auth.checks.ownerEmailChange.{key}"), f"state {state!r}: expected {severity} / auth.checks.ownerEmailChange.{key}: {item}"
        assert "@" not in repr(item), f"no address in the item: {item}"


# ============================================================================
# 7. POST /email/verification/resend — THE SIGN-IN'S CREDENTIALS, UNDER THE SIGN-IN'S LIMIT
# ============================================================================


@pytest.fixture
def resend_limit(throttle: _Throttle, monkeypatch: pytest.MonkeyPatch) -> SlidingWindowLimiter:
    """E's ``delivery.ADDRESS_BUDGET`` — every resend hits it first, before the sign-in's limit and the password — replaced by a fresh limiter of the shipped size (its limit and window, never its counts) on the throttle's fake clock: the process's own is neither counted nor consulted. E's route reads it through the module at request time."""
    shipped = delivery.ADDRESS_BUDGET
    assert isinstance(shipped, SlidingWindowLimiter), f"delivery.ADDRESS_BUDGET must be E's SlidingWindowLimiter: {shipped!r}"
    limiter = SlidingWindowLimiter(shipped.limit, shipped.window_seconds, clock=throttle.clock)
    monkeypatch.setattr(delivery, "ADDRESS_BUDGET", limiter)
    return limiter


async def _resend(private: _Private, identifier: str, password: str, *, address: tuple[str, int]) -> httpx.Response:
    """``POST /email/verification/resend`` with the sign-in's credentials — ``identifier`` in its ``username`` field, as at sign-in — from ``address``."""
    return await _request(private, "POST", RESEND, address=address, json={"username": identifier, "password": password})


def _resend_addresses(count: int) -> list[tuple[str, int]]:
    """``count`` documentation addresses (192.0.2.101 onwards), each different and none another constant names: one resend from each keeps E's limit per address out of the way."""
    return [(f"192.0.2.{101 + number}", 42101 + number) for number in range(count)]


async def _fail_resends(private: _Private, identifier: str, addresses: Iterable[tuple[str, int]]) -> None:
    """A wrong password at the resend for ``identifier``, once from each of ``addresses``, in order. It ends on its promise: each one answered 401, a failure the limits still allowed."""
    for number, address in enumerate(addresses, start=1):
        response = await _resend(private, identifier, WRONG_PASSWORD, address=address)
        assert response.status_code == 401, f"wrong password at the resend #{number} ({identifier!r} from {address[0]}): expected 401, a failure still allowed — got {response.status_code} {response.text}"


def _counted(throttle: _Throttle, identifier: str, address: tuple[str, int]) -> tuple[int, int]:
    """The failures the sign-in's two limiters hold now for ``identifier`` — under its key, ``login_throttle.identifier_key`` — and for ``address`` — an IPv4 address is its own key."""
    return throttle.by_identifier.count(_login_throttle().identifier_key(identifier)), throttle.by_address.count(address[0])


def _assert_resend_refused(response: httpx.Response, request: str, wait: int) -> None:
    """``response`` is the resend's answer to a limit: 429, ``detail.error_code`` ``EMAIL_RATE_LIMITED`` (the code, never the wording), ``detail.retry_after`` ``wait`` and one ``Retry-After`` of the same whole seconds, no session cookie."""
    assert response.status_code == 429, f"{request}: expected 429 {EMAIL_RATE_LIMITED}, got {response.status_code} {response.text}"
    assert _error_code(response) == EMAIL_RATE_LIMITED, f"{request}: the 429 carries detail.error_code {EMAIL_RATE_LIMITED}, the resend's answer to all its limits: {response.text}"
    retry_after = response.json()["detail"].get("retry_after")
    assert retry_after == wait, f"{request}: detail.retry_after must be the wait, {wait} s on the fake clock: {retry_after!r}"
    assert _retry_after(response) == wait, f"{request}: one Retry-After of the same whole seconds as detail.retry_after, {wait}: {response.headers.get_list('retry-after')}"
    assert _session_cookies(response) == [], f"{request}: a refusal sets no session cookie: Set-Cookie {response.headers.get_list('set-cookie')}"


class TestResend:
    """POST /email/verification/resend checks the sign-in's credentials: it counts, is refused and forgets in the sign-in's two buckets, both ways."""

    # red until A8a (resend)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("typed", "signs_in_as"), [(ALICE, ALICE), (NOBODY, NOBODY), (ALICE_EMAIL_IN_CAPITALS, ALICE_EMAIL)], ids=["an-account", "no-account", "its-address-in-capitals"])
    async def test_wrong_passwords_at_the_resend_lock_the_sign_in(self, private_api: _Private, throttle: _Throttle, resend_limit: SlidingWindowLimiter, typed: str, signs_in_as: str) -> None:
        """LT-API-16: ten wrong passwords at the resend typed ``typed``, each from an address of its own → the sign-in typed ``signs_in_as`` with Alice's right password, from an address none of them came from, → 429 ``TOO_MANY_ATTEMPTS``: the resend's failures count on the sign-in's identifier. ``alice``, her username; ``nobody_here``, which no account matches — the same failure, or the resend would tell which accounts exist: its eleventh attempt, a sign-in, is refused alike —; ``ALICE@EXAMPLE.COM``, her address in capitals — an account matches it — and then the sign-in typed ``alice@example.com``: the identifier as typed, A–Z folded, not the username of the account it finds."""
        print_section(f"LT-API-16: wrong passwords at the resend lock the sign-in ({typed!r})")
        await _add_user(private_api.engine, ALICE)
        await _fail_resends(private_api, typed, _resend_addresses(IDENTIFIER_LIMIT))

        refused = await _login(private_api, signs_in_as, PASSWORD, address=ADDRESS_A)

        _assert_too_many_attempts(refused, f"POST /auth/login as {signs_in_as!r} with Alice's right password, after {IDENTIFIER_LIMIT} wrong passwords at the resend as {typed!r}")
        print_success("the resend's failures lock the sign-in")

    # red until A8a (resend)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("lock", "failed_sign_ins", "resend_from"), [("identifier", [ALICE] * IDENTIFIER_LIMIT, ADDRESS_B), ("address", _strangers(ADDRESS_LIMIT), ADDRESS_A)], ids=["identifier", "address"])
    async def test_a_locked_sign_in_refuses_the_resend_before_the_password(self, private_api: _Private, throttle: _Throttle, resend_limit: SlidingWindowLimiter, checkpw_calls: list[bytes], lock: str, failed_sign_ins: list[str], resend_from: tuple[str, int]) -> None:
        """LT-API-17: wrong passwords at the sign-in from address A at START lock Alice — ten for her (``identifier``: her resend then comes from address B, where nothing failed), or fifty for fifty other identifiers (``address``: her resend comes from A) —; 600 seconds later her resend, with her right password and with a wrong one, → 429 ``EMAIL_RATE_LIMITED`` both, one body, ``detail.retry_after`` and ``Retry-After`` the wait — 300 s on the fake clock —, and not one ``bcrypt.checkpw``: refused before the password, the answer cannot tell the right one. The two refusals counted nothing, for her identifier or for the address they came from — barrier: the limiters ``login_throttle`` holds, read before and after —; once the wait is over, her right password signs in from there (200)."""
        print_section(f"LT-API-17: a locked sign-in refuses the resend before the password (by the {lock})")
        await _add_user(private_api.engine, ALICE)
        await _fail_logins(private_api, failed_sign_ins, address=ADDRESS_A)
        throttle.clock.now = START + ASKED_AFTER_SECONDS
        counted_before = _counted(throttle, ALICE, resend_from)
        checks_before = len(checkpw_calls)
        right = await _resend(private_api, ALICE, PASSWORD, address=resend_from)
        wrong = await _resend(private_api, ALICE, WRONG_PASSWORD, address=resend_from)
        checks = len(checkpw_calls) - checks_before
        counted_after = _counted(throttle, ALICE, resend_from)
        throttle.clock.now = START + WINDOW_SECONDS
        after_the_wait = await _login(private_api, ALICE, PASSWORD, address=resend_from)

        wait = WINDOW_SECONDS - ASKED_AFTER_SECONDS
        _assert_resend_refused(right, f"POST /email/verification/resend as {ALICE!r} with the right password from {resend_from[0]}, {ASKED_AFTER_SECONDS} s into the lock", wait)
        _assert_resend_refused(wrong, f"POST /email/verification/resend as {ALICE!r} with a wrong password from {resend_from[0]}, {ASKED_AFTER_SECONDS} s into the lock", wait)
        assert wrong.json() == right.json(), f"refused before the password: one answer for the right password and a wrong one: {wrong.json()} vs {right.json()}"
        assert checks == 0, f"the 429 comes before bcrypt: bcrypt.checkpw ran {checks} time(s) for the two refused resends"
        assert counted_after == counted_before, f"a refused resend is not counted: failures (identifier {ALICE!r}, address {resend_from[0]}) {counted_before} before the two refusals, {counted_after} after"
        assert after_the_wait.status_code == 200, f"once the {wait} s are over, the right password signs in from {resend_from[0]} — the wait named is enough, and the refusals did not push it away —: {after_the_wait.status_code} {after_the_wait.text}"
        print_success(f"two 429 {EMAIL_RATE_LIMITED}, {wait} s, no password check, nothing counted; then 200")

    # red until A8a (resend)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("active", "answer"), [(True, (409, "EMAIL_VERIFICATION_NOT_NEEDED")), (False, (403, "ACCOUNT_DISABLED"))], ids=["active", "deactivated"])
    async def test_the_right_password_at_the_resend_resets_the_identifier(self, private_api: _Private, throttle: _Throttle, resend_limit: SlidingWindowLimiter, active: bool, answer: tuple[int, str]) -> None:
        """LT-API-18: Alice active, or deactivated by an administrator (no link to wait for); nine wrong passwords at the sign-in, then her resend with the right password → 409 ``EMAIL_VERIFICATION_NOT_NEEDED``, or 403 ``ACCOUNT_DISABLED``, and the right password forgets the nine whatever the answer — as a change of password does, unlike the sign-in's own 403 (LT-API-08) —: ten more wrong passwords are ten 401s — without the reset the second would be a 429 —, and only then is the next attempt 429, the barrier that the limit was on all along. Every attempt typed with her address, ``alice@example.com``: what the right password forgets is the identifier as typed, the sign-in's key, not the username of the account it finds."""
        print_section(f"LT-API-18: the right password at the resend resets the identifier ({'active' if active else 'deactivated'})")
        await _add_user(private_api.engine, ALICE, active=active)
        await _fail_logins(private_api, [ALICE_EMAIL] * (IDENTIFIER_LIMIT - 1))
        resent = await _resend(private_api, ALICE_EMAIL, PASSWORD, address=ADDRESS_A)
        after_the_reset = [await _login(private_api, ALICE_EMAIL, WRONG_PASSWORD) for _ in range(IDENTIFIER_LIMIT)]
        refused = await _login(private_api, ALICE_EMAIL, PASSWORD)

        assert (resent.status_code, _error_code(resent)) == answer, f"nine wrong passwords leave the right one allowed at the resend, which answers {answer} for this account: {resent.status_code} {resent.text}"
        statuses = [response.status_code for response in after_the_reset]
        assert statuses == [401] * IDENTIFIER_LIMIT, f"after the resend's {answer[0]}, ten wrong passwords must be ten 401s — the right password at the resend resets the identifier as typed, {ALICE_EMAIL!r} —: {statuses}"
        _assert_too_many_attempts(refused, f"POST /auth/login as {ALICE_EMAIL!r} after the reset and {IDENTIFIER_LIMIT} new wrong passwords (barrier: the limit is on)")

    # red until A8a (resend)
    @pytest.mark.asyncio
    async def test_a_wrong_password_at_the_resend_counts_on_the_address(self, private_api: _Private, throttle: _Throttle, resend_limit: SlidingWindowLimiter) -> None:
        """LT-API-19: forty-nine wrong passwords at the sign-in from address A, each for an identifier of its own, and Alice's resend from A with a wrong password make fifty failures from A → Carol's right password from A is 429; from address B she signs in (200)."""
        print_section("LT-API-19: a wrong password at the resend counts on the address")
        await _add_user(private_api.engine, ALICE)
        await _add_user(private_api.engine, CAROL)
        await _fail_logins(private_api, _strangers(ADDRESS_LIMIT - 1), address=ADDRESS_A)
        await _fail_resends(private_api, ALICE, [ADDRESS_A])
        carol_from_the_address = await _login(private_api, CAROL, PASSWORD, address=ADDRESS_A)
        carol_elsewhere = await _login(private_api, CAROL, PASSWORD, address=ADDRESS_B)

        _assert_too_many_attempts(carol_from_the_address, f"POST /auth/login as {CAROL!r} from an address with {ADDRESS_LIMIT - 1} failed sign-ins and one wrong password at the resend")
        assert carol_elsewhere.status_code == 200, f"another address is not affected: {carol_elsewhere.status_code} {carol_elsewhere.text}"


# ============================================================================
# 8. BEHIND A LOCAL PROXY LIBREFOLIO DOES NOT TRUST (N70): NO LOCK UNDER ITS ADDRESS, THE IDENTIFIER'S KEPT
# ============================================================================

CLIENT_ADDRESS_MODULE = "backend.app.services.platform.client_address"
CLIENT_IP_HEADER_VARIABLE = "LIBREFOLIO_CLIENT_IP_HEADER"
#: uvicorn's own variable: the peers whose X-Forwarded-For it applies — 127.0.0.1 when unset.
TRUSTED_PROXIES_VARIABLE = "FORWARDED_ALLOW_IPS"

#: A header line as a proxy adds it: its name, its value.
Header = tuple[str, str]
#: The proxy of the cases that vary the place, not the proxy: a reverse proxy on the local network (``lan``), and the header it forwards.
LOCAL_PROXY = ("10.0.0.7", 123)
XFF: Header = ("X-Forwarded-For", "203.0.113.50")
#: Two peers ``classify_ip`` calls ``public`` — no documentation range is a local one of N70 —: each is the client, whatever it forwards.
PUBLIC_PEER = ("198.51.100.20", 41020)
OTHER_PUBLIC_PEER = ("198.51.100.21", 41021)

#: Proxies ``classify_ip`` calls local — ``lan``, ``loopback``, ``vpn`` (the CGNAT range) —, each forwarding a header nothing applies, naming a visitor of its own (RFC 5737): the three headers from 10.0.0.7, one from each of the others.
THROUGH_A_LOCAL_PROXY = [
    pytest.param(LOCAL_PROXY, XFF, id="lan-10.0.0.7-x-forwarded-for"),
    pytest.param(LOCAL_PROXY, ("Forwarded", "for=203.0.113.51"), id="lan-10.0.0.7-forwarded"),
    pytest.param(LOCAL_PROXY, ("X-Real-IP", "203.0.113.52"), id="lan-10.0.0.7-x-real-ip"),
    pytest.param(("192.168.1.20", 124), ("X-Forwarded-For", "203.0.113.53"), id="lan-192.168.1.20-x-forwarded-for"),
    pytest.param(("127.0.0.1", 125), ("X-Real-IP", "203.0.113.54"), id="loopback-127.0.0.1-x-real-ip"),
    pytest.param(("100.100.1.5", 126), ("Forwarded", "for=203.0.113.55"), id="vpn-100.100.1.5-forwarded"),
]
#: The three forwarding headers of N70, as a public peer may send them.
FORWARDING_HEADERS = [
    pytest.param(XFF, id="x-forwarded-for"),
    pytest.param(("Forwarded", "for=203.0.113.51"), id="forwarded"),
    pytest.param(("X-Real-IP", "203.0.113.52"), id="x-real-ip"),
]
#: Local peers forwarding nothing: clients like any other.
LOCAL_PEERS = [
    pytest.param(LOCAL_PROXY, id="lan-10.0.0.7"),
    pytest.param(("127.0.0.1", 125), id="loopback-127.0.0.1"),
]


def _start_client_address_over() -> None:
    """Workstream H's module reads its settings once per process — ``LIBREFOLIO_CLIENT_IP_HEADER`` among them —: every cached function of its own cleared, so the next request reads the environment as it is then. And the forwarding headers it noted from untrusted peers (``_untrusted_forwarding``, which the configuration check ``platform.client_address`` reports, and which has no reset function, decision N58) emptied in place: a case of this section leaves no note for the next test of the process."""
    module = importlib.import_module(CLIENT_ADDRESS_MODULE)
    for value in list(vars(module).values()):
        if getattr(value, "__module__", None) == module.__name__ and callable(getattr(value, "cache_clear", None)):
            value.cache_clear()
    for seen in module._untrusted_forwarding.values():
        seen.clear()


@pytest.fixture
def untrusted_proxy(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """N70's setting, whatever the lane exported: ``LIBREFOLIO_CLIENT_IP_HEADER`` unset — no header gives the address, X-Real-IP included — and ``FORWARDED_ALLOW_IPS`` unset — uvicorn's default —, the reads H's module caches started over before and after. Premise: a request from the proxy carrying X-Real-IP has the proxy's address."""
    monkeypatch.delenv(CLIENT_IP_HEADER_VARIABLE, raising=False)
    monkeypatch.delenv(TRUSTED_PROXIES_VARIABLE, raising=False)
    _start_client_address_over()
    probe = Request({"type": "http", "method": "POST", "path": LOGIN, "headers": [(b"x-real-ip", b"203.0.113.52")], "client": LOCAL_PROXY, "query_string": b""})
    seen = client_address(probe)
    assert seen == LOCAL_PROXY[0], f"premise: with {CLIENT_IP_HEADER_VARIABLE} unset, a request from {LOCAL_PROXY[0]} carrying X-Real-IP has {LOCAL_PROXY[0]}'s address, not {seen!r}: a header that gives the address is applied, and N70 is not about it"
    yield
    _start_client_address_over()


def _through(forwarded: Optional[Header]) -> str:
    """How a message names what a request forwards: `` forwarding <header>``, or nothing."""
    return f" forwarding {forwarded[0]}" if forwarded else ""


async def _send(private: _Private, method: str, path: str, *, peer: tuple[str, int], forwarded: Optional[Header] = None, cookie: Optional[str] = None, json: Any = None) -> httpx.Response:
    """One request from a client of its own at ``peer`` (the ASGI ``client``), carrying ``forwarded`` when given — as a proxy adds it — and the session cookie when given."""
    headers = {forwarded[0]: forwarded[1]} if forwarded else {}
    if cookie:
        headers["Cookie"] = f"{COOKIE}={cookie}"
    transport = httpx.ASGITransport(app=private.app, client=peer)
    async with httpx.AsyncClient(transport=transport, base_url=BASE_URL, timeout=TIMEOUT) as client:
        return await client.request(method, path, json=json, headers=headers)


async def _login_from(private: _Private, identifier: str, password: str, *, peer: tuple[str, int], forwarded: Optional[Header] = None) -> httpx.Response:
    """``POST /auth/login`` with ``identifier`` and ``password`` from ``peer``, forwarding ``forwarded`` when given."""
    return await _send(private, "POST", LOGIN, peer=peer, forwarded=forwarded, json={"username": identifier, "password": password})


async def _fail_logins_from(private: _Private, identifiers: Iterable[str], *, peer: tuple[str, int], forwarded: Optional[Header] = None) -> None:
    """A wrong password for each of ``identifiers``, in order, from ``peer``, forwarding ``forwarded`` when given. It ends on its promise: each one answered 401, a failure the limit still allowed."""
    for number, identifier in enumerate(identifiers, start=1):
        response = await _login_from(private, identifier, WRONG_PASSWORD, peer=peer, forwarded=forwarded)
        assert response.status_code == 401, f"wrong password #{number} ({identifier!r} from {peer[0]}{_through(forwarded)}): expected 401, a failure still allowed — got {response.status_code} {response.text}"


def _answer(response: httpx.Response) -> tuple[int, Optional[str]]:
    """What a place answered: the status, and ``detail.error_code`` when there is one."""
    return response.status_code, _error_code(response)


@dataclass(frozen=True)
class _Place:
    """One of the three places of ``auth.py`` that check a password, as Alice's browser reaches it: the request, and the answer — status and ``detail.error_code`` — to a wrong password and to the right one."""

    name: str
    method: str
    path: str
    body: Callable[[str], dict[str, Any]]
    wrong: tuple[int, Optional[str]]
    right: tuple[int, Optional[str]]

    async def attempt(self, private: _Private, alice: _Browser, password: str, *, forwarded: Optional[Header] = None) -> httpx.Response:
        """``password`` at this place from Alice's browser — its address, its session cookie —, forwarding ``forwarded`` when given."""
        return await _send(private, self.method, self.path, peer=alice.address, forwarded=forwarded, cookie=alice.cookie, json=self.body(password))


#: The three places of ``auth.py`` that give the throttle an address (N70): the sign-in, the change of password, the change of email address.
PASSWORD_PLACES = [
    pytest.param(_Place("POST /auth/login", "POST", LOGIN, lambda password: {"username": ALICE, "password": password}, wrong=(401, None), right=(200, None)), id="sign-in"),
    pytest.param(_Place("POST /auth/change-password", "POST", CHANGE_PASSWORD, lambda password: {"current_password": password, "new_password": NEW_PASSWORD}, wrong=(400, None), right=(200, None)), id="change-of-password"),
    pytest.param(_Place("PUT /auth/profile changing the email", "PUT", PROFILE, lambda password: {"email": NEW_EMAIL, "current_password": password}, wrong=(400, "CURRENT_PASSWORD_INVALID"), right=(200, None)), id="change-of-email"),
]


class TestUntrustedLocalProxy:
    """N70: what a local proxy LibreFolio does not trust forwards locks nothing under the proxy's address, and the identifier's limit holds; a public peer, and a local one forwarding nothing, are limited by their address as before."""

    # red until A8a (N70)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("proxy", "forwarded"), THROUGH_A_LOCAL_PROXY)
    async def test_fifty_failures_through_the_proxy_lock_nobody_else_out(self, private: _Private, throttle: _Throttle, untrusted_proxy: None, proxy: tuple[str, int], forwarded: Header) -> None:
        """LT-API-20: fifty wrong passwords through a local proxy LibreFolio does not trust — from ``proxy``, each request forwarding ``forwarded``, each for an identifier of its own — → Carol's right password through it → 200, not the shared address's lockout (today: 429 ``TOO_MANY_ATTEMPTS``). Barrier: the fifty failures counted, each on its identifier, none on an address."""
        print_section(f"LT-API-20: fifty failures through {proxy[0]}, forwarding {forwarded[0]}")
        await _add_user(private.engine, CAROL)
        await _fail_logins_from(private, _strangers(ADDRESS_LIMIT), peer=proxy, forwarded=forwarded)

        carol = await _login_from(private, CAROL, PASSWORD, peer=proxy, forwarded=forwarded)

        assert carol.status_code == 200, f"POST /auth/login as {CAROL!r}, right password, from {proxy[0]}{_through(forwarded)}, after {ADDRESS_LIMIT} failures through it: expected 200 — every visitor of the proxy has its address, so no limit per address —, got {carol.status_code} {carol.text}"
        counted = (len(throttle.by_identifier), len(throttle.by_address))
        assert counted == (ADDRESS_LIMIT, 0), f"each failure through the proxy counts on its identifier and on no address: keys counted (identifier, address) {counted}"
        print_success("fifty failures through the proxy, and Carol signs in")

    # guard (N70): green today, and to stay green — the identifier's limit holds through the proxy
    @pytest.mark.asyncio
    @pytest.mark.parametrize(("proxy", "forwarded"), THROUGH_A_LOCAL_PROXY)
    async def test_the_identifier_limit_holds_through_the_proxy(self, private: _Private, throttle: _Throttle, untrusted_proxy: None, proxy: tuple[str, int], forwarded: Header) -> None:
        """LT-API-21: ten wrong passwords for Alice through the local proxy → her eleventh attempt through it, her right password, → 429 ``TOO_MANY_ATTEMPTS`` with ``Retry-After``, no session cookie; Bob's right password through it → 200: the lock is Alice's, not the proxy's."""
        print_section(f"LT-API-21: the identifier's limit through {proxy[0]}, forwarding {forwarded[0]}")
        await _add_user(private.engine, ALICE)
        await _add_user(private.engine, BOB)
        await _fail_logins_from(private, [ALICE] * IDENTIFIER_LIMIT, peer=proxy, forwarded=forwarded)

        alice = await _login_from(private, ALICE, PASSWORD, peer=proxy, forwarded=forwarded)
        bob = await _login_from(private, BOB, PASSWORD, peer=proxy, forwarded=forwarded)

        _assert_too_many_attempts(alice, f"POST /auth/login as {ALICE!r}, her right password, from {proxy[0]}{_through(forwarded)}, after {IDENTIFIER_LIMIT} wrong passwords through it: the identifier's limit holds behind the proxy")
        assert bob.status_code == 200, f"another identifier through the same proxy signs in: {bob.status_code} {bob.text}"
        print_success("Alice locked, Bob signs in")

    # guard (N70): green today, and to stay green — a public peer's forwarding header changes nothing
    @pytest.mark.asyncio
    @pytest.mark.parametrize("forwarded", FORWARDING_HEADERS)
    async def test_a_public_peer_is_the_client_whatever_it_forwards(self, private: _Private, throttle: _Throttle, untrusted_proxy: None, forwarded: Header) -> None:
        """LT-API-22: fifty wrong passwords from a public peer, each request forwarding ``forwarded``, each for an identifier of its own → Carol's right password from it, forwarding the same, → 429 ``TOO_MANY_ATTEMPTS``: the fifty counted on the peer's address, as without the header. Nor is the header the key: from another public peer forwarding the same, Carol signs in (200)."""
        print_section(f"LT-API-22: a public peer forwarding {forwarded[0]}")
        await _add_user(private.engine, CAROL)
        await _fail_logins_from(private, _strangers(ADDRESS_LIMIT), peer=PUBLIC_PEER, forwarded=forwarded)

        locked = await _login_from(private, CAROL, PASSWORD, peer=PUBLIC_PEER, forwarded=forwarded)
        elsewhere = await _login_from(private, CAROL, PASSWORD, peer=OTHER_PUBLIC_PEER, forwarded=forwarded)

        _assert_too_many_attempts(locked, f"POST /auth/login as {CAROL!r} from the public peer {PUBLIC_PEER[0]}{_through(forwarded)}, after {ADDRESS_LIMIT} wrong passwords from it: a public peer is the client, whatever it forwards")
        assert elsewhere.status_code == 200, f"the forwarded header is not the key: from another public peer forwarding the same, Carol signs in — got {elsewhere.status_code} {elsewhere.text}"
        counted = (len(throttle.by_address), throttle.by_address.count(PUBLIC_PEER[0]))
        assert counted == (1, ADDRESS_LIMIT), f"the fifty failures count on the public peer's address, under one key: (address keys, count) {counted}"
        print_success("the public peer locked, its header ignored")

    # guard (N70): green today, and to stay green — a local peer forwarding nothing is a client
    @pytest.mark.asyncio
    @pytest.mark.parametrize("peer", LOCAL_PEERS)
    async def test_a_local_peer_forwarding_nothing_is_limited_by_its_address(self, private: _Private, throttle: _Throttle, untrusted_proxy: None, peer: tuple[str, int]) -> None:
        """LT-API-23: fifty wrong passwords from a local peer whose requests forward nothing, each for an identifier of its own → Carol's right password from it → 429 ``TOO_MANY_ATTEMPTS``: a local client is still a client, limited by its address."""
        print_section(f"LT-API-23: {peer[0]} forwarding nothing")
        await _add_user(private.engine, CAROL)
        await _fail_logins_from(private, _strangers(ADDRESS_LIMIT), peer=peer)

        locked = await _login_from(private, CAROL, PASSWORD, peer=peer)

        _assert_too_many_attempts(locked, f"POST /auth/login as {CAROL!r} from the local peer {peer[0]}, forwarding nothing, after {ADDRESS_LIMIT} wrong passwords from it: a local client is still a client")
        print_success("the local client locked by its address")

    # red until A8a (N70)
    @pytest.mark.asyncio
    @pytest.mark.parametrize("place", PASSWORD_PLACES)
    async def test_a_wrong_password_through_the_proxy_counts_on_the_identifier_only(self, private: _Private, throttle: _Throttle, untrusted_proxy: None, place: _Place) -> None:
        """LT-API-24: Alice signed in from the local proxy's address, where forty-nine failures are then recorded — written in its limiter, as forty-nine wrong passwords from it forwarding nothing count there (LT-API-23) —; her wrong password at ``place`` through the proxy (``X-Forwarded-For``) gets the place's own answer, and counts on her identifier and on no address: Carol's right password from the proxy's address, forwarding nothing, → 200 — a fiftieth failure there would refuse her —; the address holds forty-nine, Alice one. Each place of ``auth.py`` that checks a password: the sign-in, the change of password, the change of email address."""
        print_section(f"LT-API-24: a wrong password through the proxy at {place.name}")
        alice = await _signed_in(private, ALICE, address=LOCAL_PROXY)
        await _add_user(private.engine, CAROL)
        for _ in range(ADDRESS_LIMIT - 1):
            throttle.by_address.hit(LOCAL_PROXY[0])
        wrong = await place.attempt(private, alice, WRONG_PASSWORD, forwarded=XFF)
        carol = await _login_from(private, CAROL, PASSWORD, peer=LOCAL_PROXY)

        assert _answer(wrong) == place.wrong, f"{place.name}, a wrong password through the proxy: expected {place.wrong}, the place's answer to a wrong password — got {wrong.status_code} {wrong.text}"
        assert carol.status_code == 200, f"POST /auth/login as {CAROL!r}, right password, from {LOCAL_PROXY[0]} forwarding nothing, after {ADDRESS_LIMIT - 1} failures there and one through the proxy at {place.name}: expected 200, got {carol.status_code} {carol.text}"
        counted = (*_counted(throttle, ALICE, LOCAL_PROXY), len(throttle.by_address))
        assert counted == (1, ADDRESS_LIMIT - 1, 1), f"the failure through the proxy counts on Alice's identifier and on no address: (Alice, the proxy's address, address keys) {counted}"
        print_success("counted on Alice only")

    # red until A8a (N70)
    @pytest.mark.asyncio
    @pytest.mark.parametrize("place", PASSWORD_PLACES)
    async def test_an_address_its_own_failures_locked_lets_the_proxy_through(self, private: _Private, throttle: _Throttle, untrusted_proxy: None, place: _Place) -> None:
        """LT-API-25: Alice signed in from the local proxy's address, where fifty failures are then recorded — written in its limiter —: her right password at ``place`` from it, forwarding nothing, → 429 ``TOO_MANY_ATTEMPTS``, the barrier that the place reads that address; the same request through the proxy (``X-Forwarded-For``) → 200: decided per request, the limit per address skipped for what the proxy forwards. Each place of ``auth.py`` that checks a password."""
        print_section(f"LT-API-25: a locked address and its proxy, at {place.name}")
        alice = await _signed_in(private, ALICE, address=LOCAL_PROXY)
        for _ in range(ADDRESS_LIMIT):
            throttle.by_address.hit(LOCAL_PROXY[0])
        direct = await place.attempt(private, alice, PASSWORD)
        through_the_proxy = await place.attempt(private, alice, PASSWORD, forwarded=XFF)

        _assert_too_many_attempts(direct, f"{place.name}, the right password from {LOCAL_PROXY[0]} forwarding nothing, the address holding {ADDRESS_LIMIT} failures (barrier: the place reads that address)")
        assert _answer(through_the_proxy) == place.right, f"{place.name}, the right password through the proxy, its address locked by its own failures: expected {place.right} — no limit per address for what it forwards —, got {through_the_proxy.status_code} {through_the_proxy.text}"
        print_success("refused direct, let through the proxy")
