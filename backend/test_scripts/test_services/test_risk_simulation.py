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
    RiskErrorCode,
    RiskSamplingStrategy,
    RiskSimulationBandPoint,
    RiskSimulationCovarianceEstimator,
    RiskSimulationDriftEstimator,
    RiskSimulationOutput,
    RiskSimulationProcess,
    RiskSimulationRegime,
)
from backend.app.services.risk.base import RiskUnavailableError
from backend.app.services.risk.quant import engine as simulation_engine_module
from backend.app.services.risk.quant import models as simulation_models
from backend.app.services.risk.quant import resampling as resampling_module
from backend.app.services.risk.quant.engine import (
    MAX_HISTORY_CELLS,
    SimulationResourceLimitError,
    clear_simulation_cache,
    run_simulation,
    validate_resource_budget,
)
from backend.app.services.risk.quant.estimation import (
    estimate_drift_uncertainty,
    estimate_gbm_parameters,
)
from backend.app.services.risk.quant.models import (
    MAX_HISTORY_OBSERVATIONS,
    MAX_SOBOL_DIMENSION,
    SimulationEngineRequest,
    SimulationEngineResult,
    historical_returns_digest,
    simulation_cache_key,
)
from backend.app.services.risk.quant.quantlib_worker import (
    execute_simulation_job,
)
from backend.app.services.risk.quant.resampling import (
    resolve_block_length,
    resolve_regime_days,
)
from backend.app.services.risk.quant.spawn_worker import SpawnWorkerResult
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)
from backend.app.services.risk_plugins.simulation import (
    SimulationAnalytic,
    SimulationParams,
)


