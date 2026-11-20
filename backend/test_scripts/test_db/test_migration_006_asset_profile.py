"""Migration ``006_release_1_4_0_schema``, steps ``asset_profile`` (lot A2: the two tables of the asset profile) and
``asset_profile_legacy_copy`` (lot A4: ``classification_params`` copied into it), project 68.

The 1.4 cycle has one revision (the developer's decision of 19/10/2026), and several workstreams each add a step of
their own to it (its docstring says how). This file pins ONLY what the steps ``asset_profile`` and ``asset_profile_legacy_copy`` write (10); of ``asset_profile`` what it creates — the tables
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
   ``classification_params``, prices; plain SQL) upgraded to 006 keeps every row of every table it had, on every column
   but the one ``drop_classification_params`` drops (11), gets ``asset_enrichers`` empty and — since A4 — the legacy copy of its classification in
   ``asset_profile_updates`` (10), and no foreign-key violation, integrity ``ok``.
5. Models = migration: ``SQLModel.metadata`` declares both tables and the index, and ``create_all`` builds them with
   the shape the migration gives them (``_full_shape``, and the defaults of every column).
6. The downgrade 006 → 005 removes both tables and the index and leaves every other object as a new database at 005
   has it (11: once the column 006 drops is taken out of both texts); the populated database goes down keeping every
   other row — ``assets.classification_params`` with the same meaning, since A4 rebuilds it from the profile and every
   part of this install is one the copy keeps —, and up again, the two tables back, ``asset_enrichers`` empty and
   the profile holding the legacy copy again.
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
10. Step ``asset_profile_legacy_copy`` (project 68, lot A4), after ``asset_profile`` in ``upgrade()`` and before it in
    ``downgrade()``; self-contained, like every migration (no import from ``backend.app``: guard). For every asset with
    ``classification_params`` (read with ``parse_float=Decimal``: JSON numbers as ``populate_mock_data`` writes them,
    strings as the app writes them), each part becomes a row of ``asset_profile_updates``, ``source='legacy'``,
    ``user_id`` and ``source_date`` NULL: ``short_description`` (non-empty text) → ``description``,
    ``geographic_area.distribution`` → ``geography``, ``sector_area.distribution`` → ``sector``. ``read_on`` is the
    asset's first day (A4b, PROF's decision of round 43): the earliest of the day of its ``created_at``, its first
    ``price_history`` day and its first ``transactions`` day — imported prices and back-dated transactions often go back
    years before ``created_at``; with neither, the day of ``created_at``. 1.3 held these values as true on every day, so
    the profile does too; never the day of the upgrade. One ``created_at`` for the run. Skipped, that asset or that voice only: a column NULL, ``''``, ``'{}'``, not JSON, not
    an object; a description that is not a non-empty text; a distribution absent, not an object, empty, with a negative
    weight, a weight that is not a number, or a sum farther than 0.01 from 1. Each copied value reads back as the store
    reads it — ``normalize_value(key, json.loads(row.value))`` — equal to ``normalize_value(key, the part)``. Run
    again, it adds no row: an asset and voice with a ``legacy`` row already is skipped. Every other row stays, no
    violation. Downgrade: ``classification_params`` rebuilt from each asset's last row in (``read_on``, ``id``) order of
    each of the three voices (a map as ``{"distribution": …}`` with string weights; a NULL last row removes the part).
    Since D7b (11) the column comes back empty first: a part the copy skipped is gone, and an asset with no profile row
    gets a NULL column.

11. Step ``drop_classification_params`` (project 68, lot D7b): ``assets.classification_params`` is dropped after the
    legacy copy in ``upgrade()``, added back before the copy's downgrade in ``downgrade()``. A new database at 006 and an
    upgraded 1.3 install have no such column, the model neither; the 1.3 rows are compared on the columns 006 keeps
    (``alembic_harness._kept_columns``). Back at 005 the column is there again, TEXT and nullable, **last** in
    ``assets`` (``ALTER TABLE ADD COLUMN``): the schema is compared with a new 005 once its definition is taken out of
    both texts (``_without_dropped_columns``). A part the copy skipped is lost with the column: the rebuilt column holds
    only the copied parts, and an asset without profile rows gets it back NULL.

Safety and fidelity: ``alembic_harness``. Every database is a file under ``tmp_path``; Alembic runs in this process on
that file alone — a connect listener refuses any other — with ``PRAGMA foreign_keys`` asserted 1 at every step, as
production migrates. Rows are written with plain SQL. The models are reached through ``SQLModel.metadata``, never by
importing a class the lot has not written yet. ``get_async_engine`` and ``get_sync_engine`` are tripwires: no lane
database.

Red until the cure: ``006_release_1_4_0_schema`` exists with no step, so every migration below goes through and the
tests fail on assertions — the tables, the index, the step functions, the models are missing; each test that needs the
tables passes a barrier first, so none of them passes on an empty database. Guards, green before and after: the chain
(1), the rows a 1.3 database keeps (4), the redundant-index check at 005 (9).

Red until A4 (10): the step ``asset_profile_legacy_copy`` does not exist, so every upgrade leaves the profile empty and
the tests fail on assertions — the step functions, the missing ``legacy`` rows. Each test about what the copy skips,
what a second run adds or what the downgrade rebuilds passes a barrier first (the copy ran on that database: the fully
classified asset has its three ``legacy`` rows), so none of them passes on an empty table. Guards, green before and
after: no import from ``backend.app`` in the revision, the A2 round trip down to 005 (the column's meaning kept).
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.app.services.assets.profile.catalogue import normalize_value
from backend.test_scripts.test_db.alembic_harness import (
    DROPPED_AT_006,
    Rows,
    _assert_dropped_columns_back,
    _connect,
    _copy,
    _create_all,
    _foreign_keys,
    _foreign_keys_on,
    _full_shape,
    _index_list,
    _integrity,
    _kept_columns,
    _migrate,
    _on_columns,
    _revision,
    _row_changes,
    _rows,
    _scripts,
    _table_info,
    _tables,
    _violations,
    _without_dropped_columns,
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


def _profile_rows(db: Path) -> list[dict[str, Any]]:
    """Every row of ``asset_profile_updates``, by id, as dicts of its columns; none when the table is not there."""
    if UPDATES not in _tables(db):
        return []
    with _connect(db) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(f"SELECT * FROM {UPDATES} ORDER BY id")]


#: The parts of ``classification_params`` and the profile voice each becomes (plan 68, A4).
VOICE_OF_PART = {"short_description": "description", "geographic_area": "geography", "sector_area": "sector"}


def _part_meaning(part: str, value: Any) -> tuple[str, Any]:
    """What one part of ``classification_params`` means: the catalogue's stored form when the catalogue takes it, else
    the part as written (a part the copy skipped stays as it was)."""
    voice = VOICE_OF_PART.get(part)
    try:
        if voice == "description" and isinstance(value, str):
            return ("stored form", normalize_value(voice, value))
        if voice in ("geography", "sector") and isinstance(value, dict) and "distribution" in value:
            return ("stored form", normalize_value(voice, value["distribution"]))
    except (ValueError, TypeError):
        # Parsing probe: a part the catalogue refuses is compared as written
        pass
    return ("as written", value)


def _meaning(text: Optional[str]) -> Any:
    """What a ``classification_params`` text means, whatever its spelling: each part through ``_part_meaning``, the
    JSON read with ``parse_float=Decimal`` (so ``1.0`` and ``"1.0"`` stay told apart only where the catalogue does)."""
    if text is None:
        return None
    try:
        data = json.loads(text, parse_float=Decimal)
    except ValueError:
        return ("not JSON", text)
    if not isinstance(data, dict):
        return ("not an object", data)
    return {part: _part_meaning(part, value) for part, value in data.items()}


def _classification_by_asset(rows: Rows) -> dict[int, Optional[str]]:
    columns, content = rows["assets"]
    return {row[columns.index("id")]: row[columns.index("classification_params")] for row in content}


def _assert_assets_kept_but_classification(before: Rows, after: Rows) -> None:
    """Every row of ``assets`` identical on every column but ``classification_params``, which A4's downgrade rebuilds."""
    columns = [column for column in before["assets"][0] if column != "classification_params"]
    lost, gained = (sorted(set(_on_columns(before, "assets", columns)) - set(_on_columns(after, "assets", columns)), key=repr), sorted(set(_on_columns(after, "assets", columns)) - set(_on_columns(before, "assets", columns)), key=repr))
    assert not lost and not gained, f"assets changed outside classification_params: missing {lost[:2]}, unexpected {gained[:2]}"


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
    """Every table the 1.3 install had is there, every row identical on the columns it had but those 006 drops (another
    step of 006 may add a column: its values are that step's to pin; ``drop_classification_params`` drops
    ``assets.classification_params``, D7b)."""
    print_section("A populated 1.3 database upgraded to 006")
    before, after = upgraded_1_3.rows_before, upgraded_1_3.rows_after
    lost = sorted(set(before) - set(after))
    assert lost == [], f"the upgrade lost the tables {lost}"
    changes = _row_changes(before, after, set(before) - BOOKKEEPING, columns_of=_kept_columns(before))
    assert not changes, f"the upgrade changed rows: {changes}"
    assert _revision(upgraded_1_3.db) == REV_006
    print_success(f"{len(set(before) - BOOKKEEPING)} tables, every row kept")


