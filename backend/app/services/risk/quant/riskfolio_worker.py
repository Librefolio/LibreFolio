"""Riskfolio-Lib optimization executed only inside a spawn worker."""

from __future__ import annotations

import math
from importlib.metadata import version
from typing import Any

import cvxpy as cp
import numpy as np
import pandas as pd
import riskfolio as rp

from backend.app.schemas.risk import (
    RiskCovarianceEstimator,
    RiskOptimizationStrategy,
)
from backend.app.services.risk.quant.optimization_models import (
    OptimizationEngineRequest,
    OptimizationEngineResult,
    OptimizationFrontierPointResult,
    OptimizationSensitivityPointResult,
    OptimizationWeightResult,
)

ALGORITHM_VERSION = "riskfolio-lib-7.0.1-mv-v1"
_BOUND_TOLERANCE = 1e-6
_ESTIMATOR_METHODS = {
    RiskCovarianceEstimator.HISTORICAL: "hist",
    RiskCovarianceEstimator.LEDOIT_WOLF: "ledoit",
    RiskCovarianceEstimator.OAS: "oas",
}


class OptimizationInfeasibleError(ValueError):
    """Riskfolio returned no feasible solution."""


def _period_risk_free_rate(
    annual_rate: float,
    annualization_factor: float,
) -> float:
    return math.expm1(
        math.log1p(annual_rate) / annualization_factor,
    )


def _configure_portfolio(
    request: OptimizationEngineRequest,
    *,
    covariance_estimator: RiskCovarianceEstimator,
):
    columns = [str(asset_id) for asset_id in request.asset_ids]
    returns = pd.DataFrame(
        request.returns,
        columns=columns,
        dtype=float,
    )
    portfolio = rp.Portfolio(returns=returns)
    portfolio.assets_stats(
        method_mu="hist",
        method_cov=_ESTIMATOR_METHODS[covariance_estimator],
    )
    portfolio.sht = False
    portfolio.budget = 1
    portfolio.upperlng = float(request.max_weight)
    solver = request.solver.value.upper()
    if solver not in cp.installed_solvers():
        raise RuntimeError(
            f"requested solver '{solver}' is not installed",
        )
    portfolio.solvers = [solver]
    asset_count = len(request.asset_ids)
    portfolio.ainequality = np.vstack(
        [
            np.eye(asset_count),
            -np.eye(asset_count),
        ],
    )
    portfolio.binequality = np.concatenate(
        [
            np.full(asset_count, request.max_weight),
            np.full(asset_count, -request.min_weight),
        ],
    ).reshape(-1, 1)
    return portfolio


def _solve(
    request: OptimizationEngineRequest,
    *,
    covariance_estimator: RiskCovarianceEstimator,
):
    portfolio = _configure_portfolio(
        request,
        covariance_estimator=covariance_estimator,
    )
    risk_free = _period_risk_free_rate(
        request.risk_free_annual_rate,
        request.annualization_factor,
    )
    if request.strategy == RiskOptimizationStrategy.RISK_PARITY:
        solution = portfolio.rp_optimization(
            model="Classic",
            rm="MV",
            rf=0,
            b=None,
            hist=True,
        )
    else:
        objective = "MinRisk" if request.strategy == RiskOptimizationStrategy.MIN_RISK else "Sharpe"
        solution = portfolio.optimization(
            model="Classic",
            rm="MV",
            obj=objective,
            rf=(risk_free if request.strategy == RiskOptimizationStrategy.MAX_SHARPE else 0),
            l=0,
            hist=True,
        )
    if solution is None:
        raise OptimizationInfeasibleError(
            "Riskfolio returned no feasible weights",
        )
    weights = solution["weights"].reindex([str(asset_id) for asset_id in request.asset_ids]).to_numpy(dtype=float)
    if not np.isfinite(weights).all():
        raise FloatingPointError(
            "Riskfolio returned non-finite weights",
        )
    if not math.isclose(
        float(weights.sum()),
        1.0,
        rel_tol=0.0,
        abs_tol=_BOUND_TOLERANCE,
    ):
        raise RuntimeError(
            "Riskfolio weights do not satisfy the unit budget",
        )
    if np.min(weights) < request.min_weight - _BOUND_TOLERANCE or np.max(weights) > request.max_weight + _BOUND_TOLERANCE:
        raise RuntimeError(
            "Riskfolio weights violate requested bounds",
        )
    covariance = portfolio.cov.to_numpy(dtype=float)
    expected_returns = portfolio.mu.to_numpy(dtype=float).reshape(-1)
    covariance = (covariance + covariance.T) / 2.0
    minimum_eigenvalue = float(
        np.linalg.eigvalsh(covariance).min(),
    )
    if minimum_eigenvalue < -1e-10:
        raise RuntimeError(
            "Riskfolio covariance is not positive semidefinite",
        )
    return portfolio, weights, expected_returns, covariance


def _weight_results(
    asset_ids: list[int],
    weights: np.ndarray,
    covariance: np.ndarray,
) -> list[OptimizationWeightResult]:
    variance = float(weights @ covariance @ weights)
    if variance <= 0:
        raise RuntimeError(
            "optimized portfolio volatility is undefined",
        )
    volatility = math.sqrt(variance)
    marginal = covariance @ weights / volatility
    component = weights * marginal
    percentages = component / volatility
    return [
        OptimizationWeightResult(
            asset_id=asset_id,
            weight=float(weight),
            marginal_risk_contribution=float(marginal_value),
            component_risk_contribution=float(component_value),
            percentage_risk_contribution=float(percentage),
        )
        for (
            asset_id,
            weight,
            marginal_value,
            component_value,
            percentage,
        ) in zip(
            asset_ids,
            weights,
            marginal,
            component,
            percentages,
            strict=True,
        )
    ]


