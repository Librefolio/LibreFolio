"""
Restoring a backup, the check of an archive through the API (workstream B, lot B2b): the four routes of
``/api/v1/backup/restore``.

Under test: ``backend/app/api/v1/backup/restore.py`` (the routes), ``backend/app/services/platform/instance_backup/
restore_jobs.py`` (the upload, the check in a thread followed through a state file, ``prune``),
``backend/app/config/backup.py`` (``backup_max_upload_mb``) and the ``Restore*`` models of ``backend/app/schemas/backup.py``.

(a) ``PUT /backup/restore/upload``, the archive as the raw body: 201 with a new id (32 lowercase hex), its size and its
    kind (``zip``; ``envelope`` for a file that starts with ``LFBK``, lot B4), the bytes kept whole in
    ``.restore/upload/<id>`` (0600, its folders 0700), written in pieces of 1 MiB off the event loop.
    The limit (``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB``, decision 43): a ``Content-Length`` above it is 413
    ``backup_too_large`` with ``limit_mb`` before anything is created, whatever the body; a body without one is refused at
    the piece that passes it, and what was written of it removed; the limit itself is received. Unset: no limit on a
    self-hosted instance, 500 MB in the managed profile; the variable wins over the profile. A value that cannot be read:
    503 ``backup_upload_unavailable``, nothing written, one error logged naming the variable. No room for the declared
    size (``shutil.disk_usage`` replaced), or a disk that fills during the upload: 507 ``backup_no_space``, no file left.
    B-30: a full disk or a quota (``ENOSPC``, ``EDQUOT``) where a first upload creates ``.restore/upload``, or at the end
    of the upload (its ``fsync``, or its ``close``, where a network file system reports it), is 507 ``backup_no_space``
    too: no partial and no final file left, the partial's descriptor closed exactly once, a failing ``close`` included.
    Any other failure to write the archive (a write, its ``fsync`` or its rename failing): 500 ``backup_upload_failed``,
    one error logged, no file left, neither the system's words nor a path in the answer. An empty body: 400
    ``backup_upload_empty``; a client that leaves before the end: 400 ``backup_upload_incomplete``, no partial left. A
    finished upload replaces the previous one, but the one a running check reads. ``.restore`` or ``.restore/upload`` a
    link (dangling too) or a file: 500 ``restore_folder_unusable``, nothing written through it, no path in the answer.
(b) ``POST /backup/restore/stage`` → 202, the check running; ``GET /backup/restore/stage/{id}`` → its end: ``done`` with
    the report mapped from staging's (a backup at the head; an older one, upgraded, with its migrations and warnings;
    one without an active administrator, not restorable), or ``failed`` with the code of the refusal (staging's, or
    ``stage_failed`` / ``restore_folder_unusable`` when the check fails otherwise). ``done_bytes`` and ``total_bytes``
    follow the unpacking only: the later phases and the end keep its figures. The upload is removed when its check ends,
    the copy kept until it is dropped; ``DELETE`` → 204, then 404. Unknown ids: 404 (``backup_upload_not_found``,
    ``restore_stage_not_found``); a malformed upload id: 422, from the pattern of ``RestoreStageRequest`` (the route never
    runs). Every code a check can end with is one ``RestoreStage.error_code`` declares, and no other. The end of a check
    is written before its lock is let go, and a poll judges a running state only on what it reads once it found the lock
    free: a poll that comes as a check ends never reads it as interrupted. B-30, a check that cannot start (its folders,
    its first state): a full disk or a quota is 507 with the check's own code, ``no_space``, and one warning; any other
    ``OSError`` 500 ``stage_failed`` and one error naming its type and the system's words, which stay out of the answer.
    Either way the upload is kept, no check is recorded, and the lock is let go: the next start answers 202.
(c) One check at a time, the lock taken by the request: while it is held (by the test, or by a check still running) a
    start is 409 ``restore_busy`` and consumes nothing; a running check cannot be dropped (409 ``restore_stage_running``).
    A running state nobody holds the lock for (its server stopped) reads as failed ``restore_interrupted``, its copy and
    its upload removed, at the next poll or drop, or at the next ``prune``. ``prune``, which every start runs before it
    looks for its upload: the ended checks older than 24 hours with their copies (exactly 24 hours is kept), never a
    running check; while no check runs, what no check records and is older than 24 hours (uploads, finished or partial,
    and copies), nothing of it while one runs, nor anything that is not named by an id. Nothing is pruned through a link:
    ``.restore``, ``checks/`` or ``stage/`` a link, the link's target is left as it was; a link in place of ``stage/``,
    ``checks/`` or ``upload/`` at a start is 500 ``restore_folder_unusable``, and nothing is pruned.
(d) Administrators only: a regular user gets 403 from each route, and nothing is received, started, read or dropped.
    None of the four routes is allowed on a blocked instance. OpenAPI: the upload's body is ``application/octet-stream``
    binary and required, the four operations carry the ``Backup & Export`` tag and document their answers; the stage's
    start documents 507 (code ``no_space``), and its 500 names ``stage_failed`` beside ``restore_folder_unusable``.
(e) ``backup_max_upload_mb()``: unset or blank, 0 self-hosted and 500 managed; a whole number of ASCII digits, spaces
    around allowed, wins over the profile; anything else raises ``BackupConfigError`` ``BACKUP_MAX_UPLOAD_MB_INVALID``,
    naming the variable. The managed value is the entry of H's profile table, read at each call (a guard of lot B4, which
    H-37 extended: the entry removed raises, never gives 0, below). An entry of that table of another type than the
    code's default (``"500"``, ``None``, ``500.0``, ``True``), on which H's ``profile_default`` raises
    ``ProfileDefaultError`` (H-27), is a limit that cannot be read, as a variable that cannot be (B-21: the routes catch
    H's error as they catch ``BackupConfigError``, never a plain 500): the upload 503 ``backup_upload_unavailable``,
    nothing written; ``GET /backup/restore/status`` (lot B3's route) 200 with ``upload_limit_mb`` null; each with one
    error logged, the line of a limit that cannot be read, naming the variable. A missing managed entry is the same: H's
    ``profile_default`` raises ``ProfileDefaultError`` for a variable a profile other than ``selfhosted`` does not list
    (H-37; E, R13-SEC7: fail closed, where the code's own 0 would be no limit at all), so the upload is 503 and the
    status null, never no limit.
(f) Found while writing the second round, each fixed since; what each pins now: an upload whose file cannot be created
    (a folder that cannot be written) is 500 ``backup_upload_failed``, as the same failure a byte later; a drop through a
    link in place of ``.restore`` or ``checks/`` removes and changes nothing in the link's target (behind a link a check
    is not found); a check removed by another request while a poll probes its lock is not found, never still running.
(g) The ledger's control totals (lot B-13): a done check's report carries ``control_totals`` (``same`` for a backup as
    recorded; ``changed`` with its differences, each with its six fields, and the warning ``control_totals_changed``;
    ``absent`` and ``other_version`` without a warning; ``unreadable`` with ``control_totals_unreadable``),
    ``control_totals_differences`` and ``control_totals_differences_count``, restorable all the same; a ``report.json``
    written before lot B-13 still reads, its totals ``absent`` (§7.6). OpenAPI documents the three fields, the five
    statuses, the two warnings and ``RestoreTotalsDifference``.
(h) B-35, the restore limit: ``LIBREFOLIO_BACKUP_MAX_RESTORE_MB`` caps what an archive declares unpacked (its manifest's
    sizes, which are its zip headers'), in MiB, 0 for none; unset, none self-hosted, and in the managed profile 8 times
    the upload limit. An archive declaring more ends its check ``failed`` with ``unpacked_too_large``, a code
    ``RestoreStage`` declares (the GET answers 200, never a 500): nothing unpacked (``done_bytes`` and ``total_bytes``
    stay 0), its stage removed, its upload consumed, the lock free. Exactly at the cap, or below, it is checked as
    before: the cap counts whole MiB and refuses only what is above it. Managed with an upload limit of 1 MB, the cap is
    8 MiB: one byte past it is refused, at it and below checked; an explicit 0 lifts it. A limit that cannot be read
    (the variable, or, unset in the managed profile, the upload limit it is a multiple of, its variable or H's table
    entry): 503 ``backup_restore_unavailable``, «The restore limit of this instance cannot be read», one error logged
    naming the variable, neither the value nor a path in the answer; no check started, the upload kept, and the same
    start, the limit readable, is 202. OpenAPI: the start documents its 503 with its code, and ``RestoreStage.error_code``
    allows ``unpacked_too_large``. The archives of a chosen size are the head archive's data directory with one more file
    of zeros, which deflate to almost nothing: whatever they declare, they weigh far less than 1 MB.

Pure: an app of each test holds ``backup_router`` under ``/api/v1``, as ``router.py`` mounts it; ``get_current_user`` is
overridden by an administrator or a regular user, so the real ``require_admin`` decides and no session or database is
reached. ``restore.get_data_dir`` and ``restore_jobs.get_data_dir`` give a data directory under ``tmp_path``; the
process's own data directory is configured to another folder of the test that must stay absent (``configure`` of
``test_backup_staging.py``), so a write anywhere else fails the test and the lane's data directory is never reached.
``threading`` as ``restore_jobs`` sees it is replaced: a check runs at once, in the request that starts it, or is held,
still running with the lock its request took, until the test runs it; no sleep, no clock. Real archives, built as
``test_backup_staging.py`` builds them, from its module fixtures (two databases made once by ``alembic upgrade`` in a
process of their own) and its helpers, imported from it. ``LF_APP_VERSION`` is set, so no git process runs. The app runs
behind ``httpx.ASGITransport`` with ``raise_app_exceptions=False``: an exception a route does not turn into an answer
comes back as a client's plain 500 and fails an assertion instead of erroring. Modes and links are POSIX-only.
"""

from __future__ import annotations

import ast
import asyncio
import errno
import json
import os
import re
import shutil
import stat
import typing
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from structlog.testing import capture_logs

from backend.app import config
from backend.app.api.v1.auth import get_current_user
from backend.app.api.v1.backup import backup_router, restore
from backend.app.api.v1.instance_block import ALLOWED_WHEN_BLOCKED
from backend.app.config import backup as backup_config
from backend.app.config.backup import BackupConfigError, backup_max_upload_mb
from backend.app.schemas.backup import RestoreErrorCode, RestoreStageReport
from backend.app.services.platform.instance_backup import restore_jobs
from backend.app.services.platform.instance_backup import staging as staging_service
from backend.app.services.platform.instance_backup.jobs import _RunLock
from backend.app.services.platform.instance_backup.paths import (
    RESTORE_FOLDER,
    STAGE_DATA_FOLDER,
    STAGE_LOCK_FILE,
    STAGE_REPORT_FILE,
    BackupPathError,
    check_state_path,
    checks_dir,
    ensure_private_dir,
    restore_dir,
    stage_dir,
    stages_dir,
    upload_path,
    uploads_dir,
)
from backend.app.services.platform.instance_backup.staging import STAGE_LIFETIME, read_report
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utils import print_section, print_success

# The module fixtures of test_backup_staging.py (lot B2a), re-exported: the real databases and archives checked here.
databases = cases.databases
head_archive = cases.head_archive
older_archive = cases.older_archive

API = "/api/v1/backup/restore"
UPLOAD = f"{API}/upload"
STAGE = f"{API}/stage"
STAGE_ITEM = f"{STAGE}/{{stage_id}}"
#: Lot B3's route, read here for its ``upload_limit_mb`` alone (B-21): ``test_backup_restore_apply.py`` pins the rest.
STATUS = f"{API}/status"
#: What the upload and the status log, once each, when the limit cannot be read.
LIMIT_ERROR = "The upload limit of a restore cannot be read"
#: B-30: what a check that cannot start answers (507, code ``no_space``; 500, code ``stage_failed``) and logs.
NO_SPACE_TO_CHECK = "Not enough free space to check the archive"
CHECK_NOT_STARTED = "The check could not start: the server's log has the cause"
CHECK_NO_SPACE_WARNING = "A check of a backup archive could not start: not enough free space"
CHECK_START_ERROR = "A check of a backup archive could not start"
#: ``EDQUOT`` (quota exceeded) where the platform has it.
EDQUOT = getattr(errno, "EDQUOT", None)
needs_edquot = pytest.mark.skipif(EDQUOT is None, reason="this platform has no EDQUOT")
#: B-30: the errno of a full disk, and of a quota.
NO_SPACE = [pytest.param(errno.ENOSPC, id="ENOSPC"), pytest.param(EDQUOT, id="EDQUOT", marks=needs_edquot)]
#: The variables of this lot, as .env.example and the deployments write them: spelled out here, so a rename shows.
LIMIT_VARIABLE = "LIBREFOLIO_BACKUP_MAX_UPLOAD_MB"
PROFILE_VARIABLE = "LIBREFOLIO_PROFILE"
#: B-35: the largest restore, in megabytes of what an archive declares unpacked; 0 is no limit.
MAX_RESTORE_VARIABLE = "LIBREFOLIO_BACKUP_MAX_RESTORE_MB"
#: A megabyte of the limit, as the server counts it.
MIB = 1024 * 1024
#: An upload id, a stage id: what the routes make, and the only thing they take.
AN_ID = re.compile(r"[0-9a-f]{32}")
UNKNOWN_ID = "0123456789abcdef0123456789abcdef"
ADMIN = SimpleNamespace(id=1, username="b2b-admin", is_superuser=True)
REGULAR_USER = SimpleNamespace(id=2, username="b2b-user", is_superuser=False)
ADMIN_ONLY_ANSWER = (403, {"detail": "Admin access required"})
#: The tag of every route of ``backup_router``.
TAG = "Backup & Export"


# =============================================================================
# The threads of the checks, the data directory, the app of a test
# =============================================================================


@dataclass
class FakeThread:
    """A thread ``restore_jobs`` started: what it runs, and whether it ran. What its target raises is kept, as a real
    thread's would be lost to the request that started it; the end of every test asserts there was none."""

    owner: Threads
    target: Callable[..., object]
    args: tuple
    kwargs: dict
    name: str | None
    daemon: bool | None
    ran: bool = False
    raised: BaseException | None = None

    def start(self) -> None:
        self.owner.started.append(self)
        if not self.owner.hold:
            self.run()

    def run(self) -> None:
        assert not self.ran, f"a thread runs once: {self.name}"
        self.ran = True
        try:
            self.target(*self.args, **self.kwargs)
        except Exception as exc:
            self.raised = exc

    @property
    def lock(self) -> _RunLock:
        """The lock of the checks the request took and handed to the thread: ``_run_check(data_dir, check, lock, key)``, its
        third argument."""
        return self.args[2]


class Threads:
    """``threading`` as ``restore_jobs`` sees it. A thread it starts runs its target at once, in the thread that starts
    it, so a check has ended when ``POST /stage`` answers; while ``hold`` is set it is kept instead, a check still running
    with the lock its request took, until the test runs it (``run_held``)."""

    def __init__(self) -> None:
        self.hold = False
        self.started: list[FakeThread] = []

    def Thread(self, *, target, args=(), kwargs=None, name=None, daemon=None) -> FakeThread:  # the name restore_jobs calls
        return FakeThread(self, target, tuple(args), dict(kwargs or {}), name, daemon)

    @property
    def held(self) -> list[FakeThread]:
        return [thread for thread in self.started if not thread.ran]

    def run_held(self) -> None:
        for thread in self.held:
            thread.run()


@dataclass(frozen=True)
class Instance:
    """The data directory the routes of a test use, and the threads its checks run in."""

    root: Path
    threads: Threads