def engine_request(**overrides) -> SimulationEngineRequest:
    payload = {
        "process": "gbm",
        "sampling_method": "mc",
        "asset_ids": [1, 2],
        "annual_drifts": [0.05, 0.03],
        "annual_covariance": [
            [0.04, 0.01],
            [0.01, 0.09],
        ],
        "weights": [0.6, 0.3],
        "cash_weight": 0.1,
        "horizon_days": 30,
        "path_count": 1024,
    }
    payload.update(overrides)
    if "random_seed" not in payload and "sobol_start_index" not in payload:
        sequence_field = "sobol_start_index" if payload["sampling_method"] == "qmc" else "random_seed"
        payload[sequence_field] = 123456
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
    assert payload["sampling_method"] == "mc"
    assert payload["random_seed"] == 123456
    assert payload["sobol_start_index"] is None
    assert "sampling" not in payload
    assert "paths" not in payload
    assert "seed" not in payload
    assert sum(payload["weights"]) + payload["cash_weight"] == pytest.approx(1.0)

    first_key = simulation_cache_key(
        request,
        algorithm_version="simulation@2.1.0",
    )
    assert len(first_key) == 64
    assert first_key == simulation_cache_key(
        SimulationEngineRequest.model_validate_json(
            request.model_dump_json(),
        ),
        algorithm_version="simulation@2.1.0",
    )
    assert first_key != simulation_cache_key(
        engine_request(random_seed=123457),
        algorithm_version="simulation@2.1.0",
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
        engine_request(sampling_method="rqmc")
    with pytest.raises(ValidationError, match="power of two"):
        engine_request(
            sampling_method="qmc",
            path_count=1000,
            sobol_start_index=0,
        )

    seeded_qmc = engine_request(
        sampling_method="qmc",
        path_count=1024,
        sobol_start_index=4096,
    )
    assert seeded_qmc.sobol_start_index == 4096
    assert seeded_qmc.random_seed is None

    with pytest.raises(ValidationError, match="forbids sobol_start_index"):
        engine_request(sobol_start_index=4096)
    with pytest.raises(ValidationError, match="forbids random_seed"):
        engine_request(
            sampling_method="qmc",
            random_seed=4096,
        )

    with pytest.raises(ValidationError, match="Sobol dimension"):
        engine_request(
            sampling_method="qmc",
            asset_ids=list(range(1, 22)),
            annual_drifts=[0.03] * 21,
            annual_covariance=[[0.04 if row == column else 0.0 for column in range(21)] for row in range(21)],
            weights=[1 / 21] * 21,
            cash_weight=0,
            horizon_days=1010,
            path_count=1024,
            sobol_start_index=0,
        )


def test_simulation_params_normalize_legacy_sequence_contract():
    legacy_mc = SimulationParams.model_validate(
        {
            "sampling": "mc",
            "paths": 1024,
            "seed": 7,
        },
    )
    legacy_qmc = SimulationParams.model_validate(
        {
            "sampling": "qmc",
            "paths": 1024,
            "seed": 4096,
        },
    )
    canonical_mc = SimulationParams(
        sampling_method="mc",
        path_count=1024,
        random_seed=7,
    )
    canonical_qmc = SimulationParams(
        sampling_method="qmc",
        path_count=1024,
        sobol_start_index=4096,
    )

    assert legacy_mc == canonical_mc
    assert legacy_qmc == canonical_qmc
    assert legacy_mc.model_dump(mode="json", exclude_none=True) == {
        "process": "gbm",
        "regime": "none",
        "sampling_method": "mc",
        "horizon_days": 365,
        "path_count": 1024,
        "random_seed": 7,
    }
    assert legacy_qmc.model_dump(mode="json", exclude_none=True) == {
        "process": "gbm",
        "regime": "none",
        "sampling_method": "qmc",
        "horizon_days": 365,
        "path_count": 1024,
        "sobol_start_index": 4096,
    }

    with pytest.raises(ValidationError, match="conflicts"):
        SimulationParams.model_validate(
            {
                "sampling_method": "mc",
                "random_seed": 1,
                "seed": 2,
            },
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
        sampling_method=RiskSamplingStrategy.QMC,
        horizon_days=2,
        path_count=1024,
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
    sample_count = request.path_count

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
        process="gbm",
        sampling_method="mc",
        asset_ids=list(range(1, asset_count + 1)),
        annual_drifts=drifts,
        annual_covariance=covariance,
        weights=[1 / asset_count] * asset_count,
        horizon_days=60,
        path_count=paths,
        random_seed=123456,
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
        process="gbm",
        sampling_method="qmc",
        asset_ids=[1, 2, 3],
        annual_drifts=[0.05, 0.05, 0.01],
        annual_covariance=[
            [0.04, 0.04, 0.0],
            [0.04, 0.04, 0.0],
            [0.0, 0.0, 0.0],
        ],
        weights=[0.4, 0.4, 0.2],
        horizon_days=30,
        path_count=1024,
        sobol_start_index=0,
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
                process="gbm",
                sampling_method="qmc",
                asset_ids=[1, 2],
                annual_drifts=drifts.tolist(),
                annual_covariance=covariance.tolist(),
                weights=[0.5, 0.5],
                horizon_days=horizon_days,
                path_count=paths,
                sobol_start_index=0,
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
    "sampling_method",
    [
        RiskSamplingStrategy.MC,
        RiskSamplingStrategy.QMC,
    ],
)
def test_quantlib_sequence_control_is_repeatable_and_selects_another_stream(
    sampling_method,
):
    sequence_field = "random_seed" if sampling_method == RiskSamplingStrategy.MC else "sobol_start_index"
    base = engine_request(
        sampling_method=sampling_method,
        horizon_days=10,
        path_count=256,
        **{sequence_field: 128},
    )
    same = run_direct(base)
    repeated = run_direct(base)
    different = run_direct(
        base.model_copy(update={sequence_field: 512}),
    )

    assert repeated == same
    assert different != same


@pytest.mark.asyncio
async def test_spawned_quantlib_matches_direct_result_and_cache():
    clear_simulation_cache()
    request = engine_request(
        sampling_method="qmc",
        horizon_days=10,
        path_count=256,
        sobol_start_index=64,
    )
    direct = run_direct(request)
    try:
        first, first_hit, worker = await run_simulation(
            request,
            algorithm_version="simulation@2.1.0",
        )
        second, second_hit, cached_worker = await run_simulation(
            request,
            algorithm_version="simulation@2.1.0",
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
    request = engine_request(horizon_days=5, path_count=256)
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
        path_count=100_000,
    )
    with pytest.raises(
        SimulationResourceLimitError,
        match="memory budget",
    ):
        validate_resource_budget(oversized)


BOOTSTRAP_ALGORITHM_VERSION = "simulation@3.0.0-bootstrap-quantlib-1.43"


def bootstrap_history(
    *,
    observations: int = 756,
    asset_count: int = 2,
    seed: int = 20260918,
) -> np.ndarray:
    """Build a synthetic simple-return history with a stable joint structure.

    The draw is seeded because the correlation and dispersion expectations
    below are read off *this* matrix: a history redrawn per run would turn
    every one of them into a bet on the weather.
    """
    generator = np.random.default_rng(seed)
    common = generator.normal(0.0002, 0.010, size=(observations, 1))
    idiosyncratic = generator.normal(0.0, 0.0045, size=(observations, asset_count))
    loadings = np.linspace(1.0, 0.85, asset_count)
    return np.expm1(common * loadings + idiosyncratic)


def bootstrap_request(
    history: np.ndarray | None = None,
    **overrides,
) -> SimulationEngineRequest:
    """Mirror ``engine_request`` for the resampling contract.

    ``asset_ids`` and ``weights`` are derived from the matrix, so callers pass
    a different history rather than re-declaring the two in step with it.
    """
    matrix = bootstrap_history() if history is None else history
    asset_count = matrix.shape[1]
    payload = {
        "process": "block_bootstrap",
        "sampling_method": "mc",
        "asset_ids": list(range(1, asset_count + 1)),
        "historical_returns": matrix.tolist(),
        "historical_digest": historical_returns_digest(matrix),
        "weights": [1 / asset_count] * asset_count,
        "cash_weight": 0.0,
        "horizon_days": 252,
        "path_count": 4096,
        "bootstrap_seed": 987654,
    }
    payload.update(overrides)
    return SimulationEngineRequest.model_validate(payload)


def terminal_log_dispersion(
    result: SimulationEngineResult,
) -> np.ndarray:
    """Per-asset standard deviation of the terminal log return."""
    return np.sqrt(
        np.asarray(
            result.terminal_asset_log_covariance,
        ).diagonal(),
    )


def terminal_log_correlation(
    result: SimulationEngineResult,
) -> float:
    """Pearson correlation between the first two resampled assets."""
    covariance = np.asarray(
        result.terminal_asset_log_covariance,
    )
    dispersion = np.sqrt(covariance.diagonal())
    return float(
        covariance[0, 1] / (dispersion[0] * dispersion[1]),
    )


def bootstrap_output(**overrides) -> RiskSimulationOutput:
    """Build the renderer-facing result of a resampled simulation."""
    payload = {
        "process": RiskSimulationProcess.BLOCK_BOOTSTRAP,
        "regime": RiskSimulationRegime.NONE,
        "sampling_method": RiskSamplingStrategy.MC,
        "horizon_days": 2,
        "path_count": 512,
        "block_length_days": 9,
        "drift_estimator": (RiskSimulationDriftEstimator.EMPIRICAL_RESAMPLED),
        "covariance_estimator": (RiskSimulationCovarianceEstimator.NOT_ESTIMATED_JOINT_RESAMPLING),
        "aggregation_policy": (RiskCompositionPolicy.CURRENT_BUY_AND_HOLD),
        "percentile_bands": [
            RiskSimulationBandPoint(
                day=day,
                p05=-0.01 * day,
                p50=0.0,
                p95=0.01 * day,
            )
            for day in range(3)
        ],
        "terminal_mean_return": 0.01,
        "terminal_volatility": 0.2,
        "probability_of_loss": 0.4,
    }
    payload.update(overrides)
    return RiskSimulationOutput(**payload)


def test_block_bootstrap_is_reproducible_at_a_fixed_seed():
    """Anchor every other resampling expectation in this file.

    The bootstrap introduces a brand-new random draw. Without a seeded
    reproducibility floor, a red anywhere below could always be blamed on the
    sampler instead of on the claim under test.
    """
    request = bootstrap_request(horizon_days=120, path_count=2048)

    first = run_direct(request)
    second = run_direct(
        SimulationEngineRequest.model_validate_json(
            request.model_dump_json(),
        ),
    )

    assert second == first
    assert first.block_length_days == resolve_block_length(
        len(request.historical_returns),
    )
    assert first.regime_declared_days is None
    assert first.regime_applied_days is None


def test_block_bootstrap_seed_selects_another_resample():
    """Keep the reproducibility test above from passing on a constant."""
    request = bootstrap_request(horizon_days=120, path_count=2048)

    base = run_direct(request)
    other = run_direct(
        request.model_copy(update={"bootstrap_seed": 987655}),
    )

    assert other != base
    assert other.percentile_paths != base.percentile_paths
    assert other.block_length_days == base.block_length_days
    assert other.terminal_volatility == pytest.approx(
        base.terminal_volatility,
        rel=0.2,
    )


def test_block_bootstrap_is_invariant_to_the_internal_chunk_boundary(
    monkeypatch,
):
    """A machine with a different memory budget must simulate the same thing.

    Block origins are drawn in one call before the work is sliced, so slicing
    cannot move the seed. This configuration deliberately crosses the internal
    boundary, and the assertion compares it against the same request run in a
    single slice.
    """
    matrix = bootstrap_history(asset_count=4)
    request = bootstrap_request(
        matrix,
        horizon_days=1000,
        path_count=1536,
    )
    cells_per_path = request.horizon_days * len(request.asset_ids)
    chunk_size = max(
        1,
        resampling_module._CELL_BUDGET // cells_per_path,
    )

    assert chunk_size < request.path_count
    chunked = run_direct(request)

    monkeypatch.setattr(
        resampling_module,
        "_CELL_BUDGET",
        cells_per_path * request.path_count,
    )
    assert (resampling_module._CELL_BUDGET // cells_per_path) >= request.path_count
    single_chunk = run_direct(request)

    assert single_chunk == chunked


def test_regimes_leave_the_resampled_correlation_invariant():
    """Guard the on-screen claim that correlations stay those of the history.

    Scaling dispersion and shifting level are the only two transformations a
    regime applies, and both are correlation-preserving on a joint resample.
    If this goes red, the hypothesis text became a lie.
    """
    matrix = bootstrap_history()
    request = bootstrap_request(
        matrix,
        horizon_days=252,
        path_count=4096,
    )
    correlations = {
        regime: terminal_log_correlation(
            run_direct(request.model_copy(update={"regime": regime})),
        )
        for regime in (
            RiskSimulationRegime.NONE,
            RiskSimulationRegime.CALM,
            RiskSimulationRegime.PROLONGED_CRISIS,
        )
    }
    observed_history = float(
        np.corrcoef(np.log1p(matrix), rowvar=False)[0, 1],
    )
    baseline = correlations[RiskSimulationRegime.NONE]

    assert baseline == pytest.approx(observed_history, abs=0.03)
    for regime, correlation in correlations.items():
        assert correlation == pytest.approx(baseline, abs=1e-9), regime


def test_regime_dispersion_scales_by_the_declared_multiple():
    """Calm narrows the spread to 0.7x, a prolonged crisis widens it to 2.5x.

    The horizon is shorter than the crisis hypothesis, so the scale is uniform
    over every simulated day and the log-scale ratio is exact. Do not reuse
    that tolerance on a horizon long enough to outlast the regime window.
    """
    request = bootstrap_request(horizon_days=252, path_count=4096)

    baseline = run_direct(request)
    calm = run_direct(
        request.model_copy(update={"regime": RiskSimulationRegime.CALM}),
    )
    crisis = run_direct(
        request.model_copy(
            update={"regime": RiskSimulationRegime.PROLONGED_CRISIS},
        ),
    )
    calm_ratio = (terminal_log_dispersion(calm) / terminal_log_dispersion(baseline)).tolist()
    crisis_ratio = (terminal_log_dispersion(crisis) / terminal_log_dispersion(baseline)).tolist()

    assert calm_ratio == pytest.approx([0.7] * len(calm_ratio), rel=1e-9)
    assert crisis_ratio == pytest.approx([2.5] * len(crisis_ratio), rel=1e-9)
    assert calm.terminal_volatility / baseline.terminal_volatility == pytest.approx(0.7, abs=0.08)
    assert crisis.terminal_volatility / baseline.terminal_volatility == pytest.approx(2.5, abs=0.25)
    assert calm.regime_applied_days == request.horizon_days
    assert crisis.regime_declared_days == 426
    assert crisis.regime_applied_days == request.horizon_days


def test_shock_recovery_regime_delivers_its_declared_fall():
    """The preset is advertised as a 35% fall over two months."""
    matrix = bootstrap_history(asset_count=1)
    request = bootstrap_request(
        matrix,
        horizon_days=61,
        path_count=8192,
    )

    baseline = run_direct(request)
    shocked = run_direct(
        request.model_copy(
            update={"regime": RiskSimulationRegime.SHOCK_RECOVERY},
        ),
    )
    baseline_median = baseline.percentile_paths[1][request.horizon_days]
    shocked_median = shocked.percentile_paths[1][request.horizon_days]

    assert shocked.regime_declared_days == 61
    assert shocked.regime_applied_days == 61
    # Exact, and independent of the history: the preset multiplies every path
    # by one gross factor, and a quantile of a positively scaled sample scales
    # with it.
    assert (1 + shocked_median) / (1 + baseline_median) == pytest.approx(0.65, rel=1e-9)
    # The figure the caption promises. It is approximate where the one above is
    # exact, because what the user reads is the fall applied on top of the
    # history's own drift -- here a median +1.6% over the two months.
    assert shocked_median == pytest.approx(-0.35, abs=0.02)


def test_prolonged_crisis_discloses_truncation_against_a_short_horizon():
    """A 14-month crisis squeezed into a year is a different hypothesis."""
    assert resolve_regime_days(
        RiskSimulationRegime.PROLONGED_CRISIS,
        365,
    ) == (426, 365)
    assert resolve_regime_days(
        RiskSimulationRegime.PROLONGED_CRISIS,
        500,
    ) == (426, 426)
    assert resolve_regime_days(
        RiskSimulationRegime.SHOCK_RECOVERY,
        30,
    ) == (61, 30)
    assert resolve_regime_days(RiskSimulationRegime.CALM, 30) == (30, 30)
    assert resolve_regime_days(RiskSimulationRegime.NONE, 365) == (
        None,
        None,
    )

    request = bootstrap_request(
        horizon_days=365,
        path_count=1024,
        regime=RiskSimulationRegime.PROLONGED_CRISIS,
    )
    truncated = run_direct(request)
    untruncated = run_direct(
        request.model_copy(update={"horizon_days": 500}),
    )

    assert truncated.regime_declared_days == 426
    assert truncated.regime_applied_days == 365
    assert untruncated.regime_declared_days == 426
    assert untruncated.regime_applied_days == 426


def test_simulation_output_refuses_an_undisclosed_regime():
    """Disclosure is structural: the contract cannot be built without it."""
    disclosed = bootstrap_output(
        regime=RiskSimulationRegime.PROLONGED_CRISIS,
        regime_declared_days=426,
        regime_applied_days=365,
    )

    assert disclosed.regime_declared_days == 426
    assert disclosed.regime_applied_days == 365

    with pytest.raises(
        ValidationError,
        match="must disclose declared and applied",
    ):
        bootstrap_output(
            regime=RiskSimulationRegime.PROLONGED_CRISIS,
        )
    with pytest.raises(
        ValidationError,
        match="must disclose declared and applied",
    ):
        bootstrap_output(
            regime=RiskSimulationRegime.CALM,
            regime_declared_days=365,
        )
    with pytest.raises(
        ValidationError,
        match="cannot exceed regime_declared_days",
    ):
        bootstrap_output(
            regime=RiskSimulationRegime.PROLONGED_CRISIS,
            regime_declared_days=61,
            regime_applied_days=365,
        )
    with pytest.raises(
        ValidationError,
        match="must disclose block_length_days",
    ):
        bootstrap_output(block_length_days=None)
    with pytest.raises(
        ValidationError,
        match="meaningful only for a prescribed regime",
    ):
        bootstrap_output(
            regime_declared_days=365,
            regime_applied_days=365,
        )
    with pytest.raises(
        ValidationError,
        match="meaningful only for the block bootstrap",
    ):
        bootstrap_output(process=RiskSimulationProcess.GBM)
    with pytest.raises(
        ValidationError,
        match="require the block bootstrap process",
    ):
        bootstrap_output(
            process=RiskSimulationProcess.GBM,
            block_length_days=None,
            regime=RiskSimulationRegime.CALM,
            regime_declared_days=365,
            regime_applied_days=365,
        )


def test_worker_rejects_history_that_does_not_match_its_digest():
    """A cache key must never outlive the data it claims to describe."""
    request = bootstrap_request(horizon_days=30, path_count=512)
    stale_matrix = (np.asarray(request.historical_returns) * 1.5).tolist()

    with pytest.raises(
        ValueError,
        match="do not match the digest",
    ):
        execute_simulation_job(
            request.model_copy(
                update={"historical_digest": "0" * 64},
            ).model_dump(mode="json"),
        )
    with pytest.raises(
        ValueError,
        match="do not match the digest",
    ):
        execute_simulation_job(
            request.model_copy(
                update={"historical_returns": stale_matrix},
            ).model_dump(mode="json"),
        )

    honest = run_direct(request)

    assert honest.block_length_days == resolve_block_length(
        len(request.historical_returns),
    )


def test_bootstrap_cache_key_is_content_addressed_and_bounded():
    """The key is the digest, never the matrix: even a hit pays for the key."""
    small = bootstrap_request(
        bootstrap_history(observations=64),
        horizon_days=30,
        path_count=512,
    )
    large = bootstrap_request(
        bootstrap_history(observations=5000, asset_count=50),
        horizon_days=30,
        path_count=512,
    )
    other_history = bootstrap_history(observations=64, seed=20260919)
    changed = bootstrap_request(
        other_history,
        horizon_days=30,
        path_count=512,
    )
    base_key = simulation_cache_key(
        small,
        algorithm_version=BOOTSTRAP_ALGORITHM_VERSION,
    )

    assert len(base_key) == 64
    assert (
        len(
            simulation_cache_key(
                large,
                algorithm_version=BOOTSTRAP_ALGORITHM_VERSION,
            ),
        )
        == 64
    )
    assert (
        simulation_cache_key(
            changed,
            algorithm_version=BOOTSTRAP_ALGORITHM_VERSION,
        )
        != base_key
    )
    assert (
        simulation_cache_key(
            small.model_copy(update={"bootstrap_seed": 987655}),
            algorithm_version=BOOTSTRAP_ALGORITHM_VERSION,
        )
        != base_key
    )
    assert (
        simulation_cache_key(
            small.model_copy(
                update={"historical_returns": other_history.tolist()},
            ),
            algorithm_version=BOOTSTRAP_ALGORITHM_VERSION,
        )
        == base_key
    )


def test_bootstrap_and_parametric_contracts_are_mutually_exclusive():
    """Neither contract can borrow a field that belongs to the other."""
    with pytest.raises(
        ValidationError,
        match="must not carry an estimated drift",
    ):
        bootstrap_request(annual_drifts=[0.05, 0.03])
    with pytest.raises(
        ValidationError,
        match="must not carry an estimated drift",
    ):
        bootstrap_request(
            annual_covariance=[[0.04, 0.01], [0.01, 0.09]],
        )
    with pytest.raises(
        ValidationError,
        match="forbids random_seed and sobol_start_index",
    ):
        bootstrap_request(random_seed=7)
    with pytest.raises(
        ValidationError,
        match="forbids random_seed and sobol_start_index",
    ):
        bootstrap_request(sobol_start_index=7)
    with pytest.raises(
        ValidationError,
        match="requires mc sampling",
    ):
        bootstrap_request(sampling_method="qmc")
    with pytest.raises(
        ValidationError,
        match="requires bootstrap_seed",
    ):
        bootstrap_request(bootstrap_seed=None)
    with pytest.raises(
        ValidationError,
        match="requires aligned historical returns",
    ):
        bootstrap_request(
            historical_returns=None,
            historical_digest=None,
        )
    with pytest.raises(
        ValidationError,
        match="cannot exceed the observed history",
    ):
        bootstrap_request(block_length_days=5000)

    for field, value in (
        ("historical_returns", [[0.01, 0.02], [0.0, 0.0]]),
        ("historical_digest", "0" * 64),
        ("block_length_days", 5),
        ("bootstrap_seed", 5),
    ):
        with pytest.raises(
            ValidationError,
            match=f"{field} is meaningful only",
        ):
            engine_request(**{field: value})
    for regime in (
        RiskSimulationRegime.CALM,
        RiskSimulationRegime.PROLONGED_CRISIS,
        RiskSimulationRegime.SHOCK_RECOVERY,
    ):
        with pytest.raises(
            ValidationError,
            match="require the block bootstrap process",
        ):
            engine_request(regime=regime)


# A block is compared with the history in observations, the unit the history is counted in; and
# `steps_per_year` belongs to the bootstrap alone, positive when set (developer's decisions of
# 30/09/2026).


def test_the_engine_compares_a_block_with_the_history_in_observations():
    history = bootstrap_history(observations=30, asset_count=1)

    # 40 calendar days of a 252-a-year series are 28 observations: they fit in 30...
    assert bootstrap_request(history, block_length_days=40, steps_per_year=252.0).block_length_days == 40
    # ...and 50 days are 35, which do not.
    with pytest.raises(ValidationError, match="cannot exceed the observed history"):
        bootstrap_request(history, block_length_days=50, steps_per_year=252.0)
    # Unset, a day is an observation, as today: 30 fit, 31 do not.
    assert bootstrap_request(history, block_length_days=30).block_length_days == 30
    with pytest.raises(ValidationError, match="cannot exceed the observed history"):
        bootstrap_request(history, block_length_days=31)


def test_steps_per_year_belongs_to_the_bootstrap_and_is_positive():
    with pytest.raises(ValidationError, match="steps_per_year is meaningful only for the block bootstrap process"):
        engine_request(steps_per_year=252.0)

    for invalid in (0.0, -252.0):
        with pytest.raises(ValidationError) as refused:
            bootstrap_request(steps_per_year=invalid)
        errors = refused.value.errors()
        # Refused for its value, not as a field the contract does not know.
        assert errors and all(error["type"] != "extra_forbidden" for error in errors), errors
        assert any("steps_per_year" in " ".join([*map(str, error["loc"]), error["msg"]]) for error in errors), errors

    assert bootstrap_request(steps_per_year=252.0).steps_per_year == 252.0


def test_block_length_follows_the_cube_root_rule_and_is_disclosed():
    """The rule of thumb is a hypothesis about dependence: it must be shown."""
    assert [resolve_block_length(observations) for observations in (30, 252, 1250, 2500)] == [3, 6, 11, 14]
    assert resolve_block_length(30, 500) == 30
    assert resolve_block_length(1250, 3) == 3

    request = bootstrap_request(
        bootstrap_history(observations=1250),
        horizon_days=30,
        path_count=512,
    )
    disclosed = run_direct(request)
    overridden = run_direct(
        request.model_copy(update={"block_length_days": 25}),
    )

    assert disclosed.block_length_days == 11
    assert disclosed.regime_declared_days is None
    assert disclosed.regime_applied_days is None
    assert overridden.block_length_days == 25
    assert overridden != disclosed


def test_resource_budget_covers_history_as_well_as_paths():
    """History crosses the process boundary, so it has to be budgeted too."""
    oversized = bootstrap_request(
        bootstrap_history(observations=2501, asset_count=100),
        horizon_days=30,
        path_count=256,
    )
    with pytest.raises(
        SimulationResourceLimitError,
        match="process-boundary budget",
    ) as history_error:
        validate_resource_budget(oversized)

    assert history_error.value.metric == "history_cells"
    assert history_error.value.actual == 2501 * 100
    assert history_error.value.limit == MAX_HISTORY_CELLS

    validate_resource_budget(
        bootstrap_request(
            bootstrap_history(observations=2500, asset_count=100),
            horizon_days=30,
            path_count=256,
        ),
    )

    with pytest.raises(
        SimulationResourceLimitError,
        match="memory budget",
    ) as portfolio_error:
        validate_resource_budget(
            bootstrap_request(horizon_days=365, path_count=100_000),
        )
    with pytest.raises(
        SimulationResourceLimitError,
        match="compute budget",
    ) as stochastic_error:
        validate_resource_budget(
            bootstrap_request(
                bootstrap_history(observations=60, asset_count=11),
                horizon_days=365,
                path_count=50_000,
            ),
        )

    assert portfolio_error.value.metric == "portfolio_cells"
    assert stochastic_error.value.metric == "stochastic_cells"
    validate_resource_budget(
        bootstrap_request(horizon_days=252, path_count=4096),
    )


def test_degenerate_collinear_history_still_resamples():
    """A robustness floor, not a claim of accuracy.

    A joint resample never inverts or factorises a covariance, so a perfectly
    collinear history has no ill-conditioned matrix to reject: it must come
    back with a result instead of the parametric path's INVALID_COVARIANCE.
    """
    matrix = bootstrap_history()
    collinear = np.column_stack([matrix[:, 0], matrix[:, 0]])

    result = run_direct(
        bootstrap_request(
            collinear,
            horizon_days=60,
            path_count=1024,
        ),
    )
    covariance = np.asarray(
        result.terminal_asset_log_covariance,
    )

    assert covariance[0, 0] == pytest.approx(
        covariance[1, 1],
        rel=1e-12,
    )
    assert covariance[0, 1] == pytest.approx(
        covariance[0, 0],
        rel=1e-12,
    )
    assert float(np.linalg.det(covariance)) == pytest.approx(0, abs=1e-12)
    assert result.terminal_volatility > 0
    assert result.block_length_days == resolve_block_length(
        len(collinear),
    )
    assert all(
        p05 <= p50 <= p95
        for p05, p50, p95 in zip(
            *result.percentile_paths,
            strict=True,
        )
    )


# --- Steps per year (developer's decision of 30/09/2026) ---------------------
#
# The block bootstrap resamples OBSERVATIONS, and a series quoted Monday to
# Friday holds about 252 of them a year, not 365. With `steps_per_year` the
# engine simulates round(horizon_days × steps / 365) steps and maps them back
# onto calendar days — day d reads step floor(d × steps / days) — so the bands
# keep one point per calendar day. A regime is declared in calendar days and
# applied in steps; the prolonged crisis drifts by log(0.8) per YEAR OF STEPS.
# The disclosure stays in calendar days. `None` means 365: today's engine, to
# the byte. GBM is not concerned.

STEADY_RETURN = 0.001


def constant_history(simple_return: float, observations: int = 60) -> np.ndarray:
    """One asset whose every observation is the same, so every resampled path is the same path."""
    return np.full((observations, 1), simple_return)


def resample(history: np.ndarray, **overrides):
    """Run the resampler itself: the whole path matrix, one column per calendar day."""
    request = bootstrap_request(history, **{"path_count": 256, **overrides})
    return resampling_module.run_block_bootstrap(request)


@pytest.mark.parametrize(
    ("steps_per_year", "steps"),
    [
        pytest.param(None, 365, id="unset-is-every-calendar-day"),
        pytest.param(365.0, 365, id="a-series-quoted-every-day"),
        pytest.param(252.0, 252, id="a-series-quoted-on-trading-days"),
    ],
)
def test_bootstrap_simulates_the_steps_its_calendar_horizon_holds_and_maps_them_back_to_days(steps_per_year, steps):
    frequency = {} if steps_per_year is None else {"steps_per_year": steps_per_year}

    portfolio, terminal, _timings, _disclosure = resample(constant_history(STEADY_RETURN), horizon_days=365, **frequency)

    # One point per calendar day, whatever the number of steps.
    assert portfolio.shape == (256, 366)
    # Every path compounds the same return once per step, and the terminal is the final step.
    assert (terminal[:, 0] / math.log1p(STEADY_RETURN)).tolist() == pytest.approx([steps] * 256, rel=1e-9)
    # Day d reads step floor(d × steps / 365): day 0 is step 0, day 365 the last step.
    assert portfolio[0].tolist() == pytest.approx([(1 + STEADY_RETURN) ** (day * steps // 365) - 1 for day in range(366)], rel=1e-9, abs=1e-12)


@pytest.mark.parametrize("steps_per_year", [pytest.param(252.0, id="252-a-year"), pytest.param(365.0, id="365-a-year")])
def test_a_prolonged_crisis_drifts_by_its_annual_factor_over_one_year_of_steps(steps_per_year):
    # No return and no dispersion in the history: the regime's level shift is all that moves.
    portfolio, _terminal, _timings, disclosure = resample(constant_history(0.0), horizon_days=365, regime=RiskSimulationRegime.PROLONGED_CRISIS, steps_per_year=steps_per_year)

    assert (1 + portfolio[:, -1]).tolist() == pytest.approx([0.8] * 256, rel=1e-12)
    # Disclosed in calendar days: fourteen months declared, the one-year horizon applied.
    assert (disclosure["regime_declared_days"], disclosure["regime_applied_days"]) == (426, 365)


@pytest.mark.parametrize(
    ("steps_per_year", "crisis_steps"),
    [pytest.param(252.0, 294, id="426-days-are-294-steps-of-252"), pytest.param(365.0, 426, id="426-days-are-426-daily-steps")],
)
def test_a_prolonged_crisis_lasts_its_declared_days_in_steps_and_ends_on_its_calendar_day(steps_per_year, crisis_steps):
    portfolio, _terminal, _timings, disclosure = resample(constant_history(0.0), horizon_days=730, regime=RiskSimulationRegime.PROLONGED_CRISIS, steps_per_year=steps_per_year)
    path = 1 + portfolio[0]

    # round(426 × steps / 365) steps of log(0.8) / steps each, then the shift stops.
    assert path[-1] == pytest.approx(0.8 ** (crisis_steps / steps_per_year), rel=1e-12)
    # The last crisis step falls on day 426, the declared calendar length, at either frequency.
    assert path[425] > path[426]
    assert path[426:].tolist() == pytest.approx([path[426]] * (731 - 426), rel=1e-12)
    assert (disclosure["regime_declared_days"], disclosure["regime_applied_days"]) == (426, 426)


@pytest.mark.parametrize(
    ("steps_per_year", "shock_steps", "first_step_day"),
    [pytest.param(252.0, 42, 2, id="61-days-are-42-steps-of-252"), pytest.param(365.0, 61, 1, id="61-days-are-61-daily-steps")],
)
def test_a_shock_falls_step_by_step_and_lands_whole_on_its_declared_calendar_day(steps_per_year, shock_steps, first_step_day):
    portfolio, _terminal, _timings, disclosure = resample(constant_history(0.0), horizon_days=365, regime=RiskSimulationRegime.SHOCK_RECOVERY, steps_per_year=steps_per_year)
    path = 1 + portfolio[0]

    # Each step takes an equal share of the 35% fall: the first calendar day that reaches step 1.
    assert path[first_step_day - 1] == 1.0
    assert path[first_step_day] == pytest.approx(0.65 ** (1 / shock_steps), rel=1e-12)
    # The whole fall has landed by day 61, the declared length, and nothing moves after it.
    assert path[60] > path[61]
    assert path[61:].tolist() == pytest.approx([0.65] * (366 - 61), rel=1e-12)
    assert (disclosure["regime_declared_days"], disclosure["regime_applied_days"]) == (61, 61)


def test_a_calm_regime_spans_every_step_of_the_horizon():
    request = bootstrap_request(horizon_days=365, path_count=4096, steps_per_year=252.0)

    baseline = run_direct(request)
    calm = run_direct(request.model_copy(update={"regime": RiskSimulationRegime.CALM}))

    ratio = (terminal_log_dispersion(calm) / terminal_log_dispersion(baseline)).tolist()
    assert ratio == pytest.approx([0.7] * len(ratio), rel=1e-9)
    assert (calm.regime_declared_days, calm.regime_applied_days) == (365, 365)


@pytest.mark.parametrize(
    ("steps_per_year", "block_length_days", "disclosed_days"),
    [
        pytest.param(252.0, 5, 4, id="five-days-are-three-steps-which-span-four-days"),
        pytest.param(365.0, 5, 5, id="five-days-of-a-daily-series"),
        pytest.param(252.0, None, 6, id="the-cube-root-rule-counts-steps-and-discloses-days"),
        pytest.param(365.0, None, 4, id="the-cube-root-rule-of-a-daily-series"),
    ],
)
def test_the_block_length_is_resolved_in_steps_and_disclosed_in_calendar_days(steps_per_year, block_length_days, disclosed_days):
    block = {} if block_length_days is None else {"block_length_days": block_length_days}

    _portfolio, _terminal, _timings, disclosure = resample(bootstrap_history(observations=60, asset_count=1), horizon_days=90, steps_per_year=steps_per_year, **block)

    # 5 days × 252/365 → 3 steps, which span round(3 × 365/252) = 4 days; the cube root of 60
    # observations is 4 steps, which span 6 days of a 252-a-year series.
    assert disclosure["block_length_days"] == disclosed_days


def test_the_worker_publishes_one_band_point_per_calendar_day_whatever_the_steps():
    result = run_direct(bootstrap_request(horizon_days=365, path_count=512, steps_per_year=252.0))

    assert [len(path) for path in result.percentile_paths] == [366, 366, 366]


def test_the_step_frequency_is_part_of_the_simulation_cache_key():
    daily = bootstrap_request(horizon_days=30, path_count=512)
    trading_days = bootstrap_request(horizon_days=30, path_count=512, steps_per_year=252.0)

    assert simulation_cache_key(daily, algorithm_version="simulation@steps") != simulation_cache_key(trading_days, algorithm_version="simulation@steps")


BOOTSTRAP_CONFIGURATIONS = {
    "no-regime": {"horizon_days": 120, "path_count": 2048},
    "crisis-with-a-block-length": {"horizon_days": 500, "path_count": 512, "regime": RiskSimulationRegime.PROLONGED_CRISIS, "block_length_days": 5},
    "shock": {"horizon_days": 61, "path_count": 1024, "regime": RiskSimulationRegime.SHOCK_RECOVERY},
    "calm": {"horizon_days": 90, "path_count": 512, "regime": RiskSimulationRegime.CALM},
}
# Captured through the worker on 10b0b0d48, from the resampler as it stood before `steps_per_year`:
# the (p05, p50, p95) band on the first, middle and last day, the terminal statistics and the
# disclosure. With the frequency unset the engine must still give these numbers. The relative
# tolerance absorbs libm and BLAS differences between machines; the absolute one covers the day-1
# medians, where growth − 1 cancels to 1e-4 and one ulp of the growth is already 3e-12 of the result.
CAPTURED_REL = 1e-12
CAPTURED_ABS = 1e-15
CAPTURED_BEFORE_STEPS = {
    "no-regime": {
        "bands": {
            1: (-0.017147875418507263, 7.174996803871458e-05, 0.016450060605750126),
            60: (-0.10743679198887132, 0.009680407442035133, 0.150395401437865),
            120: (-0.14290783802907317, 0.020701669780889054, 0.23221075242428496),
        },
        "terminal": (0.027372953919993254, 0.11352508096858487, 0.42919921875),
        "disclosure": (9, None, None),
    },
    "crisis-with-a-block-length": {
        "bands": {
            1: (-0.04285002460368267, 0.004116087555147807, 0.042931095637983994),
            250: (-0.5214748663737993, -0.11687598974657865, 0.7032753594111638),
            500: (-0.6313621579696969, -0.14096361115713357, 1.0436286047743275),
        },
        "terminal": (-0.02322925179858988, 0.5509644351880697, 0.638671875),
        "disclosure": (5, 426, 426),
    },
    "shock": {
        "bands": {
            1: (-0.02337869902903633, -0.0066776863793373, 0.009365614265159847),
            30: (-0.25079857351774304, -0.1868603518112133, -0.10430778592799196),
            61: (-0.41619527485431124, -0.34204164739847925, -0.24930159452695597),
        },
        "terminal": (-0.33888212381307414, 0.05240024674243283, 1.0),
        "disclosure": (9, 61, 61),
    },
    "calm": {
        "bands": {
            1: (-0.011752697896862174, 0.00012459598771175084, 0.0117947082250013),
            45: (-0.06433854557413517, 0.004164999795066238, 0.09013845248394589),
            90: (-0.08436606034916302, 0.015656081127116805, 0.14677827783133654),
        },
        "terminal": (0.017385307339057965, 0.06858222271989217, 0.427734375),
        "disclosure": (9, 90, 90),
    },
}


@pytest.mark.parametrize("configuration", list(BOOTSTRAP_CONFIGURATIONS))
def test_with_the_step_frequency_unset_the_bootstrap_gives_the_results_captured_before_it(configuration):
    result = run_direct(bootstrap_request(**BOOTSTRAP_CONFIGURATIONS[configuration]))
    captured = CAPTURED_BEFORE_STEPS[configuration]

    for day, band in captured["bands"].items():
        assert tuple(path[day] for path in result.percentile_paths) == pytest.approx(band, rel=CAPTURED_REL, abs=CAPTURED_ABS), day
    assert (result.terminal_mean_return, result.terminal_volatility, result.probability_of_loss) == pytest.approx(captured["terminal"], rel=CAPTURED_REL, abs=CAPTURED_ABS)
    assert (result.block_length_days, result.regime_declared_days, result.regime_applied_days) == captured["disclosure"]


@pytest.mark.parametrize("configuration", list(BOOTSTRAP_CONFIGURATIONS))
def test_at_365_steps_a_year_the_bootstrap_is_the_unset_one_to_the_byte(configuration):
    unset = resampling_module.run_block_bootstrap(bootstrap_request(**BOOTSTRAP_CONFIGURATIONS[configuration]))
    daily = resampling_module.run_block_bootstrap(bootstrap_request(**BOOTSTRAP_CONFIGURATIONS[configuration], steps_per_year=365.0))

    unset_portfolio, unset_terminal, _unset_timings, unset_disclosure = unset
    daily_portfolio, daily_terminal, _daily_timings, daily_disclosure = daily
    assert daily_portfolio.tobytes() == unset_portfolio.tobytes()
    assert daily_terminal.tobytes() == unset_terminal.tobytes()
    assert daily_disclosure == unset_disclosure


# --- Drift uncertainty -------------------------------------------------------
#
# A band is dispersion *conditional on* an estimated drift, and that drift is a
# sample mean: it carries a standard error of sigma/sqrt(n) which compounds over
# the horizon. Everything below is about the factor that publishes that missing
# part, and about the contract that refuses to publish half of it.

DRIFT_UNCERTAINTY_Z_SCORE = 1.959963984540054


def drift_history() -> dict[int, list[float]]:
    """Two short return series, written out rather than drawn.

    Every expectation below is a closed form recomputed from these exact
    numbers, so a draw would buy nothing here and an unseeded one would turn
    each assertion into a bet on the weather.
    """
    return {
        1: [0.012, -0.008, 0.021, -0.004, 0.015, 0.0, -0.011, 0.009],
        2: [0.004, 0.006, -0.012, 0.011, -0.002, 0.007, 0.003, -0.005],
    }


def drift_projection(
    history: dict[int, list[float]],
    weights: list[float],
) -> list[float]:
    """Weight the two series into one, by hand.

    Deliberately not ``matrix @ weights``: borrowing the estimator's own
    arithmetic would make the closed form agree with the implementation by
    construction rather than by result.
    """
    return [weights[0] * first + weights[1] * second for first, second in zip(history[1], history[2], strict=True)]


def drift_factor_closed_form(
    portfolio_returns: list[float],
    *,
    horizon_observations: int,
) -> float:
    """``exp(z * H * sigma / sqrt(n))`` over the log returns of a projected series."""
    log_returns = np.log1p(
        np.asarray(portfolio_returns, dtype=float),
    )
    sigma = float(log_returns.std(ddof=1))
    return math.exp(
        DRIFT_UNCERTAINTY_Z_SCORE * horizon_observations * sigma / math.sqrt(log_returns.size),
    )


def test_drift_uncertainty_matches_its_closed_form_and_sample_size():
    """Pin the estimate to arithmetic recomputed outside the estimator."""
    history = drift_history()
    weights = [0.6, 0.4]

    factor, observations = estimate_drift_uncertainty(
        history,
        [1, 2],
        weights,
        horizon_observations=93,
    )

    assert factor == pytest.approx(
        drift_factor_closed_form(
            drift_projection(history, weights),
            horizon_observations=93,
        ),
        rel=1e-12,
    )
    assert observations == len(history[1])
    assert factor > 1.0
    # The default quantile is part of the claim, not an implementation detail:
    # the schema calls the field a 95% confidence factor and nothing downstream
    # re-states which quantile produced it.
    explicit, _ = estimate_drift_uncertainty(
        history,
        [1, 2],
        weights,
        horizon_observations=93,
        z_score=DRIFT_UNCERTAINTY_Z_SCORE,
    )
    assert explicit == factor


def test_drift_uncertainty_compounds_with_the_horizon():
    """Estimation error is not a fixed margin: it grows with what it qualifies."""
    history = drift_history()
    weights = [0.6, 0.4]
    factors = {horizon: estimate_drift_uncertainty(history, [1, 2], weights, horizon_observations=horizon)[0] for horizon in (30, 93, 365)}

    assert factors[30] < factors[93] < factors[365]
    # Strictly more than monotone, and the reason the disclosure is a factor
    # rather than a spread: its logarithm is linear in the horizon, so a year is
    # the same error compounded 365 times and not added 365 times.
    assert math.log(factors[93]) == pytest.approx(
        math.log(factors[30]) * (93 / 30),
        rel=1e-12,
    )
    assert math.log(factors[365]) == pytest.approx(
        math.log(factors[30]) * (365 / 30),
        rel=1e-12,
    )


def test_cash_damps_the_drift_uncertainty_instead_of_being_renormalised_away():
    """Separate this definition from the plausible wrong one.

    The weights are the portfolio's own, so a half-invested book arrives with
    weights summing to 0.5 and the estimate shrinks with the exposure.
    Renormalising onto the risky sleeve — the alternative most portfolio code
    reaches for by reflex — would answer about a portfolio the user does not
    hold, and would publish the *same* number for both of these.
    """
    history = drift_history()
    half_invested = [0.3, 0.2]
    fully_invested = [0.6, 0.4]
    assert [weight / sum(half_invested) for weight in half_invested] == pytest.approx(fully_invested)

    damped, damped_observations = estimate_drift_uncertainty(
        history,
        [1, 2],
        half_invested,
        horizon_observations=365,
    )
    invested, invested_observations = estimate_drift_uncertainty(
        history,
        [1, 2],
        fully_invested,
        horizon_observations=365,
    )

    assert damped < invested
    # And by the right amount: half the exposure is half the compounded error,
    # in logs. The tolerance covers the curvature of log1p over these returns
    # (measured: 5e-4 of relative departure), not slack in the claim — the
    # renormalised estimator would land on 1.0 here, not near 0.5.
    assert math.log(damped) / math.log(invested) == pytest.approx(0.5, abs=0.01)
    # Cash changes the exposure, never the sample the drift was estimated from.
    assert damped_observations == invested_observations == len(history[1])


def test_a_flat_history_discloses_no_estimation_error():
    """Zero dispersion is an answer, and the schema's floor is exactly it."""
    flat = {1: [0.001] * 8}

    factor, observations = estimate_drift_uncertainty(
        flat,
        [1],
        [1.0],
        horizon_observations=365,
    )

    assert factor == 1.0
    assert observations == 8
    # `drift_uncertainty_factor` is declared `ge=1`, so the degenerate case sits
    # on the boundary rather than outside it: it is published, not suppressed.
    degenerate = bootstrap_output(
        drift_uncertainty_factor=factor,
        drift_uncertainty_observations=observations,
    )
    assert degenerate.drift_uncertainty_factor == 1.0


def test_drift_uncertainty_refuses_the_questions_it_cannot_answer():
    """Every documented raise, including one it is easy to think unreachable."""
    history = drift_history()

    for horizon in (0, -1):
        with pytest.raises(ValueError, match="positive horizon"):
            estimate_drift_uncertainty(history, [1, 2], [0.6, 0.4], horizon_observations=horizon)

    for weights in ([1.0], [0.5, 0.3, 0.2]):
        with pytest.raises(ValueError, match="one weight per aligned asset"):
            estimate_drift_uncertainty(history, [1, 2], weights, horizon_observations=93)

    # A long-only book cannot reach the third: weights in [0, 1] summing to at
    # most 1 project returns above -1 onto returns above -1. It takes leverage or
    # a short, which is precisely when the log becomes undefined rather than
    # merely large — the guard is about the arithmetic, not about taste.
    levered = {
        1: [-0.6, 0.02, 0.01, -0.03],
        2: [0.3, 0.01, 0.0, 0.02],
    }
    with pytest.raises(ValueError, match="greater than -1"):
        estimate_drift_uncertainty(levered, [1, 2], [2.0, -1.0], horizon_observations=93)


def test_simulation_output_refuses_half_a_drift_uncertainty_disclosure():
    """A factor without its sample size is a number nobody can argue with."""
    silent = bootstrap_output()

    assert silent.drift_uncertainty_factor is None
    assert silent.drift_uncertainty_observations is None

    disclosed = bootstrap_output(
        drift_uncertainty_factor=1.2032,
        drift_uncertainty_observations=93,
    )

    assert disclosed.drift_uncertainty_factor == pytest.approx(1.2032)
    assert disclosed.drift_uncertainty_observations == 93

    for half in (
        {"drift_uncertainty_factor": 1.2032},
        {"drift_uncertainty_observations": 93},
    ):
        with pytest.raises(
            ValidationError,
            match="must disclose both the factor and the observation count",
        ):
            bootstrap_output(**half)

    # The pair validator is about disclosure; the two field bounds are about
    # plausibility. Together they are what lets the renderer treat a factor below
    # 1 or an empty sample as a payload this build cannot have produced — the
    # generated client keeps neither bound, so that inference is the only one
    # left on the other side of the wire.
    with pytest.raises(
        ValidationError,
        match="greater than or equal to 1",
    ):
        bootstrap_output(
            drift_uncertainty_factor=0.9,
            drift_uncertainty_observations=93,
        )
    with pytest.raises(
        ValidationError,
        match="greater than 0",
    ):
        bootstrap_output(
            drift_uncertainty_factor=1.2,
            drift_uncertainty_observations=0,
        )


# ---------------------------------------------------------------------------
# Declared refusals: the two guards whose predicate `validate_params` cannot see
# ---------------------------------------------------------------------------
#
# Both predicates compare a PARAMETER against something only known at execution
# time -- the observation count, the size of the scope. Parameter validation runs
# before either exists, so these cannot be moved upstream: they are reachable by
# construction for any user who picks the combination.
#
# The engine checks both too, but it raises a bare ValueError, which the service
# can only report as a failure of ours. These tests assert the PLUGIN refuses
# first, with a code that names the user's choice -- and each is paired with a
# control that keeps everything else fixed, so a green cannot come from the
# request being malformed for some unrelated reason.


def _returns_by_asset(asset_count: int, observations: int) -> dict[int, list[float]]:
    """Synthetic returns. Only the SHAPE is under test, never the values."""
    return {asset_id: [0.001] * observations for asset_id in range(1, asset_count + 1)}


def test_bootstrap_refuses_a_block_longer_than_the_history_as_invalid_parameters():
    params = SimulationParams.model_validate({"process": "block_bootstrap", "block_length_days": 900})
    asset_ids = (1,)

    with pytest.raises(RiskUnavailableError) as refused:
        SimulationAnalytic._build_bootstrap_request(params, _returns_by_asset(1, 30), asset_ids, [1.0], 0.0)

    # INVALID_PARAMETERS, not INSUFFICIENT_HISTORY: the user can lower the block
    # length, which is an action available to them; "find more history" usually
    # is not. The code has to name the door that is actually open.
    assert refused.value.code == RiskErrorCode.INVALID_PARAMETERS
    # No step frequency is given, so the builder counts 365 a year: 900 calendar days
    # are 900 observations, compared with the 30 the history holds.
    assert refused.value.details == {"block_length_days": 900, "block_length_observations": 900, "observations": 30}

    # CONTROL -- the identical parameters against a longer history are accepted.
    # Without this the test above would also pass if the builder refused every
    # bootstrap request, which is a different bug wearing the same green.
    request, observations = SimulationAnalytic._build_bootstrap_request(params, _returns_by_asset(1, 1000), asset_ids, [1.0], 0.0)
    assert observations == 1000
    assert request.block_length_days == 900


def test_parametric_qmc_refuses_an_oversized_sobol_dimension_as_resource_limit():
    horizon = 3650
    params = SimulationParams.model_validate(
        {
            "process": "gbm",
            "sampling_method": "qmc",
            "horizon_days": horizon,
            "path_count": 8192,
        }
    )
    # Derived from the live limit rather than hard-coded: if MAX_SOBOL_DIMENSION
    # moves, this test follows it instead of turning red for the wrong reason.
    largest_allowed = MAX_SOBOL_DIMENSION // horizon
    over = largest_allowed + 1

    with pytest.raises(RiskUnavailableError) as refused:
        SimulationAnalytic._build_parametric_request(
            params,
            _returns_by_asset(over, 60),
            [1.0 / over] * over,
            0.0,
            annualization_factor=252.0,
        )

    assert refused.value.code == RiskErrorCode.RESOURCE_LIMIT
    assert refused.value.details["limit"] == MAX_SOBOL_DIMENSION
    assert refused.value.details["required_dimension"] == over * horizon
    assert refused.value.details["horizon_days"] == horizon
    # D379: like every size limit, the refusal names its metric and the remedy that
    # works. Sobol's dimension is positions x horizon and the paths play no part in
    # it, so the cure is a shorter horizon or MC sampling -- never fewer paths. The
    # four keys it already carried stay, beside the three every size limit shares.
    assert refused.value.details == {
        "required_dimension": over * horizon,
        "limit": MAX_SOBOL_DIMENSION,
        "assets": over,
        "horizon_days": horizon,
        "metric": "sobol_dimension",
        "actual": over * horizon,
        "remedy": "horizon_or_sampling",
    }

    # CONTROL: one asset fewer, everything else identical, is accepted. The only
    # moving part between the refusal and this line is the size of the scope.
    request, _observations = SimulationAnalytic._build_parametric_request(
        params,
        _returns_by_asset(largest_allowed, 60),
        [1.0 / largest_allowed] * largest_allowed,
        0.0,
        annualization_factor=252.0,
    )
    assert len(request.asset_ids) == largest_allowed
    assert request.horizon_days == horizon


def test_mc_sampling_is_not_subject_to_the_sobol_dimension_limit():
    """The Sobol ceiling belongs to QMC, and must not leak onto the MC path.

    Guarding unconditionally would refuse a scope that the engine runs happily,
    which is the mirror of the defect being fixed: a working request reported as
    a limit. The engine applies the check only under QMC, so the plugin must too.
    """
    horizon = 3650
    params = SimulationParams.model_validate({"process": "gbm", "sampling_method": "mc", "horizon_days": horizon})
    over = (MAX_SOBOL_DIMENSION // horizon) + 1

    request, _observations = SimulationAnalytic._build_parametric_request(
        params,
        _returns_by_asset(over, 60),
        [1.0 / over] * over,
        0.0,
        annualization_factor=252.0,
    )
    assert len(request.asset_ids) * request.horizon_days > MAX_SOBOL_DIMENSION


# ---------------------------------------------------------------------------
# Size limits (developer's decision D379, 07/10/2026)
# ---------------------------------------------------------------------------
#
# A simulation too large to run says so: every size limit is RESOURCE_LIMIT --
# never INVALID_PARAMETERS ("your parameters are wrong") nor EXECUTION_FAILED
# ("we failed") -- and its details name the limit that was hit and the remedy
# that actually works. `remedy` is a wire contract with the frontend, which turns
# it into a sentence, so its literal values are asserted, never paraphrased.
#
# Positions and observations are both capped by the engine's own model. Until
# D379 the builders constructed the request with no guard of their own, so a
# scope over either cap failed pydantic validation outside the plugin's `try`: a
# ValidationError escaped, and the service could only log a traceback and answer
# EXECUTION_FAILED. The builders now refuse first, before any request exists.
#
# `MAX_SIMULATION_ASSETS` is read inside the test bodies, never imported at the
# top: the constant is itself part of the contract under test, and a missing name
# must fail the tests that use it, not the collection of this whole file.


def _build_request_for(process: RiskSimulationProcess, asset_count: int, observations: int = 30):
    """Call the builder `execute` dispatches to for `process`, on an equally weighted, fully invested scope."""
    returns_by_asset = _returns_by_asset(asset_count, observations)
    weights = [1.0 / asset_count] * asset_count
    if process == RiskSimulationProcess.BLOCK_BOOTSTRAP:
        params = SimulationParams.model_validate({"process": "block_bootstrap"})
        return SimulationAnalytic._build_bootstrap_request(params, returns_by_asset, tuple(returns_by_asset), weights, 0.0)
    params = SimulationParams.model_validate({"process": "gbm", "sampling_method": "mc"})
    return SimulationAnalytic._build_parametric_request(params, returns_by_asset, weights, 0.0, annualization_factor=252.0)


@pytest.mark.parametrize(
    "process",
    [
        pytest.param(RiskSimulationProcess.BLOCK_BOOTSTRAP, id="block-bootstrap"),
        pytest.param(RiskSimulationProcess.GBM, id="gbm"),
    ],
)
def test_both_builders_refuse_more_positions_than_the_engine_carries_as_resource_limit(process):
    limit = simulation_models.MAX_SIMULATION_ASSETS
    over = limit + 1

    with pytest.raises(RiskUnavailableError) as refused:
        _build_request_for(process, over)

    # `positions`: no setting makes one position too many fit -- not fewer paths,
    # not a shorter horizon, not a shorter period -- so the remedy names the scope.
    assert refused.value.code == RiskErrorCode.RESOURCE_LIMIT
    assert refused.value.details == {"metric": "assets", "actual": over, "limit": limit, "remedy": "positions"}

    # CONTROL -- one position fewer, same process, same history, is built. The only
    # moving part between the refusal and this line is the size of the scope.
    request, _observations = _build_request_for(process, limit)
    assert request.process == process
    assert len(request.asset_ids) == limit


def test_bootstrap_refuses_more_observations_than_the_engine_carries_as_resource_limit():
    params = SimulationParams.model_validate({"process": "block_bootstrap"})
    over = MAX_HISTORY_OBSERVATIONS + 1

    with pytest.raises(RiskUnavailableError) as refused:
        SimulationAnalytic._build_bootstrap_request(params, _returns_by_asset(1, over), (1,), [1.0], 0.0)

    # `period`: the bootstrap carries the aligned history across the process boundary
    # whole, and a shorter analysis period is what holds fewer observations. Fewer
    # paths or a shorter horizon would change nothing here.
    assert refused.value.code == RiskErrorCode.RESOURCE_LIMIT
    assert refused.value.details == {"metric": "observations", "actual": over, "limit": MAX_HISTORY_OBSERVATIONS, "remedy": "period"}

    # CONTROL -- exactly the limit, the same asset and parameters, is built with the
    # whole history: the ceiling is inclusive, and nothing is trimmed to reach it.
    request, observations = SimulationAnalytic._build_bootstrap_request(params, _returns_by_asset(1, MAX_HISTORY_OBSERVATIONS), (1,), [1.0], 0.0)
    assert observations == MAX_HISTORY_OBSERVATIONS
    assert len(request.historical_returns) == MAX_HISTORY_OBSERVATIONS


def test_gbm_is_not_subject_to_the_bootstrap_observation_limit():
    """The observation ceiling belongs to the process that carries the history.

    GBM sends estimated drifts and a covariance across the boundary, whatever the
    length of the history they come from. Inheriting the bootstrap's ceiling would
    refuse a request the engine runs happily -- a working run reported as a limit,
    the mirror of the defect being fixed. Green before D379, and it must stay so.
    """
    request, observations = _build_request_for(RiskSimulationProcess.GBM, 1, MAX_HISTORY_OBSERVATIONS + 1)

    assert observations == MAX_HISTORY_OBSERVATIONS + 1
    assert request.historical_returns is None


def _diagonal_gbm_payload(asset_count: int) -> dict:
    """`engine_request` overrides for `asset_count` uncorrelated, equally weighted positions."""
    return {
        "asset_ids": list(range(1, asset_count + 1)),
        "annual_drifts": [0.03] * asset_count,
        "annual_covariance": [[0.04 if row == column else 0.0 for column in range(asset_count)] for row in range(asset_count)],
        "weights": [1 / asset_count] * asset_count,
        "cash_weight": 0,
    }


def test_the_engine_contract_refuses_the_positions_the_plugin_guard_refuses():
    """Defence in depth, on one constant.

    The plugin refuses first, with a code the user can act on. The model refuses
    anyway, so a caller that bypasses the plugin still cannot hand the worker a
    scope no guard was written for. The two halves below go red if the guard's
    limit and the model's `max_length` ever drift apart, in either direction.
    """
    limit = simulation_models.MAX_SIMULATION_ASSETS

    with pytest.raises(ValidationError) as refused:
        engine_request(**_diagonal_gbm_payload(limit + 1))

    # Refused for the number of positions alone, not for another flaw of the payload.
    assert [(error["loc"], error["type"]) for error in refused.value.errors()] == [(("asset_ids",), "too_long")]

    # CONTROL -- the same payload one position smaller is a valid request.
    assert len(engine_request(**_diagonal_gbm_payload(limit)).asset_ids) == limit


def test_the_ceilings_cited_to_the_user_are_pinned():
    """Pinned like `largest == 66`: the user reads these two ceilings as numbers.

    Every limit test derives its threshold from these constants, so moving one keeps
    the guards and the model in step, and those tests follow it in silence. The user,
    though, is told the values themselves. A change here must be deliberate, and must
    carry the texts that cite it.
    """
    # The frontend's sentence for the `positions` remedy cites 100 in all four catalogues:
    # EN «at most 100 holdings», IT «al massimo 100 posizioni», FR «au plus 100 positions»,
    # ES «como máximo 100 posiciones» (`levelHelpers.test.ts` pins that 100 in each one).
    # The CHANGELOG line cites 100 holdings.
    assert simulation_models.MAX_SIMULATION_ASSETS == 100
    # The same CHANGELOG line cites 5,000 observations.
    assert simulation_models.MAX_HISTORY_OBSERVATIONS == 5000
