"""Migration ``010_provider_reported_currency``: the quote currency a provider reported, kept on its assignment (release 1.3, workstream Z, lot Z-32 (c), the coordinator's contract of 17/10).

Yahoo quotes the London lines in pence, with the currency ``GBp``. The price schemas fold it to ``GBP`` and keep the
numbers, so pence are stored as pounds, and a holding is worth a hundred times too much until the user sets the asset's
quote base to 100 by hand. ``FAHistoricalData.currency`` keeps the code as the provider reported it; from this revision
``asset_provider_assignments.reported_currency`` keeps it too, for the data-quality report to warn. The contract pinned
here (§1 of that contract, with §2 for the model):

1. The revision: id ``010_provider_reported_currency`` (30 characters; ``alembic_version.version_num`` holds 32), in
   ``010_provider_reported_currency.py``, on top of ``009_email_unique_ignoring_case``; the chain keeps one head, which
   is not named.
2. A new database at head: ``reported_currency VARCHAR(8)``, nullable, no default, in no key, index or constraint; every
   other column, key and index of the table as at 009. A row written without it reads NULL; ``GBp`` reads ``GBp``.
3. The ``AssetProviderAssignment`` model declares the same column (§2): the service suites build their databases with
   ``create_all``, production with the migrations. The column is what is compared: on the rest of this table the two
   already differ before this lot (the migration's ``ON DELETE CASCADE`` on ``asset_id`` and ``identifier_type
   VARCHAR(20)``, the models' ``NO ACTION`` and ``VARCHAR(14)``), which 010 neither causes nor has to cure.
4. A populated install at 009 upgraded to 010 keeps every row of every table, ids included (each table read on the
   columns it had), and every other object of the schema; every assignment reads NULL in the new column; no
   foreign-key violation, integrity ok; taken on to head, the database is at head.
5. The downgrade to 009 of that install at 010, with values in the new column, drops the column and nothing else: the
   table declared as at 009 (columns, keys and their ``ON DELETE``, unique constraint, index), every other object of the
   schema as it was, every row of every table as it was — the events the providers generated
   (``asset_events.provider_assignment_id``) and the transactions linked to them above all —, no violation, integrity
   ok, at 009. It runs with foreign keys on, as production migrates: a rebuild of the table — Alembic's batch «move and
   copy», what ``batch_alter_table`` does on SQLite for a dropped column unless told ``recreate="never"`` — drops the
   old table, and SQLite deletes its rows first: ``ON DELETE CASCADE`` takes the provider's events with it, or
   ``transactions.asset_event_id`` (``ON DELETE RESTRICT``) stops the downgrade with ``FOREIGN KEY constraint failed``.
   Upgrading again gives the column back, NULL on every row: the values went with the downgrade.
6. Idempotent both ways: an upgrade that finds the column (a run that stopped after its ``ALTER``, the revision still
   009) keeps it, once, with its values; a downgrade that finds it gone (the revision still 010) goes through and changes
   nothing else.

Safety and fidelity: the harness of ``test_migration_005_accounts``, reused as it is, and ``_full_shape`` of
``test_migration_007_plugin_settings``. Every database is a file under ``tmp_path``; Alembic runs in this process on
that file alone — a connect listener refuses any other — with ``PRAGMA foreign_keys`` asserted 1 at every step, as
production migrates. Rows are written with plain SQL, the way a real install holds them. The populated install is the
1.2 one of 005 (the v1.1.0 install of ``test_post_migration`` taken to 004, converted by the post-migration fixes, plus
the rows only 1.2 writes), taken to 006 with the account tokens of 1.3, then to 009 by the real migrations, plus a London
line written at 009: Vodafone, its yfinance assignment, a dividend the provider generated and the DIVIDEND transaction
linked to it. The 1.1 rows bring the same shape (AAPL's provider dividend and its transaction): the fixture asserts both
are there, or «nothing cascades» would prove nothing.

Red until Z-32 (c): Alembic cannot locate 010 (each test that migrates to it fails saying so, never as an error of its
fixture), the head does not include it, the model has no ``reported_currency``. Each test says which.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from backend.app.db import post_migration
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.test_scripts.test_db.test_migration_005_accounts import (
    BOOKKEEPING,
    HEAD_ROWS,
    REV_004,
    ROWS_1_2,
    Declared,
    Rows,
    _connect,
    _copy,
    _foreign_keys_on,
    _integrity,
    _lineage,
    _migrate,
    _revision,
    _row_changes,
    _rows,
    _scripts,
    _table_info,
    _violations,
)
from backend.test_scripts.test_db.test_migration_007_plugin_settings import _full_shape
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_006 = "006_registration_mode"
REV_009 = "009_email_unique_ignoring_case"
REV_010 = "010_provider_reported_currency"
TABLE = "asset_provider_assignments"
COLUMN = "reported_currency"
#: What ``PRAGMA table_info`` must say of the new column (§1): ``VARCHAR(8)``, nullable, no default, not a key.
DECLARED = Declared("VARCHAR(8)", False, None, False)
#: The column as §1 declares it, added by hand: the state a run interrupted after its ``ALTER`` leaves.
ADD_COLUMN = f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} VARCHAR(8)"
DROP_COLUMN = f"ALTER TABLE {TABLE} DROP COLUMN {COLUMN}"
#: The entries of ``_full_shape`` that list the table's columns: the new one is taken out to compare with 009.
COLUMN_ENTRIES = ("columns (name: nullable)", "column types")
#: The entries of ``_full_shape`` that list keys, indexes and constraints: the new column must be in none of them.
KEY_ENTRIES = ("primary key", "foreign keys", "indexes (name, columns, unique)", "unique column sets", "unique constraints", "check constraints (name: sql)")
STAMP = "2026-10-01 09:00:00.000000"
FETCHED = "2026-10-16 22:00:00.000000"
LONDON_NAME = "Vodafone Group"
LONDON_TICKER = "VOD.L"

# A London line as a 1.3 server at 009 holds it: the asset, its yfinance assignment, a dividend the provider generated
# (``provider_assignment_id`` its assignment) and the DIVIDEND transaction linked to that event.
LONDON_LINE = f"""
PRAGMA foreign_keys = ON;
BEGIN;

