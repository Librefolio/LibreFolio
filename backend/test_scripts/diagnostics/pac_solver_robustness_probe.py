#!/usr/bin/env python3
"""Measure what the PAC planner publishes on the synthetic solver grids.

Solver robustness slice, 2026-10. A diagnostic, not a test: it is not
registered in the runner. It plans every variant of
``backend/test_scripts/test_services/_pac_synthetic_requests.py`` -- ``m-*``,
the multi-broker grid ``V``, and ``r-*``, the realistic grid -- through the
real ``plan_pac_allocation`` and prints one line per variant: the 1-minute
load average before it, the wall seconds, ``result_state``, the proof kind,
``stop_reason`` and the exact objective vector of the published solution (or
the exception type when the planner raises). SCIP's timing depends on the
machine, so read every line with its load.

    pipenv run python backend/test_scripts/diagnostics/pac_solver_robustness_probe.py --only m-5x2,r-10x3
    ... --budget 30 --record /tmp/pac_before.json
    ... --budget 30 --compare /tmp/pac_before.json

``--compare`` reads the old record before ``--record`` writes the new one, so
both may name the same file. The exit status is 1 when a check line fails.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Callable
from fractions import Fraction
from functools import partial
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("LIBREFOLIO_TEST_MODE", "1")

from backend.app.schemas.pac_allocator import PAC_PLAN_INPUT_ADAPTER, _exact_fraction  # noqa: E402
from backend.app.services.pac_allocator.planner import plan_pac_allocation  # noqa: E402
from backend.test_scripts.test_services._pac_synthetic_requests import V, make, realistic_make  # noqa: E402

REALISTIC_SHAPES = ((3, 2), (5, 2), (8, 2), (12, 2), (3, 3), (5, 3), (8, 3), (10, 3))
VARIANTS: dict[str, Callable[[], dict]] = {
    **{f"m-{name}": partial(make, **settings) for name, settings in V.items()},
    **{f"r-{assets}x{brokers}": partial(realistic_make, assets, brokers) for assets, brokers in REALISTIC_SHAPES},
}

type Vector = tuple[Fraction, ...]


def _vector_of(*values: int | str) -> Vector:
    return tuple(Fraction(value) for value in values)


# variant -> (relation, reference vector). "==" holds only for a proven run;
# "<=" is lexicographic and holds for any run that publishes a plan.
CHECKS: dict[str, tuple[str, Vector]] = {
    "m-5x2": ("==", _vector_of(475, 25, 9, "239/40", 6)),
    "m-10x2": ("<=", _vector_of(3100, 35, 15, "1593/200", 10)),
    "r-10x3": ("<=", _vector_of("11098593/2500", "333/10", 15, "1549/100", 10)),
}


def _published_vector(result: object) -> Vector | None:
    """The exact objective values of the published solution, in ordinal order."""
    solution = getattr(result, "primary_solution", None)
    if solution is None:
        return None
    return tuple(_exact_fraction(stage.value) for stage in solution.objectives.stages)


def run_variant(name: str, budget: float) -> dict:
    """Plan one variant; never raises, the exception type is part of the row."""
    load = os.getloadavg()[0]
    payload = VARIANTS[name]()
    started = time.perf_counter()
    try:
        result = plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(payload), solver_time_budget_seconds=budget)
    except Exception as error:  # a probe reports every failure and goes on with the grid
        return {"load": load, "wall": time.perf_counter() - started, "error": type(error).__name__, "state": None, "proof": None, "stop": None, "vector": None}
    wall = time.perf_counter() - started
    proof = getattr(result, "proof", None)
    return {
        "load": load,
        "wall": wall,
        "error": None,
        "state": result.result_state,
        "proof": getattr(proof, "kind", None),
        "stop": getattr(result, "stop_reason", None),
        "vector": _published_vector(result),
    }


def _format_vector(vector: Vector | None) -> str:
    return "no vector" if vector is None else "(" + ", ".join(str(value) for value in vector) + ")"


def print_row(name: str, row: dict) -> None:
    outcome = f"raised {row['error']}" if row["error"] else f"{row['state']} {row['proof']} {row['stop']}"
    print(f"{name:<28} load {row['load']:5.2f}  wall {row['wall']:7.2f}s  {outcome}  {_format_vector(row['vector'])}", flush=True)


def _check_verdict(relation: str, reference: Vector, row: dict) -> tuple[bool, str]:
    vector = row["vector"]
    if vector is None:
        return False, f"no published vector ({row['error'] or row['state']})"
    if relation == "==" and row["proof"] != "optimal_proven":
        return True, f"proof {row['proof']}: equality not required, got {_format_vector(vector)}"
    holds = vector == reference if relation == "==" else vector <= reference
    return holds, f"{_format_vector(vector)} {relation} {_format_vector(reference)}"


def run_checks(rows: dict[str, dict]) -> int:
    """Print one PASS/FAIL line per checked variant that ran; return the failures."""
    failures = 0
    for name, (relation, reference) in CHECKS.items():
        if name not in rows:
            continue
        holds, detail = _check_verdict(relation, reference, rows[name])
        failures += not holds
        print(f"{'PASS' if holds else 'FAIL'} {name}: {detail}")
    return failures


def _recorded_vector(entry: dict) -> Vector | None:
    return None if entry.get("vector") is None else tuple(Fraction(text) for text in entry["vector"])


def _comparison(old: Vector | None, new: Vector | None) -> str:
    if old is None or new is None:
        sides = [side for side, vector in (("recorded", old), ("current", new)) if vector is None]
        return f"no vector ({' and '.join(sides)})"
    if new < old:
        return "improved"
    return "same" if new == old else "REGRESSION"


def compare(rows: dict[str, dict], recorded: dict[str, dict]) -> None:
    """Per variant, the current vector against the recorded one, lexicographically."""
    for name, row in rows.items():
        verdict = "not in the record" if name not in recorded else _comparison(_recorded_vector(recorded[name]), row["vector"])
        print(f"{name:<28} {verdict}")


def _record_entry(row: dict) -> dict:
    vector = row["vector"]
    return {
        "state": row["state"],
        "proof": row["proof"],
        "stop": row["stop"],
        "vector": None if vector is None else [str(value) for value in vector],
        "wall": round(row["wall"], 3),
        "error": row["error"],
    }


def _selected(only: str | None) -> list[str]:
    if not only:
        return list(VARIANTS)
    names = [name.strip() for name in only.split(",") if name.strip()]
    unknown = [name for name in names if name not in VARIANTS]
    if unknown:
        raise SystemExit(f"unknown variant(s) {', '.join(unknown)}; known: {', '.join(VARIANTS)}")
    return names


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", metavar="NAME[,NAME...]", help="the variants to run (default: all of them)")
    parser.add_argument("--budget", metavar="SECONDS", type=float, default=30.0, help="SCIP time budget per plan (default: 30)")
    parser.add_argument("--record", metavar="PATH", type=Path, help="write the results to this JSON file")
    parser.add_argument("--compare", metavar="PATH", type=Path, help="compare the vectors with a JSON file written by --record")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    names = _selected(args.only)
    recorded = json.loads(args.compare.read_text()) if args.compare else None
    rows = {}
    for name in names:
        rows[name] = run_variant(name, args.budget)
        print_row(name, rows[name])
    failures = run_checks(rows)
    if recorded is not None:
        compare(rows, recorded)
    if args.record:
        args.record.write_text(json.dumps({name: _record_entry(row) for name, row in rows.items()}, indent=2) + "\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
