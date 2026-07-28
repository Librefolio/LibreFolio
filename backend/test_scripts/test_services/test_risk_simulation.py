"""Contracts and mathematical tests for QuantLib risk simulation."""

from __future__ import annotations

import asyncio
import math
import os

import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.schemas.risk import (
    RiskCompositionPolicy,
    RiskSamplingStrategy,
    RiskSimulationBandPoint,
    RiskSimulationCovarianceEstimator,
    RiskSimulationDriftEstimator,
    RiskSimulationOutput,
    RiskSimulationProcess,
)
from backend.app.services.risk.quant import engine as simulation_engine_module
from backend.app.services.risk.quant.engine import (
    SimulationResourceLimitError,
    clear_simulation_cache,
    run_simulation,
    validate_resource_budget,
)
from backend.app.services.risk.quant.estimation import (
    estimate_gbm_parameters,
)
from backend.app.services.risk.quant.models import (
    SimulationEngineRequest,
    SimulationEngineResult,
    simulation_cache_key,
)
from backend.app.services.risk.quant.quantlib_worker import (
    execute_simulation_job,
)
from backend.app.services.risk.quant.spawn_worker import SpawnWorkerResult
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)


def engine_request(**overrides) -> SimulationEngineRequest:
    payload = {
        "sampling": "mc",
        "asset_ids": [1, 2],
        "annual_drifts": [0.05, 0.03],
        "annual_covariance": [
            [0.04, 0.01],
            [0.01, 0.09],
        ],
        "weights": [0.6, 0.3],
        "cash_weight": 0.1,
        "horizon_days": 30,
        "paths": 1024,
        "seed": 123456,
    }
    payload.update(overrides)
    return SimulationEngineRequest.model_validate(payload)


def run_direct(
    request: SimulationEngineRequest,
) -> SimulationEngineResult:
    return SimulationEngineResult.model_validate(
        execute_simulation_job(
            request.model_dump(mode="json"),
        ),
    )


def output_assumptions() -> dict[str, object]:
    return {
        "drift_estimator": (RiskSimulationDriftEstimator.HISTORICAL_LOG_MLE),
        "covariance_estimator": (RiskSimulationCovarianceEstimator.SAMPLE_LOG_RETURNS),
        "aggregation_policy": (RiskCompositionPolicy.CURRENT_BUY_AND_HOLD),
    }


def test_simulation_contract_is_serializable_and_content_keyed():
    request = engine_request()
    payload = request.model_dump(mode="json")

    assert payload["process"] == "gbm"
    assert payload["sampling"] == "mc"
    assert sum(payload["weights"]) + payload["cash_weight"] == pytest.approx(1.0)

    first_key = simulation_cache_key(
        request,
        algorithm_version="simulation@2.0.0",
    )
    assert len(first_key) == 64
    assert first_key == simulation_cache_key(
        SimulationEngineRequest.model_validate_json(
            request.model_dump_json(),
        ),
        algorithm_version="simulation@2.0.0",
    )
    assert first_key != simulation_cache_key(
        engine_request(seed=123457),
        algorithm_version="simulation@2.0.0",
    )


def test_simulation_contract_rejects_invalid_dimensions_and_sampling():
    with pytest.raises(ValidationError, match="weights must sum"):
        engine_request(weights=[0.6, 0.2])
    with pytest.raises(
        ValidationError,
        match="covariance must be symmetric",
    ):
        engine_request(
            annual_covariance=[
                [0.04, 0.02],
                [0.01, 0.09],
            ],
        )
    with pytest.raises(ValidationError):
        engine_request(sampling="rqmc")
    with pytest.raises(ValidationError, match="power of two"):
        engine_request(sampling="qmc", paths=1000)

    seeded_qmc = engine_request(
        sampling="qmc",
        paths=1024,
        seed=4096,
    )
    assert seeded_qmc.seed == 4096

    with pytest.raises(ValidationError, match="Sobol dimension"):
        engine_request(
            sampling="qmc",
            asset_ids=list(range(1, 22)),
            annual_drifts=[0.03] * 21,
            annual_covariance=[[0.04 if row == column else 0.0 for column in range(21)] for row in range(21)],
            weights=[1 / 21] * 21,
            cash_weight=0,
            horizon_days=1010,
            paths=1024,
        )


