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

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from backend.app.schemas.common import (
    BackwardFillInfo,
    DateRangeModel,
    BaseDeleteResult,
    BaseBulkResponse,
    BaseBulkDeleteResponse,
    BaseListResponse,
    Currency,
    )
from backend.app.utils.datetime_utils import parse_ISO_date


# ============================================================================
# PROVIDER MODELS
# ============================================================================


class FXProviderInfo(BaseModel):
    """Information about a single FX rate provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(..., description="Provider code (e.g., ECB, FED, BOE, SNB)")
    name: str = Field(..., description="Provider full name")
    base_currency: str = Field(..., description="Default base currency")
    # TODO: deprecate base_currency in favor of base_currencies
    base_currencies: list[str] = Field(..., description="All supported base currencies")
    target_currencies: list[str] = Field(default_factory=list, description="All target currencies this provider can convert to (from get_supported_currencies)")
    description: str = Field(..., description="Provider description")
    description_i18n: dict[str, str] = Field(default_factory=dict, description="Multilingual provider descriptions {lang_code: description}")
    icon_url: Optional[str] = Field(None, description="Provider icon URL (hardcoded)")
    docs_url: Optional[str] = Field(None, description="URL to documentation page for this provider")


# ============================================================================
# RATE SYNC MODELS

# ============================================================================
# CONVERSION MODELS
# ============================================================================


class FXConversionRequest(BaseModel):
    """Single conversion request with date range.

    Breaking change: Now uses Currency object for from_amount instead of
    separate amount + from_currency fields.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        )

    from_amount: Currency = Field(..., description="Amount to convert with source currency")
    to_currency: str = Field(
        ..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)"
        )
    date_range: DateRangeModel = Field(
        ..., description="Date range for conversion (start required, end optional for single day)"
        )

    @field_validator("to_currency", mode="before")
    @classmethod
    def validate_to_currency(cls, v):
        return Currency.validate_code(v)


