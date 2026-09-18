"""Risk against expected return, one point per holding, for the composition held today."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.risk import (
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskReturnItem,
    RiskReturnOutput,
    RiskScopeKind,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_asset_returns,
    require_annualization_factor,
    require_primary_returns,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import (
    annualized_expected_return,
    annualized_volatility,
)


class AssetRiskReturnParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(RiskAnalyticRegistry)
class AssetRiskReturnAnalytic(RiskAnalytic):
    """Per-asset volatility and expected return, plus the portfolio's own pair.

    WHY THIS IS A PLUGIN OF ITS OWN and not two more columns on ``risk_contribution``.
    The two analytics consume the same prepared series and even the same covariance
    diagonal, so merging them would have been cheaper by a few lines. But a
    contribution payload answers "who produces the risk", and a payload carrying
    expected returns answers "who is paying for it" — a different question, read by a
    different level of the panel. Naming one after the other is how a contract starts
    meaning whatever its newest field needed.

    WHY ``current_composition`` ONLY. A per-asset point is a statement about the mix
    held *now*; the historical portfolio series has no composition to decompose — it is
    one TWRR curve. Offering this in ``historical`` would have to invent weights, and
    the invented ones would be today's, which is this mode by another name.

    ⚠️ THE RETURN IS ARITHMETIC, AND THAT IS THE WHOLE GEOMETRY. See
    ``metrics.annualized_expected_return``: paired with the annualized volatility it
    makes the slope from the risk-free intercept *identically* the Sharpe ratio, which
    is what licenses reading "above the line" as "better paid for the risk". It is the
    same convention the optimizer already uses, so an efficient frontier can one day be
    drawn on these axes without converting anything.
    """

    analytic_code = "asset_risk_return"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.assetRiskReturn.name"
    description_i18n_key = "risk.analytics.assetRiskReturn.description"
    output_kind = RiskOutputKind.RISK_RETURN
    supported_scopes = (RiskScopeKind.PORTFOLIO,)
    supported_modes = (RiskMode.CURRENT_COMPOSITION,)
    params_model = AssetRiskReturnParams
    min_observations = 20

    def compute(self, params, context):
        del params
        asset_ids = context.scope_asset_ids
        if any(asset_id not in context.weights for asset_id in asset_ids):
            raise RiskUnavailableError(
                "Current target-currency weights are unavailable",
                code=RiskErrorCode.DATA_UNAVAILABLE,
            )
        _dates, primary_returns = require_primary_returns(context)
        annualization = require_annualization_factor(context)

        items: list[RiskReturnItem] = []
        for asset_id in asset_ids:
            _asset_dates, returns = prepared_asset_returns(context, asset_id)
            if len(returns) < 2:
                # Volatility needs two observations. Dropping the point is the honest
                # outcome: a zero would place the asset on the vertical axis as if it
                # were riskless, which is a measurement nobody made.
                continue
            items.append(
                RiskReturnItem(
                    asset_id=asset_id,
                    weight=context.weights[asset_id],
                    volatility=annualized_volatility(returns, annualization),
                    expected_annual_return=annualized_expected_return(returns, annualization),
                )
            )

        return RiskComputation(
            output=RiskReturnOutput(
                # Measured on the primary series rather than summed from the items: the
                # buy-and-hold series lets weights drift over the window, so a weighted
                # average of the parts lands about 1% away from the whole. Both are
                # right about their own question; only one of them is the portfolio.
                portfolio_volatility=annualized_volatility(primary_returns, annualization),
                portfolio_expected_annual_return=annualized_expected_return(primary_returns, annualization),
                cash_weight=context.cash_weight,
                items=items,
            ),
            method="asset_risk_return_current_composition",
            n_observations=context.prepared_series.n_observations if context.prepared_series else 0,
            calendar_days=context.prepared_series.calendar_days if context.prepared_series else 0,
            annualization_factor=annualization,
            coverage=context.prepared_series.calendar_coverage if context.prepared_series else 0,
            return_basis=context.primary_return_basis,
        )
