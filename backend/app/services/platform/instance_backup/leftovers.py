"""What a run killed outright leaves in clear, removed at every start (lot B4b, B-23; decision N66).

A run killed outright (a power cut, ``kill -9``, a container stopped past its grace period) cannot clean up behind
itself, and three runs of the backup leave clear data on disk while they work:

- the check of a secure backup decrypts it into its copy (``.restore/stage/<id>/archive.zip``) until it is unpacked;
- ``dev.py backup inspect`` decrypts one into a folder ``backups/.decrypt-<random>/``;
- a backup writes the database's copy and the clear zip into its job folder (``backups/.jobs/<id>/``): a secure one
  keeps them there until it is encrypted.

``sweep_backup_leftovers`` removes them at every start (the step ``backup-leftovers``, right after ``restore-commit``),
each under its own rule: nothing a running process holds (the run lock of the backups, the lock of the checks, an
``inspect`` younger than an hour), nothing through a link. It never raises: after ``restore-commit`` a step that raises
would stop every start of the server.
"""

from __future__ import annotations

import shutil
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup import jobs, restore_jobs
from backend.app.services.platform.instance_backup.paths import backups_dir, is_plain_dir

logger = get_logger(__name__)

#: The folders ``dev.py backup inspect`` decrypts a secure backup into, in ``backups/``.
DECRYPT_FOLDER_PREFIX = ".decrypt-"
#: How old such a folder must be before anyone removes it: a younger one may be another ``inspect``'s, still running.
DECRYPT_FOLDER_LIFETIME = timedelta(hours=1)


def remove_stale_decrypt_folders(backups: Path, *, now: datetime | None = None) -> int:
    """Remove the ``.decrypt-*`` folders of ``backups`` older than ``DECRYPT_FOLDER_LIFETIME``, with what they hold; how
    many. A younger one may be another run's; a link or a file of that name is never followed nor removed."""
    if not is_plain_dir(backups):
        return 0
    cutoff = (now or datetime.now(UTC)).timestamp() - DECRYPT_FOLDER_LIFETIME.total_seconds()
    removed = 0
    for entry in backups.glob(f"{DECRYPT_FOLDER_PREFIX}*"):
        try:
            info = entry.lstat()
        except OSError:
            continue
        if stat.S_ISDIR(info.st_mode) and info.st_mtime < cutoff:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
    return removed


def sweep_backup_leftovers(data_dir: Path | None = None) -> None:
    """Remove what runs killed outright left in clear: the checks a stopped server left running and the decrypted
    archives in the copies, the ``inspect`` folders older than an hour, the work files of the backups that died with
    their process, and the backups past their hour. Never raises: a part that fails is logged, and the others still run.
    """
    data_dir = data_dir or get_data_dir()
    counts = {"checks_interrupted": 0, "decrypted_archives": 0, "decrypt_folders": 0, "jobs_interrupted": 0, "jobs_expired": 0}

    def restore() -> None:
        counts["checks_interrupted"] = restore_jobs.prune(data_dir)
        counts["decrypted_archives"] = restore_jobs.remove_stray_decrypted_archives(data_dir)

    def decrypt_folders() -> None:
        counts["decrypt_folders"] = remove_stale_decrypt_folders(backups_dir(data_dir))

    def backup_jobs() -> None:
        counts["jobs_interrupted"] = jobs.end_interrupted_jobs(data_dir)
        counts["jobs_expired"] = jobs.remove_expired_jobs(data_dir)

    for part, run in (("restore", restore), ("decrypt_folders", decrypt_folders), ("jobs", backup_jobs)):
        try:
            run()
        except Exception as exc:
            logger.error("A cleanup of backup leftovers failed", part=part, error=type(exc).__name__)
    if any(counts.values()):
        logger.info("Backup leftovers removed at startup", **counts)
