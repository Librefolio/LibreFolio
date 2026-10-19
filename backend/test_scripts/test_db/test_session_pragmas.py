"""H-51: every new SQLite connection of the process stops trusting the database's schema.

``backend/app/db/session.py`` registers ``set_sqlite_pragma()`` as a ``connect`` listener on the ``Engine`` class: every
engine of a process that imported the module runs it on every new DBAPI connection, the sync engine under the async one
included. Before H-51 it set ``foreign_keys=ON``, ``journal_mode=WAL`` and ``busy_timeout=30000``, not ``trusted_schema``,
which SQLite leaves at 1. SQLAlchemy 2.0.52's SQLite dialects (pysqlite, inherited by aiosqlite) register two Python functions
on every connection: ``regexp``, behind ``REGEXP`` and ``regexp_match``, and ``floor`` (``math.floor``, over SQLite's
built-in). With the schema trusted, the SQL a database's schema keeps — a ``CHECK``, a ``DEFAULT``, a generated column,
an index expression — may call them. A restored archive's schema is not LibreFolio's: the restore check (B-28) refuses
triggers, views and virtual tables by kind but does not read the expressions inside tables and indexes, and its plain
sqlite3 connections never evaluate a ``DEFAULT``. A column ``x INTEGER DEFAULT (regexp('^a$', 'b'))`` passes it; in the
server, every insert that leaves ``x`` out then runs SQLAlchemy's ``regexp`` on the archive's pattern and value, and a
catastrophic pattern holds the process.

The cure: ``set_sqlite_pragma()`` runs ``PRAGMA trusted_schema=OFF`` first, then the three PRAGMAs as before, then
``PRAGMA writable_schema=RESET``: the listener runs before the dialect registers ``regexp`` and ``floor``, and
``journal_mode`` reads the schema then, so the reset makes SQLite read it again at the next statement, with them
registered. SQLite then
refuses an application function called from the schema — from a ``DEFAULT`` when an insert needs it, from a ``CHECK`` or
an index expression as soon as it reads the schema, whatever the statement — while the built-in functions stay usable
there and a statement's own SQL keeps both Python functions. The pins, each through a ``sync`` and an ``async`` engine
(8: async only):

1. A new connection answers ``PRAGMA trusted_schema`` 0.
2. The archive's ``DEFAULT (regexp('^a$', 'b'))``: the INSERT that needs it is refused, «unsafe use of regexp()», and
   nothing is written.
3. The same with ``DEFAULT (floor(2.5))``.
4. ``CHECK (email REGEXP '^[a-z]+@x$')``: every statement is refused with the schema, a SELECT of another table included.
5. Guard: ``foreign_keys`` 1, ``journal_mode`` ``wal``, ``busy_timeout`` 30000, as before.
6. Guard: LibreFolio's kind of schema works: ``lower()`` in a unique index (009's ``ux_users_email_lower``), ``length()``
   in a CHECK, ``abs()`` in a DEFAULT.
7. Guard: a statement's own SQL still calls ``regexp`` (``REGEXP``, ``regexp_match``) and ``floor``.
8. Guard: the real schema, a new database taken to head by the real migrations, takes a user through an async engine.

How. Every database is a file under ``tmp_path``. The engines are made here as ``session.py`` makes the server's —
pysqlite and aiosqlite, ``NullPool``, so that every connection is a new DBAPI connection and goes through the listener —
and are disposed. An archive is written by a plain sqlite3 connection that brings its own deterministic ``regexp`` and
``floor``, as its author would: the file keeps only the SQL text. The state is read back by a plain sqlite3 connection,
which registers nothing. ``get_sync_engine`` and ``get_async_engine`` are tripwires: no lane database, no server, no
network. Isolation: pure.

Written by H. Red before the cure: 1-4; guards: 5-8, green before and after. Each red fails on an assertion that says
what happens today.
"""

from __future__ import annotations

import math
import re
import sqlite3
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn, Optional, Union

import pytest
from sqlalchemy import Engine, Executable, create_engine, literal, select, text
from sqlalchemy.exc import DatabaseError, DBAPIError, IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from backend.app.db import session as db_session  # importing it registers set_sqlite_pragma() for every engine of the process
from backend.test_scripts.test_db.alembic_harness import _migrate
from backend.test_scripts.test_utils import print_section, print_success

