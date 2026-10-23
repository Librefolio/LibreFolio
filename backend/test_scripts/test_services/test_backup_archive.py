"""
Instance backup, the archive (workstream B, lot B1): layout, database copy, manifest, build and check.

Under test, in ``backend/app/services/platform/instance_backup/``:

(a) ``paths``: an archive carries ``sqlite/app.db`` and the folders ``custom-uploads``, ``broker_reports`` and
    ``scenario_catalog``, described by ``manifest.json``; backups are written in ``backups/``, the jobs in
    ``backups/.jobs/<32 lowercase hex>/`` under the lock ``backups/.jobs/.lock``. ``ensure_private_dir`` creates the
    missing folders 0700 and refuses a link or a file where a folder belongs, without writing through it; the
    ``BackupPathError`` names that very folder (``.path``: ``backups``, ``backups/.jobs`` or the job's own folder),
    its message "<path> is not a plain folder". ``job_dir`` never builds a path from something that is not a job id.
    Lot B-53, ``read_regular_file(path, *, limit=None)``, the one reader of the files the backup keeps (a check's
    state, a report, the restore's state, the outcome's ticket): a regular file's bytes, all of them or its first
    ``limit`` at most, an empty one ``b""``, no descriptor left open. Never a link, whatever it points to (a regular
    file, a folder, nothing): ``NotRegularFileError`` keeping ``ELOOP``; never a wait on a FIFO: ``NotRegularFileError``
    at once, a device alike; a folder ``IsADirectoryError`` (``EISDIR``), its descriptor closed however often it is
    read; nothing there ``FileNotFoundError``, a file on the way ``NotADirectoryError``, mode 000 ``PermissionError``,
    as the system raises them; any other error of ``os.open`` or ``os.fstat`` (``EIO``) the very error raised, the
    descriptor closed. ``NotRegularFileError``: an ``OSError`` of its own kind, neither ``PermissionError``,
    ``IsADirectoryError`` nor ``FileNotFoundError``, keeping the ``errno``, ``strerror`` and ``filename`` it is given.
(b) ``snapshot``: ``snapshot_database`` copies the live database with ``VACUUM INTO``. The copy is the database as of
    one instant even while another connection keeps committing in WAL mode, that writer is never blocked, and the copy
    is a standalone rollback-journal file with nothing beside it. ``describe_database`` reads a file without changing
    it: integrity, foreign-key violations, rows per table, the Alembic revision only when exactly one is recorded.
(c) ``manifest``: ``BackupManifest`` (format ``librefolio-backup``, version 1, unknown fields ignored, ``created_at``
    with its time zone and kept in UTC, the database first, no path twice, every path checked by ``check_entry_path``)
    and ``from_bytes``, whose ``ManifestError.code`` says why a manifest is refused, the format and its version checked
    before the fields.
(d) ``collect_files`` / ``build_archive``: regular files only; links (to files, to folders, in place of an archived
    folder), special files and names that are not UTF-8 are reported as left out and never followed or opened. The
    logs, the secrets, the scheduler state, the backups and the files SQLite keeps beside the database (``-wal``,
    ``-shm``, the post-migration lock and copies) never enter an archive, while the rows still in the ``-wal`` do. The
    database is the first entry, the manifest the last; every size and SHA-256 matches; the archive is created 0600 as
    ``<name>.part`` and renamed, so a failed build never leaves a file under the final name; the space is checked
    before anything is written.
(e) ``check_archive``: an intact archive is ok; missing, mismatched (other bytes, more or fewer of them) and
    unexpected entries are reported, a name written twice among the unexpected ones; a file that is not a zip is
    ``ArchiveError('archive_unreadable')``, a zip without manifest ``ManifestError('manifest_missing')``; an entry is
    never read beyond the size its manifest declares, plus one byte.
(f) ``_add_file`` / ``build_archive``, a file that fails: before its entry starts (gone, a link, a folder or a FIFO in
    its place, unreadable) it is an ``OSError``, the archive gets no entry, and the build leaves the file out
    (``files_skipped``) and goes on, never blocked by a FIFO. Such a refusal closes the descriptor it opened: a folder
    in place of a file used to leak one per call (``os.fdopen`` refuses a folder without closing the descriptor it is
    given), for as long as the server runs. Once its entry has started, a failure reading the file, opening the
    entry, writing it or closing it is ``PartialEntryError(entry)``, the ``OSError`` as its ``__cause__``: a zip entry
    cannot be taken back, so the build stops instead of leaving the file out, and no archive reaches the target (the
    ``.part`` is the caller's to remove).
(g) The ledger's control totals (lot B-13): ``build_archive`` reads them once with ``ledger_totals_of``, on the snapshot
    (the very bytes the archive carries, never the live database), in the phase ``database``, before the zip is opened,
    and writes J's JSON as it is into ``manifest.database.control_totals``: equal to ``ledger_totals_of`` of the
    archived database, and to J's ``control_totals`` of its rows. Totals that cannot be read (``None``; a database
    without the ledger's table, for real) leave the field ``null``: the backup is done, without a new warning. The
    format stays version 1: a manifest without the field reads as ``None``; the field (``Any``, contract §7.2) holds any
    JSON value as it is, never refused nor read into amounts at reading (a document of another version or shape, a
    list, a string, a number, an amount that is not plain text: the archive stays readable).

Pure: every data directory, database and archive lives in ``tmp_path``; ``LF_APP_VERSION`` is set so the manifest's
``app_version`` is exact and no git process runs. No lane database, no server, no network. The concurrent writer of (b)
is a thread with its own SQLite connection, synchronised with the copy through the copy's progress handler: no clock
wait decides anything, and every wait has a deadline. File modes, links and FIFOs are POSIX-only; the permission case is
skipped as root, which bypasses it. A file that fails half-way is simulated in this process only: the ``os`` of
``archive`` is replaced, for one test, by a stand-in whose one file reads its first block, then fails (``EIO``); the
stages of a zip entry fail through a stand-in for the archive given to ``_add_file``. The descriptors left open are
found in ``/dev/fd``, the list of this process's own, by the device and inode of the test's folder or FIFO.
``ledger_totals_of`` is replaced, for the tests of (g) that say so, wherever ``archive`` may read it (the totals
module's own, and the name ``archive`` imported); ``instance_backup.totals`` is imported by the tests that need it,
never at collection: until lot B-13 writes it, each of them fails on its own.
Lot B-53's ``paths.read_regular_file`` and ``paths.NotRegularFileError`` are looked up the same way, by the test that
needs them (``new_in_paths``): written red, each of those tests fails on its own ("[new] …") until the lot adds them.
Their transient errors are the global ``os.open`` failing for that one path (``opening_fails``) and the global
``os.fstat`` failing for the descriptor opened on it, every other call the real one; a FIFO is read in a thread waited
for ``DEADLINE_S`` (``answered_within``), a read still waiting then released by a writer that appears and leaves, so
that a red run never hangs the suite. ``/dev/null`` is the device, only read. ``answered_within``, ``opening_fails``,
``descriptors_on`` and ``close_all`` serve the B-53 tests of ``test_backup_staging.py``, ``test_backup_outcome.py`` and
``test_backup_apply.py`` too.
"""

from __future__ import annotations

import errno
import hashlib
import importlib
import json
import os
import shutil
import sqlite3
import stat
import struct
import threading
import uuid
import warnings
import zipfile
from collections.abc import Callable
from contextlib import closing, suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from structlog.testing import capture_logs

from backend.app.services.financial_math.ledger_totals import control_totals
from backend.app.services.platform.instance_backup import archive, paths, snapshot
from backend.app.services.platform.instance_backup.archive import ArchiveError, BackupNoSpaceError, BuiltArchive, PartialEntryError, build_archive, check_archive, collect_files, required_space
from backend.app.services.platform.instance_backup.manifest import FORMAT, FORMAT_VERSION, MANIFEST_MAX_BYTES, BackupManifest, ManifestDatabase, ManifestError, ManifestFile, check_entry_path
from backend.app.services.platform.instance_backup.paths import (
    ARCHIVED_FOLDERS,
    DATABASE_ENTRY,
    MANIFEST_ENTRY,
    BackupPathError,
    backups_dir,
    database_path,
    ensure_private_dir,
    is_job_id,
    job_dir,
    jobs_dir,
    lock_path,
)
from backend.app.services.platform.instance_backup.snapshot import DatabaseDescription, SnapshotError, describe_database, file_digest, snapshot_database
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_utils import print_section, print_success

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")
needs_symlinks = pytest.mark.skipif(not POSIX, reason="symbolic links need a privilege on Windows")
needs_fifo = pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="this platform has no FIFOs")
needs_permission_checks = pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs POSIX permissions, which root bypasses")
needs_dev_fd = pytest.mark.skipif(not Path("/dev/fd").is_dir(), reason="needs /dev/fd to list this process's open descriptors")

#: What the manifest must say made the archive: set as LF_APP_VERSION, so no ``git describe`` runs.
APP_VERSION = "v0.0.0-b1-archive-test"
REVISION = "b1a2c3d4e5f6"
#: The content of the instance key in the synthetic data directories: no archive may hold these bytes.
SECRET = b"instance-key-never-in-an-archive-6b1f0c"
#: Seconds. Every wait of this module ends by then; none of them decides anything by itself.
DEADLINE_S = 30
#: The writer's SQLite busy timeout: a writer the copy blocked fails within it, instead of hiding behind the copy.
WRITER_BUSY_S = 5
#: Rows per table before the copy starts: enough for the copy to run thousands of virtual machine steps.
SEED_ROWS = 4000
#: Transactions the writer commits while the copy holds its snapshot.
WRITES_DURING_COPY = 25
#: Virtual machine steps between two calls of the copy's progress handler.
PROGRESS_STEPS = 1000
#: The newest date a zip entry can carry.
ZIP_LAST_DATE = (2107, 12, 31, 23, 59, 59)

#: Every regular file of the synthetic data directory an archive must carry, besides the database.
ARCHIVED_FILES = {
    "custom-uploads/logo.png": bytes(range(256)) * 8,
    "custom-uploads/.hidden-note": b"hidden files are files too\n",
    "custom-uploads/avatars/user-1.webp": b"RIFF\x24\x00\x00\x00WEBPVP8 " + bytes(64),
    "broker_reports/uploaded/2026-10.csv": b"date,amount\n2026-10-01,10.00\n",
    "broker_reports/parsed/2026-09.csv": b"date,amount\n2026-09-01,20.00\n",
    "broker_reports/failed/broken.csv": b"\xff\xfe a report that is not UTF-8 is still a file\n",
    "scenario_catalog/user-scenarios.json": b'{"scenarios": []}\n',
}
#: Files of the data directory no archive may carry (the database's side files are added by the live fixture).
NEVER_ARCHIVED = {
    "logs/librefolio.log": b'{"event": "a log line"}\n',
    "secrets/instance.key": SECRET + b"\n",
    "scheduler_state.json": b'{"last_run": null}\n',
    "backups/librefolio-backup-20261014-090000.zip": b"PK an older backup",
    f"backups/.jobs/{'e' * 32}/state.json": b'{"status": "done"}\n',
    "README.txt": b"a stray file at the root of the data directory\n",
    "sqlite/app.db.post-migration.lock": b"",
}
#: The post-migration copy of the database, as backend/app/db/post_migration names it.
POST_MIGRATION_COPY = "sqlite/app.db.pre-001_fix_dates-20261015T101500.bak"
#: Links inside the archived folders, to the instance key and to the secrets folder: entry -> link target.
LINKS = {
    "custom-uploads/link-to-key": "../secrets/instance.key",
    "custom-uploads/avatars/link-to-secrets": "../../secrets",
}


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture(autouse=True)
def app_version(monkeypatch):
    """The version every manifest of this module must carry, without a git process.

    ``get_git_version`` keeps the first version it computes for the life of the process: its cache is emptied before
    the test, so this version is the one read, and after it, so this version never reaches the tests that follow.
    """
    monkeypatch.setenv("LF_APP_VERSION", APP_VERSION)
    get_git_version.cache_clear()
    yield
    get_git_version.cache_clear()


def mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_files(root: Path, files: dict[str, bytes]) -> None:
    for entry, content in files.items():
        path = root / entry
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def make_database(path: Path, *, revisions: tuple[str, ...] = (REVISION,)) -> dict[str, int]:
    """A small database shaped like LibreFolio's, in rollback-journal mode. Returns its rows per table.

    ``sqlite_sequence`` (AUTOINCREMENT) and ``sqlite_stat1`` (ANALYZE) exist too: they are SQLite's, not tables a
    description counts.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE brokers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id), name TEXT NOT NULL);
            CREATE INDEX ix_brokers_user ON brokers (user_id);
            CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);
            """)
        with conn:
            conn.executemany("INSERT INTO users (id, name) VALUES (?, ?)", [(1, "ada"), (2, "grace"), (3, "linus")])
            conn.executemany("INSERT INTO brokers (user_id, name) VALUES (?, ?)", [(1, "Broker A"), (2, "Broker B")])
            conn.executemany("INSERT INTO alembic_version (version_num) VALUES (?)", [(revision,) for revision in revisions])
        conn.execute("ANALYZE")
    return {"alembic_version": len(revisions), "brokers": 2, "users": 3}


def count_rows(database: Path, table: str) -> int:
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        return conn.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]


def side_files(database: Path) -> list[str]:
    """The files SQLite may keep beside a database, that exist beside this one."""
    return [suffix for suffix in ("-wal", "-shm", "-journal") if database.with_name(database.name + suffix).exists()]


@dataclass
class LiveDataDir:
    """A data directory as a running server leaves it: the database open in WAL mode, rows still in its ``-wal``."""

    root: Path
    tables: dict[str, int]
    connection: sqlite3.Connection


def build_live_data_dir(root: Path) -> LiveDataDir:
    database = root / DATABASE_ENTRY
    tables = make_database(database)
    connection = sqlite3.connect(database, isolation_level=None)
    assert connection.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal", "precondition: the live database runs in WAL mode"
    connection.execute("PRAGMA wal_autocheckpoint=0")
    connection.execute("INSERT INTO users (id, name) VALUES (4, 'committed, still in the wal'), (5, 'idem')")
    tables["users"] += 2
    write_files(root, ARCHIVED_FILES)
    write_files(root, NEVER_ARCHIVED)
    (root / POST_MIGRATION_COPY).write_bytes(database.read_bytes())
    for entry, target in LINKS.items():
        (root / entry).symlink_to(target)
    return LiveDataDir(root=root, tables=tables, connection=connection)


@pytest.fixture
def live_data(tmp_path):
    live = build_live_data_dir(tmp_path / "data")
    yield live
    live.connection.close()


def small_data_dir(root: Path) -> Path:
    """A data directory with a database and one file in each archived folder, nothing else."""
    make_database(root / DATABASE_ENTRY)
    write_files(
        root,
        {
            "custom-uploads/a.txt": b"uploaded file\n" * 64,
            "broker_reports/uploaded/r.csv": b"date,amount\n2026-10-01,10.00\n",
            "scenario_catalog/s.json": b'{"scenarios": [1, 2, 3]}\n',
        },
    )
    return root


