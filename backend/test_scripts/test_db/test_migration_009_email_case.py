"""Migration ``009_email_unique_ignoring_case``: one account per address, whatever its A–Z case (release 1.3, workstream A, lot P18; contract C6, C2, and the remedy of C7).

Until P18 ``users.email`` is ``UNIQUE`` and ``ix_users_email`` unique, both exact (SQLite's BINARY): an install can hold
``alice@example.com`` and ``Alice@example.com`` as two accounts. 009 makes the database refuse that from now on with a
unique index on ``lower(email)`` — SQLite's ``lower()``, which folds A–Z and nothing else —, an index it cannot build
over accounts that already collide. The contract pinned here:

1. The revision: id ``009_email_unique_ignoring_case`` (30 characters; ``alembic_version.version_num`` holds 32), in
   ``009_email_unique_ignoring_case.py``, on top of ``008_registration_invite_default``; the chain keeps one head,
   which is not named.
2. A new database at head has ``ux_users_email_lower``: unique, on every row (not partial), one key, the expression
   ``lower(email)``; ``ix_users_email`` stays, unique on ``email``. It is the index the ``User`` model declares: the same
   SQL as ``create_all`` builds. Plain SQL is refused by it, naming it — an ``INSERT`` or an ``UPDATE`` that would give
   an address another account has in another A–Z case —, and ``Émile@`` beside ``émile@`` is taken (the documented limit).
3. An install whose addresses are all distinct: the upgrade creates the index and changes no row of any table nor the
   columns of ``users`` (no new column), and leaves no foreign-key violation.
4. An install whose accounts collide: first the migration reads ``id``, ``username`` and ``email`` of every account and
   groups them by the same fold; a group of more than one stops it before it writes anything. The error names every
   account of every group by id and username — and no account outside a group —, and the remedy, ``./dev.py user
   set-email <username> <address>``. It shows no address, neither whole nor its local part, in any case: not in the
   error, not on the standard output or error, not in any structlog event nor any log record a server writes
   (workstream E's rule). Nothing is written: no index, ``alembic_version`` still 008, every object of the schema and
   every row of every table as it was.
5. ``Émile@example.com`` beside ``émile@example.com`` is no collision: the upgrade goes through.
6. The remedy works on the database 009 refused, in this process: ``scripts.user_cli.cmd_set_email(username, address)``,
   its ``get_async_engine`` pointed at that database, prints a line starting with ✅, changes the address as an email
   change does (the verification reset, the session version raised) and leaves the database at 008 — the ``user``
   commands do not migrate, only the server's start does. With one group left the upgrade still stops, naming that group
   alone; with none it goes through, and the index is there.
7. The downgrade drops the index and changes nothing else; upgrading again recreates it, the same; a second ``upgrade
   head`` changes nothing. The body run again over its own index — an upgrade interrupted after its ``CREATE INDEX``,
   which pysqlite runs outside the transaction, the version still 008 — goes through and leaves one index.
8. The real 1.1 install of ``test_post_migration``, taken to 008 by the real migrations, reaches 009 with the index and
   every row of every table as it was at 008.

Safety and fidelity: the harness of ``test_migration_005_accounts``, reused as it is. Every database is a file under
``tmp_path``; Alembic runs in this process on that file alone — a connect listener refuses any other — with
``PRAGMA foreign_keys`` 1, as production migrates. Rows are written with plain SQL, the way a real install holds them,
with ids of their own that nothing else prints (4101, 5201…). Each address has a random local part that no username
shares, so «no address» is looked for by its local part too. The remedy runs ``cmd_set_email`` on an engine of the
private file, disposed after it; meanwhile ``get_async_engine`` of ``backend.app.db.session`` is a tripwire, and the
email variables of the shell are removed.

Red until P18: Alembic cannot locate 009 (every test that migrates to it), or the head is 008 and an upgrade over
colliding accounts goes through (the refusals); ``user_cli`` has no ``cmd_set_email``. Each test says which.
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import sqlite3
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

import pytest
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from structlog.testing import capture_logs

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.app.services.email import flows as email_flows
from backend.app.services.email import verification as email_verification
from backend.test_scripts.test_db.test_migration_005_accounts import (
    BOOKKEEPING,
    Rows,
    _alembic_config,
    _alembic_connections,
    _connect,
    _copy,
    _foreign_keys_on,
    _lineage,
    _migrate,
    _revision,
    _rows,
    _scripts,
    _violations,
)
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_008 = "008_registration_invite_default"
REV_009 = "009_email_unique_ignoring_case"
INDEX = "ux_users_email_lower"
EXACT_INDEX = "ix_users_email"
#: ``CREATE UNIQUE INDEX ux_users_email_lower ON users (lower(email))`` as ``sqlite_master`` keeps it, read in lower case
#: and without quotes, brackets or spaces: how the statement is spelled does not matter, what it says does.
INDEX_SQL = "createuniqueindexux_users_email_loweronusers(lower(email))"
#: The remedy the refusal names (C7): ``./dev.py user set-email <username> <address>``.
REMEDY = "user set-email"
USER_CLI_MODULE = "scripts.user_cli"
STAMP = "2026-10-16 09:00:00.000000"
VERIFIED = "2026-10-02 08:00:00.000000"
#: What the accounts written as rows hold for a hash: nobody signs in with them.
MARKER_HASH = "$argon2id$p18-marker"
#: The session version every account written here starts at: the remedy's change shows as one more.
SESSION_VERSION = 1
#: An account as a row, in plain SQL: its own id, active, verified, at ``SESSION_VERSION`` (``_values``).
INSERT_ACCOUNT = "INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, session_version, email_verified_at, created_at, updated_at) VALUES (?, ?, ?, ?, 1, 0, ?, ?, ?, ?)"
#: The SQL loggers: below WARNING they print every statement and every row read — the addresses 009 reads included.
#: ``configure_logging`` sets them to WARNING: a running server never writes those records (UADM-030 pins it).
SQL_LOGGERS = ("aiosqlite", "sqlalchemy.engine", "sqlalchemy.pool")
#: Removed before every test: an email the remedy might send must find no transport, and no account variable applies.
INHERITED_PREFIXES = ("LIBREFOLIO_SMTP_", "LIBREFOLIO_ADMIN_")
INHERITED_VARIABLES = ("LIBREFOLIO_PUBLIC_URL", "LIBREFOLIO_BLOCKED", "LIBREFOLIO_REGISTRATION", "LIBREFOLIO_MAX_USERS")


# =============================================================================
# THE SCENES — accounts as an install holds them, written in plain SQL
# =============================================================================


def _tag() -> str:
    """Twelve random hex characters: time alone is not unique across workers."""
    return uuid.uuid4().hex[:12]


@dataclass(frozen=True)
class Account:
    """A ``users`` row: an id of its own, nowhere else in the error, and a username that shares nothing with its address."""

    id: int
    username: str
    email: str


@dataclass(frozen=True)
class Collisions:
    """Two groups whose addresses differ only in A–Z case — a pair, and a trio whose domains vary in case too — and an account alone."""

    pair: tuple[Account, Account]
    trio: tuple[Account, Account, Account]
    alone: Account

    @property
    def colliding(self) -> tuple[Account, ...]:
        return (*self.pair, *self.trio)

    @property
    def everyone(self) -> tuple[Account, ...]:
        return (*self.pair, *self.trio, self.alone)


def _collisions() -> Collisions:
    pair_box, trio_box, alone_box = f"dupe.{_tag()}", f"twin.{_tag()}", f"solo.{_tag()}"
    pair = (Account(4101, f"ina_{_tag()}", f"{pair_box}@example.com"), Account(4102, f"ivo_{_tag()}", f"{pair_box.upper()}@EXAMPLE.COM"))
    trio = (
        Account(5201, f"kai_{_tag()}", f"{trio_box}@example.com"),
        Account(5202, f"lea_{_tag()}", f"{trio_box.capitalize()}@Example.com"),
        Account(5203, f"max_{_tag()}", f"{trio_box.upper()}@example.COM"),
    )
    return Collisions(pair=pair, trio=trio, alone=Account(6301, f"zed_{_tag()}", f"{alone_box}@example.com"))


def _distinct() -> tuple[Account, ...]:
    """Three accounts whose addresses are distinct, whatever their case."""
    return (
        Account(7101, f"amy_{_tag()}", f"first.{_tag()}@example.com"),
        Account(7102, f"ben_{_tag()}", f"Second.{_tag()}@Example.com"),
        Account(7103, f"cyd_{_tag()}", f"THIRD.{_tag().upper()}@EXAMPLE.COM"),
    )


def _non_ascii_pair() -> tuple[Account, Account]:
    """``Émile.<hex>@example.com`` and ``émile.<hex>@example.com``: two addresses, É not being A–Z."""
    tag = _tag()
    return (Account(8101, f"emi_{_tag()}", f"Émile.{tag}@example.com"), Account(8102, f"eme_{_tag()}", f"émile.{tag}@example.com"))


def _values(account: Account) -> tuple[Any, ...]:
    """The parameters of ``INSERT_ACCOUNT`` for ``account``."""
    return (account.id, account.username, account.email, MARKER_HASH, SESSION_VERSION, VERIFIED, STAMP, STAMP)


def _insert(db: Path, accounts: Iterable[Account]) -> None:
    """The accounts as rows, in plain SQL with foreign keys on: active, verified, at session version 1."""
    with _foreign_keys_on(db) as conn:
        conn.executemany(INSERT_ACCOUNT, [_values(account) for account in accounts])
        conn.commit()


def _insert_neighbours(db: Path, owner: Account) -> None:
    """Rows of other tables that point at ``owner``: its settings, and a global setting it updated."""
    with _foreign_keys_on(db) as conn:
        conn.execute("INSERT INTO user_settings (user_id, base_currency, language, theme, avatar_url, created_at, updated_at) VALUES (?, 'EUR', 'it', 'dark', NULL, ?, ?)", (owner.id, STAMP, STAMP))
        conn.execute("INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id) VALUES ('default_language', 'it', 'str', NULL, ?, ?)", (STAMP, owner.id))
        conn.commit()


def _scene(at_008: Path, target: Path, accounts: Iterable[Account]) -> Path:
    """A copy of the database at 008 holding ``accounts``, the first with neighbours."""
    db = _copy(at_008, target)
    written = list(accounts)
    _insert(db, written)
    _insert_neighbours(db, written[0])
    return db


# =============================================================================
# HELPERS — the schema and the rows, read from SQLite itself
# =============================================================================


def _schema(db: Path) -> list[tuple[Any, ...]]:
    """Every object of ``sqlite_master``: type, name, table and SQL, by type and name."""
    with _connect(db) as conn:
        return conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()


def _index_sql(db: Path, name: str = INDEX) -> Optional[str]:
    with _connect(db) as conn:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)).fetchone()
    return None if row is None else row[0]


def _normalized(sql: str) -> str:
    """A ``CREATE INDEX`` in lower case, without quotes, brackets or spaces."""
    return re.sub(r"[\s\"`\[\]]", "", sql).lower()


def _index_flags(db: Path, name: str) -> Optional[tuple[bool, bool]]:
    """``(unique, partial)`` of the index ``name`` of ``users``, from ``PRAGMA index_list``; None when ``users`` has no such index."""
    with _connect(db) as conn:
        flags = {index: (bool(unique), bool(partial)) for _seq, index, unique, _origin, partial in conn.execute('PRAGMA index_list("users")')}
    return flags.get(name)


def _key_columns(db: Path, name: str) -> list[tuple[int, Optional[str]]]:
    """``(cid, column)`` of each key of the index ``name``, from ``PRAGMA index_xinfo``: an expression is cid -2, without a name."""
    with _connect(db) as conn:
        return [(cid, column) for _seqno, cid, column, _desc, _coll, key in conn.execute(f'PRAGMA index_xinfo("{name}")') if key]


def _index_violations(db: Path) -> list[str]:
    """What keeps ``db`` from holding the index of C2: unique, on every row, one key, the expression ``lower(email)``; and the exact index beside it."""
    sql = _index_sql(db)
    if sql is None:
        return [f"no {INDEX}"]
    violations = []
    if _normalized(sql) != INDEX_SQL:
        violations.append(f"{INDEX} is {sql!r}: not a unique index on lower(email)")
    if _index_flags(db, INDEX) != (True, False):
        violations.append(f"{INDEX} must be unique and cover every row (not partial): (unique, partial) = {_index_flags(db, INDEX)}")
    if _key_columns(db, INDEX) != [(-2, None)]:
        violations.append(f"{INDEX} must have one key, an expression: {_key_columns(db, INDEX)}")
    if _index_flags(db, EXACT_INDEX) != (True, False) or [column for _cid, column in _key_columns(db, EXACT_INDEX)] != ["email"]:
        violations.append(f"the exact {EXACT_INDEX} must stay, unique on email")
    return violations


def _users_columns(db: Path) -> list[tuple[Any, ...]]:
    with _connect(db) as conn:
        return conn.execute('PRAGMA table_info("users")').fetchall()


def _account_rows(db: Path) -> dict[int, tuple[str, Optional[str], int]]:
    """``{id: (email, email_verified_at, session_version)}`` of every account."""
    with _connect(db) as conn:
        return {user_id: (email, verified, version) for user_id, email, verified, version in conn.execute("SELECT id, email, email_verified_at, session_version FROM users")}


def _changed(before: Rows, after: Rows, *, skip: frozenset[str] = frozenset()) -> list[str]:
    """The tables, ``skip`` aside, whose columns or rows differ between ``before`` and ``after``."""
    return sorted(table for table in (set(before) | set(after)) - skip if before.get(table) != after.get(table))


def _refused_by_sql(db: Path, statement: str, parameters: tuple[Any, ...]) -> Optional[str]:
    """``statement`` in plain SQL, in a transaction of its own: None when SQLite took it (committed), else the message of its ``IntegrityError`` (rolled back)."""
    with _foreign_keys_on(db) as conn:
        try:
            with conn:
                conn.execute(statement, parameters)
        except sqlite3.IntegrityError as refused:
            return str(refused)
    return None


# =============================================================================
# HELPERS — an upgrade that must stop, and what it shows
# =============================================================================


@dataclass(frozen=True)
class Refusal:
    """What a stopped upgrade gives to read: its error with the chain of causes, what it printed, what it logged."""

    error: str
    output: str
    log: str


def _chain_text(error: BaseException) -> str:
    """The error and every error it was raised from or during: class names and messages."""
    texts: list[str] = []
    seen: set[int] = set()
    current: Optional[BaseException] = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        texts.append(f"{type(current).__name__}: {current}")
        current = current.__cause__ or current.__context__
    return "\n".join(texts)


def _written_by_a_server(record: logging.LogRecord) -> bool:
    """Every record a running server writes: all but those below WARNING of the SQL loggers and their children."""
    of_sql = any(record.name == name or record.name.startswith(f"{name}.") for name in SQL_LOGGERS)
    return record.levelno >= logging.WARNING or not of_sql


def _refused_upgrade(db: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> Refusal:
    """``alembic upgrade head`` on ``db``, in this process and on ``db`` alone, expected to stop: its error, and everything printed or logged meanwhile — stdlib records at DEBUG, structlog events."""
    caplog.set_level(logging.DEBUG)
    caplog.clear()
    capsys.readouterr()
    stopped: Optional[BaseException] = None
    with capture_logs() as events, _alembic_connections(db):
        try:
            command.upgrade(_alembic_config(db), "head")
        except Exception as error:  # whatever the migration raises: its message is the contract, not its class
            stopped = error
    printed = capsys.readouterr()
    if stopped is None:
        pytest.fail(f"red until P18: `alembic upgrade head` went through over accounts whose addresses differ only in A–Z case, and left the database at {_revision(db)}: migration 009 must stop before writing anything", pytrace=False)
    if isinstance(stopped, RuntimeError) and str(stopped).startswith("safety:"):
        raise stopped
    records = [f"{record.name}: {record.getMessage()} {vars(record)!r}" for record in caplog.records if _written_by_a_server(record)]
    return Refusal(error=_chain_text(stopped), output=printed.out + printed.err, log="\n".join([*records, repr(events)]))


def _named(text: str, account: Account) -> bool:
    """Whether ``text`` names ``account``: its username, and its id as a whole number."""
    return account.username in text and re.search(rf"(?<!\d){account.id}(?!\d)", text) is not None


def _showing(text: str, addresses: Iterable[str]) -> list[str]:
    """The ``addresses`` that ``text`` shows, whole or by their local part, in any case."""
    lowered = text.lower()
    return sorted({address for address in addresses if address.lower() in lowered or address.lower().partition("@")[0] in lowered})


def _assert_refusal(refusal: Refusal, *, named: Iterable[Account], unnamed: Iterable[Account], addresses: Iterable[str]) -> None:
    """The stop of C6: every account of ``named`` named by id and username, no username of ``unnamed``, the remedy, and no address anywhere."""
    missing = [(account.id, account.username) for account in named if not _named(refusal.error, account)]
    assert missing == [], f"the error must name every account of every group by id and username; it misses {missing}: {refusal.error}"
    outside = [account.username for account in unnamed if account.username in refusal.error]
    assert outside == [], f"the error must name no account outside a group, yet it names {outside}: {refusal.error}"
    assert REMEDY in refusal.error, f"the error must name the remedy, ./dev.py {REMEDY} <username> <address>: {refusal.error}"
    needles = list(addresses)
    for where, text in (("the error", refusal.error), ("the standard output and error", refusal.output), ("the log", refusal.log)):
        shown = _showing(text, needles)
        assert shown == [], f"{where} must show no address, whole or by its local part, in any case (workstream E's rule): it shows {shown}"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(autouse=True)
def quiet_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """None of the email and accounts variables of the shell that started the run: whatever the remedy might send finds no transport."""
    for name in list(os.environ):
        if name.startswith(INHERITED_PREFIXES) or name in INHERITED_VARIABLES:
            monkeypatch.delenv(name, raising=False)


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> AsyncEngine:
    raise AssertionError("get_async_engine() was called: that is the lane's database, not this test's private one")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` raises — in the session module, and in workstream E's modules that import it by name and open sessions of their own —: the remedy reaches its database through ``user_cli``'s own name only."""
    for module in (db_session, email_flows, email_verification):
        monkeypatch.setattr(module, "get_async_engine", _lane_database_tripwire, raising=False)


