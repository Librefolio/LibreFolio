"""Migration ``005_accounts_invites``: the accounts schema of release 1.3 (plan phase01Accounts §4.3, lot A4).

Invitations, password resets, e-mail verification and the setup link of the first administrator all rest on one table
of single-use tokens, ``account_tokens``, and on three new columns of ``users``. The migration adds them to
installations that hold real data, so it follows 004: raw, idempotent ``ALTER TABLE users ADD COLUMN`` guarded by
``PRAGMA table_info``, never a batch on ``users`` — with foreign keys on, a batch rebuild drops ``users``, and dropping
it cascades into every table that points at it —, ``op.create_table`` for the new table, ``ALTER TABLE … DROP COLUMN``
in the downgrade. The contract pinned here:

1. The revision: id ``005_accounts_invites`` (20 characters; ``alembic_version.version_num`` holds 32), in
   ``005_accounts_invites.py``, on top of ``004_release_1_2_0_schema``, and the chain keeps exactly one head. Which
   revision *is* the head is not pinned: 006 and 007 will sit on top of this one.
2. A new database at head: ``users`` gains ``session_version INTEGER NOT NULL DEFAULT 0``, ``email_verified_at DATETIME
   NULL`` and ``last_seen_version VARCHAR(40) NULL``; ``account_tokens`` has its columns, its three foreign keys to
   ``users``, its two indexes, ``uq_account_tokens_token_hash`` and ``ck_account_tokens_purpose``. With foreign keys
   on: an unknown purpose is refused and the four are accepted, a duplicate hash is refused, and deleting a user deletes
   the tokens that are its own while unlinking the ones it created or consumed.
3. Models and migration agree on ``users`` and ``account_tokens``: ``SQLModel.metadata.create_all`` builds the same
   columns and nullability, primary key, foreign keys (target and ON DELETE), indexes, unique and check constraints.
   Three service suites build their databases that way: a drift would test them against a schema production lacks.
   The comparison itself is pinned too (MIG005-A26-01 to -03, lot A-26): it sees an index on an expression, unique or
   not, by its name.
4. A populated 1.2 install upgraded keeps, right after 005, every row of every table, ids included (each table read on
   the columns it had); every existing user gets 0 / NULL / NULL — no backfill, ``email_verified_at`` included, by
   decision of the developer —; no foreign-key violation; ``account_tokens`` exists and is empty; taken on to head, the
   database is at head. The rows are compared at 005 because the migrations above it may convert data on purpose (006
   turns ``enable_registration`` into ``registration_mode``), and pin that themselves.
5. The downgrade to 004 of a populated database at 005 — tokens pointing at users through all three foreign keys, users
   with values of their own in the new columns — drops ``account_tokens`` and the three columns and touches no other
   row: nothing cascades into ``user_settings``, ``broker_user_access``, the onboarding tables or
   ``global_settings.updated_by_user_id``. No violation, at 004. Upgrading to 005 again works, and brings the columns
   back at their defaults.
6. An upgrade interrupted after its first ``ALTER`` (``session_version`` already there, the revision still 004)
   completes, and ends with the schema a new database gets.

The 1.2 install is the real one: the v1.1.0 schema and rows of ``test_post_migration`` (every table, gaps, a transfer
pair, a deleted user), taken to 004 by the real migrations and converted by the post-migration fixes a 1.2 server runs at
startup, plus rows only 1.2 writes: a user created after the upgrade, with settings, onboarding progress, a broker access
and a global setting she updated, a benchmark flag, an existing user's tour completed.

Safety and fidelity. Every database is a file under ``tmp_path``. Alembic runs in this process, always with
``cmd_opts.x = ["sqlalchemy.url=…"]`` (without it ``backend/alembic/env.py`` falls back to the configured database) and
without an ini file (``env.py`` would hand it to ``logging.config.fileConfig`` and reconfigure this process's logging).
While it runs, a connect listener refuses any connection to another file and records ``PRAGMA foreign_keys`` on its
own: production migrates in a process that imports ``backend.app.db.session``, whose listener turns foreign keys on,
and only with them on does "nothing cascades" mean anything. Every migration step asserts it.

Red until the migration and the models exist: every test first checks that the database it reads includes 005.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, Optional

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.pool import NullPool

from backend.app.config import PROJECT_ROOT
from backend.app.db import post_migration
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener
from backend.test_scripts.test_db.test_post_migration import _install_v110
from backend.test_scripts.test_utils import print_section, print_success

REV_004 = "004_release_1_2_0_schema"
REV_005 = "005_accounts_invites"
ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "backend" / "alembic"
AUTOINCREMENT_FIX = "autoincrement"

PURPOSES = ("invite", "password_reset", "email_verification", "admin_setup")

# The three columns 005 gives users: declared type, NOT NULL, and the value every existing user gets (no backfill).
NEW_USER_COLUMNS = {
    "session_version": ("INTEGER", True, 0),
    "email_verified_at": ("DATETIME", False, None),
    "last_seen_version": ("VARCHAR(40)", False, None),
}
EXISTING_USER_VALUES = (0, None, None)

TOKEN_NOT_NULL = frozenset({"purpose", "token_hash", "grants_admin", "created_at", "expires_at"})
TOKEN_NULLABLE = frozenset({"user_id", "email", "created_by_user_id", "consumed_at", "revoked_at", "consumed_by_user_id"})
TOKEN_COLUMNS = frozenset({"id"}) | TOKEN_NOT_NULL | TOKEN_NULLABLE
# column: (target table, target column, ON DELETE)
TOKEN_FOREIGN_KEYS = {
    "user_id": ("users", "id", "CASCADE"),
    "created_by_user_id": ("users", "id", "SET NULL"),
    "consumed_by_user_id": ("users", "id", "SET NULL"),
}
TOKEN_INDEXES = {
    "ix_account_tokens_purpose_expires_at": ("purpose", "expires_at"),
    "ix_account_tokens_user_id": ("user_id",),
}
TOKEN_CHECK = "ck_account_tokens_purpose"
TOKEN_UNIQUE = "uq_account_tokens_token_hash"

# The 1.2 tables that point at users: what a rebuild of users would empty, or unlink, with foreign keys on.
CHILDREN_OF_USERS = frozenset({"user_settings", "broker_user_access", "global_settings", "user_onboarding_progress", "user_onboarding_step_progress"})
# Alembic's own bookkeeping: its row is expected to change, and is asserted on its own.
BOOKKEEPING = frozenset({"alembic_version"})

STAMP = "2026-10-15 09:30:00.000000"
LATER = "2026-10-22 09:30:00.000000"

Rows = dict[str, tuple[list[str], list[tuple[Any, ...]]]]

# Rows only a 1.2 server writes, on top of the 1.1 install it upgraded and converted. Erin signed up after the upgrade:
# AUTOINCREMENT gives her an id above every id ever used. Her onboarding rows are created lazily, as the service does.
ROWS_1_2 = """
PRAGMA foreign_keys = ON;
BEGIN;

INSERT INTO users (username, email, hashed_password, is_active, is_superuser, login_count,
                   donation_popup_last_shown_at, donation_popup_logins_since_shown, created_at, updated_at) VALUES
    ('erin', 'erin@example.test', '$argon2id$erin', 1, 0, 2, NULL, 2, '2026-09-25 08:00:00.000000', '2026-09-25 08:00:00.000000');

INSERT INTO user_settings (user_id, base_currency, language, theme, avatar_url, created_at, updated_at)
    SELECT id, 'EUR', 'it', 'dark', NULL, '2026-09-25 08:00:00.000000', '2026-09-25 08:00:00.000000' FROM users WHERE username = 'erin';

