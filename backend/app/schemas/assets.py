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
- Scheduled Investment: FAInterestRatePeriod, FALateInterestConfig, FAScheduledInvestmentSchedule
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.db.models import AssetType, IdentifierType
# Import from common and prices modules
from backend.app.schemas.common import BackwardFillInfo, BaseDeleteResult, BaseBulkResponse, OldNew, Currency
from backend.app.schemas.prices import FACurrentValue, FAPricePoint, FAHistoricalData
from backend.app.schemas.provider import FAProviderRefreshFieldsDetail
from backend.app.utils.geo_utils import normalize_country_keys
from backend.app.utils.sector_fin_utils import normalize_sector
from backend.app.utils.validation_utils import validate_compound_frequency


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


# ============================================================================
# ASSET METADATA & CLASSIFICATION
# ============================================================================

# ============================================================================
# DISTRIBUTION BASE MODELS
# ============================================================================

class BaseDistribution(BaseModel):
    """
    Base class for distribution models (geographic, sector, etc.).

    Handles common validation:
    - Weights must be Decimal with 4 decimal places
    - Weights must sum to 1.0 (±1e-6 tolerance)
    - Auto-renormalization if sum != 1.0
    - Quantization with ROUND_HALF_EVEN

    Child classes must override validate_distribution() to normalize keys
    before calling parent validation via _validate_and_normalize_weights().
    """
    model_config = ConfigDict(extra="forbid")

    distribution: dict[str, Decimal] = Field(..., description="Distribution weights (must sum to 1.0)")

    @classmethod
    def _validate_and_normalize_weights(
        cls,
        weights: dict[str, Decimal],
        allow_empty: bool = False
        ) -> dict[str, Decimal]:
        """
        Common validation logic for distribution weights.

        This method:
        1. Validates weights are non-negative
        2. Quantizes to 4 decimals (ROUND_HALF_EVEN)
        3. Validates sum is ~1.0 (tolerance: 1e-6)
        4. Renormalizes if needed (adjusts smallest weight)

        Args:
            weights: Dictionary of weights (keys must already be normalized)
            allow_empty: Whether to allow empty distributions

        Returns:
            Normalized and quantized weights summing to exactly 1.0

        Raises:
            ValueError: If validation fails
        """
        if not weights and not allow_empty:
            raise ValueError("Distribution cannot be empty")

        if not weights:
            return {}

        # First pass: convert to Decimal and validate non-negative
        quantizer = Decimal('0.0001')
        parsed_weights = {}

        for key, weight in weights.items():
            # Ensure it's a Decimal
            if not isinstance(weight, Decimal):
                weight = Decimal(str(weight))

            # Check non-negative
            if weight < 0:
                raise ValueError(f"Weight for '{key}' cannot be negative: {weight}")

            parsed_weights[key] = weight

        # Check if sum is zero (can't normalize)
        raw_total = sum(parsed_weights.values())
        if raw_total == Decimal('0'):
            raise ValueError("Distribution weights sum to zero")

        target = Decimal('1.0')
        tolerance = Decimal('0.01')  # Allow up to 1% deviation before rejecting

        # Check if raw sum is too far from 1.0 to be a rounding issue
        if abs(raw_total - target) > tolerance:
            raise ValueError(
                f"Distribution weights must sum to approximately 1.0 (±{tolerance}). "
                f"Current sum: {raw_total} (difference: {abs(raw_total - target)})"
                )

        # Normalize weights to sum to exactly 1.0, then quantize
        quantized = {}
        for key, weight in parsed_weights.items():
            normalized = (weight / raw_total).quantize(quantizer, rounding=ROUND_HALF_EVEN)
            quantized[key] = normalized

        # Calculate sum after quantization
        total = sum(quantized.values())

        # Fine-tune to ensure exactly 1.0
        if total != target:
            # Adjust the smallest weight
            min_key = min(quantized, key=quantized.get)
            adjustment = target - total
            adjusted_weight = quantized[min_key] + adjustment

            if adjusted_weight < 0:
                raise ValueError(
                    f"Cannot renormalize: adjustment would make weight negative. "
                    f"Key: {min_key}, Original: {quantized[min_key]}, Adjustment: {adjustment}"
                    )

            quantized[min_key] = adjusted_weight

        # Final validation
        final_sum = sum(quantized.values())
        if final_sum != target:
            raise ValueError(
                f"Internal error: final sum is {final_sum} after renormalization (expected {target})"
                )

        return quantized


