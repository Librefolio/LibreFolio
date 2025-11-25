"""
Financial Asset (FA) Core Schemas.

This module contains Pydantic models for Financial Assets domain, including
price points, asset metadata, and scheduled investment calculations.

**Naming Conventions**:
- FA domain: Financial Assets (stocks, ETFs, bonds, P2P loans, etc.)
- No FA prefix on base models (FAPricePoint, not FAFAPricePoint)
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
- Base models: FAPricePoint, FACurrentValue, FAHistoricalData
- Provider: FAAssetProviderAssignment
- Scheduled Investment: FAInterestRatePeriod, FALateInterestConfig, FAScheduledInvestmentSchedule, FAScheduledInvestmentParams
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import from common and prices modules
from backend.app.schemas.common import BackwardFillInfo
from backend.app.schemas.prices import FACurrentValue, FAPricePoint, FAHistoricalData
from backend.app.utils.geo_normalization import validate_and_normalize_geographic_area
from backend.app.utils.validation_utils import validate_compound_frequency, normalize_currency_code


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
# PROVIDER ASSIGNMENT
# ============================================================================
class FAAssetProviderAssignment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_id: int
    provider_code: str
    provider_params: Optional[dict] = None
    last_fetch_at: Optional[str] = None
    fetch_interval: Optional[int] = None


# ============================================================================
# SCHEDULED INVESTMENT SCHEMAS
# ============================================================================

class FAInterestRatePeriod(BaseModel):
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
    def validate_compound_frequency_field(cls, v, info):
        """Ensure compound_frequency is consistent with compounding type."""
        if "compounding" in info.data:
            validate_compound_frequency(
                compounding=info.data["compounding"].value,
                compound_frequency=v.value if v else None,
                field_name="compound_frequency"
                )
        return v


class FALateInterestConfig(BaseModel):
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
    def validate_compound_frequency_field(cls, v, info):
        """Ensure compound_frequency is consistent with compounding type."""
        if "compounding" in info.data:
            validate_compound_frequency(
                compounding=info.data["compounding"].value,
                compound_frequency=v.value if v else None,
                field_name="compound_frequency"
                )
        return v


class FAScheduledInvestmentSchedule(BaseModel):
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

    schedule: List[FAInterestRatePeriod]
    late_interest: Optional[FALateInterestConfig] = None

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


class FAScheduledInvestmentParams(BaseModel):
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
    interest_schedule: List[FAInterestRatePeriod]
    maturity_date: date
    late_interest: Optional[FALateInterestConfig] = None

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
    def currency_uppercase(cls, v):
        if not v:
            raise ValueError("currency is required")
        return normalize_currency_code(v)


# ============================================================================
# ASSET METADATA & CLASSIFICATION
# ============================================================================

class FAClassificationParams(BaseModel):
    """
    Asset classification metadata.

    All fields optional (partial updates supported via PATCH).
    geographic_area is indivisible block (full replace on update, no merge).

    Validation:
    - geographic_area: ISO-3166-A3 codes, weights must sum to 1.0 (±1e-6)
    - Weights quantized to 4 decimals (ROUND_HALF_EVEN)
    - Automatic renormalization if sum != 1.0

    Examples:
        >>> params = FAClassificationParams(
        ...     investment_type="stock",
        ...     short_description="Apple Inc. - Technology company",
        ...     geographic_area={"USA": Decimal("0.6"), "EUR": Decimal("0.4")},
        ...     sector="Technology"
        ... )
    """
    model_config = ConfigDict(extra="forbid")

    investment_type: Optional[str] = None
    short_description: Optional[str] = None
    geographic_area: Optional[dict[str, Decimal]] = None
    sector: Optional[str] = None

    @field_validator("geographic_area")
    @classmethod
    def validate_geo_area(cls, v):
        """Validate and normalize geographic area distribution."""
        if v is None:
            return None
        return validate_and_normalize_geographic_area(v)


class FAPatchMetadataRequest(BaseModel):
    """
    PATCH metadata request (partial update).

    Rules:
    - **Absent fields** (not in request JSON): ignored (no update)
    - **null in JSON** (None in Python): clear field
    - **Value present**: update field
    - **geographic_area**: full block replace (no merge)

    Examples:
        >>> # Update only short_description
        >>> patch = FAPatchMetadataRequest(short_description="New description")

        >>> # Clear sector field
        >>> patch = FAPatchMetadataRequest(sector=None)

        >>> # Update geographic_area (full replace)
        >>> patch = FAPatchMetadataRequest(
        ...     geographic_area={"USA": Decimal("1.0")}
        ... )
    """
    model_config = ConfigDict(extra="forbid")

    investment_type: Optional[str] = None
    short_description: Optional[str] = None
    geographic_area: Optional[dict[str, Decimal] | None] = None
    sector: Optional[str] = None


class FAPatchMetadataItem(BaseModel):
    """Single asset metadata patch item for bulk requests."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    patch: FAPatchMetadataRequest


