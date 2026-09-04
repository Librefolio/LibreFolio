"""Rolling compounded-return signal."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

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
from backend.app.services.risk.metrics import compounded_return
from backend.app.services.risk.signal_helpers import (
    build_line_computation,
    prepared_primary_returns,
    rolling_single_values,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class RollingReturnParams(BaseModel):
    """Rolling-return parameters."""

    model_config = ConfigDict(extra="forbid")

    window: int = Field(
        default=30,
        ge=1,
        le=500,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.window",
            "x-control-order": 1,
            "x-suffix": "days",
            "x-step": 1,
            "x-tooltip-key": "signals.tooltips.riskWindow",
        },
    )


@register_plugin(SignalPluginRegistry)
class RollingReturnPlugin(SignalPlugin):
    """Compound canonical simple returns inside each rolling window."""

    signal_code = "RISK_ROLLING_RETURN"
    implementation_version = "1.0.0"
    display_name_key = "signals.riskRollingReturn.name"
    description_key = "signals.riskRollingReturn.description"
    semantic_id = "rolling_compounded_return"
    semantic_description = "Compounds canonical simple returns over a rolling window."
    icon = "↗️"
    category = SignalCategory.RISK
    params_model = RollingReturnParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        uses_prepared_asset_series=True,
    )
    output_specs = (
        SignalOutputSpec(
            key="rolling_return",
            label_key="signals.riskRollingReturn.output",
            description_key="signals.riskRollingReturn.outputDescription",
            semantic_id="rolling_compounded_return.value",
            semantic_description="Compounded price-only holding-period return.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            axis=SignalAxisSpec(
                key="risk_return",
                role=SignalAxisRole.INDEPENDENT,
            ),
            supports_reference_levels=True,
            default_reference_levels=[
                SignalReferenceLevel(
                    key="zero",
                    value=0.0,
                    label_key="signals.reference.zero",
                    semantic="No compounded gain or loss.",
                )
            ],
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: RollingReturnParams,
        context: SignalExecutionContext,
    ) -> SignalWarmupRequirement:
        del context
        return SignalWarmupRequirement(
            minimum_points=params.window + 1,
            stabilization_points=0,
            total_points=params.window + 1,
            normalized_tolerance=1e-6,
        )

    def compute(
        self,
        price_points: Sequence[SignalPricePoint],
        event_points: Sequence[SignalEventPoint],
        params: RollingReturnParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points
        returns = prepared_primary_returns(context, price_points)
        values, _ = rolling_single_values(
            returns,
            params.window,
            lambda window: compounded_return(window) * 100,
        )
        return build_line_computation(self.output_specs[0], price_points, values)


__all__ = ["RollingReturnParams", "RollingReturnPlugin"]
