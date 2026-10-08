"""The first post-migration fix: ``AUTOINCREMENT`` on the tables whose ids leave the backend.

Without ``AUTOINCREMENT`` SQLite gives a new row ``max(id) + 1``: delete the newest broker and the
next one takes its id, and with it whatever still points at that id outside the database — a
saved URL, a benchmark in localStorage, the ``broker_<id>`` folder of the uploaded reports.
New databases get ``AUTOINCREMENT`` from ``001_initial.py``; this fix converts existing ones.

Each table is rebuilt from its CURRENT ``CREATE TABLE`` with one change only —
``id INTEGER PRIMARY KEY`` becomes ``id INTEGER PRIMARY KEY AUTOINCREMENT`` — so whatever later
migrations added stays. The old table is renamed aside with ``legacy_alter_table`` on (so the
foreign keys of the other tables keep naming it), the new one is created from that exact text,
the rows are copied, the old table dropped and the indexes recreated: the stored DDL is the
original plus ``AUTOINCREMENT``, nothing else. (Creating ``new_X`` and renaming it would make
SQLite store a quoted name.) Any other shape of the id column stops the fix before anything is
touched: it never guesses. Ids are copied as they are, and SQLite then starts the sequence after
the highest one.

When ``brokers`` is converted, the ``broker_reports/<status>/broker_<n>`` folders whose broker no
longer exists are quarantined first (renamed in place, atomically, out of the listing's
``broker_*`` glob), deleted once the fix is verified, renamed back if it fails: the first broker
created after the conversion may reuse ``<n>`` once, and must not inherit them.
Plan ``34_accountAndIdReuse`` §2.3, decisions D1 and D4.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.app.db.post_migration.base import FixContext, PostMigrationError, PostMigrationFix
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

# The tables whose ids leave the backend and stay saved (URLs, localStorage, BRIM sidecars,
# exports): an id reused after a deletion would silently point at another row.
AUTOINCREMENT_TABLES: tuple[str, ...] = ("users", "brokers", "assets", "transactions", "fx_conversion_routes", "asset_events")

_ID_PRIMARY_KEY = re.compile(r"\bid\s+INTEGER\s+PRIMARY\s+KEY\b(?!\s+AUTOINCREMENT)", re.IGNORECASE)
# Only the name the app writes (``broker_<id>``, no leading zero): anything else is not ours to judge.
_BROKER_DIR = re.compile(r"broker_([1-9]\d*)")
_STATUS_FOLDERS = ("uploaded", "parsed", "failed")
_OLD_SUFFIX = "__pre_autoincrement"


@dataclass
class _Anomaly:
    tables: list[str]
    orphan_dirs: list[Path] = field(default_factory=list)


def _table_sql(conn: sqlite3.Connection, table: str) -> Optional[str]:
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone()
    return row[0] if row else None


def _index_sqls(conn: sqlite3.Connection, table: str) -> list[str]:
    return [sql for (sql,) in conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? AND sql IS NOT NULL ORDER BY name", (table,))]


def _normalised(sql: str) -> str:
    return " ".join(sql.split())


def _autoincrement_sql(table: str, sql: str) -> str:
    """The table's own DDL with ``AUTOINCREMENT`` on its id; anything else is refused, never guessed."""
    converted, count = _ID_PRIMARY_KEY.subn(lambda match: f"{match.group(0)} AUTOINCREMENT", sql)
    if count != 1:
        raise PostMigrationError(f"{table}: the id column is not a single 'id INTEGER PRIMARY KEY' ({count} found); left as it is")
    return converted


