"""The in-process Alembic harness of the migration tests: Alembic on one private SQLite file, and the readers of that file.

Not a test module: pytest collects ``test_*.py`` only (``pytest.ini``). ``test_migration_005_release_1_3`` and
``test_session_pragmas`` import it. It was the harness of ``test_migration_005_accounts``, which the tests of ``006`` to
``010`` imported in turn; when the 1.3 migrations became one revision (lot H-57, 19/10/2026) those files were deleted
and the harness moved here, unchanged in what it does.

Safety. Every database is a file its caller owns, under ``tmp_path``. ``_migrate`` runs Alembic in this process with
``cmd_opts.x = ["sqlalchemy.url=…"]``: without it ``backend/alembic/env.py`` falls back to the configured database, the
lane's. No ini file either: ``env.py`` would hand it to ``logging.config.fileConfig`` and reconfigure this process's
logging. While Alembic runs, a connect listener refuses any connection to another file.

Fidelity. Production migrates in a process that imports ``backend.app.db.session``, whose connect listener turns
foreign keys on, and only with them on does «nothing cascades» mean anything. This module imports it (through
``backend.app.db.base``) before it registers a listener of its own, so that its listener reads what production's set:
``_migrate`` asserts ``PRAGMA foreign_keys`` 1 on every connection of every step. The readers use plain ``sqlite3``, the
way a real install is read, never the models; ``_create_all`` is the one exception, and its point.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any, NamedTuple, Optional

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.pool import NullPool

from backend.app.config import PROJECT_ROOT
from backend.app.db.base import SQLModel  # imports every model, and backend.app.db.session with its PRAGMA listener

ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "backend" / "alembic"

#: Every row of every table, with the table's columns, as ``_rows`` reads them: ``{table: (columns, rows)}``.
Rows = dict[str, tuple[list[str], list[tuple[Any, ...]]]]


class Declared(NamedTuple):
    """One column as ``PRAGMA table_info`` reports it."""

    type: str
    not_null: bool
    default: Optional[str]
    primary_key: bool


# =============================================================================
# ALEMBIC — in this process, on a private file only
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
    """The revisions of ``backend/alembic/versions``, read without a database."""
    return ScriptDirectory.from_config(_alembic_config())


def _known(revision: str) -> bool:
    """Whether Alembic finds ``revision`` among the scripts."""
    return revision in {script.revision for script in _scripts().walk_revisions()}


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
# READERS — the private databases, through plain sqlite3
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
    brackets, cut at its own commas. Each key is read in lower case, without spaces, names without their quotes or
    brackets (a string keeps its ``'…'``): ``LOWER( "email" )`` is the key ``lower(email)``, a spelling and not another
    index. Quoted text is not syntax: a comma or a bracket inside a string or a quoted name cuts nothing.
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
    """Every row of every table, ``sqlite_sequence`` and ``alembic_version`` included, with the table's columns: ``{table: (columns, rows)}``."""
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
        if table not in actual or table not in expected:
            changes[table] = "the table is only on one side"
            continue
        columns = columns_of[table][0]
        wanted, found = _on_columns(expected, table, columns), _on_columns(actual, table, columns)
        if wanted != found:
            missing = [row for row in wanted if row not in found]
            unexpected = [row for row in found if row not in wanted]
            changes[table] = f"{len(missing)} row(s) missing or changed, e.g. {missing[:2]}; {len(unexpected)} unexpected, e.g. {unexpected[:2]}"
    return changes


# =============================================================================
# THE MODELS — what create_all builds, and how a table is compared
# =============================================================================


def _create_all(db: Path) -> Path:
    """A new database at ``db`` built by ``SQLModel.metadata.create_all``, as the service suites build theirs."""
    db.parent.mkdir(parents=True, exist_ok=True)
    assert not db.exists(), f"setup: {db} already exists"
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        SQLModel.metadata.create_all(engine)
    finally:
        engine.dispose()
    return db


def _collapsed_whitespace(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


def _shape(db: Path, table: str) -> Optional[dict[str, Any]]:
    """What ``table`` is, read back from SQLite, as a migration and the models are compared on it. ``None`` when the table does not exist.

    A primary-key column counts as NOT NULL whatever its declaration says: SQLite gives a NULL ``INTEGER PRIMARY KEY`` a
    rowid, and ``001_initial`` declares ``users.id`` without NOT NULL where ``create_all`` writes it. Indexes and
    uniqueness are read from ``PRAGMA index_list`` (``_index_list``), where a key that is an expression counts by its
    text: the indexes are those written with ``CREATE INDEX`` (origin ``c``), by name, keys and uniqueness; uniqueness is
    the set of column tuples that are unique, whether by a constraint or by an index. SQLAlchemy's inspector would leave
    an expression index such as ``ux_users_email_lower`` out of ``get_indexes``, on both sides alike, with the warning
    "Skipped unsupported reflection of expression-based index": a non-unique one on one side only, or under another
    name, would pass unseen (lot A-26).
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


def _full_shape(db: Path, table: str) -> Optional[dict[str, Any]]:
    """``_shape``, plus what it does not compare: declared types, unique constraint names, CHECK texts (whitespace collapsed).

    For tables whose unique constraints are all named, or all unnamed: their names are sorted together.
    """
    shape = _shape(db, table)
    if shape is None:
        return None
    engine = create_engine(f"sqlite:///{db}", poolclass=NullPool)
    try:
        inspector = inspect(engine)
        shape["column types"] = {column["name"]: str(column["type"]) for column in inspector.get_columns(table)}
        shape["unique constraints"] = sorted((constraint["name"], tuple(constraint["column_names"])) for constraint in inspector.get_unique_constraints(table))
        shape["check constraints (name: sql)"] = sorted((check["name"], _collapsed_whitespace(check["sqltext"])) for check in inspector.get_check_constraints(table))
    finally:
        engine.dispose()
    return shape
