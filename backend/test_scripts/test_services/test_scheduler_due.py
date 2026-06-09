"""
Test: Scheduler due-check functions — due_current_price() and due_history_sync().

Tests all edge cases: never-run, overdue, already-run, wrong day, multi-slot,
midnight crossing, corrupt timestamps.

Test IDs: SD-001..SD-010
"""

import sys
from datetime import datetime, time, timedelta, timezone

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.scheduler.scheduler import due_current_price, due_history_sync
from backend.app.services.scheduler.settings import SchedulerSettings
from backend.app.services.scheduler.state import JobState, SchedulerState
from backend.test_scripts.test_utils import print_section, print_success

# Timezone offset +02:00 (CEST) used as reference
TZ = timezone(timedelta(hours=2))


def _now(hour: int = 10, minute: int = 0, day: int = 9, month: int = 6) -> datetime:
    """Build a tz-aware datetime for testing (2026-06-{day} {hour}:{minute} +02:00)."""
    return datetime(2026, month, day, hour, minute, 0, tzinfo=TZ)


def _iso(hour: int = 10, minute: int = 0, day: int = 9, month: int = 6) -> str:
    """Build an ISO-format string matching _now() for use in JobState."""
    return _now(hour, minute, day, month).isoformat()


def _make_settings(
    freq_minutes: int = 10,
    times: list[time] | None = None,
    days: list[str] | None = None,
    enabled: bool = True,
) -> SchedulerSettings:
    return SchedulerSettings(
        scheduler_enabled=enabled,
        current_price_frequency_minutes=freq_minutes,
        history_sync_times=times if times is not None else [time(6, 0), time(23, 0)],
        history_sync_days=days if days is not None else ["mon", "tue", "wed", "thu", "fri", "sat"],
        history_sync_horizon_days=14,
    )


def _make_state(current_last: str | None = None, history_last: str | None = None) -> SchedulerState:
    return SchedulerState(
        current_price=JobState(last_run_at=current_last),
        history_sync=JobState(last_run_at=history_last),
    )


# ============================================================================
# due_current_price
# ============================================================================


class TestDueCurrentPrice:
    def test_never_run(self):
        """SD-001: last_run_at = None → always due."""
        print_section("SD-001: due_current_price — never run")
        now = _now(10, 0)
        state = _make_state(current_last=None)
        settings = _make_settings(freq_minutes=10)
        assert due_current_price(now, settings, state) is True
        print_success("Never run → True")

    def test_just_run_not_due(self):
        """SD-002: last_run_at = now - 1min, freq=10 → NOT due."""
        print_section("SD-002: due_current_price — just run (1 min ago)")
        now = _now(10, 5)
        state = _make_state(current_last=_iso(10, 4))
        settings = _make_settings(freq_minutes=10)
        assert due_current_price(now, settings, state) is False
        print_success("Just run (1 min ago) with freq=10 → False")

    def test_overdue(self):
        """SD-003: last_run_at = now - 15min, freq=10 → due."""
        print_section("SD-003: due_current_price — overdue (15 min)")
        now = _now(10, 15)
        state = _make_state(current_last=_iso(10, 0))
        settings = _make_settings(freq_minutes=10)
        assert due_current_price(now, settings, state) is True
        print_success("Overdue (15 min with freq=10) → True")

    def test_exactly_at_interval(self):
        """SD-003b: last_run_at = now - exactly freq_minutes → due (>= check)."""
        print_section("SD-003b: due_current_price — exactly at interval")
        now = _now(10, 10)
        state = _make_state(current_last=_iso(10, 0))
        settings = _make_settings(freq_minutes=10)
        assert due_current_price(now, settings, state) is True
        print_success("Exactly at interval → True")

    def test_corrupt_timestamp(self):
        """SD-004: last_run_at = 'INVALID' → fail-safe True."""
        print_section("SD-004: due_current_price — corrupt timestamp")
        now = _now(10, 5)
        state = _make_state(current_last="NOT_A_VALID_ISO_DATETIME")
        settings = _make_settings(freq_minutes=10)
        assert due_current_price(now, settings, state) is True
        print_success("Corrupt timestamp → True (fail-safe)")


# ============================================================================
# due_history_sync
# ============================================================================


