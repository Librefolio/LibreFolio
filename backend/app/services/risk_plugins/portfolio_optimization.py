"""Long-only historical portfolio optimization through Riskfolio-Lib."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.risk import (
    RiskCovarianceEstimator,
    RiskErrorCode,
    RiskFreeReference,
    RiskMode,
    RiskOptimizationConstraintSummary,
    RiskOptimizationFrontierPoint,
    RiskOptimizationSensitivityPoint,
    RiskOptimizationSolver,
    RiskOptimizationStrategy,
    RiskOptimizationWeight,
    RiskOutputKind,
    RiskPortfolioOptimizationOutput,
    RiskReturnBasis,
    RiskScopeKind,
)
from backend.app.services.provider_registry import (
    RiskAnalyticRegistry,
    register_plugin,
)
from backend.app.services.risk.base import (
    RiskAnalytic,
    RiskComputation,
    RiskUnavailableError,
)
from backend.app.services.risk.quant.optimization_engine import (
    OptimizationResourceLimitError,
    run_optimization,
)
from backend.app.services.risk.quant.optimization_models import (
    OptimizationEngineRequest,
    OptimizationWeightResult,
)
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerQueueFullError,
    SpawnWorkerRemoteError,
    SpawnWorkerTimeoutError,
)


class PortfolioOptimizationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: RiskOptimizationStrategy = Field(
        RiskOptimizationStrategy.MIN_RISK,
        json_schema_extra={
            "x-i18n-key": "risk.params.optimizationStrategy",
            "x-control-order": 1,
        },
    )
    covariance_estimator: RiskCovarianceEstimator = Field(
        RiskCovarianceEstimator.HISTORICAL,
        json_schema_extra={
            "x-i18n-key": "risk.params.covarianceEstimator",
            "x-control-order": 2,
        },
    )
    risk_free_annual_rate: float = Field(
        0.0,
        gt=-1,
        le=1,
        json_schema_extra={
            "x-i18n-key": "risk.params.riskFreeRate",
            "x-control-order": 3,
            "x-step": 0.001,
        },
    )
    min_weight: float = Field(
        0.0,
        ge=0,
        le=1,
        json_schema_extra={
            "x-i18n-key": "risk.params.minWeight",
            "x-control-order": 4,
            "x-step": 0.01,
        },
    )
    max_weight: float = Field(
        1.0,
        ge=0,
        le=1,
        json_schema_extra={
            "x-i18n-key": "risk.params.maxWeight",
            "x-control-order": 5,
            "x-step": 0.01,
        },
    )
    include_frontier: bool = Field(
        False,
        json_schema_extra={
            "x-i18n-key": "risk.params.includeFrontier",
            "x-control-order": 6,
        },
    )
    frontier_points: int = Field(
        10,
        ge=3,
        le=50,
        json_schema_extra={
            "x-i18n-key": "risk.params.frontierPoints",
            "x-control-order": 7,
            "x-step": 1,
        },
    )
    include_sensitivity: bool = Field(
        False,
        json_schema_extra={
            "x-i18n-key": "risk.params.includeSensitivity",
            "x-control-order": 8,
        },
    )
    solver: RiskOptimizationSolver = Field(
        RiskOptimizationSolver.CLARABEL,
        json_schema_extra={
            "x-i18n-key": "risk.params.optimizationSolver",
            "x-control-order": 9,
        },
    )


def _api_weight(
    item: OptimizationWeightResult,
) -> RiskOptimizationWeight:
    return RiskOptimizationWeight(
        asset_id=item.asset_id,
        weight=item.weight,
        marginal_risk_contribution=(item.marginal_risk_contribution),
        component_risk_contribution=(item.component_risk_contribution),
        percentage_risk_contribution=(item.percentage_risk_contribution),
    )


@register_plugin(RiskAnalyticRegistry)
class PortfolioOptimizationAnalytic(RiskAnalytic):
    analytic_code = "portfolio_optimization"
    algorithm_version = "1.0.0-riskfolio-7.0.1"
    name_i18n_key = "risk.analytics.portfolioOptimization.name"
    description_i18n_key = "risk.analytics.portfolioOptimization.description"
    output_kind = RiskOutputKind.OPTIMIZATION
    supported_scopes = (
        RiskScopeKind.ASSET_SET,
        RiskScopeKind.PORTFOLIO,
    )
    supported_modes = (RiskMode.HISTORICAL,)
    params_model = PortfolioOptimizationParams
    min_observations = 30

    async def execute(self, params, context):
        prepared = context.prepared_series
        if prepared is None or context.annualization_factor is None:
            raise RiskUnavailableError(
                "Optimization requires aligned historical returns",
                code=RiskErrorCode.DATA_UNAVAILABLE,
            )
        asset_ids = context.scope_asset_ids
        if len(asset_ids) < 2:
            raise RiskUnavailableError(
                "Optimization requires at least two usable assets",
                code=RiskErrorCode.INSUFFICIENT_HISTORY,
            )
        prepared_by_asset = {item.returns.asset_id: item.returns for item in prepared.series}
        return_columns = [[float(point.value) for point in prepared_by_asset[asset_id].points] for asset_id in asset_ids]
        returns = [list(row) for row in zip(*return_columns, strict=True)]
        try:
            request = OptimizationEngineRequest(
                asset_ids=asset_ids,
                returns=returns,
                annualization_factor=(context.annualization_factor),
                strategy=params.strategy,
                covariance_estimator=(params.covariance_estimator),
                risk_free_annual_rate=(params.risk_free_annual_rate),
                min_weight=params.min_weight,
                max_weight=params.max_weight,
                include_frontier=params.include_frontier,
                frontier_points=params.frontier_points,
                include_sensitivity=params.include_sensitivity,
                solver=params.solver,
            )
            result, _cache_hit, _worker_result = await run_optimization(
                request,
                algorithm_version=(f"{self.analytic_code}@" f"{self.algorithm_version}"),
            )
        except OptimizationResourceLimitError as exc:
            raise RiskUnavailableError(
                str(exc),
                code=RiskErrorCode.RESOURCE_LIMIT,
                details={
                    "actual": exc.actual,
                    "limit": exc.limit,
                },
            ) from exc
        except SpawnWorkerQueueFullError as exc:
            raise RiskUnavailableError(
                str(exc),
                code=RiskErrorCode.WORKER_BUSY,
            ) from exc
        except SpawnWorkerTimeoutError as exc:
            raise RiskUnavailableError(
                str(exc),
                code=RiskErrorCode.EXECUTION_TIMEOUT,
            ) from exc
        except SpawnWorkerRemoteError as exc:
            code = (
                RiskErrorCode.OPTIMIZATION_INFEASIBLE
                if exc.remote_type.endswith(
                    "OptimizationInfeasibleError",
                )
                else RiskErrorCode.EXECUTION_FAILED
            )
            raise RiskUnavailableError(
                str(exc),
                code=code,
                details={"remote_type": exc.remote_type},
            ) from exc
        except ValueError as exc:
            raise RiskUnavailableError(
                str(exc),
                code=RiskErrorCode.INVALID_PARAMETERS,
            ) from exc

        return RiskComputation(
            output=RiskPortfolioOptimizationOutput(
                strategy=result.strategy,
                covariance_estimator=(result.covariance_estimator),
                solver=result.solver,
                solver_status=result.solver_status,
                risk_free_annual_rate=(params.risk_free_annual_rate if params.strategy == RiskOptimizationStrategy.MAX_SHARPE else None),
                expected_period_return=(result.expected_period_return),
                expected_annual_return=(result.expected_annual_return),
                annual_volatility=result.annual_volatility,
                sharpe_ratio=result.sharpe_ratio,
                weights=[_api_weight(item) for item in result.weights],
                constraints=RiskOptimizationConstraintSummary(
                    min_weight=params.min_weight,
                    max_weight=params.max_weight,
                ),
                frontier=[
                    RiskOptimizationFrontierPoint(
                        expected_annual_return=(point.expected_annual_return),
                        annual_volatility=(point.annual_volatility),
                        sharpe_ratio=point.sharpe_ratio,
                        weights=[_api_weight(item) for item in point.weights],
                    )
                    for point in result.frontier
                ],
                sensitivity=[
                    RiskOptimizationSensitivityPoint(
                        covariance_estimator=(point.covariance_estimator),
                        expected_annual_return=(point.expected_annual_return),
                        annual_volatility=(point.annual_volatility),
                        max_absolute_weight_delta=(point.max_absolute_weight_delta),
                        weights=[_api_weight(item) for item in point.weights],
                    )
                    for point in result.sensitivity
                ],
                method=("riskfolio_classic_mean_variance_" "long_only_fully_invested"),
                algorithm_version=result.algorithm_version,
            ),
            method=("riskfolio_classic_mean_variance_" "long_only_fully_invested"),
            n_observations=len(returns),
            calendar_days=prepared.calendar_days,
            annualization_factor=prepared.annualization_factor,
            coverage=prepared.calendar_coverage,
            return_basis=RiskReturnBasis.PRICE_ONLY,
            risk_free=(
                RiskFreeReference(
                    annual_rate=params.risk_free_annual_rate,
                    source="request",
                    currency=context.target_currency,
                )
                if params.strategy == RiskOptimizationStrategy.MAX_SHARPE
                else None
            ),
        )