class FABulkPatchMetadataRequest(BaseModel):
    """Bulk metadata patch payload matching FA bulk patterns."""
    model_config = ConfigDict(extra="forbid")

    assets: List[FAPatchMetadataItem] = Field(..., min_length=1, description="List of metadata patches")


class FAAssetMetadataResponse(BaseModel):
    """
    Asset with metadata fields.

    Used for GET/PATCH responses.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    display_name: str
    identifier: str
    currency: str
    classification_params: Optional[FAClassificationParams] = None


class FAMetadataChangeDetail(BaseModel):
    """Single field change in metadata."""
    model_config = ConfigDict(extra="forbid")

    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class FAMetadataRefreshResult(BaseModel):
    """
    Result of metadata refresh for single asset.

    Follows FA pattern: { asset_id, success, message, ... }
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    success: bool
    message: str
    changes: Optional[List[FAMetadataChangeDetail]] = None
    warnings: Optional[List[str]] = None


class FABulkAssetReadRequest(BaseModel):
    """Request to read multiple assets by IDs."""
    model_config = ConfigDict(extra="forbid")

    asset_ids: List[int]


class FABulkMetadataRefreshRequest(BaseModel):
    """Bulk metadata refresh request."""
    model_config = ConfigDict(extra="forbid")

    asset_ids: List[int]


class FABulkMetadataRefreshResponse(BaseModel):
    """
    Bulk metadata refresh response (partial success).

    Follows FA pattern: { results, success_count, failed_count }
    """
    model_config = ConfigDict(extra="forbid")

    results: List[FAMetadataRefreshResult]
    success_count: int
    failed_count: int


# ============================================================================
# ASSET CRUD SCHEMAS
# ============================================================================

