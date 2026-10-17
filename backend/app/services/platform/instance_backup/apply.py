"""A checked restore, applied at the next start of the server (lot B3).

A restore confirmed from Settings › Administration › Backup or from ``dev.py backup restore`` waits in
``.restore/restore.json``, the state of the one restore of a data directory, until a start applies it: the startup
step ``pending-restore`` (``app_lifespan.py``) runs before any step reads the data.

- **The swap.** The four folders an archive carries (``SWAPPED_FOLDERS``) swap places with those of the checked copy,
  by renames inside the data directory, each instant whatever its size: the live ones go to ``.restore/previous/``, the
  copy's take their place. ``secrets/``, ``logs/``, ``scheduler_state.json``, ``backups/`` and ``.restore`` itself
  stay as they are, so the one-time ticket of the outcome (``.restore/outcome-ticket.json``, ``outcome.py``) outlives
  the swap, the commit and a rollback; a new confirmation and a cancel remove it. A
  journal, written before the first move, records what existed: a start that dies during the swap is undone by the next
  one, from what the files say, and again by the one after if that too is cut.
- **The first start must complete.** Its step ``restore-commit`` ends every session (decision 40: each account's
  session version becomes the restore time in milliseconds), revokes every one-time link the backup still held live
  (invitations, password resets, email verifications, the admin setup: a link used or revoked on the instance after the
  backup was taken must not work again), removes the data of before (decision 41: it only served to go back) and
  records the restore as committed. A start that dies before it — a migration that fails, a damaged file —
  leaves the restore applied by a boot that no longer runs: the next start puts the data of before back and records the
  restore as rolled back, with why.

A **boot** is the server's root process: uvicorn's master when it runs workers, otherwise the server's own process
(``restart.server_pid``), known by its pid and its creation time, so that a reused pid is never taken for it. Each
process reads it once: a clock step between two steps of one start does not make it another boot. The workers of one
server each run the start: they take turns on ``.restore/apply.lock``, the first swaps, the others find the restore
applied by their own boot.

**Never under a running server.** From the moment its data directories exist, before any step reads the data, until it
exits, every server process holds a shared ``flock`` on the data directory itself (the step ``serving-lock``, right
after ``data-directories``; ``hold_serving_lock``; no file is created). A swap, or the undo of a dead start, happens
only where nobody holds it, and holds it exclusively while the folders move, so that a process reaching ``serving-lock``
meanwhile waits until they have: a worker uvicorn starts again under its running siblings (after a crash, ``SIGHUP``,
``SIGTTIN``), or a second server on the same data directory, leaves a pending restore waiting (``server_running``) and
never undoes one under a process that may have read the restored data. A restore found applied by another server that
still runs, or by another boot at the commit, stops the start (``RestoreInUseError``) rather than serve uncommitted
data.

**Never on a blocked instance** (developer decision P7). While the hosting provider blocks the instance
(``LIBREFOLIO_BLOCKED``), a pending restore is not applied: it waits for the first start after the unblock
(``instance_blocked``). The undo of a swap a start left half done, and the commit of the restore this start applied,
still run: the first repairs the data directory, and the block cannot change during one start.

An ordinary start, with no restore, only finds that ``.restore/restore.json`` does not exist: it creates no folder and
no lock file.
"""

from __future__ import annotations

import contextlib
import functools
import os
import shutil
import sqlite3
import stat
import threading
from collections.abc import Iterator
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import psutil
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

try:
    import fcntl
except ImportError:  # pragma: no cover - not POSIX: the restores of one process take turns, no more
    fcntl = None  # type: ignore[assignment]

from backend.app.config import get_data_dir
from backend.app.config.platform import instance_blocked
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup import restart
from backend.app.services.platform.instance_backup.jobs import _lock_held
from backend.app.services.platform.instance_backup.outcome import drop_ticket, issue_ticket
from backend.app.services.platform.instance_backup.paths import (
    DATABASE_ENTRY,
    SWAPPED_FOLDERS,
    BackupPathError,
    apply_lock_path,
    check_state_path,
    checks_dir,
    database_path,
    ensure_private_dir,
    failed_dir,
    is_job_id,
    is_plain_dir,
    lock_path,
    previous_dir,
    restore_dir,
    restore_state_path,
    stage_data_dir,
    stage_dir,
    stages_dir,
)
from backend.app.services.platform.instance_backup.staging import read_report, remove_stage
from backend.app.services.platform.readiness import alembic_head_revision

