"""Session revocation through the session version, ``sv`` (release 1.3, workstream A, lot A4b; plan phase01Accounts §4.5, D-A17).

A session is the JWT of the ``session`` cookie: signed, stateless, good until its ``exp``. Nothing on the server could end
it before that: a cookie stolen before a password change kept working after it, on every device, and an account
deactivated then reactivated got its old sessions back. Each account now has a session generation,
``users.session_version`` (migration 005), and each cookie carries the generation it was issued at, the ``sv`` claim.
Raising the account's version ends every session issued before, everywhere at once. The contract pinned here:

1. ``auth_service.SessionClaims``: a frozen dataclass ``(user_id, session_version)``, compared by value.
2. ``create_jwt_token(user_id, ttl_hours, session_version)``: an HS256 token whose payload is exactly ``sub`` (the user
   id as a string), ``iat``, ``exp`` (``iat`` plus the TTL) — as before — and ``sv``, the version as an integer.
3. ``decode_jwt_token`` answers ``SessionClaims`` or ``None``, never an exception. ``None`` for a token that is expired,
   signed by another key, tampered, unsigned or no token at all, for a missing ``sub`` or one that is not a number, and
   for an ``sv`` that is present but not an integer (a string, a float, a bool, null, a list, an object). A token without
   ``sv`` — every cookie issued before 1.3 — is a session at version 0: the upgrade signs nobody out.
4. ``auth.get_current_user``: after its checks of the account, unchanged (it exists, it is active, with their details), a
   cookie whose version differs from the account's, behind or ahead, is 401 «Session expired or invalid»: the detail of
   an invalid token, so nothing tells the holder why.
5. ``user_service.end_sessions(user)`` raises ``user.session_version`` by one, at once, and does not commit: the caller
   commits it with the change that ends the sessions.
6. Raised by exactly one, and committed, by ``reset_password`` (the CLI ``user reset``, later the reset link), which also
   hashes the new password in a worker thread instead of the event loop (backlog A-3); by ``set_user_active(..., False)``,
   so that a reactivation does not bring the old sessions back; and by ``set_user_admin(..., False)``. Activation and
   promotion leave it alone, and a refused operation (unknown user, last active administrator, already an admin, not an
   admin) changes nothing, for anybody.

``POST /auth/change-password``, which raises the version and re-issues the current device's cookie in the same response,
is tested over HTTP in ``test_api/test_session_revocation_api.py``. Cookies without ``sv`` and version mismatches are
tested here, in-process: the lane's server signs with a secret ``dev.py`` generates when it starts it, so no test can
forge a cookie that server accepts.

Every database is a private file under ``tmp_path`` built by ``SQLModel.metadata.create_all``, opened as production opens
its own (``sqlite+aiosqlite``, NullPool, the connect listener of ``backend.app.db.session``). Users are written as rows,
with a marker for a hash and with starting versions other than 0, so that «raised by one» cannot pass for «set to one»;
every version check reads all the users of the database, so that raising somebody else's version is caught too. The JWT
secret is replaced by a known one for each test (monkeypatch, this process only), so a hand-made token is signed exactly
as the server signs. No server, no session on the lane's database. Nothing is timed.

Red until A4b lands. A test that needs ``SessionClaims``, ``end_sessions`` or the new signature of ``create_jwt_token``
fails on its absence; the others fail on the behaviour (a token with a broken ``sv`` or ``sub`` accepted or raising, a
cookie at another version accepted, a version not raised, bcrypt on the event loop's thread). The guards — the tokens
refused today, the cookies at the account's version, the inactive account's 401, activation, promotion and every
refusal — are green today and must stay green.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import json
import threading
import time
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any, Optional, Union

import jwt
import pytest
import pytest_asyncio
from fastapi import HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import User
from backend.app.services.accounts import auth_service, user_service
from backend.test_scripts.test_utils import print_section, print_success

#: The JWT secret of every test here (the ``secret`` fixture): known, so that a hand-made token is signed as the server signs.
TEST_SECRET = "a4b-session-version-test-secret-0123456789abcdef0123456789abcdef"
#: Another instance's secret: what it signed is worth nothing here.
FOREIGN_SECRET = "a4b-another-instance-secret-key-fedcba9876543210fedcba9876543210"
ALGORITHM = "HS256"
#: What the users written here hold for a hash: never a bcrypt hash, never checked.
MARKER_HASH = "marker-hash-not-bcrypt"
#: What the stand-in for hash_password answers: the hash reset_password must store.
STAND_IN_HASH = "stand-in-hash-of-the-new-password"
NEW_PASSWORD = "Reset-Password-123!"
#: get_current_user's refusals, as (status code, detail).
SESSION_EXPIRED = (401, "Session expired or invalid")
ACCOUNT_DISABLED = (401, "User account is disabled")


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest.fixture(autouse=True)
def secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """auth_service signs and checks with TEST_SECRET during the test: it reads its module-level secret at every call."""
    monkeypatch.setattr(auth_service, "_JWT_SECRET", TEST_SECRET)
    return TEST_SECRET


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own, disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'sessions.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


def _claims_type() -> type:
    """``auth_service.SessionClaims``, looked up by the test that needs it: its absence is that test's red, not a collection error of the whole file."""
    claims_type = getattr(auth_service, "SessionClaims", None)
    assert claims_type is not None, "[new] auth_service.SessionClaims does not exist: decode_jwt_token has no claims to answer with"
    return claims_type


