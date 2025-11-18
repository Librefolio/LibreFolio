"""
Test suite for day count conventions.

Tests all 4 supported day count conventions with exact value comparisons:
- ACT/365 (Actual/365 Fixed)
- ACT/360 (Actual/360)
- ACT/ACT (Actual/Actual)
- 30/360 (30/360 US NASD)

All test values are calculated exactly - NO tolerance ranges.
"""
from datetime import date
from decimal import Decimal

import pytest

from backend.app.schemas.assets import DayCountConvention
from backend.app.utils.financial_math import calculate_day_count_fraction


class TestACT365:
    """Test ACT/365 (Actual/365 Fixed) convention."""

    def test_30_days(self):
        """30 days = 30/365."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2025, 1, 31),
            DayCountConvention.ACT_365
            )
        expected = Decimal("30") / Decimal("365")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_1_year_non_leap(self):
        """1 year (non-leap) = 365/365 = 1.0."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2026, 1, 1),
            DayCountConvention.ACT_365
            )
        expected = Decimal("365") / Decimal("365")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_1_year_leap(self):
        """1 year (leap year) = 366/365."""
        result = calculate_day_count_fraction(
            date(2024, 1, 1),
            date(2025, 1, 1),
            DayCountConvention.ACT_365
            )
        expected = Decimal("366") / Decimal("365")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_multi_year_range(self):
        """2 years crossing leap year (2024-2026)."""
        result = calculate_day_count_fraction(
            date(2024, 1, 1),
            date(2026, 1, 1),
            DayCountConvention.ACT_365
            )
        # 366 days (2024) + 365 days (2025) = 731 days
        expected = Decimal("731") / Decimal("365")
        assert result == expected, f"Expected {expected}, got {result}"


class TestACT360:
    """Test ACT/360 (Actual/360) convention."""

    def test_30_days(self):
        """30 days = 30/360."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2025, 1, 31),
            DayCountConvention.ACT_360
            )
        expected = Decimal("30") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_90_days(self):
        """90 days = 90/360 = 0.25."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2025, 4, 1),
            DayCountConvention.ACT_360
            )
        expected = Decimal("90") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_360_days(self):
        """360 days = 360/360 = 1.0."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2025, 12, 27),  # 360 days after Jan 1
            DayCountConvention.ACT_360
            )
        expected = Decimal("360") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_1_year_365_days(self):
        """1 year (365 days) = 365/360."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2026, 1, 1),
            DayCountConvention.ACT_360
            )
        expected = Decimal("365") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"