logger = get_logger(__name__)

RestorePhase = Literal["pending", "applying", "applied", "rolling_back", "committed", "rolled_back"]
#: Why a restore was rolled back: the first start on the restored data did not complete; a start died during the swap;
#: a folder could not be moved; the checked copy was gone or changed.
RollbackReason = Literal["first_start_failed", "swap_interrupted", "swap_failed", "stage_missing"]
#: Why a pending restore was not applied at a start, and still waits: a backup was running; the data directory is not
#: the one the restore was confirmed for (a copy of it); another server process was serving it (a worker started again
#: under its running siblings, or a second server); the hosting provider blocked the instance (developer decision P7).
WaitReason = Literal["backup_running", "other_data_directory", "server_running", "instance_blocked"]
#: The phases of a restore not finished yet: its copy is kept, and no other restore can be confirmed.
ACTIVE: frozenset[str] = frozenset({"pending", "applying", "applied", "rolling_back"})

_PARTIAL_SUFFIX = ".part"
_PROCESS_LOCKS: dict[str, threading.Lock] = {}
_PROCESS_LOCKS_GUARD = threading.Lock()
#: The descriptors this process holds its shared serving lock on, by data directory: kept open until it exits.
_SERVING: dict[str, int] = {}
_STAGE_ID_PATTERN = r"^[0-9a-f]{32}$"


class Boot(BaseModel):
    """A start of the server: its root process, and that process's creation time (a reused pid is another boot)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pid: int
    started: float


class SwapEntry(BaseModel):
    """One folder of the swap, as it was when the swap began: whether the live one and the copy's existed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    live: bool
    staged: bool

    @field_validator("name")
    @classmethod
    def _a_swapped_folder(cls, value: str) -> str:
        # The state file lives in the data directory: a name read from it never becomes a path outside the swap.
        if value not in SWAPPED_FOLDERS:
            raise ValueError("not a folder a restore swaps")
        return value


class RestoreState(BaseModel):
    """The state of the restore of a data directory, kept in ``.restore/restore.json``."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    format: Literal[1] = 1
    status: RestorePhase
    stage_id: str = Field(pattern=_STAGE_ID_PATTERN)
    #: The data directory's real path when the restore was confirmed: a copy of the data directory does not apply it.
    data_dir: str
    confirmed_at: datetime
    #: The username of the administrator who confirmed it, or ``cli``.
    confirmed_by: str
    backup_created_at: datetime
    backup_app_version: str
    action: Literal["same", "upgrade"]
    #: The journal of the swap, written before its first move.
    swap: list[SwapEntry] = []
    boot: Boot | None = None
    applied_at: datetime | None = None
    finished_at: datetime | None = None
    reason: RollbackReason | None = None
    waiting: WaitReason | None = None
    #: The session version every account got at the commit: the restore time in milliseconds (decision 40).
    session_version: int | None = None


class RestoreStateError(RuntimeError):
    """A restore cannot be confirmed, cancelled or applied; ``code`` says why, in a stable word."""

    code = "restore_failed"


class RestoreStageMissingError(RestoreStateError):
    """No checked copy has this id, or its copy is gone or changed."""

    code = "restore_stage_not_found"


class RestoreNotRestorableError(RestoreStateError):
    """The check refused the archive, or found what forbids a restore (no administrator)."""

    code = "restore_not_restorable"


class RestoreStageExpiredError(RestoreStateError):
    """The check is older than its lifetime: the archive must be checked again."""

    code = "restore_stage_expired"


class RestoreStageOutdatedError(RestoreStateError):
    """LibreFolio was updated since the check: its copy is not at this LibreFolio's revision."""

    code = "restore_stage_outdated"


class RestoreAlreadyPendingError(RestoreStateError):
    """Another restore waits for the next start, or is being applied."""

    code = "restore_already_pending"


class RestoreNotPendingError(RestoreStateError):
    """No restore waits for the next start."""

    code = "restore_not_pending"


class RestoreStateUnreadableError(RestoreStateError):
    """The state file of the restore is there, but the file system does not let it be read: its owner or permissions, a
    disk error (B-32). Whether a restore waits, or is being applied, is not known. ``reason`` is what the file system
    said, never a path."""

    code = "restore_state_unreadable"

    def __init__(self, reason: str) -> None:
        super().__init__(f"The state of the restore cannot be read: {reason}")
        self.reason = reason


