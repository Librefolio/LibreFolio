"""
Test suite for interest calculations.

Tests simple and compound interest calculations with exact value comparisons:
- SIMPLE interest (I = P * r * t)
- COMPOUND interest with all frequencies (annual, semiannual, quarterly, monthly, daily, continuous)

All test values are calculated exactly - NO tolerance ranges.

Formula references:
- Simple: I = P * r * t
- Compound periodic: A = P * (1 + r/n)^(n*t), I = A - P
- Compound continuous: A = P * e^(r*t), I = A - P

Where:
- P = Principal
- r = Annual rate (as decimal, e.g., 0.05 for 5%)
- t = Time in years
- n = Number of compounding periods per year
- I = Interest earned
- A = Final amount (principal + interest)
"""

import math
from decimal import Decimal

import pytest

from backend.app.schemas.assets import MaturationFrequency
from backend.app.utils.financial_math import (
    calculate_simple_interest,
    calculate_compound_interest,
    get_compounding_periods_per_year,
    )


class TestSimpleInterest:
    """Test simple interest calculations (I = P * r * t)."""

    def test_10k_5percent_1year(self):
        """€10,000 at 5% for 1 year = €500."""
        result = calculate_simple_interest(
            principal=Decimal("10000"), annual_rate=Decimal("0.05"), time_fraction=Decimal("1")
            )
        expected = Decimal("500")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_6months(self):
        """€10,000 at 5% for 6 months (0.5 years) = €250."""
        result = calculate_simple_interest(
            principal=Decimal("10000"), annual_rate=Decimal("0.05"), time_fraction=Decimal("0.5")
            )
        expected = Decimal("250")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_3months(self):
        """€10,000 at 5% for 3 months (0.25 years) = €125."""
        result = calculate_simple_interest(
            principal=Decimal("10000"), annual_rate=Decimal("0.05"), time_fraction=Decimal("0.25")
            )
        expected = Decimal("125")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_12percent_30days_act365(self):
        """€10,000 at 12% for 30 days (ACT/365)."""
        # 30/365 = 0.0821917808219178...
        # Interest = 10000 * 0.12 * (30/365) = 98.630136986301369863...
        time_fraction = Decimal("30") / Decimal("365")
        result = calculate_simple_interest(
            principal=Decimal("10000"), annual_rate=Decimal("0.12"), time_fraction=time_fraction
            )
        expected = Decimal("10000") * Decimal("0.12") * time_fraction
        assert result == expected, f"Expected {expected}, got {result}"

    def test_different_principal_amounts(self):
        """Test with various principal amounts."""
        test_cases = [
            (Decimal("1000"), Decimal("0.05"), Decimal("1"), Decimal("50")),
            (Decimal("5000"), Decimal("0.10"), Decimal("1"), Decimal("500")),
            (Decimal("100000"), Decimal("0.03"), Decimal("1"), Decimal("3000")),
            ]

        for principal, rate, time, expected in test_cases:
            result = calculate_simple_interest(principal, rate, time)
            assert result == expected, f"Principal {principal}: expected {expected}, got {result}"


