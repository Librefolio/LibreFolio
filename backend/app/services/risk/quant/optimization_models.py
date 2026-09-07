"""Serializable Riskfolio worker contracts."""

from __future__ import annotations

import hashlib
import json
from typing import List

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from backend.app.schemas.risk import (
    RiskCovarianceEstimator,
    RiskOptimizationSolver,
    RiskOptimizationStrategy,
)


class OptimizationEngineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_ids: List[int] = Field(..., min_length=2, max_length=100)
    returns: List[List[FiniteFloat]] = Field(..., min_length=2)
    annualization_factor: FiniteFloat = Field(..., gt=0)
    strategy: RiskOptimizationStrategy
    covariance_estimator: RiskCovarianceEstimator
    risk_free_annual_rate: FiniteFloat = Field(0.0, gt=-1)
    min_weight: FiniteFloat = Field(0.0, ge=0, le=1)
    max_weight: FiniteFloat = Field(1.0, ge=0, le=1)
    include_frontier: bool = False
    frontier_points: int = Field(10, ge=3, le=50)
    include_sensitivity: bool = False
    solver: RiskOptimizationSolver = RiskOptimizationSolver.CLARABEL

    @model_validator(mode="after")
    def validate_matrix_and_constraints(self) -> OptimizationEngineRequest:
        asset_count = len(self.asset_ids)
        if len(set(self.asset_ids)) != asset_count:
            raise ValueError("optimization asset ids must be unique")
        if any(len(row) != asset_count for row in self.returns):
            raise ValueError("every return row must match the asset count")
        if self.min_weight > self.max_weight:
            raise ValueError("min_weight cannot exceed max_weight")
        if asset_count * self.min_weight > 1.0 + 1e-12:
            raise ValueError("minimum weights make the budget infeasible")
        if asset_count * self.max_weight < 1.0 - 1e-12:
            raise ValueError("maximum weights make the budget infeasible")
        return self


class OptimizationWeightResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    weight: FiniteFloat
    marginal_risk_contribution: FiniteFloat
    component_risk_contribution: FiniteFloat
    percentage_risk_contribution: FiniteFloat


class OptimizationFrontierPointResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    sharpe_ratio: FiniteFloat | None = None
    weights: List[OptimizationWeightResult]


class OptimizationSensitivityPointResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    covariance_estimator: RiskCovarianceEstimator
    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    max_absolute_weight_delta: FiniteFloat = Field(..., ge=0)
    weights: List[OptimizationWeightResult]


class OptimizationEngineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: RiskOptimizationStrategy
    covariance_estimator: RiskCovarianceEstimator
    solver: RiskOptimizationSolver
    solver_status: str
    expected_period_return: FiniteFloat
    expected_annual_return: FiniteFloat
    annual_volatility: FiniteFloat = Field(..., ge=0)
    sharpe_ratio: FiniteFloat | None = None
    weights: List[OptimizationWeightResult] = Field(..., min_length=2)
    frontier: List[OptimizationFrontierPointResult] = Field(default_factory=list)
    sensitivity: List[OptimizationSensitivityPointResult] = Field(default_factory=list)
    period_expected_returns: List[FiniteFloat]
    period_covariance: List[List[FiniteFloat]]
    algorithm_version: str

    @model_validator(mode="after")
    def validate_dimensions(self) -> OptimizationEngineResult:
        asset_count = len(self.weights)
        if len(self.period_expected_returns) != asset_count:
            raise ValueError("expected return count must match optimized weights")
        if len(self.period_covariance) != asset_count:
            raise ValueError("covariance row count must match optimized weights")
        if any(len(row) != asset_count for row in self.period_covariance):
            raise ValueError("optimization covariance must be square")
        return self


def optimization_cache_key(
    request: OptimizationEngineRequest,
    *,
    algorithm_version: str,
) -> str:
    """Hash every input that can change an optimization result."""
    payload = {
        "algorithm_version": algorithm_version,
        "request": request.model_dump(mode="json"),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "OptimizationEngineRequest",
    "OptimizationEngineResult",
    "OptimizationFrontierPointResult",
    "OptimizationSensitivityPointResult",
    "OptimizationWeightResult",
    "optimization_cache_key",
]