#: The two engines ``backend.app.db.session`` builds: ``get_sync_engine`` (pysqlite) and ``get_async_engine`` (aiosqlite,
#: the server's).
ENGINE_KINDS = ("sync", "async")
#: The PRAGMAs the listener sets before the cure, with their values: the cure leaves them as they are.
UNCHANGED_PRAGMAS: dict[str, Any] = {"foreign_keys": 1, "journal_mode": "wal", "busy_timeout": 30000}
PRAGMAS = ("trusted_schema", *UNCHANGED_PRAGMAS)
#: What reaches a test when SQLite refuses a statement: SQLAlchemy's wrapper, or the driver's own error should one escape it.
DRIVER_ERRORS = (DBAPIError, sqlite3.Error)

#: The archive of the H-51 probe: a column whose DEFAULT calls ``regexp``, which SQLite does not have and SQLAlchemy registers.
REGEXP_DEFAULT_ARCHIVE = """
BEGIN;
CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL, x INTEGER DEFAULT (regexp('^a$', 'b')));
INSERT INTO notes (body, x) VALUES ('written by the archive', 7);
COMMIT;
"""
#: The same with ``floor``, which SQLAlchemy registers over SQLite's built-in.
FLOOR_DEFAULT_ARCHIVE = """
BEGIN;
CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL, x INTEGER DEFAULT (floor(2.5)));
INSERT INTO notes (body, x) VALUES ('written by the archive', 7);
COMMIT;
"""
#: A CHECK calling ``REGEXP``, and another table beside it: a schema SQLite must refuse whole, whatever the statement.
REGEXP_CHECK_ARCHIVE = """
BEGIN;
CREATE TABLE members (id INTEGER PRIMARY KEY, email TEXT NOT NULL CHECK (email REGEXP '^[a-z]+@x$'));
CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL);
INSERT INTO members (email) VALUES ('author@x');
INSERT INTO notes (body) VALUES ('written by the archive');
COMMIT;
"""
#: Through an app engine, on that archive: a SELECT of the other table, an address the CHECK accepts, one it refuses.
CHECK_ARCHIVE_STATEMENTS = (
    ("SELECT count(*) FROM notes", {}),
    ("INSERT INTO members (email) VALUES (:email)", {"email": "alice@x"}),
    ("INSERT INTO members (email) VALUES (:email)", {"email": "Mallory@elsewhere"}),
)
#: LibreFolio's kind of schema, built-in functions only: ``lower()`` in a unique index, as 009's ``ux_users_email_lower``,
#: ``length()`` in a CHECK, ``abs()`` in a DEFAULT.
BUILTINS_SCHEMA = """
BEGIN;
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, email VARCHAR NOT NULL CHECK (length(email) >= 3), login_count INTEGER NOT NULL DEFAULT (abs(-2)));
CREATE UNIQUE INDEX ux_users_email_lower ON users (lower(email));
COMMIT;
"""
INSERT_EMAIL = "INSERT INTO users (email) VALUES (:email)"
#: A statement's own SQL calling the two Python functions, and what it answers.
TOP_LEVEL_CALLS = (
    ("SELECT 'abc' REGEXP '^a'", ((1,),)),
    (select(literal("abc").regexp_match("^a")), ((True,),)),
    ("SELECT floor(2.7)", ((2,),)),
)
#: A user as the schema at head requires one: every other column of ``users`` has a default or takes NULL.
INSERT_ACCOUNT = "INSERT INTO users (username, email, hashed_password, created_at, updated_at) VALUES (:username, :email, :hashed_password, :created_at, :updated_at)"
STAMP = "2026-10-17 12:00:00.000000"
#: What the user written here holds for a hash: nobody signs in with it.
MARKER_HASH = "$argon2id$h51-marker"


# =============================================================================
# HELPERS — app engines on private files, and what a statement did through them
# =============================================================================


@dataclass(frozen=True)
class Outcome:
    """What one statement did through an app engine: the rows it answered, or the class and the message of what refused it.

    Never the exception itself: its traceback holds the frames that held the connection.
    """

    statement: str
    rows: tuple[tuple[Any, ...], ...] = ()
    error: Optional[type[BaseException]] = None
    message: str = ""

    @property
    def refused(self) -> bool:
        return self.error is not None

    def refused_as(self, error: type[BaseException], *fragments: str) -> bool:
        """Refused with ``error`` or a subclass of it, by a message that holds every fragment, whatever their case."""
        return self.error is not None and issubclass(self.error, error) and all(fragment.lower() in self.message.lower() for fragment in fragments)

    def __str__(self) -> str:
        if self.error is None:
            return f"{self.statement} → went through, answering {list(self.rows)}"
        return f"{self.statement} → {self.error.__name__}: {self.message}"


