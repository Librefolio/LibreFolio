"""
Instance backup, what a run killed at the wrong moment leaves behind, removed at startup (workstream B, lot B4b: the
security review R13-SEC4, note B-23; the coordinator's decision N66). Selector: ``services backup-leftovers``.

A hard kill (out of memory, a power cut, ``kill -9``) skips every ``finally``: the check of a secure backup leaves its
decrypted archive in ``.restore/stage/<id>/archive.zip``, an ``inspect`` its ``backups/.decrypt-<random>/`` folder, a
backup its database copy, its clear zip and a partial envelope in ``backups/.jobs/<id>/`` — every user's data in clear,
kept until someone happens to run the same command again. The startup step ``backup-leftovers``, right after
``restore-commit``, removes them, and never raises.

Under test: ``backend/app/services/platform/instance_backup/leftovers.py`` (new: ``DECRYPT_FOLDER_PREFIX``,
``DECRYPT_FOLDER_LIFETIME``, ``remove_stale_decrypt_folders``, ``sweep_backup_leftovers``),
``restore_jobs.remove_stray_decrypted_archives`` (new), ``restore_jobs.prune`` (its answer), ``jobs.end_interrupted_jobs``
(new), ``jobs.remove_expired_jobs`` (no link followed), ``jobs.get_job`` (its interrupted branch) and the step of
``app_lifespan.py``. The frozen contract: ``b4b-test-brief.md`` §1, with its revision of 03:58.

(a) The restore's folder. A check recorded ``running`` while the lock of the checks is free was left by a stopped
    server: ``prune`` ends it ``failed``/``restore_interrupted``, its stage and its upload removed, as before, and now
    answers how many checks it ended so (1, then 0 the next time; 0 without ``.restore/``, behind a link, while a check
    runs, or when it only removes an ended check older than 24 hours); the sweep, which reaches it, says so in its INFO
    line (``checks_interrupted`` 1, every other count 0). With the lock free, the ``archive.zip`` and the
    ``archive.zip.part`` that are regular files in a stage — a plain folder named by a job id: an unrecorded one (a
    check of the command line, or a ``restore`` killed while decrypting), the protected stage of a pending restore —
    are removed, and nothing else of the stage: its ``data/`` and its report stay (``prune``'s 24 hours still decide
    them). ``remove_stray_decrypted_archives`` answers how many, both names counted. Left alone: an ``archive.zip`` or
    an ``archive.zip.part`` that is a link (and the file it points to) or a folder, an ``archive.zip`` in a folder not
    named by a job id, a stage that is a link; anything, while ``.restore`` or ``.restore/stage`` is a link (its target
    as it was). While the lock is held (a check runs), nothing in ``.restore/`` changes: names, bytes, modes,
    modification times.
(b) The decrypt folders of ``inspect``, the cases of the command line's own sweep (``test_backup_cli_secure.py`` (j),
    imported, so that the two stay the same cases): ``DECRYPT_FOLDER_PREFIX`` ``.decrypt-``, ``DECRYPT_FOLDER_LIFETIME``
    one hour. Two stale real folders, two hours old (one with ``archive.zip``, one with ``archive.zip.part``), removed;
    two younger ones (just made, 50 minutes old) kept; a link ``.decrypt-link`` to a folder two hours old kept, with
    its folder; a file ``.decrypt-file`` two hours old kept; nothing else in ``backups/`` changes (a job, the earlier
    backups). Through ``remove_stale_decrypt_folders`` (it answers 2) and through the sweep. The age is read against
    the ``now`` given. ``backups/`` missing, a link or a file: 0, nothing touched.
(c) The backup jobs. A job recorded ``running`` while the run lock is free was left by a stopped server: ended as
    ``get_job`` ends it (``failed``, ``backup_interrupted``, ``phase`` None, ``finished_at`` now, the rest of its state
    as it was), its work files removed (the database copy, the clear zip and its partial, the partial envelope),
    ``state.json`` kept. ``end_interrupted_jobs`` answers how many; under a held run lock (a ``backup create`` running)
    it touches nothing; it ends only the plain folders named by a job id whose state says running: a finished job, an
    unreadable state, a link, a folder of another name stay as they are, and nothing at all is ended while ``backups/``
    or ``.jobs`` is a link (revision 03:58: both levels), directly or through the sweep. ``get_job`` on an interrupted
    job removes its work files too. The sweep also removes the jobs that ended
    more than an hour ago, and keeps one that ended ten minutes ago; ``remove_expired_jobs`` follows no link either:
    ``backups/`` or ``backups/.jobs`` a link to a folder holding a job that ended two hours ago, it removes nothing (0),
    directly or through the sweep, and the link's target stays as it was.
(d) Never raises. Each of the three parts — ``restore``, ``decrypt_folders``, ``jobs`` — made to raise in turn (an
    error of the test's own, then a ``PermissionError`` naming a path): the sweep returns ``None``, the two other parts
    do their work, and one error is logged, «A cleanup of backup leftovers failed», with the ``part`` and the
    exception's type name: neither its message, nor a path, nor a traceback (which would carry both).
(e) Quiet. A data directory with nothing left behind — a check that ended with its copy, a backup that finished with
    its archive, an earlier backup, the lock files, free — and one without ``.restore/`` and ``backups/``: nothing
    raised, nothing logged at INFO or above, nothing changed or created.
(f) What was removed or ended is said once: one INFO «Backup leftovers removed at startup» with, in this order,
    ``checks_interrupted``, ``decrypted_archives``, ``decrypt_folders``, ``jobs_interrupted`` and ``jobs_expired`` — 5,
    1, 2, 3 and 4 here: five distinct counts, so that two swapped fields show. Without an argument the sweep works on
    the configured data directory, as the step calls it. Two orders are read in the counts: the five interrupted checks
    hold a decrypted archive in their stage, which ``prune`` removes with the stage before
    ``remove_stray_decrypted_archives`` runs (1 decrypted archive, not 6); one of the interrupted jobs started three
    hours ago, and the jobs part ends it before it removes the expired ones, so it is kept an hour, as any job that
    ends now (3 and 4, not 2 and 5).
(g) The step ``backup-leftovers`` of ``STARTUP_STEPS``: its awaitable runs ``app_lifespan.sweep_backup_leftovers``
    once, without arguments, in a worker thread. Its place, right after ``restore-commit``, is pinned with the other
    steps in ``test_backup_apply.py`` (j).

How. Every data directory is a folder of ``tmp_path`` built file by file: the sweep never opens a database nor reads
an archive, and none is made. A check's state is written as ``restore_jobs`` writes it (a ``RestoreCheck`` as JSON in
``.restore/checks/<id>.json``) and read back by ``read_check`` while the lock is held, the precondition that the product
reads it as running; a job's state with ``write_job`` of ``test_backup_jobs.py``; a pending restore as ``apply`` keeps
it (a ``RestoreState`` in ``restore.json``), ``protected_stage`` checked. The locks are held as another holder holds
them, through a ``_RunLock`` of the test's own (``hold_the_lock`` of the staging tests, ``lock_held`` of the jobs
tests): an ``flock`` on another open file description, which the product's probe is refused. Ages are modification
times set with ``os.utime`` (``aged`` of the command line's tests), a link's own, never its target's. A folder is
compared whole with ``entries`` of the same tests: every path, never through a link, with its kind (a link's target, a
file's SHA-256), its mode and its modification time. A part made to raise is its functions replaced, in their module and
wherever a module of the package bound them, each reaching a barrier. Logs are read with ``capture_logs`` behind a
barrier (``logs`` of ``test_backup_apply.py``: a warning through a logger of the module's name must reach the capture).

Pure: every path under ``tmp_path``. This process's production data directory is a folder of the test that must stay
absent but where a test configures its own (``configured_data_dir`` of the staging tests, imported, autouse): the lane's
data directory is never reached. No database, no server, no network, no sleep. Modes, links and ``flock`` are
POSIX-only.

Written RED, before B4b: ``instance_backup.leftovers`` does not exist, nor do
``restore_jobs.remove_stray_decrypted_archives`` and ``jobs.end_interrupted_jobs``. Each is looked up by the test that
needs it (``leftovers_module``, ``new_function``), never at collection: the file collects without them, and each test
fails on its own with a "[new] …" message. The cases on what exists already fail on what it does today: ``get_job``
leaves the work files, ``prune`` answers ``None``, ``remove_expired_jobs`` removes a job through a link.
"""

from __future__ import annotations

