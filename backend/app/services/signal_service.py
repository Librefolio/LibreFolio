"""Library-agnostic orchestration for technical signal plugins."""

from __future__ import annotations

import asyncio
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, TypeAdapter, ValidationError

from backend.app.logging_config import get_logger
from backend.app.schemas.common import BackwardFillInfo
from backend.app.schemas.portfolio import DataQualityReport, DataQualityStatus
from backend.app.schemas.risk import (
    PreparedAssetSeriesSet,
    RiskFreeReference,
    RiskResultMetadata,
    RiskReturnBasis,
)
from backend.app.schemas.signals import (
    SignalAnnotation,
    SignalAnnotationRequest,
    SignalAvailability,
    SignalAvailabilityReason,
    SignalBandValueSource,
    SignalCadence,
    SignalComputation,
    SignalError,
    SignalErrorCode,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputData,
    SignalLineCrossoverRequest,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalRequest,
    SignalResult,
    SignalSeries,
    SignalSeriesKind,
    SignalStatus,
    SignalThresholdCrossingRequest,
    SignalValueSource,
    SignalWarmupMetadata,
    SignalWarmupRequirement,
    SignalWarning,
    SignalWarningCode,
)
from backend.app.services.provider_registry import SignalPluginRegistry
from backend.app.services.series_preparation import date_is_within_range
from backend.app.services.signal_annotations import SignalAnnotationService
from backend.app.services.signal_plugins.base import (
    SignalPlugin,
    SignalUnavailableError,
)
from backend.app.services.signal_series_preparation import (
    build_signal_availability_warnings,
    build_signal_coverage,
    resolve_signal_availability,
    select_signal_computation_points,
    select_signal_events,
    slice_signal_series,
    visible_signal_output_state,
)

logger = get_logger(__name__)
_ANNOTATION_REQUEST_ADAPTER = TypeAdapter(SignalAnnotationRequest)


class SignalOutputValidationError(ValueError):
    """Raised when plugin output violates canonical LibreFolio contracts."""


class SignalNonFiniteOutputError(SignalOutputValidationError):
    """Raised when plugin output contains positive or negative infinity."""