def build_into(data: Path, work: Path, *, name: str = "librefolio-backup-test.zip", **kwargs) -> BuiltArchive:
    work.mkdir(parents=True, exist_ok=True)
    return build_archive(data, work, work / name, origin=kwargs.pop("origin", "cli"), **kwargs)


def small_archive(tmp_path: Path) -> BuiltArchive:
    return build_into(small_data_dir(tmp_path / "data"), tmp_path / "work")


def entry_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def rewrite(source: Path, target: Path, *, drop: tuple[str, ...] = (), swap: dict[str, bytes] | None = None, add: dict[str, bytes] | None = None, twice: tuple[str, ...] = ()) -> Path:
    """A copy of the archive ``source``: entries left out, given other bytes, added, or written twice; the rest as is."""
    swap = swap or {}
    with zipfile.ZipFile(source) as old, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as new, warnings.catch_warnings():
        # zipfile warns about the names written twice, on purpose here.
        warnings.simplefilter("ignore", UserWarning)
        for info in old.infolist():
            if info.filename in drop:
                continue
            data = swap.get(info.filename, old.read(info))
            for _ in range(2 if info.filename in twice else 1):
                new.writestr(info, data)
        for name, data in (add or {}).items():
            new.writestr(name, data)
    return target


def corrupt(source: Path, target: Path, entry: str) -> Path:
    """A copy of the archive ``source`` with one byte inverted in the middle of the stored data of ``entry``.

    The zip structure stays intact, as after bit rot on a disk or a damaged copy: only the data of that entry changes.
    """
    raw = bytearray(source.read_bytes())
    with zipfile.ZipFile(source) as zf:
        info = zf.getinfo(entry)
    signature, *_, name_length, extra_length = struct.unpack("<4s2B4HL2L2H", raw[info.header_offset : info.header_offset + 30])
    assert signature == b"PK\x03\x04", "precondition: the local header of the entry is where the central directory says"
    raw[info.header_offset + 30 + name_length + extra_length + info.compress_size // 2] ^= 0xFF
    target.write_bytes(bytes(raw))
    return target


def record_reads(monkeypatch) -> list[tuple[str, int]]:
    """Every read of a zip entry from now on, as (entry, bytes returned)."""
    reads: list[tuple[str, int]] = []
    real_read = zipfile.ZipExtFile.read

    def read(self, n=-1):
        data = real_read(self, n)
        reads.append((self.name, len(data)))
        return data

    monkeypatch.setattr(zipfile.ZipExtFile, "read", read)
    return reads


# =============================================================================
# (a) paths
# =============================================================================


def test_the_layout_is_pinned():
    """(a) What an archive carries and where backups go: a change here changes every archive written and every restore."""
    print_section("Layout of the data directory")
    assert DATABASE_ENTRY == "sqlite/app.db", f"the database entry moved to {DATABASE_ENTRY!r}: archives written so far could not be restored"
    assert ARCHIVED_FOLDERS == ("custom-uploads", "broker_reports", "scenario_catalog"), f"the archived folders changed: {ARCHIVED_FOLDERS}"
    assert MANIFEST_ENTRY == "manifest.json", f"the manifest entry moved to {MANIFEST_ENTRY!r}"
    data = Path("/srv/librefolio-data")
    assert database_path(data) == data / "sqlite" / "app.db", "the live database is <data dir>/sqlite/app.db"
    assert backups_dir(data) == data / "backups", "backups are written in <data dir>/backups"
    assert jobs_dir(data) == data / "backups" / ".jobs", "the jobs live in <data dir>/backups/.jobs"
    assert lock_path(data) == data / "backups" / ".jobs" / ".lock", "the run lock is <data dir>/backups/.jobs/.lock"
    print_success("sqlite/app.db + custom-uploads, broker_reports, scenario_catalog; backups/, backups/.jobs/.lock")


VALID_ID = "0123456789abcdef0123456789abcdef"
NOT_JOB_IDS = [
    pytest.param("../x", id="parent-folder"),
    pytest.param("a" * 31, id="31-hex"),
    pytest.param("a" * 33, id="33-hex"),
    pytest.param(VALID_ID.upper(), id="uppercase-hex"),
    pytest.param("", id="empty"),
    pytest.param(VALID_ID + "\n", id="trailing-newline"),
    pytest.param("g" + VALID_ID[1:], id="not-hex"),
    pytest.param("../" + VALID_ID[3:], id="parent-folder-32-chars"),
    pytest.param("/" + VALID_ID[1:], id="absolute-32-chars"),
]


def test_a_job_id_is_32_lowercase_hexadecimal_digits():
    """(a) The ids the jobs make (``secrets.token_hex(16)``) are job ids, and their folder is below the jobs folder."""
    print_section("Job ids")
    for value in (VALID_ID, uuid.uuid4().hex, "f" * 32):
        assert is_job_id(value), f"{value!r} is 32 lowercase hexadecimal digits: a job id"
    data = Path("/srv/librefolio-data")
    assert job_dir(data, VALID_ID) == data / "backups" / ".jobs" / VALID_ID, "a job's folder is backups/.jobs/<id>"
    print_success("32 lowercase hex digits → backups/.jobs/<id>")


@pytest.mark.parametrize("value", NOT_JOB_IDS)
def test_anything_else_never_becomes_a_job_folder(value):
    """(a) ``job_dir`` refuses what is not a job id instead of building a path from it."""
    assert not is_job_id(value), f"{value!r} must not pass for a job id"
    with pytest.raises(ValueError, match="not a backup job id"):
        job_dir(Path("/srv/librefolio-data"), value)
    print_success(f"{value!r} refused")


@needs_posix_modes
def test_missing_folders_are_created_readable_by_their_owner_only(tmp_path):
    """(a) Every missing folder from the data directory down is created 0700; an existing one is reused as it is."""
    print_section("ensure_private_dir")
    data = tmp_path / "data"
    data.mkdir()
    folder = ensure_private_dir(job_dir(data, VALID_ID), data)
    assert folder == job_dir(data, VALID_ID), "ensure_private_dir returns the folder it was given"
    for created in (backups_dir(data), jobs_dir(data), folder):
        assert created.is_dir() and not created.is_symlink(), f"{created} must be a plain folder"
        assert mode(created) == 0o700, f"{created} must be readable by its owner only (0700), it is {oct(mode(created))}"
    (folder / "kept.txt").write_bytes(b"kept")
    assert ensure_private_dir(job_dir(data, VALID_ID), data) == folder, "a second call on existing folders succeeds"
    assert (folder / "kept.txt").read_bytes() == b"kept", "an existing folder is reused, never recreated"
    print_success("backups/, .jobs/ and the job folder created 0700; existing folders reused")


@needs_symlinks
@pytest.mark.parametrize("case", ["backups-is-a-link-to-a-folder", "backups-is-a-dangling-link", "backups-is-a-file", "jobs-is-a-link-to-a-folder"])
def test_a_link_or_a_file_where_a_folder_belongs_is_refused_and_never_written_through(tmp_path, case):
    """(a) A backup holds the whole database: a link where a folder belongs could send it anywhere, so it is refused."""
    data = tmp_path / "data"
    data.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    if case == "backups-is-a-link-to-a-folder":
        backups_dir(data).symlink_to(elsewhere, target_is_directory=True)
    elif case == "backups-is-a-dangling-link":
        backups_dir(data).symlink_to(tmp_path / "nowhere", target_is_directory=True)
    elif case == "backups-is-a-file":
        backups_dir(data).write_bytes(b"not a folder")
    else:
        backups_dir(data).mkdir()
        jobs_dir(data).symlink_to(elsewhere, target_is_directory=True)
    with pytest.raises(BackupPathError, match="not a plain folder"):
        ensure_private_dir(job_dir(data, VALID_ID), data)
    assert list(elsewhere.iterdir()) == [], f"nothing may be created through the link: {sorted(p.name for p in elsewhere.iterdir())}"
    assert not (tmp_path / "nowhere").exists(), "a dangling link must not be made to point to a new folder"
    print_success(f"{case}: refused, nothing written through it")


@needs_symlinks
@pytest.mark.parametrize("case", ["backups-is-a-link", "backups-is-a-file", "jobs-is-a-link", "job-folder-is-a-file"])
def test_the_refusal_names_the_folder_that_is_not_a_plain_folder(tmp_path, case):
    """(a) ``BackupPathError.path`` is the folder that is a link or a file, not the one asked for: the CLI names it."""
    data = tmp_path / "data"
    data.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    if case == "backups-is-a-link":
        backups_dir(data).symlink_to(elsewhere, target_is_directory=True)
        culprit = backups_dir(data)
    elif case == "backups-is-a-file":
        backups_dir(data).write_bytes(b"not a folder")
        culprit = backups_dir(data)
    elif case == "jobs-is-a-link":
        backups_dir(data).mkdir()
        jobs_dir(data).symlink_to(elsewhere, target_is_directory=True)
        culprit = jobs_dir(data)
    else:
        jobs_dir(data).mkdir(parents=True)
        job_dir(data, VALID_ID).write_bytes(b"not a folder")
        culprit = job_dir(data, VALID_ID)
    with pytest.raises(BackupPathError) as raised:
        ensure_private_dir(job_dir(data, VALID_ID), data)
    assert raised.value.path == culprit, f"{case}: the error names {culprit}, not {raised.value.path}"
    assert str(raised.value) == f"{culprit} is not a plain folder", f"{case}: the message keeps its format: {raised.value}"
    assert list(elsewhere.iterdir()) == [], f"{case}: nothing is created through a link"
    print_success(f"{case}: .path = {culprit.relative_to(data)}")


# -----------------------------------------------------------------------------
# (a) paths, lot B-53: read_regular_file, the one reader of the files the backup keeps
# -----------------------------------------------------------------------------
#
# ``os.fdopen`` refuses a folder without closing the descriptor it is handed: a reader that opened a file the backup
# keeps with ``os.open`` and wrapped it with ``os.fdopen`` left one descriptor open per read of a folder in its place
# (measured: twenty reads, twenty descriptors, in ``outcome._read_record`` and ``staging.read_report``). And ``os.open``
# without ``O_NONBLOCK`` waits on a FIFO for a writer that never comes. Lot B-53 gives ``paths`` one reader for them,
# ``read_regular_file``, and its ``NotRegularFileError``: both looked up by the test that needs them (``new_in_paths``),
# so that until the lot adds them each of these tests fails on its own and the file still collects.

#: A regular file's content, larger than one read of 64 KiB: a reader that reads once returns a part of it.
REGULAR_CONTENT = bytes(range(256)) * 800
#: A device every POSIX system has: no regular file either.
DEVICE = Path(os.devnull)
needs_a_device = pytest.mark.skipif(not POSIX or not DEVICE.is_char_device(), reason="needs /dev/null, a character device")


def new_in_paths(name: str) -> Any:
    """A name lot B-53 adds to ``paths`` (``read_regular_file``, ``NotRegularFileError``), looked up by the test that needs
    it, never imported at the top: the file collects without it, and each test fails on its own ("[new] …")."""
    value = getattr(paths, name, None)
    assert value is not None, f"[new] paths.{name} does not exist yet: lot B-53 adds it"
    return value


def opening_fails(patch: pytest.MonkeyPatch, path: Path, code: int) -> OSError:
    """The global ``os.open`` failing with ``code`` for ``path`` alone, as a dying disk fails (``EIO``), every other path
    opened as it is: the error it raises, one instance, so that a test tells whether it reached the caller as it is.
    Every reader looks ``os.open`` up when it opens. Shared with the B-53 tests of ``test_backup_staging.py`` and
    ``test_backup_apply.py``."""
    error = OSError(code, os.strerror(code), str(path))
    target = os.path.realpath(path)
    real_open = os.open

    def failing_open(file: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if kwargs.get("dir_fd") is None and os.path.realpath(os.fsdecode(file)) == target:
            raise error
        return real_open(file, flags, *args, **kwargs)

    patch.setattr(os, "open", failing_open)
    return error


@dataclass
class Answer:
    """What a call answered within ``answered_within``: what it returned or raised; ``blocked`` when it was still waiting
    at the deadline, ``deadline`` seconds (released then, so that it ended)."""

    blocked: bool = False
    returned: Any = None
    raised: BaseException | None = None
    deadline: float = DEADLINE_S


def answered_within(call: Callable[[], Any], fifo: Path) -> Answer:
    """``call()`` in a thread of its own, waited for ``DEADLINE_S``: a read that opens a FIFO without ``O_NONBLOCK`` waits
    there for a writer that never comes. Still waiting then, it is ``blocked``, and a writer appears on ``fifo`` and
    leaves (opened with ``O_NONBLOCK``: this never waits itself), so that the blocked open returns and a red run never
    hangs the suite. A read that does not wait answers at once: the deadline only ends a red run. Shared with the B-53
    tests of ``test_backup_staging.py`` and ``test_backup_outcome.py``."""
    answer = Answer()

    def run() -> None:
        try:
            answer.returned = call()
        except BaseException as exc:  # reported by the test, in its own thread
            answer.raised = exc

    worker = threading.Thread(target=run, name="b53-read", daemon=True)
    worker.start()
    try:
        worker.join(answer.deadline)
    finally:
        if worker.is_alive():
            answer.blocked = True
            with suppress(OSError):
                os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))  # a writer appears and leaves: the blocked open returns
            worker.join(answer.deadline)
    return answer


def close_all(descriptors: list[int]) -> list[int]:
    """Close ``descriptors``, left open by a red run that must not carry them into the tests that follow; returns them."""
    for fd in descriptors:
        os.close(fd)
    return descriptors


#: (content, limit, what is read): every byte, or at most ``limit`` of them.
READS = [
    pytest.param(REGULAR_CONTENT, None, REGULAR_CONTENT, id="whole-more-than-one-read-of-64-KiB"),
    pytest.param(REGULAR_CONTENT, 70_000, REGULAR_CONTENT[:70_000], id="a-limit-past-one-read-of-64-KiB"),
    pytest.param(REGULAR_CONTENT, 4097, REGULAR_CONTENT[:4097], id="the-outcome-ticket-s-limit"),
    pytest.param(REGULAR_CONTENT, len(REGULAR_CONTENT), REGULAR_CONTENT, id="a-limit-of-its-size"),
    pytest.param(REGULAR_CONTENT, len(REGULAR_CONTENT) + 1, REGULAR_CONTENT, id="a-limit-past-its-size"),
    pytest.param(b"", None, b"", id="empty"),
    pytest.param(b"", 4097, b"", id="empty-with-a-limit"),
]


