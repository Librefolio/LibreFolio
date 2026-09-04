"""Library-independent technical annotation primitives."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Mapping, Optional, Sequence

from backend.app.schemas.signals import (
    SignalAnnotation,
    SignalAnnotationDirection,
    SignalAnnotationRequest,
    SignalAnnotationSampling,
    SignalAreaSeries,
    SignalBandSeries,
    SignalBandValueSource,
    SignalBarSeries,
    SignalCadence,
    SignalExecutionContext,
    SignalLineCrossoverRequest,
    SignalLineSeries,
    SignalOutputValueSource,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalSeries,
    SignalThresholdCrossingRequest,
    SignalThresholdDirection,
    SignalValueSource,
    SignalWarning,
    SignalWarningCode,
)


class SignalAnnotationSourceUnavailable(ValueError):
    """Raised when an annotation source cannot provide scalar values."""


@dataclass(frozen=True)
class SignalAnnotationBatch:
    annotations_by_target: dict[str, tuple[SignalAnnotation, ...]]
    warnings_by_target: dict[str, tuple[SignalWarning, ...]]


@dataclass(frozen=True)
class _ValueTimeline:
    values: dict[date, Optional[float]]
    source_metadata: dict[str, object]


class SignalAnnotationService:
    """Derive cross and threshold events from extended canonical data."""

    def compute(
        self,
        requests: Sequence[SignalAnnotationRequest],
        price_points: Sequence[SignalPricePoint],
        series_by_instance: Mapping[str, Sequence[SignalSeries]],
        context: SignalExecutionContext,
    ) -> SignalAnnotationBatch:
        annotations_by_target: dict[str, list[SignalAnnotation]] = {}
        warnings_by_target: dict[str, list[SignalWarning]] = {}
        observed_dates = {point.date for point in price_points if point.backward_fill_info is None or point.backward_fill_info.days_back == 0}
        represented_dates = {point.date for point in price_points}

        for request in requests:
            try:
                if isinstance(request, SignalLineCrossoverRequest):
                    annotations = self._line_crossovers(
                        request,
                        price_points,
                        series_by_instance,
                        context,
                        observed_dates,
                        represented_dates,
                    )
                elif isinstance(request, SignalThresholdCrossingRequest):
                    annotations = self._threshold_crossings(
                        request,
                        price_points,
                        series_by_instance,
                        context,
                        observed_dates,
                        represented_dates,
                    )
                else:
                    raise SignalAnnotationSourceUnavailable(f"Unsupported annotation request: {type(request).__name__}")
            except SignalAnnotationSourceUnavailable as exc:
                warnings_by_target.setdefault(
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
                continue

            annotations_by_target.setdefault(
                request.attach_to_instance_id,
                [],
            ).extend(annotations)

        return SignalAnnotationBatch(
            annotations_by_target={target: tuple(sorted(items, key=lambda item: item.date)) for target, items in annotations_by_target.items()},
            warnings_by_target={target: tuple(items) for target, items in warnings_by_target.items()},
        )

    def _line_crossovers(
        self,
        request: SignalLineCrossoverRequest,
        price_points: Sequence[SignalPricePoint],
        series_by_instance: Mapping[str, Sequence[SignalSeries]],
        context: SignalExecutionContext,
        observed_dates: set[date],
        represented_dates: set[date],
    ) -> list[SignalAnnotation]:
        left = self._resolve_source(
            request.left,
            price_points,
            series_by_instance,
        )
        right = self._resolve_source(
            request.right,
            price_points,
            series_by_instance,
        )
        dates = sorted(set(left.values) | set(right.values))
        events = self._crossings(
            dates=dates,
            value_pair=lambda item_date: (
                left.values.get(item_date),
                right.values.get(item_date),
            ),
            request=request,
            context=context,
            observed_dates=observed_dates,
            represented_dates=represented_dates,
            values_for_event=lambda left_value, right_value: {
                "left": left_value,
                "right": right_value,
                "difference": left_value - right_value,
            },
            metadata={
                "left": left.source_metadata,
                "right": right.source_metadata,
            },
        )
        return self._limit_events(
            events,
            request.limit,
            request.sampling,
        )

    def _threshold_crossings(
        self,
        request: SignalThresholdCrossingRequest,
        price_points: Sequence[SignalPricePoint],
        series_by_instance: Mapping[str, Sequence[SignalSeries]],
        context: SignalExecutionContext,
        observed_dates: set[date],
        represented_dates: set[date],
    ) -> list[SignalAnnotation]:
        source = self._resolve_source(
            request.source,
            price_points,
            series_by_instance,
        )
        events = self._crossings(
            dates=sorted(source.values),
            value_pair=lambda item_date: (
                source.values.get(item_date),
                request.threshold,
            ),
            request=request,
            context=context,
            observed_dates=observed_dates,
            represented_dates=represented_dates,
            values_for_event=lambda value, threshold: {
                "value": value,
                "threshold": threshold,
                "difference": value - threshold,
            },
            metadata={"source": source.source_metadata},
        )
        if request.direction != SignalThresholdDirection.BOTH:
            events = [event for event in events if event.direction.value == request.direction.value]
        return self._limit_events(
            events,
            request.limit,
            request.sampling,
        )

    def _crossings(  # noqa: C901 — TODO(P2-refactor): stateful crossing detection, nested gap/equality branches
        self,
        *,
        dates: Sequence[date],
        value_pair,
        request: SignalLineCrossoverRequest | SignalThresholdCrossingRequest,
        context: SignalExecutionContext,
        observed_dates: set[date],
        represented_dates: set[date],
        values_for_event,
        metadata: dict[str, object],
    ) -> list[SignalAnnotation]:
        events: list[SignalAnnotation] = []
        last_side: Optional[int] = None
        pending_equality: Optional[tuple[date, float, float]] = None
        previous_date: Optional[date] = None
        last_event_date: Optional[date] = None

        for item_date in dates:
            if request.observed_only and item_date not in observed_dates:
                continue
            if (
                previous_date is not None
                and self._has_cadence_gap(
                    previous_date,
                    item_date,
                    context.cadence,
                )
                and not self._gap_contains_only_represented_backfill(
                    previous_date,
                    item_date,
                    context.cadence,
                    represented_dates,
                    observed_dates,
                    request.observed_only,
                )
            ):
                last_side = None
                pending_equality = None
            previous_date = item_date

            left_value, right_value = value_pair(item_date)
            if left_value is None or right_value is None:
                last_side = None
                pending_equality = None
                continue

            left_float = float(left_value)
            right_float = float(right_value)
            if not math.isfinite(left_float) or not math.isfinite(right_float):
                last_side = None
                pending_equality = None
                continue
            side = self._side(
                left_float - right_float,
                self._effective_epsilon(
                    left_float,
                    right_float,
                    request.epsilon,
                    request.relative_epsilon,
                ),
            )
            if side == 0:
                if last_side is not None and pending_equality is None:
                    pending_equality = (
                        item_date,
                        left_float,
                        right_float,
                    )
                continue

            if last_side is not None and side != last_side:
                if pending_equality is not None and self._date_is_visible(
                    pending_equality[0],
                    context,
                ):
                    event_date, event_left, event_right = pending_equality
                else:
                    event_date = item_date
                    event_left = left_float
                    event_right = right_float
                if self._date_is_visible(event_date, context) and (last_event_date is None or (event_date - last_event_date).days >= request.min_gap_days):
                    direction = SignalAnnotationDirection.UP if side > last_side else SignalAnnotationDirection.DOWN
                    events.append(
                        SignalAnnotation(
                            key=request.key,
                            annotation_type=request.kind,
                            date=event_date,
                            direction=direction,
                            values=values_for_event(
                                event_left,
                                event_right,
                            ),
                            metadata=metadata,
                        )
                    )
                    last_event_date = event_date

            last_side = side
            pending_equality = None

        return events

    @staticmethod
    def _resolve_source(
        source: SignalValueSource,
        price_points: Sequence[SignalPricePoint],
        series_by_instance: Mapping[str, Sequence[SignalSeries]],
    ) -> _ValueTimeline:
        if isinstance(source, SignalPriceValueSource):
            return _ValueTimeline(
                values={
                    point.date: (
                        float(value)
                        if (
                            value := getattr(
                                point,
                                source.field.value,
                            )
                        )
                        is not None
                        else None
                    )
                    for point in price_points
                },
                source_metadata=source.model_dump(mode="json"),
            )
        if isinstance(source, SignalOutputValueSource):
            series = series_by_instance.get(source.instance_id)
            if series is None:
                raise SignalAnnotationSourceUnavailable(f"Signal instance '{source.instance_id}' has no extended output")
            selected = next(
                (item for item in series if item.key == source.series_key),
                None,
            )
            if selected is None:
                raise SignalAnnotationSourceUnavailable(f"Series '{source.series_key}' is missing from '{source.instance_id}'")
            if not isinstance(selected, (SignalLineSeries, SignalAreaSeries, SignalBarSeries)):
                raise SignalAnnotationSourceUnavailable(f"Series '{source.series_key}' is not scalar")
            return _ValueTimeline(
                values={point.date: point.value for point in selected.points},
                source_metadata=source.model_dump(mode="json"),
            )
        if isinstance(source, SignalBandValueSource):
            series = series_by_instance.get(source.instance_id)
            if series is None:
                raise SignalAnnotationSourceUnavailable(f"Signal instance '{source.instance_id}' has no extended output")
            selected = next(
                (item for item in series if item.key == source.series_key),
                None,
            )
            if selected is None:
                raise SignalAnnotationSourceUnavailable(f"Series '{source.series_key}' is missing from '{source.instance_id}'")
            if not isinstance(selected, SignalBandSeries):
                raise SignalAnnotationSourceUnavailable(f"Series '{source.series_key}' is not a band")
            return _ValueTimeline(
                values={point.date: getattr(point, source.component.value) for point in selected.points},
                source_metadata=source.model_dump(mode="json"),
            )
        raise SignalAnnotationSourceUnavailable(f"Unsupported source: {type(source).__name__}")

    @staticmethod
    def _side(difference: float, epsilon: float) -> int:
        if difference > epsilon:
            return 1
        if difference < -epsilon:
            return -1
        return 0

    @staticmethod
    def _effective_epsilon(
        left: float,
        right: float,
        absolute_epsilon: float,
        relative_epsilon: float,
    ) -> float:
        return max(
            absolute_epsilon,
            relative_epsilon * max(abs(left), abs(right)),
        )

    @staticmethod
    def _limit_events(
        events: list[SignalAnnotation],
        limit: Optional[int],
        sampling: SignalAnnotationSampling,
    ) -> list[SignalAnnotation]:
        if limit is None or len(events) <= limit:
            return events
        if sampling == SignalAnnotationSampling.RECENT:
            return events[-limit:]
        if limit == 1:
            return [events[(len(events) - 1) // 2]]
        indexes = [round(index * (len(events) - 1) / (limit - 1)) for index in range(limit)]
        return [events[index] for index in indexes]

    @staticmethod
    def _date_is_visible(
        value: date,
        context: SignalExecutionContext,
    ) -> bool:
        end = context.requested_range.end or context.requested_range.start
        return context.requested_range.start <= value <= end

    @staticmethod
    def _has_cadence_gap(
        previous: date,
        current: date,
        cadence: SignalCadence,
    ) -> bool:
        if cadence == SignalCadence.IRREGULAR:
            return False
        if cadence == SignalCadence.DAILY:
            return (current - previous).days > 1
        if cadence == SignalCadence.WEEKLY:
            return (current - previous).days > 7
        month_distance = (current.year - previous.year) * 12 + current.month - previous.month
        return month_distance > 1

    @staticmethod
    def _gap_contains_only_represented_backfill(
        previous: date,
        current: date,
        cadence: SignalCadence,
        represented_dates: set[date],
        observed_dates: set[date],
        observed_only: bool,
    ) -> bool:
        if not observed_only or cadence != SignalCadence.DAILY or (current - previous).days <= 1:
            return False
        current_date = previous + timedelta(days=1)
        while current_date < current:
            if current_date not in represented_dates or current_date in observed_dates:
                return False
            current_date += timedelta(days=1)
        return True


__all__ = [
    "SignalAnnotationBatch",
    "SignalAnnotationService",
    "SignalAnnotationSourceUnavailable",
]
