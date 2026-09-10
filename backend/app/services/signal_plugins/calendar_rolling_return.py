"""Calendar-day rolling return over an already-resolved daily asset series."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAvailabilityReason,
    SignalAxisRole,
    SignalAxisSpec,
    SignalCalendarReturnPointStatus,
    SignalCalendarReturnProvenance,
    SignalCalendarReturnValuePoint,
    SignalCategory,
    SignalComputation,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalLineSeries,
    SignalOutputSpec,
    SignalPriceField,
    SignalPricePoint,
    SignalReferenceLevel,
    SignalSeriesKind,
    SignalUnit,
    SignalWarmupRequirement,
    SignalWarning,
    SignalWarningCode,
)
from backend.app.services.provider_registry import SignalPluginRegistry, register_plugin
from backend.app.services.signal_plugins.base import SignalPlugin, SignalUnavailableError

CalendarWindowDays = Literal[7, 30, 90, 365]


class CalendarRollingReturnParams(BaseModel):
    """Calendar rolling-return parameters."""

    model_config = ConfigDict(extra="forbid")

    window_days: CalendarWindowDays = Field(
        default=30,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.window",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "signals.tooltips.riskWindow",
        },
    )


def _resolved_provenance(
    point: SignalPricePoint,
) -> tuple[date_type, int, date_type | None, int | None]:
    info = point.backward_fill_info
    return (
        info.actual_rate_date if info is not None else point.date,
        info.days_back if info is not None else 0,
        getattr(info, "fx_rate_date", None),
        getattr(info, "fx_days_back", None),
    )


def _point_provenance(
    current: SignalPricePoint,
    reference_target_date: date_type,
    status: SignalCalendarReturnPointStatus,
    reference: SignalPricePoint | None,
) -> SignalCalendarReturnProvenance:
    current_price_date, current_price_days_back, current_fx_date, current_fx_days_back = _resolved_provenance(current)
    if reference is None:
        reference_price_date = None
        reference_price_days_back = None
        reference_fx_date = None
        reference_fx_days_back = None
    else:
        reference_price_date, reference_price_days_back, reference_fx_date, reference_fx_days_back = _resolved_provenance(reference)
    return SignalCalendarReturnProvenance(
        status=status,
        reference_target_date=reference_target_date,
        current_price_date=current_price_date,
        current_price_days_back=current_price_days_back,
        reference_price_date=reference_price_date,
        reference_price_days_back=reference_price_days_back,
        current_fx_date=current_fx_date,
        current_fx_days_back=current_fx_days_back,
        reference_fx_date=reference_fx_date,
        reference_fx_days_back=reference_fx_days_back,
    )


@register_plugin(SignalPluginRegistry)
class CalendarRollingReturnPlugin(SignalPlugin):
    """Compare each resolved daily price with the resolved price N calendar days earlier."""

    signal_code = "ASSET_CALENDAR_ROLLING_RETURN"
    implementation_version = "1.0.0"
    display_name_key = "signals.riskRollingReturn.name"
    description_key = "signals.riskRollingReturn.description"
    semantic_id = "calendar_rolling_return"
    semantic_description = "Measures price-only return over an exact calendar-day window."
    icon = "↗️"
    category = SignalCategory.RISK
    params_model = CalendarRollingReturnParams
    catalog_visible = False
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
    )
    output_specs = (
        SignalOutputSpec(
            key="calendar_return",
            label_key="signals.riskRollingReturn.output",
            description_key="signals.riskRollingReturn.outputDescription",
            semantic_id="calendar_rolling_return.value",
            semantic_description="Price-only return from the resolved value exactly N calendar days earlier.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            axis=SignalAxisSpec(
                key="calendar_return",
                role=SignalAxisRole.INDEPENDENT,
            ),
            supports_reference_levels=True,
            default_reference_levels=[
                SignalReferenceLevel(
                    key="zero",
                    value=0.0,
                    label_key="signals.reference.zero",
                    semantic="No price-only gain or loss.",
                )
            ],
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: CalendarRollingReturnParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        del context
        return SignalWarmupRequirement(
            minimum_points=2,
            stabilization_points=params.window_days - 2,
            total_points=params.window_days,
            normalized_tolerance=1e-6,
        )

    @classmethod
    def validate_input(
        cls,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: CalendarRollingReturnParams,
        context: SignalExecutionContext,
    ) -> None:
        del event_points
        available_dates = {point.date for point in price_points}
        requested_end = context.requested_range.end or context.requested_range.start
        visible_dates = (point.date for point in price_points if context.requested_range.start <= point.date <= requested_end)
        if not any(current_date - timedelta(days=params.window_days) in available_dates for current_date in visible_dates):
            raise SignalUnavailableError(
                "Calendar return has no visible point with a resolved reference date",
                reason_code=SignalAvailabilityReason.INSUFFICIENT_HISTORY,
                details={"window_days": params.window_days},
            )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: CalendarRollingReturnParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points
        points_by_date = {point.date: point for point in price_points}
        output_points: list[SignalCalendarReturnValuePoint] = []
        unavailable_counts: Counter[str] = Counter()
        one = Decimal("1")
        hundred = Decimal("100")
        requested_end = context.requested_range.end or context.requested_range.start

        for current in price_points:
            reference_target_date = current.date - timedelta(days=params.window_days)
            reference = points_by_date.get(reference_target_date)
            if current.close <= 0:
                status = SignalCalendarReturnPointStatus.INVALID_CURRENT_PRICE
                value = None
            elif reference is None:
                status = SignalCalendarReturnPointStatus.MISSING_REFERENCE
                value = None
            elif reference.close <= 0:
                status = SignalCalendarReturnPointStatus.INVALID_REFERENCE_PRICE
                value = None
            else:
                status = SignalCalendarReturnPointStatus.AVAILABLE
                value = float((current.close / reference.close - one) * hundred)
            if value is None and context.requested_range.start <= current.date <= requested_end:
                unavailable_counts[status.value] += 1
            output_points.append(
                SignalCalendarReturnValuePoint(
                    date=current.date,
                    value=value,
                    provenance=_point_provenance(
                        current,
                        reference_target_date,
                        status,
                        reference,
                    ),
                )
            )

        spec = self.output_specs[0]
        warnings = (
            [
                SignalWarning(
                    code=SignalWarningCode.UNDEFINED_METRIC_WINDOW,
                    message="One or more calendar-return points are unavailable",
                    details={
                        "unavailable_points": sum(unavailable_counts.values()),
                        "reasons": dict(sorted(unavailable_counts.items())),
                    },
                )
            ]
            if unavailable_counts
            else []
        )
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    description_key=spec.description_key,
                    semantic_id=spec.semantic_id,
                    semantic_description=spec.semantic_description,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    view_transform=spec.view_transform,
                    style=spec.style.model_copy(deep=True),
                    points=output_points,
                    reference_levels=[level.model_copy(deep=True) for level in spec.default_reference_levels],
                    value_regions=[region.model_copy(deep=True) for region in spec.default_value_regions],
                )
            ],
            warnings=warnings,
        )


__all__ = [
    "CalendarRollingReturnParams",
    "CalendarRollingReturnPlugin",
]
