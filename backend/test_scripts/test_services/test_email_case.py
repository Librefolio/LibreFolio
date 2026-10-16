"""P18: one email address per account, whatever its A–Z case — the services (release 1.3, workstream A, lot P18).

Until P18 ``users.email`` is ``UNIQUE`` and ``ix_users_email`` unique, both exact (SQLite's BINARY): ``alice@example.com``
and ``Alice@example.com`` can be two accounts, and every lookup compares exactly. ``EmailStr`` lowercases the domain only,
never the local part. The developer decided (P18) that an address is unique regardless of case; the contract the
coordinator approved, pinned here:

- C1 — one rule, in ``backend/app/services/accounts/user_service.py``: ``email_fold(address)`` folds A–Z to a–z and
  nothing else, exactly what SQLite's built-in ``lower()`` does — no ``strip()``, no Unicode case folding —, and
  ``same_email(a, b)`` is ``email_fold(a) == email_fold(b)``, a ``bool``. The documented limit: letters outside ASCII
  compare as written, so ``Émile@example.com`` and ``émile@example.com`` are two addresses.
- C2 — the database: a unique index ``ux_users_email_lower`` on ``lower(email)``, declared on the ``User`` model, so
  ``SQLModel.metadata.create_all`` builds it (migration 009 builds it on an install: unit ``db migration-009``). No new
  column; the exact index stays. Every write is covered, plain SQL included; the non-ASCII pair is not refused.
- C3 — the lookups: ``get_user_by_email`` and the email half of ``get_user_by_username_or_email`` compare
  ``lower(email) = lower(:value)``: an equality, never a pattern. The username half is pinned neither way here (lot A-21
  changes it): no username of this module looks like an address, and no probe like a username.
- C4 — the writes: an address is stored as written; one that differs from another account's only in A–Z case is refused
  like an exact duplicate today: ``create_user`` → ``(None, "Email already registered")``, nothing written;
  ``register_user`` → ``RegistrationError`` ``ACCOUNT_EXISTS``, nothing written — an invitation offered with it stays live.
- C5 — a case-only change of one's own address is the same address: ``update_profile`` stores the new form, keeps
  ``email_verified_at`` and ``session_version``, and its «User profile updated» carries ``email_changed`` False; another
  account's address in another case is ``(None, "Email already registered")``, nothing changed.
- F02 — ``run_admin_bootstrap``: the administrator waiting for its setup and a ``LIBREFOLIO_ADMIN_EMAIL`` that is its own
  address in another A–Z case are the same account — no error, the stored form follows the variable (C5) —; another
  account's address in another case is not taken (C3): an error naming the variable, nothing renamed.

Pure: every database is a private SQLite file under ``tmp_path`` built with ``create_all`` and the global settings the
startup seeds, opened as production opens its own (aiosqlite, NullPool — a session is a connection —, the PRAGMA listener
of ``backend.app.db.session``), disposed at teardown; ``get_async_engine`` is a tripwire, so nothing here opens the lane's
database. The accounts and email variables of the shell are removed. Every address carries a random local part of its
own, at ``example.com``, that no username shares; the accounts are rows written with a marker hash unless the service
under test creates them, and what a test counts are its own rows, found by their folded address. bcrypt runs at its
lowest cost. No clock wait: F02 gets its ``now``. The log is read with ``structlog.testing.capture_logs``, behind a canary
barrier, and no event may show an address, whole or by its local part (workstream E's rule).

Red until P18, each test on its own: ``email_fold`` and ``same_email`` are looked up when a test runs, so their absence
fails the tests that need them and nothing else; ``create_all`` builds no ``ux_users_email_lower``; the lookups compare
exactly; a case variant is a second account; a case-only change of one's own address resets the verification and ends
the sessions. A test about a negative (a pair the index must take, a lookup that must find nothing) carries a presence
barrier when it could pass for want of P18. The GUARDS are green today and must stay so: they say what P18 must not
break.
"""

from __future__ import annotations

import contextlib
import os
import re
import sqlite3
import uuid
from collections.abc import AsyncIterator, Callable, Iterable, Iterator
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional, Union

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.config import accounts
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.db.models import AccountTokenPurpose, GlobalSetting, User
from backend.app.services.accounts import auth_service, bootstrap_admin_service, registration_service, token_service, user_service
from backend.app.services.accounts.settings_service import initialize_global_settings
from backend.test_scripts.test_utils import print_section, print_success

#: The index P18 adds, and the exact one that stays.
INDEX = "ux_users_email_lower"
EXACT_INDEX = "ix_users_email"
#: ``CREATE UNIQUE INDEX ux_users_email_lower ON users (lower(email))`` as ``sqlite_master`` keeps it, read in lower case
#: and without quotes, brackets or spaces: how the statement is spelled does not matter, what it says does.
INDEX_SQL = "createuniqueindexux_users_email_loweronusers(lower(email))"
EMAIL_TAKEN = "Email already registered"
ACCOUNT_EXISTS = "ACCOUNT_EXISTS"
USER_PROFILE_UPDATED = "User profile updated"
ADMIN_EMAIL_VARIABLE = "LIBREFOLIO_ADMIN_EMAIL"
PASSWORD = "Email-Case-2026!"
#: What the accounts written as rows hold for a hash: nobody signs in with them.
MARKER_HASH = "$argon2id$email-case-marker"
#: When an address was verified: any value that is not NULL; what a kept verification keeps is the value read back.
VERIFIED_AT = datetime(2026, 10, 2, 8, 0, 0)
#: A session version of its own: a raised one would show as one more, a kept one shows as itself.
SESSION_VERSION = 4
#: Months before the real clock, as in test_admin_bootstrap: a ``now`` dropped on the way shows.
NOW = datetime(2026, 1, 15, 9, 30, 0, 123456, tzinfo=UTC)
HOUR = timedelta(hours=1)
#: A ``users`` row in plain SQL, the way a hand-written fix would write it: every NOT NULL column ``create_all`` declares.
RAW_INSERT = "INSERT INTO users (username, email, hashed_password, is_active, is_superuser, login_count, donation_popup_logins_since_shown, session_version, created_at, updated_at) VALUES (?, ?, ?, 1, 0, 0, 0, 0, ?, ?)"
STAMP = "2026-10-16 09:00:00.000000"
LOG_CANARY = "canary: the capture reaches the logger under test"
#: Removed before every test: each changes what registration, the bootstrap or an email decide.
INHERITED_PREFIXES = ("LIBREFOLIO_ADMIN_", "LIBREFOLIO_SMTP_")
INHERITED_VARIABLES = ("LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS", "LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BILLING_URL", "LIBREFOLIO_BLOCKED")


