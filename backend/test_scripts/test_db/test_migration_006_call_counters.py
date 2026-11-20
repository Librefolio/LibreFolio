"""Migration ``006_release_1_4_0_schema``, step ``plugin_call_counters`` (project 76, lot U1): the per-instance call
counter of every plugin that calls an external service (plan 76, §3.5).

The 1.4 cycle has one revision, and several workstreams each add a step of their own to it (its docstring says how).
This file pins ONLY what the step ``plugin_call_counters`` creates — the table ``plugin_call_counters`` — and never the
whole schema at 006: what another step adds is that step's to pin. So the table set is asserted as a superset, rows are
compared on the columns they had before the upgrade, and a full schema comparison appears only after a downgrade, at
005.

``plugin_call_counters``: one row per (``family``, ``plugin_code``) — the code may be a shared group's name, family
``group`` —, five calendar windows aligned in UTC, each a start (``<w>_since``, epoch seconds) and a count
(``<w>_count``). ``family`` VARCHAR(16) NOT NULL, ``plugin_code`` VARCHAR(64) NOT NULL, PRIMARY KEY (``family``,
``plugin_code``) in that order — no separate id, so no AUTOINCREMENT and the census of ``test_autoincrement_schema``
stays as it is —; ``minute_since``, ``minute_count``, ``hour_since``, ``hour_count``, ``day_since``, ``day_count``,
``week_since``, ``week_count``, ``month_since``, ``month_count`` INTEGER NOT NULL; ``updated_at`` DATETIME NOT NULL. No
foreign key, no CHECK, no index but the primary key's own.

The contract pinned here:

1. The revision holds the step as its docstring asks: ``_upgrade_plugin_call_counters`` and
   ``_downgrade_plugin_call_counters``, each called on its own line of ``upgrade()`` and ``downgrade()``, and a
   docstring section named ``plugin_call_counters``.
2. A new database taken to 006 — by name, not ``head`` — has the table with exactly those columns (name, declared type
   with its length, NOT NULL — also on the two key columns, which SQLite does not imply for a composite key —, primary
   key position), no foreign key, no CHECK, no AUTOINCREMENT, one index only: SQLite's own of the primary key, on
   (``family``, ``plugin_code``). At work: a second row of the same pair is refused, the same code under another family
   is stored.
3. A populated 1.3 database (at 005, plain SQL) upgraded to 006 keeps every row of every table it had, gets the table
   empty, no foreign-key violation, integrity ``ok``.
4. Models = migration: ``SQLModel.metadata`` declares the table, ``backend.app.db.models.PluginCallCounter`` maps it,
   and ``create_all`` builds it with the shape the migration gives it (``_full_shape`` and every column's default).
5. The downgrade 006 → 005 removes the table and leaves every object as a new database at 005 has it; the populated
   database goes down keeping every other row, and up again gets the table back, empty.
6. Every part checks before it acts: an upgrade run again over its own work changes no object and no row; an upgrade
   that finds the table already there (an upgrade stopped half way) completes, the row it found kept; a downgrade that
   finds the table already gone completes to 005.
7. The redundant-index check of ``db_schema_validate`` (``test_no_redundant_indexes``) passes on a database at 006.

Safety and fidelity: ``alembic_harness``. Every database is a file under ``tmp_path``; Alembic runs in this process on
that file alone, with ``PRAGMA foreign_keys`` asserted 1 at every step. Rows are written with plain SQL. The model is
reached through ``SQLModel.metadata`` and ``getattr`` on ``models``, never imported by name. ``get_async_engine`` and
``get_sync_engine`` are tripwires: no lane database.

Red on HEAD f2464fb32: ``006_release_1_4_0_schema`` has no step ``plugin_call_counters``, so every migration below goes
through and each test fails on an assertion — the step functions, the table, the model are missing. Every test whose
assertions would hold on an absent table (no FK, no CHECK, no extra index, nothing changed when run again, the
downgrade finding it gone, the redundant-index check) passes a barrier first: the table is there. No guard of this file
is green on HEAD; the chain and the 005 guards are ``test_migration_006_asset_profile``'s.
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

from backend.app.db import models as db_models
from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.test_scripts.test_db.alembic_harness import (
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
STEP = "plugin_call_counters"
UPGRADE_STEP, DOWNGRADE_STEP = f"_upgrade_{STEP}", f"_downgrade_{STEP}"
TABLE = "plugin_call_counters"
MODEL = "PluginCallCounter"
KEY = ("family", "plugin_code")
WINDOWS = ("minute", "hour", "day", "week", "month")
#: Alembic's own bookkeeping: its row changes with every step.
BOOKKEEPING = frozenset({"alembic_version"})


@dataclass(frozen=True)
class Column:
    """A column as the contract states it: declared type as ``PRAGMA table_info`` reports it (length included), NOT
    NULL, and its position in the primary key (0 = not a key column)."""

    declared: str
    not_null: bool
    key_position: int = 0


CONTRACT: dict[str, Column] = {
    "family": Column("VARCHAR(16)", True, 1),
    "plugin_code": Column("VARCHAR(64)", True, 2),
    **{f"{window}_{part}": Column("INTEGER", True) for window in WINDOWS for part in ("since", "count")},
    "updated_at": Column("DATETIME", True),
}

STAMP = "2026-11-10 09:30:00.000000"
#: A populated 1.3 install, as plain SQL: a user and its settings, a broker, an asset without ``classification_params``
#: (so the legacy copy of another step writes nothing that a downgrade would rebuild), its prices.
ROWS_1_3 = f"""
INSERT INTO users (id, username, email, hashed_password, created_at, updated_at)
    VALUES (1, 'counter_owner', 'counter_owner@example.test', '$argon2id$test', '{STAMP}', '{STAMP}');
