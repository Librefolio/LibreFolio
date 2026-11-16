"""The Rebalancer's money is continuous in the model, with a reserve per rounded posting (row 6 of lot CR, project 67).

Specification §16.6–16.7 (journal ``67_rebalancer/specifica-REB.md``): with the cents inside the solver, one integer and three
or four rows per rounded posting, SCIP closed the first stage «optimal» at false values on G5 (every seed, 786–800 €, while a
775.81 € plan exists). Out of the model, the postings are the exact amounts, and each one that happens keeps back the worst
case of its rounding (``posting_reserve``): SCIP proves the optimum of a slightly pessimistic model, and the exact replay
still rounds every posting against the plan, as always. The published values are the replay's, unchanged.

The cascade compares SCIP's numbers with exact ones (pins, D4, the bound check). Those comparisons read the plan's value
«as the solver sees it» (``evaluation.solver_view``): the same postings, continuous, less their reserves, in exact
arithmetic. On the same plan it equals SCIP's value; that is the first guard here.

The PAC keeps its rounded postings: its model does not move.
"""

from __future__ import annotations

import json
from fractions import Fraction

import pytest

from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER
from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import CandidateActionVector, CandidateDecision
from backend.app.services.pac_allocator.normalize import normalize_rebalancer_plan
from backend.app.services.pac_allocator.numeric import ExactRatio as R
from backend.app.services.pac_allocator.solver import solve_policy_program
from backend.test_scripts.test_services import _reb_small_cases as cases
from backend.test_scripts.test_services.test_pac_planner_cash_rule import G5_REQUEST
from backend.test_scripts.test_services.test_pac_planner_oracle import _two_asset_pac_scenario

# A G5 plan (seed 0 of the CR sweep): its purchases, its two conversions into dollars, and Broker 1's euros sent to Broker 2.
G5_PLAN = {
    "buy:route:12": 9,
    "buy:route:14": 16,
    "buy:route:20": 12,
    "buy:route:7": 1,
    "buy:route:8": 11,
    "fx:8:broker:1:EUR:USD": 180_563,
    "fx:8:broker:2:EUR:USD": 1_731_020,
    "transfer:8:broker:18:broker:2:EUR": 940_671,
}
G5_NETS = {("broker:1", "EUR"): -940_671, ("broker:2", "EUR"): 940_671, ("broker:1", "USD"): 0, ("broker:2", "USD"): 0}
# The exact values the replay publishes for G5_PLAN, recorded before row 6: they must not move.
G5_PLAN_SCORE = Fraction(924164374068006298984835975679602330578943967943, 1164330760132714530580354293086457500000000000)
G5_TARGET_FIRST = {"target_distance": Fraction(924126483954158074079868431718099932518943967943, 19604344020668682250000000000000000000000), "wealth_loss": Fraction(1139110107, 35003878375)}


def _scenario(target_first: bool):
    """The G5 scenario, «Balanced» or «Target first»."""
    request = json.loads(G5_REQUEST.read_text())
    if target_first:
        request["target_fidelity"] = {"kind": "target_first"}
    outcome = normalize_rebalancer_plan(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(request))
    assert outcome.ready, [issue.code for issue in outcome.issues]
    return outcome.normalized


def _candidate(view) -> CandidateActionVector:
    return CandidateActionVector(view_id=view.view_id, candidate_id="candidate:g5-plan", decisions=tuple(CandidateDecision(decision_id=access.decision_id, quanta=G5_PLAN.get(access.decision_id, 0)) for access in view.decisions))