def _claims(user_id: int, session_version: int) -> Any:
    return _claims_type()(user_id=user_id, session_version=session_version)


def _end_sessions() -> Callable[[User], None]:
    """``user_service.end_sessions``, looked up by the test that needs it, like _claims_type."""
    end_sessions = getattr(user_service, "end_sessions", None)
    assert end_sessions is not None, "[new] user_service.end_sessions does not exist: nothing raises an account's session version"
    return end_sessions


def _payload(user_id: int, **claims: Any) -> dict[str, Any]:
    """A live payload for ``user_id`` as every cookie before 1.3 carried it — ``sub`` (a string), ``iat``, ``exp`` an hour later — plus ``claims``."""
    now = int(time.time())
    return {"sub": str(user_id), "iat": now, "exp": now + 3600, **claims}


def _sign(payload: dict[str, Any], key: str = TEST_SECRET) -> str:
    return jwt.encode(payload, key, algorithm=ALGORITHM)


def _cookie(user_id: int, session_version: int) -> str:
    """A session cookie of ``user_id`` at ``session_version``, signed as the server signs it."""
    return _sign(_payload(user_id, sv=session_version))


def _legacy_cookie(user_id: int) -> str:
    """A session cookie issued before 1.3: no ``sv``."""
    return _sign(_payload(user_id))


def _decode(token: str) -> Any:
    """decode_jwt_token(token). An exception is a breach of the contract, reported as such rather than as an error of the test."""
    try:
        return auth_service.decode_jwt_token(token)
    except Exception as exc:
        pytest.fail(f"decode_jwt_token must answer None for a token it cannot accept, never raise: it raised {exc!r}")