INSERT INTO user_settings (user_id, base_currency, language, ui_preferences, created_at, updated_at)
    VALUES (1, 'EUR', 'it', '{{"theme":"dark"}}', '{STAMP}', '{STAMP}');
INSERT INTO brokers (id, name, created_at, updated_at) VALUES (1, 'Counter Broker', '{STAMP}', '{STAMP}');
INSERT INTO assets (id, display_name, currency, classification_params, asset_type, active, created_at, updated_at)
    VALUES (1, 'Counter ETF', 'EUR', NULL, 'ETF', 1, '{STAMP}', '{STAMP}');
INSERT INTO price_history (asset_id, date, close, currency, source_plugin_key, fetched_at) VALUES
    (1, '2026-11-02', 101.5, 'EUR', 'manual', '{STAMP}'),
    (1, '2026-11-03', 102.25, 'EUR', 'manual', '{STAMP}');
"""
#: One counter row, every column written: the windows of 2026-11-17 13:45 UTC.
INSERT_COUNTER = (
    "INSERT INTO plugin_call_counters (family, plugin_code, minute_since, minute_count, hour_since, hour_count, day_since, day_count, " "week_since, week_count, month_since, month_count, updated_at) VALUES (?, ?, 1794923100, 1, 1794920400, 2, 1794873600, 3, 1794787200, 4, 1793491200, 5, ?)"
)


# =============================================================================
# HELPERS
# =============================================================================


def _assert_table(db: Path) -> None:
    """Barrier: ``db`` holds the table of the step, or nothing that follows is about it."""
    assert TABLE in _tables(db), f"red until U1: {db.parent.name} (at {_revision(db)}) has no {TABLE}: the step {STEP} of {REV_006} has not created it"


def _columns(db: Path) -> dict[str, Column]:
    """``PRAGMA table_info`` of the table as the contract states a column, the key position read as SQLite reports it."""
    with _connect(db) as conn:
        return {name: Column(declared, bool(not_null), key) for _cid, name, declared, not_null, _default, key in conn.execute(f'PRAGMA table_info("{TABLE}")')}


def _table_sql(db: Path) -> str:
    with _connect(db) as conn:
        found = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLE,)).fetchone()
    assert found is not None, f"barrier: {db.parent.name} has no {TABLE}"
    return found[0]


def _objects(db: Path) -> list[tuple[Optional[str], ...]]:
    """Every row of ``sqlite_master`` as ``(type, name, tbl_name, sql)``, whitespace collapsed, by type and name."""
    with _connect(db) as conn:
        rows = conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    return [(kind, name, table, re.sub(r"\s+", " ", sql).strip() if sql else None) for kind, name, table, sql in rows]


def _of_the_step(objects: list[tuple[Optional[str], ...]]) -> list[tuple[Optional[str], ...]]:
    """The objects of the table, its automatic index included."""
    return [entry for entry in objects if entry[2] == TABLE]


def _counter_rows(db: Path) -> list[tuple[Any, ...]]:
    with _connect(db) as conn:
        return conn.execute(f"SELECT * FROM {TABLE} ORDER BY family, plugin_code").fetchall()


@contextmanager
def _environment_kept() -> Iterator[None]:
    """The process environment as it was before the block: importing ``db_schema_validate`` runs
    ``setup_test_database()``, which rewrites it."""
    saved = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


def _schema_validate() -> ModuleType:
    """``db_schema_validate``, imported here: imported by name its ``test_*`` functions would be collected in this file."""
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
        prices = conn.execute("SELECT count(*) FROM price_history").fetchone()[0]
    assert prices == 2 and _revision(db) == REV_005 and _violations(db) == [], "setup: a consistent 1.3 install at 005, two prices"
    return db


# =============================================================================
# 1. THE STEP IN THE REVISION
# =============================================================================


def test_u1_006_holds_the_plugin_call_counters_step() -> None:
    """``_upgrade_plugin_call_counters`` and ``_downgrade_plugin_call_counters``, each called on its own line of
    ``upgrade()`` and ``downgrade()``; the revision's docstring has a section named after the step."""
    print_section(f"{REV_006}: step {STEP}")
    module = _scripts().get_revision(REV_006).module
    missing = [name for name in (UPGRADE_STEP, DOWNGRADE_STEP) if not callable(getattr(module, name, None))]
    assert not missing, f"red until U1: {REV_006} defines no {missing}"
    assert f"{UPGRADE_STEP}(conn)" in inspect.getsource(module.upgrade), f"upgrade() of {REV_006} must call {UPGRADE_STEP}(conn)"
    assert f"{DOWNGRADE_STEP}(conn)" in inspect.getsource(module.downgrade), f"downgrade() of {REV_006} must call {DOWNGRADE_STEP}(conn)"
    assert re.search(rf"^{STEP} \(project 76, lot U1\)$", module.__doc__ or "", re.MULTILINE), f"the docstring of {REV_006} must have a section «{STEP} (project 76, lot U1)»"
    print_success(f"{STEP}: both functions, both calls, its docstring section")


