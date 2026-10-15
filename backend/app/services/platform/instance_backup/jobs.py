"""Background backups for the API, and the same run in the foreground for the CLI: one at a time, state on disk.

A job runs in a thread of the worker that received the request; the next requests may reach any worker, so its state
lives in a file, ``backups/.jobs/<id>/state.json``, written atomically. One backup runs at a time: the run holds an
exclusive ``flock`` on ``backups/.jobs/.lock`` from its start to its end, and a second start finds it taken and is
refused. The lock is what says "running": a state that still says running while nobody holds the lock belongs to a run
that died with its process (a restart, a crash), and reads as interrupted. The final state is written before the lock is
released, so a finished run never reads as interrupted. A finished job keeps its archive for an hour: after that a read
of the job answers that there is none and removes it, and the next start removes every such job.

Without ``fcntl`` (not POSIX) the lock only serialises the runs of one process.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

try:
    import fcntl
except ImportError:  # pragma: no cover - not POSIX: runs are serialised per process only
    fcntl = None  # type: ignore[assignment]

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup.archive import BackupNoSpaceError, Phase, build_archive
from backend.app.services.platform.instance_backup.manifest import BackupOrigin
from backend.app.services.platform.instance_backup.paths import STATE_FILE, ensure_private_dir, is_job_id, job_dir, jobs_dir, lock_path

logger = get_logger(__name__)

#: How long a finished job keeps its archive and its state.
JOB_RETENTION = timedelta(hours=1)
#: How often a running job writes its progress.
_PROGRESS_INTERVAL_S = 0.5
#: How many left-out entries a job's state lists.
_SKIPPED_KEPT = 50
_PROCESS_LOCKS: dict[Path, threading.Lock] = {}

JobStatus = Literal["running", "done", "failed"]
#: Why a job failed, as a stable code: no space, an error during the build, or its process died while it ran.
JobError = Literal["backup_no_space", "backup_failed", "backup_interrupted"]


class BackupBusyError(RuntimeError):
    """Another backup is running on this data directory."""


class BackupJobNotFoundError(LookupError):
    """No job has this id, or its files are gone."""


class BackupJobStateError(RuntimeError):
    """The job cannot do this in its state: its archive is not ready, or it is still running."""

    def __init__(self, status: JobStatus):
        super().__init__(f"The backup job is {status}")
        self.status = status


@dataclass(frozen=True)
class BackupJob:
    """The state of one backup run."""

    job_id: str
    origin: BackupOrigin
    status: JobStatus
    phase: Phase | None
    done_bytes: int
    total_bytes: int
    created_at: datetime
    finished_at: datetime | None = None
    file_name: str | None = None
    file_size: int | None = None
    file_sha256: str | None = None
    warnings: tuple[str, ...] = ()
    #: The entries the build left out (links, special files, files that vanished or could not be read), at most 50.
    skipped: tuple[str, ...] = ()
    error_code: JobError | None = None

    def to_json(self) -> str:
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["finished_at"] = self.finished_at.isoformat() if self.finished_at else None
        data["warnings"] = list(self.warnings)
        data["skipped"] = list(self.skipped)
        return json.dumps(data, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> BackupJob:
        known = {item.name for item in fields(cls)}
        data = {key: value for key, value in json.loads(text).items() if key in known}
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["finished_at"] = datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None
        data["warnings"] = tuple(data.get("warnings") or ())
        data["skipped"] = tuple(data.get("skipped") or ())
        return cls(**data)


def archive_name(created_at: datetime) -> str:
    """The file name of an archive made at ``created_at``: ``librefolio-backup-YYYYMMDD-HHMMSS.zip``, in UTC."""
    return f"librefolio-backup-{created_at.astimezone(UTC):%Y%m%d-%H%M%S}.zip"


class _RunLock:
    """The exclusive lock of the backup runs of one data directory."""

    def __init__(self, path: Path):
        self._path = path
        self._fd: int | None = None
        self._local: threading.Lock | None = None

    def try_acquire(self) -> bool:
        if fcntl is None:
            local = _PROCESS_LOCKS.setdefault(self._path, threading.Lock())
            if not local.acquire(blocking=False):
                return False
            self._local = local
            return True
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._local is not None:
            self._local.release()
            self._local = None
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)
            self._fd = None


def _now() -> datetime:
    return datetime.now(UTC)


def _write_state(folder: Path, job: BackupJob) -> None:
    """Write the state of a job atomically: a reader sees the old state or the new one, never half of one."""
    partial = folder / (STATE_FILE + ".part")
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(job.to_json())
    os.replace(partial, folder / STATE_FILE)


def _read_state(folder: Path) -> BackupJob:
    try:
        return BackupJob.from_json((folder / STATE_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, NotADirectoryError):
        raise BackupJobNotFoundError("No such backup job") from None


def _prepare(data_dir: Path, origin: BackupOrigin) -> tuple[_RunLock, BackupJob]:
    """Take the run lock and create the job's folder and first state. ``BackupBusyError`` when a run holds the lock."""
    ensure_private_dir(jobs_dir(data_dir), data_dir)
    remove_expired_jobs(data_dir)
    lock = _RunLock(lock_path(data_dir))
    if not lock.try_acquire():
        raise BackupBusyError("Another backup is running")
    try:
        job_id = secrets.token_hex(16)
        folder = ensure_private_dir(job_dir(data_dir, job_id), data_dir)
        job = BackupJob(job_id=job_id, origin=origin, status="running", phase="preparing", done_bytes=0, total_bytes=0, created_at=_now())
        _write_state(folder, job)
    except BaseException:
        lock.release()
        raise
    return lock, job


