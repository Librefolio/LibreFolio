#!/usr/bin/env python3
"""Probe quantitative libraries against deterministic LibreFolio fixtures."""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import resource
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
    parser.add_argument("--expected-numpy-version")
    parser.add_argument("--expected-riskfolio-version")
    parser.add_argument("--forbid-package", action="append", default=[])
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
        dist = distribution(name)
        info = metadata(name)
        return {
            "version": version(name),
            "license": info.get("License"),
            "requires_python": info.get("Requires-Python"),
            "distribution_size_bytes": distribution_size_bytes(name),
            "requires": sorted(dist.requires or ()),
        }
    except PackageNotFoundError:
        return {"installed": False}


def installed_version(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def max_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return int(value)
    return int(value * 1024)


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


def probe_riskfolio(  # noqa: C901 — flat sequential probe steps, data packing, no nested logic
    fixture: dict[str, Any],
    *,
    expected_numpy_version: str | None,
    expected_riskfolio_version: str | None,
    forbidden_packages: list[str],
) -> dict[str, Any]:
    started = perf_counter()
    try:
        rp = importlib.import_module("riskfolio")
        cp = importlib.import_module("cvxpy")
        np = importlib.import_module("numpy")
        pd = importlib.import_module("pandas")
        importlib.import_module("scipy")
    except Exception as exc:
        return {
            "status": "unavailable",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }

    try:
        returns = pd.DataFrame(fixture["riskfolio_returns"])
        solvers = list(cp.installed_solvers())
        solver = next(
            (candidate for candidate in ("CLARABEL", "SCS") if candidate in solvers),
            None,
        )
        if solver is None:
            raise RuntimeError(
                "Riskfolio probe requires CLARABEL or SCS",
            )
        min_weight = 0.05
        max_weight = 0.8

        def configure_portfolio(
            *,
            covariance_method: str = "hist",
            infeasible: bool = False,
        ) -> Any:
            portfolio = rp.Portfolio(returns=returns)
            portfolio.assets_stats(
                method_mu="hist",
                method_cov=covariance_method,
            )
            portfolio.sht = False
            portfolio.budget = 1
            portfolio.upperlng = max_weight
            portfolio.solvers = [solver]
            asset_count = returns.shape[1]
            lower = 0.5 if infeasible else min_weight
            portfolio.ainequality = np.vstack(
                [
                    np.eye(asset_count),
                    -np.eye(asset_count),
                ]
            )
            portfolio.binequality = np.concatenate(
                [
                    np.full(asset_count, max_weight),
                    np.full(asset_count, -lower),
                ]
            ).reshape(-1, 1)
            return portfolio

        def optimize(
            strategy: str,
            *,
            covariance_method: str = "hist",
        ) -> tuple[Any, Any]:
            portfolio = configure_portfolio(
                covariance_method=covariance_method,
            )
            if strategy == "risk_parity":
                weights = portfolio.rp_optimization(
                    model="Classic",
                    rm="MV",
                    rf=0,
                    b=None,
                    hist=True,
                )
            else:
                objective = "MinRisk" if strategy == "min_risk" else "Sharpe"
                weights = portfolio.optimization(
                    model="Classic",
                    rm="MV",
                    obj=objective,
                    rf=0,
                    l=0,
                    hist=True,
                )
            return portfolio, weights

        optimization_checks = {}
        with warnings.catch_warnings(record=True) as warning_records:
            warnings.simplefilter("always")
            for strategy in ("min_risk", "max_sharpe", "risk_parity"):
                first_portfolio, first = optimize(strategy)
                _, second = optimize(strategy)
                if first is None or second is None:
                    raise RuntimeError(f"Riskfolio {strategy} optimization returned no weights")
                first_weights = first["weights"]
                second_weights = second["weights"]
                first_array = first_weights.to_numpy(dtype=float)
                second_array = second_weights.to_numpy(dtype=float)
                covariance = first_portfolio.cov.to_numpy(dtype=float)
                variance = float(first_array @ covariance @ first_array)
                percentage_contributions = first_array * (covariance @ first_array) / variance
                optimization_checks[strategy] = {
                    "weights": {str(asset): float(value) for asset, value in first_weights.items()},
                    "weight_sum": float(first_weights.sum()),
                    "weights_finite": bool(np.isfinite(first_array).all()),
                    "weights_within_bounds": bool((first_array >= min_weight - 1e-7).all() and (first_array <= max_weight + 1e-7).all()),
                    "repeat_max_abs_delta": float(np.max(np.abs(first_array - second_array))),
                    "portfolio_variance": variance,
                    "percentage_risk_contributions": [float(value) for value in percentage_contributions],
                }

            covariance_checks = {}
            for method in ("hist", "ledoit", "oas"):
                portfolio = configure_portfolio(
                    covariance_method=method,
                )
                covariance = portfolio.cov.to_numpy(dtype=float)
                covariance_checks[method] = {
                    "finite": bool(np.isfinite(covariance).all()),
                    "symmetric": bool(
                        np.allclose(
                            covariance,
                            covariance.T,
                            rtol=0,
                            atol=1e-12,
                        )
                    ),
                    "min_eigenvalue": float(np.linalg.eigvalsh(covariance).min()),
                }

            frontier_portfolio = configure_portfolio()
            frontier = frontier_portfolio.efficient_frontier(
                model="Classic",
                rm="MV",
                points=5,
                rf=0,
                solver=solver,
                hist=True,
            )
            if frontier is None:
                raise RuntimeError("Riskfolio efficient frontier returned no weights")
            frontier_array = frontier.to_numpy(dtype=float)
            frontier_check = {
                "shape": list(frontier_array.shape),
                "finite": bool(np.isfinite(frontier_array).all()),
                "weight_sums": [float(value) for value in frontier_array.sum(axis=0)],
            }

            infeasible_portfolio = configure_portfolio(
                infeasible=True,
            )
            infeasible_result = infeasible_portfolio.optimization(
                model="Classic",
                rm="MV",
                obj="MinRisk",
                rf=0,
                l=0,
                hist=True,
            )

        forbidden_versions = {name: installed_version(name) for name in forbidden_packages}
        dependency_versions = {
            name: installed_version(name)
            for name in (
                "numpy",
                "pandas",
                "scipy",
                "cvxpy",
                "clarabel",
                "scikit-learn",
                "statsmodels",
                "arch",
                "astropy",
                "vectorbt",
                "numba",
            )
        }
        checks = {
            "solvers": solvers,
            "selected_solver": solver,
            "optimizations": optimization_checks,
            "covariance_estimators": covariance_checks,
            "frontier": frontier_check,
            "infeasible_returns_none": infeasible_result is None,
            "warnings": sorted({f"{record.category.__name__}: {record.message}" for record in warning_records}),
            "dependency_versions": dependency_versions,
            "forbidden_packages": forbidden_versions,
            "max_rss_bytes": max_rss_bytes(),
        }
        version_checks = {
            "numpy": (expected_numpy_version is None or np.__version__ == expected_numpy_version),
            "riskfolio": (expected_riskfolio_version is None or getattr(rp, "__version__", None) == expected_riskfolio_version),
            "forbidden_packages_absent": all(value is None for value in forbidden_versions.values()),
        }
        risk_parity_contributions = optimization_checks["risk_parity"]["percentage_risk_contributions"]
        hard_checks = (
            all(version_checks.values()),
            all(result["weights_finite"] and result["weights_within_bounds"] and abs(result["weight_sum"] - 1.0) <= 1e-6 and result["repeat_max_abs_delta"] <= 1e-6 for result in optimization_checks.values()),
            max(risk_parity_contributions) - min(risk_parity_contributions) <= 1e-4,
            all(result["finite"] and result["symmetric"] and result["min_eigenvalue"] >= -1e-10 for result in covariance_checks.values()),
            frontier_check["finite"],
            len(frontier_check["weight_sums"]) >= 2,
            all(abs(weight_sum - 1.0) <= 1e-6 for weight_sum in frontier_check["weight_sums"]),
            checks["infeasible_returns_none"],
        )
        return {
            "status": "ok" if all(hard_checks) else "failed",
            "package": package_metadata("riskfolio-lib"),
            "imported_version": getattr(rp, "__version__", None),
            "version_checks": version_checks,
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
        "riskfolio": probe_riskfolio(
            fixture,
            expected_numpy_version=args.expected_numpy_version,
            expected_riskfolio_version=(args.expected_riskfolio_version),
            forbidden_packages=args.forbid_package,
        ),
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
