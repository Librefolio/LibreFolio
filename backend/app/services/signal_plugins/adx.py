"""ADX signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

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


class AdxSignalParams(BaseModel):
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


_ADX_AXIS = SignalAxisSpec(
    key="adx",
    role=SignalAxisRole.INDEPENDENT,
    minimum=0,
    maximum=100,
)


@register_plugin(SignalPluginRegistry)
class AdxSignalPlugin(SignalPlugin):
    signal_code = "ADX"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.adx.name"
    description_key = "signals.adx.description"
    icon = "💹"
    docs_path = "financial-theory/technical-analysis/indicators/adx/"
    params_model = AdxSignalParams
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
            key="adx",
            label_key="signals.adx.adx",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_ADX_AXIS,
        ),
        SignalOutputSpec(
            key="plus_di",
            label_key="signals.adx.plusDi",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_ADX_AXIS,
        ),
        SignalOutputSpec(
            key="minus_di",
            label_key="signals.adx.minusDi",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_ADX_AXIS,
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)
    annotation_capabilities = ("line_crossover",)

    @classmethod
    def warmup_requirement(
        cls,
        params: AdxSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        minimum_points = 2 * params.period
        total_points = 18 * params.period
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
        params: AdxSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        index = [point.date for point in price_points]
        output = ta.adx(
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
            raise ValueError("pandas-ta-classic returned no ADX output")
        values = (
            self._column(output, "ADX_"),
            self._column(output, "DMP_"),
            self._column(output, "DMN_"),
        )
        series = []
        for spec, column in zip(
            self.output_specs,
            values,
            strict=True,
        ):
            series.append(
                SignalLineSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    points=[
                        SignalValuePoint(
                            date=point.date,
                            value=(None if pd.isna(raw_value) else float(raw_value)),
                        )
                        for point, raw_value in zip(
                            price_points,
                            column,
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
            raise ValueError(f"Expected one ADX column with prefix '{prefix}', got {matches}")
        return output[matches[0]]


__all__ = ["AdxSignalParams", "AdxSignalPlugin"]
