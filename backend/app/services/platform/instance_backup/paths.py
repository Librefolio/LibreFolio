"""The layout the instance backup reads and writes, inside the data directory.

An archive carries the database and the folders below, each whole, under the same relative paths they have in the data
directory: unpacked into an empty data directory it is an instance again. Everything else stays out: the logs, the
scheduler state, the secrets (the instance key travels only inside a password-protected archive, lot B4), the backups
themselves and the files the database writes beside itself (``-wal``, ``-shm``, locks, the copies of the post-migration
fixes).

Backups are written under ``backups/``, the instance's own folder for them, which is never archived. The background
jobs of the API keep their state and their work files in ``backups/.jobs/<job id>/``. A restore unpacks and checks an
archive in ``.restore/stage/<stage id>/``, never archived either. A confirmed restore waits there too
(``.restore/restore.json``) for the next start, which swaps the folders of ``SWAPPED_FOLDERS`` with the copy's. The page
that asked the restart reads the outcome with a one-time ticket, whose hash waits in ``.restore/outcome-ticket.json``
(lot B5c).
"""

from __future__ import annotations

import errno
import os
import re
import stat
from pathlib import Path

#: The database entry of an archive: a consistent copy (``VACUUM INTO``), never the live file.
DATABASE_ENTRY = "sqlite/app.db"
#: The folders an archive carries whole, as they are in the data directory.
ARCHIVED_FOLDERS = ("custom-uploads", "broker_reports", "scenario_catalog")
#: The description of the archive, its last entry.
MANIFEST_ENTRY = "manifest.json"
#: The instance key inside a password-protected archive only (decision 39, lot B4): never among the manifest's files,
#: never unpacked into a data directory, only read to re-encrypt the restored secrets.
INSTANCE_KEY_ENTRY = "secrets/instance.key"

BACKUPS_FOLDER = "backups"
JOBS_FOLDER = ".jobs"
LOCK_FILE = ".lock"
STATE_FILE = "state.json"

#: The restore's own folder in the data directory, never archived: the copies being checked (``stage/``) and, with lot
#: B3, the restore waiting for the next start.
RESTORE_FOLDER = ".restore"
STAGE_FOLDER = "stage"
#: Inside one stage: the data directory as the archive rebuilds it, and the report of the check.
STAGE_DATA_FOLDER = "data"
STAGE_REPORT_FILE = "report.json"
#: Inside one stage, while it is checked: a password-protected archive decrypted (lot B4), removed once unpacked.
STAGE_DECRYPTED_ARCHIVE = "archive.zip"
#: The lock that lets one archive be checked at a time.
STAGE_LOCK_FILE = ".stage.lock"
#: Inside ``.restore``: the archives uploaded for a check (lot B2b), and the state of each check.
UPLOAD_FOLDER = "upload"
CHECKS_FOLDER = "checks"
#: Inside ``.restore`` (lot B3): the state of the restore confirmed for the next start, the lock its startup steps take
#: turns on, the live folders it replaced (kept until its first start completes) and the restored ones a rollback sets
#: aside.
RESTORE_STATE_FILE = "restore.json"
APPLY_LOCK_FILE = "apply.lock"
#: Inside ``.restore`` (lot B5c): the hash of the one-time ticket with which the page that asked a restart reads the
#: restore's outcome, without a session.
OUTCOME_TICKET_FILE = "outcome-ticket.json"
PREVIOUS_FOLDER = "previous"
FAILED_FOLDER = "failed"
#: The live folders a restore replaces, in this order: the database's, then those an archive carries.
SWAPPED_FOLDERS = ("sqlite", *ARCHIVED_FOLDERS)

_JOB_ID = re.compile(r"[0-9a-f]{32}")


class BackupPathError(RuntimeError):
    """A folder the backup writes to is not a plain folder: a link, or a file, stands where it should be (``path``)."""

    def __init__(self, path: Path):
        super().__init__(f"{path} is not a plain folder")
        self.path = path


def database_path(data_dir: Path) -> Path:
    """The live database of the data directory."""
    return data_dir / DATABASE_ENTRY


def backups_dir(data_dir: Path) -> Path:
    """Where backups are written: ``<data dir>/backups``."""
    return data_dir / BACKUPS_FOLDER


def jobs_dir(data_dir: Path) -> Path:
    """Where the background jobs keep their state and work files: ``<data dir>/backups/.jobs``."""
    return backups_dir(data_dir) / JOBS_FOLDER


def lock_path(data_dir: Path) -> Path:
    """The lock that lets one backup run at a time, across processes and workers."""
    return jobs_dir(data_dir) / LOCK_FILE


def is_job_id(value: str) -> bool:
    """Whether ``value`` is a job id as the jobs make them: 32 lowercase hexadecimal digits, nothing else."""
    return bool(_JOB_ID.fullmatch(value))


def job_dir(data_dir: Path, job_id: str) -> Path:
    """The folder of one job. ``ValueError`` for anything that is not a job id: never a path built from user input."""
    if not is_job_id(job_id):
        raise ValueError("not a backup job id")
    return jobs_dir(data_dir) / job_id


