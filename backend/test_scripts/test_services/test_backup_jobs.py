"""
Instance backup, the jobs (workstream B, lot B1): one backup at a time, in the background for the API and in the
foreground for the CLI, with the state of each run on disk.

Under test: ``backend/app/services/platform/instance_backup/jobs.py``.

(a) ``start_backup`` returns the first state (running, preparing) and builds in a thread; ``get_job`` follows the run to
    done; ``job_archive`` gives the archive (``BackupJobStateError`` until done, ``BackupJobNotFoundError`` once the
    file is gone); ``delete_job`` removes a finished job (``BackupJobStateError`` while it runs). ``run_backup`` is the
    same run in the calling thread, under the same lock.
(b) One run at a time: while ``backups/.jobs/.lock`` is held (by a run, or by this test through ``_RunLock``), both
    ``start_backup`` and ``run_backup`` raise ``BackupBusyError`` and create nothing.
(c) A state that says running while nobody holds the lock belongs to a run that died with its process: ``get_job``
    reads it as failed/``backup_interrupted`` and writes that down. With the lock held, running stays running.
(d) A build that fails ends the job failed/``backup_failed``, a lack of space failed/``backup_no_space``. Either way
    the work files are removed and the lock released, and in every outcome the final state is on disk before the
    lock is released, so a finished run never reads as interrupted. A lack of space is also a build that stops on a
    full disk or quota after the space check: ``ENOSPC``, ``EDQUOT`` or SQLite's ``SQLITE_FULL``, as the failure or
    as one of its causes (a ``PartialEntryError`` caused by ``ENOSPC``, the database copy finding the disk full, the
    archive's own writes failing); a file that fails while it is being archived for any other reason (a read error)
    is ``backup_failed``. The partial archive such a build leaves is removed: it was there when the cleanup ran.
(e) ``remove_expired_jobs`` removes what ended more than ``JOB_RETENTION`` (1 h) ago: finished jobs, dead runs, job
    folders whose state cannot be read (by the folder's date). It keeps the rest, a running job whose lock is held
    included, never follows a link and never touches what is not a job folder. The next start removes them as well.
    A read (``get_job``, and ``job_archive`` through it) of a job that finished more than an hour ago, done or failed,
    answers ``BackupJobNotFoundError`` and removes its folder, archive included; up to the hour included, the job reads
    as written and its archive is served. The age comes from the ``finished_at`` written in ``state.json`` and a fixed
    ``jobs._now``: never waited for.
(f) A job id is never a path: ``../x``, 31 or 33 hex digits, uppercase hex, the empty string are not found, even when
    a folder of that name holds a finished job.
(g) ``BackupJob.to_json`` / ``from_json`` round trip; unknown keys are ignored, on disk too; a job keeps at most 50
    left-out entries.
(h) Without ``fcntl`` (not POSIX) the run lock is a lock of the process: runs are still serialised within it, and a
    running job must still read as running.
(i) ``out_of_space``: true for an ``OSError`` with ``errno`` ``ENOSPC`` or ``EDQUOT`` and for an ``sqlite3.Error``
    whose ``sqlite_errorcode`` is ``SQLITE_FULL`` (SQLite's own, from a database capped by ``max_page_count``), itself
    or through ``__cause__`` / ``__context__`` up to the eighth exception of the chain; false otherwise: no ``errno``,
    another ``errno``, another SQLite code, SQLite's message without its code, a plain ``RuntimeError``, a ninth
    exception of the chain. A cycle of causes or contexts ends the walk.
(j) ``backup_in_progress`` (workstream Z's idle monitor: never suspend during a backup): true while anyone holds the
    run lock (``backups/.jobs/.lock``) or the lock of the restore checks (``.restore/stage/.stage.lock``), false
    otherwise. Read only: without the lock files it creates nothing; with them free, it leaves them free. Without
    ``fcntl`` it follows the locks of the process. Without ``data_dir``, the configured data directory.
(k) B-8, the running job named by its lock: a run writes its job id into the run lock it holds, right after taking it
    (the content of ``backups/.jobs/.lock``), replacing whatever the file held; the CLI's ``run_backup`` as the API's
    ``start_backup``. While it runs, every start refused (``BackupBusyError``, from ``start_backup`` as from
    ``run_backup``) carries that job as ``running``: its id, its origin, running; neither a read of the job nor a refused
    start erases the record. Another worker knows the run only by the file: a lock held elsewhere (here by the test,
    through ``_RunLock``) whose content is the id of a job whose state says running names that job. Anything else names
    none (``running`` None) though a job's state says running: an empty lock, garbage, bytes that are not text, the id
    in capitals, a path to the running job's folder (the content is never a path, never bent into an id, and no job is
    guessed from a running state), the id of a job that is gone, finished (done, failed, interrupted) or whose state
    cannot be read (not JSON, JSON without its fields, a field of the wrong type), and what a run that ended left there.
    Whatever the lock and the job's state hold, a refused start raises ``BackupBusyError`` (the API's 409
    ``backup_busy``), never another exception, which the API would answer with a 500.
(B-50) A job whose ``state.json`` cannot be read is «not found», never a 500: JSON that is no object (a list, null, a
    number, a string), an empty file, not JSON, ``{}``, a field of the wrong type, a ``created_at`` that is no date,
    bytes that are not UTF-8, a folder, a file the server may not read (mode 000, skipped as root), and a whole state
    whose ``finished_at`` has no time zone. ``get_job``, ``job_archive`` and ``delete_job`` answer
    ``BackupJobNotFoundError`` (caught as that base: the cure raises a subclass) and leave the folder as it is; the read
    logs one warning, ``"A backup job's state cannot be read"``, with ``job_id`` and ``error`` (the class of the error),
    never the content: a canary in the state reaches no logged event, and no traceback is logged. The views of the
    routes (``job_views``, as the Backup tab and the hosting panel call them) answer 404 ``backup_job_not_found``. A
    start, ``remove_expired_jobs`` and ``end_interrupted_jobs`` go on past such folders: the backup is made, an expired
    job removed, a dead run ended ``backup_interrupted``, and the unreadable folder kept until it is an hour old by its
    date, then removed; a lock that names such a job names none. Two guards, green before the cure and after it: a
    missing state is not found without that warning; a transient ``OSError`` (the first read of a state failing with
    ``EIO``) reaches the caller as it is (the API's 500, which the tab retries), is not logged as unreadable, and the
    next read finds the job.

Pure: every data directory is in ``tmp_path`` and every call is given its ``data_dir``; ``jobs.get_data_dir`` is
replaced by a guard that fails the test, so the lane's data directory is never reached (the cases of the routes' views,
B-50, replace it with the test's own). ``LF_APP_VERSION`` is set, so no git process runs. No lane database, no server,
no network. A background run ends before its test does: the test waits for the final state, then joins the run's
thread, and an autouse fixture fails any test that would leave one running. Every wait polls a condition with a
deadline; the cases that need a run in progress hold its build at a gate (an ``Event`` the test opens) instead of
hoping it is slow, or, for the CLI's run in the calling thread, look from its first progress report, while it holds
the lock. A failing disk is simulated in this process only: the ``os`` of ``archive`` is replaced, for one test, by a
stand-in that hands out the real files but one, which reads badly (``EIO`` after its first block) or is on a disk with
a few hundred bytes left (``ENOSPC``).
"""

from __future__ import annotations

import errno
import json
import os
import sqlite3
import stat
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from structlog.testing import capture_logs

from backend.app.api.v1.backup import job_views
from backend.app.services.platform.instance_backup import archive, jobs
from backend.app.services.platform.instance_backup.archive import PartialEntryError, check_archive
from backend.app.services.platform.instance_backup.jobs import (
    JOB_RETENTION,
    BackupBusyError,
    BackupJob,
    BackupJobNotFoundError,
    BackupJobStateError,
    archive_name,
    backup_in_progress,
    delete_job,
    end_interrupted_jobs,
    get_job,
    job_archive,
    remove_expired_jobs,
    run_backup,
    start_backup,
)
from backend.app.services.platform.instance_backup.paths import DATABASE_ENTRY, STAGE_LOCK_FILE, STATE_FILE, ensure_private_dir, is_job_id, job_dir, jobs_dir, lock_path, stages_dir
from backend.app.services.platform.instance_backup.snapshot import file_digest
from backend.app.utils.runtime.version import get_git_version
from backend.test_scripts.test_utils import print_section, print_success

POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_posix_modes = pytest.mark.skipif(not POSIX, reason="file modes are POSIX only")
needs_symlinks = pytest.mark.skipif(not POSIX, reason="symbolic links need a privilege on Windows")
needs_permission_checks = pytest.mark.skipif(not POSIX or AS_ROOT, reason="needs POSIX permissions, which root bypasses")

APP_VERSION = "v0.0.0-b1-jobs-test"
#: Seconds. Every wait of this module ends by then; a hung run fails the test instead of the session.
DEADLINE_S = 60
#: Seconds a wait on a run's thread lasts at most between two reads of the job's state (it ends with the thread).
POLL_S = 0.02
#: A fixed "now" for the retention cases, so that no clock decides them.
NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
VALID_ID = "0123456789abcdef0123456789abcdef"
FILES = {
    "custom-uploads/logo.png": bytes(range(256)) * 4,
    "broker_reports/uploaded/2026-10.csv": b"date,amount\n2026-10-01,10.00\n",
    "scenario_catalog/user-scenarios.json": b'{"scenarios": []}\n',
}


# =============================================================================
# Helpers
# =============================================================================


@pytest.fixture(autouse=True)
def app_version(monkeypatch):
    """The version of every manifest, without a git process; ``get_git_version``'s process-wide cache emptied around the test."""
    monkeypatch.setenv("LF_APP_VERSION", APP_VERSION)
    get_git_version.cache_clear()
    yield
    get_git_version.cache_clear()


@pytest.fixture(autouse=True)
def no_lane_data_dir(monkeypatch) -> None:
    """Every call of this module names its data directory: the configured one is the lane's, never a test's."""

    def lane_data_dir() -> Path:
        raise AssertionError("jobs.get_data_dir() was called: a test of this module must pass data_dir")

    monkeypatch.setattr(jobs, "get_data_dir", lane_data_dir)


@pytest.fixture(autouse=True)
def no_backup_thread_outlives_its_test():
    """A background run started by a test ends within it: joined here, and a failure if it does not end."""
    before = set(threading.enumerate())
    yield
    started = [thread for thread in threading.enumerate() if thread.name.startswith("backup-") and thread not in before]
    deadline = time.monotonic() + DEADLINE_S
    for thread in started:
        thread.join(max(0.0, deadline - time.monotonic()))
    alive = [thread.name for thread in started if thread.is_alive()]
    if alive:
        pytest.fail(f"backup threads still running {DEADLINE_S}s after the end of the test: {alive}")


@pytest.fixture
def data_dir(tmp_path) -> Path:
    """A data directory of this test: a small database and one file in each archived folder."""
    root = tmp_path / "data"
    database = root / DATABASE_ENTRY
    database.parent.mkdir(parents=True)
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        with conn:
            conn.executemany("INSERT INTO users (id, name) VALUES (?, ?)", [(1, "ada"), (2, "grace")])
            conn.execute("INSERT INTO alembic_version (version_num) VALUES ('b1a2c3d4e5f6')")
    for entry, content in FILES.items():
        (root / entry).parent.mkdir(parents=True, exist_ok=True)
        (root / entry).write_bytes(content)
    return root


def mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def job_folders(data_dir: Path) -> list[str]:
    """The entries of the jobs folder but its lock."""
    folder = jobs_dir(data_dir)
    return sorted(path.name for path in folder.iterdir() if path.name != ".lock") if folder.is_dir() else []


def run_thread(job_id: str) -> threading.Thread | None:
    """The thread of a background run, while it lives (``start_backup`` names it after the job)."""
    return next((thread for thread in threading.enumerate() if thread.name == f"backup-{job_id[:8]}"), None)


def wait_until_finished(job_id: str, data_dir: Path) -> BackupJob:
    """The state of a job once it is no longer running, its thread joined, within the deadline.

    The state is read while the run lasts, as the UI reads it; between two reads the wait is on the run's thread, and
    ends as soon as the thread does. The thread exists from ``start_backup``'s return until after the final state is
    written, so a running state without it is a failure, not something to wait for.
    """
    deadline = time.monotonic() + DEADLINE_S
    thread = run_thread(job_id)
    job = get_job(job_id, data_dir=data_dir)
    while job.status == "running":
        if thread is None or time.monotonic() > deadline:
            pytest.fail(f"job {job_id} still running after {DEADLINE_S}s, its thread {'gone' if thread is None else 'alive'}: {job}")
        thread.join(POLL_S)
        job = get_job(job_id, data_dir=data_dir)
    if thread is not None:
        thread.join(max(0.0, deadline - time.monotonic()))
        assert not thread.is_alive(), f"the thread of job {job_id} was still running {DEADLINE_S}s after the job ended"
    return job


