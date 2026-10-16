"""The layout the instance backup reads and writes, inside the data directory.

An archive carries the database and the folders below, each whole, under the same relative paths they have in the data
directory: unpacked into an empty data directory it is an instance again. Everything else stays out: the logs, the
scheduler state, the secrets (the instance key travels only inside a password-protected archive, lot B4), the backups
themselves and the files the database writes beside itself (``-wal``, ``-shm``, locks, the copies of the post-migration
fixes).

Backups are written under ``backups/``, the instance's own folder for them, which is never archived. The background
jobs of the API keep their state and their work files in ``backups/.jobs/<job id>/``. A restore unpacks and checks an
archive in ``.restore/stage/<stage id>/``, never archived either.
"""

from __future__ import annotations

import re
import stat
from pathlib import Path

#: The database entry of an archive: a consistent copy (``VACUUM INTO``), never the live file.
DATABASE_ENTRY = "sqlite/app.db"
#: The folders an archive carries whole, as they are in the data directory.
ARCHIVED_FOLDERS = ("custom-uploads", "broker_reports", "scenario_catalog")
#: The description of the archive, its last entry.
MANIFEST_ENTRY = "manifest.json"

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
#: The lock that lets one archive be checked at a time.
STAGE_LOCK_FILE = ".stage.lock"
#: Inside ``.restore``: the archives uploaded for a check (lot B2b), and the state of each check.
UPLOAD_FOLDER = "upload"
CHECKS_FOLDER = "checks"

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
