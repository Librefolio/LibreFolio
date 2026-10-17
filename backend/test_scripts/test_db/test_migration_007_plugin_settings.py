"""Migration ``007_plugin_settings``: the instance's and each user's plugin settings (plan 03, CP10 step 2).

Two new tables, empty after the upgrade: ``plugin_system_settings`` (one value per field for the whole instance) and
``plugin_user_settings`` (one value per field and user). The contract pinned here:

1. The revision: id ``007_plugin_settings`` (19 characters; ``alembic_version.version_num`` holds 32), in
   ``007_plugin_settings.py``, on top of ``006_registration_mode``; the chain keeps exactly one head.
2. A new database at head: both tables with their columns, declared types and nullability; ``user_id`` points at
   ``users`` with ``ON DELETE CASCADE``, ``updated_by_user_id`` with ``ON DELETE SET NULL``; the named unique constraints
   on the field (and the user); the two named CHECKs of each table. With foreign keys on, as production runs: a row holds
   exactly one of ``value_json`` and ``secret_ciphertext``, and ``key_id`` exactly when it holds a ciphertext; a field
   twice is refused, the same field for two users or two families is not; a user row for no user is refused; deleting a
   user deletes that user's rows and unlinks the system rows the user wrote, and nothing else.
3. Models and migration build the same two tables (columns, types, nullability, primary key, foreign keys with their
   ON DELETE, unique constraints with their names, CHECKs with their names and text): the service suites build their
   databases with ``create_all``, and production with the migrations.
4. A populated install at 006 upgraded keeps every row of every table, ids included; the two tables are empty; no
   foreign-key violation, integrity ok; taken on to head, it is at head.
5. The downgrade to 006 of a database holding settings — plain values and secrets, of the instance and of users — drops
   both tables (their values are lost, as the migration says) and touches no other row; no violation; at 006.
   Upgrading again gives the two tables empty, with the schema of a new database.
6. Idempotent both ways: an upgrade that finds one of the tables (a run that stopped half way) creates the other and
   keeps the one it found, rows included; a downgrade that finds one already dropped drops the other.

Safety and fidelity: the harness of ``test_migration_005_accounts``, reused as it is. Every database is a file under
``tmp_path``; Alembic runs in this process on that file alone — a connect listener refuses any other — with
``PRAGMA foreign_keys`` asserted 1 at every step, as production migrates. Rows are written with plain SQL, the way a real
install holds them. The populated install is the 1.2 one of 005 (the v1.1.0 schema and rows, taken to 004, converted by
the post-migration fixes, plus the rows only 1.2 writes), taken to 006 by the real migrations, with the account tokens
of 1.3 on top: every table that points at users has rows that do.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import NullPool

from backend.app.db import post_migration
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.test_scripts.test_db.test_migration_005_accounts import (
    HEAD_ROWS,
    REV_004,
    ROWS_1_2,
    Declared,
    Rows,
    _connect,
    _copy,
    _foreign_keys,
    _foreign_keys_on,
    _insert_user,
    _integrity,
    _lineage,
    _migrate,
    _revision,
    _rows,
    _scripts,
    _shape,
    _table_info,
    _tables,
    _violations,
)
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_006 = "006_registration_mode"
REV_007 = "007_plugin_settings"
SYSTEM_TABLE, USER_TABLE = "plugin_system_settings", "plugin_user_settings"
PLUGIN_TABLES = (SYSTEM_TABLE, USER_TABLE)
# Alembic's own bookkeeping: its row is expected to change.
BOOKKEEPING = frozenset({"alembic_version"})
STAMP = "2026-10-15 12:00:00.000000"
KEY_ID = "0123456789abcdef0123456789abcdef"
BLOB = b"\x01" + bytes(range(12)) + b"ciphertext-and-tag-of-test"

#: What PRAGMA table_info says of each column: (declared type, NOT NULL, default, primary key).
SYSTEM_COLUMNS = {
    "id": Declared("INTEGER", True, None, True),
    "family": Declared("VARCHAR(16)", True, None, False),
    "plugin_code": Declared("VARCHAR(64)", True, None, False),
    "field_key": Declared("VARCHAR(64)", True, None, False),
    "value_json": Declared("TEXT", False, None, False),
    "secret_ciphertext": Declared("BLOB", False, None, False),
    "key_id": Declared("VARCHAR(32)", False, None, False),
    "updated_at": Declared("DATETIME", True, None, False),
    "updated_by_user_id": Declared("INTEGER", False, None, False),
}
USER_COLUMNS = {key: value for key, value in SYSTEM_COLUMNS.items() if key != "updated_by_user_id"} | {"user_id": Declared("INTEGER", True, None, False)}
UNIQUE = {
    SYSTEM_TABLE: ("uq_plugin_system_settings_field", ("family", "plugin_code", "field_key")),
    USER_TABLE: ("uq_plugin_user_settings_field", ("user_id", "family", "plugin_code", "field_key")),
}
CHECKS = {table: {f"ck_{table}_one_value", f"ck_{table}_key_id"} for table in PLUGIN_TABLES}


# =============================================================================
# HELPERS
# =============================================================================


def _assert_includes_007(db: Path) -> None:
    """Barrier: ``db`` is at 007 or above; otherwise nothing that follows is about 007."""
    revision = _revision(db)
    assert REV_007 in _lineage(revision), f"barrier: {db.name} is at {revision}, which does not include {REV_007}"


def _insert_system(conn: sqlite3.Connection, key: str, *, family: str = "asset", code: str = "lab", value_json: str | None = '"us"', ciphertext: bytes | None = None, key_id: str | None = None, author: int | None = None) -> int:
    return conn.execute(
        f"INSERT INTO {SYSTEM_TABLE} (family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at, updated_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (family, code, key, value_json, ciphertext, key_id, STAMP, author),
    ).lastrowid


def _insert_user_row(conn: sqlite3.Connection, user_id: int, key: str, *, family: str = "asset", code: str = "lab", value_json: str | None = "7", ciphertext: bytes | None = None, key_id: str | None = None) -> int:
    return conn.execute(
        f"INSERT INTO {USER_TABLE} (user_id, family, plugin_code, field_key, value_json, secret_ciphertext, key_id, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, family, code, key, value_json, ciphertext, key_id, STAMP),
    ).lastrowid


def _insert_into(conn: sqlite3.Connection, table: str, user_id: int, key: str, **columns: Any) -> int:
    if table == SYSTEM_TABLE:
        return _insert_system(conn, key, **columns)
    return _insert_user_row(conn, user_id, key, **columns)


def _without(rows: Rows, tables: set[str] | frozenset[str]) -> Rows:
    excluded = set(tables)
    return {table: content for table, content in rows.items() if table not in excluded}


def _differences(expected: Rows, actual: Rows) -> dict[str, Any]:
    """The tables whose columns or rows differ, with a sample of what is missing and what is new."""
    differences: dict[str, Any] = {}
    for table in sorted(set(expected) | set(actual)):
        if table not in actual or table not in expected:
            differences[table] = "the table is only on one side"
        elif expected[table] != actual[table]:
            wanted, found = expected[table][1], actual[table][1]
            differences[table] = {"columns": (expected[table][0], actual[table][0]), "missing or changed": [row for row in wanted if row not in found][:2], "unexpected": [row for row in found if row not in wanted][:2]}
    return differences


def _create_sql(db: Path, table: str) -> str:
    with _connect(db) as conn:
        return conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()[0]


def _normalized(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def _full_shape(db: Path, table: str) -> dict[str, Any] | None:
    """``_shape`` of the 005 harness, plus what it does not compare: declared types, unique constraint names, CHECK texts."""
    shape = _shape(db, table)
    if shape is None:
        return None
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        inspector = inspect(engine)
        shape["column types"] = {column["name"]: str(column["type"]) for column in inspector.get_columns(table)}
        shape["unique constraints"] = sorted((constraint["name"], tuple(constraint["column_names"])) for constraint in inspector.get_unique_constraints(table))
        shape["check constraints (name: sql)"] = sorted((check["name"], _normalized(check["sqltext"])) for check in inspector.get_check_constraints(table))
    finally:
        engine.dispose()
    return shape


@contextmanager
def _refused(conn: sqlite3.Connection, *fragments: str) -> Iterator[None]:
    """The statement in the block must fail with an integrity error naming every fragment; the transaction is rolled back."""
    with pytest.raises(sqlite3.IntegrityError) as refused:
        yield
    conn.rollback()
    assert all(fragment in str(refused.value) for fragment in fragments), f"refused for another reason: {refused.value}"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture(scope="module")
def fresh_head(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to head by the real migrations. Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("fresh-head") / "app.db"
    _migrate(db, "upgrade", "head")
    _assert_includes_007(db)
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
def install_at_006(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A populated install at 006 (see the module docstring). Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("install-006") / "sqlite" / "app.db"
    _install_v110(db)
    _migrate(db, "upgrade", REV_004)
    report = post_migration.run_post_migration_fixes(db, None)
    assert report.outcomes.get("autoincrement") == "applied", f"setup: the post-migration fixes did not convert the 1.1 rows: {report}"
    with _foreign_keys_on(db) as conn:
        conn.executescript(ROWS_1_2)
    _migrate(db, "upgrade", REV_006)
    with _foreign_keys_on(db) as conn:
        conn.executescript(HEAD_ROWS)
    assert _revision(db) == REV_006, "setup: the install is at 006"
    assert not set(PLUGIN_TABLES) & _tables(db), "setup: an install at 006 has no plugin settings table"
    assert _violations(db) == [], "setup: the install's rows are consistent"
    return db


def _users(db: Path) -> dict[str, int]:
    with _connect(db) as conn:
        return dict(conn.execute("SELECT username, id FROM users").fetchall())


@dataclass(frozen=True)
class Upgrade:
    """A copy of the install at 006: its rows before ``upgrade 007`` and right after; then taken on to head."""

    db: Path
    rows_before: Rows
    rows_after: Rows
    violations: list[tuple[Any, ...]]
    integrity: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def upgraded(install_at_006: Path, tmp_path_factory: pytest.TempPathFactory) -> Upgrade:
    db = _copy(install_at_006, tmp_path_factory.mktemp("upgraded") / "app.db")
    rows_before = _rows(db)
    _migrate(db, "upgrade", REV_007)
    _assert_includes_007(db)
    rows_after, violations, integrity = _rows(db), _violations(db), _integrity(db)
    _migrate(db, "upgrade", "head")
    return Upgrade(db=db, rows_before=rows_before, rows_after=rows_after, violations=violations, integrity=integrity)


@dataclass(frozen=True)
class RoundTrip:
    """A copy of the install taken to 007, given settings of every kind, downgraded to 006, then upgraded to 007 again."""

    db: Path
    rows_with_settings: Rows
    tables_down: set[str]
    rows_down: Rows
    revision_down: str
    violations_down: list[tuple[Any, ...]]
    integrity_down: list[tuple[Any, ...]]
    rows_again: Rows
    revision_again: str


@pytest.fixture(scope="module")
def round_trip(install_at_006: Path, tmp_path_factory: pytest.TempPathFactory) -> RoundTrip:
    db = _copy(install_at_006, tmp_path_factory.mktemp("round-trip") / "app.db")
    _migrate(db, "upgrade", REV_007)
    _assert_includes_007(db)
    users = _users(db)
    with _foreign_keys_on(db) as conn:
        _insert_system(conn, "region", author=users["alice"])
        _insert_system(conn, "api_key", value_json=None, ciphertext=BLOB, key_id=KEY_ID, author=users["erin"])
        _insert_system(conn, "decimals", family="fx", code="LAB", value_json="3")
        _insert_user_row(conn, users["alice"], "limit")
        _insert_user_row(conn, users["erin"], "token", value_json=None, ciphertext=BLOB, key_id=KEY_ID)
        conn.commit()
    rows_with_settings = _rows(db)
    assert len(rows_with_settings[SYSTEM_TABLE][1]) == 3 and len(rows_with_settings[USER_TABLE][1]) == 2, "barrier: the settings are written before the downgrade"

    _migrate(db, "downgrade", REV_006)
    tables_down, rows_down, revision_down, violations_down, integrity_down = _tables(db), _rows(db), _revision(db), _violations(db), _integrity(db)
    _migrate(db, "upgrade", REV_007)
    return RoundTrip(
        db=db,
        rows_with_settings=rows_with_settings,
        tables_down=tables_down,
        rows_down=rows_down,
        revision_down=revision_down,
        violations_down=violations_down,
        integrity_down=integrity_down,
        rows_again=_rows(db),
        revision_again=_revision(db),
    )


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_revision_007_sits_on_006_and_the_chain_keeps_one_head() -> None:
    """1: ``007_plugin_settings`` exists in ``007_plugin_settings.py``, fits ``version_num``, revises 006; one head."""
    print_section("1: revision 007_plugin_settings")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_007 in revisions, f"revision {REV_007} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_007]
    assert len(script.revision) <= 32
    assert script.down_revision == REV_006, f"{REV_007} must revise {REV_006}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_007}.py"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {heads}"
    print_success(f"{REV_007} revises {REV_006}; one head ({heads[0]})")


# =============================================================================
# 2. A NEW DATABASE AT HEAD
# =============================================================================


@pytest.mark.parametrize(("table", "columns"), [pytest.param(SYSTEM_TABLE, SYSTEM_COLUMNS, id="system"), pytest.param(USER_TABLE, USER_COLUMNS, id="user")])
def test_the_tables_have_their_columns(fresh_head: Path, table: str, columns: dict[str, Declared]) -> None:
    """2: every column with its declared type, NOT NULL and primary key, and nothing else."""
    assert _table_info(fresh_head, table) == columns


def test_the_foreign_keys_cascade_from_a_user_and_unlink_an_author(fresh_head: Path) -> None:
    """2: a user's rows go with the user; a system row stays without its author."""
    assert _foreign_keys(fresh_head, USER_TABLE) == {"user_id": ("users", "id", "CASCADE")}
    assert _foreign_keys(fresh_head, SYSTEM_TABLE) == {"updated_by_user_id": ("users", "id", "SET NULL")}