class FAGeographicArea(BaseDistribution):
    """
    Geographic area distribution with ISO-3166-A3 validation.

    Extends BaseDistribution with country code normalization.
    Keys must be ISO-3166-A3 country codes (or names/ISO-2 that will be normalized).

    Examples:
        >>> geo = FAGeographicArea(distribution={"USA": Decimal("0.6"), "ITA": Decimal("0.4")})
        >>> geo.distribution
        {'USA': Decimal('0.6000'), 'ITA': Decimal('0.4000')}

        >>> geo = FAGeographicArea(distribution={"US": 0.5, "Italy": 0.5})
        >>> geo.distribution
        {'USA': Decimal('0.5000'), 'ITA': Decimal('0.5000')}
    """

    @field_validator("distribution")
    @classmethod
    def validate_distribution(cls, v):
        """
        Validate and normalize geographic area distribution.

        Process:
        1. Normalize country keys to ISO-3166-A3 (geo_normalization)
        2. Validate and normalize weights (BaseDistribution)
        """
        if not v:
            raise ValueError("Geographic distribution cannot be empty")

        # Step 1: Normalize country codes
        normalized_countries = normalize_country_keys(v)

        # Step 2: Validate and normalize weights
        return cls._validate_and_normalize_weights(normalized_countries)


class FASectorArea(BaseDistribution):
    """
    Sector allocation distribution with standard classification.

    Validates sector names against FinancialSector enum:
    - Industrials, Technology, Financials, Consumer Discretionary,
      Health Care, Real Estate, Basic Materials, Energy, Consumer Staples,
      Telecommunication, Utilities, Other

    Unknown sectors are mapped to "Other" with warning log.
    Weights are automatically merged if multiple input keys map to same sector.

    Examples:
        >>> sector_dist = FASectorArea(distribution={
        ...     "Technology": Decimal("0.35"),
        ...     "Financials": Decimal("0.25"),
        ...     "Health Care": Decimal("0.40")
        ... })

        >>> # Aliases and case-insensitive
        >>> sector_dist = FASectorArea(distribution={
        ...     "technology": 0.3,
        ...     "healthcare": 0.3,  # Will be normalized to "Health Care"
        ...     "FINANCIALS": 0.4
        ... })
    """

    @field_validator("distribution")
    @classmethod
    def validate_distribution(cls, v):
        """
        Validate and normalize sector distribution.

        Process:
        1. Normalize sector names using FinancialSector enum
        2. Merge weights for sectors that map to same standard name
        3. Validate and normalize weights (BaseDistribution)
        """
        if not v:
            raise ValueError("Sector distribution cannot be empty")

        # Step 1: Normalize sector names and merge weights
        normalized_sectors: dict[str, Decimal] = {}

        for sector_name, weight in v.items():
            # Normalize sector name using enum
            normalized_name = normalize_sector(sector_name)

            # Parse to Decimal if needed
            if not isinstance(weight, Decimal):
                weight = Decimal(str(weight))

            # Merge weights if multiple keys map to same sector
            if normalized_name in normalized_sectors:
                normalized_sectors[normalized_name] += weight
            else:
                normalized_sectors[normalized_name] = weight

        # Step 2: Validate and normalize weights
        return cls._validate_and_normalize_weights(normalized_sectors)


class FAClassificationParams(BaseModel):
    """
    Asset classification metadata.

    All fields optional (partial updates supported via PATCH).
    geographic_area and sector_area are indivisible blocks (full replace on update, no merge).

    Validation:
    - geographic_area: ISO-3166-A3 codes, weights must sum to 1.0 (±1e-6)
    - sector_area: Standard FinancialSector enum values, weights must sum to 1.0 (±1e-6)
    - Weights quantized to 4 decimals (ROUND_HALF_EVEN)
    - Automatic renormalization if sum != 1.0

    Examples:
        >>> params = FAClassificationParams(
        ...     short_description="Apple Inc. - Technology company",
        ...     geographic_area=FAGeographicArea(distribution={"USA": Decimal("0.6"), "EUR": Decimal("0.4")}),
        ...     sector_area=FASectorArea(distribution={"Technology": Decimal("1.0")})
        ... )
    """
    model_config = ConfigDict(extra="forbid")

    short_description: Optional[str] = None
    geographic_area: Optional[FAGeographicArea] = None
    sector_area: Optional[FASectorArea] = None