def _portfolio_metrics(
    request: OptimizationEngineRequest,
    weights: np.ndarray,
    expected_returns: np.ndarray,
    covariance: np.ndarray,
) -> tuple[float, float, float, float | None]:
    expected_period_return = float(expected_returns @ weights)
    period_variance = float(weights @ covariance @ weights)
    annual_volatility = math.sqrt(
        max(period_variance, 0.0) * request.annualization_factor,
    )
    expected_annual_return = expected_period_return * request.annualization_factor
    sharpe = None
    if request.strategy == RiskOptimizationStrategy.MAX_SHARPE:
        risk_free = _period_risk_free_rate(
            request.risk_free_annual_rate,
            request.annualization_factor,
        )
        period_volatility = math.sqrt(
            max(period_variance, 0.0),
        )
        if period_volatility > 0:
            sharpe = (expected_period_return - risk_free) / period_volatility * math.sqrt(request.annualization_factor)
    return (
        expected_period_return,
        expected_annual_return,
        annual_volatility,
        sharpe,
    )


def _frontier(
    request: OptimizationEngineRequest,
    portfolio,
    expected_returns: np.ndarray,
    covariance: np.ndarray,
) -> list[OptimizationFrontierPointResult]:
    if not request.include_frontier:
        return []
    result = portfolio.efficient_frontier(
        model="Classic",
        rm="MV",
        points=request.frontier_points,
        rf=0,
        solver=request.solver.value.upper(),
        hist=True,
    )
    if result is None:
        raise OptimizationInfeasibleError(
            "Riskfolio returned no efficient frontier",
        )
    points = []
    for column in result.columns:
        weights = (
            result[column]
            .reindex(
                [str(asset_id) for asset_id in request.asset_ids],
            )
            .to_numpy(dtype=float)
        )
        (
            _period_return,
            annual_return,
            annual_volatility,
            sharpe,
        ) = _portfolio_metrics(
            request,
            weights,
            expected_returns,
            covariance,
        )
        points.append(
            OptimizationFrontierPointResult(
                expected_annual_return=annual_return,
                annual_volatility=annual_volatility,
                sharpe_ratio=sharpe,
                weights=_weight_results(
                    request.asset_ids,
                    weights,
                    covariance,
                ),
            ),
        )
    return sorted(
        points,
        key=lambda point: point.annual_volatility,
    )


def _sensitivity(
    request: OptimizationEngineRequest,
    base_weights: np.ndarray,
) -> list[OptimizationSensitivityPointResult]:
    if not request.include_sensitivity:
        return []
    points = []
    for estimator in RiskCovarianceEstimator:
        if estimator == request.covariance_estimator:
            continue
        (
            _portfolio,
            weights,
            expected_returns,
            covariance,
        ) = _solve(
            request,
            covariance_estimator=estimator,
        )
        (
            _period_return,
            annual_return,
            annual_volatility,
            _sharpe,
        ) = _portfolio_metrics(
            request,
            weights,
            expected_returns,
            covariance,
        )
        points.append(
            OptimizationSensitivityPointResult(
                covariance_estimator=estimator,
                expected_annual_return=annual_return,
                annual_volatility=annual_volatility,
                max_absolute_weight_delta=float(
                    np.max(np.abs(weights - base_weights)),
                ),
                weights=_weight_results(
                    request.asset_ids,
                    weights,
                    covariance,
                ),
            ),
        )
    return points


def execute_optimization_job(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Run one deterministic long-only Riskfolio optimization."""
    if version("riskfolio-lib") != "7.0.1":
        raise RuntimeError(
            "portfolio optimization requires Riskfolio-Lib 7.0.1",
        )
    request = OptimizationEngineRequest.model_validate(payload)
    (
        portfolio,
        weights,
        expected_returns,
        covariance,
    ) = _solve(
        request,
        covariance_estimator=request.covariance_estimator,
    )
    (
        expected_period_return,
        expected_annual_return,
        annual_volatility,
        sharpe,
    ) = _portfolio_metrics(
        request,
        weights,
        expected_returns,
        covariance,
    )
    result = OptimizationEngineResult(
        strategy=request.strategy,
        covariance_estimator=request.covariance_estimator,
        solver=request.solver,
        solver_status="solution_returned",
        expected_period_return=expected_period_return,
        expected_annual_return=expected_annual_return,
        annual_volatility=annual_volatility,
        sharpe_ratio=sharpe,
        weights=_weight_results(
            request.asset_ids,
            weights,
            covariance,
        ),
        frontier=_frontier(
            request,
            portfolio,
            expected_returns,
            covariance,
        ),
        sensitivity=_sensitivity(request, weights),
        period_expected_returns=expected_returns.tolist(),
        period_covariance=covariance.tolist(),
        algorithm_version=ALGORITHM_VERSION,
    )
    return result.model_dump(mode="json")


__all__ = [
    "ALGORITHM_VERSION",
    "OptimizationInfeasibleError",
    "execute_optimization_job",
]