@needs_dev_fd
@pytest.mark.parametrize(("content", "limit", "expected"), READS)
def test_read_regular_file_gives_a_regular_file_whole_or_its_first_limit_bytes_and_closes_it(tmp_path, content, limit, expected):
    """(a) B-53 A regular file: every byte of it, more than one read's worth, or its first ``limit`` bytes at most —
    ``outcome`` reads the ticket's file with ``limit=4097``, one byte past what it accepts — and an empty file ``b""``.
    No descriptor is left open on it. Red until lot B-53 adds the reader."""
    print_section("(a) B-53: read_regular_file")
    read = new_in_paths("read_regular_file")
    path = tmp_path / "state.json"
    path.write_bytes(content)
    got = read(path) if limit is None else read(path, limit=limit)
    left_open = close_all(descriptors_on(path))
    seen = f"{len(got)} bytes" if isinstance(got, bytes) else repr(got)[:80]
    assert got == expected, f"limit={limit}: the file's first {len(expected)} bytes, not {seen}"
    assert left_open == [], f"limit={limit}: {len(left_open)} descriptor(s) left open on the file: {left_open}"
    print_success(f"limit={limit}: {seen}, no descriptor left open")


@pytest.mark.parametrize("case", ["nothing-there", "a-file-on-the-way"])
def test_read_regular_file_says_nothing_there_and_a_file_on_the_way_as_the_system_does(tmp_path, case):
    """(a) B-53 Nothing at the path: ``FileNotFoundError``; a file where a folder of the path belongs:
    ``NotADirectoryError``. As the system raises them: a reader tells «none» from the rest by them. Red until lot B-53
    adds the reader."""
    read = new_in_paths("read_regular_file")
    if case == "nothing-there":
        path, expected = tmp_path / "state.json", FileNotFoundError
    else:
        (tmp_path / "job").write_bytes(b"a file where a folder belongs")
        path, expected = tmp_path / "job" / "state.json", NotADirectoryError
    with pytest.raises(OSError) as raised:
        read(path)
    assert type(raised.value) is expected, f"{case}: {expected.__name__}, not {type(raised.value).__name__}: {raised.value}"
    print_success(f"{case}: {expected.__name__}")


@needs_dev_fd
def test_read_regular_file_refuses_a_folder_as_is_a_directory_and_closes_its_descriptor(tmp_path):
    """(a) B-53 A folder where a file is read: ``IsADirectoryError`` (``EISDIR``) at every read, and no descriptor left
    open on it however often it is read. Regression: ``os.fdopen`` refuses a folder without closing the descriptor
    ``os.open`` gave, so each read of a folder in place of a check's report or of the outcome's ticket left one open, for
    as long as the server ran. Red until lot B-53 adds the reader."""
    read = new_in_paths("read_regular_file")
    folder = tmp_path / "report.json"
    folder.mkdir()
    assert descriptors_on(folder) == [], "precondition: no descriptor of this process is open on the folder"
    answers: set[str] = set()
    for _ in range(LEAK_CALLS):
        try:
            got = read(folder)
        except OSError as exc:
            answers.add(f"{type(exc).__name__} ({errno.errorcode.get(exc.errno or 0)})")
        else:
            answers.add(f"returned {got!r:.60}")
    left_open = close_all(descriptors_on(folder))
    assert answers == {"IsADirectoryError (EISDIR)"}, f"a folder: IsADirectoryError (EISDIR) at every read: {sorted(answers)}"
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the folder by {LEAK_CALLS} reads: {left_open}"
    print_success(f"folder: IsADirectoryError at each of {LEAK_CALLS} reads, no descriptor left open")


@needs_symlinks
@pytest.mark.parametrize("pointed", ["a-regular-file", "a-folder", "nothing"], ids=["to-a-regular-file", "to-a-folder", "dangling"])
def test_read_regular_file_never_follows_a_link(tmp_path, pointed):
    """(a) B-53 A link where a file is read is refused, never followed: ``NotRegularFileError`` keeping ``ELOOP``,
    whatever it points to — a regular file, whose content it never returns; a folder; nothing: a dangling link is not
    «nothing there» (``FileNotFoundError``), which a reader takes for no file at all and would not report. Red until lot
    B-53 adds the reader."""
    read = new_in_paths("read_regular_file")
    not_regular = new_in_paths("NotRegularFileError")
    target = tmp_path / "elsewhere" / "state.json"
    target.parent.mkdir()
    if pointed == "a-regular-file":
        target.write_bytes(b'{"status": "done", "read": "through a link: never returned"}')
    elif pointed == "a-folder":
        target.mkdir()
    link = tmp_path / "state.json"
    link.symlink_to(target, target_is_directory=pointed == "a-folder")
    with pytest.raises(OSError) as raised:
        read(link)
    found = (type(raised.value).__name__, errno.errorcode.get(raised.value.errno or 0))
    assert isinstance(raised.value, not_regular) and raised.value.errno == errno.ELOOP, f"a link to {pointed}: NotRegularFileError, errno ELOOP, not {found}: {raised.value}"
    print_success(f"a link to {pointed}: NotRegularFileError (ELOOP), never followed")


@needs_dev_fd
@needs_fifo
def test_read_regular_file_refuses_a_fifo_at_once_and_closes_its_descriptor(tmp_path):
    """(a) B-53 A FIFO where a file is read: ``NotRegularFileError`` at once — opened with ``O_NONBLOCK``, never waiting
    for a writer that never comes, which stopped every reader of a check's state, a report or the outcome's ticket for
    good, the startup's sweep among them — and no descriptor left open on it. The read runs in a thread waited for
    ``DEADLINE_S`` (``answered_within``): a read still waiting then is released, and the test fails. Red until lot B-53
    adds the reader."""
    read = new_in_paths("read_regular_file")
    not_regular = new_in_paths("NotRegularFileError")
    fifo = tmp_path / "state.json"
    os.mkfifo(fifo, 0o600)
    assert descriptors_on(fifo) == [], "precondition: no descriptor of this process is open on the FIFO"
    answer = answered_within(lambda: read(fifo), fifo)
    left_open = close_all(descriptors_on(fifo))
    assert not answer.blocked, f"read_regular_file was still waiting after {DEADLINE_S}s: it opened the FIFO without O_NONBLOCK and waited for a writer that never comes"
    assert isinstance(answer.raised, not_regular), f"a FIFO is no regular file: NotRegularFileError, not {answer}"
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the FIFO: {left_open}"
    print_success("FIFO: NotRegularFileError at once, no descriptor left open")


@needs_a_device
def test_read_regular_file_refuses_a_device_as_no_regular_file():
    """(a) B-53 A device (``/dev/null``, only read) is no regular file either: ``NotRegularFileError``, as a FIFO — what
    is refused is anything but a regular file, not a FIFO alone. Red until lot B-53 adds the reader."""
    read = new_in_paths("read_regular_file")
    not_regular = new_in_paths("NotRegularFileError")
    with pytest.raises(OSError) as raised:
        read(DEVICE)
    assert isinstance(raised.value, not_regular), f"{DEVICE}: NotRegularFileError, not {type(raised.value).__name__}: {raised.value}"
    print_success(f"{DEVICE}: NotRegularFileError")


@needs_permission_checks
def test_read_regular_file_says_a_file_it_may_not_read_is_a_permission_error(tmp_path):
    """(a) B-53 A file of mode 000: ``PermissionError`` (``EACCES``), as the system raises it; root reads it all the same
    (skipped). Its mode is put back whatever happens. Red until lot B-53 adds the reader."""
    read = new_in_paths("read_regular_file")
    path = tmp_path / "state.json"
    path.write_bytes(b'{"status": "done"}')
    path.chmod(0o000)
    try:
        with pytest.raises(OSError) as raised:
            read(path)
    finally:
        path.chmod(0o600)
    assert type(raised.value) is PermissionError and raised.value.errno == errno.EACCES, f"mode 000: PermissionError (EACCES), not {type(raised.value).__name__}: {raised.value}"
    print_success("mode 000: PermissionError")


def test_not_regular_file_error_is_an_oserror_of_its_own_kind():
    """(a) B-53 ``NotRegularFileError`` is an ``OSError`` — a reader that takes any ``OSError`` for «cannot be read» keeps
    doing so — of its own kind: neither a ``PermissionError``, an ``IsADirectoryError`` nor a ``FileNotFoundError``, which
    a reader may take for something else (no permission, a folder, nothing there). It keeps the ``errno``, ``strerror``
    and ``filename`` it is given, as an ``OSError`` does. Red until lot B-53 adds it."""
    not_regular = new_in_paths("NotRegularFileError")
    assert isinstance(not_regular, type) and issubclass(not_regular, OSError), f"an OSError: {not_regular!r}"
    kinds = [kind.__name__ for kind in (PermissionError, IsADirectoryError, FileNotFoundError) if issubclass(not_regular, kind)]
    assert kinds == [], f"of its own kind, not a {kinds}: {not_regular.__mro__}"
    error = not_regular(errno.ELOOP, os.strerror(errno.ELOOP), "state.json")
    found = (type(error), error.errno, error.strerror, error.filename)
    assert found == (not_regular, errno.ELOOP, os.strerror(errno.ELOOP), "state.json"), f"its errno, strerror and filename kept, as an OSError's: {found}"
    print_success(f"NotRegularFileError: {[kind.__name__ for kind in not_regular.__mro__]}")


def test_read_regular_file_lets_a_transient_error_of_its_opening_through_as_it_is(tmp_path, monkeypatch):
    """(a) B-53 ``os.open`` failing for the file alone with ``EIO``, as a dying disk fails: that very error reaches the
    caller — not a ``NotRegularFileError``, a ``PermissionError`` nor anything a reader takes for «no file» — so that a
    caller can answer «try again» instead of «none». Red until lot B-53 adds the reader."""
    read = new_in_paths("read_regular_file")
    path = tmp_path / "state.json"
    path.write_bytes(b'{"status": "done"}')
    refusal = opening_fails(monkeypatch, path, errno.EIO)
    with pytest.raises(OSError) as raised:
        read(path)
    assert raised.value is refusal, f"the very EIO os.open raised, as it is: not {type(raised.value).__name__} ({errno.errorcode.get(raised.value.errno or 0)}): {raised.value}"
    print_success("os.open EIO: raised as it is")