# =============================================================================
# THE FOLD, WRITTEN OUT — and the ways to write an address in another A–Z case
# =============================================================================


def _ascii_fold(text: str) -> str:
    """The fold of the contract, written out: A–Z to a–z, every other character as it is."""
    return "".join(chr(ord(character) + 32) if "A" <= character <= "Z" else character for character in text)


def _sqlite_lower(text: str) -> str:
    """What SQLite's built-in ``lower()`` makes of ``text``, asked of an in-memory database of this very build."""
    with contextlib.closing(sqlite3.connect(":memory:")) as conn:
        return conn.execute("SELECT lower(?)", (text,)).fetchone()[0]


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


def _address(prefix: str) -> str:
    """An address nobody has: ``prefix``, a tag of its own, at ``example.com``, all in lower case."""
    return f"{prefix}.{_tag()}@example.com"


def _upper(address: str) -> str:
    return address.upper()


def _capitalized(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local.capitalize()}@{domain.capitalize()}"


def _alternating(address: str) -> str:
    return "".join(character.upper() if position % 2 else character for position, character in enumerate(address))


def _local_upper(address: str) -> str:
    """The local part in upper case, the domain left in lower case, as ``EmailStr`` hands an address over."""
    local, _, domain = address.partition("@")
    return f"{local.upper()}@{domain}"


def _local_capitalized(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local.capitalize()}@{domain}"


Variant = Callable[[str], str]

#: Three ways to write an all-ASCII address in another A–Z case, and nothing else.
VARIANTS = [
    pytest.param(_upper, id="UPPER"),
    pytest.param(_capitalized, id="Capitalized"),
    pytest.param(_alternating, id="aLtErNaTiNg"),
]
#: How a ``LIBREFOLIO_ADMIN_EMAIL`` reaches the bootstrap in another case: its local part changed, its domain in lower case.
CONFIG_VARIANTS = [
    pytest.param(_local_upper, id="ADMIN.HEX@example.com"),
    pytest.param(_local_capitalized, id="Admin.hex@example.com"),
]
LOOKUPS = [
    pytest.param("get_user_by_email", id="get_user_by_email"),
    pytest.param("get_user_by_username_or_email", id="get_user_by_username_or_email"),
]


def _case_variant(address: str, variant: Variant) -> str:
    """``variant`` of ``address``, checked to differ from it in A–Z case and in nothing else."""
    written = variant(address)
    assert written != address and written.isascii() and _ascii_fold(written) == _ascii_fold(address), f"test bug: {written!r} is not {address!r} in another A–Z case"
    return written


def _p18(name: str) -> Callable[..., Any]:
    """``user_service.<name>``, looked up when the test runs: until P18 adds it, the test that needs it fails on its own, saying so."""
    found = getattr(user_service, name, None)
    if not callable(found):
        pytest.fail(f"red until P18: backend.app.services.accounts.user_service has no {name}", pytrace=False)
    return found


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def accounts_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the accounts, F02 and email variables of the shell that started the run."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def cheap_bcrypt(monkeypatch: pytest.MonkeyPatch) -> None:
    """bcrypt at its lowest cost in this process: real hashes that verify, a hundred times cheaper."""
    monkeypatch.setattr(auth_service, "BCRYPT_ROUNDS", 4)


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's private one")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` raises, in the session module and in the bootstrap module that imports it by name."""
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire)
    monkeypatch.setattr(bootstrap_admin_service, "get_async_engine", _lane_database_tripwire, raising=False)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "email-case.db"


@pytest_asyncio.fixture
async def engine(db_path: Path) -> AsyncIterator[AsyncEngine]:
    """A private SQLite file with the whole ORM schema (``create_all``) and the global settings the startup seeds; disposed at teardown."""
    private = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)
    try:
        async with private.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(private) as session:
            await initialize_global_settings(session)
        yield private
    finally:
        await private.dispose()


# =============================================================================
# HELPERS — the schema, read from SQLite itself
# =============================================================================


def _schema_object(db_path: Path, name: str) -> Optional[tuple[str, str, str]]:
    """``(type, tbl_name, sql)`` of the schema object ``name``, from ``sqlite_master``; None when there is none."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        return conn.execute("SELECT type, tbl_name, sql FROM sqlite_master WHERE name = ?", (name,)).fetchone()


def _normalized(sql: str) -> str:
    """A ``CREATE INDEX`` in lower case, without quotes, brackets or spaces."""
    return re.sub(r"[\s\"`\[\]]", "", sql).lower()


def _index_flags(db_path: Path, name: str) -> Optional[tuple[bool, bool]]:
    """``(unique, partial)`` of the index ``name`` of ``users``, from ``PRAGMA index_list``; None when ``users`` has no such index."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        flags = {index: (bool(unique), bool(partial)) for _seq, index, unique, _origin, partial in conn.execute('PRAGMA index_list("users")')}
    return flags.get(name)


def _key_columns(db_path: Path, name: str) -> list[tuple[int, Optional[str]]]:
    """``(cid, column)`` of each key of the index ``name``, from ``PRAGMA index_xinfo``: an expression is cid -2, without a name."""
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        return [(cid, column) for _seqno, cid, column, _desc, _coll, key in conn.execute(f'PRAGMA index_xinfo("{name}")') if key]