def _refusal(statement: str, error: BaseException) -> Outcome:
    """``statement`` refused by ``error``: its class, and the driver's message, which SQLAlchemy keeps in ``orig``."""
    driver_error = getattr(error, "orig", None)
    return Outcome(statement, error=type(error), message=str(driver_error if driver_error is not None else error))


def _sync_engine(db: Path) -> Engine:
    """An engine of ``db`` as ``get_sync_engine`` builds one: pysqlite, ``NullPool`` — every connection a new one, through the listener."""
    return create_engine(f"sqlite:///{db}", poolclass=NullPool)


def _async_engine(db: Path) -> AsyncEngine:
    """An engine of ``db`` as ``get_async_engine`` builds the server's: aiosqlite over pysqlite, ``NullPool``."""
    return create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)


def _sync_one(db: Path, label: str, statement: Executable, parameters: Mapping[str, Any]) -> Outcome:
    """``statement`` on a new connection of a sync app engine of ``db``, committed if it goes through; the engine disposed."""
    engine = _sync_engine(db)
    try:
        with engine.begin() as conn:
            result = conn.execute(statement, dict(parameters))
            rows = tuple(tuple(row) for row in result) if result.returns_rows else ()
    except DRIVER_ERRORS as error:
        return _refusal(label, error)
    finally:
        engine.dispose()
    return Outcome(label, rows=rows)


async def _async_one(db: Path, label: str, statement: Executable, parameters: Mapping[str, Any]) -> Outcome:
    """``statement`` on a new connection of an async app engine of ``db``, committed if it goes through; the engine disposed."""
    engine = _async_engine(db)
    try:
        async with engine.begin() as conn:
            result = await conn.execute(statement, dict(parameters))
            rows = tuple(tuple(row) for row in result) if result.returns_rows else ()
    except DRIVER_ERRORS as error:
        return _refusal(label, error)
    finally:
        await engine.dispose()
    return Outcome(label, rows=rows)


async def _one(kind: str, db: Path, statement: Union[str, Executable], **parameters: Any) -> Outcome:
    """``statement`` with ``parameters`` on a new connection of a ``kind`` app engine of ``db``, ``sync`` or ``async``: what it did."""
    label = f"{statement} {parameters}" if parameters else str(statement)
    executable = text(statement) if isinstance(statement, str) else statement
    if kind == "sync":
        return _sync_one(db, label, executable, parameters)
    return await _async_one(db, label, executable, parameters)


def _sync_pragmas(db: Path) -> list[dict[str, Any]]:
    """``PRAGMAS`` as two new connections of a sync app engine of ``db`` answer them, one after the other."""
    engine = _sync_engine(db)
    try:
        answers: list[dict[str, Any]] = []
        for _ in range(2):
            with engine.connect() as conn:
                answers.append({name: conn.exec_driver_sql(f"PRAGMA {name}").scalar() for name in PRAGMAS})
        return answers
    finally:
        engine.dispose()


async def _async_pragmas(db: Path) -> list[dict[str, Any]]:
    """``PRAGMAS`` as two new connections of an async app engine of ``db`` answer them, one after the other."""
    engine = _async_engine(db)
    try:
        answers: list[dict[str, Any]] = []
        for _ in range(2):
            async with engine.connect() as conn:
                answers.append({name: (await conn.exec_driver_sql(f"PRAGMA {name}")).scalar() for name in PRAGMAS})
        return answers
    finally:
        await engine.dispose()


async def _pragmas(kind: str, db: Path) -> list[dict[str, Any]]:
    """``PRAGMAS`` as two new connections of a ``kind`` app engine of ``db`` answer them."""
    if kind == "sync":
        return _sync_pragmas(db)
    return await _async_pragmas(db)


# =============================================================================
# HELPERS — the archive's author, and plain reads
# =============================================================================


def _author_regexp(pattern: str, value: Optional[str]) -> Optional[int]:
    """The archive author's ``regexp``: SQLite calls ``regexp(pattern, value)`` for ``value REGEXP pattern``."""
    if value is None:
        return None
    return 1 if re.search(pattern, value) else 0


def _archive(db: Path, script: str) -> Path:
    """``db`` as an archive's author writes it: a plain sqlite3 connection, the schema trusted, bringing its own deterministic ``regexp`` and ``floor`` to create and fill the tables. The file keeps the schema's SQL text, not the functions."""
    assert not db.exists(), f"setup: {db} already exists"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("PRAGMA trusted_schema=ON")
        conn.create_function("regexp", 2, _author_regexp, deterministic=True)
        conn.create_function("floor", 1, math.floor, deterministic=True)
        conn.executescript(script)
    return db


