"""Offline entry point: ``python -m backend.app.db.post_migration [--db PATH] [--data-dir PATH] [--dry-run]``.

Runs the same post-migration fixes the server runs at startup, with the server stopped (also
inside the Docker image). The database and the data dir default to the configured ones.
Exit code 0 when nothing failed (a dry run included), 1 when a fix failed or the database
failed its integrity check. Plan ``34_accountAndIdReuse`` §2.3.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from backend.app.config import get_data_dir, get_settings
from backend.app.db.post_migration import configured_sqlite_path, run_post_migration_fixes
from backend.app.logging_config import configure_logging
from backend.app.services.transactions.lone_transfer_legs import run_lone_giving_legs


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
    # Then, as at startup, the lone giving TRANSFER legs, converted to ADJUSTMENT-out without a value (decision 47, N78-1).
    legs, legs_error = [], None
    if report.integrity_ok and not report.failed:
        try:
            legs = asyncio.run(run_lone_giving_legs(db_path, dry_run=args.dry_run))
        except Exception as exc:  # noqa: BLE001 — reported like a failed fix
            legs_error = str(exc)

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
    for leg in legs:
        print(leg.describe(dry_run=args.dry_run))
    if legs_error is not None:
        print(f"Error: lone transfer legs: {legs_error}")
    return 1 if report.failed or legs_error is not None else 0


if __name__ == "__main__":
    # A run by hand logs as the server does at startup: one line per row a fix changes, and how long it took. On the
    # console only, so the script writes nothing in the data dir but what the fixes change. main() called from code
    # configures nothing.
    configure_logging(get_settings().LOG_LEVEL, enable_file_logging=False)
    sys.exit(main())