def test_a_populated_1_3_database_gets_its_classification_copied_the_enrichers_empty_and_no_violation(upgraded_1_3: Upgrade) -> None:
    """The two tables are there; ``asset_enrichers`` empty; ``asset_profile_updates`` holds the legacy copy of the
    install's classification and nothing else — the geography of asset 1, the sector of asset 2, nothing for asset 3
    (NULL column) —; ``foreign_key_check`` empty, integrity ``ok``.

    Changed by A4, by design: under A2 this test was ``…_gets_the_two_tables_empty_…`` and asserted an empty profile
    table; the step ``asset_profile_legacy_copy`` now fills it from ``classification_params``."""
    after = upgraded_1_3.rows_after
    missing = [table for table in NEW_TABLES if table not in after]
    assert not missing, f"red until A2: the upgraded 1.3 install has no {missing}"
    assert after[ENRICHERS][1] == [], f"the upgrade must leave {ENRICHERS} empty: {after[ENRICHERS][1]}"
    copied = sorted((row["asset_id"], row["key"], row["source"]) for row in _profile_rows(upgraded_1_3.db))
    assert copied == [(1, "geography", "legacy"), (2, "sector", "legacy")], f"red until A4: the profile must hold the legacy copy of the two classified assets and nothing else: {copied}"
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
    ``sqlite_master`` is what a new database at 005 holds, SQL text included (whitespace collapsed) once the definition
    of each column 006 drops is taken out of both sides — the downgrade adds it back last (D7b) —; the column back, TEXT
    and nullable; the rows too."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_profile_tables(db)

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005
    left = _of_the_step(_objects(db))
    assert left == [], f"the downgrade must remove both tables and their index: {left}"
    _assert_dropped_columns_back(db)
    expected, found = _without_dropped_columns(_not_of_the_step(_objects(at_005))), _without_dropped_columns(_not_of_the_step(_objects(db)))
    assert found == expected, f"every other object must be as at 005: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"
    changes = _row_changes(_rows(at_005), _rows(db), set(_rows(at_005)) - BOOKKEEPING, columns_of=_rows(at_005))
    assert not changes, f"the downgrade of a new database changed rows: {changes}"


def test_the_downgrade_of_a_populated_database_keeps_every_other_row(round_trip: RoundTrip | str) -> None:
    """The populated install at 006, given a profile row and an enricher row, goes down to 005: the two tables gone,
    every other row as it was at 005, no violation, integrity ``ok``.

    Changed by A4, by design: the downgrade of ``asset_profile_legacy_copy`` rebuilds ``assets.classification_params``
    from the profile, and the contract does not promise the column's text back (``"0.6"`` comes back as the stored
    form's ``"0.6000"``, the keys in another order). So ``assets`` is compared on every other column exactly, and on
    ``classification_params`` by meaning (``_meaning``); every other table exactly, as under A2."""
    trip = _ran(round_trip)
    assert trip.revision_down == REV_005
    assert not set(NEW_TABLES) & trip.tables_down, f"the downgrade must remove both tables: {sorted(set(NEW_TABLES) & trip.tables_down)}"
    changes = _row_changes(trip.rows_at_005, trip.rows_down, set(trip.rows_at_005) - BOOKKEEPING - {"assets"}, columns_of=trip.rows_at_005)
    assert not changes, f"the downgrade changed other rows: {changes}"
    _assert_assets_kept_but_classification(trip.rows_at_005, trip.rows_down)
    meanings = {asset_id: (_meaning(text), _meaning(_classification_by_asset(trip.rows_down)[asset_id])) for asset_id, text in _classification_by_asset(trip.rows_at_005).items()}
    differ = {asset_id: pair for asset_id, pair in meanings.items() if pair[0] != pair[1]}
    assert not differ, f"the downgrade must give classification_params back with the same meaning: (at 005, after) {differ}"
    assert trip.violations_down == [] and trip.integrity_down == [("ok",)], f"violations {trip.violations_down}, integrity {trip.integrity_down}"


