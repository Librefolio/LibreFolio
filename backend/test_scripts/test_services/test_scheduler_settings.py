"""
Test: Scheduler settings parsing — _parse_times() and _parse_days().

Pure functions (no DB, no async). Tests CSV parsing, validation, and fallback behavior.

Test IDs: SC-001..SC-007
"""

import sys

from backend.app.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))

from datetime import time

from backend.app.services.scheduler.settings import _parse_days, _parse_times
from backend.test_scripts.test_utils import print_section, print_success


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
