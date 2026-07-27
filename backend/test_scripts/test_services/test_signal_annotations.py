"""Tests for library-independent signal annotation primitives."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.signals import (
    SignalAnnotationDirection,
    SignalAnnotationSampling,
    SignalAxisRole,
    SignalAxisSpec,
    SignalBandComponent,
    SignalBandPoint,
    SignalBandSeries,
    SignalBandValueSource,
    SignalDomain,
    SignalExecutionContext,
    SignalLineCrossoverRequest,
    SignalLineSeries,
    SignalOutputValueSource,
    SignalPriceField,
    SignalPricePoint,
    SignalPriceValueSource,
    SignalThresholdCrossingRequest,
    SignalThresholdDirection,
    SignalUnit,
    SignalValuePoint,
    SignalWarningCode,
)
from backend.app.services.signal_annotations import SignalAnnotationService

START = date(2026, 1, 1)


def dates(count: int, *, gap_after: int | None = None) -> list[date]:
    output: list[date] = []
    offset = 0
    for index in range(count):
        if gap_after is not None and index > gap_after:
            offset = 1
        output.append(START + timedelta(days=index + offset))
    return output


def context(
    start: date = START,
    end: date = START + timedelta(days=9),
) -> SignalExecutionContext:
    return SignalExecutionContext(
        domain=SignalDomain.ASSET,
        requested_range=DateRangeModel(start=start, end=end),
        source_reference="annotation:fixture",
    )


def price_points(
    values: list[float],
    *,
    point_dates: list[date] | None = None,
    backfilled_indexes: set[int] | None = None,
) -> list[SignalPricePoint]:
    point_dates = point_dates or dates(len(values))
    backfilled_indexes = backfilled_indexes or set()
    return [
        SignalPricePoint(
            date=point_date,
            close=Decimal(str(value)),
            backward_fill_info=(
                BackwardFillInfo(
                    actual_rate_date=point_date - timedelta(days=1),
                    days_back=1,
                )
                if index in backfilled_indexes
                else None
            ),
        )
        for index, (point_date, value) in enumerate(zip(point_dates, values, strict=True))
    ]


def line_series(
    values: list[float | None],
    *,
    key: str = "line",
    point_dates: list[date] | None = None,
) -> SignalLineSeries:
    point_dates = point_dates or dates(len(values))
    return SignalLineSeries(
        key=key,
        label_key=f"signals.{key}",
        semantic_id=f"test.{key}",
        semantic_description=f"Test semantic value for {key}.",
        unit=SignalUnit.INDEX,
        axis=SignalAxisSpec(
            key="annotation",
            role=SignalAxisRole.INDEPENDENT,
        ),
        points=[
            SignalValuePoint(date=point_date, value=value)
            for point_date, value in zip(
                point_dates,
                values,
                strict=True,
            )
        ],
    )


def band_series(
    lower: list[float | None],
    middle: list[float | None],
    upper: list[float | None],
    *,
    key: str = "envelope",
    point_dates: list[date] | None = None,
) -> SignalBandSeries:
    point_dates = point_dates or dates(len(lower))
    return SignalBandSeries(
        key=key,
        label_key=f"signals.{key}",
        semantic_id=f"test.{key}",
        semantic_description=f"Test band semantic value for {key}.",
        unit=SignalUnit.INDEX,
        axis=SignalAxisSpec(
            key="annotation",
            role=SignalAxisRole.INDEPENDENT,
        ),
        points=[
            SignalBandPoint(
                date=point_date,
                lower=lower_value,
                middle=middle_value,
                upper=upper_value,
            )
            for point_date, lower_value, middle_value, upper_value in zip(
                point_dates,
                lower,
                middle,
                upper,
                strict=True,
            )
        ],
    )


def test_line_crossover_emits_up_and_down_events():
    points = price_points([1, 2, 3, 2, 1])
    series = {"baseline": [line_series([2.5, 2.5, 2.5, 2.5, 2.5], key="baseline")]}
    request = SignalLineCrossoverRequest(
        key="price-vs-baseline",
        attach_to_instance_id="baseline",
        left=SignalPriceValueSource(field=SignalPriceField.CLOSE),
        right=SignalOutputValueSource(
            instance_id="baseline",
            series_key="baseline",
        ),
    )

    result = SignalAnnotationService().compute(
        [request],
        points,
        series,
        context(end=START + timedelta(days=4)),
    )
    events = result.annotations_by_target["baseline"]

    assert [event.date for event in events] == [
        START + timedelta(days=2),
        START + timedelta(days=3),
    ]
    assert [event.direction for event in events] == [
        SignalAnnotationDirection.UP,
        SignalAnnotationDirection.DOWN,
    ]


def test_exact_threshold_equality_uses_equality_date():
    request = SignalThresholdCrossingRequest(
        key="threshold",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=2,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 2, 3]),
        {"signal": [line_series([1, 2, 3])]},
        context(end=START + timedelta(days=2)),
    )
    event = result.annotations_by_target["signal"][0]

    assert event.date == START + timedelta(days=1)
    assert event.direction == SignalAnnotationDirection.UP
    assert event.values == {
        "value": 2.0,
        "threshold": 2.0,
        "difference": 0.0,
    }


def test_threshold_direction_filter_keeps_downward_only():
    request = SignalThresholdCrossingRequest(
        key="threshold",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=2,
        direction=SignalThresholdDirection.DOWN,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([3, 2, 1]),
        {"signal": [line_series([3, 2, 1])]},
        context(end=START + timedelta(days=2)),
    )

    assert len(result.annotations_by_target["signal"]) == 1
    assert result.annotations_by_target["signal"][0].direction == SignalAnnotationDirection.DOWN


def test_previsible_point_detects_cross_at_visible_boundary():
    request = SignalThresholdCrossingRequest(
        key="boundary",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=0,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 1]),
        {"signal": [line_series([-1, 1])]},
        context(
            start=START + timedelta(days=1),
            end=START + timedelta(days=1),
        ),
    )

    event = result.annotations_by_target["signal"][0]
    assert event.date == START + timedelta(days=1)
    assert event.direction == SignalAnnotationDirection.UP


def test_previsible_equality_uses_visible_confirmation_date():
    request = SignalThresholdCrossingRequest(
        key="boundary-equality",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=0,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 1, 1]),
        {"signal": [line_series([-1, 0, 1])]},
        context(
            start=START + timedelta(days=2),
            end=START + timedelta(days=2),
        ),
    )

    event = result.annotations_by_target["signal"][0]
    assert event.date == START + timedelta(days=2)
    assert event.direction == SignalAnnotationDirection.UP


def test_missing_value_resets_cross_state():
    request = SignalThresholdCrossingRequest(
        key="missing",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=2,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 2, 3]),
        {"signal": [line_series([1, None, 3])]},
        context(end=START + timedelta(days=2)),
    )

    assert result.annotations_by_target.get("signal", ()) == ()


def test_date_gap_does_not_bridge_crossing():
    point_dates = dates(2, gap_after=0)
    request = SignalThresholdCrossingRequest(
        key="gap",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=2,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 3], point_dates=point_dates),
        {
            "signal": [
                line_series(
                    [1, 3],
                    point_dates=point_dates,
                )
            ]
        },
        context(end=point_dates[-1]),
    )

    assert result.annotations_by_target.get("signal", ()) == ()


def test_observed_only_excludes_backfilled_crossing():
    points = price_points(
        [1, 2, 3],
        backfilled_indexes={1},
    )
    base = {
        "key": "observed",
        "attach_to_instance_id": "signal",
        "source": SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        "threshold": 0,
    }
    service = SignalAnnotationService()

    all_points = service.compute(
        [SignalThresholdCrossingRequest(**base)],
        points,
        {"signal": [line_series([-1, 1, 2])]},
        context(end=START + timedelta(days=2)),
    )
    observed = service.compute(
        [
            SignalThresholdCrossingRequest(
                **base,
                observed_only=True,
            )
        ],
        points,
        {"signal": [line_series([-1, 1, 2])]},
        context(end=START + timedelta(days=2)),
    )

    assert len(all_points.annotations_by_target["signal"]) == 1
    assert observed.annotations_by_target.get("signal", ()) == ()


def test_min_gap_deduplicates_dense_crossings():
    values = [-1, 1, -1, 1, -1, 1]
    request = SignalThresholdCrossingRequest(
        key="dedup",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=0,
        min_gap_days=3,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1] * len(values)),
        {"signal": [line_series(values)]},
        context(end=START + timedelta(days=len(values) - 1)),
    )

    assert [event.date for event in result.annotations_by_target["signal"]] == [
        START + timedelta(days=1),
        START + timedelta(days=4),
    ]


def test_recent_and_uniform_limits_preserve_order():
    values = [-1, 1, -1, 1, -1, 1, -1]
    recent = SignalThresholdCrossingRequest(
        key="recent",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=0,
        limit=2,
        sampling=SignalAnnotationSampling.RECENT,
    )
    uniform = SignalThresholdCrossingRequest(
        key="uniform",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=0,
        limit=3,
        sampling=SignalAnnotationSampling.UNIFORM,
    )
    result = SignalAnnotationService().compute(
        [recent, uniform],
        price_points([1] * len(values)),
        {"signal": [line_series(values)]},
        context(end=START + timedelta(days=len(values) - 1)),
    )
    events = result.annotations_by_target["signal"]

    recent_dates = [event.date for event in events if event.key == "recent"]
    uniform_dates = [event.date for event in events if event.key == "uniform"]
    assert recent_dates == [
        START + timedelta(days=5),
        START + timedelta(days=6),
    ]
    assert uniform_dates == [
        START + timedelta(days=1),
        START + timedelta(days=3),
        START + timedelta(days=6),
    ]


def test_uniform_limit_one_selects_middle_event():
    values = [-1, 1, -1, 1, -1, 1]
    request = SignalThresholdCrossingRequest(
        key="uniform-one",
        attach_to_instance_id="signal",
        source=SignalOutputValueSource(
            instance_id="signal",
            series_key="line",
        ),
        threshold=0,
        limit=1,
        sampling=SignalAnnotationSampling.UNIFORM,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1] * len(values)),
        {"signal": [line_series(values)]},
        context(end=START + timedelta(days=len(values) - 1)),
    )

    event = result.annotations_by_target["signal"][0]
    assert event.date == START + timedelta(days=3)


def test_signal_to_signal_crossover_uses_common_extended_dates():
    request = SignalLineCrossoverRequest(
        key="signal-cross",
        attach_to_instance_id="fast",
        left=SignalOutputValueSource(
            instance_id="fast",
            series_key="line",
        ),
        right=SignalOutputValueSource(
            instance_id="slow",
            series_key="line",
        ),
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 1, 1]),
        {
            "fast": [line_series([1, 2, 3])],
            "slow": [line_series([2, 2, 2])],
        },
        context(end=START + timedelta(days=2)),
    )

    event = result.annotations_by_target["fast"][0]
    assert event.date == START + timedelta(days=1)
    assert event.direction == SignalAnnotationDirection.UP


@pytest.mark.parametrize(
    "component",
    [
        SignalBandComponent.LOWER,
        SignalBandComponent.MIDDLE,
        SignalBandComponent.UPPER,
    ],
)
def test_band_source_crosses_for_each_component(component: SignalBandComponent):
    source = SignalBandValueSource(
        instance_id="band",
        series_key="envelope",
        component=component,
    )
    request = SignalThresholdCrossingRequest(
        key=f"{component.value}-threshold",
        attach_to_instance_id="band",
        source=source,
        threshold=0.5,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 1]),
        {
            "band": [
                band_series(
                    [-2, 2],
                    [-1, 3],
                    [0, 4],
                )
            ]
        },
        context(end=START + timedelta(days=1)),
    )

    event = result.annotations_by_target["band"][0]
    assert event.date == START + timedelta(days=1)
    assert event.direction == SignalAnnotationDirection.UP
    assert event.metadata["source"] == source.model_dump(mode="json")


def test_band_source_preserves_null_dates_and_resets_cross_state():
    source = SignalBandValueSource(
        instance_id="band",
        series_key="envelope",
        component=SignalBandComponent.MIDDLE,
    )
    series = band_series(
        [-2, None, 0],
        [-1, None, 1],
        [0, None, 2],
    )
    timeline = SignalAnnotationService._resolve_source(
        source,
        [],
        {"band": [series]},
    )
    request = SignalThresholdCrossingRequest(
        key="middle-null-gap",
        attach_to_instance_id="band",
        source=source,
        threshold=0,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1, 1, 1]),
        {"band": [series]},
        context(end=START + timedelta(days=2)),
    )

    assert timeline.values == {
        START: -1.0,
        START + timedelta(days=1): None,
        START + timedelta(days=2): 1.0,
    }
    assert timeline.source_metadata == source.model_dump(mode="json")
    assert result.annotations_by_target.get("band", ()) == ()


@pytest.mark.parametrize(
    ("source", "series_by_instance", "reason"),
    [
        (
            SignalBandValueSource(
                instance_id="missing",
                series_key="envelope",
                component=SignalBandComponent.LOWER,
            ),
            {},
            "has no extended output",
        ),
        (
            SignalBandValueSource(
                instance_id="band",
                series_key="missing",
                component=SignalBandComponent.MIDDLE,
            ),
            {"band": [band_series([0], [1], [2])]},
            "is missing",
        ),
        (
            SignalBandValueSource(
                instance_id="line",
                series_key="line",
                component=SignalBandComponent.UPPER,
            ),
            {"line": [line_series([1])]},
            "is not a band",
        ),
    ],
)
def test_unavailable_band_sources_return_structured_warning(
    source: SignalBandValueSource,
    series_by_instance,
    reason: str,
):
    request = SignalThresholdCrossingRequest(
        key="band-unavailable",
        attach_to_instance_id="target",
        source=source,
        threshold=0,
    )
    result = SignalAnnotationService().compute(
        [request],
        price_points([1]),
        series_by_instance,
        context(end=START),
    )

    warning = result.warnings_by_target["target"][0]
    assert warning.code == SignalWarningCode.ANNOTATION_UNAVAILABLE
    assert reason in warning.details["reason"]


def test_missing_or_non_scalar_source_returns_structured_warning():
    missing = SignalThresholdCrossingRequest(
        key="missing-source",
        attach_to_instance_id="target",
        source=SignalOutputValueSource(
            instance_id="missing",
            series_key="line",
        ),
        threshold=0,
    )
    band = SignalThresholdCrossingRequest(
        key="band-source",
        attach_to_instance_id="target",
        source=SignalOutputValueSource(
            instance_id="band",
            series_key="envelope",
        ),
        threshold=0,
    )
    band_series = SignalBandSeries(
        key="envelope",
        label_key="signals.envelope",
        semantic_id="test.envelope",
        semantic_description="Test band envelope.",
        unit=SignalUnit.INDEX,
        axis=SignalAxisSpec(
            key="annotation",
            role=SignalAxisRole.INDEPENDENT,
        ),
        points=[
            SignalBandPoint(
                date=START,
                lower=0,
                middle=1,
                upper=2,
            )
        ],
    )
    result = SignalAnnotationService().compute(
        [missing, band],
        price_points([1]),
        {"band": [band_series]},
        context(end=START),
    )

    warnings = result.warnings_by_target["target"]
    assert len(warnings) == 2
    assert all(warning.code == SignalWarningCode.ANNOTATION_UNAVAILABLE for warning in warnings)
