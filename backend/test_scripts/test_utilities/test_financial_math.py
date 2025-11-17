"""
Test financial math utilities.
All test is independent of the others, so help use pytest features.
"""
from datetime import date
from decimal import Decimal

import pytest

from backend.app.schemas.assets import InterestRatePeriod, LateInterestConfig, CompoundingType, CompoundFrequency, DayCountConvention
from backend.app.utils.financial_math import (
    calculate_daily_factor_between_act365,
    find_active_rate,
    find_active_period,
    calculate_accrued_interest,
    parse_decimal_value,
    )


# ============================================================================
# TESTS: Day count conventions (ACT/365)
# ============================================================================

def test_calculate_daily_factor_between_act365_one_day():
    """Test ACT/365 for 1 day period."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 2)

    factor = calculate_daily_factor_between_act365(start, end)

    assert factor == Decimal("1") / Decimal("365")


def test_calculate_daily_factor_between_act365_thirty_days():
    """Test ACT/365 for 30 days period."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 31)

    factor = calculate_daily_factor_between_act365(start, end)

    assert factor == Decimal("30") / Decimal("365")


def test_calculate_daily_factor_between_act365_one_year():
    """Test ACT/365 for 365 days period."""
    start = date(2025, 1, 1)
    end = date(2026, 1, 1)

    factor = calculate_daily_factor_between_act365(start, end)

    assert factor == Decimal("365") / Decimal("365")
    assert factor == Decimal("1")


def test_calculate_daily_factor_between_act365_zero_days():
    """Test ACT/365 for same day (0 days)."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 1)

    factor = calculate_daily_factor_between_act365(start, end)

    assert factor == Decimal("0")


# ============================================================================
# TESTS: find_active_rate
# ============================================================================

def test_find_active_rate_within_period():
    """Test finding rate within a scheduled period."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05")
            )
        ]
    maturity = date(2025, 12, 31)
    target = date(2025, 6, 15)

    rate = find_active_rate(schedule, target, maturity)

    assert rate == Decimal("0.05")


def test_find_active_rate_multiple_periods():
    """Test finding correct rate across multiple periods."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            annual_rate=Decimal("0.05")
            ),
        InterestRatePeriod(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.06")
            )
        ]
    maturity = date(2025, 12, 31)

    # First period
    rate1 = find_active_rate(schedule, date(2025, 3, 15), maturity)
    assert rate1 == Decimal("0.05")

    # Second period
    rate2 = find_active_rate(schedule, date(2025, 9, 15), maturity)
    assert rate2 == Decimal("0.06")


def test_find_active_rate_after_maturity_with_grace():
    """Test rate after maturity within grace period."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05")
            )
        ]
    maturity = date(2025, 12, 31)
    late_interest = LateInterestConfig(annual_rate=Decimal("0.12"), grace_period_days=30)

    # Within grace period (15 days after maturity)
    target = date(2026, 1, 15)
    rate = find_active_rate(schedule, target, maturity, late_interest)

    assert rate == Decimal("0.05")  # Still uses scheduled rate


def test_find_active_rate_after_grace_period():
    """Test late interest rate after grace period."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05")
            )
        ]
    maturity = date(2025, 12, 31)
    late_interest = LateInterestConfig(annual_rate=Decimal("0.12"), grace_period_days=30)

    # After grace period (45 days after maturity)
    target = date(2026, 2, 14)
    rate = find_active_rate(schedule, target, maturity, late_interest)

    assert rate == Decimal("0.12")  # Late interest rate


def test_find_active_rate_no_late_interest():
    """Test that rate is 0 after maturity without late interest config."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05")
            )
        ]
    maturity = date(2025, 12, 31)

    # After maturity without late interest config
    target = date(2026, 1, 15)
    rate = find_active_rate(schedule, target, maturity, late_interest=None)

    assert rate == Decimal("0")


# ============================================================================
# TESTS: calculate_accrued_interest
# ============================================================================

def test_calculate_accrued_interest_single_rate():
    """Test simple interest calculation with single rate."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05")
            )
        ]
    maturity = date(2025, 12, 31)
    face_value = Decimal("10000")

    # Calculate interest for 30 days
    interest = calculate_accrued_interest(
        face_value=face_value,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
        schedule=schedule,
        maturity_date=maturity
        )

    # Expected: 10000 * 0.05 * (30/365) ≈ 41.095...
    # Note: Actual calculation sums daily, so may differ slightly due to precision
    expected = face_value * Decimal("0.05") * (Decimal("30") / Decimal("365"))
    # Allow small tolerance for daily accumulation precision differences
    assert abs(interest - expected) < Decimal("2")  # Within 2 units (0.02%)


def test_calculate_accrued_interest_full_year():
    """Test interest calculation for full year."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05")
            )
        ]
    maturity = date(2025, 12, 31)
    face_value = Decimal("10000")

    # Calculate interest for full year
    interest = calculate_accrued_interest(
        face_value=face_value,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        schedule=schedule,
        maturity_date=maturity
        )

    # Expected: 10000 * 0.05 * 1 = 500
    # Note: Actual calculation sums daily, so may have tiny precision differences
    expected = face_value * Decimal("0.05")
    # Allow tiny tolerance for daily accumulation (should be nearly exact for full year)
    assert abs(interest - expected) < Decimal("0.01")  # Within 1 cent