class FAAssetCreateItem(BaseModel):
    """Single asset to create in bulk operation."""
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., description="Human-readable asset name")
    identifier: str = Field(..., min_length=1, description="Asset identifier (ticker, ISIN, etc.)")
    identifier_type: Optional[str] = Field(None, description="Identifier type (TICKER, ISIN, CUSIP, etc.)")
    currency: str = Field(..., min_length=3, max_length=3, description="Asset currency (ISO 4217)")
    asset_type: Optional[str] = Field(None, description="Asset type (STOCK, ETF, BOND, etc.)")
    valuation_model: Optional[str] = Field("MARKET_PRICE", description="Valuation model (MARKET_PRICE, SCHEDULED_YIELD, MANUAL)")

    # Scheduled yield fields (optional, for bonds/loans)
    # TODO: ho scoperto che face_value è usato 1 sola volta ed è inutile perchè la tabella Asset non la usa più.
    #  è necessario avviare un attività di pulizia del codice manuale per rimuovere tutti questi residui delle prime versioni da ovunque
    face_value: Optional[Decimal] = Field(None, description="Face value/principal for scheduled yield assets")
    maturity_date: Optional[date] = Field(None, description="Maturity date for scheduled yield assets")
    interest_schedule: Optional[str] = Field(None, description="Interest schedule JSON for scheduled yield assets")
    late_interest: Optional[str] = Field(None, description="Late interest policy JSON for scheduled yield assets")

    # Classification metadata (optional)
    classification_params: Optional[FAClassificationParams] = Field(None, description="Asset classification metadata")

    @field_validator('currency')
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return normalize_currency_code(v)

    @field_validator('identifier')
    @classmethod
    def identifier_not_empty(cls, v: str) -> str:
        """Ensure identifier is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("identifier cannot be empty")
        return v.strip()


class FABulkAssetCreateRequest(BaseModel):
    """Bulk asset creation request."""
    model_config = ConfigDict(extra="forbid")

    assets: List[FAAssetCreateItem] = Field(..., min_length=1, description="List of assets to create")


class FAAssetCreateResult(BaseModel):
    """Result of single asset creation in bulk operation."""
    model_config = ConfigDict(extra="forbid")

    asset_id: Optional[int] = Field(None, description="Created asset ID (null if failed)")
    success: bool = Field(..., description="Whether creation succeeded")
    message: str = Field(..., description="Success message or error description")
    display_name: str = Field(..., description="Asset display name (for identification)")
    identifier: str = Field(..., description="Asset identifier (for identification)")


class FABulkAssetCreateResponse(BaseModel):
    """Bulk asset creation response (partial success allowed)."""
    model_config = ConfigDict(extra="forbid")

    results: List[FAAssetCreateResult] = Field(..., description="Per-asset creation results")
    success_count: int = Field(..., description="Number of successfully created assets")
    failed_count: int = Field(..., description="Number of failed asset creations")


class FAAinfoFiltersRequest(BaseModel):
    """Filters for asset list query (used internally, not in request body)."""
    model_config = ConfigDict(extra="forbid")

    currency: Optional[str] = Field(None, description="Filter by currency (e.g., USD)")
    asset_type: Optional[str] = Field(None, description="Filter by asset type (e.g., STOCK)")
    valuation_model: Optional[str] = Field(None, description="Filter by valuation model (e.g., MARKET_PRICE)")
    active: bool = Field(True, description="Include only active assets (default: true)")
    search: Optional[str] = Field(None, description="Search in display_name or identifier")


class FAinfoResponse(BaseModel):
    """Single asset info, near equivalent to Asset DB model. Create new model to decouple from ORM."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="Asset ID")
    display_name: str = Field(..., description="Asset display name")
    identifier: str = Field(..., description="Asset identifier")
    identifier_type: Optional[str] = Field(None, description="Identifier type")
    currency: str = Field(..., description="Asset currency")
    asset_type: Optional[str] = Field(None, description="Asset type")
    valuation_model: Optional[str] = Field(None, description="Valuation model")
    active: bool = Field(..., description="Whether asset is active")
    has_provider: bool = Field(..., description="Whether asset has a provider assigned")
    has_metadata: bool = Field(..., description="Whether asset has classification metadata")


class FABulkAssetDeleteRequest(BaseModel):
    """Bulk asset deletion request."""
    model_config = ConfigDict(extra="forbid")

    asset_ids: List[int] = Field(..., min_length=1, description="List of asset IDs to delete")


class FAAssetDeleteResult(BaseModel):
    """Result of single asset deletion in bulk operation."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    success: bool = Field(..., description="Whether deletion succeeded")
    message: str = Field(..., description="Success message or error description")


class FABulkAssetDeleteResponse(BaseModel):
    """Bulk asset deletion response (partial success allowed)."""
    model_config = ConfigDict(extra="forbid")

    results: List[FAAssetDeleteResult] = Field(..., description="Per-asset deletion results")
    success_count: int = Field(..., description="Number of successfully deleted assets")
    failed_count: int = Field(..., description="Number of failed asset deletions")


# Export convenience
__all__ = [
    # Enums
    "CompoundingType",
    "CompoundFrequency",
    "DayCountConvention",
    # Basic models
    "BackwardFillInfo",
    "FACurrentValue",
    "FAPricePoint",
    "FAHistoricalData",
    "FAAssetProviderAssignment",
    # Scheduled investment schemas
    "FAInterestRatePeriod",
    "FALateInterestConfig",
    "FAScheduledInvestmentSchedule",
    "FAScheduledInvestmentParams",
    # Metadata & classification (NEW)
    "FAClassificationParams",
    "FAPatchMetadataRequest",
    "FAAssetMetadataResponse",
    "FAMetadataChangeDetail",
    "FAMetadataRefreshResult",
    "FABulkAssetReadRequest",
    "FABulkMetadataRefreshRequest",
    "FABulkMetadataRefreshResponse",
    "FAPatchMetadataItem",
    "FABulkPatchMetadataRequest",
    # Asset CRUD schemas
    "FAAssetCreateItem",
    "FABulkAssetCreateRequest",
    "FAAssetCreateResult",
    "FABulkAssetCreateResponse",
    "FAAinfoFiltersRequest",
    "FAinfoResponse",
    "FABulkAssetDeleteRequest",
    "FAAssetDeleteResult",
    "FABulkAssetDeleteResponse",
    ]
