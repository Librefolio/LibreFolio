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
``app_lifespan.py``. The frozen contract: ``b4b-test-brief.md`` §1, with its revision of 03:58. And B-50, (h): what
``restore_jobs`` and ``jobs`` make of a state no reader can take, through ``restore_jobs._checks``, ``prune``,
``read_check``, ``remove_check``, ``confirm_check``, ``start_check``, ``UploadWriter.finish`` and the sweep; its contract:
``b50-contract.md``. And B-53, B-54, B-55, (i): one reader of the check states, through the same functions; its contract:
``b53-contract.md``.

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
(h) B-50: a state no reader can take is no state, never a failed sweep (the coordinator, 19/10 17:37 and 20/10 09:06).
    A check's state that is JSON but no object (``[]``, ``null``, ``"x"``, ``5``) is skipped as ``_read_state`` already
    skips an empty file, ``{}``, a folder where the file belongs and a file of mode 000: ``_checks`` answers the checks
    it reads; ``prune`` does its usual work on them (a check a stopped server left running ended, one that ended 25
    hours ago removed with its copy, one that ended ten minutes ago kept) and leaves the unreadable state as it was;
    ``read_check``, ``remove_check`` and ``confirm_check`` of its id raise ``CheckNotFoundError`` — the routes' 404
    ``restore_stage_not_found`` — and log nothing; a check starts beside it, and an upload that finishes still replaces
    the one before; the sweep logs neither an error nor a warning, and does the whole work of its ``restore`` part; a
    state that is a folder, read 20 times, leaves no descriptor open on it. A job's ``state.json`` that is JSON but no
    object, a folder or a file the server may not read is a job without a state, as one missing, empty or ``{}``
    already is: the sweep logs no error, ends the run that died, removes the job that ended two hours ago, keeps the
    one that ended ten minutes ago, and dates the unreadable folder by its modification time — kept ten minutes on,
    removed two hours on, whatever a state of mode 000 would say were it read.
(i) B-53, B-54, B-55 (the coordinator, 20/10 10:10). A transient error (EIO) on a valid check's state is never «no
    check»: ``read_check``, ``_checks`` and ``prune`` raise it, and ``prune`` removes nothing, not even an ended check a
    day old beside it; a check's start raises it, nothing started, its upload kept; an upload that finishes raises it,
    no upload removed; the sweep logs one error for its ``restore`` part and does the work of the two others; readable
    again, the check answers as it was. In a state's place, a link (to a valid state of that id, or to nothing), a FIFO,
    a done check's state whose ``created_at`` or ``finished_at`` has no time zone: no check, in silence, within a
    deadline, no descriptor left on the FIFO. While no check runs, ``prune`` removes from ``checks/`` an unreadable
    ``<id>.json`` or ``<id>.json.part`` older than ``STAGE_LIFETIME`` by its own modification time — a file whatever
    its content or mode, a folder with its content, a link (never its target), a FIFO —, in silence, its usual work on
    the readable checks unchanged; kept: everything while a check runs, the protected stage's, the names that are no
    state's. The startup sweep returns in time beside a FIFO in a check state's place, and (point 7, 10:39) beside a FIFO
    in place of a job's ``state.json``: the jobs part does its usual work, dates such a folder by its modification time,
    and logs no error.

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
(h) reads a file of mode 000 by ``lstat`` alone (``as_left``), and gives every mode back when the test ends
(``mode_000``); the thread of a check's start runs inline (``InlineThreads``, as the API tests' ``Threads``), on an
upload that is no archive: the check stops at its first bytes, before any copy is made or any database opened. The
descriptors left open on a folder are found in ``/dev/fd`` by its device and inode (``descriptors_on`` of
``test_backup_archive.py``, imported, with its ``needs_dev_fd``), behind a barrier: one the test opens itself is found.
(i) makes the global ``os.open`` refuse one path (``refuse_open``, as ``refused_for`` of ``test_backup_cli_restore.py``),
checked, for as long as a ``monkeypatch.context`` lasts; runs every call that may meet a FIFO in a thread of its own,
given a deadline (``within_deadline``), and lets a reader left waiting go before it returns (``let_readers_go``: a
writer opened without waiting, closed at once), so that a red run never hangs the suite.

Pure: every path under ``tmp_path``. This process's production data directory is a folder of the test that must stay
absent but where a test configures its own (``configured_data_dir`` of the staging tests, imported, autouse): the lane's
data directory is never reached. No database, no server, no network, no sleep. Modes, links and ``flock`` are
POSIX-only.

Written RED, before B4b: ``instance_backup.leftovers`` does not exist, nor do
``restore_jobs.remove_stray_decrypted_archives`` and ``jobs.end_interrupted_jobs``. Each is looked up by the test that
needs it (``leftovers_module``, ``new_function``), never at collection: the file collects without them, and each test
fails on its own with a "[new] …" message. The cases on what exists already fail on what it does today: ``get_job``
leaves the work files, ``prune`` answers ``None``, ``remove_expired_jobs`` removes a job through a link.

Written RED again for B-50, before its cure: JSON that is no object raises ``AttributeError`` from
``restore_jobs._read_state`` (``record.get``) and from ``BackupJob.from_json`` (``.items()``), and a job's ``state.json``
that is a folder or of mode 000 raises ``IsADirectoryError`` or ``PermissionError`` from ``jobs._read_state``: nobody
catches them, and the rows of (h) that hold one fail on it. A check state that is a folder reads as none today, yet each
read leaves a descriptor open on it (``os.fdopen`` refuses a folder without closing the descriptor it is handed): the
test that looks for them fails, 20 reads leaving 20. The other rows of (h), what the readers already take for no state,
are guards, green today.

Written RED again for B-53, B-54 and B-55, before their cure: ``restore_jobs._read_state`` takes every ``OSError`` for
«no check», EIO included; waits forever on a FIFO; reads a date without a time zone, which ``prune`` then compares with
an aware one (``TypeError``) or uses to remove the check; and ``prune`` never removes an unreadable entry of ``checks/``.
The jobs' reader, too, waits forever on a FIFO in place of a job's ``state.json``. The rows of (i) that meet one of those
fail on it; the links, the names that are no state's and most rows of the keepers are guards, green today. Each test of
(i) names its red rows.
"""

from __future__ import annotations

import errno
import importlib
import inspect
import json
import os
import stat
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
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
    is_plain_dir,
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
from backend.app.services.platform.instance_backup.staging import STAGE_LIFETIME, new_stage_id
from backend.test_scripts.test_services import test_backup_apply as apply_cases
from backend.test_scripts.test_services import test_backup_archive as archive_cases
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


# =============================================================================
# (h) B-50, unreadable states: skipped, never a failed sweep
# =============================================================================
#
# A state no reader can take for one is no state. The coordinator, 19/10 17:37: the cure in two files, the 404
# ``backup_job_not_found`` for an unreadable state, in the backup as in the restore (whose own not-found is
# ``restore_stage_not_found``); 20/10 09:06, its perimeter: a ``state.json`` that is a folder, or that the server may not
# read, is unreadable too, while any other ``OSError`` (transient) stays a 500 the tab retries. A check's unreadable
# state reads as no check, unlogged; a job's as a job without a state, dated by its folder's modification time. Each row
# of the lists below is one way a state cannot be read: the rows red until the cure are named with each list, the others
# are guards, green today and to stay green.

#: JSON that is no object, a state's whole content. ``restore_jobs._read_state`` calls ``record.get`` on it and
#: ``BackupJob.from_json`` ``.items()``: today neither catches the ``AttributeError``. Red until B-50's cure.
NOT_AN_OBJECT = {"json-list": b"[]", "json-null": b"null", "json-string": b'"x"', "json-number": b"5"}
#: Contents every reader already takes for no state: an empty file, an object without a field of a state. Guards.
ALREADY_NO_STATE = {"empty-file": b"", "empty-object": b"{}"}
#: What a state file holds, for the ways that are a content.
CONTENTS = {**NOT_AN_OBJECT, **ALREADY_NO_STATE}
#: The ways a check's state cannot be read. Red until the cure: ``NOT_AN_OBJECT``. Guards: what ``_read_state`` already
#: answers ``None`` for — ``ALREADY_NO_STATE``, a folder where the file belongs (whose descriptor each read leaves open,
#: though: red, ``FOLDER_READS``), a file of mode 000 (root reads it all the same: skipped as root).
CHECK_STATES = [
    *(pytest.param(how, id=how) for how in CONTENTS),
    pytest.param("a-folder", id="a-folder"),
    pytest.param("mode-000", id="mode-000", marks=cases.needs_permission_checks),
]
#: The ways a job's ``state.json`` cannot be read. Red until the cure: ``NOT_AN_OBJECT`` (``AttributeError``), a folder
#: (``IsADirectoryError``), a file of mode 000 (``PermissionError``; skipped as root) — the perimeter of 20/10 09:06.
#: Guards: no ``state.json`` at all, and ``ALREADY_NO_STATE``.
JOB_STATES = [
    *(pytest.param(how, id=how) for how in NOT_AN_OBJECT),
    pytest.param("a-folder", id="a-folder"),
    pytest.param("mode-000", id="mode-000", marks=cases.needs_permission_checks),
    pytest.param("no-state-file", id="no-state-file"),
    *(pytest.param(how, id=how) for how in ALREADY_NO_STATE),
]
#: An upload that is neither a zip nor an envelope: its check ends at its first bytes, ``not_a_backup``, before any copy
#: is made or any database opened.
NOT_A_BACKUP = b"neither a zip nor an envelope: the file an administrator uploaded"
#: The lines an operator must look at: a check's unreadable state never makes one (contract §3: unlogged).
WARNED_LEVELS = {"warning", "error", "critical"}
#: An error, what a failed part of the sweep is logged at.
ERROR_LEVELS = {"error", "critical"}


class Mode000:
    """The files a test made mode 000, each given its mode back when the test ends, whatever happened (as ``Modes`` of
    ``test_backup_apply.py`` (o)), so that pytest can remove ``tmp_path``; one the sweep removed meanwhile, with its
    folder, needs nothing."""

    def __init__(self) -> None:
        self._made: list[tuple[Path, int]] = []

    def make(self, path: Path) -> None:
        self._made.append((path, stat.S_IMODE(path.lstat().st_mode)))
        path.chmod(0o000)

    def put_back(self) -> None:
        while self._made:
            path, mode = self._made.pop()
            if os.path.lexists(path):
                path.chmod(mode)


@pytest.fixture
def mode_000() -> Iterator[Mode000]:
    """``Mode000`` for one test."""
    made = Mode000()
    try:
        yield made
    finally:
        made.put_back()


def as_left(path: Path) -> dict[str, tuple[int, int, int, int]]:
    """``path`` and, when it is a folder itself (never one a link points to), everything below it, read without opening a
    file nor following a link — a file of mode 000 or a FIFO too, whose bytes ``entries`` would have to read: each
    entry's kind, mode, size and modification time."""
    below = [Path(folder, name) for folder, folders, files in os.walk(path) for name in (*folders, *files)] if stat.S_ISDIR(path.lstat().st_mode) else []
    found: dict[str, tuple[int, int, int, int]] = {}
    for entry in (path, *below):
        info = entry.lstat()
        found[entry.relative_to(path.parent).as_posix()] = (stat.S_IFMT(info.st_mode), stat.S_IMODE(info.st_mode), info.st_size, info.st_mtime_ns)
    return found