class TestDueHistorySync:
    def test_wrong_day(self):
        """SD-005: today=Sunday (2026-06-07), configured days=[mon..sat] → False."""
        print_section("SD-005: due_history_sync — wrong day (Sunday)")
        # 2026-06-07 is a Sunday
        now = datetime(2026, 6, 7, 10, 0, 0, tzinfo=TZ)
        state = _make_state(history_last=None)
        settings = _make_settings(days=["mon", "tue", "wed", "thu", "fri", "sat"])
        assert due_history_sync(now, settings, state) is False
        print_success("Sunday not in Mon-Sat → False")

    def test_right_day_slot_not_yet(self):
        """SD-006: today=Mon, slot=23:00, now=10:00 → slot not yet reached → False."""
        print_section("SD-006: due_history_sync — right day, slot not yet reached")
        # 2026-06-08 is a Monday
        now = datetime(2026, 6, 8, 10, 0, 0, tzinfo=TZ)
        state = _make_state(history_last=None)
        settings = _make_settings(times=[time(23, 0)], days=["mon"])
        assert due_history_sync(now, settings, state) is False
        print_success("Slot at 23:00 not yet reached at 10:00 → False")

    def test_right_day_slot_due_never_run(self):
        """SD-007: today=Mon, slot=06:00, now=08:00, last=None → True."""
        print_section("SD-007: due_history_sync — slot passed, never run")
        now = datetime(2026, 6, 8, 8, 0, 0, tzinfo=TZ)
        state = _make_state(history_last=None)
        settings = _make_settings(times=[time(6, 0)], days=["mon"])
        assert due_history_sync(now, settings, state) is True
        print_success("Slot passed (06:00) + never run → True")

    def test_already_run_this_slot(self):
        """SD-008: last_run=today 06:05, slot=06:00, now=08:00 → False."""
        print_section("SD-008: due_history_sync — already run this slot")
        now = datetime(2026, 6, 8, 8, 0, 0, tzinfo=TZ)
        # last run was at 06:05 today (after the 06:00 slot)
        state = _make_state(history_last=_iso(6, 5, day=8))
        settings = _make_settings(times=[time(6, 0)], days=["mon"])
        assert due_history_sync(now, settings, state) is False
        print_success("Already run this slot → False")

    def test_multi_slot_first_done_second_due(self):
        """SD-009: slots=[06:00,23:00], last=today 07:00, now=23:05 → True (second slot)."""
        print_section("SD-009: due_history_sync — multi-slot, second slot due")
        now = datetime(2026, 6, 8, 23, 5, 0, tzinfo=TZ)
        # last run covers the 06:00 slot but not the 23:00 slot
        state = _make_state(history_last=_iso(7, 0, day=8))
        settings = _make_settings(times=[time(6, 0), time(23, 0)], days=["mon"])
        assert due_history_sync(now, settings, state) is True
        print_success("First slot done, second slot due at 23:05 → True")

    def test_midnight_crossing(self):
        """SD-010: last=yesterday 23:05, today=Mon, now=00:30, slot=23:00 → False.

        The 23:00 slot for TODAY has not been reached (it's 00:30).
        Yesterday's 23:00 slot was already run (yesterday).
        """
        print_section("SD-010: due_history_sync — midnight crossing")
        # now is 00:30 on Monday (June 8)
        now = datetime(2026, 6, 8, 0, 30, 0, tzinfo=TZ)
        # last run was yesterday (Sunday June 7) at 23:05 → irrelevant (Sunday not in days)
        # but the check is: slot_dt = today 23:00, now(00:30) < slot_dt(23:00) → slot not due
        state = _make_state(history_last=_iso(23, 5, day=7))
        settings = _make_settings(times=[time(23, 0)], days=["mon"])
        # 00:30 < 23:00 today → slot not yet reached → False
        assert due_history_sync(now, settings, state) is False
        print_success("00:30 today, slot=23:00 not yet reached → False (no midnight recovery)")

    def test_all_days_configured(self):
        """SD-010b: All 7 days configured → even Sunday triggers."""
        print_section("SD-010b: due_history_sync — 7-day schedule on Sunday")
        # 2026-06-07 is Sunday
        now = datetime(2026, 6, 7, 10, 0, 0, tzinfo=TZ)
        state = _make_state(history_last=None)
        settings = _make_settings(times=[time(6, 0)], days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"])
        assert due_history_sync(now, settings, state) is True
        print_success("7-day schedule includes Sunday → True")
