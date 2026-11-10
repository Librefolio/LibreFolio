"""
Instance backup, the kept backups and their clean-up (workstream B, lot FB-24, contract ``B6r-fb24-backend-interface``
§1 and §3).

Under test: ``backend/app/services/platform/instance_backup/paths.py`` (``kept_folder_name``, ``is_kept_name``,
``kept_dir``) and ``retention.py`` (``list_kept``, ``plan_cleanup``, ``apply_cleanup``). The jobs' side of the same lot
(the move into ``backups/``) is ``test_backup_jobs.py``'s; the policy read from the settings is
``test_backup_cleanup_settings.py``'s.

(a) The names. ``kept_folder_name(created_at, origin, job_id)`` is ``librefolio-backup-YYYYMMDD-HHMMSS-<origin>-<8 first
    digits of the job id>``, the date in UTC whatever the zone of ``created_at``; ``is_kept_name`` accepts that and only
    that (the whole string, every origin of ``BackupOrigin``, ``pre-restore`` included); ``kept_dir(data_dir, name)`` is
    ``backups/<name>`` and refuses, with ``ValueError``, a name that is not a kept name.
(b) ``list_kept(data_dir)``: the backups kept in ``backups/``, the most recent first (by ``job.created_at``), each with its
    folder and the size of its archive on disk. Only a folder with a valid name that is no link, whose ``state.json``
    reads, says ``done`` and has the job id the name ends with, and whose archive is a regular file (no link). Never listed:
    what is in ``.jobs/`` (a running job, a finished one), the ``.decrypt-*`` folders, the loose
    ``librefolio-backup-*.zip`` files of the old command line, a file or a link with a kept name, an unreadable state, a
    failed one, a missing archive. ``backups/`` missing, a link or a file: nothing listed.
(c) ``plan_cleanup(kept, policy, now)``: what to remove, and why (``"age"`` or ``"space"``). Never the most recent backup,
    so one backup is never removed; a policy of 0 and 0 removes nothing. The age first: older than ``max_days`` days,
    against the ``now`` given (a backup exactly ``max_days`` old stays). Then the space, on the backups that stay: while
    their archives add up to more than ``max_mb`` MiB the oldest goes, until it fits or one is left (exactly ``max_mb``
    MiB fits). Whatever the order of ``kept``.
(d) ``apply_cleanup(data_dir, policy, now=...)``: removes, with ``shutil.rmtree``, the folders ``list_kept`` names and the
    plan picks, and answers the job ids it removed, as a tuple; it never raises (a policy that cannot be read, a listing
    that fails, a folder that cannot be removed: the other folders still go). Nothing but a kept backup is touched, however
    old: no running job, no loose zip, no link and the folder it points to, no unreadable state, no missing archive. One
    INFO line per removal, with ``job_id``, ``reason``, ``size_bytes`` and ``origin``, and never a file name nor a path.
    Without a ``policy`` it reads ``read_policy()``.

Pure: every data directory is in ``tmp_path`` and every call is given its ``data_dir`` and, but for one case, its policy;
the clock is the ``now`` given. A backup is a folder with a ``state.json`` and a sparse archive of the size the case
needs. The product is looked up when a test needs it (``retention_module``, ``new_attr``), so that its absence is that
test's red, not a collection error of the whole file; and the backups are planted with this module's own
``kept_name``/``plant_kept``, the contract's string written out, never with the product's helpers, so that a case of
``list_kept`` is red because of ``list_kept``. No lane database, no server, no network.
"""

from __future__ import annotations

import importlib
import os
import re
import shutil
import stat
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, get_args

import pytest
from structlog.testing import capture_logs

from backend.app.logging_config import get_logger
from backend.app.services.platform.instance_backup.jobs import BackupJob, archive_name
from backend.app.services.platform.instance_backup.manifest import BackupOrigin
from backend.app.services.platform.instance_backup.paths import STATE_FILE, backups_dir, ensure_private_dir, job_dir
from backend.test_scripts.test_utils import print_section, print_success

PACKAGE = "backend.app.services.platform.instance_backup"
RETENTION = f"{PACKAGE}.retention"
PATHS = f"{PACKAGE}.paths"
ORIGINS = get_args(BackupOrigin)
MIB = 1024 * 1024
DAY = timedelta(days=1)
#: Far from the real clock: a clean-up reading the wall clock instead of the ``now`` given is wrong by years.
NOW = datetime(2030, 6, 15, 12, 0, tzinfo=UTC)
#: The name of a kept backup, as the contract writes it.
KEPT_NAME = re.compile(r"librefolio-backup-\d{8}-\d{6}-[a-z-]+-[0-9a-f]{8}")
LOG_BARRIER = "fb24 retention test: a canary through a logger of retention's name"
POSIX = os.name != "nt"
AS_ROOT = POSIX and os.geteuid() == 0
needs_symlinks = pytest.mark.skipif(not POSIX, reason="symbolic links need a privilege on Windows")


# =============================================================================
# The product, looked up when a test needs it
# =============================================================================