import errno
import importlib
import inspect
import json
import os
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from backend.app.services.platform.instance_backup import jobs, restore_jobs
from backend.app.services.platform.instance_backup.apply import RestoreState, protected_stage
from backend.app.services.platform.instance_backup.jobs import BackupJob, get_job
from backend.app.services.platform.instance_backup.paths import (
    STAGE_DATA_FOLDER,
    STAGE_DECRYPTED_ARCHIVE,
    STAGE_REPORT_FILE,
    STATE_FILE,
    backups_dir,
    check_state_path,
    checks_dir,
    ensure_private_dir,
    job_dir,
    jobs_dir,
    restore_dir,
    restore_state_path,
    stage_dir,
    stages_dir,
    upload_path,
    uploads_dir,
)
from backend.app.services.platform.instance_backup.restore_jobs import RestoreCheck
from backend.app.services.platform.instance_backup.staging import new_stage_id
from backend.test_scripts.test_services import test_backup_apply as apply_cases
from backend.test_scripts.test_services import test_backup_jobs as jobs_cases
from backend.test_scripts.test_services import test_backup_staging as cases
from backend.test_scripts.test_utilities import test_backup_cli_secure as cli_secure
from backend.test_scripts.test_utils import print_section, print_success

# Autouse: the production data directory of this process is a folder of the test that must stay absent, unless a test
# configures its own (test_backup_staging.py): a sweep without a data directory never reaches the lane's.
configured_data_dir = cases.configured_data_dir

pytestmark = pytest.mark.skipif(os.name == "nt", reason="modes, links and flock are POSIX only")

PACKAGE = "backend.app.services.platform.instance_backup"
LEFTOVERS = f"{PACKAGE}.leftovers"
#: What the sweep logs (contract §1): once when it removed or ended something; once for each part that failed.
SUMMARY = "Backup leftovers removed at startup"
FAILURE = "A cleanup of backup leftovers failed"
#: The counts of the summary, in their order (revision 03:58: ``checks_interrupted`` first), and the three parts of the
#: sweep, in theirs.
COUNTS = ("checks_interrupted", "decrypted_archives", "decrypt_folders", "jobs_interrupted", "jobs_expired")
PARTS = ("restore", "decrypt_folders", "jobs")
#: The partial of a decrypted archive: what a ``restore`` killed while decrypting leaves in its stage (revision 03:58).
PARTIAL_ARCHIVE = f"{STAGE_DECRYPTED_ARCHIVE}.part"
#: The levels an operator reads: a start with nothing left behind says none of them.
SEEN_LEVELS = {"info", "warning", "error", "critical"}
#: What every leftover holds: every user's data, in clear (bytes that stand for it).
CLEAR = b"PK\x03\x04 every user's data, in clear: what a killed run left behind"
#: What a backup run keeps beside its state while it works: the database copy, the zip and its partial, the partial
#: envelope of a secure backup. Everything but ``state.json``: what a run that died leaves.
WORK_FILES = {
    "app.db": b"SQLite format 3\x00 the database copy of a run that died",
    "librefolio-backup-20261017-011500.zip": CLEAR,
    "librefolio-backup-20261017-011500.zip.part": CLEAR[:24],
    "librefolio-backup-20261017-011500.lfbk.part": b"LFBK half an envelope",
}
#: The archive a finished job keeps for an hour, and the earlier backups ``backups/`` holds.
FINISHED_ARCHIVE = "librefolio-backup-20261017-010000.zip"
EARLIER_BACKUPS = ("librefolio-backup-20261014-090000.zip", "librefolio-backup-20261014-090000.lfbk")
#: A stage's copy as a check leaves it once it unpacked the archive, beside the decrypted archive it has not removed yet.
STAGE_FILES = {f"{STAGE_DATA_FOLDER}/sqlite/app.db": b"SQLite format 3\x00 a copy being checked", f"{STAGE_DATA_FOLDER}/custom-uploads/logo.png": bytes(range(256))}
#: The live data of the data directory: no sweep ever touches it.
LIVE_FILES = {"sqlite/app.db": b"SQLite format 3\x00 the live database", "custom-uploads/logo.png": b"the live instance's logo"}
#: A job that ended this long ago is removed by the next start; one that ended this recently is kept.
LONG_AGO = timedelta(hours=2)
RECENTLY = timedelta(minutes=10)
#: When the interrupted jobs of (d) and (f) started: one three hours ago, longer than a job is kept.
INTERRUPTED_STARTS = (timedelta(minutes=5), timedelta(minutes=30), timedelta(hours=3))
#: How many jobs ended long ago (d) and (f) leave: a fourth count, distinct from the others.
EXPIRED_JOBS = 4
#: How many checks a stopped server left running in (d) and (f): a fifth count, distinct from the others.
INTERRUPTED_CHECKS = 5
#: The message of the failures the tests inject: never in the log.
MESSAGE_MARK = "b4b-injected-message-5e1d"
#: How a case is cleaned: by the function of its part, which answers how many it removed or ended, or by the sweep.
THROUGH = [pytest.param("function", id="by-its-function"), pytest.param("sweep", id="by-the-startup-sweep")]


# =============================================================================
# The product, looked up when a test needs it
# =============================================================================


def leftovers_module() -> ModuleType:
    """``instance_backup.leftovers`` (§1), imported by the test that needs it: its absence is that test's red, not a
    collection error of the whole file."""
    try:
        return importlib.import_module(LEFTOVERS)
    except ModuleNotFoundError as exc:
        if exc.name != LEFTOVERS:
            raise
        pytest.fail(f"[new] {LEFTOVERS} does not exist yet: lot B4b brings it (§1)")


def new_function(module: ModuleType, name: str) -> Callable[..., Any]:
    """``module.<name>``, a function lot B4b adds, read when the test calls it."""
    function = getattr(module, name, None)
    assert callable(function), f"[new] {module.__name__}.{name}() does not exist yet: lot B4b adds it (§1)"
    return function


def sweep(root: Path | None = None) -> None:
    """``sweep_backup_leftovers`` on ``root`` (without one: the configured data directory, as the step calls it); it
    answers ``None``."""
    module = leftovers_module()
    outcome = module.sweep_backup_leftovers() if root is None else module.sweep_backup_leftovers(root)
    assert outcome is None, f"sweep_backup_leftovers answers None, not {outcome!r}"


def remove_stray_archives(root: Path) -> int:
    return new_function(restore_jobs, "remove_stray_decrypted_archives")(root)


def end_interrupted_jobs(root: Path) -> int:
    return new_function(jobs, "end_interrupted_jobs")(root)


def prune(root: Path) -> object:
    """``restore_jobs.prune(root)``: what it answers (revision 03:58, how many checks it ended as interrupted)."""
    return restore_jobs.prune(root)


def summary_counts(events: list[dict[str, Any]]) -> dict[str, Any]:
    """The counts of the one INFO line that says what the sweep removed and ended, checked to come once, at INFO, its
    counts in the contract's order (``checks_interrupted`` first)."""
    summaries = [event for event in events if event.get("event") == SUMMARY]
    assert [event.get("log_level") for event in summaries] == ["info"], f"one INFO line says what the sweep removed and ended: {apply_cases.logged(events)}"
    order = [key for key in summaries[0] if key in COUNTS]
    assert order == list(COUNTS), f"its counts, in this order: {list(COUNTS)}, not {order}: {summaries[0]}"
    return {name: summaries[0][name] for name in COUNTS}


# =============================================================================
# Data directories, as killed runs leave them
# =============================================================================


def data_root(tmp_path: Path) -> Path:
    """The data directory of the test, a plain folder of ``tmp_path`` (0700)."""
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    return root


def moved_behind_a_link(folder: Path, elsewhere: Path) -> Path:
    """``folder`` moved to ``elsewhere``, outside the data directory, a link to it left in its place: what it held is now
    the link's target, which is returned. (``test_backup_restore.py`` has the same for the restore's folders only.)"""
    elsewhere.parent.mkdir(parents=True, exist_ok=True)
    folder.rename(elsewhere)
    folder.symlink_to(elsewhere, target_is_directory=True)
    return elsewhere


def without_names(snapshot: dict[str, tuple[Any, ...]], names: set[str]) -> dict[str, tuple[Any, ...]]:
    """``snapshot`` (``entries``) without the entries ``names``, exactly those."""
    return {name: value for name, value in snapshot.items() if name not in names}


# -----------------------------------------------------------------------------
# The restore's folder
# -----------------------------------------------------------------------------