def test_upgrading_the_downgraded_database_again_brings_the_tables_back_with_the_legacy_copy(round_trip: RoundTrip | str) -> None:
    """Up again to 006: the two tables back, ``asset_enrichers`` empty, the profile holding the legacy copy again — the
    geography of asset 1, the sector of asset 2; the ``ter`` row written before the downgrade went with its table —,
    every other row as at 005 (``classification_params`` by meaning), no violation.

    Changed by A4, by design: under A2 this test was ``…_brings_the_tables_back_empty`` and asserted both tables empty;
    the upgrade now copies ``classification_params`` again."""
    trip = _ran(round_trip)
    assert trip.revision_again == REV_006
    missing = [table for table in NEW_TABLES if table not in trip.rows_again]
    assert not missing, f"the upgrade again must create {missing}"
    assert trip.rows_again[ENRICHERS][1] == [], f"{ENRICHERS} comes back empty: {trip.rows_again[ENRICHERS][1]}"
    columns, content = trip.rows_again[UPDATES]
    copied = sorted((row[columns.index("asset_id")], row[columns.index("key")], row[columns.index("source")]) for row in content)
    assert copied == [(1, "geography", "legacy"), (2, "sector", "legacy")], f"red until A4: up again, the profile holds the legacy copy and nothing else: {copied}"
    changes = _row_changes(trip.rows_at_005, trip.rows_again, set(trip.rows_at_005) - BOOKKEEPING - {"assets"}, columns_of=trip.rows_at_005)
    assert not changes, f"up again changed other rows: {changes}"
    _assert_assets_kept_but_classification(trip.rows_at_005, trip.rows_again)
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
    _assert_dropped_columns_back(db)
    expected, found = _without_dropped_columns(_not_of_the_step(_objects(at_005))), _without_dropped_columns(_not_of_the_step(_objects(db)))
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


# =============================================================================
# 10. A4: THE LEGACY COPY OF classification_params
# =============================================================================

LEGACY_STEP = "asset_profile_legacy_copy"
UPGRADE_LEGACY, DOWNGRADE_LEGACY = f"_upgrade_{LEGACY_STEP}", f"_downgrade_{LEGACY_STEP}"
LEGACY = "legacy"
#: Where each voice sits in ``classification_params``.
PATH_OF_VOICE = {"description": ("short_description",), "geography": ("geographic_area", "distribution"), "sector": ("sector_area", "distribution")}
#: Two zones 26 hours apart: their dates always differ, and at any hour at least one differs from UTC's.
INSERT_TRANSACTION = "INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency, created_at, updated_at) VALUES (1, ?, 'BUY', ?, 1, -100, 'EUR', ?, ?)"
INSERT_CLASSIFIED = "INSERT INTO assets (id, display_name, currency, classification_params, asset_type, active, created_at, updated_at) VALUES (?, ?, 'EUR', ?, 'ETF', 1, ?, ?)"


@dataclass(frozen=True)
class LegacyCase:
    """One asset of the classified 1.3 install: its ``classification_params`` as written, and the voices the copy keeps."""

    name: str
    text: Optional[str]
    copied: tuple[str, ...]


#: The classified 1.3 install, one asset per case, ids in this order from 1. Texts as the two writers of 1.3 wrote them:
#: the app (``FAClassificationParams.model_dump_json(exclude_none=True)``: string weights, four decimals) and
#: ``populate_mock_data.py`` (``json.dumps`` of floats, non-standard sector names); then every shape the copy skips.
LEGACY_CASES: tuple[LegacyCase, ...] = (
    LegacyCase(
        "full-as-the-app-writes-it",
        '{"short_description":"Global developed-markets equity ETF","geographic_area":{"distribution":{"USA":"0.6000","JPN":"0.2500","DEU":"0.1500"}},' '"sector_area":{"distribution":{"Technology":"0.5000","Financials":"0.3000","Health Care":"0.2000"}}}',
        ("description", "geography", "sector"),
    ),
    LegacyCase(
        "floats-and-services-as-mock-data-writes-them",
        json.dumps({"short_description": "Technology company", "geographic_area": {"distribution": {"USA": 1.0}}, "sector_area": {"distribution": {"Technology": 0.85, "Services": 0.15}}}),
        ("description", "geography", "sector"),
    ),
    LegacyCase(
        "floats-three-countries-and-cloud",
        json.dumps({"short_description": "Software and cloud computing", "geographic_area": {"distribution": {"USA": 0.50, "CHN": 0.25, "DEU": 0.25}}, "sector_area": {"distribution": {"Technology": 0.70, "Cloud": 0.30}}}),
        ("description", "geography", "sector"),
    ),
    LegacyCase("description-only", json.dumps({"short_description": "Digital gold, store of value", "sector_area": None}), ("description",)),
    LegacyCase("null-column", None, ()),
    LegacyCase("empty-string", "", ()),
    LegacyCase("empty-object", "{}", ()),
    LegacyCase("broken-json", '{"short_description": "Broken', ()),
    LegacyCase("json-array", '["Technology"]', ()),
    LegacyCase("json-string", '"just a text"', ()),
    LegacyCase("bad-sum-geography-good-sector", '{"geographic_area":{"distribution":{"USA":"0.5","JPN":"0.3"}},"sector_area":{"distribution":{"Energy":"1"}}}', ("sector",)),
    LegacyCase("geography-not-an-object", '{"short_description":"Euro government bond ladder","geographic_area":{"distribution":["ITA","DEU"]}}', ("description",)),
    LegacyCase("empty-geography-good-sector", '{"geographic_area":{"distribution":{}},"sector_area":{"distribution":{"Utilities":"1.0"}}}', ("sector",)),
    LegacyCase("negative-weight", '{"short_description":"Hedged world equity","geographic_area":{"distribution":{"USA":"1.2","JPN":"-0.2"}}}', ("description",)),
    LegacyCase("weight-not-a-number", '{"geographic_area":{"distribution":{"ITA":1}},"sector_area":{"distribution":{"Technology":"lots"}}}', ("geography",)),
    LegacyCase("weight-a-boolean", '{"short_description":"Energy tracker","sector_area":{"distribution":{"Energy":true}}}', ("description",)),
    LegacyCase("empty-description-good-sector", '{"short_description":"","sector_area":{"distribution":{"Energy":"1"}}}', ("sector",)),
    LegacyCase("description-not-a-text", '{"short_description":42,"sector_area":{"distribution":{"Energy":"1"}}}', ("sector",)),
    LegacyCase("sum-within-a-hundredth", '{"geographic_area":{"distribution":{"USA":"0.605","JPN":"0.4"}}}', ("geography",)),
    LegacyCase("distribution-missing", '{"short_description":"Odd shape","geographic_area":{"weights":{"USA":"1"}}}', ("description",)),
)
CASE_ID = {case.name: index for index, case in enumerate(LEGACY_CASES, start=1)}
FULL = CASE_ID["full-as-the-app-writes-it"]
MOCK_FLOATS = CASE_ID["floats-and-services-as-mock-data-writes-them"]
DESCRIPTION_ONLY = CASE_ID["description-only"]
COPIED_PAIRS = [pytest.param(case.name, key, id=f"{case.name}:{key}") for case in LEGACY_CASES for key in case.copied]