def retention_module() -> ModuleType:
    """``instance_backup.retention`` (§3), imported by the test that needs it: its absence is that test's red."""
    try:
        return importlib.import_module(RETENTION)
    except ModuleNotFoundError as exc:
        if exc.name != RETENTION:
            raise
        pytest.fail(f"[new] {RETENTION} does not exist yet: lot FB-24 brings it (§3)", pytrace=False)


def paths_module() -> ModuleType:
    return importlib.import_module(PATHS)


def new_attr(module: ModuleType, name: str) -> Any:
    """``module.<name>``, a name lot FB-24 adds, read when the test needs it."""
    found = getattr(module, name, None)
    if found is None:
        pytest.fail(f"[new] {module.__name__}.{name} does not exist yet: lot FB-24 adds it", pytrace=False)
    return found


def cleanup_policy(max_mb: int = 0, max_days: int = 0) -> Any:
    return new_attr(retention_module(), "CleanupPolicy")(max_mb=max_mb, max_days=max_days)


def list_kept(data_dir: Path) -> list[Any]:
    return new_attr(retention_module(), "list_kept")(data_dir)


def plan_cleanup(kept: list[Any], policy: Any, now: datetime = NOW) -> list[tuple[Any, str]]:
    return new_attr(retention_module(), "plan_cleanup")(kept, policy, now)


def apply_cleanup(data_dir: Path, policy: Any | None = None, **kwargs: Any) -> tuple[str, ...]:
    """What ``apply_cleanup`` answers; a call that raises is a failure of the test that makes it (it never raises)."""
    function = new_attr(retention_module(), "apply_cleanup")
    return function(data_dir, policy, **kwargs) if policy is not None else function(data_dir, **kwargs)


# =============================================================================
# Data directories and backups, planted by hand
# =============================================================================


def data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    root.mkdir(mode=0o700)
    return root


def kept_name(created: datetime, origin: str, job_id: str) -> str:
    """The name of a kept backup's folder, the contract's string (§1), the date in UTC."""
    return f"librefolio-backup-{created.astimezone(UTC):%Y%m%d-%H%M%S}-{origin}-{job_id[:8]}"


@dataclass(frozen=True)
class Planted:
    """A kept backup written by hand: its job (as its state records it), its folder and its archive."""

    job: BackupJob
    folder: Path
    archive: Path


def a_job(created: datetime, *, origin: str = "ui", size: int = 1000, job_id: str | None = None, status: str = "done") -> BackupJob:
    return BackupJob(
        job_id=job_id or uuid.uuid4().hex,
        origin=origin,
        status=status,
        phase=None,
        done_bytes=size,
        total_bytes=size,
        created_at=created,
        finished_at=created + timedelta(minutes=1),
        file_name=archive_name(created),
        file_size=size,
        file_sha256="0" * 64,
    )


def plant_kept(
    data_dir: Path,
    *,
    created: datetime,
    origin: str = "ui",
    size: int = 1000,
    job_id: str | None = None,
    name: str | None = None,
    status: str = "done",
    with_state: bool = True,
    with_archive: bool = True,
) -> Planted:
    """A kept backup in ``backups/``: ``backups/<name>/state.json`` and an archive of ``size`` bytes (a sparse file)."""
    job = a_job(created, origin=origin, size=size, job_id=job_id, status=status)
    folder = ensure_private_dir(backups_dir(data_dir) / (name or kept_name(created, origin, job.job_id)), data_dir)
    if with_state:
        (folder / STATE_FILE).write_text(job.to_json(), encoding="utf-8")
    archive = folder / job.file_name
    if with_archive:
        with archive.open("wb") as handle:
            handle.truncate(size)
    return Planted(job=job, folder=folder, archive=archive)


def kept_folders(data_dir: Path) -> list[str]:
    """The kept backups of ``backups/`` by name (what the contract's name says), whatever their content."""
    folder = backups_dir(data_dir)
    return sorted(path.name for path in folder.iterdir() if KEPT_NAME.fullmatch(path.name)) if folder.is_dir() else []


def snapshot(root: Path) -> dict[str, tuple]:
    """Everything below ``root``: kind and size, a link by its target; read without following a link."""
    seen: dict[str, tuple] = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            seen[str(path.relative_to(root))] = ("link", os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):
            seen[str(path.relative_to(root))] = ("dir",)
        else:
            seen[str(path.relative_to(root))] = ("file", info.st_size)
    return seen


@dataclass(frozen=True)
class FakeKept:
    """A ``KeptBackup`` for ``plan_cleanup``, which reads no disk: built by the product's own class, with a folder that is
    nowhere."""

    job: BackupJob
    folder: Path
    size: int


def in_memory(created: datetime, size: int, *, origin: str = "ui") -> Any:
    job = a_job(created, origin=origin, size=size)
    return new_attr(retention_module(), "KeptBackup")(job=job, folder=Path("/nowhere") / kept_name(created, origin, job.job_id), size=size)


def plan_of(plan: list[tuple[Any, str]]) -> dict[str, str]:
    """A plan as ``{job id: reason}``: the order of a plan is nobody's business."""
    return {item.job.job_id: reason for item, reason in plan}


# =============================================================================
# (a) the names
# =============================================================================


