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
    horizon_days: int,
) -> float:
    """``exp(z * H * sigma / sqrt(n))`` over the log returns of a projected series."""
    log_returns = np.log1p(
        np.asarray(portfolio_returns, dtype=float),
    )
    sigma = float(log_returns.std(ddof=1))
    return math.exp(
        DRIFT_UNCERTAINTY_Z_SCORE * horizon_days * sigma / math.sqrt(log_returns.size),
    )


def test_drift_uncertainty_matches_its_closed_form_and_sample_size():
    """Pin the estimate to arithmetic recomputed outside the estimator."""
    history = drift_history()
    weights = [0.6, 0.4]

    factor, observations = estimate_drift_uncertainty(
        history,
        [1, 2],
        weights,
        horizon_days=93,
    )

    assert factor == pytest.approx(
        drift_factor_closed_form(
            drift_projection(history, weights),
            horizon_days=93,
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
        horizon_days=93,
        z_score=DRIFT_UNCERTAINTY_Z_SCORE,
    )
    assert explicit == factor


def test_drift_uncertainty_compounds_with_the_horizon():
    """Estimation error is not a fixed margin: it grows with what it qualifies."""
    history = drift_history()
    weights = [0.6, 0.4]
    factors = {horizon: estimate_drift_uncertainty(history, [1, 2], weights, horizon_days=horizon)[0] for horizon in (30, 93, 365)}

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
        horizon_days=365,
    )
    invested, invested_observations = estimate_drift_uncertainty(
        history,
        [1, 2],
        fully_invested,
        horizon_days=365,
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
        horizon_days=365,
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
            estimate_drift_uncertainty(history, [1, 2], [0.6, 0.4], horizon_days=horizon)

    for weights in ([1.0], [0.5, 0.3, 0.2]):
        with pytest.raises(ValueError, match="one weight per aligned asset"):
            estimate_drift_uncertainty(history, [1, 2], weights, horizon_days=93)

    # A long-only book cannot reach the third: weights in [0, 1] summing to at
    # most 1 project returns above -1 onto returns above -1. It takes leverage or
    # a short, which is precisely when the log becomes undefined rather than
    # merely large — the guard is about the arithmetic, not about taste.
    levered = {
        1: [-0.6, 0.02, 0.01, -0.03],
        2: [0.3, 0.01, 0.0, 0.02],
    }
    with pytest.raises(ValueError, match="greater than -1"):
        estimate_drift_uncertainty(levered, [1, 2], [2.0, -1.0], horizon_days=93)


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
    assert refused.value.details == {"block_length_days": 900, "observations": 30}

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