def logged_at(events: list[dict[str, Any]], levels: set[str]) -> list[dict[str, Any]]:
    """The events logged at one of ``levels``, the canary of ``logs`` left out: whole, so that a failure shows the
    ``part`` and the ``error`` of each."""
    return [event for event in events if event.get("log_level") in levels and event.get("event") != apply_cases.LOG_CANARY]


# -----------------------------------------------------------------------------
# The restore's checks
# -----------------------------------------------------------------------------

#: The suffix of a check's state being written (``_write_state``): ``<id>.json.part``, renamed once whole.
PARTIAL_STATE = ".part"
#: What a ``<id>.json.part`` holds when its writer was killed half-way: half a state.
HALF_WRITTEN = b'{"stage_id": "0123456789abcdef0123456789abcdef", "upload_id": "0123'


def outside_checks(root: Path) -> Path:
    """A folder beside the data directory, never in it: where a link in a check state's place points (i-2)."""
    return root.parent / "outside-checks"


def without_time_zone(path: Path, key: str) -> None:
    """The date ``key`` of the check state at ``path`` written again without its time zone, the rest as it was."""
    record = json.loads(path.read_text(encoding="utf-8"))
    record[key] = datetime.fromisoformat(record[key]).replace(tzinfo=None).isoformat()
    path.write_text(json.dumps(record), encoding="utf-8")


def unreadable_check_state(root: Path, how: str, mode_000: Mode000, *, says_ended: timedelta = RECENTLY) -> str:
    """A check's state no reader can take for one, ``.restore/checks/<id>.json``, as ``how`` says. ``CHECK_STATES``: a
    content of ``CONTENTS``, 0600 as the checks write theirs; a folder where the file belongs; or the state of a check
    that ended ten minutes ago, made mode 000. ``NEW_SHAPES`` (i-2): a link to such a state of that very id, moved to
    ``outside_checks`` — followed, it would answer a check —, or a link to nothing there; a FIFO; the state of a check
    that ended ``says_ended`` ago, its ``created_at`` or its ``finished_at`` (``naive-<key>``) written without a time
    zone. ``half-written-part`` (i-3): no state, but a ``<id>.json.part`` holding ``HALF_WRITTEN``. Its id."""
    stage_id = new_stage_id()
    path = check_state_path(root, stage_id)
    if how == "a-folder":
        path.mkdir(mode=0o700)
    elif how == "mode-000":
        recorded_check(root, stage_id, new_stage_id(), status="done")
        mode_000.make(path)
    elif how in ("link-to-a-check", "dangling-link"):
        target = outside_checks(root) / path.name
        if how == "link-to-a-check":
            target.parent.mkdir(exist_ok=True)
            recorded_check(root, stage_id, new_stage_id(), status="done")
            path.replace(target)
        path.symlink_to(target)
    elif how == "fifo":
        os.mkfifo(path, 0o600)
    elif how.startswith("naive-"):
        recorded_check(root, stage_id, new_stage_id(), status="done", ended_ago=says_ended)
        without_time_zone(path, how.removeprefix("naive-"))
    elif how == "half-written-part":
        part = path.with_name(path.name + PARTIAL_STATE)
        part.write_bytes(HALF_WRITTEN)
        part.chmod(0o600)
    else:
        path.write_bytes(CONTENTS[how])
        path.chmod(0o600)
    return stage_id


@dataclass(frozen=True)
class ChecksBeside:
    """``.restore/`` where ``prune`` has its usual work, beside a check's state no reader can take: a check that ended 25
    hours ago, with its copy (``old``); one that ended ten minutes ago, with its copy (``recent``); one a stopped server
    left running, with its stage and its upload (``interrupted``). And the id of the unreadable state."""

    old: RestoreCheck
    recent: RestoreCheck
    interrupted: InterruptedCheck
    unreadable: str


def checks_beside(root: Path, how: str, mode_000: Mode000, *, says_ended: timedelta = RECENTLY) -> ChecksBeside:
    """``ChecksBeside`` in ``root``, the lock of the checks there and free; the unreadable state made last, as ``how``
    says (``says_ended``: what the dates of a ``naive-*`` one say), once the running check was read as running while its
    lock was held (``interrupted_checks``)."""
    restore_folders(root)
    old_id, recent_id = new_stage_id(), new_stage_id()
    stage_holding(root, old_id, archive=None, report=True)
    old = recorded_check(root, old_id, new_stage_id(), status="done", ended_ago=timedelta(hours=25))
    stage_holding(root, recent_id, archive=None, report=True)
    recent = recorded_check(root, recent_id, new_stage_id(), status="done")
    [interrupted] = interrupted_checks(root, 1)
    return ChecksBeside(old=old, recent=recent, interrupted=interrupted, unreadable=unreadable_check_state(root, how, mode_000, says_ended=says_ended))


def readable_checks(root: Path) -> dict[str, str]:
    """``restore_jobs._checks``, what ``prune`` and an upload that finishes read: every check it answers, by id, with its
    status."""
    return {check.stage_id: check.status for check in restore_jobs._checks(root)}


def assert_prune_did_its_usual_work(root: Path, world: ChecksBeside) -> None:
    """``prune``'s usual work on the checks it reads: the one a stopped server left running ended ``restore_interrupted``,
    its stage and its upload removed; the one that ended 25 hours ago removed with its copy; the one that ended ten
    minutes ago kept as it was, with its copy."""
    assert ended_interrupted(root, world.interrupted), f"the check a stopped server left running is ended restore_interrupted, its stage and its upload removed: {check_state(root, world.interrupted.stage_id)}"
    old = (check_state(root, world.old.stage_id), os.path.lexists(stage_dir(root, world.old.stage_id)))
    assert old == (None, False), f"the check that ended 25 hours ago is removed with its copy: its state {old[0]}, its copy there {old[1]}"
    recent = restore_jobs.read_check(world.recent.stage_id, data_dir=root)
    assert (recent, stage_dir(root, world.recent.stage_id).is_dir()) == (world.recent, True), f"the check that ended ten minutes ago is kept as it was, with its copy: {recent}"