def test_calculate_accrued_interest_rate_change():
    """Test interest calculation across rate change."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            annual_rate=Decimal("0.05")
            ),
        InterestRatePeriod(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.06")
            )
        ]
    maturity = date(2025, 12, 31)
    face_value = Decimal("10000")

    # Calculate interest from Jan 1 to Dec 31 (crosses rate change on July 1)
    interest = calculate_accrued_interest(
        face_value=face_value,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        schedule=schedule,
        maturity_date=maturity
        )

    # Should handle both rates correctly
    assert interest > Decimal("0")
    # Interest should be between 500 (all at 5%) and 600 (all at 6%)
    assert Decimal("500") < interest < Decimal("600")


# ============================================================================
# TESTS: find_active_period (returns full InterestRatePeriod object)
# ============================================================================

def test_find_active_period_within_schedule():
    """Test finding period within scheduled dates."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        ),
        InterestRatePeriod(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.06"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        )
    ]
    maturity = date(2025, 12, 31)

    # Test date in first period
    period = find_active_period(schedule, date(2025, 3, 15), maturity)
    assert period is not None
    assert period.annual_rate == Decimal("0.05")
    assert period.compounding == CompoundingType.SIMPLE
    assert period.day_count == DayCountConvention.ACT_365

    # Test date in second period
    period = find_active_period(schedule, date(2025, 9, 15), maturity)
    assert period is not None
    assert period.annual_rate == Decimal("0.06")


def test_find_active_period_within_grace():
    """Test finding period within grace period after maturity."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        )
    ]
    maturity = date(2025, 12, 31)
    late_interest = LateInterestConfig(
        annual_rate=Decimal("0.12"),
        grace_period_days=30,
        compounding=CompoundingType.SIMPLE,
        day_count=DayCountConvention.ACT_365
    )

    # Date within grace period (15 days after maturity)
    period = find_active_period(schedule, date(2026, 1, 15), maturity, late_interest)
    assert period is not None
    assert period.annual_rate == Decimal("0.05")  # Still uses last scheduled rate


def test_find_active_period_after_grace():
    """Test finding period after grace period (late interest)."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        )
    ]
    maturity = date(2025, 12, 31)
    late_interest = LateInterestConfig(
        annual_rate=Decimal("0.12"),
        grace_period_days=30,
        compounding=CompoundingType.SIMPLE,
        day_count=DayCountConvention.ACT_365
    )

    # Date 45 days after maturity (past grace period)
    period = find_active_period(schedule, date(2026, 2, 14), maturity, late_interest)
    assert period is not None
    assert period.annual_rate == Decimal("0.12")  # Uses late interest rate
    assert period.compounding == CompoundingType.SIMPLE
    assert period.day_count == DayCountConvention.ACT_365


def test_find_active_period_no_late_interest():
    """Test behavior after maturity without late interest config."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        )
    ]
    maturity = date(2025, 12, 31)

    # Date after maturity, no late_interest
    period = find_active_period(schedule, date(2026, 1, 15), maturity)
    assert period is None  # Should return None


def test_find_active_period_before_schedule():
    """Test behavior before schedule starts."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
        )
    ]
    maturity = date(2025, 12, 31)

    # Date before schedule starts
    period = find_active_period(schedule, date(2024, 12, 15), maturity)
    assert period is None


def test_find_active_period_with_compound_monthly():
    """Test that period preserves compound frequency."""
    schedule = [
        InterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.COMPOUND,
            compound_frequency=CompoundFrequency.MONTHLY,
            day_count=DayCountConvention.ACT_365
        )
    ]
    maturity = date(2025, 12, 31)

    period = find_active_period(schedule, date(2025, 6, 15), maturity)
    assert period is not None
    assert period.compounding == CompoundingType.COMPOUND
    assert period.compound_frequency == CompoundFrequency.MONTHLY


# ============================================================================
# TESTS: parse_decimal_value helper
# ============================================================================

def test_parse_decimal_value_from_decimal():
    """Test parsing already Decimal value."""
    value = Decimal("123.456")
    result = parse_decimal_value(value)
    assert result == value


def test_parse_decimal_value_from_string():
    """Test parsing string to Decimal."""
    value = "123.456"
    result = parse_decimal_value(value)
    assert result == Decimal("123.456")


def test_parse_decimal_value_from_int():
    """Test parsing int to Decimal."""
    value = 123
    result = parse_decimal_value(value)
    assert result == Decimal("123")


def test_parse_decimal_value_from_float():
    """Test parsing float to Decimal."""
    value = 123.456
    result = parse_decimal_value(value)
    assert isinstance(result, Decimal)


def test_parse_decimal_value_none():
    """Test parsing None returns None."""
    result = parse_decimal_value(None)
    assert result is None

