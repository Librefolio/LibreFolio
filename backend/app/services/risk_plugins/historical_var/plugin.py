"""Historical-simulation VaR and CVaR."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
    RiskVarCvarBin,
    RiskVarCvarOutput,
)
from backend.app.services.data_quality_thresholds import RISK_MIN_OBSERVATIONS
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import require_annualization_factor, require_primary_returns
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskSeriesInputs,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import calendar_days_to_observations, historical_var_cvar, return_distribution_histogram


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
    # 3.1.0 — D380: a window whose interquartile range is zero is binned at the Sturges
    # width instead of one bar cut in two by the pin. VaR and CVaR do not move.
    # 3.0.0 — the horizon is in calendar days, compounded over the observations the
    # series holds in them (`horizon_observations`), so "a month" is 30 days on any
    # series. 2.x compounded `horizon_days` observations: three weeks of a series
    # quoted every calendar day.
    # 2.0.0 — M2: coherent Acerbi-Tasche tail estimator (published VaR/CVaR move) plus
    # the return histogram of K1. 1.x published the plug-in estimator, which understated
    # CVaR by a measured 0.27 %.
    algorithm_version = "3.1.0"
    name_i18n_key = "risk.analytics.historicalVar.name"
    description_i18n_key = "risk.analytics.historicalVar.description"
    output_kind = RiskOutputKind.VAR_CVAR
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
    )
    supported_modes = (RiskMode.HISTORICAL, RiskMode.CURRENT_COMPOSITION)
    params_model = HistoricalVarParams
    min_observations = RISK_MIN_OBSERVATIONS
    series_inputs = RiskSeriesInputs.PRIMARY

    def compute(self, params, context):
        _dates, returns = require_primary_returns(context)
        horizon_observations = calendar_days_to_observations(params.horizon_days, require_annualization_factor(context))
        windows = len(returns) - horizon_observations + 1
        if windows < self.min_observations:
            raise RiskUnavailableError(
                "VaR/CVaR has insufficient compounded horizon observations",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={
                    "observations": max(windows, 0),
                    "required": self.min_observations,
                    "horizon_days": params.horizon_days,
                    "horizon_observations": horizon_observations,
                },
            )
        summary = historical_var_cvar(
            returns,
            confidence_level=params.confidence_level,
            horizon_observations=horizon_observations,
        )
        # The bins live in signed-return space while value_at_risk is a positive loss
        # magnitude, so the cut is negated to cross between the two conventions.
        var_bin_edge = -summary.value_at_risk
        histogram = return_distribution_histogram(summary.horizon_returns, pinned_edge=var_bin_edge)
        return_bins = [RiskVarCvarBin(lower_bound=lower, upper_bound=upper, count=count) for lower, upper, count in zip(histogram.edges[:-1], histogram.edges[1:], histogram.counts, strict=True)]
        return RiskComputation(
            output=RiskVarCvarOutput(
                confidence_level=params.confidence_level,
                horizon_days=params.horizon_days,
                horizon_observations=horizon_observations,
                observations=len(summary.horizon_returns),
                value_at_risk=summary.value_at_risk,
                conditional_value_at_risk=summary.conditional_value_at_risk,
                return_bins=return_bins,
                var_bin_edge=var_bin_edge,
            ),
            method="historical_simulation_acerbi_tasche",
        )
