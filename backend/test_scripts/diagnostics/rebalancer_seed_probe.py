#!/usr/bin/env python3
"""Check the Rebalancer's first stage against its seeds: no bound above a plan (lot S1 of project 67).

A diagnostic, not a test: it is not registered in the runner. The consultant's diagnosis of G5
(``67_rebalancer/notes/diagnosi-G5-soundness.md``, §6.2) found SCIP's cuts deducing a false bound on the old writing of
the distance, on some random seeds only. This probe solves the first stage of the heavy Rebalancer scenarios over several
seeds and branching priorities, and fails when a run's lower bound (or a stage it closes «optimal») sits above:

- the best plan any run of the same scenario found, valued «as the solver sees it» (``evaluation.solver_view``, row 6 of lot
  CR: money continuous, each posting less its reserve), within ``CLOSED_TOLERANCE``.

Since row 6 SCIP proves the optimum of that slightly pessimistic model, a few cents above the plan's published (exact)
score, so the checks compare like with like. The reference of lot S1, the exact score 796.70 € of a valid G5 plan, is a
published value: it bounds no model value any more, and is no longer used.

It also fails when a run's plan cannot be carried out: the planner's own step counter (``planner._executable_steps``)
refuses it, as it would refuse to publish it (lot CR of project 67: the cash rule makes every plan executable).

Scenarios: ``g5`` (the planner's real request on the test server's mock data,
``backend/test_scripts/fixtures/pac_allocator/rebalancer_plan_request.g5-browser.2-0-0.json``), ``g5-all-eur`` (the
same, with every USD price, route and cash moved to EUR at the request's rate, and no currency pair) and ``g5-one-route``
(one buy route per Asset: a case that closes, for the «closed above» check).

    pipenv run python backend/test_scripts/diagnostics/rebalancer_seed_probe.py
    ... --scenarios g5 --seeds 0-9 --priorities none,bin10qty20,bin20qty10 --budget 5

One line per run: scenario, seed, priorities, the machine's load, the stage's status, primal and dual in euros, the
candidate's score as the solver sees it and its exact (published) score. SCIP's timing depends on the machine: read every line with its load. Exit 1 when a check
fails. Priorities are a search parameter only (``chgVarBranchPriority``): they change no plan's value, so a bound that
moves above a plan under them is a defect of the bound.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("LIBREFOLIO_TEST_MODE", "1")

from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER  # noqa: E402
from backend.app.services.pac_allocator import planner, planner_report, rebalancer_report  # noqa: E402
from backend.app.services.pac_allocator.compiler import compile_policy_program  # noqa: E402
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, evaluate_exact_candidate, rounding_top_ups  # noqa: E402
from backend.app.services.pac_allocator.evaluation.solver_view import solver_view_objectives  # noqa: E402
from backend.app.services.pac_allocator.normalize import normalize_rebalancer_plan  # noqa: E402
from backend.app.services.pac_allocator.plan_sequence import PlanNotExecutableError  # noqa: E402
from backend.app.services.pac_allocator.solver import solve_policy_program  # noqa: E402

G5_REQUEST = PROJECT_ROOT / "backend/test_scripts/fixtures/pac_allocator/rebalancer_plan_request.g5-browser.2-0-0.json"
# How far above the best plan a closure may sit: after row 6 the closures of one scenario agree to four decimals (the
# consultant's measure, 16/11), so a tenth of a cent tells a false closure from SCIP's own precision.
CLOSED_TOLERANCE = Fraction(1, 1000)
PRIORITIES = {"none": None, "bin10qty20": (10, 20), "bin20qty10": (20, 10)}


def _g5() -> dict:
    return json.loads(G5_REQUEST.read_text())


def _all_eur(request: dict) -> dict:
    """Every USD price, route and cash in EUR at the request's rate; no pair. The objective changes (the cash targets
    merge), so its plans are not comparable with G5's."""
    request = copy.deepcopy(request)
    rate = Decimal(request["fx_rates"]["EUR/USD"])
    for asset in request["assets"]:
        if asset["quote"]["currency"] == "USD":
            asset["quote"]["amount"] = str((Decimal(asset["quote"]["amount"]) / rate).quantize(Decimal("0.0000000001")))
            asset["quote"]["currency"] = "EUR"
    for route in request["order_routes"]:
        route["capability_id"] = route["capability_id"].replace("mode:USD", "mode:EUR")
    eur = {cash["broker_id"]: cash for cash in request["existing_cash"] if cash["available"]["currency"] == "EUR"}
    for cash in [cash for cash in request["existing_cash"] if cash["available"]["currency"] == "USD"]:
        added = (Decimal(cash["available"]["amount"]) / rate).quantize(Decimal("0.01"))
        for side in ("available", "selected"):
            eur[cash["broker_id"]][side]["amount"] = str(Decimal(eur[cash["broker_id"]][side]["amount"]) + added)
    request["existing_cash"] = list(eur.values())
    usd = sum(Decimal(entry["weight"]) for entry in request["target_weights"] if entry["kind"] == "cash" and entry["currency"] == "USD")
    request["target_weights"] = [entry for entry in request["target_weights"] if not (entry["kind"] == "cash" and entry["currency"] == "USD")]
    for entry in request["target_weights"]:
        if entry["kind"] == "cash" and entry["broker_id"] == "broker:1":
            entry["weight"] = str(Decimal(entry["weight"]) + usd)
    for broker in request["brokers"]:
        if "capabilities" in broker:
            broker["capabilities"] = [capability for capability in broker["capabilities"] if not capability["capability_id"].endswith("mode:USD")]
    request["fx_rates"] = {}
    return request