def assert_prune_did_its_work(root: Path, world: ChecksBeside, unreadable: dict[str, tuple[int, int, int, int]]) -> None:
    """``prune``'s usual work (``assert_prune_did_its_usual_work``), and the unreadable state, just made, left as it was
    (``unreadable``: its ``as_left`` before)."""
    assert_prune_did_its_usual_work(root, world)
    path = check_state_path(root, world.unreadable)
    assert os.path.lexists(path), "the unreadable state, just made, is left: it was removed"
    assert as_left(path) == unreadable, "the unreadable state, just made, is left as it was"


@pytest.mark.parametrize("how", CHECK_STATES)
def test_an_unreadable_check_state_is_skipped_and_prune_does_its_work(tmp_path, mode_000, how):
    """(h) B-50. ``_checks`` answers the three checks it reads and skips the unreadable state; ``prune``, which reads them
    through it, does its usual work on them and answers 1, the check it ended as interrupted. Red until the cure for
    ``NOT_AN_OBJECT``: ``_read_state`` raises ``AttributeError`` (``record.get``), which nobody catches — every new check
    (``start_check`` prunes first) and every upload that finishes is a 500. Guards, the other rows."""
    print_section(f"(h) B-50 An unreadable check state, {how}: prune")
    root = data_root(tmp_path)
    world = checks_beside(root, how, mode_000)
    unreadable = as_left(check_state_path(root, world.unreadable))
    found = readable_checks(root)
    expected = {world.old.stage_id: "done", world.recent.stage_id: "done", world.interrupted.stage_id: "running"}
    assert found == expected, f"_checks answers the three checks it reads, and skips the unreadable state: {found}"
    answer = prune(root)
    assert answer == 1, f"prune ends the check a stopped server left running, and answers 1, not {answer!r}"
    assert_prune_did_its_work(root, world, unreadable)
    print_success(f"{how}: skipped; prune ended 1 check, removed 1, kept 1")


def read_it(root: Path, stage_id: str) -> object:
    """``GET /backup/restore/stage/{id}``."""
    return restore_jobs.read_check(stage_id, data_dir=root)


def remove_it(root: Path, stage_id: str) -> object:
    """``DELETE /backup/restore/stage/{id}``."""
    return restore_jobs.remove_check(stage_id, data_dir=root)


def confirm_it(root: Path, stage_id: str) -> object:
    """``POST /backup/restore/stage/{id}/confirm``."""
    return restore_jobs.confirm_check(stage_id, confirmed_by="cli", data_dir=root)


#: What the three routes that reach a check by its id call: each answers ``CheckNotFoundError`` with its 404
#: ``restore_stage_not_found`` (``api/v1/backup/restore.py``).
BY_ITS_ID = [pytest.param(read_it, id="read_check"), pytest.param(remove_it, id="remove_check"), pytest.param(confirm_it, id="confirm_check")]


@pytest.mark.parametrize("reach", BY_ITS_ID)
@pytest.mark.parametrize("how", CHECK_STATES)
def test_a_check_whose_state_is_unreadable_is_not_found_and_nothing_is_logged(tmp_path, mode_000, how, reach):
    """(h) B-50. A check whose state no reader can take is no check: reading it, removing it and confirming its restore
    raise ``CheckNotFoundError`` — the routes' 404 ``restore_stage_not_found``, the restore's own not-found —, nothing is
    logged (contract §3: unlogged, as the other unreadable checks today), and nothing in ``.restore/`` is written or
    removed. Red until the cure for ``NOT_AN_OBJECT``: ``AttributeError``, a 500. Guards, the other rows."""
    root = data_root(tmp_path)
    restore_folders(root)
    stage_id = unreadable_check_state(root, how, mode_000)
    before = as_left(restore_dir(root))
    with apply_cases.logs(restore_jobs.__name__) as events, pytest.raises(restore_jobs.CheckNotFoundError):
        reach(root, stage_id)
    assert apply_cases.logged(events) == [], f"an unreadable check is not found in silence: {apply_cases.logged(events)}"
    after = as_left(restore_dir(root))
    assert after == before, f"nothing in .restore/ is written or removed: {cli_secure.differences(before, after)}"
    print_success(f"{how}, {reach.__name__}: CheckNotFoundError, nothing logged")


#: How often the descriptor test reads a check state that is a folder: each read opens the folder and, until B-50's cure,
#: leaves its descriptor open — that many left, then.
FOLDER_READS = 20


def read_every_check(root: Path, stage_id: str) -> None:
    """``restore_jobs._checks``, what ``prune``, an upload that finishes and a check's start read: it skips the state."""
    found = restore_jobs._checks(root)
    assert found == [], f"_checks skips a check state that is a folder: {found}"


def read_that_check(root: Path, stage_id: str) -> None:
    """``read_check`` of the state's id, what the routes call: no check."""
    with pytest.raises(restore_jobs.CheckNotFoundError):
        restore_jobs.read_check(stage_id, data_dir=root)


@archive_cases.needs_dev_fd
@pytest.mark.parametrize("reader", [pytest.param(read_every_check, id="_checks"), pytest.param(read_that_check, id="read_check")])
def test_reading_a_check_state_that_is_a_folder_leaves_no_descriptor_open(tmp_path, mode_000, reader):
    """(h) B-50, the descriptor. A check state that is a folder reads as no check (the rows ``a-folder`` above), yet each
    read opens the folder and leaves its descriptor open: ``os.fdopen`` refuses a folder without closing the descriptor
    it is handed — the defect ``test_backup_archive.py`` (f) pins for ``_add_file``. In a server every prune, upload that
    finishes, check's start and read of that id keeps one more, up to «too many open files». After 20 reads, through
    ``_checks`` or ``read_check``, no descriptor of this process is open on the folder. Red until the cure: 20 are,
    closed by the test, so that a red run carries none into the tests that follow."""
    root = data_root(tmp_path)
    restore_folders(root)
    stage_id = unreadable_check_state(root, "a-folder", mode_000)
    folder = check_state_path(root, stage_id)
    assert archive_cases.descriptors_on(folder) == [], "precondition: no descriptor of this process is open on the folder"
    probe = os.open(folder, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))  # as restore_jobs opens a state
    try:
        seen = archive_cases.descriptors_on(folder)
    finally:
        os.close(probe)
    closed = archive_cases.descriptors_on(folder)
    assert (seen, closed) == ([probe], []), f"barrier: /dev/fd lists this process's descriptors, and the folder opens as restore_jobs opens a state — the test's own found on it, then none once closed: {seen}, then {closed}"
    try:
        for _ in range(FOLDER_READS):
            reader(root, stage_id)
    finally:
        left_open = archive_cases.descriptors_on(folder)
        for fd in left_open:
            os.close(fd)  # a red run must not carry them into the tests that follow
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on a check state that is a folder by {FOLDER_READS} reads through {reader.__name__}: one per read, os.fdopen refusing a folder without closing the descriptor it is handed: {left_open}"
    print_success(f"{reader.__name__}: {FOLDER_READS} reads of a folder, no descriptor left open")


@pytest.mark.parametrize("how", CHECK_STATES)
def test_an_upload_that_finishes_beside_an_unreadable_check_state_replaces_the_one_before(tmp_path, mode_000, how):
    """(h) B-50. An upload that finishes drops the uploads it replaces but the one a running check reads
    (``_remove_replaced_uploads``, which reads every check). Beside an unreadable check state, while a check runs: the
    upload is received under its id, the upload before it removed, the one the running check reads kept. Red until the
    cure for ``NOT_AN_OBJECT``: ``finish`` raises ``AttributeError`` once the archive is in place — the upload's request
    a 500, the upload it replaces left. Guards, the other rows."""
    root = data_root(tmp_path)
    restore_folders(root)
    earlier = an_upload(root, new_stage_id())
    read = an_upload(root, new_stage_id())
    recorded_check(root, new_stage_id(), read.name)
    unreadable_check_state(root, how, mode_000)
    holder = cases.hold_the_lock(root)
    try:
        writer = restore_jobs.UploadWriter(root, max_bytes=None, declared=None)
        writer.write(CLEAR)
        received = writer.finish()
    finally:
        holder.release()
    assert received == restore_jobs.RestoreUploaded(upload_id=writer.upload_id, size=len(CLEAR), kind="zip"), f"the upload is received: {received}"
    assert upload_path(root, received.upload_id).read_bytes() == CLEAR, "the archive is kept under its id, as sent"
    assert (os.path.lexists(earlier), read.is_file()) == (False, True), "the upload before it is replaced; the one a running check reads is kept"
    print_success(f"{how}: received; the upload before it removed, the one a check reads kept")