INSERT INTO assets (display_name, currency, asset_type, quote_base_quantity, active, identifier_ticker, created_at, updated_at)
    VALUES ('{LONDON_NAME}', 'GBP', 'STOCK', 1, 1, '{LONDON_TICKER}', '{STAMP}', '{STAMP}');
INSERT INTO asset_provider_assignments (asset_id, provider_code, identifier, identifier_type, provider_params, last_fetch_at, created_at, updated_at)
    SELECT id, 'yfinance', '{LONDON_TICKER}', 'TICKER', NULL, '{FETCHED}', '{STAMP}', '{FETCHED}' FROM assets WHERE display_name = '{LONDON_NAME}';
INSERT INTO asset_events (asset_id, date, type, value, currency, provider_assignment_id, notes, created_at, updated_at)
    SELECT asset_id, '2026-06-18', 'DIVIDEND', 2.0, 'GBP', id, NULL, '{FETCHED}', '{FETCHED}' FROM asset_provider_assignments WHERE identifier = '{LONDON_TICKER}';
INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency, asset_event_id, created_at, updated_at)
    SELECT 1, e.asset_id, 'DIVIDEND', '2026-06-18', 0, 20.0, 'GBP', e.id, '{FETCHED}', '{FETCHED}'
      FROM asset_events e JOIN asset_provider_assignments a ON a.id = e.provider_assignment_id WHERE a.identifier = '{LONDON_TICKER}';

