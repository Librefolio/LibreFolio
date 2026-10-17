"""
Scheduled investment schemas (FA): the interest schedule of an asset with predictable cash flows (bonds, P2P loans,
crowdfunding), which the ``scheduled_investment`` provider turns into synthetic prices and events.

- Enums of the financial calculations: ``MaturationFrequency``, ``DayCountConvention``, ``InterestType``.
- ``FAInterestRatePeriod``: a period of the schedule with its interest rate.
- ``FALateInterestConfig``: the late (penalty) interest after maturity.
- ``FAScheduledInvestmentSchedule``: the complete schedule configuration.
"""

# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import List, Optional

from pydantic import Field, field_validator

from backend.app.schemas.assets.events import FAAssetEventPoint
from backend.app.schemas.common import (
    Currency,
    SafeDecimal,
    StrictModel,
)

# ============================================================================
# BOUNDS (R13-SEC7-2, night decision N73)
# ============================================================================

# The schedule is generated day by day: an unbounded span is unbounded work and memory (a dry-run probe of a
# year-1-to-9999 DAILY schedule walked millions of days). 100 years cover any dated security and the model of a
# perpetual; dates outside 1900-2200 are not a live security's.
SCHEDULE_MIN_DATE = date(1900, 1, 1)
SCHEDULE_MAX_DATE = date(2200, 12, 31)
SCHEDULE_MAX_SPAN_DAYS = 36_525
SCHEDULE_MAX_PERIODS = 1_200
LATE_INTEREST_MAX_GRACE_DAYS = 36_525
# The manual events of a plan are replayed on every valuation, so their number is work too (MF-SI2, E's review of
# R13-SEC7-2): ten thousand cover the 1 200 monthly or 5 218 weekly payouts of a century, or 27 years of daily ones;
# past it the parameters are refused (INVALID_PARAMS).
SCHEDULE_MAX_EVENTS = 10_000


# ============================================================================
# ENUMS FOR FINANCIAL CALCULATIONS
# ============================================================================


class MaturationFrequency(StrEnum):
    """
    Frequency at which interest matures/accrues.

    Determines how often accrued interest is "crystallized" into the price.
    Interest is always simple: I = P * r * t (calculated on initial_value).

    - DAILY: Interest matures every day
    - WEEKLY: Interest matures every week
    - MONTHLY: Interest matures every month
    - QUARTERLY: Interest matures every quarter
    - SEMIANNUAL: Interest matures twice a year
    - ANNUAL: Interest matures once a year
    """

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMIANNUAL = "SEMIANNUAL"
    ANNUAL = "ANNUAL"


class DayCountConvention(StrEnum):
    """
    Day count convention for interest calculations.

    - ACT_365: Actual days / 365 (standard for most markets)
    - ACT_360: Actual days / 360 (common in money markets)
    - ACT_ACT: Actual days / actual days in year (365 or 366)
    - THIRTY_360: Assumes 30 days per month, 360 days per year
    """

    ACT_365 = "ACT/365"
    ACT_360 = "ACT/360"
    ACT_ACT = "ACT/ACT"
    THIRTY_360 = "30/360"


class InterestType(StrEnum):
    """
    Interest calculation method for the entire scheduled investment.

    - SIMPLE: Interest always calculated on the initial principal.
              I = P₀ * r * Δt  (P₀ is constant throughout)
    - COMPOUND: Interest calculated on the running accumulated value.
                Each day's interest adds to the base for the next day.
                I_day = V_{t-1} * r * Δt  (V grows over time)

    This is a global property of the asset — all periods use the same method.
    """

    SIMPLE = "SIMPLE"
    COMPOUND = "COMPOUND"


# ============================================================================
# SCHEDULED INVESTMENT SCHEMAS
# ============================================================================


