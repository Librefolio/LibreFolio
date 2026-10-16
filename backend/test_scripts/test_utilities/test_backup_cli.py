"""
Instance backup, the command line (workstream B, lot B1): ``scripts/backup_cli.py``.

``dev.py backup`` is registered in a later step: the commands are tested through the module's functions and through
``python scripts/backup_cli.py``.

(a) ``_requested`` / ``_output_path``: ``--output`` made absolute (``~`` is the home folder; a relative path starts
    from the working directory, which ``dev.py`` sets to the project root; an absolute path is kept as it is); no
    ``--output``, the archive goes to ``<data dir>/backups/<name>``; an existing folder receives it under its own
    name; any other path is the archive's file.
(b) ``_drop_root_privileges``: run as root (``docker compose exec`` without a user) on a data directory owned by
    another user, the command drops its supplementary groups, takes the owner's group, then the owner's user, in that
    order (once the user is changed, the group can no longer be). A failure comes back as a message and the command
    stops. Nothing changes when the command is not root, when the owner is root, or without ``os.geteuid``.
(c) ``_dispatch`` without a subcommand prints how to get help and returns 1.
(d) ``cmd_inspect``: 0 for an intact archive; ``--no-verify`` compares the entry names with the manifest without
    reading the entries: other bytes under the right names exit 0, its closing line saying the contents were not read,
    and a name the manifest does not list still exits 1. 1 for a missing file, a file that is not a zip, a zip without
    manifest, an entry altered or added, and a damaged archive.
(e) ``cmd_create``: 1 without a data directory, without a database (nothing written), and when the switch to the
    owner of the data directory fails; 0 otherwise, with the archive (0600) where it was asked for and the job's folder
    removed. An ``--output`` the archive could not be written to (a file or a link already there, dangling or not; a
    path below a file; a folder it cannot write into) is refused before the backup starts: nothing is run, nothing is
    created. A backup that fails creates none of the missing folders of ``--output``; one that succeeds creates them
    with the archive. ``backups/`` or ``backups/.jobs`` a link or a file: 1, a message naming that very folder, nothing
    written through it, no traceback; an ``OSError`` before the run starts: 1 and the system's reason. An archive that
    cannot reach ``--output`` lands in ``backups/`` with a ⚠️ and exit 1, the job's folder removed; one that cannot
    leave its job folder stays there, said with its path and the hour it is kept, exit 1. Backups of the same second
    into one folder (``backups/``, or an ``--output`` folder) keep their own names, ``-2``, ``-3``, and exit 0.
(f) The script: ``python scripts/backup_cli.py create``, then ``inspect`` on the archive it wrote, both exit 0;
    without a command, exit 1.
(g) ``_check_output``: an existing folder is accepted, even one holding a ``librefolio-backup.zip``; a new file path is
    accepted when the nearest folder of it that exists is a folder this process can write into, and nothing is
    created. A file, a link to a file or a dangling link at the path: "already exists"; a file where a folder of the
    path belongs: "is not a folder"; a folder it cannot write into: "cannot write into". A relative path starts from
    the working directory.
(h) ``_free_path``: the name, then ``<stem>-2<suffix>``, ``-3`` … past every name taken, by a file, a folder or a link
    (dangling too); it creates nothing.
(i) ``_place_archive``: the archive moved to its target, the missing folders created, ``(target, None)``. When the
    target is taken (a file, a dangling link: never replaced, never followed), when it is on another device that lacks
    the space (checked on the nearest folder of the target that exists, before any folder is created), or when the move
    fails (a partial copy at the target removed), the archive goes to ``<data dir>/backups/`` under a free name, with
    the reason; when that folder is the target's own, or the rename into it fails, the archive stays in its job folder.
    Wherever it ends, the path returned holds the archive with the bytes it was built with. A move that raises once the
    archive has left its job folder for the target got there whole: ``(target, None)``, and the target, its only copy,
    is never removed. The folders created for a target the archive never reached are removed again, deepest first, the
    folder that existed left as it was (B1 fix 8: "the missing folders are created only when the archive gets there").
(j) The help: ``--no-verify`` compares the entry names without reading the entries; ``--output`` is checked before the
    backup starts; a relative path starts from the project root.
(k) ``cmd_restore`` (lot B2a): a missing file is exit 1 with nothing created in the data directory, with ``--dry-run``
    and without it (the restore itself, lot B3: ``test_backup_cli_restore.py``), ``--yes`` or not. ``--dry-run`` checks the archive on a copy in ``.restore/stage/``: exit 0 for a restorable archive, its
    report printed (the backup's revision, its files, its administrators named), the copy removed and the data
    directory as it was; exit 1 with the ``StagingError`` code for a refused one (not a backup, a backup of another
    LibreFolio, an altered or added entry), with the blocker for a backup without active administrator, while another
    check runs, and when ``.restore`` is a link (named, nothing written through it). ``_print_stage_report`` of an
    upgrade lists the migrations, the tables the upgrade changed and the warnings. The script runs
    ``restore --dry-run`` end to end; ``restore --help`` says what a dry run does. Lot B-13: right after «Files: …»
    the report says what became of the ledger's totals, one line per status (verbatim, contract §5 and §7.5: totals
    that ``differ from the backup's``), ``changed`` with its count and each difference (``—`` for a line absent on a
    side), the first 20 then ``… and <n> more``, a currency through ``_safe``; the two warnings at the end; a dry run of
    a backup as recorded says ``same``.

Pure: data directories in ``tmp_path``. In this process a command sees a production data directory of the test through
its environment (``LIBREFOLIO_TEST_MODE`` removed, ``LIBREFOLIO_DATA_DIR`` in ``tmp_path``, set with ``monkeypatch``
and checked before any command runs). A child process gets this process's environment without ``LIBREFOLIO_*`` and
``COVERAGE_*``, plus that ``LIBREFOLIO_DATA_DIR``, and runs in ``tmp_path``. In every root case ``os.geteuid``,
``os.setgroups``, ``os.setgid`` and ``os.setuid`` are replaced: no test changes the identity of its process. The cases
that need a failure replace, for that test only, ``shutil.move``, ``shutil.disk_usage``, ``backup_cli.os`` (a stand-in
that puts one folder and everything below it on another device, as a disk mounted there), or ``jobs.run_backup``,
``jobs.archive_name`` and ``jobs.build_archive``;
the permission cases are skipped as root, which bypasses them. ``LF_APP_VERSION`` is set, so no git process runs. No
lane database, no server, no network. The restore cases need a real database: one, made once for the module by
``alembic upgrade head`` in a child with the same environment as the script's children, on a file of ``tmp_path``.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import os
import re
import shlex
import shutil
import sqlite3
import stat
import struct
import subprocess
import sys
import zipfile
from contextlib import closing
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.config import get_data_dir
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.archive import build_archive, check_archive
from backend.app.services.platform.instance_backup.manifest import BackupManifest
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, MANIFEST_ENTRY, STAGE_LOCK_FILE, backups_dir, ensure_private_dir, job_dir, jobs_dir, restore_dir, stages_dir
from backend.app.services.platform.instance_backup.staging import ALEMBIC_INI, AppliedMigration, StagedBackup, StagingReport, TableRows
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_utils import print_section, print_success
from scripts import backup_cli

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")
needs_symlinks = pytest.mark.skipif(not POSIX, reason="symbolic links need a privilege on Windows")
needs_permission_checks = pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs POSIX permissions, which root bypasses")

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = PROJECT_ROOT / "scripts" / "backup_cli.py"
APP_VERSION = "v0.0.0-b1-cli-test"
REVISION = "b1a2c3d4e5f6"
NAME = "librefolio-backup-20261015-101500.zip"
#: The names a folder gives to the archives of that same second after NAME: an archive never replaces another.
SECOND_NAME = "librefolio-backup-20261015-101500-2.zip"
THIRD_NAME = "librefolio-backup-20261015-101500-3.zip"
VALID_ID = "0123456789abcdef0123456789abcdef"
#: The bytes of the archive a placement moves: whatever its path in the end, it must still hold exactly these.
ARCHIVE_BYTES = b"PK\x03\x04 an archive as a job leaves it " + bytes(range(256)) * 64
#: Seconds. A child imports the application first, and a loaded parallel run is slow; a hang still ends.
CLI_TIMEOUT = 120
#: Characters of a child's output quoted by an assertion message.
TAIL = 3000
FILES = {
    "custom-uploads/a.txt": b"uploaded file\n" * 64,
    "broker_reports/uploaded/r.csv": b"date,amount\n2026-10-01,10.00\n",
    "scenario_catalog/s.json": b'{"scenarios": [1, 2, 3]}\n',
}


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture(autouse=True)
def app_version(monkeypatch):
    """The version of every manifest, without a git process; ``get_git_version``'s process-wide cache emptied around the test."""
    monkeypatch.setenv("LF_APP_VERSION", APP_VERSION)
    get_git_version.cache_clear()
    yield
    get_git_version.cache_clear()


def make_data_dir(root: Path, *, database: bool = True) -> Path:
    """A data directory: a small database (unless ``database`` is false) and one file in each archived folder."""
    for entry, content in FILES.items():
        (root / entry).parent.mkdir(parents=True, exist_ok=True)
        (root / entry).write_bytes(content)
    if database:
        (root / DATABASE_ENTRY).parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(root / DATABASE_ENTRY)) as conn:
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
            with conn:
                conn.executemany("INSERT INTO users (id, name) VALUES (?, ?)", [(1, "ada"), (2, "grace")])
                conn.execute("INSERT INTO alembic_version (version_num) VALUES (?)", (REVISION,))
    return root


def point_at(monkeypatch, root: Path) -> Path:
    """Make ``root`` the production data directory the commands of this process see; checked before returning it."""
    monkeypatch.delenv("LIBREFOLIO_TEST_MODE", raising=False)
    monkeypatch.delenv("LIBREFOLIO_TEST_DATA_DIR", raising=False)
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(root))
    assert get_data_dir() == root.resolve(), f"precondition: the command must work on this test's data directory, not on {get_data_dir()}"
    return root.resolve()


