"""Strict serializable contracts for stochastic simulation adapters."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from typing import List

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, PositiveInt, model_validator

from backend.app.schemas.risk import (
    RiskSamplingStrategy,
    RiskSimulationProcess,
    RiskSimulationRegime,
)

MAX_SOBOL_DIMENSION = 21_201
MAX_HISTORY_OBSERVATIONS = 5_000


def historical_returns_digest(matrix: Sequence[Sequence[float]]) -> str:
    """Hash a return matrix by its raw bytes instead of its serialization.

    Serializing a 100x2500 matrix to JSON costs ~99 ms; hashing its buffer
    costs ~0.9 ms. The cache key must not be more expensive than the cache
    lookup it guards, because even a *hit* pays that price.
    """
    array = np.ascontiguousarray(np.asarray(matrix, dtype=np.float64))
    hasher = hashlib.sha256()
    hasher.update(repr(array.shape).encode("ascii"))
    hasher.update(array.tobytes())
    return hasher.hexdigest()


class SimulationEngineRequest(BaseModel):
    """Library-neutral simulation request safe to pass across a process boundary.

    Two mutually exclusive contracts share this model:

    * ``gbm`` carries *estimated parameters* — annual drifts and an annual
      covariance matrix — and is evolved by QuantLib.
    * ``block_bootstrap`` carries the *aligned historical return matrix* and
      estimates nothing. It cannot even express a covariance: the fields are
      rejected by validation, which is what makes an ill-conditioned
      covariance structurally unreachable in that mode.

    ``process`` is deliberately **required**. The two contracts carry different
    data, so a default would let one shape be built by accident and silently
    evolved under the other's physics. Both production call sites declare it;
    the field exists to make a construction without it fail loudly.
    """

    model_config = ConfigDict(extra="forbid")

    process: RiskSimulationProcess
    regime: RiskSimulationRegime = RiskSimulationRegime.NONE
    sampling_method: RiskSamplingStrategy
    asset_ids: List[PositiveInt] = Field(..., min_length=1, max_length=100)
    annual_drifts: List[FiniteFloat] | None = Field(None, min_length=1)
    annual_covariance: List[List[FiniteFloat]] | None = Field(None, min_length=1)
    historical_returns: List[List[FiniteFloat]] | None = Field(None, min_length=2, max_length=MAX_HISTORY_OBSERVATIONS)
    historical_digest: str | None = Field(None, min_length=64, max_length=64)
    block_length_days: int | None = Field(None, ge=1, le=MAX_HISTORY_OBSERVATIONS)
    weights: List[FiniteFloat] = Field(..., min_length=1)
    cash_weight: FiniteFloat = Field(0.0, ge=0, le=1)
    horizon_days: int = Field(..., ge=1, le=3650)
    path_count: int = Field(..., ge=256, le=100_000)
    random_seed: int | None = Field(None, ge=0, le=2**32 - 1)
    sobol_start_index: int | None = Field(None, ge=0, le=2**32 - 1)
    bootstrap_seed: int | None = Field(None, ge=0, le=2**32 - 1)
    diagnostics: bool = False

    @model_validator(mode="after")
    def validate_dimensions(self) -> SimulationEngineRequest:
        asset_count = len(self.asset_ids)
        if len(set(self.asset_ids)) != asset_count:
            raise ValueError("simulation asset_ids must be unique")
        if len(self.weights) != asset_count:
            raise ValueError("simulation weights must match asset_ids")
        if any(weight < 0 for weight in self.weights):
            raise ValueError("simulation weights must be non-negative")
        if not math.isclose(sum(self.weights) + self.cash_weight, 1.0, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("simulation asset and cash weights must sum to one")
        if self.process == RiskSimulationProcess.BLOCK_BOOTSTRAP:
            self._validate_bootstrap_contract(asset_count)
        else:
            self._validate_parametric_contract(asset_count)
        return self

    def _validate_bootstrap_contract(self, asset_count: int) -> None:
        """Reject every parametric field: the bootstrap estimates nothing."""
        if self.annual_drifts is not None or self.annual_covariance is not None:
            raise ValueError("block bootstrap must not carry an estimated drift or covariance")
        if self.random_seed is not None or self.sobol_start_index is not None:
            raise ValueError("block bootstrap forbids random_seed and sobol_start_index")
        if self.sampling_method != RiskSamplingStrategy.MC:
            raise ValueError("block bootstrap resampling is pseudo-random and requires mc sampling")
        if self.bootstrap_seed is None:
            raise ValueError("block bootstrap requires bootstrap_seed")
        if self.historical_returns is None or self.historical_digest is None:
            raise ValueError("block bootstrap requires aligned historical returns and their digest")
        if any(len(row) != asset_count for row in self.historical_returns):
            raise ValueError("historical return rows must match asset_ids")
        if any(value <= -1 for row in self.historical_returns for value in row):
            raise ValueError("historical simple returns must be greater than -1")
        if self.block_length_days is not None and self.block_length_days > len(self.historical_returns):
            raise ValueError("block length cannot exceed the observed history")

    def _validate_parametric_contract(self, asset_count: int) -> None:
        """Keep the pre-existing GBM contract bit-for-bit unchanged."""
        if self.regime != RiskSimulationRegime.NONE:
            raise ValueError("prescribed regimes require the block bootstrap process")
        for name in ("historical_returns", "historical_digest", "block_length_days", "bootstrap_seed"):
            if getattr(self, name) is not None:
                raise ValueError(f"{name} is meaningful only for the block bootstrap process")
        self._validate_covariance_shape(asset_count)
        self._validate_sequence_control(asset_count)

    def _validate_covariance_shape(self, asset_count: int) -> None:
        if self.annual_drifts is None or self.annual_covariance is None:
            raise ValueError("parametric simulation requires annual_drifts and annual_covariance")
        if len(self.annual_drifts) != asset_count or len(self.annual_covariance) != asset_count:
            raise ValueError("simulation vectors and covariance must match asset_ids")
        if any(len(row) != asset_count for row in self.annual_covariance):
            raise ValueError("simulation covariance must be square")
        for row_index, row in enumerate(self.annual_covariance):
            if row[row_index] < 0:
                raise ValueError("simulation covariance diagonal must be non-negative")
            for column_index, value in enumerate(row):
                if not math.isclose(value, self.annual_covariance[column_index][row_index], rel_tol=1e-10, abs_tol=1e-12):
                    raise ValueError("simulation covariance must be symmetric")

    def _validate_sequence_control(self, asset_count: int) -> None:
        if self.sampling_method == RiskSamplingStrategy.MC:
            if self.random_seed is None or self.sobol_start_index is not None:
                raise ValueError("MC simulation requires random_seed and forbids sobol_start_index")
            return
        if self.sobol_start_index is None or self.random_seed is not None:
            raise ValueError("QMC simulation requires sobol_start_index and forbids random_seed")
        if self.path_count & (self.path_count - 1):
            raise ValueError("QMC paths must be a power of two")
        if asset_count * self.horizon_days > MAX_SOBOL_DIMENSION:
            raise ValueError(f"Sobol dimension exceeds the supported maximum of {MAX_SOBOL_DIMENSION}")


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
    block_length_days: PositiveInt | None = None
    regime_declared_days: PositiveInt | None = None
    regime_applied_days: PositiveInt | None = None
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
    """Hash every input that can change the simulated distribution.

    ``historical_returns`` is excluded and represented by ``historical_digest``:
    the matrix is already hashed, and re-serializing megabytes of history to
    build a key would make every cache *hit* pay for the lookup it avoids. The
    worker re-derives the digest from the matrix it receives, so a key can never
    outlive the data it claims to describe.
    """
    payload = {
        "algorithm_version": algorithm_version,
        "request": request.model_dump(mode="json", exclude={"historical_returns"}),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "MAX_HISTORY_OBSERVATIONS",
    "MAX_SOBOL_DIMENSION",
    "SimulationEngineDiagnostics",
    "SimulationEngineRequest",
    "SimulationEngineResult",
    "historical_returns_digest",
    "simulation_cache_key",
]
