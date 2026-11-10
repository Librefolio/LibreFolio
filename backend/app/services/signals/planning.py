"""The plan of a signal batch: requests validated and deduplicated, the history they need before the visible
range, and the failures known before any price is read."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.app.schemas.signals import (
    SignalAnnotationRequest,
    SignalBandValueSource,
    SignalError,
    SignalErrorCode,
    SignalExecutionContext,
    SignalLineCrossoverRequest,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPriceValueSource,
    SignalRequest,
    SignalResult,
    SignalSeriesKind,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalWarmupRequirement,
)
from backend.app.services.signals.annotations import annotation_sources
from backend.app.services.signals.base import SignalPlugin
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.signals.series import SESSION_WARMUP_DAY_MULTIPLIER
from backend.app.services.signals.validation import exception_details

_ANNOTATION_REQUEST_ADAPTER = TypeAdapter(SignalAnnotationRequest)


class SignalRequestValidationError(ValueError):
    """Raised when a signal or annotation request is structurally inconsistent."""


@dataclass(frozen=True)
class PlannedSignal:
    dedup_key: str
    plugin_class: type[SignalPlugin]
    params: BaseModel
    normalized_params: dict[str, Any]
    requirement: SignalWarmupRequirement
    instance_ids: tuple[str, ...]
    statically_compatible: bool
    comparison_asset_id: Optional[int]


@dataclass(frozen=True)
class SignalExecutionPlan:
    requests: tuple[SignalRequest, ...]
    context: SignalExecutionContext
    computations: tuple[PlannedSignal, ...]
    preflight_results: dict[str, SignalResult]
    max_total_points: int
    max_prepared_total_points: int
    required_price_fields: frozenset[SignalPriceField]
    requires_events: bool
    required_event_types: frozenset[str]
    comparison_asset_ids: frozenset[int]
    annotation_requests: tuple[SignalAnnotationRequest, ...]
    # E1: at least one computation declared full-history warm-up (e.g.
    # drawdown). The fetch path then loads from the start of the available
    # history, which Z-30 sets at 1900-01-01, or from the points-derived
    # warm-up's start when that is earlier.
    requires_full_history: bool = False
    # The same warm-up split by what a plugin counts: sessions (quote days) or calendar days.
    max_session_total_points: int = 0
    max_calendar_total_points: int = 0

    @property
    def max_history_points_before_visible(self) -> int:
        return self.max_total_points

    @property
    def max_history_days_before_visible(self) -> int:
        """Calendar days of raw price history the plan needs before the visible start.

        A plugin that computes on quote days counts sessions, and each takes more than one calendar
        day; a plugin that counts calendar days asks for them directly.
        """
        return max(
            self.max_session_total_points * SESSION_WARMUP_DAY_MULTIPLIER,
            self.max_calendar_total_points,
        )

    @property
    def max_prepared_history_points_before_visible(self) -> int:
        return self.max_prepared_total_points

    @property
    def requires_prepared_asset_series(self) -> bool:
        return self.max_prepared_total_points > 0


def prepare_signal_plan(  # noqa: C901 — per-request validation/dedup loop, branches are early-continue guards
    registry: type[SignalPluginRegistry],
    requests: Sequence[SignalRequest | dict[str, Any]],
    context: SignalExecutionContext,
    annotation_requests: Sequence[SignalAnnotationRequest | dict[str, Any]] = (),
) -> SignalExecutionPlan:
    request_models = tuple(request if isinstance(request, SignalRequest) else SignalRequest.model_validate(request) for request in requests)
    instance_ids = [request.instance_id for request in request_models]
    if len(instance_ids) != len(set(instance_ids)):
        raise SignalRequestValidationError("signal instance_id values must be unique within one batch")
    annotation_models = tuple(
        (
            item
            if isinstance(
                item,
                (
                    SignalLineCrossoverRequest,
                    SignalThresholdCrossingRequest,
                ),
            )
            else _ANNOTATION_REQUEST_ADAPTER.validate_python(item)
        )
        for item in annotation_requests
    )
    annotation_keys = [item.key for item in annotation_models]
    if len(annotation_keys) != len(set(annotation_keys)):
        raise SignalRequestValidationError("annotation request keys must be unique within one batch")
    request_ids = set(instance_ids)
    for annotation in annotation_models:
        if annotation.attach_to_instance_id not in request_ids:
            raise SignalRequestValidationError(f"annotation target '{annotation.attach_to_instance_id}' is not a requested signal instance")
        for source in annotation_sources(annotation):
            if isinstance(source, (SignalOutputValueSource, SignalBandValueSource)) and source.instance_id not in request_ids:
                raise SignalRequestValidationError(f"annotation source '{source.instance_id}' is not a requested signal instance")

    grouped: dict[str, dict[str, Any]] = {}
    plugin_classes_by_instance: dict[str, type[SignalPlugin]] = {}
    preflight_results: dict[str, SignalResult] = {}
    max_total_points = 0
    max_prepared_total_points = 0
    max_session_total_points = 0
    max_calendar_total_points = 0
    requires_full_history = False
    required_price_fields: set[SignalPriceField] = set()
    requires_events = False
    required_event_types: set[str] = set()
    comparison_asset_ids: set[int] = set()
    for annotation in annotation_models:
        for source in annotation_sources(annotation):
            if isinstance(source, SignalPriceValueSource):
                required_price_fields.add(source.field)
        if annotation.observed_only:
            required_price_fields.add(SignalPriceField.CLOSE)

    for request in request_models:
        plugin_class = registry.get_plugin(request.signal_code)
        if plugin_class is None:
            preflight_results[request.instance_id] = preflight_failure(
                request=request,
                implementation_version=None,
                code=SignalErrorCode.UNKNOWN_SIGNAL,
                message=f"Unknown signal code: {request.signal_code}",
            )
            continue
        plugin_classes_by_instance[request.instance_id] = plugin_class

        try:
            params = plugin_class.validate_params(request.params)
        except ValidationError as exc:
            preflight_results[request.instance_id] = preflight_failure(
                request=request,
                implementation_version=plugin_class.implementation_version,
                code=SignalErrorCode.INVALID_PARAMS,
                message=f"Invalid parameters for {request.signal_code}",
                details={"validation_errors": json.loads(exc.json(include_url=False))},
            )
            continue

        normalized_params = params.model_dump(
            mode="json",
            by_alias=True,
        )
        comparison_asset_param = plugin_class.input_requirements.comparison_asset_param
        comparison_asset_id = int(getattr(params, comparison_asset_param)) if comparison_asset_param is not None else None
        dedup_key = signal_dedup_key(
            request.signal_code,
            normalized_params,
        )
        existing = grouped.get(dedup_key)
        if existing is not None:
            existing["instance_ids"].append(request.instance_id)
            continue

        try:
            requirement = SignalWarmupRequirement.model_validate(plugin_class.warmup_requirement(params, context))
        except Exception as exc:
            preflight_results[request.instance_id] = preflight_failure(
                request=request,
                implementation_version=plugin_class.implementation_version,
                code=SignalErrorCode.PLANNING_ERROR,
                message=f"Unable to plan {request.signal_code}",
                details=exception_details(exc, phase="planning"),
            )
            continue

        statically_compatible = context.domain in plugin_class.compatible_domains
        grouped[dedup_key] = {
            "plugin_class": plugin_class,
            "params": params,
            "normalized_params": normalized_params,
            "requirement": requirement,
            "instance_ids": [request.instance_id],
            "statically_compatible": statically_compatible,
            "comparison_asset_id": comparison_asset_id,
        }
        if statically_compatible:
            max_total_points = max(
                max_total_points,
                requirement.total_points,
            )
            if requirement.full_history:
                requires_full_history = True
            if plugin_class.input_requirements.uses_prepared_asset_series:
                max_prepared_total_points = max(
                    max_prepared_total_points,
                    requirement.total_points,
                )
                if comparison_asset_id is not None:
                    comparison_asset_ids.add(comparison_asset_id)
            elif plugin_class.computes_on_quote_days:
                max_session_total_points = max(max_session_total_points, requirement.total_points)
            else:
                max_calendar_total_points = max(max_calendar_total_points, requirement.total_points)
            required_price_fields.update(plugin_class.input_requirements.price_fields)
            if plugin_class.input_requirements.requires_events:
                requires_events = True
                required_event_types.update(plugin_class.input_requirements.event_types)

    computations = tuple(
        PlannedSignal(
            dedup_key=dedup_key,
            plugin_class=entry["plugin_class"],
            params=entry["params"],
            normalized_params=entry["normalized_params"],
            requirement=entry["requirement"],
            instance_ids=tuple(entry["instance_ids"]),
            statically_compatible=entry["statically_compatible"],
            comparison_asset_id=entry["comparison_asset_id"],
        )
        for dedup_key, entry in grouped.items()
    )
    validate_annotation_output_sources(
        annotation_models,
        plugin_classes_by_instance,
    )
    return SignalExecutionPlan(
        requests=request_models,
        context=context,
        computations=computations,
        preflight_results=preflight_results,
        max_total_points=max_total_points,
        max_prepared_total_points=max_prepared_total_points,
        required_price_fields=frozenset(required_price_fields),
        requires_events=requires_events,
        required_event_types=frozenset(required_event_types),
        comparison_asset_ids=frozenset(comparison_asset_ids),
        annotation_requests=annotation_models,
        requires_full_history=requires_full_history,
        max_session_total_points=max_session_total_points,
        max_calendar_total_points=max_calendar_total_points,
    )


def validate_annotation_output_sources(
    requests: tuple[SignalAnnotationRequest, ...],
    plugin_classes_by_instance: dict[str, type[SignalPlugin]],
) -> None:
    for request in requests:
        for source in annotation_sources(request):
            if not isinstance(source, (SignalOutputValueSource, SignalBandValueSource)):
                continue
            plugin_class = plugin_classes_by_instance.get(source.instance_id)
            if plugin_class is None:
                continue
            spec = next(
                (item for item in plugin_class.output_specs if item.key == source.series_key),
                None,
            )
            if isinstance(source, SignalBandValueSource):
                if spec is None:
                    raise SignalRequestValidationError(f"annotation band source series '{source.series_key}' is not declared by '{source.instance_id}'")
                if spec.kind != SignalSeriesKind.BAND:
                    raise SignalRequestValidationError(f"annotation band source series '{source.series_key}' is not a band")
            elif spec is not None and spec.kind == SignalSeriesKind.BAND:
                raise SignalRequestValidationError(f"annotation scalar source series '{source.series_key}' is a band; use kind='band'")


def signal_dedup_key(
    signal_code: str,
    normalized_params: dict[str, Any],
) -> str:
    canonical_params = json.dumps(
        normalized_params,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{signal_code}:{canonical_params}"


def preflight_failure(
    request: SignalRequest,
    implementation_version: Optional[str],
    code: SignalErrorCode,
    message: str,
    details: Optional[dict[str, Any]] = None,
) -> SignalResult:
    return SignalResult(
        instance_id=request.instance_id,
        signal_code=request.signal_code,
        implementation_version=implementation_version,
        normalized_params=request.params,
        status=SignalStatus.FAILED,
        error=SignalError(
            code=code,
            message=message,
            details=details or {},
        ),
    )