def test_a_kept_folder_is_named_after_its_time_in_utc_its_origin_and_the_start_of_its_job_id():
    """(a) The contract's example, and a time in another zone: 14:00+02:00 is 12:00 UTC."""
    name = new_attr(paths_module(), "kept_folder_name")
    job_id = "1a2b3c4d" + "0" * 24
    assert name(datetime(2026, 11, 4, 12, 0, 0, tzinfo=UTC), "ui", job_id) == "librefolio-backup-20261104-120000-ui-1a2b3c4d"
    assert name(datetime(2026, 11, 4, 14, 0, 0, tzinfo=timezone(timedelta(hours=2))), "cli", job_id) == "librefolio-backup-20261104-120000-cli-1a2b3c4d"
    print_success("librefolio-backup-20261104-120000-ui-1a2b3c4d")


@pytest.mark.parametrize("origin", ORIGINS)
def test_every_origin_makes_a_kept_name_and_the_name_is_recognised(origin):
    """(a) ``pre-restore`` has a hyphen of its own: the name still reads as one."""
    paths = paths_module()
    name = new_attr(paths, "kept_folder_name")(NOW, origin, uuid.uuid4().hex)
    assert KEPT_NAME.fullmatch(name), f"the name follows the contract's pattern: {name}"
    assert new_attr(paths, "is_kept_name")(name) is True, f"is_kept_name recognises {name}"
    assert name.endswith(f"-{origin}-{name[-8:]}"), f"the origin is in the name: {name}"


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("librefolio-backup-20261104-120000.zip", id="the-archive-name"),
        pytest.param("librefolio-backup-20261104-120000-ui", id="no-id"),
        pytest.param("librefolio-backup-20261104-120000-ui-1a2b3c4", id="7-digits"),
        pytest.param("librefolio-backup-20261104-120000-ui-1a2b3c4d5", id="9-digits"),
        pytest.param("librefolio-backup-20261104-120000-ui-1A2B3C4D", id="uppercase"),
        pytest.param("librefolio-backup-20261104-120000-ui-1a2b3c4g", id="not-hex"),
        pytest.param("librefolio-backup-20261104-120000-ui2-1a2b3c4d", id="digit-in-origin"),
        pytest.param("librefolio-backup-20261104-120000-ui-1a2b3c4d\n", id="trailing-newline"),
        pytest.param("librefolio-backup-20261104-120000-ui-1a2b3c4d.zip", id="suffix"),
        pytest.param("x-librefolio-backup-20261104-120000-ui-1a2b3c4d", id="prefix"),
        pytest.param("librefolio-backup-2026114-120000-ui-1a2b3c4d", id="short-date"),
        pytest.param("librefolio-backup-20261104-12000-ui-1a2b3c4d", id="short-time"),
        pytest.param("../librefolio-backup-20261104-120000-ui-1a2b3c4d", id="parent"),
        pytest.param(".jobs", id="jobs"),
        pytest.param("", id="empty"),
    ],
)
def test_only_the_whole_kept_name_is_a_kept_name(value):
    """(a) ``is_kept_name`` takes the whole string, nothing else: and ``kept_dir`` refuses it with ``ValueError``."""
    paths = paths_module()
    assert new_attr(paths, "is_kept_name")(value) is False, f"{value!r} is no kept name"
    with pytest.raises(ValueError):
        new_attr(paths, "kept_dir")(Path("/srv/librefolio-data"), value)


def test_a_kept_dir_is_a_folder_of_backups_by_its_name():
    """(a) ``kept_dir(data_dir, name)`` is ``backups/<name>``."""
    name = "librefolio-backup-20261104-120000-ui-1a2b3c4d"
    assert new_attr(paths_module(), "kept_dir")(Path("/srv/librefolio-data"), name) == Path("/srv/librefolio-data/backups") / name


# =============================================================================
# (b) list_kept
# =============================================================================


def test_the_kept_backups_are_listed_most_recent_first_with_their_folder_and_the_size_of_their_archive(tmp_path):
    """(b) By ``job.created_at``, not by name nor by the order they were written."""
    print_section("list_kept")
    root = data_root(tmp_path)
    middle = plant_kept(root, created=NOW - 2 * DAY, size=2000, origin="cli")
    newest = plant_kept(root, created=NOW - 1 * DAY, size=1000)
    oldest = plant_kept(root, created=NOW - 3 * DAY, size=3000, origin="panel")
    listed = list_kept(root)
    assert [item.job.job_id for item in listed] == [newest.job.job_id, middle.job.job_id, oldest.job.job_id], f"the most recent first: {[item.job.job_id for item in listed]}"
    assert [(item.job, item.folder, item.size) for item in listed] == [(planted.job, planted.folder, planted.job.file_size) for planted in (newest, middle, oldest)], "each with its job as the state records it, its folder and the size of its archive"
    print_success("3 listed, newest first")


def test_the_size_is_that_of_the_archive_on_disk(tmp_path):
    """(b) The size comes from the file, not from what the state says."""
    root = data_root(tmp_path)
    planted = plant_kept(root, created=NOW - DAY, size=4096)
    with planted.archive.open("wb") as handle:
        handle.truncate(5000)
    [item] = list_kept(root)
    assert item.size == 5000, f"the archive on disk is 5000 bytes: {item.size}"


