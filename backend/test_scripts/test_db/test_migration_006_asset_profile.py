"""Migration ``006_release_1_4_0_schema``, step ``asset_profile``: the two tables of the asset profile (project 68, lot A2).

The 1.4 cycle has one revision (the developer's decision of 19/10/2026), and several workstreams each add a step of
their own to it (its docstring says how). This file pins ONLY what the step ``asset_profile`` creates — the tables
``asset_profile_updates`` and ``asset_enrichers`` and the index ``ix_asset_profile_updates_asset_key_read_on`` — and
never the whole schema at 006: what another step adds is that step's to pin. So a table set is asserted as a superset,
rows are compared on the columns they had before the upgrade, and a full schema comparison appears only after a
downgrade, at 005.

``asset_profile_updates``: one row per change of a profile voice. Rows are never updated: they are inserted, and deleted
to «forget» a change. ``id`` a plain ``INTEGER PRIMARY KEY`` (no AUTOINCREMENT: the census of
``test_autoincrement_schema`` stays as it is); ``asset_id`` NOT NULL → ``assets.id`` ON DELETE CASCADE; ``key`` VARCHAR
NOT NULL, no CHECK — the catalogue checks the voices, not the database; ``value`` TEXT NULL (JSON; NULL = left empty on
purpose); ``source`` VARCHAR NOT NULL (a plugin code, ``user`` or ``legacy``), no CHECK; ``user_id`` NULL → ``users.id``
ON DELETE SET NULL; ``read_on`` DATE NOT NULL; ``source_date`` DATE NULL; ``created_at`` DATETIME NOT NULL. One index,
not unique, on ``(asset_id, key, read_on)``.

``asset_enrichers``: one row per asset. ``asset_id`` INTEGER PRIMARY KEY → ``assets.id`` ON DELETE CASCADE; ``config`` and
``state`` TEXT NOT NULL DEFAULT ``'{}'``; ``updated_at`` DATETIME NOT NULL. No index: the primary key serves.

The contract pinned here:

1. The revision ``006_release_1_4_0_schema`` revises ``005_release_1_3_0_schema`` and is its only child, the chain
   keeps one head (guard); the revision holds the step ``asset_profile``, ``_upgrade_asset_profile`` and
   ``_downgrade_asset_profile`` called by ``upgrade()`` and ``downgrade()``.
2. A new database taken to 006 — by name, not ``head`` — has both tables with exactly those columns (name, declared
   type family, NOT NULL, the defaults of ``config`` and ``state``, primary key), the foreign keys with their ON DELETE,
   the index with its columns and no other index on either table, no CHECK on ``key`` or ``source``, and no
   AUTOINCREMENT in their SQL.
3. At work, with foreign keys on: deleting an asset deletes its rows in both tables; deleting a user keeps its profile
   rows with ``user_id`` NULL; a row for an asset that does not exist is refused; a key outside the catalogue and a
   NULL value are stored; two rows of one asset, key and day are stored; an enricher row written without
   ``config``/``state`` holds ``'{}'`` in both.
4. A populated 1.3 database (at 005: a user and its settings, a broker, assets with and without
   ``classification_params``, prices; plain SQL) upgraded to 006 keeps every row of every table it had (guard, green
   before and after), gets the two tables empty, and no foreign-key violation, integrity ``ok``.
5. Models = migration: ``SQLModel.metadata`` declares both tables and the index, and ``create_all`` builds them with
   the shape the migration gives them (``_full_shape``, and the defaults of every column).
6. The downgrade 006 → 005 removes both tables and the index and leaves every other object as a new database at 005
   has it; the populated database goes down keeping every other row, and up again, the two tables back and empty.
7. Every part checks before it acts: an upgrade run again over its own work changes no object and no row; an upgrade
   that finds one table, or both, or a table and its index already there completes with the shape of a new database
   at 006, a row it found kept; a downgrade that finds the index or a table already gone completes to 005.
8. The index serves the reads the profile store really runs (``services/assets/profile/store.py``, listed in the 006
   docstring), each searching the table through ``ix_asset_profile_updates_asset_key_read_on`` with the constraint the
   docstring states, never scanning it and never sorting (no ``USE TEMP B-TREE``): the index order is the store's
   (``read_on``, ``id``) order within a voice. (a) The rows of some assets and voices up to a day, ``ORDER BY asset_id,
   key, read_on, id`` → ``(asset_id=? AND key=? AND read_on<?)``; (b) the same with no voice named → ``(asset_id=?)``;
   (c) the first day of each asset among the voices asked (``start: "min"``), ``min(read_on) … GROUP BY asset_id`` →
   ``(asset_id=? AND key=?)``, a covering index allowed. «Now» of a voice is the last row of (a) or (b): its
   (``read_on``, ``id``) order is the steps' (consultant's decision).
9. The redundant-index check of ``db_schema_validate`` (``test_no_redundant_indexes``) passes on a database at 006; a
   guard runs it the same way on a database at 005.

Safety and fidelity: ``alembic_harness``. Every database is a file under ``tmp_path``; Alembic runs in this process on
that file alone — a connect listener refuses any other — with ``PRAGMA foreign_keys`` asserted 1 at every step, as
production migrates. Rows are written with plain SQL. The models are reached through ``SQLModel.metadata``, never by
importing a class the lot has not written yet. ``get_async_engine`` and ``get_sync_engine`` are tripwires: no lane
database.

Red until the cure: ``006_release_1_4_0_schema`` exists with no step, so every migration below goes through and the
tests fail on assertions — the tables, the index, the step functions, the models are missing; each test that needs the
tables passes a barrier first, so none of them passes on an empty database. Guards, green before and after: the chain
(1), the rows a 1.3 database keeps (4), the redundant-index check at 005 (9).
"""

from __future__ import annotations

