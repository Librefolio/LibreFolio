"""Mathematical and process tests for Riskfolio optimization."""

from __future__ import annotations

import asyncio
import math
import os

import numpy as np
import pytest
from pydantic import ValidationError

from backend.app.schemas.risk import (
    RiskCovarianceEstimator,
    RiskOptimizationStrategy,
)
from backend.app.services.risk.quant import (
    optimization_engine as optimization_engine_module,
)
from backend.app.services.risk.quant.optimization_engine import (
    clear_optimization_cache,
    run_optimization,
)
from backend.app.services.risk.quant.optimization_models import (
    OptimizationEngineRequest,
    OptimizationEngineResult,
    optimization_cache_key,
)
from backend.app.services.risk.quant.riskfolio_worker import (
    execute_optimization_job,
)
from backend.app.services.risk.quant.spawn_worker import SpawnWorkerResult
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)


def return_fixture() -> list[list[float]]:
    generator = np.random.default_rng(20260727)
    means = np.asarray([0.00035, 0.00055, 0.00025])
    covariance = np.asarray(
        [
            [0.00012, 0.000025, -0.00001],
            [0.000025, 0.00025, 0.000035],
            [-0.00001, 0.000035, 0.00008],
        ],
    )
    return generator.multivariate_normal(
        means,
        covariance,
        size=600,
    ).tolist()


def optimization_request(
    **overrides,
) -> OptimizationEngineRequest:
    payload = {
        "asset_ids": [101, 102, 103],
        "returns": return_fixture(),
        "annualization_factor": 252.0,
        "strategy": "min_risk",
        "covariance_estimator": "historical",
        "risk_free_annual_rate": 0.02,
        "min_weight": 0.0,
        "max_weight": 1.0,
        "include_frontier": False,
        "frontier_points": 8,
        "include_sensitivity": False,
        "solver": "clarabel",
    }
    payload.update(overrides)
    return OptimizationEngineRequest.model_validate(payload)


def run_direct(
    request: OptimizationEngineRequest,
) -> OptimizationEngineResult:
    return OptimizationEngineResult.model_validate(
        execute_optimization_job(
            request.model_dump(mode="json"),
        ),
    )


