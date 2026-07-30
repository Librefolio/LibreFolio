"""MFI signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

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
    SignalAggregationProfile,
    SignalAxisRole,
    SignalAxisSpec,
    SignalCategory,
    SignalComputation,
    SignalDataPolicy,
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


class MfiSignalParams(BaseModel):
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
        80,
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
        20,
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
    def validate_thresholds(self) -> MfiSignalParams:
        if self.oversold >= self.overbought:
            raise ValueError("oversold must be lower than overbought")
        return self


_MFI_AXIS = SignalAxisSpec(
    key="mfi",
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
        label_key="signals.mfi.oversold",
        semantic="oversold",
        value=20,
    ),
    SignalReferenceLevel(
        key="overbought",
        label_key="signals.mfi.overbought",
        semantic="overbought",
        value=80,
    ),
]
_DEFAULT_REGIONS = [
    SignalValueRegion(
        key="oversold",
        label_key="signals.mfi.oversoldRegion",
        description_key="signals.regions.oversoldDescription",
        semantic="oversold",
        upper=20,
        include_upper=False,
        line_style=_EXTREME_LINE_STYLE,
    ),
    SignalValueRegion(
        key="neutral",
        label_key="signals.mfi.neutralRegion",
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
        label_key="signals.mfi.overboughtRegion",
        description_key="signals.regions.overboughtDescription",
        semantic="overbought",
        lower=80,
        include_lower=False,
        line_style=_EXTREME_LINE_STYLE,
    ),
]


@register_plugin(SignalPluginRegistry)
class MfiSignalPlugin(SignalPlugin):
    signal_code = "MFI"
    implementation_version = "1.0.0"
    category = SignalCategory.VOLUME
    display_name_key = "signals.mfi.name"
    description_key = "signals.mfi.description"
    semantic_id = "money_flow_index"
    semantic_description = "Measures price-and-volume flow over a rolling window."
    icon = "💸"
    docs_path = "financial-theory/technical-analysis/indicators/mfi/"
    params_model = MfiSignalParams
    input_requirements = SignalInputRequirements(
        price_fields=[
            SignalPriceField.HIGH,
            SignalPriceField.LOW,
            SignalPriceField.CLOSE,
            SignalPriceField.VOLUME,
        ],
        data_policy=SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS,
        minimum_coverage=0.5,
        requires_meaningful_volume=True,
    )
    output_specs = (
        SignalOutputSpec(
            key="mfi",
            label_key="signals.mfi.output",
            semantic_id="money_flow_index.value",
            semantic_description="Bounded price-and-volume flow index.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.INDEX,
            axis=_MFI_AXIS,
            supports_reference_levels=True,
            supports_value_regions=True,
            default_reference_levels=_DEFAULT_LEVELS,
            default_value_regions=_DEFAULT_REGIONS,
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)
    annotation_capabilities = ("threshold_crossing",)

    @classmethod
    def warmup_requirement(
        cls,
        params: MfiSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        total_points = params.period + 1
        return SignalWarmupRequirement(
            minimum_points=total_points,
            stabilization_points=0,
            total_points=total_points,
            normalized_tolerance=1e-6,
        )

    @classmethod
    def validate_input(
        cls,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: MfiSignalParams,
        context: SignalExecutionContext,
    ) -> None:
        cls.validate_meaningful_volume_input(
            price_points,
            minimum_coverage=cls.input_requirements.minimum_coverage,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: MfiSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        index = [point.date for point in price_points]
        output = ta.mfi(
            pd.Series(
                [float(point.high) for point in price_points],
                index=index,
                dtype=float,
            ),
            pd.Series(
                [float(point.low) for point in price_points],
                index=index,
                dtype=float,
            ),
            pd.Series(
                [float(point.close) for point in price_points],
                index=index,
                dtype=float,
            ),
            pd.Series(
                [float(point.volume) for point in price_points],
                index=index,
                dtype=float,
            ),
            length=params.period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no MFI output")
        levels = [
            SignalReferenceLevel(
                key="oversold",
                label_key="signals.mfi.oversold",
                semantic="oversold",
                value=params.oversold,
            ),
            SignalReferenceLevel(
                key="overbought",
                label_key="signals.mfi.overbought",
                semantic="overbought",
                value=params.overbought,
            ),
        ]
        regions = [
            SignalValueRegion(
                key="oversold",
                label_key="signals.mfi.oversoldRegion",
                description_key="signals.regions.oversoldDescription",
                semantic="oversold",
                upper=params.oversold,
                include_upper=False,
                line_style=_EXTREME_LINE_STYLE.model_copy(deep=True),
            ),
            SignalValueRegion(
                key="neutral",
                label_key="signals.mfi.neutralRegion",
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
                label_key="signals.mfi.overboughtRegion",
                description_key="signals.regions.overboughtDescription",
                semantic="overbought",
                lower=params.overbought,
                include_lower=False,
                line_style=_EXTREME_LINE_STYLE.model_copy(deep=True),
            ),
        ]
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


__all__ = ["MfiSignalParams", "MfiSignalPlugin"]