INSERT INTO user_onboarding_progress (user_id, flow, status, version, created_at, updated_at, completed_at, skipped_at)
    SELECT id, 'welcome', 'completed', 1, '2026-09-25 08:00:01.000000', '2026-09-25 08:05:00.000000', '2026-09-25 08:05:00.000000', NULL FROM users WHERE username = 'erin';
INSERT INTO user_onboarding_progress (user_id, flow, status, version, created_at, updated_at, completed_at, skipped_at)
    SELECT id, 'intro_tour', 'pending', 1, '2026-09-25 08:00:01.000000', '2026-09-25 08:00:01.000000', NULL, NULL FROM users WHERE username = 'erin';
INSERT INTO user_onboarding_step_progress (user_id, flow, step_id, status, version, created_at, updated_at, completed_at, skipped_at)
    SELECT id, 'import_guide', 'import.upload', 'pending', 1, '2026-09-25 08:00:01.000000', '2026-09-25 08:00:01.000000', NULL, NULL FROM users WHERE username = 'erin';

INSERT INTO broker_user_access (user_id, broker_id, role, share_percentage, created_at, updated_at)
    SELECT id, 1, 'VIEWER', 0, '2026-09-25 08:10:00.000000', '2026-09-25 08:10:00.000000' FROM users WHERE username = 'erin';

INSERT INTO global_settings (key, value, value_type, description, updated_at, updated_by_user_id)
    SELECT 'session_ttl_hours', '48', 'int', 'Session cookie TTL in hours', '2026-09-26 09:00:00.000000', id FROM users WHERE username = 'erin';

-- 004 seeded the flag on the INDEX assets only; a user then offered a bond for comparison.
UPDATE assets SET is_benchmark = 1 WHERE id = 4;
-- An existing user went through the tour the upgrade had marked skipped.
UPDATE user_onboarding_progress
   SET status = 'completed', completed_at = '2026-09-27 10:00:00.000000', skipped_at = NULL, updated_at = '2026-09-27 10:00:00.000000'
 WHERE user_id = 1 AND flow = 'intro_tour';

COMMIT;
"""

# Five distinct 64-hex-character hashes, as hash_token writes them.
RESET_HASH, ADMIN_INVITE_HASH, VERIFICATION_HASH, CONSUMED_INVITE_HASH, SETUP_HASH = (str(n) * 64 for n in range(1, 6))

# What a 1.3 server writes once at head: values of their own in the new user columns, and tokens pointing at users
# through all three foreign keys — the rows a careless downgrade would have to get rid of first.
HEAD_ROWS = f"""
PRAGMA foreign_keys = ON;
BEGIN;

UPDATE users SET session_version = 3, email_verified_at = '2026-10-02 08:00:00.000000', last_seen_version = '1.3.0' WHERE username = 'alice';
UPDATE users SET session_version = 1, last_seen_version = '1.2.0' WHERE username = 'carol';
UPDATE users SET email_verified_at = '2026-10-03 09:30:00.000000' WHERE username = 'erin';

INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_by_user_id, created_at, expires_at, consumed_at, revoked_at, consumed_by_user_id) VALUES
    -- alice's reset, asked for by carol, used by dave: the three foreign keys at once
    ('password_reset', '{RESET_HASH}', 1, NULL, 0, 3, '{STAMP}', '{LATER}', '2026-10-15 09:40:00.000000', NULL, 4),
    -- an admin invite alice created, still pending
    ('invite', '{ADMIN_INVITE_HASH}', NULL, 'frank@example.test', 1, 1, '{STAMP}', '{LATER}', NULL, NULL, NULL),
    -- dave's e-mail verification, pending
    ('email_verification', '{VERIFICATION_HASH}', 4, NULL, 0, NULL, '{STAMP}', '{LATER}', NULL, NULL, NULL);

INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_by_user_id, created_at, expires_at, consumed_at, revoked_at, consumed_by_user_id)
    -- an invite erin created, consumed by carol
    SELECT 'invite', '{CONSUMED_INVITE_HASH}', NULL, NULL, 0, id, '{STAMP}', '{LATER}', '2026-10-16 11:00:00.000000', NULL, 3 FROM users WHERE username = 'erin';
INSERT INTO account_tokens (purpose, token_hash, user_id, email, grants_admin, created_by_user_id, created_at, expires_at, consumed_at, revoked_at, consumed_by_user_id)
    -- erin's setup link, revoked
    SELECT 'admin_setup', '{SETUP_HASH}', id, NULL, 0, NULL, '{STAMP}', '{LATER}', NULL, '2026-10-15 10:00:00.000000', NULL FROM users WHERE username = 'erin';

COMMIT;
"""


class Declared(NamedTuple):
    """One column as ``PRAGMA table_info`` reports it."""

    type: str
    not_null: bool
    default: Optional[str]
    primary_key: bool


# =============================================================================
# HELPERS — Alembic, in this process, on a private file only
# =============================================================================


def _alembic_config(db: Optional[Path] = None) -> Config:
    """An Alembic ``Config`` for the private database ``db``, or for no database at all to read the scripts.

    ``backend/alembic/env.py`` honours a URL only from ``-x sqlalchemy.url=…``: ``sqlalchemy.url`` set on the Config
    alone is ignored and the migration runs on the configured database. ``cmd_opts.x`` is what the ``alembic`` command
    line fills in; it is filled in here. No ini file: ``env.py`` would pass it to ``logging.config.fileConfig``.
    """
    cfg = Config()
    cfg.set_main_option("script_location", str(ALEMBIC_SCRIPT_LOCATION))
    if db is not None:
        url = f"sqlite:///{db}"
        cfg.set_main_option("sqlalchemy.url", url)
        cfg.cmd_opts = argparse.Namespace(x=[f"sqlalchemy.url={url}"])
    return cfg


def _scripts() -> ScriptDirectory:
    return ScriptDirectory.from_config(_alembic_config())


@contextmanager
def _alembic_connections(db: Path) -> Iterator[list[int]]:
    """While the block runs, refuse every new connection to a database other than ``db``; yield ``PRAGMA foreign_keys`` of each one to ``db``.

    Registered after the listener of ``backend.app.db.session``, so it reads the PRAGMAs that listener set: the ones
    production migrates with.
    """
    target = db.resolve()
    foreign_keys: list[int] = []

    def watch(dbapi_connection: Any, _connection_record: Any) -> None:
        opened = next((row[2] for row in dbapi_connection.execute("PRAGMA database_list") if row[1] == "main"), "")
        if not opened or Path(opened).resolve() != target:
            raise RuntimeError(f"safety: Alembic connected to {opened or 'a database without a file'}, not to the private database {target}")
        foreign_keys.append(dbapi_connection.execute("PRAGMA foreign_keys").fetchone()[0])

    event.listen(Engine, "connect", watch)
    try:
        yield foreign_keys
    finally:
        event.remove(Engine, "connect", watch)


def _migrate(db: Path, direction: str, revision: str) -> None:
    """``alembic <direction> <revision>`` on ``db``, in this process: on ``db`` alone, with foreign keys on, or the setup fails."""
    assert db.is_absolute() and db.parent.is_dir(), f"setup: {db} must be an absolute path in an existing folder"
    step = {"upgrade": command.upgrade, "downgrade": command.downgrade}[direction]
    with _alembic_connections(db) as foreign_keys:
        step(_alembic_config(db), revision)
    assert foreign_keys, f"setup: alembic {direction} {revision} opened no connection to {db}"
    assert set(foreign_keys) == {1}, f"setup: alembic {direction} {revision} ran with PRAGMA foreign_keys {foreign_keys}; production migrates with them on (backend.app.db.session), and only then can a rebuild of users cascade"


def _lineage(revision: str) -> set[str]:
    """``revision`` and every revision below it."""
    scripts = _scripts()
    found: set[str] = set()
    pending: list[Optional[str]] = [revision]
    while pending:
        current = pending.pop()
        if current is None or current in found:
            continue
        found.add(current)
        down = scripts.get_revision(current).down_revision
        pending.extend(down if isinstance(down, (tuple, list)) else [down])
    return found


# =============================================================================
# HELPERS — reading and writing the private databases
# =============================================================================


def _connect(db: Path) -> closing[sqlite3.Connection]:
    """A connection to an existing database: ``sqlite3.connect`` would silently create a missing one."""
    assert db.is_file(), f"{db} does not exist"
    return closing(sqlite3.connect(db))


@contextmanager
def _foreign_keys_on(db: Path) -> Iterator[sqlite3.Connection]:
    """A connection to ``db`` that enforces foreign keys, as the application's engine does."""
    with _connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1, "setup: foreign keys must be on"
        yield conn