def _model_value_on_the_plan(scenario, view, stage_index: int) -> float:
    """SCIP's value of a stage with every decision of G5_PLAN fixed (the balances too): what remains are the model's own
    auxiliary variables (fees, the distance's squares), which minimizing sets to their exact values."""
    program = compile_policy_program(scenario, view)
    model = program.model
    for access in view.decisions:
        if access.family == "broker_transfer":
            continue
        variable = program.variables.quanta[access.decision_id]
        model.chgVarLb(variable, G5_PLAN.get(access.decision_id, 0))
        model.chgVarUb(variable, G5_PLAN.get(access.decision_id, 0))
    for cell, balance in program.variables.pool.net.items():
        model.chgVarLb(balance, G5_NETS[cell])
        model.chgVarUb(balance, G5_NETS[cell])
    stage = program.objective_stages[stage_index]
    model.setObjective(stage.expression, "minimize")
    model.optimize()
    assert model.getStatus() == "optimal"
    return model.getObjVal() / float(stage.scale)


def _solver_view(scenario, view) -> dict[str, Fraction]:
    from backend.app.services.pac_allocator.evaluation.solver_view import solver_view_objectives  # noqa: PLC0415 - comes with row 6

    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view))
    assert evaluation.feasible, evaluation.conflict_codes
    return {code: Fraction(value.numerator, value.denominator) for code, value in solver_view_objectives(scenario, view, evaluation).items()}


# ---------------------------------------------------------------------------
# The model
# ---------------------------------------------------------------------------


def test_the_rebalancer_model_has_no_rounding_variable() -> None:
    """G5: no posting-unit integer, the conversion still a whole number of minor units."""
    scenario = _scenario(target_first=False)
    program = compile_policy_program(scenario, build_exact_policy_view(scenario))
    names = {var.name: var.vtype() for var in program.model.getVars()}
    assert not [name for name in names if name.startswith("posted_")]
    fx = [access.decision_id for access in program.view.decisions if access.family == "fx_debit"]
    assert fx and all(names[decision_id] == "INTEGER" for decision_id in fx)


def test_the_pac_keeps_its_rounded_postings() -> None:
    """The PAC's model does not move: its buys still post through rounding integers."""
    scenario = _two_asset_pac_scenario()
    program = compile_policy_program(scenario, build_exact_policy_view(scenario))
    assert [var.name for var in program.model.getVars() if var.name.startswith("posted_buy_debit:")]


# ---------------------------------------------------------------------------
# The value «as the solver sees it» equals SCIP's, and the published one does not move
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("reserve", [True, False], ids=["reserve", "no-reserve"])
def test_scip_and_the_solver_view_agree_on_a_fixed_plan_balanced(monkeypatch: pytest.MonkeyPatch, reserve: bool) -> None:
    """«Balanced» on G5: SCIP's ``plan_score`` of the fixed plan is the replay's value «as the solver sees it», with the
    reserve and without it (the switch the developer has not chosen yet)."""
    from backend.app.services.pac_allocator import posting_reserve  # noqa: PLC0415 - comes with row 6

    monkeypatch.setattr(posting_reserve, "RESERVE_ENABLED", reserve)
    scenario = _scenario(target_first=False)
    view = build_exact_policy_view(scenario)
    solver_view = _solver_view(scenario, view)
    assert _model_value_on_the_plan(scenario, view, 0) == pytest.approx(float(solver_view["plan_score"]), rel=1e-9, abs=1e-6)


def test_scip_and_the_solver_view_agree_on_a_fixed_plan_target_first() -> None:
    """«Target first»: the distance and then the money lost, each SCIP's value equal to the solver view's."""
    scenario = _scenario(target_first=True)
    view = build_exact_policy_view(scenario)
    solver_view = _solver_view(scenario, view)
    assert _model_value_on_the_plan(scenario, view, 0) == pytest.approx(float(solver_view["target_distance"]), rel=1e-9)
    assert _model_value_on_the_plan(scenario, view, 1) == pytest.approx(float(solver_view["wealth_loss"]), rel=1e-9, abs=1e-6)