def listing(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def create_args(output: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(test_db=False, output=output)


def inspect(path: Path, *, no_verify: bool = False) -> int:
    return backup_cli.cmd_inspect(argparse.Namespace(archive=str(path), no_verify=no_verify))


@pytest.fixture
def good_archive(tmp_path) -> Path:
    data = make_data_dir(tmp_path / "data")
    work = tmp_path / "work"
    work.mkdir()
    return build_archive(data, work, work / NAME, origin="cli").path


def rebuilt(source: Path, target: Path, *, drop: tuple[str, ...] = (), swap: dict[str, bytes] | None = None, add: dict[str, bytes] | None = None) -> Path:
    """A copy of the archive ``source`` with entries left out, given other bytes, or added."""
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as new:
        for info in old.infolist():
            if info.filename not in drop:
                new.writestr(info, (swap or {}).get(info.filename, old.read(info)))
        for name, data in (add or {}).items():
            new.writestr(name, data)
    return target


def corrupt(source: Path, target: Path, entry: str) -> Path:
    """A copy of the archive ``source`` with one byte inverted in the middle of the stored data of ``entry``."""
    raw = bytearray(source.read_bytes())
    with zipfile.ZipFile(source) as zf:
        info = zf.getinfo(entry)
    signature, *_, name_length, extra_length = struct.unpack("<4s2B4HL2L2H", raw[info.header_offset : info.header_offset + 30])
    assert signature == b"PK\x03\x04", "precondition: the local header of the entry is where the central directory says"
    raw[info.header_offset + 30 + name_length + extra_length + info.compress_size // 2] ^= 0xFF
    target.write_bytes(bytes(raw))
    return target


EXPECTED_SHA = hashlib.sha256(ARCHIVE_BYTES).hexdigest()
#: The closing line of ``inspect --no-verify``: the names were compared, the contents were not read.
NO_VERIFY_LINE = "ℹ️  The entry names match the manifest; their contents were not read (--no-verify)"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def job_archive(data: Path) -> Path:
    """A finished job's archive as ``run_backup`` leaves it: ``<data dir>/backups/.jobs/<id>/<name>``."""
    data.mkdir(parents=True, exist_ok=True)
    folder = ensure_private_dir(job_dir(data, VALID_ID), data)
    archive = folder / NAME
    archive.write_bytes(ARCHIVE_BYTES)
    return archive


def job_folders(root: Path) -> list[str]:
    """The entries of the jobs folder but its lock: what a command left behind."""
    folder = jobs_dir(root)
    return sorted(path.name for path in folder.iterdir() if path.name != ".lock") if folder.is_dir() else []


def create(output: str | None = None) -> int:
    """``cmd_create`` as ``dev.py backup create`` runs it. An exception escaping it is a traceback on the user's screen
    where a message and exit code 1 belong: a failure of the test, not an error."""
    try:
        return backup_cli.cmd_create(create_args(output))
    except Exception as exc:
        pytest.fail(f"backup create raised {type(exc).__name__} ({exc}): the user would get a traceback instead of a message and exit code 1")


def no_space() -> OSError:
    return OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))


def on_mount(path, mount: Path) -> bool:
    """Whether ``path`` is ``mount`` or below it: on the disk mounted there."""
    path = Path(path)
    return path == mount or mount in path.parents


class OsStandIn:
    """``backup_cli``'s ``os``, but for what a case needs: ``other_device`` and everything below it are on another
    device than the rest (``os.stat``), as a disk mounted there; ``os.replace`` fails with ``rename_error`` when one is
    given. The rest is the real ``os``."""

    def __init__(self, *, other_device: Path | None = None, rename_error: OSError | None = None):
        self._other_device = other_device
        self._rename_error = rename_error

    def __getattr__(self, name: str):
        return getattr(os, name)

    def stat(self, path, *args, **kwargs):
        result = os.stat(path, *args, **kwargs)
        if self._other_device is not None and on_mount(path, self._other_device):
            return SimpleNamespace(st_dev=result.st_dev + 1, st_mode=result.st_mode, st_size=result.st_size)
        return result

    def replace(self, src, dst, *args, **kwargs):
        if self._rename_error is not None:
            raise self._rename_error
        return os.replace(src, dst, *args, **kwargs)


def free_space(monkeypatch, mount: Path, free: int) -> None:
    """``shutil.disk_usage`` reports ``free`` bytes on the disk mounted at ``mount`` (it and everything below it), the
    real figures anywhere else."""
    real_disk_usage = shutil.disk_usage

    def disk_usage(path):
        if on_mount(path, mount):
            return SimpleNamespace(total=max(free, 0) * 2, used=max(free, 0), free=free)
        return real_disk_usage(path)

    monkeypatch.setattr(backup_cli.shutil, "disk_usage", disk_usage)


def failing_move(monkeypatch, error: OSError, *, target: Path | None = None, partial: bytes = b"") -> None:
    """``shutil.move`` to ``target`` (to anywhere when ``None``) fails with ``error``, after writing ``partial`` there
    when given: a copy to another disk that stops half-way. Moves elsewhere go through."""
    real_move = shutil.move

    def move(src, dst, *args, **kwargs):
        if target is not None and Path(dst) != target:
            return real_move(src, dst, *args, **kwargs)
        if partial:
            Path(dst).write_bytes(partial)
        raise error

    monkeypatch.setattr(backup_cli.shutil, "move", move)


# =============================================================================
# (a) _output_path
# =============================================================================


def test_without_output_the_archive_goes_to_the_backups_folder_of_the_data_directory(tmp_path):
    print_section("_output_path")
    data = tmp_path / "data"
    for output in (None, ""):
        assert backup_cli._output_path(output, data, NAME) == data / "backups" / NAME, f"--output {output!r}: the archive goes to <data dir>/backups/"
    print_success("no --output → <data dir>/backups/<name>")


def test_an_existing_folder_receives_the_archive_under_its_own_name(tmp_path):
    nas = tmp_path / "nas"
    nas.mkdir()
    for output in (str(nas), f"{nas}/"):
        assert backup_cli._output_path(output, tmp_path / "data", NAME) == nas / NAME, f"--output {output}: an existing folder receives the archive"
    print_success("existing folder → <folder>/<name>")


def test_any_other_path_is_the_archive_file(tmp_path):
    target = tmp_path / "nas" / "monday.zip"
    assert backup_cli._output_path(str(target), tmp_path / "data", NAME) == target, "a path that is not an existing folder is the archive's file, its folder created later"
    print_success("file path → that file")


def test_a_relative_path_is_relative_to_the_working_directory(tmp_path, monkeypatch):
    (tmp_path / "nas").mkdir()
    monkeypatch.chdir(tmp_path)
    assert backup_cli._output_path("nas", tmp_path / "data", NAME) == Path.cwd() / "nas" / NAME, "a relative folder is found from the working directory"
    assert backup_cli._output_path("monday.zip", tmp_path / "data", NAME) == Path.cwd() / "monday.zip", "a relative file too"
    print_success("relative paths from the working directory")


def test_a_path_from_the_home_folder_is_expanded(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "nas").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    assert backup_cli._output_path("~/nas", tmp_path / "data", NAME) == home / "nas" / NAME, "~ is the home folder"
    print_success("~/nas → <home>/nas/<name>")


def test_requested_makes_the_output_absolute_and_creates_nothing(tmp_path, monkeypatch):
    """(a) ``~`` is the home folder; a relative path starts from the working directory (dev.py's is the project root)."""
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(project)
    cases = {
        "~/nas/monday.zip": home / "nas" / "monday.zip",
        "~": home,
        "nas/monday.zip": Path.cwd() / "nas" / "monday.zip",
        "monday.zip": Path.cwd() / "monday.zip",
        str(tmp_path / "elsewhere" / "monday.zip"): tmp_path / "elsewhere" / "monday.zip",
    }
    for output, expected in cases.items():
        requested = backup_cli._requested(output)
        assert requested == expected and requested.is_absolute(), f"--output {output!r} must be read as {expected}, not {requested}"
    assert listing(tmp_path) == ["project"], f"reading a path creates nothing: {listing(tmp_path)}"
    print_success("~ → home, relative → working directory, absolute → as is")


# =============================================================================
# (b) _drop_root_privileges
# =============================================================================


class Owned:
    """A data directory as ``stat()`` describes it: owned by ``uid``:``gid``."""

    def __init__(self, uid: int, gid: int):
        self.uid = uid
        self.gid = gid

    def stat(self) -> SimpleNamespace:
        return SimpleNamespace(st_uid=self.uid, st_gid=self.gid)

    def __str__(self) -> str:
        return "/srv/librefolio-data"


def refuse(identity: int) -> None:
    raise PermissionError(1, "Operation not permitted")


@pytest.fixture
def identity(monkeypatch) -> list[tuple[str, object]]:
    """The identity changes, recorded instead of made; the effective user is root unless a test says otherwise."""
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(backup_cli.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(backup_cli.os, "setgroups", lambda groups: calls.append(("setgroups", list(groups))), raising=False)
    monkeypatch.setattr(backup_cli.os, "setgid", lambda gid: calls.append(("setgid", gid)), raising=False)
    monkeypatch.setattr(backup_cli.os, "setuid", lambda uid: calls.append(("setuid", uid)), raising=False)
    return calls


def test_as_root_the_command_becomes_the_owner_of_the_data_directory(identity):
    """(b) Groups dropped, then the group, then the user: every file it writes (archive, lock, SQLite's) is the server's."""
    print_section("_drop_root_privileges")
    assert backup_cli._drop_root_privileges(Owned(1000, 1001)) is None, "a successful switch returns no message"
    assert identity == [("setgroups", []), ("setgid", 1001), ("setuid", 1000)], f"root must drop its groups, take gid 1001, then uid 1000, in that order: {identity}"
    print_success("setgroups([]) → setgid(1001) → setuid(1000)")


def test_a_failed_switch_is_a_message_naming_the_owner(identity, monkeypatch):
    monkeypatch.setattr(backup_cli.os, "setuid", refuse)
    message = backup_cli._drop_root_privileges(Owned(1000, 1001))
    assert message is not None and "1000:1001" in message and "Run the command as that user" in message, f"the message names the owner and what to do: {message!r}"
    print_success(message)


@pytest.mark.parametrize("case", ["not-root", "owner-is-root", "no-geteuid"])
def test_nothing_changes_when_there_is_nothing_to_drop(identity, monkeypatch, case):
    if case == "not-root":
        monkeypatch.setattr(backup_cli.os, "geteuid", lambda: 1000)
    elif case == "no-geteuid":
        monkeypatch.delattr(backup_cli.os, "geteuid")
    owner = Owned(0, 0) if case == "owner-is-root" else Owned(1000, 1001)
    assert backup_cli._drop_root_privileges(owner) is None, f"{case}: no message"
    assert identity == [], f"{case}: the identity must not change: {identity}"
    print_success(f"{case}: nothing changed")


@pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs a data directory owned by a user other than root")
def test_create_stops_when_the_switch_to_the_owner_fails(tmp_path, monkeypatch, identity, capsys):
    """(b)(e) Started as root, unable to become the owner: the command stops before writing anything as root."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    monkeypatch.setattr(backup_cli.os, "setuid", refuse)
    before = listing(root)
    assert backup_cli.cmd_create(create_args()) == 1, "a failed switch is exit code 1"
    assert "cannot switch to the owner" in capsys.readouterr().out, "the command says why it stopped"
    assert listing(root) == before, f"nothing may be written: {sorted(set(listing(root)) - set(before))}"
    print_success("switch refused → exit 1, nothing written")


# =============================================================================
# (c) _dispatch
# =============================================================================


def test_without_a_command_the_cli_says_how_to_get_help_and_exits_1(capsys):
    assert backup_cli._dispatch(argparse.Namespace(test_db=False)) == 1, "no subcommand is exit code 1"
    assert "backup command required" in capsys.readouterr().out, "and says a command is required"
    print_success("no subcommand → 1")


# =============================================================================
# (d) cmd_inspect
# =============================================================================


def test_inspect_an_intact_archive(good_archive, capsys):
    print_section("cmd_inspect")
    assert inspect(good_archive) == 0, "an intact archive is exit code 0"
    out = capsys.readouterr().out
    assert "✅ Every entry matches the manifest" in out, f"the verification is reported: {out}"
    for fact in (f"LibreFolio {APP_VERSION} (cli)", f"revision {REVISION}", "Files: 3", "Instance key: not included"):
        assert fact in out, f"inspect shows {fact!r}: {out}"
    print_success("intact archive → 0")


def test_inspect_without_verification_reads_no_entry(good_archive, tmp_path, capsys):
    """(d) Repaired (was ``…_reads_the_manifest_only``, which asserted the old closing line): ``--no-verify`` compares
    the names and reads no entry, so other bytes under the right names pass, and the last line says exactly that."""
    tampered = rebuilt(good_archive, tmp_path / "tampered.zip", swap={"custom-uploads/a.txt": FILES["custom-uploads/a.txt"].upper()})
    assert inspect(tampered, no_verify=True) == 0, "--no-verify does not read the entries: names right, exit code 0"
    out = capsys.readouterr().out
    assert NO_VERIFY_LINE in out, f"the last line says the names match and the contents were not read: {out}"
    assert "✅" not in out, f"an archive whose entries were not read is never called intact: {out}"
    assert inspect(tampered) == 1, "verified, the same archive is exit code 1"
    print_success("--no-verify → 0, names matched, contents not read; verified → 1")


def test_inspect_without_verification_still_compares_the_names(good_archive, tmp_path, capsys):
    """(d) What the help of ``--no-verify`` promises: a name the manifest does not list is found without reading it."""
    added = rebuilt(good_archive, tmp_path / "added.zip", add={"custom-uploads/extra.txt": b"not in the manifest"})
    assert inspect(added, no_verify=True) == 1, "an entry the manifest does not list is exit code 1, with --no-verify too"
    out = capsys.readouterr().out
    assert "1 entry not in the manifest: custom-uploads/extra.txt" in out, f"inspect names the entry: {out}"
    assert NO_VERIFY_LINE not in out, f"names that do not match are not reported as matching: {out}"
    print_success("--no-verify, an added entry → 1")


def bad_archive(case: str, good: Path, tmp_path: Path) -> Path:
    if case == "missing-file":
        return tmp_path / "absent.zip"
    if case == "not-a-zip":
        path = tmp_path / "not-a-zip.zip"
        path.write_text("not a zip\n", encoding="utf-8")
        return path
    if case == "no-manifest":
        return rebuilt(good, tmp_path / "bad.zip", drop=(MANIFEST_ENTRY,))
    if case == "altered-entry":
        return rebuilt(good, tmp_path / "bad.zip", swap={"custom-uploads/a.txt": b"something else"})
    return rebuilt(good, tmp_path / "bad.zip", add={"custom-uploads/extra.txt": b"not in the manifest"})


@pytest.mark.parametrize(
    ("case", "said"),
    [
        ("missing-file", "No file at"),
        ("not-a-zip", "(archive_unreadable)"),
        ("no-manifest", "(manifest_missing)"),
        ("altered-entry", "1 entry different from the manifest: custom-uploads/a.txt"),
        ("added-entry", "1 entry not in the manifest: custom-uploads/extra.txt"),
    ],
)
def test_inspect_says_what_is_wrong_and_exits_1(good_archive, tmp_path, capsys, case, said):
    assert inspect(bad_archive(case, good_archive, tmp_path)) == 1, f"{case}: exit code 1"
    out = capsys.readouterr().out
    assert said in out, f"{case}: inspect must say {said!r}: {out}"
    print_success(f"{case} → 1: {said}")


def test_inspect_reports_a_damaged_archive_and_exits_1(good_archive, tmp_path, capsys):
    """(d) One byte of an entry damaged, the zip structure intact: what ``inspect`` is run for, on a suspect backup."""
    damaged = corrupt(good_archive, tmp_path / "damaged.zip", "custom-uploads/a.txt")
    try:
        code = inspect(damaged)
    except Exception as exc:
        pytest.fail(f"backup inspect crashed with {type(exc).__module__}.{type(exc).__name__} ({exc}) on an archive with one damaged entry, where it must say so and exit 1: cmd_inspect catches ArchiveError and ManifestError only, and check_archive lets zipfile's own errors through")
    assert code == 1, f"a damaged archive is exit code 1, not {code}"
    print_success("damaged archive → 1")


#: Values a crafted archive may carry that a terminal would obey, and how ``inspect`` must show them: each control
#: character as ``?`` (contract §10's ``_safe``: "values read from an archive").
HOSTILE_MANIFEST = {
    "app_version": ("1.2\x1b[2J\x07", "1.2?[2J?"),
    "alembic_revision": ("004\x1b]0;owned\x07", "004?]0;owned?"),
    "integrity_check": ("ok\x1b[31m\r", "ok?[31m?"),
    "unexpected entry": ("custom-uploads/evil\x1b[2J\x9b.txt", "custom-uploads/evil?[2J?.txt"),
}


def test_inspect_prints_no_control_character_from_the_archive(good_archive, tmp_path, capsys):
    """(d) Contract §10, ``_safe`` (found 16/10 and fixed): the manifest's version, revision and integrity, and the names
    of the entries it lists or the zip holds, come from the archive; ``inspect`` is run on a suspect archive by
    definition. Each character that is not printable reaches the terminal as ``?``."""
    raw = {key: value for key, (value, _shown) in HOSTILE_MANIFEST.items()}
    with zipfile.ZipFile(good_archive) as zf:
        manifest = BackupManifest.from_bytes(zf.read(MANIFEST_ENTRY))
    crafted = manifest.model_copy(update={"app_version": raw["app_version"], "alembic_revision": raw["alembic_revision"], "database": manifest.database.model_copy(update={"integrity_check": raw["integrity_check"]})})
    archive = rebuilt(good_archive, tmp_path / "crafted.zip", swap={MANIFEST_ENTRY: crafted.to_bytes()}, add={raw["unexpected entry"]: b"not in the manifest"})
    assert inspect(archive) == 1, "an entry the manifest does not list: exit 1"
    out = capsys.readouterr().out
    # Split on line feeds only: a carriage return left in the output must be seen, not taken for a line break.
    unprintable = sorted({repr(char) for line in out.split("\n") for char in line if not char.isprintable()})
    assert unprintable == [], f"no control character from the archive reaches the terminal: {unprintable} in {out!r}"
    missing = [shown for _raw, shown in HOSTILE_MANIFEST.values() if shown not in out]
    assert missing == [], f"each control character shown as ?: {missing} not in {out!r}"
    print_success("inspect: control characters shown as ?")


# =============================================================================
# (e) cmd_create
# =============================================================================


def test_create_without_a_data_directory_exits_1(tmp_path, monkeypatch, capsys):
    print_section("cmd_create")
    absent = point_at(monkeypatch, tmp_path / "absent")
    assert backup_cli.cmd_create(create_args()) == 1, "no data directory is exit code 1"
    assert "No data directory at" in capsys.readouterr().out, "the command says the data directory is missing"
    assert not absent.exists(), "and does not create it"
    print_success("no data directory → 1")


def test_create_without_a_database_exits_1_and_writes_nothing(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data", database=False))
    before = listing(root)
    assert backup_cli.cmd_create(create_args()) == 1, "no database is exit code 1"
    assert "nothing to back up" in capsys.readouterr().out, "the command says there is no database to back up"
    assert listing(root) == before, f"nothing may be written, not even backups/: {sorted(set(listing(root)) - set(before))}"
    print_success("no database → 1, nothing written")


def test_create_refuses_an_output_file_that_already_exists_before_running(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    existing = tmp_path / "monday.zip"
    existing.write_bytes(b"an archive kept by the user")
    assert backup_cli.cmd_create(create_args(str(existing))) == 1, "an existing --output file is exit code 1"
    assert "already exists" in capsys.readouterr().out, "the command says the file exists"
    assert existing.read_bytes() == b"an archive kept by the user", "the existing file is untouched"
    assert not backups_dir(root).exists(), "no backup ran: nothing was written in the data directory"
    print_success("existing --output file → 1 before any run")


def test_create_writes_the_archive_where_asked_and_removes_its_job(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    nas = tmp_path / "nas"
    nas.mkdir()
    assert backup_cli.cmd_create(create_args(str(nas))) == 0, "a backup into an existing folder is exit code 0"
    written = sorted(nas.iterdir())
    assert len(written) == 1 and re.fullmatch(r"librefolio-backup-\d{8}-\d{6}\.zip", written[0].name), f"the folder receives one archive, named after its time: {[path.name for path in written]}"
    check = check_archive(written[0])
    assert check.ok and check.manifest.origin == "cli", f"the archive checks ok and says the CLI made it: {check}"
    if POSIX:
        assert stat.S_IMODE(written[0].stat().st_mode) == 0o600, "the archive stays readable by its owner only (0600)"
    assert [path.name for path in jobs_dir(root).iterdir() if path.name != ".lock"] == [], "the job's folder is removed once the archive is moved"
    out = capsys.readouterr().out
    assert f"✅ Backup written: {written[0]}" in out and "keep it private" in out, f"the command says where the archive is and that it is private: {out}"
    print_success(f"{written[0].name} written, job folder removed")


@needs_symlinks
@pytest.mark.parametrize("case", ["below-a-file", "dangling-link", "link-to-a-file"])
def test_create_refuses_an_unusable_output_before_running(tmp_path, monkeypatch, capsys, case):
    """(e)(g) The output is checked before the backup: a refusal costs no backup, writes nothing, creates no folder."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    kept = tmp_path / "kept.zip"
    kept.write_bytes(b"an archive kept by the user")
    output = tmp_path / "monday.zip"
    if case == "below-a-file":
        output, said = kept / "2026" / "monday.zip", f"{kept} is not a folder"
    elif case == "dangling-link":
        output.symlink_to(tmp_path / "nowhere.zip")
        said = f"{output} already exists"
    else:
        output.symlink_to(kept)
        said = f"{output} already exists"
    before = listing(tmp_path)
    assert create(str(output)) == 1, f"{case}: an unusable --output is exit code 1"
    out = capsys.readouterr().out
    assert f"❌ {said}" in out, f"{case}: the command says {said!r}: {out}"
    assert "💾 Backing up" not in out and not backups_dir(root).exists(), f"{case}: the backup never started (no backups/, no job folder): {out}"
    assert listing(tmp_path) == before, f"{case}: nothing may be created or written: {sorted(set(listing(tmp_path)) ^ set(before))}"
    assert kept.read_bytes() == b"an archive kept by the user", f"{case}: the file already there is untouched"
    print_success(f"{case}: refused before running — {said}")


@needs_permission_checks
def test_create_refuses_an_output_in_a_folder_it_cannot_write_into(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        code = create(str(locked / "2026" / "monday.zip"))
        created = sorted(path.name for path in locked.iterdir())
    finally:
        locked.chmod(0o700)
    out = capsys.readouterr().out
    assert code == 1 and f"❌ cannot write into {locked}" in out, f"a folder it cannot write into is refused with exit code 1, got {code}: {out}"
    assert created == [] and not backups_dir(root).exists(), f"nothing created there, no backup run: {created}"
    print_success("read-only folder → refused before running")


def test_a_backup_that_fails_creates_none_of_the_folders_of_its_output(tmp_path, monkeypatch, capsys):
    """(e) B1 fix 8: the missing folders of --output come with the archive, so a failed backup leaves no empty one."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))

    def broken_build(*args, **kwargs):
        raise RuntimeError("the build failed")

    monkeypatch.setattr(jobs, "build_archive", broken_build)
    assert create(str(tmp_path / "nas" / "2026" / "monday.zip")) == 1, "a failed backup is exit code 1"
    out = capsys.readouterr().out
    assert "💾 Backing up" in out and "❌ Backup failed (backup_failed)" in out, f"precondition: --output was accepted, the backup ran and failed: {out}"
    assert not (tmp_path / "nas").exists(), f"no folder of --output may be created by a failed backup: {listing(tmp_path / 'nas') if (tmp_path / 'nas').exists() else []}"
    assert job_folders(root) == [], f"the failed job's folder is removed: {job_folders(root)}"
    print_success("failed backup → no folder created for --output")


def test_a_backup_creates_the_missing_folders_of_its_output_with_the_archive(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    output = tmp_path / "nas" / "2026" / "monday.zip"
    assert create(str(output)) == 0, "a backup into folders that do not exist yet is exit code 0"
    assert output.is_file() and check_archive(output).ok, "the archive is where it was asked for, and checks ok"
    assert f"✅ Backup written: {output}" in capsys.readouterr().out, "the command says where it is"
    assert job_folders(root) == [], f"the job's folder is removed: {job_folders(root)}"
    print_success("nas/2026/ created with the archive")


@needs_symlinks
@pytest.mark.parametrize("case", ["backups-is-a-link", "backups-is-a-dangling-link", "backups-is-a-file", "jobs-is-a-link"])
def test_create_names_the_folder_that_is_not_a_plain_folder_and_writes_nothing_through_it(tmp_path, monkeypatch, capsys, case):
    """(e) ``BackupPathError``: exit 1 and a message naming the very folder that is a link or a file (``backups/.jobs``
    when that is the one), never a traceback; nothing is created through the link."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    culprit = jobs_dir(root) if case == "jobs-is-a-link" else backups_dir(root)
    if case == "backups-is-a-link":
        backups_dir(root).symlink_to(elsewhere, target_is_directory=True)
    elif case == "backups-is-a-dangling-link":
        backups_dir(root).symlink_to(tmp_path / "nowhere", target_is_directory=True)
    elif case == "backups-is-a-file":
        backups_dir(root).write_bytes(b"not a folder")
    else:
        backups_dir(root).mkdir()
        jobs_dir(root).symlink_to(elsewhere, target_is_directory=True)
    assert create() == 1, f"{case}: exit code 1"
    out = capsys.readouterr().out
    assert f"❌ {culprit} is not a plain folder (a link, or a file)" in out, f"{case}: the message names {culprit}: {out}"
    if case == "jobs-is-a-link":
        assert f"❌ {backups_dir(root)} is not a plain folder" not in out, f"backups/ is a plain folder: the message must name .jobs, not backups/: {out}"
    assert list(elsewhere.iterdir()) == [], f"{case}: nothing may be created through the link: {sorted(path.name for path in elsewhere.iterdir())}"
    assert not (tmp_path / "nowhere").exists(), f"{case}: a dangling link is not made to point to a new folder"
    print_success(f"{case}: names {culprit.name}, exit 1, nothing written through it")


def test_create_reports_an_error_that_keeps_the_run_from_starting(tmp_path, monkeypatch, capsys):
    """(e) Any ``OSError`` of ``jobs.run_backup`` before the run (backups/ cannot be written): a message, exit 1."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))

    def cannot_start(**kwargs):
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), str(jobs_dir(root)))

    monkeypatch.setattr(jobs, "run_backup", cannot_start)
    assert create() == 1, "a run that cannot start is exit code 1"
    out = capsys.readouterr().out
    assert f"❌ The backup could not run in {backups_dir(root)}: {os.strerror(errno.EACCES)}" in out, f"the message says where and why: {out}"
    print_success("OSError before the run → message, exit 1")


@needs_permission_checks
def test_create_reports_a_backups_folder_it_cannot_write_into(tmp_path, monkeypatch, capsys):
    """(e) The same, for real: ``backups/`` read-only, so ``backups/.jobs`` cannot be created."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    backups_dir(root).mkdir()
    backups_dir(root).chmod(0o500)
    try:
        code = create()
        created = sorted(path.name for path in backups_dir(root).iterdir())
    finally:
        backups_dir(root).chmod(0o700)
    out = capsys.readouterr().out
    assert code == 1 and f"❌ The backup could not run in {backups_dir(root)}: {os.strerror(errno.EACCES)}" in out, f"a read-only backups/ is exit code 1 with the reason, got {code}: {out}"
    assert created == [], f"nothing is created in it: {created}"
    print_success("read-only backups/ → message, exit 1")


def test_create_that_cannot_write_its_output_puts_the_archive_in_the_backups_folder_and_exits_1(tmp_path, monkeypatch, capsys):
    """(e)(i) The disk of --output fills up during the copy: no partial file left there, the archive in backups/."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    (tmp_path / "nas").mkdir()
    output = tmp_path / "nas" / "monday.zip"
    failing_move(monkeypatch, no_space(), target=output, partial=b"PK half an archive")
    assert create(str(output)) == 1, "an archive written elsewhere than asked is exit code 1"
    out = capsys.readouterr().out
    written = sorted(backups_dir(root).glob("*.zip"))
    assert len(written) == 1, f"the archive lands in <data dir>/backups/: {[path.name for path in written]}"
    assert f"⚠️  cannot write {output}: {os.strerror(errno.ENOSPC)}: the archive was written to {written[0]} instead" in out, f"the command says why and where: {out}"
    assert "✅" not in out, f"an archive not where it was asked for is not reported as written there: {out}"
    assert not output.exists(), "no partial archive is left at --output"
    assert check_archive(written[0]).ok, "the archive in backups/ is whole"
    assert job_folders(root) == [], f"the job's folder is removed: {job_folders(root)}"
    print_success(f"--output full → {written[0].name} in backups/, exit 1")


def test_create_whose_archive_cannot_leave_its_job_folder_says_where_it_stays(tmp_path, monkeypatch, capsys):
    """(e)(i) Default place, and the move into backups/ fails: the archive stays in its job folder, which is kept."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    failing_move(monkeypatch, OSError(errno.EIO, os.strerror(errno.EIO)))
    assert create() == 1, "an archive left in its job folder is exit code 1"
    out = capsys.readouterr().out
    folders = job_folders(root)
    assert len(folders) == 1, f"the job's folder is kept, it holds the archive: {folders}"
    kept = sorted(job_dir(root, folders[0]).glob("*.zip"))
    assert len(kept) == 1 and check_archive(kept[0]).ok, f"the archive is whole in its job folder: {[path.name for path in kept]}"
    said = f"❌ cannot write {backups_dir(root) / kept[0].name}: {os.strerror(errno.EIO)}: the archive stays in {kept[0]}. Move it within the hour"
    assert said in out, f"the command says where the archive stays and for how long: {out}"
    assert sorted(backups_dir(root).glob("*.zip")) == [], "no archive reached backups/"
    print_success("move failed → archive kept in its job folder, path said, exit 1")


@pytest.mark.parametrize("into", ["backups-folder", "output-folder"])
def test_backups_of_the_same_second_keep_their_own_names(tmp_path, monkeypatch, capsys, into):
    """(e)(h) Three backups of one second into one folder: -2, -3, each exit 0 (the second used to stay in its job)."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    monkeypatch.setattr(jobs, "archive_name", lambda created_at: NAME)
    folder = tmp_path / "nas" if into == "output-folder" else backups_dir(root)
    if into == "output-folder":
        folder.mkdir()
    codes = [create(str(folder) if into == "output-folder" else None) for _ in range(3)]
    out = capsys.readouterr().out
    assert codes == [0, 0, 0], f"every backup of the same second is exit code 0: {codes}\n{out}"
    names = sorted(path.name for path in folder.glob("*.zip"))
    assert names == sorted([NAME, SECOND_NAME, THIRD_NAME]), f"each archive keeps its own name: {names}"
    for name in (NAME, SECOND_NAME, THIRD_NAME):
        assert f"✅ Backup written: {folder / name}" in out and check_archive(folder / name).ok, f"{name} is written, said, and checks ok: {out}"
    assert job_folders(root) == [], f"every job folder is removed: {job_folders(root)}"
    print_success(f"{into}: {', '.join(names)}")


def test_create_prints_a_left_out_name_with_its_control_characters_as_question_marks(tmp_path, monkeypatch, capsys):
    """(e) The names a backup left out are printed through ``_safe``: each control character as ``?``. The build is the
    real one; only the list of names it left out gains one (no unreadable file is needed)."""
    point_at(monkeypatch, make_data_dir(tmp_path / "data"))
    real_build = jobs.build_archive
    hostile = "custom-uploads/evil\x1b[2J\x07.txt"

    def build_leaving_out_a_name(*args, **kwargs):
        built = real_build(*args, **kwargs)
        return replace(built, skipped=(*built.skipped, hostile))

    monkeypatch.setattr(jobs, "build_archive", build_leaving_out_a_name)
    assert create() == 0, "a backup that left a file out is still written: exit code 0"
    lines = capsys.readouterr().out.split("\n")
    unprintable = sorted({repr(char) for line in lines for char in line if not char.isprintable()})
    assert unprintable == [] and "     custom-uploads/evil?[2J?.txt" in lines, f"the left-out name, its control characters as ?: {unprintable} {lines}"
    print_success("left-out name printed with ?")


# =============================================================================
# (f) the script
# =============================================================================


def child_env(data: Path) -> dict[str, str]:
    """This process's environment without what could point a child elsewhere (or start coverage in it), plus the data dir."""
    env = {name: value for name, value in os.environ.items() if not name.startswith(("LIBREFOLIO_", "COVERAGE_"))}
    env.update(LIBREFOLIO_DATA_DIR=str(data), LF_APP_VERSION=APP_VERSION, PYTHONUNBUFFERED="1", PYTHONUTF8="1")
    return env


def script(*argv: str, env: dict[str, str], cwd: Path) -> subprocess.CompletedProcess:
    command = [sys.executable, str(SCRIPT), *argv]
    try:
        return subprocess.run(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=CLI_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"`{shlex.join(command)}` did not end within {CLI_TIMEOUT}s: {exc.stdout!r} {exc.stderr!r}")


def test_the_script_creates_an_archive_then_inspects_it(tmp_path):
    """(f) ``python scripts/backup_cli.py create`` then ``inspect``, as ``dev.py backup`` will run them."""
    print_section("python scripts/backup_cli.py")
    data = make_data_dir(tmp_path / "data").resolve()
    env = child_env(data)
    created = script("create", env=env, cwd=tmp_path)
    assert created.returncode == 0, f"create must exit 0, it exited {created.returncode}\n--- stdout\n{created.stdout[-TAIL:]}\n--- stderr\n{created.stderr[-TAIL:]}"
    written = sorted(backups_dir(data).glob("*.zip"))
    assert len(written) == 1, f"create writes one archive in <data dir>/backups/: {[path.name for path in written]}"
    assert [path.name for path in jobs_dir(data).iterdir() if path.name != ".lock"] == [], "the job's folder is removed"
    with zipfile.ZipFile(written[0]) as zf:
        manifest = BackupManifest.from_bytes(zf.read(MANIFEST_ENTRY))
    assert (manifest.origin, manifest.app_version, manifest.alembic_revision) == ("cli", APP_VERSION, REVISION), f"the archive was made by the CLI of this test: {manifest.origin}, {manifest.app_version}, {manifest.alembic_revision}"
    inspected = script("inspect", str(written[0]), env=env, cwd=tmp_path)
    assert inspected.returncode == 0 and "Every entry matches the manifest" in inspected.stdout, f"inspect must exit 0 on it\n--- stdout\n{inspected.stdout[-TAIL:]}\n--- stderr\n{inspected.stderr[-TAIL:]}"
    print_success(f"create → {written[0].name}, inspect → 0")


def test_the_script_without_a_command_exits_1(tmp_path):
    done = script(env=child_env(tmp_path / "data"), cwd=tmp_path)
    assert done.returncode == 1 and "backup command required" in done.stdout, f"no command: exit 1 and a hint, got {done.returncode}\n{done.stdout[-TAIL:]}{done.stderr[-TAIL:]}"
    print_success("no command → exit 1")


# =============================================================================
# (g) _check_output
# =============================================================================


def test_check_output_accepts_an_existing_folder_and_a_new_file_path_and_creates_nothing(tmp_path):
    """(g) A folder receives the archive under its own name, whatever it holds (B1 fix 2: a ``librefolio-backup.zip``
    in it read as "already exists"); the missing folders of a new file path are left for the archive to bring."""
    print_section("_check_output")
    nas = tmp_path / "nas"
    nas.mkdir()
    (nas / "librefolio-backup.zip").write_bytes(b"an archive kept by the user")
    before = listing(tmp_path)
    for output in (str(nas), f"{nas}/", str(nas / "monday.zip"), str(tmp_path / "new" / "2026" / "monday.zip")):
        problem = backup_cli._check_output(output)
        assert problem is None, f"--output {output} must be accepted, not refused with {problem!r}"
    assert listing(tmp_path) == before, f"the check creates nothing: {sorted(set(listing(tmp_path)) ^ set(before))}"
    print_success("existing folder, new file, new folders → accepted, nothing created")


@needs_symlinks
@pytest.mark.parametrize("taken_by", ["file", "link-to-a-file", "dangling-link"])
def test_check_output_refuses_a_file_path_already_taken(tmp_path, taken_by):
    """(g) An archive never replaces a file, and a link at its place, dangling or not, is never written through."""
    kept = tmp_path / "kept.zip"
    kept.write_bytes(b"an archive kept by the user")
    path = tmp_path / "monday.zip"
    if taken_by == "file":
        path.write_bytes(b"an archive kept by the user")
    elif taken_by == "link-to-a-file":
        path.symlink_to(kept)
    else:
        path.symlink_to(tmp_path / "nowhere.zip")
    expected = f"{path} already exists: choose another name or folder"
    assert backup_cli._check_output(str(path)) == expected, f"{taken_by}: must be refused with {expected!r}"
    assert kept.read_bytes() == b"an archive kept by the user" and not (tmp_path / "nowhere.zip").exists(), f"{taken_by}: nothing written through it"
    print_success(f"{taken_by} → already exists")


@pytest.mark.parametrize("where", ["in-it", "folders-below-it"])
def test_check_output_refuses_a_path_where_a_file_stands_for_a_folder(tmp_path, where):
    blocker = tmp_path / "nas"
    blocker.write_bytes(b"a file where a folder belongs")
    output = blocker / "monday.zip" if where == "in-it" else blocker / "2026" / "10" / "monday.zip"
    expected = f"{blocker} is not a folder: choose another path"
    assert backup_cli._check_output(str(output)) == expected, f"{where}: the nearest existing part of the path is a file: {expected!r}"
    assert blocker.read_bytes() == b"a file where a folder belongs", "the file is untouched"
    print_success(f"{where} → is not a folder")


@needs_permission_checks
@pytest.mark.parametrize("output", ["the-folder", "a-file-in-it", "a-file-below-it"])
def test_check_output_refuses_a_folder_it_cannot_write_into(tmp_path, output):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    path = {"the-folder": locked, "a-file-in-it": locked / "monday.zip", "a-file-below-it": locked / "2026" / "monday.zip"}[output]
    try:
        problem = backup_cli._check_output(str(path))
        created = sorted(entry.name for entry in locked.iterdir())
    finally:
        locked.chmod(0o700)
    expected = f"cannot write into {locked}: choose another folder, or run the command as a user who can"
    assert problem == expected, f"{output}: the nearest existing folder is read-only: {expected!r}, not {problem!r}"
    assert created == [], f"{output}: nothing created in it: {created}"
    print_success(f"{output} → cannot write into")


def test_check_output_reads_a_relative_or_home_path_as_the_command_does(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / "nas").mkdir(parents=True)
    (home / "nas" / "monday.zip").write_bytes(b"an archive kept by the user")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(home / "nas")
    expected = f"{Path.cwd() / 'monday.zip'} already exists: choose another name or folder"
    assert backup_cli._check_output("monday.zip") == expected, "a relative path is checked from the working directory"
    assert backup_cli._check_output("~/nas/monday.zip") == f"{home / 'nas' / 'monday.zip'} already exists: choose another name or folder", "~ is the home folder"
    assert backup_cli._check_output("tuesday.zip") is None, "a free relative name is accepted"
    print_success("relative and ~ paths checked where they point")


# =============================================================================
# (h) _free_path
# =============================================================================


@needs_symlinks
def test_free_path_takes_the_next_number_past_every_name_taken(tmp_path):
    print_section("_free_path")
    folder = tmp_path / "nas"
    folder.mkdir()
    assert backup_cli._free_path(folder, NAME) == folder / NAME, "a free name is kept"
    (folder / NAME).write_bytes(b"first")
    assert backup_cli._free_path(folder, NAME) == folder / SECOND_NAME, "taken by a file: -2, before the suffix"
    (folder / SECOND_NAME).symlink_to(tmp_path / "nowhere.zip")
    assert backup_cli._free_path(folder, NAME) == folder / THIRD_NAME, "a dangling link takes its name too"
    (folder / THIRD_NAME).mkdir()
    assert backup_cli._free_path(folder, NAME) == folder / "librefolio-backup-20261015-101500-4.zip", "and so does a folder"
    assert sorted(path.name for path in folder.iterdir()) == sorted([NAME, SECOND_NAME, THIRD_NAME]), "it chooses a name, it creates nothing"
    assert not (tmp_path / "nowhere.zip").exists(), "the dangling link is not followed"
    print_success("name, -2, -3, -4")


# =============================================================================
# (i) _place_archive
# =============================================================================


def test_place_moves_the_archive_to_its_target_creating_the_missing_folders(tmp_path):
    print_section("_place_archive")
    data = tmp_path / "data"
    source = job_archive(data)
    target = tmp_path / "nas" / "2026" / "monday.zip"
    assert backup_cli._place_archive(source, target, data) == (target, None), "a move that succeeds returns the target and no problem"
    assert sha256_of(target) == EXPECTED_SHA, "the target holds the archive's bytes"
    assert not source.exists(), "the archive left its job folder"
    print_success("moved, nas/2026/ created")


@needs_symlinks
@pytest.mark.parametrize("taken_by", ["file", "dangling-link"])
def test_place_never_replaces_a_taken_target_and_falls_back_to_the_backups_folder(tmp_path, taken_by):
    data = tmp_path / "data"
    source = job_archive(data)
    (tmp_path / "nas").mkdir()
    target = tmp_path / "nas" / "monday.zip"
    if taken_by == "file":
        target.write_bytes(b"an archive kept by the user")
    else:
        target.symlink_to(tmp_path / "nowhere.zip")
    placed, problem = backup_cli._place_archive(source, target, data)
    assert (placed, problem) == (backups_dir(data) / NAME, f"{target} already exists"), f"{taken_by}: into backups/, with the reason: {placed}, {problem!r}"
    assert sha256_of(placed) == EXPECTED_SHA and not source.exists(), f"{taken_by}: the archive is whole where it is said to be"
    if taken_by == "file":
        assert target.read_bytes() == b"an archive kept by the user", "the file at the target is untouched"
    else:
        assert target.is_symlink() and not (tmp_path / "nowhere.zip").exists(), "the link is neither replaced nor followed"
    print_success(f"{taken_by} at the target → backups/{placed.name}")


def test_place_falls_back_under_a_free_name(tmp_path):
    data = tmp_path / "data"
    source = job_archive(data)
    (backups_dir(data) / NAME).write_bytes(b"an archive of the same second")
    (tmp_path / "nas").mkdir()
    target = tmp_path / "nas" / "monday.zip"
    target.write_bytes(b"an archive kept by the user")
    placed, _ = backup_cli._place_archive(source, target, data)
    assert placed == backups_dir(data) / SECOND_NAME and sha256_of(placed) == EXPECTED_SHA, f"backups/ holds the name: the archive takes -2, {placed}"
    assert (backups_dir(data) / NAME).read_bytes() == b"an archive of the same second", "the archive already there is untouched"
    print_success(f"fallback → {SECOND_NAME}")


@pytest.mark.parametrize(
    ("device", "spare", "lands"),
    [
        pytest.param("other", -1, "backups", id="other-device-one-byte-short"),
        pytest.param("other", 0, "target", id="other-device-exactly-enough"),
        pytest.param("same", -1, "target", id="same-device-a-rename-needs-no-space"),
    ],
)
def test_place_checks_the_space_of_another_device_before_moving(tmp_path, monkeypatch, device, spare, lands):
    """(i) On another device the archive is copied, so it needs its size free there; on the same one it is renamed."""
    data = tmp_path / "data"
    source = job_archive(data)
    nas = tmp_path / "nas"
    nas.mkdir()
    target = nas / "monday.zip"
    free_space(monkeypatch, nas, len(ARCHIVE_BYTES) + spare)
    if device == "other":
        monkeypatch.setattr(backup_cli, "os", OsStandIn(other_device=nas))
    placed, problem = backup_cli._place_archive(source, target, data)
    if lands == "target":
        assert (placed, problem) == (target, None), f"{device} device, {spare:+d} byte(s) spare: the archive goes to its target: {placed}, {problem!r}"
    else:
        expected = f"not enough free space in {nas} for {backup_cli._human(len(ARCHIVE_BYTES))}"
        assert (placed, problem) == (backups_dir(data) / NAME, expected), f"one byte short on another device: into backups/, {expected!r}: {placed}, {problem!r}"
        assert not target.exists(), "nothing is written at the target"
    assert sha256_of(placed) == EXPECTED_SHA and not source.exists(), "the archive is whole where it is said to be"
    print_success(f"{device} device, {spare:+d} → {lands}")


@pytest.mark.parametrize("partial", [b"", b"PK half an archive"], ids=["nothing-written", "half-written"])
def test_place_removes_a_partial_copy_and_falls_back_when_the_move_fails(tmp_path, monkeypatch, partial):
    data = tmp_path / "data"
    source = job_archive(data)
    (tmp_path / "nas").mkdir()
    target = tmp_path / "nas" / "monday.zip"
    failing_move(monkeypatch, no_space(), target=target, partial=partial)
    placed, problem = backup_cli._place_archive(source, target, data)
    expected = f"cannot write {target}: {os.strerror(errno.ENOSPC)}"
    assert (placed, problem) == (backups_dir(data) / NAME, expected), f"a failed move falls back to backups/ with {expected!r}: {placed}, {problem!r}"
    assert not target.exists(), "no partial copy is left at the target"
    assert sha256_of(placed) == EXPECTED_SHA, "the archive is whole in backups/"
    print_success(f"move failed ({'half-written' if partial else 'nothing written'}) → backups/, target clean")


def test_a_move_that_fails_once_the_archive_left_its_job_folder_never_removes_the_only_copy(tmp_path, monkeypatch):
    """(i) The move raises, but the archive has left its job folder and is at the target: it got there whole (a rename
    is atomic; a move to another disk removes its source only after a complete copy). It is reported as written there,
    ``(target, None)``, never as a failure pointing at a job folder that no longer holds it; and the target, its only
    copy, is never removed."""
    data = tmp_path / "data"
    source = job_archive(data)
    (tmp_path / "nas").mkdir()
    target = tmp_path / "nas" / "monday.zip"

    def move_then_fail(src, dst, *args, **kwargs):
        os.replace(src, dst)
        raise OSError(errno.EIO, os.strerror(errno.EIO))

    monkeypatch.setattr(backup_cli.shutil, "move", move_then_fail)
    placed, problem = backup_cli._place_archive(source, target, data)
    assert not source.exists(), "precondition: the archive had left its job folder when the move failed"
    assert target.is_file() and sha256_of(target) == EXPECTED_SHA, "the target, the archive's only copy, is kept whole"
    assert (placed, problem) == (target, None), f"the archive is whole at the target: reported written there, not as a failure pointing at a job folder that no longer holds it: {placed}, {problem!r}"
    print_success("raised after the archive arrived → (target, None), the only copy kept")


def test_an_archive_bound_for_the_backups_folder_stays_in_its_job_folder_when_the_move_fails(tmp_path, monkeypatch):
    """(i) The fallback is the target's own folder: trying it again is pointless, the archive stays where it is."""
    data = tmp_path / "data"
    source = job_archive(data)
    target = backups_dir(data) / NAME
    failing_move(monkeypatch, OSError(errno.EIO, os.strerror(errno.EIO)), target=target)
    placed, problem = backup_cli._place_archive(source, target, data)
    assert (placed, problem) == (source, f"cannot write {target}: {os.strerror(errno.EIO)}"), f"the archive stays in its job folder, the reason given: {placed}, {problem!r}"
    assert sha256_of(placed) == EXPECTED_SHA, "the archive is whole in its job folder"
    assert sorted(path.name for path in backups_dir(data).iterdir()) == [".jobs"], "nothing reached backups/"
    print_success("bound for backups/, move failed → stays in its job folder")


def test_an_archive_that_cannot_be_renamed_into_the_backups_folder_stays_in_its_job_folder(tmp_path, monkeypatch):
    data = tmp_path / "data"
    source = job_archive(data)
    (tmp_path / "nas").mkdir()
    target = tmp_path / "nas" / "monday.zip"
    target.write_bytes(b"an archive kept by the user")
    monkeypatch.setattr(backup_cli, "os", OsStandIn(rename_error=PermissionError(errno.EACCES, os.strerror(errno.EACCES))))
    placed, problem = backup_cli._place_archive(source, target, data)
    assert (placed, problem) == (source, f"{target} already exists"), f"neither the target nor backups/: the archive stays, the first reason given: {placed}, {problem!r}"
    assert sha256_of(placed) == EXPECTED_SHA, "the archive is whole in its job folder"
    print_success("target taken, rename refused → stays in its job folder")


@pytest.mark.parametrize("failure", ["no-space-on-another-device", "the-move-fails"])
def test_a_target_the_archive_never_reached_leaves_none_of_the_folders_created_for_it(tmp_path, monkeypatch, failure):
    """(i) B1 fix 8: the missing folders of --output are created only when the archive gets there. ``nas/`` exists and
    the archive is bound for ``nas/2026/10/``. On another disk without the space, the check runs on ``nas``, the nearest
    folder that exists, before anything is created; when the move fails, the two folders made for it are removed again,
    deepest first. Either way the archive goes to backups/ and ``nas`` is left as it was."""
    data = tmp_path / "data"
    source = job_archive(data)
    nas = tmp_path / "nas"
    nas.mkdir()
    older = nas / "librefolio-backup-20261014-090000.zip"
    older.write_bytes(b"an older archive")
    target = nas / "2026" / "10" / "monday.zip"
    if failure == "no-space-on-another-device":
        free_space(monkeypatch, nas, 0)
        monkeypatch.setattr(backup_cli, "os", OsStandIn(other_device=nas))
        expected = f"not enough free space in {nas} for {backup_cli._human(len(ARCHIVE_BYTES))}"
    else:
        failing_move(monkeypatch, no_space(), target=target, partial=b"PK half an archive")
        expected = f"cannot write {target}: {os.strerror(errno.ENOSPC)}"
    placed, problem = backup_cli._place_archive(source, target, data)
    assert sorted(os.listdir(nas)) == [older.name], f"{failure}: the archive never reached {target}, so no folder made for it may be left in nas/: {listing(nas)}"
    assert older.read_bytes() == b"an older archive", f"{failure}: what nas/ held is untouched"
    assert (placed, problem) == (backups_dir(data) / NAME, expected), f"{failure}: into backups/, with {expected!r}: {placed}, {problem!r}"
    assert sha256_of(placed) == EXPECTED_SHA, "the archive is whole in backups/"
    print_success(f"{failure}: {expected}; nas/ as it was")


# =============================================================================
# (j) the help
# =============================================================================


def help_of(monkeypatch, capsys, *command: str) -> str:
    """What ``dev.py <command> --help`` prints, its whitespace collapsed: the wrapping depends on the terminal."""
    monkeypatch.setenv("COLUMNS", "120")
    parser = argparse.ArgumentParser(prog="dev.py")
    backup_cli.register_subparser(parser.add_subparsers(dest="command"))
    with pytest.raises(SystemExit) as done:
        parser.parse_args([*command, "--help"])
    assert done.value.code == 0, f"{' '.join(command)} --help exits 0, not {done.value.code}"
    return " ".join(capsys.readouterr().out.split())


def test_the_help_says_what_no_verify_compares_and_where_a_relative_path_starts(monkeypatch, capsys):
    print_section("Help")
    group = help_of(monkeypatch, capsys, "backup")
    assert "A relative path starts from the project root, like every path given to dev.py." in group, f"backup --help says where a relative path starts: {group}"
    inspect_help = help_of(monkeypatch, capsys, "backup", "inspect")
    assert "--no-verify Compare the entry names with the manifest without reading the entries (faster)" in inspect_help, f"--no-verify says it still compares the names: {inspect_help}"
    create_help = help_of(monkeypatch, capsys, "backup", "create")
    assert "checked before the backup starts" in create_help, f"--output says it is checked first: {create_help}"
    print_success("--no-verify, --output and the relative-path line")


# =============================================================================
# (k) cmd_restore
# =============================================================================


#: The accounts of the restore cases, in the order they are inserted: (username, is_active, is_superuser).
RESTORE_ACCOUNTS = (("zoe_admin", 1, 1), ("bob_user", 1, 0), ("olga_former_admin", 0, 1), ("ada_admin", 1, 1))
#: A user and a disabled administrator: nobody could manage the instance after a restore.
WITHOUT_ADMINISTRATOR = (("bob_user", 1, 0), ("olga_former_admin", 0, 1))
CREATED = "2026-10-15 10:15:00.000000"
#: The last line of a dry run that found the archive restorable.
RESTORABLE_LINE = "✅ The archive can be restored. Dry run: the instance was left as it is, and the copy removed."
#: The one notice the report gives, under the administrators, of the invitations and links after a restore (developer decision P11): verbatim.
ACCOUNT_LINK_LINES = ("   Invitations and links sent before the restore will have expired: send them again if needed.",)
#: What the report says of the ledger's totals, right after «Files: …» (lot B-13, contract §5 and §7.5): verbatim.
LEDGER_SAME = "   Ledger totals: the same as when the backup was made"
LEDGER_ABSENT = "   Ledger totals: not recorded in this archive"
LEDGER_OTHER_VERSION = "   Ledger totals: recorded by another version of the method, not compared"
LEDGER_UNREADABLE = "⚠️  Ledger totals: could not be read on the copy"
#: And among the warnings, at the end of the report.
LEDGER_WARNINGS = {
    "control_totals_changed": "⚠️  The ledger's totals differ from those the backup recorded (listed above)",
    "control_totals_unreadable": "⚠️  The ledger's totals could not be read on the copy",
}


@pytest.fixture(scope="module")
def head_database(tmp_path_factory) -> Path:
    """A real database at this LibreFolio's head, made once by ``alembic upgrade head`` in a process of its own, in
    rollback-journal mode so that a copy of the file is the whole database."""
    root = tmp_path_factory.mktemp("migrated")
    database, configured = root / "head.db", root / "configured-data-dir"
    command = [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), "-x", f"sqlalchemy.url=sqlite:///{database}", "upgrade", "head"]
    try:
        done = subprocess.run(command, cwd=PROJECT_ROOT, env=child_env(configured), stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", timeout=5 * CLI_TIMEOUT, check=False)
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"precondition: alembic upgrade head did not end within {5 * CLI_TIMEOUT}s: {exc.stdout!r} {exc.stderr!r}")
    assert done.returncode == 0, f"precondition: alembic upgrade head of a new database exited {done.returncode}\n--- stdout\n{done.stdout[-TAIL:]}\n--- stderr\n{done.stderr[-TAIL:]}"
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("PRAGMA journal_mode=DELETE")
    assert not configured.exists(), f"alembic wrote in the configured data directory: {listing(configured)}"
    return database


def restorable(tmp_path: Path, database: Path, accounts=RESTORE_ACCOUNTS) -> Path:
    """The archive of a data directory whose database is a copy of ``database`` with ``accounts``, and ``FILES``."""
    data = make_data_dir(tmp_path / "source", database=False)
    (data / DATABASE_ENTRY).parent.mkdir(parents=True)
    shutil.copyfile(database, data / DATABASE_ENTRY)
    with closing(sqlite3.connect(data / DATABASE_ENTRY)) as conn, conn:
        conn.executemany(
            "INSERT INTO users (username, email, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(name, f"{name}@example.test", "$argon2id$not-a-real-hash", active, admin, CREATED, CREATED) for name, active, admin in accounts],
        )
    work = tmp_path / "work"
    work.mkdir()
    return build_archive(data, work, work / NAME, origin="cli").path


def revision_in(archive: Path) -> str | None:
    with zipfile.ZipFile(archive) as zf:
        return BackupManifest.from_bytes(zf.read(MANIFEST_ENTRY)).alembic_revision


def restore(path: Path, *, dry_run: bool = True, yes: bool = False) -> int:
    """``cmd_restore`` as ``dev.py backup restore`` runs it (argparse always sets ``yes``); an exception escaping it is a
    traceback for the user."""
    try:
        return backup_cli.cmd_restore(argparse.Namespace(test_db=False, archive=str(path), dry_run=dry_run, yes=yes))
    except Exception as exc:
        pytest.fail(f"backup restore raised {type(exc).__name__} ({exc}): the user would get a traceback instead of a message and exit code 1")


def stages_left(root: Path) -> list[str]:
    """What ``.restore/stage/`` holds but its lock: the copies a dry run left behind."""
    folder = stages_dir(root)
    return sorted(path.name for path in folder.iterdir() if path.name != STAGE_LOCK_FILE) if folder.is_dir() else []


def outside_restore(root: Path) -> list[str]:
    return [name for name in listing(root) if not name.startswith(".restore")]


@pytest.mark.parametrize("yes", [False, True], ids=["without-yes", "with-yes"])
def test_restore_without_dry_run_of_a_missing_file_exits_1_and_creates_nothing(tmp_path, monkeypatch, capsys, yes):
    """(k) The restore itself (lot B3) refuses a missing archive before anything else, ``--yes`` or not: no check, no
    copy, not even ``.restore``. The rest of the restore is pinned by ``test_backup_cli_restore.py``."""
    print_section("cmd_restore")
    root = point_at(monkeypatch, make_data_dir(tmp_path / "instance"))
    before = listing(root)
    assert restore(tmp_path / "absent.zip", dry_run=False, yes=yes) == 1, "a missing archive is exit code 1"
    assert f"❌ No file at {tmp_path / 'absent.zip'}" in capsys.readouterr().out, "the command says there is no file"
    assert listing(root) == before, f"nothing is created in the data directory, not even .restore: {sorted(set(listing(root)) - set(before))}"
    print_success(f"no --dry-run, {'--yes' if yes else 'no --yes'}, missing file → 1, nothing created")


def test_restore_of_a_missing_file_exits_1_and_creates_nothing(tmp_path, monkeypatch, capsys):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "instance"))
    before = listing(root)
    assert restore(tmp_path / "absent.zip") == 1, "a missing archive is exit code 1"
    assert f"❌ No file at {tmp_path / 'absent.zip'}" in capsys.readouterr().out, "the command says there is no file"
    assert listing(root) == before, f"nothing is created: {sorted(set(listing(root)) - set(before))}"
    print_success("missing file → 1, nothing created")