def _run(data_dir: Path, job: BackupJob, lock: _RunLock, progress: Callable[[Phase, int, int], None] | None = None) -> BackupJob:
    """Build the archive of a prepared job, keep its state up to date, and release the lock once the end is recorded."""
    folder = job_dir(data_dir, job.job_id)
    name = archive_name(job.created_at)
    current = job
    last_write = 0.0

    def on_progress(phase: Phase, done: int, total: int) -> None:
        nonlocal current, last_write
        current = replace(current, phase=phase, done_bytes=done, total_bytes=total)
        if progress is not None:
            progress(phase, done, total)
        now = time.monotonic()
        if now - last_write >= _PROGRESS_INTERVAL_S:
            last_write = now
            _write_state(folder, current)

    started = time.monotonic()
    try:
        built = build_archive(data_dir, folder, folder / name, origin=job.origin, progress=on_progress)
    except BackupNoSpaceError as exc:
        current = replace(current, status="failed", phase=None, finished_at=_now(), error_code="backup_no_space")
        logger.warning("Instance backup refused: not enough free space", job_id=job.job_id, needed_bytes=exc.needed, free_bytes=exc.free)
    except Exception as exc:  # noqa: BLE001 — any failure ends the job as failed, with the cause in the log
        current = replace(current, status="failed", phase=None, finished_at=_now(), error_code="backup_failed")
        logger.error("Instance backup failed", job_id=job.job_id, error=f"{type(exc).__name__}: {exc}")
    else:
        current = replace(
            current,
            status="done",
            phase=None,
            done_bytes=current.total_bytes,
            finished_at=_now(),
            file_name=name,
            file_size=built.size,
            file_sha256=built.sha256,
            warnings=built.warnings,
            skipped=built.skipped[:_SKIPPED_KEPT],
        )
        logger.info(
            "Instance backup written",
            job_id=job.job_id,
            origin=job.origin,
            size_bytes=built.size,
            files=len(built.manifest.files),
            alembic_revision=built.manifest.alembic_revision,
            seconds=round(time.monotonic() - started, 1),
            warnings=list(built.warnings),
            skipped=list(built.skipped[:_SKIPPED_KEPT]),
        )
    finally:
        try:
            _remove_work_files(folder, keep=current.file_name)
            _write_state(folder, current)
        finally:
            lock.release()
    return current


def _remove_work_files(folder: Path, keep: str | None) -> None:
    """Remove what a run leaves in its folder (the database copy, a partial archive) but its state and its archive."""
    for path in folder.iterdir():
        if path.name in (STATE_FILE, keep):
            continue
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)


