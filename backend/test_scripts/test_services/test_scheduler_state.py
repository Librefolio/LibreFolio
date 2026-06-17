"""
Test: Scheduler state persistence.

Tests load_state(), save_state(), atomic write, and recovery from corrupt/partial files.

Test IDs: SS-001..SS-006
"""

import json
import sys

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_utils import print_section, print_success

# ============================================================================
# Helpers
# ============================================================================


def _make_state_module(tmp_path, monkeypatch):
    """Patch get_data_dir to point to tmp_path and reimport state module."""
    monkeypatch.setenv("LIBREFOLIO_DATA_DIR", str(tmp_path))

    # Patch at the module level where it is used
    import backend.app.services.scheduler.state as state_mod

    monkeypatch.setattr(state_mod, "get_data_dir", lambda: str(tmp_path))
    return state_mod


# ============================================================================
# SS-001: Missing file → fresh SchedulerState
# ============================================================================


class TestLoadStateMissingFile:
    def test_load_state_missing_file(self, tmp_path, monkeypatch):
        """SS-001: File does not exist → returns fresh SchedulerState with all None."""
        print_section("SS-001: load_state — missing file")

        state_mod = _make_state_module(tmp_path, monkeypatch)

        result = state_mod.load_state()

        assert result.current_price.last_run_at is None
        assert result.current_price.last_status is None
        assert result.history_sync.last_run_at is None
        assert result.history_sync.last_status is None

        print_success("Missing file → fresh SchedulerState OK")


# ============================================================================
# SS-002: Save + reload → data preserved
# ============================================================================


class TestSaveAndReload:
    def test_save_and_reload(self, tmp_path, monkeypatch):
        """SS-002: save_state() then load_state() → all fields preserved."""
        print_section("SS-002: save_state + load_state roundtrip")

        state_mod = _make_state_module(tmp_path, monkeypatch)

        state = state_mod.SchedulerState(
            current_price=state_mod.JobState(
                last_run_at="2026-06-08T10:00:00+02:00",
                last_duration_s=1.5,
                last_status="ok",
                last_items_ok=10,
                last_items_err=2,
            ),
            history_sync=state_mod.JobState(
                last_run_at="2026-06-08T06:05:00+02:00",
                last_duration_s=7.2,
                last_status="partial",
                last_items_ok=5,
                last_items_err=1,
            ),
        )

        state_mod.save_state(state)
        loaded = state_mod.load_state()

        assert loaded.current_price.last_run_at == "2026-06-08T10:00:00+02:00"
        assert loaded.current_price.last_duration_s == 1.5
        assert loaded.current_price.last_status == "ok"
        assert loaded.current_price.last_items_ok == 10
        assert loaded.current_price.last_items_err == 2

        assert loaded.history_sync.last_run_at == "2026-06-08T06:05:00+02:00"
        assert loaded.history_sync.last_status == "partial"
        assert loaded.history_sync.last_items_ok == 5
        assert loaded.history_sync.last_items_err == 1

        print_success("Save+reload roundtrip preserves all fields")


# ============================================================================
# SS-003: Atomic write — no .tmp residue
# ============================================================================


class TestAtomicWrite:
    def test_atomic_write_no_tmp_residue(self, tmp_path, monkeypatch):
        """SS-003: After save_state(), no .tmp file remains on disk."""
        print_section("SS-003: atomic write — no .tmp residue")

        state_mod = _make_state_module(tmp_path, monkeypatch)

        state_mod.save_state(state_mod.SchedulerState())

        tmp_files = list(tmp_path.glob("*.tmp"))
        assert len(tmp_files) == 0, f"Unexpected .tmp files found: {tmp_files}"

        state_file = tmp_path / "scheduler_state.json"
        assert state_file.exists(), "scheduler_state.json should exist after save"

        print_success("No .tmp residue after save_state()")


# ============================================================================
# SS-004: Corrupt JSON → fresh state (no crash)
# ============================================================================


class TestLoadCorruptJson:
    def test_load_corrupt_json(self, tmp_path, monkeypatch):
        """SS-004: File with invalid JSON → returns fresh SchedulerState, no crash."""
        print_section("SS-004: load_state — corrupt JSON")

        state_mod = _make_state_module(tmp_path, monkeypatch)

        state_file = tmp_path / "scheduler_state.json"
        state_file.write_text("{ this is not valid json !!!")

        result = state_mod.load_state()

        assert result.current_price.last_run_at is None
        assert result.history_sync.last_run_at is None

        print_success("Corrupt JSON → fresh state, no crash")


# ============================================================================
# SS-005: Partial JSON (only current_price) → history_sync defaults
# ============================================================================


class TestLoadPartialData:
    def test_load_partial_data(self, tmp_path, monkeypatch):
        """SS-005: JSON with only current_price → history_sync gets default JobState."""
        print_section("SS-005: load_state — partial JSON (only current_price)")

        state_mod = _make_state_module(tmp_path, monkeypatch)

        partial = {
            "current_price": {
                "last_run_at": "2026-06-08T10:00:00+02:00",
                "last_status": "ok",
                "last_items_ok": 5,
                "last_items_err": 0,
                "last_duration_s": 1.2,
                "last_error": None,
            }
        }
        (tmp_path / "scheduler_state.json").write_text(json.dumps(partial))

        result = state_mod.load_state()

        assert result.current_price.last_run_at == "2026-06-08T10:00:00+02:00"
        assert result.history_sync.last_run_at is None
        assert result.history_sync.last_items_ok == 0

        print_success("Partial JSON → missing sections get default JobState")


# ============================================================================
# SS-006: Extra keys in JSON → tolerated (KeyError/TypeError → fresh state)
# ============================================================================


class TestLoadExtraFields:
    def test_load_extra_fields_in_job_state(self, tmp_path, monkeypatch):
        """SS-006: JSON with unexpected extra keys in JobState → returns fresh state gracefully."""
        print_section("SS-006: load_state — extra fields in JSON")

        state_mod = _make_state_module(tmp_path, monkeypatch)

        # JobState dataclass does NOT accept extra kwargs → TypeError → fresh state
        bad_data = {
            "current_price": {
                "last_run_at": "2026-06-08T10:00:00+02:00",
                "last_status": "ok",
                "last_items_ok": 5,
                "last_items_err": 0,
                "last_duration_s": 1.2,
                "last_error": None,
                "unknown_extra_field": "boom",
            },
            "history_sync": {},
        }
        (tmp_path / "scheduler_state.json").write_text(json.dumps(bad_data))

        # Should not raise — returns fresh state on TypeError
        result = state_mod.load_state()

        assert result is not None
        # Either all-None (recovered) or correctly loaded (if implementation tolerates extra fields)
        assert result.current_price is not None
        assert result.history_sync is not None

        print_success("Extra fields tolerated — no crash")