@pytest.fixture(autouse=True)
def instance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Instance]:
    """Every test, the unit tests included: the routes use a data directory of the test, the process is configured with
    another one that must stay absent, a self-hosted profile without an upload or a restore limit is set (B-35: whatever
    the environment holds), the checks run in fake threads.

    At its end: the configured data directory was never created, the routes wrote nothing outside ``.restore``, and no
    check's thread raised. A check the test left running has its lock let go, as its server would."""
    configured = cases.configure(monkeypatch, tmp_path / "configured-data-dir")
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    monkeypatch.delenv(MAX_RESTORE_VARIABLE, raising=False)
    root = tmp_path / "instance"
    root.mkdir()
    monkeypatch.setattr(restore, "get_data_dir", lambda: root)
    monkeypatch.setattr(restore_jobs, "get_data_dir", lambda: root)
    threads = Threads()
    monkeypatch.setattr(restore_jobs, "threading", threads)
    yield Instance(root, threads)
    for thread in threads.held:
        if thread.lock is not None:
            thread.lock.release()
    get_git_version.cache_clear()
    assert not configured.exists(), f"something was written in the configured data directory instead of the one given: {cases.listing(configured)}"
    outside = [name for name in cases.listing(root) if Path(name).parts[0] != RESTORE_FOLDER]
    assert outside == [], f"the restore's routes write nothing outside .restore: {outside}"
    raised = [(thread.name, repr(thread.raised)) for thread in threads.started if thread.raised is not None]
    assert raised == [], f"a check's thread raised: {raised}"


def restore_app(user: SimpleNamespace = ADMIN) -> FastAPI:
    """``backup_router`` under ``/api/v1``, as ``router.py`` mounts it, in an app of the test and nothing else.
    ``get_current_user`` answers ``user``: the real ``require_admin`` decides, without a session or a database."""
    app = FastAPI()
    app.include_router(backup_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: user
    return app


async def call(method: str, path: str, *, user: SimpleNamespace = ADMIN, **kwargs: Any) -> httpx.Response:
    transport = httpx.ASGITransport(app=restore_app(user), raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://in-process") as client:
        return await client.request(method, path, **kwargs)


async def upload(content: bytes | AsyncIterator[bytes], *, headers: dict[str, str] | None = None, user: SimpleNamespace = ADMIN) -> httpx.Response:
    """``PUT /upload``, ``content`` the raw body: bytes, with their ``Content-Length``; or pieces, without one."""
    return await call("PUT", UPLOAD, content=content, headers={"Content-Type": "application/octet-stream", **(headers or {})}, user=user)


async def start(upload_id: str, *, user: SimpleNamespace = ADMIN) -> httpx.Response:
    return await call("POST", STAGE, json={"upload_id": upload_id}, user=user)


async def poll(stage_id: str, *, user: SimpleNamespace = ADMIN) -> httpx.Response:
    return await call("GET", f"{STAGE}/{stage_id}", user=user)


async def drop(stage_id: str, *, user: SimpleNamespace = ADMIN) -> httpx.Response:
    return await call("DELETE", f"{STAGE}/{stage_id}", user=user)


def code(response: httpx.Response) -> tuple[int, str | None]:
    """Status and ``detail.code``; None for an answer without one (a plain 500 is text)."""
    if not response.headers.get("content-type", "").startswith("application/json"):
        return response.status_code, None
    detail = response.json().get("detail")
    return response.status_code, detail.get("code") if isinstance(detail, dict) else None


def shown(response: httpx.Response) -> str:
    return f"{response.status_code} {response.text[:800]}"


async def uploaded(content: bytes) -> str:
    """``content`` uploaded: its id."""
    response = await upload(content)
    assert response.status_code == 201, f"precondition: the archive is received: {shown(response)}"
    return response.json()["upload_id"]


async def started(content: bytes) -> dict:
    """``content`` uploaded and its check started: the first state of the check."""
    response = await start(await uploaded(content))
    assert response.status_code == 202, f"precondition: the check starts: {shown(response)}"
    return response.json()


async def ended(content: bytes) -> dict:
    """``content`` uploaded and checked (the check runs at once): the state of the check, ended."""
    first = await started(content)
    response = await poll(first["stage_id"])
    assert response.status_code == 200 and response.json()["status"] != "running", f"precondition: the check has ended: {shown(response)}"
    return response.json()


async def pieces(data: bytes, size: int = 64 * 1024) -> AsyncIterator[bytes]:
    """``data`` as a client streams it, without a ``Content-Length``, ``size`` bytes at a time."""
    for offset in range(0, len(data), size):
        yield data[offset : offset + size]


def files_in(folder: Path) -> list[str]:
    """The names in ``folder``; none when it does not exist."""
    return sorted(path.name for path in folder.iterdir()) if folder.is_dir() else []


def tree(folder: Path) -> dict[str, tuple]:
    """Every path below ``folder``, links never followed: a folder; a link with its target; a file with its size and
    SHA-256. A link to a folder is listed, never walked into."""
    found: dict[str, tuple] = {}
    pending = [folder]
    while pending:
        current = pending.pop()
        for path in current.iterdir():
            info = path.lstat()
            name = path.relative_to(folder).as_posix()
            if stat.S_ISLNK(info.st_mode):
                found[name] = ("link", os.readlink(path))
            elif stat.S_ISDIR(info.st_mode):
                found[name] = ("folder",)
                pending.append(path)
            else:
                found[name] = ("file", info.st_size, cases.sha256(path.read_bytes()))
    return dict(sorted(found.items()))


def age(path: Path, by: timedelta) -> None:
    """Make ``path`` look ``by`` old: its modification time moved back (a link's own, never its target's)."""
    when = (datetime.now(UTC) - by).timestamp()
    os.utime(path, (when, when), follow_symlinks=False)


def moment(value: str) -> datetime:
    return datetime.fromisoformat(value)


#: Older than a check's lifetime, and well within it.
OLD = STAGE_LIFETIME + timedelta(hours=1)
RECENT = timedelta(hours=1)


def age_check(root: Path, stage_id: str, by: timedelta) -> None:
    """The check ``stage_id`` as if it was made and ended ``by`` ago: the dates of its state file moved back, as a server
    of then wrote them, and its copy's folder as old."""
    path = check_state_path(root, stage_id)
    record = json.loads(path.read_text(encoding="utf-8"))
    for key in ("created_at", "finished_at"):
        if record.get(key) is not None:
            record[key] = (moment(record[key]) - by).isoformat()
    path.write_text(json.dumps(record), encoding="utf-8")
    if stage_dir(root, stage_id).is_dir():
        age(stage_dir(root, stage_id), by)


def left_upload(root: Path, name: str, by: timedelta) -> Path:
    """A file left in ``.restore/upload`` ``by`` ago: an upload nobody checked, or the partial of one that never ended."""
    path = ensure_private_dir(uploads_dir(root), root) / name
    path.write_bytes(b"an archive nobody checked")
    age(path, by)
    return path


def left_copy(root: Path, stage_id: str, by: timedelta) -> Path:
    """A copy no check records (a command-line check stopped before its end), its folder ``by`` old."""
    folder = ensure_private_dir(stages_dir(root), root) / stage_id
    (folder / STAGE_DATA_FOLDER / "sqlite").mkdir(parents=True)
    (folder / STAGE_DATA_FOLDER / "sqlite" / "app.db").write_bytes(b"part of a copy nobody records")
    age(folder, by)
    return folder


#: The restore's folders a link may stand in place of, by name.
RESTORE_FOLDERS: dict[str, Callable[[Path], Path]] = {".restore": restore_dir, "checks": checks_dir, "stage": stages_dir, "upload": uploads_dir}


def moved_behind_a_link(root: Path, name: str, elsewhere: Path) -> Path:
    """The restore folder ``name`` moved into ``elsewhere``, a link to it left in its place: what it held is now in the
    link's target, which is returned."""
    folder = RESTORE_FOLDERS[name](root)
    target = elsewhere / name.lstrip(".")
    folder.rename(target)
    folder.symlink_to(target, target_is_directory=True)
    return target


class Patched:
    """A module as ``restore_jobs`` sees it, some of its functions replaced; the rest is the module's own."""

    def __init__(self, module: Any, **replaced: Callable[..., Any]) -> None:
        self._module = module
        self._replaced = replaced

    def __getattr__(self, name: str) -> Any:
        return self._replaced[name] if name in self._replaced else getattr(self._module, name)


def disk_with(monkeypatch: pytest.MonkeyPatch, free: int) -> list[Path]:
    """``shutil.disk_usage`` as ``restore_jobs`` sees it, ``free`` bytes free; the folders it was asked about."""
    asked: list[Path] = []

    def disk_usage(path: str | os.PathLike[str]) -> SimpleNamespace:
        asked.append(Path(path))
        return SimpleNamespace(total=2 * free, used=free, free=free)

    monkeypatch.setattr(restore_jobs, "shutil", Patched(shutil, disk_usage=disk_usage))
    return asked


def on_an_event_loop() -> bool:
    """Whether this thread runs an event loop: a write here would stop every other request meanwhile."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def spy_writes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, bool]]:
    """Every ``UploadWriter.write`` from now on, as it is asked: (bytes, whether on the event loop's thread)."""
    writes: list[tuple[int, bool]] = []
    original = restore_jobs.UploadWriter.write

    def write(self: restore_jobs.UploadWriter, data: bytes) -> None:
        writes.append((len(data), on_an_event_loop()))
        original(self, data)

    monkeypatch.setattr(restore_jobs.UploadWriter, "write", write)
    return writes


def too_large(response: httpx.Response, limit_mb: int) -> bool:
    """Whether ``response`` is the 413 of a limit of ``limit_mb``: its code, the limit, and an English message."""
    if code(response) != (413, "backup_too_large"):
        return False
    detail = response.json()["detail"]
    return set(detail) == {"code", "message", "limit_mb"} and detail["limit_mb"] == limit_mb and isinstance(detail["message"], str)


# =============================================================================
# (a) PUT /backup/restore/upload
# =============================================================================


@cases.needs_posix_modes
@pytest.mark.asyncio
async def test_an_archive_is_received_whole_under_a_new_id_for_the_server_only(instance):
    """(a) 201 with a new id, the size and the kind (``zip``: the body does not start with ``LFBK``); the bytes as sent, in
    ``.restore/upload/<id>``, nothing else beside them."""
    print_section("PUT /backup/restore/upload")
    root = instance.root
    body = bytes(range(256)) * (4 * 1024 + 3)  # 1 MiB and a bit: more than one piece written
    response = await upload(body)
    assert response.status_code == 201, f"an archive received is 201: {shown(response)}"
    answer = response.json()
    assert set(answer) == {"upload_id", "size", "kind"} and AN_ID.fullmatch(answer["upload_id"]), f"the answer is an id of 32 lowercase hex digits, a size and a kind: {answer}"
    assert answer["size"] == len(body), f"the size is the body's: {answer['size']} != {len(body)}"
    assert answer["kind"] == "zip", f"a body that does not start with LFBK is received as a zip, not {answer['kind']!r}"
    kept = upload_path(root, answer["upload_id"])
    assert cases.sha256(kept.read_bytes()) == cases.sha256(body), "the archive is kept byte for byte"
    assert files_in(uploads_dir(root)) == [answer["upload_id"]], f"one file under its id, no partial beside it: {files_in(uploads_dir(root))}"
    modes = {path.relative_to(root).as_posix(): oct(cases.mode(path)) for path in (restore_dir(root), uploads_dir(root), kept)}
    assert modes == {".restore": "0o700", ".restore/upload": "0o700", f".restore/upload/{answer['upload_id']}": "0o600"}, f"an archive holds every user's data: for the server only: {modes}"
    second = (await upload(body)).json()
    assert second["upload_id"] != answer["upload_id"], "every upload gets an id of its own"
    print_success(f"201, {answer['size']} bytes, 0600 under .restore/upload")


@pytest.mark.asyncio
async def test_the_body_is_written_in_pieces_of_1_mib_off_the_event_loop(instance, monkeypatch):
    """(a) The network's pieces are gathered up to 1 MiB before each write, and each write runs in a worker thread."""
    writes = spy_writes(monkeypatch)
    body = bytes(range(256)) * (10 * 1024)  # 2.5 MiB, streamed 64 KiB at a time
    response = await upload(pieces(body))
    assert response.status_code == 201 and response.json()["size"] == len(body), f"received whole: {shown(response)}"
    assert writes == [(MIB, False), (MIB, False), (len(body) - 2 * MIB, False)], f"1 MiB, 1 MiB, the rest; never on the event loop: {writes}"
    print_success(f"{len(writes)} writes for {len(body)} bytes in {len(body) // (64 * 1024)} pieces")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "declared"),
    [
        pytest.param(b"x" * (MIB + 1), None, id="the-body-is-larger"),
        pytest.param(b"a small body", MIB + 1, id="the-header-announces-more"),
    ],
)
async def test_a_declared_size_above_the_limit_is_413_before_anything_is_created(instance, monkeypatch, body, declared):
    """(a) The ``Content-Length`` is judged before a byte is read: 413 with the limit, and not even ``.restore`` created.
    The transport of the test does not hold a client to the size it announces: the header alone is refused here."""
    monkeypatch.setenv(LIMIT_VARIABLE, "1")
    writes = spy_writes(monkeypatch)
    response = await upload(body, headers={} if declared is None else {"Content-Length": str(declared)})
    assert too_large(response, 1), f"413 backup_too_large, limit_mb 1: {shown(response)}"
    assert not restore_dir(instance.root).exists(), f"refused before anything is written: {cases.listing(instance.root)}"
    assert writes == [], f"no piece was written: {writes}"


@pytest.mark.asyncio
@pytest.mark.parametrize("streamed", [False, True], ids=["with-its-content-length", "streamed"])
async def test_the_limit_itself_is_received(instance, monkeypatch, streamed):
    """(a) The limit is the largest archive taken: exactly 1 MiB under a limit of 1 is received, either way."""
    monkeypatch.setenv(LIMIT_VARIABLE, "1")
    body = b"\x00" * MIB
    response = await upload(pieces(body) if streamed else body)
    assert response.status_code == 201 and response.json()["size"] == MIB, f"the limit itself is received: {shown(response)}"


@pytest.mark.asyncio
async def test_a_streamed_body_past_the_limit_is_413_at_that_piece_and_leaves_no_partial(instance, monkeypatch):
    """(a) Without a ``Content-Length`` the limit is checked at every write: the piece that would pass it is refused
    before it is written, and what was written before it is removed."""
    monkeypatch.setenv(LIMIT_VARIABLE, "1")
    writes = spy_writes(monkeypatch)
    response = await upload(pieces(b"\x00" * MIB + b"!"))
    assert "content-length" not in response.request.headers, "precondition: the body is streamed, without a Content-Length"
    assert too_large(response, 1), f"413 backup_too_large, limit_mb 1: {shown(response)}"
    assert [size for size, _on_loop in writes] == [MIB, 1], f"1 MiB written, then the byte too many refused: {writes}"
    assert files_in(uploads_dir(instance.root)) == [], f"no partial left: {files_in(uploads_dir(instance.root))}"
    print_success("413 at the byte past 1 MiB, nothing left")


LIMITS = [
    pytest.param("selfhosted", "2", 2, id="the-variable"),
    pytest.param("managed", None, 500, id="managed-unset"),
    pytest.param("managed", "3", 3, id="managed-the-variable-wins"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("profile", "value", "limit"), LIMITS)
async def test_the_limit_is_the_variable_or_else_the_profile_s(instance, monkeypatch, profile, value, limit):
    """(a) One byte past the limit is 413 with ``limit_mb``, the limit the variable gives, or else the profile's."""
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if value is not None:
        monkeypatch.setenv(LIMIT_VARIABLE, value)
    response = await upload(b"an archive", headers={"Content-Length": str(limit * MIB + 1)})
    assert too_large(response, limit), f"{profile}, {LIMIT_VARIABLE}={value!r}: 413 with limit_mb {limit}: {shown(response)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("profile", "value"),
    [
        pytest.param("selfhosted", None, id="self-hosted-unset"),
        pytest.param("selfhosted", "0", id="self-hosted-0"),
        pytest.param("managed", "0", id="managed-0"),
    ],
)
async def test_without_a_limit_any_size_is_received(instance, monkeypatch, profile, value):
    """(a) No limit: 10 GiB announced, far past the managed 500 MB, is received (the disk says there is room)."""
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if value is not None:
        monkeypatch.setenv(LIMIT_VARIABLE, value)
    disk_with(monkeypatch, free=1024**5)
    response = await upload(b"an archive", headers={"Content-Length": str(10 * 1024 * MIB)})
    assert response.status_code == 201, f"{profile}, {LIMIT_VARIABLE}={value!r}: no limit, received: {shown(response)}"


#: Values of the limit that cannot be read: a digit outside ASCII too (an Arabic-Indic three, a superscript two), which
#: ``str.isdigit`` takes.
UNREADABLE_LIMITS = [
    pytest.param("-1", id="negative"),
    pytest.param("1.5", id="decimal"),
    pytest.param("abc", id="letters"),
    pytest.param("\u0663", id="arabic-indic-digit"),
    pytest.param("\u00b2", id="superscript-digit"),
    pytest.param("+5", id="plus-sign"),
    pytest.param("1e3", id="exponent"),
    pytest.param("0x10", id="hexadecimal"),
    pytest.param("5 0", id="space-inside"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("value", UNREADABLE_LIMITS[:4])
async def test_a_limit_that_cannot_be_read_is_503_and_nothing_is_written(instance, monkeypatch, value):
    """(a) The upload is refused, not taken without a limit: 503, nothing written, one error naming the variable."""
    monkeypatch.setenv(LIMIT_VARIABLE, value)
    with capture_logs() as events:
        response = await upload(b"an archive")
    assert code(response) == (503, "backup_upload_unavailable"), f"{value!r}: 503 backup_upload_unavailable: {shown(response)}"
    assert not restore_dir(instance.root).exists(), f"nothing written: {cases.listing(instance.root)}"
    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 1 and LIMIT_VARIABLE in str(errors[0].get("error")), f"one error in the log, naming the variable: {errors}"


@pytest.mark.asyncio
async def test_without_room_for_the_declared_size_507_and_one_byte_more_is_enough(instance, monkeypatch):
    """(a) The declared size and a margin must fit in the free space of the upload folder: one byte short is 507 with
    no file written; with that byte, received."""
    root = instance.root
    body = b"an archive of a few bytes"
    asked = disk_with(monkeypatch, free=len(body) + restore_jobs._SPACE_MARGIN - 1)
    response = await upload(body)
    assert code(response) == (507, "backup_no_space"), f"507 backup_no_space: {shown(response)}"
    assert files_in(uploads_dir(root)) == [], f"no file written: {files_in(uploads_dir(root))}"
    assert asked == [uploads_dir(root)], f"the free space asked is the upload folder's: {asked}"
    disk_with(monkeypatch, free=len(body) + restore_jobs._SPACE_MARGIN)
    assert (await upload(body)).status_code == 201, "with one byte more, received"


@pytest.mark.asyncio
async def test_a_disk_that_fills_during_the_upload_is_507_and_leaves_no_partial(instance, monkeypatch):
    """(a) A body without a ``Content-Length`` whose second write meets a full disk: 507, what was written removed, and
    the system's words for it kept out of the answer."""
    written: list[int] = []

    def write(fd: int, data: bytes) -> int:
        if written:
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))
        written.append(len(data))
        return os.write(fd, data)

    monkeypatch.setattr(restore_jobs, "os", Patched(os, write=write))
    response = await upload(pieces(b"\x01" * (MIB + 10)))
    assert code(response) == (507, "backup_no_space"), f"507 backup_no_space: {shown(response)}"
    assert written == [MIB], f"precondition: the first piece was written: {written}"
    assert files_in(uploads_dir(instance.root)) == [], f"no partial left: {files_in(uploads_dir(instance.root))}"
    assert os.strerror(errno.ENOSPC) not in response.text, f"the system's words stay in the server: {response.text}"


#: Failures to write an archive that are not a lack of space: (the function of ``os`` that fails, its errno). An
#: ``OSError`` built with ``EACCES`` is a ``PermissionError``.
WRITE_FAILURES = [
    pytest.param("write", errno.EIO, id="a-write-fails-EIO"),
    pytest.param("write", errno.EACCES, id="a-write-is-refused-EACCES"),
    pytest.param("fsync", errno.EIO, id="its-fsync-fails-EIO"),
    pytest.param("replace", errno.EACCES, id="its-rename-is-refused-EACCES"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("failing", "error_number"), WRITE_FAILURES)
async def test_any_other_failure_to_write_the_archive_is_500_and_leaves_nothing(instance, monkeypatch, failing, error_number):
    """(a) Not a lack of space, yet the archive cannot be written: 500 ``backup_upload_failed``, nothing left (the partial
    removed, no archive kept under its id), the system's words in the log only, once."""
    calls: list[str] = []

    def fail(*args: Any, **kwargs: Any) -> Any:
        calls.append(failing)
        raise OSError(error_number, os.strerror(error_number))

    monkeypatch.setattr(restore_jobs, "os", Patched(os, **{failing: fail}))
    with capture_logs() as events:
        response = await upload(b"\x03" * (MIB + 7))
    assert code(response) == (500, "backup_upload_failed"), f"{failing} failing with {errno.errorcode[error_number]}: 500 backup_upload_failed: {shown(response)}"
    assert calls == [failing], f"precondition: the failure came from {failing}, once: {calls}"
    assert files_in(uploads_dir(instance.root)) == [], f"nothing left, neither the partial nor an archive: {files_in(uploads_dir(instance.root))}"
    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 1 and os.strerror(error_number) in str(errors[0].get("error")), f"one error in the log, with the system's words: {errors}"
    leaked = [word for word in (os.strerror(error_number), str(instance.root)) if word in response.text]
    assert leaked == [], f"the answer carries neither the system's words nor a path: {leaked}"


@pytest.mark.asyncio
@pytest.mark.parametrize("error_number", NO_SPACE)
async def test_a_first_upload_whose_folder_cannot_be_created_for_lack_of_space_is_507(instance, monkeypatch, error_number):
    """(a) B-30 (1): the first upload of an instance creates ``.restore/upload``; a full disk or a quota there (mkdir(2):
    ENOSPC, EDQUOT) is 507 ``backup_no_space``, as the same disk a byte later, never 500 ``backup_upload_failed``.
    Nothing written; neither the system's words nor a path in the answer. Barriers: the folder did not exist, and the
    failure came from its creation, through ``restore_jobs.ensure_private_dir`` (the real one for any other folder)."""
    root = instance.root
    folder = uploads_dir(root)
    assert not folder.exists(), f"precondition: the first upload of the instance creates {folder.relative_to(root)}"
    asked: list[Path] = []
    real = restore_jobs.ensure_private_dir

    def ensure_private_dir(path: Path, data_dir: Path) -> Path:
        asked.append(Path(path))
        if Path(path) == folder:
            raise OSError(error_number, os.strerror(error_number))
        return real(path, data_dir)

    monkeypatch.setattr(restore_jobs, "ensure_private_dir", ensure_private_dir)
    response = await upload(b"the first archive of an instance on a full disk")
    assert folder in asked, f"barrier: the folder of the uploads is created through restore_jobs.ensure_private_dir: {asked}"
    assert code(response) == (507, "backup_no_space"), f"{errno.errorcode[error_number]} creating the folder: 507 backup_no_space, not {shown(response)}"
    written = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if not path.is_dir())
    assert written == [], f"nothing written: {written}"
    leaked = [word for word in (os.strerror(error_number), str(root)) if word in response.text]
    assert leaked == [], f"the answer carries neither the system's words nor a path: {leaked}"


#: B-30 (2): the end of an upload on a full disk or a quota: (the call of ``os`` that reports it, its errno). A network
#: file system reports a failed write, or a quota, at ``close`` only (close(2)); others at ``fsync``.
END_NO_SPACE = [
    pytest.param("fsync", errno.ENOSPC, id="fsync-ENOSPC"),
    pytest.param("close", EDQUOT, id="close-EDQUOT", marks=needs_edquot),
    pytest.param("close", errno.ENOSPC, id="close-ENOSPC"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("failing", "error_number"), END_NO_SPACE)
async def test_a_full_disk_at_the_end_of_the_upload_is_507_and_its_file_is_closed_once(instance, monkeypatch, failing, error_number):
    """(a) B-30 (2): ``finish`` meets a full disk or a quota at ``fsync`` or at ``close``: 507 ``backup_no_space``, no
    partial and no final file left, and the descriptor ``os.open`` gave for the partial closed exactly once, also when
    ``close`` itself fails: close(2) releases the descriptor before it reports (Linux does), so ``abort`` must never close
    it again, when its number may already be another file's. Through ``restore_jobs.os``, as the write tests above; a
    second close of that descriptor is counted, never done. Barriers: the partial was opened through
    ``restore_jobs.os``, and the failure came from the call the case names, once."""
    root = instance.root
    partials: list[int] = []
    closes: dict[int, int] = {}
    failed: list[str] = []

    def open_(path: Any, flags: int, mode: int = 0o777, **kwargs: Any) -> int:
        fd = os.open(path, flags, mode, **kwargs)
        if Path(path).parent == uploads_dir(root):
            partials.append(fd)
        return fd

    def fsync(fd: int) -> None:
        if failing == "fsync" and fd in partials:
            failed.append("fsync")
            raise OSError(error_number, os.strerror(error_number))
        os.fsync(fd)

    def close(fd: int) -> None:
        if fd not in partials:
            os.close(fd)
            return
        closes[fd] = closes.get(fd, 0) + 1
        if closes[fd] > 1:
            return  # counted, never done: the number may already be another file's
        os.close(fd)  # close(2) releases the descriptor first, then reports
        if failing == "close":
            failed.append("close")
            raise OSError(error_number, os.strerror(error_number))

    monkeypatch.setattr(restore_jobs, "os", Patched(os, open=open_, fsync=fsync, close=close))
    response = await upload(b"an archive whose last bytes meet a full disk")
    assert (len(partials), failed) == (1, [failing]), f"barrier: the partial opened through restore_jobs.os, and {failing} failed once: {partials}, {failed}"
    assert code(response) == (507, "backup_no_space"), f"{errno.errorcode[error_number]} at {failing}: 507 backup_no_space, not {shown(response)}"
    assert files_in(uploads_dir(root)) == [], f"neither the partial nor a final file left: {files_in(uploads_dir(root))}"
    assert closes == {partials[0]: 1}, f"the partial's descriptor closed exactly once, never twice: {closes}"
    leaked = [word for word in (os.strerror(error_number), str(root)) if word in response.text]
    assert leaked == [], f"the answer carries neither the system's words nor a path: {leaked}"


@pytest.mark.asyncio
@pytest.mark.parametrize("streamed", [False, True], ids=["content-length-0", "streamed-nothing"])
async def test_an_empty_body_is_400_and_leaves_nothing(instance, streamed):
    response = await upload(pieces(b"") if streamed else b"")
    assert code(response) == (400, "backup_upload_empty"), f"400 backup_upload_empty: {shown(response)}"
    assert files_in(uploads_dir(instance.root)) == [], f"nothing left: {files_in(uploads_dir(instance.root))}"


async def upload_then_leave(app: FastAPI, sent: bytes) -> tuple[int, Any]:
    """``PUT /upload`` on ``app`` from a client that sends ``sent`` and leaves: the server receives ``http.disconnect``
    before the end of the body. Called as an ASGI server calls it, since ``httpx`` cannot leave halfway."""
    messages: list[dict[str, Any]] = [{"type": "http.request", "body": sent, "more_body": True}]
    answer: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return messages.pop(0) if messages else {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        answer.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "PUT",
        "scheme": "http",
        "path": UPLOAD,
        "raw_path": UPLOAD.encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"host", b"in-process"), (b"content-type", b"application/octet-stream"), (b"transfer-encoding", b"chunked")],
        "client": ("127.0.0.1", 50000),
        "server": ("in-process", 80),
    }
    await app(scope, receive, send)
    status = next(message["status"] for message in answer if message["type"] == "http.response.start")
    body = b"".join(message.get("body", b"") for message in answer if message["type"] == "http.response.body")
    return status, json.loads(body) if body.startswith(b"{") else body