class TestCompoundInterestAnnual:
    """Test compound interest with annual compounding."""

    def test_10k_5percent_1year(self):
        """€10,000 at 5% for 1 year, annual compounding = €500 (same as simple)."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("1"),
            frequency=MaturationFrequency.ANNUAL,
            )
        # (1 + 0.05)^1 = 1.05, Interest = 10000 * 0.05 = 500
        expected = Decimal("500")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_2years(self):
        """€10,000 at 5% for 2 years, annual compounding."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("2"),
            frequency=MaturationFrequency.ANNUAL,
            )
        # A = 10000 * (1.05)^2 = 10000 * 1.1025 = 11025
        # I = 11025 - 10000 = 1025
        expected = Decimal("1025")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_half_year(self):
        """€10,000 at 5% for 0.5 years, annual compounding."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("0.5"),
            frequency=MaturationFrequency.ANNUAL,
            )
        # A = 10000 * (1.05)^0.5 = 10000 * 1.024695076595959...
        # I = 246.95076595959...
        base = Decimal("1.05")
        exponent = 0.5
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"


class TestCompoundInterestSemiannual:
    """Test compound interest with semiannual compounding."""

    def test_10k_5percent_1year(self):
        """€10,000 at 5% for 1 year, semiannual (n=2)."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("1"),
            frequency=MaturationFrequency.SEMIANNUAL,
            )
        # A = 10000 * (1 + 0.05/2)^(2*1) = 10000 * (1.025)^2 = 10000 * 1.050625 = 10506.25
        # I = 506.25
        expected = Decimal("506.25")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_half_year(self):
        """€10,000 at 5% for 0.5 years, semiannual."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("0.5"),
            frequency=MaturationFrequency.SEMIANNUAL,
            )
        # A = 10000 * (1.025)^1 = 10250
        # I = 250
        expected = Decimal("250")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_2years(self):
        """€10,000 at 5% for 2 years, semiannual."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("2"),
            frequency=MaturationFrequency.SEMIANNUAL,
            )
        # A = 10000 * (1.025)^4 = 10000 * 1.10381289062 = 11038.1289062
        # I = 1038.1289062...
        base = Decimal("1") + Decimal("0.05") / Decimal("2")
        exponent = 4
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"


class TestCompoundInterestQuarterly:
    """Test compound interest with quarterly compounding."""

    def test_10k_5percent_1year(self):
        """€10,000 at 5% for 1 year, quarterly (n=4)."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("1"),
            frequency=MaturationFrequency.QUARTERLY,
            )
        # A = 10000 * (1 + 0.05/4)^4 = 10000 * (1.0125)^4
        base = Decimal("1") + Decimal("0.05") / Decimal("4")
        exponent = 4
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_2years(self):
        """€10,000 at 5% for 2 years, quarterly."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("2"),
            frequency=MaturationFrequency.QUARTERLY,
            )
        # A = 10000 * (1.0125)^8
        base = Decimal("1") + Decimal("0.05") / Decimal("4")
        exponent = 8
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"


class TestCompoundInterestMonthly:
    """Test compound interest with monthly compounding."""

    def test_10k_5percent_1year(self):
        """€10,000 at 5% for 1 year, monthly (n=12)."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("1"),
            frequency=MaturationFrequency.MONTHLY,
            )
        # A = 10000 * (1 + 0.05/12)^12
        base = Decimal("1") + Decimal("0.05") / Decimal("12")
        exponent = 12
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_2years(self):
        """€10,000 at 5% for 2 years, monthly."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("2"),
            frequency=MaturationFrequency.MONTHLY,
            )
        # A = 10000 * (1 + 0.05/12)^24
        base = Decimal("1") + Decimal("0.05") / Decimal("12")
        exponent = 24
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"


class TestCompoundInterestDaily:
    """Test compound interest with daily compounding."""

    def test_10k_5percent_1year(self):
        """€10,000 at 5% for 1 year (365 days), daily (n=365)."""
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=Decimal("1"),
            frequency=MaturationFrequency.DAILY,
            )
        # A = 10000 * (1 + 0.05/365)^365
        base = Decimal("1") + Decimal("0.05") / Decimal("365")
        exponent = 365
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"

    def test_10k_5percent_30days(self):
        """€10,000 at 5% for 30 days, daily."""
        time_fraction = Decimal("30") / Decimal("365")
        result = calculate_compound_interest(
            principal=Decimal("10000"),
            annual_rate=Decimal("0.05"),
            time_fraction=time_fraction,
            frequency=MaturationFrequency.DAILY,
            )
        # A = 10000 * (1 + 0.05/365)^(365 * 30/365) = 10000 * (1 + 0.05/365)^30
        base = Decimal("1") + Decimal("0.05") / Decimal("365")
        exponent = 30
        multiplier = Decimal(str(pow(float(base), exponent)))
        expected = Decimal("10000") * multiplier - Decimal("10000")
        assert result == expected, f"Expected {expected}, got {result}"




