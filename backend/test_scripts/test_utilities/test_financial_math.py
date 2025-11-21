"""
Test financial math utilities.
All test is independent of the others, so help use pytest features.
"""
from datetime import date
from decimal import Decimal

from backend.app.schemas.assets import FAInterestRatePeriod, FALateInterestConfig, CompoundingType, CompoundFrequency, DayCountConvention
from backend.app.utils.financial_math import (
    find_active_period,
    parse_decimal_value,
    calculate_day_count_fraction,
    )


# ============================================================================
# TESTS: Day count conventions (ACT/365)
# ============================================================================

def test_calculate_daily_factor_between_act365_one_day():
    """Test ACT/365 for 1 day period."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 2)

    factor = calculate_day_count_fraction(start, end)

    assert factor == Decimal("1") / Decimal("365")


def test_calculate_daily_factor_between_act365_thirty_days():
    """Test ACT/365 for 30 days period."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 31)

    factor = calculate_day_count_fraction(start, end)

    assert factor == Decimal("30") / Decimal("365")


def test_calculate_daily_factor_between_act365_one_year():
    """Test ACT/365 for 365 days period."""
    start = date(2025, 1, 1)
    end = date(2026, 1, 1)

    factor = calculate_day_count_fraction(start, end)

    assert factor == Decimal("365") / Decimal("365")
    assert factor == Decimal("1")


def test_calculate_daily_factor_between_act365_zero_days():
    """Test ACT/365 for same day (0 days)."""
    start = date(2025, 1, 1)
    end = date(2025, 1, 1)

    factor = calculate_day_count_fraction(start, end)

    assert factor == Decimal("0")


# ============================================================================
# TESTS: find_active_period
# ============================================================================

def test_find_active_period_within_schedule():
    """Test finding period within scheduled dates."""
    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)
    target = date(2025, 6, 15)

    period = find_active_period(schedule, target, maturity)

    assert period is not None
    assert period.annual_rate == Decimal("0.05")
    assert period.compounding == CompoundingType.SIMPLE


def test_find_active_period_multiple_periods():
    """Test finding correct period across multiple periods."""
    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            ),
        FAInterestRatePeriod(
            start_date=date(2025, 7, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.06"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)

    # First period
    period1 = find_active_period(schedule, date(2025, 3, 15), maturity)
    assert period1 is not None
    assert period1.annual_rate == Decimal("0.05")

    # Second period
    period2 = find_active_period(schedule, date(2025, 9, 15), maturity)
    assert period2 is not None
    assert period2.annual_rate == Decimal("0.06")


def test_find_active_period_within_grace():
    """Test finding period within grace period after maturity."""
    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)
    late_interest = FALateInterestConfig(
        annual_rate=Decimal("0.12"),
        grace_period_days=30,
        compounding=CompoundingType.SIMPLE,
        day_count=DayCountConvention.ACT_365
        )

    # Within grace period (15 days after maturity)
    target = date(2026, 1, 15)
    period = find_active_period(schedule, target, maturity, late_interest)

    assert period is not None
    assert period.annual_rate == Decimal("0.05")  # Still uses scheduled rate


def test_find_active_period_after_grace():
    """Test finding period after grace period (late interest)."""
    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)
    late_interest = FALateInterestConfig(
        annual_rate=Decimal("0.12"),
        grace_period_days=30,
        compounding=CompoundingType.SIMPLE,
        day_count=DayCountConvention.ACT_365
        )

    # After grace period (45 days after maturity)
    target = date(2026, 2, 14)
    period = find_active_period(schedule, target, maturity, late_interest)

    assert period is not None
    assert period.annual_rate == Decimal("0.12")  # Late interest rate


def test_find_active_period_no_late_interest():
    """Test behavior after maturity without late interest config."""
    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)

    # After maturity without late interest config
    target = date(2026, 1, 15)
    period = find_active_period(schedule, target, maturity, late_interest=None)

    assert period is None  # No period found


def test_find_active_period_before_schedule():
    """Test behavior before schedule starts."""
    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)

    # Before schedule starts
    target = date(2024, 12, 1)
    period = find_active_period(schedule, target, maturity)

    assert period is None


# ============================================================================
# TESTS: find_active_period (returns full FAInterestRatePeriod object)
# ============================================================================

def test_find_active_period_within_schedule():
    """Test finding period within scheduled dates."""
    schedule = [
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            ),
        FAInterestRatePeriod(
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
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)
    late_interest = FALateInterestConfig(
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
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.SIMPLE,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)
    late_interest = FALateInterestConfig(
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
        FAInterestRatePeriod(
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
        FAInterestRatePeriod(
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
        FAInterestRatePeriod(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            annual_rate=Decimal("0.05"),
            compounding=CompoundingType.COMPOUND,
            compound_frequency=CompoundFrequency.MONTHLY,
            day_count=DayCountConvention.ACT_365
            )
        ]
    maturity = date(2025, 12, 31)
    print("ciao")
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
