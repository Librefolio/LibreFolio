"""
Test: Scheduler state persistence.

Tests load_state(), save_state(), atomic write, and recovery from corrupt/partial files.

Lot Z7b (SS-007..SS-011): ``JobState`` gains, after its six fields, ``last_items_deferred`` (0), ``retry_at``,
``consecutive_failures`` (0) and ``next_attempt_at`` (None); ``save_state`` writes them; a file written before them loads
with their defaults, one written by a newer version loads ignoring the keys ``JobState`` does not know, and a section
that is not an object loads as a fresh ``JobState``, without an exception, as today.

Test IDs: SS-001..SS-011
"""

import dataclasses
import json
import sys

import pytest

import backend.app.services.platform.scheduler.state as state_mod
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


# ============================================================================
# SS-007..SS-011: the fields of lot Z7b
# ============================================================================

#: The six fields of ``JobState`` before lot Z7b, as such a file holds them: every value differs from its default.
BEFORE_Z7B = {
    "current_price": {
        "last_run_at": "2026-06-08T10:00:00+02:00",
        "last_duration_s": 1.5,
        "last_status": "partial",
        "last_items_ok": 10,
        "last_items_err": 2,
        "last_error": "QuotaExceeded",
    },
    "history_sync": {
        "last_run_at": "2026-06-08T06:05:00+02:00",
        "last_duration_s": 7.2,
        "last_status": "ok",
        "last_items_ok": 5,
        "last_items_err": 0,
        "last_error": None,
    },
}
#: The four fields lot Z7b adds, in their order.
Z7B_FIELDS = ("last_items_deferred", "retry_at", "consecutive_failures", "next_attempt_at")


class TestZ7bFields:
    def test_job_state_gains_four_fields_after_its_six_with_their_defaults(self):
        """SS-007: ``JobState``'s fields, in order, with their defaults: the six of before, then ``last_items_deferred`` 0, ``retry_at`` None, ``consecutive_failures`` 0, ``next_attempt_at`` None."""
        print_section("SS-007: JobState fields of lot Z7b")

        shape = [(field.name, field.default) for field in dataclasses.fields(state_mod.JobState)]

        assert shape == [
            ("last_run_at", None),
            ("last_duration_s", None),
            ("last_status", None),
            ("last_items_ok", 0),
            ("last_items_err", 0),
            ("last_error", None),
            ("last_items_deferred", 0),
            ("retry_at", None),
            ("consecutive_failures", 0),
            ("next_attempt_at", None),
        ]
        print_success("four fields after the six, with their defaults")

    def test_save_state_writes_the_new_fields_and_load_state_reads_them_back(self, tmp_path, monkeypatch):
        """SS-008: ``save_state`` writes the four fields in each job's object — set or at their defaults —, and ``load_state`` gives back the very state saved."""
        print_section("SS-008: save_state + load_state with the fields of lot Z7b")
        state_mod = _make_state_module(tmp_path, monkeypatch)
        state = state_mod.SchedulerState(
            current_price=state_mod.JobState(
                last_run_at="2026-06-08T10:00:00+00:00",
                last_duration_s=1.5,
                last_status="partial",
                last_items_ok=3,
                last_items_err=1,
                last_items_deferred=2,
                retry_at="2026-06-08T10:05:00+00:00",
            ),
            history_sync=state_mod.JobState(
                last_run_at="2026-06-08T06:05:00+00:00",
                last_status="error",
                last_error="ProviderExploded",
                consecutive_failures=2,
                next_attempt_at="2026-06-08T10:02:00+00:00",
            ),
        )

        state_mod.save_state(state)
        written = json.loads((tmp_path / "scheduler_state.json").read_text())

        assert {key: written["current_price"].get(key, "<missing>") for key in Z7B_FIELDS} == {"last_items_deferred": 2, "retry_at": "2026-06-08T10:05:00+00:00", "consecutive_failures": 0, "next_attempt_at": None}
        assert {key: written["history_sync"].get(key, "<missing>") for key in Z7B_FIELDS} == {"last_items_deferred": 0, "retry_at": None, "consecutive_failures": 2, "next_attempt_at": "2026-06-08T10:02:00+00:00"}
        assert state_mod.load_state() == state
        print_success("written, and read back as saved")

    def test_a_file_written_before_z7b_loads_with_the_defaults_and_keeps_its_values(self, tmp_path, monkeypatch):
        """SS-009: a file with the six fields of before only: each job keeps its values, and the four new fields are at their defaults."""
        print_section("SS-009: load_state — a file written before lot Z7b")
        state_mod = _make_state_module(tmp_path, monkeypatch)
        (tmp_path / "scheduler_state.json").write_text(json.dumps(BEFORE_Z7B))

        result = state_mod.load_state()

        assert result == state_mod.SchedulerState(
            current_price=state_mod.JobState(**BEFORE_Z7B["current_price"]),
            history_sync=state_mod.JobState(**BEFORE_Z7B["history_sync"]),
        )
        assert [tuple(getattr(job, key) for key in Z7B_FIELDS) for job in (result.current_price, result.history_sync)] == [(0, None, 0, None), (0, None, 0, None)]
        print_success("old values kept, new fields at their defaults")

    def test_a_file_of_a_newer_version_loads_ignoring_the_keys_job_state_does_not_know(self, tmp_path, monkeypatch):
        """SS-010: a file written by a newer version — a key ``JobState`` does not know in each job, and a job of its own —: each job keeps its known values; the unknown keys are ignored. Before lot Z7b the whole state fell back to a fresh one."""
        print_section("SS-010: load_state — a file of a newer version")
        state_mod = _make_state_module(tmp_path, monkeypatch)
        newer = {
            "current_price": {**BEFORE_Z7B["current_price"], "last_provider": "yfinance"},
            "history_sync": {**BEFORE_Z7B["history_sync"], "skipped_pairs": ["NOK-SEK"]},
            "notifications": {"last_run_at": "2026-06-08T07:00:00+02:00"},
        }
        (tmp_path / "scheduler_state.json").write_text(json.dumps(newer))

        result = state_mod.load_state()

        assert result.current_price == state_mod.JobState(**BEFORE_Z7B["current_price"]), "the known values of current_price are kept"
        assert result.history_sync == state_mod.JobState(**BEFORE_Z7B["history_sync"]), "the known values of history_sync are kept"
        print_success("known values kept, unknown keys ignored")

    @pytest.mark.parametrize("section", [None, "garbage", [1, 2], 42], ids=["null", "a-string", "a-list", "a-number"])
    def test_a_section_that_is_not_an_object_loads_as_a_fresh_job_state(self, tmp_path, monkeypatch, section):
        """SS-011: ``current_price`` is not a JSON object: ``load_state`` does not raise, and that job loads as a fresh ``JobState``, as today — ignoring unknown keys must not turn a corrupt file into an exception at every tick. The other job's fate is not pinned."""
        print_section(f"SS-011: load_state — current_price is {section!r}")
        state_mod = _make_state_module(tmp_path, monkeypatch)
        (tmp_path / "scheduler_state.json").write_text(json.dumps({"current_price": section, "history_sync": BEFORE_Z7B["history_sync"]}))

        result = state_mod.load_state()

        assert result.current_price == state_mod.JobState()
        print_success("no exception, a fresh JobState")