def _copy(source: Path, target: Path) -> Path:
    """A consistent copy of ``source`` at ``target``, through SQLite's backup API (WAL content included)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    assert not target.exists(), f"setup: {target} already exists"
    with _connect(source) as src, closing(sqlite3.connect(target)) as dst:
        src.backup(dst)
    return target


def _revision(db: Path) -> str:
    with _connect(db) as conn:
        return conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]


def _assert_includes_005(db: Path) -> None:
    """Barrier: ``db`` is at 005 or above; otherwise nothing that follows is about 005."""
    revision = _revision(db)
    assert REV_005 in _lineage(revision), f"barrier: {db.name} is at {revision}, which does not include {REV_005}: the assertions that follow would say nothing about the migration"


def _tables(db: Path) -> set[str]:
    with _connect(db) as conn:
        return {name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def _table_info(db: Path, table: str) -> dict[str, Declared]:
    """``PRAGMA table_info`` as ``{column: Declared}``; empty when the table does not exist."""
    with _connect(db) as conn:
        return {name: Declared(declared, bool(not_null), default, bool(key)) for _cid, name, declared, not_null, default, key in conn.execute(f'PRAGMA table_info("{table}")')}


def _index_list(db: Path, table: str) -> dict[str, tuple[bool, str, tuple[str, ...]]]:
    """Every index of ``table``, SQLite's own included: ``{name: (unique, origin, columns)}``.

    A key is its column's name. ``PRAGMA index_info`` names no column for a key that is an expression —
    ``ux_users_email_lower`` is on ``lower(email)`` —, and ``None`` would neither sort nor say which expression: such a
    key is named by its text in the index's SQL instead, as ``_written_keys`` reads it.
    """
    with _connect(db) as conn:
        found: dict[str, tuple[bool, str, tuple[str, ...]]] = {}
        for _seq, name, unique, origin, _partial in conn.execute(f'PRAGMA index_list("{table}")').fetchall():
            keys = conn.execute(f'PRAGMA index_info("{name}")').fetchall()
            if any(column is None for _seqno, _cid, column in keys):
                (sql,) = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)).fetchone()
                written = _written_keys(sql)
                assert len(written) == len(keys), f"{name}: PRAGMA index_info gives {len(keys)} key(s), its SQL {written}: {sql!r}"
                keys = [(seqno, cid, written[seqno] if column is None else column) for seqno, cid, column in keys]
            found[name] = (bool(unique), origin, tuple(column for _seqno, _cid, column in keys))
        return found


def _written_keys(sql: str) -> list[str]:
    """The keys of ``CREATE [UNIQUE] INDEX name ON table (key, …) [WHERE …]`` as its SQL writes them: the first list in
    brackets, cut at its own commas. Each key is read as ``test_migration_009_email_case`` reads the index — lower case,
    no spaces, names without their quotes or brackets (a string keeps its ``'…'``) —: ``LOWER( "email" )`` is the key
    ``lower(email)``, a spelling and not another index. Quoted text is not syntax: a comma or a bracket inside a string
    or a quoted name cuts nothing.
    """
    plain = re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`|\[[^\]]*\]", lambda quoted: "_" * len(quoted.group()), sql)  # same length: positions still point into sql
    keys: list[str] = []
    depth, start = 0, plain.index("(") + 1
    for position in range(start, len(plain)):
        char = plain[position]
        if char == "(":
            depth += 1
        elif char == ")" and depth:
            depth -= 1
        elif char in ",)" and not depth:
            keys.append(re.sub(r"[\s\"`\[\]]", "", sql[start:position]).lower())
            start = position + 1
            if char == ")":
                return keys
    raise AssertionError(f"no closed list of keys in {sql!r}")


def _foreign_keys(db: Path, table: str) -> dict[str, tuple[str, str, str]]:
    """``PRAGMA foreign_key_list`` as ``{column: (target table, target column, ON DELETE)}``."""
    with _connect(db) as conn:
        return {column: (target, target_column, on_delete.upper()) for _id, _seq, target, column, target_column, _on_update, on_delete, _match in conn.execute(f'PRAGMA foreign_key_list("{table}")')}


def _violations(db: Path) -> list[tuple[Any, ...]]:
    with _connect(db) as conn:
        return conn.execute("PRAGMA foreign_key_check").fetchall()


def _integrity(db: Path) -> list[tuple[Any, ...]]:
    with _connect(db) as conn:
        return conn.execute("PRAGMA integrity_check").fetchall()


def _rows(db: Path) -> Rows:
    """Every row of every table, ``sqlite_sequence`` included, with the table's columns: ``{table: (columns, rows)}``."""
    with _connect(db) as conn:
        rows: Rows = {}
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall():
            cursor = conn.execute(f'SELECT * FROM "{table}"')
            rows[table] = ([column[0] for column in cursor.description], sorted(cursor.fetchall(), key=repr))
        return rows


def _on_columns(rows: Rows, table: str, columns: list[str]) -> list[tuple[Any, ...]]:
    """The rows of ``table`` read on ``columns`` only, sorted as ``_rows`` sorts them."""
    present, content = rows[table]
    lost = [column for column in columns if column not in present]
    assert not lost, f"{table} lost its columns {lost}"
    positions = [present.index(column) for column in columns]
    return sorted((tuple(row[position] for position in positions) for row in content), key=repr)


def _row_changes(expected: Rows, actual: Rows, tables: Iterable[str], *, columns_of: Rows) -> dict[str, str]:
    """The tables whose rows differ between ``expected`` and ``actual``, both read on the columns ``columns_of`` gives the table."""
    changes: dict[str, str] = {}
    for table in sorted(tables):
        if table not in actual:
            changes[table] = "the table is gone"
            continue
        columns = columns_of[table][0]
        wanted, found = _on_columns(expected, table, columns), _on_columns(actual, table, columns)
        if wanted != found:
            missing = [row for row in wanted if row not in found]
            unexpected = [row for row in found if row not in wanted]
            changes[table] = f"{len(missing)} row(s) missing or changed, e.g. {missing[:2]}; {len(unexpected)} unexpected, e.g. {unexpected[:2]}"
    return changes


