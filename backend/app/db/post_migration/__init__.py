"""Post-migration fixes: ordered repairs that run after ``alembic upgrade head``.

Some repairs cannot be Alembic migrations. Rebuilding a referenced table is one: the Alembic
process imports ``backend.app.db.session``, whose engine listener turns foreign keys on, and with
foreign keys on, dropping a table referenced with ``ON DELETE CASCADE`` empties the tables that
point at it. A post-migration fix runs on a direct ``sqlite3`` connection instead, after the
migrations, and only when it finds the anomaly it corrects:

1. ``PRAGMA integrity_check``: a damaged database is never touched;
2. every fix ``detect``s, in order; nothing found, nothing written;
3. the WAL is checkpointed and a backup copy made next to the database;
4. each fix with an anomaly runs in one transaction with foreign keys off (switched outside the
   transaction, the only place SQLite allows it), then verifies: no ``foreign_key_check`` row it did not
   find there (one the database already held stays, and is logged once), the row count of every table
   unchanged but for the changes the fix declares (``row_count_changes``), its own checks;
5. all verified: the backup is deleted. Any error: rollback, the backup is kept and logged.

Every worker of a multi-worker server runs them as it starts, so runs take turns: each holds an
exclusive lock on ``<db file name>.post-migration.lock``, beside the database, from the integrity
check to the cleanup, dry runs included. The first converts; the next find nothing to do.

The server runs them at startup (``backend.app.services.platform.database_bootstrap.run_post_migration_fixes_at_startup``, which
never lets an error stop the startup); ``python -m backend.app.db.post_migration`` runs them with
the server stopped. Plan ``34_accountAndIdReuse`` §2.3.
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - not POSIX: runs are not serialised there
    fcntl = None  # type: ignore[assignment]

from backend.app.config import PROJECT_ROOT, get_settings
from backend.app.db.post_migration.autoincrement import AUTOINCREMENT_TABLES, AutoincrementFix
from backend.app.db.post_migration.base import FixContext, PostMigrationError, PostMigrationFix, PostMigrationReport
from backend.app.db.post_migration.event_types import EventTypesFix
from backend.app.db.post_migration.orphan_pair_halves import OrphanPairHalfFix
from backend.app.logging_config import get_logger

__all__ = ["AUTOINCREMENT_TABLES", "FIXES", "PostMigrationReport", "configured_sqlite_path", "run_post_migration_fixes"]

logger = get_logger(__name__)

# Seconds a fix waits for another connection to release the database before giving up.
_BUSY_TIMEOUT = 10.0


def configured_sqlite_path() -> Optional[Path]:
    """The SQLite file the server uses (``DATABASE_URL``), or ``None`` for another database."""
    db_url = get_settings().DATABASE_URL
    if not db_url.startswith("sqlite:///"):
        return None
    path = Path(db_url.replace("sqlite:///", "", 1))
    return path if path.is_absolute() else PROJECT_ROOT / path


def _integrity_ok(conn: sqlite3.Connection) -> bool:
    """``PRAGMA integrity_check`` answers a single ``ok`` row on a sound database."""
    return conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]


def _quoted(name: str) -> str:
    """``name`` as an SQL identifier, in double quotes with its own doubled (B-36): a restore's check runs these fixes on
    an archive's database, whose tables may be named anything."""
    return '"' + name.replace('"', '""') + '"'


