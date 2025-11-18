"""
Financial Asset (FA) Core Schemas.

This module contains Pydantic models for Financial Assets domain, including
price points, asset metadata, and scheduled investment calculations.

**Naming Conventions**:
- FA domain: Financial Assets (stocks, ETFs, bonds, P2P loans, etc.)
- No FA prefix on base models (PricePointModel, not FAPricePointModel)
  because these are foundational schemas used throughout FA system

**Domain Coverage**:
- Price points: OHLC data with volume and backward-fill info
- Current values: Latest available price/valuation
- Historical data: Time series of price points
- Provider assignments: Asset-to-provider mappings
- Scheduled investments: Interest schedules for bonds/loans (synthetic yield)

**Design Notes**:
- No backward compatibility maintained during refactoring
- All numeric fields use Decimal for precision
- Pydantic v2 with strict validation (extra="forbid")
- Scheduled investment uses Pydantic models (not dict configs)
- Enums for compounding types, frequencies, and day count conventions

**Structure**:
- Enums: Financial calculation types (compounding, frequencies, day counts)
- Base models: PricePointModel, CurrentValueModel, HistoricalDataModel
- Provider: AssetProviderAssignmentModel
- Scheduled Investment: InterestRatePeriod, LateInterestConfig, ScheduledInvestmentSchedule, ScheduledInvestmentParams
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, field_validator


class CommonConfig:
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": []})


# ============================================================================
# ENUMS FOR FINANCIAL CALCULATIONS
# ============================================================================

class CompoundingType(str, Enum):
    """
    Interest compounding type.

    - SIMPLE: Interest calculated on principal only (I = P * r * t)
    - COMPOUND: Interest calculated on principal + accumulated interest (A = P * (1 + r/n)^(nt))
    """
    SIMPLE = "SIMPLE"
    COMPOUND = "COMPOUND"


class CompoundFrequency(str, Enum):
    """
    Frequency of interest compounding (for COMPOUND interest).

    - DAILY: Compounds every day (n=365)
    - MONTHLY: Compounds every month (n=12)
    - QUARTERLY: Compounds every quarter (n=4)
    - SEMIANNUAL: Compounds twice a year (n=2)
    - ANNUAL: Compounds once a year (n=1)
    - CONTINUOUS: Continuous compounding (A = P * e^(rt))
    """
    DAILY = "DAILY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    SEMIANNUAL = "SEMIANNUAL"
    ANNUAL = "ANNUAL"
    CONTINUOUS = "CONTINUOUS"


class DayCountConvention(str, Enum):
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


# ============================================================================
# BASIC MODELS
# ============================================================================


class BackwardFillInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actual_rate_date: date
    days_back: int


class CurrentValueModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: Decimal
    currency: str
    as_of_date: date
    source: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def parse_decimal(cls, v):
        return Decimal(str(v))


class PricePointModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Decimal
    volume: Optional[Decimal] = None
    currency: Optional[str] = None
    backward_fill_info: Optional[BackwardFillInfo] = None

    @field_validator("open", "high", "low", "close", "volume", mode="before")
    @classmethod
    def parse_optional_decimal(cls, v):
        if v is None:
            return None
        return Decimal(str(v))


class HistoricalDataModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prices: List[PricePointModel]
    currency: Optional[str] = None
    source: Optional[str] = None


class AssetProviderAssignmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: int
    provider_code: str
    provider_params: Optional[dict] = None
    last_fetch_at: Optional[str] = None
    fetch_interval: Optional[int] = None


# ============================================================================
# SCHEDULED INVESTMENT SCHEMAS
# ============================================================================

class InterestRatePeriod(BaseModel):
    """
    Interest rate period for scheduled investments.

    Represents a time period with specific interest calculation parameters.
    Used in interest_schedule arrays.

    Attributes:
        start_date: Period start date (inclusive)
        end_date: Period end date (inclusive)
        annual_rate: Annual interest rate as decimal (e.g., 0.05 for 5%)
        compounding: Interest compounding type (SIMPLE or COMPOUND)
        compound_frequency: Compounding frequency (for COMPOUND type only)
        day_count: Day count convention for time fraction calculation

    Example (Simple interest):
        {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "annual_rate": 0.05,
            "compounding": "SIMPLE",
            "day_count": "ACT/365"
        }

    Example (Compound interest):
        {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "annual_rate": 0.05,
            "compounding": "COMPOUND",
            "compound_frequency": "MONTHLY",
            "day_count": "ACT/365"
        }
    """
    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    annual_rate: Decimal
    compounding: CompoundingType = CompoundingType.SIMPLE
    compound_frequency: Optional[CompoundFrequency] = None
    day_count: DayCountConvention = DayCountConvention.ACT_365

    @field_validator("annual_rate", mode="before")
    @classmethod
    def parse_rate(cls, v):
        """Convert rate to Decimal and validate it's non-negative."""
        rate = Decimal(str(v))
        if rate < 0:
            raise ValueError("Interest rate must be non-negative")
        return rate

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        """Ensure end_date is not before start_date."""
        if "start_date" in info.data and v < info.data["start_date"]:
            raise ValueError("end_date must be on or after start_date")
        return v

    @field_validator("compound_frequency")
    @classmethod
    def validate_compound_frequency(cls, v, info):
        """Ensure compound_frequency is provided when compounding is COMPOUND."""
        if "compounding" in info.data:
            if info.data["compounding"] == CompoundingType.COMPOUND and v is None:
                raise ValueError("compound_frequency is required when compounding is COMPOUND")
            if info.data["compounding"] == CompoundingType.SIMPLE and v is not None:
                raise ValueError("compound_frequency should not be set when compounding is SIMPLE")
        return v


