"""EMA signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from backend.app.schemas.signals import (
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


class EmaSignalParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: int = Field(
        14,
        ge=2,
        le=500,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.period",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.emaPeriod",
        },
    )
    offset: FiniteFloat = Field(
        0.0,
        ge=-100,
        le=100,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.offset",
            "x-control-order": 2,
            "x-suffix": "%",
            "x-step": 0.5,
            "x-tooltip-key": "chartSettings.tooltips.offset",
        },
    )


@register_plugin(SignalPluginRegistry)
class EmaSignalPlugin(SignalPlugin):
    signal_code = "EMA"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.ema.name"
    description_key = "signals.ema.description"
    semantic_id = "exponential_moving_average"
    semantic_description = "Smooths prices with greater weight on recent observations."
    icon = "📉"
    docs_path = "financial-theory/technical-analysis/indicators/ema/"
    params_model = EmaSignalParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="ema",
            label_key="signals.ema.output",
            semantic_id="exponential_moving_average.value",
            semantic_description="Exponentially weighted closing-price average with the configured offset.",
            kind=SignalSeriesKind.LINE,
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
        params: EmaSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        total_points = 6 * params.period
        return SignalWarmupRequirement(
            minimum_points=params.period,
            stabilization_points=total_points - params.period,
            total_points=total_points,
            normalized_tolerance=1e-6,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: EmaSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.ema(
            close,
            length=params.period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no EMA output")
        factor = 1.0 + params.offset / 100.0
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
                            value=(None if pd.isna(raw_value) else float(raw_value) * factor),
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


__all__ = ["EmaSignalParams", "EmaSignalPlugin"]
