"""Contract tests for the lexicographic SCIP search adapter (Step 3, Stage 3).

`solver.py` takes a `CompiledProgram` (from `compiler.py`) and runs the
cascade `fixed_l2 -> shortfall -> route_priority -> explicit_cost ->
active_order_rows -> canonical tie-breaks` as a genuine lexicographic search:
solve stage *k*, freeze its optimum as a hard constraint, then solve stage
*k+1* on that face. It never decides anything about proof -- it returns a
candidate plus a pile of explicitly floating, explicitly non-authoritative
facts, and the only source of truth for feasibility and for every reported
number is the Decimal-exact `evaluate_exact_candidate` replay.

The keystone here is `test_solver_incumbent_equals_exhaustive_oracle_optimum`
(item B1): a parametrized gate asserting that, for every toy fixture, the
solver's incumbent equals the exhaustive oracle's proven optimum *exactly* --
same decision quanta and the same full lexicographic key (the tuple of exact
objective values in ascending-ordinal order, plus `canonical_tie_quanta`).
The oracle (`oracle.py`) has zero SCIP dependency and enumerates the whole
discrete domain, so it is independent ground truth. Adding a fixture to
`_ORACLE_AGREEMENT_FIXTURES` automatically extends the gate. From here on
"solver green" means "oracle-agreement green".

Scope, as everywhere else in this package: PAC `proportional` policy,
`primary` purpose only. Every fixture is small enough for the oracle to
enumerate in a fraction of a second (the coarse funding/FX case, which is the
fixture that caught the Step3 §16.11 HALF_UP ledger defect, has 585
candidates; the rest are in the tens). Fixtures with a *binding* fee cap are
deliberately excluded from the agreement gate: the fee epigraph is documented
cap-oblivious (`compiler.py`), so a capped route could legitimately bias which
candidate the solver prefers -- that is a known modelling limitation, not a
disagreement the gate should police.

These are pure in-process tests (`isolation="pure"`): no server, no database,
no clock assertions, no network. Two ready-made scenario fixtures are imported
from the sibling oracle suite (`_two_asset_pac_scenario`,
`_coarse_funding_fx_scenario`), exactly the way that module imports its own
primitives from `test_pac_planner_evaluator.py`.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from backend.app.services.pac_allocator.compiler import compile_policy_program
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view, evaluate_exact_candidate
from backend.app.services.pac_allocator.models import CandidateActionVector, ExactEvaluation, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.oracle import run_exhaustive_oracle
from backend.app.services.pac_allocator.solver import (
    DEFAULT_SOLVER_TIME_BUDGET_SECONDS,
    ENGINE_NAME,
    SolverRunResult,
    SolverStageReport,
    solve_policy_program,
)
from backend.test_scripts.test_services.test_pac_planner_evaluator import ZERO, R, _pac_scenario
from backend.test_scripts.test_services.test_pac_planner_oracle import _coarse_funding_fx_scenario, _two_asset_pac_scenario

# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _run(scenario: ExactPlannerScenario, **kwargs) -> tuple[ExactPolicyView, SolverRunResult]:
    """Build the view, compile a fresh model, and run the lexicographic solve.

    A fresh `compile_policy_program` per call keeps every solve on its own
    `Model` -- the solver itself never re-`optimize()`s a stale one, but a
    test that solved the same program twice would (see the policy-compiler
    suite's module docstring on that PySCIPOpt trap).
    """
    view = build_exact_policy_view(scenario)
    program = compile_policy_program(scenario, view)
    return view, solve_policy_program(program, **kwargs)


def _quanta(candidate: CandidateActionVector) -> dict[str, int]:
    """One candidate's decisions as a plain `decision_id -> quanta` dict."""
    return {decision.decision_id: decision.quanta for decision in candidate.decisions}


def _lexicographic_key(view: ExactPolicyView, evaluation: ExactEvaluation) -> tuple[tuple, tuple[int, ...]]:
    """The full total-order key: exact objective values in ascending-ordinal
    order, then the canonical tie-break vector.

    Built only from an `evaluate_exact_candidate` result, so every value is
    exact (`ExactRatio`) and comparable with `==`, never a SCIP float. This
    is an independent re-implementation of the same key `oracle.py` uses --
    it does not import `oracle._lexicographic_key`.
    """
    ordered_ref_ids = tuple(objective.ref_id for objective in sorted(view.objectives, key=lambda objective: objective.ordinal))
    values_by_ref_id = {objective.ref_id: objective.value for objective in evaluation.objectives}
    stage_values = tuple(values_by_ref_id[ref_id] for ref_id in ordered_ref_ids)
    return stage_values, evaluation.canonical_tie_quanta


# --------------------------------------------------------------------------
# Oracle-agreement fixtures (each one automatically extends the B1 gate)
# --------------------------------------------------------------------------


def _single_buy_scenario() -> ExactPlannerScenario:
    """One BUY route, no funding/FX: the plainest cascade there is."""
    return _pac_scenario(price=R(10), route_cap=R(5))


def _proportional_fee_no_cap_scenario() -> ExactPlannerScenario:
    """A proportional fee with a floor but *no* cap, so the fee epigraph is
    exact (the cap-oblivious bias cannot apply) and `explicit_cost` genuinely
    discriminates between candidates.
    """
    return _pac_scenario(price=R(10), fee_rate=R(1, 10), fee_floor=R(5), fee_cap=None, route_cap=R(6), cash=R(1000))


def _execution_margin_scenario() -> ExactPlannerScenario:
    """A BUY execution margin, so `explicit_cost`'s execution-margin-loss term
    is nonzero and the cascade has to weigh it.
    """
    return _pac_scenario(price=R(10), margin=R(1, 20), route_cap=R(6))


_ORACLE_AGREEMENT_FIXTURES = [
    pytest.param(_two_asset_pac_scenario, id="two_asset_pac"),
    pytest.param(_coarse_funding_fx_scenario, id="coarse_funding_fx"),  # the fixture that caught the Step3 §16.11 defect
    pytest.param(_single_buy_scenario, id="single_buy"),
    pytest.param(_proportional_fee_no_cap_scenario, id="proportional_fee_no_cap"),
    pytest.param(_execution_margin_scenario, id="execution_margin"),
]


# --------------------------------------------------------------------------
# B1: THE oracle-agreement gate (the most important test in this file)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("build_scenario", _ORACLE_AGREEMENT_FIXTURES)
def test_solver_incumbent_equals_exhaustive_oracle_optimum(build_scenario: Callable[[], ExactPlannerScenario]) -> None:
    """The solver's incumbent must equal the exhaustive oracle's proven
    optimum *exactly* -- same decision quanta and the same full lexicographic
    key. This is the gate that would have caught the Step3 §16.11 ledger
    defect: with the old exact-sum ledger, the solver's incumbent on the
    coarse funding/FX fixture disagreed with the oracle.

    The solver's candidate is replayed through `evaluate_exact_candidate`
    first and required to be feasible; the comparison is then between two
    Decimal-exact evaluations, never against SCIP's floating values.
    """
    scenario = build_scenario()
    view, result = _run(scenario)

    assert result.outcome == "incumbent"
    assert result.candidate is not None

    # Never trust SCIP's floats: the incumbent is only a proposal until it
    # survives an exact replay.
    solver_evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    assert solver_evaluation.feasible is True

    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.best_candidate is not None
    assert oracle.best_evaluation is not None

    # (1) same decision quanta ...
    assert _quanta(result.candidate) == _quanta(oracle.best_candidate)
    # (2) ... and the same full lexicographic key (exact objective values in
    # ascending-ordinal order + the canonical tie-break vector).
    assert _lexicographic_key(view, solver_evaluation) == _lexicographic_key(view, oracle.best_evaluation)


# --------------------------------------------------------------------------
# B2: cascade structure follows the view's own ordinals
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build_scenario",
    [pytest.param(_two_asset_pac_scenario, id="two_asset"), pytest.param(_coarse_funding_fx_scenario, id="coarse_funding_fx")],
)
def test_cascade_stage_structure_follows_view_ordinals(build_scenario: Callable[[], ExactPlannerScenario]) -> None:
    """Stage codes and ordinals come from the view's own ordinals, never a
    hardcoded list here: the five named objective stages in ascending ordinal
    order, then one `tie:<decision_id>` stage per canonical tie-break decision.
    Stage 0 is `global`, every later stage is `incumbent_face`, `sense` is
    always `min`, and `finished_stage_count` is exactly the number of finished
    stages.
    """
    scenario = build_scenario()
    view, result = _run(scenario)

    named_codes = tuple(objective.code for objective in sorted(view.objectives, key=lambda objective: objective.ordinal))
    tie_codes = tuple(f"tie:{decision_id}" for decision_id in view.tie_breaks[0].decision_ids)
    expected_codes = named_codes + tie_codes

    assert tuple(stage.stage for stage in result.stages) == expected_codes
    assert tuple(stage.ordinal for stage in result.stages) == tuple(range(1, len(result.stages) + 1))

    for stage in result.stages:
        assert isinstance(stage, SolverStageReport)
        assert stage.objective_code == stage.stage
        assert stage.sense == "min"
        assert stage.scope == ("global" if stage.ordinal == 1 else "incumbent_face")

    assert result.finished_stage_count == sum(1 for stage in result.stages if stage.status == "finished")
    assert result.exact_replay_required is True


