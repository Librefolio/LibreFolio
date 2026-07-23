"""CCI signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAxisRole,
    SignalAxisSpec,
    SignalCategory,
    SignalComputation,
    SignalDataPolicy,
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
    SignalValuePoint,
    SignalValueRegion,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class CciSignalParams(BaseModel):
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


_CCI_LEVELS = [
    SignalReferenceLevel(
        key="oversold",
        label_key="signals.cci.oversold",
        semantic="oversold",
        value=-100,
    ),
    SignalReferenceLevel(
        key="zero",
        label_key="signals.reference.zero",
        semantic="zero",
        value=0,
    ),
    SignalReferenceLevel(
        key="overbought",
        label_key="signals.cci.overbought",
        semantic="overbought",
        value=100,
    ),
]
_CCI_REGIONS = [
    SignalValueRegion(
        key="oversold",
        label_key="signals.cci.oversoldRegion",
        semantic="oversold",
        upper=-100,
        include_upper=False,
    ),
    SignalValueRegion(
        key="neutral",
        label_key="signals.cci.neutralRegion",
        semantic="neutral",
        lower=-100,
        upper=100,
        include_lower=True,
        include_upper=True,
    ),
    SignalValueRegion(
        key="overbought",
        label_key="signals.cci.overboughtRegion",
        semantic="overbought",
        lower=100,
        include_lower=False,
    ),
]


@register_plugin(SignalPluginRegistry)
class CciSignalPlugin(SignalPlugin):
    signal_code = "CCI"
    implementation_version = "1.0.0"
    category = SignalCategory.MOMENTUM
    display_name_key = "signals.cci.name"
    description_key = "signals.cci.description"
    icon = "🧭"
    docs_path = "financial-theory/technical-analysis/indicators/cci/"
    params_model = CciSignalParams
    input_requirements = SignalInputRequirements(
        price_fields=[
            SignalPriceField.HIGH,
            SignalPriceField.LOW,
            SignalPriceField.CLOSE,
        ],
        data_policy=SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS,
        minimum_coverage=0.5,
    )
    output_specs = (
        SignalOutputSpec(
            key="cci",
            label_key="signals.cci.output",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(
                key="cci",
                role=SignalAxisRole.INDEPENDENT,
            ),
            supports_reference_levels=True,
            supports_value_regions=True,
            default_reference_levels=_CCI_LEVELS,
            default_value_regions=_CCI_REGIONS,
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)
    annotation_capabilities = ("threshold_crossing",)

    @classmethod
    def warmup_requirement(
        cls,
        params: CciSignalParams,
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
        params: CciSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        index = [point.date for point in price_points]
        output = ta.cci(
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
            length=params.period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no CCI output")
        spec = self.output_specs[0]
        return SignalComputation(
            series=[
                SignalLineSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    reference_levels=[item.model_copy(deep=True) for item in _CCI_LEVELS],
                    value_regions=[item.model_copy(deep=True) for item in _CCI_REGIONS],
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


__all__ = ["CciSignalParams", "CciSignalPlugin"]