@pytest.mark.asyncio
async def test_a_client_that_leaves_before_the_end_is_400_and_leaves_no_partial(instance):
    """(a) The client sends more than a piece, then leaves: 400 ``backup_upload_incomplete``, what was written removed."""
    status, body = await upload_then_leave(restore_app(), b"\x02" * (MIB + 5))
    assert (status, body["detail"]["code"] if isinstance(body, dict) else body) == (400, "backup_upload_incomplete"), f"400 backup_upload_incomplete: {status} {body!r}"
    assert files_in(uploads_dir(instance.root)) == [], f"no partial left: {files_in(uploads_dir(instance.root))}"


@pytest.mark.asyncio
async def test_a_second_upload_replaces_the_first(instance):
    root = instance.root
    first = await uploaded(b"the first archive")
    second = await uploaded(b"the second archive")
    assert files_in(uploads_dir(root)) == [second], f"the second replaces the first: {files_in(uploads_dir(root))}"
    assert code(await start(first)) == (404, "backup_upload_not_found"), "the first is no longer there to check"
    assert (await start(second)).status_code == 202, "the second is"


@pytest.mark.asyncio
async def test_the_upload_a_running_check_reads_is_kept_until_its_check_ends(instance, head_archive):
    """(a) A finished upload replaces the others, but the one a running check reads; that one goes when its check ends."""
    root = instance.root
    instance.threads.hold = True
    read = await uploaded(head_archive.path.read_bytes())
    check = (await start(read)).json()
    newer = await uploaded(b"an archive uploaded while the other is checked")
    assert files_in(uploads_dir(root)) == sorted([read, newer]), f"the upload being checked is kept: {files_in(uploads_dir(root))}"
    instance.threads.run_held()
    assert files_in(uploads_dir(root)) == [newer], f"once its check ends, the upload checked is removed: {files_in(uploads_dir(root))}"
    assert (await poll(check["stage_id"])).json()["status"] == "done", "and the check read it whole"


def link_restore(root: Path, elsewhere: Path) -> None:
    (root / RESTORE_FOLDER).symlink_to(elsewhere, target_is_directory=True)


def dangling_restore(root: Path, elsewhere: Path) -> None:
    (root / RESTORE_FOLDER).symlink_to(elsewhere / "gone", target_is_directory=True)


def file_restore(root: Path, elsewhere: Path) -> None:
    (root / RESTORE_FOLDER).write_bytes(b"a file where the restore's folder should be")


def link_upload(root: Path, elsewhere: Path) -> None:
    ensure_private_dir(restore_dir(root), root)
    uploads_dir(root).symlink_to(elsewhere, target_is_directory=True)


@cases.needs_symlinks
@pytest.mark.asyncio
@pytest.mark.parametrize("make", [link_restore, dangling_restore, file_restore, link_upload], ids=["restore-a-link", "restore-a-dangling-link", "restore-a-file", "upload-a-link"])
async def test_a_link_or_a_file_in_place_of_a_restore_folder_is_500_and_nothing_goes_through_it(instance, tmp_path, make):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    make(instance.root, elsewhere)
    response = await upload(b"an archive that must not land elsewhere")
    assert code(response) == (500, "restore_folder_unusable"), f"500 restore_folder_unusable: {shown(response)}"
    assert cases.listing(elsewhere) == [] and not (elsewhere / "gone").exists(), f"nothing written through it: {cases.listing(elsewhere)}"
    assert str(tmp_path) not in response.text and RESTORE_FOLDER not in response.text, f"no path in the answer: {response.text}"


# =============================================================================
# (b) POST /backup/restore/stage, GET and DELETE /backup/restore/stage/{id}
# =============================================================================