def _new_user_columns(db: Path) -> dict[int, tuple[Any, ...]]:
    """``{user id: (session_version, email_verified_at, last_seen_version)}``, with ``session_version`` as SQLite stores it."""
    with _connect(db) as conn:
        rows = conn.execute("SELECT id, session_version, typeof(session_version), email_verified_at, last_seen_version FROM users").fetchall()
    return {user_id: (version if kind == "integer" else f"{version!r} stored as {kind}", verified, seen) for user_id, version, kind, verified, seen in rows}


def _tables_pointing_at_users(db: Path) -> set[str]:
    """The tables with at least one row whose foreign key points at an existing user."""
    found: set[str] = set()
    with _connect(db) as conn:
        tables = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()]
        for table in tables:
            columns = [column for _id, _seq, target, column, *_rest in conn.execute(f'PRAGMA foreign_key_list("{table}")').fetchall() if target == "users"]
            if any(conn.execute(f'SELECT 1 FROM "{table}" WHERE "{column}" IN (SELECT id FROM users) LIMIT 1').fetchone() for column in columns):
                found.add(table)
    return found


def _insert_user(conn: sqlite3.Connection, username: str) -> int:
    """A user with every column the application always writes, the new ones left to their defaults."""
    return conn.execute(
        "INSERT INTO users (username, email, hashed_password, created_at, updated_at) VALUES (?, ?, '$argon2id$test', ?, ?)",
        (username, f"{username}@example.test", STAMP, STAMP),
    ).lastrowid


def _token_hash(n: int) -> str:
    """A distinct 64-hex-character hash, as ``hash_token`` writes them."""
    return f"{n:064x}"


def _insert_token(conn: sqlite3.Connection, purpose: str, token_hash: str, **columns: Any) -> int:
    """An ``account_tokens`` row with the NOT NULL columns filled in and ``columns`` on top (``grants_admin`` left to its default unless given)."""
    values = {"purpose": purpose, "token_hash": token_hash, "created_at": STAMP, "expires_at": LATER, **columns}
    names = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    return conn.execute(f"INSERT INTO account_tokens ({names}) VALUES ({marks})", tuple(values.values())).lastrowid


def _token_links(conn: sqlite3.Connection) -> dict[int, tuple[Optional[int], Optional[int], Optional[int]]]:
    """``{token id: (user_id, created_by_user_id, consumed_by_user_id)}`` for every token."""
    return {token_id: (user_id, created_by, consumed_by) for token_id, user_id, created_by, consumed_by in conn.execute("SELECT id, user_id, created_by_user_id, consumed_by_user_id FROM account_tokens").fetchall()}