COMMIT;
"""

#: What a 1.3 server at 010 writes in the new column (§2, §4): the London line's pence, AAPL's dollars; the other
#: assignments never fetched since, NULL.
REPORTED_AT_010 = {LONDON_TICKER: "GBp", "AAPL": "USD"}


# =============================================================================
# HELPERS
# =============================================================================


def _missing_010() -> Optional[str]:
    """Why nothing can be migrated to 010 yet, or None when Alembic knows the revision."""
    scripts = _scripts()
    if REV_010 in {script.revision for script in scripts.walk_revisions()}:
        return None
    return f"red until Z-32 (c): Alembic cannot locate {REV_010}; the chain ends at {scripts.get_current_head()}"


def _require_010() -> None:
    """Barrier of the tests that migrate to 010 themselves: the test fails, saying why, rather than erroring in Alembic."""
    missing = _missing_010()
    if missing is not None:
        pytest.fail(missing, pytrace=False)


def _ran[ResultT](result: ResultT | str) -> ResultT:
    """The result of a fixture that migrates to 010, or the test fails with the reason the fixture could not."""
    if isinstance(result, str):
        pytest.fail(result, pytrace=False)
    return result


def _assert_includes_010(db: Path) -> None:
    """Barrier: ``db`` is at 010 or above; otherwise nothing that follows is about 010."""
    revision = _revision(db)
    assert REV_010 in _lineage(revision), f"red until Z-32 (c): {db.name} is at {revision}, which does not include {REV_010}"


def _schema(db: Path) -> list[tuple[Any, ...]]:
    """Every object of ``sqlite_master``: type, name, table and SQL, by type and name."""
    with _connect(db) as conn:
        return conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master ORDER BY type, name").fetchall()


def _beside_the_table(schema: list[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
    """The objects of ``schema`` that are neither the assignments table nor one of its indexes: those keep their SQL."""
    return [row for row in schema if row[2] != TABLE]


def _without_column(columns: dict[str, Declared]) -> dict[str, Declared]:
    return {name: declared for name, declared in columns.items() if name != COLUMN}


def _shape_without_column(shape: dict[str, Any]) -> dict[str, Any]:
    """``_full_shape`` of the table, the new column taken out of the entries that list columns."""
    return {key: ({name: value for name, value in entry.items() if name != COLUMN} if key in COLUMN_ENTRIES else entry) for key, entry in shape.items()}


def _keys_naming_the_column(shape: dict[str, Any]) -> dict[str, Any]:
    """The key, index and constraint entries of ``_full_shape`` that name the new column: none, by §1."""
    return {key: shape[key] for key in KEY_ENTRIES if COLUMN in repr(shape[key])}


def _assignment_values(db: Path) -> dict[int, Optional[str]]:
    """``{assignment id: reported_currency}`` of every assignment."""
    with _connect(db) as conn:
        return dict(conn.execute(f"SELECT id, {COLUMN} FROM {TABLE}").fetchall())


def _assignment_ids(rows: Rows) -> set[int]:
    columns, content = rows[TABLE]
    return {row[columns.index("id")] for row in content}


def _provider_events(db: Path) -> dict[int, int]:
    """``{event id: assignment id}`` of every event a provider assignment generated."""
    with _connect(db) as conn:
        return dict(conn.execute("SELECT id, provider_assignment_id FROM asset_events WHERE provider_assignment_id IS NOT NULL").fetchall())


def _linked_transactions(db: Path) -> dict[int, int]:
    """``{transaction id: event id}`` of every transaction linked to an event a provider generated."""
    with _connect(db) as conn:
        return dict(conn.execute("SELECT t.id, t.asset_event_id FROM transactions t JOIN asset_events e ON e.id = t.asset_event_id WHERE e.provider_assignment_id IS NOT NULL").fetchall())


def _write_reported_at_010(db: Path) -> None:
    """``REPORTED_AT_010`` in the new column, by identifier, in plain SQL."""
    with _foreign_keys_on(db) as conn:
        for identifier, code in REPORTED_AT_010.items():
            conn.execute(f"UPDATE {TABLE} SET {COLUMN} = ? WHERE identifier = ?", (code, identifier))
        conn.commit()


def _insert_asset(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute("INSERT INTO assets (display_name, currency, asset_type, active, created_at, updated_at) VALUES (?, 'GBP', 'STOCK', 1, ?, ?)", (name, STAMP, STAMP)).lastrowid


def _insert_assignment(conn: sqlite3.Connection, asset_id: int, identifier: str, **columns: Any) -> int:
    """An assignment with the NOT NULL columns filled in, and ``columns`` on top."""
    values = {"asset_id": asset_id, "provider_code": "yfinance", "identifier": identifier, "identifier_type": "TICKER", "created_at": STAMP, "updated_at": STAMP, **columns}
    return conn.execute(f"INSERT INTO {TABLE} ({', '.join(values)}) VALUES ({', '.join('?' for _ in values)})", tuple(values.values())).lastrowid


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def fresh_head(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("fresh-head") / "app.db"
    _migrate(db, "upgrade", "head")
    return db


@pytest.fixture(scope="module")
def fresh_009(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to 009: the table as it is before this lot. Read-only."""
    db = tmp_path_factory.mktemp("fresh-009") / "app.db"
    _migrate(db, "upgrade", REV_009)
    assert COLUMN not in _table_info(db, TABLE), "setup: at 009 the table has no reported_currency"
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
def install_at_009(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A populated install at 009 (see the module docstring). Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("install-009") / "sqlite" / "app.db"
    _install_v110(db)
    _migrate(db, "upgrade", REV_004)
    report = post_migration.run_post_migration_fixes(db, None)
    assert report.outcomes.get("autoincrement") == "applied", f"setup: the post-migration fixes did not convert the 1.1 rows: {report}"
    with _foreign_keys_on(db) as conn:
        conn.executescript(ROWS_1_2)
    _migrate(db, "upgrade", REV_006)
    with _foreign_keys_on(db) as conn:
        conn.executescript(HEAD_ROWS)
    _migrate(db, "upgrade", REV_009)
    with _foreign_keys_on(db) as conn:
        conn.executescript(LONDON_LINE)
    assert _revision(db) == REV_009, "setup: the install is at 009"
    assert COLUMN not in _table_info(db, TABLE), "setup: an install at 009 has no reported_currency"
    assert _violations(db) == [], "setup: the install's rows are consistent"
    events, linked = _provider_events(db), _linked_transactions(db)
    assert len(set(events.values())) >= 2 and len(linked) >= 2, f"setup: events of two assignments, each linked to a transaction, or «nothing cascades» proves nothing; events {events}, linked {linked}"
    with _connect(db) as conn:
        identifiers = {identifier for (identifier,) in conn.execute(f"SELECT identifier FROM {TABLE}")}
    assert identifiers >= set(REPORTED_AT_010), f"setup: the assignments the values are written on, among {sorted(map(str, identifiers))}"
    return db


@dataclass(frozen=True)
class Upgrade:
    """A copy of the install at 009: its schema and rows before ``upgrade 010`` and right after; then taken on to head."""

    db: Path
    rows_before: Rows
    schema_before: list[tuple[Any, ...]]
    table_before: dict[str, Declared]
    shape_before: dict[str, Any]
    rows_after: Rows
    schema_after: list[tuple[Any, ...]]
    table_after: dict[str, Declared]
    shape_after: dict[str, Any]
    values_after: dict[int, Optional[str]]
    violations: list[tuple[Any, ...]]
    integrity: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def upgraded(install_at_009: Path, tmp_path_factory: pytest.TempPathFactory) -> Upgrade | str:
    """The upgrade of the install to 010, or, while Alembic knows no 010, the reason: each test fails on it."""
    missing = _missing_010()
    if missing is not None:
        return missing
    db = _copy(install_at_009, tmp_path_factory.mktemp("upgraded") / "app.db")
    rows_before, schema_before, table_before, shape_before = _rows(db), _schema(db), _table_info(db, TABLE), _full_shape(db, TABLE)
    _migrate(db, "upgrade", REV_010)
    upgrade = Upgrade(
        db=db,
        rows_before=rows_before,
        schema_before=schema_before,
        table_before=table_before,
        shape_before=shape_before,
        rows_after=_rows(db),
        schema_after=_schema(db),
        table_after=_table_info(db, TABLE),
        shape_after=_full_shape(db, TABLE),
        values_after=_assignment_values(db),
        violations=_violations(db),
        integrity=_integrity(db),
    )
    _migrate(db, "upgrade", "head")
    return upgrade


@dataclass(frozen=True)
class RoundTrip:
    """A copy of the install taken to 010, given values in the new column, downgraded to 009, then upgraded to 010 again.

    ``downgrade_error`` is what the downgrade raised, None when it went through; the reads after it are of the database
    as the downgrade left it. ``*_again`` are None when the downgrade failed: nothing was upgraded again.
    """

    db: Path
    rows_at_010: Rows
    schema_at_010: list[tuple[Any, ...]]
    table_at_010: dict[str, Declared]
    shape_at_010: dict[str, Any]
    events_at_010: dict[int, int]
    linked_at_010: dict[int, int]
    downgrade_error: Optional[str]
    revision_down: str
    table_down: dict[str, Declared]
    shape_down: Optional[dict[str, Any]]
    schema_down: list[tuple[Any, ...]]
    rows_down: Rows
    events_down: dict[int, int]
    linked_down: dict[int, int]
    violations_down: list[tuple[Any, ...]]
    integrity_down: list[tuple[Any, ...]]
    revision_again: Optional[str]
    table_again: Optional[dict[str, Declared]]
    shape_again: Optional[dict[str, Any]]
    values_again: Optional[dict[int, Optional[str]]]
    rows_again: Optional[Rows]


@pytest.fixture(scope="module")
def round_trip(install_at_009: Path, tmp_path_factory: pytest.TempPathFactory) -> RoundTrip | str:
    """The round trip of the module docstring (5), or, while Alembic knows no 010, the reason: each test fails on it."""
    missing = _missing_010()
    if missing is not None:
        return missing
    db = _copy(install_at_009, tmp_path_factory.mktemp("round-trip") / "app.db")
    _migrate(db, "upgrade", REV_010)
    _write_reported_at_010(db)
    values = _assignment_values(db)
    assert sorted(code for code in values.values() if code is not None) == sorted(REPORTED_AT_010.values()), f"barrier: the values are written before the downgrade: {values}"
    rows_at_010, schema_at_010, table_at_010, shape_at_010 = _rows(db), _schema(db), _table_info(db, TABLE), _full_shape(db, TABLE)
    events_at_010, linked_at_010 = _provider_events(db), _linked_transactions(db)

    downgrade_error: Optional[str] = None
    try:
        _migrate(db, "downgrade", REV_009)
    except AssertionError:
        raise  # the harness's own setup checks: never a verdict on the migration
    except Exception as error:  # what the downgrade raises is the finding: its tests report it
        if isinstance(error, RuntimeError) and str(error).startswith("safety:"):
            raise
        downgrade_error = f"{type(error).__name__}: {error}"

    again: dict[str, Any] = dict.fromkeys(("revision_again", "table_again", "shape_again", "values_again", "rows_again"))
    trip = {
        "revision_down": _revision(db),
        "table_down": _table_info(db, TABLE),
        "shape_down": _full_shape(db, TABLE),
        "schema_down": _schema(db),
        "rows_down": _rows(db),
        "events_down": _provider_events(db),
        "linked_down": _linked_transactions(db),
        "violations_down": _violations(db),
        "integrity_down": _integrity(db),
    }
    if downgrade_error is None:
        _migrate(db, "upgrade", REV_010)
        again = {"revision_again": _revision(db), "table_again": _table_info(db, TABLE), "shape_again": _full_shape(db, TABLE), "values_again": _assignment_values(db), "rows_again": _rows(db)}
    return RoundTrip(
        db=db,
        rows_at_010=rows_at_010,
        schema_at_010=schema_at_010,
        table_at_010=table_at_010,
        shape_at_010=shape_at_010,
        events_at_010=events_at_010,
        linked_at_010=linked_at_010,
        downgrade_error=downgrade_error,
        **trip,
        **again,
    )


def _went_down(trip: RoundTrip) -> None:
    """Barrier of the tests that read the database after the downgrade: it went through."""
    assert trip.downgrade_error is None, f"barrier: the downgrade to {REV_009} failed, so what follows would read a database it left half way: {trip.downgrade_error}"


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_revision_010_sits_on_009_and_the_chain_keeps_one_head() -> None:
    """MIG010-001 — §1, red until Z-32 (c) (Alembic knows no 010): ``010_provider_reported_currency`` exists, in ``010_provider_reported_currency.py``, fits ``version_num``, and revises ``009_email_unique_ignoring_case``; one head, not named."""
    print_section(f"MIG010-001: revision {REV_010}")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_010 in revisions, f"red until Z-32 (c): revision {REV_010} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_010]
    assert len(script.revision) <= 32, f"{script.revision!r} is {len(script.revision)} characters: alembic_version.version_num is VARCHAR(32)"
    assert script.down_revision == REV_009, f"{REV_010} must revise {REV_009}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_010}.py", f"the revision id is the file name without .py, found in {Path(script.path).name}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_010} revises {REV_009}; one head ({heads[0]})")


