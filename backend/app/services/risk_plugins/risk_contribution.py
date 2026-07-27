"""Volatility contribution for the current portfolio composition."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.risk import (
    RiskContributionItem,
    RiskContributionOutput,
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_asset_returns,
    require_annualization_factor,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    covariance_matrix,
    risk_contributions_from_covariance,
)


class RiskContributionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(RiskAnalyticRegistry)
class RiskContributionAnalytic(RiskAnalytic):
    analytic_code = "risk_contribution"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.riskContribution.name"
    description_i18n_key = "risk.analytics.riskContribution.description"
    output_kind = RiskOutputKind.CONTRIBUTION
    supported_scopes = (RiskScopeKind.PORTFOLIO, RiskScopeKind.BROKER)
    supported_modes = (RiskMode.CURRENT_COMPOSITION,)
    params_model = RiskContributionParams
    min_observations = 20

    def compute(self, params, context):
        del params
        asset_ids = context.scope_asset_ids
        if any(asset_id not in context.weights for asset_id in asset_ids):
            raise RiskUnavailableError(
                "Current target-currency weights are unavailable",
                code=RiskErrorCode.DATA_UNAVAILABLE,
            )
        rows = [prepared_asset_returns(context, asset_id)[1] for asset_id in asset_ids]
        weights = [context.weights[asset_id] for asset_id in asset_ids]
        summary = risk_contributions_from_covariance(
            covariance_matrix(rows),
            weights,
            annualization_factor=require_annualization_factor(context),
        )
        return RiskComputation(
            output=RiskContributionOutput(
                portfolio_volatility=summary.portfolio_volatility,
                cash_weight=context.cash_weight,
                items=[
                    RiskContributionItem(
                        asset_id=asset_id,
                        weight=weight,
                        marginal_contribution=marginal,
                        component_contribution=component,
                        percentage_contribution=percentage,
                    )
                    for asset_id, weight, marginal, component, percentage in zip(
                        asset_ids,
                        weights,
                        summary.marginal,
                        summary.component,
                        summary.percentage,
                        strict=True,
                    )
                ],
            ),
            method="volatility_contribution",
            n_observations=context.prepared_series.n_observations if context.prepared_series else 0,
            calendar_days=context.prepared_series.calendar_days if context.prepared_series else 0,
            annualization_factor=context.prepared_series.annualization_factor if context.prepared_series else None,
            coverage=context.prepared_series.calendar_coverage if context.prepared_series else 0,
            return_basis=context.prepared_series.series[0].returns.return_basis if context.prepared_series and context.prepared_series.series else None,
        )
