"""Rolling Omega signal (RN-22): gains against losses around the Sortino's target, window by window, read against 1×."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.signals.inputs import SignalEventPoint, SignalExecutionContext, SignalInputRequirements, SignalPricePoint, SignalWarmupRequirement
from backend.app.schemas.signals.outputs import SignalAxisSpec, SignalOutputSpec, SignalReferenceLevel
from backend.app.schemas.signals.result import SignalComputation
from backend.app.schemas.signals.vocabulary import SignalAggregationProfile, SignalAvailabilityReason, SignalAxisRole, SignalCategory, SignalDomain, SignalPriceField, SignalSeriesKind, SignalUnit
from backend.app.services.platform.provider_registry import register_plugin
from backend.app.services.signals.base import SignalPlugin, SignalUnavailableError
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.signals.risk_adapters import (
    build_line_computation,
    observed_annualization_factor,
    prepared_primary_returns,
    rolling_omega_values,
    undefined_window_warnings,
)


class RollingOmegaParams(BaseModel):
    """Rolling-Omega parameters: the window and the Sortino's target."""

    model_config = ConfigDict(extra="forbid")

    # 90 like the rolling Sharpe, the other ratio of the family.
    window: int = Field(
        default=90,
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
class RollingOmegaPlugin(SignalPlugin):
    """Divide, window by window, the gains above the target by the losses below it (``omega_ratio``)."""

    signal_code = "RISK_ROLLING_OMEGA"
    implementation_version = "1.0.0"
    computes_on_quote_days = False
    display_name_key = "signals.riskRollingOmega.name"
    description_key = "signals.riskRollingOmega.description"
    semantic_id = "rolling_omega_ratio"
    semantic_description = "Compares rolling gains above the target with losses below it."
    icon = "➗"
    docs_path = "financial-theory/technical-analysis/risk-metrics/sortino-ratio/"
    category = SignalCategory.RISK
    params_model = RollingOmegaParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        uses_prepared_asset_series=True,
    )
    output_specs = (
        SignalOutputSpec(
            key="rolling_omega",
            label_key="signals.riskRollingOmega.output",
            description_key="signals.riskRollingOmega.outputDescription",
            semantic_id="rolling_omega_ratio.value",
            semantic_description="Sum of price-only returns above the target divided by the sum of shortfalls below it.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(
                key="risk_omega",
                role=SignalAxisRole.INDEPENDENT,
                minimum=0.0,
            ),
            supports_reference_levels=True,
            default_reference_levels=[
                SignalReferenceLevel(
                    key="even",
                    value=1.0,
                    label_key="signals.riskRollingOmega.referenceEven",
                    semantic="Gains above the target equal the losses below it.",
                )
            ],
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: RollingOmegaParams,
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
        params: RollingOmegaParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points
        annualization_factor = observed_annualization_factor(context)
        returns = prepared_primary_returns(context, price_points)
        values, undefined_windows = rolling_omega_values(
            returns,
            params.window,
            annualization_factor,
            annual_target_return=params.target_annual_return,
        )
        if undefined_windows and all(value is None for value in values):
            raise SignalUnavailableError(
                "Omega ratio is undefined because no return falls below the target",
                reason_code=SignalAvailabilityReason.UNDEFINED_METRIC,
            )
        return build_line_computation(
            self.output_specs[0],
            price_points,
            values,
            warnings=undefined_window_warnings(undefined_windows),
        )


__all__ = ["RollingOmegaParams", "RollingOmegaPlugin"]
