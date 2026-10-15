#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
Instance backup CLI: ``./dev.py backup …``.

The same archive as Settings › Backup: the database (a consistent copy, safe while the server runs), the uploaded
files, the broker reports and the risk scenarios, with a manifest. It holds every user's data: keep it private.

Usage:
    ./dev.py backup create [--output PATH]     Write an archive (default: <data dir>/backups/)
    ./dev.py backup inspect ARCHIVE            Check an archive and show what it holds
    ./dev.py backup --test-db create           Use the test data directory

In Docker: ``docker compose exec librefolio python dev.py backup create``. Run as root, the command works as the owner of
the data directory, so every file it writes belongs to the server.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

# Make the project importable when run directly (``python scripts/backup_cli.py``).
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _human(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def _drop_root_privileges(data_dir: Path) -> str | None:
    """Run as the owner of the data directory when started as root (``docker compose exec`` without a user).

    The archive, the lock and the files SQLite creates beside the database then belong to the server's user, never to
    root. Returns an error message when the drop fails, ``None`` otherwise.
    """
    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return None
    owner = data_dir.stat()
    if owner.st_uid == 0:
        return None
    try:
        os.setgroups([])
        os.setgid(owner.st_gid)
        os.setuid(owner.st_uid)
    except OSError as exc:
        return f"cannot switch to the owner of {data_dir} ({owner.st_uid}:{owner.st_gid}): {exc}. Run the command as that user."
    return None


def _output_path(output: str | None, data_dir: Path, name: str) -> Path:
    """Where the archive goes: ``--output`` (a file, or a folder for it), or ``<data dir>/backups/<name>``."""
    from backend.app.services.platform.instance_backup.paths import backups_dir  # noqa: PLC0415 — keep dev.py's start light

    if not output:
        return backups_dir(data_dir) / name
    path = Path(output).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path / name if path.is_dir() else path


def _data_dir_for(args) -> Path | None:
    """The data directory the command works on, once checked and once this process runs as its owner."""
    from backend.app.config import get_data_dir, set_test_mode  # noqa: PLC0415 — keep dev.py's start light
    from backend.app.services.platform.instance_backup.paths import database_path  # noqa: PLC0415

    if args.test_db:
        set_test_mode(True)
        print("ℹ️  Operating on the TEST data directory")
    data_dir = get_data_dir()
    if not data_dir.is_dir():
        print(f"❌ No data directory at {data_dir}")
        return None
    problem = _drop_root_privileges(data_dir)
    if problem:
        print(f"❌ {problem}")
        return None
    if not database_path(data_dir).is_file():
        print(f"❌ No database at {database_path(data_dir)}: nothing to back up")
        return None
    return data_dir


def _print_warnings(job) -> None:
    if "database_integrity" in job.warnings:
        print("⚠️  The database failed its integrity check: the archive keeps it as it is (./dev.py backup inspect shows the result)")
    if "foreign_key_violations" in job.warnings:
        print("⚠️  The database has foreign-key violations: the archive keeps it as it is")
    if job.skipped:
        print(f"⚠️  Left out ({len(job.skipped)}{'+' if len(job.skipped) >= 50 else ''}): links, special files, or files that changed during the backup:")
        for entry in job.skipped:
            print(f"     {entry}")


def cmd_create(args) -> int:
    """Write a backup archive of the instance."""
    data_dir = _data_dir_for(args)
    if data_dir is None:
        return 1
    if args.output:
        planned = _output_path(args.output, data_dir, "librefolio-backup.zip")
        if planned.exists() and not planned.is_dir():
            print(f"❌ {planned} already exists: choose another name or folder")
            return 1

    from backend.app.services.platform.instance_backup import jobs  # noqa: PLC0415 — keep dev.py's start light

    shown: list[str] = []

    def progress(phase: str, done: int, total: int) -> None:
        if not shown or shown[-1] != phase:
            shown.append(phase)
            print(f"   … {phase}")

    print(f"💾 Backing up {data_dir}")
    started = time.monotonic()
    try:
        job, folder = jobs.run_backup(origin="cli", data_dir=data_dir, progress=progress)
    except jobs.BackupBusyError:
        print("❌ Another backup is running (from the web interface or another command): try again when it ends")
        return 1
    if job.status != "done" or job.file_name is None:
        reason = {"backup_no_space": "not enough free space"}.get(job.error_code or "", "the cause is in the log above")
        print(f"❌ Backup failed ({job.error_code}): {reason}")
        shutil.rmtree(folder, ignore_errors=True)
        return 1

    target = _output_path(args.output, data_dir, job.file_name)
    if target.exists():
        print(f"❌ {target} already exists: the archive stays in {folder}")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder / job.file_name), str(target))
    shutil.rmtree(folder, ignore_errors=True)

    print(f"✅ Backup written: {target}")
    print(f"   {_human(job.file_size or 0)} in {time.monotonic() - started:.1f} s")
    _print_warnings(job)
    print("🔒 The archive holds every user's data: keep it private.")
    return 0