class AutoincrementFix(PostMigrationFix):
    fix_id = "autoincrement"

    def detect(self, conn: sqlite3.Connection, ctx: FixContext) -> Optional[_Anomaly]:
        tables = [table for table in AUTOINCREMENT_TABLES if (sql := _table_sql(conn, table)) is not None and "AUTOINCREMENT" not in sql.upper()]
        if not tables:
            return None
        orphans = self._orphan_broker_dirs(conn, ctx) if "brokers" in tables else []
        ctx.report.orphan_broker_dirs = [str(path.relative_to(ctx.data_dir.resolve())) for path in orphans] if ctx.data_dir else []
        return _Anomaly(tables=tables, orphan_dirs=orphans)

    @staticmethod
    def _orphan_broker_dirs(conn: sqlite3.Connection, ctx: FixContext) -> list[Path]:
        if ctx.data_dir is None:
            return []
        root = ctx.data_dir.resolve()
        if not ctx.db_path.resolve().is_relative_to(root):
            logger.warning("Orphan broker folders left alone: the database is not under the data dir", db_path=str(ctx.db_path), data_dir=str(ctx.data_dir))
            return []
        live = {broker_id for (broker_id,) in conn.execute("SELECT id FROM brokers")}
        orphans = []
        for status in _STATUS_FOLDERS:
            folder = root / "broker_reports" / status
            if not folder.is_dir():
                continue
            for entry in sorted(folder.iterdir()):
                match = _BROKER_DIR.fullmatch(entry.name)
                if match and entry.is_dir() and not entry.is_symlink() and int(match.group(1)) not in live:
                    orphans.append(entry)
        return orphans

    def prepare(self, anomaly: _Anomaly, ctx: FixContext) -> None:
        moved: list[tuple[Path, Path]] = []
        ctx.state["quarantine"] = moved
        for original in anomaly.orphan_dirs:
            quarantined = original.with_name(f".quarantine-{self.fix_id}-{ctx.timestamp}-{original.name}")
            original.rename(quarantined)
            moved.append((original, quarantined))
        if moved:
            logger.info("Orphan broker folders quarantined", count=len(moved), folders=[str(original) for original, _ in moved])

    def apply(self, conn: sqlite3.Connection, anomaly: _Anomaly, ctx: FixContext) -> None:
        plan = {}
        for table in anomaly.tables:  # every table is checked before any is touched
            sql = _table_sql(conn, table)
            if _table_sql(conn, f"{table}{_OLD_SUFFIX}") is not None:
                raise PostMigrationError(f"{table}: a table named {table}{_OLD_SUFFIX} already exists; left as it is")
            plan[table] = (sql, _index_sqls(conn, table), _autoincrement_sql(table, sql))
        ctx.state["before"] = plan
        conn.execute("PRAGMA legacy_alter_table = ON")
        try:
            for table, (_, indexes, new_sql) in plan.items():
                conn.execute(f'ALTER TABLE "{table}" RENAME TO "{table}{_OLD_SUFFIX}"')
                conn.execute(new_sql)
                conn.execute(f'INSERT INTO "{table}" SELECT * FROM "{table}{_OLD_SUFFIX}"')
                conn.execute(f'DROP TABLE "{table}{_OLD_SUFFIX}"')
                for index_sql in indexes:
                    conn.execute(index_sql)
        finally:
            conn.execute("PRAGMA legacy_alter_table = OFF")

    def verify(self, conn: sqlite3.Connection, anomaly: _Anomaly, ctx: FixContext) -> list[str]:
        problems = []
        for table, (_, indexes, new_sql) in ctx.state.get("before", {}).items():
            if _normalised(_table_sql(conn, table) or "") != _normalised(new_sql):
                problems.append(f"{table}: the rebuilt DDL differs from the original plus AUTOINCREMENT")
            if sorted(map(_normalised, _index_sqls(conn, table))) != sorted(map(_normalised, indexes)):
                problems.append(f"{table}: its indexes differ after the rebuild")
            highest = conn.execute(f'SELECT max(id) FROM "{table}"').fetchone()[0]
            sequence = conn.execute("SELECT seq FROM sqlite_sequence WHERE name = ?", (table,)).fetchone()
            if highest is not None and (sequence is None or sequence[0] < highest):
                problems.append(f"{table}: sqlite_sequence is behind the highest id")
        return problems

    def finish(self, ctx: FixContext, *, success: bool) -> None:
        for original, quarantined in ctx.state.get("quarantine", []):
            try:
                if success:
                    shutil.rmtree(quarantined)
                else:
                    quarantined.rename(original)
            except OSError as exc:
                ctx.report.errors.append(f"{self.fix_id}: {quarantined}: {exc}")
                logger.warning("Orphan broker folder left in quarantine", folder=str(quarantined), error=str(exc))