def _part(text: str, key: str) -> Any:
    """The part of ``classification_params`` that becomes voice ``key``, read with ``parse_float=Decimal`` as the copy reads it."""
    value = json.loads(text, parse_float=Decimal)
    for step in PATH_OF_VOICE[key]:
        value = value[step]
    return value


def _read_back(key: str, text: Optional[str]) -> Any:
    """A row's value as the store reads it (``store._same_value_text``): plain ``json.loads``, then the catalogue's stored
    form. A value the store could not read back in its stored form fails here."""
    if text is None:
        return None
    try:
        return normalize_value(key, json.loads(text))
    except (ValueError, TypeError) as exc:
        pytest.fail(f"the store cannot read the {key} row {text!r} back in its stored form: {exc!r}", pytrace=False)


def _populate_classified(db: Path) -> None:
    """``LEGACY_CASES`` and the rest of a 1.3 install (a user and its settings, a broker, prices), as plain SQL."""
    with _foreign_keys_on(db) as conn:
        conn.execute(INSERT_USER, ("legacy_owner", "legacy_owner@example.test", STAMP, STAMP))
        conn.execute("INSERT INTO user_settings (user_id, base_currency, language, ui_preferences, created_at, updated_at) VALUES (1, 'EUR', 'en', '{}', ?, ?)", (STAMP, STAMP))
        conn.execute("INSERT INTO brokers (id, name, created_at, updated_at) VALUES (1, 'Legacy Broker', ?, ?)", (STAMP, STAMP))
        conn.executemany(INSERT_CLASSIFIED, [(asset_id, f"Legacy {case.name}", case.text, STAMP, STAMP) for asset_id, case in enumerate(LEGACY_CASES, start=1)])
        conn.executemany(
            "INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) VALUES (?, ?, ?, 'EUR', 'manual', ?)",
            [(FULL, "2026-11-02", 101.5, STAMP), (FULL, "2026-11-03", 102.25, STAMP), (CASE_ID["null-column"], "2026-11-03", 99.875, STAMP)],
        )
        conn.commit()


def _legacy_rows_of(rows: list[dict[str, Any]], asset_id: int) -> dict[str, list[dict[str, Any]]]:
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row["asset_id"] == asset_id:
            by_key.setdefault(row["key"], []).append(row)
    return by_key


def _copy_ran(rows: list[dict[str, Any]], where: str) -> Optional[str]:
    """Barrier: why the copy did not run on that database (the fully classified asset lacks its three ``legacy`` rows), or None."""
    found = sorted(key for key, of_key in _legacy_rows_of(rows, FULL).items() if any(row["source"] == LEGACY for row in of_key))
    if found != ["description", "geography", "sector"]:
        return f"red until A4: {where}: the fully classified asset has legacy rows for {found}, not its three voices: the step {LEGACY_STEP} has not copied it"
    return None


def _assert_copy_ran(rows: list[dict[str, Any]], where: str) -> None:
    reason = _copy_ran(rows, where)
    assert reason is None, reason


#: The first day of each asset of the classified install (``_populate_classified``): the fully classified one has
#: prices from 2 November, before its ``created_at`` (``STAMP``, 10 November); the others have no price and no
#: transaction, so their day is the day of their ``created_at``.
CREATED_DAY = date(2026, 11, 10)
FIRST_DAY = {FULL: date(2026, 11, 2)}