# =============================================================================
# 2. A NEW DATABASE AT HEAD
# =============================================================================


def test_a_new_database_at_head_has_the_column_and_the_rest_of_the_table_as_at_009(fresh_head: Path, fresh_009: Path) -> None:
    """MIG010-002 — §1, red until Z-32 (c) (the head does not include 010): ``reported_currency`` is ``VARCHAR(8)``, nullable, without a default, not the key; every other column as at 009, and the keys and their ``ON DELETE``, the unique constraint and the index as at 009, so the new column is in none of them."""
    print_section(f"MIG010-002: {TABLE}.{COLUMN} on a new database at head")
    _assert_includes_010(fresh_head)
    columns = _table_info(fresh_head, TABLE)

    assert columns.get(COLUMN) == DECLARED, f"{TABLE}.{COLUMN} must be {DECLARED}, is {columns.get(COLUMN)}"
    assert _without_column(columns) == _table_info(fresh_009, TABLE), "every other column must be declared as at 009"
    shape = _full_shape(fresh_head, TABLE)
    assert _keys_naming_the_column(shape) == {}, f"{COLUMN} must be in no key, index or constraint: {_keys_naming_the_column(shape)}"
    assert _shape_without_column(shape) == _full_shape(fresh_009, TABLE), "the keys, ON DELETE, unique constraint and index must be as at 009"
    print_success(f"{COLUMN} VARCHAR(8) NULL, nothing else changed")