@needs_dev_fd
def test_read_regular_file_lets_a_transient_error_of_fstat_through_and_closes_the_descriptor(tmp_path):
    """(a) B-53 ``os.fstat`` failing with ``EIO`` on the descriptor opened for the file, every other call the real one:
    that very error reaches the caller, and the descriptor is closed all the same. Red until lot B-53 adds the reader."""
    read = new_in_paths("read_regular_file")
    path = tmp_path / "state.json"
    path.write_bytes(b'{"status": "done"}')
    refusal = os_error(errno.EIO)
    target, opened = os.path.realpath(path), []
    real_open, real_fstat = os.open, os.fstat

    def opening(file: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        fd = real_open(file, flags, *args, **kwargs)
        if kwargs.get("dir_fd") is None and os.path.realpath(os.fsdecode(file)) == target:
            opened.append(fd)
        return fd

    def failing_fstat(fd: Any, *args: Any, **kwargs: Any) -> os.stat_result:
        if fd in opened:
            raise refusal
        return real_fstat(fd, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(os, "open", opening)
        patch.setattr(os, "fstat", failing_fstat)
        try:
            returned, raised = read(path), None
        except OSError as exc:
            returned, raised = None, exc
    left_open = close_all(descriptors_on(path))  # after the patch: descriptors_on reads every descriptor with os.fstat
    assert opened, "precondition: the reader opened the file through the global os.open"
    assert raised is refusal, f"the very EIO os.fstat raised, as it is: {type(raised).__name__}: {raised} (returned {returned!r})"
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the file once os.fstat failed: {left_open}"
    print_success("os.fstat EIO: raised as it is, the descriptor closed")


# =============================================================================
# (b) snapshot
# =============================================================================


def seed_pairs(path: Path, count: int) -> None:
    """A WAL database whose two tables always hold the same ``seq`` values: each transaction writes one row in each."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal", "precondition: the source runs in WAL mode"
        conn.execute("CREATE TABLE left_side (seq INTEGER PRIMARY KEY, pad BLOB)")
        conn.execute("CREATE TABLE right_side (seq INTEGER PRIMARY KEY, pad BLOB)")
        with conn:
            conn.executemany("INSERT INTO left_side (seq, pad) VALUES (?, randomblob(32))", ((seq,) for seq in range(count)))
            conn.executemany("INSERT INTO right_side (seq, pad) VALUES (?, randomblob(32))", ((seq,) for seq in range(count)))


def seqs(database: Path, table: str) -> list[int]:
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        return [row[0] for row in conn.execute(f"SELECT seq FROM {table} ORDER BY seq")]


class WalWriter(threading.Thread):
    """Another connection of the live database, as the server's: it commits pairs of rows while the copy holds its snapshot."""

    def __init__(self, database: Path, first_seq: int, count: int):
        super().__init__(name="wal-writer", daemon=True)
        self.database = database
        self.first_seq = first_seq
        self.count = count
        self.connected = threading.Event()  # its connection has read the database: -wal and -shm exist
        self.go = threading.Event()  # the copy is paused inside its snapshot
        self.finished = threading.Event()  # it has committed everything, or failed
        self.committed: list[int] = []
        self.failure: Exception | None = None

    def run(self) -> None:
        try:
            with closing(sqlite3.connect(self.database, timeout=WRITER_BUSY_S, isolation_level=None)) as conn:
                conn.execute("SELECT count(*) FROM left_side").fetchone()
                self.connected.set()
                if not self.go.wait(DEADLINE_S):
                    raise TimeoutError("the copy never paused inside its snapshot")
                for seq in range(self.first_seq, self.first_seq + self.count):
                    conn.execute("BEGIN IMMEDIATE")
                    conn.execute("INSERT INTO left_side (seq, pad) VALUES (?, randomblob(32))", (seq,))
                    conn.execute("INSERT INTO right_side (seq, pad) VALUES (?, randomblob(32))", (seq,))
                    conn.execute("COMMIT")
                    self.committed.append(seq)
        except Exception as exc:  # reported by the test's assertions, in the test's thread
            self.failure = exc
        finally:
            self.connected.set()
            self.finished.set()


class CopyPause:
    """The progress handler of the copy's connection: its first call, inside ``VACUUM INTO``, waits for the writer."""

    def __init__(self, writer: WalWriter):
        self.writer = writer
        self.calls = 0

    def __call__(self) -> int:
        self.calls += 1
        if self.calls == 1:
            self.writer.go.set()
            self.writer.finished.wait(DEADLINE_S)
        return 0


def pause_the_copy_of(source: Path, pause: CopyPause, monkeypatch) -> None:
    """Give the connection ``snapshot_database`` opens on ``source`` the progress handler ``pause``; nothing else changes."""
    real_connect = sqlite3.connect

    def connect(database, *args, **kwargs):
        conn = real_connect(database, *args, **kwargs)
        if database == str(source):
            conn.set_progress_handler(pause, PROGRESS_STEPS)
        return conn

    monkeypatch.setattr(snapshot, "sqlite3", SimpleNamespace(connect=connect))


def test_the_copy_is_one_instant_and_never_blocks_a_wal_writer(tmp_path, monkeypatch):
    """(b) While the copy runs, another connection commits in WAL mode: it is not blocked, and the copy holds none of it."""
    print_section("VACUUM INTO beside a WAL writer")
    source = tmp_path / "live" / "app.db"
    target = tmp_path / "copy" / "app.db"
    target.parent.mkdir()
    seed_pairs(source, SEED_ROWS)
    writer = WalWriter(source, SEED_ROWS, WRITES_DURING_COPY)
    pause = CopyPause(writer)
    pause_the_copy_of(source, pause, monkeypatch)
    writer.start()
    try:
        assert writer.connected.wait(DEADLINE_S) and writer.failure is None, f"precondition: the writer could not open the database: {writer.failure!r}"
        assert side_files(source) == ["-wal", "-shm"], f"precondition: the source is live, its -wal and -shm beside it; found {side_files(source)}"
        description = snapshot_database(source, target)
    finally:
        writer.go.set()
        writer.join(DEADLINE_S)
    assert not writer.is_alive(), f"the writer did not end within {DEADLINE_S}s"
    assert pause.calls > 0, "the progress handler never ran inside VACUUM INTO: nothing was written during the copy, so this test proved nothing"
    assert writer.failure is None, f"the writer failed while the copy held its snapshot ({writer.failure!r}): VACUUM INTO must not block a WAL writer"
    assert writer.committed == list(range(SEED_ROWS, SEED_ROWS + WRITES_DURING_COPY)), f"the writer committed {len(writer.committed)} of its {WRITES_DURING_COPY} transactions during the copy"
    left, right = seqs(target, "left_side"), seqs(target, "right_side")
    assert left == right == list(range(SEED_ROWS)), f"the copy must be the database as of one instant: the {SEED_ROWS} pairs committed before it, none of the {WRITES_DURING_COPY} committed while it ran; it holds {len(left)} left and {len(right)} right rows"
    assert seqs(source, "left_side") == list(range(SEED_ROWS + WRITES_DURING_COPY)), "the writer's transactions must be in the live database"
    with closing(sqlite3.connect(f"{target.as_uri()}?mode=ro", uri=True)) as copy:
        journal_mode = copy.execute("PRAGMA journal_mode").fetchone()[0]
    assert journal_mode == "delete", f"the copy must be a standalone rollback-journal database, it is in {journal_mode!r} mode"
    assert target.read_bytes()[18:20] == b"\x01\x01", "the copy's header must say rollback journal (bytes 18-19 = 1, 1), not WAL (2, 2)"
    assert side_files(target) == [], f"nothing may stand beside the copy: {side_files(target)}"
    assert description.integrity_check == "ok", f"the copy must pass its integrity check: {description.integrity_check}"
    assert description.tables == {"left_side": SEED_ROWS, "right_side": SEED_ROWS}, f"the description counts the rows of the copy: {description.tables}"
    assert (description.size, description.sha256) == file_digest(target), "the description's size and SHA-256 are the copy's"
    print_success(f"{WRITES_DURING_COPY} commits during the copy, none in it; copy in rollback mode, integrity ok")


def test_a_missing_source_or_a_taken_target_is_refused(tmp_path):
    """(b) No database, nothing to copy; a target already there is never overwritten."""
    print_section("snapshot_database refusals")
    source = tmp_path / "app.db"
    target = tmp_path / "copy.db"
    with pytest.raises(SnapshotError, match="No database"):
        snapshot_database(source, target)
    folder = tmp_path / "a-folder.db"
    folder.mkdir()
    with pytest.raises(SnapshotError, match="No database"):
        snapshot_database(folder, target)
    assert not target.exists(), "a refused copy writes nothing"
    make_database(source)
    target.write_bytes(b"taken")
    with pytest.raises(SnapshotError, match="already exists"):
        snapshot_database(source, target)
    assert target.read_bytes() == b"taken", "the file in the target's place must be left as it was"
    print_success("missing source, folder as source and taken target refused")


def test_describe_reads_a_database_without_changing_it(tmp_path):
    """(b) Integrity, foreign keys, rows of every table of the application (not SQLite's own), the revision."""
    print_section("describe_database")
    database = tmp_path / "app.db"
    tables = make_database(database)
    size, digest = file_digest(database)
    listing = sorted(os.listdir(tmp_path))
    description = describe_database(database)
    assert file_digest(database) == (size, digest), "describe_database must not change the file it reads"
    assert sorted(os.listdir(tmp_path)) == listing, f"describe_database must create no file beside the database: {sorted(set(os.listdir(tmp_path)) - set(listing))}"
    expected = DatabaseDescription(size=size, sha256=digest, integrity_check="ok", foreign_key_violations=0, tables=tables, alembic_revision=REVISION)
    assert description == expected, f"description {description} differs from {expected} (sqlite_sequence and sqlite_stat1 are not tables of the application)"
    print_success(f"{tables}, revision {REVISION}, file unchanged")


@pytest.mark.parametrize(("revisions", "expected"), [((), None), (("abc123",), "abc123"), (("abc123", "def456"), None)], ids=["no-row", "one-row", "two-rows"])
def test_the_alembic_revision_is_read_only_when_exactly_one_is_recorded(tmp_path, revisions, expected):
    """(b) A restore compares this revision with the app's head: two rows or none mean no revision at all."""
    database = tmp_path / "app.db"
    make_database(database, revisions=revisions)
    description = describe_database(database)
    assert description.alembic_revision == expected, f"alembic_version holds {revisions}: the revision must be {expected!r}, not {description.alembic_revision!r}"
    assert description.tables["alembic_version"] == len(revisions), "alembic_version is counted like any other table"
    print_success(f"{len(revisions)} row(s) → {expected!r}")


def test_a_database_without_alembic_version_has_no_revision(tmp_path):
    database = tmp_path / "app.db"
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("CREATE TABLE notes (body TEXT)")
    description = describe_database(database)
    assert description.alembic_revision is None, f"no alembic_version table, no revision: {description.alembic_revision!r}"
    assert description.tables == {"notes": 0}, f"the empty table is counted with 0 rows: {description.tables}"
    print_success("no alembic_version → None")


def test_foreign_key_violations_are_counted(tmp_path):
    """(b) Rows that point to a missing parent are counted, one per row: the archive keeps them, the manifest says so."""
    database = tmp_path / "app.db"
    make_database(database)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.executemany("INSERT INTO brokers (user_id, name) VALUES (?, ?)", [(404, "orphan 1"), (405, "orphan 2")])
    description = describe_database(database)
    assert description.foreign_key_violations == 2, f"two brokers point to missing users: {description.foreign_key_violations} violation(s) counted"
    assert description.integrity_check == "ok", "foreign keys are not part of the integrity check"
    print_success("2 orphan rows → 2 violations")


def break_not_null(database: Path, rows: int) -> None:
    """Rows that break a NOT NULL constraint the schema now declares: PRAGMA integrity_check reports one line per row."""
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("CREATE TABLE notes (body TEXT)")
        with conn:
            conn.executemany("INSERT INTO notes (body) VALUES (NULL)", [()] * rows)
        conn.execute("PRAGMA writable_schema = ON")
        with conn:
            conn.execute("UPDATE sqlite_schema SET sql = 'CREATE TABLE notes (body TEXT NOT NULL)' WHERE name = 'notes'")


def test_a_failed_integrity_check_keeps_its_first_five_lines(tmp_path):
    database = tmp_path / "app.db"
    make_database(database)
    break_not_null(database, rows=7)
    lines = describe_database(database).integrity_check.split("; ")
    assert len(lines) == 5, f"seven problems: the description keeps the first five lines, joined by '; ', got {len(lines)}: {lines}"
    assert all("notes.body" in line for line in lines), f"every kept line names the broken column notes.body: {lines}"
    print_success(f"7 NULLs in a NOT NULL column → 5 lines: {lines[0]!r} …")


def test_a_database_under_a_path_with_spaces_percent_signs_and_accents_is_copied_and_described(tmp_path):
    """(b) The description opens the file through a ``file:`` URI: every character of the path must survive it."""
    folder = tmp_path / "data dir 100% é"
    folder.mkdir()
    source = folder / "app.db"
    tables = make_database(source)
    description = snapshot_database(source, folder / "copy 50%.db")
    assert description.tables == tables, f"the copy under {folder.name!r} must be described like any other: {description.tables}"
    assert describe_database(source).tables == tables, "the source under the same folder must be described too"
    print_success(f"{folder.name!r}: copied and described")


def test_a_table_whose_name_holds_a_double_quote_is_counted(tmp_path):
    """(b) Every table is counted, whatever its name: a restore describes a database it did not make."""
    database = tmp_path / "app.db"
    tables = make_database(database)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute('CREATE TABLE "odd""name" (x)')
        conn.execute('INSERT INTO "odd""name" (x) VALUES (1)')
    try:
        description = describe_database(database)
    except sqlite3.Error as exc:
        pytest.fail(f'describe_database failed on a table named odd"name ({type(exc).__name__}: {exc}): the name is put between double quotes without doubling the quote it holds')
    assert description.tables == {**tables, 'odd"name': 1}, f'the table odd"name holds one row: {description.tables}'
    print_success('odd"name counted')


def test_file_digest_reads_a_file_of_several_chunks(tmp_path):
    data = bytes(range(256)) * (10 * 1024 + 7)  # 2.5 MiB and a bit: three chunks of the digest, the last partial
    path = tmp_path / "big.bin"
    path.write_bytes(data)
    assert file_digest(path) == (len(data), sha256(data)), "file_digest gives the size and SHA-256 of the whole file"
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    assert file_digest(empty) == (0, sha256(b"")), "an empty file has size 0 and the SHA-256 of nothing"
    print_success(f"{len(data)} bytes digested")


# =============================================================================
# (c) manifest
# =============================================================================


def manifest_document(**overrides) -> dict:
    """A manifest as an archive carries it, as JSON data: valid unless ``overrides`` breaks it."""
    document = {
        "format": "librefolio-backup",
        "format_version": 1,
        "created_at": "2026-10-15T10:15:00+00:00",
        "origin": "cli",
        "app_version": APP_VERSION,
        "alembic_revision": REVISION,
        "database": {"path": "sqlite/app.db", "integrity_check": "ok", "foreign_key_violations": 0, "tables": {"users": 3}},
        "files": [
            {"path": "sqlite/app.db", "size": 8192, "sha256": "a" * 64},
            {"path": "custom-uploads/logo.png", "size": 10, "sha256": "b" * 64},
        ],
        "instance_key": {"included": False},
    }
    document.update(overrides)
    return document


def encoded(document) -> bytes:
    return json.dumps(document).encode("utf-8")


def manifest_code(raw: bytes) -> str:
    with pytest.raises(ManifestError) as raised:
        BackupManifest.from_bytes(raw)
    return raised.value.code


ACCEPTED_PATHS = ["sqlite/app.db", "custom-uploads/logo.png", "custom-uploads/avatars/user-1.webp", "broker_reports/uploaded/2026-10.csv", "scenario_catalog/user-scenarios.json", "custom-uploads/résumé.pdf", "custom-uploads/.hidden"]
REFUSED_PATHS = [
    pytest.param("../etc/passwd", id="parent-folder"),
    pytest.param("custom-uploads/../secrets/instance.key", id="parent-inside"),
    pytest.param("/custom-uploads/logo.png", id="absolute"),
    pytest.param("/sqlite/app.db", id="absolute-database"),
    pytest.param("custom-uploads\\logo.png", id="backslash"),
    pytest.param("custom-uploads/logo\x00.png", id="nul"),
    pytest.param("secrets/instance.key", id="secrets"),
    pytest.param("logs/librefolio.log", id="logs"),
    pytest.param("backups/old.zip", id="backups"),
    pytest.param("scheduler_state.json", id="scheduler-state"),
    pytest.param("sqlite/app.db-wal", id="database-wal"),
    pytest.param("manifest.json", id="manifest"),
    pytest.param("custom-uploads", id="archived-folder-itself"),
    pytest.param("custom-uploads/", id="trailing-slash"),
    pytest.param("custom-uploads//logo.png", id="empty-part"),
    pytest.param("custom-uploads/./logo.png", id="dot-part"),
    pytest.param("./sqlite/app.db", id="dot-database"),
    pytest.param("C:/custom-uploads/logo.png", id="drive"),
    pytest.param("", id="empty"),
]


@pytest.mark.parametrize("value", ACCEPTED_PATHS)
def test_the_database_and_files_below_the_archived_folders_are_entries(value):
    assert check_entry_path(value) == value, f"{value!r} is an entry a backup carries"
    print_success(f"{value!r} accepted")


@pytest.mark.parametrize("value", REFUSED_PATHS)
def test_any_other_path_is_refused_by_the_check_and_by_the_manifest(value):
    """(c) What a restore would write is checked: a path out of the archived folders never comes out of a manifest."""
    with pytest.raises(ValueError, match="not an entry a backup carries"):
        check_entry_path(value)
    files = manifest_document()["files"] + [{"path": value, "size": 1, "sha256": "c" * 64}]
    assert manifest_code(encoded(manifest_document(files=files))) == "manifest_invalid", f"a manifest listing {value!r} must be refused"
    print_success(f"{value!r} refused")


def test_a_manifest_reads_back_as_it_was_written(tmp_path):
    """(c) to_bytes then from_bytes gives the same manifest: UTF-8 JSON, indented, ending with a line break."""
    print_section("Manifest round trip")
    written = BackupManifest(
        created_at=datetime(2026, 10, 15, 12, 15, tzinfo=timezone(timedelta(hours=2))),
        origin="pre-restore",
        app_version=APP_VERSION,
        alembic_revision=REVISION,
        database=ManifestDatabase(integrity_check="ok", foreign_key_violations=0, tables={"users": 3, "brokers": 2}),
        files=[ManifestFile(path=DATABASE_ENTRY, size=8192, sha256="a" * 64), ManifestFile(path="custom-uploads/résumé.pdf", size=0, sha256=sha256(b""))],
    )
    raw = written.to_bytes()
    assert raw.endswith(b"}\n") and raw.startswith(b'{\n  "'), "the manifest is indented JSON ending with a line break"
    assert "résumé".encode() in raw, "non-ASCII paths are written as UTF-8, not escaped"
    read = BackupManifest.from_bytes(raw)
    assert read == written, f"the manifest read back differs from the one written: {read} != {written}"
    assert (read.format, read.format_version) == (FORMAT, FORMAT_VERSION) == ("librefolio-backup", 1), "format librefolio-backup, version 1"
    assert read.created_at == datetime(2026, 10, 15, 10, 15, tzinfo=UTC) and read.created_at.tzinfo == UTC, f"created_at is kept in UTC: {read.created_at!r}"
    assert read.instance_key.included is False, "an archive without password never carries the instance key"
    print_success("written, read back, equal; 12:15+02:00 kept as 10:15 UTC")


def test_unknown_fields_are_ignored_at_every_level():
    """(c) A field a later version adds is ignored by this one: the format version changes only for incompatible changes."""
    document = manifest_document(compression="zstd", note="added later")
    document["database"]["page_size"] = 4096
    document["files"][1]["mode"] = "0600"
    document["instance_key"]["algorithm"] = "added later"
    read = BackupManifest.from_bytes(encoded(document))
    dumped = read.model_dump()
    assert "compression" not in dumped and "note" not in dumped, f"unknown top-level fields are ignored: {sorted(dumped)}"
    assert "page_size" not in dumped["database"] and "mode" not in dumped["files"][1] and "algorithm" not in dumped["instance_key"], "unknown nested fields are ignored"
    assert [entry.path for entry in read.files] == [DATABASE_ENTRY, "custom-uploads/logo.png"], "the known fields are read as usual"
    print_success("unknown fields ignored at the top, in database, in a file and in instance_key")


def test_created_at_must_carry_its_time_zone():
    assert manifest_code(encoded(manifest_document(created_at="2026-10-15T10:15:00"))) == "manifest_invalid", "a date without time zone is ambiguous: refused"
    read = BackupManifest.from_bytes(encoded(manifest_document(created_at="2026-10-15T07:15:00-03:00")))
    assert read.created_at == datetime(2026, 10, 15, 10, 15, tzinfo=UTC), f"an aware date is converted to UTC: {read.created_at!r}"
    print_success("naive date refused, -03:00 converted to UTC")


@pytest.mark.parametrize(
    "files",
    [
        pytest.param([], id="no-entry"),
        pytest.param([{"path": "custom-uploads/logo.png", "size": 10, "sha256": "b" * 64}], id="no-database"),
        pytest.param([{"path": "custom-uploads/logo.png", "size": 10, "sha256": "b" * 64}, {"path": "sqlite/app.db", "size": 8192, "sha256": "a" * 64}], id="database-second"),
        pytest.param([{"path": "sqlite/app.db", "size": 8192, "sha256": "a" * 64}, {"path": "sqlite/app.db", "size": 8192, "sha256": "a" * 64}], id="database-twice"),
        pytest.param([{"path": "sqlite/app.db", "size": 8192, "sha256": "a" * 64}] + [{"path": "custom-uploads/logo.png", "size": 10, "sha256": "b" * 64}] * 2, id="file-twice"),
    ],
)
def test_the_database_comes_first_and_no_entry_is_listed_twice(files):
    assert manifest_code(encoded(manifest_document(files=files))) == "manifest_invalid", f"files {[entry['path'] for entry in files]} must be refused"
    print_success(f"{[entry['path'] for entry in files]} refused")


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        pytest.param(b"\xff\xfe{}", "manifest_unreadable", id="not-utf8"),
        pytest.param(b"{not json", "manifest_unreadable", id="not-json"),
        pytest.param(b"", "manifest_unreadable", id="empty"),
        pytest.param(b"[]", "manifest_unknown_format", id="json-array"),
        pytest.param(b'"librefolio-backup"', "manifest_unknown_format", id="json-string"),
        pytest.param(b"{}", "manifest_unknown_format", id="no-format"),
        pytest.param(encoded(manifest_document(format="another-backup")), "manifest_unknown_format", id="another-format"),
        pytest.param(encoded(manifest_document(format="LibreFolio-Backup")), "manifest_unknown_format", id="format-other-case"),
        pytest.param(encoded({key: value for key, value in manifest_document().items() if key != "format_version"}), "manifest_invalid", id="no-version"),
        pytest.param(encoded(manifest_document(format_version="1")), "manifest_invalid", id="version-string"),
        pytest.param(encoded(manifest_document(format_version=True)), "manifest_invalid", id="version-true"),
        pytest.param(encoded(manifest_document(format_version=1.0)), "manifest_invalid", id="version-float"),
        pytest.param(encoded(manifest_document(format_version=0)), "manifest_invalid", id="version-0"),
        pytest.param(encoded(manifest_document(format_version=-1)), "manifest_invalid", id="version-negative"),
        pytest.param(encoded(manifest_document(format_version=2)), "manifest_newer_format", id="version-2"),
        pytest.param(encoded(manifest_document(format_version=2, files=[], origin="unknown")), "manifest_newer_format", id="version-2-before-fields"),
        pytest.param(encoded(manifest_document(format="another-backup", format_version="x")), "manifest_unknown_format", id="format-before-version"),
        pytest.param(encoded(manifest_document(origin="cron")), "manifest_invalid", id="unknown-origin"),
        pytest.param(encoded(manifest_document(files=[{"path": "sqlite/app.db", "size": -1, "sha256": "a" * 64}])), "manifest_invalid", id="negative-size"),
        pytest.param(encoded(manifest_document(files=[{"path": "sqlite/app.db", "size": 1, "sha256": "A" * 64}])), "manifest_invalid", id="uppercase-sha256"),
        pytest.param(encoded(manifest_document(database={"path": "sqlite/other.db", "integrity_check": "ok", "foreign_key_violations": 0, "tables": {}})), "manifest_invalid", id="database-elsewhere"),
        pytest.param(encoded({key: value for key, value in manifest_document().items() if key != "created_at"}), "manifest_invalid", id="no-created-at"),
    ],
)
def test_from_bytes_says_why_it_refuses_a_manifest(raw, code):
    """(c) The format and its version are checked before the fields: a newer archive says so, never 'invalid'."""
    assert manifest_code(raw) == code, f"{raw[:80]!r} must be refused as {code}"
    print_success(code)


