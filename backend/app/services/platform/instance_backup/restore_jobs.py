"""The restore's background work for the API (lot B2b): the archive an administrator uploads, and its check on a copy
(``staging.py``), run in a thread and followed through a state file, so that every worker of the server sees one check.

- ``UploadWriter`` receives an archive in pieces into ``.restore/upload/``: never beyond the limit the hosting provider
  set (``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``, decision 43), never past the free space. A finished upload replaces the
  previous one, unless a check is reading it.
- ``start_check`` checks an upload in the background, one check at a time: the lock of the checks is taken by the
  request, so that a second start is refused at once, and handed to the thread, which releases it only once the
  check's end is recorded. ``read_check`` follows it; a check whose server stopped reads as ``restore_interrupted``.
  A secure backup's password is checked in the request (lot B4): a missing or wrong one is refused at once and keeps
  the upload, for another try; the thread gets the key it gives, never the password.
- ``remove_check`` drops an ended check with its copy; ``prune`` drops what is older than ``STAGE_LIFETIME``, and
  ends a check its stopped server left running. At every start (lot B4b), ``remove_stray_decrypted_archives`` also
  removes the decrypted archive a check killed outright left in its copy.
- ``confirm_check`` confirms the restore of a finished check (lot B3, ``apply.py``): its copy then waits for the next
  start, and neither ``remove_check`` nor ``prune`` removes it until that restore is finished.

The upload is removed as soon as its check ends: the copy (``.restore/stage/<stage id>/``) is what a restore uses.
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import threading
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from backend.app.config import get_data_dir
from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup.apply import EVERY_STAGE, ConfirmedVia, RestoreNotRestorableError, RestoreState, confirm_restore, protected_stage
from backend.app.services.platform.instance_backup.envelope import EnvelopeKey, is_envelope, read_header, unlock
from backend.app.services.platform.instance_backup.jobs import _lock_held, _RunLock, out_of_space
from backend.app.services.platform.instance_backup.paths import (
    STAGE_DECRYPTED_ARCHIVE,
    STAGE_LOCK_FILE,
    BackupPathError,
    NotRegularFileError,
    check_state_path,
    checks_dir,
    ensure_private_dir,
    is_job_id,
    is_plain_dir,
    read_regular_file,
    restore_dir,
    stage_dir,
    stages_dir,
    upload_path,
    uploads_dir,
)
from backend.app.services.platform.instance_backup.staging import STAGE_LIFETIME, StagePhase, StagingBusyError, StagingError, new_stage_id, remove_stage, stage_archive

logger = get_logger(__name__)

#: Room an upload leaves free beyond its declared size.
_SPACE_MARGIN = 64 * 1024 * 1024
#: A running check writes its state at every change of phase, and otherwise at most this often (seconds).
_STATE_INTERVAL = 1.0
_PARTIAL_SUFFIX = ".part"

CheckStatus = Literal["running", "done", "failed"]
#: Who started a check (L3): an administrator's session, the command line, or a hosting panel, which sees only its own.
CheckOrigin = Literal["admin", "cli", "panel"]


class UploadTooLargeError(RuntimeError):
    """The archive is larger than the limit the hosting provider set (``limit_bytes``)."""

    def __init__(self, limit_bytes: int):
        super().__init__(f"The archive is larger than {limit_bytes} bytes")
        self.limit_bytes = limit_bytes


class UploadNoSpaceError(RuntimeError):
    """The archive does not fit in the free space of the data directory."""


class UploadEmptyError(RuntimeError):
    """The upload carried no byte."""


class UploadNotFoundError(LookupError):
    """No finished upload has this id: never received, replaced, or already checked."""


class PasswordRequiredError(RuntimeError):
    """The upload is a secure backup, and no password came with it: the upload stays for another try."""


class CheckNotFoundError(LookupError):
    """No check has this id."""


class CheckRunningError(RuntimeError):
    """The check still runs: it cannot be removed yet."""


class CheckPendingError(RuntimeError):
    """A restore waits to apply the check's copy, or is being applied: the copy cannot be removed."""