class RestoreApplyError(RestoreStateError):
    """The undo of a swap failed: the data directory is half restored, and the server must not start on it."""

    code = "restore_apply_failed"


class RestoreInUseError(RestoreStateError):
    """Another server uses the data directory, or applied the restore found there: this start must not touch it, nor
    serve data whose restore is not committed."""

    code = "restore_in_use"


def _now() -> datetime:
    return datetime.now(UTC)


# =============================================================================
# Boots
# =============================================================================


def current_boot() -> Boot:
    """This start of the server: its root process (``restart.server_pid``, looked up at each call) and its creation
    time, read once per process (``_boot_of``)."""
    return _boot_of(restart.server_pid())


@functools.cache
def _boot_of(pid: int) -> Boot:
    """The boot of the root process ``pid``, read once per process: on Linux psutil derives a creation time from the
    system's boot time, which a clock step moves, and the two steps of one start must find the same boot."""
    try:
        started = round(psutil.Process(pid).create_time(), 3)
    except psutil.Error:
        started = 0.0
    return Boot(pid=pid, started=started)


def boot_alive(boot: Boot) -> bool:
    """Whether the root process of ``boot`` still runs: its pid exists, with the same creation time."""
    try:
        return round(psutil.Process(boot.pid).create_time(), 3) == boot.started
    except psutil.Error:
        return False


# =============================================================================
# The state, its lock, its files
# =============================================================================


def _restore_folder(data_dir: Path) -> bool | None:
    """``None`` when there is no ``.restore``; ``False`` when it is a link or a file (never followed); ``True`` otherwise."""
    folder = restore_dir(data_dir)
    if not os.path.lexists(folder):
        return None
    return is_plain_dir(folder)


def _has_state(data_dir: Path) -> bool:
    """Whether ``.restore`` is a plain folder holding a state file: found without creating anything, never through a
    link."""
    return _restore_folder(data_dir) is True and os.path.lexists(restore_state_path(data_dir))


def _state_present(data_dir: Path, step: str) -> bool:
    """Whether a startup step has a restore to look at; a ``.restore`` that is a link or a file is logged and ignored."""
    if _restore_folder(data_dir) is False:
        logger.error("The restore folder of the data directory is not a plain folder: a restore waiting in it is ignored", step=step)
        return False
    return _has_state(data_dir)


