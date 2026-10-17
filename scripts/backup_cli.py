#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
Instance backup CLI: ``./dev.py backup …``.

The same archive as Settings › Administration › Backup: the database (a consistent copy, safe while the server runs),
the uploaded files, the broker reports and the risk scenarios, with a manifest. It holds every user's data: keep it
private.

Usage:
    ./dev.py backup create [--output PATH]     Write an archive (default: <data dir>/backups/)
    ./dev.py backup create --encrypt           A secure backup: an .lfbk only its password opens (asked twice)
    ./dev.py backup inspect ARCHIVE            Check an archive and show what it holds
    ./dev.py backup restore ARCHIVE --dry-run  Check an archive for a restore, on a copy: the instance stays as it is
    ./dev.py backup restore ARCHIVE [--yes]    The same check, then the restore at the next start of the server
    ./dev.py backup decrypt ARCHIVE -o ZIP     The archive inside a secure backup, as a plain .zip
    ./dev.py backup pending [--cancel]         The restore waiting for the next start, or the last one; --cancel drops it
    ./dev.py backup --test-db create           Use the test data directory

A relative PATH or ARCHIVE starts from the project root, like every path given to dev.py. The password of a secure
backup is never an argument (every process sees a command line, the shell keeps it): ``--password-file FILE`` (a Docker
secret works), ``--password-stdin``, or typed at the terminal.

In Docker: ``docker compose exec librefolio python dev.py backup create``. Run as root, the command works as the owner of
the data directory, so every file it writes belongs to the server.
"""

from __future__ import annotations

import argparse
import contextlib
import getpass
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


def _safe(text: object) -> str:
    """A value read from an archive or a restore's state, as the terminal may print it: control characters (escape
    sequences included) become ``?``, so an archive cannot drive the operator's terminal."""
    return "".join(char if char.isprintable() else "?" for char in str(text))


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


def _decrypt_as_owner(args) -> bool:
    """``decrypt`` writes a zip of every user's data: started as root where a data directory is (``docker compose exec``
    without a user), it runs as that directory's owner, as the other commands do, so the zip belongs to the server's
    user (B-19). Not root, or without a data directory (decrypting on another computer), it stays who it is, and never
    reads the data directory's setting. ``False`` after printing why the switch failed."""
    from backend.app.config import get_data_dir, set_test_mode  # noqa: PLC0415 — keep dev.py's start light

    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return True
    try:
        if args.test_db:
            set_test_mode(True)
        data_dir = get_data_dir()
    except ValueError as exc:
        print(f"❌ {exc}")
        return False
    if not data_dir.is_dir():
        return True
    problem = _drop_root_privileges(data_dir)
    if problem:
        print(f"❌ {problem}")
        return False
    return True


def _password_file_first(args) -> tuple[bool, str | None]:
    """``--password-file``, read before any switch of user, as ``create``, ``inspect`` and ``restore`` read it: a secret
    only root can read (a Docker secret) works for every command. ``(False, None)`` after printing why it gives no
    password; ``(True, None)`` without the option (the terminal and ``--password-stdin`` come later)."""
    if not getattr(args, "password_file", None):
        return True, None
    try:
        return True, _password(args, twice=False)
    except _PasswordProblem as exc:
        print(f"❌ {exc} ({exc.code})")
        return False, None


