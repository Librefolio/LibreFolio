"""Aroon signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAxisRole,
    SignalAxisSpec,
    SignalCategory,
    SignalColorRole,
    SignalComputation,
    SignalDataPolicy,
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


class AroonSignalParams(BaseModel):
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


_AROON_AXIS = SignalAxisSpec(
    key="aroon",
    role=SignalAxisRole.INDEPENDENT,
    minimum=-100,
    maximum=100,
)
_ZERO_LEVEL = SignalReferenceLevel(
    key="zero",
    label_key="signals.reference.zero",
    semantic="zero",
    value=0,
)


@register_plugin(SignalPluginRegistry)
class AroonSignalPlugin(SignalPlugin):
    signal_code = "AROON"
    implementation_version = "1.0.0"
    category = SignalCategory.TREND
    display_name_key = "signals.aroon.name"
    description_key = "signals.aroon.description"
    semantic_id = "aroon"
    semantic_description = "Measures how recently lookback-period highs and lows occurred."
    icon = "⏱️"
    docs_path = "financial-theory/technical-analysis/indicators/aroon/"
    params_model = AroonSignalParams
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
            key="up",
            label_key="signals.aroon.up",
            description_key="signals.aroon.upDescription",
            semantic_id="aroon.up",
            semantic_description="Recency score for the highest high in the lookback window.",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_AROON_AXIS,
            style=SignalOutputStyle(
                color_role=SignalColorRole.POSITIVE,
                line_pattern=SignalLinePattern.SOLID,
            ),
        ),
        SignalOutputSpec(
            key="down",
            label_key="signals.aroon.down",
            description_key="signals.aroon.downDescription",
            semantic_id="aroon.down",
            semantic_description="Recency score for the lowest low in the lookback window.",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_AROON_AXIS,
            style=SignalOutputStyle(
                color_role=SignalColorRole.NEGATIVE,
                line_pattern=SignalLinePattern.SOLID,
            ),
        ),
        SignalOutputSpec(
            key="oscillator",
            label_key="signals.aroon.oscillator",
            description_key="signals.aroon.oscillatorDescription",
            semantic_id="aroon.oscillator",
            semantic_description="Difference between the Aroon up and down scores.",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.INDEX,
            axis=_AROON_AXIS,
            style=SignalOutputStyle(
                color_role=SignalColorRole.ACCENT,
                line_pattern=SignalLinePattern.DASHED,
            ),
            supports_reference_levels=True,
            default_reference_levels=[_ZERO_LEVEL],
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)
    annotation_capabilities = (
        "line_crossover",
        "threshold_crossing",
    )

    @classmethod
    def warmup_requirement(
        cls,
        params: AroonSignalParams,
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
        params: AroonSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        index = [point.date for point in price_points]
        output = ta.aroon(
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
            length=params.period,
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no Aroon output")
        columns = (
            self._column(output, "AROONU_"),
            self._column(output, "AROOND_"),
            self._column(output, "AROONOSC_"),
        )
        series = []
        for index_position, (spec, column) in enumerate(
            zip(
                self.output_specs,
                columns,
                strict=True,
            )
        ):
            series.append(
                SignalLineSeries(
                    key=spec.key,
                    label_key=spec.label_key,
                    description_key=spec.description_key,
                    semantic_id=spec.semantic_id,
                    semantic_description=spec.semantic_description,
                    unit=spec.unit,
                    axis=spec.axis.model_copy(deep=True),
                    style=spec.style.model_copy(deep=True),
                    reference_levels=([_ZERO_LEVEL.model_copy(deep=True)] if index_position == 2 else []),
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
            raise ValueError(f"Expected one Aroon column with prefix '{prefix}', got {matches}")
        return output[matches[0]]


__all__ = ["AroonSignalParams", "AroonSignalPlugin"]
