"""Migration ``006_release_1_4_0_schema``, step ``charge_links`` (project 66, lot R1): a transaction that is the charge
(a fee, a tax) of another points at it with ``transactions.parent_transaction_id``.

The 1.4 cycle has one revision, and several workstreams each add a step of their own to it (its docstring says how).
This file pins ONLY what the step ``charge_links`` creates — the column ``transactions.parent_transaction_id``, its
foreign key and its index ``idx_transactions_parent`` — and never the whole schema at 006: what another step adds is that
step's to pin. So the objects of the step are compared on their own, rows are compared on the columns they had before
the upgrade, and a whole-database comparison appears only after a downgrade, at 005.

``transactions.parent_transaction_id``: INTEGER, nullable, default NULL, not part of the primary key; a foreign key to
``transactions(id)`` with no ON DELETE and no ON UPDATE action (NO ACTION), ``DEFERRABLE INITIALLY DEFERRED`` — as
``related_transaction_id`` is: the parent and its child may be written in one transaction, in either order, and the link
is checked at COMMIT. One new index, ``idx_transactions_parent`` on (``parent_transaction_id``), PARTIAL: ``WHERE
parent_transaction_id IS NOT NULL`` (most rows have no parent). ``related_transaction_id`` and ``idx_transactions_related``
stay as they are.

The contract pinned here:

1. The revision holds the step as its docstring asks: ``_upgrade_charge_links`` and ``_downgrade_charge_links``, each
   called on its own line of ``upgrade()`` and ``downgrade()``, and a docstring section named ``charge_links``.
2. A new database taken to 006 — by name, not ``head`` — has the column (name, declared type, nullable, default NULL, not
   in the primary key), the foreign key (``PRAGMA foreign_key_list`` and, for the deferral that only the SQL text shows,
   ``sqlite_master``), the partial index (``PRAGMA index_list`` partial flag and its SQL), and the old
   ``idx_transactions_related`` unchanged. At work, foreign keys on, plain SQL: a child of an existing transaction
   commits; a child of a missing id fails at COMMIT, not at the statement; a parent deleted while a child remains fails
   at COMMIT; parent and child deleted in one transaction, in either order, commit. ``EXPLAIN QUERY PLAN`` of
   ``WHERE parent_transaction_id IN (?, ?)`` searches ``idx_transactions_parent``.
3. A populated 1.3 database (at 005, plain SQL: a user, two brokers, an asset, a BUY, a TRANSFER pair linked both ways,
   a FEE) upgraded to 006 keeps every row of every table on the columns it had, every transaction gets
   ``parent_transaction_id`` NULL, no foreign-key violation, integrity ``ok``.
4. Models = migration: ``SQLModel.metadata`` has the column, its deferred foreign key and the partial index; ``create_all``
   builds the step's objects with the shape the migration gives them (column info without its position, foreign-key
   list, deferral, index flags and normalised SQL).
5. The downgrade 006 → 005 removes the index then the column and leaves every object as a new database at 005 has it;
   the populated database goes down keeping every row on its 005 columns, and up again gets the column back, all NULL.
6. Every part checks before it acts: an upgrade run again over its own work changes no object and no row; an upgrade that
   finds the column already there but no index (stopped half way) completes and creates the index, the rows kept; a
   downgrade that finds the column already gone completes to 005.
7. The redundant-index check of ``db_schema_validate`` (``test_no_redundant_indexes``) passes on a database at 006.

Safety and fidelity: ``alembic_harness``. Every database is a file under ``tmp_path``; Alembic runs in this process on
that file alone, with ``PRAGMA foreign_keys`` asserted 1 at every step. Rows are written with plain SQL. The model is
reached through ``SQLModel.metadata``, never imported by name. ``get_async_engine`` and ``get_sync_engine`` are
tripwires: no lane database.

Red on HEAD 2767d238a: ``006_release_1_4_0_schema`` has no step ``charge_links``, so every migration below goes through
and each test fails on an assertion — the step functions, the column, the index, the model column are missing. Every test
whose assertions would hold on an absent column (the unchanged related index, nothing changed when run again, the
downgrade finding it gone, the redundant-index check) passes a barrier first: the column is there. No guard of this file
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
from pathlib import Path
from types import ModuleType
from typing import Any, NoReturn, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import session as db_session
from backend.app.db.base import SQLModel
from backend.test_scripts.test_db.alembic_harness import (
    _connect,
    _copy,
    _create_all,
    _foreign_keys_on,
    _index_list,
    _integrity,
    _migrate,
    _revision,
    _row_changes,
    _rows,
    _scripts,
    _table_info,
    _violations,
)
from backend.test_scripts.test_utils import print_section, print_success

REV_005 = "005_release_1_3_0_schema"
REV_006 = "006_release_1_4_0_schema"
STEP = "charge_links"
UPGRADE_STEP, DOWNGRADE_STEP = f"_upgrade_{STEP}", f"_downgrade_{STEP}"
TABLE = "transactions"
COLUMN = "parent_transaction_id"
INDEX = "idx_transactions_parent"
RELATED_INDEX = "idx_transactions_related"
#: Alembic's own bookkeeping: its row changes with every step.
BOOKKEEPING = frozenset({"alembic_version"})

STAMP = "2026-11-10 09:30:00.000000"
#: A populated 1.3 install, as plain SQL: a user, two brokers, an asset, a BUY, a TRANSFER pair linked both ways (the
#: links written with UPDATE: each statement commits alone, and a link to a row not yet written is refused at its
#: commit), a FEE.
ROWS_1_3 = f"""
INSERT INTO users (id, username, email, hashed_password, created_at, updated_at)
    VALUES (1, 'charge_owner', 'charge_owner@example.test', '$argon2id$test', '{STAMP}', '{STAMP}');