def test_a_dry_run_reports_what_a_restore_would_do_and_removes_its_copy(tmp_path, monkeypatch, capsys, head_database):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "instance"))
    archive = restorable(tmp_path, head_database)
    before, database = listing(root), sha256_of(root / DATABASE_ENTRY)
    code = restore(archive)
    out = capsys.readouterr().out
    assert code == 0, f"a restorable archive is exit code 0: {out}"
    said = [
        f"🔎 Checking {archive} on a copy, in {stages_dir(root)}",
        "   … checking",
        "   … unpacking",
        "   … verifying",
        f"📦 Made by LibreFolio {APP_VERSION} (cli)",
        f"   Database: revision {revision_in(archive)}, this LibreFolio's own: restored as it is",
        f"   Files: {len(FILES)}",
        LEDGER_SAME,
        "   Instance key: not included",
        "   Administrators: ada_admin, zoe_admin",
        *ACCOUNT_LINK_LINES,
        RESTORABLE_LINE,
    ]
    assert [line for line in said if line not in out] == [], f"the dry run says what a restore would do: {out}"
    assert [line for line in ACCOUNT_LINK_LINES if line not in out.splitlines()] == [], f"the notice on the invitations and links, a whole line, verbatim: {out}"
    former_lines = [line for line in out.splitlines() if any(word in line.lower() for word in ("email verification", "waiting", "activates it", "send new ones", "stop working"))]
    assert former_lines == [], f"that one notice and nothing more (P11): neither the line on the links that stop working nor the one on the accounts waiting for their email verification comes back: {former_lines}"
    assert "… upgrading" not in out and "⚠️" not in out and "❌" not in out, f"at the head: no upgrade, nothing to warn: {out}"
    assert stages_left(root) == [], f"the copy is removed: {stages_left(root)}"
    assert (outside_restore(root), sha256_of(root / DATABASE_ENTRY)) == (before, database), "the data directory is as it was"
    print_success("dry run → 0, report printed, copy removed")