async def _add_user(engine: AsyncEngine, username: str, *, version: int, active: bool = True, admin: bool = False) -> int:
    """Write a user as a row — no bcrypt — at session version ``version``; its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username, email=f"{username}@example.test", hashed_password=MARKER_HASH, is_active=active, is_superuser=admin, session_version=version)
        session.add(user)
        await session.commit()
    return user.id


async def _versions(engine: AsyncEngine) -> dict[str, int]:
    """{username: session_version} of every user of the private database, as a fresh connection reads it: what is committed."""
    async with engine.connect() as connection:
        rows = (await connection.execute(text("SELECT username, session_version FROM users"))).tuples().all()
    return dict(rows)


async def _accounts(engine: AsyncEngine) -> dict[str, tuple[bool, bool, str]]:
    """{username: (is_active, is_superuser, hashed_password)} of every user of the private database, read in a fresh session."""
    async with AsyncSession(engine) as session:
        users = (await session.execute(select(User))).scalars().all()
    return {user.username: (user.is_active, user.is_superuser, user.hashed_password) for user in users}


async def _account(engine: AsyncEngine, username: str) -> User:
    """``username`` as a fresh session reads it."""
    async with AsyncSession(engine) as session:
        return (await session.execute(select(User).where(User.username == username))).scalar_one()


async def _end_sessions_of(engine: AsyncEngine, user_id: int) -> None:
    """end_sessions on the user, committed by its caller as the services that call it commit."""
    end_sessions = _end_sessions()
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        assert user is not None, f"user {user_id} is not in the private database"
        end_sessions(user)
        await session.commit()


def _request(token: str) -> Request:
    """GET /api/v1/auth/me as uvicorn hands it to the app, carrying the session cookie ``token`` and nothing else."""
    cookie = f"{auth_api.SESSION_COOKIE_NAME}={token}".encode("latin-1")
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/auth/me",
        "raw_path": b"/api/v1/auth/me",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"librefolio.test"), (b"cookie", cookie)],
        "client": ("127.0.0.1", 50000),
        "server": ("librefolio.test", 80),
    }
    return Request(scope)


async def _current_user(engine: AsyncEngine, token: str) -> Union[User, HTTPException]:
    """get_current_user as FastAPI calls it for GET /auth/me, on the private database: the user, or the refusal (returned, never raised)."""
    async with AsyncSession(engine) as session:
        try:
            return await auth_api.get_current_user(_request(token), session)
        except HTTPException as refusal:
            return refusal


def _refusal(outcome: Union[User, HTTPException]) -> Optional[tuple[int, Any]]:
    """(status code, detail) of a refusal; None when the cookie signed somebody in."""
    return (outcome.status_code, outcome.detail) if isinstance(outcome, HTTPException) else None


def _signed_in_as(outcome: Union[User, HTTPException], user_id: int) -> bool:
    return isinstance(outcome, User) and outcome.id == user_id


def _describe(outcome: Union[User, HTTPException]) -> str:
    return f"refused {_refusal(outcome)}" if isinstance(outcome, HTTPException) else f"signed in as user {outcome.id}"


# =============================================================================
# 1-2. THE CLAIMS AND THE TOKEN
# =============================================================================


def test_session_claims_is_a_frozen_pair_compared_by_value() -> None:
    """Contract 1 — NEW, red today (no SessionClaims): ``SessionClaims(user_id, session_version)``, a frozen dataclass; claims with the same values are equal."""
    print_section("Contract 1: SessionClaims")
    claims_type = _claims_type()

    assert dataclasses.is_dataclass(claims_type), f"SessionClaims must be a dataclass: {claims_type!r}"
    assert [field.name for field in dataclasses.fields(claims_type)] == ["user_id", "session_version"]
    claims = claims_type(user_id=7, session_version=3)
    assert claims == claims_type(user_id=7, session_version=3), "two claims with the same values must be equal"
    assert claims != claims_type(user_id=7, session_version=4), "claims at two versions must differ"
    with pytest.raises(dataclasses.FrozenInstanceError):
        claims.session_version = 4
    print_success("SessionClaims(user_id, session_version), frozen, compared by value")


@pytest.mark.parametrize(("user_id", "session_version"), [(1, 0), (7, 3), (123456, 41)], ids=["version-0", "version-3", "version-41"])
def test_a_token_decodes_to_the_claims_it_was_issued_with(user_id: int, session_version: int) -> None:
    """Contracts 2 and 3 — NEW, red today (create_jwt_token takes no session_version): what create_jwt_token signs, decode_jwt_token reads back as the same SessionClaims."""
    print_section(f"Contract 2: round trip of user {user_id} at version {session_version}")

    token = auth_service.create_jwt_token(user_id=user_id, ttl_hours=1, session_version=session_version)

    decoded = _decode(token)
    assert decoded == _claims(user_id, session_version), f"decode_jwt_token(create_jwt_token(...)) must give back SessionClaims({user_id}, {session_version}): got {decoded!r}"
    print_success(f"user {user_id} at version {session_version}: round trip")


def test_the_payload_is_sub_iat_exp_and_sv(secret: str) -> None:
    """Contract 2 — NEW, red today: HS256; ``sub`` the user id as a string and ``exp`` ``iat`` plus the TTL, as before 1.3; ``sv`` the version, an integer.

    Nothing else: the cookie says whose session it is and of which generation, no more.
    """
    print_section("Contract 2: the payload")

    token = auth_service.create_jwt_token(user_id=7, ttl_hours=5, session_version=3)

    assert jwt.get_unverified_header(token)["alg"] == ALGORITHM, f"the token must be signed with {ALGORITHM}: {jwt.get_unverified_header(token)}"
    payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    assert set(payload) == {"sub", "iat", "exp", "sv"}, f"the payload must be exactly sub, iat, exp and sv: {sorted(payload)}"
    assert payload["sub"] == "7", f"sub stays the user id as a string, as in every cookie issued before 1.3: {payload['sub']!r}"
    assert type(payload["sv"]) is int and payload["sv"] == 3, f"sv must be the version, an integer: {payload['sv']!r}"
    assert payload["exp"] - payload["iat"] == 5 * 3600, f"exp must be iat plus the TTL: {payload}"
    print_success("{sub, iat, exp, sv}, signed HS256")


# =============================================================================
# 3. DECODE
# =============================================================================


def test_a_token_without_sv_is_a_session_at_version_zero() -> None:
    """Contract 3 — NEW, red today (decode_jwt_token answers the bare user id): every cookie issued before 1.3 has no ``sv``; it is a session at version 0, so the upgrade signs nobody out."""
    print_section("Contract 3: a token without sv")

    decoded = _decode(_legacy_cookie(7))

    assert decoded == _claims(7, 0), f"a token without sv must decode to SessionClaims(7, 0): got {decoded!r}"
    print_success("no sv: version 0")


@pytest.mark.parametrize(
    "sv",
    [
        pytest.param("1", id="string"),
        pytest.param(1.0, id="float"),
        pytest.param(True, id="bool"),
        pytest.param(None, id="null"),
        pytest.param([1], id="list"),
        pytest.param({"version": 1}, id="object"),
    ],
)
def test_an_sv_that_is_not_an_integer_makes_the_token_invalid(sv: Any) -> None:
    """Contract 3 — NEW, red today (sv is ignored, the user id comes back): an ``sv`` present but not an integer is no version, and the token is worth None.

    A bool is no integer here, although ``isinstance(True, int)``; and null is not «absent»: absent is version 0, present
    and null is a broken token. Barrier: the same payload with an integer ``sv`` decodes.
    """
    print_section(f"Contract 3: sv = {sv!r}")
    assert _decode(_cookie(7, 3)) is not None, "barrier: the same payload with sv = 3 decodes"

    decoded = _decode(_sign(_payload(7, sv=sv)))

    assert decoded is None, f"[new] sv = {sv!r} ({type(sv).__name__}) is no integer: decode_jwt_token must answer None, got {decoded!r}"
    print_success(f"sv = {sv!r}: None")


def _tampered() -> str:
    """User 7's token whose payload now says user 1, the signature left as it was."""
    header, _, signature = _cookie(7, 0).split(".")
    forged_payload = base64.urlsafe_b64encode(json.dumps(_payload(1, sv=0)).encode("utf-8")).rstrip(b"=").decode("ascii")
    return f"{header}.{forged_payload}.{signature}"


