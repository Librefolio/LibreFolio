"""
Test: Scheduler loop integration — due_* with real SchedulerSettings + SchedulerState.

Does NOT start the async loop, does NOT mock service layer.
Tests logical scheduling decisions and state serialization roundtrip.

Test IDs: SLO-001..SLO-003
"""

import json
import sys
from datetime import datetime, time, timedelta, timezone

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.scheduler.scheduler import due_current_price, due_history_sync
from backend.app.services.scheduler.settings import SchedulerSettings
from backend.app.services.scheduler.state import JobState, SchedulerState
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

        import backend.app.services.scheduler.state as state_mod

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
        """SLO-003b: JSON file has correct top-level keys: current_price, history_sync."""
        print_section("SLO-003b: JSON structure verification")

        import backend.app.services.scheduler.state as state_mod

        monkeypatch.setattr(state_mod, "get_data_dir", lambda: str(tmp_path))

        state_mod.save_state(SchedulerState())

        raw = json.loads((tmp_path / "scheduler_state.json").read_text())
        assert "current_price" in raw
        assert "history_sync" in raw
        assert "last_run_at" in raw["current_price"]
        assert "last_status" in raw["current_price"]
        assert "last_items_ok" in raw["current_price"]

        print_success("JSON structure has expected top-level and nested keys ✓")