class FAAssetMetadataResponse(BaseModel):
    """
    Asset with metadata fields.

    Used for GET/PATCH responses and bulk read operations.

    Fields:
    - asset_id: Asset database ID
    - display_name: User-friendly asset name
    - currency: Asset currency code
    - icon_url: Asset icon URL (optional)
    - asset_type: Asset type (STOCK, BOND, ETF, etc.)
    - classification_params: Optional classification metadata
    - has_provider: Whether asset has pricing provider assigned
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    display_name: str
    currency: str
    icon_url: Optional[str] = None
    asset_type: Optional[str] = None
    classification_params: Optional[FAClassificationParams] = None
    has_provider: bool = False


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
    Includes fields_detail with old/new values for each refreshed field.
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    success: bool
    message: str
    fields_detail: Optional["FAProviderRefreshFieldsDetail"] = Field(None, description="Details of refreshed fields with old/new values")
    warnings: Optional[List[str]] = None


class FABulkMetadataRefreshResponse(BaseBulkResponse[FAMetadataRefreshResult]):
    """Bulk metadata refresh response (partial success).

    Each result includes fields_detail with:
    - refreshed_fields: List[OldNew[str]] with old/new values
    - missing_data_fields: Fields provider didn't return
    - ignored_fields: Fields skipped (future use)
    """
    pass


# ============================================================================
# ASSET CRUD SCHEMAS
# ============================================================================

class FAAssetCreateItem(BaseModel):
    """Single asset to create in bulk operation.

    Identifier fields (identifier_isin, identifier_ticker, etc.) are stored directly on Asset.
    Provider assignment can be done separately via POST /assets/provider.
    """
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., description="Human-readable asset name (must be unique)")
    currency: str = Field(..., min_length=3, max_length=3, description="Asset currency (ISO 4217)")
    asset_type: Optional[AssetType] = Field(None, description="Asset type (STOCK, ETF, BOND, CROWDFUND_LOAN, etc.)")
    icon_url: Optional[str] = Field(None, description="URL to asset icon (local or remote)")

    # Classification metadata (optional)
    classification_params: Optional[FAClassificationParams] = Field(None, description="Asset classification metadata")

    # Identifier fields (one per IdentifierType) - optional
    identifier_isin: Optional[str] = Field(None, max_length=12, description="ISIN code (12 chars)")
    identifier_ticker: Optional[str] = Field(None, max_length=20, description="Ticker symbol")
    identifier_cusip: Optional[str] = Field(None, max_length=9, description="CUSIP code (9 chars)")
    identifier_sedol: Optional[str] = Field(None, max_length=7, description="SEDOL code (7 chars)")
    identifier_figi: Optional[str] = Field(None, max_length=12, description="FIGI code (12 chars)")
    identifier_uuid: Optional[str] = Field(None, max_length=36, description="UUID for custom assets")
    identifier_other: Optional[str] = Field(None, max_length=100, description="Other identifier")

    @field_validator('currency')
    @classmethod
    def currency_uppercase(cls, v: str) -> str:
        return Currency.validate_code(v)

    @field_validator('identifier_isin')
    @classmethod
    def validate_isin(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize ISIN."""
        if v is None or v == '':
            return None
        v = v.strip().upper()
        if len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        return v

    @field_validator('identifier_ticker')
    @classmethod
    def validate_ticker(cls, v: Optional[str]) -> Optional[str]:
        """Normalize ticker to uppercase."""
        if v is None or v == '':
            return None
        return v.strip().upper()


class FAAssetCreateResult(BaseModel):
    """Result of single asset creation in bulk operation."""
    model_config = ConfigDict(extra="forbid")

    asset_id: Optional[int] = Field(None, description="Created asset ID (null if failed)")
    success: bool = Field(..., description="Whether creation succeeded")
    message: str = Field(..., description="Success message or error description")
    display_name: str = Field(..., description="Asset display name (for identification)")