def _shape(db: Path, table: str) -> Optional[dict[str, Any]]:
    """What ``table`` is, read back from SQLite: what contract 3 compares. ``None`` when the table does not exist.

    A primary-key column counts as NOT NULL whatever its declaration says: SQLite gives a NULL ``INTEGER PRIMARY KEY``
    a rowid, and ``001_initial`` declares ``users.id`` without NOT NULL where ``create_all`` writes it. Indexes and
    uniqueness are read from ``PRAGMA index_list`` (``_index_list``), where a key that is an expression counts by its
    text: the indexes are those written with ``CREATE INDEX`` (origin ``c``), by name, keys and uniqueness; uniqueness is
    the set of column tuples that are unique, whether by a constraint or by an index. SQLAlchemy's inspector would leave an
    expression index such as ``ux_users_email_lower`` out of ``get_indexes``, on both sides alike, with the warning
    "Skipped unsupported reflection of expression-based index": a non-unique one on one side only, or under another name,
    would pass unseen (A-26).
    """
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        inspector = inspect(engine)
        if table not in inspector.get_table_names():
            return None
        primary_key = tuple(inspector.get_pk_constraint(table)["constrained_columns"])
        shape = {
            "columns (name: nullable)": {column["name"]: bool(column["nullable"]) and column["name"] not in primary_key for column in inspector.get_columns(table)},
            "primary key": primary_key,
            "foreign keys": sorted((tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]), ((fk.get("options") or {}).get("ondelete") or "NO ACTION").upper()) for fk in inspector.get_foreign_keys(table)),
            "check constraints": sorted(check["name"] or "<unnamed>" for check in inspector.get_check_constraints(table)),
        }
    finally:
        engine.dispose()
    indexes = _index_list(db, table)
    shape["indexes (name, columns, unique)"] = sorted((name, columns, unique) for name, (unique, origin, columns) in indexes.items() if origin == "c")
    shape["unique column sets"] = sorted({columns for unique, origin, columns in indexes.values() if unique and origin != "pk"})
    return shape


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
def install_1_2(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A populated 1.2 install at 004 (see the module docstring). Read-only for the tests: ``_copy`` it to write."""
    db = tmp_path_factory.mktemp("install-1.2") / "sqlite" / "app.db"
    _install_v110(db)
    _migrate(db, "upgrade", REV_004)
    report = post_migration.run_post_migration_fixes(db, None)
    assert report.outcomes.get(AUTOINCREMENT_FIX) == "applied", f"setup: the post-migration fixes a 1.2 server runs at startup did not convert the 1.1 rows: {report}"
    with _foreign_keys_on(db) as conn:
        conn.executescript(ROWS_1_2)
    assert _revision(db) == REV_004, "setup: a 1.2 install is at 004"
    assert _violations(db) == [], "setup: the 1.2 rows must be consistent"
    assert CHILDREN_OF_USERS <= _tables_pointing_at_users(db), f"setup: every table that points at users must have rows pointing at one, or 'nothing cascades' proves nothing for it; found {sorted(_tables_pointing_at_users(db))}"
    return db


@dataclass(frozen=True)
class Upgrade:
    """A copy of the 1.2 install: its rows before ``alembic upgrade``, its rows right after 005, and the database then taken to head.

    Contract 4 compares the rows at 005: the migrations above may convert data on purpose — 006 turns
    ``enable_registration`` into ``registration_mode`` — and pin that themselves (``test_migration_006_registration``).
    """

    db: Path
    rows_before: Rows
    rows_after: Rows


@pytest.fixture(scope="module")
def upgraded_1_2(install_1_2: Path, tmp_path_factory: pytest.TempPathFactory) -> Upgrade:
    db = _copy(install_1_2, tmp_path_factory.mktemp("upgraded-1.2") / "app.db")
    rows_before = _rows(db)
    _migrate(db, "upgrade", REV_005)
    rows_after = _rows(db)
    _migrate(db, "upgrade", "head")
    return Upgrade(db=db, rows_before=rows_before, rows_after=rows_after)


@dataclass(frozen=True)
class RoundTrip:
    """A copy of the 1.2 install taken to 005, given ``HEAD_ROWS``, downgraded to 004, then upgraded to 005 again.

    005 and nothing above it: 006 converts the registration row both ways on purpose, and would show here as a change
    005 never made.
    """

    db: Path
    tables_at_004: set[str]
    users_at_004: dict[str, Declared]
    rows_at_head: Rows
    tables_down: set[str]
    users_down: dict[str, Declared]
    rows_down: Rows
    revision_down: str
    violations_down: list[tuple[Any, ...]]
    integrity_down: list[tuple[Any, ...]]
    rows_again: Rows
    tables_again: set[str]
    new_columns_again: dict[int, tuple[Any, ...]]
    revision_again: str
    violations_again: list[tuple[Any, ...]]


@pytest.fixture(scope="module")
def round_trip(install_1_2: Path, tmp_path_factory: pytest.TempPathFactory) -> RoundTrip:
    db = _copy(install_1_2, tmp_path_factory.mktemp("round-trip") / "app.db")
    tables_at_004, users_at_004 = _tables(db), _table_info(db, "users")

    _migrate(db, "upgrade", REV_005)
    _assert_includes_005(db)
    with _foreign_keys_on(db) as conn:
        conn.executescript(HEAD_ROWS)
    pointing = _tables_pointing_at_users(db)
    assert CHILDREN_OF_USERS | {"account_tokens"} <= pointing, f"barrier: every table that points at users must have rows pointing at one before the downgrade; found {sorted(pointing)}"
    rows_at_head = _rows(db)

    _migrate(db, "downgrade", REV_004)
    tables_down, users_down, rows_down = _tables(db), _table_info(db, "users"), _rows(db)
    revision_down, violations_down, integrity_down = _revision(db), _violations(db), _integrity(db)

    _migrate(db, "upgrade", REV_005)
    return RoundTrip(
        db=db,
        tables_at_004=tables_at_004,
        users_at_004=users_at_004,
        rows_at_head=rows_at_head,
        tables_down=tables_down,
        users_down=users_down,
        rows_down=rows_down,
        revision_down=revision_down,
        violations_down=violations_down,
        integrity_down=integrity_down,
        rows_again=_rows(db),
        tables_again=_tables(db),
        new_columns_again=_new_user_columns(db),
        revision_again=_revision(db),
        violations_again=_violations(db),
    )


# =============================================================================
# 1. THE REVISION
# =============================================================================


def test_revision_005_sits_on_004_and_the_chain_keeps_one_head() -> None:
    """Contract 1: ``005_accounts_invites`` exists in ``005_accounts_invites.py``, fits ``version_num``, revises 004; one head.

    The head is not named: the next migrations go on top, and a test that names the head turns red for a change that is
    correct.
    """
    print_section("Contract 1: revision 005_accounts_invites")
    scripts = _scripts()
    revisions = {script.revision: script for script in scripts.walk_revisions()}

    assert REV_005 in revisions, f"revision {REV_005} not found; the chain has {sorted(revisions)}"
    script = revisions[REV_005]
    assert len(script.revision) <= 32, f"{script.revision!r} is {len(script.revision)} characters: alembic_version.version_num is VARCHAR(32)"
    assert script.down_revision == REV_004, f"{REV_005} must revise {REV_004}, revises {script.down_revision!r}"
    assert Path(script.path).name == f"{REV_005}.py", f"the revision id is the file name without .py, found in {Path(script.path).name}"
    heads = scripts.get_heads()
    assert len(heads) == 1, f"the chain must not fork: {len(heads)} heads {heads}"
    print_success(f"{REV_005} revises {REV_004}; one head ({heads[0]})")


# =============================================================================
# 2. A NEW DATABASE AT HEAD
# =============================================================================


def test_a_new_database_at_head_gives_users_the_three_columns(fresh_head: Path) -> None:
    """Contract 2: ``users`` has ``session_version INTEGER NOT NULL``, ``email_verified_at DATETIME`` and ``last_seen_version VARCHAR(40)``, nullable."""
    print_section("Contract 2: the three columns of users")
    _assert_includes_005(fresh_head)
    columns = _table_info(fresh_head, "users")

    missing = sorted(set(NEW_USER_COLUMNS) - set(columns))
    assert not missing, f"users lacks {missing}"
    found = {name: (columns[name].type.upper(), columns[name].not_null) for name in NEW_USER_COLUMNS}
    assert found == {name: (declared, not_null) for name, (declared, not_null, _value) in NEW_USER_COLUMNS.items()}
    print_success("users: session_version, email_verified_at, last_seen_version")


def test_a_user_inserted_without_the_new_columns_gets_their_defaults(fresh_head: Path, tmp_path: Path) -> None:
    """Contract 2: a user written without the three columns reads back 0 (an integer) / NULL / NULL; ``session_version`` refuses NULL.

    What every user an older code path creates, and every existing user, gets: the defaults are behaviour, not DDL text.
    """
    print_section("Contract 2: the defaults of the new user columns")
    db = _copy(fresh_head, tmp_path / "app.db")
    _assert_includes_005(db)

    with _foreign_keys_on(db) as conn:
        user_id = _insert_user(conn, "defaults")
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError, match=r"users\.session_version"):
            conn.execute("UPDATE users SET session_version = NULL WHERE id = ?", (user_id,))

    assert _new_user_columns(db) == {user_id: EXISTING_USER_VALUES}
    print_success("a user written without them gets 0 / NULL / NULL")


def test_account_tokens_has_its_columns(fresh_head: Path) -> None:
    """Contract 2: ``account_tokens`` has exactly its twelve columns; ``id`` is the ``INTEGER PRIMARY KEY``; NOT NULL where the contract says."""
    print_section("Contract 2: the columns of account_tokens")
    _assert_includes_005(fresh_head)
    columns = _table_info(fresh_head, "account_tokens")

    assert set(columns) == TOKEN_COLUMNS, f"missing: {sorted(TOKEN_COLUMNS - set(columns))}, unexpected: {sorted(set(columns) - TOKEN_COLUMNS)}"
    assert [name for name, column in columns.items() if column.primary_key] == ["id"]
    assert columns["id"].type.upper() == "INTEGER", f"id must be an INTEGER PRIMARY KEY (the rowid), is {columns['id'].type}"
    assert {name for name in TOKEN_NOT_NULL | TOKEN_NULLABLE if columns[name].not_null} == TOKEN_NOT_NULL
    print_success("account_tokens: 12 columns, NOT NULL on purpose, token_hash, grants_admin, created_at, expires_at")


def test_account_tokens_points_at_users_with_the_declared_actions(fresh_head: Path) -> None:
    """Contract 2: ``user_id`` → ``users.id`` ON DELETE CASCADE; ``created_by_user_id`` and ``consumed_by_user_id`` → ``users.id`` ON DELETE SET NULL."""
    print_section("Contract 2: the foreign keys of account_tokens")
    _assert_includes_005(fresh_head)

    assert _foreign_keys(fresh_head, "account_tokens") == TOKEN_FOREIGN_KEYS
    print_success("account_tokens: CASCADE from its owner, SET NULL from its creator and its consumer")


def test_account_tokens_has_its_indexes_and_named_constraints(fresh_head: Path) -> None:
    """Contract 2: two plain indexes, on ``(purpose, expires_at)`` and on ``user_id``; ``token_hash`` unique as ``uq_account_tokens_token_hash``; ``ck_account_tokens_purpose``."""
    print_section("Contract 2: the indexes and constraints of account_tokens")
    _assert_includes_005(fresh_head)
    indexes = _index_list(fresh_head, "account_tokens")

    found = {name: (unique, columns) for name, (unique, _origin, columns) in indexes.items() if name in TOKEN_INDEXES}
    assert found == {name: (False, columns) for name, columns in TOKEN_INDEXES.items()}, f"indexes of account_tokens: {indexes}"
    engine = create_engine(f"sqlite:///{fresh_head}", poolclass=NullPool)
    try:
        inspector = inspect(engine)
        unique = {constraint["name"]: tuple(constraint["column_names"]) for constraint in inspector.get_unique_constraints("account_tokens")}
        unique |= {index["name"]: tuple(index["column_names"]) for index in inspector.get_indexes("account_tokens") if index["unique"]}
        checks = {check["name"] for check in inspector.get_check_constraints("account_tokens")}
    finally:
        engine.dispose()
    assert unique.get(TOKEN_UNIQUE) == ("token_hash",), f"named unique constraints and indexes of account_tokens: {unique}"
    assert TOKEN_CHECK in checks, f"check constraints of account_tokens: {sorted(name or '<unnamed>' for name in checks)}"
    print_success("account_tokens: its two indexes, its UNIQUE and its CHECK, by name")


@pytest.mark.parametrize("purpose", ["magic_link", "INVITE", ""])
def test_the_purpose_check_refuses_an_unknown_purpose(fresh_head: Path, tmp_path: Path, purpose: str) -> None:
    """Contract 2: with foreign keys on, ``ck_account_tokens_purpose`` refuses any other value — the enum's names included, an empty string included."""
    print_section(f"Contract 2: purpose {purpose!r} is refused")
    db = _copy(fresh_head, tmp_path / "app.db")
    _assert_includes_005(db)

    with _foreign_keys_on(db) as conn:
        with pytest.raises(sqlite3.IntegrityError, match=TOKEN_CHECK):
            _insert_token(conn, purpose, _token_hash(1))
    print_success(f"{TOKEN_CHECK} refuses {purpose!r}")


def test_the_purpose_check_accepts_the_four_purposes(fresh_head: Path, tmp_path: Path) -> None:
    """Contract 2: ``invite``, ``password_reset``, ``email_verification`` and ``admin_setup`` are stored as written."""
    print_section("Contract 2: the four purposes are accepted")
    db = _copy(fresh_head, tmp_path / "app.db")
    _assert_includes_005(db)

    with _foreign_keys_on(db) as conn:
        owner = _insert_user(conn, "owner")
        written = {_insert_token(conn, purpose, _token_hash(n), user_id=None if purpose == "invite" else owner): purpose for n, purpose in enumerate(PURPOSES, start=1)}
        conn.commit()
        stored = dict(conn.execute("SELECT id, purpose FROM account_tokens").fetchall())

    assert stored == written
    print_success("the four purposes are accepted")


def test_a_duplicate_token_hash_is_refused(fresh_head: Path, tmp_path: Path) -> None:
    """Contract 2: two tokens never share a hash, whatever their purposes: the hash is how a token is found."""
    print_section("Contract 2: token_hash is unique")
    db = _copy(fresh_head, tmp_path / "app.db")
    _assert_includes_005(db)

    with _foreign_keys_on(db) as conn:
        owner = _insert_user(conn, "owner")
        _insert_token(conn, "invite", _token_hash(7))
        conn.commit()
        with pytest.raises(sqlite3.IntegrityError, match=r"account_tokens\.token_hash"):
            _insert_token(conn, "password_reset", _token_hash(7), user_id=owner)
    print_success("a second token with the same hash is refused")


def test_grants_admin_defaults_to_false_and_is_never_null(fresh_head: Path, tmp_path: Path) -> None:
    """Contract 2: a token written without ``grants_admin`` does not grant admin; NULL is refused."""
    print_section("Contract 2: grants_admin defaults to 0")
    db = _copy(fresh_head, tmp_path / "app.db")
    _assert_includes_005(db)

    with _foreign_keys_on(db) as conn:
        token_id = _insert_token(conn, "invite", _token_hash(1))
        conn.commit()
        stored = conn.execute("SELECT grants_admin FROM account_tokens WHERE id = ?", (token_id,)).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError, match=r"account_tokens\.grants_admin"):
            _insert_token(conn, "invite", _token_hash(2), grants_admin=None)

    assert stored == 0
    print_success("grants_admin: 0 by default, never NULL")


