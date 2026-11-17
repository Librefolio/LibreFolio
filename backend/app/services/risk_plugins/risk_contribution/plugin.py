"""Volatility contribution for the current portfolio composition."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.risk.outputs import RiskContributionItem, RiskContributionOutput
from backend.app.schemas.risk.vocabulary import RiskErrorCode, RiskMode, RiskOutputKind, RiskScopeKind
from backend.app.services.financial_math.weights import effective_number_of_positions
from backend.app.services.platform.data_quality_thresholds import RISK_MIN_OBSERVATIONS
from backend.app.services.platform.provider_registry import register_plugin
from backend.app.services.risk.acquired import diversification_ratio
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
from backend.app.services.risk.registry import RiskAnalyticRegistry


class RiskContributionParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _effective_number(weights: list[float]) -> float | None:
    """N_eff of the measured weights, through ``financial_math.weights`` (the one home of the formula)."""
    effective = effective_number_of_positions(dict(enumerate(Decimal(weight) for weight in weights)))
    return None if effective is None else float(effective)


@register_plugin(RiskAnalyticRegistry)
class RiskContributionAnalytic(RiskAnalytic):
    analytic_code = "risk_contribution"
    # 1.2.0 — the reported numbers are unchanged; the payload additionally carries
    # `excluded_weight`, so a client can tell a zero excluded weight apart from a server
    # that predates the field.
    # 1.3.0 (RN-15, developer's Q8 a, 16/11/2026) — N_eff is measured on the priced positions alone, their weights
    # renormalized on the measured part: cash is no longer in its denominator, and it never exceeds their count.
    algorithm_version = "1.3.0"
    name_i18n_key = "risk.analytics.riskContribution.name"
    description_i18n_key = "risk.analytics.riskContribution.description"
    output_kind = RiskOutputKind.CONTRIBUTION
    supported_scopes = (RiskScopeKind.PORTFOLIO,)
    supported_modes = (RiskMode.CURRENT_COMPOSITION,)
    params_model = RiskContributionParams
    min_observations = RISK_MIN_OBSERVATIONS

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
        annualization = require_annualization_factor(context)
        covariance = covariance_matrix(rows)
        summary = risk_contributions_from_covariance(
            covariance,
            weights,
            annualization_factor=annualization,
        )
        # Both sides of the ratio must sit at the same scale, and
        # risk_contributions_from_covariance annualizes internally, so the diagonal is
        # annualized here too. The ratio is invariant to that choice, but only when the
        # numerator and denominator agree on it.
        annualized_covariance = [[value * annualization for value in row] for row in covariance]
        # The contributions and the diversification ratio read the weights as the context supplies them (position value
        # over net worth; the ratio is scale-invariant anyway). N_eff does not (RN-15, developer's Q8 a): it is measured on
        # the priced positions alone, weighed on their own sum — the banner already says which assets are left out — so
        # cash and the unpriced holdings leave its denominator and it never exceeds the positions measured. AI Export's
        # Herfindahl index reads every position, priced or not: a different set, stated as such.
        return RiskComputation(
            output=RiskContributionOutput(
                portfolio_volatility=summary.portfolio_volatility,
                cash_weight=context.cash_weight,
                excluded_weight=context.excluded_weight,
                effective_number_of_assets=_effective_number(weights),
                diversification_ratio=diversification_ratio(
                    annualized_covariance,
                    weights,
                    portfolio_volatility=summary.portfolio_volatility,
                ),
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
