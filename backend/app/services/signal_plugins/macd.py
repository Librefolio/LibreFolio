"""MACD signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.schemas.signals import (
    SignalAxisRole,
    SignalAxisSpec,
    SignalBarSeries,
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
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import (
    SignalPluginRegistry,
    register_plugin,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class MacdSignalParams(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
    )

    fast_period: int = Field(
        12,
        alias="fastPeriod",
        ge=2,
        le=200,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.fastPeriod",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.fastPeriod",
        },
    )
    slow_period: int = Field(
        26,
        alias="slowPeriod",
        ge=2,
        le=500,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.slowPeriod",
            "x-control-order": 2,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.slowPeriod",
        },
    )
    signal_period: int = Field(
        9,
        alias="signalPeriod",
        ge=2,
        le=100,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.signalPeriod",
            "x-control-order": 3,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "chartSettings.tooltips.signalPeriod",
        },
    )

    @model_validator(mode="after")
    def validate_periods(self) -> MacdSignalParams:
        if self.fast_period >= self.slow_period:
            raise ValueError("fastPeriod must be lower than slowPeriod")
        return self


_MACD_AXIS = SignalAxisSpec(
    key="macd",
    role=SignalAxisRole.INDEPENDENT,
)


@register_plugin(SignalPluginRegistry)
class MacdSignalPlugin(SignalPlugin):
    signal_code = "MACD"
    implementation_version = "1.0.0"
    category = SignalCategory.MOMENTUM
    display_name_key = "signals.macd.name"
    description_key = "signals.macd.description"
    icon = "📶"
    docs_path = "financial-theory/technical-analysis/indicators/macd/"
    params_model = MacdSignalParams
    input_requirements = SignalInputRequirements(price_fields=[SignalPriceField.CLOSE])
    output_specs = (
        SignalOutputSpec(
            key="macd",
            label_key="signals.macd.line",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.PRICE,
            axis=_MACD_AXIS,
        ),
        SignalOutputSpec(
            key="signal",
            label_key="signals.macd.signal",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.PRICE,
            axis=_MACD_AXIS,
        ),
        SignalOutputSpec(
            key="histogram",
            label_key="signals.macd.histogram",
            kind=SignalSeriesKind.BAR,
            unit=SignalUnit.PRICE,
            axis=_MACD_AXIS,
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
        params: MacdSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        minimum_points = params.slow_period + params.signal_period - 1
        total_points = max(
            minimum_points,
            8 * max(params.slow_period, params.signal_period),
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
        params: MacdSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        close = pd.Series(
            [float(point.close) for point in price_points],
            index=[point.date for point in price_points],
            dtype=float,
        )
        output = ta.macd(
            close,
            fast=params.fast_period,
            slow=params.slow_period,
            signal=params.signal_period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no MACD output")
        macd_values = self._column(output, "MACD_")
        histogram_values = self._column(output, "MACDh_")
        signal_values = self._column(output, "MACDs_")
        raw_series = (
            (SignalLineSeries, macd_values),
            (SignalLineSeries, signal_values),
            (SignalBarSeries, histogram_values),
        )
        series = []
        for spec, (series_type, values) in zip(
            self.output_specs,
            raw_series,
            strict=True,
        ):
            series.append(
                series_type(
                    key=spec.key,
                    label_key=spec.label_key,
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
            raise ValueError(f"Expected one MACD column with prefix '{prefix}', got {matches}")
        return output[matches[0]]


__all__ = ["MacdSignalParams", "MacdSignalPlugin"]
