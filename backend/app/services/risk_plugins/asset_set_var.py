"""Historical-simulation VaR and CVaR of each selected asset."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskAssetSetVarCvarItem,
    RiskAssetSetVarCvarOutput,
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import prepared_scope_series
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskExecutionContext,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import historical_var_cvar


class AssetSetVarParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence_level: float = Field(
        0.95,
        gt=0,
        lt=1,
        json_schema_extra={
            "x-i18n-key": "risk.params.confidenceLevel",
            "x-control-order": 1,
            "x-step": 0.01,
        },
    )
    horizon_days: int = Field(
        1,
        ge=1,
        le=365,
        json_schema_extra={
            "x-i18n-key": "risk.params.horizonDays",
            "x-control-order": 2,
            "x-step": 1,
            "x-suffix": "days",
        },
    )


@register_plugin(RiskAnalyticRegistry)
class AssetSetVarAnalytic(RiskAnalytic):
    """One bad day, and one bad month, per selected asset.

    The estimator is the one the singular analytic publishes — the coherent
    Acerbi-Tasche tail rather than the plug-in one — so a figure read here and a
    figure read on an asset detail page mean the same thing.

    ⚠️ THE HORIZON CHECK IS SET-LEVEL, AND IT CAN ONLY BE. Compounding to a
    multi-day horizon costs ``horizon_days - 1`` observations, so a request that
    clears the plugin's minimum on raw returns can still fall short once
    compounded. Because every asset in one prepared set carries the same joint
    calendar, that shortfall is the same for all of them: there is no case where
    the horizon leaves one asset measurable and another not. The refusal is
    therefore reported once, for the request, instead of silently dropping rows.
    """

    analytic_code = "asset_set_var"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.assetSetVar.name"
    description_i18n_key = "risk.analytics.assetSetVar.description"
    output_kind = RiskOutputKind.VAR_CVAR_SET
    supported_scopes = (RiskScopeKind.ASSET_SET,)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = AssetSetVarParams
    min_observations = 20

    def compute(self, params: AssetSetVarParams, context: RiskExecutionContext) -> RiskComputation:
        series = prepared_scope_series(context)
        prepared = context.prepared_series
        observations = prepared.n_observations if prepared else 0
        horizon_observations = observations - params.horizon_days + 1
        if horizon_observations < self.min_observations:
            raise RiskUnavailableError(
                "VaR/CVaR has insufficient compounded horizon observations",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={
                    "observations": max(horizon_observations, 0),
                    "required": self.min_observations,
                    "horizon_days": params.horizon_days,
                },
            )

        items: list[RiskAssetSetVarCvarItem] = []
        horizon_count = horizon_observations
        for asset_id, _dates, returns in series:
            summary = historical_var_cvar(
                returns,
                confidence_level=params.confidence_level,
                horizon_days=params.horizon_days,
            )
            horizon_count = len(summary.horizon_returns)
            items.append(
                RiskAssetSetVarCvarItem(
                    asset_id=asset_id,
                    value_at_risk=summary.value_at_risk,
                    conditional_value_at_risk=summary.conditional_value_at_risk,
                )
            )

        return RiskComputation(
            output=RiskAssetSetVarCvarOutput(
                confidence_level=params.confidence_level,
                horizon_days=params.horizon_days,
                # Stated once: the joint calendar gives every asset the same
                # compounded count, so the loop above rewrites the same number.
                observations=horizon_count,
                items=items,
            ),
            method="historical_simulation_acerbi_tasche",
            n_observations=observations,
            calendar_days=prepared.calendar_days if prepared else 0,
            annualization_factor=prepared.annualization_factor if prepared else None,
            coverage=prepared.calendar_coverage if prepared else 0,
            return_basis=context.primary_return_basis,
        )