@pytest.mark.asyncio
async def test_a_check_runs_on_a_copy_and_reports_what_a_restore_would_do(instance, head_archive):
    """(b) A backup at this LibreFolio's head: 202 running, then done with the report of staging, field by field; the
    upload removed, the copy and its report kept, the state of the check written for the server only."""
    print_section("POST /backup/restore/stage, then GET /backup/restore/stage/{id}")
    root = instance.root
    manifest = head_archive.manifest
    upload_id = await uploaded(head_archive.path.read_bytes())
    response = await start(upload_id)
    assert response.status_code == 202, f"a check that starts is 202: {shown(response)}"
    first = response.json()
    stage_id = first["stage_id"]
    assert AN_ID.fullmatch(stage_id) and stage_id != upload_id, f"the check has an id of its own: {stage_id}"
    beginning = {key: first[key] for key in ("status", "phase", "done_bytes", "total_bytes", "finished_at", "error_code", "report")}
    assert beginning == {"status": "running", "phase": "checking", "done_bytes": 0, "total_bytes": 0, "finished_at": None, "error_code": None, "report": None}, f"its first state: {first}"
    [thread] = instance.threads.started
    assert thread.daemon is True, "the check runs in a daemon thread: a server that stops does not wait for it (its state then reads as interrupted)"

    response = await poll(stage_id)
    assert response.status_code == 200, f"GET of a check is 200: {shown(response)}"
    state = response.json()
    assert (state["stage_id"], state["status"], state["phase"], state["error_code"], state["created_at"]) == (stage_id, "done", None, None, first["created_at"]), f"done: {state}"
    report = state["report"]
    assert report is not None and set(report) == set(RestoreStageReport.model_fields), f"a done check carries its report, every field: {report}"
    assert (report["backup_app_version"], report["backup_origin"], report["backup_revision"]) == (cases.APP_VERSION, "cli", cases.HEAD), f"the backup, as its manifest says: {report}"
    assert moment(report["backup_created_at"]) == manifest.created_at, f"when it was made: {report['backup_created_at']}"
    assert (report["app_version"], report["head_revision"]) == (cases.APP_VERSION, cases.HEAD), f"this LibreFolio: {report['app_version']}, {report['head_revision']}"
    assert (report["action"], report["migrations"], report["post_migration_fixes"]) == ("same", [], []), f"at the head: nothing to upgrade: {report['action']}, {report['migrations']}"
    assert report["tables"] == {name: {"before": rows, "after": rows} for name, rows in manifest.database.tables.items()}, f"every table, its rows unchanged: {report['tables']}"
    sizes = (report["files"], report["files_size"], report["database_size"], report["instance_key_included"])
    assert sizes == (len(cases.FILES), sum(map(len, cases.FILES.values())), manifest.files[0].size, False), f"the files and the database: {sizes}"
    assert (report["foreign_key_violations_before"], report["foreign_key_violations_after"]) == (0, 0), "no broken reference"
    verdict = (report["administrators"], report["warnings"], report["blockers"], report["restorable"])
    assert verdict == (cases.ADMINISTRATORS, [], [], True), f"the administrators one signs in with afterwards; nothing to warn, nothing blocking: {verdict}"
    staged = read_report(root, stage_id)
    expires = moment(report["expires_at"])
    assert expires == staged.expires_at, f"the copy expires when staging says: {expires} != {staged.expires_at}"
    assert moment(state["created_at"]) <= expires - STAGE_LIFETIME <= moment(state["finished_at"]), "24 hours after the check, which ran between its creation and its end"
    unpacked = sum(entry.size for entry in manifest.files)
    assert (state["done_bytes"], state["total_bytes"]) == (unpacked, unpacked), f"a finished check reports what it unpacked, every entry of the archive ({unpacked} bytes), not 0/0: {state['done_bytes']}/{state['total_bytes']}"

    assert files_in(uploads_dir(root)) == [], f"the upload is removed once checked: the copy is what a restore uses: {files_in(uploads_dir(root))}"
    assert files_in(stage_dir(root, stage_id)) == [STAGE_DATA_FOLDER, STAGE_REPORT_FILE], "the copy and its report are kept"
    assert files_in(checks_dir(root)) == [f"{stage_id}.json"], f"one state file, no partial beside it: {files_in(checks_dir(root))}"
    if cases.POSIX:
        assert oct(cases.mode(check_state_path(root, stage_id))) == "0o600", "the state of a check is for the server only"
    assert cases.lock_is_free(root), "the lock is let go at the end of the check"
    print_success(f"202 running → 200 done: same, {len(report['tables'])} tables, administrators {report['administrators']}")


@pytest.mark.asyncio
async def test_an_older_backup_reports_its_upgrade_its_migrations_and_its_warnings(instance, older_archive, monkeypatch):
    """(b) A backup at an older revision (``cases.OLDER``), upgraded (``staging._upgrade`` simulated, as the tests of
    staging do: the real alembic run is theirs) with a broken reference added: the report says the upgrade, its
    migrations each with the first line of its description, and both warnings; restorable all the same."""

    def upgrade_adding_a_broken_reference(database: Path) -> None:
        cases.stamp_head(database)
        cases.execute(database, f"INSERT INTO user_settings (user_id, created_at, updated_at) VALUES (999, '{cases.CREATED}', '{cases.CREATED}')")

    monkeypatch.setattr(staging_service, "_upgrade", upgrade_adding_a_broken_reference)
    state = await ended(older_archive.path.read_bytes())
    report = state["report"]
    assert state["status"] == "done" and report is not None, f"done, with its report: {state}"
    assert (report["action"], report["backup_revision"], report["head_revision"]) == ("upgrade", cases.OLDER, cases.HEAD), f"an upgrade, from {cases.OLDER}: {report['action']}"
    assert report["migrations"] == [{"revision": migration.revision, "message": migration.message} for migration in cases.AFTER_OLDER], f"the migrations after the backup's revision, oldest first: {report['migrations']}"
    assert (report["warnings"], report["blockers"], report["restorable"]) == (["rows_changed", "foreign_key_violations_added"], [], True), f"warned, not blocked: {report['warnings']}"
    counts = (report["foreign_key_violations_before"], report["foreign_key_violations_after"], report["tables"]["user_settings"])
    assert counts == (0, 1, {"before": 0, "after": 1}), f"the broken reference the upgrade added: {counts}"
    assert report["post_migration_fixes"] == read_report(instance.root, state["stage_id"]).post_migration_fixes, "the post-migration fixes, as staging reports them"


@pytest.mark.asyncio
async def test_the_bytes_follow_the_unpacking_and_keep_its_figures_to_the_end(instance, older_archive, monkeypatch):
    """(b) ``done_bytes`` of ``total_bytes`` measure the unpacking. The upgrade counts migrations and the verification
    nothing: their states, read while each runs (from the simulated upgrade, and as the copy's administrators are read),
    and the final one keep the unpacked figures."""
    unpacked = sum(entry.size for entry in older_archive.manifest.files)
    stage_ids: list[str] = []
    seen: dict[str, restore_jobs.RestoreCheck] = {}

    def upgrade(database: Path) -> None:
        seen["upgrading"] = restore_jobs.read_check(stage_ids[0])
        cases.stamp_head(database)

    administrators = staging_service._administrators

    def administrators_while_verifying(database: Path) -> list[str]:
        seen["verifying"] = restore_jobs.read_check(stage_ids[0])
        return administrators(database)

    monkeypatch.setattr(staging_service, "_upgrade", upgrade)
    monkeypatch.setattr(staging_service, "_administrators", administrators_while_verifying)
    instance.threads.hold = True
    stage_ids.append((await started(older_archive.path.read_bytes()))["stage_id"])
    instance.threads.run_held()
    final = (await poll(stage_ids[0])).json()
    figures = {phase: (check.status, check.phase, check.done_bytes, check.total_bytes) for phase, check in seen.items()}
    expected = {"upgrading": ("running", "upgrading", unpacked, unpacked), "verifying": ("running", "verifying", unpacked, unpacked)}
    assert figures == expected, f"the later phases keep the unpacked figures ({unpacked} bytes): {figures}"
    ending = (final["status"], final["report"] and final["report"]["action"], final["done_bytes"], final["total_bytes"])
    assert ending == ("done", "upgrade", unpacked, unpacked), f"and so does the end of an upgraded backup: {ending}"
    print_success(f"upgrading, verifying, done: {unpacked}/{unpacked} bytes")


@pytest.mark.asyncio
async def test_a_backup_without_an_active_administrator_is_reported_not_restorable(instance, databases, tmp_path):
    source = tmp_path / "source"
    archive = cases.build_into(cases.make_data_dir(source / "data", databases.head, accounts=cases.WITHOUT_ADMINISTRATOR), source / "work")
    state = await ended(archive.path.read_bytes())
    report = state["report"]
    verdict = (state["status"], report and report["administrators"], report and report["blockers"], report and report["restorable"])
    assert verdict == ("done", [], ["no_administrator"], False), f"checked, but nobody could sign in afterwards: blocked: {verdict}"


REFUSED = [
    pytest.param(cases.not_a_zip, "not_a_backup", id="not-a-zip"),
    pytest.param(cases.bytes_differ, "checksum_mismatch", id="an-entry-changed"),
    pytest.param(cases.newer_revision, "revision_unknown", id="from-a-newer-librefolio"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("make", "error_code"), REFUSED)
async def test_a_refused_archive_ends_failed_with_its_code_and_leaves_nothing(instance, head_archive, databases, tmp_path, make, error_code):
    """(b) Refused before, during and after the unpacking: failed with staging's code, no report, the upload and the
    copy removed, the lock free."""
    root = instance.root
    source = tmp_path / "source"
    source.mkdir()
    state = await ended(make(source, head_archive, databases).read_bytes())
    ending = (state["status"], state["phase"], state["error_code"], state["report"])
    assert ending == ("failed", None, error_code, None), f"failed with {error_code}: {ending}"
    assert state["finished_at"] is not None, "with the time it ended"
    assert files_in(uploads_dir(root)) == [], f"the upload is removed, refused too: {files_in(uploads_dir(root))}"
    assert cases.leftover_stages(root) == [] and cases.lock_is_free(root), f"nothing of the copy left, the lock free: {cases.leftover_stages(root)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "error_code"),
    [
        pytest.param(lambda root: RuntimeError("an unexpected failure"), "stage_failed", id="unexpected"),
        pytest.param(lambda root: OSError(errno.EIO, os.strerror(errno.EIO), str(root)), "stage_failed", id="input-output-error"),
        pytest.param(lambda root: BackupPathError(stages_dir(root)), "restore_folder_unusable", id="restore-folder-unusable"),
    ],
)
async def test_a_check_that_fails_otherwise_ends_failed_with_its_code(instance, monkeypatch, error, error_code):
    """(b) The check's thread turns any other failure into a code, never into a thread that dies with a running state;
    the upload is removed in any case, and the lock its request took is let go. ``stage_archive`` is replaced: it raises,
    and, as it does with a lock it was given, leaves the lock to its caller."""

    def stage_archive(archive_path: Path, data_dir: Path, *, stage_id=None, progress=None, lock=None, key=None, instance_key=None, max_unpacked=None) -> None:
        raise error(data_dir)

    monkeypatch.setattr(restore_jobs, "stage_archive", stage_archive)
    state = await ended(b"an archive the check never gets to read")
    assert (state["status"], state["error_code"], state["report"]) == ("failed", error_code, None), f"failed with {error_code}: {state}"
    assert str(instance.root) not in json.dumps(state), "the state names no path"
    assert files_in(uploads_dir(instance.root)) == [] and cases.lock_is_free(instance.root), "the upload removed, the lock let go by the check's thread"


def produced_codes() -> set[str]:
    """Every code a check can end with, read from the sources: the ``StagingError`` codes of staging, the
    ``ManifestError`` codes it passes on (all but the two it calls ``not_a_backup``), and the codes ``restore_jobs`` sets."""
    folder = Path(staging_service.__file__).parent

    def first_arguments(module: str, error_class: str) -> set[str]:
        tree = ast.parse((folder / module).read_text(encoding="utf-8"))
        calls = (node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == error_class and node.args)
        return {call.args[0].value for call in calls if isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)}

    set_here: set[str] = set()
    for node in ast.walk(ast.parse((folder / "restore_jobs.py").read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "error_code" for target in node.targets):
            value = node.value
        elif isinstance(node, ast.keyword) and node.arg == "error_code":
            value = node.value
        else:
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            set_here.add(value.value)
    passed_on = (first_arguments("manifest.py", "ManifestError") | first_arguments("archive.py", "ManifestError")) - {"manifest_missing", "manifest_unknown_format"}
    return first_arguments("staging.py", "StagingError") | passed_on | set_here


def test_every_code_a_check_can_end_with_is_one_the_api_declares():
    """(b) ``RestoreStage.error_code`` is a closed list: a code it does not declare would make the GET of that check a
    500 (the answer fails its own model), and a code nothing produces is a promise to the client nobody keeps."""
    produced = produced_codes()
    declared = set(typing.get_args(RestoreErrorCode))
    assert {"not_a_backup", "manifest_newer_format", "revision_unknown", "stage_failed", "restore_interrupted", "restore_folder_unusable"} <= produced, f"precondition: the sources are read: {sorted(produced)}"
    assert (sorted(produced - declared), sorted(declared - produced)) == ([], []), f"(produced, not declared: a 500 on GET; declared, never produced): {sorted(produced - declared)}, {sorted(declared - produced)}"
    print_success(f"{len(produced)} codes, all declared")


@pytest.mark.asyncio
async def test_an_upload_never_received_or_already_checked_is_404(instance):
    root = instance.root
    assert code(await start(UNKNOWN_ID)) == (404, "backup_upload_not_found"), "never received: 404"
    checked = await uploaded(b"an archive checked once")
    assert (await start(checked)).status_code == 202, "precondition: checked once"
    assert code(await start(checked)) == (404, "backup_upload_not_found"), "an upload is checked once: its check removed it"
    assert len(files_in(checks_dir(root))) == 1, f"one check, not two: {files_in(checks_dir(root))}"


BAD_REQUESTS = [
    pytest.param({"upload_id": "../" + "0" * 29}, ["body", "upload_id"], "string_pattern_mismatch", id="parent-folder"),
    pytest.param({"upload_id": "0" * 31}, ["body", "upload_id"], "string_pattern_mismatch", id="31-digits"),
    pytest.param({"upload_id": "0" * 33}, ["body", "upload_id"], "string_pattern_mismatch", id="33-digits"),
    pytest.param({"upload_id": "ABCDEF" + "0" * 26}, ["body", "upload_id"], "string_pattern_mismatch", id="uppercase"),
    pytest.param({"upload_id": "0" * 31 + "g"}, ["body", "upload_id"], "string_pattern_mismatch", id="not-hex"),
    pytest.param({"upload_id": ""}, ["body", "upload_id"], "string_pattern_mismatch", id="empty"),
    pytest.param({}, ["body", "upload_id"], "missing", id="no-upload-id"),
    pytest.param({"upload_id": UNKNOWN_ID, "keep": True}, ["body", "keep"], "extra_forbidden", id="another-field"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("body", "location", "error_type"), BAD_REQUESTS)
async def test_a_malformed_start_is_422_from_the_request_schema(instance, body, location, error_type):
    """(b) 422, not 404: ``RestoreStageRequest.upload_id`` has the pattern of an id (and forbids other fields), so the body
    is refused before the route runs, and no path is ever built from it."""
    response = await call("POST", STAGE, json=body)
    assert response.status_code == 422, f"422 from the schema: {shown(response)}"
    assert [(error["loc"], error["type"]) for error in response.json()["detail"]] == [(location, error_type)], f"one error, at {location}: {response.json()['detail']}"
    assert not restore_dir(instance.root).exists(), "the route never ran"


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "DELETE"])
@pytest.mark.parametrize("value", [UNKNOWN_ID, "0" * 31, "0" * 33, "ABCDEF" + "0" * 26, "0" * 31 + "g", "not-a-stage-id"])
async def test_a_stage_id_no_check_has_is_404(instance, method, value):
    """(b) Unknown, or no id at all: 404 ``restore_stage_not_found``, never a path built from it."""
    response = await call(method, f"{STAGE}/{value}")
    assert code(response) == (404, "restore_stage_not_found"), f"{method} {value!r}: 404 restore_stage_not_found: {shown(response)}"