INSERT INTO user_settings (user_id, base_currency, language, ui_preferences, created_at, updated_at)
    VALUES (1, 'EUR', 'it', '{{"theme":"dark"}}', '{STAMP}', '{STAMP}');
INSERT INTO brokers (id, name, created_at, updated_at) VALUES (1, 'Charge Broker A', '{STAMP}', '{STAMP}'), (2, 'Charge Broker B', '{STAMP}', '{STAMP}');
INSERT INTO assets (id, display_name, currency, classification_params, asset_type, active, created_at, updated_at)
    VALUES (1, 'Charge ETF', 'EUR', NULL, 'ETF', 1, '{STAMP}', '{STAMP}');
INSERT INTO transactions (id, broker_id, asset_id, type, date, quantity, amount, currency, created_at, updated_at) VALUES
    (1, 1, 1, 'BUY', '2026-11-02', 10, -1000, 'EUR', '{STAMP}', '{STAMP}'),
    (2, 1, 1, 'TRANSFER', '2026-11-03', -5, 0, NULL, '{STAMP}', '{STAMP}'),
    (3, 2, 1, 'TRANSFER', '2026-11-03', 5, 0, NULL, '{STAMP}', '{STAMP}'),
    (4, 1, NULL, 'FEE', '2026-11-02', 0, -2.5, 'EUR', '{STAMP}', '{STAMP}');
