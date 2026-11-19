"""Rolling semi-deviation signal (RN-22): the Sortino's denominator, window by window, on the volatility's axis."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals.inputs import SignalEventPoint, SignalExecutionContext, SignalInputRequirements, SignalPricePoint, SignalWarmupRequirement
from backend.app.schemas.signals.outputs import SignalAxisSpec, SignalOutputSpec
from backend.app.schemas.signals.result import SignalComputation
from backend.app.schemas.signals.vocabulary import SignalAggregationProfile, SignalAxisRole, SignalCategory, SignalDomain, SignalPriceField, SignalSeriesKind, SignalUnit
from backend.app.services.platform.provider_registry import register_plugin
from backend.app.services.signals.base import SignalPlugin
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.signals.risk_adapters import (
    build_line_computation,
    observed_annualization_factor,
    prepared_primary_returns,
    rolling_annualized_downside_deviation_values,
)


class RollingDownsideDeviationParams(BaseModel):
    """Rolling semi-deviation parameters: the window and the Sortino's target."""

    model_config = ConfigDict(extra="forbid")

    # 30 like the rolling volatility: switched on together, the pair compares like with like.
    window: int = Field(
        default=30,
        ge=2,
        le=500,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.window",
            "x-control-order": 1,
            "x-suffix": "observations",
            "x-step": 1,
            "x-tooltip-key": "signals.tooltips.riskWindow",
        },
    )
    # The analytics' own name and the Sharpe's bounds: RN-21 fills it from the user's common rate.
    target_annual_return: float = Field(
        default=0.0,
        gt=-1.0,
        le=10.0,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.targetAnnualReturn",
            # The reader's one risk-free rate, shared with the risk pages (RN-21): the chart shows it, never a field.
            "x-control": "risk_free_rate",
            "x-control-order": 2,
            "x-step": 0.001,
            "x-tooltip-key": "signals.tooltips.targetAnnualReturn",
        },
    )


@register_plugin(SignalPluginRegistry)
class RollingDownsideDeviationPlugin(SignalPlugin):
    """Annualize, window by window, the RMS shortfall below the Sortino's target (``annualized_downside_deviation``)."""

    signal_code = "RISK_ROLLING_DOWNSIDE_DEVIATION"
    implementation_version = "1.0.0"
    computes_on_quote_days = False
    display_name_key = "signals.riskRollingDownsideDeviation.name"
    description_key = "signals.riskRollingDownsideDeviation.description"
    semantic_id = "rolling_downside_deviation"
    semantic_description = "Annualizes the rolling semi-deviation below the target return."
    icon = "🔻"
    docs_path = "financial-theory/technical-analysis/risk-metrics/sortino-ratio/"
    category = SignalCategory.RISK
    params_model = RollingDownsideDeviationParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        uses_prepared_asset_series=True,
    )
    output_specs = (
        SignalOutputSpec(
            key="rolling_downside_deviation",
            label_key="signals.riskRollingDownsideDeviation.output",
            description_key="signals.riskRollingDownsideDeviation.outputDescription",
            semantic_id="rolling_downside_deviation.value",
            semantic_description="Annualized root-mean-square shortfall of price-only returns below the target.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.PERCENTAGE,
            # The rolling volatility's own axis (Q23 a): on together, the two lines read as a pair.
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
        params: RollingDownsideDeviationParams,
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
        params: RollingDownsideDeviationParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points
        annualization_factor = observed_annualization_factor(context)
        returns = prepared_primary_returns(context, price_points)
        values, _ = rolling_annualized_downside_deviation_values(
            returns,
            params.window,
            annualization_factor,
            annual_target_return=params.target_annual_return,
            scale=100.0,
        )
        return build_line_computation(self.output_specs[0], price_points, values)


__all__ = ["RollingDownsideDeviationParams", "RollingDownsideDeviationPlugin"]
