"""Signal request, result and catalog: warnings, errors, input coverage, availability, computation, the AI description, the catalog and the result with its consistency rules."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import ConfigDict, Field, FiniteFloat, JsonValue, field_validator, model_validator

from backend.app.schemas.portfolio.data_quality import DataQualityReport
from backend.app.schemas.risk.results import RiskResultMetadata
from backend.app.schemas.signals.annotations import SignalAnnotation
from backend.app.schemas.signals.base import _KEY_PATTERN, _SIGNAL_CODE_PATTERN, NonNegativeInt, SignalModel, SignalSemanticDescription, SignalSemanticId, _ensure_unique
from backend.app.schemas.signals.inputs import SignalInputRequirements, SignalWarmupMetadata
from backend.app.schemas.signals.outputs import SignalBandSeries, SignalOutputSpec, SignalSeries
from backend.app.schemas.signals.vocabulary import SignalAvailabilityReason, SignalCategory, SignalDomain, SignalErrorCode, SignalPriceField, SignalStatus, SignalTemporalClass, SignalUnit, SignalWarningCode
from backend.app.utils.json_utils import ensure_json_safe


class SignalWarning(SignalModel):
    code: SignalWarningCode
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("details", mode="before")
    @classmethod
    def validate_details(cls, value: Any) -> Any:
        return ensure_json_safe(value, "details")


class SignalError(SignalModel):
    code: SignalErrorCode
    message: str = Field(..., min_length=1)
    details: Dict[str, JsonValue] = Field(default_factory=dict)
    retryable: bool = False

    @field_validator("details", mode="before")
    @classmethod
    def validate_details(cls, value: Any) -> Any:
        return ensure_json_safe(value, "details")


class SignalInputCoverage(SignalModel):
    requested_points: int = Field(..., ge=0)
    available_points: int = Field(..., ge=0)
    contiguous_points: int = Field(..., ge=0)
    observed_points: int = Field(..., ge=0)
    backfilled_points: int = Field(..., ge=0)
    missing_points: int = Field(..., ge=0)
    max_consecutive_missing_points: int = Field(0, ge=0)
    internal_gap_count: int = Field(..., ge=0)
    coverage_ratio: FiniteFloat = Field(..., ge=0, le=1)
    field_coverage: Dict[SignalPriceField, FiniteFloat] = Field(default_factory=dict)
    event_type_counts: Dict[str, NonNegativeInt] = Field(default_factory=dict)
    first_available_date: Optional[date] = None
    last_available_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_coverage(self) -> SignalInputCoverage:  # noqa: C901 — flat invariant raises, no nested logic
        if self.available_points > self.requested_points:
            raise ValueError("available_points cannot exceed requested_points")
        if self.contiguous_points > self.available_points:
            raise ValueError("contiguous_points cannot exceed available_points")
        if self.observed_points + self.backfilled_points != self.available_points:
            raise ValueError("observed_points + backfilled_points must equal available_points")
        if self.missing_points != self.requested_points - self.available_points:
            raise ValueError("missing_points must equal requested_points - available_points")
        if self.max_consecutive_missing_points > self.missing_points:
            raise ValueError("max_consecutive_missing_points cannot exceed missing_points")
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
            SignalAvailabilityReason.MISSING_PREPARED_SERIES,
            SignalAvailabilityReason.MISSING_COMPARISON_SERIES,
            SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE,
            SignalAvailabilityReason.INSUFFICIENT_EVENT_COVERAGE,
            SignalAvailabilityReason.INSUFFICIENT_HISTORY,
            SignalAvailabilityReason.UNDEFINED_METRIC,
        }
        partial_reasons = {
            SignalAvailabilityReason.INCOMPLETE_WARMUP,
            SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE,
            SignalAvailabilityReason.PARTIAL_EVENT_COVERAGE,
            SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC,
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
        return ensure_json_safe(value, "params")


class SignalAiOutputDescription(SignalModel):
    """AI-consumable description of a single output series, reusing the
    same semantic identifiers already carried by `SignalOutputSpec` so no
    indicator knowledge needs to be duplicated by AI Export."""

    key: str = Field(..., pattern=_KEY_PATTERN)
    semantic_id: SignalSemanticId
    semantic_description: SignalSemanticDescription
    unit: SignalUnit


class SignalAiEventDescription(SignalModel):
    """AI-consumable description of an event type a signal consumes,
    including whether AI Export should deduplicate repeated events of this
    type when summarizing (e.g. collapsing consecutive identical crossings)."""

    event_type: str = Field(..., min_length=1)
    semantic_description: SignalSemanticDescription
    deduplicate: bool = True


class SignalAiDescription(SignalModel):
    """Plugin-owned AI semantics for a signal, derived by default from
    existing catalog metadata (`semantic_id`/`semantic_description`/
    `category`/`output_specs`) so plugins need no boilerplate unless they
    want to override the derived description."""

    signal_code: str = Field(..., min_length=1, max_length=64)
    semantic_id: SignalSemanticId
    semantic_description: SignalSemanticDescription
    category: SignalCategory
    outputs: tuple[SignalAiOutputDescription, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def validate_outputs(self) -> SignalAiDescription:
        _ensure_unique([output.key for output in self.outputs], "ai output keys")
        _ensure_unique([output.semantic_id for output in self.outputs], "ai output semantic_ids")
        return self


class SignalAiExportTemporalRule(SignalModel):
    model_config = ConfigDict(extra="forbid")

    temporal_class: SignalTemporalClass
    parameter_match: Dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("parameter_match", mode="before")
    @classmethod
    def validate_parameter_match(cls, value: Any) -> Any:
        return ensure_json_safe(value, "parameter_match")


class SignalCatalogDefinition(SignalModel):
    signal_code: str = Field(..., min_length=1, max_length=64)
    implementation_version: str = Field(..., min_length=1, max_length=64)
    category: SignalCategory
    display_name_key: str = Field(..., min_length=1)
    description_key: str = Field(..., min_length=1)
    semantic_id: SignalSemanticId
    semantic_description: SignalSemanticDescription
    icon: str = Field(..., min_length=1)
    docs_path: Optional[str] = None
    params_schema: Dict[str, JsonValue]
    default_params: Dict[str, JsonValue] = Field(default_factory=dict)
    input_requirements: SignalInputRequirements
    output_specs: List[SignalOutputSpec] = Field(..., min_length=1)
    compatible_domains: List[SignalDomain] = Field(..., min_length=1)
    annotation_capabilities: List[str] = Field(default_factory=list)
    ai_description: Optional[SignalAiDescription] = None
    ai_events: List[SignalAiEventDescription] = Field(default_factory=list)
    ai_export_temporal_rules: List[SignalAiExportTemporalRule] = Field(default_factory=list)

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
        return ensure_json_safe(value, info.field_name)

    @model_validator(mode="after")
    def validate_catalog(self) -> SignalCatalogDefinition:
        _ensure_unique([spec.key for spec in self.output_specs], "output spec keys")
        _ensure_unique([spec.semantic_id for spec in self.output_specs], "output semantic_ids")
        _ensure_unique(
            [self.semantic_id, *[spec.semantic_id for spec in self.output_specs]],
            "signal and output semantic_ids",
        )
        _ensure_unique(self.compatible_domains, "compatible_domains")
        _ensure_unique(self.annotation_capabilities, "annotation_capabilities")
        if self.ai_description is None:
            # Default derivation keeps existing catalog construction sites
            # (and test factories) working unchanged: plugins only need to
            # provide an explicit `ai_description` when they want AI-facing
            # semantics to diverge from the catalog's own metadata.
            self.ai_description = SignalAiDescription(
                signal_code=self.signal_code,
                semantic_id=self.semantic_id,
                semantic_description=self.semantic_description,
                category=self.category,
                outputs=tuple(
                    SignalAiOutputDescription(
                        key=spec.key,
                        semantic_id=spec.semantic_id,
                        semantic_description=spec.semantic_description,
                        unit=spec.unit,
                    )
                    for spec in self.output_specs
                ),
            )
        return self


class SignalCatalogResponse(SignalModel):
    items: List[SignalCatalogDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_semantic_ids(self) -> SignalCatalogResponse:
        _ensure_unique([item.semantic_id for item in self.items], "signal semantic_ids")
        _ensure_unique(
            [spec.semantic_id for item in self.items for spec in item.output_specs],
            "catalog output semantic_ids",
        )
        _ensure_unique(
            [
                semantic_id
                for item in self.items
                for semantic_id in (
                    item.semantic_id,
                    *[spec.semantic_id for spec in item.output_specs],
                )
            ],
            "all catalog semantic_ids",
        )
        return self


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
    risk_metadata: Optional[RiskResultMetadata] = None
    data_quality: Optional[DataQualityReport] = None

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
        return ensure_json_safe(value, "normalized_params")

    @model_validator(mode="after")
    def validate_status_matrix(self) -> SignalResult:
        if self.series:
            _validate_series_alignment(self.series)

        _validate_result_rules(self, _RESULT_STATUS_RULES[self.status])
        if self.status == SignalStatus.FAILED and self.error is not None:
            failure_rules = _FAILED_PRECOMPUTE_RULES if self.error.code in _PRECOMPUTE_ERROR_CODES else _FAILED_RUNTIME_RULES
            _validate_result_rules(self, failure_rules)

        if self.availability is not None and self.warmup is not None:
            _validate_result_rules(self, _RESULT_METADATA_RULES)
        _validate_result_rules(self, _RESULT_RISK_CONTEXT_RULES)
        return self


def _validate_series_alignment(series: List[SignalSeries]) -> None:
    _ensure_unique([item.key for item in series], "series keys")
    _ensure_unique([item.semantic_id for item in series], "series semantic_ids")
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


_ResultField = Literal["availability", "warmup", "series", "annotations", "warnings", "error"]


_PresenceRequirement = Literal["present", "absent", "nonempty", "empty"]


@dataclass(frozen=True, slots=True)
class _ResultPresenceRule:
    fields: tuple[_ResultField, ...]
    requirement: _PresenceRequirement
    message: str

    def matches(self, result: SignalResult) -> bool:
        values: tuple[object, ...] = tuple(getattr(result, field) for field in self.fields)
        if self.requirement == "present":
            return all(value is not None for value in values)
        if self.requirement == "absent":
            return all(value is None for value in values)
        if self.requirement == "nonempty":
            return all(bool(value) for value in values)
        if self.requirement == "empty":
            return not any(values)
        raise ValueError(f"unknown result presence requirement: {self.requirement}")


@dataclass(frozen=True, slots=True)
class _ResultPredicateRule:
    predicate: Callable[[SignalResult], bool]
    message: str

    def matches(self, result: SignalResult) -> bool:
        return self.predicate(result)


_ResultRule = Union[_ResultPresenceRule, _ResultPredicateRule]


def _has_computable_input(result: SignalResult) -> bool:
    return result.availability is not None and result.availability.can_compute


def _has_noncomputable_input(result: SignalResult) -> bool:
    return result.availability is not None and not result.availability.can_compute


def _has_computable_complete_input(result: SignalResult) -> bool:
    return _has_computable_input(result) and result.warmup is not None and result.warmup.complete


def _has_full_availability(result: SignalResult) -> bool:
    availability = result.availability
    return availability is not None and availability.reason_code is None and not availability.partial_coverage_used


def _has_no_missing_output_values(result: SignalResult) -> bool:
    return not _series_have_missing_values(result.series)


def _has_justified_partial_state(result: SignalResult) -> bool:
    availability = result.availability
    warmup = result.warmup
    return availability is not None and warmup is not None and (not warmup.complete or availability.partial_coverage_used or availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC)


def _has_matching_required_points(result: SignalResult) -> bool:
    availability = result.availability
    warmup = result.warmup
    return availability is not None and warmup is not None and availability.required_points == warmup.requirement.total_points


def _has_matching_warmup_completion(result: SignalResult) -> bool:
    availability = result.availability
    warmup = result.warmup
    return availability is not None and warmup is not None and availability.warmup_complete == warmup.complete


def _has_paired_risk_context(result: SignalResult) -> bool:
    return (result.risk_metadata is None) == (result.data_quality is None)


# Rule order preserves which error is reported when several constraints fail.
_RESULT_STATUS_RULES: Mapping[SignalStatus, tuple[_ResultRule, ...]] = MappingProxyType(
    {
        SignalStatus.OK: (
            _ResultPresenceRule(("availability", "warmup"), "present", "ok result requires availability and warm-up metadata"),
            _ResultPresenceRule(("series",), "nonempty", "ok result requires series"),
            _ResultPredicateRule(_has_computable_complete_input, "ok result requires computable input and complete warm-up"),
            _ResultPredicateRule(_has_full_availability, "ok result cannot use partial availability"),
            _ResultPredicateRule(_has_no_missing_output_values, "ok result cannot contain missing output values"),
            _ResultPresenceRule(("error",), "absent", "ok result cannot contain error"),
        ),
        SignalStatus.PARTIAL: (
            _ResultPresenceRule(("availability", "warmup"), "present", "partial result requires availability and warm-up metadata"),
            _ResultPresenceRule(("series",), "nonempty", "partial result requires series"),
            _ResultPredicateRule(_has_computable_input, "partial result requires computable input"),
            _ResultPresenceRule(("warnings",), "nonempty", "partial result requires at least one warning"),
            _ResultPredicateRule(_has_justified_partial_state, "partial result requires incomplete warm-up or partial coverage"),
            _ResultPresenceRule(("error",), "absent", "partial result cannot contain error"),
        ),
        SignalStatus.UNAVAILABLE: (
            _ResultPresenceRule(("availability", "warmup"), "present", "unavailable result requires availability and warm-up metadata"),
            _ResultPresenceRule(("series", "annotations"), "empty", "unavailable result cannot contain series or annotations"),
            _ResultPredicateRule(_has_noncomputable_input, "unavailable result requires can_compute=false"),
            _ResultPresenceRule(("error",), "absent", "unavailable result uses availability reason, not error"),
        ),
        SignalStatus.FAILED: (
            _ResultPresenceRule(("series", "annotations"), "empty", "failed result cannot contain series or annotations"),
            _ResultPresenceRule(("error",), "present", "failed result requires structured error"),
        ),
    }
)


_PRECOMPUTE_ERROR_CODES = frozenset(
    {
        SignalErrorCode.UNKNOWN_SIGNAL,
        SignalErrorCode.INVALID_PARAMS,
        SignalErrorCode.PLANNING_ERROR,
    }
)


_FAILED_PRECOMPUTE_RULES: tuple[_ResultRule, ...] = (_ResultPresenceRule(("availability", "warmup"), "absent", "pre-compute failure cannot contain availability or warm-up metadata"),)


_FAILED_RUNTIME_RULES: tuple[_ResultRule, ...] = (
    _ResultPresenceRule(("availability", "warmup"), "present", "compute failure requires availability and warm-up metadata"),
    _ResultPredicateRule(_has_computable_input, "compute failure requires computable input"),
)


_RESULT_METADATA_RULES: tuple[_ResultRule, ...] = (
    _ResultPredicateRule(_has_matching_required_points, "availability required_points must match warm-up total_points"),
    _ResultPredicateRule(_has_matching_warmup_completion, "availability warmup_complete must match warm-up metadata"),
)


_RESULT_RISK_CONTEXT_RULES: tuple[_ResultRule, ...] = (_ResultPredicateRule(_has_paired_risk_context, "risk_metadata and data_quality must be provided together"),)


def _validate_result_rules(result: SignalResult, rules: tuple[_ResultRule, ...]) -> None:
    for rule in rules:
        if not rule.matches(result):
            raise ValueError(rule.message)
