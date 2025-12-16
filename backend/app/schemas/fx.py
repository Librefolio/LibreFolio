"""
Foreign Exchange (FX) Schemas.

This module contains Pydantic models for Foreign Exchange rate operations.
Covers provider info, currency conversion, rate upsert/delete, and pair sources.

**Naming Conventions**:
- FX prefix: Foreign Exchange (currency rates from central banks)
- Model suffix REMOVED during refactoring (e.g., RateUpsertItemModel → FXUpsertItem)

**Domain Coverage**:
- Provider info: FX rate provider discovery (ECB, FED, BOE, SNB)
- Conversion: Currency conversion requests and results
- Upsert: Insert/update FX rates in bulk
- Delete: Remove FX rates by date ranges
- Pair sources: Configure provider priority for currency pairs

**Design Notes**:
- No backward compatibility maintained during refactoring
- All models use Pydantic v2 with strict validation
- Decimal fields serialize as strings in JSON for precision
- FX Sync models moved to refresh.py (consolidation with FA refresh)

**Structure Differences vs FA**:
- FX: 2-level nesting (Item → Bulk) - direct item-to-bulk
- FA: 3-level nesting (Item → Asset → Bulk) - grouping by asset first
- Reason: FX rates are simpler (pair-date-rate), FA prices are complex (OHLC+volume per asset)
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel, BaseDeleteResult, BaseBulkResponse, BaseBulkDeleteResponse
from backend.app.utils.datetime_utils import parse_ISO_date
from backend.app.utils.validation_utils import normalize_currency_code


# ============================================================================
# PROVIDER MODELS
# ============================================================================

class FXProviderInfo(BaseModel):
    """Information about a single FX rate provider."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        )

    code: str = Field(..., description="Provider code (e.g., ECB, FED, BOE, SNB)")
    name: str = Field(..., description="Provider full name")
    base_currency: str = Field(..., description="Default base currency")
    base_currencies: list[str] = Field(..., description="All supported base currencies")
    description: str = Field(..., description="Provider description")
    icon_url: Optional[str] = Field(None, description="Provider icon URL (hardcoded)")



# ============================================================================
# RATE SYNC MODELS

# ============================================================================
# CONVERSION MODELS
# ============================================================================

class FXConversionRequest(BaseModel):
    """Single conversion request with date range."""
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        )

    amount: Decimal = Field(..., gt=0, description="Amount to convert (must be positive)")
    from_currency: str = Field(..., alias="from", min_length=3, max_length=3, description="Source currency (ISO 4217)")
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    date_range: DateRangeModel = Field(..., description="Date range for conversion (start required, end optional for single day)")

    @field_validator('amount', mode='before')
    @classmethod
    def coerce_amount(cls, v):
        """Coerce amount to Decimal."""
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @field_validator('from_currency', 'to_currency', mode='before')
    @classmethod
    def uppercase_currency(cls, v):
        return normalize_currency_code(v)


class FXConversionResult(BaseModel):
    """Single conversion result."""
    model_config = ConfigDict()

    amount: Decimal = Field(..., description="Original amount")
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    conversion_date: date_type = Field(..., description="Date requested for conversion (ISO format)")
    converted_amount: Decimal = Field(..., description="Converted amount")
    rate: Optional[Decimal] = Field(None, description="Exchange rate used (if not identity)")
    backward_fill_info: Optional[BackwardFillInfo] = Field(
        None,
        description="Backward-fill info (only present if rate from a different date was used). "
                    "If null, rate_date = conversion_date"
        )

    @field_validator("conversion_date", mode="before")
    @classmethod
    def _parse_conversion_date(cls, v):
        return parse_ISO_date(v)

    def conversion_date_str(self) -> str:
        """Restituisce la data in formato ISO string (YYYY-MM-DD)."""
        return self.conversion_date.isoformat()


class FXConvertResponse(BaseBulkResponse[FXConversionResult]):
    """Response model for bulk currency conversion."""
    # Inherits: results, success_count, errors
    # Note: success_count should be populated by service layer
    pass


# ============================================================================
# RATE UPSERT MODELS
# ============================================================================

class FXUpsertItem(BaseModel):
    """Single rate to upsert."""
    model_config = ConfigDict(

        populate_by_name=True,
        str_strip_whitespace=True,
        )

    rate_date: date_type = Field(..., description="Date of the rate (ISO format)", alias="date")
    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    rate: Decimal = Field(..., gt=0, description="Exchange rate (must be positive)")
    source: str = Field(default="MANUAL", description="Source of the rate")

    @field_validator('rate', mode='before')
    @classmethod
    def coerce_rate(cls, v):
        """Coerce rate to Decimal."""
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @field_validator('base', 'quote', mode='before')
    @classmethod
    def uppercase_currency(cls, v):
        return normalize_currency_code(v)