class InlineThreads:
    """``threading`` as ``restore_jobs`` sees it: the thread a start makes runs its target at once, inside the call that
    starts it, so the check has ended when ``start_check`` returns (the API tests' ``Threads``, ``test_backup_restore.py``,
    never holding one). What the target raises is kept, as a real thread would lose it."""

    def __init__(self) -> None:
        self.started: list[str | None] = []
        self.raised: list[Exception] = []

    def Thread(self, *, target: Callable[..., Any], args: tuple[Any, ...] = (), kwargs: dict[str, Any] | None = None, name: str | None = None, daemon: bool | None = None) -> SimpleNamespace:  # the name restore_jobs calls
        def start() -> None:
            self.started.append(name)
            try:
                target(*args, **(kwargs or {}))
            except Exception as exc:
                self.raised.append(exc)

        return SimpleNamespace(start=start)


@pytest.mark.parametrize("how", CHECK_STATES)
def test_a_check_starts_beside_an_unreadable_check_state(tmp_path, monkeypatch, mode_000, how):
    """(h) B-50. ``start_check`` prunes first. Beside an unreadable check state, the check of an upload still starts, in
    its thread, and runs to its end — here at once: ``failed``/``not_a_backup``, the upload being no backup —, its upload
    removed and the lock of the checks free again. Red until the cure for ``NOT_AN_OBJECT``: the start raises
    ``AttributeError`` from ``prune`` before it takes the lock — every new check a 500. Guards, the other rows."""
    root = data_root(tmp_path)
    restore_folders(root)
    unreadable_check_state(root, how, mode_000)
    upload_id = new_stage_id()
    upload = upload_path(root, upload_id)
    upload.write_bytes(NOT_A_BACKUP)
    upload.chmod(0o600)
    threads = InlineThreads()
    monkeypatch.setattr(restore_jobs, "threading", threads)
    first = restore_jobs.start_check(upload_id, data_dir=root)
    started = (first.upload_id, first.status, len(threads.started), threads.raised)
    assert started == (upload_id, "running", 1, []), f"the check of the upload starts, in its thread, which raises nothing: {first}, {threads.started}, {threads.raised}"
    ended = restore_jobs.read_check(first.stage_id, data_dir=root)
    assert (ended.status, ended.error_code) == ("failed", "not_a_backup"), f"the check ran to its end, as any check of a file that is no backup: {ended}"
    assert (upload.exists(), cases.lock_is_free(root)) == (False, True), "its upload is removed, and the lock of the checks is free again"
    print_success(f"{how}: the check started and ended, not_a_backup")


@pytest.mark.parametrize("how", CHECK_STATES)
def test_the_sweep_cleans_the_checks_beside_an_unreadable_check_state_and_logs_no_error(tmp_path, mode_000, how):
    """(h) B-50. The sweep's ``restore`` part beside an unreadable check state: neither an error nor a warning logged, and
    its whole work done — ``prune``'s (the check a stopped server left running ended, the one 25 hours old removed with
    its copy, the recent one kept, the unreadable state left as it was), then the decrypted archive a killed check left
    in a copy removed; its INFO line says so, ``checks_interrupted`` 1 and ``decrypted_archives`` 1, every other count 0.
    Red until the cure for ``NOT_AN_OBJECT``: the part fails at ``prune`` — «A cleanup of backup leftovers failed»,
    ``part`` ``restore``, ``AttributeError`` — and none of that work is done. Guards, the other rows."""
    print_section(f"(h) B-50 An unreadable check state, {how}: the sweep")
    root = data_root(tmp_path)
    world = checks_beside(root, how, mode_000)
    stray = stage_holding(root) / STAGE_DECRYPTED_ARCHIVE
    unreadable = as_left(check_state_path(root, world.unreadable))
    with apply_cases.logs(LEFTOVERS) as events:
        sweep(root)
    warned = logged_at(events, WARNED_LEVELS)
    assert warned == [], f"an unreadable check state is no check: the restore part does not fail, and nothing is said of it: {warned}"
    assert_prune_did_its_work(root, world, unreadable)
    assert not os.path.lexists(stray), "the decrypted archive a killed check left in a copy is removed, after prune, in the same part"
    counts = summary_counts(events)
    assert counts == {**dict.fromkeys(COUNTS, 0), "checks_interrupted": 1, "decrypted_archives": 1}, f"the sweep says what it did, and nothing else: {counts}"
    print_success(f"{how}: nothing logged above INFO; 1 check ended, 1 removed, 1 decrypted archive removed")


# -----------------------------------------------------------------------------
# The backup jobs
# -----------------------------------------------------------------------------


def unreadable_job_folder(root: Path, how: str, mode_000: Mode000, *, age: timedelta) -> Path:
    """A job folder, ``backups/.jobs/<id>/``, whose ``state.json`` no reader can take for a state, as ``how`` says
    (``JOB_STATES``): a content of ``CONTENTS``; a folder; none at all; or the state of a finished job, beside its
    archive, made mode 000 — a state that says the opposite of the folder's age (ended two hours ago in a folder ten
    minutes old, and the reverse), so that only the folder's modification time can decide. And (i-5) a FIFO (``fifo``),
    never in ``JOB_STATES``: a sweep that waits on it must run within a deadline. The folder, last modified ``age`` ago
    once everything in it is made."""
    if how == "mode-000":
        _job, folder = finished_job(root, ended=RECENTLY if age > jobs.JOB_RETENTION else LONG_AGO)
        mode_000.make(folder / STATE_FILE)
    else:
        folder = ensure_private_dir(job_dir(root, new_stage_id()), root)
        if how == "a-folder":
            (folder / STATE_FILE).mkdir(mode=0o700)
        elif how == "fifo":
            os.mkfifo(folder / STATE_FILE, 0o600)
        elif how != "no-state-file":
            (folder / STATE_FILE).write_bytes(CONTENTS[how])
    return cli_secure.aged(folder, age.total_seconds())


@pytest.mark.parametrize("how", JOB_STATES)
def test_the_sweep_cleans_the_jobs_beside_an_unreadable_job_state_and_logs_no_error(tmp_path, mode_000, how):
    """(h) B-50. The sweep's ``jobs`` part beside two job folders whose ``state.json`` no reader can take, one last
    modified ten minutes ago, one two hours ago: no error logged; the run a stopped server left running ended
    ``backup_interrupted``, its state alone left; the job that ended two hours ago removed; the one that ended ten minutes
    ago kept as it was; the unreadable folder ten minutes old kept as it was, the one two hours old removed — dated by
    its modification time, as a folder without a state is, whatever a state of mode 000 would say were it read. Its INFO
    line says so: ``jobs_interrupted`` 1, ``jobs_expired`` 2, every other count 0. Red until the cure for
    ``NOT_AN_OBJECT`` (``AttributeError`` from ``BackupJob.from_json``), ``a-folder`` (``IsADirectoryError``) and
    ``mode-000`` (``PermissionError``): ``end_interrupted_jobs`` raises, «A cleanup of backup leftovers failed» is logged
    with ``part`` ``jobs``, and ``remove_expired_jobs`` never runs. Guards, green today: ``no-state-file`` and
    ``ALREADY_NO_STATE``."""
    print_section(f"(h) B-50 An unreadable job state, {how}: the sweep")
    root = data_root(tmp_path)
    job, folder = running_job(root)
    _expired_job, expired = finished_job(root, ended=LONG_AGO)
    _recent_job, recent = finished_job(root, ended=RECENTLY)
    young = unreadable_job_folder(root, how, mode_000, age=RECENTLY)
    old = unreadable_job_folder(root, how, mode_000, age=LONG_AGO)
    free_run_lock(root)
    kept, young_before = cli_secure.entries(recent), as_left(young)
    started = datetime.now(UTC)
    with apply_cases.logs(LEFTOVERS) as events:
        sweep(root)
    errors = logged_at(events, ERROR_LEVELS)
    assert errors == [], f"an unreadable job state is no state: the jobs part does not fail: {errors}"
    assert_ended_interrupted(job, folder, started, datetime.now(UTC))
    assert not os.path.lexists(expired), "the job that ended two hours ago is removed, with its archive"
    assert cli_secure.entries(recent) == kept, "the job that ended ten minutes ago is kept as it was"
    assert as_left(young) == young_before, "the unreadable folder last modified ten minutes ago is kept as it was"
    assert not os.path.lexists(old), "the unreadable folder last modified two hours ago is removed: its modification time dates it"
    counts = summary_counts(events)
    assert counts == {**dict.fromkeys(COUNTS, 0), "jobs_interrupted": 1, "jobs_expired": 2}, f"the sweep says what it did, and nothing else: {counts}"
    print_success(f"{how}: no error; 1 job ended, the expired job and the unreadable folder two hours old removed")


