"""The checks of a restore that wait for a decision (release 1.3, lot C9-6): ``restore_jobs.waiting_checks``.

The id of a check used to live only in the browser tab that started it; another tab or device could not resume it. The
server now lists them: what the Backup tab of Settings shows as «restore waiting until …», with «Resume» and «Discard».

- Listed: a check started from the app (origin ``admin``) that runs (no expiry, no verdict yet), and one that ended with a
  report still valid (its ``expires_at``, whether it is restorable), the newest first.
- Not listed: a failed check, an expired one, a hosting panel's (origin ``panel``), the copy a confirmed restore waits to
  apply, and an ended check whose report cannot be read.

How: the states written as ``restore_jobs`` writes them, under ``tmp_path``; the reports read through a replaced
``read_report``; the lock of the checks held while a check is said to run. Isolation: pure.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.services.platform.instance_backup import restore_jobs
from backend.app.services.platform.instance_backup.jobs import _RunLock
from backend.app.services.platform.instance_backup.paths import STAGE_LOCK_FILE, checks_dir, ensure_private_dir, stages_dir, uploads_dir
from backend.test_scripts.test_utils import print_section, print_success

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "data"
    root.mkdir()
    for folder in (stages_dir(root), checks_dir(root), uploads_dir(root)):
        ensure_private_dir(folder, root)
    monkeypatch.setattr(restore_jobs, "protected_stage", lambda _data_dir: None)
    return root


def _check(data_dir: Path, letter: str, status: str, *, minutes: int, origin: str = "admin") -> str:
    stage_id = letter * 32
    created = NOW - timedelta(minutes=minutes)
    check = restore_jobs.RestoreCheck(
        stage_id=stage_id,
        upload_id="0" * 32,
        status=status,
        phase="checking" if status == "running" else None,
        done_bytes=0,
        total_bytes=0,
        created_at=created,
        finished_at=None if status == "running" else created,
        error_code="not_a_backup" if status == "failed" else None,
        origin=origin,
    )
    restore_jobs._write_state(data_dir, check)
    return stage_id


def test_the_waiting_checks_are_the_running_and_the_valid_ones_started_from_the_app_newest_first(data_dir, monkeypatch):
    print_section("waiting_checks")
    reports = {
        "a" * 32: SimpleNamespace(expires_at=NOW + timedelta(hours=3), restorable=True),
        "b" * 32: SimpleNamespace(expires_at=NOW + timedelta(hours=1), restorable=False),
        "c" * 32: SimpleNamespace(expires_at=NOW - timedelta(minutes=1), restorable=True),
        "e" * 32: SimpleNamespace(expires_at=NOW + timedelta(hours=1), restorable=True),
    }

    def read_report(_data_dir, stage_id):
        if stage_id not in reports:
            raise FileNotFoundError(stage_id)
        return reports[stage_id]

    monkeypatch.setattr(restore_jobs, "read_report", read_report)
    _check(data_dir, "a", "done", minutes=30)
    _check(data_dir, "b", "done", minutes=10)
    _check(data_dir, "c", "done", minutes=5)  # expired
    _check(data_dir, "d", "failed", minutes=4)
    _check(data_dir, "e", "done", minutes=3, origin="panel")
    _check(data_dir, "f", "done", minutes=2)  # its report cannot be read
    running = _check(data_dir, "9", "running", minutes=1)
    lock = _RunLock(stages_dir(data_dir) / STAGE_LOCK_FILE)
    assert lock.try_acquire(), "precondition: the check said to run holds the lock"
    try:
        waiting = restore_jobs.waiting_checks(data_dir=data_dir, now=NOW)
    finally:
        lock.release()

    listed = [(item.check.stage_id[0], item.check.status, item.expires_at, item.restorable) for item in waiting]
    assert listed == [
        ("9", "running", None, None),
        ("b", "done", NOW + timedelta(hours=1), False),
        ("a", "done", NOW + timedelta(hours=3), True),
    ], listed
    assert waiting[0].check.stage_id == running
    print_success(f"{[item[0] for item in listed]}")


def test_the_copy_a_confirmed_restore_waits_to_apply_is_not_listed(data_dir, monkeypatch):
    stage_id = _check(data_dir, "a", "done", minutes=1)
    monkeypatch.setattr(restore_jobs, "read_report", lambda _data_dir, _stage_id: SimpleNamespace(expires_at=NOW + timedelta(hours=1), restorable=True))
    assert [item.check.stage_id for item in restore_jobs.waiting_checks(data_dir=data_dir, now=NOW)] == [stage_id]
    monkeypatch.setattr(restore_jobs, "protected_stage", lambda _data_dir: stage_id)
    assert restore_jobs.waiting_checks(data_dir=data_dir, now=NOW) == []
    print_success("the pending restore's copy is the status's, not a waiting check")


def test_a_data_directory_with_no_checks_lists_none(tmp_path):
    assert restore_jobs.waiting_checks(data_dir=tmp_path, now=NOW) == []
