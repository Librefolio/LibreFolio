"""
Test: Scheduler settings parsing — _parse_times() and _parse_days().

Tests CSV parsing, validation, fallback behavior, and timezone storage semantics.

Test IDs: SC-001..SC-011
"""

import importlib.util
import sys
from datetime import time

import pytest

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.scheduler import settings as scheduler_settings
from backend.app.services.scheduler.settings import _parse_days, _parse_times
from backend.test_scripts.test_utils import print_section, print_success


class DummyAsyncSession:
    def __init__(self, _engine):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, _exc_type, _exc, _tb):
        return False


# ============================================================================
# _parse_times
# ============================================================================


class TestParseTimes:
    def test_parse_times_valid(self):
        """SC-001: '06:00,23:00' → [time(6,0), time(23,0)], sorted."""
        print_section("SC-001: _parse_times — valid CSV")
        result = _parse_times("06:00,23:00")
        assert result == [time(6, 0), time(23, 0)]
        print_success("Two valid times parsed and sorted")

    def test_parse_times_single(self):
        """SC-002: '12:30' → [time(12,30)]."""
        print_section("SC-002: _parse_times — single time")
        result = _parse_times("12:30")
        assert result == [time(12, 30)]
        print_success("Single time parsed correctly")

    def test_parse_times_whitespace(self):
        """SC-003: ' 06:00 , 23:00 ' → [time(6,0), time(23,0)] (whitespace stripped)."""
        print_section("SC-003: _parse_times — whitespace tolerance")
        result = _parse_times(" 06:00 , 23:00 ")
        assert result == [time(6, 0), time(23, 0)]
        print_success("Leading/trailing whitespace stripped correctly")

    def test_parse_times_sorted(self):
        """SC-003b: '23:00,06:00' → sorted result [time(6,0), time(23,0)]."""
        print_section("SC-003b: _parse_times — order normalized")
        result = _parse_times("23:00,06:00")
        assert result == [time(6, 0), time(23, 0)]
        print_success("Times sorted ascending regardless of input order")

    def test_parse_times_four_slots(self):
        """SC-003c: '06:00,12:00,18:00,23:00' → 4 slots."""
        print_section("SC-003c: _parse_times — four slots")
        result = _parse_times("06:00,12:00,18:00,23:00")
        assert len(result) == 4
        assert result[0] == time(6, 0)
        assert result[3] == time(23, 0)
        print_success("Four time slots parsed correctly")


# ============================================================================
# _parse_days
# ============================================================================


class TestParseDays:
    def test_parse_days_valid(self):
        """SC-004: 'mon,tue,wed,thu,fri,sat' → all 6 days."""
        print_section("SC-004: _parse_days — valid weekday CSV")
        result = _parse_days("mon,tue,wed,thu,fri,sat")
        assert result == ["mon", "tue", "wed", "thu", "fri", "sat"]
        print_success("All 6 weekdays parsed correctly")

    def test_parse_days_invalid_removed(self):
        """SC-005: 'mon,xyz,fri' → ['mon', 'fri'] (invalid values dropped)."""
        print_section("SC-005: _parse_days — invalid values removed")
        result = _parse_days("mon,xyz,fri")
        assert result == ["mon", "fri"]
        print_success("Invalid day codes removed from result")

    def test_parse_days_all_invalid_fallback(self):
        """SC-006: 'xyz,abc' → fallback to default Mon-Sat."""
        print_section("SC-006: _parse_days — all invalid → fallback")
        result = _parse_days("xyz,abc")
        assert result == ["mon", "tue", "wed", "thu", "fri", "sat"]
        print_success("All invalid → fallback to default Mon-Sat")

    def test_parse_days_case_insensitive(self):
        """SC-007: 'MON,TUE,WED' → ['mon', 'tue', 'wed']."""
        print_section("SC-007: _parse_days — case insensitive")
        result = _parse_days("MON,TUE,WED")
        assert result == ["mon", "tue", "wed"]
        print_success("Uppercase day codes normalized to lowercase")

    def test_parse_days_all_seven(self):
        """SC-007b: All 7 days including sunday."""
        print_section("SC-007b: _parse_days — all 7 days")
        result = _parse_days("mon,tue,wed,thu,fri,sat,sun")
        assert "sun" in result
        assert len(result) == 7
        print_success("All 7 days including sunday parsed correctly")