def good(root: Path) -> Planted:
    """The one backup every stranger below is listed beside: the proof that the listing works."""
    return plant_kept(root, created=NOW - DAY, size=500)


def plant_job_in_jobs_running(root: Path, tmp_path: Path, created: datetime) -> None:
    job = a_job(created, status="running")
    folder = ensure_private_dir(job_dir(root, job.job_id), root)
    (folder / STATE_FILE).write_text(job.to_json(), encoding="utf-8")


def plant_job_in_jobs_done(root: Path, tmp_path: Path, created: datetime) -> None:
    job = a_job(created)
    folder = ensure_private_dir(job_dir(root, job.job_id), root)
    (folder / STATE_FILE).write_text(job.to_json(), encoding="utf-8")
    (folder / job.file_name).write_bytes(b"PK archive")


def plant_decrypt_folder(root: Path, tmp_path: Path, created: datetime) -> None:
    folder = ensure_private_dir(backups_dir(root) / ".decrypt-abc123", root)
    (folder / "archive.zip").write_bytes(b"PK clear")


def plant_loose_archives(root: Path, tmp_path: Path, created: datetime) -> None:
    for name in (archive_name(created), archive_name(created, encrypted=True)):
        ensure_private_dir(backups_dir(root), root)
        (backups_dir(root) / name).write_bytes(b"an old archive of the command line")


def plant_kept_named_file(root: Path, tmp_path: Path, created: datetime) -> None:
    ensure_private_dir(backups_dir(root), root)
    (backups_dir(root) / kept_name(created, "ui", uuid.uuid4().hex)).write_bytes(b"a file with a kept name")


def plant_link_to_a_kept_dir(root: Path, tmp_path: Path, created: datetime) -> None:
    outside = data_root_outside(tmp_path)
    target = plant_kept(outside, created=created, size=700).folder
    ensure_private_dir(backups_dir(root), root)
    (backups_dir(root) / kept_name(created, "ui", uuid.uuid4().hex)).symlink_to(target, target_is_directory=True)


def data_root_outside(tmp_path: Path) -> Path:
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    return outside


def plant_without_state(root: Path, tmp_path: Path, created: datetime) -> None:
    plant_kept(root, created=created, with_state=False)


def plant_garbage_state(root: Path, tmp_path: Path, created: datetime) -> None:
    (plant_kept(root, created=created).folder / STATE_FILE).write_bytes(b"{not json")


def plant_list_state(root: Path, tmp_path: Path, created: datetime) -> None:
    (plant_kept(root, created=created).folder / STATE_FILE).write_bytes(b"[]")


def plant_state_a_folder(root: Path, tmp_path: Path, created: datetime) -> None:
    folder = plant_kept(root, created=created).folder
    (folder / STATE_FILE).unlink()
    (folder / STATE_FILE).mkdir()


def plant_state_a_link(root: Path, tmp_path: Path, created: datetime) -> None:
    planted = plant_kept(root, created=created)
    elsewhere = data_root_outside(tmp_path) / "state-elsewhere.json"
    elsewhere.write_text(planted.job.to_json(), encoding="utf-8")
    (planted.folder / STATE_FILE).unlink()
    (planted.folder / STATE_FILE).symlink_to(elsewhere)


def plant_state_without_time_zone(root: Path, tmp_path: Path, created: datetime) -> None:
    planted = plant_kept(root, created=created)
    (planted.folder / STATE_FILE).write_text(planted.job.to_json().replace("+00:00", ""), encoding="utf-8")


def plant_failed(root: Path, tmp_path: Path, created: datetime) -> None:
    plant_kept(root, created=created, status="failed")


def plant_running(root: Path, tmp_path: Path, created: datetime) -> None:
    plant_kept(root, created=created, status="running")


def plant_job_id_of_another_name(root: Path, tmp_path: Path, created: datetime) -> None:
    """The folder's name ends with one id, its state says another job."""
    plant_kept(root, created=created, name=kept_name(created, "ui", "ffffffff" + "0" * 24))


def plant_without_archive(root: Path, tmp_path: Path, created: datetime) -> None:
    plant_kept(root, created=created, with_archive=False)


def plant_archive_a_link(root: Path, tmp_path: Path, created: datetime) -> None:
    planted = plant_kept(root, created=created)
    elsewhere = data_root_outside(tmp_path) / "archive-elsewhere.zip"
    elsewhere.write_bytes(b"PK an archive elsewhere")
    planted.archive.unlink()
    planted.archive.symlink_to(elsewhere)


def plant_archive_a_folder(root: Path, tmp_path: Path, created: datetime) -> None:
    planted = plant_kept(root, created=created)
    planted.archive.unlink()
    planted.archive.mkdir()