def _one_route(request: dict) -> dict:
    """One buy route per Asset (Broker 2's): a G5 variant SCIP closes inside its window on the sound distance. Its objective
    differs from G5's (the fidelity level is calibrated on the scenario's own costs)."""
    request = copy.deepcopy(request)
    request["order_routes"] = [route for route in request["order_routes"] if route["broker_id"] == "broker:2"]
    return request


SCENARIOS = {"g5": _g5, "g5-all-eur": lambda: _all_eur(_g5()), "g5-one-route": lambda: _one_route(_g5())}


def executable(scenario, evaluation) -> bool:
    """Whether the planner's step counter finds an order the balances can follow, the steps built as the planner builds them."""
    sequence = planner_report._SequenceAllocator()
    try:
        planner._executable_steps(
            scenario,
            planner_report.build_ledger_rows(evaluation),
            planner_report.build_rounding_top_ups(scenario, rounding_top_ups(scenario, evaluation)),
            planner_report.build_funding_actions(scenario, evaluation, sequence),
            rebalancer_report.build_transfers(evaluation, sequence),
            planner_report.build_conversions(scenario, evaluation, sequence),
            planner_report.build_order_rows(scenario, evaluation, sequence),
        )
    except PlanNotExecutableError:
        return False
    return True


def run_once(request: dict, seed: int, priorities: tuple[int, int] | None, budget: float) -> dict:
    scenario = normalize_rebalancer_plan(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request)).normalized
    view = build_exact_policy_view(scenario)
    program = compile_policy_program(scenario, view)
    program.model.setParam("randomization/randomseedshift", seed)
    if priorities is not None:
        binary, quantity = priorities
        for var in program.variables.quanta.values():
            program.model.chgVarBranchPriority(var, quantity)
        pool = program.variables.pool
        for group in (program.variables.buy_active, program.variables.funding_active, program.variables.fx_active, *((pool.active, pool.moving) if pool is not None else ())):
            for var in group.values():
                program.model.chgVarBranchPriority(var, binary)
        for var in pool.net.values() if pool is not None else ():
            program.model.chgVarBranchPriority(var, quantity)
    load = os.getloadavg()[0]
    start = time.monotonic()
    run = solve_policy_program(program, time_budget_seconds=budget)
    stage = run.stages[0]
    exact = seen = None
    steps_ok = None
    if run.candidate is not None:
        evaluation = evaluate_exact_candidate(scenario, view, run.candidate)
        if evaluation.candidate_valid and evaluation.feasible:
            by_ref = {item.ref_id: item.value for item in evaluation.objectives}
            first = by_ref[view.objectives[0].ref_id]
            exact = Fraction(first.numerator, first.denominator)
            as_seen = solver_view_objectives(scenario, view, evaluation)[view.objectives[0].code]
            seen = Fraction(as_seen.numerator, as_seen.denominator)
            steps_ok = executable(scenario, evaluation)
    scale = float(stage.scale)
    band = getattr(next((item for item in program.objective_stages if item.code == stage.objective_code), None), "band", 0.0) / scale
    return {
        "band": band,
        "load": round(load, 2),
        "wall": round(time.monotonic() - start, 1),
        "status": stage.status,
        "primal": None if stage.primal is None else stage.primal / scale,
        "dual": None if stage.dual is None else stage.dual / scale,
        "exact": exact,
        "seen": seen,
        "executable": steps_ok,
    }


def _seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for part in text.split(","):
        low, _, high = part.partition("-")
        seeds += list(range(int(low), int(high) + 1)) if high else [int(low)]
    return seeds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenarios", default="g5,g5-all-eur", help="g5, g5-all-eur (default: both)")
    parser.add_argument("--seeds", default="0-9", help="seed shifts, e.g. 0-9 or 0,11 (default: 0-9)")
    parser.add_argument("--priorities", default="none,bin10qty20", help=f"branching priorities: {', '.join(PRIORITIES)}")
    parser.add_argument("--budget", type=float, default=5.0, help="SCIP time budget per run, seconds (default: 5)")
    args = parser.parse_args(argv)
    failures = 0
    for name in args.scenarios.split(","):
        request = SCENARIOS[name]()
        rows = []
        for priority in args.priorities.split(","):
            for seed in _seeds(args.seeds):
                row = run_once(request, seed, PRIORITIES[priority], args.budget) | {"seed": seed, "priority": priority}
                rows.append(row)
                print(
                    f"{name:<11} seed {seed:>2} {priority:<11} load {row['load']:>5} wall {row['wall']:>5}s {row['status']:<10} primal {row['primal']} dual {row['dual']} seen {None if row['seen'] is None else float(row['seen'])} exact {None if row['exact'] is None else float(row['exact'])} executable {row['executable']}",
                    flush=True,
                )
        best = min((row["seen"] for row in rows if row["seen"] is not None), default=None)
        if best is None:
            print(f"== {name}: {len(rows)} runs, no plan")
            failures += 1
            continue
        ceiling = best + CLOSED_TOLERANCE
        for row in rows:
            if row["executable"] is False:
                failures += 1
                print(f"FAIL {name} seed {row['seed']} {row['priority']}: the plan cannot be carried out (the step counter refuses it)")
            above = row["dual"] is not None and Fraction(row["dual"]) > ceiling
            # A closed stage's floating value may sit above its own plan's value by its quadratic rows' band.
            closed_above = row["status"] == "finished" and row["primal"] is not None and Fraction(row["primal"]) > ceiling + Fraction(row["band"])
            if above or closed_above:
                failures += 1
                print(f"FAIL {name} seed {row['seed']} {row['priority']}: {'closed «optimal»' if closed_above else 'bound'} at {row['dual']} €, above a plan of {float(best):.4f} € as the solver sees it")
        print(f"== {name}: {len(rows)} runs, best plan as the solver sees it {float(best):.4f} € (tolerance {float(CLOSED_TOLERANCE)} €)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
