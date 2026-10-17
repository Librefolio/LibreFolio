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

import math
from datetime import date as date_type
from decimal import Decimal
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from backend.app.schemas.common import (
    BackwardFillInfo,
    BaseBulkDeleteResponse,
    BaseBulkResponse,
    BaseDeleteResult,
    BaseListResponse,
    Currency,
    DateRangeModel,
    PeriodChangesAsOf,
    SafeDecimal,
    StrictModel,
)
from backend.app.schemas.signals import (
    SignalAnnotationRequest,
    SignalBandValueSource,
    SignalLineCrossoverRequest,
    SignalOutputValueSource,
    SignalRequest,
    SignalResult,
)
from backend.app.utils.datetime_utils import parse_ISO_date

# ============================================================================
# PROVIDER MODELS
# ============================================================================


class FXProviderInfo(StrictModel):
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
    warning_i18n: dict[str, str] = Field(default_factory=dict, description="Multilingual provider warnings/caveats {lang_code: warning}. Empty = no warning.")
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
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    date_range: DateRangeModel = Field(..., description="Date range for conversion (start required, end optional for single day)")
    signals: List[SignalRequest] = Field(
        default_factory=list,
        description="Technical signal instances computed on effective FX rates",
    )
    annotation_requests: List[SignalAnnotationRequest] = Field(
        default_factory=list,
        description="Optional cross/threshold rules evaluated on extended signal output",
    )

    @field_validator("to_currency", mode="before")
    @classmethod
    def validate_to_currency(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_signal_references(self) -> FXConversionRequest:
        instance_ids = [signal.instance_id for signal in self.signals]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("signal instance_id values must be unique")
        annotation_keys = [annotation.key for annotation in self.annotation_requests]
        if len(annotation_keys) != len(set(annotation_keys)):
            raise ValueError("annotation request keys must be unique")
        known_instances = set(instance_ids)
        for annotation in self.annotation_requests:
            if annotation.attach_to_instance_id not in known_instances:
                raise ValueError(f"annotation target '{annotation.attach_to_instance_id}' is not in signals")
            sources = (annotation.left, annotation.right) if isinstance(annotation, SignalLineCrossoverRequest) else (annotation.source,)
            for source in sources:
                if isinstance(source, (SignalOutputValueSource, SignalBandValueSource)) and source.instance_id not in known_instances:
                    raise ValueError(f"annotation source '{source.instance_id}' is not in signals")
        return self


class FXConversionResult(BaseModel):
    """Single conversion result.

    Breaking change: Now uses Currency objects for from_amount and to_amount
    instead of separate amount/currency fields.
    """

    model_config = ConfigDict()

    from_amount: Currency = Field(..., description="Original amount with source currency")
    to_amount: Currency = Field(..., description="Converted amount with target currency")
    conversion_date: date_type = Field(..., description="Date requested for conversion (ISO format)")
    rate: Optional[SafeDecimal] = Field(None, description="Exchange rate used (if not identity)")
    backward_fill_info: Optional[BackwardFillInfo] = Field(
        None,
        description="Backward-fill info (only present if rate from a different date was used). " "If null, rate_date = conversion_date",
    )

    @field_validator("conversion_date", mode="before")
    @classmethod
    def _parse_conversion_date(cls, v):
        return parse_ISO_date(v)


class FXSignalQueryResult(BaseModel):
    """Signal results for one original (pre-daily-expansion) FX request."""

    request_index: int = Field(..., ge=0)
    from_currency: str = Field(..., min_length=3, max_length=3)
    to_currency: str = Field(..., min_length=3, max_length=3)
    date_range: DateRangeModel = Field(
        ...,
        description="The range the signals cover: the requested one cut at the ceiling (latest_range_end(), at most 100 years long). A conversion entirely after the ceiling echoes the requested range, with no points.",
    )
    signals: List[SignalResult] = Field(default_factory=list)


class FXConvertResponse(BaseBulkResponse[FXConversionResult]):
    """Response model for bulk currency conversion."""

    # Inherits: results, success_count, errors
    # Note: success_count should be populated by service layer
    signal_results: List[FXSignalQueryResult] = Field(
        default_factory=list,
        description="Signal results grouped by original conversion request",
    )


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
    rate: SafeDecimal = Field(..., gt=0, description="Exchange rate (must be positive)")
    source: str = Field(default="MANUAL", description="Source of the rate")

    @field_validator("rate", mode="before")
    @classmethod
    def coerce_rate(cls, v):
        """A finite float as its shortest decimal text (``0.1`` → ``Decimal("0.1")``, never ``0.1000000000000000055…``);
        anything else as it came. Pydantic's own parsing then refuses what is not a finite number with a 422 that echoes
        the text sent: ``Decimal("abc")`` here raised ``InvalidOperation`` past Pydantic (a 500), and an echoed
        ``Decimal('Infinity')`` or ``inf`` (the JSON number ``1E+400``) is a value the JSON renderer cannot write (X-R38).
        """
        if isinstance(v, float):
            return Decimal(str(v)) if math.isfinite(v) else str(v)
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
    rate: SafeDecimal = Field(..., description="The rate value stored")
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


# ============================================================================
# RATE DELETE MODELS
# ============================================================================


class FXDeleteItem(BaseModel):
    """Single rate deletion request.

    Either `date_range` or `delete_all=True` must be specified.
    If `delete_all=True`, all rates for the pair are deleted regardless of date_range.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    from_currency: str = Field(..., alias="from", min_length=3, max_length=3, description="Source currency (ISO 4217)")
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    date_range: Optional[DateRangeModel] = Field(None, description="Date range to delete (start required, end optional for single day). Required unless delete_all=True.")
    delete_all: bool = Field(False, description="If True, delete ALL rates for this pair (ignores date_range)")

    @field_validator("from_currency", "to_currency", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_range_or_all(self) -> FXDeleteItem:
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


# ============================================================================
# CONVERSION ROUTE CONFIGURATION MODELS (replaces pair-sources)
# ============================================================================


def validate_chain_steps(  # noqa: C901 — flat numbered rule-chain validation
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
        to_cur = _get(steps[i], "to_currency", "to")
        from_cur = _get(steps[i + 1], "from_currency", "from")
        if to_cur != from_cur:
            raise ValueError(f"Chain discontinuity at step {i}: {to_cur} != {from_cur}")

    # 2. No repeated edges (unordered pair, any direction/provider)
    edges_seen: set[tuple[str, str]] = set()
    for s in steps:
        fc = _get(s, "from_currency", "from")
        tc = _get(s, "to_currency", "to")
        edge = tuple(sorted([fc, tc]))
        if edge in edges_seen:
            raise ValueError(f"Duplicate edge: {edge[0]}-{edge[1]}")
        edges_seen.add(edge)

    # 3. Endpoints must match (base, quote) of the route
    first_from = _get(steps[0], "from_currency", "from")
    last_to = _get(steps[-1], "to_currency", "to")
    endpoints = tuple(sorted([first_from, last_to]))
    pair = tuple(sorted([base, quote]))
    if endpoints != pair:
        raise ValueError(f"Chain endpoints {endpoints} don't match pair {pair}")

    # 4. Multi-step chains must not contain MANUAL provider
    if len(steps) > 1:
        for s in steps:
            prov = _get(s, "provider", "provider")
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

    base: str = Field(..., min_length=3, max_length=3, description="Base currency. Stored alphabetically: posting EUR/DKK yields a DKK-EUR row.")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency. See `base` — the pair is sorted on write, not rejected.")
    priority: int = Field(..., ge=1)
    chain_steps: list[FXRouteStep] = Field(..., min_length=1, description="Ordered list of conversion steps (edges of the graph)")

    @field_validator("base", "quote", mode="before")
    @classmethod
    def uppercase_currency(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_chain(self):
        validate_chain_steps(self.chain_steps, self.base, self.quote)
        return self


class FXConversionRouteReadItem(FXConversionRouteItem):
    """Configured route with derived, response-only routing metadata."""

    model_config = ConfigDict(extra="forbid")

    is_chain: bool = Field(..., description="Whether the configured route contains more than one step", json_schema_extra={"readOnly": True})
    providers_used: list[str] = Field(
        ...,
        description="Sorted unique provider codes configured in the route, including MANUAL; membership only, not ordered traversal or successful-fetch provenance",
        json_schema_extra={"readOnly": True, "uniqueItems": True},
    )


class FXConversionRoutesResponse(BaseListResponse[FXConversionRouteReadItem]):
    """Response model for listing conversion routes."""


class FXConversionRouteResult(BaseModel):
    """Result of a single route creation/update."""

    success: bool = Field(..., description="Whether the operation succeeded")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    priority: int = Field(..., description="Priority level")
    chain_steps: list[FXRouteStep] = Field(..., description="Chain steps configured")
    is_chain: bool = Field(..., description="Whether the configured route contains more than one step", json_schema_extra={"readOnly": True})
    providers_used: list[str] = Field(
        ...,
        description="Sorted unique provider codes in the submitted configuration, including MANUAL and unknown codes in failed results; not successful-fetch provenance",
        json_schema_extra={"readOnly": True, "uniqueItems": True},
    )
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


# NOTE: FXCurrenciesResponse was removed — GET /fx/currencies endpoint absorbed by
# GET /fx/providers which now includes target_currencies per provider.
# FXPairItem/FXPairsListResponse were removed too — the GET /currencies/pairs
# endpoint they were pre-written for never shipped (audit 08/G2).


# ============================================================================
# FX FIXED-PERIOD CHANGES (MF-P2, D-MF6 b)
# ============================================================================


#: The most pairs one fixed-period changes request may list (MF-P2b): the FX table sends every pair it lists.
PERIOD_CHANGES_MAX_PAIRS = 1_000


class FXPeriodChangesRequest(StrictModel):
    """One pair of a fixed-period changes request: the FX table's Δ columns (1D … 5Y), up to ``as_of``."""

    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217): the rate is quote per 1 base")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    as_of: PeriodChangesAsOf = Field(..., description="Anchor day: the end of the range the table shows (1900-01-01 or later)")

    @field_validator("base", "quote", mode="before")
    @classmethod
    def validate_codes(cls, v):
        return Currency.validate_code(v)

    @model_validator(mode="after")
    def validate_distinct(self) -> FXPeriodChangesRequest:
        if self.base == self.quote:
            raise ValueError("base and quote must differ")
        return self