# ============================================================================
# load_scheduler_settings
# ============================================================================


class TestLoadSchedulerSettings:
    @pytest.mark.asyncio
    async def test_load_scheduler_settings_keeps_configured_times_local(self, monkeypatch):
        """SC-008: Stored HH:MM values are scheduler-local, not converted from UTC."""
        print_section("SC-008: load_scheduler_settings — stored times are local")
        values = {
            "scheduler_enabled": "true",
            "scheduler_current_price_frequency_minutes": "10",
            "scheduler_history_sync_times": "06:00,23:00",
            "scheduler_history_sync_days": "mon,tue",
            "scheduler_history_sync_horizon_days": "14",
            "scheduler_timezone": "Europe/Rome",
        }

        async def fake_get_setting_value(_session, key):
            return values.get(key)

        monkeypatch.setattr(scheduler_settings, "get_async_engine", lambda: object())
        monkeypatch.setattr(scheduler_settings, "AsyncSession", DummyAsyncSession)
        monkeypatch.setattr(scheduler_settings, "get_setting_value", fake_get_setting_value)

        result = await scheduler_settings.load_scheduler_settings()

        assert result.scheduler_timezone == "Europe/Rome"
        assert result.history_sync_times == [time(6, 0), time(23, 0)]
        assert result.history_sync_days == ["mon", "tue"]
        print_success("Stored times stay unchanged in configured timezone")

    @pytest.mark.asyncio
    async def test_load_scheduler_settings_default_times_are_local_no_conversion(self, monkeypatch):
        """SC-009: Missing times fall back to 06:00/23:00 in the configured timezone."""
        print_section("SC-009: load_scheduler_settings — default times are local")
        values = {
            "scheduler_enabled": "true",
            "scheduler_current_price_frequency_minutes": "10",
            "scheduler_history_sync_times": None,
            "scheduler_history_sync_days": "mon,tue",
            "scheduler_history_sync_horizon_days": "14",
            "scheduler_timezone": "Europe/Rome",
        }

        async def fake_get_setting_value(_session, key):
            return values.get(key)

        monkeypatch.setattr(scheduler_settings, "get_async_engine", lambda: object())
        monkeypatch.setattr(scheduler_settings, "AsyncSession", DummyAsyncSession)
        monkeypatch.setattr(scheduler_settings, "get_setting_value", fake_get_setting_value)

        result = await scheduler_settings.load_scheduler_settings()

        assert result.scheduler_timezone == "Europe/Rome"
        assert result.history_sync_times == [time(6, 0), time(23, 0)]
        print_success("Default times stay local and are not shifted to UTC")


# ============================================================================
# Alembic data migration helper
# ============================================================================


def _load_scheduler_timezone_migration():
    migration_path = PROJECT_ROOT / "backend" / "alembic" / "versions" / "5b1333fa6b07_scheduler_times_use_configured_timezone.py"
    spec = importlib.util.spec_from_file_location("scheduler_timezone_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSchedulerTimezoneMigration:
    def test_migration_is_noop_for_utc_timezone(self):
        """SC-010: Default UTC timezone leaves stored times unchanged."""
        print_section("SC-010: migration — UTC no-op")
        migration = _load_scheduler_timezone_migration()

        assert migration._convert_time_csv("06:00,23:00", "UTC", from_utc=True) == "06:00,23:00"
        assert migration._convert_time_csv("06:00,23:00", "UTC", from_utc=False) == "06:00,23:00"
        print_success("UTC upgrade/downgrade conversion leaves CSV untouched")

    def test_migration_converts_existing_utc_times_to_visible_local_times(self):
        """SC-011: Existing UTC HH:MM values become the local HH:MM values the modal showed."""
        print_section("SC-011: migration — UTC storage to Bogotá local display")
        migration = _load_scheduler_timezone_migration()

        assert migration._convert_time_csv("06:00,23:00", "America/Bogota", from_utc=True) == "01:00,18:00"
        print_success("UTC times converted to configured local timezone")
