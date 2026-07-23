"""Library-independent contracts for technical signal plugins and consumers."""

from __future__ import annotations

import math
import re
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, FiniteFloat, JsonValue, field_validator, model_validator

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel

_SIGNAL_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
_KEY_PATTERN = r"^[a-z][a-z0-9_.-]*$"


def _finite_decimal(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise ValueError("signal numeric values must be finite")
    return value


SignalDecimal = Annotated[Decimal, AfterValidator(_finite_decimal)]
NonNegativeInt = Annotated[int, Field(ge=0)]


def _ensure_json_safe(value: Any, path: str = "value") -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite float")
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            _ensure_json_safe(item, f"{path}[{index}]")
        return value
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string key")
            _ensure_json_safe(item, f"{path}.{key}")
        return value
    raise ValueError(f"{path} contains a non-JSON value of type {type(value).__name__}")


def _ensure_unique(values: list[Any], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must not contain duplicates")


def _ensure_strictly_increasing(dates: list[date], label: str) -> None:
    if any(current >= following for current, following in zip(dates, dates[1:], strict=False)):
        raise ValueError(f"{label} dates must be strictly increasing and unique")


def _inject_discriminator(
    value: Any,
    *,
    kind: str,
) -> Any:
    if isinstance(value, dict) and "kind" not in value:
        return {
            **value,
            "kind": kind,
        }
    return value


class SignalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SignalDomain(StrEnum):
    ASSET = "asset"
    FX = "fx"


class SignalCategory(StrEnum):
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"


class SignalPriceField(StrEnum):
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"


class SignalDataPolicy(StrEnum):
    STRICT_CONTIGUOUS = "strict_contiguous"
    ALLOW_PARTIAL_CONTIGUOUS = "allow_partial_contiguous"


class SignalCadence(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    IRREGULAR = "irregular"


class SignalSeriesKind(StrEnum):
    LINE = "line"
    BAR = "bar"
    BAND = "band"


class SignalAxisRole(StrEnum):
    PRICE = "price"
    INDEPENDENT = "independent"
    VOLUME = "volume"


class SignalUnit(StrEnum):
    PRICE = "price"
    PERCENTAGE = "percentage"
    INDEX = "index"
    VOLUME = "volume"
    NONE = "none"


class SignalViewTransform(StrEnum):
    NONE = "none"
    BASE_PERCENTAGE = "base_percentage"


class SignalStatus(StrEnum):
    OK = "ok"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class SignalAvailabilityReason(StrEnum):
    INCOMPATIBLE_DOMAIN = "incompatible_domain"
    MISSING_INPUT_FIELDS = "missing_input_fields"
    MISSING_EVENT_TYPES = "missing_event_types"
    INSUFFICIENT_INPUT_COVERAGE = "insufficient_input_coverage"
    INSUFFICIENT_EVENT_COVERAGE = "insufficient_event_coverage"
    INSUFFICIENT_HISTORY = "insufficient_history"
    INCOMPLETE_WARMUP = "incomplete_warmup"
    PARTIAL_INPUT_COVERAGE = "partial_input_coverage"
    PARTIAL_EVENT_COVERAGE = "partial_event_coverage"
    DATA_GAP = "data_gap"


class SignalWarningCode(StrEnum):
    INCOMPLETE_WARMUP = "incomplete_warmup"
    PARTIAL_INPUT_COVERAGE = "partial_input_coverage"
    PARTIAL_EVENT_COVERAGE = "partial_event_coverage"
    DATA_GAP = "data_gap"
    OUTPUT_TRUNCATED = "output_truncated"
    ANNOTATION_UNAVAILABLE = "annotation_unavailable"


class SignalErrorCode(StrEnum):
    UNKNOWN_SIGNAL = "unknown_signal"
    INVALID_PARAMS = "invalid_params"
    PLANNING_ERROR = "planning_error"
    COMPUTE_ERROR = "compute_error"
    INVALID_OUTPUT = "invalid_output"
    CONTRACT_VIOLATION = "contract_violation"


class SignalAnnotationDirection(StrEnum):
    UP = "up"
    DOWN = "down"


class SignalThresholdDirection(StrEnum):
    UP = "up"
    DOWN = "down"
    BOTH = "both"


class SignalAnnotationSampling(StrEnum):
    RECENT = "recent"
    UNIFORM = "uniform"


class SignalPricePoint(SignalModel):
    date: date
    open: Optional[SignalDecimal] = None
    high: Optional[SignalDecimal] = None
    low: Optional[SignalDecimal] = None
    close: SignalDecimal
    volume: Optional[SignalDecimal] = None
    backward_fill_info: Optional[BackwardFillInfo] = None


class SignalEventPoint(SignalModel):
    date: date
    type: str = Field(..., min_length=1)
    value: Optional[SignalDecimal] = None
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "metadata")


class SignalInputData(SignalModel):
    price_points: List[SignalPricePoint] = Field(default_factory=list)
    event_points: List[SignalEventPoint] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self) -> SignalInputData:
        _ensure_strictly_increasing([point.date for point in self.price_points], "price point")
        event_dates = [point.date for point in self.event_points]
        if any(current > following for current, following in zip(event_dates, event_dates[1:], strict=False)):
            raise ValueError("event point dates must be sorted")
        return self


class SignalExecutionContext(SignalModel):
    domain: SignalDomain
    requested_range: DateRangeModel
    cadence: SignalCadence = SignalCadence.DAILY
    data_policy: SignalDataPolicy = SignalDataPolicy.STRICT_CONTIGUOUS
    source_reference: str = Field(..., min_length=1)
    target_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    observed_only: bool = False

    @field_validator("target_currency", mode="before")
    @classmethod
    def normalize_target_currency(cls, value: Any) -> Any:
        return value.strip().upper() if isinstance(value, str) else value


class SignalWarmupRequirement(SignalModel):
    minimum_points: int = Field(..., ge=0, description="Minimum input units needed to produce the first valid output")
    stabilization_points: int = Field(..., ge=0, description="Additional pre-visible units required for numerical stabilization")
    total_points: int = Field(..., ge=0, description="Total input units requested before the visible range")
    normalized_tolerance: Optional[FiniteFloat] = Field(None, gt=0)

    @model_validator(mode="after")
    def validate_total(self) -> SignalWarmupRequirement:
        if self.total_points != self.minimum_points + self.stabilization_points:
            raise ValueError("total_points must equal minimum_points + stabilization_points")
        return self


class SignalWarmupMetadata(SignalModel):
    requirement: SignalWarmupRequirement
    loaded_points: int = Field(..., ge=0, description="Total price or event units loaded for the computation")
    used_points: int = Field(..., ge=0, description="Contiguous units before requested_start used as warm-up")
    complete: bool = Field(..., description="True when used_points satisfies total_points")

    @model_validator(mode="after")
    def validate_counts(self) -> SignalWarmupMetadata:
        if self.used_points > self.loaded_points:
            raise ValueError("used_points cannot exceed loaded_points")
        if self.complete and self.used_points < self.requirement.total_points:
            raise ValueError("complete warm-up requires used_points >= total_points")
        return self


class SignalInputRequirements(SignalModel):
    price_fields: List[SignalPriceField] = Field(default_factory=list)
    requires_events: bool = False
    event_types: List[str] = Field(default_factory=list)
    data_policy: SignalDataPolicy = SignalDataPolicy.STRICT_CONTIGUOUS
    minimum_coverage: FiniteFloat = Field(1.0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_requirements(self) -> SignalInputRequirements:
        _ensure_unique(self.price_fields, "price_fields")
        _ensure_unique(self.event_types, "event_types")
        if not self.price_fields and not self.requires_events:
            raise ValueError("signal requires price fields and/or events")
        if self.event_types and not self.requires_events:
            raise ValueError("event_types require requires_events=true")
        return self


class SignalAxisSpec(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    role: SignalAxisRole
    minimum: Optional[FiniteFloat] = None
    maximum: Optional[FiniteFloat] = None

    @model_validator(mode="after")
    def validate_bounds(self) -> SignalAxisSpec:
        if self.minimum is not None and self.maximum is not None and self.minimum >= self.maximum:
            raise ValueError("axis minimum must be lower than maximum")
        return self


class SignalReferenceLevel(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    label_key: str = Field(..., min_length=1)
    semantic: str = Field(..., min_length=1)
    value: FiniteFloat


class SignalValueRegion(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    label_key: str = Field(..., min_length=1)
    semantic: str = Field(..., min_length=1)
    lower: Optional[FiniteFloat] = None
    upper: Optional[FiniteFloat] = None
    include_lower: bool = True
    include_upper: bool = False

    @model_validator(mode="after")
    def validate_bounds(self) -> SignalValueRegion:
        if self.lower is None and self.upper is None:
            raise ValueError("value region requires lower and/or upper bound")
        if self.lower is not None and self.upper is not None and self.lower >= self.upper:
            raise ValueError("value region lower bound must be lower than upper bound")
        return self


class SignalOutputBase(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    label_key: str = Field(..., min_length=1)
    unit: SignalUnit
    axis: SignalAxisSpec
    view_transform: SignalViewTransform = SignalViewTransform.NONE


class SignalOutputSpec(SignalOutputBase):
    kind: SignalSeriesKind
    supports_reference_levels: bool = False
    supports_value_regions: bool = False
    default_reference_levels: List[SignalReferenceLevel] = Field(default_factory=list)
    default_value_regions: List[SignalValueRegion] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_capabilities(self) -> SignalOutputSpec:
        if self.default_reference_levels and not self.supports_reference_levels:
            raise ValueError("default reference levels require supports_reference_levels=true")
        if self.default_value_regions and not self.supports_value_regions:
            raise ValueError("default value regions require supports_value_regions=true")
        _ensure_unique([level.key for level in self.default_reference_levels], "reference level keys")
        _ensure_unique([region.key for region in self.default_value_regions], "value region keys")
        return self


class SignalValuePoint(SignalModel):
    date: date
    value: Optional[FiniteFloat] = None


class SignalBandPoint(SignalModel):
    date: date
    lower: Optional[FiniteFloat] = None
    middle: Optional[FiniteFloat] = None
    upper: Optional[FiniteFloat] = None

    @model_validator(mode="after")
    def validate_order(self) -> SignalBandPoint:
        present = [value for value in (self.lower, self.middle, self.upper) if value is not None]
        if any(current > following for current, following in zip(present, present[1:], strict=False)):
            raise ValueError("band values must satisfy lower <= middle <= upper")
        return self


class SignalSeriesBase(SignalOutputBase):
    reference_levels: List[SignalReferenceLevel] = Field(default_factory=list)
    value_regions: List[SignalValueRegion] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_semantic_keys(self) -> SignalSeriesBase:
        _ensure_unique([level.key for level in self.reference_levels], "reference level keys")
        _ensure_unique([region.key for region in self.value_regions], "value region keys")
        return self


class SignalScalarSeriesBase(SignalSeriesBase):
    points: List[SignalValuePoint] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_points(self) -> SignalScalarSeriesBase:
        _ensure_strictly_increasing([point.date for point in self.points], "series point")
        if not any(point.value is not None for point in self.points):
            raise ValueError("series must contain at least one finite value")
        return self


class SignalLineSeries(SignalScalarSeriesBase):
    kind: Literal["line"] = Field(json_schema_extra={"enum": ["line"]})

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="line")


class SignalBarSeries(SignalScalarSeriesBase):
    kind: Literal["bar"] = Field(json_schema_extra={"enum": ["bar"]})

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="bar")


class SignalBandSeries(SignalSeriesBase):
    kind: Literal["band"] = Field(json_schema_extra={"enum": ["band"]})
    points: List[SignalBandPoint] = Field(..., min_length=1)

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="band")

    @model_validator(mode="after")
    def validate_points(self) -> SignalBandSeries:
        _ensure_strictly_increasing([point.date for point in self.points], "series point")
        if not any(point.lower is not None or point.middle is not None or point.upper is not None for point in self.points):
            raise ValueError("band series must contain at least one finite value")
        return self


SignalSeries = Annotated[
    Union[SignalLineSeries, SignalBarSeries, SignalBandSeries],
    Field(discriminator="kind"),
]


class SignalPriceValueSource(SignalModel):
    kind: Literal["price"] = Field(json_schema_extra={"enum": ["price"]})
    field: SignalPriceField = SignalPriceField.CLOSE

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="price")


class SignalOutputValueSource(SignalModel):
    kind: Literal["signal"] = Field(json_schema_extra={"enum": ["signal"]})
    instance_id: str = Field(..., min_length=1, max_length=128)
    series_key: str = Field(..., pattern=_KEY_PATTERN)

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(value, kind="signal")


SignalValueSource = Annotated[
    Union[SignalPriceValueSource, SignalOutputValueSource],
    Field(discriminator="kind"),
]


class SignalAnnotationRequestBase(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    attach_to_instance_id: str = Field(..., min_length=1, max_length=128)
    observed_only: bool = False
    epsilon: FiniteFloat = Field(0.0, ge=0)
    min_gap_days: int = Field(0, ge=0)
    limit: Optional[int] = Field(None, ge=1)
    sampling: SignalAnnotationSampling = SignalAnnotationSampling.RECENT


class SignalLineCrossoverRequest(SignalAnnotationRequestBase):
    kind: Literal["line_crossover"] = Field(json_schema_extra={"enum": ["line_crossover"]})
    left: SignalValueSource
    right: SignalValueSource

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(
            value,
            kind="line_crossover",
        )


class SignalThresholdCrossingRequest(SignalAnnotationRequestBase):
    kind: Literal["threshold_crossing"] = Field(json_schema_extra={"enum": ["threshold_crossing"]})
    source: SignalValueSource
    threshold: FiniteFloat
    direction: SignalThresholdDirection = SignalThresholdDirection.BOTH

    @model_validator(mode="before")
    @classmethod
    def default_kind(cls, value: Any) -> Any:
        return _inject_discriminator(
            value,
            kind="threshold_crossing",
        )


SignalAnnotationRequest = Annotated[
    Union[SignalLineCrossoverRequest, SignalThresholdCrossingRequest],
    Field(discriminator="kind"),
]


class SignalAnnotation(SignalModel):
    key: str = Field(..., pattern=_KEY_PATTERN)
    annotation_type: str = Field(..., min_length=1)
    date: date
    direction: Optional[SignalAnnotationDirection] = None
    values: Dict[str, FiniteFloat] = Field(..., min_length=1)
    metadata: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "metadata")


class SignalWarning(SignalModel):
    code: SignalWarningCode
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("details", mode="before")
    @classmethod
    def validate_details(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "details")


class SignalError(SignalModel):
    code: SignalErrorCode
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)
    retryable: bool = False

    @field_validator("details", mode="before")
    @classmethod
    def validate_details(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "details")


class SignalInputCoverage(SignalModel):
    requested_points: int = Field(..., ge=0)
    available_points: int = Field(..., ge=0)
    contiguous_points: int = Field(..., ge=0)
    observed_points: int = Field(..., ge=0)
    backfilled_points: int = Field(..., ge=0)
    missing_points: int = Field(..., ge=0)
    internal_gap_count: int = Field(..., ge=0)
    coverage_ratio: FiniteFloat = Field(..., ge=0, le=1)
    field_coverage: Dict[SignalPriceField, FiniteFloat] = Field(default_factory=dict)
    event_type_counts: Dict[str, NonNegativeInt] = Field(default_factory=dict)
    first_available_date: Optional[date] = None
    last_available_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_coverage(self) -> SignalInputCoverage:
        if self.available_points > self.requested_points:
            raise ValueError("available_points cannot exceed requested_points")
        if self.contiguous_points > self.available_points:
            raise ValueError("contiguous_points cannot exceed available_points")
        if self.observed_points + self.backfilled_points != self.available_points:
            raise ValueError("observed_points + backfilled_points must equal available_points")
        if self.missing_points != self.requested_points - self.available_points:
            raise ValueError("missing_points must equal requested_points - available_points")
        if self.internal_gap_count > self.missing_points:
            raise ValueError("internal_gap_count cannot exceed missing_points")
        if self.missing_points == 0 and self.contiguous_points != self.available_points:
            raise ValueError("full coverage requires contiguous_points == available_points")
        expected_ratio = self.available_points / self.requested_points if self.requested_points else 0.0
        if not math.isclose(self.coverage_ratio, expected_ratio, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("coverage_ratio must match available_points / requested_points")
        for field, ratio in self.field_coverage.items():
            if ratio < 0 or ratio > 1:
                raise ValueError(f"field coverage for {field.value} must be between 0 and 1")
        if (self.first_available_date is None) != (self.last_available_date is None):
            raise ValueError("first_available_date and last_available_date must be provided together")
        if self.first_available_date is not None and self.last_available_date is not None and self.first_available_date > self.last_available_date:
            raise ValueError("first_available_date must not be after last_available_date")
        if self.available_points == 0 and self.first_available_date is not None:
            raise ValueError("empty coverage cannot have available dates")
        return self


class SignalAvailability(SignalModel):
    domain_compatible: bool
    can_compute: bool
    missing_price_fields: List[SignalPriceField] = Field(default_factory=list)
    missing_event_types: List[str] = Field(default_factory=list)
    input_coverage: SignalInputCoverage
    required_points: int = Field(..., ge=0)
    warmup_complete: bool
    partial_coverage_used: bool = False
    reason_code: Optional[SignalAvailabilityReason] = None

    @model_validator(mode="after")
    def validate_availability(self) -> SignalAvailability:
        _ensure_unique(self.missing_price_fields, "missing_price_fields")
        _ensure_unique(self.missing_event_types, "missing_event_types")
        if self.can_compute and not self.domain_compatible:
            raise ValueError("an incompatible domain cannot be computable")
        if self.can_compute and (self.missing_price_fields or self.missing_event_types):
            raise ValueError("a computable signal cannot have wholly missing required inputs")
        if not self.can_compute and self.reason_code is None:
            raise ValueError("unavailable input requires reason_code")
        unavailable_reasons = {
            SignalAvailabilityReason.INCOMPATIBLE_DOMAIN,
            SignalAvailabilityReason.MISSING_INPUT_FIELDS,
            SignalAvailabilityReason.MISSING_EVENT_TYPES,
            SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE,
            SignalAvailabilityReason.INSUFFICIENT_EVENT_COVERAGE,
            SignalAvailabilityReason.INSUFFICIENT_HISTORY,
        }
        partial_reasons = {
            SignalAvailabilityReason.INCOMPLETE_WARMUP,
            SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE,
            SignalAvailabilityReason.PARTIAL_EVENT_COVERAGE,
            SignalAvailabilityReason.DATA_GAP,
        }
        if self.can_compute and self.reason_code in unavailable_reasons:
            raise ValueError("computable input cannot use an unavailable reason")
        if not self.can_compute and self.reason_code in partial_reasons:
            raise ValueError("unavailable input cannot use a partial reason")
        if self.can_compute and not self.warmup_complete and self.reason_code not in partial_reasons:
            raise ValueError("incomplete warm-up requires a partial reason")
        if self.warmup_complete and self.reason_code == SignalAvailabilityReason.INCOMPLETE_WARMUP:
            raise ValueError("complete warm-up cannot use incomplete_warmup reason")
        coverage_reasons = {
            SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE,
            SignalAvailabilityReason.PARTIAL_EVENT_COVERAGE,
            SignalAvailabilityReason.DATA_GAP,
        }
        if self.partial_coverage_used != (self.can_compute and self.reason_code in coverage_reasons):
            raise ValueError("partial_coverage_used must match a computable partial coverage reason")
        return self


class SignalComputation(SignalModel):
    series: List[SignalSeries] = Field(..., min_length=1)
    annotations: List[SignalAnnotation] = Field(default_factory=list)
    warnings: List[SignalWarning] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_series_alignment(self) -> SignalComputation:
        _validate_series_alignment(self.series)
        return self


class SignalRequest(SignalModel):
    instance_id: str = Field(..., min_length=1, max_length=128)
    signal_code: str = Field(..., min_length=1, max_length=64)
    params: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("instance_id", mode="before")
    @classmethod
    def normalize_instance_id(cls, value: Any) -> Any:
        return value.strip() if isinstance(value, str) else value

    @field_validator("signal_code", mode="before")
    @classmethod
    def normalize_signal_code(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if not _SIGNAL_CODE_PATTERN.fullmatch(normalized):
            raise ValueError("signal_code must contain only uppercase letters, numbers, and underscores")
        return normalized

    @field_validator("params", mode="before")
    @classmethod
    def validate_params(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "params")


class SignalCatalogDefinition(SignalModel):
    signal_code: str = Field(..., min_length=1, max_length=64)
    implementation_version: str = Field(..., min_length=1, max_length=64)
    category: SignalCategory
    display_name_key: str = Field(..., min_length=1)
    description_key: str = Field(..., min_length=1)
    icon: str = Field(..., min_length=1)
    docs_path: Optional[str] = None
    params_schema: Dict[str, JsonValue]
    default_params: Dict[str, JsonValue] = Field(default_factory=dict)
    input_requirements: SignalInputRequirements
    output_specs: List[SignalOutputSpec] = Field(..., min_length=1)
    compatible_domains: List[SignalDomain] = Field(..., min_length=1)
    annotation_capabilities: List[str] = Field(default_factory=list)

    @field_validator("signal_code", mode="before")
    @classmethod
    def normalize_signal_code(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if not _SIGNAL_CODE_PATTERN.fullmatch(normalized):
            raise ValueError("signal_code must contain only uppercase letters, numbers, and underscores")
        return normalized

    @field_validator("params_schema", "default_params", mode="before")
    @classmethod
    def validate_json_contract(cls, value: Any, info: Any) -> Any:
        return _ensure_json_safe(value, info.field_name)

    @model_validator(mode="after")
    def validate_catalog(self) -> SignalCatalogDefinition:
        _ensure_unique([spec.key for spec in self.output_specs], "output spec keys")
        _ensure_unique(self.compatible_domains, "compatible_domains")
        _ensure_unique(self.annotation_capabilities, "annotation_capabilities")
        return self


class SignalCatalogResponse(SignalModel):
    items: List[SignalCatalogDefinition] = Field(default_factory=list)


class SignalResult(SignalModel):
    instance_id: str = Field(..., min_length=1, max_length=128)
    signal_code: str = Field(..., min_length=1, max_length=64)
    implementation_version: Optional[str] = Field(None, min_length=1, max_length=64)
    normalized_params: Dict[str, JsonValue] = Field(default_factory=dict)
    status: SignalStatus
    series: List[SignalSeries] = Field(default_factory=list)
    availability: Optional[SignalAvailability] = None
    warmup: Optional[SignalWarmupMetadata] = None
    annotations: List[SignalAnnotation] = Field(default_factory=list)
    warnings: List[SignalWarning] = Field(default_factory=list)
    error: Optional[SignalError] = None

    @field_validator("signal_code", mode="before")
    @classmethod
    def normalize_signal_code(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if not _SIGNAL_CODE_PATTERN.fullmatch(normalized):
            raise ValueError("signal_code must contain only uppercase letters, numbers, and underscores")
        return normalized

    @field_validator("normalized_params", mode="before")
    @classmethod
    def validate_params(cls, value: Any) -> Any:
        return _ensure_json_safe(value, "normalized_params")

    @model_validator(mode="after")
    def validate_status_matrix(self) -> SignalResult:
        if self.series:
            _validate_series_alignment(self.series)

        if self.status == SignalStatus.OK:
            if self.availability is None or self.warmup is None:
                raise ValueError("ok result requires availability and warm-up metadata")
            if not self.series:
                raise ValueError("ok result requires series")
            if not self.availability.can_compute or not self.warmup.complete:
                raise ValueError("ok result requires computable input and complete warm-up")
            if self.availability.reason_code is not None or self.availability.partial_coverage_used:
                raise ValueError("ok result cannot use partial availability")
            if _series_have_missing_values(self.series):
                raise ValueError("ok result cannot contain missing output values")
            if self.error is not None:
                raise ValueError("ok result cannot contain error")
        elif self.status == SignalStatus.PARTIAL:
            if self.availability is None or self.warmup is None:
                raise ValueError("partial result requires availability and warm-up metadata")
            if not self.series:
                raise ValueError("partial result requires series")
            if not self.availability.can_compute:
                raise ValueError("partial result requires computable input")
            if not self.warnings:
                raise ValueError("partial result requires at least one warning")
            if self.warmup.complete and not self.availability.partial_coverage_used:
                raise ValueError("partial result requires incomplete warm-up or partial coverage")
            if self.error is not None:
                raise ValueError("partial result cannot contain error")
        elif self.status == SignalStatus.UNAVAILABLE:
            if self.availability is None or self.warmup is None:
                raise ValueError("unavailable result requires availability and warm-up metadata")
            if self.series or self.annotations:
                raise ValueError("unavailable result cannot contain series or annotations")
            if self.availability.can_compute:
                raise ValueError("unavailable result requires can_compute=false")
            if self.error is not None:
                raise ValueError("unavailable result uses availability reason, not error")
        elif self.status == SignalStatus.FAILED:
            if self.series or self.annotations:
                raise ValueError("failed result cannot contain series or annotations")
            if self.error is None:
                raise ValueError("failed result requires structured error")
            precompute_errors = {
                SignalErrorCode.UNKNOWN_SIGNAL,
                SignalErrorCode.INVALID_PARAMS,
                SignalErrorCode.PLANNING_ERROR,
            }
            if self.error.code in precompute_errors:
                if self.availability is not None or self.warmup is not None:
                    raise ValueError("pre-compute failure cannot contain availability or warm-up metadata")
            else:
                if self.availability is None or self.warmup is None:
                    raise ValueError("compute failure requires availability and warm-up metadata")
                if not self.availability.can_compute:
                    raise ValueError("compute failure requires computable input")

        if self.availability is not None and self.warmup is not None:
            if self.availability.required_points != self.warmup.requirement.total_points:
                raise ValueError("availability required_points must match warm-up total_points")
            if self.availability.warmup_complete != self.warmup.complete:
                raise ValueError("availability warmup_complete must match warm-up metadata")
        return self


def _validate_series_alignment(series: List[SignalSeries]) -> None:
    _ensure_unique([item.key for item in series], "series keys")
    reference_dates = [point.date for point in series[0].points]
    for item in series[1:]:
        if [point.date for point in item.points] != reference_dates:
            raise ValueError("all signal series must have identical dates and cardinality")


def _series_have_missing_values(series: List[SignalSeries]) -> bool:
    for item in series:
        if isinstance(item, SignalBandSeries):
            if any(point.lower is None or point.middle is None or point.upper is None for point in item.points):
                return True
        elif any(point.value is None for point in item.points):
            return True
    return False


__all__ = [
    "SignalAnnotation",
    "SignalAnnotationDirection",
    "SignalAnnotationRequest",
    "SignalAnnotationRequestBase",
    "SignalAnnotationSampling",
    "SignalAvailability",
    "SignalAvailabilityReason",
    "SignalAxisRole",
    "SignalAxisSpec",
    "SignalBandPoint",
    "SignalBandSeries",
    "SignalBarSeries",
    "SignalCadence",
    "SignalCatalogDefinition",
    "SignalCatalogResponse",
    "SignalCategory",
    "SignalComputation",
    "SignalDataPolicy",
    "SignalDecimal",
    "SignalDomain",
    "SignalError",
    "SignalErrorCode",
    "SignalEventPoint",
    "SignalExecutionContext",
    "SignalInputCoverage",
    "SignalInputData",
    "SignalInputRequirements",
    "SignalLineCrossoverRequest",
    "SignalLineSeries",
    "SignalModel",
    "SignalOutputValueSource",
    "SignalOutputSpec",
    "SignalPriceField",
    "SignalPricePoint",
    "SignalPriceValueSource",
    "SignalReferenceLevel",
    "SignalRequest",
    "SignalResult",
    "SignalSeries",
    "SignalSeriesKind",
    "SignalStatus",
    "SignalThresholdCrossingRequest",
    "SignalThresholdDirection",
    "SignalUnit",
    "SignalValuePoint",
    "SignalValueRegion",
    "SignalValueSource",
    "SignalViewTransform",
    "SignalWarning",
    "SignalWarningCode",
    "SignalWarmupMetadata",
    "SignalWarmupRequirement",
]