def _refusal(conn: sqlite3.Connection, statement: str, parameters: tuple[Any, ...]) -> Optional[str]:
    """``statement`` in a transaction of its own: None when SQLite took it (committed), else the message of its ``IntegrityError`` (rolled back)."""
    try:
        with conn:
            conn.execute(statement, parameters)
    except sqlite3.IntegrityError as refused:
        return str(refused)
    return None


# =============================================================================
# HELPERS — the accounts, written as rows and read fresh
# =============================================================================


@dataclass(frozen=True)
class Stored:
    """A committed ``users`` row, as far as an address goes, read in a fresh session."""

    id: int
    username: str
    email: str
    email_verified_at: Optional[datetime]
    session_version: int
    is_active: bool
    is_superuser: bool


async def _add_account(engine: AsyncEngine, *, email: str, username: Optional[str] = None, verified: bool = False, session_version: int = 0) -> int:
    """An account written as a row and committed in a session of its own, before anything under test runs: no service, no bcrypt. Its id."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user = User(username=username or f"acct_{_tag()}", email=email, hashed_password=MARKER_HASH, email_verified_at=VERIFIED_AT if verified else None, session_version=session_version)
        session.add(user)
        await session.commit()
        return user.id


async def _stored(engine: AsyncEngine, user_id: int) -> Optional[Stored]:
    """The committed row of ``user_id``, read in a fresh session; None when there is none."""
    columns = (User.id, User.username, User.email, User.email_verified_at, User.session_version, User.is_active, User.is_superuser)
    async with AsyncSession(engine) as session:
        row = (await session.execute(select(*columns).where(User.id == user_id))).one_or_none()
    return None if row is None else Stored(row.id, row.username, row.email, row.email_verified_at, row.session_version, bool(row.is_active), bool(row.is_superuser))


async def _same_fold(engine: AsyncEngine, address: str) -> list[tuple[int, str]]:
    """``(id, email)`` of every account whose address SQLite's ``lower()`` folds as it folds ``address``, by id: this test's own rows."""
    async with AsyncSession(engine) as session:
        rows = (await session.execute(select(User.id, User.email).where(func.lower(User.email) == func.lower(address)).order_by(User.id))).all()
    return [(row.id, row.email) for row in rows]


async def _usernames(engine: AsyncEngine, *names: str) -> set[str]:
    """Which of ``names`` the database holds as usernames."""
    async with AsyncSession(engine) as session:
        return set((await session.execute(select(User.username).where(User.username.in_(names)))).scalars().all())


async def _orm_refusal(engine: AsyncEngine, username: str, email: str) -> Optional[str]:
    """A ``User`` added through the ORM and committed, as any code path that skips the service's lookup would: None when it was committed, else the ``IntegrityError``'s message (rolled back)."""
    async with AsyncSession(engine) as session:
        session.add(User(username=username, email=email, hashed_password=MARKER_HASH))
        try:
            await session.commit()
        except IntegrityError as refused:
            await session.rollback()
            return str(refused)
    return None


async def _registration_open(engine: AsyncEngine) -> None:
    """``registration_mode`` = ``open``, on the row the startup seeded: a registration needs no invitation."""
    async with AsyncSession(engine) as session:
        row = await session.get(GlobalSetting, "registration_mode")
        assert row is not None, "setup: initialize_global_settings seeded no registration_mode row"
        row.value = "open"
        session.add(row)
        await session.commit()


async def _invitation(engine: AsyncEngine, creator: int) -> str:
    """A live invitation issued by the token service directly and committed: the scene is set without the service under test."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        issued = await token_service.issue_token(session, AccountTokenPurpose.INVITE, created_by_user_id=creator)
        await session.commit()
    return issued.token


async def _invitation_status(engine: AsyncEngine, token: str) -> token_service.TokenStatus:
    async with AsyncSession(engine) as session:
        return (await token_service.inspect_token(session, token, AccountTokenPurpose.INVITE)).status


# =============================================================================
# HELPERS — calling the services as their callers do, each in a session of its own
# =============================================================================


async def _look_up(engine: AsyncEngine, lookup: str, value: str) -> Optional[int]:
    """The id of the account ``user_service.<lookup>(session, value)`` answers, or None."""
    async with AsyncSession(engine) as session:
        found = await getattr(user_service, lookup)(session, value)
        return None if found is None else found.id


async def _create(engine: AsyncEngine, username: str, email: str) -> tuple[Optional[int], Optional[str]]:
    """``create_user`` as the command line calls it: the new account's id, or None, and the error."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        user, error = await user_service.create_user(session, username, email, PASSWORD)
        return (None if user is None else user.id), error


async def _register(engine: AsyncEngine, username: str, email: str, invite_token: Optional[str]) -> Union[User, registration_service.RegistrationError]:
    """``register_user`` as test_registration_service calls it: the new account, or the refusal — committed after it, as a careless caller would, so a refusal that left something behind shows."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        try:
            user = await registration_service.register_user(session, username=username, email=email, password=PASSWORD, invite_token=invite_token)
        except registration_service.RegistrationError as refusal:
            await session.commit()
            return refusal
        await session.commit()
    return user


async def _update_profile(engine: AsyncEngine, user_id: int, *, email: str, username: Optional[str] = None) -> tuple[Optional[int], Optional[str]]:
    """``update_profile`` in a session that never loaded the account, as a request runs it: the id of the account it answers, or None, and the error."""
    async with AsyncSession(engine, expire_on_commit=False) as session:
        updated, error = await user_service.update_profile(session, user_id, username=username, email=email)
        return (None if updated is None else updated.id), error


async def _bootstrap(engine: AsyncEngine, email: str, username: str, *, now: datetime) -> Any:
    """``run_admin_bootstrap`` with the F02 variables ``email`` and ``username``, no token, in a session of its own, as the startup step runs it."""
    config = accounts.AdminBootstrapConfig(email=email, username=username, token=None)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        return await bootstrap_admin_service.run_admin_bootstrap(session, config, now=now)