UPDATE transactions SET related_transaction_id = 3 WHERE id = 2;
UPDATE transactions SET related_transaction_id = 2 WHERE id = 3;
"""
INSERT_TRANSACTION = f"INSERT INTO transactions (broker_id, type, date, quantity, amount, currency, {COLUMN}, created_at, updated_at) VALUES (?, ?, '2026-11-05', 0, ?, 'EUR', ?, '{STAMP}', '{STAMP}')"
#: An id no row of a new database holds.
MISSING = 987654321


# =============================================================================
# HELPERS
# =============================================================================


def _assert_column(db: Path) -> None:
    """Barrier: ``db`` holds the column of the step, or nothing that follows is about it."""
    assert COLUMN in _table_info(db, TABLE), f"red until R1: {db.parent.name} (at {_revision(db)}) has no {TABLE}.{COLUMN}: the step {STEP} of {REV_006} has not added it"


def _table_sql(db: Path) -> str:
    with _connect(db) as conn:
        found = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLE,)).fetchone()
    assert found is not None, f"barrier: {db.parent.name} has no {TABLE}"
    return found[0]


def _squeezed(sql: Optional[str]) -> Optional[str]:
    """``sql`` without any whitespace and without quotes: ``ALTER TABLE`` and ``DROP COLUMN`` edit the text of the table
    and may leave another spacing than the one it had."""
    return re.sub(r"[\s\"`]", "", sql) if sql else None


def _objects(db: Path) -> list[tuple[Optional[str], ...]]:
    """Every row of ``sqlite_master`` as ``(type, name, tbl_name, squeezed sql)``, by type and name."""
    with _connect(db) as conn:
        rows = conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()
    return [(kind, name, table, _squeezed(sql)) for kind, name, table, sql in rows]


def _deferred_foreign_key(table_sql: str) -> bool:
    """Whether the table's SQL declares ``parent_transaction_id`` as a ``REFERENCES transactions (id) DEFERRABLE INITIALLY
    DEFERRED``: written on the column, or as a table-level ``FOREIGN KEY``."""
    text = re.sub(r"\s+", " ", re.sub(r"[\"`]", "", table_sql))
    tail = r"REFERENCES transactions ?\( ?id ?\) DEFERRABLE INITIALLY DEFERRED"
    return bool(re.search(rf"{COLUMN} INTEGER (?:NULL )?{tail}", text) or re.search(rf"FOREIGN KEY ?\( ?{COLUMN} ?\) {tail}", text))


def _foreign_key_rows(db: Path) -> list[tuple[Any, ...]]:
    """The ``PRAGMA foreign_key_list`` rows of the column: (target table, target column, ON UPDATE, ON DELETE, MATCH)."""
    with _connect(db) as conn:
        return [(target, to, on_update, on_delete, match) for _id, _seq, target, source, to, on_update, on_delete, match in conn.execute(f'PRAGMA foreign_key_list("{TABLE}")') if source == COLUMN]


def _index_row(db: Path, name: str) -> Optional[tuple[bool, str, bool]]:
    """``(unique, origin, partial)`` of an index of the table, ``None`` when it does not exist."""
    with _connect(db) as conn:
        for _seq, listed, unique, origin, partial in conn.execute(f'PRAGMA index_list("{TABLE}")'):
            if listed == name:
                return bool(unique), origin, bool(partial)
    return None


def _index_sql(db: Path, name: str) -> Optional[str]:
    with _connect(db) as conn:
        found = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)).fetchone()
    return _squeezed(found[0]).lower() if found and found[0] else None


#: The index as the contract writes it, squeezed and lower case (``CREATE INDEX [IF NOT EXISTS]`` read the same).
PARTIAL_INDEX_SQL = f"createindex{INDEX}on{TABLE}({COLUMN})where{COLUMN}isnotnull"


def _step_objects(db: Path) -> dict[str, Any]:
    """What the step is, read back from SQLite, for the migration and the models to be compared: the column as
    ``PRAGMA table_info`` reports it (never its position), the foreign key and its deferral, the index."""
    info = _table_info(db, TABLE).get(COLUMN)
    return {
        "column": info,
        "foreign key": _foreign_key_rows(db),
        "deferred in the table's SQL": _deferred_foreign_key(_table_sql(db)),
        "index": _index_row(db, INDEX),
        "index columns": _index_list(db, TABLE).get(INDEX),
        "index sql": (_index_sql(db, INDEX) or "").replace("createindexifnotexists", "createindex"),
    }


def _children(db: Path) -> list[tuple[int, Any]]:
    with _connect(db) as conn:
        return conn.execute(f"SELECT id, {COLUMN} FROM {TABLE} ORDER BY id").fetchall()


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


def _new_broker(conn: sqlite3.Connection) -> int:
    cursor = conn.execute("INSERT INTO brokers (name, created_at, updated_at) VALUES (?, ?, ?)", (f"R1 {os.urandom(4).hex()}", STAMP, STAMP))
    conn.commit()
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def _new_transaction(conn: sqlite3.Connection, broker: int, parent: Optional[int] = None) -> int:
    """A FEE of ``broker`` pointing at ``parent``; not committed."""
    cursor = conn.execute(INSERT_TRANSACTION, (broker, "FEE", -1, parent))
    assert cursor.lastrowid is not None
    return cursor.lastrowid


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
        count = conn.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
        linked = conn.execute(f"SELECT count(*) FROM {TABLE} WHERE related_transaction_id IS NOT NULL").fetchone()[0]
    assert count == 4 and linked == 2 and _revision(db) == REV_005 and _violations(db) == [], "setup: a consistent 1.3 install at 005, four transactions, a TRANSFER pair linked both ways"
    return db


# =============================================================================
# 1. THE STEP IN THE REVISION
# =============================================================================


def test_r1_006_holds_the_charge_links_step() -> None:
    """``_upgrade_charge_links`` and ``_downgrade_charge_links``, each called on its own line of ``upgrade()`` and
    ``downgrade()``; the revision's docstring has a section named after the step."""
    print_section(f"{REV_006}: step {STEP}")
    module = _scripts().get_revision(REV_006).module
    missing = [name for name in (UPGRADE_STEP, DOWNGRADE_STEP) if not callable(getattr(module, name, None))]
    assert not missing, f"red until R1: {REV_006} defines no {missing}"
    assert f"{UPGRADE_STEP}(conn)" in inspect.getsource(module.upgrade), f"upgrade() of {REV_006} must call {UPGRADE_STEP}(conn)"
    assert f"{DOWNGRADE_STEP}(conn)" in inspect.getsource(module.downgrade), f"downgrade() of {REV_006} must call {DOWNGRADE_STEP}(conn)"
    assert re.search(rf"^{STEP} \(project 66, lot R1\)$", module.__doc__ or "", re.MULTILINE), f"the docstring of {REV_006} must have a section «{STEP} (project 66, lot R1)»"
    print_success(f"{STEP}: both functions, both calls, its docstring section")