def test_a_row_written_without_the_column_reads_null_and_a_code_reads_as_written(fresh_head: Path, tmp_path: Path) -> None:
    """MIG010-003 — §1 and §2, red until Z-32 (c) (the head does not include 010): with foreign keys on, an assignment written without the column reads NULL (no default), one written with ``GBp`` reads ``GBp``, its case kept."""
    db = _copy(fresh_head, tmp_path / "app.db")
    _assert_includes_010(db)

    with _foreign_keys_on(db) as conn:
        never_fetched = _insert_assignment(conn, _insert_asset(conn, "never fetched"), "NEVER.L")
        in_pence = _insert_assignment(conn, _insert_asset(conn, "in pence"), "PENCE.L", **{COLUMN: "GBp"})
        conn.commit()

    assert _assignment_values(db) == {never_fetched: None, in_pence: "GBp"}


# =============================================================================
# 3. THE MODEL AND THE MIGRATION AGREE ON THE COLUMN
# =============================================================================


def test_the_model_declares_the_column_the_migration_adds(fresh_head: Path, created_by_models: Path) -> None:
    """MIG010-004 — §2, red until Z-32 (c) (the model declares no ``reported_currency``; then the head does not include 010): ``create_all`` and ``alembic upgrade head`` declare ``reported_currency`` alike — ``VARCHAR(8)``, nullable, no default, in no key, index or constraint — and give the table the same columns. The rest of the table is not compared (see the module docstring: a drift older than this lot)."""
    print_section(f"MIG010-004: {COLUMN}, migration = model")
    modelled = _table_info(created_by_models, TABLE)
    assert COLUMN in modelled, f"red until Z-32 (c): the AssetProviderAssignment model declares no {COLUMN}; create_all builds {sorted(modelled)}"
    _assert_includes_010(fresh_head)
    migrated = _table_info(fresh_head, TABLE)

    assert (migrated.get(COLUMN), modelled.get(COLUMN)) == (DECLARED, DECLARED), f"migration {migrated.get(COLUMN)}, model {modelled.get(COLUMN)}: both must be {DECLARED}"
    assert set(migrated) == set(modelled), f"the migration and the model must give the table the same columns: only in the migration {sorted(set(migrated) - set(modelled))}, only in the model {sorted(set(modelled) - set(migrated))}"
    assert _keys_naming_the_column(_full_shape(created_by_models, TABLE)) == {}, "the model must put the column in no key, index or constraint"
    print_success(f"{COLUMN}: the same declaration both ways")