def restore_dir(data_dir: Path) -> Path:
    """The restore's own folder: ``<data dir>/.restore``."""
    return data_dir / RESTORE_FOLDER


def stages_dir(data_dir: Path) -> Path:
    """Where archives are unpacked and checked before a restore: ``<data dir>/.restore/stage``."""
    return restore_dir(data_dir) / STAGE_FOLDER


def stage_dir(data_dir: Path, stage_id: str) -> Path:
    """The folder of one checked archive. ``ValueError`` for anything that is not an id the stages make (as a job id)."""
    if not is_job_id(stage_id):
        raise ValueError("not a restore stage id")
    return stages_dir(data_dir) / stage_id


def uploads_dir(data_dir: Path) -> Path:
    """Where archives uploaded for a check are received: ``<data dir>/.restore/upload``."""
    return restore_dir(data_dir) / UPLOAD_FOLDER


def upload_path(data_dir: Path, upload_id: str) -> Path:
    """One uploaded archive. ``ValueError`` for anything that is not an id the uploads make (as a job id)."""
    if not is_job_id(upload_id):
        raise ValueError("not an upload id")
    return uploads_dir(data_dir) / upload_id


def checks_dir(data_dir: Path) -> Path:
    """Where the state of each check is kept: ``<data dir>/.restore/checks``."""
    return restore_dir(data_dir) / CHECKS_FOLDER


def check_state_path(data_dir: Path, stage_id: str) -> Path:
    """The state file of one check. ``ValueError`` for anything that is not a stage id."""
    if not is_job_id(stage_id):
        raise ValueError("not a restore stage id")
    return checks_dir(data_dir) / f"{stage_id}.json"


def stage_data_dir(data_dir: Path, stage_id: str) -> Path:
    """The data directory a checked archive rebuilds, inside its stage. ``ValueError`` for anything that is not a stage
    id."""
    return stage_dir(data_dir, stage_id) / STAGE_DATA_FOLDER


def restore_state_path(data_dir: Path) -> Path:
    """The state of the restore confirmed for the next start: ``<data dir>/.restore/restore.json``."""
    return restore_dir(data_dir) / RESTORE_STATE_FILE


def apply_lock_path(data_dir: Path) -> Path:
    """The lock the startup steps of a restore take turns on, across the workers of a server."""
    return restore_dir(data_dir) / APPLY_LOCK_FILE


def outcome_ticket_path(data_dir: Path) -> Path:
    """The one-time ticket of the outcome of a restore (its hash): ``<data dir>/.restore/outcome-ticket.json``."""
    return restore_dir(data_dir) / OUTCOME_TICKET_FILE


def previous_dir(data_dir: Path) -> Path:
    """Where a restore keeps the live folders it replaced, until its first start completes: ``.restore/previous``."""
    return restore_dir(data_dir) / PREVIOUS_FOLDER


def failed_dir(data_dir: Path) -> Path:
    """Where a rollback sets the restored folders aside, until the start removes them: ``.restore/failed``."""
    return restore_dir(data_dir) / FAILED_FOLDER


def is_plain_dir(path: Path) -> bool:
    """Whether ``path`` is a folder itself: not a link to one, nor anything else."""
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except FileNotFoundError:
        return False


def ensure_private_dir(path: Path, data_dir: Path) -> Path:
    """Create ``path`` and its missing parents below ``data_dir`` as plain folders, readable only by their owner.

    A link, or anything else than a folder, where one is expected is refused rather than followed: a backup holds the
    whole database, and writing it through a link could put it anywhere.
    """
    current = data_dir
    for part in path.relative_to(data_dir).parts:
        current = current / part
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        if not stat.S_ISDIR(current.lstat().st_mode):
            raise BackupPathError(current)
    return path


class NotRegularFileError(OSError):
    """Something else than a regular file where one is read: a link (never followed), a FIFO, a device (B-53)."""


def read_regular_file(path: Path, *, limit: int | None = None) -> bytes:
    """The content of the regular file at ``path``, its first ``limit`` bytes when given (B-53).

    Opened without following a link and without waiting on a FIFO, its descriptor closed whatever happens: ``os.fdopen``
    keeps a descriptor it refuses, so a folder read that way left one open at each read. ``FileNotFoundError`` when
    nothing is there, ``NotADirectoryError`` when a folder on the way is a file, ``IsADirectoryError`` for a folder,
    ``NotRegularFileError`` for a link or a special file, ``PermissionError`` when it may not be read; any other
    ``OSError``, a transient one, as the system raised it.
    """
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise NotRegularFileError(exc.errno, exc.strerror, exc.filename) from None
        raise
    try:
        mode = os.fstat(fd).st_mode
        if stat.S_ISDIR(mode):
            raise IsADirectoryError(errno.EISDIR, os.strerror(errno.EISDIR), str(path))
        if not stat.S_ISREG(mode):
            raise NotRegularFileError(errno.EINVAL, "Not a regular file", str(path))
        handle = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)  # until the file object owns it, the descriptor is closed here
        raise
    with handle:
        return handle.read() if limit is None else handle.read(limit)