# =============================================================================
# (i) B-53, B-54, B-55: one reader of the check states; a transient error is no «no check»; old unreadable states pruned
# =============================================================================
#
# The coordinator, 20/10 10:10 (``b53-contract.md``). B-55: the restore follows the jobs' rule of B-50 — a folder, a file
# the server may not read and a content that is no check's state are «no check»; any other ``OSError``, a transient one
# (EIO), goes through: an error the tab retries, never a check forgotten. B-53: a check's state is read through
# ``paths.read_regular_file``, never through a link nor waiting on a FIFO, its descriptor always closed; a date without a
# time zone is a content that is no check's state. B-54: while no check runs, ``prune`` also removes from ``checks/`` the
# ``<id>.json`` and ``<id>.json.part`` no readable check records, older than ``STAGE_LIFETIME`` by their own modification
# time, but the protected stage's; in silence. Point 7 (10:39): the jobs' reader goes through the same helper, so a FIFO
# in place of a job's ``state.json`` is a state no reader can take, never one the start of the server waits on. Each
# list and each test says which of its rows are red until the cure.

#: Older than a check is kept, by an hour's margin: what B-54 removes when no readable check records it.
PAST_LIFETIME = STAGE_LIFETIME + timedelta(hours=1)
#: Seconds a call that reads check states may take before it is said to wait: one that waits on nothing ends in
#: milliseconds, on a loaded machine too. A red run waits this long once per case, then lets its reader go.
READ_DEADLINE_S = 10
#: Seconds between two attempts to let a waiting reader go, and how long the attempts go on at most.
RELEASE_POLL_S = 0.05
RELEASE_DEADLINE_S = 30
#: (i-2) The shapes a state's place may take beside those of (h). A link, to a valid state of that very id or to nothing:
#: guards, ``O_NOFOLLOW`` already refuses both. A FIFO: red, the read waits for a writer forever today. A done check whose
#: ``created_at``, or whose ``finished_at``, has no time zone: red, it is read as a check today.
LINK_SHAPES = [pytest.param("link-to-a-check", id="link-to-a-check"), pytest.param("dangling-link", id="dangling-link")]
FIFO_SHAPE = [pytest.param("fifo", id="fifo", marks=[archive_cases.needs_fifo, archive_cases.needs_dev_fd])]
NAIVE_SHAPES = [pytest.param(f"naive-{key}", id=f"naive-{key}") for key in ("created_at", "finished_at")]
NEW_SHAPES = [*LINK_SHAPES, *FIFO_SHAPE, *NAIVE_SHAPES]
#: (i-3) Every unreadable entry B-54 ages: the shapes of (h) and of (i-2), and a half-written ``<id>.json.part``.
OLD_SHAPES = [*CHECK_STATES, *NEW_SHAPES, pytest.param("half-written-part", id="half-written-part")]
#: (i-3) What ``checks/`` may hold that is no check's state nor one being written: never removed, however old.
OTHER_NAMES = ("notes.txt", "abc.json", "{id}.yaml")


@dataclass(frozen=True)
class Outcome:
    """What a call given a deadline did: whether it ended in time, then what it answered or raised (once let go, when it
    did not end in time)."""

    in_time: bool
    value: Any = None
    raised: Exception | None = None


def let_readers_go(fifos: tuple[Path, ...], thread: threading.Thread) -> None:
    """Let the readers waiting on any of ``fifos`` go, one after the other, until ``thread`` ends (``RELEASE_DEADLINE_S``
    at most): a writer opened without waiting (``O_NONBLOCK``) completes a reader's open, and its close at once ends the
    reader's read (end of file). ``ENXIO``: no reader has that FIFO open, not yet or no longer; ``ENOENT``: it is gone."""
    deadline = time.monotonic() + RELEASE_DEADLINE_S
    while thread.is_alive() and time.monotonic() < deadline:
        for fifo in fifos:
            try:
                os.close(os.open(fifo, os.O_WRONLY | os.O_NONBLOCK))
            except OSError as exc:
                if exc.errno not in (errno.ENXIO, errno.ENOENT):
                    raise
        thread.join(RELEASE_POLL_S)


def within_deadline(call: Callable[[], Any], *, fifos: tuple[Path, ...] = ()) -> Outcome:
    """``call`` in a thread of its own, given ``READ_DEADLINE_S`` to end: whether it did, then what it answered or raised.
    Before this returns, the readers left waiting on ``fifos`` are let go (``let_readers_go``), so that a red run never
    hangs the suite; the thread is a daemon all the same."""
    ended: dict[str, Any] = {}

    def run() -> None:
        try:
            ended["value"] = call()
        except Exception as exc:
            ended["raised"] = exc

    thread = threading.Thread(target=run, name="b53-check-reader", daemon=True)
    thread.start()
    try:
        thread.join(READ_DEADLINE_S)
        in_time = not thread.is_alive()
    finally:
        if fifos:
            let_readers_go(fifos, thread)
    return Outcome(in_time=in_time, value=ended.get("value"), raised=ended.get("raised"))


def fifos_of(how: str, entry: Path) -> tuple[Path, ...]:
    """``entry`` when the row is the FIFO's: the FIFO a waiting reader must be let go from; none otherwise."""
    return (entry,) if how == "fifo" else ()


def closed_descriptors_on(path: Path) -> list[int]:
    """The descriptors of this process left open on ``path`` (``descriptors_on``, by its device and inode), closed: a red
    run carries none into the tests that follow."""
    left_open = archive_cases.descriptors_on(path)
    for fd in left_open:
        os.close(fd)
    return left_open


def said_of(events: list[dict[str, Any]], stage_id: str) -> list[dict[str, Any]]:
    """The events that name ``stage_id``, in any field: what was said of that state."""
    return [event for event in events if stage_id in repr(event)]


def raised_by(call: Callable[[], Any]) -> Exception | None:
    """What ``call`` raised; ``None`` when it returned."""
    try:
        call()
    except Exception as exc:
        return exc
    return None


def the_eio(raised: Exception | None) -> bool:
    """Whether ``raised`` is the transient error the tests inject: an ``OSError``, errno EIO."""
    return isinstance(raised, OSError) and raised.errno == errno.EIO


def what_it_did(raised: Exception | None) -> str:
    return "it returned" if raised is None else f"it raised {raised!r}"


def refused_open(path: Path, error: int, real: Callable[..., int]) -> Callable[..., int]:
    """``os.open`` refusing ``path`` with ``error``, as a file system refuses a file it cannot read now, the real one for
    every other path: matched by its real path, or by its name when relative to a folder's descriptor (``refused_for``
    of ``test_backup_cli_restore.py``)."""
    wanted = os.path.realpath(path)

    def refusing(target: Any, *args: Any, dir_fd: int | None = None, **kwargs: Any) -> int:
        name = os.fsdecode(target)
        if (dir_fd is None and os.path.realpath(name) == wanted) or (dir_fd is not None and name == path.name):
            raise OSError(error, os.strerror(error), name)
        return real(target, *args, dir_fd=dir_fd, **kwargs)

    return refusing


def refuse_open(patch: pytest.MonkeyPatch, path: Path, error: int) -> None:
    """The global ``os.open`` made to refuse ``path`` with ``error`` while ``patch`` lasts, the file on disk as it was.
    Checked: the precondition that whoever opens it meets that error."""
    patch.setattr(os, "open", refused_open(path, error, os.open))
    try:
        os.close(os.open(path, os.O_RDONLY))
    except OSError as exc:
        assert exc.errno == error, f"precondition: os.open refuses {path.name} with {errno.errorcode[error]}, not {exc!r}"
    else:
        pytest.fail(f"precondition: os.open must refuse {path.name} with {errno.errorcode[error]}")


def by_read_check(root: Path, stage_id: str) -> object:
    """``read_check`` of the state's id: what the routes call."""
    return restore_jobs.read_check(stage_id, data_dir=root)


def by_checks(root: Path, stage_id: str) -> object:
    """``restore_jobs._checks``: every check at once, as ``prune``, an upload that finishes and a check's start read them."""
    return restore_jobs._checks(root)


def by_prune(root: Path, stage_id: str) -> object:
    """``restore_jobs.prune``: at every check's start and at every start of the server."""
    return prune(root)


#: The readers of a check's state: by its id, every check at once, and ``prune``.
READERS = [pytest.param(by_read_check, id="read_check"), pytest.param(by_checks, id="_checks"), pytest.param(by_prune, id="prune")]