# =============================================================================
# 4. A POPULATED INSTALL UPGRADED
# =============================================================================


def test_a_populated_install_keeps_every_row_of_every_table(upgraded: Upgrade | str) -> None:
    """MIG010-005 — §1, red until Z-32 (c) (Alembic cannot locate 010): every table of the install at 009, ids included and ``sqlite_sequence`` too, read on the columns it had at 009: as it was; no table added or dropped."""
    print_section("MIG010-005: the install at 009, upgraded")
    up = _ran(upgraded)

    assert set(up.rows_after) == set(up.rows_before), f"the upgrade must add or drop no table: added {sorted(set(up.rows_after) - set(up.rows_before))}, dropped {sorted(set(up.rows_before) - set(up.rows_after))}"
    changes = _row_changes(up.rows_before, up.rows_after, set(up.rows_before) - BOOKKEEPING, columns_of=up.rows_before)
    assert not changes, f"the upgrade changed rows: {changes}"
    print_success(f"{len(set(up.rows_before) - BOOKKEEPING)} tables, every row as it was")


def test_every_existing_assignment_reads_null_in_the_new_column(upgraded: Upgrade | str) -> None:
    """MIG010-006 — §1, red until Z-32 (c) (Alembic cannot locate 010): after the upgrade the column is declared as on a new database, and every assignment of the install reads NULL there: nothing is backfilled, the next fetch writes it (§4)."""
    up = _ran(upgraded)

    assert up.table_after.get(COLUMN) == DECLARED, f"{TABLE}.{COLUMN} must be {DECLARED}, is {up.table_after.get(COLUMN)}"
    assert _without_column(up.table_after) == up.table_before, "every other column must be declared as at 009"
    assert up.values_after == dict.fromkeys(_assignment_ids(up.rows_before), None), f"every existing assignment must read NULL: {up.values_after}"


