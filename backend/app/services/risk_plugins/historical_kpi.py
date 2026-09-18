"""Historical risk KPIs computed from the canonical primary return series."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskFreeReference,
    RiskKpiOutput,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.acquired import (
    conditional_drawdown_at_risk,
    drawdown_at_risk,
    ulcer_index,
    worst_realization,
    worst_realization_index,
)
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


class HistoricalKpiParams(BaseModel):
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
    drawdown_confidence_level: float = Field(
        0.95,
        gt=0,
        lt=1,
        json_schema_extra={
            # Reuses the existing translated key rather than introducing a new one:
            # this model has a single confidence parameter, so the label is unambiguous.
            "x-i18n-key": "risk.params.confidenceLevel",
            "x-control-order": 3,
            "x-step": 0.01,
        },
    )


@register_plugin(RiskAnalyticRegistry)
class HistoricalKpiAnalytic(RiskAnalytic):
    analytic_code = "historical_kpi"
    algorithm_version = "2.1.0"
    name_i18n_key = "risk.analytics.historicalKpi.name"
    description_i18n_key = "risk.analytics.historicalKpi.description"
    output_kind = RiskOutputKind.KPI
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
    )
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = HistoricalKpiParams
    min_observations = 20

    def compute(self, params, context):
        dates, returns = require_primary_returns(context)
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

        # The acquired measures reuse the underwater series summarize_drawdown already
        # produced, so none of them costs a second pass over the history.
        worst = worst_realization(returns)
        worst_date = dates[worst_realization_index(returns)]
        if worst > 0:
            # Every day in the window gained. RiskKpiOutput states realized losses as
            # non-positive, and reporting zero here would claim a loss that never
            # happened while pointing at a profitable date.
            worst = None
            worst_date = None
            warnings.append(
                RiskWarning(
                    code="worst_realization_undefined",
                    message="No losing observation in the selected window.",
                )
            )

        return RiskComputation(
            output=RiskKpiOutput(
                volatility=annualized_volatility(returns, annualization),
                max_drawdown=drawdown.max_drawdown,
                max_drawdown_duration_days=drawdown.max_duration,
                sharpe=sharpe,
                sortino=sortino,
                worst_realization=worst,
                worst_realization_date=worst_date,
                drawdown_confidence_level=params.drawdown_confidence_level,
                drawdown_at_risk=drawdown_at_risk(
                    drawdown.drawdowns,
                    confidence_level=params.drawdown_confidence_level,
                ),
                conditional_drawdown_at_risk=conditional_drawdown_at_risk(
                    drawdown.drawdowns,
                    confidence_level=params.drawdown_confidence_level,
                ),
                ulcer_index=ulcer_index(drawdown.drawdowns),
            ),
            method=("historical_twrr" if context.primary_return_basis == RiskReturnBasis.TWRR else "historical_close_returns"),
            warnings=tuple(warnings),
            risk_free=RiskFreeReference(
                annual_rate=params.risk_free_annual_rate,
                source="analytic_param",
                currency=context.target_currency,
            ),
        )
