"""Rolling beta against a real comparison asset."""

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
from backend.app.services.risk.metrics import beta
from backend.app.services.risk.signal_helpers import (
    build_line_computation,
    prepared_comparison_returns,
    prepared_primary_returns,
    rolling_pair_values,
    undefined_window_warnings,
)
from backend.app.services.signal_plugins.base import (
    SignalPlugin,
    SignalUnavailableError,
)


class RollingBetaParams(BaseModel):
    """Rolling-beta parameters."""

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
    comparison_asset_id: int = Field(
        ge=1,
        json_schema_extra={
            "x-control": "comparison_asset",
            "x-i18n-key": "chartSettings.params.comparisonAsset",
            "x-control-order": 2,
            "x-tooltip-key": "signals.tooltips.comparisonAsset",
        },
    )


@register_plugin(SignalPluginRegistry)
class RollingBetaPlugin(SignalPlugin):
    """Estimate rolling sample beta on a canonical joint return calendar."""

    signal_code = "RISK_ROLLING_BETA"
    implementation_version = "1.0.0"
    display_name_key = "signals.riskRollingBeta.name"
    description_key = "signals.riskRollingBeta.description"
    semantic_id = "rolling_beta"
    semantic_description = "Estimates rolling sensitivity to a real comparison asset."
    icon = "β"
    category = SignalCategory.RISK
    params_model = RollingBetaParams
    input_requirements = SignalInputRequirements(
        price_fields=[SignalPriceField.CLOSE],
        uses_prepared_asset_series=True,
        comparison_asset_param="comparison_asset_id",
    )
    output_specs = (
        SignalOutputSpec(
            key="rolling_beta",
            label_key="signals.riskRollingBeta.output",
            description_key="signals.riskRollingBeta.outputDescription",
            semantic_id="rolling_beta.value",
            semantic_description="Sample covariance divided by comparison-asset sample variance.",
            kind=SignalSeriesKind.LINE,
            aggregation_profile=SignalAggregationProfile.LAST_WITH_RANGE,
            unit=SignalUnit.INDEX,
            axis=SignalAxisSpec(
                key="risk_beta",
                role=SignalAxisRole.INDEPENDENT,
            ),
            supports_reference_levels=True,
            default_reference_levels=[
                SignalReferenceLevel(
                    key="zero",
                    value=0.0,
                    label_key="signals.reference.zero",
                    semantic="No measured co-movement sensitivity.",
                ),
                SignalReferenceLevel(
                    key="one",
                    value=1.0,
                    label_key="signals.riskRollingBeta.referenceOne",
                    semantic="One-for-one measured sensitivity.",
                ),
            ],
        ),
    )
    compatible_domains = (SignalDomain.ASSET,)

    @classmethod
    def warmup_requirement(
        cls,
        params: RollingBetaParams,
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
        params: RollingBetaParams,
        context: SignalExecutionContext,
    ) -> SignalComputation:
        del event_points
        primary_returns = prepared_primary_returns(context, price_points)
        comparison_returns = prepared_comparison_returns(context, price_points)
        values, undefined_windows = rolling_pair_values(
            primary_returns,
            comparison_returns,
            params.window,
            beta,
        )
        if undefined_windows and all(value is None for value in values):
            raise SignalUnavailableError(
                "Beta is undefined because comparison-asset variance is zero",
                reason_code=SignalAvailabilityReason.UNDEFINED_METRIC,
            )
        return build_line_computation(
            self.output_specs[0],
            price_points,
            values,
            warnings=undefined_window_warnings(undefined_windows),
        )


__all__ = ["RollingBetaParams", "RollingBetaPlugin"]
