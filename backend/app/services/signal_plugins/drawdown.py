"""Price-only underwater drawdown signal."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAxisRole,
    SignalAxisSpec,
    SignalCategory,
    SignalComputation,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalInputRequirements,
    SignalOutputSpec,
    SignalPriceField,
    SignalPricePoint,
    SignalReferenceLevel,
    SignalSeriesKind,
    SignalUnit,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import SignalPluginRegistry, register_plugin
from backend.app.services.risk.metrics import underwater_drawdown
from backend.app.services.risk.signal_helpers import build_line_computation
from backend.app.services.signal_plugins.base import SignalPlugin


class DrawdownParams(BaseModel):
    """Underwater drawdown has no configurable parameters."""

    model_config = ConfigDict(extra="forbid")


@register_plugin(SignalPluginRegistry)
class DrawdownPlugin(SignalPlugin):
    """Render running drawdown from the canonical target-currency price series."""

    signal_code = "RISK_DRAWDOWN"
    implementation_version = "1.0.0"
    display_name_key = "signals.riskDrawdown.name"
    description_key = "signals.riskDrawdown.description"
    semantic_id = "underwater_drawdown"
    semantic_description = "Measures each price observation below its running peak."
    icon = "📉"
    category = SignalCategory.RISK
    params_model = DrawdownParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        uses_prepared_asset_series=True,
    )
    output_specs = (
        SignalOutputSpec(
            key="drawdown",
            label_key="signals.riskDrawdown.output",
            description_key="signals.riskDrawdown.outputDescription",
            semantic_id="underwater_drawdown.value",
            semantic_description="Peak-relative price-only drawdown, never above zero.",
            kind=SignalSeriesKind.AREA,
            aggregation_profile=SignalAggregationProfile.MIN_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            axis=SignalAxisSpec(
                key="risk_drawdown",
                role=SignalAxisRole.INDEPENDENT,
                maximum=0.0,
            ),
            supports_reference_levels=True,
            default_reference_levels=[
                SignalReferenceLevel(
                    key="peak",
                    value=0.0,
                    label_key="signals.riskDrawdown.referencePeak",
                    semantic="Running peak with no drawdown.",
                )
            ],
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: DrawdownParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        del params, context
        return SignalWarmupRequirement(
            minimum_points=2,
            stabilization_points=0,
            total_points=2,
            normalized_tolerance=1e-6,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: DrawdownParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points, params, context
        values = [value * 100 for value in underwater_drawdown([float(point.close) for point in price_points])]
        return build_line_computation(self.output_specs[0], price_points, values)


__all__ = ["DrawdownParams", "DrawdownPlugin"]