def start_backup(*, origin: BackupOrigin = "ui", data_dir: Path | None = None) -> BackupJob:
    """Start a backup in a background thread and return its first state. ``BackupBusyError`` if one is running."""
    data_dir = data_dir or get_data_dir()
    lock, job = _prepare(data_dir, origin)
    try:
        thread = threading.Thread(target=_run, args=(data_dir, job, lock), name=f"backup-{job.job_id[:8]}", daemon=True)
        thread.start()
    except BaseException:
        lock.release()
        raise
    return job


def run_backup(*, origin: BackupOrigin = "cli", data_dir: Path | None = None, progress: Callable[[Phase, int, int], None] | None = None) -> tuple[BackupJob, Path]:
    """Run a backup in this thread, holding the same lock as the API's jobs: the job's end state and its folder."""
    data_dir = data_dir or get_data_dir()
    lock, job = _prepare(data_dir, origin)
    return _run(data_dir, job, lock, progress), job_dir(data_dir, job.job_id)


def get_job(job_id: str, *, data_dir: Path | None = None) -> BackupJob:
    """The state of a job; a run that died with its process reads as failed, ``backup_interrupted``."""
    data_dir = data_dir or get_data_dir()
    if not is_job_id(job_id):
        raise BackupJobNotFoundError("No such backup job")
    folder = job_dir(data_dir, job_id)
    job = _read_state(folder)
    if job.finished_at is not None and _now() - job.finished_at > JOB_RETENTION:
        shutil.rmtree(folder, ignore_errors=True)
        raise BackupJobNotFoundError("The backup job has expired")
    if job.status == "running" and not _run_lock_held(data_dir):
        job = _read_state(folder)
        if job.status == "running":
            job = replace(job, status="failed", phase=None, finished_at=_now(), error_code="backup_interrupted")
            _write_state(folder, job)
    return job


def job_archive(job_id: str, *, data_dir: Path | None = None) -> tuple[Path, str]:
    """The archive of a finished job and its file name. ``BackupJobStateError`` until it is done."""
    data_dir = data_dir or get_data_dir()
    job = get_job(job_id, data_dir=data_dir)
    if job.status != "done" or job.file_name is None:
        raise BackupJobStateError(job.status)
    path = job_dir(data_dir, job_id) / job.file_name
    if not path.is_file():
        raise BackupJobNotFoundError("The backup archive is gone")
    return path, job.file_name


def delete_job(job_id: str, *, data_dir: Path | None = None) -> None:
    """Remove a finished job and its archive. ``BackupJobStateError`` while it runs."""
    data_dir = data_dir or get_data_dir()
    job = get_job(job_id, data_dir=data_dir)
    if job.status == "running":
        raise BackupJobStateError(job.status)
    shutil.rmtree(job_dir(data_dir, job_id), ignore_errors=True)


def remove_expired_jobs(data_dir: Path, *, now: datetime | None = None) -> int:
    """Remove the jobs that finished more than ``JOB_RETENTION`` ago, or died that long ago; how many were removed."""
    folder = jobs_dir(data_dir)
    if not folder.is_dir():
        return 0
    now = now or _now()
    removed = 0
    for path in folder.iterdir():
        if not is_job_id(path.name) or path.is_symlink() or not path.is_dir():
            continue
        try:
            job = _read_state(path)
            ended = job.finished_at or (job.created_at if not _run_lock_held(data_dir) else None)
        except (BackupJobNotFoundError, ValueError, TypeError, KeyError):
            ended = datetime.fromtimestamp(path.stat().st_mtime, UTC)
        if ended is not None and now - ended > JOB_RETENTION:
            shutil.rmtree(path, ignore_errors=True)
            removed += 1
    return removed


def _run_lock_held(data_dir: Path) -> bool:
    """Whether a run holds the lock now (a probe: taken and released at once when free)."""
    if fcntl is not None and not lock_path(data_dir).exists():
        return False
    probe = _RunLock(lock_path(data_dir))
    if probe.try_acquire():
        probe.release()
        return False
    return True
