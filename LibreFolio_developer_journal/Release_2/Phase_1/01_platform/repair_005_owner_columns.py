#!/usr/bin/env python3
"""One-off repair: a database stamped ``005_release_1_3_0_schema`` by the nightly of train 10, before the owner of the
instance was folded into 005 (24/10/2026).

That nightly carried a 005 without ``users.is_instance_owner``, its partial unique index and the ``email_change``
purpose of ``account_tokens``; the fold put them in 005, and Alembic sees the head and runs nothing. This script adds
what is missing, by hand, once. It is NOT application code: nothing in the app calls it.

    python3 repair_005_owner_columns.py /path/to/app.db            # repair
    python3 repair_005_owner_columns.py /path/to/app.db --check    # only say what is missing, change nothing

What it does, and only when something is missing (a database that is already right is left untouched, no copy made):

1. refuses a database that is not stamped ``005_release_1_3_0_schema`` (and any file that is not a LibreFolio database);
2. copies the database file first (SQLite backup API, WAL included) to ``<db>.before-owner-fix-<timestamp>``;
3. in ONE transaction: adds ``users.is_instance_owner BOOLEAN NOT NULL DEFAULT 0`` (every account gets 0: the startup
   sync records the owner), creates ``ux_users_instance_owner``, rebuilds ``account_tokens`` so that
   ``ck_account_tokens_purpose`` also accepts ``email_change`` (rows kept, the table keeps its own SQL but for the CHECK);
4. verifies integrity, foreign keys and the result, and prints ``OK``.

Stop the server first (or use a copy of the file). Standard library only; never point it at a file you did not mean to
change: without ``--check`` it writes to it.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REVISION = "005_release_1_3_0_schema"
OWNER_COLUMN = "is_instance_owner"
OWNER_INDEX = "ux_users_instance_owner"
OWNER_COLUMN_SQL = f"ALTER TABLE users ADD COLUMN {OWNER_COLUMN} BOOLEAN NOT NULL DEFAULT 0"
OWNER_INDEX_SQL = f"CREATE UNIQUE INDEX {OWNER_INDEX} ON users ({OWNER_COLUMN}) WHERE {OWNER_COLUMN} = 1"
OLD_PURPOSES = ("invite", "password_reset", "email_verification", "admin_setup")
NEW_PURPOSES = (*OLD_PURPOSES, "email_change")
CHECK_NAME = "ck_account_tokens_purpose"


def _purposes_sql(purposes: tuple[str, ...]) -> str:
    return "purpose IN (" + ", ".join(f"'{purpose}'" for purpose in purposes) + ")"


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def _missing(conn: sqlite3.Connection) -> list[str]:
    """What the 005 of today has and this database lacks: ``column``, ``index``, ``check`` (in this order)."""
    missing: list[str] = []
    columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if OWNER_COLUMN not in columns:
        missing.append("column")
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (OWNER_INDEX,)).fetchone() is None:
        missing.append("index")
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'account_tokens'").fetchone()
    if row is None:
        _fail("the table account_tokens is missing: this is not a 005 database")
    if "'email_change'" not in row[0]:
        missing.append("check")
    return missing


def _check_revision(conn: sqlite3.Connection) -> None:
    try:
        revisions = [row[0] for row in conn.execute("SELECT version_num FROM alembic_version")]
    except sqlite3.DatabaseError as exc:
        _fail(f"not a LibreFolio database ({exc})")
    if revisions != [REVISION]:
        _fail(f"the database is stamped {revisions}, not {REVISION!r}: nothing was changed. (At 004 or older, start LibreFolio normally: its migrations do this.)")


def _backup(db: Path) -> Path:
    target = db.with_name(f"{db.name}.before-owner-fix-{datetime.now():%Y%m%d-%H%M%S}")
    source, copy = sqlite3.connect(db), sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        copy.close()
        source.close()
    return target


def _rebuild_tokens(conn: sqlite3.Connection) -> None:
    """``account_tokens`` again with a CHECK that accepts ``email_change``: its rows and its indexes kept. Nothing references the table."""
    (create_sql,) = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'account_tokens'").fetchone()
    old_check = f"CHECK ({_purposes_sql(OLD_PURPOSES)})"
    squeezed = re.sub(r"\s+", " ", create_sql)
    if old_check not in squeezed:
        _fail("account_tokens has a CHECK this script does not know: nothing was changed. Ask before going on.")
    new_sql = squeezed.replace(old_check, f"CHECK ({_purposes_sql(NEW_PURPOSES)})")
    indexes = conn.execute("SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = 'account_tokens' AND sql IS NOT NULL").fetchall()
    for name, _sql in indexes:
        conn.execute(f'DROP INDEX "{name}"')
    conn.execute("ALTER TABLE account_tokens RENAME TO account_tokens_old")
    conn.execute(new_sql)
    conn.execute("INSERT INTO account_tokens SELECT * FROM account_tokens_old")
    conn.execute("DROP TABLE account_tokens_old")
    for _name, sql in indexes:
        conn.execute(sql)


def repair(db: Path, check_only: bool) -> int:
    if not db.is_file():
        _fail(f"{db} is not a file")
    probe = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        _check_revision(probe)
        missing = _missing(probe)
    finally:
        probe.close()
    if not missing:
        print("Nothing to do: the owner's column, its index and the email_change purpose are all there. Nothing changed, no copy made.")
        return 0
    print(f"Missing: {', '.join(missing)}.")
    if check_only:
        print("--check: nothing changed.")
        return 0

    copy = _backup(db)
    print(f"Copy made: {copy}")
    conn = sqlite3.connect(db, isolation_level=None)  # explicit transaction below
    try:
        conn.execute("PRAGMA foreign_keys = OFF")  # the table rebuild; nothing points at account_tokens
        conn.execute("BEGIN IMMEDIATE")
        try:
            _check_revision(conn)  # again, now that the write lock is held
            missing = _missing(conn)
            if "column" in missing:
                conn.execute(OWNER_COLUMN_SQL)
            if "index" in missing:
                conn.execute(OWNER_INDEX_SQL)
            if "check" in missing:
                _rebuild_tokens(conn)
            problems = conn.execute("PRAGMA foreign_key_check").fetchall()
            if problems:
                raise sqlite3.IntegrityError(f"foreign key violations: {len(problems)}")
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        remaining = _missing(conn)
        integrity = conn.execute("PRAGMA integrity_check").fetchall()
    finally:
        conn.close()
    if remaining or integrity != [("ok",)]:
        _fail(f"after the repair: still missing {remaining}, integrity {integrity}. The copy {copy} holds the database as it was.")
    print("OK: column, index and email_change purpose are there; integrity ok. Start LibreFolio again.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("db", type=Path, help="path of the LibreFolio SQLite database file to repair")
    parser.add_argument("--check", action="store_true", help="only report what is missing; change nothing")
    args = parser.parse_args()
    return repair(args.db, args.check)


if __name__ == "__main__":
    raise SystemExit(main())