def test_deleting_a_user_deletes_its_tokens_and_unlinks_the_others(fresh_head: Path, tmp_path: Path) -> None:
    """Contract 2: with foreign keys on, deleting a user deletes the tokens whose ``user_id`` is that user, and sets ``created_by_user_id`` / ``consumed_by_user_id`` to NULL where it created or consumed someone else's.

    Every other token and link stays as it was. The database belongs to this test alone, so the comparison is exact.
    """
    print_section("Contract 2: deleting a user")
    db = _copy(fresh_head, tmp_path / "app.db")
    _assert_includes_005(db)

    with _foreign_keys_on(db) as conn:
        gone, creator, consumer, bystander = (_insert_user(conn, name) for name in ("gone", "creator", "consumer", "bystander"))
        owned = _insert_token(conn, "password_reset", _token_hash(1), user_id=gone, created_by_user_id=creator, consumed_by_user_id=consumer, consumed_at=STAMP)
        created = _insert_token(conn, "invite", _token_hash(2), created_by_user_id=gone)
        consumed = _insert_token(conn, "invite", _token_hash(3), created_by_user_id=creator, consumed_by_user_id=gone, consumed_at=STAMP)
        unrelated = _insert_token(conn, "email_verification", _token_hash(4), user_id=bystander, created_by_user_id=creator, consumed_by_user_id=consumer, consumed_at=STAMP)
        conn.commit()
        assert set(_token_links(conn)) == {owned, created, consumed, unrelated}, "setup: the four tokens are written"

        conn.execute("DELETE FROM users WHERE id = ?", (gone,))
        conn.commit()
        links = _token_links(conn)
        users = {user_id for (user_id,) in conn.execute("SELECT id FROM users").fetchall()}

    assert links == {
        created: (None, None, None),
        consumed: (None, creator, None),
        unrelated: (bystander, creator, consumer),
    }, f"(user_id, created_by_user_id, consumed_by_user_id) by token after deleting user {gone}: {links}"
    assert users == {creator, consumer, bystander}
    assert _violations(db) == []
    print_success("its own tokens deleted, its links to the others set to NULL, nothing else touched")


# =============================================================================
# 3. MODELS AND MIGRATION AGREE
# =============================================================================


@pytest.mark.parametrize("table", ["users", "account_tokens"])
def test_the_models_and_the_migration_build_the_same_table(fresh_head: Path, created_by_models: Path, table: str) -> None:
    """Contract 3: ``create_all`` and ``alembic upgrade head`` build ``table`` alike — columns and nullability, primary key, foreign keys and their ON DELETE, indexes, unique column sets, check constraints.

    Barrier first: both have the table with its 005 columns, or the comparison would be about 1.2.
    """
    print_section(f"Contract 3: {table}, migration = models")
    migrated, modelled = _shape(fresh_head, table), _shape(created_by_models, table)
    expected_columns = set(NEW_USER_COLUMNS) if table == "users" else TOKEN_COLUMNS

    for origin, shape in (("alembic upgrade head", migrated), ("SQLModel.metadata.create_all", modelled)):
        assert shape is not None, f"barrier: {origin} has no {table} table"
        missing = sorted(expected_columns - set(shape["columns (name: nullable)"]))
        assert not missing, f"barrier: {origin} builds {table} without {missing}"

    differences = {key: {"migration": migrated[key], "models": modelled[key]} for key in migrated if migrated[key] != modelled[key]}
    assert not differences, f"{table}: the migration and the models disagree on {differences}"
    print_success(f"{table}: the migration and the models build the same table")


# Contract 3 is only as good as ``_shape``. Its "indexes (name, columns, unique)" come from SQLAlchemy's inspector, which
# skips an index on an expression, on both sides alike: a unique one is still compared, by its columns, through "unique
# column sets" (``_index_list`` reads it by its text), but a NON-unique index on an expression present on one side only,
# or the same index under two names, passes unseen. The meta-tests below (lot A-26) put such an index on one of two
# copies of ``fresh_head`` and ask ``_shape`` to see it, under "indexes (name, columns, unique)". Red until ``_shape``
# reads that key from ``_index_list`` (its CREATE INDEX indexes, origin 'c'). The copies are written, never
# ``fresh_head``.