class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_rate(self):
        """Rate 0% should return 0 interest."""
        result_simple = calculate_simple_interest(Decimal("10000"), Decimal("0"), Decimal("1"))
        assert result_simple == Decimal("0")

        result_compound = calculate_compound_interest(
            Decimal("10000"), Decimal("0"), Decimal("1"), MaturationFrequency.MONTHLY
            )
        assert result_compound == Decimal("0")

    def test_zero_time(self):
        """Time 0 should return 0 interest."""
        result_simple = calculate_simple_interest(Decimal("10000"), Decimal("0.05"), Decimal("0"))
        assert result_simple == Decimal("0")

        result_compound = calculate_compound_interest(
            Decimal("10000"), Decimal("0.05"), Decimal("0"), MaturationFrequency.MONTHLY
            )
        assert result_compound == Decimal("0")

    def test_zero_principal(self):
        """Principal 0 should return 0 interest."""
        result_simple = calculate_simple_interest(Decimal("0"), Decimal("0.05"), Decimal("1"))
        assert result_simple == Decimal("0")

        result_compound = calculate_compound_interest(
            Decimal("0"), Decimal("0.05"), Decimal("1"), MaturationFrequency.MONTHLY
            )
        assert result_compound == Decimal("0")

    def test_very_small_amounts(self):
        """Test with very small principal amounts."""
        result = calculate_simple_interest(Decimal("0.01"), Decimal("0.05"), Decimal("1"))
        expected = Decimal("0.0005")
        assert result == expected, f"Expected {expected}, got {result}"


class TestCompoundingPeriodsHelper:
    """Test get_compounding_periods_per_year helper function."""

    def test_all_frequencies(self):
        """Verify all frequency values."""
        assert get_compounding_periods_per_year(MaturationFrequency.DAILY) == 365
        assert get_compounding_periods_per_year(MaturationFrequency.WEEKLY) == 52
        assert get_compounding_periods_per_year(MaturationFrequency.MONTHLY) == 12
        assert get_compounding_periods_per_year(MaturationFrequency.QUARTERLY) == 4
        assert get_compounding_periods_per_year(MaturationFrequency.SEMIANNUAL) == 2
        assert get_compounding_periods_per_year(MaturationFrequency.ANNUAL) == 1



class TestComparisonSimpleVsCompound:
    """Compare simple vs compound interest to verify implementation."""

    def test_compound_annual_equals_simple_1year(self):
        """For 1 year, annual compounding equals simple interest."""
        principal = Decimal("10000")
        rate = Decimal("0.05")
        time = Decimal("1")

        simple = calculate_simple_interest(principal, rate, time)
        compound = calculate_compound_interest(principal, rate, time, MaturationFrequency.ANNUAL)

        assert simple == compound, f"Simple: {simple}, Compound: {compound}"

    def test_compound_always_higher_than_simple(self):
        """For multi-period, compound should be higher than simple."""
        principal = Decimal("10000")
        rate = Decimal("0.05")
        time = Decimal("2")

        simple = calculate_simple_interest(principal, rate, time)  # 1000
        compound_annual = calculate_compound_interest(
            principal, rate, time, MaturationFrequency.ANNUAL
            )  # 1025
        compound_monthly = calculate_compound_interest(
            principal, rate, time, MaturationFrequency.MONTHLY
            )

        assert (
            compound_annual > simple
        ), f"Compound annual ({compound_annual}) should be > simple ({simple})"
        assert (
            compound_monthly > compound_annual
        ), f"Compound monthly ({compound_monthly}) should be > annual ({compound_annual})"

    def test_higher_frequency_yields_more_interest(self):
        """Higher compounding frequency yields more interest."""
        principal = Decimal("10000")
        rate = Decimal("0.05")
        time = Decimal("1")

        annual = calculate_compound_interest(principal, rate, time, MaturationFrequency.ANNUAL)
        semiannual = calculate_compound_interest(
            principal, rate, time, MaturationFrequency.SEMIANNUAL
            )
        quarterly = calculate_compound_interest(principal, rate, time, MaturationFrequency.QUARTERLY)
        monthly = calculate_compound_interest(principal, rate, time, MaturationFrequency.MONTHLY)
        daily = calculate_compound_interest(principal, rate, time, MaturationFrequency.DAILY)

        # Each should be progressively higher
        assert semiannual > annual
        assert quarterly > semiannual
        assert monthly > quarterly
        assert daily > monthly


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