# -----------------------------------------------------------------------------
# (i-1) B-55 A transient error is no «no check»
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class RefusedBeside:
    """``.restore/`` with two checks, each with its copy: one that ended ten minutes ago, whose state the tests make the
    file system refuse (``refused``); one that ended 25 hours ago, which ``prune`` removes (``old``)."""

    refused: RestoreCheck
    old: RestoreCheck


def refused_beside_old(root: Path) -> RefusedBeside:
    """``RefusedBeside`` in ``root``, the lock of the checks there and free. Checked: the state to refuse is a valid
    check's, read back as written."""
    restore_folders(root)
    refused_id, old_id = new_stage_id(), new_stage_id()
    stage_holding(root, refused_id, archive=None, report=True)
    refused = recorded_check(root, refused_id, new_stage_id(), status="done")
    stage_holding(root, old_id, archive=None, report=True)
    old = recorded_check(root, old_id, new_stage_id(), status="done", ended_ago=timedelta(hours=25))
    assert restore_jobs.read_check(refused_id, data_dir=root) == refused, "precondition: the state to refuse is a valid check's, read back as written"
    return RefusedBeside(refused=refused, old=old)


@pytest.mark.parametrize("reader", READERS)
def test_a_transient_error_on_a_check_state_goes_through_never_taken_for_no_check(tmp_path, monkeypatch, reader):
    """(i-1) B-55. The file system refuses a valid check's state with EIO, as a failing disk or a network file system
    does for a while: ``read_check`` of its id, ``_checks`` and ``prune`` raise that very error — the routes' 500, which
    the tab retries —, never «no check», which would forget a check that may run; ``prune`` removes nothing, not even the
    check that ended 25 hours ago beside it: nothing in ``.restore/`` written or removed. Readable again, the check
    answers as it was, and ``prune`` then removes the old one (the barrier: there was work it did not do). Red until the
    cure, every row: today ``_read_state`` takes any ``OSError`` for «no check» — ``read_check`` raises
    ``CheckNotFoundError``, ``_checks`` answers the old check alone, ``prune`` answers 0 and removes the old check."""
    print_section(f"(i-1) B-55 EIO on a check state: {reader.__name__}")
    root = data_root(tmp_path)
    world = refused_beside_old(root)
    before = as_left(restore_dir(root))
    with monkeypatch.context() as patch:
        refuse_open(patch, check_state_path(root, world.refused.stage_id), errno.EIO)
        raised = raised_by(lambda: reader(root, world.refused.stage_id))
    after = as_left(restore_dir(root))
    assert the_eio(raised), f"{reader.__name__}: the EIO it met goes through, an error the tab retries, never «no check»: {what_it_did(raised)}"
    assert after == before, f"nothing in .restore/ is written or removed: {cli_secure.differences(before, after)}"
    again = restore_jobs.read_check(world.refused.stage_id, data_dir=root)
    assert again == world.refused, f"readable again, the check answers as it was: {again}"
    answer, old = prune(root), (check_state(root, world.old.stage_id), os.path.lexists(stage_dir(root, world.old.stage_id)))
    assert (answer, old, stage_dir(root, world.refused.stage_id).is_dir()) == (0, (None, False), True), f"barrier: readable again, prune removes the check that ended 25 hours ago with its copy, and keeps the other: {answer}, {old}"
    print_success(f"{reader.__name__}: EIO raised, nothing touched; readable again, as it was")


def test_a_check_does_not_start_past_a_transient_error_on_a_check_state(tmp_path, monkeypatch):
    """(i-1) B-55. A check's start prunes first: the file system refusing a valid check's state with EIO, the start
    raises that error, and nothing starts — no thread, no state written, the lock of the checks free, the upload kept
    for the next try, nothing in ``.restore/`` written or removed. Red until the cure: today ``prune`` takes the state for
    no check, removes the check that ended 25 hours ago, and the check starts — here, inline, to its end
    (``not_a_backup``), its upload removed."""
    root = data_root(tmp_path)
    world = refused_beside_old(root)
    upload_id = new_stage_id()
    upload = upload_path(root, upload_id)
    upload.write_bytes(NOT_A_BACKUP)
    upload.chmod(0o600)
    threads = InlineThreads()
    monkeypatch.setattr(restore_jobs, "threading", threads)
    before = as_left(restore_dir(root))
    with monkeypatch.context() as patch:
        refuse_open(patch, check_state_path(root, world.refused.stage_id), errno.EIO)
        raised = raised_by(lambda: restore_jobs.start_check(upload_id, data_dir=root))
    after = as_left(restore_dir(root))
    assert the_eio(raised), f"the start raises the EIO its prune met, never past it: {what_it_did(raised)}"
    assert (threads.started, upload.is_file(), cases.lock_is_free(root)) == ([], True, True), f"nothing starts, the upload is kept, the lock of the checks is free: {threads.started}"
    assert after == before, f"nothing in .restore/ is written or removed: {cli_secure.differences(before, after)}"
    print_success("start_check: EIO raised, nothing started, the upload kept")


def test_an_upload_that_finishes_past_a_transient_error_on_a_check_state_removes_no_upload(tmp_path, monkeypatch):
    """(i-1) B-55. An upload that finishes drops the uploads it replaces but those a running check reads, which it learns
    from every check's state. A check runs (its lock held) on an upload, and the file system refuses its state with EIO:
    the end of the next upload raises that error, and no upload is removed — neither the one the running check reads nor
    the one before. Red until the cure: today the running check is taken for no check, ``finish`` returns, and both
    uploads are removed, the running check's included."""
    root = data_root(tmp_path)
    restore_folders(root)
    read = an_upload(root, new_stage_id())
    refused_id = new_stage_id()
    recorded_check(root, refused_id, read.name)
    read_as_running(root, refused_id)
    earlier = an_upload(root, new_stage_id())
    holder = cases.hold_the_lock(root)
    try:
        with monkeypatch.context() as patch:
            refuse_open(patch, check_state_path(root, refused_id), errno.EIO)
            writer = restore_jobs.UploadWriter(root, max_bytes=None, declared=None)
            writer.write(CLEAR)
            raised = raised_by(writer.finish)
    finally:
        holder.release()
    assert the_eio(raised), f"the end of the upload raises the EIO it met reading the checks, never past it: {what_it_did(raised)}"
    assert (read.is_file(), earlier.is_file()) == (True, True), "no upload is removed: neither the one the running check reads nor the one before"
    print_success("UploadWriter.finish: EIO raised, no upload removed")


def test_the_startup_sweep_logs_a_transient_error_on_a_check_state_and_goes_on(tmp_path, monkeypatch):
    """(i-1) B-55. Every part of the sweep has work (``everything_left``), and the file system refuses a valid check's
    state with EIO: one error is logged, «A cleanup of backup leftovers failed», for the part ``restore``, naming
    ``OSError``; that part's work is left undone — its ``prune`` raised before it ended any check, and the decrypted
    archive it removes after stays —; the two other parts do theirs. Readable again, the check answers as it was. Red
    until the cure: today no error is logged and the restore part does its whole work, past the state it could not
    read."""
    leftovers = leftovers_module()
    root = data_root(tmp_path)
    world = everything_left(root, tmp_path)
    refused_id = new_stage_id()
    refused = recorded_check(root, refused_id, new_stage_id(), status="done")
    assert restore_jobs.read_check(refused_id, data_dir=root) == refused, "precondition: the state to refuse is a valid check's, read back as written"
    with monkeypatch.context() as patch:
        refuse_open(patch, check_state_path(root, refused_id), errno.EIO)
        with apply_cases.logs(LEFTOVERS) as events:
            outcome = leftovers.sweep_backup_leftovers(root)
    assert outcome is None, f"the sweep answers None, whatever failed: {outcome!r}"
    failures = [event for event in events if event.get("event") == FAILURE]
    assert [(event.get("log_level"), event.get("part")) for event in failures] == [("error", "restore")], f"one error, for the part restore: {apply_cases.logged(events)}"
    assert "OSError" in [value for key, value in failures[0].items() if key not in ("event", "log_level", "part")], f"the error names the exception's type, OSError: {failures[0]}"
    assert work_done(world) == {"restore": False, "decrypt_folders": True, "jobs": True}, f"the two other parts do their whole work, restore none: {work_done(world)}"
    assert work_untouched(world)["restore"], "the restore part's work is left as it was: the checks still recorded running, the decrypted archive there"
    assert restore_jobs.read_check(refused_id, data_dir=root) == refused, "readable again, the check answers as it was"
    print_success("restore: OSError logged once; decrypt_folders and jobs done")


# -----------------------------------------------------------------------------
# (i-2) B-53 A link, a FIFO, a date without a time zone: no check, in silence
# -----------------------------------------------------------------------------


