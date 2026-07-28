#!/usr/bin/env python3
"""Benchmark persistent spawned QuantLib and Riskfolio workers."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import platform
import resource
import statistics
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np
from pydantic import ValidationError

SCRIPT_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = SCRIPT_PATH.parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.services.risk.quant.engine import (
    MAX_PORTFOLIO_CELLS,
    MAX_STOCHASTIC_CELLS,
    SimulationResourceLimitError,
    clear_simulation_cache,
    run_simulation,
    validate_resource_budget,
)
from backend.app.services.risk.quant.models import (
    SimulationEngineRequest,
)
from backend.app.services.risk.quant.optimization_models import (
    OptimizationEngineRequest,
)
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerPool,
    SpawnWorkerTimeoutError,
)
from backend.app.services.risk.quant.workers import (
    shutdown_quant_worker_pools,
)

DEFAULT_OUTPUT = Path(
    "/tmp/libreFolio_quant_worker_benchmark.json",
)
ASSET_COUNTS = (1, 5, 20, 50)
HORIZONS = {
    "1y": 365,
    "5y": 1825,
    "10y": 3650,
}
PATH_COUNTS = {
    "1k": {"mc": 1000, "qmc": 1024},
    "10k": {"mc": 10_000, "qmc": 8192},
    "100k": {"mc": 100_000, "qmc": 65_536},
}
SIMULATION_HANDLER = "backend.app.services.risk.quant." "quantlib_worker:execute_simulation_job"
OPTIMIZATION_HANDLER = "backend.app.services.risk.quant." "riskfolio_worker:execute_optimization_job"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=2,
    )
    return parser.parse_args()


def peak_rss_bytes() -> int:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def synthetic_covariance(asset_count: int) -> np.ndarray:
    volatilities = np.linspace(0.1, 0.3, asset_count)
    loadings = np.linspace(0.2, 0.6, asset_count)
    correlation = np.outer(loadings, loadings) + np.diag(1 - loadings**2)
    return np.outer(volatilities, volatilities) * correlation


def simulation_request(
    *,
    assets: int,
    paths: int,
    horizon_days: int,
    sampling: str,
    seed: int,
    diagnostics: bool = False,
) -> SimulationEngineRequest:
    covariance = synthetic_covariance(assets)
    return SimulationEngineRequest(
        sampling=sampling,
        asset_ids=list(range(1, assets + 1)),
        annual_drifts=np.linspace(
            0.02,
            0.07,
            assets,
        ).tolist(),
        annual_covariance=covariance.tolist(),
        weights=[0.95 / assets] * assets,
        cash_weight=0.05,
        horizon_days=horizon_days,
        paths=paths,
        seed=seed,
        diagnostics=diagnostics,
    )


def optimization_request(
    *,
    strategy: str = "min_risk",
    estimator: str = "historical",
) -> OptimizationEngineRequest:
    rows = [
        [
            0.0004 + 0.01 * math.sin(index / 7),
            0.0006 + 0.012 * math.cos(index / 11),
            0.0003 + 0.008 * math.sin(index / 5 + 1),
        ]
        for index in range(300)
    ]
    return OptimizationEngineRequest(
        asset_ids=[101, 102, 103],
        returns=rows,
        annualization_factor=252,
        strategy=strategy,
        covariance_estimator=estimator,
        risk_free_annual_rate=0.02,
        min_weight=0.05,
        max_weight=0.8,
    )


def result_digest(payload: dict[str, Any]) -> str:
    stable = dict(payload)
    stable.pop("diagnostics", None)
    encoded = json.dumps(
        stable,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def worker_metrics(result) -> dict[str, Any]:
    return {
        "worker_pid": result.worker_pid,
        "cold_start": result.cold_start,
        "queue_wait_seconds": result.queue_wait_seconds,
        "execution_seconds": result.execution_seconds,
        "round_trip_seconds": result.round_trip_seconds,
        "ipc_startup_seconds": (result.round_trip_seconds - result.execution_seconds),
        "peak_rss_bytes": result.peak_rss_bytes,
    }


def classify_matrix() -> list[dict[str, Any]]:
    rows = []
    for assets in ASSET_COUNTS:
        for path_tier, path_values in PATH_COUNTS.items():
            for horizon_tier, horizon_days in HORIZONS.items():
                for sampling, paths in path_values.items():
                    row = {
                        "assets": assets,
                        "path_tier": path_tier,
                        "paths": paths,
                        "horizon_tier": horizon_tier,
                        "horizon_days": horizon_days,
                        "sampling": sampling,
                    }
                    try:
                        request = simulation_request(
                            assets=assets,
                            paths=paths,
                            horizon_days=horizon_days,
                            sampling=sampling,
                            seed=4096,
                        )
                        validate_resource_budget(request)
                    except ValidationError as exc:
                        row["status"] = "dimension_limit"
                        row["reason"] = str(exc)
                    except SimulationResourceLimitError as exc:
                        row["status"] = "resource_limit"
                        row["reason"] = str(exc)
                    else:
                        row["status"] = "accepted"
                    rows.append(row)
    return rows


async def benchmark_persistent_case(
    label: str,
    request: SimulationEngineRequest,
) -> dict[str, Any]:
    pool = SpawnWorkerPool(
        name=f"benchmark-{label}",
        handler_path=SIMULATION_HANDLER,
        workers=1,
        queue_capacity=1,
        timeout_seconds=120,
    )
    try:
        cold = await pool.submit(
            request.model_dump(mode="json"),
        )
        warm = await pool.submit(
            request.model_dump(mode="json"),
        )
    finally:
        await pool.shutdown()
    return {
        "label": label,
        "assets": len(request.asset_ids),
        "paths": request.paths,
        "horizon_days": request.horizon_days,
        "sampling": request.sampling.value,
        "equivalent": (result_digest(cold.payload) == result_digest(warm.payload)),
        "cold": worker_metrics(cold),
        "warm": worker_metrics(warm),
        "engine_stages": warm.payload.get("diagnostics"),
    }


async def benchmark_simulation_cache() -> dict[str, Any]:
    await shutdown_quant_worker_pools()
    clear_simulation_cache()
    request = simulation_request(
        assets=5,
        paths=2048,
        horizon_days=90,
        sampling="mc",
        seed=123456,
    )
    started = perf_counter()
    first, first_hit, worker = await run_simulation(
        request,
        algorithm_version="benchmark-quantlib-1.43",
    )
    first_seconds = perf_counter() - started
    started = perf_counter()
    second, second_hit, cached_worker = await run_simulation(
        request,
        algorithm_version="benchmark-quantlib-1.43",
    )
    cache_seconds = perf_counter() - started
    await shutdown_quant_worker_pools()
    return {
        "first_seconds": first_seconds,
        "cache_hit_seconds": cache_seconds,
        "first_hit": first_hit,
        "second_hit": second_hit,
        "equivalent": first == second,
        "worker": (worker_metrics(worker) if worker is not None else None),
        "cache_worker": cached_worker,
    }


async def benchmark_simulation_concurrency(
    *,
    workers: int,
) -> dict[str, Any]:
    requests = [
        simulation_request(
            assets=5,
            paths=2048,
            horizon_days=90,
            sampling="mc",
            seed=123456 + index,
        )
        for index in range(4)
    ]
    pool = SpawnWorkerPool(
        name=f"benchmark-simulation-{workers}",
        handler_path=SIMULATION_HANDLER,
        workers=workers,
        queue_capacity=4,
        timeout_seconds=120,
    )
    warmup_request = simulation_request(
        assets=1,
        paths=256,
        horizon_days=10,
        sampling="mc",
        seed=1000,
    )
    warmup = await asyncio.gather(
        *(
            pool.submit(
                warmup_request.model_copy(
                    update={"seed": 1000 + index},
                ).model_dump(mode="json"),
            )
            for index in range(workers)
        ),
    )
    started = perf_counter()
    try:
        results = await asyncio.gather(
            *(pool.submit(request.model_dump(mode="json")) for request in requests),
        )
        wall_seconds = perf_counter() - started
    finally:
        await pool.shutdown()
    rss_by_pid = {}
    for result in results:
        rss_by_pid[result.worker_pid] = max(
            rss_by_pid.get(result.worker_pid, 0),
            result.peak_rss_bytes,
        )
    return {
        "workers": workers,
        "wall_seconds": wall_seconds,
        "digests": [result_digest(result.payload) for result in results],
        "worker_pids": sorted(rss_by_pid),
        "combined_peak_rss_bytes": sum(rss_by_pid.values()),
        "warmup": [worker_metrics(result) for result in warmup],
        "jobs": [worker_metrics(result) for result in results],
    }


async def benchmark_timeout_recycle() -> dict[str, Any]:
    pool = SpawnWorkerPool(
        name="benchmark-timeout",
        handler_path=SIMULATION_HANDLER,
        workers=1,
        queue_capacity=0,
        timeout_seconds=0.1,
    )
    slow = simulation_request(
        assets=5,
        paths=8192,
        horizon_days=365,
        sampling="mc",
        seed=123456,
    )
    task = asyncio.create_task(
        pool.submit(slow.model_dump(mode="json")),
    )
    await asyncio.sleep(0.05)
    timed_out_pid = next(iter(pool.process_ids), None)
    timed_out = False
    try:
        await task
    except SpawnWorkerTimeoutError:
        timed_out = True
    pool.timeout_seconds = 30
    recovered = await pool.submit(
        simulation_request(
            assets=1,
            paths=256,
            horizon_days=10,
            sampling="mc",
            seed=1,
        ).model_dump(mode="json"),
    )
    await pool.shutdown()
    return {
        "timed_out": timed_out,
        "timed_out_pid": timed_out_pid,
        "recovered_pid": recovered.worker_pid,
        "worker_recycled": (timed_out_pid is not None and recovered.worker_pid != timed_out_pid),
        "recovery": worker_metrics(recovered),
    }


async def benchmark_optimization_persistence() -> dict[str, Any]:
    request = optimization_request()
    pool = SpawnWorkerPool(
        name="benchmark-optimization",
        handler_path=OPTIMIZATION_HANDLER,
        workers=1,
        queue_capacity=1,
        timeout_seconds=60,
    )
    try:
        cold = await pool.submit(
            request.model_dump(mode="json"),
        )
        warm = await pool.submit(
            request.model_dump(mode="json"),
        )
    finally:
        await pool.shutdown()
    return {
        "equivalent": (result_digest(cold.payload) == result_digest(warm.payload)),
        "cold": worker_metrics(cold),
        "warm": worker_metrics(warm),
    }


async def benchmark_optimization_concurrency(
    *,
    workers: int,
) -> dict[str, Any]:
    requests = [
        optimization_request(
            strategy=strategy,
            estimator=estimator,
        )
        for strategy, estimator in (
            ("min_risk", "historical"),
            ("max_sharpe", "historical"),
            ("risk_parity", "ledoit_wolf"),
            ("min_risk", "oas"),
        )
    ]
    pool = SpawnWorkerPool(
        name=f"benchmark-optimization-{workers}",
        handler_path=OPTIMIZATION_HANDLER,
        workers=workers,
        queue_capacity=4,
        timeout_seconds=60,
    )
    warmup_request = optimization_request()
    warmup = await asyncio.gather(
        *(
            pool.submit(
                warmup_request.model_dump(mode="json"),
            )
            for _index in range(workers)
        ),
    )
    started = perf_counter()
    try:
        results = await asyncio.gather(
            *(pool.submit(request.model_dump(mode="json")) for request in requests),
        )
        wall_seconds = perf_counter() - started
    finally:
        await pool.shutdown()
    rss_by_pid = {}
    for result in results:
        rss_by_pid[result.worker_pid] = max(
            rss_by_pid.get(result.worker_pid, 0),
            result.peak_rss_bytes,
        )
    return {
        "workers": workers,
        "wall_seconds": wall_seconds,
        "digests": [result_digest(result.payload) for result in results],
        "worker_pids": sorted(rss_by_pid),
        "combined_peak_rss_bytes": sum(rss_by_pid.values()),
        "warmup": [worker_metrics(result) for result in warmup],
        "jobs": [worker_metrics(result) for result in results],
    }


async def run_benchmark(repeats: int) -> dict[str, Any]:
    matrix = classify_matrix()
    representative = []
    for label, request in (
        (
            "small_mc",
            simulation_request(
                assets=1,
                paths=1024,
                horizon_days=30,
                sampling="mc",
                seed=123456,
                diagnostics=True,
            ),
        ),
        (
            "small_qmc",
            simulation_request(
                assets=1,
                paths=1024,
                horizon_days=30,
                sampling="qmc",
                seed=4096,
                diagnostics=True,
            ),
        ),
        (
            "medium_mc",
            simulation_request(
                assets=5,
                paths=4096,
                horizon_days=90,
                sampling="mc",
                seed=123456,
                diagnostics=True,
            ),
        ),
        (
            "medium_qmc",
            simulation_request(
                assets=5,
                paths=4096,
                horizon_days=90,
                sampling="qmc",
                seed=4096,
                diagnostics=True,
            ),
        ),
        (
            "long_mc",
            simulation_request(
                assets=1,
                paths=2048,
                horizon_days=365,
                sampling="mc",
                seed=123456,
                diagnostics=True,
            ),
        ),
    ):
        representative.append(
            await benchmark_persistent_case(label, request),
        )

    simulation_concurrency = []
    optimization_concurrency = []
    for _repeat in range(repeats):
        simulation_concurrency.append(
            {
                "one_worker": (
                    await benchmark_simulation_concurrency(
                        workers=1,
                    )
                ),
                "two_workers": (
                    await benchmark_simulation_concurrency(
                        workers=2,
                    )
                ),
            },
        )
        optimization_concurrency.append(
            {
                "one_worker": (
                    await benchmark_optimization_concurrency(
                        workers=1,
                    )
                ),
                "two_workers": (
                    await benchmark_optimization_concurrency(
                        workers=2,
                    )
                ),
            },
        )

    simulation_speedups = [run["one_worker"]["wall_seconds"] / run["two_workers"]["wall_seconds"] for run in simulation_concurrency]
    optimization_speedups = [run["one_worker"]["wall_seconds"] / run["two_workers"]["wall_seconds"] for run in optimization_concurrency]
    matrix_summary = {status: sum(row["status"] == status for row in matrix) for status in {row["status"] for row in matrix}}
    return {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "numpy": np.__version__,
            "quantlib": version("QuantLib"),
            "riskfolio_lib": version("riskfolio-lib"),
            "parent_peak_rss_bytes": peak_rss_bytes(),
        },
        "limits": {
            "max_portfolio_cells": MAX_PORTFOLIO_CELLS,
            "max_stochastic_cells": MAX_STOCHASTIC_CELLS,
        },
        "matrix": matrix,
        "matrix_summary": matrix_summary,
        "simulation_representative": representative,
        "simulation_cache": await benchmark_simulation_cache(),
        "simulation_concurrency": simulation_concurrency,
        "simulation_concurrency_median_speedup": (statistics.median(simulation_speedups)),
        "optimization_persistence": (await benchmark_optimization_persistence()),
        "optimization_concurrency": optimization_concurrency,
        "optimization_concurrency_median_speedup": (statistics.median(optimization_speedups)),
        "timeout_recycle": await benchmark_timeout_recycle(),
        "decision": {
            "process_isolation": "always",
            "default_workers_per_pool": 1,
            "multiple_workers_configurable": True,
            "selection_rule": ("Default remains one worker because concurrency gains " "must be weighed against measured per-process RSS; " "operators may configure more workers for concurrent load."),
        },
    }


def main() -> int:
    args = parse_args()
    report = asyncio.run(run_benchmark(args.repeats))
    equivalent = all(row["equivalent"] for row in report["simulation_representative"])
    equivalent = equivalent and report["simulation_cache"]["equivalent"] and report["optimization_persistence"]["equivalent"] and report["timeout_recycle"]["timed_out"] and report["timeout_recycle"]["worker_recycled"]
    report["status"] = "ok" if equivalent else "failed"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            report,
            indent=2,
            sort_keys=True,
        ),
    )
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
