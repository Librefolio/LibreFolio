"""``token_service``: the single-use account tokens of release 1.3 (plan phase01Accounts §4.4, lot A4).

Invitations, password resets, e-mail verification and the setup link of the first administrator all hand somebody a
secret inside a URL, and all need the same guarantees: only its hash is kept, it is good for one purpose, once, until it
expires or is revoked, and it never shows up in a log. ``token_service`` gives them those guarantees in one place. The
contract pinned here:

1. The vocabulary: ``AccountTokenPurpose`` and ``TokenStatus`` with their values; ``DEFAULT_TTL`` — invite 7 days,
   reset 30 minutes, setup 72 hours, e-mail verification 24 hours; ``hash_token``, the SHA-256 hex digest of the UTF-8
   token; ``token_path``, one front-end page per purpose with the token in the URL fragment (``#token=…``, encoded by
   ``urlencode``), never in the query string — a browser never sends the fragment, so the token stays out of the
   instance's access log and out of every proxy's (review of 15/10), and those pages are the API client's
   ``LINK_PAGES``, where a 401 does not go to the login (a guard, A7b); ``IssuedToken`` and ``TokenInspection``, frozen.
2. ``issue_token``: 256 random bits, URL-safe (43 characters); only the hash is stored; ``created_at`` is ``now`` and
   ``expires_at`` is ``now`` plus the purpose's TTL, or the one given, which must be positive. An invite belongs to
   nobody yet and may carry an e-mail, the admin role and its creator; the other purposes belong to a user and never
   grant admin. A refused issue leaves the caller's transaction as it was.
3. ``inspect_token`` answers for the purpose it is asked about only: another purpose's token is ``UNKNOWN`` without a
   record, like a token never issued — a reset token is not an invite. Then revoked, consumed, expired (at
   ``expires_at`` exactly, not a microsecond before), valid. It never writes.
4. ``consume_token`` is one conditional UPDATE: the first use gets the record, stamped with ``now`` and the consumer;
   any other — a second use, an expired, revoked, other-purpose or unknown token — gets ``None`` and changes nothing.
5. ``revoke_tokens`` revokes by id, or every pending token of a user, optionally of one purpose, and says how many;
   consumed and revoked tokens keep their timestamps; without an id or a user it refuses rather than revoke everything.
6. Transactions: the service flushes and never commits, so that consuming an invite and creating its user share the
   caller's transaction. A rollback undoes an issue, a consumption and a revocation.
7. Single use under concurrency: two sessions on two connections consume one token at the same time; exactly one wins.
8. The plaintext never reaches the logs, structlog or stdlib, nor any column of the database.
9. ``retire_tokens(session, *, user_id, purpose, now=None)`` (lot A7b-2, N60) ends one user's links of one purpose for
   good: each one not consumed — live, expired or already revoked — is consumed at ``now``, with no consumer, and
   revoked at ``now`` unless it already was (that first revocation keeps its moment); it says how many. The user's
   consumed tokens, its tokens of the other purposes and every other user's are untouched; a second call finds nothing;
   it flushes without committing. A retired token is ``REVOKED`` to ``inspect_token`` and refused by ``consume_token``.

Every database is a private file under ``tmp_path``, built by ``SQLModel.metadata.create_all`` (contract 5 of
``test_migration_005_release_1_3`` keeps that schema equal to the migrated one) and opened the way production opens its own:
``sqlite+aiosqlite``, NullPool — a session is a connection —, and the connect listener of ``backend.app.db.session``
(foreign keys, WAL, busy_timeout). No test reads the clock to decide anything: every call gets its ``now``, but for the
defaults, which are bracketed.

Red until ``AccountToken`` and ``token_service`` exist: the module does not import.

Red until lot A7b-2, contract 9: ``retire_tokens`` does not exist. It is read when each of its tests runs, so each fails
on its own, saying so, and the module still imports.
"""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import inspect
import logging
import re
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
import pytest_asyncio
import structlog
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import AccountToken, AccountTokenPurpose, User
from backend.app.services.accounts import token_service
from backend.app.services.accounts.token_service import (
    DEFAULT_TTL,
    IssuedToken,
    TokenInspection,
    TokenStatus,
    consume_token,
    hash_token,
    inspect_token,
    issue_token,
    revoke_tokens,
    token_path,
)
from backend.app.utils.datetime_utils import ensure_utc, utcnow
from backend.test_scripts.test_utils import print_section, print_success

INVITE = AccountTokenPurpose.INVITE
PASSWORD_RESET = AccountTokenPurpose.PASSWORD_RESET
EMAIL_VERIFICATION = AccountTokenPurpose.EMAIL_VERIFICATION
ADMIN_SETUP = AccountTokenPurpose.ADMIN_SETUP
USER_PURPOSES = (PASSWORD_RESET, EMAIL_VERIFICATION, ADMIN_SETUP)

NOW = datetime(2026, 10, 15, 9, 30, 0, 123456, tzinfo=UTC)
MICROSECOND = timedelta(microseconds=1)
# secrets.token_urlsafe(32): 32 random bytes, base64url without padding.
URL_SAFE_256_BITS = re.compile(r"[A-Za-z0-9_-]{43}")
NEVER_ISSUED = "never-issued-0123456789abcdefghijklmnopqrst"
SAMPLE_TOKEN = "Zm9v_YmFy-0123456789abcdefghijklmnopqrstuv"
TOKEN_SERVICE_LOGGER = "backend.app.services.accounts.token_service"
CANARY = "canary: the capture reaches the token service's logger"


# =============================================================================
# FIXTURES AND HELPERS
# =============================================================================


