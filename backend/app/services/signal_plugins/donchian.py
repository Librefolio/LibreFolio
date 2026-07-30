"""Donchian Channels plugin using native pandas-ta-classic."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAxisRole,
    SignalAxisSpec,
    SignalBandPoint,
    SignalBandSeries,
    SignalCategory,
    SignalComputation,
    SignalDataPolicy,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalOutputSpec,
    SignalPriceField,
    SignalPricePoint,
    SignalSeriesKind,
    SignalUnit,
    SignalViewTransform,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class DonchianSignalParams(BaseModel):
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
class DonchianSignalPlugin(SignalPlugin):
    signal_code = "DONCHIAN"
    implementation_version = "1.0.0"
    category = SignalCategory.VOLATILITY
    display_name_key = "signals.donchian.name"
    description_key = "signals.donchian.description"
    semantic_id = "donchian_channels"
    semantic_description = "Describes recent high and low boundaries over a rolling window."
    icon = "↔️"
    docs_path = "financial-theory/technical-analysis/indicators/donchian-channels/"
    params_model = DonchianSignalParams
    input_requirements = SignalInputRequirements(
        price_fields=[
            SignalPriceField.HIGH,
            SignalPriceField.LOW,
        ],
        data_policy=SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS,
        minimum_coverage=0.5,
    )
    output_specs = (
        SignalOutputSpec(
            key="channels",
            label_key="signals.donchian.channels",
            semantic_id="donchian_channels.envelope",
            semantic_description="Rolling lower, midpoint, and upper price boundaries.",
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
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: DonchianSignalParams,
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
        params: DonchianSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        index = [point.date for point in price_points]
        output = ta.donchian(
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
            lower_length=params.period,
            upper_length=params.period,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no Donchian output")
        lower = self._column(output, "DCL_")
        middle = self._column(output, "DCM_")
        upper = self._column(output, "DCU_")
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
            raise ValueError(f"Expected one Donchian column with prefix '{prefix}', got {matches}")
        return output[matches[0]]


__all__ = ["DonchianSignalParams", "DonchianSignalPlugin"]