def test_a_manifest_larger_than_64_mib_is_refused_before_anything_else():
    assert MANIFEST_MAX_BYTES == 64 * 1024 * 1024, f"the limit is 64 MiB, not {MANIFEST_MAX_BYTES}"
    raw = encoded(manifest_document()) + b" " * (MANIFEST_MAX_BYTES + 1)
    assert manifest_code(raw) == "manifest_too_large", "one byte over 64 MiB is too large, however valid the JSON"
    error = ManifestError("manifest_too_large", "message")
    assert isinstance(error, ValueError) and error.code == "manifest_too_large", "ManifestError is a ValueError with a stable code"
    print_success("64 MiB + 1 byte refused as manifest_too_large")


def test_a_manifest_of_exactly_the_limit_is_not_refused_for_its_size(monkeypatch):
    """(c) The limit itself is allowed: shown with a limit of 4 KiB, the module reading it at each call."""
    monkeypatch.setattr("backend.app.services.platform.instance_backup.manifest.MANIFEST_MAX_BYTES", 4096)
    body = encoded(manifest_document())
    assert BackupManifest.from_bytes(body + b" " * (4096 - len(body))).origin == "cli", "a manifest of exactly the limit is read"
    assert manifest_code(body + b" " * (4097 - len(body))) == "manifest_too_large", "one byte over the limit is refused"
    print_success("limit allowed, limit + 1 refused")


# =============================================================================
# (d) collect_files / build_archive
# =============================================================================


@needs_symlinks
def test_the_archive_carries_the_database_and_the_archived_folders_and_nothing_else(live_data, tmp_path):
    """(d) No log, secret, scheduler state, backup, stray file or SQLite side file; every archived file, byte for byte."""
    print_section("What an archive carries")
    built = build_into(live_data.root, tmp_path / "work")
    names = entry_names(built.path)
    assert names[0] == DATABASE_ENTRY, f"the database must be the first entry, not {names[0]!r}"
    assert names[-1] == MANIFEST_ENTRY, f"the manifest must be the last entry, not {names[-1]!r}"
    assert len(names) == len(set(names)), f"no entry may be written twice: {names}"
    extra, missing = sorted(set(names[1:-1]) - set(ARCHIVED_FILES)), sorted(set(ARCHIVED_FILES) - set(names[1:-1]))
    assert not extra, f"entries that no archive may carry: {extra}"
    assert not missing, f"files of the archived folders left out of the archive: {missing}"
    with zipfile.ZipFile(built.path) as zf:
        changed = [entry for entry, content in ARCHIVED_FILES.items() if zf.read(entry) != content]
        holding_the_key = [name for name in names if SECRET in zf.read(name)]
    assert not changed, f"archived files must be stored byte for byte: {changed}"
    assert not holding_the_key, f"the instance key reached the archive through {holding_the_key}"
    print_success(f"{len(names)} entries: the database, {len(ARCHIVED_FILES)} files, the manifest")


@needs_symlinks
def test_links_are_left_out_reported_and_never_followed(live_data, tmp_path):
    """(d) A link to the instance key or to the secrets folder, inside an archived folder, is reported and not followed."""
    built = build_into(live_data.root, tmp_path / "work")
    assert sorted(built.skipped) == sorted(LINKS), f"the links must be reported as left out, exactly: {sorted(built.skipped)}"
    assert built.warnings == ("files_skipped",), f"left-out entries give the warning files_skipped, and nothing else here: {built.warnings}"
    assert not [name for name in entry_names(built.path) if name.startswith(tuple(LINKS))], "nothing below a link may be archived"
    print_success(f"left out: {sorted(built.skipped)}")


@needs_symlinks
def test_the_database_entry_is_a_consistent_copy_with_the_rows_still_in_the_wal(live_data, tmp_path):
    """(d) The rows committed but not yet checkpointed are in the archive; the copy is a standalone rollback database."""
    alone = tmp_path / "main-file-alone.db"
    shutil.copyfile(live_data.root / DATABASE_ENTRY, alone)
    assert count_rows(alone, "users") == 3, "precondition: two users are committed in the -wal only, the main file alone has three"
    built = build_into(live_data.root, tmp_path / "work")
    extracted = tmp_path / "extracted.db"
    with zipfile.ZipFile(built.path) as zf:
        extracted.write_bytes(zf.read(DATABASE_ENTRY))
    description = describe_database(extracted)
    assert description.tables == live_data.tables, f"the archived database must hold every committed row, the -wal's included: {description.tables} != {live_data.tables}"
    assert description.integrity_check == "ok", f"the archived database must pass its integrity check: {description.integrity_check}"
    assert extracted.read_bytes()[18:20] == b"\x01\x01", "the archived database must be in rollback-journal mode, readable without a -wal"
    print_success(f"archived database: {description.tables}")


@needs_symlinks
def test_every_entry_matches_the_manifest_and_the_manifest_describes_the_build(live_data, tmp_path):
    """(d) Size and SHA-256 of every entry; origin, version, revision, database facts and date of the build."""
    print_section("Manifest of a build")
    before = datetime.now(UTC)
    built = build_into(live_data.root, tmp_path / "work", origin="ui")
    after = datetime.now(UTC)
    with zipfile.ZipFile(built.path) as zf:
        stored = BackupManifest.from_bytes(zf.read(MANIFEST_ENTRY))
        actual = {name: (len(data), sha256(data)) for name in zf.namelist() if name != MANIFEST_ENTRY for data in [zf.read(name)]}
        order = [name for name in zf.namelist() if name != MANIFEST_ENTRY]
    assert stored == built.manifest, "the manifest in the archive is the one the build returns"
    assert [entry.path for entry in stored.files] == order, "the manifest lists every entry but itself, in the archive's order, the database first"
    wrong = [entry.path for entry in stored.files if (entry.size, entry.sha256) != actual[entry.path]]
    assert not wrong, f"entries whose size or SHA-256 differ from the manifest: {wrong}"
    assert (stored.origin, stored.app_version, stored.alembic_revision) == ("ui", APP_VERSION, REVISION), f"origin, app version and revision of the build: {stored.origin}, {stored.app_version}, {stored.alembic_revision}"
    assert stored.database == ManifestDatabase(integrity_check="ok", foreign_key_violations=0, tables=live_data.tables), f"the database facts of the copy: {stored.database}"
    assert before <= stored.created_at <= after and stored.created_at.tzinfo == UTC, f"created_at is the build's time, in UTC: {stored.created_at!r}"
    assert (built.path, built.size, built.sha256) == (tmp_path / "work" / "librefolio-backup-test.zip", *file_digest(built.path)), "the build returns the archive's path, size and SHA-256"
    print_success(f"{len(stored.files)} entries match; origin ui, {APP_VERSION}, revision {REVISION}")


@needs_posix_modes
def test_the_archive_and_its_entries_are_readable_by_their_owner_only(tmp_path):
    """(d) The archive holds every user's data: the file is created 0600, and every entry unpacks 0600, deflated."""
    built = small_archive(tmp_path)
    assert mode(built.path) == 0o600, f"the archive must be created readable by its owner only (0600), it is {oct(mode(built.path))}"
    with zipfile.ZipFile(built.path) as zf:
        loose = [(info.filename, oct(info.external_attr >> 16)) for info in zf.infolist() if info.external_attr >> 16 != stat.S_IFREG | 0o600]
        stored = [info.filename for info in zf.infolist() if info.compress_type != zipfile.ZIP_DEFLATED]
    assert not loose, f"entries that would unpack with other permissions than a regular file 0600: {loose}"
    assert not stored, f"entries not deflated: {stored}"
    assert sorted(os.listdir(tmp_path / "work")) == [built.path.name], f"the work folder keeps the archive alone, no .part and no database copy: {sorted(os.listdir(tmp_path / 'work'))}"
    print_success("archive 0600, entries 0600 and deflated, nothing else left in the work folder")


def test_a_file_dated_before_1980_is_dated_1980_in_the_archive(tmp_path):
    """(d) A zip cannot date an entry before 1980: such a file is archived, dated at the zip's first day."""
    data = small_data_dir(tmp_path / "data")
    os.utime(data / "custom-uploads" / "a.txt", (0, 0))
    built = build_into(data, tmp_path / "work")
    with zipfile.ZipFile(built.path) as zf:
        assert zf.getinfo("custom-uploads/a.txt").date_time == (1980, 1, 1, 0, 0, 0), "a file of 1970 is dated 1980-01-01 00:00:00 in the archive"
    print_success("1970 → 1980-01-01")


def test_a_file_dated_after_2107_does_not_stop_the_backup(tmp_path):
    """(d) A zip cannot date an entry after 2107 either: one such file must not make every backup of the instance fail."""
    data = small_data_dir(tmp_path / "data")
    future = datetime(2200, 1, 1, tzinfo=UTC).timestamp()
    os.utime(data / "custom-uploads" / "a.txt", (future, future))
    try:
        built = build_into(data, tmp_path / "work")
    except (struct.error, ValueError) as exc:
        pytest.fail(f"one file dated 2200 made the build fail ({type(exc).__name__}: {exc}): _entry_info clamps the date to 1980 at the bottom but not to 2107 at the top, so no backup of this instance can be made until the file is touched")
    with zipfile.ZipFile(built.path) as zf:
        info = zf.getinfo("custom-uploads/a.txt")
        assert zf.read(info) == (data / "custom-uploads" / "a.txt").read_bytes(), "the file is archived whole"
    assert info.date_time <= ZIP_LAST_DATE, f"the entry carries a date a zip can hold: {info.date_time}"
    print_success(f"2200 → {info.date_time}")