@pytest.mark.asyncio
async def test_an_ended_check_is_dropped_with_its_copy_then_is_unknown(instance, head_archive):
    root = instance.root
    done = await ended(head_archive.path.read_bytes())
    failed = await ended(b"not a zip")
    assert (done["status"], failed["status"]) == ("done", "failed"), "precondition: one check done, one failed"
    for state in (done, failed):
        response = await drop(state["stage_id"])
        assert (response.status_code, response.content) == (204, b""), f"{state['status']}: dropped, 204 without a body: {shown(response)}"
        assert code(await poll(state["stage_id"])) == (404, "restore_stage_not_found"), f"{state['status']}: then unknown"
        assert code(await drop(state["stage_id"])) == (404, "restore_stage_not_found"), f"{state['status']}: dropped once"
    assert (cases.leftover_stages(root), files_in(checks_dir(root))) == ([], []), "no copy, no state left"


@pytest.mark.asyncio
async def test_a_poll_as_a_check_ends_never_reads_it_as_interrupted(instance, head_archive, monkeypatch):
    """(b) The lock is what says "running": a running state nobody holds it for reads as interrupted. The check's thread
    keeps the lock it was handed until its end is written (``stage_archive`` leaves a lock it was given to its caller),
    so a poll right after the copy is checked, before that end is written (here: what ``GET /stage/{id}`` does), still
    finds the check running; its end then says ``done``, with its report, and its copy is there to restore from."""
    root = instance.root
    polls: list[tuple[str, str | None]] = []
    checked = restore_jobs.stage_archive

    def stage_archive_then_a_poll(*args: Any, **kwargs: Any) -> staging_service.StagingReport:
        report = checked(*args, **kwargs)
        polled = restore_jobs.read_check(kwargs["stage_id"])
        polls.append((polled.status, polled.error_code))
        return report

    monkeypatch.setattr(restore_jobs, "stage_archive", stage_archive_then_a_poll)
    stage_id = (await started(head_archive.path.read_bytes()))["stage_id"]
    state = (await poll(stage_id)).json()
    seen = (polls, state["status"], state["error_code"], state["report"] is not None, stage_dir(root, stage_id).is_dir())
    assert seen == ([("running", None)], "done", None, True, True), f"(the poll as the check ended, then: status, error, a report, the copy): {seen}"


@pytest.mark.asyncio
async def test_a_check_that_ends_while_a_poll_probes_its_lock_keeps_its_result(instance, head_archive, monkeypatch):
    """(b) ``read_check`` reads the state, then probes the lock. A check that ends between the two — its end written, the
    lock let go — is judged on the state read once the lock was found free: ``done``, with its report and its copy,
    never ``restore_interrupted``."""
    root = instance.root
    instance.threads.hold = True
    stage_id = (await started(head_archive.path.read_bytes()))["stage_id"]
    probe = restore_jobs._a_check_runs

    def probe_as_the_check_ends(data_dir: Path) -> bool:
        instance.threads.run_held()
        return probe(data_dir)

    monkeypatch.setattr(restore_jobs, "_a_check_runs", probe_as_the_check_ends)
    state = (await poll(stage_id)).json()
    monkeypatch.setattr(restore_jobs, "_a_check_runs", probe)
    again = (await poll(stage_id)).json()
    seen = ((state["status"], state["error_code"]), (again["status"], again["report"] is not None), stage_dir(root, stage_id).is_dir())
    assert seen == (("done", None), ("done", True), True), f"(the poll that raced, the next one with a report, the copy): {seen}"


#: B-30 (3), (3'): the steps of the check's start a failure is put in: the folders of the check (``stage/``, which the
#: first check creates, through ``restore_jobs.ensure_private_dir``) and its first state (``restore_jobs._write_state``,
#: its first call only: the start's own, under the lock).
START_STEPS = ["its-folders", "its-first-state"]
#: B-30 (3'): failures of the check's start that are not a lack of space.
OTHER_START_FAILURES = [pytest.param(errno.EACCES, id="EACCES"), pytest.param(errno.EIO, id="EIO")]


class StartFailure:
    """A failure put in one step of the check's start: what it raised, and ``cured`` to let the next start through."""

    def __init__(self) -> None:
        self.raised: list[OSError] = []
        self.cured = False


def fail_the_start(monkeypatch: pytest.MonkeyPatch, root: Path, step: str, error_number: int) -> StartFailure:
    """``step`` of the next check's start raises ``OSError(error_number)``, until ``cured``; everything else is the
    module's own."""
    failure = StartFailure()

    def fail() -> None:
        error = OSError(error_number, os.strerror(error_number))
        failure.raised.append(error)
        raise error

    if step == "its-folders":
        real_ensure = restore_jobs.ensure_private_dir

        def ensure_private_dir(path: Path, data_dir: Path) -> Path:
            if not failure.cured and Path(path) == stages_dir(root):
                fail()
            return real_ensure(path, data_dir)

        monkeypatch.setattr(restore_jobs, "ensure_private_dir", ensure_private_dir)
    else:
        real_write = restore_jobs._write_state

        def write_state(data_dir: Path, check: restore_jobs.RestoreCheck) -> None:
            if not failure.cured and not failure.raised:
                fail()
            real_write(data_dir, check)

        monkeypatch.setattr(restore_jobs, "_write_state", write_state)
    return failure


def refusal(response: httpx.Response) -> tuple[int, str | None, str | None]:
    """Status, ``detail.code`` and ``detail.message``; None for an answer without them (a plain 500 is text)."""
    if not response.headers.get("content-type", "").startswith("application/json"):
        return response.status_code, None, None
    detail = response.json().get("detail")
    return (response.status_code, detail.get("code"), detail.get("message")) if isinstance(detail, dict) else (response.status_code, None, None)


def loud(events: list[dict]) -> list[dict]:
    """The events logged at WARNING or above."""
    return [event for event in events if event.get("log_level") in ("warning", "error", "critical")]


def assert_nothing_started(instance: Instance, upload_id: str, response: httpx.Response, error_number: int) -> None:
    """What a start that failed leaves: its upload kept, for another try; no check recorded, no thread started; and the
    answer without the system's words or a path."""
    root = instance.root
    assert upload_path(root, upload_id).is_file(), f"the upload is kept, for another try once there is room: {files_in(uploads_dir(root))}"
    assert (files_in(checks_dir(root)), instance.threads.started) == ([], []), f"no check recorded, no thread started: {files_in(checks_dir(root))}, {instance.threads.started}"
    leaked = [word for word in (os.strerror(error_number), str(root)) if word in response.text]
    assert leaked == [], f"the answer carries neither the system's words nor a path: {leaked}"


@pytest.mark.asyncio
@pytest.mark.parametrize("step", START_STEPS)
@pytest.mark.parametrize("error_number", NO_SPACE)
async def test_a_check_that_cannot_start_for_lack_of_space_is_507_no_space_and_keeps_the_upload(instance, monkeypatch, step, error_number):
    """(b) B-30 (3): a full disk or a quota while the check starts, creating its folders or writing its first state: 507
    with the check's own code, ``no_space`` (as a check that runs out of room later: the restore card says «…to check the
    archive»), never the plain 500 of an error escaping the route; one WARNING, «A check of a backup archive could not
    start: not enough free space». The upload is kept, no check is recorded, and the lock is let go: once the disk has
    room, the same start answers 202. Barrier: the start failed at that step, once."""
    upload_id = await uploaded(b"an archive whose check meets a full disk")
    failure = fail_the_start(monkeypatch, instance.root, step, error_number)

    with capture_logs() as events:
        response = await start(upload_id)

    assert len(failure.raised) == 1, f"barrier: the start failed at {step}, once: {failure.raised}"
    assert refusal(response) == (507, "no_space", NO_SPACE_TO_CHECK), f"{errno.errorcode[error_number]} at {step}: 507 no_space, not {shown(response)}"
    assert [(event.get("log_level"), event.get("event")) for event in loud(events)] == [("warning", CHECK_NO_SPACE_WARNING)], f"one warning: {loud(events)}"
    assert_nothing_started(instance, upload_id, response, error_number)
    failure.cured = True
    retry = await start(upload_id)
    assert retry.status_code == 202, f"room again: the same start is 202 (the lock let go, the upload kept), not {shown(retry)}"
    print_success(f"{errno.errorcode[error_number]} at {step}: 507 no_space, then 202")


@pytest.mark.asyncio
@pytest.mark.parametrize("step", START_STEPS)
@pytest.mark.parametrize("error_number", OTHER_START_FAILURES)
async def test_a_check_that_cannot_start_otherwise_is_500_stage_failed_and_keeps_the_upload(instance, monkeypatch, step, error_number):
    """(b) B-30 (3'): any other ``OSError`` while the check starts (EACCES, EIO): 500 with the check's code
    ``stage_failed``, «The check could not start: the server's log has the cause», never Starlette's plain 500; one
    ERROR, «A check of a backup archive could not start», whose ``error`` is the exception's type and its system's
    words, which stay out of the answer with any path. The upload is kept, no check is recorded, the lock is let go: the
    same start then answers 202. Barrier: the start failed at that step, once."""
    upload_id = await uploaded(b"an archive whose check cannot start")
    failure = fail_the_start(monkeypatch, instance.root, step, error_number)

    with capture_logs() as events:
        response = await start(upload_id)

    assert len(failure.raised) == 1, f"barrier: the start failed at {step}, once: {failure.raised}"
    raised = failure.raised[0]
    assert refusal(response) == (500, "stage_failed", CHECK_NOT_STARTED), f"{errno.errorcode[error_number]} at {step}: 500 stage_failed, not {shown(response)}"
    logged = [(event.get("log_level"), event.get("event"), event.get("error")) for event in loud(events)]
    assert logged == [("error", CHECK_START_ERROR, f"{type(raised).__name__}: {raised.strerror}")], f"one error, with the type and the system's words: {loud(events)}"
    assert_nothing_started(instance, upload_id, response, error_number)
    failure.cured = True
    retry = await start(upload_id)
    assert retry.status_code == 202, f"the failure gone: the same start is 202 (the lock let go, the upload kept), not {shown(retry)}"
    print_success(f"{errno.errorcode[error_number]} at {step}: 500 stage_failed, then 202")


# =============================================================================
# (c) One check at a time; interrupted checks; prune
# =============================================================================


@pytest.mark.asyncio
async def test_while_the_lock_of_the_checks_is_held_a_start_is_409_and_consumes_nothing(instance):
    """(c) The lock is taken by the request: held elsewhere, the start is refused at once, its upload kept for later."""
    root = instance.root
    upload_id = await uploaded(b"an archive waiting for its check")
    ensure_private_dir(stages_dir(root), root)
    lock = _RunLock(stages_dir(root) / STAGE_LOCK_FILE)
    assert lock.try_acquire(), "precondition: the test holds the lock of the checks"
    try:
        response = await start(upload_id)
    finally:
        lock.release()
    assert code(response) == (409, "restore_busy"), f"409 restore_busy: {shown(response)}"
    left = (files_in(uploads_dir(root)), files_in(checks_dir(root)), cases.leftover_stages(root), instance.threads.started)
    assert left == ([upload_id], [], [], []), f"the upload kept, no check written, none started: {left}"
    assert (await start(upload_id)).status_code == 202, "the lock let go, the same upload is checked"


@pytest.mark.asyncio
async def test_while_a_check_runs_another_start_is_409_and_it_cannot_be_dropped(instance, head_archive):
    """(c) The lock the request took is held by the running check: a second start is 409, the running check reads as
    running and cannot be dropped; once it ends, it is done and the second archive is checked."""
    print_section("One check at a time")
    root = instance.root
    instance.threads.hold = True
    first = await started(head_archive.path.read_bytes())
    second = await uploaded(b"a second archive")
    assert code(await start(second)) == (409, "restore_busy"), "a second start while a check runs: 409"
    assert second in files_in(uploads_dir(root)), "the second upload is kept"
    assert (await poll(first["stage_id"])).json()["status"] == "running", "the first check reads as running"
    assert code(await drop(first["stage_id"])) == (409, "restore_stage_running"), "a running check cannot be dropped"
    assert check_state_path(root, first["stage_id"]).is_file(), "and is still there"
    instance.threads.run_held()
    assert (await poll(first["stage_id"])).json()["status"] == "done", "once run, the first check is done"
    instance.threads.hold = False
    assert (await start(second)).status_code == 202, "and the second archive can be checked"
    print_success("409 restore_busy, 409 restore_stage_running, then done")


@pytest.mark.asyncio
@pytest.mark.parametrize("first_request", ["poll", "drop"])
async def test_a_check_whose_server_stopped_reads_as_interrupted_and_its_copy_is_removed(instance, head_archive, first_request):
    """(c) Its thread died with its server, and the lock, an ``flock`` of that process, with it; what it had written of the
    copy stays. The next request about it finds a running state nobody holds the lock for: failed
    ``restore_interrupted``, the copy and the upload removed. A drop then removes its state too."""
    root = instance.root
    instance.threads.hold = True
    upload_id = await uploaded(head_archive.path.read_bytes())
    stage_id = (await start(upload_id)).json()["stage_id"]
    [thread] = instance.threads.held
    thread.lock.release()
    partial = stage_dir(root, stage_id) / STAGE_DATA_FOLDER / "sqlite"
    partial.mkdir(parents=True)
    (partial / "app.db").write_bytes(b"half of every user's data")
    if first_request == "drop":
        response = await drop(stage_id)
        assert response.status_code == 204, f"an interrupted check is dropped: {shown(response)}"
        assert code(await poll(stage_id)) == (404, "restore_stage_not_found"), "then unknown"
    else:
        response = await poll(stage_id)
        state = response.json()
        ending = (response.status_code, state["status"], state["phase"], state["error_code"], state["report"])
        assert ending == (200, "failed", None, "restore_interrupted", None), f"read as interrupted: {ending}"
        assert state["finished_at"] is not None, "with the time it was found so"
        assert (await poll(stage_id)).json() == state, "read again: the same failed state, it was written down"
    assert not stage_dir(root, stage_id).exists(), f"the copy is removed: {cases.listing(root)}"
    assert upload_id not in files_in(uploads_dir(root)), "and its upload"


@pytest.mark.asyncio
async def test_prune_drops_ended_checks_older_than_24_hours_never_a_running_one(instance, head_archive):
    """(c) A done and a failed check, then a check still running (holding the lock, part of its copy written). Exactly
    24 hours after its end a check is kept, a microsecond later dropped with its copy; the running one never, however
    old."""
    print_section("prune")
    root = instance.root
    done = await ended(head_archive.path.read_bytes())
    failed = await ended(b"not a zip")
    instance.threads.hold = True
    running = await started(head_archive.path.read_bytes())
    partial = stage_dir(root, running["stage_id"]) / STAGE_DATA_FOLDER
    partial.mkdir(parents=True)

    def kept(state: dict) -> tuple[bool, bool]:
        return check_state_path(root, state["stage_id"]).is_file(), stage_dir(root, state["stage_id"]).is_dir()

    end = moment(done["finished_at"])
    restore_jobs.prune(root, now=end + STAGE_LIFETIME)
    assert kept(done) == (True, True), "ended exactly 24 hours ago: kept, with its copy"
    restore_jobs.prune(root, now=end + STAGE_LIFETIME + timedelta(microseconds=1))
    assert kept(done) == (False, False), "a microsecond more: dropped, state and copy"
    assert kept(failed)[0], "the failed one ended later: kept"
    restore_jobs.prune(root, now=datetime.now(UTC) + 3 * STAGE_LIFETIME)
    assert kept(failed) == (False, False), "the failed one, older than 24 hours: dropped"
    assert kept(running) == (True, True) and partial.is_dir(), "the running check, never: its state and its copy stay"
    assert code(await poll(done["stage_id"])) == (404, "restore_stage_not_found"), "a dropped check is unknown"
    assert (await poll(running["stage_id"])).json()["status"] == "running", "the running one still reads as running"