# =============================================================================
# HELPERS — the log
# =============================================================================


@contextlib.contextmanager
def _captured(logger: Any) -> Iterator[list[dict[str, Any]]]:
    """The structlog events of the block, behind a barrier: a canary logged through ``logger``, the module's own, must be among them."""
    with capture_logs() as events:
        logger.debug(LOG_CANARY)
        yield events
    assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the events of the module's logger do not reach capture_logs, so what this test reads of the log proves nothing: {events}"


def _logged(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The captured events, the canary aside."""
    return [event for event in events if event.get("event") != LOG_CANARY]


def _errors(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in _logged(events) if event.get("log_level") in ("error", "critical")]


def _showing(events: list[dict[str, Any]], addresses: Iterable[str]) -> list[dict[str, Any]]:
    """The events that show one of ``addresses``, whole or by its local part, in any case."""
    needles = {needle for address in addresses for needle in (address.lower(), address.lower().partition("@")[0])}
    return [event for event in _logged(events) if any(needle in repr(event).lower() for needle in needles)]


def _the_event(events: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """The event ``name`` of the capture, asserted to be there once."""
    found = [event for event in _logged(events) if event.get("event") == name]
    assert len(found) == 1, f"«{name}» must be logged once: {found}"
    return found[0]


# =============================================================================
# C1 — ONE RULE: email_fold AND same_email
# =============================================================================

#: (written, folded): A–Z folded, everything else kept — accents, the letters Python's ``lower()`` or ``casefold()`` would
#: change (İ, ẞ, the Kelvin sign, the long s), spaces around: SQLite's ``lower()`` keeps them all.
FOLDS = [
    pytest.param("ALICE@Example.COM", "alice@example.com", id="ascii-letters"),
    pytest.param("alice@example.com", "alice@example.com", id="already-folded"),
    pytest.param("Émile@X", "Émile@x", id="E-acute-kept"),
    pytest.param(" Alice@Example.com ", " alice@example.com ", id="spaces-kept"),
    pytest.param("\tBOB@EXAMPLE.COM\n", "\tbob@example.com\n", id="tab-and-newline-kept"),
    pytest.param("ÀÉÎÕÜÇ.Ñ@EXAMPLE.COM", "ÀÉÎÕÜÇ.Ñ@example.com", id="latin-capitals-kept"),
    pytest.param("İNCI@EXAMPLE.COM", "İnci@example.com", id="dotted-capital-I-kept"),
    pytest.param("STRAẞE@EXAMPLE.COM", "straẞe@example.com", id="capital-sharp-s-kept"),
    pytest.param("straße@example.com", "straße@example.com", id="sharp-s-kept"),
    pytest.param("\u212aELVIN@EXAMPLE.COM", "\u212aelvin@example.com", id="kelvin-sign-kept"),
    pytest.param("ΣΙΣΥΦΟΣ@EXAMPLE.COM", "ΣΙΣΥΦΟΣ@example.com", id="greek-kept"),
    pytest.param("ſam@example.com", "ſam@example.com", id="long-s-kept"),
    pytest.param("0123-_.+=@[127.0.0.1]", "0123-_.+=@[127.0.0.1]", id="no-letter"),
    pytest.param("", "", id="empty"),
]

#: Every character from U+0001 to U+052F (Latin, IPA, Greek, Cyrillic), the letters whose Python ``lower()`` or
#: ``casefold()`` differ from SQLite's ``lower()`` further up (İ, ẞ, the Kelvin and Ångström signs, Ω, ﬀ, 𐐀), and a final Σ
#: after a letter, which ``str.lower()`` turns into ς by its context.
SWEEP = "".join(chr(code) for code in range(1, 0x530)) + "\u0130\u1e9e\u212a\u212b\u2126\ufb00\U00010400 ΟΔΟΣ"

#: (a, b, the same address?): A–Z case variants are; the others are not — the non-ASCII pair (the documented limit), the
#: pairs Python's ``lower()`` or ``casefold()`` would merge, surrounding spaces (never stripped), another domain or local part.
PAIRS = [
    pytest.param("alice@example.com", "ALICE@EXAMPLE.COM", True, id="upper"),
    pytest.param("Alice@Example.com", "aLiCe@eXaMpLe.CoM", True, id="mixed"),
    pytest.param("alice@example.com", "alice@example.com", True, id="identical"),
    pytest.param("Émile@example.com", "Émile@EXAMPLE.COM", True, id="E-acute-on-both-sides"),
    pytest.param("Émile@example.com", "émile@example.com", False, id="E-acute-against-e-acute"),
    pytest.param("\u212aelvin@example.com", "kelvin@example.com", False, id="kelvin-sign-against-k"),
    pytest.param("İnci@example.com", "inci@example.com", False, id="dotted-capital-I-against-i"),
    pytest.param("straße@example.com", "strasse@example.com", False, id="sharp-s-against-ss"),
    pytest.param(" alice@example.com", "alice@example.com", False, id="leading-space"),
    pytest.param("alice@example.com ", "alice@example.com", False, id="trailing-space"),
    pytest.param("alice@example.com", "alice@example.org", False, id="another-domain"),
    pytest.param("alice@example.com", "alicia@example.com", False, id="another-local-part"),
]


@pytest.mark.parametrize(("written", "folded"), FOLDS)
def test_email_fold_folds_a_to_z_and_nothing_else(written: str, folded: str) -> None:
    """ECASE-001 — C1, red until P18 (``user_service.email_fold`` does not exist): ``email_fold(written)`` is ``folded``: A–Z to a–z, and every other character as written — accented and non-Latin letters, the ones Python's ``lower()`` or ``casefold()`` would change, spaces, tabs and newlines around (no ``strip()``). The premise asks this very SQLite: its ``lower()`` gives the same, or the index of C2 and this rule would disagree."""
    email_fold = _p18("email_fold")
    assert _ascii_fold(written) == folded, f"test bug: {written!r} folds to {_ascii_fold(written)!r}, not {folded!r}"
    assert _sqlite_lower(written) == folded, f"premise: SQLite's lower() makes {written!r} into {_sqlite_lower(written)!r}, not {folded!r}: this build folds more than A–Z (ICU?), and the documented limit no longer holds"

    assert email_fold(written) == folded, f"email_fold({written!r}) must be {folded!r}, what SQLite's lower() gives: got {email_fold(written)!r}"


def test_email_fold_leaves_every_character_but_a_to_z_as_it_is() -> None:
    """ECASE-002 — C1, red until P18: over the sweep of U+0001–U+052F and the known traps, ``email_fold`` changes A–Z and nothing else — character by character, and on the whole string at once, where a fold that reads the context (``str.lower()`` makes a final Σ into ς) shows. The premise: SQLite's ``lower()`` gives the same sweep."""
    email_fold = _p18("email_fold")
    assert _sqlite_lower(SWEEP) == _ascii_fold(SWEEP), "premise: SQLite's lower() of this build folds more than A–Z (ICU?): the documented limit no longer holds"

    wrong = {f"U+{ord(character):04X}": (email_fold(character), _ascii_fold(character)) for character in SWEEP if email_fold(character) != _ascii_fold(character)}

    assert wrong == {}, f"email_fold must fold A–Z and nothing else; (got, expected) for the first characters it gets wrong: {dict(list(wrong.items())[:12])}"
    assert email_fold(SWEEP) == _ascii_fold(SWEEP), "email_fold of the whole sweep must be the sweep with A–Z folded, whatever the context of a character"


@pytest.mark.parametrize(("first", "second", "same"), PAIRS)
def test_same_email_is_email_fold_compared(first: str, second: str, same: bool) -> None:
    """ECASE-003 — C1, red until P18 (``user_service.same_email`` does not exist): ``same_email(a, b)`` is the ``bool`` ``email_fold(a) == email_fold(b)``, both ways round: true for A–Z case variants, false for the non-ASCII pair ``Émile@``/``émile@`` (the documented limit), for the pairs Python's ``lower()`` or ``casefold()`` would merge, for surrounding spaces, another domain, another local part."""
    same_email = _p18("same_email")
    email_fold = _p18("email_fold")
    assert (_ascii_fold(first) == _ascii_fold(second)) is same, f"test bug: {first!r} and {second!r} are {'not ' if same else ''}the same fold"

    assert same_email(first, second) is same, f"same_email({first!r}, {second!r}) must be {same}: got {same_email(first, second)!r}"
    assert same_email(second, first) is same, f"same_email({second!r}, {first!r}) must be {same}, as the other way round: got {same_email(second, first)!r}"
    assert (email_fold(first) == email_fold(second)) is same, "same_email must be email_fold compared: the two disagree"


# =============================================================================
# C2 — THE DATABASE: ux_users_email_lower ON lower(email), DECLARED ON THE MODEL
# =============================================================================


@pytest.mark.asyncio
async def test_create_all_builds_a_unique_index_on_lower_email(engine: AsyncEngine, db_path: Path) -> None:
    """ECASE-010 — C2, red until P18 (``create_all`` builds no such index): the ``User`` model declares ``ux_users_email_lower``, so a ``create_all`` database has it, read from ``sqlite_master`` and SQLite's PRAGMAs: an index of ``users``, unique, on every row (not partial), with one key, the expression ``lower(email)``. ``ix_users_email`` stays, unique on ``email``."""
    print_section(f"ECASE-010: {INDEX} built by create_all")

    found = _schema_object(db_path, INDEX)

    assert found is not None, f"red until P18: create_all builds no {INDEX}: the User model must declare it"
    kind, table, sql = found
    assert (kind, table) == ("index", "users"), f"{INDEX} must be an index of users: {found}"
    assert _normalized(sql) == INDEX_SQL, f"{INDEX} must be a unique index on lower(email), SQLite's own fold: {sql!r}"
    assert _index_flags(db_path, INDEX) == (True, False), f"{INDEX} must be unique, and cover every row (not partial): (unique, partial) = {_index_flags(db_path, INDEX)}"
    assert _key_columns(db_path, INDEX) == [(-2, None)], f"{INDEX} must have one key, an expression: {_key_columns(db_path, INDEX)}"
    assert _index_flags(db_path, EXACT_INDEX) == (True, False) and [column for _cid, column in _key_columns(db_path, EXACT_INDEX)] == ["email"], f"the exact {EXACT_INDEX} must stay, unique on email"
    print_success(f"{INDEX}: unique, on lower(email); {EXACT_INDEX} kept")


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", VARIANTS)
async def test_the_database_refuses_through_the_orm_an_address_in_another_case(engine: AsyncEngine, variant: Variant) -> None:
    """ECASE-011 — C2, red until P18 (the second account is committed): an account holds ``address``; a ``User`` with ``address`` in another A–Z case, added through the ORM as a path that skips the service would, is refused by SQLite at the commit with an ``IntegrityError`` naming ``ux_users_email_lower``. Nothing is written: the address keeps its one account, as written."""
    address = _address("orm")
    first = await _add_account(engine, email=address)
    intruder = f"intruder_{_tag()}"

    refused = await _orm_refusal(engine, intruder, _case_variant(address, variant))

    assert refused is not None, f"red until P18: a second account was committed with {address!r} in another case"
    assert INDEX in refused, f"the refusal must come from {INDEX}: {refused}"
    assert await _same_fold(engine, address) == [(first, address)], "the address must keep its one account, as written"
    assert await _usernames(engine, intruder) == set(), f"the refused {intruder} must not be in the database"


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", VARIANTS)
async def test_the_database_refuses_plain_sql_in_another_case(engine: AsyncEngine, db_path: Path, variant: Variant) -> None:
    """ECASE-012 — C2, red until P18 (both statements go through): plain SQL on the file, as a hand-written fix would run it: an ``INSERT`` of a new account with an address another account has in another A–Z case, and an ``UPDATE`` of a second account's address to it, are both refused by SQLite, naming ``ux_users_email_lower``. Nothing is written."""
    address, other = _address("raw"), _address("other")
    first = await _add_account(engine, email=address)
    second = await _add_account(engine, email=other)
    written = _case_variant(address, variant)

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        inserted = _refusal(conn, RAW_INSERT, (f"raw_{_tag()}", written, MARKER_HASH, STAMP, STAMP))
        updated = _refusal(conn, "UPDATE users SET email = ? WHERE id = ?", (written, second))

    assert inserted is not None and INDEX in inserted, f"red until P18: an INSERT of {written!r} must be refused by {INDEX}: {inserted}"
    assert updated is not None and INDEX in updated, f"red until P18: an UPDATE to {written!r} must be refused by {INDEX}: {updated}"
    assert await _same_fold(engine, address) == [(first, address)], "the address must keep its one account, as written"
    second_after = await _stored(engine, second)
    assert second_after is not None and second_after.email == other, f"the refused UPDATE must leave the second account's address: {second_after}"


@pytest.mark.asyncio
async def test_the_database_takes_the_non_ascii_pair_and_refuses_its_a_to_z_variant(engine: AsyncEngine, db_path: Path) -> None:
    """ECASE-013 — C2 and the documented limit, red until P18 (barrier: the index exists — without it this pair proves nothing): ``Émile.<hex>@example.com`` and ``émile.<hex>@example.com`` are two addresses, both committed as written; ``ÉMILE.<HEX>@EXAMPLE.COM``, Émile's own but for A–Z, is refused, naming the index: SQLite's ``lower()`` folds A–Z only, and the index with it."""
    assert _schema_object(db_path, INDEX) is not None, f"red until P18 — barrier: create_all builds no {INDEX}, so that the non-ASCII pair goes in would prove nothing"
    tag = _tag()
    capital, small = f"Émile.{tag}@example.com", f"émile.{tag}@example.com"
    upper = capital.upper()
    assert _ascii_fold(upper) == _ascii_fold(capital) != _ascii_fold(small), "test bug: ÉMILE… must fold as Émile…, and émile… otherwise"

    kept = [await _add_account(engine, email=capital), await _add_account(engine, email=small)]
    refused = await _orm_refusal(engine, f"upper_{_tag()}", upper)

    assert [account.email for account in [await _stored(engine, user_id) for user_id in kept] if account is not None] == [capital, small], "Émile… and émile… are two addresses: both committed, as written"
    assert refused is not None and INDEX in refused, f"{upper!r} is Émile's address but for A–Z: {INDEX} must refuse it: {refused}"


# =============================================================================
# C3 — THE LOOKUPS: lower(email) = lower(:value), AN EQUALITY
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("lookup", LOOKUPS)
async def test_a_lookup_finds_the_account_whatever_the_a_to_z_case(engine: AsyncEngine, lookup: str, variant: Variant) -> None:
    """ECASE-020 — C3, red until P18 (the lookups compare exactly): ``alice.<hex>@example.com``, asked for as ``ALICE.<HEX>@EXAMPLE.COM``, ``Alice.<hex>@Example.com`` or in alternating case, is found by ``get_user_by_email`` and by ``get_user_by_username_or_email`` — that account, not one of the decoys written before it (another domain, a longer local part, a prefixed one). As written it is found too (GUARD, green today). No username looks like the address: the username half is not what answers."""
    tag = _tag()
    address = f"alice.{tag}@example.com"
    for decoy in (f"alice.{tag}@example.org", f"alice.{tag}x@example.com", f"xalice.{tag}@example.com"):
        await _add_account(engine, email=decoy)
    target = await _add_account(engine, email=address, username=f"c3_{_tag()}")
    asked = _case_variant(address, variant)

    assert await _look_up(engine, lookup, address) == target, f"GUARD: {lookup} must find {address!r} as written"
    assert await _look_up(engine, lookup, asked) == target, f"red until P18: {lookup}({asked!r}) must find the account of {address!r}, the same address but for A–Z, and not a decoy"


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", LOOKUPS)
async def test_a_lookup_is_an_equality_never_a_pattern(engine: AsyncEngine, lookup: str) -> None:
    """ECASE-021 — C3, GUARD (green today, where the lookups compare exactly; red if A–Z case is ignored through LIKE or ILIKE, whose ``_`` and ``%`` are wildcards): an account holds ``pat.<hex>@example.com``; ``pat_<hex>@example.com``, ``pat.%@example.com``, ``%@example.com`` and ``PAT.<HEX>@EXAMPLE.CO_`` are other addresses, and find nobody. Each probe ends in ``@example.co…``, so it can match no username, whatever the username half does."""
    tag = _tag()
    await _add_account(engine, email=f"pat.{tag}@example.com", username=f"c3_{_tag()}")
    probes = (f"pat_{tag}@example.com", "pat.%@example.com", "%@example.com", f"PAT.{tag.upper()}@EXAMPLE.CO_")

    found = {probe: await _look_up(engine, lookup, probe) for probe in probes}

    assert found == dict.fromkeys(probes), f"{lookup} must compare for equality: _ and % are characters of an address, not wildcards; found {found}"


@pytest.mark.asyncio
@pytest.mark.parametrize("lookup", LOOKUPS)
async def test_a_lookup_folds_a_to_z_and_nothing_else(engine: AsyncEngine, lookup: str) -> None:
    """ECASE-022 — C3 and the documented limit, red until P18 (``ÉMILE…`` is not found today, the barrier that gives the negative its meaning): ``Émile.<hex>@example.com`` is found when asked for as ``ÉMILE.<HEX>@EXAMPLE.COM`` — its own address but for A–Z — and not as ``émile.<hex>@example.com``, another address: É is not A–Z, as for the index."""
    tag = _tag()
    capital = f"Émile.{tag}@example.com"
    target = await _add_account(engine, email=capital, username=f"c3_{_tag()}")

    assert await _look_up(engine, lookup, capital.upper()) == target, f"red until P18: {lookup}({capital.upper()!r}) must find {capital!r}, the same address but for A–Z"
    assert await _look_up(engine, lookup, f"émile.{tag}@example.com") is None, f"{lookup} must not find {capital!r} as émile…: letters outside ASCII compare as written (the documented limit)"


# =============================================================================
# C4 — THE WRITES: AN ADDRESS IN ANOTHER A–Z CASE IS AN ADDRESS TAKEN
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", VARIANTS)
async def test_create_user_refuses_an_address_another_account_has_in_another_case(engine: AsyncEngine, variant: Variant) -> None:
    """ECASE-030 — C4, red until P18 (a second account is created): an account holds ``address``; ``create_user`` of another username with ``address`` in another A–Z case answers ``(None, "Email already registered")``, as for an exact duplicate, and writes nothing: the address keeps its one account, as written, and the new username is nowhere."""
    print_section("ECASE-030: create_user with an address taken in another case")
    address = _address("taken")
    first = await _add_account(engine, email=address)
    newcomer = f"newcomer_{_tag()}"

    outcome = await _create(engine, newcomer, _case_variant(address, variant))

    assert outcome == (None, EMAIL_TAKEN), f"red until P18: an address another account has in another A–Z case must be refused like an exact duplicate, got {outcome}"
    assert await _same_fold(engine, address) == [(first, address)], "the address must keep its one account, as written"
    assert await _usernames(engine, newcomer) == set(), f"the refused {newcomer} must not be in the database"
    print_success("refused, Email already registered, nothing written")


@pytest.mark.asyncio
@pytest.mark.parametrize("with_invitation", [False, True], ids=["no-invitation", "a-valid-invitation"])
@pytest.mark.parametrize("variant", VARIANTS)
async def test_register_user_refuses_an_address_another_account_has_in_another_case(engine: AsyncEngine, variant: Variant, with_invitation: bool) -> None:
    """ECASE-031 — C4, red until P18 (the registration goes through, the invitation consumed): registration ``open`` (the row, as test_registration_service sets it) and an account holding ``address``; ``register_user`` with ``address`` in another A–Z case — with no invitation, or with a valid one — raises ``RegistrationError`` ``ACCOUNT_EXISTS`` and writes nothing: the address keeps its one account, the new username is nowhere, and the invitation is still live (the account and its invitation share one transaction)."""
    address = _address("member")
    first = await _add_account(engine, email=address)
    await _registration_open(engine)
    invitation = await _invitation(engine, first) if with_invitation else None
    newcomer = f"newcomer_{_tag()}"

    outcome = await _register(engine, newcomer, _case_variant(address, variant), invitation)

    assert isinstance(outcome, registration_service.RegistrationError), f"red until P18: an address another account has in another A–Z case must be refused like an exact duplicate, got {outcome!r}"
    assert outcome.code == ACCOUNT_EXISTS, f"the refusal must be {ACCOUNT_EXISTS}, as for an exact duplicate: {outcome.code!r} ({outcome!r})"
    assert await _same_fold(engine, address) == [(first, address)], "the address must keep its one account, as written"
    assert await _usernames(engine, newcomer) == set(), f"the refused {newcomer} must not be in the database"
    if invitation is not None:
        assert await _invitation_status(engine, invitation) == token_service.TokenStatus.VALID, "a refused registration must leave its invitation live"


@pytest.mark.asyncio
async def test_create_user_takes_the_non_ascii_pair_as_two_addresses(engine: AsyncEngine) -> None:
    """ECASE-032 — C4 and the documented limit, red until P18 (barrier: ``ÉMILE…``, Émile's address but for A–Z, is refused first — without that, a second account proves nothing): with ``Émile.<hex>@example.com`` taken, ``create_user`` refuses ``ÉMILE.<HEX>@EXAMPLE.COM`` and creates ``émile.<hex>@example.com``, another address; both stored as written."""
    tag = _tag()
    capital, small = f"Émile.{tag}@example.com", f"émile.{tag}@example.com"
    first = await _add_account(engine, email=capital)

    refused = await _create(engine, f"upper_{_tag()}", capital.upper())
    created, error = await _create(engine, f"small_{_tag()}", small)

    assert refused == (None, EMAIL_TAKEN), f"red until P18 — barrier: {capital.upper()!r} is {capital!r} but for A–Z, so it must be refused: {refused}"
    assert created is not None and error is None, f"{small!r} is another address than {capital!r} (É is not A–Z): it must be created, got error {error!r}"
    stored = [await _stored(engine, user_id) for user_id in (first, created)]
    assert [account.email if account else None for account in stored] == [capital, small], "both addresses are stored as written"


# =============================================================================
# C5 — A CASE-ONLY CHANGE OF ONE'S OWN ADDRESS IS THE SAME ADDRESS
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("with_username", [False, True], ids=["email-only", "with-a-new-username"])
@pytest.mark.parametrize("variant", VARIANTS)
async def test_a_case_only_change_of_ones_own_address_keeps_the_verification_and_the_sessions(engine: AsyncEngine, variant: Variant, with_username: bool) -> None:
    """ECASE-040 — C5, red until P18 (today it is an email change: the verification reset, the session version raised, ``email_changed`` True): an account, its address verified, at session version 4; ``update_profile`` with its own address in another A–Z case — alone, or with a new username — answers ``(user, None)`` and stores the new form; ``email_verified_at`` and ``session_version`` are as they were; «User profile updated» is logged once, with ``email_changed`` exactly False, and no event shows the address in either form."""
    print_section("ECASE-040: a case-only change of one's own address")
    address = _address("mailbox")
    account = await _add_account(engine, email=address, username=f"c5_{_tag()}", verified=True, session_version=SESSION_VERSION)
    before = await _stored(engine, account)
    assert before is not None and before.email_verified_at is not None and before.session_version == SESSION_VERSION, f"setup: a verified address at session version {SESSION_VERSION}: {before}"
    written = _case_variant(address, variant)
    username = f"c5_{_tag()}" if with_username else None

    with _captured(user_service.logger) as events:
        outcome = await _update_profile(engine, account, email=written, username=username)

    assert outcome == (account, None), f"a case-only change of one's own address must succeed: {outcome}"
    after = await _stored(engine, account)
    assert after == replace(before, email=written, username=username or before.username), f"red until P18: the new form is stored, and the verification and the session version stay — it is the same address: {before} → {after}"
    event = _the_event(events, USER_PROFILE_UPDATED)
    assert event.get("email_changed") is False, f"«{USER_PROFILE_UPDATED}» must carry email_changed=False for a case-only change: {event}"
    assert _showing(events, [address, written]) == [], "no event may show the address, in either form"
    print_success("the new form stored; verification and sessions kept; email_changed False")


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", VARIANTS)
async def test_another_accounts_address_in_another_case_is_refused(engine: AsyncEngine, variant: Variant) -> None:
    """ECASE-041 — C5, red until P18 (the change goes through: two accounts share an address but for A–Z case): two accounts, both verified at session version 4; ``update_profile`` of the first with the second's address in another A–Z case answers ``(None, "Email already registered")`` and changes neither: address, verification and session version as they were."""
    their_address = _address("theirs")
    mine = await _add_account(engine, email=_address("mine"), verified=True, session_version=SESSION_VERSION)
    theirs = await _add_account(engine, email=their_address, verified=True, session_version=SESSION_VERSION)
    before = [await _stored(engine, mine), await _stored(engine, theirs)]

    outcome = await _update_profile(engine, mine, email=_case_variant(their_address, variant))

    assert outcome == (None, EMAIL_TAKEN), f"red until P18: another account's address in another A–Z case must be refused like an exact duplicate, got {outcome}"
    assert [await _stored(engine, mine), await _stored(engine, theirs)] == before, "a refused change must change neither account"


# =============================================================================
# F02 — THE ADMINISTRATOR WAITING FOR ITS SETUP, AND LIBREFOLIO_ADMIN_EMAIL IN ANOTHER CASE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", CONFIG_VARIANTS)
async def test_f02_takes_its_own_address_in_another_case_as_the_same_account(engine: AsyncEngine, variant: Variant) -> None:
    """ECASE-050 — F02 and C5, GUARD (green today, where the exact lookup finds nobody else; red if C3 is applied without ``_follow_variables`` telling the waiting account from another one): the empty instance creates the administrator ``admin.<hex>@example.com`` at NOW; a restart an hour later with ``LIBREFOLIO_ADMIN_EMAIL`` the same address in another A–Z case (local part changed, domain in lower case, as ``EmailStr`` gives it) finds the same account: ``PENDING``, no error logged — none of «LIBREFOLIO_ADMIN_EMAIL belongs to another account» —, the stored form follows the variable, still inactive, still a superuser, still the address's one account."""
    address, username = _address("admin"), f"admin_{_tag()}"
    created = await _bootstrap(engine, address, username, now=NOW)
    assert created.action == bootstrap_admin_service.BootstrapAction.CREATED and created.user_id is not None, f"setup: the empty instance creates its administrator: {created!r}"
    written = _case_variant(address, variant)

    with _captured(bootstrap_admin_service.logger) as events:
        result = await _bootstrap(engine, written, username, now=NOW + HOUR)

    assert (result.action, result.user_id) == (bootstrap_admin_service.BootstrapAction.PENDING, created.user_id), f"the restart finds the same waiting administrator: {result!r}"
    assert _errors(events) == [], f"its own address in another case is no other account's: no error may be logged: {_errors(events)}"
    stored = await _stored(engine, created.user_id)
    assert stored is not None and (stored.email, stored.is_active, stored.is_superuser) == (written, False, True), f"the stored form follows the variable; the account still waits, a superuser: {stored}"
    assert await _same_fold(engine, address) == [(created.user_id, written)], "the address keeps its one account"
    assert _showing(events, [address, written]) == [], "no event may show the address, in either form"


@pytest.mark.asyncio
async def test_f02_never_takes_another_accounts_address_in_another_case(engine: AsyncEngine) -> None:
    """ECASE-051 — F02 and C3, red until P18 (today the waiting administrator takes the address: two accounts then share it but for A–Z case): the administrator ``admin.<hex>@example.com`` waits for its setup, and an operator created ``boss`` with ``boss.<hex>@example.com``; a restart with ``LIBREFOLIO_ADMIN_EMAIL`` ``BOSS.<HEX>@example.com`` — boss's address but for A–Z — takes nothing: both accounts as they were, an error naming ``LIBREFOLIO_ADMIN_EMAIL``, the restart otherwise ``PENDING``; no event shows either address."""
    address, username = _address("admin"), f"admin_{_tag()}"
    created = await _bootstrap(engine, address, username, now=NOW)
    assert created.action == bootstrap_admin_service.BootstrapAction.CREATED and created.user_id is not None, f"setup: the empty instance creates its administrator: {created!r}"
    boss_address = _address("boss")
    boss = await _add_account(engine, email=boss_address, username=f"boss_{_tag()}")
    before = [await _stored(engine, created.user_id), await _stored(engine, boss)]

    with _captured(bootstrap_admin_service.logger) as events:
        result = await _bootstrap(engine, _local_upper(boss_address), username, now=NOW + HOUR)

    assert [await _stored(engine, created.user_id), await _stored(engine, boss)] == before, "red until P18: boss's address in another case belongs to boss: the waiting administrator must keep its own, and boss stays as it was"
    assert (result.action, result.user_id) == (bootstrap_admin_service.BootstrapAction.PENDING, created.user_id), f"the conflict changes nothing else: {result!r}"
    assert any(ADMIN_EMAIL_VARIABLE in str(event.get("event")) for event in _errors(events)), f"the conflict must be logged as an error naming {ADMIN_EMAIL_VARIABLE}: {_logged(events)}"
    assert _showing(events, [address, boss_address]) == [], "no event may show an address, in any form"