class FABulkAssetCreateResponse(BaseBulkResponse[FAAssetCreateResult]):
    """Bulk asset creation response (partial success allowed)."""
    # Inherits from BaseBulkResponse:
    # - results: List[FAAssetCreateResult]
    # - success_count: int
    # - errors: List[str]
    # Computed properties:
    # - failed_count: int (computed from len(results) - success_count)
    # - total_count: int
    pass


class FAAinfoFiltersRequest(BaseModel):
    """Filters for asset list query - enhanced for BRIM asset matching.

    Supports exact match on all identifier columns (one per IdentifierType):
    - isin, ticker, cusip, sedol, figi, uuid: exact match
    - identifier_other: partial match (LIKE)
    - identifier_contains: partial match across ALL identifier columns
    """
    model_config = ConfigDict(extra="forbid")

    # Filters with proper validation
    currency: Optional[str] = Field(None, description="Filter by currency (ISO 4217)")
    asset_type: Optional[AssetType] = Field(None, description="Filter by asset type enum")
    active: bool = Field(True, description="Include only active assets (default: true)")

    # Search in display_name (partial match)
    search: Optional[str] = Field(None, description="Search in display_name (partial match)")

    # Identifier-based exact search (one per IdentifierType)
    isin: Optional[str] = Field(None, description="Exact ISIN match (Asset.identifier_isin)")
    ticker: Optional[str] = Field(None, description="Exact ticker/symbol match (Asset.identifier_ticker)")
    cusip: Optional[str] = Field(None, description="Exact CUSIP match (Asset.identifier_cusip)")
    sedol: Optional[str] = Field(None, description="Exact SEDOL match (Asset.identifier_sedol)")
    figi: Optional[str] = Field(None, description="Exact FIGI match (Asset.identifier_figi)")
    uuid: Optional[str] = Field(None, description="Exact UUID match (Asset.identifier_uuid)")

    # identifier_other uses partial match (LIKE) since it can contain anything
    identifier_other: Optional[str] = Field(None, description="Partial match in identifier_other")

    # Partial match across ALL identifier columns
    identifier_contains: Optional[str] = Field(None, description="Partial match in any identifier field")

    @field_validator('currency')
    @classmethod
    def validate_currency_code(cls, v: Optional[str]) -> Optional[str]:
        """Validate currency using Currency.validate_code()."""
        if v is None:
            return None
        return Currency.validate_code(v)

    @field_validator('isin')
    @classmethod
    def validate_isin_format(cls, v: Optional[str]) -> Optional[str]:
        """Normalize ISIN to uppercase."""
        if v is None:
            return None
        return v.strip().upper()

    @field_validator('ticker', 'cusip', 'sedol', 'figi')
    @classmethod
    def validate_identifier_uppercase(cls, v: Optional[str]) -> Optional[str]:
        """Normalize identifier to uppercase."""
        if v is None:
            return None
        return v.strip().upper()


class FAinfoResponse(BaseModel):
    """Single asset info - enhanced with identifier data for BRIM and frontend."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="Asset ID")
    display_name: str = Field(..., description="Asset display name")
    currency: str = Field(..., description="Asset currency")
    icon_url: Optional[str] = Field(None, description="Asset icon URL")
    asset_type: Optional[str] = Field(None, description="Asset type")
    active: bool = Field(..., description="Whether asset is active")
    has_provider: bool = Field(..., description="Whether asset has a provider assigned")
    has_metadata: bool = Field(..., description="Whether asset has classification metadata")

    # Identifier columns (one per IdentifierType)
    identifier_isin: Optional[str] = Field(None, description="ISIN code")
    identifier_ticker: Optional[str] = Field(None, description="Ticker symbol")
    identifier_cusip: Optional[str] = Field(None, description="CUSIP code")
    identifier_sedol: Optional[str] = Field(None, description="SEDOL code")
    identifier_figi: Optional[str] = Field(None, description="FIGI code")
    identifier_uuid: Optional[str] = Field(None, description="UUID for custom assets")
    identifier_other: Optional[str] = Field(None, description="Other identifier")

    # Legacy fields for backward compatibility with provider assignment
    identifier: Optional[str] = Field(None, description="Primary identifier (from provider assignment)")
    identifier_type: Optional[IdentifierType] = Field(None, description="Primary identifier type")


class FAAssetDeleteResult(BaseDeleteResult):
    """Result of single asset deletion in bulk operation."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    # Inherits from BaseDeleteResult:
    # - success: bool
    # - deleted_count: int (always 0 or 1 for single asset)
    # - message: Optional[str]