# --------------------------------------------------------------------------
# B3: evidence shape (engine, version, settings, tolerances)
# --------------------------------------------------------------------------


def test_solver_evidence_reports_engine_settings_and_real_tolerances() -> None:
    """The wire-evidence block is the engine name, a non-empty version, the
    settings actually applied (always `limits/time`), and the tolerances read
    back from SCIP itself (`feasibility == 1e-6`, `integrality == 1e-9` by
    default), not values this module made up.
    """
    _view, result = _run(_two_asset_pac_scenario())

    assert result.engine == ENGINE_NAME == "SCIP"
    assert result.version  # non-empty engine version string

    setting_by_name = {setting.name: setting.value for setting in result.settings}
    assert "limits/time" in setting_by_name
    assert setting_by_name["limits/time"] == f"{DEFAULT_SOLVER_TIME_BUDGET_SECONDS:g}"
    assert "limits/nodes" not in setting_by_name  # no node limit was requested

    assert result.tolerances.feasibility == 1e-6
    assert result.tolerances.integrality == 1e-9


def test_solver_node_limit_is_reported_in_settings() -> None:
    """Passing `node_limit` applies `limits/nodes` and records it as evidence
    alongside `limits/time`.
    """
    _view, result = _run(_two_asset_pac_scenario(), node_limit=1)

    setting_by_name = {setting.name: setting.value for setting in result.settings}
    assert setting_by_name.get("limits/nodes") == "1"
    assert "limits/time" in setting_by_name