class _PasswordProblem(Exception):
    """No password could be read: ``code`` says why, in a stable word."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _password(args, *, twice: bool) -> str:
    """The password from ``--password-file``, from ``--password-stdin`` (a pipe), or typed at the terminal without being
    shown, ``--password-stdin`` at a terminal included (``twice`` to choose one). ``_PasswordProblem`` when there is
    none: no source, and no terminal to ask on."""
    from backend.app.config import SecretFileError, read_secret_file  # noqa: PLC0415 — keep dev.py's start light

    password_file = getattr(args, "password_file", None)
    if password_file:
        try:
            return read_secret_file(_requested(password_file), "password file")
        except SecretFileError as exc:
            raise _PasswordProblem("password_unreadable", str(exc)) from None
    # At a terminal, a line read would show the password as it is typed: --password-stdin asks it there as without it.
    if getattr(args, "password_stdin", False) and not sys.stdin.isatty():
        line = sys.stdin.readline().rstrip("\r\n")
        if not line:
            raise _PasswordProblem("password_required", "The standard input carried no password")
        return line
    if not sys.stdin.isatty():
        raise _PasswordProblem("password_required", "A password is needed: give it with --password-file or --password-stdin, or run the command at a terminal")
    try:
        password = getpass.getpass("   Password: ")
        if twice and getpass.getpass("   The same password again: ") != password:
            raise _PasswordProblem("password_mismatch", "The two passwords differ")
    except EOFError:
        raise _PasswordProblem("password_required", "No password was typed") from None
    if not password:
        raise _PasswordProblem("password_required", "No password was typed")
    return password


def _archive_password(args) -> str | None:
    """The password of a new secure backup, once it meets the rules (P12); ``None`` after saying why not."""
    from backend.app.services.platform.instance_backup.secure import ARCHIVE_PASSWORD_MAX_LENGTH, archive_password_problems, archive_password_rules  # noqa: PLC0415

    try:
        password = _password(args, twice=True)
    except _PasswordProblem as exc:
        print(f"❌ {exc} ({exc.code})")
        return None
    if len(password) > ARCHIVE_PASSWORD_MAX_LENGTH:
        print(f"❌ The password is longer than {ARCHIVE_PASSWORD_MAX_LENGTH} characters (password_too_long)")
        return None
    failed = archive_password_problems(password)
    if failed:
        minimum = next((rule.value for rule in archive_password_rules() if rule.code == "min_length"), None)
        print(f"❌ The password of a backup needs at least {minimum} characters, with an uppercase and a lowercase letter, a digit and a symbol (password_too_weak: {', '.join(failed)})")
        return None
    return password


def _unlock(args, path: Path, password: str | None = None):
    """The key of the secure backup at ``path``, from its password (``password``, when already read); ``None`` after
    saying why not."""
    from backend.app.services.platform.instance_backup.envelope import EnvelopeError, unlock  # noqa: PLC0415

    if password is None:
        try:
            password = _password(args, twice=False)
        except _PasswordProblem as exc:
            print(f"❌ {exc} ({exc.code})")
            return None
    try:
        return unlock(path, password)
    except EnvelopeError as exc:
        print(f"❌ {exc} ({exc.code})")
        return None


@contextlib.contextmanager
def _private_folder(data_dir: Path):
    """A new folder of the data directory that only its owner reads, removed with everything in it at the end. The ones
    killed runs left are removed first, once an hour old: the rule of ``leftovers.py``, which every start of the server
    applies too (lot B4b)."""
    import tempfile  # noqa: PLC0415

    from backend.app.services.platform.instance_backup.leftovers import DECRYPT_FOLDER_PREFIX, remove_stale_decrypt_folders  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.paths import backups_dir, ensure_private_dir  # noqa: PLC0415

    parent = ensure_private_dir(backups_dir(data_dir), data_dir)
    remove_stale_decrypt_folders(parent)
    folder = Path(tempfile.mkdtemp(prefix=DECRYPT_FOLDER_PREFIX, dir=parent))
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


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
    if "instance_key_unusable" in job.warnings:
        print("⚠️  The instance key cannot be used: the secure backup was made without it, so saved provider keys must be entered again after a restore")
    if job.skipped:
        print(f"⚠️  Left out ({len(job.skipped)}{'+' if len(job.skipped) >= 50 else ''}): links, special files, files or folders that could not be read, or files removed during the backup:")
        for entry in job.skipped:
            print(f"     {_safe(entry)}")


def _run_backup(data_dir: Path, password: str | None = None):
    """Run the backup in this process, printing its phases: the job's end state and its folder, or ``None`` when the
    run could not start (another backup runs, ``backups/`` is not a plain folder, it cannot be written). ``password``:
    a secure backup."""
    from backend.app.services.platform.instance_backup import jobs  # noqa: PLC0415 — keep dev.py's start light
    from backend.app.services.platform.instance_backup.paths import BackupPathError, backups_dir  # noqa: PLC0415

    shown: list[str] = []

    def progress(phase: str, done: int, total: int) -> None:
        if not shown or shown[-1] != phase:
            shown.append(phase)
            print(f"   … {phase}")

    try:
        return jobs.run_backup(origin="cli", data_dir=data_dir, progress=progress, password=password)
    except jobs.BackupBusyError:
        print("❌ Another backup is running (from the web interface or another command): try again when it ends")
    except BackupPathError as exc:
        print(f"❌ {exc.path} is not a plain folder (a link, or a file): backups are built in a folder of the data directory. Make it a folder; --output puts the archives on another disk.")
    except OSError as exc:
        print(f"❌ The backup could not run in {backups_dir(data_dir)}: {exc.strerror or exc}")
    return None


def cmd_create(args) -> int:
    """Write a backup archive of the instance; with a password, a secure backup (an ``.lfbk`` envelope)."""
    password = None
    # A namespace built by hand (a script, a test) may lack the password options: no password, as before lot B4.
    if getattr(args, "encrypt", False) or getattr(args, "password_file", None) or getattr(args, "password_stdin", False):
        password = _archive_password(args)
        if password is None:
            return 1
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
    result = _run_backup(data_dir, password)
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
    return _print_written(job, placed, problem, started)


def _print_written(job, placed: Path, problem: str | None, started: float) -> int:
    """Say where the archive went, what it holds and how to keep it; the exit code of ``create``."""
    if problem:
        print(f"⚠️  {problem}: the archive was written to {placed} instead")
    else:
        print(f"✅ Backup written: {placed}")
    print(f"   {_human(job.file_size or 0)} in {time.monotonic() - started:.1f} s")
    _print_warnings(job)
    if job.encrypted:
        print("🔐 Encrypted with your password: only that password opens it, and LibreFolio cannot recover a lost one.")
    else:
        print("🔒 The archive holds every user's data: keep it private.")
    return 1 if problem else 0


def cmd_inspect(args) -> int:
    """Check an archive against its manifest and print what it holds; a secure backup is decrypted first, in a private
    folder of the data directory removed at the end."""
    from backend.app.services.platform.instance_backup.archive import ArchiveError, check_archive  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.envelope import is_envelope  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.manifest import ManifestError  # noqa: PLC0415

    path = Path(args.archive).expanduser()
    if not path.is_file():
        print(f"❌ No file at {path}")
        return 1
    if is_envelope(path):
        return _inspect_envelope(args, path)
    try:
        check = check_archive(path, verify=not args.no_verify)
    except (ArchiveError, ManifestError) as exc:
        print(f"❌ {exc} ({exc.code})")
        return 1
    return _print_check(path, check)


def _inspect_envelope(args, path: Path) -> int:
    """``inspect`` of a secure backup: its password, then the archive inside it, decrypted in a private folder."""
    from backend.app.services.platform.instance_backup.archive import ArchiveError, check_archive  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.envelope import EnvelopeError, decrypt_file  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.manifest import ManifestError  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.paths import BackupPathError  # noqa: PLC0415

    key = _unlock(args, path)
    if key is None:
        return 1
    data_dir = _data_dir_for(args, need_database=False)
    if data_dir is None:
        return 1
    try:
        with _private_folder(data_dir) as folder:
            clear = folder / "archive.zip"
            print(f"🔓 Decrypting {path}")
            try:
                decrypt_file(path, clear, key)
                check = check_archive(clear, verify=not args.no_verify)
            except (EnvelopeError, ArchiveError, ManifestError) as exc:
                print(f"❌ {exc} ({exc.code})")
                return 1
            except OSError as exc:
                print(f"❌ The archive could not be decrypted in {folder}: {exc.strerror or exc}")
                return 1
            return _print_check(path, check, encrypted=True)
    except BackupPathError as exc:
        print(f"❌ {exc.path} is not a plain folder (a link, or a file): a secure backup is decrypted in a folder of the data directory")
        return 1


def _print_check(path: Path, check, *, encrypted: bool = False) -> int:
    """Print what ``check_archive`` found; the exit code."""
    manifest = check.manifest
    files = manifest.files[1:]
    print(f"📦 {path}")
    print(f"   Made by LibreFolio {_safe(manifest.app_version)} ({manifest.origin}) on {manifest.created_at:%Y-%m-%d %H:%M:%S} UTC")
    print(f"   Database: revision {_safe(manifest.alembic_revision or 'unknown')}, {_human(manifest.files[0].size)}, integrity {_safe(manifest.database.integrity_check)}")
    print(f"   Rows: {sum(manifest.database.tables.values())} in {len(manifest.database.tables)} tables")
    print(f"   Files: {len(files)}, {_human(sum(entry.size for entry in files))}")
    if encrypted:
        print("   Secure backup: decrypted with its password")
    print(f"   Instance key: {'included' if manifest.instance_key.included else 'not included'}")
    for label, entries in (("missing", check.missing), ("different from the manifest", check.mismatched), ("not in the manifest", check.unexpected)):
        if entries:
            print(f"❌ {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} {label}: {', '.join(_safe(entry) for entry in entries[:5])}{' …' if len(entries) > 5 else ''}")
    if not check.ok:
        return 1
    print("✅ Every entry matches the manifest" if check.verified else "ℹ️  The entry names match the manifest; their contents were not read (--no-verify)")
    return 0


_STAGE_WARNINGS = {
    "rows_changed": "The upgrade changed the rows of some tables (listed above)",
    "foreign_key_violations": "The backup's database has broken references: they are kept as they are",
    "foreign_key_violations_added": "The upgrade added broken references to the copy",
    "control_totals_changed": "The ledger's totals differ from those the backup recorded (listed above)",
    "control_totals_unreadable": "The ledger's totals could not be read on the copy",
}
_STAGE_BLOCKERS = {
    "no_administrator": "The backup has no active administrator: after a restore nobody could manage the instance",
}


def _print_totals(report) -> None:
    """How the ledger's control totals the backup recorded compare with the copy's (lot B-13)."""
    status = report.control_totals
    if status == "same":
        print("   Ledger totals: the same as when the backup was made")
    elif status == "changed":
        count = report.control_totals_differences_count
        print(f"⚠️  Ledger totals differ from the backup's ({count} line{'' if count == 1 else 's'}):")
        for line in report.control_totals_differences:
            what = f"{_safe(line.currency)} cash" if line.kind == "cash" else f"asset {line.asset_id} quantity"
            print(f"     broker {line.broker_id}, {what}: {_safe(line.before or '—')} → {_safe(line.after or '—')}")
        if count > len(report.control_totals_differences):
            print(f"     … and {count - len(report.control_totals_differences)} more")
    elif status == "absent":
        print("   Ledger totals: not recorded in this archive")
    elif status == "other_version":
        print("   Ledger totals: recorded by another version of the method, not compared")
    else:
        print("⚠️  Ledger totals: could not be read on the copy")


def _print_key_and_secrets(report) -> None:
    """The instance key of the archive, and what becomes of the saved provider keys (lot B4): re-encrypted with this
    instance's key, or to enter again."""
    if report.encrypted:
        print("   Secure backup: decrypted with its password")
    print(f"   Instance key: {'included' if report.instance_key_included else 'not included'}")
    if report.secrets_rekeyed:
        print(f"   Saved provider keys: {report.secrets_rekeyed} re-encrypted with this instance's key")
    unreadable = report.secrets_unreadable.system + report.secrets_unreadable.user
    if unreadable:
        print(f"⚠️  {unreadable} saved provider key{'s' if unreadable != 1 else ''} cannot be read with this instance's key: enter {'them' if unreadable != 1 else 'it'} again after the restore")