def test_a_dry_run_of_a_backup_without_administrator_exits_1_and_says_why(tmp_path, monkeypatch, capsys, head_database):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "instance"))
    assert restore(restorable(tmp_path, head_database, WITHOUT_ADMINISTRATOR)) == 1, "a blocked restore is exit code 1"
    out = capsys.readouterr().out
    assert "❌ The backup has no active administrator: after a restore nobody could manage the instance" in out, f"the blocker is said: {out}"
    assert "Administrators:" not in out and "✅" not in out, f"no administrator named, nothing called restorable: {out}"
    assert stages_left(root) == [], f"the copy is removed: {stages_left(root)}"
    print_success("no active administrator → 1")


@pytest.mark.parametrize(
    ("case", "code"),
    [
        ("not-a-zip", "not_a_backup"),
        ("no-manifest", "not_a_backup"),
        ("another-librefolio", "revision_unknown"),
        ("altered-entry", "checksum_mismatch"),
        ("added-entry", "unexpected_entry"),
    ],
)
def test_a_dry_run_of_a_refused_archive_exits_1_with_its_code(good_archive, tmp_path, monkeypatch, capsys, case, code):
    """(k) ``another-librefolio``: the archives of (d), whose database records a revision this LibreFolio's migrations
    do not have."""
    root = point_at(monkeypatch, make_data_dir(tmp_path / "instance"))
    archive = good_archive if case == "another-librefolio" else bad_archive(case, good_archive, tmp_path)
    assert restore(archive) == 1, f"{case}: exit code 1"
    out = capsys.readouterr().out
    assert f"({code})" in out and "❌" in out and "✅" not in out, f"{case}: the refusal and its code {code}: {out}"
    assert stages_left(root) == [], f"{case}: no copy left: {stages_left(root)}"
    print_success(f"{case} → 1 ({code})")


