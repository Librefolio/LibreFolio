"""RSI signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAxisRole,
    SignalAxisSpec,
    SignalCategory,
    SignalComputation,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalLinePattern,
    SignalLineSeries,
    SignalOutputSpec,
    SignalPriceField,
    SignalPricePoint,
    SignalReferenceLevel,
    SignalRegionLineStyle,
    SignalSeriesKind,
    SignalUnit,
    SignalValuePoint,
    SignalValueRegion,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class RsiSignalParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: int = Field(
        14,
        ge=2,
        le=200,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.period",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.period",
        },
    )
    overbought: FiniteFloat = Field(
        70,
        ge=50,
        le=100,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.overbought",
            "x-control-order": 2,
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.overbought",
        },
    )
    oversold: FiniteFloat = Field(
        30,
        ge=0,
        le=50,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.oversold",
            "x-control-order": 3,
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.oversold",
        },
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> RsiSignalParams:
        if self.oversold >= self.overbought:
            raise ValueError("oversold must be lower than overbought")
        return self


_RSI_AXIS = SignalAxisSpec(
    key="rsi",
    role=SignalAxisRole.INDEPENDENT,
    minimum=0,
    maximum=100,
)
_EXTREME_LINE_STYLE = SignalRegionLineStyle(
    pattern=SignalLinePattern.SOLID,
    width_delta=1,
)
_NEUTRAL_LINE_STYLE = SignalRegionLineStyle(pattern=SignalLinePattern.DASHED)
_DEFAULT_LEVELS = [
    SignalReferenceLevel(
        key="oversold",
        label_key="signals.rsi.oversold",
        semantic="oversold",
        value=30,
    ),
    SignalReferenceLevel(
        key="overbought",
        label_key="signals.rsi.overbought",
        semantic="overbought",
        value=70,
    ),
]
_DEFAULT_REGIONS = [
    SignalValueRegion(
        key="oversold",
        label_key="signals.rsi.oversoldRegion",
        description_key="signals.regions.oversoldDescription",
        semantic="oversold",
        upper=30,
        include_upper=False,
        line_style=_EXTREME_LINE_STYLE,
    ),
    SignalValueRegion(
        key="neutral",
        label_key="signals.rsi.neutralRegion",
        description_key="signals.regions.neutralDescription",
        semantic="neutral",
        lower=30,
        upper=70,
        include_lower=True,
        include_upper=True,
        line_style=_NEUTRAL_LINE_STYLE,
    ),
    SignalValueRegion(
        key="overbought",
        label_key="signals.rsi.overboughtRegion",
        description_key="signals.regions.overboughtDescription",
        semantic="overbought",
        lower=70,
        include_lower=False,
        line_style=_EXTREME_LINE_STYLE,
    ),
]


@register_plugin(SignalPluginRegistry)
class RsiSignalPlugin(SignalPlugin):
    signal_code = "RSI"
    implementation_version = "1.0.0"
    category = SignalCategory.MOMENTUM
    display_name_key = "signals.rsi.name"
    description_key = "signals.rsi.description"
    semantic_id = "relative_strength_index"
    semantic_description = "Measures recent gain and loss magnitude on a bounded scale."
    icon = "💪"
    docs_path = "financial-theory/technical-analysis/indicators/rsi/"
    params_model = RsiSignalParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="rsi",
            label_key="signals.rsi.output",
            semantic_id="relative_strength_index.value",
            semantic_description="Bounded ratio of smoothed gains to total directional movement.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.INDEX,
            axis=_RSI_AXIS,
            supports_reference_levels=True,
            supports_value_regions=True,
            default_reference_levels=_DEFAULT_LEVELS,
            default_value_regions=_DEFAULT_REGIONS,
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)
    annotation_capabilities = ("threshold_crossing",)

    @classmethod
    def warmup_requirement(
        cls,
        params: RsiSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        minimum_points = params.period + 1
        total_points = 16 * params.period
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
        params: RsiSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.rsi(
            close,
            length=params.period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no RSI output")
        spec = self.output_specs[0]
        levels = [
            SignalReferenceLevel(
                key="oversold",
                label_key="signals.rsi.oversold",
                semantic="oversold",
                value=params.oversold,
            ),
            SignalReferenceLevel(
                key="overbought",
                label_key="signals.rsi.overbought",
                semantic="overbought",
                value=params.overbought,
            ),
        ]
        regions = [
            SignalValueRegion(
                key="oversold",
                label_key="signals.rsi.oversoldRegion",
                description_key="signals.regions.oversoldDescription",
                semantic="oversold",
                upper=params.oversold,
                include_upper=False,
                line_style=_EXTREME_LINE_STYLE.model_copy(deep=True),
            ),
            SignalValueRegion(
                key="neutral",
                label_key="signals.rsi.neutralRegion",
                description_key="signals.regions.neutralDescription",
                semantic="neutral",
                lower=params.oversold,
                upper=params.overbought,
                include_lower=True,
                include_upper=True,
                line_style=_NEUTRAL_LINE_STYLE.model_copy(deep=True),
            ),
            SignalValueRegion(
                key="overbought",
                label_key="signals.rsi.overboughtRegion",
                description_key="signals.regions.overboughtDescription",
                semantic="overbought",
                lower=params.overbought,
                include_lower=False,
                line_style=_EXTREME_LINE_STYLE.model_copy(deep=True),
            ),
        ]
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
                    reference_levels=levels,
                    value_regions=regions,
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


__all__ = ["RsiSignalParams", "RsiSignalPlugin"]