@contextmanager
def lock_held(data_dir: Path) -> Iterator[jobs._RunLock]:
    """The run lock, held by this test as a run in another worker or process would hold it."""
    ensure_private_dir(jobs_dir(data_dir), data_dir)
    holder = jobs._RunLock(lock_path(data_dir))
    assert holder.try_acquire(), "precondition: nobody holds the run lock"
    try:
        yield holder
    finally:
        holder.release()


def write_job(data_dir: Path, *, status: str, created: datetime, finished: datetime | None = None, error_code: str | None = None, job_id: str | None = None, origin: str = "ui") -> BackupJob:
    """A job's state as a run of another process left it on disk."""
    job = BackupJob(
        job_id=job_id or uuid.uuid4().hex,
        origin=origin,
        status=status,
        phase="files" if status == "running" else None,
        done_bytes=10,
        total_bytes=100,
        created_at=created,
        finished_at=finished,
        error_code=error_code,
    )
    folder = ensure_private_dir(job_dir(data_dir, job.job_id), data_dir)
    (folder / STATE_FILE).write_text(job.to_json(), encoding="utf-8")
    return job


def date_folder(folder: Path, when: datetime) -> None:
    os.utime(folder, (when.timestamp(), when.timestamp()))


@dataclass
class Gate:
    """Holds a run's build until the test opens it: the run is in progress, for as long as the test needs."""

    entered: threading.Event = field(default_factory=threading.Event)
    opened: threading.Event = field(default_factory=threading.Event)


@pytest.fixture
def gate(monkeypatch):
    held = Gate()
    real_build = jobs.build_archive

    def build_at_the_gate(*args, **kwargs):
        held.entered.set()
        if not held.opened.wait(DEADLINE_S):
            raise TimeoutError("the test never opened the gate")
        return real_build(*args, **kwargs)

    monkeypatch.setattr(jobs, "build_archive", build_at_the_gate)
    yield held
    held.opened.set()


class BrokenBuild:
    """A first build that leaves work files behind and fails; the builds after it are real."""

    def __init__(self, real_build):
        self.real_build = real_build
        self.calls = 0

    def __call__(self, data_dir, work_dir, target, **kwargs):
        self.calls += 1
        if self.calls > 1:
            return self.real_build(data_dir, work_dir, target, **kwargs)
        (work_dir / "app.db").write_bytes(b"half a database copy")
        target.with_name(target.name + ".part").write_bytes(b"PK half an archive")
        (work_dir / "scratch").mkdir()
        (work_dir / "scratch" / "piece").write_bytes(b"piece")
        raise RuntimeError("the disk went away")


def no_space(monkeypatch) -> None:
    monkeypatch.setattr(archive.shutil, "disk_usage", lambda path: SimpleNamespace(total=1024, used=1024, free=0))


@dataclass
class Release:
    """What was on disk when a ``_RunLock`` was released."""

    held: bool
    states: dict[str, dict]
    listing: dict[str, list[str]]


def watch_releases(data_dir: Path, monkeypatch) -> list[Release]:
    """Every release of a run lock from now on, with the job folders and their states as they were at that instant."""
    seen: list[Release] = []
    real_release = jobs._RunLock.release

    def release(self) -> None:
        folders = [path for path in jobs_dir(data_dir).iterdir() if path.is_dir()]
        states = {path.name: json.loads((path / STATE_FILE).read_text(encoding="utf-8")) for path in folders if (path / STATE_FILE).is_file()}
        seen.append(Release(held=self._fd is not None or self._local is not None, states=states, listing={path.name: sorted(os.listdir(path)) for path in folders}))
        real_release(self)

    monkeypatch.setattr(jobs._RunLock, "release", release)
    return seen


def watch_cleanup(monkeypatch) -> list[list[str]]:
    """What a run's folder held each time the run started removing its work files: proof of what was removed."""
    seen: list[list[str]] = []
    real_remove = jobs._remove_work_files

    def remove_work_files(folder: Path, keep: str | None) -> None:
        seen.append(sorted(os.listdir(folder)))
        real_remove(folder, keep)

    monkeypatch.setattr(jobs, "_remove_work_files", remove_work_files)
    return seen


#: ``EDQUOT`` (quota exceeded) where the platform has it.
EDQUOT = getattr(errno, "EDQUOT", None)
needs_edquot = pytest.mark.skipif(EDQUOT is None, reason="this platform has no EDQUOT")
#: Seconds. The walk of ``out_of_space`` is a handful of steps: a walk still going by then loops.
WALK_DEADLINE_S = 10


def os_error(code: int) -> OSError:
    return OSError(code, os.strerror(code))


def sqlite_full_error() -> sqlite3.Error:
    """SQLite's own ``SQLITE_FULL``, as ``VACUUM INTO`` raises it on a full disk: from a database capped at 3 pages."""
    with closing(sqlite3.connect(":memory:")) as conn:
        conn.execute("PRAGMA max_page_count=3")
        conn.execute("CREATE TABLE filler (data BLOB)")
        try:
            for _ in range(16):
                conn.execute("INSERT INTO filler (data) VALUES (?)", (bytes(4096),))
        except sqlite3.OperationalError as exc:
            assert exc.sqlite_errorcode == sqlite3.SQLITE_FULL, f"precondition: SQLite reports SQLITE_FULL, not {exc.sqlite_errorname}"
            return exc
    pytest.fail("precondition: a database capped at 3 pages never reported itself full")


def sqlite_syntax_error() -> sqlite3.Error:
    """SQLite's own ``SQLITE_ERROR``: an error of SQLite that is not a full disk."""
    with closing(sqlite3.connect(":memory:")) as conn:
        try:
            conn.execute("SELEC 1")
        except sqlite3.OperationalError as exc:
            return exc
    pytest.fail("precondition: SQLite accepted SELEC")


def caused_by(cause: BaseException) -> RuntimeError:
    """A failure raised ``from`` ``cause``."""
    try:
        raise RuntimeError("the build failed") from cause
    except RuntimeError as exc:
        return exc


def raised_while_handling(error: BaseException) -> RuntimeError:
    """A failure raised while ``error`` was being handled: ``error`` is its ``__context__``, not its cause."""
    try:
        try:
            raise error
        except BaseException:
            raise RuntimeError("the cleanup failed too")  # noqa: B904 — on purpose: the context, not a cause, is under test
    except RuntimeError as exc:
        return exc


def partial_entry(cause: OSError) -> PartialEntryError:
    """What ``_add_file`` raises when a file fails once its entry has started."""
    try:
        raise PartialEntryError("custom-uploads/logo.png") from cause
    except PartialEntryError as exc:
        return exc


def chain(length: int, root: BaseException) -> BaseException:
    """``root`` as the ``length``-th exception of a chain: the failure, its cause, the cause of that…"""
    top = root
    for index in range(length - 1):
        wrapper = RuntimeError(f"wrapper {index}")
        wrapper.__cause__ = top
        top = wrapper
    return top