#: Tokens nobody may be signed in with, built when the test runs (their clock is the test's).
UNTRUSTED_TOKENS: dict[str, Callable[[], str]] = {
    "expired": lambda: _sign({**_payload(7, sv=0), "iat": int(time.time()) - 7200, "exp": int(time.time()) - 3600}),
    "signed-by-another-key": lambda: _sign(_payload(7, sv=0), key=FOREIGN_SECRET),
    "tampered": _tampered,
    "unsigned": lambda: jwt.encode(_payload(7, sv=0), None, algorithm="none"),
    "not-a-token": lambda: "not-a-jwt",
    "empty": lambda: "",
    "without-sub": lambda: _sign({claim: value for claim, value in _payload(7, sv=0).items() if claim != "sub"}),
    "sub-not-a-number": lambda: _sign({**_payload(7, sv=0), "sub": "seven"}),
}


@pytest.mark.parametrize("case", list(UNTRUSTED_TOKENS))
def test_a_token_that_cannot_be_trusted_decodes_to_none_and_never_raises(case: str) -> None:
    """Contract 3: expired, signed by another key, tampered (another user in the payload), unsigned (alg none), no token at all, without ``sub``, or with a ``sub`` that is no number: None, and no exception escapes.

    GUARD, green today and after — but for sub-not-a-number, NEW, red today: ``int("seven")`` raises ValueError out of
    decode_jwt_token. Barrier: the same claims, signed with this instance's key, decode.
    """
    print_section(f"Contract 3: an untrusted token ({case})")
    assert _decode(_cookie(7, 0)) is not None, "barrier: user 7's token, signed with this instance's key, decodes"

    decoded = _decode(UNTRUSTED_TOKENS[case]())

    assert decoded is None, f"a token {case} must decode to None: got {decoded!r}"
    print_success(f"{case}: None")


