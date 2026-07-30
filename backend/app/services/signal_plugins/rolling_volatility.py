"""Observed-frequency rolling volatility signal."""

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
    SignalSeriesKind,
    SignalUnit,
    SignalWarmupRequirement,
)
from backend.app.services.provider_registry import SignalPluginRegistry, register_plugin
from backend.app.services.risk.metrics import annualized_volatility
from backend.app.services.risk.signal_helpers import (
    build_line_computation,
    observed_annualization_factor,
    prepared_primary_returns,
    rolling_single_values,
)
from backend.app.services.signal_plugins.base import SignalPlugin


class RollingVolatilityParams(BaseModel):
    """Rolling-volatility parameters."""

    model_config = ConfigDict(extra="forbid")

    window: int = Field(
        default=30,
        ge=2,
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
class RollingVolatilityPlugin(SignalPlugin):
    """Annualize rolling sample volatility with the observed calendar factor."""

    signal_code = "RISK_ROLLING_VOLATILITY"
    implementation_version = "1.0.0"
    display_name_key = "signals.riskRollingVolatility.name"
    description_key = "signals.riskRollingVolatility.description"
    semantic_id = "rolling_realized_volatility"
    semantic_description = "Annualizes rolling sample volatility at observed frequency."
    icon = "〽️"
    category = SignalCategory.RISK
    params_model = RollingVolatilityParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        uses_prepared_asset_series=True,
    )
    output_specs = (
        SignalOutputSpec(
            key="rolling_volatility",
            label_key="signals.riskRollingVolatility.output",
            description_key="signals.riskRollingVolatility.outputDescription",
            semantic_id="rolling_realized_volatility.value",
            semantic_description="Annualized sample standard deviation of price-only returns.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            axis=SignalAxisSpec(
                key="risk_volatility",
                role=SignalAxisRole.INDEPENDENT,
                minimum=0.0,
            ),
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: RollingVolatilityParams,
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
        params: RollingVolatilityParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points
        annualization_factor = observed_annualization_factor(context)
        returns = prepared_primary_returns(context, price_points)
        values, _ = rolling_single_values(
            returns,
            params.window,
            lambda window: annualized_volatility(
                window,
                annualization_factor,
            )
            * 100,
        )
        return build_line_computation(self.output_specs[0], price_points, values)


__all__ = ["RollingVolatilityParams", "RollingVolatilityPlugin"]