def _print_stage_report(report) -> None:
    backup = report.backup
    print(f"📦 Made by LibreFolio {_safe(backup.app_version)} ({backup.origin}) on {backup.created_at:%Y-%m-%d %H:%M:%S} UTC")
    if report.action == "same":
        print(f"   Database: revision {_safe(backup.alembic_revision)}, this LibreFolio's own: restored as it is")
    else:
        print(f"   Database: revision {_safe(backup.alembic_revision)}, upgraded on the copy to {report.head_revision} ({len(report.migrations)} migration{'s' if len(report.migrations) != 1 else ''}):")
        for migration in report.migrations:
            print(f"     - {migration.revision}: {migration.message}")
    if report.post_migration_fixes:
        print(f"   Post-migration fixes applied to the copy: {', '.join(report.post_migration_fixes)}")
    changed = [f"{_safe(name)} ({rows.before if rows.before is not None else '—'} → {rows.after if rows.after is not None else '—'})" for name, rows in report.tables.items() if (rows.before or 0) != (rows.after or 0)]
    rows = sum(table.after or 0 for table in report.tables.values())
    print(f"   Rows: {rows} in {sum(1 for table in report.tables.values() if table.after is not None)} tables, {_human(report.database_size)}")
    if changed:
        print(f"   Changed by the upgrade: {', '.join(changed[:10])}{' …' if len(changed) > 10 else ''}")
    print(f"   Files: {report.files}, {_human(report.files_size)}")
    _print_totals(report)
    _print_key_and_secrets(report)
    if report.administrators:
        print(f"   Administrators: {', '.join(_safe(name) for name in report.administrators)}")
        print("   After a restore you sign in with one of them, with the password of then; every session open now ends.")
        print("   Invitations and links sent before the restore will have expired: send them again if needed.")
    for code in report.warnings:
        print(f"⚠️  {_STAGE_WARNINGS.get(code, code)}")
    for code in report.blockers:
        print(f"❌ {_STAGE_BLOCKERS.get(code, code)}")


