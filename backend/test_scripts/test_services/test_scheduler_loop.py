"""
Test: Scheduler loop integration — due_* with real SchedulerSettings + SchedulerState.

Does NOT start the async loop, does NOT mock service layer.
Tests logical scheduling decisions and state serialization roundtrip.

Lot B6 (project 68, SLO-004..SLO-008): the third job, ``profile_read``. ``JOBS`` lists it after the other two; each
job's name is its ``SchedulerState`` field (``_record_failure`` writes ``setattr(state, job.name, …)``); and it does
not light the «price refresh» banner (``_Job.price_banner`` False: ``_run_job`` calls neither
``PRICE_REFRESH.job_started`` nor ``job_finished`` for it). ``_run_job`` is driven on the real ``JOBS`` entry with its
``run`` replaced (``dataclasses.replace``), ``save_state`` and ``PRICE_REFRESH`` replaced on the module: no file, no
database. SLO-008 is the green guard that the two price jobs still light the banner.

Test IDs: SLO-001..SLO-008
"""

import asyncio
import dataclasses
import json
import sys
from datetime import UTC, datetime, time, timedelta, timezone

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

import backend.app.services.platform.scheduler.state as state_mod
from backend.app.services.platform.scheduler import scheduler as scheduler_module
from backend.app.services.platform.scheduler.scheduler import due_current_price, due_history_sync
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import JobState, SchedulerState
from backend.test_scripts.test_utils import print_section, print_success

TZ = timezone(timedelta(hours=2))


# ============================================================================
# SLO-001: Empty state + default settings → both jobs are due
# ============================================================================


class TestBothJobsDue:
    def test_both_jobs_due_on_empty_state(self):
        """SLO-001: Default settings + empty state → both current_price and history_sync are due."""
        print_section("SLO-001: Both jobs due on empty state")

        settings = SchedulerSettings(
            scheduler_enabled=True,
            current_price_frequency_minutes=10,
            history_sync_times=[time(6, 0), time(23, 0)],
            history_sync_days=["mon", "tue", "wed", "thu", "fri", "sat"],
            history_sync_horizon_days=14,
            scheduler_timezone="UTC",
        )
        state = SchedulerState()  # all None

        # Use a Monday at 10:00 (slot 06:00 passed, no last_run → both due)
        # 2026-06-08 is a Monday
        now = datetime(2026, 6, 8, 10, 0, 0, tzinfo=TZ)

        assert due_current_price(now, settings, state) is True, "current_price should be due"
        assert due_history_sync(now, settings, state) is True, "history_sync should be due (slot 06:00 passed)"

        print_success("Both jobs due with empty state on Monday 10:00 ✓")


# ============================================================================
# SLO-002: scheduler_enabled=False reflected in SchedulerSettings
# ============================================================================


class TestDisabledScheduler:
    def test_disabled_setting_reflected(self):
        """SLO-002: SchedulerSettings with enabled=False is constructed correctly."""
        print_section("SLO-002: scheduler_enabled=False reflected in settings object")

        settings = SchedulerSettings(
            scheduler_enabled=False,
            current_price_frequency_minutes=10,
            history_sync_times=[time(6, 0)],
            history_sync_days=["mon"],
            history_sync_horizon_days=14,
            scheduler_timezone="UTC",
        )

        assert settings.scheduler_enabled is False
        assert settings.current_price_frequency_minutes == 10

        print_success("scheduler_enabled=False correctly reflected in SchedulerSettings ✓")

    def test_due_functions_still_return_true_when_disabled(self):
        """SLO-002b: due_* functions don't check enabled flag — scheduler_loop is responsible.

        The due_* functions are pure scheduling checks; the enabled flag is
        checked by scheduler_loop() before calling them.
        """
        print_section("SLO-002b: due_* unaffected by enabled flag (loop responsibility)")

        settings = SchedulerSettings(
            scheduler_enabled=False,
            current_price_frequency_minutes=10,
            history_sync_times=[time(6, 0)],
            history_sync_days=["mon"],
            history_sync_horizon_days=14,
            scheduler_timezone="UTC",
        )
        state = SchedulerState()
        now = datetime(2026, 6, 8, 10, 0, 0, tzinfo=TZ)

        # due_* functions don't check enabled — they just compute due status
        assert due_current_price(now, settings, state) is True
        assert due_history_sync(now, settings, state) is True

        print_success("due_* unaffected by enabled flag (loop guards this externally) ✓")


# ============================================================================
# SLO-003: State serialization roundtrip with all fields
# ============================================================================


