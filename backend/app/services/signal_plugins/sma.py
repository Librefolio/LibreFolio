"""SMA signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAiExportTemporalRule,
    SignalAxisRole,
    SignalAxisSpec,
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
    SignalSeriesKind,
    SignalTemporalClass,
    SignalUnit,
    SignalValuePoint,
    SignalViewTransform,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class SmaSignalParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: int = Field(
        20,
        ge=2,
        le=500,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.period",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.period",
        },
    )


@register_plugin(SignalPluginRegistry)
class SmaSignalPlugin(SignalPlugin):
    signal_code = "SMA"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.sma.name"
    description_key = "signals.sma.description"
    semantic_id = "simple_moving_average"
    semantic_description = "Averages closing prices over a rolling window."
    icon = "📏"
    docs_path = "financial-theory/technical-analysis/indicators/sma/"
    params_model = SmaSignalParams
    ai_export_temporal_rules = (
        SignalAiExportTemporalRule(
            temporal_class=SignalTemporalClass.SLOW,
            parameter_match={"period": 50},
        ),
        SignalAiExportTemporalRule(
            temporal_class=SignalTemporalClass.VERY_SLOW,
            parameter_match={"period": 200},
        ),
    )
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="sma",
            label_key="signals.sma.output",
            semantic_id="simple_moving_average.value",
            semantic_description="Arithmetic mean of closing prices in the lookback window.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PRICE,
            axis=SignalAxisSpec(
                key="price",
                role=SignalAxisRole.PRICE,
            ),
            view_transform=SignalViewTransform.BASE_PERCENTAGE,
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)
    annotation_capabilities = ("line_crossover",)

    @classmethod
    def warmup_requirement(
        cls,
        params: SmaSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        return SignalWarmupRequirement(
            minimum_points=params.period,
            stabilization_points=0,
            total_points=params.period,
            normalized_tolerance=1e-6,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: SmaSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.sma(
            close,
            length=params.period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no SMA output")
        spec = self.output_specs[0]
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    semantic_id=spec.semantic_id,
                    semantic_description=spec.semantic_description,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    view_transform=spec.view_transform,
                    points=[
                        SignalValuePoint(
                            date=point.date,
                            value=(None if pd.isna(raw_value) else float(raw_value)),
                        )
                        for point, raw_value in zip(
                            price_points,
                            output,
                            strict=True,
                        )
                    ],
                )
            ]
        )


__all__ = ["SmaSignalParams", "SmaSignalPlugin"]