_ROLLBACK_REASONS = {
    "first_start_failed": "the first start after it did not complete",
    "swap_interrupted": "the start that applied it was interrupted",
    "swap_failed": "its folders could not be moved into place",
    "stage_missing": "its checked copy was gone",
}


def _when(moment) -> str:
    from datetime import UTC  # noqa: PLC0415

    return f"{moment.astimezone(UTC):%Y-%m-%d %H:%M:%S} UTC" if moment is not None else "an unknown date"


def _confirmed(args) -> bool | None:
    """Whether the restore is confirmed: ``--yes``, or the word ``restore`` typed at the terminal. ``None`` without a
    terminal to ask on."""
    if args.yes:
        return True
    if not sys.stdin.isatty():
        return None
    try:
        answer = input('   Type "restore" to restore this archive at the next start of the server: ')
    except EOFError:
        return False
    return answer.strip() == "restore"


def _instance_blocked() -> bool:
    """Whether the hosting provider blocks the instance (``LIBREFOLIO_BLOCKED``): a restore confirmed now waits for the
    unblock (developer decision P7). A value that cannot be read counts as blocked, as at the start."""
    from backend.app.config.platform import instance_blocked  # noqa: PLC0415 — keep dev.py's start light

    try:
        return instance_blocked()
    except ValueError:
        return True


