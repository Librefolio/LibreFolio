"""QuantLib-only stochastic evolution executed inside a spawn worker."""

from __future__ import annotations

import math
import time
from typing import Any

import numpy as np
import QuantLib as ql

from backend.app.schemas.risk import RiskSamplingStrategy
from backend.app.services.risk.quant.models import (
    SimulationEngineRequest,
    SimulationEngineResult,
)

_PSD_RELATIVE_TOLERANCE = 1e-10
_REQUIRED_QUANTLIB_VERSION = "1.43"


def _validated_covariance(request: SimulationEngineRequest) -> np.ndarray:
    covariance = np.asarray(
        request.annual_covariance,
        dtype=np.float64,
    )
    covariance = (covariance + covariance.T) / 2.0
    eigenvalues = np.linalg.eigvalsh(covariance)
    scale = max(
        float(np.max(np.abs(np.diag(covariance)))),
        1.0,
    )
    if float(np.min(eigenvalues)) < (-_PSD_RELATIVE_TOLERANCE * scale):
        raise ValueError(
            "simulation covariance must be positive semidefinite",
        )
    return covariance


def _correlation_from_covariance(
    covariance: np.ndarray,
) -> np.ndarray:
    volatilities = np.sqrt(
        np.clip(np.diag(covariance), 0.0, None),
    )
    correlation = np.eye(covariance.shape[0], dtype=np.float64)
    for row in range(covariance.shape[0]):
        for column in range(row):
            denominator = volatilities[row] * volatilities[column]
            if denominator == 0:
                if not math.isclose(
                    float(covariance[row, column]),
                    0.0,
                    rel_tol=0.0,
                    abs_tol=1e-12,
                ):
                    raise ValueError(
                        "zero-volatility assets require zero covariance",
                    )
                value = 0.0
            else:
                value = float(
                    covariance[row, column] / denominator,
                )
            value = min(1.0, max(-1.0, value))
            correlation[row, column] = value
            correlation[column, row] = value
    return correlation


def _build_process(
    request: SimulationEngineRequest,
    covariance: np.ndarray,
):
    volatilities = np.sqrt(
        np.clip(np.diag(covariance), 0.0, None),
    )
    components = ql.StochasticProcess1DVector()
    component_refs = []
    for drift, volatility in zip(
        request.annual_drifts,
        volatilities,
        strict=True,
    ):
        component = ql.GeometricBrownianMotionProcess(
            1.0,
            float(drift),
            float(volatility),
        )
        component_refs.append(component)
        components.push_back(component)

    correlation = _correlation_from_covariance(covariance)
    matrix = ql.Matrix(
        len(request.asset_ids),
        len(request.asset_ids),
    )
    for row in range(correlation.shape[0]):
        for column in range(correlation.shape[1]):
            matrix[row][column] = float(
                correlation[row, column],
            )
    process = ql.StochasticProcessArray(components, matrix)
    return process, (components, component_refs, matrix)


