"""OBV signal plugin backed by pandas-ta-classic delegating to TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import pandas_ta_classic as ta
from pydantic import BaseModel, ConfigDict

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


class ObvSignalParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(SignalPluginRegistry)
class ObvSignalPlugin(SignalPlugin):
    signal_code = "OBV"
    implementation_version = "1.0.0"
    category = SignalCategory.VOLUME
    display_name_key = "signals.obv.name"
    description_key = "signals.obv.description"
    semantic_id = "on_balance_volume"
    semantic_description = "Accumulates volume according to closing-price direction."
    icon = "📊"
    docs_path = "financial-theory/technical-analysis/indicators/obv/"
    params_model = ObvSignalParams
    input_requirements = SignalInputRequirements(
        price_fields=[
            SignalPriceField.CLOSE,
            SignalPriceField.VOLUME,
        ],
        data_policy=SignalDataPolicy.ALLOW_PARTIAL_CONTIGUOUS,
        minimum_coverage=0.5,
    )
    output_specs = (
        SignalOutputSpec(
            key="obv",
            label_key="signals.obv.output",
            semantic_id="on_balance_volume.value",
            semantic_description="Cumulative signed volume rebased at the requested range.",
            kind=SignalSeriesKind.LINE,
            unit=SignalUnit.VOLUME,
            axis=SignalAxisSpec(
                key="obv",
                role=SignalAxisRole.VOLUME,
            ),
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)
    annotation_capabilities = ("threshold_crossing",)

    @classmethod
    def warmup_requirement(
        cls,
        params: ObvSignalParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        return SignalWarmupRequirement(
            minimum_points=1,
            stabilization_points=0,
            total_points=1,
            normalized_tolerance=1e-6,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: ObvSignalParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        index = [point.date for point in price_points]
        output = ta.obv(
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
            talib=True,
        )
        if output is None:
            raise ValueError("pandas-ta-classic returned no OBV output")
        baseline_index = next(
            (position for position, point in enumerate(price_points) if point.date >= context.requested_range.start),
            None,
        )
        if baseline_index is None:
            raise ValueError("OBV input has no point in the requested range")
        baseline = float(output.iloc[baseline_index])
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
                    points=[
                        SignalValuePoint(
                            date=point.date,
                            value=(None if pd.isna(raw_value) else float(raw_value) - baseline),
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


__all__ = ["ObvSignalParams", "ObvSignalPlugin"]
