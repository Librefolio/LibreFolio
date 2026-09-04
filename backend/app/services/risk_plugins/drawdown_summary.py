"""Dated current and maximum drawdown episodes from the primary return series."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.risk import (
    RiskDrawdownOutput,
    RiskDrawdownRecoveryStatus,
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskScopeKind,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import require_primary_returns
from backend.app.services.risk.base import RiskAnalytic, RiskComputation, RiskExecutionContext, RiskUnavailableError
from backend.app.services.risk.metrics import drawdown_episodes


class DrawdownSummaryParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(RiskAnalyticRegistry)
class DrawdownSummaryAnalytic(RiskAnalytic):
    analytic_code = "drawdown_summary"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.drawdownSummary.name"
    description_i18n_key = "risk.analytics.drawdownSummary.description"
    output_kind = RiskOutputKind.DRAWDOWN
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
    )
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = DrawdownSummaryParams
    min_observations = 2

    def compute(self, params: DrawdownSummaryParams, context: RiskExecutionContext) -> RiskComputation:
        dates, returns = require_primary_returns(context)
        baseline = context.primary_baseline_date
        if baseline is None or baseline >= dates[0]:
            raise RiskUnavailableError(
                "Primary return baseline is unavailable",
                code=RiskErrorCode.DATA_UNAVAILABLE,
            )
        report = drawdown_episodes(
            returns,
            dates=dates,
            baseline_date=baseline,
        )
        calculation_basis = "historical_twrr" if context.primary_return_basis == RiskReturnBasis.TWRR else "price_only_close"
        return RiskComputation(
            output=RiskDrawdownOutput(
                current_drawdown=report.current_drawdown,
                current_peak_date=report.current_peak_date,
                current_drawdown_duration_days=report.current_drawdown_duration_days,
                maximum_drawdown=report.maximum_drawdown,
                maximum_drawdown_peak_date=report.maximum_drawdown_peak_date,
                maximum_drawdown_trough_date=report.maximum_drawdown_trough_date,
                maximum_drawdown_recovery_status=RiskDrawdownRecoveryStatus(report.maximum_drawdown_recovery_status),
                maximum_drawdown_recovery_date=report.maximum_drawdown_recovery_date,
                maximum_drawdown_duration_days=report.maximum_drawdown_duration_days,
                maximum_drawdown_recovered_ratio=report.maximum_drawdown_recovered_ratio,
                remaining_to_peak_ratio=report.remaining_to_peak_ratio,
                available_start=report.available_start,
                available_end=report.available_end,
                n_observations=report.n_observations,
                coverage=max(0.0, min(1.0, context.coverage)),
                calculation_basis=calculation_basis,
                return_basis=context.primary_return_basis,
            ),
            method=calculation_basis,
            return_basis=context.primary_return_basis,
        )