def test_progress_goes_through_the_phases_and_ends_at_the_total(tmp_path):
    """(d) preparing, database, files, finalizing; the bytes done never go back and end at the database plus the files."""
    data = small_data_dir(tmp_path / "data")
    calls: list[tuple[str, int, int]] = []
    built = build_into(data, tmp_path / "work", progress=lambda phase, done, total: calls.append((phase, done, total)))
    phases = [phase for index, (phase, _, _) in enumerate(calls) if index == 0 or calls[index - 1][0] != phase]
    assert phases == ["preparing", "database", "files", "finalizing"], f"the phases must come in this order, each once: {phases}"
    total = sum(entry.size for entry in built.manifest.files)
    assert calls[-1] == ("finalizing", total, total), f"the last report is finalizing with every byte done: {calls[-1]}, total {total}"
    done = [done for _, done, _ in calls]
    assert done == sorted(done), "the bytes done never go back"
    print_success(f"{len(calls)} reports, {total} bytes")


@needs_symlinks
def test_the_space_needed_is_the_database_twice_its_wal_included_plus_the_files_and_a_margin(live_data):
    """(d) The copy, then the copy inside the archive, the files, and 64 MiB for the file system."""
    database = live_data.root / DATABASE_ENTRY
    wal = database.with_name(database.name + "-wal")
    assert wal.stat().st_size > 0, "precondition: the live database has rows in its -wal"
    files, _ = collect_files(live_data.root)
    expected = 2 * (database.stat().st_size + wal.stat().st_size) + sum(len(content) for content in ARCHIVED_FILES.values()) + 64 * 1024 * 1024
    assert required_space(live_data.root, files) == expected, f"required_space must be 2 × (database + wal) + files + 64 MiB = {expected}"
    print_success(f"{expected} bytes")


def test_a_wal_that_goes_while_the_space_is_counted_counts_as_none(tmp_path, monkeypatch):
    """(d) L3-2: SQLite removes the ``-wal`` when its last connection closes, at any moment, so the file can be there when
    it is looked for and gone when it is measured. Measured on the shared test server: a backup then failed with
    ``backup_failed`` (``FileNotFoundError`` on ``app.db-wal``). The count takes it as absent and the backup goes on.
    Red before L3-2: ``required_space`` checked ``exists()`` then called ``stat()``, and the second raised."""
    database = tmp_path / DATABASE_ENTRY
    database.parent.mkdir(parents=True)
    database.write_bytes(b"\0" * 4096)
    wal = database.with_name(database.name + "-wal")
    real_exists = Path.exists
    # The -wal is «there» when looked for, and gone when measured: the window of the race, held open.
    monkeypatch.setattr(Path, "exists", lambda self, *args, **kwargs: True if self == wal else real_exists(self, *args, **kwargs))
    assert not wal.is_file(), "precondition: the -wal is gone"
    try:
        needed = required_space(tmp_path, [])
    except FileNotFoundError as exc:
        pytest.fail(f"a -wal gone between its lookup and its size failed the count: {exc}")
    assert needed == 2 * 4096 + 64 * 1024 * 1024, f"the database twice and the margin, the -wal none: {needed}"
    print_success(f"{needed} bytes, the -wal gone")


def test_without_enough_space_nothing_is_written(tmp_path, monkeypatch):
    """(d) The space is checked before the copy: one byte short and the build stops with nothing in the work folder."""
    data = small_data_dir(tmp_path / "data")
    work = tmp_path / "work"
    work.mkdir()
    needed = required_space(data, collect_files(data)[0])
    monkeypatch.setattr(archive.shutil, "disk_usage", lambda path: SimpleNamespace(total=needed * 2, used=0, free=needed - 1))
    with pytest.raises(BackupNoSpaceError) as raised:
        build_archive(data, work, work / "backup.zip", origin="cli")
    assert (raised.value.needed, raised.value.free) == (needed, needed - 1), f"the error says what is needed and what is free: {raised.value.needed}, {raised.value.free}"
    assert list(work.iterdir()) == [], f"nothing may be written without the space: {sorted(p.name for p in work.iterdir())}"
    monkeypatch.setattr(archive.shutil, "disk_usage", lambda path: SimpleNamespace(total=needed * 2, used=0, free=needed))
    assert build_archive(data, work, work / "backup.zip", origin="cli").path.is_file(), "exactly the space needed is enough"
    print_success(f"{needed - 1} free of {needed} refused, {needed} accepted")


def test_a_failure_during_the_build_never_leaves_a_file_under_the_final_name(tmp_path, monkeypatch):
    """(d) The archive is written as <name>.part: a failure leaves that partial file, 0600, for the caller to remove."""
    data = small_data_dir(tmp_path / "data")
    work = tmp_path / "work"
    work.mkdir()
    target = work / "librefolio-backup-test.zip"

    def no_version() -> str:
        raise RuntimeError("the version cannot be read")

    monkeypatch.setattr(archive, "get_version", no_version)
    with pytest.raises(RuntimeError, match="the version cannot be read"):
        build_archive(data, work, target, origin="cli")
    assert not target.exists(), "a failed build must not leave a file under the final name"
    assert sorted(os.listdir(work)) == [target.name + ".part"], f"the failure leaves the partial archive alone, the database copy removed: {sorted(os.listdir(work))}"
    if POSIX:
        assert mode(work / (target.name + ".part")) == 0o600, "even a partial archive holds data: 0600 from its creation"
    print_success("failure after the files: only <name>.part, 0600")


def test_a_build_without_database_fails_before_writing_anything(tmp_path):
    data = tmp_path / "data"
    write_files(data, {"custom-uploads/a.txt": b"a file but no database"})
    work = tmp_path / "work"
    work.mkdir()
    with pytest.raises(SnapshotError, match="No database"):
        build_archive(data, work, work / "backup.zip", origin="cli")
    assert list(work.iterdir()) == [], "no database, nothing written"
    print_success("no database → SnapshotError, nothing written")


def test_a_file_that_vanishes_during_the_build_is_reported_and_the_build_goes_on(tmp_path, monkeypatch):
    """(d) A file collected and then removed (a report parsed and moved meanwhile) is left out with a warning."""
    data = small_data_dir(tmp_path / "data")
    real_collect = archive.collect_files

    def collect_then_vanish(data_dir):
        collected = real_collect(data_dir)
        (data_dir / "broker_reports" / "uploaded" / "r.csv").unlink()
        return collected

    monkeypatch.setattr(archive, "collect_files", collect_then_vanish)
    built = build_into(data, tmp_path / "work")
    assert built.skipped == ("broker_reports/uploaded/r.csv",), f"the vanished file is reported as left out: {built.skipped}"
    assert built.warnings == ("files_skipped",), f"and the build warns files_skipped: {built.warnings}"
    assert "broker_reports/uploaded/r.csv" not in entry_names(built.path), "the vanished file is not in the archive"
    assert check_archive(built.path).ok, "the archive written without it is consistent with its manifest"
    print_success("vanished file left out, archive consistent")


@needs_symlinks
def test_a_file_replaced_by_a_link_during_the_build_is_never_followed(tmp_path, monkeypatch):
    """(d) Collected as a file, swapped for a link to the instance key before it is read: opened without following links."""
    data = small_data_dir(tmp_path / "data")
    write_files(data, {"secrets/instance.key": SECRET})
    real_collect = archive.collect_files

    def collect_then_swap(data_dir):
        collected = real_collect(data_dir)
        swapped = data_dir / "custom-uploads" / "a.txt"
        swapped.unlink()
        swapped.symlink_to(data_dir / "secrets" / "instance.key")
        return collected

    monkeypatch.setattr(archive, "collect_files", collect_then_swap)
    built = build_into(data, tmp_path / "work")
    assert built.skipped == ("custom-uploads/a.txt",), f"the swapped file is reported as left out: {built.skipped}"
    with zipfile.ZipFile(built.path) as zf:
        assert not [name for name in zf.namelist() if SECRET in zf.read(name)], "the instance key must not reach the archive through the swapped link"
    print_success("swapped link not followed")


@needs_symlinks
@pytest.mark.parametrize("replacement", ["link-to-the-secrets-folder", "file"])
def test_an_archived_folder_that_is_not_a_folder_is_reported_and_never_followed(tmp_path, replacement):
    data = small_data_dir(tmp_path / "data")
    write_files(data, {"secrets/instance.key": SECRET})
    shutil.rmtree(data / "scenario_catalog")
    if replacement == "file":
        (data / "scenario_catalog").write_bytes(SECRET)
    else:
        (data / "scenario_catalog").symlink_to(data / "secrets", target_is_directory=True)
    built = build_into(data, tmp_path / "work")
    assert built.skipped == ("scenario_catalog",), f"the folder is reported as left out, as a whole: {built.skipped}"
    with zipfile.ZipFile(built.path) as zf:
        assert not [name for name in zf.namelist() if name.startswith("scenario_catalog") or SECRET in zf.read(name)], "nothing of it may be archived"
    print_success(f"scenario_catalog as a {replacement}: left out")


def test_missing_archived_folders_are_simply_absent(tmp_path):
    data = tmp_path / "data"
    make_database(data / DATABASE_ENTRY)
    built = build_into(data, tmp_path / "work")
    assert entry_names(built.path) == [DATABASE_ENTRY, MANIFEST_ENTRY], "a database alone: the database and the manifest"
    assert (built.skipped, built.warnings) == ((), ()), f"an absent folder is no warning: {built.skipped}, {built.warnings}"
    print_success("database only → two entries, no warning")


@needs_fifo
def test_a_fifo_is_left_out_and_never_opened(tmp_path):
    """(d) Reading a FIFO waits for a writer that never comes: it is reported, never opened. A hang is a failure here."""
    data = small_data_dir(tmp_path / "data")
    fifo = data / "custom-uploads" / "pipe"
    os.mkfifo(fifo)
    outcome: dict[str, object] = {}

    def build() -> None:
        try:
            outcome["built"] = build_into(data, tmp_path / "work")
        except Exception as exc:  # reported below, in the test's thread
            outcome["error"] = exc

    worker = threading.Thread(target=build, name="fifo-build", daemon=True)
    worker.start()
    worker.join(DEADLINE_S)
    if worker.is_alive():
        os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))  # a writer appears and leaves: the blocked read ends
        worker.join(DEADLINE_S)
        pytest.fail(f"the build was still running after {DEADLINE_S}s: it opened the FIFO and waited for a writer")
    assert "error" not in outcome, f"the build failed: {outcome.get('error')!r}"
    built = outcome["built"]
    assert built.skipped == ("custom-uploads/pipe",), f"the FIFO is reported as left out: {built.skipped}"
    assert "custom-uploads/pipe" not in entry_names(built.path), "the FIFO is not in the archive"
    print_success("FIFO left out without being opened")


def test_a_name_that_is_not_utf8_is_reported_not_archived(tmp_path):
    """(d) An entry name must be UTF-8 to be restored anywhere: such a file is left out, its name reported readably."""
    data = small_data_dir(tmp_path / "data")
    raw_name = os.fsencode(data / "custom-uploads") + b"/report-\xff.csv"
    try:
        os.close(os.open(raw_name, os.O_WRONLY | os.O_CREAT, 0o600))
    except OSError as exc:
        pytest.skip(f"this file system refuses a name that is not UTF-8 ({exc.strerror})")
    built = build_into(data, tmp_path / "work")
    assert built.skipped == ("custom-uploads/report-?.csv",), f"the file is reported with its bad byte replaced: {built.skipped}"
    assert [name for name in entry_names(built.path) if "report-" in name] == [], "the file is not in the archive"
    print_success("non-UTF-8 name left out and reported")


@needs_permission_checks
def test_a_folder_that_cannot_be_read_is_reported_never_silently_left_out(tmp_path):
    """(d) A subfolder the server cannot list (left by a command run as root) must not vanish from a backup in silence."""
    data = small_data_dir(tmp_path / "data")
    locked = data / "custom-uploads" / "locked"
    write_files(data, {"custom-uploads/locked/statement.pdf": b"%PDF-1.7 a statement"})
    locked.chmod(0)
    try:
        built = build_into(data, tmp_path / "work")
    finally:
        locked.chmod(0o700)
    reported = [entry for entry in built.skipped if entry == "custom-uploads/locked" or entry.startswith("custom-uploads/locked/")]
    assert reported and "files_skipped" in built.warnings, f"custom-uploads/locked could not be read and its files are not in the archive, yet the build reports nothing (skipped {built.skipped}, warnings {built.warnings}): os.walk drops a folder it cannot list unless it is given an onerror"
    print_success(f"unreadable folder reported: {reported}")


def broken_database(path: Path) -> None:
    make_database(path)
    break_not_null(path, rows=2)
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("INSERT INTO brokers (user_id, name) VALUES (404, 'orphan')")


def test_a_database_that_fails_its_checks_is_archived_as_it_is_with_warnings(tmp_path):
    """(d) Integrity problems and foreign-key violations do not stop a backup: they are warnings, and the manifest says them."""
    data = tmp_path / "data"
    broken_database(data / DATABASE_ENTRY)
    built = build_into(data, tmp_path / "work")
    assert built.warnings == ("database_integrity", "foreign_key_violations"), f"both problems are warned, in this order: {built.warnings}"
    database = built.manifest.database
    assert database.integrity_check != "ok" and "notes.body" in database.integrity_check, f"the manifest keeps the integrity check's result: {database.integrity_check!r}"
    assert database.foreign_key_violations == 1, f"and the number of foreign-key violations: {database.foreign_key_violations}"
    assert check_archive(built.path).ok, "the archive itself is consistent with its manifest"
    print_success(f"warnings {built.warnings}")


# =============================================================================
# (e) check_archive
# =============================================================================


def test_an_intact_archive_checks_ok(tmp_path):
    print_section("check_archive")
    built = small_archive(tmp_path)
    check = check_archive(built.path)
    assert check.ok and check.verified, f"an intact archive checks ok, verified: missing {check.missing}, mismatched {check.mismatched}, unexpected {check.unexpected}"
    assert check.manifest == built.manifest, "the check returns the archive's manifest"
    print_success("intact archive: ok, verified")


def test_without_verification_only_the_names_are_checked(tmp_path):
    """(e) ``verify=False`` reads the manifest and the names: other bytes under a listed name go unnoticed, by design."""
    built = small_archive(tmp_path)
    content = (tmp_path / "data" / "custom-uploads" / "a.txt").read_bytes()
    tampered = rewrite(built.path, tmp_path / "tampered.zip", swap={"custom-uploads/a.txt": content.upper()})
    check = check_archive(tampered, verify=False)
    assert check.ok and not check.verified, f"unverified, an archive with the right names checks ok: {check}"
    assert not check_archive(tampered).ok, "verified, the same archive does not"
    print_success("verify=False: names only")