def test_a_dry_run_while_another_check_runs_exits_1(tmp_path, monkeypatch, capsys, head_database):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "instance"))
    archive = restorable(tmp_path, head_database)
    ensure_private_dir(stages_dir(root), root)
    holder = jobs._RunLock(stages_dir(root) / STAGE_LOCK_FILE)
    assert holder.try_acquire(), "precondition: the lock of the checks is free"
    try:
        code = restore(archive)
    finally:
        holder.release()
    out = capsys.readouterr().out
    assert code == 1 and "❌ Another archive is being checked" in out, f"busy: exit code 1 and a message, got {code}: {out}"
    assert stages_left(root) == [], f"no copy made: {stages_left(root)}"
    print_success("another check running → 1")


@needs_symlinks
def test_a_dry_run_names_a_restore_folder_that_is_a_link_and_writes_nothing_through_it(tmp_path, monkeypatch, capsys, head_database):
    root = point_at(monkeypatch, make_data_dir(tmp_path / "instance"))
    archive = restorable(tmp_path, head_database)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    restore_dir(root).symlink_to(elsewhere, target_is_directory=True)
    assert restore(archive) == 1, ".restore a link: exit code 1"
    out = capsys.readouterr().out
    assert f"❌ {restore_dir(root)} is not a plain folder (a link, or a file)" in out, f"the message names .restore: {out}"
    assert list(elsewhere.iterdir()) == [], f"nothing is created through the link: {listing(elsewhere)}"
    print_success(".restore a link → 1, named, nothing written through it")