@pytest.mark.asyncio
async def test_prune_removes_what_no_check_records_after_24_hours_only_while_no_check_runs(instance, head_archive):
    """(c) Left by a server or a command that stopped: an upload nobody checked, the partial of one that never ended, a
    copy no check records, 25 hours old. While a check runs (the lock held) nothing of it is removed; once none runs,
    exactly those three are. Kept in any case: the same an hour old, a recent check with its copy, the lock, and what is
    not named by an id."""
    root = instance.root
    checked = await ended(head_archive.path.read_bytes())
    old = [left_upload(root, "a" * 32, OLD), left_upload(root, "b" * 32 + ".part", OLD), left_copy(root, "c" * 32, OLD)]
    for recent in (left_upload(root, "d" * 32, RECENT), left_upload(root, "e" * 32 + ".part", RECENT), left_copy(root, "f" * 32, RECENT)):
        assert recent.exists(), "precondition: a recent leftover"
    left_upload(root, "notes.txt", OLD)
    stranger = stages_dir(root) / "notes.txt"
    stranger.write_bytes(b"not a copy")
    age(stranger, OLD)
    before = tree(restore_dir(root))
    lock = _RunLock(stages_dir(root) / STAGE_LOCK_FILE)
    assert lock.try_acquire(), "precondition: the test holds the lock of the checks, as a running check would"
    try:
        restore_jobs.prune(root)
    finally:
        lock.release()
    held = tree(restore_dir(root))
    assert held == before, f"while a check runs, nothing of it is removed: {cases.changed(before, held)}"
    restore_jobs.prune(root)
    after = tree(restore_dir(root))
    old_names = {path.relative_to(restore_dir(root)).as_posix() for path in old}
    gone = {name for name in before if name in old_names or any(name.startswith(prefix + "/") for prefix in old_names)}
    assert after == {name: entry for name, entry in before.items() if name not in gone}, f"once none runs, exactly the old leftovers are removed: {cases.changed(before, after)}"
    assert check_state_path(root, checked["stage_id"]).is_file() and stage_dir(root, checked["stage_id"]).is_dir(), "the recent check is kept, with its copy"
    print_success(f"held: nothing removed; idle: {sorted(old_names)}")


@pytest.mark.asyncio
async def test_prune_ends_a_check_its_stopped_server_left_running_and_keeps_its_end_to_read(instance, head_archive):
    """(c) A running state is the running check's while the lock is held: ``prune`` leaves it. Once nobody holds the lock
    the state was left by a stopped server: ``prune``, which every start runs, ends it as ``restore_interrupted``, its
    copy and its upload removed, and keeps that end for the client to read."""
    root = instance.root
    instance.threads.hold = True
    upload_id = await uploaded(head_archive.path.read_bytes())
    stage_id = (await start(upload_id)).json()["stage_id"]
    partial = stage_dir(root, stage_id) / STAGE_DATA_FOLDER / "sqlite"
    partial.mkdir(parents=True)
    (partial / "app.db").write_bytes(b"half of every user's data")
    restore_jobs.prune(root)
    running = (restore_jobs.read_check(stage_id).status, stage_dir(root, stage_id).is_dir(), upload_path(root, upload_id).is_file())
    assert running == ("running", True, True), f"while its lock is held the check runs: untouched: {running}"
    [thread] = instance.threads.held
    thread.lock.release()
    restore_jobs.prune(root)
    left = (stage_dir(root, stage_id).exists(), upload_path(root, upload_id).exists(), check_state_path(root, stage_id).is_file())
    assert left == (False, False, True), f"ended: (its copy, its upload, its state): {left}"
    state = (await poll(stage_id)).json()
    assert (state["status"], state["error_code"]) == ("failed", "restore_interrupted"), f"its end, to read: {state}"


@pytest.mark.asyncio
async def test_prune_drops_a_check_interrupted_long_ago_with_its_copy(instance, head_archive):
    """(c) A check whose server stopped, which nobody asked about since: ``prune`` two days later ends it and, its end
    being then older than 24 hours, drops it, and its copy of every user's data with it."""
    root = instance.root
    instance.threads.hold = True
    stage_id = (await started(head_archive.path.read_bytes()))["stage_id"]
    [thread] = instance.threads.held
    thread.lock.release()
    partial = stage_dir(root, stage_id) / STAGE_DATA_FOLDER / "sqlite"
    partial.mkdir(parents=True)
    (partial / "app.db").write_bytes(b"half of every user's data")
    restore_jobs.prune(root, now=datetime.now(UTC) + 2 * STAGE_LIFETIME)
    assert not stage_dir(root, stage_id).exists(), f"a check interrupted two days ago keeps its copy after prune: {cases.listing(stage_dir(root, stage_id))}"


@pytest.mark.asyncio
async def test_an_upload_older_than_24_hours_is_not_found_rather_than_checked_and_lost(instance, head_archive):
    """(c) A start prunes first, then looks for its upload: one left 24 hours is gone, 404 ``backup_upload_not_found`` as
    one never received; never a check that starts (202) and then fails on nothing (``archive_unreadable``)."""
    root = instance.root
    upload_id = await uploaded(head_archive.path.read_bytes())
    age(upload_path(root, upload_id), STAGE_LIFETIME + timedelta(hours=1))
    response = await start(upload_id)
    then = None
    if response.status_code == 202:
        ending = (await poll(response.json()["stage_id"])).json()
        then = (ending["status"], ending["error_code"])
    assert code(response) == (404, "backup_upload_not_found"), f"an upload older than 24 hours is not found: {response.status_code}, the check then ended {then}"


async def what_prune_would_remove(root: Path, archive: Path) -> str:
    """A check ended two days ago with its copy, an upload and a copy no check records, 25 hours old: what a ``prune``
    removes. The id of the check."""
    done = await ended(archive.read_bytes())
    age_check(root, done["stage_id"], 2 * STAGE_LIFETIME)
    left_upload(root, "a" * 32, OLD)
    left_copy(root, "c" * 32, OLD)
    return done["stage_id"]


