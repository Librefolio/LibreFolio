"""Shared immutable builders and detail overlays for AI Export profiles."""

from __future__ import annotations

from typing import Any, Mapping

from backend.app.schemas.ai_export import AiExportDetailLevel
from backend.app.services.ai_export.models import (
    AnnotationDirection,
    AnnotationRequestKind,
    AnnotationRequestSpec,
    AnnotationSourceKind,
    AnnotationSourceSpec,
    BandComponent,
    CardinalitySpec,
    CompactSelectionSpec,
    DetailOverlay,
    EventLimitMode,
    EventLimitSpec,
    PrecisionSpec,
    RoundingStage,
    SamplingSpec,
    SignalEligibility,
    SignalInstanceSpec,
    SignalOutputMode,
    TechnicalBundleSpec,
    TechnicalDepth,
    TechnicalDetailSpec,
)

COMMON_PRECISION = PrecisionSpec(
    policy_id="ai_export_v1",
    rounding_stage=RoundingStage.AFTER_SAMPLING,
)

COMPACT_OVERLAY = DetailOverlay(
    detail_level=AiExportDetailLevel.COMPACT,
    cardinality=CardinalitySpec(
        complete_aggregates=True,
        all_positions=False,
        all_entities=False,
        all_contributions=False,
        requires_compact_selection=True,
    ),
    sampling=SamplingSpec(
        include_latest=True,
        include_aggregates=True,
        include_series=False,
        recent_daily_points=0,
        preceding_weekly_points=0,
        weekly_across_technical_window=False,
    ),
    precision=COMMON_PRECISION,
    event_limits=EventLimitSpec(
        mode=EventLimitMode.FIXED,
        max_events=10,
        deduplicate=True,
    ),
)

STANDARD_OVERLAY = DetailOverlay(
    detail_level=AiExportDetailLevel.STANDARD,
    cardinality=CardinalitySpec(
        complete_aggregates=True,
        all_positions=True,
        all_entities=True,
        all_contributions=True,
        requires_compact_selection=False,
    ),
    sampling=SamplingSpec(
        include_latest=True,
        include_aggregates=True,
        include_series=True,
        recent_daily_points=7,
        preceding_weekly_points=8,
        weekly_across_technical_window=False,
    ),
    precision=COMMON_PRECISION,
    event_limits=EventLimitSpec(
        mode=EventLimitMode.FIXED,
        max_events=40,
        deduplicate=True,
    ),
)

FULL_OVERLAY = DetailOverlay(
    detail_level=AiExportDetailLevel.FULL,
    cardinality=CardinalitySpec(
        complete_aggregates=True,
        all_positions=True,
        all_entities=True,
        all_contributions=True,
        requires_compact_selection=False,
    ),
    sampling=SamplingSpec(
        include_latest=True,
        include_aggregates=True,
        include_series=True,
        recent_daily_points=7,
        preceding_weekly_points=None,
        weekly_across_technical_window=True,
    ),
    precision=COMMON_PRECISION,
    event_limits=EventLimitSpec(
        mode=EventLimitMode.FIXED,
        max_events=120,
        deduplicate=True,
    ),
)

DETAIL_OVERLAYS = (
    COMPACT_OVERLAY,
    STANDARD_OVERLAY,
    FULL_OVERLAY,
)


def signal(
    instance_id: str,
    signal_code: str,
    params: Mapping[str, Any],
    requested_components: tuple[str, ...],
    mode: SignalOutputMode,
    *,
    eligibility: SignalEligibility = SignalEligibility.ALWAYS,
) -> SignalInstanceSpec:
    return SignalInstanceSpec(
        instance_id=instance_id,
        signal_code=signal_code,
        params=params,
        requested_components=requested_components,
        mode=mode,
        eligibility=eligibility,
    )


def price_source(price_field: str = "close") -> AnnotationSourceSpec:
    return AnnotationSourceSpec(
        kind=AnnotationSourceKind.PRICE,
        price_field=price_field,
    )


def signal_source(
    instance_id: str,
    component: str,
    *,
    band_component: BandComponent | None = None,
) -> AnnotationSourceSpec:
    return AnnotationSourceSpec(
        kind=AnnotationSourceKind.SIGNAL_COMPONENT,
        signal_instance_id=instance_id,
        component=component,
        band_component=band_component,
    )


def constant_source(value: int | float) -> AnnotationSourceSpec:
    return AnnotationSourceSpec(
        kind=AnnotationSourceKind.CONSTANT,
        constant=value,
    )


def line_crossover(
    key: str,
    attach_to_instance_id: str,
    left: AnnotationSourceSpec,
    right: AnnotationSourceSpec,
) -> AnnotationRequestSpec:
    return AnnotationRequestSpec(
        key=key,
        kind=AnnotationRequestKind.LINE_CROSSOVER,
        attach_to_instance_id=attach_to_instance_id,
        left=left,
        right=right,
    )


def threshold_crossing(
    key: str,
    attach_to_instance_id: str,
    source: AnnotationSourceSpec,
    threshold: int | float,
    *,
    direction: AnnotationDirection = AnnotationDirection.BOTH,
) -> AnnotationRequestSpec:
    return AnnotationRequestSpec(
        key=key,
        kind=AnnotationRequestKind.THRESHOLD_CROSSING,
        attach_to_instance_id=attach_to_instance_id,
        source=source,
        threshold=threshold,
        direction=direction,
    )


def compact_selection(
    rule: str,
    entity_limit: int,
    **parameters: Any,
) -> CompactSelectionSpec:
    return CompactSelectionSpec(
        rule=rule,
        entity_limit=entity_limit,
        parameters=parameters,
    )


def technical_detail(
    detail_level: AiExportDetailLevel,
    depth: TechnicalDepth,
    bundle: TechnicalBundleSpec | None,
    *,
    event_limit_override: int | None = None,
) -> TechnicalDetailSpec:
    return TechnicalDetailSpec(
        detail_level=detail_level,
        depth=depth,
        bundle=bundle,
        event_limit_override=event_limit_override,
    )


def technical_matrix(
    compact: TechnicalDetailSpec,
    standard: TechnicalDetailSpec,
    full: TechnicalDetailSpec,
) -> Mapping[AiExportDetailLevel, TechnicalDetailSpec]:
    return {
        AiExportDetailLevel.COMPACT: compact,
        AiExportDetailLevel.STANDARD: standard,
        AiExportDetailLevel.FULL: full,
    }


def no_technical(detail_level: AiExportDetailLevel) -> TechnicalDetailSpec:
    return technical_detail(
        detail_level,
        TechnicalDepth.NONE,
        None,
    )