# =============================================================================
# 2. THE TABLE ON A NEW DATABASE
# =============================================================================


def test_u1_a_new_database_at_006_has_the_columns_of_the_contract(fresh_006: Path) -> None:
    """Exactly the columns of the contract: name, declared type with its length, NOT NULL — the two key columns
    included —, position in the composite primary key (``family`` 1, ``plugin_code`` 2)."""
    print_section(f"{TABLE}: columns")
    _assert_table(fresh_006)
    found = _columns(fresh_006)
    assert found == CONTRACT, f"{TABLE}: the columns differ from the contract: missing or different {sorted(set(CONTRACT.items()) - set(found.items()))}, unexpected {sorted(set(found.items()) - set(CONTRACT.items()))}"
    print_success(f"{TABLE}: {len(found)} columns as the contract states them")


def test_u1_a_new_database_at_006_has_no_foreign_key_no_check_no_autoincrement_and_only_the_key_index(fresh_006: Path) -> None:
    """No foreign key, no CHECK, no AUTOINCREMENT in the table's SQL, and one index: SQLite's own of the primary key, on
    (``family``, ``plugin_code``), unique. Nothing written with ``CREATE INDEX`` (origin ``c``), no other UNIQUE (``u``)."""
    _assert_table(fresh_006)
    assert _foreign_keys(fresh_006, TABLE) == {}, f"{TABLE} has no foreign key: {_foreign_keys(fresh_006, TABLE)}"
    shape = _full_shape(fresh_006, TABLE)
    assert shape is not None and shape["primary key"] == KEY, f"{TABLE}: primary key {shape and shape['primary key']}, expected {KEY}"
    assert shape["check constraints (name: sql)"] == [], f"{TABLE} has no CHECK: {shape['check constraints (name: sql)']}"
    sql = _table_sql(fresh_006)
    assert "AUTOINCREMENT" not in sql.upper(), f"{TABLE} must not be AUTOINCREMENT: {sql}"
    indexes = sorted(_index_list(fresh_006, TABLE).values())
    assert indexes == [(True, "pk", KEY)], f"{TABLE}: the primary key's own index only, expected [(True, 'pk', {KEY})], found {indexes}"


