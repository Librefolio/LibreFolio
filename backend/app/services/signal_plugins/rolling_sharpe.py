"""Rolling price-only Sharpe signal."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals import (
    SignalAggregationProfile,
    SignalAvailabilityReason,
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
from backend.app.services.risk.metrics import annualized_sharpe
from backend.app.services.risk.signal_helpers import (
    build_line_computation,
    observed_annualization_factor,
    prepared_primary_returns,
    rolling_single_values,
    undefined_window_warnings,
)
from backend.app.services.signal_plugins.base import (
    SignalPlugin,
    SignalUnavailableError,
)


class RollingSharpeParams(BaseModel):
    """Rolling-Sharpe parameters."""

    model_config = ConfigDict(extra="forbid")

    window: int = Field(
        default=90,
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
    risk_free_annual_rate: float = Field(
        default=0.0,
        gt=-1.0,
        le=10.0,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.riskFreeAnnualRate",
            "x-control-order": 2,
            "x-step": 0.001,
            "x-tooltip-key": "signals.tooltips.riskFreeAnnualRate",
        },
    )


@register_plugin(SignalPluginRegistry)
class RollingSharpePlugin(SignalPlugin):
    """Compare rolling mean excess return with rolling sample volatility."""

    signal_code = "RISK_ROLLING_SHARPE"
    implementation_version = "1.0.0"
    display_name_key = "signals.riskRollingSharpe.name"
    description_key = "signals.riskRollingSharpe.description"
    semantic_id = "rolling_sharpe_ratio"
    semantic_description = "Compares rolling excess return with sample volatility."
    icon = "⚖️"
    category = SignalCategory.RISK
    params_model = RollingSharpeParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        uses_prepared_asset_series=True,
    )
    output_specs = (
        SignalOutputSpec(
            key="rolling_sharpe",
            label_key="signals.riskRollingSharpe.output",
            description_key="signals.riskRollingSharpe.outputDescription",
            semantic_id="rolling_sharpe_ratio.value",
            semantic_description="Annualized mean daily excess return divided by sample volatility.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(
                key="risk_sharpe",
                role=SignalAxisRole.INDEPENDENT,
            ),
            supports_reference_levels=True,
            default_reference_levels=[
                SignalReferenceLevel(
                    key="zero",
                    value=0.0,
                    label_key="signals.reference.zero",
                    semantic="Zero observed excess return per unit of volatility.",
                )
            ],
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: RollingSharpeParams,
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
        params: RollingSharpeParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points
        annualization_factor = observed_annualization_factor(context)
        returns = prepared_primary_returns(context, price_points)
        values, undefined_windows = rolling_single_values(
            returns,
            params.window,
            lambda window: annualized_sharpe(
                window,
                annualization_factor,
                annual_risk_free_rate=params.risk_free_annual_rate,
            ),
        )
        if undefined_windows and all(value is None for value in values):
            raise SignalUnavailableError(
                "Sharpe ratio is undefined because return variance is zero",
                reason_code=SignalAvailabilityReason.UNDEFINED_METRIC,
            )
        return build_line_computation(
            self.output_specs[0],
            price_points,
            values,
            warnings=undefined_window_warnings(undefined_windows),
        )


__all__ = ["RollingSharpeParams", "RollingSharpePlugin"]