def _confirm(args, stage_id: str, data_dir: Path) -> bool:
    """Ask, then confirm the restore of the checked copy for the next start; whether it waits now."""
    from backend.app.services.platform.instance_backup.apply import RestoreStateError, confirm_restore  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.paths import BackupPathError  # noqa: PLC0415

    answer = _confirmed(args)
    if answer is None:
        print("❌ No terminal to ask on: add --yes to confirm the restore. Nothing restored: the copy was removed.")
        return False
    if not answer:
        print("Nothing restored: the copy was removed.")
        return False
    try:
        confirm_restore(stage_id, confirmed_by="cli", data_dir=data_dir)
    except RestoreStateError as exc:
        print(f"❌ {exc} ({exc.code})")
        return False
    except BackupPathError as exc:
        print(f"❌ {exc.path} is not a plain folder (a link, or a file): the restore waits in a folder of the data directory")
        return False
    print("✅ The restore waits for the next start of the server: restart LibreFolio to apply it.")
    print("   That start replaces the database and the files, and ends every session: sign in with an administrator of the backup.")
    print("   ./dev.py backup pending shows it; ./dev.py backup pending --cancel drops it.")
    if _instance_blocked():
        print("⚠️  The hosting provider blocked this instance: the restore waits until it is unblocked (instance_blocked)")
    return True


def _restore_already_active(data_dir: Path) -> bool:
    """Whether a restore waits for the next start, or is being applied, or its state cannot be read (B-32): then no other
    one is checked (said once)."""
    from backend.app.services.platform.instance_backup.apply import ACTIVE, RestoreStateUnreadableError, read_restore  # noqa: PLC0415

    try:
        waiting = read_restore(data_dir)
    except RestoreStateUnreadableError as exc:
        print(f"❌ {exc} ({exc.code})")
        return True
    if waiting is None or waiting.status not in ACTIVE:
        return False
    print("❌ A restore already waits for the next start: ./dev.py backup pending --cancel drops it (restore_already_pending)")
    return True