# =============================================================================
# 2. THE COLUMN, ITS FOREIGN KEY AND ITS INDEX ON A NEW DATABASE
# =============================================================================


def test_r1_a_new_database_at_006_has_the_column_of_the_contract(fresh_006: Path) -> None:
    """INTEGER, nullable, default NULL, not in the primary key; ``related_transaction_id`` beside it as it was."""
    print_section(f"{TABLE}.{COLUMN}: the column")
    _assert_column(fresh_006)
    info = _table_info(fresh_006, TABLE)
    column = info[COLUMN]
    assert column.type.upper() == "INTEGER", f"{COLUMN}: declared {column.type!r}, expected INTEGER"
    assert column.not_null is False, f"{COLUMN} must be nullable"
    assert column.default is None, f"{COLUMN} must default to NULL: {column.default!r}"
    assert column.primary_key is False, f"{COLUMN} is not part of the primary key"
    assert [name for name, declared in info.items() if declared.primary_key] == ["id"], "the primary key stays (id)"
    related = info.get("related_transaction_id")
    assert related is not None and related.type.upper() == "INTEGER" and related.not_null is False, f"related_transaction_id must stay as it was: {related}"
    print_success(f"{COLUMN}: INTEGER NULL DEFAULT NULL, not a key")


def test_r1_the_foreign_key_points_at_the_transaction_with_no_action_and_is_deferred(fresh_006: Path) -> None:
    """``PRAGMA foreign_key_list``: ``transactions(id)``, ON UPDATE and ON DELETE NO ACTION, MATCH NONE; the table's SQL
    says ``DEFERRABLE INITIALLY DEFERRED`` (it shows nowhere else). ``related_transaction_id``'s foreign key as before."""
    _assert_column(fresh_006)
    assert _foreign_key_rows(fresh_006) == [(TABLE, "id", "NO ACTION", "NO ACTION", "NONE")], f"{COLUMN}: foreign key rows {_foreign_key_rows(fresh_006)}"
    assert _deferred_foreign_key(_table_sql(fresh_006)), f"{COLUMN} must be DEFERRABLE INITIALLY DEFERRED in the table's SQL: {_table_sql(fresh_006)}"
    with _connect(fresh_006) as conn:
        related = [(target, to, on_delete) for _id, _seq, target, source, to, _on_update, on_delete, _match in conn.execute(f'PRAGMA foreign_key_list("{TABLE}")') if source == "related_transaction_id"]
    assert related == [(TABLE, "id", "NO ACTION")], f"related_transaction_id's foreign key must stay: {related}"