A26_INDEXES_KEY = "indexes (name, columns, unique)"
#: An index on an expression of users, as SQLite reports its key: ``_index_list`` names it by its text.
A26_EXPRESSION = "lower(username)"
A26_PROBE_INDEX = "ix_a26_probe"


def _a26_copy(fresh_head: Path, target: Path, statement: Optional[str] = None) -> Path:
    """A copy of ``fresh_head`` at ``target``, with ``statement`` run on it and committed when given."""
    db = _copy(fresh_head, target)
    if statement is not None:
        with _connect(db) as conn:
            with conn:
                conn.execute(statement)
    return db


def _a26_differences(with_index: Path, without: Path) -> dict[str, dict[str, Any]]:
    """The keys of ``_shape(…, "users")`` that differ between the two copies, with both values."""
    shape_with, shape_without = _shape(with_index, "users"), _shape(without, "users")
    assert shape_with is not None and shape_without is not None, "barrier: both copies have a users table"
    return {key: {"with": shape_with[key], "without": shape_without[key]} for key in shape_with if shape_with[key] != shape_without.get(key)}


def test_shape_sees_an_index_on_an_expression_present_on_one_side_only(fresh_head: Path, tmp_path: Path) -> None:
    """MIG005-A26-01 — NEW, red until A-26: a NON-unique index on an expression, on one copy only, makes ``_shape`` differ under "indexes (name, columns, unique)".

    Two copies of ``fresh_head``; on one, ``CREATE INDEX ix_a26_probe ON users (lower(username))``. Barrier first: SQLite
    holds the index on that copy only (``_index_list``: non-unique, origin 'c', key ``lower(username)``). Then ``_shape``
    of users must differ between the copies, under "indexes (name, columns, unique)" alone, the probe named there on the
    copy that has it. Today the inspector skips it, "unique column sets" counts only unique indexes: the shapes are equal.
    """
    print_section("MIG005-A26-01: _shape sees a non-unique index on an expression present on one side only")
    _assert_includes_005(fresh_head)
    with_index = _a26_copy(fresh_head, tmp_path / "with" / "app.db", f"CREATE INDEX {A26_PROBE_INDEX} ON users ({A26_EXPRESSION})")
    without = _a26_copy(fresh_head, tmp_path / "without" / "app.db")
    assert _index_list(with_index, "users").get(A26_PROBE_INDEX) == (False, "c", (A26_EXPRESSION,)), f"barrier: the probe index must be on the copy: {_index_list(with_index, 'users')}"
    assert A26_PROBE_INDEX not in _index_list(without, "users"), "barrier: the other copy has no probe index"

    differences = _a26_differences(with_index, without)

    assert differences, f"red until A-26: _shape must see {A26_PROBE_INDEX} on {A26_EXPRESSION}, present on one copy only — today the inspector skips an index on an expression and 'unique column sets' counts only unique ones, so the two shapes are equal"
    assert set(differences) == {A26_INDEXES_KEY}, f"the probe must differ under {A26_INDEXES_KEY!r} alone: {differences}"
    entries = differences[A26_INDEXES_KEY]
    assert A26_PROBE_INDEX in repr(entries["with"]) and A26_PROBE_INDEX not in repr(entries["without"]), f"{A26_INDEXES_KEY!r} must name {A26_PROBE_INDEX} on the copy that has it, and only there: {entries}"
    print_success(f"_shape sees {A26_PROBE_INDEX} under {A26_INDEXES_KEY!r}")


@pytest.mark.parametrize("create", ["CREATE INDEX", "CREATE UNIQUE INDEX"], ids=["non-unique", "unique"])
def test_shape_sees_an_index_on_an_expression_under_another_name(fresh_head: Path, tmp_path: Path, create: str) -> None:
    """MIG005-A26-02 — NEW, red until A-26: the same index on an expression, under a name of its own on each copy, makes ``_shape`` differ under "indexes (name, columns, unique)".

    ``… ix_a26_probe_a ON users (lower(username))`` on one copy, ``… ix_a26_probe_b`` on the other, the same key. A model
    and a migration that named an index differently would build that. Non-unique: invisible to the inspector and to
    "unique column sets" alike. Unique: "unique column sets" holds the key on both sides, and has no names — the drift
    ``ux_users_email_lower`` could take today unseen. Barrier first: each copy holds its own name, the same key. Today the
    two shapes are equal.
    """
    print_section(f"MIG005-A26-02 ({create}): _shape sees an index on an expression under another name")
    _assert_includes_005(fresh_head)
    names = {"a": f"{A26_PROBE_INDEX}_a", "b": f"{A26_PROBE_INDEX}_b"}
    copies = {side: _a26_copy(fresh_head, tmp_path / side / "app.db", f"{create} {name} ON users ({A26_EXPRESSION})") for side, name in names.items()}
    unique = create == "CREATE UNIQUE INDEX"
    for side, name in names.items():
        other = names["b" if side == "a" else "a"]
        indexes = _index_list(copies[side], "users")
        assert indexes.get(name) == (unique, "c", (A26_EXPRESSION,)) and other not in indexes, f"barrier: copy {side} must hold {name} on {A26_EXPRESSION}, unique={unique}, and not {other}: {indexes}"

    differences = _a26_differences(copies["a"], copies["b"])

    assert differences, f"red until A-26: _shape must see that the index on {A26_EXPRESSION} is {names['a']} on one copy and {names['b']} on the other — today the two shapes are equal"
    assert set(differences) == {A26_INDEXES_KEY}, f"the names must differ under {A26_INDEXES_KEY!r} alone: {differences}"
    entries = differences[A26_INDEXES_KEY]
    assert names["a"] in repr(entries["with"]) and names["b"] in repr(entries["without"]), f"{A26_INDEXES_KEY!r} must name each copy's index: {entries}"
    print_success(f"_shape sees {names['a']} and {names['b']} under {A26_INDEXES_KEY!r}")


def test_shape_of_two_untouched_copies_is_the_same(fresh_head: Path, tmp_path: Path) -> None:
    """MIG005-A26-03 — GUARD, green today and after: two untouched copies of ``fresh_head`` have the same ``_shape`` of users, so a difference above is the index's, not the copy's."""
    print_section("MIG005-A26-03: two untouched copies, the same _shape")
    _assert_includes_005(fresh_head)
    first, second = _a26_copy(fresh_head, tmp_path / "first" / "app.db"), _a26_copy(fresh_head, tmp_path / "second" / "app.db")

    differences = _a26_differences(first, second)

    assert differences == {}, f"two copies of one database must have the same shape: {differences}"
    print_success("same _shape")


# =============================================================================
# 4. A 1.2 INSTALL UPGRADED TO HEAD
# =============================================================================


def test_a_1_2_install_is_upgraded_to_the_head(upgraded_1_2: Upgrade) -> None:
    """Contract 4: after ``alembic upgrade head`` a 1.2 install is at the head of the chain, whichever revision that is."""
    print_section("Contract 4: a 1.2 install reaches the head")
    _assert_includes_005(upgraded_1_2.db)

    assert _revision(upgraded_1_2.db) == _scripts().get_current_head()
    print_success("the 1.2 install is at head")


def test_a_1_2_install_keeps_every_row_of_every_table(upgraded_1_2: Upgrade) -> None:
    """Contract 4: every table of the 1.2 install keeps every row, ids included, read on the columns it had — ``users`` on its 1.2 columns, ``sqlite_sequence`` included."""
    print_section("Contract 4: no row of a 1.2 install changes")
    _assert_includes_005(upgraded_1_2.db)
    before, after = upgraded_1_2.rows_before, upgraded_1_2.rows_after

    changes = _row_changes(before, after, set(before) - BOOKKEEPING, columns_of=before)
    assert not changes, f"the upgrade changed rows of the 1.2 install: {changes}"
    print_success(f"{len(set(before) - BOOKKEEPING)} tables, every row as it was")


