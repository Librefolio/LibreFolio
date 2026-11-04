"""An on-demand check of the live database file (B-56): the checks a restore runs on a backup's copy, read only.

A restore by hand does not pass through the check of an archive, and a damage the start does not see (a text that is
not UTF-8, a spoiled page) shows only when a page reads those rows. ``./dev.py db check --integrity`` (also
``python -m backend.app.services.platform.db_integrity_check``) runs, on the file and never at the start:

- ``PRAGMA integrity_check`` and ``PRAGMA foreign_key_check`` (``describe_database`` of the backup, the same function);
- the text that is not UTF-8, by table and rowid, never by content (``undecodable_tables`` of the restore's scan);
- the Alembic revision against this LibreFolio's migrations (``_revision_plan`` of the restore).

The file is opened ``mode=ro``: nothing is written, not even a journal. Exit 0: no problem; 1: some; 2: not readable.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

from backend.app.services.platform.instance_backup.snapshot import describe_database
from backend.app.services.platform.instance_backup.staging import StagingError, _revision_plan, undecodable_tables

#: How many rowids of a table the report names; more than that is only counted by the table being listed.
_ROWIDS_SHOWN = 20
_ROWID_NAMES = ("rowid", "_rowid_", "oid")

RevisionStatus = Literal["head", "older", "unknown", "missing", "unreadable"]

_STATUS_OF_ERROR: dict[str, RevisionStatus] = {"revision_missing": "missing", "revision_unknown": "unknown", "head_unknown": "unreadable"}


@dataclass(frozen=True)
class IntegrityReport:
    """What the check found in one database file."""

    integrity_check: str
    foreign_key_violations: int
    #: A table holding a text that is not UTF-8 -> the rowids of its rows that do (empty for a table without a rowid).
    undecodable: dict[str, list[int]]
    revision: Optional[str]
    revision_status: RevisionStatus
    tables: dict[str, int] = field(default_factory=dict)

    def problems(self) -> list[str]:
        """One line per problem; an older revision is none (the start upgrades it)."""
        lines = []
        if self.integrity_check != "ok":
            lines.append(f"integrity_check: {self.integrity_check}")
        if self.foreign_key_violations:
            lines.append(f"foreign_key_check: {self.foreign_key_violations} row(s) refer to a row that is not there")
        for table, rowids in sorted(self.undecodable.items()):
            where = f"rowid {', '.join(str(rowid) for rowid in rowids)}" if rowids else "rows without a rowid"
            lines.append(f"text that is not UTF-8 in table {table}: {where}")
        if self.revision_status == "unknown":
            lines.append("the recorded Alembic revision is not one of this LibreFolio's: it comes from a newer one, or not from this one")
        elif self.revision_status == "missing":
            lines.append("the database records no single Alembic revision")
        elif self.revision_status == "unreadable":
            lines.append("this LibreFolio's migration scripts cannot be read: the revision was not checked")
        return lines


def check_database(path: Path) -> IntegrityReport:
    """Run the checks on the SQLite file ``path``; ``sqlite3.Error`` if it cannot be read."""
    description = describe_database(path)
    undecodable = {table: _undecodable_rowids(path, table) for table in undecodable_tables(path)}
    try:
        status: RevisionStatus = "head" if _revision_plan(description.alembic_revision)[0] == "same" else "older"
    except StagingError as error:
        status = _STATUS_OF_ERROR.get(error.code, "unreadable")
    return IntegrityReport(
        integrity_check=description.integrity_check,
        foreign_key_violations=description.foreign_key_violations,
        undecodable=undecodable,
        revision=description.alembic_revision,
        revision_status=status,
        tables=description.tables,
    )


def _undecodable_rowids(path: Path, table: str) -> list[int]:
    """The rowids, at most ``_ROWIDS_SHOWN``, of the rows of ``table`` with a text that is not UTF-8. Row by row, only
    for a table the scan flagged. A table without a rowid has none to give."""
    with closing(sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        conn.execute("PRAGMA trusted_schema=OFF")
        quoted = '"' + table.replace('"', '""') + '"'
        names = [name for (name,) in conn.execute("SELECT name FROM pragma_table_xinfo(?)", (table,))]
        rowid = next((candidate for candidate in _ROWID_NAMES if candidate not in {name.lower() for name in names}), None)
        if rowid is None or conn.execute("SELECT wr FROM pragma_table_list WHERE schema = 'main' AND name = ?", (table,)).fetchone()[0]:
            return []
        conn.text_factory = bytes
        texts = ", ".join(f'CASE WHEN typeof("{name.replace(chr(34), chr(34) * 2)}") = \'text\' THEN "{name.replace(chr(34), chr(34) * 2)}" END' for name in names)
        found: list[int] = []
        for key, *values in conn.execute(f"SELECT {rowid}, {texts} FROM {quoted} ORDER BY {rowid}"):
            if any(not _is_utf8(value) for value in values):
                found.append(key)
                if len(found) == _ROWIDS_SHOWN:
                    break
        return found


def _is_utf8(value: object) -> bool:
    if not isinstance(value, bytes):
        return True
    try:
        value.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def main(argv: Optional[list[str]] = None) -> int:
    """Check the database; print what is wrong, never a stored value."""
    parser = argparse.ArgumentParser(prog="python -m backend.app.services.platform.db_integrity_check", description="Check the integrity of the database file (read-only).")
    parser.add_argument("--db-file", type=Path, default=None, help="the SQLite database (default: the configured one)")
    args = parser.parse_args(argv)
    path = args.db_file
    if path is None:
        from backend.app.db.post_migration import configured_sqlite_path  # noqa: PLC0415 — only the default needs the settings

        path = configured_sqlite_path()
    if path is None:
        print("No SQLite database is configured", file=sys.stderr)
        return 2
    try:
        report = check_database(path)
    except (sqlite3.Error, OSError) as error:
        print(f"Cannot read {path}: {error}", file=sys.stderr)
        return 2
    problems = report.problems()
    if not problems:
        print(f"No problem found in {path} (revision {report.revision}, {len(report.tables)} tables).")
        return 0
    print(f"{len(problems)} problem(s) found in {path}:")
    for line in problems:
        print(f"  - {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