def restore_folders(root: Path) -> None:
    """``.restore`` with its three folders, and the lock of the checks as a check that ended leaves it: there, free."""
    for folder in (stages_dir(root), checks_dir(root), uploads_dir(root)):
        ensure_private_dir(folder, root)
    cases.hold_the_lock(root).release()


def stage_holding(root: Path, stage_id: str | None = None, *, archive: str | None = STAGE_DECRYPTED_ARCHIVE, data: bool = True, report: bool = False) -> Path:
    """A stage, ``.restore/stage/<id>/``, as a killed check leaves it: its ``data/`` once it unpacked the archive, its
    report when it got that far, and beside them ``archive`` — the decrypted archive, or its partial for a check killed
    while decrypting — a regular file (0600), or nothing (``None``). The folder."""
    folder = ensure_private_dir(stage_dir(root, stage_id or new_stage_id()), root)
    if data:
        cases.write_files(folder, STAGE_FILES)
    if report:
        (folder / STAGE_REPORT_FILE).write_bytes(b"{}\n")
    if archive is not None:
        (folder / archive).write_bytes(CLEAR)
        (folder / archive).chmod(0o600)
    return folder


def recorded_check(root: Path, stage_id: str, upload_id: str, *, status: str = "running", ended_ago: timedelta = RECENTLY) -> RestoreCheck:
    """A check's state as ``restore_jobs`` writes it, ``.restore/checks/<stage id>.json``: running, or ended ``ended_ago``."""
    now = datetime.now(UTC)
    running = status == "running"
    finished = None if running else now - ended_ago
    check = RestoreCheck(stage_id=stage_id, upload_id=upload_id, status=status, phase="unpacking" if running else None, done_bytes=512, total_bytes=2048, created_at=(finished or now) - timedelta(minutes=1), finished_at=finished)
    record = {key: value.isoformat() if isinstance(value, datetime) else value for key, value in asdict(check).items()}
    path = check_state_path(root, stage_id)
    path.write_text(json.dumps(record), encoding="utf-8")
    path.chmod(0o600)
    return check


def an_upload(root: Path, upload_id: str) -> Path:
    """An archive received for a check, ``.restore/upload/<id>`` (0600)."""
    path = upload_path(root, upload_id)
    path.write_bytes(b"LFBK the secure backup a check was reading")
    path.chmod(0o600)
    return path


def read_as_running(root: Path, *stage_ids: str) -> None:
    """The precondition of checks recorded running: ``read_check`` reads each so while the lock is held, as it does while
    a check runs (then ``read_check`` changes nothing). The lock is free again on return."""
    holder = cases.hold_the_lock(root)
    try:
        read = [restore_jobs.read_check(stage_id, data_dir=root) for stage_id in stage_ids]
    finally:
        holder.release()
    assert all(check.status == "running" for check in read), f"precondition: the checks are recorded running, and read so while their lock is held: {read}"


@dataclass(frozen=True)
class InterruptedCheck:
    """A check a stopped server left running: its stage (its copy and the decrypted archive in it) and its upload."""

    stage_id: str
    stage: Path
    upload: Path


def interrupted_checks(root: Path, count: int) -> tuple[InterruptedCheck, ...]:
    """``count`` checks recorded running, each with its stage and its upload, in ``.restore`` with the lock free: what a
    server stopped during the checks leaves. Read as running while the lock is held (the precondition)."""
    made = []
    for _ in range(count):
        stage_id, upload_id = new_stage_id(), new_stage_id()
        stage = stage_holding(root, stage_id)
        upload = an_upload(root, upload_id)
        recorded_check(root, stage_id, upload_id)
        made.append(InterruptedCheck(stage_id=stage_id, stage=stage, upload=upload))
    read_as_running(root, *(check.stage_id for check in made))
    return tuple(made)