# =============================================================================
# 4. GET_CURRENT_USER
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [0, 3], ids=["version-0", "version-3"])
async def test_a_cookie_at_the_accounts_version_signs_the_user_in(engine: AsyncEngine, version: int) -> None:
    """Contract 4 — GUARD, green today (sv is ignored) and after: a cookie whose ``sv`` is the account's version is the account's session. The presence barrier of the refusals below."""
    print_section(f"Contract 4: a cookie at the account's version, {version}")
    user_id = await _add_user(engine, "alice", version=version)

    outcome = await _current_user(engine, _cookie(user_id, version))

    assert _signed_in_as(outcome, user_id), f"a cookie at alice's version {version} must sign her in: {_describe(outcome)}"
    print_success(f"version {version}: signed in")


@pytest.mark.asyncio
@pytest.mark.parametrize(("cookie_version", "account_version"), [(0, 1), (2, 1)], ids=["behind", "ahead"])
async def test_a_cookie_at_another_version_is_refused_as_an_invalid_session(engine: AsyncEngine, cookie_version: int, account_version: int) -> None:
    """Contract 4 — NEW, red today (the cookie signs the user in): a version behind the account's (a session issued before its sessions ended) or ahead of it (a version it never had) is 401 «Session expired or invalid»: the detail of an invalid token, so nothing tells the holder why."""
    print_section(f"Contract 4: a cookie at version {cookie_version}, the account at {account_version}")
    user_id = await _add_user(engine, "bob", version=account_version)
    assert _signed_in_as(await _current_user(engine, _cookie(user_id, account_version)), user_id), f"barrier: a cookie at bob's version, {account_version}, signs him in"

    outcome = await _current_user(engine, _cookie(user_id, cookie_version))

    assert _refusal(outcome) == SESSION_EXPIRED, f"[new] a cookie at version {cookie_version}, for an account at version {account_version}, must be refused with {SESSION_EXPIRED}: {_describe(outcome)}"
    print_success(f"version {cookie_version} against {account_version}: refused")


@pytest.mark.asyncio
async def test_a_cookie_without_sv_signs_in_an_account_at_version_zero(engine: AsyncEngine) -> None:
    """Contracts 3 and 4 — GUARD, green today and after: after the upgrade every account is at version 0 and every cookie it holds has no ``sv``; they keep signing in."""
    print_section("Contract 4: a cookie without sv, the account at version 0")
    user_id = await _add_user(engine, "carol", version=0)

    outcome = await _current_user(engine, _legacy_cookie(user_id))

    assert _signed_in_as(outcome, user_id), f"a cookie issued before 1.3 must keep carol signed in while her version is 0: {_describe(outcome)}"
    print_success("no sv, version 0: signed in")


@pytest.mark.asyncio
async def test_a_cookie_without_sv_is_refused_once_the_sessions_are_ended(engine: AsyncEngine) -> None:
    """Contracts 4 and 5 — NEW, red today (no end_sessions): ending the sessions moves the account to version 1; a cookie without ``sv``, worth 0, is then refused like any older session."""
    print_section("Contract 4: a cookie without sv, after end_sessions")
    user_id = await _add_user(engine, "dan", version=0)
    cookie = _legacy_cookie(user_id)
    assert _signed_in_as(await _current_user(engine, cookie), user_id), "barrier: dan's cookie without sv signs him in before his sessions end"

    await _end_sessions_of(engine, user_id)

    outcome = await _current_user(engine, cookie)
    assert _refusal(outcome) == SESSION_EXPIRED, f"[new] once dan's sessions are ended, his cookie without sv must be refused with {SESSION_EXPIRED}: {_describe(outcome)}"
    print_success("no sv, after end_sessions: refused")


@pytest.mark.asyncio
async def test_a_cookie_issued_at_the_accounts_version_works_until_its_sessions_end(engine: AsyncEngine) -> None:
    """Contracts 2, 4 and 5 — NEW, red today (create_jwt_token takes no session_version): a password change in-process.

    The cookie create_jwt_token issued at the account's version signs the user in; once end_sessions is committed it is
    refused; the cookie issued at the new version, the one the device that changed the password receives, signs in.
    """
    print_section("Contracts 2, 4, 5: issued, ended, re-issued")
    user_id = await _add_user(engine, "eve", version=2)
    first = auth_service.create_jwt_token(user_id=user_id, ttl_hours=1, session_version=2)
    assert _signed_in_as(await _current_user(engine, first), user_id), "barrier: the cookie issued at eve's version signs her in"

    await _end_sessions_of(engine, user_id)
    refused = await _current_user(engine, first)
    reissued = await _current_user(engine, auth_service.create_jwt_token(user_id=user_id, ttl_hours=1, session_version=3))

    assert _refusal(refused) == SESSION_EXPIRED, f"[new] the cookie issued at version 2 must be refused once eve is at version 3: {_describe(refused)}"
    assert _signed_in_as(reissued, user_id), f"the cookie issued at version 3 must sign eve in: {_describe(reissued)}"
    print_success("version 2 refused after end_sessions, version 3 signed in")