def _row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    names = [name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {name: conn.execute(f"SELECT count(*) FROM {_quoted(name)}").fetchone()[0] for name in names}


def _fk_violations(conn: sqlite3.Connection) -> set[tuple]:
    """What ``PRAGMA foreign_key_check`` reports: one ``(table, rowid, parent table, foreign key index)`` per broken reference."""
    return {tuple(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()}


def _expected_counts(counts: dict[str, int], changes: dict[str, int]) -> dict[str, int]:
    """The row count each table must have after a fix: the one it has now, plus the change the fix declares."""
    return {**counts, **{name: counts.get(name, 0) + delta for name, delta in changes.items()}}


def _common_problems(conn: sqlite3.Connection, counts_expected: dict[str, int], violations_before: set[tuple]) -> list[str]:
    """What a fix broke: a foreign key violation that was not there before it (one already there stays, and is not
    the fix's), or a table whose row count is not the expected one (unchanged, but for the rows the fix declares)."""
    problems = [f"foreign_key_check: {row}" for row in sorted(_fk_violations(conn) - violations_before, key=repr)]
    counts_after = _row_counts(conn)
    if counts_after != counts_expected:
        changed = sorted(name for name in set(counts_expected) | set(counts_after) if counts_expected.get(name) != counts_after.get(name))
        problems.append("row counts not as expected: " + ", ".join(f"{name} (expected {counts_expected.get(name)}, found {counts_after.get(name)})" for name in changed))
    return problems


def _backup(conn: sqlite3.Connection, db_path: Path, fix_ids: list[str], timestamp: str) -> Path:
    """Checkpoint the WAL, then copy the database next to itself with SQLite's backup API."""
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    target = db_path.with_name(f"{db_path.name}.pre-{'-'.join(fix_ids)}-{timestamp}.bak")
    copy = sqlite3.connect(str(target))
    try:
        conn.backup(copy)
    finally:
        copy.close()
    return target


def _apply_one(conn: sqlite3.Connection, fix: PostMigrationFix, anomaly: Any, ctx: FixContext) -> bool:
    """One fix, one transaction: prepare outside it, apply and verify inside it, finish after it."""
    try:
        fix.prepare(anomaly, ctx)
    except Exception as exc:  # noqa: BLE001 — every failure is reported, never raised
        ctx.report.errors.append(f"{fix.fix_id}: {exc}")
        fix.finish(ctx, success=False)
        return False

    counts_before = _row_counts(conn)
    violations_before = _fk_violations(conn)
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        # What the fix declares it deletes or adds: asked here, so that a fix failing to say is reported, not raised.
        counts_expected = _expected_counts(counts_before, fix.row_count_changes(anomaly, ctx))
        conn.execute("BEGIN IMMEDIATE")
        fix.apply(conn, anomaly, ctx)
        problems = fix.verify(conn, anomaly, ctx) + _common_problems(conn, counts_expected, violations_before)
        if problems:
            raise PostMigrationError("; ".join(problems))
        conn.execute("COMMIT")
    except Exception as exc:  # noqa: BLE001 — rolled back and reported, never raised
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        ctx.report.errors.append(f"{fix.fix_id}: {exc}")
        fix.finish(ctx, success=False)
        return False
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
    fix.finish(ctx, success=True)
    return True


# The fixes, in the order they run. A new fix is appended, never inserted before an older one.
FIXES: tuple[PostMigrationFix, ...] = (AutoincrementFix(), OrphanPairHalfFix(), EventTypesFix())


def _apply_pending(conn: sqlite3.Connection, pending: list[tuple[PostMigrationFix, Any]], ctx: FixContext) -> None:
    """Back up, apply each pending fix in order, then delete the backup — or keep it if anything failed.

    The closing log line says how long it all took (``seconds``): on a big database, the first start
    after an upgrade is slower once.
    """
    report = ctx.report
    started = time.monotonic()
    try:
        backup = _backup(conn, ctx.db_path, [fix.fix_id for fix, _ in pending], ctx.timestamp)
    except Exception as exc:  # noqa: BLE001 — no backup, no fix
        for fix, _ in pending:
            report.outcomes[fix.fix_id] = "failed"
        report.errors.append(f"backup: {exc}")
        logger.warning("Post-migration fixes skipped: the backup copy could not be made", db_path=str(ctx.db_path), error=str(exc))
        return

    # Broken references the database already holds are not the fixes' to judge: each fix is checked for the ones it adds.
    existing = _fk_violations(conn)
    if existing:
        logger.warning("Foreign key violations already in the database, left as they are", db_path=str(ctx.db_path), count=len(existing), violations=[list(row) for row in sorted(existing, key=repr)[:20]])

    for fix, anomaly in pending:
        if not _apply_one(conn, fix, anomaly, ctx):
            report.outcomes[fix.fix_id] = "failed"
            break
        report.outcomes[fix.fix_id] = "applied"

    if report.failed:
        report.backup_path = backup
        logger.warning("Post-migration fix failed: the database was left as it was", db_path=str(ctx.db_path), backup=str(backup), errors=report.errors, seconds=round(time.monotonic() - started, 3))
    else:
        backup.unlink(missing_ok=True)
        logger.info("Post-migration fixes applied and verified", db_path=str(ctx.db_path), fixes=[fix.fix_id for fix, _ in pending], seconds=round(time.monotonic() - started, 3))


@contextmanager
def _exclusive_run(db_path: Path) -> Iterator[None]:
    """Hold an exclusive lock on ``<db file name>.post-migration.lock`` until the block ends; wait for it if another run holds it.

    Taken before the database is opened, so a waiting run holds no SQLite lock. The file stays on
    disk: deleting it while another run waits on it would let a third lock a new file at once. It is
    opened with ``O_NOFOLLOW`` and created ``0o600`` (Z-28): a symbolic link in its place raises
    ``OSError`` before anything runs, and nothing behind the link is created or locked.
    """
    if fcntl is None:  # pragma: no cover - not POSIX
        yield
        return
    fd = os.open(db_path.with_name(f"{db_path.name}.post-migration.lock"), os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def run_post_migration_fixes(db_path: Path, data_dir: Optional[Path] = None, *, dry_run: bool = False) -> PostMigrationReport:
    """Run every registered fix, in order, on the SQLite database at ``db_path``, one run at a time (``_exclusive_run``)."""
    report = PostMigrationReport()
    db_path = Path(db_path)
    if not db_path.is_file():
        return report

    with _exclusive_run(db_path):
        ctx = FixContext(db_path=db_path, data_dir=Path(data_dir) if data_dir is not None else None, timestamp=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"), report=report)
        conn = sqlite3.connect(str(db_path), isolation_level=None, timeout=_BUSY_TIMEOUT)
        try:
            # Before anything else, as every connection to a restore's copy (B-28, B-37): the schema of an archive's
            # database reaches no function that is not harmless. LibreFolio's own holds only tables and indexes.
            conn.execute("PRAGMA trusted_schema=OFF")
            if not _integrity_ok(conn):
                report.integrity_ok = False
                report.errors.append("integrity_check did not answer ok: no fix applied")
                logger.warning("Post-migration fixes skipped: the database fails its integrity check", db_path=str(db_path))
                return report

            pending = []
            for fix in FIXES:
                anomaly = fix.detect(conn, ctx)
                report.outcomes[fix.fix_id] = "clean" if anomaly is None else "would_apply"
                if anomaly is not None:
                    pending.append((fix, anomaly))
            if pending and not dry_run:
                _apply_pending(conn, pending, ctx)
            return report
        finally:
            conn.close()