def test_the_upgrade_leaves_every_other_object_and_no_violation(upgraded: Upgrade | str) -> None:
    """MIG010-007 — §1, red until Z-32 (c) (Alembic cannot locate 010): every object of the schema but the table and its indexes keeps its SQL; the table keeps its keys, ``ON DELETE``, unique constraint and index; ``PRAGMA foreign_key_check`` is empty, ``integrity_check`` ok."""
    up = _ran(upgraded)

    assert _beside_the_table(up.schema_after) == _beside_the_table(up.schema_before), "the upgrade must touch no other object of the schema"
    assert _shape_without_column(up.shape_after) == up.shape_before, "the table must keep its keys, ON DELETE, unique constraint and index"
    assert (up.violations, up.integrity) == ([], [("ok",)])


def test_a_populated_install_reaches_the_head(upgraded: Upgrade | str) -> None:
    """MIG010-008 — red until Z-32 (c) (Alembic cannot locate 010): taken on to head, the install is at the head of the chain, whichever revision that is."""
    up = _ran(upgraded)

    _assert_includes_010(up.db)
    assert _revision(up.db) == _scripts().get_current_head()


# =============================================================================
# 5. THE DOWNGRADE, AND BACK
# =============================================================================


def test_the_downgrade_goes_through_with_foreign_keys_on_and_drops_the_column_only(round_trip: RoundTrip | str, install_at_009: Path) -> None:
    """MIG010-009 — §1, red until Z-32 (c) (Alembic cannot locate 010): the downgrade to 009 of the install at 010, with ``GBp`` and ``USD`` in the new column, goes through with foreign keys on (``FOREIGN KEY constraint failed`` is what a rebuild of the table raises here), and leaves the table declared exactly as at 009: its columns, its keys and their ``ON DELETE``, its unique constraint and its index."""
    print_section("MIG010-009: the downgrade drops the column only")
    trip = _ran(round_trip)

    assert trip.downgrade_error is None, f"the downgrade to {REV_009} must go through with foreign keys on, as production migrates: {trip.downgrade_error}"
    assert trip.revision_down == REV_009, f"the downgrade must leave the database at {REV_009}: {trip.revision_down}"
    assert COLUMN not in trip.table_down, f"the downgrade must drop {COLUMN}"
    assert trip.table_down == _table_info(install_at_009, TABLE), "the table must be declared exactly as at 009"
    assert trip.shape_down == _full_shape(install_at_009, TABLE), "the table must keep the keys, ON DELETE, unique constraint and index it had at 009"
    print_success(f"at {REV_009}; {COLUMN} dropped, the table as at 009")


def test_the_downgrade_keeps_every_row_the_provider_events_and_their_transactions(round_trip: RoundTrip | str) -> None:
    """MIG010-010 — §1, red until Z-32 (c) (Alembic cannot locate 010): after the downgrade every table is there, every row as at 010 read on the columns the table keeps — the events the providers generated and the transactions linked to them above all, which a rebuild of the table deletes with its rows —; every other object of the schema keeps its SQL; no violation, integrity ok."""
    print_section("MIG010-010: the downgrade touches no other row")
    trip = _ran(round_trip)
    _went_down(trip)

    assert trip.events_down == trip.events_at_010, f"the events the providers generated must survive the downgrade: at 010 {trip.events_at_010}, after {trip.events_down}"
    assert trip.linked_down == trip.linked_at_010, f"the transactions linked to them must keep their link: at 010 {trip.linked_at_010}, after {trip.linked_down}"
    assert set(trip.rows_down) == set(trip.rows_at_010), f"the downgrade must add or drop no table: added {sorted(set(trip.rows_down) - set(trip.rows_at_010))}, dropped {sorted(set(trip.rows_at_010) - set(trip.rows_down))}"
    changes = _row_changes(trip.rows_at_010, trip.rows_down, set(trip.rows_down) - BOOKKEEPING, columns_of=trip.rows_down)
    assert not changes, f"the downgrade changed rows it had no reason to touch: {changes}"
    assert _beside_the_table(trip.schema_down) == _beside_the_table(trip.schema_at_010), "the downgrade must touch no other object of the schema"
    assert (trip.violations_down, trip.integrity_down) == ([], [("ok",)])
    print_success(f"{len(set(trip.rows_down) - BOOKKEEPING)} tables, every row as it was at 010")


