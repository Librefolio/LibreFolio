"""The space limit, applied (release 1.3, lot C8).

The limit is the global setting ``storage_limit_mb`` (0 = none), or ``LIBREFOLIO_STORAGE_LIMIT_MB`` when its hosting
provider sets it (``storage_usage.read_limit``). It is the most space LibreFolio should take in its data directory, all
of it: the database, the uploaded files, the broker reports, the backups and the rest.

What it stops, and what it never stops (developer decision, 06/11/2026):

=====================================================  =============================================================
an upload, a broker report (also a combined one)       refused when it would take the data past the limit
a backup started by hand                               the clean-up of the backups first; refused if still past it
a backup of the hosting panel, one of the command line always made (the clean-up of ``jobs`` runs after it)
a restore                                              refused when what it leaves would pass the limit
transactions, prices, the database                     never: the app would stop working
=====================================================  =============================================================

Every refusal is a ``StorageLimitExceededError`` carrying the numbers a message needs: the limit, the space used, what
the data would need to hold (``required_mb``: raise the limit to at least that) and the room the disk is missing to
hold it (``disk_missing_bytes``: free at least that), 0 when it has enough. A limit that cannot be read is no limit
(``read_limit`` never raises), and a measure that fails counts for what could be read, as in the space bar.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from backend.app.config import get_data_dir
from backend.app.config.backup import BackupConfigError, storage_limit_override_mb
from backend.app.services.platform import storage_usage

BYTES_PER_MB = 1024 * 1024

#: The code of the 507 answer of every refusal.
STORAGE_LIMIT_CODE = "storage_limit_exceeded"


@dataclass(frozen=True)
class StorageLimitProblem:
    """What the data would take past the limit, and what it needs to be allowed."""

    limit_mb: int
    #: The space the data directory takes now.
    used_bytes: int
    #: The space it would take after the action: the used one plus what is added, or what a restore leaves.
    required_bytes: int
    #: The room the volume is missing to hold ``required_bytes``: 0 when it has enough, or cannot be asked.
    disk_missing_bytes: int
    #: The limit is fixed by ``LIBREFOLIO_STORAGE_LIMIT_MB`` (its hosting provider): the administrator cannot raise it, so the
    #: message asks the provider and never says «raise it here».
    limit_locked: bool = False

    @property
    def required_mb(self) -> int:
        """The limit that would allow the action, in whole megabytes (rounded up)."""
        return max(1, math.ceil(self.required_bytes / BYTES_PER_MB))


class StorageLimitExceededError(Exception):
    """The action would take the data past the space limit."""

    def __init__(self, problem: StorageLimitProblem) -> None:
        super().__init__(f"The space limit of {problem.limit_mb} MB would be passed: {problem.required_bytes} bytes are needed")
        self.problem = problem


def storage_limit_detail(problem: StorageLimitProblem) -> dict[str, str | int]:
    """The ``detail`` of the 507 answer of a refusal: a stable ``code``, an English ``message`` (the screens word their own
    from the numbers) and the numbers; the user is told to raise the limit to ``required_mb`` and, when
    ``disk_missing_bytes`` is not 0, to free that much on the disk."""
    return {
        "code": STORAGE_LIMIT_CODE,
        "message": "The space limit would be passed",
        "limit_mb": problem.limit_mb,
        "used_bytes": problem.used_bytes,
        "required_bytes": problem.required_bytes,
        "required_mb": problem.required_mb,
        "disk_missing_bytes": problem.disk_missing_bytes,
        "limit_locked": problem.limit_locked,
    }


def judge(limit_mb: int | None, used_bytes: int, required_bytes: int, free_bytes: int | None, *, locked: bool = False) -> StorageLimitProblem | None:
    """The problem of taking ``required_bytes`` in all when ``used_bytes`` are taken now, with ``free_bytes`` free on the
    volume; ``None`` when there is no limit or the data stays within it. Pure."""
    if not limit_mb or required_bytes <= limit_mb * BYTES_PER_MB:
        return None
    growth = required_bytes - used_bytes
    missing = max(0, growth - free_bytes) if free_bytes is not None and growth > 0 else 0
    return StorageLimitProblem(limit_mb=limit_mb, used_bytes=used_bytes, required_bytes=required_bytes, disk_missing_bytes=missing, limit_locked=locked)


def _usage(data_dir: Path) -> storage_usage.StorageUsage:
    return storage_usage.measure_storage(data_dir)


def problem_for_total(required_bytes: int, *, data_dir: Path | None = None) -> StorageLimitProblem | None:
    """The problem of a data directory that would take ``required_bytes`` in all (a restore), or ``None``."""
    limit_mb, locked = storage_usage.read_limit()
    if limit_mb is None:
        return None
    usage = _usage(data_dir or get_data_dir())
    return judge(limit_mb, usage.data_bytes, required_bytes, usage.volume_free_bytes, locked=locked)


def problem_for_added(added_bytes: int, *, data_dir: Path | None = None) -> StorageLimitProblem | None:
    """The problem of adding ``added_bytes`` to the data directory (a file, a report, a backup), or ``None``."""
    limit_mb, locked = storage_usage.read_limit()
    if limit_mb is None:
        return None
    usage = _usage(data_dir or get_data_dir())
    return judge(limit_mb, usage.data_bytes, usage.data_bytes + max(0, added_bytes), usage.volume_free_bytes, locked=locked)


def judge_restore(limit_mb: int | None, locked: bool, restored_bytes: int, data_dir: Path) -> StorageLimitProblem | None:
    """The problem of a restore that puts ``restored_bytes`` (the copy's database and files) in place of the live ones under
    ``limit_mb``, or ``None``. What the data directory takes afterwards: the restored data, the backups and the rest of what
    stays (logs, state, keys), without the work folder of the restore itself (``.restore/``: the upload, the copy and the live
    data set aside, all gone when the restore ends). Reads the disk only, never the database."""
    if not limit_mb:
        return None
    usage = _usage(data_dir)
    kept = usage.backups_bytes + max(0, usage.other_bytes - storage_usage.folder_bytes(data_dir / ".restore"))
    return judge(limit_mb, usage.data_bytes, kept + max(0, restored_bytes), usage.volume_free_bytes, locked=locked)


def problem_after_restore(restored_bytes: int, *, data_dir: Path | None = None) -> tuple[int | None, bool, StorageLimitProblem | None]:
    """The limit in force now (``read_limit``: the setting is read from the database), whether its provider fixes it, and the
    problem of a restore that would leave ``restored_bytes`` of restored data: ``(limit_mb or None, locked, problem or None)``.
    The limit is the one in force before the restore, not the archive's own: the check asks it."""
    limit_mb, locked = storage_usage.read_limit()
    return limit_mb, locked, judge_restore(limit_mb, locked, restored_bytes, data_dir or get_data_dir())


def problem_at_confirmation(restored_bytes: int, recorded_limit_mb: int | None, recorded_locked: bool, *, data_dir: Path | None = None) -> StorageLimitProblem | None:
    """The problem of confirming a restore whose check recorded ``recorded_limit_mb``: asked again with the data of now, for
    data that grew since the check, and with the limit its hosting provider fixes now (``LIBREFOLIO_STORAGE_LIMIT_MB``, read
    from the environment); otherwise with the limit the check recorded. The database is never read here: a confirmation writes
    nothing outside ``.restore/``, and opening the database creates files beside it. A limit lowered in the settings since the
    check is seen at the next check, which an expired or outdated report makes anyway."""
    try:
        pinned = storage_limit_override_mb()
    except BackupConfigError:
        pinned = None
    if pinned is not None:
        return judge_restore(pinned or None, True, restored_bytes, data_dir or get_data_dir())
    return judge_restore(recorded_limit_mb, recorded_locked, restored_bytes, data_dir or get_data_dir())


def require_room_for(added_bytes: int, *, data_dir: Path | None = None) -> None:
    """Raise ``StorageLimitExceededError`` when adding ``added_bytes`` would pass the limit."""
    problem = problem_for_added(added_bytes, data_dir=data_dir)
    if problem is not None:
        raise StorageLimitExceededError(problem)


def backup_estimate_bytes(data_dir: Path | None = None) -> int:
    """What a backup started now would add: the size of what the archive carries (the database, the uploaded files and the
    broker reports), as they are on disk. The archive is compressed, so this is an upper bound: a backup refused on it
    loses nothing, the administrator raises the limit or frees space, and the message says how much."""
    usage = _usage(data_dir or get_data_dir())
    return usage.database_bytes + usage.uploads_bytes + usage.broker_reports_bytes