@dataclass(frozen=True)
class RestoreUploaded:
    """A finished upload: the id to check it with, its size, and its kind: ``envelope`` for a secure backup."""

    upload_id: str
    size: int
    kind: Literal["zip", "envelope"] = "zip"


@dataclass(frozen=True)
class RestoreCheck:
    """The state of one check, as its state file keeps it."""

    stage_id: str
    upload_id: str
    status: CheckStatus
    phase: StagePhase | None
    done_bytes: int
    total_bytes: int
    created_at: datetime
    finished_at: datetime | None = None
    error_code: str | None = None
    #: Who started it (L3); a state written before reads ``admin``, the only caller then.
    origin: CheckOrigin = "admin"


def _now() -> datetime:
    return datetime.now(UTC)


# =============================================================================
# The upload
# =============================================================================


class UploadWriter:
    """An archive received in pieces: ``write`` each one, then ``finish``; ``abort`` leaves nothing behind.

    ``max_bytes`` is the limit (``None``: no limit); ``declared`` the size the request announced, checked against the
    limit and the free space before a byte is written. A full disk or quota, from the creation of its folder to the
    end of the file, raises ``UploadNoSpaceError`` (B-30).
    """

    def __init__(self, data_dir: Path, *, max_bytes: int | None, declared: int | None):
        if max_bytes is not None and declared is not None and declared > max_bytes:
            raise UploadTooLargeError(max_bytes)
        try:
            folder = ensure_private_dir(uploads_dir(data_dir), data_dir)
        except OSError as exc:
            if out_of_space(exc):
                raise UploadNoSpaceError("Not enough free space for the archive") from None
            raise
        if declared is not None and shutil.disk_usage(folder).free < declared + _SPACE_MARGIN:
            raise UploadNoSpaceError("Not enough free space for the archive")
        self._data_dir = data_dir
        self._max_bytes = max_bytes
        self.upload_id = new_stage_id()
        self._final = upload_path(data_dir, self.upload_id)
        self._partial = self._final.with_name(self._final.name + _PARTIAL_SUFFIX)
        try:
            self._fd: int | None = os.open(self._partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
        except OSError as exc:
            if out_of_space(exc):
                raise UploadNoSpaceError("Not enough free space for the archive") from None
            raise
        self.size = 0

    def write(self, data: bytes) -> None:
        """Append ``data``; ``UploadTooLargeError`` before a byte past the limit is written."""
        if self._fd is None:
            raise RuntimeError("the upload is closed")
        if self._max_bytes is not None and self.size + len(data) > self._max_bytes:
            raise UploadTooLargeError(self._max_bytes)
        view = memoryview(data)
        try:
            while view:
                view = view[os.write(self._fd, view) :]
        except OSError as exc:
            if out_of_space(exc):
                raise UploadNoSpaceError("Not enough free space for the archive") from None
            raise
        self.size += len(data)

    def finish(self) -> RestoreUploaded:
        """Keep the archive under its id, and drop the uploads it replaces. ``UploadEmptyError`` for an empty body;
        ``UploadNoSpaceError`` when the disk reports itself full only now, as a network file system or a quota may, at
        ``fsync`` or ``close``."""
        if self._fd is None:
            raise RuntimeError("the upload is closed")
        if self.size == 0:
            self.abort()
            raise UploadEmptyError("The upload carried no byte")
        # The descriptor stops being the writer's before it is closed: ``abort`` never closes it twice, not even after
        # a ``close`` that failed, which releases it all the same.
        fd, self._fd = self._fd, None
        try:
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            os.replace(self._partial, self._final)
        except OSError as exc:
            if out_of_space(exc):
                raise UploadNoSpaceError("Not enough free space for the archive") from None
            raise
        _remove_replaced_uploads(self._data_dir, keep=self.upload_id)
        kind: Literal["zip", "envelope"] = "envelope" if is_envelope(self._final) else "zip"
        logger.info("Backup archive received for a restore", upload_id=self.upload_id, size=self.size, kind=kind)
        return RestoreUploaded(upload_id=self.upload_id, size=self.size, kind=kind)

    def abort(self) -> None:
        """Drop what was received; nothing when already finished or aborted."""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        self._partial.unlink(missing_ok=True)


def _remove_replaced_uploads(data_dir: Path, *, keep: str) -> None:
    """Remove the finished uploads other than ``keep``, but the one a running check reads."""
    if not _plain_folders(data_dir, uploads_dir(data_dir)):
        return
    reading = {check.upload_id for check in _checks(data_dir) if check.status == "running"}
    for path in uploads_dir(data_dir).iterdir():
        if path.name != keep and is_job_id(path.name) and path.name not in reading:
            path.unlink(missing_ok=True)


# =============================================================================
# The check
# =============================================================================


def start_check(upload_id: str, *, data_dir: Path | None = None, password: str | None = None, max_unpacked: int | None = None, origin: CheckOrigin = "admin") -> RestoreCheck:
    """Check the upload ``upload_id`` in the background, on a copy; its first state.

    ``UploadNotFoundError`` when there is no such upload, ``StagingBusyError`` while another check runs,
    ``BackupPathError`` when ``.restore`` is not a plain folder. A secure backup needs its ``password``, checked here:
    ``PasswordRequiredError`` without one, ``EnvelopeError`` (``wrong_password``, ``envelope_damaged``,
    ``envelope_unsupported``) when it does not open it; the upload then stays, and no check starts. A zip ignores it.
    ``max_unpacked``: the most bytes the archive may unpack to (B-35, ``staging.stage_archive``); ``None``: no limit.
    ``origin``: who starts it (L3), kept in its state.
    """
    data_dir = data_dir or get_data_dir()
    if not is_job_id(upload_id):
        raise UploadNotFoundError("No uploaded archive has this id")
    for folder in (stages_dir(data_dir), checks_dir(data_dir), uploads_dir(data_dir)):
        ensure_private_dir(folder, data_dir)
    prune(data_dir)
    if not upload_path(data_dir, upload_id).is_file():
        raise UploadNotFoundError("No uploaded archive has this id")
    lock = _RunLock(stages_dir(data_dir) / STAGE_LOCK_FILE)
    if not lock.try_acquire():
        raise StagingBusyError("Another archive is being checked")
    try:
        key = _envelope_key(upload_path(data_dir, upload_id), password)
        phase: StagePhase = "decrypting" if key is not None else "checking"
        check = RestoreCheck(stage_id=new_stage_id(), upload_id=upload_id, status="running", phase=phase, done_bytes=0, total_bytes=0, created_at=_now(), origin=origin)
        _write_state(data_dir, check)
        threading.Thread(target=_run_check, args=(data_dir, check, lock, key, max_unpacked), name=f"restore-check-{check.stage_id[:8]}", daemon=True).start()
    except BaseException:
        lock.release()
        raise
    return check


def _envelope_key(upload: Path, password: str | None) -> EnvelopeKey | None:
    """The key of a secure backup's upload, for its password; ``None`` for a zip, whatever the password. Its header is
    read first: an envelope that cannot be opened asks for no password."""
    if not is_envelope(upload):
        return None
    read_header(upload)
    if password is None:
        raise PasswordRequiredError("The backup is protected by a password")
    return unlock(upload, password)


def _run_check(data_dir: Path, check: RestoreCheck, lock: _RunLock, key: EnvelopeKey | None = None, max_unpacked: int | None = None) -> None:
    """The thread of one check: the copy, its state along the way, its end; the upload removed in any case."""
    upload = upload_path(data_dir, check.upload_id)
    current = check
    written = time.monotonic()

    def progress(phase: StagePhase, done: int, total: int) -> None:
        nonlocal current, written
        moved = phase != current.phase
        # done_bytes and total_bytes measure the decryption, then the unpacking; the later phases count other things, and
        # keep its figures.
        current = replace(current, phase=phase, done_bytes=done, total_bytes=total) if phase in ("decrypting", "unpacking") else replace(current, phase=phase)
        if moved or time.monotonic() - written >= _STATE_INTERVAL:
            _write_state(data_dir, current)
            written = time.monotonic()

    error_code: str | None = None
    try:
        stage_archive(upload, data_dir, stage_id=check.stage_id, progress=progress, lock=lock, key=key, max_unpacked=max_unpacked)
    except StagingError as exc:
        error_code = exc.code
    except BackupPathError:
        error_code = "restore_folder_unusable"
    except Exception:
        logger.exception("A restore check failed unexpectedly", stage_id=check.stage_id)
        error_code = "stage_failed"
    finally:
        _remove_upload(data_dir, check.upload_id)
    status: CheckStatus = "failed" if error_code else "done"
    try:
        _write_state(data_dir, replace(current, status=status, phase=None, finished_at=_now(), error_code=error_code))
    finally:
        # Released only now: a reader that finds the lock free must find the check's end already written.
        lock.release()


def read_check(stage_id: str, *, data_dir: Path | None = None) -> RestoreCheck:
    """The state of a check. ``CheckNotFoundError`` when there is none; a check whose server stopped is ``failed``."""
    data_dir = data_dir or get_data_dir()
    if not is_job_id(stage_id):
        raise CheckNotFoundError("No check has this id")
    check = _read_state(data_dir, stage_id)
    if check is None:
        raise CheckNotFoundError("No check has this id")
    if check.status == "running" and not _a_check_runs(data_dir):
        # The check may have ended between the two reads: only a state still running after the probe was left behind.
        again = _read_state(data_dir, stage_id)
        if again is None:
            raise CheckNotFoundError("No check has this id")
        if again.status != "running":
            return again
        check = replace(again, status="failed", phase=None, finished_at=_now(), error_code="restore_interrupted")
        remove_stage(data_dir, stage_id)
        _remove_upload(data_dir, check.upload_id)
        _write_state(data_dir, check)
    return check


def running_check(upload_id: str, *, data_dir: Path | None = None) -> RestoreCheck | None:
    """The check of the upload ``upload_id`` that still runs, as ``read_check`` judges it; ``None`` otherwise. A caller
    that sends the same start again (a hosting panel retrying, L3) is answered with it instead of a refusal."""
    data_dir = data_dir or get_data_dir()
    if not is_job_id(upload_id):
        return None
    for check in _checks(data_dir):
        if check.upload_id == upload_id and check.status == "running":
            try:
                current = read_check(check.stage_id, data_dir=data_dir)
            except CheckNotFoundError:
                continue
            if current.status == "running":
                return current
    return None


def remove_check(stage_id: str, *, data_dir: Path | None = None) -> None:
    """Remove an ended check, its copy and its upload. ``CheckNotFoundError``, or ``CheckRunningError`` while it runs."""
    data_dir = data_dir or get_data_dir()
    check = read_check(stage_id, data_dir=data_dir)
    if check.status == "running":
        raise CheckRunningError("The check still runs")
    protected = protected_stage(data_dir)
    # An unreadable state protects every copy still there: which one a restore needs is not known (B-33).
    if protected == check.stage_id or (protected == EVERY_STAGE and os.path.lexists(stage_dir(data_dir, check.stage_id))):
        raise CheckPendingError("A restore waits to apply this copy")
    _remove(data_dir, check)


def confirm_check(stage_id: str, *, confirmed_by: str, confirmed_via: ConfirmedVia = "admin", data_dir: Path | None = None) -> RestoreState:
    """Confirm the restore of a finished check: the next start of the server applies its copy (``apply.py``).

    ``BackupPathError`` when ``.restore`` is a link or a file: the confirmation writes there, and a link is refused rather
    than followed (behind one, a check is not found by the routes that only read). Then ``CheckNotFoundError``;
    ``CheckRunningError`` while it runs; ``RestoreNotRestorableError`` when it refused the archive; then the errors of
    ``apply.confirm_restore``.
    """
    data_dir = data_dir or get_data_dir()
    if os.path.lexists(restore_dir(data_dir)) and not is_plain_dir(restore_dir(data_dir)):
        raise BackupPathError(restore_dir(data_dir))
    check = read_check(stage_id, data_dir=data_dir)
    if check.status == "running":
        raise CheckRunningError("The check still runs")
    if check.status == "failed":
        raise RestoreNotRestorableError("The check refused the archive")
    return confirm_restore(stage_id, confirmed_by=confirmed_by, confirmed_via=confirmed_via, data_dir=data_dir)


def prune(data_dir: Path, now: datetime | None = None) -> int:
    """Remove the ended checks and their copies older than ``STAGE_LIFETIME``, and the uploads and copies left that old;
    how many checks it ended as ``restore_interrupted``.

    While no check runs, a check still recorded as running was left by a stopped server: it is ended as
    ``restore_interrupted`` first, its copy removed. Nothing is removed through a link: a folder that is not a plain
    one is left alone. The copy of a restore not finished yet (``apply.protected_stage``) is kept however old, with its
    check: the restore needs it at the next start.
    """
    if not is_plain_dir(restore_dir(data_dir)):
        return 0
    cutoff = (now or _now()) - STAGE_LIFETIME
    idle = not _a_check_runs(data_dir)
    protected = protected_stage(data_dir)
    recorded, interrupted = _prune_checks(data_dir, cutoff, idle=idle, protected=protected)
    if idle:
        _prune_unrecorded(data_dir, cutoff, recorded if protected is None else recorded | {protected}, keep_stages=protected == EVERY_STAGE)
    return interrupted


def _prune_checks(data_dir: Path, cutoff: datetime, *, idle: bool, protected: str | None = None) -> tuple[set[str], int]:
    """End the checks a stopped server left running (when ``idle``), remove the ended ones older than ``cutoff`` but the
    ``protected`` one; the ids of every check found, and how many it ended."""
    checks = _checks(data_dir)
    interrupted = 0
    for check in checks:
        # An unreadable state of the restore protects every copy, with its check (B-33).
        if protected in (check.stage_id, EVERY_STAGE):
            continue
        if check.status == "running" and idle:
            try:
                check = read_check(check.stage_id, data_dir=data_dir)
            except CheckNotFoundError:
                continue
            if check.status == "failed" and check.error_code == "restore_interrupted":
                interrupted += 1
        if check.status != "running" and (check.finished_at or check.created_at) < cutoff:
            _remove(data_dir, check)
    return {check.stage_id for check in checks}, interrupted


def _prune_unrecorded(data_dir: Path, cutoff: datetime, recorded: set[str], *, keep_stages: bool = False) -> None:
    """Remove what no check records, older than ``cutoff``: uploads never checked, the copies of a command-line check
    stopped before its end, and the states in ``checks/`` no check could be read from, or half written (B-54)."""
    for folder, keep in ((uploads_dir(data_dir), set()), (stages_dir(data_dir), recorded)):
        if keep_stages and folder == stages_dir(data_dir):
            continue
        if is_plain_dir(folder):
            for path in folder.iterdir():
                if is_job_id(path.name.removesuffix(_PARTIAL_SUFFIX)) and path.name not in keep and _older_than(path, cutoff):
                    _remove_path(path)
    if _plain_folders(data_dir, checks_dir(data_dir)):
        for path in checks_dir(data_dir).iterdir():
            name = path.name.removesuffix(_PARTIAL_SUFFIX)
            stage_id = name.removesuffix(".json")
            if name == f"{stage_id}.json" and is_job_id(stage_id) and stage_id not in recorded and _older_than(path, cutoff):
                _remove_path(path)


def _older_than(path: Path, cutoff: datetime) -> bool:
    return datetime.fromtimestamp(path.lstat().st_mtime, UTC) < cutoff


def _remove_path(path: Path) -> None:
    """Remove a file, or a folder with its content; a link is removed, never followed."""
    if is_plain_dir(path):
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def _remove(data_dir: Path, check: RestoreCheck) -> None:
    remove_stage(data_dir, check.stage_id)
    _remove_upload(data_dir, check.upload_id)
    if _plain_folders(data_dir, checks_dir(data_dir)):
        check_state_path(data_dir, check.stage_id).unlink(missing_ok=True)
    logger.info("Restore check removed", stage_id=check.stage_id)


def _a_check_runs(data_dir: Path) -> bool:
    """Whether some process holds the lock of the checks: a running state without it was left by a stopped server."""
    return _lock_held(stages_dir(data_dir) / STAGE_LOCK_FILE)


def remove_stray_decrypted_archives(data_dir: Path) -> int:
    """Remove the decrypted archives runs killed outright left in the copies, while no check runs; how many (lot B4b).

    A check decrypts a secure backup into its copy (``archive.zip``) and removes it once unpacked, or with the whole copy
    on any error, always under the lock of the checks: with that lock free, one still there is what a run killed outright
    left, and it holds the source instance's key. Only a regular file goes; a link or a folder of that name, and the rest
    of the copy, stay (``prune`` removes the copy at its age).
    """
    if not _plain_folders(data_dir, stages_dir(data_dir)) or _a_check_runs(data_dir):
        return 0
    removed = 0
    for stage in stages_dir(data_dir).iterdir():
        if not is_job_id(stage.name) or not is_plain_dir(stage):
            continue
        # The decrypted archive, or its part when the run was killed while decrypting: both hold clear data.
        for name in (STAGE_DECRYPTED_ARCHIVE, STAGE_DECRYPTED_ARCHIVE + _PARTIAL_SUFFIX):
            archive = stage / name
            try:
                if not stat.S_ISREG(archive.lstat().st_mode):
                    continue
                archive.unlink()
            except FileNotFoundError:
                continue
            removed += 1
    return removed


# =============================================================================
# The state files
# =============================================================================


def _plain_folders(data_dir: Path, folder: Path) -> bool:
    """Whether ``.restore`` and ``folder`` inside it are plain folders: only then is anything of a check read, written or
    removed there. Behind a link, a check is not found, and nothing is written or removed through it."""
    return is_plain_dir(restore_dir(data_dir)) and is_plain_dir(folder)


def _remove_upload(data_dir: Path, upload_id: str) -> None:
    if _plain_folders(data_dir, uploads_dir(data_dir)):
        upload_path(data_dir, upload_id).unlink(missing_ok=True)


def _write_state(data_dir: Path, check: RestoreCheck) -> None:
    """Write the state of a check atomically: a reader sees the old state or the new one, never half of one.

    ``BackupPathError`` while ``.restore`` or ``checks/`` is not a plain folder: nothing is written through a link."""
    if not _plain_folders(data_dir, checks_dir(data_dir)):
        raise BackupPathError(checks_dir(data_dir))
    target = check_state_path(data_dir, check.stage_id)
    partial = target.with_name(target.name + _PARTIAL_SUFFIX)
    record = {key: value.isoformat() if isinstance(value, datetime) else value for key, value in asdict(check).items()}
    fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(record, handle)
    os.replace(partial, target)


def _read_state(data_dir: Path, stage_id: str) -> RestoreCheck | None:
    """The state of the check ``stage_id``. ``None`` when there is none, or none this module can read: a content that is
    no check's state (a date without a time zone included), a folder, a link or a special file in its place, no
    permission to read it (B-50, B-55). Any other ``OSError``, a transient one, as it came: a «no check» would make the
    tab forget a check it follows, where an error lets it try again."""
    if not _plain_folders(data_dir, checks_dir(data_dir)):
        return None
    try:
        record = json.loads(read_regular_file(check_state_path(data_dir, stage_id)).decode("utf-8"))
        # A document that is not a JSON object is no check's state, like the other unreadable ones (B-50).
        if not isinstance(record, dict):
            return None
        for key in ("created_at", "finished_at"):
            if record.get(key) is not None:
                moment = datetime.fromisoformat(record[key])
                if moment.tzinfo is None:
                    return None  # every state this module writes has one: prune could not compare it (B-55)
                record[key] = moment
        return RestoreCheck(**record)
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError, NotRegularFileError, ValueError, TypeError):
        return None


def _checks(data_dir: Path) -> list[RestoreCheck]:
    folder = checks_dir(data_dir)
    if not _plain_folders(data_dir, folder):
        return []
    found = (_read_state(data_dir, path.stem) for path in folder.iterdir() if path.suffix == ".json" and is_job_id(path.stem))
    return [check for check in found if check is not None]
