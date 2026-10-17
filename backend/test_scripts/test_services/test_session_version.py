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
5. Updated in A8a (A-34): ``await user_service.end_sessions(session, user)``, a coroutine function, raises the account's
   stored version by one in the caller's transaction, at once — one SQL increment, ``UPDATE users SET session_version =
   session_version + 1 WHERE id = :id RETURNING session_version`` —, and answers None. ``user.session_version`` then
   holds the value returned, set as committed (``set_committed_value``): the version alone does not mark the object
   changed, and nothing else of it is flushed or refreshed — a field the caller set before, a new hash, stays pending
   for the caller's commit, neither written early nor lost. It does not commit: the caller commits it with the change
   that ends the sessions; until then a fresh connection reads the old version, and a rollback leaves it there. Two
   requests that end the same account's sessions, each from the account as it loaded it before the other committed,
   raise it by two (A-34): the cookie the first one re-issued does not survive the second. Two sessions on the private
   file, one after the other in a set order: nothing is raced.
6. Raised by exactly one, and committed, by ``reset_password`` (the CLI ``user reset``, later the reset link), which also
   hashes the new password in a worker thread instead of the event loop (backlog A-3); by ``set_user_active(..., False)``,
   so that a reactivation does not bring the old sessions back; and by ``set_user_admin(..., False)``. Activation and
   promotion leave it alone, and a refused operation (unknown user, last active administrator, already an admin, not an
   admin) changes nothing, for anybody.
7. Lot A-27 (the security review of workstream E, E6.9): ``reset_password``, and ``update_profile`` when the address
   really changes — another address under ``same_email`` (P18: other A–Z capitals are the same address, a letter outside
   A–Z in capitals is another one) —, also revoke, in the commit of the change, every live password-reset link of the
   account (``PASSWORD_RESET``, neither consumed nor revoked), whoever issued it: a link the old mailbox asked for before
   the change opens nothing after it. Nothing else moves — the account's links of the other purposes (its email
   verification, an invitation it issued), its reset links already spent or revoked, which keep their own moments, every
   other account's links —, and a change that keeps the address (other A–Z capitals, the username alone) or is refused
   (an address another account holds) revokes nothing.
   Updated in A7b-2 (A-32/A-33), on every account, waiting for its setup or not: the account's admin setup link moves
   too. ``reset_password`` retires it — revoked and consumed at the change's moment, without a consumer —; a real change
   of the address revokes it, not consumed. A change that keeps the address, or a refused one, leaves it as it was.

``POST /auth/change-password``, which raises the version and re-issues the current device's cookie in the same response,
is tested over HTTP in ``test_api/test_session_revocation_api.py``, with the reset links it and ``PUT /auth/profile``
revoke (contract 7). Cookies without ``sv`` and version mismatches are tested here, in-process: the lane's server signs
with a secret ``dev.py`` generates when it starts it, so no test can forge a cookie that server accepts.

Every database is a private file under ``tmp_path`` built by ``SQLModel.metadata.create_all``, opened as production opens
its own (``sqlite+aiosqlite``, NullPool, the connect listener of ``backend.app.db.session``). Users are written as rows,
with a marker for a hash and with starting versions other than 0, so that «raised by one» cannot pass for «set to one»;
every version check reads all the users of the database, so that raising somebody else's version is caught too. Contract
7's links are issued there by ``token_service.issue_token``, then read back as rows — every row of ``account_tokens``, so
that a link revoked by mistake is caught too — and through ``token_service.inspect_token``. The JWT secret is replaced by
a known one for each test (monkeypatch, this process only), so a hand-made token is signed exactly as the server signs.
No server, no session on the lane's database. Nothing is timed.

