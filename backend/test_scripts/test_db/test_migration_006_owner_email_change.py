"""Migration ``006_owner_email_change``: who the instance owner is, and the ``email_change`` token purpose (release 1.3, A5-1b part 2).

The revision, on top of ``005_release_1_3_0_schema``, does two things in one step:

1. ``users.is_instance_owner`` — ``BOOLEAN NOT NULL DEFAULT 0`` — and the partial unique index
   ``ux_users_instance_owner ON users (is_instance_owner) WHERE is_instance_owner = 1``: at most one owner. The query
   that reads it, ``SELECT id FROM users WHERE is_instance_owner = 1``, plans ``SEARCH users USING … INDEX
   ux_users_instance_owner`` (proven below).
2. ``account_tokens`` rebuilt (SQLite table rebuild through ``batch_alter_table``) so that ``ck_account_tokens_purpose``
   also accepts ``email_change``; every row, foreign key (``CASCADE`` / ``SET NULL``), unique constraint and index kept.

The downgrade drops the index and the column, removes the ``email_change`` rows, and restores the old CHECK; every other
row survives. Contract pinned here:

1. The revision exists, its id fits ``alembic_version`` (32), it revises 005 and is its only child; one head.
2. A new database taken to it by name has the column, the index and the new CHECK; ``account_tokens`` is otherwise what 005
   built (columns, foreign keys, unique, indexes).
3. A POPULATED database taken from 005 up keeps every row of every table, its users get ``0``, nothing is violated, and
   the foreign keys still cascade.
4. At most one owner (the index), and the index is used.
5. Down: a populated database goes back to the 005 schema with every non-``email_change`` row; up again works.
6. ``create_all`` (the models) builds the same ``users``, ``account_tokens`` and index as the migrations (``db create-clean``).
7. An upgrade stopped half way (the column already there) completes.

Safety and fidelity: ``alembic_harness`` — every database is a file under ``tmp_path``, foreign keys asserted ON at every
step, as production migrates.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

from backend.test_scripts.test_db.alembic_harness import (
    _connect,
    _copy,
    _create_all,
    _foreign_keys,
    _foreign_keys_on,
    _full_shape,
    _index_list,
    _integrity,
    _known,
    _lineage,
    _migrate,
    _revision,
    _rows,
    _scripts,
    _shape,
    _table_info,
    _violations,
)
from backend.test_scripts.test_utils import print_section, print_success

REV_005 = "005_release_1_3_0_schema"
REV_006 = "006_owner_email_change"
INDEX = "ux_users_instance_owner"
INDEX_SQL = "CREATE UNIQUE INDEX ux_users_instance_owner ON users (is_instance_owner) WHERE is_instance_owner = 1"
OWNER_QUERY = "SELECT id FROM users WHERE is_instance_owner = 1"
OLD_PURPOSES = ("invite", "password_reset", "email_verification", "admin_setup")
STAMP = "2026-10-22 09:30:00.000000"
LATER = "2026-10-29 09:30:00.000000"


def _collapsed(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def _need_006() -> None:
    assert _known(REV_006), f"red until A5-1b part 2: Alembic cannot locate {REV_006}; the chain's heads are {list(_scripts().get_heads())}"


@pytest.fixture(scope="module")
def at_005(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to 005 by name. Read-only: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("own-005") / "app.db"
    _migrate(db, "upgrade", REV_005)
    return db


@pytest.fixture(scope="module")
def at_006(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A new database taken to 006 by name. Read-only."""
    _need_006()
    db = tmp_path_factory.mktemp("own-006") / "app.db"
    _migrate(db, "upgrade", REV_006)
    return db


def _populate(db: Path) -> None:
    """The rows of an install at 005: two users, tokens of the four purposes (one spent, one with a creator), settings."""
    with _foreign_keys_on(db) as conn:
        conn.execute("INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (1, 'alice', 'alice@x.test', 'h', 1, 1, ?, ?)", (STAMP, STAMP))
        conn.execute("INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (2, 'bob', 'bob@x.test', 'h', 1, 0, ?, ?)", (STAMP, STAMP))
        conn.execute("INSERT INTO user_settings (user_id, base_currency, language, theme, created_at, updated_at) VALUES (1, 'EUR', 'it', 'dark', ?, ?)", (STAMP, STAMP))
        for number, purpose in enumerate(OLD_PURPOSES, start=1):
            user = None if purpose == "invite" else 1
            conn.execute(
                "INSERT INTO account_tokens (id, purpose, token_hash, user_id, email, grants_admin, created_by_user_id, created_at, expires_at, consumed_at, revoked_at, consumed_by_user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (number, purpose, f"{number:064x}", user, f"t{number}@x.test", 1 if purpose == "invite" else 0, 2, STAMP, LATER, STAMP if number == 2 else None, STAMP if number == 3 else None, 2 if number == 2 else None),
            )
        conn.commit()