def test_simulation_result_contract_enforces_shapes_and_order():
    engine_result = SimulationEngineResult(
        percentile_paths=[
            [0.0, -0.1, -0.2],
            [0.0, 0.0, 0.1],
            [0.0, 0.1, 0.3],
        ],
        terminal_mean_return=0.11,
        terminal_volatility=0.2,
        probability_of_loss=0.3,
        terminal_asset_log_means=[0.02],
        terminal_asset_log_covariance=[[0.04]],
    )
    output = RiskSimulationOutput(
        process=RiskSimulationProcess.GBM,
        sampling=RiskSamplingStrategy.QMC,
        horizon_days=2,
        paths=1024,
        **output_assumptions(),
        percentile_bands=[
            RiskSimulationBandPoint(
                day=day,
                p05=engine_result.percentile_paths[0][day],
                p50=engine_result.percentile_paths[1][day],
                p95=engine_result.percentile_paths[2][day],
            )
            for day in range(3)
        ],
        terminal_mean_return=engine_result.terminal_mean_return,
        terminal_volatility=engine_result.terminal_volatility,
        probability_of_loss=engine_result.probability_of_loss,
    )

    assert output.model_dump(mode="json")["kind"] == "simulation"
    with pytest.raises(
        ValidationError,
        match="p05 <= p50 <= p95",
    ):
        RiskSimulationBandPoint(
            day=1,
            p05=0.1,
            p50=0.0,
            p95=0.2,
        )
    with pytest.raises(
        ValidationError,
        match="covariance row count",
    ):
        SimulationEngineResult(
            percentile_paths=[
                [0.0, -0.1],
                [0.0, 0.0],
                [0.0, 0.1],
            ],
            terminal_mean_return=0,
            terminal_volatility=0.1,
            probability_of_loss=0.5,
            terminal_asset_log_means=[0.0, 0.0],
            terminal_asset_log_covariance=[[0.1]],
        )


def test_gbm_estimation_matches_log_mle_and_observed_annualization():
    returns_by_asset = {
        1: [0.02, -0.01, 0.015, 0.005],
        2: [0.01, 0.0, -0.005, 0.02],
    }
    annualization = 300.0
    estimates = estimate_gbm_parameters(
        returns_by_asset,
        annualization_factor=annualization,
    )
    log_returns = np.log1p(
        np.column_stack(list(returns_by_asset.values())),
    )
    expected_covariance = np.cov(log_returns, rowvar=False, ddof=1) * annualization
    expected_drifts = log_returns.mean(axis=0) * annualization + 0.5 * np.diag(expected_covariance)

    assert estimates.asset_ids == (1, 2)
    assert estimates.observations == 4
    assert np.asarray(
        estimates.annual_covariance,
    ) == pytest.approx(expected_covariance)
    assert np.asarray(
        estimates.annual_drifts,
    ) == pytest.approx(expected_drifts)


def _assert_mc_log_moments(
    result: SimulationEngineResult,
    request: SimulationEngineRequest,
) -> None:
    covariance = np.asarray(
        request.annual_covariance,
        dtype=float,
    )
    horizon = request.horizon_days / 365.0
    expected_mean = (np.asarray(request.annual_drifts) - 0.5 * np.diag(covariance)) * horizon
    expected_covariance = covariance * horizon
    observed_mean = np.asarray(
        result.terminal_asset_log_means,
    )
    observed_covariance = np.asarray(
        result.terminal_asset_log_covariance,
    )
    sample_count = request.paths

    mean_standard_error = np.sqrt(
        np.diag(expected_covariance) / sample_count,
    )
    assert np.all(
        np.abs(observed_mean - expected_mean) <= 4.5 * mean_standard_error + 1e-12,
    )

    for row in range(len(request.asset_ids)):
        for column in range(len(request.asset_ids)):
            covariance_standard_error = math.sqrt(
                (expected_covariance[row, column] ** 2 + expected_covariance[row, row] * expected_covariance[column, column]) / (sample_count - 1),
            )
            assert observed_covariance[
                row,
                column,
            ] == pytest.approx(
                expected_covariance[row, column],
                abs=4.5 * covariance_standard_error + 1e-12,
            )

    standard_deviations = np.sqrt(
        np.diag(expected_covariance),
    )
    for row in range(len(request.asset_ids)):
        for column in range(row):
            denominator = standard_deviations[row] * standard_deviations[column]
            if denominator == 0:
                continue
            expected_correlation = expected_covariance[row, column] / denominator
            if abs(expected_correlation) >= 1 - 1e-12:
                continue
            observed_correlation = observed_covariance[row, column] / math.sqrt(
                observed_covariance[row, row] * observed_covariance[column, column],
            )
            fisher_error = abs(np.arctanh(observed_correlation) - np.arctanh(expected_correlation))
            assert fisher_error <= (4.5 / math.sqrt(sample_count - 3))