class LateInterestConfig(BaseModel):
    """
    Late interest configuration for scheduled investments.

    Defines the penalty interest rate and grace period applied
    after the asset's maturity date.

    Attributes:
        annual_rate: Annual late interest rate as decimal (e.g., 0.12 for 12%)
        grace_period_days: Number of days after maturity before late interest applies
        compounding: Interest compounding type (default: SIMPLE)
        compound_frequency: Compounding frequency (for COMPOUND type only)
        day_count: Day count convention (default: ACT/365)

    Example:
        {
            "annual_rate": 0.12,
            "grace_period_days": 30,
            "compounding": "SIMPLE",
            "day_count": "ACT/365"
        }
    """
    model_config = ConfigDict(extra="forbid")

    annual_rate: Decimal
    grace_period_days: int = 0
    compounding: CompoundingType = CompoundingType.SIMPLE
    compound_frequency: Optional[CompoundFrequency] = None
    day_count: DayCountConvention = DayCountConvention.ACT_365

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
        """Ensure grace period is non-negative."""
        if v < 0:
            raise ValueError("Grace period must be non-negative")
        return v

    @field_validator("compound_frequency")
    @classmethod
    def validate_compound_frequency(cls, v, info):
        """Ensure compound_frequency is provided when compounding is COMPOUND."""
        if "compounding" in info.data:
            if info.data["compounding"] == CompoundingType.COMPOUND and v is None:
                raise ValueError("compound_frequency is required when compounding is COMPOUND")
            if info.data["compounding"] == CompoundingType.SIMPLE and v is not None:
                raise ValueError("compound_frequency should not be set when compounding is SIMPLE")
        return v