def test_upgrading_again_brings_the_column_back_null(round_trip: RoundTrip | str) -> None:
    """MIG010-011 — §1, red until Z-32 (c) (Alembic cannot locate 010): ``upgrade 010`` after the downgrade gives the table it had at 010 — the column declared the same, the keys and the index the same — with NULL on every assignment (``GBp`` and ``USD`` went with the downgrade), every other row as after the downgrade."""
    trip = _ran(round_trip)
    _went_down(trip)

    assert trip.revision_again == REV_010
    assert (trip.table_again, trip.shape_again) == (trip.table_at_010, trip.shape_at_010), "upgrading again must give the table it had at 010"
    assert trip.values_again == dict.fromkeys(_assignment_ids(trip.rows_down), None), f"upgrading again must give NULL on every assignment: {trip.values_again}"
    changes = _row_changes(trip.rows_down, trip.rows_again, set(trip.rows_down) - BOOKKEEPING, columns_of=trip.rows_down)
    assert not changes, f"upgrading again changed rows: {changes}"


# =============================================================================
# 6. IDEMPOTENT BOTH WAYS
# =============================================================================


def test_an_upgrade_that_finds_the_column_keeps_it_with_its_values(install_at_009: Path, tmp_path: Path) -> None:
    """MIG010-012 — §1, red until Z-32 (c) (Alembic cannot locate 010): the install at 009 with the column already added as §1 declares it and ``GBp`` on the London line — a run interrupted after its ``ALTER``, the revision still 009 —: ``upgrade 010`` goes through, the column declared once as §1 says, ``GBp`` kept, every other assignment NULL, every row of every table as before."""
    print_section("MIG010-012: an upgrade that finds the column")
    _require_010()
    db = _copy(install_at_009, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        conn.execute(ADD_COLUMN)
        conn.execute(f"UPDATE {TABLE} SET {COLUMN} = 'GBp' WHERE identifier = ?", (LONDON_TICKER,))
        conn.commit()
    assert _revision(db) == REV_009 and _table_info(db, TABLE).get(COLUMN) == DECLARED, "setup: the interrupted state"
    rows_before, values_before = _rows(db), _assignment_values(db)

    _migrate(db, "upgrade", REV_010)

    assert _revision(db) == REV_010
    assert _table_info(db, TABLE).get(COLUMN) == DECLARED and _without_column(_table_info(db, TABLE)) == _table_info(install_at_009, TABLE), "the column must be there once, as §1 declares it, beside the columns of 009"
    assert _assignment_values(db) == values_before, f"the values the column held must be kept: before {values_before}, after {_assignment_values(db)}"
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=rows_before)
    assert not changes, f"the upgrade over its own column changed rows: {changes}"
    print_success("the column found, kept with its values")


def test_a_downgrade_that_finds_the_column_gone_changes_nothing_else(install_at_009: Path, tmp_path: Path) -> None:
    """MIG010-013 — §1, red until Z-32 (c) (Alembic cannot locate 010): the install at 010 whose column was already dropped — a downgrade interrupted after its ``ALTER``, the revision still 010 —: ``downgrade 009`` goes through, at 009, and changes no object of the schema and no row of any table."""
    print_section("MIG010-013: a downgrade that finds the column gone")
    _require_010()
    db = _copy(install_at_009, tmp_path / "app.db")
    _migrate(db, "upgrade", REV_010)
    _write_reported_at_010(db)
    with _foreign_keys_on(db) as conn:
        conn.execute(DROP_COLUMN)
        conn.commit()
    assert _revision(db) == REV_010 and COLUMN not in _table_info(db, TABLE), "setup: the interrupted state"
    rows_before, schema_before = _rows(db), _schema(db)

    _migrate(db, "downgrade", REV_009)

    assert _revision(db) == REV_009
    assert _schema(db) == schema_before, "a downgrade that finds the column gone must change no object of the schema"
    changes = _row_changes(rows_before, _rows(db), set(rows_before) - BOOKKEEPING, columns_of=rows_before)
    assert not changes, f"a downgrade that finds the column gone changed rows: {changes}"
    print_success("nothing to drop, nothing changed")
