"""Pearson correlation matrix on canonical post-FX returns."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskCorrelationOutput,
    RiskMatrixCell,
    RiskMode,
    RiskOutputKind,
    RiskScopeKind,
    RiskValueStatus,
    RiskWarning,
)
from backend.app.services.provider_registry import RiskAnalyticRegistry, register_plugin
from backend.app.services.risk.analytic_helpers import prepared_asset_returns
from backend.app.services.risk.base import RiskAnalytic, RiskComputation
from backend.app.services.risk.metrics import pairwise_correlation


class CorrelationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_observations: int = Field(
        20,
        ge=2,
        le=5000,
        json_schema_extra={
            "x-i18n-key": "risk.params.minObservations",
            "x-control-order": 1,
            "x-step": 1,
        },
    )
    min_coverage: float = Field(
        0.6,
        ge=0,
        le=1,
        json_schema_extra={
            "x-i18n-key": "risk.params.minCoverage",
            "x-control-order": 2,
            "x-step": 0.05,
        },
    )


@register_plugin(RiskAnalyticRegistry)
class CorrelationAnalytic(RiskAnalytic):
    analytic_code = "correlation"
    algorithm_version = "1.0.0"
    name_i18n_key = "risk.analytics.correlation.name"
    description_i18n_key = "risk.analytics.correlation.description"
    output_kind = RiskOutputKind.MATRIX
    supported_scopes = (
        RiskScopeKind.ASSET_SET,
        RiskScopeKind.PORTFOLIO,
        RiskScopeKind.BROKER,
    )
    supported_modes = (RiskMode.HISTORICAL, RiskMode.CURRENT_COMPOSITION)
    params_model = CorrelationParams
    min_observations = 2

    def compute(self, params, context):
        asset_ids = context.scope_asset_ids
        series = {asset_id: prepared_asset_returns(context, asset_id)[1] for asset_id in asset_ids}
        expected = context.prepared_series.n_observations if context.prepared_series else 0
        cells: list[RiskMatrixCell] = []
        insufficient = False
        undefined = False
        low_coverage = False
        for row_asset_id in asset_ids:
            for column_asset_id in asset_ids:
                value, observations, coverage = pairwise_correlation(
                    series[row_asset_id],
                    series[column_asset_id],
                    expected_observations=expected,
                )
                if observations < params.min_observations:
                    status = RiskValueStatus.INSUFFICIENT
                    value = None
                    insufficient = True
                elif value is None:
                    status = RiskValueStatus.UNDEFINED
                    undefined = True
                else:
                    status = RiskValueStatus.OK
                low_coverage = low_coverage or coverage < params.min_coverage
                cells.append(
                    RiskMatrixCell(
                        row_asset_id=row_asset_id,
                        column_asset_id=column_asset_id,
                        value=value,
                        observations=observations,
                        coverage=coverage,
                        status=status,
                    )
                )

        warnings: list[RiskWarning] = []
        if insufficient:
            warnings.append(
                RiskWarning(
                    code="insufficient_pair_history",
                    message="One or more correlation cells have insufficient common observations.",
                    details={"min_observations": params.min_observations},
                )
            )
        if undefined:
            warnings.append(
                RiskWarning(
                    code="flat_series",
                    message="One or more correlation cells are undefined because a series has zero variance.",
                )
            )
        if low_coverage:
            warnings.append(
                RiskWarning(
                    code="low_pair_coverage",
                    message="One or more correlation cells are below the requested coverage threshold.",
                    details={"min_coverage": params.min_coverage},
                )
            )
        return RiskComputation(
            output=RiskCorrelationOutput(
                asset_ids=list(asset_ids),
                cells=cells,
            ),
            method="pearson_post_fx",
            warnings=tuple(warnings),
            n_observations=context.prepared_series.n_observations if context.prepared_series else 0,
            calendar_days=context.prepared_series.calendar_days if context.prepared_series else 0,
            annualization_factor=context.prepared_series.annualization_factor if context.prepared_series else None,
            coverage=context.prepared_series.calendar_coverage if context.prepared_series else 0,
            return_basis=context.prepared_series.series[0].returns.return_basis if context.prepared_series and context.prepared_series.series else None,
        )