# --------------------------------------------------------------------------
# B4: honest limit behaviour (no fabricated observations)
# --------------------------------------------------------------------------


def test_zero_time_budget_yields_no_incumbent_without_fabricated_observations() -> None:
    """A deliberately impossible time budget must not crash: it returns
    `no_incumbent` with no candidate, and every stage is `unfinished` with
    `None` observations -- never a fabricated zero primal/dual/gap that a
    downstream reader could mistake for a real solve. No wall-clock assertion
    is made (that would be machine-speed-dependent).
    """
    _view, result = _run(_two_asset_pac_scenario(), time_budget_seconds=0.0)

    assert result.outcome == "no_incumbent"
    assert result.candidate is None
    assert result.finished_stage_count == 0
    assert result.anomaly is None
    assert result.stages  # the stages are still reported, just unfinished

    for stage in result.stages:
        assert stage.status == "unfinished"
        assert stage.primal is None
        assert stage.dual is None
        assert stage.absolute_gap is None
        assert stage.relative_gap is None


# --------------------------------------------------------------------------
# B5: no false infeasibility claim
# --------------------------------------------------------------------------


def test_infeasible_scenario_reports_floating_infeasible_only_from_global_stage() -> None:
    """A genuinely infeasible scenario (`ORDER_REQUIRED_MIN` above the route's
    reachable cap -- the same construction the oracle suite proves infeasible)
    must be reported as `reported_infeasible`, in the floating vocabulary that
    is never a proof claim, and *only* from the first, still-global stage-0.
    No later, `incumbent_face` stage may ever claim infeasibility.

    The exhaustive oracle corroborates that the scenario really is infeasible,
    so `reported_infeasible` is not a false claim.
    """
    scenario = _pac_scenario(required=R(5), route_cap=R(3))
    view, result = _run(scenario)

    assert result.outcome == "reported_infeasible"
    assert "proven" not in result.outcome  # floating word, not a proof verdict
    assert result.outcome != "infeasible"
    assert result.candidate is None
    assert result.anomaly is None

    stage_zero = result.stages[0]
    assert stage_zero.ordinal == 1
    assert stage_zero.scope == "global"
    assert stage_zero.scip_status == "infeasible"

    for later_stage in result.stages[1:]:
        assert later_stage.scope == "incumbent_face"
        assert later_stage.scip_status != "infeasible"

    # The floating "reported_infeasible" is corroborated by the exhaustive
    # oracle -- it is not a false infeasibility claim.
    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.feasible_candidates == 0
    assert oracle.best_candidate is None


# --------------------------------------------------------------------------
# B6: no-op scenario (doing nothing is optimal)
# --------------------------------------------------------------------------


def test_no_op_scenario_solver_incumbent_is_all_zero_and_matches_oracle() -> None:
    """With no cash, the one BUY decision's upper bound collapses to zero, so
    doing nothing is the only -- and therefore optimal -- move. The solver
    returns an all-zero candidate that replays feasible and matches the
    oracle's optimum on both quanta and the full lexicographic key.
    """
    scenario = _pac_scenario(cash=ZERO)
    view, result = _run(scenario)

    assert result.outcome == "incumbent"
    assert result.candidate is not None
    assert all(decision.quanta == 0 for decision in result.candidate.decisions)

    solver_evaluation = evaluate_exact_candidate(scenario, view, result.candidate)
    assert solver_evaluation.feasible is True

    oracle = run_exhaustive_oracle(scenario, view)
    assert oracle.best_candidate is not None
    assert oracle.best_evaluation is not None
    assert _quanta(result.candidate) == _quanta(oracle.best_candidate)
    assert _lexicographic_key(view, solver_evaluation) == _lexicographic_key(view, oracle.best_evaluation)