def assert_no_check(reader: Callable[..., object], outcome: Outcome, root: Path, world: ChecksBeside, unreadable: dict[str, tuple[int, int, int, int]]) -> None:
    """What ``reader`` answers beside a check state that is no check's: ``read_check`` of its id ``CheckNotFoundError``
    (the routes' 404 ``restore_stage_not_found``); ``_checks`` the three checks it reads; ``prune`` 1, its usual work done,
    the state left as it was (just made: B-54 leaves it)."""
    if reader is by_read_check:
        assert isinstance(outcome.raised, restore_jobs.CheckNotFoundError), f"read_check of its id: no check, not {outcome}"
        return
    assert outcome.raised is None, f"{reader.__name__} reads past it, and raises nothing: {outcome.raised!r}"
    if reader is by_checks:
        found = {check.stage_id: check.status for check in outcome.value}
        expected = {world.old.stage_id: "done", world.recent.stage_id: "done", world.interrupted.stage_id: "running"}
        assert found == expected, f"_checks answers the three checks it reads, and skips the state: {found}"
        return
    assert outcome.value == 1, f"prune ends the check a stopped server left running, and answers 1, not {outcome.value!r}"
    assert_prune_did_its_work(root, world, unreadable)


@pytest.mark.parametrize("reader", READERS)
@pytest.mark.parametrize("how", NEW_SHAPES)
def test_a_link_a_fifo_or_a_date_without_time_zone_as_a_check_state_is_no_check_in_silence(tmp_path, mode_000, how, reader):
    """(i-2) B-53, B-55. In a check state's place: a link — to a valid state of that very id elsewhere, which would answer
    a check were it followed, or to nothing —, a FIFO, a done check's state one of whose dates has no time zone (its
    dates say it ended 25 hours ago: read as a check, ``prune`` would remove it). Each is no check, through
    ``read_check``, ``_checks`` and ``prune``, which return within ``READ_DEADLINE_S``; nothing is said of it, nothing
    logged as a warning; the link's target stays as it was; no descriptor is left open on the FIFO. Guards, green today:
    the links (``O_NOFOLLOW``). Red until the cure: the FIFO, every reader waits on it for a writer (let go, past the
    deadline, by the test); the dates without a time zone — ``read_check`` returns the check, ``_checks`` lists it,
    ``prune`` raises ``TypeError`` comparing a naive ``finished_at`` with an aware time, or, the ``created_at`` naive,
    removes the check by what its ``finished_at`` says and logs it."""
    print_section(f"(i-2) B-53 {how} as a check state: {reader.__name__}")
    root = data_root(tmp_path)
    world = checks_beside(root, how, mode_000, says_ended=PAST_LIFETIME)
    entry = check_state_path(root, world.unreadable)
    unreadable = as_left(entry)
    outside = cli_secure.entries(outside_checks(root)) if outside_checks(root).is_dir() else None
    fifos = fifos_of(how, entry)
    with apply_cases.logs(restore_jobs.__name__) as events:
        outcome = within_deadline(lambda: reader(root, world.unreadable), fifos=fifos)
    left_open = [fd for fifo in fifos for fd in closed_descriptors_on(fifo)]
    assert outcome.in_time, f"{reader.__name__} returns within {READ_DEADLINE_S} s: it waited on the {how} (then let go: {outcome})"
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the FIFO: {left_open}"
    assert_no_check(reader, outcome, root, world, unreadable)
    assert outside is None or cli_secure.entries(outside_checks(root)) == outside, "the link's target stays as it was"
    said = said_of(events, world.unreadable) + logged_at(events, WARNED_LEVELS)
    assert said == [], f"no check, in silence: {said}"
    print_success(f"{how}, {reader.__name__}: no check, in time, nothing said")


# -----------------------------------------------------------------------------
# (i-3) B-54 Old unreadable states pruned while no check runs
# -----------------------------------------------------------------------------


def entry_of(root: Path, how: str, stage_id: str) -> Path:
    """The entry ``unreadable_check_state`` made in ``checks/``: ``<id>.json``, or ``<id>.json.part``."""
    path = check_state_path(root, stage_id)
    return path.with_name(path.name + PARTIAL_STATE) if how == "half-written-part" else path


def made_old(entry: Path) -> Path:
    """``entry`` last modified ``PAST_LIFETIME`` ago, by its own modification time — a link's own, never its target's; a
    folder with a file put in it first, both aged, so that it is removed with what it holds. Checked."""
    seconds = PAST_LIFETIME.total_seconds()
    if is_plain_dir(entry):
        inside = entry / "left-inside.bin"
        inside.write_bytes(CLEAR)
        cli_secure.aged(inside, seconds)
    cli_secure.aged(entry, seconds)
    age = time.time() - entry.lstat().st_mtime
    assert age > STAGE_LIFETIME.total_seconds(), f"precondition: {entry.name} last modified longer ago than STAGE_LIFETIME, by its own time: {age:.0f} s"
    return entry


def other_names_made_old(root: Path) -> list[Path]:
    """The ``OTHER_NAMES`` in ``checks/`` (``{id}`` a stage id), files of a few bytes (0600), each ``PAST_LIFETIME`` old."""
    made = []
    for name in OTHER_NAMES:
        path = checks_dir(root) / name.format(id=new_stage_id())
        path.write_bytes(b"not a check's state")
        path.chmod(0o600)
        made.append(cli_secure.aged(path, PAST_LIFETIME.total_seconds()))
    return made


@pytest.mark.parametrize("how", OLD_SHAPES)
def test_prune_removes_an_unreadable_check_state_older_than_its_lifetime_while_no_check_runs(tmp_path, mode_000, how):
    """(i-3) B-54. While no check runs, an entry of ``checks/`` no readable check records — ``<id>.json`` or
    ``<id>.json.part`` — older than ``STAGE_LIFETIME`` by its own modification time is removed by ``prune``: a file
    whatever its content or mode, a folder with its content, a link (never its target), a FIFO; its content never read
    for its age (a ``naive-*`` one says it ended ten minutes ago). In silence: nothing said of it, no warning. ``prune``
    answers 1 and does its usual work on the readable checks; the old names that are no state's stay as they were. Red
    until the cure, every row: today ``prune`` leaves every unreadable entry forever — and ``naive-finished_at`` raises
    ``TypeError``, ``fifo`` waits on its FIFO, ``naive-created_at`` is kept as the recent check its dates say."""
    print_section(f"(i-3) B-54 An unreadable check state older than STAGE_LIFETIME, {how}: prune")
    root = data_root(tmp_path)
    world = checks_beside(root, how, mode_000)
    entry = made_old(entry_of(root, how, world.unreadable))
    others = {path: as_left(path) for path in other_names_made_old(root)}
    outside = cli_secure.entries(outside_checks(root)) if outside_checks(root).is_dir() else None
    with apply_cases.logs(restore_jobs.__name__) as events:
        outcome = within_deadline(lambda: prune(root), fifos=fifos_of(how, entry))
    assert outcome.in_time, f"prune returns within {READ_DEADLINE_S} s: it waited on the {how} (then let go: {outcome})"
    assert (outcome.raised, outcome.value) == (None, 1), f"prune works, and answers the check it ended as interrupted: {outcome}"
    assert_prune_did_its_usual_work(root, world)
    assert not os.path.lexists(entry), f"the unreadable {entry.name}, {how}, older than STAGE_LIFETIME, is removed"
    gone = sorted(path.name for path in others if not os.path.lexists(path))
    assert gone == [], f"what is no check's state stays, however old: {gone} removed"
    assert {path: as_left(path) for path in others} == others, "what is no check's state is left as it was"
    assert outside is None or cli_secure.entries(outside_checks(root)) == outside, "a link is removed itself, never its target"
    said = said_of(events, world.unreadable) + logged_at(events, WARNED_LEVELS)
    assert said == [], f"removed in silence: {said}"
    print_success(f"{how}: removed, in silence; prune's usual work done")


#: (i-3) Who keeps an old unreadable state: a check that runs (the lock of the checks held), a restore waiting on the
#: stage of its id (the protected stage).
KEEPERS = [pytest.param("a-check-runs", id="while-a-check-runs"), pytest.param("a-restore-waits", id="a-restore-waits-on-its-stage")]


