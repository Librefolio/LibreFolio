"""Pure input preparation for technical signal execution."""

from __future__ import annotations

from collections import Counter
from typing import Optional

from backend.app.schemas.signals import (
    SignalAvailability,
    SignalAvailabilityReason,
    SignalBandSeries,
    SignalCadence,
    SignalDataPolicy,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputCoverage,
    SignalInputRequirements,
    SignalPriceField,
    SignalPricePoint,
    SignalSeries,
    SignalSourceCapability,
    SignalWarmupMetadata,
    SignalWarning,
    SignalWarningCode,
)
from backend.app.services.series_preparation import (
    date_is_within_range,
    distance_slots,
    gap_slots,
)


def _visible_slot_count(context: SignalExecutionContext) -> int:
    end = context.requested_range.end or context.requested_range.start
    if context.cadence == SignalCadence.IRREGULAR:
        return 0
    return (
        distance_slots(
            context.requested_range.start,
            end,
            context.cadence.value,
        )
        + 1
    )


def _boundary_missing_slots(
    price_points: list[SignalPricePoint],
    context: SignalExecutionContext,
) -> int:
    if not price_points:
        return 0
    end = context.requested_range.end or context.requested_range.start
    if context.cadence == SignalCadence.IRREGULAR:
        return 0 if any(date_is_within_range(point.date, context.requested_range.start, end) for point in price_points) else 1
    before = (
        distance_slots(
            context.requested_range.start,
            price_points[0].date,
            context.cadence.value,
        )
        if price_points[0].date > context.requested_range.start
        else 0
    )
    after = (
        distance_slots(
            price_points[-1].date,
            end,
            context.cadence.value,
        )
        if price_points[-1].date < end
        else 0
    )
    return before + after


def _longest_contiguous_run(
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
            and gap_slots(
                price_points[index - 1].date,
                price_points[index].date,
                cadence.value,
            )
            == 0
        ):
            current += 1
        else:
            current = 1
        longest = max(longest, current)
    return longest


def _max_consecutive_missing_points(
    price_points: list[SignalPricePoint],
    valid_flags: list[bool],
    context: SignalExecutionContext,
) -> int:
    if not price_points:
        return _visible_slot_count(context)

    end = context.requested_range.end or context.requested_range.start
    current = (
        distance_slots(
            context.requested_range.start,
            price_points[0].date,
            context.cadence.value,
        )
        if price_points[0].date > context.requested_range.start
        else 0
    )
    maximum = current
    for index, (point, valid) in enumerate(
        zip(
            price_points,
            valid_flags,
            strict=True,
        )
    ):
        if index > 0:
            current += gap_slots(
                price_points[index - 1].date,
                point.date,
                context.cadence.value,
            )
            maximum = max(maximum, current)
        if valid:
            current = 0
        else:
            current += 1
            maximum = max(maximum, current)
    if price_points[-1].date < end:
        current += distance_slots(
            price_points[-1].date,
            end,
            context.cadence.value,
        )
        maximum = max(maximum, current)
    return maximum


def build_signal_coverage(
    price_points: list[SignalPricePoint],
    event_points: list[SignalEventPoint],
    required_fields: list[SignalPriceField],
    context: SignalExecutionContext,
) -> tuple[SignalInputCoverage, list[bool], int]:
    """Build source coverage without invoking a signal plugin."""
    valid_flags = [all(getattr(point, field.value) is not None for field in required_fields) for point in price_points]
    internal_calendar_gaps = sum(
        gap_slots(
            previous.date,
            current.date,
            context.cadence.value,
        )
        for previous, current in zip(
            price_points,
            price_points[1:],
            strict=False,
        )
    )
    boundary_missing = _boundary_missing_slots(price_points, context)
    expected_points = len(price_points) + internal_calendar_gaps + boundary_missing
    if not price_points and required_fields:
        expected_points = _visible_slot_count(context)

    available_points = sum(valid_flags)
    missing_points = expected_points - available_points
    invalid_internal = sum(1 for index, valid in enumerate(valid_flags) if not valid and any(valid_flags[:index]) and any(valid_flags[index + 1 :]))
    internal_gap_count = internal_calendar_gaps + invalid_internal
    contiguous_points = _longest_contiguous_run(
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
        max_consecutive_missing_points=(
            _max_consecutive_missing_points(
                price_points,
                valid_flags,
                context,
            )
            if required_fields
            else 0
        ),
        internal_gap_count=internal_gap_count,
        coverage_ratio=(available_points / expected_points if expected_points else 0.0),
        field_coverage=field_coverage,
        event_type_counts=dict(event_counts),
        first_available_date=available_dates[0] if available_dates else None,
        last_available_date=available_dates[-1] if available_dates else None,
    )
    return coverage, valid_flags, internal_calendar_gaps


