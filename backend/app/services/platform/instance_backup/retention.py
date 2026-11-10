"""The backups an instance keeps, and the clean-up that bounds them (lot FB-24).

A backup that ends ``done`` is kept: its job folder moves from ``backups/.jobs/<id>/`` to ``backups/<kept name>/``
(``jobs.py``, ``paths.kept_folder_name``), with its ``state.json`` beside the archive. ``list_kept`` reads those folders,
the newest first; it is where the Backup tab and the Files page get their table.

The clean-up has two rules, both optional (0 switches a rule off): a total size (``backup_cleanup_max_mb``: when the
kept archives weigh more, the oldest go until they fit) and an age (``backup_cleanup_max_days``: the older ones go).
**The latest backup is never removed**, whatever the rules say, so an instance always keeps one. It runs after every
backup, at every start, and at most once an hour in the scheduler's run (``scheduler.py``); a self-hosted instance
starts with both rules off, a managed one with 250 MB and 30 days (``config/backup.py``).

Only a folder this module lists is removed: a kept name, a plain folder (never a link), a readable ``done`` state whose
id matches the name, an archive that is a regular file. A running job, a failed one, the ``.decrypt-*`` folders and the
loose files an older ``dev.py backup create`` left in ``backups/`` are none of its business and stay as they are.
"""

from __future__ import annotations

import re
import shutil
import stat
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from sqlalchemy.exc import OperationalError

from backend.app.db import session as db_session
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup import jobs
from backend.app.services.platform.instance_backup.paths import backups_dir, is_kept_name, is_plain_dir

logger = get_logger(__name__)

#: A megabyte of the size rule: 1024 × 1024 bytes, as the rest of the app counts storage.
_MB = 1024 * 1024
CleanupReason = Literal["age", "space"]


@dataclass(frozen=True)
class KeptBackup:
    """A finished backup the instance keeps: its state, its folder, and the size of its archive on disk (bytes)."""

    job: jobs.BackupJob
    folder: Path
    size: int


@dataclass(frozen=True)
class CleanupPolicy:
    """The two rules of the clean-up; 0 switches a rule off."""

    max_mb: int = 0
    max_days: int = 0


def list_kept(data_dir: Path) -> list[KeptBackup]:
    """The backups kept in ``backups/``, the newest first. Anything that is not a finished backup in a kept folder (see the
    module) is left out; reading never raises."""
    root = backups_dir(data_dir)
    if not is_plain_dir(root):
        return []
    found: list[KeptBackup] = []
    try:
        entries = list(root.iterdir())
    except OSError:
        return []
    for folder in entries:
        kept = _read_kept(folder)
        if kept is not None:
            found.append(kept)
    found.sort(key=lambda item: item.job.created_at, reverse=True)
    return found


def _read_kept(folder: Path) -> KeptBackup | None:
    """``folder`` as a kept backup, or ``None`` when it is not one."""
    if not is_kept_name(folder.name) or not is_plain_dir(folder):
        return None
    try:
        job = jobs._read_state(folder)  # noqa: SLF001 — the same package reads the state it writes
    except (jobs.BackupJobNotFoundError, OSError):
        return None
    if job.status != "done" or not job.file_name or Path(job.file_name).name != job.file_name or not folder.name.endswith(f"-{job.job_id[:8]}"):
        return None
    try:
        info = (folder / job.file_name).lstat()
    except OSError:
        return None
    if not stat.S_ISREG(info.st_mode):
        return None
    return KeptBackup(job=job, folder=folder, size=info.st_size)