def _insert_token(db: Path, purpose: str, number: int) -> None:
    with _foreign_keys_on(db) as conn:
        conn.execute("INSERT INTO account_tokens (purpose, token_hash, user_id, email, created_at, expires_at) VALUES (?, ?, 1, 'new@x.test', ?, ?)", (purpose, f"{number:064x}", STAMP, LATER))
        conn.commit()


def test_the_revision_exists_fits_and_follows_005() -> None:
    """MIG6-001: ``006_owner_email_change`` exists, is at most 32 characters, revises 005 and is its only child; one head, which includes it."""
    print_section("MIG6-001: the revision")
    _need_006()
    assert len(REV_006) <= 32
    scripts = _scripts()
    assert scripts.get_revision(REV_006).down_revision == REV_005
    assert [script.revision for script in scripts.walk_revisions() if script.down_revision == REV_005] == [REV_006]
    heads = scripts.get_heads()
    assert len(heads) == 1 and REV_006 in _lineage(heads[0]), heads
    print_success(f"{REV_006} follows {REV_005}; head {heads[0]}")


def test_a_new_database_has_the_column_the_index_and_the_new_check(at_006: Path, at_005: Path) -> None:
    """MIG6-002: at 006 the column is ``BOOLEAN NOT NULL DEFAULT 0``, the index is the partial unique one, ``email_change`` is accepted and an unknown purpose still refused; ``account_tokens`` is otherwise 005's."""
    print_section("MIG6-002: a new database at 006")
    column = _table_info(at_006, "users")["is_instance_owner"]
    assert column.type.upper() in ("BOOLEAN", "INTEGER") and column.not_null and column.default == "0", column
    with _connect(at_006) as conn:
        (sql,) = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (INDEX,)).fetchone()
    assert _collapsed(sql) == INDEX_SQL, sql
    copy = _copy(at_006, at_006.parent / "probe.db")
    with _foreign_keys_on(copy) as conn:
        conn.execute("INSERT INTO users (id, username, email, hashed_password, created_at, updated_at) VALUES (1, 'a', 'a@x.test', 'h', ?, ?)", (STAMP, STAMP))
        conn.commit()
    _insert_token(copy, "email_change", 1)
    with pytest.raises(sqlite3.IntegrityError, match="ck_account_tokens_purpose|CHECK"):
        _insert_token(copy, "bogus", 2)
    before, after = _full_shape(at_005, "account_tokens"), _full_shape(at_006, "account_tokens")
    assert before is not None and after is not None
    for key in ("columns (name: nullable)", "primary key", "foreign keys", "indexes (name, columns, unique)", "unique column sets", "unique constraints", "column types"):
        assert before[key] == after[key], f"{key}: 005 {before[key]} vs 006 {after[key]}"
    assert "email_change" in dict(after["check constraints (name: sql)"])["ck_account_tokens_purpose"]
    assert "email_change" not in dict(before["check constraints (name: sql)"])["ck_account_tokens_purpose"]


def test_a_populated_database_keeps_every_row(at_005: Path, tmp_path: Path) -> None:
    """MIG6-003: an install at 005 with rows goes up: every row of every table kept (the users with ``is_instance_owner`` 0), nothing violated, and the foreign keys of ``account_tokens`` still cascade and null."""
    print_section("MIG6-003: up on a populated database")
    _need_006()
    db = _copy(at_005, tmp_path / "populated.db")
    _populate(db)
    before = _rows(db)

    _migrate(db, "upgrade", REV_006)

    after = _rows(db)
    assert _revision(db) == REV_006 and _violations(db) == [] and _integrity(db) == [("ok",)]
    for table, (columns, rows) in before.items():
        if table == "alembic_version":
            continue
        if table == "users":
            new_columns, new_rows = after[table]
            assert new_columns == [*columns, "is_instance_owner"]
            assert sorted((row[:-1] for row in new_rows), key=repr) == rows and {row[-1] for row in new_rows} == {0}
        else:
            assert after[table] == (columns, rows), table
    assert _foreign_keys(db, "account_tokens") == {"user_id": ("users", "id", "CASCADE"), "created_by_user_id": ("users", "id", "SET NULL"), "consumed_by_user_id": ("users", "id", "SET NULL")}
    with _foreign_keys_on(db) as conn:
        conn.execute("DELETE FROM users WHERE id = 2")
        assert conn.execute("SELECT count(*) FROM account_tokens WHERE created_by_user_id IS NULL AND consumed_by_user_id IS NULL").fetchone()[0] == 4
        conn.execute("DELETE FROM users WHERE id = 1")
        assert conn.execute("SELECT count(*) FROM account_tokens").fetchone()[0] == 1, "only the invitation (no user) survives the cascade"
        conn.rollback()