@pytest.mark.parametrize(
    ("drifts", "covariance", "paths"),
    [
        ([0.05], [[0.04]], 4096),
        (
            [0.05, 0.03],
            [[0.04, -0.015], [-0.015, 0.0225]],
            8192,
        ),
        (
            [0.05, 0.03, 0.07, 0.02, 0.04],
            (
                np.asarray(
                    [
                        [0.18, 0.04, 0.00],
                        [0.10, -0.12, 0.03],
                        [0.00, 0.15, 0.08],
                        [-0.07, 0.02, 0.06],
                        [0.05, -0.04, 0.10],
                    ],
                )
                @ np.asarray(
                    [
                        [0.18, 0.04, 0.00],
                        [0.10, -0.12, 0.03],
                        [0.00, 0.15, 0.08],
                        [-0.07, 0.02, 0.06],
                        [0.05, -0.04, 0.10],
                    ],
                ).T
            ).tolist(),
            8192,
        ),
    ],
)
def test_quantlib_mc_matches_multivariate_gbm_oracle(
    drifts,
    covariance,
    paths,
):
    asset_count = len(drifts)
    request = SimulationEngineRequest(
        sampling="mc",
        asset_ids=list(range(1, asset_count + 1)),
        annual_drifts=drifts,
        annual_covariance=covariance,
        weights=[1 / asset_count] * asset_count,
        horizon_days=60,
        paths=paths,
        seed=123456,
    )

    first = run_direct(request)
    second = run_direct(request)

    assert first == second
    _assert_mc_log_moments(first, request)
    assert all(len(path) == request.horizon_days + 1 and path[0] == pytest.approx(0) for path in first.percentile_paths)
    assert all(
        p05 <= p50 <= p95
        for p05, p50, p95 in zip(
            *first.percentile_paths,
            strict=True,
        )
    )
    assert min(value for path in first.percentile_paths for value in path) > -1


def test_quantlib_handles_positive_semidefinite_and_zero_volatility():
    request = SimulationEngineRequest(
        sampling="qmc",
        asset_ids=[1, 2, 3],
        annual_drifts=[0.05, 0.05, 0.01],
        annual_covariance=[
            [0.04, 0.04, 0.0],
            [0.04, 0.04, 0.0],
            [0.0, 0.0, 0.0],
        ],
        weights=[0.4, 0.4, 0.2],
        horizon_days=30,
        paths=1024,
        seed=0,
    )

    result = run_direct(request)
    observed = np.asarray(
        result.terminal_asset_log_covariance,
    )

    assert observed[0, 1] == pytest.approx(
        observed[0, 0],
        rel=1e-8,
        abs=1e-10,
    )
    assert observed[2, 2] == pytest.approx(0, abs=1e-18)


