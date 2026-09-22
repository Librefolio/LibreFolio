"""Historical risk KPIs of each selected asset, measured on one shared calendar."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskAssetSetKpiItem,
    RiskAssetSetKpiOutput,
    RiskFreeReference,
    RiskMode,
    RiskOutputKind,
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
    joint_elapsed_calendar_days,
    prepared_scope_series,
    require_annualization_factor,
)
from backend.app.services.risk.base import RiskAnalytic, RiskComputation, RiskExecutionContext
from backend.app.services.risk.metrics import (
    annualized_sharpe,
    annualized_sortino,
    annualized_volatility,
    summarize_drawdown,
)


class AssetSetKpiParams(BaseModel):
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
            "x-i18n-key": "risk.params.confidenceLevel",
            "x-control-order": 3,
            "x-step": 0.01,
        },
    )


@register_plugin(RiskAnalyticRegistry)
class AssetSetKpiAnalytic(RiskAnalytic):
    """Volatility, drawdown, Sharpe and Sortino of every selected asset.

    THE SET IS NEVER SUMMARIZED. ``historical_kpi`` reduces one series to one row
    because a portfolio has an aggregate curve; a selection of assets does not,
    and inventing one would require weights — at which point it is a portfolio
    and belongs on the surface that governs portfolios. So this analytic answers
    *n* questions rather than one, and publishes *n* rows.

    WHY THE ROWS ARE COMPARABLE, which is the only reason to put them in one
    payload. They are measured on one prepared set, so they share a joint
    calendar and an observation count. That is a property of the *request*, not
    of this code: the service prepares the series once, before it dispatches any
    analytic. Asking for these figures one asset at a time would have produced a
    different joint calendar per call, and the resulting rows would have looked
    like a table while being *n* unrelated measurements.

    ⚠️ EVERY OMISSION IS DECLARED, NEVER ZERO-FILLED. A Sharpe is ``None`` when
    sample volatility is zero and a Sortino is ``None`` when downside deviation
    is, each with its own warning naming the asset — because a zero in either
    position reads as "measured, and it is nil" rather than "undefined". The same
    rule governs ``worst_realization``: a window in which every observation
    gained has no worst loss, and reporting ``0`` there would claim a loss that
    never happened.
    """

    analytic_code = "asset_set_kpi"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.assetSetKpi.name"
    description_i18n_key = "risk.analytics.assetSetKpi.description"
    output_kind = RiskOutputKind.KPI_SET
    supported_scopes = (RiskScopeKind.ASSET_SET,)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = AssetSetKpiParams
    min_observations = 20

    def compute(self, params: AssetSetKpiParams, context: RiskExecutionContext) -> RiskComputation:
        annualization = require_annualization_factor(context)
        elapsed_units = joint_elapsed_calendar_days(context)
        prepared = context.prepared_series
        warnings: list[RiskWarning] = []
        undefined_sharpe: list[int] = []
        undefined_sortino: list[int] = []
        no_losing_observation: list[int] = []
        items: list[RiskAssetSetKpiItem] = []

        for asset_id, dates, returns in prepared_scope_series(context):
            drawdown = summarize_drawdown(returns, elapsed_units=elapsed_units)
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
            if sharpe is None:
                undefined_sharpe.append(asset_id)
            if sortino is None:
                undefined_sortino.append(asset_id)

            worst = worst_realization(returns)
            worst_date = dates[worst_realization_index(returns)]
            if worst > 0:
                worst = None
                worst_date = None
                no_losing_observation.append(asset_id)

            items.append(
                RiskAssetSetKpiItem(
                    asset_id=asset_id,
                    volatility=annualized_volatility(returns, annualization),
                    max_drawdown=drawdown.max_drawdown,
                    max_drawdown_duration_days=drawdown.max_duration,
                    sharpe=sharpe,
                    sortino=sortino,
                    worst_realization=worst,
                    worst_realization_date=worst_date,
                    drawdown_at_risk=drawdown_at_risk(
                        drawdown.drawdowns,
                        confidence_level=params.drawdown_confidence_level,
                    ),
                    conditional_drawdown_at_risk=conditional_drawdown_at_risk(
                        drawdown.drawdowns,
                        confidence_level=params.drawdown_confidence_level,
                    ),
                    ulcer_index=ulcer_index(drawdown.drawdowns),
                )
            )

        # One warning per condition naming the assets, rather than one warning per
        # asset: a selection of eighty would otherwise bury the panel in notices
        # that all say the same thing.
        if undefined_sharpe:
            warnings.append(
                RiskWarning(
                    code="sharpe_undefined",
                    message="Sharpe is undefined for one or more assets because sample volatility is zero.",
                    details={"asset_ids": undefined_sharpe},
                )
            )
        if undefined_sortino:
            warnings.append(
                RiskWarning(
                    code="sortino_undefined",
                    message="Sortino is undefined for one or more assets because downside deviation is zero.",
                    details={"asset_ids": undefined_sortino},
                )
            )
        if no_losing_observation:
            warnings.append(
                RiskWarning(
                    code="worst_realization_undefined",
                    message="One or more assets had no losing observation in the selected window.",
                    details={"asset_ids": no_losing_observation},
                )
            )

        return RiskComputation(
            output=RiskAssetSetKpiOutput(
                drawdown_confidence_level=params.drawdown_confidence_level,
                items=items,
            ),
            method="asset_set_close_returns",
            warnings=tuple(warnings),
            risk_free=RiskFreeReference(
                annual_rate=params.risk_free_annual_rate,
                source="analytic_param",
                currency=context.target_currency,
            ),
            n_observations=prepared.n_observations if prepared else 0,
            calendar_days=prepared.calendar_days if prepared else 0,
            annualization_factor=annualization,
            coverage=prepared.calendar_coverage if prepared else 0,
            return_basis=context.primary_return_basis,
        )