def plant_invalid_names(root: Path, tmp_path: Path, created: datetime) -> None:
    job_id = uuid.uuid4().hex
    for name in (
        f"librefolio-backup-{created:%Y%m%d-%H%M%S}-ui-{job_id[:8].upper()}",
        f"librefolio-backup-{created:%Y%m%d-%H%M%S}-ui-{job_id[:7]}",
        f"librefolio-backup-{created:%Y%m%d-%H%M%S}-{job_id[:8]}",
        f"backup-{created:%Y%m%d-%H%M%S}-ui-{job_id[:8]}",
    ):
        plant_kept(root, created=created, job_id=job_id, name=name)


#: Each way a thing of ``backups/`` is not a kept backup: (id, planter, needs links).
STRANGERS = [
    pytest.param(plant_job_in_jobs_running, id="a-running-job-in-jobs"),
    pytest.param(plant_job_in_jobs_done, id="a-finished-job-in-jobs"),
    pytest.param(plant_decrypt_folder, id="a-decrypt-folder"),
    pytest.param(plant_loose_archives, id="loose-archives-of-the-command-line"),
    pytest.param(plant_kept_named_file, id="a-file-with-a-kept-name"),
    pytest.param(plant_link_to_a_kept_dir, id="a-link-to-a-kept-folder", marks=needs_symlinks),
    pytest.param(plant_without_state, id="no-state"),
    pytest.param(plant_garbage_state, id="a-state-that-is-no-json"),
    pytest.param(plant_list_state, id="a-state-that-is-no-object"),
    pytest.param(plant_state_a_folder, id="a-state-that-is-a-folder"),
    pytest.param(plant_state_a_link, id="a-state-that-is-a-link", marks=needs_symlinks),
    pytest.param(plant_state_without_time_zone, id="a-state-without-time-zone"),
    pytest.param(plant_failed, id="a-failed-job"),
    pytest.param(plant_running, id="a-running-state-in-a-kept-folder"),
    pytest.param(plant_job_id_of_another_name, id="a-job-id-the-name-does-not-end-with"),
    pytest.param(plant_without_archive, id="no-archive"),
    pytest.param(plant_archive_a_link, id="an-archive-that-is-a-link", marks=needs_symlinks),
    pytest.param(plant_archive_a_folder, id="an-archive-that-is-a-folder"),
    pytest.param(plant_invalid_names, id="names-that-are-no-kept-names"),
]


@pytest.mark.parametrize("stranger", STRANGERS)
def test_what_is_not_a_kept_backup_is_not_listed(tmp_path, stranger):
    """(b) Beside a good backup, an old stranger: only the good one is listed."""
    root = data_root(tmp_path)
    planted = good(root)
    stranger(root, tmp_path, NOW - 40 * DAY)
    assert [item.job.job_id for item in list_kept(root)] == [planted.job.job_id], "only the good backup is listed"
    print_success("not listed")


def test_a_data_directory_without_backups_lists_nothing(tmp_path):
    root = data_root(tmp_path)
    assert list_kept(root) == [], "no backups/: nothing"
    assert not (root / "backups").exists(), "and none is created"


@needs_symlinks
def test_backups_a_link_or_a_file_lists_nothing_and_is_not_followed(tmp_path):
    """(b) A ``backups`` that is a link to a folder of kept backups is not read through."""
    root = data_root(tmp_path)
    other = tmp_path / "other-root"
    other.mkdir()
    plant_kept(other, created=NOW - DAY)
    backups_dir(root).symlink_to(backups_dir(other), target_is_directory=True)
    assert list_kept(root) == [], "backups/ is a link: not read through it"
    backups_dir(root).unlink()
    backups_dir(root).write_bytes(b"a file where the folder belongs")
    assert list_kept(root) == [], "backups is a file: nothing"


# =============================================================================
# (c) plan_cleanup
# =============================================================================


def test_nothing_is_planned_without_a_limit(tmp_path):
    """(c) 0 and 0 is off: however old and however big."""
    kept = [in_memory(NOW - 400 * DAY, 900 * MIB), in_memory(NOW - 300 * DAY, 900 * MIB), in_memory(NOW - 1 * DAY, 900 * MIB)]
    assert plan_cleanup(kept, cleanup_policy(0, 0)) == [], "a policy of 0 and 0 removes nothing"
    assert plan_cleanup([], cleanup_policy(1, 1)) == [], "nothing kept, nothing planned"


def test_the_age_alone_removes_what_is_older_than_the_days_given_against_the_now_given():
    """(c) 29 days and exactly 30 stay; 31 and 90 go, as ``age``. The ``now`` is the one given (2030), not the clock's."""
    print_section("plan_cleanup: age")
    young, edge, old, older, newest = in_memory(NOW - 29 * DAY, 10), in_memory(NOW - 30 * DAY, 10), in_memory(NOW - 31 * DAY, 10), in_memory(NOW - 90 * DAY, 10), in_memory(NOW - 1 * DAY, 10)
    plan = plan_cleanup([young, edge, old, older, newest], cleanup_policy(0, 30))
    assert plan_of(plan) == {old.job.job_id: "age", older.job.job_id: "age"}, f"older than 30 days go, for their age: {plan_of(plan)}"
    assert all(item in (young, edge, old, older, newest) for item, _reason in plan), "the plan names the backups it was given"
    print_success("age: 31 and 90 days removed")


