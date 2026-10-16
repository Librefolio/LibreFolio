#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
Instance backup CLI: ``./dev.py backup …``.

The same archive as Settings › Backup: the database (a consistent copy, safe while the server runs), the uploaded
files, the broker reports and the risk scenarios, with a manifest. It holds every user's data: keep it private.

Usage:
    ./dev.py backup create [--output PATH]     Write an archive (default: <data dir>/backups/)
    ./dev.py backup inspect ARCHIVE            Check an archive and show what it holds
    ./dev.py backup restore ARCHIVE --dry-run  Check an archive for a restore, on a copy: the instance stays as it is
    ./dev.py backup --test-db create           Use the test data directory

A relative PATH or ARCHIVE starts from the project root, like every path given to dev.py.

In Docker: ``docker compose exec librefolio python dev.py backup create``. Run as root, the command works as the owner of
the data directory, so every file it writes belongs to the server.
"""

from __future__ import annotations

import argparse
import contextlib
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


def _requested(output: str) -> Path:
    """``--output`` as an absolute path: ``~`` is the home folder; a relative path starts from the working directory,
    which ``dev.py`` sets to the project root."""
    path = Path(output).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _output_path(output: str | None, data_dir: Path, name: str) -> Path:
    """Where the archive goes: ``--output`` (a file, or a folder for it), or ``<data dir>/backups/<name>``."""
    from backend.app.services.platform.instance_backup.paths import backups_dir  # noqa: PLC0415 — keep dev.py's start light

    if not output:
        return backups_dir(data_dir) / name
    path = _requested(output)
    return path / name if path.is_dir() else path


def _free_path(folder: Path, name: str) -> Path:
    """``folder/name``, or ``<stem>-2``, ``<stem>-3`` … when a file already holds the name: an archive never replaces one."""
    candidate = folder / name
    stem, suffix = Path(name).stem, Path(name).suffix
    index = 2
    while candidate.exists() or candidate.is_symlink():
        candidate = folder / f"{stem}-{index}{suffix}"
        index += 1
    return candidate


def _check_output(output: str) -> str | None:
    """Refuse an ``--output`` the archive could not be written to, before any backup runs; a message, or ``None``.

    An existing folder receives the archive under its own name. Any other path is the archive's file: it must not exist
    yet, and the nearest folder of it that exists must be writable (the missing ones are created with the archive, so a
    backup that fails leaves no empty folder). The space there is checked once the archive's size is known.
    """
    path = _requested(output)
    if path.is_dir():
        folder = path
    else:
        if path.exists() or path.is_symlink():
            return f"{path} already exists: choose another name or folder"
        folder = path.parent
        while not folder.exists():
            folder = folder.parent
        if not folder.is_dir():
            return f"{folder} is not a folder: choose another path"
    if not os.access(folder, os.W_OK | os.X_OK):
        return f"cannot write into {folder}: choose another folder, or run the command as a user who can"
    return None


def _folders_to_create(folder: Path, existing: Path) -> list[Path]:
    """The folders from ``existing`` (excluded) down to ``folder`` (included), outermost first."""
    missing: list[Path] = []
    while folder != existing:
        missing.append(folder)
        folder = folder.parent
    return missing[::-1]


def _move_to(source: Path, target: Path) -> str | None:
    """Move ``source`` to ``target``, creating its missing folders; why it did not get there, or ``None``.

    When ``target`` is on another disk, its free space is checked first. On a failure nothing is left at ``target``, and
    the folders made for it are removed again (deepest first, when still empty).
    """
    created: list[Path] = []
    try:
        existing = target.parent
        while not existing.exists():
            existing = existing.parent
        size = source.stat().st_size
        if os.stat(existing).st_dev != os.stat(source).st_dev and shutil.disk_usage(existing).free < size:
            return f"not enough free space in {existing} for {_human(size)}"
        for folder in _folders_to_create(target.parent, existing):
            folder.mkdir()
            created.append(folder)
        shutil.move(str(source), str(target))
        return None
    except OSError as exc:
        if not source.exists() and target.exists():
            return None  # the archive got there; only the clean-up after the copy failed
        with contextlib.suppress(OSError):
            target.unlink(missing_ok=True)
        for folder in reversed(created):
            with contextlib.suppress(OSError):
                folder.rmdir()
        return f"cannot write {target}: {exc.strerror or exc}"


def _place_archive(source: Path, target: Path, data_dir: Path) -> tuple[Path, str | None]:
    """Move the finished archive to ``target``; when that fails, put it in ``<data dir>/backups/`` instead.

    Returns where the archive is, and why it is not at ``target`` (``None`` when it is). The archive is never lost: a
    move that fails half-way leaves no partial copy at ``target``, and when ``backups/`` cannot take it either, it stays
    in its job folder.
    """
    from backend.app.services.platform.instance_backup.paths import backups_dir  # noqa: PLC0415

    if target.exists() or target.is_symlink():
        problem = f"{target} already exists"
    else:
        problem = _move_to(source, target)
        if problem is None:
            return target, None

    fallback = _free_path(backups_dir(data_dir), source.name)
    if fallback.parent != target.parent:
        try:
            os.replace(source, fallback)  # same file system: the job folder is inside backups/
            return fallback, problem
        except OSError:
            pass
    return source, problem


def _data_dir_for(args, *, need_database: bool = True) -> Path | None:
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
    if need_database and not database_path(data_dir).is_file():
        print(f"❌ No database at {database_path(data_dir)}: nothing to back up")
        return None
    return data_dir


def _print_warnings(job) -> None:
    if "database_integrity" in job.warnings:
        print("⚠️  The database failed its integrity check: the archive keeps it as it is (./dev.py backup inspect shows the result)")
    if "foreign_key_violations" in job.warnings:
        print("⚠️  The database has foreign-key violations: the archive keeps it as it is")
    if job.skipped:
        print(f"⚠️  Left out ({len(job.skipped)}{'+' if len(job.skipped) >= 50 else ''}): links, special files, files or folders that could not be read, or files removed during the backup:")
        for entry in job.skipped:
            print(f"     {entry}")


def _run_backup(data_dir: Path):
    """Run the backup in this process, printing its phases: the job's end state and its folder, or ``None`` when the
    run could not start (another backup runs, ``backups/`` is not a plain folder, it cannot be written)."""
    from backend.app.services.platform.instance_backup import jobs  # noqa: PLC0415 — keep dev.py's start light
    from backend.app.services.platform.instance_backup.paths import BackupPathError, backups_dir  # noqa: PLC0415

    shown: list[str] = []

    def progress(phase: str, done: int, total: int) -> None:
        if not shown or shown[-1] != phase:
            shown.append(phase)
            print(f"   … {phase}")

    try:
        return jobs.run_backup(origin="cli", data_dir=data_dir, progress=progress)
    except jobs.BackupBusyError:
        print("❌ Another backup is running (from the web interface or another command): try again when it ends")
    except BackupPathError as exc:
        print(f"❌ {exc.path} is not a plain folder (a link, or a file): backups are built in a folder of the data directory. Make it a folder; --output puts the archives on another disk.")
    except OSError as exc:
        print(f"❌ The backup could not run in {backups_dir(data_dir)}: {exc.strerror or exc}")
    return None


def cmd_create(args) -> int:
    """Write a backup archive of the instance."""
    data_dir = _data_dir_for(args)
    if data_dir is None:
        return 1
    if args.output:
        problem = _check_output(args.output)
        if problem:
            print(f"❌ {problem}")
            return 1

    print(f"💾 Backing up {data_dir}")
    started = time.monotonic()
    result = _run_backup(data_dir)
    if result is None:
        return 1
    job, folder = result
    if job.status != "done" or job.file_name is None:
        reason = {"backup_no_space": "not enough free space"}.get(job.error_code or "", "the cause is in the log above")
        print(f"❌ Backup failed ({job.error_code}): {reason}")
        shutil.rmtree(folder, ignore_errors=True)
        return 1

    target = _output_path(args.output, data_dir, job.file_name)
    if target.name == job.file_name:
        # A folder receives the archive under its own name: another archive of the same second keeps its own.
        target = _free_path(target.parent, target.name)
    placed, problem = _place_archive(folder / job.file_name, target, data_dir)
    if placed.parent == folder:
        print(f"❌ {problem}: the archive stays in {placed}. Move it within the hour: the next backup after that removes it.")
        return 1
    shutil.rmtree(folder, ignore_errors=True)

    if problem:
        print(f"⚠️  {problem}: the archive was written to {placed} instead")
    else:
        print(f"✅ Backup written: {placed}")
    print(f"   {_human(job.file_size or 0)} in {time.monotonic() - started:.1f} s")
    _print_warnings(job)
    print("🔒 The archive holds every user's data: keep it private.")
    return 1 if problem else 0


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
    print("✅ Every entry matches the manifest" if check.verified else "ℹ️  The entry names match the manifest; their contents were not read (--no-verify)")
    return 0


_STAGE_WARNINGS = {
    "rows_changed": "The upgrade changed the rows of some tables (listed above)",
    "foreign_key_violations": "The backup's database has broken references: they are kept as they are",
    "foreign_key_violations_added": "The upgrade added broken references to the copy",
}
_STAGE_BLOCKERS = {
    "no_administrator": "The backup has no active administrator: after a restore nobody could manage the instance",
}


def _print_stage_report(report) -> None:
    backup = report.backup
    print(f"📦 Made by LibreFolio {backup.app_version} ({backup.origin}) on {backup.created_at:%Y-%m-%d %H:%M:%S} UTC")
    if report.action == "same":
        print(f"   Database: revision {backup.alembic_revision}, this LibreFolio's own: restored as it is")
    else:
        print(f"   Database: revision {backup.alembic_revision}, upgraded on the copy to {report.head_revision} ({len(report.migrations)} migration{'s' if len(report.migrations) != 1 else ''}):")
        for migration in report.migrations:
            print(f"     - {migration.revision}: {migration.message}")
    if report.post_migration_fixes:
        print(f"   Post-migration fixes applied to the copy: {', '.join(report.post_migration_fixes)}")
    changed = [f"{name} ({rows.before if rows.before is not None else '—'} → {rows.after if rows.after is not None else '—'})" for name, rows in report.tables.items() if (rows.before or 0) != (rows.after or 0)]
    rows = sum(table.after or 0 for table in report.tables.values())
    print(f"   Rows: {rows} in {sum(1 for table in report.tables.values() if table.after is not None)} tables, {_human(report.database_size)}")
    if changed:
        print(f"   Changed by the upgrade: {', '.join(changed[:10])}{' …' if len(changed) > 10 else ''}")
    print(f"   Files: {report.files}, {_human(report.files_size)}")
    print(f"   Instance key: {'included' if report.instance_key_included else 'not included'}")
    if report.administrators:
        print(f"   Administrators: {', '.join(report.administrators)}")
        print("   After a restore you sign in with one of them, with the password of then; every session open now ends.")
    for code in report.warnings:
        print(f"⚠️  {_STAGE_WARNINGS.get(code, code)}")
    for code in report.blockers:
        print(f"❌ {_STAGE_BLOCKERS.get(code, code)}")


def cmd_restore(args) -> int:
    """Check an archive for a restore on a copy (``--dry-run``), and say what a restore would do."""
    from backend.app.services.platform.instance_backup.paths import BackupPathError, stages_dir  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.staging import StagingBusyError, StagingError, remove_stage, stage_archive  # noqa: PLC0415

    if not args.dry_run:
        print("❌ Only --dry-run is available for now: it checks the archive on a copy and leaves the instance as it is")
        return 1
    path = Path(args.archive).expanduser()
    if not path.is_file():
        print(f"❌ No file at {path}")
        return 1
    data_dir = _data_dir_for(args, need_database=False)
    if data_dir is None:
        return 1

    shown: list[str] = []

    def progress(phase: str, done: int, total: int) -> None:
        if not shown or shown[-1] != phase:
            shown.append(phase)
            print(f"   … {phase}")

    print(f"🔎 Checking {path} on a copy, in {stages_dir(data_dir)}")
    try:
        report = stage_archive(path, data_dir, progress=progress)
    except StagingBusyError:
        print("❌ Another archive is being checked (from the web interface or another command): try again when it ends")
        return 1
    except StagingError as exc:
        print(f"❌ {exc} ({exc.code})")
        return 1
    except BackupPathError as exc:
        print(f"❌ {exc.path} is not a plain folder (a link, or a file): the copy is made in a folder of the data directory")
        return 1
    try:
        _print_stage_report(report)
    finally:
        remove_stage(data_dir, report.stage_id)
    if not report.restorable:
        return 1
    print("✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.")
    return 0


def register_subparser(parent_subparsers):
    """Register ``backup`` as a command group of dev.py."""
    parser = parent_subparsers.add_parser(
        "backup",
        help="💾 Instance backup (create, inspect, restore --dry-run)",
        description="Backup of the whole instance: database, uploaded files, broker reports and risk scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./dev.py backup create                       Write an archive into <data dir>/backups/
  ./dev.py backup create -o /mnt/nas/          Write it into another folder
  ./dev.py backup inspect /mnt/nas/librefolio-backup-20261015-101500.zip
                                               Check an archive and show what it holds
  ./dev.py backup restore /mnt/nas/librefolio-backup-20261015-101500.zip --dry-run
                                               What a restore would do: unpacked, upgraded and checked
                                               on a copy, then removed
  ./dev.py backup --test-db create             Use the test data directory

A relative path starts from the project root, like every path given to dev.py.
""",
    )
    parser.add_argument("--test-db", action="store_true", help="Use the test data directory instead of production")
    commands = parser.add_subparsers(dest="backup_cmd", title="Backup commands", metavar="")

    create = commands.add_parser("create", help="Write a backup archive of the instance (safe while the server runs)")
    create.add_argument("--output", "-o", metavar="PATH", help="Archive file, or an existing folder for it (default: <data dir>/backups/); checked before the backup starts")
    create.set_defaults(backup_func=cmd_create)

    inspect = commands.add_parser("inspect", help="Check an archive against its manifest and show what it holds")
    inspect.add_argument("archive", help="The backup archive (.zip)")
    inspect.add_argument("--no-verify", action="store_true", help="Compare the entry names with the manifest without reading the entries (faster)")
    inspect.set_defaults(backup_func=cmd_inspect)

    restore = commands.add_parser("restore", help="Check an archive for a restore on a copy (--dry-run): what a restore would do")
    restore.add_argument("archive", help="The backup archive (.zip)")
    restore.add_argument("--dry-run", action="store_true", help="Unpack the archive into a copy, upgrade and check it, report, then remove the copy; the instance is left as it is")
    restore.set_defaults(backup_func=cmd_restore)

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
