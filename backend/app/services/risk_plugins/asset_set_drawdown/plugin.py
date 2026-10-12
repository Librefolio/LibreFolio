"""Dated drawdown episodes of each selected asset, over one shared window."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.risk import (
    RiskAssetSetDrawdownItem,
    RiskAssetSetDrawdownOutput,
    RiskDrawdownRecoveryStatus,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskScopeKind,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_scope_series,
    require_joint_baseline,
    require_joint_return_dates,
)
from backend.app.services.risk.base import RiskAnalytic, RiskComputation, RiskExecutionContext
from backend.app.services.risk.metrics import drawdown_episodes


class AssetSetDrawdownParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


@register_plugin(RiskAnalyticRegistry)
class AssetSetDrawdownAnalytic(RiskAnalytic):
    """How far each selected asset fell, for how long, and what it still owes.

    WHY THIS ANALYTIC DECIDES THE MODE FOR ITS WHOLE FAMILY. A drawdown is a
    property of a path: it asks what a series did between a peak and a trough,
    which is a question only history can answer. There is no reading of it over
    a hypothetical composition, and the singular analytic has always declared
    ``historical`` alone. Since one request carries one mode for every analytic
    in it, this constraint propagates: any surface wanting a drawdown column
    beside a risk/return point must ask for both on the historical wave. That is
    why the rest of this family is historical too — not a preference, an
    inherited fact.

    ``remaining_to_peak_ratio`` is the asymmetry that makes losses worth
    reporting separately from returns: recovering a 50% fall takes a 100% rise.
    It is published per asset because it is per asset; nothing here is summed.

    📌 THE WINDOW IS SHARED AND STATED ONCE. Every asset is measured from the
    same joint baseline to the same final date, so ``available_start`` and
    ``available_end`` sit on the output rather than on each row. Two assets whose
    drawdowns are compared here fell over the same days — which is the whole
    reason they can be put in one table.
    """

    analytic_code = "asset_set_drawdown"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.assetSetDrawdown.name"
    description_i18n_key = "risk.analytics.assetSetDrawdown.description"
    output_kind = RiskOutputKind.DRAWDOWN_SET
    supported_scopes = (RiskScopeKind.ASSET_SET,)
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = AssetSetDrawdownParams
    # Two, as the singular analytic declares: a drawdown needs only a peak and a
    # trough, where an annualized dispersion needs a sample. ⚠️ The family is
    # designed to travel in one request, so on a short window this analytic can
    # return OK while its four siblings return UNAVAILABLE for insufficient
    # history. That is correct per-analytic isolation rather than an
    # inconsistency — but a surface rendering the family has to handle the mix,
    # and lifting this to 20 to make the response uniform would refuse a figure
    # that is genuinely measurable.
    min_observations = 2

    def compute(self, params: AssetSetDrawdownParams, context: RiskExecutionContext) -> RiskComputation:
        del params
        baseline = require_joint_baseline(context)
        series = prepared_scope_series(context)
        prepared = context.prepared_series
        # Price-only by construction: a weightless scope has no TWRR curve, and
        # each row is one asset's own converted close series.
        calculation_basis = "price_only_close"

        items: list[RiskAssetSetDrawdownItem] = []
        for asset_id, dates, returns in series:
            report = drawdown_episodes(returns, dates=dates, baseline_date=baseline)
            items.append(
                RiskAssetSetDrawdownItem(
                    asset_id=asset_id,
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
                )
            )

        joint_dates = require_joint_return_dates(context)
        return RiskComputation(
            output=RiskAssetSetDrawdownOutput(
                available_start=joint_dates[0],
                available_end=joint_dates[-1],
                calculation_basis=calculation_basis,
                return_basis=RiskReturnBasis.PRICE_ONLY,
                items=items,
            ),
            method=calculation_basis,
            n_observations=prepared.n_observations if prepared else 0,
            calendar_days=prepared.calendar_days if prepared else 0,
            annualization_factor=prepared.annualization_factor if prepared else None,
            coverage=prepared.calendar_coverage if prepared else 0,
            return_basis=RiskReturnBasis.PRICE_ONLY,
        )