def test_u1_the_composite_key_refuses_a_second_row_of_a_pair_and_stores_the_code_under_another_family(fresh_006: Path, tmp_path: Path) -> None:
    """(``asset``, ``yfinance``) twice is refused; (``group``, ``yfinance``) and (``asset``, ``justetf``) are stored."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_table(db)
    with _foreign_keys_on(db) as conn:
        conn.execute(INSERT_COUNTER, ("asset", "yfinance", STAMP))
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError) as refused:
            conn.execute(INSERT_COUNTER, ("asset", "yfinance", STAMP))
        conn.rollback()
        assert "UNIQUE constraint failed" in str(refused.value), f"refused for another reason: {refused.value}"
        conn.execute(INSERT_COUNTER, ("group", "yfinance", STAMP))
        conn.execute(INSERT_COUNTER, ("asset", "justetf", STAMP))
        conn.commit()
        found = conn.execute(f"SELECT family, plugin_code FROM {TABLE} ORDER BY family, plugin_code").fetchall()
    assert found == [("asset", "justetf"), ("asset", "yfinance"), ("group", "yfinance")], f"one row per pair: {found}"


# =============================================================================
# 3. A POPULATED 1.3 DATABASE UPGRADED
# =============================================================================


def test_u1_a_populated_1_3_database_keeps_its_rows_and_gets_the_table_empty(populated_1_3: Path, tmp_path: Path) -> None:
    """Every table the 1.3 install had is there, every row identical on the columns it had but those 006 drops
    (``alembic_harness.DROPPED_AT_006``: ``assets.classification_params``, plan 68 D7b); the counter table is there
    and empty; no foreign-key violation, integrity ``ok``."""
    print_section("A populated 1.3 database upgraded to 006")
    db = _copy(populated_1_3, tmp_path / "app.db")
    before = _rows(db)
    _migrate(db, "upgrade", REV_006)
    after = _rows(db)

    assert TABLE in after, f"red until U1: the upgraded 1.3 install has no {TABLE}"
    assert after[TABLE][1] == [], f"{TABLE} must start empty: {after[TABLE][1]}"
    lost = sorted(set(before) - set(after))
    assert lost == [], f"the upgrade lost the tables {lost}"
    changes = _row_changes(before, after, set(before) - BOOKKEEPING, columns_of=_kept_columns(before))
    assert not changes, f"the upgrade changed rows: {changes}"
    assert _violations(db) == [] and _integrity(db) == [("ok",)], f"violations {_violations(db)}, integrity {_integrity(db)}"
    print_success(f"{len(set(before) - BOOKKEEPING)} tables kept, {TABLE} empty")


# =============================================================================
# 4. THE MODELS AND THE MIGRATION AGREE
# =============================================================================


def test_u1_the_models_declare_the_table_and_its_class() -> None:
    """``SQLModel.metadata`` holds the table with its composite key; ``models.PluginCallCounter`` maps it."""
    declared = SQLModel.metadata.tables.get(TABLE)
    assert declared is not None, f"red until U1: the models declare no {TABLE}"
    assert tuple(column.name for column in declared.primary_key.columns) == KEY, f"{TABLE}: primary key {[c.name for c in declared.primary_key.columns]}, expected {KEY}"
    model = getattr(db_models, MODEL, None)
    assert model is not None, f"red until U1: backend.app.db.models has no {MODEL}"
    assert model.__tablename__ == TABLE, f"{MODEL}.__tablename__ is {model.__tablename__!r}, expected {TABLE!r}"


def test_u1_the_models_and_the_migration_build_the_same_table(fresh_006: Path, created_by_models: Path) -> None:
    """``create_all`` and ``alembic upgrade 006`` build the table alike: ``_full_shape`` (columns and nullability,
    primary key, foreign keys, indexes, unique sets, CHECKs, declared types) and the default of every column."""
    print_section(f"{TABLE}: migration = models")
    migrated, modelled = _full_shape(fresh_006, TABLE), _full_shape(created_by_models, TABLE)
    assert migrated is not None and modelled is not None, f"red until U1: {TABLE} is built by the migration: {migrated is not None}; by the models: {modelled is not None}"
    differences = {key: {"migration": migrated[key], "models": modelled.get(key)} for key in migrated if migrated[key] != modelled.get(key)}
    assert not differences, f"{TABLE}: the migration and the models disagree on {differences}"
    defaults = {origin: {name: column.default for name, column in _table_info(db, TABLE).items()} for origin, db in (("migration", fresh_006), ("models", created_by_models))}
    assert defaults["migration"] == defaults["models"], f"{TABLE}: the defaults differ: {defaults}"
    not_null = {origin: {name: column.not_null for name, column in _table_info(db, TABLE).items()} for origin, db in (("migration", fresh_006), ("models", created_by_models))}
    assert not_null["migration"] == not_null["models"], f"{TABLE}: NOT NULL as declared differs (the key columns included): {not_null}"
    print_success(f"{TABLE}: the same table both ways")


# =============================================================================
# 5. THE DOWNGRADE
# =============================================================================


def test_u1_the_downgrade_of_a_new_database_removes_the_table_and_leaves_005(fresh_006: Path, at_005: Path, tmp_path: Path) -> None:
    """``downgrade 005`` of a new database at 006: the table and its automatic index are gone, and every object of
    ``sqlite_master`` is what a new database at 005 holds, SQL text included once the columns 006 drops are taken out
    of both sides (its downgrade adds them back last; checked apart, ``_assert_dropped_columns_back``); the rows too."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_table(db)

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005
    assert _of_the_step(_objects(db)) == [], f"the downgrade must remove {TABLE}: {_of_the_step(_objects(db))}"
    _assert_dropped_columns_back(db)
    expected, found = _without_dropped_columns(_objects(at_005)), _without_dropped_columns(_objects(db))
    assert found == expected, f"every object must be as at 005: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"
    changes = _row_changes(_rows(at_005), _rows(db), set(_rows(at_005)) - BOOKKEEPING, columns_of=_rows(at_005))
    assert not changes, f"the downgrade of a new database changed rows: {changes}"