@cases.needs_symlinks
@pytest.mark.asyncio
@pytest.mark.parametrize("linked", [".restore", "checks", "stage"])
async def test_prune_never_removes_through_a_link(instance, head_archive, tmp_path, linked):
    """(c) What prune would remove, moved behind a link in place of ``.restore``, ``checks/`` or ``stage/``: the link's
    target is left as it was, whatever prune does on this side of it."""
    root = instance.root
    await what_prune_would_remove(root, head_archive.path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    moved_behind_a_link(root, linked, elsewhere)
    before = tree(elsewhere)
    restore_jobs.prune(root)
    after = tree(elsewhere)
    assert after == before, f"{linked} a link: prune removed or changed in the link's target: {cases.changed(before, after)}"


@cases.needs_symlinks
@pytest.mark.asyncio
@pytest.mark.parametrize("linked", [".restore", "stage", "checks", "upload"])
async def test_a_start_with_a_link_in_place_of_a_restore_folder_is_500_and_prunes_nothing(instance, head_archive, tmp_path, linked):
    """(c) A start makes sure of its folders before anything else: a link in place of one of them is 500
    ``restore_folder_unusable``, no path in the answer, and nothing is pruned on either side of the link, though what
    prune removes is there."""
    root = instance.root
    await what_prune_would_remove(root, head_archive.path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    moved_behind_a_link(root, linked, elsewhere)
    before = (tree(root), tree(elsewhere))
    response = await start("a" * 32)
    assert code(response) == (500, "restore_folder_unusable"), f"{linked} a link: 500 restore_folder_unusable: {shown(response)}"
    after = (tree(root), tree(elsewhere))
    assert after == before, f"{linked} a link: pruned all the same: {cases.changed(before[0], after[0]) + cases.changed(before[1], after[1])}"
    assert str(tmp_path) not in response.text, f"no path in the answer: {response.text}"


# =============================================================================
# (d) Administrators only, never on a blocked instance, OpenAPI
# =============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["upload", "start", "poll", "drop"])
async def test_a_regular_user_is_refused_403_and_nothing_happens(instance, route):
    """(d) An archive holds every user's data: each route is for administrators. A regular user's request is 403, and
    nothing is received, started, read through or dropped."""
    root = instance.root
    checked = await ended(b"an archive an administrator checked")
    waiting = await uploaded(b"an archive an administrator uploaded")
    before = tree(restore_dir(root))
    requests: dict[str, Callable[[], Awaitable[httpx.Response]]] = {
        "upload": lambda: upload(b"an archive of a regular user", user=REGULAR_USER),
        "start": lambda: start(waiting, user=REGULAR_USER),
        "poll": lambda: poll(checked["stage_id"], user=REGULAR_USER),
        "drop": lambda: drop(checked["stage_id"], user=REGULAR_USER),
    }
    response = await requests[route]()
    assert (response.status_code, response.json()) == ADMIN_ONLY_ANSWER, f"{route} as a regular user: 403: {shown(response)}"
    assert tree(restore_dir(root)) == before, f"{route}: nothing changed under .restore"
    assert len(instance.threads.started) == 1, "no check started"


def test_no_restore_route_is_allowed_on_a_blocked_instance():
    """(d) The block lets the data leave (the backup routes), never come in: none of the four is in ALLOWED_WHEN_BLOCKED.
    ``restore.py`` holds lot B3's four routes too (confirm, status, cancel, restart): ``test_backup_restore_apply.py``
    pins them."""
    endpoints = {restore.upload_restore_archive, restore.start_restore_check, restore.get_restore_check, restore.delete_restore_check}
    missing = sorted(endpoint.__name__ for endpoint in endpoints - {route.endpoint for route in restore.restore_router.routes})
    assert missing == [], f"precondition: these are routes of restore.py: {missing} missing"
    allowed = sorted(endpoint.__name__ for endpoint in endpoints & ALLOWED_WHEN_BLOCKED)
    assert allowed == [], f"a restore route allowed on a blocked instance: {allowed}"


def test_openapi_documents_a_raw_upload_and_the_answers_under_the_backup_tag():
    """(d) The generated client sends the archive as raw bytes, not as a form: the body is ``application/octet-stream``,
    binary, required. The four operations carry ``Backup & Export``, their success model and their refusals."""
    document = restore_app().openapi()
    operations = {(method.upper(), path): operation for path in (UPLOAD, STAGE, STAGE_ITEM) for method, operation in document["paths"][path].items()}
    expected = {("PUT", UPLOAD), ("POST", STAGE), ("GET", STAGE_ITEM), ("DELETE", STAGE_ITEM)}
    assert set(operations) == expected, f"the four operations of /backup/restore: {sorted(operations)}"
    body = operations[("PUT", UPLOAD)]["requestBody"]
    assert body == {"required": True, "content": {"application/octet-stream": {"schema": {"type": "string", "format": "binary"}}}}, f"the upload's body: {body}"
    tags = {key: operation["tags"] for key, operation in operations.items()}
    assert tags == dict.fromkeys(expected, [TAG]), f"each under {TAG} and no other: {tags}"
    success = {key: next(status for status in operation["responses"] if status.startswith("2")) for key, operation in operations.items()}
    assert success == {("PUT", UPLOAD): "201", ("POST", STAGE): "202", ("GET", STAGE_ITEM): "200", ("DELETE", STAGE_ITEM): "204"}, f"the success of each: {success}"
    models = {key: operation["responses"][success[key]].get("content", {}).get("application/json", {}).get("schema") for key, operation in operations.items()}
    assert models == {
        ("PUT", UPLOAD): {"$ref": "#/components/schemas/RestoreUpload"},
        ("POST", STAGE): {"$ref": "#/components/schemas/RestoreStage"},
        ("GET", STAGE_ITEM): {"$ref": "#/components/schemas/RestoreStage"},
        ("DELETE", STAGE_ITEM): None,
    }, f"the model of each success: {models}"
    refusals = {("PUT", UPLOAD): {"400", "413", "500", "503", "507"}, ("POST", STAGE): {"404", "409", "500", "507"}, ("GET", STAGE_ITEM): {"404"}, ("DELETE", STAGE_ITEM): {"404", "409"}}
    undocumented = {key: sorted(statuses - set(operations[key]["responses"])) for key, statuses in refusals.items() if statuses - set(operations[key]["responses"])}
    assert undocumented == {}, f"refusals each route answers but does not document: {undocumented}"


def test_openapi_names_the_codes_of_a_check_that_cannot_start():
    """(d) B-30: the start of a check documents its 507, the check's own code ``no_space`` (never ``backup_no_space``,
    the upload's), and its 500 names ``stage_failed`` beside ``restore_folder_unusable``."""
    responses = restore_app().openapi()["paths"][STAGE]["post"]["responses"]
    described = {status: responses.get(status, {}).get("description", "") for status in ("500", "507")}
    expected = {"500": ["`restore_folder_unusable`", "`stage_failed`"], "507": ["`no_space`"]}
    missing = {status: [code for code in codes if code not in described[status]] for status, codes in expected.items() if any(code not in described[status] for code in codes)}
    assert missing == {}, f"POST {STAGE}: codes its answers do not name: {missing}, in {described}"


# =============================================================================
# (e) backup_max_upload_mb()
# =============================================================================


def test_the_variable_and_the_managed_default_are_the_documented_ones():
    """(e) Decision 43: the variable's name, and 500 MB in the managed profile. The 500 is the entry of H's
    ``ENVIRONMENT_PROFILE_DEFAULTS`` for that variable (H-17), which ``backup_max_upload_mb()`` reads through
    ``profile_default``, and ``config/backup.py`` keeps no managed value of its own beside it: one source, so the two can
    never disagree. The variable is read from the module itself, so the absence is checked on the limit's module."""
    variable = backup_config.MAX_UPLOAD_VARIABLE
    managed = config.ENVIRONMENT_PROFILE_DEFAULTS.get("managed", {})
    assert (variable, managed.get(variable)) == (LIMIT_VARIABLE, 500), f"decision 43: {variable}, {managed.get(variable)} MB in ENVIRONMENT_PROFILE_DEFAULTS['managed']"
    assert not hasattr(backup_config, "MANAGED_MAX_UPLOAD_MB"), f"config/backup.py keeps a managed value of its own beside the table's, MANAGED_MAX_UPLOAD_MB = {getattr(backup_config, 'MANAGED_MAX_UPLOAD_MB', None)!r}: two sources that can disagree"


def test_the_managed_limit_is_the_entry_of_the_profile_table_read_at_each_call(monkeypatch):
    """(e) A GUARD of lot B4 (the note of H-17), extended by H-37 (E, R13-SEC7): H's ``profile_default`` fails closed on
    the entry removed. The managed limit is whatever
    H's ``ENVIRONMENT_PROFILE_DEFAULTS["managed"]`` holds for the variable, read through ``profile_default`` at each
    call. With the managed profile and ``LIBREFOLIO_BACKUP_MAX_UPLOAD_MB`` unset, 123 written in the table's entry is the
    limit, and the entry removed raises H's ``ProfileDefaultError``, never gives the code's own fallback 0, which is no
    limit at all: a managed instance whose table lost the entry refuses uploads (503) rather than accept any size. A
    managed value written by hand in ``config/backup.py``, or a copy of the table taken at import, would answer 500 both
    times and fail here; the name check of the test above cannot see a value under another name."""
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    managed = config.ENVIRONMENT_PROFILE_DEFAULTS["managed"]

    monkeypatch.setitem(managed, backup_config.MAX_UPLOAD_VARIABLE, 123)
    written = backup_max_upload_mb()
    assert written == 123, f"managed, {LIMIT_VARIABLE} unset, the table's managed entry at 123: the limit is the entry, got {written}"

    monkeypatch.delitem(managed, backup_config.MAX_UPLOAD_VARIABLE)
    with pytest.raises(config.ProfileDefaultError):
        removed = backup_max_upload_mb()
        # reached only when nothing was raised: say what came back
        pytest.fail(f"managed, {LIMIT_VARIABLE} unset, no entry in the table: backup_max_upload_mb() returns {removed!r}, where H's profile_default raises ProfileDefaultError (H-37: fail closed); the code's own fallback 0 would be no limit at all")


class _Missing:
    """The type of ``MISSING``: shown as ``no entry`` where a message or a print line writes ``{value!r}``."""

    def __repr__(self) -> str:
        return "no entry"


#: The entry removed from the managed table (H-37).
MISSING = _Missing()
#: Entries of H's profile table for the upload limit that cannot be read: of another type than the code's default ``0``
#: (H-27), or missing (H-37). ``profile_default`` raises ``ProfileDefaultError`` on each. ``None``, read as it is, would
#: mean no limit at all; so would a missing entry, read as the code's own fallback ``0``.
WRONG_TABLE_LIMITS = [
    pytest.param("500", id="the-text-500"),
    pytest.param(None, id="null"),
    pytest.param(500.0, id="a-float"),
    pytest.param(True, id="true"),
    pytest.param(MISSING, id="missing"),
]


def wrong_table_entry(monkeypatch: pytest.MonkeyPatch, value: object) -> None:
    """The managed profile, the variable unset, and H's table giving the upload limit ``value``, or no entry at all for
    ``MISSING``. Checked: the limit then raises H's ``ProfileDefaultError``, for an entry of another type (H-27) as for a
    missing one (H-37), so the case is the one it names."""
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    if value is MISSING:
        monkeypatch.delitem(config.ENVIRONMENT_PROFILE_DEFAULTS["managed"], backup_config.MAX_UPLOAD_VARIABLE)
    else:
        monkeypatch.setitem(config.ENVIRONMENT_PROFILE_DEFAULTS["managed"], backup_config.MAX_UPLOAD_VARIABLE, value)
    try:
        limit = backup_max_upload_mb()
    except config.ProfileDefaultError:
        return
    pytest.fail(f"precondition: H's table giving {value!r}, backup_max_upload_mb() raises ProfileDefaultError (H-27/H-37), not {limit!r}")


def limit_errors(events: list[dict]) -> list[tuple[object, bool]]:
    """The errors logged, each as (its event, whether its ``error`` names the variable)."""
    return [(event.get("event"), LIMIT_VARIABLE in str(event.get("error"))) for event in events if event.get("log_level") == "error"]


@pytest.mark.asyncio
@pytest.mark.parametrize("value", WRONG_TABLE_LIMITS)
async def test_a_wrong_entry_in_the_profile_table_is_503_and_nothing_is_written(instance, monkeypatch, value):
    """(e) B-21: ``_upload_limit`` catches H's ``ProfileDefaultError`` (an entry of another type, H-27, or none, H-37) as
    it catches ``BackupConfigError``: a limit that cannot be read, so the upload is refused as for a variable that cannot
    be read, never taken without a limit: 503 ``backup_upload_unavailable``, nothing written, one error logged, the same
    line, naming the variable; never the plain 500 of an error escaping the route."""
    wrong_table_entry(monkeypatch, value)
    with capture_logs() as events:
        response = await upload(b"an archive")
    assert code(response) == (503, "backup_upload_unavailable"), f"H's table giving {value!r}: 503 backup_upload_unavailable, not {shown(response)}"
    assert not restore_dir(instance.root).exists(), f"nothing written: {cases.listing(instance.root)}"
    assert limit_errors(events) == [(LIMIT_ERROR, True)], f"one error in the log, the line of a limit that cannot be read, naming the variable: {limit_errors(events)}"
    print_success(f"{value!r} in H's table: 503 backup_upload_unavailable, nothing written")


@pytest.mark.asyncio
@pytest.mark.parametrize("value", WRONG_TABLE_LIMITS)
async def test_a_wrong_entry_in_the_profile_table_leaves_the_status_answering_with_a_null_limit(instance, monkeypatch, value):
    """(e) B-21: ``_readable_limit_mb`` catches H's ``ProfileDefaultError`` as it catches ``BackupConfigError``:
    ``GET /backup/restore/status`` still answers, 200, ``upload_limit_mb`` null, as for a variable that cannot be read;
    one error logged, the same line, naming the variable; never the plain 500 of an error escaping the route."""
    wrong_table_entry(monkeypatch, value)
    with capture_logs() as events:
        response = await call("GET", STATUS)
    answer = response.json() if response.headers.get("content-type", "").startswith("application/json") else None
    assert response.status_code == 200 and isinstance(answer, dict), f"H's table giving {value!r}: the status still answers, 200, not {shown(response)}"
    assert (answer.get("state"), "upload_limit_mb" in answer, answer.get("upload_limit_mb")) == ("none", True, None), f"no restore, and the limit null: {answer}"
    assert limit_errors(events) == [(LIMIT_ERROR, True)], f"one error in the log, the line of a limit that cannot be read, naming the variable: {limit_errors(events)}"
    print_success(f"{value!r} in H's table: 200, upload_limit_mb null")


@pytest.mark.parametrize(
    ("profile", "value", "expected"),
    [
        pytest.param("selfhosted", None, 0, id="self-hosted-unset"),
        pytest.param("selfhosted", "", 0, id="self-hosted-empty"),
        pytest.param("selfhosted", " \t ", 0, id="self-hosted-blank"),
        pytest.param("managed", None, 500, id="managed-unset"),
        pytest.param("managed", "  ", 500, id="managed-blank"),
        pytest.param("selfhosted", "0", 0, id="0"),
        pytest.param("selfhosted", "250", 250, id="250"),
        pytest.param("selfhosted", " 250 ", 250, id="spaces-around"),
        pytest.param("managed", "0", 0, id="managed-0-lifts-the-limit"),
        pytest.param("managed", "250", 250, id="managed-the-variable-wins"),
    ],
)
def test_the_upload_limit_is_the_variable_or_else_the_profile_s(monkeypatch, profile, value, expected):
    """(e) Megabytes, 0 for none: the variable when it holds a value, else 0 self-hosted and 500 managed."""
    monkeypatch.setenv(PROFILE_VARIABLE, profile)
    if value is not None:
        monkeypatch.setenv(LIMIT_VARIABLE, value)
    assert backup_max_upload_mb() == expected, f"{profile}, {LIMIT_VARIABLE}={value!r}: {expected}"


@pytest.mark.parametrize("value", UNREADABLE_LIMITS)
def test_anything_but_ascii_digits_is_refused_naming_the_variable(monkeypatch, value):
    """(e) ``BackupConfigError`` ``BACKUP_MAX_UPLOAD_MB_INVALID``, its message naming the variable; a digit outside ASCII
    (an Arabic-Indic three, a superscript two) is refused too, though ``str.isdigit`` takes it."""
    monkeypatch.setenv(LIMIT_VARIABLE, value)
    with pytest.raises(BackupConfigError) as refused:
        backup_max_upload_mb()
    error = refused.value
    assert (error.code, error.variable) == ("BACKUP_MAX_UPLOAD_MB_INVALID", LIMIT_VARIABLE), f"{value!r}: {(error.code, error.variable)}"
    assert LIMIT_VARIABLE in str(error), f"the message names the variable: {error}"


# =============================================================================
# (f) Found while writing the second round, each fixed since
# =============================================================================


@cases.needs_permission_checks
@pytest.mark.asyncio
@pytest.mark.parametrize("read_only", [".restore", "upload"])
async def test_an_upload_whose_file_cannot_be_created_is_500_backup_upload_failed(instance, read_only):
    """(f) Found in the second round, fixed since. A folder of the restore the server cannot write in (owned by another
    user, a read-only mount: here really, mode 0500): the upload's file cannot be created, and the ``OSError`` comes from
    the creation of the ``UploadWriter``, before ``_receive``. ``upload_restore_archive`` maps it through
    ``_upload_failure``, as the same failure a byte later: 500 ``backup_upload_failed``, nothing written, which this test
    pins. Before the fix it mapped only ``BackupPathError`` and the limit's and space's errors there, and the answer was
    a plain 500 without a code."""
    root = instance.root
    folder = ensure_private_dir(RESTORE_FOLDERS[read_only](root), root)
    folder.chmod(0o500)
    try:
        response = await upload(b"an archive the server cannot write down")
    finally:
        folder.chmod(0o700)
    assert code(response) == (500, "backup_upload_failed"), f"{read_only} not writable: 500 backup_upload_failed, not {shown(response)}"
    assert files_in(uploads_dir(root)) == [], f"nothing written: {files_in(uploads_dir(root))}"


@cases.needs_symlinks
@pytest.mark.asyncio
@pytest.mark.parametrize("linked", [".restore", "checks"])
async def test_a_drop_never_removes_through_a_link(instance, head_archive, tmp_path, linked):
    """(f) Found in the second round, fixed since. ``prune`` and ``remove_stage`` leave alone a restore folder that is a
    link; a drop did not: ``DELETE /stage/{id}`` read the check through the link (``_read_state`` opens
    ``.restore/checks/<id>.json`` with ``O_NOFOLLOW``, which guards the last part of the path only), then ``_remove``
    unlinked its state there, and its upload through ``upload/`` likewise; a poll of a check left running wrote its
    interrupted end through the link as well. The fix: the state of a check is read, written and removed only while
    ``.restore`` and the folder concerned are plain folders (``_plain_folders``): behind a link a check is not found,
    and a drop removes and changes nothing in the link's target, which this test pins."""
    root = instance.root
    done = await ended(head_archive.path.read_bytes())
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    moved_behind_a_link(root, linked, elsewhere)
    before = tree(elsewhere)
    response = await drop(done["stage_id"])
    after = tree(elsewhere)
    assert after == before, f"{linked} a link: the drop ({response.status_code}) removed or changed in the link's target: {cases.changed(before, after)}"


@pytest.mark.asyncio
async def test_a_check_dropped_while_a_poll_probes_its_lock_is_not_found(instance, head_archive, monkeypatch):
    """(f) Found in the second round, minor, fixed since. ``read_check`` reads a running state, probes the lock and finds
    it free, reads again: if the check was dropped in between (by another request: it ended, then the user discarded
    it), the second read finds nothing. ``read_check`` used to return the first state, still running: the poll answered
    that a check which no longer exists runs, and a drop in that window answered 409 ``restore_stage_running`` for it.
    The fix: that second read raises ``CheckNotFoundError``, and the poll answers 404 ``restore_stage_not_found``, which
    this test pins."""
    instance.threads.hold = True
    stage_id = (await started(head_archive.path.read_bytes()))["stage_id"]
    probe = restore_jobs._a_check_runs

    def probe_as_another_request_drops_it(data_dir: Path) -> bool:
        instance.threads.run_held()
        restore_jobs.remove_check(stage_id, data_dir=data_dir)
        return probe(data_dir)

    monkeypatch.setattr(restore_jobs, "_a_check_runs", probe_as_another_request_drops_it)
    response = await poll(stage_id)
    assert code(response) == (404, "restore_stage_not_found"), f"a check dropped meanwhile is not found, not {shown(response)}"


# =============================================================================
# (g) The ledger's control totals in the report (lot B-13)
# =============================================================================


TOTALS_STATUSES = {"same", "changed", "absent", "other_version", "unreadable"}
STAGE_WARNINGS = {"rows_changed", "foreign_key_violations", "foreign_key_violations_added", "control_totals_changed", "control_totals_unreadable"}
TOTALS_DIFFERENCE_FIELDS = {"kind", "broker_id", "currency", "asset_id", "before", "after"}


def totals_of(report: dict) -> tuple[str, list[dict], int]:
    """What a done check's report says of the ledger's totals: the status, the differences, how many in all."""
    missing = [field for field in cases.TOTALS_FIELDS if field not in report]
    assert not missing, f"the report has no {', '.join(missing)}, the totals' fields of lot B-13: {sorted(report)}"
    return report["control_totals"], report["control_totals_differences"], report["control_totals_differences_count"]


@pytest.mark.asyncio
async def test_a_ledger_as_recorded_is_reported_the_same(instance, head_archive):
    """(g) The module's backup, checked as it was made: ``same``, nothing listed, no warning."""
    print_section("The ledger's control totals in the report")
    state = await ended(head_archive.path.read_bytes())
    report = state["report"]
    assert state["status"] == "done" and report is not None, f"precondition: done, with its report: {state}"
    assert totals_of(report) == ("same", [], 0), f"same: {totals_of(report)}"
    assert (report["warnings"], report["restorable"]) == ([], True), f"no warning: {report['warnings']}"


@pytest.mark.asyncio
async def test_totals_that_changed_come_with_their_differences_and_a_warning(instance, head_archive, tmp_path):
    """(g) The manifest's totals alone rewritten: a cash line and a position the backup's (empty) ledger does not hold.
    Each difference with its six fields, in order; the warning; restorable all the same."""
    recorded = {"version": 1, "cash": [{"broker_id": 1, "currency": "EUR", "balance": "10"}], "quantities": [{"broker_id": 2, "asset_id": 3, "quantity": "0.5"}]}
    archive = cases.pack(tmp_path / "changed.zip", cases.entries_of(head_archive), cases.manifest_with_totals(head_archive, recorded))
    report = (await ended(archive.read_bytes()))["report"]
    assert report is not None, "precondition: done, with its report"
    expected = [
        {"kind": "cash", "broker_id": 1, "currency": "EUR", "asset_id": None, "before": "10", "after": None},
        {"kind": "quantity", "broker_id": 2, "currency": None, "asset_id": 3, "before": "0.5", "after": None},
    ]
    assert totals_of(report) == ("changed", expected, 2), f"the two lines, in order: {totals_of(report)}"
    assert (report["warnings"], report["blockers"], report["restorable"]) == (["control_totals_changed"], [], True), f"warned, not blocked: {report['warnings']}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("drop", "recorded", "status"), [(True, None, "absent"), (False, {"version": 99}, "other_version")], ids=["absent-a-backup-made-before", "other-version"])
async def test_totals_not_compared_are_said_without_a_warning(instance, head_archive, tmp_path, drop, recorded, status):
    archive = cases.pack(tmp_path / "not-compared.zip", cases.entries_of(head_archive), cases.manifest_with_totals(head_archive, recorded, drop=drop))
    report = (await ended(archive.read_bytes()))["report"]
    assert report is not None, "precondition: done, with its report"
    assert totals_of(report) == (status, [], 0), f"{status}: {totals_of(report)}"
    assert (report["warnings"], report["restorable"]) == ([], True), f"{status}: no warning: {report['warnings']}"


@pytest.mark.asyncio
async def test_totals_the_copy_cannot_give_are_unreadable_with_a_warning(instance, head_archive, monkeypatch):
    cases.replace_ledger_totals(monkeypatch, lambda database: None)
    report = (await ended(head_archive.path.read_bytes()))["report"]
    assert report is not None, "precondition: done, with its report"
    assert totals_of(report) == ("unreadable", [], 0), f"unreadable: {totals_of(report)}"
    assert (report["warnings"], report["blockers"], report["restorable"]) == (["control_totals_unreadable"], [], True), f"warned, not blocked: {report['warnings']}"


@pytest.mark.asyncio
async def test_a_check_whose_report_was_written_before_the_totals_answers_them_absent(instance, head_archive):
    """(g) §7.6: a ``report.json`` a check of before lot B-13 wrote, without the three fields: the check still reads as
    done with its report, the totals ``absent``."""
    state = await ended(head_archive.path.read_bytes())
    path = stage_dir(instance.root, state["stage_id"]) / STAGE_REPORT_FILE
    written = json.loads(path.read_text(encoding="utf-8"))
    assert set(cases.TOTALS_FIELDS) <= set(written), f"precondition: report.json has the totals' fields of lot B-13: {sorted(written)}"
    path.write_text(json.dumps({key: value for key, value in written.items() if key not in cases.TOTALS_FIELDS}, indent=2) + "\n", encoding="utf-8")
    response = await poll(state["stage_id"])
    report = response.json()["report"]
    assert response.status_code == 200 and report is not None, f"done, with its report: {shown(response)}"
    assert totals_of(report) == ("absent", [], 0), f"a report of before: absent: {totals_of(report)}"
    assert report["warnings"] == [] and report["restorable"] is True, f"as it was: {report['warnings']}"


def enum_of(schema: dict, schemas: dict) -> set:
    """The values a schema allows: its ``enum`` (or ``const``), through one ``$ref``."""
    if "$ref" in schema:
        schema = schemas[schema["$ref"].rsplit("/", 1)[-1]]
    return set(schema.get("enum", [schema["const"]] if "const" in schema else []))


def test_openapi_documents_the_totals_of_the_report():
    """(g) The generated client reads the three fields, the five statuses, the two warnings among the five, and each
    difference as ``RestoreTotalsDifference`` with its six fields."""
    schemas = restore_app().openapi()["components"]["schemas"]
    report = schemas["RestoreStageReport"]["properties"]
    missing = [field for field in cases.TOTALS_FIELDS if field not in report]
    assert missing == [], f"RestoreStageReport documents the totals: {missing} missing"
    assert enum_of(report["control_totals"], schemas) == TOTALS_STATUSES, f"the five statuses: {report['control_totals']}"
    assert enum_of(report["warnings"]["items"], schemas) == STAGE_WARNINGS, f"the warnings, the two of the totals included: {report['warnings']}"
    assert report["control_totals_differences"].get("items") == {"$ref": "#/components/schemas/RestoreTotalsDifference"}, f"a list of RestoreTotalsDifference: {report['control_totals_differences']}"
    assert report["control_totals_differences_count"].get("type") == "integer", f"a count: {report['control_totals_differences_count']}"
    difference = schemas.get("RestoreTotalsDifference", {}).get("properties", {})
    assert set(difference) == TOTALS_DIFFERENCE_FIELDS, f"the six fields of a difference: {sorted(difference)}"
    assert enum_of(difference["kind"], schemas) == {"cash", "quantity"}, f"cash or quantity: {difference['kind']}"


# =============================================================================
# (h) B-35: the restore limit, on what an archive declares unpacked
# =============================================================================


#: B-35: what a start answers when the restore limit cannot be read.
RESTORE_LIMIT_UNREADABLE = "The restore limit of this instance cannot be read"
#: B-35: the file of zeros an archive of a chosen size carries beside ``FILES``: zeros deflate to almost nothing.
ZEROS = "custom-uploads/b35-zeros.bin"
#: B-35: the managed profile's restore limit for an upload limit of 1 MB: 8 times it (contract §1, K = 8), in MiB.
EIGHT_MIB = 8 * MIB


def declared_total(archive: cases.BuiltArchive) -> int:
    """What an archive declares unpacked: the sizes its manifest gives its files, the database included."""
    return sum(entry.size for entry in archive.manifest.files)


def archive_declaring(databases: cases.Databases, head_archive: cases.BuiltArchive, root: Path, total: int) -> cases.BuiltArchive:
    """The head archive's data directory (the database at the head, ``ACCOUNTS``, ``FILES``) and one more file of zeros,
    sized so that the manifest declares exactly ``total`` bytes. ``VACUUM INTO`` copies the same database to the same
    size, so the head archive tells what the rest declares; checked on the archive built, not assumed."""
    rest = declared_total(head_archive)
    assert total > rest, f"precondition: {total} bytes are more than the head archive declares ({rest})"
    with pytest.MonkeyPatch.context() as patch:
        cases.configure(patch, root / "configured-data-dir")
        data = cases.make_data_dir(root / "data", databases.head)
        (data / ZEROS).write_bytes(bytes(total - rest))
        built = cases.build_into(data, root / "work")
        get_git_version.cache_clear()
    assert declared_total(built) == total, f"precondition: the archive declares exactly {total} bytes, not {declared_total(built)}"
    return built


@pytest.fixture(scope="module")
def eight_mib_archive(databases, head_archive, tmp_path_factory) -> cases.BuiltArchive:
    """B-35: an archive declaring exactly 8 MiB unpacked, built once."""
    return archive_declaring(databases, head_archive, tmp_path_factory.mktemp("eight-mib-archive"), EIGHT_MIB)


@pytest.fixture(scope="module")
def past_eight_mib_archive(databases, head_archive, tmp_path_factory) -> cases.BuiltArchive:
    """B-35: an archive declaring 8 MiB and one byte unpacked, built once."""
    return archive_declaring(databases, head_archive, tmp_path_factory.mktemp("past-eight-mib-archive"), EIGHT_MIB + 1)


def checked_as_before(state: dict) -> tuple:
    """How a check ended, and what it unpacked: (status, code, restorable, done_bytes, total_bytes)."""
    report = state["report"]
    return state["status"], state["error_code"], report and report["restorable"], state["done_bytes"], state["total_bytes"]


def within_the_upload_limit(archive: cases.BuiltArchive, limit_mb: int) -> None:
    """Precondition: the archive fits the upload limit, so the check, not the upload, is what refuses it."""
    size = archive.path.stat().st_size
    assert size <= limit_mb * MIB, f"precondition: the archive fits the upload limit of {limit_mb} MB: {size} bytes"


#: B-35 (r1, r2): restore limits, self-hosted, around an archive declaring exactly 8 MiB.
CAPS_BELOW = [pytest.param("1", id="1-mb"), pytest.param("7", id="a-mib-below")]
CAPS_AT_OR_ABOVE = [pytest.param("8", id="the-total-itself"), pytest.param("9", id="a-mib-above")]


@pytest.mark.asyncio
@pytest.mark.parametrize("cap", CAPS_BELOW)
async def test_an_archive_declaring_more_than_the_restore_limit_ends_failed_unpacked_too_large(instance, monkeypatch, eight_mib_archive, cap):
    """(h) B-35 (r1): the restore limit below what the archive declares (8 MiB; a limit of 1 MB, or of a MiB less): the
    start is 202, the limit being the check's to apply, and the check ends ``failed`` with ``unpacked_too_large``, its GET
    answering 200 (a code ``RestoreStage`` declares, never the 500 of an answer that fails its own model). Refused before
    anything is unpacked: ``done_bytes`` and ``total_bytes`` 0, no report. Its stage removed (no ``data/`` left), its
    upload consumed, as any refused archive's; the lock free."""
    print_section("B-35: the restore limit")
    root = instance.root
    monkeypatch.setenv(MAX_RESTORE_VARIABLE, cap)
    response = await start(await uploaded(eight_mib_archive.path.read_bytes()))
    assert response.status_code == 202, f"{MAX_RESTORE_VARIABLE}={cap}: the check starts, 202: {shown(response)}"
    stage_id = response.json()["stage_id"]
    polled = await poll(stage_id)
    assert polled.status_code == 200, f"{MAX_RESTORE_VARIABLE}={cap}: the GET of the check answers 200, unpacked_too_large being a code RestoreStage declares, not {shown(polled)}"
    state = polled.json()
    ending = (state["status"], state["phase"], state["error_code"], state["report"] is None, state["done_bytes"], state["total_bytes"])
    assert ending == ("failed", None, "unpacked_too_large", True, 0, 0), f"{MAX_RESTORE_VARIABLE}={cap}, 8 MiB declared: (status, phase, code, no report, done, total) = {ending}: refused before anything is unpacked"
    assert state["finished_at"] is not None, "with the time it ended"
    left = (os.path.lexists(stage_dir(root, stage_id)), cases.leftover_stages(root), files_in(uploads_dir(root)))
    assert left == (False, [], []), f"its stage removed, no data/ left; its upload consumed: {left}"
    assert cases.lock_is_free(root), "the lock let go"
    print_success(f"{MAX_RESTORE_VARIABLE}={cap}, 8 MiB declared: failed unpacked_too_large, nothing unpacked, nothing left")


@pytest.mark.asyncio
@pytest.mark.parametrize("cap", CAPS_AT_OR_ABOVE)
async def test_an_archive_declaring_the_restore_limit_or_less_is_checked_as_before(instance, monkeypatch, eight_mib_archive, cap):
    """(h) B-35 (r2), a GUARD: green before the code, and so it must stay. The restore limit at what the archive declares
    (8 MiB: the limit counts whole MiB, ×1024², and refuses only what is above it), or above: checked as before, done,
    restorable, every declared byte unpacked."""
    monkeypatch.setenv(MAX_RESTORE_VARIABLE, cap)
    state = await ended(eight_mib_archive.path.read_bytes())
    assert checked_as_before(state) == ("done", None, True, EIGHT_MIB, EIGHT_MIB), f"{MAX_RESTORE_VARIABLE}={cap}, 8 MiB declared: checked as before: {checked_as_before(state)}"
    print_success(f"{MAX_RESTORE_VARIABLE}={cap}, 8 MiB declared: done")


#: B-35 (r3): values of the restore limit that cannot be read: anything but a whole number of ASCII digits, an
#: Arabic-Indic three included, which ``str.isdigit`` takes.
INVALID_RESTORE_LIMITS = {"letters": "abc", "negative": "-1", "decimal": "1.5", "arabic-indic-digit": "\u0663"}
#: B-35 (r3): the managed profile, the restore limit unset: a multiple of the upload limit, unreadable in turn, through
#: its variable or through H's table entry (of another type: ``ProfileDefaultError``). By case, the value.
UNREADABLE_UPLOAD_LIMITS = {"managed-upload-limit-letters": "abc", "managed-upload-limit-table-entry": "500"}


def unreadable_restore_limit(monkeypatch: pytest.MonkeyPatch, case: str) -> tuple[str, str]:
    """The restore limit made unreadable as ``case`` says: the variable its error must name, and the value no answer may
    show. The table entry goes through ``wrong_table_entry``, which checks that the upload limit then raises H's
    ``ProfileDefaultError``."""
    if case in INVALID_RESTORE_LIMITS:
        monkeypatch.setenv(MAX_RESTORE_VARIABLE, INVALID_RESTORE_LIMITS[case])
        return MAX_RESTORE_VARIABLE, INVALID_RESTORE_LIMITS[case]
    monkeypatch.delenv(MAX_RESTORE_VARIABLE, raising=False)
    value = UNREADABLE_UPLOAD_LIMITS[case]
    if case == "managed-upload-limit-table-entry":
        wrong_table_entry(monkeypatch, value)
    else:
        monkeypatch.setenv(PROFILE_VARIABLE, "managed")
        monkeypatch.setenv(LIMIT_VARIABLE, value)
    return LIMIT_VARIABLE, value


@pytest.mark.asyncio
@pytest.mark.parametrize("case", [*INVALID_RESTORE_LIMITS, *UNREADABLE_UPLOAD_LIMITS])
async def test_a_restore_limit_that_cannot_be_read_is_503_starts_no_check_and_keeps_the_upload(instance, monkeypatch, case):
    """(h) B-35 (r3): a restore limit that cannot be read is no limit to skip: the start answers 503
    ``backup_restore_unavailable``, «The restore limit of this instance cannot be read», neither the value nor a path in
    the answer; one error in the log, naming the variable that cannot be read (the restore limit's, or the upload limit's
    it multiplies). No check started or recorded, the upload kept: the limit readable again, the same start is 202."""
    root = instance.root
    upload_id = await uploaded(b"an archive whose check waits for a limit that can be read")
    variable, value = unreadable_restore_limit(monkeypatch, case)
    with capture_logs() as events:
        response = await start(upload_id)
    assert refusal(response) == (503, "backup_restore_unavailable", RESTORE_LIMIT_UNREADABLE), f"{case}: 503 backup_restore_unavailable, not {shown(response)}"
    shown_forms = sorted(form for form in {value, json.dumps(value)[1:-1], str(root), str(root.resolve())} if form in response.text)
    assert shown_forms == [], f"{case}: neither the value nor a path in the answer: {shown_forms}"
    errors = [event for event in events if event.get("log_level") == "error"]
    assert len(errors) == 1 and variable in str(errors[0]), f"{case}: one error in the log, naming {variable}: {errors}"
    nothing = (instance.threads.started, files_in(checks_dir(root)), upload_path(root, upload_id).is_file())
    assert nothing == ([], [], True), f"{case}: no check started or recorded, the upload kept: {nothing}"
    monkeypatch.setenv(PROFILE_VARIABLE, "selfhosted")
    monkeypatch.delenv(MAX_RESTORE_VARIABLE, raising=False)
    monkeypatch.delenv(LIMIT_VARIABLE, raising=False)
    again = await start(upload_id)
    assert again.status_code == 202, f"{case}: the limit readable again, the same upload starts its check: {shown(again)}"
    print_success(f"{case}: 503 backup_restore_unavailable, the upload kept, then 202")


#: B-35 (r4): the managed profile, the restore limit unset, the upload limit 1 MB: a cap of 8 MiB. Each archive by the
#: name of its fixture, and the code its check ends with (``None``: done).
MANAGED_CAP = [
    pytest.param("head_archive", None, id="a-small-archive"),
    pytest.param("eight_mib_archive", None, id="at-the-cap"),
    pytest.param("past_eight_mib_archive", "unpacked_too_large", id="one-byte-past-the-cap"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("archive_fixture", "error_code"), MANAGED_CAP)
async def test_the_managed_restore_limit_is_eight_times_the_upload_limit(instance, monkeypatch, request, archive_fixture, error_code):
    """(h) B-35 (r4): managed, the restore limit unset, the upload limit 1 MB: the cap is 8 MiB, 8 times the upload limit
    (never a figure of its own: H's table gives it none). One byte past it, the check ends ``failed``
    ``unpacked_too_large`` before anything is unpacked (red before the code); at it, and a small archive, checked as before
    (green before the code). Each archive fits the upload limit: the check, not the upload, refuses it."""
    archive = request.getfixturevalue(archive_fixture)
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.setenv(LIMIT_VARIABLE, "1")
    within_the_upload_limit(archive, 1)
    total = declared_total(archive)
    state = await ended(archive.path.read_bytes())
    expected = ("done", None, True, total, total) if error_code is None else ("failed", error_code, None, 0, 0)
    assert checked_as_before(state) == expected, f"managed, an upload limit of 1 MB, {total} bytes declared: (status, code, restorable, done, total) = {checked_as_before(state)}, not {expected}"
    print_success(f"managed, upload limit 1 MB, {total} bytes declared: {error_code or 'done'}")


@pytest.mark.asyncio
async def test_an_explicit_0_lifts_the_managed_restore_limit(instance, monkeypatch, past_eight_mib_archive):
    """(h) B-35 (r5), a GUARD: green before the code, and so it must stay. Managed, the upload limit 1 MB, the restore
    limit set to 0: no limit, the explicit value winning over the profile's 8 MiB. The archive one byte past them, which
    the profile's cap refuses (r4), is checked as before."""
    monkeypatch.setenv(PROFILE_VARIABLE, "managed")
    monkeypatch.setenv(LIMIT_VARIABLE, "1")
    monkeypatch.setenv(MAX_RESTORE_VARIABLE, "0")
    within_the_upload_limit(past_eight_mib_archive, 1)
    state = await ended(past_eight_mib_archive.path.read_bytes())
    assert checked_as_before(state) == ("done", None, True, EIGHT_MIB + 1, EIGHT_MIB + 1), f"managed, {MAX_RESTORE_VARIABLE}=0: no limit, checked as before: {checked_as_before(state)}"
    print_success(f"managed, {MAX_RESTORE_VARIABLE}=0: 8 MiB and a byte checked")


def test_openapi_documents_the_restore_limit_that_cannot_be_read_and_the_archive_too_large_unpacked():
    """(h) B-35 (r6): the start of a check documents its 503 with its code, ``backup_restore_unavailable``;
    ``unpacked_too_large`` is a code ``RestoreErrorCode`` lists, so ``RestoreStage.error_code`` allows it in the document
    the generated client reads."""
    document = restore_app().openapi()
    schemas = document["components"]["schemas"]
    unavailable = document["paths"][STAGE]["post"]["responses"].get("503", {}).get("description", "")
    error_code = schemas["RestoreStage"]["properties"]["error_code"]
    allowed = {value for option in error_code.get("anyOf", [error_code]) for value in enum_of(option, schemas)}
    assert "not_a_backup" in allowed, f"precondition: the codes of RestoreStage.error_code are read: {error_code}"
    found = {
        "POST /stage documents a 503 naming backup_restore_unavailable": "backup_restore_unavailable" in unavailable,
        "RestoreErrorCode lists unpacked_too_large": "unpacked_too_large" in typing.get_args(RestoreErrorCode),
        "RestoreStage.error_code allows unpacked_too_large": "unpacked_too_large" in allowed,
    }
    assert found == dict.fromkeys(found, True), f"missing: {sorted(name for name, present in found.items() if not present)}"
    print_success("503 backup_restore_unavailable documented, unpacked_too_large declared")