def test_at_most_one_owner_and_the_index_is_used(at_006: Path, tmp_path: Path) -> None:
    """MIG6-004: two accounts at 0 are fine, one at 1 is fine, a second at 1 is refused; the owner query plans the partial index."""
    _need_006()
    db = _copy(at_006, tmp_path / "owners.db")
    with _foreign_keys_on(db) as conn:
        for number in (1, 2, 3):
            conn.execute("INSERT INTO users (id, username, email, hashed_password, created_at, updated_at) VALUES (?, ?, ?, 'h', ?, ?)", (number, f"u{number}", f"u{number}@x.test", STAMP, STAMP))
        conn.execute("UPDATE users SET is_instance_owner = 1 WHERE id = 1")
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conn.execute("UPDATE users SET is_instance_owner = 1 WHERE id = 2")
        conn.rollback()
        conn.execute("UPDATE users SET is_instance_owner = 1 WHERE id = 1")
        plan = " ".join(str(row[3]) for row in conn.execute(f"EXPLAIN QUERY PLAN {OWNER_QUERY}"))
    assert INDEX in plan, plan


def test_the_downgrade_goes_back_to_005_and_up_again(at_005: Path, tmp_path: Path) -> None:
    """MIG6-005: from 006 with an owner and ``email_change`` rows down to 005: the column and the index gone, the ``email_change`` rows removed and ``email_change`` refused again, every other row exactly kept, the 005 schema restored; then up again."""
    print_section("MIG6-005: down and up")
    _need_006()
    db = _copy(at_005, tmp_path / "down.db")
    _populate(db)
    _migrate(db, "upgrade", REV_006)
    _insert_token(db, "email_change", 10)
    _insert_token(db, "email_change", 11)
    with _foreign_keys_on(db) as conn:
        conn.execute("UPDATE users SET is_instance_owner = 1 WHERE id = 1")
        conn.commit()
    kept = {row for row in _rows(db)["account_tokens"][1] if row[1] != "email_change"}

    _migrate(db, "downgrade", REV_005)

    assert _revision(db) == REV_005 and _violations(db) == [] and _integrity(db) == [("ok",)]
    assert "is_instance_owner" not in _table_info(db, "users") and INDEX not in _index_list(db, "users")
    assert set(_rows(db)["account_tokens"][1]) == kept
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        _insert_token(db, "email_change", 12)
    fresh = _copy(at_005, tmp_path / "fresh005.db")
    for table in ("users", "account_tokens"):
        assert _full_shape(db, table) == _full_shape(fresh, table), table

    _migrate(db, "upgrade", REV_006)
    assert _revision(db) == REV_006 and set(_rows(db)["account_tokens"][1]) == kept


def test_an_upgrade_stopped_half_way_completes(at_005: Path, tmp_path: Path) -> None:
    """MIG6-006: the column already added (a run stopped after its first step): the upgrade runs again to the end with the index and the new CHECK."""
    _need_006()
    db = _copy(at_005, tmp_path / "half.db")
    with _connect(db) as conn:
        conn.execute("ALTER TABLE users ADD COLUMN is_instance_owner BOOLEAN NOT NULL DEFAULT 0")
        conn.commit()
    _migrate(db, "upgrade", REV_006)
    assert INDEX in _index_list(db, "users")
    with _foreign_keys_on(db) as conn:
        conn.execute("INSERT INTO users (id, username, email, hashed_password, created_at, updated_at) VALUES (1, 'a', 'a@x.test', 'h', ?, ?)", (STAMP, STAMP))
        conn.commit()
    _insert_token(db, "email_change", 1)
    fresh = tmp_path / "fresh006.db"
    _migrate(fresh, "upgrade", REV_006)
    for table in ("users", "account_tokens"):
        assert _full_shape(db, table) == _full_shape(fresh, table), table


def test_the_models_and_the_migration_build_the_same_tables(at_006: Path, tmp_path: Path) -> None:
    """MIG6-007 (``db create-clean``): ``create_all`` and the migrations build the same ``users`` and ``account_tokens``, and the same partial index (its SQL, whitespace collapsed)."""
    created = _create_all(tmp_path / "models.db")
    for table in ("users", "account_tokens"):
        assert _shape(at_006, table) == _shape(created, table), table
    assert _full_shape(at_006, "account_tokens") == _full_shape(created, "account_tokens")
    sqls = []
    for db in (at_006, created):
        with _connect(db) as conn:
            row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (INDEX,)).fetchone()
        assert row is not None, f"{db.name} has no {INDEX}"
        sqls.append(_collapsed(row[0]).replace('"', ""))
    assert sqls[0] == sqls[1] == INDEX_SQL, sqls