class TestACTACT:
    """Test ACT/ACT (Actual/Actual) convention."""

    def test_30_days_non_leap_year(self):
        """30 days in non-leap year = 30/365."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2025, 1, 31),
            DayCountConvention.ACT_ACT
            )
        expected = Decimal("30") / Decimal("365")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_30_days_leap_year(self):
        """30 days in leap year = 30/366."""
        result = calculate_day_count_fraction(
            date(2024, 1, 1),
            date(2024, 1, 31),
            DayCountConvention.ACT_ACT
            )
        expected = Decimal("30") / Decimal("366")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_cross_year_non_leap_to_leap(self):
        """Range crossing from non-leap (2023) to leap (2024)."""
        # Dec 1, 2023 to Feb 1, 2024
        # Days calculation: timedelta.days does NOT include end date
        # 2023: Dec 1 to Dec 31 = 30 days (30/365)
        # 2024: Jan 1 to Feb 1 = 31 days (31/366)
        result = calculate_day_count_fraction(
            date(2023, 12, 1),
            date(2024, 2, 1),
            DayCountConvention.ACT_ACT
            )
        expected = Decimal("30") / Decimal("365") + Decimal("31") / Decimal("366")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_cross_year_leap_to_non_leap(self):
        """Range crossing from leap (2024) to non-leap (2025)."""
        # Dec 1, 2024 to Feb 1, 2025
        # 2024: Dec 1 to Dec 31 = 30 days (30/366)
        # 2025: Jan 1 to Feb 1 = 31 days (31/365)
        result = calculate_day_count_fraction(
            date(2024, 12, 1),
            date(2025, 2, 1),
            DayCountConvention.ACT_ACT
            )
        expected = Decimal("30") / Decimal("366") + Decimal("31") / Decimal("365")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_multi_year_range(self):
        """3 years: 2023 (non-leap) → 2024 (leap) → 2025 (non-leap)."""
        # Jan 1, 2023 to Jan 1, 2026
        # Based on manual calculation:
        # 2023: Jan 1 to Dec 31 = 364 days
        # 2024: Jan 1 to Dec 31 = 365 days
        # 2025: Jan 1 to Jan 1, 2026 = 365 days
        # Total: 364/365 + 365/366 + 365/365 = 2.994528033535444269780672206
        result = calculate_day_count_fraction(
            date(2023, 1, 1),
            date(2026, 1, 1),
            DayCountConvention.ACT_ACT
            )
        expected = Decimal("364") / Decimal("365") + Decimal("365") / Decimal("366") + Decimal("365") / Decimal("365")
        assert result == expected, f"Expected {expected}, got {result}"


class Test30360:
    """Test 30/360 (30/360 US NASD) convention."""

    def test_same_month(self):
        """Same month: (day2 - day1) / 360."""
        # Jan 5 to Jan 20 = 15 days
        result = calculate_day_count_fraction(
            date(2025, 1, 5),
            date(2025, 1, 20),
            DayCountConvention.THIRTY_360
            )
        expected = Decimal("15") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_consecutive_months(self):
        """Consecutive months: each month = 30 days."""
        # Jan 1 to Feb 1 = 30 days (1 month)
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2025, 2, 1),
            DayCountConvention.THIRTY_360
            )
        expected = Decimal("30") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_1_year(self):
        """1 year = 360/360 = 1.0."""
        result = calculate_day_count_fraction(
            date(2025, 1, 1),
            date(2026, 1, 1),
            DayCountConvention.THIRTY_360
            )
        # 12 months * 30 days = 360 days
        expected = Decimal("360") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_end_of_month_31_to_28(self):
        """End-of-month edge case: Jan 31 to Feb 28."""
        # Day 31 adjusted to 30
        # (2026-2025)*360 + (2-1)*30 + (28-30) = 0 + 30 + (-2) = 28
        result = calculate_day_count_fraction(
            date(2025, 1, 31),
            date(2025, 2, 28),
            DayCountConvention.THIRTY_360
            )
        expected = Decimal("28") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_day_31_adjustment(self):
        """Day 31 is adjusted to 30."""
        # Jan 31 to Mar 15
        # d1=31 → 30, d2=15
        # (2025-2025)*360 + (3-1)*30 + (15-30) = 0 + 60 + (-15) = 45
        result = calculate_day_count_fraction(
            date(2025, 1, 31),
            date(2025, 3, 15),
            DayCountConvention.THIRTY_360
            )
        expected = Decimal("45") / Decimal("360")
        assert result == expected, f"Expected {expected}, got {result}"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_same_date_all_conventions(self):
        """Same date should return 0 for all conventions."""
        test_date = date(2025, 6, 15)

        for convention in DayCountConvention:
            result = calculate_day_count_fraction(test_date, test_date, convention)
            expected = Decimal("0")
            assert result == expected, f"{convention.value}: Expected {expected}, got {result}"

    def test_1_day_difference(self):
        """1 day difference for all conventions."""
        start = date(2025, 6, 15)
        end = date(2025, 6, 16)

        # ACT/365: 1/365
        result = calculate_day_count_fraction(start, end, DayCountConvention.ACT_365)
        assert result == Decimal("1") / Decimal("365")

        # ACT/360: 1/360
        result = calculate_day_count_fraction(start, end, DayCountConvention.ACT_360)
        assert result == Decimal("1") / Decimal("360")

        # ACT/ACT: 1/365 (2025 is non-leap)
        result = calculate_day_count_fraction(start, end, DayCountConvention.ACT_ACT)
        assert result == Decimal("1") / Decimal("365")

        # 30/360: 1/360
        result = calculate_day_count_fraction(start, end, DayCountConvention.THIRTY_360)
        assert result == Decimal("1") / Decimal("360")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
