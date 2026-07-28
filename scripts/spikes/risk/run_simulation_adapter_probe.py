#!/usr/bin/env python3
"""Verify QuantLib GBM against analytical multivariate-normal oracles."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = SCRIPT_PATH.parents[3]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.app.services.risk.quant.models import (
    SimulationEngineRequest,
    SimulationEngineResult,
)
from backend.app.services.risk.quant.quantlib_worker import (
    execute_simulation_job,
)
from backend.app.services.risk.quant.spawn_worker import (
    SpawnWorkerPool,
)

DEFAULT_FIXTURE = REPOSITORY_ROOT / "backend/test_scripts/fixtures/risk/" "simulation_adapter_probe.json"
DEFAULT_OUTPUT = Path(
    "/tmp/libreFolio_simulation_adapter_probe.json",
)
HANDLER_PATH = "backend.app.services.risk.quant." "quantlib_worker:execute_simulation_job"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    return parser.parse_args()


def make_request(
    fixture: dict[str, Any],
    *,
    sampling: str,
    paths: int,
    seed: int,
) -> SimulationEngineRequest:
    return SimulationEngineRequest(
        sampling=sampling,
        asset_ids=fixture["asset_ids"],
        annual_drifts=fixture["annual_drifts"],
        annual_covariance=fixture["annual_covariance"],
        weights=fixture["weights"],
        cash_weight=fixture["cash_weight"],
        horizon_days=fixture["horizon_days"],
        paths=paths,
        seed=seed,
    )


def run_direct(
    request: SimulationEngineRequest,
) -> SimulationEngineResult:
    return SimulationEngineResult.model_validate(
        execute_simulation_job(
            request.model_dump(mode="json"),
        ),
    )


def analytical_moments(
    request: SimulationEngineRequest,
) -> tuple[np.ndarray, np.ndarray]:
    covariance = np.asarray(
        request.annual_covariance,
        dtype=float,
    )
    horizon = request.horizon_days / 365.0
    mean = (np.asarray(request.annual_drifts) - 0.5 * np.diag(covariance)) * horizon
    return mean, covariance * horizon


def mc_oracle_report(
    request: SimulationEngineRequest,
    result: SimulationEngineResult,
    *,
    confidence_sigma: float,
) -> dict[str, Any]:
    expected_mean, expected_covariance = analytical_moments(request)
    observed_mean = np.asarray(
        result.terminal_asset_log_means,
    )
    observed_covariance = np.asarray(
        result.terminal_asset_log_covariance,
    )
    mean_standard_error = np.sqrt(
        np.diag(expected_covariance) / request.paths,
    )
    mean_z = np.divide(
        np.abs(observed_mean - expected_mean),
        mean_standard_error,
        out=np.zeros_like(observed_mean),
        where=mean_standard_error > 0,
    )
    covariance_z = np.zeros_like(expected_covariance)
    for row in range(len(request.asset_ids)):
        for column in range(len(request.asset_ids)):
            standard_error = math.sqrt(
                (expected_covariance[row, column] ** 2 + expected_covariance[row, row] * expected_covariance[column, column]) / (request.paths - 1),
            )
            if standard_error > 0:
                covariance_z[row, column] = (
                    abs(
                        observed_covariance[row, column] - expected_covariance[row, column],
                    )
                    / standard_error
                )

    fisher_z_scores = []
    expected_std = np.sqrt(np.diag(expected_covariance))
    observed_std = np.sqrt(np.diag(observed_covariance))
    for row in range(len(request.asset_ids)):
        for column in range(row):
            expected_denominator = expected_std[row] * expected_std[column]
            observed_denominator = observed_std[row] * observed_std[column]
            if expected_denominator == 0 or observed_denominator == 0:
                continue
            expected_correlation = expected_covariance[row, column] / expected_denominator
            observed_correlation = observed_covariance[row, column] / observed_denominator
            if abs(expected_correlation) >= 1:
                continue
            fisher_z_scores.append(
                abs(np.arctanh(observed_correlation) - np.arctanh(expected_correlation)) * math.sqrt(request.paths - 3),
            )
    max_mean_z = float(np.max(mean_z))
    max_covariance_z = float(np.max(covariance_z))
    max_fisher_z = float(
        max(fisher_z_scores, default=0.0),
    )
    return {
        "paths": request.paths,
        "confidence_sigma": confidence_sigma,
        "max_mean_standard_errors": max_mean_z,
        "max_covariance_standard_errors": (max_covariance_z),
        "max_fisher_standard_errors": max_fisher_z,
        "passed": (max_mean_z <= confidence_sigma and max_covariance_z <= confidence_sigma and max_fisher_z <= confidence_sigma),
    }


def qmc_convergence_report(
    fixture: dict[str, Any],
) -> tuple[dict[str, Any], SimulationEngineResult]:
    rows = []
    largest_result = None
    for paths in fixture["qmc_path_counts"]:
        request = make_request(
            fixture,
            sampling="qmc",
            paths=paths,
            seed=fixture["qmc_start_index"],
        )
        result = run_direct(request)
        expected_mean, expected_covariance = analytical_moments(request)
        mean_error = float(
            np.linalg.norm(
                np.asarray(
                    result.terminal_asset_log_means,
                )
                - expected_mean,
            ),
        )
        covariance_error = float(
            np.linalg.norm(
                np.asarray(
                    result.terminal_asset_log_covariance,
                )
                - expected_covariance,
                ord="fro",
            ),
        )
        rows.append(
            {
                "paths": paths,
                "mean_l2_error": mean_error,
                "covariance_frobenius_error": (covariance_error),
            },
        )
        largest_result = result
    exponents = np.log2(
        [row["paths"] for row in rows],
    )
    mean_slope = float(
        np.polyfit(
            exponents,
            np.log(
                [row["mean_l2_error"] for row in rows],
            ),
            1,
        )[0],
    )
    covariance_slope = float(
        np.polyfit(
            exponents,
            np.log(
                [row["covariance_frobenius_error"] for row in rows],
            ),
            1,
        )[0],
    )
    report = {
        "start_index": fixture["qmc_start_index"],
        "rows": rows,
        "mean_log2_slope": mean_slope,
        "covariance_log2_slope": covariance_slope,
        "passed": (rows[-1]["mean_l2_error"] < rows[0]["mean_l2_error"] and rows[-1]["covariance_frobenius_error"] < rows[0]["covariance_frobenius_error"] and mean_slope < 0 and covariance_slope < 0),
    }
    return report, largest_result


async def spawned_equivalence(
    request: SimulationEngineRequest,
    direct: SimulationEngineResult,
) -> dict[str, Any]:
    pool = SpawnWorkerPool(
        name="simulation-oracle-probe",
        handler_path=HANDLER_PATH,
        workers=1,
        queue_capacity=0,
        timeout_seconds=120,
    )
    try:
        spawned = await pool.submit(
            request.model_dump(mode="json"),
        )
    finally:
        await pool.shutdown()
    parsed = SimulationEngineResult.model_validate(
        spawned.payload,
    )
    return {
        "equivalent": parsed == direct,
        "worker_pid": spawned.worker_pid,
        "cold_round_trip_seconds": (spawned.round_trip_seconds),
        "execution_seconds": spawned.execution_seconds,
        "peak_rss_bytes": spawned.peak_rss_bytes,
    }


def main() -> int:
    args = parse_args()
    fixture = json.loads(
        args.fixture.read_text(encoding="utf-8"),
    )
    mc_request = make_request(
        fixture,
        sampling="mc",
        paths=fixture["mc_paths"],
        seed=fixture["seed"],
    )
    mc_result = run_direct(mc_request)
    mc_report = mc_oracle_report(
        mc_request,
        mc_result,
        confidence_sigma=fixture["confidence_sigma"],
    )
    qmc_report, qmc_result = qmc_convergence_report(
        fixture,
    )
    largest_qmc_request = make_request(
        fixture,
        sampling="qmc",
        paths=fixture["qmc_path_counts"][-1],
        seed=fixture["qmc_start_index"],
    )
    process_report = asyncio.run(
        spawned_equivalence(
            largest_qmc_request,
            qmc_result,
        ),
    )
    report = {
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "numpy": np.__version__,
            "quantlib": version("QuantLib"),
        },
        "algorithm_version": fixture["algorithm_version"],
        "mc_oracle": mc_report,
        "qmc_convergence": qmc_report,
        "spawned_equivalence": process_report,
    }
    report["status"] = "ok" if (mc_report["passed"] and qmc_report["passed"] and process_report["equivalent"]) else "failed"
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
