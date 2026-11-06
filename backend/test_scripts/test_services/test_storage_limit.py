"""The space limit, applied (release 1.3, lot C8): ``services/platform/storage_limit.py`` and its use by the manual backup.

The limit (``storage_limit_mb``, or ``LIBREFOLIO_STORAGE_LIMIT_MB``) was only drawn on the space bar; now it stops what adds
data (developer decision, 06/11/2026). What this suite pins:

(a) ``judge(limit_mb, used, required, free)`` (pure): no limit (``None`` or 0) never refuses; ``required`` up to the limit,
    boundary included, is fine; past it a ``StorageLimitProblem`` with ``required_mb`` (whole megabytes, rounded up, at
    least 1) and ``disk_missing_bytes`` (what the volume lacks to hold the growth, 0 when it has enough, when the volume
    cannot be asked, or when the data would shrink).
(b) ``problem_for_added`` and ``problem_for_total`` over a real data directory: no limit (or a limit that cannot be read,
    which ``read_limit`` answers as none) is never a problem; an addition that passes the limit is, with the space used now.
(c) ``backup_estimate_bytes``: the database, the uploaded files and the broker reports, never the backups, the logs or the
    rest.
(d) ``storage_limit_detail``: the 507 body, a stable ``storage_limit_exceeded`` code and the numbers.
(e) the backup started by hand (``job_views.start_job("ui")``): fits, nothing happens; passes the limit, the clean-up runs
    first and, if that makes room, the backup starts; if it does not, 507 ``storage_limit_exceeded`` and nothing starts. The
    backups of a hosting panel and of the command line (``panel``, ``cli``) are never asked.

How: data directories under ``tmp_path``; ``read_limit`` and ``shutil.disk_usage`` replaced; ``jobs.start_backup`` and the
clean-up replaced by recorders. Isolation: pure. No lane database, no server, no network.
"""

from __future__ import annotations

import math
import shutil
from collections import namedtuple
from pathlib import Path

import pytest
from fastapi import HTTPException

from backend.app.api.v1.backup import job_views
from backend.app.services.platform import storage_limit, storage_usage
from backend.app.services.platform.storage_limit import BYTES_PER_MB, StorageLimitProblem, judge
from backend.test_scripts.test_utils import print_section, print_success

MB = BYTES_PER_MB
DiskUsage = namedtuple("DiskUsage", "total used free")


def _write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Path:
    """A data directory of 10 MB: 4 of database, 3 of uploads, 1 of reports, 2 of backups. Plenty of disk."""
    root = tmp_path / "data"
    _write(root / "sqlite" / "app.db", 4 * MB)
    _write(root / "custom-uploads" / "a.bin", 3 * MB)
    _write(root / "broker_reports" / "uploaded" / "r.csv", 1 * MB)
    _write(root / "backups" / "b" / "b.zip", 2 * MB)
    monkeypatch.setattr(shutil, "disk_usage", lambda _path: DiskUsage(1000 * MB, 100 * MB, 900 * MB))
    return root


def _limit(monkeypatch, limit_mb: int | None) -> None:
    monkeypatch.setattr(storage_usage, "read_limit", lambda: (limit_mb, False))


# =====================================================================================================================
# (a) judge
# =====================================================================================================================


@pytest.mark.parametrize("limit_mb", [None, 0])
def test_no_limit_never_refuses(limit_mb):
    """(a) No limit, or 0, is no problem whatever the data would take."""
    print_section("judge: no limit")
    assert judge(limit_mb, 10 * MB, 10_000 * MB, 0) is None
    print_success("no limit never refuses")


def test_up_to_the_limit_is_fine_and_one_byte_past_is_not():
    """(a) The limit is inclusive: exactly 100 MB is allowed, one byte more is not."""
    print_section("judge: the boundary")
    assert judge(100, 50 * MB, 100 * MB, 900 * MB) is None
    problem = judge(100, 50 * MB, 100 * MB + 1, 900 * MB)
    assert problem is not None
    assert problem.limit_mb == 100
    assert problem.required_mb == 101, "rounded up to whole megabytes: the limit that would allow it"
    print_success("the boundary is inclusive, required_mb is rounded up")