def _plain(db: Path, query: str) -> list[tuple[Any, ...]]:
    """``query`` answered by a plain sqlite3 connection: no function registered, none of the app's PRAGMAs."""
    assert db.is_file(), f"{db} does not exist"
    with closing(sqlite3.connect(db)) as conn:
        return conn.execute(query).fetchall()


def _table(db: Path, table: str) -> list[tuple[Any, ...]]:
    """Every row of ``table``, by rowid, read by a plain sqlite3 connection."""
    return _plain(db, f'SELECT * FROM "{table}" ORDER BY rowid')


async def _assert_default_refused(kind: str, db: Path, function: str) -> None:
    """Through a ``kind`` app engine, the INSERT that leaves ``notes.x`` to its DEFAULT, a call of ``function``, is refused as an unsafe use, and writes nothing."""
    before = _table(db, "notes")
    assert before == [(1, "written by the archive", 7)], f"setup: the archive holds its own row: {before}"
    outcome = await _one(kind, db, "INSERT INTO notes (body) VALUES (:body)", body=f"through the {kind} engine")
    after = _table(db, "notes")
    written = [row for row in after if row not in before]

    assert outcome.refused, f"red until H-51 — {kind} engine: an INSERT leaving x to the archive's DEFAULT, {function}(…), must be refused (trusted_schema off); it wrote {written}: SQLAlchemy's Python {function} ran on the archive's arguments"
    assert outcome.refused_as(OperationalError, f"unsafe use of {function}()"), f"{kind} engine: the INSERT must be refused as an unsafe use of {function}() from the schema: {outcome}"
    assert after == before, f"{kind} engine: the refused INSERT must leave notes as the archive left it, {before}: {after}"


# =============================================================================
# FIXTURES
# =============================================================================


def _lane_engine_tripwire(*_arguments: object, **_keywords: object) -> NoReturn:
    raise AssertionError("an engine of the lane's database was asked for: this file opens only its own temporary databases")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_sync_engine`` and ``get_async_engine`` raise: every engine here is made, and disposed, on a file under ``tmp_path``."""
    monkeypatch.setattr(db_session, "get_sync_engine", _lane_engine_tripwire)
    monkeypatch.setattr(db_session, "get_async_engine", _lane_engine_tripwire)


@pytest.fixture
def at_head(tmp_path: Path) -> Path:
    """A new database taken to head by the real migrations, in this process and under the listener: the shared ``alembic_harness.py``, on this file alone, with foreign keys on."""
    db = tmp_path / "app.db"
    _migrate(db, "upgrade", "head")
    return db


# =============================================================================
# 1-4. RED BEFORE THE CURE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ENGINE_KINDS)
async def test_every_new_connection_answers_trusted_schema_0(kind: str, tmp_path: Path) -> None:
    """H51-1 — red until the cure: two new connections of a ``kind`` app engine, one after the other, answer ``PRAGMA trusted_schema`` 0. Today 1, SQLite's default: the database's schema may call SQLAlchemy's Python ``regexp`` and ``floor``."""
    print_section(f"H51-1: PRAGMA trusted_schema on new {kind} connections")
    answers = [pragmas["trusted_schema"] for pragmas in await _pragmas(kind, tmp_path / "app.db")]

    assert answers == [0, 0], f"red until H-51 — {kind} engine: every new connection must answer PRAGMA trusted_schema 0, answered {answers}: at 1, SQLite's default, the database's schema may call SQLAlchemy's Python regexp and floor"
    print_success(f"{kind}: trusted_schema 0 on every new connection")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ENGINE_KINDS)
async def test_a_default_calling_regexp_refuses_the_insert_that_needs_it(kind: str, tmp_path: Path) -> None:
    """H51-2 — red until the cure: the probe's archive, ``notes.x INTEGER DEFAULT (regexp('^a$', 'b'))``. Through a ``kind`` app engine, an INSERT that leaves ``x`` out is refused — ``OperationalError``, «unsafe use of regexp()» — and a plain read finds ``notes`` as the archive left it. Today it is written with ``x`` 0: SQLAlchemy's Python ``regexp`` ran the archive's pattern on the archive's value."""
    print_section(f"H51-2: DEFAULT (regexp(...)) through the {kind} engine")
    await _assert_default_refused(kind, _archive(tmp_path / "archive.db", REGEXP_DEFAULT_ARCHIVE), "regexp")
    print_success(f"{kind}: the INSERT that needs DEFAULT (regexp(...)) is refused, nothing written")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ENGINE_KINDS)
