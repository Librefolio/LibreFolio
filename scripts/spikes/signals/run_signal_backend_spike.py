#!/usr/bin/env python3
"""Validate the Phase 0 composite technical-indicator stack."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any, Iterator

import numpy as np
import pandas as pd
import pandas_ta_classic as ta
import talib

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_MANIFEST = PROJECT_ROOT / "backend/test_scripts/fixtures/signals/backend_spike_datasets.json"
DEFAULT_OUTPUT = Path("/tmp/libreFolio_signal_backend_spike.json")


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    function_name: str
    required_fields: tuple[str, ...]
    params: dict[str, int | float | str]
    expected_columns: int
    expected_talib_calls: tuple[str, ...]


INDICATORS = (
    IndicatorSpec("EMA", "ema", ("close",), {"length": 20}, 1, ("EMA",)),
    IndicatorSpec("SMA", "sma", ("close",), {"length": 20}, 1, ("SMA",)),
    IndicatorSpec("RSI", "rsi", ("close",), {"length": 14}, 1, ("RSI",)),
    IndicatorSpec("MACD", "macd", ("close",), {"fast": 12, "slow": 26, "signal": 9}, 3, ("MACD",)),
    IndicatorSpec("BBANDS", "bbands", ("close",), {"length": 20, "std": 2.0}, 5, ("BBANDS",)),
    IndicatorSpec("ROC", "roc", ("close",), {"length": 12}, 1, ("ROC",)),
    IndicatorSpec(
        "STOCHRSI",
        "stochrsi",
        ("close",),
        {"length": 14, "rsi_length": 14, "k": 3, "d": 3},
        2,
        ("STOCHRSI",),
    ),
    IndicatorSpec("KAMA", "kama", ("close",), {"length": 10, "fast": 2, "slow": 30}, 1, ("KAMA",)),
    IndicatorSpec("PPO", "ppo", ("close",), {"fast": 12, "slow": 26, "signal": 9}, 3, ("PPO",)),
    IndicatorSpec("ATR", "atr", ("high", "low", "close"), {"length": 14}, 1, ("ATR",)),
    IndicatorSpec(
        "ADX",
        "adx",
        ("high", "low", "close"),
        {"length": 14},
        3,
        ("ADX", "MINUS_DI", "PLUS_DI"),
    ),
    IndicatorSpec("NATR", "natr", ("high", "low", "close"), {"length": 14}, 1, ("NATR",)),
    IndicatorSpec("AROON", "aroon", ("high", "low"), {"length": 14}, 3, ("AROON", "AROONOSC")),
    IndicatorSpec(
        "DONCHIAN",
        "donchian",
        ("high", "low"),
        {"lower_length": 20, "upper_length": 20},
        3,
        (),
    ),
    IndicatorSpec("CCI", "cci", ("high", "low", "close"), {"length": 14}, 1, ("CCI",)),
    IndicatorSpec("OBV", "obv", ("close", "volume"), {}, 1, ("OBV",)),
    IndicatorSpec("MFI", "mfi", ("high", "low", "close", "volume"), {"length": 14}, 1, ("MFI",)),
)

TRACKED_TALIB_FUNCTIONS = tuple(sorted({function_name for spec in INDICATORS for function_name in spec.expected_talib_calls}))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-benchmarks", action="store_true")
    return parser.parse_args()


def load_manifest() -> dict[str, Any]:
    return json.loads(FIXTURE_MANIFEST.read_text())


def deterministic_noise(seed: int, count: int) -> list[float]:
    state = seed & 0xFFFFFFFF
    values: list[float] = []
    for _ in range(count):
        state = (1664525 * state + 1013904223) & 0xFFFFFFFF
        values.append((state / 0xFFFFFFFF) * 2.0 - 1.0)
    return values


def triangle_wave(position: int, period: int) -> float:
    phase = (position % period) / period
    return -1.0 + 4.0 * phase if phase < 0.5 else 3.0 - 4.0 * phase


def generate_base_frame(config: dict[str, Any]) -> pd.DataFrame:
    points = config["points"]
    base_price = config["base_price"]
    volatility = config["volatility"]
    noise = iter(deterministic_noise(config["seed"], points * 4))
    close_values: list[float] = []
    open_values: list[float] = []
    high_values: list[float] = []
    low_values: list[float] = []
    volume_values: list[float] = []
    random_walk = 0.0
    previous_close = base_price
    for position in range(points):
        random_walk += next(noise) * volatility
        cycle = config["cycle_amplitude"] * triangle_wave(position, config["cycle_period"])
        close = max(
            base_price * 0.05,
            base_price + config["daily_drift"] * position + random_walk + cycle,
        )
        open_value = previous_close + next(noise) * volatility * 0.15
        spread = abs(base_price * 0.002 + next(noise) * volatility * 0.25) + base_price * 0.0005
        high = max(open_value, close) + spread
        low = max(min(open_value, close) - spread, base_price * 0.001)
        volume = max(
            1.0,
            1_000_000.0 + 150_000.0 * triangle_wave(position, 31) + next(noise) * 50_000.0,
        )
        close_values.append(close)
        open_values.append(open_value)
        high_values.append(high)
        low_values.append(low)
        volume_values.append(volume)
        previous_close = close
    index = pd.date_range(config["start_date"], periods=points, freq="D", name="date")
    return pd.DataFrame(
        {
            "open": open_values,
            "high": high_values,
            "low": low_values,
            "close": close_values,
            "volume": volume_values,
        },
        index=index,
        dtype=float,
    )


def generate_datasets(manifest: dict[str, Any]) -> dict[str, pd.DataFrame]:
    generator = manifest["generator"]
    variants = manifest["variants"]
    volatile = generate_base_frame(generator)
    datasets = {"volatile": volatile}

    flat = volatile.copy()
    flat.loc[:, ("open", "high", "low", "close")] = variants["flat"]["price"]
    flat.loc[:, "volume"] = variants["flat"]["volume"]
    datasets["flat"] = flat

    trend_config = generator | variants["trend"] | {"volatility": 0.0, "cycle_amplitude": 0.0}
    datasets["trend"] = generate_base_frame(trend_config)

    for name in ("scale_low", "scale_high"):
        scaled = volatile.copy()
        scaled.loc[:, ("open", "high", "low", "close")] *= variants[name]["price_scale"]
        datasets[name] = scaled

    date_gap = volatile.drop(volatile.index[variants["date_gap"]["drop_indexes"]])
    datasets["date_gap"] = date_gap

    for name in ("nan_close_gap", "nan_hlc_gap", "nan_volume_gap"):
        frame = volatile.copy()
        frame.loc[frame.index[variants[name]["indexes"]], variants[name]["fields"]] = np.nan
        datasets[name] = frame

    datasets["short"] = volatile.iloc[: variants["short"]["points"]].copy()
    return datasets


def frame_fingerprint(frame: pd.DataFrame) -> str:
    digest = hashlib.sha256()
    digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    digest.update("|".join(frame.columns).encode())
    return digest.hexdigest()


def invoke_indicator(
    spec: IndicatorSpec,
    frame: pd.DataFrame,
    talib_mode: bool | None,
    missing_field: str | None = None,
) -> pd.Series | pd.DataFrame | None:
    kwargs: dict[str, Any] = {}
    for field in spec.required_fields:
        kwargs[field] = None if field == missing_field else frame[field]
    kwargs.update(spec.params)
    if spec.code != "DONCHIAN" and talib_mode is not None:
        kwargs["talib"] = talib_mode
    return getattr(ta, spec.function_name)(**kwargs)


def output_frame(result: pd.Series | pd.DataFrame | None) -> pd.DataFrame | None:
    if result is None:
        return None
    if isinstance(result, pd.Series):
        return result.to_frame(name=result.name or "value")
    if isinstance(result, pd.DataFrame):
        return result
    raise TypeError(f"Unexpected indicator output: {type(result)!r}")


def output_fingerprint(result: pd.Series | pd.DataFrame | None) -> str:
    frame = output_frame(result)
    if frame is None:
        return "none"
    return frame_fingerprint(frame)


def summarize_output(result: pd.Series | pd.DataFrame | None, expected_index: pd.Index) -> dict[str, Any]:
    frame = output_frame(result)
    if frame is None:
        return {"status": "none"}
    values = frame.to_numpy(dtype=float)
    finite = np.isfinite(values)
    infinity = np.isinf(values)
    columns: dict[str, Any] = {}
    for position, column in enumerate(frame.columns):
        finite_positions = np.flatnonzero(finite[:, position])
        columns[str(column)] = {
            "finite_count": int(finite_positions.size),
            "first_finite_position": int(finite_positions[0]) if finite_positions.size else None,
            "last_finite_position": int(finite_positions[-1]) if finite_positions.size else None,
            "nan_count": int(np.isnan(values[:, position]).sum()),
            "infinity_count": int(infinity[:, position].sum()),
        }
    return {
        "status": "ok",
        "rows": len(frame),
        "column_count": len(frame.columns),
        "columns": columns,
        "index_aligned": frame.index.equals(expected_index),
        "fingerprint": output_fingerprint(frame),
    }


@contextmanager
def track_talib_calls() -> Iterator[Counter[str]]:
    originals: dict[str, Any] = {}
    calls: Counter[str] = Counter()
    for function_name in TRACKED_TALIB_FUNCTIONS:
        original = getattr(talib, function_name)
        originals[function_name] = original

        def wrapper(*args: Any, _name: str = function_name, _original: Any = original, **kwargs: Any) -> Any:
            calls[_name] += 1
            return _original(*args, **kwargs)

        setattr(talib, function_name, wrapper)
    try:
        yield calls
    finally:
        for function_name, original in originals.items():
            setattr(talib, function_name, original)


def verify_backend_paths(
    datasets: dict[str, pd.DataFrame],
    failures: list[str],
) -> dict[str, Any]:
    frame = datasets["volatile"]
    checks: dict[str, Any] = {}
    for spec in INDICATORS:
        with track_talib_calls() as delegated_calls:
            delegated = invoke_indicator(spec, frame, True)
        with track_talib_calls() as native_calls:
            native = invoke_indicator(spec, frame, False)
        with track_talib_calls() as default_calls:
            default = invoke_indicator(spec, frame, None)

        delegated_summary = summarize_output(delegated, frame.index)
        native_summary = summarize_output(native, frame.index)
        default_summary = summarize_output(default, frame.index)
        expected_calls_found = all(delegated_calls[name] > 0 for name in spec.expected_talib_calls)

        if delegated_summary["status"] != "ok":
            failures.append(f"{spec.code}: delegated output missing")
        elif delegated_summary["column_count"] != spec.expected_columns:
            failures.append(f"{spec.code}: expected {spec.expected_columns} columns, got {delegated_summary['column_count']}")
        elif not delegated_summary["index_aligned"]:
            failures.append(f"{spec.code}: delegated output index is not aligned")
        if not expected_calls_found:
            failures.append(f"{spec.code}: expected TA-Lib path not observed")
        if native_calls:
            failures.append(f"{spec.code}: talib=False unexpectedly called {dict(native_calls)}")
        if default_calls:
            failures.append(f"{spec.code}: default call unexpectedly used TA-Lib {dict(default_calls)}")

        checks[spec.code] = {
            "expected_calls": list(spec.expected_talib_calls),
            "delegated_calls": dict(delegated_calls),
            "native_calls": dict(native_calls),
            "default_calls": dict(default_calls),
            "delegated": delegated_summary,
            "native": native_summary,
            "default": default_summary,
        }
    return checks


def verify_dataset_behavior(
    datasets: dict[str, pd.DataFrame],
    failures: list[str],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for spec in INDICATORS:
        signal_checks: dict[str, Any] = {}
        for dataset_name, frame in datasets.items():
            try:
                result = invoke_indicator(spec, frame, True)
                summary = summarize_output(result, frame.index)
            except Exception as exc:
                summary = {"status": "exception", "error": f"{type(exc).__name__}: {exc}"}

            signal_checks[dataset_name] = summary
            if dataset_name != "short":
                if summary["status"] != "ok":
                    failures.append(f"{spec.code}/{dataset_name}: no aligned output")
                elif not summary["index_aligned"]:
                    failures.append(f"{spec.code}/{dataset_name}: output index is not aligned")
                elif summary["column_count"] != spec.expected_columns:
                    failures.append(f"{spec.code}/{dataset_name}: output column count changed")

        missing_checks: dict[str, Any] = {}
        for field in spec.required_fields:
            try:
                missing_result = invoke_indicator(spec, datasets["volatile"], True, missing_field=field)
                missing_checks[field] = summarize_output(missing_result, datasets["volatile"].index)
            except Exception as exc:
                missing_checks[field] = {"status": "exception", "error": f"{type(exc).__name__}: {exc}"}
        signal_checks["missing_fields"] = missing_checks
        checks[spec.code] = signal_checks
    return checks


def probe_minimum_output(
    spec: IndicatorSpec,
    frame: pd.DataFrame,
) -> tuple[int | None, list[dict[str, Any]]]:
    exceptions: list[dict[str, Any]] = []
    for points in range(1, min(512, len(frame)) + 1):
        try:
            result = output_frame(invoke_indicator(spec, frame.iloc[:points], True))
        except Exception as exc:
            exceptions.append(
                {
                    "points": points,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        if result is None or result.empty:
            continue
        if np.isfinite(result.iloc[-1].to_numpy(dtype=float)).all():
            return points, exceptions
    return None, exceptions


def normalized_output_error(
    reference: pd.DataFrame,
    candidate: pd.DataFrame | None,
    rebase: bool,
) -> float | None:
    if candidate is None or reference.shape != candidate.shape:
        return None
    reference_values = reference.to_numpy(dtype=float)
    candidate_values = candidate.to_numpy(dtype=float)
    if rebase:
        reference_values = reference_values - reference_values[0]
        candidate_values = candidate_values - candidate_values[0]
    reference_finite = np.isfinite(reference_values)
    if not reference_finite.any() or not np.isfinite(candidate_values[reference_finite]).all():
        return None
    difference = np.abs(reference_values[reference_finite] - candidate_values[reference_finite])
    scale = max(1.0, float(np.max(np.abs(reference_values[reference_finite]))))
    return float(np.max(difference) / scale)


def warmup_candidates(limit: int) -> list[int]:
    candidates = list(range(0, min(limit, 64) + 1))
    candidates.extend(range(68, min(limit, 256) + 1, 4))
    candidates.extend(range(264, limit + 1, 8))
    return sorted(set(candidates))


def measure_warmup(
    spec: IndicatorSpec,
    datasets: dict[str, pd.DataFrame],
    config: dict[str, Any],
    rebase: bool = False,
) -> dict[str, Any]:
    visible_points = config["visible_points"]
    tolerance_values = config["normalized_tolerances"]
    references: dict[str, pd.DataFrame] = {}
    for dataset_name in config["comparison_datasets"]:
        result = output_frame(invoke_indicator(spec, datasets[dataset_name], True))
        if result is None:
            return {"status": "reference_missing"}
        references[dataset_name] = result.iloc[-visible_points:].copy()

    resolved: dict[str, int | None] = {str(tolerance): None for tolerance in tolerance_values}
    errors_by_candidate: dict[int, float | None] = {}
    for candidate_points in warmup_candidates(config["candidate_limit"]):
        max_error = 0.0
        comparable = True
        for dataset_name in config["comparison_datasets"]:
            source = datasets[dataset_name].iloc[-(visible_points + candidate_points) :]
            candidate = output_frame(invoke_indicator(spec, source, True))
            candidate_visible = candidate.iloc[-visible_points:].copy() if candidate is not None else None
            error = normalized_output_error(references[dataset_name], candidate_visible, rebase)
            if error is None:
                comparable = False
                break
            max_error = max(max_error, error)
        errors_by_candidate[candidate_points] = max_error if comparable else None
        if comparable:
            for tolerance in tolerance_values:
                key = str(tolerance)
                if resolved[key] is None and max_error <= tolerance:
                    resolved[key] = candidate_points
        if all(value is not None for value in resolved.values()):
            break

    measured_errors = [{"history_before_visible": points, "normalized_max_error": error} for points, error in errors_by_candidate.items() if error is not None]
    return {
        "status": "ok",
        "rebase_at_visible_start": rebase,
        "history_before_visible_by_tolerance": resolved,
        "last_measured_error": measured_errors[-1] if measured_errors else None,
    }


def compare_native_to_talib(spec: IndicatorSpec, frame: pd.DataFrame, visible_points: int) -> dict[str, Any]:
    delegated = output_frame(invoke_indicator(spec, frame, True))
    native = output_frame(invoke_indicator(spec, frame, False))
    if delegated is None or native is None:
        return {"status": "missing_output"}
    delegated = delegated.iloc[-visible_points:]
    native = native.iloc[-visible_points:]
    return {
        "status": "ok",
        "normalized_max_error": normalized_output_error(delegated, native, spec.code == "OBV"),
        "talib_fingerprint": frame_fingerprint(delegated),
        "native_fingerprint": frame_fingerprint(native),
    }


def verify_silent_fallback(frame: pd.DataFrame, failures: list[str]) -> dict[str, Any]:
    ema = next(spec for spec in INDICATORS if spec.code == "EMA")
    original_import_state = ta.Imports["talib"]
    fallback_result: pd.DataFrame | None = None
    fail_fast_error: str | None = None
    try:
        ta.Imports["talib"] = False
        fallback_result = output_frame(invoke_indicator(ema, frame, True))
        try:
            require_talib()
        except RuntimeError as exc:
            fail_fast_error = str(exc)
    finally:
        ta.Imports["talib"] = original_import_state

    native_result = output_frame(invoke_indicator(ema, frame, False))
    fallback_matches_native = fallback_result is not None and native_result is not None and frame_fingerprint(fallback_result) == frame_fingerprint(native_result)
    if not fallback_matches_native:
        failures.append("Silent fallback probe did not reproduce the native path")
    if fail_fast_error is None:
        failures.append("Fail-fast probe did not reject missing TA-Lib")
    return {
        "library_falls_back_silently": fallback_matches_native,
        "fail_fast_error": fail_fast_error,
    }


def require_talib() -> None:
    if not ta.Imports.get("talib"):
        raise RuntimeError("TA-Lib is required for delegated LibreFolio signal plugins")


def make_benchmark_frames(base: pd.DataFrame, asset_count: int, history_points: int) -> list[pd.DataFrame]:
    source = base.iloc[-history_points:]
    frames: list[pd.DataFrame] = []
    for asset_index in range(asset_count):
        frame = source.copy()
        price_factor = 1.0 + asset_index / 200.0
        volume_factor = 1.0 + asset_index / 100.0
        frame.loc[:, ("open", "high", "low", "close")] *= price_factor
        frame.loc[:, "volume"] *= volume_factor
        frames.append(frame)
    return frames


def calculate_asset_digest(frame: pd.DataFrame, talib_mode: bool) -> str:
    digest = hashlib.sha256()
    for spec in INDICATORS:
        digest.update(spec.code.encode())
        digest.update(output_fingerprint(invoke_indicator(spec, frame, talib_mode)).encode())
    return digest.hexdigest()


def benchmark_sequential(
    frames: list[pd.DataFrame],
    talib_mode: bool,
    rounds: int,
) -> dict[str, Any]:
    timings: list[float] = []
    expected_digests: list[str] | None = None
    stable = True
    for _ in range(rounds):
        started = perf_counter()
        digests = [calculate_asset_digest(frame, talib_mode) for frame in frames]
        timings.append(perf_counter() - started)
        if expected_digests is None:
            expected_digests = digests
        else:
            stable = stable and digests == expected_digests
    return {
        "seconds": timings,
        "median_seconds": float(np.median(timings)),
        "stable": stable,
        "digests": expected_digests,
    }


def benchmark_concurrency(
    frames: list[pd.DataFrame],
    workers: list[int],
    rounds: int,
    expected_digests: list[str],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for worker_count in workers:
        timings: list[float] = []
        stable = True
        for _ in range(rounds):
            started = perf_counter()
            with ThreadPoolExecutor(max_workers=worker_count) as executor:
                digests = list(executor.map(lambda frame: calculate_asset_digest(frame, True), frames))
            timings.append(perf_counter() - started)
            stable = stable and digests == expected_digests
        results[str(worker_count)] = {
            "seconds": timings,
            "median_seconds": float(np.median(timings)),
            "stable": stable,
        }
    return results


def run_benchmarks(
    datasets: dict[str, pd.DataFrame],
    config: dict[str, Any],
    failures: list[str],
) -> dict[str, Any]:
    frames = make_benchmark_frames(datasets["volatile"], config["assets"], config["history_points"])
    delegated = benchmark_sequential(frames, True, config["rounds"])
    native = benchmark_sequential(frames, False, config["rounds"])
    concurrency = benchmark_concurrency(
        frames,
        config["workers"],
        config["concurrency_rounds"],
        delegated["digests"],
    )
    if not delegated["stable"] or not native["stable"]:
        failures.append("Sequential benchmark produced unstable output")
    for worker_count, result in concurrency.items():
        if not result["stable"]:
            failures.append(f"Concurrent benchmark with {worker_count} workers changed output")
    return {
        "shape": {
            "assets": config["assets"],
            "history_points": config["history_points"],
            "signals_per_asset": len(INDICATORS),
        },
        "talib": {key: value for key, value in delegated.items() if key != "digests"},
        "native": {key: value for key, value in native.items() if key != "digests"},
        "talib_vs_native_speedup": native["median_seconds"] / delegated["median_seconds"],
        "concurrency": concurrency,
    }


def environment_report() -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "packages": {
            "numpy": version("numpy"),
            "pandas": version("pandas"),
            "pandas-ta-classic": version("pandas-ta-classic"),
            "TA-Lib": version("TA-Lib"),
        },
        "pandas_ta_imports_talib": bool(ta.Imports.get("talib")),
        "talib_c_version": getattr(talib, "__ta_version__", None),
    }


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    failures: list[str] = []
    require_talib()
    datasets = generate_datasets(manifest)
    fingerprints = {name: frame_fingerprint(frame) for name, frame in datasets.items()}
    for name, expected in manifest.get("expected_fingerprints", {}).items():
        if fingerprints.get(name) != expected:
            failures.append(f"Fixture fingerprint changed for {name}")

    backend_paths = verify_backend_paths(datasets, failures)
    dataset_behavior = verify_dataset_behavior(datasets, failures)
    silent_fallback = verify_silent_fallback(datasets["volatile"], failures)

    warmup: dict[str, Any] = {}
    native_differences: dict[str, Any] = {}
    minimum_points: dict[str, int | None] = {}
    minimum_probe_exceptions: dict[str, list[dict[str, Any]]] = {}
    for spec in INDICATORS:
        minimum_points[spec.code], minimum_probe_exceptions[spec.code] = probe_minimum_output(
            spec,
            datasets["volatile"],
        )
        warmup[spec.code] = measure_warmup(spec, datasets, manifest["warmup"])
        if spec.code == "OBV":
            warmup[spec.code]["rebased"] = measure_warmup(
                spec,
                datasets,
                manifest["warmup"],
                rebase=True,
            )
        native_differences[spec.code] = compare_native_to_talib(
            spec,
            datasets["volatile"],
            manifest["warmup"]["visible_points"],
        )

    benchmarks = None
    if not args.skip_benchmarks:
        benchmarks = run_benchmarks(datasets, manifest["benchmark"], failures)

    report = {
        "schema_version": 1,
        "environment": environment_report(),
        "fixture_manifest": str(FIXTURE_MANIFEST.relative_to(PROJECT_ROOT)),
        "fixture_fingerprints": fingerprints,
        "backend_paths": backend_paths,
        "dataset_behavior": dataset_behavior,
        "silent_fallback": silent_fallback,
        "minimum_complete_output_points": minimum_points,
        "minimum_probe_exceptions": minimum_probe_exceptions,
        "warmup": warmup,
        "native_vs_talib": native_differences,
        "benchmarks": benchmarks,
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(json_safe(report), indent=2, sort_keys=True, allow_nan=False) + "\n")

    print(f"Report: {args.output}")
    print(f"Indicators: {len(INDICATORS)}")
    print(f"Fixture fingerprints: {len(fingerprints)}")
    if benchmarks:
        print(f"TA-Lib batch median: {benchmarks['talib']['median_seconds']:.4f}s")
        print(f"Native batch median: {benchmarks['native']['median_seconds']:.4f}s")
        print(f"Measured speedup: {benchmarks['talib_vs_native_speedup']:.2f}x")
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("All hard spike gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
