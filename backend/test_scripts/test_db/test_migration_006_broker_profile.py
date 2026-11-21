"""The broker's operating profile column of ``006_release_1_4_0_schema`` (P1 of project 67, tests 12–16).

Subject. Release 1.4's migration adds ``brokers.operating_profile``, a nullable ``TEXT`` holding the profile's JSON (decision
D1 (a)): ``ALTER TABLE brokers ADD COLUMN operating_profile TEXT DEFAULT NULL`` when the column is missing, ``DROP COLUMN``
on the way back when it is there. Every broker row of a 1.3 database survives, with the column ``NULL``.

How. Each test owns its databases under ``tmp_path`` (``alembic_harness``: Alembic in this process, on that file alone,
with foreign keys on as production migrates). A 1.3 database is built by upgrading to ``005_release_1_3_0_schema`` **by
name**, so another workstream's step in the same 006 does not move these tests' starting point. Rows are written and read
with plain ``sqlite3``, the way a real install is read. The comparison with the models is ``_full_shape`` of the harness,
as the 005 tests compare their tables: names, nullability, declared types, keys, constraints; not the column order.
"""

from __future__ import annotations

from pathlib import Path

from backend.test_scripts.test_db.alembic_harness import _connect, _create_all, _full_shape, _migrate, _revision, _scripts, _table_info
from backend.test_scripts.test_utils import print_success

REV_005 = "005_release_1_3_0_schema"
REV_006 = "006_release_1_4_0_schema"
COLUMN = "operating_profile"

#: Two brokers as a 1.3 install holds them, every column written.
BROKER_ROWS = [
    (1, "Broker one", "first", "https://one.example", None, None, 0, 0, 1, "2024-01-02", "2026-01-01 10:00:00", "2026-01-01 10:00:00"),
    (2, "Broker two", None, None, "https://two.example/icon.png", "broker_generic_csv", 1, 1, 0, None, "2026-02-01 10:00:00", "2026-02-03 11:00:00"),
]
BROKER_COLUMNS = "id, name, description, portal_url, icon_url, default_import_plugin, allow_cash_overdraft, allow_asset_shorting, is_active, opened_at, created_at, updated_at"


def _database_at_1_3(tmp_path: Path, name: str = "app.db") -> Path:
    db = tmp_path / name
    _migrate(db, "upgrade", REV_005)
    assert _revision(db) == REV_005, f"setup: the new database is at {_revision(db)}, not at {REV_005}"
    assert COLUMN not in _table_info(db, "brokers"), "setup: a 1.3 database has no operating profile column"
    with _connect(db) as conn:
        conn.executemany(f"INSERT INTO brokers ({BROKER_COLUMNS}) VALUES ({', '.join('?' * 12)})", BROKER_ROWS)
        conn.commit()
    return db


def _broker_rows(db: Path, columns: str = BROKER_COLUMNS) -> list[tuple]:
    with _connect(db) as conn:
        return conn.execute(f"SELECT {columns} FROM brokers ORDER BY id").fetchall()


def test_a_1_3_database_gets_the_column_and_keeps_every_broker_row(tmp_path):
    db = _database_at_1_3(tmp_path)

    _migrate(db, "upgrade", "head")

    declared = _table_info(db, "brokers")[COLUMN]
    assert (declared.type, declared.not_null, declared.primary_key) == ("TEXT", False, False), f"TEXT, nullable: {declared}"
    assert list(_table_info(db, "brokers"))[-1] == COLUMN, "a plain ADD COLUMN puts the column last"
    assert _broker_rows(db) == BROKER_ROWS, "every broker row is kept as it was"
    assert _broker_rows(db, COLUMN) == [(None,), (None,)], "every existing broker has no profile"
    print_success("1.3 → head: brokers.operating_profile TEXT NULL, rows kept")


def test_the_upgrade_run_again_changes_nothing(tmp_path):
    db = _database_at_1_3(tmp_path)
    _migrate(db, "upgrade", "head")
    shape, rows = _full_shape(db, "brokers"), _broker_rows(db, f"{BROKER_COLUMNS}, {COLUMN}")

    # The step run again on its own work: the stamp back to 1.3, the column already there.
    with _connect(db) as conn:
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_005,))
        conn.commit()
    _migrate(db, "upgrade", "head")

    assert (_full_shape(db, "brokers"), _broker_rows(db, f"{BROKER_COLUMNS}, {COLUMN}")) == (shape, rows)
    print_success("the upgrade run again changes nothing")


def test_an_upgrade_that_finds_the_column_completes(tmp_path):
    db = _database_at_1_3(tmp_path)
    with _connect(db) as conn:
        conn.execute(f"ALTER TABLE brokers ADD COLUMN {COLUMN} TEXT DEFAULT NULL")
        conn.commit()

    _migrate(db, "upgrade", "head")

    assert _revision(db) != REV_005 and COLUMN in _table_info(db, "brokers")
    assert _broker_rows(db) == BROKER_ROWS
    print_success("a column already there: the upgrade reaches the head")


def test_the_downgrade_drops_the_column_and_keeps_the_rows(tmp_path):
    db = _database_at_1_3(tmp_path)
    _migrate(db, "upgrade", "head")
    with _connect(db) as conn:
        conn.execute(f"UPDATE brokers SET {COLUMN} = ? WHERE id = 1", ('{"profile_version":1}',))
        conn.commit()

    _migrate(db, "downgrade", REV_005)

    assert COLUMN not in _table_info(db, "brokers")
    assert _broker_rows(db) == BROKER_ROWS

    # Run again from a database stamped at the head without the column: nothing to drop, nothing fails.
    with _connect(db) as conn:
        conn.execute("UPDATE alembic_version SET version_num = ?", (REV_006,))
        conn.commit()
    _migrate(db, "downgrade", REV_005)
    assert COLUMN not in _table_info(db, "brokers") and _broker_rows(db) == BROKER_ROWS
    print_success("downgrade: the column goes, the rows stay; run again, nothing happens")


def test_the_models_and_the_migration_build_the_same_brokers_table(tmp_path):
    migrated = tmp_path / "migrated.db"
    _migrate(migrated, "upgrade", "head")
    built = _create_all(tmp_path / "models.db")

    assert COLUMN in _table_info(built, "brokers"), "the model declares the column"
    assert _full_shape(built, "brokers") == _full_shape(migrated, "brokers")
    print_success("create_all and upgrade head build the same brokers table")


def test_the_column_is_the_releases_own():
    """The column belongs to 1.4's one migration: the revision that adds it is the release's, a child of 1.3's."""
    script = _scripts().get_revision(REV_006)
    assert script.down_revision == REV_005
    assert COLUMN in Path(script.path).read_text(encoding="utf-8")
