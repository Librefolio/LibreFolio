"""Stochastic RSI plugin using the explicit pandas-ta TA-Lib path."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    model_validator,
)

from backend.app.schemas.signals import (
    SignalAxisRole,
    SignalAxisSpec,
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


class StochRsiSignalParams(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    period: int = Field(
        14,
        ge=2,
        le=200,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.period",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "signals.tooltips.stochRsiPeriod",
            "x-affects-outputs": ["k", "d"],
        },
    )
    d_period: int = Field(
        3,
        alias="dPeriod",
        ge=2,
        le=100,
        json_schema_extra={
            "x-i18n-key": "signals.params.dPeriod",
            "x-control-order": 2,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "signals.tooltips.dPeriod",
            "x-affects-outputs": ["d"],
        },
    )
    overbought: FiniteFloat = Field(
        80,
        ge=50,
        le=100,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.overbought",
            "x-control-order": 3,
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.overbought",
            "x-affects-outputs": ["k"],
        },
    )
    oversold: FiniteFloat = Field(
        20,
        ge=0,
        le=50,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.oversold",
            "x-control-order": 4,
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.oversold",
            "x-affects-outputs": ["k"],
        },
    )

    @model_validator(mode="after")
    def validate_thresholds(self) -> StochRsiSignalParams:
        if self.oversold >= self.overbought:
            raise ValueError("oversold must be lower than overbought")
        return self


_STOCH_RSI_AXIS = SignalAxisSpec(
    key="stoch-rsi",
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
        label_key="signals.stochRsi.oversold",
        semantic="oversold",
        value=20,
    ),
    SignalReferenceLevel(
        key="overbought",
        label_key="signals.stochRsi.overbought",
        semantic="overbought",
        value=80,
    ),
]
_DEFAULT_REGIONS = [
    SignalValueRegion(
        key="oversold",
        label_key="signals.stochRsi.oversoldRegion",
        description_key="signals.regions.oversoldDescription",
        semantic="oversold",
        upper=20,
        include_upper=False,
        line_style=_EXTREME_LINE_STYLE,
    ),
    SignalValueRegion(
        key="neutral",
        label_key="signals.stochRsi.neutralRegion",
        description_key="signals.regions.neutralDescription",
        semantic="neutral",
        lower=20,
        upper=80,
        include_lower=True,
        include_upper=True,
        line_style=_NEUTRAL_LINE_STYLE,
    ),
    SignalValueRegion(
        key="overbought",
        label_key="signals.stochRsi.overboughtRegion",
        description_key="signals.regions.overboughtDescription",
        semantic="overbought",
        lower=80,
        include_lower=False,
        line_style=_EXTREME_LINE_STYLE,
    ),
]


@register_plugin(SignalPluginRegistry)
class StochRsiSignalPlugin(SignalPlugin):
    signal_code = "STOCH_RSI"
    implementation_version = "1.0.0"
    category = SignalCategory.MOMENTUM
    display_name_key = "signals.stochRsi.name"
    description_key = "signals.stochRsi.description"
    icon = "🎛️"
    docs_path = "financial-theory/technical-analysis/indicators/stochastic-rsi/"
    params_model = StochRsiSignalParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="k",
            label_key="signals.stochRsi.k",
            description_key="signals.stochRsi.kDescription",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_STOCH_RSI_AXIS,
            style=SignalOutputStyle(
                color_role=SignalColorRole.PRIMARY,
                line_pattern=SignalLinePattern.SOLID,
                width_delta=1,
            ),
            supports_reference_levels=True,
            supports_value_regions=True,
            default_reference_levels=_DEFAULT_LEVELS,
            default_value_regions=_DEFAULT_REGIONS,
        ),
        SignalOutputSpec(
            key="d",
            label_key="signals.stochRsi.d",
            description_key="signals.stochRsi.dDescription",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_STOCH_RSI_AXIS,
            style=SignalOutputStyle(
                color_role=SignalColorRole.SECONDARY,
                line_pattern=SignalLinePattern.DASHED,
            ),
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
        params: StochRsiSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        minimum_points = 2 * params.period + params.d_period - 1
        total_points = max(
            minimum_points,
            16 * max(params.period, params.d_period),
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
        params: StochRsiSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.stochrsi(
            close,
            length=params.period,
            d=params.d_period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no StochRSI output")
        k_values = self._column(output, "STOCHRSIk_")
        d_values = self._column(output, "STOCHRSId_")
        levels = [
            SignalReferenceLevel(
                key="oversold",
                label_key="signals.stochRsi.oversold",
                semantic="oversold",
                value=params.oversold,
            ),
            SignalReferenceLevel(
                key="overbought",
                label_key="signals.stochRsi.overbought",
                semantic="overbought",
                value=params.overbought,
            ),
        ]
        regions = [
            SignalValueRegion(
                key="oversold",
                label_key="signals.stochRsi.oversoldRegion",
                description_key="signals.regions.oversoldDescription",
                semantic="oversold",
                upper=params.oversold,
                include_upper=False,
                line_style=_EXTREME_LINE_STYLE.model_copy(deep=True),
            ),
            SignalValueRegion(
                key="neutral",
                label_key="signals.stochRsi.neutralRegion",
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
                label_key="signals.stochRsi.overboughtRegion",
                description_key="signals.regions.overboughtDescription",
                semantic="overbought",
                lower=params.overbought,
                include_lower=False,
                line_style=_EXTREME_LINE_STYLE.model_copy(deep=True),
            ),
        ]
        series = []
        for index, (spec, values) in enumerate(
            zip(
                self.output_specs,
                (k_values, d_values),
                strict=True,
            )
        ):
            series.append(
                SignalLineSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    description_key=spec.description_key,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    view_transform=spec.view_transform,
                    style=spec.style.model_copy(deep=True),
                    reference_levels=([item.model_copy(deep=True) for item in levels] if index == 0 else []),
                    value_regions=([item.model_copy(deep=True) for item in regions] if index == 0 else []),
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
            raise ValueError(f"Expected one StochRSI column with prefix '{prefix}', got {matches}")
        return output[matches[0]]


__all__ = ["StochRsiSignalParams", "StochRsiSignalPlugin"]
