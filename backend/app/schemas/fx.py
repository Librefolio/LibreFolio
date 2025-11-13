"""
FX (Foreign Exchange) Pydantic schemas.

This module contains all Pydantic v2 models for FX request/response shapes.
Used by API endpoints, services, and tests to ensure consistent validation
and serialization.

All Decimal fields are configured to serialize as strings in JSON to preserve
precision for financial calculations.
"""
# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from backend.app.schemas.common import BackwardFillInfo


# ============================================================================
# PROVIDER MODELS
# ============================================================================

class ProviderInfoModel(BaseModel):
    """Information about a single FX rate provider."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        str_strip_whitespace=True,
        )

    code: str = Field(..., description="Provider code (e.g., ECB, FED, BOE, SNB)")
    name: str = Field(..., description="Provider full name")
    base_currency: str = Field(..., description="Default base currency")
    base_currencies: list[str] = Field(..., description="All supported base currencies")
    description: str = Field(..., description="Provider description")


class ProvidersResponseModel(BaseModel):
    """Response model for listing FX providers."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    providers: list[ProviderInfoModel] = Field(..., description="List of available providers")
    count: int = Field(..., description="Number of providers")


# ============================================================================
# RATE SYNC MODELS
# ============================================================================

class SyncResponseModel(BaseModel):
    """Response model for FX rate sync operation."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    synced: int = Field(..., description="Number of new rates inserted")
    date_range: tuple[str, str] = Field(..., description="Date range synced (ISO format)")
    currencies: list[str] = Field(..., description="Currencies synced")


# ============================================================================
# CONVERSION MODELS
# ============================================================================

class ConversionRequestModel(BaseModel):
    """Single conversion request with optional date range."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        populate_by_name=True,
        str_strip_whitespace=True,
        )

    amount: Decimal = Field(..., gt=0, description="Amount to convert (must be positive)")
    from_currency: str = Field(..., alias="from", min_length=3, max_length=3, description="Source currency (ISO 4217)")
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    start_date: date = Field(..., description="Start date (required). If end_date is not provided, only this date is used")
    end_date: Optional[date] = Field(None, description="End date (optional). If provided, converts for all dates from start_date to end_date (inclusive)")

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
        """Uppercase currency codes."""
        if isinstance(v, str):
            return v.upper().strip()
        return v


class ConvertRequestModel(BaseModel):
    """Request model for bulk currency conversion."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    conversions: list[ConversionRequestModel] = Field(..., min_length=1, description="List of conversions to perform")


class ConversionResultModel(BaseModel):
    """Single conversion result."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    amount: Decimal = Field(..., description="Original amount")
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    conversion_date: str = Field(..., description="Date requested for conversion (ISO format)")
    converted_amount: Decimal = Field(..., description="Converted amount")
    rate: Optional[Decimal] = Field(None, description="Exchange rate used (if not identity)")
    backward_fill_info: Optional[BackwardFillInfo] = Field(
        None,
        description="Backward-fill info (only present if rate from a different date was used). "
                    "If null, rate_date = conversion_date"
        )


class ConvertResponseModel(BaseModel):
    """Response model for bulk currency conversion."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    results: list[ConversionResultModel] = Field(..., description="Conversion results in order")
    errors: list[str] = Field(default_factory=list, description="Errors encountered (if any)")


# ============================================================================
# RATE UPSERT MODELS
# ============================================================================

class RateUpsertItemModel(BaseModel):
    """Single rate to upsert."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        populate_by_name=True,
        str_strip_whitespace=True,
        )

    rate_date: date = Field(..., description="Date of the rate (ISO format)", alias="date")
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
        """Uppercase currency codes."""
        if isinstance(v, str):
            return v.upper().strip()
        return v


class UpsertRatesRequestModel(BaseModel):
    """Request model for bulk rate upsert."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    rates: list[RateUpsertItemModel] = Field(..., min_length=1, description="List of rates to insert/update")


class RateUpsertResultModel(BaseModel):
    """Single rate upsert result."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    success: bool = Field(..., description="Whether the operation was successful")
    action: str = Field(..., description="Action taken: 'inserted' or 'updated'")
    rate: Decimal = Field(..., description="The rate value stored")
    date: str = Field(..., description="Date of the rate (ISO format)")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")


class UpsertRatesResponseModel(BaseModel):
    """Response model for bulk rate upsert."""
    model_config = ConfigDict(
        json_encoders={Decimal: str},
        )

    results: list[RateUpsertResultModel] = Field(..., description="Upsert results in order")
    success_count: int = Field(..., description="Number of successful operations")
    errors: list[str] = Field(default_factory=list, description="Errors encountered (if any)")


# ============================================================================
# RATE DELETE MODELS
# ============================================================================

