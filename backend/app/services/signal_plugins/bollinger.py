"""Bollinger Bands plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAiExportTemporalRule,
    SignalAxisRole,
    SignalAxisSpec,
    SignalBandPoint,
    SignalBandSeries,
    SignalCategory,
    SignalComputation,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalOutputSpec,
    SignalPriceField,
    SignalPricePoint,
    SignalSeriesKind,
    SignalTemporalClass,
    SignalUnit,
    SignalViewTransform,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class BollingerSignalParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: int = Field(
        20,
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
    multiplier: FiniteFloat = Field(
        2.0,
        ge=0.5,
        le=5,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.multiplier",
            "x-control-order": 2,
            "x-suffix": "σ",
            "x-step": 0.1,
            "x-tooltip-key": "chartSettings.tooltips.multiplier",
        },
    )


@register_plugin(SignalPluginRegistry)
class BollingerSignalPlugin(SignalPlugin):
    signal_code = "BOLLINGER"
    implementation_version = "1.0.0"
    category = SignalCategory.VOLATILITY
    display_name_key = "signals.bollinger.name"
    description_key = "signals.bollinger.description"
    semantic_id = "bollinger_bands"
    semantic_description = "Describes a moving-average envelope scaled by recent price dispersion."
    icon = "🌊"
    docs_path = "financial-theory/technical-analysis/indicators/bollinger-bands/"
    params_model = BollingerSignalParams
    ai_export_temporal_rules = (SignalAiExportTemporalRule(temporal_class=SignalTemporalClass.MEDIUM_FAST),)
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="bands",
            label_key="signals.bollinger.bands",
            semantic_id="bollinger_bands.envelope",
            semantic_description="Lower, middle, and upper bands around the moving average.",
            kind=SignalSeriesKind.BAND,
            aggregation_profile=SignalAggregationProfile.BAND_ENVELOPE,
            unit=SignalUnit.PRICE,
            axis=SignalAxisSpec(
                key="price",
                role=SignalAxisRole.PRICE,
            ),
            view_transform=SignalViewTransform.BASE_PERCENTAGE,
        ),
    )
    compatible_domains = (SignalDomain.ASSET, SignalDomain.FX)

    @classmethod
    def warmup_requirement(
        cls,
        params: BollingerSignalParams,
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
        params: BollingerSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.bbands(
            close,
            length=params.period,
            std=params.multiplier,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no Bollinger Bands output")
        lower = self._column(output, "BBL_")
        middle = self._column(output, "BBM_")
        upper = self._column(output, "BBU_")
        spec = self.output_specs[0]
        return SignalComputation(
            series=[
                SignalBandSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    semantic_id=spec.semantic_id,
                    semantic_description=spec.semantic_description,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    view_transform=spec.view_transform,
                    points=[
                        SignalBandPoint(
                            date=point.date,
                            lower=(None if pd.isna(lower_value) else float(lower_value)),
                            middle=(None if pd.isna(middle_value) else float(middle_value)),
                            upper=(None if pd.isna(upper_value) else float(upper_value)),
                        )
                        for (
                            point,
                            lower_value,
                            middle_value,
                            upper_value,
                        ) in zip(
                            price_points,
                            lower,
                            middle,
                            upper,
                            strict=True,
                        )
                    ],
                )
            ]
        )

    @staticmethod
    def _column(output: pd.DataFrame, prefix: str) -> pd.Series:
        matches = [column for column in output.columns if column.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"Expected one Bollinger column with prefix '{prefix}', got {matches}")
        return output[matches[0]]


__all__ = ["BollingerSignalParams", "BollingerSignalPlugin"]