@pytest.fixture(scope="module")
def at_008(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database at 008, without accounts. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("at-008") / "app.db"
    _migrate(db, "upgrade", REV_008)
    assert _revision(db) == REV_008 and _account_rows(db) == {}, "setup: the database is at 008, without accounts"
    return db


@pytest.fixture(scope="module")
def fresh_head(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations. Read-only: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("fresh-head") / "app.db"
    _migrate(db, "upgrade", "head")
    return db


@pytest.fixture(scope="module")
def created_by_models(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database built by ``SQLModel.metadata.create_all``, as the service suites build theirs. Read-only."""
    db = tmp_path_factory.mktemp("create-all") / "app.db"
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
    finally:
        engine.dispose()
    return db


@pytest.fixture(scope="module")
def install_at_008(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The real 1.1 install of test_post_migration — every table, gaps, a deleted user —, taken to 008 by the real migrations. Read-only."""
    db = tmp_path_factory.mktemp("install-1.1") / "sqlite" / "app.db"
    _install_v110(db)
    _migrate(db, "upgrade", REV_008)
    assert _revision(db) == REV_008 and _account_rows(db), "setup: the 1.1 install is at 008, with its accounts"
    return db


@pytest.fixture
def user_cli() -> ModuleType:
    """``scripts/user_cli.py``, in this process, as the F02 tests import it."""
    return importlib.import_module(USER_CLI_MODULE)


async def _set_email(user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], db: Path, username: str, address: str) -> tuple[Any, str]:
    """``cmd_set_email(username, address)`` in this process, its ``get_async_engine`` an engine of ``db``, disposed after: what it answered, and what it printed."""
    set_email = getattr(user_cli, "cmd_set_email", None)
    if set_email is None:
        pytest.fail("red until P18: scripts/user_cli.py has no cmd_set_email (C7: ./dev.py user set-email <username> <address>)", pytrace=False)
    private = create_async_engine(f"sqlite+aiosqlite:///{db}", poolclass=NullPool)
    monkeypatch.setattr(user_cli, "get_async_engine", lambda: private)
    capsys.readouterr()
    try:
        answer = await set_email(username, address)
    finally:
        await private.dispose()
    return answer, capsys.readouterr().out


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_revision_009_sits_on_008_and_the_chain_keeps_one_head() -> None:
    """MIG009-001 — C6, red until P18 (Alembic knows no 009): ``009_email_unique_ignoring_case`` exists, in ``009_email_unique_ignoring_case.py``, fits ``version_num``, and revises ``008_registration_invite_default``; one head, not named."""
    print_section(f"MIG009-001: revision {REV_009}")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_009 in revisions, f"red until P18: revision {REV_009} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_009]
    assert len(script.revision) <= 32, f"{script.revision!r} is {len(script.revision)} characters: alembic_version.version_num is VARCHAR(32)"
    assert script.down_revision == REV_008, f"{REV_009} must revise {REV_008}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_009}.py", f"the revision id is the file name without .py, found in {Path(script.path).name}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_009} revises {REV_008}; one head ({heads[0]})")


# =============================================================================
# 2. THE INDEX: ON A NEW DATABASE, AS THE MODELS DECLARE IT, AND AT WORK
# =============================================================================


def test_a_new_database_at_head_has_the_unique_index_on_lower_email(fresh_head: Path) -> None:
    """MIG009-002 — C2 and C6, red until P18 (no such index at head): a new database taken to head includes 009 and holds ``ux_users_email_lower``: an index of ``users``, unique, on every row (not partial), with one key, the expression ``lower(email)``; ``ix_users_email`` stays, unique on ``email``."""
    print_section(f"MIG009-002: {INDEX} on a new database at head")

    assert REV_009 in _lineage(_revision(fresh_head)), f"red until P18: the head, {_revision(fresh_head)}, does not include {REV_009}"
    assert _index_violations(fresh_head) == [], f"a new database at head must hold the index of C2: {_index_violations(fresh_head)}"
    print_success(f"{INDEX} on lower(email), unique; {EXACT_INDEX} kept")


def test_the_migration_builds_the_index_the_models_declare(fresh_head: Path, created_by_models: Path) -> None:
    """MIG009-003 — C2, red until P18 (barrier: both databases must hold it, or their agreement proves nothing): ``ux_users_email_lower`` of a new database at head and the one ``create_all`` builds from the ``User`` model say the same, read as ``sqlite_master`` keeps them: the service suites build their databases with ``create_all``, and must test the index production has."""
    migrated, modelled = _index_sql(fresh_head), _index_sql(created_by_models)

    assert migrated is not None and modelled is not None, f"red until P18 — barrier: {INDEX} built by the migration: {migrated!r}; by the models: {modelled!r}"
    assert _normalized(migrated) == _normalized(modelled) == INDEX_SQL, f"the migration and the models must build the same index on lower(email): {migrated!r} and {modelled!r}"


def test_the_index_refuses_plain_sql_in_another_case_and_takes_the_non_ascii_pair(fresh_head: Path, tmp_path: Path) -> None:
    """MIG009-004 — C2, red until P18 (barrier: the index exists): on a database at head holding ``Box.<hex>@Example.com``, plain SQL is refused by ``ux_users_email_lower``, naming it — an ``INSERT`` of ``box.<hex>@example.com``, an ``UPDATE`` of another account to ``BOX.<HEX>@EXAMPLE.COM`` —, and nothing changes; ``Émile.<hex>@example.com`` and ``émile.<hex>@example.com`` go in as two addresses (the documented limit)."""
    db = _copy(fresh_head, tmp_path / "app.db")
    assert _index_sql(db) is not None, f"red until P18 — barrier: no {INDEX} at head, so neither a refusal nor the non-ASCII pair would say anything about it"
    tag = _tag()
    holder, other = Account(9101, f"hal_{_tag()}", f"Box.{tag}@Example.com"), Account(9102, f"oli_{_tag()}", f"other.{_tag()}@example.com")
    _insert(db, (holder, other))

    inserted = _refused_by_sql(db, "INSERT INTO users (username, email, hashed_password, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (f"new_{_tag()}", f"box.{tag}@example.com", MARKER_HASH, STAMP, STAMP))
    updated = _refused_by_sql(db, "UPDATE users SET email = ? WHERE id = ?", (f"BOX.{tag.upper()}@EXAMPLE.COM", other.id))
    pair = _non_ascii_pair()
    pair_refused = [_refused_by_sql(db, INSERT_ACCOUNT, _values(account)) for account in pair]

    assert inserted is not None and INDEX in inserted, f"an INSERT of the same address but for A–Z must be refused by {INDEX}: {inserted}"
    assert updated is not None and INDEX in updated, f"an UPDATE to the same address but for A–Z must be refused by {INDEX}: {updated}"
    rows = _account_rows(db)
    assert (rows[holder.id][0], rows[other.id][0]) == (holder.email, other.email), f"the refused statements must change nothing: {rows}"
    assert sorted(email for email, _verified, _version in rows.values() if email.lower().startswith(f"box.{tag}")) == [holder.email], "the address must keep its one account"
    assert pair_refused == [None, None], f"Émile… and émile… are two addresses (É is not A–Z): both must go in, refused: {pair_refused}"
    assert [rows[account.id][0] for account in pair] == [account.email for account in pair], "the non-ASCII pair is stored as written"


# =============================================================================
# 3. DISTINCT ADDRESSES: THE INDEX, AND NOTHING ELSE
# =============================================================================


def test_an_install_with_distinct_addresses_gets_the_index_and_nothing_else(at_008: Path, tmp_path: Path) -> None:
    """MIG009-005 — C6, red until P18 (Alembic cannot locate 009): a database at 008 whose three accounts' addresses are distinct — in lower, capitalised and upper case — with neighbours pointing at one of them, upgraded to 009: the database is at 009, the index of C2 is there, and no row of any table changes, nor the columns of ``users`` (no new column); no foreign-key violation."""
    print_section("MIG009-005: distinct addresses, upgraded to 009")
    db = _scene(at_008, tmp_path / "app.db", _distinct())
    rows_at_008, columns_at_008 = _rows(db), _users_columns(db)

    _migrate(db, "upgrade", REV_009)

    assert _revision(db) == REV_009, f"the upgrade must leave the database at {REV_009}: {_revision(db)!r}"
    assert _index_violations(db) == [], f"the upgrade must create the index of C2: {_index_violations(db)}"
    assert _changed(rows_at_008, _rows(db), skip=BOOKKEEPING) == [], f"009 must change no row: {_changed(rows_at_008, _rows(db), skip=BOOKKEEPING)}"
    assert _users_columns(db) == columns_at_008, "009 must add no column to users"
    assert _violations(db) == []
    print_success(f"at {REV_009}; {INDEX} created; every row as it was")


# =============================================================================
# 4. COLLIDING ACCOUNTS: THE UPGRADE STOPS, NAMES THEM, SHOWS NO ADDRESS, WRITES NOTHING
# =============================================================================


def test_colliding_accounts_stop_the_upgrade_before_anything_is_written(at_008: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    """MIG009-006 — C6, red until P18 (the head is 008: the upgrade goes through and the accounts keep colliding): a database at 008 holding a pair and a trio of accounts whose addresses differ only in A–Z case (the trio's domains too), an account alone, and neighbours: ``upgrade head`` stops. Its error names each of the five colliding accounts by id and username, not the account alone, and the remedy ``user set-email``; no address shows, whole or by its local part, in any case, in the error, the output or the log. Nothing is written: no ``ux_users_email_lower``, ``alembic_version`` still 008, every object of the schema and every row of every table as it was."""
    print_section("MIG009-006: colliding accounts stop the upgrade")
    scene = _collisions()
    db = _scene(at_008, tmp_path / "app.db", scene.everyone)
    rows_at_008, schema_at_008 = _rows(db), _schema(db)

    refusal = _refused_upgrade(db, capsys, caplog)

    _assert_refusal(refusal, named=scene.colliding, unnamed=[scene.alone], addresses=[account.email for account in scene.everyone])
    assert _index_sql(db) is None, f"a stopped upgrade must not leave {INDEX} behind"
    assert _revision(db) == REV_008, f"a stopped upgrade must leave the database at {REV_008}: {_revision(db)}"
    assert _schema(db) == schema_at_008, "a stopped upgrade must leave every object of the schema as it was"
    assert _changed(rows_at_008, _rows(db)) == [], f"a stopped upgrade must write no row: {_changed(rows_at_008, _rows(db))}"
    print_success("stopped; five accounts named, the remedy named, no address shown, nothing written")


def test_the_non_ascii_pair_does_not_stop_the_upgrade(at_008: Path, tmp_path: Path) -> None:
    """MIG009-007 — C6 and the documented limit, red until P18 (Alembic cannot locate 009): a database at 008 holding ``Émile.<hex>@example.com`` and ``émile.<hex>@example.com`` — two addresses, É not being A–Z — upgrades to 009: the index is there, both accounts as written; the index then refuses ``ÉMILE.<HEX>@EXAMPLE.COM`` (Émile's address but for A–Z), as it folds."""
    capital, small = _non_ascii_pair()
    db = _scene(at_008, tmp_path / "app.db", (capital, small))

    _migrate(db, "upgrade", REV_009)

    assert _index_violations(db) == [], f"the non-ASCII pair must not stop the upgrade, and the index must be there: {_index_violations(db)}"
    rows = _account_rows(db)
    assert (rows[capital.id][0], rows[small.id][0]) == (capital.email, small.email), "both accounts keep their address, as written"
    refused = _refused_by_sql(db, INSERT_ACCOUNT, _values(Account(8103, f"emu_{_tag()}", capital.email.upper())))
    assert refused is not None and INDEX in refused, f"{capital.email.upper()!r} is Émile's address but for A–Z: {INDEX} must refuse it: {refused}"


# =============================================================================
# 5. THE REMEDY: user set-email ON THE DATABASE 009 REFUSED
# =============================================================================


@pytest.mark.asyncio
async def test_set_email_on_the_refused_database_lets_the_upgrade_through(at_008: Path, tmp_path: Path, user_cli: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture) -> None:
    """MIG009-008 — C6 and C7, red until P18 (first barrier: the upgrade does not stop today; then ``cmd_set_email`` does not exist): the database of MIG009-006 is refused (barrier). ``cmd_set_email`` of the pair's second account to a new address, in this process on that database, prints a line starting with ✅, changes the address as an email change does — the verification reset, the session version one more —, and leaves the database at 008. The upgrade still stops, now naming the trio alone, not the pair. Two more ``cmd_set_email``, for the trio's second and third: the upgrade goes through, the index is there, and every account holds the address the remedy left."""
    print_section("MIG009-008: the remedy, user set-email, then the upgrade")
    scene = _collisions()
    db = _scene(at_008, tmp_path / "app.db", scene.everyone)
    _assert_refusal(_refused_upgrade(db, capsys, caplog), named=scene.colliding, unnamed=[scene.alone], addresses=[account.email for account in scene.everyone])
    moves = {account.id: f"moved.{_tag()}@example.com" for account in (scene.pair[1], *scene.trio[1:])}

    answer, printed = await _set_email(user_cli, monkeypatch, capsys, db, scene.pair[1].username, moves[scene.pair[1].id])

    assert answer, f"cmd_set_email must succeed on the database 009 refused — the model has no new column: {printed!r}"
    assert any(line.startswith("✅") for line in printed.splitlines()), f"a line must start with ✅: {printed!r}"
    assert _account_rows(db)[scene.pair[1].id] == (moves[scene.pair[1].id], None, SESSION_VERSION + 1), f"the address must change as an email change does: the verification reset, the session version one more: {_account_rows(db)[scene.pair[1].id]}"
    assert _revision(db) == REV_008, f"a user command must not migrate the database: {_revision(db)}"
    still = _refused_upgrade(db, capsys, caplog)
    _assert_refusal(still, named=scene.trio, unnamed=[*scene.pair, scene.alone], addresses=[account.email for account in scene.everyone] + list(moves.values()))

    for account in scene.trio[1:]:
        answer, printed = await _set_email(user_cli, monkeypatch, capsys, db, account.username, moves[account.id])
        assert answer and any(line.startswith("✅") for line in printed.splitlines()), f"cmd_set_email of {account.username} must succeed: {printed!r}"
    _migrate(db, "upgrade", "head")

    assert REV_009 in _lineage(_revision(db)), f"with no collision left the upgrade must go through: {_revision(db)}"
    assert _index_violations(db) == [], f"the index of C2 must be there: {_index_violations(db)}"
    addresses = {user_id: email for user_id, (email, _verified, _version) in _account_rows(db).items()}
    assert addresses == {account.id: moves.get(account.id, account.email) for account in scene.everyone}, f"every account holds the address the remedy left: {addresses}"
    print_success("set-email on the refused database, the upgrade through, the index there")


# =============================================================================
# 6. DOWN, UP AGAIN, AND THE BODY RUN TWICE
# =============================================================================


def test_the_downgrade_drops_the_index_and_the_upgrade_brings_it_back(at_008: Path, tmp_path: Path) -> None:
    """MIG009-009 — C6, red until P18 (Alembic cannot locate 009): distinct addresses upgraded to 009, then down to 008: the index is gone, the exact one stays, and the schema and every row of every table are as they were at 008; up to 009 again: the same index; then ``upgrade head`` twice: the second changes nothing, neither the schema nor a row."""
    print_section("MIG009-009: down, up again, and a second upgrade head")
    db = _scene(at_008, tmp_path / "app.db", _distinct())
    rows_at_008, schema_at_008 = _rows(db), _schema(db)

    _migrate(db, "upgrade", REV_009)
    first = _index_sql(db)
    assert _index_violations(db) == [], f"barrier: the upgrade did not create the index of C2, so the downgrade would have nothing to drop: {_index_violations(db)}"
    _migrate(db, "downgrade", REV_008)

    assert (_revision(db), _index_sql(db)) == (REV_008, None), f"the downgrade must drop {INDEX} and return to {REV_008}: {_revision(db)}, {_index_sql(db)!r}"
    assert _index_flags(db, EXACT_INDEX) == (True, False), f"the downgrade must leave the exact {EXACT_INDEX}"
    assert _schema(db) == schema_at_008, "after the downgrade every object of the schema must be as it was at 008"
    assert _changed(rows_at_008, _rows(db)) == [], f"the downgrade must leave every row as it was at 008: {_changed(rows_at_008, _rows(db))}"

    _migrate(db, "upgrade", REV_009)
    assert _index_sql(db) == first and _index_violations(db) == [], f"upgrading again must bring the same index back: {first!r} then {_index_sql(db)!r}"
    _migrate(db, "upgrade", "head")
    at_head = (_schema(db), _rows(db))
    _migrate(db, "upgrade", "head")
    assert (_schema(db), _rows(db)) == at_head, "a second upgrade head must change nothing"
    print_success("down: no index, every row kept; up: the same index; a second upgrade: nothing")


def test_the_body_run_again_over_its_own_index_goes_through(at_008: Path, tmp_path: Path) -> None:
    """MIG009-010 — C6, red until P18 (Alembic cannot locate 009): an upgrade interrupted after its ``CREATE INDEX`` — which pysqlite runs outside the transaction — leaves the index and the version 008; written so by hand (009 applied, then ``alembic_version`` set back to 008), the next ``upgrade`` to 009 goes through: one index, the same, the version recorded, and no row changed."""
    db = _scene(at_008, tmp_path / "app.db", _distinct())
    _migrate(db, "upgrade", REV_009)
    assert _index_violations(db) == [], f"barrier: the upgrade did not create the index of C2: {_index_violations(db)}"
    with _foreign_keys_on(db) as conn:
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_008,))
        conn.commit()
    rows_before, schema_before = _rows(db), _schema(db)

    _migrate(db, "upgrade", REV_009)

    assert _revision(db) == REV_009, f"the upgrade over its own index must go through: {_revision(db)}"
    assert _schema(db) == schema_before, "the body run again must leave the schema as it found it: one index, the same"
    assert _changed(rows_before, _rows(db), skip=BOOKKEEPING) == [], f"the body run again must change no row: {_changed(rows_before, _rows(db), skip=BOOKKEEPING)}"


# =============================================================================
# 7. THE REAL 1.1 INSTALL
# =============================================================================


def test_the_1_1_install_reaches_009_with_the_index_and_every_row(install_at_008: Path, tmp_path: Path) -> None:
    """MIG009-011 — C6 on real data, red until P18 (Alembic cannot locate 009): the 1.1 install of test_post_migration (four accounts, distinct addresses) taken to 008, then to 009: the index of C2, every row of every table as it was at 008, no foreign-key violation."""
    db = _copy(install_at_008, tmp_path / "sqlite" / "app.db")
    rows_at_008 = _rows(db)

    _migrate(db, "upgrade", REV_009)

    assert _revision(db) == REV_009
    assert _index_violations(db) == [], f"the 1.1 install must get the index of C2: {_index_violations(db)}"
    assert _changed(rows_at_008, _rows(db), skip=BOOKKEEPING) == [], f"009 must change no row of the 1.1 install: {_changed(rows_at_008, _rows(db), skip=BOOKKEEPING)}"
    assert _violations(db) == []