@pytest.mark.asyncio
@pytest.mark.parametrize("cookie", ["at-the-accounts-version", "behind-it", "without-sv"])
async def test_an_inactive_accounts_cookie_is_told_the_account_is_disabled(engine: AsyncEngine, cookie: str) -> None:
    """Contract 4 — GUARD, green today and after: the account's checks come first and keep their details; an inactive account is 401 «User account is disabled», whatever version its cookie carries."""
    print_section(f"Contract 4: an inactive account, its cookie {cookie}")
    user_id = await _add_user(engine, "fay", version=2, active=False)
    token = {"at-the-accounts-version": _cookie(user_id, 2), "behind-it": _cookie(user_id, 1), "without-sv": _legacy_cookie(user_id)}[cookie]

    outcome = await _current_user(engine, token)

    assert _refusal(outcome) == ACCOUNT_DISABLED, f"an inactive account's cookie ({cookie}) must be refused with {ACCOUNT_DISABLED}: {_describe(outcome)}"
    print_success(f"inactive, cookie {cookie}: account disabled")


# =============================================================================
# 5. END_SESSIONS
# =============================================================================


@pytest.mark.asyncio
async def test_end_sessions_raises_the_version_by_one_and_leaves_the_commit_to_the_caller(engine: AsyncEngine) -> None:
    """Contract 5 — NEW, red today (no end_sessions): the version is one higher at once, in memory; nothing is committed — a fresh connection still reads the old version, and a rollback undoes it —; the caller's commit stores it, for that account only."""
    print_section("Contract 5: end_sessions")
    end_sessions = _end_sessions()
    user_id = await _add_user(engine, "gus", version=4)
    await _add_user(engine, "hana", version=2)

    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        assert user is not None, "gus is in the private database"
        assert end_sessions(user) is None, "end_sessions is a plain function answering None"
        assert user.session_version == 5, f"end_sessions must raise the version by one, at once: {user.session_version}"
        assert await _versions(engine) == {"gus": 4, "hana": 2}, "end_sessions must not commit: the caller commits, with the change that ends the sessions"
        await session.rollback()
    assert await _versions(engine) == {"gus": 4, "hana": 2}, "a rollback must undo it"

    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        assert user is not None, "gus is in the private database"
        end_sessions(user)
        await session.commit()
    assert await _versions(engine) == {"gus": 5, "hana": 2}, "committed by the caller: gus one higher, nobody else"
    print_success("4 → 5 in memory, rolled back, then committed by the caller")


# =============================================================================
# 6. WHAT RAISES THE VERSION, AND WHAT DOES NOT
# =============================================================================


@pytest.mark.asyncio
async def test_reset_password_ends_the_accounts_sessions_and_sets_the_new_password(engine: AsyncEngine) -> None:
    """Contract 6 — NEW, red today (the version stays): the password is reset and the new one verifies (GUARD), and the version is one higher, committed, for that account only."""
    print_section("Contract 6: reset_password")
    await _add_user(engine, "ivan", version=2)
    await _add_user(engine, "jade", version=5)
    before = await _versions(engine)

    async with AsyncSession(engine) as session:
        outcome = await user_service.reset_password(session, "ivan", NEW_PASSWORD)

    assert outcome == (True, None), f"reset_password must succeed: {outcome}"
    stored = (await _account(engine, "ivan")).hashed_password
    assert await asyncio.to_thread(auth_service.verify_password, NEW_PASSWORD, stored), "the new password must verify against the stored hash"
    after = await _versions(engine)
    assert after == {**before, "ivan": before["ivan"] + 1}, f"[new] reset_password must raise ivan's version by one, and nobody else's: {before} → {after}"
    print_success("password reset, ivan 2 → 3")