def test_u1_the_populated_database_goes_down_keeping_its_rows_and_up_again_gets_the_table_empty(populated_1_3: Path, tmp_path: Path) -> None:
    """The populated install at 006, given a counter row, goes down to 005: the table gone, every other row as it was at
    005, no violation, integrity ``ok``. Up again: the table back, empty (the counter row went with it)."""
    db = _copy(populated_1_3, tmp_path / "app.db")
    rows_at_005 = _rows(db)
    _migrate(db, "upgrade", REV_006)
    _assert_table(db)
    with _foreign_keys_on(db) as conn:
        conn.execute(INSERT_COUNTER, ("asset", "yfinance", STAMP))
        conn.commit()

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005 and TABLE not in _tables(db), f"down: at {_revision(db)}, {TABLE} still there: {TABLE in _tables(db)}"
    changes = _row_changes(rows_at_005, _rows(db), set(rows_at_005) - BOOKKEEPING, columns_of=rows_at_005)
    assert not changes, f"the downgrade changed other rows: {changes}"
    assert _violations(db) == [] and _integrity(db) == [("ok",)], f"violations {_violations(db)}, integrity {_integrity(db)}"

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006 and TABLE in _tables(db), f"up again: at {_revision(db)}, {TABLE} there: {TABLE in _tables(db)}"
    assert _counter_rows(db) == [], f"{TABLE} comes back empty: {_counter_rows(db)}"