def _check_on_a_copy(path: Path, data_dir: Path, key=None):
    """Check the archive on a copy, printing its phases: the report, or ``None`` when it was refused (said why).
    ``key``: the key of a secure backup."""
    from backend.app.services.platform.instance_backup.paths import BackupPathError, stages_dir  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.staging import StagingBusyError, StagingError, stage_archive  # noqa: PLC0415

    shown: list[str] = []

    def progress(phase: str, done: int, total: int) -> None:
        if not shown or shown[-1] != phase:
            shown.append(phase)
            print(f"   … {phase}")

    print(f"🔎 Checking {path} on a copy, in {stages_dir(data_dir)}")
    try:
        return stage_archive(path, data_dir, progress=progress, key=key)
    except StagingBusyError:
        print("❌ Another archive is being checked (from the web interface or another command): try again when it ends")
    except StagingError as exc:
        print(f"❌ {exc} ({exc.code})")
    except BackupPathError as exc:
        print(f"❌ {exc.path} is not a plain folder (a link, or a file): the copy is made in a folder of the data directory")
    return None


def cmd_restore(args) -> int:
    """Check an archive for a restore on a copy and say what a restore would do; without ``--dry-run``, then confirm the
    restore, which the next start of the server applies."""
    from backend.app.services.platform.instance_backup.envelope import is_envelope  # noqa: PLC0415
    from backend.app.services.platform.instance_backup.staging import remove_stage  # noqa: PLC0415

    path = Path(args.archive).expanduser()
    if not path.is_file():
        print(f"❌ No file at {path}")
        return 1
    key = None
    if is_envelope(path):
        key = _unlock(args, path)
        if key is None:
            return 1
    data_dir = _data_dir_for(args, need_database=False)
    if data_dir is None or (not args.dry_run and _restore_already_active(data_dir)):
        return 1
    report = _check_on_a_copy(path, data_dir, key)
    if report is None:
        return 1
    keep = False
    try:
        _print_stage_report(report)
        if not report.restorable:
            return 1
        if args.dry_run:
            print("✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed.")
            return 0
        keep = _confirm(args, report.stage_id, data_dir)
        return 0 if keep else 1
    finally:
        if not keep:
            remove_stage(data_dir, report.stage_id)


def _print_restore_state(state) -> None:
    if state is None:
        print("ℹ️  No restore waits for the next start")
        return
    backup = f"backup made by LibreFolio {_safe(state.backup_app_version)} on {_when(state.backup_created_at)}"
    if state.status == "pending":
        print("⏳ A restore waits for the next start of the server")
        print(f"   {backup}; confirmed by {_safe(state.confirmed_by)} on {_when(state.confirmed_at)}")
        if state.waiting == "backup_running":
            print("⚠️  At the last start a backup was running: the next start applies it (backup_running)")
        elif state.waiting == "other_data_directory":
            print(f"⚠️  It was confirmed for another data directory ({_safe(state.data_dir)}): this one does not apply it (other_data_directory)")
        elif state.waiting == "server_running":
            print("⚠️  At the last start another server process was serving the data directory: restart the whole server to apply it (server_running)")
        # What the last start found, or the block read now: a restore confirmed on a blocked instance waits for the unblock.
        # A copy of another data directory never applies it, unblocked or not: there the block says nothing.
        if state.waiting == "instance_blocked" or (state.waiting != "other_data_directory" and _instance_blocked()):
            print("⚠️  The hosting provider blocked this instance: the restore waits until it is unblocked (instance_blocked)")
    elif state.status == "committed":
        print(f"✅ The last restore was applied on {_when(state.finished_at)}: {backup}")
    elif state.status == "rolled_back":
        reason = _ROLLBACK_REASONS.get(state.reason or "", "for a reason this LibreFolio does not know")
        print(f"⚠️  The last restore was rolled back on {_when(state.finished_at)}, the data is as it was before: {reason} ({state.reason})")
    else:
        print("⏳ A restore is being applied by the server")


def cmd_decrypt(args) -> int:
    """Write the archive inside a secure backup as a plain ``.zip``: to move an instance by hand («Porta a casa»)."""
    from backend.app.services.platform.instance_backup.envelope import EnvelopeError, decrypt_file  # noqa: PLC0415

    has_password, password = _password_file_first(args)
    if not has_password or not _decrypt_as_owner(args):
        return 1
    path = Path(args.archive).expanduser()
    if not _readable_envelope(path):
        return 1
    target = _requested(args.output)
    if target.exists() or target.is_symlink():
        print(f"❌ {target} already exists: choose another name")
        return 1
    key = _unlock(args, path, password)
    if key is None:
        return 1
    try:
        size = decrypt_file(path, target, key)
    except EnvelopeError as exc:
        print(f"❌ {exc} ({exc.code})")
        return 1
    except FileExistsError:
        print(f"❌ {target} already exists: choose another name")
        return 1
    except OSError as exc:
        print(f"❌ Cannot write {target}: {exc.strerror or exc}")
        return 1
    print(f"✅ Decrypted: {target} ({_human(size)})")
    print("🔒 It holds every user's data in clear: keep it private, and remove it once used.")
    if _carries_instance_key(target):
        print("🔑 It also holds the instance key: with it, every saved provider key can be read.")
    return 0