def test_a_missing_entry_is_reported(tmp_path):
    built = small_archive(tmp_path)
    check = check_archive(rewrite(built.path, tmp_path / "missing.zip", drop=("custom-uploads/a.txt",)))
    assert (check.missing, check.mismatched, check.unexpected) == (["custom-uploads/a.txt"], [], []), f"only the dropped entry is missing: {check}"
    assert not check.ok, "an archive with a missing entry is not ok"
    print_success("missing: custom-uploads/a.txt")


@pytest.mark.parametrize("change", ["other-bytes-same-size", "one-byte-less", "one-byte-more"])
def test_an_entry_whose_bytes_differ_from_the_manifest_is_mismatched(tmp_path, change):
    built = small_archive(tmp_path)
    content = (tmp_path / "data" / "custom-uploads" / "a.txt").read_bytes()
    altered = {"other-bytes-same-size": content.upper(), "one-byte-less": content[:-1], "one-byte-more": content + b"!"}[change]
    check = check_archive(rewrite(built.path, tmp_path / "altered.zip", swap={"custom-uploads/a.txt": altered}))
    assert (check.missing, check.mismatched, check.unexpected) == ([], ["custom-uploads/a.txt"], []), f"{change}: the entry is mismatched, nothing else: {check}"
    print_success(f"{change}: mismatched")


def test_an_entry_larger_than_declared_is_read_one_byte_past_its_size_and_no_further(tmp_path, monkeypatch):
    """(e) Ten MiB where the manifest declares a few hundred bytes: the check reads the declared size plus one byte."""
    built = small_archive(tmp_path)
    declared = next(entry.size for entry in built.manifest.files if entry.path == "custom-uploads/a.txt")
    inflated = rewrite(built.path, tmp_path / "inflated.zip", swap={"custom-uploads/a.txt": bytes(10 * 1024 * 1024)})
    reads = record_reads(monkeypatch)
    check = check_archive(inflated)
    assert check.mismatched == ["custom-uploads/a.txt"], f"an entry larger than declared is mismatched: {check}"
    read = sum(size for name, size in reads if name == "custom-uploads/a.txt")
    assert read == declared + 1, f"the check must read {declared} + 1 bytes of the entry to know it is larger, it read {read}"
    print_success(f"10 MiB entry declared {declared} bytes: {read} bytes read")


def test_an_entry_the_manifest_does_not_list_is_unexpected(tmp_path):
    built = small_archive(tmp_path)
    check = check_archive(rewrite(built.path, tmp_path / "extra.zip", add={"secrets/instance.key": SECRET, "custom-uploads/new.txt": b"new"}))
    assert (check.missing, check.mismatched, check.unexpected) == ([], [], ["custom-uploads/new.txt", "secrets/instance.key"]), f"both added entries are unexpected, sorted: {check}"
    print_success(f"unexpected: {check.unexpected}")


@pytest.mark.parametrize("twice", ["custom-uploads/a.txt", MANIFEST_ENTRY])
def test_a_name_written_twice_is_unexpected(tmp_path, twice):
    """(e) Which of two entries of one name a restore would write is not defined: the name is reported, even the manifest's."""
    built = small_archive(tmp_path)
    check = check_archive(rewrite(built.path, tmp_path / "twice.zip", twice=(twice,)))
    assert (check.missing, check.mismatched, check.unexpected) == ([], [], [twice]), f"the duplicated name {twice} is unexpected, and only that: {check}"
    print_success(f"{twice} twice: unexpected")


@pytest.mark.parametrize("case", ["text-file", "no-file"])
def test_a_file_that_is_not_a_zip_is_archive_unreadable(tmp_path, case):
    path = tmp_path / "not-a-zip.zip"
    if case == "text-file":
        path.write_text("these are not the bytes of a zip\n", encoding="utf-8")
    with pytest.raises(ArchiveError) as raised:
        check_archive(path)
    assert raised.value.code == "archive_unreadable", f"{case}: code {raised.value.code}"
    print_success(f"{case}: archive_unreadable")


@pytest.mark.parametrize(("manifest", "code"), [(None, "manifest_missing"), (b"{not json", "manifest_unreadable"), (encoded(manifest_document(format_version=9)), "manifest_newer_format")])
def test_an_archive_whose_manifest_cannot_be_used_is_refused_with_its_code(tmp_path, manifest, code):
    built = small_archive(tmp_path)
    if manifest is None:
        changed = rewrite(built.path, tmp_path / "changed.zip", drop=(MANIFEST_ENTRY,))
    else:
        changed = rewrite(built.path, tmp_path / "changed.zip", swap={MANIFEST_ENTRY: manifest})
    with pytest.raises(ManifestError) as raised:
        check_archive(changed)
    assert raised.value.code == code, f"code {raised.value.code}, expected {code}"
    print_success(code)


@pytest.mark.parametrize("entry", ["custom-uploads/a.txt", MANIFEST_ENTRY])
def test_a_corrupted_entry_is_reported_never_raised_as_a_zip_error(tmp_path, entry):
    """(e) Bit rot, a damaged copy: the zip is intact but one entry's data is not. The check must say so in its own terms.

    The documented outcomes are a report (mismatched), ``ArchiveError`` or, for the manifest, ``ManifestError``: those
    are what ``./dev.py backup inspect`` and the restore check catch. A raw ``zipfile.BadZipFile`` or ``zlib.error``
    escapes them both.
    """
    built = small_archive(tmp_path)
    damaged = corrupt(built.path, tmp_path / "damaged.zip", entry)
    try:
        check = check_archive(damaged)
    except (ArchiveError, ManifestError):
        print_success(f"{entry} corrupted: refused with a code")
        return
    except Exception as exc:
        pytest.fail(f"check_archive raised {type(exc).__module__}.{type(exc).__name__} ({exc}) for an archive whose entry {entry} is corrupted: it must report it (mismatched), or raise ArchiveError / ManifestError")
    assert entry in check.mismatched and not check.ok, f"the corrupted entry must be reported as mismatched: {check}"
    print_success(f"{entry} corrupted: mismatched")


