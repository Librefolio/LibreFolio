"""
Test: Scheduler due-check functions — due_current_price() and due_history_sync().

Tests all edge cases: never-run, overdue, already-run, wrong day, multi-slot,
midnight crossing, corrupt timestamps.

Decision D-Z3-1 (lot Z3, plan phase01SleepWake): with a readable last run,
history sync is due when the most recent slot occurrence at or before now —
today and the MISSED_SLOT_LOOKBACK_DAYS (7) days before, configured days only,
in the scheduler's timezone — falls after the last run, so a slot missed while
the machine slept is caught up, even on a day that is not configured. Without a
last run (None or unreadable) only today's slots count, as before: SD-001..013
stay valid as they are. SD-014..022 pin the decision.

Test IDs: SD-001..SD-022
"""

import sys
from datetime import UTC, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.platform.scheduler import scheduler as scheduler_module
from backend.app.services.platform.scheduler.scheduler import due_current_price, due_history_sync
from backend.app.services.platform.scheduler.settings import SchedulerSettings
from backend.app.services.platform.scheduler.state import JobState, SchedulerState
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
    scheduler_timezone: str = "Europe/Rome",
) -> SchedulerSettings:
    return SchedulerSettings(
        scheduler_enabled=enabled,
        current_price_frequency_minutes=freq_minutes,
        history_sync_times=times if times is not None else [time(6, 0), time(23, 0)],
        history_sync_days=days if days is not None else ["mon", "tue", "wed", "thu", "fri", "sat"],
        history_sync_horizon_days=14,
        scheduler_timezone=scheduler_timezone,
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

    def test_configured_timezone_west_uses_previous_local_day(self):
        """SD-011: Monday 02:05 UTC is Sunday 21:05 in Bogotá; Sunday slot is due."""
        print_section("SD-011: due_history_sync — west timezone uses previous local day")
        now = datetime(2026, 6, 8, 2, 5, 0, tzinfo=UTC)
        state = _make_state(history_last=None)

        sunday_settings = _make_settings(times=[time(21, 0)], days=["sun"], scheduler_timezone="America/Bogota")
        monday_settings = _make_settings(times=[time(21, 0)], days=["mon"], scheduler_timezone="America/Bogota")

        assert due_history_sync(now, sunday_settings, state) is True
        assert due_history_sync(now, monday_settings, state) is False
        print_success("Bogotá local Sunday is used instead of UTC Monday")

    def test_configured_timezone_east_uses_next_local_day(self):
        """SD-012: Sunday 23:05 UTC is Monday 08:05 in Tokyo; Monday slot is due."""
        print_section("SD-012: due_history_sync — east timezone uses next local day")
        now = datetime(2026, 6, 7, 23, 5, 0, tzinfo=UTC)
        state = _make_state(history_last=None)

        monday_settings = _make_settings(times=[time(8, 0)], days=["mon"], scheduler_timezone="Asia/Tokyo")
        sunday_settings = _make_settings(times=[time(8, 0)], days=["sun"], scheduler_timezone="Asia/Tokyo")

        assert due_history_sync(now, monday_settings, state) is True
        assert due_history_sync(now, sunday_settings, state) is False
        print_success("Tokyo local Monday is used instead of UTC Sunday")

    def test_dst_keeps_same_local_time_across_winter_and_summer(self):
        """SD-013: 09:00 Europe/Rome remains 09:00 local in both CET and CEST."""
        print_section("SD-013: due_history_sync — DST keeps local wall-clock time stable")
        settings = _make_settings(times=[time(9, 0)], days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"], scheduler_timezone="Europe/Rome")
        state = _make_state(history_last=None)

        winter_before = datetime(2026, 1, 15, 7, 59, 0, tzinfo=UTC)  # 08:59 CET
        winter_due = datetime(2026, 1, 15, 8, 0, 0, tzinfo=UTC)  # 09:00 CET
        summer_before = datetime(2026, 7, 15, 6, 59, 0, tzinfo=UTC)  # 08:59 CEST
        summer_due = datetime(2026, 7, 15, 7, 0, 0, tzinfo=UTC)  # 09:00 CEST

        assert due_history_sync(winter_before, settings, state) is False
        assert due_history_sync(winter_due, settings, state) is True
        assert due_history_sync(summer_before, settings, state) is False
        assert due_history_sync(summer_due, settings, state) is True
        print_success("09:00 Europe/Rome is due at 08:00 UTC in winter and 07:00 UTC in summer")


# ============================================================================
# due_history_sync — missed slots (D-Z3-1)
# ============================================================================

ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ROME = ZoneInfo("Europe/Rome")
TOKYO = ZoneInfo("Asia/Tokyo")


class TestDueHistorySyncMissedSlot:
    """D-Z3-1. In June 2026 Europe/Rome is at +02:00, the offset of _now() and _iso(); 2026-06-08 is a Monday."""

    def test_missed_saturday_slot_is_due_on_an_unconfigured_sunday(self):
        """SD-014: days Mon–Sat, slots 06:00 and 23:00; last run Sat 06:05, now Sun 10:00 → True.

        Sunday is not a configured day: the rule of the day alone would wait for Monday 06:00. The Saturday 23:00 slot,
        missed, is the most recent one, and it falls after the last run.
        """
        print_section("SD-014: due_history_sync — Saturday 23:00 missed, Sunday not configured")
        now = _now(10, 0, day=14)  # Sunday
        state = _make_state(history_last=_iso(6, 5, day=13))  # Saturday 06:05
        assert due_history_sync(now, _make_settings(), state) is True
        print_success("Saturday 23:00 missed → due on Sunday 10:00")

    def test_saturday_slot_already_run_is_not_due_on_sunday(self):
        """SD-015: the same Sunday 10:00, last run Sat 23:05 → False: the most recent slot is covered."""
        print_section("SD-015: due_history_sync — Saturday 23:00 already run")
        now = _now(10, 0, day=14)
        state = _make_state(history_last=_iso(23, 5, day=13))
        assert due_history_sync(now, _make_settings(), state) is False
        print_success("Saturday 23:00 covered → not due on Sunday")

    def test_yesterday_late_slot_missed_before_today_first_slot(self):
        """SD-016: every day, slots 06:00 and 23:00, now Tue 05:00 — today's 06:00 not yet reached: last run Mon 07:00 → True (Mon 23:00 missed); last run Mon 23:05 → False."""
        print_section("SD-016: due_history_sync — yesterday's 23:00 missed, today's 06:00 not yet")
        settings = _make_settings(days=ALL_DAYS)
        now = _now(5, 0, day=9)  # Tuesday 05:00
        assert due_history_sync(now, settings, _make_state(history_last=_iso(7, 0, day=8))) is True
        assert due_history_sync(now, settings, _make_state(history_last=_iso(23, 5, day=8))) is False
        print_success("yesterday 23:00 missed → due; covered → not due")

    def test_weekly_slot_six_days_back(self):
        """SD-017: a weekly slot, Sunday 06:00 only; now the following Saturday 10:00: last run the Sunday before at 05:00 → True; at 07:00 → False."""
        print_section("SD-017: due_history_sync — weekly Sunday slot, checked on Saturday")
        settings = _make_settings(times=[time(6, 0)], days=["sun"])
        now = _now(10, 0, day=13)  # Saturday; the Sunday before is 2026-06-07
        assert due_history_sync(now, settings, _make_state(history_last=_iso(5, 0, day=7))) is True
        assert due_history_sync(now, settings, _make_state(history_last=_iso(7, 0, day=7))) is False
        print_success("Sunday 06:00 missed → due on Saturday; covered → not due")

    def test_previous_day_slot_in_another_time_zone(self):
        """SD-018: Asia/Tokyo, a slot Monday 08:00; now Tuesday 09:00 in Tokyo (Tuesday 00:00 UTC): last run Monday 07:00 in Tokyo → True; Monday 08:30 → False."""
        print_section("SD-018: due_history_sync — Tokyo, Monday's slot checked on Tuesday")
        settings = _make_settings(times=[time(8, 0)], days=["mon"], scheduler_timezone="Asia/Tokyo")
        now = datetime(2026, 6, 9, 9, 0, tzinfo=TOKYO)
        missed = _make_state(history_last=datetime(2026, 6, 8, 7, 0, tzinfo=TOKYO).isoformat())
        covered = _make_state(history_last=datetime(2026, 6, 8, 8, 30, tzinfo=TOKYO).isoformat())
        assert due_history_sync(now, settings, missed) is True
        assert due_history_sync(now, settings, covered) is False
        print_success("Monday 08:00 Tokyo missed → due on Tuesday; covered → not due")

    def test_slot_at_a_local_time_that_does_not_exist_on_the_dst_day(self):
        """SD-019: Europe/Rome, 2026-03-29, clocks jump from 02:00 to 03:00; a slot at 02:30, every day; now that day 10:00, last run 2026-03-28 03:00 → True, and no exception.

        Whichever instant the missing 02:30 is read as, it falls after the last run and before now.
        """
        print_section("SD-019: due_history_sync — slot 02:30 on the spring-forward day")
        settings = _make_settings(times=[time(2, 30)], days=ALL_DAYS, scheduler_timezone="Europe/Rome")
        state = _make_state(history_last=datetime(2026, 3, 28, 3, 0, tzinfo=ROME).isoformat())
        assert due_history_sync(datetime(2026, 3, 29, 10, 0, tzinfo=ROME), settings, state) is True
        assert due_history_sync(datetime(2026, 3, 29, 8, 0, tzinfo=UTC), settings, state) is True
        print_success("a slot in the DST gap → due, no exception")

    def test_same_weekday_seven_days_back(self):
        """SD-020: a weekly slot, Monday 23:00; now Monday 10:00 — today's slot not yet reached —: the slot seven days back still counts. Last run that Monday 22:00 → True; 23:05 → False."""
        print_section("SD-020: due_history_sync — the slot seven days back")
        settings = _make_settings(times=[time(23, 0)], days=["mon"])
        now = _now(10, 0, day=15)  # Monday; the Monday before is 2026-06-08
        assert due_history_sync(now, settings, _make_state(history_last=_iso(22, 0, day=8))) is True
        assert due_history_sync(now, settings, _make_state(history_last=_iso(23, 5, day=8))) is False
        print_success("last Monday 23:00 missed → due; covered → not due")

    def test_lookback_days_are_read_at_call_time(self, monkeypatch: pytest.MonkeyPatch):
        """SD-021: SD-017's weekly Sunday slot, six days back: ``MISSED_SLOT_LOOKBACK_DAYS`` 5 keeps it out of the window → False; 6 takes it in → True."""
        print_section("SD-021: due_history_sync — MISSED_SLOT_LOOKBACK_DAYS read at call time")
        settings = _make_settings(times=[time(6, 0)], days=["sun"])
        now = _now(10, 0, day=13)
        state = _make_state(history_last=_iso(5, 0, day=7))

        monkeypatch.setattr(scheduler_module, "MISSED_SLOT_LOOKBACK_DAYS", 5)
        assert due_history_sync(now, settings, state) is False
        monkeypatch.setattr(scheduler_module, "MISSED_SLOT_LOOKBACK_DAYS", 6)
        assert due_history_sync(now, settings, state) is True
        print_success("5 days: out of the window; 6 days: in it")

    @pytest.mark.parametrize("history_last", [None, "NOT_A_VALID_ISO_DATETIME"], ids=["never-run", "unreadable"])
    def test_without_a_readable_last_run_only_today_counts(self, history_last: str | None):
        """SD-022: no last run, or an unreadable one: today's slots alone, unchanged. Sunday 10:00, days Mon–Sat → False; Tuesday 05:00, every day — yesterday's 23:00 passed — → False; Monday 08:00, slot 06:00 → True."""
        print_section(f"SD-022: due_history_sync — last run {history_last!r}: today's rule")
        state = _make_state(history_last=history_last)
        assert due_history_sync(_now(10, 0, day=14), _make_settings(), state) is False
        assert due_history_sync(_now(5, 0, day=9), _make_settings(days=ALL_DAYS), state) is False
        assert due_history_sync(_now(8, 0, day=8), _make_settings(times=[time(6, 0)], days=["mon"]), state) is True
        print_success("only today's slots")