class FXUpsertResult(BaseModel):
    """Single rate upsert result."""
    model_config = ConfigDict()

    success: bool = Field(..., description="Whether the operation was successful")
    action: str = Field(..., description="Action taken: 'inserted' or 'updated'")
    rate: Decimal = Field(..., description="The rate value stored")
    date: date_type = Field(..., description="Date of the rate (ISO format)")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")

    @field_validator("date", mode="before")
    @classmethod
    def _parse_date(cls, v):
        return parse_ISO_date(v)

    def date_str(self) -> str:
        return self.date.isoformat()

class FXBulkUpsertResponse(BaseBulkResponse[FXUpsertResult]):
    """Response model for bulk rate upsert."""
    pass


# ============================================================================
# RATE DELETE MODELS
# ============================================================================

class FXDeleteItem(BaseModel):
    """Single rate deletion request."""
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        )

    from_currency: str = Field(..., alias="from", min_length=3, max_length=3, description="Source currency (ISO 4217)")
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    date_range: DateRangeModel = Field(..., description="Date range to delete (start required, end optional for single day)")

    @field_validator('from_currency', 'to_currency', mode='before')
    @classmethod
    def uppercase_currency(cls, v):
        return normalize_currency_code(v)


class FXDeleteResult(BaseDeleteResult):
    """Single FX rate deletion result."""

    base: str = Field(..., description="Base currency (normalized)")
    quote: str = Field(..., description="Quote currency (normalized)")
    date_range: DateRangeModel = Field(..., description="Date range deleted")
    existing_count: int = Field(..., description="Number of rates present before deletion")
    # Inherits from BaseDeleteResult:
    # - success: bool
    # - deleted_count: int (number of FX rates actually deleted)
    # - message: Optional[str] (e.g., 'no rates found')

class FXBulkDeleteResponse(BaseBulkDeleteResponse[FXDeleteResult]):
    """Response model for bulk FX rate deletion."""
    # Inherits from BaseBulkDeleteResponse:
    # - results: List[FXDeleteResult]
    # - success_count: int
    # - errors: List[str]
    # - total_deleted: int (total FX rates deleted)
    pass

# ============================================================================
# PAIR SOURCE CONFIGURATION MODELS
# ============================================================================

class FXPairSourceItem(BaseModel):
    """Configuration for a currency pair source."""
    model_config = ConfigDict(str_strip_whitespace=True,)

    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    provider_code: str = Field(..., description="Provider code (e.g., ECB, FED)")
    priority: int = Field(..., ge=1, description="Priority (1 = primary, 2+ = fallback)")

    @field_validator('base', 'quote', mode='before')
    @classmethod
    def uppercase_currency(cls, v):
        return normalize_currency_code(v)


class FXPairSourcesResponse(BaseModel):
    """Response model for listing pair sources."""
    sources: list[FXPairSourceItem] = Field(..., description="Configured pair sources")
    count: int = Field(..., description="Number of configured sources")




class FXPairSourceResult(BaseModel):
    """Result of a single pair source creation/update."""
    success: bool = Field(..., description="Whether the operation succeeded")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    provider_code: str = Field(..., description="Provider code")
    priority: int = Field(..., description="Priority level")
    action: str = Field(..., description="Action taken: 'created' or 'updated'")
    message: Optional[str] = Field(None, description="Additional info/warning")


class FXCreatePairSourcesResponse(BaseBulkResponse[FXPairSourceResult]):
    """Response model for bulk pair source creation."""
    # Operation-specific field
    error_count: int = Field(default=0, description="Number of failed operations")


class FXDeletePairSourceItem(BaseModel):
    """Single pair source to delete."""
    model_config = ConfigDict(str_strip_whitespace=True,)

    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    priority: Optional[int] = Field(None, ge=1, description="Priority level (optional, if not provided deletes all priorities)")

    @field_validator('base', 'quote', mode='before')
    @classmethod
    def uppercase_currency(cls, v):
        return normalize_currency_code(v)

class FXDeletePairSourceResult(BaseDeleteResult):
    """Result of a single pair source deletion."""

    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    priority: Optional[int] = Field(None, description="Priority level (if specified)")
    # Inherits from BaseDeleteResult:
    # - success: bool
    # - deleted_count: int (number of pair source records deleted)
    # - message: Optional[str]

class FXDeletePairSourcesResponse(BaseBulkDeleteResponse[FXDeletePairSourceResult]):
    """Response model for DELETE /pair-sources/bulk."""
    # Inherits from BaseBulkDeleteResponse:
    # - results: List[FXDeletePairSourceResult]
    # - success_count: int
    # - errors: List[str]
    # - total_deleted: int (total pair source records deleted)
    pass


# ============================================================================
# CURRENCY LIST MODELS
# ============================================================================

class FXCurrenciesResponse(BaseModel):
    """Response model for available currencies list."""
    currencies: list[str] = Field(..., description="List of available currency codes")
    count: int = Field(..., description="Number of available currencies")