@pytest.mark.parametrize("table", PLUGIN_TABLES)
def test_the_named_unique_constraint_and_checks(fresh_head: Path, table: str) -> None:
    """2: one row per field (and user), and the two CHECKs, under the names the migration and the models give them."""
    shape = _full_shape(fresh_head, table)
    assert shape is not None
    assert shape["unique constraints"] == [UNIQUE[table]]
    assert {name for name, _sql in shape["check constraints (name: sql)"]} == CHECKS[table]
    assert shape["indexes (name, columns, unique)"] == [], "no index beyond the unique constraint's"


@pytest.mark.parametrize("table", PLUGIN_TABLES)
@pytest.mark.parametrize(
    ("columns", "constraint"),
    [
        pytest.param({"value_json": None}, "one_value", id="neither-value-nor-secret"),
        pytest.param({"value_json": '"us"', "ciphertext": BLOB, "key_id": KEY_ID}, "one_value", id="value-and-secret"),
        pytest.param({"value_json": None, "ciphertext": BLOB}, "key_id", id="secret-without-key-id"),
        pytest.param({"value_json": '"us"', "key_id": KEY_ID}, "key_id", id="key-id-without-secret"),
    ],
)
def test_a_row_holds_exactly_one_value_and_a_key_id_only_with_a_secret(fresh_head: Path, tmp_path: Path, table: str, columns: dict[str, Any], constraint: str) -> None:
    """2: the two CHECKs, each case refused by the one it names; the two valid shapes accepted."""
    db = _copy(fresh_head, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        user = _insert_user(conn, "owner")
        conn.commit()
        with _refused(conn, "CHECK constraint failed", f"ck_{table}_{constraint}"):
            _insert_into(conn, table, user, "field", **columns)
        _insert_into(conn, table, user, "plain")
        _insert_into(conn, table, user, "secret", value_json=None, ciphertext=BLOB, key_id=KEY_ID)
        conn.commit()
        assert conn.execute(f"SELECT field_key FROM {table} ORDER BY id").fetchall() == [("plain",), ("secret",)]


def test_a_field_is_stored_once_per_instance_and_once_per_user(fresh_head: Path, tmp_path: Path) -> None:
    """2: the unique constraints: a duplicate refused; the same field for two users, or in two families, accepted."""
    db = _copy(fresh_head, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        alice, bob = _insert_user(conn, "alice"), _insert_user(conn, "bob")
        _insert_system(conn, "region")
        _insert_user_row(conn, alice, "limit")
        conn.commit()

        with _refused(conn, "UNIQUE constraint failed", SYSTEM_TABLE):
            _insert_system(conn, "region", value_json='"eu"')
        with _refused(conn, "UNIQUE constraint failed", USER_TABLE):
            _insert_user_row(conn, alice, "limit", value_json="9")
        _insert_system(conn, "region", family="fx")
        _insert_system(conn, "region", code="other")
        _insert_user_row(conn, bob, "limit")
        _insert_user_row(conn, alice, "limit", family="fx")
        conn.commit()


def test_a_user_row_needs_a_user(fresh_head: Path, tmp_path: Path) -> None:
    db = _copy(fresh_head, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        with _refused(conn, "FOREIGN KEY constraint failed"):
            _insert_user_row(conn, 987_654, "limit")
        with _refused(conn, "NOT NULL constraint failed", "user_id"):
            conn.execute(f"INSERT INTO {USER_TABLE} (family, plugin_code, field_key, value_json, updated_at) VALUES ('asset', 'lab', 'limit', '7', ?)", (STAMP,))


def test_deleting_a_user_deletes_its_rows_and_unlinks_the_system_rows_it_wrote(fresh_head: Path, tmp_path: Path) -> None:
    """2: with foreign keys on; every other row and link stays. The database belongs to this test alone: the comparison is exact."""
    print_section("2: deleting a user")
    db = _copy(fresh_head, tmp_path / "app.db")
    with _foreign_keys_on(db) as conn:
        gone, kept = _insert_user(conn, "gone"), _insert_user(conn, "kept")
        written_by_gone = _insert_system(conn, "region", author=gone)
        written_by_kept = _insert_system(conn, "verbose", value_json="true", author=kept)
        _insert_user_row(conn, gone, "limit")
        _insert_user_row(conn, gone, "token", value_json=None, ciphertext=BLOB, key_id=KEY_ID)
        kept_row = _insert_user_row(conn, kept, "limit")
        conn.commit()

        conn.execute("DELETE FROM users WHERE id = ?", (gone,))
        conn.commit()
        system = conn.execute(f"SELECT id, updated_by_user_id FROM {SYSTEM_TABLE} ORDER BY id").fetchall()
        user = conn.execute(f"SELECT id, user_id FROM {USER_TABLE} ORDER BY id").fetchall()

    assert system == [(written_by_gone, None), (written_by_kept, kept)], "the system rows stay; the deleted author is unlinked"
    assert user == [(kept_row, kept)], "the deleted user's rows go, the others stay"
    assert _violations(db) == []
    print_success("its rows deleted, its system rows unlinked, nothing else touched")


# =============================================================================
# 3. MODELS AND MIGRATION AGREE
# =============================================================================


@pytest.mark.parametrize("table", PLUGIN_TABLES)
def test_the_models_and_the_migration_build_the_same_table(fresh_head: Path, created_by_models: Path, table: str) -> None:
    """3: columns and types, nullability, primary key, foreign keys and ON DELETE, unique constraints and CHECKs, by name and text."""
    print_section(f"3: {table}, migration = models")
    migrated, modelled = _full_shape(fresh_head, table), _full_shape(created_by_models, table)
    for origin, shape in (("alembic upgrade head", migrated), ("SQLModel.metadata.create_all", modelled)):
        assert shape is not None, f"barrier: {origin} has no {table} table"
        assert set(shape["columns (name: nullable)"]) == set(SYSTEM_COLUMNS if table == SYSTEM_TABLE else USER_COLUMNS), f"barrier: {origin} builds {table} with other columns"

    differences = {key: {"migration": migrated[key], "models": modelled[key]} for key in migrated if migrated[key] != modelled[key]}
    assert not differences, f"{table}: the migration and the models disagree on {differences}"
    print_success(f"{table}: the same table both ways")


# =============================================================================
# 4. A POPULATED INSTALL UPGRADED
# =============================================================================


def test_a_populated_install_keeps_every_row_of_every_table(upgraded: Upgrade, fresh_head: Path) -> None:
    """4: every table of the install at 006, ids included, read on its columns: as it was."""
    print_section("4: the install at 006, upgraded")
    before = _without(upgraded.rows_before, BOOKKEEPING)
    after = _without(upgraded.rows_after, BOOKKEEPING | set(PLUGIN_TABLES))
    assert set(before) == _tables(fresh_head) - set(PLUGIN_TABLES) - BOOKKEEPING, "barrier: the install holds every table of the schema at 006"
    assert all(before[name][1] for name in ("users", "user_settings", "brokers", "broker_user_access", "transactions", "account_tokens", "global_settings")), "barrier: the install is populated"

    differences = _differences(before, after)

    assert not differences, f"the upgrade changed rows: {differences}"
    print_success(f"{len(before)} tables, every row as it was")


def test_a_populated_install_gets_the_two_tables_empty_and_no_violation(upgraded: Upgrade) -> None:
    assert {table: upgraded.rows_after[table][1] for table in PLUGIN_TABLES} == {SYSTEM_TABLE: [], USER_TABLE: []}
    assert upgraded.violations == [] and upgraded.integrity == [("ok",)]


def test_a_populated_install_reaches_the_head(upgraded: Upgrade) -> None:
    _assert_includes_007(upgraded.db)
    assert _revision(upgraded.db) == _scripts().get_current_head()


# =============================================================================
# 5. THE DOWNGRADE, AND BACK
# =============================================================================


def test_the_downgrade_drops_both_tables_and_returns_to_006(round_trip: RoundTrip) -> None:
    """5: the settings, secrets included, are lost with their tables, as the migration documents."""
    assert not set(PLUGIN_TABLES) & round_trip.tables_down
    assert round_trip.revision_down == REV_006


def test_the_downgrade_touches_no_other_row(round_trip: RoundTrip) -> None:
    """5: dropping the child tables of ``users`` unlinks nothing and deletes nothing elsewhere."""
    print_section("5: the downgrade touches no other row")
    expected = _without(round_trip.rows_with_settings, BOOKKEEPING | set(PLUGIN_TABLES))
    actual = _without(round_trip.rows_down, BOOKKEEPING)

    differences = _differences(expected, actual)
    assert not differences, f"the downgrade changed rows it had no reason to touch: {differences}"
    assert round_trip.violations_down == [] and round_trip.integrity_down == [("ok",)]
    print_success(f"{len(expected)} tables, every row as it was at 007")


def test_upgrading_again_gives_empty_tables_with_the_schema_of_a_new_database(round_trip: RoundTrip, fresh_head: Path) -> None:
    assert round_trip.revision_again == REV_007
    assert {table: round_trip.rows_again[table][1] for table in PLUGIN_TABLES} == {SYSTEM_TABLE: [], USER_TABLE: []}
    for table in PLUGIN_TABLES:
        assert _full_shape(round_trip.db, table) == _full_shape(fresh_head, table), f"{table}: not the schema of a new database"
    differences = _differences(_without(round_trip.rows_down, BOOKKEEPING), _without(round_trip.rows_again, BOOKKEEPING | set(PLUGIN_TABLES)))
    assert not differences, f"upgrading again changed rows: {differences}"


# =============================================================================
# 6. IDEMPOTENT BOTH WAYS
# =============================================================================


@pytest.mark.parametrize("present", PLUGIN_TABLES)
def test_an_upgrade_that_finds_one_table_creates_the_other_and_keeps_it(fresh_head: Path, tmp_path: Path, present: str) -> None:
    """6: a run that stopped after its first table: the table is kept, its row included, and the schema completed."""
    print_section(f"6: an upgrade that finds {present}")
    db = tmp_path / "app.db"
    _migrate(db, "upgrade", REV_006)
    with _foreign_keys_on(db) as conn:
        conn.execute(_create_sql(fresh_head, present))
        user = _insert_user(conn, "owner")
        row = _insert_into(conn, present, user, "survivor")
        conn.commit()
    assert _revision(db) == REV_006, "setup: the revision is still 006"

    _migrate(db, "upgrade", REV_007)

    assert _revision(db) == REV_007
    for table in PLUGIN_TABLES:
        assert _full_shape(db, table) == _full_shape(fresh_head, table), f"{table}: not the schema of a new database"
    with _connect(db) as conn:
        assert conn.execute(f"SELECT id, field_key FROM {present}").fetchall() == [(row, "survivor")], "the table found must be kept with its rows"
    print_success(f"{present} kept with its row, the other table created")


@pytest.mark.parametrize("gone", PLUGIN_TABLES)
def test_a_downgrade_that_finds_one_table_gone_drops_the_other(fresh_head: Path, tmp_path: Path, gone: str) -> None:
    """6: a downgrade that stopped after its first drop: the revision is still 007, one table left; the rerun completes."""
    db = _copy(fresh_head, tmp_path / "app.db")
    _migrate(db, "downgrade", REV_007)
    with _foreign_keys_on(db) as conn:
        conn.execute(f"DROP TABLE {gone}")
        conn.commit()
    assert _revision(db) == REV_007 and gone not in _tables(db), "setup: the interrupted state"

    _migrate(db, "downgrade", REV_006)

    assert _revision(db) == REV_006
    assert not set(PLUGIN_TABLES) & _tables(db)