@pytest.mark.asyncio
async def test_reset_password_hashes_the_new_password_off_the_event_loop(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 6, backlog A-3 — NEW, red today (hash_password runs on the event loop's thread): bcrypt holds its thread for about a quarter of a second.

    reset_password runs under the CLI today and behind the reset link tomorrow, where a held loop serves no other request:
    hash_password belongs in a worker thread (asyncio.to_thread), and its hash is the one stored. The stand-in records the
    thread that calls it; nothing is timed.
    """
    print_section("Contract 6: reset_password hashes off the event loop")
    await _add_user(engine, "kai", version=0)
    loop_thread = threading.get_ident()
    calls: list[tuple[str, int]] = []

    def hash_password(password: str) -> str:
        calls.append((password, threading.get_ident()))
        return STAND_IN_HASH

    monkeypatch.setattr(user_service, "hash_password", hash_password)

    async with AsyncSession(engine) as session:
        outcome = await user_service.reset_password(session, "kai", NEW_PASSWORD)

    assert outcome == (True, None), f"reset_password must succeed: {outcome}"
    assert [password for password, _ in calls] == [NEW_PASSWORD], f"reset_password must hash the new password, once, through user_service.hash_password: {[password for password, _ in calls]}"
    [(_, hashing_thread)] = calls
    assert (await _account(engine, "kai")).hashed_password == STAND_IN_HASH, "the hash computed must be the one stored"
    assert hashing_thread != loop_thread, f"[new] hash_password ran on the event loop's thread ({loop_thread}): it holds the loop for the whole bcrypt run; it belongs in await asyncio.to_thread(...)"
    print_success("hash_password ran in a worker thread")


@pytest.mark.asyncio
@pytest.mark.parametrize("admin", [False, True], ids=["a-user", "an-administrator-beside-another"])
async def test_deactivating_an_account_ends_its_sessions(engine: AsyncEngine, admin: bool) -> None:
    """Contract 6 — NEW, red today (the version stays): the deactivation goes through and the version is one higher, committed, for that account only."""
    print_section(f"Contract 6: deactivating {'an administrator' if admin else 'a user'}")
    await _add_user(engine, "root", version=1, admin=True)
    await _add_user(engine, "lena", version=2, admin=admin)
    before = await _versions(engine)

    async with AsyncSession(engine) as session:
        outcome = await user_service.set_user_active(session, "lena", False)

    assert outcome == (True, None), f"deactivating lena must succeed: {outcome}"
    assert (await _account(engine, "lena")).is_active is False, "lena must be inactive"
    after = await _versions(engine)
    assert after == {**before, "lena": before["lena"] + 1}, f"[new] deactivating lena must raise her version by one, and nobody else's: {before} → {after}"
    print_success("deactivated, lena 2 → 3")


@pytest.mark.asyncio
async def test_a_reactivated_account_does_not_get_its_old_sessions_back(engine: AsyncEngine) -> None:
    """Contracts 4 and 6 — NEW, red today (the old cookie signs the user in again): why deactivation raises the version.

    A cookie issued before the deactivation is refused while the account is inactive (GUARD: the account check, today
    already), and still refused, as an invalid session, once the account is active again.
    """
    print_section("Contract 6: a reactivated account and its old cookie")
    user_id = await _add_user(engine, "mona", version=2)
    old = _cookie(user_id, 2)
    assert _signed_in_as(await _current_user(engine, old), user_id), "barrier: mona's cookie signs her in before the deactivation"

    async with AsyncSession(engine) as session:
        assert await user_service.set_user_active(session, "mona", False) == (True, None), "setup: deactivating mona"
    while_inactive = await _current_user(engine, old)
    async with AsyncSession(engine) as session:
        assert await user_service.set_user_active(session, "mona", True) == (True, None), "setup: reactivating mona"
    once_active = await _current_user(engine, old)

    assert _refusal(while_inactive) == ACCOUNT_DISABLED, f"while mona is inactive her cookie must be refused with {ACCOUNT_DISABLED}: {_describe(while_inactive)}"
    assert _refusal(once_active) == SESSION_EXPIRED, f"[new] once mona is active again, the cookie issued before her deactivation must stay refused with {SESSION_EXPIRED}: {_describe(once_active)}"
    print_success("the old cookie stays refused after the reactivation")


@pytest.mark.asyncio
async def test_activating_an_account_leaves_its_version_alone(engine: AsyncEngine) -> None:
    """Contract 6 — GUARD, green today and after: an activation ends nothing; the version stays where the deactivation left it."""
    print_section("Contract 6: activating an account")
    await _add_user(engine, "nina", version=4, active=False)
    await _add_user(engine, "omar", version=1)
    before = await _versions(engine)

    async with AsyncSession(engine) as session:
        outcome = await user_service.set_user_active(session, "nina", True)

    assert outcome == (True, None), f"activating nina must succeed: {outcome}"
    assert (await _account(engine, "nina")).is_active is True, "nina must be active"
    assert await _versions(engine) == before, "an activation must raise no version"
    print_success("activated, versions unchanged")


@pytest.mark.asyncio
@pytest.mark.parametrize("active", [True, False], ids=["active-beside-another-administrator", "inactive"])
async def test_demoting_an_administrator_ends_their_sessions(engine: AsyncEngine, active: bool) -> None:
    """Contract 6 — NEW, red today (the version stays): a demotion takes the role away from every session the account holds; they end, and the next login is a user's."""
    print_section(f"Contract 6: demoting an {'active' if active else 'inactive'} administrator")
    await _add_user(engine, "root", version=1, admin=True)
    await _add_user(engine, "paul", version=2, admin=True, active=active)
    before = await _versions(engine)

    async with AsyncSession(engine) as session:
        outcome = await user_service.set_user_admin(session, "paul", False)

    assert outcome == (True, None), f"demoting paul must succeed: {outcome}"
    assert (await _account(engine, "paul")).is_superuser is False, "paul must no longer be an administrator"
    after = await _versions(engine)
    assert after == {**before, "paul": before["paul"] + 1}, f"[new] demoting paul must raise his version by one, and nobody else's: {before} → {after}"
    print_success("demoted, paul 2 → 3")


@pytest.mark.asyncio
async def test_promoting_a_user_leaves_their_version_alone(engine: AsyncEngine) -> None:
    """Contract 6 — GUARD, green today and after: a promotion takes nothing away; the sessions stay, and their next request is an administrator's."""
    print_section("Contract 6: promoting a user")
    await _add_user(engine, "root", version=1, admin=True)
    await _add_user(engine, "quinn", version=4)
    before = await _versions(engine)

    async with AsyncSession(engine) as session:
        outcome = await user_service.set_user_admin(session, "quinn", True)

    assert outcome == (True, None), f"promoting quinn must succeed: {outcome}"
    assert (await _account(engine, "quinn")).is_superuser is True, "quinn must be an administrator"
    assert await _versions(engine) == before, "a promotion must raise no version"
    print_success("promoted, versions unchanged")


#: Operations user_service refuses, as (function, username, its third argument). In the database of the test, root is the
#: only active administrator, otto an inactive one (he cannot log in, so he does not count), rita a user.
REFUSALS: dict[str, tuple[str, str, Any]] = {
    "deactivate-the-last-active-administrator": ("set_user_active", "root", False),
    "demote-the-last-active-administrator": ("set_user_admin", "root", False),
    "promote-an-administrator": ("set_user_admin", "root", True),
    "demote-a-user": ("set_user_admin", "rita", False),
    "deactivate-an-unknown-user": ("set_user_active", "nobody", False),
    "demote-an-unknown-user": ("set_user_admin", "nobody", False),
    "reset-an-unknown-users-password": ("reset_password", "nobody", NEW_PASSWORD),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(REFUSALS))
async def test_a_refused_operation_raises_nobodys_version(engine: AsyncEngine, case: str) -> None:
    """Contract 6 — GUARD, green today and after: a refusal answers (False, a message) and changes nothing — no flag, no hash, no version — for anybody."""
    print_section(f"Contract 6: refused, {case}")
    operation, username, argument = REFUSALS[case]
    await _add_user(engine, "root", version=1, admin=True)
    await _add_user(engine, "otto", version=2, admin=True, active=False)
    await _add_user(engine, "rita", version=3)
    accounts, versions = await _accounts(engine), await _versions(engine)

    async with AsyncSession(engine) as session:
        ok, error = await getattr(user_service, operation)(session, username, argument)

    assert ok is False and error, f"{operation}({username!r}, {argument!r}) must be refused with a message: {(ok, error)}"
    assert await _accounts(engine) == accounts, "a refusal must change no account"
    assert await _versions(engine) == versions, "a refusal must raise no version"
    print_success(f"{case}: refused, nothing changed")