class FailingReads:
    """A file open for reading that gives its first block, then fails as a dying disk does (``EIO``)."""

    def __init__(self, handle):
        self._handle = handle
        self.reads = 0

    def read(self, size: int = -1) -> bytes:
        self.reads += 1
        if self.reads > 1:
            raise os_error(errno.EIO)
        return self._handle.read(size)

    def __getattr__(self, name: str):
        return getattr(self._handle, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        self._handle.close()
        return False


class FillingDisk:
    """A file open for writing on a disk with ``room`` bytes left: the write that does not fit fails with ``ENOSPC``."""

    def __init__(self, handle, room: int):
        self._handle = handle
        self._room = room

    def write(self, data) -> int:
        if len(data) > self._room:
            raise os_error(errno.ENOSPC)
        self._room -= len(data)
        return self._handle.write(data)

    def __getattr__(self, name: str):
        return getattr(self._handle, name)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> bool:
        self._handle.close()
        return False


class FailingDiskOs:
    """``archive``'s ``os``, every call the real one, but the file opened from ``reads_badly`` reads badly and the
    partial archive (``*.part``) is written to a disk with ``room`` bytes left, when they are given."""

    def __init__(self, *, reads_badly: Path | None = None, room: int | None = None):
        self._reads_badly = reads_badly
        self._room = room
        self._failing: dict[int, str] = {}

    def __getattr__(self, name: str):
        return getattr(os, name)

    def open(self, path, flags, *args, **kwargs) -> int:
        fd = os.open(path, flags, *args, **kwargs)
        if self._reads_badly is not None and Path(path) == self._reads_badly:
            self._failing[fd] = "read"
        elif self._room is not None and str(path).endswith(".part"):
            self._failing[fd] = "write"
        return fd

    def fdopen(self, fd: int, *args, **kwargs):
        handle = os.fdopen(fd, *args, **kwargs)
        failing = self._failing.pop(fd, None)
        if failing == "read":
            return FailingReads(handle)
        if failing == "write":
            return FillingDisk(handle, self._room)
        return handle


# =============================================================================
# (a) a run, in the background and in the foreground
# =============================================================================


def test_a_started_backup_runs_in_the_background_to_done(data_dir):
    """(a) The first state comes back at once; the run ends done, with its archive, 0600, in a 0700 folder of its own."""
    print_section("start_backup → get_job → job_archive")
    first = start_backup(origin="ui", data_dir=data_dir)
    assert is_job_id(first.job_id), f"the job id must be 32 lowercase hex digits: {first.job_id!r}"
    assert (first.status, first.phase, first.origin, first.done_bytes, first.total_bytes, first.file_name) == ("running", "preparing", "ui", 0, 0, None), f"the first state of a run: {first}"
    job = wait_until_finished(first.job_id, data_dir)
    folder = job_dir(data_dir, job.job_id)
    assert (job.status, job.error_code, job.phase) == ("done", None, None), f"the run must end done: {job}"
    assert job.created_at == first.created_at and job.finished_at >= job.created_at, f"created at the start, finished after: {job.created_at} → {job.finished_at}"
    assert job.file_name == archive_name(job.created_at), f"the archive is named after the run's creation time: {job.file_name}"
    assert (job.file_size, job.file_sha256) == file_digest(folder / job.file_name), "the state gives the archive's size and SHA-256"
    assert job.done_bytes == job.total_bytes > 0, f"a finished run has done all its bytes: {job.done_bytes}/{job.total_bytes}"
    assert (job.warnings, job.skipped) == ((), ()), f"nothing was left out of this data directory: {job.warnings}, {job.skipped}"
    assert sorted(os.listdir(folder)) == sorted([STATE_FILE, job.file_name]), f"the job folder keeps its state and its archive, nothing else: {sorted(os.listdir(folder))}"
    assert BackupJob.from_json((folder / STATE_FILE).read_text(encoding="utf-8")) == job, "get_job reads the state on disk"
    if POSIX:
        assert (mode(folder), mode(folder / job.file_name), mode(folder / STATE_FILE)) == (0o700, 0o600, 0o600), "the job folder is 0700, its archive and state 0600"
    assert job_archive(job.job_id, data_dir=data_dir) == (folder / job.file_name, job.file_name), "job_archive gives the archive's path and file name"
    check = check_archive(folder / job.file_name)
    assert check.ok and check.manifest.origin == "ui", f"the archive checks ok and says it was made from the UI: {check}"
    print_success(f"{job.file_name}: {job.file_size} bytes")


def test_a_deleted_job_is_gone_with_its_archive(data_dir):
    job, folder = run_backup(data_dir=data_dir)
    delete_job(job.job_id, data_dir=data_dir)
    assert not folder.exists(), "delete_job removes the job's folder, its archive with it"
    for call in (get_job, job_archive, delete_job):
        with pytest.raises(BackupJobNotFoundError):
            call(job.job_id, data_dir=data_dir)
    print_success("deleted: get_job, job_archive and delete_job → not found")


def test_run_backup_runs_in_the_calling_thread(data_dir):
    """(a) The CLI's run: no thread, the progress reported to the caller, the lock free once it returns."""
    before = set(threading.enumerate())
    phases: list[str] = []
    job, folder = run_backup(origin="cli", data_dir=data_dir, progress=lambda phase, done, total: phases.append(phase))
    assert [thread.name for thread in threading.enumerate() if thread not in before] == [], "run_backup starts no thread"
    assert (job.status, job.origin, folder) == ("done", "cli", job_dir(data_dir, job.job_id)), f"run_backup returns the end state and the job's folder: {job}, {folder}"
    assert get_job(job.job_id, data_dir=data_dir) == job, "the state on disk is the one returned"
    assert phases[0] == "preparing" and phases[-1] == "finalizing" and {"database", "files"} <= set(phases), f"the caller sees every phase: {sorted(set(phases))}"
    assert not jobs._run_lock_held(data_dir), "the lock is free once run_backup returns"
    print_success(f"done in the calling thread, {len(phases)} progress reports")


def test_the_archive_is_named_after_its_creation_time_in_utc():
    created = datetime(2026, 10, 15, 12, 15, 0, tzinfo=timezone(timedelta(hours=2)))
    assert archive_name(created) == "librefolio-backup-20261015-101500.zip", f"12:15+02:00 is 10:15 UTC: {archive_name(created)}"
    print_success(archive_name(created))


def test_the_archive_of_a_job_whose_file_is_gone_is_not_found(data_dir):
    job, folder = run_backup(data_dir=data_dir)
    (folder / job.file_name).unlink()
    with pytest.raises(BackupJobNotFoundError, match="gone"):
        job_archive(job.job_id, data_dir=data_dir)
    print_success("archive removed → BackupJobNotFoundError")


# =============================================================================
# (b) one run at a time
# =============================================================================


@pytest.mark.parametrize("start", [start_backup, run_backup], ids=["start_backup", "run_backup"])
def test_a_backup_is_refused_while_the_run_lock_is_held(data_dir, start):
    """(b) The lock is held by a run elsewhere: the start is refused, and leaves no job behind."""
    with lock_held(data_dir):
        with pytest.raises(BackupBusyError):
            start(data_dir=data_dir)
        assert job_folders(data_dir) == [], f"a refused start creates no job: {job_folders(data_dir)}"
    job, _ = run_backup(data_dir=data_dir)
    assert job.status == "done", "once the lock is released, a backup runs"
    print_success(f"{start.__name__} refused while the lock was held, a run after it succeeded")


def test_while_a_backup_runs_its_archive_is_not_ready_it_cannot_be_deleted_and_no_other_starts(data_dir, gate):
    """(a)(b) A run in progress, held at the gate: it reads as running, the lock being held by its own thread."""
    print_section("A run in progress")
    job = start_backup(data_dir=data_dir)
    assert gate.entered.wait(DEADLINE_S), "precondition: the run reached its build"
    assert get_job(job.job_id, data_dir=data_dir).status == "running", "a run in progress reads as running"
    with pytest.raises(BackupJobStateError) as not_ready:
        job_archive(job.job_id, data_dir=data_dir)
    with pytest.raises(BackupJobStateError) as running:
        delete_job(job.job_id, data_dir=data_dir)
    assert (not_ready.value.status, running.value.status) == ("running", "running"), "both errors say the job is running"
    for other in (start_backup, run_backup):
        with pytest.raises(BackupBusyError):
            other(data_dir=data_dir)
    assert job_folders(data_dir) == [job.job_id], f"the refused starts created nothing, the running job was not deleted: {job_folders(data_dir)}"
    gate.opened.set()
    assert wait_until_finished(job.job_id, data_dir).status == "done", "once the gate opens, the run ends done"
    print_success("running: not ready, not deletable, busy for others; then done")


# =============================================================================
# (c) a run that died with its process
# =============================================================================


def test_a_running_state_with_a_free_lock_reads_as_interrupted_and_is_written_down(data_dir):
    """(c) The lock is what says running: free, the run is dead. The interruption is persisted, not recomputed."""
    print_section("A dead run")
    created = datetime.now(UTC) - timedelta(minutes=5)
    job = write_job(data_dir, status="running", created=created)
    read = get_job(job.job_id, data_dir=data_dir)
    assert (read.status, read.error_code, read.phase) == ("failed", "backup_interrupted", None), f"a running state nobody holds the lock for is an interrupted run: {read}"
    assert read.finished_at is not None and read.finished_at >= created, f"the interruption is dated: {read.finished_at}"
    stored = BackupJob.from_json((job_dir(data_dir, job.job_id) / STATE_FILE).read_text(encoding="utf-8"))
    assert stored == read, f"the interruption is written down: {stored}"
    assert get_job(job.job_id, data_dir=data_dir) == read, "a second read gives the same state, with the same date"
    with pytest.raises(BackupJobStateError) as raised:
        job_archive(job.job_id, data_dir=data_dir)
    assert raised.value.status == "failed", "an interrupted job has no archive to give"
    delete_job(job.job_id, data_dir=data_dir)
    assert job_folders(data_dir) == [], "an interrupted job can be deleted"
    print_success("running + free lock → failed/backup_interrupted, persisted")


def test_a_running_state_stays_running_while_its_lock_is_held(data_dir):
    job = write_job(data_dir, status="running", created=datetime.now(UTC) - timedelta(minutes=5))
    state = job_dir(data_dir, job.job_id) / STATE_FILE
    before = state.read_bytes()
    with lock_held(data_dir):
        assert get_job(job.job_id, data_dir=data_dir) == job, "with the lock held, the run is alive: it reads as running, unchanged"
    assert state.read_bytes() == before, "reading a live run writes nothing"
    print_success("running + held lock → running")


# =============================================================================
# (d) how a run ends
# =============================================================================


def test_a_failed_build_ends_the_job_failed_with_its_work_files_removed_and_the_lock_free(data_dir, monkeypatch):
    """(d) Any error of the build: failed/backup_failed, only the state left in the folder, the next start runs."""
    broken = BrokenBuild(jobs.build_archive)
    monkeypatch.setattr(jobs, "build_archive", broken)
    job = wait_until_finished(start_backup(data_dir=data_dir).job_id, data_dir)
    assert (job.status, job.error_code, job.phase, job.file_name) == ("failed", "backup_failed", None, None), f"a failed build ends the job failed/backup_failed: {job}"
    assert job.finished_at is not None, "a failed job is dated"
    assert os.listdir(job_dir(data_dir, job.job_id)) == [STATE_FILE], f"the work files (copy, partial archive, folders) are removed: {os.listdir(job_dir(data_dir, job.job_id))}"
    assert not jobs._run_lock_held(data_dir), "the lock is released after a failure"
    following = wait_until_finished(start_backup(data_dir=data_dir).job_id, data_dir)
    assert (following.status, broken.calls) == ("done", 2), f"the next start runs a real build to done: {following.status}, {broken.calls} builds"
    print_success("failed/backup_failed, work files removed, next run done")


def test_without_enough_space_the_job_fails_with_backup_no_space(data_dir, monkeypatch):
    no_space(monkeypatch)
    job = wait_until_finished(start_backup(data_dir=data_dir).job_id, data_dir)
    assert (job.status, job.error_code, job.file_name) == ("failed", "backup_no_space", None), f"no space: failed/backup_no_space, no archive: {job}"
    assert os.listdir(job_dir(data_dir, job.job_id)) == [STATE_FILE], "nothing but the state in the job folder"
    assert not jobs._run_lock_held(data_dir), "the lock is released"
    print_success("failed/backup_no_space")


@pytest.mark.parametrize("outcome", ["done", "backup_failed", "backup_no_space"])
def test_the_final_state_is_on_disk_before_the_lock_is_released(data_dir, monkeypatch, outcome):
    """(d) Released first, the lock would let a reader find a running state with a free lock: an interrupted run."""
    if outcome == "backup_failed":
        monkeypatch.setattr(jobs, "build_archive", BrokenBuild(jobs.build_archive))
    elif outcome == "backup_no_space":
        no_space(monkeypatch)
    releases = watch_releases(data_dir, monkeypatch)
    job, _ = run_backup(data_dir=data_dir)
    assert (job.error_code or job.status) == outcome, f"precondition: the run ended {outcome}: {job}"
    held = [release for release in releases if release.held]
    assert held, "the run released no lock it held"
    at_release = held[-1]
    assert at_release.states == {job.job_id: json.loads(job.to_json())}, f"when the run released its lock, the state on disk must already be the final one: {at_release.states}"
    expected = sorted([STATE_FILE, *([job.file_name] if job.file_name else [])])
    assert at_release.listing == {job.job_id: expected}, f"and the work files already removed: {at_release.listing}"
    print_success(f"{outcome}: final state written, then the lock released")


@pytest.mark.parametrize(
    ("cause", "error_code"),
    [
        pytest.param(errno.ENOSPC, "backup_no_space", id="ENOSPC"),
        pytest.param(EDQUOT, "backup_no_space", id="EDQUOT", marks=needs_edquot),
        pytest.param(errno.EIO, "backup_failed", id="EIO"),
    ],
)
def test_a_file_that_fails_while_archived_ends_the_job_by_its_cause(data_dir, monkeypatch, cause, error_code):
    """(d) ``PartialEntryError``: a full disk or quota behind it is ``backup_no_space``, any other cause ``backup_failed``."""
    print_section("A build that stops after the space check")
    error = os_error(cause)

    def stopped_build(data_dir, work_dir, target, **kwargs):
        target.with_name(target.name + ".part").write_bytes(b"PK part of an archive")
        raise PartialEntryError("custom-uploads/logo.png") from error

    monkeypatch.setattr(jobs, "build_archive", stopped_build)
    cleanup = watch_cleanup(monkeypatch)
    job, folder = run_backup(data_dir=data_dir)
    assert (job.status, job.error_code, job.file_name) == ("failed", error_code, None), f"{errno.errorcode[cause]} behind the failure: failed/{error_code}, no archive: {job}"
    assert cleanup == [sorted([STATE_FILE, archive_name(job.created_at) + ".part"])], f"the partial archive was in the job folder when the cleanup ran: {cleanup}"
    assert os.listdir(folder) == [STATE_FILE], f"and only the state is left: {os.listdir(folder)}"
    assert not jobs._run_lock_held(data_dir), "the lock is released"
    print_success(f"{errno.errorcode[cause]} → {error_code}, partial archive removed")


def test_a_file_that_fails_while_it_is_read_ends_the_job_failed_and_its_partial_archive_removed(data_dir, monkeypatch):
    """(d) A real build: logo.png reads its first block, then fails (``EIO``). Part of it is in the archive already, so
    the build stops instead of leaving it out; the job ends ``backup_failed`` and the partial archive is removed."""
    monkeypatch.setattr(archive, "_CHUNK", 256)
    monkeypatch.setattr(archive, "os", FailingDiskOs(reads_badly=data_dir / "custom-uploads" / "logo.png"))
    cleanup = watch_cleanup(monkeypatch)
    job, folder = run_backup(data_dir=data_dir)
    assert (job.status, job.error_code, job.file_name, job.skipped) == ("failed", "backup_failed", None, ()), f"a file failing half-way stops the backup, it is not left out: {job}"
    assert cleanup == [sorted([STATE_FILE, archive_name(job.created_at) + ".part"])], f"the build had written part of the archive when it stopped: {cleanup}"
    assert os.listdir(folder) == [STATE_FILE], f"the partial archive is removed: {os.listdir(folder)}"
    print_success("read error half-way → backup_failed, partial archive removed")


def test_a_disk_that_fills_up_while_the_archive_is_written_ends_the_job_with_backup_no_space(data_dir, monkeypatch):
    """(d) A real build on a disk with 256 bytes left once the space was checked: the archive's writes fail with
    ``ENOSPC``, the job ends ``backup_no_space`` (not ``backup_failed``) and the partial archive is removed."""
    monkeypatch.setattr(archive, "os", FailingDiskOs(room=256))
    cleanup = watch_cleanup(monkeypatch)
    job, folder = run_backup(data_dir=data_dir)
    assert (job.status, job.error_code, job.file_name) == ("failed", "backup_no_space", None), f"a disk full during the build is backup_no_space: {job}"
    assert len(cleanup) == 1 and archive_name(job.created_at) + ".part" in cleanup[0], f"the build had started the archive when the disk was full: {cleanup}"
    assert os.listdir(folder) == [STATE_FILE], f"the partial archive and the database copy are removed: {os.listdir(folder)}"
    assert not jobs._run_lock_held(data_dir), "the lock is released"
    print_success("disk full while writing → backup_no_space")


def test_a_database_copy_that_finds_the_disk_full_ends_the_job_with_backup_no_space(data_dir, monkeypatch):
    """(d) ``VACUUM INTO`` on a full disk raises SQLite's ``SQLITE_FULL``: a lack of space, not a failure of the build."""
    full = sqlite_full_error()

    def copy_on_a_full_disk(source: Path, target: Path):
        raise full

    monkeypatch.setattr(archive, "snapshot_database", copy_on_a_full_disk)
    job, folder = run_backup(data_dir=data_dir)
    assert (job.status, job.error_code, job.file_name) == ("failed", "backup_no_space", None), f"SQLITE_FULL from the copy is backup_no_space: {job}"
    assert os.listdir(folder) == [STATE_FILE], f"nothing but the state in the job folder: {os.listdir(folder)}"
    print_success("SQLITE_FULL → backup_no_space")


# =============================================================================
# (e) retention
# =============================================================================


def unreadable_job(data_dir: Path, content: bytes | None, dated: datetime) -> str:
    """A job folder whose state cannot be read (``None``: there is none), dated ``dated``."""
    job_id = uuid.uuid4().hex
    folder = ensure_private_dir(job_dir(data_dir, job_id), data_dir)
    if content is not None:
        (folder / STATE_FILE).write_bytes(content)
    date_folder(folder, dated)
    return job_id


def strangers(data_dir: Path, outside: Path) -> list[Path]:
    """What lives in the jobs folder without being a job folder: none of it is ever removed."""
    old = NOW - timedelta(hours=3)
    folder = ensure_private_dir(jobs_dir(data_dir), data_dir)
    finished = BackupJob(job_id=VALID_ID, origin="ui", status="done", phase=None, done_bytes=1, total_bytes=1, created_at=old, finished_at=old)
    places = [folder / "notes", folder / ("ABCDEF" * 5 + "AB"), outside]
    for place in places:
        place.mkdir()
        (place / STATE_FILE).write_text(finished.to_json(), encoding="utf-8")
        date_folder(place, old)
    plain_file = folder / uuid.uuid4().hex
    plain_file.write_bytes(b"a file named like a job")
    link = folder / uuid.uuid4().hex
    link.symlink_to(outside, target_is_directory=True)
    return [*places, plain_file, link, outside / STATE_FILE]


@needs_symlinks
def test_retention_removes_what_ended_more_than_an_hour_ago_and_nothing_else(data_dir, tmp_path):
    """(e) Finished more than 1 h ago, dead runs started more than 1 h ago, unreadable folders dated more than 1 h ago."""
    print_section("Retention")
    assert timedelta(hours=1) == JOB_RETENTION, f"a finished job is kept one hour, not {JOB_RETENTION}"
    with lock_held(data_dir):
        pass  # the lock file exists, free: as after any run
    hour = JOB_RETENTION
    removed = {
        "done 61 min ago": write_job(data_dir, status="done", created=NOW - 2 * hour, finished=NOW - hour - timedelta(minutes=1)).job_id,
        "failed 1 h and 1 µs ago": write_job(data_dir, status="failed", error_code="backup_failed", created=NOW - 2 * hour, finished=NOW - hour - timedelta(microseconds=1)).job_id,
        "dead run started 2 h ago": write_job(data_dir, status="running", created=NOW - 2 * hour).job_id,
        "unreadable state, folder 2 h old": unreadable_job(data_dir, b"{not json", NOW - 2 * hour),
        "no state, folder 2 h old": unreadable_job(data_dir, None, NOW - 2 * hour),
    }
    kept = {
        "done 59 min ago": write_job(data_dir, status="done", created=NOW - 2 * hour, finished=NOW - hour + timedelta(minutes=1)).job_id,
        "failed exactly 1 h ago": write_job(data_dir, status="failed", error_code="backup_no_space", created=NOW - 2 * hour, finished=NOW - hour).job_id,
        "dead run started 10 min ago": write_job(data_dir, status="running", created=NOW - timedelta(minutes=10)).job_id,
        "unreadable state, folder 5 min old": unreadable_job(data_dir, b"{not json", NOW - timedelta(minutes=5)),
    }
    others = strangers(data_dir, tmp_path / "outside")
    count = remove_expired_jobs(data_dir, now=NOW)
    left = [label for label, job_id in removed.items() if job_dir(data_dir, job_id).exists()]
    lost = [label for label, job_id in kept.items() if not job_dir(data_dir, job_id).exists()]
    assert not left, f"jobs that ended more than an hour ago must be removed: {left}"
    assert not lost, f"jobs that ended an hour ago or less must be kept: {lost}"
    assert count == len(removed), f"remove_expired_jobs says how many it removed: {count}, expected {len(removed)}"
    assert all(os.path.lexists(path) for path in others), f"what is not a job folder is never touched: {[str(path) for path in others if not os.path.lexists(path)]}"
    assert lock_path(data_dir).exists(), "the lock file stays"
    print_success(f"{count} removed, {len(kept)} kept, {len(others)} strangers untouched")


def test_retention_keeps_a_running_job_whose_lock_is_held(data_dir):
    running = write_job(data_dir, status="running", created=NOW - 2 * JOB_RETENTION)
    finished = write_job(data_dir, status="done", created=NOW - 3 * JOB_RETENTION, finished=NOW - 2 * JOB_RETENTION)
    with lock_held(data_dir):
        count = remove_expired_jobs(data_dir, now=NOW)
    assert job_dir(data_dir, running.job_id).exists(), "a run that holds the lock is alive, however long it has run: kept"
    assert not job_dir(data_dir, finished.job_id).exists(), "a job finished two hours ago is removed meanwhile"
    assert count == 1, f"one job removed: {count}"
    print_success("running with its lock held: kept")


def test_the_next_backup_removes_the_jobs_that_expired(data_dir):
    real_now = datetime.now(UTC)
    expired = write_job(data_dir, status="done", created=real_now - 3 * JOB_RETENTION, finished=real_now - 2 * JOB_RETENTION)
    job, _ = run_backup(data_dir=data_dir)
    assert job_folders(data_dir) == [job.job_id], f"the next start removed the job that finished two hours ago ({expired.job_id}): {job_folders(data_dir)}"
    print_success("expired job removed by the next start")


@pytest.fixture
def frozen_now(monkeypatch) -> datetime:
    """``jobs._now`` fixed at ``NOW``: a job's age is the one its state was written with, never one waited for."""
    monkeypatch.setattr(jobs, "_now", lambda: NOW)
    return NOW


def finished_job(data_dir: Path, *, finished: datetime, status: str = "done", error_code: str | None = None) -> tuple[BackupJob, Path]:
    """A job that finished at ``finished``, as its run left it on disk: its ``state.json`` and, when done, its archive."""
    job_id = uuid.uuid4().hex
    folder = ensure_private_dir(job_dir(data_dir, job_id), data_dir)
    created = finished - timedelta(minutes=1)
    file_name = file_size = file_sha256 = None
    if status == "done":
        file_name = archive_name(created)
        (folder / file_name).write_bytes(b"PK the archive of job " + job_id.encode("ascii"))
        file_size, file_sha256 = file_digest(folder / file_name)
    job = BackupJob(
        job_id=job_id,
        origin="ui",
        status=status,
        phase=None,
        done_bytes=100,
        total_bytes=100,
        created_at=created,
        finished_at=finished,
        file_name=file_name,
        file_size=file_size,
        file_sha256=file_sha256,
        error_code=error_code,
    )
    (folder / STATE_FILE).write_text(job.to_json(), encoding="utf-8")
    return job, folder


def expect_not_found(read, job_id: str, data_dir: Path) -> None:
    """``read`` of a job past its retention must answer ``BackupJobNotFoundError``, whatever the job held."""
    try:
        answer = read(job_id, data_dir=data_dir)
    except BackupJobNotFoundError:
        return
    pytest.fail(f"{read.__name__} of a job that finished more than {JOB_RETENTION} ago must answer BackupJobNotFoundError, it answered {answer!r}")


FINISHED = [
    pytest.param("done", None, id="done"),
    pytest.param("failed", "backup_failed", id="failed"),
    pytest.param("failed", "backup_no_space", id="no-space"),
    pytest.param("failed", "backup_interrupted", id="interrupted"),
]


@pytest.mark.parametrize(("status", "error_code"), FINISHED)
def test_a_finished_job_read_after_the_retention_is_not_found_and_its_folder_is_gone(data_dir, frozen_now, status, error_code):
    """(e) One microsecond past the hour, a read answers that there is no such job and removes its folder.

    The age is the one ``finished_at`` gives, whatever the outcome: a failure, or an interruption an earlier read wrote
    down, expires like an archive. The job that finished exactly an hour ago, beside it, still reads and is left alone.
    """
    print_section(f"Retention on read: {status} {error_code or ''}".strip())
    expired, folder = finished_job(data_dir, finished=frozen_now - JOB_RETENTION - timedelta(microseconds=1), status=status, error_code=error_code)
    kept, kept_folder = finished_job(data_dir, finished=frozen_now - JOB_RETENTION, status=status, error_code=error_code)
    kept_files = sorted(os.listdir(kept_folder))
    expect_not_found(get_job, expired.job_id, data_dir)
    assert not os.path.lexists(folder), f"the read must remove the folder of the expired job, state and archive included; it still holds {sorted(os.listdir(folder))}"
    expect_not_found(get_job, expired.job_id, data_dir)
    assert get_job(kept.job_id, data_dir=data_dir) == kept, "a job that finished exactly an hour ago is within the retention: it must read as written"
    assert sorted(os.listdir(kept_folder)) == kept_files, f"the read of the expired job must leave the other jobs alone: {sorted(os.listdir(kept_folder))} != {kept_files}"
    print_success(f"{status} {error_code or ''}: 1 h + 1 µs → not found, folder removed; exactly 1 h → read")


def test_the_archive_of_a_job_past_its_retention_is_never_served(data_dir, frozen_now):
    """(e) The download reads the job first: one microsecond past the hour there is no archive to serve, and it is removed."""
    expired, folder = finished_job(data_dir, finished=frozen_now - JOB_RETENTION - timedelta(microseconds=1))
    assert (folder / expired.file_name).is_file(), "precondition: the expired job's archive is on disk"
    expect_not_found(job_archive, expired.job_id, data_dir)
    assert not os.path.lexists(folder), "the read must remove the expired job's folder, its archive with it"
    print_success("archive 1 h + 1 µs after the end: not served, removed")


@pytest.mark.parametrize("age", [pytest.param(timedelta(0), id="just-finished"), pytest.param(timedelta(minutes=59), id="59-min"), pytest.param(JOB_RETENTION, id="exactly-1-h")])
def test_a_finished_job_within_the_retention_still_reads_and_serves_its_archive(data_dir, frozen_now, age):
    """(e) Up to the hour included, the job reads as written, its archive is served, and reading it changes nothing."""
    job, folder = finished_job(data_dir, finished=frozen_now - age)
    state = (folder / STATE_FILE).read_bytes()
    assert get_job(job.job_id, data_dir=data_dir) == job, f"a job that finished {age} ago is within the retention: it must read as written"
    assert job_archive(job.job_id, data_dir=data_dir) == (folder / job.file_name, job.file_name), f"the archive of a job that finished {age} ago must still be served"
    assert (folder / STATE_FILE).read_bytes() == state, "reading a finished job within the retention must write nothing"
    assert sorted(os.listdir(folder)) == sorted([STATE_FILE, job.file_name]), f"its folder must keep its state and its archive: {sorted(os.listdir(folder))}"
    print_success(f"finished {age} ago: read, archive served")


# =============================================================================
# (f) a job id is never a path
# =============================================================================


NOT_JOB_IDS = [
    pytest.param("../x", id="parent-folder"),
    pytest.param("a" * 31, id="31-hex"),
    pytest.param("a" * 33, id="33-hex"),
    pytest.param(VALID_ID.upper(), id="uppercase-hex"),
    pytest.param("", id="empty"),
    pytest.param(VALID_ID + "\n", id="trailing-newline"),
    pytest.param("../" + VALID_ID[3:], id="parent-folder-32-chars"),
]


def plant_decoy(data_dir: Path, value: str) -> Path | None:
    """A finished job, with its archive, where a path built from ``value`` below the jobs folder would land."""
    if not value:
        return None
    folder = jobs_dir(data_dir) / value
    os.makedirs(folder)
    created = datetime.now(UTC) - timedelta(minutes=1)
    decoy = BackupJob(job_id=value, origin="ui", status="done", phase=None, done_bytes=1, total_bytes=1, created_at=created, finished_at=created, file_name="decoy.zip", file_size=5, file_sha256="0" * 64)
    (folder / STATE_FILE).write_text(decoy.to_json(), encoding="utf-8")
    (folder / "decoy.zip").write_bytes(b"decoy")
    return folder


@pytest.mark.parametrize("value", NOT_JOB_IDS)
def test_a_job_id_is_never_a_path(data_dir, value):
    """(f) Even with a finished job where the path would land, what is not a job id is not found and nothing is removed."""
    ensure_private_dir(jobs_dir(data_dir), data_dir)
    decoy = plant_decoy(data_dir, value)
    for call in (get_job, job_archive, delete_job):
        with pytest.raises(BackupJobNotFoundError):
            call(value, data_dir=data_dir)
    if decoy is not None:
        assert sorted(os.listdir(decoy)) == sorted([STATE_FILE, "decoy.zip"]), f"the folder at {decoy} must be left as it was: {sorted(os.listdir(decoy))}"
    print_success(f"{value!r}: not found, nothing touched")


def test_an_uppercase_id_never_reaches_the_job_it_spells(data_dir):
    """(f) On a case-insensitive file system the uppercase id would open the real job's folder: it is refused first."""
    job, folder = run_backup(data_dir=data_dir)
    for call in (get_job, job_archive, delete_job):
        with pytest.raises(BackupJobNotFoundError):
            call(job.job_id.upper(), data_dir=data_dir)
    assert get_job(job.job_id, data_dir=data_dir) == job and (folder / job.file_name).is_file(), "the real job is untouched"
    print_success("uppercase id refused, real job untouched")


# =============================================================================
# (g) the state file
# =============================================================================


def test_a_job_state_reads_back_as_written_and_ignores_what_it_does_not_know():
    job = BackupJob(
        job_id=VALID_ID,
        origin="cli",
        status="done",
        phase=None,
        done_bytes=10,
        total_bytes=10,
        created_at=datetime(2026, 10, 15, 10, 15, tzinfo=UTC),
        finished_at=datetime(2026, 10, 15, 10, 16, tzinfo=UTC),
        file_name="librefolio-backup-20261015-101500.zip",
        file_size=10,
        file_sha256="a" * 64,
        warnings=("files_skipped",),
        skipped=("custom-uploads/link",),
    )
    assert BackupJob.from_json(job.to_json()) == job, "to_json then from_json gives the same job"
    data = json.loads(job.to_json())
    data.update(added_by_a_later_version=True, eta_seconds=12)
    assert BackupJob.from_json(json.dumps(data)) == job, "unknown keys are ignored"
    older = {key: value for key, value in json.loads(job.to_json()).items() if key not in ("warnings", "skipped", "error_code")}
    assert BackupJob.from_json(json.dumps(older)) == replace(job, warnings=(), skipped=(), error_code=None), "a state without the optional keys reads with their defaults"
    print_success("round trip; unknown keys ignored; missing optional keys defaulted")


def test_a_state_file_with_unknown_keys_is_read_from_disk(data_dir):
    job, folder = run_backup(data_dir=data_dir)
    data = json.loads((folder / STATE_FILE).read_text(encoding="utf-8"))
    data["written_by_a_newer_version"] = {"anything": [1, 2, 3]}
    (folder / STATE_FILE).write_text(json.dumps(data), encoding="utf-8")
    assert get_job(job.job_id, data_dir=data_dir) == job, "get_job ignores the keys it does not know"
    print_success("state with an unknown key read")


@needs_symlinks
def test_a_job_keeps_at_most_50_left_out_entries(data_dir):
    links = [f"custom-uploads/link-{index:02d}" for index in range(60)]
    for entry in links:
        (data_dir / entry).symlink_to("nowhere")
    job, _ = run_backup(data_dir=data_dir)
    assert (job.status, job.warnings) == ("done", ("files_skipped",)), f"links left out: done, with the warning files_skipped: {job}"
    assert len(job.skipped) == len(set(job.skipped)) == 50, f"the state keeps 50 distinct left-out entries of the 60, not {len(job.skipped)}"
    assert set(job.skipped) <= set(links), f"every kept entry is one of the links: {sorted(set(job.skipped) - set(links))}"
    print_success("60 left out → 50 kept")


# =============================================================================
# (h) without fcntl
# =============================================================================


@pytest.fixture
def without_fcntl(monkeypatch) -> None:
    """Not POSIX: the run lock is a lock of the process, from a registry of this test only."""
    monkeypatch.setattr(jobs, "fcntl", None)
    monkeypatch.setattr(jobs, "_PROCESS_LOCKS", {})


def test_without_fcntl_runs_are_still_one_at_a_time_within_the_process(data_dir, without_fcntl):
    ensure_private_dir(jobs_dir(data_dir), data_dir)
    first, second = jobs._RunLock(lock_path(data_dir)), jobs._RunLock(lock_path(data_dir))
    assert first.try_acquire(), "precondition: the lock is free"
    try:
        assert not second.try_acquire(), "a second holder is refused while the first holds the lock"
        for start in (start_backup, run_backup):
            with pytest.raises(BackupBusyError):
                start(data_dir=data_dir)
        assert job_folders(data_dir) == [], "the refused starts created nothing"
    finally:
        first.release()
    assert second.try_acquire(), "once released, the lock can be taken again"
    second.release()
    job, _ = run_backup(data_dir=data_dir)
    assert job.status == "done", f"a run under the process lock ends done: {job}"
    print_success("process-local lock: one run at a time")


def test_without_fcntl_a_running_job_still_reads_as_running(data_dir, without_fcntl, gate):
    """(h) The process lock serialises the runs; the job state must still tell a live run from a dead one."""
    job = start_backup(data_dir=data_dir)
    assert gate.entered.wait(DEADLINE_S), "precondition: the run reached its build"
    during = get_job(job.job_id, data_dir=data_dir)
    gate.opened.set()
    wait_until_finished(job.job_id, data_dir)
    final = get_job(job.job_id, data_dir=data_dir)
    assert during.status == "running", f"a run in progress read as {during.status}/{during.error_code} (written down, then overwritten: it ended {final.status}): _run_lock_held returns False when backups/.jobs/.lock does not exist, and the process-local lock never creates that file"
    print_success("running job reads as running without fcntl")


# =============================================================================
# (i) what counts as a lack of space
# =============================================================================


OUT_OF_SPACE = [
    pytest.param(lambda: os_error(errno.ENOSPC), id="ENOSPC"),
    pytest.param(lambda: os_error(EDQUOT), id="EDQUOT", marks=needs_edquot),
    pytest.param(sqlite_full_error, id="SQLITE_FULL"),
    pytest.param(lambda: partial_entry(os_error(errno.ENOSPC)), id="partial-entry-caused-by-ENOSPC"),
    pytest.param(lambda: caused_by(sqlite_full_error()), id="caused-by-SQLITE_FULL"),
    pytest.param(lambda: raised_while_handling(os_error(errno.ENOSPC)), id="raised-while-handling-ENOSPC"),
    pytest.param(lambda: caused_by(raised_while_handling(os_error(EDQUOT))), id="context-of-a-cause", marks=needs_edquot),
    pytest.param(lambda: chain(8, os_error(errno.ENOSPC)), id="eighth-of-the-chain"),
]

NOT_OUT_OF_SPACE = [
    pytest.param(lambda: OSError("an error without errno"), id="errno-None"),
    pytest.param(lambda: os_error(errno.EIO), id="EIO"),
    pytest.param(lambda: PermissionError(errno.EACCES, os.strerror(errno.EACCES)), id="EACCES"),
    pytest.param(lambda: RuntimeError("the build failed"), id="RuntimeError"),
    pytest.param(sqlite_syntax_error, id="SQLITE_ERROR"),
    pytest.param(lambda: sqlite3.OperationalError("database or disk is full"), id="SQLite-message-without-its-code"),
    pytest.param(lambda: partial_entry(os_error(errno.EIO)), id="partial-entry-caused-by-EIO"),
    pytest.param(lambda: chain(9, os_error(errno.ENOSPC)), id="ninth-of-the-chain"),
]


@pytest.mark.parametrize("make", OUT_OF_SPACE)
def test_a_full_disk_or_quota_is_a_lack_of_space_itself_or_as_a_cause(make):
    """(i) The file system's full disk or quota, or SQLite's SQLITE_FULL, as the failure or among its 8 first links."""
    error = make()
    assert jobs.out_of_space(error) is True, f"{type(error).__name__}: {error} must count as a lack of space"
    print_success(f"{type(error).__name__} → lack of space")


@pytest.mark.parametrize("make", NOT_OUT_OF_SPACE)
def test_any_other_failure_is_not_a_lack_of_space(make):
    """(i) Neither another errno nor SQLite's words without its code: those end as backup_failed, with the cause logged."""
    error = make()
    assert jobs.out_of_space(error) is False, f"{type(error).__name__}: {error} must not count as a lack of space"
    print_success(f"{type(error).__name__} → not a lack of space")


@pytest.mark.parametrize("link", ["__cause__", "__context__"])
def test_a_cycle_of_causes_ends_the_walk(link):
    """(i) Two failures that are each other's cause (or context): the walk ends, and finds no lack of space."""
    first, second = RuntimeError("first"), RuntimeError("second")
    setattr(first, link, second)
    setattr(second, link, first)
    answers: list[bool] = []
    walker = threading.Thread(target=lambda: answers.append(jobs.out_of_space(first)), name="out-of-space-walk", daemon=True)
    walker.start()
    walker.join(WALK_DEADLINE_S)
    assert not walker.is_alive(), f"out_of_space was still walking a cycle of {link} after {WALK_DEADLINE_S}s: the walk must be bounded"
    assert answers == [False], f"a cycle without a full disk is no lack of space: {answers}"
    print_success(f"cycle of {link} → walk ended, False")


# =============================================================================
# (j) backup_in_progress
# =============================================================================


def check_lock_path(data_dir: Path) -> Path:
    """The lock of the restore checks (lot B2b): held while an archive is checked, in its request's thread or after."""
    return stages_dir(data_dir) / STAGE_LOCK_FILE


#: The two locks ``backup_in_progress`` asks about, by what holds them.
LOCKS = {"a-backup": lock_path, "a-restore-check": check_lock_path}


def everything_below(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def free_lock_files(data_dir: Path) -> None:
    """Both lock files on disk, as runs that ended leave them: taken once, released."""
    for path in (lock_path(data_dir), check_lock_path(data_dir)):
        ensure_private_dir(path.parent, data_dir)
        holder = jobs._RunLock(path)
        assert holder.try_acquire(), f"precondition: nobody holds {path.name}"
        holder.release()


def test_without_lock_files_nothing_is_in_progress_and_nothing_is_created(data_dir):
    """(j) A data directory where no backup ever ran nor archive was checked: false, and no file or folder created."""
    print_section("backup_in_progress")
    before = everything_below(data_dir)
    assert backup_in_progress(data_dir=data_dir) is False, "no lock file: nothing in progress"
    assert everything_below(data_dir) == before, f"read only: nothing created: {sorted(set(everything_below(data_dir)) - set(before))}"


def test_free_lock_files_are_not_in_progress_and_stay_free(data_dir):
    """(j) Both lock files there, nobody holding them: false, and both can still be taken afterwards."""
    free_lock_files(data_dir)
    before = everything_below(data_dir)
    assert backup_in_progress(data_dir=data_dir) is False, "free locks: nothing in progress"
    assert everything_below(data_dir) == before, "nothing created"
    for path in (lock_path(data_dir), check_lock_path(data_dir)):
        again = jobs._RunLock(path)
        assert again.try_acquire(), f"the probe left {path.name} free"
        again.release()


@pytest.mark.parametrize("holder", sorted(LOCKS))
def test_a_held_lock_is_work_in_progress(data_dir, monkeypatch, holder):
    """(j) Either lock held (here by this test, as by a backup or a check in another worker), the other free: true; the
    configured data directory is the one asked about without ``data_dir``. Released: false again."""
    free_lock_files(data_dir)
    lock = jobs._RunLock(LOCKS[holder](data_dir))
    assert lock.try_acquire(), "precondition: nobody holds it"
    try:
        given = backup_in_progress(data_dir=data_dir)
        monkeypatch.setattr(jobs, "get_data_dir", lambda: data_dir)
        configured = backup_in_progress()
    finally:
        lock.release()
    assert (given, configured, backup_in_progress(data_dir=data_dir)) == (True, True, False), f"{holder}: (held, held without data_dir, released): {(given, configured)}"
    print_success(f"{holder}: in progress while held")


@pytest.mark.parametrize("holder", sorted(LOCKS))
def test_without_fcntl_backup_in_progress_follows_the_locks_of_the_process(data_dir, without_fcntl, holder):
    """(j) Not POSIX: the locks are the process's own, and no file: false, then true while one is held, false once it is
    released, and nothing created on disk."""
    before = everything_below(data_dir)
    lock = jobs._RunLock(LOCKS[holder](data_dir))
    idle = backup_in_progress(data_dir=data_dir)
    assert lock.try_acquire(), "precondition: nobody holds it"
    try:
        held = backup_in_progress(data_dir=data_dir)
    finally:
        lock.release()
    assert (idle, held, backup_in_progress(data_dir=data_dir)) == (False, True, False), f"{holder}: (before, held, released): {(idle, held)}"
    assert everything_below(data_dir) == before, "the locks of the process are no files: nothing created"


# =============================================================================
# (k) the running job, named by its lock (B-8)
# =============================================================================


def lock_record(data_dir: Path) -> str:
    """What the run lock holds (B-8: the job id of the run that holds it), read as another worker reads it: from the
    file, never from its holder. The spaces and line breaks around it are not part of the record."""
    return lock_path(data_dir).read_bytes().decode("ascii", errors="replace").strip()


def named_job(error: BackupBusyError) -> tuple[str, str, str] | str | None:
    """What a refusal says of the running job (``BackupBusyError.running``, B-8): ``(job_id, origin, status)`` of the job
    it carries, None when it carries none, and a sentence when it has no ``running`` at all (before B-8) or holds
    something else than a job."""
    if not hasattr(error, "running"):
        return "BackupBusyError has no running: the refusal names no job"
    running = error.running
    if running is None:
        return None
    if not isinstance(running, BackupJob):
        return f"BackupBusyError.running is not a BackupJob: {running!r}"
    return (running.job_id, running.origin, running.status)


def refusals(data_dir: Path) -> dict[str, tuple[str, str, str] | str | None]:
    """Both starts while the run lock is held, the API's (``start_backup``) and the CLI's (``run_backup``): each must be
    refused, with ``BackupBusyError`` (the API's 409 ``backup_busy``); what each refusal says of the running job. A start
    that raises anything else instead is no refusal but a crash, which the API would answer with a 500: it is kept as a
    sentence naming the exception, for the caller's assertion to show, and the other start is still tried."""
    named: dict[str, tuple[str, str, str] | str | None] = {}
    for start in (start_backup, run_backup):
        try:
            start(data_dir=data_dir)
        except BackupBusyError as refused:
            named[start.__name__] = named_job(refused)
        except Exception as exc:  # noqa: BLE001 — kept and asserted by the caller: raised from here, it would hide what the other start does
            named[start.__name__] = f"raised {type(exc).__name__} ({exc}) instead of BackupBusyError: a crash, not a refusal (the API would answer 500, not 409 backup_busy)"
        else:
            pytest.fail(f"{start.__name__} was not refused while the run lock was held")
    return named


def running_elsewhere(data_dir: Path, origin: str = "ui") -> BackupJob:
    """The state of a job in progress, as the run that holds the lock in another worker or process wrote it."""
    return write_job(data_dir, status="running", created=datetime.now(UTC) - timedelta(minutes=1), origin=origin)


def ended_a_minute_ago(data_dir: Path, status: str, error_code: str | None = None) -> str:
    """The id of a job that ended a minute ago, as its run left it on disk: well within the retention."""
    now = datetime.now(UTC)
    return write_job(data_dir, status=status, error_code=error_code, created=now - timedelta(minutes=2), finished=now - timedelta(minutes=1)).job_id


#: What a run lock may hold that is no job id, while a job's state says running and the lock is held. The spellings and
#: the paths are built from that running job: each would reach it, were it taken for an id.
NOT_A_JOB_ID: dict[str, Callable[[Path, BackupJob], bytes]] = {
    "empty": lambda data_dir, running: b"",
    "garbage": lambda data_dir, running: b"not a job id",
    "bytes-not-text": lambda data_dir, running: b"\xff\xfe\x00\x9c",
    "the-id-in-capitals": lambda data_dir, running: running.job_id.upper().encode("ascii"),
    "relative-path-to-the-job": lambda data_dir, running: f"../{jobs_dir(data_dir).name}/{running.job_id}".encode("ascii"),
    "absolute-path-to-the-job": lambda data_dir, running: os.fsencode(job_dir(data_dir, running.job_id)),
}

#: Job ids a run lock may still hold once their job no longer runs, by what became of the job: built in ``data_dir``.
#: The ``state-*`` jobs have a state that cannot be read as a job, each in its own way, so that every exception such a
#: read raises (``ValueError``, ``KeyError``, ``TypeError``) is met once by a refused start.
NO_LONGER_RUNNING: dict[str, Callable[[Path], str]] = {
    "gone": lambda data_dir: uuid.uuid4().hex,
    "done": lambda data_dir: ended_a_minute_ago(data_dir, "done"),
    "failed": lambda data_dir: ended_a_minute_ago(data_dir, "failed", "backup_failed"),
    "interrupted": lambda data_dir: ended_a_minute_ago(data_dir, "failed", "backup_interrupted"),
    "state-unreadable": lambda data_dir: unreadable_job(data_dir, b"{not json", datetime.now(UTC)),
    "state-without-fields": lambda data_dir: unreadable_job(data_dir, b"{}", datetime.now(UTC)),
    "state-of-wrong-types": lambda data_dir: unreadable_job(data_dir, b'{"created_at": 5}', datetime.now(UTC)),
}


@pytest.mark.parametrize("origin", ["ui", "panel"])
def test_while_a_run_holds_the_lock_the_lock_holds_its_id_and_each_refused_start_names_its_job(data_dir, gate, origin):
    """(k) B-8: a run in progress, held at the gate (its lock taken by its own thread): the lock holds its job id, and each
    start refused meanwhile names that job (its id, its origin, running). A read of the job (a probe of the lock) and the
    refused starts leave the record as it was, and create nothing."""
    print_section(f"B-8: the running job named by its lock (origin {origin})")
    job = start_backup(origin=origin, data_dir=data_dir)
    assert gate.entered.wait(DEADLINE_S), "precondition: the run reached its build"
    assert get_job(job.job_id, data_dir=data_dir).status == "running", "precondition: the run reads as running"
    recorded = lock_record(data_dir)
    named = refusals(data_dir)
    kept, created = lock_record(data_dir), job_folders(data_dir)
    gate.opened.set()
    assert wait_until_finished(job.job_id, data_dir).status == "done", "once the gate opens, the run ends done"
    assert recorded == job.job_id, f"while the run holds the lock, the lock must hold its job id {job.job_id}: {recorded!r}"
    assert named == dict.fromkeys(named, (job.job_id, origin, "running")), f"each start refused while the run holds the lock must name its job (id, origin, running): {named}"
    assert kept == job.job_id, f"a read of the job and the refused starts must leave the record as it was: {kept!r}"
    assert created == [job.job_id], f"the refused starts created nothing: {created}"
    print_success(f"the lock holds the run's id; both refusals name its job, origin {origin}")


def test_the_cli_run_records_its_id_too_and_a_start_refused_meanwhile_names_it(data_dir):
    """(k) B-8: the CLI's run (``run_backup`` in the calling thread, as ``scripts/backup_cli.py`` runs it) takes the lock
    as the API's runs do. Seen from its first progress report, while it holds the lock: the lock holds its id, and a start
    of the Backup tab refused meanwhile names it, origin ``cli``."""
    seen: dict[str, object] = {}

    def progress(phase: str, done: int, total: int) -> None:
        if seen:
            return
        try:
            seen["record"] = lock_record(data_dir)
            start_backup(origin="ui", data_dir=data_dir)
        except BackupBusyError as refused:
            seen["named"] = named_job(refused)
        except Exception as exc:  # noqa: BLE001 — kept and asserted below: raised from here, it would fail the run, not the test
            seen["named"] = f"the probe raised {type(exc).__name__}: {exc}"
        else:
            seen["named"] = "start_backup was not refused while the CLI's run held the lock"

    job, _ = run_backup(origin="cli", data_dir=data_dir, progress=progress)
    assert job.status == "done", f"precondition: the CLI's run ends done: {job}"
    assert seen, "precondition: the CLI's run reported its progress"
    assert seen.get("record") == job.job_id, f"while the CLI's run holds the lock, the lock must hold its job id {job.job_id}: {seen.get('record')!r}"
    assert seen["named"] == (job.job_id, "cli", "running"), f"a start refused while the CLI's run holds the lock must name it (id, origin cli, running): {seen['named']}"
    print_success("the CLI's run: its id in the lock, named by a refused start")


@pytest.mark.parametrize("origin", ["ui", "panel", "cli"])
def test_a_lock_held_elsewhere_names_the_running_job_whose_id_it_holds(data_dir, origin):
    """(k) B-8, across workers: the run that holds the lock runs in another worker or process (here the test holds it),
    and the file is all this process can know of it. The lock holds the id of a job whose state says running: both
    starts refused name that job, with its origin, and create nothing."""
    running = running_elsewhere(data_dir, origin)
    with lock_held(data_dir):
        lock_path(data_dir).write_bytes(running.job_id.encode("ascii"))
        named = refusals(data_dir)
    assert named == dict.fromkeys(named, (running.job_id, origin, "running")), f"a lock held elsewhere, holding the id of a running job of origin {origin}, must name that job: {named}"
    assert job_folders(data_dir) == [running.job_id], f"the refused starts created nothing: {job_folders(data_dir)}"
    print_success(f"lock held elsewhere: both refusals name the running job of origin {origin}")


@pytest.mark.parametrize("content", sorted(NOT_A_JOB_ID))
def test_a_lock_that_holds_no_job_id_names_no_job_though_one_runs(data_dir, content):
    """(k) B-8: the lock is held and a job's state says running, but the lock holds no job id (``NOT_A_JOB_ID``): empty,
    as in the instant before a run records its id; garbage; bytes that are not text; the running job's id in capitals; a
    path, relative or absolute, to the running job's folder. Both starts are refused naming no job, ``running`` None: the
    content is never taken as a path nor bent into an id, and no job is guessed from a running state."""
    running = running_elsewhere(data_dir)
    with lock_held(data_dir):
        lock_path(data_dir).write_bytes(NOT_A_JOB_ID[content](data_dir, running))
        named = refusals(data_dir)
    assert named == dict.fromkeys(named, None), f"a lock holding {content} must name no job, though the state of {running.job_id} says running: {named}"
    print_success(f"{content}: refused, no job named")


@pytest.mark.parametrize("stale", sorted(NO_LONGER_RUNNING))
def test_a_lock_that_holds_the_id_of_a_job_no_longer_running_names_no_job(data_dir, stale):
    """(k) B-8: the lock is held and a job's state says running, but the lock holds the id of another job, one that no
    longer runs (``NO_LONGER_RUNNING``), as a run that ended may leave the lock:

    - ``gone``: there is no such job;
    - ``done``, ``failed``, ``interrupted``: it ended a minute ago;
    - ``state-unreadable``: its state is not JSON (``ValueError``);
    - ``state-without-fields``: its state is ``{}``, JSON without a field (``KeyError`` in ``BackupJob.from_json``);
    - ``state-of-wrong-types``: its state's ``created_at`` is a number (``TypeError`` in ``BackupJob.from_json``).

    Both starts are refused naming no job, ``running`` None. A refusal reads the job its lock names, so the three states
    that cannot be read matter: whatever their read raises, a refused start must still raise ``BackupBusyError``, the
    API's 409 ``backup_busy``; any other exception would reach the API as a 500, for a start that only had to wait."""
    running = running_elsewhere(data_dir)
    stale_id = NO_LONGER_RUNNING[stale](data_dir)
    assert is_job_id(stale_id) and stale_id != running.job_id, f"precondition: the lock holds a job id, not the running job's: {stale_id!r}"
    with lock_held(data_dir):
        lock_path(data_dir).write_bytes(stale_id.encode("ascii"))
        named = refusals(data_dir)
    assert named == dict.fromkeys(named, None), f"a lock holding the id of a job {stale} must name no job, though the state of {running.job_id} says running: {named}"
    print_success(f"{stale}: refused, no job named")


def test_what_a_run_that_ended_left_in_the_lock_names_no_job_to_the_next_holder(data_dir):
    """(k) B-8: a run ends and frees the lock, leaving in the file whatever it leaves there; the next holder (here the
    test, as a run in the instant before it records its own id) is named by none of it: both starts refused name no
    job, the job of the run that ended being done."""
    ended, _ = run_backup(data_dir=data_dir)
    assert ended.status == "done", f"precondition: the first run ended done: {ended}"
    with lock_held(data_dir):
        named = refusals(data_dir)
    assert named == dict.fromkeys(named, None), f"what the run {ended.job_id} left in the lock must not name its job, done, to the refusals of the next holder: {named}"
    print_success("what a run that ended left: no job named")


def test_the_record_of_a_run_replaces_whatever_the_lock_held(data_dir, gate):
    """(k) B-8: a lock file that already holds more than an id (three ids, one per line) is rewritten whole by the run
    that takes it: while it runs, the lock holds its id and nothing of the old text, and a refused start names its job."""
    ensure_private_dir(jobs_dir(data_dir), data_dir)
    lock_path(data_dir).write_bytes(f"{VALID_ID}\n".encode("ascii") * 3)
    job = start_backup(data_dir=data_dir)
    assert gate.entered.wait(DEADLINE_S), "precondition: the run reached its build"
    recorded = lock_record(data_dir)
    named = refusals(data_dir)
    gate.opened.set()
    assert wait_until_finished(job.job_id, data_dir).status == "done", "once the gate opens, the run ends done"
    assert recorded == job.job_id, f"the run's record must replace the lock's old text whole: {recorded!r}"
    assert named == dict.fromkeys(named, (job.job_id, "ui", "running")), f"each start refused while the run holds the lock must name its job: {named}"
    print_success("the lock's old text replaced by the run's id")


# =============================================================================
# (B-50) an unreadable state is «not found», never a 500
# =============================================================================
# The defect (measured 19/10 and 20/10): a job's state.json that is JSON but no object ([], null, 5, "x") raises
# AttributeError from get_job, remove_expired_jobs, end_interrupted_jobs and every start (_prepare runs
# remove_expired_jobs first): a 500 for the Backup tab and the hosting panel, a traceback for the CLI, until someone
# removes the folder by hand. A whole state whose finished_at has no time zone does the same with a TypeError (the
# retention subtracts it from an aware now, outside the loops' try), end_interrupted_jobs excepted. The other unreadable
# contents (empty, not JSON, {}, a field of the wrong type, a date that is no date, bytes that are not UTF-8) break
# get_job only: the job's GET, file and DELETE are 500s. A state.json that is a folder (IsADirectoryError), or that the
# server may not read (PermissionError), escapes everywhere as an OSError: every start fails (500 backup_failed, the
# CLI's exit 1).
# The decision (coordinator, 19/10 17:37 and 20/10 09:06), verbatim: «B-50: sì, la cura in 2 file, con il 404
# `backup_job_not_found` per uno stato illeggibile, sia nel backup sia nel ripristino» and «Il perimetro di B-50: approvo
# la tua proposta. Contano come «illeggibile» (cioè 404) anche lo `state.json` che è una cartella e quello senza
# permessi di lettura. Gli altri `OSError`, quelli transitori, restano un 500 che la scheda riprova.» Added 20/10: a
# finished_at without a time zone is unreadable too (the cure's from_json refuses it, a ValueError).
# Red today: every case below but the two guards, green today and after the cure: a missing state (not found, no
# warning) and a transient OSError (EIO: the caller gets that very error).


#: The warning a read logs for a job whose state cannot be read, verbatim (B-50).
UNREADABLE_WARNING = "A backup job's state cannot be read"
#: Written into the states that are readable text but no job: it must reach no logged event. ``fromisoformat``'s own
#: message quotes it (``Invalid isoformat string: 'CANARY…'``), so a log of the error's message would leak it.
CANARY = "CANARY-B50-a-state-s-content-is-never-logged"
#: A warning through the jobs' own logger, before each capture: it must reach the capture, or «no such warning» would
#: prove nothing either way.
LOG_BARRIER = "b50 jobs test: a barrier through the jobs' own logger"
#: Added 20/10, measured with a probe: a whole state whose ``finished_at`` has no time zone. Today it blocks every start
#: as the non-objects do (a ``TypeError``); the cure's ``from_json`` refuses it (a ``ValueError``). Pinned where the
#: coordinator asked: the reads and their warning, a start, the removal of the expired jobs.
WITHOUT_TIME_ZONE = "finished-at-without-time-zone"


@contextmanager
def jobs_logs() -> Iterator[list[dict]]:
    """What is logged inside the block, behind a barrier: a warning through the jobs' own logger reaches the capture."""
    with capture_logs() as events:
        jobs.logger.warning(LOG_BARRIER)
        assert any(event.get("event") == LOG_BARRIER for event in events), f"barrier: the jobs' logger does not reach capture_logs: {events}"
        yield events


def unreadable_warnings(events: list[dict]) -> list[dict]:
    """The warnings of a state that cannot be read, among ``events``."""
    return [event for event in events if event.get("event") == UNREADABLE_WARNING]


def a_job_state(folder: Path, now: datetime, **changes: object) -> None:
    """In ``folder``, a job that finished a minute before ``now``, its archive beside its state, as its run left them;
    ``changes`` written over the state."""
    created = now - timedelta(minutes=2)
    name = archive_name(created)
    (folder / name).write_bytes(b"PK the archive of job " + folder.name.encode("ascii"))
    size, sha256 = file_digest(folder / name)
    job = BackupJob(job_id=folder.name, origin="ui", status="done", phase=None, done_bytes=100, total_bytes=100, created_at=created, finished_at=now - timedelta(minutes=1), file_name=name, file_size=size, file_sha256=sha256)
    (folder / STATE_FILE).write_text(json.dumps({**json.loads(job.to_json()), **changes}), encoding="utf-8")


def holding(content: bytes) -> Callable[[Path, datetime], None]:
    """A state of these bytes."""

    def plant(folder: Path, now: datetime) -> None:
        (folder / STATE_FILE).write_bytes(content)

    return plant


def changed(**changes: object) -> Callable[[Path, datetime], None]:
    """A whole job's state, but for ``changes``."""

    def plant(folder: Path, now: datetime) -> None:
        a_job_state(folder, now, **changes)

    return plant


def without_time_zone(folder: Path, now: datetime) -> None:
    """A whole job's state, but for its ``finished_at``: a minute before ``now`` in UTC, written without a time zone.
    Read as UTC it would be a job within its retention, read as a local time one past it or not yet ended: no zone may
    be guessed."""
    a_job_state(folder, now, finished_at=(now - timedelta(minutes=1)).replace(tzinfo=None).isoformat())


def a_folder(folder: Path, now: datetime) -> None:
    """A ``state.json`` that is a folder."""
    (folder / STATE_FILE).mkdir()


def not_readable(folder: Path, now: datetime) -> None:
    """A whole job's state that the server may not read: mode 000."""
    a_job_state(folder, now)
    (folder / STATE_FILE).chmod(0)


#: How each shape of a state that cannot be read is planted in a job's folder, given the time the test reads at.
PLANTS: dict[str, Callable[[Path, datetime], None]] = {
    "json-list": holding(json.dumps([CANARY]).encode("utf-8")),
    "json-null": holding(b"null"),
    "json-number": holding(b"5"),
    "json-string": holding(json.dumps(CANARY).encode("utf-8")),
    "empty-file": holding(b""),
    "not-json": holding(b"{not json"),
    "empty-object": holding(b"{}"),
    "created-at-a-number": holding(b'{"created_at": 5}'),
    "created-at-not-a-date": changed(created_at=CANARY),
    "not-utf-8": holding(b"\xff\xfe{"),
    "a-folder": a_folder,
    "mode-000": not_readable,
    WITHOUT_TIME_ZONE: without_time_zone,
}
#: Every shape (``PLANTS``) with the class of the error its read meets, which the warning names: the shapes the
#: decision names (19/10 17:37, 20/10 09:06), then the date without a time zone (20/10). JSON that is no object and
#: that date meet the ``ValueError`` of the cure's ``from_json`` (today: an ``AttributeError``; for the date, no error
#: from the read, the ``TypeError`` coming after it, from the retention's subtraction).
DECIDED: dict[str, str] = {
    "json-list": "ValueError",
    "json-null": "ValueError",
    "json-number": "ValueError",
    "json-string": "ValueError",
    "empty-file": "JSONDecodeError",
    "not-json": "JSONDecodeError",
    "empty-object": "KeyError",
    "created-at-a-number": "TypeError",
    "created-at-not-a-date": "ValueError",
    "not-utf-8": "UnicodeDecodeError",
    "a-folder": "IsADirectoryError",
    "mode-000": "PermissionError",
    WITHOUT_TIME_ZONE: "ValueError",
}
#: The shapes that stop, besides ``get_job``, every loop over the jobs today: JSON that is no object, a folder, mode 000.
BLOCKING = ("json-list", "json-null", "json-number", "json-string", "a-folder", "mode-000")
#: The shapes whose state is text holding ``CANARY``.
HOLDS_THE_CANARY = ("json-list", "json-string", "created-at-not-a-date")


def shapes(*names: str) -> list:
    """The parameters of the shapes ``names``, each its own id; ``mode-000`` skipped as root, who reads it all the same,
    and off POSIX."""
    return [pytest.param(name, id=name, marks=needs_permission_checks if name == "mode-000" else ()) for name in names]


def job_whose_state_cannot_be_read(data_dir: Path, shape: str, *, now: datetime, dated: datetime) -> str:
    """The id of a new job folder whose ``state.json`` has ``shape`` (``PLANTS``), planted as of ``now``; the folder
    dated ``dated`` once planted, its date being all ``remove_expired_jobs`` can go by."""
    job_id = uuid.uuid4().hex
    folder = ensure_private_dir(job_dir(data_dir, job_id), data_dir)
    PLANTS[shape](folder, now)
    date_folder(folder, dated)
    return job_id


@pytest.fixture
def plant_unreadable(data_dir) -> Iterator[Callable[..., str]]:
    """``job_whose_state_cannot_be_read`` in the test's data directory. Afterwards every state left at mode 000 gets its
    mode back, so that ``tmp_path`` can be removed whatever the test left."""

    def plant(shape: str, *, now: datetime, dated: datetime) -> str:
        return job_whose_state_cannot_be_read(data_dir, shape, now=now, dated=dated)

    yield plant
    for state in data_dir.rglob(STATE_FILE):
        if state.is_file() and not state.is_symlink() and mode(state) == 0:
            state.chmod(0o600)


def job_answer(call: Callable[..., object], job_id: str, data_dir: Path) -> str:
    """What ``call`` of the job answers: ``not found`` for ``BackupJobNotFoundError`` (the cure's subclass included),
    otherwise what it returned or raised instead; any other exception reaches the API as a 500."""
    try:
        value = call(job_id, data_dir=data_dir)
    except BackupJobNotFoundError:
        return "not found"
    except Exception as exc:  # noqa: BLE001 — named by the caller's assertion: the API would answer it with a 500
        return f"raised {type(exc).__name__} ({exc})"
    return f"returned {value!r}"


def returned_or_raised(call: Callable[..., object], *args: object, **kwargs: object) -> object:
    """What ``call`` returns, or a sentence naming what it raised instead, for the caller's assertion to show."""
    try:
        return call(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — named by the caller's assertion, beside what was expected
        return f"{call.__name__} raised {type(exc).__name__} ({exc})"


def route_answer(view: Callable[..., object], job_id: str, origin: str | None) -> tuple[int, object] | str:
    """What the route of ``view`` answers for the job: the status and the ``code`` of the ``HTTPException`` the view
    raises, or what it returned or raised instead (any other exception reaches the client as a 500)."""
    try:
        value = view(job_id, origin=origin)
    except HTTPException as exc:
        code = exc.detail.get("code") if isinstance(exc.detail, dict) else exc.detail
        return exc.status_code, code
    except Exception as exc:  # noqa: BLE001 — named by the caller's assertion: the API would answer it with a 500
        return f"raised {type(exc).__name__} ({exc})"
    return f"returned {value!r}"


def backup_made(start: Callable[..., object], data_dir: Path) -> BackupJob | str:
    """The end state of the backup ``start`` makes (``start_backup``'s run followed to its end), or a sentence naming
    what the start raised instead: the API's 500 (``start_job``), the CLI's traceback or exit 1."""
    try:
        started = start(data_dir=data_dir)
    except Exception as exc:  # noqa: BLE001 — named by the caller's assertion
        return f"{start.__name__} raised {type(exc).__name__} ({exc})"
    return started[0] if isinstance(started, tuple) else wait_until_finished(started.job_id, data_dir)


def a_disk_that_fails_once(monkeypatch, state: Path, error: OSError) -> list[str]:
    """The first read of ``state`` fails with ``error``, as a disk fails for an instant (through ``Path.read_text`` or
    ``Path.read_bytes``: how a state is read); every other file, and ``state`` after that, reads as it is. How the
    failed read was made, kept: an empty list is a read that never came this way."""
    failed: list[str] = []
    for name in ("read_text", "read_bytes"):
        real = getattr(Path, name)

        def fail_once(self: Path, *args, _real=real, _name=name, **kwargs):
            if self == state and not failed:
                failed.append(_name)
                raise error
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(Path, name, fail_once)
    return failed


@pytest.mark.parametrize("shape", shapes(*DECIDED))
def test_a_job_whose_state_cannot_be_read_is_not_found_and_left_as_it_is(data_dir, plant_unreadable, shape):
    """(B-50) ``get_job``, ``job_archive`` and ``delete_job`` of a job whose state cannot be read answer
    ``BackupJobNotFoundError`` (the API's 404 ``backup_job_not_found``) whatever the state holds, never another
    exception (the API's 500); and its folder is left as it is, by ``delete_job`` too: it expires by its date."""
    print_section(f"B-50: a job whose state cannot be read ({shape})")
    now = datetime.now(UTC)
    job_id = plant_unreadable(shape, now=now, dated=now)
    folder = job_dir(data_dir, job_id)
    before = everything_below(folder)
    answers = {call.__name__: job_answer(call, job_id, data_dir) for call in (get_job, job_archive, delete_job)}
    assert answers == dict.fromkeys(answers, "not found"), f"a job whose state is {shape} must be not found (the API's 404), never a crash (the API's 500): {answers}"
    assert folder.is_dir() and everything_below(folder) == before, f"its folder must be left as it is, by delete_job too: {everything_below(folder) if folder.is_dir() else 'removed'}, before {before}"
    print_success(f"{shape}: not found three times, its folder left as it is")


@pytest.mark.parametrize("shape", shapes(*DECIDED))
def test_reading_a_state_that_cannot_be_read_logs_one_warning_with_the_job_id_and_the_error_class(data_dir, plant_unreadable, shape):
    """(B-50) The read (``get_job``) of a job whose state cannot be read logs one warning,
    ``"A backup job's state cannot be read"``, with the job's id (``job_id``) and the class of the error its read met
    (``error``), never the file's content: no traceback (the error's message may quote the file), and the canary a
    readable state holds reaches no logged event."""
    now = datetime.now(UTC)
    job_id = plant_unreadable(shape, now=now, dated=now)
    if shape in HOLDS_THE_CANARY:
        assert CANARY.encode("ascii") in (job_dir(data_dir, job_id) / STATE_FILE).read_bytes(), "precondition: the state holds the canary"
    with jobs_logs() as events:
        read = job_answer(get_job, job_id, data_dir)
    warned = unreadable_warnings(events)
    assert [(event.get("log_level"), event.get("job_id"), event.get("error")) for event in warned] == [("warning", job_id, DECIDED[shape])], f"the read of a job whose state is {shape} must log one warning {UNREADABLE_WARNING!r} with its id and {DECIDED[shape]}: {warned} (get_job {read})"
    assert not [event for event in warned if {"exc_info", "exception"} & set(event)], f"the warning names the error's class, never its message nor a traceback, which may quote the file: {warned}"
    assert CANARY not in repr(events), f"the content of the state must reach no logged event: {[event for event in events if CANARY in repr(event)]}"
    print_success(f"{shape}: one warning, error {DECIDED[shape]}, no content")


@pytest.mark.parametrize("missing", ["no-state", "no-folder"])
def test_a_job_whose_state_is_missing_is_not_found_and_not_logged_as_unreadable(data_dir, missing):
    """(B-50) Guard, green before the cure and after it: a job folder without a state, or no folder at all, is not
    found, as it always was, and is not logged as a state that cannot be read: there was nothing to read."""
    job_id = unreadable_job(data_dir, None, datetime.now(UTC)) if missing == "no-state" else uuid.uuid4().hex
    with jobs_logs() as events:
        answers = {call.__name__: job_answer(call, job_id, data_dir) for call in (get_job, job_archive, delete_job)}
    assert answers == dict.fromkeys(answers, "not found"), f"a job with {missing} must be not found: {answers}"
    assert unreadable_warnings(events) == [], f"a missing state is no state that cannot be read: {unreadable_warnings(events)}"
    print_success(f"{missing}: not found, no warning")


def test_a_transient_error_reading_a_state_reaches_the_caller_as_it_is_never_as_not_found(data_dir, monkeypatch):
    """(B-50) Guard, green before the cure and after it: a read of a job's state that fails for an instant (``EIO``) is
    no state that cannot be read. ``get_job`` lets that very ``OSError`` through (the API's 500, which the Backup tab
    retries: «not found» would make the tab forget a job that runs), logs no warning of an unreadable state, and the
    next read finds the job as it was written."""
    job, folder = finished_job(data_dir, finished=datetime.now(UTC) - timedelta(minutes=1))
    eio = OSError(errno.EIO, os.strerror(errno.EIO))
    failed = a_disk_that_fails_once(monkeypatch, folder / STATE_FILE, eio)
    with jobs_logs() as events:
        try:
            first = get_job(job.job_id, data_dir=data_dir)
        except Exception as exc:  # noqa: BLE001 — asserted below: that very OSError, nothing else
            first = exc
    assert failed, "precondition: get_job read the state through Path.read_text or Path.read_bytes, where the disk failed"
    assert first is eio, f"an EIO reading the state must reach the caller as that very OSError, never as not found: {first!r}"
    assert unreadable_warnings(events) == [], f"a transient error is no state that cannot be read: {unreadable_warnings(events)}"
    assert get_job(job.job_id, data_dir=data_dir) == job, "the next read (the tab retries) finds the job as it was written"
    print_success("EIO: the OSError itself, no warning, the job read again")


@pytest.mark.parametrize("origin", [pytest.param(None, id="backup-tab"), pytest.param("panel", id="hosting-panel")])
@pytest.mark.parametrize("shape", shapes("json-list", "a-folder", "empty-object"))
def test_the_routes_of_a_job_whose_state_cannot_be_read_answer_404_backup_job_not_found(data_dir, monkeypatch, plant_unreadable, shape, origin):
    """(B-50) The views of a job's routes (``job_views``: its state, its file, its deletion), as the Backup tab
    (``origin`` None) and the hosting panel (``origin`` panel) call them, each answer 404 ``backup_job_not_found`` for a
    job whose state cannot be read, never a 500; the deletion removes nothing. Called as functions, no server: the jobs'
    data directory (``jobs.get_data_dir``) is this test's."""
    assert job_views.jobs is jobs, "precondition: the views call the very module whose data directory is replaced here"
    monkeypatch.setattr(jobs, "get_data_dir", lambda: data_dir)
    now = datetime.now(UTC)
    job_id = plant_unreadable(shape, now=now, dated=now)
    folder = job_dir(data_dir, job_id)
    before = everything_below(folder)
    answers = {view.__name__: route_answer(view, job_id, origin) for view in (job_views.read_job, job_views.job_file, job_views.remove_job)}
    assert answers == dict.fromkeys(answers, (404, "backup_job_not_found")), f"each route of a job whose state is {shape} must answer 404 backup_job_not_found, never a 500: {answers}"
    assert folder.is_dir() and everything_below(folder) == before, "the deletion must remove nothing of it"
    print_success(f"{shape}, {origin or 'ui'}: 404 backup_job_not_found three times")


@pytest.mark.parametrize("start", [start_backup, run_backup], ids=["start_backup", "run_backup"])
@pytest.mark.parametrize("shape", shapes("json-list", "a-folder", "mode-000", WITHOUT_TIME_ZONE))
def test_a_backup_starts_past_a_job_whose_state_cannot_be_read_and_its_folder_expires_by_its_date(data_dir, plant_unreadable, shape, start):
    """(B-50) Every start removes the expired jobs first (``_prepare`` → ``remove_expired_jobs``): two job folders whose
    state cannot be read, one dated 5 minutes ago and one 2 hours ago, stop it no more. The backup is made, done; the
    younger folder is kept, the older removed, by its date: a state that cannot be read has no end to go by."""
    now = datetime.now(UTC)
    young = plant_unreadable(shape, now=now, dated=now - timedelta(minutes=5))
    old = plant_unreadable(shape, now=now, dated=now - 2 * JOB_RETENTION)
    made = backup_made(start, data_dir)
    assert isinstance(made, BackupJob) and made.status == "done", f"{start.__name__} must make a backup past a job whose state is {shape}: {made}"
    assert job_folders(data_dir) == sorted([young, made.job_id]), f"the start keeps the unreadable folder dated 5 min ago ({young}) and removes the one dated 2 h ago ({old}): {job_folders(data_dir)}"
    print_success(f"{shape}, {start.__name__}: done; the unreadable folder kept until it is an hour old")


@pytest.mark.parametrize("shape", shapes(*BLOCKING, WITHOUT_TIME_ZONE))
def test_the_removal_of_expired_jobs_goes_on_past_a_state_it_cannot_read(data_dir, plant_unreadable, shape):
    """(B-50) ``remove_expired_jobs`` raises nothing for folders whose state cannot be read, and does its work on the
    others: the job that finished 2 hours ago is removed, the one that finished 5 minutes ago kept; the unreadable
    folders go by their date, the one dated 2 hours ago removed, the one dated 5 minutes ago kept."""
    hour = JOB_RETENTION
    expired = write_job(data_dir, status="done", created=NOW - 3 * hour, finished=NOW - 2 * hour).job_id
    kept = write_job(data_dir, status="done", created=NOW - timedelta(minutes=10), finished=NOW - timedelta(minutes=5)).job_id
    young = plant_unreadable(shape, now=NOW, dated=NOW - timedelta(minutes=5))
    old = plant_unreadable(shape, now=NOW, dated=NOW - 2 * hour)
    removed = returned_or_raised(remove_expired_jobs, data_dir, now=NOW)
    assert removed == 2, f"remove_expired_jobs must go past the folders whose state is {shape} and remove two (the job finished 2 h ago, the unreadable folder dated 2 h ago): {removed}"
    assert job_folders(data_dir) == sorted([kept, young]), f"left: the job finished 5 min ago ({kept}) and the unreadable folder dated 5 min ago ({young}); gone: {expired}, {old}: {job_folders(data_dir)}"
    print_success(f"{shape}: 2 removed, 2 kept")


@pytest.mark.parametrize("shape", shapes(*BLOCKING))
def test_the_end_of_dead_runs_goes_on_past_a_state_it_cannot_read(data_dir, plant_unreadable, shape):
    """(B-50) ``end_interrupted_jobs`` (the sweep at the application's start) raises nothing for a folder whose state
    cannot be read, and still ends the dead run beside it: failed, ``backup_interrupted``, written down. The unreadable
    folder is left as it is, to ``remove_expired_jobs``."""
    now = datetime.now(UTC)
    dead = write_job(data_dir, status="running", created=now - timedelta(minutes=5))
    job_id = plant_unreadable(shape, now=now, dated=now)
    folder = job_dir(data_dir, job_id)
    before = everything_below(folder)
    ended = returned_or_raised(end_interrupted_jobs, data_dir)
    stored = BackupJob.from_json((job_dir(data_dir, dead.job_id) / STATE_FILE).read_text(encoding="utf-8"))
    assert ended == 1, f"end_interrupted_jobs must go past the folder whose state is {shape} and end the one dead run: {ended}"
    assert (stored.status, stored.error_code) == ("failed", "backup_interrupted"), f"the dead run is ended, and that is written down: {stored}"
    assert folder.is_dir() and everything_below(folder) == before, "the folder whose state cannot be read is left as it is"
    print_success(f"{shape}: the dead run ended, the unreadable folder left")


@pytest.mark.parametrize("shape", shapes("json-list", "a-folder", "mode-000"))
def test_a_lock_that_holds_the_id_of_a_job_whose_state_cannot_be_read_names_no_job(data_dir, plant_unreadable, shape):
    """(B-50, after B-8) The lock is held and a job's state says running, but the lock holds the id of a job whose state
    cannot be read: JSON that is no object, a folder, a file the server may not read. Both starts are refused with
    ``BackupBusyError`` (the API's 409 ``backup_busy``) naming no job: neither their removal of the expired jobs nor the
    read of the job the lock names may turn the refusal into a crash (the API's 500)."""
    running = running_elsewhere(data_dir)
    now = datetime.now(UTC)
    stale_id = plant_unreadable(shape, now=now, dated=now)
    with lock_held(data_dir):
        lock_path(data_dir).write_bytes(stale_id.encode("ascii"))
        named = refusals(data_dir)
    assert named == dict.fromkeys(named, None), f"a lock holding the id of a job whose state is {shape} must name no job, though the state of {running.job_id} says running: {named}"
    print_success(f"{shape}: refused, no job named")