class FXConversionResult(BaseModel):
    """Single conversion result.

    Breaking change: Now uses Currency objects for from_amount and to_amount
    instead of separate amount/currency fields.
    """

    model_config = ConfigDict()

    from_amount: Currency = Field(..., description="Original amount with source currency")
    to_amount: Currency = Field(..., description="Converted amount with target currency")
    conversion_date: date_type = Field(
        ..., description="Date requested for conversion (ISO format)"
        )
    rate: Optional[Decimal] = Field(None, description="Exchange rate used (if not identity)")
    backward_fill_info: Optional[BackwardFillInfo] = Field(
        None,
        description="Backward-fill info (only present if rate from a different date was used). "
                    "If null, rate_date = conversion_date",
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

    @field_validator("rate", mode="before")
    @classmethod
    def coerce_rate(cls, v):
        """Coerce rate to Decimal."""
        if isinstance(v, str):
            return Decimal(v)
        if isinstance(v, (int, float)):
            return Decimal(str(v))
        return v

    @field_validator("base", "quote", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)


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
    """Single rate deletion request.

    Either `date_range` or `delete_all=True` must be specified.
    If `delete_all=True`, all rates for the pair are deleted regardless of date_range.
    """

    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, )

    from_currency: str = Field(..., alias="from", min_length=3, max_length=3, description="Source currency (ISO 4217)")
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    date_range: Optional[DateRangeModel] = Field(None, description="Date range to delete (start required, end optional for single day). Required unless delete_all=True.")
    delete_all: bool = Field(False, description="If True, delete ALL rates for this pair (ignores date_range)")

    @field_validator("from_currency", "to_currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_range_or_all(self) -> "FXDeleteItem":
        """Ensure either date_range or delete_all is specified."""
        if not self.delete_all and self.date_range is None:
            raise ValueError("Either 'date_range' or 'delete_all: true' must be specified")
        return self


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
# CONVERSION ROUTE CONFIGURATION MODELS (replaces pair-sources)
# ============================================================================


def validate_chain_steps(
    steps: list,  # list[FXRouteStep] or list[dict] with from/to keys
    base: str,
    quote: str,
    ) -> None:
    """
    Validate the coherence of a chain_steps list.

    Used by both Pydantic schema (FXConversionRouteItem.validate_chain)
    and SQLModel (FxConversionRoute validator).

    Raises:
        ValueError if any rule is violated.
    """
    if not steps:
        raise ValueError("chain_steps must have at least 1 element")

    def _get(step, attr_pydantic, key_dict):
        if hasattr(step, attr_pydantic):
            return getattr(step, attr_pydantic)
        return step[key_dict]

    # 1. Continuity: step[i].to == step[i+1].from
    for i in range(len(steps) - 1):
        to_cur = _get(steps[i], 'to_currency', 'to')
        from_cur = _get(steps[i + 1], 'from_currency', 'from')
        if to_cur != from_cur:
            raise ValueError(f"Chain discontinuity at step {i}: {to_cur} != {from_cur}")

    # 2. No repeated edges (unordered pair, any direction/provider)
    edges_seen: set[tuple[str, str]] = set()
    for s in steps:
        fc = _get(s, 'from_currency', 'from')
        tc = _get(s, 'to_currency', 'to')
        edge = tuple(sorted([fc, tc]))
        if edge in edges_seen:
            raise ValueError(f"Duplicate edge: {edge[0]}-{edge[1]}")
        edges_seen.add(edge)

    # 3. Endpoints must match (base, quote) of the route
    first_from = _get(steps[0], 'from_currency', 'from')
    last_to = _get(steps[-1], 'to_currency', 'to')
    endpoints = tuple(sorted([first_from, last_to]))
    pair = tuple(sorted([base, quote]))
    if endpoints != pair:
        raise ValueError(f"Chain endpoints {endpoints} don't match pair {pair}")

    # 4. Multi-step chains must not contain MANUAL provider
    if len(steps) > 1:
        for s in steps:
            prov = _get(s, 'provider', 'provider')
            if prov.upper() == "MANUAL":
                raise ValueError("MANUAL provider cannot be used in multi-step chains")


class FXRouteStep(BaseModel):
    """Single step (edge) in a conversion chain.

    Corresponds to an edge in the currency graph built by the DFS algorithm.
    """
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    from_currency: str = Field(..., alias="from", min_length=3, max_length=3)
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3)
    provider: str = Field(..., description="Provider code for this step")

    @field_validator("from_currency", "to_currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)

    @field_validator("provider", mode="before")
    @classmethod
    def uppercase_provider(cls, v):
        if isinstance(v, str):
            return v.strip().upper()
        return v

    @model_validator(mode="after")
    def validate_different(self):
        if self.from_currency == self.to_currency:
            raise ValueError(f"from and to must differ (got {self.from_currency})")
        return self


class FXConversionRouteItem(BaseModel):
    """Configuration for a conversion route.

    Replaces FXPairSourceItem. Every route is a chain of steps:
    - 1 step = direct conversion (e.g., EUR→USD via ECB)
    - 2+ steps = chain conversion (e.g., RON→EUR→USD via ECB+ECB)
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    base: str = Field(..., min_length=3, max_length=3)
    quote: str = Field(..., min_length=3, max_length=3)
    priority: int = Field(..., ge=1)
    chain_steps: list[FXRouteStep] = Field(..., min_length=1,
                                           description="Ordered list of conversion steps (edges of the graph)")

    @field_validator("base", "quote", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_chain(self):
        validate_chain_steps(self.chain_steps, self.base, self.quote)
        return self


class FXConversionRoutesResponse(BaseListResponse[FXConversionRouteItem]):
    """Response model for listing conversion routes."""
    pass


class FXConversionRouteResult(BaseModel):
    """Result of a single route creation/update."""

    success: bool = Field(..., description="Whether the operation succeeded")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    priority: int = Field(..., description="Priority level")
    chain_steps: list[FXRouteStep] = Field(..., description="Chain steps configured")
    action: str = Field(..., description="Action taken: 'created' or 'updated'")
    message: Optional[str] = Field(None, description="Additional info/warning")


class FXCreateRoutesResponse(BaseBulkResponse[FXConversionRouteResult]):
    """Response model for bulk route creation."""

    error_count: int = Field(default=0, description="Number of failed operations")


class FXDeleteRouteItem(BaseModel):
    """Single route to delete."""

    model_config = ConfigDict(str_strip_whitespace=True)

    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    priority: Optional[int] = Field(None, ge=1, description="Priority level (optional, if not provided deletes all priorities)")

    @field_validator("base", "quote", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)


class FXDeleteRouteResult(BaseDeleteResult):
    """Result of a single route deletion."""

    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    priority: Optional[int] = Field(None, description="Priority level (if specified)")
    # Inherits from BaseDeleteResult:
    # - success: bool
    # - deleted_count: int
    # - message: Optional[str]


class FXDeleteRoutesResponse(BaseBulkDeleteResponse[FXDeleteRouteResult]):
    """Response model for DELETE /routes."""
    pass


# NOTE: FXCurrenciesResponse was removed — GET /fx/currencies endpoint absorbed by
# GET /fx/providers which now includes target_currencies per provider.


class FXPairItem(BaseModel):
    """A unique currency pair with optional metadata."""

    base: str = Field(..., description="Base currency (alphabetically first)")
    quote: str = Field(..., description="Quote currency (alphabetically second)")
    has_provider: bool = Field(default=False, description="Whether this pair has configured providers")
    rate_count: int = Field(default=0, description="Number of rate data points in the DB")


class FXPairsListResponse(BaseListResponse[FXPairItem]):
    """Response for GET /currencies/pairs — all known FX pairs."""
    pass
