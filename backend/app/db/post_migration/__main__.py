"""Offline entry point: ``python -m backend.app.db.post_migration [--db PATH] [--data-dir PATH] [--dry-run]``.

Runs the same post-migration fixes the server runs at startup, with the server stopped (also
inside the Docker image). The database and the data dir default to the configured ones.
Exit code 0 when nothing failed (a dry run included), 1 when a fix failed or the database
failed its integrity check. Plan ``34_accountAndIdReuse`` §2.3.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from backend.app.config import get_data_dir
from backend.app.db.post_migration import configured_sqlite_path, run_post_migration_fixes


def main(argv: Optional[list[str]] = None) -> int:
    """Run the post-migration fixes with the server stopped; 0 when nothing failed, 1 when a fix failed."""
    parser = argparse.ArgumentParser(prog="python -m backend.app.db.post_migration", description="Run the post-migration fixes on a stopped LibreFolio database.")
    parser.add_argument("--db", type=Path, default=None, help="SQLite database (default: the configured one)")
    parser.add_argument("--data-dir", type=Path, default=None, help="data directory holding broker_reports (default: the configured one)")
    parser.add_argument("--dry-run", action="store_true", help="report what would be fixed, change nothing")
    args = parser.parse_args(argv)

    db_path = args.db or configured_sqlite_path()
    if db_path is None:
        print("The configured database is not SQLite: nothing to do.")
        return 0
    data_dir = args.data_dir or get_data_dir()
    report = run_post_migration_fixes(db_path, data_dir, dry_run=args.dry_run)

    print(f"Database: {db_path}")
    print(f"Integrity check: {'ok' if report.integrity_ok else 'FAILED'}")
    for fix_id, outcome in report.outcomes.items():
        print(f"Fix {fix_id}: {outcome}")
    for folder in report.orphan_broker_dirs:
        print(f"Orphan broker folder: {folder}")
    if report.backup_path is not None:
        print(f"Backup kept: {report.backup_path}")
    for error in report.errors:
        print(f"Error: {error}")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
