"""The distance is written so that SCIP never expands a square into products (lot S1 of project 67).

Found on the G5 browser scenario (the consultant's diagnosis, journal ``67_rebalancer/notes/diagnosi-G5-soundness.md``): the
distance was written ``square ≥ (long sum)²``. SCIP expands such a row into pairwise products of integer variables, and its
cuts (cMIR, LCI) deduced at node 1 a false bound, «buy at least one unit of Asset 5 on Broker 1». Plans better than the one
published were excluded before the search, and the first stage could close «optimal» at a wrong value. The cure is one
auxiliary variable per residual, ``r = residual / √F``, and ``square ≥ r²``: the same function, no product, the score in
euros at scale 1.

The PAC keeps its own writing (``fixed_l2``, released in 1.3.0): rewritten the same way it lost the proof of its reference
case ``r-3x3`` and its node-1 incumbent got worse, and its sums are short (two or three variables per Asset). Whether to
harden it is a separate decision, with the A1 probe.

Two guards:
- the shape, on the compiled models: every quadratic row of the Rebalancer's distance squares exactly one variable, with no
  bilinear term (its score and the «Target first» chain);
- the behaviour, on the G5 request with the random seed that misled the search (shift 11), read at the solver: on the old
  model the first stage closed at 799.72 €, above a valid plan of the same scenario. That plan scores 796.70 € exactly: the as-is G5 plan
  found with Broker 1's purchases forbidden in the model, replayed against the full scenario
  (``67_rebalancer/notes/67-G5-diagnosis/result-as_is-broker1-buys-forbidden.json``). No bound may sit above it.
"""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

import pytest

from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view
from backend.app.services.pac_allocator.normalize import normalize_rebalancer_plan
from backend.app.services.pac_allocator.solver import solve_policy_program

G5_REQUEST = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator" / "rebalancer_plan_request.g5-browser.2-0-0.json"
# The exact score of a valid plan of the G5 scenario, «Balanced» (module docstring): no bound of the first stage may exceed it.
VALID_G5_PLAN_SCORE = Fraction("796.696628470523622586")


def _g5(fidelity: dict | None = None) -> dict:
    request = json.loads(G5_REQUEST.read_text())
    if fidelity is not None:
        request["target_fidelity"] = fidelity
    return request


def _rebalancer_model(request: dict):
    normalized = normalize_rebalancer_plan(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request)).normalized
    return compile_policy_program(normalized, build_exact_policy_view(normalized)).model


def _quadratic_shapes(model) -> dict[str, tuple[int, int]]:
    """Every quadratic row of the model: its name → (bilinear terms, squared variables)."""
    shapes = {}
    for cons in model.getConss():
        if not cons.isNonlinear():
            continue
        bilinear, squares, _linear = model.getTermsQuadratic(cons)
        shapes[cons.name] = (len(bilinear), len(squares))
    return shapes


@pytest.mark.parametrize(
    "fidelity",
    [pytest.param(None, id="balanced"), pytest.param({"kind": "target_first"}, id="target-first")],
)
def test_every_square_of_the_rebalancer_distance_holds_one_variable(fidelity: dict | None) -> None:
    shapes = _quadratic_shapes(_rebalancer_model(_g5(fidelity)))
    distance = {name: shape for name, shape in shapes.items() if name.startswith("distance_epigraph:")}
    # Seven Assets, two cash cells with a target, the uninvested row.
    assert len(distance) == 10
    assert {name: shape for name, shape in distance.items() if shape != (0, 1)} == {}


def test_the_seed_that_misled_the_search_no_longer_bounds_the_score_above_a_valid_plan() -> None:
    """Read at the solver, not through the planner: the subject is the first stage's bound, not the numbering of a plan."""
    normalized = normalize_rebalancer_plan(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(_g5())).normalized
    program = compile_policy_program(normalized, build_exact_policy_view(normalized))
    program.model.setParam("randomization/randomseedshift", 11)
    run = solve_policy_program(program, time_budget_seconds=6)
    stage = run.stages[0]
    assert stage.objective_code == "plan_score"
    assert stage.dual is not None
    dual = Fraction(stage.dual) / stage.scale
    # A lower bound above a valid plan is false. Its quadratic rows let the stage sit below the truth by its band, never above.
    assert dual <= VALID_G5_PLAN_SCORE, f"stage 1 bounds the score at {float(dual):.2f} €, above a valid plan of {float(VALID_G5_PLAN_SCORE):.2f} €"