def test_r1_the_index_is_partial_on_the_column_and_the_related_index_is_unchanged(fresh_006: Path, at_005: Path) -> None:
    """``idx_transactions_parent``: one column, not unique, created with ``CREATE INDEX`` (origin ``c``), partial
    (``PRAGMA index_list``), its SQL ``WHERE parent_transaction_id IS NOT NULL``. ``idx_transactions_related`` is the full
    index it was: same columns, not partial, same SQL as at 005."""
    _assert_column(fresh_006)
    assert _index_row(fresh_006, INDEX) == (False, "c", True), f"{INDEX}: (unique, origin, partial) {_index_row(fresh_006, INDEX)}, expected (False, 'c', True)"
    assert _index_list(fresh_006, TABLE)[INDEX] == (False, "c", (COLUMN,)), f"{INDEX}: {_index_list(fresh_006, TABLE)[INDEX]}"
    sql = (_index_sql(fresh_006, INDEX) or "").replace("createindexifnotexists", "createindex")
    assert sql == PARTIAL_INDEX_SQL, f"{INDEX}: its SQL is {sql!r}, expected {PARTIAL_INDEX_SQL!r}"
    assert _index_row(fresh_006, RELATED_INDEX) == _index_row(at_005, RELATED_INDEX) == (False, "c", False), f"{RELATED_INDEX} must stay a full index: {_index_row(fresh_006, RELATED_INDEX)}"
    assert _index_sql(fresh_006, RELATED_INDEX) == _index_sql(at_005, RELATED_INDEX), f"{RELATED_INDEX} must stay as at 005"


def test_r1_a_child_of_an_existing_transaction_commits(fresh_006: Path, tmp_path: Path) -> None:
    """Foreign keys on: a FEE pointing at a transaction that exists is stored, read back."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)
    with _foreign_keys_on(db) as conn:
        broker = _new_broker(conn)
        parent = _new_transaction(conn, broker)
        conn.commit()
        child = _new_transaction(conn, broker, parent)
        conn.commit()
    assert dict(_children(db)) == {parent: None, child: parent}, f"the child must point at its parent: {_children(db)}"


def test_r1_a_child_of_a_missing_transaction_fails_at_commit_and_not_at_the_statement(fresh_006: Path, tmp_path: Path) -> None:
    """The check is deferred: the INSERT of a child of a missing id goes through, the COMMIT is refused with a foreign-key
    error, and after the rollback the row is not there."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)
    with _foreign_keys_on(db) as conn:
        broker = _new_broker(conn)
        child = _new_transaction(conn, broker, MISSING)  # must not raise: deferred
        with pytest.raises(sqlite3.IntegrityError) as refused:
            conn.commit()
        conn.rollback()
        assert "FOREIGN KEY constraint failed" in str(refused.value), f"refused for another reason: {refused.value}"
        assert conn.execute(f"SELECT count(*) FROM {TABLE} WHERE id = ?", (child,)).fetchone()[0] == 0, "the refused row must not stay"
    assert _violations(db) == []


def test_r1_a_parent_deleted_while_a_child_remains_fails_at_commit(fresh_006: Path, tmp_path: Path) -> None:
    """NO ACTION: deleting a parent that still has a child is refused at COMMIT, and after the rollback both rows are there."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)
    with _foreign_keys_on(db) as conn:
        broker = _new_broker(conn)
        parent = _new_transaction(conn, broker)
        child = _new_transaction(conn, broker, parent)
        conn.commit()
        conn.execute(f"DELETE FROM {TABLE} WHERE id = ?", (parent,))  # must not raise: deferred
        with pytest.raises(sqlite3.IntegrityError) as refused:
            conn.commit()
        conn.rollback()
        assert "FOREIGN KEY constraint failed" in str(refused.value), f"refused for another reason: {refused.value}"
    assert dict(_children(db)) == {parent: None, child: parent}, f"the delete must have been rolled back: {_children(db)}"


@pytest.mark.parametrize("first", ["parent", "child"])
def test_r1_parent_and_child_deleted_in_one_transaction_commit_in_either_order(fresh_006: Path, tmp_path: Path, first: str) -> None:
    """The check runs at COMMIT: deleting the child before or after its parent in one transaction is accepted."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)
    with _foreign_keys_on(db) as conn:
        broker = _new_broker(conn)
        parent = _new_transaction(conn, broker)
        child = _new_transaction(conn, broker, parent)
        conn.commit()
        order = (parent, child) if first == "parent" else (child, parent)
        for identifier in order:
            conn.execute(f"DELETE FROM {TABLE} WHERE id = ?", (identifier,))
        conn.commit()  # must not raise
        left = conn.execute(f"SELECT count(*) FROM {TABLE} WHERE id IN (?, ?)", (parent, child)).fetchone()[0]
    assert left == 0, f"both rows must be gone: {left} left"


