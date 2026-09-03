"""Strict serializable contracts for stochastic simulation adapters."""

from __future__ import annotations

import hashlib
import json
import math
from typing import List

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, PositiveInt, model_validator

from backend.app.schemas.risk import RiskSamplingStrategy, RiskSimulationProcess

MAX_SOBOL_DIMENSION = 21_201


class SimulationEngineRequest(BaseModel):
    """Library-neutral GBM request safe to pass across a process boundary."""

    model_config = ConfigDict(extra="forbid")

    process: RiskSimulationProcess = RiskSimulationProcess.GBM
    sampling_method: RiskSamplingStrategy
    asset_ids: List[PositiveInt] = Field(..., min_length=1, max_length=100)
    annual_drifts: List[FiniteFloat] = Field(..., min_length=1)
    annual_covariance: List[List[FiniteFloat]] = Field(..., min_length=1)
    weights: List[FiniteFloat] = Field(..., min_length=1)
    cash_weight: FiniteFloat = Field(0.0, ge=0, le=1)
    horizon_days: int = Field(..., ge=1, le=3650)
    path_count: int = Field(..., ge=256, le=100_000)
    random_seed: int | None = Field(None, ge=0, le=2**32 - 1)
    sobol_start_index: int | None = Field(None, ge=0, le=2**32 - 1)
    diagnostics: bool = False

    @model_validator(mode="after")
    def validate_dimensions(self) -> SimulationEngineRequest:  # noqa: C901 — sequential field validation raises, no nested logic
        asset_count = len(self.asset_ids)
        if len(set(self.asset_ids)) != asset_count:
            raise ValueError("simulation asset_ids must be unique")
        if len(self.annual_drifts) != asset_count or len(self.weights) != asset_count or len(self.annual_covariance) != asset_count:
            raise ValueError("simulation vectors and covariance must match asset_ids")
        if any(len(row) != asset_count for row in self.annual_covariance):
            raise ValueError("simulation covariance must be square")
        if any(weight < 0 for weight in self.weights):
            raise ValueError("simulation weights must be non-negative")
        if not math.isclose(sum(self.weights) + self.cash_weight, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("simulation asset and cash weights must sum to one")
        for row_index, row in enumerate(self.annual_covariance):
            if row[row_index] < 0:
                raise ValueError("simulation covariance diagonal must be non-negative")
            for column_index, value in enumerate(row):
                if not math.isclose(value, self.annual_covariance[column_index][row_index], rel_tol=1e-10, abs_tol=1e-12):
                    raise ValueError("simulation covariance must be symmetric")
        if self.sampling_method == RiskSamplingStrategy.MC:
            if self.random_seed is None or self.sobol_start_index is not None:
                raise ValueError("MC simulation requires random_seed and forbids sobol_start_index")
        else:
            if self.sobol_start_index is None or self.random_seed is not None:
                raise ValueError("QMC simulation requires sobol_start_index and forbids random_seed")
            if self.path_count & (self.path_count - 1):
                raise ValueError("QMC paths must be a power of two")
            if asset_count * self.horizon_days > MAX_SOBOL_DIMENSION:
                raise ValueError(f"Sobol dimension exceeds the supported maximum of {MAX_SOBOL_DIMENSION}")
        return self


class SimulationEngineDiagnostics(BaseModel):
    """Optional benchmark-only stage timings from the child engine."""

    model_config = ConfigDict(extra="forbid")

    process_build_seconds: FiniteFloat = Field(..., ge=0)
    rng_seconds: FiniteFloat = Field(..., ge=0)
    process_evolution_seconds: FiniteFloat = Field(..., ge=0)
    generation_evolution_seconds: FiniteFloat = Field(..., ge=0)
    path_aggregation_seconds: FiniteFloat = Field(..., ge=0)
    result_aggregation_seconds: FiniteFloat = Field(..., ge=0)
    total_seconds: FiniteFloat = Field(..., ge=0)


class SimulationEngineResult(BaseModel):
    """Compact process-safe result returned by a simulation adapter."""

    model_config = ConfigDict(extra="forbid")

    percentile_levels: List[FiniteFloat] = Field(default_factory=lambda: [0.05, 0.5, 0.95], min_length=3, max_length=3)
    percentile_paths: List[List[FiniteFloat]] = Field(..., min_length=3, max_length=3)
    terminal_mean_return: FiniteFloat = Field(..., gt=-1)
    terminal_volatility: FiniteFloat = Field(..., ge=0)
    probability_of_loss: FiniteFloat = Field(..., ge=0, le=1)
    terminal_asset_log_means: List[FiniteFloat]
    terminal_asset_log_covariance: List[List[FiniteFloat]]
    diagnostics: SimulationEngineDiagnostics | None = None

    @model_validator(mode="after")
    def validate_percentiles(self) -> SimulationEngineResult:
        if self.percentile_levels != [0.05, 0.5, 0.95]:
            raise ValueError("simulation engine percentiles must be [0.05, 0.5, 0.95]")
        lengths = {len(path) for path in self.percentile_paths}
        if len(lengths) != 1 or not lengths or next(iter(lengths)) < 2:
            raise ValueError("simulation percentile paths must have one shared non-empty horizon")
        for p05, p50, p95 in zip(*self.percentile_paths, strict=True):
            if not p05 <= p50 <= p95:
                raise ValueError("simulation engine percentiles must be ordered")
        if any(not math.isclose(path[0], 0.0, rel_tol=0.0, abs_tol=1e-12) for path in self.percentile_paths):
            raise ValueError("simulation engine percentile paths must start at zero")
        asset_count = len(self.terminal_asset_log_means)
        if len(self.terminal_asset_log_covariance) != asset_count:
            raise ValueError("terminal covariance row count must match asset means")
        if any(len(row) != asset_count for row in self.terminal_asset_log_covariance):
            raise ValueError("terminal covariance must be square")
        return self


def simulation_cache_key(
    request: SimulationEngineRequest,
    *,
    algorithm_version: str,
) -> str:
    """Hash every input that can change the simulated distribution."""
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
    "MAX_SOBOL_DIMENSION",
    "SimulationEngineRequest",
    "SimulationEngineDiagnostics",
    "SimulationEngineResult",
    "simulation_cache_key",
]
