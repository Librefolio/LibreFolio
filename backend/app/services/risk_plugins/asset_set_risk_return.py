"""Risk against expected return, one point per selected asset, with no whole to compare them to."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.risk import (
    RiskAssetSetReturnItem,
    RiskAssetSetReturnOutput,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_scope_series,
    require_annualization_factor,
)
from backend.app.services.risk.base import RiskAnalytic, RiskComputation, RiskExecutionContext
from backend.app.services.risk.metrics import (
    annualized_expected_return,
    annualized_volatility,
)


class AssetSetRiskReturnParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(RiskAnalyticRegistry)
class AssetSetRiskReturnAnalytic(RiskAnalytic):
    """Per-asset volatility and expected return for a selection with no composition.

    WHY THIS IS NOT ``asset_risk_return`` WITH A WIDER SCOPE ENUM. Capabilities
    are declared as two independent class-level tuples, and every consumer reads
    them as a cross product: a scope added here would be offered in every mode
    listed, and a mode added there would be offered in every scope. The singular
    analytic is ``portfolio`` x ``current_composition``, and this one has to be
    ``asset_set`` x ``historical``; expressed on one class those four pairs
    become a rectangle, two corners of which nobody intends. One of those corners
    is ``portfolio`` x ``historical``, where weights *do* exist in the context —
    so the analytic would not have failed, it would have returned numbers,
    per-asset points measured against a portfolio's own TWRR curve. A fabricated
    chart is worse than a missing one, and it would have been advertised by the
    catalogue rather than requested by anyone.

    Two codes make the rectangle a pair of points. Each declares one scope and
    one mode, so there is no combination either of them offers and neither of
    them has ever run.

    WHY ``historical`` AND NOT ``current_composition``. The name of the other
    mode describes the mix held today, and a selection has no mix — it has a
    selection. The decisive reason is narrower than the naming, though:
    ``asset_set_drawdown`` can only be historical, because a drawdown is a
    property of a path, and the reduced levels of a comparison page need it
    alongside these points. One request carries one mode, so any other choice
    here would have split the page across two requests — and two requests are
    two prepared sets, two joint calendars, and points that no longer sit on the
    same days.

    ⚠️ THE RETURN IS ARITHMETIC, AND THAT IS THE WHOLE GEOMETRY, exactly as in
    the singular analytic. See ``metrics.annualized_expected_return``: paired
    with the annualized volatility it makes the slope from a risk-free intercept
    identically the Sharpe ratio. The convention is kept here so the two payloads
    can never be read on axes that mean different things.

    📌 NO WEIGHTS ENTER ANY NUMBER, and that is a measurement rather than an
    intention: volatility and expected return are computed from one asset's own
    prepared series. In the singular analytic weights appear only in accessory
    positions — the bubble size, the portfolio point, the cash note — and this
    payload carries none of the three.
    """

    analytic_code = "asset_set_risk_return"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.assetSetRiskReturn.name"
    description_i18n_key = "risk.analytics.assetSetRiskReturn.description"
    output_kind = RiskOutputKind.RISK_RETURN_SET
    supported_scopes = (RiskScopeKind.ASSET_SET,)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = AssetSetRiskReturnParams
    min_observations = 20

    def compute(self, params: AssetSetRiskReturnParams, context: RiskExecutionContext) -> RiskComputation:
        del params
        annualization = require_annualization_factor(context)
        prepared = context.prepared_series
        items = [
            RiskAssetSetReturnItem(
                asset_id=asset_id,
                volatility=annualized_volatility(returns, annualization),
                expected_annual_return=annualized_expected_return(returns, annualization),
            )
            for asset_id, _dates, returns in prepared_scope_series(context)
        ]
        return RiskComputation(
            # No portfolio pair and no cash weight: RiskAssetSetReturnOutput has
            # no field for either, which is the point. See its docstring.
            output=RiskAssetSetReturnOutput(items=items),
            method="asset_set_risk_return_historical",
            n_observations=prepared.n_observations if prepared else 0,
            calendar_days=prepared.calendar_days if prepared else 0,
            annualization_factor=annualization,
            coverage=prepared.calendar_coverage if prepared else 0,
            return_basis=context.primary_return_basis,
        )