import importlib
import inspect
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.test_scripts.test_db.alembic_harness import (
    Rows,
    _connect,
    _copy,
    _create_all,
    _foreign_keys,
    _foreign_keys_on,
    _full_shape,
    _index_list,
    _integrity,
    _migrate,
    _revision,
    _row_changes,
    _rows,
    _scripts,
    _table_info,
    _tables,
    _violations,
)
from backend.test_scripts.test_utils import print_section, print_success

REV_005 = "005_release_1_3_0_schema"
REV_006 = "006_release_1_4_0_schema"
STEP = "asset_profile"
UPGRADE_STEP, DOWNGRADE_STEP = f"_upgrade_{STEP}", f"_downgrade_{STEP}"

UPDATES = "asset_profile_updates"
ENRICHERS = "asset_enrichers"
NEW_TABLES = (UPDATES, ENRICHERS)
PROFILE_INDEX = "ix_asset_profile_updates_asset_key_read_on"
PROFILE_INDEX_COLUMNS = ("asset_id", "key", "read_on")
#: Alembic's own bookkeeping: its row changes with every step, and is asserted on its own.
BOOKKEEPING = frozenset({"alembic_version"})

#: A default the contract does not pin: the column's default is left to the implementation (models = migration still
#: compares it, test 5).
UNPINNED = object()


@dataclass(frozen=True)
class Column:
    """A column as the contract states it: the family of its declared type (``VARCHAR`` for ``VARCHAR(40)``), NOT NULL,
    its default as ``PRAGMA table_info`` reports it (``"'{}'"``, quotes included) or ``UNPINNED``, primary key. The NOT
    NULL of a primary-key column is not pinned: SQLite gives a NULL ``INTEGER PRIMARY KEY`` a rowid either way."""

    family: str
    not_null: bool
    default: Any
    primary_key: bool = False


CONTRACT: dict[str, dict[str, Column]] = {
    UPDATES: {
        "id": Column("INTEGER", True, UNPINNED, primary_key=True),
        "asset_id": Column("INTEGER", True, UNPINNED),
        "key": Column("VARCHAR", True, UNPINNED),
        "value": Column("TEXT", False, UNPINNED),
        "source": Column("VARCHAR", True, UNPINNED),
        "user_id": Column("INTEGER", False, UNPINNED),
        "read_on": Column("DATE", True, UNPINNED),
        "source_date": Column("DATE", False, UNPINNED),
        "created_at": Column("DATETIME", True, UNPINNED),
    },
    ENRICHERS: {
        "asset_id": Column("INTEGER", True, UNPINNED, primary_key=True),
        "config": Column("TEXT", True, "'{}'"),
        "state": Column("TEXT", True, "'{}'"),
        "updated_at": Column("DATETIME", True, UNPINNED),
    },
}
#: column: (target table, target column, ON DELETE)
FOREIGN_KEYS: dict[str, dict[str, tuple[str, str, str]]] = {
    UPDATES: {"asset_id": ("assets", "id", "CASCADE"), "user_id": ("users", "id", "SET NULL")},
    ENRICHERS: {"asset_id": ("assets", "id", "CASCADE")},
}
#: ``_index_list`` of each table: SQLite's own indexes included, so «no other index» is exact. ``asset_enrichers.asset_id``
#: is an ``INTEGER PRIMARY KEY``, the rowid: no automatic index.
INDEXES: dict[str, dict[str, tuple[bool, str, tuple[str, ...]]]] = {
    UPDATES: {PROFILE_INDEX: (False, "c", PROFILE_INDEX_COLUMNS)},
    ENRICHERS: {},
}

STAMP = "2026-11-10 09:30:00.000000"
INSERT_USER = "INSERT INTO users (username, email, hashed_password, created_at, updated_at) VALUES (?, ?, '$argon2id$test', ?, ?)"
INSERT_ASSET = "INSERT INTO assets (display_name, currency, asset_type, active, created_at, updated_at) VALUES (?, 'EUR', 'ETF', 1, ?, ?)"
INSERT_UPDATE = "INSERT INTO asset_profile_updates (asset_id, key, value, source, user_id, read_on, source_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
#: Only the columns without a default the contract pins: ``config`` and ``state`` come from their DEFAULT.
INSERT_ENRICHER = "INSERT INTO asset_enrichers (asset_id, updated_at) VALUES (?, ?)"

#: A populated 1.3 install, as plain SQL: a user and its settings, a broker, two assets with ``classification_params``
#: and one without, prices of each.
ROWS_1_3 = f"""
INSERT INTO users (id, username, email, hashed_password, created_at, updated_at)
    VALUES (1, 'profile_owner', 'profile_owner@example.test', '$argon2id$test', '{STAMP}', '{STAMP}');
INSERT INTO user_settings (user_id, base_currency, language, ui_preferences, created_at, updated_at)
    VALUES (1, 'EUR', 'it', '{{"theme":"dark"}}', '{STAMP}', '{STAMP}');
INSERT INTO brokers (id, name, created_at, updated_at) VALUES (1, 'Profile Broker', '{STAMP}', '{STAMP}');
INSERT INTO assets (id, display_name, currency, classification_params, asset_type, active, created_at, updated_at) VALUES
    (1, 'World Equity ETF', 'EUR', '{{"geographic_area":{{"distribution":{{"USA":"0.6","JPN":"0.4"}}}}}}', 'ETF', 1, '{STAMP}', '{STAMP}'),
    (2, 'Tech Stock', 'USD', '{{"sector_area":{{"distribution":{{"Technology":"1"}}}}}}', 'STOCK', 1, '{STAMP}', '{STAMP}'),
    (3, 'Plain Bond', 'EUR', NULL, 'BOND', 1, '{STAMP}', '{STAMP}');
INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) VALUES
    (1, '2026-11-02', 101.5, 'EUR', 'manual', '{STAMP}'),
    (1, '2026-11-03', 102.25, 'EUR', 'manual', '{STAMP}'),
    (2, '2026-11-03', 250.0, 'USD', 'manual', '{STAMP}'),
    (3, '2026-11-03', 99.875, 'EUR', 'manual', '{STAMP}');
"""