class FAInterestRatePeriod(StrictModel):
    """
    Interest rate period for scheduled investments.

    Represents a time period with a specific interest rate.
    Interest type (simple/compound) and day count convention are
    global properties defined at the FAScheduledInvestmentSchedule level.

    Attributes:
        start_date: Period start date (inclusive)
        end_date: Period end date (inclusive)
        annual_rate: Annual interest rate as decimal (e.g., 0.05 for 5%)
        maturation_frequency: How often interest matures (DAILY, WEEKLY, MONTHLY, etc.)
        generate_interest: If True, auto-generate INTEREST events at each maturation date.
            Event value = current_value - initial_value (resets price to initial_value).
            Only generated when positive (no negative coupons).

    Example:
        {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "annual_rate": 0.05,
            "maturation_frequency": "MONTHLY",
            "generate_interest": true
        }
    """

    start_date: date
    end_date: date
    annual_rate: SafeDecimal
    maturation_frequency: MaturationFrequency = MaturationFrequency.DAILY
    generate_interest: bool = Field(default=False, description="Auto-generate INTEREST events at each maturation date. " "Event value = asset_value - initial_value (resets price to initial_value). " "Only generated if positive (no negative coupons).")

    @field_validator("annual_rate", mode="before")
    @classmethod
    def parse_rate(cls, v):
        """Convert rate to Decimal and validate it's non-negative."""
        rate = Decimal(str(v))
        if rate < 0:
            raise ValueError("Interest rate must be non-negative")
        return rate

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_bounds(cls, v):
        """A period lies between SCHEDULE_MIN_DATE and SCHEDULE_MAX_DATE."""
        if not SCHEDULE_MIN_DATE <= v <= SCHEDULE_MAX_DATE:
            raise ValueError(f"period dates must be between {SCHEDULE_MIN_DATE} and {SCHEDULE_MAX_DATE}")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date is not before start_date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be on or after start_date")
        return v


class FALateInterestConfig(StrictModel):
    """
    Late interest configuration for scheduled investments.

    Defines the penalty interest rate, grace period, interest type, and
    maturation frequency applied after the asset's maturity date.
    Day count is inherited from the parent FAScheduledInvestmentSchedule.

    Attributes:
        annual_rate: Annual late interest rate as decimal (e.g., 0.12 for 12%)
        grace_period_days: Number of days after maturity before late interest applies
        interest_type: SIMPLE or COMPOUND for late interest (default: COMPOUND — penalties grow)
        maturation_frequency: How often late interest matures/emits price points (default: DAILY)
    """

    annual_rate: SafeDecimal
    grace_period_days: int = 0
    interest_type: InterestType = Field(default=InterestType.COMPOUND, description="Interest type for late interest: SIMPLE (on principal) or COMPOUND (on accumulated value, default)")
    maturation_frequency: MaturationFrequency = Field(default=MaturationFrequency.DAILY, description="Maturation frequency for late interest period")
    generate_interest: bool = Field(default=False, description="Auto-generate INTEREST events at each late maturation date, " "plus a MATURITY_SETTLEMENT event at the end. " "After settlement, the asset produces no further price points.")

    @field_validator("annual_rate", mode="before")
    @classmethod
    def parse_rate(cls, v):
        """Convert rate to Decimal and validate it's non-negative."""
        rate = Decimal(str(v))
        if rate < 0:
            raise ValueError("Late interest rate must be non-negative")
        return rate

    @field_validator("grace_period_days")
    @classmethod
    def validate_grace_period(cls, v):
        """Ensure grace period is non-negative and at most LATE_INTEREST_MAX_GRACE_DAYS."""
        if v < 0:
            raise ValueError("Grace period must be non-negative")
        if v > LATE_INTEREST_MAX_GRACE_DAYS:
            raise ValueError(f"Grace period must be at most {LATE_INTEREST_MAX_GRACE_DAYS} days")
        return v


