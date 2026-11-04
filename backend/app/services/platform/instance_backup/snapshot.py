"""The consistent copy of the database for a backup: ``VACUUM INTO``, never the live file.

SQLite writes the copy from one read transaction, so it is the database as of one instant, whatever the server writes
meanwhile; in WAL mode the copy blocks no writer (the scheduler keeps refreshing prices, a user keeps saving). The copy
is a standalone file in rollback-journal mode, with nothing beside it. It is then described on its own: integrity, foreign
keys, rows per table and the Alembic revision it is at.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

#: Matches PRAGMA busy_timeout=30000 in backend/app/db/session.py: the copy waits for a writer as long as the app does.
_BUSY_TIMEOUT_MS = 30_000
_CHUNK = 1024 * 1024
#: How many lines of a failed integrity check the description keeps.
_INTEGRITY_LINES = 5


class SnapshotError(RuntimeError):
    """The database cannot be copied: it is missing, or the copy's place is taken."""


@dataclass(frozen=True)
class DatabaseDescription:
    """What a database file holds, read on its own: the facts the manifest records and a restore compares."""

    size: int
    sha256: str
    integrity_check: str
    foreign_key_violations: int
    tables: dict[str, int]
    alembic_revision: str | None


def snapshot_database(source: Path, target: Path) -> DatabaseDescription:
    """Copy the database at ``source`` into the new file ``target`` with ``VACUUM INTO``, and describe the copy."""
    if not source.is_file():
        raise SnapshotError(f"No database at {source}")
    if target.exists():
        raise SnapshotError(f"{target} already exists")
    with closing(sqlite3.connect(str(source), timeout=_BUSY_TIMEOUT_MS / 1000)) as conn:
        conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        conn.execute("VACUUM INTO ?", (str(target),))
    return describe_database(target)


def describe_database(path: Path) -> DatabaseDescription:
    """Describe the database file ``path``, opened read-only."""
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        # A schema's functions only if innocuous: the database may be an archive's (lot B-28).
        conn.execute("PRAGMA trusted_schema=OFF")
        integrity = [str(row[0]) for row in conn.execute("PRAGMA integrity_check").fetchmany(_INTEGRITY_LINES)]
        violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
        names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        tables = {name: conn.execute(f"SELECT count(*) FROM {_identifier(name)}").fetchone()[0] for name in names}
        revision = _alembic_revision(conn) if "alembic_version" in tables else None
    size, sha256 = file_digest(path)
    return DatabaseDescription(
        size=size,
        sha256=sha256,
        integrity_check="ok" if integrity == ["ok"] else "; ".join(integrity),
        foreign_key_violations=violations,
        tables=tables,
        alembic_revision=revision,
    )


def _identifier(name: str) -> str:
    """``name`` as an SQL identifier: in double quotes, a quote it holds doubled (an archive's tables may be named
    anything)."""
    return '"' + name.replace('"', '""') + '"'


def _alembic_revision(conn: sqlite3.Connection) -> str | None:
    """The revision ``alembic_version`` records; ``None`` unless it records exactly one."""
    rows = conn.execute("SELECT version_num FROM alembic_version").fetchall()
    return str(rows[0][0]) if len(rows) == 1 else None


def file_digest(path: Path) -> tuple[int, str]:
    """The size and the SHA-256 of a file, read in chunks."""
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()