@pytest.mark.parametrize(
    ("used", "required", "free", "missing"),
    [
        (50 * MB, 150 * MB, 900 * MB, 0),
        (50 * MB, 150 * MB, 30 * MB, 70 * MB),
        (50 * MB, 150 * MB, None, 0),
        (150 * MB, 120 * MB, 0, 0),
    ],
    ids=["disk has room", "disk lacks 70 MB", "volume cannot be asked", "the data would shrink but still pass the limit"],
)
def test_disk_missing_bytes_is_what_the_volume_lacks_for_the_growth(used, required, free, missing):
    """(a) ``disk_missing_bytes``: the growth less the free space, never negative; 0 when unknown or when the data shrinks."""
    print_section("judge: the room the disk lacks")
    problem = judge(100, used, required, free)
    assert problem is not None
    assert problem.disk_missing_bytes == missing, f"expected {missing}, got {problem.disk_missing_bytes}"
    assert problem.required_mb == math.ceil(required / MB)
    print_success(f"missing {missing}")


def test_required_mb_is_at_least_one():
    """(a) A problem always names a limit of at least 1 MB."""
    assert StorageLimitProblem(limit_mb=1, used_bytes=0, required_bytes=1, disk_missing_bytes=0).required_mb == 1
    assert StorageLimitProblem(limit_mb=1, used_bytes=0, required_bytes=0, disk_missing_bytes=0).required_mb == 1


# =====================================================================================================================
# (b) over a data directory
# =====================================================================================================================


def test_no_limit_and_an_unreadable_limit_are_never_a_problem(data_dir, monkeypatch):
    """(b) ``read_limit`` answers a limit that cannot be read as none: nothing is refused."""
    print_section("problem_for_added: no limit")
    _limit(monkeypatch, None)
    assert storage_limit.problem_for_added(10_000 * MB, data_dir=data_dir) is None
    assert storage_limit.problem_for_total(10_000 * MB, data_dir=data_dir) is None
    storage_limit.require_room_for(10_000 * MB, data_dir=data_dir)
    print_success("no limit, nothing refused")


def test_an_addition_that_passes_the_limit_is_a_problem_with_the_space_used_now(data_dir, monkeypatch):
    """(b) 10 MB used, limit 12: +2 fits, +3 does not, and the problem says what it needs."""
    print_section("problem_for_added: over the limit")
    _limit(monkeypatch, 12)
    assert storage_limit.problem_for_added(2 * MB, data_dir=data_dir) is None
    problem = storage_limit.problem_for_added(3 * MB, data_dir=data_dir)
    assert problem is not None
    assert (problem.limit_mb, problem.used_bytes, problem.required_bytes, problem.required_mb, problem.disk_missing_bytes) == (12, 10 * MB, 13 * MB, 13, 0)
    with pytest.raises(storage_limit.StorageLimitExceededError) as raised:
        storage_limit.require_room_for(3 * MB, data_dir=data_dir)
    assert raised.value.problem == problem
    print_success("11 MB would pass a limit of 12: refused with 13 MB")


def test_a_total_is_judged_as_it_is_not_added_to_what_is_used(data_dir, monkeypatch):
    """(b) A restore leaves a total: 11 MB passes a limit of 10 even if the data now is 10 MB."""
    print_section("problem_for_total")
    _limit(monkeypatch, 10)
    assert storage_limit.problem_for_total(10 * MB, data_dir=data_dir) is None
    problem = storage_limit.problem_for_total(11 * MB, data_dir=data_dir)
    assert problem is not None and problem.required_mb == 11
    print_success("a total is not summed with the data of now")


# =====================================================================================================================
# (c) the estimate of a backup
# =====================================================================================================================


def test_a_backup_adds_what_the_archive_carries(data_dir):
    """(c) 4 MB of database, 3 of uploads, 1 of reports: 8 MB; the 2 MB of backups are not carried."""
    assert storage_limit.backup_estimate_bytes(data_dir) == 8 * MB
    print_success("the estimate is the database, the uploads and the reports")


# =====================================================================================================================
# (d) the 507 body
# =====================================================================================================================