def _readable_envelope(path: Path) -> bool:
    """Whether ``path`` is a secure backup this command can read; ``False`` after printing why not."""
    from backend.app.services.platform.instance_backup.envelope import is_envelope  # noqa: PLC0415 — keep dev.py's start light

    if not path.is_file():
        print(f"❌ No file at {path}")
        return False
    # is_envelope() answers False for a file it cannot read: say why instead, before a password is asked.
    try:
        with path.open("rb"):
            pass
    except OSError as exc:
        print(f"❌ Cannot read {path}: {exc.strerror or exc} (archive_unreadable)")
        return False
    if not is_envelope(path):
        print(f"❌ {path} is not a secure backup: a plain .zip needs no decrypting (not_an_envelope)")
        return False
    return True


def _carries_instance_key(path: Path) -> bool:
    """Whether the zip at ``path`` announces the instance key in its manifest; ``False`` when it cannot be read."""
    import zipfile  # noqa: PLC0415

    from backend.app.services.platform.instance_backup.archive import read_manifest  # noqa: PLC0415

    try:
        with zipfile.ZipFile(path) as archive:
            return read_manifest(archive).instance_key.included
    except (OSError, ValueError, zipfile.BadZipFile):
        return False


def cmd_pending(args) -> int:
    """Show the restore waiting for the next start, or the last one; ``--cancel`` drops the one waiting."""
    from backend.app.services.platform.instance_backup.apply import RestoreStateUnreadableError, read_restore  # noqa: PLC0415

    data_dir = _data_dir_for(args, need_database=False)
    if data_dir is None:
        return 1
    if args.cancel:
        return _cancel_pending(data_dir)
    try:
        state = read_restore(data_dir)
    except RestoreStateUnreadableError as exc:
        print(f"❌ {exc} ({exc.code})")
        return 1
    _print_restore_state(state)
    return 0


def _cancel_pending(data_dir: Path) -> int:
    """``backup pending --cancel``: drop the restore waiting, with its checked copy, and say whether the copy went (B-32)."""
    from backend.app.services.platform.instance_backup.apply import RestoreNotPendingError, RestoreStateUnreadableError, cancel_restore  # noqa: PLC0415

    try:
        state = cancel_restore(data_dir=data_dir, drop_copy=True)
    except RestoreNotPendingError:
        print("❌ No restore waits for the next start: nothing to cancel (restore_not_pending)")
        return 1
    except RestoreStateUnreadableError as exc:
        print(f"❌ {exc} ({exc.code})")
        return 1
    except OSError as exc:
        # Raised before the state is removed: the restore still waits.
        print(f"❌ The restore could not be cancelled: {exc.strerror or type(exc).__name__}. It still waits for the next start (restore_cancel_failed)")
        return 1
    if _copy_left(data_dir, state.stage_id):
        # Its removal failed after the drop: a warning above when it raised (B-31).
        print("✅ The restore waiting for the next start was dropped: the data stays as it is")
        print("⚠️  Its checked copy could not be removed: it goes when its check expires")
        return 0
    print("✅ The restore waiting for the next start was dropped, with its copy: the data stays as it is")
    return 0


def _copy_left(data_dir: Path, stage_id: str) -> bool:
    """Whether the checked copy of the restore just dropped is still there. One that cannot even be looked at counts as
    there: never say that a copy went when it may not have."""
    from backend.app.services.platform.instance_backup.paths import stage_dir  # noqa: PLC0415

    try:
        os.lstat(stage_dir(data_dir, stage_id))
    except FileNotFoundError:
        return False
    except OSError:
        return True
    return True


