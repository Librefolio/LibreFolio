"""Library-agnostic orchestration for technical signal plugins."""

from __future__ import annotations

import asyncio
import json
import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.app.logging_config import get_logger
from backend.app.schemas.signals import (
    SignalAnnotation,
    SignalAnnotationRequest,
    SignalAvailability,
    SignalAvailabilityReason,
    SignalBandSeries,
    SignalCadence,
    SignalComputation,
    SignalDataPolicy,
    SignalError,
    SignalErrorCode,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputCoverage,
    SignalInputData,
    SignalLineCrossoverRequest,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalRequest,
    SignalResult,
    SignalSeries,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalValueSource,
    SignalWarmupMetadata,
    SignalWarmupRequirement,
    SignalWarning,
    SignalWarningCode,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.signal_annotations import SignalAnnotationService
from backend.app.services.signal_plugins.base import SignalPlugin

logger = get_logger(__name__)
_ANNOTATION_REQUEST_ADAPTER = TypeAdapter(SignalAnnotationRequest)


class SignalOutputValidationError(ValueError):
    """Raised when plugin output violates canonical LibreFolio contracts."""


class SignalNonFiniteOutputError(SignalOutputValidationError):
    """Raised when plugin output contains positive or negative infinity."""


class SignalOutputContractError(SignalOutputValidationError):
    """Raised when canonical output disagrees with plugin metadata."""


@dataclass(frozen=True)
class PlannedSignal:
    dedup_key: str
    plugin_class: type[SignalPlugin]
    params: BaseModel
    normalized_params: dict[str, Any]
    requirement: SignalWarmupRequirement
    instance_ids: tuple[str, ...]
    statically_compatible: bool


@dataclass(frozen=True)
class SignalExecutionPlan:
    requests: tuple[SignalRequest, ...]
    context: SignalExecutionContext
    computations: tuple[PlannedSignal, ...]
    preflight_results: dict[str, SignalResult]
    max_total_points: int
    required_price_fields: frozenset[SignalPriceField]
    requires_events: bool
    required_event_types: frozenset[str]
    annotation_requests: tuple[SignalAnnotationRequest, ...]

    @property
    def unique_computation_count(self) -> int:
        return len(self.computations)

    @property
    def max_history_points_before_visible(self) -> int:
        return self.max_total_points


class SignalService:
    """Resolve, plan and execute signal plugins as one sequential worker batch."""

    def __init__(
        self,
        registry: type[SignalPluginRegistry] = SignalPluginRegistry,
        annotation_service: Optional[SignalAnnotationService] = None,
    ) -> None:
        self.registry = registry
        self.annotation_service = annotation_service or SignalAnnotationService()

    def prepare_plan(
        self,
        requests: Sequence[SignalRequest | dict[str, Any]],
        context: SignalExecutionContext,
        annotation_requests: Sequence[SignalAnnotationRequest | dict[str, Any]] = (),
    ) -> SignalExecutionPlan:
        request_models = tuple(request if isinstance(request, SignalRequest) else SignalRequest.model_validate(request) for request in requests)
        instance_ids = [request.instance_id for request in request_models]
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("signal instance_id values must be unique within one batch")
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
            raise ValueError("annotation request keys must be unique within one batch")
        request_ids = set(instance_ids)
        for annotation in annotation_models:
            if annotation.attach_to_instance_id not in request_ids:
                raise ValueError(f"annotation target '{annotation.attach_to_instance_id}' is not a requested signal instance")
            for source in self._annotation_sources(annotation):
                if isinstance(source, SignalOutputValueSource) and source.instance_id not in request_ids:
                    raise ValueError(f"annotation source '{source.instance_id}' is not a requested signal instance")

        grouped: dict[str, dict[str, Any]] = {}
        preflight_results: dict[str, SignalResult] = {}
        max_total_points = 0
        required_price_fields: set[SignalPriceField] = set()
        requires_events = False
        required_event_types: set[str] = set()
        for annotation in annotation_models:
            for source in self._annotation_sources(annotation):
                if isinstance(source, SignalPriceValueSource):
                    required_price_fields.add(source.field)
            if annotation.observed_only:
                required_price_fields.add(SignalPriceField.CLOSE)

        for request in request_models:
            plugin_class = self.registry.get_plugin(request.signal_code)
            if plugin_class is None:
                preflight_results[request.instance_id] = self._preflight_failure(
                    request=request,
                    implementation_version=None,
                    code=SignalErrorCode.UNKNOWN_SIGNAL,
                    message=f"Unknown signal code: {request.signal_code}",
                )
                continue

            try:
                params = plugin_class.validate_params(request.params)
            except ValidationError as exc:
                preflight_results[request.instance_id] = self._preflight_failure(
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
            dedup_key = self._dedup_key(
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
                preflight_results[request.instance_id] = self._preflight_failure(
                    request=request,
                    implementation_version=plugin_class.implementation_version,
                    code=SignalErrorCode.PLANNING_ERROR,
                    message=f"Unable to plan {request.signal_code}",
                    details=self._exception_details(exc, phase="planning"),
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
            }
            if statically_compatible:
                max_total_points = max(
                    max_total_points,
                    requirement.total_points,
                )
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
            )
            for dedup_key, entry in grouped.items()
        )
        return SignalExecutionPlan(
            requests=request_models,
            context=context,
            computations=computations,
            preflight_results=preflight_results,
            max_total_points=max_total_points,
            required_price_fields=frozenset(required_price_fields),
            requires_events=requires_events,
            required_event_types=frozenset(required_event_types),
            annotation_requests=annotation_models,
        )

    async def execute(
        self,
        plan: SignalExecutionPlan,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint] = (),
        *,
        events_loaded: bool = False,
    ) -> list[SignalResult]:
        """Execute the entire signal batch in one worker thread."""
        return await asyncio.to_thread(
            self._execute_sync,
            plan,
            tuple(price_points),
            tuple(event_points),
            events_loaded,
        )

    async def compute(
        self,
        requests: Sequence[SignalRequest | dict[str, Any]],
        price_points: Sequence[SignalPricePoint],
        context: SignalExecutionContext,
        event_points: Sequence[SignalEventPoint] = (),
        *,
        events_loaded: bool = False,
        annotation_requests: Sequence[SignalAnnotationRequest | dict[str, Any]] = (),
    ) -> list[SignalResult]:
        plan = self.prepare_plan(
            requests,
            context,
            annotation_requests,
        )
        return await self.execute(
            plan,
            price_points,
            event_points,
            events_loaded=events_loaded,
        )

    def _execute_sync(
        self,
        plan: SignalExecutionPlan,
        price_points: tuple[SignalPricePoint, ...],
        event_points: tuple[SignalEventPoint, ...],
        events_loaded: bool,
    ) -> list[SignalResult]:
        input_data = SignalInputData(
            price_points=list(price_points),
            event_points=list(event_points),
        )
        result_by_instance = {instance_id: result.model_copy(deep=True) for instance_id, result in plan.preflight_results.items()}
        extended_series_by_instance: dict[
            str,
            tuple[SignalSeries, ...],
        ] = {}

        for computation in plan.computations:
            try:
                result, extended_series = self._execute_planned_signal(
                    computation,
                    plan.context,
                    input_data.price_points,
                    input_data.event_points,
                    events_loaded,
                )
            except Exception as exc:
                logger.error(
                    "Signal orchestration failed",
                    signal_code=computation.plugin_class.signal_code,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                result = SignalResult(
                    instance_id=computation.instance_ids[0],
                    signal_code=computation.plugin_class.signal_code,
                    implementation_version=computation.plugin_class.implementation_version,
                    normalized_params=computation.normalized_params,
                    status=SignalStatus.FAILED,
                    error=SignalError(
                        code=SignalErrorCode.PLANNING_ERROR,
                        message=f"Signal orchestration failed for {computation.plugin_class.signal_code}",
                        details=self._exception_details(
                            exc,
                            phase="orchestration",
                        ),
                    ),
                )
                extended_series = None
            for instance_id in computation.instance_ids:
                result_by_instance[instance_id] = result.model_copy(
                    update={"instance_id": instance_id},
                    deep=True,
                )
                if extended_series is not None:
                    extended_series_by_instance[instance_id] = extended_series

        if plan.annotation_requests:
            self._attach_annotations(
                result_by_instance,
                plan.annotation_requests,
                input_data.price_points,
                extended_series_by_instance,
                plan.context,
            )

        return [result_by_instance[request.instance_id] for request in plan.requests]

    def _attach_annotations(
        self,
        result_by_instance: dict[str, SignalResult],
        requests: tuple[SignalAnnotationRequest, ...],
        price_points: list[SignalPricePoint],
        extended_series_by_instance: dict[
            str,
            tuple[SignalSeries, ...],
        ],
        context: SignalExecutionContext,
    ) -> None:
        try:
            batch = self.annotation_service.compute(
                requests,
                price_points,
                extended_series_by_instance,
                context,
            )
        except Exception as exc:
            logger.error(
                "Signal annotation batch failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            batch_annotations: dict[
                str,
                tuple[SignalAnnotation, ...],
            ] = {}
            warning_lists: dict[str, list[SignalWarning]] = {}
            for request in requests:
                warning_lists.setdefault(
                    request.attach_to_instance_id,
                    [],
                ).append(
                    SignalWarning(
                        code=SignalWarningCode.ANNOTATION_UNAVAILABLE,
                        message=f"Annotation '{request.key}' is unavailable",
                        details={
                            "annotation_key": request.key,
                            "reason": str(exc),
                        },
                    )
                )
            batch_warnings = {target: tuple(items) for target, items in warning_lists.items()}
        else:
            batch_annotations = batch.annotations_by_target
            batch_warnings = batch.warnings_by_target

        targets = set(batch_annotations) | set(batch_warnings)
        for target in targets:
            result = result_by_instance[target]
            annotations = list(batch_annotations.get(target, ()))
            warnings = list(batch_warnings.get(target, ()))
            if annotations and result.status not in {
                SignalStatus.OK,
                SignalStatus.PARTIAL,
            }:
                for annotation_key in sorted({item.key for item in annotations}):
                    warnings.append(
                        SignalWarning(
                            code=SignalWarningCode.ANNOTATION_UNAVAILABLE,
                            message=f"Annotation '{annotation_key}' could not be attached",
                            details={
                                "annotation_key": annotation_key,
                                "reason": f"target status is {result.status.value}",
                            },
                        )
                    )
                annotations = []

            data = result.model_dump(mode="python")
            merged_annotations = [
                *[item.model_dump(mode="python") for item in result.annotations],
                *[item.model_dump(mode="python") for item in annotations],
            ]
            data["annotations"] = sorted(
                merged_annotations,
                key=lambda item: item["date"],
            )
            data["warnings"] = [
                *[item.model_dump(mode="python") for item in result.warnings],
                *[item.model_dump(mode="python") for item in warnings],
            ]
            result_by_instance[target] = SignalResult.model_validate(data)

    def _execute_planned_signal(
        self,
        planned: PlannedSignal,
        context: SignalExecutionContext,
        price_points: list[SignalPricePoint],
        event_points: list[SignalEventPoint],
        events_loaded: bool,
    ) -> tuple[
        SignalResult,
        Optional[tuple[SignalSeries, ...]],
    ]:
        plugin_class = planned.plugin_class
        requirements = plugin_class.input_requirements
        coverage, valid_flags, calendar_gap_slots = self._build_coverage(
            price_points,
            event_points,
            requirements.price_fields,
            context,
        )
        selected_points = self._select_computation_points(
            price_points,
            valid_flags,
            context.cadence,
            requirements.data_policy,
            planned.requirement.minimum_points,
        )
        selected_events = self._select_events(
            event_points,
            requirements.event_types,
        )
        if requirements.price_fields:
            available_units = len(selected_points)
            warmup_units = sum(point.date < context.requested_range.start for point in selected_points)
            loaded_units = len(price_points)
            requested_end = context.requested_range.end or context.requested_range.start
            visible_units = sum(context.requested_range.start <= point.date <= requested_end for point in selected_points)
        else:
            available_units = len(selected_events)
            warmup_units = sum(event.date < context.requested_range.start for event in selected_events)
            loaded_units = len(event_points)
            requested_end = context.requested_range.end or context.requested_range.start
            visible_units = sum(context.requested_range.start <= event.date <= requested_end for event in selected_events)
        warmup_complete = warmup_units >= planned.requirement.total_points
        warmup = SignalWarmupMetadata(
            requirement=planned.requirement,
            loaded_points=loaded_units,
            used_points=warmup_units,
            complete=warmup_complete,
        )

        missing_price_fields = [field for field in requirements.price_fields if coverage.field_coverage.get(field, 0.0) == 0.0]
        missing_event_types = []
        if requirements.requires_events and not events_loaded:
            missing_event_types = list(requirements.event_types) or ["*"]
        can_compute, reason_code, partial_coverage_used = self._availability_state(
            planned=planned,
            coverage=coverage,
            missing_price_fields=missing_price_fields,
            missing_event_types=missing_event_types,
            available_units=available_units,
            visible_units=visible_units,
            warmup_complete=warmup_complete,
            calendar_gap_slots=calendar_gap_slots,
        )
        availability = SignalAvailability(
            domain_compatible=planned.statically_compatible,
            can_compute=can_compute,
            missing_price_fields=missing_price_fields,
            missing_event_types=missing_event_types,
            input_coverage=coverage,
            required_points=planned.requirement.total_points,
            warmup_complete=warmup_complete,
            partial_coverage_used=partial_coverage_used,
            reason_code=reason_code,
        )

        if not can_compute:
            return (
                SignalResult(
                    instance_id=planned.instance_ids[0],
                    signal_code=plugin_class.signal_code,
                    implementation_version=plugin_class.implementation_version,
                    normalized_params=planned.normalized_params,
                    status=SignalStatus.UNAVAILABLE,
                    availability=availability,
                    warmup=warmup,
                ),
                None,
            )

        service_warnings = self._availability_warnings(
            availability,
            warmup,
            price_points,
            selected_points,
            context,
        )
        try:
            raw_computation = plugin_class().compute(
                selected_points,
                selected_events,
                planned.params,
                context,
            )
            computation = self._normalize_computation(raw_computation)
            self._validate_plugin_output(
                plugin_class,
                computation,
                selected_points,
            )
            all_series_have_finite, visible_has_missing = self._visible_output_state(
                computation.series,
                context,
            )
            if not all_series_have_finite:
                if not warmup.complete:
                    unavailable = self._visible_history_unavailable(availability)
                    return (
                        SignalResult(
                            instance_id=planned.instance_ids[0],
                            signal_code=plugin_class.signal_code,
                            implementation_version=plugin_class.implementation_version,
                            normalized_params=planned.normalized_params,
                            status=SignalStatus.UNAVAILABLE,
                            availability=unavailable,
                            warmup=warmup,
                        ),
                        None,
                    )
                raise SignalOutputValidationError("visible output has no finite value for every series")
            if visible_has_missing and warmup.complete and not availability.partial_coverage_used:
                raise SignalOutputValidationError("complete visible output contains missing values")
            sliced_series = self._slice_series(
                computation.series,
                context,
            )
            sliced_annotations = [annotation for annotation in computation.annotations if self._date_is_visible(annotation.date, context)]
        except SignalNonFiniteOutputError as exc:
            return (
                self._runtime_failure(
                    planned,
                    availability,
                    warmup,
                    SignalErrorCode.INVALID_OUTPUT,
                    str(exc),
                    exc,
                    phase="output",
                ),
                None,
            )
        except SignalOutputContractError as exc:
            return (
                self._runtime_failure(
                    planned,
                    availability,
                    warmup,
                    SignalErrorCode.CONTRACT_VIOLATION,
                    f"Output contract violation from {plugin_class.signal_code}",
                    exc,
                    phase="output",
                ),
                None,
            )
        except (SignalOutputValidationError, ValidationError) as exc:
            return (
                self._runtime_failure(
                    planned,
                    availability,
                    warmup,
                    SignalErrorCode.INVALID_OUTPUT,
                    f"Invalid output from {plugin_class.signal_code}",
                    exc,
                    phase="output",
                ),
                None,
            )
        except Exception as exc:
            logger.error(
                "Signal plugin compute failed",
                signal_code=plugin_class.signal_code,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return (
                self._runtime_failure(
                    planned,
                    availability,
                    warmup,
                    SignalErrorCode.COMPUTE_ERROR,
                    f"Signal computation failed for {plugin_class.signal_code}",
                    exc,
                    phase="compute",
                ),
                None,
            )

        status = SignalStatus.PARTIAL if not warmup.complete or availability.partial_coverage_used else SignalStatus.OK
        warnings = [*computation.warnings, *service_warnings]
        try:
            return (
                SignalResult(
                    instance_id=planned.instance_ids[0],
                    signal_code=plugin_class.signal_code,
                    implementation_version=plugin_class.implementation_version,
                    normalized_params=planned.normalized_params,
                    status=status,
                    series=sliced_series,
                    availability=availability,
                    warmup=warmup,
                    annotations=sliced_annotations,
                    warnings=warnings,
                ),
                tuple(computation.series),
            )
        except ValidationError as exc:
            return (
                self._runtime_failure(
                    planned,
                    availability,
                    warmup,
                    SignalErrorCode.INVALID_OUTPUT,
                    f"Invalid visible output from {plugin_class.signal_code}",
                    exc,
                    phase="output",
                ),
                None,
            )

    @staticmethod
    def _annotation_sources(
        request: SignalLineCrossoverRequest | SignalThresholdCrossingRequest,
    ) -> tuple[SignalValueSource, ...]:
        if isinstance(request, SignalLineCrossoverRequest):
            return (request.left, request.right)
        return (request.source,)

    @staticmethod
    def _dedup_key(
        signal_code: str,
        normalized_params: dict[str, Any],
    ) -> str:
        canonical_params = json.dumps(
            normalized_params,
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"{signal_code}:{canonical_params}"

    @staticmethod
    def _preflight_failure(
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

    @staticmethod
    def _runtime_failure(
        planned: PlannedSignal,
        availability: SignalAvailability,
        warmup: SignalWarmupMetadata,
        code: SignalErrorCode,
        message: str,
        exc: Exception,
        *,
        phase: str,
    ) -> SignalResult:
        return SignalResult(
            instance_id=planned.instance_ids[0],
            signal_code=planned.plugin_class.signal_code,
            implementation_version=planned.plugin_class.implementation_version,
            normalized_params=planned.normalized_params,
            status=SignalStatus.FAILED,
            availability=availability,
            warmup=warmup,
            error=SignalError(
                code=code,
                message=message,
                details=SignalService._exception_details(
                    exc,
                    phase=phase,
                ),
            ),
        )

    @staticmethod
    def _exception_details(
        exc: Exception,
        *,
        phase: str,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {
            "phase": phase,
            "exception_type": type(exc).__name__,
            "exception": str(exc),
        }
        if isinstance(exc, ValidationError):
            details["validation_errors"] = json.loads(exc.json(include_url=False))
        return details

    @classmethod
    def _build_coverage(
        cls,
        price_points: list[SignalPricePoint],
        event_points: list[SignalEventPoint],
        required_fields: list[SignalPriceField],
        context: SignalExecutionContext,
    ) -> tuple[SignalInputCoverage, list[bool], int]:
        valid_flags = [all(getattr(point, field.value) is not None for field in required_fields) for point in price_points]
        internal_calendar_gaps = sum(
            cls._gap_slots(previous.date, current.date, context.cadence)
            for previous, current in zip(
                price_points,
                price_points[1:],
                strict=False,
            )
        )
        boundary_missing = cls._boundary_missing_slots(
            price_points,
            context,
        )
        expected_points = len(price_points) + internal_calendar_gaps + boundary_missing
        if not price_points and required_fields:
            expected_points = cls._visible_slot_count(context)

        available_points = sum(valid_flags)
        missing_points = expected_points - available_points
        invalid_internal = sum(1 for index, valid in enumerate(valid_flags) if not valid and any(valid_flags[:index]) and any(valid_flags[index + 1 :]))
        internal_gap_count = internal_calendar_gaps + invalid_internal
        contiguous_points = cls._longest_contiguous_run(
            price_points,
            valid_flags,
            context.cadence,
        )
        observed_points = sum(
            1
            for point, valid in zip(
                price_points,
                valid_flags,
                strict=True,
            )
            if valid and point.backward_fill_info is None
        )
        backfilled_points = available_points - observed_points
        denominator = expected_points or 1
        field_coverage = {field: sum(1 for point in price_points if getattr(point, field.value) is not None) / denominator for field in required_fields}
        available_dates = [
            point.date
            for point, valid in zip(
                price_points,
                valid_flags,
                strict=True,
            )
            if valid
        ]
        event_counts = Counter(event.type for event in event_points)
        coverage = SignalInputCoverage(
            requested_points=expected_points,
            available_points=available_points,
            contiguous_points=contiguous_points,
            observed_points=observed_points,
            backfilled_points=backfilled_points,
            missing_points=missing_points,
            internal_gap_count=internal_gap_count,
            coverage_ratio=(available_points / expected_points if expected_points else 0.0),
            field_coverage=field_coverage,
            event_type_counts=dict(event_counts),
            first_available_date=available_dates[0] if available_dates else None,
            last_available_date=available_dates[-1] if available_dates else None,
        )
        return coverage, valid_flags, internal_calendar_gaps

    @classmethod
    def _select_computation_points(
        cls,
        price_points: list[SignalPricePoint],
        valid_flags: list[bool],
        cadence: SignalCadence,
        data_policy: SignalDataPolicy,
        minimum_points: int,
    ) -> list[SignalPricePoint]:
        if not price_points:
            return []
        has_date_gap = any(
            cls._gap_slots(previous.date, current.date, cadence) > 0
            for previous, current in zip(
                price_points,
                price_points[1:],
                strict=False,
            )
        )
        if all(valid_flags) and not has_date_gap:
            return price_points
        if data_policy != SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS:
            return []

        runs: list[list[SignalPricePoint]] = []
        current_run: list[SignalPricePoint] = []
        for index, point in enumerate(price_points):
            is_contiguous = not current_run or (
                valid_flags[index - 1]
                and cls._gap_slots(
                    price_points[index - 1].date,
                    point.date,
                    cadence,
                )
                == 0
            )
            if not valid_flags[index] or not is_contiguous:
                if current_run:
                    runs.append(current_run)
                    current_run = []
                if not valid_flags[index]:
                    continue
            current_run.append(point)
        if current_run:
            runs.append(current_run)
        if not runs:
            return []

        latest_run = runs[-1]
        if len(latest_run) >= minimum_points:
            return latest_run
        return max(runs, key=lambda run: (len(run), run[-1].date))

    @staticmethod
    def _select_events(
        event_points: list[SignalEventPoint],
        event_types: list[str],
    ) -> list[SignalEventPoint]:
        if not event_types:
            return event_points
        allowed = set(event_types)
        return [event for event in event_points if event.type in allowed]

    @staticmethod
    def _availability_state(
        *,
        planned: PlannedSignal,
        coverage: SignalInputCoverage,
        missing_price_fields: list[SignalPriceField],
        missing_event_types: list[str],
        available_units: int,
        visible_units: int,
        warmup_complete: bool,
        calendar_gap_slots: int,
    ) -> tuple[bool, Optional[SignalAvailabilityReason], bool]:
        requirements = planned.plugin_class.input_requirements
        if not planned.statically_compatible:
            return False, SignalAvailabilityReason.INCOMPATIBLE_DOMAIN, False
        if missing_event_types:
            return False, SignalAvailabilityReason.MISSING_EVENT_TYPES, False
        if missing_price_fields:
            return False, SignalAvailabilityReason.MISSING_INPUT_FIELDS, False
        if requirements.price_fields and coverage.coverage_ratio < requirements.minimum_coverage:
            return (
                False,
                SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE,
                False,
            )
        partial_coverage = bool(requirements.price_fields) and coverage.missing_points > 0
        if partial_coverage and requirements.data_policy != SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS:
            return (
                False,
                SignalAvailabilityReason.INSUFFICIENT_INPUT_COVERAGE,
                False,
            )
        if available_units < planned.requirement.minimum_points:
            return False, SignalAvailabilityReason.INSUFFICIENT_HISTORY, False
        if visible_units == 0:
            return False, SignalAvailabilityReason.INSUFFICIENT_HISTORY, False
        if partial_coverage:
            reason = SignalAvailabilityReason.DATA_GAP if calendar_gap_slots else SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE
            return True, reason, True
        if not warmup_complete:
            return True, SignalAvailabilityReason.INCOMPLETE_WARMUP, False
        return True, None, False

    @staticmethod
    def _availability_warnings(
        availability: SignalAvailability,
        warmup: SignalWarmupMetadata,
        price_points: list[SignalPricePoint],
        selected_points: list[SignalPricePoint],
        context: SignalExecutionContext,
    ) -> list[SignalWarning]:
        warnings: list[SignalWarning] = []
        if not warmup.complete:
            warnings.append(
                SignalWarning(
                    code=SignalWarningCode.INCOMPLETE_WARMUP,
                    message="Signal warm-up is incomplete",
                    details={
                        "used_points": warmup.used_points,
                        "required_points": warmup.requirement.total_points,
                    },
                )
            )
        if availability.partial_coverage_used:
            warning_code = SignalWarningCode.DATA_GAP if availability.reason_code == SignalAvailabilityReason.DATA_GAP else SignalWarningCode.PARTIAL_INPUT_COVERAGE
            selected_dates = {point.date for point in selected_points}
            excluded_points = [point for point in price_points if point.date not in selected_dates]
            selected_start = selected_points[0].date if selected_points else None
            selected_end = selected_points[-1].date if selected_points else None
            requested_end = context.requested_range.end or context.requested_range.start
            warnings.append(
                SignalWarning(
                    code=warning_code,
                    message="Signal used one complete contiguous input segment",
                    details={
                        "coverage_ratio": availability.input_coverage.coverage_ratio,
                        "contiguous_points": availability.input_coverage.contiguous_points,
                        "selected_start_date": max(selected_start, context.requested_range.start).isoformat() if selected_start else None,
                        "selected_end_date": min(selected_end, requested_end).isoformat() if selected_end else None,
                        "excluded_points": len(excluded_points),
                        "first_excluded_date": excluded_points[0].date.isoformat() if excluded_points else None,
                    },
                )
            )
        return warnings

    @classmethod
    def _normalize_computation(
        cls,
        raw_computation: Any,
    ) -> SignalComputation:
        if isinstance(raw_computation, BaseModel):
            raw_computation = raw_computation.model_dump(mode="python")
        sanitized = cls._sanitize_output(raw_computation)
        return SignalComputation.model_validate(sanitized)

    @classmethod
    def _visible_output_state(
        cls,
        series: list[SignalSeries],
        context: SignalExecutionContext,
    ) -> tuple[bool, bool]:
        all_series_have_finite = True
        visible_has_missing = False
        for item in series:
            visible_points = [point for point in item.points if cls._date_is_visible(point.date, context)]
            if isinstance(item, SignalBandSeries):
                values = [
                    value
                    for point in visible_points
                    for value in (
                        point.lower,
                        point.middle,
                        point.upper,
                    )
                ]
            else:
                values = [point.value for point in visible_points]
            if not any(value is not None for value in values):
                all_series_have_finite = False
            if any(value is None for value in values):
                visible_has_missing = True
        return all_series_have_finite, visible_has_missing

    @staticmethod
    def _visible_history_unavailable(
        availability: SignalAvailability,
    ) -> SignalAvailability:
        data = availability.model_dump(mode="python")
        data.update(
            {
                "can_compute": False,
                "partial_coverage_used": False,
                "reason_code": SignalAvailabilityReason.INSUFFICIENT_HISTORY,
            }
        )
        return SignalAvailability.model_validate(data)

    @classmethod
    def _sanitize_output(
        cls,
        value: Any,
        path: str = "output",
    ) -> Any:
        if isinstance(value, float):
            if math.isnan(value):
                return None
            if math.isinf(value):
                raise SignalNonFiniteOutputError(f"{path} contains infinity")
            return value
        if isinstance(value, Decimal):
            if not value.is_finite():
                if value.is_nan():
                    return None
                raise SignalNonFiniteOutputError(f"{path} contains infinity")
            return value
        if isinstance(value, dict):
            return {key: cls._sanitize_output(item, f"{path}.{key}") for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._sanitize_output(item, f"{path}[{index}]") for index, item in enumerate(value)]
        return value

    @staticmethod
    def _validate_plugin_output(
        plugin_class: type[SignalPlugin],
        computation: SignalComputation,
        selected_points: list[SignalPricePoint],
    ) -> None:
        expected_specs = plugin_class.output_specs
        if len(computation.series) != len(expected_specs):
            raise SignalOutputContractError("plugin output count does not match output_specs")
        for series, spec in zip(
            computation.series,
            expected_specs,
            strict=True,
        ):
            if series.key != spec.key or series.kind != spec.kind or series.label_key != spec.label_key or series.unit != spec.unit or series.axis != spec.axis or series.view_transform != spec.view_transform:
                raise SignalOutputContractError(f"plugin output metadata does not match spec '{spec.key}'")

        if selected_points and plugin_class.input_requirements.price_fields:
            expected_dates = [point.date for point in selected_points]
            for series in computation.series:
                actual_dates = [point.date for point in series.points]
                if actual_dates != expected_dates:
                    raise SignalOutputContractError(f"series '{series.key}' dates/cardinality do not match input")

    @classmethod
    def _slice_series(
        cls,
        series: list[SignalSeries],
        context: SignalExecutionContext,
    ) -> list[SignalSeries]:
        sliced: list[SignalSeries] = []
        for item in series:
            data = item.model_dump(mode="python", exclude={"points"})
            data["points"] = [point.model_dump(mode="python") for point in item.points if cls._date_is_visible(point.date, context)]
            sliced.append(type(item).model_validate(data))
        return sliced

    @staticmethod
    def _date_is_visible(
        value: date,
        context: SignalExecutionContext,
    ) -> bool:
        end = context.requested_range.end or context.requested_range.start
        return context.requested_range.start <= value <= end

    @classmethod
    def _longest_contiguous_run(
        cls,
        price_points: list[SignalPricePoint],
        valid_flags: list[bool],
        cadence: SignalCadence,
    ) -> int:
        longest = 0
        current = 0
        for index, valid in enumerate(valid_flags):
            if not valid:
                current = 0
                continue
            if (
                index > 0
                and valid_flags[index - 1]
                and cls._gap_slots(
                    price_points[index - 1].date,
                    price_points[index].date,
                    cadence,
                )
                == 0
            ):
                current += 1
            else:
                current = 1
            longest = max(longest, current)
        return longest

    @classmethod
    def _boundary_missing_slots(
        cls,
        price_points: list[SignalPricePoint],
        context: SignalExecutionContext,
    ) -> int:
        if not price_points:
            return 0
        end = context.requested_range.end or context.requested_range.start
        if context.cadence == SignalCadence.IRREGULAR:
            return 0 if any(context.requested_range.start <= point.date <= end for point in price_points) else 1
        before = (
            cls._distance_slots(
                context.requested_range.start,
                price_points[0].date,
                context.cadence,
            )
            if price_points[0].date > context.requested_range.start
            else 0
        )
        after = (
            cls._distance_slots(
                price_points[-1].date,
                end,
                context.cadence,
            )
            if price_points[-1].date < end
            else 0
        )
        return before + after

    @classmethod
    def _visible_slot_count(
        cls,
        context: SignalExecutionContext,
    ) -> int:
        end = context.requested_range.end or context.requested_range.start
        if context.cadence == SignalCadence.IRREGULAR:
            return 0
        return (
            cls._distance_slots(
                context.requested_range.start,
                end,
                context.cadence,
            )
            + 1
        )

    @classmethod
    def _gap_slots(
        cls,
        previous: date,
        current: date,
        cadence: SignalCadence,
    ) -> int:
        return max(
            0,
            cls._distance_slots(previous, current, cadence) - 1,
        )

    @staticmethod
    def _distance_slots(
        start: date,
        end: date,
        cadence: SignalCadence,
    ) -> int:
        if cadence == SignalCadence.DAILY:
            return (end - start).days
        if cadence == SignalCadence.WEEKLY:
            days = (end - start).days
            return math.ceil(days / 7)
        if cadence == SignalCadence.MONTHLY:
            return (end.year - start.year) * 12 + end.month - start.month
        return 0


__all__ = [
    "PlannedSignal",
    "SignalExecutionPlan",
    "SignalNonFiniteOutputError",
    "SignalOutputContractError",
    "SignalOutputValidationError",
    "SignalService",
]