def upgrade_report(**changes) -> StagingReport:
    """The report of an older backup's check, as staging writes it: two migrations, a table whose rows the upgrade
    changed, one it left alone and one it created empty, a fix, both warnings of a broken reference added."""
    staged_at = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    report = StagingReport(
        stage_id=VALID_ID,
        staged_at=staged_at,
        expires_at=staged_at + timedelta(hours=24),
        backup=StagedBackup(created_at=datetime(2026, 10, 15, 10, 15, tzinfo=UTC), app_version="v1.2.0", origin="ui", alembic_revision="004_older"),
        app_version=APP_VERSION,
        head_revision="006_head",
        action="upgrade",
        migrations=[AppliedMigration(revision="005_tokens", message="Accounts: tokens"), AppliedMigration(revision="006_head", message="Accounts: registration mode")],
        post_migration_fixes=["event_types"],
        tables={"users": TableRows(before=3, after=4), "brokers": TableRows(before=2, after=2), "account_tokens": TableRows(before=None, after=0)},
        foreign_key_violations_before=0,
        foreign_key_violations_after=1,
        files=3,
        files_size=2048,
        database_size=1024 * 1024,
        instance_key_included=False,
        administrators=["ada_admin"],
        warnings=["rows_changed", "foreign_key_violations_added"],
        blockers=[],
        # Lot B-13 (§7.6: the three have defaults, absent, [] and 0): a report of an upgrade whose totals are the same.
        control_totals="same",
        control_totals_differences=[],
        control_totals_differences_count=0,
    )
    return report.model_copy(update=changes)