Red until A4b lands. A test that needs ``SessionClaims``, ``end_sessions`` or the new signature of ``create_jwt_token``
fails on its absence; the others fail on the behaviour (a token with a broken ``sv`` or ``sub`` accepted or raising, a
cookie at another version accepted, a version not raised, bcrypt on the event loop's thread). The guards — the tokens
refused today, the cookies at the account's version, the inactive account's 401, activation, promotion and every
refusal — are green today and must stay green.

Red until A-27, contract 7: the account's live reset links still valid after ``reset_password`` or a real change of the
address. Its guards — the address kept, the username alone, the refusal, and every other link — are green today and must
stay green.

Red until A7b-2 (A-32/A-33), in the same two tests of contract 7: the account's admin setup link still valid after
``reset_password`` (it must be retired) and after a real change of the address (it must be revoked).

Red until A8a (A-34), from workstream E's security review: ``end_sessions(user)`` adds one to the object's own copy, so
two requests that loaded the account before either committed — an administrator's «sign out everywhere» while the user
changes the password, which re-issues the device's cookie at the new version — store the same value, and the cookie
issued between them survives the second. Every test that calls end_sessions fails today on its shape, a plain function
of ``(user)``, asserted where it is looked up (``_end_sessions``): contract 5's three tests, and the two of contract 4
that end the sessions through ``_end_sessions_of`` — and ``test_backup_apply.py``'s test (i), which calls that helper
too. Behind the shape, an asynchronous end_sessions that still adds one to the object fails on what A-34 is about: the
object marked changed by the version, the increment missing from the caller's transaction, v+1 stored by the race
instead of v+2. The other tests reach end_sessions only through the services, unchanged until A8a: green today, and
after.
"""

from __future__ import annotations

import asyncio
import base64
import dataclasses
import inspect
import json
import threading
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union

import jwt
import pytest
import pytest_asyncio
from fastapi import HTTPException, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm.attributes import get_history
from sqlalchemy.pool import NullPool

from backend.app.api.v1 import auth as auth_api
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.services.accounts import auth_service, token_service, user_service
from backend.app.services.accounts.token_service import TokenStatus
from backend.app.utils.datetime_utils import ensure_utc, utcnow
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


# updated in A8a (A-34): the shape is asserted where the function is looked up
def _end_sessions() -> Callable[[AsyncSession, User], Awaitable[None]]:
    """``user_service.end_sessions``, looked up by the test that needs it, like _claims_type; since A8a (A-34) checked for
    its shape too, a coroutine function of ``(session, user)``, so that a test calling it fails on that, and says so,
    rather than on a TypeError at the call."""
    end_sessions = getattr(user_service, "end_sessions", None)
    assert end_sessions is not None, "[new] user_service.end_sessions does not exist: nothing raises an account's session version"
    shape = f"{'a coroutine function' if inspect.iscoroutinefunction(end_sessions) else 'a plain function'} of ({', '.join(inspect.signature(end_sessions).parameters)})"
    assert shape == "a coroutine function of (session, user)", f"red until A8a (A-34): end_sessions must be a coroutine function of (session, user), one SQL increment in the caller's transaction: it is {shape}"
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


# updated in A8a (A-34): end_sessions awaited, with the session. test_backup_apply.py's test (i) calls this helper too.
async def _end_sessions_of(engine: AsyncEngine, user_id: int) -> None:
    """end_sessions on the user, committed by its caller as the services that call it commit."""
    end_sessions = _end_sessions()
    async with AsyncSession(engine) as session:
        user = await session.get(User, user_id)
        assert user is not None, f"user {user_id} is not in the private database"
        await end_sessions(session, user)
        await session.commit()


async def _rows_seen_by(session: AsyncSession) -> dict[int, dict[str, Any]]:
    """Every column of every user, by id, as ``session``'s own transaction reads them — what it wrote, committed or not —,
    in the form of ``_user_rows``. A Core read on the session's connection, which flushes nothing: what is still pending
    on an object stays pending."""
    connection = await session.connection()
    rows = (await connection.execute(text("SELECT * FROM users"))).mappings().all()
    return {row["id"]: dict(row) for row in rows}


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


# red until A8a (A-34): it ends the sessions through _end_sessions_of, which awaits end_sessions(session, user)
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


# red until A8a (A-34): it ends the sessions through _end_sessions_of, which awaits end_sessions(session, user)
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


# updated in A8a (A-34)
# red until A8a (A-34)
@pytest.mark.asyncio
async def test_end_sessions_raises_the_version_by_one_and_leaves_the_commit_to_the_caller(engine: AsyncEngine) -> None:
    """Contract 5 — updated in A8a (A-34), red until A8a (end_sessions is a plain function of ``(user)``: its shape fails in
    ``_end_sessions``). A coroutine function of ``(session, user)`` answering None, whose increment is in the caller's
    transaction at once: that transaction reads the account's version one higher, and nothing else of anybody changed;
    ``user.session_version`` holds it, set as committed, so the version alone does not mark the object changed. Nothing
    is committed: a fresh connection still reads the old version, and a rollback leaves it there. The caller's commit
    stores it, for that account only, and ``user.session_version`` is then the stored version."""
    print_section("Contract 5: end_sessions")
    end_sessions = _end_sessions()
    user_id = await _add_user(engine, "gus", version=4)
    await _add_user(engine, "hana", version=2)
    rows = await _user_rows(engine)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        assert user is not None, "gus is in the private database"
        assert await end_sessions(session, user) is None, "end_sessions answers None"
        assert user.session_version == 5, f"user.session_version must hold the new version at once: {user.session_version}"
        assert user not in session.dirty, f"the version alone must not mark gus changed: set as committed (set_committed_value), its increment is already in the transaction; history of session_version: {get_history(user, 'session_version')}"
        assert await _rows_seen_by(session) == {**rows, user_id: {**rows[user_id], "session_version": 5}}, "the increment must be in the caller's transaction at once, written by end_sessions itself: gus's version one higher, nothing else of anybody"
        assert await _versions(engine) == {"gus": 4, "hana": 2}, "end_sessions must not commit: a fresh connection still reads the old version; the caller commits, with the change that ends the sessions"
        await session.rollback()
    assert await _versions(engine) == {"gus": 4, "hana": 2}, "a rollback must leave the stored version as it was"

    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        assert user is not None, "gus is in the private database"
        await end_sessions(session, user)
        await session.commit()
    assert await _versions(engine) == {"gus": 5, "hana": 2}, "committed by the caller: gus one higher, nobody else"
    assert user.session_version == 5, f"after the caller's commit user.session_version must be the stored version: {user.session_version}"
    print_success("4 → 5 in the caller's transaction, the object not marked changed, rolled back, then committed by the caller")


# red until A8a (A-34)
@pytest.mark.asyncio
async def test_end_sessions_leaves_what_the_caller_set_before_to_the_callers_commit(engine: AsyncEngine) -> None:
    """Contract 5 — NEW in A8a (A-34), red until A8a (the shape, in ``_end_sessions``). What the caller set on the user
    before ending its sessions — a new hash, as a password change does — is neither written by end_sessions nor lost: in
    the caller's transaction the row has the version one higher and still the old hash, the new hash is still pending on
    the object, and the version is not among its changes; the caller's commit writes the two. end_sessions writes the
    version alone and touches nothing else of the object: no flush, which would write the caller's hash before its
    commit, no refresh, which flushes first or throws pending values away."""
    print_section("Contract 5: end_sessions beside a change the caller has not written yet")
    end_sessions = _end_sessions()
    user_id = await _add_user(engine, "ines", version=3)
    await _add_user(engine, "jon", version=7)
    rows = await _user_rows(engine)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = await session.get(User, user_id)
        assert user is not None, "ines is in the private database"
        user.hashed_password = STAND_IN_HASH
        await end_sessions(session, user)
        assert await _rows_seen_by(session) == {**rows, user_id: {**rows[user_id], "session_version": 4}}, "end_sessions must write the version alone: in the caller's transaction ines's version is one higher and her hash still the old one"
        assert user.hashed_password == STAND_IN_HASH and list(get_history(user, "hashed_password").added) == [STAND_IN_HASH], f"the new hash must stay pending on the object, for the caller's commit: {get_history(user, 'hashed_password')}"
        assert user.session_version == 4 and not get_history(user, "session_version").has_changes(), f"the version must be set as committed, at its new value: {user.session_version}, history {get_history(user, 'session_version')}"
        await session.commit()
    assert await _user_rows(engine) == {**rows, user_id: {**rows[user_id], "hashed_password": STAND_IN_HASH, "session_version": 4}}, "the caller's commit must write the new hash and the version one higher, and nothing else of anybody"
    print_success("3 → 4 by end_sessions, the new hash left pending, both written by the caller's commit")


# red until A8a (A-34)
@pytest.mark.asyncio
async def test_two_requests_ending_the_same_accounts_sessions_raise_its_version_by_two(engine: AsyncEngine) -> None:
    """Contract 5, A-34 — NEW in A8a, red until A8a (the shape, in ``_end_sessions``; behind it, the increment of the object
    stores v+1). Workstream E's race: two requests load the same account at version v before either commits — the user
    changing the password, an administrator signing the account out everywhere —, two sessions on two connections to the
    private file. The password change sets a new hash, ends the sessions, commits and re-issues its device's cookie at
    ``user.session_version``, as ``POST /auth/change-password`` does; then the «sign out everywhere» ends them from the
    account as it loaded it before, and commits. Each ends every session issued before it: the stored version is v+2,
    the second request writes nothing else, its ``user.session_version`` is the stored one, and the cookie re-issued
    between the two is refused. Raised on the object, both stored v+1 and that cookie survived the «sign out
    everywhere». The order is set, not raced: both accounts loaded, then the first request's call and commit, then the
    second's. Nobody else's version moves."""
    print_section("Contract 5, A-34: two requests end the same account's sessions")
    end_sessions = _end_sessions()
    user_id = await _add_user(engine, "kim", version=6)
    await _add_user(engine, "lou", version=1)

    async with AsyncSession(engine, expire_on_commit=False) as password_change, AsyncSession(engine, expire_on_commit=False) as sign_out:
        changing = await password_change.get(User, user_id)
        signing_out = await sign_out.get(User, user_id)
        assert changing is not None and signing_out is not None, "kim is in the private database"
        assert (changing.session_version, signing_out.session_version) == (6, 6), "barrier: both requests loaded kim at version 6, before either committed"

        changing.hashed_password = STAND_IN_HASH
        await end_sessions(password_change, changing)
        await password_change.commit()
        reissued = auth_service.create_jwt_token(user_id=user_id, ttl_hours=1, session_version=changing.session_version)
        between = await _user_rows(engine)
        assert await _versions(engine) == {"kim": 7, "lou": 1}, "barrier: the password change is committed, kim at version 7"
        assert _signed_in_as(await _current_user(engine, reissued), user_id), "barrier: the cookie the password change re-issued signs kim in"

        await end_sessions(sign_out, signing_out)
        await sign_out.commit()

    versions = await _versions(engine)
    assert versions == {"kim": 8, "lou": 1}, f"red until A8a (A-34): the «sign out everywhere» must raise kim's version once more, to 8 — the increment of the account it loaded at 6 stores 7 a second time: {versions}"
    assert await _user_rows(engine) == {**between, user_id: {**between[user_id], "session_version": 8}}, "the second request must write kim's version alone: nothing it loaded before the password change, nothing of anybody else"
    assert signing_out.session_version == 8, f"the second request's user must hold the stored version, the one a cookie it re-issued would carry: {signing_out.session_version}"
    outcome = await _current_user(engine, reissued)
    assert _refusal(outcome) == SESSION_EXPIRED, f"the cookie the password change re-issued must not survive the «sign out everywhere» that followed it: {_describe(outcome)}"
    latest = await _current_user(engine, auth_service.create_jwt_token(user_id=user_id, ttl_hours=1, session_version=signing_out.session_version))
    assert _signed_in_as(latest, user_id), f"a cookie at the stored version must sign kim in: {_describe(latest)}"
    print_success("6 → 7 → 8: the cookie re-issued at 7 refused after the «sign out everywhere», 8 signs in")


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


# =============================================================================
# 7. A-27: THE LIVE RESET LINKS END WITH THE PASSWORD OR THE ADDRESS
# =============================================================================


@dataclasses.dataclass(frozen=True)
class _Link:
    """A link of contract 7's database: the token its holder has, the id of its row, and what it is for."""

    token: str
    token_id: int
    purpose: AccountTokenPurpose


#: The account's live reset links, those a real change of its password or of its address must revoke: the one it asked
#: for («forgot password») and one an administrator issued.
LIVE_RESET_LINKS = ("asked-for-by-the-account", "issued-by-an-administrator")
#: What every link of contract 7's database is worth before any change, by label. Those after the first two stay as they
#: are whatever the change: the account's reset links already spent and already revoked, its live links of the other
#: purposes, an invitation it issued, and another account's live reset link — but ITS_ADMIN_SETUP, since A7b-2.
LINKS_BEFORE: dict[str, TokenStatus] = {
    "asked-for-by-the-account": TokenStatus.VALID,
    "issued-by-an-administrator": TokenStatus.VALID,
    "already-spent": TokenStatus.CONSUMED,
    "already-revoked": TokenStatus.REVOKED,
    "its-email-verification": TokenStatus.VALID,
    "its-admin-setup": TokenStatus.VALID,
    "an-invitation-it-issued": TokenStatus.VALID,
    "another-accounts-reset-link": TokenStatus.VALID,
}
# updated in A7b-2 (A-32/A-33)
#: The account's admin setup link, which a real change moves by design since A7b-2, on every account — retired by a
#: password set, revoked by a new address —: left out of the «every other link as it was» guard of a real change, and
#: asserted on its own (``_assert_its_admin_setup``). A change that keeps the address, or a refused one, still leaves it.
ITS_ADMIN_SETUP = "its-admin-setup"


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: Any) -> _Link:
    """A link issued by token_service.issue_token on the private database, committed as a route or the CLI commits it."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, purpose, **arguments)
        await session.commit()
    return _Link(token=issued.token, token_id=issued.record.id, purpose=purpose)


async def _link_statuses(engine: AsyncEngine, links: dict[str, _Link]) -> dict[str, TokenStatus]:
    """What token_service.inspect_token says of each link now, by label, in a fresh session."""
    async with AsyncSession(engine) as session:
        return {label: (await token_service.inspect_token(session, link.token, link.purpose)).status for label, link in links.items()}


async def _link_moments(engine: AsyncEngine) -> dict[int, tuple[Any, Any]]:
    """{token id: (consumed_at, revoked_at)} of every account token of the private database, as a fresh connection reads it: what is committed."""
    async with engine.connect() as connection:
        rows = (await connection.execute(text("SELECT id, consumed_at, revoked_at FROM account_tokens"))).tuples().all()
    return {token_id: (consumed_at, revoked_at) for token_id, consumed_at, revoked_at in rows}


async def _profiles(engine: AsyncEngine) -> dict[int, tuple[str, str, int]]:
    """{user id: (username, email, session_version)} of every user of the private database, as a fresh connection reads it."""
    async with engine.connect() as connection:
        rows = (await connection.execute(text("SELECT id, username, email, session_version FROM users"))).tuples().all()
    return {user_id: (username, email, version) for user_id, username, email, version in rows}


async def _user_rows(engine: AsyncEngine) -> dict[int, dict[str, Any]]:
    """Every column of every user of the private database, by id, as a fresh connection reads it: «nothing written», to the letter."""
    async with engine.connect() as connection:
        rows = (await connection.execute(text("SELECT * FROM users"))).mappings().all()
    return {row["id"]: dict(row) for row in rows}


async def _account_with_links(engine: AsyncEngine, username: str) -> tuple[int, dict[str, _Link]]:
    """``username`` (version 2) with every link of LINKS_BEFORE, beside ``zack`` (version 5) and ``root``, an administrator:
    the account's id and its links by label, all committed, each checked to be worth what LINKS_BEFORE says.

    Every link was issued five minutes ago, so a reset link has 25 minutes left and the others longer. The spent one was
    consumed a minute later, the revoked one revoked two minutes later: moments of their own, which a second revocation
    would overwrite.
    """
    user_id = await _add_user(engine, username, version=2)
    other_id = await _add_user(engine, "zack", version=5)
    admin_id = await _add_user(engine, "root", version=1, admin=True)
    issued_at = utcnow() - timedelta(minutes=5)
    reset = AccountTokenPurpose.PASSWORD_RESET
    links = {
        "asked-for-by-the-account": await _issue(engine, reset, user_id=user_id, now=issued_at),
        "issued-by-an-administrator": await _issue(engine, reset, user_id=user_id, created_by_user_id=admin_id, now=issued_at),
        "already-spent": await _issue(engine, reset, user_id=user_id, now=issued_at),
        "already-revoked": await _issue(engine, reset, user_id=user_id, created_by_user_id=admin_id, now=issued_at),
        "its-email-verification": await _issue(engine, AccountTokenPurpose.EMAIL_VERIFICATION, user_id=user_id, now=issued_at),
        "its-admin-setup": await _issue(engine, AccountTokenPurpose.ADMIN_SETUP, user_id=user_id, now=issued_at),
        "an-invitation-it-issued": await _issue(engine, AccountTokenPurpose.INVITE, email="guest@example.test", created_by_user_id=user_id, now=issued_at),
        "another-accounts-reset-link": await _issue(engine, reset, user_id=other_id, now=issued_at),
    }
    async with AsyncSession(engine) as session:
        spent = await token_service.consume_token(session, links["already-spent"].token, reset, now=issued_at + timedelta(minutes=1)) is not None
        revoked = await token_service.revoke_tokens(session, token_id=links["already-revoked"].token_id, now=issued_at + timedelta(minutes=2))
        await session.commit()
    assert spent and revoked == 1, f"setup: one reset link spent, one revoked: spent {spent}, revoked {revoked}"
    statuses = await _link_statuses(engine, links)
    assert statuses == LINKS_BEFORE, f"barrier: before any change every link is worth what it was written to be: {statuses}"
    return user_id, links


async def _assert_only_the_live_reset_links_revoked(engine: AsyncEngine, links: dict[str, _Link], before: dict[int, tuple[Any, Any]], change: str) -> None:
    """After a real change of the password or the address. First the GUARD: no link added or deleted, every other link as it
    was, its moments included — but ITS_ADMIN_SETUP, which moves by design since A7b-2 and which the caller asserts on its
    own (``_assert_its_admin_setup``). Last the contract, red until A-27: each live reset link of the account revoked — its
    row has a revoked_at and inspect_token says so."""
    after = await _link_moments(engine)
    assert after.keys() == before.keys(), f"{change} must neither add nor delete a link: token ids {sorted(before)} → {sorted(after)}"
    # updated in A7b-2 (A-32/A-33): ITS_ADMIN_SETUP leaves this guard, its caller asserts its new state
    moved = {label: (before[link.token_id], after[link.token_id]) for label, link in links.items() if label not in (*LIVE_RESET_LINKS, ITS_ADMIN_SETUP) and after[link.token_id] != before[link.token_id]}
    assert not moved, f"{change} must leave every other link as it was — the account's links of the other purposes, its reset links already spent or revoked with their own moments, another account's link —: (consumed_at, revoked_at) before → after {moved}"
    statuses = await _link_statuses(engine, links)
    live = {label: (statuses[label], after[links[label].token_id][1] is not None) for label in LIVE_RESET_LINKS}
    revoked = dict.fromkeys(LIVE_RESET_LINKS, (TokenStatus.REVOKED, True))
    assert live == revoked, f"red until A-27: {change} must revoke, in its commit, every live reset link of the account, whoever issued it — a link asked for before the change still opens the account after it: (status, revoked_at set) {live}"


async def _assert_no_link_moved(engine: AsyncEngine, links: dict[str, _Link], before: dict[int, tuple[Any, Any]], change: str) -> None:
    """After a change that must revoke nothing: every row of account_tokens as it was, and every link worth what it was, the account's live reset links valid."""
    after = await _link_moments(engine)
    assert after == before, f"{change} must revoke no link: (consumed_at, revoked_at) by token id, {before} → {after}"
    statuses = await _link_statuses(engine, links)
    assert statuses == LINKS_BEFORE, f"{change} must leave every link worth what it was, the account's live reset links valid: {statuses}"


