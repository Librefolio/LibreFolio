#!/usr/bin/env python3
"""Probe quantitative libraries against deterministic LibreFolio fixtures."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
import traceback
import warnings
from importlib.metadata import PackageNotFoundError, distribution, metadata, version
from pathlib import Path
from time import perf_counter
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
LOCAL_FIXTURE_PATH = SCRIPT_PATH.with_name("quant_library_probe.json")
if len(SCRIPT_PATH.parents) > 3:
    PROJECT_FIXTURE_PATH = SCRIPT_PATH.parents[3] / "backend/test_scripts/fixtures/risk/quant_library_probe.json"
else:
    PROJECT_FIXTURE_PATH = LOCAL_FIXTURE_PATH
FIXTURE_PATH = PROJECT_FIXTURE_PATH if PROJECT_FIXTURE_PATH.exists() else LOCAL_FIXTURE_PATH
DEFAULT_OUTPUT = Path("/tmp/libreFolio_quant_library_probe.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--require-quantlib", action="store_true")
    parser.add_argument("--require-riskfolio", action="store_true")
    return parser.parse_args()


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def distribution_size_bytes(name: str) -> int | None:
    try:
        dist = distribution(name)
    except PackageNotFoundError:
        return None
    total = 0
    for file in dist.files or ():
        candidate = Path(dist.locate_file(file))
        if candidate.is_file():
            total += candidate.stat().st_size
    return total


def package_metadata(name: str) -> dict[str, Any]:
    try:
        info = metadata(name)
        return {
            "version": version(name),
            "license": info.get("License"),
            "requires_python": info.get("Requires-Python"),
            "distribution_size_bytes": distribution_size_bytes(name),
        }
    except PackageNotFoundError:
        return {"installed": False}


def ql_path_values(path: Any) -> list[float]:
    return [float(path[index]) for index in range(len(path))]


def ql_multi_path_values(multi_path: Any) -> list[list[float]]:
    return [ql_path_values(multi_path.at(asset_index)) for asset_index in range(multi_path.assetNumber())]


def make_quantlib_market(ql: Any, fixture: dict[str, Any]) -> dict[str, Any]:
    year, month, day = map(int, fixture["evaluation_date"].split("-"))
    evaluation_date = ql.Date(day, month, year)
    ql.Settings.instance().evaluationDate = evaluation_date
    day_counter = ql.Actual365Fixed()
    calendar = ql.NullCalendar()
    risk_free_curve = ql.YieldTermStructureHandle(ql.FlatForward(evaluation_date, fixture["risk_free_rate"], day_counter))
    dividend_curve = ql.YieldTermStructureHandle(ql.FlatForward(evaluation_date, fixture["dividend_rate"], day_counter))
    quotes = [ql.QuoteHandle(ql.SimpleQuote(spot)) for spot in fixture["multi_asset"]["spots"]]
    vol_curves = [ql.BlackVolTermStructureHandle(ql.BlackConstantVol(evaluation_date, calendar, volatility, day_counter)) for volatility in fixture["multi_asset"]["volatilities"]]
    processes = [
        ql.BlackScholesMertonProcess(
            quote,
            dividend_curve,
            risk_free_curve,
            vol_curve,
        )
        for quote, vol_curve in zip(quotes, vol_curves, strict=True)
    ]
    return {
        "evaluation_date": evaluation_date,
        "day_counter": day_counter,
        "calendar": calendar,
        "risk_free_curve": risk_free_curve,
        "dividend_curve": dividend_curve,
        "quotes": quotes,
        "vol_curves": vol_curves,
        "processes": processes,
    }


def quantlib_single_path(
    ql: Any,
    process: Any,
    horizon_years: float,
    steps: int,
    seed: int,
) -> list[float]:
    uniform = ql.UniformRandomSequenceGenerator(
        steps,
        ql.UniformRandomGenerator(seed),
    )
    gaussian = ql.GaussianRandomSequenceGenerator(uniform)
    generator = ql.GaussianPathGenerator(
        process,
        horizon_years,
        steps,
        gaussian,
        False,
    )
    sample = generator.next()
    return ql_path_values(sample.value())


def quantlib_multi_process(
    ql: Any,
    processes: list[Any],
    correlation: list[list[float]],
) -> Any:
    process_vector = ql.StochasticProcess1DVector()
    for process in processes:
        process_vector.push_back(process)
    matrix = ql.Matrix(len(correlation), len(correlation))
    for row_index, row in enumerate(correlation):
        for column_index, value in enumerate(row):
            matrix[row_index][column_index] = value
    return ql.StochasticProcessArray(process_vector, matrix)


def quantlib_multi_path(
    ql: Any,
    process: Any,
    horizon_years: float,
    steps: int,
    seed: int,
    qmc: bool,
) -> list[list[float]]:
    grid = ql.TimeGrid(horizon_years, steps)
    dimension = process.factors() * steps
    if qmc:
        uniform = ql.UniformLowDiscrepancySequenceGenerator(
            dimension,
            seed,
            ql.SobolRsg.JoeKuoD7,
        )
        gaussian = ql.GaussianLowDiscrepancySequenceGenerator(uniform)
        generator = ql.GaussianSobolMultiPathGenerator(
            process,
            grid,
            gaussian,
            False,
        )
    else:
        uniform = ql.UniformRandomSequenceGenerator(
            dimension,
            ql.UniformRandomGenerator(seed),
        )
        gaussian = ql.GaussianRandomSequenceGenerator(uniform)
        generator = ql.GaussianMultiPathGenerator(
            process,
            grid,
            gaussian,
            False,
        )
    sample = generator.next()
    return ql_multi_path_values(sample.value())


def quantlib_normal_sequence(
    ql: Any,
    dimension: int,
    seed: int,
    scramble_seed: int | None,
) -> tuple[float, ...]:
    if scramble_seed is None:
        uniform = ql.SobolRsg(
            dimension,
            seed,
            ql.SobolRsg.JoeKuoD7,
        )
        gaussian = ql.InvCumulativeSobolGaussianRsg(uniform)
    else:
        uniform = ql.Burley2020SobolRsg(
            dimension,
            seed,
            ql.SobolRsg.JoeKuoD7,
            scramble_seed,
        )
        gaussian = ql.InvCumulativeBurley2020SobolGaussianRsg(uniform)
    return tuple(float(value) for value in gaussian.nextSequence().value())


def quantlib_bond_analytics(ql: Any, evaluation_date: Any) -> dict[str, float | int]:
    calendar = ql.TARGET()
    day_counter = ql.ActualActual(ql.ActualActual.ISDA)
    maturity = calendar.advance(evaluation_date, ql.Period(5, ql.Years))
    schedule = ql.Schedule(
        evaluation_date,
        maturity,
        ql.Period(ql.Annual),
        calendar,
        ql.Following,
        ql.Following,
        ql.DateGeneration.Backward,
        False,
    )
    bond = ql.FixedRateBond(
        2,
        100.0,
        schedule,
        [0.03],
        day_counter,
    )
    interest_rate = ql.InterestRate(
        0.035,
        day_counter,
        ql.Compounded,
        ql.Annual,
    )
    return {
        "duration": float(
            ql.BondFunctions.duration(
                bond,
                interest_rate,
                ql.Duration.Modified,
            )
        ),
        "convexity": float(
            ql.BondFunctions.convexity(
                bond,
                interest_rate,
            )
        ),
        "cashflow_count": len(bond.cashflows()),
    }


def probe_quantlib(fixture: dict[str, Any]) -> dict[str, Any]:
    started = perf_counter()
    try:
        ql = importlib.import_module("QuantLib")
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }

    try:
        market = make_quantlib_market(ql, fixture)
        horizon_years = fixture["multi_asset"]["horizon_days"] / 365.0
        steps = fixture["multi_asset"]["steps"]
        seed = fixture["seed"]
        scramble_seed = fixture["scramble_seed"]
        first_single = quantlib_single_path(
            ql,
            market["processes"][0],
            horizon_years,
            steps,
            seed,
        )
        second_single = quantlib_single_path(
            ql,
            market["processes"][0],
            horizon_years,
            steps,
            seed,
        )
        multi_process = quantlib_multi_process(
            ql,
            market["processes"],
            fixture["multi_asset"]["correlation"],
        )
        pseudo_multi = quantlib_multi_path(
            ql,
            multi_process,
            horizon_years,
            steps,
            seed,
            qmc=False,
        )
        qmc_multi = quantlib_multi_path(
            ql,
            multi_process,
            horizon_years,
            steps,
            seed,
            qmc=True,
        )
        qmc_first = quantlib_normal_sequence(
            ql,
            fixture["sequence_dimension"],
            seed,
            None,
        )
        qmc_second = quantlib_normal_sequence(
            ql,
            fixture["sequence_dimension"],
            seed,
            None,
        )
        rqmc_first = quantlib_normal_sequence(
            ql,
            fixture["sequence_dimension"],
            seed,
            scramble_seed,
        )
        rqmc_second = quantlib_normal_sequence(
            ql,
            fixture["sequence_dimension"],
            seed,
            scramble_seed,
        )
        rqmc_other_scramble = quantlib_normal_sequence(
            ql,
            fixture["sequence_dimension"],
            seed,
            scramble_seed + 1,
        )
        capability_names = fixture["quantlib_capabilities"]
        checks = {
            "single_path_points": len(first_single),
            "single_path_reproducible": first_single == second_single,
            "pseudo_multi_assets": len(pseudo_multi),
            "pseudo_multi_points": [len(path) for path in pseudo_multi],
            "qmc_multi_assets": len(qmc_multi),
            "qmc_multi_points": [len(path) for path in qmc_multi],
            "qmc_sequence_dimension": len(qmc_first),
            "qmc_reproducible": qmc_first == qmc_second,
            "rqmc_sequence_dimension": len(rqmc_first),
            "rqmc_reproducible": rqmc_first == rqmc_second,
            "rqmc_scramble_changes_sequence": (rqmc_first != rqmc_other_scramble),
            "capabilities": {name: hasattr(ql, name) for name in capability_names},
            "bond": quantlib_bond_analytics(
                ql,
                market["evaluation_date"],
            ),
        }
        hard_checks = (
            checks["single_path_reproducible"],
            checks["pseudo_multi_assets"] == len(fixture["multi_asset"]["spots"]),
            checks["qmc_multi_assets"] == len(fixture["multi_asset"]["spots"]),
            checks["qmc_sequence_dimension"] == fixture["sequence_dimension"],
            checks["rqmc_sequence_dimension"] == fixture["sequence_dimension"],
            checks["qmc_reproducible"],
            checks["rqmc_reproducible"],
            checks["rqmc_scramble_changes_sequence"],
            all(checks["capabilities"].values()),
            checks["bond"]["duration"] > 0,
            checks["bond"]["convexity"] > 0,
        )
        return {
            "status": "ok" if all(hard_checks) else "failed",
            "package": package_metadata("QuantLib"),
            "imported_version": getattr(ql, "__version__", None),
            "checks": checks,
            "elapsed_seconds": perf_counter() - started,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "package": package_metadata("QuantLib"),
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "elapsed_seconds": perf_counter() - started,
        }


def probe_riskfolio(fixture: dict[str, Any]) -> dict[str, Any]:
    started = perf_counter()
    try:
        rp = importlib.import_module("riskfolio")
        cp = importlib.import_module("cvxpy")
        np = importlib.import_module("numpy")
        pd = importlib.import_module("pandas")
        scipy = importlib.import_module("scipy")
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }

    try:
        returns = pd.DataFrame(fixture["riskfolio_returns"])

        def optimize(strategy: str) -> Any:
            portfolio = rp.Portfolio(returns=returns)
            portfolio.assets_stats(
                method_mu="hist",
                method_cov="hist",
            )
            if strategy == "risk_parity":
                return portfolio.rp_optimization(
                    model="Classic",
                    rm="MV",
                    rf=0,
                    b=None,
                    hist=True,
                )
            objective = "MinRisk" if strategy == "min_risk" else "Sharpe"
            return portfolio.optimization(
                model="Classic",
                rm="MV",
                obj=objective,
                rf=0,
                l=0,
                hist=True,
            )

        optimization_checks = {}
        with warnings.catch_warnings(record=True) as warning_records:
            warnings.simplefilter("always")
            for strategy in ("min_risk", "max_sharpe", "risk_parity"):
                first = optimize(strategy)
                second = optimize(strategy)
                if first is None or second is None:
                    raise RuntimeError(f"Riskfolio {strategy} optimization returned no weights")
                first_weights = first["weights"]
                second_weights = second["weights"]
                first_array = first_weights.to_numpy(dtype=float)
                second_array = second_weights.to_numpy(dtype=float)
                optimization_checks[strategy] = {
                    "weights": {str(asset): float(value) for asset, value in first_weights.items()},
                    "weight_sum": float(first_weights.sum()),
                    "weights_finite": bool(np.isfinite(first_array).all()),
                    "weights_non_negative": bool((first_array >= -1e-8).all()),
                    "repeat_max_abs_delta": float(np.max(np.abs(first_array - second_array))),
                }

        checks = {
            "solvers": list(cp.installed_solvers()),
            "optimizations": optimization_checks,
            "warnings": sorted({f"{record.category.__name__}: {record.message}" for record in warning_records}),
            "dependency_versions": {
                "numpy": np.__version__,
                "pandas": pd.__version__,
                "scipy": scipy.__version__,
                "cvxpy": cp.__version__,
                "vectorbt": version("vectorbt"),
                "numba": version("numba"),
            },
        }
        hard_checks = (
            bool(checks["solvers"]),
            all(result["weights_finite"] and result["weights_non_negative"] and abs(result["weight_sum"] - 1.0) <= 1e-6 and result["repeat_max_abs_delta"] <= 1e-6 for result in optimization_checks.values()),
        )
        return {
            "status": "ok" if all(hard_checks) else "failed",
            "package": package_metadata("riskfolio-lib"),
            "imported_version": getattr(rp, "__version__", None),
            "checks": checks,
            "elapsed_seconds": perf_counter() - started,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "package": package_metadata("riskfolio-lib"),
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
            "elapsed_seconds": perf_counter() - started,
        }


def main() -> int:
    args = parse_args()
    fixture = load_fixture(args.fixture)
    report = {
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "executable": sys.executable,
        },
        "quantlib": probe_quantlib(fixture),
        "riskfolio": probe_riskfolio(fixture),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))

    failures = []
    if args.require_quantlib and report["quantlib"]["status"] != "ok":
        failures.append("QuantLib")
    if args.require_riskfolio and report["riskfolio"]["status"] != "ok":
        failures.append("Riskfolio-Lib")
    if failures:
        print(
            "Required probe failed: " + ", ".join(failures),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
