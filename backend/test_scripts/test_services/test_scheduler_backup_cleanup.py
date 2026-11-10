"""The hourly clean-up of the kept backups in the scheduler's run (workstream B, lot FB-24, contract
``B6r-fb24-backend-interface`` §6, decision D3).

``run_due_jobs(reason)`` calls ``retention.apply_cleanup``, once an hour at most (the process's monotonic clock), on a
worker thread (``asyncio.to_thread``), inside the busy span of the run. It is no third job: ``JOB_NAMES`` stays
``("current_price", "history_sync")`` and so does the ``RunReport`` (and what ``wake-sync`` answers from it). Any error of
the clean-up is logged and swallowed. The first run of a process applies it at once.

Pure, on the fakes of ``test_scheduler_catchup.py`` (its ``World``, ``MonotonicClock`` and ``Activity``, imported): every
collaborator of ``run_due_jobs`` is replaced; ``scheduler.time_module`` is a fake monotonic clock that moves only when the
test moves it; ``apply_cleanup`` is a recorder put in place of the product's, on ``retention`` and on the scheduler's own
namespace. The gate that lets one run in an hour is state of the process, which the contract does not name: each test starts
its clock a thousand hours after the one before, so that its first run is always one the gate lets through. No database,
no server, no network.
"""

from __future__ import annotations

import dataclasses
import itertools
import threading
import time as time_module
from typing import Any

import pytest
from structlog.testing import capture_logs

from backend.app.services.platform.scheduler import scheduler
from backend.test_scripts.test_services import test_backup_retention as retention_cases
from backend.test_scripts.test_services import test_scheduler_catchup as catchup
from backend.test_scripts.test_services.test_scheduler_catchup import REASONS, MonotonicClock, RecordingActivity

# The fixtures of ``test_scheduler_catchup.py``: the process's ``Activity`` replaced by one on a fake clock (autouse) and the
# collaborators of ``run_due_jobs`` faked.
activity = catchup.activity
world = catchup.world

HOUR = 3600.0
#: Each test's clock starts this many seconds after the last one's.
STEP = 1000 * HOUR
_TESTS = itertools.count(1)


class CleanupSpy:
    """``apply_cleanup`` in place of the product's: each call with the thread it ran in and whether ``scheduler`` was listed
    busy; it raises ``error`` when one is given."""

    def __init__(self, activity: RecordingActivity, error: BaseException | None = None) -> None:
        self.activity = activity
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> tuple[str, ...]:
        self.calls.append({"thread": threading.get_ident(), "busy": "scheduler" in self.activity.busy_reasons(), "args": args, "kwargs": kwargs})
        if self.error is not None:
            raise self.error
        return ()


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> MonotonicClock:
    """``scheduler.time_module`` with a fake monotonic clock, started well after any reading an earlier test left."""
    fake = MonotonicClock(time_module.monotonic() + STEP * next(_TESTS))
    monkeypatch.setattr(scheduler, "time_module", fake)
    return fake


def spy_on_cleanup(monkeypatch: pytest.MonkeyPatch, activity: RecordingActivity, error: BaseException | None = None) -> CleanupSpy:
    module = retention_cases.retention_module()
    retention_cases.new_attr(module, "apply_cleanup")
    spy = CleanupSpy(activity, error)
    monkeypatch.setattr(module, "apply_cleanup", spy)
    monkeypatch.setattr(scheduler, "apply_cleanup", spy, raising=False)
    return spy


@pytest.mark.asyncio
async def test_a_run_applies_the_cleanup_in_a_worker_thread_inside_its_busy_span(world, activity, clock, monkeypatch):
    """The first run of the process: once, off the event loop, while ``scheduler`` is listed busy."""
    spy = spy_on_cleanup(monkeypatch, activity)
    await scheduler.run_due_jobs("tick")
    assert len(spy.calls) == 1, f"one clean-up for the first run: {spy.calls}"
    assert spy.calls[0]["busy"] is True, "inside the busy span of the run"
    assert spy.calls[0]["thread"] != threading.get_ident(), "on a worker thread, not on the event loop"


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", REASONS)
async def test_the_first_run_applies_it_whatever_its_reason(world, activity, clock, monkeypatch, reason):
    spy = spy_on_cleanup(monkeypatch, activity)
    await scheduler.run_due_jobs(reason)
    assert len(spy.calls) == 1, f"a {reason} run applies the clean-up: {spy.calls}"


@pytest.mark.asyncio
async def test_it_runs_at_most_once_an_hour_by_the_monotonic_clock(world, activity, clock, monkeypatch):
    """Runs at 0, 30 min and 59 min: one clean-up; past the hour: a second; and not again within the next hour."""
    spy = spy_on_cleanup(monkeypatch, activity)
    await scheduler.run_due_jobs("tick")
    for minutes in (30, 59):
        clock.now += (minutes * 60.0) - (clock.now - clock.readings[0])
        await scheduler.run_due_jobs("tick")
    assert len(spy.calls) == 1, f"within the hour, the clean-up does not run again: {len(spy.calls)}"
    clock.now = clock.readings[0] + HOUR + 1
    await scheduler.run_due_jobs("tick")
    assert len(spy.calls) == 2, f"an hour and a second after the first: a second clean-up: {len(spy.calls)}"
    clock.now += 30 * 60.0
    await scheduler.run_due_jobs("tick")
    assert len(spy.calls) == 2, "and the hour is counted from the second one"


@pytest.mark.asyncio
async def test_an_error_of_the_cleanup_is_logged_and_does_not_touch_the_run(world, activity, clock, monkeypatch):
    """The report is the run's own: both jobs, ``ok``; the error is a line of the log, not an outcome."""
    spy = spy_on_cleanup(monkeypatch, activity, error=RuntimeError("the clean-up broke"))
    with capture_logs() as events:
        report = await scheduler.run_due_jobs("tick")
    assert spy.calls, "barrier: the clean-up ran"
    assert (report.status, [outcome.name for outcome in report.jobs]) == ("ok", ["current_price", "history_sync"]), f"the run is not changed by a clean-up that fails: {report}"
    assert {str(event.get("log_level")) for event in events} & {"warning", "error", "critical"}, f"the error is logged: {[(event.get('log_level'), event.get('event')) for event in events]}"
    assert "scheduler" not in activity.busy_reasons(), "and the busy span is closed"


@pytest.mark.asyncio
async def test_the_cleanup_is_no_third_job_and_the_report_has_the_same_shape(world, activity, clock, monkeypatch):
    spy = spy_on_cleanup(monkeypatch, activity)
    report = await scheduler.run_due_jobs("tick")
    assert spy.calls, "barrier: the clean-up ran"
    assert scheduler.JOB_NAMES == ("current_price", "history_sync"), f"JOB_NAMES: {scheduler.JOB_NAMES}"
    assert [field.name for field in dataclasses.fields(scheduler.RunReport)] == ["reason", "status", "started_at", "finished_at", "jobs"], "the RunReport has its fields"
    assert tuple(outcome.name for outcome in report.jobs) == scheduler.JOB_NAMES, f"and one outcome per job, none for the clean-up: {report.jobs}"