class RateDeleteRequestModel(BaseModel):
    """Single rate deletion request."""
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        )

    from_currency: str = Field(..., alias="from", min_length=3, max_length=3, description="Source currency (ISO 4217)")
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    start_date: date = Field(..., description="Start date (required). If end_date is not provided, only this date is deleted")
    end_date: Optional[date] = Field(None, description="End date (optional). If provided, deletes all dates from start_date to end_date (inclusive)")

    @field_validator('from_currency', 'to_currency', mode='before')
    @classmethod
    def uppercase_currency(cls, v):
        """Uppercase currency codes."""
        if isinstance(v, str):
            return v.upper().strip()
        return v


class DeleteRatesRequestModel(BaseModel):
    """Request model for bulk rate deletion."""
    deletions: list[RateDeleteRequestModel] = Field(..., min_length=1, description="List of rates to delete")


class RateDeleteResultModel(BaseModel):
    """Single rate deletion result."""
    success: bool = Field(..., description="Whether the operation succeeded (always True, errors are graceful)")
    base: str = Field(..., description="Base currency (normalized)")
    quote: str = Field(..., description="Quote currency (normalized)")
    start_date: str = Field(..., description="Start date (ISO format)")
    end_date: Optional[str] = Field(None, description="End date (ISO format) if range deletion")
    existing_count: int = Field(..., description="Number of rates present before deletion")
    deleted_count: int = Field(..., description="Number of rates actually deleted")
    message: Optional[str] = Field(None, description="Warning/info message (e.g., 'no rates found')")


class DeleteRatesResponseModel(BaseModel):
    """Response model for bulk rate deletion."""
    results: list[RateDeleteResultModel] = Field(..., description="Deletion results in order")
    total_deleted: int = Field(..., description="Total number of rates deleted across all requests")
    errors: list[str] = Field(default_factory=list, description="Errors encountered (if any)")


# ============================================================================
# PAIR SOURCE CONFIGURATION MODELS
# ============================================================================

class PairSourceItemModel(BaseModel):
    """Configuration for a currency pair source."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        )

    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    provider_code: str = Field(..., description="Provider code (e.g., ECB, FED)")
    priority: int = Field(..., ge=1, description="Priority (1 = primary, 2+ = fallback)")

    @field_validator('base', 'quote', mode='before')
    @classmethod
    def uppercase_currency(cls, v):
        """Uppercase currency codes."""
        if isinstance(v, str):
            return v.upper().strip()
        return v


class PairSourcesResponseModel(BaseModel):
    """Response model for listing pair sources."""
    sources: list[PairSourceItemModel] = Field(..., description="Configured pair sources")
    count: int = Field(..., description="Number of configured sources")


class CreatePairSourcesRequestModel(BaseModel):
    """Request model for creating/updating pair sources."""
    sources: list[PairSourceItemModel] = Field(..., min_length=1, description="Pair sources to create/update")


class PairSourceResultModel(BaseModel):
    """Result of a single pair source creation/update."""
    success: bool = Field(..., description="Whether the operation succeeded")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    provider_code: str = Field(..., description="Provider code")
    priority: int = Field(..., description="Priority level")
    action: str = Field(..., description="Action taken: 'created' or 'updated'")
    message: Optional[str] = Field(None, description="Additional info/warning")


class CreatePairSourcesResponseModel(BaseModel):
    """Response model for bulk pair source creation."""
    results: list[PairSourceResultModel] = Field(..., description="Results for each source")
    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(default=0, description="Number of failed operations")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")


class DeletePairSourcesRequestModel(BaseModel):
    """Request model for deleting pair sources."""
    sources: list[dict] = Field(
        ...,
        min_length=1,
        description="Pair sources to delete: [{base, quote, priority?}, ...]"
        )


class DeletePairSourceResultModel(BaseModel):
    """Result of a single pair source deletion."""
    success: bool = Field(..., description="Whether the operation succeeded")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    priority: Optional[int] = Field(None, description="Priority level (if specified)")
    deleted_count: int = Field(..., description="Number of records deleted")
    message: Optional[str] = Field(None, description="Warning/error message if any")


class DeletePairSourcesResponseModel(BaseModel):
    """Response model for DELETE /pair-sources/bulk."""
    results: list[DeletePairSourceResultModel] = Field(..., description="Results for each deletion")
    total_deleted: int = Field(..., description="Total number of records deleted")


# ============================================================================
# CURRENCY LIST MODELS
# ============================================================================

class CurrenciesResponseModel(BaseModel):
    """Response model for available currencies list."""
    currencies: list[str] = Field(..., description="List of available currency codes")
    count: int = Field(..., description="Number of available currencies")
