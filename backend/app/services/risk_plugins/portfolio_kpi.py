"""Historical portfolio risk KPIs computed from period TWRR."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskFreeReference,
    RiskKpiOutput,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    elapsed_calendar_days,
    require_annualization_factor,
    require_primary_returns,
)
from backend.app.services.risk.base import RiskAnalytic, RiskComputation
from backend.app.services.risk.metrics import (
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
    summarize_drawdown,
)


class PortfolioKpiParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    risk_free_annual_rate: float = Field(
        0.0,
        gt=-1,
        json_schema_extra={
            "x-i18n-key": "chartSettings.params.riskFreeAnnualRate",
            "x-control-order": 1,
            "x-step": 0.001,
        },
    )
    target_annual_return: float = Field(
        0.0,
        gt=-1,
        json_schema_extra={
            "x-i18n-key": "risk.params.targetAnnualReturn",
            "x-control-order": 2,
            "x-step": 0.001,
        },
    )


@register_plugin(RiskAnalyticRegistry)
class PortfolioKpiAnalytic(RiskAnalytic):
    analytic_code = "portfolio_kpi"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.portfolioKpi.name"
    description_i18n_key = "risk.analytics.portfolioKpi.description"
    output_kind = RiskOutputKind.KPI
    supported_scopes = (RiskScopeKind.PORTFOLIO, RiskScopeKind.BROKER)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = PortfolioKpiParams
    min_observations = 20

    def compute(self, params, context):
        _dates, returns = require_primary_returns(context)
        annualization = require_annualization_factor(context)
        drawdown = summarize_drawdown(
            returns,
            elapsed_units=elapsed_calendar_days(context),
        )
        sharpe = annualized_sharpe(
            returns,
            annualization,
            annual_risk_free_rate=params.risk_free_annual_rate,
        )
        sortino = annualized_sortino(
            returns,
            annualization,
            annual_target_return=params.target_annual_return,
        )
        warnings: list[RiskWarning] = []
        if sharpe is None:
            warnings.append(
                RiskWarning(
                    code="sharpe_undefined",
                    message="Sharpe is undefined because sample volatility is zero.",
                )
            )
        if sortino is None:
            warnings.append(
                RiskWarning(
                    code="sortino_undefined",
                    message="Sortino is undefined because downside deviation is zero.",
                )
            )
        return RiskComputation(
            output=RiskKpiOutput(
                volatility=annualized_volatility(returns, annualization),
                max_drawdown=drawdown.max_drawdown,
                max_drawdown_duration_days=drawdown.max_duration,
                sharpe=sharpe,
                sortino=sortino,
            ),
            method="historical_twrr",
            warnings=tuple(warnings),
            risk_free=RiskFreeReference(
                annual_rate=params.risk_free_annual_rate,
                source="analytic_param",
                currency=context.target_currency,
            ),
        )