@contextlib.contextmanager
def _apply_lock(data_dir: Path) -> Iterator[None]:
    """The exclusive lock of the restore of a data directory, waited for: the workers of one server take turns."""
    path = apply_lock_path(data_dir)
    if fcntl is None:
        with _PROCESS_LOCKS_GUARD:
            local = _PROCESS_LOCKS.setdefault(str(path), threading.Lock())
        with local:
            yield
        return
    fd = os.open(path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def _read_state(data_dir: Path) -> RestoreState | None:
    """The state file, read without following a link. ``None`` when there is none, when it is not a file (a link, a
    folder: never followed) or not a state this LibreFolio can read (§10), both logged. ``RestoreStateUnreadableError``
    when the file system does not let it be read (logged): whether a restore waits is then not known (B-32)."""
    path = restore_state_path(data_dir)
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            logger.error("The state of the restore is not a file: it is ignored")
            return None
        with os.fdopen(os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)), "rb") as handle:
            raw = handle.read()
    except FileNotFoundError:
        return None
    except OSError as exc:
        logger.error("The state of the restore cannot be read", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        raise RestoreStateUnreadableError(exc.strerror or type(exc).__name__) from None
    try:
        return RestoreState.model_validate_json(raw)
    except ValidationError:
        logger.error("The state of the restore is not one this LibreFolio can read: it is ignored")
        return None


def _state_at_start(data_dir: Path) -> RestoreState | None:
    """The state, for a startup step: one the file system does not let be read is logged by the reader and left as it
    is, and the start goes on with the data as it is, as for a state no restore can hold (§10, B-32)."""
    try:
        return _read_state(data_dir)
    except RestoreStateUnreadableError:
        return None


def _write_state(data_dir: Path, state: RestoreState) -> None:
    """Write the state atomically: a reader, or the next start, finds the old state or the new one, never half of one."""
    folder = restore_dir(data_dir)
    if not is_plain_dir(folder):
        raise BackupPathError(folder)
    target = restore_state_path(data_dir)
    partial = target.with_name(target.name + _PARTIAL_SUFFIX)
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(state.model_dump_json(indent=2))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(partial, target)
    _fsync_dir(folder)


def _record(data_dir: Path, state: RestoreState) -> RestoreState:
    """Write the state where failing to must not stop what follows (an undo): the failure is logged."""
    try:
        _write_state(data_dir, state)
    except (OSError, BackupPathError) as exc:
        logger.error("The state of the restore could not be written", status=state.status, error=str(exc))
    return state


def _fsync_dir(folder: Path) -> None:
    """Make the renames inside ``folder`` durable; nothing where the file system cannot."""
    with contextlib.suppress(OSError):
        fd = os.open(folder, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _remove_path(path: Path) -> None:
    """Remove a folder with its content, or a file; a link is removed, never followed."""
    if is_plain_dir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.lexists(path):
        with contextlib.suppress(OSError):
            path.unlink()


def _move(source: Path, target: Path) -> None:
    """One move of the swap or of its undo: a rename inside the data directory."""
    os.rename(source, target)


def read_restore(data_dir: Path | None = None) -> RestoreState | None:
    """The restore of the data directory: waiting, being applied, or the last one that ended. ``None`` when there is
    none, when ``.restore`` or the state file is a link (never followed), or when the state is not one this LibreFolio
    can read. ``RestoreStateUnreadableError`` when the file system does not let the state be read (B-32)."""
    data_dir = data_dir or get_data_dir()
    if not _restore_folder(data_dir):
        return None
    return _read_state(data_dir)


def protected_stage(data_dir: Path) -> str | None:
    """The stage of a restore not finished yet: its copy must be neither pruned nor dropped. ``None`` as well when the
    state cannot be read (logged by the reader), as before B-32."""
    try:
        state = read_restore(data_dir)
    except RestoreStateUnreadableError:
        return None
    return state.stage_id if state is not None and state.status in ACTIVE else None


def _copy_usable(data_dir: Path, stage_id: str) -> bool:
    """Whether the checked copy can be moved into place: plain folders down to it, its database a file."""
    copy = stage_data_dir(data_dir, stage_id)
    folders = (restore_dir(data_dir), stages_dir(data_dir), stage_dir(data_dir, stage_id), copy, copy / "sqlite")
    if not all(is_plain_dir(folder) for folder in folders):
        return False
    if any(os.path.lexists(copy / name) and not is_plain_dir(copy / name) for name in SWAPPED_FOLDERS):
        return False
    try:
        return stat.S_ISREG((copy / DATABASE_ENTRY).lstat().st_mode)
    except OSError:
        return False


def _remove_leftovers(data_dir: Path, stage_id: str | None) -> None:
    """Remove what a finished restore leaves: the data of before, the restored data a rollback set aside, its copy."""
    for path in (previous_dir(data_dir), failed_dir(data_dir)):
        _remove_path(path)
    if stage_id is None or not is_job_id(stage_id):
        return
    remove_stage(data_dir, stage_id)
    if is_plain_dir(restore_dir(data_dir)) and is_plain_dir(checks_dir(data_dir)):
        with contextlib.suppress(OSError):
            check_state_path(data_dir, stage_id).unlink(missing_ok=True)


# =============================================================================
# Confirming and cancelling
# =============================================================================


def confirm_restore(stage_id: str, *, confirmed_by: str, data_dir: Path | None = None, now: datetime | None = None) -> RestoreState:
    """Confirm the restore of a checked copy: it waits for the next start of the server, which applies it.

    ``BackupPathError`` when ``.restore`` is a link or a file; then ``RestoreStageMissingError``,
    ``RestoreNotRestorableError``, ``RestoreStageExpiredError``, ``RestoreStageOutdatedError``, in this order; then
    ``RestoreAlreadyPendingError``, or ``RestoreStateUnreadableError`` when the state there cannot be read: a restore
    half applied may be behind it, and its journal is never written over (B-32).
    """
    data_dir = data_dir or get_data_dir()
    now = now or _now()
    if _restore_folder(data_dir) is False:
        raise BackupPathError(restore_dir(data_dir))
    if not is_job_id(stage_id) or not _copy_usable(data_dir, stage_id):
        raise RestoreStageMissingError("No checked copy has this id")
    try:
        report = read_report(data_dir, stage_id)
    except OSError:
        raise RestoreStageMissingError("No checked copy has this id") from None
    if report.blockers:
        raise RestoreNotRestorableError(f"The archive cannot be restored: {', '.join(report.blockers)}")
    if report.expires_at <= now:
        raise RestoreStageExpiredError("The check of the archive expired: check it again")
    head = alembic_head_revision()
    if head is not None and head != report.head_revision:
        raise RestoreStageOutdatedError("LibreFolio was updated since the check: check the archive again")
    ensure_private_dir(restore_dir(data_dir), data_dir)
    with _apply_lock(data_dir):
        current = _read_state(data_dir)
        if current is not None and current.status in ACTIVE:
            raise RestoreAlreadyPendingError("A restore already waits for the next start")
        _remove_leftovers(data_dir, None)
        state = RestoreState(
            status="pending",
            stage_id=stage_id,
            data_dir=str(data_dir.resolve()),
            confirmed_at=now,
            confirmed_by=confirmed_by,
            backup_created_at=report.backup.created_at,
            backup_app_version=report.backup.app_version,
            action=report.action,
        )
        _write_state(data_dir, state)
        # A new restore: no ticket of an older one reads it.
        drop_ticket(data_dir=data_dir)
    logger.warning("Restore confirmed: the next start of the server applies it", stage_id=stage_id, confirmed_by=confirmed_by, action=report.action)
    return state


def cancel_restore(*, data_dir: Path | None = None, drop_copy: bool = False) -> RestoreState:
    """Drop the restore waiting for the next start; the state it had. ``RestoreNotPendingError`` when none waits.

    ``drop_copy`` also removes its checked copy; otherwise the copy stays until it expires, and can be confirmed again.
    A copy that cannot be removed is logged, never raised: the restore is cancelled already, and the copy goes when its
    check expires (``restore_jobs.prune``).
    The one-time ticket of its outcome goes too. Without a restore nothing is created, not even the lock.
    ``RestoreStateUnreadableError`` when the state cannot be read: nothing is dropped (B-32).
    """
    data_dir = data_dir or get_data_dir()
    # Read first without the lock, as prepare_restart does: a state that cannot be read is said, never taken for none.
    waiting = read_restore(data_dir)
    if waiting is None or waiting.status != "pending":
        raise RestoreNotPendingError("No restore waits for the next start")
    with _apply_lock(data_dir):
        state = _read_state(data_dir)
        if state is None or state.status != "pending":
            raise RestoreNotPendingError("No restore waits for the next start")
        restore_state_path(data_dir).unlink()
        _fsync_dir(restore_dir(data_dir))
        drop_ticket(data_dir=data_dir)
        copy_dropped = drop_copy
        if drop_copy:
            # Inside the lock: a confirmation of the same copy, from another page, cannot come in between.
            try:
                _remove_leftovers(data_dir, state.stage_id)
            except OSError as exc:
                copy_dropped = False
                logger.warning("The copy of a cancelled restore could not be removed: it goes when its check expires", stage_id=state.stage_id, error=f"{type(exc).__name__}: {exc.strerror or exc}")
    logger.info("Pending restore cancelled", stage_id=state.stage_id, copy_dropped=copy_dropped)
    return state


def prepare_restart(*, data_dir: Path | None = None) -> tuple[RestoreState, str]:
    """The restore waiting for the next start, and a new one-time ticket of its outcome (``outcome.issue_ticket``),
    issued under the restore's lock: a cancel or a confirmation cannot come in between, and two restart requests take
    turns on the ticket's file. ``RestoreNotPendingError`` when none waits; then nothing is written, not even the lock.
    ``RestoreStateUnreadableError`` when the state cannot be read (B-32); ``BackupPathError`` or an ``OSError`` when the
    ticket cannot be written.
    """
    data_dir = data_dir or get_data_dir()
    # Read first without the lock, as a refused restart writes nothing (not even the lock); then again under it.
    waiting = read_restore(data_dir)
    if waiting is None or waiting.status != "pending":
        raise RestoreNotPendingError("No restore waits for the next start")
    with _apply_lock(data_dir):
        state = _read_state(data_dir)
        if state is None or state.status != "pending":
            raise RestoreNotPendingError("No restore waits for the next start")
        return state, issue_ticket(state.stage_id, data_dir=data_dir)


# =============================================================================
# The serving lock
# =============================================================================


def _open_directory(data_dir: Path) -> int | None:
    try:
        return os.open(data_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError as exc:
        logger.warning("The data directory cannot be opened for its serving lock", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        return None


@contextlib.contextmanager
def _exclusive_serving_lock(data_dir: Path) -> Iterator[bool]:
    """Whether a server process serves the data directory now (holds its serving lock). When none does, this process
    holds that lock exclusively until the block ends: a process reaching its step ``serving-lock`` meanwhile waits until
    the folders have moved, and never reads them half moved. ``False`` where it cannot be known (no ``fcntl``, a file
    system without ``flock``): the restore then behaves as before the lock existed, and a warning says so."""
    if fcntl is None:
        yield False
        return
    fd = _open_directory(data_dir)
    if fd is None:
        yield False
        return
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            served = False
        except BlockingIOError:
            served = True
        except OSError as exc:
            logger.warning("The serving lock of the data directory cannot be probed: a restore is applied without it", error=f"{type(exc).__name__}: {exc.strerror or exc}")
            served = False
        yield served
    finally:
        # Closing the descriptor releases the lock, however the block ended.
        os.close(fd)


def hold_serving_lock(data_dir: Path | None = None) -> bool:
    """The startup step ``serving-lock``, right after ``data-directories`` and before any step reads the data: this
    process serves the data directory from now until it exits, and holds a shared ``flock`` on the directory itself to
    say so (no file is created); the system releases it with the process, however it ends. While a restore moves the
    folders, it waits until they have moved. Whether it is held; once per data directory and process."""
    data_dir = data_dir or get_data_dir()
    key = str(data_dir.resolve())
    if fcntl is None or key in _SERVING:
        return key in _SERVING
    fd = _open_directory(data_dir)
    if fd is None:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.warning("A restore is moving the folders of the data directory: this start waits until they have moved")
            fcntl.flock(fd, fcntl.LOCK_SH)
    except OSError as exc:
        os.close(fd)
        logger.warning("The serving lock of the data directory cannot be taken: a restore cannot tell that this server runs", error=f"{type(exc).__name__}: {exc.strerror or exc}")
        return False
    _SERVING[key] = fd
    return True


# =============================================================================
# The startup steps
# =============================================================================


def apply_pending_restore(data_dir: Path | None = None, *, boot: Boot | None = None, now: datetime | None = None) -> RestoreState | None:
    """The startup step ``pending-restore``: apply the restore waiting, or undo the one a dead start left half done.

    Returns the state after the step, ``None`` when there is no restore. ``RestoreApplyError`` when an undo fails: the
    data directory is half restored, and the start must stop.
    """
    data_dir = data_dir or get_data_dir()
    if not _state_present(data_dir, "pending-restore"):
        return None
    boot = boot or current_boot()
    with _apply_lock(data_dir):
        state = _state_at_start(data_dir)
        if state is None:
            return None
        if state.status == "pending":
            return _swap(data_dir, state, boot, now or _now())
        if state.status in ("applying", "rolling_back"):
            # A start died during the swap or its undo: the data directory is half swapped, and only the undo makes it
            # whole again, whoever serves it.
            with _exclusive_serving_lock(data_dir) as served:
                if served:
                    logger.error("A server serves a data directory that a restore left half swapped: it is put back all the same, and that server must be restarted", stage_id=state.stage_id)
                return _undo(data_dir, state, state.reason or "swap_interrupted", now or _now())
        if state.status == "applied" and state.boot != boot:
            if state.boot is not None and boot_alive(state.boot):
                logger.error("A restore was applied by another server still running on this data directory: this start stops", stage_id=state.stage_id, pid=state.boot.pid)
                raise RestoreInUseError("Another LibreFolio server applied a restore on this data directory and still runs")
            with _exclusive_serving_lock(data_dir) as served:
                if served:
                    logger.error("A server serves this data directory: the restore a start before it applied is not undone under it, and this start stops", stage_id=state.stage_id)
                    raise RestoreInUseError("A LibreFolio server serves this data directory")
                return _undo(data_dir, state, "first_start_failed", now or _now())
        return state


def _swap(data_dir: Path, state: RestoreState, boot: Boot, now: datetime) -> RestoreState:
    """Move the checked copy into place, the live data into ``.restore/previous/``; the journal first. The serving lock
    is held exclusively from the checks to the last move."""
    with _exclusive_serving_lock(data_dir) as served:
        refused = _not_applicable(data_dir, state, now, served=served)
        if refused is not None:
            return refused
        _remove_leftovers(data_dir, None)
        copy = stage_data_dir(data_dir, state.stage_id)
        swap = [SwapEntry(name=name, live=os.path.lexists(data_dir / name), staged=os.path.lexists(copy / name)) for name in SWAPPED_FOLDERS]
        journal = state.model_copy(update={"status": "applying", "swap": swap, "boot": boot, "waiting": None, "reason": None})
        try:
            _write_state(data_dir, journal)
        except (OSError, BackupPathError) as exc:
            logger.error("The journal of the restore could not be written: nothing is restored, the restore still waits", error=str(exc))
            return state
        try:
            _move_into_place(data_dir, copy, swap)
            applied = journal.model_copy(update={"status": "applied", "applied_at": now})
            _write_state(data_dir, applied)
        except (OSError, BackupPathError) as exc:
            logger.error("The restore could not move the folders into place: the data of before is put back", error=str(exc))
            return _undo(data_dir, journal, "swap_failed", now)
        logger.warning("Restore applied: this start must complete for it to be kept", stage_id=state.stage_id, action=state.action, pid=boot.pid)
        return applied


def _blocked() -> bool:
    """Whether the hosting provider blocks the instance (``LIBREFOLIO_BLOCKED``). A value that cannot be read counts as
    blocked: the startup checks stop the server on it anyway, and a restore is never applied on a guess."""
    try:
        return instance_blocked()
    except ValueError:
        logger.error("LIBREFOLIO_BLOCKED cannot be read: the restore waits, as on a blocked instance")
        return True


def _not_applicable(data_dir: Path, state: RestoreState, now: datetime, *, served: bool) -> RestoreState | None:
    """Why a pending restore is not applied at this start, as the state then recorded; ``None`` when it can be."""
    if str(data_dir.resolve()) != state.data_dir:
        logger.warning("A restore waits for another data directory: it is not applied here", stage_id=state.stage_id)
        return _record(data_dir, state.model_copy(update={"waiting": "other_data_directory"}))
    if _blocked():
        logger.warning("The hosting provider blocked the instance: the restore waits until it is unblocked", stage_id=state.stage_id)
        return _record(data_dir, state.model_copy(update={"waiting": "instance_blocked"}))
    if served:
        logger.error("A server serves the data directory: the restore waits for a start of the whole server", stage_id=state.stage_id)
        return _record(data_dir, state.model_copy(update={"waiting": "server_running"}))
    if _lock_held(lock_path(data_dir)):
        logger.error("A backup runs on the data directory: the restore waits for the next start", stage_id=state.stage_id)
        return _record(data_dir, state.model_copy(update={"waiting": "backup_running"}))
    if not _copy_usable(data_dir, state.stage_id):
        logger.error("The checked copy of the restore is gone or changed: nothing is restored", stage_id=state.stage_id)
        return _record(data_dir, state.model_copy(update={"status": "rolled_back", "reason": "stage_missing", "finished_at": now, "waiting": None}))
    unmovable = [name for name in SWAPPED_FOLDERS if os.path.lexists(data_dir / name) and not is_plain_dir(data_dir / name)]
    if unmovable:
        logger.error("A folder of the data directory is a link or a file: the restore cannot move it, nothing is restored", folders=unmovable)
        return _record(data_dir, state.model_copy(update={"status": "rolled_back", "reason": "swap_failed", "finished_at": now, "waiting": None}))
    return None


def _move_into_place(data_dir: Path, copy: Path, swap: list[SwapEntry]) -> None:
    """The moves of the swap, in order: each live folder to ``previous/``, then the copy's in its place, with its mode."""
    previous = ensure_private_dir(previous_dir(data_dir), data_dir)
    for entry in swap:
        live = data_dir / entry.name
        mode = stat.S_IMODE(live.lstat().st_mode) if entry.live else None
        if entry.live:
            _move(live, previous / entry.name)
        if entry.staged:
            _move(copy / entry.name, live)
            if mode is not None:
                with contextlib.suppress(OSError):
                    os.chmod(live, mode)
    for folder in (data_dir, previous, copy):
        _fsync_dir(folder)


def _undo(data_dir: Path, state: RestoreState, reason: RollbackReason, now: datetime) -> RestoreState:
    """Put the data of before back, from what the files say; the restored data set aside in ``.restore/failed/``."""
    state = _record(data_dir, state.model_copy(update={"status": "rolling_back", "reason": reason}))
    copy = stage_data_dir(data_dir, state.stage_id)
    previous = previous_dir(data_dir)
    failed = failed_dir(data_dir)
    try:
        for entry in reversed(state.swap):
            live = data_dir / entry.name
            if entry.live:
                if os.path.lexists(previous / entry.name):
                    if os.path.lexists(live):
                        _set_aside(live, failed / entry.name, data_dir)
                    _move(previous / entry.name, live)
            elif entry.staged and not os.path.lexists(copy / entry.name) and os.path.lexists(live):
                _set_aside(live, failed / entry.name, data_dir)
        _fsync_dir(data_dir)
    except (OSError, BackupPathError) as exc:
        logger.critical("The data directory is half restored: the restore could not be undone, and LibreFolio does not start on it", reason=reason, error=str(exc))
        raise RestoreApplyError("The data directory is half restored: the undo of the restore failed") from exc
    with contextlib.suppress(OSError):
        if is_plain_dir(previous) and not any(previous.iterdir()):
            previous.rmdir()
    logger.error("Restore rolled back: the data of before is back", reason=reason, stage_id=state.stage_id)
    return _record(data_dir, state.model_copy(update={"status": "rolled_back", "finished_at": now}))


def _set_aside(path: Path, target: Path, data_dir: Path) -> None:
    """Move what stands at ``path`` to ``target`` in ``.restore/failed/``, an older one there removed first."""
    ensure_private_dir(target.parent, data_dir)
    _remove_path(target)
    _move(path, target)


def finish_pending_restore(data_dir: Path | None = None, *, boot: Boot | None = None, now: datetime | None = None) -> RestoreState | None:
    """The startup step ``restore-commit``: the first start on the restored data completed; end every session, keep the
    restore, remove the data of before. Then, and at every later start, remove what a finished restore leaves."""
    data_dir = data_dir or get_data_dir()
    if not _state_present(data_dir, "restore-commit"):
        return None
    boot = boot or current_boot()
    with _apply_lock(data_dir):
        state = _state_at_start(data_dir)
        if state is None:
            return None
        if state.status == "applied" and state.boot != boot:
            logger.error("A restore applied by another start reaches this start's commit: it stops rather than serve uncommitted data", stage_id=state.stage_id)
            raise RestoreInUseError("The restore found here was applied by another start of LibreFolio")
        if state.status == "applied" and state.boot == boot:
            now = now or _now()
            value, revoked = _close_the_way_in(data_dir, now)
            state = state.model_copy(update={"status": "committed", "finished_at": now, "session_version": value})
            _write_state(data_dir, state)
            logger.warning("Restore committed: every session ended, the backup's one-time links revoked", stage_id=state.stage_id, session_version=value, links_revoked=revoked)
        if state.status in ("committed", "rolled_back"):
            _remove_leftovers(data_dir, state.stage_id)
        return state


def _close_the_way_in(data_dir: Path, now: datetime) -> tuple[int, int]:
    """Close in the restored database every way in that was open before the restore, in one transaction; the session
    version given to every account, and how many one-time links were revoked.

    - Every account's session version becomes the restore time in milliseconds, or one past the largest value either
      database holds when the clock is behind it: every session token issued before, by either database, is refused
      (decision 40). A time, not a counter: a password change afterwards still adds one.
    - Every one-time link still live in the backup (not consumed, not revoked: invitation, password reset, email
      verification, admin setup) is revoked at the restore time, as ``token_service.revoke_tokens`` revokes one.
    """
    restore_ms = int(now.timestamp() * 1000)
    before = _largest_session_version(previous_dir(data_dir) / DATABASE_ENTRY)
    # As SQLAlchemy stores a datetime in SQLite: UTC, without offset.
    revoked_at = now.astimezone(UTC).replace(tzinfo=None).isoformat(sep=" ", timespec="microseconds")
    database = database_path(data_dir)
    with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=rw", uri=True, timeout=30)) as conn:
        conn.execute("PRAGMA busy_timeout = 30000")
        restored = int(conn.execute("SELECT COALESCE(MAX(session_version), 0) FROM users").fetchone()[0])
        value = max(restore_ms, restored + 1, before + 1)
        with conn:
            conn.execute("UPDATE users SET session_version = ?", (value,))
            revoked = conn.execute("UPDATE account_tokens SET revoked_at = ? WHERE consumed_at IS NULL AND revoked_at IS NULL", (revoked_at,)).rowcount
    return value, revoked


def _largest_session_version(database: Path) -> int:
    """The largest session version of a database, read-only; 0 when it cannot be read."""
    try:
        if not stat.S_ISREG(database.lstat().st_mode):
            return 0
        with closing(sqlite3.connect(f"{database.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            return int(conn.execute("SELECT COALESCE(MAX(session_version), 0) FROM users").fetchone()[0])
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return 0