class FAScheduledInvestmentSchedule(StrictModel):
    """
    Complete interest schedule configuration for scheduled investments.

    This is the comprehensive schema stored in Asset.interest_schedule JSON field.
    It includes all periods, late interest configuration, and planned asset events.

    Global properties (apply to ALL periods uniformly):
        - interest_type: SIMPLE or COMPOUND (default: SIMPLE)
        - day_count: Day count convention (default: ACT/365)

    SIMPLE interest: I = P₀ * r * Δt (always on initial principal)
    COMPOUND interest: I_day = V_{t-1} * r * Δt (on running accumulated value)

    Note: day_count is constant for the entire asset. In the rare case where
    a financial instrument changes convention mid-life, the user can compute
    an equivalent rate for the new convention. This is a theoretical edge case.

    Attributes:
        initial_value: Currency object with code (e.g. 'EUR') and amount (e.g. 10000)
        interest_type: SIMPLE or COMPOUND interest calculation method
        day_count: Day count convention for time fraction calculation
        asset_events: Planned asset events (interest payouts, price adjustments)
        schedule: List of interest rate periods (must be non-overlapping and contiguous)
        late_interest: Optional late interest configuration applied after maturity

    Validation:
        - Periods must not overlap
        - Periods must not have gaps (contiguous dates)
        - Periods must be ordered by start_date
        - At most SCHEDULE_MAX_PERIODS periods, dates in [SCHEDULE_MIN_DATE, SCHEDULE_MAX_DATE], spanning at most
          SCHEDULE_MAX_SPAN_DAYS (R13-SEC7-2)

    Example:
        {
            "initial_value": {"code": "EUR", "amount": "10000"},
            "interest_type": "SIMPLE",
            "day_count": "ACT/365",
            "schedule": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-06-30",
                    "annual_rate": "0.05",
                    "maturation_frequency": "DAILY"
                },
                {
                    "start_date": "2025-07-01",
                    "end_date": "2025-12-31",
                    "annual_rate": "0.06",
                    "maturation_frequency": "MONTHLY"
                }
            ],
            "late_interest": {
                "annual_rate": "0.12",
                "grace_period_days": 30
            },
            "asset_events": [
                {
                    "date": "2025-07-01",
                    "type": "INTEREST",
                    "value": {"code": "EUR", "amount": "250"},
                    "notes": "H1 interest payout"
                }
            ]
        }
    """

    initial_value: Currency = Field(..., description="Initial capital / face value with currency (e.g., {code: 'EUR', amount: 10000})")
    interest_type: InterestType = Field(default=InterestType.SIMPLE, description="Interest calculation method: SIMPLE (on initial principal) or COMPOUND (on running value)")
    day_count: DayCountConvention = Field(default=DayCountConvention.ACT_365, description="Day count convention for time fraction calculation (global for all periods)")
    asset_events: List[FAAssetEventPoint] = Field(default_factory=list, max_length=SCHEDULE_MAX_EVENTS, description="Planned asset events (interest payouts, price adjustments); at most SCHEDULE_MAX_EVENTS (10 000)")
    schedule: List[FAInterestRatePeriod]
    late_interest: Optional[FALateInterestConfig] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule_continuity(cls, v):
        """Ensure schedule periods are contiguous and non-overlapping."""
        if not v:
            return v  # Allow empty schedule (probe returns initial_value)
        if len(v) > SCHEDULE_MAX_PERIODS:
            raise ValueError(f"A schedule has at most {SCHEDULE_MAX_PERIODS} periods, got {len(v)}")

        # Sort by start_date to ensure proper ordering
        sorted_schedule = sorted(v, key=lambda p: p.start_date)
        span_days = (max(p.end_date for p in sorted_schedule) - sorted_schedule[0].start_date).days
        if span_days > SCHEDULE_MAX_SPAN_DAYS:
            raise ValueError(f"A schedule spans at most {SCHEDULE_MAX_SPAN_DAYS} days (100 years), got {span_days}")

        # Check for overlaps and gaps
        for i in range(len(sorted_schedule) - 1):
            current = sorted_schedule[i]
            next_period = sorted_schedule[i + 1]

            # Check if current end_date is before next start_date (with at most 1 day gap)
            days_gap = (next_period.start_date - current.end_date).days

            if days_gap < 0:
                raise ValueError(f"Overlapping periods detected: period ending {current.end_date} " f"overlaps with period starting {next_period.start_date}")
            elif days_gap > 1:
                raise ValueError(f"Gap detected between periods: period ending {current.end_date} " f"and period starting {next_period.start_date} ({days_gap} days gap)")

        return sorted_schedule