#: The statements the profile store runs (the 006 docstring lists them), each with its parameters and the constraint its
#: index search must report: the rows of some assets and voices up to a day, the same for every voice, and the first day
#: of each asset among the voices asked («start: min»).
_PROFILE_ROW_COLUMNS = "id, asset_id, key, value, source, user_id, read_on, source_date, created_at"
PROFILE_READS = [
    pytest.param(
        f"SELECT {_PROFILE_ROW_COLUMNS} FROM asset_profile_updates WHERE asset_id IN (?, ?) AND key IN (?, ?) AND read_on <= ? ORDER BY asset_id, key, read_on, id",
        (1, 2, "ter", "geography", "2026-11-16"),
        "(asset_id=? AND key=? AND read_on<?)",
        id="rows-of-some-voices-up-to-a-day",
    ),
    pytest.param(
        f"SELECT {_PROFILE_ROW_COLUMNS} FROM asset_profile_updates WHERE asset_id IN (?, ?) AND read_on <= ? ORDER BY asset_id, key, read_on, id",
        (1, 2, "2026-11-16"),
        "(asset_id=?)",
        id="rows-of-every-voice-up-to-a-day",
    ),
    pytest.param(
        "SELECT asset_id, min(read_on) FROM asset_profile_updates WHERE asset_id IN (?, ?) AND key IN (?) GROUP BY asset_id",
        (1, 2, "ter"),
        "(asset_id=? AND key=?)",
        id="first-day-of-each-asset",
    ),
]
#: An upgrade stopped half way: the objects of the step it had already created, by name, with the SQL a new database at
#: 006 holds for them.
STOPPED_UPGRADES = {
    "profile-table-without-its-index": (UPDATES,),
    "profile-table-and-its-index": (UPDATES, PROFILE_INDEX),
    "enrichers-table-only": (ENRICHERS,),
    "both-tables-without-the-index": (UPDATES, ENRICHERS),
}
#: A downgrade stopped half way: what it had already dropped.
STOPPED_DOWNGRADES = {
    "index-dropped": ("DROP INDEX ix_asset_profile_updates_asset_key_read_on",),
    "enrichers-dropped": ("DROP TABLE asset_enrichers",),
    "both-tables-dropped": ("DROP TABLE asset_enrichers", "DROP TABLE asset_profile_updates"),
}


# =============================================================================
# HELPERS
# =============================================================================


def _missing_tables(db: Path) -> list[str]:
    """The tables of the step that ``db`` does not hold."""
    present = _tables(db)
    return [table for table in NEW_TABLES if table not in present]


def _assert_profile_tables(db: Path) -> None:
    """Barrier: ``db`` holds the two tables of the step, or nothing that follows is about them."""
    missing = _missing_tables(db)
    assert not missing, f"red until A2: {db.parent.name} (at {_revision(db)}) has no {missing}: the step {STEP} of {REV_006} has not created them"


def _ran[ResultT](result: ResultT | str) -> ResultT:
    """The result of a fixture that needs the two tables, or the test fails with the reason the fixture could not."""
    if isinstance(result, str):
        pytest.fail(result, pytrace=False)
    return result


def _family(declared: str) -> str:
    """The family of a declared type: ``VARCHAR(40)`` → ``VARCHAR``."""
    found = re.match(r"\s*([A-Za-z]+)", declared)
    return found.group(1).upper() if found else declared


def _as_contract(db: Path, table: str) -> dict[str, Column]:
    """The columns of ``table`` read back as the contract states them, with the defaults the contract leaves unpinned
    marked ``UNPINNED``, and the NOT NULL of a primary key column as the contract writes it."""
    wanted = CONTRACT[table]
    read: dict[str, Column] = {}
    for name, declared in _table_info(db, table).items():
        expected = wanted.get(name)
        default = declared.default if expected is None or expected.default is not UNPINNED else UNPINNED
        not_null = expected.not_null if expected is not None and expected.primary_key and declared.primary_key else declared.not_null
        read[name] = Column(_family(declared.type), not_null, default, declared.primary_key)
    return read


def _table_sql(db: Path, table: str) -> str:
    with _connect(db) as conn:
        found = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    assert found is not None, f"barrier: {db.parent.name} has no {table}"
    return found[0]


def _objects(db: Path) -> list[tuple[Optional[str], ...]]:
    """Every row of ``sqlite_master`` as ``(type, name, tbl_name, sql)``, whitespace collapsed, by type and name."""
    with _connect(db) as conn:
        rows = conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    return [(kind, name, table, re.sub(r"\s+", " ", sql).strip() if sql else None) for kind, name, table, sql in rows]


def _of_the_step(objects: list[tuple[Optional[str], ...]]) -> list[tuple[Optional[str], ...]]:
    """The objects of the two tables, their indexes included."""
    return [entry for entry in objects if entry[2] in NEW_TABLES]


def _not_of_the_step(objects: list[tuple[Optional[str], ...]]) -> list[tuple[Optional[str], ...]]:
    """Every object but those of the two tables."""
    return [entry for entry in objects if entry[2] not in NEW_TABLES]


def _sql_of(db: Path, name: str) -> str:
    with _connect(db) as conn:
        found = conn.execute("SELECT sql FROM sqlite_master WHERE name = ?", (name,)).fetchone()
    assert found is not None and found[0], f"barrier: {db.parent.name} holds no {name} to copy"
    return found[0]


def _insert_user(conn: sqlite3.Connection, username: str) -> int:
    return conn.execute(INSERT_USER, (username, f"{username}@example.test", STAMP, STAMP)).lastrowid