class TestStateRoundtrip:
    def test_full_state_roundtrip(self, tmp_path, monkeypatch):
        """SLO-003: Save SchedulerState with all fields, reload and verify all fields match."""
        print_section("SLO-003: State serialization roundtrip")

        monkeypatch.setattr(state_mod, "get_data_dir", lambda: str(tmp_path))

        now_iso = datetime(2026, 6, 8, 10, 0, 0, tzinfo=TZ).isoformat()

        original = SchedulerState(
            current_price=JobState(
                last_run_at=now_iso,
                last_duration_s=2.34,
                last_status="ok",
                last_items_ok=15,
                last_items_err=1,
                last_error=None,
            ),
            history_sync=JobState(
                last_run_at=now_iso,
                last_duration_s=8.91,
                last_status="partial",
                last_items_ok=20,
                last_items_err=3,
                last_error="Some error",
            ),
        )

        state_mod.save_state(original)
        reloaded = state_mod.load_state()

        # Verify all fields
        assert reloaded.current_price.last_run_at == now_iso
        assert reloaded.current_price.last_duration_s == 2.34
        assert reloaded.current_price.last_status == "ok"
        assert reloaded.current_price.last_items_ok == 15
        assert reloaded.current_price.last_items_err == 1
        assert reloaded.current_price.last_error is None

        assert reloaded.history_sync.last_run_at == now_iso
        assert reloaded.history_sync.last_duration_s == 8.91
        assert reloaded.history_sync.last_status == "partial"
        assert reloaded.history_sync.last_items_ok == 20
        assert reloaded.history_sync.last_items_err == 3
        assert reloaded.history_sync.last_error == "Some error"

        print_success("Full state roundtrip: all 12 fields preserved ✓")

    def test_state_json_structure(self, tmp_path, monkeypatch):
        """SLO-003b: JSON file has correct top-level keys: current_price, history_sync, profile_read (lot B6)."""
        print_section("SLO-003b: JSON structure verification")

        monkeypatch.setattr(state_mod, "get_data_dir", lambda: str(tmp_path))

        state_mod.save_state(SchedulerState())

        raw = json.loads((tmp_path / "scheduler_state.json").read_text())
        assert set(raw) == set(ALL_JOBS), f"one object per job, the three of lot B6: {sorted(raw)}"
        assert "last_run_at" in raw["current_price"]
        assert "last_status" in raw["current_price"]
        assert "last_items_ok" in raw["current_price"]

        print_success("JSON structure has expected top-level and nested keys ✓")


# ============================================================================
# SLO-004..SLO-008: the third job, profile_read (lot B6)
# ============================================================================

#: The literals of the contract, never read from the module under test.
ALL_JOBS = ("current_price", "history_sync", "profile_read")
PRICE_JOBS = ("current_price", "history_sync")
#: The longest a test waits for a run: against a hang, never a wait.
WAIT_SECONDS = 30.0


class ProviderExploded(Exception):
    """A job's failure, named so that its class is recognisable in a state and in an outcome."""


def _settings() -> SchedulerSettings:
    return SchedulerSettings(
        scheduler_enabled=True,
        current_price_frequency_minutes=10,
        history_sync_times=[time(6, 0), time(23, 0)],
        history_sync_days=["mon", "tue", "wed", "thu", "fri", "sat"],
        history_sync_horizon_days=14,
        scheduler_timezone="UTC",
    )


def _job(name: str):
    """The real ``JOBS`` entry named ``name``."""
    found = [job for job in scheduler_module.JOBS if job.name == name]
    assert len(found) == 1, f"one job {name!r} in JOBS: {[job.name for job in scheduler_module.JOBS]}"
    return found[0]