class SignalOutputContractError(SignalOutputValidationError):
    """Raised when canonical output disagrees with plugin metadata."""


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
class SignalPreparedSeriesBundle:
    """Prepared primary and optional comparison series for one Asset query."""

    primary_asset_id: int
    series_sets: Mapping[Optional[int], PreparedAssetSeriesSet]


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

    @property
    def unique_computation_count(self) -> int:
        return len(self.computations)

    @property
    def max_history_points_before_visible(self) -> int:
        return self.max_total_points

    @property
    def max_prepared_history_points_before_visible(self) -> int:
        return self.max_prepared_total_points

    @property
    def requires_prepared_asset_series(self) -> bool:
        return self.max_prepared_total_points > 0


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
            for source in self._annotation_sources(annotation):
                if isinstance(source, (SignalOutputValueSource, SignalBandValueSource)) and source.instance_id not in request_ids:
                    raise SignalRequestValidationError(f"annotation source '{source.instance_id}' is not a requested signal instance")

        grouped: dict[str, dict[str, Any]] = {}
        plugin_classes_by_instance: dict[str, type[SignalPlugin]] = {}
        preflight_results: dict[str, SignalResult] = {}
        max_total_points = 0
        max_prepared_total_points = 0
        required_price_fields: set[SignalPriceField] = set()
        requires_events = False
        required_event_types: set[str] = set()
        comparison_asset_ids: set[int] = set()
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
            plugin_classes_by_instance[request.instance_id] = plugin_class

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
            comparison_asset_param = plugin_class.input_requirements.comparison_asset_param
            comparison_asset_id = int(getattr(params, comparison_asset_param)) if comparison_asset_param is not None else None
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
                "comparison_asset_id": comparison_asset_id,
            }
            if statically_compatible:
                max_total_points = max(
                    max_total_points,
                    requirement.total_points,
                )
                if plugin_class.input_requirements.uses_prepared_asset_series:
                    max_prepared_total_points = max(
                        max_prepared_total_points,
                        requirement.total_points,
                    )
                    if comparison_asset_id is not None:
                        comparison_asset_ids.add(comparison_asset_id)
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
        self._validate_annotation_output_sources(
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
        )

    async def execute(
        self,
        plan: SignalExecutionPlan,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint] = (),
        *,
        events_loaded: bool = False,
        prepared_series_bundle: Optional[SignalPreparedSeriesBundle] = None,
    ) -> list[SignalResult]:
        """Execute the entire signal batch in one worker thread."""
        return await asyncio.to_thread(
            self._execute_sync,
            plan,
            tuple(price_points),
            tuple(event_points),
            events_loaded,
            prepared_series_bundle,
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
        prepared_series_bundle: Optional[SignalPreparedSeriesBundle] = None,
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
            prepared_series_bundle=prepared_series_bundle,
        )

    def _execute_sync(
        self,
        plan: SignalExecutionPlan,
        price_points: tuple[SignalPricePoint, ...],
        event_points: tuple[SignalEventPoint, ...],
        events_loaded: bool,
        prepared_series_bundle: Optional[SignalPreparedSeriesBundle],
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
            risk_metadata: Optional[RiskResultMetadata] = None
            data_quality: Optional[DataQualityReport] = None
            try:
                (
                    execution_context,
                    computation_price_points,
                    risk_metadata,
                    data_quality,
                    forced_unavailable_reason,
                ) = self._prepared_signal_inputs(
                    computation,
                    plan.context,
                    input_data.price_points,
                    prepared_series_bundle,
                )
                result, extended_series = self._execute_planned_signal(
                    computation,
                    execution_context,
                    computation_price_points,
                    input_data.event_points,
                    events_loaded,
                    risk_metadata,
                    data_quality,
                    forced_unavailable_reason,
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
                    risk_metadata=risk_metadata,
                    data_quality=data_quality,
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

    @classmethod
    def _prepared_signal_inputs(
        cls,
        planned: PlannedSignal,
        context: SignalExecutionContext,
        default_price_points: list[SignalPricePoint],
        bundle: Optional[SignalPreparedSeriesBundle],
    ) -> tuple[
        SignalExecutionContext,
        list[SignalPricePoint],
        Optional[RiskResultMetadata],
        Optional[DataQualityReport],
        Optional[SignalAvailabilityReason],
    ]:
        requirements = planned.plugin_class.input_requirements
        if not requirements.uses_prepared_asset_series:
            return context, default_price_points, None, None, None
        if bundle is None:
            return (
                context,
                [],
                None,
                None,
                SignalAvailabilityReason.MISSING_PREPARED_SERIES,
            )

        dependency_key = planned.comparison_asset_id if requirements.comparison_asset_param is not None else None
        prepared = bundle.series_sets.get(dependency_key)
        if prepared is None:
            return (
                context,
                [],
                None,
                None,
                (SignalAvailabilityReason.MISSING_COMPARISON_SERIES if dependency_key is not None else SignalAvailabilityReason.MISSING_PREPARED_SERIES),
            )

        primary = next(
            (item for item in prepared.series if item.valuations.asset_id == bundle.primary_asset_id),
            None,
        )
        comparison = (
            next(
                (item for item in prepared.series if item.valuations.asset_id == planned.comparison_asset_id),
                None,
            )
            if planned.comparison_asset_id is not None
            else None
        )
        if comparison is None and planned.comparison_asset_id == bundle.primary_asset_id:
            comparison = primary

        forced_reason: Optional[SignalAvailabilityReason] = None
        if primary is None:
            forced_reason = SignalAvailabilityReason.MISSING_PREPARED_SERIES
        elif requirements.comparison_asset_param is not None and comparison is None:
            forced_reason = SignalAvailabilityReason.MISSING_COMPARISON_SERIES

        context_data = context.model_dump(mode="python")
        context_data.update(
            {
                "target_currency": prepared.target_currency,
                "primary_asset_series": primary,
                "comparison_asset_series": comparison,
                "annualization_factor": prepared.annualization_factor,
            }
        )
        execution_context = SignalExecutionContext.model_validate(context_data)
        risk_metadata = cls._risk_result_metadata(planned, prepared)
        price_points = cls._prepared_price_points(primary)
        return (
            execution_context,
            price_points,
            risk_metadata,
            prepared.data_quality,
            forced_reason,
        )

    @staticmethod
    def _prepared_price_points(
        primary: Any,
    ) -> list[SignalPricePoint]:
        if primary is None:
            return []
        return [
            SignalPricePoint(
                date=point.valuation_date,
                close=point.target_close,
                backward_fill_info=(
                    BackwardFillInfo(
                        actual_rate_date=point.effective_price_date,
                        days_back=(point.valuation_date - point.effective_price_date).days,
                    )
                    if point.is_price_carried_forward
                    else None
                ),
            )
            for point in primary.valuations.points
        ]

    @staticmethod
    def _risk_result_metadata(
        planned: PlannedSignal,
        prepared: PreparedAssetSeriesSet,
    ) -> RiskResultMetadata:
        risk_free = None
        if "risk_free_annual_rate" in planned.normalized_params:
            risk_free = RiskFreeReference(
                annual_rate=float(planned.normalized_params["risk_free_annual_rate"]),
                source="signal_param",
                currency=prepared.target_currency,
            )
        return RiskResultMetadata(
            analyzed_range=prepared.requested_range,
            n_observations=prepared.n_observations,
            calendar_days=prepared.calendar_days,
            annualization_factor=prepared.annualization_factor,
            coverage=prepared.calendar_coverage,
            currency=prepared.target_currency,
            method="rolling",
            params=planned.normalized_params,
            return_basis=RiskReturnBasis.PRICE_ONLY,
            comparison_asset_id=planned.comparison_asset_id,
            risk_free=risk_free,
            algorithm_version=planned.plugin_class.implementation_version,
            computed_at=datetime.now(UTC),
        )

    @staticmethod
    def _risk_quality_warnings(
        data_quality: Optional[DataQualityReport],
    ) -> list[SignalWarning]:
        if data_quality is None or data_quality.data_quality_status == DataQualityStatus.OK:
            return []
        return [
            SignalWarning(
                code=SignalWarningCode.DATA_QUALITY,
                message="Risk signal used degraded prepared price or FX data",
                details={
                    "data_quality_status": (data_quality.data_quality_status.value),
                    "carried_forward_price_points": (data_quality.carried_forward_price_points),
                    "carried_forward_fx_points": (data_quality.carried_forward_fx_points),
                    "unresolved_fx_pairs": list(data_quality.unresolved_fx_pairs),
                    "unusable_asset_ids": [item.asset_id for item in data_quality.unusable_assets],
                },
            )
        ]

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
        risk_metadata: Optional[RiskResultMetadata] = None,
        data_quality: Optional[DataQualityReport] = None,
        forced_unavailable_reason: Optional[SignalAvailabilityReason] = None,
    ) -> tuple[
        SignalResult,
        Optional[tuple[SignalSeries, ...]],
    ]:
        plugin_class = planned.plugin_class
        requirements = plugin_class.input_requirements
        coverage_context = context.model_copy(update={"cadence": SignalCadence.IRREGULAR}) if requirements.uses_prepared_asset_series else context
        coverage, valid_flags, calendar_gap_slots = build_signal_coverage(
            price_points,
            event_points,
            requirements.price_fields,
            coverage_context,
        )
        selected_points = select_signal_computation_points(
            price_points,
            valid_flags,
            coverage_context.cadence,
            requirements.data_policy,
            planned.requirement.minimum_points,
        )
        selected_events = select_signal_events(
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
        can_compute, reason_code, partial_coverage_used = resolve_signal_availability(
            requirements=requirements,
            minimum_points=planned.requirement.minimum_points,
            statically_compatible=planned.statically_compatible,
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
        if forced_unavailable_reason is not None:
            availability = self._unavailable_availability(
                availability,
                forced_unavailable_reason,
            )
            can_compute = False

        risk_warnings = self._risk_quality_warnings(data_quality)
        result_context = {
            "risk_metadata": risk_metadata,
            "data_quality": data_quality,
        }

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
                    warnings=risk_warnings,
                    **result_context,
                ),
                None,
            )

        service_warnings = [
            *build_signal_availability_warnings(
                availability,
                warmup,
                price_points,
                selected_points,
                context,
            ),
            *risk_warnings,
        ]
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
            all_series_have_finite, visible_has_missing = visible_signal_output_state(
                computation.series,
                context,
            )
            has_undefined_window = any(warning.code == SignalWarningCode.UNDEFINED_METRIC_WINDOW for warning in computation.warnings)
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
                            warnings=service_warnings,
                            **result_context,
                        ),
                        None,
                    )
                if has_undefined_window:
                    unavailable = self._unavailable_availability(
                        availability,
                        SignalAvailabilityReason.UNDEFINED_METRIC,
                    )
                    return (
                        SignalResult(
                            instance_id=planned.instance_ids[0],
                            signal_code=plugin_class.signal_code,
                            implementation_version=plugin_class.implementation_version,
                            normalized_params=planned.normalized_params,
                            status=SignalStatus.UNAVAILABLE,
                            availability=unavailable,
                            warmup=warmup,
                            warnings=[
                                *computation.warnings,
                                *service_warnings,
                            ],
                            **result_context,
                        ),
                        None,
                    )
                raise SignalOutputValidationError("visible output has no finite value for every series")
            if visible_has_missing and warmup.complete and not availability.partial_coverage_used:
                if has_undefined_window:
                    availability = self._partial_metric_availability(availability)
                else:
                    raise SignalOutputValidationError("complete visible output contains missing values")
            sliced_series = slice_signal_series(
                computation.series,
                context,
            )
            sliced_annotations = [
                annotation
                for annotation in computation.annotations
                if date_is_within_range(
                    annotation.date,
                    context.requested_range.start,
                    context.requested_range.end,
                )
            ]
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
                    risk_metadata=risk_metadata,
                    data_quality=data_quality,
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
                    risk_metadata=risk_metadata,
                    data_quality=data_quality,
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
                    risk_metadata=risk_metadata,
                    data_quality=data_quality,
                ),
                None,
            )
        except SignalUnavailableError as exc:
            unavailable = self._unavailable_availability(
                availability,
                exc.reason_code,
            )
            warning_code = SignalWarningCode.UNDEFINED_METRIC_WINDOW if exc.reason_code == SignalAvailabilityReason.UNDEFINED_METRIC else SignalWarningCode.DATA_QUALITY
            return (
                SignalResult(
                    instance_id=planned.instance_ids[0],
                    signal_code=plugin_class.signal_code,
                    implementation_version=plugin_class.implementation_version,
                    normalized_params=planned.normalized_params,
                    status=SignalStatus.UNAVAILABLE,
                    availability=unavailable,
                    warmup=warmup,
                    warnings=[
                        SignalWarning(
                            code=warning_code,
                            message=str(exc),
                            details=exc.details,
                        ),
                        *service_warnings,
                    ],
                    **result_context,
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
                    risk_metadata=risk_metadata,
                    data_quality=data_quality,
                ),
                None,
            )

        status = SignalStatus.PARTIAL if (not warmup.complete or availability.partial_coverage_used or availability.reason_code == SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC) else SignalStatus.OK
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
                    **result_context,
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
                    risk_metadata=risk_metadata,
                    data_quality=data_quality,
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
    def _validate_annotation_output_sources(
        requests: tuple[SignalAnnotationRequest, ...],
        plugin_classes_by_instance: dict[str, type[SignalPlugin]],
    ) -> None:
        for request in requests:
            for source in SignalService._annotation_sources(request):
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
        risk_metadata: Optional[RiskResultMetadata] = None,
        data_quality: Optional[DataQualityReport] = None,
    ) -> SignalResult:
        return SignalResult(
            instance_id=planned.instance_ids[0],
            signal_code=planned.plugin_class.signal_code,
            implementation_version=planned.plugin_class.implementation_version,
            normalized_params=planned.normalized_params,
            status=SignalStatus.FAILED,
            availability=availability,
            warmup=warmup,
            risk_metadata=risk_metadata,
            data_quality=data_quality,
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
    def _normalize_computation(
        cls,
        raw_computation: Any,
    ) -> SignalComputation:
        if isinstance(raw_computation, BaseModel):
            raw_computation = raw_computation.model_dump(mode="python")
        sanitized = cls._sanitize_output(raw_computation)
        return SignalComputation.model_validate(sanitized)

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

    @staticmethod
    def _unavailable_availability(
        availability: SignalAvailability,
        reason: SignalAvailabilityReason,
    ) -> SignalAvailability:
        data = availability.model_dump(mode="python")
        data.update(
            {
                "can_compute": False,
                "partial_coverage_used": False,
                "reason_code": reason,
            }
        )
        return SignalAvailability.model_validate(data)

    @staticmethod
    def _partial_metric_availability(
        availability: SignalAvailability,
    ) -> SignalAvailability:
        data = availability.model_dump(mode="python")
        data.update(
            {
                "can_compute": True,
                "partial_coverage_used": False,
                "reason_code": (SignalAvailabilityReason.PARTIAL_UNDEFINED_METRIC),
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
            if (
                series.key != spec.key
                or series.kind != spec.kind
                or series.label_key != spec.label_key
                or series.description_key != spec.description_key
                or series.semantic_id != spec.semantic_id
                or series.semantic_description != spec.semantic_description
                or series.unit != spec.unit
                or series.axis != spec.axis
                or series.view_transform != spec.view_transform
                or series.style != spec.style
            ):
                raise SignalOutputContractError(f"plugin output metadata does not match spec '{spec.key}'")

        if selected_points and plugin_class.input_requirements.price_fields:
            expected_dates = [point.date for point in selected_points]
            for series in computation.series:
                actual_dates = [point.date for point in series.points]
                if actual_dates != expected_dates:
                    raise SignalOutputContractError(f"series '{series.key}' dates/cardinality do not match input")


__all__ = [
    "PlannedSignal",
    "SignalExecutionPlan",
    "SignalNonFiniteOutputError",
    "SignalOutputContractError",
    "SignalOutputValidationError",
    "SignalPreparedSeriesBundle",
    "SignalRequestValidationError",
    "SignalService",
]
