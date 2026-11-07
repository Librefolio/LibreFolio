"""The space an instance takes, for the space bar of the Files page (lot FB-29).

``measure_storage`` walks the data directory once and splits what it finds in five parts that never overlap: the
database (``sqlite/``), the uploaded files (``custom-uploads/``), the broker reports (``broker_reports/``), the
backups (``backups/``, ``.jobs/`` included), a restore under way (``.restore/``, C9-7) and everything else LibreFolio keeps
there (logs, state). Their sum is ``data_bytes``. Next to it, the volume the data directory lives on (total, used, free), so a
self-hosted instance with no limit can draw «LibreFolio's parts, the other files of the disk, the free space».

The limit is the global setting ``storage_limit_mb`` (0 = none), or ``LIBREFOLIO_STORAGE_LIMIT_MB`` when its hosting
provider sets it, which wins and locks the setting (``read_limit``).

Everything here is bytes and sums: the frontend only turns them into the widths of a bar. Nothing raises: a folder that
cannot be read counts for what could be read, a volume that cannot be asked is ``None``.
"""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from backend.app.config.backup import BackupConfigError, storage_limit_override_mb
from backend.app.db import session as db_session
from backend.app.logging_config import get_logger

logger = get_logger(__name__)

#: The top-level entries of the data directory that make the named parts; ``.restore`` is a restore under way (C9-7): the
#: uploaded archive and its opened version, until the restore ends or is discarded.
_PARTS = {"sqlite": "database_bytes", "custom-uploads": "uploads_bytes", "broker_reports": "broker_reports_bytes", "backups": "backups_bytes", ".restore": "restore_bytes"}


@dataclass(frozen=True)
class StorageUsage:
    """The space an instance takes, in bytes."""

    database_bytes: int
    uploads_bytes: int
    broker_reports_bytes: int
    backups_bytes: int
    other_bytes: int
    data_bytes: int
    volume_total_bytes: int | None
    volume_used_bytes: int | None
    volume_free_bytes: int | None
    limit_mb: int | None
    limit_locked: bool
    #: C9-7: a restore under way (``.restore/``: the uploaded archive, its opened version, the data set aside while it applies).
    restore_bytes: int = 0


def _entry_bytes(entry: os.DirEntry[str]) -> int:
    """The bytes of one entry: a folder is walked, anything else (a link included, never followed) counts its own size."""
    try:
        if entry.is_dir(follow_symlinks=False):
            return folder_bytes(Path(entry.path))
        return entry.stat(follow_symlinks=False).st_size
    except OSError:
        return 0


def folder_bytes(path: Path) -> int:
    """The bytes of the files below ``path``, a folder's own entry not counted. A link is not followed: it counts its own
    size, not its target's; ``path`` itself being a link, or missing, is 0. An entry that vanishes or cannot be read counts
    0. Never raises."""
    try:
        if path.is_symlink():
            return 0
        if not path.is_dir():
            return path.lstat().st_size
        with os.scandir(path) as entries:
            return sum(_entry_bytes(entry) for entry in entries)
    except OSError:
        return 0


def measure_storage(data_dir: Path, *, limit_mb: int | None = None, limit_locked: bool = False) -> StorageUsage:
    """The space ``data_dir`` takes, split in parts, and the volume it is on. ``limit_mb`` and ``limit_locked`` are passed
    through (see ``read_limit``). Never raises."""
    sizes = dict.fromkeys(_PARTS.values(), 0)
    other = 0
    try:
        with os.scandir(data_dir) as entries:
            for entry in entries:
                size = _entry_bytes(entry)
                name = _PARTS.get(entry.name)
                if name is None:
                    other += size
                else:
                    sizes[name] += size
    except OSError:
        sizes = dict.fromkeys(_PARTS.values(), 0)
        other = 0
    total, used, free = _volume(data_dir)
    return StorageUsage(**sizes, other_bytes=other, data_bytes=sum(sizes.values()) + other, volume_total_bytes=total, volume_used_bytes=used, volume_free_bytes=free, limit_mb=limit_mb, limit_locked=limit_locked)


def _volume(data_dir: Path) -> tuple[int | None, int | None, int | None]:
    """The volume the data directory is on: total, used, free; ``None`` three times when it cannot be asked."""
    try:
        usage = shutil.disk_usage(data_dir)
    except Exception as exc:  # noqa: BLE001 — isolation boundary: a volume that cannot be asked is three Nones, whatever the cause
        logger.debug("The volume of the data directory cannot be asked", error=type(exc).__name__)
        return None, None, None
    return usage.total, usage.used, usage.free


def read_limit() -> tuple[int | None, bool]:
    """The space limit in force and whether it is locked: ``(limit in MB or None for no limit, locked)``.

    ``LIBREFOLIO_STORAGE_LIMIT_MB``, when it is set and usable, is the limit and locks the setting. A variable that is
    set but unusable is ignored (the configuration audit is the place to say so): the global setting speaks, unlocked.
    Without a variable the setting does, read from the database in this thread. A value that is not a whole number, a
    database that does not hold the setting yet, a failure: no limit. Never raises.
    """
    try:
        override = storage_limit_override_mb()
    except BackupConfigError:
        override = None
    if override is not None:
        return (override or None), True
    return _limit_of_the_setting(), False


def _limit_of_the_setting() -> int | None:
    """The ``storage_limit_mb`` row, as a limit in MB (0 and anything unusable are no limit)."""
    try:
        from sqlalchemy import select  # noqa: PLC0415 — only when the limit is read
        from sqlalchemy.orm import Session  # noqa: PLC0415

        from backend.app.db.models import GlobalSetting  # noqa: PLC0415
        from backend.app.schemas.settings import SETTINGS_REGISTRY  # noqa: PLC0415

        key = SETTINGS_REGISTRY.global_.STORAGE_LIMIT_MB.key
        with Session(db_session.get_sync_engine()) as session:
            row = session.execute(select(GlobalSetting).where(GlobalSetting.key == key)).scalar_one_or_none()  # type: ignore[attr-defined]
        text = str(row.value).strip() if row is not None else ""
        return int(text) or None if re.fullmatch(r"\d{1,9}", text) else None
    except Exception as exc:  # noqa: BLE001 — a limit that cannot be read is no limit; the cause is logged
        logger.warning("The space limit cannot be read: the bar shows no limit", exc_info=exc)
        return None