class ScheduledInvestmentSchedule(BaseModel):
    """
    Complete interest schedule configuration for scheduled investments.

    This is the comprehensive schema that should be stored in Asset.interest_schedule JSON field.
    It includes all periods and late interest configuration with full validation.

    Attributes:
        schedule: List of interest rate periods (must be non-overlapping and contiguous)
        late_interest: Optional late interest configuration applied after maturity

    Validation:
        - Periods must not overlap
        - Periods must not have gaps (contiguous dates)
        - Periods must be ordered by start_date
        - Each period's end_date must be before the next period's start_date (or exactly 1 day before)

    Example:
        {
            "schedule": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-06-30",
                    "annual_rate": 0.05,
                    "compounding": "SIMPLE",
                    "day_count": "ACT/365"
                },
                {
                    "start_date": "2025-07-01",
                    "end_date": "2025-12-31",
                    "annual_rate": 0.06,
                    "compounding": "SIMPLE",
                    "day_count": "ACT/365"
                }
            ],
            "late_interest": {
                "annual_rate": 0.12,
                "grace_period_days": 30,
                "compounding": "SIMPLE",
                "day_count": "ACT/365"
            }
        }
    """
    model_config = ConfigDict(extra="forbid")

    schedule: List[InterestRatePeriod]
    late_interest: Optional[LateInterestConfig] = None

    @field_validator("schedule")
    @classmethod
    def validate_schedule_continuity(cls, v):
        """Ensure schedule periods are contiguous and non-overlapping."""
        if not v:
            raise ValueError("schedule must contain at least one period")

        # Sort by start_date to ensure proper ordering
        sorted_schedule = sorted(v, key=lambda p: p.start_date)

        # Check for overlaps and gaps
        for i in range(len(sorted_schedule) - 1):
            current = sorted_schedule[i]
            next_period = sorted_schedule[i + 1]

            # Check if current end_date is before next start_date (with at most 1 day gap)
            days_gap = (next_period.start_date - current.end_date).days

            if days_gap < 0:
                raise ValueError(
                    f"Overlapping periods detected: period ending {current.end_date} "
                    f"overlaps with period starting {next_period.start_date}"
                    )
            elif days_gap > 1:
                raise ValueError(
                    f"Gap detected between periods: period ending {current.end_date} "
                    f"and period starting {next_period.start_date} ({days_gap} days gap)"
                    )

        return sorted_schedule


class ScheduledInvestmentParams(BaseModel):
    """
    Provider parameters for scheduled investment assets.

    Contains all configuration needed to calculate synthetic values
    for scheduled-yield assets like loans and bonds.

    Attributes:
        face_value: Principal amount (starting value)
        currency: ISO 4217 currency code (e.g., "EUR", "USD")
        interest_schedule: List of interest rate periods
        maturity_date: Asset maturity date
        late_interest: Optional late interest configuration

    Example:
        {
            "face_value": "10000",
            "currency": "EUR",
            "interest_schedule": [
                {
                    "start_date": "2025-01-01",
                    "end_date": "2025-12-31",
                    "rate": "0.05"
                }
            ],
            "maturity_date": "2025-12-31",
            "late_interest": {
                "rate": "0.12",
                "grace_period_days": 30
            }
        }
    """
    model_config = ConfigDict(extra="forbid")

    face_value: Decimal
    currency: str
    interest_schedule: List[InterestRatePeriod]
    maturity_date: date
    late_interest: Optional[LateInterestConfig] = None

    @field_validator("face_value", mode="before")
    @classmethod
    def parse_face_value(cls, v):
        """Convert face_value to Decimal and validate it's positive."""
        value = Decimal(str(v))
        if value <= 0:
            raise ValueError("face_value must be positive")
        return value

    @field_validator("interest_schedule")
    @classmethod
    def validate_schedule(cls, v):
        """Ensure schedule is not empty."""
        if not v:
            raise ValueError("interest_schedule must contain at least one period")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Ensure currency is provided and uppercase."""
        if not v:
            raise ValueError("currency is required")
        return v.upper()


# Export convenience
__all__ = [
    # Enums
    "CompoundingType",
    "CompoundFrequency",
    "DayCountConvention",
    # Basic models
    "BackwardFillInfo",
    "CurrentValueModel",
    "PricePointModel",
    "HistoricalDataModel",
    "AssetProviderAssignmentModel",
    # Scheduled investment schemas
    "InterestRatePeriod",
    "LateInterestConfig",
    "ScheduledInvestmentSchedule",
    "ScheduledInvestmentParams",
    ]
