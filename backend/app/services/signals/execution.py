"""The execution of a planned signal batch: prepared inputs, coverage and availability, the plugin call, its
failures and the visible slice of its output."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Optional

from pydantic import ValidationError

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
    SignalAvailability,
    SignalAvailabilityReason,
    SignalCadence,
    SignalError,
    SignalErrorCode,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputData,
    SignalPricePoint,
    SignalResult,
    SignalSeries,
    SignalSourceCapability,
    SignalStatus,
    SignalWarmupMetadata,
    SignalWarning,
    SignalWarningCode,
)
from backend.app.services.market_series import date_is_within_range
from backend.app.services.signals.annotations import SignalAnnotationService, attach_annotations
from backend.app.services.signals.base import SignalUnavailableError
from backend.app.services.signals.planning import PlannedSignal, SignalExecutionPlan
from backend.app.services.signals.series import (
    build_signal_availability_warnings,
    build_signal_coverage,
    quote_day_points,
    resolve_signal_availability,
    select_signal_computation_points,
    select_signal_events,
    slice_signal_series,
    visible_signal_output_state,
)
from backend.app.services.signals.validation import (
    SignalNonFiniteOutputError,
    SignalOutputContractError,
    SignalOutputValidationError,
    exception_details,
    normalize_computation,
    partial_metric_availability,
    unavailable_availability,
    validate_plugin_output,
    visible_history_unavailable,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class SignalPreparedSeriesBundle:
    """Prepared primary and optional comparison series for one Asset query."""

    primary_asset_id: int
    series_sets: Mapping[Optional[int], PreparedAssetSeriesSet]


def execute_signal_plan(
    annotation_service: SignalAnnotationService,
    plan: SignalExecutionPlan,
    price_points: tuple[SignalPricePoint, ...],
    event_points: tuple[SignalEventPoint, ...],
    events_loaded: bool,
    prepared_series_bundle: Optional[SignalPreparedSeriesBundle],
    source_capability: Optional[SignalSourceCapability] = None,
) -> list[SignalResult]:
    input_data = SignalInputData(
        price_points=list(price_points),
        event_points=list(event_points),
    )
    # `plan.context` is frozen at prepare_plan() time, before actual
    # price data (and thus source capability) is known. Callers that
    # discover capability from the loaded series (e.g. AssetSourceManager)
    # pass it here so it can be merged in just before per-computation
    # execution, without needing to re-plan.
    base_context = plan.context if source_capability is None else plan.context.model_copy(update={"source_capability": source_capability})
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
            ) = prepared_signal_inputs(
                computation,
                base_context,
                input_data.price_points,
                prepared_series_bundle,
            )
            result, extended_series = execute_planned_signal(
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
            logger.exception(
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
                    details=exception_details(
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
        attach_annotations(
            annotation_service,
            result_by_instance,
            plan.annotation_requests,
            input_data.price_points,
            extended_series_by_instance,
            base_context,
        )

    return [result_by_instance[request.instance_id] for request in plan.requests]


def prepared_signal_inputs(
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
    risk_metadata = risk_result_metadata(planned, prepared)
    price_points = prepared_price_points(primary)
    return (
        execution_context,
        price_points,
        risk_metadata,
        prepared.data_quality,
        forced_reason,
    )


def prepared_price_points(
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


def risk_result_metadata(
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


def risk_quality_warnings(
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


def execute_planned_signal(  # noqa: C901 — sequential availability pipeline; branches build result/error variants
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
    selected_points = (
        [
            point
            for point, valid in zip(
                price_points,
                valid_flags,
                strict=True,
            )
            if valid
        ]
        if plugin_class.allows_sparse_input_dates
        else select_signal_computation_points(
            price_points,
            valid_flags,
            coverage_context.cadence,
            requirements.data_policy,
            planned.requirement.minimum_points,
        )
    )
    # The partial-coverage warning describes the calendar segment the coverage chose; the quote-day
    # filter below is a separate, declared contract and must not count carried days as excluded.
    coverage_selected_points = selected_points
    if plugin_class.computes_on_quote_days and not requirements.uses_prepared_asset_series:
        # Indicators count sessions (developer's decision of 30/09/2026): the coverage above keeps its
        # calendar meaning, while the plugin computes on the days a price was actually quoted.
        selected_points = quote_day_points(selected_points)
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
        source_capability=context.source_capability,
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
        availability = unavailable_availability(
            availability,
            forced_unavailable_reason,
        )
        can_compute = False

    risk_warnings = risk_quality_warnings(data_quality)
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
            coverage_selected_points,
            context,
        ),
        *risk_warnings,
    ]
    try:
        plugin_class.validate_input(
            selected_points,
            selected_events,
            planned.params,
            context,
        )
        raw_computation = plugin_class().compute(
            selected_points,
            selected_events,
            planned.params,
            context,
        )
        computation = normalize_computation(raw_computation)
        validate_plugin_output(
            plugin_class,
            computation,
            selected_points,
        )
        plugin_class.validate_output(
            computation,
            selected_points,
            selected_events,
            planned.params,
            context,
        )
        all_series_have_finite, visible_has_missing = visible_signal_output_state(
            computation.series,
            context,
        )
        has_undefined_window = any(warning.code == SignalWarningCode.UNDEFINED_METRIC_WINDOW for warning in computation.warnings)
        if not all_series_have_finite:
            if not warmup.complete:
                unavailable = visible_history_unavailable(availability)
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
                unavailable = unavailable_availability(
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
        if has_undefined_window:
            availability = partial_metric_availability(availability)
        elif visible_has_missing and warmup.complete and not availability.partial_coverage_used:
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
            runtime_failure(
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
            runtime_failure(
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
            runtime_failure(
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
        unavailable = unavailable_availability(
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
        logger.exception(
            "Signal plugin compute failed",
            signal_code=plugin_class.signal_code,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return (
            runtime_failure(
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
            runtime_failure(
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


def runtime_failure(
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
            details=exception_details(
                exc,
                phase=phase,
            ),
        ),
    )
