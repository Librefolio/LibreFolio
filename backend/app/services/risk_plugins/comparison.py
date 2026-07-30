"""Relative performance against a real comparison asset."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskComparisonOutput,
    RiskComparisonPoint,
    RiskErrorCode,
    RiskMode,
    RiskOutputKind,
    RiskReturnBasis,
    RiskScopeKind,
    RiskWarning,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import (
    prepared_asset_return_points,
    prepared_asset_returns,
    require_annualization_factor,
    require_primary_returns,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.metrics import comparison_summary


class ComparisonParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comparison_asset_id: int = Field(
        ge=1,
        json_schema_extra={
            "x-control": "comparison_asset",
            "x-i18n-key": "chartSettings.params.comparisonAsset",
            "x-control-order": 1,
        },
    )


@register_plugin(RiskAnalyticRegistry)
class ComparisonAnalytic(RiskAnalytic):
    analytic_code = "comparison"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.comparison.name"
    description_i18n_key = "risk.analytics.comparison.description"
    output_kind = RiskOutputKind.COMPARISON
    supported_scopes = (
        RiskScopeKind.ASSET,
        RiskScopeKind.PORTFOLIO,
    )
    supported_modes = (RiskMode.HISTORICAL, RiskMode.CURRENT_COMPOSITION)
    params_model = ComparisonParams
    min_observations = 20

    def compute(self, params, context):
        primary_dates, primary_returns = require_primary_returns(context)
        comparison_dates, comparison_returns = prepared_asset_returns(
            context,
            params.comparison_asset_id,
        )
        primary_map = dict(zip(primary_dates, primary_returns, strict=True))
        comparison_map = dict(zip(comparison_dates, comparison_returns, strict=True))
        common_dates = tuple(sorted(set(primary_map) & set(comparison_map)))
        if len(common_dates) < self.min_observations:
            raise RiskUnavailableError(
                "Comparison has insufficient common observations",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
                details={
                    "observations": len(common_dates),
                    "required": self.min_observations,
                },
            )
        comparison_points = {
            point_date: previous_date
            for point_date, previous_date, _value in prepared_asset_return_points(
                context,
                params.comparison_asset_id,
            )
        }
        baseline_date = comparison_points[common_dates[0]]
        calendar_days = (common_dates[-1] - baseline_date).days
        annualization_factor = len(common_dates) * 365 / calendar_days if calendar_days > 0 else require_annualization_factor(context)
        summary = comparison_summary(
            [primary_map[point_date] for point_date in common_dates],
            [comparison_map[point_date] for point_date in common_dates],
            annualization_factor,
        )
        warnings: list[RiskWarning] = []
        if summary.beta is None:
            warnings.append(
                RiskWarning(
                    code="comparison_beta_undefined",
                    message="Beta is undefined because the comparison asset has zero variance.",
                )
            )
        if summary.correlation is None:
            warnings.append(
                RiskWarning(
                    code="comparison_correlation_undefined",
                    message="Correlation is undefined because at least one series has zero variance.",
                )
            )
        return RiskComputation(
            output=RiskComparisonOutput(
                comparison_asset_id=params.comparison_asset_id,
                active_return=summary.active_return,
                tracking_error=summary.tracking_error,
                information_ratio=summary.information_ratio,
                correlation=summary.correlation,
                beta=summary.beta,
                observations=len(common_dates),
                series=[
                    RiskComparisonPoint(
                        date=point_date,
                        primary_cumulative_return=primary_cumulative,
                        comparison_cumulative_return=comparison_cumulative,
                        primary_drawdown=primary_drawdown,
                        comparison_drawdown=comparison_drawdown,
                    )
                    for point_date, primary_cumulative, comparison_cumulative, primary_drawdown, comparison_drawdown in zip(
                        common_dates,
                        summary.primary_cumulative,
                        summary.comparison_cumulative,
                        summary.primary_drawdowns,
                        summary.comparison_drawdowns,
                        strict=True,
                    )
                ],
            ),
            method="comparison_asset",
            warnings=tuple(warnings),
            comparison_asset_id=params.comparison_asset_id,
            n_observations=len(common_dates),
            calendar_days=calendar_days,
            annualization_factor=annualization_factor,
            coverage=len(common_dates) / len(primary_dates) if primary_dates else 0,
            return_basis=RiskReturnBasis.PRICE_ONLY if context.scope_kind == RiskScopeKind.ASSET else context.primary_return_basis,
        )