def _insert_asset(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute(INSERT_ASSET, (name, STAMP, STAMP)).lastrowid


def _insert_update(conn: sqlite3.Connection, asset_id: int, key: str = "ter", value: Optional[str] = '"0.07"', *, source: str = "justetf", user_id: Optional[int] = None, read_on: str = "2026-11-10") -> int:
    return conn.execute(INSERT_UPDATE, (asset_id, key, value, source, user_id, read_on, "2026-10-31", STAMP)).lastrowid


def _count(conn: sqlite3.Connection, table: str, asset_id: int) -> int:
    return conn.execute(f"SELECT count(*) FROM {table} WHERE asset_id = ?", (asset_id,)).fetchone()[0]


@contextmanager
def _refused(conn: sqlite3.Connection, *fragments: str) -> Iterator[None]:
    """The statement in the block must fail with an integrity error naming every fragment; the transaction is rolled back."""
    with pytest.raises(sqlite3.IntegrityError) as refused:
        yield
    conn.rollback()
    assert all(fragment in str(refused.value) for fragment in fragments), f"refused for another reason: {refused.value}"


@contextmanager
def _environment_kept() -> Iterator[None]:
    """The process environment as it was before the block: importing ``db_schema_validate`` runs
    ``setup_test_database()``, which rewrites it (``configure_test_runtime``)."""
    saved = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


def _schema_validate() -> ModuleType:
    """``db_schema_validate``, imported here and not at module level: imported by name its ``test_*`` functions would be
    collected in this file and run on the lane's database."""
    with _environment_kept():
        return importlib.import_module("backend.test_scripts.test_db.db_schema_validate")


# =============================================================================
# FIXTURES
# =============================================================================


def _lane_database_tripwire(*_arguments: object, **_keywords: object) -> NoReturn:
    raise AssertionError("the lane's engine was asked for: this module works on its private files only")


@pytest.fixture(autouse=True)
def no_lane_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """``get_async_engine`` and ``get_sync_engine`` raise: every database here is a file under ``tmp_path``."""
    monkeypatch.setattr(db_session, "get_async_engine", _lane_database_tripwire, raising=False)
    monkeypatch.setattr(db_session, "get_sync_engine", _lane_database_tripwire, raising=False)


@pytest.fixture(scope="module")
def at_005(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database at 005. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("at-005") / "app.db"
    _migrate(db, "upgrade", REV_005)
    assert _revision(db) == REV_005, f"setup: the new database is at {_revision(db)}"
    return db


@pytest.fixture(scope="module")
def fresh_006(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to 006 by name, not to head. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("fresh-006") / "app.db"
    _migrate(db, "upgrade", REV_006)
    assert _revision(db) == REV_006, f"setup: the new database is at {_revision(db)}, not at {REV_006}"
    return db


@pytest.fixture(scope="module")
def created_by_models(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database built by ``SQLModel.metadata.create_all``, as the service suites build theirs. Read-only."""
    return _create_all(tmp_path_factory.mktemp("create-all") / "app.db")


@pytest.fixture(scope="module")
def populated_1_3(at_005: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A populated 1.3 install at 005 (``ROWS_1_3``). Read-only for the tests: ``_copy`` it to write."""
    db = _copy(at_005, tmp_path_factory.mktemp("populated-1.3") / "app.db")
    with _foreign_keys_on(db) as conn:
        conn.executescript(ROWS_1_3)
        with_params = conn.execute("SELECT count(*) FROM assets WHERE classification_params IS NOT NULL").fetchone()[0]
        without = conn.execute("SELECT count(*) FROM assets WHERE classification_params IS NULL").fetchone()[0]
        prices = conn.execute("SELECT count(*) FROM price_history").fetchone()[0]
    assert (with_params, without, prices) == (2, 1, 4), f"setup: two assets with classification_params, one without, four prices: {(with_params, without, prices)}"
    assert _revision(db) == REV_005 and _violations(db) == [], "setup: a consistent 1.3 install at 005"
    return db


@dataclass(frozen=True)
class Upgrade:
    """A copy of the populated 1.3 install, before and right after ``upgrade 006``."""

    db: Path
    rows_before: Rows
    rows_after: Rows
    violations: list[tuple[Any, ...]]
    integrity: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def upgraded_1_3(populated_1_3: Path, tmp_path_factory: pytest.TempPathFactory) -> Upgrade:
    db = _copy(populated_1_3, tmp_path_factory.mktemp("upgraded-1.3") / "app.db")
    rows_before = _rows(db)
    _migrate(db, "upgrade", REV_006)
    return Upgrade(db=db, rows_before=rows_before, rows_after=_rows(db), violations=_violations(db), integrity=_integrity(db))


@dataclass(frozen=True)
class RoundTrip:
    """A copy of the populated 1.3 install up to 006, given a profile row and an enricher row, down to 005, up again."""

    rows_at_005: Rows
    revision_down: str
    tables_down: set[str]
    rows_down: Rows
    violations_down: list[tuple[Any, ...]]
    integrity_down: list[tuple[Any, ...]]
    revision_again: str
    rows_again: Rows
    violations_again: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def round_trip(populated_1_3: Path, tmp_path_factory: pytest.TempPathFactory) -> RoundTrip | str:
    """The round trip; or, while the upgrade creates no table of the step, the reason: each test fails on it."""
    db = _copy(populated_1_3, tmp_path_factory.mktemp("round-trip") / "app.db")
    rows_at_005 = _rows(db)
    _migrate(db, "upgrade", REV_006)
    missing = _missing_tables(db)
    if missing:
        return f"red until A2: the populated 1.3 install upgraded to {REV_006} has no {missing}"
    with _foreign_keys_on(db) as conn:
        _insert_update(conn, 1, user_id=1)
        conn.execute(INSERT_ENRICHER, (1, STAMP))
        conn.commit()

    _migrate(db, "downgrade", REV_005)
    down = {"revision_down": _revision(db), "tables_down": _tables(db), "rows_down": _rows(db), "violations_down": _violations(db), "integrity_down": _integrity(db)}
    _migrate(db, "upgrade", REV_006)
    again = {"revision_again": _revision(db), "rows_again": _rows(db), "violations_again": _violations(db)}
    return RoundTrip(rows_at_005=rows_at_005, **down, **again)


# =============================================================================
# 1. THE REVISION AND ITS STEP
# =============================================================================


def test_006_revises_005_and_the_chain_keeps_one_head() -> None:
    """GUARD, green before and after: ``006_release_1_4_0_schema`` revises ``005`` and is its only child; one head."""
    print_section(f"The revision {REV_006}")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_006 in revisions, f"{REV_006} not found; the chain has {sorted(revisions)}"
    assert revisions[REV_006].down_revision == REV_005, f"{REV_006} must revise {REV_005}, revises {revisions[REV_006].down_revision!r}"
    children = sorted(revision for revision, script in revisions.items() if script.down_revision == REV_005)
    assert children == [REV_006], f"{REV_005} must have one child, {REV_006}: {children}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_006} revises {REV_005}; one head ({heads[0]})")


def test_006_holds_the_asset_profile_step() -> None:
    """The step is written as the revision's docstring asks: ``_upgrade_asset_profile`` and ``_downgrade_asset_profile``,
    each called on its own line of ``upgrade()`` and ``downgrade()``."""
    module = _scripts().get_revision(REV_006).module
    missing = [name for name in (UPGRADE_STEP, DOWNGRADE_STEP) if not callable(getattr(module, name, None))]
    assert not missing, f"red until A2: {REV_006} defines no {missing}"
    assert f"{UPGRADE_STEP}(" in inspect.getsource(module.upgrade), f"upgrade() of {REV_006} must call {UPGRADE_STEP}"
    assert f"{DOWNGRADE_STEP}(" in inspect.getsource(module.downgrade), f"downgrade() of {REV_006} must call {DOWNGRADE_STEP}"


# =============================================================================
# 2. THE TWO TABLES ON A NEW DATABASE
# =============================================================================


@pytest.mark.parametrize("table", NEW_TABLES)
def test_a_new_database_at_006_has_the_columns_of_the_contract(fresh_006: Path, table: str) -> None:
    """Exactly the columns of the contract: name, declared type family, NOT NULL, the defaults of ``config`` and
    ``state``, primary key."""
    print_section(f"{table}: columns")
    _assert_profile_tables(fresh_006)
    found = _as_contract(fresh_006, table)
    assert found == CONTRACT[table], f"{table}: the columns differ from the contract: expected {CONTRACT[table]}, found {found}"
    print_success(f"{table}: {len(found)} columns as the contract states them")


@pytest.mark.parametrize("table", NEW_TABLES)
def test_a_new_database_at_006_has_the_foreign_keys_with_their_on_delete(fresh_006: Path, table: str) -> None:
    """``asset_id`` → ``assets.id`` ON DELETE CASCADE on both tables; ``asset_profile_updates.user_id`` → ``users.id``
    ON DELETE SET NULL; no other foreign key."""
    _assert_profile_tables(fresh_006)
    found = _foreign_keys(fresh_006, table)
    assert found == FOREIGN_KEYS[table], f"{table}: foreign keys {found}, expected {FOREIGN_KEYS[table]}"


@pytest.mark.parametrize("table", NEW_TABLES)
def test_a_new_database_at_006_has_the_profile_index_and_no_other(fresh_006: Path, table: str) -> None:
    """``asset_profile_updates`` has one index, ``ix_asset_profile_updates_asset_key_read_on`` on ``(asset_id, key,
    read_on)``, not unique (several rows on one day are normal); ``asset_enrichers`` none: its primary key serves.
    SQLite's own indexes included, so «no other index» is exact."""
    _assert_profile_tables(fresh_006)
    found = _index_list(fresh_006, table)
    assert found == INDEXES[table], f"{table}: indexes {found}, expected {INDEXES[table]}"


@pytest.mark.parametrize("table", NEW_TABLES)
def test_a_new_database_at_006_has_no_check_on_key_or_source_and_no_autoincrement(fresh_006: Path, table: str) -> None:
    """No CHECK names ``key`` or ``source`` — the catalogue checks the voices, the database stores them —, and the
    table's SQL has no AUTOINCREMENT: ``id`` is a plain ``INTEGER PRIMARY KEY``, the AUTOINCREMENT census unchanged."""
    _assert_profile_tables(fresh_006)
    shape = _full_shape(fresh_006, table)
    assert shape is not None, f"barrier: {table} is there"
    checks = [(name, sql) for name, sql in shape["check constraints (name: sql)"] if re.search(r"\b(key|source)\b", sql)]
    assert checks == [], f"{table}: no CHECK may restrict key or source: {checks}"
    sql = _table_sql(fresh_006, table)
    assert "AUTOINCREMENT" not in sql.upper(), f"{table} must not be AUTOINCREMENT: {sql}"


# =============================================================================
# 3. THE TABLES AT WORK, FOREIGN KEYS ON
# =============================================================================


def test_deleting_an_asset_deletes_its_rows_in_both_tables(fresh_006: Path, tmp_path: Path) -> None:
    """ON DELETE CASCADE from ``assets``: the deleted asset's profile rows and enricher row go; another asset's stay."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    with _foreign_keys_on(db) as conn:
        kept, gone = _insert_asset(conn, "Kept ETF"), _insert_asset(conn, "Gone ETF")
        for asset in (kept, gone):
            _insert_update(conn, asset, "ter")
            _insert_update(conn, asset, "geography", '[{"code":"USA","weight":"1"}]')
            conn.execute(INSERT_ENRICHER, (asset, STAMP))
        conn.commit()

        conn.execute("DELETE FROM assets WHERE id = ?", (gone,))
        conn.commit()
        counts = {asset: (_count(conn, UPDATES, asset), _count(conn, ENRICHERS, asset)) for asset in (kept, gone)}

    assert counts == {kept: (2, 1), gone: (0, 0)}, f"(profile rows, enricher rows) by asset after deleting asset {gone}: {counts}"


def test_deleting_a_user_keeps_its_profile_rows_without_their_author(fresh_006: Path, tmp_path: Path) -> None:
    """ON DELETE SET NULL from ``users``: a change written by a user survives the account, ``user_id`` NULL."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    with _foreign_keys_on(db) as conn:
        author, other = _insert_user(conn, "profile_author"), _insert_user(conn, "profile_other")
        asset = _insert_asset(conn, "Edited ETF")
        by_author = _insert_update(conn, asset, "ter", source="user", user_id=author)
        by_other = _insert_update(conn, asset, "geography", source="user", user_id=other)
        conn.commit()

        conn.execute("DELETE FROM users WHERE id = ?", (author,))
        conn.commit()
        found = dict(conn.execute("SELECT id, user_id FROM asset_profile_updates WHERE asset_id = ?", (asset,)).fetchall())

    assert found == {by_author: None, by_other: other}, f"the deleted author's row must stay with user_id NULL, the other untouched: {found}"


@pytest.mark.parametrize("table", NEW_TABLES)
def test_a_row_for_an_asset_that_does_not_exist_is_refused(fresh_006: Path, tmp_path: Path, table: str) -> None:
    """With foreign keys on, neither table takes a row for an ``asset_id`` that ``assets`` does not hold."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    with _foreign_keys_on(db) as conn:
        absent = (conn.execute("SELECT coalesce(max(id), 0) FROM assets").fetchone()[0] or 0) + 1000
        with _refused(conn, "FOREIGN KEY constraint failed"):
            if table == UPDATES:
                _insert_update(conn, absent)
            else:
                conn.execute(INSERT_ENRICHER, (absent, STAMP))
            conn.commit()
        assert _count(conn, table, absent) == 0, f"{table}: the refused row must not be there"


def test_a_key_outside_the_catalogue_and_a_null_value_are_stored(fresh_006: Path, tmp_path: Path) -> None:
    """The database does not know the list of voices: ``future_voice`` from a source no plugin has yet is stored, and a
    NULL value — a voice left empty on purpose — too."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    with _foreign_keys_on(db) as conn:
        asset = _insert_asset(conn, "Future ETF")
        future = _insert_update(conn, asset, "future_voice", '"anything"', source="a_plugin_of_tomorrow")
        empty = _insert_update(conn, asset, "ter", None, source="user")
        conn.commit()
        found = {row_id: (key, value, source) for row_id, key, value, source in conn.execute("SELECT id, key, value, source FROM asset_profile_updates WHERE asset_id = ?", (asset,))}

    assert found == {future: ("future_voice", '"anything"', "a_plugin_of_tomorrow"), empty: ("ter", None, "user")}, f"both rows must be stored as written: {found}"


def test_several_rows_of_one_asset_key_and_day_are_stored(fresh_006: Path, tmp_path: Path) -> None:
    """Two changes of one voice on one day are two rows: the index is not unique."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    with _foreign_keys_on(db) as conn:
        asset = _insert_asset(conn, "Busy ETF")
        first = _insert_update(conn, asset, "ter", '"0.07"', read_on="2026-11-10")
        second = _insert_update(conn, asset, "ter", '"0.12"', source="user", read_on="2026-11-10")
        conn.commit()
        found = conn.execute("SELECT id, value FROM asset_profile_updates WHERE asset_id = ? AND key = 'ter' AND read_on = '2026-11-10' ORDER BY id", (asset,)).fetchall()

    assert found == [(first, '"0.07"'), (second, '"0.12"')], f"both changes of the day must be stored: {found}"


def test_an_enricher_row_written_without_config_and_state_holds_empty_objects(fresh_006: Path, tmp_path: Path) -> None:
    """``config`` and ``state`` default to ``'{}'``: a row written with its asset and ``updated_at`` only holds two
    empty JSON objects, never NULL."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    with _foreign_keys_on(db) as conn:
        asset = _insert_asset(conn, "Enriched ETF")
        conn.execute(INSERT_ENRICHER, (asset, STAMP))
        conn.commit()
        found = conn.execute("SELECT config, state FROM asset_enrichers WHERE asset_id = ?", (asset,)).fetchone()

    assert found == ("{}", "{}"), f"config and state must default to '{{}}': {found}"


# =============================================================================
# 4. A POPULATED 1.3 DATABASE UPGRADED
# =============================================================================


def test_a_populated_1_3_database_keeps_every_row_of_every_table(upgraded_1_3: Upgrade) -> None:
    """GUARD, green before and after: every table the 1.3 install had is there, every row identical on the columns it
    had (another step of 006 may add a column: its values are that step's to pin)."""
    print_section("A populated 1.3 database upgraded to 006")
    before, after = upgraded_1_3.rows_before, upgraded_1_3.rows_after
    lost = sorted(set(before) - set(after))
    assert lost == [], f"the upgrade lost the tables {lost}"
    changes = _row_changes(before, after, set(before) - BOOKKEEPING, columns_of=before)
    assert not changes, f"the upgrade changed rows: {changes}"
    assert _revision(upgraded_1_3.db) == REV_006
    print_success(f"{len(set(before) - BOOKKEEPING)} tables, every row kept")


def test_a_populated_1_3_database_gets_the_two_tables_empty_and_no_violation(upgraded_1_3: Upgrade) -> None:
    """The two tables are there and empty — the upgrade writes no profile —; ``foreign_key_check`` empty, integrity ``ok``."""
    after = upgraded_1_3.rows_after
    missing = [table for table in NEW_TABLES if table not in after]
    assert not missing, f"red until A2: the upgraded 1.3 install has no {missing}"
    filled = {table: len(after[table][1]) for table in NEW_TABLES if after[table][1]}
    assert filled == {}, f"the upgrade must leave the two tables empty: {filled}"
    assert upgraded_1_3.violations == [], f"foreign key violations: {upgraded_1_3.violations}"
    assert upgraded_1_3.integrity == [("ok",)], f"integrity_check: {upgraded_1_3.integrity}"


# =============================================================================
# 5. THE MODELS AND THE MIGRATION AGREE
# =============================================================================


def test_the_models_declare_the_two_tables_and_the_index() -> None:
    """``SQLModel.metadata`` holds both tables, and ``asset_profile_updates`` declares the index by its name."""
    declared = {table: SQLModel.metadata.tables.get(table) for table in NEW_TABLES}
    missing = sorted(table for table, found in declared.items() if found is None)
    assert not missing, f"red until A2: the models declare no {missing}"
    names = {index.name for index in declared[UPDATES].indexes}
    assert PROFILE_INDEX in names, f"the model of {UPDATES} must declare {PROFILE_INDEX}: {sorted(names)}"


@pytest.mark.parametrize("table", NEW_TABLES)
def test_the_models_and_the_migration_build_the_same_table(fresh_006: Path, created_by_models: Path, table: str) -> None:
    """``create_all`` and ``alembic upgrade 006`` build ``table`` alike: ``_full_shape`` (columns and nullability,
    primary key, foreign keys and ON DELETE, indexes, unique sets, CHECKs, declared types) and the default of every
    column, which ``_full_shape`` does not read. The service suites build their databases with ``create_all``."""
    print_section(f"{table}: migration = models")
    migrated, modelled = _full_shape(fresh_006, table), _full_shape(created_by_models, table)
    assert migrated is not None and modelled is not None, f"red until A2: {table} is built by the migration: {migrated is not None}; by the models: {modelled is not None}"
    differences = {key: {"migration": migrated[key], "models": modelled.get(key)} for key in migrated if migrated[key] != modelled.get(key)}
    assert not differences, f"{table}: the migration and the models disagree on {differences}"
    defaults = {origin: {name: column.default for name, column in _table_info(db, table).items()} for origin, db in (("migration", fresh_006), ("models", created_by_models))}
    assert defaults["migration"] == defaults["models"], f"{table}: the defaults differ: {defaults}"
    print_success(f"{table}: the same table both ways")


# =============================================================================
# 6. THE DOWNGRADE
# =============================================================================


def test_the_downgrade_of_a_new_database_removes_the_two_tables_and_leaves_005(fresh_006: Path, at_005: Path, tmp_path: Path) -> None:
    """``downgrade 005`` of a new database at 006: the two tables and the index are gone, and every other object of
    ``sqlite_master`` is what a new database at 005 holds, SQL text included (whitespace collapsed); the rows too."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005
    left = _of_the_step(_objects(db))
    assert left == [], f"the downgrade must remove both tables and their index: {left}"
    expected, found = _not_of_the_step(_objects(at_005)), _not_of_the_step(_objects(db))
    assert found == expected, f"every other object must be as at 005: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"
    changes = _row_changes(_rows(at_005), _rows(db), set(_rows(at_005)) - BOOKKEEPING, columns_of=_rows(at_005))
    assert not changes, f"the downgrade of a new database changed rows: {changes}"


def test_the_downgrade_of_a_populated_database_keeps_every_other_row(round_trip: RoundTrip | str) -> None:
    """The populated install at 006, given a profile row and an enricher row, goes down to 005: the two tables gone,
    every other row as it was at 005, no violation, integrity ``ok``."""
    trip = _ran(round_trip)
    assert trip.revision_down == REV_005
    assert not set(NEW_TABLES) & trip.tables_down, f"the downgrade must remove both tables: {sorted(set(NEW_TABLES) & trip.tables_down)}"
    changes = _row_changes(trip.rows_at_005, trip.rows_down, set(trip.rows_at_005) - BOOKKEEPING, columns_of=trip.rows_at_005)
    assert not changes, f"the downgrade changed other rows: {changes}"
    assert trip.violations_down == [] and trip.integrity_down == [("ok",)], f"violations {trip.violations_down}, integrity {trip.integrity_down}"


def test_upgrading_the_downgraded_database_again_brings_the_tables_back_empty(round_trip: RoundTrip | str) -> None:
    """Up again to 006: the two tables back and empty, every other row as at 005, no violation."""
    trip = _ran(round_trip)
    assert trip.revision_again == REV_006
    missing = [table for table in NEW_TABLES if table not in trip.rows_again]
    assert not missing, f"the upgrade again must create {missing}"
    filled = {table: trip.rows_again[table][1] for table in NEW_TABLES if trip.rows_again[table][1]}
    assert filled == {}, f"the tables come back empty: {filled}"
    changes = _row_changes(trip.rows_at_005, trip.rows_again, set(trip.rows_at_005) - BOOKKEEPING, columns_of=trip.rows_at_005)
    assert not changes, f"up again changed other rows: {changes}"
    assert trip.violations_again == []


# =============================================================================
# 7. EVERY PART CHECKS BEFORE IT ACTS
# =============================================================================


def test_the_upgrade_run_again_over_its_own_work_changes_nothing(fresh_006: Path, tmp_path: Path) -> None:
    """The whole revision applied, rows in both tables, then ``alembic_version`` set back to 005 by hand — an upgrade
    that wrote everything and stopped before Alembic recorded it —: ``upgrade`` goes through and changes no object of
    ``sqlite_master``, not even its SQL text, and no row."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    with _foreign_keys_on(db) as conn:
        asset = _insert_asset(conn, "Again ETF")
        _insert_update(conn, asset)
        conn.execute(INSERT_ENRICHER, (asset, STAMP))
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_005,))
        conn.commit()
    objects_before, rows_before = _objects(db), _rows(db)

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006, f"the upgrade over its own work must go through: {_revision(db)}"
    assert _objects(db) == objects_before, "the step run again must leave the schema as it found it"
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=rows_before)
    assert not changes, f"the step run again must change no row: {changes}"