def _run_mc(
    request: SimulationEngineRequest,
    process,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    time_grid = ql.TimeGrid(
        request.horizon_days / 365.0,
        request.horizon_days,
    )
    dimension = process.factors() * request.horizon_days
    uniform = ql.UniformRandomSequenceGenerator(
        dimension,
        ql.UniformRandomGenerator(request.seed),
    )
    gaussian = ql.GaussianRandomSequenceGenerator(uniform)
    generator = ql.GaussianMultiPathGenerator(
        process,
        time_grid,
        gaussian,
        False,
    )
    weights = np.asarray(request.weights, dtype=np.float64)
    portfolio_returns = np.full(
        (request.paths, request.horizon_days + 1),
        request.cash_weight - 1.0,
        dtype=np.float64,
    )
    terminal_log_returns = np.empty(
        (request.paths, len(request.asset_ids)),
        dtype=np.float64,
    )
    generation_evolution_seconds = 0.0
    path_aggregation_seconds = 0.0
    for path_index in range(request.paths):
        stage_started = time.perf_counter()
        sample = generator.next()
        multi_path = sample.value()
        generation_evolution_seconds += time.perf_counter() - stage_started
        stage_started = time.perf_counter()
        for asset_index, weight in enumerate(weights):
            path = multi_path.at(asset_index)
            values = np.fromiter(
                (float(path[day]) for day in range(request.horizon_days + 1)),
                dtype=np.float64,
                count=request.horizon_days + 1,
            )
            portfolio_returns[path_index] += weight * values
            terminal_log_returns[path_index, asset_index] = math.log(values[-1])
        path_aggregation_seconds += time.perf_counter() - stage_started
    return (
        portfolio_returns,
        terminal_log_returns,
        {
            "rng_seconds": 0.0,
            "process_evolution_seconds": 0.0,
            "generation_evolution_seconds": generation_evolution_seconds,
            "path_aggregation_seconds": path_aggregation_seconds,
        },
    )


def _run_qmc(
    request: SimulationEngineRequest,
    process,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    factors = process.factors()
    dimension = factors * request.horizon_days
    sobol = ql.SobolRsg(
        dimension,
        0,
        ql.SobolRsg.JoeKuoD7,
    )
    sobol.skipTo(request.seed)
    gaussian = ql.InvCumulativeSobolGaussianRsg(sobol)
    weights = np.asarray(request.weights, dtype=np.float64)
    portfolio_returns = np.empty(
        (request.paths, request.horizon_days + 1),
        dtype=np.float64,
    )
    portfolio_returns[:, 0] = 0.0
    terminal_log_returns = np.empty(
        (request.paths, len(request.asset_ids)),
        dtype=np.float64,
    )
    step_time = 1.0 / 365.0
    rng_seconds = 0.0
    process_evolution_seconds = 0.0
    path_aggregation_seconds = 0.0
    for path_index in range(request.paths):
        stage_started = time.perf_counter()
        sample = gaussian.nextSequence()
        normals = tuple(float(value) for value in sample.value())
        rng_seconds += time.perf_counter() - stage_started
        state = process.initialValues()
        for day in range(request.horizon_days):
            offset = day * factors
            variation = ql.Array(
                [normals[offset + factor] for factor in range(factors)],
            )
            stage_started = time.perf_counter()
            state = process.evolve(
                day * step_time,
                state,
                step_time,
                variation,
            )
            process_evolution_seconds += time.perf_counter() - stage_started
            stage_started = time.perf_counter()
            asset_values = np.fromiter(
                (float(state[index]) for index in range(len(request.asset_ids))),
                dtype=np.float64,
                count=len(request.asset_ids),
            )
            portfolio_returns[path_index, day + 1] = request.cash_weight + float(weights @ asset_values) - 1.0
            path_aggregation_seconds += time.perf_counter() - stage_started
        terminal_log_returns[path_index] = np.log(
            asset_values,
        )
    return (
        portfolio_returns,
        terminal_log_returns,
        {
            "rng_seconds": rng_seconds,
            "process_evolution_seconds": process_evolution_seconds,
            "generation_evolution_seconds": 0.0,
            "path_aggregation_seconds": path_aggregation_seconds,
        },
    )


def execute_simulation_job(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate, evolve and aggregate one simulation request."""
    total_started = time.perf_counter()
    if ql.__version__ != _REQUIRED_QUANTLIB_VERSION:
        raise RuntimeError(
            "risk simulation requires QuantLib 1.43",
        )
    request = SimulationEngineRequest.model_validate(payload)
    covariance = _validated_covariance(request)
    process_started = time.perf_counter()
    process, dependencies = _build_process(
        request,
        covariance,
    )
    process_build_seconds = time.perf_counter() - process_started
    if request.sampling == RiskSamplingStrategy.MC:
        portfolio_returns, terminal_log_returns, stage_timings = _run_mc(
            request,
            process,
        )
    else:
        portfolio_returns, terminal_log_returns, stage_timings = _run_qmc(
            request,
            process,
        )
    if not np.isfinite(portfolio_returns).all():
        raise FloatingPointError(
            "QuantLib produced non-finite portfolio paths",
        )
    if not np.isfinite(terminal_log_returns).all():
        raise FloatingPointError(
            "QuantLib produced non-finite terminal log returns",
        )

    aggregation_started = time.perf_counter()
    terminal_returns = portfolio_returns[:, -1]
    log_covariance = np.atleast_2d(
        np.cov(
            terminal_log_returns,
            rowvar=False,
            ddof=1,
        ),
    )
    result_payload = {
        "percentile_paths": np.quantile(
            portfolio_returns,
            [0.05, 0.5, 0.95],
            axis=0,
        ).tolist(),
        "terminal_mean_return": float(
            np.mean(terminal_returns),
        ),
        "terminal_volatility": float(
            np.std(terminal_returns, ddof=1),
        ),
        "probability_of_loss": float(
            np.mean(terminal_returns < 0),
        ),
        "terminal_asset_log_means": np.mean(
            terminal_log_returns,
            axis=0,
        ).tolist(),
        "terminal_asset_log_covariance": log_covariance.tolist(),
    }
    result_aggregation_seconds = time.perf_counter() - aggregation_started
    if request.diagnostics:
        result_payload["diagnostics"] = {
            "process_build_seconds": process_build_seconds,
            **stage_timings,
            "result_aggregation_seconds": result_aggregation_seconds,
            "total_seconds": time.perf_counter() - total_started,
        }
    result = SimulationEngineResult(**result_payload)
    _ = dependencies
    return result.model_dump(mode="json")


__all__ = ["execute_simulation_job"]
