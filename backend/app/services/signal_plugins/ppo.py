"""PPO signal plugin using pandas-ta with an explicit TA-Lib PPO path."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAxisRole,
    SignalAxisSpec,
    SignalBarSeries,
    SignalCategory,
    SignalColorRole,
    SignalComputation,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalLinePattern,
    SignalLineSeries,
    SignalOutputSpec,
    SignalOutputStyle,
    SignalPriceField,
    SignalPricePoint,
    SignalReferenceLevel,
    SignalSeriesKind,
    SignalUnit,
    SignalValuePoint,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class PpoSignalParams(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    fast_period: int = Field(
        12,
        alias="fastPeriod",
        ge=2,
        le=200,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.fastPeriod",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.fastPeriod",
        },
    )
    slow_period: int = Field(
        26,
        alias="slowPeriod",
        ge=2,
        le=500,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.slowPeriod",
            "x-control-order": 2,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.slowPeriod",
        },
    )
    signal_period: int = Field(
        9,
        alias="signalPeriod",
        ge=2,
        le=100,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.signalPeriod",
            "x-control-order": 3,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.signalPeriod",
        },
    )

    @model_validator(mode="after")
    def validate_periods(self) -> PpoSignalParams:
        if self.fast_period >= self.slow_period:
            raise ValueError("fastPeriod must be lower than slowPeriod")
        return self


_PPO_AXIS = SignalAxisSpec(
    key="ppo",
    role=SignalAxisRole.INDEPENDENT,
)
_ZERO_LEVEL = SignalReferenceLevel(
    key="zero",
    label_key="signals.reference.zero",
    semantic="zero",
    value=0,
)


@register_plugin(SignalPluginRegistry)
class PpoSignalPlugin(SignalPlugin):
    signal_code = "PPO"
    implementation_version = "1.0.0"
    category = SignalCategory.MOMENTUM
    display_name_key = "signals.ppo.name"
    description_key = "signals.ppo.description"
    semantic_id = "percentage_price_oscillator"
    semantic_description = "Compares fast and slow exponential trends as a percentage."
    icon = "📡"
    docs_path = "financial-theory/technical-analysis/indicators/ppo/"
    params_model = PpoSignalParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="ppo",
            label_key="signals.ppo.line",
            description_key="signals.ppo.lineDescription",
            semantic_id="percentage_price_oscillator.line",
            semantic_description="Percentage difference between fast and slow exponential moving averages.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            axis=_PPO_AXIS,
            style=SignalOutputStyle(
                color_role=SignalColorRole.PRIMARY,
                line_pattern=SignalLinePattern.SOLID,
                width_delta=1,
            ),
            supports_reference_levels=True,
            default_reference_levels=[_ZERO_LEVEL],
        ),
        SignalOutputSpec(
            key="signal",
            label_key="signals.ppo.signal",
            description_key="signals.ppo.signalDescription",
            semantic_id="percentage_price_oscillator.signal",
            semantic_description="Smoothed average of the PPO line.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            axis=_PPO_AXIS,
            style=SignalOutputStyle(
                color_role=SignalColorRole.SECONDARY,
                line_pattern=SignalLinePattern.DASHED,
            ),
        ),
        SignalOutputSpec(
            key="histogram",
            label_key="signals.ppo.histogram",
            description_key="signals.ppo.histogramDescription",
            semantic_id="percentage_price_oscillator.histogram",
            semantic_description="Difference between the PPO line and its signal line.",
            kind=SignalSeriesKind.BAR,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            axis=_PPO_AXIS,
            style=SignalOutputStyle(color_role=SignalColorRole.NEUTRAL),
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)
    annotation_capabilities = (
        "line_crossover",
        "threshold_crossing",
    )

    @classmethod
    def warmup_requirement(
        cls,
        params: PpoSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        minimum_points = params.slow_period + params.signal_period - 1
        total_points = max(
            minimum_points,
            8 * max(params.slow_period, params.signal_period),
        )
        return SignalWarmupRequirement(
            minimum_points=minimum_points,
            stabilization_points=total_points - minimum_points,
            total_points=total_points,
            normalized_tolerance=1e-6,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: PpoSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.ppo(
            close,
            fast=params.fast_period,
            slow=params.slow_period,
            signal=params.signal_period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no PPO output")
        ppo_values = self._column(output, "PPO_")
        histogram_values = self._column(output, "PPOh_")
        signal_values = self._column(output, "PPOs_")
        raw_series = (
            (SignalLineSeries, ppo_values),
            (SignalLineSeries, signal_values),
            (SignalBarSeries, histogram_values),
        )
        series = []
        for index, (spec, (series_type, values)) in enumerate(
            zip(
                self.output_specs,
                raw_series,
                strict=True,
            )
        ):
            series.append(
                series_type(
                    key=spec.key,
                    label_key=spec.label_key,
                    description_key=spec.description_key,
                    semantic_id=spec.semantic_id,
                    semantic_description=spec.semantic_description,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    view_transform=spec.view_transform,
                    style=spec.style.model_copy(deep=True),
                    reference_levels=([_ZERO_LEVEL.model_copy(deep=True)] if index == 0 else []),
                    points=[
                        SignalValuePoint(
                            date=point.date,
                            value=(None if pd.isna(raw_value) else float(raw_value)),
                        )
                        for point, raw_value in zip(
                            price_points,
                            values,
                            strict=True,
                        )
                    ],
                )
            )
        return SignalComputation(series=series)

    @staticmethod
    def _column(output: pd.DataFrame, prefix: str) -> pd.Series:
        matches = [column for column in output.columns if column.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"Expected one PPO column with prefix '{prefix}', got {matches}")
        return output[matches[0]]


__all__ = ["PpoSignalParams", "PpoSignalPlugin"]