# =============================================================================
# 6. EVERY PART CHECKS BEFORE IT ACTS
# =============================================================================


def test_u1_the_upgrade_run_again_over_its_own_work_changes_nothing(fresh_006: Path, tmp_path: Path) -> None:
    """The whole revision applied, a counter row written, then ``alembic_version`` set back to 005 by hand — an
    upgrade that wrote everything and stopped before Alembic recorded it —: ``upgrade`` goes through and changes no
    object of ``sqlite_master`` and no row."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_table(db)
    with _foreign_keys_on(db) as conn:
        conn.execute(INSERT_COUNTER, ("fx", "ECB", STAMP))
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_005,))
        conn.commit()
    objects_before, rows_before = _objects(db), _rows(db)

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006, f"the upgrade over its own work must go through: {_revision(db)}"
    assert _objects(db) == objects_before, "the step run again must leave the schema as it found it"
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=rows_before)
    assert not changes, f"the step run again must change no row: {changes}"


def test_u1_an_upgrade_finding_the_table_already_there_completes_and_keeps_its_row(fresh_006: Path, at_005: Path, tmp_path: Path) -> None:
    """A database at 005 holding the table — written with the SQL a new database at 006 holds — and a row in it:
    ``upgrade 006`` goes through, the table's objects are those of a new database at 006, the row is kept."""
    _assert_table(fresh_006)
    db = _copy(at_005, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        conn.execute(_table_sql(fresh_006))
        conn.execute(INSERT_COUNTER, ("group", "x76_shared", STAMP))
        conn.commit()
    kept = _counter_rows(db)
    assert _revision(db) == REV_005 and len(kept) == 1, "setup: the run stopped before Alembic recorded the revision, one row written"

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006, f"the upgrade must go through: {_revision(db)}"
    expected, found = _of_the_step(_objects(fresh_006)), _of_the_step(_objects(db))
    assert found == expected, f"the table must end as on a new database at 006: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"
    assert _counter_rows(db) == kept, f"the table found must be kept with its row: {_counter_rows(db)}"


def test_u1_a_downgrade_finding_the_table_already_gone_completes_to_005(fresh_006: Path, at_005: Path, tmp_path: Path) -> None:
    """A downgrade that had already dropped the table, the revision still 006: ``downgrade 005`` goes through, every
    object as at 005."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_table(db)
    with _foreign_keys_on(db) as conn:
        conn.execute(f"DROP TABLE {TABLE}")
        conn.commit()
    assert _revision(db) == REV_006, "setup: the downgrade stopped before Alembic recorded it"

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005
    _assert_dropped_columns_back(db)
    expected, found = _without_dropped_columns(_objects(at_005)), _without_dropped_columns(_objects(db))
    assert found == expected, f"every object must be as at 005: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"


# =============================================================================
# 7. NO REDUNDANT INDEX
# =============================================================================


def test_u1_the_redundant_index_check_passes_at_006(fresh_006: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``db_schema_validate.test_no_redundant_indexes`` on a copy of a new database at 006, its engine patched to that
    private file: the key's automatic index repeats no other. Barrier: the table is there, or the check proves nothing."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_table(db)
    schema_validate = _schema_validate()
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    monkeypatch.setattr(schema_validate, "get_sync_engine", lambda: engine)
    try:
        schema_validate.test_no_redundant_indexes()
    finally:
        engine.dispose()