def test_r1_the_children_of_some_parents_are_searched_through_the_partial_index(fresh_006: Path) -> None:
    """``WHERE parent_transaction_id IN (?, ?)`` — the query that reads the charges of some transactions — searches
    ``idx_transactions_parent`` (SQLite proves ``IN`` implies ``IS NOT NULL``, so the partial index applies)."""
    _assert_column(fresh_006)
    with _connect(fresh_006) as conn:
        plan = [detail for _id, _parent, _unused, detail in conn.execute(f"EXPLAIN QUERY PLAN SELECT id FROM {TABLE} WHERE {COLUMN} IN (?, ?)", (1, 2))]
    assert any(re.search(rf"SEARCH {TABLE} USING (?:COVERING )?INDEX {INDEX}\b", detail) for detail in plan), f"the plan must search {INDEX}: {plan}"


# =============================================================================
# 3. A POPULATED 1.3 DATABASE UPGRADED
# =============================================================================


def test_r1_a_populated_1_3_database_keeps_its_rows_and_every_transaction_has_no_parent(populated_1_3: Path, tmp_path: Path) -> None:
    """Every table the 1.3 install had is there, every row identical on the columns it had; every transaction has
    ``parent_transaction_id`` NULL; no foreign-key violation, integrity ``ok``."""
    print_section("A populated 1.3 database upgraded to 006")
    db = _copy(populated_1_3, tmp_path / "app.db")
    before = _rows(db)
    _migrate(db, "upgrade", REV_006)
    after = _rows(db)

    _assert_column(db)
    lost = sorted(set(before) - set(after))
    assert lost == [], f"the upgrade lost the tables {lost}"
    changes = _row_changes(before, after, set(before) - BOOKKEEPING, columns_of=before)
    assert not changes, f"the upgrade changed rows: {changes}"
    assert _children(db) == [(1, None), (2, None), (3, None), (4, None)], f"every transaction must have no parent: {_children(db)}"
    assert _violations(db) == [] and _integrity(db) == [("ok",)], f"violations {_violations(db)}, integrity {_integrity(db)}"
    print_success(f"{len(set(before) - BOOKKEEPING)} tables kept, {len(_children(db))} transactions without a parent")


# =============================================================================
# 4. THE MODELS AND THE MIGRATION AGREE
# =============================================================================


def test_r1_the_models_declare_the_column_its_deferred_foreign_key_and_the_partial_index() -> None:
    """``SQLModel.metadata``: ``transactions.parent_transaction_id`` nullable, a foreign key to ``transactions.id``
    deferrable initially deferred with no ondelete/onupdate; ``idx_transactions_parent`` on the column with its
    ``sqlite_where``; ``idx_transactions_related`` still declared."""
    table = SQLModel.metadata.tables[TABLE]
    column = table.columns.get(COLUMN)
    assert column is not None, f"red until R1: the models declare no {TABLE}.{COLUMN}"
    assert column.nullable and not column.primary_key, f"{COLUMN} must be nullable and not a key"
    foreign_keys = list(column.foreign_keys)
    assert len(foreign_keys) == 1, f"{COLUMN}: one foreign key expected: {foreign_keys}"
    fk = foreign_keys[0]
    assert fk.target_fullname == f"{TABLE}.id", f"{COLUMN} references {fk.target_fullname}"
    assert fk.constraint.deferrable is True and (fk.constraint.initially or "").upper() == "DEFERRED", f"deferrable {fk.constraint.deferrable}, initially {fk.constraint.initially}"
    assert not fk.constraint.ondelete and not fk.constraint.onupdate, f"no action expected: ondelete {fk.constraint.ondelete}, onupdate {fk.constraint.onupdate}"
    indexes = {index.name: index for index in table.indexes}
    assert RELATED_INDEX in indexes, f"{RELATED_INDEX} must stay declared"
    index = indexes.get(INDEX)
    assert index is not None, f"red until R1: the models declare no {INDEX}: {sorted(name for name in indexes if name)}"
    assert [c.name for c in index.columns] == [COLUMN] and not index.unique, f"{INDEX}: columns {[c.name for c in index.columns]}, unique {index.unique}"
    where = index.dialect_options["sqlite"]["where"]
    assert where is not None, f"{INDEX} must be partial: no sqlite_where"
    assert re.sub(r"\s+", "", str(where)).lower().replace(f"{TABLE}.", "") == f"{COLUMN}isnotnull", f"{INDEX}: sqlite_where is {str(where)!r}, expected {COLUMN} IS NOT NULL"