class FABulkAssetDeleteResponse(BaseBulkResponse[FAAssetDeleteResult]):
    """Bulk asset deletion response (partial success allowed)."""
    pass


# ============================================================================
# ASSET PATCH SCHEMAS (for PATCH /assets endpoint)
# ============================================================================

class FAAssetPatchItem(BaseModel):
    """Single asset patch item for bulk update operations.

    Merge logic:
    - Field present in patch (even if None): UPDATE or BLANK
    - Field absent in patch: IGNORE (keep existing value)

    For classification_params:
    - If None: Set DB column to NULL
    - If present: Full replace (no merge of subfields)
    """
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID to update")

    # Optional fields - if present (even if None), they will be updated
    display_name: Optional[str] = Field(None, description="Update display name")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Update currency (ISO 4217)")
    asset_type: Optional[AssetType] = Field(None, description="Update asset type (STOCK, ETF, BOND, etc.)")
    icon_url: Optional[str] = Field(None, description="Update icon URL (None = clear)")
    classification_params: Optional[FAClassificationParams] = Field(None, description="Update classification (None = clear)")
    active: Optional[bool] = Field(None, description="Update active status")

    # Identifier fields (one per IdentifierType)
    identifier_isin: Optional[str] = Field(None, max_length=12, description="Update ISIN code")
    identifier_ticker: Optional[str] = Field(None, max_length=20, description="Update ticker symbol")
    identifier_cusip: Optional[str] = Field(None, max_length=9, description="Update CUSIP code")
    identifier_sedol: Optional[str] = Field(None, max_length=7, description="Update SEDOL code")
    identifier_figi: Optional[str] = Field(None, max_length=12, description="Update FIGI code")
    identifier_uuid: Optional[str] = Field(None, max_length=36, description="Update UUID")
    identifier_other: Optional[str] = Field(None, max_length=100, description="Update other identifier")

    @field_validator('currency')
    @classmethod
    def currency_uppercase(cls, v: Optional[str]) -> Optional[str]:
        """Normalize currency to uppercase."""
        return Currency.validate_code(v) if v else None

    @field_validator('identifier_isin')
    @classmethod
    def validate_isin(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize ISIN."""
        if v is None or v == '':
            return None
        v = v.strip().upper()
        if len(v) != 12:
            raise ValueError("ISIN must be 12 characters")
        return v

    @field_validator('identifier_ticker')
    @classmethod
    def validate_ticker(cls, v: Optional[str]) -> Optional[str]:
        """Normalize ticker to uppercase."""
        if v is None or v == '':
            return None
        return v.strip().upper()


class FAAssetPatchResult(BaseModel):
    """Result of single asset patch in bulk operation."""
    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset ID")
    success: bool = Field(..., description="Whether patch succeeded")
    message: str = Field(..., description="Success message or error description")
    updated_fields: Optional[List[OldNew[str | None]]] = Field(None, description="List of fields updated: [{info: field, old: old_value, new: new_value}]")


class FABulkAssetPatchResponse(BaseBulkResponse[FAAssetPatchResult]):
    """Bulk asset patch response (partial success allowed)."""
    pass


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
    # Distribution base models
    "BaseDistribution",
    # Metadata & classification
    "FAGeographicArea",
    "FASectorArea",
    "FAClassificationParams",
    "FAAssetMetadataResponse",
    "FAMetadataChangeDetail",
    "FAMetadataRefreshResult",
    "FABulkMetadataRefreshResponse",
    # Asset CRUD schemas
    "FAAssetCreateItem",
    "FAAssetCreateResult",
    "FABulkAssetCreateResponse",
    "FAAinfoFiltersRequest",
    "FAinfoResponse",
    "FAAssetDeleteResult",
    "FABulkAssetDeleteResponse",
    # Asset PATCH schemas
    "FAAssetPatchItem",
    "FABulkAssetPatchResponse",
    "FAAssetPatchResult",
    ]