def register_subparser(parent_subparsers):
    """Register ``backup`` as a command group of dev.py."""
    parser = parent_subparsers.add_parser(
        "backup",
        help="💾 Instance backup (create, inspect, restore, decrypt, pending)",
        description="Backup of the whole instance: database, uploaded files, broker reports and risk scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./dev.py backup create                       Write an archive into <data dir>/backups/
  ./dev.py backup create -o /mnt/nas/          Write it into another folder
  ./dev.py backup create --encrypt             A secure backup (.lfbk): the password is asked twice
  ./dev.py backup create --password-file /run/secrets/backup_password
                                               The same, the password read from a file
  ./dev.py backup inspect /mnt/nas/librefolio-backup-20261015-101500.zip
                                               Check an archive and show what it holds
  ./dev.py backup restore /mnt/nas/librefolio-backup-20261015-101500.zip --dry-run
                                               What a restore would do: unpacked, upgraded and checked
                                               on a copy, then removed
  ./dev.py backup restore /mnt/nas/librefolio-backup-20261015-101500.zip
                                               The same check, then, once you type "restore", the
                                               restore at the next start of the server
  ./dev.py backup decrypt backup.lfbk -o backup.zip
                                               The archive inside a secure backup, as a plain .zip
  ./dev.py backup pending --cancel             Drop the restore waiting for the next start
  ./dev.py backup --test-db create             Use the test data directory

A relative path starts from the project root, like every path given to dev.py. A password is never an argument:
--password-file, --password-stdin, or typed at the terminal.
""",
    )
    parser.add_argument("--test-db", action="store_true", help="Use the test data directory instead of production")
    commands = parser.add_subparsers(dest="backup_cmd", title="Backup commands", metavar="")

    # No abbreviated options: «--password» must never pass for one of the password sources.
    create = commands.add_parser("create", help="Write a backup archive of the instance (safe while the server runs)", allow_abbrev=False)
    create.add_argument("--output", "-o", metavar="PATH", help="Archive file, or an existing folder for it (default: <data dir>/backups/); checked before the backup starts")
    create.add_argument("--encrypt", action="store_true", help="A secure backup: an .lfbk envelope that only its password opens, with the instance key LibreFolio generated (the password is asked twice at the terminal)")
    _password_options(create)
    create.set_defaults(backup_func=cmd_create)

    inspect = commands.add_parser("inspect", help="Check an archive against its manifest and show what it holds", allow_abbrev=False)
    inspect.add_argument("archive", help="The backup archive (.zip, or .lfbk for a secure backup)")
    inspect.add_argument("--no-verify", action="store_true", help="Compare the entry names with the manifest without reading the entries (faster)")
    _password_options(inspect)
    inspect.set_defaults(backup_func=cmd_inspect)

    restore = commands.add_parser("restore", help="Restore an archive at the next start of the server, once checked on a copy (--dry-run: only the check)", allow_abbrev=False)
    restore.add_argument("archive", help="The backup archive (.zip, or .lfbk for a secure backup)")
    restore.add_argument("--dry-run", action="store_true", help="Unpack the archive into a copy, upgrade and check it, report, then remove the copy; the instance is left as it is")
    restore.add_argument("--yes", "-y", action="store_true", help='Confirm the restore without typing "restore" (needed without a terminal)')
    _password_options(restore)
    restore.set_defaults(backup_func=cmd_restore)

    decrypt = commands.add_parser("decrypt", help="Write the archive inside a secure backup (.lfbk) as a plain .zip", allow_abbrev=False)
    decrypt.add_argument("archive", help="The secure backup (.lfbk)")
    decrypt.add_argument("--output", "-o", metavar="PATH", required=True, help="The .zip to write: it must not exist yet")
    _password_options(decrypt)
    decrypt.set_defaults(backup_func=cmd_decrypt)

    pending = commands.add_parser("pending", help="Show the restore waiting for the next start of the server, or the last one")
    pending.add_argument("--cancel", action="store_true", help="Drop the restore waiting for the next start, and its checked copy")
    pending.set_defaults(backup_func=cmd_pending)

    parser.set_defaults(func=_dispatch)
    return parser


def _password_options(command) -> None:
    """Where the password of a secure backup comes from, never the command line."""
    sources = command.add_mutually_exclusive_group()
    sources.add_argument("--password-file", metavar="FILE", help="Read the password from FILE: its whole content, without a byte order mark and the line breaks at its end (a Docker secret works)")
    sources.add_argument("--password-stdin", action="store_true", help="Read the password from the standard input, one line; at a terminal, it is asked without being shown")


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