async def test_a_default_calling_floor_refuses_the_insert_that_needs_it(kind: str, tmp_path: Path) -> None:
    """H51-3 — red until the cure: the same with ``notes.x INTEGER DEFAULT (floor(2.5))``, where SQLAlchemy's ``floor`` stands over SQLite's built-in: refused, «unsafe use of floor()», nothing written. Today it is written with ``x`` 2 — a value the built-in would give too, so the test reads the refusal, not the value."""
    print_section(f"H51-3: DEFAULT (floor(...)) through the {kind} engine")
    await _assert_default_refused(kind, _archive(tmp_path / "archive.db", FLOOR_DEFAULT_ARCHIVE), "floor")
    print_success(f"{kind}: the INSERT that needs DEFAULT (floor(...)) is refused, nothing written")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ENGINE_KINDS)
async def test_a_check_calling_regexp_refuses_every_statement(kind: str, tmp_path: Path) -> None:
    """H51-4 — red until the cure: an archive whose ``members.email`` has ``CHECK (email REGEXP '^[a-z]+@x$')``, beside a table ``notes``. Through a ``kind`` app engine every statement is refused with the schema — ``DatabaseError``, «malformed database schema (members) - unsafe use of REGEXP()» —: a SELECT of ``notes``, an address the CHECK accepts, one it refuses; a plain read finds both tables as the archive left them. Today the SELECT answers, the first address is written and the second fails «CHECK constraint failed»: SQLAlchemy's Python ``regexp`` judges the archive's CHECK.

    SQLite refuses that schema only if it parses it with ``trusted_schema`` off and with ``regexp`` already registered on the connection: reading a schema, it passes over a function it does not know, and marks as the schema's only a call to a function it found — a call it did not mark later runs as if the statement had written it.
    """
    print_section(f"H51-4: CHECK (email REGEXP ...) through the {kind} engine")
    db = _archive(tmp_path / "archive.db", REGEXP_CHECK_ARCHIVE)
    before = (_table(db, "members"), _table(db, "notes"))
    assert before == ([(1, "author@x")], [(1, "written by the archive")]), f"setup: the archive holds its own rows: {before}"
    outcomes = [await _one(kind, db, statement, **parameters) for statement, parameters in CHECK_ARCHIVE_STATEMENTS]
    through = [str(outcome) for outcome in outcomes if not outcome.refused_as(DatabaseError, "malformed database schema (members)", "unsafe use of regexp()")]

    assert not through, f"red until H-51 — {kind} engine: with the archive's CHECK calling REGEXP, SQLite must refuse the schema, so every statement, a SELECT of another table first («malformed database schema (members) - unsafe use of REGEXP()»); what they did: {through}"
    after = (_table(db, "members"), _table(db, "notes"))
    assert after == before, f"{kind} engine: the refused statements must leave both tables as the archive left them, {before}: {after}"
    print_success(f"{kind}: the archive's schema is refused, whatever the statement")


# =============================================================================
# 5-8. GUARDS, GREEN BEFORE AND AFTER THE CURE
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ENGINE_KINDS)
async def test_the_other_pragmas_are_as_before(kind: str, tmp_path: Path) -> None:
    """H51-5 — guard: two new connections of a ``kind`` app engine answer ``foreign_keys`` 1, ``journal_mode`` ``wal`` and ``busy_timeout`` 30000, the values the listener set before the cure."""
    print_section(f"H51-5: the other PRAGMAs on new {kind} connections")
    answers = [{name: pragmas[name] for name in UNCHANGED_PRAGMAS} for pragmas in await _pragmas(kind, tmp_path / "app.db")]

    assert answers == [UNCHANGED_PRAGMAS, UNCHANGED_PRAGMAS], f"{kind} engine: every new connection must keep foreign_keys, journal_mode and busy_timeout as the listener sets them, {UNCHANGED_PRAGMAS}: {answers}"
    print_success(f"{kind}: foreign_keys 1, journal_mode wal, busy_timeout 30000")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ENGINE_KINDS)