def cmd_inspect(args) -> int:
    """Check an archive against its manifest and print what it holds."""
    from backend.app.services.platform.instance_backup.archive import ArchiveError, check_archive  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.manifest import ManifestError  # noqa: PLC0415

    path = Path(args.archive).expanduser()
    if not path.is_file():
        print(f"❌ No file at {path}")
        return 1
    try:
        check = check_archive(path, verify=not args.no_verify)
    except (ArchiveError, ManifestError) as exc:
        print(f"❌ {exc} ({exc.code})")
        return 1

    manifest = check.manifest
    files = manifest.files[1:]
    print(f"📦 {path}")
    print(f"   Made by LibreFolio {manifest.app_version} ({manifest.origin}) on {manifest.created_at:%Y-%m-%d %H:%M:%S} UTC")
    print(f"   Database: revision {manifest.alembic_revision or 'unknown'}, {_human(manifest.files[0].size)}, integrity {manifest.database.integrity_check}")
    print(f"   Rows: {sum(manifest.database.tables.values())} in {len(manifest.database.tables)} tables")
    print(f"   Files: {len(files)}, {_human(sum(entry.size for entry in files))}")
    print(f"   Instance key: {'included' if manifest.instance_key.included else 'not included'}")
    for label, entries in (("missing", check.missing), ("different from the manifest", check.mismatched), ("not in the manifest", check.unexpected)):
        if entries:
            print(f"❌ {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} {label}: {', '.join(entries[:5])}{' …' if len(entries) > 5 else ''}")
    if not check.ok:
        return 1
    print("✅ Every entry matches the manifest" if check.verified else "ℹ️  Manifest read; entries not verified (--no-verify)")
    return 0


def register_subparser(parent_subparsers):
    """Register ``backup`` as a command group of dev.py."""
    parser = parent_subparsers.add_parser(
        "backup",
        help="💾 Instance backup (create, inspect)",
        description="Backup of the whole instance: database, uploaded files, broker reports and risk scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./dev.py backup create                       Write an archive into <data dir>/backups/
  ./dev.py backup create -o /mnt/nas/          Write it into another folder
  ./dev.py backup inspect librefolio-backup-20261015-101500.zip
                                               Check an archive and show what it holds
  ./dev.py backup --test-db create             Use the test data directory
""",
    )
    parser.add_argument("--test-db", action="store_true", help="Use the test data directory instead of production")
    commands = parser.add_subparsers(dest="backup_cmd", title="Backup commands", metavar="")

    create = commands.add_parser("create", help="Write a backup archive of the instance (safe while the server runs)")
    create.add_argument("--output", "-o", metavar="PATH", help="Archive file, or an existing folder for it (default: <data dir>/backups/)")
    create.set_defaults(backup_func=cmd_create)

    inspect = commands.add_parser("inspect", help="Check an archive against its manifest and show what it holds")
    inspect.add_argument("archive", help="The backup archive (.zip)")
    inspect.add_argument("--no-verify", action="store_true", help="Read the manifest only, without checking every entry")
    inspect.set_defaults(backup_func=cmd_inspect)

    parser.set_defaults(func=_dispatch)
    return parser


def _dispatch(args) -> int:
    func = getattr(args, "backup_func", None)
    if func is None:
        print("Error: backup command required. Use: ./dev.py backup --help")
        return 1
    return func(args)


def main() -> int:
    parser = argparse.ArgumentParser(prog="backup_cli.py")
    register_subparser(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["backup", *sys.argv[1:]])
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