def check_state(root: Path, stage_id: str) -> dict[str, Any] | None:
    """A check's state file as written, read without ``read_check`` (which would end a running check itself); ``None``
    when there is none."""
    path = check_state_path(root, stage_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def ended_interrupted(root: Path, check: InterruptedCheck) -> bool:
    """Whether ``check`` was ended as a stopped server's: ``failed``/``restore_interrupted`` in its state file, with the
    time it ended, its stage and its upload gone."""
    state = check_state(root, check.stage_id) or {}
    recorded = (state.get("status"), state.get("error_code"), state.get("phase"), state.get("finished_at") is not None)
    return recorded == ("failed", "restore_interrupted", None, True) and not os.path.lexists(check.stage) and not os.path.lexists(check.upload)


def still_running(root: Path, check: InterruptedCheck) -> bool:
    """Whether ``check`` is still recorded running, its stage and its upload as they were left."""
    state = check_state(root, check.stage_id) or {}
    return state.get("status") == "running" and (check.stage / STAGE_DECRYPTED_ARCHIVE).is_file() and check.upload.is_file()


def pending_restore(root: Path, stage_id: str) -> None:
    """A restore confirmed for the next start (lot B3), waiting on the copy of ``stage_id``: ``restore.json`` as
    ``apply`` keeps it. The precondition that the stage is the protected one is checked."""
    now = datetime.now(UTC)
    state = RestoreState(
        status="pending",
        stage_id=stage_id,
        data_dir=str(root.resolve()),
        confirmed_at=now,
        confirmed_by="cli",
        backup_created_at=now - timedelta(days=1),
        backup_app_version="v0.0.0-b4b-leftovers-test",
        action="same",
    )
    path = restore_state_path(root)
    path.write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    assert protected_stage(root) == stage_id, f"precondition: the stage of the pending restore is the protected one: {protected_stage(root)}"


# -----------------------------------------------------------------------------
# The decrypt folders of inspect: the command line's (j)
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DecryptFolders:
    """``backups/`` as the command line's (j) leaves it, the folder ``.decrypt-link`` points to (outside the data
    directory) and the folder of the job that finished ten minutes ago."""

    backups: Path
    target: Path
    job: Path


def decrypt_leftovers(root: Path, tmp_path: Path) -> DecryptFolders:
    """``backups/`` with every case of the command line's (j): two stale folders two hours old (``STALE``, a clear file
    in each), two younger ones (``YOUNG``), a link ``.decrypt-link`` to a folder outside and a file ``.decrypt-file``,
    two hours old; a job that finished ten minutes ago, its files and folders two hours old, beside the run lock its
    backup left, free; the earlier backups, two hours old."""
    backups = ensure_private_dir(backups_dir(root), root)
    for name, entry in cli_secure.STALE.items():
        cli_secure.folder_holding(backups / name, entry, CLEAR, cli_secure.OLD)
    for name, age in cli_secure.YOUNG.items():
        cli_secure.folder_holding(backups / name, STAGE_DECRYPTED_ARCHIVE, CLEAR, age)
    target = cli_secure.folder_holding(tmp_path / "outside" / "linked", "kept.txt", cli_secure.KEPT, cli_secure.OLD)
    link = backups / ".decrypt-link"
    link.symlink_to(target, target_is_directory=True)
    cli_secure.aged(link, cli_secure.OLD)
    (backups / ".decrypt-file").write_bytes(cli_secure.KEPT)
    cli_secure.aged(backups / ".decrypt-file", cli_secure.OLD)
    _job, folder = finished_job(root, ended=RECENTLY)
    free_run_lock(root)
    for entry in (folder / FINISHED_ARCHIVE, folder / STATE_FILE, folder, jobs_dir(root)):
        cli_secure.aged(entry, cli_secure.OLD)
    for name in EARLIER_BACKUPS:
        (backups / name).write_bytes(CLEAR)
        cli_secure.aged(backups / name, cli_secure.OLD)
    ages = {name: round(time.time() - (backups / name).lstat().st_mtime) for name in [*cli_secure.STALE, *cli_secure.YOUNG]}
    assert all(ages[name] > cli_secure.SWEEP_AGE for name in cli_secure.STALE) and all(ages[name] < cli_secure.SWEEP_AGE for name in cli_secure.YOUNG), f"precondition: the stale folders older than an hour, the young ones younger (seconds): {ages}"
    assert link.is_symlink() and link.is_dir(), "precondition: .decrypt-link is a link to a folder"
    return DecryptFolders(backups=backups, target=target, job=folder)


def stale_left(backups: Path) -> list[str]:
    """The stale decrypt folders still in ``backups/``."""
    return sorted(name for name in cli_secure.STALE if os.path.lexists(backups / name))


# -----------------------------------------------------------------------------
# The backup jobs
# -----------------------------------------------------------------------------


def free_run_lock(root: Path) -> None:
    """``backups/.jobs/.lock`` as every backup leaves it: there, free (``lock_held`` of the jobs tests, taken and let
    go)."""
    with jobs_cases.lock_held(root):
        pass


def running_job(root: Path, *, started: timedelta = timedelta(minutes=5)) -> tuple[BackupJob, Path]:
    """A job recorded ``running`` (``write_job`` of the jobs tests), started ``started`` ago, its work files beside its
    state: what a run killed while it worked leaves. The job and its folder."""
    job = jobs_cases.write_job(root, status="running", created=datetime.now(UTC) - started)
    folder = job_dir(root, job.job_id)
    cases.write_files(folder, WORK_FILES)
    return job, folder


def finished_job(root: Path, *, ended: timedelta, status: str = "done") -> tuple[BackupJob, Path]:
    """A job that ended ``ended`` ago, done (with its archive) or failed. The job and its folder."""
    finished = datetime.now(UTC) - ended
    job = jobs_cases.write_job(root, status=status, created=finished - timedelta(minutes=3), finished=finished, error_code=None if status == "done" else "backup_failed")
    folder = job_dir(root, job.job_id)
    if status == "done":
        (folder / FINISHED_ARCHIVE).write_bytes(CLEAR)
    return job, folder


def read_job(folder: Path) -> BackupJob:
    """The state of a job, as its folder holds it."""
    return BackupJob.from_json((folder / STATE_FILE).read_text(encoding="utf-8"))


def status_of(folder: Path) -> str | None:
    """The status a job's folder records; ``None`` when the folder, or its state, is gone."""
    try:
        return read_job(folder).status
    except (FileNotFoundError, NotADirectoryError):
        return None


def assert_ended_interrupted(before: BackupJob, folder: Path, started: datetime, ended: datetime) -> None:
    """The job of ``folder``, recorded running as ``before``, ended as ``get_job`` ends a run that died, between
    ``started`` and ``ended``: the rest of its state as it was, ``state.json`` alone in its folder."""
    assert (folder / STATE_FILE).is_file(), f"the job's folder and its state are kept: {sorted(os.listdir(folder)) if folder.is_dir() else 'the folder is gone'}"
    after = read_job(folder)
    assert (after.status, after.error_code, after.phase) == ("failed", "backup_interrupted", None), f"a run that died ends failed, backup_interrupted, without a phase: {after}"
    assert after.finished_at is not None and started <= after.finished_at <= ended, f"finished_at is the time it was ended: {after.finished_at} not in [{started}, {ended}]"
    assert replace(after, finished_at=None) == replace(before, status="failed", phase=None, error_code="backup_interrupted"), f"the rest of its state as it was: {before} → {after}"
    assert os.listdir(folder) == [STATE_FILE], f"the work files a run leaves are removed (the database copy, the clear zip and its partial, the partial envelope), state.json kept: {sorted(os.listdir(folder))}"


# -----------------------------------------------------------------------------
# Everything at once: (d) and (f)
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Leftovers:
    """A data directory where every part of the sweep has work: five checks a stopped server left running (a decrypted
    archive in each stage) and a decrypted archive a killed check of the command line left; the decrypt folders of (b);
    three interrupted jobs, four jobs that ended long ago, one that ended recently."""

    root: Path
    checks: tuple[InterruptedCheck, ...]
    stray: Path
    backups: Path
    interrupted: tuple[tuple[BackupJob, Path], ...]
    expired: tuple[Path, ...]
    recent: Path


def everything_left(root: Path, tmp_path: Path) -> Leftovers:
    """``Leftovers`` in ``root``, beside the instance's live data, the lock files there and free."""
    cases.write_files(root, LIVE_FILES)
    restore_folders(root)
    checks = interrupted_checks(root, INTERRUPTED_CHECKS)
    stray = stage_holding(root) / STAGE_DECRYPTED_ARCHIVE
    folders = decrypt_leftovers(root, tmp_path)
    interrupted = tuple(running_job(root, started=started) for started in INTERRUPTED_STARTS)
    expired = tuple(finished_job(root, ended=LONG_AGO + timedelta(minutes=minutes))[1] for minutes in range(EXPIRED_JOBS))
    return Leftovers(root=root, checks=checks, stray=stray, backups=folders.backups, interrupted=interrupted, expired=expired, recent=folders.job)


def work_done(world: Leftovers) -> dict[str, bool]:
    """Whether each part did its whole work: every interrupted check ended with its stage and upload gone, the stray
    archive gone; the stale decrypt folders gone; every interrupted job ended with its state alone, every expired one
    gone, the recent one kept."""
    restore_done = all(ended_interrupted(world.root, check) for check in world.checks) and not os.path.lexists(world.stray)
    jobs_done = all(status_of(folder) == "failed" and os.listdir(folder) == [STATE_FILE] for _job, folder in world.interrupted) and not any(os.path.lexists(folder) for folder in world.expired)
    return {"restore": restore_done, "decrypt_folders": stale_left(world.backups) == [], "jobs": jobs_done and world.recent.is_dir()}


def work_untouched(world: Leftovers) -> dict[str, bool]:
    """Whether each part left its whole work undone."""
    restore_untouched = all(still_running(world.root, check) for check in world.checks) and world.stray.is_file()
    jobs_untouched = all(status_of(folder) == "running" and sorted(os.listdir(folder)) == sorted([STATE_FILE, *WORK_FILES]) for _job, folder in world.interrupted) and all(folder.is_dir() for folder in world.expired)
    return {"restore": restore_untouched, "decrypt_folders": stale_left(world.backups) == sorted(cli_secure.STALE), "jobs": jobs_untouched}


# -----------------------------------------------------------------------------
# A part that fails
# -----------------------------------------------------------------------------


class InjectedFailure(RuntimeError):
    """What a part of the sweep is made to raise: an error of the test's own."""


def an_error_of_its_own(root: Path) -> BaseException:
    return InjectedFailure(f"{MESSAGE_MARK}: {backups_dir(root)}")


def permission_denied(root: Path) -> BaseException:
    return PermissionError(errno.EACCES, f"{MESSAGE_MARK}: permission denied", str(backups_dir(root)))


#: What a part raises, and the type name its error log gives.
FAILURES = [
    pytest.param(an_error_of_its_own, "InjectedFailure", id="an-error-of-its-own"),
    pytest.param(permission_denied, "PermissionError", id="permission-denied-naming-a-path"),
]


def replace_everywhere(monkeypatch: pytest.MonkeyPatch, owner: ModuleType, name: str, replacement: Callable[..., Any]) -> None:
    """``owner.<name>`` replaced, and the same function wherever a module of the package bound it (``from … import``)."""
    original = getattr(owner, name, None)
    monkeypatch.setattr(owner, name, replacement, raising=False)
    if original is None:
        return
    for module_name, module in list(sys.modules.items()):
        if module_name.startswith(PACKAGE + ".") and module is not owner and getattr(module, name, None) is original:
            monkeypatch.setattr(module, name, replacement)


def fail_the_part(monkeypatch: pytest.MonkeyPatch, leftovers: ModuleType, part: str, error: BaseException) -> list[str]:
    """Every function of ``part`` raises ``error``, whichever the sweep reaches first; the names reached, in order."""
    functions = {
        "restore": ((restore_jobs, "prune"), (restore_jobs, "remove_stray_decrypted_archives")),
        "decrypt_folders": ((leftovers, "remove_stale_decrypt_folders"),),
        "jobs": ((jobs, "end_interrupted_jobs"), (jobs, "remove_expired_jobs")),
    }[part]
    reached: list[str] = []
    for owner, name in functions:

        def failing(*args: Any, _name: str = name, **kwargs: Any) -> Any:
            reached.append(_name)
            raise error

        replace_everywhere(monkeypatch, owner, name, failing)
    return reached


# =============================================================================
# (a) The restore's folder
# =============================================================================


@pytest.mark.parametrize("through", [pytest.param("prune", id="by-prune"), pytest.param("sweep", id="by-the-startup-sweep")])
def test_a_check_its_stopped_server_left_running_is_ended_at_startup_with_its_copy_and_its_upload(tmp_path, through):
    """(a) The lock of the checks free, a check recorded running was left by a stopped server: it is ended
    ``failed``/``restore_interrupted`` in its state file, its stage (the decrypted archive and the copy in it) and its
    upload removed — ``prune``'s work, as before. Revision 03:58: ``prune`` answers how many checks it ended so, 1, then
    0 the next time; the sweep, which reaches it, says so: a start that only ends that check logs its INFO line,
    ``checks_interrupted`` 1 and every other count 0."""
    print_section(f"(a) A check its stopped server left running, {through}")
    root = data_root(tmp_path)
    restore_folders(root)
    [check] = interrupted_checks(root, 1)
    if through == "prune":
        answers = (prune(root), prune(root))
        assert answers == (1, 0), f"prune answers how many checks it ended as interrupted: 1, then 0 the next time, not {answers}"
    else:
        with apply_cases.logs(LEFTOVERS) as events:
            sweep(root)
        counts = summary_counts(events)
        assert counts == {**dict.fromkeys(COUNTS, 0), "checks_interrupted": 1}, f"a start that only ends a check says so, and nothing else: {counts}"
    state = check_state(root, check.stage_id)
    assert ended_interrupted(root, check), f"the check is ended as interrupted, its stage and its upload removed: {state}, stage there {os.path.lexists(check.stage)}, upload there {os.path.lexists(check.upload)}"
    print_success(f"{through}: failed, restore_interrupted; stage and upload removed; 1 check ended")


def unchanged(folder: Path, what: str) -> Callable[[], None]:
    """What checks, later, that ``folder`` is as it is now (``entries``); ``what`` names it in the message."""
    before = cli_secure.entries(folder)

    def check() -> None:
        assert cli_secure.entries(folder) == before, f"{what} is left as it was: {cli_secure.differences(before, cli_secure.entries(folder))}"

    return check


def no_restore_folder(root: Path, tmp_path: Path) -> Callable[[], None]:
    """No ``.restore/``: no archive was ever checked. Nothing is created."""
    return unchanged(root, "the data directory")


def restore_folder_a_link(root: Path, tmp_path: Path) -> Callable[[], None]:
    """``.restore`` a link to a folder outside holding a check recorded running: nothing is ended through it."""
    restore_folders(root)
    interrupted_checks(root, 1)
    return unchanged(moved_behind_a_link(restore_dir(root), tmp_path / "elsewhere" / "restore"), "the link's target, a check recorded running in it")


def a_check_that_runs(root: Path, tmp_path: Path) -> Callable[[], None]:
    """A check recorded running while its lock is held: it runs, nobody ends it."""
    restore_folders(root)
    interrupted_checks(root, 1)
    return unchanged(restore_dir(root), ".restore/, the running check in it")


def an_ended_check_older_than_a_day(root: Path, tmp_path: Path) -> Callable[[], None]:
    """A check that ended 25 hours ago, with its copy: ``prune`` removes it, as before — removing an ended check is not
    ending one."""
    restore_folders(root)
    stage_id = new_stage_id()
    stage_holding(root, stage_id, archive=None, report=True)
    recorded_check(root, stage_id, new_stage_id(), status="done", ended_ago=timedelta(hours=25))

    def removed() -> None:
        assert check_state(root, stage_id) is None and not os.path.lexists(stage_dir(root, stage_id)), "barrier: prune removed the check that ended more than a day ago, with its copy, as before"

    return removed


#: The ways ``prune`` ends no check, and whether the lock of the checks is held (by this test) while it runs.
NOTHING_TO_END = [
    pytest.param(no_restore_folder, False, id="no-restore-folder"),
    pytest.param(restore_folder_a_link, False, id="restore-folder-a-link"),
    pytest.param(a_check_that_runs, True, id="a-check-runs-its-lock-held"),
    pytest.param(an_ended_check_older_than_a_day, False, id="an-ended-check-25-hours-old-removed"),
]


@pytest.mark.parametrize(("arrange", "lock_held"), NOTHING_TO_END)
def test_prune_answers_0_when_it_ends_no_check(tmp_path, arrange, lock_held):
    """(a) Revision 03:58: ``prune`` answers an ``int`` on every path — the sweep adds it to its counts — and 0 when it
    ends no check as interrupted: without ``.restore/``, ``.restore`` a link, while a check runs, and when it only
    removes a check that ended more than a day ago. What each case holds stays as ``prune`` always left it."""
    root = data_root(tmp_path)
    then = arrange(root, tmp_path)
    holder = cases.hold_the_lock(root) if lock_held else None
    try:
        answer = prune(root)
    finally:
        if holder is not None:
            holder.release()
    assert (type(answer), answer) == (int, 0), f"prune ended no check: it answers 0, not {answer!r}"
    then()
    print_success(f"{arrange.__name__}: 0")


@pytest.mark.parametrize("through", THROUGH)
def test_a_decrypted_archive_a_killed_check_left_is_removed_and_nothing_else_of_its_stage(tmp_path, through):
    """(a) The lock free, the ``archive.zip`` and the ``archive.zip.part`` of a stage named by a job id are what a hard
    kill left: removed when they are regular files — in an unrecorded stage (a check of the command line, young), in
    the protected stage of a pending restore, and (revision 03:58) the partial alone in the stage of a ``restore``
    killed while decrypting; the stages, their ``data/`` and their report stay. Left alone, with what they point to: an
    ``archive.zip`` and an ``archive.zip.part`` that are links to files outside, or folders; both names in a folder not
    named by a job id, and in a stage that is a link. Nothing else in ``.restore/`` changes;
    ``remove_stray_decrypted_archives`` answers 3, both names counted."""
    print_section("(a) The decrypted archives a killed check left")
    root = data_root(tmp_path)
    restore_folders(root)
    outside = tmp_path / "outside"
    linked_stage = {f"linked-stage/{STAGE_DECRYPTED_ARCHIVE}": CLEAR, f"linked-stage/{PARTIAL_ARCHIVE}": CLEAR, **{f"linked-stage/{name}": data for name, data in STAGE_FILES.items()}}
    cases.write_files(outside, {"elsewhere.zip": CLEAR, "elsewhere.zip.part": CLEAR, **linked_stage})
    unrecorded = stage_holding(root)
    protected = stage_holding(root, report=True)
    pending_restore(root, protected.name)
    decrypting = stage_holding(root, archive=PARTIAL_ARCHIVE, data=False)
    for name, target in ((STAGE_DECRYPTED_ARCHIVE, "elsewhere.zip"), (PARTIAL_ARCHIVE, "elsewhere.zip.part")):
        (stage_holding(root, archive=None) / name).symlink_to(outside / target)
        cases.write_files(stage_holding(root, archive=None) / name, {"inside.bin": CLEAR})
    cases.write_files(stages_dir(root) / "notes", {STAGE_DECRYPTED_ARCHIVE: CLEAR, PARTIAL_ARCHIVE: CLEAR})
    (stages_dir(root) / new_stage_id()).symlink_to(outside / "linked-stage", target_is_directory=True)
    before, beyond = cli_secure.entries(restore_dir(root)), cli_secure.entries(outside)
    if through == "function":
        removed = remove_stray_archives(root)
        assert removed == 3, f"remove_stray_decrypted_archives answers how many it removed, archive.zip and archive.zip.part alike: 3, not {removed}"
    else:
        sweep(root)
    after = cli_secure.entries(restore_dir(root))
    cleaned = {unrecorded: STAGE_DECRYPTED_ARCHIVE, protected: STAGE_DECRYPTED_ARCHIVE, decrypting: PARTIAL_ARCHIVE}
    gone = {f"{stages_dir(root).name}/{folder.name}/{name}" for folder, name in cleaned.items()}
    emptied = {f"{stages_dir(root).name}/{folder.name}" for folder in cleaned}
    assert sorted(gone & after.keys()) == [], f"the decrypted archives of the unrecorded and the protected stage, and the partial of the stage killed while decrypting, are removed: {sorted(gone & after.keys())} still there"
    assert all((restore_dir(root) / name).is_dir() for name in emptied), "the three stages stay"
    changed = cli_secure.differences(without_names(before, gone | emptied), without_names(after, emptied))
    assert changed == {}, f"nothing else in .restore/ changes — the data/ and report of the stages, the links and the folders named archive.zip or archive.zip.part, the folder not named by a job id, the stage that is a link, the pending restore's state, the lock: {changed}"
    assert cli_secure.entries(outside) == beyond, f"what the links point to, outside the data directory, is untouched: {cli_secure.differences(beyond, cli_secure.entries(outside))}"
    assert protected_stage(root) == protected.name, "the pending restore still waits on its stage"
    print_success("2 decrypted archives and 1 partial removed; their stages' copies and everything else kept")


@pytest.mark.parametrize("through", THROUGH)
def test_while_a_check_runs_nothing_in_the_restore_folder_changes(tmp_path, through):
    """(a) The lock of the checks held by another holder, as while a check runs: its ``archive.zip`` is the check's own,
    in use, as is the partial of a ``restore`` decrypting meanwhile. Nothing in ``.restore/`` changes, to its bytes,
    names, modes and modification times — the running check, its stage and its upload, an unrecorded stage and its
    decrypted archive, a stage and its partial; ``remove_stray_decrypted_archives`` answers 0."""
    root = data_root(tmp_path)
    restore_folders(root)
    interrupted_checks(root, 1)
    stage_holding(root)
    stage_holding(root, archive=PARTIAL_ARCHIVE, data=False)
    before = cli_secure.entries(restore_dir(root))
    holder = cases.hold_the_lock(root)
    try:
        if through == "function":
            removed = remove_stray_archives(root)
            assert removed == 0, f"while a check runs, nothing is removed: 0, not {removed}"
        else:
            sweep(root)
        during = cli_secure.entries(restore_dir(root))
    finally:
        holder.release()
    assert during == before, f"while a check runs nothing in .restore/ changes: {cli_secure.differences(before, during)}"
    print_success("lock held: .restore/ untouched")


@pytest.mark.parametrize("folder", [pytest.param(".restore", id="restore-folder-a-link"), pytest.param("stage", id="stage-folder-a-link")])
def test_no_decrypted_archive_is_removed_through_a_link_in_place_of_a_restore_folder(tmp_path, folder):
    """(a) ``.restore`` or ``.restore/stage`` a link to a folder outside the data directory, a stage holding a decrypted
    archive and one holding a partial there: nothing removed through it (0), its target as it was."""
    root = data_root(tmp_path)
    restore_folders(root)
    stage_holding(root)
    stage_holding(root, archive=PARTIAL_ARCHIVE, data=False)
    moved = moved_behind_a_link(restore_dir(root) if folder == ".restore" else stages_dir(root), tmp_path / "elsewhere" / folder.lstrip("."))
    before = cli_secure.entries(moved)
    removed = remove_stray_archives(root)
    assert removed == 0, f"{folder} is a link: nothing is removed through it, 0, not {removed}"
    assert cli_secure.entries(moved) == before, f"the link's target is untouched: {cli_secure.differences(before, cli_secure.entries(moved))}"
    print_success(f"{folder} a link: nothing removed")


# =============================================================================
# (b) The decrypt folders of inspect
# =============================================================================


def test_the_decrypt_folders_are_named_and_aged_as_the_command_line_names_and_ages_them():
    """(b) One rule, one home: ``.decrypt-`` folders, removed once older than an hour — the age the command line's (j)
    sweeps at, its folders the ones it names."""
    leftovers = leftovers_module()
    assert (leftovers.DECRYPT_FOLDER_PREFIX, leftovers.DECRYPT_FOLDER_LIFETIME) == (".decrypt-", timedelta(hours=1)), f"the rule: {leftovers.DECRYPT_FOLDER_PREFIX!r}, {leftovers.DECRYPT_FOLDER_LIFETIME}"
    assert leftovers.DECRYPT_FOLDER_LIFETIME.total_seconds() == cli_secure.SWEEP_AGE, "the age the command line's (j) sweeps at"
    assert all(name.startswith(leftovers.DECRYPT_FOLDER_PREFIX) for name in [*cli_secure.STALE, *cli_secure.YOUNG]), "the folders the command line's (j) names"
    print_success(".decrypt-*, one hour")


@pytest.mark.parametrize("through", THROUGH)
def test_a_decrypt_folder_a_killed_inspect_left_is_removed_an_hour_on_and_nothing_else(tmp_path, through):
    """(b) The command line's (j) cases in ``backups/``: the two stale folders (two hours old, a clear archive in one, its
    partial in the other) are removed — ``remove_stale_decrypt_folders`` answers 2; the young ones, the link and its
    folder, the file, a job and the earlier backups stay, to their mode and modification time."""
    print_section("(b) The decrypt folders a killed inspect left")
    root = data_root(tmp_path)
    folders = decrypt_leftovers(root, tmp_path)
    before, outside = cli_secure.entries(folders.backups), cli_secure.entries(folders.target.parent)
    if through == "function":
        removed = leftovers_module().remove_stale_decrypt_folders(folders.backups)
        assert removed == len(cli_secure.STALE), f"remove_stale_decrypt_folders answers how many it removed: {len(cli_secure.STALE)}, not {removed}"
    else:
        sweep(root)
    assert stale_left(folders.backups) == [], f"the .decrypt-* folders older than an hour are removed, with the clear file in each: {stale_left(folders.backups)} still there"
    changed = cli_secure.differences(cli_secure.without(before, set(cli_secure.STALE)), cli_secure.entries(folders.backups))
    assert changed == {}, f"nothing else in backups/ changes — the younger folders, the link, the file, the job, the earlier backups: {changed}"
    assert cli_secure.entries(folders.target.parent) == outside, "the folder the link points to, outside the data directory, is untouched"
    print_success(f"{sorted(cli_secure.STALE)} removed, nothing else")


def test_the_age_of_a_decrypt_folder_is_read_against_the_now_given(tmp_path):
    """(b) ``now``: three hours earlier, every folder is younger than an hour and none is removed (0); two hours later,
    the four real folders are all older and all removed (4) — the link and the file never."""
    root = data_root(tmp_path)
    folders = decrypt_leftovers(root, tmp_path)
    remove = leftovers_module().remove_stale_decrypt_folders
    real_folders = {*cli_secure.STALE, *cli_secure.YOUNG}
    before = cli_secure.entries(folders.backups)
    earlier = remove(folders.backups, now=datetime.now(UTC) - timedelta(hours=3))
    assert (earlier, cli_secure.entries(folders.backups) == before) == (0, True), f"three hours earlier nothing is an hour old: {earlier} removed, {cli_secure.differences(before, cli_secure.entries(folders.backups))}"
    later = remove(folders.backups, now=datetime.now(UTC) + timedelta(hours=2))
    left = sorted(name for name in real_folders if os.path.lexists(folders.backups / name))
    assert (later, left) == (len(real_folders), []), f"two hours later every real folder is older than an hour: {later} removed, {left} left"
    changed = cli_secure.differences(cli_secure.without(before, real_folders), cli_secure.entries(folders.backups))
    assert changed == {}, f"the link, the file, the job and the earlier backups stay: {changed}"
    print_success("now - 3 h: 0 removed; now + 2 h: 4 removed")


def backups_missing(backups: Path, elsewhere: Path) -> None:
    """No ``backups/``."""


def backups_a_link(backups: Path, elsewhere: Path) -> None:
    """``backups/`` a link to a folder outside, which holds a stale decrypt folder."""
    backups.symlink_to(elsewhere, target_is_directory=True)


def backups_a_file(backups: Path, elsewhere: Path) -> None:
    """A file where ``backups/`` belongs."""
    backups.write_bytes(b"a file where backups/ belongs")


@pytest.mark.parametrize("arrange", [pytest.param(backups_missing, id="missing"), pytest.param(backups_a_link, id="a-link"), pytest.param(backups_a_file, id="a-file")])
def test_without_a_plain_backups_folder_no_decrypt_folder_is_removed(tmp_path, arrange):
    """(b) ``backups/`` missing, a link (to a folder holding a stale ``.decrypt-*`` folder) or a file: 0, nothing touched,
    nothing created, the link's target as it was."""
    root = data_root(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    cli_secure.folder_holding(elsewhere / ".decrypt-old", STAGE_DECRYPTED_ARCHIVE, CLEAR, cli_secure.OLD)
    arrange(backups_dir(root), elsewhere)
    here, there = cli_secure.entries(root), cli_secure.entries(elsewhere)
    removed = leftovers_module().remove_stale_decrypt_folders(backups_dir(root))
    assert removed == 0, f"backups/ is not a plain folder: 0, not {removed}"
    assert (cli_secure.entries(root), cli_secure.entries(elsewhere)) == (here, there), "nothing touched, nothing created, nothing removed through a link"
    print_success(f"{arrange.__name__}: 0")


# =============================================================================
# (c) The backup jobs
# =============================================================================


@pytest.mark.parametrize("through", THROUGH)
def test_a_backup_its_stopped_server_left_running_is_ended_interrupted_with_only_its_state_left(tmp_path, through):
    """(c) The run lock free, a job recorded running was left by a stopped server: ended as ``get_job`` ends it (failed,
    ``backup_interrupted``, no phase, ``finished_at`` now, the rest of its state as it was), its work files removed,
    ``state.json`` kept; ``end_interrupted_jobs`` answers 1."""
    print_section("(c) A backup its stopped server left running")
    root = data_root(tmp_path)
    job, folder = running_job(root)
    assert sorted(os.listdir(folder)) == sorted([STATE_FILE, *WORK_FILES]) and not jobs._run_lock_held(root), "precondition: a job recorded running with its work files, the run lock free"
    started = datetime.now(UTC)
    if through == "function":
        ended_jobs = end_interrupted_jobs(root)
        assert ended_jobs == 1, f"end_interrupted_jobs answers how many it ended: 1, not {ended_jobs}"
    else:
        sweep(root)
    assert_ended_interrupted(job, folder, started, datetime.now(UTC))
    print_success("failed, backup_interrupted; state.json alone")


@pytest.mark.parametrize("through", THROUGH)
def test_while_a_backup_runs_its_job_is_left_as_it_is(tmp_path, through):
    """(c) The run lock held by another holder, as while ``backup create`` runs: the job recorded running is that run's,
    and nothing in ``backups/.jobs/`` changes (state, work files, modes, modification times); ``end_interrupted_jobs``
    answers 0."""
    root = data_root(tmp_path)
    running_job(root)
    with jobs_cases.lock_held(root):
        before = cli_secure.entries(jobs_dir(root))
        if through == "function":
            ended_jobs = end_interrupted_jobs(root)
            assert ended_jobs == 0, f"while a backup runs, no job is ended: 0, not {ended_jobs}"
        else:
            sweep(root)
        during = cli_secure.entries(jobs_dir(root))
    assert during == before, f"while a backup runs, its job is left as it is: {cli_secure.differences(before, during)}"
    print_success("run lock held: the job untouched")


def test_end_interrupted_jobs_ends_the_job_folders_recorded_running_and_nothing_else(tmp_path):
    """(c) Only a plain folder named by a job id whose state says running is ended (1). Left as they are: a job done and
    one failed ten minutes ago, a job folder whose state cannot be read (``remove_expired_jobs``'s), a link named by a
    job id to a folder outside holding a running state and work files (and that folder), a folder of another name
    holding the same."""
    root = data_root(tmp_path)
    job, folder = running_job(root)
    finished_job(root, ended=RECENTLY)
    finished_job(root, ended=RECENTLY, status="failed")
    unreadable = ensure_private_dir(job_dir(root, new_stage_id()), root)
    cases.write_files(unreadable, {STATE_FILE: b"{not a state", "app.db": WORK_FILES["app.db"]})
    _linked_job, linked = running_job(root)
    target = moved_behind_a_link(linked, tmp_path / "outside" / linked.name)
    _other_job, other = running_job(root)
    other.rename(jobs_dir(root) / "not-a-job-id")
    free_run_lock(root)
    before, beyond = cli_secure.without(cli_secure.entries(jobs_dir(root)), {job.job_id}), cli_secure.entries(target)
    started = datetime.now(UTC)
    ended_jobs = end_interrupted_jobs(root)
    assert ended_jobs == 1, f"one job folder recorded running: 1, not {ended_jobs}"
    assert_ended_interrupted(job, folder, started, datetime.now(UTC))
    changed = cli_secure.differences(before, cli_secure.without(cli_secure.entries(jobs_dir(root)), {job.job_id}))
    assert changed == {}, f"every other entry of .jobs/ is left as it is: {changed}"
    assert cli_secure.entries(target) == beyond, "the folder a link points to is never ended through it"
    print_success("1 ended; finished, unreadable, linked and misnamed folders untouched")


@pytest.mark.parametrize("through", THROUGH)
@pytest.mark.parametrize("folder", [pytest.param("backups", id="backups-a-link"), pytest.param(".jobs", id="jobs-folder-a-link")])
def test_while_backups_or_its_jobs_folder_is_a_link_no_job_is_ended(tmp_path, folder, through):
    """(c) ``backups/``, or ``backups/.jobs``, a link to a folder outside the data directory holding a job recorded
    running, its work files, and the run lock its backup left, free. Both must be plain folders (revision 03:58: a
    ``backups`` link makes the ``.jobs`` inside its target look plain), so nothing is ended through the link:
    ``end_interrupted_jobs`` answers 0, and neither it nor the sweep changes anything in the link's target — the job
    still running there, its state and its work files as they were."""
    root = data_root(tmp_path)
    job, _folder = running_job(root)
    free_run_lock(root)
    target = moved_behind_a_link(backups_dir(root) if folder == "backups" else jobs_dir(root), tmp_path / "outside" / folder.lstrip("."))
    there = (target / jobs_dir(root).name if folder == "backups" else target) / job.job_id
    assert status_of(there) == "running", f"precondition: the link's target holds the job recorded running: {there}"
    before = cli_secure.entries(target)
    if through == "function":
        ended_jobs = end_interrupted_jobs(root)
        assert ended_jobs == 0, f"{folder} is a link: nothing is ended through it, 0, not {ended_jobs}"
    else:
        sweep(root)
    assert status_of(there) == "running", f"the job in the link's target is not ended: {status_of(there)}"
    assert cli_secure.entries(target) == before, f"the link's target is untouched, the job's state and work files as they were: {cli_secure.differences(before, cli_secure.entries(target))}"
    print_success(f"{folder} a link: nothing ended through it")


def test_the_sweep_removes_a_backup_an_hour_after_it_ended_and_keeps_a_recent_one(tmp_path):
    """(c) ``remove_expired_jobs``, now also at startup: a job that ended two hours ago is removed with its archive; one
    that ended ten minutes ago is kept, as it was."""
    root = data_root(tmp_path)
    _old_job, old = finished_job(root, ended=LONG_AGO)
    _recent_job, recent = finished_job(root, ended=RECENTLY)
    kept = cli_secure.entries(recent)
    sweep(root)
    assert not os.path.lexists(old), "the job that ended two hours ago is removed, with its archive"
    assert recent.is_dir() and cli_secure.entries(recent) == kept, "the job that ended ten minutes ago is kept as it was"
    print_success("ended 2 h ago: removed; 10 min ago: kept")


@pytest.mark.parametrize("through", THROUGH)
@pytest.mark.parametrize("folder", [pytest.param("backups", id="backups-a-link"), pytest.param(".jobs", id="jobs-folder-a-link")])
def test_no_expired_job_is_removed_through_a_link_in_place_of_backups_or_its_jobs_folder(tmp_path, folder, through):
    """(c) Revision 03:58: ``remove_expired_jobs`` follows no link, now that it runs at every start. ``backups/``, or
    ``backups/.jobs``, a link to a folder outside the data directory holding a job that ended two hours ago (and the
    run lock its backup left, free): nothing is removed through it — ``remove_expired_jobs`` answers 0, and neither it
    nor the sweep changes anything in the link's target."""
    root = data_root(tmp_path)
    finished_job(root, ended=LONG_AGO)
    free_run_lock(root)
    target = moved_behind_a_link(backups_dir(root) if folder == "backups" else jobs_dir(root), tmp_path / "outside" / folder.lstrip("."))
    before = cli_secure.entries(target)
    if through == "function":
        removed = jobs.remove_expired_jobs(root)
        assert removed == 0, f"{folder} is a link: no job is removed through it, 0, not {removed}"
    else:
        sweep(root)
    assert cli_secure.entries(target) == before, f"the link's target, the job that ended two hours ago in it, is left as it was: {cli_secure.differences(before, cli_secure.entries(target))}"
    print_success(f"{folder} a link: nothing removed through it")


def test_get_job_ends_an_interrupted_backup_and_removes_its_work_files(tmp_path):
    """(c) ``get_job``'s own branch for a run that died: while the run lock is held the job still runs, its work files
    with it; once the lock is free, ``get_job`` answers it failed ``backup_interrupted``, as written in its state, and
    its work files are removed — not only by the next start."""
    root = data_root(tmp_path)
    job, folder = running_job(root)
    with jobs_cases.lock_held(root):
        held, kept = get_job(job.job_id, data_dir=root), sorted(os.listdir(folder))
    assert (held.status, kept) == ("running", sorted([STATE_FILE, *WORK_FILES])), f"while the run lock is held, the job runs and keeps its work files: {held.status}, {kept}"
    started = datetime.now(UTC)
    read = get_job(job.job_id, data_dir=root)
    assert read == read_job(folder), f"get_job answers the state it wrote: {read}"
    assert_ended_interrupted(job, folder, started, datetime.now(UTC))
    print_success("get_job: failed, backup_interrupted, state.json alone")


# =============================================================================
# (d) Never raises
# =============================================================================


@pytest.mark.parametrize(("make", "type_name"), FAILURES)
@pytest.mark.parametrize("part", PARTS)
def test_a_part_that_fails_is_logged_once_and_the_two_others_still_do_their_work(tmp_path, monkeypatch, part, make, type_name):
    """(d) After ``restore-commit`` a step that raises stops every start (N66): the sweep never raises. Every function of
    one part raises: the sweep returns ``None``; that part's work is left undone, the two others do theirs; one error
    is logged for it, «A cleanup of backup leftovers failed», with its ``part`` and the exception's type name — neither
    the exception's message nor a path, nor a traceback, which would carry both."""
    print_section(f"(d) The part {part} fails")
    leftovers = leftovers_module()
    root = data_root(tmp_path)
    world = everything_left(root, tmp_path)
    reached = fail_the_part(monkeypatch, leftovers, part, make(root))
    with apply_cases.logs(LEFTOVERS) as events:
        outcome = leftovers.sweep_backup_leftovers(root)
    assert outcome is None, f"the sweep answers None, whatever failed: {outcome!r}"
    assert reached, f"barrier: the sweep reached a function of the part {part!r} through a name this test replaced"
    assert work_done(world) == {name: name != part for name in PARTS}, f"the two other parts do their whole work, {part} none: done {work_done(world)}"
    assert work_untouched(world)[part], f"the work of {part} is left as it was: {work_untouched(world)}"
    failures = [event for event in events if event.get("event") == FAILURE]
    assert len(failures) == 1, f"one error for the part that failed: {apply_cases.logged(events)}"
    event = failures[0]
    assert (event.get("log_level"), event.get("part")) == ("error", part), f"an error naming the part {part!r}: {event}"
    assert type_name in [value for key, value in event.items() if key not in ("event", "log_level", "part")], f"the exception's type name, {type_name}, is in the error: {event}"
    said = repr(event)
    leaked = [form for form in (MESSAGE_MARK, str(root), str(root.resolve())) if form in said]
    assert leaked == [], f"neither the exception's message nor a path is logged: {leaked} in {event}"
    assert not event.get("exc_info") and not event.get("stack_info"), f"no traceback: it would carry the message and the paths: {event}"
    print_success(f"{part}: {type_name} logged once, the other parts done")


# =============================================================================
# (e) Quiet
# =============================================================================


def a_clean_data_directory(root: Path) -> None:
    """What an instance at rest holds: its live data; a check that ended ten minutes ago, its copy and its report beside
    it; a backup that finished ten minutes ago, with its archive; an earlier backup; the two lock files, free."""
    cases.write_files(root, LIVE_FILES)
    restore_folders(root)
    stage_id = new_stage_id()
    copy = ensure_private_dir(stage_dir(root, stage_id), root)
    cases.write_files(copy, {**STAGE_FILES, STAGE_REPORT_FILE: b"{}\n"})
    recorded_check(root, stage_id, new_stage_id(), status="done")
    finished_job(root, ended=RECENTLY)
    free_run_lock(root)
    (backups_dir(root) / EARLIER_BACKUPS[0]).write_bytes(CLEAR)


def a_bare_data_directory(root: Path) -> None:
    """A data directory where no backup was ever made nor archive checked: no ``.restore/``, no ``backups/``."""
    cases.write_files(root, LIVE_FILES)


@pytest.mark.parametrize("arrange", [pytest.param(a_clean_data_directory, id="nothing-left-behind"), pytest.param(a_bare_data_directory, id="no-restore-no-backups-folder")])
def test_a_data_directory_with_nothing_left_behind_is_swept_in_silence(tmp_path, arrange):
    """(e) Nothing to remove: no exception, nothing logged at INFO or above, and nothing in the data directory changed or
    created — no ``.restore/`` nor ``backups/`` where there was none."""
    leftovers = leftovers_module()
    root = data_root(tmp_path)
    arrange(root)
    before = cli_secure.entries(root)
    with apply_cases.logs(LEFTOVERS) as events:
        outcome = leftovers.sweep_backup_leftovers(root)
    assert outcome is None, f"the sweep answers None: {outcome!r}"
    assert apply_cases.levels(events) & SEEN_LEVELS == set(), f"a start with nothing left behind logs nothing at INFO or above: {apply_cases.logged(events)}"
    assert cli_secure.entries(root) == before, f"nothing changed or created: {cli_secure.differences(before, cli_secure.entries(root))}"
    print_success(f"{arrange.__name__}: silent, untouched")


# =============================================================================
# (f) What was removed or ended, said once
# =============================================================================


def test_what_the_sweep_removed_and_ended_is_said_once_with_its_counts(tmp_path, monkeypatch):
    """(f) One INFO «Backup leftovers removed at startup» with the five counts, ``checks_interrupted`` first: 5 checks
    ended, 1 decrypted archive, 2 decrypt folders, 3 interrupted jobs, 4 expired jobs — distinct, so that two swapped
    fields show. Called without a data directory, as the step calls it: the configured one. Two orders show in the
    counts: ``prune`` removes the five checks' stages, decrypted archives included, before
    ``remove_stray_decrypted_archives`` runs (1, not 6); the job interrupted three hours ago is ended before the expired
    ones are removed, so it is kept, as any job that ends now (3 and 4, not 2 and 5)."""
    print_section("(f) What the sweep removed, said once")
    leftovers_module()
    root = data_root(tmp_path)
    world = everything_left(root, tmp_path)
    cases.configure(monkeypatch, root)
    with apply_cases.logs(LEFTOVERS) as events:
        sweep()
    counts = summary_counts(events)
    expected = {"checks_interrupted": INTERRUPTED_CHECKS, "decrypted_archives": 1, "decrypt_folders": len(cli_secure.STALE), "jobs_interrupted": len(INTERRUPTED_STARTS), "jobs_expired": EXPIRED_JOBS}
    assert len(set(expected.values())) == len(expected), f"precondition: five distinct counts: {expected}"
    assert counts == expected, f"the counts of what was removed and ended: {counts}, not {expected}"
    assert work_done(world) == dict.fromkeys(PARTS, True), f"every part did its work: {work_done(world)}"
    assert [event for event in events if event.get("event") == FAILURE] == [], f"no part failed: {apply_cases.logged(events)}"
    print_success(f"{SUMMARY}: {counts}")


# =============================================================================
# (g) The startup step
# =============================================================================


@pytest.mark.asyncio
async def test_the_startup_step_backup_leftovers_runs_the_sweep_once_in_a_worker_thread(monkeypatch):
    """(g) ``Step("backup-leftovers", lambda: asyncio.to_thread(sweep_backup_leftovers))``: ``run()`` returns an
    awaitable; awaited, it calls ``app_lifespan.sweep_backup_leftovers`` — read from the module then — once, without
    arguments, in a worker thread: its file I/O and its lock probes never block the event loop. The real sweep never
    runs here; its place in ``STARTUP_STEPS`` is pinned in ``test_backup_apply.py`` (j)."""
    from backend.app.services.platform import app_lifespan  # noqa: PLC0415 — the app's whole startup, imported by the one test that needs it

    assert hasattr(app_lifespan, "sweep_backup_leftovers"), "[new] app_lifespan imports sweep_backup_leftovers (§1, N66)"
    steps = [step for step in app_lifespan.STARTUP_STEPS if step.name == "backup-leftovers"]
    assert len(steps) == 1, f"[new] one startup step 'backup-leftovers': {[step.name for step in app_lifespan.STARTUP_STEPS]}"
    calls: list[tuple[tuple, dict, int]] = []

    def replacement(*args: Any, **kwargs: Any) -> None:
        calls.append((args, kwargs, threading.get_ident()))

    monkeypatch.setattr(app_lifespan, "sweep_backup_leftovers", replacement)
    outcome = steps[0].run()
    assert inspect.isawaitable(outcome), f"run() returns the awaitable of asyncio.to_thread, not {outcome!r}"
    await outcome
    assert [(args, kwargs) for args, kwargs, _thread in calls] == [((), {})], f"app_lifespan.sweep_backup_leftovers called once, without arguments: {calls}"
    assert calls[0][2] != threading.get_ident(), "called in a worker thread, off the event loop"
    print_success("backup-leftovers → app_lifespan.sweep_backup_leftovers(), in a thread")