def test_the_reserve_makes_the_solver_view_pessimistic_and_the_published_value_stays() -> None:
    """With the reserve the solver sees the plan a few cents worse than it is; the replay publishes the same exact values as
    before row 6."""
    scenario = _scenario(target_first=False)
    view = build_exact_policy_view(scenario)
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view))
    published = {ref.code: next(item.value for item in evaluation.objectives if item.ref_id == ref.ref_id) for ref in view.objectives}
    assert Fraction(published["plan_score"].numerator, published["plan_score"].denominator) == G5_PLAN_SCORE
    solver_view = _solver_view(scenario, view)
    assert Fraction(0) < solver_view["plan_score"] - G5_PLAN_SCORE < Fraction(1, 10)

    target_first = _scenario(target_first=True)
    view = build_exact_policy_view(target_first)
    evaluation = evaluate_exact_candidate(target_first, view, _candidate(view))
    published = {ref.code: next(item.value for item in evaluation.objectives if item.ref_id == ref.ref_id) for ref in view.objectives}
    assert {code: Fraction(published[code].numerator, published[code].denominator) for code in G5_TARGET_FIRST} == G5_TARGET_FIRST


# ---------------------------------------------------------------------------
# The cascade
# ---------------------------------------------------------------------------


def test_the_g5_cascade_closes_with_no_anomaly() -> None:
    """G5 «Balanced» at the solver: the first stage's bounds hold the plan's value as the solver sees it, so no anomaly; with
    the cents inside every seed closed falsely and was flagged."""
    scenario = _scenario(target_first=False)
    view = build_exact_policy_view(scenario)
    run = solve_policy_program(compile_policy_program(scenario, view), time_budget_seconds=20)
    assert run.anomaly is None
    assert run.candidate is not None


# ---------------------------------------------------------------------------
# Which postings keep a reserve
# ---------------------------------------------------------------------------


def test_a_posting_keeps_a_reserve_only_where_it_can_round() -> None:
    """A posting whose every amount is a whole number of minor units never rounds and keeps nothing: T4 buys by amount in
    steps of one euro with a fixed fee of five euros. A conversion credits a fine step (EUR → USD at 1.12 credits 0.0112…
    $ per source cent): one cent. (Before row 6 the same lattice tightened the rounding rows, ``_exact_gap``.)"""
    from backend.app.services.pac_allocator.posting_reserve import posting_reserves  # noqa: PLC0415 - comes with row 6

    t4 = posting_reserves(cases.t4())
    assert set(t4.values()) == {R(0)} and "buy-debit:route:buy:asset:b" in t4 and "buy-fee:route:buy:asset:b" in t4
    g5 = posting_reserves(_scenario(target_first=False))
    assert {value for key, value in g5.items() if key.startswith("fx-credit:")} == {R(1, 100)}


def test_at_an_exact_multiple_the_model_spends_the_cell_to_its_last_cent() -> None:
    """T4: 195 € of B and a 5 € fee out of 200 € is the hand-computed plan (specifica §11). Nothing rounds, so nothing is
    kept back and the model reaches it; with a cent kept on each it would buy 194."""
    view, run = build_exact_policy_view(cases.t4()), None
    run = solve_policy_program(compile_policy_program(cases.t4(), view), time_budget_seconds=10)
    quanta = {item.decision_id: item.quanta for item in run.candidate.decisions}
    assert quanta[cases.buy_decision("asset:b")] == 195


# ---------------------------------------------------------------------------
# A SCIP failure inside a stage is data, not an exception
# ---------------------------------------------------------------------------


def _failing_on(monkeypatch: pytest.MonkeyPatch, call: int) -> None:
    """The compiler builds a SCIP model whose ``optimize`` raises on its ``call``-th run, as PySCIPOpt does on an error code
    («SCIP: error in LP solver!»)."""
    from pyscipopt import Model  # noqa: PLC0415 - the class the compiler builds, subclassed to fail on cue

    from backend.app.services.pac_allocator import compiler  # noqa: PLC0415

    class FailingModel(Model):
        calls = 0

        def optimize(self):
            FailingModel.calls += 1
            if FailingModel.calls == call:
                raise Exception("SCIP: error in LP solver!")  # noqa: TRY002 - what PySCIPOpt raises
            return super().optimize()

    monkeypatch.setattr(compiler, "Model", FailingModel)