class FXPeriodChange(StrictModel):
    """The change of a rate over one fixed period, as fractions (0.05 = +5 %), in both orientations of the pair."""

    key: str = Field(..., description="Period key: 1D, 1W, 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y")
    days: int = Field(..., ge=1, description="Calendar days of the period")
    change_ratio: Optional[SafeDecimal] = Field(None, description="(Rate on as_of ÷ rate on as_of − days) − 1 (quote per base); null without a rate on either day")
    inverse_change_ratio: Optional[SafeDecimal] = Field(None, description="The same change with the pair inverted (base per quote): (rate on as_of − days ÷ rate on as_of) − 1")


class FXPeriodChangesResult(StrictModel):
    """The fixed-period changes of one pair. The rate on a day is the conversion of 1 base on that day, with the
    conversion's unlimited backward fill — the rates the FX page shows."""

    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    as_of: date_type = Field(..., description="Anchor day")
    periods: List[FXPeriodChange] = Field(default_factory=list, description="One entry per fixed period, in display order")
    errors: List[str] = Field(default_factory=list, description="Non-fatal warnings (e.g. no rate on a day)")


class FXPeriodChangesResponse(BaseListResponse[FXPeriodChangesResult]):
    """Bulk response of fixed-period changes: one item per requested pair, in request order."""