# updated in A7b-2 (A-32/A-33)
async def _assert_its_admin_setup(engine: AsyncEngine, links: dict[str, _Link], window: tuple[datetime, datetime], *, retired: bool, change: str) -> None:
    """Lot A7b-2 (A-32/A-33), on every account, waiting for its setup or not: after a password set the account's admin setup
    link is retired — revoked and consumed at the change's moment, without a consumer —; after a real change of the address
    it is revoked at that moment, not consumed. Either way inspect_token says ``revoked``. ``window`` brackets the change:
    two readings of the clock around it, never a wait."""
    link = links[ITS_ADMIN_SETUP]
    async with AsyncSession(engine) as session:
        record = await session.get(AccountToken, link.token_id)
        assert record is not None, f"{ITS_ADMIN_SETUP} is not in the database"
        revoked_at, consumed_at, consumer = ensure_utc(record.revoked_at), ensure_utc(record.consumed_at), record.consumed_by_user_id
    status = (await _link_statuses(engine, {ITS_ADMIN_SETUP: link}))[ITS_ADMIN_SETUP]
    start, end = window
    what = "retired, revoked and consumed" if retired else "revoked, not consumed"
    assert status == TokenStatus.REVOKED, f"{change} must leave the account's admin setup link {what}: inspect_token says {status}"
    assert revoked_at is not None and start <= revoked_at <= end, f"{change} must revoke the account's admin setup link at the change's moment, within [{start}, {end}]: revoked_at {revoked_at}"
    if retired:
        assert consumed_at is not None and start <= consumed_at <= end, f"{change} must consume the account's admin setup link at the change's moment, within [{start}, {end}]: consumed_at {consumed_at}"
    else:
        assert consumed_at is None, f"{change} must revoke the account's admin setup link, not consume it: consumed_at {consumed_at}"
    assert consumer is None, f"{change} must leave the account's admin setup link without a consumer: consumed_by_user_id {consumer}"