def test_the_age_never_removes_the_most_recent_backup():
    """(c) All older than the limit: the most recent one stays."""
    newest, middle, oldest = in_memory(NOW - 40 * DAY, 10), in_memory(NOW - 50 * DAY, 10), in_memory(NOW - 60 * DAY, 10)
    assert plan_of(plan_cleanup([middle, newest, oldest], cleanup_policy(0, 30))) == {middle.job.job_id: "age", oldest.job.job_id: "age"}, "the most recent stays, whatever its age"


def test_one_backup_is_never_removed():
    """(c) Alone, too old and too big."""
    only = in_memory(NOW - 400 * DAY, 900 * MIB)
    assert plan_cleanup([only], cleanup_policy(1, 1)) == [], "one backup is never removed"


def test_the_space_alone_removes_the_oldest_until_the_rest_fits():
    """(c) Three of 600 000 bytes against 1 MiB: the oldest goes, 1 200 000 still does not fit, the next goes too."""
    print_section("plan_cleanup: space")
    newest, middle, oldest = in_memory(NOW - 1 * DAY, 600_000), in_memory(NOW - 2 * DAY, 600_000), in_memory(NOW - 3 * DAY, 600_000)
    assert plan_of(plan_cleanup([newest, middle, oldest], cleanup_policy(1, 0))) == {oldest.job.job_id: "space", middle.job.job_id: "space"}, "removed, oldest first, until 600 000 bytes fit in 1 MiB"
    two = [in_memory(NOW - 1 * DAY, 700_000), in_memory(NOW - 2 * DAY, 700_000)]
    assert plan_of(plan_cleanup(two, cleanup_policy(1, 0))) == {two[1].job.job_id: "space"}, "two of 700 000 bytes do not fit in 1 MiB: the oldest goes"