def test_r1_the_models_and_the_migration_build_the_same_objects(fresh_006: Path, created_by_models: Path) -> None:
    """``create_all`` and ``alembic upgrade 006`` give the step's objects the same shape: the column as ``PRAGMA
    table_info`` reports it (never its position), the foreign key and its deferral, the partial index (flags, columns,
    normalised SQL). Only the step's objects: the rest of ``transactions`` is not this step's."""
    print_section(f"{TABLE}.{COLUMN}: migration = models")
    migrated, modelled = _step_objects(fresh_006), _step_objects(created_by_models)
    assert migrated["column"] is not None and modelled["column"] is not None, f"red until R1: {COLUMN} is built by the migration: {migrated['column'] is not None}; by the models: {modelled['column'] is not None}"
    differences = {key: {"migration": migrated[key], "models": modelled[key]} for key in migrated if migrated[key] != modelled[key]}
    assert not differences, f"{TABLE}.{COLUMN}: the migration and the models disagree on {differences}"
    assert migrated["deferred in the table's SQL"] is True, "both must declare the foreign key deferred"
    print_success(f"{COLUMN}, its foreign key and {INDEX}: the same both ways")


# =============================================================================
# 5. THE DOWNGRADE
# =============================================================================


def test_r1_the_downgrade_of_a_new_database_removes_the_index_then_the_column_and_leaves_005(fresh_006: Path, at_005: Path, tmp_path: Path) -> None:
    """``downgrade 005`` of a new database at 006: the index and the column are gone, and every object of
    ``sqlite_master`` is what a new database at 005 holds (SQL compared without whitespace: ``DROP COLUMN`` edits the
    table's text); ``transactions`` has the columns, foreign keys and indexes it has at 005."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005
    assert COLUMN not in _table_info(db, TABLE), f"the downgrade must drop {COLUMN}"
    assert _index_row(db, INDEX) is None, f"the downgrade must drop {INDEX}"
    assert _table_info(db, TABLE) == _table_info(at_005, TABLE), "transactions must have the columns it has at 005"
    assert _index_list(db, TABLE) == _index_list(at_005, TABLE), "transactions must have the indexes it has at 005"
    expected, found = _objects(at_005), _objects(db)
    assert found == expected, f"every object must be as at 005: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"
    changes = _row_changes(_rows(at_005), _rows(db), set(_rows(at_005)) - BOOKKEEPING, columns_of=_rows(at_005))
    assert not changes, f"the downgrade of a new database changed rows: {changes}"


def test_r1_the_populated_database_goes_down_keeping_its_rows_and_up_again_gets_the_column_all_null(populated_1_3: Path, tmp_path: Path) -> None:
    """The populated install at 006, its FEE pointing at the BUY, goes down to 005: the column gone, every other row as it
    was at 005, no violation, integrity ``ok``. Up again: the column back, every transaction without a parent (the link
    went with the column)."""
    db = _copy(populated_1_3, tmp_path / "app.db")
    rows_at_005 = _rows(db)
    _migrate(db, "upgrade", REV_006)
    _assert_column(db)
    with _foreign_keys_on(db) as conn:
        conn.execute(f"UPDATE {TABLE} SET {COLUMN} = 1 WHERE id = 4")
        conn.commit()
    assert _children(db)[3] == (4, 1), "setup: the FEE points at the BUY"

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005 and COLUMN not in _table_info(db, TABLE), f"down: at {_revision(db)}, {COLUMN} still there"
    changes = _row_changes(rows_at_005, _rows(db), set(rows_at_005) - BOOKKEEPING, columns_of=rows_at_005)
    assert not changes, f"the downgrade changed other rows: {changes}"
    assert _violations(db) == [] and _integrity(db) == [("ok",)], f"violations {_violations(db)}, integrity {_integrity(db)}"

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006 and COLUMN in _table_info(db, TABLE), f"up again: at {_revision(db)}, {COLUMN} there: {COLUMN in _table_info(db, TABLE)}"
    assert _children(db) == [(1, None), (2, None), (3, None), (4, None)], f"the column comes back all NULL: {_children(db)}"
    assert _index_row(db, INDEX) == (False, "c", True)


# =============================================================================
# 6. EVERY PART CHECKS BEFORE IT ACTS
# =============================================================================


def test_r1_the_upgrade_run_again_over_its_own_work_changes_nothing(fresh_006: Path, tmp_path: Path) -> None:
    """The whole revision applied, a parent and its child written, then ``alembic_version`` set back to 005 by hand — an
    upgrade that wrote everything and stopped before Alembic recorded it —: ``upgrade`` goes through and changes no
    object of ``sqlite_master`` and no row."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)
    with _foreign_keys_on(db) as conn:
        broker = _new_broker(conn)
        parent = _new_transaction(conn, broker)
        conn.commit()
        _new_transaction(conn, broker, parent)
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_005,))
        conn.commit()
    objects_before, rows_before = _objects(db), _rows(db)

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006, f"the upgrade over its own work must go through: {_revision(db)}"
    assert _objects(db) == objects_before, "the step run again must leave the schema as it found it"
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=rows_before)
    assert not changes, f"the step run again must change no row: {changes}"
    assert any(link is not None for _id, link in _children(db)), "the link written must be kept"