def test_the_report_of_an_upgrade_lists_its_migrations_changes_and_warnings(capsys):
    """(k) ``_print_stage_report`` of an older backup: the revision upgraded, each migration, the tables whose rows the
    upgrade changed (not the one it created empty: no row changed there), the fixes, and the warnings."""
    report = upgrade_report()
    backup_cli._print_stage_report(report)
    out = capsys.readouterr().out
    lines = [
        "📦 Made by LibreFolio v1.2.0 (ui) on 2026-10-15 10:15:00 UTC",
        "   Database: revision 004_older, upgraded on the copy to 006_head (2 migrations):",
        "     - 005_tokens: Accounts: tokens",
        "     - 006_head: Accounts: registration mode",
        "   Post-migration fixes applied to the copy: event_types",
        "   Rows: 6 in 3 tables, 1.0 MB",
        "   Changed by the upgrade: users (3 → 4)",
        "   Files: 3, 2.0 KB",
        "   Administrators: ada_admin",
        "⚠️  The upgrade changed the rows of some tables (listed above)",
        "⚠️  The upgrade added broken references to the copy",
    ]
    assert [line for line in lines if line not in out.splitlines()] == [], f"every line of an upgrade's report: {out}"
    backup_cli._print_stage_report(report.model_copy(update={"migrations": report.migrations[1:]}))
    assert "(1 migration):" in capsys.readouterr().out, "one migration, singular"
    print_success("upgrade report: migrations, changes, fixes, warnings")


