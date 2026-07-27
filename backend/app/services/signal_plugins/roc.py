"""ROC signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

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
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class RocSignalParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: int = Field(
        12,
        ge=1,
        le=500,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.period",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.period",
        },
    )


_ZERO_LEVEL = SignalReferenceLevel(
    key="zero",
    label_key="signals.reference.zero",
    semantic="zero",
    value=0,
)


@register_plugin(SignalPluginRegistry)
class RocSignalPlugin(SignalPlugin):
    signal_code = "ROC"
    implementation_version = "1.0.0"
    category = SignalCategory.MOMENTUM
    display_name_key = "signals.roc.name"
    description_key = "signals.roc.description"
    semantic_id = "rate_of_change"
    semantic_description = "Measures percentage change from the price one lookback period earlier."
    icon = "🚀"
    docs_path = "financial-theory/technical-analysis/indicators/roc/"
    params_model = RocSignalParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="roc",
            label_key="signals.roc.output",
            semantic_id="rate_of_change.value",
            semantic_description="Percentage change from the closing price one lookback period earlier.",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.PERCENTAGE,
            axis=SignalAxisSpec(
                key="roc",
                role=SignalAxisRole.INDEPENDENT,
            ),
            supports_reference_levels=True,
            default_reference_levels=[_ZERO_LEVEL],
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)
    annotation_capabilities = ("threshold_crossing",)

    @classmethod
    def warmup_requirement(
        cls,
        params: RocSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        total_points = params.period + 1
        return SignalWarmupRequirement(
            minimum_points=total_points,
            stabilization_points=0,
            total_points=total_points,
            normalized_tolerance=1e-6,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: RocSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.roc(
            close,
            length=params.period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no ROC output")
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
                    reference_levels=[_ZERO_LEVEL.model_copy(deep=True)],
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


__all__ = ["RocSignalParams", "RocSignalPlugin"]