def test_quantlib_qmc_converges_over_dyadic_path_counts():
    covariance = np.asarray(
        [[0.04, 0.012], [0.012, 0.0225]],
    )
    drifts = np.asarray([0.05, 0.03])
    horizon_days = 30
    horizon = horizon_days / 365.0
    expected_mean = (drifts - 0.5 * np.diag(covariance)) * horizon
    expected_covariance = covariance * horizon
    mean_errors = []
    covariance_errors = []

    for paths in (256, 1024, 4096):
        result = run_direct(
            SimulationEngineRequest(
                sampling="qmc",
                asset_ids=[1, 2],
                annual_drifts=drifts.tolist(),
                annual_covariance=covariance.tolist(),
                weights=[0.5, 0.5],
                horizon_days=horizon_days,
                paths=paths,
                seed=0,
            ),
        )
        mean_errors.append(
            float(
                np.linalg.norm(
                    np.asarray(
                        result.terminal_asset_log_means,
                    )
                    - expected_mean,
                ),
            ),
        )
        covariance_errors.append(
            float(
                np.linalg.norm(
                    np.asarray(
                        result.terminal_asset_log_covariance,
                    )
                    - expected_covariance,
                    ord="fro",
                ),
            ),
        )

    path_exponents = np.log2([256, 1024, 4096])
    mean_slope = np.polyfit(
        path_exponents,
        np.log(mean_errors),
        1,
    )[0]
    covariance_slope = np.polyfit(
        path_exponents,
        np.log(covariance_errors),
        1,
    )[0]
    assert mean_errors[-1] < mean_errors[0]
    assert covariance_errors[-1] < covariance_errors[0]
    assert mean_slope < 0
    assert covariance_slope < 0


@pytest.mark.parametrize(
    "sampling",
    [
        RiskSamplingStrategy.MC,
        RiskSamplingStrategy.QMC,
    ],
)
def test_quantlib_seed_is_repeatable_and_selects_another_stream(
    sampling,
):
    base = engine_request(
        sampling=sampling,
        horizon_days=10,
        paths=256,
        seed=128,
    )
    same = run_direct(base)
    repeated = run_direct(base)
    different = run_direct(
        base.model_copy(update={"seed": 512}),
    )

    assert repeated == same
    assert different != same


@pytest.mark.asyncio
async def test_spawned_quantlib_matches_direct_result_and_cache():
    clear_simulation_cache()
    request = engine_request(
        sampling="qmc",
        horizon_days=10,
        paths=256,
        seed=64,
    )
    direct = run_direct(request)
    try:
        first, first_hit, worker = await run_simulation(
            request,
            algorithm_version="simulation@2.0.0",
        )
        second, second_hit, cached_worker = await run_simulation(
            request,
            algorithm_version="simulation@2.0.0",
        )
    finally:
        await shutdown_quant_worker_pools()

    assert first == direct
    assert second == first
    assert first_hit is False
    assert second_hit is True
    assert worker is not None
    assert worker.worker_pid != os.getpid()
    assert cached_worker is None


@pytest.mark.asyncio
async def test_cancelled_cache_follower_does_not_cancel_shared_simulation(
    monkeypatch,
):
    clear_simulation_cache()
    request = engine_request(horizon_days=5, paths=256)
    expected = run_direct(request)

    class ControlledPool:
        def __init__(self):
            self.started = asyncio.Event()
            self.release = asyncio.Event()
            self.calls = 0

        async def submit(self, _payload):
            self.calls += 1
            self.started.set()
            await self.release.wait()
            return SpawnWorkerResult(
                payload=expected.model_dump(mode="json"),
                worker_pid=12345,
                cold_start=True,
                queue_wait_seconds=0,
                execution_seconds=0,
                round_trip_seconds=0,
                peak_rss_bytes=0,
            )

    pool = ControlledPool()
    monkeypatch.setattr(
        simulation_engine_module,
        "get_simulation_worker_pool",
        lambda: pool,
    )
    leader = asyncio.create_task(
        run_simulation(
            request,
            algorithm_version="simulation@cancel-follower",
        ),
    )
    await pool.started.wait()
    follower = asyncio.create_task(
        run_simulation(
            request,
            algorithm_version="simulation@cancel-follower",
        ),
    )
    await asyncio.sleep(0)
    follower.cancel()
    with pytest.raises(asyncio.CancelledError):
        await follower

    pool.release.set()
    first, first_hit, worker = await leader
    second, second_hit, cached_worker = await run_simulation(
        request,
        algorithm_version="simulation@cancel-follower",
    )

    assert first == expected
    assert second == expected
    assert first_hit is False
    assert second_hit is True
    assert worker is not None
    assert cached_worker is None
    assert pool.calls == 1


def test_simulation_resource_limits_are_explicit():
    oversized = engine_request(
        horizon_days=365,
        paths=100_000,
    )
    with pytest.raises(
        SimulationResourceLimitError,
        match="memory budget",
    ):
        validate_resource_budget(oversized)