def test_the_507_detail_has_a_stable_code_and_the_numbers():
    """(d) What the screens word their message from."""
    problem = StorageLimitProblem(limit_mb=100, used_bytes=90 * MB, required_bytes=120 * MB, disk_missing_bytes=5 * MB)
    detail = storage_limit.storage_limit_detail(problem)
    assert detail == {
        "code": "storage_limit_exceeded",
        "message": "The space limit would be passed",
        "limit_mb": 100,
        "used_bytes": 90 * MB,
        "required_bytes": 120 * MB,
        "required_mb": 120,
        "disk_missing_bytes": 5 * MB,
    }
    print_success("the detail carries the code and the numbers")


# =====================================================================================================================
# (e) the backup started by hand
# =====================================================================================================================


class _Started(Exception):
    """Raised by the replaced ``jobs.start_backup``: the backup would have started."""


@pytest.fixture
def backup_world(data_dir, monkeypatch):
    """The manual backup's world: this data directory, a recorder for the clean-up and a ``start_backup`` that says it ran."""
    calls: list[str] = []
    monkeypatch.setattr(job_views, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(storage_limit, "get_data_dir", lambda: data_dir)

    def start(origin, **_kwargs):
        calls.append(f"start:{origin}")
        raise _Started

    monkeypatch.setattr(job_views.jobs, "start_backup", start)
    return calls, data_dir


def _cleanup(monkeypatch, calls, data_dir: Path, *, frees_mb: int) -> None:
    def cleanup(_data_dir):
        calls.append("cleanup")
        if frees_mb:
            shutil.rmtree(data_dir / "backups")
            _write(data_dir / "backups" / "keep" / "k.zip", max(0, 2 - frees_mb) * MB)
        return ("old",) if frees_mb else ()

    monkeypatch.setattr(job_views.retention, "apply_cleanup", cleanup)


def test_a_manual_backup_that_fits_starts_without_a_clean_up(backup_world, monkeypatch):
    """(e) 10 MB used, +8 estimated, limit 20: it fits; no clean-up is asked."""
    print_section("manual backup: fits")
    calls, data_dir = backup_world
    _limit(monkeypatch, 20)
    _cleanup(monkeypatch, calls, data_dir, frees_mb=0)
    with pytest.raises(_Started):
        job_views.start_job("ui")
    assert calls == ["start:ui"]
    print_success("fits: started, no clean-up")


def test_a_manual_backup_past_the_limit_tries_the_clean_up_and_starts_if_it_made_room(backup_world, monkeypatch):
    """(e) 10 + 8 = 18 passes a limit of 17; the clean-up frees the 2 MB of backups: 16 + ... fits."""
    print_section("manual backup: the clean-up makes room")
    calls, data_dir = backup_world
    _limit(monkeypatch, 17)
    _cleanup(monkeypatch, calls, data_dir, frees_mb=2)
    with pytest.raises(_Started):
        job_views.start_job("ui")
    assert calls == ["cleanup", "start:ui"]
    print_success("the clean-up first, then the backup")


def test_a_manual_backup_still_past_the_limit_after_the_clean_up_is_refused_with_507(backup_world, monkeypatch):
    """(e) The clean-up frees nothing (its rules are off): 507 with the numbers, and no backup is started."""
    print_section("manual backup: refused")
    calls, data_dir = backup_world
    _limit(monkeypatch, 10)
    _cleanup(monkeypatch, calls, data_dir, frees_mb=0)
    with pytest.raises(HTTPException) as refused:
        job_views.start_job("ui")
    assert refused.value.status_code == 507
    assert refused.value.detail["code"] == "storage_limit_exceeded"
    assert refused.value.detail["required_mb"] == 18
    assert calls == ["cleanup"], "the clean-up was tried and no backup was started"
    print_success("refused: 507 storage_limit_exceeded, nothing started")


@pytest.mark.parametrize("origin", ["panel", "cli"])
def test_a_panel_or_command_line_backup_is_never_asked_about_the_limit(backup_world, monkeypatch, origin):
    """(e) Always made, over a limit that would refuse a manual one; the clean-up follows the backup itself (``jobs``)."""
    print_section(f"{origin} backup")
    calls, data_dir = backup_world
    _limit(monkeypatch, 1)
    _cleanup(monkeypatch, calls, data_dir, frees_mb=0)
    with pytest.raises(_Started):
        job_views.start_job(origin)
    assert calls == [f"start:{origin}"]
    print_success(f"{origin}: started over the limit")