#: Tables of a report, and what «Changed by the upgrade» lists for them (``None``: no such line). A table absent on one
#: side counts as empty: created or dropped empty, it changed no row.
CHANGED_TABLES = [
    pytest.param({"users": (3, 3), "plugin_settings": (None, 0), "old_cache": (0, None)}, None, id="only-tables-created-or-dropped-empty"),
    pytest.param({"users": (3, 3), "plugin_settings": (None, 2)}, "plugin_settings (— → 2)", id="a-table-created-with-rows"),
    pytest.param({"users": (3, 3), "old_cache": (5, None)}, "old_cache (5 → —)", id="a-table-dropped-with-rows"),
]


@pytest.mark.parametrize(("tables", "listed"), CHANGED_TABLES)
def test_the_tables_an_upgrade_changed_are_those_whose_rows_differ(capsys, tables, listed):
    """(k) «Changed by the upgrade» follows staging's ``rows_changed``: only the tables whose count differs, an absent
    table counting as empty; with none, no such line at all."""
    rows = {name: TableRows(before=before, after=after) for name, (before, after) in tables.items()}
    backup_cli._print_stage_report(upgrade_report(tables=rows, warnings=["rows_changed"] if listed else []))
    changed = [line for line in capsys.readouterr().out.splitlines() if "Changed by the upgrade" in line]
    assert changed == ([f"   Changed by the upgrade: {listed}"] if listed else []), f"{tables}: {changed}"
    print_success(f"{list(tables)}: {changed or 'no line'}")


#: What an archive may hold that a terminal would obey (an escape sequence, a window title, a bell, a C1 control, a
#: carriage return, a backspace), and how the report must show it: each control character as ``?``.
HOSTILE_REPORT = {
    "app_version": ("1.2\x1b[2J\x07", "1.2?[2J?"),
    "alembic_revision": ("004\x1b]0;owned\x07", "004?]0;owned?"),
    "administrator": ("ada\x1b[31m\x9b0m\r", "ada?[31m?0m?"),
    "table": ("users\x1b[1m\x08", "users?[1m?"),
}


@pytest.mark.parametrize("action", ["same", "upgrade"])
def test_the_report_prints_no_control_character_from_the_archive(capsys, action):
    """(k) Contract §10: the backup's version and revision, its administrators' names and its tables' names come from
    the archive, and reach the terminal only through ``_safe``: each character that is not printable becomes ``?``.
    Both revision lines (restored as it is, upgraded) are printed through it."""
    raw = {key: value for key, (value, _shown) in HOSTILE_REPORT.items()}
    backup = StagedBackup(created_at=datetime(2026, 10, 15, 10, 15, tzinfo=UTC), app_version=raw["app_version"], origin="ui", alembic_revision=raw["alembic_revision"])
    tables = {raw["table"]: TableRows(before=3, after=4), "brokers": TableRows(before=2, after=2)}
    backup_cli._print_stage_report(upgrade_report(action=action, backup=backup, administrators=[raw["administrator"], "zoe_admin"], tables=tables))
    out = capsys.readouterr().out
    # Split on line feeds only: a carriage return left in the output must be seen, not taken for a line break.
    unprintable = sorted({repr(char) for line in out.split("\n") for char in line if not char.isprintable()})
    assert unprintable == [], f"{action}: no control character reaches the terminal: {unprintable} in {out!r}"
    missing = [shown for _raw, shown in HOSTILE_REPORT.values() if shown not in out]
    assert missing == [], f"{action}: each control character shown as ?: {missing} not in {out!r}"
    assert "zoe_admin" in out and "brokers" not in out, f"{action}: the other values as they are: {out!r}"
    print_success(f"{action}: control characters shown as ?")


def ledger_report(status: str, differences=(), count: int | None = None, **changes) -> StagingReport:
    """``upgrade_report`` with the ledger's totals of lot B-13: ``status``, ``differences`` (as JSON) and their count
    (``len(differences)`` unless given). Validated as staging reads a report back, so each difference is the model the
    report declares; a report without the fields (before lot B-13) ignores them, and prints none of their lines."""
    data = upgrade_report(**changes).model_dump(mode="json")
    data.update(control_totals=status, control_totals_differences=list(differences), control_totals_differences_count=len(differences) if count is None else count)
    return StagingReport.model_validate(data)


def cash_line(broker_id: int, currency: str, before: str | None, after: str | None) -> dict:
    return {"kind": "cash", "broker_id": broker_id, "currency": currency, "asset_id": None, "before": before, "after": after}


def quantity_line(broker_id: int, asset_id: int, before: str | None, after: str | None) -> dict:
    return {"kind": "quantity", "broker_id": broker_id, "currency": None, "asset_id": asset_id, "before": before, "after": after}


def after_files(out: str, size: int) -> list[str]:
    """The ``size`` lines right after «Files: …», where the report says what became of the ledger's totals."""
    lines = out.splitlines()
    files = [index for index, line in enumerate(lines) if line.startswith("   Files: ")]
    assert len(files) == 1, f"precondition: one «Files» line: {out}"
    return lines[files[0] + 1 : files[0] + 1 + size]


#: (status, differences, the lines right after «Files», the warnings of the report): contract §5 as §7.5 words
#: ``changed``, verbatim.
LEDGER_LINES = [
    pytest.param("same", [], [LEDGER_SAME], [], id="same"),
    pytest.param("absent", [], [LEDGER_ABSENT], [], id="absent"),
    pytest.param("other_version", [], [LEDGER_OTHER_VERSION], [], id="other-version"),
    pytest.param("unreadable", [], [LEDGER_UNREADABLE], ["control_totals_unreadable"], id="unreadable"),
    pytest.param("changed", [cash_line(1, "EUR", "10", None)], ["⚠️  Ledger totals differ from the backup's (1 line):", "     broker 1, EUR cash: 10 → —"], ["control_totals_changed"], id="changed-one-line"),
    pytest.param(
        "changed",
        [cash_line(1, "EUR", "100", "100.5"), cash_line(12, "USD", None, "-0.000001"), quantity_line(2, 7, None, "3.5"), quantity_line(2, 9, "4", "0.25")],
        [
            "⚠️  Ledger totals differ from the backup's (4 lines):",
            "     broker 1, EUR cash: 100 → 100.5",
            "     broker 12, USD cash: — → -0.000001",
            "     broker 2, asset 7 quantity: — → 3.5",
            "     broker 2, asset 9 quantity: 4 → 0.25",
        ],
        ["control_totals_changed"],
        id="changed-cash-and-positions",
    ),
]


@pytest.mark.parametrize(("status", "differences", "said", "warnings"), LEDGER_LINES)
def test_the_report_says_what_became_of_the_ledger_s_totals_right_after_the_files(capsys, status, differences, said, warnings):
    """(k) Lot B-13: one line per status, right after «Files: …»; ``changed`` lists each difference as the report gives
    it (``—`` for a line absent on that side), and its count; the two warnings at the end, with the others."""
    backup_cli._print_stage_report(ledger_report(status, differences, warnings=warnings))
    out = capsys.readouterr().out
    assert after_files(out, len(said)) == said, f"{status}: the lines right after «Files»: {out}"
    others = [line for line in out.splitlines() if "Ledger totals" in line and line not in said]
    assert others == [], f"{status}: no other line about the ledger's totals: {others}"
    missing = [LEDGER_WARNINGS[code] for code in warnings if LEDGER_WARNINGS[code] not in out.splitlines()]
    assert missing == [], f"{status}: the warning, verbatim: {missing}"
    unexpected = [text for code, text in LEDGER_WARNINGS.items() if code not in warnings and text in out]
    assert unexpected == [], f"{status}: no warning of the totals but its own: {unexpected}"
    print_success(f"{status}: {said[0].strip()}")


@pytest.mark.parametrize(("count", "more"), [(20, None), (21, 1), (25, 5)], ids=["20", "21", "25"])
def test_past_20_differences_the_report_shows_20_and_says_how_many_more(capsys, count, more):
    """(k) A report holds the first 20 differences and counts them all: the header says the count, then the 20 lines,
    then ``… and <n> more`` for the rest; nothing more for exactly 20."""
    differences = [cash_line(1, f"C{index:02d}", str(index + 1), None) for index in range(20)]
    backup_cli._print_stage_report(ledger_report("changed", differences, count=count, warnings=["control_totals_changed"]))
    out = capsys.readouterr().out
    expected = [f"⚠️  Ledger totals differ from the backup's ({count} lines):", *(f"     broker 1, C{index:02d} cash: {index + 1} → —" for index in range(20))]
    if more is not None:
        expected.append(f"     … and {more} more")
    assert after_files(out, len(expected)) == expected, f"{count} differences: the header, 20 lines, then the rest counted: {out}"
    assert ("… and" in out) == (more is not None), f"{count} differences: «… and n more» only past 20: {out}"
    print_success(f"{count}: 20 shown" + (f", … and {more} more" if more else ""))


def test_a_currency_from_the_archive_reaches_the_terminal_through_safe(capsys):
    """(k) Lot B-13: a currency of the totals comes from the archive's manifest (J reads any text as a currency): an
    escape sequence and a bell in it are shown as ``?``."""
    backup_cli._print_stage_report(ledger_report("changed", [cash_line(1, "EU\x1b[2J\x07R", "1", "2")], warnings=["control_totals_changed"]))
    out = capsys.readouterr().out
    unprintable = sorted({repr(char) for line in out.split("\n") for char in line if not char.isprintable()})
    assert unprintable == [], f"no control character reaches the terminal: {unprintable} in {out!r}"
    assert "     broker 1, EU?[2J?R cash: 1 → 2" in out.splitlines(), f"each control character shown as ?: {out!r}"
    print_success("EU\\x1b[2J\\x07R → EU?[2J?R")


def test_the_script_checks_an_archive_for_a_restore(tmp_path, head_database):
    """(k) ``python scripts/backup_cli.py restore ARCHIVE --dry-run``, as ``dev.py backup`` runs it."""
    data = make_data_dir(tmp_path / "instance").resolve()
    archive = restorable(tmp_path, head_database)
    done = script("restore", str(archive), "--dry-run", env=child_env(data), cwd=tmp_path)
    assert done.returncode == 0, f"restore --dry-run must exit 0, it exited {done.returncode}\n--- stdout\n{done.stdout[-TAIL:]}\n--- stderr\n{done.stderr[-TAIL:]}"
    assert RESTORABLE_LINE in done.stdout and "Administrators: ada_admin, zoe_admin" in done.stdout, f"the report and its verdict: {done.stdout[-TAIL:]}"
    assert stages_left(data) == [], f"the copy is removed: {stages_left(data)}"
    print_success("script restore --dry-run → 0")


def test_the_help_of_restore_says_what_a_dry_run_does(monkeypatch, capsys):
    restore_help = help_of(monkeypatch, capsys, "backup", "restore")
    assert "--dry-run Unpack the archive into a copy, upgrade and check it, report, then remove the copy; the instance is left as it is" in restore_help, f"--dry-run says what it does: {restore_help}"
    group = help_of(monkeypatch, capsys, "backup")
    assert "What a restore would do: unpacked, upgraded and checked on a copy, then removed" in group, f"backup --help shows the dry run: {group}"
    print_success("restore --help and backup --help")