class TestProfileReadJob:
    def test_jobs_lists_profile_read_after_the_other_two(self):
        """SLO-004: ``JOBS`` and ``JOB_NAMES`` are current_price, history_sync, profile_read, in this order."""
        print_section("SLO-004: JOBS order")
        assert [job.name for job in scheduler_module.JOBS] == list(ALL_JOBS)
        assert tuple(scheduler_module.JOB_NAMES) == ALL_JOBS
        print_success("profile_read third")

    def test_each_job_name_is_its_state_field(self):
        """SLO-005: every job's ``name`` is a field of ``SchedulerState``, and ``state_of`` answers that very field."""
        print_section("SLO-005: name == state field")
        state = SchedulerState()
        fields = [field.name for field in dataclasses.fields(SchedulerState)]
        for job in scheduler_module.JOBS:
            assert job.name in fields, f"{job.name} is not a SchedulerState field: {fields}"
            assert job.state_of(state) is getattr(state, job.name), f"{job.name}: state_of reads another field"
        print_success("each name is its field")

    def test_only_the_price_jobs_light_the_banner(self):
        """SLO-006: ``_Job.price_banner`` is True by default; current_price and history_sync keep it, profile_read sets it False."""
        print_section("SLO-006: price_banner")
        defaults = {field.name: field.default for field in dataclasses.fields(scheduler_module._Job)}
        assert defaults.get("price_banner", "<missing>") is True, defaults
        assert {job.name: getattr(job, "price_banner", "<missing>") for job in scheduler_module.JOBS} == {"current_price": True, "history_sync": True, "profile_read": False}
        print_success("only the price jobs")

    @pytest.mark.asyncio
    async def test_a_profile_read_that_raises_is_recorded_on_its_own_field(self, monkeypatch):
        """SLO-007: the profile_read job raises: the failure is recorded on ``state.profile_read`` — ``last_status``
        "error", ``last_error`` the class name, one failure in a row, a ``next_attempt_at`` —, the state is saved, the
        other two jobs' states are untouched and the state gains no other attribute."""
        print_section("SLO-007: a failing profile_read records on state.profile_read")
        saved: list[SchedulerState] = []
        monkeypatch.setattr(scheduler_module, "save_state", saved.append)
        state = SchedulerState()
        before = dataclasses.asdict(state)

        async def explode(_state, _settings):
            raise ProviderExploded("provoked")

        job = dataclasses.replace(_job("profile_read"), run=explode)
        outcome = await asyncio.wait_for(scheduler_module._run_job(job, "tick", state, _settings()), WAIT_SECONDS)

        assert (outcome.name, outcome.status, outcome.error) == ("profile_read", "error", "ProviderExploded"), outcome
        recorded = state.profile_read
        assert (recorded.last_status, recorded.last_error, recorded.consecutive_failures) == ("error", "ProviderExploded", 1), recorded
        assert recorded.next_attempt_at is not None and outcome.retry_at is not None
        assert set(vars(state)) == set(ALL_JOBS), f"no attribute beside the three jobs: {sorted(vars(state))}"
        assert {name: dataclasses.asdict(getattr(state, name)) for name in PRICE_JOBS} == {name: before[name] for name in PRICE_JOBS}
        assert saved and saved[-1] is state, "the failure's record is saved"
        print_success("recorded on profile_read")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("name", "lit"), [pytest.param("profile_read", False, id="profile_read-dark"), pytest.param("current_price", True, id="current_price-lit-guard")])
    async def test_profile_read_does_not_light_the_price_refresh_banner(self, monkeypatch, name, lit):
        """SLO-008: a catch-up is pending (``run_started("startup")``) and a job runs, writing 5 items ok. profile_read:
        inside its run the banner stays "starting" with no job, and once the catch-up ends nothing is remembered — no
        ``last_finished_at``, not refreshed. current_price (the guard, green today): "running" with its name inside, then
        remembered and refreshed."""
        print_section(f"SLO-008: {name} and the price refresh banner")
        tracker = scheduler_module.PriceRefreshTracker()
        monkeypatch.setattr(scheduler_module, "PRICE_REFRESH", tracker)
        monkeypatch.setattr(scheduler_module, "save_state", lambda _state: None)
        seen: list = []

        async def run(state, _settings=None, **_kwargs):
            seen.append(tracker.snapshot())
            setattr(state, name, JobState(last_run_at=datetime.now(UTC).isoformat(), last_status="ok", last_items_ok=5))

        tracker.run_started("startup")
        job = dataclasses.replace(_job(name), run=run)
        outcome = await asyncio.wait_for(scheduler_module._run_job(job, "startup", SchedulerState(), _settings()), WAIT_SECONDS)
        tracker.run_finished()

        assert outcome.status == "ok" and outcome.items_ok == 5, outcome
        assert len(seen) == 1, f"barrier: the job ran once: {seen}"
        inside, after = seen[0], tracker.snapshot()
        if lit:
            assert (inside.state, inside.job) == ("running", name), inside
            assert after.last_finished_at is not None and after.last_refreshed is True, after
        else:
            assert (inside.state, inside.job) == ("starting", None), f"profile_read never shows in the price banner: {inside}"
            assert (after.state, after.last_finished_at, after.last_refreshed) == ("idle", None, False), f"a catch-up whose only job was profile_read remembers nothing: {after}"
        print_success("lit" if lit else "dark")