@dataclass(frozen=True)
class ClassifiedUpgrade:
    """A copy of the classified 1.3 install, before and right after ``upgrade 006``, and the UTC day around the run."""

    db: Path
    rows_before: Rows
    rows_after: Rows
    profile: list[dict[str, Any]]
    days: set[date]
    violations: list[tuple[Any, ...]]
    integrity: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def classified_1_3(at_005: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The classified 1.3 install at 005 (``LEGACY_CASES``), no ``scheduler_timezone`` row. Read-only: ``_copy`` it to write."""
    db = _copy(at_005, tmp_path_factory.mktemp("classified-1.3") / "app.db")
    _populate_classified(db)
    with _connect(db) as conn:
        assets = conn.execute("SELECT count(*) FROM assets").fetchone()[0]
        zones = conn.execute("SELECT count(*) FROM global_settings WHERE key = 'scheduler_timezone'").fetchone()[0]
    assert (assets, zones) == (len(LEGACY_CASES), 0), f"setup: {len(LEGACY_CASES)} assets and no scheduler_timezone row: {(assets, zones)}"
    assert _revision(db) == REV_005 and _violations(db) == [], "setup: a consistent 1.3 install at 005"
    return db


@pytest.fixture(scope="module")
def classified_upgrade(classified_1_3: Path, tmp_path_factory: pytest.TempPathFactory) -> ClassifiedUpgrade:
    db = _copy(classified_1_3, tmp_path_factory.mktemp("classified-upgrade") / "app.db")
    rows_before = _rows(db)
    first = datetime.now(UTC).date()
    _migrate(db, "upgrade", REV_006)
    last = datetime.now(UTC).date()
    return ClassifiedUpgrade(db=db, rows_before=rows_before, rows_after=_rows(db), profile=_profile_rows(db), days={first, last}, violations=_violations(db), integrity=_integrity(db))


@dataclass(frozen=True)
class ClassifiedDowngrade:
    """The classified install at 006, given newer rows by hand, then down to 005."""

    rows_at_005: Rows
    rows_down: Rows
    revision: str
    tables: set[str]
    violations: list[tuple[Any, ...]]
    integrity: list[tuple[Any, ...]]
    newest_sector: Any


@pytest.fixture(scope="module")
def classified_downgrade(classified_upgrade: ClassifiedUpgrade, tmp_path_factory: pytest.TempPathFactory) -> ClassifiedDowngrade | str:
    """The classified install upgraded, then: two newer ``user`` sector rows of the fully classified asset, inserted in
    the reverse order of their days (the later day gets the lower id: the (``read_on``, ``id``) order picks it, not the
    id), and a NULL ``user`` description of the mock-data asset; down to 005. Or, while the copy does not run, the reason."""
    db = _copy(classified_upgrade.db, tmp_path_factory.mktemp("classified-downgrade") / "app.db")
    profile = _profile_rows(db)
    reason = _copy_ran(profile, "the classified install upgraded")
    if reason is not None:
        return reason
    day = max(date.fromisoformat(str(row["read_on"])) for row in profile)
    newest = {"Energy": "1"}
    with _foreign_keys_on(db) as conn:
        conn.execute(INSERT_UPDATE, (FULL, "sector", json.dumps(normalize_value("sector", newest)), "user", 1, (day + timedelta(days=2)).isoformat(), None, STAMP))
        conn.execute(INSERT_UPDATE, (FULL, "sector", json.dumps(normalize_value("sector", {"Utilities": "1"})), "user", 1, (day + timedelta(days=1)).isoformat(), None, STAMP))
        conn.execute(INSERT_UPDATE, (MOCK_FLOATS, "description", None, "user", 1, (day + timedelta(days=1)).isoformat(), None, STAMP))
        conn.commit()
    _migrate(db, "downgrade", REV_005)
    return ClassifiedDowngrade(
        rows_at_005=classified_upgrade.rows_before,
        rows_down=_rows(db),
        revision=_revision(db),
        tables=_tables(db),
        violations=_violations(db),
        integrity=_integrity(db),
        newest_sector=newest,
    )


def _read_on_of_one_asset(at_005: Path, target: Path, created: str, prices: tuple[str, ...], transactions: tuple[str, ...]) -> list[date]:
    """A 1.3 install at 005 with one described asset created at ``created``, those price and transaction days, upgraded
    to 006: the ``read_on`` of its profile rows."""
    db = _copy(at_005, target)
    with _foreign_keys_on(db) as conn:
        conn.execute("INSERT INTO brokers (id, name, created_at, updated_at) VALUES (1, 'First Day Broker', ?, ?)", (STAMP, STAMP))
        conn.execute(INSERT_CLASSIFIED, (1, "First day ETF", '{"short_description":"First day probe"}', created, created))
        conn.executemany(
            "INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) VALUES (1, ?, 100, 'EUR', 'manual', ?)",
            [(day, STAMP) for day in prices],
        )
        conn.executemany(INSERT_TRANSACTION, [(1, day, STAMP, STAMP) for day in transactions])
        conn.commit()
    _migrate(db, "upgrade", REV_006)
    return [date.fromisoformat(str(row["read_on"])) for row in _profile_rows(db)]


# --- the step ----------------------------------------------------------------------------------------------------------


def test_006_holds_the_legacy_copy_step_after_the_profile_step() -> None:
    """``_upgrade_asset_profile_legacy_copy`` and ``_downgrade_asset_profile_legacy_copy`` exist; ``upgrade()`` calls the
    copy after ``_upgrade_asset_profile`` (it writes into its table), ``downgrade()`` calls it before
    ``_downgrade_asset_profile`` (it reads the table that one drops)."""
    print_section(f"{REV_006}: step {LEGACY_STEP}")
    module = _scripts().get_revision(REV_006).module
    missing = [name for name in (UPGRADE_LEGACY, DOWNGRADE_LEGACY) if not callable(getattr(module, name, None))]
    assert not missing, f"red until A4: {REV_006} defines no {missing}"
    upgrade, downgrade = inspect.getsource(module.upgrade), inspect.getsource(module.downgrade)
    assert f"{UPGRADE_STEP}(" in upgrade and f"{UPGRADE_LEGACY}(" in upgrade, f"upgrade() must call {UPGRADE_STEP} and {UPGRADE_LEGACY}"
    assert upgrade.index(f"{UPGRADE_STEP}(") < upgrade.index(f"{UPGRADE_LEGACY}("), f"upgrade() must call {UPGRADE_LEGACY} after {UPGRADE_STEP}"
    assert f"{DOWNGRADE_STEP}(" in downgrade and f"{DOWNGRADE_LEGACY}(" in downgrade, f"downgrade() must call {DOWNGRADE_LEGACY} and {DOWNGRADE_STEP}"
    assert downgrade.index(f"{DOWNGRADE_LEGACY}(") < downgrade.index(f"{DOWNGRADE_STEP}("), f"downgrade() must call {DOWNGRADE_LEGACY} before {DOWNGRADE_STEP}"
    print_success(f"{LEGACY_STEP}: after {STEP} up, before it down")


def test_006_imports_nothing_from_the_application() -> None:
    """GUARD, green before and after: the revision is self-contained, like every migration — no ``backend.app`` import,
    so it runs the same on a release whose code has moved on."""
    source = inspect.getsource(_scripts().get_revision(REV_006).module)
    imports = [line.strip() for line in source.splitlines() if re.match(r"\s*(from|import)\s+backend\b", line)]
    assert imports == [], f"{REV_006} must not import application code: {imports}"


# --- what the upgrade copies -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("case_name", [case.name for case in LEGACY_CASES])
def test_the_upgrade_copies_the_valid_voices_of_each_asset_once(classified_upgrade: ClassifiedUpgrade, case_name: str) -> None:
    """Each asset of the classified install gets one ``legacy`` row per voice its ``classification_params`` holds in a
    shape today's rules accept, and none for the others: a NULL, empty, ``'{}'``, broken, non-object column gives no row;
    a voice whose part fails the rule is skipped, the others of that asset kept. Barrier: the copy ran."""
    _assert_copy_ran(classified_upgrade.profile, "the classified install upgraded")
    case = LEGACY_CASES[CASE_ID[case_name] - 1]
    by_key = _legacy_rows_of(classified_upgrade.profile, CASE_ID[case_name])
    found = {key: len(rows) for key, rows in sorted(by_key.items())}
    assert found == dict.fromkeys(sorted(case.copied), 1), f"{case_name}: rows by voice {found}, expected one each for {sorted(case.copied)}"


@pytest.mark.parametrize(("case_name", "key"), COPIED_PAIRS)
def test_each_copied_value_reads_back_in_the_catalogue_stored_form(classified_upgrade: ClassifiedUpgrade, case_name: str, key: str) -> None:
    """What the store reads back from a copied row — plain ``json.loads``, then ``normalize_value`` — is the stored form
    of the part it came from (read with ``parse_float=Decimal``): string weights and float weights alike, non-standard
    sectors as the catalogue maps them."""
    _assert_copy_ran(classified_upgrade.profile, "the classified install upgraded")
    case = LEGACY_CASES[CASE_ID[case_name] - 1]
    rows = _legacy_rows_of(classified_upgrade.profile, CASE_ID[case_name]).get(key, [])
    assert len(rows) == 1, f"{case_name}: one {key} row expected, found {rows}"
    expected = normalize_value(key, _part(case.text, key))
    found = _read_back(key, rows[0]["value"])
    assert found == expected, f"{case_name}: the {key} row {rows[0]['value']!r} reads back as {found}, the part's stored form is {expected}"


def test_the_mock_data_floats_and_services_read_back_as_known_maps(classified_upgrade: ClassifiedUpgrade) -> None:
    """An anchor written out: ``{"USA": 1.0}`` reads back ``{"USA": "1.0000"}``, ``{"Technology": 0.85, "Services":
    0.15}`` reads back ``{"Other": "0.1500", "Technology": "0.8500"}`` (an unknown sector is «Other»)."""
    _assert_copy_ran(classified_upgrade.profile, "the classified install upgraded")
    by_key = _legacy_rows_of(classified_upgrade.profile, MOCK_FLOATS)
    found = {key: _read_back(key, by_key[key][0]["value"]) for key in ("geography", "sector") if key in by_key}
    assert found == {"geography": {"USA": "1.0000"}, "sector": {"Other": "0.1500", "Technology": "0.8500"}}, f"the mock-data maps read back as {found}"


def test_every_legacy_row_has_no_author_no_source_date_the_assets_first_day_and_one_created_at(classified_upgrade: ClassifiedUpgrade) -> None:
    """Every row of the copy: ``source='legacy'``, ``user_id`` and ``source_date`` NULL, ``read_on`` its asset's first day
    (A4b: the fully classified asset's first price, before its ``created_at``; the others' ``created_at`` day, having
    neither price nor transaction), and one ``created_at`` for the whole run."""
    rows = classified_upgrade.profile
    _assert_copy_ran(rows, "the classified install upgraded")
    expected = sum(len(case.copied) for case in LEGACY_CASES)
    assert len(rows) == expected, f"the copy writes {expected} rows, found {len(rows)}"
    wrong = [row for row in rows if (row["source"], row["user_id"], row["source_date"]) != (LEGACY, None, None)]
    assert wrong == [], f"a legacy row has no author and no source date: {wrong[:3]}"
    wrong_days = [(row["asset_id"], row["key"], row["read_on"]) for row in rows if date.fromisoformat(str(row["read_on"])) != FIRST_DAY.get(row["asset_id"], CREATED_DAY)]
    assert wrong_days == [], f"read_on must be the asset's first day (first price {FIRST_DAY}, else the created_at day {CREATED_DAY}): {wrong_days}"
    stamps = {row["created_at"] for row in rows}
    assert len(stamps) == 1, f"one created_at for the run, found {sorted(stamps)}"


def test_the_classified_upgrade_keeps_every_other_row_and_no_violation(classified_upgrade: ClassifiedUpgrade) -> None:
    """Every table but the profile keeps every row it had, on every column but ``classification_params``, which the step
    ``drop_classification_params`` drops after the copy (D7b); ``asset_enrichers`` empty; ``foreign_key_check`` empty,
    integrity ``ok``. Barrier: the copy ran."""
    _assert_copy_ran(classified_upgrade.profile, "the classified install upgraded")
    before, after = classified_upgrade.rows_before, classified_upgrade.rows_after
    changes = _row_changes(before, after, set(before) - BOOKKEEPING, columns_of=_kept_columns(before))
    assert not changes, f"the upgrade changed rows: {changes}"
    assert after[ENRICHERS][1] == [], f"{ENRICHERS} stays empty: {after[ENRICHERS][1]}"
    assert classified_upgrade.violations == [], f"foreign key violations: {classified_upgrade.violations}"
    assert classified_upgrade.integrity == [("ok",)], f"integrity_check: {classified_upgrade.integrity}"


# --- read_on: the asset's first day (A4b) ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("created", "prices", "transactions", "expected"),
    [
        pytest.param("2026-11-10 09:30:00.000000", ("2021-03-01", "2026-11-03"), (), date(2021, 3, 1), id="prices-before-creation"),
        pytest.param("2026-11-10 09:30:00.000000", ("2021-03-01",), ("2019-06-14",), date(2019, 6, 14), id="a-transaction-before-everything"),
        pytest.param("2026-11-10 09:30:00.000000", (), (), date(2026, 11, 10), id="no-price-no-transaction"),
        pytest.param("2018-01-05 23:59:59.000000", ("2021-03-01",), ("2022-02-02",), date(2018, 1, 5), id="created-first"),
    ],
)
def test_read_on_is_the_assets_first_day(at_005: Path, tmp_path: Path, created: str, prices: tuple[str, ...], transactions: tuple[str, ...], expected: date) -> None:
    """``read_on`` is the earliest of the day of ``created_at``, the first price and the first transaction; with neither
    price nor transaction, the day of ``created_at``. Never the day of the upgrade."""
    days = _read_on_of_one_asset(at_005, tmp_path / "app.db", created, prices, transactions)
    assert days == [expected], f"the described asset gets one legacy row on its first day {expected}: {days}"


# --- run again ---------------------------------------------------------------------------------------------------------


def test_the_upgrade_run_again_after_the_copy_adds_no_row(classified_upgrade: ClassifiedUpgrade, tmp_path: Path) -> None:
    """The classified install upgraded, ``alembic_version`` set back to 005 by hand — an upgrade that copied and stopped
    before Alembic recorded it —: ``upgrade`` again leaves the profile rows exactly as they were. Barrier: the copy ran."""
    db = _copy(classified_upgrade.db, tmp_path / "app.db")
    before = _profile_rows(db)
    _assert_copy_ran(before, "the classified install upgraded")
    with _foreign_keys_on(db) as conn:
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_005,))
        conn.commit()

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006
    after = _profile_rows(db)
    assert after == before, f"the copy run again must add no row: {len(before)} rows before, {len(after)} after; new {[row for row in after if row not in before][:3]}"


def test_an_upgrade_stopped_during_the_copy_skips_the_voices_already_copied(classified_1_3: Path, fresh_006: Path, tmp_path: Path) -> None:
    """A classified install at 005 holding the step's tables (``asset_profile`` ran) and one ``legacy`` row already —
    the fully classified asset's description, with another text —: ``upgrade 006`` keeps that row as the only
    description of the asset, copies its geography and sector, and copies every other asset. Barrier: the copy ran."""
    _assert_profile_tables(fresh_006)
    db = _copy(classified_1_3, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        for name in (UPDATES, PROFILE_INDEX, ENRICHERS):
            conn.execute(_sql_of(fresh_006, name))
        kept = conn.execute(INSERT_UPDATE, (FULL, "description", '"An older description of the fund"', LEGACY, None, "2026-11-01", None, STAMP)).lastrowid
        conn.commit()
    assert _revision(db) == REV_005, "setup: the run stopped before Alembic recorded the revision"

    _migrate(db, "upgrade", REV_006)

    rows = _profile_rows(db)
    full = _legacy_rows_of(rows, FULL)
    assert sorted(full) == ["description", "geography", "sector"] and len(full["geography"]) == len(full["sector"]) == 1, f"red until A4: the stopped copy must complete the fully classified asset: {full}"
    assert [(row["id"], row["value"]) for row in full["description"]] == [(kept, '"An older description of the fund"')], f"the description already copied must be the only one: {full['description']}"
    described = _legacy_rows_of(rows, DESCRIPTION_ONLY)
    assert {key: len(of_key) for key, of_key in described.items()} == {"description": 1}, f"every other asset is copied: {described}"


# --- the downgrade -----------------------------------------------------------------------------------------------------


def test_the_downgrade_of_the_copy_reaches_005_keeping_every_other_row(classified_downgrade: ClassifiedDowngrade | str) -> None:
    """Down to 005: both tables gone, every other table's rows as at 005, ``assets`` identical but for
    ``classification_params``; no violation, integrity ``ok``."""
    trip = _ran(classified_downgrade)
    assert trip.revision == REV_005
    assert not set(NEW_TABLES) & trip.tables, f"the downgrade must remove both tables: {sorted(set(NEW_TABLES) & trip.tables)}"
    changes = _row_changes(trip.rows_at_005, trip.rows_down, set(trip.rows_at_005) - BOOKKEEPING - {"assets"}, columns_of=trip.rows_at_005)
    assert not changes, f"the downgrade changed other rows: {changes}"
    _assert_assets_kept_but_classification(trip.rows_at_005, trip.rows_down)
    assert trip.violations == [] and trip.integrity == [("ok",)], f"violations {trip.violations}, integrity {trip.integrity}"


def test_the_downgrade_rebuilds_a_voice_from_its_last_row_in_read_on_order(classified_downgrade: ClassifiedDowngrade | str) -> None:
    """The fully classified asset, two newer ``user`` sector rows (the later day inserted first): the column's sector is
    the later day's, as ``{"distribution": …}`` with string weights; its description and geography stay those of the
    copy (the same meaning as at 005)."""
    trip = _ran(classified_downgrade)
    original = _classification_by_asset(trip.rows_at_005)[FULL]
    rebuilt = _classification_by_asset(trip.rows_down)[FULL]
    assert rebuilt is not None, "the fully classified asset must keep a classification"
    data = json.loads(rebuilt)
    assert set(data) == {"short_description", "geographic_area", "sector_area"}, f"the three parts are rebuilt: {sorted(data)}"
    assert data["sector_area"] == {"distribution": data["sector_area"].get("distribution")}, f"a map part is {{'distribution': …}}: {data['sector_area']}"
    weights = data["sector_area"]["distribution"]
    assert all(isinstance(weight, str) for weight in weights.values()), f"weights are written as strings: {weights}"
    assert normalize_value("sector", weights) == normalize_value("sector", trip.newest_sector), f"the sector is the last row in (read_on, id) order, {trip.newest_sector}: {weights}"
    expected = {part: meaning for part, meaning in _meaning(original).items() if part != "sector_area"}
    assert {part: meaning for part, meaning in _meaning(rebuilt).items() if part != "sector_area"} == expected, f"description and geography keep their meaning: {rebuilt} against {original}"


def test_the_downgrade_removes_a_part_whose_last_row_is_null(classified_downgrade: ClassifiedDowngrade | str) -> None:
    """The mock-data asset, its description emptied on purpose by a newer NULL row: ``short_description`` is gone from
    the column, geography and sector keep their meaning."""
    trip = _ran(classified_downgrade)
    original = _meaning(_classification_by_asset(trip.rows_at_005)[MOCK_FLOATS])
    rebuilt = _meaning(_classification_by_asset(trip.rows_down)[MOCK_FLOATS])
    expected = {part: meaning for part, meaning in original.items() if part != "short_description"}
    assert rebuilt == expected, f"the NULL description removes short_description, the rest keeps its meaning: {rebuilt}, expected {expected}"


@pytest.mark.parametrize("case_name", [case.name for case in LEGACY_CASES if case.copied and CASE_ID[case.name] not in (FULL, MOCK_FLOATS)])
def test_the_downgrade_gives_back_the_meaning_of_an_untouched_asset(classified_downgrade: ClassifiedDowngrade | str, case_name: str) -> None:
    """An asset with legacy rows and no later change: the rebuilt column means what the parts the copy kept meant at 005,
    in the catalogue's stored form. A part the copy skipped is gone: it made no row, and the column went with
    ``drop_classification_params`` (D7b). Every map part rebuilt from a row is ``{"distribution": …}`` with string weights."""
    trip = _ran(classified_downgrade)
    asset_id = CASE_ID[case_name]
    original, rebuilt = _classification_by_asset(trip.rows_at_005)[asset_id], _classification_by_asset(trip.rows_down)[asset_id]
    kept_parts = {PATH_OF_VOICE[key][0] for key in LEGACY_CASES[asset_id - 1].copied}
    expected = {part: meaning for part, meaning in _meaning(original).items() if part in kept_parts}
    assert _meaning(rebuilt) == expected, f"{case_name}: the rebuilt {rebuilt!r} must mean the copied parts of {original!r}: {expected}"
    data = json.loads(rebuilt)
    for key in ("geography", "sector"):
        if key in LEGACY_CASES[asset_id - 1].copied:
            part = data[PATH_OF_VOICE[key][0]]
            assert set(part) == {"distribution"} and all(isinstance(weight, str) for weight in part["distribution"].values()), f"{case_name}: {key} rebuilt as {part}"


@pytest.mark.parametrize("case_name", [case.name for case in LEGACY_CASES if not case.copied])
def test_the_downgrade_gives_an_asset_without_profile_rows_an_empty_column(classified_downgrade: ClassifiedDowngrade | str, case_name: str) -> None:
    """An asset the copy gave no row (NULL, ``''``, ``'{}'``, broken, non-object column): its column comes back NULL.
    What the copy could not read went with the column (D7b): the copy logged each skip on the way up."""
    trip = _ran(classified_downgrade)
    asset_id = CASE_ID[case_name]
    after = _classification_by_asset(trip.rows_down)[asset_id]
    assert after is None, f"{case_name}: the column comes back empty, found {after!r}"


# =============================================================================
# 11. D7b: THE OLD COLUMN GOES
# =============================================================================

DROP_STEP = "drop_classification_params"
UPGRADE_DROP, DOWNGRADE_DROP = f"_upgrade_{DROP_STEP}", f"_downgrade_{DROP_STEP}"
CLASSIFICATION_COLUMN = "classification_params"


def test_006_drops_the_column_after_the_copy_and_adds_it_back_before_the_copy_is_undone() -> None:
    """The step ``drop_classification_params`` exists; ``upgrade()`` calls it after the legacy copy (which reads the
    column), ``downgrade()`` before the copy's downgrade (which writes it). Mis-ordered, an upgrade would drop every
    classification before copying it, and the copy, finding no column, would copy nothing."""
    print_section(f"{REV_006}: step {DROP_STEP}")
    module = _scripts().get_revision(REV_006).module
    missing = [name for name in (UPGRADE_DROP, DOWNGRADE_DROP) if not callable(getattr(module, name, None))]
    assert not missing, f"red until D7b: {REV_006} defines no {missing}"
    upgrade, downgrade = inspect.getsource(module.upgrade), inspect.getsource(module.downgrade)
    assert upgrade.index(f"{UPGRADE_LEGACY}(") < upgrade.index(f"{UPGRADE_DROP}("), f"upgrade() must call {UPGRADE_DROP} after {UPGRADE_LEGACY}"
    assert downgrade.index(f"{DOWNGRADE_DROP}(") < downgrade.index(f"{DOWNGRADE_LEGACY}("), f"downgrade() must call {DOWNGRADE_DROP} before {DOWNGRADE_LEGACY}"
    assert (module._CLASSIFICATION_COLUMN, "TEXT") in DROPPED_AT_006.get(module._ASSETS, ()), f"alembic_harness.DROPPED_AT_006 must name what the step drops: {DROPPED_AT_006}"
    print_success(f"{DROP_STEP}: after the copy up, before its downgrade down")


def test_a_new_database_at_006_has_no_classification_column(fresh_006: Path, at_005: Path) -> None:
    """At 005 ``assets`` has the column (barrier); at 006 it has not, and every other column of 005 is there."""
    at_1_3, at_1_4 = _table_info(at_005, "assets"), _table_info(fresh_006, "assets")
    assert CLASSIFICATION_COLUMN in at_1_3, "barrier: a new database at 005 has assets.classification_params"
    assert CLASSIFICATION_COLUMN not in at_1_4, f"red until D7b: a new database at 006 still has assets.{CLASSIFICATION_COLUMN}"
    lost = sorted(set(at_1_3) - set(at_1_4) - {CLASSIFICATION_COLUMN})
    assert not lost, f"the step drops only its column: {lost}"


def test_the_models_and_the_migration_build_the_same_assets_table(fresh_006: Path, created_by_models: Path) -> None:
    """The model ``Asset`` has no ``classification_params`` either: ``create_all`` and the migration give ``assets`` the
    same columns. Only the columns: the names of the constraints and the declared types of ``assets`` differed between
    the two before 1.4, and are not this step's."""
    assert CLASSIFICATION_COLUMN not in _table_info(created_by_models, "assets"), "red until D7b: the model still declares the column"
    by_migration, by_models = set(_table_info(fresh_006, "assets")), set(_table_info(created_by_models, "assets"))
    assert by_migration == by_models, f"assets: columns only in the migration {sorted(by_migration - by_models)}, only in the models {sorted(by_models - by_migration)}"


def test_a_populated_1_3_database_loses_the_column_only_after_its_copy(upgraded_1_3: Upgrade) -> None:
    """The populated 1.3 install upgraded: the column is gone, and its classification is in the profile (the copy ran
    first): the geography of asset 1, the sector of asset 2."""
    assert CLASSIFICATION_COLUMN not in _table_info(upgraded_1_3.db, "assets"), f"red until D7b: the upgraded install still has assets.{CLASSIFICATION_COLUMN}"
    copied = sorted((row["asset_id"], row["key"]) for row in _profile_rows(upgraded_1_3.db))
    assert copied == [(1, "geography"), (2, "sector")], f"the copy ran before the drop: {copied}"