def select_signal_computation_points(
    price_points: list[SignalPricePoint],
    valid_flags: list[bool],
    cadence: SignalCadence,
    data_policy: SignalDataPolicy,
    minimum_points: int,
) -> list[SignalPricePoint]:
    """Select the complete input or one contiguous segment per plugin policy."""
    if not price_points:
        return []
    has_date_gap = any(
        gap_slots(previous.date, current.date, cadence.value) > 0
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
            and gap_slots(
                price_points[index - 1].date,
                point.date,
                cadence.value,
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


def select_signal_events(
    event_points: list[SignalEventPoint],
    event_types: list[str],
) -> list[SignalEventPoint]:
    """Filter events to the types declared by the plugin."""
    if not event_types:
        return event_points
    allowed = set(event_types)
    return [event for event in event_points if event.type in allowed]


def resolve_signal_availability(
    *,
    requirements: SignalInputRequirements,
    minimum_points: int,
    statically_compatible: bool,
    coverage: SignalInputCoverage,
    missing_price_fields: list[SignalPriceField],
    missing_event_types: list[str],
    available_units: int,
    visible_units: int,
    warmup_complete: bool,
    calendar_gap_slots: int,
    source_capability: SignalSourceCapability,
) -> tuple[bool, Optional[SignalAvailabilityReason], bool]:
    """Resolve signal availability from prepared coverage and plugin requirements."""
    if not statically_compatible:
        return False, SignalAvailabilityReason.INCOMPATIBLE_DOMAIN, False
    if missing_event_types:
        return False, SignalAvailabilityReason.MISSING_EVENT_TYPES, False
    if missing_price_fields:
        return False, SignalAvailabilityReason.MISSING_INPUT_FIELDS, False
    if requirements.requires_meaningful_volume and not source_capability.supports_meaningful_volume:
        # Semantic gate: the volume field is structurally present (checked
        # above) but its *meaning* is not vouched for by the source(s) that
        # produced this series (unknown/mixed/manual/no-volume sources).
        return False, SignalAvailabilityReason.MISSING_SOURCE_CAPABILITY, False
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
    if available_units < minimum_points:
        return False, SignalAvailabilityReason.INSUFFICIENT_HISTORY, False
    if visible_units == 0:
        return False, SignalAvailabilityReason.INSUFFICIENT_HISTORY, False
    if partial_coverage:
        reason = SignalAvailabilityReason.DATA_GAP if calendar_gap_slots else SignalAvailabilityReason.PARTIAL_INPUT_COVERAGE
        return True, reason, True
    if not warmup_complete:
        return True, SignalAvailabilityReason.INCOMPLETE_WARMUP, False
    return True, None, False


def build_signal_availability_warnings(
    availability: SignalAvailability,
    warmup: SignalWarmupMetadata,
    price_points: list[SignalPricePoint],
    selected_points: list[SignalPricePoint],
    context: SignalExecutionContext,
) -> list[SignalWarning]:
    """Build service-owned warnings for warm-up and partial coverage."""
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
                    "max_consecutive_missing_points": availability.input_coverage.max_consecutive_missing_points,
                    "selected_start_date": max(selected_start, context.requested_range.start).isoformat() if selected_start else None,
                    "selected_end_date": min(selected_end, requested_end).isoformat() if selected_end else None,
                    "excluded_points": len(excluded_points),
                    "first_excluded_date": excluded_points[0].date.isoformat() if excluded_points else None,
                },
            )
        )
    return warnings


def visible_signal_output_state(
    series: list[SignalSeries],
    context: SignalExecutionContext,
) -> tuple[bool, bool]:
    """Report whether each visible series has values and whether any are missing."""
    all_series_have_finite = True
    visible_has_missing = False
    for item in series:
        visible_points = [
            point
            for point in item.points
            if date_is_within_range(
                point.date,
                context.requested_range.start,
                context.requested_range.end,
            )
        ]
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


def slice_signal_series(
    series: list[SignalSeries],
    context: SignalExecutionContext,
) -> list[SignalSeries]:
    """Slice canonical signal output to the requested inclusive range."""
    sliced: list[SignalSeries] = []
    for item in series:
        data = item.model_dump(mode="python", exclude={"points"})
        data["points"] = [
            point.model_dump(mode="python")
            for point in item.points
            if date_is_within_range(
                point.date,
                context.requested_range.start,
                context.requested_range.end,
            )
        ]
        sliced.append(type(item).model_validate(data))
    return sliced


__all__ = [
    "build_signal_availability_warnings",
    "build_signal_coverage",
    "resolve_signal_availability",
    "select_signal_computation_points",
    "select_signal_events",
    "slice_signal_series",
    "visible_signal_output_state",
]
