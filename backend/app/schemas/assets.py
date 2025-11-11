from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, field_validator


class CommonConfig:
    model_config = ConfigDict(extra="forbid", json_schema_extra={"examples": []})


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

    Represents a time period with a specific interest rate.
    Used in interest_schedule arrays.

    Attributes:
        start_date: Period start date (inclusive)
        end_date: Period end date (inclusive)
        rate: Annual interest rate as decimal (e.g., 0.05 for 5%)

    Example:
        {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "rate": "0.05"  # 5% annual rate
        }
    """
    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    rate: Decimal

    @field_validator("rate", mode="before")
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


class LateInterestConfig(BaseModel):
    """
    Late interest configuration for scheduled investments.

    Defines the penalty interest rate and grace period applied
    after the asset's maturity date.

    Attributes:
        rate: Annual late interest rate as decimal (e.g., 0.12 for 12%)
        grace_period_days: Number of days after maturity before late interest applies

    Example:
        {
            "rate": "0.12",  # 12% annual late interest
            "grace_period_days": 30  # 30 days grace period
        }
    """
    model_config = ConfigDict(extra="forbid")

    rate: Decimal
    grace_period_days: int = 0

    @field_validator("rate", mode="before")
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
    "BackwardFillInfo",
    "CurrentValueModel",
    "PricePointModel",
    "HistoricalDataModel",
    "AssetProviderAssignmentModel",
    # Scheduled investment schemas
    "InterestRatePeriod",
    "LateInterestConfig",
    "ScheduledInvestmentParams",
    ]