@pytest.mark.parametrize("how", OLD_SHAPES)
@pytest.mark.parametrize("keeper", KEEPERS)
def test_an_old_unreadable_check_state_stays_while_a_check_runs_or_a_restore_waits_on_its_stage(tmp_path, mode_000, keeper, how):
    """(i-3) B-54. An unreadable entry of ``checks/`` older than ``STAGE_LIFETIME`` stays while a check runs — nothing in
    ``checks/`` is removed then, however old — and when its id is the stage a restore waits on: ``prune`` answers 0,
    returns within ``READ_DEADLINE_S``, ``checks/`` as it was, nothing logged. Guards, green today (``prune`` never
    touches an unreadable entry), but three rows red until the cure for (i-2)'s reasons: ``fifo`` under both keepers (the
    read waits on it), and ``naive-finished_at`` while a check runs (``TypeError``; the protected one is skipped before
    its dates are compared)."""
    root = data_root(tmp_path)
    restore_folders(root)
    stage_id = unreadable_check_state(root, how, mode_000)
    entry = made_old(entry_of(root, how, stage_id))
    if keeper == "a-restore-waits":
        pending_restore(root, stage_id)
    before = as_left(checks_dir(root))
    holder = cases.hold_the_lock(root) if keeper == "a-check-runs" else None
    try:
        with apply_cases.logs(restore_jobs.__name__) as events:
            outcome = within_deadline(lambda: prune(root), fifos=fifos_of(how, entry))
    finally:
        if holder is not None:
            holder.release()
    assert outcome.in_time, f"prune returns within {READ_DEADLINE_S} s: it waited on the {how} (then let go: {outcome})"
    assert (outcome.raised, outcome.value) == (None, 0), f"prune works, and ends no check: {outcome}"
    after = as_left(checks_dir(root))
    assert after == before, f"{keeper}: nothing in checks/ is removed, however old: {cli_secure.differences(before, after)}"
    assert apply_cases.logged(events) == [], f"nothing logged: {apply_cases.logged(events)}"
    print_success(f"{keeper}, {how}: kept")


def test_prune_leaves_what_is_not_a_check_state_in_the_checks_folder_however_old(tmp_path, mode_000):
    """(i-3) B-54. Only ``<id>.json`` and ``<id>.json.part`` with a stage id are a check's state or one being written:
    ``notes.txt``, ``abc.json`` and ``<id>.yaml``, older than ``STAGE_LIFETIME``, stay as they were while ``prune`` does
    its usual work beside them and leaves the state of (h) just made; nothing is said of them. Guard, green today."""
    root = data_root(tmp_path)
    world = checks_beside(root, "empty-file", mode_000)
    unreadable = as_left(check_state_path(root, world.unreadable))
    others = {path: as_left(path) for path in other_names_made_old(root)}
    with apply_cases.logs(restore_jobs.__name__) as events:
        answer = prune(root)
    assert answer == 1, f"prune ends the check a stopped server left running, and answers 1, not {answer!r}"
    assert_prune_did_its_work(root, world, unreadable)
    gone = sorted(path.name for path in others if not os.path.lexists(path))
    assert gone == [], f"what is no check's state stays, however old: {gone} removed"
    assert {path: as_left(path) for path in others} == others, "what is no check's state is left as it was"
    said = [event for event in events if any(path.name in repr(event) for path in others)] + logged_at(events, WARNED_LEVELS)
    assert said == [], f"nothing said of them: {said}"
    print_success(f"{[path.name for path in others]}: kept")


# -----------------------------------------------------------------------------
# (i-4) B-53 The startup sweep beside a FIFO
# -----------------------------------------------------------------------------


@archive_cases.needs_fifo
@archive_cases.needs_dev_fd
def test_the_startup_sweep_returns_in_time_beside_a_fifo_as_a_check_state(tmp_path, mode_000):
    """(i-4) B-53. A FIFO in a check state's place, the sweep at startup: it returns within ``READ_DEADLINE_S``, raises
    nothing, logs neither an error nor a warning, leaves no descriptor open on the FIFO, and does the whole work of its
    ``restore`` part — ``prune``'s (the FIFO, just made, left as it was), then the decrypted archive a killed check left —,
    its INFO line saying so. Red until the cure: today ``prune`` waits on the FIFO for a writer, and with it the start of
    the server (let go, past the deadline, by the test)."""
    print_section("(i-4) B-53 The startup sweep beside a FIFO as a check state")
    root = data_root(tmp_path)
    world = checks_beside(root, "fifo", mode_000)
    stray = stage_holding(root) / STAGE_DECRYPTED_ARCHIVE
    fifo = check_state_path(root, world.unreadable)
    unreadable = as_left(fifo)
    with apply_cases.logs(LEFTOVERS) as events:
        outcome = within_deadline(lambda: sweep(root), fifos=(fifo,))
    left_open = closed_descriptors_on(fifo)
    assert outcome.in_time, f"the sweep returns within {READ_DEADLINE_S} s: it waited on the FIFO (then let go: {outcome})"
    assert outcome.raised is None, f"the sweep raises nothing: {outcome.raised!r}"
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the FIFO: {left_open}"
    warned = logged_at(events, WARNED_LEVELS)
    assert warned == [], f"the restore part does not fail, and nothing is said of the FIFO: {warned}"
    assert_prune_did_its_work(root, world, unreadable)
    assert not os.path.lexists(stray), "the decrypted archive a killed check left in a copy is removed, after prune, in the same part"
    counts = summary_counts(events)
    assert counts == {**dict.fromkeys(COUNTS, 0), "checks_interrupted": 1, "decrypted_archives": 1}, f"the sweep says what it did, and nothing else: {counts}"
    print_success("the sweep returned in time; nothing logged above INFO")


# -----------------------------------------------------------------------------
# (i-5) B-53, point 7: the startup sweep beside a FIFO as a job's state
# -----------------------------------------------------------------------------


@archive_cases.needs_fifo
@archive_cases.needs_dev_fd
def test_the_startup_sweep_returns_in_time_beside_a_fifo_as_a_job_state(tmp_path, mode_000):
    """(i-5) B-53, point 7 of its contract (the coordinator, 10:39: the jobs' reader goes through the same helper). A
    FIFO in place of the ``state.json`` of two job folders, one last modified ten minutes ago, one two hours ago, beside
    the jobs of (h)'s jobs sweep: the sweep returns within ``READ_DEADLINE_S`` and raises nothing; no error logged; the
    jobs part does its usual work — the run a stopped server left running ended ``backup_interrupted``, its state alone
    left; the job that ended two hours ago removed; the one that ended ten minutes ago kept as it was —, and dates the
    folders whose state is a FIFO by their modification time, as any unreadable one: the one ten minutes old kept as it
    was, the one two hours old removed. Its INFO line says so: ``jobs_interrupted`` 1, ``jobs_expired`` 2. No
    descriptor left open on the FIFO that stays. Red until the cure: ``end_interrupted_jobs``, then
    ``remove_expired_jobs``, wait on each FIFO for a writer (``read_text``), and with them the start of the server (let
    go, past the deadline, by the test, one reader after the other)."""
    print_section("(i-5) B-53 The startup sweep beside a FIFO as a job's state")
    root = data_root(tmp_path)
    job, folder = running_job(root)
    _expired_job, expired = finished_job(root, ended=LONG_AGO)
    _recent_job, recent = finished_job(root, ended=RECENTLY)
    young = unreadable_job_folder(root, "fifo", mode_000, age=RECENTLY)
    old = unreadable_job_folder(root, "fifo", mode_000, age=LONG_AGO)
    free_run_lock(root)
    kept, young_before = cli_secure.entries(recent), as_left(young)
    started = datetime.now(UTC)
    with apply_cases.logs(LEFTOVERS) as events:
        outcome = within_deadline(lambda: sweep(root), fifos=(young / STATE_FILE, old / STATE_FILE))
    left_open = closed_descriptors_on(young / STATE_FILE)
    assert outcome.in_time, f"the sweep returns within {READ_DEADLINE_S} s: it waited on a FIFO as a job's state (then let go: {outcome})"
    assert outcome.raised is None, f"the sweep raises nothing: {outcome.raised!r}"
    assert left_open == [], f"{len(left_open)} descriptor(s) left open on the FIFO: {left_open}"
    errors = logged_at(events, ERROR_LEVELS)
    assert errors == [], f"a FIFO as a job's state is no state: the jobs part does not fail: {errors}"
    assert_ended_interrupted(job, folder, started, datetime.now(UTC))
    assert not os.path.lexists(expired), "the job that ended two hours ago is removed, with its archive"
    assert cli_secure.entries(recent) == kept, "the job that ended ten minutes ago is kept as it was"
    assert as_left(young) == young_before, "the folder whose state is a FIFO, last modified ten minutes ago, is kept as it was"
    assert not os.path.lexists(old), "the folder whose state is a FIFO, last modified two hours ago, is removed: its modification time dates it"
    counts = summary_counts(events)
    assert counts == {**dict.fromkeys(COUNTS, 0), "jobs_interrupted": 1, "jobs_expired": 2}, f"the sweep says what it did, and nothing else: {counts}"
    print_success("the sweep returned in time; 1 job ended, the expired job and the FIFO folder two hours old removed")