def test_a_huge_manifest_is_refused_without_being_read_whole(tmp_path, monkeypatch):
    """(e) 65 MiB of blanks deflate to a few dozen KiB: the manifest is the one entry no other entry bounds.

    Reading it past ``MANIFEST_MAX_BYTES + 1`` lets a small crafted archive make the check inflate whatever the zip
    header declares (gigabytes) into memory before refusing it.
    """
    crafted = tmp_path / "huge-manifest.zip"
    with zipfile.ZipFile(crafted, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(DATABASE_ENTRY, b"not even a database")
        with zf.open(MANIFEST_ENTRY, "w", force_zip64=True) as handle:
            for _ in range(MANIFEST_MAX_BYTES // (1024 * 1024) + 1):
                handle.write(b" " * (1024 * 1024))
    assert crafted.stat().st_size < 1024 * 1024, "precondition: the crafted archive is small"
    reads = record_reads(monkeypatch)
    with pytest.raises(ManifestError) as raised:
        check_archive(crafted)
    assert raised.value.code == "manifest_too_large", f"a manifest over 64 MiB is manifest_too_large, not {raised.value.code}"
    read = sum(size for name, size in reads if name == MANIFEST_ENTRY)
    assert read <= MANIFEST_MAX_BYTES + 1, f"the check inflated {read} bytes of manifest.json into memory; it must stop at MANIFEST_MAX_BYTES + 1 = {MANIFEST_MAX_BYTES + 1}: read_manifest reads info.file_size + 1, which the archive declares"
    print_success(f"refused after reading {read} bytes")


def test_check_and_build_agree_on_a_manifest_rebuilt_from_the_entries(tmp_path):
    """(e) A manifest is only as good as its entries: listing the real size and SHA-256 of a changed entry makes it check ok."""
    built = small_archive(tmp_path)
    changed = b"replaced content\n"
    files = [entry.model_copy(update={"size": len(changed), "sha256": sha256(changed)}) if entry.path == "custom-uploads/a.txt" else entry for entry in built.manifest.files]
    manifest = built.manifest.model_copy(update={"files": files})
    consistent = rewrite(built.path, tmp_path / "consistent.zip", swap={"custom-uploads/a.txt": changed, MANIFEST_ENTRY: manifest.to_bytes()})
    assert check_archive(consistent).ok, "an archive whose manifest lists the real size and SHA-256 of every entry checks ok"
    print_success("manifest and entries agree → ok")


# =============================================================================
# (f) a file that fails: before its entry starts, or once it has
# =============================================================================


ENTRY = "custom-uploads/a.txt"


def os_error(code: int) -> OSError:
    return OSError(code, os.strerror(code))


class FailingReads:
    """A file open for reading that gives its first block, then fails as a dying disk does (``EIO``)."""

    def __init__(self, handle):
        self._handle = handle
        self.reads = 0

    def read(self, size: int = -1) -> bytes:
        self.reads += 1
        if self.reads > 1:
            raise os_error(errno.EIO)
        return self._handle.read(size)

    def __getattr__(self, name: str):
        return getattr(self._handle, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        self._handle.close()
        return False


class OsReadingBadly:
    """``archive``'s ``os``, every call the real one, but the file opened from ``path`` reads badly (``FailingReads``)."""

    def __init__(self, path: Path):
        self._path = path
        self._fds: set[int] = set()

    def __getattr__(self, name: str):
        return getattr(os, name)

    def open(self, path, flags, *args, **kwargs) -> int:
        fd = os.open(path, flags, *args, **kwargs)
        if Path(path) == self._path:
            self._fds.add(fd)
        return fd

    def fdopen(self, fd: int, *args, **kwargs):
        handle = os.fdopen(fd, *args, **kwargs)
        if fd in self._fds:
            self._fds.discard(fd)
            return FailingReads(handle)
        return handle


class FailingEntryArchive:
    """Stands for the zip ``_add_file`` writes into: the entry fails at ``stage`` with ``error``. ``open``: the entry
    cannot start (its header cannot be written); ``write``: its first block cannot be written; ``close``: it cannot be
    finished (the last compressed bytes, the sizes)."""

    def __init__(self, stage: str, error: OSError):
        self.stage = stage
        self.error = error
        self.written = 0

    def open(self, info: zipfile.ZipInfo, mode: str = "r", *, force_zip64: bool = False) -> FailingEntry:
        assert mode == "w", f"_add_file must open its entry for writing, not {mode!r}"
        if self.stage == "open":
            raise self.error
        return FailingEntry(self)


class FailingEntry:
    def __init__(self, owner: FailingEntryArchive):
        self._owner = owner

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None and self._owner.stage == "close":
            raise self._owner.error
        return False

    def write(self, data: bytes) -> int:
        if self._owner.stage == "write":
            raise self._owner.error
        self._owner.written += len(data)
        return len(data)


@pytest.mark.parametrize("case", ["gone", pytest.param("link", marks=needs_symlinks), pytest.param("unreadable", marks=needs_permission_checks)])
def test_a_file_that_fails_before_its_entry_starts_is_an_oserror_and_adds_no_entry(tmp_path, case):
    """(f) Nothing of the file is in the archive yet: a plain ``OSError``, which ``build_archive`` turns into a skip."""
    print_section("_add_file: before and after the entry starts")
    path = tmp_path / "a.txt"
    if case == "link":
        write_files(tmp_path, {"secrets/instance.key": SECRET})
        path.symlink_to(tmp_path / "secrets" / "instance.key")
    elif case == "unreadable":
        path.write_bytes(b"uploaded file\n")
        path.chmod(0)
    counted: list[int] = []
    try:
        with zipfile.ZipFile(tmp_path / "archive.zip", "w") as zf:
            with pytest.raises(OSError) as raised:
                archive._add_file(zf, path, ENTRY, counted.append)
            names = zf.namelist()
    finally:
        if case == "unreadable":
            path.chmod(0o600)
    assert (names, counted) == ([], []), f"{case}: no entry was started and no byte counted: {names}, {counted}"
    print_success(f"{case}: {type(raised.value).__name__}, no entry")


#: Calls of ``_add_file`` on one refused path: a leak of one descriptor per call leaves that many open.
LEAK_CALLS = 16


def descriptors_on(path: Path) -> list[int]:
    """The descriptors of this process open on the file ``path`` names (same device and inode), from ``/dev/fd``.

    Found by what they are open on, not by their number: a descriptor another part of the process opens meanwhile
    cannot pass for a leaked one, nor hide one.
    """
    wanted = path.lstat()
    found: list[int] = []
    for name in os.listdir("/dev/fd"):
        try:
            info = os.fstat(int(name))
        except (OSError, ValueError):
            continue  # the descriptor that listed /dev/fd, closed since
        if (info.st_dev, info.st_ino) == (wanted.st_dev, wanted.st_ino):
            found.append(int(name))
    return sorted(found)


@needs_dev_fd
@pytest.mark.parametrize("replacement", ["folder", pytest.param("fifo", marks=needs_fifo)])
def test_a_file_refused_before_its_entry_starts_leaves_no_descriptor_open(tmp_path, replacement):
    """(f) Regression: a folder where a collected file was expected leaked the descriptor ``os.open`` gave, once per
    call: ``os.fdopen`` refuses a folder without closing a descriptor it is handed. The server keeps running after a
    backup, so every such entry of every backup kept one open for good. A refusal closes what it opened; a FIFO,
    refused by the same check, too."""
    path = tmp_path / "a.txt"
    if replacement == "folder":
        path.mkdir()
    else:
        os.mkfifo(path)
    assert descriptors_on(path) == [], f"precondition: no descriptor of this process is open on the {replacement}"
    with zipfile.ZipFile(tmp_path / "archive.zip", "w") as zf:
        for _ in range(LEAK_CALLS):
            with pytest.raises(OSError):
                archive._add_file(zf, path, ENTRY, lambda count: None)
        names = zf.namelist()
    left_open = descriptors_on(path)
    for fd in left_open:
        os.close(fd)  # a red run must not carry them into the tests that follow
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the {replacement} by {LEAK_CALLS} refused calls of _add_file: {left_open}"
    assert names == [], f"a refused file starts no entry: {names}"
    print_success(f"{replacement}: {LEAK_CALLS} refusals, no descriptor left open")


@pytest.mark.parametrize(
    ("stage", "code"),
    [
        pytest.param("open", errno.ENOSPC, id="open-ENOSPC"),
        pytest.param("write", errno.ENOSPC, id="write-ENOSPC"),
        pytest.param("close", errno.EIO, id="close-EIO"),
    ],
)
def test_an_entry_that_fails_once_started_raises_partial_entry_error_with_its_cause(tmp_path, stage, code):
    """(f) Opening, writing or closing the entry: part of it may be in the archive, which cannot take it back."""
    path = tmp_path / "a.txt"
    path.write_bytes(b"uploaded file\n" * 64)
    error = os_error(code)
    with pytest.raises(PartialEntryError) as raised:
        archive._add_file(FailingEntryArchive(stage, error), path, ENTRY, lambda count: None)
    assert raised.value.entry == ENTRY, f"{stage}: the error names the entry: {raised.value.entry!r}"
    assert str(raised.value) == f"{ENTRY} failed while it was being archived", f"{stage}: {raised.value}"
    assert raised.value.__cause__ is error, f"{stage}: the OSError is the cause, for the job to tell a full disk: {raised.value.__cause__!r}"
    print_success(f"{stage} → PartialEntryError from {errno.errorcode[code]}")


def test_a_file_that_fails_while_it_is_read_raises_partial_entry_error_with_its_cause(tmp_path, monkeypatch):
    """(f) A real zip, a real file: its first block is in the entry when the second read fails (``EIO``)."""
    path = tmp_path / "a.txt"
    path.write_bytes(bytes(range(256)) * 16)
    monkeypatch.setattr(archive, "_CHUNK", 1024)
    monkeypatch.setattr(archive, "os", OsReadingBadly(path))
    counted: list[int] = []
    with zipfile.ZipFile(tmp_path / "archive.zip", "w") as zf:
        with pytest.raises(PartialEntryError) as raised:
            archive._add_file(zf, path, ENTRY, counted.append)
    assert counted == [1024], f"precondition: the entry had started, its first block written, when the read failed: {counted}"
    cause = raised.value.__cause__
    assert raised.value.entry == ENTRY and isinstance(cause, OSError) and cause.errno == errno.EIO, f"PartialEntryError({ENTRY!r}) from the read's EIO: {raised.value!r} from {cause!r}"
    print_success("read error after the first block → PartialEntryError from EIO")


def test_a_file_that_fails_while_it_is_read_stops_the_build_instead_of_being_left_out(tmp_path, monkeypatch):
    """(f) The build must not leave out a file of which part is archived: it stops, and no archive reaches the target."""
    print_section("build_archive: a file that fails half-way")
    data = small_data_dir(tmp_path / "data")
    work = tmp_path / "work"
    work.mkdir()
    target = work / "librefolio-backup-test.zip"
    monkeypatch.setattr(archive, "_CHUNK", 64)
    monkeypatch.setattr(archive, "os", OsReadingBadly(data / ENTRY))
    with pytest.raises(PartialEntryError) as raised:
        build_archive(data, work, target, origin="cli")
    cause = raised.value.__cause__
    assert raised.value.entry == ENTRY and isinstance(cause, OSError) and cause.errno == errno.EIO, f"the build stops on {ENTRY}, its EIO as the cause: {raised.value!r} from {cause!r}"
    assert not target.exists(), "no archive under the final name"
    assert sorted(os.listdir(work)) == [target.name + ".part"], f"only the partial archive is left, for the caller to remove: {sorted(os.listdir(work))}"
    print_success("build stopped, no archive at the target")


@pytest.mark.parametrize("replacement", [pytest.param("fifo", marks=needs_fifo), pytest.param("unreadable", marks=needs_permission_checks)])
def test_a_file_that_fails_before_its_entry_starts_is_left_out_and_the_build_goes_on(tmp_path, monkeypatch, replacement):
    """(f) Collected as a file, then a FIFO in its place (never waited on) or unreadable: nothing of it is archived
    yet, so it is left out and reported, and the archive is consistent without it."""
    data = small_data_dir(tmp_path / "data")
    swapped = data / ENTRY
    real_collect = archive.collect_files

    def collect_then_swap(data_dir):
        collected = real_collect(data_dir)
        if replacement == "fifo":
            swapped.unlink()
            os.mkfifo(swapped)
        else:
            swapped.chmod(0)
        return collected

    monkeypatch.setattr(archive, "collect_files", collect_then_swap)
    outcome: dict[str, object] = {}

    def build() -> None:
        try:
            outcome["built"] = build_into(data, tmp_path / "work")
        except Exception as exc:  # reported below, in the test's thread
            outcome["error"] = exc

    worker = threading.Thread(target=build, name="swapped-file-build", daemon=True)
    worker.start()
    worker.join(DEADLINE_S)
    hung = worker.is_alive()
    if hung and replacement == "fifo":
        os.close(os.open(swapped, os.O_WRONLY | os.O_NONBLOCK))  # a writer appears and leaves: the blocked read ends
        worker.join(DEADLINE_S)
    if replacement == "unreadable":
        swapped.chmod(0o600)
    assert not hung, f"the build was still running after {DEADLINE_S}s: it waited on the {replacement}"
    assert "error" not in outcome, f"a file that fails before its entry starts must not stop the build: {outcome.get('error')!r}"
    built = outcome["built"]
    assert (built.skipped, built.warnings) == ((ENTRY,), ("files_skipped",)), f"{replacement}: left out and reported: {built.skipped}, {built.warnings}"
    assert ENTRY not in entry_names(built.path) and check_archive(built.path).ok, f"{replacement}: not in the archive, which checks ok without it"
    print_success(f"{replacement} in place of a file → left out, build done")


# =============================================================================
# (g) The ledger's control totals in the manifest (lot B-13)
# =============================================================================


TOTALS_MODULE = "backend.app.services.platform.instance_backup.totals"
READ_ERROR = "The ledger's control totals could not be read"
#: The ledger of the cases of (g): the eight columns J reads of ``transactions``, declared as the app declares them.
LEDGER_TABLE = "CREATE TABLE transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, broker_id INTEGER NOT NULL, asset_id INTEGER, type VARCHAR(32) NOT NULL, date DATE NOT NULL, quantity NUMERIC(18, 6) NOT NULL DEFAULT 0, amount NUMERIC(18, 6) NOT NULL DEFAULT 0, currency VARCHAR(3))"
#: (broker id, asset id, type, date, quantity, amount, currency): cash of two brokers in two currencies, two positions,
#: one of them without cash.
LEDGER_ROWS = (
    (1, None, "DEPOSIT", "2026-01-02", "0", "100", "EUR"),
    (1, 1, "BUY", "2026-01-05", "2", "-30.5", "EUR"),
    (2, None, "DEPOSIT", "2026-01-03", "0", "7", "USD"),
    (2, 1, "ADJUSTMENT", "2026-01-04", "0.5", "0", None),
)
#: J's totals of ``LEDGER_ROWS``, as its ``to_json`` writes them.
LEDGER_TOTALS = {
    "version": 1,
    "cash": [{"broker_id": 1, "currency": "EUR", "balance": "69.5"}, {"broker_id": 2, "currency": "USD", "balance": "7"}],
    "quantities": [{"broker_id": 1, "asset_id": 1, "quantity": "2"}, {"broker_id": 2, "asset_id": 1, "quantity": "0.5"}],
}


def totals_module() -> ModuleType:
    """``instance_backup.totals`` (lot B-13). Imported when a test needs it, never at collection: until it exists, each
    test that needs it fails on its own, with this message."""
    try:
        return importlib.import_module(TOTALS_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != TOTALS_MODULE:
            raise
        pytest.fail(f"{TOTALS_MODULE} does not exist: lot B-13 is not written yet ({exc})")


def recorded_totals(manifest: BackupManifest) -> object:
    """What the manifest records of the ledger's totals (lot B-13)."""
    assert "control_totals" in ManifestDatabase.model_fields, "ManifestDatabase has no control_totals: lot B-13 is not written yet"
    return manifest.database.control_totals


def ledger_data_dir(root: Path) -> Path:
    """``small_data_dir``, its database holding the ledger ``LEDGER_ROWS``."""
    data = small_data_dir(root)
    with closing(sqlite3.connect(data / DATABASE_ENTRY)) as conn, conn:
        conn.execute(LEDGER_TABLE)
        conn.executemany("INSERT INTO transactions (broker_id, asset_id, type, date, quantity, amount, currency) VALUES (?, ?, ?, ?, ?, ?, ?)", LEDGER_ROWS)
    return data


def replace_ledger_totals(monkeypatch, replacement) -> None:
    """``ledger_totals_of`` replaced wherever a build may read it: the totals module's own, and the name ``archive``
    imported (set even if it has none: the module's is then the one it reads)."""
    monkeypatch.setattr(totals_module(), "ledger_totals_of", replacement)
    monkeypatch.setattr(archive, "ledger_totals_of", replacement, raising=False)


def test_the_ledger_of_these_cases_sums_as_j_says():
    """(g) The precondition of the cases: ``LEDGER_TOTALS`` is J's ``control_totals`` of ``LEDGER_ROWS``."""
    rows = [SimpleNamespace(id=row_id, type=kind, date=date.fromisoformat(day), broker_id=broker_id, asset_id=asset_id, currency=currency, amount=Decimal(amount), quantity=Decimal(quantity)) for row_id, (broker_id, asset_id, kind, day, quantity, amount, currency) in enumerate(LEDGER_ROWS, start=1)]
    assert control_totals(rows).to_json() == LEDGER_TOTALS, f"J sums the ledger of these cases otherwise: {control_totals(rows).to_json()}"


def test_the_manifest_records_the_ledger_totals_of_the_snapshot(tmp_path, monkeypatch):
    """(g) Read once, on the snapshot (the very bytes the archive then carries as its database, never the live file), in
    the phase ``database``, before the zip is opened; the manifest holds J's JSON as it is, equal to ``ledger_totals_of``
    of the archived database; the format is still version 1."""
    print_section("The ledger's control totals in the manifest")
    real = totals_module().ledger_totals_of
    data = ledger_data_dir(tmp_path / "data")
    work = tmp_path / "work"
    progress: list[tuple[str, int, int]] = []
    calls: list[tuple[Path, str, list[str], tuple[str, int, int] | None]] = []

    def recording(database: Path):
        path = Path(database)
        calls.append((path.resolve(), sha256(path.read_bytes()), sorted(part.name for part in work.glob("*.part")), progress[-1] if progress else None))
        return real(database)

    replace_ledger_totals(monkeypatch, recording)
    built = build_into(data, work, progress=lambda phase, done, total: progress.append((phase, done, total)))
    manifest = built.manifest
    assert len(calls) == 1, f"read once: {calls}"
    path, read_sha256, parts, phase = calls[0]
    assert path != (data / DATABASE_ENTRY).resolve(), "read on the snapshot, never on the live database"
    assert read_sha256 == manifest.files[0].sha256, "the file read holds the bytes the archive carries as its database: the snapshot"
    assert (parts, phase) == ([], ("database", 0, 0)), f"in the phase database, before the zip is opened: {parts}, {phase}"
    extracted = tmp_path / "extracted" / "app.db"
    extracted.parent.mkdir()
    with zipfile.ZipFile(built.path) as zf:
        document = json.loads(zf.read(MANIFEST_ENTRY))
        extracted.write_bytes(zf.read(DATABASE_ENTRY))
    assert recorded_totals(manifest) == real(extracted) == LEDGER_TOTALS, f"the manifest records J's totals of the archived database: {recorded_totals(manifest)}"
    assert document["database"]["control_totals"] == LEDGER_TOTALS, f"written into manifest.json as they are: {document['database']}"
    assert document["format_version"] == FORMAT_VERSION == 1, f"the format stays version 1: {document['format_version']}"
    assert (built.warnings, built.skipped) == ((), ()), f"nothing to warn: {built.warnings}"
    print_success(f"control_totals: {len(LEDGER_TOTALS['cash'])} cash lines, {len(LEDGER_TOTALS['quantities'])} positions")


@pytest.mark.parametrize("case", ["read-as-none", "no-ledger-table"])
def test_totals_that_cannot_be_read_leave_the_field_null_and_the_backup_goes_on(tmp_path, monkeypatch, case):
    """(g) ``ledger_totals_of`` answers ``None`` (it has logged why): the field is ``null``, the backup done and intact,
    no new warning. For real: B1's small database has no ledger table, and one error says so."""
    if case == "read-as-none":
        data = ledger_data_dir(tmp_path / "data")
        asked: list[Path] = []
        replace_ledger_totals(monkeypatch, lambda database: asked.append(database))
    else:
        totals_module()
        data = small_data_dir(tmp_path / "data")
    with capture_logs() as events:
        built = build_into(data, tmp_path / "work")
    assert recorded_totals(built.manifest) is None, f"{case}: no totals: {recorded_totals(built.manifest)}"
    with zipfile.ZipFile(built.path) as zf:
        database = json.loads(zf.read(MANIFEST_ENTRY))["database"]
    assert "control_totals" in database and database["control_totals"] is None, f"{case}: the field is there, null: {database}"
    assert (built.warnings, built.skipped) == ((), ()), f"{case}: no new warning: {built.warnings}"
    assert check_archive(built.path).ok, f"{case}: the backup is done and intact"
    errors = [event for event in events if event.get("log_level") == "error"]
    if case == "read-as-none":
        assert (len(asked), errors) == (1, []), f"asked once; the build itself logs no error: {asked}, {errors}"
    else:
        assert [event.get("event") for event in errors] == [READ_ERROR], f"one error, the totals': {errors}"
    print_success(f"{case}: control_totals null, backup done")


def test_a_manifest_without_the_totals_reads_them_as_none():
    """(g) An archive made before lot B-13: the same format, version 1, without the field."""
    document = manifest_document()
    assert "control_totals" not in document["database"], "precondition: a manifest of before lot B-13"
    read = BackupManifest.from_bytes(encoded(document))
    assert recorded_totals(read) is None, f"no totals: {recorded_totals(read)}"
    assert read.format_version == FORMAT_VERSION == 1, f"version 1: {read.format_version}"


#: What the field may hold, kept as it is: B reads, stores and compares J's JSON, never reshapes it at reading.
KEPT_TOTALS = [
    pytest.param(LEDGER_TOTALS, id="version-1"),
    pytest.param({"version": 99, "method": "another one", "lines": [[1, "EUR", 2.5]]}, id="another-version-another-shape"),
    pytest.param({"version": 1, "cash": [{"broker_id": 1, "currency": "EUR", "balance": "1E+3"}], "quantities": []}, id="an-amount-not-plain-text"),
    pytest.param({}, id="an-empty-object"),
    pytest.param(None, id="null"),
    pytest.param([LEDGER_TOTALS], id="a-list"),
    pytest.param("totals", id="a-string"),
    pytest.param(42, id="a-number"),
    pytest.param(True, id="true"),
]


@pytest.mark.parametrize("recorded", KEPT_TOTALS)
def test_a_manifest_keeps_the_totals_as_they_were_written(recorded):
    """(g) §7.2, ``control_totals: Any = None``: any JSON value is read and written back as it is, never refused and never
    read into amounts here; a document of another version or of another shape, or a value of another type, keeps the
    archive readable (the check then says ``other_version`` or ``absent``)."""
    database = {**manifest_document()["database"], "control_totals": recorded}
    read = BackupManifest.from_bytes(encoded(manifest_document(database=database)))
    assert recorded_totals(read) == recorded, f"read as written: {recorded_totals(read)!r}"
    assert json.loads(read.to_bytes())["database"]["control_totals"] == recorded, "written back as read"
    assert BackupManifest.from_bytes(read.to_bytes()) == read, "and read back equal"