def test_a_1_2_install_gives_every_existing_user_the_defaults(upgraded_1_2: Upgrade) -> None:
    """Contract 4: every user of the 1.2 install has ``session_version`` 0 and NULL ``email_verified_at`` and ``last_seen_version``.

    No backfill: ``email_verified_at`` stays NULL for existing users (decision of the developer); what a verification
    requirement does with them is decided in the logic, not in the data.
    """
    print_section("Contract 4: existing users get 0 / NULL / NULL")
    _assert_includes_005(upgraded_1_2.db)
    columns, rows = upgraded_1_2.rows_before["users"]
    existing = {row[columns.index("id")] for row in rows}

    assert _new_user_columns(upgraded_1_2.db) == dict.fromkeys(existing, EXISTING_USER_VALUES)
    print_success(f"{len(existing)} existing users: 0 / NULL / NULL")


def test_a_1_2_install_gets_an_empty_account_tokens_and_no_violation(upgraded_1_2: Upgrade) -> None:
    """Contract 4: ``account_tokens`` exists and holds no row; ``PRAGMA foreign_key_check`` is empty."""
    print_section("Contract 4: account_tokens empty, no violation")
    _assert_includes_005(upgraded_1_2.db)

    assert "account_tokens" in upgraded_1_2.rows_after, "account_tokens is missing"
    assert upgraded_1_2.rows_after["account_tokens"][1] == []
    assert _violations(upgraded_1_2.db) == []
    print_success("account_tokens is there and empty; foreign_key_check is empty")


# =============================================================================
# 5. THE DOWNGRADE, AND BACK
# =============================================================================


def test_the_downgrade_drops_account_tokens_and_returns_to_004(round_trip: RoundTrip) -> None:
    """Contract 5: after ``alembic downgrade 004`` the tables are the 1.2 install's — ``account_tokens`` gone, no leftover of a rebuild — and the revision is 004."""
    print_section("Contract 5: the downgrade returns to 004")

    assert "account_tokens" not in round_trip.tables_down
    assert round_trip.tables_down == round_trip.tables_at_004, f"missing: {sorted(round_trip.tables_at_004 - round_trip.tables_down)}, unexpected: {sorted(round_trip.tables_down - round_trip.tables_at_004)}"
    assert round_trip.revision_down == REV_004
    print_success("account_tokens dropped, at 004")


def test_the_downgrade_drops_the_three_user_columns(round_trip: RoundTrip) -> None:
    """Contract 5: ``users`` is declared again exactly as at 004 — the three columns gone, every other column as it was."""
    print_section("Contract 5: the downgrade drops the three user columns")

    assert not set(NEW_USER_COLUMNS) & set(round_trip.users_down), f"users still has {sorted(set(NEW_USER_COLUMNS) & set(round_trip.users_down))}"
    assert round_trip.users_down == round_trip.users_at_004
    print_success("users is back to its 004 columns")


def test_the_downgrade_touches_no_other_row(round_trip: RoundTrip) -> None:
    """Contract 5: every row of every table the downgrade keeps is the row it had at head — no user lost, nothing cascaded into ``user_settings``, ``broker_user_access``, the onboarding tables, nothing unlinked in ``global_settings``.

    Read on the columns each table keeps. The downgrade ran with foreign keys on (asserted by ``_migrate``), and before it
    every one of those tables had rows pointing at users (asserted by the fixture): a rebuild of ``users`` would show here.
    """
    print_section("Contract 5: the downgrade touches no other row")
    kept = (set(round_trip.rows_down) & set(round_trip.rows_at_head)) - BOOKKEEPING

    changes = _row_changes(round_trip.rows_at_head, round_trip.rows_down, kept, columns_of=round_trip.rows_down)
    assert not changes, f"the downgrade changed rows it had no reason to touch: {changes}"
    assert CHILDREN_OF_USERS | {"users"} <= kept
    print_success(f"{len(kept)} tables, every row as it was at head")


def test_the_downgrade_leaves_no_violation(round_trip: RoundTrip) -> None:
    """Contract 5: after the downgrade ``PRAGMA foreign_key_check`` is empty and ``PRAGMA integrity_check`` answers ok."""
    print_section("Contract 5: no violation after the downgrade")

    assert round_trip.violations_down == []
    assert round_trip.integrity_down == [("ok",)]
    print_success("foreign_key_check empty, integrity_check ok")


def test_upgrading_again_brings_the_columns_back_at_their_defaults(round_trip: RoundTrip) -> None:
    """Contract 5: ``upgrade 005`` after the downgrade works: ``account_tokens`` back and empty, the three columns back at 0 / NULL / NULL for every user — the values they held are gone with the downgrade —, every other row as after the downgrade, no violation."""
    print_section("Contract 5: the round trip")
    _assert_includes_005(round_trip.db)
    users_columns, user_rows = round_trip.rows_down["users"]
    users = {row[users_columns.index("id")] for row in user_rows}

    assert round_trip.revision_again == REV_005
    assert "account_tokens" in round_trip.tables_again and round_trip.rows_again["account_tokens"][1] == []
    assert round_trip.new_columns_again == dict.fromkeys(users, EXISTING_USER_VALUES)
    changes = _row_changes(round_trip.rows_down, round_trip.rows_again, set(round_trip.rows_down) - BOOKKEEPING, columns_of=round_trip.rows_down)
    assert not changes, f"upgrading again changed rows: {changes}"
    assert round_trip.violations_again == []
    print_success("upgraded again: columns at their defaults, account_tokens empty, every other row kept")


# =============================================================================
# 6. AN INTERRUPTED UPGRADE
# =============================================================================


def test_an_upgrade_interrupted_after_its_first_alter_completes(fresh_head: Path, tmp_path: Path) -> None:
    """Contract 6: a database at 004 that already has ``session_version`` — added exactly as the migration adds it, as if a previous run had stopped after its first ``ALTER`` — upgrades to head, and ends with the ``users`` and ``account_tokens`` of a new database.

    Compared on ``PRAGMA table_info`` (by column name: a re-run may add the remaining columns in any order) and
    ``PRAGMA index_list`` with the columns of each index.
    """
    print_section("Contract 6: an interrupted upgrade completes")
    _assert_includes_005(fresh_head)
    declared = _table_info(fresh_head, "users")["session_version"]
    first_alter = f"ALTER TABLE users ADD COLUMN session_version {declared.type}{' NOT NULL' if declared.not_null else ''}{'' if declared.default is None else f' DEFAULT {declared.default}'}"

    db = tmp_path / "app.db"
    _migrate(db, "upgrade", REV_004)
    with _foreign_keys_on(db) as conn:
        conn.execute(first_alter)
        conn.commit()
    assert "session_version" in _table_info(db, "users") and _revision(db) == REV_004, "setup: the interrupted state"

    _migrate(db, "upgrade", "head")

    assert _revision(db) == _scripts().get_current_head()
    for table in ("users", "account_tokens"):
        assert _table_info(db, table) == _table_info(fresh_head, table), f"{table}: columns differ from a new database's"
        assert _index_list(db, table) == _index_list(fresh_head, table), f"{table}: indexes differ from a new database's"
    print_success("the re-run skipped session_version and completed the schema")