def test_r1_an_upgrade_finding_the_column_but_no_index_completes_and_keeps_its_rows(fresh_006: Path, at_005: Path, tmp_path: Path) -> None:
    """A database at 005 holding the column — added with an ``ALTER TABLE`` as the step adds it — but no index (an upgrade
    stopped half way), a parent and a child in it: ``upgrade 006`` goes through, the step's objects are those of a new
    database at 006, the rows are kept."""
    _assert_column(fresh_006)
    db = _copy(at_005, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        conn.execute(f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} INTEGER REFERENCES {TABLE} (id) DEFERRABLE INITIALLY DEFERRED")
        broker = _new_broker(conn)
        parent = _new_transaction(conn, broker)
        conn.commit()
        _new_transaction(conn, broker, parent)
        conn.commit()
    kept = _children(db)
    assert _revision(db) == REV_005 and _index_row(db, INDEX) is None and len(kept) == 2, "setup: the run stopped after the column, before the index"

    _migrate(db, "upgrade", REV_006)

    assert _revision(db) == REV_006, f"the upgrade must go through: {_revision(db)}"
    assert _step_objects(db) == _step_objects(fresh_006), f"the step's objects must end as on a new database at 006: {_step_objects(db)}"
    assert _children(db) == kept, f"the rows found must be kept: {_children(db)}"


def test_r1_a_downgrade_finding_the_column_already_gone_completes_to_005(fresh_006: Path, at_005: Path, tmp_path: Path) -> None:
    """A downgrade that had already dropped the index and the column, the revision still 006: ``downgrade 005`` goes
    through, every object as at 005."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)
    with _foreign_keys_on(db) as conn:
        conn.execute(f"DROP INDEX {INDEX}")
        conn.execute(f"ALTER TABLE {TABLE} DROP COLUMN {COLUMN}")
        conn.commit()
    assert _revision(db) == REV_006 and COLUMN not in _table_info(db, TABLE), "setup: the downgrade stopped before Alembic recorded it"

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005
    expected, found = _objects(at_005), _objects(db)
    assert found == expected, f"every object must be as at 005: missing {sorted(set(expected) - set(found))}, unexpected {sorted(set(found) - set(expected))}"


# =============================================================================
# 7. NO REDUNDANT INDEX
# =============================================================================


def test_r1_the_redundant_index_check_passes_at_006(fresh_006: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``db_schema_validate.test_no_redundant_indexes`` on a copy of a new database at 006, its engine patched to that
    private file: the partial index beside the full ``idx_transactions_related`` is no redundancy. Barrier: the partial
    index is there, or the check proves nothing about it."""
    db = _copy(fresh_006, tmp_path / "app.db")
    _assert_column(db)
    assert _index_row(db, INDEX) == (False, "c", True), f"barrier: {INDEX} must be there and partial: {_index_row(db, INDEX)}"
    schema_validate = _schema_validate()
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    monkeypatch.setattr(schema_validate, "get_sync_engine", lambda: engine)
    try:
        schema_validate.test_no_redundant_indexes()
    finally:
        engine.dispose()