@pytest_asyncio.fixture
async def engine(tmp_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file under tmp_path with the whole ORM schema, opened as production opens its own, disposed at teardown."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'tokens.db'}", poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def users(engine: AsyncEngine) -> dict[str, int]:
    """Three users of the private database, by name: the owners, creators and consumers the foreign keys need."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        created = {name: User(username=name, email=f"{name}@example.test", hashed_password="$argon2id$test") for name in ("alice", "bob", "carol")}
        session.add_all(created.values())
        await session.commit()
    return {name: user.id for name, user in created.items()}


def _owner(purpose: AccountTokenPurpose, users: dict[str, int]) -> Optional[int]:
    """Whom a token of ``purpose`` belongs to here: nobody for an invite, alice otherwise."""
    return None if purpose == INVITE else users["alice"]


def _another(purpose: AccountTokenPurpose) -> AccountTokenPurpose:
    return next(other for other in AccountTokenPurpose if other != purpose)


async def _issue(engine: AsyncEngine, purpose: AccountTokenPurpose, **arguments: Any) -> IssuedToken:
    """``issue_token`` in a session of its own, committed afterwards — the service never commits, its caller does."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, **arguments)
        await session.commit()
    return issued


async def _inspect(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose, **arguments: Any) -> TokenInspection:
    """``inspect_token`` in a session of its own, committed afterwards: whatever it wrote would stay."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        inspection = await inspect_token(session, token, purpose, **arguments)
        await session.commit()
    return inspection


async def _consume(engine: AsyncEngine, token: str, purpose: AccountTokenPurpose, **arguments: Any) -> Optional[AccountToken]:
    """``consume_token`` in a session of its own, committed afterwards."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        record = await consume_token(session, token, purpose, **arguments)
        await session.commit()
    return record


async def _revoke(engine: AsyncEngine, **arguments: Any) -> int:
    """``revoke_tokens`` in a session of its own, committed afterwards."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        revoked = await revoke_tokens(session, **arguments)
        await session.commit()
    return revoked


async def _record(engine: AsyncEngine, token_id: int) -> AccountToken:
    """The token as a fresh session reads it from the database."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        record = await session.get(AccountToken, token_id)
    assert record is not None, f"token {token_id} is not in the database"
    return record


async def _stored(engine: AsyncEngine, token_id: int) -> dict[str, Any]:
    """The row of ``token_id`` exactly as SQLite holds it: raw values, no ORM in between."""
    async with engine.connect() as connection:
        row = (await connection.execute(text("SELECT * FROM account_tokens WHERE id = :id"), {"id": token_id})).mappings().one_or_none()
    assert row is not None, f"token {token_id} is not in the database"
    return dict(row)


async def _tokens_in(session: AsyncSession) -> int:
    """How many tokens ``session`` sees, its own pending writes included (the query autoflushes them)."""
    return (await session.execute(select(func.count()).select_from(AccountToken))).scalar_one()


async def _plaintext_in_database(engine: AsyncEngine, plaintexts: list[str]) -> list[str]:
    """``table.column`` of every value, in every table, that holds one of ``plaintexts``."""
    found: list[str] = []
    async with engine.connect() as connection:
        tables = (await connection.execute(text("SELECT name FROM sqlite_master WHERE type = 'table'"))).scalars().all()
        for table in tables:
            for row in (await connection.execute(text(f'SELECT * FROM "{table}"'))).mappings().all():
                found.extend(f"{table}.{column}" for column, value in row.items() if value is not None and any(plaintext in str(value) for plaintext in plaintexts))
    return found


# =============================================================================
# 1. THE VOCABULARY
# =============================================================================


def test_the_purposes_and_the_statuses_have_their_values() -> None:
    """Contract 1: the four purposes and the five statuses, as StrEnums with lowercase values — the values are what the database stores and the API speaks."""
    print_section("Contract 1: purposes and statuses")

    assert issubclass(AccountTokenPurpose, StrEnum) and issubclass(TokenStatus, StrEnum)
    assert {purpose.name: purpose.value for purpose in AccountTokenPurpose} == {
        "INVITE": "invite",
        "PASSWORD_RESET": "password_reset",
        "EMAIL_VERIFICATION": "email_verification",
        "ADMIN_SETUP": "admin_setup",
    }
    assert {status.name: status.value for status in TokenStatus} == {
        "VALID": "valid",
        "EXPIRED": "expired",
        "CONSUMED": "consumed",
        "REVOKED": "revoked",
        "UNKNOWN": "unknown",
    }
    print_success("4 purposes, 5 statuses")


def test_each_purpose_has_its_default_ttl() -> None:
    """Contract 1: invite 7 days, password reset 30 minutes, admin setup 72 hours, e-mail verification 24 hours — and no purpose without one."""
    print_section("Contract 1: DEFAULT_TTL")

    assert DEFAULT_TTL == {
        INVITE: timedelta(days=7),
        PASSWORD_RESET: timedelta(minutes=30),
        ADMIN_SETUP: timedelta(hours=72),
        EMAIL_VERIFICATION: timedelta(hours=24),
    }
    print_success("one TTL per purpose")


def test_hash_token_is_the_sha256_hex_digest_of_the_utf8_token() -> None:
    """Contract 1: 64 lowercase hex characters, the SHA-256 of the UTF-8 bytes; ``abc`` is the FIPS 180-2 test vector."""
    print_section("Contract 1: hash_token")

    assert hash_token("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    for token in (SAMPLE_TOKEN, "pässwörd-€"):
        assert hash_token(token) == hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert re.fullmatch(r"[0-9a-f]{64}", hash_token(token))
    print_success("SHA-256 hex of the UTF-8 token")


@pytest.mark.parametrize(
    ("purpose", "page"),
    [(INVITE, "/invite"), (PASSWORD_RESET, "/reset-password"), (ADMIN_SETUP, "/setup"), (EMAIL_VERIFICATION, "/verify-email")],
)
def test_token_path_sends_each_purpose_to_its_page_with_the_token_in_the_fragment(purpose: AccountTokenPurpose, page: str) -> None:
    """Contract 1 (review of 15/10): ``token_path`` is the page of the purpose with the token in the URL fragment, ``#token=…``, and no query string.

    A browser never sends the fragment of a URL to the server: whoever opens the link, the token reaches neither the
    instance's access log nor a proxy's on the way. A token in the query string reaches both.
    """
    print_section(f"Contract 1: token_path({purpose.value})")
    path = token_path(purpose, SAMPLE_TOKEN)
    parts = urlsplit(path)

    assert (parts.path, parts.query) == (page, ""), f"the token must not travel in the query string, which the server and every proxy log: {path!r}"
    assert parse_qs(parts.fragment) == {"token": [SAMPLE_TOKEN]}, f"the token must travel in the fragment, as its 'token' field: {path!r}"
    assert path == f"{page}#token={SAMPLE_TOKEN}"
    print_success(f"{purpose.value} → {page}#token=…")


def test_token_path_encodes_the_token_in_the_fragment_as_urlencode_does() -> None:
    """Contract 1 (review of 15/10): the fragment is ``urlencode({'token': token})``, so a token holding characters that mean something in a URL (``+``, a space, ``&``, ``=``, ``/``, ``#``, a non-ASCII letter) comes back intact from the fragment, read as form fields — as the page reads it.

    Real tokens are URL-safe base64 and never need it; the encoding is pinned so that the page and the service cannot drift.
    """
    print_section("Contract 1: token_path encodes the token")
    odd = "a+b c&d=e/é#f"
    path = token_path(INVITE, odd)
    parts = urlsplit(path)

    assert (parts.path, parts.query) == ("/invite", ""), f"the token must not travel in the query string: {path!r}"
    assert parse_qs(parts.fragment) == {"token": [odd]}, f"the fragment must give the token back intact: {path!r}"
    assert path == "/invite#" + urlencode({"token": odd})
    print_success("the fragment gives the token back intact")


# The guard of A7b (review by H): the API client's LINK_PAGES and the pages of token_path (_TOKEN_PATHS) are one list
# written twice, once in TypeScript and once in Python. The TS file is read as text, never run.
REPO_ROOT = Path(__file__).resolve().parents[3]
API_CLIENT_FILE = "frontend/src/lib/api/zodios-client.ts"
TOKEN_SERVICE_FILE = "backend/app/services/accounts/token_service.py"
LINK_PAGES_DECLARATION = re.compile(r"\b(?:const|let|var)\s+LINK_PAGES\b")
# The one form the guard reads: a literal Set of strings, exported and typed or not, on one line or wrapped by Prettier.
LINK_PAGES_LITERAL = re.compile(r"\b(?:const|let|var)\s+LINK_PAGES\b[^=;]*=\s*new\s+Set\s*(?:<[^>]*>)?\(\s*\[(?P<entries>[^\]]*)\]\s*\)\s*;")
QUOTED_PAGE = re.compile(r"""(?P<quote>['"])(?P<page>[^'"\n]*)(?P=quote)""")
# Synthetic declarations, with the entries the parser must give back: exactly those, in that order.
LINK_PAGES_READ = [
    # as zodios-client.ts writes it today, between a comment and a use of the set that declares nothing
    ("// The pages of a link.\nconst LINK_PAGES = new Set(['/setup', '/invite', '/reset-password', '/verify-email']);\nreturn LINK_PAGES.has(path);", ["/setup", "/invite", "/reset-password", "/verify-email"]),
    # double quotes, exported and typed, wrapped by Prettier with its trailing comma
    ('export const LINK_PAGES: ReadonlySet<string> = new Set<string>([\n    "/invite",\n    "/setup",\n]);', ["/invite", "/setup"]),
]
# Synthetic declarations the parser must refuse rather than guess at, with the reason it gives.
LINK_PAGES_REFUSED = [
    ("const PAGES = new Set(['/setup']);", "0 declarations of LINK_PAGES"),
    ("const LINK_PAGES = new Set(['/setup']);\nlet LINK_PAGES = new Set(['/invite']);", "2 declarations of LINK_PAGES"),
    ("const LINK_PAGES = new Set(PAGES);", "not a literal"),
    ("const LINK_PAGES = new Set(['/setup', SETUP_PAGE]);", "not a quoted string"),
]


def _link_pages(source: str) -> list[str]:
    """The entries of the one ``LINK_PAGES`` declaration in a TS source, in order; ``ValueError`` on anything the guard does not read."""
    declarations = len(LINK_PAGES_DECLARATION.findall(source))
    if declarations != 1:
        raise ValueError(f"{declarations} declarations of LINK_PAGES: the guard reads exactly one")
    literal = LINK_PAGES_LITERAL.search(source)
    if literal is None:
        raise ValueError("LINK_PAGES is not a literal new Set([...]) of strings: the guard reads only that form")
    listed = literal["entries"].strip().removesuffix(",")  # the trailing comma Prettier adds to a list it wraps
    if not listed:
        return []
    entries = []
    for item in listed.split(","):
        quoted = QUOTED_PAGE.fullmatch(item.strip())
        if quoted is None:
            raise ValueError(f"LINK_PAGES holds {item.strip()!r}, not a quoted string: the guard reads only string literals")
        entries.append(quoted["page"])
    return entries


def _link_page_drift(link_pages: set[str], token_pages: set[str]) -> tuple[list[str], list[str]]:
    """``(the pages a link opens that LINK_PAGES lacks, the LINK_PAGES no link opens)``: ``([], [])`` when the two lists agree."""
    return sorted(token_pages - link_pages), sorted(link_pages - token_pages)


def test_token_path_pages_are_the_link_pages_of_the_api_client() -> None:
    """Contract 1, a guard — green on arrival, the two lists agree today (A7b, review by H): the pages ``token_path`` sends a link to are exactly ``LINK_PAGES``, the pages where the API client lets a 401 through instead of going to the login.

    On a 401 the client goes to the login, except on the anonymous page a link opens: there the 401 is the instance's
    block, which the page receives, and a trip to the login would lose the token in the URL fragment (backlog A-13).
    Those pages are written twice, in two languages: ``LINK_PAGES`` in ``frontend/src/lib/api/zodios-client.ts`` and
    ``_TOKEN_PATHS`` in ``backend/app/services/accounts/token_service.py``, read here through ``token_path``. A page added
    to one list only is a link whose token a 401 throws away.

    Barriers first, so that the equality cannot pass on nothing: the parser gives back exactly the entries of synthetic
    declarations — today's, one in double quotes, one a page short for each page — and refuses what it does not read;
    the comparison names a page short and a page more, each on its side; the real file gives at least one entry, each a
    path, none twice.
    """
    print_section("Contract 1 (guard): the pages of token_path are the API client's LINK_PAGES")
    token_pages = {urlsplit(token_path(purpose, SAMPLE_TOKEN)).path for purpose in AccountTokenPurpose}

    for snippet, entries in LINK_PAGES_READ:
        assert _link_pages(snippet) == entries, f"the parser misreads {snippet!r}"
    for snippet, reason in LINK_PAGES_REFUSED:
        with pytest.raises(ValueError, match=reason):
            _link_pages(snippet)
    for dropped in sorted(token_pages):
        short = sorted(token_pages - {dropped})
        listed = ", ".join(f"'{page}'" for page in short)
        assert _link_pages(f"const LINK_PAGES = new Set([{listed}]);") == short, f"the parser misreads a LINK_PAGES without {dropped}"
        assert _link_page_drift(set(short), token_pages) == ([dropped], []), f"the comparison must name {dropped}, missing from LINK_PAGES"
    assert _link_page_drift(token_pages | {"/elsewhere"}, token_pages) == ([], ["/elsewhere"]), "the comparison must name a page only LINK_PAGES has"

    link_pages = _link_pages((REPO_ROOT / API_CLIENT_FILE).read_text(encoding="utf-8"))
    assert link_pages, f"LINK_PAGES in {API_CLIENT_FILE} is empty: nothing to compare"
    assert all(page.startswith("/") for page in link_pages), f"LINK_PAGES in {API_CLIENT_FILE} holds something that is not a path: {link_pages}"
    assert len(set(link_pages)) == len(link_pages), f"LINK_PAGES in {API_CLIENT_FILE} lists a page twice: {link_pages}"

    missing, extra = _link_page_drift(set(link_pages), token_pages)
    assert (missing, extra) == ([], []), (
        f"LINK_PAGES ({API_CLIENT_FILE}) and the pages of token_path (_TOKEN_PATHS, {TOKEN_SERVICE_FILE}) differ; a link page belongs in both or in neither.\n"
        f"  missing from LINK_PAGES: {missing} — a 401 there sends the browser to the login, and the token in the fragment is lost\n"
        f"  missing from _TOKEN_PATHS: {extra} — a 401 there never goes to the login, yet no link opens the page"
    )
    print_success(f"{len(link_pages)} link pages, the same in both files: {', '.join(sorted(link_pages))}")


def test_the_results_are_frozen_dataclasses() -> None:
    """Contract 1: ``IssuedToken(token, record)`` and ``TokenInspection(status, record)``, frozen: a result is not something to edit."""
    print_section("Contract 1: IssuedToken and TokenInspection")

    assert [field.name for field in dataclasses.fields(IssuedToken)] == ["token", "record"]
    assert [field.name for field in dataclasses.fields(TokenInspection)] == ["status", "record"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        IssuedToken(token=SAMPLE_TOKEN, record=None).token = NEVER_ISSUED  # type: ignore[arg-type,misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        TokenInspection(status=TokenStatus.UNKNOWN, record=None).status = TokenStatus.VALID  # type: ignore[misc]
    print_success("two frozen dataclasses")


# =============================================================================
# 2. ISSUE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", list(AccountTokenPurpose))
async def test_issue_stores_only_the_hash_and_dates_the_token(engine: AsyncEngine, users: dict[str, int], purpose: AccountTokenPurpose) -> None:
    """Contract 2: a 43-character URL-safe secret; the row holds its hash, the purpose and the owner, ``created_at = now`` and ``expires_at = now + DEFAULT_TTL``, nothing consumed or revoked.

    The record has its id before the caller commits: the service flushes.
    """
    print_section(f"Contract 2: issue {purpose.value}")
    owner = _owner(purpose, users)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await issue_token(session, purpose, user_id=owner, now=NOW)
        flushed_id = issued.record.id
        await session.commit()

    assert URL_SAFE_256_BITS.fullmatch(issued.token), f"expected secrets.token_urlsafe(32), got {len(issued.token)} characters"
    assert flushed_id is not None, "issue_token must flush: the caller needs the id inside its own transaction"
    stored = await _record(engine, flushed_id)
    assert stored.token_hash == hash_token(issued.token)
    assert (stored.purpose, stored.user_id, bool(stored.grants_admin), stored.email, stored.created_by_user_id) == (purpose, owner, False, None, None)
    assert (ensure_utc(stored.created_at), ensure_utc(stored.expires_at)) == (NOW, NOW + DEFAULT_TTL[purpose])
    assert (stored.consumed_at, stored.revoked_at, stored.consumed_by_user_id) == (None, None, None)
    print_success(f"{purpose.value}: hash stored, dated {NOW.isoformat()} + {DEFAULT_TTL[purpose]}")


@pytest.mark.asyncio
async def test_every_issue_draws_a_new_secret(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 2: three invites issued at the same instant have three secrets and three hashes."""
    print_section("Contract 2: a new secret every time")

    issued = [await _issue(engine, INVITE, now=NOW) for _ in range(3)]

    assert len({token.token for token in issued}) == 3
    assert len({token.record.token_hash for token in issued}) == 3
    print_success("three secrets, three hashes")


@pytest.mark.asyncio
async def test_issue_without_now_dates_the_token_at_the_current_time(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 2: without ``now``, ``created_at`` is the current UTC time (bracketed by two readings, never waited for) and ``expires_at`` follows by the TTL."""
    print_section("Contract 2: issue without now")

    before = utcnow()
    issued = await _issue(engine, PASSWORD_RESET, user_id=users["alice"])
    after = utcnow()

    stored = await _record(engine, issued.record.id)
    created_at = ensure_utc(stored.created_at)
    assert before <= created_at <= after, f"created_at {created_at} outside [{before}, {after}]"
    assert ensure_utc(stored.expires_at) - created_at == DEFAULT_TTL[PASSWORD_RESET]
    print_success("dated now, expiring 30 minutes later")


@pytest.mark.asyncio
async def test_issue_with_a_ttl_uses_it(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 2: an explicit ``ttl`` replaces the purpose's default."""
    print_section("Contract 2: issue with a ttl")

    issued = await _issue(engine, INVITE, ttl=timedelta(hours=2), now=NOW)

    assert ensure_utc((await _record(engine, issued.record.id)).expires_at) == NOW + timedelta(hours=2)
    print_success("expires_at = now + ttl")


@pytest.mark.asyncio
@pytest.mark.parametrize("ttl", [timedelta(0), -MICROSECOND, timedelta(days=-7)], ids=["zero", "minus one microsecond", "minus seven days"])
async def test_issue_refuses_a_ttl_that_is_not_positive(engine: AsyncEngine, users: dict[str, int], ttl: timedelta) -> None:
    """Contract 2: a token that is born expired is a mistake of the caller: ValueError, and nothing added to the caller's transaction."""
    print_section(f"Contract 2: ttl {ttl} is refused")

    async with AsyncSession(engine) as session:
        with pytest.raises(ValueError):
            await issue_token(session, INVITE, ttl=ttl, now=NOW)
        assert await _tokens_in(session) == 0, "a refused issue must leave the caller's transaction as it was"
    print_success(f"ttl {ttl}: ValueError, nothing written")


@pytest.mark.asyncio
async def test_an_invite_carries_an_email_the_admin_role_and_its_creator(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 2: an invite stores the e-mail it is for, whether it grants admin, and who created it — and no owner."""
    print_section("Contract 2: an invite's fields")

    issued = await _issue(engine, INVITE, email="new@example.test", grants_admin=True, created_by_user_id=users["alice"], now=NOW)

    stored = await _record(engine, issued.record.id)
    assert (stored.user_id, stored.email, bool(stored.grants_admin), stored.created_by_user_id) == (None, "new@example.test", True, users["alice"])
    print_success("invite: e-mail, admin role and creator stored")


@pytest.mark.asyncio
async def test_an_invite_belongs_to_nobody_yet(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 2: an invite is for an account that does not exist yet: a ``user_id`` is a ValueError, and nothing is added."""
    print_section("Contract 2: an invite refuses a user_id")

    async with AsyncSession(engine) as session:
        with pytest.raises(ValueError):
            await issue_token(session, INVITE, user_id=users["alice"], now=NOW)
        assert await _tokens_in(session) == 0, "a refused issue must leave the caller's transaction as it was"
    print_success("invite with a user_id: ValueError")


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", USER_PURPOSES)
async def test_a_user_token_requires_its_user(engine: AsyncEngine, users: dict[str, int], purpose: AccountTokenPurpose) -> None:
    """Contract 2: a reset, a verification or a setup link without ``user_id`` is a ValueError, and nothing is added."""
    print_section(f"Contract 2: {purpose.value} requires a user")

    async with AsyncSession(engine) as session:
        with pytest.raises(ValueError):
            await issue_token(session, purpose, now=NOW)
        assert await _tokens_in(session) == 0, "a refused issue must leave the caller's transaction as it was"
    print_success(f"{purpose.value} without a user: ValueError")


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", USER_PURPOSES)
async def test_a_user_token_never_grants_admin(engine: AsyncEngine, users: dict[str, int], purpose: AccountTokenPurpose) -> None:
    """Contract 2: only an invite may grant the admin role: ``grants_admin=True`` on another purpose is a ValueError, and nothing is added."""
    print_section(f"Contract 2: {purpose.value} never grants admin")

    async with AsyncSession(engine) as session:
        with pytest.raises(ValueError):
            await issue_token(session, purpose, user_id=users["alice"], grants_admin=True, now=NOW)
        assert await _tokens_in(session) == 0, "a refused issue must leave the caller's transaction as it was"
    print_success(f"{purpose.value} with grants_admin: ValueError")


# =============================================================================
# 3. INSPECT
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", list(AccountTokenPurpose))
async def test_a_fresh_token_is_valid_and_inspecting_it_writes_nothing(engine: AsyncEngine, users: dict[str, int], purpose: AccountTokenPurpose) -> None:
    """Contract 3: a token just issued is ``VALID`` for its purpose, with its record; the row is the same afterwards."""
    print_section(f"Contract 3: a fresh {purpose.value} is valid")
    issued = await _issue(engine, purpose, user_id=_owner(purpose, users), now=NOW)
    before = await _stored(engine, issued.record.id)

    inspection = await _inspect(engine, issued.token, purpose, now=NOW)

    assert inspection.status == TokenStatus.VALID
    assert inspection.record is not None and inspection.record.id == issued.record.id
    assert await _stored(engine, issued.record.id) == before, "inspect_token must never write"
    print_success(f"{purpose.value}: VALID, row untouched")


@pytest.mark.asyncio
@pytest.mark.parametrize(("issued_for", "asked_for"), [(issued_for, asked_for) for issued_for in AccountTokenPurpose for asked_for in AccountTokenPurpose if issued_for != asked_for])
async def test_a_token_is_unknown_to_every_other_purpose(engine: AsyncEngine, users: dict[str, int], issued_for: AccountTokenPurpose, asked_for: AccountTokenPurpose) -> None:
    """Contract 3: a token is looked up for one purpose only: asked about any other, it is ``UNKNOWN`` and its record is not handed out."""
    print_section(f"Contract 3: a {issued_for.value} is not a {asked_for.value}")
    issued = await _issue(engine, issued_for, user_id=_owner(issued_for, users), now=NOW)
    assert (await _inspect(engine, issued.token, issued_for, now=NOW)).status == TokenStatus.VALID, "barrier: the token is valid for its own purpose"

    inspection = await _inspect(engine, issued.token, asked_for, now=NOW)

    assert (inspection.status, inspection.record) == (TokenStatus.UNKNOWN, None)
    print_success(f"{issued_for.value} asked as {asked_for.value}: UNKNOWN")


@pytest.mark.asyncio
async def test_a_token_never_issued_is_unknown(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 3: a string that was never issued is ``UNKNOWN`` for every purpose, beside one token that was."""
    print_section("Contract 3: a token never issued")
    await _issue(engine, INVITE, now=NOW)

    for purpose in AccountTokenPurpose:
        inspection = await _inspect(engine, NEVER_ISSUED, purpose, now=NOW)
        assert (inspection.status, inspection.record) == (TokenStatus.UNKNOWN, None), purpose
    print_success("never issued: UNKNOWN for every purpose")


@pytest.mark.asyncio
async def test_a_token_expires_at_its_expires_at_exactly(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 3: ``VALID`` a microsecond before ``expires_at``, ``EXPIRED`` at ``expires_at`` and after, with its record."""
    print_section("Contract 3: the expiry boundary")
    issued = await _issue(engine, PASSWORD_RESET, user_id=users["alice"], now=NOW)
    expires_at = NOW + DEFAULT_TTL[PASSWORD_RESET]
    before = await _stored(engine, issued.record.id)

    last_valid = await _inspect(engine, issued.token, PASSWORD_RESET, now=expires_at - MICROSECOND)
    first_expired = await _inspect(engine, issued.token, PASSWORD_RESET, now=expires_at)
    long_expired = await _inspect(engine, issued.token, PASSWORD_RESET, now=expires_at + timedelta(days=1))

    assert last_valid.status == TokenStatus.VALID
    for inspection in (first_expired, long_expired):
        assert inspection.status == TokenStatus.EXPIRED
        assert inspection.record is not None and inspection.record.id == issued.record.id
    assert await _stored(engine, issued.record.id) == before, "inspect_token must never write, not even to an expired token"
    print_success("valid at expires_at - 1 µs, expired at expires_at")


@pytest.mark.asyncio
async def test_a_consumed_or_revoked_token_says_so_even_once_expired(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 3: ``CONSUMED`` and ``REVOKED`` before and after the token's expiry: what happened to it outranks the calendar."""
    print_section("Contract 3: consumed and revoked")
    consumed = await _issue(engine, INVITE, now=NOW)
    revoked = await _issue(engine, INVITE, now=NOW)
    assert await _consume(engine, consumed.token, INVITE, consumed_by_user_id=users["bob"], now=NOW + timedelta(hours=1)) is not None, "barrier: the first use succeeds"
    assert await _revoke(engine, token_id=revoked.record.id, now=NOW + timedelta(hours=1)) == 1, "barrier: the revocation hits the token"

    for issued, status in ((consumed, TokenStatus.CONSUMED), (revoked, TokenStatus.REVOKED)):
        before = await _stored(engine, issued.record.id)
        for moment in (NOW + timedelta(hours=2), NOW + DEFAULT_TTL[INVITE] + timedelta(days=1)):
            inspection = await _inspect(engine, issued.token, INVITE, now=moment)
            assert inspection.status == status, f"at {moment}: {inspection.status}, expected {status}"
            assert inspection.record is not None and inspection.record.id == issued.record.id
        assert await _stored(engine, issued.record.id) == before, "inspect_token must never write"
    print_success("CONSUMED and REVOKED, before and after expiry")


# =============================================================================
# 4. CONSUME
# =============================================================================


@pytest.mark.asyncio
async def test_the_first_use_consumes_the_token_and_a_second_gets_nothing(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 4: the first use returns the record with ``consumed_at = now`` and the consumer; the second returns ``None`` and leaves the row as the first left it."""
    print_section("Contract 4: single use")
    issued = await _issue(engine, INVITE, now=NOW)
    first_use = NOW + timedelta(hours=1)

    record = await _consume(engine, issued.token, INVITE, consumed_by_user_id=users["bob"], now=first_use)

    assert record is not None and record.id == issued.record.id
    assert (ensure_utc(record.consumed_at), record.consumed_by_user_id) == (first_use, users["bob"])
    stored = await _record(engine, issued.record.id)
    assert (ensure_utc(stored.consumed_at), stored.consumed_by_user_id, stored.revoked_at) == (first_use, users["bob"], None)
    after_first_use = await _stored(engine, issued.record.id)

    assert await _consume(engine, issued.token, INVITE, consumed_by_user_id=users["carol"], now=first_use + timedelta(minutes=1)) is None
    assert await _stored(engine, issued.record.id) == after_first_use
    print_success("first use stamped, second use refused")


@pytest.mark.asyncio
async def test_consume_without_a_consumer(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 4: ``consumed_by_user_id`` is optional — a reset is used by its own owner — and ``consumed_at`` is stamped all the same."""
    print_section("Contract 4: consume without a consumer")
    issued = await _issue(engine, PASSWORD_RESET, user_id=users["alice"], now=NOW)

    record = await _consume(engine, issued.token, PASSWORD_RESET, now=NOW + timedelta(minutes=5))

    assert record is not None and record.consumed_by_user_id is None
    assert ensure_utc((await _record(engine, issued.record.id)).consumed_at) == NOW + timedelta(minutes=5)
    print_success("consumed, no consumer recorded")


@pytest.mark.asyncio
async def test_a_token_can_be_used_until_the_microsecond_before_it_expires(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 4: the condition is ``expires_at > now``: at ``expires_at - 1 µs`` the token is still good."""
    print_section("Contract 4: the last microsecond")
    issued = await _issue(engine, PASSWORD_RESET, user_id=users["alice"], now=NOW)
    last_moment = NOW + DEFAULT_TTL[PASSWORD_RESET] - MICROSECOND

    record = await _consume(engine, issued.token, PASSWORD_RESET, consumed_by_user_id=users["alice"], now=last_moment)

    assert record is not None and ensure_utc(record.consumed_at) == last_moment
    print_success("consumed at expires_at - 1 µs")


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["expired", "revoked", "another purpose", "never issued"])
async def test_consume_refuses_and_changes_nothing(engine: AsyncEngine, users: dict[str, int], case: str) -> None:
    """Contract 4: an expired token (at ``expires_at`` exactly), a revoked one, one asked for as an invite while it is a reset, a string never issued: ``None``, and the row is untouched."""
    print_section(f"Contract 4: consume refuses {case}")
    issued = await _issue(engine, PASSWORD_RESET, user_id=users["alice"], now=NOW)
    if case == "revoked":
        assert await _revoke(engine, token_id=issued.record.id, now=NOW + timedelta(minutes=1)) == 1, "barrier: the revocation hits the token"
    token = NEVER_ISSUED if case == "never issued" else issued.token
    purpose = INVITE if case == "another purpose" else PASSWORD_RESET
    moment = NOW + DEFAULT_TTL[PASSWORD_RESET] if case == "expired" else NOW + timedelta(minutes=5)
    before = await _stored(engine, issued.record.id)

    assert await _consume(engine, token, purpose, consumed_by_user_id=users["bob"], now=moment) is None
    assert await _stored(engine, issued.record.id) == before
    print_success(f"{case}: None, row untouched")


# =============================================================================
# 5. REVOKE
# =============================================================================


@pytest.mark.asyncio
async def test_revoke_by_id(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 5: by id, one token is revoked at ``now`` and the count is 1; its neighbour is not; a second revocation counts 0 and keeps the first timestamp."""
    print_section("Contract 5: revoke by id")
    invite = await _issue(engine, INVITE, created_by_user_id=users["alice"], now=NOW)
    neighbour = await _issue(engine, INVITE, created_by_user_id=users["alice"], now=NOW)
    revoked_at = NOW + timedelta(hours=1)

    assert await _revoke(engine, token_id=invite.record.id, now=revoked_at) == 1
    assert ensure_utc((await _record(engine, invite.record.id)).revoked_at) == revoked_at
    assert (await _record(engine, neighbour.record.id)).revoked_at is None

    assert await _revoke(engine, token_id=invite.record.id, now=revoked_at + timedelta(hours=1)) == 0
    assert ensure_utc((await _record(engine, invite.record.id)).revoked_at) == revoked_at
    print_success("revoked once, by id")


@pytest.mark.asyncio
async def test_revoke_every_pending_token_of_a_user(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 5: by user, every token of that user neither consumed nor revoked is revoked at ``now``, whatever its purpose, and counted; a consumed or already revoked one keeps its timestamps; another user's tokens are untouched."""
    print_section("Contract 5: revoke a user's tokens")
    alice, bob = users["alice"], users["bob"]
    reset = await _issue(engine, PASSWORD_RESET, user_id=alice, now=NOW)
    verification = await _issue(engine, EMAIL_VERIFICATION, user_id=alice, now=NOW)
    used = await _issue(engine, ADMIN_SETUP, user_id=alice, now=NOW)
    already = await _issue(engine, PASSWORD_RESET, user_id=alice, now=NOW)
    bobs = await _issue(engine, PASSWORD_RESET, user_id=bob, now=NOW)
    assert await _consume(engine, used.token, ADMIN_SETUP, consumed_by_user_id=alice, now=NOW + timedelta(hours=1)) is not None, "barrier: the setup link is used"
    assert await _revoke(engine, token_id=already.record.id, now=NOW + timedelta(hours=2)) == 1, "barrier: the earlier revocation hits"
    untouched = {issued.record.id: await _stored(engine, issued.record.id) for issued in (used, already, bobs)}
    revocation = NOW + timedelta(hours=3)

    assert await _revoke(engine, user_id=alice, now=revocation) == 2

    for issued in (reset, verification):
        assert ensure_utc((await _record(engine, issued.record.id)).revoked_at) == revocation
    for token_id, row in untouched.items():
        assert await _stored(engine, token_id) == row, f"token {token_id} must keep its row"
    print_success("alice's two pending tokens revoked; the used one, the revoked one and bob's untouched")


@pytest.mark.asyncio
async def test_revoke_a_users_tokens_of_one_purpose(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 5: by user and purpose, only that user's pending tokens of that purpose are revoked."""
    print_section("Contract 5: revoke a user's tokens of one purpose")
    alice, bob = users["alice"], users["bob"]
    reset = await _issue(engine, PASSWORD_RESET, user_id=alice, now=NOW)
    verification = await _issue(engine, EMAIL_VERIFICATION, user_id=alice, now=NOW)
    bobs_reset = await _issue(engine, PASSWORD_RESET, user_id=bob, now=NOW)
    revocation = NOW + timedelta(minutes=10)

    assert await _revoke(engine, user_id=alice, purpose=PASSWORD_RESET, now=revocation) == 1

    assert ensure_utc((await _record(engine, reset.record.id)).revoked_at) == revocation
    assert (await _record(engine, verification.record.id)).revoked_at is None
    assert (await _record(engine, bobs_reset.record.id)).revoked_at is None
    print_success("only alice's reset is revoked")


@pytest.mark.asyncio
@pytest.mark.parametrize("arguments", [{}, {"purpose": PASSWORD_RESET}], ids=["no arguments", "a purpose alone"])
async def test_revoke_refuses_to_revoke_everything(engine: AsyncEngine, users: dict[str, int], arguments: dict[str, Any]) -> None:
    """Contract 5: neither ``token_id`` nor ``user_id`` is a ValueError — never every token by accident — and nothing is revoked."""
    print_section(f"Contract 5: revoke with {arguments or 'no arguments'}")
    issued = await _issue(engine, PASSWORD_RESET, user_id=users["alice"], now=NOW)
    before = await _stored(engine, issued.record.id)

    async with AsyncSession(engine) as session:
        with pytest.raises(ValueError):
            await revoke_tokens(session, now=NOW + timedelta(minutes=1), **arguments)
        await session.commit()

    assert await _stored(engine, issued.record.id) == before
    print_success("ValueError, nothing revoked")


# =============================================================================
# 6. THE CALLER'S TRANSACTION
# =============================================================================


@pytest.mark.asyncio
async def test_a_rolled_back_issue_leaves_no_token(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 6: ``issue_token`` flushes (the record has its id) but does not commit: after a rollback a new session does not know the token."""
    print_section("Contract 6: issue, then rollback")

    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await issue_token(session, INVITE, now=NOW)
        assert issued.record.id is not None, "barrier: issue_token flushed"
        await session.rollback()

    inspection = await _inspect(engine, issued.token, INVITE, now=NOW)
    assert (inspection.status, inspection.record) == (TokenStatus.UNKNOWN, None)
    print_success("rolled back: UNKNOWN")


@pytest.mark.asyncio
async def test_a_rolled_back_consumption_leaves_the_token_valid(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 6: ``consume_token`` does not commit: after a rollback the token is ``VALID`` again and its row is as before."""
    print_section("Contract 6: consume, then rollback")
    issued = await _issue(engine, INVITE, now=NOW)
    before = await _stored(engine, issued.record.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert await consume_token(session, issued.token, INVITE, consumed_by_user_id=users["bob"], now=NOW) is not None, "barrier: the consumption succeeded"
        await session.rollback()

    assert (await _inspect(engine, issued.token, INVITE, now=NOW)).status == TokenStatus.VALID
    assert await _stored(engine, issued.record.id) == before
    print_success("rolled back: VALID")


@pytest.mark.asyncio
async def test_a_rolled_back_revocation_leaves_the_token_valid(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 6: ``revoke_tokens`` does not commit: after a rollback the token is ``VALID`` again and its row is as before."""
    print_section("Contract 6: revoke, then rollback")
    issued = await _issue(engine, PASSWORD_RESET, user_id=users["alice"], now=NOW)
    before = await _stored(engine, issued.record.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert await revoke_tokens(session, user_id=users["alice"], now=NOW) == 1, "barrier: the revocation hit the token"
        await session.rollback()

    assert (await _inspect(engine, issued.token, PASSWORD_RESET, now=NOW)).status == TokenStatus.VALID
    assert await _stored(engine, issued.record.id) == before
    print_success("rolled back: VALID")


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["commit", "rollback"])
async def test_an_invite_and_its_new_user_share_one_transaction(engine: AsyncEngine, users: dict[str, int], outcome: str) -> None:
    """Contract 6: what registration does — create the user, consume the invite in their name — commits or rolls back as one."""
    print_section(f"Contract 6: invite and new user, {outcome}")
    issued = await _issue(engine, INVITE, now=NOW)
    redeemed_at = NOW + timedelta(hours=1)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        newcomer = User(username="newcomer", email="newcomer@example.test", hashed_password="$argon2id$test")
        session.add(newcomer)
        await session.flush()
        assert await consume_token(session, issued.token, INVITE, consumed_by_user_id=newcomer.id, now=redeemed_at) is not None, "barrier: the invite is consumed"
        await (session.commit() if outcome == "commit" else session.rollback())

    async with AsyncSession(engine) as session:
        registered = (await session.execute(select(User.id).where(User.username == "newcomer"))).scalar_one_or_none()
    stored = await _record(engine, issued.record.id)
    if outcome == "commit":
        assert registered is not None and (stored.consumed_by_user_id, ensure_utc(stored.consumed_at)) == (registered, redeemed_at)
    else:
        assert registered is None and (stored.consumed_by_user_id, stored.consumed_at) == (None, None)
    print_success(f"{outcome}: the user and the consumption together")


# =============================================================================
# 7. SINGLE USE UNDER CONCURRENCY
# =============================================================================


async def _attempt(engine: AsyncEngine, token: str, consumer: int, moment: datetime) -> tuple[int, Optional[AccountToken]]:
    """One consumption in a session — a connection — of its own, committed: what one request does."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        record = await consume_token(session, token, INVITE, consumed_by_user_id=consumer, now=moment)
        await session.commit()
    return consumer, record


@pytest.mark.asyncio
async def test_two_sessions_consuming_one_token_at_once_one_wins(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 7: two sessions on two connections consume the same invite at the same time: exactly one gets the record, the other ``None``, and the row names the winner.

    WAL and busy_timeout come from the PRAGMA listener, as in production: the loser waits for the winner's commit, then
    its conditional UPDATE matches nothing. Five tokens, five races; no sleep anywhere.
    """
    print_section("Contract 7: two consumers, one token")
    moment = NOW + timedelta(minutes=1)

    for race in range(5):
        issued = await _issue(engine, INVITE, now=NOW)
        outcomes = await asyncio.gather(_attempt(engine, issued.token, users["bob"], moment), _attempt(engine, issued.token, users["carol"], moment))

        winners = [consumer for consumer, record in outcomes if record is not None]
        assert len(winners) == 1, f"race {race}: {len(winners)} sessions consumed the token"
        stored = await _record(engine, issued.record.id)
        assert (stored.consumed_by_user_id, ensure_utc(stored.consumed_at)) == (winners[0], moment)
    print_success("5 races, one winner each")


# =============================================================================
# 8. THE PLAINTEXT STAYS WITH ITS RECIPIENT
# =============================================================================


@pytest.mark.asyncio
async def test_the_plaintext_never_reaches_the_logs_nor_the_database(engine: AsyncEngine, users: dict[str, int], caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    """Contract 8: while tokens of every purpose are issued, inspected (valid, other purpose, consumed, revoked, expired), consumed twice and revoked, no structlog event and no stdlib record contains a plaintext — and no column of any table holds one.

    Barriers first: a canary logged through the service's logger name reaches both captures at DEBUG. Otherwise a capture
    that sees nothing would pass for a service that logs nothing.
    """
    print_section("Contract 8: the plaintext never leaves")
    monkeypatch.setattr(logging.getLogger(TOKEN_SERVICE_LOGGER), "disabled", False)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=TOKEN_SERVICE_LOGGER)
    plaintext_of: dict[AccountTokenPurpose, str] = {}

    with capture_logs() as events:
        structlog.get_logger(TOKEN_SERVICE_LOGGER).debug(CANARY)
        logging.getLogger(TOKEN_SERVICE_LOGGER).debug(CANARY)
        for purpose in AccountTokenPurpose:
            issued = await _issue(engine, purpose, user_id=_owner(purpose, users), email="new@example.test" if purpose == INVITE else None, now=NOW)
            plaintext_of[purpose] = issued.token
            await _inspect(engine, issued.token, purpose, now=NOW)
            await _inspect(engine, issued.token, _another(purpose), now=NOW)
            await _inspect(engine, issued.token, purpose, now=NOW + DEFAULT_TTL[purpose])
        invite, reset = plaintext_of[INVITE], plaintext_of[PASSWORD_RESET]
        await _consume(engine, invite, INVITE, consumed_by_user_id=users["bob"], now=NOW)
        await _consume(engine, invite, INVITE, consumed_by_user_id=users["bob"], now=NOW)
        await _inspect(engine, invite, INVITE, now=NOW)
        await _revoke(engine, user_id=users["alice"], purpose=PASSWORD_RESET, now=NOW)
        await _inspect(engine, reset, PASSWORD_RESET, now=NOW)
        await _consume(engine, reset, PASSWORD_RESET, now=NOW)

    plaintexts = list(plaintext_of.values())
    assert any(event.get("event") == CANARY for event in events), "barrier: structlog events of the token service's logger do not reach capture_logs"
    assert any(record.name == TOKEN_SERVICE_LOGGER and record.getMessage() == CANARY for record in caplog.records), "barrier: stdlib records of the token service's logger do not reach caplog at DEBUG"
    leaked_events = [event for event in events if any(secret in repr(event) for secret in plaintexts)]
    leaked_records = [f"{record.name}: {record.getMessage()}" for record in caplog.records if any(secret in record.getMessage() or secret in repr(vars(record)) for secret in plaintexts)]
    assert leaked_events == [], f"structlog events carrying a plaintext token: {leaked_events}"
    assert leaked_records == [], f"stdlib records carrying a plaintext token: {leaked_records}"
    assert await _plaintext_in_database(engine, plaintexts) == []
    print_success(f"{len(events)} events and {len(caplog.records)} records checked, no plaintext; none in the database either")


# =============================================================================
# 9. RETIRE — LOT A7b-2 (N60)
# =============================================================================
# A link is retired when what it was for is done by another way — the waiting administrator activated, or given a
# password, without its setup link (A-32) —: revoked AND consumed, so that it opens nothing and the account no longer
# counts as waiting for it (``registration_service.pending_admin_filter`` reads «none consumed»). ``retire_tokens`` is
# read when each test runs: until A7b-2 writes it, each fails on its own, saying so.

POSITIONAL = inspect.Parameter.POSITIONAL_OR_KEYWORD
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
EMPTY = inspect.Parameter.empty


def _retire_tokens() -> Callable[..., Awaitable[int]]:
    """``token_service.retire_tokens``; while lot A7b-2 has not written it, the test that needs it fails on its own, saying so."""
    retire = getattr(token_service, "retire_tokens", None)
    if retire is None:
        pytest.fail("red until A7b-2: token_service.retire_tokens does not exist yet", pytrace=False)
    return retire


async def _retire(engine: AsyncEngine, **arguments: Any) -> int:
    """``retire_tokens`` in a session of its own, committed afterwards — the service never commits, its caller does."""
    retire = _retire_tokens()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        retired = await retire(session, **arguments)
        await session.commit()
    return retired


def _another_user_purpose(purpose: AccountTokenPurpose) -> AccountTokenPurpose:
    """A purpose other than ``purpose`` whose tokens belong to a user: never the invite, which belongs to nobody yet."""
    return next(other for other in USER_PURPOSES if other != purpose)


def _moments(record: AccountToken) -> tuple[Optional[datetime], Optional[datetime], Optional[int]]:
    """``(revoked_at, consumed_at, consumed_by_user_id)`` of a row, the moments in UTC."""
    return ensure_utc(record.revoked_at), ensure_utc(record.consumed_at), record.consumed_by_user_id


# red until A7b-2
def test_retire_tokens_takes_one_user_one_purpose_and_an_optional_now() -> None:
    """Contract 9 — NEW, red until A7b-2 (``retire_tokens`` does not exist): ``retire_tokens(session, *, user_id, purpose, now=None)``, a coroutine function like every write of the service; ``user_id`` and ``purpose`` keyword-only and required — one user's links of one purpose, never more by accident."""
    print_section("Contract 9: retire_tokens' signature")
    retire = _retire_tokens()

    parameters = [(parameter.name, parameter.kind, parameter.default) for parameter in inspect.signature(retire).parameters.values()]

    assert inspect.iscoroutinefunction(retire), "retire_tokens must be a coroutine function, like the service's other writes"
    assert parameters == [("session", POSITIONAL, EMPTY), ("user_id", KEYWORD_ONLY, EMPTY), ("purpose", KEYWORD_ONLY, EMPTY), ("now", KEYWORD_ONLY, None)], f"expected retire_tokens(session, *, user_id, purpose, now=None): {parameters}"
    print_success("retire_tokens(session, *, user_id, purpose, now=None)")


# red until A7b-2
@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", USER_PURPOSES)
async def test_retire_spends_and_revokes_every_unconsumed_token_of_one_user_and_purpose(engine: AsyncEngine, users: dict[str, int], purpose: AccountTokenPurpose) -> None:
    """Contract 9 — NEW, red until A7b-2: alice's tokens of ``purpose`` not consumed — live, expired, already revoked — are retired, and counted: 3. Each is consumed at ``now`` with no consumer, and revoked at ``now`` unless it was already: the earlier revocation keeps its moment. Her token of that purpose already consumed, her live token of another purpose, bob's live token of that purpose and an invitation she created keep their rows, to the letter.

    Barrier first: at the moment of the retirement every token is worth what its name says.
    """
    print_section(f"Contract 9: retire alice's {purpose.value} tokens")
    alice, bob = users["alice"], users["bob"]
    first_revocation = NOW + timedelta(minutes=2)
    retirement = NOW + timedelta(minutes=10)
    live = await _issue(engine, purpose, user_id=alice, now=NOW)
    expired = await _issue(engine, purpose, user_id=alice, now=NOW - DEFAULT_TTL[purpose] - timedelta(minutes=1))
    revoked = await _issue(engine, purpose, user_id=alice, now=NOW)
    spent = await _issue(engine, purpose, user_id=alice, now=NOW)
    other_purpose = await _issue(engine, _another_user_purpose(purpose), user_id=alice, now=NOW)
    bobs = await _issue(engine, purpose, user_id=bob, now=NOW)
    invitation = await _issue(engine, INVITE, created_by_user_id=alice, now=NOW)
    assert await _consume(engine, spent.token, purpose, consumed_by_user_id=alice, now=NOW + timedelta(minutes=1)) is not None, "setup: the spent token is consumed"
    assert await _revoke(engine, token_id=revoked.record.id, now=first_revocation) == 1, "setup: the earlier revocation hits the token"
    scene = {"live": live, "expired": expired, "revoked": revoked, "spent": spent}
    statuses = {label: (await _inspect(engine, issued.token, purpose, now=retirement)).status for label, issued in scene.items()}
    assert statuses == {"live": TokenStatus.VALID, "expired": TokenStatus.EXPIRED, "revoked": TokenStatus.REVOKED, "spent": TokenStatus.CONSUMED}, f"barrier: the scene is not what it claims: {statuses}"
    untouched = {issued.record.id: await _stored(engine, issued.record.id) for issued in (spent, other_purpose, bobs, invitation)}

    retired = await _retire(engine, user_id=alice, purpose=purpose, now=retirement)

    assert retired == 3, f"alice's live, expired and revoked {purpose.value} tokens: 3 retired, got {retired}"
    assert _moments(await _record(engine, live.record.id)) == (retirement, retirement, None), "the live token: revoked and consumed at now, without a consumer"
    assert _moments(await _record(engine, expired.record.id)) == (retirement, retirement, None), "the expired token: revoked and consumed at now, without a consumer"
    assert _moments(await _record(engine, revoked.record.id)) == (first_revocation, retirement, None), "the revoked token: consumed at now, its revocation keeping its own moment"
    for token_id, row in untouched.items():
        assert await _stored(engine, token_id) == row, f"token {token_id} must keep its row: the spent one, another purpose's, bob's and the invitation are not alice's unconsumed {purpose.value} tokens"
    print_success(f"{purpose.value}: 3 retired; the spent one, another purpose's, bob's and the invitation untouched")


# red until A7b-2
@pytest.mark.asyncio
@pytest.mark.parametrize("purpose", USER_PURPOSES)
async def test_a_retired_token_is_revoked_and_can_no_longer_be_used(engine: AsyncEngine, users: dict[str, int], purpose: AccountTokenPurpose) -> None:
    """Contract 9 — NEW, red until A7b-2: once retired, a token is ``REVOKED`` to ``inspect_token`` — the revocation is read before the consumption —, before its expiry and after, with its record; ``consume_token`` refuses it, and its row stays as the retirement left it."""
    print_section(f"Contract 9: a retired {purpose.value} token")
    issued = await _issue(engine, purpose, user_id=users["alice"], now=NOW)
    retirement = NOW + timedelta(minutes=5)
    assert (await _inspect(engine, issued.token, purpose, now=retirement)).status == TokenStatus.VALID, "barrier: the token is valid before the retirement"

    assert await _retire(engine, user_id=users["alice"], purpose=purpose, now=retirement) == 1

    for moment in (retirement + timedelta(minutes=1), NOW + DEFAULT_TTL[purpose] + timedelta(days=1)):
        inspection = await _inspect(engine, issued.token, purpose, now=moment)
        assert inspection.status == TokenStatus.REVOKED, f"at {moment}: {inspection.status}, expected revoked"
        assert inspection.record is not None and inspection.record.id == issued.record.id
    after_retirement = await _stored(engine, issued.record.id)
    assert await _consume(engine, issued.token, purpose, consumed_by_user_id=users["bob"], now=retirement + timedelta(minutes=1)) is None, "a retired token must not be consumed"
    assert await _stored(engine, issued.record.id) == after_retirement, "a refused consumption must leave the row as the retirement left it"
    print_success(f"{purpose.value}: REVOKED, and refused")


# red until A7b-2
@pytest.mark.asyncio
async def test_a_second_retirement_finds_nothing_and_keeps_the_first_moments(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 9 — NEW, red until A7b-2: a second retirement of the same user and purpose counts 0 and leaves the row as the first one left it; a user without any token counts 0 too."""
    print_section("Contract 9: retire twice")
    issued = await _issue(engine, ADMIN_SETUP, user_id=users["alice"], now=NOW)
    first = NOW + timedelta(hours=1)
    assert await _retire(engine, user_id=users["alice"], purpose=ADMIN_SETUP, now=first) == 1, "barrier: the first retirement hits the token"
    after_first = await _stored(engine, issued.record.id)

    again = await _retire(engine, user_id=users["alice"], purpose=ADMIN_SETUP, now=first + timedelta(hours=1))
    nobody = await _retire(engine, user_id=users["carol"], purpose=ADMIN_SETUP, now=first + timedelta(hours=1))

    assert (again, nobody) == (0, 0), f"nothing left to retire: alice again {again}, carol {nobody}"
    assert await _stored(engine, issued.record.id) == after_first, "a second retirement must not move the first one's moments"
    print_success("1, then 0; the first moments kept")


# red until A7b-2
@pytest.mark.asyncio
async def test_a_rolled_back_retirement_leaves_the_token_valid(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 9 — NEW, red until A7b-2: ``retire_tokens`` does not commit, like the service's other writes: after a rollback the token is ``VALID`` again and its row is as before."""
    print_section("Contract 9: retire, then rollback")
    retire = _retire_tokens()
    issued = await _issue(engine, ADMIN_SETUP, user_id=users["alice"], now=NOW)
    before = await _stored(engine, issued.record.id)

    async with AsyncSession(engine, expire_on_commit=False) as session:
        assert await retire(session, user_id=users["alice"], purpose=ADMIN_SETUP, now=NOW + timedelta(minutes=5)) == 1, "barrier: the retirement hit the token"
        await session.rollback()

    assert (await _inspect(engine, issued.token, ADMIN_SETUP, now=NOW + timedelta(minutes=5))).status == TokenStatus.VALID
    assert await _stored(engine, issued.record.id) == before
    print_success("rolled back: VALID")


# red until A7b-2
@pytest.mark.asyncio
async def test_retire_without_now_retires_at_the_current_time(engine: AsyncEngine, users: dict[str, int]) -> None:
    """Contract 9 — NEW, red until A7b-2: without ``now`` the token is retired at the current UTC time — bracketed by two readings, never waited for —, one moment for ``revoked_at`` and ``consumed_at`` alike. A ``now`` left ``None`` on the way would leave it unconsumed, and its account still waiting."""
    print_section("Contract 9: retire without now")
    issued = await _issue(engine, ADMIN_SETUP, user_id=users["alice"], now=utcnow())

    before = utcnow()
    assert await _retire(engine, user_id=users["alice"], purpose=ADMIN_SETUP) == 1, "barrier: the retirement hits the token"
    after = utcnow()

    revoked_at, consumed_at, consumer = _moments(await _record(engine, issued.record.id))
    assert consumed_at is not None and before <= consumed_at <= after, f"consumed_at {consumed_at} outside [{before}, {after}]"
    assert (revoked_at, consumer) == (consumed_at, None), f"one moment for both, and no consumer: revoked_at {revoked_at}, consumed_at {consumed_at}, consumed_by_user_id {consumer}"
    print_success("retired now, one moment for both")