def _plan(product: str):
    from backend.app.schemas.pac_allocator.preview import REBALANCER_TOOL_INPUT_ADAPTER  # noqa: PLC0415
    from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER  # noqa: PLC0415
    from backend.app.services.pac_allocator.planner import plan_pac_allocation, plan_rebalancing  # noqa: PLC0415
    from backend.test_scripts.test_services import _pac_reference_values as reference  # noqa: PLC0415
    from backend.test_scripts.test_services import _reb_small_requests as reb  # noqa: PLC0415

    if product == "pac":
        return plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(reference.CASES["r-3x3"]()))
    payload = reb.t4()
    payload["operation"] = "plan"
    return plan_rebalancing(REBALANCER_TOOL_INPUT_ADAPTER.validate_python(payload))


@pytest.mark.parametrize("product", ["pac", "rebalancer"])
def test_a_scip_failure_in_a_later_stage_keeps_the_best_plan(monkeypatch: pytest.MonkeyPatch, product: str) -> None:
    """G5 seed 5 at 30 s: SCIP met «unresolved numerical troubles in LP» in a tie-break and raised; the whole plan failed
    (``execution_failed``), although every named stage had closed. ``solve_policy_program`` promises never to raise on a
    solver outcome: the failed stage is reported (``solver_error``), the cascade stops with an anomaly, and the best plan
    so far is published, not proven. The cascade is shared, so the PAC (r-3x3) gets it too. SCIP fails on its third
    ``optimize``."""
    _failing_on(monkeypatch, 3)
    result = _plan(product)

    assert result.result_state == "ready_incumbent"
    assert result.proof.kind == "not_proven"
    assert result.stop_reason == "time_limit"
    statuses = [stage.status for stage in result.solver_evidence.stages]
    assert statuses[:2] == ["finished", "finished"] and "unfinished" in statuses


@pytest.mark.parametrize("product", ["pac", "rebalancer"])
def test_a_scip_failure_before_any_plan_fails_the_run_as_before(monkeypatch: pytest.MonkeyPatch, product: str) -> None:
    """With no plan held there is nothing to keep: the run fails as it did before (``execution_failed`` for the user), and
    does not read as «no plan within the time limit», which would ask for a budget that is not the cause."""
    from backend.app.services.pac_allocator.solver import SolverStageError  # noqa: PLC0415

    _failing_on(monkeypatch, 1)
    with pytest.raises(SolverStageError):
        _plan(product)


def test_a_fee_that_could_be_zero_on_some_active_orders_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The fee's reserve rides on the buy's binary, so a schedule that can charge must charge every active order (the
    consultant's condition). ``fixed + clamp(rate × notional, floor, cap)`` always does when it can charge at all; a
    schedule with nothing to charge but a positive upper bound would break the model = solver-view equality, and the
    compiler refuses it. Forced here: T4 without its fixed fee, its upper bound made positive."""
    from dataclasses import replace  # noqa: PLC0415

    from backend.app.services.pac_allocator.constraints import cells  # noqa: PLC0415

    base = cases.t4()
    free = tuple(replace(item, fixed_fee=replace(item.fixed_fee, amount=R(0))) for item in base.brokers[0].fee_schedules)
    scenario = replace(base, brokers=(replace(base.brokers[0], fee_schedules=free),))
    monkeypatch.setattr(cells, "_fee_variable_upper", lambda *_args: 1.0)
    with pytest.raises(cells.LedgerPostingScopeError, match="can charge some active orders"):
        compile_policy_program(scenario, build_exact_policy_view(scenario))