def test_the_space_is_over_only_above_the_limit():
    """(c) Exactly ``max_mb`` MiB fits; one byte more does not."""
    exact = [in_memory(NOW - 1 * DAY, MIB // 2), in_memory(NOW - 2 * DAY, MIB // 2)]
    assert plan_cleanup(exact, cleanup_policy(1, 0)) == [], "1 MiB exactly in 1 MiB: nothing to remove"
    over = [in_memory(NOW - 1 * DAY, MIB // 2), in_memory(NOW - 2 * DAY, MIB // 2 + 1)]
    assert plan_of(plan_cleanup(over, cleanup_policy(1, 0))) == {over[1].job.job_id: "space"}, "1 MiB and one byte: the oldest goes"


def test_the_space_keeps_the_most_recent_backup_however_big():
    """(c) The one left may be bigger than the limit: it stays."""
    newest, old = in_memory(NOW - 1 * DAY, 5 * MIB), in_memory(NOW - 2 * DAY, 10)
    assert plan_of(plan_cleanup([old, newest], cleanup_policy(1, 0))) == {old.job.job_id: "space"}, "the old one goes, the big recent one stays over the limit"


def test_both_limits_age_first_then_the_space_of_those_that_stay():
    """(c) C is too old: it goes for its age. A and B, 500 000 + 400 000 bytes, fit in 1 MiB once C (900 000) is gone, so B
    stays; with the limit lowered to fit only A, B goes for its space."""
    print_section("plan_cleanup: both")
    a, b, c = in_memory(NOW - 5 * DAY, 500_000), in_memory(NOW - 10 * DAY, 400_000), in_memory(NOW - 40 * DAY, 900_000)
    assert plan_of(plan_cleanup([a, b, c], cleanup_policy(1, 30))) == {c.job.job_id: "age"}, "C goes for its age; the rest, 900 000 bytes, fits: the space is not asked again of C"
    d, e, f = in_memory(NOW - 5 * DAY, 700_000), in_memory(NOW - 10 * DAY, 700_000), in_memory(NOW - 40 * DAY, 700_000)
    assert plan_of(plan_cleanup([d, e, f], cleanup_policy(1, 30))) == {f.job.job_id: "age", e.job.job_id: "space"}, "F for its age, then E for the space: D and E, 1 400 000 bytes, do not fit"
    print_success("age first, then space")


def test_a_backup_too_old_and_too_big_is_removed_for_its_age():
    """(c) The age is asked first: the reason of a backup both too old and in the way of the space is ``age``."""
    newest, old = in_memory(NOW - 1 * DAY, 10), in_memory(NOW - 90 * DAY, 3 * MIB)
    assert plan_of(plan_cleanup([newest, old], cleanup_policy(1, 30))) == {old.job.job_id: "age"}


def test_the_plan_does_not_depend_on_the_order_of_the_list():
    """(c) The most recent is the most recent by its date, not by its place."""
    backups = [in_memory(NOW - days * DAY, 400_000) for days in (4, 1, 3, 2, 5)]
    expected = plan_of(plan_cleanup(sorted(backups, key=lambda item: item.job.created_at, reverse=True), cleanup_policy(1, 0)))
    assert expected, "precondition: something is removed"
    for order in (backups, list(reversed(backups))):
        assert plan_of(plan_cleanup(order, cleanup_policy(1, 0))) == expected, "the same plan, whatever the order"
    newest = max(backups, key=lambda item: item.job.created_at)
    assert newest.job.job_id not in expected, "and the most recent is not in it"


# =============================================================================
# (d) apply_cleanup
# =============================================================================


def test_the_cleanup_removes_what_the_plan_names_and_answers_their_job_ids(tmp_path):
    """(d) By age: two of four go, with their archives; the others are as they were; the answer is a tuple of ids."""
    print_section("apply_cleanup: age")
    root = data_root(tmp_path)
    newest, young = plant_kept(root, created=NOW - 1 * DAY), plant_kept(root, created=NOW - 29 * DAY)
    old, older = plant_kept(root, created=NOW - 31 * DAY), plant_kept(root, created=NOW - 90 * DAY, origin="cli")
    before = {planted.folder: snapshot(planted.folder) for planted in (newest, young)}
    removed = apply_cleanup(root, cleanup_policy(0, 30), now=NOW)
    assert isinstance(removed, tuple), f"the answer is a tuple: {removed!r}"
    assert sorted(removed) == sorted([old.job.job_id, older.job.job_id]), f"the job ids of the two removed: {removed}"
    assert not os.path.lexists(old.folder) and not os.path.lexists(older.folder), "their folders are gone, archives with them"
    assert {folder: snapshot(folder) for folder in before} == before, "the others are as they were"
    print_success("2 removed by age")


def test_the_cleanup_by_space_and_by_both(tmp_path):
    """(d) By space, then both limits at once."""
    root = data_root(tmp_path)
    one, two, three = (plant_kept(root, created=NOW - days * DAY, size=600_000) for days in (1, 2, 3))
    removed = apply_cleanup(root, cleanup_policy(1, 0), now=NOW)
    assert sorted(removed) == sorted([two.job.job_id, three.job.job_id]) and one.folder.is_dir(), f"the oldest two go for the space, the newest stays: {removed}"
    d, e, f = (plant_kept(root, created=NOW - days * DAY, size=700_000) for days in (4, 5, 40))
    removed = apply_cleanup(root, cleanup_policy(1, 30), now=NOW)
    assert sorted(removed) == sorted([d.job.job_id, e.job.job_id, f.job.job_id]), f"F for its age, then E and D for the space (1 400 000 + 600 000 bytes do not fit in 1 MiB): {removed}"
    assert one.folder.is_dir(), "the most recent stays"


def test_a_policy_of_zero_removes_nothing(tmp_path):
    root = data_root(tmp_path)
    for days in (1, 100, 1000):
        plant_kept(root, created=NOW - days * DAY, size=900_000)
    before = snapshot(root)
    assert apply_cleanup(root, cleanup_policy(0, 0), now=NOW) == (), "nothing removed"
    assert snapshot(root) == before, "nothing touched"


def test_without_a_policy_the_cleanup_reads_the_policy_of_the_settings(tmp_path, monkeypatch):
    """(d) ``apply_cleanup(data_dir)`` asks ``read_policy()``."""
    root = data_root(tmp_path)
    plant_kept(root, created=NOW - 1 * DAY)
    old = plant_kept(root, created=NOW - 90 * DAY)
    module = retention_module()
    new_attr(module, "read_policy")
    monkeypatch.setattr(module, "read_policy", lambda: cleanup_policy(0, 30))
    assert apply_cleanup(root, now=NOW) == (old.job.job_id,), "the policy of the settings: 30 days"


def test_a_cleanup_whose_policy_cannot_be_read_removes_nothing_and_does_not_raise(tmp_path, monkeypatch):
    root = data_root(tmp_path)
    plant_kept(root, created=NOW - 1 * DAY)
    plant_kept(root, created=NOW - 90 * DAY)
    module = retention_module()

    def unreadable() -> Any:
        raise RuntimeError("the settings cannot be read")

    new_attr(module, "read_policy")
    monkeypatch.setattr(module, "read_policy", unreadable)
    before = snapshot(root)
    assert apply_cleanup(root, now=NOW) == (), "no policy, nothing removed, nothing raised"
    assert snapshot(root) == before


def test_a_listing_that_fails_does_not_raise(tmp_path, monkeypatch):
    root = data_root(tmp_path)
    plant_kept(root, created=NOW - 90 * DAY)
    module = retention_module()

    def failing(data_dir: Path) -> Any:
        raise OSError("the disk went away")

    new_attr(module, "list_kept")
    monkeypatch.setattr(module, "list_kept", failing)
    assert apply_cleanup(root, cleanup_policy(0, 1), now=NOW) == (), "nothing removed, nothing raised"


def test_a_folder_that_cannot_be_removed_does_not_stop_the_others(tmp_path, monkeypatch):
    """(d) One ``rmtree`` fails: it is left, the others go, nothing is raised, and it is not said removed."""
    print_section("apply_cleanup: a folder that fails")
    root = data_root(tmp_path)
    plant_kept(root, created=NOW - 1 * DAY)
    old, older, oldest = (plant_kept(root, created=NOW - days * DAY) for days in (40, 50, 60))
    real_rmtree = shutil.rmtree
    attempts: list[Path] = []

    def rmtree(path: Any, *args: Any, **kwargs: Any) -> None:
        attempts.append(Path(path))
        if Path(path) == older.folder:
            raise PermissionError(13, "denied", str(path))
        real_rmtree(path, *args, **kwargs)

    retention_module()
    monkeypatch.setattr(shutil, "rmtree", rmtree)
    removed = apply_cleanup(root, cleanup_policy(0, 30), now=NOW)
    assert older.folder in attempts, "barrier: the cleanup tried the folder that fails"
    assert sorted(removed) == sorted([old.job.job_id, oldest.job.job_id]), f"the two others are removed and said so, the third is not: {removed}"
    assert older.folder.is_dir() and not old.folder.exists() and not oldest.folder.exists(), "the third is still there, the others gone"
    print_success("one rmtree failed, two removed")


@pytest.mark.parametrize("stranger", STRANGERS)
def test_nothing_but_a_kept_backup_is_ever_removed(tmp_path, stranger):
    """(d) The harshest policy, a stranger older than any limit: it stays as it was, and what it points to. Beside it a
    kept backup that is removed, so that the cleanup is known to have acted."""
    root = data_root(tmp_path)
    plant_kept(root, created=NOW - 1 * DAY)
    old = plant_kept(root, created=NOW - 90 * DAY)
    stranger(root, tmp_path, NOW - 400 * DAY)
    outside = tmp_path / "outside"
    jobs_before = snapshot(backups_dir(root) / ".jobs") if (backups_dir(root) / ".jobs").exists() else None
    strangers_before = {name: kind for name, kind in snapshot(backups_dir(root)).items() if not name.startswith(old.folder.name)}
    outside_before = snapshot(outside) if outside.exists() else None
    removed = apply_cleanup(root, cleanup_policy(1, 1), now=NOW)
    assert removed == (old.job.job_id,), f"barrier: the old kept backup went: {removed}"
    after = {name: kind for name, kind in snapshot(backups_dir(root)).items() if not name.startswith(old.folder.name)}
    assert after == strangers_before, f"the stranger is as it was: {set(strangers_before) ^ set(after)}"
    assert (snapshot(outside) if outside.exists() else None) == outside_before, "and what a link points to"
    assert (snapshot(backups_dir(root) / ".jobs") if (backups_dir(root) / ".jobs").exists() else None) == jobs_before, "the jobs folder is as it was"


def test_without_backups_the_cleanup_does_nothing_and_creates_nothing(tmp_path):
    root = data_root(tmp_path)
    assert apply_cleanup(root, cleanup_policy(1, 1), now=NOW) == ()
    assert not (root / "backups").exists(), "no backups/ is created"


@contextmanager
def retention_logs():
    """What is logged inside the block, behind a barrier: a line through a logger of retention's name must reach it."""
    with capture_logs() as events:
        get_logger(RETENTION).warning(LOG_BARRIER)
        assert any(event.get("event") == LOG_BARRIER for event in events), f"barrier: a logger of {RETENTION} does not reach capture_logs"
        yield events


def test_each_removal_is_one_info_line_with_its_job_and_never_a_file_name_nor_a_path(tmp_path):
    """(d) ``job_id``, ``reason``, ``size_bytes`` and ``origin``: nothing that names a file or a place."""
    print_section("apply_cleanup: the log")
    root = data_root(tmp_path)
    plant_kept(root, created=NOW - 1 * DAY)
    by_age = plant_kept(root, created=NOW - 90 * DAY, size=1234, origin="cli")
    by_space = plant_kept(root, created=NOW - 5 * DAY, size=2 * MIB, origin="panel")
    with retention_logs() as events:
        removed = apply_cleanup(root, cleanup_policy(1, 30), now=NOW)
    assert sorted(removed) == sorted([by_age.job.job_id, by_space.job.job_id]), f"precondition: both removed: {removed}"
    lines = [event for event in events if event.get("log_level") == "info" and "job_id" in event]
    assert sorted(line["job_id"] for line in lines) == sorted(removed), f"one INFO line per removal, no more: {[line['job_id'] for line in lines]}"
    by_id = {line["job_id"]: line for line in lines}
    assert (by_id[by_age.job.job_id]["reason"], by_id[by_age.job.job_id]["size_bytes"], by_id[by_age.job.job_id]["origin"]) == ("age", 1234, "cli")
    assert (by_id[by_space.job.job_id]["reason"], by_id[by_space.job.job_id]["size_bytes"], by_id[by_space.job.job_id]["origin"]) == ("space", 2 * MIB, "panel")
    for event in events:
        said = repr(event)
        for secret in ("librefolio-backup", by_age.folder.name, by_space.archive.name, str(tmp_path)):
            assert secret not in said, f"no file name and no path in the log: {secret!r} in {event}"
    print_success("2 removals, 2 lines")


def test_a_cleanup_that_removes_nothing_says_no_removal(tmp_path):
    root = data_root(tmp_path)
    plant_kept(root, created=NOW - 1 * DAY)
    with retention_logs() as events:
        assert apply_cleanup(root, cleanup_policy(0, 30), now=NOW) == ()
    assert [event for event in events if event.get("log_level") == "info" and "job_id" in event] == [], "no removal, no line of removal"