def plan_cleanup(kept: Sequence[KeptBackup], policy: CleanupPolicy, now: datetime) -> list[tuple[KeptBackup, CleanupReason]]:
    """The backups to remove under ``policy`` at ``now``, each with the rule that takes it. The latest is never in it. The
    age rule goes first (a backup older than ``max_days`` days); then, while what is left weighs more than ``max_mb``, the
    oldest of it goes, until it fits or only the latest is left."""
    ordered = sorted(kept, key=lambda item: item.job.created_at, reverse=True)
    if len(ordered) <= 1:
        return []
    plan: list[tuple[KeptBackup, CleanupReason]] = []
    left = [ordered[0]]
    for item in ordered[1:]:
        if policy.max_days > 0 and now - item.job.created_at > timedelta(days=policy.max_days):
            plan.append((item, "age"))
        else:
            left.append(item)
    if policy.max_mb > 0:
        limit = policy.max_mb * _MB
        while len(left) > 1 and sum(item.size for item in left) > limit:
            plan.append((left.pop(), "space"))
    return plan


def read_policy() -> CleanupPolicy:
    """The clean-up the administrator set (or the profile gives while nobody did), read from the database in this thread. A
    value that is not a whole number of zero or more, a database without the setting, a failure: that rule is off."""
    try:
        from sqlalchemy import select  # noqa: PLC0415 — only when a policy is read
        from sqlalchemy.orm import Session  # noqa: PLC0415

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415
        from backend.app.schemas.settings import SETTINGS_REGISTRY  # noqa: PLC0415
        from backend.app.services.accounts.global_settings_service import effective_stored_value  # noqa: PLC0415

        keys = (SETTINGS_REGISTRY.global_.BACKUP_CLEANUP_MAX_MB.key, SETTINGS_REGISTRY.global_.BACKUP_CLEANUP_MAX_DAYS.key)
        with Session(db_session.get_sync_engine()) as session:
            rows = {row.key: row for row in session.execute(select(GlobalSetting).where(GlobalSetting.key.in_(keys))).scalars()}  # type: ignore[attr-defined]
        values = [_whole_number(effective_stored_value(key, rows.get(key)), rows.get(key)) for key in keys]
        return CleanupPolicy(max_mb=values[0], max_days=values[1])
    except OperationalError as exc:
        # A database that does not hold the settings yet (never started, or not migrated): expected, no traceback.
        logger.warning("The clean-up rules of the kept backups are not in the database: the clean-up stays off", error=str(exc.orig)[:200])
        return CleanupPolicy()
    except Exception as exc:  # noqa: BLE001 — a clean-up that cannot read its rules removes nothing; the cause is logged
        logger.warning("The clean-up rules of the kept backups cannot be read: the clean-up stays off", exc_info=exc)
        return CleanupPolicy()


def _whole_number(effective: str | None, row: object | None) -> int:
    """The number a setting holds, ``effective`` (a profile's value) first, then its row; 0 for anything else."""
    text = effective if effective is not None else (getattr(row, "value", None) if row is not None else None)
    if text is None:
        return 0
    text = str(text).strip()
    return int(text) if re.fullmatch(r"\d{1,9}", text) else 0


def apply_cleanup(data_dir: Path, policy: CleanupPolicy | None = None, *, now: datetime | None = None) -> tuple[str, ...]:
    """Remove the kept backups ``policy`` (default: the rules in the database) takes at ``now``; the ids removed. Never
    raises: a folder that cannot be removed is logged and the others still go."""
    removed: list[str] = []
    try:
        policy = policy if policy is not None else read_policy()
        if policy.max_mb <= 0 and policy.max_days <= 0:
            return ()
        for item, reason in plan_cleanup(list_kept(data_dir), policy, now or datetime.now(UTC)):
            try:
                shutil.rmtree(item.folder)
            except OSError as exc:
                logger.warning("A kept backup could not be removed", job_id=item.job.job_id, reason=reason, exc_info=exc)
                continue
            removed.append(item.job.job_id)
            logger.info("Kept backup removed", job_id=item.job.job_id, reason=reason, size_bytes=item.size, origin=item.job.origin)
    except Exception as exc:  # noqa: BLE001 — isolation boundary: a clean-up never stops a backup, a start or a scheduler run
        logger.error("The clean-up of the kept backups failed", exc_info=exc)
    return tuple(removed)
