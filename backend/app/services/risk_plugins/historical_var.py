"""Historical-simulation VaR and CVaR."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
    RiskVarCvarOutput,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import require_primary_returns
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import historical_var_cvar


class HistoricalVarParams(BaseModel):
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
class HistoricalVarAnalytic(RiskAnalytic):
    analytic_code = "historical_var"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.historicalVar.name"
    description_i18n_key = "risk.analytics.historicalVar.description"
    output_kind = RiskOutputKind.VAR_CVAR
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
        RiskScopeKind.BROKER,
    )
    supported_modes = (RiskMode.HISTORICAL, RiskMode.CURRENT_COMPOSITION)
    params_model = HistoricalVarParams
    min_observations = 20

    def compute(self, params, context):
        _dates, returns = require_primary_returns(context)
        if len(returns) - params.horizon_days + 1 < self.min_observations:
            raise RiskUnavailableError(
                "VaR/CVaR has insufficient compounded horizon observations",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={
                    "observations": max(len(returns) - params.horizon_days + 1, 0),
                    "required": self.min_observations,
                    "horizon_days": params.horizon_days,
                },
            )
        summary = historical_var_cvar(
            returns,
            confidence_level=params.confidence_level,
            horizon_days=params.horizon_days,
        )
        return RiskComputation(
            output=RiskVarCvarOutput(
                confidence_level=params.confidence_level,
                horizon_days=params.horizon_days,
                observations=len(summary.horizon_returns),
                value_at_risk=summary.value_at_risk,
                conditional_value_at_risk=summary.conditional_value_at_risk,
            ),
            method="historical_simulation_higher_quantile",
        )