# updated in A7b-2 (A-32/A-33)
@pytest.mark.asyncio
async def test_reset_password_revokes_the_accounts_live_reset_links(engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 7 — NEW, red until A-27 (both links stay valid): the CLI's ``user reset`` stores the new password and ends
    the account's sessions (contract 6: the barrier); its commit must also revoke every live reset link of the account, the
    one it asked for and the one an administrator issued. Nothing else moves, but the account's admin setup link: updated in
    A7b-2 (A-32), a password set retires it — revoked and consumed at the change's moment, without a consumer —, on every
    account, waiting for its setup or not (red until A7b-2). bcrypt is not under test: hash_password is a stand-in."""
    print_section("Contract 7: reset_password revokes the live reset links")
    monkeypatch.setattr(user_service, "hash_password", lambda password: STAND_IN_HASH)
    user_id, links = await _account_with_links(engine, "ivy")
    profiles, before = await _profiles(engine), await _link_moments(engine)

    started = utcnow()
    async with AsyncSession(engine) as session:
        outcome = await user_service.reset_password(session, "ivy", NEW_PASSWORD)
    ended = utcnow()

    assert outcome == (True, None), f"reset_password must succeed: {outcome}"
    assert (await _account(engine, "ivy")).hashed_password == STAND_IN_HASH, "barrier: the new password's hash is stored"
    username, email, version = profiles[user_id]
    assert await _profiles(engine) == {**profiles, user_id: (username, email, version + 1)}, "barrier: ivy's sessions end (contract 6), nobody else's"
    await _assert_only_the_live_reset_links_revoked(engine, links, before, "reset_password")
    await _assert_its_admin_setup(engine, links, (started, ended), retired=True, change="reset_password")
    print_success("ivy's two live reset links revoked, its admin setup link retired, every other link as it was")


#: Real changes of the address (contract 7), as (the account's username — its address is <username>@example.test —, the
#: new address): another mailbox, and the same one with a letter outside A–Z in capitals, which P18 compares as written.
REAL_ADDRESS_CHANGES: dict[str, tuple[str, str]] = {
    "another-address": ("ivy", "ivy.elsewhere@example.test"),
    "a-letter-outside-a-z-in-capitals": ("émile", "Émile@example.test"),
}


# updated in A7b-2 (A-32/A-33)
@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(REAL_ADDRESS_CHANGES))
async def test_a_real_change_of_the_address_revokes_the_accounts_live_reset_links(engine: AsyncEngine, case: str) -> None:
    """Contract 7 — NEW, red until A-27 (both links stay valid): ``update_profile`` to another address — behind ``PUT
    /auth/profile`` and the CLI's ``user set-email`` — stores it and ends the account's sessions (A6e: the barrier); its
    commit must also revoke every live reset link of the account: one the old mailbox asked for before the change no longer
    opens the account. Nothing else moves, but the account's admin setup link: updated in A7b-2 (A-33), a real change of the
    address revokes it at the change's moment — not consumed, without a consumer —, on every account, waiting for its
    setup or not (red until A7b-2)."""
    print_section(f"Contract 7: update_profile to another address ({case})")
    username, new_address = REAL_ADDRESS_CHANGES[case]
    user_id, links = await _account_with_links(engine, username)
    profiles, before = await _profiles(engine), await _link_moments(engine)
    old_address, version = profiles[user_id][1], profiles[user_id][2]
    assert not user_service.same_email(new_address, old_address), f"setup: {new_address} must be another address than {old_address}, under P18"

    started = utcnow()
    async with AsyncSession(engine) as session:
        user, error = await user_service.update_profile(session, user_id, email=new_address)
    ended = utcnow()

    assert user is not None and error is None, f"update_profile must accept {new_address}: {error}"
    assert await _profiles(engine) == {**profiles, user_id: (username, new_address, version + 1)}, "barrier: the new address stored and the account's sessions ended (A6e), nobody else's"
    await _assert_only_the_live_reset_links_revoked(engine, links, before, f"a real change of the address ({case})")
    await _assert_its_admin_setup(engine, links, (started, ended), retired=False, change=f"a real change of the address ({case})")
    print_success(f"{case}: the address changed, the two live reset links and the admin setup link revoked, every other link as it was")


#: Changes that keep the address (contract 7), as (the arguments of update_profile, the account's username and address
#: after): the own address in other A–Z capitals — the same address (P18's C5), its new form stored — and a new username.
CHANGES_THAT_KEEP_THE_ADDRESS: dict[str, tuple[dict[str, str], tuple[str, str]]] = {
    "the-own-address-in-capitals": ({"email": "IVY@example.test"}, ("ivy", "IVY@example.test")),
    "the-username-alone": ({"username": "ivy_renamed"}, ("ivy_renamed", "ivy@example.test")),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(CHANGES_THAT_KEEP_THE_ADDRESS))
async def test_a_change_that_keeps_the_address_revokes_no_reset_link(engine: AsyncEngine, case: str) -> None:
    """Contract 7 — GUARD, green today and after: the own address in other A–Z capitals is no change of address (P18), and
    a new username touches no address: the change is stored, no session ends, and no link moves — the account's live reset
    links stay valid."""
    print_section(f"Contract 7: update_profile keeps the address ({case})")
    arguments, (username, email) = CHANGES_THAT_KEEP_THE_ADDRESS[case]
    user_id, links = await _account_with_links(engine, "ivy")
    profiles, before = await _profiles(engine), await _link_moments(engine)

    async with AsyncSession(engine) as session:
        user, error = await user_service.update_profile(session, user_id, **arguments)

    assert user is not None and error is None, f"update_profile({arguments}) must succeed: {error}"
    assert await _profiles(engine) == {**profiles, user_id: (username, email, profiles[user_id][2])}, "barrier: the change stored, and no session ended, for anybody"
    await _assert_no_link_moved(engine, links, before, f"a change that keeps the address ({case})")
    print_success(f"{case}: stored, every link as it was")


#: Addresses another account holds (contract 7): zack's, as written and in other A–Z capitals — the same address (P18).
TAKEN_ADDRESSES: dict[str, str] = {
    "another-accounts-address": "zack@example.test",
    "another-accounts-address-in-capitals": "ZACK@example.test",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(TAKEN_ADDRESSES))
async def test_a_refused_change_of_the_address_revokes_no_reset_link_and_writes_nothing(engine: AsyncEngine, case: str) -> None:
    """Contract 7 — GUARD, green today and after: an address another account holds is refused, «Email already registered»,
    before anything is written: no user row changes and no link moves — the account's live reset links stay valid."""
    print_section(f"Contract 7: update_profile refused ({case})")
    user_id, links = await _account_with_links(engine, "ivy")
    users, before = await _user_rows(engine), await _link_moments(engine)

    async with AsyncSession(engine) as session:
        outcome = await user_service.update_profile(session, user_id, email=TAKEN_ADDRESSES[case])

    assert outcome == (None, "Email already registered"), f"{TAKEN_ADDRESSES[case]} is zack's address: update_profile must refuse it, got {outcome}"
    assert await _user_rows(engine) == users, "a refusal must write no user row"
    await _assert_no_link_moved(engine, links, before, f"a refused change of the address ({case})")
    print_success(f"{case}: refused, nothing written, every link as it was")