def result_arrays(
    result: OptimizationEngineResult,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    weights = np.asarray(
        [item.weight for item in result.weights],
    )
    expected_returns = np.asarray(
        result.period_expected_returns,
    )
    covariance = np.asarray(result.period_covariance)
    return weights, expected_returns, covariance


def test_optimization_contract_is_strict_and_content_keyed():
    request = optimization_request(
        min_weight=0.05,
        max_weight=0.8,
    )
    key = optimization_cache_key(
        request,
        algorithm_version="portfolio_optimization@1",
    )

    assert len(key) == 64
    assert key == optimization_cache_key(
        OptimizationEngineRequest.model_validate_json(
            request.model_dump_json(),
        ),
        algorithm_version="portfolio_optimization@1",
    )
    assert key != optimization_cache_key(
        request.model_copy(
            update={
                "strategy": (RiskOptimizationStrategy.MAX_SHARPE),
            },
        ),
        algorithm_version="portfolio_optimization@1",
    )

    with pytest.raises(ValidationError, match="unique"):
        optimization_request(asset_ids=[101, 101, 103])
    with pytest.raises(ValidationError, match="budget infeasible"):
        optimization_request(max_weight=0.3)
    with pytest.raises(ValidationError, match="budget infeasible"):
        optimization_request(min_weight=0.4)
    with pytest.raises(ValidationError):
        optimization_request(solver="unapproved")


@pytest.mark.parametrize(
    "strategy",
    list(RiskOptimizationStrategy),
)
def test_riskfolio_strategies_are_deterministic_and_feasible(
    strategy,
):
    request = optimization_request(strategy=strategy)
    first = run_direct(request)
    second = run_direct(request)
    weights, _means, covariance = result_arrays(first)

    assert first == second
    assert np.isfinite(weights).all()
    assert weights.sum() == pytest.approx(1.0, abs=1e-7)
    assert np.min(weights) >= request.min_weight - 1e-7
    assert np.max(weights) <= request.max_weight + 1e-7
    assert np.allclose(
        covariance,
        covariance.T,
        rtol=0,
        atol=1e-12,
    )
    assert np.linalg.eigvalsh(covariance).min() >= -1e-10
    assert sum(item.percentage_risk_contribution for item in first.weights) == pytest.approx(1.0, abs=1e-7)


def test_minimum_risk_beats_equal_weight_and_feasible_vertices():
    result = run_direct(
        optimization_request(
            strategy=RiskOptimizationStrategy.MIN_RISK,
        ),
    )
    weights, _means, covariance = result_arrays(result)
    optimized_variance = float(weights @ covariance @ weights)
    equal_weights = np.full(len(weights), 1 / len(weights))
    candidate_variances = [
        float(equal_weights @ covariance @ equal_weights),
        *[float(covariance[index, index]) for index in range(len(weights))],
    ]

    assert optimized_variance <= min(candidate_variances) + 1e-10


def test_maximum_sharpe_matches_independent_objective():
    request = optimization_request(
        strategy=RiskOptimizationStrategy.MAX_SHARPE,
        risk_free_annual_rate=0.02,
    )
    result = run_direct(request)
    weights, means, covariance = result_arrays(result)
    period_return = float(means @ weights)
    period_volatility = math.sqrt(
        float(weights @ covariance @ weights),
    )
    period_risk_free = math.expm1(
        math.log1p(request.risk_free_annual_rate) / request.annualization_factor,
    )
    expected_sharpe = (period_return - period_risk_free) / period_volatility * math.sqrt(request.annualization_factor)
    equal_weights = np.full(len(weights), 1 / len(weights))
    equal_sharpe = (
        (float(means @ equal_weights) - period_risk_free)
        / math.sqrt(
            float(equal_weights @ covariance @ equal_weights),
        )
        * math.sqrt(request.annualization_factor)
    )

    assert result.sharpe_ratio == pytest.approx(
        expected_sharpe,
        rel=1e-10,
        abs=1e-12,
    )
    assert expected_sharpe >= equal_sharpe - 1e-7


def test_risk_parity_equalizes_percentage_contributions():
    result = run_direct(
        optimization_request(
            strategy=RiskOptimizationStrategy.RISK_PARITY,
        ),
    )
    contributions = np.asarray(
        [item.percentage_risk_contribution for item in result.weights],
    )

    assert contributions == pytest.approx(
        np.full(3, 1 / 3),
        abs=2e-4,
    )


def test_frontier_and_covariance_sensitivity_are_valid():
    request = optimization_request(
        include_frontier=True,
        frontier_points=8,
        include_sensitivity=True,
    )
    result = run_direct(request)

    assert len(result.frontier) == 8
    assert len(result.sensitivity) == 2
    volatilities = [point.annual_volatility for point in result.frontier]
    assert volatilities == sorted(volatilities)
    for point in result.frontier:
        assert sum(item.weight for item in point.weights) == pytest.approx(1.0, abs=1e-6)
    for index, point in enumerate(result.frontier):
        for other_index, other in enumerate(result.frontier):
            if index == other_index:
                continue
            dominates = other.annual_volatility <= point.annual_volatility - 1e-8 and other.expected_annual_return >= point.expected_annual_return + 1e-8
            assert not dominates

    covariance_results = {
        estimator: run_direct(
            optimization_request(
                covariance_estimator=estimator,
            ),
        )
        for estimator in RiskCovarianceEstimator
    }
    covariance_matrices = [np.asarray(item.period_covariance) for item in covariance_results.values()]
    assert all(np.linalg.eigvalsh(covariance).min() >= -1e-10 for covariance in covariance_matrices)
    assert not np.allclose(
        covariance_matrices[0],
        covariance_matrices[1],
    )
    assert not np.allclose(
        covariance_matrices[0],
        covariance_matrices[2],
    )


@pytest.mark.asyncio
async def test_spawned_riskfolio_matches_direct_result_and_cache():
    clear_optimization_cache()
    request = optimization_request(
        strategy=RiskOptimizationStrategy.RISK_PARITY,
    )
    direct = run_direct(request)
    try:
        first, first_hit, worker = await run_optimization(
            request,
            algorithm_version="portfolio_optimization@1",
        )
        second, second_hit, cached_worker = await run_optimization(
            request,
            algorithm_version="portfolio_optimization@1",
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
async def test_cancelled_cache_leader_releases_optimization_followers(
    monkeypatch,
):
    clear_optimization_cache()
    request = optimization_request()
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
        optimization_engine_module,
        "get_optimization_worker_pool",
        lambda: pool,
    )
    leader = asyncio.create_task(
        run_optimization(
            request,
            algorithm_version="portfolio_optimization@cancel-leader",
        ),
    )
    await pool.started.wait()
    follower = asyncio.create_task(
        run_optimization(
            request,
            algorithm_version="portfolio_optimization@cancel-leader",
        ),
    )
    await asyncio.sleep(0)
    leader.cancel()

    with pytest.raises(asyncio.CancelledError):
        await leader
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(follower, timeout=0.5)

    pool.release.set()
    recovered, cache_hit, worker = await run_optimization(
        request,
        algorithm_version="portfolio_optimization@cancel-leader",
    )

    assert recovered == expected
    assert cache_hit is False
    assert worker is not None
    assert pool.calls == 2