@pytest.mark.parametrize("state", sorted(STOPPED_UPGRADES))
def test_an_upgrade_stopped_half_way_completes_with_the_shape_of_a_new_database(fresh_006: Path, at_005: Path, tmp_path: Path, state: str) -> None:
    """A database at 005 holding part of what the step creates — written with the SQL a new database at 006 holds —:
    ``upgrade 006`` goes through, the objects of the two tables are those of a new database at 006, and a profile row
    the run found is kept."""
    _assert_profile_tables(fresh_006)
    created = STOPPED_UPGRADES[state]
    statements = [_sql_of(fresh_006, name) for name in created]
    db = _copy(at_005, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        for statement in statements:
            conn.execute(statement)
        survivor = None
        if UPDATES in created:
            survivor = _insert_update(conn, _insert_asset(conn, "Survivor ETF"))
        conn.commit()
    assert _revision(db) == REV_005, "setup: the run stopped before Alembic recorded the revision"

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006, f"the upgrade must go through: {_revision(db)}"
    expected, found = _of_the_step(_objects(fresh_006)), _of_the_step(_objects(db))
    assert found == expected, f"the two tables must end as on a new database at 006: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"
    if survivor is not None:
        with _connect(db) as conn:
            kept = conn.execute("SELECT id, key FROM asset_profile_updates").fetchall()
        assert kept == [(survivor, "ter")], f"the table found must be kept with its rows: {kept}"


@pytest.mark.parametrize("state", sorted(STOPPED_DOWNGRADES))
def test_a_downgrade_stopped_half_way_completes_to_005(fresh_006: Path, at_005: Path, tmp_path: Path, state: str) -> None:
    """A downgrade that had already dropped the index, or a table, or both, the revision still 006: ``downgrade 005``
    goes through, nothing of the step is left, every other object as at 005."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)
    assert PROFILE_INDEX in _index_list(db, UPDATES), f"red until A2: {PROFILE_INDEX} is not on a new database at 006"
    with _foreign_keys_on(db) as conn:
        for statement in STOPPED_DOWNGRADES[state]:
            conn.execute(statement)
        conn.commit()
    assert _revision(db) == REV_006, "setup: the downgrade stopped before Alembic recorded it"

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005
    assert _of_the_step(_objects(db)) == [], f"nothing of the step may be left: {_of_the_step(_objects(db))}"
    expected, found = _not_of_the_step(_objects(at_005)), _not_of_the_step(_objects(db))
    assert found == expected, f"every other object must be as at 005: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"


# =============================================================================
# 8. THE INDEX SERVES THE PROFILE READS
# =============================================================================


@pytest.mark.parametrize(("query", "parameters", "constraint"), PROFILE_READS)
def test_the_profile_read_searches_through_the_index(fresh_006: Path, query: str, parameters: tuple[Any, ...], constraint: str) -> None:
    """``EXPLAIN QUERY PLAN`` of each statement the store runs reports ``SEARCH asset_profile_updates USING (COVERING)
    INDEX ix_asset_profile_updates_asset_key_read_on`` with the constraint the 006 docstring states, no scan of the
    table, and no temporary B-tree: the index order is the order the store reads in."""
    _assert_profile_tables(fresh_006)
    assert PROFILE_INDEX in _index_list(fresh_006, UPDATES), f"red until A2: a new database at 006 has no {PROFILE_INDEX}"
    with _connect(fresh_006) as conn:
        plan = [detail for _id, _parent, _unused, detail in conn.execute(f"EXPLAIN QUERY PLAN {query}", parameters)]

    search = re.compile(rf"SEARCH {UPDATES} USING (COVERING )?INDEX {PROFILE_INDEX} {re.escape(constraint)}$")
    assert any(search.match(detail) for detail in plan), f"the read must search {UPDATES} through {PROFILE_INDEX} {constraint}: {plan}"
    assert not any(detail.startswith(f"SCAN {UPDATES}") for detail in plan), f"the read must not scan {UPDATES}: {plan}"
    assert not any("TEMP B-TREE" in detail for detail in plan), f"the read must come in the index order, with no sort: {plan}"


# =============================================================================
# 9. NO REDUNDANT INDEX
# =============================================================================


def _redundant_index_check(db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``db_schema_validate.test_no_redundant_indexes`` with its engine an engine of ``db``, a private file."""
    schema_validate = _schema_validate()
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    monkeypatch.setattr(schema_validate, "get_sync_engine", lambda: engine)
    try:
        schema_validate.test_no_redundant_indexes()
    finally:
        engine.dispose()


def test_the_redundant_index_check_runs_on_a_private_database_at_005(at_005: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GUARD, green before and after: the check, reached on a private file through its patched engine, passes on a new
    database at 005 — so a red at 006 is the step's, not the way the check is called."""
    _redundant_index_check(_copy(at_005, tmp_path / "app.db"), monkeypatch)


def test_the_redundant_index_check_passes_at_006(fresh_006: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The check on a copy of a new database at 006: the profile index repeats no other index of its table, nor a left
    prefix. Barrier: the index is there, or the check would pass on its absence."""
    db = _copy(fresh_006, tmp_path / "app.db")
    assert UPDATES in _tables(db) and PROFILE_INDEX in _index_list(db, UPDATES), f"red until A2: no {PROFILE_INDEX} at 006: the check would prove nothing about it"
    _redundant_index_check(db, monkeypatch)