async def test_librefolio_kind_of_schema_works_untrusted(kind: str, tmp_path: Path) -> None:
    """H51-6 — guard: a schema of LibreFolio's kind calls built-in functions only, and works with the schema untrusted. Through a ``kind`` app engine, with ``lower()`` in a unique index (as 009's ``ux_users_email_lower``), ``length()`` in a CHECK and ``abs()`` in a DEFAULT: ``a@x`` is written with the DEFAULT's 2, ``A@x`` is refused by the index and ``x`` by the CHECK, both ``IntegrityError``."""
    print_section(f"H51-6: built-in functions in the schema through the {kind} engine")
    db = _archive(tmp_path / "builtins.db", BUILTINS_SCHEMA)
    first = await _one(kind, db, INSERT_EMAIL, email="a@x")
    other_case = await _one(kind, db, INSERT_EMAIL, email="A@x")
    too_short = await _one(kind, db, INSERT_EMAIL, email="x")

    assert not first.refused, f"{kind} engine: built-in functions in the schema must stay usable: {first}"
    assert other_case.refused_as(IntegrityError, "ux_users_email_lower"), f"{kind} engine: A@x after a@x must be refused by the unique index on lower(email): {other_case}"
    assert too_short.refused_as(IntegrityError, "CHECK constraint failed"), f"{kind} engine: x must be refused by the CHECK on length(email): {too_short}"
    rows = _plain(db, "SELECT email, login_count FROM users ORDER BY id")
    assert rows == [("a@x", 2)], f"{kind} engine: users must hold a@x alone, with abs(-2) from its DEFAULT: {rows}"
    print_success(f"{kind}: lower(), length() and abs() work from the schema")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ENGINE_KINDS)
async def test_top_level_sql_still_calls_regexp_and_floor(kind: str, tmp_path: Path) -> None:
    """H51-7 — guard: ``trusted_schema`` limits only what the schema calls. Through a ``kind`` app engine, a statement's own SQL still calls SQLAlchemy's Python functions: ``'abc' REGEXP '^a'`` and ``regexp_match`` answer 1, ``floor(2.7)`` answers 2."""
    print_section(f"H51-7: regexp and floor in a statement's own SQL through the {kind} engine")
    db = tmp_path / "app.db"
    wrong: list[str] = []
    for statement, expected in TOP_LEVEL_CALLS:
        outcome = await _one(kind, db, statement)
        if outcome.refused or outcome.rows != expected:
            wrong.append(f"{outcome}, expected {list(expected)}")

    assert not wrong, f"{kind} engine: trusted_schema limits only what the schema calls, a statement's own SQL must still call SQLAlchemy's regexp and floor: {wrong}"
    print_success(f"{kind}: REGEXP, regexp_match and floor() answer in a statement's own SQL")


@pytest.mark.asyncio
async def test_the_schema_at_head_takes_a_user_through_the_async_engine(at_head: Path) -> None:
    """H51-8 — guard: LibreFolio's real schema — a new database taken to head by the real migrations, under the listener — through an async app engine, the server's. A user given the columns the head requires is written, and read back by the engine and by a plain read; the same address in another case is refused by ``ux_users_email_lower``."""
    print_section("H51-8: the schema at head through the async engine")
    index = _plain(at_head, "SELECT name FROM sqlite_master WHERE type = 'index' AND name = 'ux_users_email_lower'")
    assert index == [("ux_users_email_lower",)], f"setup: the database at head holds 009's index: {index}"
    alice = {"username": "h51_alice", "email": "h51.alice@example.com", "hashed_password": MARKER_HASH, "created_at": STAMP, "updated_at": STAMP}
    inserted = await _one("async", at_head, INSERT_ACCOUNT, **alice)
    read = await _one("async", at_head, "SELECT username, email, is_active, session_version FROM users WHERE username = :username", username="h51_alice")
    clash = await _one("async", at_head, INSERT_ACCOUNT, **{**alice, "username": "h51_bob", "email": "H51.Alice@Example.com"})

    assert not inserted.refused, f"the async engine must write a user into the schema at head: {inserted}"
    assert read.rows == (("h51_alice", "h51.alice@example.com", 1, 0),), f"the user must read back with the head's defaults, active and at session version 0: {read}"
    assert clash.refused_as(IntegrityError, "ux_users_email_lower"), f"the same address in another case must be refused by ux_users_email_lower: {clash}"
    rows = _plain(at_head, "SELECT username, email FROM users WHERE username IN ('h51_alice', 'h51_bob') ORDER BY id")
    assert rows == [("h51_alice", "h51.alice@example.com")], f"a plain read must find the one user written: {rows}"
    print_success("the schema at head takes a user through the async engine")
